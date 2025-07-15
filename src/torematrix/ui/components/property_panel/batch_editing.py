"""Batch editing capabilities for modifying multiple elements simultaneously"""

from typing import List, Dict, Any, Optional, Set, Callable
from dataclasses import dataclass, field
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, QLabel,
    QPushButton, QCheckBox, QComboBox, QProgressBar, QTextEdit, QScrollArea,
    QSplitter, QTabWidget, QListWidget, QListWidgetItem, QFrame, QSpacerItem,
    QSizePolicy, QMessageBox, QDialogButtonBox, QDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread, QObject
from PyQt6.QtGui import QFont, QPixmap, QIcon

from .models import PropertyChange, ChangeType, PropertyMetadata
from .events import PropertyNotificationCenter, PropertyEventType
from .editors import PropertyEditorFactory, get_property_editor_factory


@dataclass
class BatchOperation:
    """Represents a batch operation to be applied to multiple elements"""
    property_name: str
    operation_type: str  # 'set', 'append', 'prepend', 'replace', 'clear'
    new_value: Any
    old_value: Optional[Any] = None
    target_elements: List[str] = field(default_factory=list)
    condition_func: Optional[Callable[[Any], bool]] = None
    description: str = ""
    
    def can_apply_to_element(self, element_id: str, current_value: Any) -> bool:
        """Check if operation can be applied to element"""
        if element_id not in self.target_elements:
            return False
        
        if self.condition_func:
            return self.condition_func(current_value)
        
        return True


@dataclass
class BatchEditContext:
    """Context information for batch editing session"""
    selected_elements: List[str]
    common_properties: Set[str]
    property_summaries: Dict[str, Dict[str, Any]]
    total_elements: int
    session_id: str = ""
    start_time: Optional[float] = None
    
    def get_property_value_counts(self, property_name: str) -> Dict[Any, int]:
        """Get count of different values for a property across elements"""
        summary = self.property_summaries.get(property_name, {})
        return summary.get('value_counts', {})
    
    def is_property_uniform(self, property_name: str) -> bool:
        """Check if property has same value across all elements"""
        value_counts = self.get_property_value_counts(property_name)
        return len(value_counts) <= 1


