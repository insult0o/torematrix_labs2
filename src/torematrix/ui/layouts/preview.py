"""Layout Preview Tools for TORE Matrix Labs V3.

This module provides comprehensive layout preview functionality including
live preview, template showcase, responsive simulation, and export capabilities.
"""

from typing import Dict, List, Optional, Any, Tuple, Set, Union, Callable
from enum import Enum, auto
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import logging
import time
from datetime import datetime
import json

from PyQt6.QtWidgets import (
    QWidget, QMainWindow, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QScrollArea, QComboBox, QSpinBox,
    QSlider, QCheckBox, QTabWidget, QStackedWidget, QSplitter,
    QProgressBar, QTextEdit, QGroupBox, QButtonGroup, QRadioButton,
    QToolBar, QToolButton, QMenu, QDialog, QDialogButtonBox,
    QFileDialog, QMessageBox
)
from PyQt6.QtCore import (
    Qt, QRect, QSize, QPoint, QTimer, pyqtSignal, QObject,
    QPropertyAnimation, QEasingCurve, QThread, QMutex
)
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QPixmap, QPalette,
    QIcon, QScreen, QTransform, QLinearGradient
)

from ...core.events import EventBus
from ...core.config import ConfigurationManager
from ...core.state import Store
from ..base import BaseUIComponent
from .base import LayoutConfiguration, LayoutType, LayoutGeometry, LayoutItem
from .manager import LayoutManager
from .responsive import ScreenProperties, ResponsiveLayoutEngine
from .animations import AnimationManager

logger = logging.getLogger(__name__)


class PreviewMode(Enum):
    """Preview display modes."""
    LIVE = auto()           # Live interactive preview
    STATIC = auto()         # Static screenshot-like preview
    WIREFRAME = auto()      # Wireframe outline preview
    MOCKUP = auto()         # High-fidelity mockup preview


class DeviceType(Enum):
    """Device types for responsive preview."""
    DESKTOP = auto()
    LAPTOP = auto()
    TABLET = auto()
    MOBILE = auto()
    WATCH = auto()
    CUSTOM = auto()


class ExportFormat(Enum):
    """Export formats for previews."""
    PNG = auto()
    JPEG = auto()
    PDF = auto()
    SVG = auto()
    HTML = auto()
    JSON = auto()


@dataclass
class DeviceProfile:
    """Device profile for responsive preview."""
    name: str
    device_type: DeviceType
    screen_size: QSize
    dpi: float = 96.0
    scale_factor: float = 1.0
    is_touch: bool = False
    orientation: str = "landscape"  # "landscape" or "portrait"
    
    def __post_init__(self):
        """Calculate derived properties."""
        self.aspect_ratio = self.screen_size.width() / self.screen_size.height()
        self.diagonal_inches = ((self.screen_size.width() ** 2 + self.screen_size.height() ** 2) ** 0.5) / self.dpi


@dataclass
class PreviewSettings:
    """Settings for layout preview."""
    mode: PreviewMode = PreviewMode.LIVE
    device_profile: Optional[DeviceProfile] = None
    zoom_level: float = 1.0
    show_grid: bool = False
    show_rulers: bool = False
    show_component_bounds: bool = False
    show_responsive_breakpoints: bool = True
    animation_enabled: bool = True
    auto_refresh: bool = True
    refresh_interval_ms: int = 1000


@dataclass
class PreviewMetrics:
    """Performance metrics for preview rendering."""
    render_time_ms: float = 0.0
    memory_usage_mb: float = 0.0
    widget_count: int = 0
    animation_count: int = 0
    fps: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


