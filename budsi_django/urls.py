# budsi_django/urls.py - VERSIÓN OPTIMIZADA
from django.urls import path, include
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

# Importaciones corregidas
from budsi_django import views
from logic.auth import intro_view, login_view, register_view, onboarding_view
from logic.account_settings import account_settings_view
from logic.invoices import (
    invoice_list_view, invoice_create_view, invoice_detail_view,
    invoices_create_from_customer_view, invoice_save_view,
    invoices_list_view, invoices_detail_view, invoices_update_status_view,
    credit_note_create_view, credit_note_save_view
)
from logic.expenses import (
    expense_list_view, expenses_upload_view, invoice_upload_view,
    expenses_create_view, invoice_preview_view, general_upload,
    visualize_expense_view, expense_create_manual_view, expense_save_manual_view,
    expense_detail_view, expense_update_status_view
)
from logic.tax_report import tax_report_view
from budsi_django.views import dashboard_view
from logic.track import track_view, create_project_view, toggle_project_status_view, update_project_dates_view
from logic.stripe import process_payment_view, pricing_view, create_payment_intent_view, payment_page

from logic.mvp import (
    mvp_index, init_session, update_profile, update_location, 
    search_candidates, like_user, poll_status, confirm_match, cancel_match
)

urlpatterns = [
    # -------- MVP ROUTES --------
    path('', mvp_index, name='mvp_index'), # Replaces intro
    path('api/mvp/init/', init_session, name='mvp_init'),
    path('api/mvp/profile/', update_profile, name='mvp_profile'),
    path('api/mvp/location/', update_location, name='mvp_location'),
    path('api/mvp/search/', search_candidates, name='mvp_search'),
    path('api/mvp/like/', like_user, name='mvp_like'),
    path('api/mvp/poll/', poll_status, name='mvp_poll'),
    path('api/mvp/confirm/', confirm_match, name='mvp_confirm'),
    path('api/mvp/cancel/', cancel_match, name='mvp_cancel'),

    # -------- ADMIN --------
    path('admin/', admin.site.urls),
    
    # -------- LANDING & AUTH --------
    path("", intro_view, name="intro"),  # ✅ Página principal
    path("login/", login_view, name="login"),
    path("register/", register_view, name="register"),
    path("signup/", register_view, name="signup"),  # ✅ ALIAS para templates
    path("logout/", auth_views.LogoutView.as_view(next_page="intro"), name="logout"),
    
    # -------- PASSWORD MANAGEMENT --------
    path("password-change/", auth_views.PasswordChangeView.as_view(
        template_name="budsidesk_app/auth/password_change_form.html",
        success_url="/password-change/done/"
    ), name="password_change"),
    path("password-change/done/", auth_views.PasswordChangeDoneView.as_view(
        template_name="budsidesk_app/auth/password_change_done.html"
    ), name="password_change_done"),
    
    # -------- ONBOARDING & SETTINGS --------
    path("onboarding/", onboarding_view, name="onboarding"),
    path("account/settings/", account_settings_view, name="account_settings"),
    
    # -------- DASHBOARD --------
    path("dashboard/", dashboard_view, name="dashboard"),
    
    # -------- MAIN NAVIGATION CENTER --------
    path("main/invoice/", views.main_invoice_view, name="main_invoice"),
    path("main/expenses/", views.main_expenses_view, name="main_expenses"),
    path("main/pulse/", views.main_pulse_view, name="main_pulse"),
    path("main/track/", track_view, name="main_track"),
    
    # -------- EXPENSES --------
    path("expenses/", expense_list_view, name="expense_list"),
    path("expenses/create/", expenses_create_view, name="expense_create"),
    path("expenses/create/manual/", expense_create_manual_view, name="expense_create_manual"),
    path("expenses/save/manual/", expense_save_manual_view, name="expense_save_manual"),
    path("expenses/upload/", expenses_upload_view, name="expense_upload"),
    path("expenses/<int:invoice_id>/preview/", invoice_preview_view, name="invoice_preview"),
    path("expenses/<int:invoice_id>/", visualize_expense_view, name="expense_view"),
    path("expenses/<int:invoice_id>/detail/", expense_detail_view, name="expense_detail"),
    path("expenses/<int:invoice_id>/update-status/", expense_update_status_view, name="expense_update_status"),
    path('expenses/delete/<int:invoice_id>/', views.expenses_delete_view, name='expense_delete'),
    
    # -------- INVOICES --------
    path("invoices/", invoice_list_view, name="invoice_list"),
    path("invoices/credit-note/", credit_note_create_view, name="credit_note_create"),
    path("invoices/credit-note/save/", credit_note_save_view, name="credit_note_save"),
    path("invoices/create/", invoice_create_view, name="invoice_create"),
    path("invoices/<int:invoice_id>/", invoice_detail_view, name="invoice_detail"),
    path("invoices/<int:invoice_id>/update_status/", views.update_invoice_status, name="invoice_update_status"),

    path("invoices/create/from-customer/<int:customer_id>/", invoices_create_from_customer_view, name="invoice_create_from_customer"),
    path("invoices/save/", invoice_save_view, name="invoice_save"),
    
    # -------- URLs DE COMPATIBILIDAD --------
    path("invoices/list/", invoices_list_view, name="invoices_list"),
    path("invoices/<int:pk>/detail/", invoices_detail_view, name="invoices_detail"),
    path("invoices/<int:pk>/status/", views.invoices_update_status_view, name="invoices_update_status"),
    
    
    # -------- UPLOAD --------
    path("upload/", general_upload, name="general_upload"),
    path("invoice/upload/", invoice_upload_view, name="invoice_upload"),
    
    # -------- TAX REPORT --------
    path("tax/report/", tax_report_view, name="tax_report"),
    
    # -------- TRACK PROJECTS --------
    path("projects/create/", create_project_view, name="create_project_view"),
    path("projects/<int:project_id>/toggle-status/", toggle_project_status_view, name="toggle_project_status"),
    path("projects/<int:project_id>/update-dates/", update_project_dates_view, name="update_project_dates"),
    
    # -------- STRIPE & BILLING --------
    path("pricing/", pricing_view, name="pricing"),
    path("payment/", payment_page, name="payment"),
    path("payment-page/", payment_page, name="payment_page"),  # ✅ ALIAS para templates
    path("create-payment-intent/", create_payment_intent_view, name="create_payment_intent"),
    path("process-payment/", process_payment_view, name="process_payment"),
    
    # -------- DASHBOARD SECTIONS --------
    path("dash/flow/", views.flow_view, name="dash_flow"),
    path("dash/buzz/", views.buzz_view, name="dash_buzz"),
    path("dash/nest/", views.nest_view, name="dash_nest"),
    path("dash/whiz/", views.whiz_view, name="dash_whiz"),
    path("dash/help/", views.help_view, name="dash_help"),
    
    # -------- HELP & SUPPORT --------
    path('help/faqs/', views.faqs_view, name='faqs'),
    path('help/support/', views.help_view, name='help_support'),
    
    # -------- DOCUMENTOS (CIRCUITO SIMPLE ACTUAL) --------
    path("legal/templates/", views.legal_templates_view, name="legal_templates"),
    path("legal/templates/service-agreement/", views.service_agreement_form_view, name="service_agreement_form"),
    path("legal/templates/project-proposal/", views.project_proposal_form_view, name="project_proposal_form"),
    path("legal/templates/time-sheet/", views.time_sheet_form_view, name="time_sheet_form"),
    path("legal/templates/non-disclosure/", views.non_disclosure_form_view, name="non_disclosure_form"),
    path("legal/templates/statement-of-work/", views.statement_of_work_form_view, name="statement_of_work_form"),
    
    # -------- FINANCES & BALANCE --------
    path("balance/", views.balance_overview_view, name="balance_overview"),
    
    # -------- REMINDERS --------
    path("reminders/", views.reminders_view, name="reminders"),
    
    # -------- INVOICE UTILITIES --------
    path("invoices/create-pdf/", views.create_invoice_pdf_view, name="create_invoice_pdf"),
    path("invoices/<int:invoice_id>/gallery/", views.invoice_gallery_view, name="invoice_gallery"),
    
    # -------- Email action --------
    path("email/action/", views.email_action_view, name="email_action"),
    

    
    # -------- LEGAL POLICIES --------
    path("privacy/", TemplateView.as_view(
        template_name="budsidesk_app/policies/privacypolicy.html"), name="privacy"),
    path("terms/", TemplateView.as_view(
        template_name="budsidesk_app/policies/terms.html"), name="terms"),
    path("cookies/", TemplateView.as_view(
        template_name="budsidesk_app/policies/cookies.html"), name="cookies"),
    path("refunds/", TemplateView.as_view(
        template_name="budsidesk_app/policies/refunds.html"), name="refunds"),
    path("refund/", TemplateView.as_view(  # ✅ ALIAS para templates
        template_name="budsidesk_app/policies/refunds.html"), name="refund"),
    path("disclaimer/", TemplateView.as_view(
        template_name="budsidesk_app/policies/disclaimer.html"), name="disclaimer"),
    path("legal/", TemplateView.as_view(
        template_name="budsidesk_app/policies/legal.html"), name="legal"),
    path("accessibility/", TemplateView.as_view(
        template_name="budsidesk_app/policies/accessibility.html"), name="accessibility"),
]

# ✅ SERVIR ARCHIVOS STATIC & MEDIA
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# ✅ SERVIR ARCHIVOS MEDIA EN RENDER (producción)
if hasattr(settings, 'RENDER') and settings.RENDER:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)