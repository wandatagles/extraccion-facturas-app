#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de agentes mejorado con resumen tabular
"""

import os
import json
import re
import logging
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List
from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TableExtractionAgent:
    """
    Agente especializado en extracción de tablas con resumen tabular
    """
    
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        """
        Inicializa el agente de extracción
        
        Args:
            api_key: API key de OpenAI
            model: Modelo de OpenAI a usar
        """
        self.api_key = api_key
        self.model = model
        
        # Configurar LLM con parámetros optimizados para precisión
        self.llm = ChatOpenAI(
            api_key=api_key,
            model=model,
            temperature=0.0,  # Máxima consistencia
            max_tokens=16000,  # Máximo soportado por gpt-4o-mini
            request_timeout=180,  # Timeout más corto pero suficiente
            max_retries=3  # Reintentos automáticos
        )
        
        # Agente especializado en extracción de tablas
        self.table_extractor = Agent(
            role='Especialista en Extracción de Tablas',
            goal='Extraer y estructurar datos de facturas desde texto ASCII',
            backstory="""Eres un experto analista de documentos financieros especializado en facturas de servicios públicos.
            Tu especialidad es identificar y extraer información estructurada de facturas de energía eléctrica,
            sin importar cómo esté formateada. Tienes experiencia interpretando tablas ASCII, números,
            fechas, códigos de cliente y toda la información relevante para el procesamiento automático
            de facturas. Eres meticuloso y nunca pierdes detalles importantes.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )
    
    def extract_tables_from_text(self, ascii_text: str) -> Dict[str, Any]:
        """
        Extrae tablas desde texto ASCII usando el agente especializado con prompt mejorado
        
        Args:
            ascii_text: Texto ASCII con tablas de facturas
            
        Returns:
            Dict con datos extraídos estructurados con valores reales
        """
        logger.info("Iniciando extracción MEJORADA de tablas con agentes")
        
        # PROMPT MEJORADO - MÁS ESPECÍFICO PARA TODOS LOS CAMPOS CON CORRECCIÓN DE TOTALES
        prompt_mejorado = f"""
Analiza LÍNEA POR LÍNEA esta factura de energía eléctrica de Panamá y extrae TODOS los datos disponibles:

{ascii_text}

INSTRUCCIONES ESPECÍFICAS - BUSCA CADA CAMPO:

1. NIS COMPLETO: Si ves "NIS: 6012355 002" → extraer "6012355002" (concatenar TODOS los dígitos)

2. VALORES MONETARIOS (convertir comas):
   - "B/. 1.549,19" → 1549.19
   - "B/. 42,68" → 42.68
   - "B/. 3,16" → 3.16

3. CONSUMOS Y LECTURAS:
   - Busca kWh actuales y históricos
   - Busca kW de demanda
   - Busca kVARh reactiva
   - Lecturas anterior/actual del medidor

4. CARGOS ESPECÍFICOS DE ENERGÍA:
   - Generación: Busca "Generación" y su valor en B/.
   - Transmisión: Busca "Transmisión" y su valor en B/.
   - Distribución: Busca "Distribución" y su valor en B/.

5. CAMPO SECTOR:
   - SECTOR: Busca "Sector" o campo que indica clasificación como "Residencial", "No Residencial", "Comercial", "Industrial"
   - Si ves "No Residencial" → va en campo "sector"
   - Si ves "Residencial" → va en campo "sector"

6. OTROS DETALLES IMPORTANTES:
   - Variación por Combustible: Busca "Combustible" y valor
   - Compensación por Incumplimiento: Busca "Compensación" o "Incumplimiento"
   - Demandas por tipo (Punta, Fuera Punta, etc.)
   - Energía por franjas horarias

7. HISTÓRICO COMPLETO:
   - Extrae TODOS los meses mostrados con kWh e importes
   - No omitas ningún mes que aparezca en la tabla

8. ⚠️ TOTALES - DIFERENCIA CRÍTICA:
   - "TOTAL ESTE MES" o "Total Este Mes": Es el total SOLO de este período de facturación
   - "GRAN TOTAL" o "Gran Total": Es el total INCLUYENDO saldos pendientes anteriores
   - Busca específicamente cada campo en su ubicación en la factura
   - Extrae el valor que aparece junto a "TOTAL ESTE MES" para "total_mes"
   - Extrae el valor que aparece junto a "GRAN TOTAL" para "gran_total"
   - Si ambos campos muestran el mismo valor en la factura, está bien que coincidan
   - AMBOS campos SIEMPRE deben estar presentes y extraídos correctamente

REGLAS CRÍTICAS:
- SI VES UN VALOR EN LA FACTURA, EXTRÁELO (no pongas 0)
- Convierte correctamente las comas decimales y de miles
- Busca valores en TODA la factura, no solo en una sección
- Extrae cada campo desde su ubicación específica, no copies valores entre campos

RESPONDE SOLO CON ESTE JSON (sin texto adicional):"""
        
        # Definir tarea de extracción
        extraction_task = Task(
            description=prompt_mejorado + """
{
  "informacion_cliente": {
    "nombre_cliente": "",
    "direccion": "",
    "ciudad": "",
    "nis": "6012355002",
    "contrato": "",
    "ruta": ""
  },
  "datos_factura": {
    "numero_factura": "",
    "mes_factura": "",
    "fecha_emision": "",
    "fecha_vencimiento": "",
    "fecha_corte": "",
    "medidor": "",
    "sector": "",
    "tipo_lectura": ""
  },
  "periodo_lectura": {
    "fecha_desde": "",
    "fecha_hasta": "",
    "dias": 0,
    "tarifa": ""
  },
  "lecturas_medidor": {
    "energia_activa": {
      "lectura_anterior": 0,
      "lectura_actual": 0,
      "consumo": 0
    },
    "energia_reactiva": {
      "consumo": 0
    },
    "demanda": {
      "lectura_actual": 0
    }
  },
  "cargos_energia": {
    "generacion": 0,
    "transmision": 0,
    "distribucion": 0,
    "var_combustible": 0,
    "var_transmision": 0,
    "var_generacion": 0
  },
  "conceptos_facturacion": [
    {
      "concepto": "Cargo Fijo",
      "importe": 3.16
    },
    {
      "concepto": "Energía",
      "importe": 1534.72
    },
    {
      "concepto": "Interés por mora",
      "importe": 2.08
    },
    {
      "concepto": "Subsidio Ley 15 (Recargo)",
      "importe": 9.23
    },
    {
      "concepto": "Variación por Combustible",
      "importe": 0
    },
    {
      "concepto": "Compensación por Incumplimiento",
      "importe": 0
    }
  ],
  "historico_consumo": [
    {
      "mes": "Ene-2025",
      "kwh": 5280,
      "importe": 77.60
    },
    {
      "mes": "Dic-2024",
      "kwh": 5760,
      "importe": 67.36
    }
  ],
  "demandas_detalladas": {
    "demanda_maxima": 0,
    "demanda_punta": 0,
    "demanda_fuera_punta": 0,
    "demanda_generacion": 0
  },
  "energia_por_franjas": {
    "energia_punta": 0,
    "energia_fuera_punta": 0,
    "energia_llano": 0
  },
  "totales": {
    "total_mes": 1549.19,
    "gran_total": 1551.27,
    "saldo_anterior": 0,
    "saldo_corte": 0
  },
  "resumen_tabular": {
    "numero_factura": "",
    "nis": "6012355002",
    "mes_factura": "",
    "tarifa": "",
    "periodo_lectura_desde": "",
    "periodo_lectura_hasta": "",
    "tipo_lectura": "",
    "sector": "",
    "total_mes": 1549.19,
    "gran_total": 1549.19,
    "historico_consumo_kwh": 5280,
    "historico_consumo_kw": 0.485,
    "reactiva_kvarh": 480,
    "demanda_media_f": 0,
    "interes_por_mora": 2.08,
    "subsidio_ley_15_recargo": 9.23,
    "compensacion_por_incumplimiento": 0,
    "cargo_fijo": 3.16,
    "energia": 1534.72,
    "demanda_maxima": 0,
    "deman_max_gen": 0,
    "demanda_max_punta": 0,
    "demanda_baja_f_punta": 0,
    "energia_punta": 0,
    "energia_f_punta": 0,
    "energia_llano": 0,
    "var_combustible": 0,
    "var_transmision": 64.19,
    "var_generacion": 1111.70,
    "detalle_energia": [],
    "otros_detalles_factura": {
      "generacion_kwh": 0,
      "transmision_kwh": 0,
      "distribucion_kwh": 0,
      "compensaciones": 0,
      "ajustes": 0,
      "descuentos": 0
    }
  }
}

IMPORTANTE: Busca valores específicos en la factura para CADA campo. Si ves números o importes, extráelos correctamente.

⚠️ RECORDATORIO CRÍTICO PARA SECTOR:
- Si encuentras "Residencial", "No Residencial", "Comercial", "Industrial" → va en campo "sector"
- Extrae el valor del sector desde su ubicación específica en la factura""",
            agent=self.table_extractor,
            expected_output="JSON estructurado con TODOS los datos reales de la factura (sin ceros falsos) incluyendo resumen_tabular"
        )
        
        # Crear crew y ejecutar
        crew = Crew(
            agents=[self.table_extractor],
            tasks=[extraction_task],
            verbose=True
        )
        
        try:
            result = crew.kickoff()
            logger.info("Extracción completada exitosamente")
            
            # Convertir CrewOutput a string y luego parsear JSON
            result_str = str(result)
            
            # Intentar parsear el JSON resultado
            if isinstance(result_str, str):
                # Limpiar posible texto adicional y extraer JSON
                json_match = re.search(r'\{.*\}', result_str, re.DOTALL)
                if json_match:
                    json_str = json_match.group()
                    return json.loads(json_str)
                else:
                    # Si no hay JSON válido, intentar parsear directamente
                    return json.loads(result_str)
            else:
                return result_str
                
        except json.JSONDecodeError as e:
            logger.error(f"Error parseando JSON del agente: {e}")
            return None  # Devolver None en lugar de fallback
        except Exception as e:
            logger.error(f"Error en extracción de tablas: {e}")
            return None  # Devolver None en lugar de fallback
    
    def _create_fallback_structure(self, text: str) -> Dict[str, Any]:
        """Crea una estructura básica en caso de error"""
        return {
            "informacion_cliente": {},
            "datos_factura": {},
            "resumen_tabular": {},
            "texto_original": text[:500] + "..." if len(text) > 500 else text
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
            logger.info("Iniciando procesamiento completo de factura")
            
            # Extraer datos estructurados
            extracted_data = self.extract_tables_from_text(ascii_text)
            
            # Verificar si la extracción fue exitosa
            if extracted_data is None:
                logger.error("La extracción de datos falló - no se pudo procesar la factura")
                return False
                
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
        
        Args:
            extracted_data: Datos extraídos por el agente
            output_path: Ruta del archivo Excel
            
        Returns:
            True si se guardó exitosamente
        """
        try:
            import pandas as pd
            from pathlib import Path
            
            # Crear directorio si no existe
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Extraer datos del resumen tabular y otras secciones
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
            var_combustible = 0
            var_transmision = 0
            var_generacion = 0
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
                elif 'combustible' in nombre:
                    var_combustible = importe
                elif 'transmisión' in nombre or 'transmision' in nombre:
                    var_transmision = importe
                elif 'generación' in nombre or 'generacion' in nombre:
                    var_generacion = importe
                elif 'interés' in nombre or 'interes' in nombre or 'mora' in nombre:
                    interes_mora = importe
                elif 'subsidio' in nombre or 'ley 15' in nombre:
                    subsidio = importe
                elif 'compensación' in nombre or 'compensacion' in nombre or 'incumplimiento' in nombre:
                    compensacion = importe
            
            # Crear DataFrame con UNA SOLA FILA con TODOS los campos consolidados
            consolidado_data = {
                'Número de factura': resumen_tabular.get('numero_factura') or datos_factura.get('numero_factura', ''),
                'NIS': resumen_tabular.get('nis') or cliente.get('nis', ''),
                'Mes de la factura': resumen_tabular.get('mes_factura') or datos_factura.get('mes_factura', ''),
                'Tarifa': resumen_tabular.get('tarifa') or periodo.get('tarifa', ''),
                'Periodo de lectura desde': resumen_tabular.get('periodo_lectura_desde') or periodo.get('fecha_desde', ''),
                'Periodo de lectura hasta': resumen_tabular.get('periodo_lectura_hasta') or periodo.get('fecha_hasta', ''),
                'Tipo de lectura': resumen_tabular.get('tipo_lectura') or datos_factura.get('tipo_lectura', ''),
                'Sector': resumen_tabular.get('sector') or datos_factura.get('sector', ''),
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
                
                # Histórico
                'Histórico consumo kWh': resumen_tabular.get('historico_consumo_kwh', 0),
                'Histórico consumo kW': resumen_tabular.get('historico_consumo_kw', 0),
                'Reactiva kVARh': resumen_tabular.get('reactiva_kvarh', 0),
                
                # Demandas detalladas
                'Demanda Media F': resumen_tabular.get('demanda_media_f', 0),
                'Demanda Máxima': resumen_tabular.get('demanda_maxima') or demandas.get('demanda_maxima', 0),
                'Deman. Max. Gen.': resumen_tabular.get('deman_max_gen') or demandas.get('demanda_generacion', 0),
                'Demanda Max. Punta': resumen_tabular.get('demanda_max_punta') or demandas.get('demanda_punta', 0),
                'Demanda Baja F. Punta': resumen_tabular.get('demanda_baja_f_punta') or demandas.get('demanda_fuera_punta', 0),
                
                # Energía por franjas
                'Energía Punta': resumen_tabular.get('energia_punta') or energia_franjas.get('energia_punta', 0),
                'Energía F. Punta': resumen_tabular.get('energia_f_punta') or energia_franjas.get('energia_fuera_punta', 0),
                'Energía Llano': resumen_tabular.get('energia_llano') or energia_franjas.get('energia_llano', 0),
                
                # Conceptos de facturación
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
                
                # Otros detalles
                'Generación kWh': otros_detalles.get('generacion_kwh', 0),
                'Transmisión kWh': otros_detalles.get('transmision_kwh', 0),
                'Distribución kWh': otros_detalles.get('distribucion_kwh', 0),
                'Compensaciones': otros_detalles.get('compensaciones', 0),
                'Ajustes': otros_detalles.get('ajustes', 0),
                'Descuentos': otros_detalles.get('descuentos', 0),
                
                'Detalle Energía (kWh e importe)': str(resumen_tabular.get('detalle_energia', []))
            }
            
            # Crear DataFrame con una sola fila
            df_consolidado = pd.DataFrame([consolidado_data])
            
            # Guardar SOLO el consolidado en una sola hoja
            df_consolidado.to_excel(output_path, sheet_name='Resumen_Consolidado', index=False)
            
            # Contar campos no vacíos para validación
            campos_llenos = sum(1 for v in consolidado_data.values() if v and v != 0 and v != "")
            
            logger.info(f"✅ Excel consolidado guardado exitosamente: {output_path}")
            logger.info(f"📊 Campos extraídos correctamente: {campos_llenos}/{len(consolidado_data)}")
            logger.info(f"🆔 NIS extraído: {consolidado_data['NIS']}")
            logger.info(f"💰 Total extraído: {consolidado_data['Gran total']}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error guardando Excel: {e}")
            return False

def test_agent_v2():
    """Test del agente v2 con resumen tabular"""
    from config import Config
    
    config = Config()
    agent = TableExtractionAgent(config.openai_api_key, config.openai_model)
    
    # Leer archivo de prueba
    with open('resultado_tabla_mode.txt', 'r', encoding='utf-8') as f:
        text = f.read()
    
    print('🤖 Ejecutando extracción con agente V2...')
    result = agent.extract_tables_from_text(text)
    
    if 'resumen_tabular' in result:
        print('✅ RESUMEN TABULAR ENCONTRADO!')
        resumen = result['resumen_tabular']
        print(f'📄 Número factura: {resumen.get("numero_factura", "N/A")}')
        print(f'🆔 NIS: {resumen.get("nis", "N/A")}')
        print(f'📅 Mes: {resumen.get("mes_factura", "N/A")}')
        print(f'💰 Total: {resumen.get("gran_total", "N/A")}')
        
        # Guardar resultado para verificación
        with open('test_resumen_tabular_result.json', 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print('💾 Resultado guardado en: test_resumen_tabular_result.json')
        
    else:
        print('❌ No se encontró resumen tabular')
        print(f'📋 Claves disponibles: {list(result.keys())}')

if __name__ == "__main__":
    test_agent_v2()
