"""
Logging middleware for state management.

This module provides middleware that logs all actions and state changes
for debugging and monitoring purposes.
"""

import logging
import time
import json
from typing import Callable, Any, Optional, Dict
from datetime import datetime

from .base import Middleware
from ..actions import Action, ActionValidator

logger = logging.getLogger(__name__)


class LoggingMiddleware(Middleware):
    """
    Middleware that logs actions and state changes.
    
    Features:
    - Log actions before and after processing
    - Log processing time
    - Log state diffs (optional)
    - Configurable log levels
    """
    
    def __init__(self, 
                 log_level: int = logging.DEBUG,
                 log_state_diff: bool = False,
                 log_payload: bool = True,
                 max_payload_length: int = 200,
                 name: str = None):
        """
        Initialize logging middleware.
        
        Args:
            log_level: Logging level for action logs
            log_state_diff: Whether to log state differences
            log_payload: Whether to log action payloads
            max_payload_length: Maximum payload string length
            name: Optional name for debugging
        """
        super().__init__(name or "LoggingMiddleware")
        self.log_level = log_level
        self.log_state_diff = log_state_diff
        self.log_payload = log_payload
        self.max_payload_length = max_payload_length
        self._store = None
    
    def __call__(self, store: 'Store') -> Callable[[Callable], Callable]:
        """Capture store reference for state diffing."""
        self._store = store
        return super().__call__(store)
    
    def process(self, action: Action, next_dispatch: Callable) -> Any:
        """Log action and process it."""
        # Log action dispatch
        start_time = time.time()
        prev_state = None
        
        # Get previous state if diffing
        if self.log_state_diff and self._store:
            prev_state = self._store.get_state()
        
        # Format action for logging
        action_info = self._format_action(action)
        
        logger.log(
            self.log_level,
            f"Dispatching action: {action_info['type']}",
            extra={
                'action_id': action.id,
                'action_type': action_info['type'],
                'action_payload': action_info.get('payload'),
                'timestamp': action_info['timestamp']
            }
        )
        
        try:
            # Process action
            result = next_dispatch(action)
            
            # Log success
            duration = time.time() - start_time
            logger.log(
                self.log_level,
                f"Action processed: {action_info['type']} ({duration:.3f}s)",
                extra={
                    'action_id': action.id,
                    'duration': duration,
                    'success': True
                }
            )
            
            # Log state diff if enabled
            if self.log_state_diff and self._store and prev_state:
                self._log_state_diff(prev_state, self._store.get_state(), action)
            
            return result
            
        except Exception as e:
            # Log error
            duration = time.time() - start_time
            logger.error(
                f"Action failed: {action_info['type']} ({duration:.3f}s) - {str(e)}",
                extra={
                    'action_id': action.id,
                    'duration': duration,
                    'success': False,
                    'error': str(e)
                }
            )
            raise
    
    def _format_action(self, action: Action) -> Dict[str, Any]:
        """Format action for logging."""
        info = {
            'type': str(action.type),
            'id': action.id,
            'timestamp': datetime.fromtimestamp(action.timestamp).isoformat(),
            'error': action.error
        }
        
        if self.log_payload and action.payload is not None:
            try:
                # Try to serialize payload
                payload_str = json.dumps(action.payload, default=str)
                if len(payload_str) > self.max_payload_length:
                    payload_str = payload_str[:self.max_payload_length] + "..."
                info['payload'] = payload_str
            except:
                info['payload'] = f"<{type(action.payload).__name__}>"
        
        if action.meta:
            info['meta'] = action.meta
        
        return info
    
    def _log_state_diff(self, prev_state: Dict, next_state: Dict, action: Action) -> None:
        """Log differences between states."""
        try:
            # Find changed keys
            all_keys = set(prev_state.keys()) | set(next_state.keys())
            changed_keys = []
            
            for key in all_keys:
                if key not in prev_state:
                    changed_keys.append(f"+{key}")
                elif key not in next_state:
                    changed_keys.append(f"-{key}")
                elif prev_state[key] != next_state[key]:
                    changed_keys.append(f"~{key}")
            
            if changed_keys:
                logger.log(
                    self.log_level,
                    f"State changed: {', '.join(changed_keys)}",
                    extra={
                        'action_id': action.id,
                        'changed_keys': changed_keys
                    }
                )
        except Exception as e:
            logger.debug(f"Could not log state diff: {e}")


class ActionLoggerMiddleware(LoggingMiddleware):
    """Simplified logging middleware that only logs action types."""
    
    def __init__(self, name: str = None):
        """Initialize action logger with minimal logging."""
        super().__init__(
            log_level=logging.INFO,
            log_state_diff=False,
            log_payload=False,
            name=name or "ActionLogger"
        )


def create_logging_middleware(verbose: bool = False) -> LoggingMiddleware:
    """
    Create a logging middleware with sensible defaults.
    
    Args:
        verbose: If True, enables payload and state diff logging
        
    Returns:
        Configured LoggingMiddleware
    """
    return LoggingMiddleware(
        log_level=logging.DEBUG if verbose else logging.INFO,
        log_state_diff=verbose,
        log_payload=verbose,
        max_payload_length=500 if verbose else 200
    )