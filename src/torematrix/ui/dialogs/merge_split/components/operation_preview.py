"""
Operation Preview Component

Agent 2 implementation providing visual preview of merge/split operations
with before/after comparison and interactive feedback.
"""

from typing import List, Union, Optional
import logging

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QSplitter,
    QFrame, QTextEdit, QGroupBox, QTabWidget, QPushButton
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QColor, QPalette

from torematrix.core.models.element import Element
from .element_preview import ElementPreview

logger = logging.getLogger(__name__)


class OperationPreview(QWidget):
    """
    Widget for previewing merge/split operations with before/after comparison.
    
    Agent 2 implementation with:
    - Side-by-side before/after comparison
    - Interactive element selection
    - Operation result visualization
    - Detailed change indicators
    """
    
    # Signals
    element_selected = pyqtSignal(object)
    preview_mode_changed = pyqtSignal(str)
    
    def __init__(self, parent=None):
        """Initialize operation preview widget."""
        super().__init__(parent)
        
        self.logger = logging.getLogger(__name__ + ".OperationPreview")
        self.original_elements: List[Element] = []
        self.result_elements: Union[List[Element], Element] = []
        self.operation_type: str = ""
        self.preview_mode = "side_by_side"
        
        self._setup_ui()
        self._show_empty_state()
    
    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        # Header with controls
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Operation Preview")
        title_font = QFont()
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Preview mode buttons
        self.side_by_side_btn = QPushButton("Side by Side")
        self.side_by_side_btn.setCheckable(True)
        self.side_by_side_btn.setChecked(True)
        self.side_by_side_btn.clicked.connect(lambda: self._set_preview_mode("side_by_side"))
        header_layout.addWidget(self.side_by_side_btn)
        
        self.tabbed_btn = QPushButton("Tabbed")
        self.tabbed_btn.setCheckable(True)
        self.tabbed_btn.clicked.connect(lambda: self._set_preview_mode("tabbed"))
        header_layout.addWidget(self.tabbed_btn)
        
        # Operation info
        self.operation_info_label = QLabel("")
        self.operation_info_label.setStyleSheet("color: #666666; font-size: 10px;")
        header_layout.addWidget(self.operation_info_label)
        
        layout.addLayout(header_layout)
        
        # Main content area - will be populated based on preview mode
        self.content_frame = QFrame()
        layout.addWidget(self.content_frame)
        
        self._setup_side_by_side_mode()
    
    def _setup_side_by_side_mode(self):
        """Set up side-by-side comparison mode."""
        # Clear existing content
        if self.content_frame.layout():
            self._clear_layout(self.content_frame.layout())
        
        # Create splitter layout
        layout = QVBoxLayout(self.content_frame)
        
        # Create splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Before panel
        before_panel = self._create_before_panel()
        splitter.addWidget(before_panel)
        
        # After panel
        after_panel = self._create_after_panel()
        splitter.addWidget(after_panel)
        
        # Set equal sizes
        splitter.setSizes([50, 50])
        
        layout.addWidget(splitter)
    
    def _setup_tabbed_mode(self):
        """Set up tabbed comparison mode."""
        # Clear existing content
        if self.content_frame.layout():
            self._clear_layout(self.content_frame.layout())
        
        # Create tabbed layout
        layout = QVBoxLayout(self.content_frame)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Before tab
        before_panel = self._create_before_panel()
        self.tab_widget.addTab(before_panel, "Before")
        
        # After tab
        after_panel = self._create_after_panel()
        self.tab_widget.addTab(after_panel, "After")
        
        layout.addWidget(self.tab_widget)
    
    def _create_before_panel(self) -> QWidget:
        """Create the 'before' panel showing original elements."""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(panel)
        
        # Header
        header = QLabel("Before Operation")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_font = QFont()
        header_font.setBold(True)
        header.setFont(header_font)
        header.setStyleSheet("background-color: #f0f8ff; padding: 5px; border-radius: 3px;")
        layout.addWidget(header)
        
        # Element preview
        self.before_preview = ElementPreview()
        self.before_preview.element_clicked.connect(self.element_selected)
        layout.addWidget(self.before_preview)
        
        # Stats
        self.before_stats_label = QLabel("No elements")\n        self.before_stats_label.setStyleSheet("color: #666666; font-size: 10px; text-align: center;")
        layout.addWidget(self.before_stats_label)
        
        return panel
    
    def _create_after_panel(self) -> QWidget:
        """Create the 'after' panel showing result elements."""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(panel)
        
        # Header
        header = QLabel("After Operation")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_font = QFont()
        header_font.setBold(True)
        header.setFont(header_font)
        header.setStyleSheet("background-color: #f0fff0; padding: 5px; border-radius: 3px;")
        layout.addWidget(header)
        
        # Element preview
        self.after_preview = ElementPreview()
        self.after_preview.element_clicked.connect(self.element_selected)
        layout.addWidget(self.after_preview)
        
        # Stats
        self.after_stats_label = QLabel("No elements")
        self.after_stats_label.setStyleSheet("color: #666666; font-size: 10px; text-align: center;")
        layout.addWidget(self.after_stats_label)
        
        return panel
    
    def _clear_layout(self, layout):
        """Clear all widgets from a layout."""
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
    
    def _set_preview_mode(self, mode: str):
        """Set the preview mode."""
        self.preview_mode = mode
        
        # Update button states
        self.side_by_side_btn.setChecked(mode == "side_by_side")
        self.tabbed_btn.setChecked(mode == "tabbed")
        
        # Rebuild UI for new mode
        if mode == "side_by_side":
            self._setup_side_by_side_mode()
        elif mode == "tabbed":
            self._setup_tabbed_mode()
        
        # Update content
        self._update_preview_content()
        
        # Emit signal
        self.preview_mode_changed.emit(mode)
    
    def set_preview(self, original_elements: List[Element], 
                   result_element: Union[List[Element], Element], 
                   operation_type: str):
        """Set preview content for operation."""
        self.original_elements = original_elements
        self.result_elements = result_element
        self.operation_type = operation_type
        
        self._update_preview_content()
        self._update_operation_info()
    
    def _update_preview_content(self):
        """Update the preview content."""
        # Update before preview
        if hasattr(self, 'before_preview'):
            self.before_preview.set_elements(self.original_elements)
            self._update_before_stats()
        
        # Update after preview
        if hasattr(self, 'after_preview'):
            # Handle both single element and list of elements
            if isinstance(self.result_elements, list):
                self.after_preview.set_elements(self.result_elements)
            else:
                self.after_preview.set_elements([self.result_elements] if self.result_elements else [])
            self._update_after_stats()
    
    def _update_before_stats(self):
        """Update before operation statistics."""
        if not hasattr(self, 'before_stats_label'):
            return
        
        count = len(self.original_elements)
        if count == 0:
            self.before_stats_label.setText("No elements")
        elif count == 1:
            element = self.original_elements[0]
            char_count = len(element.text) if element.text else 0
            self.before_stats_label.setText(f"1 element, {char_count} characters")
        else:
            total_chars = sum(len(e.text) if e.text else 0 for e in self.original_elements)
            self.before_stats_label.setText(f"{count} elements, {total_chars} characters")
    
    def _update_after_stats(self):
        """Update after operation statistics."""
        if not hasattr(self, 'after_stats_label'):
            return
        
        # Get result elements as list
        if isinstance(self.result_elements, list):
            result_list = self.result_elements
        else:
            result_list = [self.result_elements] if self.result_elements else []
        
        count = len(result_list)
        if count == 0:
            self.after_stats_label.setText("No elements")
        elif count == 1:
            element = result_list[0]
            char_count = len(element.text) if element.text else 0
            self.after_stats_label.setText(f"1 element, {char_count} characters")
        else:
            total_chars = sum(len(e.text) if e.text else 0 for e in result_list)
            self.after_stats_label.setText(f"{count} elements, {total_chars} characters")
    
    def _update_operation_info(self):
        """Update operation information display."""
        if not self.operation_type:
            self.operation_info_label.setText("")
            return
        
        # Create info text based on operation type
        if self.operation_type == "merge":
            info_text = f"Merge: {len(self.original_elements)} → 1 element"
        elif self.operation_type == "split":
            if isinstance(self.result_elements, list):
                result_count = len(self.result_elements)
            else:
                result_count = 1 if self.result_elements else 0
            info_text = f"Split: 1 → {result_count} elements"
        else:
            info_text = f"Operation: {self.operation_type}"
        
        self.operation_info_label.setText(info_text)
    
    def clear_preview(self):
        """Clear the preview display."""
        self.original_elements = []
        self.result_elements = []
        self.operation_type = ""
        
        self._show_empty_state()
    
    def _show_empty_state(self):
        """Show empty state when no preview is available."""
        if hasattr(self, 'before_preview'):
            self.before_preview.clear_preview()
        if hasattr(self, 'after_preview'):
            self.after_preview.clear_preview()
        
        self.operation_info_label.setText("No operation preview")
        
        if hasattr(self, 'before_stats_label'):
            self.before_stats_label.setText("No elements")
        if hasattr(self, 'after_stats_label'):
            self.after_stats_label.setText("No elements")
    
    def get_preview_mode(self) -> str:
        """Get current preview mode."""
        return self.preview_mode
    
    def set_show_coordinates(self, show: bool):
        """Set whether to show coordinates in previews."""
        if hasattr(self, 'before_preview'):
            self.before_preview.set_show_coordinates(show)
        if hasattr(self, 'after_preview'):
            self.after_preview.set_show_coordinates(show)
    
    def set_show_metadata(self, show: bool):
        """Set whether to show metadata in previews."""
        if hasattr(self, 'before_preview'):
            self.before_preview.set_show_metadata(show)
        if hasattr(self, 'after_preview'):
            self.after_preview.set_show_metadata(show)
    
    def sizeHint(self) -> QSize:
        """Provide size hint for the widget."""
        return QSize(600, 400)