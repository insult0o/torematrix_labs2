"""
Reading order visualization for document validation.

This module provides visualization tools for showing and editing the reading order
of document elements, with visual flow indicators and interactive controls.
"""

from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import math
import logging

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGraphicsView, QGraphicsScene,
    QGraphicsItem, QGraphicsLineItem, QGraphicsEllipseItem, QGraphicsTextItem,
    QGraphicsProxyWidget, QLabel, QSlider, QCheckBox, QComboBox, QSpinBox,
    QToolButton, QButtonGroup, QFrame, QGroupBox, QScrollArea
)
from PyQt6.QtCore import (
    Qt, QRectF, QPointF, QSizeF, QTimer, QPropertyAnimation, QEasingCurve,
    pyqtSignal, QParallelAnimationGroup, QSequentialAnimationGroup
)
from PyQt6.QtGui import (
    QPen, QBrush, QColor, QPainter, QFont, QFontMetrics, QPainterPath,
    QLinearGradient, QPolygonF, QTransform, QPalette
)

from torematrix.core.models.element import Element, ElementType
from torematrix.core.operations.hierarchy import HierarchyManager
from torematrix.core.events import EventBus
from torematrix.core.state import StateStore
from torematrix.utils.geometry import Point, Rect


logger = logging.getLogger(__name__)


class ReadingOrderMode(Enum):
    """Reading order visualization modes."""
    FLOW_ARROWS = "flow_arrows"
    NUMBERED_SEQUENCE = "numbered_sequence"
    HIGHLIGHTED_PATH = "highlighted_path"
    SPATIAL_GROUPING = "spatial_grouping"


class FlowDirection(Enum):
    """Flow direction for reading order."""
    LEFT_TO_RIGHT = "left_to_right"
    RIGHT_TO_LEFT = "right_to_left"
    TOP_TO_BOTTOM = "top_to_bottom"
    BOTTOM_TO_TOP = "bottom_to_top"


@dataclass
class ReadingOrderConfig:
    """Configuration for reading order visualization."""
    mode: ReadingOrderMode = ReadingOrderMode.FLOW_ARROWS
    flow_direction: FlowDirection = FlowDirection.LEFT_TO_RIGHT
    show_numbers: bool = True
    show_connections: bool = True
    highlight_current: bool = True
    animate_flow: bool = True
    arrow_size: float = 12.0
    number_size: float = 16.0
    connection_width: float = 2.0
    highlight_color: QColor = QColor(255, 165, 0)
    arrow_color: QColor = QColor(0, 120, 215)
    number_color: QColor = QColor(255, 255, 255)
    connection_color: QColor = QColor(128, 128, 128)


class ReadingOrderItem(QGraphicsItem):
    """Graphics item representing an element in reading order."""
    
    def __init__(self, element: Element, order_index: int, config: ReadingOrderConfig):
        super().__init__()
        self.element = element
        self.order_index = order_index
        self.config = config
        self.is_highlighted = False
        self.is_current = False
        
        # Visual properties
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        
        # Set position and size based on element bounds
        self.setPos(element.bounds.x, element.bounds.y)
        self._bounding_rect = QRectF(0, 0, element.bounds.width, element.bounds.height)
        
        # Create sub-items
        self._create_visual_elements()
    
    def _create_visual_elements(self):
        """Create visual elements for this item."""
        # Number indicator
        if self.config.show_numbers:
            self._number_item = QGraphicsEllipseItem(self)
            self._number_text = QGraphicsTextItem(self)
            self._setup_number_display()
        
        # Element highlight
        self._highlight_item = QGraphicsItem(self)
        self._setup_highlight()
    
    def _setup_number_display(self):
        """Set up the number display."""
        # Create circle for number
        radius = self.config.number_size / 2
        self._number_item.setRect(-radius, -radius, radius * 2, radius * 2)
        self._number_item.setBrush(QBrush(self.config.arrow_color))
        self._number_item.setPen(QPen(Qt.GlobalColor.white, 2))
        
        # Position at top-left corner
        self._number_item.setPos(radius, radius)
        
        # Set number text
        self._number_text.setPlainText(str(self.order_index + 1))
        self._number_text.setDefaultTextColor(self.config.number_color)
        
        # Center text in circle
        font = QFont()
        font.setPointSize(int(self.config.number_size * 0.6))
        font.setBold(True)
        self._number_text.setFont(font)
        
        # Calculate text position
        text_rect = self._number_text.boundingRect()
        text_x = radius - text_rect.width() / 2
        text_y = radius - text_rect.height() / 2
        self._number_text.setPos(text_x, text_y)
    
    def _setup_highlight(self):
        """Set up the highlight display."""
        # Highlight will be drawn in paint method
        pass
    
    def set_highlighted(self, highlighted: bool):
        """Set highlight state."""
        if self.is_highlighted != highlighted:
            self.is_highlighted = highlighted
            self.update()
    
    def set_current(self, current: bool):
        """Set current state."""
        if self.is_current != current:
            self.is_current = current
            self.update()
    
    def boundingRect(self) -> QRectF:
        """Return bounding rectangle."""
        return self._bounding_rect
    
    def paint(self, painter: QPainter, option, widget=None):
        """Paint the item."""
        # Draw element highlight
        if self.is_highlighted or self.is_current:
            color = self.config.highlight_color if self.is_highlighted else QColor(255, 255, 0)
            painter.setPen(QPen(color, 3))
            painter.setBrush(QBrush(color.lighter(180)))
            painter.drawRect(self._bounding_rect)
        
        # Draw element outline
        painter.setPen(QPen(QColor(100, 100, 100), 1))
        painter.setBrush(QBrush(QColor(255, 255, 255, 100)))
        painter.drawRect(self._bounding_rect)
        
        # Draw element type indicator
        type_text = self.element.element_type.value
        painter.setPen(QPen(Qt.GlobalColor.black))
        painter.drawText(self._bounding_rect, Qt.AlignmentFlag.AlignCenter, type_text)


