"""Main property panel widget with responsive layout and display components"""

from typing import Dict, Any, Optional, List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, 
    QLabel, QFrame, QSplitter, QHeaderView
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QPalette

from .models import PropertyValue, PropertyMetadata
from .events import PropertyNotificationCenter, PropertyEvent, PropertyEventType
from .display import PropertyDisplayWidget, ConfidenceScoreWidget
from .layout import ResponsivePropertyLayout
from ....core.property.manager import PropertyManager


class PropertyPanel(QWidget):
    """Main property panel widget for element property management"""
    
    # Signals
    property_changed = pyqtSignal(str, str, object)  # element_id, property_name, new_value
    property_selected = pyqtSignal(str, str)  # element_id, property_name
    validation_failed = pyqtSignal(str, str, str)  # element_id, property_name, error
    
    def __init__(self, property_manager: PropertyManager, parent=None):
        super().__init__(parent)
        self._property_manager = property_manager
        self._notification_center = property_manager.get_notification_center()
        self._current_element_id: Optional[str] = None
        self._property_widgets: Dict[str, PropertyDisplayWidget] = {}
        self._confidence_widgets: Dict[str, ConfidenceScoreWidget] = {}
        
        # Layout configuration
        self._layout_mode = "vertical"  # vertical, horizontal, grid
        self._compact_mode = False
        self._show_metadata = True
        self._group_by_category = True
        
        self._setup_ui()
        self._connect_signals()
        self._apply_styles()
    
    def _setup_ui(self) -> None:
        """Initialize the UI components"""
        # Main layout
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(8, 8, 8, 8)
        self._main_layout.setSpacing(4)
        
        # Header
        self._create_header()
        
        # Content area with scroll
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll_area.setFrameStyle(QFrame.Shape.NoFrame)
        
        # Content widget
        self._content_widget = QWidget()
        self._content_layout = ResponsivePropertyLayout(self._content_widget)
        self._content_widget.setLayout(self._content_layout)
        self._scroll_area.setWidget(self._content_widget)
        
        self._main_layout.addWidget(self._scroll_area)
        
        # Status bar
        self._create_status_bar()
    
    def _create_header(self) -> None:
        """Create property panel header"""
        header_frame = QFrame()
        header_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        header_frame.setMaximumHeight(40)
        
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(8, 4, 8, 4)
        
        # Title
        self._title_label = QLabel("Properties")
        font = QFont()
        font.setBold(True)
        font.setPointSize(10)
        self._title_label.setFont(font)
        
        # Element info
        self._element_info_label = QLabel("No element selected")
        self._element_info_label.setStyleSheet("color: #666; font-size: 9px;")
        
        header_layout.addWidget(self._title_label)
        header_layout.addStretch()
        header_layout.addWidget(self._element_info_label)
        
        self._main_layout.addWidget(header_frame)
    
    def _create_status_bar(self) -> None:
        """Create property panel status bar"""
        status_frame = QFrame()
        status_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        status_frame.setMaximumHeight(25)
        
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(8, 2, 8, 2)
        
        self._status_label = QLabel("Ready")
        self._status_label.setStyleSheet("color: #666; font-size: 8px;")
        
        self._property_count_label = QLabel("0 properties")
        self._property_count_label.setStyleSheet("color: #666; font-size: 8px;")
        
        status_layout.addWidget(self._status_label)
        status_layout.addStretch()
        status_layout.addWidget(self._property_count_label)
        
        self._main_layout.addWidget(status_frame)
    
    def _connect_signals(self) -> None:
        """Connect property notification signals"""
        self._notification_center.property_changed.connect(self._on_property_changed)
        self._notification_center.property_selected.connect(self._on_property_selected)
        self._notification_center.validation_failed.connect(self._on_validation_failed)
        self._notification_center.batch_update_started.connect(self._on_batch_update_started)
        self._notification_center.batch_update_completed.connect(self._on_batch_update_completed)
    
    def _apply_styles(self) -> None:
        """Apply custom styling to the property panel"""
        self.setStyleSheet("""
            PropertyPanel {
                background-color: #f5f5f5;
                border: 1px solid #ccc;
            }
            QScrollArea {
                background-color: white;
                border: 1px solid #ddd;
            }
            QFrame[frameShape="4"] {
                background-color: #e8e8e8;
                border: 1px solid #ccc;
            }
        """)
    
    async def set_element(self, element_id: str) -> None:
        """Set the current element and load its properties"""
        if self._current_element_id == element_id:
            return
        
        self._current_element_id = element_id
        self._update_element_info()
        
        # Clear existing widgets
        self._clear_property_widgets()
        
        if element_id:
            # Load properties for the element
            properties = await self._property_manager.get_element_properties(element_id)
            await self._display_properties(properties)
            
            self._status_label.setText("Properties loaded")
        else:
            self._status_label.setText("No element selected")
        
        self._update_property_count()
    
    async def _display_properties(self, properties: Dict[str, Any]) -> None:
        """Display properties in the panel"""
        if not properties:
            self._display_empty_state()
            return
        
        # Group properties by category if enabled
        if self._group_by_category:
            categorized_props = self._categorize_properties(properties)
            await self._display_categorized_properties(categorized_props)
        else:
            await self._display_flat_properties(properties)
    
    def _categorize_properties(self, properties: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Group properties by category"""
        categories = {}
        
        for prop_name, prop_value in properties.items():
            # Get category from metadata or use default
            category = self._get_property_category(prop_name)
            
            if category not in categories:
                categories[category] = {}
            categories[category][prop_name] = prop_value
        
        return categories
    
    def _get_property_category(self, property_name: str) -> str:
        """Get category for a property name"""
        # Category mapping - will be enhanced by other agents
        category_mapping = {
            "text": "Content",
            "content": "Content", 
            "x": "Position",
            "y": "Position",
            "width": "Dimensions",
            "height": "Dimensions",
            "confidence": "Analysis",
            "type": "Classification",
            "page": "Document"
        }
        return category_mapping.get(property_name, "General")
    
    async def _display_categorized_properties(self, categorized_props: Dict[str, Dict[str, Any]]) -> None:
        """Display properties grouped by category"""
        for category, properties in categorized_props.items():
            # Create category header
            self._create_category_header(category)
            
            # Add properties in this category
            for prop_name, prop_value in properties.items():
                await self._create_property_widget(prop_name, prop_value)
    
    async def _display_flat_properties(self, properties: Dict[str, Any]) -> None:
        """Display properties in flat list"""
        for prop_name, prop_value in properties.items():
            await self._create_property_widget(prop_name, prop_value)
    
    def _create_category_header(self, category: str) -> None:
        """Create a category header widget"""
        header_frame = QFrame()
        header_frame.setFrameStyle(QFrame.Shape.Box)
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #e0e0e0;
                border: 1px solid #bbb;
                margin: 4px 0px;
                padding: 2px;
            }
        """)
        
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(8, 4, 8, 4)
        
        category_label = QLabel(category)
        font = QFont()
        font.setBold(True)
        font.setPointSize(9)
        category_label.setFont(font)
        
        header_layout.addWidget(category_label)
        header_layout.addStretch()
        
        self._content_layout.addWidget(header_frame)
    
    async def _create_property_widget(self, property_name: str, property_value: Any) -> None:
        """Create a display widget for a property"""
        # Get property metadata if available
        metadata = await self._property_manager.get_property_metadata(
            self._current_element_id, property_name
        )
        
        # Create main property display widget
        prop_widget = PropertyDisplayWidget(
            property_name, property_value, metadata, self
        )
        
        # Connect signals
        prop_widget.value_changed.connect(
            lambda name, value: self._on_property_value_changed(name, value)
        )
        prop_widget.selected.connect(
            lambda name: self._on_property_widget_selected(name)
        )
        
        self._property_widgets[property_name] = prop_widget
        
        # Create confidence widget if property has confidence score
        if self._has_confidence_score(property_value):
            confidence_widget = ConfidenceScoreWidget(
                self._get_confidence_score(property_value), self
            )
            self._confidence_widgets[property_name] = confidence_widget
            
            # Create container for property + confidence
            container = self._create_property_container(prop_widget, confidence_widget)
            self._content_layout.addWidget(container)
        else:
            self._content_layout.addWidget(prop_widget)
    
    def _create_property_container(self, prop_widget: PropertyDisplayWidget, 
                                 conf_widget: ConfidenceScoreWidget) -> QWidget:
        """Create container for property widget and confidence widget"""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        layout.addWidget(prop_widget, 1)  # Property widget takes most space
        layout.addWidget(conf_widget, 0)  # Confidence widget fixed size
        
        return container
    
    def _has_confidence_score(self, property_value: Any) -> bool:
        """Check if property value has confidence score"""
        if isinstance(property_value, dict):
            return "confidence" in property_value
        return False
    
    def _get_confidence_score(self, property_value: Any) -> float:
        """Extract confidence score from property value"""
        if isinstance(property_value, dict):
            return property_value.get("confidence", 0.0)
        return 0.0
    
    def _display_empty_state(self) -> None:
        """Display empty state when no properties available"""
        empty_label = QLabel("No properties available")
        empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_label.setStyleSheet("color: #999; font-style: italic; padding: 20px;")
        self._content_layout.addWidget(empty_label)
    
    def _clear_property_widgets(self) -> None:
        """Clear all property widgets"""
        # Clear layout
        while self._content_layout.count():
            child = self._content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Clear widget dictionaries
        self._property_widgets.clear()
        self._confidence_widgets.clear()
    
    def _update_element_info(self) -> None:
        """Update element information in header"""
        if self._current_element_id:
            self._element_info_label.setText(f"Element: {self._current_element_id}")
        else:
            self._element_info_label.setText("No element selected")
    
    def _update_property_count(self) -> None:
        """Update property count in status bar"""
        count = len(self._property_widgets)
        self._property_count_label.setText(f"{count} properties")
    
    # Layout configuration methods
    def set_layout_mode(self, mode: str) -> None:
        """Set layout mode: vertical, horizontal, grid"""
        self._layout_mode = mode
        self._content_layout.set_layout_mode(mode)
    
    def set_compact_mode(self, compact: bool) -> None:
        """Enable/disable compact display mode"""
        self._compact_mode = compact
        for widget in self._property_widgets.values():
            widget.set_compact_mode(compact)
    
    def set_show_metadata(self, show: bool) -> None:
        """Enable/disable metadata display"""
        self._show_metadata = show
        for widget in self._property_widgets.values():
            widget.set_show_metadata(show)
    
    def set_group_by_category(self, group: bool) -> None:
        """Enable/disable property grouping by category"""
        self._group_by_category = group
        # Refresh display if element is loaded
        if self._current_element_id:
            # Async refresh would need to be handled properly
            pass
    
    # Signal handlers
    def _on_property_changed(self, event: PropertyEvent) -> None:
        """Handle property change events"""
        if (event.element_id == self._current_element_id and 
            event.property_name in self._property_widgets):
            
            widget = self._property_widgets[event.property_name]
            widget.update_value(event.new_value)
    
    def _on_property_selected(self, element_id: str, property_name: str) -> None:
        """Handle property selection events"""
        if element_id == self._current_element_id:
            self.property_selected.emit(element_id, property_name)
    
    def _on_validation_failed(self, element_id: str, property_name: str, error: str) -> None:
        """Handle validation failure events"""
        if (element_id == self._current_element_id and 
            property_name in self._property_widgets):
            
            widget = self._property_widgets[property_name]
            widget.show_validation_error(error)
            
        self.validation_failed.emit(element_id, property_name, error)
        self._status_label.setText(f"Validation error: {error}")
    
    def _on_batch_update_started(self, element_ids: List[str]) -> None:
        """Handle batch update start"""
        if self._current_element_id in element_ids:
            self._status_label.setText("Updating properties...")
    
    def _on_batch_update_completed(self, element_ids: List[str], count: int) -> None:
        """Handle batch update completion"""
        if self._current_element_id in element_ids:
            self._status_label.setText(f"Updated {count} properties")
    
    def _on_property_value_changed(self, property_name: str, new_value: Any) -> None:
        """Handle property value changes from widgets"""
        if self._current_element_id:
            self.property_changed.emit(self._current_element_id, property_name, new_value)
    
    def _on_property_widget_selected(self, property_name: str) -> None:
        """Handle property widget selection"""
        if self._current_element_id:
            self.property_selected.emit(self._current_element_id, property_name)
    
    # Public interface
    def get_current_element_id(self) -> Optional[str]:
        """Get current element ID"""
        return self._current_element_id
    
    def get_property_widget(self, property_name: str) -> Optional[PropertyDisplayWidget]:
        """Get property widget by name"""
        return self._property_widgets.get(property_name)
    
    def get_confidence_widget(self, property_name: str) -> Optional[ConfidenceScoreWidget]:
        """Get confidence widget by property name"""
        return self._confidence_widgets.get(property_name)
    
    def refresh_properties(self) -> None:
        """Refresh property display for current element"""
        if self._current_element_id:
            # This would need to be called from an async context
            pass
    
    def sizeHint(self) -> QSize:
        """Provide size hint for the widget"""
        return QSize(300, 400)