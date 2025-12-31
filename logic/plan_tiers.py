# logic/plan_tiers.py
from functools import wraps
from django.shortcuts import redirect
from logic.monitoring.monitoring import get_trial_status

PLAN_TIERS = {
    'lite': 0,
    'smart': 1, 
    'elite': 2,
    'admin': 3,
}

FEATURE_MATRIX = {
    # Dashboard Features
    "spending_wheel": "smart",
    "advanced_dashboard": "smart",
    "buzz_module": "elite",  # CAMBIADO: solo Elite tiene Buzz
    
    # Module Access
    "pulse_module": "smart",
    "docs_module": "smart",
    "track_module": "smart", 
    "budsiwhiz_module": "smart",
    
    # Invoice Features
    "unlimited_invoices": "smart",
    "favorite_customers": "elite",  # CAMBIADO: solo Elite tiene Favorites
    "mark_paid": "smart",
    "invoice_logo": "elite",
    "invoice_projects": "elite",
    "recurring_invoices": "elite",
    
    # Expense Features  
    "expense_categories": "smart",
    "expense_projects": "elite",
    "expense_basic_upload": "lite",
    
    # Report Features
    "advanced_reports": "elite",
    "vat_reports": "smart",
    "full_tax_report": "elite",
    "tax_report_basic": "lite",
    
    # Pulse Advanced Features
    "pulse_advanced": "smart",
    "download_reports": "elite",
    "send_reminders": "elite",
    "pulse_basic_reports": "smart",
    
    # Track Advanced Features
    "track_analytics": "elite",
    "track_calendar": "smart",
    "track_basic": "smart",
    "track_advanced": "elite",
    
    # Docs Features
    "docs_limited_templates": "smart",  # 2 templates
    "docs_full_templates": "elite",     # 5 templates
    
    # BudsiWhiz Features
    "budsiwhiz_access": "smart",
    
    # HelpDesk Features
    "helpdesk_whatsapp": "elite",
    "helpdesk_priority_email": "smart", 
    "helpdesk_basic_email": "lite",
}

def get_effective_plan(user):
    """Determina plan REAL considerando trials"""
    if not user or not user.is_authenticated:
        return "lite"
    
    # Si es Smart y tiene trial activo → trata como Smart
    if user.plan == 'smart' and get_trial_status(user):
        return 'smart'
    # Si es Smart pero trial expirado → trata como Lite
    elif user.plan == 'smart' and not get_trial_status(user):
        return 'lite'
    # Otros casos
    else:
        return user.plan

def has_feature(user, feature_code):
    """Verifica si usuario tiene acceso a una feature específica"""
    if not user or not user.is_authenticated:
        return False
        
    # Admin tiene acceso a todo
    if user.plan == 'admin':
        return True
        
    effective_plan = get_effective_plan(user)
    user_level = PLAN_TIERS.get(effective_plan, 0)
    required_plan = FEATURE_MATRIX.get(feature_code, "elite")
    required_level = PLAN_TIERS.get(required_plan, 0)
    
    return user_level >= required_level

# Decoradores para views
def require_plan(required_plan):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
                
            effective_plan = get_effective_plan(request.user)
            user_level = PLAN_TIERS.get(effective_plan, 0)
            required_level = PLAN_TIERS.get(required_plan, 1)
            
            if user_level < required_level:
                return redirect('pricing')
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def smart_required(view_func):
    """Requiere plan Smart o superior"""
    return require_plan("smart")(view_func)

def elite_required(view_func):
    """Requiere plan Elite o superior""" 
    return require_plan("elite")(view_func)

def lite_required(view_func):
    """Requiere al menos plan Lite (cualquier usuario autenticado)"""
    return require_plan("lite")(view_func)

# Funciones helper para características específicas
def can_access_buzz(user):
    """Verifica si usuario puede acceder al módulo Buzz"""
    return has_feature(user, "buzz_module")

def can_access_favorite_customers(user):
    """Verifica si usuario puede usar Favorite Customers"""
    return has_feature(user, "favorite_customers")

def can_use_invoice_projects(user):
    """Verifica si usuario puede vincular facturas con proyectos"""
    return has_feature(user, "invoice_projects")

def can_download_reports(user):
    """Verifica si usuario puede descargar reportes PDF"""
    return has_feature(user, "download_reports")

def get_available_doc_templates(user):
    """Retorna número de templates de documentos disponibles"""
    if has_feature(user, "docs_full_templates"):
        return 5  # Elite: 5 templates
    elif has_feature(user, "docs_limited_templates"):
        return 2  # Smart: 2 templates
    else:
        return 0  # Lite: 0 templates

def get_helpdesk_options(user):
    """Retorna opciones de helpdesk disponibles"""
    options = []
    if has_feature(user, "helpdesk_basic_email"):
        options.append("basic_email")
    if has_feature(user, "helpdesk_priority_email"):
        options.append("priority_email") 
    if has_feature(user, "helpdesk_whatsapp"):
        options.append("whatsapp")
    return options