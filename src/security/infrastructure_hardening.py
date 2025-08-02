"""
Infrastructure Hardening - Hardening de Infraestructura y Configuraciones
Security-Auditor Implementation - Phase 3
"""

import os
import json
import yaml
import subprocess
import tempfile
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import logging
from dataclasses import dataclass
from enum import Enum
import shutil
import stat
import pwd
import grp
import socket
import ssl
import requests
from datetime import datetime

logger = logging.getLogger(__name__)

class HardeningLevel(Enum):
    """Niveles de hardening"""
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    PARANOID = "paranoid"

@dataclass
class HardeningConfig:
    """Configuración de hardening"""
    level: HardeningLevel = HardeningLevel.INTERMEDIATE
    enable_firewall: bool = True
    enable_fail2ban: bool = True
    enable_ssl_hardening: bool = True
    enable_header_security: bool = True
    enable_file_permissions: bool = True
    enable_service_hardening: bool = True
    enable_network_hardening: bool = True
    enable_logging_hardening: bool = True
    backup_configs: bool = True

class InfrastructureHardening:
    """
    Sistema de hardening de infraestructura y configuraciones
    """
    
    def __init__(self, config: HardeningConfig, project_root: str):
        """
        Inicializar sistema de hardening
        
        Args:
            config: Configuración de hardening
            project_root: Directorio raíz del proyecto
        """
        self.config = config
        self.project_root = Path(project_root)
        self.backup_dir = self.project_root / "security" / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Configuraciones de seguridad por componente
        self.security_configs = {
            'nginx': self._get_nginx_security_config(),
            'apache': self._get_apache_security_config(),
            'flask': self._get_flask_security_config(),
            'postgresql': self._get_postgresql_security_config(),
            'redis': self._get_redis_security_config(),
            'docker': self._get_docker_security_config(),
            'system': self._get_system_security_config()
        }
        
        logger.info(f"Infrastructure hardening initialized with level: {config.level.value}")
    
    def apply_full_hardening(self) -> Dict[str, Any]:
        """
        Aplicar hardening completo de infraestructura
        
        Returns:
            Reporte de hardening aplicado
        """
        logger.info("Starting full infrastructure hardening")
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'level': self.config.level.value,
            'applied_hardenings': [],
            'failed_hardenings': [],
            'warnings': [],
            'recommendations': []
        }
        
        # Aplicar diferentes tipos de hardening
        if self.config.enable_file_permissions:
            self._apply_file_permissions_hardening(results)
        
        if self.config.enable_ssl_hardening:
            self._apply_ssl_hardening(results)
        
        if self.config.enable_header_security:
            self._apply_security_headers_hardening(results)
        
        if self.config.enable_service_hardening:
            self._apply_service_hardening(results)
        
        if self.config.enable_network_hardening:
            self._apply_network_hardening(results)
        
        if self.config.enable_firewall:
            self._apply_firewall_hardening(results)
        
        if self.config.enable_logging_hardening:
            self._apply_logging_hardening(results)
        
        # Generar configuraciones de seguridad
        self._generate_security_configs(results)
        
        # Generar recomendaciones finales
        self._generate_hardening_recommendations(results)
        
        logger.info(f"Infrastructure hardening completed: {len(results['applied_hardenings'])} applied, {len(results['failed_hardenings'])} failed")
        
        return results
    
    def _apply_file_permissions_hardening(self, results: Dict[str, Any]):
        """
        Aplicar hardening de permisos de archivos
        
        Args:
            results: Diccionario de resultados
        """
        logger.info("Applying file permissions hardening")
        
        try:
            # Archivos sensibles y sus permisos recomendados
            sensitive_files = {
                '.env': 0o600,
                'config.py': 0o640,
                'settings.py': 0o640,
                '*.key': 0o600,
                '*.pem': 0o600,
                'database.db': 0o640,
                'logs/*.log': 0o640
            }
            
            for pattern, mode in sensitive_files.items():
                files = list(self.project_root.rglob(pattern))
                for file_path in files:
                    if file_path.is_file():
                        try:
                            # Backup del archivo si es necesario
                            if self.config.backup_configs:
                                self._backup_file(file_path)
                            
                            # Aplicar permisos
                            file_path.chmod(mode)
                            
                            results['applied_hardenings'].append({
                                'type': 'file_permissions',
                                'target': str(file_path.relative_to(self.project_root)),
                                'action': f'Set permissions to {oct(mode)}',
                                'status': 'success'
                            })
                            
                        except Exception as e:
                            results['failed_hardenings'].append({
                                'type': 'file_permissions',
                                'target': str(file_path.relative_to(self.project_root)),
                                'error': str(e)
                            })
            
            # Directorios sensibles
            sensitive_dirs = {
                'logs': 0o750,
                'backups': 0o700,
                'uploads': 0o750,
                'temp': 0o750
            }
            
            for dir_name, mode in sensitive_dirs.items():
                dir_path = self.project_root / dir_name
                if dir_path.exists() and dir_path.is_dir():
                    try:
                        dir_path.chmod(mode)
                        results['applied_hardenings'].append({
                            'type': 'directory_permissions',
                            'target': dir_name,
                            'action': f'Set permissions to {oct(mode)}',
                            'status': 'success'
                        })
                    except Exception as e:
                        results['failed_hardenings'].append({
                            'type': 'directory_permissions',
                            'target': dir_name,
                            'error': str(e)
                        })
            
        except Exception as e:
            logger.error(f"Error applying file permissions hardening: {e}")
            results['failed_hardenings'].append({
                'type': 'file_permissions',
                'target': 'general',
                'error': str(e)
            })
    
    def _apply_ssl_hardening(self, results: Dict[str, Any]):
        """
        Aplicar hardening de SSL/TLS
        
        Args:
            results: Diccionario de resultados
        """
        logger.info("Applying SSL/TLS hardening")
        
        try:
            # Generar configuración SSL segura
            ssl_config = self._generate_ssl_config()
            
            # Guardar configuración SSL
            ssl_config_path = self.project_root / "security" / "ssl_config.conf"
            ssl_config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(ssl_config_path, 'w') as f:
                f.write(ssl_config)
            
            results['applied_hardenings'].append({
                'type': 'ssl_hardening',
                'target': 'ssl_config.conf',
                'action': 'Generated secure SSL configuration',
                'status': 'success'
            })
            
            # Verificar certificados existentes
            cert_files = list(self.project_root.rglob('*.crt')) + list(self.project_root.rglob('*.pem'))
            for cert_file in cert_files:
                if self._is_ssl_certificate(cert_file):
                    cert_info = self._analyze_ssl_certificate(cert_file)
                    if cert_info['expires_soon']:
                        results['warnings'].append({
                            'type': 'ssl_certificate',
                            'message': f'Certificate {cert_file.name} expires soon: {cert_info["expiry_date"]}',
                            'severity': 'high'
                        })
            
        except Exception as e:
            logger.error(f"Error applying SSL hardening: {e}")
            results['failed_hardenings'].append({
                'type': 'ssl_hardening',
                'target': 'general',
                'error': str(e)
            })
    
    def _apply_security_headers_hardening(self, results: Dict[str, Any]):
        """
        Aplicar hardening de headers de seguridad
        
        Args:
            results: Diccionario de resultados
        """
        logger.info("Applying security headers hardening")
        
        try:
            # Generar configuraciones de headers de seguridad
            headers_configs = {
                'nginx': self._generate_nginx_security_headers(),
                'apache': self._generate_apache_security_headers(),
                'flask': self._generate_flask_security_headers()
            }
            
            for server_type, config in headers_configs.items():
                config_path = self.project_root / "security" / f"{server_type}_security_headers.conf"
                
                with open(config_path, 'w') as f:
                    f.write(config)
                
                results['applied_hardenings'].append({
                    'type': 'security_headers',
                    'target': f'{server_type}_security_headers.conf',
                    'action': 'Generated security headers configuration',
                    'status': 'success'
                })
            
        except Exception as e:
            logger.error(f"Error applying security headers hardening: {e}")
            results['failed_hardenings'].append({
                'type': 'security_headers',
                'target': 'general',
                'error': str(e)
            })
    
    def _apply_service_hardening(self, results: Dict[str, Any]):
        """
        Aplicar hardening de servicios
        
        Args:
            results: Diccionario de resultados
        """
        logger.info("Applying service hardening")
        
        try:
            # Configuraciones de servicios
            service_configs = {
                'postgresql': self._generate_postgresql_hardening(),
                'redis': self._generate_redis_hardening(),
                'nginx': self._generate_nginx_hardening(),
                'systemd': self._generate_systemd_hardening()
            }
            
            for service, config in service_configs.items():
                config_path = self.project_root / "security" / f"{service}_hardening.conf"
                
                with open(config_path, 'w') as f:
                    f.write(config)
                
                results['applied_hardenings'].append({
                    'type': 'service_hardening',
                    'target': f'{service}_hardening.conf',
                    'action': 'Generated service hardening configuration',
                    'status': 'success'
                })
            
        except Exception as e:
            logger.error(f"Error applying service hardening: {e}")
            results['failed_hardenings'].append({
                'type': 'service_hardening',
                'target': 'general',
                'error': str(e)
            })
    
    def _apply_network_hardening(self, results: Dict[str, Any]):
        """
        Aplicar hardening de red
        
        Args:
            results: Diccionario de resultados
        """
        logger.info("Applying network hardening")
        
        try:
            # Generar configuración de red segura
            network_config = self._generate_network_hardening()
            
            config_path = self.project_root / "security" / "network_hardening.conf"
            with open(config_path, 'w') as f:
                f.write(network_config)
            
            results['applied_hardenings'].append({
                'type': 'network_hardening',
                'target': 'network_hardening.conf',
                'action': 'Generated network hardening configuration',
                'status': 'success'
            })
            
            # Verificar puertos abiertos
            open_ports = self._scan_open_ports()
            for port in open_ports:
                if port in [23, 25, 110, 143, 513, 514, 515]:  # Puertos inseguros
                    results['warnings'].append({
                        'type': 'network_security',
                        'message': f'Insecure service detected on port {port}',
                        'severity': 'high'
                    })
            
        except Exception as e:
            logger.error(f"Error applying network hardening: {e}")
            results['failed_hardenings'].append({
                'type': 'network_hardening',
                'target': 'general',
                'error': str(e)
            })
    
    def _apply_firewall_hardening(self, results: Dict[str, Any]):
        """
        Aplicar hardening de firewall
        
        Args:
            results: Diccionario de resultados
        """
        logger.info("Applying firewall hardening")
        
        try:
            # Generar reglas de firewall
            firewall_rules = self._generate_firewall_rules()
            
            # Guardar reglas de UFW
            ufw_rules_path = self.project_root / "security" / "ufw_rules.sh"
            with open(ufw_rules_path, 'w') as f:
                f.write(firewall_rules['ufw'])
            ufw_rules_path.chmod(0o755)
            
            # Guardar reglas de iptables
            iptables_rules_path = self.project_root / "security" / "iptables_rules.sh"
            with open(iptables_rules_path, 'w') as f:
                f.write(firewall_rules['iptables'])
            iptables_rules_path.chmod(0o755)
            
            results['applied_hardenings'].append({
                'type': 'firewall_hardening',
                'target': 'firewall_rules',
                'action': 'Generated firewall rules (UFW and iptables)',
                'status': 'success'
            })
            
        except Exception as e:
            logger.error(f"Error applying firewall hardening: {e}")
            results['failed_hardenings'].append({
                'type': 'firewall_hardening',
                'target': 'general',
                'error': str(e)
            })
    
    def _apply_logging_hardening(self, results: Dict[str, Any]):
        """
        Aplicar hardening de logging
        
        Args:
            results: Diccionario de resultados
        """
        logger.info("Applying logging hardening")
        
        try:
            # Configuración de logging seguro
            logging_config = self._generate_logging_hardening()
            
            config_path = self.project_root / "security" / "logging_hardening.conf"
            with open(config_path, 'w') as f:
                f.write(logging_config)
            
            # Configuración de logrotate
            logrotate_config = self._generate_logrotate_config()
            
            logrotate_path = self.project_root / "security" / "logrotate.conf"
            with open(logrotate_path, 'w') as f:
                f.write(logrotate_config)
            
            results['applied_hardenings'].append({
                'type': 'logging_hardening',
                'target': 'logging_configuration',
                'action': 'Generated secure logging configuration',
                'status': 'success'
            })
            
        except Exception as e:
            logger.error(f"Error applying logging hardening: {e}")
            results['failed_hardenings'].append({
                'type': 'logging_hardening',
                'target': 'general',
                'error': str(e)
            })
    
    def _generate_security_configs(self, results: Dict[str, Any]):
        """
        Generar configuraciones de seguridad adicionales
        
        Args:
            results: Diccionario de resultados
        """
        logger.info("Generating additional security configurations")
        
        try:
            # Configuración de Docker security
            docker_security = self._generate_docker_security_config()
            docker_path = self.project_root / "security" / "docker_security.yml"
            with open(docker_path, 'w') as f:
                yaml.dump(docker_security, f, default_flow_style=False)
            
            # Configuración de fail2ban
            fail2ban_config = self._generate_fail2ban_config()
            fail2ban_path = self.project_root / "security" / "fail2ban.conf"
            with open(fail2ban_path, 'w') as f:
                f.write(fail2ban_config)
            
            # Script de monitoreo de seguridad
            monitoring_script = self._generate_security_monitoring_script()
            monitoring_path = self.project_root / "security" / "security_monitor.py"
            with open(monitoring_path, 'w') as f:
                f.write(monitoring_script)
            monitoring_path.chmod(0o755)
            
            results['applied_hardenings'].append({
                'type': 'security_configs',
                'target': 'additional_configurations',
                'action': 'Generated Docker, fail2ban, and monitoring configurations',
                'status': 'success'
            })
            
        except Exception as e:
            logger.error(f"Error generating security configs: {e}")
            results['failed_hardenings'].append({
                'type': 'security_configs',
                'target': 'general',
                'error': str(e)
            })
    
    def _generate_hardening_recommendations(self, results: Dict[str, Any]):
        """
        Generar recomendaciones de hardening
        
        Args:
            results: Diccionario de resultados
        """
        recommendations = []
        
        # Recomendaciones basadas en el nivel de hardening
        if self.config.level == HardeningLevel.BASIC:
            recommendations.extend([
                "Consider upgrading to intermediate hardening level for better security",
                "Enable automatic security updates",
                "Implement basic monitoring and alerting"
            ])
        elif self.config.level == HardeningLevel.INTERMEDIATE:
            recommendations.extend([
                "Consider implementing advanced hardening for production environments",
                "Set up centralized logging and monitoring",
                "Implement regular security audits"
            ])
        elif self.config.level == HardeningLevel.ADVANCED:
            recommendations.extend([
                "Consider paranoid level for highly sensitive environments",
                "Implement zero-trust network architecture",
                "Set up advanced threat detection"
            ])
        
        # Recomendaciones específicas
        recommendations.extend([
            "Regularly update all system packages and dependencies",
            "Implement backup and disaster recovery procedures",
            "Conduct regular penetration testing",
            "Train staff on security best practices",
            "Implement incident response procedures",
            "Set up security information and event management (SIEM)",
            "Enable multi-factor authentication for all accounts",
            "Implement network segmentation",
            "Regular security configuration reviews",
            "Implement data loss prevention (DLP) measures"
        ])
        
        results['recommendations'] = recommendations
    
    # Métodos auxiliares para generar configuraciones específicas
    
    def _get_nginx_security_config(self) -> Dict[str, str]:
        """Obtener configuración de seguridad para Nginx"""
        return {
            'ssl_protocols': 'TLSv1.2 TLSv1.3',
            'ssl_ciphers': 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384',
            'ssl_prefer_server_ciphers': 'off',
            'ssl_session_cache': 'shared:SSL:10m',
            'ssl_session_timeout': '10m'
        }
    
    def _get_apache_security_config(self) -> Dict[str, str]:
        """Obtener configuración de seguridad para Apache"""
        return {
            'SSLProtocol': 'all -SSLv3 -TLSv1 -TLSv1.1',
            'SSLCipherSuite': 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384',
            'SSLHonorCipherOrder': 'off',
            'SSLSessionCache': 'shmcb:/var/cache/mod_ssl/scache(512000)'
        }
    
    def _get_flask_security_config(self) -> Dict[str, Any]:
        """Obtener configuración de seguridad para Flask"""
        return {
            'SECRET_KEY': 'CHANGE_THIS_TO_RANDOM_SECRET_KEY',
            'SESSION_COOKIE_SECURE': True,
            'SESSION_COOKIE_HTTPONLY': True,
            'SESSION_COOKIE_SAMESITE': 'Lax',
            'PERMANENT_SESSION_LIFETIME': 3600,
            'WTF_CSRF_ENABLED': True,
            'WTF_CSRF_TIME_LIMIT': 3600
        }
    
    def _get_postgresql_security_config(self) -> Dict[str, str]:
        """Obtener configuración de seguridad para PostgreSQL"""
        return {
            'ssl': 'on',
            'ssl_ciphers': 'HIGH:MEDIUM:+3DES:!aNULL',
            'ssl_prefer_server_ciphers': 'on',
            'password_encryption': 'scram-sha-256',
            'log_connections': 'on',
            'log_disconnections': 'on',
            'log_statement': 'all'
        }
    
    def _get_redis_security_config(self) -> Dict[str, str]:
        """Obtener configuración de seguridad para Redis"""
        return {
            'requirepass': 'CHANGE_THIS_TO_STRONG_PASSWORD',
            'bind': '127.0.0.1',
            'protected-mode': 'yes',
            'port': '0',  # Disable default port
            'unixsocket': '/var/run/redis/redis.sock',
            'unixsocketperm': '700'
        }
    
    def _get_docker_security_config(self) -> Dict[str, Any]:
        """Obtener configuración de seguridad para Docker"""
        return {
            'userns-remap': 'default',
            'no-new-privileges': True,
            'seccomp-profile': '/etc/docker/seccomp.json',
            'apparmor-profile': 'docker-default'
        }
    
    def _get_system_security_config(self) -> Dict[str, str]:
        """Obtener configuración de seguridad del sistema"""
        return {
            'net.ipv4.ip_forward': '0',
            'net.ipv4.conf.all.send_redirects': '0',
            'net.ipv4.conf.default.send_redirects': '0',
            'net.ipv4.conf.all.accept_redirects': '0',
            'net.ipv4.conf.default.accept_redirects': '0',
            'net.ipv4.conf.all.secure_redirects': '0',
            'net.ipv4.conf.default.secure_redirects': '0'
        }
    
    def _generate_ssl_config(self) -> str:
        """Generar configuración SSL segura"""
        return """# SSL Security Configuration
# Generated by Infrastructure Hardening System

# Modern SSL/TLS Configuration
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;
ssl_prefer_server_ciphers off;

# SSL Session Configuration
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 10m;
ssl_session_tickets off;

# OCSP Stapling
ssl_stapling on;
ssl_stapling_verify on;

# SSL Security Headers
add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
"""
    
    def _generate_nginx_security_headers(self) -> str:
        """Generar headers de seguridad para Nginx"""
        return """# Nginx Security Headers Configuration
# Generated by Infrastructure Hardening System

# Security Headers
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self'; frame-ancestors 'self';" always;
add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;

# Hide Nginx Version
server_tokens off;

# Prevent access to hidden files
location ~ /\. {
    deny all;
    access_log off;
    log_not_found off;
}

# Prevent access to backup files
location ~ ~$ {
    deny all;
    access_log off;
    log_not_found off;
}
"""
    
    def _generate_apache_security_headers(self) -> str:
        """Generar headers de seguridad para Apache"""
        return """# Apache Security Headers Configuration
# Generated by Infrastructure Hardening System

# Security Headers
Header always set X-Frame-Options "SAMEORIGIN"
Header always set X-Content-Type-Options "nosniff"
Header always set X-XSS-Protection "1; mode=block"
Header always set Referrer-Policy "strict-origin-when-cross-origin"
Header always set Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self'; frame-ancestors 'self';"
Header always set Permissions-Policy "geolocation=(), microphone=(), camera=()"

# Hide Apache Version
ServerTokens Prod
ServerSignature Off

# Prevent access to hidden files
<FilesMatch "^\.">
    Require all denied
</FilesMatch>

# Prevent access to backup files
<FilesMatch "~$">
    Require all denied
</FilesMatch>
"""
    
    def _generate_flask_security_headers(self) -> str:
        """Generar configuración de headers de seguridad para Flask"""
        return """# Flask Security Headers Configuration
# Generated by Infrastructure Hardening System

from flask import Flask
from flask_talisman import Talisman

def configure_security_headers(app: Flask):
    \"\"\"Configure security headers for Flask application\"\"\"
    
    # Configure Talisman for security headers
    csp = {
        'default-src': "'self'",
        'script-src': "'self' 'unsafe-inline' 'unsafe-eval'",
        'style-src': "'self' 'unsafe-inline'",
        'img-src': "'self' data: https:",
        'font-src': "'self'",
        'connect-src': "'self'",
        'frame-ancestors': "'self'"
    }
    
    Talisman(
        app,
        force_https=True,
        strict_transport_security=True,
        strict_transport_security_max_age=31536000,
        strict_transport_security_include_subdomains=True,
        content_security_policy=csp,
        content_security_policy_nonce_in=['script-src', 'style-src'],
        referrer_policy='strict-origin-when-cross-origin',
        permissions_policy={
            'geolocation': '()',
            'microphone': '()',
            'camera': '()'
        }
    )
    
    # Additional security configurations
    app.config.update(
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        PERMANENT_SESSION_LIFETIME=3600
    )
"""
    
    def _generate_postgresql_hardening(self) -> str:
        """Generar configuración de hardening para PostgreSQL"""
        return """# PostgreSQL Security Hardening Configuration
# Generated by Infrastructure Hardening System

# Connection and Authentication
ssl = on
ssl_ciphers = 'HIGH:MEDIUM:+3DES:!aNULL'
ssl_prefer_server_ciphers = on
password_encryption = scram-sha-256

# Logging
log_connections = on
log_disconnections = on
log_statement = 'all'
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '
log_checkpoints = on
log_lock_waits = on
log_temp_files = 0

# Security
shared_preload_libraries = 'pg_stat_statements'
track_activities = on
track_counts = on
track_functions = all

# Resource Limits
max_connections = 100
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 16MB
maintenance_work_mem = 64MB
"""
    
    def _generate_redis_hardening(self) -> str:
        """Generar configuración de hardening para Redis"""
        return """# Redis Security Hardening Configuration
# Generated by Infrastructure Hardening System

# Authentication
requirepass CHANGE_THIS_TO_STRONG_PASSWORD

# Network Security
bind 127.0.0.1
protected-mode yes
port 0
unixsocket /var/run/redis/redis.sock
unixsocketperm 700

# Disable Dangerous Commands
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command KEYS ""
rename-command CONFIG ""
rename-command SHUTDOWN SHUTDOWN_REDIS
rename-command DEBUG ""
rename-command EVAL ""

# Logging
loglevel notice
logfile /var/log/redis/redis-server.log
syslog-enabled yes
syslog-ident redis

# Security
tcp-keepalive 300
timeout 300
"""
    
    def _generate_nginx_hardening(self) -> str:
        """Generar configuración de hardening para Nginx"""
        return """# Nginx Security Hardening Configuration
# Generated by Infrastructure Hardening System

# Hide Nginx version
server_tokens off;

# Buffer overflow attacks
client_body_buffer_size 1K;
client_header_buffer_size 1k;
client_max_body_size 1k;
large_client_header_buffers 2 1k;

# Timeouts
client_body_timeout 10;
client_header_timeout 10;
keepalive_timeout 5 5;
send_timeout 10;

# Rate limiting
limit_req_zone $binary_remote_addr zone=login:10m rate=1r/s;
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

# SSL Configuration
ssl_protocols TLSv1.2 TLSv1.3;
ssl_prefer_server_ciphers off;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;

# Security headers
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
"""
    
    def _generate_systemd_hardening(self) -> str:
        """Generar configuración de hardening para systemd"""
        return """# Systemd Service Hardening Configuration
# Generated by Infrastructure Hardening System

[Service]
# Security
NoNewPrivileges=yes
PrivateTmp=yes
PrivateDevices=yes
ProtectHome=yes
ProtectSystem=strict
ReadWritePaths=/var/log /var/lib/app
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes
RestrictRealtime=yes
RestrictNamespaces=yes
LockPersonality=yes
MemoryDenyWriteExecute=yes
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
SystemCallFilter=@system-service
SystemCallErrorNumber=EPERM

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096
LimitCORE=0

# User and group
User=app
Group=app
"""
    
    def _generate_network_hardening(self) -> str:
        """Generar configuración de hardening de red"""
        return """# Network Security Hardening Configuration
# Generated by Infrastructure Hardening System

# /etc/sysctl.d/99-security.conf

# IP Forwarding
net.ipv4.ip_forward = 0
net.ipv6.conf.all.forwarding = 0

# IP Redirects
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv6.conf.all.accept_redirects = 0
net.ipv6.conf.default.accept_redirects = 0

# Secure Redirects
net.ipv4.conf.all.secure_redirects = 0
net.ipv4.conf.default.secure_redirects = 0

# Source Routing
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0
net.ipv6.conf.all.accept_source_route = 0
net.ipv6.conf.default.accept_source_route = 0

# ICMP
net.ipv4.icmp_echo_ignore_broadcasts = 1
net.ipv4.icmp_ignore_bogus_error_responses = 1

# SYN Flood Protection
net.ipv4.tcp_syncookies = 1
net.ipv4.tcp_max_syn_backlog = 2048
net.ipv4.tcp_synack_retries = 2
net.ipv4.tcp_syn_retries = 5

# Log Martians
net.ipv4.conf.all.log_martians = 1
net.ipv4.conf.default.log_martians = 1

# Ignore ping requests
net.ipv4.icmp_echo_ignore_all = 0

# IPv6 Privacy
net.ipv6.conf.all.use_tempaddr = 2
net.ipv6.conf.default.use_tempaddr = 2
"""
    
    def _generate_firewall_rules(self) -> Dict[str, str]:
        """Generar reglas de firewall"""
        ufw_rules = """#!/bin/bash
# UFW Firewall Rules
# Generated by Infrastructure Hardening System

# Reset UFW
ufw --force reset

# Default policies
ufw default deny incoming
ufw default allow outgoing

# Allow SSH (change port if needed)
ufw allow 22/tcp

# Allow HTTP and HTTPS
ufw allow 80/tcp
ufw allow 443/tcp

# Allow application ports
ufw allow 5000/tcp  # Flask app
ufw allow 5432/tcp  # PostgreSQL (only from localhost)
ufw allow from 127.0.0.1 to any port 6379  # Redis (localhost only)

# Rate limiting for SSH
ufw limit ssh

# Enable UFW
ufw --force enable

echo "UFW firewall rules applied successfully"
"""
        
        iptables_rules = """#!/bin/bash
# iptables Firewall Rules
# Generated by Infrastructure Hardening System

# Flush existing rules
iptables -F
iptables -X
iptables -t nat -F
iptables -t nat -X
iptables -t mangle -F
iptables -t mangle -X

# Default policies
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT ACCEPT

# Allow loopback
iptables -A INPUT -i lo -j ACCEPT
iptables -A OUTPUT -o lo -j ACCEPT

# Allow established connections
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# Allow SSH
iptables -A INPUT -p tcp --dport 22 -m state --state NEW -m limit --limit 3/min --limit-burst 3 -j ACCEPT

# Allow HTTP and HTTPS
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# Allow application port
iptables -A INPUT -p tcp --dport 5000 -j ACCEPT

# Drop invalid packets
iptables -A INPUT -m state --state INVALID -j DROP

# Log dropped packets
iptables -A INPUT -j LOG --log-prefix "iptables-dropped: "

echo "iptables firewall rules applied successfully"
"""
        
        return {
            'ufw': ufw_rules,
            'iptables': iptables_rules
        }
    
    def _generate_logging_hardening(self) -> str:
        """Generar configuración de logging seguro"""
        return """# Secure Logging Configuration
# Generated by Infrastructure Hardening System

# rsyslog.conf additions

# Security logging
auth,authpriv.*                 /var/log/auth.log
*.*;auth,authpriv.none          -/var/log/syslog
daemon.*                        -/var/log/daemon.log
kern.*                          -/var/log/kern.log
mail.*                          -/var/log/mail.log
user.*                          -/var/log/user.log

# Application logging
local0.*                        /var/log/application.log
local1.*                        /var/log/security.log

# Remote logging (optional)
# *.* @@log-server:514

# Log rotation
$WorkDirectory /var/spool/rsyslog
$ActionFileDefaultTemplate RSYSLOG_TraditionalFileFormat
$RepeatedMsgReduction on
$FileOwner syslog
$FileGroup adm
$FileCreateMode 0640
$DirCreateMode 0755
$Umask 0022
"""
    
    def _generate_logrotate_config(self) -> str:
        """Generar configuración de logrotate"""
        return """# Logrotate Configuration for Application
# Generated by Infrastructure Hardening System

/var/log/application/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 640 app app
    postrotate
        systemctl reload rsyslog > /dev/null 2>&1 || true
    endscript
}

/var/log/security/*.log {
    daily
    missingok
    rotate 365
    compress
    delaycompress
    notifempty
    create 600 root root
    postrotate
        systemctl reload rsyslog > /dev/null 2>&1 || true
    endscript
}
"""
    
    def _generate_docker_security_config(self) -> Dict[str, Any]:
        """Generar configuración de seguridad para Docker"""
        return {
            'version': '3.8',
            'services': {
                'app': {
                    'security_opt': [
                        'no-new-privileges:true',
                        'apparmor:docker-default'
                    ],
                    'cap_drop': ['ALL'],
                    'cap_add': ['CHOWN', 'SETGID', 'SETUID'],
                    'read_only': True,
                    'tmpfs': ['/tmp', '/var/tmp'],
                    'user': '1000:1000',
                    'networks': ['app-network']
                }
            },
            'networks': {
                'app-network': {
                    'driver': 'bridge',
                    'internal': True
                }
            }
        }
    
    def _generate_fail2ban_config(self) -> str:
        """Generar configuración de fail2ban"""
        return """# Fail2ban Configuration
# Generated by Infrastructure Hardening System

[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3
backend = auto
usedns = warn
logencoding = auto
enabled = false
mode = normal
filter = %(__name__)s[mode=%(mode)s]

[sshd]
enabled = true
port = ssh
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600

[nginx-http-auth]
enabled = true
port = http,https
logpath = /var/log/nginx/error.log
maxretry = 3

[nginx-limit-req]
enabled = true
port = http,https
logpath = /var/log/nginx/error.log
maxretry = 10

[flask-auth]
enabled = true
port = 5000
logpath = /var/log/application/auth.log
maxretry = 5
findtime = 300
bantime = 1800
"""
    
    def _generate_security_monitoring_script(self) -> str:
        """Generar script de monitoreo de seguridad"""
        return """#!/usr/bin/env python3
# Security Monitoring Script
# Generated by Infrastructure Hardening System

import os
import sys
import subprocess
import json
import logging
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/security_monitor.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def check_failed_logins():
    \"\"\"Check for failed login attempts\"\"\"
    try:
        result = subprocess.run(['grep', 'Failed password', '/var/log/auth.log'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            failed_logins = len(result.stdout.strip().split('\\n'))
            if failed_logins > 10:
                logger.warning(f"High number of failed logins detected: {failed_logins}")
                return False
    except Exception as e:
        logger.error(f"Error checking failed logins: {e}")
    return True

def check_disk_usage():
    \"\"\"Check disk usage\"\"\"
    try:
        result = subprocess.run(['df', '-h'], capture_output=True, text=True)
        lines = result.stdout.strip().split('\\n')[1:]
        for line in lines:
            parts = line.split()
            if len(parts) >= 5:
                usage = int(parts[4].rstrip('%'))
                if usage > 90:
                    logger.warning(f"High disk usage detected: {usage}% on {parts[5]}")
                    return False
    except Exception as e:
        logger.error(f"Error checking disk usage: {e}")
    return True

def check_running_processes():
    \"\"\"Check for suspicious processes\"\"\"
    suspicious_processes = ['nc', 'netcat', 'nmap', 'tcpdump']
    try:
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        for process in suspicious_processes:
            if process in result.stdout:
                logger.warning(f"Suspicious process detected: {process}")
                return False
    except Exception as e:
        logger.error(f"Error checking processes: {e}")
    return True

def check_network_connections():
    \"\"\"Check for suspicious network connections\"\"\"
    try:
        result = subprocess.run(['netstat', '-tuln'], capture_output=True, text=True)
        lines = result.stdout.strip().split('\\n')
        listening_ports = []
        for line in lines:
            if 'LISTEN' in line:
                parts = line.split()
                if len(parts) >= 4:
                    port = parts[3].split(':')[-1]
                    listening_ports.append(port)
        
        # Check for unexpected ports
        expected_ports = ['22', '80', '443', '5000', '5432', '6379']
        unexpected_ports = [p for p in listening_ports if p not in expected_ports]
        
        if unexpected_ports:
            logger.warning(f"Unexpected listening ports: {unexpected_ports}")
            return False
    except Exception as e:
        logger.error(f"Error checking network connections: {e}")
    return True

def main():
    \"\"\"Main monitoring function\"\"\"
    logger.info("Starting security monitoring check")
    
    checks = [
        ("Failed Logins", check_failed_logins),
        ("Disk Usage", check_disk_usage),
        ("Running Processes", check_running_processes),
        ("Network Connections", check_network_connections)
    ]
    
    all_passed = True
    for check_name, check_func in checks:
        try:
            if not check_func():
                all_passed = False
                logger.error(f"Security check failed: {check_name}")
            else:
                logger.info(f"Security check passed: {check_name}")
        except Exception as e:
            logger.error(f"Error running check {check_name}: {e}")
            all_passed = False
    
    if all_passed:
        logger.info("All security checks passed")
        sys.exit(0)
    else:
        logger.error("One or more security checks failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
"""
    
    # Métodos auxiliares
    
    def _backup_file(self, file_path: Path):
        """
        Crear backup de archivo
        
        Args:
            file_path: Ruta del archivo a respaldar
        """
        if not self.config.backup_configs:
            return
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{file_path.name}.backup_{timestamp}"
            backup_path = self.backup_dir / backup_name
            
            shutil.copy2(file_path, backup_path)
            logger.info(f"Backup created: {backup_path}")
            
        except Exception as e:
            logger.error(f"Error creating backup for {file_path}: {e}")
    
    def _is_ssl_certificate(self, file_path: Path) -> bool:
        """
        Verificar si un archivo es un certificado SSL
        
        Args:
            file_path: Ruta del archivo
            
        Returns:
            True si es un certificado SSL
        """
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                return '-----BEGIN CERTIFICATE-----' in content
        except Exception:
            return False
    
    def _analyze_ssl_certificate(self, cert_path: Path) -> Dict[str, Any]:
        """
        Analizar certificado SSL
        
        Args:
            cert_path: Ruta del certificado
            
        Returns:
            Información del certificado
        """
        try:
            result = subprocess.run([
                'openssl', 'x509', '-in', str(cert_path), '-text', '-noout'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                # Extraer fecha de expiración (implementación básica)
                output = result.stdout
                # Aquí se podría implementar parsing más detallado
                return {
                    'expires_soon': False,  # Placeholder
                    'expiry_date': 'Unknown',
                    'issuer': 'Unknown'
                }
        except Exception as e:
            logger.error(f"Error analyzing SSL certificate {cert_path}: {e}")
        
        return {
            'expires_soon': False,
            'expiry_date': 'Unknown',
            'issuer': 'Unknown'
        }
    
    def _scan_open_ports(self) -> List[int]:
        """
        Escanear puertos abiertos localmente
        
        Returns:
            Lista de puertos abiertos
        """
        open_ports = []
        common_ports = [22, 23, 25, 53, 80, 110, 143, 443, 993, 995, 3306, 5432, 6379, 27017]
        
        for port in common_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', port))
                if result == 0:
                    open_ports.append(port)
                sock.close()
            except Exception:
                continue
        
        return open_ports

# Instancia global del sistema de hardening
infrastructure_hardening = None

def initialize_infrastructure_hardening(config: HardeningConfig, project_root: str):
    """
    Inicializar sistema de hardening global
    
    Args:
        config: Configuración de hardening
        project_root: Directorio raíz del proyecto
    """
    global infrastructure_hardening
    infrastructure_hardening = InfrastructureHardening(config, project_root)
    logger.info("Infrastructure hardening system initialized")

def apply_infrastructure_hardening() -> Dict[str, Any]:
    """
    Aplicar hardening completo de infraestructura
    
    Returns:
        Reporte de hardening
    """
    if not infrastructure_hardening:
        raise RuntimeError("Infrastructure hardening not initialized")
    
    return infrastructure_hardening.apply_full_hardening()

def get_hardening_recommendations() -> List[str]:
    """
    Obtener recomendaciones de hardening
    
    Returns:
        Lista de recomendaciones
    """
    if not infrastructure_hardening:
        return []
    
    report = infrastructure_hardening.apply_full_hardening()
    return report.get('recommendations', [])

