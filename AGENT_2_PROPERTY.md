# AGENT 2 - PROPERTY DISPLAY & LAYOUT

## 🎯 Your Assignment
You are **Agent 2** responsible for creating the main property panel widget with responsive layout, property display components, and basic UI structure. This is a focused 2-day task building on Agent 1's foundation.

## 📋 Your Specific Tasks (2 Days)

### Day 1: Main Panel & Layout
1. **PropertyPanel Widget** - Main container with layout management
2. **Layout System** - Responsive layout for different panel sizes
3. **Property Selection** - Click handling and visual feedback
4. **Basic Integration** - Connect with Agent 1's event system

### Day 2: Display Components
1. **PropertyDisplayWidget** - Individual property display
2. **MetadataDisplayWidget** - Rich formatting for metadata
3. **ConfidenceScoreWidget** - Visual confidence indicators
4. **Comprehensive Testing** - UI and interaction tests

## 🏗️ Files You Must Create

### Day 1 Files

**File**: `src/torematrix/ui/components/property_panel/panel.py`
```python
"""Main property panel widget with layout management"""

from typing import Optional, Dict, Any, List
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QFrame
from PyQt6.QtCore import pyqtSignal, Qt
from ...core.elements import Element
from .events import PropertyNotificationCenter
from .models import PropertyValue

class PropertyPanel(QWidget):
    """Main property panel widget"""
    
    property_selected = pyqtSignal(str, str)  # element_id, property_name
    property_edit_requested = pyqtSignal(str, str)  # element_id, property_name
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._current_element: Optional[Element] = None
        self._property_widgets: Dict[str, QWidget] = {}
        self._notification_center: Optional[PropertyNotificationCenter] = None
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Initialize the property panel UI structure"""
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(4, 4, 4, 4)
        self.layout().setSpacing(2)
        
        # Create scroll area for properties
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Create content widget
        self._content_widget = QWidget()
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(2, 2, 2, 2)
        self._content_layout.setSpacing(1)
        
        self._scroll_area.setWidget(self._content_widget)
        self.layout().addWidget(self._scroll_area)
        
        # Add stretch to push properties to top
        self._content_layout.addStretch()
    
    def set_notification_center(self, center: PropertyNotificationCenter) -> None:
        """Set the property notification center"""
        self._notification_center = center
        # Connect to property change events
        center.property_changed.connect(self._on_property_changed)
    
    def set_element(self, element: Optional[Element]) -> None:
        """Set the current element for property display"""
        self._current_element = element
        self._refresh_properties()
    
    def _refresh_properties(self) -> None:
        """Refresh the property display"""
        # Clear existing widgets
        self._clear_property_widgets()
        
        if not self._current_element:
            return
        
        # Create property widgets for current element
        self._create_property_widgets()
    
    def _clear_property_widgets(self) -> None:
        """Clear all property widgets"""
        for widget in self._property_widgets.values():
            self._content_layout.removeWidget(widget)
            widget.deleteLater()
        self._property_widgets.clear()
    
    def _create_property_widgets(self) -> None:
        """Create property widgets for current element"""
        if not self._current_element:
            return
        
        # Import here to avoid circular imports
        from .display import PropertyDisplayWidget
        
        # Get element properties
        properties = self._get_element_properties()
        
        for prop_name, prop_value in properties.items():
            widget = PropertyDisplayWidget(
                property_name=prop_name,
                value=prop_value,
                property_type=self._get_property_type(prop_name)
            )
            
            # Connect signals
            widget.property_clicked.connect(
                lambda name: self._on_property_clicked(name)
            )
            widget.edit_requested.connect(
                lambda name: self._on_edit_requested(name)
            )
            
            self._property_widgets[prop_name] = widget
            # Insert before stretch
            self._content_layout.insertWidget(
                self._content_layout.count() - 1, widget
            )
    
    def _get_element_properties(self) -> Dict[str, Any]:
        """Get properties for current element"""
        if not self._current_element:
            return {}
        
        # Return element attributes as properties
        return {
            "text": getattr(self._current_element, "text", ""),
            "type": getattr(self._current_element, "type", ""),
            "x": getattr(self._current_element, "x", 0.0),
            "y": getattr(self._current_element, "y", 0.0),
            "width": getattr(self._current_element, "width", 0.0),
            "height": getattr(self._current_element, "height", 0.0),
            "confidence": getattr(self._current_element, "confidence", 0.0),
            "page": getattr(self._current_element, "page", 1),
        }
    
    def _get_property_type(self, property_name: str) -> str:
        """Get property type for display"""
        type_mapping = {
            "text": "string",
            "type": "choice",
            "x": "coordinate",
            "y": "coordinate", 
            "width": "coordinate",
            "height": "coordinate",
            "confidence": "confidence",
            "page": "integer"
        }
        return type_mapping.get(property_name, "string")
    
    def _on_property_clicked(self, property_name: str) -> None:
        """Handle property click"""
        if self._current_element:
            self.property_selected.emit(self._current_element.id, property_name)
    
    def _on_edit_requested(self, property_name: str) -> None:
        """Handle edit request"""
        if self._current_element:
            self.property_edit_requested.emit(self._current_element.id, property_name)
    
    def _on_property_changed(self, event) -> None:
        """Handle property change events"""
        if (self._current_element and 
            event.element_id == self._current_element.id and
            event.property_name in self._property_widgets):
            
            widget = self._property_widgets[event.property_name]
            if hasattr(widget, 'update_value'):
                widget.update_value(event.new_value)
    
    def resizeEvent(self, event):
        """Handle resize events for responsive layout"""
        super().resizeEvent(event)
        # Update layout based on width
        self._update_layout_for_width(self.width())
    
    def _update_layout_for_width(self, width: int) -> None:
        """Update layout based on panel width"""
        # Adjust spacing and margins for narrow panels
        if width < 200:
            self._content_layout.setContentsMargins(1, 1, 1, 1)
            self._content_layout.setSpacing(0)
        else:
            self._content_layout.setContentsMargins(2, 2, 2, 2) 
            self._content_layout.setSpacing(1)
```