class BatchEditWorker(QObject):
    """Worker thread for performing batch operations"""
    
    # Signals
    progress_updated = pyqtSignal(int, str)  # progress percentage, status message
    operation_completed = pyqtSignal(str, bool, str)  # operation_id, success, message
    batch_completed = pyqtSignal(dict)  # summary statistics
    error_occurred = pyqtSignal(str, str)  # element_id, error_message
    
    def __init__(self):
        super().__init__()
        self.operations: List[BatchOperation] = []
        self.property_manager = None
        self.cancel_requested = False
        
    def set_property_manager(self, manager) -> None:
        """Set property manager for applying changes"""
        self.property_manager = manager
    
    def add_operation(self, operation: BatchOperation) -> None:
        """Add operation to batch"""
        self.operations.append(operation)
    
    def clear_operations(self) -> None:
        """Clear all pending operations"""
        self.operations.clear()
    
    def execute_batch(self) -> None:
        """Execute all batch operations"""
        if not self.operations:
            self.batch_completed.emit({'total_operations': 0, 'successful': 0, 'failed': 0})
            return
        
        self.cancel_requested = False
        total_ops = len(self.operations)
        successful = 0
        failed = 0
        
        for i, operation in enumerate(self.operations):
            if self.cancel_requested:
                break
            
            # Update progress
            progress = int((i / total_ops) * 100)
            self.progress_updated.emit(progress, f"Applying {operation.property_name}...")
            
            # Execute operation
            try:
                success = self._execute_operation(operation)
                if success:
                    successful += 1
                    self.operation_completed.emit(f"op_{i}", True, "Operation completed")
                else:
                    failed += 1
                    self.operation_completed.emit(f"op_{i}", False, "Operation failed")
            except Exception as e:
                failed += 1
                self.error_occurred.emit("batch", str(e))
        
        # Final progress update
        self.progress_updated.emit(100, "Batch operations completed")
        
        # Emit completion summary
        summary = {
            'total_operations': total_ops,
            'successful': successful,
            'failed': failed,
            'cancelled': self.cancel_requested
        }
        self.batch_completed.emit(summary)
    
    def _execute_operation(self, operation: BatchOperation) -> bool:
        """Execute a single batch operation"""
        if not self.property_manager:
            return False
        
        success_count = 0
        
        for element_id in operation.target_elements:
            try:
                # Get current value
                current_value = self.property_manager.get_property_value(element_id, operation.property_name)
                
                # Check if operation can be applied
                if not operation.can_apply_to_element(element_id, current_value):
                    continue
                
                # Apply operation based on type
                new_value = self._calculate_new_value(operation, current_value)
                
                # Set new value
                self.property_manager.set_property_value(
                    element_id, operation.property_name, new_value
                )
                
                success_count += 1
                
            except Exception as e:
                self.error_occurred.emit(element_id, str(e))
        
        return success_count > 0
    
    def _calculate_new_value(self, operation: BatchOperation, current_value: Any) -> Any:
        """Calculate new value based on operation type"""
        if operation.operation_type == 'set':
            return operation.new_value
        
        elif operation.operation_type == 'append':
            if isinstance(current_value, str):
                return current_value + str(operation.new_value)
            elif isinstance(current_value, list):
                return current_value + [operation.new_value]
            return operation.new_value
        
        elif operation.operation_type == 'prepend':
            if isinstance(current_value, str):
                return str(operation.new_value) + current_value
            elif isinstance(current_value, list):
                return [operation.new_value] + current_value
            return operation.new_value
        
        elif operation.operation_type == 'replace':
            if isinstance(current_value, str) and isinstance(operation.old_value, str):
                return current_value.replace(operation.old_value, str(operation.new_value))
            return operation.new_value
        
        elif operation.operation_type == 'clear':
            if isinstance(current_value, str):
                return ""
            elif isinstance(current_value, list):
                return []
            elif isinstance(current_value, dict):
                return {}
            return None
        
        return operation.new_value
    
    def cancel_batch(self) -> None:
        """Cancel batch execution"""
        self.cancel_requested = True


