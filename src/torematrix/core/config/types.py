"""
Type definitions for the configuration management system.
"""

from enum import IntEnum
from typing import Any, Dict, Union, Optional, List, TypeVar, Protocol
from pathlib import Path

# Configuration value types
ConfigValue = Union[str, int, float, bool, None, List[Any], Dict[str, Any]]
ConfigDict = Dict[str, ConfigValue]
ConfigPath = Union[str, Path]

# Generic type variable for configuration classes
T = TypeVar('T', bound='BaseConfig')


class ConfigSource(IntEnum):
    """
    Configuration source with precedence (lower value = lower precedence).
    """
    DEFAULT = 1      # Built-in defaults
    FILE = 2         # Configuration files
    ENVIRONMENT = 3  # Environment variables
    RUNTIME = 4      # Runtime modifications
    CLI = 5          # Command-line arguments
    
    def __str__(self) -> str:
        return self.name


class ConfigFormat(IntEnum):
    """Supported configuration file formats."""
    YAML = 1
    JSON = 2
    TOML = 3
    INI = 4
    ENV = 5
    
    def __str__(self) -> str:
        return self.name.lower()


class ConfigUpdatePolicy(IntEnum):
    """Policy for configuration updates."""
    MERGE = 1        # Merge with existing values
    REPLACE = 2      # Replace entire configuration
    MERGE_DEEP = 3   # Deep merge nested structures
    
    def __str__(self) -> str:
        return self.name


class ValidationSeverity(IntEnum):
    """Severity levels for validation errors."""
    WARNING = 1
    ERROR = 2
    CRITICAL = 3
    
    def __str__(self) -> str:
        return self.name


class ConfigProtocol(Protocol):
    """Protocol for configuration objects."""
    
    def to_dict(self) -> ConfigDict:
        """Convert configuration to dictionary."""
        ...
    
    def from_dict(self, data: ConfigDict) -> None:
        """Update configuration from dictionary."""
        ...
    
    def validate(self) -> List[str]:
        """Validate configuration and return errors."""
        ...