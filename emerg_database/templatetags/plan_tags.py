# emerg_database/templatetags/plan_tags.py
from django import template
from logic.plan_tiers import has_feature

register = template.Library()

@register.filter
def feature_available(user, feature_code):
    return has_feature(user, feature_code)

@register.filter
def invoice_limits(user):
    """Filtro para obtener límites de invoices en templates"""
    from logic.invoice_limits import get_invoice_limits
    return get_invoice_limits(user)