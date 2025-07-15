# AGENT 4: Integration & Polish (Issue #23.4/#188)

## 🎯 Your Assignment
You are **Agent 4** implementing **Integration & Polish** for the Inline Editing System. Your focus is completing the system with full element list integration, comprehensive testing, accessibility features, and final production polish.

## 📋 Specific Tasks

### 1. Element List Integration
```python
# src/torematrix/ui/components/editors/integration.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

@dataclass
class ElementEditContext:
    element_id: str
    element_type: str
    content: str
    metadata: Dict[str, Any]
    validation_rules: List[str]

class ElementEditorBridge(QObject):
    """Bridge between element list and inline editors"""
    
    # Signals
    edit_requested = pyqtSignal(str, str)  # element_id, element_type
    edit_completed = pyqtSignal(str, str, bool)  # element_id, new_content, success
    validation_failed = pyqtSignal(str, str)  # element_id, error_message
    
    def __init__(self):
        super().__init__()
        self.active_editors: Dict[str, Any] = {}
        self.element_contexts: Dict[str, ElementEditContext] = {}
    
    def request_edit(self, element_id: str, element_type: str, 
                    current_content: str, metadata: Dict[str, Any] = None):
        """Request editing for specific element"""
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
        self.active_editors[element_id] = editor
        
        # Configure editor for element
        self._configure_editor(editor, context)
        
        # Start editing
        editor.start_editing(current_content)
        
        self.edit_requested.emit(element_id, element_type)
    
    def _create_editor_for_element(self, context: ElementEditContext):
        """Create appropriate editor for element type"""
        from ..text import EnhancedTextEdit
        from ..diff import DiffDisplayWidget
        from ..autosave import AutoSaveManager
        
        if context.element_type == 'text':
            from .advanced_inline import AdvancedInlineEditor
            editor = AdvancedInlineEditor()
        elif context.element_type == 'code':
            from .code_editor import CodeInlineEditor
            editor = CodeInlineEditor()
        elif context.element_type == 'formula':
            from .formula_editor import FormulaInlineEditor
            editor = FormulaInlineEditor()
        else:
            # Default to advanced inline editor
            from .advanced_inline import AdvancedInlineEditor
            editor = AdvancedInlineEditor()
        
        return editor
    
    def _configure_editor(self, editor, context: ElementEditContext):
        """Configure editor for specific element"""
        # Set element context
        editor.set_element_context(context.element_id, context.element_type)
        
        # Configure validation
        if hasattr(editor, 'set_validation_rules'):
            editor.set_validation_rules(context.validation_rules)
        
        # Configure auto-save
        if hasattr(editor, 'enable_auto_save'):
            editor.enable_auto_save(f"{context.element_type}_{context.element_id}")
        
        # Connect signals
        editor.editing_finished.connect(
            lambda success: self._on_editing_finished(context.element_id, success)
        )
        editor.content_changed.connect(
            lambda content: self._on_content_changed(context.element_id, content)
        )
    
    def _on_editing_finished(self, element_id: str, success: bool):
        """Handle editing completion"""
        if element_id in self.active_editors:
            editor = self.active_editors[element_id]
            content = editor.get_content() if success else ""
            
            if success:
                # Validate final content
                validation_result = self._validate_content(element_id, content)
                if validation_result.is_valid:
                    self.edit_completed.emit(element_id, content, True)
                else:
                    self.validation_failed.emit(element_id, validation_result.message)
                    return
            
            # Cleanup
            self._cleanup_editor(element_id)
    
    def _cleanup_editor(self, element_id: str):
        """Clean up editor resources"""
        if element_id in self.active_editors:
            editor = self.active_editors[element_id]
            if hasattr(editor, 'disable_auto_save'):
                editor.disable_auto_save()
            del self.active_editors[element_id]
        
        if element_id in self.element_contexts:
            del self.element_contexts[element_id]

class ElementListIntegration:
    """Integration with Element List component"""
    
    def __init__(self, element_list_widget, inline_editor_manager):
        self.element_list = element_list_widget
        self.editor_manager = inline_editor_manager
        self.bridge = ElementEditorBridge()
        self._setup_connections()
    
    def _setup_connections(self):
        """Setup signal connections"""
        # Element list signals
        if hasattr(self.element_list, 'edit_requested'):
            self.element_list.edit_requested.connect(self._on_element_edit_request)
        
        # Editor bridge signals
        self.bridge.edit_completed.connect(self._on_edit_completed)
        self.bridge.validation_failed.connect(self._on_validation_failed)
    
    def _on_element_edit_request(self, element_id: str):
        """Handle edit request from element list"""
        element_data = self.element_list.get_element_data(element_id)
        if element_data:
            self.bridge.request_edit(
                element_id=element_id,
                element_type=element_data.get('type', 'text'),
                current_content=element_data.get('content', ''),
                metadata=element_data.get('metadata', {})
            )
    
    def _on_edit_completed(self, element_id: str, new_content: str, success: bool):
        """Handle edit completion"""
        if success:
            # Update element in list
            self.element_list.update_element_content(element_id, new_content)
            
            # Trigger state save
            if hasattr(self.element_list, 'save_state'):
                self.element_list.save_state()
```

