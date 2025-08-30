#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏭 EXTRACTOR DE FACTURAS ELÉCTRICAS PANAMEÑAS
Aplicación web simple y fácil de usar para procesamiento por lotes
"""

import streamlit as st
import os
import tempfile
from pathlib import Path
import pandas as pd
from datetime import datetime
import time
import logging

# Configurar logging
logger = logging.getLogger(__name__)
import logging

# Configurar logging
logger = logging.getLogger(__name__)

# Importar módulos locales
try:
    from config import Config
    from llm_whisperer_wrapper import LLMWhispererClient  
    from agents_system import TableExtractionAgent
except Exception as e:
    st.error(f"Error cargando el sistema: {e}")
    st.stop()

# Configuración de la página
st.set_page_config(
    page_title="🏭 Extractor de Facturas",
    page_icon="🏭",
    layout="wide"
)

# Variables de sesión
if 'extracted_data' not in st.session_state:
    st.session_state.extracted_data = {}
if 'batch_results' not in st.session_state:
    st.session_state.batch_results = []
if 'config' not in st.session_state:
    st.session_state.config = None
if 'whisperer_client' not in st.session_state:
    st.session_state.whisperer_client = None
if 'extraction_agent' not in st.session_state:
    st.session_state.extraction_agent = None

def initialize_services():
    """Inicializar servicios"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        config = Config()
        
        if not config.openai_api_key:
            st.error("❌ Falta configuración de OpenAI")
            st.info("Configure su clave API de OpenAI en .env o secretos de Streamlit")
            return False
        
        if not config.llm_whisperer_api_key:
            st.error("❌ Falta configuración de LLM Whisperer")
            st.info("Configure su clave API de LLM Whisperer en .env o secretos de Streamlit")
            return False
            
        whisperer_client = LLMWhispererClient(config.llm_whisperer_api_key)
        extraction_agent = TableExtractionAgent(config.openai_api_key, config.openai_model)
        
        # Guardar en sesión
        st.session_state.config = config
        st.session_state.whisperer_client = whisperer_client
        st.session_state.extraction_agent = extraction_agent
        
        return True
        
    except Exception as e:
        st.error(f"❌ Error de configuración: {e}")
        return False

def process_single_pdf(pdf_file, file_name: str):
    """Procesar un PDF individual con optimización de memoria"""
    temp_path = None
    excel_filename = None
    
    try:
        # Crear archivo temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            pdf_file.seek(0)
            temp_file.write(pdf_file.read())
            temp_path = temp_file.name
        
        # Extraer texto con validación mejorada
        extracted_text = st.session_state.whisperer_client.extract_text_from_pdf(temp_path)
        
        if not extracted_text or len(extracted_text.strip()) < 50:
            return None
        
        # Procesar con agentes
        excel_filename = f"temp_{file_name.replace('.pdf', '').replace(' ', '_')}.xlsx"
        success = st.session_state.extraction_agent.process_invoice_text(extracted_text, excel_filename)
        
        if success and os.path.exists(excel_filename):
            # Leer datos del Excel
            df = pd.read_excel(excel_filename)
            
            # Crear resultado
            result = {
                'filename': file_name,
                'extracted_text': extracted_text[:2000],  # Limitar texto para memoria
                'structured_data': df,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'rows_extracted': len(df),
                'columns_extracted': len(df.columns)
            }
            
            # Limpiar inmediatamente
            del extracted_text  # Liberar memoria del texto
            
            return result
        
        return None
        
    except Exception as e:
        logger.error(f"Error procesando {file_name}: {str(e)}")
        return None
    finally:
        # Limpiar archivos temporales siempre
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except:
                pass
        if excel_filename and os.path.exists(excel_filename):
            try:
                os.unlink(excel_filename)
            except:
                pass

