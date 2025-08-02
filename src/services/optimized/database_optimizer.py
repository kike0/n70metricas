"""
Optimizador de Base de Datos para Máximo Rendimiento
Performance-Optimizer Implementation
"""

import asyncio
import asyncpg
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool
import sqlite3
from typing import Dict, List, Any, Optional, Union
import logging
import time
from contextlib import contextmanager
from functools import wraps
import threading
from datetime import datetime, timedelta
import json

from .cache_manager import cache_manager, cached
from .performance_monitor import performance_monitor

logger = logging.getLogger(__name__)

class DatabaseOptimizer:
    """
    Optimizador de base de datos con pool de conexiones y caché inteligente
    """
    
    def __init__(self, database_url: str, pool_size: int = 20, max_overflow: int = 30):
        """
        Inicializar optimizador de base de datos
        
        Args:
            database_url: URL de conexión a la base de datos
            pool_size: Tamaño del pool de conexiones
            max_overflow: Conexiones adicionales permitidas
        """
        self.database_url = database_url
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.connection_pool = None
        self.query_stats = {}
        self.slow_queries = []
        self.lock = threading.Lock()
        
        # Inicializar pool de conexiones
        self._initialize_connection_pool()
        
        # Configurar optimizaciones
        self._setup_database_optimizations()
    
    def _initialize_connection_pool(self):
        """
        Inicializar pool de conexiones optimizado
        """
        try:
            if 'postgresql' in self.database_url or 'postgres' in self.database_url:
                # Pool para PostgreSQL
                self.connection_pool = ThreadedConnectionPool(
                    minconn=self.pool_size // 2,
                    maxconn=self.pool_size + self.max_overflow,
                    dsn=self.database_url
                )
                self.db_type = 'postgresql'
                logger.info(f"PostgreSQL connection pool initialized: {self.pool_size} connections")
                
            else:
                # Fallback a SQLite
                self.db_type = 'sqlite'
                logger.info("Using SQLite database")
                
        except Exception as e:
            logger.error(f"Error initializing connection pool: {e}")
            self.db_type = 'sqlite'
    
    def _setup_database_optimizations(self):
        """
        Configurar optimizaciones específicas de la base de datos
        """
        if self.db_type == 'postgresql':
            self._setup_postgresql_optimizations()
        elif self.db_type == 'sqlite':
            self._setup_sqlite_optimizations()
    
    def _setup_postgresql_optimizations(self):
        """
        Configurar optimizaciones específicas de PostgreSQL
        """
        optimizations = [
            # Configuraciones de memoria
            "SET shared_buffers = '256MB'",
            "SET effective_cache_size = '1GB'",
            "SET work_mem = '16MB'",
            "SET maintenance_work_mem = '64MB'",
            
            # Configuraciones de checkpoint
            "SET checkpoint_completion_target = 0.9",
            "SET wal_buffers = '16MB'",
            
            # Configuraciones de consultas
            "SET random_page_cost = 1.1",
            "SET effective_io_concurrency = 200",
            
            # Configuraciones de logging
            "SET log_min_duration_statement = 1000",  # Log queries > 1s
            "SET log_statement = 'mod'",
            
            # Configuraciones de autovacuum
            "SET autovacuum = on",
            "SET autovacuum_vacuum_scale_factor = 0.1",
            "SET autovacuum_analyze_scale_factor = 0.05"
        ]
        
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    for optimization in optimizations:
                        try:
                            cursor.execute(optimization)
                            logger.debug(f"Applied optimization: {optimization}")
                        except Exception as e:
                            logger.warning(f"Could not apply optimization {optimization}: {e}")
                    conn.commit()
                    
        except Exception as e:
            logger.error(f"Error setting up PostgreSQL optimizations: {e}")
    
    def _setup_sqlite_optimizations(self):
        """
        Configurar optimizaciones específicas de SQLite
        """
        optimizations = [
            "PRAGMA journal_mode = WAL",
            "PRAGMA synchronous = NORMAL",
            "PRAGMA cache_size = 10000",
            "PRAGMA temp_store = MEMORY",
            "PRAGMA mmap_size = 268435456",  # 256MB
            "PRAGMA optimize"
        ]
        
        try:
            with sqlite3.connect(self.database_url.replace('sqlite:///', '')) as conn:
                for optimization in optimizations:
                    try:
                        conn.execute(optimization)
                        logger.debug(f"Applied SQLite optimization: {optimization}")
                    except Exception as e:
                        logger.warning(f"Could not apply optimization {optimization}: {e}")
                        
        except Exception as e:
            logger.error(f"Error setting up SQLite optimizations: {e}")
    
    @contextmanager
    def get_connection(self):
        """
        Obtener conexión del pool con manejo automático
        """
        conn = None
        try:
            if self.db_type == 'postgresql' and self.connection_pool:
                conn = self.connection_pool.getconn()
                yield conn
            else:
                # SQLite connection
                conn = sqlite3.connect(
                    self.database_url.replace('sqlite:///', ''),
                    timeout=30.0,
                    check_same_thread=False
                )
                conn.row_factory = sqlite3.Row
                yield conn
                
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                if self.db_type == 'postgresql' and self.connection_pool:
                    self.connection_pool.putconn(conn)
                else:
                    conn.close()
    
    def execute_query(self, query: str, params: tuple = None, 
                     fetch_one: bool = False, fetch_all: bool = True,
                     cache_ttl: int = 0, cache_key: str = None) -> Any:
        """
        Ejecutar consulta optimizada con caché opcional
        
        Args:
            query: Consulta SQL
            params: Parámetros de la consulta
            fetch_one: Si obtener solo un resultado
            fetch_all: Si obtener todos los resultados
            cache_ttl: Tiempo de vida del caché en segundos
            cache_key: Clave personalizada para caché
            
        Returns:
            Resultados de la consulta
        """
        start_time = time.time()
        query_hash = hash(query + str(params or ()))
        
        # Verificar caché si está habilitado
        if cache_ttl > 0:
            if not cache_key:
                cache_key = f"query_{query_hash}"
            
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                performance_monitor.record_database_query(
                    query_type=query.split()[0].upper(),
                    duration=time.time() - start_time,
                    cache_hit=True
                )
                return cached_result
        
        try:
            with self.get_connection() as conn:
                if self.db_type == 'postgresql':
                    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                        cursor.execute(query, params)
                        
                        if fetch_one:
                            result = dict(cursor.fetchone()) if cursor.rowcount > 0 else None
                        elif fetch_all:
                            result = [dict(row) for row in cursor.fetchall()]
                        else:
                            result = cursor.rowcount
                            
                        conn.commit()
                else:
                    # SQLite
                    cursor = conn.cursor()
                    cursor.execute(query, params or ())
                    
                    if fetch_one:
                        row = cursor.fetchone()
                        result = dict(row) if row else None
                    elif fetch_all:
                        result = [dict(row) for row in cursor.fetchall()]
                    else:
                        result = cursor.rowcount
                        
                    conn.commit()
            
            # Registrar estadísticas
            duration = time.time() - start_time
            self._record_query_stats(query, duration, len(result) if isinstance(result, list) else 1)
            
            # Cachear resultado si está habilitado
            if cache_ttl > 0 and cache_key:
                cache_manager.set(cache_key, result, cache_ttl)
            
            # Registrar métricas de rendimiento
            performance_monitor.record_database_query(
                query_type=query.split()[0].upper(),
                duration=duration,
                rows_affected=len(result) if isinstance(result, list) else 1,
                cache_hit=False
            )
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Database query error: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            
            # Registrar error en métricas
            performance_monitor.record_database_query(
                query_type="ERROR",
                duration=duration,
                cache_hit=False
            )
            
            raise e
    
    def _record_query_stats(self, query: str, duration: float, rows: int):
        """
        Registrar estadísticas de consultas
        
        Args:
            query: Consulta ejecutada
            duration: Duración en segundos
            rows: Número de filas afectadas
        """
        with self.lock:
            query_type = query.split()[0].upper()
            
            if query_type not in self.query_stats:
                self.query_stats[query_type] = {
                    'count': 0,
                    'total_duration': 0,
                    'avg_duration': 0,
                    'max_duration': 0,
                    'total_rows': 0
                }
            
            stats = self.query_stats[query_type]
            stats['count'] += 1
            stats['total_duration'] += duration
            stats['avg_duration'] = stats['total_duration'] / stats['count']
            stats['max_duration'] = max(stats['max_duration'], duration)
            stats['total_rows'] += rows
            
            # Registrar consultas lentas
            if duration > 1.0:  # Consultas > 1 segundo
                self.slow_queries.append({
                    'query': query[:200] + '...' if len(query) > 200 else query,
                    'duration': duration,
                    'rows': rows,
                    'timestamp': datetime.now().isoformat()
                })
                
                # Mantener solo las últimas 100 consultas lentas
                if len(self.slow_queries) > 100:
                    self.slow_queries = self.slow_queries[-100:]
    
    def get_query_stats(self) -> Dict[str, Any]:
        """
        Obtener estadísticas de consultas
        
        Returns:
            Estadísticas de rendimiento de consultas
        """
        with self.lock:
            return {
                'query_types': dict(self.query_stats),
                'slow_queries': list(self.slow_queries),
                'total_queries': sum(stats['count'] for stats in self.query_stats.values()),
                'avg_duration_all': sum(stats['total_duration'] for stats in self.query_stats.values()) / max(sum(stats['count'] for stats in self.query_stats.values()), 1)
            }
    
    def analyze_table_performance(self, table_name: str) -> Dict[str, Any]:
        """
        Analizar rendimiento de una tabla específica
        
        Args:
            table_name: Nombre de la tabla
            
        Returns:
            Análisis de rendimiento de la tabla
        """
        if self.db_type == 'postgresql':
            return self._analyze_postgresql_table(table_name)
        else:
            return self._analyze_sqlite_table(table_name)
    
    def _analyze_postgresql_table(self, table_name: str) -> Dict[str, Any]:
        """
        Analizar tabla PostgreSQL
        """
        queries = {
            'table_size': f"""
                SELECT 
                    pg_size_pretty(pg_total_relation_size('{table_name}')) as total_size,
                    pg_size_pretty(pg_relation_size('{table_name}')) as table_size,
                    pg_size_pretty(pg_total_relation_size('{table_name}') - pg_relation_size('{table_name}')) as index_size
            """,
            'row_count': f"SELECT COUNT(*) as row_count FROM {table_name}",
            'index_usage': f"""
                SELECT 
                    indexrelname as index_name,
                    idx_tup_read,
                    idx_tup_fetch,
                    idx_scan
                FROM pg_stat_user_indexes 
                WHERE relname = '{table_name}'
            """,
            'table_stats': f"""
                SELECT 
                    seq_scan,
                    seq_tup_read,
                    idx_scan,
                    idx_tup_fetch,
                    n_tup_ins,
                    n_tup_upd,
                    n_tup_del
                FROM pg_stat_user_tables 
                WHERE relname = '{table_name}'
            """
        }
        
        analysis = {}
        
        for stat_name, query in queries.items():
            try:
                result = self.execute_query(query, fetch_all=True)
                analysis[stat_name] = result
            except Exception as e:
                logger.error(f"Error analyzing {stat_name} for table {table_name}: {e}")
                analysis[stat_name] = None
        
        return analysis
    
    def _analyze_sqlite_table(self, table_name: str) -> Dict[str, Any]:
        """
        Analizar tabla SQLite
        """
        queries = {
            'table_info': f"PRAGMA table_info({table_name})",
            'index_list': f"PRAGMA index_list({table_name})",
            'row_count': f"SELECT COUNT(*) as row_count FROM {table_name}"
        }
        
        analysis = {}
        
        for stat_name, query in queries.items():
            try:
                result = self.execute_query(query, fetch_all=True)
                analysis[stat_name] = result
            except Exception as e:
                logger.error(f"Error analyzing {stat_name} for table {table_name}: {e}")
                analysis[stat_name] = None
        
        return analysis
    
    def suggest_optimizations(self, table_name: str = None) -> List[Dict[str, str]]:
        """
        Sugerir optimizaciones basadas en análisis
        
        Args:
            table_name: Tabla específica a analizar (opcional)
            
        Returns:
            Lista de sugerencias de optimización
        """
        suggestions = []
        
        # Analizar consultas lentas
        slow_queries = [q for q in self.slow_queries if q['duration'] > 2.0]
        if slow_queries:
            suggestions.append({
                'type': 'slow_queries',
                'priority': 'high',
                'description': f"Se detectaron {len(slow_queries)} consultas lentas (>2s)",
                'recommendation': "Revisar y optimizar consultas lentas, considerar índices adicionales"
            })
        
        # Analizar estadísticas de consultas
        stats = self.get_query_stats()
        if stats['avg_duration_all'] > 0.5:
            suggestions.append({
                'type': 'avg_duration',
                'priority': 'medium',
                'description': f"Duración promedio de consultas: {stats['avg_duration_all']:.3f}s",
                'recommendation': "Optimizar consultas frecuentes y considerar caché adicional"
            })
        
        # Analizar tabla específica si se proporciona
        if table_name:
            table_analysis = self.analyze_table_performance(table_name)
            
            if self.db_type == 'postgresql':
                # Sugerencias específicas de PostgreSQL
                table_stats = table_analysis.get('table_stats', [])
                if table_stats and len(table_stats) > 0:
                    stats = table_stats[0]
                    
                    # Verificar uso de índices vs scans secuenciales
                    seq_scan = stats.get('seq_scan', 0)
                    idx_scan = stats.get('idx_scan', 0)
                    
                    if seq_scan > idx_scan * 2:
                        suggestions.append({
                            'type': 'index_usage',
                            'priority': 'high',
                            'description': f"Tabla {table_name}: {seq_scan} scans secuenciales vs {idx_scan} scans de índice",
                            'recommendation': "Considerar agregar índices en columnas frecuentemente consultadas"
                        })
        
        # Sugerencias generales de caché
        cache_stats = cache_manager.get_stats()
        if cache_stats.get('type') == 'memory' and cache_stats.get('total_keys', 0) > 1000:
            suggestions.append({
                'type': 'cache',
                'priority': 'medium',
                'description': "Usando caché en memoria con muchas claves",
                'recommendation': "Considerar migrar a Redis para mejor rendimiento de caché"
            })
        
        return suggestions
    
    def create_optimized_indexes(self, table_name: str, columns: List[str]) -> bool:
        """
        Crear índices optimizados para una tabla
        
        Args:
            table_name: Nombre de la tabla
            columns: Lista de columnas para indexar
            
        Returns:
            True si se crearon exitosamente
        """
        try:
            for column in columns:
                index_name = f"idx_{table_name}_{column}"
                
                if self.db_type == 'postgresql':
                    # Crear índice con configuraciones optimizadas
                    query = f"""
                        CREATE INDEX CONCURRENTLY IF NOT EXISTS {index_name} 
                        ON {table_name} ({column})
                    """
                else:
                    # SQLite
                    query = f"""
                        CREATE INDEX IF NOT EXISTS {index_name} 
                        ON {table_name} ({column})
                    """
                
                self.execute_query(query, fetch_all=False)
                logger.info(f"Created index {index_name} on {table_name}.{column}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")
            return False
    
    def vacuum_analyze(self, table_name: str = None) -> bool:
        """
        Ejecutar VACUUM y ANALYZE para optimizar la base de datos
        
        Args:
            table_name: Tabla específica (opcional)
            
        Returns:
            True si se ejecutó exitosamente
        """
        try:
            if self.db_type == 'postgresql':
                if table_name:
                    queries = [
                        f"VACUUM ANALYZE {table_name}",
                        f"REINDEX TABLE {table_name}"
                    ]
                else:
                    queries = [
                        "VACUUM ANALYZE",
                        "REINDEX DATABASE"
                    ]
            else:
                # SQLite
                queries = [
                    "VACUUM",
                    "ANALYZE",
                    "PRAGMA optimize"
                ]
            
            for query in queries:
                try:
                    self.execute_query(query, fetch_all=False)
                    logger.info(f"Executed maintenance query: {query}")
                except Exception as e:
                    logger.warning(f"Could not execute {query}: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error during vacuum/analyze: {e}")
            return False
    
    def close_connections(self):
        """
        Cerrar todas las conexiones del pool
        """
        try:
            if self.connection_pool:
                self.connection_pool.closeall()
                logger.info("Database connection pool closed")
        except Exception as e:
            logger.error(f"Error closing connection pool: {e}")

