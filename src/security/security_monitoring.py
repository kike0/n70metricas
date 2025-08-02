"""
Security Monitoring and Incident Response - Monitoreo de Seguridad y Respuesta a Incidentes
Security-Auditor Implementation - Phase 5
"""

import os
import json
import time
import threading
import queue
import smtplib
import ssl
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import logging
from pathlib import Path
import subprocess
import psutil
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import hashlib
import re
import sqlite3
from collections import defaultdict, deque
import asyncio
import websockets
import json

logger = logging.getLogger(__name__)

class ThreatLevel(Enum):
    """Niveles de amenaza"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class IncidentType(Enum):
    """Tipos de incidentes de seguridad"""
    AUTHENTICATION_FAILURE = "auth_failure"
    BRUTE_FORCE_ATTACK = "brute_force"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    DATA_BREACH = "data_breach"
    MALWARE_DETECTION = "malware"
    NETWORK_INTRUSION = "network_intrusion"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DATA_EXFILTRATION = "data_exfiltration"
    SYSTEM_COMPROMISE = "system_compromise"
    DENIAL_OF_SERVICE = "dos_attack"

class IncidentStatus(Enum):
    """Estados de incidentes"""
    NEW = "new"
    INVESTIGATING = "investigating"
    CONTAINED = "contained"
    RESOLVED = "resolved"
    CLOSED = "closed"

@dataclass
class SecurityEvent:
    """Evento de seguridad"""
    event_id: str
    timestamp: datetime
    event_type: IncidentType
    threat_level: ThreatLevel
    source_ip: str
    user_id: Optional[str]
    description: str
    raw_data: Dict[str, Any]
    indicators: List[str] = field(default_factory=list)
    affected_systems: List[str] = field(default_factory=list)

@dataclass
class SecurityIncident:
    """Incidente de seguridad"""
    incident_id: str
    title: str
    description: str
    incident_type: IncidentType
    threat_level: ThreatLevel
    status: IncidentStatus
    created_at: datetime
    updated_at: datetime
    assigned_to: Optional[str]
    events: List[SecurityEvent] = field(default_factory=list)
    timeline: List[Dict[str, Any]] = field(default_factory=list)
    containment_actions: List[str] = field(default_factory=list)
    resolution_notes: Optional[str] = None

@dataclass
class MonitoringConfig:
    """Configuración de monitoreo"""
    enable_real_time_monitoring: bool = True
    enable_log_analysis: bool = True
    enable_network_monitoring: bool = True
    enable_file_integrity_monitoring: bool = True
    enable_behavioral_analysis: bool = True
    alert_thresholds: Dict[str, int] = field(default_factory=dict)
    notification_channels: List[str] = field(default_factory=list)
    retention_days: int = 90
    auto_response_enabled: bool = True

class SecurityEventDetector:
    """
    Detector de eventos de seguridad
    """
    
    def __init__(self, config: MonitoringConfig):
        """
        Inicializar detector de eventos
        
        Args:
            config: Configuración de monitoreo
        """
        self.config = config
        self.detection_rules = {}
        self.event_queue = queue.Queue()
        self.running = False
        
        # Contadores para detección de patrones
        self.failed_logins = defaultdict(int)
        self.request_counts = defaultdict(lambda: deque(maxlen=100))
        self.suspicious_ips = set()
        
        # Configurar reglas de detección
        self._setup_detection_rules()
        
        logger.info("Security event detector initialized")
    
    def _setup_detection_rules(self):
        """Configurar reglas de detección"""
        self.detection_rules = {
            'failed_login_threshold': {
                'pattern': r'Failed password for .* from (\d+\.\d+\.\d+\.\d+)',
                'threshold': 5,
                'window_minutes': 5,
                'threat_level': ThreatLevel.MEDIUM,
                'incident_type': IncidentType.BRUTE_FORCE_ATTACK
            },
            'suspicious_user_agent': {
                'pattern': r'(sqlmap|nikto|nmap|masscan|zap)',
                'threshold': 1,
                'window_minutes': 1,
                'threat_level': ThreatLevel.HIGH,
                'incident_type': IncidentType.SUSPICIOUS_ACTIVITY
            },
            'sql_injection_attempt': {
                'pattern': r'(union.*select|drop.*table|exec.*xp_|script.*alert)',
                'threshold': 1,
                'window_minutes': 1,
                'threat_level': ThreatLevel.HIGH,
                'incident_type': IncidentType.SUSPICIOUS_ACTIVITY
            },
            'privilege_escalation': {
                'pattern': r'(sudo.*su|chmod.*777|usermod.*-G)',
                'threshold': 1,
                'window_minutes': 1,
                'threat_level': ThreatLevel.CRITICAL,
                'incident_type': IncidentType.PRIVILEGE_ESCALATION
            },
            'data_exfiltration': {
                'pattern': r'(wget.*http|curl.*-o|scp.*@)',
                'threshold': 3,
                'window_minutes': 10,
                'threat_level': ThreatLevel.HIGH,
                'incident_type': IncidentType.DATA_EXFILTRATION
            }
        }
    
    def analyze_log_entry(self, log_entry: str, source: str) -> Optional[SecurityEvent]:
        """
        Analizar entrada de log para detectar eventos de seguridad
        
        Args:
            log_entry: Entrada de log
            source: Fuente del log
            
        Returns:
            Evento de seguridad si se detecta algo
        """
        for rule_name, rule in self.detection_rules.items():
            pattern = rule['pattern']
            match = re.search(pattern, log_entry, re.IGNORECASE)
            
            if match:
                # Extraer IP si está disponible
                ip_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', log_entry)
                source_ip = ip_match.group(1) if ip_match else 'unknown'
                
                # Crear evento
                event = SecurityEvent(
                    event_id=f"evt_{int(time.time())}_{hash(log_entry) % 10000}",
                    timestamp=datetime.utcnow(),
                    event_type=rule['incident_type'],
                    threat_level=rule['threat_level'],
                    source_ip=source_ip,
                    user_id=None,
                    description=f"Security rule triggered: {rule_name}",
                    raw_data={
                        'log_entry': log_entry,
                        'source': source,
                        'rule': rule_name,
                        'match': match.group(0) if match else None
                    },
                    indicators=[match.group(0)] if match else []
                )
                
                return event
        
        return None
    
    def analyze_network_traffic(self, connection_info: Dict[str, Any]) -> Optional[SecurityEvent]:
        """
        Analizar tráfico de red para detectar anomalías
        
        Args:
            connection_info: Información de conexión de red
            
        Returns:
            Evento de seguridad si se detecta algo
        """
        source_ip = connection_info.get('source_ip', 'unknown')
        destination_port = connection_info.get('destination_port', 0)
        
        # Detectar escaneo de puertos
        if destination_port in [21, 22, 23, 25, 53, 80, 110, 143, 443, 993, 995, 3389]:
            current_time = datetime.utcnow()
            self.request_counts[source_ip].append(current_time)
            
            # Contar requests en los últimos 5 minutos
            recent_requests = [
                t for t in self.request_counts[source_ip]
                if (current_time - t).total_seconds() < 300
            ]
            
            if len(recent_requests) > 20:  # Más de 20 requests en 5 minutos
                return SecurityEvent(
                    event_id=f"net_{int(time.time())}_{hash(source_ip) % 10000}",
                    timestamp=current_time,
                    event_type=IncidentType.NETWORK_INTRUSION,
                    threat_level=ThreatLevel.HIGH,
                    source_ip=source_ip,
                    user_id=None,
                    description=f"Potential port scan detected from {source_ip}",
                    raw_data=connection_info,
                    indicators=[f"high_request_rate:{len(recent_requests)}"]
                )
        
        return None
    
    def analyze_authentication_event(self, auth_data: Dict[str, Any]) -> Optional[SecurityEvent]:
        """
        Analizar evento de autenticación
        
        Args:
            auth_data: Datos de autenticación
            
        Returns:
            Evento de seguridad si se detecta algo
        """
        if not auth_data.get('success', True):
            source_ip = auth_data.get('source_ip', 'unknown')
            user_id = auth_data.get('user_id', 'unknown')
            
            # Incrementar contador de fallos
            key = f"{source_ip}:{user_id}"
            self.failed_logins[key] += 1
            
            # Verificar umbral
            if self.failed_logins[key] >= 5:
                return SecurityEvent(
                    event_id=f"auth_{int(time.time())}_{hash(key) % 10000}",
                    timestamp=datetime.utcnow(),
                    event_type=IncidentType.BRUTE_FORCE_ATTACK,
                    threat_level=ThreatLevel.HIGH,
                    source_ip=source_ip,
                    user_id=user_id,
                    description=f"Brute force attack detected: {self.failed_logins[key]} failed attempts",
                    raw_data=auth_data,
                    indicators=[f"failed_attempts:{self.failed_logins[key]}"]
                )
        
        return None
    
    def start_monitoring(self):
        """Iniciar monitoreo en tiempo real"""
        self.running = True
        
        # Iniciar hilos de monitoreo
        if self.config.enable_log_analysis:
            threading.Thread(target=self._monitor_logs, daemon=True).start()
        
        if self.config.enable_network_monitoring:
            threading.Thread(target=self._monitor_network, daemon=True).start()
        
        if self.config.enable_file_integrity_monitoring:
            threading.Thread(target=self._monitor_file_integrity, daemon=True).start()
        
        logger.info("Security monitoring started")
    
    def stop_monitoring(self):
        """Detener monitoreo"""
        self.running = False
        logger.info("Security monitoring stopped")
    
    def _monitor_logs(self):
        """Monitorear logs del sistema"""
        log_files = [
            '/var/log/auth.log',
            '/var/log/syslog',
            '/var/log/nginx/access.log',
            '/var/log/nginx/error.log',
            '/var/log/application.log'
        ]
        
        while self.running:
            for log_file in log_files:
                if os.path.exists(log_file):
                    try:
                        with open(log_file, 'r') as f:
                            # Ir al final del archivo
                            f.seek(0, 2)
                            
                            while self.running:
                                line = f.readline()
                                if line:
                                    event = self.analyze_log_entry(line.strip(), log_file)
                                    if event:
                                        self.event_queue.put(event)
                                else:
                                    time.sleep(1)
                    except Exception as e:
                        logger.error(f"Error monitoring log file {log_file}: {e}")
            
            time.sleep(5)
    
    def _monitor_network(self):
        """Monitorear conexiones de red"""
        while self.running:
            try:
                connections = psutil.net_connections(kind='inet')
                for conn in connections:
                    if conn.raddr:
                        connection_info = {
                            'source_ip': conn.raddr.ip,
                            'source_port': conn.raddr.port,
                            'destination_port': conn.laddr.port,
                            'status': conn.status,
                            'pid': conn.pid
                        }
                        
                        event = self.analyze_network_traffic(connection_info)
                        if event:
                            self.event_queue.put(event)
            
            except Exception as e:
                logger.error(f"Error monitoring network: {e}")
            
            time.sleep(10)
    
    def _monitor_file_integrity(self):
        """Monitorear integridad de archivos críticos"""
        critical_files = [
            '/etc/passwd',
            '/etc/shadow',
            '/etc/sudoers',
            '/etc/ssh/sshd_config',
            '/etc/nginx/nginx.conf'
        ]
        
        # Calcular hashes iniciales
        file_hashes = {}
        for file_path in critical_files:
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    file_hashes[file_path] = hashlib.sha256(f.read()).hexdigest()
        
        while self.running:
            try:
                for file_path in critical_files:
                    if os.path.exists(file_path):
                        with open(file_path, 'rb') as f:
                            current_hash = hashlib.sha256(f.read()).hexdigest()
                        
                        if file_path in file_hashes and file_hashes[file_path] != current_hash:
                            event = SecurityEvent(
                                event_id=f"fim_{int(time.time())}_{hash(file_path) % 10000}",
                                timestamp=datetime.utcnow(),
                                event_type=IncidentType.SYSTEM_COMPROMISE,
                                threat_level=ThreatLevel.CRITICAL,
                                source_ip='localhost',
                                user_id=None,
                                description=f"Critical file modified: {file_path}",
                                raw_data={
                                    'file_path': file_path,
                                    'old_hash': file_hashes[file_path],
                                    'new_hash': current_hash
                                },
                                indicators=[f"file_modified:{file_path}"]
                            )
                            
                            self.event_queue.put(event)
                            file_hashes[file_path] = current_hash
            
            except Exception as e:
                logger.error(f"Error monitoring file integrity: {e}")
            
            time.sleep(30)

class IncidentResponseManager:
    """
    Gestor de respuesta a incidentes
    """
    
    def __init__(self, config: MonitoringConfig):
        """
        Inicializar gestor de respuesta a incidentes
        
        Args:
            config: Configuración de monitoreo
        """
        self.config = config
        self.incidents: Dict[str, SecurityIncident] = {}
        self.response_playbooks = {}
        self.notification_handlers = {}
        
        # Base de datos para persistencia
        self.db_path = Path("security_incidents.db")
        self._init_database()
        
        # Configurar playbooks de respuesta
        self._setup_response_playbooks()
        
        # Configurar manejadores de notificación
        self._setup_notification_handlers()
        
        logger.info("Incident response manager initialized")
    
    def _init_database(self):
        """Inicializar base de datos de incidentes"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS incidents (
                incident_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                incident_type TEXT,
                threat_level TEXT,
                status TEXT,
                created_at TEXT,
                updated_at TEXT,
                assigned_to TEXT,
                resolution_notes TEXT,
                raw_data TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                incident_id TEXT,
                timestamp TEXT,
                event_type TEXT,
                threat_level TEXT,
                source_ip TEXT,
                user_id TEXT,
                description TEXT,
                raw_data TEXT,
                FOREIGN KEY (incident_id) REFERENCES incidents (incident_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _setup_response_playbooks(self):
        """Configurar playbooks de respuesta automática"""
        self.response_playbooks = {
            IncidentType.BRUTE_FORCE_ATTACK: {
                'auto_actions': [
                    'block_source_ip',
                    'increase_monitoring',
                    'notify_admin'
                ],
                'manual_actions': [
                    'review_logs',
                    'check_account_compromise',
                    'update_security_policies'
                ]
            },
            IncidentType.SUSPICIOUS_ACTIVITY: {
                'auto_actions': [
                    'log_detailed_activity',
                    'increase_monitoring',
                    'notify_security_team'
                ],
                'manual_actions': [
                    'investigate_user_activity',
                    'check_system_integrity',
                    'review_access_logs'
                ]
            },
            IncidentType.SYSTEM_COMPROMISE: {
                'auto_actions': [
                    'isolate_system',
                    'backup_evidence',
                    'notify_admin_urgent'
                ],
                'manual_actions': [
                    'forensic_analysis',
                    'restore_from_backup',
                    'patch_vulnerabilities'
                ]
            },
            IncidentType.DATA_BREACH: {
                'auto_actions': [
                    'isolate_affected_systems',
                    'backup_evidence',
                    'notify_legal_team',
                    'notify_admin_critical'
                ],
                'manual_actions': [
                    'assess_data_exposure',
                    'notify_affected_users',
                    'regulatory_reporting',
                    'implement_additional_controls'
                ]
            }
        }
    
    def _setup_notification_handlers(self):
        """Configurar manejadores de notificación"""
        self.notification_handlers = {
            'email': self._send_email_notification,
            'webhook': self._send_webhook_notification,
            'sms': self._send_sms_notification,
            'slack': self._send_slack_notification
        }
    
    def create_incident(self, event: SecurityEvent) -> SecurityIncident:
        """
        Crear nuevo incidente de seguridad
        
        Args:
            event: Evento que desencadena el incidente
            
        Returns:
            Incidente creado
        """
        incident_id = f"inc_{int(time.time())}_{hash(event.event_id) % 10000}"
        
        incident = SecurityIncident(
            incident_id=incident_id,
            title=f"{event.incident_type.value.replace('_', ' ').title()} - {event.source_ip}",
            description=event.description,
            incident_type=event.incident_type,
            threat_level=event.threat_level,
            status=IncidentStatus.NEW,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            assigned_to=None,
            events=[event],
            timeline=[{
                'timestamp': datetime.utcnow().isoformat(),
                'action': 'incident_created',
                'description': 'Incident created from security event',
                'user': 'system'
            }]
        )
        
        # Almacenar incidente
        self.incidents[incident_id] = incident
        self._save_incident_to_db(incident)
        
        # Ejecutar respuesta automática
        if self.config.auto_response_enabled:
            self._execute_auto_response(incident)
        
        # Enviar notificaciones
        self._send_notifications(incident)
        
        logger.info(f"Security incident created: {incident_id}")
        
        return incident
    
    def update_incident(self, incident_id: str, status: IncidentStatus = None,
                       assigned_to: str = None, notes: str = None) -> bool:
        """
        Actualizar incidente
        
        Args:
            incident_id: ID del incidente
            status: Nuevo estado
            assigned_to: Asignado a
            notes: Notas adicionales
            
        Returns:
            True si se actualizó correctamente
        """
        if incident_id not in self.incidents:
            return False
        
        incident = self.incidents[incident_id]
        
        if status:
            incident.status = status
            incident.timeline.append({
                'timestamp': datetime.utcnow().isoformat(),
                'action': 'status_changed',
                'description': f'Status changed to {status.value}',
                'user': assigned_to or 'system'
            })
        
        if assigned_to:
            incident.assigned_to = assigned_to
            incident.timeline.append({
                'timestamp': datetime.utcnow().isoformat(),
                'action': 'assigned',
                'description': f'Incident assigned to {assigned_to}',
                'user': 'system'
            })
        
        if notes:
            incident.resolution_notes = notes
            incident.timeline.append({
                'timestamp': datetime.utcnow().isoformat(),
                'action': 'notes_added',
                'description': 'Resolution notes added',
                'user': assigned_to or 'system'
            })
        
        incident.updated_at = datetime.utcnow()
        self._save_incident_to_db(incident)
        
        logger.info(f"Incident updated: {incident_id}")
        
        return True
    
    def add_event_to_incident(self, incident_id: str, event: SecurityEvent) -> bool:
        """
        Añadir evento a incidente existente
        
        Args:
            incident_id: ID del incidente
            event: Evento a añadir
            
        Returns:
            True si se añadió correctamente
        """
        if incident_id not in self.incidents:
            return False
        
        incident = self.incidents[incident_id]
        incident.events.append(event)
        incident.updated_at = datetime.utcnow()
        
        incident.timeline.append({
            'timestamp': datetime.utcnow().isoformat(),
            'action': 'event_added',
            'description': f'Security event added: {event.event_id}',
            'user': 'system'
        })
        
        self._save_incident_to_db(incident)
        
        logger.info(f"Event added to incident: {event.event_id} -> {incident_id}")
        
        return True
    
    def _execute_auto_response(self, incident: SecurityIncident):
        """
        Ejecutar respuesta automática
        
        Args:
            incident: Incidente de seguridad
        """
        playbook = self.response_playbooks.get(incident.incident_type)
        if not playbook:
            return
        
        auto_actions = playbook.get('auto_actions', [])
        
        for action in auto_actions:
            try:
                if action == 'block_source_ip':
                    self._block_source_ip(incident)
                elif action == 'increase_monitoring':
                    self._increase_monitoring(incident)
                elif action == 'isolate_system':
                    self._isolate_system(incident)
                elif action == 'backup_evidence':
                    self._backup_evidence(incident)
                elif action.startswith('notify_'):
                    self._send_priority_notification(incident, action)
                
                incident.containment_actions.append(f"Auto: {action}")
                
            except Exception as e:
                logger.error(f"Error executing auto response action {action}: {e}")
    
    def _block_source_ip(self, incident: SecurityIncident):
        """
        Bloquear IP de origen
        
        Args:
            incident: Incidente de seguridad
        """
        for event in incident.events:
            if event.source_ip and event.source_ip != 'unknown':
                try:
                    # Usar iptables para bloquear IP
                    subprocess.run([
                        'iptables', '-A', 'INPUT', '-s', event.source_ip, '-j', 'DROP'
                    ], check=True)
                    
                    logger.info(f"Blocked IP: {event.source_ip}")
                    
                except subprocess.CalledProcessError as e:
                    logger.error(f"Failed to block IP {event.source_ip}: {e}")
    
    def _increase_monitoring(self, incident: SecurityIncident):
        """
        Aumentar nivel de monitoreo
        
        Args:
            incident: Incidente de seguridad
        """
        # Implementar lógica para aumentar monitoreo
        logger.info(f"Increased monitoring for incident: {incident.incident_id}")
    
    def _isolate_system(self, incident: SecurityIncident):
        """
        Aislar sistema comprometido
        
        Args:
            incident: Incidente de seguridad
        """
        # Implementar lógica de aislamiento
        logger.warning(f"System isolation triggered for incident: {incident.incident_id}")
    
    def _backup_evidence(self, incident: SecurityIncident):
        """
        Respaldar evidencia
        
        Args:
            incident: Incidente de seguridad
        """
        evidence_dir = Path(f"evidence/{incident.incident_id}")
        evidence_dir.mkdir(parents=True, exist_ok=True)
        
        # Guardar datos del incidente
        with open(evidence_dir / "incident_data.json", 'w') as f:
            incident_data = {
                'incident_id': incident.incident_id,
                'title': incident.title,
                'description': incident.description,
                'incident_type': incident.incident_type.value,
                'threat_level': incident.threat_level.value,
                'created_at': incident.created_at.isoformat(),
                'events': [
                    {
                        'event_id': event.event_id,
                        'timestamp': event.timestamp.isoformat(),
                        'event_type': event.event_type.value,
                        'source_ip': event.source_ip,
                        'description': event.description,
                        'raw_data': event.raw_data
                    }
                    for event in incident.events
                ]
            }
            json.dump(incident_data, f, indent=2)
        
        logger.info(f"Evidence backed up for incident: {incident.incident_id}")
    
    def _send_notifications(self, incident: SecurityIncident):
        """
        Enviar notificaciones
        
        Args:
            incident: Incidente de seguridad
        """
        for channel in self.config.notification_channels:
            if channel in self.notification_handlers:
                try:
                    self.notification_handlers[channel](incident)
                except Exception as e:
                    logger.error(f"Error sending notification via {channel}: {e}")
    
    def _send_priority_notification(self, incident: SecurityIncident, priority: str):
        """
        Enviar notificación prioritaria
        
        Args:
            incident: Incidente de seguridad
            priority: Nivel de prioridad
        """
        # Implementar notificaciones prioritarias
        logger.info(f"Priority notification sent: {priority} for incident {incident.incident_id}")
    
    def _send_email_notification(self, incident: SecurityIncident):
        """
        Enviar notificación por email
        
        Args:
            incident: Incidente de seguridad
        """
        # Configuración de email (debería venir de configuración)
        smtp_server = os.getenv('SMTP_SERVER', 'localhost')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        smtp_user = os.getenv('SMTP_USER', '')
        smtp_password = os.getenv('SMTP_PASSWORD', '')
        
        if not smtp_user:
            logger.warning("Email notifications not configured")
            return
        
        try:
            msg = MIMEMultipart()
            msg['From'] = smtp_user
            msg['To'] = os.getenv('SECURITY_EMAIL', 'security@company.com')
            msg['Subject'] = f"Security Incident: {incident.title}"
            
            body = f"""
Security Incident Alert

Incident ID: {incident.incident_id}
Title: {incident.title}
Type: {incident.incident_type.value}
Threat Level: {incident.threat_level.value}
Status: {incident.status.value}
Created: {incident.created_at}

Description:
{incident.description}

Events:
"""
            
            for event in incident.events:
                body += f"- {event.timestamp}: {event.description} (IP: {event.source_ip})\n"
            
            msg.attach(MIMEText(body, 'plain'))
            
            context = ssl.create_default_context()
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls(context=context)
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email notification sent for incident: {incident.incident_id}")
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
    
    def _send_webhook_notification(self, incident: SecurityIncident):
        """
        Enviar notificación por webhook
        
        Args:
            incident: Incidente de seguridad
        """
        webhook_url = os.getenv('SECURITY_WEBHOOK_URL')
        if not webhook_url:
            return
        
        try:
            payload = {
                'incident_id': incident.incident_id,
                'title': incident.title,
                'incident_type': incident.incident_type.value,
                'threat_level': incident.threat_level.value,
                'status': incident.status.value,
                'created_at': incident.created_at.isoformat(),
                'description': incident.description
            }
            
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            
            logger.info(f"Webhook notification sent for incident: {incident.incident_id}")
            
        except Exception as e:
            logger.error(f"Failed to send webhook notification: {e}")
    
    def _send_sms_notification(self, incident: SecurityIncident):
        """
        Enviar notificación por SMS
        
        Args:
            incident: Incidente de seguridad
        """
        # Implementar integración con servicio SMS
        logger.info(f"SMS notification would be sent for incident: {incident.incident_id}")
    
    def _send_slack_notification(self, incident: SecurityIncident):
        """
        Enviar notificación a Slack
        
        Args:
            incident: Incidente de seguridad
        """
        slack_webhook = os.getenv('SLACK_WEBHOOK_URL')
        if not slack_webhook:
            return
        
        try:
            color = {
                ThreatLevel.LOW: 'good',
                ThreatLevel.MEDIUM: 'warning',
                ThreatLevel.HIGH: 'danger',
                ThreatLevel.CRITICAL: 'danger'
            }.get(incident.threat_level, 'warning')
            
            payload = {
                'attachments': [{
                    'color': color,
                    'title': f'Security Incident: {incident.title}',
                    'fields': [
                        {'title': 'Incident ID', 'value': incident.incident_id, 'short': True},
                        {'title': 'Type', 'value': incident.incident_type.value, 'short': True},
                        {'title': 'Threat Level', 'value': incident.threat_level.value, 'short': True},
                        {'title': 'Status', 'value': incident.status.value, 'short': True},
                        {'title': 'Description', 'value': incident.description, 'short': False}
                    ],
                    'ts': int(incident.created_at.timestamp())
                }]
            }
            
            response = requests.post(slack_webhook, json=payload, timeout=10)
            response.raise_for_status()
            
            logger.info(f"Slack notification sent for incident: {incident.incident_id}")
            
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
    
    def _save_incident_to_db(self, incident: SecurityIncident):
        """
        Guardar incidente en base de datos
        
        Args:
            incident: Incidente a guardar
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO incidents 
            (incident_id, title, description, incident_type, threat_level, status, 
             created_at, updated_at, assigned_to, resolution_notes, raw_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            incident.incident_id,
            incident.title,
            incident.description,
            incident.incident_type.value,
            incident.threat_level.value,
            incident.status.value,
            incident.created_at.isoformat(),
            incident.updated_at.isoformat(),
            incident.assigned_to,
            incident.resolution_notes,
            json.dumps({
                'timeline': incident.timeline,
                'containment_actions': incident.containment_actions
            })
        ))
        
        # Guardar eventos
        for event in incident.events:
            cursor.execute('''
                INSERT OR REPLACE INTO events
                (event_id, incident_id, timestamp, event_type, threat_level, 
                 source_ip, user_id, description, raw_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                event.event_id,
                incident.incident_id,
                event.timestamp.isoformat(),
                event.event_type.value,
                event.threat_level.value,
                event.source_ip,
                event.user_id,
                event.description,
                json.dumps(event.raw_data)
            ))
        
        conn.commit()
        conn.close()
    
    def get_incident_statistics(self) -> Dict[str, Any]:
        """
        Obtener estadísticas de incidentes
        
        Returns:
            Estadísticas de incidentes
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Estadísticas generales
        cursor.execute('SELECT COUNT(*) FROM incidents')
        total_incidents = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM incidents WHERE status = ?', (IncidentStatus.NEW.value,))
        new_incidents = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM incidents WHERE status = ?', (IncidentStatus.INVESTIGATING.value,))
        investigating_incidents = cursor.fetchone()[0]
        
        # Incidentes por tipo
        cursor.execute('''
            SELECT incident_type, COUNT(*) 
            FROM incidents 
            GROUP BY incident_type
        ''')
        incidents_by_type = dict(cursor.fetchall())
        
        # Incidentes por nivel de amenaza
        cursor.execute('''
            SELECT threat_level, COUNT(*) 
            FROM incidents 
            GROUP BY threat_level
        ''')
        incidents_by_threat_level = dict(cursor.fetchall())
        
        # Incidentes recientes (últimos 7 días)
        week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
        cursor.execute('SELECT COUNT(*) FROM incidents WHERE created_at > ?', (week_ago,))
        recent_incidents = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_incidents': total_incidents,
            'new_incidents': new_incidents,
            'investigating_incidents': investigating_incidents,
            'recent_incidents': recent_incidents,
            'incidents_by_type': incidents_by_type,
            'incidents_by_threat_level': incidents_by_threat_level,
            'last_updated': datetime.utcnow().isoformat()
        }

