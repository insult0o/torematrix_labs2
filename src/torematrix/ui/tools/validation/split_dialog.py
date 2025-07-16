"""
Split Dialog Component for Document Element Splitting.

This module provides a comprehensive dialog interface for splitting document
elements with interactive text editing and split point selection.
"""

from typing import List, Optional, Dict, Any, Tuple
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QListWidget, QListWidgetItem, QTextEdit, QLabel, QPushButton,
    QSplitter, QWidget, QFrame, QCheckBox, QComboBox,
    QProgressBar, QMessageBox, QToolButton, QSpinBox,
    QScrollArea, QInputDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import (
    QTextCursor, QTextCharFormat, QColor, QFont, QMouseEvent,
    QSyntaxHighlighter, QTextDocument
)

from ....core.models import Element, ElementType
from .components.element_preview import ElementPreview
from .components.metadata_resolver import MetadataConflictResolver
from .components.operation_preview import OperationPreview
from .components.validation_ui import ValidationWarnings


class SplitPointHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for marking split points in text."""
    
    def __init__(self, parent: QTextDocument):
        super().__init__(parent)
        self.split_positions: List[int] = []
        
        # Format for split points
        self.split_format = QTextCharFormat()
        self.split_format.setBackground(QColor("#ffeb3b"))
        self.split_format.setForeground(QColor("#000000"))
        self.split_format.setFontWeight(QFont.Weight.Bold)
    
    def set_split_positions(self, positions: List[int]):
        """Set the positions where splits should be highlighted."""
        self.split_positions = positions
        self.rehighlight()
    
    def highlightBlock(self, text: str):
        """Highlight split points in the current block."""
        if not self.split_positions:
            return
        
        block_start = self.currentBlock().position()
        block_length = len(text)
        
        for position in self.split_positions:
            relative_pos = position - block_start
            if 0 <= relative_pos < block_length:
                # Highlight the character at the split position
                self.setFormat(relative_pos, 1, self.split_format)


class InteractiveSplitTextEdit(QTextEdit):
    """Interactive text editor for selecting split points."""
    
    split_point_added = pyqtSignal(int)
    split_point_removed = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.split_positions: List[int] = []
        
        # Set up syntax highlighter
        self.highlighter = SplitPointHighlighter(self.document())
        
        # Configure editor
        self.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.setAcceptRichText(False)
        
        # Set tooltip
        self.setToolTip("Ctrl+Click to add/remove split points")
    
    def add_split_point(self, position: int):
        """Add a split point at the specified position."""
        if position <= 0 or position in self.split_positions:
            return
        
        if position >= len(self.toPlainText()):
            return
        
        self.split_positions.append(position)
        self.split_positions.sort()
        self.highlighter.set_split_positions(self.split_positions)
        self.split_point_added.emit(position)
    
    def remove_split_point(self, position: int):
        """Remove a split point at the specified position."""
        if position in self.split_positions:
            self.split_positions.remove(position)
            self.highlighter.set_split_positions(self.split_positions)
            self.split_point_removed.emit(position)
    
    def clear_split_points(self):
        """Clear all split points."""
        self.split_positions.clear()
        self.highlighter.set_split_positions(self.split_positions)
    
    def get_split_positions(self) -> List[int]:
        """Get sorted list of split positions."""
        return sorted(self.split_positions)
    
    def set_split_positions(self, positions: List[int]):
        """Set split positions programmatically."""
        self.split_positions = sorted(positions)
        self.highlighter.set_split_positions(self.split_positions)
    
    def get_split_segments(self) -> List[str]:
        """Get text segments based on current split points."""
        text = self.toPlainText()
        if not self.split_positions:
            return [text]
        
        segments = []
        start = 0
        
        for position in sorted(self.split_positions):
            if start < position <= len(text):
                segments.append(text[start:position])
                start = position
        
        # Add final segment
        if start < len(text):
            segments.append(text[start:])
        
        return segments
    
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press events for split point selection."""
        if (event.button() == Qt.MouseButton.LeftButton and 
            event.modifiers() == Qt.KeyboardModifier.ControlModifier):
            
            # Get cursor position at click
            cursor = self.cursorForPosition(event.pos())
            position = cursor.position()
            
            # Toggle split point
            if position in self.split_positions:
                self.remove_split_point(position)
            else:
                self.add_split_point(position)
        else:
            super().mousePressEvent(event)


