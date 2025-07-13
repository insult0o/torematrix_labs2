"""
Configuration Management System for TORE Matrix Labs V3.

This module provides a comprehensive configuration management system with:
- Type-safe configuration models
- Multi-source configuration loading
- Runtime updates and hot reload
- Validation and security features
"""

from .types import ConfigSource, ConfigValue, ConfigDict
from .exceptions import ConfigurationError, ValidationError

# Optional imports that may require additional dependencies
try:
    from .models import ApplicationConfig
    _HAS_MODELS = True
except ImportError:
    ApplicationConfig = None
    _HAS_MODELS = False

try:
    from .manager import ConfigurationManager
    _HAS_MANAGER = True
except ImportError:
    ConfigurationManager = None
    _HAS_MANAGER = False

__all__ = [
    "ConfigSource",
    "ConfigValue", 
    "ConfigDict",
    "ConfigurationError",
    "ValidationError",
]

if _HAS_MODELS:
    __all__.append("ApplicationConfig")
    
if _HAS_MANAGER:
    __all__.append("ConfigurationManager")