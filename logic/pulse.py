# logic/pulse.py
from __future__ import annotations
from datetime import timedelta
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q
from django.shortcuts import render
from django.utils import timezone

from budsi_database.models import Invoice, FiscalProfile
from logic.expenses import get_cash_out_for_period

# Categorías predefinidas
PREDEFINED_CATEGORIES = [
    "Office",
    "Equipment", 
    "Travel",
    "Marketing",
    "Development",
    "Communication",
    "Financial",
    "Payment Fees",
    "Insurance",
    "Miscellaneous"
]

# Helpers
def _period_dates(request):
    """Últimos N días (default 30)"""
    try:
        days = int(request.GET.get("period_days", "30"))
    except Exception:
        days = 30
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)
    return start_date, end_date, days

def _fmt_period_label(start_date, end_date):
    return f"{start_date.strftime('%d %b %Y')} – {end_date.strftime('%d %b %Y')}"

def _get_profile(user):
    try:
        return FiscalProfile.objects.get(user=user)
    except FiscalProfile.DoesNotExist:
        return None

def _cash_in_out(user, start_date, end_date):
    """
    Cash In = facturas de venta CONFIRMADAS, excluyendo credit notes
    Cash Out = facturas de compra CONFIRMADAS (no necesariamente pagadas)
    """
    # Ventas confirmadas (no purchase, no credit_note)
    sales_confirmed = (
        Invoice.objects
        .filter(
            user=user,
            date__range=[start_date, end_date],
            is_confirmed=True,
            is_credit_note=False
        )
        .exclude(invoice_type="purchase")
        .order_by("-date", "-id")
    )

    # Compras confirmadas (purchase) - MODIFICADO: usar is_confirmed en lugar de status="paid"
    purchases_confirmed = (
        Invoice.objects
        .filter(
            user=user,
            date__range=[start_date, end_date],
            invoice_type="purchase",
            is_confirmed=True,
        )
        .order_by("-date", "-id")
    )

    # Calcular categorías de gastos - INCLUYENDO TODAS LAS CATEGORÍAS PREDEFINIDAS
    expense_categories = []
    category_totals = {}
    
    # Inicializar todas las categorías predefinidas con 0
    for category in PREDEFINED_CATEGORIES:
        category_totals[category] = Decimal('0.00')
    
    # Sumar los gastos por categoría
    for inv in purchases_confirmed:
        category = inv.category or "Miscellaneous"  # Si no tiene categoría, va a Miscellaneous
        if category in category_totals:
            category_totals[category] += inv.total
        else:
            # Si la categoría no está en las predefinidas, la agregamos a Miscellaneous
            category_totals["Miscellaneous"] += inv.total
    
    # Calcular porcentajes
    total_expenses_amount = sum(category_totals.values())
    
    # Crear la lista de categorías para el template
    for category in PREDEFINED_CATEGORIES:
        amount = category_totals[category]
        percentage = 0.0
        if total_expenses_amount > 0:
            percentage = float((amount / total_expenses_amount * 100).quantize(Decimal('0.01')))
        
        expense_categories.append({
            'name': category,
            'amount': amount,
            'percentage': percentage
        })
    
    # Listas para el template (aunque no se usen en la nueva vista, las mantenemos por compatibilidad)
    cash_in_transactions = [
        {
            "date": inv.date,
            "description": (inv.summary or inv.contact.name or "Sale"),
            "amount": inv.total,
            "method": "-",
        }
        for inv in sales_confirmed
    ]

    cash_out_transactions = [
        {
            "date": inv.date,
            "description": (inv.summary or inv.contact.name or "Purchase"),
            "amount": inv.total,
            "category": inv.category or "-",
        }
        for inv in purchases_confirmed
    ]

    # Totales
    total_income = sales_confirmed.aggregate(s=Sum("total"))["s"] or Decimal("0.00")
    total_expenses = total_expenses_amount
    net_profit = total_income - total_expenses

    return cash_in_transactions, cash_out_transactions, total_income, total_expenses, net_profit, expense_categories

