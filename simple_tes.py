#!/usr/bin/env python
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'budsi_django.settings')
django.setup()

print("=== TEST SIMPLE DEL SISTEMA ===")

# Test básico de imports
try:
    from budsi_database.models import User, Invoice
    from budsi_django.forms import InvoiceForm
    print("✅ Importaciones básicas: OK")
    
    # Test de conexión a BD
    user_count = User.objects.count()
    print(f"✅ Conexión BD: OK ({user_count} usuarios)")
    
    # Test de formulario
    form = InvoiceForm()
    print("✅ Formulario InvoiceForm: OK")
    
    print("\n🎯 SISTEMA FUNCIONANDO CORRECTAMENTE")
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()