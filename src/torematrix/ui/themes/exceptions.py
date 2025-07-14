"""Theme-specific exceptions."""


class ThemeError(Exception):
    """Base class for all theme-related errors."""
    
    def __init__(self, message: str, theme_name: str = None):
        super().__init__(message)
        self.theme_name = theme_name
        

class ThemeNotFoundError(ThemeError):
    """Raised when a requested theme cannot be found."""
    
    def __init__(self, theme_name: str):
        super().__init__(f"Theme '{theme_name}' not found", theme_name)
        

class ThemeValidationError(ThemeError):
    """Raised when theme data fails validation."""
    
    def __init__(self, message: str, theme_name: str = None, field: str = None):
        super().__init__(message, theme_name)
        self.field = field
        

class ThemeLoadError(ThemeError):
    """Raised when theme loading fails."""
    
    def __init__(self, theme_name: str, reason: str):
        super().__init__(f"Failed to load theme '{theme_name}': {reason}", theme_name)
        self.reason = reason
        

class ThemeFormatError(ThemeError):
    """Raised when theme file format is invalid or unsupported."""
    
    def __init__(self, file_path: str, reason: str):
        super().__init__(f"Invalid theme file format '{file_path}': {reason}")
        self.file_path = file_path
        self.reason = reason
        

class StyleSheetGenerationError(ThemeError):
    """Raised when stylesheet generation fails."""
    
    def __init__(self, theme_name: str, component: str, reason: str):
        super().__init__(
            f"Failed to generate stylesheet for '{component}' in theme '{theme_name}': {reason}",
            theme_name
        )
        self.component = component
        self.reason = reason