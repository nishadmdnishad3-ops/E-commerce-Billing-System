from decimal import Decimal
import datetime
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

from .models import (
    UserProfile,
    Company,
    BankAccount,
    Client,
    Service,
    InvoiceTemplate,
    Invoice,
    InvoiceItem,
    Payment,
    PaymentMethod,
    AuditLog,
    Settings,
)

User = get_user_model()


class InvoiceCalculationAndNumberTest(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            name="RAKTCH TECHNOLOGY & SOFTWARE",
            address="Sector 6, Uttara, Dhaka",
            email="support@raktch.com",
            phone="+8801581677077",
            website="www.raktch.com",
        )
        self.bank = BankAccount.objects.create(
            company=self.company,
            bank_name="Islami Bank PLC",
            account_name="RAKTCH TECHNOLOGY AND SOFTWARE",
            account_number="20502180100311104",
        )
        self.client = Client.objects.create(
            name="Rose International",
            contact_person="Director",
            phone="+8801700000000",
        )
        self.service = Service.objects.create(
            name="Supershop Software",
            default_tech_specification="Hosting & Maintenance Bill",
            default_price=Decimal("1000.00"),
        )
        self.template = InvoiceTemplate.objects.create(
            name="Standard Template",
            invoice_number_prefix="INV-",
        )

    def test_invoice_calculation_logic(self):
        """
        Verify pure Decimal calculations:
        Subtotal: 2 * 1000.00 = 2000.00
        Discount: 200.00
        Tax base: 1800.00
        VAT (5%): 90.00
        Payable: 1890.00
        Advance: 500.00
        Due: 1390.00
        """
        invoice = Invoice.objects.create(
            title="Monthly Service Bill",
            client=self.client,
            company=self.company,
            bank_account=self.bank,
            template=self.template,
            discount=Decimal("200.00"),
            vat_rate=Decimal("5.00"),
            advance_amount=Decimal("500.00"),
        )

        item1 = InvoiceItem.objects.create(
            invoice=invoice,
            sl=1,
            service=self.service,
            item_name="Supershop Software",
            quantity=Decimal("2.00"),
            unit_price=Decimal("1000.00"),
        )

        invoice.refresh_from_db()
        self.assertEqual(invoice.sub_total, Decimal("2000.00"))
        self.assertEqual(invoice.vat_amount, Decimal("90.00"))
        self.assertEqual(invoice.payable_amount, Decimal("1890.00"))
        self.assertEqual(invoice.advance_amount, Decimal("500.00"))
        self.assertEqual(invoice.due_amount, Decimal("1390.00"))
        self.assertEqual(invoice.status, "PARTIALLY_PAID")

        # Record a payment of 1390.00
        Payment.objects.create(
            invoice=invoice,
            amount=Decimal("1390.00"),
        )

        invoice.refresh_from_db()
        self.assertEqual(invoice.paid_amount, Decimal("1390.00"))
        self.assertEqual(invoice.due_amount, Decimal("0.00"))
        self.assertEqual(invoice.status, "PAID")

    def test_transaction_safe_invoice_number_generator(self):
        """Test that successive calls generate sequential, gapless, unique numbers"""
        date = datetime.date(2026, 4, 1)
        num1 = Invoice.generate_next_invoice_number(prefix="INV-", date=date)
        num2 = Invoice.generate_next_invoice_number(prefix="INV-", date=date)
        num3 = Invoice.generate_next_invoice_number(prefix="INV-", date=date)

        self.assertEqual(num1, "INV-202604-0001")
        self.assertEqual(num2, "INV-202604-0002")
        self.assertEqual(num3, "INV-202604-0003")
        self.assertNotEqual(num1, num2)
        self.assertNotEqual(num2, num3)

    def test_invoice_historical_snapshots(self):
        """Verify snapshots freeze company and bank details at invoice creation time"""
        invoice = Invoice.objects.create(
            title="Snapshot Test Bill",
            client=self.client,
            company=self.company,
            bank_account=self.bank,
        )

        self.assertEqual(invoice.company_name, "RAKTCH TECHNOLOGY & SOFTWARE")
        self.assertEqual(invoice.bank_name, "Islami Bank PLC")
        self.assertEqual(invoice.client_name, "Rose International")

        # Now change the live company name
        self.company.name = "NEW BRAND NAME"
        self.company.save()

        # The invoice snapshot must remain unchanged!
        invoice.refresh_from_db()
        self.assertEqual(invoice.company_name, "RAKTCH TECHNOLOGY & SOFTWARE")

    def test_multipage_pdf_generation_5_20_50_items(self):
        """Test generating PDF with 5, 20, and 50 line items across multiple pages"""
        from .pdf_service import generate_invoice_pdf

        prev_size = 0
        for count in [5, 20, 50]:
            inv = Invoice.objects.create(
                title=f"Multi-Page Bill ({count} items)",
                client=self.client,
                company=self.company,
                bank_account=self.bank,
                billing_month="April-2026",
            )
            for i in range(1, count + 1):
                InvoiceItem.objects.create(
                    invoice=inv,
                    sl=i,
                    service=self.service,
                    item_name=f"Service Line #{i} - Hosting & Maintenance",
                    technical_specification="Cloud infrastructure, backup & security update",
                    quantity=Decimal("1.00"),
                    unit_price=Decimal("100.00"),
                )

            inv.calculate_totals()
            inv.save()

            # Verify math accuracy
            expected_total = Decimal(str(count * 100)).quantize(Decimal("0.01"))
            self.assertEqual(inv.sub_total, expected_total)
            self.assertEqual(inv.payable_amount, expected_total)

            # Generate PDF
            pdf_bytes = generate_invoice_pdf(inv)
            self.assertIsNotNone(pdf_bytes)
            self.assertTrue(pdf_bytes.startswith(b"%PDF"))
            self.assertGreater(len(pdf_bytes), prev_size)
            prev_size = len(pdf_bytes)


