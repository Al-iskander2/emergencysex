# logic/invoices.py - VERSIÓN COMPLETA ACTUALIZADA
import json
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.urls import reverse

from logic.invoice_service import InvoiceService
from logic.send_email import send_invoice_email
from budsi_database.models import FiscalProfile, Invoice, Contact, InvoiceConcept
from logic.create_contact import get_or_create_contact

from logic.track import ensure_project

from logic.logo_service import inject_logo_context

from logic.invoice_limits import can_create_invoice, get_invoice_limits


@login_required
def invoice_list_view(request):
    """✅ Vista principal de invoices con InvoiceConcept - SOLO VENTAS"""
    try:
        profile = FiscalProfile.objects.get(user=request.user)
    except FiscalProfile.DoesNotExist:
        return redirect("onboarding")

    # ✅ CORRECCIÓN: Filtrar solo invoices de venta
    invoices = Invoice.objects.filter(
        user=request.user, 
        invoice_type="sale"  # ← SOLO VENTAS
    ).select_related('contact').order_by("-date")

    # ✅ CORRECCIÓN CRÍTICA: Obtener clientes favoritos
    favorite_customers = Contact.objects.filter(
        user=request.user, 
        is_client=True,
        is_favorite=True
    ).order_by("name")

    # Calcular contadores de estado
    paid_count = invoices.filter(status="paid").count()
    pending_count = invoices.filter(status="pending").count()
    overdue_count = invoices.filter(status="overdue").count()

    context = {
        "invoice_count": profile.invoice_count,
        "sales_invoices": invoices,
        "favorite_customers": favorite_customers,  # ✅ AHORA SÍ SE INCLUYE
        "paid_count": paid_count,
        "pending_count": pending_count,
        "overdue_count": overdue_count,
    }
    return render(request, "budsidesk_app/dash/invoice/main_invoice.html", context)

@login_required
@require_GET
def invoice_create_view(request):
    """✅ Vista para crear invoice con soporte para InvoiceConcept"""
    # Verificar si viene de un favorite customer
    customer_id = request.GET.get('customer')
    prefilled_contact = None
    
    if customer_id:
        try:
            prefilled_contact = Contact.objects.get(id=customer_id, user=request.user, is_client=True)
        except Contact.DoesNotExist:
            messages.error(request, "Cliente no encontrado")
    
    try:
        profile = FiscalProfile.objects.get(user=request.user)
    except FiscalProfile.DoesNotExist:
        return redirect('onboarding')

    return render(request, "budsidesk_app/dash/invoice/create_invoice.html", {
        'profile': profile,
        'invoice_count': profile.invoice_count,
        'prefilled_contact': prefilled_contact
    })


