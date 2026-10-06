import base64
import io
import os
from decimal import Decimal
from django.template.loader import render_to_string
from django.conf import settings
from .models import Invoice, Payment

_FONT_CACHE = {}


def _init_gtk_env():
    """Ensure GTK3 binaries are discoverable on Windows for WeasyPrint"""
    if os.name == "nt":
        candidates = [
            settings.BASE_DIR / "gtk3" / "bin",
            settings.BASE_DIR.parent / "backend" / "gtk3" / "bin",
            r"C:\Program Files\GTK3-Runtime Win64\bin",
        ]
        for candidate in candidates:
            if candidate.exists():
                c_str = str(candidate)
                if hasattr(os, "add_dll_directory"):
                    try:
                        os.add_dll_directory(c_str)
                    except Exception:
                        pass
                if c_str not in os.environ.get("PATH", ""):
                    os.environ["PATH"] = c_str + os.pathsep + os.environ.get("PATH", "")
                break


def get_bengali_font_base64():
    """Loads and caches base64-encoded NotoSansBengali fonts for embedding in PDFs"""
    if "regular" not in _FONT_CACHE:
        font_dir = settings.BASE_DIR / "billing" / "static" / "billing" / "fonts"
        reg_path = font_dir / "NotoSansBengali-Regular.ttf"
        bold_path = font_dir / "NotoSansBengali-Bold.ttf"
        reg_b64, bold_b64 = "", ""
        if reg_path.exists():
            with open(reg_path, "rb") as f:
                reg_b64 = base64.b64encode(f.read()).decode("utf-8")
        if bold_path.exists():
            with open(bold_path, "rb") as f:
                bold_b64 = base64.b64encode(f.read()).decode("utf-8")
        _FONT_CACHE["regular"] = reg_b64
        _FONT_CACHE["bold"] = bold_b64 or reg_b64
    return _FONT_CACHE["regular"], _FONT_CACHE["bold"]


