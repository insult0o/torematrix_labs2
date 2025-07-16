"""
Element Preview Component.

This module provides comprehensive element preview functionality with
text display, metadata viewing, and comparison capabilities.
"""

from typing import List, Optional, Dict, Any, Tuple
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QTextEdit,
    QLabel, QTreeWidget, QTreeWidgetItem, QSplitter, QGroupBox,
    QScrollArea, QFrame, QPushButton, QSpinBox, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QTextCharFormat, QColor, QTextCursor

from .....core.models import Element, ElementType


class ElementTextWidget(QWidget):
    """Widget for displaying element text content with highlighting."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self._highlight_ranges: List[Tuple[int, int]] = []
    
    def setup_ui(self):
        """Set up the text widget UI."""
        layout = QVBoxLayout(self)
        
        # Text display
        self.text_display = QTextEdit()
        self.text_display.setReadOnly(True)
        self.text_display.setFont(QFont("Consolas", 10))
        layout.addWidget(self.text_display)
        
        # Character count
        self.char_count_label = QLabel("Characters: 0")
        self.char_count_label.setStyleSheet("color: #666666; font-size: 12px;")
        layout.addWidget(self.char_count_label)
    
    def set_element(self, element: Optional[Element]):
        """Set the element to display."""
        if element is None:
            self.text_display.clear()
            self.char_count_label.setText("Characters: 0")
            return
        
        self.text_display.setPlainText(element.text)
        self.char_count_label.setText(f"Characters: {len(element.text)}")
    
    def set_highlight_ranges(self, ranges: List[Tuple[int, int]]):
        """Set text ranges to highlight."""
        self._highlight_ranges = ranges
        self._apply_highlighting()
    
    def _apply_highlighting(self):
        """Apply highlighting to specified ranges."""
        if not self._highlight_ranges:
            return
        
        cursor = self.text_display.textCursor()
        highlight_format = QTextCharFormat()
        highlight_format.setBackground(QColor("#ffeb3b"))
        
        for start, end in self._highlight_ranges:
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            cursor.setCharFormat(highlight_format)


class ElementMetadataWidget(QWidget):
    """Widget for displaying element metadata in a tree structure."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the metadata widget UI."""
        layout = QVBoxLayout(self)
        
        self.metadata_tree = QTreeWidget()
        self.metadata_tree.setHeaderLabels(["Property", "Value"])
        self.metadata_tree.setAlternatingRowColors(True)
        layout.addWidget(self.metadata_tree)
    
    def set_element(self, element: Optional[Element]):
        """Set the element to display metadata for."""
        self.metadata_tree.clear()
        
        if element is None:
            return
        
        # Basic properties
        basic_item = QTreeWidgetItem(["Basic Properties", ""])
        self.metadata_tree.addTopLevelItem(basic_item)
        
        self._add_property(basic_item, "ID", element.element_id)
        self._add_property(basic_item, "Type", element.element_type.value)
        self._add_property(basic_item, "Text Length", str(len(element.text)))
        
        if element.parent_id:
            self._add_property(basic_item, "Parent ID", element.parent_id)
        
        # Position properties
        if element.bbox or element.page_number is not None:
            position_item = QTreeWidgetItem(["Position", ""])
            self.metadata_tree.addTopLevelItem(position_item)
            
            if element.page_number is not None:
                self._add_property(position_item, "Page", str(element.page_number))
            
            if element.bbox:
                bbox_str = f"({element.bbox[0]}, {element.bbox[1]}, {element.bbox[2]}, {element.bbox[3]})"
                self._add_property(position_item, "Bounding Box", bbox_str)
        
        # Expand all items
        self.metadata_tree.expandAll()
        self.metadata_tree.resizeColumnToContents(0)
    
    def _add_property(self, parent: QTreeWidgetItem, name: str, value: str):
        """Add a property to the metadata tree."""
        item = QTreeWidgetItem([name, value])
        parent.addChild(item)


class ElementComparisonWidget(QWidget):
    """Widget for comparing two elements side by side."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the comparison widget UI."""
        layout = QHBoxLayout(self)
        
        # Left element (original)
        left_group = QGroupBox("Original")
        left_layout = QVBoxLayout(left_group)
        self.left_element = ElementTextWidget()
        left_layout.addWidget(self.left_element)
        layout.addWidget(left_group)
        
        # Right element (modified)
        right_group = QGroupBox("Modified")
        right_layout = QVBoxLayout(right_group)
        self.right_element = ElementTextWidget()
        right_layout.addWidget(self.right_element)
        layout.addWidget(right_group)
    
    def set_elements(self, original: Optional[Element], modified: Optional[Element]):
        """Set the elements to compare."""
        self.left_element.set_element(original)
        self.right_element.set_element(modified)


