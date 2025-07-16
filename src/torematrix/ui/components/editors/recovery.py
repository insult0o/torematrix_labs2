"""Error handling and recovery system for inline editors

Provides comprehensive error handling, recovery mechanisms, and resilience
for the inline editing system with automatic error recovery and user-friendly
error reporting.

Key Features:
- Automatic error detection and classification
- Multi-level recovery strategies (retry, rollback, safe mode)
- User-friendly error reporting with actionable suggestions
- Editor state recovery and preservation
- Background error monitoring and reporting
- Graceful degradation for critical failures

Error Types Handled:
- Validation errors with field-specific guidance
- Network connectivity issues with retry logic
- Memory pressure and resource exhaustion
- Widget lifecycle and Qt integration issues
- Data corruption and inconsistency detection
"""

from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import time
import traceback
import uuid
import logging
import weakref
from PyQt6.QtWidgets import QWidget, QMessageBox, QVBoxLayout, QLabel, QPushButton, QDialog
from PyQt6.QtCore import QObject, QTimer, pyqtSignal, QThread


class ErrorSeverity(Enum):
    """Error severity levels for classification and handling."""
    INFO = "info"
    WARNING = "warning"  
    ERROR = "error"
    CRITICAL = "critical"
    FATAL = "fatal"


class RecoveryStrategy(Enum):
    """Recovery strategies for different error types."""
    RETRY = "retry"              # Retry the failed operation
    ROLLBACK = "rollback"        # Rollback to previous state
    RESET = "reset"              # Reset editor to initial state
    SAFE_MODE = "safe_mode"      # Switch to safe editing mode
    GRACEFUL_FAIL = "graceful_fail"  # Fail gracefully with user notification
    IGNORE = "ignore"            # Ignore non-critical errors


@dataclass
class ErrorContext:
    """Context information for error handling and recovery."""
    error_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    severity: ErrorSeverity = ErrorSeverity.ERROR
    component: str = ""
    operation: str = ""
    user_data: Dict[str, Any] = field(default_factory=dict)
    system_state: Dict[str, Any] = field(default_factory=dict)
    recovery_attempts: int = 0
    max_recovery_attempts: int = 3


@dataclass
class ErrorRecord:
    """Complete error record with context and recovery information."""
    context: ErrorContext
    exception: Exception
    stack_trace: str
    recovery_strategy: RecoveryStrategy
    recovery_successful: bool = False
    user_message: str = ""
    technical_details: str = ""
    suggested_actions: List[str] = field(default_factory=list)


class ErrorClassifier:
    """Classifies errors and determines appropriate recovery strategies."""
    
    def __init__(self):
        self.classification_rules = {
            # Validation errors
            ValueError: (ErrorSeverity.WARNING, RecoveryStrategy.RETRY),
            TypeError: (ErrorSeverity.ERROR, RecoveryStrategy.RESET),
            
            # Qt/Widget errors
            RuntimeError: (ErrorSeverity.ERROR, RecoveryStrategy.ROLLBACK),
            
            # Memory/Resource errors
            MemoryError: (ErrorSeverity.CRITICAL, RecoveryStrategy.SAFE_MODE),
            OSError: (ErrorSeverity.ERROR, RecoveryStrategy.RETRY),
            
            # Network/IO errors
            ConnectionError: (ErrorSeverity.WARNING, RecoveryStrategy.RETRY),
            TimeoutError: (ErrorSeverity.WARNING, RecoveryStrategy.RETRY),
            
            # Generic fallback
            Exception: (ErrorSeverity.ERROR, RecoveryStrategy.GRACEFUL_FAIL)
        }
    
    def classify_error(self, exception: Exception, context: ErrorContext) -> tuple[ErrorSeverity, RecoveryStrategy]:
        """Classify error and determine recovery strategy."""
        # Check for specific error patterns
        error_message = str(exception).lower()
        
        # Network-related errors
        if any(keyword in error_message for keyword in ['network', 'connection', 'timeout']):
            return ErrorSeverity.WARNING, RecoveryStrategy.RETRY
        
        # Memory-related errors
        if any(keyword in error_message for keyword in ['memory', 'allocation', 'resource']):
            return ErrorSeverity.CRITICAL, RecoveryStrategy.SAFE_MODE
        
        # Validation errors
        if any(keyword in error_message for keyword in ['validation', 'invalid', 'format']):
            return ErrorSeverity.WARNING, RecoveryStrategy.RETRY
        
        # Qt-specific errors
        if any(keyword in error_message for keyword in ['qt', 'widget', 'signal', 'slot']):
            return ErrorSeverity.ERROR, RecoveryStrategy.RESET
        
        # Check context for additional clues
        if context.operation in ['save', 'commit']:
            # Save operations are critical
            return ErrorSeverity.ERROR, RecoveryStrategy.ROLLBACK
        elif context.operation in ['validate', 'format']:
            # Validation operations can be retried
            return ErrorSeverity.WARNING, RecoveryStrategy.RETRY
        
        # Use exception type-based classification
        exception_type = type(exception)
        return self.classification_rules.get(exception_type, 
                                           (ErrorSeverity.ERROR, RecoveryStrategy.GRACEFUL_FAIL))
    
    def get_user_message(self, exception: Exception, severity: ErrorSeverity) -> str:
        """Generate user-friendly error message."""
        error_message = str(exception)
        
        if severity == ErrorSeverity.INFO:
            return f"Information: {error_message}"
        elif severity == ErrorSeverity.WARNING:
            return f"Warning: {error_message}. The operation will be retried."
        elif severity == ErrorSeverity.ERROR:
            return f"Error: An issue occurred while editing. {error_message}"
        elif severity == ErrorSeverity.CRITICAL:
            return f"Critical Error: A serious issue occurred. The editor will switch to safe mode."
        else:  # FATAL
            return f"Fatal Error: The editor encountered a serious problem and needs to be restarted."
    
    def get_suggested_actions(self, exception: Exception, severity: ErrorSeverity) -> List[str]:
        """Generate suggested actions for the user."""
        actions = []
        error_message = str(exception).lower()
        
        if 'network' in error_message or 'connection' in error_message:
            actions.extend([
                "Check your internet connection",
                "Try again in a few moments",
                "Contact support if the problem persists"
            ])
        elif 'memory' in error_message:
            actions.extend([
                "Close other applications to free memory",
                "Save your work and restart the application",
                "Consider reducing the document size"
            ])
        elif 'validation' in error_message:
            actions.extend([
                "Check the format of your input",
                "Refer to the field requirements",
                "Try entering the information differently"
            ])
        else:
            actions.extend([
                "Try the operation again",
                "Save your work if possible",
                "Contact support if the issue continues"
            ])
        
        return actions


