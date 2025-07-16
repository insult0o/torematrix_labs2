"""
Element Preview Widget for Merge/Split Operations.

This module provides a comprehensive widget for previewing document elements
with support for highlighting changes, metadata display, and visual comparison.
"""

from typing import List, Optional, Dict, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QTextEdit,
    QScrollArea, QFrame, QSplitter, QTabWidget, QTreeWidget, QTreeWidgetItem
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPalette, QTextCharFormat, QTextCursor

from .....core.models import Element, ElementType


class ElementMetadataWidget(QWidget):
    """Widget for displaying element metadata in a structured format."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self._element: Optional[Element] = None
    
    def setup_ui(self):
        """Set up the metadata display UI."""
        layout = QVBoxLayout(self)
        
        # Metadata tree
        self.metadata_tree = QTreeWidget()
        self.metadata_tree.setHeaderLabels(["Property", "Value"])
        self.metadata_tree.setAlternatingRowColors(True)
        self.metadata_tree.setRootIsDecorated(True)
        layout.addWidget(self.metadata_tree)
    
    def set_element(self, element: Element):
        """Set the element and display its metadata."""
        self._element = element
        self.update_metadata_display()
    
    def update_metadata_display(self):
        """Update the metadata tree display."""
        self.metadata_tree.clear()
        
        if not self._element:
            return
        
        # Basic element properties
        basic_item = QTreeWidgetItem(["Basic Properties", ""])
        self.metadata_tree.addTopLevelItem(basic_item)
        
        basic_item.addChild(QTreeWidgetItem(["ID", self._element.element_id]))
        basic_item.addChild(QTreeWidgetItem(["Type", self._element.element_type.value]))
        basic_item.addChild(QTreeWidgetItem(["Text Length", str(len(self._element.text))]))
        if self._element.parent_id:
            basic_item.addChild(QTreeWidgetItem(["Parent ID", self._element.parent_id]))
        
        basic_item.setExpanded(True)
        
        # Extended metadata if available
        if self._element.metadata:
            metadata_item = QTreeWidgetItem(["Extended Metadata", ""])
            self.metadata_tree.addTopLevelItem(metadata_item)
            
            # Add metadata fields (simplified representation)
            metadata_item.addChild(QTreeWidgetItem(["Has Metadata", "Yes"]))
            metadata_item.setExpanded(True)


class ElementTextWidget(QWidget):
    """Widget for displaying element text with highlighting and formatting."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self._element: Optional[Element] = None
        self._highlight_ranges: List[tuple] = []
    
    def setup_ui(self):
        """Set up the text display UI."""
        layout = QVBoxLayout(self)
        
        # Text display
        self.text_display = QTextEdit()
        self.text_display.setReadOnly(True)
        self.text_display.setFont(QFont("Consolas", 10))
        layout.addWidget(self.text_display)
        
        # Character count label
        self.char_count_label = QLabel("Characters: 0")
        self.char_count_label.setStyleSheet("color: #666666; font-size: 10px;")
        layout.addWidget(self.char_count_label)
    
    def set_element(self, element: Element):
        """Set the element and display its text."""
        self._element = element
        self.update_text_display()
    
    def update_text_display(self):
        """Update the text display."""
        if not self._element:
            self.text_display.clear()
            self.char_count_label.setText("Characters: 0")
            return
        
        # Set text
        self.text_display.setPlainText(self._element.text)
        
        # Apply highlighting if any
        self.apply_highlighting()
        
        # Update character count
        self.char_count_label.setText(f"Characters: {len(self._element.text)}")
    
    def set_highlight_ranges(self, ranges: List[tuple]):
        """Set ranges to highlight in the text (start, end) positions."""
        self._highlight_ranges = ranges
        if self._element:
            self.apply_highlighting()
    
    def apply_highlighting(self):
        """Apply highlighting to specified text ranges."""
        if not self._highlight_ranges:
            return
        
        cursor = self.text_display.textCursor()
        
        for start, end in self._highlight_ranges:
            # Create highlight format
            highlight_format = QTextCharFormat()
            highlight_format.setBackground(QColor(255, 255, 0, 100))  # Semi-transparent yellow
            
            # Apply highlighting
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            cursor.setCharFormat(highlight_format)


