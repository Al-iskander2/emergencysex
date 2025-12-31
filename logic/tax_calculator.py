# logic/tax_calculator.py
from decimal import Decimal
from datetime import datetime, timedelta
from django.db.models import Sum, Count, Q
from budsi_database.models import Invoice

def calculate_taxes(sales_invoices, purchase_invoices, tax_credits=None):
    """
    ✅ CORREGIDO: Acepta tax_credits como parámetro
    ✅ CORREGIDO: Usa NETOS (sin IVA) para cálculos de impuestos sobre renta
    ✅ CORREGIDO: Tax Credits por defecto €2,000
    """
    # ✅ Configurar tax_credits (parámetro o por defecto)
    if tax_credits is None:
        TAX_CREDITS = Decimal('2000')
    else:
        TAX_CREDITS = Decimal(tax_credits)
    
    INCOME_TAX_BRACKETS = [(Decimal('44000'), Decimal('0.20')), (Decimal('9999999'), Decimal('0.40'))]
    USC_BANDS = [
        (Decimal('0'), Decimal('12012'), Decimal('0.005')),
        (Decimal('12012'), Decimal('25760'), Decimal('0.02')),
        (Decimal('25760'), Decimal('70044'), Decimal('0.045')),
        (Decimal('70044'), Decimal('9999999'), Decimal('0.08'))
    ]

    # ✅ CALCULAR NETOS (sin IVA) para impuestos sobre renta
    sales_net = sum(inv.subtotal for inv in sales_invoices) if sales_invoices else Decimal('0')
    purchases_net = sum(inv.subtotal for inv in purchase_invoices) if purchase_invoices else Decimal('0')
    
    # ✅ CALCULAR IVA POR SEPARADO
    vat_collected = sum(inv.vat_amount for inv in sales_invoices) if sales_invoices else Decimal('0')
    vat_paid = sum(inv.vat_amount for inv in purchase_invoices) if purchase_invoices else Decimal('0')
    
    # ✅ CALCULAR TOTALES (con IVA) solo para display
    gross_income = sales_net + vat_collected  # Para compatibilidad
    expenses = purchases_net + vat_paid       # Para compatibilidad
    
    vat_liability = vat_collected - vat_paid
    
    # ✅ BASE IMPONIBLE CORRECTA: Neto Ventas - Neto Compras (sin IVA)
    taxable_income = sales_net - purchases_net

    # Income tax calculation
    income_tax = Decimal('0')
    remaining_income = taxable_income
    for bracket, rate in INCOME_TAX_BRACKETS:
        if remaining_income <= Decimal('0'):
            break
        amount = min(remaining_income, bracket)
        income_tax += amount * rate
        remaining_income -= amount
    
    net_income_tax = max(Decimal('0'), income_tax - TAX_CREDITS)

    # USC calculation
    usc = Decimal('0')
    remaining_income = taxable_income
    usc_breakdown = []
    for lower, upper, rate in USC_BANDS:
        if remaining_income <= Decimal('0'):
            break
        band_amount = min(remaining_income, upper - lower)
        band_tax = band_amount * rate
        usc += band_tax
        usc_breakdown.append({
            'band': f"€{lower:,.2f} - €{upper:,.2f}",
            'rate': f"{rate*100}%",
            'amount': float(band_amount),
            'tax': float(band_tax)
        })
        remaining_income -= band_amount

    # PRSI calculation (sobre base neta)
    prsi = max(Decimal('0'), taxable_income) * Decimal('0.04')
    total_tax = net_income_tax + usc + prsi

    return {
        'vat': {
            'collected': float(vat_collected),
            'paid': float(vat_paid),
            'liability': float(vat_liability)
        },
        'income': {
            'gross': float(gross_income),           # Para compatibilidad
            'gross_sales': float(gross_income),     # Total con IVA
            'gross_purchases': float(expenses),     # Total con IVA
            'net_sales': float(sales_net),          # ✅ NUEVO: Subtotal sin IVA
            'net_purchases': float(purchases_net),  # ✅ NUEVO: Subtotal sin IVA
            'expenses': float(expenses),            # Para compatibilidad
            'taxable': float(taxable_income),       # ✅ CORREGIDO: Base neta
            'taxable_income': float(taxable_income) # Alias para template
        },
        'income_tax': {
            'gross': float(income_tax),
            'tax_credits': float(TAX_CREDITS),      # ✅ Cambiado de 'credits' a 'tax_credits'
            'net_tax': float(net_income_tax)        # ✅ Cambiado de 'net' a 'net_tax'
        },
        'usc': {
            'total': float(usc),
            'breakdown': usc_breakdown
        },
        'prsi': {
            'tax': float(prsi)                      # ✅ Estructura consistente
        },
        'total_tax': float(total_tax)
    }
