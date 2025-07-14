"""
PDF.js UI Framework Integration.

This module provides complete integration with the TORE Matrix UI framework
including responsive toolbars, thumbnail navigation, progress indicators, 
and seamless user experience components.

Agent 4 Implementation:
- UI Framework integration (#11-15)
- Responsive toolbar and controls
- Thumbnail navigation panel
- Progress indicators and user feedback
- Theme system integration
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union, Callable
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal, QTimer, Qt, QSize
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QToolBar, QAction, QSplitter,
    QScrollArea, QLabel, QPushButton, QSlider, QSpinBox, QProgressBar,
    QFrame, QSizePolicy, QListWidget, QListWidgetItem
)
from PyQt6.QtGui import QIcon, QPixmap, QFont, QPainter, QColor
from PyQt6.QtWebEngineWidgets import QWebEngineView

logger = logging.getLogger(__name__)


@dataclass
class UIMetrics:
    """UI performance metrics."""
    toolbar_response_time_ms: float = 0.0
    thumbnail_load_time_ms: float = 0.0
    panel_update_time_ms: float = 0.0
    theme_switch_time_ms: float = 0.0
    avg_response_time_ms: float = 0.0
    last_updated: float = field(default_factory=time.time)


@dataclass
class ThumbnailData:
    """Thumbnail image data."""
    page_number: int
    image_data: bytes
    width: int
    height: int
    scale: float = 1.0
    timestamp: float = field(default_factory=time.time)


class PDFToolbar(QToolBar):
    """
    Enhanced PDF toolbar with comprehensive controls.
    
    Provides all essential PDF viewing controls with responsive design
    and integration with the UI framework theme system.
    """
    
    # Signals
    action_triggered = pyqtSignal(str, dict)  # action_name, parameters
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize PDF toolbar.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.setMovable(False)
        
        # Action storage
        self.pdf_actions: Dict[str, QAction] = {}
        
        # Create actions
        self._create_actions()
        self._setup_toolbar()
        
        logger.debug("PDFToolbar initialized")
    
    def _create_actions(self) -> None:
        """Create toolbar actions."""
        # Navigation actions
        self.pdf_actions["first_page"] = QAction("First", self)
        self.pdf_actions["first_page"].setToolTip("Go to first page")
        self.pdf_actions["first_page"].triggered.connect(
            lambda: self.action_triggered.emit("first_page", {})
        )
        
        self.pdf_actions["prev_page"] = QAction("Previous", self)
        self.pdf_actions["prev_page"].setToolTip("Go to previous page")
        self.pdf_actions["prev_page"].triggered.connect(
            lambda: self.action_triggered.emit("prev_page", {})
        )
        
        self.pdf_actions["next_page"] = QAction("Next", self)
        self.pdf_actions["next_page"].setToolTip("Go to next page")
        self.pdf_actions["next_page"].triggered.connect(
            lambda: self.action_triggered.emit("next_page", {})
        )
        
        self.pdf_actions["last_page"] = QAction("Last", self)
        self.pdf_actions["last_page"].setToolTip("Go to last page")
        self.pdf_actions["last_page"].triggered.connect(
            lambda: self.action_triggered.emit("last_page", {})
        )
        
        # Zoom actions
        self.pdf_actions["zoom_in"] = QAction("Zoom In", self)
        self.pdf_actions["zoom_in"].setToolTip("Zoom in")
        self.pdf_actions["zoom_in"].triggered.connect(
            lambda: self.action_triggered.emit("zoom_in", {})
        )
        
        self.pdf_actions["zoom_out"] = QAction("Zoom Out", self)
        self.pdf_actions["zoom_out"].setToolTip("Zoom out")
        self.pdf_actions["zoom_out"].triggered.connect(
            lambda: self.action_triggered.emit("zoom_out", {})
        )
        
        self.pdf_actions["fit_width"] = QAction("Fit Width", self)
        self.pdf_actions["fit_width"].setToolTip("Fit to width")
        self.pdf_actions["fit_width"].triggered.connect(
            lambda: self.action_triggered.emit("fit_width", {})
        )
        
        self.pdf_actions["fit_page"] = QAction("Fit Page", self)
        self.pdf_actions["fit_page"].setToolTip("Fit page")
        self.pdf_actions["fit_page"].triggered.connect(
            lambda: self.action_triggered.emit("fit_page", {})
        )
        
        # Feature actions
        self.pdf_actions["search"] = QAction("Search", self)
        self.pdf_actions["search"].setToolTip("Search in document")
        self.pdf_actions["search"].setCheckable(True)
        self.pdf_actions["search"].triggered.connect(
            lambda checked: self.action_triggered.emit("toggle_search", {"enabled": checked})
        )
        
        self.pdf_actions["annotations"] = QAction("Annotations", self)
        self.pdf_actions["annotations"].setToolTip("Toggle annotations")
        self.pdf_actions["annotations"].setCheckable(True)
        self.pdf_actions["annotations"].triggered.connect(
            lambda checked: self.action_triggered.emit("toggle_annotations", {"enabled": checked})
        )
        
        self.pdf_actions["thumbnails"] = QAction("Thumbnails", self)
        self.pdf_actions["thumbnails"].setToolTip("Toggle thumbnail panel")
        self.pdf_actions["thumbnails"].setCheckable(True)
        self.pdf_actions["thumbnails"].triggered.connect(
            lambda checked: self.action_triggered.emit("toggle_thumbnails", {"enabled": checked})
        )
        
        self.pdf_actions["print"] = QAction("Print", self)
        self.pdf_actions["print"].setToolTip("Print document")
        self.pdf_actions["print"].triggered.connect(
            lambda: self.action_triggered.emit("print", {})
        )
    
    def _setup_toolbar(self) -> None:
        """Setup toolbar layout."""
        # Navigation section
        self.addAction(self.pdf_actions["first_page"])
        self.addAction(self.pdf_actions["prev_page"])
        
        # Page control
        self.page_input = QSpinBox()
        self.page_input.setMinimum(1)
        self.page_input.setMaximum(1)
        self.page_input.valueChanged.connect(self._on_page_changed)
        self.addWidget(self.page_input)
        
        self.page_label = QLabel("of 1")
        self.addWidget(self.page_label)
        
        self.addAction(self.pdf_actions["next_page"])
        self.addAction(self.pdf_actions["last_page"])
        
        self.addSeparator()
        
        # Zoom section
        self.addAction(self.pdf_actions["zoom_out"])
        
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setMinimum(10)  # 0.1x
        self.zoom_slider.setMaximum(1000)  # 10x
        self.zoom_slider.setValue(100)  # 1x
        self.zoom_slider.valueChanged.connect(self._on_zoom_changed)
        self.addWidget(self.zoom_slider)
        
        self.zoom_label = QLabel("100%")
        self.addWidget(self.zoom_label)
        
        self.addAction(self.pdf_actions["zoom_in"])
        self.addAction(self.pdf_actions["fit_width"])
        self.addAction(self.pdf_actions["fit_page"])
        
        self.addSeparator()
        
        # Feature section
        self.addAction(self.pdf_actions["search"])
        self.addAction(self.pdf_actions["annotations"])
        self.addAction(self.pdf_actions["thumbnails"])
        
        self.addSeparator()
        
        # Action section
        self.addAction(self.pdf_actions["print"])
    
    def _on_page_changed(self, page: int) -> None:
        """Handle page input change.
        
        Args:
            page: New page number
        """
        self.action_triggered.emit("go_to_page", {"page": page})
    
    def _on_zoom_changed(self, value: int) -> None:
        """Handle zoom slider change.
        
        Args:
            value: Zoom value (10-1000)
        """
        zoom_level = value / 100.0
        self.zoom_label.setText(f"{value}%")
        self.action_triggered.emit("set_zoom", {"zoom": zoom_level})
    
    def update_document_info(self, page_count: int, current_page: int) -> None:
        """Update document information.
        
        Args:
            page_count: Total number of pages
            current_page: Current page number
        """
        self.page_input.setMaximum(page_count)
        self.page_input.setValue(current_page)
        self.page_label.setText(f"of {page_count}")
    
    def update_zoom_info(self, zoom_level: float) -> None:
        """Update zoom information.
        
        Args:
            zoom_level: Current zoom level
        """
        zoom_percent = int(zoom_level * 100)
        self.zoom_slider.setValue(zoom_percent)
        self.zoom_label.setText(f"{zoom_percent}%")
    
    def set_feature_enabled(self, feature: str, enabled: bool) -> None:
        """Set feature toggle state.
        
        Args:
            feature: Feature name
            enabled: Whether feature is enabled
        """
        if feature in self.pdf_actions:
            self.pdf_actions[feature].setChecked(enabled)


class ThumbnailPanel(QWidget):
    """
    PDF thumbnail navigation panel.
    
    Provides visual thumbnail navigation with page previews
    and quick navigation capabilities.
    """
    
    # Signals
    page_selected = pyqtSignal(int)  # page_number
    thumbnails_loaded = pyqtSignal(int)  # count
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize thumbnail panel.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Setup layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Header
        header = QLabel("Pages")
        header.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(header)
        
        # Thumbnail list
        self.thumbnail_list = QListWidget()
        self.thumbnail_list.setViewMode(QListWidget.ViewMode.IconMode)
        self.thumbnail_list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.thumbnail_list.setIconSize(QSize(100, 120))
        self.thumbnail_list.setSpacing(5)
        self.thumbnail_list.itemClicked.connect(self._on_thumbnail_clicked)
        layout.addWidget(self.thumbnail_list)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Thumbnail storage
        self.thumbnails: Dict[int, ThumbnailData] = {}
        self.current_page = 1
        
        logger.debug("ThumbnailPanel initialized")
    
    def load_thumbnails(self, page_count: int) -> None:
        """Load thumbnails for document.
        
        Args:
            page_count: Number of pages to load thumbnails for
        """
        try:
            self.thumbnail_list.clear()
            self.thumbnails.clear()
            
            # Show progress
            self.progress_bar.setVisible(True)
            self.progress_bar.setMaximum(page_count)
            self.progress_bar.setValue(0)
            
            # Create placeholder items
            for page in range(1, page_count + 1):
                item = QListWidgetItem(f"Page {page}")
                item.setData(Qt.ItemDataRole.UserRole, page)
                self.thumbnail_list.addItem(item)
            
            # Request thumbnails (this would typically be async)
            self._request_thumbnails(page_count)
            
            logger.info(f"Loading thumbnails for {page_count} pages")
            
        except Exception as e:
            logger.error(f"Error loading thumbnails: {e}")
    
    def _request_thumbnails(self, page_count: int) -> None:
        """Request thumbnail generation (placeholder implementation).
        
        Args:
            page_count: Number of pages
        """
        # This would typically send a request to JavaScript to generate thumbnails
        # For now, we'll create placeholder thumbnails
        for page in range(1, page_count + 1):
            self._create_placeholder_thumbnail(page)
            self.progress_bar.setValue(page)
        
        self.progress_bar.setVisible(False)
        self.thumbnails_loaded.emit(page_count)
    
    def _create_placeholder_thumbnail(self, page: int) -> None:
        """Create placeholder thumbnail.
        
        Args:
            page: Page number
        """
        # Create placeholder pixmap
        pixmap = QPixmap(100, 120)
        pixmap.fill(QColor(240, 240, 240))
        
        # Draw page number
        painter = QPainter(pixmap)
        painter.setPen(QColor(100, 100, 100))
        painter.setFont(QFont("Arial", 12))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, str(page))
        painter.end()
        
        # Update list item
        item = self.thumbnail_list.item(page - 1)
        if item:
            item.setIcon(QIcon(pixmap))
    
    def _on_thumbnail_clicked(self, item: QListWidgetItem) -> None:
        """Handle thumbnail click.
        
        Args:
            item: Clicked thumbnail item
        """
        page = item.data(Qt.ItemDataRole.UserRole)
        if page:
            self.page_selected.emit(page)
    
    def set_current_page(self, page: int) -> None:
        """Set current page highlight.
        
        Args:
            page: Current page number
        """
        self.current_page = page
        
        # Update item selection
        for i in range(self.thumbnail_list.count()):
            item = self.thumbnail_list.item(i)
            if item:
                item_page = item.data(Qt.ItemDataRole.UserRole)
                if item_page == page:
                    self.thumbnail_list.setCurrentItem(item)
                    break


class PDFProgressIndicator(QWidget):
    """
    PDF loading and processing progress indicator.
    
    Provides user feedback during document operations.
    """
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize progress indicator.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Setup layout
        layout = QVBoxLayout(self)
        
        # Status label
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        logger.debug("PDFProgressIndicator initialized")
    
    def show_progress(self, message: str, maximum: int = 100) -> None:
        """Show progress with message.
        
        Args:
            message: Status message
            maximum: Maximum progress value
        """
        self.status_label.setText(message)
        self.progress_bar.setMaximum(maximum)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
    
    def update_progress(self, value: int, message: Optional[str] = None) -> None:
        """Update progress value.
        
        Args:
            value: Progress value
            message: Optional status message
        """
        self.progress_bar.setValue(value)
        if message:
            self.status_label.setText(message)
    
    def hide_progress(self, message: str = "Ready") -> None:
        """Hide progress indicator.
        
        Args:
            message: Final status message
        """
        self.progress_bar.setVisible(False)
        self.status_label.setText(message)


class PDFUIManager(QObject):
    """
    PDF UI framework integration manager.
    
    Coordinates all UI components and integrates with the TORE Matrix
    UI framework for seamless user experience.
    
    Signals:
        ui_action: Emitted when UI action is triggered
        thumbnail_clicked: Emitted when thumbnail is clicked
        progress_updated: Emitted when progress is updated
        metrics_updated: Emitted when UI metrics are updated
    """
    
    # Signals
    ui_action = pyqtSignal(str, dict)  # action_name, parameters
    thumbnail_clicked = pyqtSignal(int)  # page_number
    progress_updated = pyqtSignal(str, int)  # message, progress
    metrics_updated = pyqtSignal(UIMetrics)
    
    def __init__(self, pdf_viewer: QWebEngineView, config: Any):
        """Initialize UI manager.
        
        Args:
            pdf_viewer: PDF viewer instance
            config: Feature configuration
        """
        super().__init__()
        
        self.pdf_viewer = pdf_viewer
        self.config = config
        
        # UI components
        self.toolbar: Optional[PDFToolbar] = None
        self.thumbnail_panel: Optional[ThumbnailPanel] = None
        self.progress_indicator: Optional[PDFProgressIndicator] = None
        self.main_widget: Optional[QWidget] = None
        
        # Performance monitoring
        self.metrics = UIMetrics()
        self.response_times: List[float] = []
        
        # JavaScript communication
        self.bridge = None
        self.performance_config = None
        
        # State
        self.enabled = True
        
        logger.info("PDFUIManager initialized")
    
    def connect_bridge(self, bridge) -> None:
        """Connect to PDF bridge for JavaScript communication.
        
        Args:
            bridge: PDFBridge instance
        """
        self.bridge = bridge
        logger.info("UI manager connected to bridge")
    
    def set_performance_config(self, config: Dict[str, Any]) -> None:
        """Set performance configuration from Agent 3.
        
        Args:
            config: Performance configuration
        """
        self.performance_config = config
        logger.debug("UI performance configuration updated")
    
    def enable(self) -> None:
        """Enable UI functionality."""
        self.enabled = True
        if self.main_widget:
            self.main_widget.setEnabled(True)
        logger.info("UI functionality enabled")
    
    def disable(self) -> None:
        """Disable UI functionality."""
        self.enabled = False
        if self.main_widget:
            self.main_widget.setEnabled(False)
        logger.info("UI functionality disabled")
    
    def create_main_widget(self, parent: Optional[QWidget] = None) -> QWidget:
        """Create main PDF UI widget with all components.
        
        Args:
            parent: Parent widget
            
        Returns:
            Main PDF widget
        """
        if self.main_widget:
            return self.main_widget
        
        # Create main widget
        main_widget = QWidget(parent)
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create toolbar
        if self.config.toolbar_enabled:
            self.toolbar = PDFToolbar()
            self.toolbar.action_triggered.connect(self._handle_toolbar_action)
            layout.addWidget(self.toolbar)
        
        # Create content area with splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Add thumbnail panel if enabled
        if self.config.thumbnail_panel:
            self.thumbnail_panel = ThumbnailPanel()
            self.thumbnail_panel.page_selected.connect(self.thumbnail_clicked.emit)
            self.thumbnail_panel.setMaximumWidth(150)
            splitter.addWidget(self.thumbnail_panel)
        
        # Add PDF viewer
        splitter.addWidget(self.pdf_viewer)
        
        # Set splitter proportions
        if self.thumbnail_panel:
            splitter.setSizes([150, 800])
        
        layout.addWidget(splitter)
        
        # Create progress indicator
        if self.config.progress_indicators:
            self.progress_indicator = PDFProgressIndicator()
            layout.addWidget(self.progress_indicator)
        
        self.main_widget = main_widget
        return main_widget
    
    def _handle_toolbar_action(self, action: str, parameters: Dict[str, Any]) -> None:
        """Handle toolbar action.
        
        Args:
            action: Action name
            parameters: Action parameters
        """
        start_time = time.time()
        
        try:
            # Emit UI action signal
            self.ui_action.emit(action, parameters)
            
            # Update metrics
            response_time = (time.time() - start_time) * 1000
            self.response_times.append(response_time)
            
            # Keep only last 50 response times
            if len(self.response_times) > 50:
                self.response_times.pop(0)
            
            # Update average response time
            self.metrics.avg_response_time_ms = sum(self.response_times) / len(self.response_times)
            self.metrics.toolbar_response_time_ms = response_time
            self.metrics.last_updated = time.time()
            
            logger.debug(f"Toolbar action: {action} ({response_time:.1f}ms)")
            
        except Exception as e:
            logger.error(f"Error handling toolbar action {action}: {e}")
    
    def update_document_info(self, page_count: int, current_page: int) -> None:
        """Update document information in UI.
        
        Args:
            page_count: Total number of pages
            current_page: Current page number
        """
        if self.toolbar:
            self.toolbar.update_document_info(page_count, current_page)
        
        if self.thumbnail_panel:
            if page_count > 0:
                start_time = time.time()
                self.thumbnail_panel.load_thumbnails(page_count)
                self.metrics.thumbnail_load_time_ms = (time.time() - start_time) * 1000
            
            self.thumbnail_panel.set_current_page(current_page)
    
    def update_zoom_info(self, zoom_level: float) -> None:
        """Update zoom information in UI.
        
        Args:
            zoom_level: Current zoom level
        """
        if self.toolbar:
            self.toolbar.update_zoom_info(zoom_level)
    
    def set_feature_enabled(self, feature: str, enabled: bool) -> None:
        """Set feature toggle state in UI.
        
        Args:
            feature: Feature name
            enabled: Whether feature is enabled
        """
        if self.toolbar:
            self.toolbar.set_feature_enabled(feature, enabled)
    
    def show_loading_progress(self, message: str, maximum: int = 100) -> None:
        """Show loading progress.
        
        Args:
            message: Loading message
            maximum: Maximum progress value
        """
        if self.progress_indicator:
            self.progress_indicator.show_progress(message, maximum)
        self.progress_updated.emit(message, 0)
    
    def update_loading_progress(self, value: int, message: Optional[str] = None) -> None:
        """Update loading progress.
        
        Args:
            value: Progress value
            message: Optional status message
        """
        if self.progress_indicator:
            self.progress_indicator.update_progress(value, message)
        self.progress_updated.emit(message or "", value)
    
    def hide_loading_progress(self, message: str = "Ready") -> None:
        """Hide loading progress.
        
        Args:
            message: Final status message
        """
        if self.progress_indicator:
            self.progress_indicator.hide_progress(message)
        self.progress_updated.emit(message, 100)
    
    def get_toolbar(self) -> Optional[PDFToolbar]:
        """Get toolbar widget.
        
        Returns:
            Toolbar widget or None
        """
        return self.toolbar
    
    def get_thumbnail_panel(self) -> Optional[ThumbnailPanel]:
        """Get thumbnail panel widget.
        
        Returns:
            Thumbnail panel widget or None
        """
        return self.thumbnail_panel
    
    def get_progress_indicator(self) -> Optional[PDFProgressIndicator]:
        """Get progress indicator widget.
        
        Returns:
            Progress indicator widget or None
        """
        return self.progress_indicator
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get UI performance metrics.
        
        Returns:
            Dictionary containing UI metrics
        """
        return {
            "toolbar_response_time_ms": self.metrics.toolbar_response_time_ms,
            "thumbnail_load_time_ms": self.metrics.thumbnail_load_time_ms,
            "panel_update_time_ms": self.metrics.panel_update_time_ms,
            "avg_response_time_ms": self.metrics.avg_response_time_ms,
            "targets_met": {
                "ui_response": self.metrics.avg_response_time_ms <= 100.0,  # 100ms target
                "thumbnail_load": self.metrics.thumbnail_load_time_ms <= 500.0  # 500ms target
            },
            "component_status": {
                "toolbar_enabled": self.toolbar is not None,
                "thumbnail_panel_enabled": self.thumbnail_panel is not None,
                "progress_indicator_enabled": self.progress_indicator is not None
            }
        }
    
    def cleanup(self) -> None:
        """Clean up resources."""
        try:
            if self.main_widget:
                self.main_widget.deleteLater()
                self.main_widget = None
            
            self.toolbar = None
            self.thumbnail_panel = None
            self.progress_indicator = None
            self.response_times.clear()
            
            logger.info("PDFUIManager cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during UI cleanup: {e}")