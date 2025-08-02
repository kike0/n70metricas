"""
Optimizador de APIs con Caché Inteligente y Rate Limiting
Performance-Optimizer Implementation
"""

import asyncio
import aiohttp
import requests
from typing import Dict, List, Any, Optional, Callable
import time
import json
import hashlib
from datetime import datetime, timedelta
from functools import wraps
import threading
from collections import defaultdict, deque
import logging
from dataclasses import dataclass
from enum import Enum

from .cache_manager import cache_manager, cached
from .performance_monitor import performance_monitor

logger = logging.getLogger(__name__)

class RateLimitStrategy(Enum):
    """Estrategias de rate limiting"""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    EXPONENTIAL_BACKOFF = "exponential_backoff"

@dataclass
class RateLimitConfig:
    """Configuración de rate limiting"""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW
    backoff_factor: float = 2.0
    max_retries: int = 3

@dataclass
class APIEndpoint:
    """Configuración de endpoint de API"""
    name: str
    base_url: str
    rate_limit: RateLimitConfig
    cache_ttl: int = 3600
    timeout: int = 30
    headers: Dict[str, str] = None
    auth_required: bool = False

class RateLimiter:
    """
    Rate limiter avanzado con múltiples estrategias
    """
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.requests = defaultdict(lambda: deque())
        self.tokens = defaultdict(lambda: config.requests_per_minute)
        self.last_refill = defaultdict(lambda: time.time())
        self.lock = threading.Lock()
    
    def is_allowed(self, key: str) -> bool:
        """
        Verificar si una request está permitida
        
        Args:
            key: Identificador único (ej: API key, IP, user_id)
            
        Returns:
            True si la request está permitida
        """
        with self.lock:
            current_time = time.time()
            
            if self.config.strategy == RateLimitStrategy.SLIDING_WINDOW:
                return self._sliding_window_check(key, current_time)
            elif self.config.strategy == RateLimitStrategy.TOKEN_BUCKET:
                return self._token_bucket_check(key, current_time)
            elif self.config.strategy == RateLimitStrategy.FIXED_WINDOW:
                return self._fixed_window_check(key, current_time)
            else:
                return True
    
    def _sliding_window_check(self, key: str, current_time: float) -> bool:
        """Implementar sliding window rate limiting"""
        requests = self.requests[key]
        
        # Limpiar requests antiguas (más de 1 minuto)
        while requests and current_time - requests[0] > 60:
            requests.popleft()
        
        # Verificar límite por minuto
        if len(requests) >= self.config.requests_per_minute:
            return False
        
        # Verificar límite por hora
        hour_requests = [r for r in requests if current_time - r < 3600]
        if len(hour_requests) >= self.config.requests_per_hour:
            return False
        
        # Agregar request actual
        requests.append(current_time)
        return True
    
    def _token_bucket_check(self, key: str, current_time: float) -> bool:
        """Implementar token bucket rate limiting"""
        last_refill = self.last_refill[key]
        tokens = self.tokens[key]
        
        # Calcular tokens a agregar
        time_passed = current_time - last_refill
        tokens_to_add = time_passed * (self.config.requests_per_minute / 60.0)
        
        # Actualizar tokens (máximo = requests_per_minute)
        self.tokens[key] = min(
            self.config.requests_per_minute,
            tokens + tokens_to_add
        )
        self.last_refill[key] = current_time
        
        # Verificar si hay tokens disponibles
        if self.tokens[key] >= 1:
            self.tokens[key] -= 1
            return True
        
        return False
    
    def _fixed_window_check(self, key: str, current_time: float) -> bool:
        """Implementar fixed window rate limiting"""
        window_start = int(current_time // 60) * 60  # Ventana de 1 minuto
        requests = self.requests[key]
        
        # Limpiar requests de ventanas anteriores
        requests = deque([r for r in requests if r >= window_start])
        self.requests[key] = requests
        
        if len(requests) >= self.config.requests_per_minute:
            return False
        
        requests.append(current_time)
        return True
    
    def get_wait_time(self, key: str) -> float:
        """
        Obtener tiempo de espera hasta la próxima request permitida
        
        Args:
            key: Identificador único
            
        Returns:
            Tiempo de espera en segundos
        """
        with self.lock:
            if self.config.strategy == RateLimitStrategy.SLIDING_WINDOW:
                requests = self.requests[key]
                if len(requests) >= self.config.requests_per_minute:
                    oldest_request = requests[0]
                    return max(0, 60 - (time.time() - oldest_request))
            
            elif self.config.strategy == RateLimitStrategy.TOKEN_BUCKET:
                tokens = self.tokens[key]
                if tokens < 1:
                    return (1 - tokens) * (60.0 / self.config.requests_per_minute)
        
        return 0

class APIOptimizer:
    """
    Optimizador de APIs con caché inteligente y rate limiting
    """
    
    def __init__(self):
        self.endpoints: Dict[str, APIEndpoint] = {}
        self.rate_limiters: Dict[str, RateLimiter] = {}
        self.session = requests.Session()
        self.async_session = None
        self.request_stats = defaultdict(lambda: {
            'total_requests': 0,
            'cache_hits': 0,
            'rate_limited': 0,
            'errors': 0,
            'avg_response_time': 0,
            'total_response_time': 0
        })
        
        # Configurar session con optimizaciones
        self.session.headers.update({
            'User-Agent': 'SocialMediaAnalytics/1.0',
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        })
        
        # Pool de conexiones optimizado
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=20,
            pool_maxsize=20,
            max_retries=3,
            pool_block=False
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
    
    def register_endpoint(self, endpoint: APIEndpoint):
        """
        Registrar un endpoint de API
        
        Args:
            endpoint: Configuración del endpoint
        """
        self.endpoints[endpoint.name] = endpoint
        self.rate_limiters[endpoint.name] = RateLimiter(endpoint.rate_limit)
        logger.info(f"Registered API endpoint: {endpoint.name}")
    
    def _generate_cache_key(self, endpoint_name: str, url: str, 
                          params: Dict = None, data: Dict = None) -> str:
        """
        Generar clave de caché para request
        
        Args:
            endpoint_name: Nombre del endpoint
            url: URL de la request
            params: Parámetros de query
            data: Datos del body
            
        Returns:
            Clave de caché única
        """
        key_data = f"{endpoint_name}:{url}:{str(params or {})}:{str(data or {})}"
        return f"api_cache:{hashlib.md5(key_data.encode()).hexdigest()}"
    
    def _check_rate_limit(self, endpoint_name: str, api_key: str = None) -> bool:
        """
        Verificar rate limit para un endpoint
        
        Args:
            endpoint_name: Nombre del endpoint
            api_key: Clave de API (opcional)
            
        Returns:
            True si la request está permitida
        """
        if endpoint_name not in self.rate_limiters:
            return True
        
        rate_limiter = self.rate_limiters[endpoint_name]
        key = api_key or endpoint_name
        
        return rate_limiter.is_allowed(key)
    
    def _wait_for_rate_limit(self, endpoint_name: str, api_key: str = None):
        """
        Esperar hasta que el rate limit permita la request
        
        Args:
            endpoint_name: Nombre del endpoint
            api_key: Clave de API (opcional)
        """
        if endpoint_name not in self.rate_limiters:
            return
        
        rate_limiter = self.rate_limiters[endpoint_name]
        key = api_key or endpoint_name
        
        wait_time = rate_limiter.get_wait_time(key)
        if wait_time > 0:
            logger.info(f"Rate limited for {endpoint_name}, waiting {wait_time:.2f}s")
            time.sleep(wait_time)
    
    def make_request(self, endpoint_name: str, url: str, method: str = 'GET',
                    params: Dict = None, data: Dict = None, headers: Dict = None,
                    use_cache: bool = True, api_key: str = None) -> Dict[str, Any]:
        """
        Realizar request optimizada con caché y rate limiting
        
        Args:
            endpoint_name: Nombre del endpoint registrado
            url: URL completa o relativa
            method: Método HTTP
            params: Parámetros de query
            data: Datos del body
            headers: Headers adicionales
            use_cache: Si usar caché
            api_key: Clave de API
            
        Returns:
            Respuesta de la API
        """
        start_time = time.time()
        
        # Obtener configuración del endpoint
        if endpoint_name not in self.endpoints:
            raise ValueError(f"Endpoint {endpoint_name} not registered")
        
        endpoint = self.endpoints[endpoint_name]
        
        # Construir URL completa
        if not url.startswith('http'):
            url = f"{endpoint.base_url.rstrip('/')}/{url.lstrip('/')}"
        
        # Generar clave de caché
        cache_key = self._generate_cache_key(endpoint_name, url, params, data)
        
        # Verificar caché para requests GET
        if use_cache and method.upper() == 'GET' and endpoint.cache_ttl > 0:
            cached_response = cache_manager.get(cache_key)
            if cached_response is not None:
                self.request_stats[endpoint_name]['cache_hits'] += 1
                performance_monitor.record_cache_operation('get', cache_key, True)
                logger.debug(f"Cache hit for {endpoint_name}: {url}")
                return cached_response
        
        # Verificar rate limit
        if not self._check_rate_limit(endpoint_name, api_key):
            self.request_stats[endpoint_name]['rate_limited'] += 1
            self._wait_for_rate_limit(endpoint_name, api_key)
        
        # Preparar headers
        request_headers = {}
        if endpoint.headers:
            request_headers.update(endpoint.headers)
        if headers:
            request_headers.update(headers)
        if api_key and endpoint.auth_required:
            request_headers['Authorization'] = f"Bearer {api_key}"
        
        try:
            # Realizar request
            response = self.session.request(
                method=method.upper(),
                url=url,
                params=params,
                json=data if data else None,
                headers=request_headers,
                timeout=endpoint.timeout
            )
            
            response.raise_for_status()
            
            # Procesar respuesta
            try:
                response_data = response.json()
            except ValueError:
                response_data = {'text': response.text, 'status_code': response.status_code}
            
            # Cachear respuesta para requests GET exitosas
            if (use_cache and method.upper() == 'GET' and 
                endpoint.cache_ttl > 0 and response.status_code == 200):
                cache_manager.set(cache_key, response_data, endpoint.cache_ttl)
                performance_monitor.record_cache_operation('set', cache_key, False)
            
            # Registrar estadísticas
            duration = time.time() - start_time
            self._update_stats(endpoint_name, duration, success=True)
            
            # Registrar métricas de rendimiento
            performance_monitor.record_apify_request(
                actor_name=endpoint_name,
                duration=duration,
                success=True,
                data_size=len(str(response_data))
            )
            
            return response_data
            
        except requests.exceptions.RequestException as e:
            duration = time.time() - start_time
            self._update_stats(endpoint_name, duration, success=False)
            
            # Registrar error en métricas
            performance_monitor.record_apify_request(
                actor_name=endpoint_name,
                duration=duration,
                success=False
            )
            
            logger.error(f"API request failed for {endpoint_name}: {e}")
            raise e
    
    def _update_stats(self, endpoint_name: str, duration: float, success: bool):
        """
        Actualizar estadísticas de requests
        
        Args:
            endpoint_name: Nombre del endpoint
            duration: Duración de la request
            success: Si la request fue exitosa
        """
        stats = self.request_stats[endpoint_name]
        stats['total_requests'] += 1
        stats['total_response_time'] += duration
        stats['avg_response_time'] = stats['total_response_time'] / stats['total_requests']
        
        if not success:
            stats['errors'] += 1
    
    async def make_async_request(self, endpoint_name: str, url: str, 
                                method: str = 'GET', **kwargs) -> Dict[str, Any]:
        """
        Realizar request asíncrona optimizada
        
        Args:
            endpoint_name: Nombre del endpoint
            url: URL de la request
            method: Método HTTP
            **kwargs: Argumentos adicionales
            
        Returns:
            Respuesta de la API
        """
        if not self.async_session:
            self.async_session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                connector=aiohttp.TCPConnector(limit=20, limit_per_host=10)
            )
        
        endpoint = self.endpoints[endpoint_name]
        
        if not url.startswith('http'):
            url = f"{endpoint.base_url.rstrip('/')}/{url.lstrip('/')}"
        
        start_time = time.time()
        
        try:
            async with self.async_session.request(
                method=method.upper(),
                url=url,
                **kwargs
            ) as response:
                response.raise_for_status()
                response_data = await response.json()
                
                duration = time.time() - start_time
                self._update_stats(endpoint_name, duration, success=True)
                
                return response_data
                
        except Exception as e:
            duration = time.time() - start_time
            self._update_stats(endpoint_name, duration, success=False)
            raise e
    
    def batch_requests(self, requests: List[Dict[str, Any]], 
                      max_concurrent: int = 5) -> List[Dict[str, Any]]:
        """
        Realizar múltiples requests en lotes
        
        Args:
            requests: Lista de configuraciones de request
            max_concurrent: Máximo de requests concurrentes
            
        Returns:
            Lista de respuestas
        """
        async def process_batch():
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def make_single_request(request_config):
                async with semaphore:
                    return await self.make_async_request(**request_config)
            
            tasks = [make_single_request(req) for req in requests]
            return await asyncio.gather(*tasks, return_exceptions=True)
        
        # Ejecutar batch asíncrono
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            results = loop.run_until_complete(process_batch())
            return results
        finally:
            loop.close()
    
    def get_endpoint_stats(self, endpoint_name: str = None) -> Dict[str, Any]:
        """
        Obtener estadísticas de endpoints
        
        Args:
            endpoint_name: Endpoint específico (opcional)
            
        Returns:
            Estadísticas de rendimiento
        """
        if endpoint_name:
            if endpoint_name in self.request_stats:
                stats = dict(self.request_stats[endpoint_name])
                stats['cache_hit_rate'] = (
                    stats['cache_hits'] / max(stats['total_requests'], 1) * 100
                )
                stats['error_rate'] = (
                    stats['errors'] / max(stats['total_requests'], 1) * 100
                )
                stats['rate_limited_rate'] = (
                    stats['rate_limited'] / max(stats['total_requests'], 1) * 100
                )
                return stats
            return {}
        
        # Estadísticas de todos los endpoints
        all_stats = {}
        for name, stats in self.request_stats.items():
            endpoint_stats = dict(stats)
            endpoint_stats['cache_hit_rate'] = (
                stats['cache_hits'] / max(stats['total_requests'], 1) * 100
            )
            endpoint_stats['error_rate'] = (
                stats['errors'] / max(stats['total_requests'], 1) * 100
            )
            endpoint_stats['rate_limited_rate'] = (
                stats['rate_limited'] / max(stats['total_requests'], 1) * 100
            )
            all_stats[name] = endpoint_stats
        
        return all_stats
    
    def clear_cache(self, endpoint_name: str = None):
        """
        Limpiar caché de endpoints
        
        Args:
            endpoint_name: Endpoint específico (opcional)
        """
        if endpoint_name:
            pattern = f"api_cache:*{endpoint_name}*"
            cache_manager.clear_pattern(pattern)
            logger.info(f"Cleared cache for endpoint: {endpoint_name}")
        else:
            cache_manager.clear_pattern("api_cache:*")
            logger.info("Cleared all API cache")
    
    def close(self):
        """
        Cerrar sesiones y limpiar recursos
        """
        self.session.close()
        
        if self.async_session:
            asyncio.run(self.async_session.close())

