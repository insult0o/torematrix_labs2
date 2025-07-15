"""Error handling and recovery system for robust editor management

Provides comprehensive error handling with classification, recovery strategies,
and user-friendly error reporting to ensure reliable editor operations.
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import traceback
import time
import uuid

try:
    from PyQt6.QtWidgets import QWidget, QMessageBox
    from PyQt6.QtCore import QObject, pyqtSignal, QTimer
except ImportError:
    # Mock classes for environments without PyQt6
    class QWidget:
        def __init__(self, parent=None):
            pass
            
    class QObject:
        def __init__(self, parent=None):
            pass
            
    class QMessageBox:
        Critical = Warning = Information = Question = 0
        @staticmethod
        def critical(parent, title, text): pass
        @staticmethod
        def warning(parent, title, text): pass
        
    class QTimer:
        def __init__(self):
            pass
        def singleShot(ms, func): pass
            
    def pyqtSignal(*args):
        return lambda: None


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification"""
    VALIDATION = "validation"
    NETWORK = "network"
    PERMISSION = "permission"
    DATA_CORRUPTION = "data_corruption"
    RESOURCE = "resource"
    UI = "ui"
    SYSTEM = "system"
    UNKNOWN = "unknown"


class RecoveryStrategy(Enum):
    """Recovery strategies for different error types"""
    RETRY = "retry"
    ROLLBACK = "rollback"
    RESET = "reset"
    SAFE_MODE = "safe_mode"
    GRACEFUL_FAIL = "graceful_fail"


@dataclass
class ErrorRecord:
    """Record of an error occurrence"""
    error_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    error_type: str = ""
    message: str = ""
    details: str = ""
    category: ErrorCategory = ErrorCategory.UNKNOWN
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    component: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    traceback_text: str = ""
    recovery_attempted: bool = False
    recovery_successful: bool = False
    user_notified: bool = False


class ErrorClassifier:
    """Classifies errors into categories and assigns severity"""
    
    def __init__(self):
        self.classification_rules = {
            # Validation errors
            ValueError: (ErrorCategory.VALIDATION, ErrorSeverity.LOW),
            TypeError: (ErrorCategory.VALIDATION, ErrorSeverity.MEDIUM),
            
            # Network errors
            ConnectionError: (ErrorCategory.NETWORK, ErrorSeverity.HIGH),
            TimeoutError: (ErrorCategory.NETWORK, ErrorSeverity.MEDIUM),
            
            # Permission errors
            PermissionError: (ErrorCategory.PERMISSION, ErrorSeverity.HIGH),
            
            # Resource errors
            MemoryError: (ErrorCategory.RESOURCE, ErrorSeverity.CRITICAL),
            OSError: (ErrorCategory.SYSTEM, ErrorSeverity.HIGH),
            
            # Default fallback
            Exception: (ErrorCategory.UNKNOWN, ErrorSeverity.MEDIUM),
        }
        
    def classify_error(self, error: Exception) -> tuple[ErrorCategory, ErrorSeverity]:
        """Classify error by type"""
        error_type = type(error)
        
        # Check exact match first
        if error_type in self.classification_rules:
            return self.classification_rules[error_type]
            
        # Check inheritance chain
        for rule_type, (category, severity) in self.classification_rules.items():
            if isinstance(error, rule_type):
                return category, severity
                
        return ErrorCategory.UNKNOWN, ErrorSeverity.MEDIUM


