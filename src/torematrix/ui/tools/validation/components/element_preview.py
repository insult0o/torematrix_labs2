"""
Element Preview Component for Agent 2 - Issue #235.

This module provides UI components for previewing document elements
with text, metadata, and comparison views.
"""

from typing import List, Optional, Any, Dict
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QTextEdit,
    QLabel, QTreeWidget, QTreeWidgetItem, QFrame, QSplitter,
    QGroupBox, QScrollArea, QPushButton, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPalette

from src.torematrix.core.models import Element, ElementType


class ElementTextWidget(QWidget):
    """Widget for displaying element text content."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self._highlight_ranges = []
        
    def setup_ui(self):
        """Setup the text display UI."""
        layout = QVBoxLayout(self)
        
        # Text display
        self.text_display = QTextEdit()
        self.text_display.setReadOnly(True)
        layout.addWidget(self.text_display)
        
        # Character count
        self.char_count_label = QLabel("Characters: 0")
        self.char_count_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(self.char_count_label)
        
    def set_element(self, element: Optional[Element]):
        """Set the element to display."""
        if element is None:
            self.text_display.setPlainText("")
            self.char_count_label.setText("Characters: 0")
            return
            
        self.text_display.setPlainText(element.text)
        self.char_count_label.setText(f"Characters: {len(element.text)}")
        
    def set_highlight_ranges(self, ranges: List[tuple]):
        """Set text ranges to highlight."""
        self._highlight_ranges = ranges
        # Apply highlighting (simplified implementation)
        # In a full implementation, you would use QTextCharFormat


class ElementMetadataWidget(QWidget):
    """Widget for displaying element metadata."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the metadata display UI."""
        layout = QVBoxLayout(self)
        
        self.metadata_tree = QTreeWidget()
        self.metadata_tree.setHeaderLabels(["Property", "Value"])
        layout.addWidget(self.metadata_tree)
        
    def set_element(self, element: Optional[Element]):
        """Set the element to display metadata for."""
        self.metadata_tree.clear()
        
        if element is None:
            return
            
        # Basic properties
        basic_item = QTreeWidgetItem(["Basic Properties", ""])
        self.metadata_tree.addTopLevelItem(basic_item)
        
        # Add basic properties
        properties = [
            ("ID", element.element_id),
            ("Type", element.element_type.value),
            ("Text Length", str(len(element.text)))
        ]
        
        if element.parent_id:
            properties.append(("Parent ID", element.parent_id))
            
        for prop_name, prop_value in properties:
            prop_item = QTreeWidgetItem([prop_name, str(prop_value)])
            basic_item.addChild(prop_item)
            
        # Expand basic properties
        basic_item.setExpanded(True)


class ElementComparisonWidget(QWidget):
    """Widget for comparing two elements side by side."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the comparison UI."""
        layout = QHBoxLayout(self)
        
        # Left element
        left_group = QGroupBox("Original")
        left_layout = QVBoxLayout(left_group)
        self.left_element = ElementTextWidget()
        left_layout.addWidget(self.left_element)
        layout.addWidget(left_group)
        
        # Right element
        right_group = QGroupBox("Modified")
        right_layout = QVBoxLayout(right_group)
        self.right_element = ElementTextWidget()
        right_layout.addWidget(self.right_element)
        layout.addWidget(right_group)
        
    def set_elements(self, left: Optional[Element], right: Optional[Element]):
        """Set elements for comparison."""
        self.left_element.set_element(left)
        self.right_element.set_element(right)


