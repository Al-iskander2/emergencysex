# logic/email_central/email_pulse.py

from django.core.mail import send_mail
from django.conf import settings
from logic.send_email import EmailResult


def send_aged_debtors_email(user, to_email: str) -> EmailResult:
    """
    Email propio de Pulse: reporte de aged debtors.
    Aquí va el TEXTO “Pulse”, más suave, más overview.
    """

    subject = "Aged Debtors – Overview"

    body_text = f"""Hi there! Hope you’re doing great,

Just a quick heads-up — it looks like some invoices are still outstanding.
No worries at all if it just slipped through!

If they’re already settled, please ignore this message.
If not, whenever you get a moment, we’d really appreciate you taking a look.

Sender: {user.email or "BudsiDesk user"}

Thanks so much!
"""

    try:
        send_mail(
            subject=subject,
            message=body_text,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[to_email],
            fail_silently=False,
        )
        return EmailResult(True, f"Aged debtors email sent to {to_email}")
    except Exception as e:
        print(f"❌ Error sending aged debtors email: {e}")
        return EmailResult(False, "Failed to send aged debtors email")
