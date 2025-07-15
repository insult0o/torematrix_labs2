"""
Drag and Drop Handler for Element Tree View

Provides drag-and-drop functionality with visual feedback and validation.
"""

from typing import List, Optional, Dict, Any, Tuple
from PyQt6.QtCore import QMimeData, QPoint, Qt, QRect, pyqtSignal, QObject
from PyQt6.QtGui import QDrag, QPainter, QPixmap, QColor, QPen, QBrush
from PyQt6.QtWidgets import QTreeView, QRubberBand, QWidget

from ..models.tree_node import TreeNode
from ..interfaces.tree_interfaces import ElementProtocol


class DragDropValidator:
    """Validates drag and drop operations."""
    
    @staticmethod
    def can_drop_on_target(source_node: TreeNode, target_node: TreeNode) -> Tuple[bool, str]:
        """
        Check if source can be dropped on target.
        
        Args:
            source_node: Node being dragged
            target_node: Target node for drop
            
        Returns:
            Tuple of (can_drop, reason)
        """
        if not source_node or not target_node:
            return False, "Invalid nodes"
        
        # Cannot drop on self
        if source_node is target_node:
            return False, "Cannot drop on self"
        
        # Cannot drop on descendant (would create cycle)
        if source_node.is_ancestor_of(target_node):
            return False, "Cannot drop on descendant"
        
        # Check element type compatibility
        source_element = source_node.element()
        target_element = target_node.element()
        
        if source_element and target_element:
            # Business logic: some element types cannot contain others
            incompatible_combinations = {
                ('table_cell', 'table'),  # Table cell cannot contain another table
                ('list_item', 'list'),    # List item cannot contain another list at same level
            }
            
            combination = (source_element.type, target_element.type)
            if combination in incompatible_combinations:
                return False, f"Cannot drop {source_element.type} on {target_element.type}"
        
        return True, "Valid drop"
    
    @staticmethod
    def get_insert_position(target_node: TreeNode, drop_position: str) -> Tuple[TreeNode, int]:
        """
        Get the actual parent and position for insertion.
        
        Args:
            target_node: Target node
            drop_position: 'above', 'below', or 'on'
            
        Returns:
            Tuple of (parent_node, insert_index)
        """
        if drop_position == 'on':
            return target_node, target_node.child_count()
        
        parent = target_node.parent()
        if not parent:
            # Target is root level
            return target_node, 0 if drop_position == 'above' else 1
        
        target_index = parent.index_of_child(target_node)
        if drop_position == 'above':
            return parent, target_index
        else:  # below
            return parent, target_index + 1


class DropIndicator:
    """Visual indicator for drop operations."""
    
    def __init__(self, tree_view: QTreeView):
        self.tree_view = tree_view
        self.indicator_rect = QRect()
        self.drop_position = ""
        self.visible = False
    
    def show_indicator(self, index, position: str) -> None:
        """Show drop indicator at specified position."""
        if not index.isValid():
            self.hide_indicator()
            return
        
        rect = self.tree_view.visualRect(index)
        
        if position == 'above':
            self.indicator_rect = QRect(rect.left(), rect.top() - 1, rect.width(), 2)
        elif position == 'below':
            self.indicator_rect = QRect(rect.left(), rect.bottom() - 1, rect.width(), 2)
        else:  # on
            self.indicator_rect = QRect(rect.left(), rect.top(), rect.width(), rect.height())
        
        self.drop_position = position
        self.visible = True
        self.tree_view.viewport().update()
    
    def hide_indicator(self) -> None:
        """Hide drop indicator."""
        self.visible = False
        self.indicator_rect = QRect()
        self.tree_view.viewport().update()
    
    def paint(self, painter: QPainter) -> None:
        """Paint the drop indicator."""
        if not self.visible or self.indicator_rect.isEmpty():
            return
        
        painter.save()
        
        if self.drop_position in ['above', 'below']:
            # Draw line indicator
            pen = QPen(QColor(0, 120, 215), 2)  # Blue line
            painter.setPen(pen)
            painter.drawLine(
                self.indicator_rect.left(),
                self.indicator_rect.center().y(),
                self.indicator_rect.right(),
                self.indicator_rect.center().y()
            )
        else:  # on
            # Draw highlight rectangle
            brush = QBrush(QColor(0, 120, 215, 50))  # Semi-transparent blue
            pen = QPen(QColor(0, 120, 215), 1)
            painter.setBrush(brush)
            painter.setPen(pen)
            painter.drawRect(self.indicator_rect)
        
        painter.restore()