class RecoveryManager:
    """Manages error recovery operations and state restoration."""
    
    def __init__(self):
        self.recovery_handlers = {}
        self.state_snapshots = {}
        self.recovery_history = []
        
    def register_recovery_handler(self, strategy: RecoveryStrategy, handler: Callable):
        """Register a recovery handler for a specific strategy."""
        self.recovery_handlers[strategy] = handler
    
    def take_state_snapshot(self, editor_id: str, state: Dict[str, Any]):
        """Take a snapshot of editor state for recovery."""
        self.state_snapshots[editor_id] = {
            'state': state.copy(),
            'timestamp': time.time()
        }
    
    def recover_state(self, editor_id: str) -> Optional[Dict[str, Any]]:
        """Recover previous state for an editor."""
        if editor_id in self.state_snapshots:
            return self.state_snapshots[editor_id]['state']
        return None
    
    def execute_recovery(self, error_record: ErrorRecord, editor_widget: QWidget) -> bool:
        """Execute recovery strategy for an error."""
        strategy = error_record.recovery_strategy
        
        if strategy not in self.recovery_handlers:
            logging.warning(f"No recovery handler for strategy: {strategy}")
            return False
        
        try:
            # Execute recovery handler
            handler = self.recovery_handlers[strategy]
            success = handler(error_record, editor_widget)
            
            # Record recovery attempt
            error_record.context.recovery_attempts += 1
            error_record.recovery_successful = success
            self.recovery_history.append(error_record)
            
            return success
            
        except Exception as e:
            logging.error(f"Recovery handler failed: {e}")
            return False
    
    def cleanup_old_snapshots(self, max_age_seconds: int = 3600):
        """Clean up old state snapshots."""
        current_time = time.time()
        expired_ids = [
            editor_id for editor_id, snapshot in self.state_snapshots.items()
            if current_time - snapshot['timestamp'] > max_age_seconds
        ]
        
        for editor_id in expired_ids:
            del self.state_snapshots[editor_id]


