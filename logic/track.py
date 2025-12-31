# logic/track.py
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from django.db.models import Sum
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from decimal import Decimal
from budsi_database.models import Project, Invoice

@dataclass
class ProjectCard:
    project: Any
    earned: float
    spent: float
    profit: float
    progress: int
    sales_count: int
    purchases_count: int

def _progress_pct(start, end, today):
    try:
        total = (end - start).days or 1
        done = (today - start).days
        pct = int(max(0, min(100, round((done/total)*100))))
        return pct
    except Exception:
        return 0

def get_tracker_context(user) -> Dict[str, Any]:
    """
    Returns exactly what the track.html template consumes.
    """
    today = timezone.localdate()
    month_name = today.strftime("%B %Y")

    projects = Project.objects.filter(user=user).order_by("-is_active", "start_date")

    projects_data: List[ProjectCard] = []
    total_earned = 0.0
    total_spent = 0.0

    for p in projects:
        # ✅ CORREGIDO: Usar p.name en lugar de p (porque Invoice.project es CharField)
        sales_qs = Invoice.objects.filter(
            user=user, 
            invoice_type="sale", 
            project=p.name,  # ← CORRECCIÓN CRÍTICA
            is_confirmed=True
        )
        purch_qs = Invoice.objects.filter(
            user=user, 
            invoice_type="purchase", 
            project=p.name,  # ← CORRECCIÓN CRÍTICA  
            is_confirmed=True
        )

        earned = float(sales_qs.aggregate(s=Sum("total"))["s"] or 0)
        spent = float(purch_qs.aggregate(s=Sum("total"))["s"] or 0)
        profit = earned - spent

        sales_count = sales_qs.count()
        purchases_count = purch_qs.count()
        progress = _progress_pct(p.start_date, p.end_date, today)

        total_earned += earned
        total_spent += spent

        projects_data.append(
            ProjectCard(
                project=p,
                earned=earned,
                spent=spent,
                profit=profit,
                progress=progress,
                sales_count=sales_count,
                purchases_count=purchases_count,
            )
        )

    net_profit = total_earned - total_spent

    # Most Profitable Project
    profitable_project: Optional[ProjectCard] = None
    if projects_data:
        profitable_project = max(projects_data, key=lambda x: x.profit)

    ctx = {
        "active_projects_count": projects.filter(is_active=True).count(),
        "total_earned": total_earned,
        "total_spent": total_spent,
        "net_profit": net_profit,
        "projects_data": [vars(x) for x in projects_data],
        "profitable_project": vars(profitable_project) if profitable_project else None,
        "current_month": month_name,
    }
    return ctx

def create_project(user, *, name: str, description: str, start_date, end_date):
    """Create a new project"""
    p = Project.objects.create(
        user=user, 
        name=name.strip(), 
        description=description or "",
        start_date=start_date, 
        end_date=end_date, 
        is_active=True
    )
    return p

def toggle_project_status(user, project_id: int) -> Dict[str, Any]:
    """Toggle project active status"""
    p = Project.objects.get(id=project_id, user=user)
    p.is_active = not p.is_active
    p.save(update_fields=["is_active"])
    return {"project_id": p.id, "is_active": p.is_active}
# Django Views
@login_required
def track_view(request):
    """Main track view"""
    context = get_tracker_context(request.user)
    return render(request, "budsidesk_app/dash/track/main_track.html", context)

@login_required
def create_project_view(request):
    """Create new project view"""
    if request.method == 'POST':
        try:
            name = request.POST.get('project_name')
            description = request.POST.get('project_description')
            start_date = request.POST.get('start_date')
            end_date = request.POST.get('end_date')
            
            if not all([name, start_date, end_date]):
                messages.error(request, "All fields are required")
                return redirect('main_track')  # ✅ CORREGIDO: 'main_track' en lugar de 'track_view'
                
            # Check if project with same name already exists for this user
            if Project.objects.filter(user=request.user, name=name.strip()).exists():
                messages.error(request, "A project with this name already exists")
                return redirect('main_track')  # ✅ CORREGIDO
            
            create_project(
                user=request.user,
                name=name,
                description=description,
                start_date=start_date,
                end_date=end_date
            )
            messages.success(request, "Project created successfully")
            return redirect('main_track')  # ✅ CORREGIDO
            
        except Exception as e:
            messages.error(request, f"Error creating project: {str(e)}")
            return redirect('main_track')  # ✅ CORREGIDO
    
    # If not POST, show the form
    return render(request, "budsidesk_app/dash/track/main_track.html", get_tracker_context(request.user))

@login_required
def toggle_project_status_view(request, project_id):
    """Toggle project active/inactive status"""
    try:
        result = toggle_project_status(request.user, project_id)
        status = "activated" if result["is_active"] else "archived"
        messages.success(request, f"Project {status} successfully")
        return redirect('main_track')  # ✅ CORREGIDO
    except Project.DoesNotExist:
        messages.error(request, "Project not found")
        return redirect('main_track')  # ✅ CORREGIDO
    except Exception as e:
        messages.error(request, f"Error updating project status: {str(e)}")
        return redirect('main_track')  # ✅ CORREGIDO

@login_required
def update_project_dates_view(request, project_id):
    """Update project dates from the modal"""
    if request.method == 'POST':
        try:
            project = Project.objects.get(id=project_id, user=request.user)
            start_date = request.POST.get('start_date')
            end_date = request.POST.get('end_date')
            
            if start_date and end_date:
                project.start_date = start_date
                project.end_date = end_date
                project.save()
                messages.success(request, "Project dates updated successfully")
            else:
                messages.error(request, "Start date and end date are required")
                
        except Project.DoesNotExist:
            messages.error(request, "Project not found")
        except Exception as e:
            messages.error(request, f"Error updating project dates: {str(e)}")
    
    return redirect('main_track')  # ✅ CORREGIDO

def ensure_project(user, project_name: str):
    """
    Ensure a project exists for the user.
    If it doesn't exist, create it with default dates.
    Used when creating invoices to auto-create projects.
    """
    if not project_name or not project_name.strip():
        return None
        
    name = project_name.strip()
    
    # Try to get existing project
    try:
        project = Project.objects.get(user=user, name=name)
        return project
    except Project.DoesNotExist:
        # Create new project with default dates (today to 30 days from now)
        start_date = timezone.now().date()
        end_date = start_date + timezone.timedelta(days=30)
        
        project = Project.objects.create(
            user=user,
            name=name,
            description=f"Project created from invoice: {name}",
            start_date=start_date,
            end_date=end_date,
            is_active=True
        )
        return project