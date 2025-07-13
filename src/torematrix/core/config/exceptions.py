"""
Exception types for configuration management.
"""

from typing import Optional, List, Dict, Any


class ConfigurationError(Exception):
    """Base exception for configuration errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.details = details or {}


class ValidationError(ConfigurationError):
    """Configuration validation error."""
    
    def __init__(self, message: str, errors: Optional[List[str]] = None):
        super().__init__(message)
        self.errors = errors or []
        self.details = {"validation_errors": self.errors}


class ConfigurationNotFoundError(ConfigurationError):
    """Configuration source not found."""
    
    def __init__(self, path: str):
        super().__init__(f"Configuration not found: {path}")
        self.path = path
        self.details = {"path": path}


class ConfigurationLoadError(ConfigurationError):
    """Error loading configuration from source."""
    
    def __init__(self, source: str, reason: str):
        super().__init__(f"Failed to load configuration from {source}: {reason}")
        self.source = source
        self.reason = reason
        self.details = {"source": source, "reason": reason}


class ConfigurationSaveError(ConfigurationError):
    """Error saving configuration."""
    
    def __init__(self, destination: str, reason: str):
        super().__init__(f"Failed to save configuration to {destination}: {reason}")
        self.destination = destination
        self.reason = reason
        self.details = {"destination": destination, "reason": reason}


class ConfigurationAccessError(ConfigurationError):
    """Error accessing configuration value."""
    
    def __init__(self, key: str, reason: str):
        super().__init__(f"Cannot access configuration key '{key}': {reason}")
        self.key = key
        self.reason = reason
        self.details = {"key": key, "reason": reason}


class ConfigurationLockError(ConfigurationError):
    """Error acquiring configuration lock."""
    
    def __init__(self, timeout: float):
        super().__init__(f"Failed to acquire configuration lock within {timeout}s")
        self.timeout = timeout
        self.details = {"timeout": timeout}