class AuthAndRoleAPITest(APITestCase):
    def setUp(self):
        # Admin
        self.admin_user = User.objects.create_user("admin_user", "admin@test.com", "pass123", is_staff=True)
        UserProfile.objects.create(user=self.admin_user, role=UserProfile.ROLE_ADMIN)

        # Accountant
        self.accountant_user = User.objects.create_user("accountant_user", "acc@test.com", "pass123")
        UserProfile.objects.create(user=self.accountant_user, role=UserProfile.ROLE_ACCOUNTANT)

        # Staff
        self.staff_user = User.objects.create_user("staff_user", "staff@test.com", "pass123")
        UserProfile.objects.create(user=self.staff_user, role=UserProfile.ROLE_STAFF)

        self.company = Company.objects.create(name="Test Co")
        self.billing_client = Client.objects.create(name="Test Client")
        self.invoice = Invoice.objects.create(
            title="Invoice 1",
            client=self.billing_client,
            company=self.company,
        )

    def test_jwt_login(self):
        response = self.client.post("/api/auth/login/", {
            "username": "admin_user",
            "password": "pass123"
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

        # Use token to call /api/auth/me/
        token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        me_resp = self.client.get("/api/auth/me/")
        self.assertEqual(me_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(me_resp.data["username"], "admin_user")
        self.assertEqual(me_resp.data["role"], "ADMIN")

    def test_role_permissions_on_invoice_delete(self):
        # Staff cannot delete invoice
        self.client.force_authenticate(user=self.staff_user)
        resp = self.client.delete(f"/api/invoices/{self.invoice.id}/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

        # Accountant cannot delete invoice
        self.client.force_authenticate(user=self.accountant_user)
        resp = self.client.delete(f"/api/invoices/{self.invoice.id}/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

        # Admin CAN delete invoice
        self.client.force_authenticate(user=self.admin_user)
        resp = self.client.delete(f"/api/invoices/{self.invoice.id}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)


class Phase6PaymentAndDueTrackingTest(APITestCase):
    """
    Phase 6 tests:
    1. Payment entry (Method, Date, Transaction ID)
    2. Status Auto Update (Unpaid -> Partial -> Paid) and reverse on deletion
    3. Money Receipt PDF generation and download
    """
    def setUp(self):
        self.admin = User.objects.create_superuser(username="admin6", password="password6", email="admin6@test.com")
        UserProfile.objects.create(user=self.admin, role=UserProfile.ROLE_ADMIN)

        self.company = Company.objects.create(
            name="RAKTCH TECHNOLOGY & SOFTWARE",
            address="Sector 6, Uttara, Dhaka",
            email="support@raktch.com",
            phone="+8801581677077",
            website="www.raktch.com",
        )
        self.client_entity = Client.objects.create(name="ABC Enterprise", contact_person="Karim Ahmed", phone="01711111111")
        self.payment_method = PaymentMethod.objects.create(name="bKash Merchant", description="Direct bKash payment")

        self.invoice = Invoice.objects.create(
            title="Software Monthly Fee",
            client=self.client_entity,
            company=self.company,
            issue_date=datetime.date(2026, 10, 5),
            status="ISSUED",
        )
        InvoiceItem.objects.create(
            invoice=self.invoice,
            sl=1,
            item_name="Enterprise ERP Monthly",
            quantity=Decimal("1.00"),
            unit_price=Decimal("1000.00"),
            total=Decimal("1000.00"),
        )
        self.invoice.calculate_totals()
        self.invoice.save()

    def test_status_auto_update_flow(self):
        """Unpaid (ISSUED) -> Partial (PARTIALLY_PAID) -> Paid (PAID) -> reverse on delete"""
        self.client.force_authenticate(user=self.admin)
        inv = self.invoice
        inv.refresh_from_db()
        self.assertEqual(inv.status, "ISSUED")
        self.assertEqual(inv.due_amount, Decimal("1000.00"))

        # 1. Partial payment: 400.00
        p1_resp = self.client.post(f"/api/invoices/{inv.id}/record_payment/", {
            "amount": "400.00",
            "payment_method": self.payment_method.id,
            "payment_date": "2026-10-05",
            "transaction_id": "TRX-4001",
            "note": "Advance payment via bKash"
        })
        self.assertEqual(p1_resp.status_code, status.HTTP_201_CREATED)
        inv.refresh_from_db()
        self.assertEqual(inv.status, "PARTIALLY_PAID")
        self.assertEqual(inv.paid_amount, Decimal("400.00"))
        self.assertEqual(inv.due_amount, Decimal("600.00"))

        # 2. Settle remaining 600.00 -> PAID
        p2_resp = self.client.post(f"/api/invoices/{inv.id}/record_payment/", {
            "amount": "600.00",
            "payment_method": self.payment_method.id,
            "payment_date": "2026-10-06",
            "transaction_id": "TRX-4002",
            "note": "Final settlement"
        })
        self.assertEqual(p2_resp.status_code, status.HTTP_201_CREATED)
        inv.refresh_from_db()
        self.assertEqual(inv.status, "PAID")
        self.assertEqual(inv.paid_amount, Decimal("1000.00"))
        self.assertEqual(inv.due_amount, Decimal("0.00"))

        # 3. Delete second payment -> Revert to PARTIALLY_PAID
        p2_id = p2_resp.data["payment"]["id"]
        del_resp = self.client.delete(f"/api/payments/{p2_id}/")
        self.assertEqual(del_resp.status_code, status.HTTP_204_NO_CONTENT)
        inv.refresh_from_db()
        self.assertEqual(inv.status, "PARTIALLY_PAID")
        self.assertEqual(inv.paid_amount, Decimal("400.00"))
        self.assertEqual(inv.due_amount, Decimal("600.00"))

        # 4. Delete first payment -> Revert to ISSUED (Unpaid)
        p1_id = p1_resp.data["payment"]["id"]
        del_resp2 = self.client.delete(f"/api/payments/{p1_id}/")
        self.assertEqual(del_resp2.status_code, status.HTTP_204_NO_CONTENT)
        inv.refresh_from_db()
        self.assertEqual(inv.status, "ISSUED")
        self.assertEqual(inv.paid_amount, Decimal("0.00"))
        self.assertEqual(inv.due_amount, Decimal("1000.00"))

    def test_money_receipt_pdf_endpoints(self):
        """Test download and preview of Money Receipt PDF"""
        self.client.force_authenticate(user=self.admin)

        p_resp = self.client.post(f"/api/invoices/{self.invoice.id}/record_payment/", {
            "amount": "500.00",
            "payment_method": self.payment_method.id,
            "payment_date": "2026-10-05",
            "transaction_id": "TRX-RCPT-99",
            "note": "Payment for receipt generation"
        })
        p_id = p_resp.data["payment"]["id"]

        # Download Receipt PDF
        dl_resp = self.client.get(f"/api/payments/{p_id}/download_receipt/")
        self.assertEqual(dl_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(dl_resp["Content-Type"], "application/pdf")
        self.assertIn("attachment; filename=", dl_resp["Content-Disposition"])
        self.assertGreater(len(dl_resp.content), 1000)

        # Preview Receipt PDF
        prev_resp = self.client.get(f"/api/payments/{p_id}/preview_receipt/")
        self.assertEqual(prev_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(prev_resp["Content-Type"], "application/pdf")
        self.assertIn("inline; filename=", prev_resp["Content-Disposition"])
        self.assertGreater(len(prev_resp.content), 1000)

    def test_dashboard_summary_and_deletion_deduction(self):
        """Test that deleting a payment or paid invoice immediately deducts from collected and due metrics"""
        self.client.force_authenticate(user=self.admin)

        # 1. Initial summary check
        s1 = self.client.get("/api/invoices/summary/")
        self.assertEqual(s1.status_code, status.HTTP_200_OK)
        self.assertEqual(s1.data["total_billed"], 1000.0)
        self.assertEqual(s1.data["total_collected"], 0.0)
        self.assertEqual(s1.data["total_due"], 1000.0)

        # 2. Record payment
        p_resp = self.client.post(f"/api/invoices/{self.invoice.id}/record_payment/", {
            "amount": "600.00",
            "payment_method": self.payment_method.id,
            "payment_date": "2026-10-05",
        })
        p_id = p_resp.data["payment"]["id"]

        s2 = self.client.get("/api/invoices/summary/")
        self.assertEqual(s2.data["total_collected"], 600.0)
        self.assertEqual(s2.data["total_due"], 400.0)

        # 3. Delete payment -> must immediately deduct from total_collected
        del_p = self.client.delete(f"/api/payments/{p_id}/")
        self.assertEqual(del_p.status_code, status.HTTP_204_NO_CONTENT)

        s3 = self.client.get("/api/invoices/summary/")
        self.assertEqual(s3.data["total_collected"], 0.0)
        self.assertEqual(s3.data["total_due"], 1000.0)

        # 4. Make bill fully paid (received bill), then delete the invoice
        self.client.post(f"/api/invoices/{self.invoice.id}/record_payment/", {
            "amount": "1000.00",
            "payment_method": self.payment_method.id,
            "payment_date": "2026-10-05",
        })
        s4 = self.client.get("/api/invoices/summary/")
        self.assertEqual(s4.data["total_collected"], 1000.0)
        self.assertEqual(s4.data["total_due"], 0.0)

        del_inv = self.client.delete(f"/api/invoices/{self.invoice.id}/")
        self.assertEqual(del_inv.status_code, status.HTTP_204_NO_CONTENT)

        s5 = self.client.get("/api/invoices/summary/")
        self.assertEqual(s5.data["total_billed"], 0.0)
        self.assertEqual(s5.data["total_collected"], 0.0)
        self.assertEqual(s5.data["total_due"], 0.0)


class SecurityAndRBACPermissionsTest(APITestCase):
    def setUp(self):
        # 1. Admin
        self.admin = User.objects.create_user("admin_sec", "admin_sec@test.com", "AdminPass123!", is_staff=True, is_superuser=True)
        UserProfile.objects.create(user=self.admin, role=UserProfile.ROLE_ADMIN)

        # 2. Accountant
        self.accountant = User.objects.create_user("acc_sec", "acc_sec@test.com", "AccPass123!")
        UserProfile.objects.create(user=self.accountant, role=UserProfile.ROLE_ACCOUNTANT)

        # 3. Staff
        self.staff = User.objects.create_user("staff_sec", "staff_sec@test.com", "StaffPass123!")
        UserProfile.objects.create(user=self.staff, role=UserProfile.ROLE_STAFF)

        # 4. Deactivated User
        self.inactive_user = User.objects.create_user("inactive_user", "inactive@test.com", "InactivePass123!", is_active=False)
        UserProfile.objects.create(user=self.inactive_user, role=UserProfile.ROLE_STAFF)

        # Base billing objects
        self.company = Company.objects.create(name="Security Test Co", is_default=True)
        self.settings = Settings.objects.create(default_company=self.company)
        self.client_entity = Client.objects.create(name="Secure Client")
        self.invoice = Invoice.objects.create(
            title="Secure Invoice",
            client=self.client_entity,
            company=self.company,
            status="ISSUED",
        )
        self.payment = Payment.objects.create(
            invoice=self.invoice,
            amount=Decimal("500.00"),
        )

    def test_unauthenticated_api_and_pdf_endpoints_return_401(self):
        """Unauthenticated requests to all API and PDF endpoints must return 401 Unauthorized"""
        self.client.logout()

        endpoints = [
            f"/api/invoices/",
            f"/api/invoices/{self.invoice.id}/",
            f"/api/invoices/{self.invoice.id}/download_pdf/",
            f"/api/invoices/{self.invoice.id}/preview_pdf/",
            f"/api/payments/",
            f"/api/payments/{self.payment.id}/download_receipt/",
            f"/api/payments/{self.payment.id}/preview_receipt/",
            f"/api/clients/",
            f"/api/settings/",
            f"/api/users/",
            f"/api/audit-logs/",
        ]
        for url in endpoints:
            resp = self.client.get(url)
            self.assertEqual(
                resp.status_code,
                status.HTTP_401_UNAUTHORIZED,
                f"Endpoint {url} did not return 401 for unauthenticated request (got {resp.status_code})"
            )

    def test_staff_cannot_delete_payment_or_modify_settings(self):
        """STAFF role cannot delete payments or modify settings (returns 403)"""
        self.client.force_authenticate(user=self.staff)

        # Attempt to delete payment -> 403
        del_p_resp = self.client.delete(f"/api/payments/{self.payment.id}/")
        self.assertEqual(del_p_resp.status_code, status.HTTP_403_FORBIDDEN)

        # Attempt to modify settings -> 403
        settings_resp = self.client.patch(f"/api/settings/{self.settings.id}/", {"default_nb_text": "Updated by staff"})
        self.assertEqual(settings_resp.status_code, status.HTTP_403_FORBIDDEN)

        # Attempt to modify company -> 403
        comp_resp = self.client.patch(f"/api/companies/{self.company.id}/", {"name": "Hacked Co"})
        self.assertEqual(comp_resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_accountant_cannot_access_user_management_or_audit_logs(self):
        """ACCOUNTANT role cannot access user management or audit logs (returns 403)"""
        self.client.force_authenticate(user=self.accountant)

        # User management list/create -> 403
        users_resp = self.client.get("/api/users/")
        self.assertEqual(users_resp.status_code, status.HTTP_403_FORBIDDEN)

        create_user_resp = self.client.post("/api/users/", {
            "username": "rogue_user",
            "password": "Password123!",
            "role": "ADMIN"
        })
        self.assertEqual(create_user_resp.status_code, status.HTTP_403_FORBIDDEN)

        # Audit logs -> 403
        audit_resp = self.client.get("/api/audit-logs/")
        self.assertEqual(audit_resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_deactivated_user_cannot_login(self):
        """Deactivated user (is_active=False) cannot log in (returns 401)"""
        resp = self.client.post("/api/auth/login/", {
            "username": "inactive_user",
            "password": "InactivePass123!"
        })
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("deactivated", resp.data.get("detail", "").lower())

    def test_logout_blacklists_refresh_token(self):
        """Logging out blacklists the refresh token so it cannot be used again"""
        # 1. Login
        login_resp = self.client.post("/api/auth/login/", {
            "username": "admin_sec",
            "password": "AdminPass123!"
        })
        self.assertEqual(login_resp.status_code, status.HTTP_200_OK)
        refresh_token = login_resp.data["refresh"]
        access_token = login_resp.data["access"]

        # 2. Logout with refresh token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        logout_resp = self.client.post("/api/auth/logout/", {"refresh": refresh_token})
        self.assertEqual(logout_resp.status_code, status.HTTP_200_OK)

        # 3. Try to use blacklisted refresh token to refresh -> 401
        self.client.credentials()  # clear headers
        refresh_resp = self.client.post("/api/auth/refresh/", {"refresh": refresh_token})
        self.assertEqual(refresh_resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_audit_log_properly_created(self):
        """AuditLog entries are created on login, invoice create, payment create, and payment delete"""
        # 1. Login generates audit log
        login_resp = self.client.post("/api/auth/login/", {
            "username": "admin_sec",
            "password": "AdminPass123!"
        })
        self.assertEqual(login_resp.status_code, status.HTTP_200_OK)
        token = login_resp.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        self.assertTrue(AuditLog.objects.filter(action=AuditLog.ACTION_LOGIN_SUCCESS, username="admin_sec").exists())

        # 2. Invoice create generates audit log
        inv_resp = self.client.post("/api/invoices/", {
            "title": "Audited Bill",
            "client": self.client_entity.id,
            "company": self.company.id,
            "status": "ISSUED",
        })
        self.assertEqual(inv_resp.status_code, status.HTTP_201_CREATED)
        new_inv_id = inv_resp.data["id"]
        self.assertTrue(AuditLog.objects.filter(action=AuditLog.ACTION_CREATE, model_name="Invoice", object_id=str(new_inv_id)).exists())

        # 3. Payment delete generates audit log
        del_resp = self.client.delete(f"/api/payments/{self.payment.id}/")
        self.assertEqual(del_resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertTrue(AuditLog.objects.filter(action=AuditLog.ACTION_DELETE, model_name="Payment", object_id=str(self.payment.id)).exists())


