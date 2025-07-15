# Inline Editing System Documentation

## Overview

<<<<<<< HEAD
The Inline Editing System provides a comprehensive, production-ready framework for enabling seamless inline editing of document elements within the TORE Matrix Labs application. The system is designed with accessibility, performance, and extensibility as core principles.

## Architecture

### Core Components

The system consists of four main components:

1. **Base Editor Framework** (`base.py`)
   - Abstract base classes and interfaces
   - Common lifecycle management
   - State and validation handling

2. **Element Editor Bridge** (`integration.py`)
   - Seamless integration with element lists
   - Event-driven communication
   - Request queue management

3. **Accessibility Manager** (`accessibility.py`)
   - WCAG compliance
   - Screen reader support
   - Keyboard navigation enhancement

4. **Error Recovery System** (`recovery.py`)
   - Comprehensive error handling
   - Multiple recovery strategies
   - User-friendly error reporting

5. **Complete System Integration** (`complete_system.py`)
   - Unified system orchestration
   - Performance monitoring
   - Configuration management

## Getting Started

### Basic Usage

```python
from src.torematrix.ui.components.editors import create_inline_editing_system

# Create the system with default configuration
editing_system = create_inline_editing_system()

# Set up your editor factory
def create_text_editor(element_id, element_type, parent, config):
    if element_type == "text":
        return TextEditor(parent, config)
    # Add more editor types as needed
    return None

editing_system.set_editor_factory(create_text_editor)

# Request editing for an element
success = editing_system.request_edit(
    element_id="doc_element_123",
    element_type="text", 
    current_value="Current text content",
    position=(100, 200),
    parent_widget=my_parent_widget
)
```

### Custom Configuration

```python
from src.torematrix.ui.components.editors import SystemConfiguration, InlineEditingSystem

# Create custom configuration
config = SystemConfiguration(
    auto_commit_enabled=True,
    auto_commit_delay=1500,  # 1.5 seconds
    max_concurrent_editors=5,
    accessibility_enabled=True,
    error_recovery_enabled=True,
    performance_monitoring=True
)

# Create system with custom config
editing_system = InlineEditingSystem(config=config)
```

## Editor Implementation

### Creating Custom Editors

To create a custom editor, inherit from `BaseEditor` and implement the required methods:

```python
from src.torematrix.ui.components.editors.base import BaseEditor, EditorConfig, EditorState

class CustomTextEditor(BaseEditor):
    def __init__(self, parent=None, config=None):
        super().__init__(parent, config)
        self.text_widget = QLineEdit(self)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(self.text_widget)
        self.setLayout(layout)
        
        # Connect signals
        self.text_widget.textChanged.connect(self._on_text_changed)
        self.text_widget.returnPressed.connect(self.save)
        
    def set_value(self, value):
        self.text_widget.setText(str(value) if value else "")
        self._set_original_value(value)
        return True
        
    def get_value(self):
        return self.text_widget.text()
        
    def start_editing(self, value=None):
        if value is not None:
            self.set_value(value)
        self._set_state(EditorState.EDITING)
        self.text_widget.setFocus()
        self.text_widget.selectAll()
        self.editing_started.emit()
        return True
        
    def save(self):
        if self._state == EditorState.EDITING:
            is_valid, error_msg = self.validate()
            if is_valid:
                self._set_state(EditorState.INACTIVE)
                self.editing_finished.emit(True)
                return True
            else:
                self.validation_failed.emit(error_msg)
        return False
        
    def cancel_editing(self):
        if self._state == EditorState.EDITING:
            self.set_value(self._original_value)
            self._set_state(EditorState.INACTIVE)
            self.editing_finished.emit(False)
            return True
        return False
        
    def validate(self, value=None):
        current_value = value if value is not None else self.get_value()
        
        # Required field validation
        if self.config.required and not current_value.strip():
            return False, "This field is required"
            
        # Length validation
        if self.config.max_length and len(current_value) > self.config.max_length:
            return False, f"Text too long (max {self.config.max_length} characters)"
            
        return True, ""
        
    def _on_text_changed(self, text):
        self._set_current_value(text)
=======
The Inline Editing System is a comprehensive, production-ready solution for enabling inline editing of document elements within the TORE Matrix Labs application. It provides a complete framework with accessibility support, error handling, performance optimization, and seamless integration.

## Features

### Core Features
- **Universal Editor Support**: Text, numeric, boolean, choice, and coordinate editors
- **Accessibility First**: Full WCAG compliance with screen reader support
- **Error Recovery**: Comprehensive error handling with automatic recovery
- **Performance Optimized**: Efficient memory management and fast rendering
- **Production Ready**: Robust architecture with comprehensive testing

### Advanced Features
- **Element List Integration**: Seamless workflow between element lists and editors
- **Keyboard Navigation**: Full keyboard accessibility with custom shortcuts
- **Automatic Validation**: Real-time validation with user-friendly feedback
- **Auto-save**: Configurable automatic saving of changes
- **Memory Management**: Intelligent cleanup and resource management

## Architecture

```
InlineEditingSystem
├── BaseEditor (Abstract editor interface)
├── ElementEditorBridge (Integration layer)
├── AccessibilityManager (WCAG compliance)
├── EditorRecoveryManager (Error handling)
└── Complete System Integration
```

## Quick Start

### Basic Setup

```python
from torematrix.ui.components.editors import InlineEditingSystem, SystemConfiguration

