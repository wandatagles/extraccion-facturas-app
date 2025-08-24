#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de extracción simplificado usando solo LangChain (sin CrewAI)
Compatible con Streamlit Cloud - Sin dependencias problemáticas
"""

import os
import json
import re
import logging
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleTableExtractionAgent:
    """
    Agente simplificado para extracción de tablas sin CrewAI
    Compatible con Streamlit Cloud
    """
    
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        """
        Inicializa el agente de extracción simple
        
        Args:
            api_key: API key de OpenAI
            model: Modelo de OpenAI a usar
        """
        self.api_key = api_key
        self.model = model
        
        # Configurar LLM
        self.llm = ChatOpenAI(
            api_key=api_key,
            model=model,
            temperature=0.1,
            max_tokens=16000
        )
    
    def extract_tables_from_text(self, ascii_text: str) -> Dict[str, Any]:
        """
        Extrae tablas desde texto ASCII usando LangChain directamente
        
        Args:
            ascii_text: Texto ASCII con tablas de facturas
            
        Returns:
            Dict con datos extraídos estructurados
        """
        logger.info("Iniciando extracción simplificada de tablas")
        
        # PROMPT MEJORADO Y ESPECÍFICO
        prompt = f"""
Analiza esta factura de energía eléctrica de Panamá y extrae TODOS los datos disponibles:

{ascii_text}

INSTRUCCIONES ESPECÍFICAS:

1. NIS COMPLETO: Si ves "NIS: 6012355 002" → extraer "6012355002" (concatenar TODOS los dígitos)

2. VALORES MONETARIOS (convertir comas):
   - "B/. 1.549,19" → 1549.19
   - "B/. 42,68" → 42.68
   - "B/. 3,16" → 3.16

3. CONSUMOS Y LECTURAS:
   - Busca kWh actuales e históricos
   - Busca kW de demanda
   - Busca kVARh reactiva
   - Lecturas anterior/actual del medidor

4. CARGOS ESPECÍFICOS:
   - Generación, Transmisión, Distribución
   - Variaciones por Combustible
   - Compensaciones por Incumplimiento

5. REGLAS CRÍTICAS:
   - Si ves un valor en la factura, extráelo (no pongas 0)
   - Convierte correctamente las comas decimales
   - Busca valores en TODA la factura

