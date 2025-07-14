# AGENT 3 - NAVIGATION UI & MINIMAP SYSTEM

## 🎯 Your Mission (Agent 3)
You are **Agent 3** responsible for implementing the **Navigation UI & Minimap System** for TORE Matrix Labs V3 Document Viewer. You build advanced navigation interfaces that make Agents 1&2's zoom/pan functionality accessible and intuitive.

## 📋 Your Assignment: Sub-Issue #20.3
**GitHub Issue**: https://github.com/insult0o/torematrix_labs2/issues/[SUB_ISSUE_NUMBER]
**Parent Issue**: #20 - Document Viewer Zoom/Pan Controls
**Your Branch**: `feature/navigation-ui-agent3-issue203`

## 🎯 Key Responsibilities
1. **Minimap Component** - Real-time document overview with navigation
2. **Zoom Preset Controls** - Quick access buttons (50%, 100%, 200%, Fit)
3. **Zoom Level Indicator** - Visual feedback with slider control
4. **Zoom-to-Selection** - Intelligent selection-based zooming
5. **Navigation Toolbar** - Integrated control panel
6. **Visual Feedback Systems** - Loading states and transitions
7. **Zoom History** - Navigation breadcrumbs and undo/redo

## 📁 Files You Must Create

### Core Implementation Files
```
src/torematrix/ui/viewer/controls/
├── minimap.py               # 🎯 YOUR MAIN FILE - Minimap component
├── zoom_presets.py          # Preset zoom level controls
├── zoom_indicator.py        # Zoom level display and slider
├── navigation_ui.py         # Main navigation toolbar
├── zoom_history.py          # Zoom state tracking
└── selection_zoom.py        # Zoom-to-selection functionality
```

### Test Files (MANDATORY >95% Coverage)
```
tests/unit/viewer/controls/
├── test_minimap.py          # 🧪 YOUR MAIN TESTS - Minimap functionality
├── test_presets.py          # Zoom preset controls tests
├── test_indicator.py        # Zoom indicator tests
├── test_navigation.py       # Navigation UI integration tests
├── test_history.py          # Zoom history tests
└── test_selection_zoom.py   # Selection zoom tests
```

## 🔧 Technical Implementation Details