# Create configuration
config = SystemConfiguration(
    enable_accessibility=True,
    enable_error_recovery=True,
    auto_save_interval=30
)

# Initialize system
editing_system = InlineEditingSystem(config)

# Create an editor
editor = editing_system.create_editor(
    element_id="element_123",
    element_type="text",
    parent=parent_widget
)

# Start editing
editing_system.start_editing("element_123", initial_value="Hello World")
```

### Widget Integration

```python
from torematrix.ui.components.editors import InlineEditingSystemWidget

# Create widget with integrated UI
editing_widget = InlineEditingSystemWidget(config, parent)

# The widget provides automatic UI controls and status display
```

## Editor Types

### Text Editors

```python
# Single-line text editor
text_editor = editing_system.create_editor("text_id", "text", parent)

# Multi-line text editor  
multiline_editor = editing_system.create_editor("multiline_id", "multiline", parent)

# Rich text editor with formatting
rich_editor = editing_system.create_editor("rich_id", "rich_text", parent)
```

### Numeric Editors

```python
# Integer editor with range validation
int_editor = editing_system.create_editor("int_id", "integer", parent, 
                                         EditorConfig(min_value=0, max_value=100))

# Float editor with precision
float_editor = editing_system.create_editor("float_id", "float", parent,
                                           EditorConfig(precision=2))
```

### Boolean Editors

```python
# Checkbox editor
bool_editor = editing_system.create_editor("bool_id", "boolean", parent)

# Toggle switch editor
toggle_editor = editing_system.create_editor("toggle_id", "toggle", parent)
```

### Choice Editors

```python
# Dropdown selection
choice_editor = editing_system.create_editor("choice_id", "choice", parent,
                                            EditorConfig(choices=["A", "B", "C"]))

# Multi-select editor
multi_editor = editing_system.create_editor("multi_id", "multi_choice", parent,
                                           EditorConfig(choices=["X", "Y", "Z"]))
```

### Coordinate Editors

```python
# 2D point editor
point_editor = editing_system.create_editor("point_id", "point_2d", parent)

# 3D coordinate editor
coord_editor = editing_system.create_editor("coord_id", "point_3d", parent)
```

## Configuration

### System Configuration

```python
config = SystemConfiguration(
    # Editor settings
    enable_accessibility=True,           # Enable accessibility features
    enable_error_recovery=True,          # Enable error recovery
    enable_performance_monitoring=True,  # Enable performance tracking
    auto_save_interval=30,              # Auto-save every 30 seconds
    max_concurrent_editors=10,          # Maximum concurrent editors
    
    # Accessibility settings
    screen_reader_support=True,         # Screen reader compatibility
    high_contrast_mode=False,           # High contrast visual mode
    keyboard_navigation=True,           # Keyboard navigation support
    focus_timeout=5000,                 # Focus timeout in milliseconds
    
    # Performance settings
    memory_limit_mb=100.0,              # Memory usage limit
    cleanup_interval=60,                # Cleanup interval in seconds
    metrics_update_interval=5,          # Metrics update frequency
    
    # Error handling settings
    max_recovery_attempts=3,            # Maximum recovery attempts
    show_error_dialogs=True,            # Show error dialogs to user
    log_errors=True                     # Enable error logging
)
>>>>>>> origin/main
```

### Editor Configuration

<<<<<<< HEAD
Configure editor behavior using `EditorConfig`:

```python
from src.torematrix.ui.components.editors.base import EditorConfig