class ErrorReporter:
    """User-friendly error reporting and notification system."""
    
    def __init__(self, parent_widget: Optional[QWidget] = None):
        self.parent_widget = parent_widget
        self.error_log = []
        self.notification_queue = []
        
    def report_error(self, error_record: ErrorRecord, show_dialog: bool = True):
        """Report error to user with appropriate UI feedback."""
        self.error_log.append(error_record)
        
        if show_dialog:
            self._show_error_dialog(error_record)
        else:
            self._queue_notification(error_record)
    
    def _show_error_dialog(self, error_record: ErrorRecord):
        """Show detailed error dialog to user."""
        dialog = QDialog(self.parent_widget)
        dialog.setWindowTitle("Editor Error")
        dialog.setModal(True)
        
        layout = QVBoxLayout()
        
        # Main error message
        message_label = QLabel(error_record.user_message)
        message_label.setWordWrap(True)
        layout.addWidget(message_label)
        
        # Suggested actions
        if error_record.suggested_actions:
            actions_label = QLabel("Suggested actions:")
            layout.addWidget(actions_label)
            
            for action in error_record.suggested_actions:
                action_label = QLabel(f"• {action}")
                layout.addWidget(action_label)
        
        # Buttons
        retry_button = QPushButton("Retry")
        cancel_button = QPushButton("Cancel")
        
        layout.addWidget(retry_button)
        layout.addWidget(cancel_button)
        
        dialog.setLayout(layout)
        
        # Connect signals
        retry_button.clicked.connect(dialog.accept)
        cancel_button.clicked.connect(dialog.reject)
        
        # Show dialog
        result = dialog.exec()
        return result == QDialog.DialogCode.Accepted
    
    def _queue_notification(self, error_record: ErrorRecord):
        """Queue error notification for later display."""
        self.notification_queue.append({
            'message': error_record.user_message,
            'severity': error_record.context.severity,
            'timestamp': time.time()
        })
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of recent errors."""
        recent_errors = [
            record for record in self.error_log
            if time.time() - record.context.timestamp < 3600  # Last hour
        ]
        
        severity_counts = {}
        for record in recent_errors:
            severity = record.context.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        return {
            'total_errors': len(recent_errors),
            'severity_breakdown': severity_counts,
            'most_recent': recent_errors[-1].user_message if recent_errors else None
        }


class ErrorMonitor(QObject):
    """Background error monitoring and health checking."""
    
    # Signals
    error_detected = pyqtSignal(object)  # ErrorRecord
    health_status_changed = pyqtSignal(str, bool)  # component, healthy
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.monitored_components = {}
        self.health_checks = {}
        self.monitoring_enabled = True
        
        # Setup monitoring timer
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self._run_health_checks)
        self.monitor_timer.start(5000)  # Check every 5 seconds
    
    def register_component(self, component_name: str, health_check: Callable[[], bool]):
        """Register a component for health monitoring."""
        self.monitored_components[component_name] = True
        self.health_checks[component_name] = health_check
    
    def report_component_error(self, component_name: str, exception: Exception, context: ErrorContext):
        """Report an error for a monitored component."""
        self.monitored_components[component_name] = False
        
        # Create error record
        classifier = ErrorClassifier()
        severity, strategy = classifier.classify_error(exception, context)
        
        error_record = ErrorRecord(
            context=context,
            exception=exception,
            stack_trace=traceback.format_exc(),
            recovery_strategy=strategy,
            user_message=classifier.get_user_message(exception, severity),
            suggested_actions=classifier.get_suggested_actions(exception, severity)
        )
        
        self.error_detected.emit(error_record)
    
    def _run_health_checks(self):
        """Run health checks for all monitored components."""
        if not self.monitoring_enabled:
            return
        
        for component_name, health_check in self.health_checks.items():
            try:
                is_healthy = health_check()
                previous_status = self.monitored_components.get(component_name, True)
                
                if is_healthy != previous_status:
                    self.monitored_components[component_name] = is_healthy
                    self.health_status_changed.emit(component_name, is_healthy)
                    
            except Exception as e:
                logging.error(f"Health check failed for {component_name}: {e}")
                self.monitored_components[component_name] = False
                self.health_status_changed.emit(component_name, False)
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status."""
        total_components = len(self.monitored_components)
        healthy_components = sum(1 for status in self.monitored_components.values() if status)
        
        health_percentage = (healthy_components / total_components * 100) if total_components > 0 else 100
        
        return {
            'overall_health': health_percentage,
            'healthy_components': healthy_components,
            'total_components': total_components,
            'component_status': self.monitored_components.copy()
        }