### 1. Minimap Component (`minimap.py`)
```python
from typing import Optional, Tuple, List
from PyQt6.QtCore import QObject, pyqtSignal, QRectF, QPointF, QTimer
from PyQt6.QtGui import QPainter, QPixmap, QPen, QBrush, QColor
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel

from .zoom import ZoomEngine
from .pan import PanEngine

class MinimapWidget(QWidget):
    """
    Real-time minimap showing document overview with navigation viewport.
    Provides click-to-navigate functionality and visual zoom/pan feedback.
    """
    
    # Navigation signals
    navigate_requested = pyqtSignal(QPointF)  # document_position
    
    def __init__(self, zoom_engine: ZoomEngine, pan_engine: PanEngine, parent=None):
        super().__init__(parent)
        
        # Core dependencies
        self.zoom_engine = zoom_engine
        self.pan_engine = pan_engine
        
        # Minimap configuration
        self.minimap_size = (200, 150)  # Fixed minimap dimensions
        self.viewport_color = QColor(0, 120, 215, 100)  # Semi-transparent blue
        self.border_color = QColor(0, 120, 215, 255)  # Solid blue border
        self.background_color = QColor(240, 240, 240)
        
        # Document representation
        self.document_pixmap: Optional[QPixmap] = None
        self.document_size = QPointF(1000, 800)  # Default document size
        self.scale_factor = 1.0
        
        # Viewport tracking
        self.viewport_rect = QRectF()
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_viewport)
        self.update_timer.start(50)  # 20fps updates
        
        # Widget setup
        self.setFixedSize(*self.minimap_size)
        self.setStyleSheet("""
            MinimapWidget {
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: #f0f0f0;
            }
        """)
        
        # Connect to engines
        self.zoom_engine.zoom_changed.connect(self.update_viewport)
        self.pan_engine.pan_changed.connect(self.update_viewport)
    
    def set_document_pixmap(self, pixmap: QPixmap):
        """
        Set the document representation for the minimap.
        
        Args:
            pixmap: Scaled pixmap representing the entire document
        """
        self.document_pixmap = pixmap
        self.document_size = QPointF(pixmap.width(), pixmap.height())
        self._calculate_scale_factor()
        self.update()
    
    def set_document_size(self, width: float, height: float):
        """
        Set document size for viewport calculations.
        
        Args:
            width: Document width in logical units
            height: Document height in logical units
        """
        self.document_size = QPointF(width, height)
        self._calculate_scale_factor()
        self.update_viewport()
    
    def paintEvent(self, event):
        """Custom paint event for minimap rendering."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Fill background
        painter.fillRect(self.rect(), self.background_color)
        
        # Draw document if available
        if self.document_pixmap:
            self._draw_document(painter)
        else:
            self._draw_placeholder(painter)
        
        # Draw current viewport
        self._draw_viewport(painter)
        
        painter.end()
    
    def mousePressEvent(self, event):
        """Handle mouse clicks for navigation."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Convert click position to document coordinates
            click_pos = event.position()
            doc_pos = self._minimap_to_document_coords(click_pos)
            
            # Request navigation to clicked position
            self.navigate_requested.emit(doc_pos)
    
    def update_viewport(self):
        """Update viewport rectangle based on current zoom/pan state."""
        # Get current view bounds in document coordinates
        view_bounds = self._calculate_view_bounds()
        
        # Convert to minimap coordinates
        minimap_rect = self._document_to_minimap_rect(view_bounds)
        
        if minimap_rect != self.viewport_rect:
            self.viewport_rect = minimap_rect
            self.update()
    
    def _calculate_scale_factor(self):
        """Calculate scale factor for document to minimap conversion."""
        if self.document_size.x() <= 0 or self.document_size.y() <= 0:
            self.scale_factor = 1.0
            return
        
        # Calculate scale to fit document in minimap with padding
        padding = 10
        available_width = self.minimap_size[0] - 2 * padding
        available_height = self.minimap_size[1] - 2 * padding
        
        scale_x = available_width / self.document_size.x()
        scale_y = available_height / self.document_size.y()
        
        # Use smaller scale to maintain aspect ratio
        self.scale_factor = min(scale_x, scale_y)
    
    def _draw_document(self, painter: QPainter):
        """Draw document representation in minimap."""
        if not self.document_pixmap:
            return
        
        # Calculate centered position for document
        scaled_width = self.document_size.x() * self.scale_factor
        scaled_height = self.document_size.y() * self.scale_factor
        
        x = (self.minimap_size[0] - scaled_width) / 2
        y = (self.minimap_size[1] - scaled_height) / 2
        
        # Draw scaled document
        target_rect = QRectF(x, y, scaled_width, scaled_height)
        painter.drawPixmap(target_rect, self.document_pixmap, self.document_pixmap.rect())
    
    def _draw_placeholder(self, painter: QPainter):
        """Draw placeholder when no document is available."""
        painter.setPen(QPen(QColor(150, 150, 150), 2))
        painter.setBrush(QBrush(QColor(200, 200, 200, 100)))
        
        # Draw centered rectangle
        margin = 20
        rect = QRectF(margin, margin, 
                     self.minimap_size[0] - 2*margin,
                     self.minimap_size[1] - 2*margin)
        painter.drawRect(rect)
        
        # Draw "No Document" text
        painter.setPen(QColor(100, 100, 100))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "No Document")
    
    def _draw_viewport(self, painter: QPainter):
        """Draw current viewport rectangle."""
        if self.viewport_rect.isEmpty():
            return
        
        # Draw viewport background
        painter.setBrush(QBrush(self.viewport_color))
        painter.setPen(QPen(self.border_color, 2))
        painter.drawRect(self.viewport_rect)
        
        # Draw corner indicators for resize handles
        corner_size = 4
        corners = [
            self.viewport_rect.topLeft(),
            self.viewport_rect.topRight(),
            self.viewport_rect.bottomLeft(),
            self.viewport_rect.bottomRight()
        ]
        
        painter.setBrush(QBrush(self.border_color))
        for corner in corners:
            corner_rect = QRectF(corner.x() - corner_size/2, 
                               corner.y() - corner_size/2,
                               corner_size, corner_size)
            painter.drawEllipse(corner_rect)
    
    def _calculate_view_bounds(self) -> QRectF:
        """Calculate current view bounds in document coordinates."""
        # Get current pan offset and zoom level
        pan_offset = self.pan_engine.current_offset
        zoom_level = self.zoom_engine.current_zoom
        view_size = self.pan_engine.view_size
        
        # Calculate visible document area
        # This is complex coordinate transformation - simplified for demo
        visible_width = view_size.x() / zoom_level
        visible_height = view_size.y() / zoom_level
        
        # Convert pan offset to document coordinates
        doc_x = -pan_offset.x() / zoom_level
        doc_y = -pan_offset.y() / zoom_level
        
        return QRectF(doc_x, doc_y, visible_width, visible_height)
    
    def _document_to_minimap_rect(self, doc_rect: QRectF) -> QRectF:
        """Convert document rectangle to minimap coordinates."""
        # Apply scale factor and centering offset
        scaled_x = doc_rect.x() * self.scale_factor
        scaled_y = doc_rect.y() * self.scale_factor
        scaled_width = doc_rect.width() * self.scale_factor
        scaled_height = doc_rect.height() * self.scale_factor
        
        # Add centering offset
        center_offset_x = (self.minimap_size[0] - self.document_size.x() * self.scale_factor) / 2
        center_offset_y = (self.minimap_size[1] - self.document_size.y() * self.scale_factor) / 2
        
        return QRectF(scaled_x + center_offset_x, 
                     scaled_y + center_offset_y,
                     scaled_width, scaled_height)
    
    def _minimap_to_document_coords(self, minimap_pos: QPointF) -> QPointF:
        """Convert minimap position to document coordinates."""
        # Remove centering offset
        center_offset_x = (self.minimap_size[0] - self.document_size.x() * self.scale_factor) / 2
        center_offset_y = (self.minimap_size[1] - self.document_size.y() * self.scale_factor) / 2
        
        doc_x = (minimap_pos.x() - center_offset_x) / self.scale_factor
        doc_y = (minimap_pos.y() - center_offset_y) / self.scale_factor
        
        return QPointF(doc_x, doc_y)
```