class SplitPreviewWidget(QWidget):
    """Widget for previewing split operation results."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.original_element: Optional[Element] = None
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the preview widget UI."""
        layout = QVBoxLayout(self)
        
        # Original element info
        info_group = QGroupBox("Original Element")
        info_layout = QVBoxLayout(info_group)
        
        self.original_info = QLabel("No element selected")
        self.original_info.setWordWrap(True)
        info_layout.addWidget(self.original_info)
        
        layout.addWidget(info_group)
        
        # Split options
        options_group = QGroupBox("Split Options")
        options_layout = QGridLayout(options_group)
        
        # Element type for new segments
        options_layout.addWidget(QLabel("Element Type:"), 0, 0)
        self.element_type_combo = QComboBox()
        for element_type in ElementType:
            self.element_type_combo.addItem(element_type.value)
        options_layout.addWidget(self.element_type_combo, 0, 1)
        
        # Preserve metadata
        self.preserve_metadata = QCheckBox("Preserve original metadata")
        self.preserve_metadata.setChecked(True)
        options_layout.addWidget(self.preserve_metadata, 1, 0, 1, 2)
        
        # Auto-trim whitespace
        self.auto_trim = QCheckBox("Auto-trim whitespace")
        self.auto_trim.setChecked(True)
        options_layout.addWidget(self.auto_trim, 2, 0, 1, 2)
        
        layout.addWidget(options_group)
        
        # Results preview
        results_group = QGroupBox("Split Results")
        results_layout = QVBoxLayout(results_group)
        
        self.results_label = QLabel("No splits defined")
        results_layout.addWidget(self.results_label)
        
        self.result_list = QListWidget()
        self.result_list.setMaximumHeight(150)
        results_layout.addWidget(self.result_list)
        
        layout.addWidget(results_group)
    
    def set_original_element(self, element: Element):
        """Set the original element being split."""
        self.original_element = element
        
        # Update info display
        info_text = (
            f"Type: {element.element_type.value}\n"
            f"ID: {element.element_id}\n"
            f"Length: {len(element.text)} characters"
        )
        self.original_info.setText(info_text)
        
        # Set default element type
        self.element_type_combo.setCurrentText(element.element_type.value)
    
    def set_split_segments(self, segments: List[str]):
        """Set the split segments for preview."""
        self.result_list.clear()
        
        if not segments:
            self.results_label.setText("No splits defined")
            return
        
        valid_segments = [seg.strip() for seg in segments if seg.strip()]
        self.results_label.setText(f"Will create {len(valid_segments)} new elements:")
        
        for i, segment in enumerate(valid_segments):
            item_text = f"{i+1}. {segment[:50]}{'...' if len(segment) > 50 else ''}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, segment)
            self.result_list.addItem(item)
    
    def get_resulting_elements(self) -> List[Element]:
        """Get the resulting elements from the split operation."""
        if not self.original_element:
            return []
        
        elements = []
        selected_type = ElementType(self.element_type_combo.currentText())
        
        for i in range(self.result_list.count()):
            item = self.result_list.item(i)
            segment_text = item.data(Qt.ItemDataRole.UserRole)
            
            if segment_text and segment_text.strip():
                # Create new element
                element = Element(
                    element_type=selected_type,
                    text=segment_text.strip() if self.auto_trim.isChecked() else segment_text
                )
                
                # Copy metadata if requested
                if self.preserve_metadata.isChecked():
                    element.parent_id = self.original_element.parent_id
                    element.page_number = self.original_element.page_number
                    element.bbox = self.original_element.bbox
                
                elements.append(element)
        
        return elements
    
    def get_split_options(self) -> Dict[str, Any]:
        """Get the current split options."""
        return {
            "element_type": self.element_type_combo.currentText(),
            "preserve_metadata": self.preserve_metadata.isChecked(),
            "auto_trim": self.auto_trim.isChecked()
        }


