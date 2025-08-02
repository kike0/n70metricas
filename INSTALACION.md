# 🚀 Guía de Instalación - Sistema de Reportes de Redes Sociales

## 📋 Requisitos Previos

- Python 3.11 o superior
- pip (gestor de paquetes de Python)
- Token de API de Apify
- Git (para clonar el repositorio)

## 🔧 Instalación

### 1. Clonar el Repositorio

```bash
git clone https://gitlab.com/n70/Metricassocialmedia.git
cd Metricassocialmedia
```

### 2. Crear Entorno Virtual

```bash
python3 -m venv venv
source venv/bin/activate  # En Linux/Mac
# o
venv\Scripts\activate     # En Windows
```

### 3. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar Variables de Entorno

Edita el archivo `src/config.py` y añade tu token de Apify:

```python
APIFY_API_TOKEN = "tu_token_de_apify_aqui"
```

### 5. Ejecutar la Aplicación

```bash
cd src
python main.py
```

La aplicación estará disponible en: `http://localhost:5000`

## 🌐 Despliegue en Producción

### Opción 1: Despliegue Local con Puerto Expuesto

```bash
# Ejecutar en modo producción
python main.py
```

### Opción 2: Despliegue en Servidor

1. Configura un servidor web (nginx, Apache)
2. Usa un servidor WSGI (gunicorn, uWSGI)
3. Configura variables de entorno de producción

```bash
# Ejemplo con gunicorn
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 main:app
```

## 📊 Uso del Sistema

### 1. Crear Campaña

1. Accede a la interfaz web
2. Crea una nueva campaña
3. Añade perfiles de redes sociales

### 2. Extraer Datos

1. Selecciona la campaña
2. Haz clic en "Extraer Datos"
3. Espera a que se complete la extracción

### 3. Generar Reportes

1. Ve a la sección de reportes
2. Selecciona el período deseado
3. Genera reporte en PDF

## 🔑 Configuración de Apify

### Obtener Token de API

1. Ve a [Apify Console](https://console.apify.com/)
2. Accede a Settings → Integrations
3. Copia tu API Token
4. Pégalo en `src/config.py`

### Herramientas de Apify Utilizadas

- **Facebook Scraper**: Para extraer datos de Facebook
- **Instagram Scraper**: Para métricas de Instagram
- **Twitter Scraper**: Para análisis de Twitter/X
- **TikTok Scraper**: Para datos de TikTok
- **Sentiment Analysis**: Para análisis de sentimiento

## 📁 Estructura del Proyecto

```
Metricassocialmedia/
├── src/
│   ├── main.py                 # Aplicación principal
│   ├── config.py              # Configuración
│   ├── models/                # Modelos de datos
│   ├── routes/                # Rutas de API
│   ├── services/              # Servicios (Apify, PDF)
│   └── static/                # Frontend
├── reports/                   # Reportes generados
├── requirements.txt           # Dependencias
├── README.md                  # Documentación
└── DEMO.md                   # Guía de demostración
```

## 🛠️ Funcionalidades Principales

### Backend (Flask)
- ✅ API REST completa
- ✅ Integración con Apify
- ✅ Base de datos SQLite
- ✅ Generación de PDFs
- ✅ Análisis de métricas

### Frontend (HTML/JS)
- ✅ Interfaz web responsive
- ✅ Gestión de campañas
- ✅ Visualización de datos
- ✅ Descarga de reportes

### Reportes PDF
- ✅ Métricas detalladas por día
- ✅ Top 3 de mejores publicaciones
- ✅ Análisis de tendencias
- ✅ Insights y recomendaciones

## 🔧 Personalización

### Añadir Nuevas Plataformas

1. Edita `src/services/apify_client.py`
2. Añade nuevos scrapers de Apify
3. Actualiza los modelos de datos

### Modificar Reportes

1. Edita `src/services/pdf_report_generator.py`
2. Personaliza el HTML/CSS
3. Añade nuevas métricas

### Configurar Automatización

1. Usa cron jobs para extracción automática
2. Configura webhooks para notificaciones
3. Programa reportes recurrentes

## 🆘 Solución de Problemas

### Error de Token de Apify
- Verifica que el token sea válido
- Asegúrate de tener créditos en Apify

### Error de Dependencias
```bash
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

### Error de Base de Datos
```bash
rm -f database.db  # Eliminar base de datos
python main.py     # Recrear automáticamente
```

## 📞 Soporte

Para soporte técnico o preguntas:
- Revisa la documentación en `README.md`
- Consulta ejemplos en `DEMO.md`
- Verifica logs de la aplicación

## 🔄 Actualizaciones

Para actualizar el sistema:

```bash
git pull origin main
pip install -r requirements.txt --upgrade
```

## 📈 Monitoreo

### Logs de la Aplicación
- Los logs se muestran en la consola
- Configura logging para producción

### Métricas de Uso
- Monitorea el uso de créditos de Apify
- Revisa el rendimiento de la base de datos

¡El sistema está listo para usar! 🎉