config = EditorConfig(
    auto_commit=True,           # Auto-save after delay
    commit_delay=1000,          # Delay in milliseconds
    allow_empty=False,          # Prevent empty values
    placeholder_text="Enter text...",
    max_length=500,             # Maximum character length
    required=True,              # Required field
    validation_rules={          # Custom validation rules
        'pattern': r'^[A-Za-z\s]+$',  # Letters and spaces only
        'min_words': 2
    }
)
```

## Accessibility Features

The system provides comprehensive accessibility support:

### Screen Reader Support

```python
# Automatic screen reader detection and announcements
editing_system.accessibility_manager.announce("Editing started")

# Custom accessibility configuration
accessibility_config = {
    'accessible_name': 'Document Title Editor',
    'accessible_description': 'Edit the title of the document. Press F2 to start editing.',
    'role': 'textbox',
    'aria_properties': {
        'aria-required': 'true',
        'aria-multiline': 'false'
    }
}
=======
```python
editor_config = EditorConfig(
    # Validation
    required=True,
    min_length=5,
    max_length=100,
    pattern=r'^[A-Za-z0-9]+$',
    
    # Behavior
    auto_commit=True,
    commit_delay=1000,
    placeholder="Enter text...",
    
    # Styling
    font_size=12,
    background_color="#ffffff",
    border_width=1,
    
    # Accessibility
    accessible_name="Text Editor",
    accessible_description="Enter text content",
    tab_index=1
)
```

## Accessibility

### Screen Reader Support

The system provides comprehensive screen reader support:

```python
# Automatic screen reader detection
accessibility_manager = AccessibilityManager()

# Setup accessibility for editor
accessibility_manager.setup_accessibility(editor, {
    'accessible_name': 'Document Title Editor',
    'accessible_description': 'Edit the document title. Press F2 to start editing.',
    'role': 'textbox',
    'aria_properties': {
        'aria-required': 'true',
        'aria-label': 'Document title'
    }
})

# Manual announcements
accessibility_manager.announce("Editing started")
accessibility_manager.announce("Changes saved", priority='assertive')
>>>>>>> origin/main
```

### Keyboard Navigation

<<<<<<< HEAD
Built-in keyboard shortcuts:
- `F2` - Start editing
- `Escape` - Cancel editing
- `Ctrl+Enter` - Save changes
- `Alt+H` - Help message
- `Alt+D` - Description
- `Alt+S` - Current state

### High Contrast and Large Font Support

Automatic detection and support for system accessibility settings:
- High contrast mode detection
- Large font scaling
- Focus indicators
- Reduced motion support

## Error Handling

### Automatic Error Recovery

The system provides multiple recovery strategies:

```python
# Errors are automatically classified and recovery attempted
try:
    editor.save()
except ValidationError as e:
    # Automatic rollback strategy
    pass
except NetworkError as e:
    # Automatic retry strategy
    pass
except PermissionError as e:
    # Graceful failure with user notification
    pass
```

### Custom Error Handling

