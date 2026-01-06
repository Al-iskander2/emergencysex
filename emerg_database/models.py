from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.conf import settings
from decimal import Decimal
from django.utils import timezone

# -------- Custom User (keep as is) --------
class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('plan', 'smart')  # ← AÑADIR ESTA LÍNEA
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('plan', 'admin')  # ← Superusers como admin
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self._create_user(email, password, **extra_fields)

class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    plan = models.CharField(max_length=20, default='smart')
    fiscal_data = models.JSONField(default=dict, blank=True)
    business_data = models.JSONField(default=dict, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    objects = UserManager()

    def __str__(self):
        return self.email

# Function for logo upload path
def logo_upload_to(instance, filename):
    return f"logos/user_{instance.user_id}/{filename}"

# -------- Fiscal Profile COMPLETO --------
class FiscalProfile(models.Model):
    user = models.OneToOneField('User', on_delete=models.CASCADE, related_name='fiscal_profile')

    # Identity / Business
    legal_name = models.CharField(max_length=200, blank=True)
    business_name = models.CharField(max_length=200, blank=True)
    business_type = models.CharField(max_length=50, blank=True)      # sole_trader / limited / ...
    profession = models.CharField(max_length=100, blank=True)
    sector = models.CharField(max_length=100, blank=True)

    # Contact & Branding
    contact_full_name = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    logo = models.ImageField(upload_to=logo_upload_to, blank=True, null=True)

    # Tax IDs
    vat_registered = models.BooleanField(default=False)
    vat_number = models.CharField(max_length=32, blank=True)
    pps_number = models.CharField(max_length=16, blank=True)
    tax_country = models.CharField(max_length=2, default='IE')       # ISO-3166-1 alpha-2
    tax_region = models.CharField(max_length=50, blank=True)

    # Address
    addr_line1 = models.CharField(max_length=200, blank=True)
    addr_line2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100, blank=True)
    county = models.CharField(max_length=100, blank=True)
    eircode = models.CharField(max_length=10, blank=True)
    country = models.CharField(max_length=2, default='IE')

    # Invoicing & VAT
    currency = models.CharField(max_length=3, default='EUR')
    payment_terms = models.CharField(max_length=100, blank=True)
    invoice_defaults = models.BooleanField(default=True)
    late_notice = models.TextField(blank=True)
    payment_methods = models.TextField(blank=True)
    accounting_method = models.CharField(max_length=16, default='invoice')
    vat_schemes = models.JSONField(default=dict, blank=True)

    # Periods & Reminders
    period_type = models.CharField(max_length=10, default='monthly')
    fiscal_year_start = models.DateField(null=True, blank=True)
    reminders_enabled = models.BooleanField(default=True)
    reminder_days_before_due = models.PositiveIntegerField(default=7)

    # Banking & Footer
    iban = models.CharField(max_length=34, blank=True)
    bic = models.CharField(max_length=11, blank=True)
    invoice_footer = models.TextField(blank=True)

    # Ops / OCR
    auto_detect_contacts = models.BooleanField(default=True)
    ocr_confidence_threshold = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal('0.70'))

    # Legacy/advanced knobs
    tax_bands = models.JSONField(default=dict, blank=True)

    # NUEVO: contador de facturas
    invoice_count = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'Fiscal Profile'
        verbose_name_plural = 'Fiscal Profiles'

    def __str__(self):
        return f'Fiscal profile of {self.user}'

# -------- Contacts (UPDATED con address y cellphone) --------
class Contact(models.Model):
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='contacts')
    name = models.CharField(max_length=200, verbose_name='Name')
    tax_id = models.CharField(max_length=50, blank=True, verbose_name='Tax ID')
    email = models.EmailField(blank=True, verbose_name='Email')
    # NUEVOS CAMPOS
    address = models.TextField(blank=True, verbose_name='Address')
    cellphone = models.CharField(max_length=30, blank=True, verbose_name='Cellphone')
    
    is_supplier = models.BooleanField(default=False, verbose_name='Is Supplier')
    is_client = models.BooleanField(default=False, verbose_name='Is Client')
    is_favorite = models.BooleanField(default=False, verbose_name='Favorite')

    class Meta:
        verbose_name = 'Contact'
        verbose_name_plural = 'Contacts'
        unique_together = (('user', 'tax_id'),)
        indexes = [
            models.Index(fields=['user', 'name']),
            models.Index(fields=['user', 'email']),
        ]

    def __str__(self):
        return self.name

