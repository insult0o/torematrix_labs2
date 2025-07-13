"""
Secret management for configuration system.

This module provides a unified interface for managing secrets from
various providers including environment variables, files, and external
secret management systems.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union, List
from pathlib import Path
import os
import re
import json
from enum import Enum
from ..types import ConfigDict
from ..exceptions import ConfigurationError


class SecretProvider(ABC):
    """Abstract base class for secret providers."""
    
    @abstractmethod
    def get_secret(self, key: str) -> Optional[str]:
        """
        Retrieve a secret by key.
        
        Args:
            key: Secret identifier
            
        Returns:
            Secret value or None if not found
        """
        pass
    
    @abstractmethod
    def set_secret(self, key: str, value: str) -> None:
        """
        Store a secret.
        
        Args:
            key: Secret identifier
            value: Secret value
        """
        pass
    
    @abstractmethod
    def delete_secret(self, key: str) -> bool:
        """
        Delete a secret.
        
        Args:
            key: Secret identifier
            
        Returns:
            True if secret was deleted, False if not found
        """
        pass
    
    @abstractmethod
    def list_secrets(self) -> List[str]:
        """
        List all available secret keys.
        
        Returns:
            List of secret identifiers
        """
        pass


class EnvironmentSecretProvider(SecretProvider):
    """Secret provider using environment variables."""
    
    def __init__(self, prefix: str = "TORE_SECRET_"):
        self.prefix = prefix
    
    def get_secret(self, key: str) -> Optional[str]:
        """Get secret from environment variable."""
        env_key = f"{self.prefix}{key.upper()}"
        return os.getenv(env_key)
    
    def set_secret(self, key: str, value: str) -> None:
        """Set secret as environment variable."""
        env_key = f"{self.prefix}{key.upper()}"
        os.environ[env_key] = value
    
    def delete_secret(self, key: str) -> bool:
        """Delete secret from environment."""
        env_key = f"{self.prefix}{key.upper()}"
        if env_key in os.environ:
            del os.environ[env_key]
            return True
        return False
    
    def list_secrets(self) -> List[str]:
        """List all secrets with the configured prefix."""
        secrets = []
        for key in os.environ:
            if key.startswith(self.prefix):
                secret_key = key[len(self.prefix):].lower()
                secrets.append(secret_key)
        return secrets


class FileSecretProvider(SecretProvider):
    """Secret provider using JSON files."""
    
    def __init__(self, secrets_file: Path):
        self.secrets_file = Path(secrets_file)
        self._ensure_file_exists()
    
    def _ensure_file_exists(self) -> None:
        """Ensure secrets file exists."""
        if not self.secrets_file.exists():
            self.secrets_file.parent.mkdir(parents=True, exist_ok=True)
            self.secrets_file.write_text("{}")
            self.secrets_file.chmod(0o600)  # Owner read/write only
    
    def _load_secrets(self) -> Dict[str, str]:
        """Load secrets from file."""
        try:
            return json.loads(self.secrets_file.read_text())
        except (json.JSONDecodeError, OSError) as e:
            raise ConfigurationError(f"Failed to load secrets file: {e}")
    
    def _save_secrets(self, secrets: Dict[str, str]) -> None:
        """Save secrets to file."""
        try:
            self.secrets_file.write_text(json.dumps(secrets, indent=2))
            self.secrets_file.chmod(0o600)
        except OSError as e:
            raise ConfigurationError(f"Failed to save secrets file: {e}")
    
    def get_secret(self, key: str) -> Optional[str]:
        """Get secret from file."""
        secrets = self._load_secrets()
        return secrets.get(key)
    
    def set_secret(self, key: str, value: str) -> None:
        """Set secret in file."""
        secrets = self._load_secrets()
        secrets[key] = value
        self._save_secrets(secrets)
    
    def delete_secret(self, key: str) -> bool:
        """Delete secret from file."""
        secrets = self._load_secrets()
        if key in secrets:
            del secrets[key]
            self._save_secrets(secrets)
            return True
        return False
    
    def list_secrets(self) -> List[str]:
        """List all secrets in file."""
        secrets = self._load_secrets()
        return list(secrets.keys())


class SecretManager:
    """
    Unified secret management with multiple providers.
    
    Supports secret interpolation in configuration values using
    various syntax patterns.
    """
    
    # Secret reference patterns
    SECRET_PATTERNS = [
        r'\$\{secret:([^}]+)\}',      # ${secret:key}
        r'\$\{([^}]+)\}',             # ${key}
        r'{{secret\.([^}]+)}}',       # {{secret.key}}
    ]
    
    def __init__(self):
        self.providers: Dict[str, SecretProvider] = {}
        self.default_provider: Optional[str] = None
    
    def register_provider(self, name: str, provider: SecretProvider, is_default: bool = False) -> None:
        """
        Register a secret provider.
        
        Args:
            name: Provider name
            provider: SecretProvider instance
            is_default: Whether this is the default provider
        """
        self.providers[name] = provider
        if is_default or self.default_provider is None:
            self.default_provider = name
    
    def get_secret(self, key: str, provider: Optional[str] = None) -> Optional[str]:
        """
        Get secret from specified or default provider.
        
        Args:
            key: Secret key
            provider: Provider name (uses default if None)
            
        Returns:
            Secret value or None if not found
        """
        provider_name = provider or self.default_provider
        if not provider_name or provider_name not in self.providers:
            raise ConfigurationError(f"Provider '{provider_name}' not found")
        
        return self.providers[provider_name].get_secret(key)
    
    def set_secret(self, key: str, value: str, provider: Optional[str] = None) -> None:
        """
        Set secret in specified or default provider.
        
        Args:
            key: Secret key
            value: Secret value
            provider: Provider name (uses default if None)
        """
        provider_name = provider or self.default_provider
        if not provider_name or provider_name not in self.providers:
            raise ConfigurationError(f"Provider '{provider_name}' not found")
        
        self.providers[provider_name].set_secret(key, value)
    
    def delete_secret(self, key: str, provider: Optional[str] = None) -> bool:
        """
        Delete secret from specified or default provider.
        
        Args:
            key: Secret key
            provider: Provider name (uses default if None)
            
        Returns:
            True if deleted, False if not found
        """
        provider_name = provider or self.default_provider
        if not provider_name or provider_name not in self.providers:
            raise ConfigurationError(f"Provider '{provider_name}' not found")
        
        return self.providers[provider_name].delete_secret(key)
    
    def list_secrets(self, provider: Optional[str] = None) -> List[str]:
        """
        List secrets from specified or default provider.
        
        Args:
            provider: Provider name (uses default if None)
            
        Returns:
            List of secret keys
        """
        provider_name = provider or self.default_provider
        if not provider_name or provider_name not in self.providers:
            raise ConfigurationError(f"Provider '{provider_name}' not found")
        
        return self.providers[provider_name].list_secrets()
    
    def interpolate_secrets(self, config: ConfigDict) -> ConfigDict:
        """
        Interpolate secret references in configuration.
        
        Args:
            config: Configuration with secret references
            
        Returns:
            Configuration with resolved secrets
        """
        return self._interpolate_recursive(config)
    
    def _interpolate_recursive(self, obj: Any) -> Any:
        """Recursively interpolate secrets in data structure."""
        if isinstance(obj, dict):
            return {key: self._interpolate_recursive(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._interpolate_recursive(item) for item in obj]
        elif isinstance(obj, str):
            return self._interpolate_string(obj)
        else:
            return obj
    
    def _interpolate_string(self, value: str) -> str:
        """Interpolate secrets in a string value."""
        result = value
        
        for pattern in self.SECRET_PATTERNS:
            matches = re.finditer(pattern, result)
            for match in reversed(list(matches)):  # Process in reverse to maintain positions
                secret_key = match.group(1)
                secret_value = self._resolve_secret_reference(secret_key)
                
                if secret_value is not None:
                    # Replace the entire match with the secret value
                    start, end = match.span()
                    result = result[:start] + secret_value + result[end:]
                else:
                    # Leave unresolved references as-is or raise error
                    if self._should_fail_on_missing_secret():
                        raise ConfigurationError(f"Secret '{secret_key}' not found")
        
        return result
    
    def _resolve_secret_reference(self, reference: str) -> Optional[str]:
        """
        Resolve a secret reference.
        
        Reference can be:
        - key: Use default provider
        - provider:key: Use specific provider
        """
        if ':' in reference:
            provider, key = reference.split(':', 1)
            return self.get_secret(key, provider)
        else:
            return self.get_secret(reference)
    
    def _should_fail_on_missing_secret(self) -> bool:
        """Whether to fail when a secret is not found."""
        return os.getenv('TORE_FAIL_ON_MISSING_SECRETS', 'false').lower() == 'true'
    
    def has_secret_references(self, config: ConfigDict) -> bool:
        """
        Check if configuration contains secret references.
        
        Args:
            config: Configuration to check
            
        Returns:
            True if secret references found
        """
        return self._has_references_recursive(config)
    
    def _has_references_recursive(self, obj: Any) -> bool:
        """Recursively check for secret references."""
        if isinstance(obj, dict):
            return any(self._has_references_recursive(value) for value in obj.values())
        elif isinstance(obj, list):
            return any(self._has_references_recursive(item) for item in obj)
        elif isinstance(obj, str):
            return any(re.search(pattern, obj) for pattern in self.SECRET_PATTERNS)
        else:
            return False
    
    def sanitize_config(self, config: ConfigDict) -> ConfigDict:
        """
        Sanitize configuration by replacing secret values with placeholders.
        
        Args:
            config: Configuration to sanitize
            
        Returns:
            Configuration with secrets masked
        """
        return self._sanitize_recursive(config)
    
    def _sanitize_recursive(self, obj: Any) -> Any:
        """Recursively sanitize data structure."""
        if isinstance(obj, dict):
            return {key: self._sanitize_recursive(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._sanitize_recursive(item) for item in obj]
        elif isinstance(obj, str):
            # Check if this looks like a secret value
            if self._is_secret_value(obj):
                return "[REDACTED]"
            return obj
        else:
            return obj
    
    def _is_secret_value(self, value: str) -> bool:
        """Check if a value looks like a secret."""
        # Heuristics for detecting secret-like values
        if len(value) < 8:  # Too short to be a meaningful secret
            return False
        
        # Check for common secret patterns
        secret_indicators = [
            'key', 'token', 'secret', 'password', 'pass', 'pwd',
            'credential', 'auth', 'api', 'bearer'
        ]
        
        # If it looks like base64 or hex and is long enough
        if len(value) > 20:
            # Base64-like (alphanumeric + / + =)
            if re.match(r'^[A-Za-z0-9+/]+=*$', value):
                return True
            # Hex-like
            if re.match(r'^[0-9a-fA-F]+$', value):
                return True
        
        return False