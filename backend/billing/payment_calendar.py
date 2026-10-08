"""
Monthly payment calendar logic.

The database is the source of truth: every figure here is derived from
Invoice (payable / advance / paid / due) and Payment rows. No new tables are
used. The frontend only renders what these functions return.

Status rule (single place, reused everywhere) -> `payment_status()`.
"""
import calendar
import datetime
from collections import defaultdict
from decimal import Decimal

from django.db.models import Q
from django.utils import timezone

from .models import Client, Invoice, Settings, Subscription
from .services import get_effective_billing_date

ZERO = Decimal("0.00")

STATUS_PAID = "PAID"
STATUS_PARTIALLY_PAID = "PARTIALLY_PAID"
STATUS_DUE = "DUE"
STATUS_OVERDUE = "OVERDUE"
STATUS_UPCOMING = "UPCOMING"
STATUS_NO_PAYMENT = "NO_PAYMENT"

VALID_STATUSES = {
    STATUS_PAID, STATUS_PARTIALLY_PAID, STATUS_DUE,
    STATUS_OVERDUE, STATUS_UPCOMING, STATUS_NO_PAYMENT,
}


def payment_status(expected, paid, due_date, today=None, has_bill=True):
    """
    The one status rule used by the calendar, summary and client history.

    - no bill exists for the month          -> NO_PAYMENT
    - paid >= expected                      -> PAID
    - 0 < paid < expected                   -> PARTIALLY_PAID
    - unpaid, today > due date              -> OVERDUE
    - unpaid, today == due date             -> DUE
    - unpaid, today < due date              -> UPCOMING
    """
    if not has_bill:
        return STATUS_NO_PAYMENT
    today = today or timezone.localdate()
    expected = Decimal(expected or 0)
    paid = Decimal(paid or 0)
    if paid >= expected:
        return STATUS_PAID
    if paid > 0:
        return STATUS_PARTIALLY_PAID
    if today > due_date:
        return STATUS_OVERDUE
    if today == due_date:
        return STATUS_DUE
    return STATUS_UPCOMING


def _money(value):
    return str(Decimal(value or 0).quantize(Decimal("0.01")))


def _month_bounds(year, month):
    last = calendar.monthrange(year, month)[1]
    return datetime.date(year, month, 1), datetime.date(year, month, last)


def _invoice_row(inv, today):
    """Serialize one invoice as a monthly obligation row."""
    due_date = inv.due_date or inv.issue_date
    expected = inv.payable_amount
    paid = (inv.advance_amount or ZERO) + (inv.paid_amount or ZERO)
    remaining = inv.due_amount
    payments = sorted(inv.payments.all(), key=lambda p: (p.payment_date, p.id))
    last = payments[-1] if payments else None
    return {
        "key": f"inv-{inv.id}",
        "has_invoice": True,
        "invoice_id": inv.id,
        "invoice_number": inv.invoice_number,
        "invoice_status": inv.status,
        "client_id": inv.client_id,
        "client_name": inv.client_name or inv.client.name,
        "title": inv.title,
        "billing_month": inv.billing_month,
        "currency_symbol": inv.currency_symbol,
        "due_date": due_date.isoformat(),
        "expected_amount": _money(expected),
        "paid_amount": _money(paid),
        "remaining_amount": _money(remaining),
        "status": payment_status(expected, paid, due_date, today),
        "payment_id": last.id if last else None,
        "payment_date": last.payment_date.isoformat() if last else None,
        "payment_method": last.payment_method.name if last and last.payment_method else None,
        "transaction_id": last.transaction_id if last else None,
        "payment_count": len(payments),
    }


def _virtual_rows(year, month, client_id=None):
    """
    Active monthly subscriptions that have no invoice yet for this month.
    Nothing is written to the database - these rows exist only in the
    response, so they can never create duplicate bills.
    """
    first, last = _month_bounds(year, month)
    settings_obj = Settings.objects.first()
    billing_day = settings_obj.auto_billing_day if settings_obj else 1
    currency = settings_obj.currency_symbol if settings_obj else "Tk"

    subs = (
        Subscription.objects.filter(
            is_active=True,
            billing_cycle=Subscription.CYCLE_MONTHLY,
            client__is_active=True,
            start_date__lte=last,
        )
        .filter(Q(end_date__isnull=True) | Q(end_date__gte=first))
        .select_related("client", "service")
    )
    if client_id:
        subs = subs.filter(client_id=client_id)

    period_keys = {f"{year}-{month:02d}", f"{calendar.month_name[month]}-{year}"}
    billed = set(
        Invoice.objects.filter(subscription__in=subs, billing_period__in=period_keys)
        .exclude(status="CANCELLED")
        .values_list("subscription_id", flat=True)
    )

    due_date = get_effective_billing_date(year, month, billing_day)
    rows = []
    for sub in subs:
        if sub.pk in billed:
            continue
        expected = sub.effective_price
        rows.append({
            "key": f"sub-{sub.pk}-{year}-{month}",
            "has_invoice": False,
            "invoice_id": None,
            "invoice_number": None,
            "invoice_status": None,
            "client_id": sub.client_id,
            "client_name": sub.client.name,
            "title": f"{sub.effective_name} ({calendar.month_name[month]}-{year})",
            "billing_month": f"{calendar.month_name[month]}-{year}",
            "currency_symbol": currency,
            "due_date": due_date.isoformat(),
            "expected_amount": _money(expected),
            "paid_amount": _money(ZERO),
            "remaining_amount": _money(expected),
            "status": STATUS_NO_PAYMENT,
            "payment_id": None,
            "payment_date": None,
            "payment_method": None,
            "transaction_id": None,
            "payment_count": 0,
        })
    return rows