# Instancia global del optimizador
db_optimizer = None

def initialize_database_optimizer(database_url: str, pool_size: int = 20):
    """
    Inicializar optimizador de base de datos global
    
    Args:
        database_url: URL de la base de datos
        pool_size: Tamaño del pool de conexiones
    """
    global db_optimizer
    db_optimizer = DatabaseOptimizer(database_url, pool_size)
    logger.info("Database optimizer initialized")

def optimized_query(cache_ttl: int = 0, cache_key: str = None):
    """
    Decorador para consultas optimizadas con caché
    
    Args:
        cache_ttl: Tiempo de vida del caché
        cache_key: Clave personalizada de caché
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not db_optimizer:
                raise RuntimeError("Database optimizer not initialized")
            
            # Extraer query y params de la función
            query = kwargs.get('query') or (args[0] if args else None)
            params = kwargs.get('params') or (args[1] if len(args) > 1 else None)
            
            if not query:
                return func(*args, **kwargs)
            
            return db_optimizer.execute_query(
                query=query,
                params=params,
                cache_ttl=cache_ttl,
                cache_key=cache_key,
                **{k: v for k, v in kwargs.items() if k not in ['query', 'params']}
            )
        
        return wrapper
    return decorator

# Consultas optimizadas específicas del dominio
class OptimizedQueries:
    """
    Consultas optimizadas para el sistema de reportes
    """
    
    @staticmethod
    @optimized_query(cache_ttl=1800, cache_key="campaign_metrics")
    def get_campaign_metrics(campaign_id: int, start_date: str, end_date: str):
        """
        Obtener métricas de campaña optimizadas
        """
        query = """
            SELECT 
                c.id,
                c.name,
                c.description,
                COUNT(DISTINCT p.id) as profile_count,
                COUNT(DISTINCT r.id) as report_count,
                AVG(dm.engagement_rate) as avg_engagement,
                SUM(dm.followers_count) as total_followers,
                SUM(dm.interactions_count) as total_interactions
            FROM analytics.campaigns c
            LEFT JOIN analytics.profiles p ON c.id = p.campaign_id
            LEFT JOIN analytics.reports r ON c.id = r.campaign_id
            LEFT JOIN analytics.daily_metrics dm ON p.id = dm.profile_id
                AND dm.metric_date BETWEEN %s AND %s
            WHERE c.id = %s
            GROUP BY c.id, c.name, c.description
        """
        
        return db_optimizer.execute_query(
            query=query,
            params=(start_date, end_date, campaign_id),
            fetch_one=True
        )
    
    @staticmethod
    @optimized_query(cache_ttl=3600, cache_key="top_posts")
    def get_top_posts(profile_id: int, days: int = 7, limit: int = 10):
        """
        Obtener top posts optimizado
        """
        query = """
            SELECT 
                p.id,
                p.content,
                p.platform,
                p.post_date,
                p.likes_count,
                p.comments_count,
                p.shares_count,
                p.engagement_rate,
                p.reach_count
            FROM analytics.posts p
            WHERE p.profile_id = %s
                AND p.post_date >= CURRENT_DATE - INTERVAL '%s days'
            ORDER BY p.engagement_rate DESC, p.likes_count DESC
            LIMIT %s
        """
        
        return db_optimizer.execute_query(
            query=query,
            params=(profile_id, days, limit),
            fetch_all=True
        )
    
    @staticmethod
    @optimized_query(cache_ttl=7200, cache_key="platform_summary")
    def get_platform_summary(campaign_id: int, days: int = 30):
        """
        Obtener resumen por plataforma optimizado
        """
        query = """
            SELECT 
                p.platform,
                COUNT(DISTINCT p.id) as profile_count,
                AVG(dm.followers_count) as avg_followers,
                AVG(dm.engagement_rate) as avg_engagement,
                SUM(dm.interactions_count) as total_interactions,
                COUNT(DISTINCT posts.id) as post_count
            FROM analytics.profiles p
            LEFT JOIN analytics.daily_metrics dm ON p.id = dm.profile_id
                AND dm.metric_date >= CURRENT_DATE - INTERVAL '%s days'
            LEFT JOIN analytics.posts posts ON p.id = posts.profile_id
                AND posts.post_date >= CURRENT_DATE - INTERVAL '%s days'
            WHERE p.campaign_id = %s
            GROUP BY p.platform
            ORDER BY total_interactions DESC
        """
        
        return db_optimizer.execute_query(
            query=query,
            params=(days, days, campaign_id),
            fetch_all=True
        )