### 2. Property Panel Integration
```python
# src/torematrix/ui/integration/property_panel.py
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QTextEdit, QTabWidget)
from PyQt6.QtCore import pyqtSignal, QObject
from typing import Dict, Any, Optional

class PropertyPanelEditor(QWidget):
    """Alternative editing interface in property panel"""
    
    content_changed = pyqtSignal(str, str)  # element_id, content
    edit_mode_changed = pyqtSignal(str, bool)  # element_id, is_editing
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_element_id = None
        self.is_editing = False
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup property panel editor UI"""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        self.element_label = QLabel("No element selected")
        self.edit_btn = QPushButton("Edit")
        self.edit_btn.clicked.connect(self._toggle_edit_mode)
        
        header_layout.addWidget(self.element_label)
        header_layout.addStretch()
        header_layout.addWidget(self.edit_btn)
        
        layout.addLayout(header_layout)
        
        # Tabbed editing interface
        self.tab_widget = QTabWidget()
        
        # Text content tab
        self.text_tab = QWidget()
        text_layout = QVBoxLayout(self.text_tab)
        
        self.content_edit = QTextEdit()
        self.content_edit.setMaximumHeight(200)
        self.content_edit.textChanged.connect(self._on_content_changed)
        text_layout.addWidget(self.content_edit)
        
        # Metadata tab
        self.metadata_tab = QWidget()
        metadata_layout = QVBoxLayout(self.metadata_tab)
        
        self.metadata_edit = QTextEdit()
        self.metadata_edit.setMaximumHeight(150)
        metadata_layout.addWidget(self.metadata_edit)
        
        # Properties tab
        self.properties_tab = QWidget()
        # Add property editing widgets
        
        self.tab_widget.addTab(self.text_tab, "Content")
        self.tab_widget.addTab(self.metadata_tab, "Metadata")
        self.tab_widget.addTab(self.properties_tab, "Properties")
        
        layout.addWidget(self.tab_widget)
        
        # Initially hide tabs
        self.tab_widget.hide()
    
    def set_element(self, element_id: str, element_data: Dict[str, Any]):
        """Set element for editing"""
        self.current_element_id = element_id
        self.element_label.setText(f"Element: {element_id}")
        
        # Populate content
        content = element_data.get('content', '')
        self.content_edit.setPlainText(content)
        
        # Populate metadata
        metadata = element_data.get('metadata', {})
        self.metadata_edit.setPlainText(str(metadata))
        
        # Show interface
        self.tab_widget.show()
    
    def _toggle_edit_mode(self):
        """Toggle between edit and view modes"""
        self.is_editing = not self.is_editing
        
        if self.is_editing:
            self.edit_btn.setText("Save")
            self.content_edit.setReadOnly(False)
            self.metadata_edit.setReadOnly(False)
        else:
            self.edit_btn.setText("Edit")
            self.content_edit.setReadOnly(True)
            self.metadata_edit.setReadOnly(True)
            
            # Save changes
            if self.current_element_id:
                content = self.content_edit.toPlainText()
                self.content_changed.emit(self.current_element_id, content)
        
        self.edit_mode_changed.emit(self.current_element_id or "", self.is_editing)

class PropertyPanelIntegration:
    """Integration between inline editing and property panel"""
    
    def __init__(self, property_panel, inline_editor_bridge):
        self.property_panel = property_panel
        self.editor_bridge = inline_editor_bridge
        self._setup_synchronization()
    
    def _setup_synchronization(self):
        """Setup bidirectional synchronization"""
        # Property panel to inline editing
        if hasattr(self.property_panel, 'content_changed'):
            self.property_panel.content_changed.connect(
                self._sync_to_inline_editor
            )
        
        # Inline editing to property panel
        self.editor_bridge.edit_completed.connect(
            self._sync_to_property_panel
        )
    
    def _sync_to_inline_editor(self, element_id: str, content: str):
        """Sync changes from property panel to inline editor"""
        if element_id in self.editor_bridge.active_editors:
            editor = self.editor_bridge.active_editors[element_id]
            if hasattr(editor, 'update_content'):
                editor.update_content(content)
    
    def _sync_to_property_panel(self, element_id: str, content: str, success: bool):
        """Sync changes from inline editor to property panel"""
        if success and hasattr(self.property_panel, 'update_element_content'):
            self.property_panel.update_element_content(element_id, content)
```

