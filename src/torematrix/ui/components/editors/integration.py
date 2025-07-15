<<<<<<< HEAD
=======
<<<<<<< HEAD
"""Element list integration bridge for seamless editing workflow"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass


@dataclass
class ElementEditContext:
    """Context information for element editing"""
    element_id: str
    element_type: str
    content: str
    metadata: Dict[str, Any]
    validation_rules: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'element_id': self.element_id,
            'element_type': self.element_type,
            'content': self.content,
            'metadata': self.metadata,
            'validation_rules': self.validation_rules
        }


class ElementEditorBridge(QObject):
    """Bridge between element list and inline editors
    
    Features:
    - Seamless integration with element list
    - Automatic editor type detection
    - Validation and error handling
    - State synchronization
    - Performance optimization
=======
>>>>>>> origin/main
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
<<<<<<< HEAD
            self.timeout = MockSignal()
        def start(self, ms): pass
        def stop(self): pass
        def isActive(self): return False
        
    class MockSignal:
        def connect(self, func): pass
=======
            pass
        def start(self, ms): pass
        def stop(self): pass
        def timeout(self): return lambda: None
>>>>>>> origin/main
            
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
<<<<<<< HEAD
=======
>>>>>>> origin/main
>>>>>>> origin/main
    """
    
    # Signals
    edit_requested = pyqtSignal(str, str)  # element_id, element_type
<<<<<<< HEAD
=======
<<<<<<< HEAD
    edit_completed = pyqtSignal(str, str, bool)  # element_id, new_content, success
    validation_failed = pyqtSignal(str, str)  # element_id, error_message
    editor_created = pyqtSignal(str, str)  # element_id, editor_type
    editor_destroyed = pyqtSignal(str)  # element_id
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_editors: Dict[str, Any] = {}
        self.element_contexts: Dict[str, ElementEditContext] = {}
        self.editor_factory = None
        self.validation_manager = None
        self.state_manager = None
        
        # Performance tracking
        self.edit_session_start_times: Dict[str, float] = {}
        self.metrics = {
            'total_edits': 0,
            'successful_edits': 0,
            'failed_edits': 0,
            'average_edit_time': 0.0
        }
    
    def set_editor_factory(self, factory):
        """Set editor factory for creating editors"""
        self.editor_factory = factory
    
    def set_validation_manager(self, manager):
        """Set validation manager for content validation"""
        self.validation_manager = manager
    
    def set_state_manager(self, manager):
        """Set state manager for persistence"""
        self.state_manager = manager
    
    def request_edit(self, element_id: str, element_type: str, 
                    current_content: str, metadata: Dict[str, Any] = None):
        """Request editing for specific element
        
        Args:
            element_id: Unique element identifier
            element_type: Type of element (text, rich_text, code, etc.)
            current_content: Current element content
            metadata: Additional element metadata
        """
        import time
        
        # Track edit session start
        self.edit_session_start_times[element_id] = time.time()
        self.metrics['total_edits'] += 1
        
        # Create element context
        context = ElementEditContext(
            element_id=element_id,
            element_type=element_type,
            content=current_content,
            metadata=metadata or {},
            validation_rules=self._get_validation_rules(element_type)
        )
        
        self.element_contexts[element_id] = context
        
        # Create appropriate editor
        editor = self._create_editor_for_element(context)
        if not editor:
            self.validation_failed.emit(element_id, "Failed to create editor")
            return
        
        self.active_editors[element_id] = editor
        
        # Configure editor for element
        self._configure_editor(editor, context)
        
        # Start editing
        try:
            editor.start_editing(current_content)
            self.edit_requested.emit(element_id, element_type)
            self.editor_created.emit(element_id, element_type)
        except Exception as e:
            self.validation_failed.emit(element_id, f"Failed to start editing: {str(e)}")
            self._cleanup_editor(element_id)
    
    def _create_editor_for_element(self, context: ElementEditContext):
        """Create appropriate editor for element type
        
        Args:
            context: Element editing context
            
        Returns:
            Editor instance or None if creation failed
        """
        if not self.editor_factory:
            # Fallback to basic editor creation
            return self._create_fallback_editor(context)
        
        try:
            # Use factory to create editor
            from .factory import EditorType
            
            # Map element types to editor types
            editor_type_mapping = {
                'text': EditorType.INLINE,
                'rich_text': EditorType.RICH_TEXT,
                'code': EditorType.CODE,
                'formula': EditorType.FORMULA,
                'markdown': EditorType.MARKDOWN
            }
            
            editor_type = editor_type_mapping.get(
                context.element_type, 
                EditorType.INLINE
            )
            
            return self.editor_factory.create_editor(
                editor_type, 
                config={'element_context': context.to_dict()}
            )
            
        except Exception:
            return self._create_fallback_editor(context)
    
    def _create_fallback_editor(self, context: ElementEditContext):
        """Create fallback editor when factory is unavailable
        
        Args:
            context: Element editing context
            
        Returns:
            Basic editor instance
        """
        try:
            # Import advanced inline editor as fallback
            from .complete_system import CompleteInlineEditor
            return CompleteInlineEditor()
        except ImportError:
            try:
                # Try basic inline editor
                from .inline import InlineEditor
                return InlineEditor()
            except ImportError:
                return None
    
    def _configure_editor(self, editor, context: ElementEditContext):
        """Configure editor for specific element
        
        Args:
            editor: Editor instance to configure
            context: Element editing context
        """
        # Set element context
        if hasattr(editor, 'set_element_context'):
            editor.set_element_context(context.element_id, context.element_type)
        
        # Configure validation
        if hasattr(editor, 'set_validation_rules'):
            editor.set_validation_rules(context.validation_rules)
        
        # Configure auto-save
        if hasattr(editor, 'enable_auto_save'):
            editor.enable_auto_save(f"{context.element_type}_{context.element_id}")
        
        # Configure for element type
        if hasattr(editor, 'configure_for_element_type'):
            editor.configure_for_element_type(context.element_type)
        
        # Connect signals
        if hasattr(editor, 'editing_finished'):
            editor.editing_finished.connect(
                lambda success: self._on_editing_finished(context.element_id, success)
            )
        
        if hasattr(editor, 'content_changed'):
            editor.content_changed.connect(
                lambda content: self._on_content_changed(context.element_id, content)
            )
        
        if hasattr(editor, 'validation_failed'):
            editor.validation_failed.connect(
                lambda msg: self.validation_failed.emit(context.element_id, msg)
            )
    
    def _on_editing_finished(self, element_id: str, success: bool):
        """Handle editing completion
        
        Args:
            element_id: Element identifier
            success: Whether editing completed successfully
        """
        import time
        
        # Calculate edit duration
        if element_id in self.edit_session_start_times:
            duration = time.time() - self.edit_session_start_times[element_id]
            self._update_metrics(duration, success)
            del self.edit_session_start_times[element_id]
        
        if element_id in self.active_editors:
            editor = self.active_editors[element_id]
            content = ""
            
            if success:
                # Get final content
                if hasattr(editor, 'get_content'):
                    content = editor.get_content()
                elif hasattr(editor, 'toPlainText'):
                    content = editor.toPlainText()
                
                # Validate final content
                if self.validation_manager:
                    validation_result = self.validation_manager.validate_content(
                        element_id, content, self.element_contexts[element_id].element_type
                    )
                    if not validation_result.is_valid:
                        self.validation_failed.emit(element_id, validation_result.message)
                        return
                
                # Save state if manager available
                if self.state_manager:
                    self.state_manager.save_element_state(element_id, {
                        'content': content,
                        'metadata': self.element_contexts[element_id].metadata,
                        'last_edited': time.time()
                    })
                
                self.edit_completed.emit(element_id, content, True)
            else:
                self.edit_completed.emit(element_id, "", False)
            
            # Cleanup
            self._cleanup_editor(element_id)
    
    def _on_content_changed(self, element_id: str, content: str):
        """Handle content changes during editing
        
        Args:
            element_id: Element identifier
            content: New content
        """
        # Update context with new content
        if element_id in self.element_contexts:
            self.element_contexts[element_id].content = content
        
        # Trigger real-time validation if enabled
        if self.validation_manager and hasattr(self.validation_manager, 'validate_real_time'):
            self.validation_manager.validate_real_time(element_id, content)
    
    def _cleanup_editor(self, element_id: str):
        """Clean up editor resources
        
        Args:
            element_id: Element identifier
        """
        if element_id in self.active_editors:
            editor = self.active_editors[element_id]
            
            # Disable auto-save
            if hasattr(editor, 'disable_auto_save'):
                editor.disable_auto_save()
            
            # Disconnect signals
            if hasattr(editor, 'editing_finished'):
                try:
                    editor.editing_finished.disconnect()
                except TypeError:
                    pass  # Signal not connected
            
            # Clean up editor
            if hasattr(editor, 'cleanup'):
                editor.cleanup()
            
            del self.active_editors[element_id]
            self.editor_destroyed.emit(element_id)
        
        if element_id in self.element_contexts:
            del self.element_contexts[element_id]
    
    def _get_validation_rules(self, element_type: str) -> List[str]:
        """Get validation rules for element type
        
        Args:
            element_type: Type of element
            
        Returns:
            List of validation rule names
        """
        validation_rules = {
            'text': ['required', 'max_length:10000'],
            'rich_text': ['required', 'max_length:50000', 'valid_html'],
            'code': ['valid_syntax', 'max_length:20000'],
            'formula': ['valid_formula', 'max_length:1000'],
            'markdown': ['valid_markdown', 'max_length:30000']
        }
        
        return validation_rules.get(element_type, ['required'])
    
    def _update_metrics(self, duration: float, success: bool):
        """Update performance metrics
        
        Args:
            duration: Edit session duration in seconds
            success: Whether edit was successful
        """
        if success:
            self.metrics['successful_edits'] += 1
        else:
            self.metrics['failed_edits'] += 1
        
        # Update average edit time
        total_edits = self.metrics['successful_edits'] + self.metrics['failed_edits']
        if total_edits > 0:
            current_avg = self.metrics['average_edit_time']
            self.metrics['average_edit_time'] = (
                (current_avg * (total_edits - 1) + duration) / total_edits
            )
    
    def get_active_editors(self) -> Dict[str, Any]:
        """Get currently active editors
        
        Returns:
            Dictionary of active editors
        """
        return self.active_editors.copy()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics
        
        Returns:
            Dictionary with performance metrics
        """
        return self.metrics.copy()
    
    def cancel_edit(self, element_id: str) -> bool:
        """Cancel editing for specific element
        
        Args:
            element_id: Element identifier
            
        Returns:
            True if cancellation successful
        """
        if element_id in self.active_editors:
            editor = self.active_editors[element_id]
            
            # Try to cancel editing gracefully
            if hasattr(editor, 'cancel_editing'):
                editor.cancel_editing()
            elif hasattr(editor, 'finish_editing'):
                editor.finish_editing(save=False)
            
            self._cleanup_editor(element_id)
            return True
        
        return False
    
    def force_save_all(self) -> Dict[str, bool]:
        """Force save all active editors
        
        Returns:
            Dictionary mapping element IDs to save success status
=======
>>>>>>> origin/main
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
<<<<<<< HEAD
=======
>>>>>>> origin/main
>>>>>>> origin/main
        """
        results = {}
        
        for element_id, editor in self.active_editors.items():
            try:
