"""
Configuration change events and notification system.

This module provides event-driven configuration change notifications
with integration to the event bus system.
"""

from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

from ..events.base import BaseEvent, EventPriority
from .types import ConfigDict, ConfigSource
from .watcher import ConfigurationChange, ChangeType


class ConfigEventType(Enum):
    """Configuration event types."""
    CONFIG_LOADED = "config_loaded"
    CONFIG_CHANGED = "config_changed"
    CONFIG_RELOADED = "config_reloaded"
    CONFIG_ERROR = "config_error"
    CONFIG_VALIDATED = "config_validated"
    CONFIG_FROZEN = "config_frozen"
    CONFIG_UNFROZEN = "config_unfrozen"
    CONFIG_RESET = "config_reset"
    CONFIG_MERGED = "config_merged"
    CONFIG_BACKUP_CREATED = "config_backup_created"
    CONFIG_ROLLBACK = "config_rollback"
    HOT_RELOAD_SUCCESS = "hot_reload_success"
    HOT_RELOAD_FAILURE = "hot_reload_failure"


@dataclass
class ConfigurationChangeEvent(BaseEvent):
    """Event for configuration changes."""
    
    event_type: ConfigEventType
    config_key: Optional[str] = None
    old_value: Any = None
    new_value: Any = None
    source: Optional[ConfigSource] = None
    file_path: Optional[Path] = None
    validation_errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize base event properties."""
        if not hasattr(self, 'id'):
            super().__init__(
                event_type=f"config.{self.event_type.value}",
                priority=self._get_event_priority(),
                data={
                    "config_key": self.config_key,
                    "old_value": self.old_value,
                    "new_value": self.new_value,
                    "source": self.source.name if self.source else None,
                    "file_path": str(self.file_path) if self.file_path else None,
                    "validation_errors": self.validation_errors,
                    "metadata": self.metadata
                }
            )
    
    def _get_event_priority(self) -> EventPriority:
        """Determine event priority based on type."""
        high_priority_events = {
            ConfigEventType.CONFIG_ERROR,
            ConfigEventType.HOT_RELOAD_FAILURE,
            ConfigEventType.CONFIG_RESET
        }
        
        normal_priority_events = {
            ConfigEventType.CONFIG_CHANGED,
            ConfigEventType.CONFIG_RELOADED,
            ConfigEventType.HOT_RELOAD_SUCCESS,
            ConfigEventType.CONFIG_ROLLBACK
        }
        
        if self.event_type in high_priority_events:
            return EventPriority.HIGH
        elif self.event_type in normal_priority_events:
            return EventPriority.NORMAL
        else:
            return EventPriority.LOW
    
    @classmethod
    def config_loaded(cls, 
                     file_path: Path, 
                     config: ConfigDict,
                     source: ConfigSource) -> 'ConfigurationChangeEvent':
        """Create config loaded event."""
        return cls(
            event_type=ConfigEventType.CONFIG_LOADED,
            new_value=config,
            source=source,
            file_path=file_path,
            metadata={"config_size": len(str(config))}
        )
    
    @classmethod
    def config_changed(cls,
                      key: str,
                      old_value: Any,
                      new_value: Any,
                      source: ConfigSource) -> 'ConfigurationChangeEvent':
        """Create config changed event."""
        return cls(
            event_type=ConfigEventType.CONFIG_CHANGED,
            config_key=key,
            old_value=old_value,
            new_value=new_value,
            source=source
        )
    
    @classmethod
    def config_reloaded(cls,
                       file_path: Path,
                       config: ConfigDict,
                       reload_time_ms: float) -> 'ConfigurationChangeEvent':
        """Create config reloaded event."""
        return cls(
            event_type=ConfigEventType.CONFIG_RELOADED,
            new_value=config,
            file_path=file_path,
            metadata={
                "reload_time_ms": reload_time_ms,
                "config_size": len(str(config))
            }
        )
    
    @classmethod
    def config_error(cls,
                    error: Exception,
                    file_path: Optional[Path] = None,
                    config_key: Optional[str] = None) -> 'ConfigurationChangeEvent':
        """Create config error event."""
        return cls(
            event_type=ConfigEventType.CONFIG_ERROR,
            config_key=config_key,
            file_path=file_path,
            validation_errors=[str(error)],
            metadata={
                "error_type": type(error).__name__,
                "error_message": str(error)
            }
        )
    
    @classmethod
    def config_validated(cls,
                        validation_errors: List[str],
                        config_size: int) -> 'ConfigurationChangeEvent':
        """Create config validation event."""
        return cls(
            event_type=ConfigEventType.CONFIG_VALIDATED,
            validation_errors=validation_errors,
            metadata={
                "config_size": config_size,
                "is_valid": len(validation_errors) == 0
            }
        )
    
    @classmethod
    def hot_reload_success(cls,
                          file_path: Path,
                          config: ConfigDict,
                          reload_time_ms: float) -> 'ConfigurationChangeEvent':
        """Create hot reload success event."""
        return cls(
            event_type=ConfigEventType.HOT_RELOAD_SUCCESS,
            new_value=config,
            file_path=file_path,
            metadata={
                "reload_time_ms": reload_time_ms,
                "config_size": len(str(config)),
                "trigger": "file_change"
            }
        )
    
    @classmethod
    def hot_reload_failure(cls,
                          file_path: Path,
                          error: Exception) -> 'ConfigurationChangeEvent':
        """Create hot reload failure event."""
        return cls(
            event_type=ConfigEventType.HOT_RELOAD_FAILURE,
            file_path=file_path,
            validation_errors=[str(error)],
            metadata={
                "error_type": type(error).__name__,
                "error_message": str(error),
                "trigger": "file_change"
            }
        )
    
    @classmethod
    def config_rollback(cls,
                       file_path: Path,
                       restored_config: ConfigDict,
                       reason: str) -> 'ConfigurationChangeEvent':
        """Create config rollback event."""
        return cls(
            event_type=ConfigEventType.CONFIG_ROLLBACK,
            new_value=restored_config,
            file_path=file_path,
            metadata={
                "reason": reason,
                "config_size": len(str(restored_config))
            }
        )


@dataclass
class FileSystemChangeEvent(BaseEvent):
    """Event for file system changes affecting configuration."""
    
    file_change: ConfigurationChange
    
    def __post_init__(self):
        """Initialize base event properties."""
        if not hasattr(self, 'id'):
            super().__init__(
                event_type=f"config.file.{self.file_change.change_type.value}",
                priority=self._get_file_priority(),
                data=self.file_change.to_dict()
            )
    
    def _get_file_priority(self) -> EventPriority:
        """Determine priority based on change type."""
        if self.file_change.change_type == ChangeType.DELETED:
            return EventPriority.HIGH
        elif self.file_change.change_type in [ChangeType.MODIFIED, ChangeType.CREATED]:
            return EventPriority.NORMAL
        else:
            return EventPriority.LOW


class ConfigurationEventEmitter:
    """
    Configuration event emitter that integrates with the event bus.
    
    This class provides a clean interface for emitting configuration-related
    events and handles event formatting and priority assignment.
    """
    
    def __init__(self, event_bus=None):
        """
        Initialize event emitter.
        
        Args:
            event_bus: Event bus instance for publishing events
        """
        self.event_bus = event_bus
        self._event_history: List[ConfigurationChangeEvent] = []
        self._max_history = 1000
    
    def emit_config_loaded(self,
                          file_path: Path,
                          config: ConfigDict,
                          source: ConfigSource) -> None:
        """Emit configuration loaded event."""
        event = ConfigurationChangeEvent.config_loaded(file_path, config, source)
        self._emit_event(event)
    
    def emit_config_changed(self,
                           key: str,
                           old_value: Any,
                           new_value: Any,
                           source: ConfigSource) -> None:
        """Emit configuration changed event."""
        event = ConfigurationChangeEvent.config_changed(key, old_value, new_value, source)
        self._emit_event(event)
    
    def emit_config_reloaded(self,
                            file_path: Path,
                            config: ConfigDict,
                            reload_time_ms: float) -> None:
        """Emit configuration reloaded event."""
        event = ConfigurationChangeEvent.config_reloaded(file_path, config, reload_time_ms)
        self._emit_event(event)
    
    def emit_config_error(self,
                         error: Exception,
                         file_path: Optional[Path] = None,
                         config_key: Optional[str] = None) -> None:
        """Emit configuration error event."""
        event = ConfigurationChangeEvent.config_error(error, file_path, config_key)
        self._emit_event(event)
    
    def emit_config_validated(self,
                             validation_errors: List[str],
                             config_size: int) -> None:
        """Emit configuration validation event."""
        event = ConfigurationChangeEvent.config_validated(validation_errors, config_size)
        self._emit_event(event)
    
    def emit_hot_reload_success(self,
                               file_path: Path,
                               config: ConfigDict,
                               reload_time_ms: float) -> None:
        """Emit hot reload success event."""
        event = ConfigurationChangeEvent.hot_reload_success(file_path, config, reload_time_ms)
        self._emit_event(event)
    
    def emit_hot_reload_failure(self,
                               file_path: Path,
                               error: Exception) -> None:
        """Emit hot reload failure event."""
        event = ConfigurationChangeEvent.hot_reload_failure(file_path, error)
        self._emit_event(event)
    
    def emit_config_rollback(self,
                            file_path: Path,
                            restored_config: ConfigDict,
                            reason: str) -> None:
        """Emit configuration rollback event."""
        event = ConfigurationChangeEvent.config_rollback(file_path, restored_config, reason)
        self._emit_event(event)
    
    def emit_file_change(self, file_change: ConfigurationChange) -> None:
        """Emit file system change event."""
        event = FileSystemChangeEvent(file_change=file_change)
        self._emit_event(event)
    
    def emit_config_frozen(self) -> None:
        """Emit configuration frozen event."""
        event = ConfigurationChangeEvent(
            event_type=ConfigEventType.CONFIG_FROZEN,
            metadata={"frozen_at": datetime.now().isoformat()}
        )
        self._emit_event(event)
    
    def emit_config_unfrozen(self) -> None:
        """Emit configuration unfrozen event."""
        event = ConfigurationChangeEvent(
            event_type=ConfigEventType.CONFIG_UNFROZEN,
            metadata={"unfrozen_at": datetime.now().isoformat()}
        )
        self._emit_event(event)
    
    def emit_config_reset(self) -> None:
        """Emit configuration reset event."""
        event = ConfigurationChangeEvent(
            event_type=ConfigEventType.CONFIG_RESET,
            metadata={"reset_at": datetime.now().isoformat()}
        )
        self._emit_event(event)
    
    def emit_config_merged(self,
                          source: ConfigSource,
                          merged_keys: List[str]) -> None:
        """Emit configuration merged event."""
        event = ConfigurationChangeEvent(
            event_type=ConfigEventType.CONFIG_MERGED,
            source=source,
            metadata={
                "merged_keys": merged_keys,
                "merged_count": len(merged_keys),
                "merged_at": datetime.now().isoformat()
            }
        )
        self._emit_event(event)
    
    def emit_backup_created(self,
                           file_path: Path,
                           backup_count: int) -> None:
        """Emit configuration backup created event."""
        event = ConfigurationChangeEvent(
            event_type=ConfigEventType.CONFIG_BACKUP_CREATED,
            file_path=file_path,
            metadata={
                "backup_count": backup_count,
                "created_at": datetime.now().isoformat()
            }
        )
        self._emit_event(event)
    
    def get_event_history(self, 
                         event_type: Optional[ConfigEventType] = None,
                         limit: Optional[int] = None) -> List[ConfigurationChangeEvent]:
        """
        Get event history.
        
        Args:
            event_type: Filter by event type
            limit: Maximum number of events to return
            
        Returns:
            List of configuration events
        """
        events = self._event_history
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        if limit:
            events = events[-limit:]
        
        return events
    
    def get_event_statistics(self) -> Dict[str, Any]:
        """Get event statistics."""
        if not self._event_history:
            return {"total_events": 0}
        
        # Count events by type
        event_counts = {}
        error_count = 0
        
        for event in self._event_history:
            event_type = event.event_type.value
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
            
            if event.event_type in [ConfigEventType.CONFIG_ERROR, ConfigEventType.HOT_RELOAD_FAILURE]:
                error_count += 1
        
        return {
            "total_events": len(self._event_history),
            "error_count": error_count,
            "error_rate": error_count / len(self._event_history),
            "event_counts": event_counts,
            "most_recent": self._event_history[-1].timestamp.isoformat(),
            "oldest": self._event_history[0].timestamp.isoformat()
        }
    
    def clear_history(self) -> None:
        """Clear event history."""
        self._event_history.clear()
    
    def _emit_event(self, event: Union[ConfigurationChangeEvent, FileSystemChangeEvent]) -> None:
        """Emit event to bus and store in history."""
        # Store in history (only ConfigurationChangeEvent)
        if isinstance(event, ConfigurationChangeEvent):
            self._event_history.append(event)
            
            # Trim history if needed
            if len(self._event_history) > self._max_history:
                self._event_history = self._event_history[-self._max_history:]
        
        # Emit to event bus if available
        if self.event_bus:
            try:
                self.event_bus.publish(event)
            except Exception as e:
                # Fallback: print error but don't fail
                print(f"Failed to publish configuration event: {e}")


class ConfigurationSubscriber:
    """
    Configuration event subscriber with filtering and callback management.
    
    This class provides a convenient way to subscribe to specific configuration
    events with filtering capabilities.
    """
    
    def __init__(self, event_bus=None):
        """
        Initialize subscriber.
        
        Args:
            event_bus: Event bus instance for subscribing to events
        """
        self.event_bus = event_bus
        self._subscriptions: Dict[str, List[callable]] = {}
        self._active = True
    
    def subscribe_to_config_changes(self,
                                   callback: Callable[[ConfigurationChangeEvent], None],
                                   config_key: Optional[str] = None,
                                   event_types: Optional[List[ConfigEventType]] = None) -> str:
        """
        Subscribe to configuration change events.
        
        Args:
            callback: Callback function
            config_key: Filter by specific config key (optional)
            event_types: Filter by event types (optional)
            
        Returns:
            Subscription ID
        """
        def filtered_callback(event: ConfigurationChangeEvent):
            if not self._active:
                return
            
            # Filter by config key
            if config_key and event.config_key != config_key:
                return
            
            # Filter by event types
            if event_types and event.event_type not in event_types:
                return
            
            try:
                callback(event)
            except Exception as e:
                print(f"Error in configuration change callback: {e}")
        
        # Generate subscription ID
        sub_id = f"config_changes_{id(callback)}"
        
        if self.event_bus:
            # Subscribe to all config events
            config_event_pattern = "config.*"
            self.event_bus.subscribe(config_event_pattern, filtered_callback)
        
        # Store subscription for management
        if sub_id not in self._subscriptions:
            self._subscriptions[sub_id] = []
        self._subscriptions[sub_id].append(filtered_callback)
        
        return sub_id
    
    def subscribe_to_file_changes(self,
                                 callback: Callable[[FileSystemChangeEvent], None],
                                 file_path: Optional[Path] = None) -> str:
        """
        Subscribe to file system change events.
        
        Args:
            callback: Callback function
            file_path: Filter by specific file path (optional)
            
        Returns:
            Subscription ID
        """
        def filtered_callback(event: FileSystemChangeEvent):
            if not self._active:
                return
            
            # Filter by file path
            if file_path and event.file_change.path != file_path:
                return
            
            try:
                callback(event)
            except Exception as e:
                print(f"Error in file change callback: {e}")
        
        # Generate subscription ID
        sub_id = f"file_changes_{id(callback)}"
        
        if self.event_bus:
            # Subscribe to file change events
            file_event_pattern = "config.file.*"
            self.event_bus.subscribe(file_event_pattern, filtered_callback)
        
        # Store subscription for management
        if sub_id not in self._subscriptions:
            self._subscriptions[sub_id] = []
        self._subscriptions[sub_id].append(filtered_callback)
        
        return sub_id
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """
        Unsubscribe from events.
        
        Args:
            subscription_id: Subscription ID to remove
            
        Returns:
            True if subscription was removed
        """
        if subscription_id in self._subscriptions:
            callbacks = self._subscriptions[subscription_id]
            
            # Unsubscribe from event bus
            if self.event_bus:
                for callback in callbacks:
                    try:
                        # Note: Actual unsubscribe depends on event bus implementation
                        pass
                    except Exception as e:
                        print(f"Error unsubscribing from event bus: {e}")
            
            del self._subscriptions[subscription_id]
            return True
        
        return False
    
    def pause(self) -> None:
        """Pause all subscriptions."""
        self._active = False
    
    def resume(self) -> None:
        """Resume all subscriptions."""
        self._active = True
    
    def get_subscription_count(self) -> int:
        """Get number of active subscriptions."""
        return len(self._subscriptions)