class RecoveryManager:
    """Manages recovery strategies for different error types"""
    
    def __init__(self):
        self.recovery_strategies = {
            ErrorCategory.VALIDATION: RecoveryStrategy.ROLLBACK,
            ErrorCategory.NETWORK: RecoveryStrategy.RETRY,
            ErrorCategory.PERMISSION: RecoveryStrategy.GRACEFUL_FAIL,
            ErrorCategory.DATA_CORRUPTION: RecoveryStrategy.RESET,
            ErrorCategory.RESOURCE: RecoveryStrategy.SAFE_MODE,
            ErrorCategory.UI: RecoveryStrategy.RETRY,
            ErrorCategory.SYSTEM: RecoveryStrategy.GRACEFUL_FAIL,
            ErrorCategory.UNKNOWN: RecoveryStrategy.ROLLBACK,
        }
        
        self.retry_counts = {}
        self.max_retries = 3
        
    def get_recovery_strategy(self, category: ErrorCategory, error_record: ErrorRecord) -> RecoveryStrategy:
        """Get appropriate recovery strategy for error category"""
        # Check if we've exceeded retry limit
        if category == ErrorCategory.NETWORK:
            retry_count = self.retry_counts.get(error_record.component, 0)
            if retry_count >= self.max_retries:
                return RecoveryStrategy.GRACEFUL_FAIL
                
        return self.recovery_strategies.get(category, RecoveryStrategy.ROLLBACK)
        
    def execute_recovery(self, strategy: RecoveryStrategy, context: Dict[str, Any]) -> bool:
        """Execute recovery strategy"""
        try:
            if strategy == RecoveryStrategy.RETRY:
                return self._retry_operation(context)
            elif strategy == RecoveryStrategy.ROLLBACK:
                return self._rollback_changes(context)
            elif strategy == RecoveryStrategy.RESET:
                return self._reset_component(context)
            elif strategy == RecoveryStrategy.SAFE_MODE:
                return self._enter_safe_mode(context)
            elif strategy == RecoveryStrategy.GRACEFUL_FAIL:
                return self._graceful_failure(context)
            else:
                return False
        except Exception:
            return False
            
    def _retry_operation(self, context: Dict[str, Any]) -> bool:
        """Retry the failed operation"""
        component = context.get('component')
        operation = context.get('operation')
        
        if component and operation:
            # Increment retry count
            self.retry_counts[component] = self.retry_counts.get(component, 0) + 1
            
            # Add delay before retry
            QTimer.singleShot(1000, lambda: self._execute_operation(operation, context))
            return True
        return False
        
    def _rollback_changes(self, context: Dict[str, Any]) -> bool:
        """Rollback changes to previous state"""
        editor = context.get('editor')
        if editor and hasattr(editor, 'cancel_editing'):
            return editor.cancel_editing()
        return False
        
    def _reset_component(self, context: Dict[str, Any]) -> bool:
        """Reset component to initial state"""
        editor = context.get('editor')
        if editor and hasattr(editor, 'reset'):
            return editor.reset()
        return False
        
    def _enter_safe_mode(self, context: Dict[str, Any]) -> bool:
        """Enter safe mode with limited functionality"""
        editor = context.get('editor')
        if editor and hasattr(editor, 'enable_safe_mode'):
            return editor.enable_safe_mode()
        return False
        
    def _graceful_failure(self, context: Dict[str, Any]) -> bool:
        """Handle graceful failure"""
        # Log the failure and continue
        return True
        
    def _execute_operation(self, operation: Callable, context: Dict[str, Any]):
        """Execute operation with error handling"""
        try:
            operation()
        except Exception as e:
            # Handle retry failure
            pass


