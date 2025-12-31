# logic/invoice_limits.py
from budsi_database.models import Invoice
from logic.plan_tiers import has_feature


def _sales_qs(user):
    return Invoice.objects.filter(user=user, invoice_type="sale")


def _credit_qs(user):
    return Invoice.objects.filter(user=user, invoice_type="credit_note")


def can_create_invoice(user, is_credit_note=False):
    """
    Returns True if the user can create a new invoice/credit note
    """
    if not user or not user.is_authenticated:
        return False

    # Smart/Elite (or Smart on trial) have unlimited invoices
    if has_feature(user, "unlimited_invoices"):
        return True

    # Lite (or Smart with expired trial): maximum 3 invoices + 3 credit notes
    if is_credit_note:
        count = _credit_qs(user).count()
        return count < 3
    else:
        count = _sales_qs(user).count()
        return count < 3


def get_invoice_limits(user):
    """
    Returns information about the current invoice limits
    """
    if not user or not user.is_authenticated:
        return {
            "limit_reached": True,
            "message": "Log in to create invoices",
            "current_invoices": 0,
            "current_credit_notes": 0,
            "max_invoices": 0,
            "max_credit_notes": 0,
        }

    if has_feature(user, "unlimited_invoices"):
        return {
            "limit_reached": False,
            "message": "Unlimited invoices",
            "current_invoices": _sales_qs(user).count(),
            "current_credit_notes": _credit_qs(user).count(),
            "max_invoices": "∞",
            "max_credit_notes": "∞",
        }

    current_invoices = _sales_qs(user).count()
    current_credit_notes = _credit_qs(user).count()

    return {
        "limit_reached": current_invoices >= 3 or current_credit_notes >= 3,
        "message": f"{current_invoices}/3 invoices, {current_credit_notes}/3 credit notes",
        "current_invoices": current_invoices,
        "current_credit_notes": current_credit_notes,
        "max_invoices": 3,
        "max_credit_notes": 3,
    }