def invoice_upload_to(instance, filename):
    user_id = instance.user_id or 'anon'
    return f'invoices/user_{user_id}/{filename}'

# ========== NEW: DUE POLICIES ==========
class DuePolicy(models.TextChoices):
    DUE_ON_RECEIPT = "DUE_ON_RECEIPT", "Due on receipt"
    NET_7 = "NET_7", "Net 7 days"
    NET_15 = "NET_15", "Net 15 days"
    NET_30 = "NET_30", "Net 30 days"
    NET_60 = "NET_60", "Net 60 days"
    EOM = "EOM", "End of month"
    CUSTOM_DAYS = "CUSTOM_DAYS", "Custom days"
    CUSTOM_DATE = "CUSTOM_DATE", "Specific date"

# ========== INVOICE MODEL (UPDATED con snapshot) ==========
class Invoice(models.Model):
    SALE = 'sale'
    PURCHASE = 'purchase'
    CREDIT_NOTE = 'credit_note'
    INVOICE_TYPES = (
        (SALE, 'Sale'),
        (PURCHASE, 'Purchase'),
        (CREDIT_NOTE, 'Credit Note')
    )

    # Status choices
    DRAFT = 'draft'
    SENT = 'sent'
    PAID = 'paid'
    OVERDUE = 'overdue'
    CANCELLED = 'cancelled'
    STATUS_CHOICES = (
        (DRAFT, 'Draft'),
        (SENT, 'Sent'),
        (PAID, 'Paid'),
        (OVERDUE, 'Overdue'),
        (CANCELLED, 'Cancelled')
    )

    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='invoices', verbose_name='User')
    invoice_type = models.CharField(max_length=12, choices=INVOICE_TYPES, default=PURCHASE, verbose_name='Invoice Type')
    contact = models.ForeignKey('Contact', on_delete=models.PROTECT, related_name='invoices', verbose_name='Contact')
    invoice_number = models.CharField(max_length=64, verbose_name='Invoice Number')
    date = models.DateField(verbose_name='Date')
    
    project = models.CharField(max_length=200, blank=True, null=True, verbose_name='Project')
    category = models.CharField(max_length=100, blank=True, null=True, verbose_name='Category')

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name='Subtotal')
    vat_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name='VAT Amount')
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name='Total')
    currency = models.CharField(max_length=3, default='EUR', verbose_name='Currency')

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=DRAFT, verbose_name='Status')
    is_confirmed = models.BooleanField(default=False, verbose_name='Confirmed')

    # Campos de vencimiento
    due_policy = models.CharField(
        max_length=20, 
        choices=DuePolicy.choices, 
        default=DuePolicy.NET_30,
        verbose_name='Due Policy'
    )
    due_days = models.PositiveSmallIntegerField(
        null=True, 
        blank=True, 
        verbose_name='Days Until Due'
    )
    due_date = models.DateField(
        null=True, 
        blank=True, 
        verbose_name='Due Date'
    )

    summary = models.CharField(
        max_length=200, 
        blank=True, 
        default="",
        verbose_name='Summary'
    )
    notes = models.TextField(blank=True, verbose_name='Notes')

    # SNAPSHOT de datos del cliente (NUEVO)
    client_name = models.CharField(max_length=200, blank=True, verbose_name='Client Name')
    client_email = models.EmailField(blank=True, verbose_name='Client Email')
    client_cellphone = models.CharField(max_length=30, blank=True, verbose_name='Client Cellphone')
    client_address = models.TextField(blank=True, verbose_name='Client Address')

    # Compatibilidad con dashboard
    is_credit_note = models.BooleanField(default=False, verbose_name='Is Credit Note')

    original_file = models.FileField(upload_to=invoice_upload_to, blank=True, null=True, verbose_name='Original File')
    credit_note_reason = models.TextField(blank=True, null=True, verbose_name='Credit Note Reason')

    ocr_data = models.JSONField(default=dict, blank=True, verbose_name='OCR Data')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')

    class Meta:
        verbose_name = 'Invoice'
        verbose_name_plural = 'Invoices'
        unique_together = (('user', 'invoice_number'),)
        indexes = [
            models.Index(fields=['user', 'date']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', 'invoice_type']),
            models.Index(fields=['user', 'is_credit_note']),
            models.Index(fields=['user', 'due_date']),
            models.Index(fields=['user', 'client_name']),
        ]

    def __str__(self):
        return f'{self.invoice_number} - {self.contact.name} - {self.total} {self.currency}'

    def compute_due_date(self):
        """✅ VERSIÓN ROBUSTA QUE MANEJA TODO"""
        base_date = self.date
        
        # Si es string, convertirlo a date
        if isinstance(base_date, str):
            from django.utils.dateparse import parse_date
            parsed = parse_date(base_date)
            base_date = parsed or timezone.now().date()
        
        # Si es None, usar fecha actual
        if base_date is None:
            base_date = timezone.now().date()
        
        # Calcular due_date según política
        if self.due_policy == DuePolicy.DUE_ON_RECEIPT:
            return base_date
        elif self.due_policy == DuePolicy.NET_7:
            return base_date + timezone.timedelta(days=7)
        elif self.due_policy == DuePolicy.NET_15:
            return base_date + timezone.timedelta(days=15)
        elif self.due_policy == DuePolicy.NET_30:
            return base_date + timezone.timedelta(days=30)
        elif self.due_policy == DuePolicy.NET_60:
            return base_date + timezone.timedelta(days=60)
        elif self.due_policy == DuePolicy.EOM:
            # End of month: first day of next month minus one day
            next_month = base_date.replace(day=28) + timezone.timedelta(days=4)
            return next_month.replace(day=1) - timezone.timedelta(days=1)
        elif self.due_policy == DuePolicy.CUSTOM_DAYS and self.due_days:
            return base_date + timezone.timedelta(days=self.due_days)
        
        # Fallback: 30 days by default
        return base_date + timezone.timedelta(days=30)

    def save(self, *args, **kwargs):
        # Auto-compute due_date unless CUSTOM_DATE is selected
        if self.due_policy != DuePolicy.CUSTOM_DATE:
            self.due_date = self.compute_due_date()
        
        # Auto-flag as credit note if the type is CREDIT_NOTE
        if self.invoice_type == self.CREDIT_NOTE:
            self.is_credit_note = True
            
        super().save(*args, **kwargs)

    def calculate_totals(self):
        """Calculates subtotal, VAT, and total based on the invoice concepts."""
        concepts = self.concepts.all()
        if concepts.exists():
            # Usamos amount que ya incluye descuentos
            self.subtotal = sum(concept.amount for concept in concepts)
            # VAT se calcula sobre el neto (amount)
            self.vat_amount = sum(concept.amount * (concept.vat_rate / Decimal('100.00')) for concept in concepts)
            self.total = self.subtotal + self.vat_amount
            self.save()

    def get_concepts_count(self):
        """Number of concepts in this invoice."""
        return self.concepts.count()

    def get_payment_due_date(self):
        """Alias for due_date (compatibility)."""
        return self.due_date

    def is_overdue(self):
        """Returns True if the invoice is overdue."""
        if self.due_date and self.status not in [self.PAID, self.CANCELLED]:
            return self.due_date < timezone.now().date()
        return False

# -------- Tax Period --------
class TaxPeriod(models.Model):
    MONTHLY = 'monthly'
    QUARTERLY = 'quarterly'
    YEARLY = 'yearly'
    PERIOD_TYPES = (
        (MONTHLY, 'Mensual'), 
        (QUARTERLY, 'Trimestral'), 
        (YEARLY, 'Anual')
    )

    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='tax_periods', verbose_name='Usuario')
    period_type = models.CharField(max_length=10, choices=PERIOD_TYPES, default=MONTHLY, verbose_name='Tipo de Período')
    start_date = models.DateField(verbose_name='Fecha Inicio')
    end_date = models.DateField(verbose_name='Fecha Fin')
    status = models.CharField(max_length=20, default='draft', verbose_name='Estado')
    tax_data = models.JSONField(default=dict, blank=True, verbose_name='Datos Fiscales')

    class Meta:
        verbose_name = 'Período Fiscal'
        verbose_name_plural = 'Períodos Fiscales'
        indexes = [models.Index(fields=['user', 'start_date', 'end_date'])]

    def __str__(self):
        return f'{self.user} {self.period_type} {self.start_date}–{self.end_date}'

