"""
Error handling middleware for graceful error recovery.
"""

from typing import Dict, Any, Callable, Optional, List
import logging
import traceback
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ErrorInfo:
    """Information about an error that occurred."""
    action_type: str
    error: Exception
    timestamp: datetime = field(default_factory=datetime.now)
    stack_trace: str = field(default="")
    recovered: bool = False
    
    def __post_init__(self):
        if not self.stack_trace:
            self.stack_trace = traceback.format_exc()


class ErrorHandlerMiddleware:
    """
    Middleware for handling errors in action processing.
    
    Provides error recovery, logging, and metrics collection.
    """
    
    def __init__(self, 
                 recovery_strategies: Optional[Dict[str, Callable]] = None,
                 max_errors: int = 100):
        """
        Initialize error handler.
        
        Args:
            recovery_strategies: Dict mapping error types to recovery functions
            max_errors: Maximum number of errors to keep in history
        """
        self.recovery_strategies = recovery_strategies or {}
        self.max_errors = max_errors
        self.error_history: List[ErrorInfo] = []
        self.error_counts: Dict[str, int] = {}
    
    def __call__(self, store):
        """Create error handling middleware."""
        def middleware(next_dispatch):
            def dispatch(action):
                try:
                    return next_dispatch(action)
                    
                except Exception as error:
                    error_info = ErrorInfo(
                        action_type=action.type,
                        error=error
                    )
                    
                    # Log the error
                    logger.error(
                        f"Error processing action {action.type}: {error}",
                        exc_info=True
                    )
                    
                    # Update metrics
                    self._update_error_metrics(error_info)
                    
                    # Try recovery
                    recovery_result = self._attempt_recovery(store, action, error)
                    if recovery_result is not None:
                        error_info.recovered = True
                        logger.info(f"Recovered from error in {action.type}")
                        return recovery_result
                    
                    # Store error info
                    self._store_error(error_info)
                    
                    # Re-raise if no recovery
                    raise error
            
            return dispatch
        return middleware
    
    def _update_error_metrics(self, error_info: ErrorInfo):
        """Update error counting metrics."""
        error_type = type(error_info.error).__name__
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        self.error_counts[error_info.action_type] = self.error_counts.get(error_info.action_type, 0) + 1
    
    def _attempt_recovery(self, store, action, error) -> Any:
        """Attempt to recover from the error."""
        error_type = type(error).__name__
        action_type = action.type
        
        # Try error type specific recovery
        if error_type in self.recovery_strategies:
            try:
                return self.recovery_strategies[error_type](store, action, error)
            except Exception as recovery_error:
                logger.error(f"Recovery strategy failed: {recovery_error}")
        
        # Try action type specific recovery  
        if action_type in self.recovery_strategies:
            try:
                return self.recovery_strategies[action_type](store, action, error)
            except Exception as recovery_error:
                logger.error(f"Action recovery strategy failed: {recovery_error}")
        
        # Try general recovery
        if 'default' in self.recovery_strategies:
            try:
                return self.recovery_strategies['default'](store, action, error)
            except Exception as recovery_error:
                logger.error(f"Default recovery strategy failed: {recovery_error}")
        
        return None
    
    def _store_error(self, error_info: ErrorInfo):
        """Store error information for analysis."""
        self.error_history.append(error_info)
        
        # Limit history size
        if len(self.error_history) > self.max_errors:
            self.error_history.pop(0)
    
    def get_error_metrics(self) -> Dict[str, Any]:
        """Get error metrics and statistics."""
        total_errors = len(self.error_history)
        recovered_errors = sum(1 for e in self.error_history if e.recovered)
        
        return {
            'total_errors': total_errors,
            'recovered_errors': recovered_errors,
            'recovery_rate': recovered_errors / total_errors if total_errors > 0 else 0,
            'error_counts': dict(self.error_counts),
            'recent_errors': [
                {
                    'action_type': e.action_type,
                    'error_type': type(e.error).__name__,
                    'timestamp': e.timestamp.isoformat(),
                    'recovered': e.recovered
                }
                for e in self.error_history[-10:]  # Last 10 errors
            ]
        }
    
    def clear_history(self):
        """Clear error history."""
        self.error_history.clear()
        self.error_counts.clear()
    
    def add_recovery_strategy(self, key: str, strategy: Callable):
        """Add a recovery strategy."""
        self.recovery_strategies[key] = strategy


# Common recovery strategies
def retry_recovery_strategy(max_retries: int = 3):
    """Create a retry recovery strategy."""
    retry_counts = {}
    
    def recovery(store, action, error):
        action_id = id(action)
        retries = retry_counts.get(action_id, 0)
        
        if retries < max_retries:
            retry_counts[action_id] = retries + 1
            logger.info(f"Retrying action {action.type} (attempt {retries + 1})")
            
            # Retry the action
            return store.dispatch(action)
        else:
            # Max retries exceeded
            if action_id in retry_counts:
                del retry_counts[action_id]
            raise error
    
    return recovery


def fallback_recovery_strategy(fallback_value):
    """Create a fallback recovery strategy."""
    def recovery(store, action, error):
        logger.info(f"Using fallback value for action {action.type}")
        return fallback_value
    
    return recovery


def ignore_recovery_strategy():
    """Recovery strategy that ignores the error and returns None."""
    def recovery(store, action, error):
        logger.info(f"Ignoring error for action {action.type}")
        return None
    
    return recovery