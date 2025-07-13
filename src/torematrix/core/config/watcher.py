"""
Configuration file system watcher for hot reload capabilities.

This module provides real-time monitoring of configuration files and directories
with efficient change detection and notification.
"""

import asyncio
import hashlib
import json
import threading
import time
from pathlib import Path
from typing import Dict, List, Set, Optional, Callable, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import weakref

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent, FileDeletedEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    # Create dummy classes when watchdog is not available
    class FileSystemEventHandler:
        def on_modified(self, event): pass
        def on_created(self, event): pass
        def on_deleted(self, event): pass

from .types import ConfigDict, ConfigSource
from .exceptions import ConfigurationError


class ChangeType(Enum):
    """Configuration change types."""
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    MOVED = "moved"


@dataclass
class ConfigurationChange:
    """Configuration change notification."""
    path: Path
    change_type: ChangeType
    timestamp: datetime = field(default_factory=datetime.now)
    old_content: Optional[ConfigDict] = None
    new_content: Optional[ConfigDict] = None
    content_hash: Optional[str] = None
    file_size: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "path": str(self.path),
            "change_type": self.change_type.value,
            "timestamp": self.timestamp.isoformat(),
            "old_content": self.old_content,
            "new_content": self.new_content,
            "content_hash": self.content_hash,
            "file_size": self.file_size
        }