```python
# Connect to error signals for custom handling
editing_system.error_handler.error_occurred.connect(my_error_handler)

def my_error_handler(error_record):
    print(f"Error in {error_record.component}: {error_record.message}")
    
    # Custom recovery logic
    if error_record.category == ErrorCategory.VALIDATION:
        # Show custom validation UI
        show_validation_help(error_record.context['editor'])
=======
Standard keyboard shortcuts:

- **F2**: Start editing current element
- **Escape**: Cancel editing
- **Ctrl+Enter**: Save and commit changes
- **Tab/Shift+Tab**: Navigate between elements
- **Alt+H**: Get help for current element
- **Alt+D**: Get description of current element
- **Alt+S**: Get state of current element

Custom shortcuts can be configured:

```python
shortcuts = {
    'Ctrl+S': lambda: editor.save(),
    'Ctrl+Z': lambda: editor.undo(),
    'Ctrl+Y': lambda: editor.redo(),
    'F1': lambda: show_help()
}
```

### High Contrast Mode

```python
# Enable high contrast mode
accessibility_manager.toggle_high_contrast()

# Check if high contrast is enabled
is_high_contrast = accessibility_manager.settings.high_contrast_enabled
```

## Error Handling

### Error Recovery

The system provides automatic error recovery:

```python
# Register custom recovery strategy
recovery_manager.register_recovery_strategy("custom_error", [
    RecoveryAction(
        RecoveryStrategy.RETRY,
        "Retry the operation",
        lambda: retry_operation(),
        priority=1
    ),
    RecoveryAction(
        RecoveryStrategy.FALLBACK,
        "Use fallback method",
        lambda: fallback_operation(),
        priority=2
    )
])

# Handle errors with recovery
try:
    # Some operation that might fail
    editor.save()
except Exception as e:
    error_id = recovery_manager.handle_error(e)
    recovery_manager.show_error_dialog(error_id)
```

### Error Callbacks

```python
# Register error callback
def handle_validation_error(context):
    print(f"Validation failed: {context.message}")
    # Show user-friendly message

recovery_manager.register_error_callback("ValidationError", handle_validation_error)
>>>>>>> origin/main
```

## Performance Monitoring

<<<<<<< HEAD
### Built-in Metrics

```python
# Get system metrics
metrics = editing_system.get_metrics()
print(f"Active editors: {metrics.active_editors_count}")
print(f"Success rate: {metrics.success_rate():.1%}")
=======
### Metrics Collection

```python
# Get system metrics
metrics = editing_system.get_system_metrics()
print(f"Active editors: {metrics.active_editors}")
print(f"Success rate: {metrics._calculate_success_rate():.1f}%")
>>>>>>> origin/main
print(f"Memory usage: {metrics.memory_usage_mb:.1f} MB")

# Get comprehensive status
status = editing_system.get_system_status()
<<<<<<< HEAD
print(f"Editor pool size: {status['editor_pool_size']}")
print(f"Error statistics: {status['error_handler_stats']}")
```

### Status Widget

```python
# Embed status widget in your UI
status_widget = editing_system.get_status_widget()
my_layout.addWidget(status_widget)

# Listen for metric updates
editing_system.system_metrics_updated.connect(update_my_dashboard)
```

## Event Handling

### System Events

```python
# Listen for system-wide events
editing_system.editor_activated.connect(on_editor_started)
editing_system.editor_deactivated.connect(on_editor_finished)
editing_system.system_state_changed.connect(on_system_state_change)

def on_editor_started(element_id, editor):
    print(f"Started editing {element_id}")
    
def on_editor_finished(element_id):
    print(f"Finished editing {element_id}")
    
def on_system_state_change(state):
    print(f"System state: {state}")
```

### Editor Events

```python
# Connect to individual editor events
editor.editing_started.connect(lambda: print("Editing started"))
editor.editing_finished.connect(lambda success: print(f"Editing finished: {success}"))
editor.value_changed.connect(lambda value: print(f"Value changed: {value}"))
editor.validation_failed.connect(lambda msg: print(f"Validation failed: {msg}"))
```

## Advanced Features

### Editor Pooling

For performance optimization, the system supports editor pooling:

```python
config = SystemConfiguration(
    cache_editor_instances=True,  # Enable pooling
    editor_pool_size=20,          # Pool size
    lazy_editor_creation=True     # Create on demand
)
```

### Batch Operations

```python
# Save all active editors
results = editing_system.save_all_edits()
for element_id, success in results.items():
    print(f"Save {element_id}: {'success' if success else 'failed'}")

# Cancel all active editors
editing_system.cancel_all_edits()
```

