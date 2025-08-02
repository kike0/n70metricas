"""
Sistema de Monitoreo de Rendimiento
Performance-Optimizer Implementation
"""

import time
import psutil
import threading
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from functools import wraps
import logging
import json
from collections import deque, defaultdict
import statistics

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """
    Monitor de rendimiento del sistema con métricas en tiempo real
    """
    
    def __init__(self, max_samples: int = 1000):
        """
        Inicializar monitor de rendimiento
        
        Args:
            max_samples: Número máximo de muestras a mantener
        """
        self.max_samples = max_samples
        self.metrics = defaultdict(lambda: deque(maxlen=max_samples))
        self.start_time = time.time()
        self.request_count = 0
        self.error_count = 0
        self.active_requests = 0
        self.lock = threading.Lock()
        
        # Métricas de sistema
        self.system_metrics = deque(maxlen=max_samples)
        
        # Iniciar monitoreo de sistema en background
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_system, daemon=True)
        self.monitor_thread.start()
    
    def _monitor_system(self):
        """
        Monitorear métricas del sistema en background
        """
        while self.monitoring:
            try:
                # Obtener métricas del sistema
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                # Métricas de red si están disponibles
                try:
                    network = psutil.net_io_counters()
                    network_sent = network.bytes_sent
                    network_recv = network.bytes_recv
                except:
                    network_sent = network_recv = 0
                
                system_metric = {
                    'timestamp': datetime.now().isoformat(),
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'memory_used_gb': memory.used / (1024**3),
                    'memory_available_gb': memory.available / (1024**3),
                    'disk_percent': disk.percent,
                    'disk_used_gb': disk.used / (1024**3),
                    'disk_free_gb': disk.free / (1024**3),
                    'network_sent_mb': network_sent / (1024**2),
                    'network_recv_mb': network_recv / (1024**2),
                    'active_requests': self.active_requests,
                    'total_requests': self.request_count,
                    'error_rate': self.error_count / max(self.request_count, 1) * 100
                }
                
                with self.lock:
                    self.system_metrics.append(system_metric)
                
                time.sleep(5)  # Monitorear cada 5 segundos
                
            except Exception as e:
                logger.error(f"Error monitoring system: {e}")
                time.sleep(10)
    
    def record_request(self, endpoint: str, method: str, duration: float, 
                      status_code: int, user_id: Optional[str] = None):
        """
        Registrar métricas de una request HTTP
        
        Args:
            endpoint: Endpoint de la API
            method: Método HTTP
            duration: Duración en segundos
            status_code: Código de estado HTTP
            user_id: ID del usuario (opcional)
        """
        with self.lock:
            self.request_count += 1
            
            if status_code >= 400:
                self.error_count += 1
            
            metric = {
                'timestamp': datetime.now().isoformat(),
                'endpoint': endpoint,
                'method': method,
                'duration': duration,
                'status_code': status_code,
                'user_id': user_id
            }
            
            # Registrar en métricas generales
            self.metrics['requests'].append(metric)
            
            # Registrar por endpoint
            self.metrics[f'endpoint_{endpoint}'].append(metric)
            
            # Registrar tiempos de respuesta
            self.metrics['response_times'].append(duration)
    
    def record_database_query(self, query_type: str, duration: float, 
                            rows_affected: int = 0, cache_hit: bool = False):
        """
        Registrar métricas de consultas a base de datos
        
        Args:
            query_type: Tipo de consulta (SELECT, INSERT, etc.)
            duration: Duración en segundos
            rows_affected: Número de filas afectadas
            cache_hit: Si fue un hit de caché
        """
        with self.lock:
            metric = {
                'timestamp': datetime.now().isoformat(),
                'query_type': query_type,
                'duration': duration,
                'rows_affected': rows_affected,
                'cache_hit': cache_hit
            }
            
            self.metrics['database_queries'].append(metric)
            self.metrics[f'db_{query_type.lower()}'].append(metric)
    
    def record_apify_request(self, actor_name: str, duration: float, 
                           success: bool, data_size: int = 0):
        """
        Registrar métricas de requests a Apify
        
        Args:
            actor_name: Nombre del actor de Apify
            duration: Duración en segundos
            success: Si la request fue exitosa
            data_size: Tamaño de datos obtenidos
        """
        with self.lock:
            metric = {
                'timestamp': datetime.now().isoformat(),
                'actor_name': actor_name,
                'duration': duration,
                'success': success,
                'data_size': data_size
            }
            
            self.metrics['apify_requests'].append(metric)
            self.metrics[f'apify_{actor_name}'].append(metric)
    
    def record_cache_operation(self, operation: str, key: str, hit: bool, 
                             duration: float = 0):
        """
        Registrar métricas de operaciones de caché
        
        Args:
            operation: Tipo de operación (get, set, delete)
            key: Clave del caché
            hit: Si fue un hit (para operaciones get)
            duration: Duración de la operación
        """
        with self.lock:
            metric = {
                'timestamp': datetime.now().isoformat(),
                'operation': operation,
                'key': key,
                'hit': hit,
                'duration': duration
            }
            
            self.metrics['cache_operations'].append(metric)
    
    def get_summary_stats(self, minutes: int = 60) -> Dict[str, Any]:
        """
        Obtener estadísticas resumidas de los últimos N minutos
        
        Args:
            minutes: Número de minutos a analizar
            
        Returns:
            Diccionario con estadísticas
        """
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        with self.lock:
            # Filtrar métricas recientes
            recent_requests = [
                m for m in self.metrics['requests']
                if datetime.fromisoformat(m['timestamp']) > cutoff_time
            ]
            
            recent_db_queries = [
                m for m in self.metrics['database_queries']
                if datetime.fromisoformat(m['timestamp']) > cutoff_time
            ]
            
            recent_apify = [
                m for m in self.metrics['apify_requests']
                if datetime.fromisoformat(m['timestamp']) > cutoff_time
            ]
            
            recent_cache = [
                m for m in self.metrics['cache_operations']
                if datetime.fromisoformat(m['timestamp']) > cutoff_time
            ]
            
            # Calcular estadísticas
            stats = {
                'time_window_minutes': minutes,
                'timestamp': datetime.now().isoformat(),
                'requests': {
                    'total': len(recent_requests),
                    'rate_per_minute': len(recent_requests) / minutes,
                    'avg_response_time': statistics.mean([r['duration'] for r in recent_requests]) if recent_requests else 0,
                    'p95_response_time': statistics.quantiles([r['duration'] for r in recent_requests], n=20)[18] if len(recent_requests) > 20 else 0,
                    'error_rate': len([r for r in recent_requests if r['status_code'] >= 400]) / max(len(recent_requests), 1) * 100,
                    'active_requests': self.active_requests
                },
                'database': {
                    'total_queries': len(recent_db_queries),
                    'avg_query_time': statistics.mean([q['duration'] for q in recent_db_queries]) if recent_db_queries else 0,
                    'cache_hit_rate': len([q for q in recent_db_queries if q['cache_hit']]) / max(len(recent_db_queries), 1) * 100
                },
                'apify': {
                    'total_requests': len(recent_apify),
                    'success_rate': len([a for a in recent_apify if a['success']]) / max(len(recent_apify), 1) * 100,
                    'avg_duration': statistics.mean([a['duration'] for a in recent_apify]) if recent_apify else 0
                },
                'cache': {
                    'total_operations': len(recent_cache),
                    'hit_rate': len([c for c in recent_cache if c['hit'] and c['operation'] == 'get']) / max(len([c for c in recent_cache if c['operation'] == 'get']), 1) * 100
                }
            }
            
            # Añadir métricas de sistema más recientes
            if self.system_metrics:
                latest_system = self.system_metrics[-1]
                stats['system'] = {
                    'cpu_percent': latest_system['cpu_percent'],
                    'memory_percent': latest_system['memory_percent'],
                    'disk_percent': latest_system['disk_percent'],
                    'memory_used_gb': latest_system['memory_used_gb'],
                    'disk_used_gb': latest_system['disk_used_gb']
                }
            
            return stats
    
    def get_endpoint_stats(self, endpoint: str, minutes: int = 60) -> Dict[str, Any]:
        """
        Obtener estadísticas específicas de un endpoint
        
        Args:
            endpoint: Endpoint a analizar
            minutes: Número de minutos a analizar
            
        Returns:
            Estadísticas del endpoint
        """
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        with self.lock:
            endpoint_metrics = [
                m for m in self.metrics[f'endpoint_{endpoint}']
                if datetime.fromisoformat(m['timestamp']) > cutoff_time
            ]
            
            if not endpoint_metrics:
                return {'endpoint': endpoint, 'no_data': True}
            
            durations = [m['duration'] for m in endpoint_metrics]
            status_codes = [m['status_code'] for m in endpoint_metrics]
            
            return {
                'endpoint': endpoint,
                'total_requests': len(endpoint_metrics),
                'avg_response_time': statistics.mean(durations),
                'min_response_time': min(durations),
                'max_response_time': max(durations),
                'p95_response_time': statistics.quantiles(durations, n=20)[18] if len(durations) > 20 else max(durations),
                'error_rate': len([s for s in status_codes if s >= 400]) / len(status_codes) * 100,
                'requests_per_minute': len(endpoint_metrics) / minutes
            }
    
    def get_system_health(self) -> Dict[str, Any]:
        """
        Obtener estado de salud del sistema
        
        Returns:
            Estado de salud con alertas
        """
        stats = self.get_summary_stats(minutes=5)  # Últimos 5 minutos
        
        health = {
            'status': 'healthy',
            'alerts': [],
            'timestamp': datetime.now().isoformat()
        }
        
        # Verificar alertas
        if stats.get('system', {}).get('cpu_percent', 0) > 80:
            health['alerts'].append({
                'level': 'warning',
                'message': f"High CPU usage: {stats['system']['cpu_percent']:.1f}%"
            })
            health['status'] = 'warning'
        
        if stats.get('system', {}).get('memory_percent', 0) > 85:
            health['alerts'].append({
                'level': 'critical',
                'message': f"High memory usage: {stats['system']['memory_percent']:.1f}%"
            })
            health['status'] = 'critical'
        
        if stats['requests']['error_rate'] > 10:
            health['alerts'].append({
                'level': 'warning',
                'message': f"High error rate: {stats['requests']['error_rate']:.1f}%"
            })
            health['status'] = 'warning'
        
        if stats['requests']['avg_response_time'] > 2.0:
            health['alerts'].append({
                'level': 'warning',
                'message': f"Slow response times: {stats['requests']['avg_response_time']:.2f}s"
            })
            health['status'] = 'warning'
        
        if stats['database']['cache_hit_rate'] < 70:
            health['alerts'].append({
                'level': 'info',
                'message': f"Low cache hit rate: {stats['database']['cache_hit_rate']:.1f}%"
            })
        
        return health
    
    def export_metrics(self, format: str = 'json') -> str:
        """
        Exportar métricas en formato especificado
        
        Args:
            format: Formato de exportación ('json', 'prometheus')
            
        Returns:
            Métricas en formato solicitado
        """
        if format == 'json':
            return json.dumps(self.get_summary_stats(), indent=2)
        elif format == 'prometheus':
            # Formato Prometheus
            stats = self.get_summary_stats()
            prometheus_metrics = []
            
            # Métricas de requests
            prometheus_metrics.append(f"http_requests_total {stats['requests']['total']}")
            prometheus_metrics.append(f"http_request_duration_seconds {stats['requests']['avg_response_time']}")
            prometheus_metrics.append(f"http_error_rate_percent {stats['requests']['error_rate']}")
            
            # Métricas de sistema
            if 'system' in stats:
                prometheus_metrics.append(f"system_cpu_percent {stats['system']['cpu_percent']}")
                prometheus_metrics.append(f"system_memory_percent {stats['system']['memory_percent']}")
                prometheus_metrics.append(f"system_disk_percent {stats['system']['disk_percent']}")
            
            return '\n'.join(prometheus_metrics)
        
        return "Unsupported format"
    
    def stop_monitoring(self):
        """
        Detener el monitoreo del sistema
        """
        self.monitoring = False
        if self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)

