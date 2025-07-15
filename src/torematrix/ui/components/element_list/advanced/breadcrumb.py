"""
Breadcrumb Navigation System for Hierarchical Element List

Provides hierarchical navigation breadcrumbs that show the current element's
path and allow quick navigation to parent elements.
"""

import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QFrame, QSizePolicy, QStyle
)
from PyQt6.QtCore import pyqtSignal, Qt, QSize, QPoint, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QFontMetrics, QPalette

logger = logging.getLogger(__name__)


@dataclass
class BreadcrumbItem:
    """Represents a single breadcrumb item"""
    element_id: str
    display_name: str
    element_type: str
    depth: int
    icon_path: Optional[str] = None
    tooltip: Optional[str] = None
    is_current: bool = False


class BreadcrumbButton(QPushButton):
    """Custom button for breadcrumb items with hover effects"""
    
    def __init__(self, item: BreadcrumbItem, parent=None):
        super().__init__(parent)
        
        self.item = item
        self.setFlat(True)
        self.setText(item.display_name)
        self.setMinimumHeight(24)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        
        # Style based on whether this is the current item
        self._setup_style()
        
        # Tooltip
        if item.tooltip:
            self.setToolTip(item.tooltip)
        else:
            self.setToolTip(f"{item.element_type}: {item.display_name}")
    
    def _setup_style(self):
        """Setup button styling"""
        if self.item.is_current:
            self.setStyleSheet("""
                QPushButton {
                    font-weight: bold;
                    color: #1976D2;
                    border: none;
                    padding: 4px 8px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #E3F2FD;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    color: #666666;
                    border: none;
                    padding: 4px 8px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #F5F5F5;
                    color: #1976D2;
                }
            """)


