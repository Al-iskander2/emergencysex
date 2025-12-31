#!/usr/bin/env python
import os
import django
import sys

# Configurar Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'budsi.settings')
django.setup()

from budsi_database.models import Invoice
from django.db import transaction

def backfill_invoice_snapshots():
    """Rellena los campos de snapshot para facturas existentes"""
    invoices = Invoice.objects.select_related('contact').all()
    count = 0
    
    with transaction.atomic():
        for invoice in invoices:
            contact = invoice.contact
            invoice.client_name = contact.name
            invoice.client_email = contact.email or ""
            invoice.client_cellphone = getattr(contact, 'cellphone', '') or ""
            invoice.client_address = getattr(contact, 'address', '') or ""
            invoice.save(update_fields=[
                'client_name', 'client_email', 'client_cellphone', 'client_address'
            ])
            count += 1
            
    print(f"✅ Backfill completado: {count} facturas actualizadas")

if __name__ == '__main__':
    backfill_invoice_snapshots()