class SplitDialog(QDialog):
    """
    Main dialog for splitting document elements.
    
    Provides an interactive interface for selecting split points in text
    and configuring the split operation.
    """
    
    split_requested = pyqtSignal(Element, list, dict)  # element, positions, options
    
    def __init__(self, element: Element, parent=None):
        super().__init__(parent)
        self.original_element = element
        self.split_positions: List[int] = []
        self.setup_ui()
        self.setup_connections()
        self.load_element()
        
        # Window configuration
        self.setWindowTitle(f"Split {element.element_type.value} Element")
        self.setModal(True)
        self.resize(1000, 700)
    
    def setup_ui(self):
        """Set up the main dialog UI."""
        layout = QVBoxLayout(self)
        
        # Title and description
        title_label = QLabel("Split Document Element")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        layout.addWidget(title_label)
        
        description_label = QLabel(
            "Click in the text to place your cursor, then use Ctrl+Click to add/remove split points. "
            "Split points will divide the element into separate segments."
        )
        description_label.setWordWrap(True)
        description_label.setStyleSheet("color: #666666; margin-bottom: 10px;")
        layout.addWidget(description_label)
        
        # Main content area
        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(content_splitter)
        
        # Left panel - Text editing
        self.setup_editor_panel(content_splitter)
        
        # Right panel - Preview and options
        self.setup_preview_panel(content_splitter)
        
        # Bottom section - Validation and actions
        self.setup_bottom_section(layout)
    
    def setup_editor_panel(self, parent):
        """Set up the text editor panel."""
        editor_widget = QWidget()
        editor_layout = QVBoxLayout(editor_widget)
        
        # Element info
        info_group = QGroupBox("Element Information")
        info_layout = QVBoxLayout(info_group)
        
        self.element_info = QLabel()
        self.element_info.setWordWrap(True)
        info_layout.addWidget(self.element_info)
        
        editor_layout.addWidget(info_group)
        
        # Text editor
        editor_group = QGroupBox("Text Content")
        editor_group_layout = QVBoxLayout(editor_group)
        
        self.text_editor = InteractiveSplitTextEdit()
        editor_group_layout.addWidget(self.text_editor)
        
        # Split point controls
        controls_layout = QHBoxLayout()
        
        self.add_split_button = QPushButton("Add Split at Cursor")
        self.remove_split_button = QPushButton("Remove Split at Cursor")
        self.clear_splits_button = QPushButton("Clear All Splits")
        
        controls_layout.addWidget(self.add_split_button)
        controls_layout.addWidget(self.remove_split_button)
        controls_layout.addWidget(self.clear_splits_button)
        controls_layout.addStretch()
        
        editor_group_layout.addLayout(controls_layout)
        editor_layout.addWidget(editor_group)
        
        # Split positions list
        positions_group = QGroupBox("Split Positions")
        positions_layout = QVBoxLayout(positions_group)
        
        self.positions_list = QListWidget()
        self.positions_list.setMaximumHeight(100)
        positions_layout.addWidget(self.positions_list)
        
        # Auto-split options
        auto_layout = QHBoxLayout()
        self.auto_split_combo = QComboBox()
        self.auto_split_combo.addItems([
            "Manual split only",
            "Split by sentences",
            "Split by paragraphs", 
            "Split by character count",
            "Split by word count"
        ])
        
        self.auto_split_button = QPushButton("Auto Split")
        
        auto_layout.addWidget(QLabel("Auto Split:"))
        auto_layout.addWidget(self.auto_split_combo)
        auto_layout.addWidget(self.auto_split_button)
        auto_layout.addStretch()
        
        positions_layout.addLayout(auto_layout)
        editor_layout.addWidget(positions_group)
        
        parent.addWidget(editor_widget)
    
    def setup_preview_panel(self, parent):
        """Set up the preview panel."""
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)
        
        # Split preview
        self.split_preview = SplitPreviewWidget()
        preview_layout.addWidget(self.split_preview)
        
        # Metadata conflict resolution
        self.metadata_resolver = MetadataConflictResolver()
        preview_layout.addWidget(self.metadata_resolver)
        
        # Operation preview
        self.operation_preview = OperationPreview()
        preview_layout.addWidget(self.operation_preview)
        
        parent.addWidget(preview_widget)
    
    def setup_bottom_section(self, parent_layout):
        """Set up the bottom validation and action section."""
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        
        # Validation warnings
        self.validation_warnings = ValidationWarnings()
        bottom_layout.addWidget(self.validation_warnings)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        bottom_layout.addWidget(self.progress_bar)
        
        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.preview_button = QPushButton("Preview Split")
        self.preview_button.setEnabled(False)
        
        self.split_button = QPushButton("Perform Split")
        self.split_button.setEnabled(False)
        self.split_button.setDefault(True)
        
        self.cancel_button = QPushButton("Cancel")
        
        button_layout.addWidget(self.preview_button)
        button_layout.addWidget(self.split_button)
        button_layout.addWidget(self.cancel_button)
        
        bottom_layout.addLayout(button_layout)
        parent_layout.addWidget(bottom_widget)
    
    def setup_connections(self):
        """Set up signal connections."""
        # Text editor signals
        self.text_editor.split_point_added.connect(self.on_split_point_added)
        self.text_editor.split_point_removed.connect(self.on_split_point_removed)
        
        # Control buttons
        self.add_split_button.clicked.connect(self.add_split_at_cursor)
        self.remove_split_button.clicked.connect(self.remove_split_at_cursor)
        self.clear_splits_button.clicked.connect(self.clear_all_splits)
        self.auto_split_button.clicked.connect(self.perform_auto_split)
        
        # List selection
        self.positions_list.itemSelectionChanged.connect(self.update_button_states)
        
        # Action buttons
        self.preview_button.clicked.connect(self.preview_split)
        self.split_button.clicked.connect(self.perform_split)
        self.cancel_button.clicked.connect(self.reject)
    
    def load_element(self):
        """Load the element content into the editor."""
        # Update element info
        info_text = (
            f"Type: {self.original_element.element_type.value}\n"
            f"ID: {self.original_element.element_id}\n"
            f"Length: {len(self.original_element.text)} characters"
        )
        self.element_info.setText(info_text)
        
        # Load text into editor
        self.text_editor.setPlainText(self.original_element.text)
        
        # Set up preview
        self.split_preview.set_original_element(self.original_element)
    
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
        self.update_split_preview()
        self.update_button_states()
    
    def on_split_point_added(self, position: int):
        """Handle split point addition."""
        if position not in self.split_positions:
            self.split_positions.append(position)
            self.split_positions.sort()
            
            # Add to list
            item = QListWidgetItem(f"Position {position}")
            item.setData(Qt.ItemDataRole.UserRole, position)
            self.positions_list.addItem(item)
            
            self.update_split_preview()
            self.update_button_states()
    
    def on_split_point_removed(self, position: int):
        """Handle split point removal."""
        if position in self.split_positions:
            self.split_positions.remove(position)
            
            # Remove from list
            for i in range(self.positions_list.count()):
                item = self.positions_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == position:
                    self.positions_list.takeItem(i)
                    break
            
            self.update_split_preview()
            self.update_button_states()
    
    def update_split_preview(self):
        """Update the split preview with current positions."""
        segments = self.text_editor.get_split_segments()
        self.split_preview.set_split_segments(segments)
        
        # Update operation preview
        if self.split_positions:
            split_options = self.get_split_options()
            self.operation_preview.set_operation("split", [self.original_element], split_options)
        else:
            self.operation_preview.clear_preview()
    
    def update_button_states(self):
        """Update button enabled states based on current state."""
        has_splits = len(self.split_positions) > 0
        
        self.preview_button.setEnabled(has_splits)
        self.split_button.setEnabled(has_splits)
        self.clear_splits_button.setEnabled(has_splits)
    
    def perform_auto_split(self):
        """Perform automatic splitting based on selected method."""
        method = self.auto_split_combo.currentText()
        
        if method == "Manual split only":
            return
        
        text = self.text_editor.toPlainText()
        positions = []
        
        if method == "Split by sentences":
            # Simple sentence splitting on ., !, ?
            import re
            for match in re.finditer(r'[.!?]+\s+', text):
                positions.append(match.end())
        
        elif method == "Split by paragraphs":
            # Split on double newlines
            import re
            for match in re.finditer(r'\n\s*\n', text):
                positions.append(match.end())
        
        elif method == "Split by character count":
            count, ok = QInputDialog.getInt(
                self, "Character Count", "Characters per segment:", 
                100, 1, 10000
            )
            if ok:
                positions = list(range(count, len(text), count))
        
        elif method == "Split by word count":
            count, ok = QInputDialog.getInt(
                self, "Word Count", "Words per segment:",
                50, 1, 1000
            )
            if ok:
                words = text.split()
                current_pos = 0
                word_count = 0
                for word in words:
                    word_count += 1
                    current_pos += len(word) + 1  # +1 for space
                    if word_count >= count:
                        positions.append(current_pos)
                        word_count = 0
        
        # Apply positions
        self.text_editor.clear_split_points()
        for pos in positions:
            if 0 < pos < len(text):
                self.text_editor.add_split_point(pos)
    
    def validate_split_operation(self) -> List[str]:
        """Validate the split operation and return warnings."""
        warnings = []
        
        if not self.split_positions:
            warnings.append("No split points defined. Element will not be split.")
        
        if len(self.split_positions) > 50:
            warnings.append("Too many split points may create excessive segments.")
        
        # Check for very small segments
        segments = self.text_editor.get_split_segments()
        small_segments = [seg for seg in segments if len(seg.strip()) < 5]
        if small_segments:
            warnings.append(f"{len(small_segments)} segments are very short (< 5 characters).")
        
        return warnings
    
    def preview_split(self):
        """Preview the split operation."""
        if not self.split_positions:
            QMessageBox.warning(self, "No Split Points", 
                              "Please add split points before previewing.")
            return
        
        # Validate operation
        warnings = self.validate_split_operation()
        self.validation_warnings.set_warnings(warnings)
        
        # Update preview
        self.update_split_preview()
    
    def perform_split(self):
        """Perform the actual split operation."""
        if not self.split_positions:
            QMessageBox.warning(self, "No Split Points",
                              "Please add split points before splitting.")
            return
        
        # Get split options
        split_options = self.get_split_options()
        split_options["split_positions"] = self.split_positions.copy()
        
        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(50)
        
        # Emit split request
        self.split_requested.emit(self.original_element, self.split_positions, split_options)
        
        # Close dialog
        QTimer.singleShot(500, self.accept)  # Small delay for visual feedback
    
    def get_split_positions(self) -> List[int]:
        """Get the current split positions."""
        return self.split_positions.copy()
    
    def get_resulting_elements(self) -> List[Element]:
        """Get the resulting elements from the split."""
        return self.split_preview.get_resulting_elements()
    
    def get_split_options(self) -> Dict[str, Any]:
        """Get the current split configuration options."""
        base_options = self.split_preview.get_split_options()
        base_options["split_positions"] = self.split_positions.copy()
        return base_options