### 3. State Management Integration
```python
# src/torematrix/ui/integration/state_sync.py
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from typing import Dict, Any, List
import json
from pathlib import Path

class StateManager:
    """Integration with global state management"""
    
    def __init__(self, state_store):
        self.state_store = state_store
        self.editor_states: Dict[str, Dict[str, Any]] = {}
        self.save_timer = QTimer()
        self.save_timer.setSingleShot(True)
        self.save_timer.timeout.connect(self._save_states)
    
    def save_editor_state(self, element_id: str, editor_state: Dict[str, Any]):
        """Save editor state to global state"""
        self.editor_states[element_id] = {
            'content': editor_state.get('content', ''),
            'cursor_position': editor_state.get('cursor_position', 0),
            'is_editing': editor_state.get('is_editing', False),
            'formatting': editor_state.get('formatting', ''),
            'timestamp': editor_state.get('timestamp', 0)
        }
        
        # Debounce saves
        self.save_timer.start(1000)  # Save after 1 second of inactivity
    
    def load_editor_state(self, element_id: str) -> Dict[str, Any]:
        """Load editor state from global state"""
        if element_id in self.editor_states:
            return self.editor_states[element_id].copy()
        
        # Try loading from persistent store
        try:
            state_data = self.state_store.get(f"editor_state_{element_id}")
            if state_data:
                return json.loads(state_data)
        except Exception:
            pass
        
        return {}
    
    def _save_states(self):
        """Save all editor states to persistent storage"""
        for element_id, state in self.editor_states.items():
            try:
                state_json = json.dumps(state)
                self.state_store.set(f"editor_state_{element_id}", state_json)
            except Exception as e:
                print(f"Failed to save editor state for {element_id}: {e}")

class EditorStateSync:
    """Synchronize editor states with global state management"""
    
    def __init__(self, editor_bridge, state_manager):
        self.editor_bridge = editor_bridge
        self.state_manager = state_manager
        self._setup_state_sync()
    
    def _setup_state_sync(self):
        """Setup state synchronization"""
        # Save state when editing completes
        self.editor_bridge.edit_completed.connect(self._save_editor_state)
        
        # Load state when editing starts
        self.editor_bridge.edit_requested.connect(self._load_editor_state)
    
    def _save_editor_state(self, element_id: str, content: str, success: bool):
        """Save editor state on completion"""
        if element_id in self.editor_bridge.active_editors:
            editor = self.editor_bridge.active_editors[element_id]
            
            if hasattr(editor, 'get_editor_state'):
                state = editor.get_editor_state()
                self.state_manager.save_editor_state(element_id, state)
    
    def _load_editor_state(self, element_id: str, element_type: str):
        """Load editor state on start"""
        state = self.state_manager.load_editor_state(element_id)
        
        if state and element_id in self.editor_bridge.active_editors:
            editor = self.editor_bridge.active_editors[element_id]
            
            if hasattr(editor, 'restore_editor_state'):
                editor.restore_editor_state(state)
```

