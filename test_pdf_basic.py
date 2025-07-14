#!/usr/bin/env python3
"""
Basic test of PDF.js integration components without PyQt6.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_exceptions():
    """Test exception imports and basic functionality."""
    try:
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
        
        # Test basic exception creation
        error = PDFLoadError("Test error", "/path/to/file.pdf", "FILE_NOT_FOUND")
        assert str(error) == "Test error"
        assert error.file_path == "/path/to/file.pdf"
        assert error.error_code == "FILE_NOT_FOUND"
        
        print("✅ Exception creation and attributes work correctly")
        
        # Test inheritance
        assert isinstance(error, PDFIntegrationError)
        assert isinstance(error, Exception)
        
        print("✅ Exception inheritance hierarchy works correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Exception test failed: {e}")
        return False


def test_file_structure():
    """Test that all required files exist."""
    required_files = [
        "resources/pdfjs/viewer.html",
        "resources/pdfjs/viewer.js",
        "resources/pdfjs/pdf.min.js",
        "resources/pdfjs/pdf.worker.min.js",
        "src/torematrix/integrations/pdf/__init__.py",
        "src/torematrix/integrations/pdf/viewer.py",
        "src/torematrix/integrations/pdf/exceptions.py",
        "tests/unit/pdf/test_viewer.py",
        "tests/unit/pdf/test_exceptions.py",
        "tests/unit/pdf/conftest.py",
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    
    print("✅ All required files exist")
    return True


def test_javascript_viewer():
    """Test JavaScript viewer file content."""
    try:
        viewer_js = Path("resources/pdfjs/viewer.js")
        content = viewer_js.read_text()
        
        # Check for required functions
        required_functions = [
            "loadPDF",
            "renderPage",
            "goToPage",
            "nextPage",
            "prevPage",
            "setZoom",
            "zoomIn",
            "zoomOut",
            "fitWidth",
            "fitPage",
            "clearViewer"
        ]
        
        missing_functions = []
        for func in required_functions:
            if f"function {func}" not in content:
                missing_functions.append(func)
        
        if missing_functions:
            print(f"❌ Missing JavaScript functions: {missing_functions}")
            return False
        
        print("✅ JavaScript viewer has all required functions")
        return True
        
    except Exception as e:
        print(f"❌ JavaScript viewer test failed: {e}")
        return False


def test_html_viewer():
    """Test HTML viewer file content."""
    try:
        viewer_html = Path("resources/pdfjs/viewer.html")
        content = viewer_html.read_text()
        
        # Check for required elements
        required_elements = [
            "viewerContainer",
            "viewer",
            "pdf.min.js",
            "viewer.js"
        ]
        
        missing_elements = []
        for element in required_elements:
            if element not in content:
                missing_elements.append(element)
        
        if missing_elements:
            print(f"❌ Missing HTML elements: {missing_elements}")
            return False
        
        print("✅ HTML viewer has all required elements")
        return True
        
    except Exception as e:
        print(f"❌ HTML viewer test failed: {e}")
        return False


def main():
    """Run all basic tests."""
    print("🚀 Running Agent 1 PDF.js Core Viewer Foundation Tests")
    print("=" * 60)
    
    tests = [
        ("File Structure", test_file_structure),
        ("Exception Classes", test_exceptions),
        ("JavaScript Viewer", test_javascript_viewer),
        ("HTML Viewer", test_html_viewer),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Testing {test_name}...")
        if test_func():
            passed += 1
        else:
            print(f"❌ {test_name} failed")
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All Agent 1 foundation tests passed!")
        print("✅ Ready for Agent 2 handoff")
        return True
    else:
        print("❌ Some tests failed")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)