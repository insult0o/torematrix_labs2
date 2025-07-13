"""
Configuration encryption and decryption.

This module provides field-level encryption capabilities for sensitive
configuration data using industry-standard cryptography.
"""

from typing import Dict, Any, Optional, Union, Tuple, Set
from pathlib import Path
import json
import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from ..types import ConfigDict
from ..exceptions import ConfigurationError


class ConfigEncryption:
    """
    Handle configuration encryption/decryption.
    
    Features:
    - Field-level encryption
    - Key derivation from password
    - Secure key storage
    - Transparent encryption/decryption
    """
    
    def __init__(self, key: Optional[bytes] = None):
        if key:
            self._cipher = Fernet(key)
        else:
            self._cipher = None
        self._encrypted_fields: Set[str] = set()
    
    @classmethod
    def generate_key(cls) -> bytes:
        """Generate a new encryption key."""
        return Fernet.generate_key()
    
    @classmethod
    def derive_key(cls, password: str, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]:
        """
        Derive encryption key from password.
        
        Returns (key, salt) tuple.
        """
        if salt is None:
            salt = os.urandom(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key, salt
    
    def set_key(self, key: bytes) -> None:
        """Set the encryption key."""
        self._cipher = Fernet(key)
    
    def set_key_from_password(self, password: str, salt: Optional[bytes] = None) -> bytes:
        """
        Set encryption key from password.
        
        Returns the salt used for key derivation.
        """
        key, salt = self.derive_key(password, salt)
        self.set_key(key)
        return salt
    
    def encrypt_value(self, value: Any) -> str:
        """
        Encrypt a single configuration value.
        
        Args:
            value: The value to encrypt
            
        Returns:
            Base64-encoded encrypted string
            
        Raises:
            ConfigurationError: If no encryption key is set
        """
        if not self._cipher:
            raise ConfigurationError("No encryption key set")
        
        # Convert value to JSON string
        json_str = json.dumps(value)
        
        # Encrypt and encode
        encrypted_bytes = self._cipher.encrypt(json_str.encode())
        return base64.urlsafe_b64encode(encrypted_bytes).decode()
    
    def decrypt_value(self, encrypted_value: str) -> Any:
        """
        Decrypt a configuration value.
        
        Args:
            encrypted_value: Base64-encoded encrypted string
            
        Returns:
            The decrypted value
            
        Raises:
            ConfigurationError: If decryption fails
        """
        if not self._cipher:
            raise ConfigurationError("No encryption key set")
        
        try:
            # Decode and decrypt
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_value.encode())
            decrypted_bytes = self._cipher.decrypt(encrypted_bytes)
            
            # Parse JSON
            return json.loads(decrypted_bytes.decode())
        except Exception as e:
            raise ConfigurationError(f"Failed to decrypt value: {e}")
    
    def encrypt_field(self, config: ConfigDict, field_path: str) -> ConfigDict:
        """
        Encrypt a specific field in configuration.
        
        Args:
            config: Configuration dictionary
            field_path: Dot-separated path to field (e.g., "database.password")
            
        Returns:
            Configuration with encrypted field
        """
        result = config.copy()
        
        # Navigate to the field
        path_parts = field_path.split('.')
        current = result
        
        # Navigate to parent
        for part in path_parts[:-1]:
            if part not in current or not isinstance(current[part], dict):
                raise ConfigurationError(f"Field path {field_path} not found")
            current = current[part]
        
        field_name = path_parts[-1]
        if field_name not in current:
            raise ConfigurationError(f"Field {field_path} not found")
        
        # Encrypt the value
        encrypted_value = self.encrypt_value(current[field_name])
        current[field_name] = f"ENC:{encrypted_value}"
        
        # Track encrypted field
        self._encrypted_fields.add(field_path)
        
        return result
    
    def decrypt_field(self, config: ConfigDict, field_path: str) -> ConfigDict:
        """
        Decrypt a specific field in configuration.
        
        Args:
            config: Configuration dictionary
            field_path: Dot-separated path to field
            
        Returns:
            Configuration with decrypted field
        """
        result = config.copy()
        
        # Navigate to the field
        path_parts = field_path.split('.')
        current = result
        
        # Navigate to parent
        for part in path_parts[:-1]:
            if part not in current or not isinstance(current[part], dict):
                raise ConfigurationError(f"Field path {field_path} not found")
            current = current[part]
        
        field_name = path_parts[-1]
        if field_name not in current:
            raise ConfigurationError(f"Field {field_path} not found")
        
        value = current[field_name]
        if isinstance(value, str) and value.startswith("ENC:"):
            # Decrypt the value
            encrypted_value = value[4:]  # Remove "ENC:" prefix
            current[field_name] = self.decrypt_value(encrypted_value)
            
            # Remove from tracked fields
            self._encrypted_fields.discard(field_path)
        
        return result
    
    def encrypt_config(self, config: ConfigDict, field_patterns: Optional[list] = None) -> ConfigDict:
        """
        Encrypt entire configuration or specific field patterns.
        
        Args:
            config: Configuration to encrypt
            field_patterns: List of field patterns to encrypt (default: sensitive fields)
            
        Returns:
            Configuration with encrypted fields
        """
        if field_patterns is None:
            # Default sensitive field patterns
            field_patterns = [
                "password", "secret", "key", "token", "api_key",
                "private_key", "cert", "credential"
            ]
        
        result = config.copy()
        
        # Find and encrypt matching fields
        for field_path in self._find_matching_fields(result, field_patterns):
            try:
                result = self.encrypt_field(result, field_path)
            except ConfigurationError:
                # Skip fields that can't be encrypted
                continue
        
        return result
    
    def decrypt_config(self, config: ConfigDict) -> ConfigDict:
        """
        Decrypt all encrypted fields in configuration.
        
        Args:
            config: Configuration with encrypted fields
            
        Returns:
            Configuration with all fields decrypted
        """
        result = config.copy()
        
        # Find all encrypted fields
        encrypted_fields = self._find_encrypted_fields(result)
        
        for field_path in encrypted_fields:
            try:
                result = self.decrypt_field(result, field_path)
            except ConfigurationError:
                # Skip fields that can't be decrypted
                continue
        
        return result
    
    def is_encrypted(self, value: Any) -> bool:
        """Check if a value is encrypted."""
        return isinstance(value, str) and value.startswith("ENC:")
    
    def get_encrypted_fields(self) -> Set[str]:
        """Get set of currently encrypted field paths."""
        return self._encrypted_fields.copy()
    
    def save_key(self, key_path: Path, key: Optional[bytes] = None) -> None:
        """
        Save encryption key to file.
        
        Args:
            key_path: Path to save key file
            key: Key to save (uses current key if None)
        """
        if key is None:
            if not self._cipher:
                raise ConfigurationError("No key to save")
            key = self._cipher._signing_key + self._cipher._encryption_key
        
        # Ensure directory exists
        key_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write key with restricted permissions
        key_path.write_bytes(key)
        key_path.chmod(0o600)  # Owner read/write only
    
    def load_key(self, key_path: Path) -> None:
        """
        Load encryption key from file.
        
        Args:
            key_path: Path to key file
        """
        if not key_path.exists():
            raise ConfigurationError(f"Key file not found: {key_path}")
        
        key = key_path.read_bytes()
        self.set_key(key)
    
    def _find_matching_fields(self, config: Dict[str, Any], patterns: list, prefix: str = "") -> list:
        """Find field paths matching patterns."""
        matches = []
        
        for key, value in config.items():
            field_path = f"{prefix}.{key}" if prefix else key
            
            # Check if field name matches any pattern
            if any(pattern.lower() in key.lower() for pattern in patterns):
                matches.append(field_path)
            
            # Recursively check nested dictionaries
            if isinstance(value, dict):
                matches.extend(self._find_matching_fields(value, patterns, field_path))
        
        return matches
    
    def _find_encrypted_fields(self, config: Dict[str, Any], prefix: str = "") -> list:
        """Find all encrypted field paths."""
        encrypted = []
        
        for key, value in config.items():
            field_path = f"{prefix}.{key}" if prefix else key
            
            if self.is_encrypted(value):
                encrypted.append(field_path)
            elif isinstance(value, dict):
                encrypted.extend(self._find_encrypted_fields(value, field_path))
        
        return encrypted