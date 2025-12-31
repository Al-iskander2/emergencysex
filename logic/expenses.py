# logic/expenses.py - FULL UPDATED VERSION WITH DISCOUNTS
import time
import random
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.contrib import messages
from django.db.models import Sum
from django.utils import timezone
from django.urls import reverse
from django.db import transaction

from logic.invoice_service import InvoiceService
from logic.create_contact import get_or_create_contact
from logic.track import ensure_project
from budsi_database.models import Invoice, InvoiceConcept, FiscalProfile
import json


def generate_unique_expense_number(user):
    """Generates a unique number for expenses with milliseconds and random suffix"""
    timestamp = int(time.time() * 1000)
    random_suffix = random.randint(1000, 9999)
    return f"EXP-{timestamp}-{user.id}-{random_suffix}"


@login_required
def expense_list_view(request):
    """✅ Expenses list - IMPROVED VERSION"""
    expenses = (
        Invoice.objects
        .filter(user=request.user, invoice_type="purchase")
        .select_related("contact")
        .prefetch_related("concepts")
        .order_by("-date", "-id")
    )

    # Calculate metrics
    total_expenses = expenses.aggregate(total=Sum('total'))['total'] or 0
    total_vat = expenses.aggregate(total=Sum('vat_amount'))['total'] or 0
    total_net = expenses.aggregate(total=Sum('subtotal'))['total'] or 0

    # Current month expenses
    now = timezone.now()
    month_expenses = expenses.filter(
        date__month=now.month,
        date__year=now.year
    ).aggregate(total=Sum('total'))['total'] or 0

    # Average per expense
    count = expenses.count()
    avg_expense = total_expenses / count if count else 0

    context = {
        "expenses": expenses,
        "confirmed_count": expenses.filter(is_confirmed=True).count(),
        "pending_count": expenses.filter(is_confirmed=False).count(),
        "total_expenses": total_expenses,
        "total_vat": total_vat,
        "total_net": total_net,
        "month_expenses": month_expenses,
        "avg_expense": avg_expense,
    }

    return render(request, "budsidesk_app/dash/expenses/main_expenses.html", context)


@login_required
@require_POST
def expense_upload_view(request):
    """✅ Upload expense via OCR"""
    if not request.FILES.get("file"):
        messages.error(request, "No file was provided")
        return redirect("expense_list")

    try:
        file = request.FILES["file"]
        invoice = InvoiceService.create_expense_from_ocr(request.user, file)

        messages.success(request, f"Expense from {invoice.contact.name} processed successfully!")
        return redirect("invoice_preview", invoice_id=invoice.id)

    except Exception as e:
        error_msg = f"Error processing file: {str(e)}"
        messages.error(request, error_msg)
        return redirect("expense_list")


@login_required
@require_GET
def expense_create_manual_view(request):
    """✅ View to manually create an expense - FULL FORM"""
    try:
        profile = FiscalProfile.objects.get(user=request.user)
    except FiscalProfile.DoesNotExist:
        messages.error(request, "Please complete your tax profile first")
        return redirect("onboarding")

    return render(request, "budsidesk_app/dash/expenses/create_expense.html", {
        'profile': profile,
    })


