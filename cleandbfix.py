# cleandb_fixed.py - VERSIÓN CORREGIDA
import os
import django
import sys
from django.apps import apps
from django.contrib.auth import get_user_model
from django.db import connection

# Configurar entorno Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "emerg_django.settings")
django.setup()

User = get_user_model()

def verify_and_confirm():
    """Verificación extra de seguridad con confirmación del usuario"""
    print("🔐 VERIFICACIÓN DE SEGURIDAD")
    print("=" * 50)
    
    # Mostrar superusuarios
    superusers = User.objects.filter(is_superuser=True)
    print("👑 SUPERUSUARIOS QUE SERÁN PRESERVADOS:")
    for user in superusers:
        print(f"   • {user.email} (desde: {user.date_joined.date()})")
    
    if not superusers.exists():
        print("⚠️  ¡ADVERTENCIA! No hay superusuarios en el sistema")
    
    # Mostrar estadísticas de datos a eliminar
    print("\n📊 DATOS QUE SERÁN ELIMINADOS:")
    models_to_clean = ['Invoice', 'Contact', 'FiscalProfile', 'Project', 'InvoiceConcept', 'TaxPeriod', 'FiscalConfig']
    for model_name in models_to_clean:
        try:
            model = apps.get_model('emerg_database', model_name)
            count = model.objects.count()
            print(f"   • {model_name}: {count} registros")
        except Exception as e:
            print(f"   • {model_name}: No disponible - {e}")
    
    # Confirmación del usuario
    print("\n" + "=" * 50)
    confirm = input("¿ESTÁS SEGURO de que quieres continuar? (escribe 'SI' para confirmar): ")
    
    if confirm != 'SI':
        print("❌ Operación cancelada por el usuario")
        sys.exit(0)
    
    return list(superusers)

def purge_with_sql():
    """Limpieza usando SQL directo para evitar problemas del ORM"""
    print("\n🛠️  INICIANDO LIMPIEZA CON SQL DIRECTO")
    print("--------------------------------------------------")
    
    # ORDEN CORRECTO basado en dependencias
    tables = [
        'emerg_database_invoiceconcept',  # Primero las líneas de factura
        'emerg_database_invoice',         # Luego las facturas
        'emerg_database_taxperiod',
        'emerg_database_fiscalconfig', 
        'emerg_database_project',
        'emerg_database_contact', 
        'emerg_database_fiscalprofile'
    ]
    
    deleted_total = 0
    with connection.cursor() as cursor:
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                if count > 0:
                    print(f"🗑️  Eliminando {count} registros de {table}...")
                    cursor.execute(f"DELETE FROM {table}")
                    deleted_total += count
            except Exception as e:
                print(f"⚠️  Error con {table}: {e}")
    
    # Eliminar usuarios normales
    normal_users = User.objects.filter(is_superuser=False)
    user_count = normal_users.count()
    if user_count:
        print(f"🧍 Eliminando {user_count} usuario(s) normales...")
        for user in normal_users:
            print(f"   • {user.email} (normal user)")
        normal_users.delete()
        deleted_total += user_count
    
    print(f"\n🎉 LIMPIEZA COMPLETA: {deleted_total} registros eliminados")
    print("--------------------------------------------------")

def main():
    """Función principal - VERSIÓN CORREGIDA"""
    print("🚀 INICIANDO LIMPIEZA DE BASE DE DATOS (VERSIÓN CORREGIDA)")
    print("=" * 60)
    
    # VERIFICACIÓN DE SEGURIDAD
    superusers = verify_and_confirm()
    
    # Proceder con la limpieza SQL
    try:
        purge_with_sql()
        print("✅ Base de datos limpiada exitosamente")
        
        # Verificar resultado
        print("\n📋 VERIFICACIÓN FINAL:")
        models_to_check = ['Invoice', 'Contact', 'FiscalProfile', 'Project', 'InvoiceConcept']
        for model_name in models_to_check:
            try:
                model = apps.get_model('emerg_database', model_name)
                count = model.objects.count()
                print(f"   • {model_name}: {count} registros restantes")
            except:
                print(f"   • {model_name}: No disponible")
                
        user_count = User.objects.count()
        superuser_count = User.objects.filter(is_superuser=True).count()
        print(f"   • Usuarios totales: {user_count} ({superuser_count} superusuarios)")
        
    except Exception as e:
        print(f"❌ Error limpiando base de datos: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()