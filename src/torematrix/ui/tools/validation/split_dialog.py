"""
Split Dialog Component for Agent 2 - Issue #235.

This module provides the SplitDialog component for splitting document elements
with interactive text editing, split point selection, and split preview.
"""

from typing import List, Dict, Optional, Any, Tuple
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QSplitter,
    QListWidget, QListWidgetItem, QPushButton, QLabel, QComboBox,
    QLineEdit, QCheckBox, QTextEdit, QGroupBox, QProgressBar,
    QFrame, QSpacerItem, QSizePolicy, QTabWidget, QWidget,
    QMessageBox, QInputDialog, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPoint
from PyQt6.QtGui import (
    QFont, QColor, QPalette, QTextCursor, QTextCharFormat,
    QSyntaxHighlighter, QTextDocument, QMouseEvent, QAction
)

from src.torematrix.core.models import Element, ElementType
from .components import ElementPreview, MetadataConflictResolver, OperationPreview, ValidationWarnings
from .resources import get_icon, IconType, merge_split_styles


class SplitPointHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for split points in text."""
    
    def __init__(self, document: QTextDocument):
        super().__init__(document)
        self.split_positions = []
        self.split_format = QTextCharFormat()
        self.split_format.setBackground(QColor(255, 255, 0, 100))  # Yellow highlight
        self.split_format.setProperty(QTextCharFormat.Property.FullWidthSelection, True)
        
    def set_split_positions(self, positions: List[int]):
        """Set the split positions to highlight."""
        self.split_positions = sorted(positions)
        self.rehighlight()
        
    def highlightBlock(self, text: str):
        """Highlight split points in the text block."""
        block_start = self.currentBlock().position()
        block_length = len(text)
        
        for position in self.split_positions:
            if block_start <= position < block_start + block_length:
                relative_pos = position - block_start
                # Highlight the character at the split position
                self.setFormat(relative_pos, 1, self.split_format)


class InteractiveSplitTextEdit(QTextEdit):
    """Text editor with interactive split point selection."""
    
    # Signals
    split_point_added = pyqtSignal(int)  # position
    split_point_removed = pyqtSignal(int)  # position
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.split_positions = []
        self.highlighter = SplitPointHighlighter(self.document())
        
        # Setup context menu
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press events for split point selection."""
        if (event.button() == Qt.MouseButton.LeftButton and 
            event.modifiers() == Qt.KeyboardModifier.ControlModifier):
            
            # Get cursor position at click
            cursor = self.cursorForPosition(event.pos())
            position = cursor.position()
            
            if position in self.split_positions:
                self.remove_split_point(position)
            else:
                self.add_split_point(position)
        else:
            super().mousePressEvent(event)
            
    def show_context_menu(self, position: QPoint):
        """Show context menu with split point options."""
        cursor = self.cursorForPosition(position)
        cursor_position = cursor.position()
        
        menu = QMenu(self)
        
        if cursor_position in self.split_positions:
            remove_action = QAction("Remove Split Point", self)
            remove_action.triggered.connect(lambda: self.remove_split_point(cursor_position))
            menu.addAction(remove_action)
        else:
            add_action = QAction("Add Split Point", self)
            add_action.triggered.connect(lambda: self.add_split_point(cursor_position))
            menu.addAction(add_action)
            
        menu.addSeparator()
        
        clear_action = QAction("Clear All Split Points", self)
        clear_action.triggered.connect(self.clear_split_points)
        menu.addAction(clear_action)
        
        menu.exec(self.mapToGlobal(position))
        
    def add_split_point(self, position: int):
        """Add a split point at the given position."""
        # Don't add split at position 0 or if already exists
        if position <= 0 or position in self.split_positions:
            return
            
        # Don't add split at the very end
        if position >= len(self.toPlainText()):
            return
            
        self.split_positions.append(position)
        self.split_positions.sort()
        self.highlighter.set_split_positions(self.split_positions)
        self.split_point_added.emit(position)
        
    def remove_split_point(self, position: int):
        """Remove a split point at the given position."""
        if position in self.split_positions:
            self.split_positions.remove(position)
            self.highlighter.set_split_positions(self.split_positions)
            self.split_point_removed.emit(position)
            
    def clear_split_points(self):
        """Clear all split points."""
        self.split_positions.clear()
        self.highlighter.set_split_positions(self.split_positions)
        
    def get_split_positions(self) -> List[int]:
        """Get all split positions sorted."""
        return sorted(self.split_positions)
        
    def set_split_positions(self, positions: List[int]):
        """Set split positions programmatically."""
        self.split_positions = sorted([pos for pos in positions if pos > 0])
        self.highlighter.set_split_positions(self.split_positions)
        
    def get_split_segments(self) -> List[str]:
        """Get text segments based on split positions."""
        text = self.toPlainText()
        if not self.split_positions:
            return [text]
            
        segments = []
        positions = [0] + sorted(self.split_positions) + [len(text)]
        
        for i in range(len(positions) - 1):
            start = positions[i]
            end = positions[i + 1]
            segment = text[start:end]
            segments.append(segment)
            
        return segments