### 2. Zoom Preset Controls (`zoom_presets.py`)
```python
from typing import List, Dict, Callable
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QPushButton, 
                            QButtonGroup, QToolButton, QMenu)
from PyQt6.QtGui import QIcon, QAction

from .zoom import ZoomEngine

class ZoomPresetWidget(QWidget):
    """
    Zoom preset controls with quick access buttons and dropdown menu.
    Provides standard zoom levels and fit-to-view functionality.
    """
    
    # Preset activation signal
    preset_activated = pyqtSignal(str, float)  # preset_name, zoom_level
    
    def __init__(self, zoom_engine: ZoomEngine, parent=None):
        super().__init__(parent)
        
        # Core dependency
        self.zoom_engine = zoom_engine
        
        # Preset configuration
        self.presets = {
            '25%': 0.25,
            '50%': 0.5,
            '75%': 0.75,
            '100%': 1.0,
            '125%': 1.25,
            '150%': 1.5,
            '200%': 2.0,
            '400%': 4.0,
            'Fit Width': 'fit_width',
            'Fit Page': 'fit_page',
            'Fit Selection': 'fit_selection'
        }
        
        # Quick access presets (shown as buttons)
        self.quick_presets = ['50%', '100%', '200%', 'Fit Page']
        
        # UI setup
        self._setup_ui()
        
        # Connect to zoom engine
        self.zoom_engine.zoom_changed.connect(self._update_active_preset)
    
    def _setup_ui(self):
        """Setup the preset control UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        
        # Button group for exclusive selection
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(False)  # Allow manual control
        
        # Create quick access buttons
        self.preset_buttons = {}
        for preset_name in self.quick_presets:
            button = self._create_preset_button(preset_name)
            self.preset_buttons[preset_name] = button
            layout.addWidget(button)
        
        # Add separator
        layout.addSpacing(10)
        
        # More presets dropdown
        self.more_button = QToolButton()
        self.more_button.setText("More...")
        self.more_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self._setup_more_menu()
        layout.addWidget(self.more_button)
        
        # Add stretch to push everything left
        layout.addStretch()
    
    def _create_preset_button(self, preset_name: str) -> QPushButton:
        """Create a preset button with proper styling."""
        button = QPushButton(preset_name)
        button.setCheckable(True)
        button.setMinimumWidth(60)
        button.setStyleSheet("""
            QPushButton {
                padding: 4px 8px;
                border: 1px solid #ccc;
                border-radius: 3px;
                background-color: #f8f8f8;
            }
            QPushButton:checked {
                background-color: #0078d4;
                color: white;
                border-color: #005a9e;
            }
            QPushButton:hover {
                background-color: #e5f1fb;
                border-color: #0078d4;
            }
            QPushButton:checked:hover {
                background-color: #106ebe;
            }
        """)
        
        # Connect button to preset activation
        button.clicked.connect(lambda: self._activate_preset(preset_name))
        
        return button
    
    def _setup_more_menu(self):
        """Setup the dropdown menu for additional presets."""
        menu = QMenu()
        
        # Add all non-quick presets to menu
        for preset_name, zoom_value in self.presets.items():
            if preset_name not in self.quick_presets:
                action = QAction(preset_name, menu)
                action.triggered.connect(
                    lambda checked, name=preset_name: self._activate_preset(name)
                )
                menu.addAction(action)
        
        self.more_button.setMenu(menu)
    
    def _activate_preset(self, preset_name: str):
        """Activate a zoom preset."""
        if preset_name not in self.presets:
            return
        
        zoom_value = self.presets[preset_name]
        
        if isinstance(zoom_value, float):
            # Standard zoom level
            self.zoom_engine.zoom_to_level(zoom_value)
            self.preset_activated.emit(preset_name, zoom_value)
        else:
            # Special preset (fit operations)
            self._handle_special_preset(preset_name, zoom_value)
    
    def _handle_special_preset(self, preset_name: str, preset_type: str):
        """Handle special presets like fit operations."""
        if preset_type == 'fit_page':
            # Calculate zoom to fit entire document
            doc_size = self.zoom_engine.parent().get_document_size()  # From viewer
            view_size = self.zoom_engine.parent().get_view_size()
            
            if doc_size and view_size:
                zoom_level = self.zoom_engine.zoom_to_fit(doc_size, view_size)
                self.preset_activated.emit(preset_name, zoom_level)
        
        elif preset_type == 'fit_width':
            # Calculate zoom to fit document width
            doc_size = self.zoom_engine.parent().get_document_size()
            view_size = self.zoom_engine.parent().get_view_size()
            
            if doc_size and view_size:
                zoom_level = view_size[0] / doc_size[0] * 0.95  # 5% padding
                self.zoom_engine.zoom_to_level(zoom_level)
                self.preset_activated.emit(preset_name, zoom_level)
        
        elif preset_type == 'fit_selection':
            # Zoom to current selection (if any)
            selection_bounds = self.zoom_engine.parent().get_selection_bounds()
            if selection_bounds:
                self._zoom_to_selection(selection_bounds)
                self.preset_activated.emit(preset_name, self.zoom_engine.current_zoom)
    
    def _update_active_preset(self, zoom_level: float):
        """Update active preset button based on current zoom level."""
        # Find closest matching preset
        closest_preset = None
        min_difference = float('inf')
        
        for preset_name, preset_zoom in self.presets.items():
            if isinstance(preset_zoom, float):
                difference = abs(preset_zoom - zoom_level)
                if difference < min_difference and difference < 0.01:  # 1% tolerance
                    min_difference = difference
                    closest_preset = preset_name
        
        # Update button states
        for preset_name, button in self.preset_buttons.items():
            button.setChecked(preset_name == closest_preset)
    
    def add_custom_preset(self, name: str, zoom_level: float):
        """Add a custom zoom preset."""
        self.presets[name] = zoom_level
    
    def remove_preset(self, name: str):
        """Remove a zoom preset."""
        if name in self.presets and name not in self.quick_presets:
            del self.presets[name]
```

