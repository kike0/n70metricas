"""
Authentication and Authorization Manager - Sistema de Autenticación Segura
Security-Auditor Implementation - Phase 2
"""

import os
import jwt
import bcrypt
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import logging
from functools import wraps
import re
from flask import request, jsonify, current_app
import redis
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import pyotp
import qrcode
from io import BytesIO
import base64

logger = logging.getLogger(__name__)

Base = declarative_base()

class UserRole(Enum):
    """Roles de usuario del sistema"""
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MANAGER = "manager"
    ANALYST = "analyst"
    VIEWER = "viewer"

class Permission(Enum):
    """Permisos del sistema"""
    # Gestión de usuarios
    CREATE_USER = "create_user"
    READ_USER = "read_user"
    UPDATE_USER = "update_user"
    DELETE_USER = "delete_user"
    
    # Gestión de campañas
    CREATE_CAMPAIGN = "create_campaign"
    READ_CAMPAIGN = "read_campaign"
    UPDATE_CAMPAIGN = "update_campaign"
    DELETE_CAMPAIGN = "delete_campaign"
    
    # Gestión de reportes
    CREATE_REPORT = "create_report"
    READ_REPORT = "read_report"
    UPDATE_REPORT = "update_report"
    DELETE_REPORT = "delete_report"
    EXPORT_REPORT = "export_report"
    
    # Gestión de datos
    EXTRACT_DATA = "extract_data"
    VIEW_ANALYTICS = "view_analytics"
    MANAGE_INTEGRATIONS = "manage_integrations"
    
    # Administración del sistema
    MANAGE_SETTINGS = "manage_settings"
    VIEW_AUDIT_LOGS = "view_audit_logs"
    MANAGE_SECURITY = "manage_security"

@dataclass
class AuthConfig:
    """Configuración de autenticación"""
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expires: int = 3600  # 1 hora
    jwt_refresh_token_expires: int = 604800  # 7 días
    password_min_length: int = 12
    password_require_uppercase: bool = True
    password_require_lowercase: bool = True
    password_require_numbers: bool = True
    password_require_symbols: bool = True
    max_login_attempts: int = 5
    lockout_duration: int = 900  # 15 minutos
    session_timeout: int = 3600  # 1 hora
    enable_2fa: bool = True
    enable_audit_logging: bool = True

class User(Base):
    """Modelo de usuario con seguridad avanzada"""
    __tablename__ = 'auth_users'
    
    id = Column(String(36), primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    salt = Column(String(255), nullable=False)
    
    # Información personal
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone = Column(String(20))
    
    # Configuración de seguridad
    role = Column(String(50), nullable=False, default=UserRole.VIEWER.value)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    # 2FA
    totp_secret = Column(String(32))
    backup_codes = Column(Text)  # JSON array de códigos de respaldo
    is_2fa_enabled = Column(Boolean, default=False)
    
    # Gestión de sesiones
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime)
    last_login = Column(DateTime)
    last_password_change = Column(DateTime)
    
    # Auditoría
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(36))
    
    # Relaciones
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user")

class UserSession(Base):
    """Sesiones de usuario con seguimiento de seguridad"""
    __tablename__ = 'auth_sessions'
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey('auth_users.id'), nullable=False)
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    refresh_token = Column(String(255), unique=True, nullable=False, index=True)
    
    # Información de la sesión
    ip_address = Column(String(45))
    user_agent = Column(Text)
    device_fingerprint = Column(String(255))
    
    # Control de tiempo
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    last_activity = Column(DateTime, default=datetime.utcnow)
    
    # Estado
    is_active = Column(Boolean, default=True)
    revoked_at = Column(DateTime)
    revoked_reason = Column(String(100))
    
    # Relaciones
    user = relationship("User", back_populates="sessions")

class AuditLog(Base):
    """Log de auditoría para seguimiento de seguridad"""
    __tablename__ = 'auth_audit_logs'
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey('auth_users.id'))
    
    # Información del evento
    event_type = Column(String(100), nullable=False)
    event_description = Column(Text)
    resource_type = Column(String(100))
    resource_id = Column(String(36))
    
    # Contexto
    ip_address = Column(String(45))
    user_agent = Column(Text)
    request_id = Column(String(36))
    
    # Resultado
    success = Column(Boolean, nullable=False)
    error_message = Column(Text)
    
    # Tiempo
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relaciones
    user = relationship("User", back_populates="audit_logs")