class UserNotificationManager:
    """Manages user notifications for errors"""
    
    def __init__(self, parent_widget: Optional[QWidget] = None):
        self.parent_widget = parent_widget
        self.notification_history = []
        self.suppressed_notifications = set()
        
    def notify_user(self, error_record: ErrorRecord, show_details: bool = False) -> bool:
        """Notify user about error"""
        if error_record.error_id in self.suppressed_notifications:
            return False
            
        # Determine notification type based on severity
        if error_record.severity == ErrorSeverity.CRITICAL:
            return self._show_critical_error(error_record, show_details)
        elif error_record.severity == ErrorSeverity.HIGH:
            return self._show_warning(error_record, show_details)
        elif error_record.severity == ErrorSeverity.MEDIUM:
            return self._show_information(error_record, show_details)
        else:
            # Low severity - just log
            return True
            
    def _show_critical_error(self, error_record: ErrorRecord, show_details: bool) -> bool:
        """Show critical error dialog"""
        title = "Critical Error"
        message = f"A critical error occurred: {error_record.message}"
        
        if show_details:
            message += f"\n\nDetails: {error_record.details}"
            
        QMessageBox.critical(self.parent_widget, title, message)
        error_record.user_notified = True
        return True
        
    def _show_warning(self, error_record: ErrorRecord, show_details: bool) -> bool:
        """Show warning dialog"""
        title = "Warning"
        message = f"An error occurred: {error_record.message}"
        
        if show_details:
            message += f"\n\nDetails: {error_record.details}"
            
        QMessageBox.warning(self.parent_widget, title, message)
        error_record.user_notified = True
        return True
        
    def _show_information(self, error_record: ErrorRecord, show_details: bool) -> bool:
        """Show information dialog"""
        title = "Information"
        message = error_record.message
        
        QMessageBox.information(self.parent_widget, title, message)
        error_record.user_notified = True
        return True
        
    def suppress_notification(self, error_id: str):
        """Suppress future notifications for specific error"""
        self.suppressed_notifications.add(error_id)


class EditorErrorHandler(QObject):
    """Main error handler for inline editors"""
    
    # Signals
    error_occurred = pyqtSignal(object)  # ErrorRecord
    recovery_completed = pyqtSignal(str, bool)  # error_id, successful
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.classifier = ErrorClassifier()
        self.recovery_manager = RecoveryManager()
        self.notification_manager = UserNotificationManager()
        self.error_log = []
        
    def handle_error(self, error: Exception, component: str = "", context: Dict[str, Any] = None) -> ErrorRecord:
        """Handle an error with full classification, recovery, and notification"""
        context = context or {}
        
        # Create error record
        error_record = self._create_error_record(error, component, context)
        
        # Classify error
        category, severity = self.classifier.classify_error(error)
        error_record.category = category
        error_record.severity = severity
        
        # Log error
        self.error_log.append(error_record)
        self.error_occurred.emit(error_record)
        
        # Attempt recovery
        recovery_strategy = self.recovery_manager.get_recovery_strategy(category, error_record)
        error_record.recovery_attempted = True
        
        recovery_context = {**context, 'error_record': error_record}
        recovery_successful = self.recovery_manager.execute_recovery(recovery_strategy, recovery_context)
        error_record.recovery_successful = recovery_successful
        
        # Notify user if needed
        if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            self.notification_manager.notify_user(error_record, show_details=True)
        elif severity == ErrorSeverity.MEDIUM and not recovery_successful:
            self.notification_manager.notify_user(error_record, show_details=False)
            
        self.recovery_completed.emit(error_record.error_id, recovery_successful)
        return error_record
        
    def _create_error_record(self, error: Exception, component: str, context: Dict[str, Any]) -> ErrorRecord:
        """Create detailed error record"""
        return ErrorRecord(
            error_type=type(error).__name__,
            message=str(error),
            details=getattr(error, 'details', ''),
            component=component,
            context=context,
            traceback_text=traceback.format_exc()
        )
        
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics"""
        total_errors = len(self.error_log)
        if total_errors == 0:
            return {'total_errors': 0}
            
        recovery_successful = sum(1 for e in self.error_log if e.recovery_successful)
        
        category_counts = {}
        severity_counts = {}
        
        for error in self.error_log:
            category_counts[error.category.value] = category_counts.get(error.category.value, 0) + 1
            severity_counts[error.severity.value] = severity_counts.get(error.severity.value, 0) + 1
            
        return {
            'total_errors': total_errors,
            'recovery_success_rate': recovery_successful / total_errors,
            'category_breakdown': category_counts,
            'severity_breakdown': severity_counts
        }
        
    def clear_error_log(self):
        """Clear error log"""
        self.error_log.clear()


# Export public API
__all__ = [
    'EditorErrorHandler',
    'ErrorRecord',
    'ErrorSeverity',
    'ErrorCategory',
    'RecoveryStrategy',
    'ErrorClassifier',
    'RecoveryManager',
    'UserNotificationManager'
]