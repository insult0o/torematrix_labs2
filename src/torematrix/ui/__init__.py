"""ToreMatrix UI Framework.

This module provides the user interface components for ToreMatrix V3,
built on PyQt6 with modern patterns and cross-platform support.
"""

from .main_window import MainWindow, create_application
from .base import BaseUIComponent, BaseUIWidget, UIError

__all__ = [
    # Main window
    'MainWindow',
    'create_application',
    
    # Base components
    'BaseUIComponent',
    'BaseUIWidget', 
    'UIError',
]

# Version info
__version__ = '3.0.0'