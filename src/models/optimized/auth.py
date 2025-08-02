"""
Modelos de autenticación optimizados - SUPABASE-SPECIALIST
"""

from .database import db, UUIDMixin, TimestampMixin
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
import re
from datetime import datetime, timedelta

class User(UUIDMixin, TimestampMixin, UserMixin, db.Model):
    """Modelo optimizado de usuario con seguridad mejorada"""
    __tablename__ = 'users'
    __table_args__ = {'schema': 'auth'}
    
    # Información básica
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    username = db.Column(db.String(100), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Información personal
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    avatar_url = db.Column(db.Text)
    
    # Configuración de usuario
    timezone = db.Column(db.String(50), default='UTC')
    language = db.Column(db.String(10), default='es')
    theme = db.Column(db.String(20), default='light')
    
    # Estado de la cuenta
    is_active = db.Column(db.Boolean, default=True, index=True)
    is_verified = db.Column(db.Boolean, default=False)
    email_verified_at = db.Column(db.DateTime(timezone=True))
    last_login_at = db.Column(db.DateTime(timezone=True))
    
    # Relaciones
    sessions = db.relationship('UserSession', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    organization_memberships = db.relationship('OrganizationMember', backref='user', lazy='dynamic')
    
    # Constraints
    __table_args__ = (
        db.CheckConstraint(
            "email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'",
            name='valid_email_format'
        ),
        {'schema': 'auth'}
    )
    
    def set_password(self, password):
        """Establecer contraseña con hash seguro"""
        if len(password) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        
        # Validar complejidad de contraseña
        if not re.search(r'[A-Z]', password):
            raise ValueError("La contraseña debe contener al menos una mayúscula")
        if not re.search(r'[a-z]', password):
            raise ValueError("La contraseña debe contener al menos una minúscula")
        if not re.search(r'\d', password):
            raise ValueError("La contraseña debe contener al menos un número")
        
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
    
    def check_password(self, password):
        """Verificar contraseña"""
        return check_password_hash(self.password_hash, password)
    
    def update_last_login(self):
        """Actualizar último login"""
        self.last_login_at = datetime.utcnow()
        db.session.commit()
    
    def get_active_sessions(self):
        """Obtener sesiones activas"""
        return self.sessions.filter(
            UserSession.expires_at > datetime.utcnow()
        ).all()
    
    def revoke_all_sessions(self):
        """Revocar todas las sesiones activas"""
        self.sessions.update({'expires_at': datetime.utcnow()})
        db.session.commit()
    
    @property
    def full_name(self):
        """Nombre completo del usuario"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username
    
    @property
    def organizations(self):
        """Organizaciones del usuario"""
        from .analytics import Organization
        return db.session.query(Organization).join(
            OrganizationMember
        ).filter(
            OrganizationMember.user_id == self.id
        ).all()
    
    def has_permission(self, organization_id, permission):
        """Verificar si el usuario tiene un permiso específico"""
        membership = db.session.query(OrganizationMember).filter_by(
            user_id=self.id,
            organization_id=organization_id
        ).first()
        
        if not membership:
            return False
        
        # Roles con permisos automáticos
        if membership.role in ['owner', 'admin']:
            return True
        
        # Verificar permisos específicos
        permissions = membership.permissions or {}
        return permissions.get(permission, False)
    
    def to_dict(self, include_sensitive=False):
        """Convertir a diccionario"""
        data = {
            'id': self.id,
            'email': self.email,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'avatar_url': self.avatar_url,
            'timezone': self.timezone,
            'language': self.language,
            'theme': self.theme,
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'email_verified_at': self.email_verified_at.isoformat() if self.email_verified_at else None,
            'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
        
        if include_sensitive:
            data.update({
                'active_sessions_count': len(self.get_active_sessions()),
                'organizations_count': len(self.organizations)
            })
        
        return data
    
    def __repr__(self):
        return f'<User {self.username}>'

class UserSession(UUIDMixin, db.Model):
    """Modelo para sesiones de usuario con seguridad mejorada"""
    __tablename__ = 'user_sessions'
    __table_args__ = {'schema': 'auth'}
    
    user_id = db.Column(db.String(36), db.ForeignKey('auth.users.id'), nullable=False, index=True)
    token_hash = db.Column(db.String(255), nullable=False, index=True)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    
    # Información de la sesión
    ip_address = db.Column(db.INET)
    user_agent = db.Column(db.Text)
    
    # Metadatos
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
    
    @classmethod
    def create_session(cls, user_id, token_hash, expires_in_hours=24, ip_address=None, user_agent=None):
        """Crear nueva sesión"""
        session = cls(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=datetime.utcnow() + timedelta(hours=expires_in_hours),
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.session.add(session)
        db.session.commit()
        return session
    
    @classmethod
    def cleanup_expired_sessions(cls):
        """Limpiar sesiones expiradas"""
        expired_count = cls.query.filter(
            cls.expires_at < datetime.utcnow()
        ).delete()
        db.session.commit()
        return expired_count
    
    def is_valid(self):
        """Verificar si la sesión es válida"""
        return self.expires_at > datetime.utcnow()
    
    def extend_session(self, hours=24):
        """Extender duración de la sesión"""
        self.expires_at = datetime.utcnow() + timedelta(hours=hours)
        db.session.commit()
    
    def revoke(self):
        """Revocar sesión"""
        self.expires_at = datetime.utcnow()
        db.session.commit()
    
    def to_dict(self):
        """Convertir a diccionario"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'expires_at': self.expires_at.isoformat(),
            'ip_address': str(self.ip_address) if self.ip_address else None,
            'user_agent': self.user_agent,
            'created_at': self.created_at.isoformat(),
            'is_valid': self.is_valid()
        }
    
    def __repr__(self):
        return f'<UserSession {self.id} for user {self.user_id}>'

# Importar aquí para evitar importaciones circulares
from .analytics import OrganizationMember

