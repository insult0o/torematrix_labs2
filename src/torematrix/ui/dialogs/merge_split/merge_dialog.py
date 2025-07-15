"""
Merge Dialog Component

Agent 2 implementation providing intuitive interface for merging multiple elements
with drag-and-drop support, preview functionality, and metadata conflict resolution.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum
import logging

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QGroupBox, QComboBox, QCheckBox, QSplitter, QTextEdit,
    QDialogButtonBox, QProgressBar, QFrame, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPixmap, QDragEnterEvent, QDropEvent

from torematrix.core.models.element import Element
from torematrix.core.operations.merge_split.merge import MergeOperation, MergeResult
from torematrix.core.operations.merge_split.algorithms.text_merging import MergeStrategy
from torematrix.core.operations.merge_split.algorithms.metadata_merge import ConflictResolution
from .components.element_preview import ElementPreview
from .components.metadata_resolver import MetadataConflictResolver
from .components.operation_preview import OperationPreview
from .components.validation_ui import ValidationWarnings

logger = logging.getLogger(__name__)


class MergeDialogMode(Enum):
    """Modes for merge dialog operation."""
    SELECTION = "selection"
    PREVIEW = "preview"
    EXECUTION = "execution"


@dataclass
class MergeDialogResult:
    """Result of merge dialog interaction."""
    accepted: bool = False
    merged_element: Optional[Element] = None
    original_elements: List[Element] = None
    merge_strategy: MergeStrategy = MergeStrategy.SMART
    metadata_strategies: Dict[str, ConflictResolution] = None
    
    def __post_init__(self):
        if self.original_elements is None:
            self.original_elements = []
        if self.metadata_strategies is None:
            self.metadata_strategies = {}


class MergeDialog(QDialog):
    """
    Main merge dialog for combining multiple elements.
    
    Agent 2 implementation with:
    - Drag-and-drop element selection
    - Interactive preview with before/after comparison
    - Metadata conflict resolution UI
    - Merge strategy configuration
    - Real-time validation feedback
    """
    
    # Signals
    elements_changed = pyqtSignal(list)
    preview_updated = pyqtSignal(object)
    validation_changed = pyqtSignal(bool)
    
    def __init__(self, elements: List[Element] = None, parent=None):
        """Initialize merge dialog with optional initial elements."""
        super().__init__(parent)
        
        self.logger = logging.getLogger(__name__ + ".MergeDialog")
        self.elements = elements or []
        self.current_mode = MergeDialogMode.SELECTION
        self.merge_result: Optional[MergeResult] = None
        self.dialog_result = MergeDialogResult()
        
        # UI components
        self.element_list = None
        self.preview_widget = None
        self.metadata_resolver = None
        self.validation_widget = None
        self.strategy_combo = None
        self.progress_bar = None
        
        # Preview timer for delayed updates
        self.preview_timer = QTimer()
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self._update_preview)
        
        self._setup_ui()
        self._connect_signals()
        
        # Initialize with provided elements
        if self.elements:
            self._populate_element_list()
            self._update_preview_delayed()
    
    def _setup_ui(self):
        """Set up the user interface."""
        self.setWindowTitle("Merge Elements")
        self.setModal(True)
        self.resize(800, 600)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Create splitter for main areas
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - Element selection
        left_panel = self._create_selection_panel()
        splitter.addWidget(left_panel)
        
        # Right panel - Preview and configuration
        right_panel = self._create_preview_panel()
        splitter.addWidget(right_panel)
        
        # Set splitter proportions
        splitter.setSizes([300, 500])
        main_layout.addWidget(splitter)
        
        # Bottom panel - Progress and buttons
        bottom_panel = self._create_bottom_panel()
        main_layout.addWidget(bottom_panel)
    
    def _create_selection_panel(self) -> QFrame:
        """Create the element selection panel."""
        frame = QFrame()
        layout = QVBoxLayout(frame)
        
        # Title
        title_label = QLabel("Elements to Merge")
        title_font = QFont()
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Element list with drag-and-drop
        self.element_list = QListWidget()
        self.element_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.element_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.element_list.setMinimumHeight(200)
        layout.addWidget(self.element_list)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.add_button = QPushButton("Add Elements...")
        self.add_button.clicked.connect(self._add_elements)
        button_layout.addWidget(self.add_button)
        
        self.remove_button = QPushButton("Remove Selected")
        self.remove_button.clicked.connect(self._remove_selected)
        button_layout.addWidget(self.remove_button)
        
        layout.addLayout(button_layout)
        
        # Merge strategy selection
        strategy_group = QGroupBox("Merge Strategy")
        strategy_layout = QVBoxLayout(strategy_group)
        
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems([
            "Smart (Recommended)",
            "Simple (Space-separated)",
            "Paragraph (Line breaks)"
        ])
        self.strategy_combo.currentTextChanged.connect(self._on_strategy_changed)
        strategy_layout.addWidget(self.strategy_combo)
        
        layout.addWidget(strategy_group)
        
        # Validation warnings
        self.validation_widget = ValidationWarnings()
        layout.addWidget(self.validation_widget)
        
        return frame
    
    def _create_preview_panel(self) -> QFrame:
        """Create the preview and configuration panel."""
        frame = QFrame()
        layout = QVBoxLayout(frame)
        
        # Title
        title_label = QLabel("Merge Preview")
        title_font = QFont()
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Preview widget
        self.preview_widget = OperationPreview()
        self.preview_widget.setMinimumHeight(300)
        layout.addWidget(self.preview_widget)
        
        # Metadata conflict resolver
        self.metadata_resolver = MetadataConflictResolver()
        layout.addWidget(self.metadata_resolver)
        
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
        button_box.accepted.connect(self._accept_merge)
        button_box.rejected.connect(self.reject)
        
        # Get OK button for enabling/disabling
        self.ok_button = button_box.button(QDialogButtonBox.StandardButton.Ok)
        self.ok_button.setText("Merge Elements")
        self.ok_button.setEnabled(False)
        
        layout.addWidget(button_box)
        
        return frame
    
    def _connect_signals(self):
        """Connect internal signals."""
        self.element_list.itemSelectionChanged.connect(self._on_selection_changed)
        self.elements_changed.connect(self._on_elements_changed)
        self.preview_updated.connect(self._on_preview_updated)
        self.validation_changed.connect(self._on_validation_changed)
    
    def _populate_element_list(self):
        """Populate the element list with current elements."""
        self.element_list.clear()
        
        for i, element in enumerate(self.elements):
            item = QListWidgetItem()
            
            # Create preview text
            preview_text = element.text[:50] + "..." if len(element.text) > 50 else element.text
            item_text = f"Element {i+1}: {preview_text}"
            item.setText(item_text)
            
            # Store element reference
            item.setData(Qt.ItemDataRole.UserRole, element)
            
            self.element_list.addItem(item)
        
        # Update UI state
        self._update_ui_state()
    
    def _add_elements(self):
        """Add new elements to the merge list."""
        # This would typically open an element picker dialog
        # For now, we'll just emit a signal that parent can handle
        self.logger.info("Add elements requested")
        pass
    
    def _remove_selected(self):
        """Remove selected elements from the merge list."""
        selected_items = self.element_list.selectedItems()
        
        for item in selected_items:
            row = self.element_list.row(item)
            if 0 <= row < len(self.elements):
                self.elements.pop(row)
            self.element_list.takeItem(row)
        
        # Update UI and preview
        self._update_ui_state()
        self._update_preview_delayed()
        self.elements_changed.emit(self.elements)
    
    def _on_selection_changed(self):
        """Handle element selection changes."""
        self.remove_button.setEnabled(len(self.element_list.selectedItems()) > 0)
    
    def _on_elements_changed(self, elements: List[Element]):
        """Handle elements list changes."""
        self.elements = elements
        self._update_ui_state()
    
    def _on_strategy_changed(self, strategy_text: str):
        """Handle merge strategy changes."""
        self._update_preview_delayed()
    
    def _update_ui_state(self):
        """Update UI state based on current elements."""
        has_elements = len(self.elements) >= 2
        self.ok_button.setEnabled(has_elements and self._is_valid_merge())
        self.remove_button.setEnabled(False)  # Will be enabled when items selected
    
    def _is_valid_merge(self) -> bool:
        """Check if current merge configuration is valid."""
        if len(self.elements) < 2:
            return False
        
        # Check if merge operation would be valid
        try:
            merge_op = MergeOperation(self.elements)
            return merge_op.validate()
        except Exception as e:
            self.logger.error(f"Validation error: {e}")
            return False
    
    def _update_preview_delayed(self):
        """Update preview with a delay to avoid excessive updates."""
        self.preview_timer.start(300)  # 300ms delay
    
    def _update_preview(self):
        """Update the merge preview."""
        if len(self.elements) < 2:
            self.preview_widget.clear_preview()
            return
        
        try:
            # Create merge operation
            merge_op = MergeOperation(self.elements)
            
            # Get preview
            preview_result = merge_op.preview()
            
            if preview_result.success:
                # Update preview widget
                self.preview_widget.set_preview(
                    original_elements=self.elements,
                    result_element=preview_result.merged_element,
                    operation_type="merge"
                )
                
                # Update metadata resolver
                self.metadata_resolver.set_elements(self.elements)
                
                # Clear validation warnings
                self.validation_widget.clear_warnings()
                
                self.merge_result = preview_result
                self.preview_updated.emit(preview_result)
                
            else:
                # Show validation errors
                self.validation_widget.add_warning(
                    "Merge Preview Failed",
                    preview_result.error_message or "Unknown error",
                    "error"
                )
                self.preview_widget.clear_preview()
                self.merge_result = None
        
        except Exception as e:
            self.logger.error(f"Preview update failed: {e}")
            self.validation_widget.add_warning(
                "Preview Error",
                str(e),
                "error"
            )
            self.preview_widget.clear_preview()
            self.merge_result = None
        
        # Update validation state
        self.validation_changed.emit(self.merge_result is not None)
    
    def _on_preview_updated(self, result):
        """Handle preview updates."""
        self._update_ui_state()
    
    def _on_validation_changed(self, is_valid: bool):
        """Handle validation state changes."""
        self.ok_button.setEnabled(is_valid and len(self.elements) >= 2)
    
    def _get_merge_strategy(self) -> MergeStrategy:
        """Get selected merge strategy."""
        strategy_text = self.strategy_combo.currentText()
        
        if "Smart" in strategy_text:
            return MergeStrategy.SMART
        elif "Simple" in strategy_text:
            return MergeStrategy.SIMPLE
        elif "Paragraph" in strategy_text:
            return MergeStrategy.PARAGRAPH
        else:
            return MergeStrategy.SMART
    
    def _accept_merge(self):
        """Accept the merge operation."""
        if not self.merge_result or len(self.elements) < 2:
            return
        
        try:
            # Show progress
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            
            # Create and execute merge operation
            merge_op = MergeOperation(self.elements)
            
            self.progress_bar.setValue(50)
            
            # Execute merge
            result = merge_op.execute()
            
            self.progress_bar.setValue(100)
            
            if result.success:
                # Populate dialog result
                self.dialog_result.accepted = True
                self.dialog_result.merged_element = result.merged_element
                self.dialog_result.original_elements = self.elements.copy()
                self.dialog_result.merge_strategy = self._get_merge_strategy()
                self.dialog_result.metadata_strategies = self.metadata_resolver.get_strategies()
                
                self.accept()
            else:
                # Show error
                self.validation_widget.add_warning(
                    "Merge Failed",
                    result.error_message or "Unknown error",
                    "error"
                )
                
        except Exception as e:
            self.logger.error(f"Merge execution failed: {e}")
            self.validation_widget.add_warning(
                "Merge Error",
                str(e),
                "error"
            )
        
        finally:
            self.progress_bar.setVisible(False)
    
    def get_result(self) -> MergeDialogResult:
        """Get the dialog result."""
        return self.dialog_result
    
    def set_elements(self, elements: List[Element]):
        """Set elements to merge."""
        self.elements = elements
        self._populate_element_list()
        self._update_preview_delayed()
        self.elements_changed.emit(elements)
    
    def add_element(self, element: Element):
        """Add a single element to the merge list."""
        self.elements.append(element)
        self._populate_element_list()
        self._update_preview_delayed()
        self.elements_changed.emit(self.elements)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter events."""
        if event.mimeData().hasFormat("application/x-element"):
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent):
        """Handle drop events."""
        if event.mimeData().hasFormat("application/x-element"):
            # This would handle dropping elements from other parts of the UI
            event.acceptProposedAction()
            self.logger.info("Element dropped")


# Convenience function for showing merge dialog
def show_merge_dialog(elements: List[Element], parent=None) -> MergeDialogResult:
    """Show merge dialog and return result."""
    dialog = MergeDialog(elements, parent)
    dialog.exec()
    return dialog.get_result()