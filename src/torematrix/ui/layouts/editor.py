"""Drag-and-Drop Layout Editor for TORE Matrix Labs V3.

This module provides an intuitive visual layout editor with drag-and-drop functionality,
real-time preview, grid alignment, and comprehensive editing tools.
"""

from typing import Dict, List, Optional, Any, Tuple, Set, Union
from enum import Enum, auto
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import logging
import json
from uuid import uuid4

from PyQt6.QtWidgets import (
    QWidget, QMainWindow, QSplitter, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QScrollArea, QToolBar, QAction, QComboBox,
    QSpinBox, QCheckBox, QButtonGroup, QTabWidget, QStackedWidget,
    QRubberBand, QApplication, QMenu, QDialog, QLineEdit, QTextEdit,
    QGroupBox, QSlider, QProgressBar
)
from PyQt6.QtCore import (
    Qt, QRect, QSize, QPoint, QMimeData, pyqtSignal, QObject, QTimer,
    QPropertyAnimation, QEasingCurve, QEvent
)
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QPixmap, QPalette, QDrag,
    QCursor, QIcon, QAction as QGuiAction, QKeySequence
)

from ...core.events import EventBus
from ...core.config import ConfigurationManager
from ...core.state import Store
from ..base import BaseUIComponent
from .base import LayoutConfiguration, LayoutType, LayoutGeometry, LayoutItem
from .manager import LayoutManager
from .animations import AnimationManager, AnimationConfiguration

logger = logging.getLogger(__name__)


class EditorMode(Enum):
    """Layout editor modes."""
    DESIGN = auto()     # Design/edit mode
    PREVIEW = auto()    # Preview mode
    CODE = auto()       # Code/JSON editing mode


class GridMode(Enum):
    """Grid display modes."""
    NONE = auto()       # No grid
    DOTS = auto()       # Dot grid
    LINES = auto()      # Line grid
    SNAP = auto()       # Snap-to-grid with lines


class ComponentCategory(Enum):
    """Categories of components in the palette."""
    CONTAINERS = auto()
    PANELS = auto()
    VIEWERS = auto()
    CONTROLS = auto()
    CUSTOM = auto()


@dataclass
class ComponentDefinition:
    """Definition of a draggable component."""
    id: str
    name: str
    category: ComponentCategory
    description: str
    icon_path: Optional[str] = None
    default_size: QSize = field(default_factory=lambda: QSize(200, 150))
    min_size: QSize = field(default_factory=lambda: QSize(50, 50))
    max_size: QSize = field(default_factory=lambda: QSize(2000, 2000))
    resizable: bool = True
    properties: Dict[str, Any] = field(default_factory=dict)
    
    def create_widget(self) -> QWidget:
        """Create a widget instance for this component."""
        widget = QWidget()
        widget.setObjectName(self.id)
        widget.resize(self.default_size)
        widget.setMinimumSize(self.min_size)
        widget.setMaximumSize(self.max_size)
        
        # Add visual representation
        layout = QVBoxLayout(widget)
        label = QLabel(self.name)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc; padding: 5px;")
        layout.addWidget(label)
        
        return widget


@dataclass
class EditorSettings:
    """Settings for the layout editor."""
    grid_size: int = 20
    grid_mode: GridMode = GridMode.SNAP
    show_rulers: bool = True
    show_guidelines: bool = True
    snap_to_grid: bool = True
    snap_tolerance: int = 10
    auto_save: bool = True
    auto_save_interval: int = 30  # seconds
    zoom_level: float = 1.0
    min_zoom: float = 0.25
    max_zoom: float = 4.0


@dataclass
class SelectionInfo:
    """Information about current selection."""
    selected_items: Set[str] = field(default_factory=set)
    primary_selection: Optional[str] = None
    selection_bounds: Optional[QRect] = None
    multi_select: bool = False


class DragDropHint:
    """Visual hint for drag-and-drop operations."""
    
    def __init__(self, rect: QRect, hint_type: str = "insert"):
        self.rect = rect
        self.hint_type = hint_type  # "insert", "replace", "invalid"
        self.visible = True
    
    def paint(self, painter: QPainter) -> None:
        """Paint the drag-drop hint."""
        if not self.visible:
            return
        
        # Set up painter
        painter.save()
        
        if self.hint_type == "insert":
            painter.setPen(QPen(QColor(0, 120, 215), 2, Qt.PenStyle.DashLine))
            painter.setBrush(QBrush(QColor(0, 120, 215, 50)))
        elif self.hint_type == "replace":
            painter.setPen(QPen(QColor(255, 165, 0), 2, Qt.PenStyle.SolidLine))
            painter.setBrush(QBrush(QColor(255, 165, 0, 50)))
        else:  # invalid
            painter.setPen(QPen(QColor(220, 53, 69), 2, Qt.PenStyle.SolidLine))
            painter.setBrush(QBrush(QColor(220, 53, 69, 50)))
        
        painter.drawRect(self.rect)
        painter.restore()