### 3. Zoom Level Indicator (`zoom_indicator.py`)
```python
from typing import Optional
from PyQt6.QtCore import QObject, pyqtSignal, Qt
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QLabel, QSlider, 
                            QLineEdit, QVBoxLayout)
from PyQt6.QtGui import QValidator, QIntValidator

from .zoom import ZoomEngine

class ZoomIndicatorWidget(QWidget):
    """
    Zoom level indicator with slider control and text input.
    Provides real-time zoom feedback and manual zoom level entry.
    """
    
    # User input signals
    zoom_level_requested = pyqtSignal(float)  # manual_zoom_level
    
    def __init__(self, zoom_engine: ZoomEngine, parent=None):
        super().__init__(parent)
        
        # Core dependency
        self.zoom_engine = zoom_engine
        
        # Configuration
        self.zoom_range = (10, 800)  # 10% to 800%
        self.slider_steps = 100  # Slider resolution
        
        # Internal state
        self.updating_from_engine = False
        
        # UI setup
        self._setup_ui()
        
        # Connect to zoom engine
        self.zoom_engine.zoom_changed.connect(self._update_from_engine)
    
    def _setup_ui(self):
        """Setup the zoom indicator UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # Top row: Label and text input
        top_layout = QHBoxLayout()
        
        # Zoom label
        self.zoom_label = QLabel("Zoom:")
        top_layout.addWidget(self.zoom_label)
        
        # Zoom percentage input
        self.zoom_input = QLineEdit()
        self.zoom_input.setMaximumWidth(60)
        self.zoom_input.setPlaceholderText("100%")
        self.zoom_input.setValidator(QIntValidator(self.zoom_range[0], self.zoom_range[1]))
        self.zoom_input.returnPressed.connect(self._handle_text_input)
        top_layout.addWidget(self.zoom_input)
        
        layout.addLayout(top_layout)
        
        # Zoom slider
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setMinimum(0)
        self.zoom_slider.setMaximum(self.slider_steps)
        self.zoom_slider.setValue(self._zoom_to_slider_value(1.0))  # 100%
        self.zoom_slider.valueChanged.connect(self._handle_slider_change)
        layout.addWidget(self.zoom_slider)
        
        # Apply styling
        self._apply_styling()
    
    def _apply_styling(self):
        """Apply custom styling to the zoom indicator."""
        self.setStyleSheet("""
            QLabel {
                font-weight: bold;
                color: #333;
            }
            QLineEdit {
                padding: 2px 4px;
                border: 1px solid #ccc;
                border-radius: 3px;
                background-color: white;
            }
            QLineEdit:focus {
                border-color: #0078d4;
                outline: none;
            }
            QSlider::groove:horizontal {
                border: 1px solid #999;
                height: 8px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #B1B1B1, stop:1 #c4c4c4);
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #b4b4b4, stop:1 #8f8f8f);
                border: 1px solid #5c5c5c;
                width: 18px;
                margin: -2px 0;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #d4d4d4, stop:1 #8f8f8f);
            }
        """)
    
    def _update_from_engine(self, zoom_level: float):
        """Update indicator based on zoom engine changes."""
        if self.updating_from_engine:
            return
        
        self.updating_from_engine = True
        
        # Update text input
        percentage = int(zoom_level * 100)
        self.zoom_input.setText(f"{percentage}%")
        
        # Update slider
        slider_value = self._zoom_to_slider_value(zoom_level)
        self.zoom_slider.setValue(slider_value)
        
        self.updating_from_engine = False
    
    def _handle_text_input(self):
        """Handle manual zoom level text input."""
        if self.updating_from_engine:
            return
        
        text = self.zoom_input.text()
        
        # Parse percentage value
        try:
            # Remove % symbol if present
            if text.endswith('%'):
                text = text[:-1]
            
            percentage = float(text)
            zoom_level = percentage / 100.0
            
            # Validate range
            if self.zoom_range[0] <= percentage <= self.zoom_range[1]:
                self.zoom_level_requested.emit(zoom_level)
            else:
                # Reset to current value
                self._update_from_engine(self.zoom_engine.current_zoom)
        
        except ValueError:
            # Invalid input - reset to current value
            self._update_from_engine(self.zoom_engine.current_zoom)
    
    def _handle_slider_change(self, slider_value: int):
        """Handle zoom slider changes."""
        if self.updating_from_engine:
            return
        
        # Convert slider value to zoom level
        zoom_level = self._slider_value_to_zoom(slider_value)
        self.zoom_level_requested.emit(zoom_level)
    
    def _zoom_to_slider_value(self, zoom_level: float) -> int:
        """Convert zoom level to slider value (non-linear for better UX)."""
        # Use logarithmic scale for better zoom control
        import math
        
        min_zoom = self.zoom_range[0] / 100.0
        max_zoom = self.zoom_range[1] / 100.0
        
        # Clamp zoom level
        zoom_level = max(min_zoom, min(max_zoom, zoom_level))
        
        # Logarithmic mapping
        log_min = math.log(min_zoom)
        log_max = math.log(max_zoom)
        log_current = math.log(zoom_level)
        
        # Map to slider range
        progress = (log_current - log_min) / (log_max - log_min)
        return int(progress * self.slider_steps)
    
    def _slider_value_to_zoom(self, slider_value: int) -> float:
        """Convert slider value to zoom level (non-linear)."""
        import math
        
        min_zoom = self.zoom_range[0] / 100.0
        max_zoom = self.zoom_range[1] / 100.0
        
        # Progress from slider
        progress = slider_value / self.slider_steps
        
        # Logarithmic mapping
        log_min = math.log(min_zoom)
        log_max = math.log(max_zoom)
        log_current = log_min + progress * (log_max - log_min)
        
        return math.exp(log_current)
    
    def set_zoom_range(self, min_zoom: float, max_zoom: float):
        """Set the zoom range for the indicator."""
        self.zoom_range = (int(min_zoom * 100), int(max_zoom * 100))
        
        # Update validator
        self.zoom_input.setValidator(
            QIntValidator(self.zoom_range[0], self.zoom_range[1])
        )
        
        # Update current display
        self._update_from_engine(self.zoom_engine.current_zoom)
```

