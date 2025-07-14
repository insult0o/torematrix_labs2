"""
PDF integration exceptions.

This module defines all exceptions used in the PDF.js integration system.
"""

from typing import Optional, Any


class PDFIntegrationError(Exception):
    """Base exception for PDF integration errors."""
    
    def __init__(self, message: str, error_code: Optional[str] = None):
        super().__init__(message)
        self.error_code = error_code
        self.message = message


class PDFLoadError(PDFIntegrationError):
    """Exception raised when PDF loading fails."""
    
    def __init__(self, message: str, file_path: Optional[str] = None, 
                 error_code: Optional[str] = None):
        super().__init__(message, error_code)
        self.file_path = file_path


class PDFRenderError(PDFIntegrationError):
    """Exception raised when PDF rendering fails."""
    
    def __init__(self, message: str, page_number: Optional[int] = None,
                 error_code: Optional[str] = None):
        super().__init__(message, error_code)
        self.page_number = page_number


class PDFNavigationError(PDFIntegrationError):
    """Exception raised when PDF navigation fails."""
    
    def __init__(self, message: str, requested_page: Optional[int] = None,
                 current_page: Optional[int] = None, error_code: Optional[str] = None):
        super().__init__(message, error_code)
        self.requested_page = requested_page
        self.current_page = current_page


class PDFZoomError(PDFIntegrationError):
    """Exception raised when PDF zoom operations fail."""
    
    def __init__(self, message: str, requested_zoom: Optional[float] = None,
                 current_zoom: Optional[float] = None, error_code: Optional[str] = None):
        super().__init__(message, error_code)
        self.requested_zoom = requested_zoom
        self.current_zoom = current_zoom


class PDFJSError(PDFIntegrationError):
    """Exception raised for PDF.js specific errors."""
    
    def __init__(self, message: str, js_error: Optional[Any] = None,
                 error_code: Optional[str] = None):
        super().__init__(message, error_code)
        self.js_error = js_error


class PDFWebEngineError(PDFIntegrationError):
    """Exception raised for QWebEngine specific errors."""
    
    def __init__(self, message: str, web_error: Optional[Any] = None,
                 error_code: Optional[str] = None):
        super().__init__(message, error_code)
        self.web_error = web_error