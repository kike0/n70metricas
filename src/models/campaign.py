"""
Modelos de datos para campañas de monitoreo de redes sociales
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from src.models.user import db

class Campaign(db.Model):
    """Modelo para campañas de monitoreo"""
    __tablename__ = 'campaigns'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Configuración de la campaña
    report_frequency = db.Column(db.String(50), default='weekly')  # daily, weekly, monthly
    auto_generate = db.Column(db.Boolean, default=False)
    
    # Relaciones
    profiles = db.relationship('SocialProfile', backref='campaign', lazy=True, cascade='all, delete-orphan')
    reports = db.relationship('Report', backref='campaign', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active,
            'report_frequency': self.report_frequency,
            'auto_generate': self.auto_generate,
            'profiles_count': len(self.profiles),
            'reports_count': len(self.reports)
        }

class SocialProfile(db.Model):
    """Modelo para perfiles de redes sociales a monitorear"""
    __tablename__ = 'social_profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), nullable=False)
    
    # Información del perfil
    name = db.Column(db.String(200), nullable=False)
    platform = db.Column(db.String(50), nullable=False)  # facebook, instagram, twitter, tiktok, youtube
    username = db.Column(db.String(200))
    profile_url = db.Column(db.String(500))
    
    # Configuración de scraping
    max_posts = db.Column(db.Integer, default=50)
    scrape_comments = db.Column(db.Boolean, default=True)
    scrape_reactions = db.Column(db.Boolean, default=True)
    
    # Metadatos
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_scraped = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relaciones
    metrics = db.relationship('SocialMetric', backref='profile', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'campaign_id': self.campaign_id,
            'name': self.name,
            'platform': self.platform,
            'username': self.username,
            'profile_url': self.profile_url,
            'max_posts': self.max_posts,
            'scrape_comments': self.scrape_comments,
            'scrape_reactions': self.scrape_reactions,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_scraped': self.last_scraped.isoformat() if self.last_scraped else None,
            'is_active': self.is_active
        }

class SocialMetric(db.Model):
    """Modelo para métricas de redes sociales"""
    __tablename__ = 'social_metrics'
    
    id = db.Column(db.Integer, primary_key=True)
    profile_id = db.Column(db.Integer, db.ForeignKey('social_profiles.id'), nullable=False)
    
    # Fecha de la métrica
    date = db.Column(db.Date, nullable=False)
    
    # Métricas básicas
    followers = db.Column(db.Integer, default=0)
    posts_count = db.Column(db.Integer, default=0)
    video_posts_count = db.Column(db.Integer, default=0)
    
    # Métricas de engagement
    total_interactions = db.Column(db.Integer, default=0)
    total_video_interactions = db.Column(db.Integer, default=0)
    total_views = db.Column(db.Integer, default=0)
    
    # Métricas de crecimiento
    followers_growth = db.Column(db.Integer, default=0)
    engagement_rate = db.Column(db.Float, default=0.0)
    
    # Metadatos
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    apify_run_id = db.Column(db.String(100))  # ID de la ejecución en Apify
    
    def to_dict(self):
        return {
            'id': self.id,
            'profile_id': self.profile_id,
            'date': self.date.isoformat() if self.date else None,
            'followers': self.followers,
            'posts_count': self.posts_count,
            'video_posts_count': self.video_posts_count,
            'total_interactions': self.total_interactions,
            'total_video_interactions': self.total_video_interactions,
            'total_views': self.total_views,
            'followers_growth': self.followers_growth,
            'engagement_rate': self.engagement_rate,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'apify_run_id': self.apify_run_id
        }

class Report(db.Model):
    """Modelo para reportes generados"""
    __tablename__ = 'reports'
    
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), nullable=False)
    
    # Información del reporte
    title = db.Column(db.String(300), nullable=False)
    period_start = db.Column(db.Date, nullable=False)
    period_end = db.Column(db.Date, nullable=False)
    
    # Archivos generados
    pdf_path = db.Column(db.String(500))
    json_data = db.Column(db.Text)  # Datos del reporte en JSON
    
    # Estado
    status = db.Column(db.String(50), default='pending')  # pending, generating, completed, failed
    
    # Metadatos
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    def to_dict(self):
        return {
            'id': self.id,
            'campaign_id': self.campaign_id,
            'title': self.title,
            'period_start': self.period_start.isoformat() if self.period_start else None,
            'period_end': self.period_end.isoformat() if self.period_end else None,
            'pdf_path': self.pdf_path,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

