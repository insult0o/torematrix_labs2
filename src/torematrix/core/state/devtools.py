"""
Development tools integration for state management debugging.
"""

from typing import Dict, Any, List, Optional, Callable
import json
import time
import logging
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class DevToolsOptions:
    """Configuration options for DevTools."""
    name: str = "TORE Matrix State"
    max_actions: int = 50
    latency: int = 0
    max_age: int = 30
    serialize: bool = True
    action_sanitizer: Optional[Callable] = None
    state_sanitizer: Optional[Callable] = None
    action_creator_name: str = "action"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert options to dictionary."""
        return {
            'name': self.name,
            'maxAge': self.max_age,
            'latency': self.latency,
            'serialize': self.serialize,
            'actionCreators': {self.action_creator_name: lambda action: action}
        }


@dataclass
class ActionLogEntry:
    """Entry in the action log."""
    id: str
    action: Any
    state_before: Dict[str, Any]
    state_after: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    duration: float = 0
    error: Optional[str] = None
    
    @property
    def datetime(self) -> datetime:
        """Get timestamp as datetime."""
        return datetime.fromtimestamp(self.timestamp)


class ReduxDevTools:
    """
    Redux DevTools integration for state debugging and time travel.
    
    Features:
    - Action logging and replay
    - State inspection and time travel
    - Performance monitoring
    - Import/export capabilities
    - Custom action sanitization
    """
    
    def __init__(self, options: Optional[DevToolsOptions] = None):
        """
        Initialize Redux DevTools.
        
        Args:
            options: DevTools configuration options
        """
        self.options = options or DevToolsOptions()
        self._action_log: List[ActionLogEntry] = []
        self._state_history: List[Dict[str, Any]] = []
        self._connection = None
        self._enabled = True
        self._current_index = -1
        
        # Try to connect to browser extension
        self._initialize_connection()
    
    def _initialize_connection(self):
        """Initialize connection to Redux DevTools Extension."""
        try:
            # In a real implementation, this would connect to the browser extension
            # For now, we'll simulate the connection
            logger.info("Redux DevTools initialized (simulated)")
            self._connection = "simulated"
        except Exception as e:
            logger.warning(f"Could not connect to Redux DevTools Extension: {e}")
            self._connection = None
    
    def create_middleware(self):
        """
        Create DevTools middleware for the store.
        
        Returns:
            Middleware function
        """
        def middleware(store):
            def next_middleware(next_dispatch):
                def dispatch(action):
                    if not self._enabled:
                        return next_dispatch(action)
                    
                    # Get state before action
                    state_before = store.get_state()
                    
                    # Record start time
                    start_time = time.time()
                    
                    try:
                        # Execute action
                        result = next_dispatch(action)
                        
                        # Get state after action
                        state_after = store.get_state()
                        
                        # Calculate duration
                        duration = time.time() - start_time
                        
                        # Log action
                        self._log_action(action, state_before, state_after, duration)
                        
                        return result
                        
                    except Exception as e:
                        # Log error
                        duration = time.time() - start_time
                        self._log_action(action, state_before, state_before, duration, str(e))
                        raise e
                
                return dispatch
            return next_middleware
        return middleware
    
    def _log_action(self, 
                   action: Any,
                   state_before: Dict[str, Any],
                   state_after: Dict[str, Any],
                   duration: float,
                   error: Optional[str] = None):
        """Log an action with state changes."""
        if not self._enabled:
            return
        
        # Create log entry
        entry = ActionLogEntry(
            id=f"action_{len(self._action_log)}",
            action=self._sanitize_action(action),
            state_before=self._sanitize_state(state_before),
            state_after=self._sanitize_state(state_after),
            duration=duration,
            error=error
        )
        
        # Add to log
        self._action_log.append(entry)
        self._state_history.append(state_after)
        self._current_index = len(self._action_log) - 1
        
        # Maintain max actions limit
        if len(self._action_log) > self.options.max_actions:
            self._action_log.pop(0)
            self._state_history.pop(0)
            self._current_index = len(self._action_log) - 1
        
        # Send to DevTools extension
        self._send_to_devtools(action, state_after)
        
        logger.debug(f"Logged action: {getattr(action, 'type', 'unknown')}")
    
    def _sanitize_action(self, action: Any) -> Any:
        """Sanitize action for logging."""
        if self.options.action_sanitizer:
            try:
                return self.options.action_sanitizer(action)
            except Exception as e:
                logger.warning(f"Action sanitizer failed: {e}")
        
        # Default sanitization
        if hasattr(action, '__dict__'):
            sanitized = {}
            for key, value in action.__dict__.items():
                if not key.startswith('_'):
                    sanitized[key] = self._sanitize_value(value)
            return sanitized
        
        return self._sanitize_value(action)
    
    def _sanitize_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize state for logging."""
        if self.options.state_sanitizer:
            try:
                return self.options.state_sanitizer(state)
            except Exception as e:
                logger.warning(f"State sanitizer failed: {e}")
        
        # Default sanitization
        return self._sanitize_value(state)
    
    def _sanitize_value(self, value: Any) -> Any:
        """Sanitize a value for JSON serialization."""
        if self.options.serialize:
            try:
                # Test JSON serialization
                json.dumps(value)
                return value
            except (TypeError, ValueError):
                # Convert non-serializable values
                if hasattr(value, '__dict__'):
                    return {k: self._sanitize_value(v) for k, v in value.__dict__.items()}
                elif isinstance(value, (list, tuple)):
                    return [self._sanitize_value(item) for item in value]
                elif isinstance(value, dict):
                    return {k: self._sanitize_value(v) for k, v in value.items()}
                else:
                    return str(value)
        
        return value
    
    def _send_to_devtools(self, action: Any, state: Dict[str, Any]):
        """Send action and state to DevTools extension."""
        if not self._connection:
            return
        
        try:
            # In a real implementation, this would send to the browser extension
            # For now, we'll just log it
            action_data = {
                'type': getattr(action, 'type', 'UNKNOWN_ACTION'),
                'payload': getattr(action, 'payload', None),
                'timestamp': time.time()
            }
            
            logger.debug(f"DevTools: {action_data['type']}")
            
        except Exception as e:
            logger.warning(f"Failed to send to DevTools: {e}")
    
    def time_travel(self, store: Any, index: int) -> bool:
        """
        Jump to a specific point in action history.
        
        Args:
            store: Store instance
            index: Index in action history to jump to
            
        Returns:
            True if time travel was successful
        """
        if not self._enabled:
            return False
        
        if not (0 <= index < len(self._state_history)):
            logger.warning(f"Invalid time travel index: {index}")
            return False
        
        try:
            # Get state at index
            target_state = self._state_history[index]
            
            # Apply state to store
            if hasattr(store, '_set_state'):
                store._set_state(target_state)
            else:
                # Create time travel action
                class TimeTravelAction:
                    def __init__(self, state: Dict[str, Any], index: int):
                        self.type = "__TIME_TRAVEL__"
                        self.payload = state
                        self.index = index
                        self.internal = True
                
                action = TimeTravelAction(target_state, index)
                store.dispatch(action)
            
            self._current_index = index
            logger.info(f"Time traveled to index {index}")
            return True
            
        except Exception as e:
            logger.error(f"Time travel failed: {e}")
            return False
    
    def replay_actions(self, store: Any, from_index: int = 0, to_index: Optional[int] = None) -> bool:
        """
        Replay actions from a specific point.
        
        Args:
            store: Store instance
            from_index: Starting index for replay
            to_index: Ending index for replay (end of log if None)
            
        Returns:
            True if replay was successful
        """
        if not self._enabled:
            return False
        
        to_index = to_index or len(self._action_log) - 1
        
        if not (0 <= from_index <= to_index < len(self._action_log)):
            logger.warning(f"Invalid replay range: {from_index}-{to_index}")
            return False
        
        try:
            # Reset to state before from_index
            if from_index > 0:
                initial_state = self._state_history[from_index - 1]
                if hasattr(store, '_set_state'):
                    store._set_state(initial_state)
            
            # Replay actions
            for i in range(from_index, to_index + 1):
                entry = self._action_log[i]
                
                # Temporarily disable logging to avoid duplicates
                self._enabled = False
                try:
                    store.dispatch(entry.action)
                finally:
                    self._enabled = True
            
            logger.info(f"Replayed actions {from_index} to {to_index}")
            return True
            
        except Exception as e:
            logger.error(f"Action replay failed: {e}")
            self._enabled = True  # Re-enable on error
            return False
    
    def export_state(self, format: str = 'json') -> str:
        """
        Export current state and action log.
        
        Args:
            format: Export format ('json', 'csv')
            
        Returns:
            Serialized state and actions
        """
        if format == 'json':
            return json.dumps({
                'actions': [
                    {
                        'id': entry.id,
                        'action': entry.action,
                        'timestamp': entry.timestamp,
                        'duration': entry.duration,
                        'error': entry.error
                    }
                    for entry in self._action_log
                ],
                'states': self._state_history,
                'current_index': self._current_index,
                'exported_at': time.time()
            }, indent=2)
        
        elif format == 'csv':
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow(['id', 'action_type', 'timestamp', 'duration', 'error'])
            
            # Write actions
            for entry in self._action_log:
                writer.writerow([
                    entry.id,
                    getattr(entry.action, 'type', 'unknown'),
                    entry.datetime.isoformat(),
                    entry.duration,
                    entry.error or ''
                ])
            
            return output.getvalue()
        
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def import_state(self, data: str, store: Any) -> bool:
        """
        Import state and action log.
        
        Args:
            data: Serialized state data
            store: Store instance
            
        Returns:
            True if import was successful
        """
        try:
            imported = json.loads(data)
            
            # Clear current log
            self._action_log.clear()
            self._state_history.clear()
            
            # Import actions and states
            for action_data in imported.get('actions', []):
                # Reconstruct action log entry
                entry = ActionLogEntry(
                    id=action_data['id'],
                    action=action_data['action'],
                    state_before={},
                    state_after={},
                    timestamp=action_data['timestamp'],
                    duration=action_data['duration'],
                    error=action_data.get('error')
                )
                self._action_log.append(entry)
            
            # Import state history
            self._state_history = imported.get('states', [])
            self._current_index = imported.get('current_index', -1)
            
            # Apply latest state
            if self._state_history:
                latest_state = self._state_history[-1]
                if hasattr(store, '_set_state'):
                    store._set_state(latest_state)
            
            logger.info("Successfully imported state and action log")
            return True
            
        except Exception as e:
            logger.error(f"State import failed: {e}")
            return False
    
    def get_action_log(self) -> List[ActionLogEntry]:
        """Get the action log."""
        return list(self._action_log)
    
    def get_state_history(self) -> List[Dict[str, Any]]:
        """Get the state history."""
        return list(self._state_history)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        if not self._action_log:
            return {}
        
        durations = [entry.duration for entry in self._action_log if entry.duration > 0]
        
        return {
            'total_actions': len(self._action_log),
            'avg_duration': sum(durations) / len(durations) if durations else 0,
            'max_duration': max(durations) if durations else 0,
            'min_duration': min(durations) if durations else 0,
            'errors': len([entry for entry in self._action_log if entry.error]),
            'current_index': self._current_index,
        }
    
    def clear_log(self):
        """Clear action log and state history."""
        self._action_log.clear()
        self._state_history.clear()
        self._current_index = -1
        logger.info("Cleared DevTools log")
    
    def enable(self):
        """Enable DevTools logging."""
        self._enabled = True
        logger.info("DevTools enabled")
    
    def disable(self):
        """Disable DevTools logging."""
        self._enabled = False
        logger.info("DevTools disabled")
    
    def is_enabled(self) -> bool:
        """Check if DevTools is enabled."""
        return self._enabled
    
    def set_action_sanitizer(self, sanitizer: Callable):
        """Set custom action sanitizer."""
        self.options.action_sanitizer = sanitizer
        logger.debug("Action sanitizer updated")
    
    def set_state_sanitizer(self, sanitizer: Callable):
        """Set custom state sanitizer."""
        self.options.state_sanitizer = sanitizer
        logger.debug("State sanitizer updated")