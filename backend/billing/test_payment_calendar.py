import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import (
    Client, Company, Invoice, InvoiceItem, Payment, PaymentMethod,
    Service, Subscription, UserProfile,
)
from .payment_calendar import (
    STATUS_DUE, STATUS_NO_PAYMENT, STATUS_OVERDUE, STATUS_PAID,
    STATUS_PARTIALLY_PAID, STATUS_UPCOMING, calendar_data, client_history,
    payment_status,
)

D = datetime.date


def make_invoice(client, company, amount, due, title="Hosting", **kwargs):
    inv = Invoice.objects.create(
        client=client, company=company, title=title,
        issue_date=kwargs.pop("issue_date", due), due_date=due, **kwargs,
    )
    InvoiceItem.objects.create(invoice=inv, item_name=title, quantity=1, unit_price=Decimal(amount))
    inv.refresh_from_db()
    return inv


class PaymentStatusRuleTests(TestCase):
    due = D(2026, 10, 10)

    def test_rule(self):
        s = lambda paid, today, **kw: payment_status(3000, paid, self.due, today, **kw)
        self.assertEqual(s(3000, D(2026, 10, 20)), STATUS_PAID)
        self.assertEqual(s(1000, D(2026, 10, 20)), STATUS_PARTIALLY_PAID)
        self.assertEqual(s(0, D(2026, 10, 11)), STATUS_OVERDUE)
        self.assertEqual(s(0, D(2026, 10, 10)), STATUS_DUE)
        self.assertEqual(s(0, D(2026, 10, 9)), STATUS_UPCOMING)
        self.assertEqual(s(0, D(2026, 10, 9), has_bill=False), STATUS_NO_PAYMENT)


class CalendarDataTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Raktch")
        self.alpha = Client.objects.create(name="Alpha Ltd")
        self.gamma = Client.objects.create(name="Gamma Ltd")
        self.bkash = PaymentMethod.objects.create(name="bKash")
        self.cash = PaymentMethod.objects.create(name="Cash")

    def day(self, data, iso):
        return next(d for d in data["days"] if d["date"] == iso)

    def test_partial_then_full_payment_updates_status_and_totals(self):
        inv = make_invoice(self.gamma, self.company, "5000", D(2026, 10, 10))
        Payment.objects.create(invoice=inv, amount=Decimal("3000"), payment_date=D(2026, 10, 5), payment_method=self.bkash, transaction_id="TX1")
        row = self.day(calendar_data(2026, 10), "2026-10-10")["items"][0]
        self.assertEqual((row["status"], row["paid_amount"], row["remaining_amount"]), (STATUS_PARTIALLY_PAID, "3000.00", "2000.00"))
        self.assertEqual(row["payment_method"], "bKash")

        Payment.objects.create(invoice=inv, amount=Decimal("2000"), payment_date=D(2026, 10, 9), payment_method=self.cash)
        data = calendar_data(2026, 10)
        row = self.day(data, "2026-10-10")["items"][0]
        self.assertEqual((row["status"], row["remaining_amount"]), (STATUS_PAID, "0.00"))
        self.assertEqual(data["summary"]["total_collected"], "5000.00")
        self.assertEqual(data["summary"]["total_due"], "0.00")

    def test_month_summary_and_day_aggregate(self):
        a = make_invoice(self.alpha, self.company, "4000", D(2026, 10, 10))
        make_invoice(self.gamma, self.company, "6000", D(2026, 10, 10))
        make_invoice(self.gamma, self.company, "1000", D(2026, 11, 10))  # other month
        Payment.objects.create(invoice=a, amount=Decimal("4000"), payment_date=D(2026, 10, 1))
        data = calendar_data(2026, 10)
        day = self.day(data, "2026-10-10")
        self.assertEqual((day["count"], day["expected"], day["collected"], day["due"]), (2, "10000.00", "4000.00", "6000.00"))
        s = data["summary"]
        self.assertEqual((s["total_expected"], s["total_collected"], s["total_due"], s["paid_clients"]), ("10000.00", "4000.00", "6000.00", 1))

    def test_filters_and_cancelled_excluded(self):
        a = make_invoice(self.alpha, self.company, "4000", D(2026, 10, 10))
        make_invoice(self.gamma, self.company, "6000", D(2026, 10, 12), status="CANCELLED")
        Payment.objects.create(invoice=a, amount=Decimal("1000"), payment_date=D(2026, 10, 1), payment_method=self.bkash)
        self.assertEqual(calendar_data(2026, 10)["summary"]["total_bills"], 1)
        self.assertEqual(calendar_data(2026, 10, client_id=self.gamma.id)["summary"]["total_bills"], 0)
        self.assertEqual(calendar_data(2026, 10, method_id=self.bkash.id)["summary"]["total_bills"], 1)
        self.assertEqual(calendar_data(2026, 10, method_id=self.cash.id)["summary"]["total_bills"], 0)
        self.assertEqual(calendar_data(2026, 10, status=STATUS_PARTIALLY_PAID)["summary"]["total_bills"], 1)

    def test_subscription_without_invoice_is_no_payment_and_not_duplicated(self):
        svc = Service.objects.create(name="Support", default_price=Decimal("2500"))
        sub = Subscription.objects.create(client=self.alpha, service=svc, start_date=D(2026, 1, 1))
        rows = [i for d in calendar_data(2026, 10)["days"] for i in d["items"]]
        self.assertEqual([(r["status"], r["expected_amount"], r["has_invoice"]) for r in rows], [(STATUS_NO_PAYMENT, "2500.00", False)])
        self.assertEqual(Invoice.objects.count(), 0)  # nothing created

        # Once the real invoice exists for that period, the placeholder disappears.
        inv = make_invoice(self.alpha, self.company, "2500", D(2026, 10, 1), subscription=sub, billing_period="2026-10")
        rows = [i for d in calendar_data(2026, 10)["days"] for i in d["items"]]
        self.assertEqual([r["invoice_id"] for r in rows], [inv.id])

    def test_client_history(self):
        aug = make_invoice(self.gamma, self.company, "3000", D(2026, 8, 10))
        make_invoice(self.gamma, self.company, "3000", D(2026, 9, 10))
        Payment.objects.create(invoice=aug, amount=Decimal("3000"), payment_date=D(2026, 8, 9))
        hist = client_history(self.gamma.id, months=3, end_year=2026, end_month=10)["history"]
        self.assertEqual([(h["label"], h["paid"], h["due"]) for h in hist], [("August 2026", "3000.00", "0.00"), ("September 2026", "0.00", "3000.00")])
        self.assertEqual(hist[0]["status"], STATUS_PAID)


class PaymentApiTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user("acct", password="x")
        UserProfile.objects.create(user=user, role=UserProfile.ROLE_ACCOUNTANT)
        self.api = APIClient()
        self.api.force_authenticate(user)
        company = Company.objects.create(name="Raktch")
        self.client_obj = Client.objects.create(name="Gamma Ltd")
        self.invoice = make_invoice(self.client_obj, company, "3000", D(2026, 10, 10))

    def test_calendar_summary_history_status_endpoints(self):
        r = self.api.get("/api/payments/calendar/", {"month": 10, "year": 2026})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["summary"]["total_expected"], "3000.00")
        self.assertEqual(self.api.get("/api/payments/summary/", {"month": 10, "year": 2026}).data["total_due"], "3000.00")
        self.assertEqual(self.api.get(f"/api/payments/client/{self.client_obj.id}/history/").status_code, 200)
        self.assertEqual(self.api.get("/api/payments/status/", {"invoice": self.invoice.id}).data["remaining_amount"], "3000.00")

    def test_bad_params_are_400_not_500(self):
        self.assertEqual(self.api.get("/api/payments/calendar/", {"month": 13}).status_code, 400)
        self.assertEqual(self.api.get("/api/payments/calendar/", {"month": "x"}).status_code, 400)
        self.assertEqual(self.api.get("/api/payments/calendar/", {"status": "BOGUS"}).status_code, 400)
        self.assertEqual(self.api.get("/api/payments/client/9999/history/").status_code, 404)

    def test_overpayment_and_zero_rejected_on_both_endpoints(self):
        for amount in ("3000.01", "0", "-5"):
            r = self.api.post("/api/payments/", {"invoice": self.invoice.id, "amount": amount, "payment_date": "2026-10-01"}, format="json")
            self.assertEqual(r.status_code, 400, amount)
            r = self.api.post(f"/api/invoices/{self.invoice.id}/record_payment/", {"amount": amount}, format="json")
            self.assertEqual(r.status_code, 400, amount)
        self.assertEqual(Payment.objects.count(), 0)

    def test_post_payment_updates_calendar(self):
        r = self.api.post("/api/payments/", {"invoice": self.invoice.id, "amount": "1000", "payment_date": "2026-10-01"}, format="json")
        self.assertEqual(r.status_code, 201)
        row = self.api.get("/api/payments/calendar/", {"month": 10, "year": 2026}).data["days"][0]["items"][0]
        self.assertEqual((row["status"], row["remaining_amount"]), (STATUS_PARTIALLY_PAID, "2000.00"))
