# Inline Editing System Documentation

## Overview

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
```

### Editor Configuration

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
```

### Keyboard Navigation

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
```

## Performance Monitoring

### Metrics Collection

```python
# Get system metrics
metrics = editing_system.get_system_metrics()
print(f"Active editors: {metrics.active_editors}")
print(f"Success rate: {metrics._calculate_success_rate():.1f}%")
print(f"Memory usage: {metrics.memory_usage_mb:.1f} MB")

# Get comprehensive status
status = editing_system.get_system_status()
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
```

## API Reference

### InlineEditingSystem

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