@login_required
@require_POST
def invoice_save_view(request):
    """✅ Save new invoice with InvoiceConcept - UPDATED VERSION with new fields and discounts"""
    
    # 🔒 CHECK INVOICE LIMIT
    if not can_create_invoice(request.user, is_credit_note=False):
        limits = get_invoice_limits(request.user)
        messages.error(
            request,
            f"Limit reached: {limits['message']}. "
            "Upgrade to Budsi Smart for unlimited invoices."
        )
        return redirect("pricing")
    
    try:
        with transaction.atomic():
            # ✅ OBTENER PERFIL FISCAL (FALTABA)
            profile = FiscalProfile.objects.get(user=request.user)
            invoice_count = profile.invoice_count + 1
            invoice_number = f"INV-{invoice_count:06d}"
            
            # ✅ OBTENER contact_name DEL FORMULARIO (FALTABA)
            contact_name = request.POST.get("contact", "").strip()
            if not contact_name:
                messages.error(request, "Client name is required")
                return redirect("invoice_create")
                
            # ✅ USAR TU FUNCIÓN ROBUSTA DE create_contact.py
            contact = get_or_create_contact(
                user=request.user,
                name=contact_name,  # ← AHORA SÍ DEFINIDO
                is_client=True,
                is_supplier=False
            )
            
            # ✅ ACTUALIZAR CONTACTO CON NUEVOS CAMPOS (email, address, cellphone)
            mail = (request.POST.get("email") or "").strip()
            addr = (request.POST.get("address") or "").strip()
            cell = (request.POST.get("cellphone") or "").strip()

            updated = False
            if mail and (contact.email != mail):
                contact.email = mail
                updated = True
            if addr and (getattr(contact, "address", "") != addr):
                contact.address = addr
                updated = True
            if cell and (getattr(contact, "cellphone", "") != cell):
                contact.cellphone = cell
                updated = True
            if updated:
                contact.save(update_fields=["email", "address", "cellphone"])
            
            # ✅ Marcar como favorito (como ya haces en tu función)
            if not contact.is_favorite:
                contact.is_favorite = True
                contact.save()
            
            print(f"⭐ Contacto '{contact_name}' procesado (ID: {contact.id})")
            
            # ✅ Asegurar que el proyecto exista
            project_name = request.POST.get("project", "").strip()
            if project_name:
                project = ensure_project(request.user, project_name)
                print(f"✅ Proyecto '{project_name}' asegurado (ID: {project.id if project else 'None'})")
            
            # Procesar montos y fecha
            from decimal import Decimal  # ✅ IMPORTAR DECIMAL AQUÍ
            subtotal = Decimal(request.POST.get("subtotal", 0))
            vat_amount = Decimal(request.POST.get("vat_amount", 0))
            total = subtotal + vat_amount
            
            # Obtener la fecha de la factura
            invoice_date = request.POST.get("date")
            if not invoice_date:
                invoice_date = timezone.now().date()
            
            print(f"📊 Creating invoice: {invoice_number}")
            print(f"📅 Date: {invoice_date}")
            print(f"💰 Amounts - Subtotal: {subtotal}, VAT: {vat_amount}, Total: {total}")
            print(f"📁 Project: {project_name}")
            
            # ✅ CREAR FACTURA CON SNAPSHOT DEL CLIENTE
            invoice = Invoice.objects.create(
                user=request.user,
                contact=contact,
                invoice_type="sale",
                invoice_number=invoice_number,
                date=invoice_date,
                subtotal=subtotal,
                vat_amount=vat_amount,
                total=total,
                summary=(request.POST.get("notes", "") or "").strip()[:200],
                category=request.POST.get("category", ""),
                project=project_name,
                is_confirmed=True,
                status="send",
                # ✅ SNAPSHOT del cliente
                client_name=contact.name,
                client_email=mail or contact.email or "",
                client_cellphone=cell or getattr(contact, "cellphone", "") or "",
                client_address=addr or getattr(contact, "address", "") or "",
            )
            
            # ✅ PROCESAR CONCEPTOS CON DESCUENTOS
            descriptions = request.POST.getlist('concept_description[]')
            quantities = request.POST.getlist('concept_quantity[]')
            unit_prices = request.POST.getlist('concept_unit_price[]')
            discount_rates = request.POST.getlist('concept_discount_rate[]')
            discount_amounts = request.POST.getlist('concept_discount_amount[]')
            
            # ✅ Usar VAT rate global en lugar de individual por concepto
            global_vat_rate = Decimal(request.POST.get("vat_rate", "23.0"))
            
            concepts_created = 0
            for i in range(len(descriptions)):
                if descriptions[i] and descriptions[i].strip():
                    # ✅ CORRECCIÓN: Usar cantidad segura con valores por defecto
                    quantity = quantities[i] if i < len(quantities) and quantities[i] else '1.0'
                    unit_price = unit_prices[i] if i < len(unit_prices) and unit_prices[i] else '0.0'
                    discount_rate = discount_rates[i] if i < len(discount_rates) and discount_rates[i] else '0.0'
                    discount_amount = discount_amounts[i] if i < len(discount_amounts) and discount_amounts[i] else '0.0'
                    
                    # Crear el concepto con los campos de descuento
                    InvoiceConcept.objects.create(
                        invoice=invoice,
                        description=descriptions[i].strip(),
                        quantity=Decimal(quantity),
                        unit_price=Decimal(unit_price),
                        vat_rate=global_vat_rate,  # ← Usar VAT rate global
                        discount_rate=Decimal(discount_rate),
                        discount_amount=Decimal(discount_amount)
                    )
                    concepts_created += 1
            
            print(f"✅ Created {concepts_created} concepts for invoice {invoice_number}")
            
            # Actualizar contador
            profile.invoice_count = invoice_count
            profile.save()
            
            messages.success(request, f"Invoice {invoice.invoice_number} created successfully!")
            return redirect("invoice_list")
            
    except Exception as e:
        error_msg = f"Error creating invoice: {str(e)}"
        print(f"❌ {error_msg}")
        import traceback
        print(f"🔍 Stack trace: {traceback.format_exc()}")
        
        messages.error(request, error_msg)
        try:
            profile = FiscalProfile.objects.get(user=request.user)
            return render(request, "budsidesk_app/dash/invoice/create_invoice.html", {
                "profile": profile,
                "invoice_count": profile.invoice_count,
                "form_data": request.POST,
                "error": error_msg
            })
        except FiscalProfile.DoesNotExist:
            return redirect('onboarding')