RESPONDE SOLO CON ESTE JSON (sin texto adicional):
{{
  "informacion_cliente": {{
    "nombre_cliente": "",
    "direccion": "",
    "ciudad": "",
    "nis": "",
    "contrato": "",
    "ruta": ""
  }},
  "datos_factura": {{
    "numero_factura": "",
    "mes_factura": "",
    "fecha_emision": "",
    "fecha_vencimiento": "",
    "fecha_corte": "",
    "medidor": "",
    "sector": "",
    "tipo_lectura": ""
  }},
  "periodo_lectura": {{
    "fecha_desde": "",
    "fecha_hasta": "",
    "dias": 0,
    "tarifa": ""
  }},
  "lecturas_medidor": {{
    "energia_activa": {{
      "lectura_anterior": 0,
      "lectura_actual": 0,
      "consumo": 0
    }},
    "energia_reactiva": {{
      "consumo": 0
    }},
    "demanda": {{
      "lectura_actual": 0
    }}
  }},
  "cargos_energia": {{
    "generacion": 0,
    "transmision": 0,
    "distribucion": 0,
    "var_combustible": 0,
    "var_transmision": 0,
    "var_generacion": 0
  }},
  "conceptos_facturacion": [
    {{
      "concepto": "Cargo Fijo",
      "importe": 0
    }},
    {{
      "concepto": "Energía",
      "importe": 0
    }},
    {{
      "concepto": "Interés por mora",
      "importe": 0
    }},
    {{
      "concepto": "Subsidio Ley 15 (Recargo)",
      "importe": 0
    }}
  ],
  "historico_consumo": [
    {{
      "mes": "",
      "kwh": 0,
      "importe": 0
    }}
  ],
  "demandas_detalladas": {{
    "demanda_maxima": 0,
    "demanda_punta": 0,
    "demanda_fuera_punta": 0,
    "demanda_generacion": 0
  }},
  "energia_por_franjas": {{
    "energia_punta": 0,
    "energia_fuera_punta": 0,
    "energia_llano": 0
  }},
  "totales": {{
    "total_mes": 0,
    "gran_total": 0,
    "saldo_anterior": 0,
    "saldo_corte": 0
  }},
  "resumen_tabular": {{
    "numero_factura": "",
    "nis": "",
    "mes_factura": "",
    "tarifa": "",
    "periodo_lectura_desde": "",
    "periodo_lectura_hasta": "",
    "tipo_lectura": "",
    "tipo_consumo": "",
    "total_mes": 0,
    "gran_total": 0,
    "historico_consumo_kwh": 0,
    "historico_consumo_kw": 0,
    "reactiva_kvarh": 0,
    "demanda_media_f": 0,
    "interes_por_mora": 0,
    "subsidio_ley_15_recargo": 0,
    "compensacion_por_incumplimiento": 0,
    "cargo_fijo": 0,
    "energia": 0,
    "demanda_maxima": 0,
    "deman_max_gen": 0,
    "demanda_max_punta": 0,
    "demanda_baja_f_punta": 0,
    "energia_punta": 0,
    "energia_f_punta": 0,
    "energia_llano": 0,
    "var_combustible": 0,
    "var_transmision": 0,
    "var_generacion": 0,
    "detalle_energia": [],
    "otros_detalles_factura": {{
      "generacion_kwh": 0,
      "transmision_kwh": 0,
      "distribucion_kwh": 0,
      "compensaciones": 0,
      "ajustes": 0,
      "descuentos": 0
    }}
  }}
}}
"""
        
        try:
            # Crear mensaje y enviar al LLM
            message = HumanMessage(content=prompt)
            response = self.llm([message])
            
            # Extraer contenido de la respuesta
            result_text = response.content
            logger.info("Respuesta recibida del LLM")
            
            # Intentar parsear el JSON resultado
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                result = json.loads(json_str)
                logger.info("Extracción completada exitosamente")
                return result
            else:
                logger.warning("No se encontró JSON válido en la respuesta")
                return self._create_fallback_structure(ascii_text)
                
        except json.JSONDecodeError as e:
            logger.error(f"Error parseando JSON: {e}")
            return self._create_fallback_structure(ascii_text)
        except Exception as e:
            logger.error(f"Error en extracción: {e}")
            return self._create_fallback_structure(ascii_text)
    
    def _create_fallback_structure(self, text: str) -> Dict[str, Any]:
        """Crea una estructura básica en caso de error"""
        return {
            "informacion_cliente": {"nis": ""},
            "datos_factura": {"numero_factura": "", "mes_factura": ""},
            "totales": {"total_mes": 0, "gran_total": 0},
            "resumen_tabular": {
                "nis": "",
                "numero_factura": "",
                "mes_factura": "",
                "total_mes": 0,
                "gran_total": 0
            },
            "texto_original": text[:500] + "..." if len(text) > 500 else text,
            "error": "Fallback structure created due to parsing error"
        }
    
    def process_invoice_text(self, ascii_text: str, output_path: str) -> bool:
        """
        Procesa texto de factura completo: extracción + formateo + guardado en Excel
        
        Args:
            ascii_text: Texto ASCII de la factura
            output_path: Ruta donde guardar el Excel
            
        Returns:
            True si el procesamiento fue exitoso
        """
        try:
            logger.info("Iniciando procesamiento completo de factura (simplificado)")
            
            # Extraer datos estructurados
            extracted_data = self.extract_tables_from_text(ascii_text)
            logger.info("Extracción completada exitosamente")
            
            # Crear Excel con una sola hoja consolidada
            logger.info(f"Guardando en Excel: {output_path}")
            success = self._save_to_excel(extracted_data, output_path)
            
            if success:
                logger.info(f"Procesamiento completado. Excel guardado en: {output_path}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error en procesamiento completo: {e}")
            return False
    
    def _save_to_excel(self, extracted_data: Dict[str, Any], output_path: str) -> bool:
        """
        Guarda SOLO el resumen consolidado en Excel (una sola hoja)
        """
        try:
            import pandas as pd
            from pathlib import Path
            
            # Crear directorio si no existe
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Extraer datos principales
            resumen_tabular = extracted_data.get('resumen_tabular', {})
            datos_factura = extracted_data.get('datos_factura', {})
            totales = extracted_data.get('totales', {})
            cliente = extracted_data.get('informacion_cliente', {})
            periodo = extracted_data.get('periodo_lectura', {})
            conceptos = extracted_data.get('conceptos_facturacion', [])
            cargos_energia = extracted_data.get('cargos_energia', {})
            demandas = extracted_data.get('demandas_detalladas', {})
            energia_franjas = extracted_data.get('energia_por_franjas', {})
            lecturas = extracted_data.get('lecturas_medidor', {})
            otros_detalles = resumen_tabular.get('otros_detalles_factura', {})
            
            # Buscar valores específicos en conceptos
            cargo_fijo = 0
            energia = 0
            interes_mora = 0
            subsidio = 0
            compensacion = 0
            
            for concepto in conceptos:
                nombre = concepto.get('concepto', '').lower()
                importe = concepto.get('importe', 0)
                
                if 'cargo fijo' in nombre or 'fijo' in nombre:
                    cargo_fijo = importe
                elif 'energía' in nombre or 'energia' in nombre:
                    energia = importe
                elif 'interés' in nombre or 'interes' in nombre or 'mora' in nombre:
                    interes_mora = importe
                elif 'subsidio' in nombre or 'ley 15' in nombre:
                    subsidio = importe
                elif 'compensación' in nombre or 'compensacion' in nombre:
                    compensacion = importe
            
            # Crear DataFrame consolidado con una sola fila
            consolidado_data = {
                'Número de factura': resumen_tabular.get('numero_factura') or datos_factura.get('numero_factura', ''),
                'NIS': resumen_tabular.get('nis') or cliente.get('nis', ''),
                'Mes de la factura': resumen_tabular.get('mes_factura') or datos_factura.get('mes_factura', ''),
                'Tarifa': resumen_tabular.get('tarifa') or periodo.get('tarifa', ''),
                'Periodo de lectura desde': resumen_tabular.get('periodo_lectura_desde') or periodo.get('fecha_desde', ''),
                'Periodo de lectura hasta': resumen_tabular.get('periodo_lectura_hasta') or periodo.get('fecha_hasta', ''),
                'Tipo de lectura': resumen_tabular.get('tipo_lectura') or datos_factura.get('tipo_lectura', ''),
                'Tipo de consumo': resumen_tabular.get('tipo_consumo', ''),
                'Total del mes': resumen_tabular.get('total_mes') or totales.get('total_mes', 0),
                'Gran total': resumen_tabular.get('gran_total') or totales.get('gran_total', 0),
                'Saldo anterior': totales.get('saldo_anterior', 0),
                'Saldo a corte': totales.get('saldo_corte', 0),
                
                # Lecturas del medidor
                'Lectura anterior kWh': lecturas.get('energia_activa', {}).get('lectura_anterior', 0),
                'Lectura actual kWh': lecturas.get('energia_activa', {}).get('lectura_actual', 0),
                'Consumo kWh': lecturas.get('energia_activa', {}).get('consumo', 0),
                'Consumo reactiva kVARh': lecturas.get('energia_reactiva', {}).get('consumo', 0),
                'Demanda actual kW': lecturas.get('demanda', {}).get('lectura_actual', 0),
                
                # Conceptos principales
                'Cargo Fijo': resumen_tabular.get('cargo_fijo') or cargo_fijo,
                'Energía': resumen_tabular.get('energia') or energia,
                'Interés por Mora': resumen_tabular.get('interes_por_mora') or interes_mora,
                'Subsidio Ley 15 (Recargo)': resumen_tabular.get('subsidio_ley_15_recargo') or subsidio,
                'Compensación por Incumplimiento': resumen_tabular.get('compensacion_por_incumplimiento') or compensacion,
                
                # Cargos de energía
                'Generación': cargos_energia.get('generacion', 0),
                'Transmisión': cargos_energia.get('transmision', 0),
                'Distribución': cargos_energia.get('distribucion', 0),
                'Var. Combustible': resumen_tabular.get('var_combustible') or cargos_energia.get('var_combustible', 0),
                'Var. Transmisión': resumen_tabular.get('var_transmision') or cargos_energia.get('var_transmision', 0),
                'Var. Generación': resumen_tabular.get('var_generacion') or cargos_energia.get('var_generacion', 0),
                
                # Demandas
                'Demanda Máxima': resumen_tabular.get('demanda_maxima') or demandas.get('demanda_maxima', 0),
                'Demanda Max. Punta': resumen_tabular.get('demanda_max_punta') or demandas.get('demanda_punta', 0),
                'Demanda Fuera Punta': resumen_tabular.get('demanda_baja_f_punta') or demandas.get('demanda_fuera_punta', 0),
                
                # Energía por franjas
                'Energía Punta': resumen_tabular.get('energia_punta') or energia_franjas.get('energia_punta', 0),
                'Energía F. Punta': resumen_tabular.get('energia_f_punta') or energia_franjas.get('energia_fuera_punta', 0),
                'Energía Llano': resumen_tabular.get('energia_llano') or energia_franjas.get('energia_llano', 0)
            }
            
            # Crear DataFrame con una sola fila
            df_consolidado = pd.DataFrame([consolidado_data])
            
            # Guardar en Excel
            df_consolidado.to_excel(output_path, sheet_name='Resumen_Consolidado', index=False)
            
            # Estadísticas
            campos_llenos = sum(1 for v in consolidado_data.values() if v and v != 0 and v != "")
            
            logger.info(f"✅ Excel consolidado guardado: {output_path}")
            logger.info(f"📊 Campos extraídos: {campos_llenos}/{len(consolidado_data)}")
            logger.info(f"🆔 NIS: {consolidado_data['NIS']}")
            logger.info(f"💰 Total: {consolidado_data['Gran total']}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error guardando Excel: {e}")
            return False

# Alias para compatibilidad con el código existente
TableExtractionAgent = SimpleTableExtractionAgent
