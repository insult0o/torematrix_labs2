"""
Split Dialog Component

Agent 2 implementation providing intuitive interface for splitting elements
with interactive split point selection, preview functionality, and validation.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any
from enum import Enum
import logging

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QWidget,
    QPushButton, QGroupBox, QComboBox, QSpinBox, QSlider, QTextEdit,
    QDialogButtonBox, QProgressBar, QFrame, QSplitter, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QRect
from PyQt6.QtGui import QFont, QPainter, QPen, QColor, QMouseEvent, QPixmap

from torematrix.core.models.element import Element
from torematrix.core.operations.merge_split.split import SplitOperation, SplitResult
from torematrix.core.operations.merge_split.algorithms.text_splitting import SplitStrategy
from .components.element_preview import ElementPreview
from .components.operation_preview import OperationPreview
from .components.validation_ui import ValidationWarnings

logger = logging.getLogger(__name__)


class SplitMode(Enum):
    """Modes for split operation."""
    MANUAL = "manual"
    AUTOMATIC = "automatic"
    POSITION = "position"


@dataclass
class SplitDialogResult:
    """Result of split dialog interaction."""
    accepted: bool = False
    split_elements: List[Element] = None
    original_element: Optional[Element] = None
    split_points: List[int] = None
    split_strategy: SplitStrategy = SplitStrategy.SENTENCE
    preserve_formatting: bool = True
    
    def __post_init__(self):
        if self.split_elements is None:
            self.split_elements = []
        if self.split_points is None:
            self.split_points = []


class InteractiveSplitWidget(QWidget):
    """
    Interactive widget for selecting split points in text.
    
    Provides visual feedback and allows clicking to set split points.
    """
    
    split_points_changed = pyqtSignal(list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.element: Optional[Element] = None
        self.split_points: List[int] = []
        self.text_lines: List[str] = []
        self.line_heights: List[int] = []
        self.char_positions: List[List[int]] = []
        
        self.setMinimumHeight(200)
        self.setMouseTracking(True)
        
        # Styling
        self.setStyleSheet("""
            InteractiveSplitWidget {
                background-color: white;
                border: 1px solid #cccccc;
                border-radius: 4px;
            }
        """)
    
    def set_element(self, element: Element):
        """Set the element to split."""
        self.element = element
        self.split_points = []
        
        if element and element.text:
            self._prepare_text_layout()
        
        self.update()
        self.split_points_changed.emit(self.split_points)
    
    def _prepare_text_layout(self):
        """Prepare text layout for interactive splitting."""
        if not self.element or not self.element.text:
            return
        
        # Split text into lines for display
        self.text_lines = self.element.text.split('\n')
        
        # Calculate character positions (simplified)
        self.char_positions = []
        char_pos = 0
        
        for line in self.text_lines:
            line_positions = []
            for char in line:
                line_positions.append(char_pos)
                char_pos += 1
            line_positions.append(char_pos)  # End of line
            self.char_positions.append(line_positions)
            char_pos += 1  # Newline character
    
    def add_split_point(self, position: int):
        """Add a split point at the given text position."""
        if position not in self.split_points:
            self.split_points.append(position)
            self.split_points.sort()
            self.update()
            self.split_points_changed.emit(self.split_points)
    
    def remove_split_point(self, position: int):
        """Remove a split point."""
        if position in self.split_points:
            self.split_points.remove(position)
            self.update()
            self.split_points_changed.emit(self.split_points)
    
    def clear_split_points(self):
        """Clear all split points."""
        self.split_points = []
        self.update()
        self.split_points_changed.emit(self.split_points)
    
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse clicks to add/remove split points."""
        if not self.element or not self.element.text:
            return
        
        # Convert mouse position to text position
        text_pos = self._mouse_to_text_position(event.pos())
        
        if text_pos is not None:
            if text_pos in self.split_points:
                self.remove_split_point(text_pos)
            else:
                self.add_split_point(text_pos)
    
    def _mouse_to_text_position(self, mouse_pos) -> Optional[int]:
        """Convert mouse position to text character position."""
        # Simplified implementation - in real version would use proper text metrics
        if not self.text_lines:
            return None
        
        line_height = 20  # Simplified
        line_index = min(mouse_pos.y() // line_height, len(self.text_lines) - 1)
        
        if line_index < 0 or line_index >= len(self.text_lines):
            return None
        
        # Estimate character position in line
        char_width = 8  # Simplified
        char_index = min(mouse_pos.x() // char_width, len(self.text_lines[line_index]))
        
        # Convert to absolute text position
        text_pos = sum(len(line) + 1 for line in self.text_lines[:line_index]) + char_index
        
        return min(text_pos, len(self.element.text))
    
    def paintEvent(self, event):
        """Paint the interactive split widget."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        if not self.element or not self.element.text:
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No element selected")
            return
        
        # Draw text with split points
        font = painter.font()
        font.setFamily("Consolas")
        font.setPointSize(10)
        painter.setFont(font)
        
        line_height = 20
        margin = 10
        
        for i, line in enumerate(self.text_lines):
            y = margin + (i + 1) * line_height
            painter.drawText(margin, y, line)
            
            # Draw split points for this line
            if i < len(self.char_positions):
                for char_pos in self.char_positions[i]:
                    if char_pos in self.split_points:
                        x = margin + char_pos * 8  # Simplified character width
                        
                        # Draw split point indicator
                        painter.setPen(QPen(QColor(255, 0, 0), 2))
                        painter.drawLine(x, y - 15, x, y + 5)
                        
                        # Draw split point marker
                        painter.setBrush(QColor(255, 0, 0))
                        painter.drawEllipse(x - 3, y - 18, 6, 6)
        
        painter.setPen(QPen(QColor(0, 0, 0), 1))


class SplitDialog(QDialog):
    """
    Main split dialog for dividing elements into multiple parts.
    
    Agent 2 implementation with:
    - Interactive split point selection
    - Multiple split strategies
    - Real-time preview
    - Validation feedback
    """
    
    # Signals
    split_points_changed = pyqtSignal(list)
    preview_updated = pyqtSignal(object)
    validation_changed = pyqtSignal(bool)
    
    def __init__(self, element: Element = None, parent=None):
        """Initialize split dialog with optional element."""
        super().__init__(parent)
        
        self.logger = logging.getLogger(__name__ + ".SplitDialog")
        self.element = element
        self.split_result: Optional[SplitResult] = None
        self.dialog_result = SplitDialogResult()
        
        # UI components
        self.split_widget = None
        self.preview_widget = None
        self.validation_widget = None
        self.strategy_combo = None
        self.split_count_spin = None
        self.preserve_formatting_check = None
        self.progress_bar = None
        
        # Preview timer for delayed updates
        self.preview_timer = QTimer()
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self._update_preview)
        
        self._setup_ui()
        self._connect_signals()
        
        # Initialize with provided element
        if self.element:
            self.split_widget.set_element(self.element)
            self._update_preview_delayed()
    
    def _setup_ui(self):
        """Set up the user interface."""
        self.setWindowTitle("Split Element")
        self.setModal(True)
        self.resize(900, 700)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Create splitter for main areas
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - Split configuration
        left_panel = self._create_config_panel()
        splitter.addWidget(left_panel)
        
        # Right panel - Preview
        right_panel = self._create_preview_panel()
        splitter.addWidget(right_panel)
        
        # Set splitter proportions
        splitter.setSizes([400, 500])
        main_layout.addWidget(splitter)
        
        # Bottom panel - Progress and buttons
        bottom_panel = self._create_bottom_panel()
        main_layout.addWidget(bottom_panel)
    
    def _create_config_panel(self) -> QFrame:
        """Create the split configuration panel."""
        frame = QFrame()
        layout = QVBoxLayout(frame)
        
        # Title
        title_label = QLabel("Split Configuration")
        title_font = QFont()
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Split strategy selection
        strategy_group = QGroupBox("Split Strategy")
        strategy_layout = QVBoxLayout(strategy_group)
        
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems([
            "Sentence (Recommended)",
            "Paragraph",
            "Word Count",
            "Character Count",
            "Manual Points"
        ])
        self.strategy_combo.currentTextChanged.connect(self._on_strategy_changed)
        strategy_layout.addWidget(self.strategy_combo)
        
        # Split count for automatic strategies
        count_layout = QHBoxLayout()
        count_layout.addWidget(QLabel("Target Parts:"))
        self.split_count_spin = QSpinBox()
        self.split_count_spin.setRange(2, 20)
        self.split_count_spin.setValue(2)
        self.split_count_spin.valueChanged.connect(self._on_count_changed)
        count_layout.addWidget(self.split_count_spin)
        strategy_layout.addLayout(count_layout)
        
        layout.addWidget(strategy_group)
        
        # Options
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout(options_group)
        
        self.preserve_formatting_check = QCheckBox("Preserve Formatting")
        self.preserve_formatting_check.setChecked(True)
        self.preserve_formatting_check.toggled.connect(self._update_preview_delayed)
        options_layout.addWidget(self.preserve_formatting_check)
        
        layout.addWidget(options_group)
        
        # Interactive split widget
        split_group = QGroupBox("Interactive Split Points")
        split_layout = QVBoxLayout(split_group)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        clear_button = QPushButton("Clear All")
        clear_button.clicked.connect(self._clear_split_points)
        controls_layout.addWidget(clear_button)
        
        auto_button = QPushButton("Auto Split")
        auto_button.clicked.connect(self._auto_split)
        controls_layout.addWidget(auto_button)
        
        split_layout.addLayout(controls_layout)
        
        # Interactive widget
        self.split_widget = InteractiveSplitWidget()
        self.split_widget.setMinimumHeight(200)
        split_layout.addWidget(self.split_widget)
        
        layout.addWidget(split_group)
        
        # Validation warnings
        self.validation_widget = ValidationWarnings()
        layout.addWidget(self.validation_widget)
        
        return frame
    
    def _create_preview_panel(self) -> QFrame:
        """Create the preview panel."""
        frame = QFrame()
        layout = QVBoxLayout(frame)
        
        # Title
        title_label = QLabel("Split Preview")
        title_font = QFont()
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Preview widget
        self.preview_widget = OperationPreview()
        self.preview_widget.setMinimumHeight(400)
        layout.addWidget(self.preview_widget)
        
        return frame
    
    def _create_bottom_panel(self) -> QFrame:
        """Create the bottom panel with progress and buttons."""
        frame = QFrame()
        layout = QVBoxLayout(frame)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._accept_split)
        button_box.rejected.connect(self.reject)
        
        # Get OK button for enabling/disabling
        self.ok_button = button_box.button(QDialogButtonBox.StandardButton.Ok)
        self.ok_button.setText("Split Element")
        self.ok_button.setEnabled(False)
        
        layout.addWidget(button_box)
        
        return frame
    
    def _connect_signals(self):
        """Connect internal signals."""
        self.split_widget.split_points_changed.connect(self._on_split_points_changed)
        self.split_points_changed.connect(self._update_preview_delayed)
        self.preview_updated.connect(self._on_preview_updated)
        self.validation_changed.connect(self._on_validation_changed)
    
    def _on_strategy_changed(self, strategy_text: str):
        """Handle split strategy changes."""
        self._update_preview_delayed()
        
        # Enable/disable controls based on strategy
        is_manual = "Manual" in strategy_text
        self.split_widget.setEnabled(is_manual)
        self.split_count_spin.setEnabled(not is_manual)
    
    def _on_count_changed(self, count: int):
        """Handle split count changes."""
        self._update_preview_delayed()
    
    def _on_split_points_changed(self, points: List[int]):
        """Handle split points changes."""
        self.split_points_changed.emit(points)
    
    def _clear_split_points(self):
        """Clear all split points."""
        self.split_widget.clear_split_points()
    
    def _auto_split(self):
        """Automatically determine split points."""
        if not self.element:
            return
        
        try:
            # Create split operation for auto-detection
            split_op = SplitOperation(self.element)
            strategy = self._get_split_strategy()
            count = self.split_count_spin.value()
            
            # Get suggested split points
            suggested_points = split_op.suggest_split_points(strategy, count)
            
            # Apply to interactive widget
            self.split_widget.clear_split_points()
            for point in suggested_points:
                self.split_widget.add_split_point(point)
                
        except Exception as e:
            self.logger.error(f"Auto split failed: {e}")
            self.validation_widget.add_warning(
                "Auto Split Failed",
                str(e),
                "error"
            )
    
    def _get_split_strategy(self) -> SplitStrategy:
        """Get selected split strategy."""
        strategy_text = self.strategy_combo.currentText()
        
        if "Sentence" in strategy_text:
            return SplitStrategy.SENTENCE
        elif "Paragraph" in strategy_text:
            return SplitStrategy.PARAGRAPH
        elif "Word Count" in strategy_text:
            return SplitStrategy.WORD_COUNT
        elif "Character Count" in strategy_text:
            return SplitStrategy.CHARACTER_COUNT
        elif "Manual" in strategy_text:
            return SplitStrategy.MANUAL
        else:
            return SplitStrategy.SENTENCE
    
    def _update_preview_delayed(self):
        """Update preview with a delay to avoid excessive updates."""
        self.preview_timer.start(300)  # 300ms delay
    
    def _update_preview(self):
        """Update the split preview."""
        if not self.element:
            self.preview_widget.clear_preview()
            return
        
        try:
            # Create split operation
            split_op = SplitOperation(self.element)
            
            # Get split points
            if "Manual" in self.strategy_combo.currentText():
                split_points = self.split_widget.split_points
            else:
                strategy = self._get_split_strategy()
                count = self.split_count_spin.value()
                split_points = split_op.suggest_split_points(strategy, count)
            
            if not split_points:
                self.validation_widget.add_warning(
                    "No Split Points",
                    "No valid split points found. Element cannot be split.",
                    "warning"
                )
                self.preview_widget.clear_preview()
                self.split_result = None
                return
            
            # Get preview
            preview_result = split_op.preview(split_points)
            
            if preview_result.success:
                # Update preview widget
                self.preview_widget.set_preview(
                    original_elements=[self.element],
                    result_element=preview_result.split_elements,
                    operation_type="split"
                )
                
                # Clear validation warnings
                self.validation_widget.clear_warnings()
                
                self.split_result = preview_result
                self.preview_updated.emit(preview_result)
                
            else:
                # Show validation errors
                self.validation_widget.add_warning(
                    "Split Preview Failed",
                    preview_result.error_message or "Unknown error",
                    "error"
                )
                self.preview_widget.clear_preview()
                self.split_result = None
        
        except Exception as e:
            self.logger.error(f"Preview update failed: {e}")
            self.validation_widget.add_warning(
                "Preview Error",
                str(e),
                "error"
            )
            self.preview_widget.clear_preview()
            self.split_result = None
        
        # Update validation state
        self.validation_changed.emit(self.split_result is not None)
    
    def _on_preview_updated(self, result):
        """Handle preview updates."""
        self.ok_button.setEnabled(result is not None)
    
    def _on_validation_changed(self, is_valid: bool):
        """Handle validation state changes."""
        self.ok_button.setEnabled(is_valid and self.element is not None)
    
    def _accept_split(self):
        """Accept the split operation."""
        if not self.split_result or not self.element:
            return
        
        try:
            # Show progress
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            
            # Create and execute split operation
            split_op = SplitOperation(self.element)
            
            # Get split points
            if "Manual" in self.strategy_combo.currentText():
                split_points = self.split_widget.split_points
            else:
                strategy = self._get_split_strategy()
                count = self.split_count_spin.value()
                split_points = split_op.suggest_split_points(strategy, count)
            
            self.progress_bar.setValue(50)
            
            # Execute split
            result = split_op.execute(split_points)
            
            self.progress_bar.setValue(100)
            
            if result.success:
                # Populate dialog result
                self.dialog_result.accepted = True
                self.dialog_result.split_elements = result.split_elements
                self.dialog_result.original_element = self.element
                self.dialog_result.split_points = split_points
                self.dialog_result.split_strategy = self._get_split_strategy()
                self.dialog_result.preserve_formatting = self.preserve_formatting_check.isChecked()
                
                self.accept()
            else:
                # Show error
                self.validation_widget.add_warning(
                    "Split Failed",
                    result.error_message or "Unknown error",
                    "error"
                )
                
        except Exception as e:
            self.logger.error(f"Split execution failed: {e}")
            self.validation_widget.add_warning(
                "Split Error",
                str(e),
                "error"
            )
        
        finally:
            self.progress_bar.setVisible(False)
    
    def get_result(self) -> SplitDialogResult:
        """Get the dialog result."""
        return self.dialog_result
    
    def set_element(self, element: Element):
        """Set element to split."""
        self.element = element
        self.split_widget.set_element(element)
        self._update_preview_delayed()


# Convenience function for showing split dialog
def show_split_dialog(element: Element, parent=None) -> SplitDialogResult:
    """Show split dialog and return result."""
    dialog = SplitDialog(element, parent)
    dialog.exec()
    return dialog.get_result()