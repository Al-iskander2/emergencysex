# logic/settings_user.py - VERSIÓN COMPLETA Y ROBUSTA

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from emerg_database.models import FiscalProfile, User

@login_required
def account_settings_logic(request):
    """
    Lógica completa para manejar todas las secciones de configuración
    """
    user = request.user
    profile, created = FiscalProfile.objects.get_or_create(user=user)

    if request.method == "POST":
        form_type = request.POST.get('form_type', 'general')
        
        try:
            if form_type == 'profile':
                # 🔽 ACTUALIZAR PERFIL PERSONAL
                user.first_name = request.POST.get('first_name', user.first_name)
                user.last_name = request.POST.get('last_name', user.last_name)
                user.save()
                messages.success(request, "✅ Personal profile updated successfully!")
                
            elif form_type == 'business':
                # 🔽 ACTUALIZAR INFORMACIÓN DEL NEGOCIO
                profile.business_name = request.POST.get('business_name', profile.business_name)
                profile.legal_name = request.POST.get('legal_name', profile.legal_name)
                profile.business_type = request.POST.get('business_type', profile.business_type)
                profile.profession = request.POST.get('profession', profile.profession)
                profile.sector = request.POST.get('sector', profile.sector)
                profile.contact_full_name = request.POST.get('contact_full_name', profile.contact_full_name)
                profile.phone = request.POST.get('phone', profile.phone)
                
                # 🔽 DIRECCIÓN
                profile.addr_line1 = request.POST.get('addr_line1', profile.addr_line1)
                profile.addr_line2 = request.POST.get('addr_line2', profile.addr_line2)
                profile.city = request.POST.get('city', profile.city)
                profile.county = request.POST.get('county', profile.county)
                profile.eircode = request.POST.get('eircode', profile.eircode)
                profile.country = request.POST.get('country', profile.country)
                
                profile.save()
                messages.success(request, "✅ Business details updated successfully!")
                
            elif form_type == 'branding':
                # 🔽 MANEJAR LOGO
                if 'remove_logo' in request.POST and request.POST['remove_logo']:
                    # Eliminar logo actual
                    if profile.logo:
                        profile.logo.delete(save=False)
                        profile.logo = None
                        messages.success(request, "✅ Logo removed successfully!")
                elif 'logo' in request.FILES:
                    # Subir nuevo logo
                    profile.logo = request.FILES['logo']
                    messages.success(request, "✅ Logo updated successfully!")
                
                profile.save()
                
            elif form_type == 'billing':
                # 🔽 CONFIGURACIÓN FISCAL Y FACTURACIÓN
                profile.vat_registered = 'vat_registered' in request.POST
                profile.vat_number = request.POST.get('vat_number', profile.vat_number)
                profile.pps_number = request.POST.get('pps_number', profile.pps_number)
                profile.tax_country = request.POST.get('tax_country', profile.tax_country)
                profile.tax_region = request.POST.get('tax_region', profile.tax_region)
                profile.currency = request.POST.get('currency', profile.currency)
                profile.payment_terms = request.POST.get('payment_terms', profile.payment_terms)
                profile.payment_methods = request.POST.get('payment_methods', profile.payment_methods)
                profile.accounting_method = request.POST.get('accounting_method', profile.accounting_method)
                profile.invoice_footer = request.POST.get('invoice_footer', profile.invoice_footer)
                
                # 🔽 BANCO
                profile.iban = request.POST.get('iban', profile.iban)
                profile.bic = request.POST.get('bic', profile.bic)
                
                # 🔽 RECORDATORIOS
                profile.reminders_enabled = 'reminders_enabled' in request.POST
                reminder_days = request.POST.get('reminder_days_before_due')
                if reminder_days and reminder_days.isdigit():
                    profile.reminder_days_before_due = int(reminder_days)
                
                profile.save()
                messages.success(request, "✅ Billing and tax information updated successfully!")
                
            elif form_type == 'general':
                # 🔽 VERSIÓN LEGACY - Para compatibilidad con el formulario antiguo
                user.first_name = request.POST.get('first_name', user.first_name)
                user.last_name = request.POST.get('last_name', user.last_name)
                user.save()
                
                # Negocio
                profile.business_name = request.POST.get('business_name', profile.business_name)
                profile.legal_name = request.POST.get('legal_name', profile.legal_name)
                profile.business_type = request.POST.get('business_type', profile.business_type)
                profile.profession = request.POST.get('profession', profile.profession)
                profile.sector = request.POST.get('sector', profile.sector)
                profile.contact_full_name = request.POST.get('contact_full_name', profile.contact_full_name)
                profile.phone = request.POST.get('phone', profile.phone)
                
                # Logo
                if 'remove_logo' in request.POST:
                    if profile.logo:
                        profile.logo.delete(save=False)
                        profile.logo = None
                elif 'logo' in request.FILES:
                    profile.logo = request.FILES['logo']
                
                # Dirección
                profile.addr_line1 = request.POST.get('addr_line1', profile.addr_line1)
                profile.addr_line2 = request.POST.get('addr_line2', profile.addr_line2)
                profile.city = request.POST.get('city', profile.city)
                profile.county = request.POST.get('county', profile.county)
                profile.eircode = request.POST.get('eircode', profile.eircode)
                profile.country = request.POST.get('country', profile.country)
                
                # Fiscal
                profile.vat_registered = 'vat_registered' in request.POST
                profile.vat_number = request.POST.get('vat_number', profile.vat_number)
                profile.pps_number = request.POST.get('pps_number', profile.pps_number)
                profile.tax_country = request.POST.get('tax_country', profile.tax_country)
                profile.tax_region = request.POST.get('tax_region', profile.tax_region)
                profile.currency = request.POST.get('currency', profile.currency)
                profile.payment_terms = request.POST.get('payment_terms', profile.payment_terms)
                profile.payment_methods = request.POST.get('payment_methods', profile.payment_methods)
                profile.accounting_method = request.POST.get('accounting_method', profile.accounting_method)
                profile.invoice_footer = request.POST.get('invoice_footer', profile.invoice_footer)
                
                # Recordatorios y banco
                profile.reminders_enabled = 'reminders_enabled' in request.POST
                reminder_days = request.POST.get('reminder_days_before_due')
                if reminder_days and reminder_days.isdigit():
                    profile.reminder_days_before_due = int(reminder_days)
                profile.iban = request.POST.get('iban', profile.iban)
                profile.bic = request.POST.get('bic', profile.bic)
                
                profile.save()
                messages.success(request, "✅ Account settings updated successfully!")

        except Exception as e:
            messages.error(request, f"❌ Error saving changes: {str(e)}")
            # 🔽 LOG PARA DEBUG
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in account_settings_logic: {str(e)}")

        return redirect('account_settings')

    # 🔽 GET: MOSTRAR PÁGINA CON DATOS ACTUALES
    return render(request, "emergency_app/account_settings.html", {
        "user": user,
        "profile": profile,
    })

# Alias para compatibilidad
def account_settings_view(request):
    return account_settings_logic(request)