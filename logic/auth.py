# budsi_django/views/auth.py
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

from budsi_django.forms import CustomUserCreationForm
from budsi_database.models import FiscalProfile

def intro_view(request):
    """✅ Vista de introducción - redirige a dashboard si ya está autenticado"""
    if request.user.is_authenticated:
        return redirect("dashboard")  
    return render(request, "budsidesk_app/intro.html")

def login_view(request):
    """✅ Vista de login"""
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        user = authenticate(request, email=email, password=password)
        if user is not None:
            login(request, user)
            return redirect("dashboard")
        else:
            return render(request, "budsidesk_app/login.html", {"error": "Invalid email or password"})
    return render(request, "budsidesk_app/login.html")

def register_view(request):
    """✅ Vista de registro"""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.backend = 'budsi_django.backends.EmailBackend'
            login(request, user)
            return redirect('onboarding')
    else:
        form = CustomUserCreationForm()
    return render(request, 'budsidesk_app/register.html', {'form': form})

@login_required
def onboarding_view(request):
    """✅ Vista de onboarding"""
    if request.method == "POST":
        invoice_defaults = request.POST.get("invoice_defaults", "").lower() in ["true", "yes", "1"]
        vat_registered = request.POST.get("vat_registered", "").lower() in ["true", "yes", "1"]
        vat_number = request.POST.get("vat_number", "").strip() if vat_registered else ""

        try:
            FiscalProfile.objects.create(
                user=request.user,
                contact_full_name=request.POST.get("contact_full_name"),
                phone=request.POST.get("phone"),
                logo=request.FILES.get("logo"),
                business_name=request.POST.get("business_name"),
                profession=request.POST.get("profession"),
                sector=request.POST.get("sector"),
                currency=request.POST.get("currency"),
                invoice_defaults=invoice_defaults,
                payment_terms=request.POST.get("payment_terms"),
                late_notice=request.POST.get("late_notice"),
                payment_methods=request.POST.get("payment_methods"),
                vat_registered=vat_registered,
                vat_number=vat_number,
                pps_number=request.POST.get("pps_number"),
                iban=request.POST.get("iban"),
            )
            return redirect("dashboard")

        except Exception as e:
            print(f"Error in onboarding: {e}")
            return render(request, "budsidesk_app/onboard.html", {"error": str(e)})

    return render(request, "budsidesk_app/onboard.html")

@login_required
def account_settings_view(request):
    """✅ Vista para configuración de cuenta - CON soporte POST"""
    try:
        profile = FiscalProfile.objects.get(user=request.user)
        
        # ✅ AÑADIR MANEJO DE POST (igual que en account_settings.py)
        if request.method == "POST":
            form_type = request.POST.get('form_type', 'general')
            
            if form_type == 'branding':
                # 🔽 MANEJAR LOGO (misma lógica que account_settings.py)
                if 'remove_logo' in request.POST and request.POST['remove_logo']:
                    if profile.logo:
                        profile.logo.delete(save=False)
                        profile.logo = None
                        messages.success(request, "✅ Logo removed successfully!")
                elif 'logo' in request.FILES:
                    profile.logo = request.FILES['logo']
                    messages.success(request, "✅ Logo updated successfully!")
                
                profile.save()
                return redirect('account_settings')  # ✅ REDIRIGIR después de POST
            
            # Puedes añadir más form_types aquí si necesitas...
        
        return render(request, "budsidesk_app/account_settings.html", {
            'profile': profile
        })
        
    except FiscalProfile.DoesNotExist:
        return redirect('onboarding')

