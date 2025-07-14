"""
Tests for PDF integration exceptions.
"""

import pytest
from torematrix.integrations.pdf.exceptions import (
    PDFIntegrationError,
    PDFLoadError,
    PDFRenderError,
    PDFNavigationError,
    PDFZoomError,
    PDFJSError,
    PDFWebEngineError
)


class TestPDFIntegrationError:
    """Test base PDFIntegrationError class."""
    
    def test_basic_error(self):
        """Test basic error creation."""
        error = PDFIntegrationError("Test error")
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.error_code is None
    
    def test_error_with_code(self):
        """Test error with error code."""
        error = PDFIntegrationError("Test error", "TEST_CODE")
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.error_code == "TEST_CODE"


class TestPDFLoadError:
    """Test PDFLoadError class."""
    
    def test_basic_load_error(self):
        """Test basic load error."""
        error = PDFLoadError("Load failed")
        assert str(error) == "Load failed"
        assert error.message == "Load failed"
        assert error.file_path is None
        assert error.error_code is None
    
    def test_load_error_with_file_path(self):
        """Test load error with file path."""
        error = PDFLoadError("Load failed", "/path/to/file.pdf")
        assert str(error) == "Load failed"
        assert error.file_path == "/path/to/file.pdf"
    
    def test_load_error_with_all_params(self):
        """Test load error with all parameters."""
        error = PDFLoadError("Load failed", "/path/to/file.pdf", "FILE_NOT_FOUND")
        assert str(error) == "Load failed"
        assert error.file_path == "/path/to/file.pdf"
        assert error.error_code == "FILE_NOT_FOUND"


class TestPDFRenderError:
    """Test PDFRenderError class."""
    
    def test_basic_render_error(self):
        """Test basic render error."""
        error = PDFRenderError("Render failed")
        assert str(error) == "Render failed"
        assert error.page_number is None
    
    def test_render_error_with_page(self):
        """Test render error with page number."""
        error = PDFRenderError("Render failed", 5)
        assert str(error) == "Render failed"
        assert error.page_number == 5
    
    def test_render_error_with_all_params(self):
        """Test render error with all parameters."""
        error = PDFRenderError("Render failed", 5, "RENDER_TIMEOUT")
        assert str(error) == "Render failed"
        assert error.page_number == 5
        assert error.error_code == "RENDER_TIMEOUT"


class TestPDFNavigationError:
    """Test PDFNavigationError class."""
    
    def test_basic_navigation_error(self):
        """Test basic navigation error."""
        error = PDFNavigationError("Navigation failed")
        assert str(error) == "Navigation failed"
        assert error.requested_page is None
        assert error.current_page is None
    
    def test_navigation_error_with_pages(self):
        """Test navigation error with page numbers."""
        error = PDFNavigationError("Navigation failed", 10, 5)
        assert str(error) == "Navigation failed"
        assert error.requested_page == 10
        assert error.current_page == 5
    
    def test_navigation_error_with_all_params(self):
        """Test navigation error with all parameters."""
        error = PDFNavigationError("Navigation failed", 10, 5, "PAGE_OUT_OF_RANGE")
        assert str(error) == "Navigation failed"
        assert error.requested_page == 10
        assert error.current_page == 5
        assert error.error_code == "PAGE_OUT_OF_RANGE"


class TestPDFZoomError:
    """Test PDFZoomError class."""
    
    def test_basic_zoom_error(self):
        """Test basic zoom error."""
        error = PDFZoomError("Zoom failed")
        assert str(error) == "Zoom failed"
        assert error.requested_zoom is None
        assert error.current_zoom is None
    
    def test_zoom_error_with_levels(self):
        """Test zoom error with zoom levels."""
        error = PDFZoomError("Zoom failed", 2.0, 1.5)
        assert str(error) == "Zoom failed"
        assert error.requested_zoom == 2.0
        assert error.current_zoom == 1.5
    
    def test_zoom_error_with_all_params(self):
        """Test zoom error with all parameters."""
        error = PDFZoomError("Zoom failed", 2.0, 1.5, "ZOOM_OUT_OF_RANGE")
        assert str(error) == "Zoom failed"
        assert error.requested_zoom == 2.0
        assert error.current_zoom == 1.5
        assert error.error_code == "ZOOM_OUT_OF_RANGE"