class ComponentPalette(QWidget):
    """Component palette for drag-and-drop."""
    
    # Signals
    component_requested = pyqtSignal(str)  # component_id
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self._components: Dict[ComponentCategory, List[ComponentDefinition]] = {}
        self._setup_ui()
        self._register_default_components()
    
    def _setup_ui(self) -> None:
        """Setup the palette UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Title
        title = QLabel("Components")
        title.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Category tabs
        self.category_tabs = QTabWidget()
        layout.addWidget(self.category_tabs)
        
        # Setup categories
        for category in ComponentCategory:
            self._setup_category_tab(category)
    
    def _setup_category_tab(self, category: ComponentCategory) -> None:
        """Setup a category tab."""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(5)
        layout.addStretch()
        
        scroll_area.setWidget(container)
        self.category_tabs.addTab(scroll_area, category.name.title())
    
    def _register_default_components(self) -> None:
        """Register default components."""
        # Container components
        self.register_component(ComponentDefinition(
            id="splitter_horizontal",
            name="Horizontal Splitter",
            category=ComponentCategory.CONTAINERS,
            description="Horizontal splitter container",
            default_size=QSize(400, 200)
        ))
        
        self.register_component(ComponentDefinition(
            id="splitter_vertical",
            name="Vertical Splitter", 
            category=ComponentCategory.CONTAINERS,
            description="Vertical splitter container",
            default_size=QSize(200, 400)
        ))
        
        self.register_component(ComponentDefinition(
            id="tab_widget",
            name="Tab Container",
            category=ComponentCategory.CONTAINERS,
            description="Tabbed container widget",
            default_size=QSize(300, 200)
        ))
        
        # Panel components
        self.register_component(ComponentDefinition(
            id="document_viewer",
            name="Document Viewer",
            category=ComponentCategory.PANELS,
            description="Main document viewing panel",
            default_size=QSize(600, 400)
        ))
        
        self.register_component(ComponentDefinition(
            id="properties_panel",
            name="Properties Panel",
            category=ComponentCategory.PANELS,
            description="Document properties panel",
            default_size=QSize(250, 300)
        ))
        
        self.register_component(ComponentDefinition(
            id="corrections_panel",
            name="Corrections Panel",
            category=ComponentCategory.PANELS,
            description="Document corrections panel",
            default_size=QSize(250, 300)
        ))
        
        # Viewer components
        self.register_component(ComponentDefinition(
            id="pdf_viewer",
            name="PDF Viewer",
            category=ComponentCategory.VIEWERS,
            description="PDF document viewer",
            default_size=QSize(500, 600)
        ))
        
        self.register_component(ComponentDefinition(
            id="text_viewer",
            name="Text Viewer",
            category=ComponentCategory.VIEWERS,
            description="Text content viewer",
            default_size=QSize(400, 300)
        ))
    
    def register_component(self, component: ComponentDefinition) -> None:
        """Register a new component."""
        if component.category not in self._components:
            self._components[component.category] = []
        
        self._components[component.category].append(component)
        self._add_component_to_palette(component)
    
    def _add_component_to_palette(self, component: ComponentDefinition) -> None:
        """Add component button to the palette."""
        category_index = list(ComponentCategory).index(component.category)
        tab_widget = self.category_tabs.widget(category_index)
        
        if isinstance(tab_widget, QScrollArea):
            container = tab_widget.widget()
            if container and container.layout():
                layout = container.layout()
                
                # Remove stretch
                if layout.count() > 0:
                    layout.takeAt(layout.count() - 1)
                
                # Create component button
                button = QPushButton(component.name)
                button.setToolTip(component.description)
                button.setMinimumHeight(30)
                button.clicked.connect(lambda: self.component_requested.emit(component.id))
                
                # Enable drag from button
                button.setAcceptDrops(False)
                button.mousePressEvent = lambda event, comp_id=component.id: self._start_drag(event, comp_id)
                
                layout.addWidget(button)
                layout.addStretch()
    
    def _start_drag(self, event, component_id: str) -> None:
        """Start drag operation for component."""
        if event.button() == Qt.MouseButton.LeftButton:
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(f"component:{component_id}")
            drag.setMimeData(mime_data)
            
            # Create drag pixmap
            pixmap = QPixmap(100, 60)
            pixmap.fill(QColor(200, 200, 200, 180))
            painter = QPainter(pixmap)
            painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, 
                           self.get_component(component_id).name if self.get_component(component_id) else component_id)
            painter.end()
            
            drag.setPixmap(pixmap)
            drag.setHotSpot(QPoint(50, 30))
            
            # Execute drag
            drag.exec(Qt.DropAction.MoveAction)
    
    def get_component(self, component_id: str) -> Optional[ComponentDefinition]:
        """Get component definition by ID."""
        for components in self._components.values():
            for component in components:
                if component.id == component_id:
                    return component
        return None


class LayoutCanvas(QWidget):
    """Main canvas for layout editing."""
    
    # Signals
    selection_changed = pyqtSignal(list)  # selected_item_ids
    component_added = pyqtSignal(str, QRect)  # component_id, geometry
    component_moved = pyqtSignal(str, QRect)  # component_id, new_geometry
    component_resized = pyqtSignal(str, QSize)  # component_id, new_size
    layout_modified = pyqtSignal()
    
    def __init__(self, settings: EditorSettings, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self.settings = settings
        self._components: Dict[str, QWidget] = {}
        self._selection = SelectionInfo()
        self._drag_hint: Optional[DragDropHint] = None
        
        # Interaction state
        self._dragging = False
        self._resizing = False
        self._drag_start_pos = QPoint()
        self._original_geometries: Dict[str, QRect] = {}
        self._resize_handle: Optional[str] = None  # "nw", "ne", "sw", "se", "n", "s", "e", "w"
        
        # Selection rubber band
        self._rubber_band: Optional[QRubberBand] = None
        self._rubber_band_start = QPoint()
        
        self._setup_canvas()
    
    def _setup_canvas(self) -> None:
        """Setup the canvas."""
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumSize(800, 600)
        
        # Style
        self.setStyleSheet("""
            LayoutCanvas {
                background-color: white;
                border: 1px solid #ccc;
            }
        """)
    
    def paintEvent(self, event) -> None:
        """Paint the canvas."""
        super().paintEvent(event)
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw grid
        if self.settings.grid_mode != GridMode.NONE:
            self._draw_grid(painter)
        
        # Draw rulers
        if self.settings.show_rulers:
            self._draw_rulers(painter)
        
        # Draw selection handles
        self._draw_selection_handles(painter)
        
        # Draw drag hint
        if self._drag_hint:
            self._drag_hint.paint(painter)
        
        # Draw guidelines
        if self.settings.show_guidelines:
            self._draw_guidelines(painter)
    
    def _draw_grid(self, painter: QPainter) -> None:
        """Draw grid on canvas."""
        grid_size = self.settings.grid_size
        width = self.width()
        height = self.height()
        
        if self.settings.grid_mode == GridMode.DOTS:
            painter.setPen(QPen(QColor(200, 200, 200), 1))
            for x in range(0, width, grid_size):
                for y in range(0, height, grid_size):
                    painter.drawPoint(x, y)
        
        elif self.settings.grid_mode in (GridMode.LINES, GridMode.SNAP):
            painter.setPen(QPen(QColor(230, 230, 230), 1))
            
            # Vertical lines
            for x in range(0, width, grid_size):
                painter.drawLine(x, 0, x, height)
            
            # Horizontal lines
            for y in range(0, height, grid_size):
                painter.drawLine(0, y, width, y)
    
    def _draw_rulers(self, painter: QPainter) -> None:
        """Draw rulers along edges."""
        ruler_size = 20
        painter.fillRect(0, 0, self.width(), ruler_size, QColor(240, 240, 240))
        painter.fillRect(0, 0, ruler_size, self.height(), QColor(240, 240, 240))
        
        painter.setPen(QPen(QColor(100, 100, 100), 1))
        font = QFont("Arial", 8)
        painter.setFont(font)
        
        # Horizontal ruler
        for x in range(0, self.width(), 50):
            painter.drawLine(x, 15, x, ruler_size)
            if x > 0:
                painter.drawText(x + 2, 12, str(x))
        
        # Vertical ruler
        for y in range(0, self.height(), 50):
            painter.drawLine(15, y, ruler_size, y)
            if y > 0:
                painter.save()
                painter.translate(12, y - 2)
                painter.rotate(-90)
                painter.drawText(0, 0, str(y))
                painter.restore()
    
    def _draw_selection_handles(self, painter: QPainter) -> None:
        """Draw selection handles for selected components."""
        if not self._selection.selected_items:
            return
        
        painter.setPen(QPen(QColor(0, 120, 215), 2))
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        
        handle_size = 8
        
        for item_id in self._selection.selected_items:
            if item_id in self._components:
                widget = self._components[item_id]
                rect = widget.geometry()
                
                # Draw selection border
                painter.drawRect(rect)
                
                # Draw resize handles
                handles = [
                    (rect.left() - handle_size // 2, rect.top() - handle_size // 2),  # nw
                    (rect.right() - handle_size // 2, rect.top() - handle_size // 2),  # ne
                    (rect.left() - handle_size // 2, rect.bottom() - handle_size // 2),  # sw
                    (rect.right() - handle_size // 2, rect.bottom() - handle_size // 2),  # se
                    (rect.left() + rect.width() // 2 - handle_size // 2, rect.top() - handle_size // 2),  # n
                    (rect.left() + rect.width() // 2 - handle_size // 2, rect.bottom() - handle_size // 2),  # s
                    (rect.left() - handle_size // 2, rect.top() + rect.height() // 2 - handle_size // 2),  # w
                    (rect.right() - handle_size // 2, rect.top() + rect.height() // 2 - handle_size // 2),  # e
                ]
                
                for x, y in handles:
                    painter.drawRect(x, y, handle_size, handle_size)
    
    def _draw_guidelines(self, painter: QPainter) -> None:
        """Draw alignment guidelines."""
        # This would show guidelines when dragging components
        # For now, just a placeholder
        pass
    
    def mousePressEvent(self, event) -> None:
        """Handle mouse press events."""
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            
            # Check for resize handle
            handle = self._get_resize_handle_at_pos(pos)
            if handle:
                self._start_resize(handle, pos)
                return
            
            # Check for component selection
            selected_component = self._get_component_at_pos(pos)
            if selected_component:
                self._start_drag(selected_component, pos)
            else:
                # Start rubber band selection
                self._start_rubber_band_selection(pos)
    
    def mouseMoveEvent(self, event) -> None:
        """Handle mouse move events."""
        pos = event.position().toPoint()
        
        if self._resizing:
            self._update_resize(pos)
        elif self._dragging:
            self._update_drag(pos)
        elif self._rubber_band:
            self._update_rubber_band_selection(pos)
        else:
            # Update cursor based on hover
            self._update_cursor(pos)
    
    def mouseReleaseEvent(self, event) -> None:
        """Handle mouse release events."""
        if event.button() == Qt.MouseButton.LeftButton:
            if self._resizing:
                self._end_resize()
            elif self._dragging:
                self._end_drag()
            elif self._rubber_band:
                self._end_rubber_band_selection()
    
    def _get_resize_handle_at_pos(self, pos: QPoint) -> Optional[str]:
        """Get resize handle at position."""
        if not self._selection.selected_items:
            return None
        
        handle_size = 8
        tolerance = 4
        
        for item_id in self._selection.selected_items:
            if item_id in self._components:
                widget = self._components[item_id]
                rect = widget.geometry()
                
                handles = {
                    "nw": QRect(rect.left() - handle_size // 2, rect.top() - handle_size // 2, handle_size, handle_size),
                    "ne": QRect(rect.right() - handle_size // 2, rect.top() - handle_size // 2, handle_size, handle_size),
                    "sw": QRect(rect.left() - handle_size // 2, rect.bottom() - handle_size // 2, handle_size, handle_size),
                    "se": QRect(rect.right() - handle_size // 2, rect.bottom() - handle_size // 2, handle_size, handle_size),
                    "n": QRect(rect.left() + rect.width() // 2 - handle_size // 2, rect.top() - handle_size // 2, handle_size, handle_size),
                    "s": QRect(rect.left() + rect.width() // 2 - handle_size // 2, rect.bottom() - handle_size // 2, handle_size, handle_size),
                    "w": QRect(rect.left() - handle_size // 2, rect.top() + rect.height() // 2 - handle_size // 2, handle_size, handle_size),
                    "e": QRect(rect.right() - handle_size // 2, rect.top() + rect.height() // 2 - handle_size // 2, handle_size, handle_size),
                }
                
                for handle_name, handle_rect in handles.items():
                    if handle_rect.adjusted(-tolerance, -tolerance, tolerance, tolerance).contains(pos):
                        return handle_name
        
        return None
    
    def _get_component_at_pos(self, pos: QPoint) -> Optional[str]:
        """Get component at position."""
        for item_id, widget in self._components.items():
            if widget.geometry().contains(pos):
                return item_id
        return None
    
    def _start_drag(self, component_id: str, pos: QPoint) -> None:
        """Start dragging a component."""
        self._dragging = True
        self._drag_start_pos = pos
        
        # Store original geometries
        self._original_geometries.clear()
        for item_id in self._selection.selected_items:
            if item_id in self._components:
                self._original_geometries[item_id] = self._components[item_id].geometry()
        
        # Select the component if not already selected
        if component_id not in self._selection.selected_items:
            self._selection.selected_items = {component_id}
            self._selection.primary_selection = component_id
            self.selection_changed.emit(list(self._selection.selected_items))
    
    def _update_drag(self, pos: QPoint) -> None:
        """Update drag operation."""
        if not self._dragging:
            return
        
        delta = pos - self._drag_start_pos
        
        # Apply snap to grid
        if self.settings.snap_to_grid:
            delta = self._snap_to_grid(delta)
        
        # Move all selected components
        for item_id in self._selection.selected_items:
            if item_id in self._components and item_id in self._original_geometries:
                widget = self._components[item_id]
                original_rect = self._original_geometries[item_id]
                new_rect = original_rect.translated(delta)
                
                # Constrain to canvas bounds
                new_rect = self._constrain_to_canvas(new_rect)
                
                widget.setGeometry(new_rect)
        
        self.update()
    
    def _end_drag(self) -> None:
        """End drag operation."""
        if self._dragging:
            self._dragging = False
            
            # Emit moved signals
            for item_id in self._selection.selected_items:
                if item_id in self._components:
                    widget = self._components[item_id]
                    self.component_moved.emit(item_id, widget.geometry())
            
            self.layout_modified.emit()
    
    def _start_resize(self, handle: str, pos: QPoint) -> None:
        """Start resizing operation."""
        self._resizing = True
        self._resize_handle = handle
        self._drag_start_pos = pos
        
        # Store original geometries
        self._original_geometries.clear()
        for item_id in self._selection.selected_items:
            if item_id in self._components:
                self._original_geometries[item_id] = self._components[item_id].geometry()
    
    def _update_resize(self, pos: QPoint) -> None:
        """Update resize operation."""
        if not self._resizing or not self._resize_handle:
            return
        
        delta = pos - self._drag_start_pos
        
        # Apply snap to grid
        if self.settings.snap_to_grid:
            delta = self._snap_to_grid(delta)
        
        # Resize selected components
        for item_id in self._selection.selected_items:
            if item_id in self._components and item_id in self._original_geometries:
                widget = self._components[item_id]
                original_rect = self._original_geometries[item_id]
                new_rect = self._calculate_resize_rect(original_rect, delta, self._resize_handle)
                
                # Apply size constraints
                new_rect = self._apply_size_constraints(new_rect, widget)
                
                widget.setGeometry(new_rect)
        
        self.update()
    
    def _end_resize(self) -> None:
        """End resize operation."""
        if self._resizing:
            self._resizing = False
            self._resize_handle = None
            
            # Emit resized signals
            for item_id in self._selection.selected_items:
                if item_id in self._components:
                    widget = self._components[item_id]
                    self.component_resized.emit(item_id, widget.size())
            
            self.layout_modified.emit()
    
    def _calculate_resize_rect(self, original_rect: QRect, delta: QPoint, handle: str) -> QRect:
        """Calculate new rectangle for resize operation."""
        new_rect = QRect(original_rect)
        
        if "n" in handle:
            new_rect.setTop(original_rect.top() + delta.y())
        if "s" in handle:
            new_rect.setBottom(original_rect.bottom() + delta.y())
        if "w" in handle:
            new_rect.setLeft(original_rect.left() + delta.x())
        if "e" in handle:
            new_rect.setRight(original_rect.right() + delta.x())
        
        return new_rect
    
    def _apply_size_constraints(self, rect: QRect, widget: QWidget) -> QRect:
        """Apply size constraints to rectangle."""
        min_size = widget.minimumSize()
        max_size = widget.maximumSize()
        
        # Ensure minimum size
        if rect.width() < min_size.width():
            rect.setWidth(min_size.width())
        if rect.height() < min_size.height():
            rect.setHeight(min_size.height())
        
        # Ensure maximum size
        if rect.width() > max_size.width():
            rect.setWidth(max_size.width())
        if rect.height() > max_size.height():
            rect.setHeight(max_size.height())
        
        return rect
    
    def _start_rubber_band_selection(self, pos: QPoint) -> None:
        """Start rubber band selection."""
        self._rubber_band_start = pos
        self._rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, self)
        self._rubber_band.setGeometry(QRect(pos, QSize()))
        self._rubber_band.show()
    
    def _update_rubber_band_selection(self, pos: QPoint) -> None:
        """Update rubber band selection."""
        if self._rubber_band:
            rect = QRect(self._rubber_band_start, pos).normalized()
            self._rubber_band.setGeometry(rect)
            
            # Update selection based on rubber band
            new_selection = set()
            for item_id, widget in self._components.items():
                if rect.intersects(widget.geometry()):
                    new_selection.add(item_id)
            
            if new_selection != self._selection.selected_items:
                self._selection.selected_items = new_selection
                self._selection.primary_selection = list(new_selection)[0] if new_selection else None
                self.selection_changed.emit(list(new_selection))
    
    def _end_rubber_band_selection(self) -> None:
        """End rubber band selection."""
        if self._rubber_band:
            self._rubber_band.hide()
            self._rubber_band.deleteLater()
            self._rubber_band = None
    
    def _snap_to_grid(self, delta: QPoint) -> QPoint:
        """Snap delta to grid."""
        grid_size = self.settings.grid_size
        
        snapped_x = round(delta.x() / grid_size) * grid_size
        snapped_y = round(delta.y() / grid_size) * grid_size
        
        return QPoint(snapped_x, snapped_y)
    
    def _constrain_to_canvas(self, rect: QRect) -> QRect:
        """Constrain rectangle to canvas bounds."""
        canvas_rect = self.rect()
        
        if rect.left() < canvas_rect.left():
            rect.moveLeft(canvas_rect.left())
        if rect.top() < canvas_rect.top():
            rect.moveTop(canvas_rect.top())
        if rect.right() > canvas_rect.right():
            rect.moveRight(canvas_rect.right())
        if rect.bottom() > canvas_rect.bottom():
            rect.moveBottom(canvas_rect.bottom())
        
        return rect
    
    def _update_cursor(self, pos: QPoint) -> None:
        """Update cursor based on position."""
        handle = self._get_resize_handle_at_pos(pos)
        
        if handle:
            cursor_map = {
                "nw": Qt.CursorShape.SizeFDiagCursor,
                "ne": Qt.CursorShape.SizeBDiagCursor,
                "sw": Qt.CursorShape.SizeBDiagCursor,
                "se": Qt.CursorShape.SizeFDiagCursor,
                "n": Qt.CursorShape.SizeVerCursor,
                "s": Qt.CursorShape.SizeVerCursor,
                "w": Qt.CursorShape.SizeHorCursor,
                "e": Qt.CursorShape.SizeHorCursor,
            }
            self.setCursor(cursor_map.get(handle, Qt.CursorShape.ArrowCursor))
        elif self._get_component_at_pos(pos):
            self.setCursor(Qt.CursorShape.SizeAllCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
    
    def dragEnterEvent(self, event) -> None:
        """Handle drag enter events."""
        if event.mimeData().hasText() and event.mimeData().text().startswith("component:"):
            event.acceptProposedAction()
    
    def dragMoveEvent(self, event) -> None:
        """Handle drag move events."""
        if event.mimeData().hasText() and event.mimeData().text().startswith("component:"):
            pos = event.position().toPoint()
            
            # Create drag hint
            component_id = event.mimeData().text().split(":", 1)[1]
            hint_rect = QRect(pos.x() - 50, pos.y() - 25, 100, 50)
            self._drag_hint = DragDropHint(hint_rect, "insert")
            
            self.update()
            event.acceptProposedAction()
    
    def dragLeaveEvent(self, event) -> None:
        """Handle drag leave events."""
        self._drag_hint = None
        self.update()
    
    def dropEvent(self, event) -> None:
        """Handle drop events."""
        if event.mimeData().hasText() and event.mimeData().text().startswith("component:"):
            component_id = event.mimeData().text().split(":", 1)[1]
            pos = event.position().toPoint()
            
            # Calculate drop geometry
            drop_rect = QRect(pos.x() - 50, pos.y() - 25, 100, 50)
            
            # Snap to grid
            if self.settings.snap_to_grid:
                grid_size = self.settings.grid_size
                snap_x = round(drop_rect.x() / grid_size) * grid_size
                snap_y = round(drop_rect.y() / grid_size) * grid_size
                drop_rect.moveTo(snap_x, snap_y)
            
            self.component_added.emit(component_id, drop_rect)
            event.acceptProposedAction()
        
        self._drag_hint = None
        self.update()
    
    def add_component(self, component_id: str, component_def: ComponentDefinition, geometry: QRect) -> None:
        """Add a component to the canvas."""
        widget = component_def.create_widget()
        widget.setParent(self)
        widget.setGeometry(geometry)
        widget.show()
        
        self._components[component_id] = widget
        
        logger.debug(f"Added component {component_id} to canvas at {geometry}")
    
    def remove_component(self, component_id: str) -> None:
        """Remove a component from the canvas."""
        if component_id in self._components:
            widget = self._components[component_id]
            widget.deleteLater()
            del self._components[component_id]
            
            # Remove from selection
            self._selection.selected_items.discard(component_id)
            if self._selection.primary_selection == component_id:
                self._selection.primary_selection = None
            
            self.selection_changed.emit(list(self._selection.selected_items))
            logger.debug(f"Removed component {component_id} from canvas")
    
    def clear_selection(self) -> None:
        """Clear current selection."""
        self._selection.selected_items.clear()
        self._selection.primary_selection = None
        self.selection_changed.emit([])
        self.update()
    
    def select_all(self) -> None:
        """Select all components."""
        self._selection.selected_items = set(self._components.keys())
        self._selection.primary_selection = list(self._components.keys())[0] if self._components else None
        self.selection_changed.emit(list(self._selection.selected_items))
        self.update()
    
    def delete_selected(self) -> None:
        """Delete selected components."""
        for component_id in list(self._selection.selected_items):
            self.remove_component(component_id)
        
        self.layout_modified.emit()


class LayoutEditor(BaseUIComponent):
    """Main layout editor window with drag-and-drop functionality."""
    
    # Signals
    layout_saved = pyqtSignal(str)  # layout_id
    layout_loaded = pyqtSignal(str)  # layout_id
    editor_mode_changed = pyqtSignal(EditorMode)
    
    def __init__(
        self,
        layout_manager: LayoutManager,
        animation_manager: AnimationManager,
        event_bus: EventBus,
        config_manager: ConfigurationManager,
        state_manager: Store,
        parent: Optional[QWidget] = None
    ):
        super().__init__(event_bus, config_manager, state_manager, parent)
        
        self.layout_manager = layout_manager
        self.animation_manager = animation_manager
        
        # Editor state
        self.settings = EditorSettings()
        self.current_mode = EditorMode.DESIGN
        self.current_layout_id: Optional[str] = None
        self.component_palette: Optional[ComponentPalette] = None
        self.canvas: Optional[LayoutCanvas] = None
        
        # Component tracking
        self._component_definitions: Dict[str, ComponentDefinition] = {}
        self._canvas_components: Dict[str, str] = {}  # component_instance_id -> definition_id
        
        self._setup_ui()
        self._setup_connections()
    
    def _setup_component(self) -> None:
        """Setup the editor component."""
        # Subscribe to events
        self.subscribe_to_event("layout.editor_open", self._handle_editor_open)
        self.subscribe_to_event("layout.editor_save", self._handle_editor_save)
        
        # Load settings
        self._load_editor_settings()
        
        logger.info("Layout editor setup complete")
    
    def _setup_ui(self) -> None:
        """Setup the editor UI."""
        if isinstance(self.parent(), QMainWindow):
            main_window = self.parent()
        else:
            main_window = QMainWindow()
            main_window.setWindowTitle("Layout Editor")
            main_window.resize(1200, 800)
        
        # Central widget
        central_widget = QWidget()
        main_window.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Component palette (left)
        self.component_palette = ComponentPalette()
        self.component_palette.setFixedWidth(200)
        main_layout.addWidget(self.component_palette)
        
        # Canvas area (center)
        canvas_container = QWidget()
        canvas_layout = QVBoxLayout(canvas_container)
        canvas_layout.setContentsMargins(0, 0, 0, 0)
        
        # Toolbar
        toolbar = self._create_toolbar()
        canvas_layout.addWidget(toolbar)
        
        # Canvas
        self.canvas = LayoutCanvas(self.settings)
        canvas_layout.addWidget(self.canvas)
        
        main_layout.addWidget(canvas_container, 1)
        
        # Properties panel (right)
        properties_panel = self._create_properties_panel()
        properties_panel.setFixedWidth(250)
        main_layout.addWidget(properties_panel)
    
    def _create_toolbar(self) -> QToolBar:
        """Create editor toolbar."""
        toolbar = QToolBar()
        toolbar.setMovable(False)
        
        # Mode selection
        mode_group = QButtonGroup(toolbar)
        
        design_btn = QPushButton("Design")
        design_btn.setCheckable(True)
        design_btn.setChecked(True)
        design_btn.clicked.connect(lambda: self.set_editor_mode(EditorMode.DESIGN))
        mode_group.addButton(design_btn)
        toolbar.addWidget(design_btn)
        
        preview_btn = QPushButton("Preview")
        preview_btn.setCheckable(True)
        preview_btn.clicked.connect(lambda: self.set_editor_mode(EditorMode.PREVIEW))
        mode_group.addButton(preview_btn)
        toolbar.addWidget(preview_btn)
        
        code_btn = QPushButton("Code")
        code_btn.setCheckable(True)
        code_btn.clicked.connect(lambda: self.set_editor_mode(EditorMode.CODE))
        mode_group.addButton(code_btn)
        toolbar.addWidget(code_btn)
        
        toolbar.addSeparator()
        
        # Grid controls
        grid_cb = QCheckBox("Grid")
        grid_cb.setChecked(self.settings.grid_mode != GridMode.NONE)
        grid_cb.toggled.connect(self._toggle_grid)
        toolbar.addWidget(grid_cb)
        
        snap_cb = QCheckBox("Snap")
        snap_cb.setChecked(self.settings.snap_to_grid)
        snap_cb.toggled.connect(self._toggle_snap)
        toolbar.addWidget(snap_cb)
        
        toolbar.addSeparator()
        
        # Zoom controls
        zoom_label = QLabel("Zoom:")
        toolbar.addWidget(zoom_label)
        
        zoom_slider = QSlider(Qt.Orientation.Horizontal)
        zoom_slider.setRange(25, 400)  # 25% to 400%
        zoom_slider.setValue(int(self.settings.zoom_level * 100))
        zoom_slider.setFixedWidth(100)
        zoom_slider.valueChanged.connect(self._on_zoom_changed)
        toolbar.addWidget(zoom_slider)
        
        return toolbar
    
    def _create_properties_panel(self) -> QWidget:
        """Create properties panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Title
        title = QLabel("Properties")
        title.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Properties area (placeholder)
        properties_area = QTextEdit()
        properties_area.setPlaceholderText("Select a component to view properties")
        properties_area.setMaximumHeight(200)
        layout.addWidget(properties_area)
        
        # Settings group
        settings_group = QGroupBox("Editor Settings")
        settings_layout = QVBoxLayout(settings_group)
        
        # Grid size
        grid_size_layout = QHBoxLayout()
        grid_size_layout.addWidget(QLabel("Grid Size:"))
        grid_size_spin = QSpinBox()
        grid_size_spin.setRange(5, 50)
        grid_size_spin.setValue(self.settings.grid_size)
        grid_size_spin.valueChanged.connect(self._on_grid_size_changed)
        grid_size_layout.addWidget(grid_size_spin)
        settings_layout.addLayout(grid_size_layout)
        
        layout.addWidget(settings_group)
        layout.addStretch()
        
        return panel
    
    def _setup_connections(self) -> None:
        """Setup signal connections."""
        if self.component_palette:
            self.component_palette.component_requested.connect(self._on_component_requested)
        
        if self.canvas:
            self.canvas.selection_changed.connect(self._on_selection_changed)
            self.canvas.component_added.connect(self._on_component_added)
            self.canvas.component_moved.connect(self._on_component_moved)
            self.canvas.component_resized.connect(self._on_component_resized)
            self.canvas.layout_modified.connect(self._on_layout_modified)
    
    def _load_editor_settings(self) -> None:
        """Load editor settings from configuration."""
        self.settings.grid_size = self.get_config("editor.grid_size", 20)
        self.settings.snap_to_grid = self.get_config("editor.snap_to_grid", True)
        self.settings.show_rulers = self.get_config("editor.show_rulers", True)
        self.settings.auto_save = self.get_config("editor.auto_save", True)
        self.settings.auto_save_interval = self.get_config("editor.auto_save_interval", 30)
    
    def set_editor_mode(self, mode: EditorMode) -> None:
        """Set the editor mode."""
        if mode != self.current_mode:
            self.current_mode = mode
            self.editor_mode_changed.emit(mode)
            
            # Update UI based on mode
            if self.canvas:
                if mode == EditorMode.PREVIEW:
                    self.canvas.clear_selection()
                    self.canvas.setEnabled(False)
                else:
                    self.canvas.setEnabled(True)
            
            logger.debug(f"Editor mode changed to: {mode.name}")
    
    def _toggle_grid(self, enabled: bool) -> None:
        """Toggle grid display."""
        self.settings.grid_mode = GridMode.SNAP if enabled else GridMode.NONE
        if self.canvas:
            self.canvas.update()
    
    def _toggle_snap(self, enabled: bool) -> None:
        """Toggle snap to grid."""
        self.settings.snap_to_grid = enabled
    
    def _on_zoom_changed(self, value: int) -> None:
        """Handle zoom level change."""
        self.settings.zoom_level = value / 100.0
        # Apply zoom transformation to canvas
        if self.canvas:
            transform = self.canvas.transform()
            transform.reset()
            transform.scale(self.settings.zoom_level, self.settings.zoom_level)
            self.canvas.setTransform(transform)
    
    def _on_grid_size_changed(self, value: int) -> None:
        """Handle grid size change."""
        self.settings.grid_size = value
        if self.canvas:
            self.canvas.update()
    
    def _on_component_requested(self, component_id: str) -> None:
        """Handle component request from palette."""
        if self.component_palette and self.canvas:
            component_def = self.component_palette.get_component(component_id)
            if component_def:
                # Add component to center of canvas
                canvas_center = self.canvas.rect().center()
                geometry = QRect(
                    canvas_center.x() - component_def.default_size.width() // 2,
                    canvas_center.y() - component_def.default_size.height() // 2,
                    component_def.default_size.width(),
                    component_def.default_size.height()
                )
                
                instance_id = f"{component_id}_{uuid4().hex[:8]}"
                self._component_definitions[instance_id] = component_def
                self._canvas_components[instance_id] = component_id
                
                self.canvas.add_component(instance_id, component_def, geometry)
    
    def _on_component_added(self, component_id: str, geometry: QRect) -> None:
        """Handle component added to canvas."""
        if self.component_palette:
            # Extract base component ID
            base_component_id = component_id.split("_")[0] if "_" in component_id else component_id
            component_def = self.component_palette.get_component(base_component_id)
            
            if component_def:
                instance_id = f"{component_id}_{uuid4().hex[:8]}"
                self._component_definitions[instance_id] = component_def
                self._canvas_components[instance_id] = base_component_id
                
                self.canvas.add_component(instance_id, component_def, geometry)
    
    def _on_selection_changed(self, selected_items: List[str]) -> None:
        """Handle selection change."""
        logger.debug(f"Selection changed: {selected_items}")
        # Update properties panel based on selection
    
    def _on_component_moved(self, component_id: str, geometry: QRect) -> None:
        """Handle component moved."""
        logger.debug(f"Component {component_id} moved to {geometry}")
    
    def _on_component_resized(self, component_id: str, size: QSize) -> None:
        """Handle component resized."""
        logger.debug(f"Component {component_id} resized to {size}")
    
    def _on_layout_modified(self) -> None:
        """Handle layout modification."""
        if self.settings.auto_save and self.current_layout_id:
            # Schedule auto-save
            QTimer.singleShot(self.settings.auto_save_interval * 1000, self._auto_save_layout)
    
    def _auto_save_layout(self) -> None:
        """Auto-save the current layout."""
        if self.current_layout_id:
            self.save_layout(self.current_layout_id)
    
    def save_layout(self, layout_id: str) -> bool:
        """Save the current layout."""
        try:
            # Create layout configuration from canvas state
            layout_config = self._create_layout_configuration(layout_id)
            
            # Save through layout manager
            # This would integrate with the layout persistence system
            
            self.layout_saved.emit(layout_id)
            logger.info(f"Layout saved: {layout_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save layout {layout_id}: {e}")
            return False
    
    def load_layout(self, layout_id: str) -> bool:
        """Load a layout for editing."""
        try:
            # Load layout configuration
            # This would integrate with the layout persistence system
            
            self.current_layout_id = layout_id
            self.layout_loaded.emit(layout_id)
            logger.info(f"Layout loaded: {layout_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load layout {layout_id}: {e}")
            return False
    
    def _create_layout_configuration(self, layout_id: str) -> LayoutConfiguration:
        """Create layout configuration from current canvas state."""
        # This would extract the current layout from the canvas
        # and convert it to a LayoutConfiguration object
        geometry = LayoutGeometry(
            width=self.canvas.width() if self.canvas else 800,
            height=self.canvas.height() if self.canvas else 600
        )
        
        return LayoutConfiguration(
            id=layout_id,
            name=f"Layout {layout_id}",
            layout_type=LayoutType.CUSTOM,
            geometry=geometry
        )
    
    # Event handlers
    def _handle_editor_open(self, event_data: Dict[str, Any]) -> None:
        """Handle editor open event."""
        layout_id = event_data.get("layout_id")
        if layout_id:
            self.load_layout(layout_id)
    
    def _handle_editor_save(self, event_data: Dict[str, Any]) -> None:
        """Handle editor save event."""
        layout_id = event_data.get("layout_id") or self.current_layout_id
        if layout_id:
            self.save_layout(layout_id)