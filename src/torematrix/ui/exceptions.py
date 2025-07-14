"""UI-specific exceptions for ToreMatrix V3.

This module defines custom exceptions for UI-related errors,
providing clear error messages and debugging information.
"""

from typing import Optional, Any


class UIError(Exception):
    """Base exception for all UI-related errors."""
    
    def __init__(self, message: str, details: Optional[Any] = None):
        """Initialize UI error.
        
        Args:
            message: Human-readable error message
            details: Additional error details for debugging
        """
        self.message = message
        self.details = details
        super().__init__(self.message)


class WindowInitializationError(UIError):
    """Raised when main window fails to initialize."""
    pass


class LayoutError(UIError):
    """Raised when layout operations fail."""
    pass


class ResourceLoadingError(UIError):
    """Raised when UI resources fail to load."""
    pass


class ThemeError(UIError):
    """Raised when theme operations fail."""
    pass


class StateRestorationError(UIError):
    """Raised when window state restoration fails."""
    pass