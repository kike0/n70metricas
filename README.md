# 🚀 Sistema de Reportes de Redes Sociales con Apify

Sistema completo para generar reportes automatizados de métricas de redes sociales, análisis de anuncios publicitarios y análisis de sentimiento, utilizando la plataforma Apify para extracción de datos.

## 📋 Características Principales

### 🔍 Extracción de Datos
- **Facebook**: Posts, comentarios, reacciones, métricas de engagement
- **Instagram**: Posts, stories, comentarios, métricas de interacción
- **Twitter/X**: Tweets, retweets, likes, menciones
- **TikTok**: Videos, likes, comentarios, shares, visualizaciones
- **YouTube**: Videos, comentarios, visualizaciones, suscriptores

### 📊 Análisis de Métricas
- Cálculo automático de engagement rate
- Análisis de crecimiento de seguidores
- Métricas de interacciones por plataforma
- Comparativas entre períodos
- Análisis de rendimiento de contenido

### 🎯 Análisis Publicitario
- Integración con Facebook Ads Library
- Monitoreo de gastos publicitarios
- Análisis de campañas activas
- Seguimiento de anuncios políticos

### 💭 Análisis de Sentimiento
- Análisis automático de sentimiento en comentarios
- Monitoreo de menciones en tiempo real
- Generación de nubes de palabras
- Tracking de tendencias de opinión

### 📄 Generación de Reportes
- Reportes en PDF con formato profesional
- Plantillas personalizables
- Programación automática de reportes
- Exportación en múltiples formatos

## 🏗️ Arquitectura del Sistema

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend       │    │   Apify API     │
│   (HTML/CSS/JS) │◄──►│   (Flask)       │◄──►│   (Scrapers)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   Database      │
                       │   (SQLite)      │
                       └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   PDF Reports   │
                       │   (ReportLab)   │
                       └─────────────────┘
```

## 🛠️ Tecnologías Utilizadas

### Backend
- **Flask**: Framework web para Python
- **SQLAlchemy**: ORM para base de datos
- **Apify Client**: Cliente oficial de Apify
- **ReportLab**: Generación de PDFs
- **Matplotlib/Seaborn**: Visualizaciones y gráficos
- **Pandas**: Procesamiento de datos

### Frontend
- **HTML5/CSS3**: Estructura y estilos
- **JavaScript**: Interactividad y llamadas a API
- **Responsive Design**: Compatible con móviles

### Base de Datos
- **SQLite**: Base de datos ligera y eficiente

## 📁 Estructura del Proyecto

```
social-media-reports/
├── src/
│   ├── models/
│   │   ├── user.py              # Modelo de usuarios
│   │   └── campaign.py          # Modelos de campañas y métricas
│   ├── routes/
│   │   ├── user.py              # Rutas de usuarios
│   │   ├── campaigns.py         # Rutas de campañas
│   │   └── reports.py           # Rutas de reportes
│   ├── services/
│   │   ├── apify_client.py      # Cliente de Apify
│   │   └── report_generator.py  # Generador de reportes
│   ├── static/
│   │   └── index.html           # Frontend web
│   ├── config.py                # Configuración del sistema
│   └── main.py                  # Punto de entrada
├── reports/                     # Reportes generados
├── requirements.txt             # Dependencias
└── README.md                    # Documentación
```

## 🚀 Instalación y Configuración

### 1. Clonar el Repositorio
```bash
git clone <repository-url>
cd social-media-reports
```

### 2. Crear Entorno Virtual
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

### 3. Instalar Dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar Token de Apify
Editar `src/config.py` y añadir tu token de Apify:
```python
APIFY_API_TOKEN = "tu_token_aqui"
```

### 5. Ejecutar la Aplicación
```bash
python src/main.py
```

La aplicación estará disponible en `http://localhost:5000`

## 📖 Uso del Sistema

### 1. Crear una Campaña
- Accede a la interfaz web
- Completa el formulario de "Gestión de Campañas"
- Define nombre, descripción y frecuencia de reportes

### 2. Añadir Perfiles de Redes Sociales
- Selecciona la campaña creada
- Añade perfiles especificando:
  - Nombre del perfil
  - Plataforma (Facebook, Instagram, etc.)
  - Username o URL del perfil

### 3. Extraer Datos
- Haz clic en "Extraer Datos" en la campaña
- El sistema utilizará Apify para obtener métricas
- Los datos se procesarán y almacenarán automáticamente

### 4. Generar Reportes
- Selecciona la campaña y período de fechas
- Haz clic en "Generar Reporte PDF"
- El reporte se generará en formato profesional

## 🔧 API Endpoints

### Campañas
- `GET /api/campaigns` - Listar campañas
- `POST /api/campaigns` - Crear campaña
- `GET /api/campaigns/{id}` - Obtener campaña específica

### Perfiles
- `POST /api/campaigns/{id}/profiles` - Añadir perfil a campaña
- `POST /api/profiles/{id}/scrape` - Extraer datos de perfil
- `GET /api/profiles/{id}/metrics` - Obtener métricas de perfil

### Reportes
- `POST /api/campaigns/{id}/reports` - Generar reporte
- `GET /api/reports/{id}/download` - Descargar reporte
- `POST /api/test-report` - Generar reporte de prueba

## 🎯 Actores de Apify Utilizados

### Redes Sociales
- `apify/facebook-posts-scraper` - Extracción de Facebook
- `apify/instagram-scraper` - Extracción de Instagram
- `apidojo/tweet-scraper-v2` - Extracción de Twitter/X
- `clockworks/tiktok-scraper` - Extracción de TikTok
- `streamers/youtube-scraper` - Extracción de YouTube

### Análisis Publicitario
- `easyapi/facebook-ads-library-scraper` - Facebook Ads Library
- `curious_coder/facebook-ads-library-scraper` - Ads Library alternativo

### Análisis de Sentimiento
- `tri_angle/social-media-sentiment-analysis-tool` - Análisis de sentimiento
- `scraper_one/facebook-posts-search` - Búsqueda de menciones en Facebook
- `scraper_one/x-posts-search` - Búsqueda de menciones en X

## 📊 Formato de Reportes

Los reportes generados incluyen:

### Métricas por Plataforma
- Seguidores y crecimiento
- Número de publicaciones
- Interacciones totales
- Engagement rate
- Reproducciones de video

### Análisis Publicitario
- Anuncios activos y pautados
- Montos invertidos por período
- Desglose por plataforma

### Análisis de Sentimiento
- Menciones totales
- Usuarios únicos alcanzados
- Impresiones y alcance
- Tendencias de sentimiento

## 🔒 Seguridad

- Token de Apify almacenado de forma segura
- Validación de entrada en todos los endpoints
- Manejo de errores robusto
- Logs de actividad del sistema

## 📈 Escalabilidad

- Arquitectura modular para fácil extensión
- Soporte para múltiples campañas simultáneas
- Procesamiento asíncrono de datos
- Base de datos optimizada para consultas rápidas

## 🤝 Contribución

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📝 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para detalles.

## 📞 Soporte

Para soporte técnico o consultas:
- Crear un issue en el repositorio
- Contactar al equipo de desarrollo

## 🎉 Características Avanzadas

### Programación Automática
- Reportes programados (diario, semanal, mensual)
- Notificaciones automáticas
- Actualización de datos en tiempo real

### Análisis Competitivo
- Comparación entre múltiples perfiles
- Benchmarking de industria
- Análisis de tendencias

### Integración con Terceros
- Exportación a Google Sheets
- Integración con Slack/Teams
- Webhooks para notificaciones

---

**Desarrollado con ❤️ utilizando Apify y tecnologías modernas**

