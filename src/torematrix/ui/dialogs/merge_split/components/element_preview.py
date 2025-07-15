"""
Element Preview Component

Agent 2 implementation providing visual preview of document elements
with formatting, coordinates, and metadata display.
"""

from typing import List, Optional, Dict, Any
import logging

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, 
    QFrame, QTextEdit, QGroupBox, QTreeWidget, QTreeWidgetItem
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QPixmap, QPainter, QColor, QBrush, QPen

from torematrix.core.models.element import Element, ElementType

logger = logging.getLogger(__name__)


class ElementPreview(QWidget):
    """
    Widget for previewing document elements with visual representation.
    
    Agent 2 implementation with:
    - Visual element rendering
    - Coordinate visualization
    - Metadata display
    - Formatting preservation
    """
    
    # Signals
    element_clicked = pyqtSignal(object)
    element_double_clicked = pyqtSignal(object)
    
    def __init__(self, parent=None):
        """Initialize element preview widget."""
        super().__init__(parent)
        
        self.logger = logging.getLogger(__name__ + ".ElementPreview")
        self.elements: List[Element] = []
        self.selected_element: Optional[Element] = None
        self.show_coordinates = True
        self.show_metadata = True
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Element Preview")
        title_font = QFont()
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Info label
        self.info_label = QLabel("No elements")
        self.info_label.setStyleSheet("color: #666666; font-size: 10px;")
        header_layout.addWidget(self.info_label)
        
        layout.addLayout(header_layout)
        
        # Main content area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setMinimumHeight(200)
        
        # Content widget
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.scroll_area.setWidget(self.content_widget)
        layout.addWidget(self.scroll_area)
        
        # Initial state
        self._show_empty_state()
    
    def set_elements(self, elements: List[Element]):
        """Set elements to preview."""
        self.elements = elements
        self.selected_element = None
        self._update_preview()
    
    def set_element(self, element: Element):
        """Set single element to preview."""
        self.set_elements([element] if element else [])
    
    def clear_preview(self):
        """Clear the preview display."""
        self.elements = []
        self.selected_element = None
        self._show_empty_state()
    
    def set_show_coordinates(self, show: bool):
        """Set whether to show coordinate information."""
        self.show_coordinates = show
        self._update_preview()
    
    def set_show_metadata(self, show: bool):
        """Set whether to show metadata information."""
        self.show_metadata = show
        self._update_preview()
    
    def _update_preview(self):
        """Update the preview display."""
        # Clear existing content
        self._clear_content()
        
        if not self.elements:
            self._show_empty_state()
            return
        
        # Update info label
        self.info_label.setText(f"{len(self.elements)} element(s)")
        
        # Create preview for each element
        for i, element in enumerate(self.elements):
            element_widget = self._create_element_widget(element, i)
            self.content_layout.addWidget(element_widget)
    
    def _clear_content(self):
        """Clear all content widgets."""
        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
    
    def _show_empty_state(self):
        """Show empty state message."""
        self._clear_content()
        self.info_label.setText("No elements")
        
        empty_label = QLabel("No elements to preview")
        empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_label.setStyleSheet("color: #999999; font-size: 12px; padding: 20px;")
        self.content_layout.addWidget(empty_label)
    
    def _create_element_widget(self, element: Element, index: int) -> QWidget:
        """Create preview widget for a single element."""
        # Main frame
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.Box)
        frame.setLineWidth(1)
        frame.setStyleSheet("""
            QFrame {
                border: 1px solid #cccccc;
                border-radius: 4px;
                margin: 2px;
                padding: 4px;
            }
            QFrame:hover {
                border-color: #0078d4;
            }
        """)
        
        layout = QVBoxLayout(frame)
        
        # Header with element info
        header_layout = QHBoxLayout()
        
        # Element type and index
        type_label = QLabel(f"Element {index + 1}: {element.type.value}")
        type_font = QFont()
        type_font.setBold(True)
        type_label.setFont(type_font)
        header_layout.addWidget(type_label)
        
        header_layout.addStretch()
        
        # Element ID
        if element.id:
            id_label = QLabel(f"ID: {element.id}")
            id_label.setStyleSheet("color: #666666; font-size: 10px;")
            header_layout.addWidget(id_label)
        
        layout.addLayout(header_layout)
        
        # Element content preview
        content_preview = self._create_content_preview(element)
        layout.addWidget(content_preview)
        
        # Coordinates (if enabled)
        if self.show_coordinates and element.coordinates:
            coords_widget = self._create_coordinates_widget(element)
            layout.addWidget(coords_widget)
        
        # Metadata (if enabled)
        if self.show_metadata and element.metadata:
            metadata_widget = self._create_metadata_widget(element)
            layout.addWidget(metadata_widget)
        
        # Make clickable
        frame.mousePressEvent = lambda event: self._on_element_clicked(element, event)
        
        return frame
    
    def _create_content_preview(self, element: Element) -> QWidget:
        """Create content preview widget."""
        content_frame = QFrame()
        content_layout = QVBoxLayout(content_frame)
        
        # Text content
        if element.text:
            text_edit = QTextEdit()
            text_edit.setPlainText(element.text)
            text_edit.setReadOnly(True)
            text_edit.setMaximumHeight(100)
            
            # Style based on element type
            if element.type == ElementType.HEADING:
                text_edit.setStyleSheet("font-weight: bold; font-size: 14px;")
            elif element.type == ElementType.CODE:
                text_edit.setStyleSheet("font-family: Consolas; background-color: #f5f5f5;")
            elif element.type == ElementType.TABLE:
                text_edit.setStyleSheet("font-family: monospace; background-color: #fafafa;")
            
            content_layout.addWidget(text_edit)
        
        # Additional type-specific content
        if element.type == ElementType.IMAGE:
            # Image preview placeholder
            image_label = QLabel("📷 Image Element")
            image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            image_label.setStyleSheet("color: #666666; padding: 10px; border: 1px dashed #cccccc;")
            content_layout.addWidget(image_label)
        
        elif element.type == ElementType.TABLE:
            # Table structure info
            if element.metadata and 'table_structure' in element.metadata:
                table_info = element.metadata['table_structure']
                info_text = f"Table: {table_info.get('rows', 'N/A')} rows × {table_info.get('columns', 'N/A')} columns"
                info_label = QLabel(info_text)
                info_label.setStyleSheet("color: #666666; font-size: 10px;")
                content_layout.addWidget(info_label)
        
        elif element.type == ElementType.LIST:
            # List info
            if element.metadata and 'list_structure' in element.metadata:
                list_info = element.metadata['list_structure']
                info_text = f"List: {list_info.get('items', 'N/A')} items ({list_info.get('type', 'unordered')})"
                info_label = QLabel(info_text)
                info_label.setStyleSheet("color: #666666; font-size: 10px;")
                content_layout.addWidget(info_label)
        
        return content_frame
    
    def _create_coordinates_widget(self, element: Element) -> QWidget:
        """Create coordinates display widget."""
        coords_group = QGroupBox("Coordinates")
        coords_layout = QVBoxLayout(coords_group)
        
        coords = element.coordinates
        
        # Position info
        pos_text = f"Position: ({coords.x}, {coords.y})"
        pos_label = QLabel(pos_text)
        coords_layout.addWidget(pos_label)
        
        # Size info
        size_text = f"Size: {coords.width} × {coords.height}"
        size_label = QLabel(size_text)
        coords_layout.addWidget(size_label)
        
        # Page info
        if coords.page_number:
            page_text = f"Page: {coords.page_number}"
            page_label = QLabel(page_text)
            coords_layout.addWidget(page_label)
        
        # Style for coordinate info
        coords_group.setStyleSheet("""
            QGroupBox {
                font-size: 10px;
                margin-top: 5px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        return coords_group
    
    def _create_metadata_widget(self, element: Element) -> QWidget:
        """Create metadata display widget."""
        metadata_group = QGroupBox("Metadata")
        metadata_layout = QVBoxLayout(metadata_group)
        
        # Create tree widget for metadata
        metadata_tree = QTreeWidget()
        metadata_tree.setHeaderHidden(True)
        metadata_tree.setMaximumHeight(80)
        
        # Populate metadata tree
        for key, value in element.metadata.items():
            item = QTreeWidgetItem([f"{key}: {value}"])
            metadata_tree.addTopLevelItem(item)
        
        metadata_layout.addWidget(metadata_tree)
        
        # Style for metadata info
        metadata_group.setStyleSheet("""
            QGroupBox {
                font-size: 10px;
                margin-top: 5px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        return metadata_group
    
    def _on_element_clicked(self, element: Element, event):
        """Handle element click."""
        self.selected_element = element
        self.element_clicked.emit(element)
        
        # Handle double click
        if event.type() == event.Type.MouseButtonDblClick:
            self.element_double_clicked.emit(element)
    
    def get_selected_element(self) -> Optional[Element]:
        """Get the currently selected element."""
        return self.selected_element
    
    def sizeHint(self) -> QSize:
        """Provide size hint for the widget."""
        return QSize(300, 200)