class SecurityMonitoringSystem:
    """
    Sistema completo de monitoreo de seguridad
    """
    
    def __init__(self, config: MonitoringConfig):
        """
        Inicializar sistema de monitoreo
        
        Args:
            config: Configuración de monitoreo
        """
        self.config = config
        self.event_detector = SecurityEventDetector(config)
        self.incident_manager = IncidentResponseManager(config)
        self.running = False
        
        logger.info("Security monitoring system initialized")
    
    def start(self):
        """Iniciar sistema de monitoreo"""
        self.running = True
        
        # Iniciar detector de eventos
        self.event_detector.start_monitoring()
        
        # Iniciar procesador de eventos
        threading.Thread(target=self._process_events, daemon=True).start()
        
        logger.info("Security monitoring system started")
    
    def stop(self):
        """Detener sistema de monitoreo"""
        self.running = False
        self.event_detector.stop_monitoring()
        
        logger.info("Security monitoring system stopped")
    
    def _process_events(self):
        """Procesar eventos de seguridad"""
        while self.running:
            try:
                # Obtener evento de la cola
                event = self.event_detector.event_queue.get(timeout=1)
                
                # Buscar incidente existente relacionado
                related_incident = self._find_related_incident(event)
                
                if related_incident:
                    # Añadir evento a incidente existente
                    self.incident_manager.add_event_to_incident(related_incident.incident_id, event)
                else:
                    # Crear nuevo incidente
                    self.incident_manager.create_incident(event)
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing security event: {e}")
    
    def _find_related_incident(self, event: SecurityEvent) -> Optional[SecurityIncident]:
        """
        Buscar incidente relacionado
        
        Args:
            event: Evento de seguridad
            
        Returns:
            Incidente relacionado si existe
        """
        # Buscar incidentes abiertos del mismo tipo y IP
        for incident in self.incident_manager.incidents.values():
            if (incident.status in [IncidentStatus.NEW, IncidentStatus.INVESTIGATING] and
                incident.incident_type == event.incident_type):
                
                # Verificar si hay eventos con la misma IP en las últimas 24 horas
                for existing_event in incident.events:
                    if (existing_event.source_ip == event.source_ip and
                        (event.timestamp - existing_event.timestamp).total_seconds() < 86400):
                        return incident
        
        return None
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """
        Obtener datos para dashboard de seguridad
        
        Returns:
            Datos del dashboard
        """
        stats = self.incident_manager.get_incident_statistics()
        
        # Añadir información del sistema
        stats.update({
            'monitoring_status': 'active' if self.running else 'inactive',
            'event_queue_size': self.event_detector.event_queue.qsize(),
            'system_uptime': time.time() - psutil.boot_time(),
            'cpu_usage': psutil.cpu_percent(),
            'memory_usage': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent
        })
        
        return stats

# Instancia global del sistema de monitoreo
security_monitoring_system = None

def initialize_security_monitoring(config: MonitoringConfig):
    """
    Inicializar sistema de monitoreo de seguridad
    
    Args:
        config: Configuración de monitoreo
    """
    global security_monitoring_system
    security_monitoring_system = SecurityMonitoringSystem(config)
    logger.info("Security monitoring system initialized globally")

def get_security_monitoring_system() -> SecurityMonitoringSystem:
    """
    Obtener sistema de monitoreo de seguridad
    
    Returns:
        Instancia del sistema de monitoreo
    """
    if not security_monitoring_system:
        raise RuntimeError("Security monitoring system not initialized")
    return security_monitoring_system

def start_security_monitoring():
    """Iniciar monitoreo de seguridad"""
    system = get_security_monitoring_system()
    system.start()

def stop_security_monitoring():
    """Detener monitoreo de seguridad"""
    system = get_security_monitoring_system()
    system.stop()

def get_security_dashboard_data() -> Dict[str, Any]:
    """
    Obtener datos del dashboard de seguridad
    
    Returns:
        Datos del dashboard
    """
    system = get_security_monitoring_system()
    return system.get_dashboard_data()

