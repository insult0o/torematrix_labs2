"""Layout utilities for responsive design patterns in ToreMatrix V3.

This module provides utility functions and classes for creating
responsive, adaptive layouts with common design patterns.
"""

from typing import Dict, List, Optional, Union, Tuple, Any
from enum import Enum
import logging

from PyQt6.QtWidgets import (
    QWidget, QLayout, QVBoxLayout, QHBoxLayout, QGridLayout,
    QSplitter, QScrollArea, QFrame, QSizePolicy, QSpacerItem
)
from PyQt6.QtCore import Qt, QSize, QMargins
from PyQt6.QtGui import QResizeEvent

logger = logging.getLogger(__name__)


class FlexDirection(Enum):
    """Flex layout direction options."""
    ROW = "row"
    COLUMN = "column"
    ROW_REVERSE = "row-reverse"
    COLUMN_REVERSE = "column-reverse"


class FlexWrap(Enum):
    """Flex wrap options."""
    NO_WRAP = "nowrap"
    WRAP = "wrap"
    WRAP_REVERSE = "wrap-reverse"


class JustifyContent(Enum):
    """Justify content options."""
    FLEX_START = "flex-start"
    FLEX_END = "flex-end"
    CENTER = "center"
    SPACE_BETWEEN = "space-between"
    SPACE_AROUND = "space-around"
    SPACE_EVENLY = "space-evenly"


class AlignItems(Enum):
    """Align items options."""
    FLEX_START = "flex-start"
    FLEX_END = "flex-end"
    CENTER = "center"
    STRETCH = "stretch"
    BASELINE = "baseline"