def month_rows(year, month, client_id=None, status=None, method_id=None, today=None):
    """All obligations whose (effective) due date falls in the month, filtered."""
    today = today or timezone.localdate()
    first, last = _month_bounds(year, month)

    qs = (
        Invoice.objects.exclude(status="CANCELLED")
        .filter(
            Q(due_date__range=(first, last))
            | Q(due_date__isnull=True, issue_date__range=(first, last))
        )
        .select_related("client")
        .prefetch_related("payments__payment_method")
    )
    if client_id:
        qs = qs.filter(client_id=client_id)
    if method_id:
        qs = qs.filter(payments__payment_method_id=method_id).distinct()

    rows = [_invoice_row(inv, today) for inv in qs]
    # Virtual "no bill yet" rows have no payments, so a method filter excludes them.
    if not method_id:
        rows += _virtual_rows(year, month, client_id)

    if status:
        rows = [r for r in rows if r["status"] == status]
    rows.sort(key=lambda r: (r["due_date"], r["client_name"].lower()))
    return rows


def summarize(rows):
    """Aggregate summary cards from rows (the same rows the calendar shows)."""
    expected = sum((Decimal(r["expected_amount"]) for r in rows), ZERO)
    collected = sum((Decimal(r["paid_amount"]) for r in rows), ZERO)
    by_status = defaultdict(set)
    for r in rows:
        by_status[r["status"]].add(r["client_id"])
    return {
        "total_expected": _money(expected),
        "total_collected": _money(collected),
        "total_due": _money(max(expected - collected, ZERO)),
        "paid_clients": len(by_status[STATUS_PAID]),
        "due_clients": len(by_status[STATUS_DUE] | by_status[STATUS_UPCOMING] | by_status[STATUS_PARTIALLY_PAID]),
        "overdue_clients": len(by_status[STATUS_OVERDUE]),
        "no_payment_clients": len(by_status[STATUS_NO_PAYMENT]),
        "total_bills": len(rows),
    }


def calendar_data(year, month, **filters):
    """Month grid payload: per-day aggregates plus the rows behind them."""
    rows = month_rows(year, month, **filters)
    days = {}
    for r in rows:
        d = days.setdefault(r["due_date"], {
            "date": r["due_date"], "count": 0, "expected": ZERO, "collected": ZERO,
            "status_counts": defaultdict(int), "items": [],
        })
        d["count"] += 1
        d["expected"] += Decimal(r["expected_amount"])
        d["collected"] += Decimal(r["paid_amount"])
        d["status_counts"][r["status"]] += 1
        d["items"].append(r)
    day_list = [
        {
            "date": d["date"],
            "count": d["count"],
            "expected": _money(d["expected"]),
            "collected": _money(d["collected"]),
            "due": _money(max(d["expected"] - d["collected"], ZERO)),
            "status_counts": dict(d["status_counts"]),
            "items": d["items"],
        }
        for d in days.values()
    ]
    day_list.sort(key=lambda d: d["date"])
    return {
        "year": year,
        "month": month,
        "today": timezone.localdate().isoformat(),
        "summary": summarize(rows),
        "days": day_list,
    }


def client_history(client_id, months=12, end_year=None, end_month=None):
    """Month-by-month expected/paid/due for one client, oldest first."""
    today = timezone.localdate()
    end_year = end_year or today.year
    end_month = end_month or today.month
    order = [STATUS_OVERDUE, STATUS_NO_PAYMENT, STATUS_PARTIALLY_PAID, STATUS_DUE, STATUS_UPCOMING, STATUS_PAID]
    out = []
    for i in range(months - 1, -1, -1):
        total = end_year * 12 + (end_month - 1) - i
        y, m = total // 12, total % 12 + 1
        rows = month_rows(y, m, client_id=client_id, today=today)
        if not rows:
            continue
        expected = sum((Decimal(r["expected_amount"]) for r in rows), ZERO)
        paid = sum((Decimal(r["paid_amount"]) for r in rows), ZERO)
        statuses = {r["status"] for r in rows}  # month status = worst bill status
        out.append({
            "year": y,
            "month": m,
            "label": f"{calendar.month_name[m]} {y}",
            "expected": _money(expected),
            "paid": _money(paid),
            "due": _money(max(expected - paid, ZERO)),
            "status": next(s for s in order if s in statuses),
            "bills": rows,
        })
    client = Client.objects.filter(pk=client_id).first()
    return {
        "client_id": client_id,
        "client_name": client.name if client else "",
        "history": out,
    }


def parse_month_year(params):
    """Validated (year, month) from query params; defaults to the current month."""
    today = timezone.localdate()
    try:
        year = int(params.get("year") or today.year)
        month = int(params.get("month") or today.month)
    except (TypeError, ValueError):
        raise ValueError("month and year must be integers")
    if not (1 <= month <= 12) or not (1970 <= year <= 2200):
        raise ValueError("month must be 1-12 and year 1970-2200")
    return year, month
