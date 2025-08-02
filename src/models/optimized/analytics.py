"""
Modelos de analytics optimizados - SUPABASE-SPECIALIST
Sistema de Reportes de Redes Sociales
"""

from .database import db, UUIDMixin, TimestampMixin
from sqlalchemy.dialects.postgresql import JSONB, UUID, INET
from sqlalchemy import Index, CheckConstraint, UniqueConstraint
from datetime import datetime, date, timedelta
import json

class Organization(UUIDMixin, TimestampMixin, db.Model):
    """Modelo optimizado de organización"""
    __tablename__ = 'organizations'
    __table_args__ = {'schema': 'analytics'}
    
    # Información básica
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    logo_url = db.Column(db.Text)
    website_url = db.Column(db.Text)
    
    # Configuración
    timezone = db.Column(db.String(50), default='UTC')
    default_currency = db.Column(db.String(3), default='USD')
    
    # Límites y cuotas
    max_campaigns = db.Column(db.Integer, default=10)
    max_profiles_per_campaign = db.Column(db.Integer, default=50)
    max_monthly_extractions = db.Column(db.Integer, default=1000)
    
    # Estado
    is_active = db.Column(db.Boolean, default=True, index=True)
    subscription_tier = db.Column(db.String(20), default='basic')
    subscription_expires_at = db.Column(db.DateTime(timezone=True))
    
    # Relaciones
    members = db.relationship('OrganizationMember', backref='organization', lazy='dynamic', cascade='all, delete-orphan')
    campaigns = db.relationship('Campaign', backref='organization', lazy='dynamic', cascade='all, delete-orphan')
    
    def get_usage_stats(self):
        """Obtener estadísticas de uso"""
        return {
            'campaigns_count': self.campaigns.filter_by(status='active').count(),
            'total_profiles': db.session.query(SocialProfile).join(Campaign).filter(
                Campaign.organization_id == self.id
            ).count(),
            'monthly_extractions': db.session.query(ExtractionJob).join(Campaign).filter(
                Campaign.organization_id == self.id,
                ExtractionJob.created_at >= datetime.utcnow() - timedelta(days=30)
            ).count()
        }
    
    def can_create_campaign(self):
        """Verificar si puede crear más campañas"""
        active_campaigns = self.campaigns.filter_by(status='active').count()
        return active_campaigns < self.max_campaigns
    
    def to_dict(self, include_stats=False):
        """Convertir a diccionario"""
        data = {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'logo_url': self.logo_url,
            'website_url': self.website_url,
            'timezone': self.timezone,
            'default_currency': self.default_currency,
            'subscription_tier': self.subscription_tier,
            'subscription_expires_at': self.subscription_expires_at.isoformat() if self.subscription_expires_at else None,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
        
        if include_stats:
            data['usage_stats'] = self.get_usage_stats()
            data['limits'] = {
                'max_campaigns': self.max_campaigns,
                'max_profiles_per_campaign': self.max_profiles_per_campaign,
                'max_monthly_extractions': self.max_monthly_extractions
            }
        
        return data

class OrganizationMember(UUIDMixin, db.Model):
    """Modelo para miembros de organización"""
    __tablename__ = 'organization_members'
    __table_args__ = (
        UniqueConstraint('organization_id', 'user_id'),
        {'schema': 'analytics'}
    )
    
    organization_id = db.Column(db.String(36), db.ForeignKey('analytics.organizations.id'), nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey('auth.users.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='member')  # owner, admin, member, viewer
    permissions = db.Column(JSONB, default={})
    invited_by = db.Column(db.String(36), db.ForeignKey('auth.users.id'))
    joined_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
    
    def has_permission(self, permission):
        """Verificar permiso específico"""
        if self.role in ['owner', 'admin']:
            return True
        return self.permissions.get(permission, False)
    
    def to_dict(self):
        """Convertir a diccionario"""
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'user_id': self.user_id,
            'role': self.role,
            'permissions': self.permissions,
            'invited_by': self.invited_by,
            'joined_at': self.joined_at.isoformat()
        }

class SocialPlatform(db.Model):
    """Modelo para plataformas de redes sociales"""
    __tablename__ = 'social_platforms'
    __table_args__ = {'schema': 'analytics'}
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    display_name = db.Column(db.String(100), nullable=False)
    icon_url = db.Column(db.Text)
    base_url = db.Column(db.Text)
    api_rate_limit = db.Column(db.Integer, default=100)
    supports_comments = db.Column(db.Boolean, default=True)
    supports_reactions = db.Column(db.Boolean, default=True)
    supports_shares = db.Column(db.Boolean, default=True)
    supports_video_metrics = db.Column(db.Boolean, default=True)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relaciones
    profiles = db.relationship('SocialProfile', backref='platform', lazy='dynamic')
    
    def to_dict(self):
        """Convertir a diccionario"""
        return {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name,
            'icon_url': self.icon_url,
            'base_url': self.base_url,
            'api_rate_limit': self.api_rate_limit,
            'supports_comments': self.supports_comments,
            'supports_reactions': self.supports_reactions,
            'supports_shares': self.supports_shares,
            'supports_video_metrics': self.supports_video_metrics,
            'is_active': self.is_active
        }

class Campaign(UUIDMixin, TimestampMixin, db.Model):
    """Modelo optimizado de campaña"""
    __tablename__ = 'campaigns'
    __table_args__ = (
        UniqueConstraint('organization_id', 'slug'),
        Index('idx_campaigns_status', 'status'),
        {'schema': 'analytics'}
    )
    
    organization_id = db.Column(db.String(36), db.ForeignKey('analytics.organizations.id'), nullable=False)
    created_by = db.Column(db.String(36), db.ForeignKey('auth.users.id'), nullable=False)
    
    # Información básica
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    slug = db.Column(db.String(100), nullable=False)
    
    # Configuración de monitoreo
    monitoring_frequency = db.Column(db.String(20), default='daily')
    auto_generate_reports = db.Column(db.Boolean, default=False)
    report_frequency = db.Column(db.String(20), default='weekly')
    
    # Configuración de extracción
    max_posts_per_profile = db.Column(db.Integer, default=100)
    extract_comments = db.Column(db.Boolean, default=True)
    extract_reactions = db.Column(db.Boolean, default=True)
    extract_shares = db.Column(db.Boolean, default=True)
    sentiment_analysis = db.Column(db.Boolean, default=True)
    
    # Período de análisis
    analysis_start_date = db.Column(db.Date)
    analysis_end_date = db.Column(db.Date)
    
    # Estado
    status = db.Column(db.String(20), default='active')  # active, paused, archived
    is_public = db.Column(db.Boolean, default=False)
    last_extraction_at = db.Column(db.DateTime(timezone=True))
    
    # Relaciones
    profiles = db.relationship('SocialProfile', backref='campaign', lazy='dynamic', cascade='all, delete-orphan')
    extraction_jobs = db.relationship('ExtractionJob', backref='campaign', lazy='dynamic', cascade='all, delete-orphan')
    reports = db.relationship('Report', backref='campaign', lazy='dynamic', cascade='all, delete-orphan')
    
    def get_metrics_summary(self, days=7):
        """Obtener resumen de métricas"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        metrics = db.session.query(DailyMetric).join(SocialProfile).filter(
            SocialProfile.campaign_id == self.id,
            DailyMetric.metric_date.between(start_date, end_date)
        ).all()
        
        if not metrics:
            return {}
        
        total_followers = sum(m.followers_count for m in metrics if m.followers_count)
        total_interactions = sum(
            (m.total_likes or 0) + (m.total_comments or 0) + (m.total_shares or 0) 
            for m in metrics
        )
        avg_engagement = sum(m.engagement_rate or 0 for m in metrics) / len(metrics)
        
        return {
            'total_followers': total_followers,
            'total_interactions': total_interactions,
            'avg_engagement_rate': round(avg_engagement, 4),
            'profiles_count': self.profiles.filter_by(is_active=True).count(),
            'posts_count': db.session.query(Post).join(SocialProfile).filter(
                SocialProfile.campaign_id == self.id,
                Post.published_at >= datetime.combine(start_date, datetime.min.time())
            ).count()
        }
    
    def can_add_profile(self):
        """Verificar si puede añadir más perfiles"""
        current_profiles = self.profiles.filter_by(is_active=True).count()
        return current_profiles < self.organization.max_profiles_per_campaign
    
    def to_dict(self, include_metrics=False):
        """Convertir a diccionario"""
        data = {
            'id': self.id,
            'organization_id': self.organization_id,
            'created_by': self.created_by,
            'name': self.name,
            'description': self.description,
            'slug': self.slug,
            'monitoring_frequency': self.monitoring_frequency,
            'auto_generate_reports': self.auto_generate_reports,
            'report_frequency': self.report_frequency,
            'max_posts_per_profile': self.max_posts_per_profile,
            'extract_comments': self.extract_comments,
            'extract_reactions': self.extract_reactions,
            'extract_shares': self.extract_shares,
            'sentiment_analysis': self.sentiment_analysis,
            'analysis_start_date': self.analysis_start_date.isoformat() if self.analysis_start_date else None,
            'analysis_end_date': self.analysis_end_date.isoformat() if self.analysis_end_date else None,
            'status': self.status,
            'is_public': self.is_public,
            'last_extraction_at': self.last_extraction_at.isoformat() if self.last_extraction_at else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'profiles_count': self.profiles.filter_by(is_active=True).count()
        }
        
        if include_metrics:
            data['metrics_summary'] = self.get_metrics_summary()
        
        return data

class SocialProfile(UUIDMixin, TimestampMixin, db.Model):
    """Modelo optimizado de perfil social"""
    __tablename__ = 'social_profiles'
    __table_args__ = (
        UniqueConstraint('campaign_id', 'platform_id', 'username'),
        Index('idx_social_profiles_active', 'is_active'),
        {'schema': 'analytics'}
    )
    
    campaign_id = db.Column(db.String(36), db.ForeignKey('analytics.campaigns.id'), nullable=False)
    platform_id = db.Column(db.Integer, db.ForeignKey('analytics.social_platforms.id'), nullable=False)
    
    # Información del perfil
    name = db.Column(db.String(200), nullable=False)
    username = db.Column(db.String(200))
    profile_url = db.Column(db.Text, nullable=False)
    profile_id = db.Column(db.String(200))  # ID interno de la plataforma
    
    # Configuración específica
    extraction_config = db.Column(JSONB, default={})
    custom_fields = db.Column(JSONB, default={})
    
    # Estado de monitoreo
    is_active = db.Column(db.Boolean, default=True, index=True)
    monitoring_enabled = db.Column(db.Boolean, default=True)
    last_successful_extraction = db.Column(db.DateTime(timezone=True))
    last_failed_extraction = db.Column(db.DateTime(timezone=True))
    consecutive_failures = db.Column(db.Integer, default=0)
    
    # Relaciones
    daily_metrics = db.relationship('DailyMetric', backref='profile', lazy='dynamic', cascade='all, delete-orphan')
    posts = db.relationship('Post', backref='profile', lazy='dynamic', cascade='all, delete-orphan')
    
    def get_latest_metrics(self, days=7):
        """Obtener métricas más recientes"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        return self.daily_metrics.filter(
            DailyMetric.metric_date.between(start_date, end_date)
        ).order_by(DailyMetric.metric_date.desc()).all()
    
    def get_top_posts(self, limit=5, days=30):
        """Obtener posts con mejor rendimiento"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        return self.posts.filter(
            Post.published_at >= cutoff_date,
            Post.is_active == True
        ).order_by(
            (Post.likes_count + Post.comments_count + Post.shares_count).desc()
        ).limit(limit).all()
    
    def update_extraction_status(self, success=True, error_message=None):
        """Actualizar estado de extracción"""
        if success:
            self.last_successful_extraction = datetime.utcnow()
            self.consecutive_failures = 0
        else:
            self.last_failed_extraction = datetime.utcnow()
            self.consecutive_failures += 1
            
            # Desactivar monitoreo después de muchos fallos
            if self.consecutive_failures >= 5:
                self.monitoring_enabled = False
        
        db.session.commit()
    
    def to_dict(self, include_metrics=False):
        """Convertir a diccionario"""
        data = {
            'id': self.id,
            'campaign_id': self.campaign_id,
            'platform_id': self.platform_id,
            'platform_name': self.platform.name if self.platform else None,
            'name': self.name,
            'username': self.username,
            'profile_url': self.profile_url,
            'profile_id': self.profile_id,
            'extraction_config': self.extraction_config,
            'custom_fields': self.custom_fields,
            'is_active': self.is_active,
            'monitoring_enabled': self.monitoring_enabled,
            'last_successful_extraction': self.last_successful_extraction.isoformat() if self.last_successful_extraction else None,
            'last_failed_extraction': self.last_failed_extraction.isoformat() if self.last_failed_extraction else None,
            'consecutive_failures': self.consecutive_failures,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
        
        if include_metrics:
            latest_metrics = self.get_latest_metrics()
            if latest_metrics:
                latest = latest_metrics[0]
                data['latest_metrics'] = {
                    'followers_count': latest.followers_count,
                    'engagement_rate': float(latest.engagement_rate) if latest.engagement_rate else 0,
                    'total_interactions': (latest.total_likes or 0) + (latest.total_comments or 0) + (latest.total_shares or 0),
                    'metric_date': latest.metric_date.isoformat()
                }
        
        return data

# Continúo con los demás modelos en la siguiente parte...
class ExtractionJob(UUIDMixin, TimestampMixin, db.Model):
    """Modelo para jobs de extracción de datos"""
    __tablename__ = 'extraction_jobs'
    __table_args__ = (
        Index('idx_extraction_jobs_status', 'status'),
        {'schema': 'analytics'}
    )
    
    campaign_id = db.Column(db.String(36), db.ForeignKey('analytics.campaigns.id'), nullable=False)
    profile_id = db.Column(db.String(36), db.ForeignKey('analytics.social_profiles.id'))
    
    # Información del job
    job_type = db.Column(db.String(50), nullable=False)  # full_extraction, incremental, metrics_only
    status = db.Column(db.String(20), default='pending')  # pending, running, completed, failed, cancelled
    
    # Configuración de Apify
    apify_actor_id = db.Column(db.String(100))
    apify_run_id = db.Column(db.String(100))
    apify_task_id = db.Column(db.String(100))
    
    # Progreso y resultados
    total_profiles = db.Column(db.Integer, default=0)
    processed_profiles = db.Column(db.Integer, default=0)
    extracted_posts = db.Column(db.Integer, default=0)
    extracted_comments = db.Column(db.Integer, default=0)
    
    # Tiempos
    started_at = db.Column(db.DateTime(timezone=True))
    completed_at = db.Column(db.DateTime(timezone=True))
    estimated_completion = db.Column(db.DateTime(timezone=True))
    
    # Errores y logs
    error_message = db.Column(db.Text)
    error_details = db.Column(JSONB)
    execution_log = db.Column(JSONB, default=[])
    
    def add_log_entry(self, level, message, details=None):
        """Añadir entrada al log"""
        if not self.execution_log:
            self.execution_log = []
        
        entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': level,
            'message': message
        }
        
        if details:
            entry['details'] = details
        
        self.execution_log.append(entry)
        db.session.commit()
    
    def update_progress(self, processed_profiles=None, extracted_posts=None, extracted_comments=None):
        """Actualizar progreso del job"""
        if processed_profiles is not None:
            self.processed_profiles = processed_profiles
        if extracted_posts is not None:
            self.extracted_posts = extracted_posts
        if extracted_comments is not None:
            self.extracted_comments = extracted_comments
        
        db.session.commit()
    
    @property
    def progress_percentage(self):
        """Calcular porcentaje de progreso"""
        if self.total_profiles == 0:
            return 0
        return min(100, (self.processed_profiles / self.total_profiles) * 100)
    
    def to_dict(self):
        """Convertir a diccionario"""
        return {
            'id': self.id,
            'campaign_id': self.campaign_id,
            'profile_id': self.profile_id,
            'job_type': self.job_type,
            'status': self.status,
            'apify_actor_id': self.apify_actor_id,
            'apify_run_id': self.apify_run_id,
            'apify_task_id': self.apify_task_id,
            'total_profiles': self.total_profiles,
            'processed_profiles': self.processed_profiles,
            'extracted_posts': self.extracted_posts,
            'extracted_comments': self.extracted_comments,
            'progress_percentage': self.progress_percentage,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'estimated_completion': self.estimated_completion.isoformat() if self.estimated_completion else None,
            'error_message': self.error_message,
            'error_details': self.error_details,
            'execution_log': self.execution_log,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

# Continúo con DailyMetric, Post, Comment, Report y ReportSection en archivos separados por límite de espacio...

