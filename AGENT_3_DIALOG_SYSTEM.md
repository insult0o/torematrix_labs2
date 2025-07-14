# Agent 3: Dialog System - Progress and Forms

## Your Role
You are Agent 3, responsible for implementing progress dialogs and the form builder system. These are more complex dialogs that handle dynamic content and long-running operations.

## Context Files to Read First
1. **Agent 1's Base**: `/src/torematrix/ui/dialogs/base.py` - Understand dialog foundation
2. **Agent 1's Manager**: `/src/torematrix/ui/dialogs/manager.py` - Dialog lifecycle
3. **Processing Pipeline**: `/src/torematrix/processing/` - Understand progress reporting needs
4. **Worker Patterns**: `/src/torematrix/processing/workers/` - Background task patterns

## Your Tasks

### 1. Progress Dialog Implementation
**File to create**: `/src/torematrix/ui/dialogs/progress.py`

Implement:
- `ProgressDialog` class with determinate/indeterminate modes
- `ProgressInfo` dataclass for progress state
- Time estimation (elapsed, remaining)
- Cancellation support with proper cleanup
- Sub-task progress tracking
- Details/log area for verbose output

### 2. Progress Worker Integration
**File to create**: `/src/torematrix/ui/dialogs/progress_worker.py`

Implement:
- `ProgressWorker` QThread wrapper
- Progress callback protocol
- Cancellation token pattern
- Error handling and reporting
- Async operation support

### 3. Form Builder System
**File to create**: `/src/torematrix/ui/dialogs/forms.py`

Implement:
- `FormDialog` base class
- `FormField` configuration class
- Field types: text, number, checkbox, dropdown, date, file, etc.
- Dynamic field creation from configuration
- Field grouping and sections

### 4. Form Validation Framework
**File to create**: `/src/torematrix/ui/dialogs/validation.py`

Implement:
- `ValidationRule` class
- Common validators (required, email, regex, range, etc.)
- Custom validator support
- Real-time validation feedback
- Form-level validation

### 5. Form Widgets
**File to create**: `/src/torematrix/ui/dialogs/form_widgets.py`

Implement:
- Custom widgets for complex field types
- File picker with preview
- Color picker
- Rich text editor wrapper
- List/tag input widget

## Progress Dialog Features
```python
# Example usage:
def long_operation(progress_callback):
    for i in range(100):
        # Check if cancelled
        if not progress_callback(
            current=i,
            total=100,
            message=f"Processing item {i}",
            details=f"Details about item {i}"
        ):
            return False  # Cancelled
        # Do work...
    return True

dialog = ProgressDialog(
    title="Processing Files",
    message="Starting operation...",
    can_cancel=True,
    show_details=True
)
result = dialog.run_operation(long_operation)
```

## Form Dialog Features
```python
# Example usage:
fields = [
    FormField("name", "Name", FieldType.TEXT, required=True),
    FormField("age", "Age", FieldType.NUMBER, min_value=0, max_value=150),
    FormField("email", "Email", FieldType.TEXT, validators=[EmailValidator()]),
    FormField("subscribe", "Subscribe to newsletter", FieldType.CHECKBOX),
    FormField("country", "Country", FieldType.DROPDOWN, options=["USA", "UK", "Canada"])
]

dialog = FormDialog(
    title="User Registration",
    fields=fields,
    groups={
        "Personal Info": ["name", "age"],
        "Contact": ["email", "subscribe", "country"]
    }
)

if dialog.exec() == DialogResult.OK:
    data = dialog.get_form_data()
```

## Integration Requirements
- Progress dialogs must handle QThread operations safely
- Forms must validate in real-time without blocking UI
- Both must integrate with Agent 1's base system
- Support async/await patterns where applicable

## Testing Approach
Create test files:
- `/tests/unit/ui/dialogs/test_progress.py`
- `/tests/unit/ui/dialogs/test_forms.py`
- `/tests/unit/ui/dialogs/test_validation.py`

Test scenarios:
- Progress updates and cancellation
- Time estimation accuracy
- Form field rendering
- Validation rules
- Dynamic field dependencies
- Thread safety

## Performance Considerations
- Progress updates should not flood the UI thread
- Form validation should debounce for text fields
- Large forms should render efficiently
- Cancellation should be responsive

## Dependencies
- Everything from Agent 1
- QThread for progress operations
- asyncio for async support
- datetime for time calculations
- re module for regex validation

## Success Criteria
- Progress dialogs handle long operations smoothly
- Cancellation works reliably
- Forms render all field types correctly
- Validation provides clear feedback
- Dynamic forms update properly
- Thread operations are safe
- Tests achieve >95% coverage