class DragDropHandler(QObject):
    """Handles drag and drop operations for the tree view."""
    
    # Signals
    elementMoved = pyqtSignal(str, str, int)  # element_id, new_parent_id, insert_index
    elementCopied = pyqtSignal(str, str, int)  # element_id, new_parent_id, insert_index
    dragStarted = pyqtSignal(str)  # element_id
    dragEnded = pyqtSignal()
    
    def __init__(self, tree_view: QTreeView, parent=None):
        super().__init__(parent)
        self.tree_view = tree_view
        self.validator = DragDropValidator()
        self.drop_indicator = DropIndicator(tree_view)
        
        # Drag state
        self.drag_start_position = QPoint()
        self.dragging = False
        self.drag_source_index = None
        
        # Configure tree view for drag and drop
        self._setup_drag_drop()
    
    def _setup_drag_drop(self) -> None:
        """Configure tree view for drag and drop."""
        self.tree_view.setDragEnabled(True)
        self.tree_view.setAcceptDrops(True)
        self.tree_view.setDropIndicatorShown(False)  # We'll draw our own
        self.tree_view.setDragDropMode(QTreeView.DragDropMode.DragDrop)
        self.tree_view.setDefaultDropAction(Qt.DropAction.MoveAction)
    
    def start_drag(self, index) -> None:
        """Start drag operation."""
        if not index.isValid():
            return
        
        model = self.tree_view.model()
        if not model:
            return
        
        # Get element data
        element_id = model.data(index, Qt.ItemDataRole.UserRole)
        if not element_id:
            return
        
        self.drag_source_index = index
        self.dragging = True
        
        # Create drag object
        drag = QDrag(self.tree_view)
        mime_data = QMimeData()
        
        # Set MIME data
        mime_data.setText(element_id)
        mime_data.setData("application/x-element-id", element_id.encode())
        
        # Create drag pixmap
        pixmap = self._create_drag_pixmap(index)
        drag.setPixmap(pixmap)
        drag.setMimeData(mime_data)
        
        # Start drag
        self.dragStarted.emit(element_id)
        drop_action = drag.exec(Qt.DropAction.MoveAction | Qt.DropAction.CopyAction)
        
        # Cleanup
        self.dragging = False
        self.drag_source_index = None
        self.drop_indicator.hide_indicator()
        self.dragEnded.emit()
    
    def _create_drag_pixmap(self, index) -> QPixmap:
        """Create pixmap for drag operation."""
        rect = self.tree_view.visualRect(index)
        pixmap = QPixmap(rect.size())
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setOpacity(0.8)
        
        # Render the item
        option = self.tree_view.viewOptions()
        option.rect = QRect(0, 0, rect.width(), rect.height())
        option.state |= self.tree_view.state()
        
        if self.tree_view.itemDelegate():
            self.tree_view.itemDelegate().paint(painter, option, index)
        
        painter.end()
        return pixmap
    
    def handle_drag_enter(self, event) -> None:
        """Handle drag enter event."""
        if self._is_valid_drag(event):
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def handle_drag_move(self, event) -> None:
        """Handle drag move event."""
        if not self._is_valid_drag(event):
            event.ignore()
            self.drop_indicator.hide_indicator()
            return
        
        # Get drop target
        pos = event.position().toPoint()
        index = self.tree_view.indexAt(pos)
        
        if not index.isValid():
            event.ignore()
            self.drop_indicator.hide_indicator()
            return
        
        # Determine drop position
        drop_position = self._get_drop_position(index, pos)
        
        # Validate drop
        if self._can_drop_at_position(event, index, drop_position):
            event.acceptProposedAction()
            self.drop_indicator.show_indicator(index, drop_position)
        else:
            event.ignore()
            self.drop_indicator.hide_indicator()
    
    def handle_drag_leave(self, event) -> None:
        """Handle drag leave event."""
        self.drop_indicator.hide_indicator()
        event.accept()
    
    def handle_drop(self, event) -> None:
        """Handle drop event."""
        if not self._is_valid_drag(event):
            event.ignore()
            return
        
        # Get drop target
        pos = event.position().toPoint()
        index = self.tree_view.indexAt(pos)
        
        if not index.isValid():
            event.ignore()
            return
        
        # Get dropped data
        element_id = event.mimeData().text()
        if not element_id:
            event.ignore()
            return
        
        # Determine drop position and validate
        drop_position = self._get_drop_position(index, pos)
        if not self._can_drop_at_position(event, index, drop_position):
            event.ignore()
            return
        
        # Perform the drop
        self._perform_drop(element_id, index, drop_position, event.dropAction())
        
        event.acceptProposedAction()
        self.drop_indicator.hide_indicator()
    
    def _is_valid_drag(self, event) -> bool:
        """Check if drag event contains valid data."""
        mime_data = event.mimeData()
        return (mime_data.hasText() or 
                mime_data.hasFormat("application/x-element-id"))
    
    def _get_drop_position(self, index, pos: QPoint) -> str:
        """Determine drop position relative to index."""
        rect = self.tree_view.visualRect(index)
        relative_y = pos.y() - rect.top()
        third = rect.height() // 3
        
        if relative_y < third:
            return 'above'
        elif relative_y > 2 * third:
            return 'below'
        else:
            return 'on'
    
    def _can_drop_at_position(self, event, target_index, drop_position: str) -> bool:
        """Check if drop is valid at specific position."""
        model = self.tree_view.model()
        if not model:
            return False
        
        # Get source and target nodes
        element_id = event.mimeData().text()
        source_node = model.get_node_by_element_id(element_id)
        target_node = model._node_from_index(target_index)
        
        if not source_node or not target_node:
            return False
        
        # Basic validation
        can_drop, _ = self.validator.can_drop_on_target(source_node, target_node)
        if not can_drop:
            return False
        
        # Position-specific validation
        if drop_position in ['above', 'below']:
            # Dropping as sibling - check parent compatibility
            parent = target_node.parent()
            if parent:
                can_drop_on_parent, _ = self.validator.can_drop_on_target(source_node, parent)
                return can_drop_on_parent
        
        return True
    
    def _perform_drop(self, element_id: str, target_index, drop_position: str, action) -> None:
        """Perform the actual drop operation."""
        model = self.tree_view.model()
        if not model:
            return
        
        # Get nodes
        source_node = model.get_node_by_element_id(element_id)
        target_node = model._node_from_index(target_index)
        
        if not source_node or not target_node:
            return
        
        # Get insertion position
        parent_node, insert_index = self.validator.get_insert_position(target_node, drop_position)
        
        # Get parent element ID
        parent_element = parent_node.element() if parent_node else None
        parent_id = parent_element.id if parent_element else ""
        
        # Emit appropriate signal
        if action == Qt.DropAction.CopyAction:
            self.elementCopied.emit(element_id, parent_id, insert_index)
        else:
            self.elementMoved.emit(element_id, parent_id, insert_index)
    
    def paint_drop_indicator(self, painter: QPainter) -> None:
        """Paint drop indicator during drag operations."""
        self.drop_indicator.paint(painter)


