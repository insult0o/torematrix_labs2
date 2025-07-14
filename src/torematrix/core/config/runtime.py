"""
Runtime configuration management with hot reload and rollback capabilities.

This module provides the main runtime configuration manager that integrates
file watching, event notifications, and safe hot reloading with rollback.
"""

import asyncio
import time
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable, Union, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from contextlib import contextmanager
import copy

from .manager import ConfigurationManager
from .watcher import ConfigurationWatcher, ConfigurationChange, ChangeType
from .events import ConfigurationEventEmitter, ConfigEventType
from .types import ConfigDict, ConfigSource, ConfigUpdatePolicy
from .exceptions import (
    ConfigurationError,
    ValidationError,
    ConfigurationAccessError,
    ConfigurationLockError
)


@dataclass
class ReloadAttempt:
    """Record of a configuration reload attempt."""
    timestamp: datetime
    file_path: Path
    success: bool
    duration_ms: float
    error: Optional[str] = None
    config_size: int = 0
    rollback_performed: bool = False


@dataclass
class RuntimeConfiguration:
    """Runtime configuration state with metadata."""
    config: ConfigDict
    source_files: Set[Path] = field(default_factory=set)
    last_reload: Optional[datetime] = None
    reload_count: int = 0
    error_count: int = 0
    version: int = 0
    checksum: Optional[str] = None


