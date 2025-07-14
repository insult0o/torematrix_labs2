# Agent 2: Dialog System - Standard Dialogs

## Your Role
You are Agent 2, responsible for implementing the standard dialog types that build upon Agent 1's foundation. Focus on file dialogs, confirmation dialogs, and their variations.

## Context Files to Read First
1. **Agent 1's Base Implementation**: `/src/torematrix/ui/dialogs/base.py` - Understand base dialog
2. **Agent 1's Components**: `/src/torematrix/ui/dialogs/components.py` - Use common components
3. **Event Types**: `/src/torematrix/core/events/types.py` - Add new event types if needed
4. **Existing Models**: `/src/torematrix/core/models/` - Check for file/path models

## Your Tasks

### 1. File Selection Dialogs
**File to create**: `/src/torematrix/ui/dialogs/file.py`

Implement:
- `FileDialog` class extending BaseDialog
- `FileFilter` class for file type filtering
- Multiple selection modes (single file, multiple files, directory)
- Recent files tracking
- File preview panel (optional)
- Path validation
- Common filters (documents, images, all files)

### 2. File Dialog Utilities
**File to create**: `/src/torematrix/ui/dialogs/file_utils.py`

Implement:
- Convenience functions: `show_open_file_dialog()`, `show_save_file_dialog()`
- File filter presets
- Path history management
- File type detection helpers

### 3. Confirmation Dialogs
**File to create**: `/src/torematrix/ui/dialogs/confirmation.py`

Implement:
- `ConfirmationDialog` class
- `MessageType` enum (INFO, WARNING, ERROR, QUESTION, SUCCESS)
- Standard button sets (OK, OK_CANCEL, YES_NO, YES_NO_CANCEL)
- Icon support based on message type
- Detailed/expandable text area
- "Don't show again" checkbox support

### 4. Alert Dialogs
**File to create**: `/src/torematrix/ui/dialogs/alerts.py`

Implement:
- Convenience functions: `alert()`, `error()`, `warning()`, `info()`
- Quick message display helpers
- Auto-sizing based on content
- Optional timeout for auto-close

### 5. Input Dialogs
**File to create**: `/src/torematrix/ui/dialogs/input.py`

Implement:
- `InputDialog` for simple text input
- `MultiInputDialog` for multiple fields
- Validation support
- Password input mode
- Default value support

## Integration Requirements
- Use Agent 1's BaseDialog as parent class
- Utilize DialogButton and DialogResult from components
- Emit appropriate events through event bus
- Store dialog results in state manager

## File Dialog Specific Features
```python
# Example usage you should support:
file_path = show_open_file_dialog(
    parent=main_window,
    title="Select Document",
    filters=[
        FileFilter("PDF Files", ["pdf"]),
        FileFilter("Word Documents", ["doc", "docx"]),
        FileFilter("All Files", ["*"])
    ],
    initial_dir="/home/user/documents"
)
```

## Confirmation Dialog Features
```python
# Example usage:
result = confirm(
    parent=main_window,
    title="Confirm Delete",
    message="Are you sure you want to delete this file?",
    detailed_text="This action cannot be undone.",
    buttons=ConfirmationDialog.YES_NO_CANCEL,
    default_button=DialogResult.NO
)
```

## Testing Approach
Create test files:
- `/tests/unit/ui/dialogs/test_file_dialog.py`
- `/tests/unit/ui/dialogs/test_confirmation.py`
- `/tests/unit/ui/dialogs/test_input.py`

Test scenarios:
- File filter functionality
- Path validation
- Button combinations
- Message type styling
- Event emission
- State persistence

## Dependencies
- Everything from Agent 1
- PySide6.QtWidgets.QFileDialog
- pathlib.Path for path handling
- os module for file operations

## Success Criteria
- File dialogs support all common operations
- Confirmation dialogs handle all message types
- Input dialogs validate user input
- All dialogs integrate with base system
- Convenience functions work intuitively
- Tests achieve >95% coverage