# Instancia global del monitor
performance_monitor = PerformanceMonitor()

def monitor_performance(endpoint: str = None, track_db: bool = False):
    """
    Decorador para monitorear rendimiento de funciones
    
    Args:
        endpoint: Nombre del endpoint (opcional)
        track_db: Si rastrear como operación de base de datos
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            # Incrementar requests activos
            performance_monitor.active_requests += 1
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Registrar métricas exitosas
                if endpoint:
                    performance_monitor.record_request(
                        endpoint=endpoint,
                        method='FUNCTION',
                        duration=duration,
                        status_code=200
                    )
                
                if track_db:
                    performance_monitor.record_database_query(
                        query_type='SELECT',
                        duration=duration,
                        cache_hit=False
                    )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                # Registrar métricas de error
                if endpoint:
                    performance_monitor.record_request(
                        endpoint=endpoint,
                        method='FUNCTION',
                        duration=duration,
                        status_code=500
                    )
                
                raise e
                
            finally:
                # Decrementar requests activos
                performance_monitor.active_requests -= 1
        
        return wrapper
    return decorator

class FlaskPerformanceMiddleware:
    """
    Middleware para Flask que registra métricas automáticamente
    """
    
    def __init__(self, app):
        self.app = app
        self.app.before_request(self._before_request)
        self.app.after_request(self._after_request)
        self.app.teardown_request(self._teardown_request)
    
    def _before_request(self):
        from flask import g, request
        g.start_time = time.time()
        performance_monitor.active_requests += 1
    
    def _after_request(self, response):
        from flask import g, request
        
        if hasattr(g, 'start_time'):
            duration = time.time() - g.start_time
            
            performance_monitor.record_request(
                endpoint=request.endpoint or 'unknown',
                method=request.method,
                duration=duration,
                status_code=response.status_code,
                user_id=getattr(g, 'user_id', None)
            )
        
        return response
    
    def _teardown_request(self, exception):
        performance_monitor.active_requests -= 1

# Funciones de utilidad
def get_performance_dashboard_data() -> Dict[str, Any]:
    """
    Obtener datos para dashboard de rendimiento
    
    Returns:
        Datos formateados para dashboard
    """
    stats_5min = performance_monitor.get_summary_stats(minutes=5)
    stats_60min = performance_monitor.get_summary_stats(minutes=60)
    health = performance_monitor.get_system_health()
    
    return {
        'current': stats_5min,
        'hourly': stats_60min,
        'health': health,
        'uptime_hours': (time.time() - performance_monitor.start_time) / 3600
    }

def generate_performance_report() -> str:
    """
    Generar reporte de rendimiento en texto
    
    Returns:
        Reporte formateado
    """
    stats = performance_monitor.get_summary_stats(minutes=60)
    health = performance_monitor.get_system_health()
    
    report = f"""
