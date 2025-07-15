"""
Configuration system integration with event bus and audit logging.

This module provides integration components that connect the configuration
system with the broader application event bus and audit logging systems.
"""

import json
import time
from typing import Dict, Any, Optional, List, Set, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum

from ..events import Event as BaseEvent, EventPriority
from ..audit.logger import AuditLogger, AuditLevel, AuditContext
from .events import ConfigurationChangeEvent, ConfigEventType, FileSystemChangeEvent
from .runtime import RuntimeConfigurationManager
from .api import ConfigurationAPI
from .types import ConfigSource


class ConfigAuditAction(Enum):
    """Configuration audit actions."""
    CONFIG_READ = "config_read"
    CONFIG_WRITE = "config_write"
    CONFIG_DELETE = "config_delete"
    CONFIG_RELOAD = "config_reload"
    CONFIG_ROLLBACK = "config_rollback"
    CONFIG_VALIDATION = "config_validation"
    CONFIG_FREEZE = "config_freeze"
    CONFIG_UNFREEZE = "config_unfreeze"
    CONFIG_RESET = "config_reset"
    CONFIG_IMPORT = "config_import"
    CONFIG_EXPORT = "config_export"
    FILE_WATCH_START = "file_watch_start"
    FILE_WATCH_STOP = "file_watch_stop"
    HOT_RELOAD_SUCCESS = "hot_reload_success"
    HOT_RELOAD_FAILURE = "hot_reload_failure"


@dataclass
class ConfigAuditEntry:
    """Configuration audit log entry."""
    action: ConfigAuditAction
    config_path: Optional[str] = None
    old_value: Any = None
    new_value: Any = None
    source: Optional[ConfigSource] = None
    file_path: Optional[Path] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_audit_record(self) -> Dict[str, Any]:
        """Convert to audit record format."""
        return {
            "action": self.action.value,
            "config_path": self.config_path,
            "old_value": self._sanitize_value(self.old_value),
            "new_value": self._sanitize_value(self.new_value),
            "source": self.source.name if self.source else None,
            "file_path": str(self.file_path) if self.file_path else None,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }
    
    def _sanitize_value(self, value: Any) -> Any:
        """Sanitize sensitive values for audit logging."""
        if value is None:
            return None
        
        # Redact sensitive configuration values
        sensitive_patterns = {
            "password", "secret", "key", "token", "credential", 
            "auth", "private", "cert", "ssl"
        }
        
        if isinstance(value, str):
            value_lower = value.lower()
            if any(pattern in value_lower for pattern in sensitive_patterns):
                return "[REDACTED]"
        
        elif isinstance(value, dict):
            sanitized = {}
            for k, v in value.items():
                key_lower = str(k).lower()
                if any(pattern in key_lower for pattern in sensitive_patterns):
                    sanitized[k] = "[REDACTED]"
                else:
                    sanitized[k] = self._sanitize_value(v)
            return sanitized
        
        elif isinstance(value, (list, tuple)):
            return [self._sanitize_value(item) for item in value]
        
        return value


