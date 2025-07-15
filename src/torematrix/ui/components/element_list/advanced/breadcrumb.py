"""
Breadcrumb Navigation System

Provides hierarchical breadcrumb navigation for the element tree with
clickable path segments, hover effects, and keyboard navigation support.
"""

import logging
from typing import List, Optional, Dict, Any, Callable
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QLabel, 
    QScrollArea, QFrame, QSizePolicy, QToolTip
)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer, QSize, QPoint
from PyQt6.QtGui import QFont, QPalette, QIcon, QPixmap, QPainter
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class BreadcrumbItem:
    """Single breadcrumb item in the navigation path"""
    element_id: str
    display_name: str
    element_type: str
    level: int
    icon: Optional[str] = None
    tooltip_text: Optional[str] = None
    is_current: bool = False


@dataclass
class BreadcrumbStyle:
    """Styling configuration for breadcrumb components"""
    separator_text: str = "›"
    separator_color: str = "#666666"
    item_color: str = "#0066CC"
    item_hover_color: str = "#0052A3"
    current_item_color: str = "#333333"
    background_color: str = "#F8F9FA"
    border_color: str = "#E0E0E0"
    font_size: int = 12
    item_padding: int = 8
    separator_padding: int = 4


class BreadcrumbButton(QPushButton):
    """Custom button for breadcrumb items with enhanced styling"""
    
    def __init__(self, item: BreadcrumbItem, style: BreadcrumbStyle, parent=None):
        super().__init__(parent)
        self.item = item
        self.style_config = style
        self._setup_button()
    
    def _setup_button(self):
        """Setup button appearance and behavior"""
        self.setText(self.item.display_name)
        self.setFlat(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Setup styling
        if self.item.is_current:
            color = self.style_config.current_item_color
            self.setEnabled(False)
        else:
            color = self.style_config.item_color
        
        self.setStyleSheet(f"""
            QPushButton {{
                color: {color};
                background: transparent;
                border: none;
                padding: {self.style_config.item_padding}px;
                font-size: {self.style_config.font_size}px;
                text-decoration: none;
                font-weight: {"bold" if self.item.is_current else "normal"};
            }}
            QPushButton:hover:enabled {{
                color: {self.style_config.item_hover_color};
                text-decoration: underline;
            }}
            QPushButton:pressed:enabled {{
                color: {self.style_config.item_hover_color};
            }}
        """)
        
        # Setup tooltip
        if self.item.tooltip_text:
            self.setToolTip(self.item.tooltip_text)
        else:
            tooltip = f"Navigate to {self.item.display_name} ({self.item.element_type})"
            self.setToolTip(tooltip)
    
    def get_element_id(self) -> str:
        """Get the element ID for this breadcrumb item"""
        return self.item.element_id


class BreadcrumbNavigator(QWidget):
    """
    Breadcrumb navigation system for hierarchical element tree
    
    Provides clickable navigation path showing current location in hierarchy
    with support for truncation, scrolling, and customizable styling.
    """
    
    # Signals
    breadcrumb_clicked = pyqtSignal(str)  # element_id
    path_changed = pyqtSignal(list)  # List[BreadcrumbItem]
    navigation_requested = pyqtSignal(str, str)  # element_id, navigation_type
    
    def __init__(self, parent: Optional[QWidget] = None):
        """
        Initialize breadcrumb navigator
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        # Configuration
        self.style_config = BreadcrumbStyle()
        self.max_items = 10  # Maximum items before truncation
        self.enable_scrolling = True
        self.enable_keyboard_nav = True
        
        # State
        self._current_path: List[BreadcrumbItem] = []
        self._buttons: List[BreadcrumbButton] = []
        self._separators: List[QLabel] = []
        self._element_cache: Dict[str, Dict[str, Any]] = {}
        
        # Setup UI
        self._setup_layout()
        self._setup_styling()
        self._setup_keyboard_shortcuts()
        
        # Update timer for batching path changes
        self._update_timer = QTimer()
        self._update_timer.setSingleShot(True)
        self._update_timer.timeout.connect(self._update_display)
        
        logger.info("BreadcrumbNavigator initialized")
    
    def _setup_layout(self):
        """Setup the widget layout and components"""
        # Main layout
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Scroll area for long paths
        if self.enable_scrolling:
            self.scroll_area = QScrollArea()
            self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarNever)
            self.scroll_area.setWidgetResizable(True)
            self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
            
            # Content widget for scroll area
            self.content_widget = QWidget()
            self.content_layout = QHBoxLayout(self.content_widget)
            self.content_layout.setContentsMargins(8, 4, 8, 4)
            self.content_layout.setSpacing(0)
            
            self.scroll_area.setWidget(self.content_widget)
            self.main_layout.addWidget(self.scroll_area)
        else:
            # Direct layout without scrolling
            self.content_layout = self.main_layout
            self.content_layout.setContentsMargins(8, 4, 8, 4)
        
        # Add stretch to push items to left
        self.content_layout.addStretch()
    
    def _setup_styling(self):
        """Setup widget styling and appearance"""
        self.setStyleSheet(f"""
            BreadcrumbNavigator {{
                background-color: {self.style_config.background_color};
                border: 1px solid {self.style_config.border_color};
                border-radius: 4px;
            }}
        """)
        
        # Set size policy
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(32)
        self.setMaximumHeight(40)
    
    def _setup_keyboard_shortcuts(self):
        """Setup keyboard navigation shortcuts"""
        if not self.enable_keyboard_nav:
            return
        
        # Add keyboard navigation support
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    
    def set_element_path(self, element_ids: List[str], 
                        element_provider: Optional[Callable[[str], Dict[str, Any]]] = None):
        """
        Set the current navigation path
        
        Args:
            element_ids: List of element IDs from root to current
            element_provider: Function to get element details by ID
        """
        logger.debug(f"Setting breadcrumb path: {element_ids}")
        
        # Clear current path
        self._current_path.clear()
        
        # Build breadcrumb items
        for i, element_id in enumerate(element_ids):
            # Get element details
            if element_provider:
                element_data = element_provider(element_id)
            else:
                element_data = self._get_cached_element_data(element_id)
            
            # Create breadcrumb item
            item = BreadcrumbItem(
                element_id=element_id,
                display_name=element_data.get('name', f'Element {element_id}'),
                element_type=element_data.get('type', 'unknown'),
                level=i,
                icon=element_data.get('icon'),
                tooltip_text=self._build_tooltip_text(element_data),
                is_current=(i == len(element_ids) - 1)
            )
            
            self._current_path.append(item)
        
        # Schedule UI update
        self._update_timer.start(50)  # 50ms delay for batching
    
    def add_to_path(self, element_id: str, 
                   element_provider: Optional[Callable[[str], Dict[str, Any]]] = None):
        """
        Add an element to the current path
        
        Args:
            element_id: Element ID to add
            element_provider: Function to get element details
        """
        current_ids = [item.element_id for item in self._current_path]
        current_ids.append(element_id)
        self.set_element_path(current_ids, element_provider)
    
    def navigate_to_level(self, level: int):
        """
        Navigate to a specific level in the path
        
        Args:
            level: Target level (0-based index)
        """
        if 0 <= level < len(self._current_path):
            element_id = self._current_path[level].element_id
            self.breadcrumb_clicked.emit(element_id)
            self.navigation_requested.emit(element_id, "breadcrumb_click")
    
    def navigate_up_levels(self, levels: int = 1):
        """
        Navigate up by specified number of levels
        
        Args:
            levels: Number of levels to go up
        """
        if not self._current_path:
            return
        
        current_level = len(self._current_path) - 1
        target_level = max(0, current_level - levels)
        self.navigate_to_level(target_level)
    
    def get_current_path(self) -> List[BreadcrumbItem]:
        """
        Get the current breadcrumb path
        
        Returns:
            List of breadcrumb items in current path
        """
        return self._current_path.copy()
    
    def get_current_element_id(self) -> Optional[str]:
        """
        Get the current (last) element ID in path
        
        Returns:
            Current element ID or None if path is empty
        """
        if self._current_path:
            return self._current_path[-1].element_id
        return None
    
    def clear_path(self):
        """Clear the current navigation path"""
        self._current_path.clear()
        self._update_display()
    
    def set_style_config(self, style: BreadcrumbStyle):
        """
        Update the styling configuration
        
        Args:
            style: New styling configuration
        """
        self.style_config = style
        self._setup_styling()
        self._update_display()
    
    def _update_display(self):
        """Update the breadcrumb display with current path"""
        # Clear existing items
        self._clear_display()
        
        if not self._current_path:
            return
        
        # Handle truncation if needed
        items_to_show = self._get_items_to_show()
        
        # Create breadcrumb items
        for i, item in enumerate(items_to_show):
            # Add separator before item (except first)
            if i > 0:
                separator = self._create_separator()
                self._separators.append(separator)
                self.content_layout.insertWidget(-1, separator)  # Insert before stretch
            
            # Create and add button
            button = BreadcrumbButton(item, self.style_config, self)
            button.clicked.connect(lambda checked, btn=button: self._on_button_clicked(btn))
            
            self._buttons.append(button)
            self.content_layout.insertWidget(-1, button)  # Insert before stretch
        
        # Emit path changed signal
        self.path_changed.emit(self._current_path)
        
        logger.debug(f"Updated breadcrumb display with {len(items_to_show)} items")
    
    def _clear_display(self):
        """Clear all breadcrumb display items"""
        # Remove buttons
        for button in self._buttons:
            button.setParent(None)
            button.deleteLater()
        self._buttons.clear()
        
        # Remove separators
        for separator in self._separators:
            separator.setParent(None)
            separator.deleteLater()
        self._separators.clear()
    
    def _get_items_to_show(self) -> List[BreadcrumbItem]:
        """
        Get items to show considering truncation limits
        
        Returns:
            List of items to display
        """
        if len(self._current_path) <= self.max_items:
            return self._current_path
        
        # Truncate middle items, keep first, last, and some middle items
        first_items = self._current_path[:2]  # First 2 items
        last_items = self._current_path[-(self.max_items-3):]  # Last items
        
        # Add truncation indicator
        truncation_item = BreadcrumbItem(
            element_id="__truncated__",
            display_name="...",
            element_type="truncation",
            level=-1,
            tooltip_text=f"Path truncated - {len(self._current_path) - self.max_items + 1} items hidden"
        )
        
        return first_items + [truncation_item] + last_items
    
    def _create_separator(self) -> QLabel:
        """
        Create a separator label
        
        Returns:
            Configured separator label
        """
        separator = QLabel(self.style_config.separator_text)
        separator.setStyleSheet(f"""
            QLabel {{
                color: {self.style_config.separator_color};
                font-size: {self.style_config.font_size}px;
                padding: 0 {self.style_config.separator_padding}px;
                font-weight: normal;
            }}
        """)
        separator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return separator
    
    def _on_button_clicked(self, button: BreadcrumbButton):
        """
        Handle breadcrumb button click
        
        Args:
            button: Clicked breadcrumb button
        """
        element_id = button.get_element_id()
        
        # Ignore truncation indicator clicks
        if element_id == "__truncated__":
            return
        
        logger.debug(f"Breadcrumb clicked: {element_id}")
        
        # Emit signals
        self.breadcrumb_clicked.emit(element_id)
        self.navigation_requested.emit(element_id, "breadcrumb_click")
    
    def _get_cached_element_data(self, element_id: str) -> Dict[str, Any]:
        """
        Get cached element data or return default
        
        Args:
            element_id: Element ID to get data for
            
        Returns:
            Element data dictionary
        """
        if element_id in self._element_cache:
            return self._element_cache[element_id]
        
        # Return default data
        default_data = {
            'name': f'Element {element_id[:8]}',
            'type': 'unknown',
            'icon': None,
            'description': f'Element with ID {element_id}'
        }
        
        # Cache for future use
        self._element_cache[element_id] = default_data
        return default_data
    
    def _build_tooltip_text(self, element_data: Dict[str, Any]) -> str:
        """
        Build tooltip text for breadcrumb item
        
        Args:
            element_data: Element data dictionary
            
        Returns:
            Formatted tooltip text
        """
        name = element_data.get('name', 'Unknown')
        element_type = element_data.get('type', 'unknown')
        description = element_data.get('description', '')
        
        tooltip_parts = [f"Element: {name}", f"Type: {element_type}"]
        
        if description:
            tooltip_parts.append(f"Description: {description}")
        
        return "\\n".join(tooltip_parts)
    
    def keyPressEvent(self, event):
        """Handle keyboard navigation events"""
        if not self.enable_keyboard_nav:
            super().keyPressEvent(event)
            return
        
        key = event.key()
        modifiers = event.modifiers()
        
        if key == Qt.Key.Key_Up or (modifiers & Qt.KeyboardModifier.AltModifier and key == Qt.Key.Key_Left):
            # Navigate up one level
            self.navigate_up_levels(1)
            event.accept()
        elif key == Qt.Key.Key_Home or (modifiers & Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_Home):
            # Navigate to root
            self.navigate_to_level(0)
            event.accept()
        else:
            super().keyPressEvent(event)