### Integration with Element Lists

```python
# The system integrates seamlessly with element lists
element_list.double_clicked.connect(
    lambda element_id: editing_system.request_edit(
        element_id=element_id,
        element_type=element_list.get_element_type(element_id),
        current_value=element_list.get_element_value(element_id)
    )
)

# Listen for edit completion to update element list
editing_system.editor_deactivated.connect(
    lambda element_id: element_list.refresh_element(element_id)
)
```

## Best Practices

### Editor Factory Design

```python
def create_smart_editor_factory():
    """Create a smart factory that selects appropriate editors"""
    
    editor_registry = {
        'text': TextEditor,
        'number': NumberEditor,
        'date': DateEditor,
        'choice': ChoiceEditor,
        'rich_text': RichTextEditor
    }
    
    def factory(element_id, element_type, parent, config):
        editor_class = editor_registry.get(element_type)
        if editor_class:
            return editor_class(parent, config)
        return None
        
    return factory
```

### Configuration Management

```python
def load_user_preferences():
    """Load user accessibility and editing preferences"""
    
    user_config = SystemConfiguration(
        # Load from user settings
        accessibility_enabled=user_settings.get('accessibility', True),
        auto_commit_enabled=user_settings.get('auto_commit', False),
        auto_commit_delay=user_settings.get('commit_delay', 1000),
        # ... other settings
    )
    
    return user_config
```

### Testing Strategy

```python
# Use the mock editor for testing
class TestableEditingSystem(InlineEditingSystem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_editor_factory(lambda *args: MockEditor())

# Test your integration
def test_editing_workflow():
    system = TestableEditingSystem()
    
    # Test request
    assert system.request_edit("test", "text", "value") is True
    assert system.is_editing("test")
    
    # Test completion
    editor = system.get_active_editor("test")
    editor.save()
    assert not system.is_editing("test")
```

## Troubleshooting

### Common Issues

1. **Editor not appearing**: Check that the editor factory is properly set and returns a valid editor instance.

2. **Accessibility issues**: Ensure `accessibility_enabled=True` in configuration and that the system can detect accessibility features.

3. **Performance problems**: Monitor the system metrics and consider adjusting `max_concurrent_editors` and enabling editor pooling.

4. **Memory leaks**: Make sure editors are properly cleaned up by implementing the pooling reset methods.

### Debug Information

```python
# Get comprehensive diagnostic information
diagnostics = editing_system.export_diagnostics()

# Enable debug logging
config = SystemConfiguration(debug_logging=True)

# Monitor error statistics
error_stats = editing_system.error_handler.get_error_statistics()
=======
print(f"System state: {status['state']}")
print(f"Configuration: {status['config']}")
```

### Performance Optimization

```python
# Configure performance settings
config.memory_limit_mb = 50.0        # Reduce memory limit
config.cleanup_interval = 30         # More frequent cleanup
config.max_concurrent_editors = 5    # Reduce concurrent editors

# Monitor performance
editing_system.metrics_updated.connect(lambda metrics: 
    print(f"Performance update: {metrics}")
)
```

## Integration Examples

### Element List Integration

```python
# Create element list bridge
bridge = ElementEditorBridge()

# Connect to element list signals
element_list.item_double_clicked.connect(bridge.request_edit)
bridge.edit_requested.connect(lambda element_id, element_type: 
    editing_system.create_editor(element_id, element_type, parent)
)

# Handle edit completion
bridge.edit_completed.connect(lambda element_id, value, success:
    update_element_value(element_id, value) if success else None
)
```

### Custom Editor Integration

```python
class CustomEditor(BaseEditor, AccessibleInlineEditor, EditorErrorRecoveryMixin):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_custom_ui()
    
    def _setup_custom_ui(self):
        # Custom editor implementation
        pass
    
    def get_value(self):
        # Return current editor value
        return self.custom_widget.get_value()
    
    def set_value(self, value):
        # Set editor value
        self.custom_widget.set_value(value)
    
    def validate(self):
        # Custom validation logic
        return True, ""

# Register custom editor
from torematrix.ui.components.editors.factory import PropertyEditorFactory
PropertyEditorFactory.register_editor("custom_type", CustomEditor, priority=10)
>>>>>>> origin/main
```