@login_required
@require_POST
def expense_save_manual_view(request):
    """✅ Save manual expense WITH LINE DISCOUNTS - FULL VERSION"""
    try:
        with transaction.atomic():
            supplier_name = (request.POST.get("supplier") or "").strip()

            if not supplier_name:
                messages.error(request, "Supplier name is required")
                return redirect("expense_create_manual")

            # Create contact as SUPPLIER
            contact = get_or_create_contact(
                user=request.user,
                name=supplier_name,
                is_supplier=True,
                is_client=False
            )

            # ✅ UPDATE CONTACT WITH NEW FIELDS
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

            expense_number = generate_unique_expense_number(request.user)

            # ✅ Ensure project exists
            project_name = request.POST.get("project", "").strip()
            if project_name:
                project = ensure_project(request.user, project_name)

            # Process amounts from concepts (will be calculated automatically)
            from decimal import Decimal
            subtotal = Decimal(request.POST.get("subtotal", 0))
            vat_amount = Decimal(request.POST.get("vat_amount", 0))
            total = subtotal + vat_amount

            # ✅ CREATE EXPENSE WITH SUPPLIER SNAPSHOT
            invoice = Invoice.objects.create(
                user=request.user,
                contact=contact,
                invoice_type="purchase",
                invoice_number=expense_number,
                date=request.POST.get("date") or timezone.now().date(),
                subtotal=subtotal,
                vat_amount=vat_amount,
                total=total,
                summary=(request.POST.get("notes", "") or "").strip()[:200],
                category=request.POST.get("category", ""),
                project=project_name,
                is_confirmed=True,
                status="draft",
                # ✅ Supplier snapshot
                client_name=contact.name,
                client_email=mail or contact.email or "",
                client_cellphone=cell or getattr(contact, "cellphone", "") or "",
                client_address=addr or getattr(contact, "address", "") or "",
            )

            # ✅ PROCESS CONCEPTS WITH DISCOUNTS
            descriptions = request.POST.getlist('concept_description[]')
            quantities = request.POST.getlist('concept_quantity[]')
            unit_prices = request.POST.getlist('concept_unit_price[]')
            discount_rates = request.POST.getlist('concept_discount_rate[]')
            discount_amounts = request.POST.getlist('concept_discount_amount[]')

            # ✅ Use global VAT rate
            global_vat_rate = Decimal(request.POST.get("vat_rate", "23.0"))

            concepts_created = 0
            for i in range(len(descriptions)):
                if descriptions[i] and descriptions[i].strip():
                    quantity = quantities[i] if i < len(quantities) and quantities[i] else '1.0'
                    unit_price = unit_prices[i] if i < len(unit_prices) and unit_prices[i] else '0.0'
                    discount_rate = discount_rates[i] if i < len(discount_rates) and discount_rates[i] else '0.0'
                    discount_amount = discount_amounts[i] if i < len(discount_amounts) and discount_amounts[i] else '0.0'

                    # Create concept with discounts
                    InvoiceConcept.objects.create(
                        invoice=invoice,
                        description=descriptions[i].strip(),
                        quantity=Decimal(quantity),
                        unit_price=Decimal(unit_price),
                        vat_rate=global_vat_rate,
                        discount_rate=Decimal(discount_rate),
                        discount_amount=Decimal(discount_amount)
                    )
                    concepts_created += 1

            print(f"✅ Created {concepts_created} concepts for expense {expense_number}")

            messages.success(request, f"Expense {invoice.invoice_number} created successfully!")
            return redirect("expense_list")

    except Exception as e:
        error_msg = f"Error creating expense: {str(e)}"
        print(f"❌ {error_msg}")
        import traceback
        print(f"🔍 Stack trace: {traceback.format_exc()}")

        messages.error(request, error_msg)
        return redirect("expense_create_manual")


@login_required
def expense_preview_view(request, invoice_id):
    """✅ Expense preview after OCR - UPDATED VERSION WITH CONCEPTS"""
    invoice = get_object_or_404(Invoice, id=invoice_id, user=request.user)

    # Get existing concepts
    concepts = invoice.concepts.all()

    # Get existing projects for autocomplete
    existing_projects = Invoice.objects.filter(
        user=request.user
    ).exclude(project__isnull=True).exclude(project='').values_list('project', flat=True).distinct()

    if request.method == "POST":
        try:
            with transaction.atomic():
                # Update invoice with form values
                invoice.subtotal = Decimal(request.POST.get("subtotal", invoice.subtotal) or 0)
                invoice.vat_amount = Decimal(request.POST.get("vat_amount", invoice.vat_amount) or 0)
                invoice.total = Decimal(request.POST.get("total", invoice.total) or 0)
                invoice.category = request.POST.get("category", "")
                invoice.project = request.POST.get("project", "")

                # Update contact (supplier)
                supplier_name = request.POST.get("supplier", "").strip()
                if supplier_name and supplier_name != invoice.contact.name:
                    contact = get_or_create_contact(
                        user=request.user,
                        name=supplier_name,
                        is_supplier=True,
                        is_client=False
                    )
                    invoice.contact = contact

                # ✅ UPDATE SUPPLIER SNAPSHOT
                mail = (request.POST.get("email") or "").strip()
                addr = (request.POST.get("address") or "").strip()
                cell = (request.POST.get("cellphone") or "").strip()

                invoice.client_name = supplier_name or invoice.contact.name
                invoice.client_email = mail or invoice.contact.email or ""
                invoice.client_cellphone = cell or getattr(invoice.contact, "cellphone", "") or ""
                invoice.client_address = addr or getattr(invoice.contact, "address", "") or ""

                if "confirm" in request.POST:
                    invoice.is_confirmed = True

                invoice.save()

                # ✅ UPDATE EXISTING CONCEPTS OR CREATE NEW ONES
                if concepts.exists():
                    # Update existing concepts
                    descriptions = request.POST.getlist('concept_description[]')
                    quantities = request.POST.getlist('concept_quantity[]')
                    unit_prices = request.POST.getlist('concept_unit_price[]')
                    discount_rates = request.POST.getlist('concept_discount_rate[]')
                    discount_amounts = request.POST.getlist('concept_discount_amount[]')

                    for i, concept in enumerate(concepts):
                        if i < len(descriptions):
                            concept.description = descriptions[i].strip()
                            concept.quantity = Decimal(quantities[i] if quantities[i] else '1.0')
                            concept.unit_price = Decimal(unit_prices[i] if unit_prices[i] else '0.0')
                            concept.discount_rate = Decimal(discount_rates[i] if discount_rates[i] else '0.0')
                            concept.discount_amount = Decimal(discount_amounts[i] if discount_amounts[i] else '0.0')
                            concept.save()

                messages.success(request, "Expense confirmed successfully!")
                return redirect("expense_list")

        except Exception as e:
            messages.error(request, f"Error updating expense: {str(e)}")

    original_url = invoice.original_file.url if invoice.original_file else None
    is_pdf = (original_url or "").lower().endswith(".pdf")

    return render(request, "budsidesk_app/dash/expenses/preview_purchase.html", {
        "invoice": invoice,
        "concepts": concepts,
        "original_url": original_url,
        "is_pdf": is_pdf,
        "existing_projects": existing_projects
    })


