# logic/plan_tiers.py
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden

# Ajusta esto a tu modelo real: tu User tiene "plan" (default smart) :contentReference[oaicite:1]{index=1}
def has_feature(user, feature_name: str) -> bool:
    # Implementación provisional: permite todo en dev
    if not user or not getattr(user, "is_authenticated", False):
        return False
    return True

def _require_plan(allowed_plans):
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            plan = getattr(request.user, "plan", None)
            if plan in allowed_plans or getattr(request.user, "is_superuser", False):
                return view_func(request, *args, **kwargs)
            return HttpResponseForbidden("Plan not allowed")
        return _wrapped
    return decorator

smart_required = _require_plan({"smart", "elite", "admin"})
elite_required = _require_plan({"elite", "admin"})

