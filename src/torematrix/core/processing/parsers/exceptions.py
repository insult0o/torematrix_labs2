"""Parser-specific exceptions."""

from typing import List, Optional, Dict, Any


class ParserError(Exception):
    """Base exception for parser errors."""
    
    def __init__(self, message: str, parser_name: Optional[str] = None, 
                 element_type: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.parser_name = parser_name
        self.element_type = element_type
        self.details = details or {}
        
    def __str__(self) -> str:
        base = super().__str__()
        if self.parser_name:
            base = f"[{self.parser_name}] {base}"
        if self.element_type:
            base = f"{base} (element: {self.element_type})"
        return base


class ValidationError(ParserError):
    """Raised when element validation fails."""
    
    def __init__(self, message: str, validation_errors: List[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.validation_errors = validation_errors or []


class ConfigurationError(ParserError):
    """Raised when parser configuration is invalid."""
    pass


class UnsupportedElementError(ParserError):
    """Raised when parser cannot handle the element type."""
    
    def __init__(self, element_type: str, parser_name: str, supported_types: List[str] = None):
        message = f"Parser '{parser_name}' does not support element type '{element_type}'"
        if supported_types:
            message += f". Supported types: {', '.join(supported_types)}"
        super().__init__(message, parser_name=parser_name, element_type=element_type)
        self.supported_types = supported_types or []


class ProcessingTimeoutError(ParserError):
    """Raised when parsing operation times out."""
    
    def __init__(self, timeout_seconds: float, parser_name: str = None):
        message = f"Parsing operation timed out after {timeout_seconds} seconds"
        super().__init__(message, parser_name=parser_name)
        self.timeout_seconds = timeout_seconds


class MemoryLimitError(ParserError):
    """Raised when parser exceeds memory limits."""
    
    def __init__(self, memory_used: int, memory_limit: int, parser_name: str = None):
        message = f"Parser exceeded memory limit: {memory_used} > {memory_limit} bytes"
        super().__init__(message, parser_name=parser_name)
        self.memory_used = memory_used
        self.memory_limit = memory_limit


class LanguageDetectionError(ParserError):
    """Raised when language detection fails."""
    
    def __init__(self, text_sample: str = None, attempted_languages: List[str] = None, **kwargs):
        message = "Failed to detect language"
        if attempted_languages:
            message += f" (tried: {', '.join(attempted_languages)})"
        super().__init__(message, **kwargs)
        self.text_sample = text_sample
        self.attempted_languages = attempted_languages or []


class SyntaxValidationError(ParserError):
    """Raised when syntax validation fails for code elements."""
    
    def __init__(self, syntax_errors: List[str], language: str = None, **kwargs):
        message = f"Syntax validation failed: {'; '.join(syntax_errors)}"
        if language:
            message = f"[{language}] {message}"
        super().__init__(message, **kwargs)
        self.syntax_errors = syntax_errors
        self.language = language


class StructureExtractionError(ParserError):
    """Raised when structure extraction fails."""
    
    def __init__(self, structure_type: str, reason: str, **kwargs):
        message = f"Failed to extract {structure_type} structure: {reason}"
        super().__init__(message, **kwargs)
        self.structure_type = structure_type
        self.reason = reason


class CacheError(ParserError):
    """Raised when cache operations fail."""
    
    def __init__(self, operation: str, cache_type: str, reason: str, **kwargs):
        message = f"Cache {operation} failed for {cache_type}: {reason}"
        super().__init__(message, **kwargs)
        self.operation = operation
        self.cache_type = cache_type
        self.reason = reason


class MonitoringError(ParserError):
    """Raised when monitoring operations fail."""
    
    def __init__(self, metric_name: str, reason: str, **kwargs):
        message = f"Failed to record metric '{metric_name}': {reason}"
        super().__init__(message, **kwargs)
        self.metric_name = metric_name
        self.reason = reason