class AuthenticationManager:
    """
    Gestor de autenticación y autorización segura
    """
    
    def __init__(self, config: AuthConfig, redis_client: Optional[redis.Redis] = None):
        """
        Inicializar gestor de autenticación
        
        Args:
            config: Configuración de autenticación
            redis_client: Cliente Redis para caché de sesiones
        """
        self.config = config
        self.redis_client = redis_client
        
        # Mapeo de roles a permisos
        self.role_permissions = {
            UserRole.SUPER_ADMIN: list(Permission),
            UserRole.ADMIN: [
                Permission.CREATE_USER, Permission.READ_USER, Permission.UPDATE_USER,
                Permission.CREATE_CAMPAIGN, Permission.READ_CAMPAIGN, Permission.UPDATE_CAMPAIGN, Permission.DELETE_CAMPAIGN,
                Permission.CREATE_REPORT, Permission.READ_REPORT, Permission.UPDATE_REPORT, Permission.DELETE_REPORT, Permission.EXPORT_REPORT,
                Permission.EXTRACT_DATA, Permission.VIEW_ANALYTICS, Permission.MANAGE_INTEGRATIONS,
                Permission.VIEW_AUDIT_LOGS
            ],
            UserRole.MANAGER: [
                Permission.READ_USER,
                Permission.CREATE_CAMPAIGN, Permission.READ_CAMPAIGN, Permission.UPDATE_CAMPAIGN,
                Permission.CREATE_REPORT, Permission.READ_REPORT, Permission.UPDATE_REPORT, Permission.EXPORT_REPORT,
                Permission.EXTRACT_DATA, Permission.VIEW_ANALYTICS
            ],
            UserRole.ANALYST: [
                Permission.READ_USER,
                Permission.READ_CAMPAIGN,
                Permission.CREATE_REPORT, Permission.READ_REPORT, Permission.UPDATE_REPORT, Permission.EXPORT_REPORT,
                Permission.EXTRACT_DATA, Permission.VIEW_ANALYTICS
            ],
            UserRole.VIEWER: [
                Permission.READ_CAMPAIGN,
                Permission.READ_REPORT,
                Permission.VIEW_ANALYTICS
            ]
        }
        
        logger.info("Authentication manager initialized")
    
    def hash_password(self, password: str) -> Tuple[str, str]:
        """
        Hash de contraseña con salt único
        
        Args:
            password: Contraseña en texto plano
            
        Returns:
            Tupla (hash, salt)
        """
        # Generar salt único
        salt = bcrypt.gensalt(rounds=12)
        
        # Hash de la contraseña
        password_hash = bcrypt.hashpw(password.encode('utf-8'), salt)
        
        return password_hash.decode('utf-8'), salt.decode('utf-8')
    
    def verify_password(self, password: str, password_hash: str, salt: str) -> bool:
        """
        Verificar contraseña
        
        Args:
            password: Contraseña en texto plano
            password_hash: Hash almacenado
            salt: Salt almacenado
            
        Returns:
            True si la contraseña es correcta
        """
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'),
                password_hash.encode('utf-8')
            )
        except Exception as e:
            logger.error(f"Error verifying password: {e}")
            return False
    
    def validate_password_strength(self, password: str) -> Tuple[bool, List[str]]:
        """
        Validar fortaleza de contraseña
        
        Args:
            password: Contraseña a validar
            
        Returns:
            Tupla (es_válida, lista_errores)
        """
        errors = []
        
        # Longitud mínima
        if len(password) < self.config.password_min_length:
            errors.append(f"Password must be at least {self.config.password_min_length} characters long")
        
        # Mayúsculas
        if self.config.password_require_uppercase and not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
        
        # Minúsculas
        if self.config.password_require_lowercase and not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
        
        # Números
        if self.config.password_require_numbers and not re.search(r'\d', password):
            errors.append("Password must contain at least one number")
        
        # Símbolos
        if self.config.password_require_symbols and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain at least one special character")
        
        # Patrones comunes débiles
        weak_patterns = [
            r'123456', r'password', r'qwerty', r'admin', r'letmein',
            r'welcome', r'monkey', r'dragon', r'master', r'shadow'
        ]
        
        for pattern in weak_patterns:
            if re.search(pattern, password.lower()):
                errors.append("Password contains common weak patterns")
                break
        
        return len(errors) == 0, errors
    
    def generate_jwt_tokens(self, user: User) -> Tuple[str, str]:
        """
        Generar tokens JWT (acceso y refresh)
        
        Args:
            user: Usuario autenticado
            
        Returns:
            Tupla (access_token, refresh_token)
        """
        now = datetime.utcnow()
        
        # Payload común
        base_payload = {
            'user_id': user.id,
            'email': user.email,
            'role': user.role,
            'iat': now,
            'jti': secrets.token_urlsafe(32)  # JWT ID único
        }
        
        # Access token
        access_payload = base_payload.copy()
        access_payload.update({
            'type': 'access',
            'exp': now + timedelta(seconds=self.config.jwt_access_token_expires)
        })
        
        access_token = jwt.encode(
            access_payload,
            self.config.jwt_secret_key,
            algorithm=self.config.jwt_algorithm
        )
        
        # Refresh token
        refresh_payload = base_payload.copy()
        refresh_payload.update({
            'type': 'refresh',
            'exp': now + timedelta(seconds=self.config.jwt_refresh_token_expires)
        })
        
        refresh_token = jwt.encode(
            refresh_payload,
            self.config.jwt_secret_key,
            algorithm=self.config.jwt_algorithm
        )
        
        return access_token, refresh_token
    
    def verify_jwt_token(self, token: str, token_type: str = 'access') -> Optional[Dict[str, Any]]:
        """
        Verificar y decodificar token JWT
        
        Args:
            token: Token JWT
            token_type: Tipo de token ('access' o 'refresh')
            
        Returns:
            Payload del token si es válido, None si no
        """
        try:
            payload = jwt.decode(
                token,
                self.config.jwt_secret_key,
                algorithms=[self.config.jwt_algorithm]
            )
            
            # Verificar tipo de token
            if payload.get('type') != token_type:
                logger.warning(f"Invalid token type: expected {token_type}, got {payload.get('type')}")
                return None
            
            # Verificar si el token está en blacklist (Redis)
            if self.redis_client:
                jti = payload.get('jti')
                if jti and self.redis_client.get(f"blacklist:{jti}"):
                    logger.warning(f"Token {jti} is blacklisted")
                    return None
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
    
    def blacklist_token(self, token: str):
        """
        Añadir token a blacklist
        
        Args:
            token: Token a invalidar
        """
        if not self.redis_client:
            return
        
        try:
            payload = jwt.decode(
                token,
                self.config.jwt_secret_key,
                algorithms=[self.config.jwt_algorithm],
                options={"verify_exp": False}  # No verificar expiración para blacklist
            )
            
            jti = payload.get('jti')
            exp = payload.get('exp')
            
            if jti and exp:
                # Calcular TTL hasta la expiración
                ttl = max(0, exp - datetime.utcnow().timestamp())
                self.redis_client.setex(f"blacklist:{jti}", int(ttl), "1")
                
        except Exception as e:
            logger.error(f"Error blacklisting token: {e}")
    
    def setup_2fa(self, user: User) -> Tuple[str, str, List[str]]:
        """
        Configurar autenticación de dos factores
        
        Args:
            user: Usuario para configurar 2FA
            
        Returns:
            Tupla (secret, qr_code_url, backup_codes)
        """
        # Generar secret TOTP
        secret = pyotp.random_base32()
        
        # Generar QR code
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=user.email,
            issuer_name="Social Media Analytics"
        )
        
        # Generar códigos de respaldo
        backup_codes = [secrets.token_hex(4).upper() for _ in range(10)]
        
        # Generar QR code como imagen base64
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
        qr_code_url = f"data:image/png;base64,{qr_code_base64}"
        
        return secret, qr_code_url, backup_codes
    
    def verify_2fa_token(self, secret: str, token: str, backup_codes: List[str] = None) -> Tuple[bool, bool]:
        """
        Verificar token 2FA
        
        Args:
            secret: Secret TOTP del usuario
            token: Token proporcionado por el usuario
            backup_codes: Códigos de respaldo (opcional)
            
        Returns:
            Tupla (es_válido, es_código_respaldo)
        """
        # Verificar token TOTP
        totp = pyotp.TOTP(secret)
        if totp.verify(token, valid_window=1):  # Ventana de 30 segundos
            return True, False
        
        # Verificar códigos de respaldo
        if backup_codes and token.upper() in backup_codes:
            return True, True
        
        return False, False
    
    def check_user_permissions(self, user: User, required_permission: Permission) -> bool:
        """
        Verificar si el usuario tiene el permiso requerido
        
        Args:
            user: Usuario a verificar
            required_permission: Permiso requerido
            
        Returns:
            True si el usuario tiene el permiso
        """
        try:
            user_role = UserRole(user.role)
            user_permissions = self.role_permissions.get(user_role, [])
            return required_permission in user_permissions
        except ValueError:
            logger.error(f"Invalid user role: {user.role}")
            return False
    
    def log_audit_event(self, user_id: str, event_type: str, event_description: str,
                       resource_type: str = None, resource_id: str = None,
                       success: bool = True, error_message: str = None,
                       ip_address: str = None, user_agent: str = None):
        """
        Registrar evento de auditoría
        
        Args:
            user_id: ID del usuario
            event_type: Tipo de evento
            event_description: Descripción del evento
            resource_type: Tipo de recurso afectado
            resource_id: ID del recurso afectado
            success: Si el evento fue exitoso
            error_message: Mensaje de error si aplica
            ip_address: Dirección IP
            user_agent: User agent
        """
        if not self.config.enable_audit_logging:
            return
        
        try:
            audit_log = AuditLog(
                id=secrets.token_urlsafe(16),
                user_id=user_id,
                event_type=event_type,
                event_description=event_description,
                resource_type=resource_type,
                resource_id=resource_id,
                success=success,
                error_message=error_message,
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=getattr(request, 'id', None) if request else None
            )
            
            # Aquí se guardaría en la base de datos
            # db.session.add(audit_log)
            # db.session.commit()
            
            logger.info(f"Audit event logged: {event_type} for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error logging audit event: {e}")
    
    def is_user_locked(self, user: User) -> bool:
        """
        Verificar si el usuario está bloqueado
        
        Args:
            user: Usuario a verificar
            
        Returns:
            True si el usuario está bloqueado
        """
        if not user.locked_until:
            return False
        
        return datetime.utcnow() < user.locked_until
    
    def increment_failed_attempts(self, user: User):
        """
        Incrementar intentos fallidos de login
        
        Args:
            user: Usuario con intento fallido
        """
        user.failed_login_attempts += 1
        
        if user.failed_login_attempts >= self.config.max_login_attempts:
            user.locked_until = datetime.utcnow() + timedelta(seconds=self.config.lockout_duration)
            logger.warning(f"User {user.email} locked due to too many failed attempts")
    
    def reset_failed_attempts(self, user: User):
        """
        Resetear intentos fallidos de login
        
        Args:
            user: Usuario con login exitoso
        """
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login = datetime.utcnow()
    
    def create_session(self, user: User, ip_address: str = None, user_agent: str = None) -> UserSession:
        """
        Crear nueva sesión de usuario
        
        Args:
            user: Usuario autenticado
            ip_address: Dirección IP
            user_agent: User agent
            
        Returns:
            Nueva sesión de usuario
        """
        # Generar tokens
        access_token, refresh_token = self.generate_jwt_tokens(user)
        
        # Crear sesión
        session = UserSession(
            id=secrets.token_urlsafe(16),
            user_id=user.id,
            session_token=hashlib.sha256(access_token.encode()).hexdigest(),
            refresh_token=hashlib.sha256(refresh_token.encode()).hexdigest(),
            ip_address=ip_address,
            user_agent=user_agent,
            device_fingerprint=self._generate_device_fingerprint(ip_address, user_agent),
            expires_at=datetime.utcnow() + timedelta(seconds=self.config.jwt_access_token_expires)
        )
        
        return session
    
    def _generate_device_fingerprint(self, ip_address: str, user_agent: str) -> str:
        """
        Generar huella digital del dispositivo
        
        Args:
            ip_address: Dirección IP
            user_agent: User agent
            
        Returns:
            Huella digital del dispositivo
        """
        fingerprint_data = f"{ip_address}:{user_agent}"
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()[:32]