class ElementPreview(QWidget):
    """Main element preview widget with tabbed interface."""
    
    element_changed = pyqtSignal(Element)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._elements = []
        self._current_element = None
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the preview UI."""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        
        self.title_label = QLabel("Element Preview")
        self.title_label.setFont(QFont("", 12, QFont.Weight.Bold))
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch()
        
        self.element_count_label = QLabel("0 elements")
        header_layout.addWidget(self.element_count_label)
        
        layout.addLayout(header_layout)
        
        # Tab widget
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
        
        # Navigation (for multiple elements)
        nav_layout = QHBoxLayout()
        
        self.prev_button = QPushButton("← Previous")
        self.prev_button.clicked.connect(self.previous_element)
        nav_layout.addWidget(self.prev_button)
        
        self.element_selector = QComboBox()
        self.element_selector.currentIndexChanged.connect(self.on_element_selected)
        nav_layout.addWidget(self.element_selector)
        
        self.next_button = QPushButton("Next →")
        self.next_button.clicked.connect(self.next_element)
        nav_layout.addWidget(self.next_button)
        
        layout.addLayout(nav_layout)
        
        self.update_navigation()
        
    def set_element(self, element: Element):
        """Set a single element to preview."""
        self.set_elements([element])
        
    def set_elements(self, elements: List[Element]):
        """Set multiple elements to preview."""
        self._elements = elements
        self._current_element = elements[0] if elements else None
        
        # Update element count
        count = len(elements)
        self.element_count_label.setText(f"{count} element{'s' if count != 1 else ''}")
        
        # Update title
        if self._current_element:
            self.title_label.setText(f"{self._current_element.element_type.value} Preview")
        else:
            self.title_label.setText("Element Preview")
            
        # Show/hide comparison tab
        show_comparison = len(elements) >= 2
        self.tab_widget.setTabVisible(self.comparison_tab_index, show_comparison)
        
        if show_comparison and len(elements) >= 2:
            self.comparison_widget.set_elements(elements[0], elements[1])
            
        # Update selector
        self.element_selector.clear()
        for i, element in enumerate(elements):
            preview_text = element.text[:30] + "..." if len(element.text) > 30 else element.text
            self.element_selector.addItem(f"{i+1}. {element.element_type.value}: {preview_text}")
            
        # Display current element
        self.display_current_element()
        self.update_navigation()
        
    def display_current_element(self):
        """Display the current element in the widgets."""
        self.text_widget.set_element(self._current_element)
        self.metadata_widget.set_element(self._current_element)
        
        if self._current_element:
            self.element_changed.emit(self._current_element)
            
    def previous_element(self):
        """Navigate to previous element."""
        if not self._elements:
            return
            
        current_index = self._elements.index(self._current_element) if self._current_element else 0
        if current_index > 0:
            self._current_element = self._elements[current_index - 1]
            self.element_selector.setCurrentIndex(current_index - 1)
            self.display_current_element()
            self.update_navigation()
            
    def next_element(self):
        """Navigate to next element."""
        if not self._elements:
            return
            
        current_index = self._elements.index(self._current_element) if self._current_element else 0
        if current_index < len(self._elements) - 1:
            self._current_element = self._elements[current_index + 1]
            self.element_selector.setCurrentIndex(current_index + 1)
            self.display_current_element()
            self.update_navigation()
            
    def on_element_selected(self, index: int):
        """Handle element selection from combo box."""
        if 0 <= index < len(self._elements):
            self._current_element = self._elements[index]
            self.display_current_element()
            self.update_navigation()
            
    def update_navigation(self):
        """Update navigation button states."""
        if not self._elements:
            self.prev_button.setEnabled(False)
            self.next_button.setEnabled(False)
            self.element_selector.setEnabled(False)
            return
            
        current_index = self._elements.index(self._current_element) if self._current_element else 0
        
        self.prev_button.setEnabled(current_index > 0)
        self.next_button.setEnabled(current_index < len(self._elements) - 1)
        self.element_selector.setEnabled(len(self._elements) > 1)
        
    def set_preview_mode(self, mode: str):
        """Set the preview mode (text, metadata, comparison)."""
        if mode == "text":
            self.tab_widget.setCurrentIndex(0)
        elif mode == "metadata":
            self.tab_widget.setCurrentIndex(1)
        elif mode == "comparison" and self.tab_widget.isTabVisible(self.comparison_tab_index):
            self.tab_widget.setCurrentIndex(self.comparison_tab_index)
            
    def get_current_element(self) -> Optional[Element]:
        """Get the currently displayed element."""
        return self._current_element