class SplitPreviewWidget(QWidget):
    """Widget for previewing split results."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.original_element = None
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the preview widget UI."""
        layout = QVBoxLayout(self)
        
        # Original element info
        original_group = QGroupBox("Original Element")
        original_layout = QVBoxLayout(original_group)
        
        self.original_info = QLabel("No element selected")
        original_layout.addWidget(self.original_info)
        
        layout.addWidget(original_group)
        
        # Split options
        options_group = QGroupBox("Split Options")
        options_layout = QGridLayout(options_group)
        
        # Element type for segments
        options_layout.addWidget(QLabel("Segment Type:"), 0, 0)
        self.element_type_combo = QComboBox()
        for element_type in ElementType:
            self.element_type_combo.addItem(element_type.value)
        options_layout.addWidget(self.element_type_combo, 0, 1)
        
        # Options checkboxes
        self.preserve_metadata = QCheckBox("Preserve metadata in segments")
        self.preserve_metadata.setChecked(True)
        options_layout.addWidget(self.preserve_metadata, 1, 0, 1, 2)
        
        self.auto_trim = QCheckBox("Auto-trim whitespace")
        self.auto_trim.setChecked(True)
        options_layout.addWidget(self.auto_trim, 2, 0, 1, 2)
        
        layout.addWidget(options_group)
        
        # Split results
        results_group = QGroupBox("Split Results")
        results_layout = QVBoxLayout(results_group)
        
        self.result_list = QListWidget()
        results_layout.addWidget(self.result_list)
        
        self.result_count_label = QLabel("0 segments")
        results_layout.addWidget(self.result_count_label)
        
        layout.addWidget(results_group)
        
    def set_original_element(self, element: Element):
        """Set the original element being split."""
        self.original_element = element
        
        # Update info display
        info_text = (f"Type: {element.element_type.value}\n"
                    f"ID: {element.element_id}\n"
                    f"Length: {len(element.text)} characters")
        self.original_info.setText(info_text)
        
        # Set element type combo to match original
        for i in range(self.element_type_combo.count()):
            if self.element_type_combo.itemText(i) == element.element_type.value:
                self.element_type_combo.setCurrentIndex(i)
                break
                
    def set_split_segments(self, segments: List[str]):
        """Set the split segments to display."""
        self.result_list.clear()
        
        for i, segment in enumerate(segments):
            if self.auto_trim.isChecked():
                segment = segment.strip()
                
            if segment:  # Only add non-empty segments
                item = QListWidgetItem()
                preview_text = segment[:50] + "..." if len(segment) > 50 else segment
                item.setText(f"Segment {i+1}: {preview_text}")
                item.setToolTip(segment)
                self.result_list.addItem(item)
                
        # Update count
        valid_segments = len([s for s in segments if s.strip()]) if self.auto_trim.isChecked() else len(segments)
        self.result_count_label.setText(f"{valid_segments} segment{'s' if valid_segments != 1 else ''}")
        
    def get_resulting_elements(self) -> List[Element]:
        """Get the resulting elements from the split."""
        if not self.original_element:
            return []
            
        segments = []
        for i in range(self.result_list.count()):
            item = self.result_list.item(i)
            segment_text = item.toolTip()
            
            if self.auto_trim.isChecked():
                segment_text = segment_text.strip()
                
            if segment_text:  # Only create elements for non-empty segments
                # Create new element based on original
                element = Element(
                    element_type=ElementType(self.element_type_combo.currentText()),
                    text=segment_text,
                    parent_id=self.original_element.element_id if self.preserve_metadata.isChecked() else None
                )
                segments.append(element)
                
        return segments
        
    def get_split_options(self) -> Dict[str, Any]:
        """Get current split options."""
        return {
            "element_type": self.element_type_combo.currentText(),
            "preserve_metadata": self.preserve_metadata.isChecked(),
            "auto_trim": self.auto_trim.isChecked()
        }


