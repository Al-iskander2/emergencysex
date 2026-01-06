# emerg_database/admin.py
from django.contrib import admin
from .models import (
    User, Contact, Invoice, InvoiceConcept, FiscalProfile,
    Project, TaxPeriod, FiscalConfig,  # ← IMPORTA ESTOS
)

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'last_name', 'is_staff')
    search_fields = ('email', 'first_name', 'last_name')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    ordering = ('-date_joined',)

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'tax_id', 'is_client', 'is_supplier')
    list_filter = ('is_client', 'is_supplier', 'user')
    search_fields = ('name', 'tax_id', 'user__email')
    list_select_related = ('user',)

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'user', 'contact', 'invoice_type', 'date', 'total')
    list_filter = ('invoice_type', 'date', 'user')
    search_fields = ('invoice_number', 'contact__name', 'user__email')
    list_select_related = ('user', 'contact')
    ordering = ('-date',)

@admin.register(InvoiceConcept)
class InvoiceConceptAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'description', 'quantity', 'unit_price')
    list_filter = ('invoice__invoice_type',)
    search_fields = ('invoice__invoice_number', 'description')
    list_select_related = ('invoice',)

@admin.register(FiscalProfile)
class FiscalProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'business_name', 'vat_number', 'pps_number', 'invoice_count')
    search_fields = ('business_name', 'vat_number', 'pps_number', 'user__email')
    list_select_related = ('user',)

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'status', 'budget', 'start_date', 'end_date')
    search_fields = ('name', 'user__email')
    list_filter = ('status', 'start_date')
    list_select_related = ('user',)

@admin.register(TaxPeriod)
class TaxPeriodAdmin(admin.ModelAdmin):
    list_display = ('user', 'period_type', 'start_date', 'end_date', 'status')
    search_fields = ('user__email',)
    list_filter = ('period_type', 'status')
    list_select_related = ('user',)

@admin.register(FiscalConfig)
class FiscalConfigAdmin(admin.ModelAdmin):
    list_display = ('user', 'year')
    search_fields = ('user__email',)
    list_filter = ('year',)
    list_select_related = ('user',)