# -------- Fiscal Config --------
class FiscalConfig(models.Model):
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='fiscal_configs', verbose_name='Usuario')
    year = models.PositiveIntegerField(verbose_name='Año')
    config = models.JSONField(default=dict, blank=True, verbose_name='Configuración')

    class Meta:
        verbose_name = 'Configuración Fiscal'
        verbose_name_plural = 'Configuraciones Fiscales'
        unique_together = (('user', 'year'),)

    def __str__(self):
        return f'Configuración {self.year} para {self.user}'

# -------- Invoice Concept (UPDATED con descuentos) --------
class InvoiceConcept(models.Model):
    invoice = models.ForeignKey('Invoice', on_delete=models.CASCADE, related_name='concepts', verbose_name='Factura')
    description = models.CharField(max_length=200, verbose_name='Descripción del Concepto')
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('1.00'), verbose_name='Cantidad')
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Precio Unitario')
    vat_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('21.00'), verbose_name='% IVA')
    # NUEVOS CAMPOS DE DESCUENTO
    discount_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'), verbose_name='% Descuento')
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), verbose_name='Importe de Descuento')
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), verbose_name='Importe')

    class Meta:
        verbose_name = 'Concepto de Factura'
        verbose_name_plural = 'Conceptos de Factura'
        ordering = ['id']

    def __str__(self):
        return f'{self.description} - {self.amount} {self.invoice.currency}'

    def save(self, *args, **kwargs):
        # Calculamos el importe bruto (sin descuento)
        gross_amount = self.quantity * self.unit_price
        
        # Aplicamos descuento: si hay discount_amount lo usamos, sino aplicamos el discount_rate
        if self.discount_amount > Decimal('0.00'):
            discount = self.discount_amount
        else:
            discount = gross_amount * (self.discount_rate / Decimal('100.00'))
        
        # El importe neto es el bruto menos el descuento
        self.amount = gross_amount - discount
        
        super().save(*args, **kwargs)
        if self.invoice:
            self.invoice.calculate_totals()

    def get_vat_amount(self):
        return self.amount * (self.vat_rate / Decimal('100.00'))