class BreadcrumbSeparator(QLabel):
    """Separator widget between breadcrumb items"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setText("›")
        self.setStyleSheet("""
            QLabel {
                color: #BDBDBD;
                font-size: 14px;
                padding: 0 4px;
            }
        """)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)


class BreadcrumbNavigator(QWidget):
    """
    Breadcrumb navigation widget for hierarchical element list
    
    Provides visual navigation path showing current element hierarchy
    with clickable segments for quick navigation to parent elements.
    """
    
    # Signals
    breadcrumb_clicked = pyqtSignal(str)  # element_id
    path_changed = pyqtSignal(list)  # List[BreadcrumbItem]
    navigation_requested = pyqtSignal(str, str)  # element_id, navigation_type
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Configuration
        self.max_visible_items = 6
        self.auto_scroll = True
        self.animate_transitions = True
        self.show_element_types = True
        
        # State
        self._breadcrumb_path: List[BreadcrumbItem] = []
        self._widgets: List[QWidget] = []
        self._animation = None
        
        # Setup UI
        self._setup_ui()
        
        logger.info("BreadcrumbNavigator initialized")
    
    def _setup_ui(self):
        """Setup the user interface"""
        # Main layout
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(8, 4, 8, 4)
        self.main_layout.setSpacing(0)
        
        # Scroll area for breadcrumbs
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarNever)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setMaximumHeight(32)
        
        # Container widget for breadcrumbs
        self.breadcrumb_container = QWidget()
        self.breadcrumb_layout = QHBoxLayout(self.breadcrumb_container)
        self.breadcrumb_layout.setContentsMargins(0, 0, 0, 0)
        self.breadcrumb_layout.setSpacing(0)
        self.breadcrumb_layout.addStretch()  # Push items to left
        
        self.scroll_area.setWidget(self.breadcrumb_container)
        self.main_layout.addWidget(self.scroll_area)
        
        # Style the widget
        self.setStyleSheet("""
            BreadcrumbNavigator {
                background-color: #FAFAFA;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
            }
            QScrollArea {
                background-color: transparent;
                border: none;
            }
        """)
    
    def set_breadcrumb_path(self, path: List[BreadcrumbItem]) -> None:
        """
        Set the complete breadcrumb path
        
        Args:
            path: List of breadcrumb items from root to current
        """
        if path == self._breadcrumb_path:
            return
        
        self._breadcrumb_path = path.copy()
        self._rebuild_breadcrumbs()
        
        self.path_changed.emit(self._breadcrumb_path)
        
        logger.debug(f"Breadcrumb path updated: {len(path)} items")
    
    def add_breadcrumb_item(self, item: BreadcrumbItem) -> None:
        """
        Add a new breadcrumb item to the end of the path
        
        Args:
            item: Breadcrumb item to add
        """
        # Mark previous current item as non-current
        if self._breadcrumb_path:
            self._breadcrumb_path[-1].is_current = False
        
        # Add new item as current
        item.is_current = True
        self._breadcrumb_path.append(item)
        
        self._rebuild_breadcrumbs()
        self.path_changed.emit(self._breadcrumb_path)
        
        logger.debug(f"Added breadcrumb item: {item.display_name}")
    
    def navigate_to_element(self, element_id: str) -> bool:
        """
        Navigate to specific element in the breadcrumb path
        
        Args:
            element_id: ID of element to navigate to
            
        Returns:
            True if navigation was successful
        """
        # Find the element in current path
        target_index = -1
        for i, item in enumerate(self._breadcrumb_path):
            if item.element_id == element_id:
                target_index = i
                break
        
        if target_index == -1:
            return False
        
        # Truncate path to target element
        new_path = self._breadcrumb_path[:target_index + 1]
        
        # Mark target as current
        for item in new_path:
            item.is_current = False
        new_path[-1].is_current = True
        
        self.set_breadcrumb_path(new_path)
        
        # Emit navigation signal
        self.breadcrumb_clicked.emit(element_id)
        self.navigation_requested.emit(element_id, "breadcrumb_click")
        
        logger.debug(f"Navigated to element: {element_id}")
        return True
    
    def clear_breadcrumbs(self) -> None:
        """Clear all breadcrumb items"""
        self._breadcrumb_path.clear()
        self._rebuild_breadcrumbs()
        self.path_changed.emit([])
        
        logger.debug("Breadcrumbs cleared")
    
    def get_current_path(self) -> List[BreadcrumbItem]:
        """Get current breadcrumb path"""
        return self._breadcrumb_path.copy()
    
    def get_current_element_id(self) -> Optional[str]:
        """Get ID of current (last) element in path"""
        if self._breadcrumb_path:
            return self._breadcrumb_path[-1].element_id
        return None
    
    def _rebuild_breadcrumbs(self) -> None:
        """Rebuild breadcrumb widgets"""
        # Clear existing widgets
        self._clear_widgets()
        
        if not self._breadcrumb_path:
            return
        
        # Determine which items to show
        items_to_show = self._get_visible_items()
        
        # Create widgets for visible items
        for i, item in enumerate(items_to_show):
            # Add separator before item (except first)
            if i > 0:
                separator = BreadcrumbSeparator()
                self.breadcrumb_layout.insertWidget(i * 2 - 1, separator)
                self._widgets.append(separator)
            
            # Create button for item
            button = BreadcrumbButton(item)
            button.clicked.connect(lambda checked, eid=item.element_id: self.navigate_to_element(eid))
            
            self.breadcrumb_layout.insertWidget(i * 2, button)
            self._widgets.append(button)
        
        # Auto-scroll to end if enabled
        if self.auto_scroll:
            self._scroll_to_end()
        
        # Animate if enabled
        if self.animate_transitions and self._widgets:
            self._animate_appearance()
    
    def _get_visible_items(self) -> List[BreadcrumbItem]:
        """Get items that should be visible based on max_visible_items"""
        if len(self._breadcrumb_path) <= self.max_visible_items:
            return self._breadcrumb_path
        
        # Show first item, ellipsis concept, and last items
        visible_items = []
        
        # Always show root
        visible_items.append(self._breadcrumb_path[0])
        
        # Add ellipsis item if needed
        if len(self._breadcrumb_path) > self.max_visible_items:
            ellipsis_item = BreadcrumbItem(
                element_id="__ellipsis__",
                display_name="...",
                element_type="ellipsis",
                depth=-1,
                tooltip=f"Hidden {len(self._breadcrumb_path) - self.max_visible_items + 1} levels"
            )
            visible_items.append(ellipsis_item)
        
        # Add last items
        start_index = max(1, len(self._breadcrumb_path) - self.max_visible_items + 2)
        visible_items.extend(self._breadcrumb_path[start_index:])
        
        return visible_items
    
    def _clear_widgets(self) -> None:
        """Clear all breadcrumb widgets"""
        for widget in self._widgets:
            widget.setParent(None)
            widget.deleteLater()
        self._widgets.clear()
    
    def _scroll_to_end(self) -> None:
        """Scroll to show the last breadcrumb item"""
        if self.auto_scroll:
            # Use a timer to ensure widgets are laid out first
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(10, lambda: self.scroll_area.horizontalScrollBar().setValue(
                self.scroll_area.horizontalScrollBar().maximum()
            ))
    
    def _animate_appearance(self) -> None:
        """Animate the appearance of new breadcrumb items"""
        if not self.animate_transitions or not self._widgets:
            return
        
        # Animate the last added widget
        last_widget = self._widgets[-1]
        if isinstance(last_widget, BreadcrumbButton):
            self._animation = QPropertyAnimation(last_widget, b"geometry")
            self._animation.setDuration(200)
            self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            
            # Start from slightly left position
            start_geometry = last_widget.geometry()
            start_geometry.moveLeft(start_geometry.left() - 20)
            
            self._animation.setStartValue(start_geometry)
            self._animation.setEndValue(last_widget.geometry())
            self._animation.start()
    
    def set_max_visible_items(self, max_items: int) -> None:
        """Set maximum number of visible breadcrumb items"""
        if max_items != self.max_visible_items:
            self.max_visible_items = max_items
            self._rebuild_breadcrumbs()
    
    def set_auto_scroll(self, enabled: bool) -> None:
        """Enable/disable auto-scrolling to newest items"""
        self.auto_scroll = enabled
    
    def set_animate_transitions(self, enabled: bool) -> None:
        """Enable/disable transition animations"""
        self.animate_transitions = enabled
    
    def set_show_element_types(self, enabled: bool) -> None:
        """Enable/disable showing element types in tooltips"""
        self.show_element_types = enabled
        # Update existing tooltips
        for widget in self._widgets:
            if isinstance(widget, BreadcrumbButton):
                item = widget.item
                if self.show_element_types and item.tooltip:
                    widget.setToolTip(item.tooltip)
                else:
                    widget.setToolTip(item.display_name)
    
    # Keyboard navigation support
    def keyPressEvent(self, event):
        """Handle keyboard navigation"""
        if event.key() == Qt.Key.Key_Left:
            # Navigate to previous element
            if len(self._breadcrumb_path) > 1:
                prev_element = self._breadcrumb_path[-2]
                self.navigate_to_element(prev_element.element_id)
                event.accept()
                return
        elif event.key() == Qt.Key.Key_Home:
            # Navigate to root element
            if self._breadcrumb_path:
                root_element = self._breadcrumb_path[0]
                self.navigate_to_element(root_element.element_id)
                event.accept()
                return
        
        super().keyPressEvent(event)
    
    def sizeHint(self) -> QSize:
        """Provide size hint for the widget"""
        return QSize(400, 32)
    
    def minimumSizeHint(self) -> QSize:
        """Provide minimum size hint"""
        return QSize(200, 32)