### 4. Accessibility Features
```python
# src/torematrix/ui/components/editors/accessibility.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut, QAccessible
from typing import Dict, Any, List

class AccessibilityManager:
    """Manage accessibility features for inline editors"""
    
    def __init__(self):
        self.screen_reader_enabled = self._detect_screen_reader()
        self.high_contrast_mode = False
        self.large_font_mode = False
        self.keyboard_navigation = True
    
    def _detect_screen_reader(self) -> bool:
        """Detect if screen reader is active"""
        try:
            # Check for common screen readers
            import platform
            if platform.system() == "Windows":
                # Check for NVDA, JAWS, etc.
                return QAccessible.isActive()
            return False
        except Exception:
            return False
    
    def setup_accessibility(self, editor):
        """Setup accessibility features for editor"""
        # Set accessible name and description
        editor.setAccessibleName("Inline Text Editor")
        editor.setAccessibleDescription(
            "Editable text area for document elements. "
            "Use Tab to navigate, Enter to edit, Escape to cancel."
        )
        
        # Setup keyboard navigation
        if self.keyboard_navigation:
            self._setup_keyboard_navigation(editor)
        
        # Setup high contrast if needed
        if self.high_contrast_mode:
            self._apply_high_contrast(editor)
        
        # Setup screen reader support
        if self.screen_reader_enabled:
            self._setup_screen_reader_support(editor)
    
    def _setup_keyboard_navigation(self, editor):
        """Setup keyboard navigation shortcuts"""
        # Focus management
        editor.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        # Custom shortcuts for accessibility
        shortcuts = [
            (QKeySequence("Ctrl+E"), "Start editing"),
            (QKeySequence("Ctrl+S"), "Save and exit"),
            (QKeySequence("Ctrl+Q"), "Cancel editing"),
            (QKeySequence("F1"), "Show help")
        ]
        
        for shortcut, description in shortcuts:
            qs = QShortcut(shortcut, editor)
            qs.setWhatsThis(description)
    
    def _apply_high_contrast(self, editor):
        """Apply high contrast styling"""
        high_contrast_style = """
        QTextEdit {
            background-color: black;
            color: white;
            font-size: 14pt;
            border: 2px solid white;
        }
        QTextEdit:focus {
            border: 3px solid yellow;
        }
        """
        editor.setStyleSheet(high_contrast_style)
    
    def _setup_screen_reader_support(self, editor):
        """Setup screen reader specific features"""
        # Provide text descriptions for state changes
        if hasattr(editor, 'editing_started'):
            editor.editing_started.connect(
                lambda: self._announce("Editing started")
            )
        
        if hasattr(editor, 'editing_finished'):
            editor.editing_finished.connect(
                lambda success: self._announce(
                    "Editing completed" if success else "Editing cancelled"
                )
            )
    
    def _announce(self, message: str):
        """Announce message to screen reader"""
        try:
            QAccessible.updateAccessibility(
                QAccessibleEvent(QAccessible.Event.Alert, 0, message)
            )
        except Exception:
            pass

class AccessibleInlineEditor:
    """Mixin for accessibility features in inline editors"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.accessibility_manager = AccessibilityManager()
        self._setup_accessibility()
    
    def _setup_accessibility(self):
        """Setup accessibility features"""
        self.accessibility_manager.setup_accessibility(self)
        
        # Add status announcements
        self._add_status_announcements()
    
    def _add_status_announcements(self):
        """Add status announcements for screen readers"""
        # Connect to editing events
        if hasattr(self, 'editing_started'):
            self.editing_started.connect(
                lambda: self._announce_status("Editing mode activated")
            )
        
        if hasattr(self, 'validation_failed'):
            self.validation_failed.connect(
                lambda msg: self._announce_status(f"Validation error: {msg}")
            )
    
    def _announce_status(self, message: str):
        """Announce status to assistive technologies"""
        self.accessibility_manager._announce(message)
```