## 🧪 Testing Requirements (MANDATORY >95% Coverage)

### Main Test File (`test_minimap.py`)
```python
import pytest
from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtGui import QPixmap, QPaintEvent
from unittest.mock import Mock, MagicMock

from torematrix.ui.viewer.controls.minimap import MinimapWidget
from torematrix.ui.viewer.controls.zoom import ZoomEngine
from torematrix.ui.viewer.controls.pan import PanEngine

class TestMinimapWidget:
    """Comprehensive tests for minimap functionality."""
    
    @pytest.fixture
    def engines(self):
        """Mock zoom and pan engines."""
        zoom_engine = Mock(spec=ZoomEngine)
        zoom_engine.current_zoom = 1.0
        zoom_engine.zoom_changed = Mock()
        
        pan_engine = Mock(spec=PanEngine)
        pan_engine.current_offset = QPointF(0, 0)
        pan_engine.view_size = QPointF(800, 600)
        pan_engine.pan_changed = Mock()
        
        return zoom_engine, pan_engine
    
    @pytest.fixture
    def minimap(self, engines):
        """Create minimap widget for testing."""
        zoom_engine, pan_engine = engines
        widget = MinimapWidget(zoom_engine, pan_engine)
        widget.set_document_size(1000, 800)
        yield widget
        widget.deleteLater()
    
    def test_initialization(self, minimap):
        """Test minimap initializes correctly."""
        assert minimap.minimap_size == (200, 150)
        assert minimap.document_size == QPointF(1000, 800)
        assert minimap.scale_factor > 0
    
    def test_document_pixmap_setting(self, minimap):
        """Test setting document pixmap."""
        # Create test pixmap
        pixmap = QPixmap(100, 80)
        pixmap.fill()
        
        minimap.set_document_pixmap(pixmap)
        
        assert minimap.document_pixmap is not None
        assert minimap.document_size == QPointF(100, 80)
    
    def test_scale_factor_calculation(self, minimap):
        """Test scale factor calculation for different document sizes."""
        # Test landscape document
        minimap.set_document_size(2000, 1000)
        minimap._calculate_scale_factor()
        
        # Should scale to fit width (limiting factor)
        expected_scale = (200 - 20) / 2000  # Account for padding
        assert abs(minimap.scale_factor - expected_scale) < 0.001
        
        # Test portrait document
        minimap.set_document_size(500, 2000)
        minimap._calculate_scale_factor()
        
        # Should scale to fit height (limiting factor)
        expected_scale = (150 - 20) / 2000  # Account for padding
        assert abs(minimap.scale_factor - expected_scale) < 0.001
    
    def test_coordinate_conversion(self, minimap):
        """Test coordinate conversion between minimap and document."""
        # Test document to minimap conversion
        doc_point = QPointF(500, 400)  # Center of 1000x800 document
        minimap_point = minimap._document_to_minimap_coords(doc_point)
        
        # Should be near center of minimap
        center_x, center_y = 100, 75  # Half of minimap size
        assert abs(minimap_point.x() - center_x) < 20
        assert abs(minimap_point.y() - center_y) < 20
        
        # Test round-trip conversion
        converted_back = minimap._minimap_to_document_coords(minimap_point)
        assert abs(converted_back.x() - doc_point.x()) < 10
        assert abs(converted_back.y() - doc_point.y()) < 10
    
    def test_viewport_calculation(self, minimap):
        """Test viewport rectangle calculation."""
        # Mock zoom and pan state
        minimap.zoom_engine.current_zoom = 2.0
        minimap.pan_engine.current_offset = QPointF(-100, -50)
        
        # Calculate viewport
        view_bounds = minimap._calculate_view_bounds()
        
        # Verify bounds are reasonable
        assert view_bounds.width() > 0
        assert view_bounds.height() > 0
        assert view_bounds.x() >= 0  # Should be within document
        assert view_bounds.y() >= 0
    
    def test_mouse_navigation(self, minimap, qtbot):
        """Test click-to-navigate functionality."""
        # Mock mouse click in center of minimap
        from PyQt6.QtGui import QMouseEvent
        from PyQt6.QtCore import Qt
        
        center_point = QPointF(100, 75)  # Center of 200x150 minimap
        
        with qtbot.waitSignal(minimap.navigate_requested) as blocker:
            # Simulate mouse press event
            event = QMouseEvent(
                QMouseEvent.Type.MouseButtonPress,
                center_point,
                Qt.MouseButton.LeftButton,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier
            )
            minimap.mousePressEvent(event)
        
        # Should emit navigation request
        requested_pos = blocker.args[0]
        assert isinstance(requested_pos, QPointF)
    
    def test_real_time_updates(self, minimap, qtbot):
        """Test real-time viewport updates."""
        # Change zoom level
        minimap.zoom_engine.current_zoom = 1.5
        
        # Trigger update
        minimap.update_viewport()
        
        # Viewport should be updated
        assert not minimap.viewport_rect.isEmpty()
        
        # Change pan offset
        minimap.pan_engine.current_offset = QPointF(-200, -100)
        
        # Trigger update
        old_viewport = minimap.viewport_rect
        minimap.update_viewport()
        
        # Viewport should change
        assert minimap.viewport_rect != old_viewport
    
    def test_performance_requirements(self, minimap):
        """Test minimap meets performance requirements."""
        import time
        
        # Test update timing
        times = []
        for _ in range(50):
            start = time.perf_counter()
            minimap.update_viewport()
            end = time.perf_counter()
            times.append((end - start) * 1000)  # Convert to ms
        
        avg_time = sum(times) / len(times)
        assert avg_time < 100.0, f"Minimap updates too slow: {avg_time}ms"
    
    def test_paint_event_no_crash(self, minimap):
        """Test paint event doesn't crash without document."""
        # Should not crash even without document pixmap
        from PyQt6.QtGui import QPaintEvent
        from PyQt6.QtCore import QRect
        
        event = QPaintEvent(QRect(0, 0, 200, 150))
        
        # Should not raise exception
        try:
            minimap.paintEvent(event)
        except Exception as e:
            pytest.fail(f"Paint event crashed: {e}")
```