class ElementComparisonWidget(QWidget):
    """Widget for comparing two elements side by side."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the comparison UI."""
        layout = QVBoxLayout(self)
        
        # Splitter for side-by-side comparison
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)
        
        # Left element
        left_group = QGroupBox("Original")
        left_layout = QVBoxLayout(left_group)
        self.left_element = ElementTextWidget()
        left_layout.addWidget(self.left_element)
        splitter.addWidget(left_group)
        
        # Right element
        right_group = QGroupBox("Modified")
        right_layout = QVBoxLayout(right_group)
        self.right_element = ElementTextWidget()
        right_layout.addWidget(self.right_element)
        splitter.addWidget(right_group)
    
    def set_elements(self, original: Element, modified: Element):
        """Set the elements to compare."""
        self.left_element.set_element(original)
        self.right_element.set_element(modified)


class ElementPreview(QWidget):
    """
    Comprehensive element preview widget with tabbed interface.
    
    Provides multiple views of element data including text content,
    metadata, and comparison capabilities for merge/split operations.
    """
    
    element_selected = pyqtSignal(Element)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self._elements: List[Element] = []
        self._current_element: Optional[Element] = None
    
    def setup_ui(self):
        """Set up the main preview UI."""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        self.title_label = QLabel("Element Preview")
        self.title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        
        self.element_count_label = QLabel("0 elements")
        self.element_count_label.setStyleSheet("color: #666666;")
        header_layout.addWidget(self.element_count_label)
        
        layout.addLayout(header_layout)
        
        # Tab widget for different views
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Text view tab
        self.text_widget = ElementTextWidget()
        self.tab_widget.addTab(self.text_widget, "Text Content")
        
        # Metadata view tab
        self.metadata_widget = ElementMetadataWidget()
        self.tab_widget.addTab(self.metadata_widget, "Metadata")
        
        # Comparison view tab (initially hidden)
        self.comparison_widget = ElementComparisonWidget()
        self.comparison_tab_index = self.tab_widget.addTab(self.comparison_widget, "Comparison")
        self.tab_widget.setTabVisible(self.comparison_tab_index, False)
    
    def set_element(self, element: Element):
        """Set a single element for preview."""
        self._elements = [element] if element else []
        self._current_element = element
        self.update_preview()
    
    def set_elements(self, elements: List[Element]):
        """Set multiple elements for preview."""
        self._elements = elements
        self._current_element = elements[0] if elements else None
        self.update_preview()
    
    def update_preview(self):
        """Update the preview display."""
        # Update header
        count = len(self._elements)
        self.element_count_label.setText(f"{count} element{'s' if count != 1 else ''}")
        
        if count == 0:
            self.title_label.setText("Element Preview - No elements")
            self.clear_preview()
            return
        
        # Update title based on element count
        if count == 1:
            element = self._elements[0]
            self.title_label.setText(f"Element Preview - {element.element_type.value}")
        else:
            self.title_label.setText(f"Element Preview - {count} elements")
        
        # Update current element display
        if self._current_element:
            self.text_widget.set_element(self._current_element)
            self.metadata_widget.set_element(self._current_element)
        
        # Show/hide comparison tab
        show_comparison = count == 2
        self.tab_widget.setTabVisible(self.comparison_tab_index, show_comparison)
        
        if show_comparison:
            self.comparison_widget.set_elements(self._elements[0], self._elements[1])
    
    def clear_preview(self):
        """Clear the preview display."""
        self.text_widget.set_element(None)
        self.metadata_widget.set_element(None)
        self.tab_widget.setTabVisible(self.comparison_tab_index, False)
    
    def set_highlight_ranges(self, ranges: List[tuple]):
        """Set text ranges to highlight in the preview."""
        self.text_widget.set_highlight_ranges(ranges)
    
    def get_current_element(self) -> Optional[Element]:
        """Get the currently displayed element."""
        return self._current_element
    
    def get_elements(self) -> List[Element]:
        """Get all elements in the preview."""
        return self._elements.copy()
    
    def set_preview_mode(self, mode: str):
        """Set the preview mode (text, metadata, comparison)."""
        mode_map = {
            "text": 0,
            "metadata": 1,
            "comparison": self.comparison_tab_index
        }
        
        if mode in mode_map:
            tab_index = mode_map[mode]
            if not self.tab_widget.isTabVisible(tab_index):
                return  # Can't switch to hidden tab
            self.tab_widget.setCurrentIndex(tab_index)
    
    def add_element_indicator(self, element: Element, indicator_type: str, color: QColor = None):
        """Add a visual indicator for an element (e.g., for merge/split operations)."""
        # This could be extended to show visual indicators in the preview
        # For now, it's a placeholder for future enhancement
        pass