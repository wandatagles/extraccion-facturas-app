"""
LLMWhisperer Client - Cliente para API de LLMWhisperer V2
========================================================

Este módulo proporciona un wrapper para la API de LLMWhisperer V2,
permitiendo convertir PDFs a texto estructurado con formato ASCII art.
"""

import os
import time
import logging
from typing import Dict, Any, Optional, Union
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from unstract.llmwhisperer import LLMWhispererClientV2
    from unstract.llmwhisperer.client_v2 import LLMWhispererClientException
    LLMWHISPERER_AVAILABLE = True
except ImportError:
    logger.warning("⚠ LLMWhisperer client no disponible")
    LLMWHISPERER_AVAILABLE = False


class LLMWhispererClient:
    """
    Wrapper para el cliente oficial de LLMWhisperer V2

    Características:
    - Usa el cliente oficial de Unstract
    - Conversión de PDFs a texto estructurado
    - Manejo robusto de errores
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://llmwhisperer-api.us-central.unstract.com/api/v2",
    ):
        """
        Inicializa el cliente LLMWhisperer

        Args:
            api_key: API key de LLMWhisperer
            base_url: URL base de la API
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        
        # Verificar si el cliente oficial está disponible
        if not LLMWHISPERER_AVAILABLE:
            logger.error("❌ Cliente oficial de LLMWhisperer no disponible")
            self.client = None
            return

        try:
            # Crear cliente oficial
            self.client = LLMWhispererClientV2(
                base_url=self.base_url, 
                api_key=self.api_key
            )
            logger.info(f"✅ LLMWhisperer Client V2 inicializado - Base URL: {self.base_url}")
        except Exception as e:
            logger.error(f"❌ Error inicializando cliente oficial: {str(e)}")
            self.client = None

    def extract_text_from_pdf(self, pdf_path: Union[str, Path]) -> Optional[str]:
        """
        Alias para convert_pdf_to_structured_text para compatibilidad
        
        Args:
            pdf_path: Ruta al archivo PDF

        Returns:
            Texto estructurado en formato ASCII art, o None si hay error
        """
        return self.convert_pdf_to_structured_text(pdf_path)

    def convert_pdf_to_structured_text(
        self, pdf_path: Union[str, Path]
    ) -> Optional[str]:
        """
        Convierte un PDF a texto estructurado usando LLMWhisperer

        Args:
            pdf_path: Ruta al archivo PDF

        Returns:
            Texto estructurado en formato ASCII art, o None si hay error
        """
        if not self.client:
            logger.error("❌ Cliente LLMWhisperer no disponible")
            return None

        try:
            pdf_path = Path(pdf_path)

            if not pdf_path.exists():
                logger.error(f"❌ Archivo PDF no encontrado: {pdf_path}")
                return None

            if not pdf_path.suffix.lower() == ".pdf":
                logger.error(f"❌ El archivo no es un PDF válido: {pdf_path}")
                return None

            logger.info(f"🔄 Iniciando conversión de PDF: {pdf_path.name}")

            # Usar el método whisper del cliente oficial en modo síncrono
            # Configurar para generar formato ASCII art con tablas
            result = self.client.whisper(
                file_path=str(pdf_path),
                wait_for_completion=True,
                wait_timeout=300,  # 5 minutos
                mode="form",  # Modo específico para tablas estructuradas
                output_mode="layout_preserving",  # Preservar layout
                mark_vertical_lines=True,  # Marcar líneas verticales
                mark_horizontal_lines=True,  # Marcar líneas horizontales
                line_splitter_tolerance=0.4,  # Tolerancia para división de líneas
                horizontal_stretch_factor=1.0  # Factor de estiramiento horizontal
            )

            if result and "extraction" in result and "result_text" in result["extraction"]:
                structured_text = result["extraction"]["result_text"]
                logger.info(f"✅ Conversión completada: {len(structured_text)} caracteres")
                return structured_text
            else:
                logger.error("❌ No se pudo obtener el texto estructurado")
                logger.debug(f"Respuesta recibida: {result}")
                return None

        except LLMWhispererClientException as e:
            logger.error(f"❌ Error de LLMWhisperer: {e.message} (Status: {e.status_code})")
            return None

        except Exception as e:
            logger.error(f"❌ Error en conversión de PDF: {str(e)}")
            return None

    def test_connection(self) -> Dict[str, Any]:
        """
        Prueba la conexión con la API de LLMWhisperer

        Returns:
            Dict con información del estado de la conexión
        """
        if not self.client:
            logger.warning("⚠ Cliente LLMWhisperer no disponible")
            return {
                "connected": False,
                "api_key_valid": False,
                "service_status": "client_unavailable",
                "error": "Cliente no disponible",
            }

        try:
            logger.info("🔍 Probando conexión con LLMWhisperer API...")

            # Intentar obtener información de uso
            usage_info = self.client.get_usage_info()
            
            if usage_info:
                logger.info("✅ Conexión exitosa con LLMWhisperer")
                return {
                    "connected": True,
                    "api_key_valid": True,
                    "service_status": "operational",
                    "base_url": self.base_url,
                    "usage_info": usage_info,
                }
            else:
                logger.warning("⚠ No se pudo obtener información de uso")
                # Aún consideramos que está conectado si no hay errores
                return {
                    "connected": True,
                    "api_key_valid": True,
                    "service_status": "operational",
                    "base_url": self.base_url,
                    "usage_info": None,
                }

        except LLMWhispererClientException as e:
            logger.error(f"❌ Error probando conexión: {e.message} (Status: {e.status_code})")
            return {
                "connected": False,
                "api_key_valid": e.status_code != 401,
                "service_status": "error",
                "error": f"Error de LLMWhisperer: {e.message} (Status: {e.status_code})",
            }
        except Exception as e:
            logger.error(f"❌ Error inesperado probando conexión: {str(e)}")
            return {
                "connected": False,
                "api_key_valid": False,
                "service_status": "error",
                "error": f"Error inesperado: {str(e)}",
            }

    def is_available(self) -> bool:
        """
        Verifica si el cliente está disponible

        Returns:
            True si el cliente está disponible
        """
        return self.client is not None and LLMWHISPERER_AVAILABLE
