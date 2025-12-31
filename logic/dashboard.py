# logic/dashboard.py - VERSIÓN CORREGIDA
from __future__ import annotations
from typing import Dict, Any, List
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

PALETTE = [
    "#4B49AC", "#98BDFF", "#7DA0FA", "#7978E9", "#F3797E",
    "#f39c12", "#2ecc71", "#1abc9c", "#9b59b6", "#e74c3c"
]

def monthly_income(user, year: int) -> List[Dict[str, Any]]:
    from budsi_database.models import Invoice
    try:
        # ✅ VENTAS = Todo lo que NO sea purchase
        qs = (Invoice.objects
              .filter(user=user, date__year=year, is_credit_note=False)
              .exclude(invoice_type='purchase')  # ← CRÍTICO: Excluir compras
              .annotate(m=TruncMonth("date"))
              .values("m").annotate(total=Sum("total")).order_by("m"))
        return [{"month": r["m"].strftime("%b"), "total": float(r["total"] or 0)} for r in qs]
    except Exception:
        return []

def revenue_vs_expenses(user, year: int) -> Dict[str, float]:
    from budsi_database.models import Invoice
    try:
        # ✅ VENTAS = Excluir purchases
        sales = (Invoice.objects
                 .filter(user=user, date__year=year, is_credit_note=False)
                 .exclude(invoice_type='purchase')
                 .aggregate(s=Sum("total"))["s"] or 0)
        # ✅ GASTOS = Solo purchases
        purchases = (Invoice.objects
                     .filter(user=user, date__year=year, invoice_type='purchase')
                     .aggregate(s=Sum("total"))["s"] or 0)
        return {"revenue": float(sales or 0), "expenses": float(purchases or 0)}
    except Exception:
        return {"revenue": 0.0, "expenses": 0.0}

def spending_wheel(user, year: int) -> List[Dict[str, Any]]:
    from budsi_database.models import Invoice
    try:
        rows = (Invoice.objects
                .filter(user=user, invoice_type="purchase", date__year=year)
                .values("category").annotate(total=Sum("total")).order_by("-total"))
        total = float(sum((r["total"] or 0) for r in rows) or 0)
        out = []
        for i, r in enumerate(rows):
            amt = float(r["total"] or 0)
            pct = round((amt/total)*100, 2) if total else 0
            out.append({"category": r["category"] or "Uncategorized", "percentage": pct, "color": PALETTE[i % len(PALETTE)]})
        return out
    except Exception:
        return []

def annual_comparison(user, year: int) -> Dict[str, float]:
    from budsi_database.models import Invoice
    try:
        # ✅ VENTAS = Excluir purchases
        cur = (Invoice.objects
               .filter(user=user, date__year=year, is_credit_note=False)
               .exclude(invoice_type='purchase')
               .aggregate(s=Sum("total"))["s"] or 0)
        prev = (Invoice.objects
                .filter(user=user, date__year=year-1, is_credit_note=False)
                .exclude(invoice_type='purchase')
                .aggregate(s=Sum("total"))["s"] or 0)
        return {"current_year": float(cur or 0), "previous_year": float(prev or 0)}
    except Exception:
        return {"current_year": 0.0, "previous_year": 0.0}

def tax_data(user, year: int) -> Dict[str, Any]:
    """
    ✅ VAT liability robusto - Si calculate_taxes falla, calcula desde BD
    """
    try:
        from logic.tax_calculator import calculate_taxes
        # Intenta con la firma (user, year) primero
        try:
            data = calculate_taxes(user=user, year=year)
        except TypeError:
            # Fallback: usar facturas reales
            from budsi_database.models import Invoice
            sales_invoices = Invoice.objects.filter(
                user=user, date__year=year, is_credit_note=False
            ).exclude(invoice_type='purchase')
            purchase_invoices = Invoice.objects.filter(
                user=user, date__year=year, invoice_type='purchase'
            )
            data = calculate_taxes(sales_invoices, purchase_invoices)
        
        return {
            "vat": {"liability": float(data.get("vat", {}).get("liability", 0))},
            "income_tax": {"net": float(data.get("income_tax", {}).get("net", 0))},
            "usc": {"total": float(data.get("usc", {}).get("total", 0))},
            "prsi": float(data.get("prsi", 0)),
        }
    except Exception:
        # ✅ FALLBACK: Calcular VAT desde BD directamente
        from budsi_database.models import Invoice
        from decimal import Decimal
        
        sales_qs = Invoice.objects.filter(
            user=user, date__year=year, is_credit_note=False
        ).exclude(invoice_type='purchase')
        
        try:
            # 1. Intentar usar vat_amount si existe
            vat_collected = sales_qs.aggregate(s=Sum('vat_amount'))['s'] or Decimal('0')
            if vat_collected == 0:
                # 2. Estimar 23% del total de ventas
                total_sales = sales_qs.aggregate(s=Sum('total'))['s'] or Decimal('0')
                vat_collected = total_sales * Decimal('0.23')
        except Exception:
            vat_collected = Decimal('0')
        
        return {
            "vat": {"liability": float(vat_collected)},
            "income_tax": {"net": 0.0},
            "usc": {"total": 0.0},
            "prsi": 0.0,
        }

def get_dashboard_context(user, year: int | None = None) -> Dict[str, Any]:
    if not year:
        year = timezone.localtime().year
    return {
        "monthly_income": monthly_income(user, year),
        "revenue_expenses": revenue_vs_expenses(user, year),
        "spending_data": spending_wheel(user, year),
        "annual_comparison": annual_comparison(user, year),
        "tax_data": tax_data(user, year),
        "current_year": year,
        "previous_year": year - 1,
        "smart_reminders": [],
    }

@login_required
def dashboard_page(request):
    """Vista real del dashboard"""
    year = request.GET.get('year', timezone.localtime().year)
    try:
        year = int(year)
    except (TypeError, ValueError):
        year = timezone.localtime().year
    
    context = get_dashboard_context(request.user, year)
    return render(request, 'budsidesk_app/dashboard.html', context)