class LayoutUtilities:
    """Collection of layout utility functions and patterns."""
    
    @staticmethod
    def create_flex_layout(
        direction: FlexDirection = FlexDirection.ROW,
        justify_content: JustifyContent = JustifyContent.FLEX_START,
        align_items: AlignItems = AlignItems.STRETCH,
        spacing: int = 6
    ) -> QLayout:
        """Create a CSS Flexbox-like layout using Qt layouts."""
        if direction in [FlexDirection.ROW, FlexDirection.ROW_REVERSE]:
            layout = QHBoxLayout()
        else:
            layout = QVBoxLayout()
        
        layout.setSpacing(spacing)
        
        # Apply justification (main axis alignment)
        if justify_content == JustifyContent.CENTER:
            layout.addStretch()
        elif justify_content == JustifyContent.FLEX_END:
            layout.addStretch()
        
        return layout
    
    @staticmethod
    def add_flex_item(
        layout: QLayout,
        widget: QWidget,
        flex_grow: int = 0,
        flex_shrink: int = 1,
        flex_basis: Optional[int] = None,
        align_self: Optional[AlignItems] = None
    ) -> None:
        """Add widget to flex layout with flex properties."""
        # Set size policy based on flex properties
        if flex_grow > 0:
            if isinstance(layout, QHBoxLayout):
                widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            else:
                widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        
        # Set minimum size if flex_basis is specified
        if flex_basis is not None:
            if isinstance(layout, QHBoxLayout):
                widget.setMinimumWidth(flex_basis)
            else:
                widget.setMinimumHeight(flex_basis)
        
        layout.addWidget(widget, flex_grow)
    
    @staticmethod
    def create_responsive_grid(
        columns: Dict[str, int],
        spacing: int = 6,
        margin: int = 0
    ) -> QGridLayout:
        """Create responsive grid layout with column configurations.
        
        Args:
            columns: Dict mapping screen sizes to column counts
            spacing: Grid spacing
            margin: Grid margin
        """
        layout = QGridLayout()
        layout.setSpacing(spacing)
        layout.setContentsMargins(margin, margin, margin, margin)
        
        # Store responsive configuration
        layout._responsive_columns = columns
        
        return layout
    
    @staticmethod
    def create_card_layout(
        title: Optional[str] = None,
        padding: int = 16,
        elevation: bool = True
    ) -> Tuple[QFrame, QVBoxLayout]:
        """Create a material design card layout."""
        card = QFrame()
        card.setFrameStyle(QFrame.Shape.Box)
        
        if elevation:
            card.setStyleSheet("""
                QFrame {
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                    background-color: white;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
            """)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(padding, padding, padding, padding)
        layout.setSpacing(12)
        
        if title:
            from PyQt6.QtWidgets import QLabel
            title_label = QLabel(title)
            title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
            layout.addWidget(title_label)
        
        return card, layout
    
    @staticmethod
    def create_sidebar_layout(
        sidebar_width: int = 250,
        collapsible: bool = True,
        position: str = "left"
    ) -> Tuple[QSplitter, QWidget, QWidget]:
        """Create a sidebar layout with main content area."""
        splitter = QSplitter()
        
        if position == "left":
            splitter.setOrientation(Qt.Orientation.Horizontal)
        else:
            splitter.setOrientation(Qt.Orientation.Horizontal)
        
        # Create sidebar
        sidebar = QWidget()
        sidebar.setMinimumWidth(sidebar_width)
        sidebar.setMaximumWidth(sidebar_width * 2)
        
        # Create main content area
        main_content = QWidget()
        
        # Add to splitter
        if position == "left":
            splitter.addWidget(sidebar)
            splitter.addWidget(main_content)
        else:
            splitter.addWidget(main_content)
            splitter.addWidget(sidebar)
        
        # Set initial sizes
        splitter.setSizes([sidebar_width, 800])
        
        if collapsible:
            splitter.setCollapsible(0, True)
        
        return splitter, sidebar, main_content
    
    @staticmethod
    def create_toolbar_layout(
        orientation: Qt.Orientation = Qt.Orientation.Horizontal,
        icon_size: QSize = QSize(24, 24),
        spacing: int = 4
    ) -> QLayout:
        """Create toolbar layout with proper spacing and sizing."""
        if orientation == Qt.Orientation.Horizontal:
            layout = QHBoxLayout()
        else:
            layout = QVBoxLayout()
        
        layout.setSpacing(spacing)
        layout.setContentsMargins(8, 4, 8, 4)
        
        # Store toolbar properties
        layout._icon_size = icon_size
        layout._orientation = orientation
        
        return layout
    
    @staticmethod
    def create_form_layout(
        fields: List[Tuple[str, QWidget]],
        label_width: Optional[int] = None,
        spacing: int = 8
    ) -> QVBoxLayout:
        """Create a form layout with labeled fields."""
        from PyQt6.QtWidgets import QLabel, QFormLayout
        
        main_layout = QVBoxLayout()
        main_layout.setSpacing(spacing)
        
        form_layout = QFormLayout()
        form_layout.setSpacing(spacing)
        
        for label_text, field_widget in fields:
            label = QLabel(label_text)
            if label_width:
                label.setMinimumWidth(label_width)
            
            form_layout.addRow(label, field_widget)
        
        main_layout.addLayout(form_layout)
        return main_layout
    
    @staticmethod
    def create_tab_like_layout(
        tabs: List[Tuple[str, QWidget]],
        tab_position: str = "top"
    ) -> Tuple[QWidget, QVBoxLayout]:
        """Create tab-like layout without using QTabWidget for more control."""
        from PyQt6.QtWidgets import QPushButton, QStackedWidget, QButtonGroup
        
        container = QWidget()
        main_layout = QVBoxLayout(container)
        
        # Create tab buttons
        tab_button_layout = QHBoxLayout()
        tab_buttons = QButtonGroup()
        stacked_widget = QStackedWidget()
        
        for i, (tab_name, tab_widget) in enumerate(tabs):
            button = QPushButton(tab_name)
            button.setCheckable(True)
            button.setChecked(i == 0)  # First tab selected by default
            
            tab_buttons.addButton(button, i)
            tab_button_layout.addWidget(button)
            stacked_widget.addWidget(tab_widget)
        
        # Connect tab switching
        def switch_tab(button_id):
            stacked_widget.setCurrentIndex(button_id)
        
        tab_buttons.idClicked.connect(switch_tab)
        
        # Add to main layout
        if tab_position == "top":
            main_layout.addLayout(tab_button_layout)
            main_layout.addWidget(stacked_widget)
        else:  # bottom
            main_layout.addWidget(stacked_widget)
            main_layout.addLayout(tab_button_layout)
        
        return container, main_layout
    
    @staticmethod
    def create_center_layout(
        content_widget: QWidget,
        max_width: Optional[int] = None,
        max_height: Optional[int] = None
    ) -> QVBoxLayout:
        """Create layout that centers content with optional max dimensions."""
        main_layout = QVBoxLayout()
        horizontal_layout = QHBoxLayout()
        
        # Add horizontal centering
        horizontal_layout.addStretch()
        
        if max_width:
            content_widget.setMaximumWidth(max_width)
        if max_height:
            content_widget.setMaximumHeight(max_height)
        
        horizontal_layout.addWidget(content_widget)
        horizontal_layout.addStretch()
        
        # Add vertical centering
        main_layout.addStretch()
        main_layout.addLayout(horizontal_layout)
        main_layout.addStretch()
        
        return main_layout
    
    @staticmethod
    def create_masonry_layout(
        columns: int = 3,
        spacing: int = 8
    ) -> 'MasonryLayout':
        """Create masonry/Pinterest-style layout."""
        return MasonryLayout(columns, spacing)
    
    @staticmethod
    def add_separator(
        layout: QLayout,
        orientation: Qt.Orientation = Qt.Orientation.Horizontal,
        margin: int = 4
    ) -> None:
        """Add visual separator to layout."""
        separator = QFrame()
        
        if orientation == Qt.Orientation.Horizontal:
            separator.setFrameShape(QFrame.Shape.HLine)
            separator.setMaximumHeight(1)
        else:
            separator.setFrameShape(QFrame.Shape.VLine)
            separator.setMaximumWidth(1)
        
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setContentsMargins(margin, margin, margin, margin)
        
        layout.addWidget(separator)
    
    @staticmethod
    def create_responsive_image_grid(
        images: List[str],
        min_item_width: int = 200,
        aspect_ratio: float = 1.0,
        spacing: int = 8
    ) -> QScrollArea:
        """Create responsive image grid that adapts to container width."""
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        
        grid_layout = ResponsiveImageGrid(
            min_item_width=min_item_width,
            aspect_ratio=aspect_ratio,
            spacing=spacing
        )
        
        scroll_widget.setLayout(grid_layout)
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        
        return scroll_area
    
    @staticmethod
    def apply_spacing_scale(layout: QLayout, scale_factor: float) -> None:
        """Apply spacing scale to layout (useful for DPI scaling)."""
        if hasattr(layout, 'spacing'):
            current_spacing = layout.spacing()
            new_spacing = int(current_spacing * scale_factor)
            layout.setSpacing(new_spacing)
        
        if hasattr(layout, 'contentsMargins'):
            margins = layout.contentsMargins()
            new_margins = QMargins(
                int(margins.left() * scale_factor),
                int(margins.top() * scale_factor),
                int(margins.right() * scale_factor),
                int(margins.bottom() * scale_factor)
            )
            layout.setContentsMargins(new_margins)