class ReadingOrderFlow(QGraphicsItem):
    """Graphics item representing flow between elements."""
    
    def __init__(self, from_item: ReadingOrderItem, to_item: ReadingOrderItem, config: ReadingOrderConfig):
        super().__init__()
        self.from_item = from_item
        self.to_item = to_item
        self.config = config
        self.is_animated = False
        self.animation_progress = 0.0
        
        # Calculate connection points
        self._calculate_connection_points()
        
        # Set up animation
        if config.animate_flow:
            self._setup_animation()
    
    def _calculate_connection_points(self):
        """Calculate optimal connection points between items."""
        from_rect = self.from_item.boundingRect()
        to_rect = self.to_item.boundingRect()
        
        from_center = self.from_item.pos() + from_rect.center()
        to_center = self.to_item.pos() + to_rect.center()
        
        # Calculate connection points based on relative positions
        dx = to_center.x() - from_center.x()
        dy = to_center.y() - from_center.y()
        
        # Determine best connection sides
        if abs(dx) > abs(dy):
            # Horizontal connection
            if dx > 0:
                # Left to right
                self.start_point = QPointF(
                    from_center.x() + from_rect.width() / 2,
                    from_center.y()
                )
                self.end_point = QPointF(
                    to_center.x() - to_rect.width() / 2,
                    to_center.y()
                )
            else:
                # Right to left
                self.start_point = QPointF(
                    from_center.x() - from_rect.width() / 2,
                    from_center.y()
                )
                self.end_point = QPointF(
                    to_center.x() + to_rect.width() / 2,
                    to_center.y()
                )
        else:
            # Vertical connection
            if dy > 0:
                # Top to bottom
                self.start_point = QPointF(
                    from_center.x(),
                    from_center.y() + from_rect.height() / 2
                )
                self.end_point = QPointF(
                    to_center.x(),
                    to_center.y() - to_rect.height() / 2
                )
            else:
                # Bottom to top
                self.start_point = QPointF(
                    from_center.x(),
                    from_center.y() - from_rect.height() / 2
                )
                self.end_point = QPointF(
                    to_center.x(),
                    to_center.y() + to_rect.height() / 2
                )
    
    def _setup_animation(self):
        """Set up flow animation."""
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self._animate_flow)
        self.animation_timer.start(50)  # 20 FPS
    
    def _animate_flow(self):
        """Animate flow progress."""
        self.animation_progress += 0.05
        if self.animation_progress > 1.0:
            self.animation_progress = 0.0
        self.update()
    
    def boundingRect(self) -> QRectF:
        """Return bounding rectangle."""
        margin = self.config.arrow_size
        return QRectF(
            min(self.start_point.x(), self.end_point.x()) - margin,
            min(self.start_point.y(), self.end_point.y()) - margin,
            abs(self.end_point.x() - self.start_point.x()) + 2 * margin,
            abs(self.end_point.y() - self.start_point.y()) + 2 * margin
        )
    
    def paint(self, painter: QPainter, option, widget=None):
        """Paint the flow connection."""
        if not self.config.show_connections:
            return
        
        # Draw connection line
        painter.setPen(QPen(self.config.connection_color, self.config.connection_width))
        painter.drawLine(self.start_point, self.end_point)
        
        # Draw arrow head
        self._draw_arrow_head(painter)
        
        # Draw animation if enabled
        if self.config.animate_flow:
            self._draw_animation(painter)
    
    def _draw_arrow_head(self, painter: QPainter):
        """Draw arrow head at end point."""
        # Calculate arrow direction
        dx = self.end_point.x() - self.start_point.x()
        dy = self.end_point.y() - self.start_point.y()
        length = math.sqrt(dx * dx + dy * dy)
        
        if length == 0:
            return
        
        # Normalize direction
        dx /= length
        dy /= length
        
        # Calculate arrow points
        arrow_size = self.config.arrow_size
        arrow_angle = math.pi / 6  # 30 degrees
        
        # Arrow tip is at end_point
        tip = self.end_point
        
        # Calculate arrow base points
        base_x = tip.x() - arrow_size * dx
        base_y = tip.y() - arrow_size * dy
        
        # Calculate arrow wing points
        wing_dx = arrow_size * 0.5 * math.cos(arrow_angle)
        wing_dy = arrow_size * 0.5 * math.sin(arrow_angle)
        
        # Rotate wing vectors
        wing1_x = base_x + wing_dx * (-dy) - wing_dy * dx
        wing1_y = base_y + wing_dx * dx + wing_dy * (-dy)
        
        wing2_x = base_x + wing_dx * dy + wing_dy * dx
        wing2_y = base_y + wing_dx * (-dx) + wing_dy * dy
        
        # Draw arrow head
        arrow_points = [
            tip,
            QPointF(wing1_x, wing1_y),
            QPointF(wing2_x, wing2_y)
        ]
        
        painter.setBrush(QBrush(self.config.arrow_color))
        painter.setPen(QPen(self.config.arrow_color, 1))
        painter.drawPolygon(QPolygonF(arrow_points))
    
    def _draw_animation(self, painter: QPainter):
        """Draw flow animation."""
        if not self.is_animated:
            return
        
        # Calculate animated point along the line
        animated_x = self.start_point.x() + (self.end_point.x() - self.start_point.x()) * self.animation_progress
        animated_y = self.start_point.y() + (self.end_point.y() - self.start_point.y()) * self.animation_progress
        
        # Draw animated dot
        painter.setBrush(QBrush(self.config.highlight_color))
        painter.setPen(QPen(self.config.highlight_color, 2))
        painter.drawEllipse(QPointF(animated_x, animated_y), 4, 4)