class ConfigurationAuditLogger:
    """
    Configuration-specific audit logger with enhanced capabilities.
    
    Features:
    - Automatic sensitive data redaction
    - Configuration change tracking
    - Performance metrics
    - Compliance reporting
    """
    
    def __init__(self, 
                 audit_logger: Optional[AuditLogger] = None,
                 enable_performance_tracking: bool = True,
                 retention_days: int = 365):
        """
        Initialize configuration audit logger.
        
        Args:
            audit_logger: Base audit logger instance
            enable_performance_tracking: Track configuration performance metrics
            retention_days: Number of days to retain audit logs
        """
        self.audit_logger = audit_logger or AuditLogger()
        self.enable_performance_tracking = enable_performance_tracking
        self.retention_days = retention_days
        
        # Performance tracking
        self._operation_timings: Dict[str, List[float]] = {}
        self._operation_counts: Dict[str, int] = {}
        self._error_counts: Dict[str, int] = {}
        
        # Context tracking
        self._current_user: Optional[str] = None
        self._current_session: Optional[str] = None
    
    def set_user_context(self, user_id: str, session_id: Optional[str] = None) -> None:
        """Set current user context for audit logging."""
        self._current_user = user_id
        self._current_session = session_id
    
    def clear_user_context(self) -> None:
        """Clear current user context."""
        self._current_user = None
        self._current_session = None
    
    def log_config_read(self, config_path: str, value: Any, source: Optional[ConfigSource] = None) -> None:
        """Log configuration read operation."""
        entry = ConfigAuditEntry(
            action=ConfigAuditAction.CONFIG_READ,
            config_path=config_path,
            new_value=value,
            source=source,
            user_id=self._current_user,
            session_id=self._current_session
        )
        
        self._log_audit_entry(entry, AuditLevel.INFO)
    
    def log_config_write(self, 
                        config_path: str, 
                        old_value: Any, 
                        new_value: Any,
                        source: ConfigSource) -> None:
        """Log configuration write operation."""
        entry = ConfigAuditEntry(
            action=ConfigAuditAction.CONFIG_WRITE,
            config_path=config_path,
            old_value=old_value,
            new_value=new_value,
            source=source,
            user_id=self._current_user,
            session_id=self._current_session
        )
        
        self._log_audit_entry(entry, AuditLevel.INFO)
    
    def log_config_reload(self, 
                         file_path: Path, 
                         success: bool, 
                         duration_ms: float,
                         error: Optional[str] = None) -> None:
        """Log configuration reload operation."""
        action = ConfigAuditAction.HOT_RELOAD_SUCCESS if success else ConfigAuditAction.HOT_RELOAD_FAILURE
        level = AuditLevel.INFO if success else AuditLevel.ERROR
        
        entry = ConfigAuditEntry(
            action=action,
            file_path=file_path,
            user_id=self._current_user,
            session_id=self._current_session,
            metadata={
                "duration_ms": duration_ms,
                "error": error,
                "success": success
            }
        )
        
        self._log_audit_entry(entry, level)
        
        # Track performance
        if self.enable_performance_tracking:
            self._track_operation_timing("reload", duration_ms / 1000)
    
    def log_config_validation(self, 
                            validation_errors: List[str], 
                            config_size: int) -> None:
        """Log configuration validation."""
        is_valid = len(validation_errors) == 0
        level = AuditLevel.INFO if is_valid else AuditLevel.WARNING
        
        entry = ConfigAuditEntry(
            action=ConfigAuditAction.CONFIG_VALIDATION,
            user_id=self._current_user,
            session_id=self._current_session,
            metadata={
                "is_valid": is_valid,
                "error_count": len(validation_errors),
                "errors": validation_errors[:10],  # Limit error list size
                "config_size": config_size
            }
        )
        
        self._log_audit_entry(entry, level)
    
    def log_file_watch_start(self, file_path: Path) -> None:
        """Log file watching start."""
        entry = ConfigAuditEntry(
            action=ConfigAuditAction.FILE_WATCH_START,
            file_path=file_path,
            user_id=self._current_user,
            session_id=self._current_session
        )
        
        self._log_audit_entry(entry, AuditLevel.INFO)
    
    def log_file_watch_stop(self, file_path: Path) -> None:
        """Log file watching stop."""
        entry = ConfigAuditEntry(
            action=ConfigAuditAction.FILE_WATCH_STOP,
            file_path=file_path,
            user_id=self._current_user,
            session_id=self._current_session
        )
        
        self._log_audit_entry(entry, AuditLevel.INFO)
    
    def log_config_rollback(self, file_path: Path, reason: str) -> None:
        """Log configuration rollback."""
        entry = ConfigAuditEntry(
            action=ConfigAuditAction.CONFIG_ROLLBACK,
            file_path=file_path,
            user_id=self._current_user,
            session_id=self._current_session,
            metadata={"reason": reason}
        )
        
        self._log_audit_entry(entry, AuditLevel.WARNING)
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate performance report from audit data."""
        if not self.enable_performance_tracking:
            return {"performance_tracking": False}
        
        report = {"performance_tracking": True, "operations": {}}
        
        for operation, timings in self._operation_timings.items():
            if timings:
                avg_time = sum(timings) / len(timings)
                max_time = max(timings)
                min_time = min(timings)
                
                report["operations"][operation] = {
                    "count": len(timings),
                    "avg_time_ms": avg_time * 1000,
                    "max_time_ms": max_time * 1000,
                    "min_time_ms": min_time * 1000,
                    "total_time_ms": sum(timings) * 1000
                }
        
        # Add error statistics
        report["errors"] = dict(self._error_counts)
        report["total_operations"] = sum(self._operation_counts.values())
        
        return report
    
    def get_compliance_report(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate compliance report for a date range."""
        # This would query the audit logger for entries in the date range
        # For now, return a basic structure
        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "summary": {
                "total_operations": sum(self._operation_counts.values()),
                "unique_users": 1 if self._current_user else 0,
                "config_changes": self._operation_counts.get("write", 0),
                "failed_operations": sum(self._error_counts.values())
            },
            "compliance_status": "COMPLIANT"  # Would be calculated based on policies
        }
    
    def _log_audit_entry(self, entry: ConfigAuditEntry, level: AuditLevel) -> None:
        """Log audit entry to the audit logger."""
        if self.audit_logger:
            context = AuditContext(
                component="configuration",
                operation=entry.action.value,
                user_id=entry.user_id,
                session_id=entry.session_id
            )
            
            self.audit_logger.log(
                level=level,
                message=f"Configuration {entry.action.value}",
                context=context,
                data=entry.to_audit_record()
            )
        
        # Update operation counts
        self._operation_counts[entry.action.value] = self._operation_counts.get(entry.action.value, 0) + 1
    
    def _track_operation_timing(self, operation: str, duration_seconds: float) -> None:
        """Track operation timing for performance analysis."""
        if operation not in self._operation_timings:
            self._operation_timings[operation] = []
        
        self._operation_timings[operation].append(duration_seconds)
        
        # Keep only recent timings to avoid memory growth
        max_timings = 1000
        if len(self._operation_timings[operation]) > max_timings:
            self._operation_timings[operation] = self._operation_timings[operation][-max_timings:]