class MasonryLayout(QLayout):
    """Pinterest-style masonry layout implementation."""
    
    def __init__(self, columns: int = 3, spacing: int = 8, parent: QWidget = None):
        super().__init__(parent)
        self._columns = columns
        self._spacing = spacing
        self._items: List[QLayoutItem] = []
        self._column_heights: List[int] = [0] * columns
    
    def addItem(self, item: QLayoutItem) -> None:
        """Add item to the layout."""
        self._items.append(item)
    
    def count(self) -> int:
        """Return number of items in layout."""
        return len(self._items)
    
    def itemAt(self, index: int) -> Optional[QLayoutItem]:
        """Get item at index."""
        if 0 <= index < len(self._items):
            return self._items[index]
        return None
    
    def takeAt(self, index: int) -> Optional[QLayoutItem]:
        """Remove and return item at index."""
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None
    
    def setGeometry(self, rect) -> None:
        """Set layout geometry and position items."""
        super().setGeometry(rect)
        self._arrange_items(rect)
    
    def sizeHint(self) -> QSize:
        """Return preferred size."""
        return QSize(400, 300)  # Default size
    
    def minimumSize(self) -> QSize:
        """Return minimum size."""
        return QSize(200, 100)
    
    def _arrange_items(self, rect) -> None:
        """Arrange items in masonry pattern."""
        if not self._items:
            return
        
        # Calculate column width
        available_width = rect.width() - (self._columns - 1) * self._spacing
        column_width = available_width // self._columns
        
        # Reset column heights
        self._column_heights = [0] * self._columns
        
        # Position each item
        for item in self._items:
            # Find shortest column
            shortest_column = min(range(self._columns), key=lambda i: self._column_heights[i])
            
            # Calculate position
            x = shortest_column * (column_width + self._spacing) + rect.x()
            y = self._column_heights[shortest_column] + rect.y()
            
            # Get item size
            widget = item.widget()
            if widget:
                # Maintain aspect ratio while fitting width
                widget_hint = widget.sizeHint()
                scaled_height = int(widget_hint.height() * column_width / widget_hint.width())
                
                # Set item geometry
                item.setGeometry(QRect(x, y, column_width, scaled_height))
                
                # Update column height
                self._column_heights[shortest_column] += scaled_height + self._spacing


class ResponsiveImageGrid(QGridLayout):
    """Grid layout that automatically adjusts columns based on available width."""
    
    def __init__(
        self,
        min_item_width: int = 200,
        aspect_ratio: float = 1.0,
        spacing: int = 8,
        parent: QWidget = None
    ):
        super().__init__(parent)
        self._min_item_width = min_item_width
        self._aspect_ratio = aspect_ratio
        self._current_columns = 1
        self.setSpacing(spacing)
    
    def addWidget(self, widget: QWidget, *args, **kwargs) -> None:
        """Add widget and arrange grid."""
        super().addWidget(widget, *args, **kwargs)
        self._rearrange_grid()
    
    def _rearrange_grid(self) -> None:
        """Rearrange grid based on current width."""
        if not self.parent():
            return
        
        parent_width = self.parent().width()
        if parent_width <= 0:
            return
        
        # Calculate optimal column count
        new_columns = max(1, parent_width // (self._min_item_width + self.spacing()))
        
        if new_columns != self._current_columns:
            self._current_columns = new_columns
            self._reorganize_items()
    
    def _reorganize_items(self) -> None:
        """Reorganize items into new column configuration."""
        # Get all widgets
        widgets = []
        for i in range(self.count()):
            item = self.itemAt(i)
            if item and item.widget():
                widgets.append(item.widget())
        
        # Clear layout
        while self.count():
            child = self.takeAt(0)
            if child.widget():
                child.widget().setParent(None)
        
        # Re-add widgets in new grid arrangement
        for i, widget in enumerate(widgets):
            row = i // self._current_columns
            col = i % self._current_columns
            self.addWidget(widget, row, col)
    
    def resizeEvent(self, event: QResizeEvent) -> None:
        """Handle resize event."""
        super().resizeEvent(event)
        self._rearrange_grid()