## API Reference

### InlineEditingSystem

<<<<<<< HEAD
**Methods:**
- `request_edit(element_id, element_type, current_value, position, parent_widget, config)` - Request editing
- `cancel_edit(element_id)` - Cancel specific edit
- `cancel_all_edits()` - Cancel all active edits
- `save_all_edits()` - Save all active edits
- `get_active_editor(element_id)` - Get editor for element
- `is_editing(element_id)` - Check if element is being edited
- `get_metrics()` - Get system metrics
- `get_system_status()` - Get comprehensive status
- `shutdown()` - Graceful shutdown

**Signals:**
- `editor_activated(element_id, editor)` - Editor started
- `editor_deactivated(element_id)` - Editor finished
- `system_state_changed(state)` - System state change
- `system_metrics_updated(metrics)` - Metrics updated

### BaseEditor

**Abstract Methods:**
- `set_value(value)` - Set editor value
- `get_value()` - Get current value
- `start_editing(value)` - Start editing mode
- `save()` - Save and finish editing
- `cancel_editing()` - Cancel editing
- `validate(value)` - Validate value

**Signals:**
- `editing_started()` - Editing started
- `editing_finished(success)` - Editing finished
- `value_changed(value)` - Value changed
- `validation_failed(message)` - Validation failed

This documentation provides a comprehensive guide to using and extending the Inline Editing System. For additional examples and advanced usage patterns, refer to the test suite and example implementations.
=======
Main system class providing the complete editing functionality.

#### Methods

- `create_editor(element_id, element_type, parent, config=None)`: Create new editor
- `get_editor(element_id)`: Get existing editor
- `destroy_editor(element_id)`: Destroy editor
- `start_editing(element_id, initial_value=None)`: Start editing
- `save_all_editors()`: Save all active editors
- `get_system_metrics()`: Get performance metrics
- `get_system_status()`: Get comprehensive status
- `shutdown()`: Graceful system shutdown

#### Signals

- `system_state_changed(str)`: System state changed
- `editor_created(str, object)`: Editor created
- `editor_destroyed(str)`: Editor destroyed
- `metrics_updated(dict)`: Performance metrics updated
- `error_occurred(str, str)`: Error occurred
- `recovery_completed(str, bool)`: Recovery completed

### BaseEditor

Abstract base class for all editors.

#### Methods

- `start_editing(initial_value=None)`: Start editing mode
- `finish_editing(save=True)`: Finish editing
- `cancel_editing()`: Cancel editing
- `get_value()`: Get current value
- `set_value(value)`: Set current value
- `validate()`: Validate current value
- `save()`: Save changes
- `is_dirty()`: Check if editor has unsaved changes
- `is_editing()`: Check if editor is in editing mode

#### Signals

- `editing_started()`: Editing started
- `editing_finished(bool)`: Editing finished
- `value_changed(object)`: Value changed
- `validation_failed(str)`: Validation failed

### AccessibilityManager

Manages accessibility features for editors.

#### Methods

- `setup_accessibility(widget, config=None)`: Setup accessibility
- `announce(message, priority='polite')`: Announce to screen readers
- `toggle_high_contrast()`: Toggle high contrast mode
- `refresh_accessibility()`: Refresh accessibility settings

### EditorRecoveryManager

Manages error handling and recovery.

#### Methods

- `register_editor(editor, config=None)`: Register editor for monitoring
- `show_error_dialog(error_id, parent=None)`: Show error dialog
- `get_recovery_suggestions(error_id)`: Get recovery options
- `execute_recovery(error_id, strategy)`: Execute recovery strategy

## Testing

### Unit Tests

```python
import pytest
from torematrix.ui.components.editors import InlineEditingSystem

def test_editor_creation():
    system = InlineEditingSystem()
    editor = system.create_editor("test_id", "text", None)
    assert editor is not None
    assert system.get_editor("test_id") == editor

def test_editing_workflow():
    system = InlineEditingSystem()
    editor = system.create_editor("test_id", "text", None)
    
    # Start editing
    assert system.start_editing("test_id", "initial value")
    assert editor.is_editing()
    
    # Modify value
    editor.set_value("new value")
    assert editor.is_dirty()
    
    # Save
    assert editor.save()
    assert not editor.is_dirty()
```

