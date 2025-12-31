# budsi_django/views/tax_report.py
from decimal import Decimal
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from datetime import datetime
from django.db.models import Sum
from budsi_database.models import Invoice
from logic.tax_calculator import calculate_taxes

def _get_year(request):
    """Helper para obtener año de request"""
    y = request.GET.get("year")
    try:
        return int(y) if y else datetime.now().year
    except (TypeError, ValueError):
        return datetime.now().year

def tax_report_view(request, year=None):
    if year is None:
        year = datetime.now().year
    
    user = request.user
    sales_invoices = Invoice.objects.filter(
        user=user, 
        date__year=year, 
        is_credit_note=False
    ).exclude(invoice_type='purchase')
    
    purchase_invoices = Invoice.objects.filter(
        user=user, 
        date__year=year, 
        invoice_type='purchase'
    )
    
    # Usar firma correcta directamente
    tax_data = calculate_taxes(sales_invoices, purchase_invoices, tax_credits=Decimal('2000'))
    
    context = {
        'tax_data': tax_data,
        'year': year,
        'sales_invoices': sales_invoices,
        'purchase_invoices': purchase_invoices,
    }
    
    return render(request, 'budsidesk_app/dash/tax_report/tax_report.html', context)

@login_required
def tax_report_by_year_view(request, year):
    """✅ Reporte de impuestos por año específico - CORREGIDO"""
    try:
        user = request.user
        sales_invoices = Invoice.objects.filter(
            user=user, 
            date__year=year, 
            is_credit_note=False
        ).exclude(invoice_type='purchase')
        
        purchase_invoices = Invoice.objects.filter(
            user=user, 
            date__year=year, 
            invoice_type='purchase'
        )

        # ✅ LLAMADA CORRECTA - usa la misma firma que tax_report_view
        tax_data = calculate_taxes(sales_invoices, purchase_invoices, tax_credits=Decimal('2000'))

        return render(request, "budsidesk_app/dash/tax_report/tax_report.html", {
            "tax_data": tax_data,
            "sales_invoices": sales_invoices,        # ✅ Nombre correcto para template
            "purchase_invoices": purchase_invoices,  # ✅ Nombre correcto para template
            "sales_count": sales_invoices.count(),
            "purchases_count": purchase_invoices.count(),
            "current_year": year
        })
    except Exception as e:
        print(f"Error en tax report for year {year}: {e}")
        return redirect("tax_report")