def process_batch_pdfs(uploaded_files, batch_size=5):
    """Procesar PDFs en lotes con máxima calidad y estabilidad"""
    
    total_files = len(uploaded_files)
    success_count = 0
    error_count = 0
    
    # Mostrar progreso
    st.subheader(f"🔄 Procesando {total_files} facturas con máxima precisión...")
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Contenedor para mostrar archivos procesados en tiempo real
    results_container = st.empty()
    
    # Limpiar resultados anteriores del lote
    st.session_state.batch_results = []
    
    # Procesar archivos en lotes pequeños para máxima estabilidad
    for batch_start in range(0, total_files, batch_size):
        batch_end = min(batch_start + batch_size, total_files)
        current_batch = uploaded_files[batch_start:batch_end]
        
        lote_num = batch_start // batch_size + 1
        total_lotes = (total_files - 1) // batch_size + 1
        
        status_text.text(f"📦 Procesando lote {lote_num} de {total_lotes} (Calidad Máxima)")
        
        for i, uploaded_file in enumerate(current_batch):
            current_file_index = batch_start + i + 1
            
            # Actualizar progreso
            progress = current_file_index / total_files
            progress_bar.progress(progress)
            status_text.text(f"📄 Archivo {current_file_index}/{total_files}: {uploaded_file.name}")
            
            # Procesar archivo con reintentos
            max_retries = 2
            result = None
            
            for retry in range(max_retries + 1):
                try:
                    if retry > 0:
                        status_text.text(f"🔄 Reintentando archivo {current_file_index}/{total_files}: {uploaded_file.name} (Intento {retry + 1})")
                        time.sleep(retry * 2)  # Delay progresivo
                    
                    result = process_single_pdf(uploaded_file, uploaded_file.name)
                    
                    if result:
                        break  # Éxito, salir del loop de reintentos
                        
                except Exception as e:
                    if retry == max_retries:
                        logger.error(f"Error final procesando {uploaded_file.name}: {str(e)}")
            
            # Registrar resultado
            if result:
                st.session_state.extracted_data[uploaded_file.name] = result
                st.session_state.batch_results.append({
                    'archivo': uploaded_file.name,
                    'estado': 'Exitoso ✅',
                    'filas_extraidas': result['rows_extracted'],
                    'fecha': result['timestamp']
                })
                success_count += 1
            else:
                st.session_state.batch_results.append({
                    'archivo': uploaded_file.name,
                    'estado': 'Error ❌',
                    'filas_extraidas': 0,
                    'fecha': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                error_count += 1
            
            # Mostrar progreso en tiempo real
            if st.session_state.batch_results:
                with results_container.container():
                    st.markdown("### 📊 Progreso en Tiempo Real")
                    recent_results = st.session_state.batch_results[-5:]  # Últimos 5
                    for result in recent_results:
                        col1, col2, col3 = st.columns([3, 1, 1])
                        with col1:
                            st.text(f"• {result['archivo']}")
                        with col2:
                            st.text(result['estado'])
                        with col3:
                            st.text(f"{result['filas_extraidas']} filas")
            
            # Delay inteligente entre archivos (mayor estabilidad)
            if current_file_index < total_files:
                time.sleep(1.5)  # Aumentado para mayor estabilidad
        
        # Delay entre lotes para estabilidad de APIs
        if batch_end < total_files:
            status_text.text(f"⏸️ Pausa entre lotes para optimizar calidad...")
            time.sleep(3)  # Pausa más larga entre lotes
    
    # Completar progreso
    progress_bar.progress(1.0)
    status_text.text("✅ Procesamiento completado con máxima calidad")
    
    return success_count, error_count

def main():
    """Función principal - Interfaz simple"""
    
    # Título
    st.title("🏭 Extractor de Facturas Eléctricas")
    st.markdown("**Sistema automatizado para procesar facturas PDF**")
    
    # Inicializar servicios
    if not st.session_state.config:
        with st.spinner("⚙️ Configurando sistema..."):
            if not initialize_services():
                st.stop()
        st.success("✅ Sistema listo para usar")
    
    # Crear pestañas principales
    tab1, tab2, tab3 = st.tabs(["📄 Procesar Facturas", "📊 Ver Resultados", "📥 Exportar"])
    
    with tab1:
        st.header("📄 Subir y Procesar Facturas")
        
        # Mostrar información del sistema
        if st.session_state.extracted_data:
            st.success(f"📊 {len(st.session_state.extracted_data)} facturas ya procesadas")
        
        st.markdown("---")
        
        # Opciones de carga
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📄 Una Factura")
            single_file = st.file_uploader(
                "Seleccione un archivo PDF:",
                type=['pdf'],
                key="single_upload",
                help="Arrastre y suelte su factura aquí"
            )
            
            if single_file:
                st.info(f"📄 **{single_file.name}** ({single_file.size:,} bytes)")
                
                if st.button("🔄 Procesar Factura", key="process_single", type="primary"):
                    with st.spinner("Procesando factura..."):
                        result = process_single_pdf(single_file, single_file.name)
                        
                        if result:
                            st.session_state.extracted_data[single_file.name] = result
                            st.success(f"✅ ¡Factura procesada exitosamente!")
                            st.success(f"📊 Se extrajeron **{result['rows_extracted']} filas** de datos")
                            st.balloons()
                        else:
                            st.error("❌ No se pudo procesar la factura")
                            st.error("💡 Verifique que el PDF contenga una factura válida")
        
        with col2:
            st.subheader("📁 Múltiples Facturas")
            multiple_files = st.file_uploader(
                "Seleccione múltiples archivos PDF:",
                type=['pdf'],
                accept_multiple_files=True,
                key="multiple_upload",
                help="Puede seleccionar hasta 100 archivos"
            )
            
            if multiple_files:
                num_files = len(multiple_files)
                st.success(f"📄 **{num_files} archivos** seleccionados")
                
                # Mostrar lista de archivos (primeros 5)
                with st.expander(f"👁️ Ver archivos ({min(5, num_files)} de {num_files})"):
                    for i, file in enumerate(multiple_files[:5]):
                        st.text(f"• {file.name}")
                    if num_files > 5:
                        st.text(f"... y {num_files - 5} archivos más")
                
                # Configuración optimizada para calidad máxima
                col_config1, col_config2 = st.columns(2)
                with col_config1:
                    batch_size = st.selectbox(
                        "Procesar en grupos de:",
                        [3, 5, 8],  # Lotes más pequeños para máxima estabilidad
                        index=1,  # Default = 5
                        help="Grupos pequeños = Mayor estabilidad y calidad"
                    )
                
                with col_config2:
                    st.info(f"⏱️ Tiempo estimado: {num_files * 4} segundos")
                    st.success("🎯 Configurado para máxima precisión")
                
                if st.button("🔄 Procesar Todas las Facturas", key="process_batch", type="primary"):
                    # Procesar archivos
                    success_count, error_count = process_batch_pdfs(multiple_files, batch_size)
                    
                    # Mostrar resumen
                    st.markdown("---")
                    st.subheader("📊 Resumen del Procesamiento")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("📄 Total", num_files)
                    with col2:
                        st.metric("✅ Exitosos", success_count)
                    with col3:
                        st.metric("❌ Con errores", error_count)
                    
                    if success_count > 0:
                        st.success(f"🎉 **{success_count} facturas procesadas exitosamente**")
                    
                    if error_count > 0:
                        st.warning(f"⚠️ **{error_count} facturas tuvieron errores**")
                    
                    # Mostrar resultados detallados
                    if st.session_state.batch_results:
                        st.subheader("📋 Resultados Detallados")
                        results_df = pd.DataFrame(st.session_state.batch_results)
                        st.dataframe(results_df, use_container_width=True)
                        
                        # Opción para guardar reporte
                        if st.button("💾 Guardar Reporte de Procesamiento"):
                            report_filename = f"reporte_procesamiento_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                            results_df.to_excel(report_filename, index=False)
                            st.success(f"✅ Reporte guardado: {report_filename}")
    
    with tab2:
        st.header("📊 Facturas Procesadas")
        
        if not st.session_state.extracted_data:
            st.info("📭 No hay facturas procesadas aún")
            st.info("💡 Use la pestaña **'Procesar Facturas'** para subir y procesar archivos")
        else:
            st.success(f"📄 **{len(st.session_state.extracted_data)} facturas** procesadas")
            
            # Botón para limpiar resultados
            if st.button("🗑️ Limpiar Todos los Resultados", type="secondary"):
                st.session_state.extracted_data = {}
                st.session_state.batch_results = []
                st.success("✅ Resultados limpiados")
                st.rerun()
            
            st.markdown("---")
            
            # Selector de archivo
            selected_file = st.selectbox(
                "Seleccione una factura para ver:",
                list(st.session_state.extracted_data.keys()),
                help="Puede ver los datos extraídos de cada factura"
            )
            
            if selected_file:
                data = st.session_state.extracted_data[selected_file]
                
                # Información básica
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("📄 Archivo", selected_file.split('.')[0])
                with col2:
                    st.metric("📊 Filas extraídas", data['rows_extracted'])
                with col3:
                    st.metric("📋 Columnas", data['columns_extracted'])
                
                # Mostrar datos extraídos
                st.subheader("📊 Datos Extraídos")
                if isinstance(data['structured_data'], pd.DataFrame):
                    st.dataframe(data['structured_data'], use_container_width=True)
                    
                    # Estadísticas adicionales
                    st.info(f"📅 Procesado el {data['timestamp']}")
                
                # Opción para ver texto original
                with st.expander("📄 Ver texto extraído del PDF (avanzado)"):
                    # Mostrar solo los primeros 1000 caracteres para no sobrecargar
                    text_preview = data['extracted_text'][:1000]
                    if len(data['extracted_text']) > 1000:
                        text_preview += "\n\n... (texto truncado para visualización)"
                    
                    st.text_area(
                        "Contenido extraído:",
                        text_preview,
                        height=200,
                        disabled=True
                    )
    
    with tab3:
        st.header("📥 Exportar Resultados")
        
        if not st.session_state.extracted_data:
            st.info("📭 No hay datos para exportar")
            st.info("💡 Primero procese algunas facturas")
        else:
            st.success(f"📄 Listo para exportar **{len(st.session_state.extracted_data)} facturas**")
            
            # Seleccionar archivos
            files_to_export = st.multiselect(
                "Seleccione facturas para exportar:",
                list(st.session_state.extracted_data.keys()),
                default=list(st.session_state.extracted_data.keys()),
                help="Puede exportar todas o solo algunas facturas"
            )
            
            if files_to_export:
                st.info(f"📊 Se exportarán **{len(files_to_export)} facturas**")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("📄 Archivos Separados")
                    st.markdown("*Un archivo Excel por cada factura*")
                    
                    if st.button("📊 Crear Archivos Individuales", type="primary"):
                        created_files = []
                        
                        for filename in files_to_export:
                            data = st.session_state.extracted_data[filename]
                            
                            if isinstance(data['structured_data'], pd.DataFrame):
                                # Crear nombre limpio para el archivo
                                clean_name = filename.replace('.pdf', '').replace(' ', '_')
                                output_name = f"{clean_name}_datos.xlsx"
                                
                                # Guardar Excel
                                data['structured_data'].to_excel(output_name, index=False)
                                created_files.append(output_name)
                        
                        if created_files:
                            st.success(f"✅ **{len(created_files)} archivos** creados exitosamente")
                            
                            # Mostrar archivos con botones de descarga
                            for file in created_files:
                                col_file1, col_file2 = st.columns([3, 1])
                                with col_file1:
                                    st.text(f"• {file}")
                                with col_file2:
                                    with open(file, 'rb') as f:
                                        st.download_button(
                                            label="⬇️",
                                            data=f.read(),
                                            file_name=file,
                                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                            key=f"download_{file}"
                                        )
                
                with col2:
                    st.subheader("📋 Archivo Consolidado")
                    st.markdown("*Todas las facturas en un solo archivo*")
                    
                    if st.button("📊 Crear Archivo Consolidado", type="secondary"):
                        all_data = []
                        
                        for filename in files_to_export:
                            data = st.session_state.extracted_data[filename]
                            
                            if isinstance(data['structured_data'], pd.DataFrame):
                                df_copy = data['structured_data'].copy()
                                df_copy['archivo_origen'] = filename
                                df_copy['fecha_procesamiento'] = data['timestamp']
                                all_data.append(df_copy)
                        
                        if all_data:
                            consolidated_df = pd.concat(all_data, ignore_index=True)
                            output_name = f"facturas_consolidadas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                            
                            consolidated_df.to_excel(output_name, index=False)
                            st.success(f"✅ **Archivo consolidado creado**: {output_name}")
                            
                            # Mostrar estadísticas
                            st.info(f"📊 **{len(consolidated_df)} filas** de **{len(files_to_export)} facturas**")
                            
                            # Botón de descarga
                            with open(output_name, 'rb') as file:
                                st.download_button(
                                    label=f"⬇️ Descargar {output_name}",
                                    data=file.read(),
                                    file_name=output_name,
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    type="primary"
                                )
                            
                            # Mostrar preview pequeño
                            with st.expander("👁️ Vista Previa del Archivo Consolidado"):
                                st.dataframe(consolidated_df.head(10), use_container_width=True)
                                if len(consolidated_df) > 10:
                                    st.info(f"... y {len(consolidated_df) - 10} filas más en el archivo")

if __name__ == "__main__":
    main()