def image_to_base64(file_field_or_path):
    """Converts local file or FieldFile to base64 string for embedded PDF rendering"""
    try:
        if not file_field_or_path:
            return None

        file_path = None
        if hasattr(file_field_or_path, "path"):
            file_path = file_field_or_path.path
        elif isinstance(file_field_or_path, str):
            if os.path.isabs(file_field_or_path) and os.path.exists(file_field_or_path):
                file_path = file_field_or_path
            else:
                candidate = settings.BASE_DIR / file_field_or_path
                if candidate.exists():
                    file_path = str(candidate)

        if file_path and os.path.exists(file_path):
            with open(file_path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        print("image_to_base64 error:", e)
    return None


def generate_invoice_pdf(invoice: Invoice) -> bytes:
    """
    Renders invoice HTML with Django template and converts to PDF using WeasyPrint (or xhtml2pdf fallback).
    """
    # Prepare base64 images for offline embedding
    logo_base64 = None
    if invoice.company_logo_snapshot:
        logo_base64 = image_to_base64(invoice.company_logo_snapshot)
    if not logo_base64 and invoice.company and invoice.company.logo:
        logo_base64 = image_to_base64(invoice.company.logo)

    # Fallback to local static logo if not in db
    if not logo_base64:
        static_logo = settings.BASE_DIR.parent / "frontend" / "public" / "logo.png"
        if not static_logo.exists():
            static_logo = settings.BASE_DIR.parent / "frontend" / "public" / "logo.jpg"
        if static_logo.exists():
            logo_base64 = image_to_base64(str(static_logo))

    sig_base64 = None
    if invoice.company_signature_snapshot:
        sig_base64 = image_to_base64(invoice.company_signature_snapshot)
    elif invoice.company and invoice.company.authorization_signature:
        sig_base64 = image_to_base64(invoice.company.authorization_signature)

    qr_base64 = None
    if invoice.qr_code:
        qr_base64 = image_to_base64(invoice.qr_code)

    if not qr_base64:
        try:
            import qrcode
            website = (invoice.company_website or "www.raktch.com").strip()
            if not website.startswith("http://") and not website.startswith("https://"):
                target_url = f"https://{website}"
            else:
                target_url = website
            if not target_url.endswith("/"):
                target_url += "/"
            inv_param = invoice.invoice_number or (f"INV-{invoice.id}" if invoice.id else "temp")
            qr_content = f"{target_url}?invoice={inv_param}"
            qr = qrcode.QRCode(
                version=None,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=5,
                border=2,
            )
            qr.add_data(qr_content)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        except Exception as qr_err:
            print("QR code on-the-fly error:", qr_err)

    website = (invoice.company_website or "www.raktch.com").strip()
    if not website.startswith("http://") and not website.startswith("https://"):
        target_url = f"https://{website}"
    else:
        target_url = website
    if not target_url.endswith("/"):
        target_url += "/"
    inv_param = invoice.invoice_number or (f"INV-{invoice.id}" if invoice.id else "temp")
    verification_url = f"{target_url}?invoice={inv_param}"

    total_qty = sum((item.quantity for item in invoice.items.all()), 0)

    _init_gtk_env()
    reg_font_b64, bold_font_b64 = get_bengali_font_base64()

    context = {
        "invoice": invoice,
        "total_quantity": total_qty,
        "logo_base64": logo_base64,
        "signature_base64": sig_base64,
        "qr_base64": qr_base64,
        "verification_url": verification_url,
        "bengali_font_regular_b64": reg_font_b64,
        "bengali_font_bold_b64": bold_font_b64,
    }

    html_content = render_to_string("billing/invoice_pdf.html", context)

    # 1. Attempt WeasyPrint
    try:
        import weasyprint
        pdf_bytes = weasyprint.HTML(string=html_content).write_pdf()
        return pdf_bytes
    except Exception as e:
        # 2. Fallback to xhtml2pdf (works reliably on pure Python/Windows without GTK3)
        print("WeasyPrint not available or missing GTK on system, falling back to xhtml2pdf:", e)
        from xhtml2pdf import pisa
        pdf_buffer = io.BytesIO()
        pisa_status = pisa.CreatePDF(html_content, dest=pdf_buffer)
        if pisa_status.err:
            raise RuntimeError(f"xhtml2pdf generation failed with error code: {pisa_status.err}")
        return pdf_buffer.getvalue()


def number_to_words(number, currency="Taka") -> str:
    """Converts a numerical amount into words (e.g. 5000 -> 'Five Thousand Taka Only')"""
    try:
        num = Decimal(str(number))
        taka = int(num)
        paisa = int(round((num - taka) * 100))

        ones = [
            "", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
            "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
            "Seventeen", "Eighteen", "Nineteen"
        ]
        tens = [
            "", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"
        ]

        def convert_less_than_thousand(n):
            if n == 0:
                return ""
            elif n < 20:
                return ones[n]
            elif n < 100:
                return tens[n // 10] + (" " + ones[n % 10] if n % 10 != 0 else "")
            else:
                return ones[n // 100] + " Hundred" + (" and " + convert_less_than_thousand(n % 100) if n % 100 != 0 else "")

        if taka == 0:
            words = f"Zero {currency}"
        else:
            parts = []
            if taka >= 10000000:
                crores = taka // 10000000
                parts.append(convert_less_than_thousand(crores) + " Crore")
                taka %= 10000000
            if taka >= 100000:
                lakhs = taka // 100000
                parts.append(convert_less_than_thousand(lakhs) + " Lakh")
                taka %= 100000
            if taka >= 1000:
                thousands = taka // 1000
                parts.append(convert_less_than_thousand(thousands) + " Thousand")
                taka %= 1000
            if taka > 0:
                parts.append(convert_less_than_thousand(taka))

            words = " ".join(parts).strip() + f" {currency}"

        if paisa > 0:
            words += " and " + convert_less_than_thousand(paisa) + " Paisa"

        return words.strip() + " Only"
    except Exception:
        return f"{currency} {number} Only"


def generate_money_receipt_pdf(payment: Payment) -> bytes:
    """
    Renders Money Receipt HTML using Django template with identical company branding,
    header, footer, signatures, and QR code, converting to PDF using WeasyPrint / xhtml2pdf.
    """
    invoice = payment.invoice

    # Prepare company logo
    logo_base64 = None
    if invoice.company_logo_snapshot:
        logo_base64 = image_to_base64(invoice.company_logo_snapshot)
    if not logo_base64 and invoice.company and invoice.company.logo:
        logo_base64 = image_to_base64(invoice.company.logo)
    if not logo_base64:
        static_logo = settings.BASE_DIR.parent / "frontend" / "public" / "logo.png"
        if not static_logo.exists():
            static_logo = settings.BASE_DIR.parent / "frontend" / "public" / "logo.jpg"
        if static_logo.exists():
            logo_base64 = image_to_base64(str(static_logo))

    # Prepare authorization signature
    sig_base64 = None
    if invoice.company_signature_snapshot:
        sig_base64 = image_to_base64(invoice.company_signature_snapshot)
    elif invoice.company and invoice.company.authorization_signature:
        sig_base64 = image_to_base64(invoice.company.authorization_signature)

    # QR Code generation for receipt authenticity
    qr_base64 = None
    try:
        import qrcode
        website = (invoice.company_website or "www.raktch.com").strip()
        if not website.startswith("http://") and not website.startswith("https://"):
            target_url = f"https://{website}"
        else:
            target_url = website
        if not target_url.endswith("/"):
            target_url += "/"
        verification_url = f"{target_url}?receipt={payment.receipt_number}&invoice={invoice.invoice_number}"
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=5,
            border=2,
        )
        qr.add_data(verification_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    except Exception:
        verification_url = f"https://www.raktch.com?receipt={payment.receipt_number}"

    # Ledger calculations up to and including this receipt
    all_earlier = invoice.payments.filter(id__lt=payment.id)
    prev_payments_sum = sum((p.amount for p in all_earlier), Decimal("0.00"))
    previous_settled = (invoice.advance_amount or Decimal("0.00")) + prev_payments_sum
    total_paid_upto_this = previous_settled + payment.amount
    remaining_due = max(invoice.payable_amount - total_paid_upto_this, Decimal("0.00"))

    currency_label = invoice.currency_symbol if invoice.currency_symbol in ["Tk", "BDT", "USD", "EUR"] else "Taka"
    amount_in_words = number_to_words(payment.amount, currency=currency_label)

    # Prepare official received stamp
    stamp_base64 = None
    stamp_path = settings.BASE_DIR.parent / "frontend" / "public" / "received_stamp.png"
    if stamp_path.exists():
        stamp_base64 = image_to_base64(str(stamp_path))

    _init_gtk_env()
    reg_font_b64, bold_font_b64 = get_bengali_font_base64()

    context = {
        "payment": payment,
        "invoice": invoice,
        "receipt_number": payment.receipt_number,
        "amount_in_words": amount_in_words,
        "previous_settled": previous_settled,
        "remaining_due": remaining_due,
        "logo_base64": logo_base64,
        "signature_base64": sig_base64,
        "qr_base64": qr_base64,
        "verification_url": verification_url,
        "stamp_base64": stamp_base64,
        "bengali_font_regular_b64": reg_font_b64,
        "bengali_font_bold_b64": bold_font_b64,
    }

    html_content = render_to_string("billing/money_receipt_pdf.html", context)

    # 1. Attempt WeasyPrint
    try:
        import weasyprint
        pdf_bytes = weasyprint.HTML(string=html_content).write_pdf()
        return pdf_bytes
    except Exception:
        from xhtml2pdf import pisa
        pdf_buffer = io.BytesIO()
        pisa_status = pisa.CreatePDF(html_content, dest=pdf_buffer)
        if pisa_status.err:
            raise RuntimeError(f"xhtml2pdf generation failed with error code: {pisa_status.err}")
        return pdf_buffer.getvalue()

