# logic/stripe.py - VERSIÓN COMPLETA
import json
import stripe
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages

stripe.api_key = settings.STRIPE_SECRET_KEY

@csrf_exempt
@login_required
def process_payment_view(request):
    if request.method == "POST":
        plan_code = request.GET.get("plan", "smart_monthly")
        user = request.user
        if "elite" in plan_code:
            user.plan = "elite"
        elif "smart" in plan_code:
            user.plan = "smart"
        else:
            user.plan = "lite"
        user.save()
        return redirect("dashboard")
    return redirect("checkout")

@login_required
def pricing_view(request):
    return render(request, "emergency_app/pricing.html")

@csrf_exempt
@login_required
def create_payment_intent_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    data = json.loads(request.body)
    amount = data.get("amount", 0)
    plan_code = data.get("plan_code")

    try:
        intent = stripe.PaymentIntent.create(
            amount=amount,
            currency="eur",
            metadata={"plan_code": plan_code, "user_id": request.user.id}
        )

        if plan_code and isinstance(plan_code, str):
            if plan_code.startswith("smart"):
                request.user.plan = "smart"
            elif plan_code.startswith("elite"):
                request.user.plan = "elite"
            else:
                request.user.plan = "lite"
            request.user.save()

        return JsonResponse({"clientSecret": intent.client_secret})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

@login_required
def payment_page(request):
    plan_code = request.GET.get("plan", "smart_monthly")
    plan_map = {
        "smart_monthly": {"name": "emerg Smart", "amount": 1299, "interval": "month"},
        "smart_yearly": {"name": "emerg Smart", "amount": 12900, "interval": "year"},
        "elite_monthly": {"name": "emerg Elite", "amount": 1799, "interval": "month"},
        "elite_yearly": {"name": "emerg Elite", "amount": 17900, "interval": "year"},
    }
    plan_info = plan_map.get(plan_code)

    if not plan_info:
        return redirect("pricing")

    return render(request, "emergency_app/payment.html", {
        "plan_code": plan_code,
        "name": plan_info["name"],
        "amount": plan_info["amount"],
        "interval": plan_info["interval"],
        "STRIPE_PUBLIC_KEY": settings.STRIPE_PUBLIC_KEY,
    })

# Función auxiliar para compatibilidad
def create_payment_intent(amount_cents, currency="eur", metadata=None):
    return stripe.PaymentIntent.create(
        amount=amount_cents,
        currency=currency,
        metadata=metadata or {}
    )