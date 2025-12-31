# logic/docs_master.py - VERSIÓN LIMPIA (SOLO METADATOS + MANAGER)
import logging
from pathlib import Path
from django.conf import settings

logger = logging.getLogger(__name__)

# ✅ METADATOS DE DOCUMENTOS (fuente de verdad)
DOCUMENT_METADATA = {
    "non_disclosure": {
        "name": "Non-Disclosure Agreement",
        "description": "Acuerdo de confidencialidad para proteger información sensible",
        "category": "legal",
        "icon": "fa-file-contract",
        "form_url": "non_disclosure_form",
        "generate_url": "generate_non_disclosure"
    },
    "quotation": {
        "name": "Quotation", 
        "description": "Presupuesto y cotización de servicios",
        "category": "business",
        "icon": "fa-file-invoice-dollar",
        "form_url": "quotation_form",
        "generate_url": "generate_quotation"
    },
    "service_agreement": {
        "name": "Service Agreement",
        "description": "Contrato de prestación de servicios", 
        "category": "legal",
        "icon": "fa-handshake",
        "form_url": "service_agreement_form",
        "generate_url": "generate_service_agreement"
    },
    "timesheet": {
        "name": "Timesheet",
        "description": "Registro de horas trabajadas",
        "category": "operations",
        "icon": "fa-clock",
        "form_url": "time_sheet_form", 
        "generate_url": "generate_timesheet"
    },
    "sow": {
        "name": "Statement of Work",
        "description": "Declaración de trabajo con objetivos y entregables",
        "category": "projects",
        "icon": "fa-tasks",
        "form_url": "statement_of_work_form",
        "generate_url": "generate_sow"
    }
}

# ✅ GENERADORES VACÍOS (para futuro)
DOCUMENT_GENERATORS = {}

class DocumentManager:
    """Manager para documentos - MANTENIDO PARA FUTURO USO"""
    
    def list_available_documents(self):
        """Lista documentos disponibles"""
        return DOCUMENT_METADATA
    
    def validate_document_data(self, doc_type, data):
        """Valida datos del documento - PARA FUTURO"""
        required_fields = {
            'non_disclosure': ['parties', 'effective_date', 'confidential_info'],
            'quotation': ['client', 'items', 'total_amount'],
            'service_agreement': ['parties', 'services', 'payment_terms'],
            'timesheet': ['employee', 'period', 'hours'],
            'sow': ['project', 'objectives', 'deliverables']
        }
        
        if doc_type not in required_fields:
            return False, f"Tipo de documento desconocido: {doc_type}"
            
        missing = [field for field in required_fields[doc_type] if field not in data]
        if missing:
            return False, f"Campos requeridos faltantes: {', '.join(missing)}"
            
        return True, "Datos válidos"
    
    def simple_generate_document(self, doc_type, user_id, request=None):
        """Generación simple de documento - PARA FUTURO"""
        logger.info(f"🔧 Generando documento {doc_type} para usuario {user_id}")
        
        # Validar tipo
        if doc_type not in DOCUMENT_METADATA:
            return False, None, f"Tipo de documento no válido: {doc_type}"
            
        # Aquí iría la lógica real de generación cuando la implementes
        # Por ahora solo log
        logger.info(f"📄 Documento {doc_type} procesado (modo simulación)")
        
        return True, None, "Documento generado (modo simulación)"

# ✅ INSTANCIA GLOBAL (para futuro uso)
document_manager = DocumentManager()

# ✅ FUNCIONES DE SERVICIO (para futuro uso)
def get_available_documents():
    """Obtiene metadatos de documentos disponibles"""
    return {
        "documents": DOCUMENT_METADATA,
        "categories": {
            "legal": ["non_disclosure", "service_agreement"],
            "business": ["quotation"], 
            "operations": ["timesheet"],
            "projects": ["sow"]
        }
    }

def get_document_info(doc_type):
    """Obtiene información de un documento específico"""
    return DOCUMENT_METADATA.get(doc_type, {})

def generate_legal_document(doc_type, context_data, user_id):
    """Genera documento legal - PARA FUTURO USO"""
    logger.info(f"🔧 generate_legal_document: {doc_type}, user: {user_id}")
    
    # Simulación - en el futuro aquí generarías DOCX/PDF
    result = {
        "success": True,
        "doc_type": doc_type,
        "user_id": user_id,
        "timestamp": "2024-01-01 12:00:00",
        "pdf_url": None,  # Para futuro
        "docx_url": None, # Para futuro  
        "message": "Documento procesado en modo simulación"
    }
    
    return result

