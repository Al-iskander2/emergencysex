# logic/normalize_project.py
import re
from unidecode import unidecode
from django.db.models import Sum, Count, Q
from datetime import datetime, timedelta
from budsi_database.models import Project, Invoice

def clean_project_name(raw: str) -> str:
    """Normaliza nombres de proyecto para consistencia"""
    if not raw or not isinstance(raw, str):
        return ''
    
    # 1. Minúsculas y strip
    name = raw.lower().strip()
    
    # 2. Remover acentos y caracteres especiales
    name = unidecode(name)
    
    # 3. Remover caracteres no alfanuméricos (excepto espacios y guiones)
    name = re.sub(r'[^a-z0-9\s-]', '', name)
    
    # 4. Colapsar espacios múltiples
    name = re.sub(r'\s+', ' ', name)
    
    # 5. Capitalizar palabras
    name = name.title()
    
    # 6. Limitar longitud
    return name[:190]

# ============================================================================
# NUEVAS FUNCIONES DE GESTIÓN DE PROYECTOS (integradas aquí)
# ============================================================================

def create_project_for_user(user, name, description="", start_date=None, end_date=None):
    """Crear proyecto con nombre normalizado"""
    normalized_name = clean_project_name(name)
    
    if not start_date:
        start_date = datetime.now().date()
    if not end_date:
        end_date = start_date + timedelta(days=30)  # Default 30 días
    
    project = Project.objects.create(
        user=user,
        name=normalized_name,
        description=description,
        start_date=start_date,
        end_date=end_date,
        is_active=True
    )
    return project

def get_project_performance(user, project_id=None):
    """Obtener rendimiento de proyectos"""
    projects = Project.objects.filter(user=user)
    
    if project_id:
        projects = projects.filter(id=project_id)
    
    performance_data = []
    for project in projects:
        # Ventas del proyecto
        sales = Invoice.objects.filter(
            user=user,
            project=project,
            invoice_type="sale",
            is_confirmed=True
        )
        
        # Gastos del proyecto
        expenses = Invoice.objects.filter(
            user=user,
            project=project,
            invoice_type="purchase", 
            is_confirmed=True
        )
        
        total_sales = sales.aggregate(total=Sum('total'))['total'] or 0
        total_expenses = expenses.aggregate(total=Sum('total'))['total'] or 0
        net_profit = total_sales - total_expenses
        
        # Calcular progreso basado en tiempo
        today = datetime.now().date()
        total_days = (project.end_date - project.start_date).days
        days_passed = (today - project.start_date).days
        progress = min(100, max(0, int((days_passed / total_days) * 100))) if total_days > 0 else 0
        
        performance_data.append({
            'project': project,
            'total_sales': float(total_sales),
            'total_expenses': float(total_expenses),
            'net_profit': float(net_profit),
            'sales_count': sales.count(),
            'expenses_count': expenses.count(),
            'progress': progress,
            'is_on_track': progress <= 100  # Proyecto en plazo
        })
    
    return performance_data

def get_project_timeline(user, days=30):
    """Obtener línea de tiempo de proyectos"""
    from_date = datetime.now().date() - timedelta(days=days)
    
    projects = Project.objects.filter(
        user=user,
        start_date__gte=from_date
    ).order_by('start_date')
    
    timeline = []
    for project in projects:
        timeline.append({
            'project': project,
            'type': 'start',
            'date': project.start_date,
            'title': f"Inicio: {project.name}",
            'description': project.description
        })
        
        if project.end_date:
            timeline.append({
                'project': project,
                'type': 'end', 
                'date': project.end_date,
                'title': f"Fin: {project.name}",
                'description': f"Fecha límite del proyecto"
            })
    
    # Ordenar por fecha
    timeline.sort(key=lambda x: x['date'])
    return timeline