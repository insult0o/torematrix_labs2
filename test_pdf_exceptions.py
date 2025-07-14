#!/usr/bin/env python3
"""
Test PDF exceptions without PyQt6 dependencies.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_exceptions_only():
    """Test just the exceptions module without PyQt6."""
    try:
        # Import directly from exceptions module
        from torematrix.integrations.pdf.exceptions import (
            PDFIntegrationError,
            PDFLoadError,
            PDFRenderError,
            PDFNavigationError,
            PDFZoomError,
            PDFJSError,
            PDFWebEngineError
        )
        
        print("✅ All exception classes imported successfully")
        
        # Test PDFLoadError
        error = PDFLoadError("Test error", "/path/to/file.pdf", "FILE_NOT_FOUND")
        assert str(error) == "Test error"
        assert error.file_path == "/path/to/file.pdf"
        assert error.error_code == "FILE_NOT_FOUND"
        assert error.message == "Test error"
        
        # Test PDFRenderError
        render_error = PDFRenderError("Render failed", 5, "RENDER_TIMEOUT")
        assert str(render_error) == "Render failed"
        assert render_error.page_number == 5
        assert render_error.error_code == "RENDER_TIMEOUT"
        
        # Test PDFNavigationError
        nav_error = PDFNavigationError("Navigation failed", 10, 5, "PAGE_OUT_OF_RANGE")
        assert str(nav_error) == "Navigation failed"
        assert nav_error.requested_page == 10
        assert nav_error.current_page == 5
        assert nav_error.error_code == "PAGE_OUT_OF_RANGE"
        
        # Test PDFZoomError
        zoom_error = PDFZoomError("Zoom failed", 2.0, 1.5, "ZOOM_OUT_OF_RANGE")
        assert str(zoom_error) == "Zoom failed"
        assert zoom_error.requested_zoom == 2.0
        assert zoom_error.current_zoom == 1.5
        assert zoom_error.error_code == "ZOOM_OUT_OF_RANGE"
        
        # Test PDFJSError
        js_error = PDFJSError("JS error", {"name": "ReferenceError"}, "JS_NOT_READY")
        assert str(js_error) == "JS error"
        assert js_error.js_error == {"name": "ReferenceError"}
        assert js_error.error_code == "JS_NOT_READY"
        
        # Test PDFWebEngineError
        web_error = PDFWebEngineError("Web engine error", Exception("test"), "WEB_ENGINE_NOT_READY")
        assert str(web_error) == "Web engine error"
        assert web_error.error_code == "WEB_ENGINE_NOT_READY"
        
        print("✅ Exception creation and attributes work correctly")
        
        # Test inheritance
        assert isinstance(error, PDFIntegrationError)
        assert isinstance(error, Exception)
        assert isinstance(render_error, PDFIntegrationError)
        assert isinstance(nav_error, PDFIntegrationError)
        assert isinstance(zoom_error, PDFIntegrationError)
        assert isinstance(js_error, PDFIntegrationError)
        assert isinstance(web_error, PDFIntegrationError)
        
        print("✅ Exception inheritance hierarchy works correctly")
        
        # Test exception catching
        try:
            raise PDFLoadError("test")
        except PDFIntegrationError:
            pass  # Should catch
        
        try:
            raise PDFRenderError("test")
        except PDFIntegrationError:
            pass  # Should catch
        
        print("✅ Exception catching works correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Exception test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run exception tests."""
    print("🚀 Testing PDF Exception Classes")
    print("=" * 40)
    
    if test_exceptions_only():
        print("🎉 All exception tests passed!")
        return True
    else:
        print("❌ Exception tests failed")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)