class BatchEditingPanel(QWidget):
    """Main panel for batch editing multiple elements"""
    
    # Signals
    batch_started = pyqtSignal(dict)  # batch context
    batch_completed = pyqtSignal(dict)  # summary
    property_batch_changed = pyqtSignal(str, list, Any)  # property_name, element_ids, new_value
    
    def __init__(self, notification_center: PropertyNotificationCenter):
        super().__init__()
        self.notification_center = notification_center
        self.property_manager = None
        self.factory = get_property_editor_factory()
        
        # Batch editing state
        self.selected_elements: List[str] = []
        self.batch_context: Optional[BatchEditContext] = None
        self.pending_operations: List[BatchOperation] = []
        
        # Worker thread
        self.worker_thread = QThread()
        self.worker = BatchEditWorker()
        self.worker.moveToThread(self.worker_thread)
        
        # Setup UI
        self._setup_ui()
        self._setup_worker_connections()
        
        # Connect notifications
        self.notification_center.register_listener(
            PropertyEventType.BATCH_UPDATE_START,
            self._on_batch_update_start
        )
        self.notification_center.register_listener(
            PropertyEventType.BATCH_UPDATE_END,
            self._on_batch_update_end
        )
    
    def _setup_ui(self) -> None:
        """Setup batch editing UI"""
        layout = QVBoxLayout(self)
        
        # Header with element selection info
        self._create_header(layout)
        
        # Main content area with tabs
        self.tab_widget = QTabWidget()
        
        # Property editing tab
        self.property_tab = self._create_property_tab()
        self.tab_widget.addTab(self.property_tab, "Property Editing")
        
        # Operation history tab
        self.history_tab = self._create_history_tab()
        self.tab_widget.addTab(self.history_tab, "Operation History")
        
        # Advanced operations tab
        self.advanced_tab = self._create_advanced_tab()
        self.tab_widget.addTab(self.advanced_tab, "Advanced Operations")
        
        layout.addWidget(self.tab_widget)
        
        # Progress and control area
        self._create_progress_area(layout)
    
    def _create_header(self, layout: QVBoxLayout) -> None:
        """Create header with selection info"""
        header_group = QGroupBox("Batch Editing")
        header_layout = QVBoxLayout(header_group)
        
        # Selection summary
        self.selection_label = QLabel("No elements selected")
        self.selection_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        header_layout.addWidget(self.selection_label)
        
        # Common properties info
        self.properties_label = QLabel("Common properties: None")
        header_layout.addWidget(self.properties_label)
        
        # Quick actions
        actions_layout = QHBoxLayout()
        
        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self._select_all_properties)
        
        self.clear_selection_btn = QPushButton("Clear Selection")
        self.clear_selection_btn.clicked.connect(self._clear_element_selection)
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._refresh_context)
        
        actions_layout.addWidget(self.select_all_btn)
        actions_layout.addWidget(self.clear_selection_btn)
        actions_layout.addWidget(self.refresh_btn)
        actions_layout.addStretch()
        
        header_layout.addLayout(actions_layout)
        layout.addWidget(header_group)
    
    def _create_property_tab(self) -> QWidget:
        """Create property editing tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Property selector
        prop_group = QGroupBox("Select Properties to Edit")
        prop_layout = QVBoxLayout(prop_group)
        
        self.property_list = QListWidget()
        self.property_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.property_list.itemSelectionChanged.connect(self._on_property_selection_changed)
        prop_layout.addWidget(self.property_list)
        
        layout.addWidget(prop_group)
        
        # Property editor area
        self.editor_scroll = QScrollArea()
        self.editor_widget = QWidget()
        self.editor_layout = QVBoxLayout(self.editor_widget)
        self.editor_scroll.setWidget(self.editor_widget)
        self.editor_scroll.setWidgetResizable(True)
        
        layout.addWidget(self.editor_scroll)
        
        return tab
    
    def _create_history_tab(self) -> QWidget:
        """Create operation history tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # History controls
        controls_layout = QHBoxLayout()
        
        self.undo_btn = QPushButton("Undo Last")
        self.undo_btn.clicked.connect(self._undo_last_operation)
        
        self.redo_btn = QPushButton("Redo")
        self.redo_btn.clicked.connect(self._redo_operation)
        
        self.clear_history_btn = QPushButton("Clear History")
        self.clear_history_btn.clicked.connect(self._clear_history)
        
        controls_layout.addWidget(self.undo_btn)
        controls_layout.addWidget(self.redo_btn)
        controls_layout.addWidget(self.clear_history_btn)
        controls_layout.addStretch()
        
        layout.addLayout(controls_layout)
        
        # History list
        self.history_list = QListWidget()
        layout.addWidget(self.history_list)
        
        return tab
    
    def _create_advanced_tab(self) -> QWidget:
        """Create advanced operations tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Operation type selector
        op_group = QGroupBox("Advanced Operations")
        op_layout = QGridLayout(op_group)
        
        op_layout.addWidget(QLabel("Operation Type:"), 0, 0)
        self.operation_combo = QComboBox()
        self.operation_combo.addItems(["Set Value", "Append Text", "Prepend Text", "Replace Text", "Clear Value"])
        op_layout.addWidget(self.operation_combo, 0, 1)
        
        # Conditional editing
        op_layout.addWidget(QLabel("Apply When:"), 1, 0)
        self.condition_combo = QComboBox()
        self.condition_combo.addItems(["Always", "Value Equals", "Value Contains", "Value Empty", "Value Not Empty"])
        op_layout.addWidget(self.condition_combo, 1, 1)
        
        layout.addWidget(op_group)
        
        # Script editor for complex operations
        script_group = QGroupBox("Custom Script (Advanced)")
        script_layout = QVBoxLayout(script_group)
        
        self.script_editor = QTextEdit()
        self.script_editor.setPlaceholderText(
            "Enter Python script for custom operations...\n"
            "Available variables: element_id, current_value, properties"
        )
        script_layout.addWidget(self.script_editor)
        
        script_controls = QHBoxLayout()
        self.validate_script_btn = QPushButton("Validate Script")
        self.run_script_btn = QPushButton("Run Script")
        
        script_controls.addWidget(self.validate_script_btn)
        script_controls.addWidget(self.run_script_btn)
        script_controls.addStretch()
        
        script_layout.addLayout(script_controls)
        layout.addWidget(script_group)
        
        return tab
    
    def _create_progress_area(self, layout: QVBoxLayout) -> None:
        """Create progress and control area"""
        progress_group = QGroupBox("Batch Operation Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Ready")
        progress_layout.addWidget(self.status_label)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.apply_btn = QPushButton("Apply Changes")
        self.apply_btn.clicked.connect(self._apply_batch_changes)
        self.apply_btn.setEnabled(False)
        
        self.preview_btn = QPushButton("Preview Changes")
        self.preview_btn.clicked.connect(self._preview_changes)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self._cancel_batch)
        self.cancel_btn.setVisible(False)
        
        button_layout.addWidget(self.preview_btn)
        button_layout.addWidget(self.apply_btn)
        button_layout.addWidget(self.cancel_btn)
        button_layout.addStretch()
        
        progress_layout.addLayout(button_layout)
        layout.addWidget(progress_group)
    
    def _setup_worker_connections(self) -> None:
        """Setup worker thread connections"""
        self.worker.progress_updated.connect(self._on_progress_updated)
        self.worker.operation_completed.connect(self._on_operation_completed)
        self.worker.batch_completed.connect(self._on_batch_completed)
        self.worker.error_occurred.connect(self._on_error_occurred)
        
        self.worker_thread.started.connect(self.worker.execute_batch)
    
    def set_property_manager(self, manager) -> None:
        """Set property manager"""
        self.property_manager = manager
        self.worker.set_property_manager(manager)
    
    def set_selected_elements(self, element_ids: List[str]) -> None:
        """Set selected elements for batch editing"""
        self.selected_elements = element_ids
        self._update_batch_context()
        self._update_ui_state()
    
    def _update_batch_context(self) -> None:
        """Update batch editing context"""
        if not self.selected_elements or not self.property_manager:
            self.batch_context = None
            return
        
        # Get common properties
        common_props = set()
        property_summaries = {}
        
        for i, element_id in enumerate(self.selected_elements):
            element_props = self.property_manager.get_element_properties(element_id)
            
            if i == 0:
                common_props = set(element_props.keys())
            else:
                common_props &= set(element_props.keys())
            
            # Build property summaries
            for prop_name, prop_value in element_props.items():
                if prop_name not in property_summaries:
                    property_summaries[prop_name] = {'value_counts': {}}
                
                value_counts = property_summaries[prop_name]['value_counts']
                value_key = str(prop_value)
                value_counts[value_key] = value_counts.get(value_key, 0) + 1
        
        # Create context
        self.batch_context = BatchEditContext(
            selected_elements=self.selected_elements,
            common_properties=common_props,
            property_summaries=property_summaries,
            total_elements=len(self.selected_elements)
        )
    
    def _update_ui_state(self) -> None:
        """Update UI based on current state"""
        if not self.batch_context:
            self.selection_label.setText("No elements selected")
            self.properties_label.setText("Common properties: None")
            self.property_list.clear()
            self.apply_btn.setEnabled(False)
            return
        
        # Update selection info
        count = len(self.selected_elements)
        self.selection_label.setText(f"{count} elements selected")
        
        # Update common properties
        common_count = len(self.batch_context.common_properties)
        self.properties_label.setText(f"Common properties: {common_count}")
        
        # Update property list
        self.property_list.clear()
        for prop_name in sorted(self.batch_context.common_properties):
            item = QListWidgetItem(prop_name)
            
            # Add value summary
            value_counts = self.batch_context.get_property_value_counts(prop_name)
            if len(value_counts) == 1:
                item.setText(f"{prop_name} (uniform)")
            else:
                item.setText(f"{prop_name} ({len(value_counts)} different values)")
            
            self.property_list.addItem(item)
    
    def _on_property_selection_changed(self) -> None:
        """Handle property selection change"""
        selected_items = self.property_list.selectedItems()
        if not selected_items:
            self._clear_property_editors()
            self.apply_btn.setEnabled(False)
            return
        
        # Create editors for selected properties
        self._create_property_editors([item.text().split(' ')[0] for item in selected_items])
        self.apply_btn.setEnabled(True)
    
    def _create_property_editors(self, property_names: List[str]) -> None:
        """Create editors for selected properties"""
        # Clear existing editors
        self._clear_property_editors()
        
        for prop_name in property_names:
            if not self.batch_context:
                continue
            
            # Get sample value for editor creation
            sample_value = None
            value_counts = self.batch_context.get_property_value_counts(prop_name)
            if value_counts:
                sample_value = list(value_counts.keys())[0]
            
            # Create editor
            editor = self.factory.create_editor(value=sample_value)
            if editor:
                # Create property editor group
                prop_group = QGroupBox(f"Edit {prop_name}")
                prop_layout = QVBoxLayout(prop_group)
                
                # Value summary
                if self.batch_context.is_property_uniform(prop_name):
                    summary_text = f"Current value: {sample_value}"
                else:
                    count = len(value_counts)
                    summary_text = f"{count} different values across {self.batch_context.total_elements} elements"
                
                summary_label = QLabel(summary_text)
                summary_label.setWordWrap(True)
                prop_layout.addWidget(summary_label)
                
                # Editor widget
                prop_layout.addWidget(editor)
                
                # Store reference
                editor.setProperty('property_name', prop_name)
                
                self.editor_layout.addWidget(prop_group)
    
    def _clear_property_editors(self) -> None:
        """Clear all property editors"""
        while self.editor_layout.count():
            child = self.editor_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
    
    def _apply_batch_changes(self) -> None:
        """Apply batch changes to selected elements"""
        if not self.batch_context:
            return
        
        # Collect operations from editors
        operations = self._collect_operations()
        if not operations:
            QMessageBox.information(self, "No Changes", "No property changes to apply.")
            return
        
        # Show confirmation dialog
        if not self._confirm_batch_operation(operations):
            return
        
        # Start batch operation
        self._start_batch_operation(operations)
    
    def _collect_operations(self) -> List[BatchOperation]:
        """Collect operations from property editors"""
        operations = []
        
        for i in range(self.editor_layout.count()):
            group_widget = self.editor_layout.itemAt(i).widget()
            if not isinstance(group_widget, QGroupBox):
                continue
            
            # Find editor in group
            editor = None
            for child in group_widget.findChildren(QWidget):
                if hasattr(child, 'get_value') and hasattr(child, 'property'):
                    prop_name = child.property('property_name')
                    if prop_name:
                        editor = child
                        break
            
            if editor:
                prop_name = editor.property('property_name')
                new_value = editor.get_value()
                
                operation = BatchOperation(
                    property_name=prop_name,
                    operation_type='set',
                    new_value=new_value,
                    target_elements=self.selected_elements.copy(),
                    description=f"Set {prop_name} to {new_value}"
                )
                operations.append(operation)
        
        return operations
    
    def _confirm_batch_operation(self, operations: List[BatchOperation]) -> bool:
        """Show confirmation dialog for batch operation"""
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Confirm Batch Operation")
        dialog.setIcon(QMessageBox.Icon.Question)
        
        message = f"Apply {len(operations)} operations to {len(self.selected_elements)} elements?\n\n"
        for op in operations[:5]:  # Show first 5 operations
            message += f"• {op.description}\n"
        
        if len(operations) > 5:
            message += f"... and {len(operations) - 5} more operations"
        
        dialog.setText(message)
        dialog.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        return dialog.exec() == QMessageBox.StandardButton.Yes
    
    def _start_batch_operation(self, operations: List[BatchOperation]) -> None:
        """Start batch operation"""
        # Setup worker
        self.worker.clear_operations()
        for operation in operations:
            self.worker.add_operation(operation)
        
        # Update UI for batch mode
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.cancel_btn.setVisible(True)
        self.apply_btn.setEnabled(False)
        
        # Start batch
        self.notification_center.start_batch_mode()
        self.batch_started.emit(self.batch_context.__dict__ if self.batch_context else {})
        
        # Start worker thread
        if not self.worker_thread.isRunning():
            self.worker_thread.start()
    
    def _on_progress_updated(self, percentage: int, message: str) -> None:
        """Handle progress update"""
        self.progress_bar.setValue(percentage)
        self.status_label.setText(message)
    
    def _on_operation_completed(self, operation_id: str, success: bool, message: str) -> None:
        """Handle operation completion"""
        pass  # Could update operation list or log
    
    def _on_batch_completed(self, summary: Dict[str, Any]) -> None:
        """Handle batch completion"""
        # End batch mode
        self.notification_center.end_batch_mode()
        
        # Update UI
        self.progress_bar.setVisible(False)
        self.cancel_btn.setVisible(False)
        self.apply_btn.setEnabled(True)
        
        # Show completion message
        total = summary.get('total_operations', 0)
        successful = summary.get('successful', 0)
        failed = summary.get('failed', 0)
        
        if failed == 0:
            message = f"Successfully applied {successful} operations to selected elements."
            QMessageBox.information(self, "Batch Operation Complete", message)
        else:
            message = f"Completed with {successful} successful and {failed} failed operations."
            QMessageBox.warning(self, "Batch Operation Complete", message)
        
        self.batch_completed.emit(summary)
        
        # Refresh context
        self._refresh_context()
    
    def _on_error_occurred(self, element_id: str, error_message: str) -> None:
        """Handle error during batch operation"""
        print(f"Error processing element {element_id}: {error_message}")
    
    def _preview_changes(self) -> None:
        """Preview changes before applying"""
        operations = self._collect_operations()
        if not operations:
            QMessageBox.information(self, "No Changes", "No property changes to preview.")
            return
        
        # Create preview dialog
        dialog = BatchPreviewDialog(operations, self.batch_context, self)
        dialog.exec()
    
    def _cancel_batch(self) -> None:
        """Cancel current batch operation"""
        self.worker.cancel_batch()
        self.status_label.setText("Cancelling...")
    
    def _select_all_properties(self) -> None:
        """Select all common properties"""
        self.property_list.selectAll()
    
    def _clear_element_selection(self) -> None:
        """Clear element selection"""
        self.set_selected_elements([])
    
    def _refresh_context(self) -> None:
        """Refresh batch context"""
        self._update_batch_context()
        self._update_ui_state()
    
    def _undo_last_operation(self) -> None:
        """Undo last batch operation"""
        # TODO: Implement undo functionality
        pass
    
    def _redo_operation(self) -> None:
        """Redo batch operation"""
        # TODO: Implement redo functionality
        pass
    
    def _clear_history(self) -> None:
        """Clear operation history"""
        self.history_list.clear()
    
    def _on_batch_update_start(self, event) -> None:
        """Handle batch update start"""
        pass
    
    def _on_batch_update_end(self, event) -> None:
        """Handle batch update end"""
        pass


class BatchPreviewDialog(QDialog):
    """Dialog for previewing batch changes before applying"""
    
    def __init__(self, operations: List[BatchOperation], context: BatchEditContext, parent=None):
        super().__init__(parent)
        self.operations = operations
        self.context = context
        
        self.setWindowTitle("Preview Batch Changes")
        self.setModal(True)
        self.resize(600, 400)
        
        self._setup_ui()
        self._populate_preview()
    
    def _setup_ui(self) -> None:
        """Setup preview dialog UI"""
        layout = QVBoxLayout(self)
        
        # Summary
        summary_label = QLabel(
            f"Preview of {len(self.operations)} operations on {self.context.total_elements} elements:"
        )
        summary_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(summary_label)
        
        # Preview tree
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        layout.addWidget(self.preview_text)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def _populate_preview(self) -> None:
        """Populate preview with operation details"""
        text = ""
        
        for i, operation in enumerate(self.operations, 1):
            text += f"{i}. {operation.description}\n"
            text += f"   Property: {operation.property_name}\n"
            text += f"   New Value: {operation.new_value}\n"
            text += f"   Affected Elements: {len(operation.target_elements)}\n\n"
        
        self.preview_text.setPlainText(text)


# Export batch editing components
__all__ = [
    'BatchOperation',
    'BatchEditContext',
    'BatchEditWorker',
    'BatchEditingPanel',
    'BatchPreviewDialog'
]