@login_required
@require_POST
def invoice_update_status_view(request, invoice_id):
    """✅ Actualizar estado de factura vía AJAX - CON paid_at"""
    try:
        invoice = get_object_or_404(Invoice, id=invoice_id, user=request.user)
        data = json.loads(request.body)
        new_status = data.get("status")
        
        if new_status not in ["draft", "sent", "paid", "overdue", "cancelled"]:
            return JsonResponse({"success": False, "error": "Estado inválido"}, status=400)

        # ✅ ACTUALIZAR paid_at CUANDO SE MARCA COMO PAGADO
        if new_status == "paid" and invoice.status != "paid":
            invoice.paid_at = timezone.now()
        
        success = InvoiceService.update_invoice_status(invoice, new_status)
        if success:
            invoice.save()  # Guardar el paid_at
            return JsonResponse({
                "success": True, 
                "new_status": new_status,
                "payment_date": invoice.payment_date.strftime("%d %b %Y") if invoice.payment_date else None
            })
        else:
            return JsonResponse({"success": False, "error": "Error actualizando estado"}, status=400)
            
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)

@login_required
@require_POST
def invoice_send_email_view(request, invoice_id):
    """✅ Enviar invoice por email vía AJAX"""
    try:
        invoice = get_object_or_404(Invoice, id=invoice_id, user=request.user)
        data = json.loads(request.body)
        email = data.get("email")
        
        if not email:
            return JsonResponse({"success": False, "error": "Email required"}, status=400)
        
        result = send_invoice_email(
            user=request.user, 
            invoice_id=invoice_id, 
            to_email=email
        )
        
        return JsonResponse({"success": result.success, "message": result.message}, status=result.status)
            
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)

@login_required
def invoices_create_from_customer_view(request, customer_id: int):
    """✅ Crear factura desde Favorite Customers - VERSIÓN MEJORADA"""
    try:
        contact = Contact.objects.get(id=customer_id, user=request.user, is_client=True)
        profile = FiscalProfile.objects.get(user=request.user)
        
        # ✅ CORRECCIÓN: Renderizar directamente create_invoice.html con el contacto prellenado
        return render(request, "budsidesk_app/dash/invoice/create_invoice.html", {
            'profile': profile,
            'invoice_count': profile.invoice_count,
            'prefilled_contact': contact
        })
        
    except Contact.DoesNotExist:
        messages.error(request, "Cliente no encontrado")
        return redirect("invoice_list")
    except FiscalProfile.DoesNotExist:
        messages.error(request, "Por favor completa tu perfil fiscal primero")
        return redirect("onboarding")

# ========== FUNCIONES COMPATIBILIDAD ==========

@login_required
def view_invoice(request, invoice_id):
    """Vista para visualizar una factura específica - PARÁMETRO CORREGIDO"""
    invoice = get_object_or_404(Invoice, id=invoice_id, user=request.user)
    
    # ✅ Obtener conceptos si existen
    concepts = getattr(invoice, 'concepts', None)
    if concepts:
        concepts = concepts.all()
    
    context = {
        'invoice': invoice,
        'concepts': concepts,
        'is_pdf': getattr(invoice.original_file, 'name', '').lower().endswith('.pdf') if invoice.original_file else False,
    }
    
    return render(request, 'budsidesk_app/dash/invoice/visualize_invoice.html', context)

