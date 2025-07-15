"""
Error Handler for Hierarchical Element List

Provides comprehensive error handling, recovery mechanisms,
and user-friendly error reporting for production environments.
"""

import logging
import traceback
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass
from enum import Enum
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QWidget, QMessageBox

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ElementListError:
    """Error information container"""
    error_id: str
    severity: ErrorSeverity
    message: str
    details: str
    component: str
    timestamp: float
    recovery_actions: List[str] = None
    user_message: str = ""
    
    def __post_init__(self):
        if self.recovery_actions is None:
            self.recovery_actions = []


class ElementListErrorHandler(QObject):
    """
    Comprehensive error handler for element list operations
    
    Provides error capture, logging, recovery mechanisms,
    and user-friendly error reporting.
    """
    
    # Signals
    error_occurred = pyqtSignal(object)  # ElementListError
    error_recovered = pyqtSignal(str)  # error_id
    critical_error = pyqtSignal(object)  # ElementListError
    
    def __init__(self, element_list_widget: QWidget, parent: Optional[QObject] = None):
        super().__init__(parent)
        
        self.element_list = element_list_widget
        self.show_user_dialogs = True
        self.auto_recovery_enabled = True
        
        # Error tracking
        self._error_history: List[ElementListError] = []
        self._error_count = 0
        self._recovery_handlers: Dict[str, Callable] = {}
        
        # Setup default recovery handlers
        self._setup_default_recovery_handlers()
        
        logger.info("ElementListErrorHandler initialized")
    
    def handle_error(self, error: Exception, component: str = "unknown", 
                    context: Optional[Dict[str, Any]] = None) -> str:
        """Handle an error with appropriate logging and recovery"""
        import time
        
        error_id = f"err_{int(time.time())}_{self._error_count}"
        self._error_count += 1
        
        # Determine severity
        severity = self._determine_severity(error, component)
        
        # Create error object
        element_error = ElementListError(
            error_id=error_id,
            severity=severity,
            message=str(error),
            details=traceback.format_exc(),
            component=component,
            timestamp=time.time(),
            user_message=self._create_user_message(error, component)
        )
        
        # Add to history
        self._error_history.append(element_error)
        
        # Log error
        self._log_error(element_error, context)
        
        # Emit signal
        self.error_occurred.emit(element_error)
        
        # Attempt recovery
        if self.auto_recovery_enabled:
            self._attempt_recovery(element_error)
        
        # Show user dialog if appropriate
        if self.show_user_dialogs and severity in (ErrorSeverity.ERROR, ErrorSeverity.CRITICAL):
            self._show_user_error_dialog(element_error)
        
        return error_id
    
    def register_recovery_handler(self, error_pattern: str, handler: Callable) -> None:
        """Register a recovery handler for specific error patterns"""
        self._recovery_handlers[error_pattern] = handler
        logger.debug(f"Registered recovery handler for pattern: {error_pattern}")
    
    def attempt_manual_recovery(self, error_id: str) -> bool:
        """Attempt manual recovery for a specific error"""
        error = self._find_error_by_id(error_id)
        if not error:
            return False
        
        return self._attempt_recovery(error)
    
    def get_error_history(self, limit: Optional[int] = None) -> List[ElementListError]:
        """Get error history"""
        if limit:
            return self._error_history[-limit:]
        return self._error_history.copy()
    
    def clear_error_history(self) -> None:
        """Clear error history"""
        self._error_history.clear()
        logger.debug("Error history cleared")
    
    def _determine_severity(self, error: Exception, component: str) -> ErrorSeverity:
        """Determine error severity based on error type and component"""
        if isinstance(error, (MemoryError, SystemExit, KeyboardInterrupt)):
            return ErrorSeverity.CRITICAL
        elif isinstance(error, (FileNotFoundError, PermissionError, ConnectionError)):
            return ErrorSeverity.ERROR
        elif isinstance(error, (ValueError, TypeError, AttributeError)):
            if component in ["core", "data_loading", "state_management"]:
                return ErrorSeverity.ERROR
            return ErrorSeverity.WARNING
        else:
            return ErrorSeverity.WARNING
    
    def _create_user_message(self, error: Exception, component: str) -> str:
        """Create user-friendly error message"""
        error_type = type(error).__name__
        
        user_messages = {
            "FileNotFoundError": "Could not find the required file. Please check if the file exists.",
            "PermissionError": "Permission denied. Please check file permissions.",
            "ConnectionError": "Connection failed. Please check your network connection.",
            "MemoryError": "Not enough memory to complete the operation.",
            "ValueError": "Invalid data encountered. Please check your input.",
            "TypeError": "Data type mismatch occurred.",
            "AttributeError": f"Component '{component}' encountered an internal error."
        }
        
        base_message = user_messages.get(error_type, "An unexpected error occurred.")
        return f"{base_message} ({error_type})"
    
    def _log_error(self, error: ElementListError, context: Optional[Dict[str, Any]]) -> None:
        """Log error with appropriate level"""
        log_message = f"[{error.component}] {error.message}"
        
        if context:
            log_message += f" Context: {context}"
        
        if error.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message, extra={"error_details": error.details})
        elif error.severity == ErrorSeverity.ERROR:
            logger.error(log_message, extra={"error_details": error.details})
        elif error.severity == ErrorSeverity.WARNING:
            logger.warning(log_message)
        else:
            logger.info(log_message)
    
    def _attempt_recovery(self, error: ElementListError) -> bool:
        """Attempt to recover from an error"""
        try:
            # Try specific recovery handlers
            for pattern, handler in self._recovery_handlers.items():
                if pattern in error.message.lower() or pattern in error.component.lower():
                    if handler(error):
                        self.error_recovered.emit(error.error_id)
                        logger.info(f"Recovered from error {error.error_id} using {pattern} handler")
                        return True
            
            # Try default recovery based on component
            if self._default_recovery(error):
                self.error_recovered.emit(error.error_id)
                logger.info(f"Recovered from error {error.error_id} using default recovery")
                return True
            
            return False
            
        except Exception as recovery_error:
            logger.error(f"Recovery attempt failed for {error.error_id}: {recovery_error}")
            return False
    
    def _default_recovery(self, error: ElementListError) -> bool:
        """Default recovery mechanisms"""
        try:
            if error.component == "tree_view":
                # Try refreshing the tree view
                if hasattr(self.element_list, 'refresh'):
                    self.element_list.refresh()
                    return True
            elif error.component == "data_loading":
                # Try clearing cache and reloading
                if hasattr(self.element_list, 'clear_cache'):
                    self.element_list.clear_cache()
                return True
            elif error.component == "selection":
                # Try clearing selection
                if hasattr(self.element_list, 'clear_selection'):
                    self.element_list.clear_selection()
                return True
            
            return False
            
        except Exception:
            return False
    
    def _show_user_error_dialog(self, error: ElementListError) -> None:
        """Show error dialog to user"""
        try:
            msg_box = QMessageBox()
            
            if error.severity == ErrorSeverity.CRITICAL:
                msg_box.setIcon(QMessageBox.Icon.Critical)
                msg_box.setWindowTitle("Critical Error")
            else:
                msg_box.setIcon(QMessageBox.Icon.Warning)
                msg_box.setWindowTitle("Error")
            
            msg_box.setText(error.user_message)
            msg_box.setDetailedText(error.details)
            
            # Add recovery actions if available
            if error.recovery_actions:
                msg_box.setInformativeText("Suggested actions:\n" + "\n".join(error.recovery_actions))
            
            msg_box.exec()
            
        except Exception as dialog_error:
            logger.error(f"Failed to show error dialog: {dialog_error}")
    
    def _setup_default_recovery_handlers(self) -> None:
        """Setup default recovery handlers for common error patterns"""
        def refresh_handler(error: ElementListError) -> bool:
            """Recovery handler that refreshes the tree"""
            if hasattr(self.element_list, 'refresh'):
                self.element_list.refresh()
                return True
            return False
        
        def clear_selection_handler(error: ElementListError) -> bool:
            """Recovery handler that clears selection"""
            if hasattr(self.element_list, 'clear_selection'):
                self.element_list.clear_selection()
                return True
            return False
        
        # Register default handlers
        self.register_recovery_handler("tree", refresh_handler)
        self.register_recovery_handler("selection", clear_selection_handler)
        self.register_recovery_handler("view", refresh_handler)
    
    def _find_error_by_id(self, error_id: str) -> Optional[ElementListError]:
        """Find error by ID in history"""
        for error in self._error_history:
            if error.error_id == error_id:
                return error
        return None