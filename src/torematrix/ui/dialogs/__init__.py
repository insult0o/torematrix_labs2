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

from .base import BaseDialog, DialogResult, DialogButton
from .file import FileDialog, FileFilter
from .confirmation import ConfirmationDialog
from .progress import ProgressDialog
from .forms import FormDialog, FormField
from .notifications import NotificationManager, ToastNotification

__all__ = [
    'BaseDialog',
    'DialogResult',
    'DialogButton',
    'FileDialog',
    'FileFilter',
    'ConfirmationDialog',
    'ProgressDialog',
    'FormDialog',
    'FormField',
    'NotificationManager',
    'ToastNotification'
]