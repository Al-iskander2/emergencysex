# logic/send_email.py
from dataclasses import dataclass
from typing import Optional, Tuple
import os
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.utils import timezone
from django.shortcuts import get_object_or_404

# Ajusta si tu modelo real se llama SalesInvoice
from budsi_database.models import Invoice, Contact

@dataclass
class EmailResult:
    success: bool
    message: str
    status: int = 200

def _render_subject(invoice: Invoice) -> str:
    # Puedes cambiar a templates si quieres (emails/invoice_subject.txt)
    return f"Your invoice {invoice.invoice_number} from BudsiDesk"

def _render_bodies(invoice: Invoice, user) -> Tuple[str, str]:
    # Usa plantillas si ya las tienes; si no, aquí va un fallback sencillo
    ctx = {"invoice": invoice, "user": user}
    try:
        text_body = render_to_string("emails/invoice_body.txt", ctx)
    except Exception:
        text_body = (
            f"Hi,\n\nHere is your invoice {invoice.invoice_number}."
            f"\nTotal: €{invoice.total} | Date: {invoice.date}\n\nBest,\nBudsiDesk"
        )
    try:
        html_body = render_to_string("emails/invoice_body.html", ctx)
    except Exception:
        html_body = (
            f"<p>Hi,</p><p>Here is your invoice <b>{invoice.invoice_number}</b>."
            f"<br>Total: <b>€{invoice.total}</b> | Date: {invoice.date}</p><p>Best,<br>BudsiDesk</p>"
        )
    return text_body, html_body

def _attach_original_if_any(msg: EmailMultiAlternatives, invoice: Invoice) -> None:
    f = getattr(invoice, "original_file", None)
    if not f:
        return
    try:
        filename = os.path.basename(f.name or "invoice.bin")
        # asegurar lectura
        fileobj = f.open("rb")
        try:
            msg.attach(filename, fileobj.read(), "application/octet-stream")
        finally:
            fileobj.close()
    except Exception:
        # adjunto opcional: si falla, no rompemos el envío
        pass

def send_invoice_email(*, user, invoice_id: int, to_email: str) -> EmailResult:
    """
    Llama a esta función desde donde quieras (vista, tarea async, etc.).
    - Valida ownership (user solo puede mandar sus facturas)
    - Valida email
    - Renderiza subject + body
    - Adjunta archivo original si existe
    """
    try:
        # Validación email
        to_email = (to_email or "").strip()
        try:
            validate_email(to_email)
        except ValidationError:
            return EmailResult(False, "Invalid email", 400)

        # Traer invoice y chequear ownership
        invoice = get_object_or_404(Invoice, id=invoice_id, user=user, invoice_type="sale")

        subject = _render_subject(invoice)
        text_body, html_body = _render_bodies(invoice, user)

        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@budsidesk.com")
        msg = EmailMultiAlternatives(subject, text_body, from_email, [to_email])
        msg.attach_alternative(html_body, "text/html")

        # Adjuntar archivo original (si existe)
        _attach_original_if_any(msg, invoice)

        # (Opcional) si quieres marcar algo al enviar
        invoice.last_emailed_at = timezone.now() if hasattr(invoice, "last_emailed_at") else None
        try:
            if invoice.last_emailed_at:
                invoice.save(update_fields=["last_emailed_at"])
        except Exception:
            pass

        msg.send()
        return EmailResult(True, f"Invoice sent to {to_email}")

    except Exception as e:
        return EmailResult(False, f"{type(e).__name__}: {e}", 400)



### Estructura cuando implementes email
#class EmailProvider(ABC):
 #   def send_invoice(self, invoice, to_email): pass

#class InvoiceEmailService:
#    def __init__(self, provider: EmailProvider):
#        self.provider = provider
    
#    def send_invoice(self, invoice_id, to_email):
        # 1. Render template con datos invoice
        # 2. Llamar provider.send()
        # 3. Log en EmailMessageLog
        # 4. Actualizar invoice.sent_at
 #       pass
### 
#En views.py - Delgado
#def send_invoice_email_view(request, invoice_id):
#    service = InvoiceEmailService(PostmarkProvider())
#    result = service.send_invoice(invoice_id, request.POST['email'])
#    return JsonResponse(result)