class TestPDFJSError:
    """Test PDFJSError class."""
    
    def test_basic_js_error(self):
        """Test basic JavaScript error."""
        error = PDFJSError("JS error")
        assert str(error) == "JS error"
        assert error.js_error is None
    
    def test_js_error_with_js_error(self):
        """Test JavaScript error with JS error object."""
        js_error = {"name": "ReferenceError", "message": "loadPDF is not defined"}
        error = PDFJSError("JS error", js_error)
        assert str(error) == "JS error"
        assert error.js_error == js_error
    
    def test_js_error_with_all_params(self):
        """Test JavaScript error with all parameters."""
        js_error = {"name": "ReferenceError", "message": "loadPDF is not defined"}
        error = PDFJSError("JS error", js_error, "JS_NOT_READY")
        assert str(error) == "JS error"
        assert error.js_error == js_error
        assert error.error_code == "JS_NOT_READY"


class TestPDFWebEngineError:
    """Test PDFWebEngineError class."""
    
    def test_basic_web_engine_error(self):
        """Test basic web engine error."""
        error = PDFWebEngineError("Web engine error")
        assert str(error) == "Web engine error"
        assert error.web_error is None
    
    def test_web_engine_error_with_web_error(self):
        """Test web engine error with web error object."""
        web_error = Exception("Settings not available")
        error = PDFWebEngineError("Web engine error", web_error)
        assert str(error) == "Web engine error"
        assert error.web_error == web_error
    
    def test_web_engine_error_with_all_params(self):
        """Test web engine error with all parameters."""
        web_error = Exception("Settings not available")
        error = PDFWebEngineError("Web engine error", web_error, "WEB_ENGINE_NOT_READY")
        assert str(error) == "Web engine error"
        assert error.web_error == web_error
        assert error.error_code == "WEB_ENGINE_NOT_READY"


class TestExceptionInheritance:
    """Test exception inheritance hierarchy."""
    
    def test_inheritance_hierarchy(self):
        """Test that all exceptions inherit from PDFIntegrationError."""
        # Test PDFLoadError
        error = PDFLoadError("test")
        assert isinstance(error, PDFIntegrationError)
        assert isinstance(error, Exception)
        
        # Test PDFRenderError
        error = PDFRenderError("test")
        assert isinstance(error, PDFIntegrationError)
        assert isinstance(error, Exception)
        
        # Test PDFNavigationError
        error = PDFNavigationError("test")
        assert isinstance(error, PDFIntegrationError)
        assert isinstance(error, Exception)
        
        # Test PDFZoomError
        error = PDFZoomError("test")
        assert isinstance(error, PDFIntegrationError)
        assert isinstance(error, Exception)
        
        # Test PDFJSError
        error = PDFJSError("test")
        assert isinstance(error, PDFIntegrationError)
        assert isinstance(error, Exception)
        
        # Test PDFWebEngineError
        error = PDFWebEngineError("test")
        assert isinstance(error, PDFIntegrationError)
        assert isinstance(error, Exception)
    
    def test_exception_catching(self):
        """Test that exceptions can be caught by base class."""
        # Test PDFLoadError can be caught as PDFIntegrationError
        try:
            raise PDFLoadError("test")
        except PDFIntegrationError:
            pass  # Should catch
        
        # Test PDFRenderError can be caught as PDFIntegrationError
        try:
            raise PDFRenderError("test")
        except PDFIntegrationError:
            pass  # Should catch
        
        # Test all exceptions can be caught as Exception
        try:
            raise PDFNavigationError("test")
        except Exception:
            pass  # Should catch