def _aged_debtors(user):
    """
    Aged Debtors = cuentas por cobrar abiertas + facturas próximas a vencer
    """
    today = timezone.now().date()
    
    # Facturas de venta no pagadas y no canceladas
    open_sales = (
        Invoice.objects
        .filter(
            user=user,
            is_credit_note=False
        )
        .exclude(invoice_type="purchase")
        .exclude(status__in=["paid", "cancelled"])
        .order_by("due_date", "contact__name")
    )

    debtors = []
    totals = {
        "balance": Decimal("0.00"),
        "current": Decimal("0.00"),
        "overdue_30": Decimal("0.00"),
        "overdue_60": Decimal("0.00"),
        "overdue_90": Decimal("0.00"),
        "overdue_120": Decimal("0.00"),
    }

    for inv in open_sales:
        balance = inv.total or Decimal("0.00")
        due = inv.due_date
        
        if not due:
            continue  # Saltar facturas sin fecha de vencimiento

        days_until_due = (due - today).days
        days_overdue = -days_until_due if days_until_due < 0 else 0
        
        # Determinar estado
        if days_overdue > 0:
            status = "overdue"
            status_display = f"Overdue ({days_overdue} days)"
        elif days_until_due <= 7:
            status = "due_soon"
            status_display = f"Due in {days_until_due} days"
        elif days_until_due <= 30:
            status = "upcoming"
            status_display = f"Due in {days_until_due} days"
        else:
            status = "current"
            status_display = "On track"

        # Asignar a buckets
        current = o30 = o60 = o90 = o120 = Decimal("0.00")
        
        if days_overdue > 120:
            o120 = balance
        elif days_overdue > 90:
            o90 = balance
        elif days_overdue > 60:
            o60 = balance
        elif days_overdue > 30:
            o30 = balance
        else:
            current = balance

        debtors.append({
            "customer": inv.contact.name,
            "balance": balance,
            "current": current,
            "overdue_30": o30,
            "overdue_60": o60,
            "overdue_90": o90,
            "overdue_120": o120,
            "days_overdue": days_overdue,
            "days_until_due": days_until_due,
            "status": status,
            "status_display": status_display,
            "invoice_id": inv.id,
            "invoice_number": inv.invoice_number,
            "due_date": due,
            "contact_email": inv.contact.email,
            "can_send_reminder": days_until_due <= 30 and inv.contact.email,  # Solo enviar recordatorios para facturas próximas
        })

        totals["balance"] += balance
        totals["current"] += current
        totals["overdue_30"] += o30
        totals["overdue_60"] += o60
        totals["overdue_90"] += o90
        totals["overdue_120"] += o120

    return debtors, totals

# ============ VISTA PRINCIPAL ============

@login_required
def pulse_page(request):
    start_date, end_date, days = _period_dates(request)
    period_label = _fmt_period_label(start_date, end_date)

    profile = _get_profile(request.user)

    (
        cash_in_transactions,
        cash_out_transactions,
        total_income,
        total_expenses,
        net_profit,
        expense_categories,
    ) = _cash_in_out(request.user, start_date, end_date)

    aged_debtors, aged_debtors_total = _aged_debtors(request.user)
    aged_label = f"As of {timezone.now().date().strftime('%d %b %Y')}"

    ctx = {
        # Header
        "profile": profile,
        "period_label": period_label,

        # Col 1 (Earnings)
        "cash_in_transactions": cash_in_transactions,
        "cash_out_transactions": cash_out_transactions,
        "total_income": total_income,
        "total_expenses": total_expenses,
        "net_profit": net_profit,

        # Col 2 (Cash Flow)
        "expense_categories": expense_categories,

        # Col 3 (Aged Debtors)
        "aged_label": aged_label,
        "aged_debtors": aged_debtors,
        "aged_debtors_total": aged_debtors_total,
    }

    return render(request, "budsidesk_app/dash/pulse/main_pulse.html", ctx)


def get_cash_in_for_period(user, days: int = 30):
    """
    Devuelve (queryset, total) de ingresos (CASH IN) para Pulse.
    """
    today = timezone.now().date()
    start_date = today - timedelta(days=days)

    qs = (
        Invoice.objects
        .filter(
            user=user,
            invoice_type="sale",              # ✅ ventas
            date__range=(start_date, today),
        )
        .select_related("contact")
        .order_by("-date", "-id")
    )

    total = qs.aggregate(total=Sum("total"))["total"] or Decimal("0.00")
    return qs, total