class SplitDialog(QDialog):
    """Dialog for splitting document elements."""
    
    # Signals
    split_requested = pyqtSignal(Element, list, dict)  # element, positions, options
    preview_requested = pyqtSignal(Element, list, dict)  # element, positions, options
    
    def __init__(self, element: Element, parent=None):
        super().__init__(parent)
        self.original_element = element
        self.split_positions = []
        
        self.setup_ui()
        self.setup_connections()
        self.load_element()
        self.update_button_states()
        
    def setup_ui(self):
        """Setup the user interface."""
        self.setWindowTitle(f"Split {self.original_element.element_type.value} Element")
        self.setModal(True)
        self.resize(1200, 800)
        
        # Apply styles
        self.setStyleSheet(merge_split_styles)
        
        # Main layout
        layout = QVBoxLayout(self)
        
        # Title and element info
        title_layout = QHBoxLayout()
        title_label = QLabel(f"Split {self.original_element.element_type.value} Element")
        title_label.setFont(QFont("", 14, QFont.Weight.Bold))
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        self.element_info = QLabel()
        title_layout.addWidget(self.element_info)
        layout.addLayout(title_layout)
        
        # Main content splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)
        
        # Left panel - Text editor
        left_panel = self.create_editor_panel()
        splitter.addWidget(left_panel)
        
        # Right panel - Preview and options
        right_panel = self.create_preview_panel()
        splitter.addWidget(right_panel)
        
        # Set splitter proportions
        splitter.setSizes([600, 400])
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        self.preview_button = QPushButton("Preview Split")
        self.preview_button.setEnabled(False)
        self.preview_button.clicked.connect(self.preview_split)
        
        self.split_button = QPushButton("Split Element")
        self.split_button.setEnabled(False)
        self.split_button.setDefault(True)
        self.split_button.clicked.connect(self.perform_split)
        
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.preview_button)
        button_layout.addWidget(self.split_button)
        
        layout.addLayout(button_layout)
        
    def create_editor_panel(self) -> QWidget:
        """Create the text editor panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Instructions
        instructions = QLabel(
            "Ctrl+Click to add/remove split points. Right-click for context menu."
        )
        instructions.setStyleSheet("color: #666; font-style: italic; padding: 5px;")
        layout.addWidget(instructions)
        
        # Text editor
        self.text_editor = InteractiveSplitTextEdit()
        self.text_editor.setPlaceholderText("Element text will appear here...")
        layout.addWidget(self.text_editor)
        
        # Split controls
        controls_group = QGroupBox("Split Controls")
        controls_layout = QHBoxLayout(controls_group)
        
        self.add_split_button = QPushButton("Add Split at Cursor")
        self.add_split_button.clicked.connect(self.add_split_at_cursor)
        controls_layout.addWidget(self.add_split_button)
        
        self.remove_split_button = QPushButton("Remove Split at Cursor")
        self.remove_split_button.clicked.connect(self.remove_split_at_cursor)
        controls_layout.addWidget(self.remove_split_button)
        
        self.clear_splits_button = QPushButton("Clear All Splits")
        self.clear_splits_button.clicked.connect(self.clear_all_splits)
        controls_layout.addWidget(self.clear_splits_button)
        
        layout.addWidget(controls_group)
        
        # Auto-split options
        auto_group = QGroupBox("Auto-Split Options")
        auto_layout = QHBoxLayout(auto_group)
        
        self.auto_split_combo = QComboBox()
        self.auto_split_combo.addItems([
            "Split by sentences",
            "Split by paragraphs", 
            "Split by character count",
            "Split by word count"
        ])
        auto_layout.addWidget(self.auto_split_combo)
        
        self.auto_split_button = QPushButton("Auto Split")
        self.auto_split_button.clicked.connect(self.perform_auto_split)
        auto_layout.addWidget(self.auto_split_button)
        
        layout.addWidget(auto_group)
        
        # Split positions list
        positions_group = QGroupBox("Split Positions")
        positions_layout = QVBoxLayout(positions_group)
        
        self.positions_list = QListWidget()
        self.positions_list.setMaximumHeight(100)
        positions_layout.addWidget(self.positions_list)
        
        layout.addWidget(positions_group)
        
        return panel
        
    def create_preview_panel(self) -> QWidget:
        """Create the preview panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        
        # Split preview tab
        self.split_preview = SplitPreviewWidget()
        self.tab_widget.addTab(self.split_preview, "Split Preview")
        
        # Element preview tab
        self.element_preview = ElementPreview()
        self.tab_widget.addTab(self.element_preview, "Element Preview")
        
        # Validation tab
        self.validation_warnings = ValidationWarnings()
        self.tab_widget.addTab(self.validation_warnings, "Validation")
        
        # Operation preview tab
        self.operation_preview = OperationPreview()
        self.tab_widget.addTab(self.operation_preview, "Operation Preview")
        
        layout.addWidget(self.tab_widget)
        
        return panel
        
    def setup_connections(self):
        """Setup signal connections."""
        self.text_editor.split_point_added.connect(self.on_split_point_added)
        self.text_editor.split_point_removed.connect(self.on_split_point_removed)
        self.text_editor.textChanged.connect(self.update_split_preview)
        
    def load_element(self):
        """Load the element content into the editor."""
        # Set element info
        info_text = (f"Type: {self.original_element.element_type.value} | "
                    f"ID: {self.original_element.element_id} | "
                    f"Length: {len(self.original_element.text)} chars")
        self.element_info.setText(info_text)
        
        # Load text into editor
        self.text_editor.setPlainText(self.original_element.text)
        
        # Setup preview widget
        self.split_preview.set_original_element(self.original_element)
        self.element_preview.set_element(self.original_element)
        
    def add_split_at_cursor(self):
        """Add split point at current cursor position."""
        cursor = self.text_editor.textCursor()
        position = cursor.position()
        self.text_editor.add_split_point(position)
        
    def remove_split_at_cursor(self):
        """Remove split point at current cursor position."""
        cursor = self.text_editor.textCursor()
        position = cursor.position()
        self.text_editor.remove_split_point(position)
        
    def clear_all_splits(self):
        """Clear all split points."""
        self.text_editor.clear_split_points()
        self.split_positions.clear()
        self.positions_list.clear()
        self.update_button_states()
        self.update_split_preview()
        
    def on_split_point_added(self, position: int):
        """Handle split point addition."""
        if position not in self.split_positions:
            self.split_positions.append(position)
            self.split_positions.sort()
            
            # Update positions list
            self.update_positions_list()
            self.update_button_states()
            self.update_split_preview()
            
    def on_split_point_removed(self, position: int):
        """Handle split point removal."""
        if position in self.split_positions:
            self.split_positions.remove(position)
            
            # Update positions list
            self.update_positions_list()
            self.update_button_states()
            self.update_split_preview()
            
    def update_positions_list(self):
        """Update the split positions list widget."""
        self.positions_list.clear()
        for position in sorted(self.split_positions):
            item = QListWidgetItem(f"Position {position}")
            self.positions_list.addItem(item)
            
    def update_split_preview(self):
        """Update the split preview."""
        segments = self.text_editor.get_split_segments()
        self.split_preview.set_split_segments(segments)
        
    def update_button_states(self):
        """Update button enabled states."""
        has_splits = len(self.split_positions) > 0
        self.preview_button.setEnabled(has_splits)
        self.split_button.setEnabled(has_splits)
        
    def validate_split_operation(self) -> List[str]:
        """Validate the split operation and return warnings."""
        warnings = []
        
        if not self.split_positions:
            warnings.append("No split points defined.")
            
        if len(self.split_positions) > 20:
            warnings.append("Too many split points may create too many segments.")
            
        # Check for very small segments
        segments = self.text_editor.get_split_segments()
        small_segments = [s for s in segments if len(s.strip()) < 5]
        if small_segments:
            warnings.append(f"{len(small_segments)} segments are very short (< 5 characters).")
            
        return warnings
        
    def perform_auto_split(self):
        """Perform automatic splitting based on selected method."""
        method = self.auto_split_combo.currentText()
        text = self.text_editor.toPlainText()
        
        if method == "Split by sentences":
            # Simple sentence splitting
            positions = []
            for i, char in enumerate(text):
                if char in '.!?' and i < len(text) - 1:
                    if text[i + 1] == ' ':
                        positions.append(i + 1)
                        
        elif method == "Split by paragraphs":
            # Split by double newlines
            positions = []
            i = 0
            while i < len(text):
                if text[i:i+2] == '\n\n':
                    positions.append(i + 2)
                    i += 2
                else:
                    i += 1
                    
        elif method == "Split by character count":
            # Ask for character count
            count, ok = QInputDialog.getInt(
                self, "Character Count", "Characters per segment:", 
                100, 10, 10000
            )
            if ok:
                positions = list(range(count, len(text), count))
                
        elif method == "Split by word count":
            # Ask for word count
            count, ok = QInputDialog.getInt(
                self, "Word Count", "Words per segment:", 
                20, 1, 1000
            )
            if ok:
                words = text.split()
                positions = []
                word_count = 0
                char_pos = 0
                
                for word in words:
                    word_count += 1
                    char_pos += len(word) + 1  # +1 for space
                    
                    if word_count >= count and char_pos < len(text):
                        positions.append(char_pos)
                        word_count = 0
                        
        # Apply positions
        if 'positions' in locals():
            self.text_editor.clear_split_points()
            for pos in positions:
                if 0 < pos < len(text):
                    self.text_editor.add_split_point(pos)
                    
    def get_split_positions(self) -> List[int]:
        """Get current split positions."""
        return self.split_positions.copy()
        
    def get_resulting_elements(self) -> List[Element]:
        """Get the resulting elements from split."""
        return self.split_preview.get_resulting_elements()
        
    def get_split_options(self) -> Dict[str, Any]:
        """Get current split options."""
        return self.split_preview.get_split_options()
        
    def preview_split(self):
        """Preview the split operation."""
        if not self.split_positions:
            QMessageBox.warning(self, "No Split Points", 
                              "Please add split points before previewing.")
            return
            
        warnings = self.validate_split_operation()
        if warnings:
            self.validation_warnings.set_warnings(warnings)
            
        # Update operation preview
        options = self.get_split_options()
        self.operation_preview.set_operation("split", [self.original_element], options)
        
        # Switch to preview tab
        self.tab_widget.setCurrentWidget(self.operation_preview)
        
        # Emit preview signal
        self.preview_requested.emit(self.original_element, self.split_positions, options)
        
    def perform_split(self):
        """Perform the split operation."""
        if not self.split_positions:
            QMessageBox.warning(self, "No Split Points", 
                              "Please add split points before splitting.")
            return
            
        warnings = self.validate_split_operation()
        if warnings and any("error" in w.lower() for w in warnings):
            QMessageBox.critical(self, "Split Error", 
                               "Cannot proceed with split due to errors:\n" + "\n".join(warnings))
            return
            
        options = self.get_split_options()
        
        # Emit split signal
        self.split_requested.emit(self.original_element, self.split_positions, options)
        
        # Close dialog
        self.accept()