# Agent 1: Dialog System - Core Foundation

## Your Role
You are Agent 1, responsible for implementing the core foundation of the dialog system. This includes the base dialog class, dialog manager, and integration with existing event and state systems.

## Context Files to Read First
1. **Event System**: `/src/torematrix/core/events/` - Understand event bus and event types
2. **State Management**: `/src/torematrix/core/state/` - Review state manager and middleware
3. **Existing UI Structure**: `/src/torematrix/ui/` - Check current UI organization
4. **Project Config**: `/pyproject.toml` - Review dependencies (PySide6)

## Your Tasks

### 1. Create Base Dialog Infrastructure
**File to create**: `/src/torematrix/ui/dialogs/base.py`

Implement:
- `BaseDialog` class extending QDialog
- Common properties: title, modal, size, position
- State management integration
- Event bus integration  
- Signal definitions for dialog lifecycle
- Base styling and theme preparation

### 2. Dialog State Management
**File to create**: `/src/torematrix/ui/dialogs/state.py`

Implement:
- `DialogState` dataclass with dialog metadata
- State persistence helpers
- Dialog registry for tracking open dialogs
- State change notifications

### 3. Dialog Manager
**File to create**: `/src/torematrix/ui/dialogs/manager.py`

Implement:
- `DialogManager` singleton class
- Dialog stacking and z-order management
- Global dialog operations (close all, get active)
- Dialog lifecycle tracking

### 4. Common Dialog Components
**File to create**: `/src/torematrix/ui/dialogs/components.py`

Implement:
- `DialogButton` configuration class
- `DialogResult` enum (OK, CANCEL, YES, NO, etc.)
- Button layout helpers
- Common dialog layouts

### 5. Animation Support
**File to create**: `/src/torematrix/ui/dialogs/animations.py`

Implement:
- Fade in/out animations
- Slide animations
- Animation configuration
- QPropertyAnimation wrappers

## Integration Points
- Hook into existing EventBus at `/src/torematrix/core/events/bus.py`
- Register with StateManager at `/src/torematrix/core/state/manager.py`
- Prepare for theme integration (future)

## Key Requirements
- All dialogs must emit events for open/close/result
- State must be trackable and restorable
- Support both modal and non-modal dialogs
- Keyboard navigation support (Tab, Enter, Escape)
- Prepare hooks for theme system

## Testing Approach
Create `/tests/unit/ui/dialogs/test_base.py` with tests for:
- Dialog creation and configuration
- State management integration
- Event emission
- Dialog manager operations
- Animation functionality

## Dependencies
- PySide6.QtWidgets
- PySide6.QtCore (Signals, Properties)
- torematrix.core.events
- torematrix.core.state

## Success Criteria
- Base dialog can be created and configured
- Dialog state is tracked in state manager
- Events are emitted for all lifecycle events
- Dialog manager can track multiple dialogs
- Animations work smoothly
- Tests pass with >95% coverage