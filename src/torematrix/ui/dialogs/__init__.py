"""Dialog system for ToreMatrix UI framework.

This module provides a comprehensive dialog system with support for:
- Modal and non-modal dialogs
- File selection with filtering
- Progress indication with cancellation
- Form building and validation
- Toast notifications
- Keyboard navigation
- Theme integration
"""

from .base import BaseDialog, DialogResult, DialogButton, DialogManager
from .file import FileDialog, FileFilter
from .confirmation import ConfirmationDialog, MessageType, confirm, alert, error, info
from .progress import ProgressDialog, ProgressInfo, ProgressWorker
from .forms import FormDialog, FormField, FieldType, ValidationRule
from .notifications import NotificationManager, ToastNotification, NotificationType, NotificationPosition, NotificationData
# Theme dialogs temporarily commented due to missing dependencies
# from .theme_selector_dialog import ThemeSelectorDialog
# from .theme_customizer_dialog import ThemeCustomizerDialog
# from .theme_accessibility_dialog import AccessibilityDialog

__all__ = [
    'BaseDialog',
    'DialogResult',
    'DialogButton',
    'DialogManager',
    'FileDialog',
    'FileFilter',
    'ConfirmationDialog',
    'MessageType',
    'confirm',
    'alert',
    'error',
    'info',
    'ProgressDialog',
    'ProgressInfo',
    'ProgressWorker',
    'FormDialog',
    'FormField',
    'FieldType',
    'ValidationRule',
    'NotificationManager',
    'ToastNotification',
    'NotificationType',
    'NotificationPosition',
    'NotificationData',
    # 'ThemeSelectorDialog',
    # 'ThemeCustomizerDialog',
    # 'AccessibilityDialog'
]