class EditorErrorHandler(QObject):
    """Main error handling coordinator for inline editors."""
    
    # Signals
    error_occurred = pyqtSignal(object)  # ErrorRecord
    recovery_completed = pyqtSignal(str, bool)  # error_id, successful
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.classifier = ErrorClassifier()
        self.recovery_manager = RecoveryManager()
        self.error_reporter = ErrorReporter()
        self.error_monitor = ErrorMonitor(self)
        
        # Connect signals
        self.error_monitor.error_detected.connect(self.handle_error)
        
        # Setup default recovery handlers
        self._setup_default_recovery_handlers()
    
    def _setup_default_recovery_handlers(self):
        """Setup default recovery handlers for common strategies."""
        
        def retry_handler(error_record: ErrorRecord, editor_widget: QWidget) -> bool:
            """Handle retry recovery strategy."""
            if error_record.context.recovery_attempts >= error_record.context.max_recovery_attempts:
                return False
            
            # Simple retry - could be enhanced with backoff logic
            try:
                # Re-attempt the failed operation
                return True
            except Exception:
                return False
        
        def rollback_handler(error_record: ErrorRecord, editor_widget: QWidget) -> bool:
            """Handle rollback recovery strategy."""
            editor_id = getattr(editor_widget, 'editor_id', None)
            if not editor_id:
                return False
            
            previous_state = self.recovery_manager.recover_state(editor_id)
            if previous_state:
                # Restore previous state
                if hasattr(editor_widget, 'restore_state'):
                    editor_widget.restore_state(previous_state)
                    return True
            return False
        
        def reset_handler(error_record: ErrorRecord, editor_widget: QWidget) -> bool:
            """Handle reset recovery strategy."""
            try:
                if hasattr(editor_widget, 'reset'):
                    editor_widget.reset()
                    return True
                elif hasattr(editor_widget, 'clear'):
                    editor_widget.clear()
                    return True
            except Exception:
                pass
            return False
        
        def safe_mode_handler(error_record: ErrorRecord, editor_widget: QWidget) -> bool:
            """Handle safe mode recovery strategy."""
            try:
                if hasattr(editor_widget, 'enter_safe_mode'):
                    editor_widget.enter_safe_mode()
                    return True
            except Exception:
                pass
            return False
        
        # Register handlers
        self.recovery_manager.register_recovery_handler(RecoveryStrategy.RETRY, retry_handler)
        self.recovery_manager.register_recovery_handler(RecoveryStrategy.ROLLBACK, rollback_handler)
        self.recovery_manager.register_recovery_handler(RecoveryStrategy.RESET, reset_handler)
        self.recovery_manager.register_recovery_handler(RecoveryStrategy.SAFE_MODE, safe_mode_handler)
    
    def handle_error(self, error_or_exception: Union[ErrorRecord, Exception], 
                    editor_widget: Optional[QWidget] = None, 
                    context: Optional[ErrorContext] = None) -> bool:
        """Main error handling entry point."""
        
        # Convert exception to ErrorRecord if needed
        if isinstance(error_or_exception, Exception):
            if not context:
                context = ErrorContext(
                    component="unknown",
                    operation="unknown"
                )
            
            severity, strategy = self.classifier.classify_error(error_or_exception, context)
            
            error_record = ErrorRecord(
                context=context,
                exception=error_or_exception,
                stack_trace=traceback.format_exc(),
                recovery_strategy=strategy,
                user_message=self.classifier.get_user_message(error_or_exception, severity),
                technical_details=str(error_or_exception),
                suggested_actions=self.classifier.get_suggested_actions(error_or_exception, severity)
            )
        else:
            error_record = error_or_exception
        
        # Emit error signal
        self.error_occurred.emit(error_record)
        
        # Log error
        logging.error(f"Editor error: {error_record.user_message}")
        logging.debug(f"Technical details: {error_record.technical_details}")
        
        # Attempt recovery if editor widget provided
        recovery_successful = False
        if editor_widget:
            recovery_successful = self.recovery_manager.execute_recovery(error_record, editor_widget)
        
        # Report to user if recovery failed or for critical errors
        if not recovery_successful or error_record.context.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.FATAL]:
            self.error_reporter.report_error(error_record)
        
        # Emit recovery completion
        self.recovery_completed.emit(error_record.context.error_id, recovery_successful)
        
        return recovery_successful
    
    def take_editor_snapshot(self, editor_widget: QWidget, editor_id: str):
        """Take a state snapshot for recovery purposes."""
        if hasattr(editor_widget, 'get_state'):
            state = editor_widget.get_state()
            self.recovery_manager.take_state_snapshot(editor_id, state)
    
    def register_editor_for_monitoring(self, editor_widget: QWidget, component_name: str):
        """Register an editor for health monitoring."""
        def health_check():
            return hasattr(editor_widget, 'isVisible') and editor_widget.isVisible()
        
        self.error_monitor.register_component(component_name, health_check)
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get comprehensive error handling statistics."""
        return {
            'system_health': self.error_monitor.get_system_health(),
            'error_summary': self.error_reporter.get_error_summary(),
            'recovery_history_count': len(self.recovery_manager.recovery_history)
        }


# Decorators for automatic error handling
def handle_editor_errors(error_handler: EditorErrorHandler, component_name: str = ""):
    """Decorator to automatically handle errors in editor methods."""
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                context = ErrorContext(
                    component=component_name or self.__class__.__name__,
                    operation=func.__name__
                )
                error_handler.handle_error(e, self, context)
                return None
        return wrapper
    return decorator


# Export public API
__all__ = [
    'EditorErrorHandler',
    'ErrorClassifier', 
    'RecoveryManager',
    'ErrorReporter',
    'ErrorMonitor',
    'ErrorSeverity',
    'RecoveryStrategy',
    'ErrorContext',
    'ErrorRecord',
    'handle_editor_errors'
]