### 5. Error Handling and Recovery
```python
# src/torematrix/ui/components/editors/recovery.py
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QTextEdit, QMessageBox)
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from typing import Dict, Any, Optional, List
import traceback
import logging

class ErrorRecoveryManager(QObject):
    """Manage error recovery for inline editors"""
    
    recovery_performed = pyqtSignal(str, str)  # element_id, recovery_action
    critical_error = pyqtSignal(str, str)      # element_id, error_message
    
    def __init__(self):
        super().__init__()
        self.recovery_strategies: Dict[str, callable] = {
            'content_corruption': self._recover_from_content_corruption,
            'state_inconsistency': self._recover_from_state_inconsistency,
            'memory_error': self._recover_from_memory_error,
            'validation_failure': self._recover_from_validation_failure
        }
        self.error_log: List[Dict[str, Any]] = []
    
    def handle_error(self, element_id: str, error_type: str, 
                    error_data: Dict[str, Any]) -> bool:
        """Handle editor error and attempt recovery"""
        try:
            # Log error
            self._log_error(element_id, error_type, error_data)
            
            # Attempt recovery
            if error_type in self.recovery_strategies:
                recovery_func = self.recovery_strategies[error_type]
                success = recovery_func(element_id, error_data)
                
                if success:
                    self.recovery_performed.emit(element_id, error_type)
                    return True
            
            # If recovery fails, signal critical error
            self.critical_error.emit(element_id, str(error_data))
            return False
            
        except Exception as e:
            logging.error(f"Error in error recovery: {e}")
            return False
    
    def _log_error(self, element_id: str, error_type: str, error_data: Dict[str, Any]):
        """Log error for analysis"""
        error_entry = {
            'element_id': element_id,
            'error_type': error_type,
            'error_data': error_data,
            'timestamp': time.time(),
            'traceback': traceback.format_exc()
        }
        self.error_log.append(error_entry)
        
        # Keep only last 100 errors
        if len(self.error_log) > 100:
            self.error_log.pop(0)
    
    def _recover_from_content_corruption(self, element_id: str, 
                                       error_data: Dict[str, Any]) -> bool:
        """Recover from content corruption"""
        try:
            # Try to restore from auto-save
            if 'auto_save_manager' in error_data:
                auto_save_manager = error_data['auto_save_manager']
                recovery_data = auto_save_manager.get_recovery_data(element_id)
                
                if recovery_data:
                    # Restore content from auto-save
                    editor = error_data.get('editor')
                    if editor and hasattr(editor, 'set_content'):
                        editor.set_content(recovery_data['content'])
                        return True
            
            return False
        except Exception:
            return False
    
    def _recover_from_state_inconsistency(self, element_id: str,
                                        error_data: Dict[str, Any]) -> bool:
        """Recover from state inconsistency"""
        try:
            # Reset editor to clean state
            editor = error_data.get('editor')
            if editor and hasattr(editor, 'reset_state'):
                editor.reset_state()
                return True
            return False
        except Exception:
            return False

class ResilientInlineEditor:
    """Inline editor with error recovery capabilities"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.error_recovery = ErrorRecoveryManager()
        self._setup_error_handling()
    
    def _setup_error_handling(self):
        """Setup comprehensive error handling"""
        # Connect recovery signals
        self.error_recovery.recovery_performed.connect(self._on_recovery_performed)
        self.error_recovery.critical_error.connect(self._on_critical_error)
        
        # Wrap critical methods with error handling
        self._wrap_critical_methods()
    
    def _wrap_critical_methods(self):
        """Wrap critical methods with error handling"""
        original_start_editing = self.start_editing
        
        def safe_start_editing(content: str):
            try:
                return original_start_editing(content)
            except Exception as e:
                self._handle_method_error('start_editing', e, {'content': content})
        
        self.start_editing = safe_start_editing
    
    def _handle_method_error(self, method_name: str, error: Exception, 
                           context: Dict[str, Any]):
        """Handle error in critical method"""
        error_data = {
            'method': method_name,
            'error': str(error),
            'context': context,
            'editor': self
        }
        
        # Determine error type
        error_type = self._classify_error(error)
        
        # Attempt recovery
        element_id = getattr(self, 'element_id', 'unknown')
        self.error_recovery.handle_error(element_id, error_type, error_data)
    
    def _classify_error(self, error: Exception) -> str:
        """Classify error for appropriate recovery strategy"""
        if isinstance(error, (UnicodeDecodeError, UnicodeEncodeError)):
            return 'content_corruption'
        elif isinstance(error, (AttributeError, TypeError)):
            return 'state_inconsistency'
        elif isinstance(error, MemoryError):
            return 'memory_error'
        elif isinstance(error, ValueError):
            return 'validation_failure'
        else:
            return 'unknown_error'
```