@login_required
@require_POST
def update_invoice_status(request, invoice_id):
    """Actualizar el estado de una factura"""
    invoice = get_object_or_404(Invoice, id=invoice_id, user=request.user)
    
    try:
        new_status = request.POST.get('status')
        if new_status in ['paid', 'pending', 'overdue']:
            invoice.status = new_status
            invoice.save()
            return JsonResponse({'success': True, 'new_status': new_status})
        else:
            return JsonResponse({'success': False, 'error': 'Estado inválido'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def invoices_list_view(request):
    """Vista de lista de facturas - para compatibilidad"""
    return invoice_list_view(request)

@login_required
def invoices_create_view(request):
    """Vista de creación de facturas - para compatibilidad"""
    return invoice_create_view(request)

@login_required
def invoices_detail_view(request, invoice_id):
    """Vista de detalle de factura"""
    return view_invoice(request, invoice_id)

@login_required
def invoices_update_status_view(request, invoice_id):
    """Wrapper para update_invoice_status"""
    return update_invoice_status(request, invoice_id)

@login_required
def main_invoice_view(request):
    """Vista principal de facturas"""
    return invoice_list_view(request)

@login_required
def invoices_create_from_customer_view_wrapper(request):
    """Vista para crear factura desde cliente - sin ID"""
    return redirect("invoice_create")

@login_required
@require_POST
def invoice_save(request):
    """Guardar factura - para compatibilidad con URLs legacy"""
    try:
        messages.success(request, "Factura guardada exitosamente!")
        return redirect("invoice_list")
    except Exception as e:
        messages.error(request, f"Error guardando factura: {str(e)}")
        return redirect("invoice_list")

@login_required
def invoices_send_email_view(request, invoice_id):
    """Enviar factura por email - para compatibilidad"""
    invoice = get_object_or_404(Invoice, id=invoice_id, user=request.user)
    
    # Por ahora, solo un mensaje de placeholder
    messages.info(request, f"Función de email para {invoice.invoice_number} próximamente!")
    return redirect("view_invoice", invoice_id=invoice_id)

@login_required
def credit_note_create_view(request):
    """✅ Vista para crear credit note con factura origen"""
    try:
        profile = FiscalProfile.objects.get(user=request.user)
    except FiscalProfile.DoesNotExist:
        return redirect("onboarding")
    
    base_invoice = None
    initial_data = {}
    
    # ✅ Obtener factura origen si se proporciona
    invoice_id = request.GET.get('invoice')
    if invoice_id:
        try:
            base_invoice = Invoice.objects.get(id=invoice_id, user=request.user)
            initial_data = {
                'contact': base_invoice.contact.name,
                'subtotal': str(base_invoice.subtotal),
                'vat_amount': str(base_invoice.vat_amount),
                'total': str(base_invoice.total),
                'description': f"Credit note for invoice {base_invoice.invoice_number}",
            }
        except Invoice.DoesNotExist:
            messages.error(request, "Original invoice not found")
    
    return render(request, "budsidesk_app/dash/invoice/credite_note.html", {
        'profile': profile,
        'base_invoice': base_invoice,
        'initial_data': initial_data,
    })

@login_required
@require_POST
def credit_note_save_view(request):
    """✅ Save credit note"""
    
    # 🔒 CHECK CREDIT NOTE LIMIT
    if not can_create_invoice(request.user, is_credit_note=True):
        limits = get_invoice_limits(request.user)
        messages.error(
            request,
            f"Limit reached: {limits['message']}. "
            "Upgrade to Budsi Smart for unlimited credit notes."
        )
        return redirect("pricing")

    try:
        with transaction.atomic():
            profile = FiscalProfile.objects.get(user=request.user)
            credit_note_count = getattr(profile, 'credit_note_count', 0) + 1
            credit_note_number = f"CN-{credit_note_count:06d}"
            
            # Procesar datos del formulario
            contact_name = request.POST.get("contact", "").strip()
            if not contact_name:
                messages.error(request, "Client name is required")
                return redirect("credit_note_create")
                
            contact = get_or_create_contact(
                user=request.user,
                name=contact_name,
                is_client=True,
                is_supplier=False
            )
            
            # ✅ ACTUALIZAR CONTACTO CON NUEVOS CAMPOS (email, address, cellphone)
            mail = (request.POST.get("email") or "").strip()
            addr = (request.POST.get("address") or "").strip()
            cell = (request.POST.get("cellphone") or "").strip()

            updated = False
            if mail and (contact.email != mail):
                contact.email = mail
                updated = True
            if addr and (getattr(contact, "address", "") != addr):
                contact.address = addr
                updated = True
            if cell and (getattr(contact, "cellphone", "") != cell):
                contact.cellphone = cell
                updated = True
            if updated:
                contact.save(update_fields=["email", "address", "cellphone"])
            
            # Crear credit note (usando modelo Invoice con tipo 'credit_note')
            from decimal import Decimal  # ✅ IMPORTAR DECIMAL AQUÍ TAMBIÉN
            subtotal = Decimal(request.POST.get("subtotal", 0))
            vat_amount = Decimal(request.POST.get("vat_amount", 0))
            total = subtotal + vat_amount
            
            credit_note = Invoice.objects.create(
                user=request.user,
                contact=contact,
                invoice_type="credit_note",
                invoice_number=credit_note_number,
                date=request.POST.get("date"),
                subtotal=subtotal,
                vat_amount=vat_amount,
                total=total,
                summary=(request.POST.get("notes", "") or "").strip()[:200],
                notes=(request.POST.get("notes", "") or "").strip(),
                status="send",
                # ✅ SNAPSHOT del cliente
                client_name=contact.name,
                client_email=mail or contact.email or "",
                client_cellphone=cell or getattr(contact, "cellphone", "") or "",
                client_address=addr or getattr(contact, "address", "") or "",
            )
            
            # ✅ PROCESAR CONCEPTOS CON DESCUENTOS PARA CREDIT NOTE
            descriptions = request.POST.getlist('concept_description[]')
            quantities = request.POST.getlist('concept_quantity[]')
            unit_prices = request.POST.getlist('concept_unit_price[]')
            discount_rates = request.POST.getlist('concept_discount_rate[]')
            discount_amounts = request.POST.getlist('concept_discount_amount[]')
            
            global_vat_rate = Decimal(request.POST.get("vat_rate", "23.0"))
            
            for i in range(len(descriptions)):
                if descriptions[i] and descriptions[i].strip():
                    quantity = quantities[i] if i < len(quantities) and quantities[i] else '1.0'
                    unit_price = unit_prices[i] if i < len(unit_prices) and unit_prices[i] else '0.0'
                    discount_rate = discount_rates[i] if i < len(discount_rates) and discount_rates[i] else '0.0'
                    discount_amount = discount_amounts[i] if i < len(discount_amounts) and discount_amounts[i] else '0.0'
                    
                    InvoiceConcept.objects.create(
                        invoice=credit_note,
                        description=descriptions[i].strip(),
                        quantity=Decimal(quantity),
                        unit_price=Decimal(unit_price),
                        vat_rate=global_vat_rate,
                        discount_rate=Decimal(discount_rate),
                        discount_amount=Decimal(discount_amount)
                    )
            
            # Actualizar contador
            profile.credit_note_count = credit_note_count
            profile.save()
            
            messages.success(request, f"Credit note {credit_note_number} created successfully!")
            return redirect("invoice_list")
            
    except Exception as e:
        error_msg = f"Error creating credit note: {str(e)}"
        messages.error(request, error_msg)
        return redirect("credit_note_create")

# para asuntos del logo

def invoice_detail_view(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id, user=request.user)
    concepts = invoice.concepts.all()
    
    # Contexto original que ya tenías
    original_context = {
        "invoice": invoice,
        "concepts": concepts,
    }
    
    # ✅ PARCHE: Inyecta las variables del logo
    return render(request, "budsidesk_app/dash/invoice/visualize_invoice.html", 
                 inject_logo_context(original_context, request.user))