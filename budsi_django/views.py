# budsi_django/views.py
###################
# IMPORTS
###################

# Django
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.http import FileResponse
from django.contrib import messages
from django.shortcuts import get_object_or_404

# Modelos
from budsi_database.models import Invoice, FiscalProfile

# Lógica
from logic.fill_pdf import generate_invoice_pdf
from logic.pulse import pulse_page
# email
from logic.email_central.email_central import email_action

#planes
from logic.plan_tiers import elite_required, smart_required

#############################
# VISTAS SIMPLES - SOLO RENDER
#############################

def home(request):
    """Vista de página de inicio - REDIRIGE A INTRO"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, "budsidesk_app/intro.html")

@login_required
def faqs_view(request):
    """Vista para Preguntas Frecuentes (FAQs)"""
    return render(request, "budsidesk_app/dash/help_support/faqs.html")

@login_required
def balance_overview_view(request):
    """Vista de balance financiero"""
    context = {"message": "Financial overview section - under development"}
    return render(request, "budsidesk_app/dash/finances/balance_overview.html", context)

@login_required
def reminders_view(request):
    """Vista de recordatorios"""
    return render(request, "budsidesk_app/reminders.html")

@login_required
def flow_view(request):
    """Vista de flujo"""
    return render(request, "budsidesk_app/dash/flow/flow.html")

@login_required
def pulse_view(request):
    """Vista de pulse"""
    return render(request, "budsidesk_app/dash/pulse/main_pulse.html")

@login_required
def buzz_view(request):
    """Vista de buzz"""
    return render(request, "budsidesk_app/dash/buzz/buzz.html")

@login_required
def nest_view(request):
    """Vista de nest"""
    return render(request, "budsidesk_app/dash/nest/nest.html")

@login_required
def whiz_view(request):
    """Vista de whiz"""
    return render(request, "budsidesk_app/dash/whiz/whiz.html")

@login_required
def help_view(request):
    """Vista de ayuda"""
    return render(request, "budsidesk_app/dash/help_support/support.html")

#############################
# VISTAS MAIN (CENTRO DE NAVEGACIÓN)
#############################

@login_required
def main_invoice_view(request):
    """Vista principal de invoices - redirige al listado"""
    return redirect('invoice_list')

#############################
# Expenses 
#############################

@login_required
def main_expenses_view(request):
    """Vista principal de expenses - redirige al listado"""
    return redirect('expense_list')

@login_required
def expenses_delete_view(request, invoice_id):
    from logic.expenses import expenses_delete_view as logic_expenses_delete
    return logic_expenses_delete(request, invoice_id)

#############################
# VISTAS MAIN 
#############################

@login_required
def main_pulse_view(request):
    """Vista principal de pulse (datos reales) - PUENTE"""
    from logic.pulse import pulse_page
    return pulse_page(request)

@login_required
def main_track_view(request):
    """Vista principal de track"""
    return render(request, "budsidesk_app/dash/track/main_track.html")

#############################
# VISTAS ESPECIALIZADAS
#############################

@login_required
def create_invoice_pdf_view(request):
    """Generar PDF de factura"""
    try:
        profile = FiscalProfile.objects.get(user=request.user)
        pdf_path = generate_invoice_pdf(profile)
        return FileResponse(open(pdf_path, 'rb'), as_attachment=True, filename="invoice.pdf")
    except FiscalProfile.DoesNotExist:
        messages.error(request, "Please complete your fiscal profile first")
        return redirect("onboarding")
    except Exception as e:
        messages.error(request, f"Error generating PDF: {str(e)}")
        return redirect("invoice_list")

@login_required
def invoice_gallery_view(request, invoice_id):
    """Galería de facturas"""
    from logic.expenses import invoice_gallery_view as expenses_gallery_view
    return expenses_gallery_view(request, invoice_id)

@login_required
def credit_note_create_view(request):
    """Vista para crear notas de crédito"""
    try:
        profile = FiscalProfile.objects.get(user=request.user)
        return render(request, "budsidesk_app/dash/invoice/credite_note.html", {"profile": profile})
    except FiscalProfile.DoesNotExist:
        messages.error(request, "Please complete your fiscal profile first")
        return redirect("onboarding")

@login_required
def credit_note_save_view(request):
    """Guarda una nota de crédito"""
    if request.method != "POST":
        return redirect("credit_note_create")
    messages.info(request, "Credit note functionality coming soon!")
    return redirect("dashboard")

#############################
# Dashboard
#############################

@login_required
def dashboard_view(request):
    """Vista wrapper para el dashboard"""
    try:
        # Importación tardía para evitar problemas
        from logic.dashboard import dashboard_page
        return dashboard_page(request)
    except Exception as e:
        # Fallback si hay cualquier error
        from django.shortcuts import render
        from django.contrib import messages
        messages.error(request, f"Dashboard error: {str(e)}")
        return render(request, 'budsidesk_app/dashboard.html', {
            "monthly_income": [],
            "revenue_expenses": {"revenue": 0.0, "expenses": 0.0},
            "spending_data": [],
            "annual_comparison": {"current_year": 0.0, "previous_year": 0.0},
            "tax_data": {"vat":{"liability":0.0},"income_tax":{"net":0.0},"usc":{"total":0.0},"prsi":0.0},
            "current_year": 2024,
            "previous_year": 2023,
            "smart_reminders": [],
        })

#############################
# VISTAS DE COMPATIBILIDAD (REDIRIGEN A LÓGICA)
#############################

@login_required
def invoice_list_view(request):
    """Vista de compatibilidad - redirige a invoice_list"""
    from logic.invoices import invoice_list_view as logic_invoice_list
    return logic_invoice_list(request)

@login_required 
def invoice_create_view(request):
    """Vista de compatibilidad - redirige a invoice_create"""
    from logic.invoices import invoice_create_view as logic_invoice_create
    return logic_invoice_create(request)

@login_required
def view_invoice(request, invoice_id):
    """Vista de compatibilidad - redirige a invoice_detail"""
    from logic.invoices import invoice_detail_view as logic_invoice_detail
    return logic_invoice_detail(request, invoice_id)

@login_required
def update_invoice_status(request, invoice_id):
    """Vista de compatibilidad - redirige a invoice_update_status"""
    from logic.invoices import invoice_update_status_view as logic_update_status
    return logic_update_status(request, invoice_id)

@login_required
def expenses_list_view(request):
    """Vista de compatibilidad - redirige a expense_list"""
    from logic.expenses import expense_list_view as logic_expense_list
    return logic_expense_list(request)

@login_required
def expenses_create_view(request):
    """Vista de compatibilidad para creación de expenses"""
    from logic.expenses import expenses_create_view as logic_expenses_create
    return logic_expenses_create(request)

@login_required
def general_upload(request):
    """Vista de compatibilidad para upload general"""
    from logic.expenses import general_upload as logic_upload
    return logic_upload(request)

@login_required
def invoice_upload_view(request):
    """Vista de compatibilidad para upload de invoices"""
    from logic.expenses import invoice_upload_view as logic_invoice_upload
    return logic_invoice_upload(request)

@login_required
def expenses_upload_view(request):
    """Vista de compatibilidad para upload de expenses"""
    from logic.expenses import expenses_upload_view as logic_expenses_upload
    return logic_expenses_upload(request)

@login_required
def invoice_preview_view(request, invoice_id):
    """Vista de compatibilidad para preview de invoices"""
    from logic.expenses import invoice_preview_view as logic_preview
    return logic_preview(request, invoice_id)

@login_required
def expense_list_view(request):
    """Vista de compatibilidad para lista de expenses"""
    from logic.expenses import expense_list_view as logic_expense_list
    return logic_expense_list(request)

@login_required
def tax_report_view(request):
    """Vista de compatibilidad para tax report"""
    from logic.tax_report import tax_report_view as logic_tax_report
    return logic_tax_report(request)

@login_required
def process_payment_view(request):
    """Vista de compatibilidad para procesar pago"""
    from logic.stripe import process_payment_view as logic_process_payment
    return logic_process_payment(request)

@login_required
def pricing_view(request):
    """Vista de compatibilidad para pricing"""
    from logic.stripe import pricing_view as logic_pricing
    return logic_pricing(request)

@login_required
def create_payment_intent_view(request):
    """Vista de compatibilidad para crear intento de pago"""
    from logic.stripe import create_payment_intent_view as logic_create_payment_intent
    return logic_create_payment_intent(request)

@login_required
def payment_page(request):
    """Vista de compatibilidad para página de pago"""
    from logic.stripe import payment_page as logic_payment_page
    return logic_payment_page(request)

@login_required
def intro_view(request):
    """Vista de compatibilidad para intro"""
    from logic.auth import intro_view as logic_intro
    return logic_intro(request)

@login_required
def login_view(request):
    """Vista de compatibilidad para login"""
    from logic.auth import login_view as logic_login
    return logic_login(request)

@login_required
def register_view(request):
    """Vista de compatibilidad para registro"""
    from logic.auth import register_view as logic_register
    return logic_register(request)

@login_required
def onboarding_view(request):
    """Vista de compatibilidad para onboarding"""
    from logic.auth import onboarding_view as logic_onboarding
    return logic_onboarding(request)

@login_required
def account_settings_view(request):
    """Vista de compatibilidad para configuración de cuenta"""
    from logic.auth import account_settings_view as logic_account_settings
    return logic_account_settings(request)

@login_required
def invoices_list_view(request):
    """Vista de compatibilidad para lista de invoices"""
    from logic.invoices import invoices_list_view as logic_invoices_list
    return logic_invoices_list(request)

@login_required
def invoices_create_view(request):
    """Vista de compatibilidad para crear invoice"""
    from logic.invoices import invoices_create_view as logic_invoices_create
    return logic_invoices_create(request)

@login_required
def invoices_detail_view(request, pk):
    """Vista de compatibilidad para detalle de invoice"""
    from logic.invoices import invoices_detail_view as logic_invoices_detail
    return logic_invoices_detail(request, pk)

@login_required
def invoices_update_status_view(request, pk):
    """Vista de compatibilidad para actualizar estado de invoice"""
    from logic.invoices import invoices_update_status_view as logic_invoices_update_status
    return logic_invoices_update_status(request, pk)

@login_required
def invoices_create_from_customer_view(request):
    """Vista de compatibilidad para crear invoice desde cliente"""
    from logic.invoices import invoices_create_from_customer_view as logic_invoices_from_customer
    return logic_invoices_from_customer(request)

@login_required
def invoice_save(request):
    """Vista de compatibilidad para guardar invoice"""
    from logic.invoices import invoice_save as logic_invoice_save
    return logic_invoice_save(request)

#########
# SEND EMAIL
#########

@login_required
def email_action_view(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    action = request.POST.get("action")
    to_email = request.POST.get("to_email")
    target_id = request.POST.get("target_id")
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "/"

    result = email_action(
        user=request.user,
        action=action,
        to_email=to_email,
        target_id=target_id,
    )

    if result.success:
        messages.success(request, result.message)
    else:
        messages.error(request, result.message)

    return redirect(next_url)

#############################
# VISTAS DOCS (CIRCUITO SIMPLE ACTUAL) - AGRUPADAS Y LIMPIAS
#############################

@login_required
def legal_templates_view(request):
    """Vista principal de plantillas legales - SOLO RENDER"""
    return render(request, "budsidesk_app/dash/doc/legal_templates.html")

@login_required
def service_agreement_form_view(request):
    """Formulario de Service Agreement"""
    return render(request, "budsidesk_app/dash/doc/docs_slaves /service_agreement.html")

@login_required
def project_proposal_form_view(request):
    """Formulario de Project Proposal"""  
    return render(request, "budsidesk_app/dash/doc/docs_slaves /project_proposal.html")

@login_required
def time_sheet_form_view(request):
    """Formulario de Time Sheet"""
    return render(request, "budsidesk_app/dash/doc/docs_slaves /time_sheet.html")

@login_required
def non_disclosure_form_view(request):
    """Formulario de Non-Disclosure Agreement"""
    return render(request, "budsidesk_app/dash/doc/docs_slaves /non_disclosure.html")

@login_required
def statement_of_work_form_view(request):
    """Formulario de Statement of Work"""
    return render(request, "budsidesk_app/dash/doc/docs_slaves /statement_of_work.html")



def email_action_view(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    
    # Manejar tanto JSON como form data
    if request.content_type == 'application/json':
        import json
        data = json.loads(request.body)
        action = data.get("action")
        to_email = data.get("to_email")
        target_id = data.get("target_id")
    else:
        # Form data tradicional
        action = request.POST.get("action")
        to_email = request.POST.get("to_email")
        target_id = request.POST.get("target_id")
    
    from logic.email_central import email_action
    result = email_action(
        user=request.user,
        action=action,
        to_email=to_email,
        target_id=target_id,
    )
    
    # Si es JSON, responder con JSON
    if request.content_type == 'application/json':
        from django.http import JsonResponse
        return JsonResponse({
            'success': result.success,
            'message': result.message
        })
    else:
        # Comportamiento original para form submissions
        next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "/"
        if result.success:
            messages.success(request, result.message)
        else:
            messages.error(request, result.message)
        return redirect(next_url)
    

### planes 
@elite_required
def buzz_dashboard_view(request):
    # Vista del buzz module
    pass

@elite_required  
def favorite_customers_view(request):
    # Vista de favorite customers
    pass

@smart_required
def track_view(request):
    # Solo accessible para Smart y Elite
    pass