class EventBusIntegration:
    """
    Integration component for configuration system and event bus.
    
    Features:
    - Event forwarding and transformation
    - Event filtering and routing
    - Performance monitoring
    - Error handling and recovery
    """
    
    def __init__(self, event_bus, audit_logger: Optional[ConfigurationAuditLogger] = None):
        """
        Initialize event bus integration.
        
        Args:
            event_bus: Application event bus instance
            audit_logger: Configuration audit logger
        """
        self.event_bus = event_bus
        self.audit_logger = audit_logger
        
        # Event filtering and routing
        self._event_filters: List[Callable[[BaseEvent], bool]] = []
        self._event_transformers: List[Callable[[BaseEvent], BaseEvent]] = []
        self._error_handlers: List[Callable[[Exception, BaseEvent], None]] = []
        
        # Performance tracking
        self._events_published = 0
        self._events_failed = 0
        self._last_event_time: Optional[datetime] = None
        
        # Setup default event handling
        self._setup_default_handlers()
    
    def add_event_filter(self, filter_func: Callable[[BaseEvent], bool]) -> None:
        """Add event filter function."""
        self._event_filters.append(filter_func)
    
    def add_event_transformer(self, transformer_func: Callable[[BaseEvent], BaseEvent]) -> None:
        """Add event transformer function."""
        self._event_transformers.append(transformer_func)
    
    def add_error_handler(self, handler_func: Callable[[Exception, BaseEvent], None]) -> None:
        """Add error handler for event processing failures."""
        self._error_handlers.append(handler_func)
    
    def publish_config_event(self, event: BaseEvent) -> bool:
        """
        Publish configuration event to the event bus.
        
        Args:
            event: Configuration event to publish
            
        Returns:
            True if event was published successfully
        """
        try:
            # Apply filters
            for filter_func in self._event_filters:
                if not filter_func(event):
                    return False  # Event filtered out
            
            # Apply transformers
            transformed_event = event
            for transformer_func in self._event_transformers:
                transformed_event = transformer_func(transformed_event)
            
            # Publish to event bus
            self.event_bus.publish(transformed_event)
            
            # Update statistics
            self._events_published += 1
            self._last_event_time = datetime.now()
            
            # Audit log the event publication
            if self.audit_logger and isinstance(event, ConfigurationChangeEvent):
                self._audit_event_publication(event)
            
            return True
            
        except Exception as e:
            self._events_failed += 1
            
            # Handle error
            for handler in self._error_handlers:
                try:
                    handler(e, event)
                except Exception:
                    pass  # Ignore handler errors
            
            # Log error if audit logger is available
            if self.audit_logger:
                self.audit_logger._log_audit_entry(
                    ConfigAuditEntry(
                        action=ConfigAuditAction.CONFIG_WRITE,  # Generic action for error
                        metadata={"error": str(e), "event_type": event.event_type}
                    ),
                    AuditLevel.ERROR
                )
            
            return False
    
    def get_integration_stats(self) -> Dict[str, Any]:
        """Get event bus integration statistics."""
        return {
            "events_published": self._events_published,
            "events_failed": self._events_failed,
            "success_rate": (
                self._events_published / (self._events_published + self._events_failed)
                if (self._events_published + self._events_failed) > 0 else 1.0
            ),
            "last_event_time": self._last_event_time.isoformat() if self._last_event_time else None,
            "active_filters": len(self._event_filters),
            "active_transformers": len(self._event_transformers),
            "active_error_handlers": len(self._error_handlers)
        }
    
    def _setup_default_handlers(self) -> None:
        """Setup default event handling."""
        # Default filter: Only publish significant events
        def significant_events_filter(event: BaseEvent) -> bool:
            if isinstance(event, ConfigurationChangeEvent):
                # Filter out read-only events in production
                return event.event_type not in [ConfigEventType.CONFIG_LOADED]
            return True
        
        self.add_event_filter(significant_events_filter)
        
        # Default transformer: Add integration metadata
        def add_integration_metadata(event: BaseEvent) -> BaseEvent:
            if hasattr(event, 'data') and isinstance(event.data, dict):
                event.data["integration"] = {
                    "published_at": datetime.now().isoformat(),
                    "source": "config_integration"
                }
            return event
        
        self.add_event_transformer(add_integration_metadata)
        
        # Default error handler: Log to console
        def console_error_handler(error: Exception, event: BaseEvent) -> None:
            print(f"Failed to publish config event {event.event_type}: {error}")
        
        self.add_error_handler(console_error_handler)
    
    def _audit_event_publication(self, event: ConfigurationChangeEvent) -> None:
        """Audit the publication of a configuration event."""
        if event.event_type == ConfigEventType.CONFIG_CHANGED:
            self.audit_logger.log_config_write(
                event.config_key or "unknown",
                event.old_value,
                event.new_value,
                event.source or ConfigSource.RUNTIME
            )
        elif event.event_type in [ConfigEventType.HOT_RELOAD_SUCCESS, ConfigEventType.HOT_RELOAD_FAILURE]:
            success = event.event_type == ConfigEventType.HOT_RELOAD_SUCCESS
            duration_ms = event.metadata.get("reload_time_ms", 0.0)
            error = None if success else event.validation_errors[0] if event.validation_errors else "Unknown error"
            
            self.audit_logger.log_config_reload(
                event.file_path,
                success,
                duration_ms,
                error
            )


