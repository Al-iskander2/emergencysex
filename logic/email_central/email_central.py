# logic/email_central/email_central.py

from typing import Optional
from logic.send_email import send_invoice_email, EmailResult
from .email_pulse import send_aged_debtors_email
from .email_docs import send_legal_document_email


def email_action(user, action: str, to_email: str, target_id: Optional[str] = None) -> EmailResult:
    """
    Punto central único para todas las acciones de email.
    NO contiene texto de emails, solo decide a qué módulo delegar.
    """

    # 1) FACTURAS (visualize_invoice, Pulse, etc.)
    if action == "invoice_send":
        if not target_id:
            return EmailResult(False, "Invoice ID is required")
        return send_invoice_email(
            user=user,
            invoice_id=int(target_id),
            to_email=to_email,
            mode="invoice",   # o el que uses por defecto
        )

    if action == "invoice_reminder":
        if not target_id:
            return EmailResult(False, "Invoice ID is required")
        return send_invoice_email(
            user=user,
            invoice_id=int(target_id),
            to_email=to_email,
            mode="reminder",
        )

    # 2) PULSE – AGED DEBTORS
    if action == "pulse_aged_debtors":
        return send_aged_debtors_email(
            user=user,
            to_email=to_email,
        )

    # 3) DOCUMENTOS LEGALES (caso simple desde modal)
    if action == "doc_non_disclosure":
        return send_legal_document_email(
            user=user,
            doc_type="non_disclosure",
            to_email=to_email,
        )

    if action == "doc_service_agreement":
        return send_legal_document_email(
            user=user,
            doc_type="service_agreement",
            to_email=to_email,
        )

    if action == "doc_project_proposal":
        return send_legal_document_email(
            user=user,
            doc_type="project_proposal",
            to_email=to_email,
        )

    if action == "doc_statement_of_work":
        return send_legal_document_email(
            user=user,
            doc_type="sow",
            to_email=to_email,
        )

    # Si la acción no existe:
    return EmailResult(False, f"Unknown email action: {action}")