# Instancia global del optimizador
api_optimizer = APIOptimizer()

def optimized_api_call(endpoint_name: str, cache_ttl: int = None, 
                      use_cache: bool = True):
    """
    Decorador para calls de API optimizadas
    
    Args:
        endpoint_name: Nombre del endpoint registrado
        cache_ttl: Tiempo de vida del caché (opcional)
        use_cache: Si usar caché
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extraer parámetros de la función
            url = kwargs.get('url') or (args[0] if args else None)
            method = kwargs.get('method', 'GET')
            
            if not url:
                return func(*args, **kwargs)
            
            return api_optimizer.make_request(
                endpoint_name=endpoint_name,
                url=url,
                method=method,
                use_cache=use_cache,
                **{k: v for k, v in kwargs.items() if k not in ['url', 'method']}
            )
        
        return wrapper
    return decorator

# Configuraciones predefinidas para APIs comunes
def setup_apify_endpoints(api_token: str):
    """
    Configurar endpoints de Apify optimizados
    
    Args:
        api_token: Token de API de Apify
    """
    # Facebook Scraper
    facebook_endpoint = APIEndpoint(
        name="facebook_scraper",
        base_url="https://api.apify.com/v2/acts/apify~facebook-posts-scraper/runs",
        rate_limit=RateLimitConfig(
            requests_per_minute=30,
            requests_per_hour=500,
            strategy=RateLimitStrategy.SLIDING_WINDOW
        ),
        cache_ttl=1800,  # 30 minutos
        timeout=60,
        headers={"Authorization": f"Bearer {api_token}"},
        auth_required=True
    )
    
    # Instagram Scraper
    instagram_endpoint = APIEndpoint(
        name="instagram_scraper",
        base_url="https://api.apify.com/v2/acts/apify~instagram-scraper/runs",
        rate_limit=RateLimitConfig(
            requests_per_minute=25,
            requests_per_hour=400,
            strategy=RateLimitStrategy.SLIDING_WINDOW
        ),
        cache_ttl=1800,
        timeout=60,
        headers={"Authorization": f"Bearer {api_token}"},
        auth_required=True
    )
    
    # Twitter Scraper
    twitter_endpoint = APIEndpoint(
        name="twitter_scraper",
        base_url="https://api.apify.com/v2/acts/apidojo~tweet-scraper-v2/runs",
        rate_limit=RateLimitConfig(
            requests_per_minute=20,
            requests_per_hour=300,
            strategy=RateLimitStrategy.SLIDING_WINDOW
        ),
        cache_ttl=1800,
        timeout=60,
        headers={"Authorization": f"Bearer {api_token}"},
        auth_required=True
    )
    
    # Registrar endpoints
    api_optimizer.register_endpoint(facebook_endpoint)
    api_optimizer.register_endpoint(instagram_endpoint)
    api_optimizer.register_endpoint(twitter_endpoint)
    
    logger.info("Apify endpoints configured with optimizations")

def setup_social_media_endpoints():
    """
    Configurar endpoints de redes sociales con optimizaciones
    """
    # Endpoint genérico para APIs de redes sociales
    social_endpoint = APIEndpoint(
        name="social_media_api",
        base_url="https://api.socialmedia.com/v1",
        rate_limit=RateLimitConfig(
            requests_per_minute=100,
            requests_per_hour=2000,
            strategy=RateLimitStrategy.TOKEN_BUCKET
        ),
        cache_ttl=3600,  # 1 hora
        timeout=30
    )
    
    api_optimizer.register_endpoint(social_endpoint)

# Funciones de utilidad para optimización
class ApifyOptimizedClient:
    """
    Cliente optimizado para Apify con caché inteligente
    """
    
    def __init__(self, api_token: str):
        self.api_token = api_token
        setup_apify_endpoints(api_token)
    
    @optimized_api_call("facebook_scraper", cache_ttl=1800)
    def get_facebook_data(self, profile_url: str, days: int = 7) -> Dict[str, Any]:
        """
        Obtener datos de Facebook optimizados
        
        Args:
            profile_url: URL del perfil de Facebook
            days: Número de días de datos
            
        Returns:
            Datos de Facebook
        """
        payload = {
            "startUrls": [{"url": profile_url}],
            "resultsLimit": 100,
            "maxRequestRetries": 3
        }
        
        return api_optimizer.make_request(
            endpoint_name="facebook_scraper",
            url="",
            method="POST",
            data=payload
        )
    
    @optimized_api_call("instagram_scraper", cache_ttl=1800)
    def get_instagram_data(self, profile_url: str, days: int = 7) -> Dict[str, Any]:
        """
        Obtener datos de Instagram optimizados
        
        Args:
            profile_url: URL del perfil de Instagram
            days: Número de días de datos
            
        Returns:
            Datos de Instagram
        """
        payload = {
            "usernames": [profile_url.split('/')[-1]],
            "resultsType": "posts",
            "resultsLimit": 100
        }
        
        return api_optimizer.make_request(
            endpoint_name="instagram_scraper",
            url="",
            method="POST",
            data=payload
        )
    
    def get_multiple_profiles(self, profiles: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Obtener datos de múltiples perfiles en paralelo
        
        Args:
            profiles: Lista de perfiles con 'platform' y 'url'
            
        Returns:
            Lista de datos de perfiles
        """
        requests = []
        
        for profile in profiles:
            platform = profile['platform'].lower()
            url = profile['url']
            
            if platform == 'facebook':
                requests.append({
                    'endpoint_name': 'facebook_scraper',
                    'url': '',
                    'method': 'POST',
                    'data': {
                        "startUrls": [{"url": url}],
                        "resultsLimit": 50
                    }
                })
            elif platform == 'instagram':
                username = url.split('/')[-1]
                requests.append({
                    'endpoint_name': 'instagram_scraper',
                    'url': '',
                    'method': 'POST',
                    'data': {
                        "usernames": [username],
                        "resultsType": "posts",
                        "resultsLimit": 50
                    }
                })
        
        return api_optimizer.batch_requests(requests, max_concurrent=3)

def get_api_performance_report() -> str:
    """
    Generar reporte de rendimiento de APIs
    
    Returns:
        Reporte formateado
    """
    stats = api_optimizer.get_endpoint_stats()
    
    report = f"""
REPORTE DE RENDIMIENTO DE APIs - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*70}

"""
    
    for endpoint_name, endpoint_stats in stats.items():
        report += f"""
ENDPOINT: {endpoint_name.upper()}
{'-'*50}
Total Requests: {endpoint_stats['total_requests']}
Cache Hit Rate: {endpoint_stats['cache_hit_rate']:.1f}%
Error Rate: {endpoint_stats['error_rate']:.1f}%
Rate Limited: {endpoint_stats['rate_limited_rate']:.1f}%
Avg Response Time: {endpoint_stats['avg_response_time']:.3f}s

"""
    
    return report

