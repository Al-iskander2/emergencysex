# logic/email_invoice.py

 # tu motor real

def send_invoice_reminder(user, invoice_id: int, to_email: str) -> EmailResult:
    """
    Wrapper pequeñito que deja claro que esto viene de Pulse / reminder.
    """
    return send_invoice_email(
        user=user,
        invoice_id=invoice_id,
        to_email=to_email,
        mode="reminder",
    )