<<<<<<< HEAD
=======
<<<<<<< HEAD
                if hasattr(editor, 'force_save'):
                    results[element_id] = editor.force_save()
                elif hasattr(editor, 'finish_editing'):
                    editor.finish_editing(save=True)
                    results[element_id] = True
                else:
                    results[element_id] = False
=======
>>>>>>> origin/main
                success = editor.save()
                results[element_id] = success
                
                if success:
                    self._handle_editing_finished(element_id, True)
<<<<<<< HEAD
=======
>>>>>>> origin/main
>>>>>>> origin/main
            except Exception:
                results[element_id] = False
        
        return results
<<<<<<< HEAD
=======
<<<<<<< HEAD


class ElementListIntegration:
    """Integration with Element List component
    
    Provides seamless integration between element list widget
    and inline editing system with proper lifecycle management.
    """
    
    def __init__(self, element_list_widget, inline_editor_manager):
        self.element_list = element_list_widget
        self.editor_manager = inline_editor_manager
        self.bridge = ElementEditorBridge()
        self.integration_enabled = True
        
        self._setup_connections()
        self._setup_validation()
    
    def _setup_connections(self):
        """Setup signal connections between components"""
        # Element list signals
        if hasattr(self.element_list, 'edit_requested'):
            self.element_list.edit_requested.connect(self._on_element_edit_request)
        
        if hasattr(self.element_list, 'element_selected'):
            self.element_list.element_selected.connect(self._on_element_selected)
        
        if hasattr(self.element_list, 'element_double_clicked'):
            self.element_list.element_double_clicked.connect(self._on_element_double_clicked)
        
        # Editor bridge signals
        self.bridge.edit_completed.connect(self._on_edit_completed)
        self.bridge.validation_failed.connect(self._on_validation_failed)
        self.bridge.editor_created.connect(self._on_editor_created)
        self.bridge.editor_destroyed.connect(self._on_editor_destroyed)
    
    def _setup_validation(self):
        """Setup validation for integration"""
        # Set up editor factory if available
        try:
            from .factory import EditorFactory
            self.bridge.set_editor_factory(EditorFactory())
        except ImportError:
            pass  # Factory not available, will use fallback
        
        # Set up validation manager if available
        try:
            from ...validation.content import ContentValidationManager
            self.bridge.set_validation_manager(ContentValidationManager())
        except ImportError:
            pass  # Validation manager not available
        
        # Set up state manager if available
        try:
            from ...state.manager import StateManager
            self.bridge.set_state_manager(StateManager())
        except ImportError:
            pass  # State manager not available
    
    def _on_element_edit_request(self, element_id: str):
        """Handle edit request from element list
        
        Args:
            element_id: Element identifier to edit
        """
        if not self.integration_enabled:
            return
        
        element_data = self._get_element_data(element_id)
        if element_data:
            self.bridge.request_edit(
                element_id=element_id,
                element_type=element_data.get('type', 'text'),
                current_content=element_data.get('content', ''),
                metadata=element_data.get('metadata', {})
            )
    
    def _on_element_selected(self, element_id: str):
        """Handle element selection
        
        Args:
            element_id: Selected element identifier
        """
        # Update UI to show element details
        if hasattr(self.element_list, 'show_element_details'):
            self.element_list.show_element_details(element_id)
    
    def _on_element_double_clicked(self, element_id: str):
        """Handle element double-click for quick editing
        
        Args:
            element_id: Double-clicked element identifier
        """
        self._on_element_edit_request(element_id)
    
    def _on_edit_completed(self, element_id: str, new_content: str, success: bool):
        """Handle edit completion
        
        Args:
            element_id: Element identifier
            new_content: New element content
            success: Whether edit was successful
        """
        if success and self.integration_enabled:
            # Update element in list
            if hasattr(self.element_list, 'update_element_content'):
                self.element_list.update_element_content(element_id, new_content)
            
            # Trigger state save
            if hasattr(self.element_list, 'save_state'):
                self.element_list.save_state()
            
            # Update UI
            if hasattr(self.element_list, 'refresh_element_display'):
                self.element_list.refresh_element_display(element_id)
    
    def _on_validation_failed(self, element_id: str, error_message: str):
        """Handle validation failure
        
        Args:
            element_id: Element identifier
            error_message: Validation error message
        """
        # Show error to user
        if hasattr(self.element_list, 'show_validation_error'):
            self.element_list.show_validation_error(element_id, error_message)
    
    def _on_editor_created(self, element_id: str, editor_type: str):
        """Handle editor creation
        
        Args:
            element_id: Element identifier
            editor_type: Type of editor created
        """
        # Update UI to show editing state
        if hasattr(self.element_list, 'set_element_editing_state'):
            self.element_list.set_element_editing_state(element_id, True)
    
    def _on_editor_destroyed(self, element_id: str):
        """Handle editor destruction
        
        Args:
            element_id: Element identifier
        """
        # Update UI to show normal state
        if hasattr(self.element_list, 'set_element_editing_state'):
            self.element_list.set_element_editing_state(element_id, False)
    
    def _get_element_data(self, element_id: str) -> Optional[Dict[str, Any]]:
        """Get element data from element list
        
        Args:
            element_id: Element identifier
            
        Returns:
            Element data dictionary or None
        """
        if hasattr(self.element_list, 'get_element_data'):
            return self.element_list.get_element_data(element_id)
        
        # Fallback method
        if hasattr(self.element_list, 'get_element'):
            element = self.element_list.get_element(element_id)
            if element:
                return {
                    'type': getattr(element, 'type', 'text'),
                    'content': getattr(element, 'content', ''),
                    'metadata': getattr(element, 'metadata', {})
                }
        
        return None
    
    def enable_integration(self):
        """Enable integration between element list and editors"""
        self.integration_enabled = True
    
    def disable_integration(self):
        """Disable integration between element list and editors"""
        self.integration_enabled = False
    
    def get_bridge_metrics(self) -> Dict[str, Any]:
        """Get bridge performance metrics
        
        Returns:
            Dictionary with metrics
        """
        return self.bridge.get_metrics()
    
    def cancel_all_edits(self) -> int:
        """Cancel all active editing sessions
        
        Returns:
            Number of edits cancelled
        """
        active_editors = self.bridge.get_active_editors()
        cancelled_count = 0
        
        for element_id in list(active_editors.keys()):
            if self.bridge.cancel_edit(element_id):
                cancelled_count += 1
        
        return cancelled_count
=======
>>>>>>> origin/main
    
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
<<<<<<< HEAD
]
=======
]
>>>>>>> origin/main
>>>>>>> origin/main
