import re
import os
import logging
from typing import Tuple, Dict, List
from decimal import Decimal, InvalidOperation
from datetime import datetime

from logic.ocr_config import configure_ocr
configure_ocr()

logger = logging.getLogger(__name__)

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
    print("✅ PyMuPDF disponible")
except ImportError:
    PYMUPDF_AVAILABLE = False
    print("❌ PyMuPDF no disponible")

try:
    import pytesseract
    from PIL import Image, ImageEnhance, ImageFilter
    TESSERACT_AVAILABLE = True
    print("✅ Tesseract disponible")
except ImportError:
    TESSERACT_AVAILABLE = False
    print("❌ Tesseract no disponible")

class InvoiceOCR:
    """Procesador de facturas robusto para producción - VERSIÓN MEJORADA"""
    
    # ✅ PATRONES MEJORADOS para facturas irlandesas
    DATE_PATTERNS = [
        r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',  # 31/12/2023
        r'\b(\d{4}[-/]\d{1,2}[-/]\d{1,2})\b',    # 2023-12-31
        r'\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})\b',  # 31 Dec 2023
    ]
    
    # ✅ KEYWORDS MEJORADAS - PAID tiene prioridad sobre TOTAL
    TOTAL_KEYWORDS = [
        'amount due', 'balance due',
        'paid', 'amount paid', 'total paid', 'paid amount',  # ✅ PAID primero
        'grand total', 'final total',
        'total amount', 'amount payable', 'invoice total',
        'total',  # último - más genérico
    ]
    
    # ✅ NUEVAS KEYWORDS PARA DESCUENTOS
    DISCOUNT_KEYWORDS = [
        'discount', 'first year discount', 'year discount',
        'rebate', 'promo discount', 'promotional discount',
        'coupon', 'credit', 'deduction', 'less', 'off', 'reduction'
    ]
    
    VAT_KEYWORDS = ['vat', 'tax', 'iva', 'value added tax', 'v.a.t.']
    
    # ✅ EXCLUSIONES MEJORADAS
    SUPPLIER_EXCLUDE_PHRASES = {
        'all prices in', 'prices in', 'invoice', 'receipt', 'bill',
        'date:', 'subtotal', 'total', 'vat', 'tax', 'thank you',
        'due date', 'invoice number', 'description', 'amount', 'page',
        'tel', 'phone', 'email', 'www', 'http', 'https', 'due'
    }

    @staticmethod
    def extract_text_from_pdf(file_path: str) -> str:
        """Extrae texto de PDF usando PyMuPDF (más rápido y confiable)"""
        print(f"📄 Intentando extraer texto de PDF: {file_path}")
        try:
            if not PYMUPDF_AVAILABLE:
                print("❌ PyMuPDF no disponible para extraer PDF")
                return ""
                
            text = ""
            with fitz.open(file_path) as doc:
                print(f"📑 PDF tiene {doc.page_count} páginas")
                for page_num, page in enumerate(doc):
                    page_text = page.get_text()
                    text += page_text + "\n"
                    print(f"📝 Página {page_num + 1}: {len(page_text)} caracteres")
            
            print(f"✅ Texto extraído del PDF: {len(text)} caracteres totales")
            return text
            
        except Exception as e:
            print(f"❌ Error extrayendo texto PDF: {e}")
            return ""

    @staticmethod
    def extract_text_from_image(file_path: str) -> str:
        """Extrae texto de imágenes usando Tesseract"""
        print(f"🖼️ Intentando extraer texto de imagen: {file_path}")
        try:
            if not TESSERACT_AVAILABLE:
                print("❌ Tesseract no disponible para extraer imagen")
                return ""
                
            img = Image.open(file_path)
            print(f"🖼️ Imagen cargada: {img.size} - Modo: {img.mode}")
            
            # Preprocesamiento básico
            img = img.convert('L')  # Escala de grises
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(2.0)
            
            # Configuración para facturas
            config = '--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789€$.,abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ /-'
            text = pytesseract.image_to_string(img, config=config)
            
            print(f"✅ Texto extraído de imagen: {len(text)} caracteres")
            return text
            
        except Exception as e:
            print(f"❌ Error extrayendo texto de imagen: {e}")
            return ""

    @staticmethod
    def smart_amount_extraction(text: str) -> Tuple[Decimal, Decimal, Decimal]:
        """
        ✅ VERSIÓN MEJORADA: Maneja descuentos y términos "Paid" con prioridad
        """
        print("🔍 Iniciando extracción inteligente de montos MEJORADA...")
        text_lower = text.lower()
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        total = Decimal('0')
        vat = Decimal('0')
        discount = Decimal('0')
        paid_amount = Decimal('0')
        
        print(f"📊 Analizando {len(lines)} líneas de texto...")
        
        # ✅ ESTRATEGIA MEJORADA: Buscar por líneas con palabras clave ESPECÍFICAS
        for i, line in enumerate(lines):
            line_lower = line.lower()
            
            # ✅ EXCLUIR SUBTOTAL EXPLÍCITAMENTE
            if 'subtotal' in line_lower:
                print(f"⏭️ Saltando línea de subtotal: {line}")
                continue
            
            # ✅ BUSCAR "PAID" COMO TOTAL ALTERNATIVO (ALTA PRIORIDAD)
            paid_keywords = ['paid', 'amount paid', 'total paid', 'paid amount']
            if any(keyword in line_lower for keyword in paid_keywords):
                print(f"💳 Línea {i} contiene PALABRA CLAVE DE PAGO: {line}")
                amounts = InvoiceOCR._extract_amounts_from_line(line, allow_negative=False)
                print(f"💳 Montos PAID encontrados en línea {i}: {amounts}")
                if amounts:
                    paid_amount = max(paid_amount, max(amounts))
                    print(f"✅ PAID identificado: {paid_amount}")
            
            # ✅ BUSCAR DESCUENTOS
            if any(keyword in line_lower for keyword in InvoiceOCR.DISCOUNT_KEYWORDS):
                print(f"🎫 Línea {i} contiene PALABRA CLAVE DE DESCUENTO: {line}")
                amounts = InvoiceOCR._extract_amounts_from_line(line, allow_negative=True)
                print(f"🎫 Montos DESCUENTO encontrados en línea {i}: {amounts}")
                if amounts:
                    # Para descuentos, tomar el valor más negativo o el único
                    discount_amount = min(amounts)  # Esto capturará valores negativos
                    if discount_amount < 0:
                        discount += discount_amount
                        print(f"✅ Descuento identificado: {discount}")
                    else:
                        # Si el descuento está escrito como positivo pero en contexto negativo
                        discount_amount = -abs(discount_amount)
                        discount += discount_amount
                        print(f"✅ Descuento (convertido a negativo): {discount}")
            
            # ✅ BUSCAR TOTAL (como antes, pero con prioridad menor que PAID)
            total_keywords = [kw for kw in InvoiceOCR.TOTAL_KEYWORDS if kw not in paid_keywords]
            if any(keyword in line_lower for keyword in total_keywords):
                print(f"💰 Línea {i} contiene palabra clave de TOTAL: {line}")
                amounts = InvoiceOCR._extract_amounts_from_line(line)
                print(f"💰 Montos encontrados en línea {i}: {amounts}")
                if amounts:
                    total = max(total, max(amounts))
                    print(f"✅ Total actualizado: {total}")
            
            # ✅ BUSCAR VAT
            if any(keyword in line_lower for keyword in InvoiceOCR.VAT_KEYWORDS):
                print(f"🧾 Línea {i} contiene palabra clave de VAT: {line}")
                amounts = InvoiceOCR._extract_amounts_from_line(line)
                print(f"🧾 Montos VAT encontrados en línea {i}: {amounts}")
                if amounts:
                    base_amount = paid_amount if paid_amount > 0 else total
                    valid_vat = [amt for amt in amounts if 0 < amt <= base_amount]
                    if valid_vat:
                        vat = max(vat, max(valid_vat))
                        print(f"✅ VAT actualizado: {vat}")
        
        # ✅ LÓGICA MEJORADA PARA DETERMINAR EL TOTAL FINAL
        if paid_amount > 0:
            # Si encontramos "Paid", usarlo como total principal
            final_total = paid_amount
            print(f"✅ Usando PAID como total final: {final_total}")
        else:
            final_total = total
            print(f"✅ Usando TOTAL convencional: {final_total}")
        
        # ✅ APLICAR DESCUENTOS AL CÁLCULO
        if discount < 0:
            print(f"🎫 Aplicando descuento de {abs(discount)} al análisis")
            # El descuento ya es negativo, así que se resta
            adjusted_total = final_total + discount  # discount es negativo, así que resta
            if adjusted_total > 0:
                final_total = adjusted_total
                print(f"✅ Total después de descuento: {final_total}")
        
        # ✅ ESTRATEGIA DE FALLBACK si no se encontró total
        if final_total == 0:
            print("🔍 No se encontró total por palabras clave, buscando montos significativos...")
            all_amounts = []
            for line in lines:
                line_amounts = InvoiceOCR._extract_amounts_from_line(line)
                all_amounts.extend(line_amounts)
            
            print(f"🔍 Todos los montos encontrados: {all_amounts}")
            if all_amounts:
                significant_amounts = [amt for amt in all_amounts if amt > 5]  # Montos razonables
                print(f"🔍 Montos significativos (>5): {significant_amounts}")
                if significant_amounts:
                    final_total = max(significant_amounts)
                    print(f"✅ Total por fallback: {final_total}")
        
        # ✅ CALCULAR VAT SI NO SE ENCONTRÓ
        if vat == 0 and final_total > 0:
            vat = (final_total * Decimal('0.23')).quantize(Decimal('0.01'))
            print(f"🧮 VAT calculado automáticamente (23%): {vat}")
        
        print(f"📊 RESULTADO FINAL MEJORADO - Total: {final_total}, VAT: {vat}, Discount: {discount}, Paid: {paid_amount}")
        return final_total, vat, discount

    @staticmethod
    def _extract_amounts_from_line(line: str, allow_negative: bool = False) -> List[Decimal]:
        """✅ VERSIÓN MEJORADA: Maneja montos negativos para descuentos"""
        print(f"🔍 Analizando línea para montos: '{line}'")
        
        # ✅ PATRONES MEJORADOS para permitir signos negativos
        sign_pattern = r'-?' if allow_negative else r''
        
        patterns = [
            # Formato europeo con signo opcional
            fr'{sign_pattern}€?\s*(\d{{1,3}}(?:\.\d{{3}})*(?:,\d{{2}}))',
            fr'{sign_pattern}€?\s*(\d{{1,3}}(?:,\d{{3}})*(?:\.\d{{2}}))',
            fr'{sign_pattern}€?\s*(\d+(?:,\d{{2}}))',
            fr'{sign_pattern}€?\s*(\d+(?:\.\d{{2}}))',
            # Montos al final de línea con signo opcional
            fr'{sign_pattern}(\d{{1,3}}(?:\.\d{{3}})*(?:,\d{{2}}))\s*€',
            fr'{sign_pattern}(\d{{1,3}}(?:,\d{{3}})*(?:\.\d{{2}}))\s*€',
        ]
        
        amounts = []
        for pattern_idx, pattern in enumerate(patterns):
            matches = re.findall(pattern, line)
            if matches:
                print(f"🔍 Patrón {pattern_idx} encontró matches: {matches}")
                for match in matches:
                    try:
                        # ✅ DETECTAR SI ES NEGATIVO
                        is_negative = match.strip().startswith('-')
                        clean_match = match.replace('-', '').strip()
                        
                        # DETERMINAR EL FORMATO BASADO EN EL PATRÓN
                        if pattern_idx in [0, 4]:  # Patrones europeos: 10.000,00
                            # FORMATO EUROPEO: quitar puntos de miles, convertir coma decimal a punto
                            clean_num = clean_match.replace('.', '').replace(',', '.')
                            print(f"🔍 Formato europeo detectado: '{match}' -> '{clean_num}'")
                        elif pattern_idx in [1, 5]:  # Patrones americanos: 10,000.00
                            # FORMATO AMERICANO: quitar comas de miles, dejar punto decimal
                            clean_num = clean_match.replace(',', '')
                            print(f"🔍 Formato americano detectado: '{match}' -> '{clean_num}'")
                        else:
                            # Formatos simples - determinar por el contenido
                            if ',' in clean_match and '.' in clean_match:
                                # Tiene ambos - determinar cuál es el decimal
                                if clean_match.rfind(',') > clean_match.rfind('.'):
                                    clean_num = clean_match.replace('.', '').replace(',', '.')  # Europeo
                                else:
                                    clean_num = clean_match.replace(',', '')  # Americano
                            elif ',' in clean_match:
                                # Solo coma - asumir decimal europeo
                                clean_num = clean_match.replace(',', '.')
                            else:
                                # Solo punto - asumir decimal americano
                                clean_num = clean_match
                            print(f"🔍 Formato simple detectado: '{match}' -> '{clean_num}'")
                        
                        amount = Decimal(clean_num)
                        if is_negative:
                            amount = -amount
                            
                        if amount > 0 or (allow_negative and amount < 0):
                            amounts.append(amount)
                            print(f"✅ Monto extraído: {amount} (de: '{match}')")
                        else:
                            print(f"⚠️ Monto cero ignorado: {amount} (de: '{match}')")
                            
                    except (InvalidOperation, ValueError) as e:
                        print(f"❌ Error convirtiendo monto '{match}': {e}")
                        continue
        
        print(f"📊 Montos extraídos de la línea: {amounts}")
        return amounts

    @staticmethod
    def extract_supplier_name(text: str) -> str:
        """✅ VERSIÓN MEJORADA: Excluye mejor frases no relevantes"""
        print("🏢 Extrayendo nombre del proveedor MEJORADO...")
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        for i, line in enumerate(lines[:10]):
            clean_line = line.strip()
            print(f"🔍 Línea {i} candidata: '{clean_line}'")
            
            # ✅ EXCLUSIONES MEJORADAS
            should_exclude = (
                len(clean_line) < 3 or
                len(clean_line) > 100 or
                any(exclude_phrase in clean_line.lower() for exclude_phrase in InvoiceOCR.SUPPLIER_EXCLUDE_PHRASES) or
                re.match(r'^\d+[/-]\d+[/-]\d+$', clean_line) or
                clean_line.isdigit() or
                re.search(r'€?\s*\d+[,.]\d+', clean_line)  # Excluir líneas con montos
            )
            
            if not should_exclude:
                # ✅ PRIORIZAR dominios web y nombres comerciales
                if re.search(r'[a-zA-Z]{3,}\.[a-zA-Z]{2,}', clean_line):  # Como "budsidesk.com"
                    print(f"✅ Proveedor identificado (dominio web): '{clean_line}'")
                    return clean_line[:100]
                elif re.search(r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*', clean_line):  # Nombres propios
                    print(f"✅ Proveedor identificado (nombre): '{clean_line}'")
                    return clean_line[:100]
        
        print("❌ No se pudo identificar proveedor, usando valor por defecto")
        return "Supplier Not Identified"

    @staticmethod
    def extract_date(text: str) -> str:
        """Extrae fecha con múltiples formatos - MEJORADO"""
        print("📅 Extrayendo fecha...")
        
        # Patrones adicionales para formatos sin separadores
        additional_patterns = [
            r'\b(\d{2})(\d{2})(\d{4})\b',  # 24032025 -> 24/03/2025
            r'\b(\d{4})(\d{2})(\d{2})\b',  # 20250324 -> 2025/03/24
        ]
        
        all_patterns = InvoiceOCR.DATE_PATTERNS + additional_patterns
        
        for pattern_idx, pattern in enumerate(all_patterns):
            matches = re.findall(pattern, text)
            if matches:
                date_match = matches[0]
                print(f"🔍 Patrón {pattern_idx} encontró fecha: {date_match}")
                
                # Si el patrón tiene grupos (como dd mm yyyy separados)
                if isinstance(date_match, tuple):
                    date_str = ''.join(date_match)
                    # Intentar diferentes combinaciones
                    possible_formats = [
                        "%d%m%Y",  # 24032025
                        "%Y%m%d",  # 20250324
                        "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", 
                        "%d/%m/%y", "%d-%m-%y", "%Y/%m/%d",
                        "%d %b %Y", "%d %B %Y"
                    ]
                else:
                    date_str = date_match
                    possible_formats = [
                        "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", 
                        "%d/%m/%y", "%d-%m-%y", "%Y/%m/%d",
                        "%d %b %Y", "%d %B %Y", "%d%m%Y", "%Y%m%d"
                    ]
                
                for fmt in possible_formats:
                    try:
                        parsed_date = datetime.strptime(date_str, fmt)
                        formatted_date = parsed_date.strftime("%Y-%m-%d")
                        print(f"✅ Fecha parseada: {formatted_date} (formato: {fmt})")
                        return formatted_date
                    except ValueError:
                        continue
        
        print("❌ No se pudo extraer fecha")
        return ""

    @classmethod
    def process_invoice(cls, file_path: str) -> Dict:
        """
        ✅ VERSIÓN MEJORADA: Procesa una factura y devuelve datos con descuentos
        """
        print(f"🚀 INICIANDO PROCESAMIENTO OCR MEJORADO: {file_path}")
        
        try:
            # Determinar tipo de archivo y extraer texto
            if file_path.lower().endswith('.pdf'):
                print("📄 Procesando como PDF...")
                text = cls.extract_text_from_pdf(file_path)
            else:
                print("🖼️ Procesando como imagen...")
                text = cls.extract_text_from_image(file_path)
            
            if not text or len(text.strip()) < 10:
                print("❌ No se pudo extraer texto significativo del archivo")
                return cls._get_fallback_result()
            
            print(f"📝 TEXTO EXTRAÍDO (primeros 500 chars):\n{text[:500]}...")
            
            # Extraer información
            print("🔍 Extrayendo información del texto...")
            supplier = cls.extract_supplier_name(text)
            date_str = cls.extract_date(text)
            total, vat, discount = cls.smart_amount_extraction(text)
            
            # Validar resultados
            if total == 0:
                print("⚠️ ADVERTENCIA: No se pudo extraer monto total")
            
            result = {
                'supplier': supplier,
                'date': date_str,
                'total': f"{total:.2f}",
                'vat': f"{vat:.2f}",
                'discount': f"{discount:.2f}",  # ✅ NUEVO CAMPO
                'description': f"Invoice from {supplier}",
                'raw_text_preview': text[:200] + "..." if len(text) > 200 else text,
                'confidence': 'high' if total > 0 else 'low'
            }
            
            print(f"🎉 PROCESAMIENTO MEJORADO COMPLETADO: {result}")
            return result
            
        except Exception as e:
            print(f"💥 ERROR CRÍTICO en process_invoice: {e}")
            return cls._get_fallback_result()

    @staticmethod
    def _get_fallback_result() -> Dict:
        """✅ VERSIÓN MEJORADA: Resultado por defecto con campo discount"""
        print("🔄 Devolviendo resultado de fallback mejorado...")
        return {
            'supplier': 'Supplier Not Identified',
            'date': '',
            'total': '0.00',
            'vat': '0.00',
            'discount': '0.00',  # ✅ NUEVO CAMPO
            'description': 'OCR processing failed',
            'raw_text_preview': '',
            'confidence': 'low'
        }

# Función de compatibilidad (mantener API existente)
def process_invoice(file_path: str) -> dict:
    """Función de compatibilidad con código existente"""
    print(f"🔗 Llamando a process_invoice (compatibilidad) para: {file_path}")
    return InvoiceOCR.process_invoice(file_path)