REPORTE DE RENDIMIENTO - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*60}

ESTADO DEL SISTEMA: {health['status'].upper()}
Uptime: {(time.time() - performance_monitor.start_time) / 3600:.1f} horas

REQUESTS (última hora):
- Total: {stats['requests']['total']}
- Rate: {stats['requests']['rate_per_minute']:.1f} req/min
- Tiempo promedio: {stats['requests']['avg_response_time']:.3f}s
- P95: {stats['requests']['p95_response_time']:.3f}s
- Error rate: {stats['requests']['error_rate']:.1f}%
- Activos: {stats['requests']['active_requests']}

BASE DE DATOS:
- Consultas: {stats['database']['total_queries']}
- Tiempo promedio: {stats['database']['avg_query_time']:.3f}s
- Cache hit rate: {stats['database']['cache_hit_rate']:.1f}%

APIFY:
- Requests: {stats['apify']['total_requests']}
- Success rate: {stats['apify']['success_rate']:.1f}%
- Tiempo promedio: {stats['apify']['avg_duration']:.3f}s

SISTEMA:
- CPU: {stats.get('system', {}).get('cpu_percent', 0):.1f}%
- Memoria: {stats.get('system', {}).get('memory_percent', 0):.1f}%
- Disco: {stats.get('system', {}).get('disk_percent', 0):.1f}%

ALERTAS:
"""
    
    for alert in health['alerts']:
        report += f"- [{alert['level'].upper()}] {alert['message']}\n"
    
    if not health['alerts']:
        report += "- No hay alertas activas\n"
    
    return report

