# Agent 4: Dialog System - Notifications and Integration

## Your Role
You are Agent 4, responsible for implementing the notification system, polishing all dialog features, and ensuring smooth integration across the entire dialog system. You'll also handle accessibility and keyboard navigation.

## Context Files to Read First
1. **All Agent Work**: `/src/torematrix/ui/dialogs/` - Review all implemented dialogs
2. **Main Window**: Look for main application window implementation
3. **Theme System**: `/src/torematrix/ui/theme/` (if exists) - Prepare integration
4. **Layout System**: Check for any layout management systems

## Your Tasks

### 1. Toast Notification System
**File to create**: `/src/torematrix/ui/dialogs/notifications.py`

Implement:
- `NotificationManager` singleton for app-wide notifications
- `ToastNotification` widget class
- Position options (top-right, bottom-right, etc.)
- Auto-dismiss with timers
- Notification stacking and queue management
- Animation support (slide in/out, fade)

### 2. Notification Types
**File to create**: `/src/torematrix/ui/dialogs/notification_types.py`

Implement:
- `NotificationType` enum (INFO, SUCCESS, WARNING, ERROR)
- `NotificationData` dataclass
- Action button support in notifications
- Notification history/log
- Priority levels for queue management

### 3. Keyboard Navigation Enhancement
**File to update**: `/src/torematrix/ui/dialogs/base.py` (enhance Agent 1's work)

Implement:
- Tab order management
- Focus indicators
- Keyboard shortcuts (ESC, Enter, Ctrl+shortcuts)
- Accessibility announcements
- Screen reader support

### 4. Dialog Styling and Themes
**File to create**: `/src/torematrix/ui/dialogs/styles.py`

Implement:
- Default dialog styles
- Theme integration hooks
- Style customization API
- Dark/light mode support
- Consistent spacing and sizing

### 5. Integration Module
**File to create**: `/src/torematrix/ui/dialogs/__init__.py`

Implement:
- Clean public API exports
- Dialog factory functions
- Global dialog configuration
- Integration helpers for main app

### 6. Polish and Optimization
**Files to update**: All dialog files

Tasks:
- Add comprehensive docstrings
- Optimize performance bottlenecks
- Add debug/logging support
- Ensure thread safety
- Memory leak prevention

## Notification System Features
```python
# Example usage:
# Show simple notification
notify("Operation Complete", "Your files have been processed", 
       type=NotificationType.SUCCESS)

# Show notification with actions
notify(
    title="Update Available",
    message="Version 2.0 is ready to install",
    type=NotificationType.INFO,
    actions=[
        ("Install Now", lambda: install_update()),
        ("Later", lambda: defer_update())
    ],
    duration=0  # Don't auto-dismiss
)

# Access notification manager
manager = NotificationManager.instance()
manager.set_position(NotificationPosition.BOTTOM_RIGHT)
manager.set_max_visible(5)
```

## Accessibility Requirements
- All dialogs must be keyboard navigable
- Focus must be trapped within modal dialogs
- Screen readers must announce dialog content
- High contrast mode support
- Sufficient color contrast ratios

## Integration Points
- Hook notifications into main window
- Ensure all dialogs respect app-wide settings
- Create convenience functions for common operations
- Document integration patterns

## Testing Approach
Create test files:
- `/tests/unit/ui/dialogs/test_notifications.py`
- `/tests/unit/ui/dialogs/test_accessibility.py`
- `/tests/unit/ui/dialogs/test_integration.py`

Test scenarios:
- Notification stacking and positioning
- Queue management with max visible
- Keyboard navigation flow
- Screen reader compatibility
- Memory usage over time
- Thread safety of notifications

## Performance Requirements
- Notifications must not block main thread
- Animations should be smooth (60 FPS)
- Memory usage should be bounded
- No memory leaks from closed dialogs

## Documentation Requirements
Create or update:
- `/docs/ui/dialogs.md` - Usage guide
- `/examples/dialogs/` - Example scripts
- API documentation in docstrings
- Integration guide for developers

## Polish Checklist
- [ ] All dialogs have consistent styling
- [ ] Animations are smooth and professional
- [ ] Error states are handled gracefully
- [ ] Debug logging is comprehensive
- [ ] Public API is clean and intuitive
- [ ] Examples cover common use cases
- [ ] Integration is well documented

## Success Criteria
- Notification system works reliably
- All dialogs are keyboard accessible
- Theme integration is prepared
- Performance is optimized
- Documentation is complete
- Integration is seamless
- All tests pass with >95% coverage
- No memory leaks or threading issues