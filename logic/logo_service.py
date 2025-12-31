# logic/logo_service.py
"""
Servicio para unificar el manejo de logos SIN cambiar estructura existente.
Funciones parche para corregir flujos inconsistentes del logo.
"""
from budsi_database.models import FiscalProfile

def get_user_fiscal_profile(user):
    """
    Obtiene el FiscalProfile del usuario (igual que tu función existente).
    Se mantiene por compatibilidad.
    """
    try:
        return FiscalProfile.objects.get(user=user)
    except FiscalProfile.DoesNotExist:
        return None

def get_branding_context(user):
    """
    CONTEXTO PARCHE: Para vistas que NO están pasando el profile correctamente.
    Útil para visualize_invoice, visualize_docs, etc.
    """
    profile = get_user_fiscal_profile(user)
    
    return {
        "profile": profile,  # Para templates existentes que usan {{ profile.logo }}
        "has_logo": bool(profile and profile.logo),
        "display_name": get_display_name(profile),
    }

def get_display_name(profile):
    """Nombre para mostrar (business_name > legal_name > None)"""
    if not profile:
        return None
    return profile.business_name or profile.legal_name or None

def inject_logo_context(context, user):
    """
    INYECTOR PARCHE: Añade variables de logo a un contexto existente.
    Perfecto para vistas que ya tienen su propio contexto pero falta el logo.
    """
    branding = get_branding_context(user)
    return {**context, **branding}

def safe_get_logo_url(user):
    """
    Obtiene la URL del logo de forma segura, con fallback a None.
    Útil para emails, APIs, o donde solo necesitas la URL.
    """
    profile = get_user_fiscal_profile(user)
    if profile and profile.logo:
        return profile.logo.url
    return None

def validate_logo_size(file_obj, max_size_mb=2):
    """Validación simple de tamaño (parche opcional para subidas)"""
    return file_obj.size <= max_size_mb * 1024 * 1024

# NOTA: NO reemplazamos update_logo/remove_logo porque ya los tienes 
# en account_settings.py y funcionan bien. Este servicio es SOLO lectura/contexto.