class ReadingOrderVisualization(QGraphicsView):
    """Main visualization widget for reading order."""
    
    # Signals
    element_selected = pyqtSignal(str)
    order_changed = pyqtSignal(list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.hierarchy_manager = None
        self.state_store = None
        self.config = ReadingOrderConfig()
        
        # Graphics scene
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        
        # Visual items
        self.order_items: Dict[str, ReadingOrderItem] = {}
        self.flow_items: List[ReadingOrderFlow] = []
        
        # Current state
        self.current_elements: List[Element] = []
        self.current_order: List[str] = []
        self.selected_element_id: Optional[str] = None
        
        # Setup view
        self._setup_view()
    
    def _setup_view(self):
        """Set up the graphics view."""
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        # Set background
        self.setBackgroundBrush(QBrush(QColor(250, 250, 250)))
        
        # Enable mouse tracking
        self.setMouseTracking(True)
    
    def set_hierarchy_manager(self, manager: HierarchyManager):
        """Set the hierarchy manager."""
        self.hierarchy_manager = manager
    
    def set_state_store(self, store: StateStore):
        """Set the state store."""
        self.state_store = store
    
    def set_config(self, config: ReadingOrderConfig):
        """Set visualization configuration."""
        self.config = config
        self._refresh_visualization()
    
    def show_reading_order(self, elements: List[Element], order: List[str]):
        """Show reading order for given elements."""
        self.current_elements = elements
        self.current_order = order
        self._refresh_visualization()
    
    def _refresh_visualization(self):
        """Refresh the visualization."""
        # Clear existing items
        self.scene.clear()
        self.order_items.clear()
        self.flow_items.clear()
        
        if not self.current_elements or not self.current_order:
            return
        
        # Create element map
        element_map = {elem.id: elem for elem in self.current_elements}
        
        # Create reading order items
        for i, element_id in enumerate(self.current_order):
            if element_id in element_map:
                element = element_map[element_id]
                item = ReadingOrderItem(element, i, self.config)
                self.scene.addItem(item)
                self.order_items[element_id] = item
        
        # Create flow connections
        if self.config.show_connections:
            for i in range(len(self.current_order) - 1):
                from_id = self.current_order[i]
                to_id = self.current_order[i + 1]
                
                if from_id in self.order_items and to_id in self.order_items:
                    from_item = self.order_items[from_id]
                    to_item = self.order_items[to_id]
                    
                    flow = ReadingOrderFlow(from_item, to_item, self.config)
                    self.scene.addItem(flow)
                    self.flow_items.append(flow)
        
        # Fit in view
        self.fitInView(self.scene.itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)
    
    def highlight_element(self, element_id: str):
        """Highlight a specific element."""
        # Clear previous highlights
        for item in self.order_items.values():
            item.set_highlighted(False)
        
        # Highlight selected element
        if element_id in self.order_items:
            self.order_items[element_id].set_highlighted(True)
            self.selected_element_id = element_id
    
    def set_current_element(self, element_id: str):
        """Set current element in reading flow."""
        # Clear previous current
        for item in self.order_items.values():
            item.set_current(False)
        
        # Set current element
        if element_id in self.order_items:
            self.order_items[element_id].set_current(True)
    
    def mousePressEvent(self, event):
        """Handle mouse press events."""
        super().mousePressEvent(event)
        
        # Check if an element was clicked
        item = self.itemAt(event.position().toPoint())
        if isinstance(item, ReadingOrderItem):
            self.element_selected.emit(item.element.id)
            self.highlight_element(item.element.id)


class ReadingOrderControlPanel(QWidget):
    """Control panel for reading order visualization."""
    
    # Signals
    config_changed = pyqtSignal(ReadingOrderConfig)
    mode_changed = pyqtSignal(ReadingOrderMode)
    animation_toggled = pyqtSignal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = ReadingOrderConfig()
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the UI."""
        layout = QVBoxLayout(self)
        
        # Visualization mode group
        mode_group = QGroupBox("Visualization Mode")
        mode_layout = QVBoxLayout(mode_group)
        
        # Mode selection
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            "Flow Arrows",
            "Numbered Sequence",
            "Highlighted Path",
            "Spatial Grouping"
        ])
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        mode_layout.addWidget(self.mode_combo)
        
        layout.addWidget(mode_group)
        
        # Display options group
        display_group = QGroupBox("Display Options")
        display_layout = QVBoxLayout(display_group)
        
        # Show numbers
        self.show_numbers_cb = QCheckBox("Show Numbers")
        self.show_numbers_cb.setChecked(self.config.show_numbers)
        self.show_numbers_cb.toggled.connect(self._on_config_changed)
        display_layout.addWidget(self.show_numbers_cb)
        
        # Show connections
        self.show_connections_cb = QCheckBox("Show Connections")
        self.show_connections_cb.setChecked(self.config.show_connections)
        self.show_connections_cb.toggled.connect(self._on_config_changed)
        display_layout.addWidget(self.show_connections_cb)
        
        # Animate flow
        self.animate_flow_cb = QCheckBox("Animate Flow")
        self.animate_flow_cb.setChecked(self.config.animate_flow)
        self.animate_flow_cb.toggled.connect(self._on_animation_toggled)
        display_layout.addWidget(self.animate_flow_cb)
        
        layout.addWidget(display_group)
        
        # Appearance group
        appearance_group = QGroupBox("Appearance")
        appearance_layout = QVBoxLayout(appearance_group)
        
        # Arrow size
        arrow_size_layout = QHBoxLayout()
        arrow_size_layout.addWidget(QLabel("Arrow Size:"))
        self.arrow_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.arrow_size_slider.setRange(8, 24)
        self.arrow_size_slider.setValue(int(self.config.arrow_size))
        self.arrow_size_slider.valueChanged.connect(self._on_config_changed)
        arrow_size_layout.addWidget(self.arrow_size_slider)
        appearance_layout.addLayout(arrow_size_layout)
        
        # Number size
        number_size_layout = QHBoxLayout()
        number_size_layout.addWidget(QLabel("Number Size:"))
        self.number_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.number_size_slider.setRange(12, 24)
        self.number_size_slider.setValue(int(self.config.number_size))
        self.number_size_slider.valueChanged.connect(self._on_config_changed)
        number_size_layout.addWidget(self.number_size_slider)
        appearance_layout.addLayout(number_size_layout)
        
        layout.addWidget(appearance_group)
        
        # Spacer
        layout.addStretch()
    
    def _on_mode_changed(self, index: int):
        """Handle mode change."""
        modes = [
            ReadingOrderMode.FLOW_ARROWS,
            ReadingOrderMode.NUMBERED_SEQUENCE,
            ReadingOrderMode.HIGHLIGHTED_PATH,
            ReadingOrderMode.SPATIAL_GROUPING
        ]
        
        if 0 <= index < len(modes):
            self.config.mode = modes[index]
            self.mode_changed.emit(self.config.mode)
            self._emit_config_changed()
    
    def _on_config_changed(self):
        """Handle configuration changes."""
        self.config.show_numbers = self.show_numbers_cb.isChecked()
        self.config.show_connections = self.show_connections_cb.isChecked()
        self.config.arrow_size = float(self.arrow_size_slider.value())
        self.config.number_size = float(self.number_size_slider.value())
        
        self._emit_config_changed()
    
    def _on_animation_toggled(self, enabled: bool):
        """Handle animation toggle."""
        self.config.animate_flow = enabled
        self.animation_toggled.emit(enabled)
        self._emit_config_changed()
    
    def _emit_config_changed(self):
        """Emit configuration changed signal."""
        self.config_changed.emit(self.config)


class ReadingOrderWidget(QWidget):
    """Main widget for reading order visualization and control."""
    
    # Signals
    element_selected = pyqtSignal(str)
    order_changed = pyqtSignal(list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.hierarchy_manager = None
        self.state_store = None
        self.current_elements = []
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Set up the UI."""
        layout = QHBoxLayout(self)
        
        # Create splitter
        from PyQt6.QtWidgets import QSplitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Visualization widget
        self.visualization = ReadingOrderVisualization()
        splitter.addWidget(self.visualization)
        
        # Control panel
        self.control_panel = ReadingOrderControlPanel()
        splitter.addWidget(self.control_panel)
        
        # Set splitter proportions
        splitter.setSizes([400, 200])
        
        layout.addWidget(splitter)
    
    def _connect_signals(self):
        """Connect widget signals."""
        # Visualization signals
        self.visualization.element_selected.connect(self._on_element_selected)
        self.visualization.order_changed.connect(self._on_order_changed)
        
        # Control panel signals
        self.control_panel.config_changed.connect(self._on_config_changed)
        self.control_panel.mode_changed.connect(self._on_mode_changed)
        self.control_panel.animation_toggled.connect(self._on_animation_toggled)
    
    def set_hierarchy_manager(self, manager: HierarchyManager):
        """Set the hierarchy manager."""
        self.hierarchy_manager = manager
        self.visualization.set_hierarchy_manager(manager)
    
    def set_state_store(self, store: StateStore):
        """Set the state store."""
        self.state_store = store
        self.visualization.set_state_store(store)
    
    def show_elements(self, elements: List[Element]):
        """Show reading order for elements."""
        self.current_elements = elements
        
        # Get reading order from hierarchy manager
        if self.hierarchy_manager:
            order = self.hierarchy_manager.get_reading_order()
            # Filter order to only include provided elements
            element_ids = {elem.id for elem in elements}
            filtered_order = [elem_id for elem_id in order if elem_id in element_ids]
            
            self.visualization.show_reading_order(elements, filtered_order)
    
    def highlight_element(self, element_id: str):
        """Highlight a specific element."""
        self.visualization.highlight_element(element_id)
    
    def set_current_element(self, element_id: str):
        """Set current element in reading flow."""
        self.visualization.set_current_element(element_id)
    
    def _on_element_selected(self, element_id: str):
        """Handle element selection."""
        self.element_selected.emit(element_id)
    
    def _on_order_changed(self, order: List[str]):
        """Handle order change."""
        self.order_changed.emit(order)
    
    def _on_config_changed(self, config: ReadingOrderConfig):
        """Handle configuration change."""
        self.visualization.set_config(config)
    
    def _on_mode_changed(self, mode: ReadingOrderMode):
        """Handle mode change."""
        # Mode-specific handling if needed
        pass
    
    def _on_animation_toggled(self, enabled: bool):
        """Handle animation toggle."""
        # Animation-specific handling if needed
        pass