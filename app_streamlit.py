#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏭 EXTRACTOR DE FACTURAS ELÉCTRICAS PANAMEÑAS
Aplicación web con Streamlit - SOLUCIÓN DEFINITIVA
Funcionalidades: PDF Individual/Carpeta → LLM Whisperer → Agentes → Previsualizar → Excel
"""

import streamlit as st
import os
import tempfile
import zipfile
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd
from datetime import datetime
import json
import traceback

# Importar módulos locales
try:
    from config import Config, get_pdf_files_from_directory
    from llm_whisperer_wrapper import LLMWhispererClient  
    from agents_system import TableExtractionAgent
    st.success("✅ Módulos locales importados correctamente")
except Exception as e:
    st.error(f"❌ Error importando módulos: {e}")
    st.stop()

# Configuración de la página
st.set_page_config(
    page_title="🏭 Extractor de Facturas Eléctricas",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Variables de sesión
if 'extracted_data' not in st.session_state:
    st.session_state.extracted_data = {}
if 'processing_status' not in st.session_state:
    st.session_state.processing_status = {}
if 'config' not in st.session_state:
    st.session_state.config = None
if 'whisperer_client' not in st.session_state:
    st.session_state.whisperer_client = None
if 'extraction_agent' not in st.session_state:
    st.session_state.extraction_agent = None

def initialize_services():
    """Inicializar servicios de configuración"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        config = Config()
        
        if not config.openai_api_key:
            st.error("❌ OPENAI_API_KEY no encontrada en archivo .env")
            st.info("Crea un archivo .env con: OPENAI_API_KEY=tu_clave_aqui")
            return False
        
        # Inicializar servicios
        if not config.llm_whisperer_api_key:
            st.error("❌ LLM_WHISPERER_API_KEY no encontrada en archivo .env")
            st.info("Agrega a tu archivo .env: LLM_WHISPERER_API_KEY=tu_clave_llm_whisperer")
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
    """Procesar un solo PDF con feedback detallado"""
    
    status_container = st.container()
    
    with status_container:
        # Crear archivo temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            pdf_file.seek(0)  # Asegurar que estamos al inicio del archivo
            temp_file.write(pdf_file.read())
            temp_path = temp_file.name
        
        try:
            # Paso 1: Extraer texto con LLM Whisperer
            st.info(f"🔄 **Paso 1/3**: Extrayendo texto de {file_name} con LLM Whisperer...")
            
            if not st.session_state.whisperer_client:
                st.error("❌ Cliente LLM Whisperer no disponible")
                return None
            
            extracted_text = st.session_state.whisperer_client.extract_text_from_pdf(temp_path)
            
            if not extracted_text or len(extracted_text.strip()) < 50:
                st.error(f"❌ Error: No se pudo extraer texto válido de {file_name}")
                st.error("💡 Verifica que el PDF contenga texto legible y no esté corrupto")
                return None
                
            st.success(f"✅ **Paso 1 completado**: Extraídos {len(extracted_text)} caracteres de texto")
            
            # Mostrar preview del texto extraído
            with st.expander("👁️ Vista previa del texto extraído"):
                st.text_area("Primeros 500 caracteres:", extracted_text[:500], height=100, disabled=True)
            
            # Paso 2: Procesar con agentes
            st.info(f"🤖 **Paso 2/3**: Procesando con agentes de IA...")
            
            if not st.session_state.extraction_agent:
                st.error("❌ Agente de extracción no disponible")
                return None
            
            # Crear nombre de archivo temporal para Excel
            excel_filename = f"temp_{file_name.replace('.pdf', '')}.xlsx"
            
            success = st.session_state.extraction_agent.process_invoice_text(extracted_text, excel_filename)
            
            if success and os.path.exists(excel_filename):
                st.success(f"✅ **Paso 2 completado**: Datos procesados por IA")
                
                # Paso 3: Cargar y estructurar datos
                st.info(f"📊 **Paso 3/3**: Estructurando datos finales...")
                
                try:
                    # Leer datos del Excel generado
                    df = pd.read_excel(excel_filename)
                    
                    # Limpiar archivo temporal de Excel
                    os.unlink(excel_filename)
                    
                    st.success(f"✅ **Procesamiento completado exitosamente para {file_name}**")
                    st.success(f"📊 Extraídas {len(df)} filas con {len(df.columns)} columnas")
                    
                    # Mostrar preview de los datos
                    with st.expander("👁️ Vista previa de datos estructurados"):
                        st.dataframe(df.head(), use_container_width=True)
                    
                    return {
                        'filename': file_name,
                        'extracted_text': extracted_text,
                        'structured_data': df,
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'rows_extracted': len(df),
                        'columns_extracted': len(df.columns)
                    }
                    
                except Exception as e:
                    st.error(f"❌ Error leyendo datos del Excel: {e}")
                    return None
                    
            else:
                st.error(f"❌ Error: Los agentes no pudieron procesar {file_name}")
                st.error("💡 Verifica la configuración de OpenAI y que el texto contenga información de factura válida")
                return None
                
        except Exception as e:
            st.error(f"❌ Error inesperado procesando {file_name}: {e}")
            st.error(f"🔧 Detalles técnicos: {traceback.format_exc()}")
            return None
        finally:
            # Limpiar archivo temporal PDF
            if os.path.exists(temp_path):
                os.unlink(temp_path)