## 📁 Files to Create

### Integration Files
1. **`src/torematrix/ui/components/editors/integration.py`** - Element list integration
2. **`src/torematrix/ui/integration/element_editor.py`** - Element-editor bridge
3. **`src/torematrix/ui/integration/property_panel.py`** - Property panel integration
4. **`src/torematrix/ui/integration/state_sync.py`** - State synchronization

### Accessibility and Recovery Files
5. **`src/torematrix/ui/components/editors/accessibility.py`** - Accessibility features
6. **`src/torematrix/ui/components/editors/recovery.py`** - Error recovery

### Final Integration Files
7. **`src/torematrix/ui/components/editors/advanced_inline.py`** - Complete editor
8. **`src/torematrix/ui/components/editors/complete_system.py`** - System integration

### Test Files
9. **`tests/integration/test_element_integration.py`** - Element integration tests
10. **`tests/integration/test_property_panel.py`** - Property panel tests
11. **`tests/integration/test_state_management.py`** - State management tests
12. **`tests/integration/test_accessibility.py`** - Accessibility tests
13. **`tests/integration/test_error_recovery.py`** - Error recovery tests

### Documentation Files
14. **`docs/inline_editing_guide.md`** - User documentation
15. **`docs/api/editors.md`** - API documentation

## 🧪 Testing Requirements

### Integration Tests (25+ tests minimum)
```python
# tests/integration/test_element_integration.py
import pytest
from unittest.mock import Mock, MagicMock
from torematrix.ui.components.editors.integration import ElementEditorBridge

class TestElementIntegration:
    def test_element_edit_request(self):
        """Test element edit request flow"""
        bridge = ElementEditorBridge()
        
        # Mock element list
        element_list = Mock()
        element_list.get_element_data.return_value = {
            'type': 'text',
            'content': 'Test content',
            'metadata': {}
        }
        
        # Request edit
        bridge.request_edit('elem1', 'text', 'Test content')
        
        assert 'elem1' in bridge.active_editors
        assert 'elem1' in bridge.element_contexts
    
    def test_edit_completion_flow(self):
        """Test complete edit workflow"""
        # Implementation for full workflow test
        pass
    
    def test_validation_integration(self):
        """Test validation during editing"""
        # Implementation for validation tests
        pass

# tests/integration/test_accessibility.py
class TestAccessibility:
    def test_screen_reader_support(self):
        """Test screen reader compatibility"""
        # Implementation for screen reader tests
        pass
    
    def test_keyboard_navigation(self):
        """Test keyboard-only navigation"""
        # Implementation for keyboard navigation tests
        pass
    
    def test_high_contrast_mode(self):
        """Test high contrast accessibility"""
        # Implementation for high contrast tests
        pass
```

