# 🏭 Extractor de Facturas Eléctricas Panameñas

Sistema automatizado para procesar facturas PDF y exportar datos estructurados a Excel.

## 🚀 Inicio Rápido

### Instalación
```bash
pip install -r requirements.txt
```

### Configuración
1. Crear archivo `.env` con las claves API:
```
OPENAI_API_KEY=tu_clave_openai
LLM_WHISPERER_API_KEY=tu_clave_llm_whisperer
```

### Ejecutar Aplicación
```bash
streamlit run app_streamlit.py --server.port=8505
```

### Acceder
- **URL Local:** http://localhost:8505
- **Interfaz Web:** Simple y amigable para usuarios no técnicos

## 📋 Funcionalidades

- ✅ **Procesamiento Individual:** Una factura PDF
- ✅ **Procesamiento por Lotes:** Hasta 100 facturas
- ✅ **Exportación Excel:** Individual y consolidado
- ✅ **Interfaz Simple:** Para usuarios no técnicos
- ✅ **Progreso Visual:** Barras de progreso y métricas

## � Estructura

```
DEPLOY_FINAL/
├── app_streamlit.py       # Aplicación principal
├── config.py              # Configuración
├── agents_system.py       # Sistema de agentes IA
├── llm_whisperer_wrapper.py # Cliente LLM Whisperer
├── requirements.txt       # Dependencias
├── .env                   # Variables de entorno
├── .streamlit/config.toml # Configuración Streamlit
└── README.md             # Esta documentación
```

## � Archivos Principales

- **app_streamlit.py:** Interfaz web principal
- **config.py:** Manejo de configuración y variables
- **agents_system.py:** Lógica de extracción con IA
- **llm_whisperer_wrapper.py:** Wrapper para LLM Whisperer API

## 💻 Uso

1. **Subir facturas:** PDF individual o múltiples
2. **Procesar:** El sistema extrae automáticamente los datos
3. **Visualizar:** Ver datos estructurados en tablas
4. **Exportar:** Descargar archivos Excel

## 🌐 Deployment

Para deployment en Streamlit Cloud:
1. Subir código a GitHub
2. Conectar repositorio en Streamlit Cloud
3. Configurar secrets (API keys)
4. Deployment automático

## 📊 Soporte

- **Formatos:** PDF (facturas eléctricas panameñas)
- **Salida:** Excel (.xlsx)
- **Procesamiento:** Batch hasta 100 archivos
- **Interfaz:** Web responsive
