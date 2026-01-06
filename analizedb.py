# analyze_emerg_tables.py
import os
import django
import sys
from django.db import connection
from django.core.management.color import color_style

# Configurar entorno Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "emerg_django.settings")
django.setup()

style = color_style()

def list_emerg_tables():
    """Lista todas las tablas emerg_database_* en formato similar a \dt"""
    print(style.SUCCESS("📋 LISTADO DE TABLAS emerg_database_*"))
    print("=" * 80)
    
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                table_name,
                table_type,
                table_schema
            FROM information_schema.tables 
            WHERE table_name LIKE 'emerg_database_%'
            AND table_schema = 'public'
            ORDER BY table_name;
        """)
        
        tables = cursor.fetchall()
    
    # Mostrar en formato similar a \dt
    print(f"{'Esquema':<10} {'Nombre':<40} {'Tipo':<8} {'Dueño'}")
    print("-" * 70)
    
    for schema, name, type in tables:
        # Obtener el dueño de la tabla
        cursor.execute("""
            SELECT tableowner 
            FROM pg_tables 
            WHERE tablename = %s AND schemaname = 'public';
        """, [name])
        owner_result = cursor.fetchone()
        owner = owner_result[0] if owner_result else "?"
        
        print(f"{'public':<10} {name:<40} {'tabla':<8} {owner}")
    
    print(f"({len(tables)} filas)\n")
    return [table[0] for table in tables]

def show_table_structure(table_name):
    """Muestra la estructura de una tabla específica en formato similar a \d"""
    print(style.SUCCESS(f"🛠️  ESTRUCTURA DE: {table_name}"))
    print("-" * 80)
    
    with connection.cursor() as cursor:
        # Obtener columnas con más detalles
        cursor.execute("""
            SELECT 
                column_name,
                data_type,
                character_maximum_length,
                is_nullable,
                column_default
            FROM information_schema.columns 
            WHERE table_name = %s 
            ORDER BY ordinal_position;
        """, [table_name])
        
        columns = cursor.fetchall()
        
        if not columns:
            print("   (tabla vacía o no existe)")
            return
        
        # Mostrar columnas en formato de tabla
        print(f"{'Columna':<25} {'Tipo':<25} {'Nulable':<10} {'Por omisión'}")
        print("-" * 80)
        
        for col_name, data_type, max_length, nullable, default in columns:
            # Formatear el tipo de dato
            if max_length:
                type_display = f"{data_type}({max_length})"
            else:
                type_display = data_type
            
            nullable_display = "Sí" if nullable == 'YES' else "No"
            default_display = default if default else ""
            
            print(f"{col_name:<25} {type_display:<25} {nullable_display:<10} {default_display}")
        
        # Obtener constraints
        print(f"\n🔗 CONSTRAINTS:")
        cursor.execute("""
            SELECT 
                tc.constraint_name,
                tc.constraint_type,
                kcu.column_name
            FROM information_schema.table_constraints tc
            LEFT JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
            WHERE tc.table_name = %s;
        """, [table_name])
        
        constraints = cursor.fetchall()
        
        for const_name, const_type, column_name in constraints:
            if const_type == 'PRIMARY KEY':
                print(f"   • {const_name}: PRIMARY KEY ({column_name})")
            elif const_type == 'FOREIGN KEY':
                print(f"   • {const_name}: FOREIGN KEY ({column_name})")
            elif const_type == 'UNIQUE':
                print(f"   • {const_name}: UNIQUE ({column_name})")
        
        # Obtener índices
        print(f"\n📊 ÍNDICES:")
        cursor.execute("""
            SELECT 
                indexname,
                indexdef
            FROM pg_indexes 
            WHERE tablename = %s AND schemaname = 'public';
        """, [table_name])
        
        indexes = cursor.fetchall()
        
        for idx_name, idx_def in indexes:
            # Simplificar la definición del índice para mejor lectura
            simple_def = idx_def.replace('CREATE ', '').replace('INDEX ', '').replace('ON public.', 'ON ')
            print(f"   • {simple_def}")

def show_table_content(table_name, limit=3):
    """Muestra el contenido de una tabla"""
    with connection.cursor() as cursor:
        # Contar registros
        cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
        count = cursor.fetchone()[0]
        
        print(f"\n📈 CONTENIDO: {table_name} ({count} registros)")
        
        if count == 0:
            print("   (tabla vacía)")
            return
        
        # Obtener nombres de columnas
        cursor.execute(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = %s 
            ORDER BY ordinal_position;
        """, [table_name])
        
        column_names = [col[0] for col in cursor.fetchall()]
        
        # Obtener datos de ejemplo
        cursor.execute(f"SELECT * FROM {table_name} LIMIT {limit};")
        rows = cursor.fetchall()
        
        # Mostrar columnas
        print(f"   Columnas: {', '.join(column_names)}")
        print(f"   Primeros {len(rows)} registros:")
        
        for i, row in enumerate(rows):
            formatted_values = []
            for value in row:
                if value is None:
                    formatted_values.append("NULL")
                elif isinstance(value, str) and len(value) > 30:
                    formatted_values.append(f"'{value[:30]}...'")
                elif isinstance(value, (int, float)):
                    formatted_values.append(str(value))
                else:
                    formatted_values.append(f"'{str(value)}'")
            
            print(f"     [{i+1}] {', '.join(formatted_values)}")
        
        if count > limit:
            print(f"     ... y {count - limit} más")