### Integration Tests

```python
def test_accessibility_integration():
    config = SystemConfiguration(enable_accessibility=True)
    system = InlineEditingSystem(config)
    editor = system.create_editor("test_id", "text", None)
    
    # Check accessibility setup
    assert system.accessibility_manager is not None
    assert editor in system.accessibility_manager.managed_widgets

def test_error_recovery():
    config = SystemConfiguration(enable_error_recovery=True)
    system = InlineEditingSystem(config)
    
    # Simulate error
    error = ValueError("Test error")
    context = system.recovery_manager.error_handler.handle_error(error)
    
    # Check error handling
    assert context.error_id in system.recovery_manager.error_handler.error_contexts
    suggestions = system.recovery_manager.error_handler.get_recovery_suggestions(context.error_id)
    assert len(suggestions) > 0
```

## Troubleshooting

### Common Issues

#### Editor Not Appearing
- Check that parent widget is valid and visible
- Verify editor type is supported
- Check system state (should be READY)

#### Accessibility Not Working
- Ensure `enable_accessibility=True` in configuration
- Check that screen reader is running
- Verify accessibility permissions on system

#### Performance Issues
- Reduce `max_concurrent_editors` in configuration
- Increase `cleanup_interval` for more frequent cleanup
- Enable performance monitoring to identify bottlenecks

#### Memory Usage High
- Lower `memory_limit_mb` in configuration
- Enable auto-save to reduce dirty editors
- Check for memory leaks in custom editors

### Debug Mode

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Get detailed system status
status = editing_system.get_system_status()
print(json.dumps(status, indent=2))

# Monitor metrics in real-time
editing_system.metrics_updated.connect(lambda m: print(f"Metrics: {m}"))
```

### Performance Profiling

```python
# Profile editor creation
import time
start_time = time.time()
editor = editing_system.create_editor("profile_test", "text", parent)
creation_time = time.time() - start_time
print(f"Editor creation took {creation_time:.3f} seconds")

# Profile memory usage
import psutil
import os
process = psutil.Process(os.getpid())
memory_mb = process.memory_info().rss / 1024 / 1024
print(f"Current memory usage: {memory_mb:.1f} MB")
```

## Best Practices

### Editor Lifecycle
1. Always call `destroy_editor()` when done
2. Use auto-save for important data
3. Handle validation errors gracefully
4. Provide clear user feedback

### Performance
1. Limit concurrent editors based on system resources
2. Use appropriate cleanup intervals
3. Monitor memory usage regularly
4. Profile custom editors for performance

### Accessibility
1. Always provide accessible names and descriptions
2. Test with actual screen readers
3. Use semantic HTML/Qt roles
4. Provide keyboard shortcuts

### Error Handling
1. Register appropriate error callbacks
2. Provide meaningful error messages
3. Test recovery strategies
4. Log errors for debugging

## Migration Guide

### From Previous Versions

If migrating from an older editing system:

1. **Update imports**:
   ```python
   # Old
   from old_editor import Editor
   
   # New
   from torematrix.ui.components.editors import InlineEditingSystem
   ```

2. **Update configuration**:
   ```python
   # Old
   editor = Editor(parent, config_dict)
   
   # New
   config = SystemConfiguration(**config_dict)
   system = InlineEditingSystem(config)
   editor = system.create_editor(element_id, element_type, parent)
   ```

3. **Update signal connections**:
   ```python
   # Old
   editor.valueChanged.connect(callback)
   
   # New
   editor.value_changed.connect(callback)
   ```

## Conclusion

The Inline Editing System provides a comprehensive, production-ready solution for inline editing with full accessibility support, error handling, and performance optimization. It follows modern software engineering practices and provides a clean, extensible API for integration into larger applications.

For additional support or feature requests, please refer to the project documentation or contact the development team.
>>>>>>> origin/main