class PreviewRenderer(QObject):
    """Renders layout previews with various modes and effects."""
    
    # Signals
    render_completed = pyqtSignal(QPixmap)
    render_failed = pyqtSignal(str)
    metrics_updated = pyqtSignal(PreviewMetrics)
    
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        
        self._render_cache: Dict[str, QPixmap] = {}
        self._cache_mutex = QMutex()
        self._max_cache_size = 50
        
        # Performance tracking
        self._metrics = PreviewMetrics()
        self._render_timer = QTimer()
        self._render_timer.setSingleShot(True)
        self._render_timer.timeout.connect(self._perform_render)
        
        # Current render request
        self._pending_widget: Optional[QWidget] = None
        self._pending_settings: Optional[PreviewSettings] = None
        self._pending_cache_key: Optional[str] = None
    
    def render_widget(
        self,
        widget: QWidget,
        settings: PreviewSettings,
        cache_key: Optional[str] = None
    ) -> None:
        """Render widget with given settings."""
        start_time = time.perf_counter()
        
        # Check cache first
        if cache_key and self._get_cached_render(cache_key):
            cached_pixmap = self._get_cached_render(cache_key)
            self.render_completed.emit(cached_pixmap)
            return
        
        # Store pending request
        self._pending_widget = widget
        self._pending_settings = settings
        self._pending_cache_key = cache_key
        
        # Start render with small delay to batch requests
        self._render_timer.start(10)
    
    def _perform_render(self) -> None:
        """Perform the actual rendering."""
        if not self._pending_widget or not self._pending_settings:
            return
        
        start_time = time.perf_counter()
        
        try:
            # Create pixmap
            widget = self._pending_widget
            settings = self._pending_settings
            
            # Calculate render size
            render_size = self._calculate_render_size(widget, settings)
            pixmap = QPixmap(render_size)
            pixmap.fill(Qt.GlobalColor.white)
            
            # Setup painter
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            
            # Apply zoom
            if settings.zoom_level != 1.0:
                painter.scale(settings.zoom_level, settings.zoom_level)
            
            # Render based on mode
            if settings.mode == PreviewMode.LIVE:
                self._render_live(painter, widget, settings)
            elif settings.mode == PreviewMode.STATIC:
                self._render_static(painter, widget, settings)
            elif settings.mode == PreviewMode.WIREFRAME:
                self._render_wireframe(painter, widget, settings)
            elif settings.mode == PreviewMode.MOCKUP:
                self._render_mockup(painter, widget, settings)
            
            painter.end()
            
            # Cache result
            if self._pending_cache_key:
                self._cache_render(self._pending_cache_key, pixmap)
            
            # Update metrics
            render_time = (time.perf_counter() - start_time) * 1000
            self._update_metrics(render_time, widget)
            
            # Emit completion
            self.render_completed.emit(pixmap)
            
        except Exception as e:
            logger.error(f"Preview render failed: {e}")
            self.render_failed.emit(str(e))
        finally:
            # Clear pending request
            self._pending_widget = None
            self._pending_settings = None
            self._pending_cache_key = None
    
    def _calculate_render_size(self, widget: QWidget, settings: PreviewSettings) -> QSize:
        """Calculate the render size based on widget and settings."""
        base_size = widget.size()
        
        if settings.device_profile:
            # Use device screen size
            device_size = settings.device_profile.screen_size
            scale_factor = settings.device_profile.scale_factor
            return QSize(
                int(device_size.width() * scale_factor),
                int(device_size.height() * scale_factor)
            )
        else:
            # Use widget size with zoom
            return QSize(
                int(base_size.width() * settings.zoom_level),
                int(base_size.height() * settings.zoom_level)
            )
    
    def _render_live(self, painter: QPainter, widget: QWidget, settings: PreviewSettings) -> None:
        """Render live interactive preview."""
        # Render the actual widget
        widget.render(painter)
        
        # Add overlay elements
        if settings.show_component_bounds:
            self._draw_component_bounds(painter, widget)
        
        if settings.show_grid:
            self._draw_grid(painter, widget.size())
        
        if settings.show_rulers:
            self._draw_rulers(painter, widget.size())
    
    def _render_static(self, painter: QPainter, widget: QWidget, settings: PreviewSettings) -> None:
        """Render static screenshot-like preview."""
        # Disable animations temporarily
        widget.setUpdatesEnabled(False)
        
        # Render widget
        widget.render(painter)
        
        # Re-enable updates
        widget.setUpdatesEnabled(True)
        
        # Add static overlay
        if settings.show_component_bounds:
            self._draw_component_bounds(painter, widget, alpha=0.3)
    
    def _render_wireframe(self, painter: QPainter, widget: QWidget, settings: PreviewSettings) -> None:
        """Render wireframe outline preview."""
        painter.fillRect(painter.viewport(), QColor(250, 250, 250))
        
        # Draw wireframe structure
        self._draw_wireframe_structure(painter, widget)
        
        # Add labels
        self._draw_wireframe_labels(painter, widget)
    
    def _render_mockup(self, painter: QPainter, widget: QWidget, settings: PreviewSettings) -> None:
        """Render high-fidelity mockup preview."""
        # Create enhanced version with professional styling
        self._draw_mockup_background(painter, widget.size())
        
        # Render widget with enhancements
        widget.render(painter)
        
        # Add mockup enhancements
        self._draw_mockup_shadows(painter, widget)
        self._draw_mockup_chrome(painter, widget, settings)
    
    def _draw_component_bounds(self, painter: QPainter, widget: QWidget, alpha: float = 0.5) -> None:
        """Draw component boundaries."""
        painter.save()
        
        pen = QPen(QColor(255, 0, 0, int(255 * alpha)), 1, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        
        # Draw bounds for all child widgets
        for child in widget.findChildren(QWidget):
            if child.isVisible():
                rect = child.geometry()
                painter.drawRect(rect)
                
                # Draw component type label
                painter.drawText(rect.topLeft() + QPoint(2, 12), 
                               child.metaObject().className())
        
        painter.restore()
    
    def _draw_grid(self, painter: QPainter, size: QSize) -> None:
        """Draw grid overlay."""
        painter.save()
        
        grid_size = 20
        painter.setPen(QPen(QColor(200, 200, 200, 100), 1))
        
        # Vertical lines
        for x in range(0, size.width(), grid_size):
            painter.drawLine(x, 0, x, size.height())
        
        # Horizontal lines
        for y in range(0, size.height(), grid_size):
            painter.drawLine(0, y, size.width(), y)
        
        painter.restore()
    
    def _draw_rulers(self, painter: QPainter, size: QSize) -> None:
        """Draw ruler overlay."""
        painter.save()
        
        ruler_size = 20
        painter.fillRect(0, 0, size.width(), ruler_size, QColor(240, 240, 240, 200))
        painter.fillRect(0, 0, ruler_size, size.height(), QColor(240, 240, 240, 200))
        
        painter.setPen(QPen(QColor(100, 100, 100), 1))
        font = QFont("Arial", 8)
        painter.setFont(font)
        
        # Horizontal ruler
        for x in range(0, size.width(), 50):
            painter.drawLine(x, 15, x, ruler_size)
            if x > 0:
                painter.drawText(x + 2, 12, str(x))
        
        # Vertical ruler
        for y in range(0, size.height(), 50):
            painter.drawLine(15, y, ruler_size, y)
            if y > 0:
                painter.save()
                painter.translate(12, y - 2)
                painter.rotate(-90)
                painter.drawText(0, 0, str(y))
                painter.restore()
        
        painter.restore()
    
    def _draw_wireframe_structure(self, painter: QPainter, widget: QWidget) -> None:
        """Draw wireframe structure."""
        painter.save()
        
        painter.setPen(QPen(QColor(100, 100, 100), 2))
        painter.setBrush(QBrush(QColor(245, 245, 245)))
        
        # Draw main container
        painter.drawRect(widget.rect())
        
        # Draw child components as rectangles
        for child in widget.findChildren(QWidget):
            if child.isVisible() and child.parent() == widget:
                rect = child.geometry()
                painter.drawRect(rect)
                
                # Add wireframe details based on widget type
                self._add_wireframe_details(painter, child, rect)
        
        painter.restore()
    
    def _add_wireframe_details(self, painter: QPainter, widget: QWidget, rect: QRect) -> None:
        """Add wireframe details for specific widget types."""
        widget_type = widget.metaObject().className()
        
        if "Button" in widget_type:
            # Draw button styling
            painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 4, 4)
        elif "Text" in widget_type or "Edit" in widget_type:
            # Draw text lines
            line_height = 14
            for i in range(rect.height() // line_height):
                y = rect.top() + (i + 1) * line_height
                painter.drawLine(rect.left() + 4, y, rect.right() - 4, y)
        elif "Splitter" in widget_type:
            # Draw splitter handle
            if rect.width() > rect.height():
                # Horizontal splitter
                center_y = rect.center().y()
                painter.drawLine(rect.left(), center_y, rect.right(), center_y)
            else:
                # Vertical splitter
                center_x = rect.center().x()
                painter.drawLine(center_x, rect.top(), center_x, rect.bottom())
    
    def _draw_wireframe_labels(self, painter: QPainter, widget: QWidget) -> None:
        """Draw wireframe labels."""
        painter.save()
        
        font = QFont("Arial", 9)
        painter.setFont(font)
        painter.setPen(QPen(QColor(80, 80, 80), 1))
        
        for child in widget.findChildren(QWidget):
            if child.isVisible():
                rect = child.geometry()
                if rect.width() > 50 and rect.height() > 20:
                    label = child.objectName() or child.metaObject().className()
                    painter.drawText(rect.adjusted(4, 4, -4, -4), 
                                   Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, 
                                   label)
        
        painter.restore()
    
    def _draw_mockup_background(self, painter: QPainter, size: QSize) -> None:
        """Draw mockup background with gradient."""
        gradient = QLinearGradient(0, 0, 0, size.height())
        gradient.setColorAt(0, QColor(248, 249, 250))
        gradient.setColorAt(1, QColor(233, 236, 239))
        
        painter.fillRect(0, 0, size.width(), size.height(), QBrush(gradient))
    
    def _draw_mockup_shadows(self, painter: QPainter, widget: QWidget) -> None:
        """Draw subtle shadows for mockup effect."""
        painter.save()
        
        shadow_color = QColor(0, 0, 0, 20)
        shadow_offset = QPoint(2, 2)
        
        for child in widget.findChildren(QWidget):
            if child.isVisible():
                rect = child.geometry()
                shadow_rect = rect.translated(shadow_offset)
                painter.fillRect(shadow_rect, shadow_color)
        
        painter.restore()
    
    def _draw_mockup_chrome(self, painter: QPainter, widget: QWidget, settings: PreviewSettings) -> None:
        """Draw device chrome for mockup."""
        if not settings.device_profile:
            return
        
        painter.save()
        
        # Draw device frame
        if settings.device_profile.device_type == DeviceType.MOBILE:
            self._draw_mobile_chrome(painter, widget.size())
        elif settings.device_profile.device_type == DeviceType.TABLET:
            self._draw_tablet_chrome(painter, widget.size())
        elif settings.device_profile.device_type == DeviceType.LAPTOP:
            self._draw_laptop_chrome(painter, widget.size())
        
        painter.restore()
    
    def _draw_mobile_chrome(self, painter: QPainter, size: QSize) -> None:
        """Draw mobile device chrome."""
        chrome_color = QColor(50, 50, 50)
        painter.setPen(QPen(chrome_color, 8))
        painter.drawRoundedRect(QRect(4, 4, size.width() - 8, size.height() - 8), 20, 20)
        
        # Home button
        button_rect = QRect(size.width() // 2 - 15, size.height() - 25, 30, 15)
        painter.fillRect(button_rect, chrome_color)
    
    def _draw_tablet_chrome(self, painter: QPainter, size: QSize) -> None:
        """Draw tablet device chrome."""
        chrome_color = QColor(60, 60, 60)
        painter.setPen(QPen(chrome_color, 6))
        painter.drawRoundedRect(QRect(3, 3, size.width() - 6, size.height() - 6), 15, 15)
    
    def _draw_laptop_chrome(self, painter: QPainter, size: QSize) -> None:
        """Draw laptop device chrome."""
        # Draw screen bezel
        bezel_color = QColor(40, 40, 40)
        painter.setPen(QPen(bezel_color, 12))
        painter.drawRect(QRect(6, 6, size.width() - 12, size.height() - 12))
        
        # Draw keyboard area
        keyboard_height = 40
        keyboard_rect = QRect(0, size.height(), size.width(), keyboard_height)
        painter.fillRect(keyboard_rect, QColor(220, 220, 220))
    
    def _get_cached_render(self, cache_key: str) -> Optional[QPixmap]:
        """Get cached render if available."""
        with QMutex():
            return self._render_cache.get(cache_key)
    
    def _cache_render(self, cache_key: str, pixmap: QPixmap) -> None:
        """Cache rendered pixmap."""
        with QMutex():
            # Remove oldest entries if cache is full
            if len(self._render_cache) >= self._max_cache_size:
                oldest_key = next(iter(self._render_cache))
                del self._render_cache[oldest_key]
            
            self._render_cache[cache_key] = pixmap
    
    def _update_metrics(self, render_time: float, widget: QWidget) -> None:
        """Update rendering metrics."""
        self._metrics.render_time_ms = render_time
        self._metrics.widget_count = len(widget.findChildren(QWidget))
        self._metrics.timestamp = datetime.now()
        
        # Estimate memory usage
        total_pixels = sum(
            child.width() * child.height() 
            for child in widget.findChildren(QWidget) 
            if child.isVisible()
        )
        self._metrics.memory_usage_mb = (total_pixels * 4) / (1024 * 1024)  # 4 bytes per pixel
        
        self.metrics_updated.emit(self._metrics)
    
    def clear_cache(self) -> None:
        """Clear render cache."""
        with QMutex():
            self._render_cache.clear()


class ResponsivePreview(QWidget):
    """Preview widget that shows responsive layout behavior."""
    
    # Signals
    device_changed = pyqtSignal(DeviceProfile)
    orientation_changed = pyqtSignal(str)
    
    def __init__(self, 
                 responsive_engine: ResponsiveLayoutEngine,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self.responsive_engine = responsive_engine
        self._device_profiles = self._create_default_devices()
        self._current_device: Optional[DeviceProfile] = None
        self._preview_widget: Optional[QWidget] = None
        
        self._setup_ui()
        self._setup_connections()
    
    def _setup_ui(self) -> None:
        """Setup responsive preview UI."""
        layout = QVBoxLayout(self)
        
        # Device selection toolbar
        toolbar = self._create_device_toolbar()
        layout.addWidget(toolbar)
        
        # Preview area
        self.preview_frame = QFrame()
        self.preview_frame.setFrameStyle(QFrame.Shape.Box)
        self.preview_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 2px solid #ddd;
                border-radius: 8px;
            }
        """)
        
        self.preview_layout = QVBoxLayout(self.preview_frame)
        self.preview_layout.setContentsMargins(0, 0, 0, 0)
        
        layout.addWidget(self.preview_frame)
        
        # Set default device
        if self._device_profiles:
            self.set_device(self._device_profiles[0])
    
    def _create_device_toolbar(self) -> QToolBar:
        """Create device selection toolbar."""
        toolbar = QToolBar()
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        
        # Device selector
        device_combo = QComboBox()
        for device in self._device_profiles:
            device_combo.addItem(f"{device.name} ({device.screen_size.width()}x{device.screen_size.height()})")
        device_combo.currentIndexChanged.connect(self._on_device_selected)
        toolbar.addWidget(QLabel("Device:"))
        toolbar.addWidget(device_combo)
        
        toolbar.addSeparator()
        
        # Orientation buttons
        orientation_group = QButtonGroup(toolbar)
        
        landscape_btn = QToolButton()
        landscape_btn.setText("Landscape")
        landscape_btn.setCheckable(True)
        landscape_btn.setChecked(True)
        landscape_btn.clicked.connect(lambda: self._set_orientation("landscape"))
        orientation_group.addButton(landscape_btn)
        toolbar.addWidget(landscape_btn)
        
        portrait_btn = QToolButton()
        portrait_btn.setText("Portrait")
        portrait_btn.setCheckable(True)
        portrait_btn.clicked.connect(lambda: self._set_orientation("portrait"))
        orientation_group.addButton(portrait_btn)
        toolbar.addWidget(portrait_btn)
        
        toolbar.addSeparator()
        
        # Zoom controls
        zoom_label = QLabel("Zoom:")
        toolbar.addWidget(zoom_label)
        
        zoom_slider = QSlider(Qt.Orientation.Horizontal)
        zoom_slider.setRange(25, 200)  # 25% to 200%
        zoom_slider.setValue(100)
        zoom_slider.setFixedWidth(100)
        zoom_slider.valueChanged.connect(self._on_zoom_changed)
        toolbar.addWidget(zoom_slider)
        
        return toolbar
    
    def _create_default_devices(self) -> List[DeviceProfile]:
        """Create default device profiles."""
        return [
            DeviceProfile("Desktop HD", DeviceType.DESKTOP, QSize(1920, 1080), 96.0),
            DeviceProfile("Laptop", DeviceType.LAPTOP, QSize(1366, 768), 96.0),
            DeviceProfile("iPad", DeviceType.TABLET, QSize(1024, 768), 132.0, 2.0, True),
            DeviceProfile("iPhone", DeviceType.MOBILE, QSize(375, 667), 326.0, 3.0, True),
            DeviceProfile("Small Mobile", DeviceType.MOBILE, QSize(320, 568), 326.0, 2.0, True),
        ]
    
    def _setup_connections(self) -> None:
        """Setup signal connections."""
        pass
    
    def set_preview_widget(self, widget: QWidget) -> None:
        """Set the widget to preview."""
        # Remove existing preview
        if self._preview_widget:
            self.preview_layout.removeWidget(self._preview_widget)
            self._preview_widget.setParent(None)
        
        # Add new preview
        self._preview_widget = widget
        if widget:
            self.preview_layout.addWidget(widget)
            self._apply_device_constraints()
    
    def set_device(self, device: DeviceProfile) -> None:
        """Set the current device profile."""
        self._current_device = device
        self._apply_device_constraints()
        self.device_changed.emit(device)
        
        # Update responsive engine
        if self.responsive_engine:
            screen_props = ScreenProperties(
                width=device.screen_size.width(),
                height=device.screen_size.height(),
                dpi=device.dpi,
                scale_factor=device.scale_factor,
                is_touch_enabled=device.is_touch,
                orientation=device.orientation
            )
            self.responsive_engine.update_screen_properties(screen_props)
    
    def _apply_device_constraints(self) -> None:
        """Apply device size constraints to preview."""
        if not self._current_device or not self._preview_widget:
            return
        
        device_size = self._current_device.screen_size
        
        # Apply orientation
        if self._current_device.orientation == "portrait":
            device_size = QSize(device_size.height(), device_size.width())
        
        # Set preview frame size
        self.preview_frame.setFixedSize(device_size)
        
        # Resize preview widget
        if self._preview_widget:
            self._preview_widget.resize(device_size)
    
    def _on_device_selected(self, index: int) -> None:
        """Handle device selection."""
        if 0 <= index < len(self._device_profiles):
            self.set_device(self._device_profiles[index])
    
    def _set_orientation(self, orientation: str) -> None:
        """Set device orientation."""
        if self._current_device:
            self._current_device.orientation = orientation
            self._apply_device_constraints()
            self.orientation_changed.emit(orientation)
    
    def _on_zoom_changed(self, value: int) -> None:
        """Handle zoom level change."""
        zoom_level = value / 100.0
        
        if self.preview_frame:
            # Apply zoom transformation
            transform = QTransform()
            transform.scale(zoom_level, zoom_level)
            self.preview_frame.setTransform(transform)


class LayoutPreviewManager(BaseUIComponent):
    """Main manager for layout preview functionality."""
    
    # Signals
    preview_generated = pyqtSignal(str, QPixmap)  # layout_id, preview
    export_completed = pyqtSignal(str, str)  # layout_id, file_path
    preview_failed = pyqtSignal(str, str)  # layout_id, error_message
    
    def __init__(
        self,
        layout_manager: LayoutManager,
        responsive_engine: ResponsiveLayoutEngine,
        event_bus: EventBus,
        config_manager: ConfigurationManager,
        state_manager: Store,
        parent: Optional[QObject] = None
    ):
        super().__init__(event_bus, config_manager, state_manager, parent)
        
        self.layout_manager = layout_manager
        self.responsive_engine = responsive_engine
        
        # Core components
        self.renderer = PreviewRenderer(self)
        self.responsive_preview: Optional[ResponsivePreview] = None
        
        # Preview settings
        self.default_settings = PreviewSettings()
        self._preview_cache: Dict[str, QPixmap] = {}
        
        # Device profiles
        self.device_profiles = self._load_device_profiles()
        
        self._setup_connections()
    
    def _setup_component(self) -> None:
        """Setup preview manager."""
        # Subscribe to events
        self.subscribe_to_event("layout.preview_request", self._handle_preview_request)
        self.subscribe_to_event("layout.export_request", self._handle_export_request)
        
        # Load settings
        self._load_preview_settings()
        
        logger.info("Layout preview manager setup complete")
    
    def _setup_connections(self) -> None:
        """Setup signal connections."""
        self.renderer.render_completed.connect(self._on_render_completed)
        self.renderer.render_failed.connect(self._on_render_failed)
        self.renderer.metrics_updated.connect(self._on_metrics_updated)
    
    def _load_device_profiles(self) -> List[DeviceProfile]:
        """Load device profiles from configuration."""
        # Load custom device profiles or use defaults
        return [
            DeviceProfile("Desktop FHD", DeviceType.DESKTOP, QSize(1920, 1080), 96.0),
            DeviceProfile("Desktop QHD", DeviceType.DESKTOP, QSize(2560, 1440), 109.0),
            DeviceProfile("Laptop HD", DeviceType.LAPTOP, QSize(1366, 768), 96.0),
            DeviceProfile("MacBook Pro", DeviceType.LAPTOP, QSize(1440, 900), 110.0, 2.0),
            DeviceProfile("iPad Pro", DeviceType.TABLET, QSize(1024, 1366), 264.0, 2.0, True),
            DeviceProfile("iPad", DeviceType.TABLET, QSize(768, 1024), 132.0, 2.0, True),
            DeviceProfile("iPhone 14", DeviceType.MOBILE, QSize(390, 844), 460.0, 3.0, True),
            DeviceProfile("iPhone SE", DeviceType.MOBILE, QSize(375, 667), 326.0, 2.0, True),
            DeviceProfile("Android Large", DeviceType.MOBILE, QSize(412, 915), 440.0, 2.6, True),
        ]
    
    def _load_preview_settings(self) -> None:
        """Load preview settings from configuration."""
        self.default_settings.mode = PreviewMode(
            self.get_config("preview.default_mode", PreviewMode.LIVE.value)
        )
        self.default_settings.zoom_level = self.get_config("preview.default_zoom", 1.0)
        self.default_settings.show_grid = self.get_config("preview.show_grid", False)
        self.default_settings.animation_enabled = self.get_config("preview.animations", True)
        self.default_settings.auto_refresh = self.get_config("preview.auto_refresh", True)
    
    def create_responsive_preview(self, parent: Optional[QWidget] = None) -> ResponsivePreview:
        """Create a responsive preview widget."""
        self.responsive_preview = ResponsivePreview(self.responsive_engine, parent)
        return self.responsive_preview
    
    def generate_preview(
        self,
        layout_id: str,
        settings: Optional[PreviewSettings] = None,
        force_refresh: bool = False
    ) -> None:
        """Generate preview for a layout."""
        settings = settings or self.default_settings
        
        # Check cache first
        cache_key = f"{layout_id}_{hash(str(settings.__dict__))}"
        if not force_refresh and cache_key in self._preview_cache:
            self.preview_generated.emit(layout_id, self._preview_cache[cache_key])
            return
        
        # Get layout widget
        layout = self.layout_manager.get_layout(layout_id)
        if not layout or not layout.container:
            self.preview_failed.emit(layout_id, "Layout not found or has no container")
            return
        
        # Render preview
        self.renderer.render_widget(layout.container, settings, cache_key)
    
    def export_preview(
        self,
        layout_id: str,
        file_path: str,
        export_format: ExportFormat,
        settings: Optional[PreviewSettings] = None
    ) -> None:
        """Export layout preview to file."""
        settings = settings or self.default_settings
        
        def on_render_complete(pixmap: QPixmap):
            """Handle render completion for export."""
            try:
                success = False
                
                if export_format == ExportFormat.PNG:
                    success = pixmap.save(file_path, "PNG")
                elif export_format == ExportFormat.JPEG:
                    success = pixmap.save(file_path, "JPEG")
                elif export_format == ExportFormat.PDF:
                    success = self._export_to_pdf(pixmap, file_path)
                elif export_format == ExportFormat.SVG:
                    success = self._export_to_svg(layout_id, file_path)
                elif export_format == ExportFormat.HTML:
                    success = self._export_to_html(layout_id, file_path)
                elif export_format == ExportFormat.JSON:
                    success = self._export_to_json(layout_id, file_path)
                
                if success:
                    self.export_completed.emit(layout_id, file_path)
                else:
                    self.preview_failed.emit(layout_id, f"Failed to export to {export_format.name}")
                    
            except Exception as e:
                self.preview_failed.emit(layout_id, f"Export error: {e}")
        
        # Connect temporary handler
        self.renderer.render_completed.connect(on_render_complete)
        
        # Generate preview for export
        self.generate_preview(layout_id, settings, force_refresh=True)
    
    def _export_to_pdf(self, pixmap: QPixmap, file_path: str) -> bool:
        """Export pixmap to PDF."""
        try:
            from PyQt6.QtPrintSupport import QPrinter
            from PyQt6.QtGui import QPainter
            
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(file_path)
            printer.setPageSize(QPrinter.PageSize.A4)
            
            painter = QPainter(printer)
            rect = painter.viewport()
            size = pixmap.size()
            size.scale(rect.size(), Qt.AspectRatioMode.KeepAspectRatio)
            painter.setViewport(rect.x(), rect.y(), size.width(), size.height())
            painter.setWindow(pixmap.rect())
            painter.drawPixmap(0, 0, pixmap)
            painter.end()
            
            return True
        except Exception as e:
            logger.error(f"PDF export failed: {e}")
            return False
    
    def _export_to_svg(self, layout_id: str, file_path: str) -> bool:
        """Export layout to SVG."""
        # This would require SVG generation from the layout structure
        # For now, return False as not implemented
        logger.warning("SVG export not yet implemented")
        return False
    
    def _export_to_html(self, layout_id: str, file_path: str) -> bool:
        """Export layout to HTML."""
        try:
            layout = self.layout_manager.get_layout(layout_id)
            if not layout:
                return False
            
            html_content = self._generate_html_from_layout(layout)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            return True
        except Exception as e:
            logger.error(f"HTML export failed: {e}")
            return False
    
    def _export_to_json(self, layout_id: str, file_path: str) -> bool:
        """Export layout configuration to JSON."""
        try:
            layout = self.layout_manager.get_layout(layout_id)
            if not layout:
                return False
            
            # Convert layout configuration to dictionary
            layout_data = {
                'id': layout.config.id,
                'name': layout.config.name,
                'type': layout.config.layout_type.value,
                'geometry': {
                    'width': layout.config.geometry.width,
                    'height': layout.config.geometry.height,
                    'x': layout.config.geometry.x,
                    'y': layout.config.geometry.y
                },
                'items': [
                    {
                        'id': item.id,
                        'name': item.name,
                        'type': item.layout_type.value,
                        'geometry': {
                            'width': item.geometry.width,
                            'height': item.geometry.height,
                            'x': item.geometry.x,
                            'y': item.geometry.y
                        },
                        'visible': item.visible,
                        'properties': item.properties
                    }
                    for item in layout.config.items
                ],
                'properties': layout.config.properties,
                'version': layout.config.version
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(layout_data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            logger.error(f"JSON export failed: {e}")
            return False
    
    def _generate_html_from_layout(self, layout) -> str:
        """Generate HTML representation of layout."""
        # Basic HTML template
        html = """
<!DOCTYPE html>
<html>
<head>
    <title>Layout Preview - {name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
        .layout-container {{ 
            width: {width}px; 
            height: {height}px; 
            border: 1px solid #ccc; 
            position: relative;
            background: white;
        }}
        .layout-item {{ 
            position: absolute; 
            border: 1px solid #ddd;
            background: #f8f9fa;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
    </style>
</head>
<body>
    <h1>Layout: {name}</h1>
    <div class="layout-container">
        {items}
    </div>
</body>
</html>
        """.strip()
        
        # Generate items HTML
        items_html = ""
        for item in layout.config.items:
            items_html += f"""
        <div class="layout-item" style="
            left: {item.geometry.x}px;
            top: {item.geometry.y}px;
            width: {item.geometry.width}px;
            height: {item.geometry.height}px;
            display: {'block' if item.visible else 'none'};
        ">
            {item.name}
        </div>
            """.strip()
        
        return html.format(
            name=layout.config.name,
            width=layout.config.geometry.width,
            height=layout.config.geometry.height,
            items=items_html
        )
    
    def clear_preview_cache(self) -> None:
        """Clear the preview cache."""
        self._preview_cache.clear()
        self.renderer.clear_cache()
        logger.debug("Preview cache cleared")
    
    def get_device_profile(self, name: str) -> Optional[DeviceProfile]:
        """Get device profile by name."""
        for profile in self.device_profiles:
            if profile.name == name:
                return profile
        return None
    
    def add_device_profile(self, profile: DeviceProfile) -> None:
        """Add a custom device profile."""
        self.device_profiles.append(profile)
        logger.debug(f"Added device profile: {profile.name}")
    
    # Event handlers
    def _on_render_completed(self, pixmap: QPixmap) -> None:
        """Handle render completion."""
        # Store in cache if needed
        # The renderer handles caching internally
        pass
    
    def _on_render_failed(self, error_message: str) -> None:
        """Handle render failure."""
        logger.error(f"Preview render failed: {error_message}")
    
    def _on_metrics_updated(self, metrics: PreviewMetrics) -> None:
        """Handle metrics update."""
        # Could emit performance warnings if needed
        if metrics.render_time_ms > 1000:  # 1 second threshold
            logger.warning(f"Slow preview render: {metrics.render_time_ms:.1f}ms")
    
    def _handle_preview_request(self, event_data: Dict[str, Any]) -> None:
        """Handle preview request event."""
        layout_id = event_data.get("layout_id")
        if layout_id:
            settings = PreviewSettings()
            # Apply any settings from event data
            if "mode" in event_data:
                settings.mode = PreviewMode(event_data["mode"])
            if "device" in event_data:
                device_name = event_data["device"]
                settings.device_profile = self.get_device_profile(device_name)
            
            self.generate_preview(layout_id, settings)
    
    def _handle_export_request(self, event_data: Dict[str, Any]) -> None:
        """Handle export request event."""
        layout_id = event_data.get("layout_id")
        file_path = event_data.get("file_path")
        export_format = event_data.get("format", "PNG")
        
        if layout_id and file_path:
            format_enum = ExportFormat[export_format.upper()]
            self.export_preview(layout_id, file_path, format_enum)