def main():
    """Función principal de la aplicación"""
    
    # Verificar que estamos ejecutando correctamente
    st.write("🔄 Iniciando aplicación...")
    
    # Título principal
    st.title("🏭 EXTRACTOR DE FACTURAS ELÉCTRICAS PANAMEÑAS")
    st.markdown("**Sistema automatizado con LLM Whisperer + CrewAI + OpenAI**")
    st.markdown("---")
    
    # Mensaje de bienvenida
    st.success("✅ Aplicación cargada correctamente")
    
    # Sidebar con configuración
    with st.sidebar:
        st.header("⚙️ Configuración")
        
        if st.button("🔄 Reinicializar Servicios"):
            st.session_state.config = None
            st.session_state.whisperer_client = None
            st.session_state.extraction_agent = None
            st.rerun()
        
        # Verificar configuración
        if not st.session_state.config:
            with st.spinner("Inicializando servicios..."):
                if initialize_services():
                    st.success("✅ Servicios inicializados")
                else:
                    st.error("❌ Error en configuración")
                    st.stop()
        else:
            st.success("✅ Servicios listos")
        
        st.markdown("---")
        st.markdown("**📊 Estado de Procesamiento**")
        
        total_processed = len(st.session_state.extracted_data)
        st.metric("Archivos procesados", total_processed)
        
        if total_processed > 0:
            if st.button("🗑️ Limpiar Resultados"):
                st.session_state.extracted_data = {}
                st.rerun()
    
    # Pestañas principales
    tab1, tab2, tab3 = st.tabs(["📄 Procesar PDFs", "📊 Resultados", "📥 Exportar"])
    
    with tab1:
        st.header("📄 Subir y Procesar Facturas PDF")
        
        st.info("💡 **Flujo de procesamiento**: PDF → LLM Whisperer (extracción texto) → Agentes IA (análisis) → Excel estructurado")
        
        # Opciones de subida
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📄 PDF Individual")
            
            uploaded_file = st.file_uploader(
                "Selecciona un archivo PDF",
                type=['pdf'],
                key="single_pdf",
                help="Arrastra y suelta tu factura PDF aquí"
            )
            
            if uploaded_file is not None:
                st.info(f"📄 Archivo: {uploaded_file.name}")
                st.info(f"📏 Tamaño: {uploaded_file.size:,} bytes")
                
                if st.button("🚀 Procesar PDF Individual", type="primary"):
                    with st.spinner("Procesando..."):
                        result = process_single_pdf(uploaded_file, uploaded_file.name)
                        if result:
                            st.session_state.extracted_data[uploaded_file.name] = result
                            st.success(f"✅ {uploaded_file.name} procesado exitosamente")
                            st.balloons()
                            st.rerun()
        
        with col2:
            st.subheader("📁 Múltiples PDFs")
            
            uploaded_files = st.file_uploader(
                "Selecciona múltiples archivos PDF",
                type=['pdf'],
                accept_multiple_files=True,
                key="multiple_pdfs",
                help="Puedes seleccionar varios PDFs a la vez"
            )
            
            if uploaded_files:
                st.info(f"📁 {len(uploaded_files)} archivos seleccionados")
                for file in uploaded_files:
                    st.text(f"• {file.name} ({file.size:,} bytes)")
                
                if st.button("🚀 Procesar Todos los PDFs", type="primary"):
                    
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    success_count = 0
                    
                    for i, file in enumerate(uploaded_files):
                        status_text.text(f"Procesando {i+1}/{len(uploaded_files)}: {file.name}")
                        
                        result = process_single_pdf(file, file.name)
                        if result:
                            st.session_state.extracted_data[file.name] = result
                            success_count += 1
                        
                        progress_bar.progress((i + 1) / len(uploaded_files))
                    
                    status_text.success(f"✅ Procesamiento completado: {success_count}/{len(uploaded_files)} archivos exitosos")
                    st.balloons()
                    st.rerun()
    
    with tab2:
        st.header("📊 Resultados del Procesamiento")
        
        if not st.session_state.extracted_data:
            st.info("📭 No hay resultados aún. Procesa algunos PDFs en la pestaña anterior.")
            st.info("💡 El flujo es: Subir PDF → Procesar → Ver resultados aquí")
        else:
            # Lista de archivos procesados
            st.subheader("📋 Archivos Procesados")
            
            selected_file = st.selectbox(
                "Selecciona un archivo para ver detalles:",
                list(st.session_state.extracted_data.keys())
            )
            
            if selected_file:
                data = st.session_state.extracted_data[selected_file]
                
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    st.metric("📄 Archivo", selected_file)
                    st.metric("🕐 Procesado", data['timestamp'])
                
                with col2:
                    if isinstance(data['structured_data'], pd.DataFrame):
                        st.metric("📊 Filas extraídas", len(data['structured_data']))
                        st.metric("📋 Columnas", len(data['structured_data'].columns))
                
                # Pestañas de detalles
                detail_tab1, detail_tab2 = st.tabs(["📊 Datos Estructurados", "📄 Texto Extraído"])
                
                with detail_tab1:
                    st.subheader("📊 Datos Estructurados")
                    if isinstance(data['structured_data'], pd.DataFrame):
                        st.dataframe(data['structured_data'], use_container_width=True)
                    else:
                        st.text(str(data['structured_data']))
                
                with detail_tab2:
                    st.subheader("📄 Texto Extraído por LLM Whisperer")
                    st.text_area(
                        "Contenido ASCII:",
                        data['extracted_text'],
                        height=400,
                        disabled=True
                    )
    
    with tab3:
        st.header("📥 Exportar Resultados")
        
        if not st.session_state.extracted_data:
            st.info("📭 No hay datos para exportar. Procesa algunos PDFs primero.")
            st.info("💡 Después de procesar PDFs, podrás exportar los resultados a Excel aquí")
        else:
            st.subheader("📊 Opciones de Exportación")
            
            # Seleccionar archivos para exportar
            files_to_export = st.multiselect(
                "Selecciona archivos para exportar:",
                list(st.session_state.extracted_data.keys()),
                default=list(st.session_state.extracted_data.keys())
            )
            
            if files_to_export:
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("📊 Exportar Excel Individual", type="primary"):
                        for filename in files_to_export:
                            data = st.session_state.extracted_data[filename]
                            
                            if isinstance(data['structured_data'], pd.DataFrame):
                                # Crear nombre de archivo de salida
                                output_name = f"{Path(filename).stem}_extraido.xlsx"
                                
                                # Guardar Excel
                                data['structured_data'].to_excel(output_name, index=False)
                                
                                st.success(f"✅ {output_name} guardado")
                                
                                # Opción de descarga
                                with open(output_name, 'rb') as file:
                                    st.download_button(
                                        label=f"⬇️ Descargar {output_name}",
                                        data=file.read(),
                                        file_name=output_name,
                                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                    )
                
                with col2:
                    if st.button("📋 Exportar Excel Consolidado", type="secondary"):
                        # Consolidar todos los datos
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
                            st.success(f"✅ {output_name} guardado")
                            
                            # Mostrar preview
                            st.subheader("📊 Preview Consolidado")
                            st.dataframe(consolidated_df, use_container_width=True)
                            
                            # Opción de descarga
                            with open(output_name, 'rb') as file:
                                st.download_button(
                                    label=f"⬇️ Descargar {output_name}",
                                    data=file.read(),
                                    file_name=output_name,
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                )

    # Footer
    st.markdown("---")
    st.markdown("**🏭 Extractor de Facturas Eléctricas Panameñas** | Powered by LLM Whisperer + CrewAI + OpenAI")
    
    # Información de debug
    with st.expander("🔧 Información de Debug"):
        st.write("**Estado de la sesión:**")
        st.write(f"- Archivos procesados: {len(st.session_state.extracted_data)}")
        st.write(f"- Configuración cargada: {st.session_state.config is not None}")
        st.write(f"- Whisperer disponible: {st.session_state.whisperer_client is not None}")
        st.write(f"- Agente disponible: {st.session_state.extraction_agent is not None}")

if __name__ == "__main__":
    main()
