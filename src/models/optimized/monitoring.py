"""
Modelos de monitoreo del sistema - SUPABASE-SPECIALIST
"""

from .database import db, UUIDMixin
from sqlalchemy.dialects.postgresql import JSONB, INET
from sqlalchemy import Index, func
from datetime import datetime

class SystemMetric(UUIDMixin, db.Model):
    """Modelo para métricas del sistema"""
    __tablename__ = 'system_metrics'
    __table_args__ = (
        Index('idx_system_metrics_name_time', 'metric_name', 'recorded_at'),
        {'schema': 'monitoring'}
    )
    
    metric_name = db.Column(db.String(100), nullable=False)
    metric_value = db.Column(db.Numeric(15,4), nullable=False)
    metric_unit = db.Column(db.String(20))
    tags = db.Column(JSONB, default={})
    recorded_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    
    @classmethod
    def record_metric(cls, name, value, unit=None, tags=None):
        """Registrar una métrica del sistema"""
        metric = cls(
            metric_name=name,
            metric_value=value,
            metric_unit=unit,
            tags=tags or {}
        )
        db.session.add(metric)
        db.session.commit()
        return metric
    
    @classmethod
    def get_latest_metrics(cls, metric_names=None, hours=24):
        """Obtener métricas más recientes"""
        query = cls.query.filter(
            cls.recorded_at >= datetime.utcnow() - timedelta(hours=hours)
        )
        
        if metric_names:
            query = query.filter(cls.metric_name.in_(metric_names))
        
        return query.order_by(cls.recorded_at.desc()).all()
    
    def to_dict(self):
        """Convertir a diccionario"""
        return {
            'id': self.id,
            'metric_name': self.metric_name,
            'metric_value': float(self.metric_value),
            'metric_unit': self.metric_unit,
            'tags': self.tags,
            'recorded_at': self.recorded_at.isoformat()
        }

class ApiUsage(UUIDMixin, db.Model):
    """Modelo para uso de API"""
    __tablename__ = 'api_usage'
    __table_args__ = (
        Index('idx_api_usage_org_time', 'organization_id', 'created_at'),
        Index('idx_api_usage_endpoint', 'endpoint'),
        {'schema': 'monitoring'}
    )
    
    organization_id = db.Column(db.String(36), db.ForeignKey('analytics.organizations.id'))
    user_id = db.Column(db.String(36), db.ForeignKey('auth.users.id'))
    
    # Información de la API
    endpoint = db.Column(db.String(200), nullable=False)
    method = db.Column(db.String(10), nullable=False)
    status_code = db.Column(db.Integer, nullable=False)
    response_time_ms = db.Column(db.Integer)
    
    # Request info
    ip_address = db.Column(INET)
    user_agent = db.Column(db.Text)
    request_size = db.Column(db.Integer)
    response_size = db.Column(db.Integer)
    
    # Metadatos
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    
    @classmethod
    def log_request(cls, endpoint, method, status_code, response_time_ms=None, 
                   organization_id=None, user_id=None, ip_address=None, 
                   user_agent=None, request_size=None, response_size=None):
        """Registrar uso de API"""
        usage = cls(
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            response_time_ms=response_time_ms,
            organization_id=organization_id,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            request_size=request_size,
            response_size=response_size
        )
        db.session.add(usage)
        db.session.commit()
        return usage
    
    @classmethod
    def get_usage_stats(cls, organization_id=None, hours=24):
        """Obtener estadísticas de uso"""
        query = cls.query.filter(
            cls.created_at >= datetime.utcnow() - timedelta(hours=hours)
        )
        
        if organization_id:
            query = query.filter(cls.organization_id == organization_id)
        
        stats = {
            'total_requests': query.count(),
            'successful_requests': query.filter(cls.status_code < 400).count(),
            'error_requests': query.filter(cls.status_code >= 400).count(),
            'avg_response_time': query.with_entities(func.avg(cls.response_time_ms)).scalar() or 0
        }
        
        return stats
    
    def to_dict(self):
        """Convertir a diccionario"""
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'user_id': self.user_id,
            'endpoint': self.endpoint,
            'method': self.method,
            'status_code': self.status_code,
            'response_time_ms': self.response_time_ms,
            'ip_address': str(self.ip_address) if self.ip_address else None,
            'user_agent': self.user_agent,
            'request_size': self.request_size,
            'response_size': self.response_size,
            'created_at': self.created_at.isoformat()
        }

class ErrorLog(UUIDMixin, db.Model):
    """Modelo para logs de errores"""
    __tablename__ = 'error_logs'
    __table_args__ = (
        Index('idx_error_logs_level_time', 'level', 'created_at'),
        {'schema': 'monitoring'}
    )
    
    level = db.Column(db.String(20), nullable=False)  # ERROR, WARNING, INFO
    message = db.Column(db.Text, nullable=False)
    error_code = db.Column(db.String(50))
    stack_trace = db.Column(db.Text)
    context = db.Column(JSONB, default={})
    
    # Asociaciones
    user_id = db.Column(db.String(36), db.ForeignKey('auth.users.id'))
    organization_id = db.Column(db.String(36), db.ForeignKey('analytics.organizations.id'))
    campaign_id = db.Column(db.String(36), db.ForeignKey('analytics.campaigns.id'))
    
    # Metadatos
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    
    @classmethod
    def log_error(cls, level, message, error_code=None, stack_trace=None, 
                  context=None, user_id=None, organization_id=None, campaign_id=None):
        """Registrar un error"""
        error_log = cls(
            level=level,
            message=message,
            error_code=error_code,
            stack_trace=stack_trace,
            context=context or {},
            user_id=user_id,
            organization_id=organization_id,
            campaign_id=campaign_id
        )
        db.session.add(error_log)
        db.session.commit()
        return error_log
    
    @classmethod
    def get_recent_errors(cls, level=None, hours=24, limit=100):
        """Obtener errores recientes"""
        query = cls.query.filter(
            cls.created_at >= datetime.utcnow() - timedelta(hours=hours)
        )
        
        if level:
            query = query.filter(cls.level == level)
        
        return query.order_by(cls.created_at.desc()).limit(limit).all()
    
    def to_dict(self):
        """Convertir a diccionario"""
        return {
            'id': self.id,
            'level': self.level,
            'message': self.message,
            'error_code': self.error_code,
            'stack_trace': self.stack_trace,
            'context': self.context,
            'user_id': self.user_id,
            'organization_id': self.organization_id,
            'campaign_id': self.campaign_id,
            'created_at': self.created_at.isoformat()
        }

# Importar timedelta para las funciones de clase
from datetime import timedelta

