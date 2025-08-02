"""
Security Auditor - Auditoría Completa de Seguridad
Security-Auditor Implementation
"""

import os
import re
import json
import hashlib
import secrets
import subprocess
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import socket
import ssl
import requests
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class VulnerabilityLevel(Enum):
    """Niveles de severidad de vulnerabilidades"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

@dataclass
class SecurityFinding:
    """Hallazgo de seguridad"""
    id: str
    title: str
    description: str
    level: VulnerabilityLevel
    category: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    recommendation: str = ""
    cve_references: List[str] = None
    remediation_effort: str = "medium"

class SecurityAuditor:
    """
    Auditor de seguridad completo para análisis de vulnerabilidades
    """
    
    def __init__(self, project_root: str):
        """
        Inicializar auditor de seguridad
        
        Args:
            project_root: Directorio raíz del proyecto
        """
        self.project_root = Path(project_root)
        self.findings: List[SecurityFinding] = []
        self.scan_timestamp = datetime.now()
        
        # Patrones de vulnerabilidades comunes
        self.vulnerability_patterns = {
            'sql_injection': [
                r'execute\s*\(\s*["\'].*%.*["\']',
                r'cursor\.execute\s*\(\s*["\'].*\+.*["\']',
                r'query\s*=\s*["\'].*%.*["\']',
                r'SELECT.*\+.*FROM',
                r'INSERT.*\+.*VALUES'
            ],
            'xss': [
                r'innerHTML\s*=\s*.*\+',
                r'document\.write\s*\(\s*.*\+',
                r'eval\s*\(\s*.*\+',
                r'setTimeout\s*\(\s*.*\+',
                r'setInterval\s*\(\s*.*\+'
            ],
            'hardcoded_secrets': [
                r'password\s*=\s*["\'][^"\']{8,}["\']',
                r'api_key\s*=\s*["\'][^"\']{20,}["\']',
                r'secret\s*=\s*["\'][^"\']{16,}["\']',
                r'token\s*=\s*["\'][^"\']{20,}["\']',
                r'private_key\s*=\s*["\'].*["\']'
            ],
            'insecure_random': [
                r'random\.random\(\)',
                r'Math\.random\(\)',
                r'rand\(\)',
                r'srand\('
            ],
            'path_traversal': [
                r'open\s*\(\s*.*\+.*\)',
                r'file\s*\(\s*.*\+.*\)',
                r'include\s*\(\s*.*\+.*\)',
                r'require\s*\(\s*.*\+.*\)'
            ],
            'command_injection': [
                r'os\.system\s*\(\s*.*\+',
                r'subprocess\.\w+\s*\(\s*.*\+',
                r'exec\s*\(\s*.*\+',
                r'eval\s*\(\s*.*\+'
            ]
        }
        
        # Configuraciones inseguras
        self.insecure_configs = {
            'flask_debug': r'debug\s*=\s*True',
            'flask_secret_weak': r'SECRET_KEY\s*=\s*["\'][^"\']{1,16}["\']',
            'cors_wildcard': r'CORS.*\*',
            'ssl_verify_false': r'verify\s*=\s*False',
            'trust_all_certs': r'ssl\._create_unverified_context'
        }
        
        logger.info(f"Security auditor initialized for {project_root}")
    
    def run_full_audit(self) -> Dict[str, Any]:
        """
        Ejecutar auditoría completa de seguridad
        
        Returns:
            Reporte completo de auditoría
        """
        logger.info("Starting comprehensive security audit")
        
        # Limpiar hallazgos anteriores
        self.findings = []
        
        # Ejecutar diferentes tipos de análisis
        self._scan_code_vulnerabilities()
        self._scan_dependencies()
        self._scan_configurations()
        self._scan_network_security()
        self._scan_authentication()
        self._scan_data_protection()
        self._scan_infrastructure()
        
        # Generar reporte
        report = self._generate_security_report()
        
        logger.info(f"Security audit completed: {len(self.findings)} findings")
        
        return report
    
    def _scan_code_vulnerabilities(self):
        """
        Escanear vulnerabilidades en el código fuente
        """
        logger.info("Scanning code vulnerabilities")
        
        # Archivos a escanear
        code_files = []
        for ext in ['.py', '.js', '.jsx', '.ts', '.tsx', '.html', '.php']:
            code_files.extend(self.project_root.rglob(f'*{ext}'))
        
        for file_path in code_files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    self._analyze_file_content(file_path, content)
            except Exception as e:
                logger.error(f"Error scanning file {file_path}: {e}")
    
    def _analyze_file_content(self, file_path: Path, content: str):
        """
        Analizar contenido de archivo en busca de vulnerabilidades
        
        Args:
            file_path: Ruta del archivo
            content: Contenido del archivo
        """
        lines = content.split('\n')
        
        for category, patterns in self.vulnerability_patterns.items():
            for pattern in patterns:
                for line_num, line in enumerate(lines, 1):
                    if re.search(pattern, line, re.IGNORECASE):
                        self._add_finding(
                            id=f"code_{category}_{hashlib.md5(f'{file_path}_{line_num}'.encode()).hexdigest()[:8]}",
                            title=f"Potential {category.replace('_', ' ').title()} Vulnerability",
                            description=f"Detected potential {category} pattern in code: {line.strip()}",
                            level=self._get_vulnerability_level(category),
                            category="Code Security",
                            file_path=str(file_path.relative_to(self.project_root)),
                            line_number=line_num,
                            recommendation=self._get_recommendation(category)
                        )
        
        # Escanear configuraciones inseguras
        for config_type, pattern in self.insecure_configs.items():
            for line_num, line in enumerate(lines, 1):
                if re.search(pattern, line, re.IGNORECASE):
                    self._add_finding(
                        id=f"config_{config_type}_{hashlib.md5(f'{file_path}_{line_num}'.encode()).hexdigest()[:8]}",
                        title=f"Insecure Configuration: {config_type.replace('_', ' ').title()}",
                        description=f"Insecure configuration detected: {line.strip()}",
                        level=VulnerabilityLevel.HIGH,
                        category="Configuration Security",
                        file_path=str(file_path.relative_to(self.project_root)),
                        line_number=line_num,
                        recommendation=self._get_config_recommendation(config_type)
                    )
    
    def _scan_dependencies(self):
        """
        Escanear vulnerabilidades en dependencias
        """
        logger.info("Scanning dependency vulnerabilities")
        
        # Escanear requirements.txt
        requirements_file = self.project_root / "requirements.txt"
        if requirements_file.exists():
            self._scan_python_dependencies(requirements_file)
        
        # Escanear package.json
        package_json = self.project_root / "package.json"
        if package_json.exists():
            self._scan_npm_dependencies(package_json)
    
    def _scan_python_dependencies(self, requirements_file: Path):
        """
        Escanear dependencias de Python
        
        Args:
            requirements_file: Archivo requirements.txt
        """
        try:
            # Usar safety para escanear vulnerabilidades conocidas
            result = subprocess.run([
                'safety', 'check', '--file', str(requirements_file), '--json'
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                vulnerabilities = json.loads(result.stdout)
                for vuln in vulnerabilities:
                    self._add_finding(
                        id=f"dep_python_{vuln.get('id', 'unknown')}",
                        title=f"Vulnerable Python Package: {vuln.get('package', 'unknown')}",
                        description=vuln.get('advisory', 'Known vulnerability in dependency'),
                        level=VulnerabilityLevel.HIGH,
                        category="Dependency Security",
                        recommendation=f"Update {vuln.get('package')} to version {vuln.get('safe_versions', 'latest')}",
                        cve_references=vuln.get('cve', [])
                    )
            
        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            # Análisis manual básico
            with open(requirements_file, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if '==' in line:
                            package, version = line.split('==', 1)
                            if self._is_outdated_package(package.strip(), version.strip()):
                                self._add_finding(
                                    id=f"dep_outdated_{package.strip()}",
                                    title=f"Potentially Outdated Package: {package.strip()}",
                                    description=f"Package {package.strip()} version {version.strip()} may be outdated",
                                    level=VulnerabilityLevel.MEDIUM,
                                    category="Dependency Security",
                                    recommendation=f"Review and update {package.strip()} to latest secure version"
                                )
    
    def _scan_npm_dependencies(self, package_json: Path):
        """
        Escanear dependencias de NPM
        
        Args:
            package_json: Archivo package.json
        """
        try:
            # Usar npm audit
            result = subprocess.run([
                'npm', 'audit', '--json'
            ], cwd=package_json.parent, capture_output=True, text=True, timeout=60)
            
            if result.stdout:
                audit_data = json.loads(result.stdout)
                vulnerabilities = audit_data.get('vulnerabilities', {})
                
                for package, vuln_data in vulnerabilities.items():
                    severity = vuln_data.get('severity', 'medium')
                    self._add_finding(
                        id=f"dep_npm_{package}",
                        title=f"Vulnerable NPM Package: {package}",
                        description=vuln_data.get('title', 'Known vulnerability in NPM dependency'),
                        level=self._map_npm_severity(severity),
                        category="Dependency Security",
                        recommendation=f"Update {package} to fix vulnerability",
                        cve_references=vuln_data.get('cves', [])
                    )
            
        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            logger.warning("Could not run npm audit, skipping NPM dependency scan")
    
    def _scan_configurations(self):
        """
        Escanear configuraciones de seguridad
        """
        logger.info("Scanning security configurations")
        
        # Verificar archivos de configuración
        config_files = [
            'config.py', 'settings.py', '.env', 'docker-compose.yml',
            'nginx.conf', 'apache.conf', '.htaccess'
        ]
        
        for config_file in config_files:
            file_path = self.project_root / config_file
            if file_path.exists():
                self._analyze_config_file(file_path)
        
        # Verificar permisos de archivos
        self._check_file_permissions()
    
    def _analyze_config_file(self, file_path: Path):
        """
        Analizar archivo de configuración
        
        Args:
            file_path: Ruta del archivo de configuración
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Buscar configuraciones inseguras específicas
            insecure_patterns = {
                'debug_enabled': r'DEBUG\s*=\s*True',
                'weak_secret': r'SECRET_KEY\s*=\s*["\'][^"\']{1,16}["\']',
                'default_passwords': r'password\s*[:=]\s*["\']?(admin|password|123456|root)["\']?',
                'insecure_ssl': r'ssl_verify\s*[:=]\s*false',
                'permissive_cors': r'Access-Control-Allow-Origin\s*:\s*\*'
            }
            
            for pattern_name, pattern in insecure_patterns.items():
                if re.search(pattern, content, re.IGNORECASE):
                    self._add_finding(
                        id=f"config_{pattern_name}_{file_path.name}",
                        title=f"Insecure Configuration: {pattern_name.replace('_', ' ').title()}",
                        description=f"Insecure configuration found in {file_path.name}",
                        level=VulnerabilityLevel.HIGH,
                        category="Configuration Security",
                        file_path=str(file_path.relative_to(self.project_root)),
                        recommendation=self._get_config_recommendation(pattern_name)
                    )
            
        except Exception as e:
            logger.error(f"Error analyzing config file {file_path}: {e}")
    
    def _check_file_permissions(self):
        """
        Verificar permisos de archivos sensibles
        """
        sensitive_files = [
            '.env', 'config.py', 'settings.py', 'private_key.pem',
            'id_rsa', 'database.db', '*.key', '*.pem'
        ]
        
        for pattern in sensitive_files:
            for file_path in self.project_root.rglob(pattern):
                if file_path.is_file():
                    try:
                        stat = file_path.stat()
                        mode = oct(stat.st_mode)[-3:]
                        
                        # Verificar si el archivo es legible por otros
                        if int(mode[2]) >= 4:  # Otros tienen permisos de lectura
                            self._add_finding(
                                id=f"perm_{file_path.name}",
                                title=f"Insecure File Permissions: {file_path.name}",
                                description=f"Sensitive file {file_path.name} has overly permissive permissions ({mode})",
                                level=VulnerabilityLevel.MEDIUM,
                                category="File Security",
                                file_path=str(file_path.relative_to(self.project_root)),
                                recommendation="Restrict file permissions to owner only (600 or 640)"
                            )
                    except Exception as e:
                        logger.error(f"Error checking permissions for {file_path}: {e}")
    
    def _scan_network_security(self):
        """
        Escanear configuraciones de seguridad de red
        """
        logger.info("Scanning network security")
        
        # Verificar configuraciones de SSL/TLS
        self._check_ssl_configuration()
        
        # Verificar headers de seguridad
        self._check_security_headers()
        
        # Verificar puertos abiertos
        self._check_open_ports()
    
    def _check_ssl_configuration(self):
        """
        Verificar configuración SSL/TLS
        """
        # Buscar configuraciones SSL en archivos
        ssl_patterns = {
            'weak_ssl_version': r'ssl_version\s*=\s*["\']?(SSLv2|SSLv3|TLSv1\.0)["\']?',
            'weak_ciphers': r'ssl_ciphers.*RC4|MD5|DES',
            'ssl_disabled': r'ssl\s*=\s*false',
            'verify_disabled': r'ssl_verify\s*=\s*false'
        }
        
        for file_path in self.project_root.rglob('*'):
            if file_path.is_file() and file_path.suffix in ['.py', '.conf', '.config']:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    for pattern_name, pattern in ssl_patterns.items():
                        if re.search(pattern, content, re.IGNORECASE):
                            self._add_finding(
                                id=f"ssl_{pattern_name}_{file_path.name}",
                                title=f"Weak SSL Configuration: {pattern_name.replace('_', ' ').title()}",
                                description=f"Weak SSL/TLS configuration found in {file_path.name}",
                                level=VulnerabilityLevel.HIGH,
                                category="Network Security",
                                file_path=str(file_path.relative_to(self.project_root)),
                                recommendation="Use strong SSL/TLS configuration with modern protocols and ciphers"
                            )
                except Exception:
                    continue
    
    def _check_security_headers(self):
        """
        Verificar headers de seguridad HTTP
        """
        # Buscar configuraciones de headers en archivos
        header_patterns = {
            'missing_hsts': r'Strict-Transport-Security',
            'missing_csp': r'Content-Security-Policy',
            'missing_xframe': r'X-Frame-Options',
            'missing_xss_protection': r'X-XSS-Protection',
            'missing_content_type': r'X-Content-Type-Options'
        }
        
        found_headers = set()
        
        for file_path in self.project_root.rglob('*'):
            if file_path.is_file():
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    for header_name, pattern in header_patterns.items():
                        if re.search(pattern, content, re.IGNORECASE):
                            found_headers.add(header_name)
                except Exception:
                    continue
        
        # Reportar headers faltantes
        missing_headers = set(header_patterns.keys()) - found_headers
        for missing_header in missing_headers:
            self._add_finding(
                id=f"header_{missing_header}",
                title=f"Missing Security Header: {missing_header.replace('missing_', '').replace('_', '-').upper()}",
                description=f"Important security header {missing_header.replace('missing_', '')} is not configured",
                level=VulnerabilityLevel.MEDIUM,
                category="Network Security",
                recommendation=f"Configure {missing_header.replace('missing_', '')} header for enhanced security"
            )
    
    def _check_open_ports(self):
        """
        Verificar puertos abiertos localmente
        """
        try:
            # Escanear puertos comunes
            common_ports = [22, 23, 25, 53, 80, 110, 143, 443, 993, 995, 3306, 5432, 6379, 27017]
            
            for port in common_ports:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', port))
                sock.close()
                
                if result == 0:  # Puerto abierto
                    if port in [23, 25, 110, 143]:  # Protocolos inseguros
                        self._add_finding(
                            id=f"port_insecure_{port}",
                            title=f"Insecure Service on Port {port}",
                            description=f"Potentially insecure service running on port {port}",
                            level=VulnerabilityLevel.HIGH,
                            category="Network Security",
                            recommendation=f"Disable or secure service on port {port}"
                        )
                    elif port in [3306, 5432, 6379, 27017]:  # Bases de datos
                        self._add_finding(
                            id=f"port_database_{port}",
                            title=f"Database Service Exposed on Port {port}",
                            description=f"Database service accessible on port {port}",
                            level=VulnerabilityLevel.MEDIUM,
                            category="Network Security",
                            recommendation=f"Ensure database on port {port} is properly secured and not publicly accessible"
                        )
        except Exception as e:
            logger.error(f"Error checking open ports: {e}")
    
    def _scan_authentication(self):
        """
        Escanear configuraciones de autenticación
        """
        logger.info("Scanning authentication security")
        
        # Buscar patrones de autenticación débil
        auth_patterns = {
            'weak_password_policy': r'password.*length.*[1-7]',
            'no_password_hashing': r'password\s*==\s*.*',
            'hardcoded_credentials': r'username\s*=\s*["\']admin["\'].*password\s*=\s*["\'][^"\']+["\']',
            'jwt_weak_secret': r'jwt.*secret.*["\'][^"\']{1,16}["\']',
            'session_insecure': r'session.*secure\s*=\s*false'
        }
        
        for file_path in self.project_root.rglob('*.py'):
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                for pattern_name, pattern in auth_patterns.items():
                    if re.search(pattern, content, re.IGNORECASE):
                        self._add_finding(
                            id=f"auth_{pattern_name}_{file_path.name}",
                            title=f"Weak Authentication: {pattern_name.replace('_', ' ').title()}",
                            description=f"Weak authentication configuration found in {file_path.name}",
                            level=VulnerabilityLevel.HIGH,
                            category="Authentication Security",
                            file_path=str(file_path.relative_to(self.project_root)),
                            recommendation=self._get_auth_recommendation(pattern_name)
                        )
            except Exception:
                continue
    
    def _scan_data_protection(self):
        """
        Escanear protección de datos
        """
        logger.info("Scanning data protection")
        
        # Buscar datos sensibles sin protección
        sensitive_patterns = {
            'credit_card': r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
            'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
            'email_addresses': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone_numbers': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            'api_keys': r'["\'][A-Za-z0-9]{32,}["\']'
        }
        
        for file_path in self.project_root.rglob('*'):
            if file_path.is_file() and file_path.suffix in ['.py', '.js', '.json', '.txt', '.log']:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    for pattern_name, pattern in sensitive_patterns.items():
                        matches = re.findall(pattern, content)
                        if matches and len(matches) > 2:  # Múltiples coincidencias sugieren datos reales
                            self._add_finding(
                                id=f"data_{pattern_name}_{file_path.name}",
                                title=f"Potential Sensitive Data Exposure: {pattern_name.replace('_', ' ').title()}",
                                description=f"Potential {pattern_name} found in {file_path.name}",
                                level=VulnerabilityLevel.MEDIUM,
                                category="Data Protection",
                                file_path=str(file_path.relative_to(self.project_root)),
                                recommendation=f"Review and protect {pattern_name} data"
                            )
                except Exception:
                    continue
    
    def _scan_infrastructure(self):
        """
        Escanear configuraciones de infraestructura
        """
        logger.info("Scanning infrastructure security")
        
        # Verificar Docker security
        dockerfile = self.project_root / "Dockerfile"
        if dockerfile.exists():
            self._analyze_dockerfile(dockerfile)
        
        # Verificar docker-compose security
        compose_file = self.project_root / "docker-compose.yml"
        if compose_file.exists():
            self._analyze_docker_compose(compose_file)
    
    def _analyze_dockerfile(self, dockerfile: Path):
        """
        Analizar Dockerfile para problemas de seguridad
        
        Args:
            dockerfile: Ruta del Dockerfile
        """
        try:
            with open(dockerfile, 'r') as f:
                content = f.read()
            
            # Patrones inseguros en Dockerfile
            docker_patterns = {
                'root_user': r'USER\s+root',
                'privileged_mode': r'--privileged',
                'add_instead_copy': r'^ADD\s+http',
                'latest_tag': r'FROM.*:latest',
                'sudo_install': r'RUN.*sudo'
            }
            
            for pattern_name, pattern in docker_patterns.items():
                if re.search(pattern, content, re.MULTILINE | re.IGNORECASE):
                    self._add_finding(
                        id=f"docker_{pattern_name}",
                        title=f"Docker Security Issue: {pattern_name.replace('_', ' ').title()}",
                        description=f"Insecure Docker configuration: {pattern_name}",
                        level=VulnerabilityLevel.MEDIUM,
                        category="Infrastructure Security",
                        file_path="Dockerfile",
                        recommendation=self._get_docker_recommendation(pattern_name)
                    )
        except Exception as e:
            logger.error(f"Error analyzing Dockerfile: {e}")
    
    def _analyze_docker_compose(self, compose_file: Path):
        """
        Analizar docker-compose.yml para problemas de seguridad
        
        Args:
            compose_file: Ruta del archivo docker-compose.yml
        """
        try:
            with open(compose_file, 'r') as f:
                content = f.read()
            
            # Patrones inseguros en docker-compose
            compose_patterns = {
                'privileged_container': r'privileged:\s*true',
                'host_network': r'network_mode:\s*host',
                'bind_all_interfaces': r'0\.0\.0\.0:',
                'no_restart_policy': r'restart:\s*no'
            }
            
            for pattern_name, pattern in compose_patterns.items():
                if re.search(pattern, content, re.IGNORECASE):
                    self._add_finding(
                        id=f"compose_{pattern_name}",
                        title=f"Docker Compose Security Issue: {pattern_name.replace('_', ' ').title()}",
                        description=f"Insecure Docker Compose configuration: {pattern_name}",
                        level=VulnerabilityLevel.MEDIUM,
                        category="Infrastructure Security",
                        file_path="docker-compose.yml",
                        recommendation=self._get_compose_recommendation(pattern_name)
                    )
        except Exception as e:
            logger.error(f"Error analyzing docker-compose.yml: {e}")
    
    def _add_finding(self, id: str, title: str, description: str, level: VulnerabilityLevel,
                    category: str, file_path: str = None, line_number: int = None,
                    recommendation: str = "", cve_references: List[str] = None,
                    remediation_effort: str = "medium"):
        """
        Añadir hallazgo de seguridad
        
        Args:
            id: ID único del hallazgo
            title: Título del hallazgo
            description: Descripción detallada
            level: Nivel de severidad
            category: Categoría del hallazgo
            file_path: Ruta del archivo (opcional)
            line_number: Número de línea (opcional)
            recommendation: Recomendación de remediación
            cve_references: Referencias CVE (opcional)
            remediation_effort: Esfuerzo de remediación
        """
        finding = SecurityFinding(
            id=id,
            title=title,
            description=description,
            level=level,
            category=category,
            file_path=file_path,
            line_number=line_number,
            recommendation=recommendation,
            cve_references=cve_references or [],
            remediation_effort=remediation_effort
        )
        
        self.findings.append(finding)
    
    def _generate_security_report(self) -> Dict[str, Any]:
        """
        Generar reporte completo de seguridad
        
        Returns:
            Reporte de auditoría de seguridad
        """
        # Agrupar hallazgos por severidad
        findings_by_level = {}
        for level in VulnerabilityLevel:
            findings_by_level[level.value] = [
                f for f in self.findings if f.level == level
            ]
        
        # Agrupar por categoría
        findings_by_category = {}
        for finding in self.findings:
            if finding.category not in findings_by_category:
                findings_by_category[finding.category] = []
            findings_by_category[finding.category].append(finding)
        
        # Calcular métricas
        total_findings = len(self.findings)
        critical_count = len(findings_by_level.get('critical', []))
        high_count = len(findings_by_level.get('high', []))
        medium_count = len(findings_by_level.get('medium', []))
        low_count = len(findings_by_level.get('low', []))
        
        # Calcular score de seguridad
        security_score = max(0, 100 - (critical_count * 25 + high_count * 10 + medium_count * 5 + low_count * 1))
        
        report = {
            'scan_info': {
                'timestamp': self.scan_timestamp.isoformat(),
                'project_root': str(self.project_root),
                'total_findings': total_findings,
                'security_score': security_score
            },
            'summary': {
                'critical': critical_count,
                'high': high_count,
                'medium': medium_count,
                'low': low_count,
                'info': len(findings_by_level.get('info', []))
            },
            'findings_by_category': {
                category: len(findings) for category, findings in findings_by_category.items()
            },
            'findings': [
                {
                    'id': f.id,
                    'title': f.title,
                    'description': f.description,
                    'level': f.level.value,
                    'category': f.category,
                    'file_path': f.file_path,
                    'line_number': f.line_number,
                    'recommendation': f.recommendation,
                    'cve_references': f.cve_references,
                    'remediation_effort': f.remediation_effort
                } for f in self.findings
            ],
            'recommendations': self._generate_recommendations()
        }
        
        return report
    
    def _generate_recommendations(self) -> List[Dict[str, str]]:
        """
        Generar recomendaciones prioritarias
        
        Returns:
            Lista de recomendaciones
        """
        recommendations = []
        
        # Recomendaciones basadas en hallazgos críticos y altos
        critical_high_findings = [
            f for f in self.findings 
            if f.level in [VulnerabilityLevel.CRITICAL, VulnerabilityLevel.HIGH]
        ]
        
        if critical_high_findings:
            recommendations.append({
                'priority': 'immediate',
                'title': 'Address Critical and High Severity Issues',
                'description': f'Fix {len(critical_high_findings)} critical/high severity vulnerabilities immediately',
                'effort': 'high'
            })
        
        # Recomendaciones por categoría
        category_recommendations = {
            'Code Security': {
                'title': 'Implement Secure Coding Practices',
                'description': 'Review and fix code vulnerabilities, implement input validation',
                'effort': 'medium'
            },
            'Configuration Security': {
                'title': 'Harden Security Configurations',
                'description': 'Update insecure configurations and enable security features',
                'effort': 'low'
            },
            'Dependency Security': {
                'title': 'Update Dependencies',
                'description': 'Update vulnerable dependencies to latest secure versions',
                'effort': 'low'
            },
            'Network Security': {
                'title': 'Strengthen Network Security',
                'description': 'Configure SSL/TLS properly and implement security headers',
                'effort': 'medium'
            }
        }
        
        for category, findings in self._group_findings_by_category().items():
            if findings and category in category_recommendations:
                rec = category_recommendations[category].copy()
                rec['priority'] = 'high' if len(findings) > 5 else 'medium'
                recommendations.append(rec)
        
        return recommendations
    
    def _group_findings_by_category(self) -> Dict[str, List[SecurityFinding]]:
        """
        Agrupar hallazgos por categoría
        
        Returns:
            Diccionario de hallazgos agrupados por categoría
        """
        grouped = {}
        for finding in self.findings:
            if finding.category not in grouped:
                grouped[finding.category] = []
            grouped[finding.category].append(finding)
        return grouped
    
    # Métodos auxiliares para obtener recomendaciones específicas
    def _get_vulnerability_level(self, category: str) -> VulnerabilityLevel:
        """Obtener nivel de vulnerabilidad por categoría"""
        level_map = {
            'sql_injection': VulnerabilityLevel.CRITICAL,
            'xss': VulnerabilityLevel.HIGH,
            'hardcoded_secrets': VulnerabilityLevel.HIGH,
            'command_injection': VulnerabilityLevel.CRITICAL,
            'path_traversal': VulnerabilityLevel.HIGH,
            'insecure_random': VulnerabilityLevel.MEDIUM
        }
        return level_map.get(category, VulnerabilityLevel.MEDIUM)
    
    def _get_recommendation(self, category: str) -> str:
        """Obtener recomendación por categoría de vulnerabilidad"""
        recommendations = {
            'sql_injection': 'Use parameterized queries or ORM to prevent SQL injection',
            'xss': 'Sanitize user input and use proper output encoding',
            'hardcoded_secrets': 'Use environment variables or secure secret management',
            'command_injection': 'Avoid executing user input, use safe alternatives',
            'path_traversal': 'Validate and sanitize file paths, use safe file operations',
            'insecure_random': 'Use cryptographically secure random number generators'
        }
        return recommendations.get(category, 'Review and fix security issue')
    
    def _get_config_recommendation(self, config_type: str) -> str:
        """Obtener recomendación por tipo de configuración"""
        recommendations = {
            'debug_enabled': 'Disable debug mode in production',
            'weak_secret': 'Use a strong, randomly generated secret key',
            'default_passwords': 'Change default passwords to strong, unique passwords',
            'insecure_ssl': 'Enable SSL certificate verification',
            'permissive_cors': 'Configure CORS with specific allowed origins'
        }
        return recommendations.get(config_type, 'Review and secure configuration')
    
    def _get_auth_recommendation(self, pattern_name: str) -> str:
        """Obtener recomendación por patrón de autenticación"""
        recommendations = {
            'weak_password_policy': 'Implement strong password policy (min 8 chars, complexity)',
            'no_password_hashing': 'Hash passwords using bcrypt or similar secure algorithm',
            'hardcoded_credentials': 'Remove hardcoded credentials, use secure authentication',
            'jwt_weak_secret': 'Use a strong JWT secret (min 32 characters)',
            'session_insecure': 'Enable secure session configuration'
        }
        return recommendations.get(pattern_name, 'Strengthen authentication security')
    
    def _get_docker_recommendation(self, pattern_name: str) -> str:
        """Obtener recomendación por patrón de Docker"""
        recommendations = {
            'root_user': 'Create and use non-root user in container',
            'privileged_mode': 'Avoid privileged mode, use specific capabilities',
            'add_instead_copy': 'Use COPY instead of ADD for local files',
            'latest_tag': 'Use specific version tags instead of latest',
            'sudo_install': 'Avoid sudo in containers, run as non-root user'
        }
        return recommendations.get(pattern_name, 'Follow Docker security best practices')
    
    def _get_compose_recommendation(self, pattern_name: str) -> str:
        """Obtener recomendación por patrón de Docker Compose"""
        recommendations = {
            'privileged_container': 'Remove privileged mode unless absolutely necessary',
            'host_network': 'Use bridge network instead of host network',
            'bind_all_interfaces': 'Bind to specific interfaces instead of 0.0.0.0',
            'no_restart_policy': 'Configure appropriate restart policy'
        }
        return recommendations.get(pattern_name, 'Follow Docker Compose security best practices')
    
    def _is_outdated_package(self, package: str, version: str) -> bool:
        """Verificar si un paquete está desactualizado (implementación básica)"""
        # Lista de paquetes comúnmente desactualizados
        outdated_packages = {
            'django': '3.0',
            'flask': '1.0',
            'requests': '2.20',
            'urllib3': '1.24',
            'jinja2': '2.10'
        }
        
        if package.lower() in outdated_packages:
            return version < outdated_packages[package.lower()]
        
        return False
    
    def _map_npm_severity(self, severity: str) -> VulnerabilityLevel:
        """Mapear severidad de NPM a nivel de vulnerabilidad"""
        mapping = {
            'critical': VulnerabilityLevel.CRITICAL,
            'high': VulnerabilityLevel.HIGH,
            'moderate': VulnerabilityLevel.MEDIUM,
            'low': VulnerabilityLevel.LOW,
            'info': VulnerabilityLevel.INFO
        }
        return mapping.get(severity.lower(), VulnerabilityLevel.MEDIUM)

# Instancia global del auditor
security_auditor = None

def initialize_security_auditor(project_root: str):
    """
    Inicializar auditor de seguridad global
    
    Args:
        project_root: Directorio raíz del proyecto
    """
    global security_auditor
    security_auditor = SecurityAuditor(project_root)
    logger.info("Security auditor initialized")

def run_security_audit() -> Dict[str, Any]:
    """
    Ejecutar auditoría completa de seguridad
    
    Returns:
        Reporte de auditoría
    """
    if not security_auditor:
        raise RuntimeError("Security auditor not initialized")
    
    return security_auditor.run_full_audit()

def get_security_score() -> int:
    """
    Obtener score de seguridad actual
    
    Returns:
        Score de seguridad (0-100)
    """
    if not security_auditor:
        return 0
    
    report = security_auditor.run_full_audit()
    return report['scan_info']['security_score']

