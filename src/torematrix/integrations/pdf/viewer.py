"""
Core PDF.js viewer integration with PyQt6.

This module provides the foundational PDFViewer class that embeds PDF.js
in a QWebEngineView for high-performance PDF rendering and basic controls.

Agent 1 Implementation:
- Core PDF viewer with Qt integration
- Basic navigation and zoom controls
- PDF loading and error handling
- Integration interfaces for other agents

Future Agent Extensions:
- Agent 2: Qt-JavaScript bridge communication
- Agent 3: Performance optimization and caching
- Agent 4: Advanced features and UI integration
"""

from __future__ import annotations

import logging
import tempfile
import json
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
from urllib.parse import urljoin

from PyQt6.QtCore import QUrl, QTimer, pyqtSignal, QObject, QThread
from PyQt6.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSlider
from PyQt6.QtGui import QFont

from .exceptions import (
    PDFLoadError, PDFRenderError, PDFNavigationError, 
    PDFZoomError, PDFJSError, PDFWebEngineError
)

logger = logging.getLogger(__name__)


class PDFDocument:
    """Represents a loaded PDF document with metadata and state."""
    
    def __init__(self, file_path: Path, url: Optional[str] = None):
        """Initialize PDF document.
        
        Args:
            file_path: Path to PDF file
            url: Optional URL if loaded from web
        """
        self.file_path = file_path
        self.url = url
        self.page_count: int = 0
        self.title: str = ""
        self.author: str = ""
        self.subject: str = ""
        self.creator: str = ""
        self.producer: str = ""
        self.creation_date: Optional[str] = None
        self.modification_date: Optional[str] = None
        self.metadata: Dict[str, Any] = {}
        self.current_page: int = 1
        self.zoom_level: float = 1.0
        self.is_loaded: bool = False
        self.loading_progress: float = 0.0
        self.error_message: Optional[str] = None
    
    def update_metadata(self, metadata: Dict[str, Any]) -> None:
        """Update document metadata from PDF.js."""
        self.metadata = metadata
        self.title = metadata.get('title', '')
        self.author = metadata.get('author', '')
        self.subject = metadata.get('subject', '')
        self.creator = metadata.get('creator', '')
        self.producer = metadata.get('producer', '')
        self.creation_date = metadata.get('creationDate')
        self.modification_date = metadata.get('modificationDate')
        self.page_count = metadata.get('pages', 0)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize document state."""
        return {
            'file_path': str(self.file_path),
            'url': self.url,
            'page_count': self.page_count,
            'title': self.title,
            'author': self.author,
            'subject': self.subject,
            'creator': self.creator,
            'producer': self.producer,
            'creation_date': self.creation_date,
            'modification_date': self.modification_date,
            'current_page': self.current_page,
            'zoom_level': self.zoom_level,
            'is_loaded': self.is_loaded,
            'loading_progress': self.loading_progress,
            'error_message': self.error_message
        }


class PDFViewer(QWebEngineView):
    """
    Core PDF.js viewer widget integrated with PyQt6.
    
    Provides high-performance PDF rendering using PDF.js embedded in
    QWebEngineView with support for basic navigation and zoom controls.
    
    This is the Agent 1 foundation implementation that provides:
    - PDF loading and error handling
    - Basic navigation (next/prev/goto page)
    - Zoom controls (zoom in/out/fit width/fit page)
    - Keyboard shortcuts
    - Integration interfaces for other agents
    
    Signals:
        document_loaded: Emitted when PDF is successfully loaded
        document_loading: Emitted during PDF loading with progress
        load_error: Emitted when PDF loading fails
        page_changed: Emitted when current page changes
        zoom_changed: Emitted when zoom level changes
        render_error: Emitted when page rendering fails
    """
    
    # Signals
    document_loaded = pyqtSignal(PDFDocument)
    document_loading = pyqtSignal(float)  # loading progress 0.0-1.0
    load_error = pyqtSignal(str, str)  # error_code, error_message
    page_changed = pyqtSignal(int)  # new_page_number
    zoom_changed = pyqtSignal(float)  # new_zoom_level
    render_error = pyqtSignal(int, str)  # page_number, error_message
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize PDF viewer.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Document management
        self.current_document: Optional[PDFDocument] = None
        self._temp_files: List[str] = []
        
        # Configuration
        self.min_zoom = 0.1
        self.max_zoom = 10.0
        self.zoom_step = 0.25
        self.default_zoom = 1.0
        
        # State tracking
        self._is_loading = False
        self._last_load_time = 0
        
        # Agent integration interfaces
        self._bridge = None  # Will be set by Agent 2
        self._performance_config = None  # Will be set by Agent 3
        self._enabled_features = None  # Will be set by Agent 4
        
        # Initialize web engine
        self._setup_web_engine()
        
        # Initialize PDF.js
        self._initialize_pdfjs()
        
        # Setup JavaScript communication
        self._setup_js_communication()
        
        logger.info("PDFViewer initialized successfully")
    
    def _setup_web_engine(self) -> None:
        """Configure QWebEngine settings for optimal PDF viewing."""
        try:
            # Get profile and settings
            profile = QWebEngineProfile.defaultProfile()
            settings = self.settings()
            
            # Enable JavaScript (required for PDF.js)
            settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
            
            # Enable local file access
            settings.setAttribute(
                QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True
            )
            settings.setAttribute(
                QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True
            )
            
            # Optimize for PDF viewing
            settings.setAttribute(
                QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, True
            )
            settings.setAttribute(
                QWebEngineSettings.WebAttribute.SpatialNavigationEnabled, False
            )
            
            # Performance settings
            settings.setAttribute(
                QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True
            )
            settings.setAttribute(
                QWebEngineSettings.WebAttribute.WebGLEnabled, True
            )
            settings.setAttribute(
                QWebEngineSettings.WebAttribute.PluginsEnabled, False
            )
            settings.setAttribute(
                QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, False
            )
            settings.setAttribute(
                QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, False
            )
            
            # Security settings
            settings.setAttribute(
                QWebEngineSettings.WebAttribute.LocalStorageEnabled, True
            )
            settings.setAttribute(
                QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, False
            )
            
            logger.debug("Web engine configured successfully")
            
        except Exception as e:
            logger.error(f"Failed to configure web engine: {e}")
            raise PDFWebEngineError(f"Web engine configuration failed: {e}")
    
    def _initialize_pdfjs(self) -> None:
        """Initialize PDF.js viewer."""
        try:
            # Get viewer HTML path
            viewer_path = Path(__file__).parent.parent.parent.parent / "resources" / "pdfjs" / "viewer.html"
            
            if not viewer_path.exists():
                raise FileNotFoundError(f"PDF.js viewer not found at {viewer_path}")
            
            # Load viewer
            viewer_url = QUrl.fromLocalFile(str(viewer_path))
            self.setUrl(viewer_url)
            
            logger.info(f"PDF.js viewer loaded from {viewer_path}")
            
        except Exception as e:
            logger.error(f"Failed to initialize PDF.js: {e}")
            raise PDFJSError(f"PDF.js initialization failed: {e}")
    
    def _setup_js_communication(self) -> None:
        """Setup JavaScript communication handlers."""
        try:
            # Connect to web page signals
            self.page().loadFinished.connect(self._on_page_loaded)
            self.page().loadProgress.connect(self._on_page_load_progress)
            
            # Setup JavaScript result handlers
            self._js_callbacks: Dict[str, callable] = {}
            
            logger.debug("JavaScript communication setup completed")
            
        except Exception as e:
            logger.error(f"Failed to setup JavaScript communication: {e}")
            raise PDFWebEngineError(f"JavaScript communication setup failed: {e}")
    
    def _on_page_loaded(self, success: bool) -> None:
        """Handle web page load completion."""
        if success:
            logger.debug("PDF.js viewer page loaded successfully")
        else:
            logger.error("PDF.js viewer page failed to load")
            self.load_error.emit("PAGE_LOAD_FAILED", "PDF.js viewer page failed to load")
    
    def _on_page_load_progress(self, progress: int) -> None:
        """Handle web page load progress."""
        if self._is_loading:
            self.document_loading.emit(progress / 100.0)
    
    def load_pdf(self, file_path: Union[str, Path]) -> None:
        """
        Load a PDF file for viewing.
        
        Args:
            file_path: Path to PDF file
            
        Raises:
            PDFLoadError: If PDF loading fails
        """
        try:
            # Convert to Path object
            if isinstance(file_path, str):
                file_path = Path(file_path)
            
            # Validate file exists
            if not file_path.exists():
                error_msg = f"PDF file not found: {file_path}"
                logger.error(error_msg)
                self.load_error.emit("FILE_NOT_FOUND", error_msg)
                raise PDFLoadError(error_msg, str(file_path), "FILE_NOT_FOUND")
            
            # Validate file is PDF
            if not file_path.suffix.lower() == '.pdf':
                error_msg = f"File is not a PDF: {file_path}"
                logger.error(error_msg)
                self.load_error.emit("INVALID_FILE_TYPE", error_msg)
                raise PDFLoadError(error_msg, str(file_path), "INVALID_FILE_TYPE")
            
            # Set loading state
            self._is_loading = True
            self.document_loading.emit(0.0)
            
            # Close existing document
            if self.current_document:
                self.close_document()
            
            # Create document object
            document = PDFDocument(file_path)
            
            # Load PDF via JavaScript
            pdf_url = QUrl.fromLocalFile(str(file_path)).toString()
            js_code = f"""
                (function() {{
                    if (typeof loadPDF === 'function') {{
                        loadPDF('{pdf_url}').then(function(result) {{
                            if (result.success) {{
                                console.log('PDF loaded successfully');
                                window.qt_pdf_load_result = result;
                            }} else {{
                                console.error('PDF loading failed:', result.error);
                                window.qt_pdf_load_result = result;
                            }}
                        }}).catch(function(error) {{
                            console.error('PDF loading error:', error);
                            window.qt_pdf_load_result = {{ success: false, error: error.message }};
                        }});
                    }} else {{
                        console.error('PDF.js not ready');
                        window.qt_pdf_load_result = {{ success: false, error: 'PDF.js not ready' }};
                    }}
                }})();
            """
            
            # Execute JavaScript and handle result
            self.page().runJavaScript(js_code, self._on_pdf_load_complete)
            
            # Store current document
            self.current_document = document
            
            logger.info(f"Loading PDF: {file_path}")
            
        except Exception as e:
            self._is_loading = False
            error_msg = f"Failed to load PDF: {e}"
            logger.error(error_msg)
            self.load_error.emit("LOAD_FAILED", error_msg)
            raise PDFLoadError(error_msg, str(file_path), "LOAD_FAILED")
    
    def _on_pdf_load_complete(self, result: Any) -> None:
        """Handle PDF load completion from JavaScript."""
        self._is_loading = False
        
        try:
            # Get result from JavaScript
            js_code = "window.qt_pdf_load_result"
            self.page().runJavaScript(js_code, self._handle_pdf_load_result)
            
        except Exception as e:
            logger.error(f"Failed to get PDF load result: {e}")
            self.load_error.emit("RESULT_FAILED", str(e))
    
    def _handle_pdf_load_result(self, result: Any) -> None:
        """Handle PDF load result from JavaScript."""
        try:
            if result and isinstance(result, dict):
                if result.get('success'):
                    # Update document metadata
                    if self.current_document:
                        metadata = result.get('metadata', {})
                        self.current_document.update_metadata(metadata)
                        self.current_document.is_loaded = True
                        self.current_document.loading_progress = 1.0
                        
                        # Emit success signal
                        self.document_loaded.emit(self.current_document)
                        logger.info(f"PDF loaded successfully: {self.current_document.title}")
                else:
                    # Handle error
                    error_msg = result.get('error', 'Unknown error')
                    error_type = result.get('errorType', 'JS_LOAD_FAILED')
                    
                    if self.current_document:
                        self.current_document.error_message = error_msg
                    
                    logger.error(f"PDF loading failed: {error_msg}")
                    self.load_error.emit(error_type, error_msg)
            else:
                error_msg = "Invalid PDF load result"
                logger.error(error_msg)
                self.load_error.emit("INVALID_RESULT", error_msg)
                
        except Exception as e:
            error_msg = f"Error processing PDF load result: {e}"
            logger.error(error_msg)
            self.load_error.emit("RESULT_PROCESSING_FAILED", error_msg)
    
    def close_document(self) -> None:
        """Close current document and cleanup resources."""
        if self.current_document:
            logger.info(f"Closing document: {self.current_document.file_path}")
            self.current_document = None
        
        # Cleanup temporary files
        self._cleanup_temp_files()
        
        # Clear viewer
        js_code = """
            if (typeof clearViewer === 'function') {
                clearViewer();
            }
        """
        self.page().runJavaScript(js_code)
        
        # Reset loading state
        self._is_loading = False
    
    # Navigation methods
    def go_to_page(self, page_number: int) -> bool:
        """Navigate to specific page.
        
        Args:
            page_number: Page number to navigate to (1-based)
            
        Returns:
            True if navigation was successful
            
        Raises:
            PDFNavigationError: If navigation fails
        """
        if not self.current_document or not self.current_document.is_loaded:
            logger.warning("Cannot navigate - no document loaded")
            return False
        
        if page_number < 1 or page_number > self.current_document.page_count:
            error_msg = f"Page number {page_number} out of range (1-{self.current_document.page_count})"
            logger.error(error_msg)
            raise PDFNavigationError(error_msg, page_number, self.current_document.current_page)
        
        try:
            js_code = f"""
                if (typeof goToPage === 'function') {{
                    goToPage({page_number});
                }}
            """
            self.page().runJavaScript(js_code)
            
            # Update current page
            old_page = self.current_document.current_page
            self.current_document.current_page = page_number
            
            # Emit signal
            self.page_changed.emit(page_number)
            
            logger.debug(f"Navigated from page {old_page} to {page_number}")
            return True
            
        except Exception as e:
            error_msg = f"Navigation failed: {e}"
            logger.error(error_msg)
            raise PDFNavigationError(error_msg, page_number, self.current_document.current_page)
    
    def next_page(self) -> bool:
        """Navigate to next page."""
        if self.current_document and self.current_document.current_page < self.current_document.page_count:
            return self.go_to_page(self.current_document.current_page + 1)
        return False
    
    def previous_page(self) -> bool:
        """Navigate to previous page."""
        if self.current_document and self.current_document.current_page > 1:
            return self.go_to_page(self.current_document.current_page - 1)
        return False
    
    def first_page(self) -> bool:
        """Navigate to first page."""
        return self.go_to_page(1)
    
    def last_page(self) -> bool:
        """Navigate to last page."""
        if self.current_document:
            return self.go_to_page(self.current_document.page_count)
        return False
    
    # Zoom methods
    def set_zoom(self, zoom_level: float) -> bool:
        """Set zoom level.
        
        Args:
            zoom_level: Zoom level (0.1 to 10.0)
            
        Returns:
            True if zoom was set successfully
            
        Raises:
            PDFZoomError: If zoom setting fails
        """
        if not self.current_document or not self.current_document.is_loaded:
            logger.warning("Cannot zoom - no document loaded")
            return False
        
        # Clamp zoom level
        zoom_level = max(self.min_zoom, min(self.max_zoom, zoom_level))
        
        try:
            js_code = f"""
                if (typeof setZoom === 'function') {{
                    setZoom({zoom_level});
                }}
            """
            self.page().runJavaScript(js_code)
            
            # Update zoom level
            old_zoom = self.current_document.zoom_level
            self.current_document.zoom_level = zoom_level
            
            # Emit signal
            self.zoom_changed.emit(zoom_level)
            
            logger.debug(f"Zoom changed from {old_zoom} to {zoom_level}")
            return True
            
        except Exception as e:
            error_msg = f"Zoom setting failed: {e}"
            logger.error(error_msg)
            raise PDFZoomError(error_msg, zoom_level, self.current_document.zoom_level)
    
    def zoom_in(self) -> bool:
        """Increase zoom level."""
        if self.current_document:
            current_zoom = self.current_document.zoom_level
            new_zoom = min(self.max_zoom, current_zoom + self.zoom_step)
            return self.set_zoom(new_zoom)
        return False
    
    def zoom_out(self) -> bool:
        """Decrease zoom level."""
        if self.current_document:
            current_zoom = self.current_document.zoom_level
            new_zoom = max(self.min_zoom, current_zoom - self.zoom_step)
            return self.set_zoom(new_zoom)
        return False
    
    def reset_zoom(self) -> bool:
        """Reset zoom to default level."""
        return self.set_zoom(self.default_zoom)
    
    def fit_width(self) -> bool:
        """Fit PDF to container width."""
        if not self.current_document or not self.current_document.is_loaded:
            return False
        
        try:
            js_code = "if (typeof fitWidth === 'function') { fitWidth(); }"
            self.page().runJavaScript(js_code)
            return True
        except Exception as e:
            logger.error(f"Fit width failed: {e}")
            return False
    
    def fit_page(self) -> bool:
        """Fit full page in view."""
        if not self.current_document or not self.current_document.is_loaded:
            return False
        
        try:
            js_code = "if (typeof fitPage === 'function') { fitPage(); }"
            self.page().runJavaScript(js_code)
            return True
        except Exception as e:
            logger.error(f"Fit page failed: {e}")
            return False
    
    # Integration interfaces for other agents
    def attach_bridge(self, bridge: Any) -> None:
        """Interface for Agent 2 to attach communication bridge.
        
        Args:
            bridge: QWebChannel bridge instance
        """
        self._bridge = bridge
        logger.info("Bridge attached by Agent 2")
    
    def set_performance_config(self, config: Dict[str, Any]) -> None:
        """Interface for Agent 3 to set performance configuration.
        
        Args:
            config: Performance configuration dictionary
        """
        self._performance_config = config
        logger.info("Performance configuration set by Agent 3")
    
    def enable_features(self, features: List[str]) -> None:
        """Interface for Agent 4 to enable advanced features.
        
        Args:
            features: List of feature names to enable
        """
        self._enabled_features = features
        logger.info(f"Features enabled by Agent 4: {features}")
    
    # Utility methods
    def get_document_info(self) -> Optional[Dict[str, Any]]:
        """Get current document information."""
        return self.current_document.to_dict() if self.current_document else None
    
    def is_document_loaded(self) -> bool:
        """Check if a document is currently loaded."""
        return self.current_document is not None and self.current_document.is_loaded
    
    def get_current_page(self) -> int:
        """Get current page number."""
        return self.current_document.current_page if self.current_document else 0
    
    def get_page_count(self) -> int:
        """Get total page count."""
        return self.current_document.page_count if self.current_document else 0
    
    def get_zoom_level(self) -> float:
        """Get current zoom level."""
        return self.current_document.zoom_level if self.current_document else 1.0
    
    def _cleanup_temp_files(self) -> None:
        """Cleanup temporary files."""
        for temp_file in self._temp_files:
            try:
                Path(temp_file).unlink(missing_ok=True)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file {temp_file}: {e}")
        
        self._temp_files.clear()
    
    def closeEvent(self, event) -> None:
        """Handle widget close event."""
        try:
            self.close_document()
        except Exception as e:
            logger.error(f"Error during close: {e}")
        finally:
            super().closeEvent(event)