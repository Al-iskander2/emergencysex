from django import forms
from django.contrib.auth.forms import UserCreationForm
from budsi_database.models import User, Invoice, Contact, FiscalProfile, InvoiceConcept, DuePolicy

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("email", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user

class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = [
            'invoice_type', 'contact', 'invoice_number', 'date',
            'due_policy', 'due_days', 'due_date',
            'summary', 'notes',
            'project', 'category',
            'subtotal', 'vat_amount', 'total', 'currency',
            'status', 'is_confirmed', 'is_credit_note',
            'original_file', 'credit_note_reason'
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'summary': forms.TextInput(attrs={'placeholder': 'Brief summary of the invoice'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Additional notes or terms'}),
            'due_days': forms.NumberInput(attrs={'min': 1, 'max': 365}),
            'category': forms.TextInput(attrs={'placeholder': 'Enter category'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            self.fields['contact'].queryset = Contact.objects.filter(user=user)
            
        self.fields['due_policy'].choices = DuePolicy.choices
        
        if self.instance and self.instance.invoice_type == Invoice.SALE:
            self.fields['category'].widget.attrs['placeholder'] = 'e.g., Services, Products, Consulting'
            self.fields['category'].label = "Income Category"
        else:
            self.fields['category'].widget.attrs['placeholder'] = 'e.g., Office Supplies, Travel, Software'
            self.fields['category'].label = "Expense Category"
        
        self.fields['category'].required = False

class InvoiceConceptForm(forms.ModelForm):
    class Meta:
        model = InvoiceConcept
        fields = ['description', 'quantity', 'unit_price', 'vat_rate', 'amount']
        widgets = {
            'description': forms.TextInput(attrs={'placeholder': 'Item description'}),
            'quantity': forms.NumberInput(attrs={'step': '0.01', 'min': '0.01'}),
            'unit_price': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'vat_rate': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'max': '100'}),
            'amount': forms.NumberInput(attrs={'readonly': 'readonly'}),
        }

class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ['name', 'tax_id', 'email', 'is_supplier', 'is_client', 'is_favorite']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Contact name'}),
            'tax_id': forms.TextInput(attrs={'placeholder': 'Tax ID/VAT number'}),
            'email': forms.EmailInput(attrs={'placeholder': 'email@example.com'}),
        }

class FiscalProfileForm(forms.ModelForm):
    class Meta:
        model = FiscalProfile
        fields = [
            'legal_name', 'business_name', 'business_type', 'profession', 'sector',
            'contact_full_name', 'phone', 'logo',
            'vat_registered', 'vat_number', 'pps_number', 'tax_country', 'tax_region',
            'addr_line1', 'addr_line2', 'city', 'county', 'eircode', 'country',
            'currency', 'payment_terms', 'invoice_defaults', 'late_notice', 
            'payment_methods', 'accounting_method', 'vat_schemes',
            'period_type', 'fiscal_year_start', 'reminders_enabled', 'reminder_days_before_due',
            'iban', 'bic', 'invoice_footer',
            'auto_detect_contacts', 'ocr_confidence_threshold', 'tax_bands'
        ]
        widgets = {
            'fiscal_year_start': forms.DateInput(attrs={'type': 'date'}),
            'late_notice': forms.Textarea(attrs={'rows': 3}),
            'payment_methods': forms.Textarea(attrs={'rows': 2}),
            'invoice_footer': forms.Textarea(attrs={'rows': 3}),
        }

class QuickInvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ['contact', 'summary', 'total', 'due_policy']
        widgets = {
            'summary': forms.TextInput(attrs={
                'placeholder': 'What is this invoice for?',
                'class': 'form-control'
            }),
            'total': forms.NumberInput(attrs={
                'step': '0.01',
                'min': '0',
                'class': 'form-control'
            }),
            'due_policy': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            self.fields['contact'].queryset = Contact.objects.filter(
                user=user, 
                is_client=True
            )
        self.fields['due_policy'].choices = DuePolicy.choices