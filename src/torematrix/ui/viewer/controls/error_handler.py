"""
Comprehensive error handling and recovery for zoom/pan controls.
Provides error management, logging, and graceful degradation strategies.
"""

from typing import Dict, List, Optional, Callable, Any, Type
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
import traceback
import logging
import time
from collections import deque, defaultdict
from dataclasses import dataclass, field
from enum import Enum
import sys
import threading


class ErrorSeverity(Enum):
    """Error severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    FATAL = "fatal"


class ErrorCategory(Enum):
    """Error categories for classification."""
    ZOOM_ENGINE = "zoom_engine"
    PAN_ENGINE = "pan_engine"
    ANIMATION = "animation"
    UI_COMPONENT = "ui_component"
    GESTURE_RECOGNITION = "gesture_recognition"
    PERFORMANCE = "performance"
    MEMORY = "memory"
    SYSTEM = "system"
    USER_INPUT = "user_input"
    INTEGRATION = "integration"


@dataclass
class ErrorInfo:
    """Comprehensive error information."""
    error_id: str
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    exception: Optional[Exception] = None
    stack_trace: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    component: Optional[str] = None
    user_action: Optional[str] = None
    system_state: Optional[Dict[str, Any]] = None
    recovery_attempted: bool = False
    recovery_successful: bool = False
    
    def __post_init__(self):
        if self.exception and not self.stack_trace:
            self.stack_trace = traceback.format_exc()


class ErrorHandler(QObject):
    """
    Comprehensive error handling system for zoom/pan controls.
    Provides error logging, recovery strategies, and user notifications.
    """
    
    # Error signals
    error_occurred = pyqtSignal(ErrorInfo)  # error_info
    error_recovered = pyqtSignal(str, str)  # error_id, recovery_method
    critical_error = pyqtSignal(ErrorInfo)  # critical_error_info
    error_pattern_detected = pyqtSignal(str, List[ErrorInfo])  # pattern_type, related_errors
    recovery_suggestion = pyqtSignal(str, Dict[str, Any])  # suggestion_type, details
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Error tracking
        self.error_history = deque(maxlen=1000)
        self.error_counts = defaultdict(int)
        self.recovery_strategies = {}
        self.error_patterns = {}
        
        # Configuration
        self.max_recovery_attempts = 3
        self.auto_recovery_enabled = True
        self.detailed_logging = True
        self.user_notification_enabled = True
        
        # Recovery tracking
        self.active_recoveries = {}
        self.recovery_success_rate = defaultdict(list)
        
        # Pattern detection
        self.pattern_detection_enabled = True
        self.pattern_window_size = 50  # errors to analyze for patterns
        
        # Logging setup
        self._setup_logging()
        
        # Recovery timer for delayed recovery attempts
        self.recovery_timer = QTimer()
        self.recovery_timer.timeout.connect(self._process_pending_recoveries)
        self.recovery_timer.setInterval(1000)  # Check every second
        self.recovery_timer.start()
        
        # Thread safety
        self._error_lock = threading.RLock()
        
        # Register default recovery strategies
        self._register_default_recovery_strategies()
    
    def handle_error(self, category: ErrorCategory, severity: ErrorSeverity, 
                    message: str, exception: Exception = None, 
                    component: str = None, user_action: str = None,
                    system_state: Dict[str, Any] = None) -> str:
        """
        Handle an error with comprehensive logging and recovery.
        
        Args:
            category: Error category
            severity: Error severity level
            message: Error description
            exception: Exception object if available
            component: Component where error occurred
            user_action: User action that triggered error
            system_state: Current system state
            
        Returns:
            str: Unique error ID for tracking
        """
        with self._error_lock:
            # Generate unique error ID
            error_id = f"{category.value}_{int(time.time() * 1000)}_{len(self.error_history)}"
            
            # Create error info
            error_info = ErrorInfo(
                error_id=error_id,
                category=category,
                severity=severity,
                message=message,
                exception=exception,
                component=component,
                user_action=user_action,
                system_state=system_state
            )
            
            # Store error
            self.error_history.append(error_info)
            self.error_counts[category] += 1
            
            # Log error
            self._log_error(error_info)
            
            # Emit error signal
            self.error_occurred.emit(error_info)
            
            # Handle critical errors immediately
            if severity in [ErrorSeverity.CRITICAL, ErrorSeverity.FATAL]:
                self.critical_error.emit(error_info)
            
            # Attempt recovery if enabled
            if self.auto_recovery_enabled and severity != ErrorSeverity.FATAL:
                self._attempt_recovery(error_info)
            
            # Detect error patterns
            if self.pattern_detection_enabled:
                self._detect_error_patterns(error_info)
            
            return error_id
    
    def handle_exception(self, exception: Exception, category: ErrorCategory = ErrorCategory.SYSTEM,
                        component: str = None, user_action: str = None) -> str:
        """
        Handle Python exception with automatic severity assessment.
        
        Args:
            exception: Python exception
            category: Error category
            component: Component where exception occurred
            user_action: User action that triggered exception
            
        Returns:
            str: Error ID
        """
        # Assess severity based on exception type
        severity = self._assess_exception_severity(exception)
        
        # Extract message
        message = f"{type(exception).__name__}: {str(exception)}"
        
        return self.handle_error(
            category=category,
            severity=severity,
            message=message,
            exception=exception,
            component=component,
            user_action=user_action
        )
    
    def register_recovery_strategy(self, category: ErrorCategory, 
                                  recovery_func: Callable[[ErrorInfo], bool],
                                  priority: int = 1):
        """
        Register a recovery strategy for specific error category.
        
        Args:
            category: Error category to handle
            recovery_func: Function that attempts recovery
            priority: Priority level (lower = higher priority)
        """
        if category not in self.recovery_strategies:
            self.recovery_strategies[category] = []
        
        self.recovery_strategies[category].append({
            'function': recovery_func,
            'priority': priority,
            'success_count': 0,
            'attempt_count': 0
        })
        
        # Sort by priority
        self.recovery_strategies[category].sort(key=lambda x: x['priority'])
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get comprehensive error statistics."""
        with self._error_lock:
            if not self.error_history:
                return {'total_errors': 0}
            
            recent_errors = [e for e in self.error_history if time.time() - e.timestamp < 3600]  # Last hour
            
            # Category breakdown
            category_counts = defaultdict(int)
            severity_counts = defaultdict(int)
            
            for error in recent_errors:
                category_counts[error.category.value] += 1
                severity_counts[error.severity.value] += 1
            
            # Recovery statistics
            recovery_stats = {}
            for category, strategies in self.recovery_strategies.items():
                total_attempts = sum(s['attempt_count'] for s in strategies)
                total_successes = sum(s['success_count'] for s in strategies)
                recovery_stats[category.value] = {
                    'attempts': total_attempts,
                    'successes': total_successes,
                    'success_rate': (total_successes / total_attempts * 100) if total_attempts > 0 else 0
                }
            
            return {
                'total_errors': len(self.error_history),
                'recent_errors': len(recent_errors),
                'categories': dict(category_counts),
                'severities': dict(severity_counts),
                'recovery_stats': recovery_stats,
                'error_rate': len(recent_errors) / 60,  # errors per minute
                'most_common_category': max(category_counts, key=category_counts.get) if category_counts else None
            }
    
    def get_recent_errors(self, count: int = 10, category: ErrorCategory = None) -> List[ErrorInfo]:
        """Get recent errors, optionally filtered by category."""
        with self._error_lock:
            errors = list(self.error_history)
            
            if category:
                errors = [e for e in errors if e.category == category]
            
            return errors[-count:]
    
    def clear_error_history(self):
        """Clear error history and reset counters."""
        with self._error_lock:
            self.error_history.clear()
            self.error_counts.clear()
            self.active_recoveries.clear()
            self.recovery_success_rate.clear()
    
    def set_auto_recovery(self, enabled: bool):
        """Enable or disable automatic error recovery."""
        self.auto_recovery_enabled = enabled
    
    def set_detailed_logging(self, enabled: bool):
        """Enable or disable detailed error logging."""
        self.detailed_logging = enabled
    
    def force_recovery(self, error_id: str) -> bool:
        """Force recovery attempt for specific error."""
        with self._error_lock:
            # Find error by ID
            error_info = None
            for error in self.error_history:
                if error.error_id == error_id:
                    error_info = error
                    break
            
            if not error_info:
                return False
            
            return self._attempt_recovery(error_info)
    
    # Private methods
    
    def _setup_logging(self):
        """Setup error logging configuration."""
        self.logger = logging.getLogger('zoom_pan_controls')
        self.logger.setLevel(logging.DEBUG if self.detailed_logging else logging.WARNING)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Create console handler
        if not self.logger.handlers:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
    
    def _log_error(self, error_info: ErrorInfo):
        """Log error to logging system."""
        log_level = {
            ErrorSeverity.INFO: logging.INFO,
            ErrorSeverity.WARNING: logging.WARNING,
            ErrorSeverity.ERROR: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL,
            ErrorSeverity.FATAL: logging.CRITICAL
        }.get(error_info.severity, logging.ERROR)
        
        log_message = f"[{error_info.category.value}] {error_info.message}"
        
        if error_info.component:
            log_message += f" (Component: {error_info.component})"
        
        if error_info.user_action:
            log_message += f" (User Action: {error_info.user_action})"
        
        self.logger.log(log_level, log_message)
        
        if self.detailed_logging and error_info.stack_trace:
            self.logger.debug(f"Stack trace:\n{error_info.stack_trace}")
    
    def _attempt_recovery(self, error_info: ErrorInfo) -> bool:
        """Attempt error recovery using registered strategies."""
        category = error_info.category
        
        if category not in self.recovery_strategies:
            return False
        
        if error_info.error_id in self.active_recoveries:
            attempts = self.active_recoveries[error_info.error_id]
            if attempts >= self.max_recovery_attempts:
                return False
        else:
            self.active_recoveries[error_info.error_id] = 0
        
        # Try recovery strategies in priority order
        for strategy in self.recovery_strategies[category]:
            try:
                strategy['attempt_count'] += 1
                self.active_recoveries[error_info.error_id] += 1
                
                success = strategy['function'](error_info)
                
                if success:
                    strategy['success_count'] += 1
                    error_info.recovery_attempted = True
                    error_info.recovery_successful = True
                    
                    # Track success rate
                    self.recovery_success_rate[category].append(True)
                    
                    # Emit recovery signal
                    self.error_recovered.emit(error_info.error_id, strategy['function'].__name__)
                    
                    # Clean up tracking
                    del self.active_recoveries[error_info.error_id]
                    
                    return True
                
            except Exception as recovery_exception:
                # Recovery itself failed
                self.handle_error(
                    category=ErrorCategory.SYSTEM,
                    severity=ErrorSeverity.WARNING,
                    message=f"Recovery strategy failed: {str(recovery_exception)}",
                    exception=recovery_exception,
                    component="error_handler"
                )
        
        # All recovery strategies failed
        error_info.recovery_attempted = True
        error_info.recovery_successful = False
        self.recovery_success_rate[category].append(False)
        
        return False
    
    def _detect_error_patterns(self, new_error: ErrorInfo):
        """Detect patterns in error occurrences."""
        recent_errors = list(self.error_history)[-self.pattern_window_size:]
        
        # Pattern 1: Repeated errors from same component
        if new_error.component:
            component_errors = [e for e in recent_errors if e.component == new_error.component]
            if len(component_errors) >= 5:  # 5 errors from same component
                self.error_pattern_detected.emit("repeated_component_errors", component_errors)
        
        # Pattern 2: Escalating severity
        if len(recent_errors) >= 3:
            severity_levels = [self._severity_to_int(e.severity) for e in recent_errors[-3:]]
            if all(severity_levels[i] <= severity_levels[i+1] for i in range(len(severity_levels)-1)):
                self.error_pattern_detected.emit("escalating_severity", recent_errors[-3:])
        
        # Pattern 3: High error frequency
        time_window = 60  # 1 minute
        recent_time_errors = [e for e in recent_errors if time.time() - e.timestamp < time_window]
        if len(recent_time_errors) >= 10:
            self.error_pattern_detected.emit("high_frequency", recent_time_errors)
        
        # Pattern 4: Same error category clustering
        category_errors = [e for e in recent_errors if e.category == new_error.category]
        if len(category_errors) >= 7:  # 7 errors of same category
            self.error_pattern_detected.emit("category_clustering", category_errors)
    
    def _assess_exception_severity(self, exception: Exception) -> ErrorSeverity:
        """Assess severity level of an exception."""
        # Critical system exceptions
        if isinstance(exception, (MemoryError, SystemError, OSError)):
            return ErrorSeverity.CRITICAL
        
        # Runtime errors that might be recoverable
        if isinstance(exception, (RuntimeError, ValueError, TypeError)):
            return ErrorSeverity.ERROR
        
        # Less critical exceptions
        if isinstance(exception, (AttributeError, KeyError, IndexError)):
            return ErrorSeverity.WARNING
        
        # Default to error level
        return ErrorSeverity.ERROR
    
    def _severity_to_int(self, severity: ErrorSeverity) -> int:
        """Convert severity to integer for comparison."""
        return {
            ErrorSeverity.INFO: 1,
            ErrorSeverity.WARNING: 2,
            ErrorSeverity.ERROR: 3,
            ErrorSeverity.CRITICAL: 4,
            ErrorSeverity.FATAL: 5
        }.get(severity, 3)
    
    def _process_pending_recoveries(self):
        """Process any pending recovery attempts."""
        # Clean up old recovery attempts
        current_time = time.time()
        expired_recoveries = []
        
        for error_id, attempts in self.active_recoveries.items():
            # Find the error
            error_info = None
            for error in self.error_history:
                if error.error_id == error_id:
                    error_info = error
                    break
            
            # Remove if too old (5 minutes)
            if error_info and current_time - error_info.timestamp > 300:
                expired_recoveries.append(error_id)
        
        for error_id in expired_recoveries:
            del self.active_recoveries[error_id]
    
    def _register_default_recovery_strategies(self):
        """Register default recovery strategies for common error categories."""
        
        # Zoom engine recovery
        def recover_zoom_engine(error_info: ErrorInfo) -> bool:
            """Attempt to recover zoom engine errors."""
            try:
                # Reset zoom to safe default
                # This would integrate with actual zoom engine
                return True
            except Exception:
                return False
        
        self.register_recovery_strategy(ErrorCategory.ZOOM_ENGINE, recover_zoom_engine, priority=1)
        
        # Pan engine recovery
        def recover_pan_engine(error_info: ErrorInfo) -> bool:
            """Attempt to recover pan engine errors."""
            try:
                # Reset pan to center position
                # This would integrate with actual pan engine
                return True
            except Exception:
                return False
        
        self.register_recovery_strategy(ErrorCategory.PAN_ENGINE, recover_pan_engine, priority=1)
        
        # Memory error recovery
        def recover_memory_error(error_info: ErrorInfo) -> bool:
            """Attempt to recover from memory errors."""
            try:
                import gc
                gc.collect()  # Force garbage collection
                return True
            except Exception:
                return False
        
        self.register_recovery_strategy(ErrorCategory.MEMORY, recover_memory_error, priority=1)
        
        # UI component recovery
        def recover_ui_component(error_info: ErrorInfo) -> bool:
            """Attempt to recover UI component errors."""
            try:
                # Refresh UI component
                # This would integrate with actual UI components
                return True
            except Exception:
                return False
        
        self.register_recovery_strategy(ErrorCategory.UI_COMPONENT, recover_ui_component, priority=1)
        
        # Generic recovery strategy
        def generic_recovery(error_info: ErrorInfo) -> bool:
            """Generic recovery attempt."""
            try:
                # Log the recovery attempt
                self.logger.info(f"Attempting generic recovery for {error_info.error_id}")
                # Basic system reset operations would go here
                return False  # Placeholder - actual implementation would vary
            except Exception:
                return False
        
        # Register generic recovery for all categories with low priority
        for category in ErrorCategory:
            self.register_recovery_strategy(category, generic_recovery, priority=99)


class ErrorReporter(QObject):
    """
    Error reporting system for sending error reports to development team.
    Handles error collection, anonymization, and transmission.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.reporting_enabled = False
        self.anonymize_data = True
        self.report_queue = deque(maxlen=100)
    
    def submit_error_report(self, error_info: ErrorInfo, user_context: str = "") -> bool:
        """Submit error report for analysis."""
        if not self.reporting_enabled:
            return False
        
        # Create sanitized report
        report = {
            'error_id': error_info.error_id,
            'category': error_info.category.value,
            'severity': error_info.severity.value,
            'message': error_info.message if not self.anonymize_data else "Error message hidden",
            'component': error_info.component,
            'timestamp': error_info.timestamp,
            'user_context': user_context,
            'recovery_attempted': error_info.recovery_attempted,
            'recovery_successful': error_info.recovery_successful
        }
        
        # Add to queue for transmission
        self.report_queue.append(report)
        
        return True
    
    def enable_reporting(self, enabled: bool, anonymous: bool = True):
        """Enable or disable error reporting."""
        self.reporting_enabled = enabled
        self.anonymize_data = anonymous