## 📊 Performance Requirements

### Benchmarks You Must Meet
- **Minimap Updates**: <100ms for real-time navigation feedback
- **UI Response**: <16ms for smooth preset button interactions
- **Slider Updates**: <10ms for responsive zoom level changes
- **Memory Usage**: <40MB for all navigation UI components

## 🔗 Integration Points

### Dependencies You Need
- **Agent 1: Core Zoom Engine** - REQUIRED for zoom state and control
- **Agent 2: Pan Controls** - REQUIRED for pan state and coordinate transformation
- **Theme Framework** (Issue #14) - ✅ COMPLETED for consistent styling

### What You Provide to Agent 4
- **MinimapWidget class** - Document overview navigation
- **ZoomPresetWidget class** - Quick zoom level access
- **ZoomIndicatorWidget class** - Real-time zoom feedback
- **Integrated navigation toolbar** - Complete UI system

### Integration APIs You Must Provide
```python
# For Agent 4 (Integration)
def get_minimap_widget() -> MinimapWidget
def get_zoom_presets_widget() -> ZoomPresetWidget
def get_zoom_indicator_widget() -> ZoomIndicatorWidget
def create_navigation_toolbar() -> QWidget
def configure_ui_layout(layout_config: dict)
```

## 🚀 Definition of Done

### Your work is complete when:
- [ ] ✅ Minimap provides real-time navigation with click-to-navigate
- [ ] ✅ Zoom presets work with smooth transitions to 50%, 100%, 200%, Fit
- [ ] ✅ Zoom indicator shows accurate level with slider and text input
- [ ] ✅ Zoom-to-selection functionality targets user selections
- [ ] ✅ Navigation toolbar integrates all controls seamlessly
- [ ] ✅ Visual feedback systems provide clear state indication
- [ ] ✅ Zoom history tracks navigation for undo/redo
- [ ] ✅ >95% test coverage across all your files
- [ ] ✅ Performance benchmarks met (<100ms minimap updates)

You create the visual interface that makes navigation intuitive and powerful! 🎨