def analyze_all_emerg_tables():
    """Analiza todas las tablas emerg_database_*"""
    print(style.SUCCESS("🚀 ANÁLISIS COMPLETO DE TABLAS emerg_database_*"))
    print("=" * 80)
    
    # 1. Listar todas las tablas
    emerg_tables = list_emerg_tables()
    
    # 2. Analizar cada tabla en detalle
    for table in emerg_tables:
        show_table_structure(table)
        show_table_content(table)
        print("\n" + "=" * 80)

def check_data_relationships():
    """Verifica relaciones entre tablas y datos relacionados"""
    print(style.SUCCESS("\n🔗 RELACIONES ENTRE TABLAS"))
    print("=" * 80)
    
    # Verificar relaciones comunes
    relationships = [
        ("emerg_database_invoice", "emerg_database_invoiceconcept", "invoice_id"),
        ("emerg_database_user", "emerg_database_invoice", "user_id"),
        ("emerg_database_user", "emerg_database_contact", "user_id"),
        ("emerg_database_user", "emerg_database_project", "user_id"),
    ]
    
    for table1, table2, key_field in relationships:
        with connection.cursor() as cursor:
            # Verificar si table2 existe
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = %s
                );
            """, [table2])
            
            if cursor.fetchone()[0]:
                cursor.execute(f"""
                    SELECT COUNT(*) 
                    FROM {table1} t1
                    WHERE EXISTS (
                        SELECT 1 FROM {table2} t2 
                        WHERE t2.{key_field} = t1.id
                    );
                """)
                related_count = cursor.fetchone()[0]
                
                cursor.execute(f"SELECT COUNT(*) FROM {table1};")
                total_count = cursor.fetchone()[0]
                
                print(f"   {table1} -> {table2}: {related_count}/{total_count} registros relacionados")
            else:
                print(f"   {table1} -> {table2}: {style.ERROR('tabla no existe')}")

def main():
    """Función principal"""
    try:
        # 1. Análisis completo de tablas
        analyze_all_emerg_tables()
        
        # 2. Verificar relaciones
        check_data_relationships()
        
        # 3. Resumen final
        print(style.SUCCESS("\n✅ ANÁLISIS COMPLETADO"))
        print("=" * 80)
        
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name LIKE 'emerg_database_%';")
            table_count = cursor.fetchone()[0]
            
            total_records = 0
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name LIKE 'emerg_database_%';
            """)
            
            for table in cursor.fetchall():
                table_name = table[0]
                cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
                count = cursor.fetchone()[0]
                total_records += count
            
            print(f"📊 Resumen:")
            print(f"   • Tablas analizadas: {table_count}")
            print(f"   • Registros totales: {total_records}")
            
    except Exception as e:
        print(style.ERROR(f"❌ Error durante el análisis: {e}"))
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()