# -------- Project Model --------
class Project(models.Model):
    ACTIVE = 'active'
    COMPLETED = 'completed'
    ON_HOLD = 'on_hold'
    STATUS_CHOICES = [
        (ACTIVE, 'Activo'),
        (COMPLETED, 'Completado'),
        (ON_HOLD, 'En Pausa'),
    ]

    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='projects', verbose_name='Usuario')
    name = models.CharField(max_length=200, verbose_name='Nombre del Proyecto')
    description = models.TextField(blank=True, verbose_name='Descripción')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=ACTIVE, verbose_name='Estado')
    start_date = models.DateField(null=True, blank=True, verbose_name='Fecha Inicio')
    end_date = models.DateField(null=True, blank=True, verbose_name='Fecha Fin')
    budget = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name='Presupuesto')
    is_active = models.BooleanField(default=True, verbose_name='Activo')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Creado el')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Actualizado el')

    class Meta:
        verbose_name = 'Proyecto'
        verbose_name_plural = 'Proyectos'
        unique_together = (('user', 'name'),)
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', 'start_date']),
        ]

    def __str__(self):
        return f'{self.name} ({self.get_status_display()})'
    
    def get_progress(self):
        """Calcular progreso del proyecto basado en facturas asociadas"""
        from django.db.models import Sum
        try:
            project_invoices = Invoice.objects.filter(user=self.user, project=self.name)
            if project_invoices.exists():
                total_invoiced = project_invoices.aggregate(Sum('total'))['total__sum'] or Decimal('0')
                if self.budget > 0:
                    progress = (total_invoiced / self.budget * 100).quantize(Decimal('0.01'))
                    return min(float(progress), 100.0)
            return 0.0
        except:
            return 0.0

    def get_total_invoiced(self):
        """Obtener el total facturado para este proyecto"""
        from django.db.models import Sum
        try:
            project_invoices = Invoice.objects.filter(user=self.user, project=self.name)
            total = project_invoices.aggregate(Sum('total'))['total__sum'] or Decimal('0')
            return total
        except:
            return Decimal('0.00')

