import tempfile
import os
import time
from decimal import Decimal
from datetime import datetime
from django.db import transaction

from budsi_database.models import Invoice, FiscalProfile, InvoiceConcept
from logic.create_contact import get_or_create_contact
from logic.ocr_processor import InvoiceOCR

class InvoiceService:
    """Servicio para manejar operaciones de facturas"""
    
    @classmethod
    def generate_expense_number(cls, user):
        """Genera número único para gastos"""
        timestamp = int(time.time())
        return f"EXP-{timestamp}-{user.id}"
    
    @staticmethod
    def create_expense_from_ocr(user, file) -> Invoice:
        """Create an expense invoice from OCR processing - NOW WITH DISCOUNT"""
        print(f"🔄 InvoiceService.create_expense_from_ocr started for user: {user.id}")
        tmp_path = None
        
        try:
            # Save file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.name)[1]) as tmp_file:
                for chunk in file.chunks():
                    tmp_file.write(chunk)
                tmp_path = tmp_file.name
            
            print(f"📁 Temporary file created: {tmp_path}")
            
            try:
                # Process OCR
                print("🔍 Calling InvoiceOCR.process_invoice...")
                ocr_data = InvoiceOCR.process_invoice(tmp_path)
                
                print(f"📊 OCR data received: {ocr_data}")
                
                # Validate extracted data
                if ocr_data['confidence'] == 'low':
                    print(f"⚠️ WARNING: Low OCR confidence")
                
                supplier_name = ocr_data['supplier']
                total = Decimal(ocr_data['total'])
                vat = Decimal(ocr_data['vat'])
                discount = Decimal(ocr_data.get('discount', '0.00') or '0.00')  # ✅ NUEVO: obtener descuento
                
                print(f"💰 Amounts processed - Total: {total}, VAT: {vat}, Discount: {discount}")
                
                if total == 0:
                    print("⚠️ WARNING: Total amount is 0")
                
                # ✅ CORRECTION: Robust date handling
                invoice_date = ocr_data.get('date')
                if not invoice_date:
                    invoice_date = datetime.now().date()
                    print("📅 Using current date (no date in OCR data)")
                elif isinstance(invoice_date, str):
                    try:
                        from django.utils.dateparse import parse_date
                        parsed_date = parse_date(invoice_date)
                        if parsed_date:
                            invoice_date = parsed_date
                            print(f"📅 Date parsed from OCR: {invoice_date}")
                        else:
                            invoice_date = datetime.now().date()
                            print("⚠️ Could not parse date, using current date")
                    except Exception as date_error:
                        invoice_date = datetime.now().date()
                        print(f"⚠️ Date parsing error: {date_error}, using current date")
                
                print(f"📅 Final date: {invoice_date}")
                
                # Create contact
                print(f"👤 Creating contact for: {supplier_name}")
                contact = get_or_create_contact(
                    user=user,
                    name=supplier_name,
                    is_supplier=True,
                    is_client=False
                )
                print(f"✅ Contact created/retrieved: {contact.id} - {contact.name}")
                
                # Calculate subtotal (considering discount if needed)
                # Nota: El total ya viene después del descuento del OCR, así que el subtotal se calcula normal
                subtotal = total - vat
                print(f"🧮 Subtotal calculated: {subtotal}")
                
                # GENERATE UNIQUE EXPENSE NUMBER
                expense_number = InvoiceService.generate_expense_number(user)
                print(f"🔢 Expense number generated: {expense_number}")
                
                # ✅ CORRECTION: Create invoice WITH valid date AND discount in ocr_data
                print("📄 Creating Invoice object...")
                invoice = Invoice.objects.create(
                    user=user,
                    contact=contact,
                    invoice_type="purchase",
                    date=invoice_date,
                    subtotal=subtotal,
                    vat_amount=vat,
                    total=total,
                    ocr_data=ocr_data,  # ✅ Aquí ya viene el discount en ocr_data
                    is_confirmed=False,
                    invoice_number=expense_number,
                )
                
                print(f"✅ Expense invoice created successfully: {invoice.id}")
                print(f"📊 Invoice details - Number: {expense_number}, Total: {total}, Date: {invoice_date}, Discount: {discount}")
                
                return invoice

            except Exception as inner_error:
                print(f"❌ Error in OCR processing: {str(inner_error)}")
                import traceback
                print(f"🔍 Inner stack trace: {traceback.format_exc()}")
                raise
                
            finally:
                # Clean up temporary file
                if tmp_path and os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                    print(f"🧹 Temporary file cleaned up: {tmp_path}")
                    
        except Exception as e:
            print(f"❌ General error in create_expense_from_ocr: {str(e)}")
            import traceback
            print(f"🔍 Stack trace: {traceback.format_exc()}")
            raise
    @classmethod
    def generate_expense_number(cls, user):
        """Genera un número único para gastos"""
        import time
        import random
        timestamp = int(time.time() * 1000)  # Milisegundos para mayor precisión
        random_suffix = random.randint(1000, 9999)
        return f"EXP-{timestamp}-{user.id}-{random_suffix}"

    @staticmethod
    def create_sale_invoice(user, form_data) -> Invoice:
        """Crea factura de venta manual - CONTACTOS AUTOMÁTICAMENTE FAVORITOS"""
        print(f"InvoiceService.create_sale_invoice iniciado")
        print(f"Usuario: {user.id}")
        print(f"Datos del formulario: {form_data}")
        
        try:
            profile = FiscalProfile.objects.get(user=user)
            print(f"Perfil fiscal encontrado: {profile.business_name}")
            
            with transaction.atomic():
                # Generar número de factura
                invoice_count = profile.invoice_count + 1
                invoice_number = f"INV-{invoice_count:06d}"
                print(f"Numero de factura generado: {invoice_number}")
                
                # Crear contacto
                contact_name = form_data.get("contact", "").strip()
                print(f"Creando contacto para: {contact_name}")
                
                # ✅ CORRECCIÓN: Usar get_or_create_contact y marcar como favorito
                contact = get_or_create_contact(
                    user=user,
                    name=contact_name,
                    is_supplier=False,
                    is_client=True
                )
                # ✅ MARCAR COMO FAVORITO
                contact.is_favorite = True
                contact.save()
                print(f"⭐ Contacto marcado como favorito: {contact.name}")
                
                # Resto del código igual...
                # Procesar montos
                subtotal = Decimal(form_data.get("subtotal", 0))
                vat_amount = Decimal(form_data.get("vat_amount", 0))
                total = subtotal + vat_amount
                print(f"Montos - Subtotal: {subtotal}, VAT: {vat_amount}, Total: {total}")
                
                # Crear factura sin description
                print("Creando factura de venta...")
                invoice = Invoice.objects.create(
                    user=user,
                    contact=contact,
                    invoice_type="sale",
                    invoice_number=invoice_number,
                    date=form_data.get("date"),
                    subtotal=subtotal,
                    vat_amount=vat_amount,
                    total=total,
                    category=form_data.get("category", ""),
                    project=form_data.get("project", ""),
                    is_confirmed=True,
                )
                
                # Crear concepto de factura
                description = form_data.get("description", "")
                if description:
                    InvoiceConcept.objects.create(
                        invoice=invoice,
                        description=description,
                        quantity=Decimal('1.00'),
                        unit_price=subtotal,
                        vat_rate=(vat_amount / subtotal * 100) if subtotal > 0 else Decimal('23.0')
                    )
                    print(f"Concepto de venta creado: {description}")
                
                # Actualizar contador
                profile.invoice_count = invoice_count
                profile.save()
                print(f"Contador de facturas actualizado: {invoice_count}")
                
                print(f"FACTURA DE VENTA CREADA: {invoice_number}")
                return invoice
                
        except Exception as e:
            print(f"ERROR en create_sale_invoice: {str(e)}")
            import traceback
            print(f"Stack trace: {traceback.format_exc()}")
            raise

    @staticmethod
    def create_quick_invoice(user, contact, total, date=None):
        """Crea una factura rápida - VERSIÓN CON FAVORITO"""
        try:
            print(f"Creando factura rápida para {contact.name}")
            
            # ✅ Asegurar que el contacto sea favorito
            contact.is_favorite = True
            contact.save()
            print(f"⭐ Contacto marcado como favorito: {contact.name}")
            
            # Resto del código igual...
            # Generar número único
            timestamp = int(time.time())
            invoice_number = f"QINV-{timestamp}"
            
            # Crear factura sin description
            invoice = Invoice.objects.create(
                user=user,
                contact=contact,
                invoice_type="sale",
                invoice_number=invoice_number,
                date=date or datetime.now().date(),
                subtotal=total,
                vat_amount=Decimal('0.00'),
                total=total,
                is_confirmed=True,
                status="sent"
            )
            
            # Crear concepto
            InvoiceConcept.objects.create(
                invoice=invoice,
                description="Servicios varios",
                quantity=Decimal('1.00'),
                unit_price=total,
                vat_rate=Decimal('0.00')
            )
            
            print(f"Factura rápida creada: {invoice_number}")
            return invoice
            
        except Exception as e:
            print(f"Error creando factura rápida: {str(e)}")
            raise
    @staticmethod
    def calculate_invoice_totals(invoice):
        """Calcula los totales de una factura basado en sus conceptos"""
        try:
            concepts = invoice.concepts.all()
            if concepts.exists():
                subtotal = sum(concept.amount for concept in concepts)
                vat_amount = sum(concept.get_vat_amount() for concept in concepts)
                total = subtotal + vat_amount
                
                invoice.subtotal = subtotal
                invoice.vat_amount = vat_amount
                invoice.total = total
                invoice.save()
                
                print(f"Totales recalculados: Subtotal={subtotal}, VAT={vat_amount}, Total={total}")
                return True
            return False
        except Exception as e:
            print(f"Error calculando totales: {str(e)}")
            return False

    @staticmethod
    def update_invoice_status(invoice, new_status):
        """Actualiza el estado de una factura"""
        try:
            old_status = invoice.status
            invoice.status = new_status
            
            if new_status == "paid":
                invoice.payment_date = datetime.now().date()
            
            invoice.save()
            print(f"Estado actualizado: {old_status} -> {new_status}")
            return True
        except Exception as e:
            print(f"Error actualizando estado: {str(e)}")
            return False

    @staticmethod
    def get_invoice_summary(user, period_days=30):
        """Obtiene resumen de facturas para un usuario"""
        try:
            from datetime import timedelta
            from django.utils import timezone
            from django.db.models import Count, Sum, Q
            
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=period_days)
            
            # Facturas de venta
            sales = Invoice.objects.filter(
                user=user,
                invoice_type="sale",
                date__range=[start_date, end_date]
            )
            
            # Facturas de compra (gastos)
            purchases = Invoice.objects.filter(
                user=user,
                invoice_type="purchase", 
                date__range=[start_date, end_date]
            )
            
            summary = {
                'sales': {
                    'count': sales.count(),
                    'total': sales.aggregate(Sum('total'))['total__sum'] or Decimal('0.00'),
                    'draft': sales.filter(status='draft').count(),
                    'sent': sales.filter(status='sent').count(),
                    'paid': sales.filter(status='paid').count(),
                },
                'purchases': {
                    'count': purchases.count(),
                    'total': purchases.aggregate(Sum('total'))['total__sum'] or Decimal('0.00'),
                    'confirmed': purchases.filter(is_confirmed=True).count(),
                    'pending': purchases.filter(is_confirmed=False).count(),
                },
                'period': {
                    'start_date': start_date,
                    'end_date': end_date,
                    'days': period_days
                }
            }
            
            return summary
            
        except Exception as e:
            print(f"Error obteniendo resumen: {str(e)}")
            return None

