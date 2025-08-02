"""
Configuración optimizada de base de datos PostgreSQL - SUPABASE-SPECIALIST
"""

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool
import uuid
import logging

# Configurar logging para SQLAlchemy
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# Inicializar SQLAlchemy con configuración optimizada
db = SQLAlchemy()

class DatabaseConfig:
    """Configuración optimizada para PostgreSQL"""
    
    # Configuración de conexión
    SQLALCHEMY_DATABASE_URI = None  # Se configurará dinámicamente
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = True
    SQLALCHEMY_ECHO = False  # Cambiar a True para debug
    
    # Configuración del pool de conexiones
    SQLALCHEMY_ENGINE_OPTIONS = {
        'poolclass': QueuePool,
        'pool_size': 20,
        'max_overflow': 30,
        'pool_pre_ping': True,
        'pool_recycle': 3600,  # 1 hora
        'connect_args': {
            'connect_timeout': 10,
            'application_name': 'social_media_reports',
            'options': '-c timezone=UTC'
        }
    }

def configure_database(app, database_url=None):
    """
    Configurar la base de datos con optimizaciones
    """
    if database_url:
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    else:
        # Configuración por defecto (SQLite para desarrollo)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///social_media_reports.db'
    
    # Aplicar configuración optimizada
    for key, value in DatabaseConfig.__dict__.items():
        if key.startswith('SQLALCHEMY_'):
            app.config[key] = value
    
    # Inicializar SQLAlchemy
    db.init_app(app)
    
    # Configurar eventos de SQLAlchemy
    setup_database_events()
    
    return db

def setup_database_events():
    """Configurar eventos de base de datos para optimización"""
    
    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        """Optimizaciones para SQLite (desarrollo)"""
        if 'sqlite' in str(dbapi_connection):
            cursor = dbapi_connection.cursor()
            # Habilitar foreign keys
            cursor.execute("PRAGMA foreign_keys=ON")
            # Optimizaciones de rendimiento
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA cache_size=1000")
            cursor.execute("PRAGMA temp_store=MEMORY")
            cursor.close()
    
    @event.listens_for(Engine, "connect")
    def set_postgresql_settings(dbapi_connection, connection_record):
        """Optimizaciones para PostgreSQL (producción)"""
        if 'postgresql' in str(dbapi_connection):
            cursor = dbapi_connection.cursor()
            # Configurar timezone
            cursor.execute("SET timezone TO 'UTC'")
            # Optimizaciones de rendimiento
            cursor.execute("SET statement_timeout = '30s'")
            cursor.execute("SET lock_timeout = '10s'")
            cursor.close()

def generate_uuid():
    """Generar UUID para claves primarias"""
    return str(uuid.uuid4())

class TimestampMixin:
    """Mixin para campos de timestamp automáticos"""
    created_at = db.Column(
        db.DateTime(timezone=True), 
        server_default=db.func.now(),
        nullable=False
    )
    updated_at = db.Column(
        db.DateTime(timezone=True), 
        server_default=db.func.now(),
        onupdate=db.func.now(),
        nullable=False
    )

class UUIDMixin:
    """Mixin para claves primarias UUID"""
    id = db.Column(
        db.String(36), 
        primary_key=True, 
        default=generate_uuid,
        nullable=False
    )

def create_indexes(app):
    """Crear índices adicionales para optimización"""
    with app.app_context():
        # Índices para búsqueda de texto completo
        if 'postgresql' in app.config['SQLALCHEMY_DATABASE_URI']:
            db.engine.execute("""
                CREATE INDEX IF NOT EXISTS idx_posts_content_search 
                ON analytics.posts USING gin(to_tsvector('spanish', content))
            """)
            
            db.engine.execute("""
                CREATE INDEX IF NOT EXISTS idx_comments_content_search 
                ON analytics.comments USING gin(to_tsvector('spanish', content))
            """)

def optimize_database_settings(app):
    """Aplicar configuraciones de optimización específicas"""
    with app.app_context():
        if 'postgresql' in app.config['SQLALCHEMY_DATABASE_URI']:
            # Configuraciones de PostgreSQL para analytics
            optimizations = [
                "SET work_mem = '256MB'",
                "SET maintenance_work_mem = '512MB'",
                "SET effective_cache_size = '2GB'",
                "SET random_page_cost = 1.1",
                "SET seq_page_cost = 1.0"
            ]
            
            for optimization in optimizations:
                try:
                    db.engine.execute(optimization)
                except Exception as e:
                    app.logger.warning(f"No se pudo aplicar optimización: {optimization} - {e}")

class DatabaseManager:
    """Gestor de base de datos con utilidades"""
    
    @staticmethod
    def create_all_tables(app):
        """Crear todas las tablas"""
        with app.app_context():
            db.create_all()
            create_indexes(app)
            optimize_database_settings(app)
    
    @staticmethod
    def drop_all_tables(app):
        """Eliminar todas las tablas (¡CUIDADO!)"""
        with app.app_context():
            db.drop_all()
    
    @staticmethod
    def get_table_stats(app):
        """Obtener estadísticas de tablas"""
        with app.app_context():
            if 'postgresql' in app.config['SQLALCHEMY_DATABASE_URI']:
                result = db.engine.execute("""
                    SELECT 
                        schemaname,
                        tablename,
                        n_tup_ins as inserts,
                        n_tup_upd as updates,
                        n_tup_del as deletes,
                        n_live_tup as live_rows,
                        n_dead_tup as dead_rows
                    FROM pg_stat_user_tables
                    ORDER BY schemaname, tablename
                """)
                return [dict(row) for row in result]
            else:
                # Para SQLite, información básica
                tables = db.engine.table_names()
                stats = []
                for table in tables:
                    try:
                        count = db.engine.execute(f"SELECT COUNT(*) FROM {table}").scalar()
                        stats.append({
                            'tablename': table,
                            'live_rows': count
                        })
                    except:
                        pass
                return stats
    
    @staticmethod
    def vacuum_analyze(app):
        """Ejecutar VACUUM ANALYZE para optimización"""
        with app.app_context():
            if 'postgresql' in app.config['SQLALCHEMY_DATABASE_URI']:
                # No se puede ejecutar VACUUM en una transacción
                connection = db.engine.raw_connection()
                connection.set_isolation_level(0)  # AUTOCOMMIT
                cursor = connection.cursor()
                cursor.execute("VACUUM ANALYZE")
                cursor.close()
                connection.close()
    
    @staticmethod
    def get_slow_queries(app, limit=10):
        """Obtener consultas lentas (PostgreSQL)"""
        with app.app_context():
            if 'postgresql' in app.config['SQLALCHEMY_DATABASE_URI']:
                result = db.engine.execute(f"""
                    SELECT 
                        query,
                        calls,
                        total_time,
                        mean_time,
                        rows
                    FROM pg_stat_statements
                    ORDER BY total_time DESC
                    LIMIT {limit}
                """)
                return [dict(row) for row in result]
            return []

