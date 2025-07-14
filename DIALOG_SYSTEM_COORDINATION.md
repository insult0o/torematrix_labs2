# Dialog System Implementation Coordination Guide

## Overview
This guide coordinates the implementation of the Dialog System (Issue #15) across 4 agents working in parallel. Each agent has specific responsibilities that build upon shared foundations.

## Timeline
- **Day 1-2**: Foundation and Core (Agent 1)
- **Day 2-3**: Standard Dialogs (Agent 2)  
- **Day 3-4**: Progress & Forms (Agent 3)
- **Day 4-5**: Notifications & Polish (Agent 4)
- **Day 5-6**: Integration and Testing

## Agent Dependencies

### Agent 1: Core Foundation (Start Immediately)
- No dependencies on other agents
- Creates foundation for all others
- **Key Files**:
  - `/src/torematrix/ui/dialogs/base.py`
  - `/src/torematrix/ui/dialogs/manager.py`
  - `/src/torematrix/ui/dialogs/components.py`

### Agent 2: Standard Dialogs (Depends on Agent 1)
- Wait for Agent 1's base.py and components.py
- Can start planning while waiting
- **Key Files**:
  - `/src/torematrix/ui/dialogs/file.py`
  - `/src/torematrix/ui/dialogs/confirmation.py`

### Agent 3: Progress & Forms (Depends on Agent 1)
- Wait for Agent 1's base.py and manager.py
- Can work in parallel with Agent 2
- **Key Files**:
  - `/src/torematrix/ui/dialogs/progress.py`
  - `/src/torematrix/ui/dialogs/forms.py`

### Agent 4: Notifications & Integration (Depends on All)
- Can start notification system independently
- Integration work requires all agents complete
- **Key Files**:
  - `/src/torematrix/ui/dialogs/notifications.py`
  - `/src/torematrix/ui/dialogs/__init__.py`

## Shared Interfaces

### Dialog Result Enum (Agent 1)
```python
class DialogResult(Enum):
    OK = auto()
    CANCEL = auto()
    YES = auto()
    NO = auto()
    RETRY = auto()
    ABORT = auto()
    CUSTOM = auto()
```

### Base Dialog Interface (Agent 1)
```python
class BaseDialog(QDialog):
    # Signals
    dialog_opened = Signal(str)
    dialog_closed = Signal(str, DialogResult)
    state_changed = Signal(dict)
    
    def add_button(self, button: DialogButton) -> QPushButton
    def set_content(self, widget: QWidget) -> None
    def get_result(self) -> DialogResult
    def update_state(self, data: Dict[str, Any]) -> None
```

### Event Types to Add
```python
# Add to EventType enum
DIALOG_OPENED = auto()
DIALOG_CLOSED = auto()
DIALOG_STATE_CHANGED = auto()
NOTIFICATION_SHOWN = auto()
NOTIFICATION_DISMISSED = auto()
```

## Integration Points

### State Manager Integration
- All dialogs register with state manager
- Dialog state includes: id, type, open_time, result, custom_data
- State persists across sessions where appropriate

### Event Bus Integration
- All dialogs emit lifecycle events
- Notifications emit show/dismiss events
- Form validation events for monitoring

### Theme Integration (Prepare Hooks)
- All dialogs use consistent style methods
- Prepare for theme variables
- Support dark/light modes

## Testing Strategy

### Unit Tests (Each Agent)
- Test dialog creation and configuration
- Test specific functionality
- Mock dependencies when needed

### Integration Tests (Agent 4)
- Test dialog stacking
- Test event flow
- Test state persistence
- Test notification queuing

### Performance Tests
- Measure dialog open/close time
- Test with many notifications
- Memory usage monitoring

## Common Patterns

### Dialog Creation Pattern
```python
dialog = SpecificDialog(
    parent=main_window,
    title="Dialog Title",
    # Common parameters
    modal=True,
    event_bus=app.event_bus,
    state_manager=app.state_manager
)
```

### Convenience Function Pattern
```python
def show_dialog_type(parent=None, **kwargs):
    dialog = DialogType(parent, **kwargs)
    if dialog.exec() == DialogResult.OK:
        return dialog.get_result_data()
    return None
```

## File Structure
```
src/torematrix/ui/dialogs/
├── __init__.py          # Public API (Agent 4)
├── base.py              # Base classes (Agent 1)
├── manager.py           # Dialog manager (Agent 1)
├── components.py        # Common components (Agent 1)
├── animations.py        # Animation support (Agent 1)
├── state.py            # State management (Agent 1)
├── file.py             # File dialogs (Agent 2)
├── file_utils.py       # File helpers (Agent 2)
├── confirmation.py     # Confirmations (Agent 2)
├── alerts.py           # Alert helpers (Agent 2)
├── input.py            # Input dialogs (Agent 2)
├── progress.py         # Progress dialogs (Agent 3)
├── progress_worker.py  # Worker support (Agent 3)
├── forms.py            # Form builder (Agent 3)
├── validation.py       # Form validation (Agent 3)
├── form_widgets.py     # Custom widgets (Agent 3)
├── notifications.py    # Toast system (Agent 4)
├── notification_types.py # Notification types (Agent 4)
├── styles.py           # Styling system (Agent 4)
└── tests/
    └── ... test files for each module
```

## Success Metrics
- All dialog types implemented and tested
- >95% test coverage across all modules
- Clean API with good documentation
- No memory leaks or performance issues
- Smooth integration with existing systems
- Accessibility standards met

## Communication Protocol
1. Agents should mark completion in their files with a comment
2. Create placeholder classes if others need the interface
3. Use type hints for all public methods
4. Document integration points clearly
5. Flag any blocking issues immediately