@login_required
def invoice_gallery_view(request, invoice_id):
    """✅ Invoice gallery - FULL VERSION"""
    invoice = get_object_or_404(Invoice, id=invoice_id, user=request.user)

    # Get previous and next invoices
    prev_invoice = (
        Invoice.objects.filter(user=request.user, id__lt=invoice.id)
        .order_by("-id")
        .first()
    )
    next_invoice = (
        Invoice.objects.filter(user=request.user, id__gt=invoice.id)
        .order_by("id")
        .first()
    )

    return render(
        request,
        "budsidesk_app/dash/expenses/invoice_gallery.html",
        {
            "invoice": invoice,
            "prev_invoice": prev_invoice,
            "next_invoice": next_invoice,
        },
    )


@login_required
@require_POST
def expense_update_status_view(request, invoice_id):
    """✅ Update expense status via AJAX"""
    try:
        invoice = get_object_or_404(Invoice, id=invoice_id, user=request.user)
        data = json.loads(request.body)
        new_status = data.get("status")

        if new_status not in ["draft", "sent", "paid", "overdue", "cancelled"]:
            return JsonResponse({"success": False, "error": "Invalid status"}, status=400)

        success = InvoiceService.update_invoice_status(invoice, new_status)
        if success:
            return JsonResponse({"success": True, "new_status": new_status})
        else:
            return JsonResponse({"success": False, "error": "Error updating status"}, status=400)

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


# ========== WRAPPERS FOR COMPATIBILITY ==========

@login_required
def invoice_preview_view(request, invoice_id):
    """Wrapper: URL expects 'invoice_preview_view'."""
    return expense_preview_view(request, invoice_id)


@login_required
@require_POST
def expenses_upload_view(request):
    """Wrapper: views/urls expect 'expenses_upload_view'."""
    return expense_upload_view(request)


@login_required
def expenses_create_view(request):
    """Wrapper: views/urls expect 'expenses_create_view'."""
    return expense_create_manual_view(request)


@login_required
@require_POST
def expenses_save_view(request):
    """Wrapper: views/urls expect 'expenses_save_view'."""
    return expense_save_manual_view(request)


@login_required
def general_upload(request):
    """Compat: /upload/ endpoint reuses expenses flow."""
    return expenses_upload_view(request)


@login_required
@require_POST
def invoice_upload_view(request):
    """Upload via OCR and then redirect to preview"""
    if not request.FILES.get("file"):
        messages.error(request, "No file was provided")
        return redirect("expense_list")
    try:
        file = request.FILES["file"]
        invoice = InvoiceService.create_expense_from_ocr(request.user, file)

        messages.success(request, "Invoice processed successfully!")
        return redirect("invoice_preview", invoice_id=invoice.id)
    except Exception as e:
        messages.error(request, f"Error processing file: {str(e)}")
        return redirect("expense_list")


@login_required
def visualize_expense_view(request, invoice_id):
    """✅ View for expense visualization - COMPATIBILITY"""
    return expense_preview_view(request, invoice_id)


@login_required
def expense_detail_view(request, invoice_id):
    """✅ View expense detail with its concepts"""
    invoice = get_object_or_404(Invoice, id=invoice_id, user=request.user)
    concepts = invoice.concepts.all()

    return render(request, "budsidesk_app/dash/expenses/expense_detail.html", {
        "invoice": invoice,
        "concepts": concepts,
    })


@login_required
@require_POST
def expense_delete_view(request, invoice_id):
    """✅ Delete an expense (Invoice)"""
    invoice = get_object_or_404(Invoice, id=invoice_id, user=request.user)
    try:
        invoice_number = invoice.invoice_number
        invoice.delete()
        messages.success(request, f"Expense {invoice_number} deleted successfully!")
    except Exception as e:
        messages.error(request, f"Error deleting expense: {str(e)}")

    return redirect("expense_list")


# ✅ Also add wrapper for compatibility
@login_required
@require_POST
def expenses_delete_view(request, invoice_id):
    """Wrapper: views/urls expect 'expenses_delete_view'."""
    return expense_delete_view(request, invoice_id)

def get_cash_out_for_period(user, days: int = 30):
    """
    Devuelve (queryset, total) de gastos (CASH OUT) para Pulse.
    """
    today = timezone.now().date()
    start_date = today - timedelta(days=days)

    qs = (
        Invoice.objects
        .filter(
            user=user,
            invoice_type="purchase",          # ✅ gastos
            date__range=(start_date, today),
        )
        .select_related("contact")
        .order_by("-date", "-id")
    )

    total = qs.aggregate(total=Sum("total"))["total"] or Decimal("0.00")
    return qs, total