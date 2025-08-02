"""
Configuración optimizada del sistema - SUPABASE-SPECIALIST
"""

import os
from datetime import timedelta

class BaseConfig:
    """Configuración base del sistema"""
    
    # Configuración de la aplicación
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Configuración de base de datos
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = True
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 3600,
        'connect_args': {
            'connect_timeout': 10
        }
    }
    
    # Configuración de Apify
    APIFY_API_TOKEN = os.environ.get('APIFY_API_TOKEN') or 'apify_api_aC7n0jeO2hDCGekELZyI4ywlt9ae9H33VRTw'
    APIFY_API_BASE_URL = 'https://api.apify.com/v2'
    APIFY_TIMEOUT = 300  # 5 minutos
    
    # Configuración de Redis (para caché y colas)
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'
    CACHE_TYPE = 'redis'
    CACHE_REDIS_URL = REDIS_URL
    CACHE_DEFAULT_TIMEOUT = 300
    
    # Configuración de Celery (para tareas asíncronas)
    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_RESULT_SERIALIZER = 'json'
    CELERY_ACCEPT_CONTENT = ['json']
    CELERY_TIMEZONE = 'UTC'
    CELERY_ENABLE_UTC = True
    
    # Configuración de archivos
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or 'uploads'
    REPORTS_FOLDER = os.environ.get('REPORTS_FOLDER') or 'reports'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    
    # Configuración de seguridad
    JWT_SECRET_KEY = SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    
    # Configuración de CORS
    CORS_ORIGINS = ['http://localhost:3000', 'http://localhost:5000']
    
    # Configuración de logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or 'INFO'
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Configuración de monitoreo
    ENABLE_METRICS = True
    METRICS_RETENTION_DAYS = 30
    
    # Configuración de rate limiting
    RATELIMIT_STORAGE_URL = REDIS_URL
    RATELIMIT_DEFAULT = "100 per hour"
    
    # Configuración de email (para notificaciones)
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')

class DevelopmentConfig(BaseConfig):
    """Configuración para desarrollo"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or 'sqlite:///social_media_reports_dev.db'
    SQLALCHEMY_ECHO = True
    
    # Configuración relajada para desarrollo
    CORS_ORIGINS = ['*']
    RATELIMIT_ENABLED = False
    
    # Configuración de Apify para desarrollo
    APIFY_TIMEOUT = 60  # 1 minuto para desarrollo

class ProductionConfig(BaseConfig):
    """Configuración para producción"""
    DEBUG = False
    
    # Base de datos PostgreSQL obligatoria en producción
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://user:password@localhost/social_media_reports'
    
    # Configuración de pool de conexiones optimizada para producción
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 20,
        'max_overflow': 30,
        'pool_pre_ping': True,
        'pool_recycle': 3600,
        'connect_args': {
            'connect_timeout': 10,
            'application_name': 'social_media_reports_prod'
        }
    }
    
    # Configuración de seguridad estricta
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Configuración de CORS específica
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '').split(',')
    
    # Configuración de logging para producción
    LOG_LEVEL = 'WARNING'
    
    # Configuración de monitoreo avanzado
    ENABLE_METRICS = True
    ENABLE_PROFILING = True

class TestingConfig(BaseConfig):
    """Configuración para testing"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
    # Desactivar funcionalidades externas en testing
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
    RATELIMIT_ENABLED = False
    ENABLE_METRICS = False
    
    # Configuración de Apify para testing (mock)
    APIFY_API_TOKEN = 'test_token'
    APIFY_TIMEOUT = 5

# Configuración de límites y cuotas por tier
SUBSCRIPTION_LIMITS = {
    'basic': {
        'max_campaigns': 5,
        'max_profiles_per_campaign': 10,
        'max_monthly_extractions': 500,
        'max_reports_per_month': 20,
        'max_storage_mb': 100
    },
    'pro': {
        'max_campaigns': 20,
        'max_profiles_per_campaign': 50,
        'max_monthly_extractions': 2000,
        'max_reports_per_month': 100,
        'max_storage_mb': 1000
    },
    'enterprise': {
        'max_campaigns': -1,  # Ilimitado
        'max_profiles_per_campaign': -1,
        'max_monthly_extractions': -1,
        'max_reports_per_month': -1,
        'max_storage_mb': -1
    }
}

# Configuración de plataformas soportadas
SUPPORTED_PLATFORMS = {
    'facebook': {
        'name': 'Facebook',
        'apify_actor': 'apify/facebook-posts-scraper',
        'rate_limit': 100,
        'supports_video': True,
        'supports_comments': True,
        'supports_sentiment': True
    },
    'instagram': {
        'name': 'Instagram',
        'apify_actor': 'apify/instagram-scraper',
        'rate_limit': 200,
        'supports_video': True,
        'supports_comments': True,
        'supports_sentiment': True
    },
    'twitter': {
        'name': 'Twitter/X',
        'apify_actor': 'apidojo/tweet-scraper-v2',
        'rate_limit': 300,
        'supports_video': True,
        'supports_comments': True,
        'supports_sentiment': True
    },
    'tiktok': {
        'name': 'TikTok',
        'apify_actor': 'clockworks/tiktok-scraper',
        'rate_limit': 150,
        'supports_video': True,
        'supports_comments': True,
        'supports_sentiment': True
    },
    'youtube': {
        'name': 'YouTube',
        'apify_actor': 'streamers/youtube-scraper',
        'rate_limit': 100,
        'supports_video': True,
        'supports_comments': True,
        'supports_sentiment': True
    },
    'linkedin': {
        'name': 'LinkedIn',
        'apify_actor': 'apify/linkedin-company-scraper',
        'rate_limit': 50,
        'supports_video': False,
        'supports_comments': True,
        'supports_sentiment': True
    }
}

# Configuración de tipos de reportes
REPORT_TYPES = {
    'standard': {
        'name': 'Reporte Estándar',
        'sections': ['summary', 'metrics', 'top_posts', 'growth'],
        'max_pages': 10
    },
    'detailed': {
        'name': 'Reporte Detallado',
        'sections': ['summary', 'metrics', 'top_posts', 'sentiment', 'comments', 'growth', 'recommendations'],
        'max_pages': 25
    },
    'executive': {
        'name': 'Reporte Ejecutivo',
        'sections': ['executive_summary', 'key_metrics', 'insights'],
        'max_pages': 5
    },
    'custom': {
        'name': 'Reporte Personalizado',
        'sections': [],  # Se define dinámicamente
        'max_pages': 50
    }
}

def get_config():
    """Obtener configuración basada en el entorno"""
    env = os.environ.get('FLASK_ENV', 'development')
    
    if env == 'production':
        return ProductionConfig
    elif env == 'testing':
        return TestingConfig
    else:
        return DevelopmentConfig

# Configuración de logging avanzado
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        },
        'detailed': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'default',
            'stream': 'ext://sys.stdout'
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'DEBUG',
            'formatter': 'detailed',
            'filename': 'logs/app.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5
        },
        'error_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'ERROR',
            'formatter': 'detailed',
            'filename': 'logs/errors.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5
        }
    },
    'loggers': {
        '': {  # root logger
            'level': 'INFO',
            'handlers': ['console', 'file']
        },
        'sqlalchemy.engine': {
            'level': 'WARNING',
            'handlers': ['file'],
            'propagate': False
        },
        'celery': {
            'level': 'INFO',
            'handlers': ['file'],
            'propagate': False
        },
        'apify': {
            'level': 'DEBUG',
            'handlers': ['file'],
            'propagate': False
        }
    }
}

