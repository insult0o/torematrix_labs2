"""Responsive layout management for property panel widgets"""

from typing import List, Dict, Any, Optional
from PyQt6.QtWidgets import (
    QLayout, QLayoutItem, QWidget, QVBoxLayout, QHBoxLayout, 
    QGridLayout, QSizePolicy, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, QSize, QRect, QPoint
from PyQt6.QtGui import QResizeEvent


class ResponsivePropertyLayout(QLayout):
    """Responsive layout that adapts to available space and content"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: List[QLayoutItem] = []
        self._layout_mode = "vertical"  # vertical, horizontal, grid, auto
        self._min_column_width = 200
        self._max_columns = 3
        self._spacing = 4
        self._margins = (4, 4, 4, 4)
        self._adaptive_sizing = True
        self._last_size = QSize(-1, -1)
        
        # Grid layout parameters
        self._grid_columns = 2
        self._grid_row_height = 60
        
        # Auto-layout thresholds
        self._width_threshold_grid = 600
        self._width_threshold_horizontal = 400
    
    def addItem(self, item: QLayoutItem) -> None:
        """Add item to layout"""
        self._items.append(item)
        self.invalidate()
    
    def addWidget(self, widget: QWidget) -> None:
        """Add widget to layout"""
        from PyQt6.QtWidgets import QWidgetItem
        self.addItem(QWidgetItem(widget))
    
    def count(self) -> int:
        """Get number of items in layout"""
        return len(self._items)
    
    def itemAt(self, index: int) -> Optional[QLayoutItem]:
        """Get item at index"""
        if 0 <= index < len(self._items):
            return self._items[index]
        return None
    
    def takeAt(self, index: int) -> Optional[QLayoutItem]:
        """Remove and return item at index"""
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None
    
    def sizeHint(self) -> QSize:
        """Calculate preferred size"""
        if not self._items:
            return QSize(0, 0)
        
        width, height = self._calculate_size_hint()
        return QSize(width, height)
    
    def minimumSize(self) -> QSize:
        """Calculate minimum size"""
        if not self._items:
            return QSize(0, 0)
        
        # Minimum size is single column layout
        width = self._min_column_width + self._margins[0] + self._margins[2]
        height = sum(item.minimumSize().height() for item in self._items)
        height += self._spacing * max(0, len(self._items) - 1)
        height += self._margins[1] + self._margins[3]
        
        return QSize(width, height)
    
    def setGeometry(self, rect: QRect) -> None:
        """Set layout geometry and arrange items"""
        super().setGeometry(rect)
        
        if not self._items:
            return
        
        # Check if we need to recalculate layout
        current_size = rect.size()
        if self._adaptive_sizing and current_size != self._last_size:
            self._last_size = current_size
            self._update_layout_mode(current_size)
        
        # Arrange items based on current layout mode
        self._arrange_items(rect)
    
    def _calculate_size_hint(self) -> tuple:
        """Calculate size hint based on layout mode"""
        if self._layout_mode == "vertical":
            return self._calculate_vertical_size()
        elif self._layout_mode == "horizontal":
            return self._calculate_horizontal_size()
        elif self._layout_mode == "grid":
            return self._calculate_grid_size()
        else:  # auto
            return self._calculate_auto_size()
    
    def _calculate_vertical_size(self) -> tuple:
        """Calculate size for vertical layout"""
        max_width = 0
        total_height = 0
        
        for item in self._items:
            item_size = item.sizeHint()
            max_width = max(max_width, item_size.width())
            total_height += item_size.height()
        
        # Add spacing and margins
        total_height += self._spacing * max(0, len(self._items) - 1)
        total_height += self._margins[1] + self._margins[3]
        max_width += self._margins[0] + self._margins[2]
        
        return max_width, total_height
    
    def _calculate_horizontal_size(self) -> tuple:
        """Calculate size for horizontal layout"""
        total_width = 0
        max_height = 0
        
        for item in self._items:
            item_size = item.sizeHint()
            total_width += item_size.width()
            max_height = max(max_height, item_size.height())
        
        # Add spacing and margins
        total_width += self._spacing * max(0, len(self._items) - 1)
        total_width += self._margins[0] + self._margins[2]
        max_height += self._margins[1] + self._margins[3]
        
        return total_width, max_height
    
    def _calculate_grid_size(self) -> tuple:
        """Calculate size for grid layout"""
        if not self._items:
            return 0, 0
        
        rows = (len(self._items) + self._grid_columns - 1) // self._grid_columns
        
        width = self._grid_columns * self._min_column_width
        width += (self._grid_columns - 1) * self._spacing
        width += self._margins[0] + self._margins[2]
        
        height = rows * self._grid_row_height
        height += (rows - 1) * self._spacing
        height += self._margins[1] + self._margins[3]
        
        return width, height
    
    def _calculate_auto_size(self) -> tuple:
        """Calculate size for auto layout mode"""
        # Use vertical layout as default for size hint
        return self._calculate_vertical_size()
    
    def _update_layout_mode(self, size: QSize) -> None:
        """Update layout mode based on available size"""
        if self._layout_mode != "auto":
            return
        
        width = size.width()
        
        if width >= self._width_threshold_grid:
            self._current_auto_mode = "grid"
            self._grid_columns = min(width // self._min_column_width, self._max_columns)
        elif width >= self._width_threshold_horizontal:
            self._current_auto_mode = "horizontal"
        else:
            self._current_auto_mode = "vertical"
    
    def _arrange_items(self, rect: QRect) -> None:
        """Arrange items in the layout"""
        if self._layout_mode == "vertical":
            self._arrange_vertical(rect)
        elif self._layout_mode == "horizontal":
            self._arrange_horizontal(rect)
        elif self._layout_mode == "grid":
            self._arrange_grid(rect)
        else:  # auto
            auto_mode = getattr(self, '_current_auto_mode', 'vertical')
            if auto_mode == "grid":
                self._arrange_grid(rect)
            elif auto_mode == "horizontal":
                self._arrange_horizontal(rect)
            else:
                self._arrange_vertical(rect)
    
    def _arrange_vertical(self, rect: QRect) -> None:
        """Arrange items vertically"""
        x = rect.x() + self._margins[0]
        y = rect.y() + self._margins[1]
        width = rect.width() - self._margins[0] - self._margins[2]
        
        for item in self._items:
            item_height = item.sizeHint().height()
            item_rect = QRect(x, y, width, item_height)
            item.setGeometry(item_rect)
            y += item_height + self._spacing
    
    def _arrange_horizontal(self, rect: QRect) -> None:
        """Arrange items horizontally"""
        if not self._items:
            return
        
        x = rect.x() + self._margins[0]
        y = rect.y() + self._margins[1]
        height = rect.height() - self._margins[1] - self._margins[3]
        
        # Calculate total preferred width
        total_preferred_width = sum(item.sizeHint().width() for item in self._items)
        total_spacing = self._spacing * max(0, len(self._items) - 1)
        available_width = rect.width() - self._margins[0] - self._margins[2] - total_spacing
        
        # Distribute width among items
        if total_preferred_width <= available_width:
            # Use preferred widths
            for item in self._items:
                item_width = item.sizeHint().width()
                item_rect = QRect(x, y, item_width, height)
                item.setGeometry(item_rect)
                x += item_width + self._spacing
        else:
            # Scale down proportionally
            scale_factor = available_width / total_preferred_width
            for item in self._items:
                preferred_width = item.sizeHint().width()
                item_width = int(preferred_width * scale_factor)
                item_rect = QRect(x, y, item_width, height)
                item.setGeometry(item_rect)
                x += item_width + self._spacing
    
    def _arrange_grid(self, rect: QRect) -> None:
        """Arrange items in grid layout"""
        if not self._items:
            return
        
        x_start = rect.x() + self._margins[0]
        y_start = rect.y() + self._margins[1]
        
        available_width = rect.width() - self._margins[0] - self._margins[2]
        column_width = (available_width - (self._grid_columns - 1) * self._spacing) // self._grid_columns
        
        row = 0
        col = 0
        
        for item in self._items:
            x = x_start + col * (column_width + self._spacing)
            y = y_start + row * (self._grid_row_height + self._spacing)
            
            item_rect = QRect(x, y, column_width, self._grid_row_height)
            item.setGeometry(item_rect)
            
            col += 1
            if col >= self._grid_columns:
                col = 0
                row += 1
    
    # Public configuration methods
    def set_layout_mode(self, mode: str) -> None:
        """Set layout mode: vertical, horizontal, grid, auto"""
        if mode in ["vertical", "horizontal", "grid", "auto"]:
            self._layout_mode = mode
            self.invalidate()
    
    def set_grid_columns(self, columns: int) -> None:
        """Set number of columns for grid layout"""
        self._grid_columns = max(1, min(columns, self._max_columns))
        if self._layout_mode in ["grid", "auto"]:
            self.invalidate()
    
    def set_spacing(self, spacing: int) -> None:
        """Set spacing between items"""
        self._spacing = max(0, spacing)
        self.invalidate()
    
    def set_margins(self, left: int, top: int, right: int, bottom: int) -> None:
        """Set layout margins"""
        self._margins = (left, top, right, bottom)
        self.invalidate()
    
    def set_min_column_width(self, width: int) -> None:
        """Set minimum column width"""
        self._min_column_width = max(100, width)
        self.invalidate()
    
    def set_adaptive_sizing(self, adaptive: bool) -> None:
        """Enable/disable adaptive sizing based on available space"""
        self._adaptive_sizing = adaptive
    
    def set_width_thresholds(self, grid_threshold: int, horizontal_threshold: int) -> None:
        """Set width thresholds for auto layout mode"""
        self._width_threshold_grid = grid_threshold
        self._width_threshold_horizontal = horizontal_threshold
    
    def get_layout_mode(self) -> str:
        """Get current layout mode"""
        return self._layout_mode
    
    def get_effective_layout_mode(self) -> str:
        """Get effective layout mode (resolves auto mode)"""
        if self._layout_mode == "auto":
            return getattr(self, '_current_auto_mode', 'vertical')
        return self._layout_mode
    
    def clear_layout(self) -> None:
        """Remove all items from layout"""
        while self._items:
            item = self._items.pop()
            if item.widget():
                item.widget().setParent(None)
    
    def get_items(self) -> List[QLayoutItem]:
        """Get all layout items"""
        return self._items.copy()


class PropertyCategoryFrame(QFrame):
    """Frame widget for grouping properties by category"""
    
    def __init__(self, category_name: str, parent=None):
        super().__init__(parent)
        self._category_name = category_name
        self._is_collapsible = True
        self._is_collapsed = False
        self._property_widgets: List[QWidget] = []
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Initialize the UI components"""
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            PropertyCategoryFrame {
                border: 1px solid #ccc;
                border-radius: 4px;
                margin: 2px;
                background-color: #f8f8f8;
            }
        """)
        
        # Main layout
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(4, 4, 4, 4)
        self._main_layout.setSpacing(2)
        
        # Header
        self._create_header()
        
        # Content area
        self._content_widget = QWidget()
        self._content_layout = ResponsivePropertyLayout(self._content_widget)
        self._content_widget.setLayout(self._content_layout)
        
        self._main_layout.addWidget(self._content_widget)
    
    def _create_header(self) -> None:
        """Create category header"""
        from PyQt6.QtWidgets import QPushButton
        from PyQt6.QtGui import QFont
        
        header_frame = QFrame()
        header_frame.setFrameStyle(QFrame.Shape.Box)
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #e0e0e0;
                border: 1px solid #bbb;
                border-radius: 3px;
            }
        """)
        
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(6, 3, 6, 3)
        
        # Category name
        self._name_label = QLabel(self._category_name)
        font = QFont()
        font.setBold(True)
        font.setPointSize(9)
        self._name_label.setFont(font)
        
        # Collapse/expand button
        self._toggle_button = QPushButton("−" if not self._is_collapsed else "+")
        self._toggle_button.setMaximumSize(20, 20)
        self._toggle_button.setStyleSheet("""
            QPushButton {
                background-color: #ccc;
                border: 1px solid #999;
                border-radius: 2px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #bbb;
            }
        """)
        self._toggle_button.clicked.connect(self._toggle_collapsed)
        
        # Property count
        self._count_label = QLabel("0")
        self._count_label.setStyleSheet("color: #666; font-size: 8px;")
        
        header_layout.addWidget(self._name_label)
        header_layout.addStretch()
        header_layout.addWidget(self._count_label)
        header_layout.addWidget(self._toggle_button)
        
        self._main_layout.addWidget(header_frame)
    
    def add_property_widget(self, widget: QWidget) -> None:
        """Add property widget to this category"""
        self._property_widgets.append(widget)
        self._content_layout.addWidget(widget)
        self._update_count()
    
    def remove_property_widget(self, widget: QWidget) -> None:
        """Remove property widget from this category"""
        if widget in self._property_widgets:
            self._property_widgets.remove(widget)
            # Remove from layout (widget will be deleted by parent)
            self._update_count()
    
    def clear_property_widgets(self) -> None:
        """Clear all property widgets"""
        self._property_widgets.clear()
        self._content_layout.clear_layout()
        self._update_count()
    
    def _toggle_collapsed(self) -> None:
        """Toggle collapsed state"""
        self._is_collapsed = not self._is_collapsed
        self._content_widget.setVisible(not self._is_collapsed)
        self._toggle_button.setText("+" if self._is_collapsed else "−")
    
    def _update_count(self) -> None:
        """Update property count display"""
        count = len(self._property_widgets)
        self._count_label.setText(str(count))
    
    def set_layout_mode(self, mode: str) -> None:
        """Set layout mode for property widgets"""
        self._content_layout.set_layout_mode(mode)
    
    def get_category_name(self) -> str:
        """Get category name"""
        return self._category_name
    
    def get_property_count(self) -> int:
        """Get number of property widgets"""
        return len(self._property_widgets)
    
    def is_collapsed(self) -> bool:
        """Check if category is collapsed"""
        return self._is_collapsed
    
    def set_collapsed(self, collapsed: bool) -> None:
        """Set collapsed state"""
        if collapsed != self._is_collapsed:
            self._toggle_collapsed()