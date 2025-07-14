"""
Comprehensive tests for PDF.js core viewer functionality.

This module tests the Agent 1 foundation components:
- PDFDocument class
- PDFViewer class
- PDF loading and error handling
- Navigation controls
- Zoom functionality
- Integration interfaces
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QUrl
from PyQt6.QtWebEngineCore import QWebEnginePage

from torematrix.integrations.pdf.viewer import PDFViewer, PDFDocument
from torematrix.integrations.pdf.exceptions import (
    PDFLoadError, PDFNavigationError, PDFZoomError, PDFJSError, PDFWebEngineError
)


class TestPDFDocument:
    """Test PDFDocument class functionality."""
    
    def test_document_creation(self):
        """Test document object creation with default values."""
        file_path = Path("test.pdf")
        doc = PDFDocument(file_path)
        
        assert doc.file_path == file_path
        assert doc.url is None
        assert doc.page_count == 0
        assert doc.title == ""
        assert doc.author == ""
        assert doc.subject == ""
        assert doc.creator == ""
        assert doc.producer == ""
        assert doc.creation_date is None
        assert doc.modification_date is None
        assert doc.current_page == 1
        assert doc.zoom_level == 1.0
        assert not doc.is_loaded
        assert doc.loading_progress == 0.0
        assert doc.error_message is None
    
    def test_document_with_url(self):
        """Test document creation with URL."""
        file_path = Path("test.pdf")
        url = "https://example.com/test.pdf"
        doc = PDFDocument(file_path, url)
        
        assert doc.file_path == file_path
        assert doc.url == url
    
    def test_update_metadata(self, sample_pdf_metadata):
        """Test metadata update from PDF.js."""
        file_path = Path("test.pdf")
        doc = PDFDocument(file_path)
        
        doc.update_metadata(sample_pdf_metadata)
        
        assert doc.title == sample_pdf_metadata['title']
        assert doc.author == sample_pdf_metadata['author']
        assert doc.subject == sample_pdf_metadata['subject']
        assert doc.creator == sample_pdf_metadata['creator']
        assert doc.producer == sample_pdf_metadata['producer']
        assert doc.creation_date == sample_pdf_metadata['creationDate']
        assert doc.modification_date == sample_pdf_metadata['modificationDate']
        assert doc.page_count == sample_pdf_metadata['pages']
        assert doc.metadata == sample_pdf_metadata
    
    def test_document_serialization(self):
        """Test document serialization to dictionary."""
        file_path = Path("test.pdf")
        doc = PDFDocument(file_path)
        doc.page_count = 10
        doc.current_page = 5
        doc.zoom_level = 1.5
        doc.is_loaded = True
        doc.loading_progress = 1.0
        doc.title = "Test Document"
        doc.author = "Test Author"
        
        data = doc.to_dict()
        
        assert data['file_path'] == str(file_path)
        assert data['page_count'] == 10
        assert data['current_page'] == 5
        assert data['zoom_level'] == 1.5
        assert data['is_loaded'] is True
        assert data['loading_progress'] == 1.0
        assert data['title'] == "Test Document"
        assert data['author'] == "Test Author"
        assert data['url'] is None
        assert data['error_message'] is None
    
    def test_partial_metadata_update(self):
        """Test metadata update with partial data."""
        file_path = Path("test.pdf")
        doc = PDFDocument(file_path)
        
        partial_metadata = {
            'title': 'Partial Title',
            'pages': 5
        }
        
        doc.update_metadata(partial_metadata)
        
        assert doc.title == 'Partial Title'
        assert doc.page_count == 5
        assert doc.author == ''  # Should remain empty
        assert doc.subject == ''


class TestPDFViewer:
    """Test PDFViewer class functionality."""
    
    @pytest.fixture
    def viewer(self, app):
        """Create PDFViewer instance for testing."""
        with patch('torematrix.integrations.pdf.viewer.PDFViewer._initialize_pdfjs'):
            viewer = PDFViewer()
            viewer.page = Mock(spec=QWebEnginePage)
            viewer.page().runJavaScript = Mock()
            viewer.page().loadFinished = Mock()
            viewer.page().loadProgress = Mock()
            return viewer
    
    def test_viewer_initialization(self, viewer):
        """Test viewer initialization with default values."""
        assert viewer.min_zoom == 0.1
        assert viewer.max_zoom == 10.0
        assert viewer.zoom_step == 0.25
        assert viewer.default_zoom == 1.0
        assert viewer.current_document is None
        assert viewer._bridge is None
        assert viewer._performance_config is None
        assert viewer._enabled_features is None
        assert not viewer._is_loading
    
    def test_load_pdf_success(self, viewer, temp_pdf_path):
        """Test successful PDF loading."""
        # Mock JavaScript execution
        viewer.page().runJavaScript.return_value = None
        
        # Mock the PDF load result
        mock_result = {
            'success': True,
            'pages': 5,
            'metadata': {
                'title': 'Test PDF',
                'author': 'Test Author',
                'pages': 5
            }
        }
        
        with patch.object(viewer, '_handle_pdf_load_result') as mock_handler:
            mock_handler.side_effect = lambda result: viewer._handle_pdf_load_result(mock_result)
            
            # Load PDF
            viewer.load_pdf(temp_pdf_path)
            
            # Verify document creation
            assert viewer.current_document is not None
            assert viewer.current_document.file_path == temp_pdf_path
            assert viewer._is_loading is True
            
            # Verify JavaScript call
            assert viewer.page().runJavaScript.called
            call_args = viewer.page().runJavaScript.call_args[0][0]
            assert 'loadPDF' in call_args
            assert str(temp_pdf_path) in call_args
    
    def test_load_nonexistent_file(self, viewer):
        """Test loading non-existent file raises error."""
        nonexistent_path = Path("nonexistent.pdf")
        
        with pytest.raises(PDFLoadError) as exc_info:
            viewer.load_pdf(nonexistent_path)
        
        assert "PDF file not found" in str(exc_info.value)
        assert exc_info.value.error_code == "FILE_NOT_FOUND"
        assert exc_info.value.file_path == str(nonexistent_path)
    
    def test_load_non_pdf_file(self, viewer):
        """Test loading non-PDF file raises error."""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b"Not a PDF file")
            f.flush()
            
            txt_path = Path(f.name)
            
            try:
                with pytest.raises(PDFLoadError) as exc_info:
                    viewer.load_pdf(txt_path)
                
                assert "File is not a PDF" in str(exc_info.value)
                assert exc_info.value.error_code == "INVALID_FILE_TYPE"
            finally:
                txt_path.unlink(missing_ok=True)
    
    def test_pdf_load_result_success(self, viewer, temp_pdf_path):
        """Test successful PDF load result handling."""
        # Setup document
        viewer.current_document = PDFDocument(temp_pdf_path)
        
        # Mock successful result
        result = {
            'success': True,
            'pages': 5,
            'metadata': {
                'title': 'Test PDF',
                'author': 'Test Author',
                'pages': 5
            }
        }
        
        # Handle result
        viewer._handle_pdf_load_result(result)
        
        # Verify document update
        assert viewer.current_document.is_loaded is True
        assert viewer.current_document.page_count == 5
        assert viewer.current_document.title == 'Test PDF'
        assert viewer.current_document.author == 'Test Author'
        assert viewer.current_document.loading_progress == 1.0
    
    def test_pdf_load_result_failure(self, viewer, temp_pdf_path):
        """Test PDF load result failure handling."""
        # Setup document
        viewer.current_document = PDFDocument(temp_pdf_path)
        
        # Mock failure result
        result = {
            'success': False,
            'error': 'PDF parsing failed',
            'errorType': 'PARSE_ERROR'
        }
        
        # Handle result
        viewer._handle_pdf_load_result(result)
        
        # Verify error handling
        assert viewer.current_document.error_message == 'PDF parsing failed'
    
    def test_close_document(self, viewer, temp_pdf_path):
        """Test document closure and cleanup."""
        # Setup document
        viewer.current_document = PDFDocument(temp_pdf_path)
        viewer.current_document.is_loaded = True
        
        # Close document
        viewer.close_document()
        
        # Verify cleanup
        assert viewer.current_document is None
        assert not viewer._is_loading
        assert viewer.page().runJavaScript.called
    
    def test_navigation_controls(self, viewer, temp_pdf_path):
        """Test page navigation functionality."""
        # Setup loaded document
        viewer.current_document = PDFDocument(temp_pdf_path)
        viewer.current_document.is_loaded = True
        viewer.current_document.page_count = 10
        viewer.current_document.current_page = 5
        
        # Test go_to_page
        result = viewer.go_to_page(7)
        assert result is True
        assert viewer.current_document.current_page == 7
        assert viewer.page().runJavaScript.called
        
        # Test next_page
        result = viewer.next_page()
        assert result is True
        assert viewer.current_document.current_page == 8
        
        # Test previous_page
        result = viewer.previous_page()
        assert result is True
        assert viewer.current_document.current_page == 7
        
        # Test first_page
        result = viewer.first_page()
        assert result is True
        assert viewer.current_document.current_page == 1
        
        # Test last_page
        result = viewer.last_page()
        assert result is True
        assert viewer.current_document.current_page == 10
    
    def test_navigation_invalid_page(self, viewer, temp_pdf_path):
        """Test navigation to invalid page raises error."""
        # Setup loaded document
        viewer.current_document = PDFDocument(temp_pdf_path)
        viewer.current_document.is_loaded = True
        viewer.current_document.page_count = 10
        viewer.current_document.current_page = 5
        
        # Test invalid page number
        with pytest.raises(PDFNavigationError) as exc_info:
            viewer.go_to_page(15)
        
        assert "out of range" in str(exc_info.value)
        assert exc_info.value.requested_page == 15
        assert exc_info.value.current_page == 5
    
    def test_navigation_no_document(self, viewer):
        """Test navigation without loaded document."""
        # Test navigation without document
        result = viewer.go_to_page(5)
        assert result is False
        
        result = viewer.next_page()
        assert result is False
        
        result = viewer.previous_page()
        assert result is False
    
    def test_zoom_controls(self, viewer, temp_pdf_path):
        """Test zoom functionality."""
        # Setup loaded document
        viewer.current_document = PDFDocument(temp_pdf_path)
        viewer.current_document.is_loaded = True
        viewer.current_document.zoom_level = 1.0
        
        # Test set_zoom
        result = viewer.set_zoom(1.5)
        assert result is True
        assert viewer.current_document.zoom_level == 1.5
        assert viewer.page().runJavaScript.called
        
        # Test zoom_in
        result = viewer.zoom_in()
        assert result is True
        assert viewer.current_document.zoom_level == 1.75
        
        # Test zoom_out
        result = viewer.zoom_out()
        assert result is True
        assert viewer.current_document.zoom_level == 1.5
        
        # Test reset_zoom
        result = viewer.reset_zoom()
        assert result is True
        assert viewer.current_document.zoom_level == 1.0
    
    def test_zoom_limits(self, viewer, temp_pdf_path):
        """Test zoom level limits."""
        # Setup loaded document
        viewer.current_document = PDFDocument(temp_pdf_path)
        viewer.current_document.is_loaded = True
        viewer.current_document.zoom_level = 1.0
        
        # Test minimum zoom
        result = viewer.set_zoom(0.05)  # Below minimum
        assert result is True
        assert viewer.current_document.zoom_level == viewer.min_zoom
        
        # Test maximum zoom
        result = viewer.set_zoom(15.0)  # Above maximum
        assert result is True
        assert viewer.current_document.zoom_level == viewer.max_zoom
    
    def test_zoom_no_document(self, viewer):
        """Test zoom without loaded document."""
        # Test zoom without document
        result = viewer.set_zoom(1.5)
        assert result is False
        
        result = viewer.zoom_in()
        assert result is False
        
        result = viewer.zoom_out()
        assert result is False
    
    def test_fit_controls(self, viewer, temp_pdf_path):
        """Test fit width and fit page functionality."""
        # Setup loaded document
        viewer.current_document = PDFDocument(temp_pdf_path)
        viewer.current_document.is_loaded = True
        
        # Test fit_width
        result = viewer.fit_width()
        assert result is True
        assert viewer.page().runJavaScript.called
        
        # Test fit_page
        result = viewer.fit_page()
        assert result is True
        assert viewer.page().runJavaScript.called
    
    def test_fit_no_document(self, viewer):
        """Test fit controls without loaded document."""
        # Test fit without document
        result = viewer.fit_width()
        assert result is False
        
        result = viewer.fit_page()
        assert result is False
    
    def test_document_info_methods(self, viewer, temp_pdf_path):
        """Test document information methods."""
        # Test with no document
        assert viewer.get_document_info() is None
        assert not viewer.is_document_loaded()
        assert viewer.get_current_page() == 0
        assert viewer.get_page_count() == 0
        assert viewer.get_zoom_level() == 1.0
        
        # Setup loaded document
        viewer.current_document = PDFDocument(temp_pdf_path)
        viewer.current_document.is_loaded = True
        viewer.current_document.page_count = 10
        viewer.current_document.current_page = 5
        viewer.current_document.zoom_level = 1.5
        
        # Test with document
        doc_info = viewer.get_document_info()
        assert doc_info is not None
        assert doc_info['page_count'] == 10
        assert doc_info['current_page'] == 5
        assert doc_info['zoom_level'] == 1.5
        assert doc_info['is_loaded'] is True
        
        assert viewer.is_document_loaded() is True
        assert viewer.get_current_page() == 5
        assert viewer.get_page_count() == 10
        assert viewer.get_zoom_level() == 1.5
    
    def test_integration_interfaces(self, viewer):
        """Test integration interfaces for other agents."""
        # Test bridge attachment (Agent 2)
        mock_bridge = Mock()
        viewer.attach_bridge(mock_bridge)
        assert viewer._bridge is mock_bridge
        
        # Test performance config (Agent 3)
        config = {'cache_size': 100, 'preload_pages': 3}
        viewer.set_performance_config(config)
        assert viewer._performance_config == config
        
        # Test feature enablement (Agent 4)
        features = ['search', 'annotations', 'print']
        viewer.enable_features(features)
        assert viewer._enabled_features == features
    
    def test_cleanup_temp_files(self, viewer):
        """Test temporary file cleanup."""
        # Create temporary files
        with tempfile.NamedTemporaryFile(delete=False) as f1:
            temp_path1 = f1.name
        with tempfile.NamedTemporaryFile(delete=False) as f2:
            temp_path2 = f2.name
        
        # Add to viewer's temp files
        viewer._temp_files = [temp_path1, temp_path2]
        
        # Cleanup
        viewer._cleanup_temp_files()
        
        # Verify cleanup
        assert len(viewer._temp_files) == 0
        assert not Path(temp_path1).exists()
        assert not Path(temp_path2).exists()
    
    def test_signal_connections(self, viewer):
        """Test that signals are properly defined."""
        # Test signal existence
        assert hasattr(viewer, 'document_loaded')
        assert hasattr(viewer, 'document_loading')
        assert hasattr(viewer, 'load_error')
        assert hasattr(viewer, 'page_changed')
        assert hasattr(viewer, 'zoom_changed')
        assert hasattr(viewer, 'render_error')
        
        # Test signal emission (mock required for actual testing)
        mock_handler = Mock()
        viewer.page_changed.connect(mock_handler)
        viewer.page_changed.emit(5)
        mock_handler.assert_called_once_with(5)
    
    def test_web_engine_setup(self, app):
        """Test web engine configuration."""
        with patch('torematrix.integrations.pdf.viewer.PDFViewer._initialize_pdfjs'):
            viewer = PDFViewer()
            
            # Test that settings are configured
            settings = viewer.settings()
            assert settings is not None
            
            # Verify JavaScript is enabled
            from PyQt6.QtWebEngineWidgets import QWebEngineSettings
            assert settings.testAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled)
            assert settings.testAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls)
    
    def test_load_with_string_path(self, viewer, temp_pdf_path):
        """Test loading PDF with string path."""
        # Convert to string
        pdf_path_str = str(temp_pdf_path)
        
        # Mock JavaScript execution
        viewer.page().runJavaScript.return_value = None
        
        # Load PDF
        viewer.load_pdf(pdf_path_str)
        
        # Verify document creation
        assert viewer.current_document is not None
        assert viewer.current_document.file_path == Path(pdf_path_str)
    
    def test_error_handling_in_methods(self, viewer):
        """Test error handling in various methods."""
        # Test with invalid document state
        viewer.current_document = None
        
        # Navigation should return False
        assert viewer.go_to_page(1) is False
        assert viewer.next_page() is False
        assert viewer.previous_page() is False
        assert viewer.first_page() is False
        assert viewer.last_page() is False
        
        # Zoom should return False
        assert viewer.set_zoom(1.5) is False
        assert viewer.zoom_in() is False
        assert viewer.zoom_out() is False
        assert viewer.reset_zoom() is False
        
        # Fit should return False
        assert viewer.fit_width() is False
        assert viewer.fit_page() is False


class TestPDFViewerExceptionHandling:
    """Test exception handling in PDFViewer."""
    
    @pytest.fixture
    def viewer(self, app):
        """Create PDFViewer instance with exception testing setup."""
        with patch('torematrix.integrations.pdf.viewer.PDFViewer._initialize_pdfjs'):
            viewer = PDFViewer()
            viewer.page = Mock(spec=QWebEnginePage)
            viewer.page().runJavaScript = Mock()
            return viewer
    
    def test_web_engine_setup_failure(self, app):
        """Test web engine setup failure handling."""
        with patch('torematrix.integrations.pdf.viewer.PDFViewer._initialize_pdfjs'):
            with patch('torematrix.integrations.pdf.viewer.PDFViewer.settings') as mock_settings:
                mock_settings.side_effect = Exception("Settings error")
                
                with pytest.raises(PDFWebEngineError):
                    PDFViewer()
    
    def test_pdfjs_initialization_failure(self, app):
        """Test PDF.js initialization failure handling."""
        with patch('pathlib.Path.exists', return_value=False):
            with pytest.raises(PDFJSError):
                PDFViewer()
    
    def test_javascript_execution_failure(self, viewer, temp_pdf_path):
        """Test JavaScript execution failure handling."""
        # Setup document
        viewer.current_document = PDFDocument(temp_pdf_path)
        viewer.current_document.is_loaded = True
        viewer.current_document.page_count = 10
        
        # Mock JavaScript failure
        viewer.page().runJavaScript.side_effect = Exception("JS Error")
        
        # Navigation should raise exception
        with pytest.raises(PDFNavigationError):
            viewer.go_to_page(5)
        
        # Zoom should raise exception
        with pytest.raises(PDFZoomError):
            viewer.set_zoom(1.5)
    
    def test_invalid_pdf_load_result(self, viewer, temp_pdf_path):
        """Test invalid PDF load result handling."""
        # Setup document
        viewer.current_document = PDFDocument(temp_pdf_path)
        
        # Test with None result
        viewer._handle_pdf_load_result(None)
        
        # Test with invalid result format
        viewer._handle_pdf_load_result("invalid_result")
        
        # Test with empty result
        viewer._handle_pdf_load_result({})
    
    def test_close_event_error_handling(self, viewer):
        """Test error handling during close event."""
        # Mock close_document to raise exception
        with patch.object(viewer, 'close_document', side_effect=Exception("Close error")):
            # Should not raise exception
            viewer.closeEvent(Mock())


class TestPDFViewerIntegration:
    """Test PDFViewer integration with other components."""
    
    @pytest.fixture
    def viewer(self, app):
        """Create PDFViewer instance for integration testing."""
        with patch('torematrix.integrations.pdf.viewer.PDFViewer._initialize_pdfjs'):
            viewer = PDFViewer()
            viewer.page = Mock(spec=QWebEnginePage)
            viewer.page().runJavaScript = Mock()
            viewer.page().loadFinished = Mock()
            viewer.page().loadProgress = Mock()
            return viewer
    
    def test_page_load_signals(self, viewer):
        """Test web page load signal handling."""
        # Test successful page load
        viewer._on_page_loaded(True)
        
        # Test failed page load
        viewer._on_page_loaded(False)
    
    def test_load_progress_signals(self, viewer):
        """Test load progress signal handling."""
        # Set loading state
        viewer._is_loading = True
        
        # Test progress updates
        viewer._on_page_load_progress(25)
        viewer._on_page_load_progress(50)
        viewer._on_page_load_progress(100)
        
        # Test without loading state
        viewer._is_loading = False
        viewer._on_page_load_progress(50)
    
    def test_javascript_communication_setup(self, viewer):
        """Test JavaScript communication setup."""
        # Test that communication is properly initialized
        assert hasattr(viewer, '_js_callbacks')
        assert isinstance(viewer._js_callbacks, dict)
    
    def test_agent_integration_workflow(self, viewer):
        """Test the complete agent integration workflow."""
        # Agent 1 foundation is ready
        assert viewer.current_document is None
        assert viewer._bridge is None
        assert viewer._performance_config is None
        assert viewer._enabled_features is None
        
        # Agent 2 attaches bridge
        mock_bridge = Mock()
        viewer.attach_bridge(mock_bridge)
        assert viewer._bridge is mock_bridge
        
        # Agent 3 sets performance config
        perf_config = {'cache_size': 100, 'preload_pages': 3}
        viewer.set_performance_config(perf_config)
        assert viewer._performance_config == perf_config
        
        # Agent 4 enables features
        features = ['search', 'annotations', 'print']
        viewer.enable_features(features)
        assert viewer._enabled_features == features
        
        # All agents have integrated successfully
        assert viewer._bridge is not None
        assert viewer._performance_config is not None
        assert viewer._enabled_features is not None