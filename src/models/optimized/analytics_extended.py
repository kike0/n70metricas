"""
Modelos de analytics extendidos - SUPABASE-SPECIALIST
Métricas, Posts, Comentarios y Reportes
"""

from .database import db, UUIDMixin, TimestampMixin
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Index, CheckConstraint, UniqueConstraint, func
from datetime import datetime, date, timedelta
from decimal import Decimal

class DailyMetric(UUIDMixin, TimestampMixin, db.Model):
    """Modelo optimizado para métricas diarias"""
    __tablename__ = 'daily_metrics'
    __table_args__ = (
        UniqueConstraint('profile_id', 'metric_date'),
        Index('idx_daily_metrics_profile_date', 'profile_id', 'metric_date'),
        Index('idx_daily_metrics_engagement', 'engagement_rate'),
        {'schema': 'analytics'}
    )
    
    profile_id = db.Column(db.String(36), db.ForeignKey('analytics.social_profiles.id'), nullable=False)
    extraction_job_id = db.Column(db.String(36), db.ForeignKey('analytics.extraction_jobs.id'))
    
    # Fecha de la métrica
    metric_date = db.Column(db.Date, nullable=False, index=True)
    
    # Métricas de audiencia
    followers_count = db.Column(db.Integer, default=0)
    following_count = db.Column(db.Integer, default=0)
    followers_growth = db.Column(db.Integer, default=0)
    
    # Métricas de contenido
    posts_count = db.Column(db.Integer, default=0)
    video_posts_count = db.Column(db.Integer, default=0)
    image_posts_count = db.Column(db.Integer, default=0)
    text_posts_count = db.Column(db.Integer, default=0)
    
    # Métricas de engagement
    total_likes = db.Column(db.Integer, default=0)
    total_comments = db.Column(db.Integer, default=0)
    total_shares = db.Column(db.Integer, default=0)
    total_reactions = db.Column(db.Integer, default=0)
    total_views = db.Column(db.Integer, default=0)
    
    # Métricas calculadas
    engagement_rate = db.Column(db.Numeric(5,4), default=0)
    avg_likes_per_post = db.Column(db.Numeric(10,2), default=0)
    avg_comments_per_post = db.Column(db.Numeric(10,2), default=0)
    avg_shares_per_post = db.Column(db.Numeric(10,2), default=0)
    
    # Métricas específicas de video
    video_views = db.Column(db.Integer, default=0)
    video_completion_rate = db.Column(db.Numeric(5,4), default=0)
    avg_watch_time = db.Column(db.Integer, default=0)  # en segundos
    
    # Datos adicionales
    top_performing_post_id = db.Column(db.String(200))
    top_performing_post_engagement = db.Column(db.Integer, default=0)
    
    def calculate_engagement_rate(self):
        """Calcular engagement rate automáticamente"""
        if self.followers_count > 0:
            total_engagement = (self.total_likes or 0) + (self.total_comments or 0) + (self.total_shares or 0)
            self.engagement_rate = Decimal(total_engagement) / Decimal(self.followers_count)
        else:
            self.engagement_rate = Decimal(0)
    
    def calculate_averages(self):
        """Calcular promedios por post"""
        if self.posts_count > 0:
            self.avg_likes_per_post = Decimal(self.total_likes or 0) / Decimal(self.posts_count)
            self.avg_comments_per_post = Decimal(self.total_comments or 0) / Decimal(self.posts_count)
            self.avg_shares_per_post = Decimal(self.total_shares or 0) / Decimal(self.posts_count)
        else:
            self.avg_likes_per_post = Decimal(0)
            self.avg_comments_per_post = Decimal(0)
            self.avg_shares_per_post = Decimal(0)
    
    @property
    def total_interactions(self):
        """Total de interacciones"""
        return (self.total_likes or 0) + (self.total_comments or 0) + (self.total_shares or 0)
    
    def to_dict(self):
        """Convertir a diccionario"""
        return {
            'id': self.id,
            'profile_id': self.profile_id,
            'extraction_job_id': self.extraction_job_id,
            'metric_date': self.metric_date.isoformat(),
            'followers_count': self.followers_count,
            'following_count': self.following_count,
            'followers_growth': self.followers_growth,
            'posts_count': self.posts_count,
            'video_posts_count': self.video_posts_count,
            'image_posts_count': self.image_posts_count,
            'text_posts_count': self.text_posts_count,
            'total_likes': self.total_likes,
            'total_comments': self.total_comments,
            'total_shares': self.total_shares,
            'total_reactions': self.total_reactions,
            'total_views': self.total_views,
            'total_interactions': self.total_interactions,
            'engagement_rate': float(self.engagement_rate) if self.engagement_rate else 0,
            'avg_likes_per_post': float(self.avg_likes_per_post) if self.avg_likes_per_post else 0,
            'avg_comments_per_post': float(self.avg_comments_per_post) if self.avg_comments_per_post else 0,
            'avg_shares_per_post': float(self.avg_shares_per_post) if self.avg_shares_per_post else 0,
            'video_views': self.video_views,
            'video_completion_rate': float(self.video_completion_rate) if self.video_completion_rate else 0,
            'avg_watch_time': self.avg_watch_time,
            'top_performing_post_id': self.top_performing_post_id,
            'top_performing_post_engagement': self.top_performing_post_engagement,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class Post(UUIDMixin, TimestampMixin, db.Model):
    """Modelo optimizado para posts de redes sociales"""
    __tablename__ = 'posts'
    __table_args__ = (
        UniqueConstraint('profile_id', 'platform_post_id'),
        Index('idx_posts_published_at', 'published_at'),
        Index('idx_posts_engagement', 'likes_count', 'comments_count', 'shares_count'),
        {'schema': 'analytics'}
    )
    
    profile_id = db.Column(db.String(36), db.ForeignKey('analytics.social_profiles.id'), nullable=False)
    extraction_job_id = db.Column(db.String(36), db.ForeignKey('analytics.extraction_jobs.id'))
    
    # Identificadores de la plataforma
    platform_post_id = db.Column(db.String(200), nullable=False)
    platform_url = db.Column(db.Text)
    
    # Contenido del post
    content = db.Column(db.Text)
    content_type = db.Column(db.String(50))  # text, image, video, carousel, story
    media_urls = db.Column(JSONB, default=[])
    hashtags = db.Column(JSONB, default=[])
    mentions = db.Column(JSONB, default=[])
    
    # Métricas del post
    likes_count = db.Column(db.Integer, default=0)
    comments_count = db.Column(db.Integer, default=0)
    shares_count = db.Column(db.Integer, default=0)
    reactions_count = db.Column(db.Integer, default=0)
    views_count = db.Column(db.Integer, default=0)
    
    # Métricas específicas de video
    video_duration = db.Column(db.Integer)  # en segundos
    video_views = db.Column(db.Integer, default=0)
    video_completion_rate = db.Column(db.Numeric(5,4))
    
    # Análisis de sentimiento
    sentiment_score = db.Column(db.Numeric(3,2))  # -1 a 1
    sentiment_label = db.Column(db.String(20))  # positive, negative, neutral
    sentiment_confidence = db.Column(db.Numeric(3,2))  # 0 a 1
    
    # Fechas
    published_at = db.Column(db.DateTime(timezone=True))
    extracted_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    
    # Estado
    is_active = db.Column(db.Boolean, default=True)
    is_deleted = db.Column(db.Boolean, default=False)
    
    # Relaciones
    comments = db.relationship('Comment', backref='post', lazy='dynamic', cascade='all, delete-orphan')
    
    @property
    def total_engagement(self):
        """Total de engagement del post"""
        return (self.likes_count or 0) + (self.comments_count or 0) + (self.shares_count or 0)
    
    @property
    def engagement_rate(self):
        """Calcular engagement rate del post"""
        if self.views_count and self.views_count > 0:
            return self.total_engagement / self.views_count
        return 0
    
    def extract_hashtags(self):
        """Extraer hashtags del contenido"""
        if not self.content:
            return []
        
        import re
        hashtags = re.findall(r'#\w+', self.content)
        return [tag.lower() for tag in hashtags]
    
    def extract_mentions(self):
        """Extraer menciones del contenido"""
        if not self.content:
            return []
        
        import re
        mentions = re.findall(r'@\w+', self.content)
        return [mention.lower() for mention in mentions]
    
    def update_sentiment(self, score, label, confidence):
        """Actualizar análisis de sentimiento"""
        self.sentiment_score = Decimal(str(score))
        self.sentiment_label = label
        self.sentiment_confidence = Decimal(str(confidence))
        db.session.commit()
    
    def to_dict(self, include_comments=False):
        """Convertir a diccionario"""
        data = {
            'id': self.id,
            'profile_id': self.profile_id,
            'extraction_job_id': self.extraction_job_id,
            'platform_post_id': self.platform_post_id,
            'platform_url': self.platform_url,
            'content': self.content,
            'content_type': self.content_type,
            'media_urls': self.media_urls,
            'hashtags': self.hashtags,
            'mentions': self.mentions,
            'likes_count': self.likes_count,
            'comments_count': self.comments_count,
            'shares_count': self.shares_count,
            'reactions_count': self.reactions_count,
            'views_count': self.views_count,
            'total_engagement': self.total_engagement,
            'engagement_rate': self.engagement_rate,
            'video_duration': self.video_duration,
            'video_views': self.video_views,
            'video_completion_rate': float(self.video_completion_rate) if self.video_completion_rate else None,
            'sentiment_score': float(self.sentiment_score) if self.sentiment_score else None,
            'sentiment_label': self.sentiment_label,
            'sentiment_confidence': float(self.sentiment_confidence) if self.sentiment_confidence else None,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'extracted_at': self.extracted_at.isoformat() if self.extracted_at else None,
            'is_active': self.is_active,
            'is_deleted': self.is_deleted,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
        
        if include_comments:
            data['comments'] = [comment.to_dict() for comment in self.comments.filter_by(is_active=True).limit(10)]
        
        return data

class Comment(UUIDMixin, db.Model):
    """Modelo optimizado para comentarios"""
    __tablename__ = 'comments'
    __table_args__ = (
        UniqueConstraint('post_id', 'platform_comment_id'),
        Index('idx_comments_published_at', 'published_at'),
        Index('idx_comments_sentiment', 'sentiment_label'),
        {'schema': 'analytics'}
    )
    
    post_id = db.Column(db.String(36), db.ForeignKey('analytics.posts.id'), nullable=False)
    
    # Identificadores
    platform_comment_id = db.Column(db.String(200), nullable=False)
    parent_comment_id = db.Column(db.String(36), db.ForeignKey('analytics.comments.id'))
    
    # Contenido
    content = db.Column(db.Text, nullable=False)
    author_name = db.Column(db.String(200))
    author_username = db.Column(db.String(200))
    author_profile_url = db.Column(db.Text)
    
    # Métricas
    likes_count = db.Column(db.Integer, default=0)
    replies_count = db.Column(db.Integer, default=0)
    
    # Análisis de sentimiento
    sentiment_score = db.Column(db.Numeric(3,2))
    sentiment_label = db.Column(db.String(20))
    sentiment_confidence = db.Column(db.Numeric(3,2))
    
    # Fechas
    published_at = db.Column(db.DateTime(timezone=True))
    extracted_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    
    # Estado
    is_active = db.Column(db.Boolean, default=True)
    is_spam = db.Column(db.Boolean, default=False)
    
    # Metadatos
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    
    # Relaciones
    replies = db.relationship('Comment', backref=db.backref('parent', remote_side='Comment.id'), lazy='dynamic')
    
    def update_sentiment(self, score, label, confidence):
        """Actualizar análisis de sentimiento"""
        self.sentiment_score = Decimal(str(score))
        self.sentiment_label = label
        self.sentiment_confidence = Decimal(str(confidence))
        db.session.commit()
    
    def to_dict(self, include_replies=False):
        """Convertir a diccionario"""
        data = {
            'id': self.id,
            'post_id': self.post_id,
            'platform_comment_id': self.platform_comment_id,
            'parent_comment_id': self.parent_comment_id,
            'content': self.content,
            'author_name': self.author_name,
            'author_username': self.author_username,
            'author_profile_url': self.author_profile_url,
            'likes_count': self.likes_count,
            'replies_count': self.replies_count,
            'sentiment_score': float(self.sentiment_score) if self.sentiment_score else None,
            'sentiment_label': self.sentiment_label,
            'sentiment_confidence': float(self.sentiment_confidence) if self.sentiment_confidence else None,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'extracted_at': self.extracted_at.isoformat() if self.extracted_at else None,
            'is_active': self.is_active,
            'is_spam': self.is_spam,
            'created_at': self.created_at.isoformat()
        }
        
        if include_replies:
            data['replies'] = [reply.to_dict() for reply in self.replies.filter_by(is_active=True).limit(5)]
        
        return data

class Report(UUIDMixin, TimestampMixin, db.Model):
    """Modelo optimizado para reportes"""
    __tablename__ = 'reports'
    __table_args__ = (
        Index('idx_reports_status', 'status'),
        Index('idx_reports_share_token', 'share_token'),
        {'schema': 'analytics'}
    )
    
    campaign_id = db.Column(db.String(36), db.ForeignKey('analytics.campaigns.id'), nullable=False)
    created_by = db.Column(db.String(36), db.ForeignKey('auth.users.id'), nullable=False)
    
    # Información del reporte
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    report_type = db.Column(db.String(50), default='standard')  # standard, custom, automated
    
    # Período del reporte
    period_start = db.Column(db.Date, nullable=False)
    period_end = db.Column(db.Date, nullable=False)
    
    # Configuración
    include_sentiment = db.Column(db.Boolean, default=True)
    include_top_posts = db.Column(db.Boolean, default=True)
    include_comments_analysis = db.Column(db.Boolean, default=False)
    top_posts_count = db.Column(db.Integer, default=3)
    
    # Archivos generados
    pdf_file_path = db.Column(db.Text)
    json_data = db.Column(JSONB)
    excel_file_path = db.Column(db.Text)
    
    # Estado de generación
    status = db.Column(db.String(20), default='pending')  # pending, generating, completed, failed
    generation_progress = db.Column(db.Integer, default=0)  # 0-100
    
    # Estadísticas del reporte
    total_profiles = db.Column(db.Integer, default=0)
    total_posts = db.Column(db.Integer, default=0)
    total_interactions = db.Column(db.Integer, default=0)
    
    # Configuración de acceso
    is_public = db.Column(db.Boolean, default=False)
    share_token = db.Column(db.String(100), unique=True)
    expires_at = db.Column(db.DateTime(timezone=True))
    completed_at = db.Column(db.DateTime(timezone=True))
    
    # Relaciones
    sections = db.relationship('ReportSection', backref='report', lazy='dynamic', cascade='all, delete-orphan')
    
    def generate_share_token(self):
        """Generar token para compartir"""
        import secrets
        self.share_token = secrets.token_urlsafe(32)
        db.session.commit()
        return self.share_token
    
    def update_progress(self, progress, status=None):
        """Actualizar progreso de generación"""
        self.generation_progress = min(100, max(0, progress))
        if status:
            self.status = status
        
        if progress >= 100 and status == 'completed':
            self.completed_at = datetime.utcnow()
        
        db.session.commit()
    
    def is_accessible_by_token(self, token):
        """Verificar si el reporte es accesible con el token"""
        if not self.is_public or not self.share_token:
            return False
        
        if self.expires_at and self.expires_at < datetime.utcnow():
            return False
        
        return self.share_token == token
    
    def to_dict(self, include_sections=False):
        """Convertir a diccionario"""
        data = {
            'id': self.id,
            'campaign_id': self.campaign_id,
            'created_by': self.created_by,
            'title': self.title,
            'description': self.description,
            'report_type': self.report_type,
            'period_start': self.period_start.isoformat(),
            'period_end': self.period_end.isoformat(),
            'include_sentiment': self.include_sentiment,
            'include_top_posts': self.include_top_posts,
            'include_comments_analysis': self.include_comments_analysis,
            'top_posts_count': self.top_posts_count,
            'pdf_file_path': self.pdf_file_path,
            'json_data': self.json_data,
            'excel_file_path': self.excel_file_path,
            'status': self.status,
            'generation_progress': self.generation_progress,
            'total_profiles': self.total_profiles,
            'total_posts': self.total_posts,
            'total_interactions': self.total_interactions,
            'is_public': self.is_public,
            'share_token': self.share_token if self.is_public else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
        
        if include_sections:
            data['sections'] = [section.to_dict() for section in self.sections.order_by('order_index')]
        
        return data

class ReportSection(UUIDMixin, db.Model):
    """Modelo para secciones de reportes"""
    __tablename__ = 'report_sections'
    __table_args__ = {'schema': 'analytics'}
    
    report_id = db.Column(db.String(36), db.ForeignKey('analytics.reports.id'), nullable=False)
    
    # Información de la sección
    section_type = db.Column(db.String(50), nullable=False)  # summary, metrics, top_posts, sentiment, growth
    title = db.Column(db.String(200), nullable=False)
    order_index = db.Column(db.Integer, nullable=False)
    
    # Contenido
    content = db.Column(JSONB, nullable=False)
    chart_config = db.Column(JSONB)
    
    # Estado
    is_visible = db.Column(db.Boolean, default=True)
    
    # Metadatos
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    
    def to_dict(self):
        """Convertir a diccionario"""
        return {
            'id': self.id,
            'report_id': self.report_id,
            'section_type': self.section_type,
            'title': self.title,
            'order_index': self.order_index,
            'content': self.content,
            'chart_config': self.chart_config,
            'is_visible': self.is_visible,
            'created_at': self.created_at.isoformat()
        }

# Agregar las clases al archivo principal de analytics
from .analytics import *

