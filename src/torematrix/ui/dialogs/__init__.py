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
from .confirmation import ConfirmationDialog
from .progress import ProgressDialog
from .forms import FormDialog, FormField
from .notifications import NotificationManager, ToastNotification
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
    'ProgressDialog',
    'FormDialog',
    'FormField',
    'NotificationManager',
    'ToastNotification',
    # 'ThemeSelectorDialog',
    # 'ThemeCustomizerDialog',
    # 'AccessibilityDialog'
]