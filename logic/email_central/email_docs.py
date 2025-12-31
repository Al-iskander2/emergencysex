import logging
from pathlib import Path

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

logger = logging.getLogger(__name__)


def send_legal_document_email(
    user,
    doc_type: str,
    to_email: str,
    contact_name: str = "Customer",
    context: dict = None,
) -> bool:
    """
    Enviar documento legal por email.

    • Genera el PDF usando docs_master
    • Construye subject y cuerpo (texto + HTML)
    • Adjunta el PDF y lo envía
    """

    try:
        # 1) Generar el PDF usando tu sistema existente
        pdf_path = _generate_legal_doc_pdf(user, doc_type, context or {})
        if not pdf_path or not pdf_path.exists():
            logger.error(f"❌ No se pudo generar PDF para {doc_type}")
            return False

        # 2) Construir contenido del email
        doc_name = _get_document_display_name(doc_type)
        business_name = _get_business_name(user)

        subject = f"{doc_name} from {business_name}"

        body_text = f"""Hi {contact_name},

Please find attached your {doc_name.lower()} document.

Best regards,
{business_name}
"""

        body_html = f"""
        <p>Hi {contact_name},</p>
        <p>Please find attached your <strong>{doc_name.lower()}</strong> document.</p>
        <p>Best regards,<br>{business_name}</p>
        """

        # 3) Preparar remitente y reply-to
        user_email = getattr(user, "email", None)
        default_from = getattr(settings, "DEFAULT_FROM_EMAIL", None)

        from_email = default_from or user_email
        reply_to = [user_email] if user_email else None

        # 4) Construir mensaje con adjunto
        msg = EmailMultiAlternatives(
            subject=subject,
            body=body_text,
            from_email=from_email,
            to=[to_email],
            reply_to=reply_to,
        )

        # HTML alternativo
        if body_html:
            msg.attach_alternative(body_html, "text/html")

        # Adjuntar PDF
        if pdf_path and pdf_path.exists():
            msg.attach(
                pdf_path.name,
                pdf_path.read_bytes(),
                "application/pdf",
            )

        # 5) Enviar
        msg.send()
        logger.info(f"✅ Legal document '{doc_type}' sent to {to_email}")
        return True

    except Exception as e:
        logger.error(f"❌ Error enviando documento legal {doc_type}: {e}")
        return False


def _generate_legal_doc_pdf(user, doc_type: str, context: dict) -> Path:
    """Usar tu sistema docs_master para generar PDF"""
    try:
        from logic.docs_master import generate_legal_document
        return generate_legal_document(doc_type, context or {}, user.id)
    except Exception as e:
        logger.error(f"❌ Error generando PDF para {doc_type}: {e}")
        return None


def _get_document_display_name(doc_type: str) -> str:
    """Obtener nombre legible del tipo de documento"""
    names = {
        "non_disclosure": "Non-Disclosure Agreement (NDA)",
        "service_agreement": "Service Agreement",
        "timesheet": "Timesheet",
        "quotation": "Project Proposal",
        "sow": "Statement of Work",
    }
    return names.get(doc_type, doc_type.replace("_", " ").title())


def _get_business_name(user) -> str:
    """Obtener nombre del negocio del usuario"""
    try:
        if hasattr(user, "fiscal_profile") and user.fiscal_profile.business_name:
            return user.fiscal_profile.business_name
        elif hasattr(user, "fiscal_profile") and user.fiscal_profile.legal_name:
            return user.fiscal_profile.legal_name
        else:
            return user.email or "Your Business"
    except Exception:
        return "Your Business"