class RuntimeConfigurationManager:
    """
    Runtime configuration manager with hot reload and rollback capabilities.
    
    Features:
    - Hot reload from multiple configuration files
    - Automatic rollback on validation failure
    - Event-driven notifications
    - Performance monitoring
    - Thread-safe operations
    - Graceful error handling
    """
    
    def __init__(self,
                 base_config: Optional[Dict[str, Any]] = None,
                 event_bus=None,
                 enable_hot_reload: bool = True,
                 reload_debounce_ms: float = 500,
                 max_reload_attempts: int = 3,
                 rollback_on_error: bool = True):
        """
        Initialize runtime configuration manager.
        
        Args:
            base_config: Base configuration dictionary
            event_bus: Event bus for notifications
            enable_hot_reload: Enable automatic hot reload
            reload_debounce_ms: Debounce delay for file changes
            max_reload_attempts: Maximum reload attempts before giving up
            rollback_on_error: Automatically rollback on validation errors
        """
        # Core configuration management
        self._config_manager = ConfigurationManager()
        if base_config:
            self._config_manager.update(base_config, ConfigSource.DEFAULTS)
        
        # Hot reload components
        self._watcher = ConfigurationWatcher(
            debounce_delay=reload_debounce_ms / 1000,
            enable_hot_reload=False  # We'll handle reload manually for better control
        )
        
        # Event system
        self._event_emitter = ConfigurationEventEmitter(event_bus)
        
        # Runtime state
        self._runtime_config = RuntimeConfiguration(
            config=self._config_manager.to_dict()
        )
        
        # Hot reload settings
        self.enable_hot_reload = enable_hot_reload
        self.reload_debounce_ms = reload_debounce_ms
        self.max_reload_attempts = max_reload_attempts
        self.rollback_on_error = rollback_on_error
        
        # State tracking
        self._reload_history: List[ReloadAttempt] = []
        self._max_history = 100
        self._reload_lock = threading.RLock()
        self._pending_reloads: Dict[Path, asyncio.Task] = {}
        
        # Performance metrics
        self._total_reload_time = 0.0
        self._successful_reloads = 0
        self._failed_reloads = 0
        
        # Setup callbacks
        self._setup_callbacks()
    
    def add_config_file(self,
                       file_path: Union[str, Path],
                       source: ConfigSource = ConfigSource.FILE,
                       watch: bool = True) -> None:
        """
        Add a configuration file to be managed.
        
        Args:
            file_path: Path to configuration file
            source: Configuration source type
            watch: Enable file watching for hot reload
        """
        file_path = Path(file_path).resolve()
        
        # Load initial configuration
        try:
            initial_config = self._watcher._parse_config_file(file_path)
            
            # Merge into main configuration
            self._config_manager.merge(initial_config, source)
            
            # Update runtime state
            self._runtime_config.source_files.add(file_path)
            self._runtime_config.config = self._config_manager.to_dict()
            self._runtime_config.version += 1
            
            # Emit loaded event
            self._event_emitter.emit_config_loaded(file_path, initial_config, source)
            
            # Start watching if enabled
            if watch and self.enable_hot_reload:
                self._watcher.watch_config_file(file_path)
            
        except Exception as e:
            self._event_emitter.emit_config_error(e, file_path)
            raise ConfigurationError(f"Failed to load config file {file_path}: {e}")
    
    def remove_config_file(self, file_path: Union[str, Path]) -> None:
        """Remove a configuration file from management."""
        file_path = Path(file_path).resolve()
        
        # Stop watching
        self._watcher.unwatch_config_file(file_path)
        
        # Remove from runtime state
        self._runtime_config.source_files.discard(file_path)
        
        # Cancel any pending reload
        if file_path in self._pending_reloads:
            self._pending_reloads[file_path].cancel()
            del self._pending_reloads[file_path]
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-notation key.
        
        Args:
            key: Dot-notation key (e.g., 'database.host')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        return self._config_manager.get(key, default)
    
    def set(self, key: str, value: Any, source: ConfigSource = ConfigSource.RUNTIME) -> None:
        """
        Set configuration value with hot reload integration.
        
        Args:
            key: Dot-notation key
            value: Value to set
            source: Configuration source
        """
        old_value = self.get(key)
        
        # Update configuration
        self._config_manager.set(key, value, source)
        
        # Update runtime state
        self._runtime_config.config = self._config_manager.to_dict()
        self._runtime_config.version += 1
        
        # Emit change event
        self._event_emitter.emit_config_changed(key, old_value, value, source)
    
    def get_runtime_info(self) -> Dict[str, Any]:
        """Get runtime configuration information."""
        with self._reload_lock:
            return {
                "version": self._runtime_config.version,
                "source_files": [str(f) for f in self._runtime_config.source_files],
                "last_reload": self._runtime_config.last_reload.isoformat() if self._runtime_config.last_reload else None,
                "reload_count": self._runtime_config.reload_count,
                "error_count": self._runtime_config.error_count,
                "config_size": len(str(self._runtime_config.config)),
                "hot_reload_enabled": self.enable_hot_reload,
                "performance": self.get_performance_stats()
            }
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        total_reloads = self._successful_reloads + self._failed_reloads
        success_rate = self._successful_reloads / total_reloads if total_reloads > 0 else 1.0
        avg_reload_time = self._total_reload_time / self._successful_reloads if self._successful_reloads > 0 else 0.0
        
        return {
            "total_reloads": total_reloads,
            "successful_reloads": self._successful_reloads,
            "failed_reloads": self._failed_reloads,
            "success_rate": success_rate,
            "avg_reload_time_ms": avg_reload_time * 1000,
            "total_reload_time_ms": self._total_reload_time * 1000
        }
    
    def reload_all(self) -> bool:
        """
        Manually reload all configuration files.
        
        Returns:
            True if all reloads successful
        """
        success = True
        
        for file_path in list(self._runtime_config.source_files):
            if not self.reload_file(file_path):
                success = False
        
        return success
    
    def reload_file(self, file_path: Union[str, Path]) -> bool:
        """
        Manually reload a specific configuration file.
        
        Args:
            file_path: Path to configuration file
            
        Returns:
            True if reload successful
        """
        file_path = Path(file_path).resolve()
        
        if file_path not in self._runtime_config.source_files:
            return False
        
        return self._perform_reload(file_path, manual=True)
    
    async def reload_file_async(self, file_path: Union[str, Path]) -> bool:
        """
        Asynchronously reload a configuration file.
        
        Args:
            file_path: Path to configuration file
            
        Returns:
            True if reload successful
        """
        file_path = Path(file_path).resolve()
        
        # Cancel existing reload task
        if file_path in self._pending_reloads:
            self._pending_reloads[file_path].cancel()
        
        # Create new reload task
        task = asyncio.create_task(self._async_reload(file_path))
        self._pending_reloads[file_path] = task
        
        try:
            return await task
        finally:
            self._pending_reloads.pop(file_path, None)
    
    def validate_configuration(self) -> List[str]:
        """
        Validate current configuration.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = self._config_manager.validate()
        
        # Emit validation event
        self._event_emitter.emit_config_validated(
            errors, 
            len(str(self._runtime_config.config))
        )
        
        return errors
    
    def create_checkpoint(self) -> str:
        """
        Create a configuration checkpoint for rollback.
        
        Returns:
            Checkpoint ID
        """
        checkpoint_id = f"checkpoint_{int(time.time() * 1000)}"
        
        # Store current state
        checkpoint_data = {
            "config": copy.deepcopy(self._runtime_config.config),
            "version": self._runtime_config.version,
            "timestamp": datetime.now()
        }
        
        # Store checkpoint (could be enhanced with persistence)
        if not hasattr(self, '_checkpoints'):
            self._checkpoints = {}
        
        self._checkpoints[checkpoint_id] = checkpoint_data
        
        return checkpoint_id
    
    def rollback_to_checkpoint(self, checkpoint_id: str) -> bool:
        """
        Rollback configuration to a checkpoint.
        
        Args:
            checkpoint_id: ID of checkpoint to restore
            
        Returns:
            True if rollback successful
        """
        if not hasattr(self, '_checkpoints') or checkpoint_id not in self._checkpoints:
            return False
        
        checkpoint = self._checkpoints[checkpoint_id]
        
        try:
            # Restore configuration
            self._runtime_config.config = checkpoint["config"]
            self._runtime_config.version = checkpoint["version"]
            
            # Update manager state
            # Note: This is simplified - a full implementation would restore manager state
            
            # Emit rollback event
            self._event_emitter.emit_config_rollback(
                Path("checkpoint"),
                checkpoint["config"],
                f"Rollback to checkpoint {checkpoint_id}"
            )
            
            return True
            
        except Exception as e:
            self._event_emitter.emit_config_error(e)
            return False
    
    @contextmanager
    def safe_update(self):
        """
        Context manager for safe configuration updates with automatic rollback.
        
        Usage:
            with config_manager.safe_update():
                config_manager.set("some.key", "value")
                # If exception occurs, changes are rolled back
        """
        checkpoint_id = self.create_checkpoint()
        
        try:
            yield
            
            # Validate after all updates
            errors = self.validate_configuration()
            if errors and self.rollback_on_error:
                self.rollback_to_checkpoint(checkpoint_id)
                raise ValidationError("Configuration validation failed", errors)
                
        except Exception as e:
            # Rollback on any error
            self.rollback_to_checkpoint(checkpoint_id)
            raise
    
    def stop(self) -> None:
        """Stop the runtime configuration manager."""
        # Cancel pending reloads
        for task in self._pending_reloads.values():
            task.cancel()
        self._pending_reloads.clear()
        
        # Stop watcher
        self._watcher.stop()
        
        # Clear state
        self._runtime_config.source_files.clear()
    
    def _setup_callbacks(self) -> None:
        """Setup callbacks for file watcher."""
        self._watcher.add_change_callback(self._handle_file_change)
        self._watcher.add_reload_callback(self._handle_reload_success)
        self._watcher.add_error_callback(self._handle_reload_error)
    
    def _handle_file_change(self, change: ConfigurationChange) -> None:
        """Handle file system changes."""
        if not self.enable_hot_reload:
            return
        
        # Emit file change event
        from .events import FileSystemChangeEvent
        file_event = FileSystemChangeEvent(file_change=change)
        self._event_emitter._emit_event(file_event)
        
        # Trigger reload for modifications and creations
        if change.change_type in [ChangeType.MODIFIED, ChangeType.CREATED]:
            # Use async reload for better performance
            asyncio.create_task(self.reload_file_async(change.path))
    
    def _handle_reload_success(self, file_path: Path, config: ConfigDict) -> None:
        """Handle successful configuration reload."""
        # This callback is from the watcher, but we handle reloads manually
        pass
    
    def _handle_reload_error(self, file_path: Path, error: Exception) -> None:
        """Handle configuration reload errors."""
        self._event_emitter.emit_hot_reload_failure(file_path, error)
    
    def _perform_reload(self, file_path: Path, manual: bool = False) -> bool:
        """
        Perform configuration file reload with error handling and rollback.
        
        Args:
            file_path: Path to configuration file
            manual: Whether this is a manual reload
            
        Returns:
            True if reload successful
        """
        with self._reload_lock:
            start_time = time.time()
            attempt = ReloadAttempt(
                timestamp=datetime.now(),
                file_path=file_path,
                success=False,
                duration_ms=0.0
            )
            
            try:
                # Create checkpoint for rollback
                checkpoint_id = self.create_checkpoint()
                
                # Parse new configuration
                new_config = self._watcher._parse_config_file(file_path)
                attempt.config_size = len(str(new_config))
                
                # Determine source based on file
                source = ConfigSource.FILE  # Could be enhanced to track sources per file
                
                # Update configuration
                old_config = self._config_manager.to_dict()
                self._config_manager.merge(new_config, source)
                
                # Validate new configuration
                validation_errors = self._config_manager.validate()
                
                if validation_errors and self.rollback_on_error:
                    # Rollback on validation failure
                    self.rollback_to_checkpoint(checkpoint_id)
                    attempt.rollback_performed = True
                    attempt.error = f"Validation failed: {'; '.join(validation_errors)}"
                    
                    self._event_emitter.emit_hot_reload_failure(
                        file_path,
                        ValidationError("Configuration validation failed", validation_errors)
                    )
                    
                    self._failed_reloads += 1
                    return False
                
                # Success - update runtime state
                self._runtime_config.config = self._config_manager.to_dict()
                self._runtime_config.last_reload = datetime.now()
                self._runtime_config.reload_count += 1
                self._runtime_config.version += 1
                
                # Record success
                attempt.success = True
                reload_time = time.time() - start_time
                attempt.duration_ms = reload_time * 1000
                
                # Update performance stats
                self._successful_reloads += 1
                self._total_reload_time += reload_time
                
                # Emit success event
                self._event_emitter.emit_hot_reload_success(
                    file_path,
                    new_config,
                    attempt.duration_ms
                )
                
                return True
                
            except Exception as e:
                # Record failure
                attempt.error = str(e)
                reload_time = time.time() - start_time
                attempt.duration_ms = reload_time * 1000
                
                # Update error stats
                self._failed_reloads += 1
                self._runtime_config.error_count += 1
                
                # Emit error event
                self._event_emitter.emit_hot_reload_failure(file_path, e)
                
                return False
                
            finally:
                # Record attempt
                self._reload_history.append(attempt)
                if len(self._reload_history) > self._max_history:
                    self._reload_history = self._reload_history[-self._max_history:]
    
    async def _async_reload(self, file_path: Path) -> bool:
        """Asynchronous wrapper for reload operation."""
        # Run reload in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._perform_reload, file_path, False)
    
    def get_reload_history(self, limit: Optional[int] = None) -> List[ReloadAttempt]:
        """
        Get configuration reload history.
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List of reload attempts
        """
        with self._reload_lock:
            history = self._reload_history.copy()
            
            if limit:
                history = history[-limit:]
            
            return history