### Complete System Integration
```python
# src/torematrix/ui/components/editors/complete_system.py
from .advanced_inline import AdvancedInlineEditor
from .integration import ElementEditorBridge
from .accessibility import AccessibleInlineEditor
from .recovery import ResilientInlineEditor

class CompleteInlineEditor(AdvancedInlineEditor, AccessibleInlineEditor, 
                          ResilientInlineEditor):
    """Complete inline editor with all features"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.integration_ready = True
        self._finalize_setup()
    
    def _finalize_setup(self):
        """Final setup for production use"""
        # Ensure all features are properly integrated
        self._verify_feature_integration()
        
        # Setup monitoring
        self._setup_monitoring()
        
        # Mark as ready
        self.setProperty("production_ready", True)
    
    def _verify_feature_integration(self):
        """Verify all features are properly integrated"""
        features = [
            'spell_check', 'validation', 'auto_save', 'diff_display',
            'accessibility', 'error_recovery', 'state_sync'
        ]
        
        for feature in features:
            assert hasattr(self, f"{feature}_enabled") or hasattr(self, feature)

class InlineEditingSystem:
    """Complete inline editing system for production use"""
    
    def __init__(self, element_list=None, property_panel=None, state_manager=None):
        self.element_list = element_list
        self.property_panel = property_panel
        self.state_manager = state_manager
        
        # Core components
        self.editor_bridge = ElementEditorBridge()
        self.integrations = []
        
        self._setup_integrations()
    
    def _setup_integrations(self):
        """Setup all system integrations"""
        if self.element_list:
            from .integration import ElementListIntegration
            integration = ElementListIntegration(self.element_list, self.editor_bridge)
            self.integrations.append(integration)
        
        if self.property_panel:
            from ..integration.property_panel import PropertyPanelIntegration
            integration = PropertyPanelIntegration(self.property_panel, self.editor_bridge)
            self.integrations.append(integration)
        
        if self.state_manager:
            from ..integration.state_sync import EditorStateSync
            integration = EditorStateSync(self.editor_bridge, self.state_manager)
            self.integrations.append(integration)
    
    def create_editor(self, element_type: str = 'text') -> CompleteInlineEditor:
        """Create a complete inline editor"""
        editor = CompleteInlineEditor()
        
        # Configure for element type
        editor.configure_for_element_type(element_type)
        
        return editor
```

## ✅ Acceptance Criteria Checklist

### Element List Integration
- [ ] Element list integration working seamlessly
- [ ] Double-click editing from element list
- [ ] Content updates propagate to element list
- [ ] State synchronization working

### Property Panel Integration
- [ ] Property panel alternative editing functions
- [ ] Bidirectional synchronization
- [ ] Tabbed interface for different properties
- [ ] Metadata editing capability

### State Management Integration
- [ ] State management saves editor state
- [ ] Editor state persistence across sessions
- [ ] Recovery from crashes
- [ ] Undo/redo integration

### Accessibility Features
- [ ] Screen reader compatibility
- [ ] Keyboard-only navigation
- [ ] High contrast mode support
- [ ] ARIA labels and descriptions

### Error Handling
- [ ] Graceful error recovery
- [ ] Data loss prevention
- [ ] User feedback for errors
- [ ] Automatic error reporting

### Testing and Documentation
- [ ] Comprehensive integration tests pass
- [ ] User documentation complete
- [ ] API documentation complete
- [ ] >95% code coverage achieved

## 🚀 Success Metrics
- **Integration**: Full system integration working
- **Accessibility**: WCAG 2.1 AA compliance
- **Error Recovery**: <1% data loss rate
- **Testing**: 25+ integration tests all passing
- **Documentation**: Complete user and API docs
- **Production Ready**: All acceptance criteria met

## 🔄 Development Workflow
1. Create branch: `feature/inline-editing-agent4-issue188`
2. Implement element list integration
3. Add property panel integration
4. Connect state management
5. Implement accessibility features
6. Add error handling and recovery
7. Create complete system integration
8. Write comprehensive integration tests
9. Create user and API documentation
10. Perform final testing and validation
11. Create PR when complete

## 📚 User Documentation

### Quick Start Guide
```markdown
# Inline Editing Quick Start

## Basic Usage
1. **Double-click** any element to start editing
2. **Type** to modify content
3. **Ctrl+Enter** to save changes
4. **Escape** to cancel

## Advanced Features
- **F2**: Start editing selected element
- **Ctrl+S**: Save and continue editing
- **Ctrl+Z/Y**: Undo/Redo
- **Ctrl+F**: Search and replace

## Accessibility
- Full keyboard navigation support
- Screen reader compatible
- High contrast mode available
- ARIA labels for all controls
```

Focus on delivering a complete, production-ready inline editing system that integrates seamlessly with all other components!