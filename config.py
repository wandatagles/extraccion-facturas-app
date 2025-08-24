"""
Utilidades para la configuración de la aplicación
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("app.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class Config:
    """Configuración de la aplicación"""
    
    def __init__(self):
        """Inicializa la configuración cargando variables de entorno"""
        # Cargar variables de entorno
        load_dotenv()
        
        # API Keys - Revisar múltiples nombres de variables
        self.llmwhisperer_api_key = (
            os.getenv("LLMWHISPERER_API_KEY") or 
            os.getenv("WHISPERER_API_KEY") or
            os.getenv("LLM_WHISPERER_API_KEY")
        )
        self.whisperer_api_key = self.llmwhisperer_api_key  # Alias para compatibilidad
        self.llm_whisperer_api_key = self.llmwhisperer_api_key  # Otro alias para compatibilidad
        
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        
        # Configuración de la aplicación
        self.app_name = "Extractor de Facturas"
        self.app_version = "1.0.0"
        
        # Rutas
        self.base_dir = Path(__file__).parent
        self.output_dir = self.base_dir / "output"
        self.temp_dir = self.base_dir / "temp"
        
        # Crear directorios si no existen
        self.output_dir.mkdir(exist_ok=True)
        self.temp_dir.mkdir(exist_ok=True)
        
        # Validar configuración
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Valida que la configuración sea correcta"""
        errors = []
        
        if not self.llmwhisperer_api_key:
            errors.append("LLMWHISPERER_API_KEY no encontrada en .env")
        
        if not self.openai_api_key:
            errors.append("OPENAI_API_KEY no encontrada en .env")
        
        if errors:
            logger.error("❌ Errores de configuración:")
            for error in errors:
                logger.error(f"  - {error}")
            raise ValueError("Configuración incompleta. Revisa tu archivo .env")
        
        logger.info("✅ Configuración validada correctamente")
    
    def get_config_info(self) -> Dict[str, Any]:
        """Retorna información de la configuración"""
        return {
            "app_name": self.app_name,
            "app_version": self.app_version,
            "llmwhisperer_configured": bool(self.llmwhisperer_api_key),
            "openai_configured": bool(self.openai_api_key),
            "openai_model": self.openai_model,
            "base_dir": str(self.base_dir),
            "output_dir": str(self.output_dir),
            "temp_dir": str(self.temp_dir)
        }


def get_supported_formats() -> Dict[str, list]:
    """Retorna los formatos de archivo soportados"""
    return {
        "pdf": ["*.pdf"],
        "images": ["*.png", "*.jpg", "*.jpeg", "*.tiff", "*.bmp"]
    }


def validate_file_path(file_path: str) -> bool:
    """
    Valida que un archivo existe y tiene formato válido
    
    Args:
        file_path: Ruta al archivo
        
    Returns:
        True si el archivo es válido
    """
    try:
        path = Path(file_path)
        
        if not path.exists():
            logger.error(f"❌ Archivo no encontrado: {file_path}")
            return False
        
        if not path.is_file():
            logger.error(f"❌ La ruta no es un archivo: {file_path}")
            return False
        
        # Verificar extensión
        supported_extensions = [".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp"]
        if path.suffix.lower() not in supported_extensions:
            logger.error(f"❌ Formato no soportado: {path.suffix}")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error validando archivo: {str(e)}")
        return False


def get_pdf_files_from_directory(directory_path: str) -> list:
    """
    Obtiene todos los archivos PDF de un directorio
    
    Args:
        directory_path: Ruta al directorio
        
    Returns:
        Lista de rutas a archivos PDF
    """
    try:
        directory = Path(directory_path)
        
        if not directory.exists():
            logger.error(f"❌ Directorio no encontrado: {directory_path}")
            return []
        
        if not directory.is_dir():
            logger.error(f"❌ La ruta no es un directorio: {directory_path}")
            return []
        
        # Buscar archivos PDF
        pdf_files = list(directory.glob("*.pdf"))
        pdf_files.extend(list(directory.glob("*.PDF")))
        
        logger.info(f"📁 Encontrados {len(pdf_files)} archivos PDF en: {directory_path}")
        
        return [str(pdf_file) for pdf_file in pdf_files]
        
    except Exception as e:
        logger.error(f"❌ Error buscando archivos PDF: {str(e)}")
        return []