# ============================================================================
# NUEVAS FUNCIONES DE REPORTES FINANCIEROS (integradas aquí)
# ============================================================================

def get_cash_flow_report(user, start_date=None, end_date=None):
    """Reporte detallado de flujo de caja"""
    if not start_date:
        start_date = datetime.now().date() - timedelta(days=30)
    if not end_date:
        end_date = datetime.now().date()
    
    # Ingresos (ventas pagadas)
    income = Invoice.objects.filter(
        user=user,
        invoice_type="sale",
        is_confirmed=True,
        status="paid",
        payment_date__range=[start_date, end_date]
    ).aggregate(total=Sum('total'))['total'] or Decimal('0')
    
    # Gastos (compras confirmadas)
    expenses = Invoice.objects.filter(
        user=user,
        invoice_type="purchase", 
        is_confirmed=True,
        date__range=[start_date, end_date]
    ).aggregate(total=Sum('total'))['total'] or Decimal('0')
    
    # Cuentas por cobrar
    accounts_receivable = Invoice.objects.filter(
        user=user,
        invoice_type="sale",
        is_confirmed=True,
        status__in=["sent", "overdue"]
    ).aggregate(total=Sum('total'))['total'] or Decimal('0')
    
    return {
        'period': {
            'start_date': start_date,
            'end_date': end_date
        },
        'income': float(income),
        'expenses': float(expenses),
        'net_cash_flow': float(income - expenses),
        'accounts_receivable': float(accounts_receivable),
        'cash_balance': float(income - expenses)
    }

def get_income_statement(user, year=None):
    """Estado de resultados (Profit & Loss)"""
    if not year:
        year = datetime.now().year
    
    start_date = datetime(year, 1, 1).date()
    end_date = datetime(year, 12, 31).date()
    
    # Ingresos
    revenue = Invoice.objects.filter(
        user=user,
        invoice_type="sale",
        is_confirmed=True,
        date__range=[start_date, end_date]
    ).aggregate(total=Sum('total'))['total'] or Decimal('0')
    
    # Costos (gastos directos)
    cogs = Invoice.objects.filter(
        user=user,
        invoice_type="purchase",
        is_confirmed=True,
        date__range=[start_date, end_date]
    ).aggregate(total=Sum('total'))['total'] or Decimal('0')
    
    gross_profit = revenue - cogs
    gross_margin = (gross_profit / revenue * 100) if revenue > 0 else Decimal('0')
    
    return {
        'year': year,
        'revenue': float(revenue),
        'cost_of_goods_sold': float(cogs),
        'gross_profit': float(gross_profit),
        'gross_margin': float(gross_margin),
        'net_income': float(gross_profit)  # Por ahora igual a gross profit
    }

def get_aging_report(user):
    """Reporte de antigüedad de cuentas por cobrar"""
    from django.utils import timezone
    
    today = timezone.now().date()
    aging_buckets = {
        'current': Decimal('0'),
        '1_30': Decimal('0'),
        '31_60': Decimal('0'), 
        '61_90': Decimal('0'),
        'over_90': Decimal('0')
    }
    
    overdue_invoices = Invoice.objects.filter(
        user=user,
        invoice_type="sale",
        is_confirmed=True,
        status__in=["sent", "overdue"]
    )
    
    for invoice in overdue_invoices:
        if not invoice.due_date:
            continue
            
        days_overdue = (today - invoice.due_date).days
        
        if days_overdue <= 0:
            aging_buckets['current'] += invoice.total
        elif days_overdue <= 30:
            aging_buckets['1_30'] += invoice.total
        elif days_overdue <= 60:
            aging_buckets['31_60'] += invoice.total
        elif days_overdue <= 90:
            aging_buckets['61_90'] += invoice.total
        else:
            aging_buckets['over_90'] += invoice.total
    
    # Convertir a float para JSON
    return {key: float(value) for key, value in aging_buckets.items()}