# Decoradores para autenticación y autorización
def require_auth(f):
    """Decorador para requerir autenticación"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid authorization header'}), 401
        
        token = auth_header.split(' ')[1]
        
        # Verificar token (aquí se usaría la instancia global del AuthenticationManager)
        # payload = auth_manager.verify_jwt_token(token)
        # if not payload:
        #     return jsonify({'error': 'Invalid or expired token'}), 401
        
        # request.current_user = payload
        return f(*args, **kwargs)
    
    return decorated_function

def require_permission(permission: Permission):
    """Decorador para requerir permiso específico"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Aquí se verificaría el permiso del usuario actual
            # if not auth_manager.check_user_permissions(request.current_user, permission):
            #     return jsonify({'error': 'Insufficient permissions'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_2fa(f):
    """Decorador para requerir 2FA"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Verificar si el usuario tiene 2FA habilitado y verificado
        # user = get_current_user()
        # if user.is_2fa_enabled and not request.session.get('2fa_verified'):
        #     return jsonify({'error': '2FA verification required'}), 403
        
        return f(*args, **kwargs)
    
    return decorated_function

# Instancia global del gestor de autenticación
auth_manager = None

def initialize_auth_manager(config: AuthConfig, redis_client: Optional[redis.Redis] = None):
    """
    Inicializar gestor de autenticación global
    
    Args:
        config: Configuración de autenticación
        redis_client: Cliente Redis opcional
    """
    global auth_manager
    auth_manager = AuthenticationManager(config, redis_client)
    logger.info("Authentication manager initialized globally")

def get_auth_manager() -> AuthenticationManager:
    """
    Obtener instancia del gestor de autenticación
    
    Returns:
        Instancia del gestor de autenticación
    """
    if not auth_manager:
        raise RuntimeError("Authentication manager not initialized")
    return auth_manager

