# logic/create_contact.py
import re
import time
from django.db import IntegrityError
from django.utils.text import slugify
from django.db.models import Count, Sum, Q
from datetime import datetime, timedelta
from emerg_database.models import Contact, Invoice

def get_or_create_contact(*, user, name, is_supplier=False, is_client=True, email=None, tax_id=None):
    """Servicio unificado para crear/obtener contactos - VERSIÓN MEJORADA"""
    if not name or not name.strip():
        name = "Unknown Contact"
    
    name = name.strip()
    
    # ✅ CORRECCIÓN ROBUSTA: Manejar tax_id vacío, None, o solo espacios
    if tax_id is None or (isinstance(tax_id, str) and not tax_id.strip()):
        base_tax_id = f"temp-{slugify(name)}-{user.id}"
        tax_id = base_tax_id
        print(f"🆔 Generando tax_id temporal: {tax_id}")
    elif isinstance(tax_id, str):
        tax_id = tax_id.strip()
        print(f"🆔 Usando tax_id proporcionado: {tax_id}")
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            contact, created = Contact.objects.get_or_create(
                user=user,
                tax_id=tax_id,
                defaults={
                    "name": name,
                    "is_supplier": is_supplier,
                    "is_client": is_client,
                    "email": email or "",
                    "is_favorite": True  # ✅ Nuevos contactos son favoritos por defecto
                }
            )
            if created:
                print(f"✅ Nuevo contacto creado: {name} (tax_id: {tax_id})")
            else:
                print(f"✅ Contacto existente recuperado: {name} (tax_id: {tax_id})")
            return contact
            
        except IntegrityError as e:
            print(f"🔄 Intento {attempt + 1} falló: {e}")
            if attempt < max_retries - 1:
                # Intentar con timestamp diferente
                tax_id = f"{base_tax_id}-{int(time.time() * 1000) + attempt}"
                print(f"🔄 Reintentando con tax_id: {tax_id}")
                continue
            else:
                # Último intento
                tax_id = f"{base_tax_id}-{int(time.time() * 1000)}-final"
                print(f"🔄 Último intento con tax_id: {tax_id}")
                contact = Contact.objects.create(
                    user=user,
                    name=name,
                    tax_id=tax_id,
                    is_supplier=is_supplier,
                    is_client=is_client,
                    email=email or "",
                    is_favorite=True  # ✅ Nuevos contactos son favoritos
                )
                return contact

# ============================================================================
# NUEVAS FUNCIONES DE GESTIÓN DE CONTACTOS (integradas aquí)
# ============================================================================

def get_contact_stats(user, contact_id=None):
    """Obtener estadísticas de contactos/clientes"""
    contacts = Contact.objects.filter(user=user, is_client=True)
    
    if contact_id:
        contacts = contacts.filter(id=contact_id)
    
    stats = []
    for contact in contacts:
        # Facturas del contacto
        invoices = Invoice.objects.filter(
            user=user, 
            contact=contact, 
            invoice_type="sale",
            is_confirmed=True
        )
        
        total_invoiced = invoices.aggregate(total=Sum('total'))['total'] or 0
        paid_invoices = invoices.filter(status="paid")
        total_paid = paid_invoices.aggregate(total=Sum('total'))['total'] or 0
        overdue_invoices = invoices.filter(status="overdue")
        total_overdue = overdue_invoices.aggregate(total=Sum('total'))['total'] or 0
        
        stats.append({
            'contact': contact,
            'total_invoiced': float(total_invoiced),
            'total_paid': float(total_paid),
            'total_overdue': float(total_overdue),
            'invoice_count': invoices.count(),
            'paid_count': paid_invoices.count(),
            'overdue_count': overdue_invoices.count(),
            'payment_ratio': (total_paid / total_invoiced * 100) if total_invoiced > 0 else 0
        })
    
    return stats

def get_top_customers(user, limit=5):
    """Obtener los mejores clientes por facturación"""
    top_customers = Contact.objects.filter(
        user=user, 
        is_client=True,
        invoices__invoice_type="sale",
        invoices__is_confirmed=True
    ).annotate(
        total_spent=Sum('invoices__total'),
        invoice_count=Count('invoices')
    ).order_by('-total_spent')[:limit]
    
    return [
        {
            'contact': customer,
            'total_spent': float(customer.total_spent or 0),
            'invoice_count': customer.invoice_count
        }
        for customer in top_customers
    ]

def toggle_contact_favorite(user, contact_id):
    """Alternar estado de favorito de un contacto"""
    try:
        contact = Contact.objects.get(id=contact_id, user=user)
        contact.is_favorite = not contact.is_favorite
        contact.save()
        return {'success': True, 'is_favorite': contact.is_favorite}
    except Contact.DoesNotExist:
        return {'success': False, 'error': 'Contacto no encontrado'}