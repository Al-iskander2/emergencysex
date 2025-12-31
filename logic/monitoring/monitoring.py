# logic/monitoring/monitoring.py (VERSIÓN SIN trial_ended)
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

def check_expired_trials():
    """
    Versión SIN trial_ended - usa solo date_joined y plan
    """
    try:
        cutoff_date = timezone.now() - timedelta(days=30)
        
        # Usuarios Smart registrados hace más de 30 días
        expired_users = User.objects.filter(
            plan='smart',
            date_joined__lt=cutoff_date
        )
        
        count = expired_users.count()
        
        if count > 0:
            for user in expired_users:
                user.plan = 'lite'
                user.save()
                logger.info(f"🔄 Trial expirado: {user.email} -> Plan Lite")
            
            logger.info(f"✅ {count} usuarios actualizados de Smart a Lite")
            return f"{count} usuarios actualizados a Lite"
        else:
            logger.info("✅ No hay trials expirados hoy")
            return "No hay trials expirados hoy"
            
    except Exception as e:
        logger.error(f"❌ Error en check_expired_trials: {e}")
        return f"Error: {e}"

def get_trial_status(user):
    """
    Determina trial activo basado solo en date_joined
    """
    if user.plan != 'smart':
        return False
    
    trial_end_date = user.date_joined + timedelta(days=30)
    return timezone.now() < trial_end_date

def get_days_remaining(user):
    """
    Días restantes de trial
    """
    if user.plan != 'smart':
        return 0
    
    trial_end_date = user.date_joined + timedelta(days=30)
    remaining = trial_end_date - timezone.now()
    return max(0, remaining.days)