**File**: `src/torematrix/ui/components/property_panel/layout.py`
```python
"""Layout management for property panel"""

from typing import List, Dict, Any, Optional
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame, QSizePolicy
from PyQt6.QtCore import Qt, QSize

class ResponsivePropertyLayout:
    """Responsive layout manager for property display"""
    
    def __init__(self, parent_widget: QWidget):
        self.parent = parent_widget
        self._min_width = 150
        self._compact_threshold = 200
        self._normal_threshold = 300
    
    def update_layout(self, width: int, property_widgets: List[QWidget]) -> None:
        """Update layout based on available width"""
        if width < self._compact_threshold:
            self._apply_compact_layout(property_widgets)
        elif width < self._normal_threshold:
            self._apply_normal_layout(property_widgets)
        else:
            self._apply_wide_layout(property_widgets)
    
    def _apply_compact_layout(self, widgets: List[QWidget]) -> None:
        """Apply compact layout for narrow panels"""
        for widget in widgets:
            if hasattr(widget, 'set_compact_mode'):
                widget.set_compact_mode(True)
    
    def _apply_normal_layout(self, widgets: List[QWidget]) -> None:
        """Apply normal layout for medium width panels"""
        for widget in widgets:
            if hasattr(widget, 'set_compact_mode'):
                widget.set_compact_mode(False)
    
    def _apply_wide_layout(self, widgets: List[QWidget]) -> None:
        """Apply wide layout for large panels"""
        for widget in widgets:
            if hasattr(widget, 'set_compact_mode'):
                widget.set_compact_mode(False)
            if hasattr(widget, 'set_wide_mode'):
                widget.set_wide_mode(True)

class PropertyLayoutManager:
    """Manages property widget layout and positioning"""
    
    def __init__(self):
        self._layout_cache: Dict[str, Any] = {}
    
    def calculate_optimal_layout(self, widgets: List[QWidget], 
                               available_width: int, available_height: int) -> Dict[str, Any]:
        """Calculate optimal layout for given constraints"""
        cache_key = f"{len(widgets)}_{available_width}_{available_height}"
        
        if cache_key in self._layout_cache:
            return self._layout_cache[cache_key]
        
        layout_info = {
            "widget_width": available_width - 20,  # Account for margins
            "spacing": 2 if available_width > 200 else 1,
            "margins": (4, 4, 4, 4) if available_width > 200 else (2, 2, 2, 2),
            "compact_mode": available_width < 200
        }
        
        self._layout_cache[cache_key] = layout_info
        return layout_info
```

### Day 2 Files

