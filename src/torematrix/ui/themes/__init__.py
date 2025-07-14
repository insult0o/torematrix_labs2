"""Theme Framework for TORE Matrix Labs V3.

This package provides a comprehensive theme management system with:
- Core theme engine for loading and switching themes
- Color palette and typography management
- Qt StyleSheet generation and caching
- Icon theming and accessibility features
- Hot reload support for development
"""

from .engine import ThemeEngine
from .base import Theme, ThemeProvider, ColorPalette, Typography
from .types import ThemeType, ThemeFormat, ComponentType
from .exceptions import ThemeError, ThemeNotFoundError, ThemeValidationError

__all__ = [
    # Core engine
    'ThemeEngine',
    
    # Base classes
    'Theme',
    'ThemeProvider', 
    'ColorPalette',
    'Typography',
    
    # Type definitions
    'ThemeType',
    'ThemeFormat',
    'ComponentType',
    
    # Exceptions
    'ThemeError',
    'ThemeNotFoundError',
    'ThemeValidationError',
]

__version__ = "1.0.0"