class FileWatcher:
    """File system watcher with change detection."""
    
    def __init__(self, debounce_delay: float = 0.5):
        """
        Initialize file watcher.
        
        Args:
            debounce_delay: Delay in seconds to debounce rapid file changes
        """
        self.debounce_delay = debounce_delay
        self._watched_files: Dict[Path, Dict[str, Any]] = {}
        self._file_hashes: Dict[Path, str] = {}
        self._observers: List[Observer] = []
        self._event_handlers: List[FileSystemEventHandler] = []
        self._callbacks: List[weakref.ref] = []
        self._debounce_timers: Dict[Path, threading.Timer] = {}
        self._lock = threading.RLock()
        self._running = False
    
    def add_callback(self, callback: Callable[[ConfigurationChange], None]) -> None:
        """Add change notification callback."""
        with self._lock:
            self._callbacks.append(weakref.ref(callback))
    
    def remove_callback(self, callback: Callable[[ConfigurationChange], None]) -> None:
        """Remove change notification callback."""
        with self._lock:
            self._callbacks = [ref for ref in self._callbacks 
                             if ref() is not None and ref() != callback]
    
    def watch_file(self, file_path: Path) -> None:
        """
        Start watching a configuration file.
        
        Args:
            file_path: Path to configuration file
        """
        file_path = Path(file_path).resolve()
        
        with self._lock:
            if file_path in self._watched_files:
                return
            
            # Store initial file state
            self._watched_files[file_path] = {
                "added_at": datetime.now(),
                "last_check": datetime.now(),
                "exists": file_path.exists()
            }
            
            if file_path.exists():
                self._update_file_hash(file_path)
            
            # Set up watchdog observer if available
            if WATCHDOG_AVAILABLE and file_path.parent.exists():
                handler = ConfigFileHandler(self, file_path)
                observer = Observer()
                observer.schedule(handler, str(file_path.parent), recursive=False)
                
                if not self._running:
                    observer.start()
                    self._running = True
                
                self._observers.append(observer)
                self._event_handlers.append(handler)
    
    def unwatch_file(self, file_path: Path) -> None:
        """Stop watching a configuration file."""
        file_path = Path(file_path).resolve()
        
        with self._lock:
            if file_path in self._watched_files:
                del self._watched_files[file_path]
            
            if file_path in self._file_hashes:
                del self._file_hashes[file_path]
            
            # Cancel any pending debounce timer
            if file_path in self._debounce_timers:
                self._debounce_timers[file_path].cancel()
                del self._debounce_timers[file_path]
    
    def check_file_changes(self) -> List[ConfigurationChange]:
        """
        Manually check for file changes.
        
        Returns:
            List of detected changes
        """
        changes = []
        
        with self._lock:
            for file_path in list(self._watched_files.keys()):
                change = self._check_single_file(file_path)
                if change:
                    changes.append(change)
        
        return changes
    
    def get_file_hash(self, file_path: Path) -> Optional[str]:
        """Get current hash of a watched file."""
        with self._lock:
            return self._file_hashes.get(Path(file_path).resolve())
    
    def stop(self) -> None:
        """Stop all file watching."""
        with self._lock:
            # Cancel all debounce timers
            for timer in self._debounce_timers.values():
                timer.cancel()
            self._debounce_timers.clear()
            
            # Stop observers
            for observer in self._observers:
                observer.stop()
                observer.join()
            
            self._observers.clear()
            self._event_handlers.clear()
            self._running = False
    
    def _update_file_hash(self, file_path: Path) -> str:
        """Update stored hash for a file."""
        try:
            content = file_path.read_bytes()
            file_hash = hashlib.sha256(content).hexdigest()
            self._file_hashes[file_path] = file_hash
            return file_hash
        except Exception:
            # File might be temporarily unavailable
            return ""
    
    def _check_single_file(self, file_path: Path) -> Optional[ConfigurationChange]:
        """Check a single file for changes."""
        try:
            file_info = self._watched_files[file_path]
            file_exists = file_path.exists()
            
            # Handle file deletion
            if file_info["exists"] and not file_exists:
                file_info["exists"] = False
                file_info["last_check"] = datetime.now()
                return ConfigurationChange(
                    path=file_path,
                    change_type=ChangeType.DELETED
                )
            
            # Handle file creation
            if not file_info["exists"] and file_exists:
                file_info["exists"] = True
                file_info["last_check"] = datetime.now()
                new_hash = self._update_file_hash(file_path)
                return ConfigurationChange(
                    path=file_path,
                    change_type=ChangeType.CREATED,
                    content_hash=new_hash,
                    file_size=file_path.stat().st_size if file_exists else None
                )
            
            # Handle file modification
            if file_exists:
                old_hash = self._file_hashes.get(file_path, "")
                new_hash = self._calculate_file_hash(file_path)
                
                if old_hash != new_hash:
                    self._file_hashes[file_path] = new_hash
                    file_info["last_check"] = datetime.now()
                    
                    return ConfigurationChange(
                        path=file_path,
                        change_type=ChangeType.MODIFIED,
                        content_hash=new_hash,
                        file_size=file_path.stat().st_size
                    )
            
        except Exception:
            # Ignore errors during checking
            pass
        
        return None
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate file hash without storing it."""
        try:
            content = file_path.read_bytes()
            return hashlib.sha256(content).hexdigest()
        except Exception:
            return ""
    
    def _notify_change(self, change: ConfigurationChange) -> None:
        """Notify all callbacks about a change."""
        with self._lock:
            # Clean up dead references
            self._callbacks = [ref for ref in self._callbacks if ref() is not None]
            
            # Notify active callbacks
            for ref in self._callbacks:
                callback = ref()
                if callback:
                    try:
                        callback(change)
                    except Exception as e:
                        # Log error but continue notifying other callbacks
                        print(f"Error in file change callback: {e}")
    
    def _debounced_notify(self, file_path: Path) -> None:
        """Handle debounced file change notification."""
        with self._lock:
            if file_path in self._debounce_timers:
                del self._debounce_timers[file_path]
            
            change = self._check_single_file(file_path)
            if change:
                self._notify_change(change)


class ConfigFileHandler(FileSystemEventHandler):
    """Watchdog event handler for configuration files."""
    
    def __init__(self, watcher: FileWatcher, target_file: Path):
        """Initialize handler for specific file."""
        self.watcher = watcher
        self.target_file = target_file
        super().__init__()
    
    def on_modified(self, event):
        """Handle file modification events."""
        if not event.is_directory and Path(event.src_path) == self.target_file:
            self._handle_change()
    
    def on_created(self, event):
        """Handle file creation events."""
        if not event.is_directory and Path(event.src_path) == self.target_file:
            self._handle_change()
    
    def on_deleted(self, event):
        """Handle file deletion events."""
        if not event.is_directory and Path(event.src_path) == self.target_file:
            self._handle_change()
    
    def _handle_change(self) -> None:
        """Handle file system change with debouncing."""
        with self.watcher._lock:
            # Cancel existing timer
            if self.target_file in self.watcher._debounce_timers:
                self.watcher._debounce_timers[self.target_file].cancel()
            
            # Set new debounce timer
            timer = threading.Timer(
                self.watcher.debounce_delay,
                self.watcher._debounced_notify,
                args=[self.target_file]
            )
            self.watcher._debounce_timers[self.target_file] = timer
            timer.start()


class ConfigurationWatcher:
    """
    High-level configuration watcher with hot reload capabilities.
    
    Features:
    - File system monitoring with change detection
    - Configuration parsing and validation
    - Hot reload with rollback on failure
    - Event notifications
    - Performance monitoring
    """
    
    def __init__(self, 
                 debounce_delay: float = 0.5,
                 enable_hot_reload: bool = True,
                 backup_count: int = 5):
        """
        Initialize configuration watcher.
        
        Args:
            debounce_delay: Delay to debounce rapid file changes
            enable_hot_reload: Enable automatic hot reload
            backup_count: Number of configuration backups to keep
        """
        self.debounce_delay = debounce_delay
        self.enable_hot_reload = enable_hot_reload
        self.backup_count = backup_count
        
        self._file_watcher = FileWatcher(debounce_delay)
        self._config_parsers: Dict[str, Callable[[Path], ConfigDict]] = {}
        self._change_callbacks: List[weakref.ref] = []
        self._reload_callbacks: List[weakref.ref] = []
        self._error_callbacks: List[weakref.ref] = []
        
        # Configuration state
        self._configurations: Dict[Path, ConfigDict] = {}
        self._config_backups: Dict[Path, List[ConfigDict]] = {}
        self._last_reload_times: Dict[Path, datetime] = {}
        
        # Performance tracking
        self._reload_count = 0
        self._error_count = 0
        self._total_reload_time = 0.0
        
        # Set up file watcher callback
        self._file_watcher.add_callback(self._handle_file_change)
        
        # Register default parsers
        self._register_default_parsers()
    
    def add_change_callback(self, callback: Callable[[ConfigurationChange], None]) -> None:
        """Add callback for configuration changes."""
        self._change_callbacks.append(weakref.ref(callback))
    
    def add_reload_callback(self, callback: Callable[[Path, ConfigDict], None]) -> None:
        """Add callback for successful reloads."""
        self._reload_callbacks.append(weakref.ref(callback))
    
    def add_error_callback(self, callback: Callable[[Path, Exception], None]) -> None:
        """Add callback for reload errors."""
        self._error_callbacks.append(weakref.ref(callback))
    
    def watch_config_file(self, 
                         file_path: Union[str, Path],
                         parser: Optional[Callable[[Path], ConfigDict]] = None) -> None:
        """
        Start watching a configuration file.
        
        Args:
            file_path: Path to configuration file
            parser: Custom parser function (optional)
        """
        file_path = Path(file_path).resolve()
        
        # Register custom parser if provided
        if parser:
            self._config_parsers[str(file_path)] = parser
        
        # Load initial configuration
        try:
            config = self._parse_config_file(file_path)
            self._configurations[file_path] = config
            self._create_backup(file_path, config)
        except Exception as e:
            self._notify_error(file_path, e)
        
        # Start watching
        self._file_watcher.watch_file(file_path)
    
    def unwatch_config_file(self, file_path: Union[str, Path]) -> None:
        """Stop watching a configuration file."""
        file_path = Path(file_path).resolve()
        
        self._file_watcher.unwatch_file(file_path)
        
        # Clean up state
        self._configurations.pop(file_path, None)
        self._config_backups.pop(file_path, None)
        self._last_reload_times.pop(file_path, None)
        self._config_parsers.pop(str(file_path), None)
    
    def get_configuration(self, file_path: Union[str, Path]) -> Optional[ConfigDict]:
        """Get current configuration for a file."""
        file_path = Path(file_path).resolve()
        return self._configurations.get(file_path)
    
    def reload_configuration(self, file_path: Union[str, Path]) -> bool:
        """
        Manually reload a configuration file.
        
        Args:
            file_path: Path to configuration file
            
        Returns:
            True if reload successful
        """
        file_path = Path(file_path).resolve()
        
        try:
            start_time = time.time()
            new_config = self._parse_config_file(file_path)
            
            # Backup old configuration
            old_config = self._configurations.get(file_path)
            if old_config:
                self._create_backup(file_path, old_config)
            
            # Update configuration
            self._configurations[file_path] = new_config
            self._last_reload_times[file_path] = datetime.now()
            
            # Update performance stats
            reload_time = time.time() - start_time
            self._reload_count += 1
            self._total_reload_time += reload_time
            
            # Notify success
            self._notify_reload_success(file_path, new_config)
            
            return True
            
        except Exception as e:
            self._error_count += 1
            self._notify_error(file_path, e)
            return False
    
    def rollback_configuration(self, file_path: Union[str, Path]) -> bool:
        """
        Rollback configuration to previous version.
        
        Args:
            file_path: Path to configuration file
            
        Returns:
            True if rollback successful
        """
        file_path = Path(file_path).resolve()
        
        backups = self._config_backups.get(file_path, [])
        if not backups:
            return False
        
        # Restore most recent backup
        previous_config = backups[-1]
        self._configurations[file_path] = previous_config
        
        # Remove the used backup
        backups.pop()
        
        # Notify about rollback
        self._notify_reload_success(file_path, previous_config)
        
        return True
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get watcher performance statistics."""
        avg_reload_time = (
            self._total_reload_time / self._reload_count 
            if self._reload_count > 0 else 0
        )
        
        return {
            "watched_files": len(self._configurations),
            "reload_count": self._reload_count,
            "error_count": self._error_count,
            "avg_reload_time_ms": avg_reload_time * 1000,
            "total_reload_time_ms": self._total_reload_time * 1000,
            "success_rate": (
                (self._reload_count - self._error_count) / self._reload_count
                if self._reload_count > 0 else 1.0
            )
        }
    
    def stop(self) -> None:
        """Stop all configuration watching."""
        self._file_watcher.stop()
        
        # Clear state
        self._configurations.clear()
        self._config_backups.clear()
        self._last_reload_times.clear()
        self._config_parsers.clear()
    
    def _register_default_parsers(self) -> None:
        """Register default configuration file parsers."""
        def json_parser(file_path: Path) -> ConfigDict:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        def toml_parser(file_path: Path) -> ConfigDict:
            try:
                import tomllib
                with open(file_path, 'rb') as f:
                    return tomllib.load(f)
            except ImportError:
                raise ConfigurationError("TOML support requires Python 3.11+ or tomli package")
        
        def yaml_parser(file_path: Path) -> ConfigDict:
            try:
                import yaml
                with open(file_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
            except ImportError:
                raise ConfigurationError("YAML support requires PyYAML package")
        
        # Register parsers by extension
        self._default_parsers = {
            '.json': json_parser,
            '.toml': toml_parser,
            '.yaml': yaml_parser,
            '.yml': yaml_parser
        }
    
    def _parse_config_file(self, file_path: Path) -> ConfigDict:
        """Parse a configuration file using appropriate parser."""
        # Check for custom parser first
        custom_parser = self._config_parsers.get(str(file_path))
        if custom_parser:
            return custom_parser(file_path)
        
        # Use default parser based on extension
        extension = file_path.suffix.lower()
        parser = self._default_parsers.get(extension)
        
        if not parser:
            raise ConfigurationError(f"No parser available for file type: {extension}")
        
        return parser(file_path)
    
    def _create_backup(self, file_path: Path, config: ConfigDict) -> None:
        """Create backup of configuration."""
        if file_path not in self._config_backups:
            self._config_backups[file_path] = []
        
        backups = self._config_backups[file_path]
        backups.append(config.copy())
        
        # Limit backup count
        while len(backups) > self.backup_count:
            backups.pop(0)
    
    def _handle_file_change(self, change: ConfigurationChange) -> None:
        """Handle file system change notification."""
        # Notify change callbacks
        self._notify_change(change)
        
        # Handle hot reload if enabled
        if self.enable_hot_reload and change.change_type in [ChangeType.MODIFIED, ChangeType.CREATED]:
            self.reload_configuration(change.path)
    
    def _notify_change(self, change: ConfigurationChange) -> None:
        """Notify change callbacks."""
        # Clean up dead references
        self._change_callbacks = [ref for ref in self._change_callbacks if ref() is not None]
        
        for ref in self._change_callbacks:
            callback = ref()
            if callback:
                try:
                    callback(change)
                except Exception as e:
                    print(f"Error in change callback: {e}")
    
    def _notify_reload_success(self, file_path: Path, config: ConfigDict) -> None:
        """Notify reload success callbacks."""
        # Clean up dead references
        self._reload_callbacks = [ref for ref in self._reload_callbacks if ref() is not None]
        
        for ref in self._reload_callbacks:
            callback = ref()
            if callback:
                try:
                    callback(file_path, config)
                except Exception as e:
                    print(f"Error in reload callback: {e}")
    
    def _notify_error(self, file_path: Path, error: Exception) -> None:
        """Notify error callbacks."""
        # Clean up dead references
        self._error_callbacks = [ref for ref in self._error_callbacks if ref() is not None]
        
        for ref in self._error_callbacks:
            callback = ref()
            if callback:
                try:
                    callback(file_path, error)
                except Exception as e:
                    print(f"Error in error callback: {e}")