**File**: `src/torematrix/ui/components/property_panel/display.py`
```python
"""Property display widgets with type-specific formatting"""

from typing import Any, Optional
from PyQt6.QtWidgets import (QWidget, QLabel, QHBoxLayout, QVBoxLayout, 
                            QPushButton, QProgressBar, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPainter, QColor
from datetime import datetime

class PropertyDisplayWidget(QWidget):
    """Individual property display with type-specific formatting"""
    
    property_clicked = pyqtSignal(str)  # property_name
    edit_requested = pyqtSignal(str)    # property_name
    
    def __init__(self, property_name: str, value: Any, property_type: str = "string", parent=None):
        super().__init__(parent)
        self.property_name = property_name
        self.value = value
        self.property_type = property_type
        self._compact_mode = False
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Setup property display UI"""
        self.setLayout(QHBoxLayout())
        self.layout().setContentsMargins(2, 1, 2, 1)
        self.layout().setSpacing(4)
        
        # Property name label
        self._name_label = QLabel(self._format_property_name())
        self._name_label.setFont(QFont("", 8))
        self._name_label.setStyleSheet("color: #555; font-weight: bold;")
        self._name_label.setFixedWidth(80)
        self.layout().addWidget(self._name_label)
        
        # Property value display
        self._value_widget = self._create_value_display()
        self.layout().addWidget(self._value_widget, 1)
        
        # Edit button
        self._edit_button = QPushButton("✎")
        self._edit_button.setFixedSize(18, 18)
        self._edit_button.setFlat(True)
        self._edit_button.clicked.connect(lambda: self.edit_requested.emit(self.property_name))
        self.layout().addWidget(self._edit_button)
        
        # Make clickable
        self.setCursor(Qt.CursorShape.PointingHandCursor)
    
    def _format_property_name(self) -> str:
        """Format property name for display"""
        return self.property_name.replace("_", " ").title()
    
    def _create_value_display(self) -> QWidget:
        """Create value display widget based on type"""
        if self.property_type == "confidence":
            return ConfidenceScoreWidget(float(self.value) if self.value else 0.0)
        elif self.property_type == "coordinate":
            return self._create_coordinate_display()
        elif self.property_type == "choice":
            return self._create_choice_display()
        else:
            return self._create_text_display()
    
    def _create_text_display(self) -> QLabel:
        """Create text value display"""
        text = str(self.value) if self.value is not None else ""
        if len(text) > 30 and not self._compact_mode:
            text = text[:27] + "..."
        
        label = QLabel(text)
        label.setFont(QFont("", 8))
        label.setWordWrap(False)
        return label
    
    def _create_coordinate_display(self) -> QLabel:
        """Create coordinate value display"""
        if isinstance(self.value, (int, float)):
            text = f"{self.value:.1f}"
        else:
            text = str(self.value)
        
        label = QLabel(text)
        label.setFont(QFont("monospace", 8))
        return label
    
    def _create_choice_display(self) -> QLabel:
        """Create choice value display"""
        label = QLabel(str(self.value))
        label.setFont(QFont("", 8))
        label.setStyleSheet("color: #333; background: #f0f0f0; padding: 1px 4px; border-radius: 2px;")
        return label
    
    def set_compact_mode(self, compact: bool) -> None:
        """Set compact display mode"""
        self._compact_mode = compact
        if compact:
            self._name_label.setFixedWidth(60)
            self.layout().setSpacing(2)
        else:
            self._name_label.setFixedWidth(80)
            self.layout().setSpacing(4)
    
    def update_value(self, new_value: Any) -> None:
        """Update the displayed value"""
        self.value = new_value
        # Recreate value widget
        old_widget = self._value_widget
        self.layout().removeWidget(old_widget)
        old_widget.deleteLater()
        
        self._value_widget = self._create_value_display()
        self.layout().insertWidget(1, self._value_widget, 1)
    
    def mousePressEvent(self, event):
        """Handle mouse press for selection"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.property_clicked.emit(self.property_name)
        super().mousePressEvent(event)

class ConfidenceScoreWidget(QWidget):
    """Visual confidence score display with progress bar"""
    
    def __init__(self, confidence: float, parent=None):
        super().__init__(parent)
        self.confidence = max(0.0, min(1.0, confidence))
        self.setFixedHeight(18)
        self.setMinimumWidth(60)
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Setup confidence display UI"""
        self.setLayout(QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        
        # Progress bar
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(int(self.confidence * 100))
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(12)
        self._progress.setStyleSheet(self._get_progress_style())
        self.layout().addWidget(self._progress)
        
        # Percentage label
        self._label = QLabel(f"{self.confidence:.1%}")
        self._label.setFont(QFont("", 7))
        self._label.setFixedWidth(30)
        self.layout().addWidget(self._label)
    
    def _get_progress_style(self) -> str:
        """Get progress bar style based on confidence level"""
        if self.confidence >= 0.8:
            color = "#4caf50"  # Green
        elif self.confidence >= 0.6:
            color = "#ff9800"  # Orange
        else:
            color = "#f44336"  # Red
        
        return f"""
        QProgressBar {{
            border: 1px solid #ddd;
            border-radius: 2px;
            background-color: #f5f5f5;
        }}
        QProgressBar::chunk {{
            background-color: {color};
            border-radius: 1px;
        }}
        """

class MetadataDisplayWidget(QWidget):
    """Rich metadata display with formatted information"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._metadata: Dict[str, Any] = {}
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Setup metadata display UI"""
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(4, 4, 4, 4)
        self.layout().setSpacing(2)
    
    def set_metadata(self, metadata: Dict[str, Any]) -> None:
        """Set metadata to display"""
        self._metadata = metadata
        self._refresh_display()
    
    def _refresh_display(self) -> None:
        """Refresh metadata display"""
        # Clear existing widgets
        for i in reversed(range(self.layout().count())):
            child = self.layout().itemAt(i).widget()
            if child:
                child.deleteLater()
        
        # Add metadata entries
        for key, value in self._metadata.items():
            if value is not None:
                widget = self._create_metadata_entry(key, value)
                self.layout().addWidget(widget)
    
    def _create_metadata_entry(self, key: str, value: Any) -> QWidget:
        """Create metadata entry widget"""
        frame = QFrame()
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(0, 1, 0, 1)
        
        # Key label
        key_label = QLabel(f"{key.replace('_', ' ').title()}:")
        key_label.setFont(QFont("", 7))
        key_label.setStyleSheet("color: #666;")
        key_label.setFixedWidth(70)
        layout.addWidget(key_label)
        
        # Value label
        value_label = QLabel(str(value))
        value_label.setFont(QFont("", 7))
        layout.addWidget(value_label)
        layout.addStretch()
        
        return frame
```

