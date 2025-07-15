"""Integration bridge for seamless element list and editor workflow

This module provides the bridge between element lists and inline editors,
enabling seamless editing workflow with proper state management and event handling.
"""

from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
import weakref

try:
    from PyQt6.QtWidgets import QWidget
    from PyQt6.QtCore import QObject, pyqtSignal, QTimer
except ImportError:
    # Mock classes for environments without PyQt6
    class QWidget:
        def __init__(self, parent=None):
            pass
            
    class QObject:
        def __init__(self, parent=None):
            pass
            
    class QTimer:
        def __init__(self):
            self.timeout = MockSignal()
        def start(self, ms): pass
        def stop(self): pass
        def isActive(self): return False
        
    class MockSignal:
        def connect(self, func): pass
            
    def pyqtSignal(*args):
        return lambda: None

from .base import BaseEditor, EditorConfig


@dataclass
class EditRequest:
    """Request for editing an element"""
    element_id: str
    element_type: str
    current_value: Any
    position: tuple[int, int] = (0, 0)
    parent_widget: Optional[QWidget] = None
    config: Optional[EditorConfig] = None


class ElementEditorBridge(QObject):
    """Bridge between element lists and inline editors
    
    Coordinates the editing workflow:
    1. Receives edit requests from element lists
    2. Creates appropriate editors
    3. Manages editor lifecycle
    4. Handles edit completion and updates
    """
    
    # Signals
    edit_requested = pyqtSignal(str, str)  # element_id, element_type
    edit_started = pyqtSignal(str, object)  # element_id, editor
    edit_completed = pyqtSignal(str, object, bool)  # element_id, value, success
    edit_cancelled = pyqtSignal(str)  # element_id
    validation_failed = pyqtSignal(str, str)  # element_id, error_message
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Active editing sessions
        self.active_editors: Dict[str, BaseEditor] = {}
        self.edit_requests: Dict[str, EditRequest] = {}
        self.editor_weakrefs: Dict[str, weakref.ref] = {}
        
        # Editor factory function (set externally)
        self.editor_factory: Optional[Callable] = None
        
        # Performance tracking
        self.edit_statistics = {
            'total_edits': 0,
            'successful_edits': 0,
            'cancelled_edits': 0,
            'failed_edits': 0
        }
        
        # Auto-commit timer for batch operations
        self.auto_commit_timer = QTimer()
        if hasattr(self.auto_commit_timer, 'timeout'):
            self.auto_commit_timer.timeout.connect(self._process_auto_commits)
        self.pending_commits: Dict[str, float] = {}
    
    def set_editor_factory(self, factory: Callable):
        """Set the editor factory function
        
        Args:
            factory: Function that creates editors: factory(element_id, element_type, parent, config) -> BaseEditor
        """
        self.editor_factory = factory
    
    def request_edit(self, element_id: str, element_type: str, current_value: Any = None,
                    position: tuple[int, int] = (0, 0), parent_widget: QWidget = None,
                    config: EditorConfig = None) -> bool:
        """Request editing for an element
        
        Args:
            element_id: Unique identifier for the element
            element_type: Type of element (text, number, etc.)
            current_value: Current value of the element
            position: Position for editor placement
            parent_widget: Parent widget for the editor
            config: Editor configuration
            
        Returns:
            True if edit request was accepted, False otherwise
        """
        # Check if already editing this element
        if element_id in self.active_editors:
            return False
        
        # Create edit request
        request = EditRequest(
            element_id=element_id,
            element_type=element_type,
            current_value=current_value,
            position=position,
            parent_widget=parent_widget,
            config=config or EditorConfig()
        )
        
        # Store request
        self.edit_requests[element_id] = request
        
        # Emit signal for external listeners
        self.edit_requested.emit(element_id, element_type)
        
        # Create editor if factory is available
        if self.editor_factory:
            return self._create_editor_for_request(request)
        
        return True
    
    def _create_editor_for_request(self, request: EditRequest) -> bool:
        """Create editor for edit request"""
        try:
            # Create editor using factory
            editor = self.editor_factory(
                request.element_id,
                request.element_type,
                request.parent_widget,
                request.config
            )
            
            if not editor:
                return False
            
            # Store editor references
            self.active_editors[request.element_id] = editor
            self.editor_weakrefs[request.element_id] = weakref.ref(
                editor, lambda ref: self._cleanup_editor(request.element_id)
            )
            
            # Connect editor signals
            self._connect_editor_signals(editor, request.element_id)
            
            # Start editing
            editor.set_value(request.current_value)
            editor.start_editing(request.current_value)
            
            # Update statistics
            self.edit_statistics['total_edits'] += 1
            
            # Emit signals
            self.edit_started.emit(request.element_id, editor)
            
            return True
            
        except Exception as e:
            # Cleanup on failure
            self._cleanup_edit_request(request.element_id)
            return False
    
    def _connect_editor_signals(self, editor: BaseEditor, element_id: str):
        """Connect editor signals to bridge handlers"""
        editor.editing_finished.connect(
            lambda success: self._handle_editing_finished(element_id, success)
        )
        editor.value_changed.connect(
            lambda value: self._handle_value_changed(element_id, value)
        )
        editor.validation_failed.connect(
            lambda msg: self._handle_validation_failed(element_id, msg)
        )
        editor.save_requested.connect(
            lambda: self._handle_save_requested(element_id)
        )
        editor.cancel_requested.connect(
            lambda: self._handle_cancel_requested(element_id)
        )
    
    def _handle_editing_finished(self, element_id: str, success: bool):
        """Handle editor finishing editing"""
        if element_id not in self.active_editors:
            return
        
        editor = self.active_editors[element_id]
        value = editor.get_value()
        
        # Update statistics
        if success:
            self.edit_statistics['successful_edits'] += 1
        else:
            self.edit_statistics['cancelled_edits'] += 1
        
        # Emit completion signal
        self.edit_completed.emit(element_id, value, success)
        
        # Cleanup
        self._cleanup_edit_request(element_id)
    
    def _handle_value_changed(self, element_id: str, value: Any):
        """Handle editor value changes"""
        if element_id not in self.edit_requests:
            return
        
        request = self.edit_requests[element_id]
        
        # Schedule auto-commit if enabled
        if request.config and request.config.auto_commit:
            import time
            self.pending_commits[element_id] = time.time() + (request.config.commit_delay / 1000.0)
            
            if hasattr(self.auto_commit_timer, 'isActive') and not self.auto_commit_timer.isActive():
                self.auto_commit_timer.start(100)  # Check every 100ms
    
    def _handle_validation_failed(self, element_id: str, error_message: str):
        """Handle validation failures"""
        self.validation_failed.emit(element_id, error_message)
        self.edit_statistics['failed_edits'] += 1
    
    def _handle_save_requested(self, element_id: str):
        """Handle explicit save requests"""
        if element_id in self.active_editors:
            editor = self.active_editors[element_id]
            success = editor.save()
            if success:
                self._handle_editing_finished(element_id, True)
    
    def _handle_cancel_requested(self, element_id: str):
        """Handle cancel requests"""
        if element_id in self.active_editors:
            editor = self.active_editors[element_id]
            editor.cancel_editing()
            self.edit_cancelled.emit(element_id)
            self._cleanup_edit_request(element_id)
    
    def _process_auto_commits(self):
        """Process pending auto-commits"""
        import time
        current_time = time.time()
        
        ready_commits = [
            element_id for element_id, commit_time in self.pending_commits.items()
            if current_time >= commit_time
        ]
        
        for element_id in ready_commits:
            if element_id in self.active_editors:
                editor = self.active_editors[element_id]
                if editor.is_dirty():
                    success = editor.save()
                    if success:
                        self._handle_editing_finished(element_id, True)
            
            # Remove from pending commits
            self.pending_commits.pop(element_id, None)
        
        # Stop timer if no more pending commits
        if not self.pending_commits and hasattr(self.auto_commit_timer, 'stop'):
            self.auto_commit_timer.stop()
    
    def _cleanup_edit_request(self, element_id: str):
        """Cleanup edit request and associated resources"""
        # Remove from active editors
        if element_id in self.active_editors:
            del self.active_editors[element_id]
        
        # Remove edit request
        if element_id in self.edit_requests:
            del self.edit_requests[element_id]
        
        # Remove weak reference
        if element_id in self.editor_weakrefs:
            del self.editor_weakrefs[element_id]
        
        # Remove from pending commits
        self.pending_commits.pop(element_id, None)
    
    def _cleanup_editor(self, element_id: str):
        """Cleanup after editor is garbage collected"""
        self._cleanup_edit_request(element_id)
    
    # Public API methods
    
    def create_editor(self, element_id: str, element_type: str, parent: QWidget,
                     config: EditorConfig = None) -> Optional[BaseEditor]:
        """Create editor directly (used by editing system)"""
        if self.editor_factory:
            return self.editor_factory(element_id, element_type, parent, config)
        return None
    
    def get_active_editor(self, element_id: str) -> Optional[BaseEditor]:
        """Get active editor for element"""
        return self.active_editors.get(element_id)
    
    def is_editing(self, element_id: str) -> bool:
        """Check if element is currently being edited"""
        return element_id in self.active_editors
    
    def cancel_edit(self, element_id: str) -> bool:
        """Cancel editing for specific element"""
        if element_id in self.active_editors:
            self._handle_cancel_requested(element_id)
            return True
        return False
    
    def cancel_all_edits(self):
        """Cancel all active edits"""
        for element_id in list(self.active_editors.keys()):
            self.cancel_edit(element_id)
    
    def save_all_edits(self) -> Dict[str, bool]:
        """Save all active edits
        
        Returns:
            Dictionary mapping element_id to save success status
        """
        results = {}
        
        for element_id, editor in self.active_editors.items():
            try:
                success = editor.save()
                results[element_id] = success
                
                if success:
                    self._handle_editing_finished(element_id, True)
            except Exception:
                results[element_id] = False
        
        return results
    
    def get_edit_statistics(self) -> Dict[str, int]:
        """Get editing statistics"""
        return self.edit_statistics.copy()
    
    def reset_statistics(self):
        """Reset editing statistics"""
        self.edit_statistics = {
            'total_edits': 0,
            'successful_edits': 0,
            'cancelled_edits': 0,
            'failed_edits': 0
        }


# Export public API
__all__ = [
    'ElementEditorBridge',
    'EditRequest'
]