"""
Configuration Management System for TORE Matrix Labs V3.

This module provides a comprehensive configuration management system with:
- Type-safe configuration models
- Multi-source configuration loading
- Runtime updates and hot reload
- Validation and security features
"""

from .types import ConfigSource, ConfigValue, ConfigDict
from .models import ApplicationConfig
from .manager import ConfigurationManager
from .exceptions import ConfigurationError, ValidationError

__all__ = [
    "ConfigSource",
    "ConfigValue",
    "ConfigDict",
    "ApplicationConfig",
    "ConfigurationManager",
    "ConfigurationError",
    "ValidationError",
]