class ElementPreview(QWidget):
    """
    Main element preview widget with tabbed interface.
    
    Provides text view, metadata view, and comparison view for elements.
    """
    
    element_changed = pyqtSignal(Element)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._elements: List[Element] = []
        self._current_element: Optional[Element] = None
        self._current_index: int = 0
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the main preview widget UI."""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        
        self.title_label = QLabel("Element Preview")
        self.title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch()
        
        self.element_count_label = QLabel("0 elements")
        self.element_count_label.setStyleSheet("color: #666666;")
        header_layout.addWidget(self.element_count_label)
        
        layout.addLayout(header_layout)
        
        # Navigation for multiple elements
        nav_layout = QHBoxLayout()
        
        self.prev_button = QPushButton("← Previous")
        self.prev_button.setEnabled(False)
        nav_layout.addWidget(self.prev_button)
        
        self.element_index_label = QLabel("Element 1 of 1")
        nav_layout.addWidget(self.element_index_label)
        
        self.next_button = QPushButton("Next →")
        self.next_button.setEnabled(False)
        nav_layout.addWidget(self.next_button)
        
        nav_layout.addStretch()
        layout.addLayout(nav_layout)
        
        # Tab widget for different views
        self.tab_widget = QTabWidget()
        
        # Text tab
        self.text_widget = ElementTextWidget()
        self.tab_widget.addTab(self.text_widget, "Text")
        
        # Metadata tab
        self.metadata_widget = ElementMetadataWidget()
        self.tab_widget.addTab(self.metadata_widget, "Metadata")
        
        # Comparison tab (initially hidden)
        self.comparison_widget = ElementComparisonWidget()
        self.comparison_tab_index = self.tab_widget.addTab(self.comparison_widget, "Comparison")
        self.tab_widget.setTabVisible(self.comparison_tab_index, False)
        
        layout.addWidget(self.tab_widget)
        
        # Connect signals
        self.prev_button.clicked.connect(self.show_previous_element)
        self.next_button.clicked.connect(self.show_next_element)
    
    def set_element(self, element: Optional[Element]):
        """Set a single element to preview."""
        if element is None:
            self.set_elements([])
        else:
            self.set_elements([element])
    
    def set_elements(self, elements: List[Element]):
        """Set multiple elements to preview."""
        self._elements = elements
        self._current_index = 0
        
        if elements:
            self._current_element = elements[0]
            self.element_count_label.setText(f"{len(elements)} element{'s' if len(elements) != 1 else ''}")
        else:
            self._current_element = None
            self.element_count_label.setText("0 elements")
        
        self._update_display()
        self._update_navigation()
        self._update_comparison_tab_visibility()
    
    def show_previous_element(self):
        """Show the previous element in the list."""
        if self._current_index > 0:
            self._current_index -= 1
            self._current_element = self._elements[self._current_index]
            self._update_display()
            self._update_navigation()
    
    def show_next_element(self):
        """Show the next element in the list."""
        if self._current_index < len(self._elements) - 1:
            self._current_index += 1
            self._current_element = self._elements[self._current_index]
            self._update_display()
            self._update_navigation()
    
    def set_preview_mode(self, mode: str):
        """Set the preview mode (text, metadata, comparison)."""
        mode_map = {
            "text": 0,
            "metadata": 1,
            "comparison": 2
        }
        
        if mode in mode_map:
            self.tab_widget.setCurrentIndex(mode_map[mode])
    
    def _update_display(self):
        """Update the display with current element."""
        if self._current_element:
            # Update title
            self.title_label.setText(f"{self._current_element.element_type.value} Preview")
            
            # Update text and metadata widgets
            self.text_widget.set_element(self._current_element)
            self.metadata_widget.set_element(self._current_element)
            
            # Emit signal
            self.element_changed.emit(self._current_element)
        else:
            self.title_label.setText("Element Preview")
            self.text_widget.set_element(None)
            self.metadata_widget.set_element(None)
    
    def _update_navigation(self):
        """Update navigation button states."""
        has_elements = len(self._elements) > 0
        has_multiple = len(self._elements) > 1
        
        self.prev_button.setEnabled(has_multiple and self._current_index > 0)
        self.next_button.setEnabled(has_multiple and self._current_index < len(self._elements) - 1)
        
        if has_elements:
            self.element_index_label.setText(
                f"Element {self._current_index + 1} of {len(self._elements)}"
            )
        else:
            self.element_index_label.setText("No elements")
    
    def _update_comparison_tab_visibility(self):
        """Update visibility of comparison tab based on element count."""
        show_comparison = len(self._elements) >= 2
        self.tab_widget.setTabVisible(self.comparison_tab_index, show_comparison)
        
        if show_comparison and len(self._elements) >= 2:
            # Set up comparison with first two elements
            self.comparison_widget.set_elements(self._elements[0], self._elements[1])
    
    def get_current_element(self) -> Optional[Element]:
        """Get the currently displayed element."""
        return self._current_element
    
    def get_elements(self) -> List[Element]:
        """Get all elements in the preview."""
        return self._elements.copy()