class DragDropMimeData:
    """Helper for creating and parsing MIME data."""
    
    ELEMENT_ID_FORMAT = "application/x-element-id"
    ELEMENT_LIST_FORMAT = "application/x-element-list"
    
    @staticmethod
    def create_element_mime_data(element_ids: List[str]) -> QMimeData:
        """Create MIME data for element IDs."""
        mime_data = QMimeData()
        
        # Single element as text
        if len(element_ids) == 1:
            mime_data.setText(element_ids[0])
        
        # Element ID data
        mime_data.setData(DragDropMimeData.ELEMENT_ID_FORMAT, 
                         element_ids[0].encode() if element_ids else b"")
        
        # Multiple elements as list
        if len(element_ids) > 1:
            element_list = "\n".join(element_ids)
            mime_data.setData(DragDropMimeData.ELEMENT_LIST_FORMAT, 
                             element_list.encode())
        
        return mime_data
    
    @staticmethod
    def extract_element_ids(mime_data: QMimeData) -> List[str]:
        """Extract element IDs from MIME data."""
        element_ids = []
        
        # Try single element first
        if mime_data.hasText():
            element_ids.append(mime_data.text())
        elif mime_data.hasFormat(DragDropMimeData.ELEMENT_ID_FORMAT):
            data = mime_data.data(DragDropMimeData.ELEMENT_ID_FORMAT)
            element_id = data.data().decode()
            if element_id:
                element_ids.append(element_id)
        
        # Try multiple elements
        if mime_data.hasFormat(DragDropMimeData.ELEMENT_LIST_FORMAT):
            data = mime_data.data(DragDropMimeData.ELEMENT_LIST_FORMAT)
            element_list = data.data().decode()
            if element_list:
                element_ids = element_list.split('\n')
        
        return [eid for eid in element_ids if eid.strip()]