# ==========================================
# ============ MVP MODELS START ============
# ==========================================

class SessionUser(models.Model):
    GENDER_CHOICES = [
        ('man', 'Man'),
        ('female', 'Female'),
    ]
    LOOKING_FOR_CHOICES = [
        ('man', 'Man'),
        ('female', 'Female'),
        ('trans', 'Trans'),
    ]
    ROLE_CHOICES = [
        ('host', 'I can host'),
        ('travel', 'I can travel'),
        ('either', 'Either'),
    ]
    
    session_id = models.CharField(max_length=100, unique=True, db_index=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True)
    looking_for = models.CharField(max_length=10, choices=LOOKING_FOR_CHOICES, blank=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='either')
    radius = models.IntegerField(default=10, help_text="Search radius in km")
    
    lat = models.FloatField(null=True, blank=True)
    lon = models.FloatField(null=True, blank=True)
    
    last_active = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    age_verified_at = models.DateTimeField(null=True, blank=True)
    def __str__(self):
        return f"Session {self.session_id[:8]}..."

def session_photo_upload_to(instance, filename):
    return f"mvp/photos/{instance.user.session_id}/{filename}"

class Photo(models.Model):
    user = models.ForeignKey('SessionUser', on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to=session_photo_upload_to)
    created_at = models.DateTimeField(auto_now_add=True)

class Match(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'), # Match created but not confirmed by users (maybe auto-match logic?) 
                                # Actually, if both like, it's a match. 
                                # Let's say 'matched' is the initial state when both liked.
        ('matched', 'Matched'), 
        ('confirmed', 'Confirmed'), # Both users clicked "Confirm"
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ]
    
    user1 = models.ForeignKey('SessionUser', on_delete=models.CASCADE, related_name='matches_as_user1')
    user2 = models.ForeignKey('SessionUser', on_delete=models.CASCADE, related_name='matches_as_user2')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='matched')
    
    user1_confirmed = models.BooleanField(default=False)
    user2_confirmed = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def save(self, *args, **kwargs):
        if not self.expires_at:
            # Default expiration: 30 minutes
            self.expires_at = timezone.now() + timezone.timedelta(minutes=30)
        super().save(*args, **kwargs)

class Block(models.Model):
    blocker = models.ForeignKey('SessionUser', on_delete=models.CASCADE, related_name='blocks_made')
    blocked = models.ForeignKey('SessionUser', on_delete=models.CASCADE, related_name='blocks_received')
    reason = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('blocker', 'blocked')

class Report(models.Model):
    reporter = models.ForeignKey('SessionUser', on_delete=models.CASCADE, related_name='reports_made')
    reported = models.ForeignKey('SessionUser', on_delete=models.CASCADE, related_name='reports_received')
    reason = models.CharField(max_length=200)
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Like(models.Model):
    from_user = models.ForeignKey('SessionUser', on_delete=models.CASCADE, related_name='likes_given')
    to_user = models.ForeignKey('SessionUser', on_delete=models.CASCADE, related_name='likes_received')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('from_user', 'to_user')

# ==========================================
# ============= MVP MODELS END =============
# ==========================================