class ConfigurationIntegrationManager:
    """
    Main integration manager that coordinates configuration system 
    with event bus and audit logging.
    """
    
    def __init__(self,
                 runtime_manager: RuntimeConfigurationManager,
                 event_bus,
                 audit_logger: Optional[AuditLogger] = None):
        """
        Initialize integration manager.
        
        Args:
            runtime_manager: Runtime configuration manager
            event_bus: Application event bus
            audit_logger: Base audit logger
        """
        self.runtime_manager = runtime_manager
        self.event_bus = event_bus
        
        # Setup components
        self.config_audit_logger = ConfigurationAuditLogger(audit_logger)
        self.event_bus_integration = EventBusIntegration(event_bus, self.config_audit_logger)
        
        # Setup integration
        self._setup_event_forwarding()
        self._setup_audit_tracking()
    
    def set_user_context(self, user_id: str, session_id: Optional[str] = None) -> None:
        """Set user context for audit logging."""
        self.config_audit_logger.set_user_context(user_id, session_id)
    
    def clear_user_context(self) -> None:
        """Clear user context."""
        self.config_audit_logger.clear_user_context()
    
    def get_integration_status(self) -> Dict[str, Any]:
        """Get overall integration status."""
        return {
            "runtime_manager": self.runtime_manager.get_runtime_info(),
            "audit_logger": self.config_audit_logger.get_performance_report(),
            "event_bus": self.event_bus_integration.get_integration_stats(),
            "integration_active": True
        }
    
    def generate_compliance_report(self, 
                                  start_date: Optional[datetime] = None,
                                  end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Generate compliance report for configuration operations."""
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()
        
        return self.config_audit_logger.get_compliance_report(start_date, end_date)
    
    def _setup_event_forwarding(self) -> None:
        """Setup event forwarding from configuration to event bus."""
        # Replace the event emitter's event bus with our integration
        original_emit = self.runtime_manager._event_emitter._emit_event
        
        def integrated_emit(event):
            # Call original emit
            original_emit(event)
            
            # Forward to event bus via integration
            self.event_bus_integration.publish_config_event(event)
        
        self.runtime_manager._event_emitter._emit_event = integrated_emit
    
    def _setup_audit_tracking(self) -> None:
        """Setup audit tracking for configuration operations."""
        # Intercept configuration manager operations for audit logging
        original_set = self.runtime_manager._config_manager.set
        
        def audited_set(key, value, source):
            old_value = self.runtime_manager._config_manager.get(key)
            result = original_set(key, value, source)
            self.config_audit_logger.log_config_write(key, old_value, value, source)
            return result
        
        self.runtime_manager._config_manager.set = audited_set
        
        # Intercept file watching operations
        original_watch = self.runtime_manager._watcher.watch_config_file
        original_unwatch = self.runtime_manager._watcher.unwatch_config_file
        
        def audited_watch(file_path, parser=None):
            result = original_watch(file_path, parser)
            self.config_audit_logger.log_file_watch_start(Path(file_path))
            return result
        
        def audited_unwatch(file_path):
            result = original_unwatch(file_path)
            self.config_audit_logger.log_file_watch_stop(Path(file_path))
            return result
        
        self.runtime_manager._watcher.watch_config_file = audited_watch
        self.runtime_manager._watcher.unwatch_config_file = audited_unwatch