**File**: `tests/unit/components/property_panel/test_panel.py`
```python
"""Tests for property panel widget"""

import pytest
from unittest.mock import Mock, patch
from PyQt6.QtWidgets import QApplication
from src.torematrix.ui.components.property_panel.panel import PropertyPanel
from src.torematrix.ui.components.property_panel.events import PropertyNotificationCenter

@pytest.fixture
def app():
    """Create QApplication for testing"""
    return QApplication.instance() or QApplication([])

@pytest.fixture  
def panel(app):
    """Create PropertyPanel for testing"""
    return PropertyPanel()

class TestPropertyPanel:
    def test_initialization(self, panel):
        """Test panel initializes correctly"""
        assert panel._current_element is None
        assert len(panel._property_widgets) == 0
    
    def test_notification_center_connection(self, panel):
        """Test notification center connection"""
        center = PropertyNotificationCenter()
        panel.set_notification_center(center)
        assert panel._notification_center == center
    
    def test_element_setting(self, panel):
        """Test setting current element"""
        element = Mock()
        element.id = "test_element"
        element.text = "Test text"
        element.x = 10.0
        
        panel.set_element(element)
        assert panel._current_element == element
```

## 🎯 Success Criteria
- [ ] Property panel displays element metadata in organized layout
- [ ] Layout adapts to panel width changes smoothly
- [ ] Property selection works with visual feedback
- [ ] Confidence scores display with color-coded indicators
- [ ] All display components render correctly
- [ ] Memory usage optimized for display operations

## 🤝 Integration Points
**Depends on Agent 1**: Property data models and event system
**Provides to other agents**: Main panel widget and display components

## 📊 Performance Targets
- Property display updates <25ms
- Layout reflow <16ms for responsive design
- Supports 500+ properties without performance degradation

## 🚀 Getting Started

1. **Wait for Agent 1**: Ensure property framework is complete
2. **Create your feature branch**: `git checkout -b feature/property-display-agent2-issue191`
3. **Day 1**: Build main panel and layout system
4. **Day 2**: Create display components and visual feedback
5. **Test thoroughly**: Focus on UI responsiveness and display accuracy

Your display system provides the visual foundation for the property panel!