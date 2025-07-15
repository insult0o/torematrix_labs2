# Inline Editing System Documentation

## Overview

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
```

### Editor Configuration

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
```

### Keyboard Navigation

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
```

## Performance Monitoring

### Built-in Metrics

```python
# Get system metrics
metrics = editing_system.get_metrics()
print(f"Active editors: {metrics.active_editors_count}")
print(f"Success rate: {metrics.success_rate():.1%}")
print(f"Memory usage: {metrics.memory_usage_mb:.1f} MB")

# Get comprehensive status
status = editing_system.get_system_status()
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
```

## API Reference

### InlineEditingSystem

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