import base64
import io
import os
from django.template.loader import render_to_string
from django.conf import settings
from .models import Invoice


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

    context = {
        "invoice": invoice,
        "total_quantity": total_qty,
        "logo_base64": logo_base64,
        "signature_base64": sig_base64,
        "qr_base64": qr_base64,
        "verification_url": verification_url,
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
