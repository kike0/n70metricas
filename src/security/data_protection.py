"""
Data Protection and Encryption - Sistema de Encriptación y Protección de Datos
Security-Auditor Implementation - Phase 4
"""

import os
import base64
import hashlib
import secrets
import json
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime, timedelta
from pathlib import Path
import hmac
import zlib

# Cryptographic libraries
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.backends import default_backend
import argon2

logger = logging.getLogger(__name__)

class EncryptionLevel(Enum):
    """Niveles de encriptación"""
    BASIC = "basic"          # AES-128
    STANDARD = "standard"    # AES-256
    HIGH = "high"           # AES-256 + RSA
    PARANOID = "paranoid"   # AES-256 + RSA + Multiple layers

class DataClassification(Enum):
    """Clasificación de datos"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    TOP_SECRET = "top_secret"

@dataclass
class EncryptionConfig:
    """Configuración de encriptación"""
    level: EncryptionLevel = EncryptionLevel.STANDARD
    key_rotation_days: int = 90
    backup_keys: bool = True
    compress_before_encrypt: bool = True
    use_hardware_security: bool = False
    audit_encryption_operations: bool = True
    secure_key_storage: bool = True

@dataclass
class DataProtectionPolicy:
    """Política de protección de datos"""
    classification: DataClassification
    encryption_required: bool
    retention_days: int
    backup_required: bool
    audit_access: bool
    geographic_restrictions: List[str]
    allowed_operations: List[str]

class CryptographicManager:
    """
    Gestor criptográfico avanzado para protección de datos
    """
    
    def __init__(self, config: EncryptionConfig):
        """
        Inicializar gestor criptográfico
        
        Args:
            config: Configuración de encriptación
        """
        self.config = config
        self.backend = default_backend()
        
        # Configuraciones de algoritmos por nivel
        self.algorithm_configs = {
            EncryptionLevel.BASIC: {
                'symmetric': algorithms.AES,
                'key_size': 128,
                'mode': modes.GCM,
                'kdf_iterations': 100000
            },
            EncryptionLevel.STANDARD: {
                'symmetric': algorithms.AES,
                'key_size': 256,
                'mode': modes.GCM,
                'kdf_iterations': 200000
            },
            EncryptionLevel.HIGH: {
                'symmetric': algorithms.AES,
                'key_size': 256,
                'mode': modes.GCM,
                'kdf_iterations': 500000,
                'asymmetric_key_size': 2048
            },
            EncryptionLevel.PARANOID: {
                'symmetric': algorithms.AES,
                'key_size': 256,
                'mode': modes.GCM,
                'kdf_iterations': 1000000,
                'asymmetric_key_size': 4096,
                'layers': 3
            }
        }
        
        # Inicializar argon2 para hashing de contraseñas
        self.password_hasher = argon2.PasswordHasher(
            time_cost=3,
            memory_cost=65536,
            parallelism=1,
            hash_len=32,
            salt_len=16
        )
        
        logger.info(f"Cryptographic manager initialized with level: {config.level.value}")
    
    def generate_key(self, key_type: str = "symmetric") -> bytes:
        """
        Generar clave criptográfica
        
        Args:
            key_type: Tipo de clave ("symmetric", "asymmetric")
            
        Returns:
            Clave generada
        """
        config = self.algorithm_configs[self.config.level]
        
        if key_type == "symmetric":
            key_size = config['key_size'] // 8  # Convertir bits a bytes
            return secrets.token_bytes(key_size)
        
        elif key_type == "asymmetric":
            key_size = config.get('asymmetric_key_size', 2048)
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=key_size,
                backend=self.backend
            )
            return private_key
        
        else:
            raise ValueError(f"Unsupported key type: {key_type}")
    
    def derive_key_from_password(self, password: str, salt: bytes = None) -> Tuple[bytes, bytes]:
        """
        Derivar clave desde contraseña usando PBKDF2
        
        Args:
            password: Contraseña base
            salt: Salt (se genera si no se proporciona)
            
        Returns:
            Tupla (clave_derivada, salt)
        """
        if salt is None:
            salt = secrets.token_bytes(32)
        
        config = self.algorithm_configs[self.config.level]
        key_size = config['key_size'] // 8
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=key_size,
            salt=salt,
            iterations=config['kdf_iterations'],
            backend=self.backend
        )
        
        key = kdf.derive(password.encode('utf-8'))
        return key, salt
    
    def derive_key_scrypt(self, password: str, salt: bytes = None) -> Tuple[bytes, bytes]:
        """
        Derivar clave usando Scrypt (más resistente a ataques de hardware)
        
        Args:
            password: Contraseña base
            salt: Salt (se genera si no se proporciona)
            
        Returns:
            Tupla (clave_derivada, salt)
        """
        if salt is None:
            salt = secrets.token_bytes(32)
        
        config = self.algorithm_configs[self.config.level]
        key_size = config['key_size'] // 8
        
        kdf = Scrypt(
            algorithm=hashes.SHA256(),
            length=key_size,
            salt=salt,
            n=2**14,  # CPU/memory cost
            r=8,      # Block size
            p=1,      # Parallelization
            backend=self.backend
        )
        
        key = kdf.derive(password.encode('utf-8'))
        return key, salt
    
    def encrypt_data(self, data: Union[str, bytes], key: bytes = None, 
                    additional_data: bytes = None) -> Dict[str, Any]:
        """
        Encriptar datos usando AES-GCM
        
        Args:
            data: Datos a encriptar
            key: Clave de encriptación (se genera si no se proporciona)
            additional_data: Datos adicionales para autenticación
            
        Returns:
            Diccionario con datos encriptados y metadatos
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        # Comprimir datos si está habilitado
        if self.config.compress_before_encrypt:
            data = zlib.compress(data)
        
        # Generar clave si no se proporciona
        if key is None:
            key = self.generate_key("symmetric")
        
        # Generar IV único
        iv = secrets.token_bytes(12)  # 96 bits para GCM
        
        # Configurar cifrado
        config = self.algorithm_configs[self.config.level]
        cipher = Cipher(
            config['symmetric'](key),
            config['mode'](iv),
            backend=self.backend
        )
        
        encryptor = cipher.encryptor()
        
        # Añadir datos adicionales si se proporcionan
        if additional_data:
            encryptor.authenticate_additional_data(additional_data)
        
        # Encriptar
        ciphertext = encryptor.update(data) + encryptor.finalize()
        
        # Obtener tag de autenticación
        auth_tag = encryptor.tag
        
        result = {
            'ciphertext': base64.b64encode(ciphertext).decode('utf-8'),
            'iv': base64.b64encode(iv).decode('utf-8'),
            'auth_tag': base64.b64encode(auth_tag).decode('utf-8'),
            'algorithm': config['symmetric'].name,
            'key_size': config['key_size'],
            'compressed': self.config.compress_before_encrypt,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if additional_data:
            result['additional_data'] = base64.b64encode(additional_data).decode('utf-8')
        
        return result
    
    def decrypt_data(self, encrypted_data: Dict[str, Any], key: bytes, 
                    additional_data: bytes = None) -> bytes:
        """
        Desencriptar datos
        
        Args:
            encrypted_data: Datos encriptados (del método encrypt_data)
            key: Clave de desencriptación
            additional_data: Datos adicionales para autenticación
            
        Returns:
            Datos desencriptados
        """
        # Extraer componentes
        ciphertext = base64.b64decode(encrypted_data['ciphertext'])
        iv = base64.b64decode(encrypted_data['iv'])
        auth_tag = base64.b64decode(encrypted_data['auth_tag'])
        
        # Configurar descifrado
        config = self.algorithm_configs[self.config.level]
        cipher = Cipher(
            config['symmetric'](key),
            config['mode'](iv, auth_tag),
            backend=self.backend
        )
        
        decryptor = cipher.decryptor()
        
        # Añadir datos adicionales si se proporcionan
        if additional_data:
            decryptor.authenticate_additional_data(additional_data)
        elif 'additional_data' in encrypted_data:
            stored_additional_data = base64.b64decode(encrypted_data['additional_data'])
            decryptor.authenticate_additional_data(stored_additional_data)
        
        # Desencriptar
        plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        
        # Descomprimir si fue comprimido
        if encrypted_data.get('compressed', False):
            plaintext = zlib.decompress(plaintext)
        
        return plaintext
    
    def encrypt_file(self, file_path: Path, output_path: Path = None, 
                    key: bytes = None) -> Dict[str, Any]:
        """
        Encriptar archivo
        
        Args:
            file_path: Ruta del archivo a encriptar
            output_path: Ruta del archivo encriptado (opcional)
            key: Clave de encriptación (opcional)
            
        Returns:
            Metadatos de encriptación
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if output_path is None:
            output_path = file_path.with_suffix(file_path.suffix + '.encrypted')
        
        # Leer archivo
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        # Encriptar
        encrypted_result = self.encrypt_data(file_data, key)
        
        # Añadir metadatos del archivo
        encrypted_result.update({
            'original_filename': file_path.name,
            'original_size': len(file_data),
            'file_hash': hashlib.sha256(file_data).hexdigest()
        })
        
        # Guardar archivo encriptado
        with open(output_path, 'w') as f:
            json.dump(encrypted_result, f, indent=2)
        
        logger.info(f"File encrypted: {file_path} -> {output_path}")
        
        return encrypted_result
    
    def decrypt_file(self, encrypted_file_path: Path, output_path: Path = None, 
                    key: bytes = None) -> Path:
        """
        Desencriptar archivo
        
        Args:
            encrypted_file_path: Ruta del archivo encriptado
            output_path: Ruta del archivo desencriptado (opcional)
            key: Clave de desencriptación
            
        Returns:
            Ruta del archivo desencriptado
        """
        if not encrypted_file_path.exists():
            raise FileNotFoundError(f"Encrypted file not found: {encrypted_file_path}")
        
        # Leer archivo encriptado
        with open(encrypted_file_path, 'r') as f:
            encrypted_data = json.load(f)
        
        if output_path is None:
            original_name = encrypted_data.get('original_filename', 'decrypted_file')
            output_path = encrypted_file_path.parent / original_name
        
        # Desencriptar
        decrypted_data = self.decrypt_data(encrypted_data, key)
        
        # Verificar integridad
        file_hash = hashlib.sha256(decrypted_data).hexdigest()
        expected_hash = encrypted_data.get('file_hash')
        
        if expected_hash and file_hash != expected_hash:
            raise ValueError("File integrity check failed")
        
        # Guardar archivo desencriptado
        with open(output_path, 'wb') as f:
            f.write(decrypted_data)
        
        logger.info(f"File decrypted: {encrypted_file_path} -> {output_path}")
        
        return output_path
    
    def hash_password(self, password: str) -> str:
        """
        Hash de contraseña usando Argon2
        
        Args:
            password: Contraseña en texto plano
            
        Returns:
            Hash de la contraseña
        """
        return self.password_hasher.hash(password)
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """
        Verificar contraseña
        
        Args:
            password: Contraseña en texto plano
            password_hash: Hash almacenado
            
        Returns:
            True si la contraseña es correcta
        """
        try:
            self.password_hasher.verify(password_hash, password)
            return True
        except argon2.exceptions.VerifyMismatchError:
            return False
        except Exception as e:
            logger.error(f"Error verifying password: {e}")
            return False
    
    def generate_hmac(self, data: bytes, key: bytes) -> str:
        """
        Generar HMAC para integridad de datos
        
        Args:
            data: Datos a autenticar
            key: Clave HMAC
            
        Returns:
            HMAC en formato hexadecimal
        """
        h = hmac.new(key, data, hashlib.sha256)
        return h.hexdigest()
    
    def verify_hmac(self, data: bytes, key: bytes, expected_hmac: str) -> bool:
        """
        Verificar HMAC
        
        Args:
            data: Datos originales
            key: Clave HMAC
            expected_hmac: HMAC esperado
            
        Returns:
            True si el HMAC es válido
        """
        calculated_hmac = self.generate_hmac(data, key)
        return hmac.compare_digest(calculated_hmac, expected_hmac)

class DataProtectionManager:
    """
    Gestor de protección de datos con políticas y clasificación
    """
    
    def __init__(self, crypto_manager: CryptographicManager):
        """
        Inicializar gestor de protección de datos
        
        Args:
            crypto_manager: Gestor criptográfico
        """
        self.crypto_manager = crypto_manager
        self.policies: Dict[DataClassification, DataProtectionPolicy] = {}
        self.encryption_keys: Dict[str, bytes] = {}
        self.key_metadata: Dict[str, Dict[str, Any]] = {}
        
        # Configurar políticas por defecto
        self._setup_default_policies()
        
        logger.info("Data protection manager initialized")
    
    def _setup_default_policies(self):
        """Configurar políticas de protección por defecto"""
        self.policies = {
            DataClassification.PUBLIC: DataProtectionPolicy(
                classification=DataClassification.PUBLIC,
                encryption_required=False,
                retention_days=365,
                backup_required=True,
                audit_access=False,
                geographic_restrictions=[],
                allowed_operations=['read', 'write', 'delete', 'share']
            ),
            DataClassification.INTERNAL: DataProtectionPolicy(
                classification=DataClassification.INTERNAL,
                encryption_required=True,
                retention_days=1095,  # 3 años
                backup_required=True,
                audit_access=True,
                geographic_restrictions=[],
                allowed_operations=['read', 'write', 'delete']
            ),
            DataClassification.CONFIDENTIAL: DataProtectionPolicy(
                classification=DataClassification.CONFIDENTIAL,
                encryption_required=True,
                retention_days=2555,  # 7 años
                backup_required=True,
                audit_access=True,
                geographic_restrictions=['US', 'EU'],
                allowed_operations=['read', 'write']
            ),
            DataClassification.RESTRICTED: DataProtectionPolicy(
                classification=DataClassification.RESTRICTED,
                encryption_required=True,
                retention_days=3650,  # 10 años
                backup_required=True,
                audit_access=True,
                geographic_restrictions=['US'],
                allowed_operations=['read']
            ),
            DataClassification.TOP_SECRET: DataProtectionPolicy(
                classification=DataClassification.TOP_SECRET,
                encryption_required=True,
                retention_days=7300,  # 20 años
                backup_required=True,
                audit_access=True,
                geographic_restrictions=[],
                allowed_operations=['read']
            )
        }
    
    def set_policy(self, classification: DataClassification, policy: DataProtectionPolicy):
        """
        Establecer política de protección
        
        Args:
            classification: Clasificación de datos
            policy: Política de protección
        """
        self.policies[classification] = policy
        logger.info(f"Policy set for classification: {classification.value}")
    
    def get_policy(self, classification: DataClassification) -> DataProtectionPolicy:
        """
        Obtener política de protección
        
        Args:
            classification: Clasificación de datos
            
        Returns:
            Política de protección
        """
        return self.policies.get(classification, self.policies[DataClassification.INTERNAL])
    
    def generate_data_key(self, key_id: str, classification: DataClassification) -> bytes:
        """
        Generar clave de datos
        
        Args:
            key_id: Identificador de la clave
            classification: Clasificación de datos
            
        Returns:
            Clave generada
        """
        key = self.crypto_manager.generate_key("symmetric")
        
        # Almacenar clave y metadatos
        self.encryption_keys[key_id] = key
        self.key_metadata[key_id] = {
            'classification': classification.value,
            'created_at': datetime.utcnow().isoformat(),
            'algorithm': 'AES-256-GCM',
            'key_size': len(key) * 8,
            'rotation_due': (datetime.utcnow() + timedelta(days=self.crypto_manager.config.key_rotation_days)).isoformat()
        }
        
        logger.info(f"Data key generated: {key_id} for classification: {classification.value}")
        
        return key
    
    def get_data_key(self, key_id: str) -> Optional[bytes]:
        """
        Obtener clave de datos
        
        Args:
            key_id: Identificador de la clave
            
        Returns:
            Clave si existe, None si no
        """
        return self.encryption_keys.get(key_id)
    
    def rotate_key(self, key_id: str) -> bytes:
        """
        Rotar clave de datos
        
        Args:
            key_id: Identificador de la clave
            
        Returns:
            Nueva clave
        """
        if key_id not in self.key_metadata:
            raise ValueError(f"Key not found: {key_id}")
        
        # Respaldar clave anterior si está habilitado
        if self.crypto_manager.config.backup_keys:
            old_key = self.encryption_keys[key_id]
            backup_key_id = f"{key_id}_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            self.encryption_keys[backup_key_id] = old_key
            self.key_metadata[backup_key_id] = self.key_metadata[key_id].copy()
            self.key_metadata[backup_key_id]['status'] = 'backup'
        
        # Generar nueva clave
        classification = DataClassification(self.key_metadata[key_id]['classification'])
        new_key = self.generate_data_key(key_id, classification)
        
        logger.info(f"Key rotated: {key_id}")
        
        return new_key
    
    def protect_data(self, data: Union[str, bytes], classification: DataClassification,
                    key_id: str = None) -> Dict[str, Any]:
        """
        Proteger datos según su clasificación
        
        Args:
            data: Datos a proteger
            classification: Clasificación de datos
            key_id: Identificador de clave (opcional)
            
        Returns:
            Datos protegidos con metadatos
        """
        policy = self.get_policy(classification)
        
        # Generar key_id si no se proporciona
        if key_id is None:
            key_id = f"key_{classification.value}_{secrets.token_hex(8)}"
        
        result = {
            'classification': classification.value,
            'policy_applied': True,
            'key_id': key_id,
            'protected_at': datetime.utcnow().isoformat()
        }
        
        if policy.encryption_required:
            # Obtener o generar clave
            key = self.get_data_key(key_id)
            if key is None:
                key = self.generate_data_key(key_id, classification)
            
            # Encriptar datos
            encrypted_data = self.crypto_manager.encrypt_data(data, key)
            result.update({
                'encrypted': True,
                'data': encrypted_data
            })
        else:
            # Datos no encriptados
            if isinstance(data, bytes):
                data = base64.b64encode(data).decode('utf-8')
            result.update({
                'encrypted': False,
                'data': data
            })
        
        # Añadir metadatos de política
        result.update({
            'retention_until': (datetime.utcnow() + timedelta(days=policy.retention_days)).isoformat(),
            'backup_required': policy.backup_required,
            'audit_access': policy.audit_access,
            'geographic_restrictions': policy.geographic_restrictions,
            'allowed_operations': policy.allowed_operations
        })
        
        return result
    
    def unprotect_data(self, protected_data: Dict[str, Any]) -> bytes:
        """
        Desproteger datos
        
        Args:
            protected_data: Datos protegidos
            
        Returns:
            Datos originales
        """
        if protected_data.get('encrypted', False):
            key_id = protected_data['key_id']
            key = self.get_data_key(key_id)
            
            if key is None:
                raise ValueError(f"Encryption key not found: {key_id}")
            
            return self.crypto_manager.decrypt_data(protected_data['data'], key)
        else:
            data = protected_data['data']
            if isinstance(data, str):
                return base64.b64decode(data)
            return data
    
    def audit_data_access(self, data_id: str, operation: str, user_id: str,
                         classification: DataClassification) -> Dict[str, Any]:
        """
        Auditar acceso a datos
        
        Args:
            data_id: Identificador de datos
            operation: Operación realizada
            user_id: ID del usuario
            classification: Clasificación de datos
            
        Returns:
            Registro de auditoría
        """
        policy = self.get_policy(classification)
        
        audit_record = {
            'data_id': data_id,
            'operation': operation,
            'user_id': user_id,
            'classification': classification.value,
            'timestamp': datetime.utcnow().isoformat(),
            'allowed': operation in policy.allowed_operations,
            'audit_required': policy.audit_access
        }
        
        if policy.audit_access:
            logger.info(f"Data access audited: {audit_record}")
        
        return audit_record
    
    def check_retention_policy(self, protected_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verificar política de retención
        
        Args:
            protected_data: Datos protegidos
            
        Returns:
            Estado de retención
        """
        retention_until = datetime.fromisoformat(protected_data['retention_until'])
        now = datetime.utcnow()
        
        return {
            'retention_until': protected_data['retention_until'],
            'expired': now > retention_until,
            'days_remaining': (retention_until - now).days if now <= retention_until else 0,
            'should_delete': now > retention_until
        }
    
    def secure_delete(self, data_id: str, passes: int = 3) -> bool:
        """
        Eliminación segura de datos
        
        Args:
            data_id: Identificador de datos
            passes: Número de pasadas de sobrescritura
            
        Returns:
            True si la eliminación fue exitosa
        """
        try:
            # Eliminar clave de encriptación
            if data_id in self.encryption_keys:
                # Sobrescribir clave en memoria
                key = self.encryption_keys[data_id]
                for _ in range(passes):
                    key = secrets.token_bytes(len(key))
                
                del self.encryption_keys[data_id]
                del self.key_metadata[data_id]
            
            logger.info(f"Secure deletion completed for: {data_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error in secure deletion for {data_id}: {e}")
            return False
    
    def export_keys_backup(self, master_password: str) -> Dict[str, Any]:
        """
        Exportar backup de claves
        
        Args:
            master_password: Contraseña maestra para proteger el backup
            
        Returns:
            Backup encriptado de claves
        """
        if not self.crypto_manager.config.backup_keys:
            raise ValueError("Key backup is disabled")
        
        # Preparar datos de backup
        backup_data = {
            'keys': {},
            'metadata': self.key_metadata.copy(),
            'created_at': datetime.utcnow().isoformat(),
            'version': '1.0'
        }
        
        # Encriptar cada clave individualmente
        for key_id, key in self.encryption_keys.items():
            backup_data['keys'][key_id] = base64.b64encode(key).decode('utf-8')
        
        # Encriptar todo el backup con la contraseña maestra
        master_key, salt = self.crypto_manager.derive_key_scrypt(master_password)
        encrypted_backup = self.crypto_manager.encrypt_data(
            json.dumps(backup_data).encode('utf-8'),
            master_key
        )
        
        encrypted_backup['salt'] = base64.b64encode(salt).decode('utf-8')
        encrypted_backup['backup_type'] = 'keys'
        
        logger.info("Keys backup exported successfully")
        
        return encrypted_backup
    
    def import_keys_backup(self, backup_data: Dict[str, Any], master_password: str) -> bool:
        """
        Importar backup de claves
        
        Args:
            backup_data: Datos de backup encriptados
            master_password: Contraseña maestra
            
        Returns:
            True si la importación fue exitosa
        """
        try:
            # Derivar clave maestra
            salt = base64.b64decode(backup_data['salt'])
            master_key, _ = self.crypto_manager.derive_key_scrypt(master_password, salt)
            
            # Desencriptar backup
            decrypted_data = self.crypto_manager.decrypt_data(backup_data, master_key)
            backup_content = json.loads(decrypted_data.decode('utf-8'))
            
            # Restaurar claves
            for key_id, encoded_key in backup_content['keys'].items():
                self.encryption_keys[key_id] = base64.b64decode(encoded_key)
            
            # Restaurar metadatos
            self.key_metadata.update(backup_content['metadata'])
            
            logger.info("Keys backup imported successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error importing keys backup: {e}")
            return False

# Instancias globales
crypto_manager = None
data_protection_manager = None

def initialize_data_protection(config: EncryptionConfig):
    """
    Inicializar sistema de protección de datos
    
    Args:
        config: Configuración de encriptación
    """
    global crypto_manager, data_protection_manager
    
    crypto_manager = CryptographicManager(config)
    data_protection_manager = DataProtectionManager(crypto_manager)
    
    logger.info("Data protection system initialized")

def get_crypto_manager() -> CryptographicManager:
    """
    Obtener gestor criptográfico
    
    Returns:
        Instancia del gestor criptográfico
    """
    if not crypto_manager:
        raise RuntimeError("Data protection system not initialized")
    return crypto_manager

def get_data_protection_manager() -> DataProtectionManager:
    """
    Obtener gestor de protección de datos
    
    Returns:
        Instancia del gestor de protección de datos
    """
    if not data_protection_manager:
        raise RuntimeError("Data protection system not initialized")
    return data_protection_manager

def protect_sensitive_data(data: Union[str, bytes], classification: DataClassification) -> Dict[str, Any]:
    """
    Función de conveniencia para proteger datos sensibles
    
    Args:
        data: Datos a proteger
        classification: Clasificación de datos
        
    Returns:
        Datos protegidos
    """
    manager = get_data_protection_manager()
    return manager.protect_data(data, classification)

def unprotect_sensitive_data(protected_data: Dict[str, Any]) -> bytes:
    """
    Función de conveniencia para desproteger datos
    
    Args:
        protected_data: Datos protegidos
        
    Returns:
        Datos originales
    """
    manager = get_data_protection_manager()
    return manager.unprotect_data(protected_data)

