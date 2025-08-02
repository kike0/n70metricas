"""
Sistema de Caché Avanzado para Optimización de Rendimiento
Performance-Optimizer Implementation
"""

import redis
import json
import hashlib
import time
from typing import Any, Optional, Dict, List
from functools import wraps
from datetime import datetime, timedelta
import pickle
import logging

logger = logging.getLogger(__name__)

class CacheManager:
    """
    Gestor de caché avanzado con múltiples estrategias de almacenamiento
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        """
        Inicializar el gestor de caché
        
        Args:
            redis_url: URL de conexión a Redis
        """
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            self.redis_client.ping()
            self.redis_available = True
            logger.info("Redis cache initialized successfully")
        except Exception as e:
            logger.warning(f"Redis not available, using memory cache: {e}")
            self.redis_available = False
            self.memory_cache = {}
            self.cache_timestamps = {}
    
    def _generate_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """
        Generar clave de caché única basada en parámetros
        
        Args:
            prefix: Prefijo para la clave
            *args: Argumentos posicionales
            **kwargs: Argumentos con nombre
            
        Returns:
            Clave de caché única
        """
        # Crear string único basado en argumentos
        key_data = f"{prefix}:{str(args)}:{str(sorted(kwargs.items()))}"
        
        # Generar hash MD5 para claves largas
        if len(key_data) > 100:
            key_hash = hashlib.md5(key_data.encode()).hexdigest()
            return f"{prefix}:{key_hash}"
        
        return key_data.replace(" ", "_").replace(":", "_")
    
    def get(self, key: str) -> Optional[Any]:
        """
        Obtener valor del caché
        
        Args:
            key: Clave del caché
            
        Returns:
            Valor almacenado o None si no existe
        """
        try:
            if self.redis_available:
                value = self.redis_client.get(key)
                if value:
                    return json.loads(value)
            else:
                # Memory cache con expiración
                if key in self.memory_cache:
                    timestamp = self.cache_timestamps.get(key, 0)
                    if time.time() - timestamp < 3600:  # 1 hora de expiración
                        return self.memory_cache[key]
                    else:
                        # Limpiar caché expirado
                        del self.memory_cache[key]
                        del self.cache_timestamps[key]
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting cache key {key}: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """
        Almacenar valor en caché
        
        Args:
            key: Clave del caché
            value: Valor a almacenar
            ttl: Tiempo de vida en segundos (default: 1 hora)
            
        Returns:
            True si se almacenó correctamente
        """
        try:
            if self.redis_available:
                serialized_value = json.dumps(value, default=str)
                return self.redis_client.setex(key, ttl, serialized_value)
            else:
                # Memory cache
                self.memory_cache[key] = value
                self.cache_timestamps[key] = time.time()
                return True
                
        except Exception as e:
            logger.error(f"Error setting cache key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        Eliminar clave del caché
        
        Args:
            key: Clave a eliminar
            
        Returns:
            True si se eliminó correctamente
        """
        try:
            if self.redis_available:
                return bool(self.redis_client.delete(key))
            else:
                if key in self.memory_cache:
                    del self.memory_cache[key]
                    del self.cache_timestamps[key]
                    return True
                return False
                
        except Exception as e:
            logger.error(f"Error deleting cache key {key}: {e}")
            return False
    
    def clear_pattern(self, pattern: str) -> int:
        """
        Limpiar claves que coincidan con un patrón
        
        Args:
            pattern: Patrón de búsqueda (ej: "campaign:*")
            
        Returns:
            Número de claves eliminadas
        """
        try:
            if self.redis_available:
                keys = self.redis_client.keys(pattern)
                if keys:
                    return self.redis_client.delete(*keys)
                return 0
            else:
                # Memory cache pattern matching
                keys_to_delete = [k for k in self.memory_cache.keys() if pattern.replace("*", "") in k]
                for key in keys_to_delete:
                    del self.memory_cache[key]
                    del self.cache_timestamps[key]
                return len(keys_to_delete)
                
        except Exception as e:
            logger.error(f"Error clearing cache pattern {pattern}: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Obtener estadísticas del caché
        
        Returns:
            Diccionario con estadísticas
        """
        try:
            if self.redis_available:
                info = self.redis_client.info()
                return {
                    "type": "redis",
                    "connected_clients": info.get("connected_clients", 0),
                    "used_memory": info.get("used_memory_human", "0B"),
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0),
                    "total_keys": len(self.redis_client.keys("*"))
                }
            else:
                return {
                    "type": "memory",
                    "total_keys": len(self.memory_cache),
                    "memory_usage": f"{len(str(self.memory_cache))} bytes"
                }
                
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"type": "error", "message": str(e)}

# Instancia global del gestor de caché
cache_manager = CacheManager()

def cached(ttl: int = 3600, key_prefix: str = "default"):
    """
    Decorador para cachear resultados de funciones
    
    Args:
        ttl: Tiempo de vida del caché en segundos
        key_prefix: Prefijo para la clave de caché
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generar clave de caché
            cache_key = cache_manager._generate_cache_key(
                f"{key_prefix}:{func.__name__}", *args, **kwargs
            )
            
            # Intentar obtener del caché
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_result
            
            # Ejecutar función y cachear resultado
            logger.debug(f"Cache miss for {cache_key}, executing function")
            result = func(*args, **kwargs)
            
            # Almacenar en caché
            cache_manager.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator

class QueryCache:
    """
    Caché específico para consultas de base de datos
    """
    
    @staticmethod
    @cached(ttl=1800, key_prefix="query")
    def get_campaign_metrics(campaign_id: int, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Obtener métricas de campaña con caché
        
        Args:
            campaign_id: ID de la campaña
            start_date: Fecha de inicio
            end_date: Fecha de fin
            
        Returns:
            Métricas de la campaña
        """
        # Esta función será implementada por el backend
        pass
    
    @staticmethod
    @cached(ttl=3600, key_prefix="profile")
    def get_profile_data(profile_url: str, days: int = 7) -> Dict[str, Any]:
        """
        Obtener datos de perfil con caché
        
        Args:
            profile_url: URL del perfil
            days: Número de días de datos
            
        Returns:
            Datos del perfil
        """
        # Esta función será implementada por el backend
        pass
    
    @staticmethod
    @cached(ttl=7200, key_prefix="report")
    def get_report_data(campaign_id: int, report_type: str) -> Dict[str, Any]:
        """
        Obtener datos de reporte con caché
        
        Args:
            campaign_id: ID de la campaña
            report_type: Tipo de reporte
            
        Returns:
            Datos del reporte
        """
        # Esta función será implementada por el backend
        pass

class ApifyCache:
    """
    Caché específico para datos de Apify
    """
    
    @staticmethod
    @cached(ttl=1800, key_prefix="apify")
    def get_facebook_data(profile_url: str, days: int = 7) -> Dict[str, Any]:
        """
        Obtener datos de Facebook con caché
        
        Args:
            profile_url: URL del perfil de Facebook
            days: Número de días de datos
            
        Returns:
            Datos de Facebook
        """
        # Esta función será implementada por el servicio Apify
        pass
    
    @staticmethod
    @cached(ttl=1800, key_prefix="apify")
    def get_instagram_data(profile_url: str, days: int = 7) -> Dict[str, Any]:
        """
        Obtener datos de Instagram con caché
        
        Args:
            profile_url: URL del perfil de Instagram
            days: Número de días de datos
            
        Returns:
            Datos de Instagram
        """
        # Esta función será implementada por el servicio Apify
        pass
    
    @staticmethod
    def invalidate_profile_cache(profile_url: str):
        """
        Invalidar caché de un perfil específico
        
        Args:
            profile_url: URL del perfil
        """
        pattern = f"apify:*{profile_url}*"
        cache_manager.clear_pattern(pattern)
        logger.info(f"Invalidated cache for profile: {profile_url}")

class ReportCache:
    """
    Caché específico para reportes PDF
    """
    
    @staticmethod
    def cache_report(report_id: str, pdf_data: bytes, metadata: Dict[str, Any]) -> bool:
        """
        Cachear reporte PDF
        
        Args:
            report_id: ID único del reporte
            pdf_data: Datos binarios del PDF
            metadata: Metadatos del reporte
            
        Returns:
            True si se cacheó correctamente
        """
        try:
            # Cachear metadatos
            cache_manager.set(f"report_meta:{report_id}", metadata, ttl=86400)  # 24 horas
            
            # Para PDFs, usar almacenamiento en disco si Redis no está disponible
            if cache_manager.redis_available:
                # Usar pickle para datos binarios
                cache_manager.redis_client.setex(
                    f"report_pdf:{report_id}", 
                    86400, 
                    pickle.dumps(pdf_data)
                )
            else:
                # Almacenar en disco como fallback
                import os
                os.makedirs("/tmp/report_cache", exist_ok=True)
                with open(f"/tmp/report_cache/{report_id}.pdf", "wb") as f:
                    f.write(pdf_data)
            
            return True
            
        except Exception as e:
            logger.error(f"Error caching report {report_id}: {e}")
            return False
    
    @staticmethod
    def get_cached_report(report_id: str) -> Optional[tuple]:
        """
        Obtener reporte cacheado
        
        Args:
            report_id: ID del reporte
            
        Returns:
            Tupla (pdf_data, metadata) o None si no existe
        """
        try:
            # Obtener metadatos
            metadata = cache_manager.get(f"report_meta:{report_id}")
            if not metadata:
                return None
            
            # Obtener PDF
            if cache_manager.redis_available:
                pdf_data = cache_manager.redis_client.get(f"report_pdf:{report_id}")
                if pdf_data:
                    pdf_data = pickle.loads(pdf_data)
                else:
                    return None
            else:
                # Leer desde disco
                try:
                    with open(f"/tmp/report_cache/{report_id}.pdf", "rb") as f:
                        pdf_data = f.read()
                except FileNotFoundError:
                    return None
            
            return pdf_data, metadata
            
        except Exception as e:
            logger.error(f"Error getting cached report {report_id}: {e}")
            return None

# Funciones de utilidad para limpieza de caché
def cleanup_expired_cache():
    """
    Limpiar caché expirado (para memory cache)
    """
    if not cache_manager.redis_available:
        current_time = time.time()
        expired_keys = [
            key for key, timestamp in cache_manager.cache_timestamps.items()
            if current_time - timestamp > 3600
        ]
        
        for key in expired_keys:
            cache_manager.delete(key)
        
        logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")

def warm_up_cache():
    """
    Precalentar caché con datos frecuentemente accedidos
    """
    logger.info("Starting cache warm-up process")
    
    # Aquí se pueden precargar datos comunes
    # Por ejemplo, métricas de campañas activas
    
    logger.info("Cache warm-up completed")

# Middleware para Flask
class CacheMiddleware:
    """
    Middleware para cachear respuestas HTTP
    """
    
    def __init__(self, app, default_ttl: int = 300):
        self.app = app
        self.default_ttl = default_ttl
    
    def __call__(self, environ, start_response):
        # Implementar lógica de caché HTTP aquí
        return self.app(environ, start_response)

