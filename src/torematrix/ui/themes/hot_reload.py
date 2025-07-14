"""Hot reload system for theme development.

This module provides real-time theme file watching and automatic reloading
for efficient theme development workflow.
"""

import logging
import time
import threading
from typing import Dict, List, Optional, Callable, Set, Any
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import json

from PyQt6.QtCore import QObject, QFileSystemWatcher, QTimer, pyqtSignal
from PyQt6.QtWidgets import QApplication

from .base import Theme
from .engine import ThemeEngine
from .exceptions import ThemeError

logger = logging.getLogger(__name__)


class ReloadTrigger(Enum):
    """Events that can trigger a theme reload."""
    FILE_MODIFIED = "file_modified"
    FILE_CREATED = "file_created"
    FILE_DELETED = "file_deleted"
    MANUAL = "manual"
    TIMER = "timer"


@dataclass
class ReloadEvent:
    """Information about a theme reload event."""
    timestamp: float
    theme_name: str
    trigger: ReloadTrigger
    file_path: Optional[Path] = None
    success: bool = True
    error_message: Optional[str] = None
    reload_time_ms: float = 0.0
    additional_data: Dict[str, Any] = field(default_factory=dict)


class ThemeFileWatcher(QObject):
    """File system watcher for theme files with debouncing."""
    
    # Signals for file system events
    file_changed = pyqtSignal(str)  # file_path
    file_created = pyqtSignal(str)  # file_path
    file_deleted = pyqtSignal(str)  # file_path
    
    def __init__(self, parent: Optional[QObject] = None):
        """Initialize theme file watcher.
        
        Args:
            parent: Parent QObject
        """
        super().__init__(parent)
        
        self.watcher = QFileSystemWatcher()
        self.watched_files: Set[str] = set()
        self.watched_directories: Set[str] = set()
        
        # Debouncing
        self.debounce_timer = QTimer()
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.timeout.connect(self._process_pending_changes)
        self.debounce_delay = 500  # 500ms debounce
        
        self.pending_changes: Dict[str, str] = {}  # file_path -> change_type
        
        # Connect watcher signals
        self.watcher.fileChanged.connect(self._on_file_changed)
        self.watcher.directoryChanged.connect(self._on_directory_changed)
        
        logger.debug("ThemeFileWatcher initialized")
    
    def watch_file(self, file_path: Path) -> bool:
        """Watch a specific theme file.
        
        Args:
            file_path: Path to theme file
            
        Returns:
            True if watching started successfully
        """
        file_str = str(file_path.resolve())
        
        if file_str in self.watched_files:
            return True
        
        if file_path.exists():
            success = self.watcher.addPath(file_str)
            if success:
                self.watched_files.add(file_str)
                logger.debug(f"Started watching file: {file_path}")
                return True
            else:
                logger.warning(f"Failed to watch file: {file_path}")
        else:
            logger.warning(f"File does not exist: {file_path}")
        
        return False
    
    def watch_directory(self, directory_path: Path, recursive: bool = True) -> bool:
        """Watch a directory for theme file changes.
        
        Args:
            directory_path: Path to directory
            recursive: Whether to watch subdirectories
            
        Returns:
            True if watching started successfully
        """
        dir_str = str(directory_path.resolve())
        
        if dir_str in self.watched_directories:
            return True
        
        if directory_path.exists() and directory_path.is_dir():
            success = self.watcher.addPath(dir_str)
            if success:
                self.watched_directories.add(dir_str)
                logger.debug(f"Started watching directory: {directory_path}")
                
                # Watch existing theme files in directory
                theme_extensions = ['.yaml', '.yml', '.json', '.toml', '.css', '.qss']
                for file_path in directory_path.iterdir():
                    if file_path.is_file() and file_path.suffix in theme_extensions:
                        self.watch_file(file_path)
                
                # Recursively watch subdirectories if requested
                if recursive:
                    for subdir in directory_path.iterdir():
                        if subdir.is_dir():
                            self.watch_directory(subdir, recursive=True)
                
                return True
            else:
                logger.warning(f"Failed to watch directory: {directory_path}")
        else:
            logger.warning(f"Directory does not exist: {directory_path}")
        
        return False
    
    def unwatch_file(self, file_path: Path) -> None:
        """Stop watching a specific file.
        
        Args:
            file_path: Path to stop watching
        """
        file_str = str(file_path.resolve())
        
        if file_str in self.watched_files:
            self.watcher.removePath(file_str)
            self.watched_files.remove(file_str)
            logger.debug(f"Stopped watching file: {file_path}")
    
    def unwatch_directory(self, directory_path: Path) -> None:
        """Stop watching a directory.
        
        Args:
            directory_path: Path to stop watching
        """
        dir_str = str(directory_path.resolve())
        
        if dir_str in self.watched_directories:
            self.watcher.removePath(dir_str)
            self.watched_directories.remove(dir_str)
            logger.debug(f"Stopped watching directory: {directory_path}")
    
    def _on_file_changed(self, file_path: str) -> None:
        """Handle file change event."""
        self.pending_changes[file_path] = "modified"
        self.debounce_timer.start(self.debounce_delay)
    
    def _on_directory_changed(self, directory_path: str) -> None:
        """Handle directory change event."""
        dir_path = Path(directory_path)
        
        # Check for new theme files
        theme_extensions = ['.yaml', '.yml', '.json', '.toml', '.css', '.qss']
        for file_path in dir_path.iterdir():
            if file_path.is_file() and file_path.suffix in theme_extensions:
                file_str = str(file_path.resolve())
                if file_str not in self.watched_files:
                    # New theme file detected
                    self.watch_file(file_path)
                    self.pending_changes[file_str] = "created"
        
        self.debounce_timer.start(self.debounce_delay)
    
    def _process_pending_changes(self) -> None:
        """Process all pending file changes after debounce delay."""
        for file_path, change_type in self.pending_changes.items():
            if change_type == "modified":
                self.file_changed.emit(file_path)
            elif change_type == "created":
                self.file_created.emit(file_path)
            elif change_type == "deleted":
                self.file_deleted.emit(file_path)
        
        self.pending_changes.clear()
    
    def get_watched_files(self) -> List[str]:
        """Get list of currently watched files."""
        return list(self.watched_files)
    
    def get_watched_directories(self) -> List[str]:
        """Get list of currently watched directories."""
        return list(self.watched_directories)
    
    def clear_watches(self) -> None:
        """Clear all file and directory watches."""
        self.watcher.removePaths(list(self.watched_files))
        self.watcher.removePaths(list(self.watched_directories))
        self.watched_files.clear()
        self.watched_directories.clear()
        self.pending_changes.clear()
        logger.debug("Cleared all file watches")


class HotReloadManager(QObject):
    """Manager for hot reloading themes during development."""
    
    # Signals for reload events
    reload_started = pyqtSignal(str)  # theme_name
    reload_completed = pyqtSignal(str, float)  # theme_name, time_taken
    reload_failed = pyqtSignal(str, str)  # theme_name, error_message
    theme_file_detected = pyqtSignal(str)  # file_path
    
    def __init__(
        self, 
        theme_engine: ThemeEngine, 
        parent: Optional[QObject] = None
    ):
        """Initialize hot reload manager.
        
        Args:
            theme_engine: Theme engine instance
            parent: Parent QObject
        """
        super().__init__(parent)
        
        self.theme_engine = theme_engine
        self.file_watcher = ThemeFileWatcher(self)
        
        # Reload configuration
        self.auto_reload_enabled = True
        self.reload_delay = 1000  # 1 second delay after file change
        self.max_reload_attempts = 3
        
        # File to theme mapping
        self.file_theme_mapping: Dict[str, str] = {}
        
        # Reload history
        self.reload_history: List[ReloadEvent] = []
        self.max_history_size = 100
        
        # Reload callbacks
        self.reload_callbacks: List[Callable[[str, bool], None]] = []
        
        # Delayed reload timer
        self.reload_timer = QTimer()
        self.reload_timer.setSingleShot(True)
        self.reload_timer.timeout.connect(self._execute_pending_reloads)
        
        self.pending_reloads: Set[str] = set()
        
        # Connect file watcher signals
        self.file_watcher.file_changed.connect(self._on_file_changed)
        self.file_watcher.file_created.connect(self._on_file_created)
        self.file_watcher.file_deleted.connect(self._on_file_deleted)
        
        logger.info("HotReloadManager initialized")
    
    def start_watching(self, theme_paths: List[Path]) -> None:
        """Start watching theme files and directories.
        
        Args:
            theme_paths: List of paths to watch (files or directories)
        """
        for path in theme_paths:
            if path.is_file():
                if self.file_watcher.watch_file(path):
                    # Try to determine theme name from file
                    theme_name = self._extract_theme_name_from_file(path)
                    if theme_name:
                        self.file_theme_mapping[str(path.resolve())] = theme_name
            elif path.is_dir():
                self.file_watcher.watch_directory(path, recursive=True)
                # Map existing theme files
                self._map_theme_files_in_directory(path)
        
        logger.info(f"Started watching {len(theme_paths)} theme paths")
    
    def stop_watching(self) -> None:
        """Stop watching all theme files."""
        self.file_watcher.clear_watches()
        self.file_theme_mapping.clear()
        self.pending_reloads.clear()
        logger.info("Stopped watching theme files")
    
    def _extract_theme_name_from_file(self, file_path: Path) -> Optional[str]:
        """Extract theme name from file path or content.
        
        Args:
            file_path: Path to theme file
            
        Returns:
            Theme name or None if not determinable
        """
        # Try filename first (without extension)
        if file_path.stem and file_path.stem != 'theme':
            return file_path.stem
        
        # Try to read theme name from file content
        try:
            if file_path.suffix in ['.yaml', '.yml']:
                import yaml
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                if isinstance(data, dict):
                    metadata = data.get('metadata', {})
                    if 'name' in metadata:
                        return metadata['name']
            
            elif file_path.suffix == '.json':
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    metadata = data.get('metadata', {})
                    if 'name' in metadata:
                        return metadata['name']
        
        except Exception as e:
            logger.debug(f"Could not extract theme name from {file_path}: {e}")
        
        return None
    
    def _map_theme_files_in_directory(self, directory: Path) -> None:
        """Map all theme files in directory to theme names.
        
        Args:
            directory: Directory to scan
        """
        theme_extensions = ['.yaml', '.yml', '.json', '.toml']
        
        for file_path in directory.rglob('*'):
            if file_path.is_file() and file_path.suffix in theme_extensions:
                theme_name = self._extract_theme_name_from_file(file_path)
                if theme_name:
                    self.file_theme_mapping[str(file_path.resolve())] = theme_name
    
    def _on_file_changed(self, file_path: str) -> None:
        """Handle file change event."""
        if not self.auto_reload_enabled:
            return
        
        theme_name = self.file_theme_mapping.get(file_path)
        if theme_name:
            self.pending_reloads.add(theme_name)
            self.reload_timer.start(self.reload_delay)
            logger.debug(f"Scheduled reload for theme '{theme_name}' (file: {file_path})")
    
    def _on_file_created(self, file_path: str) -> None:
        """Handle file creation event."""
        self.theme_file_detected.emit(file_path)
        
        # Try to determine theme name and add to mapping
        path = Path(file_path)
        theme_name = self._extract_theme_name_from_file(path)
        if theme_name:
            self.file_theme_mapping[file_path] = theme_name
            logger.info(f"New theme file detected: {file_path} -> {theme_name}")
            
            if self.auto_reload_enabled:
                self.pending_reloads.add(theme_name)
                self.reload_timer.start(self.reload_delay)
    
    def _on_file_deleted(self, file_path: str) -> None:
        """Handle file deletion event."""
        if file_path in self.file_theme_mapping:
            theme_name = self.file_theme_mapping.pop(file_path)
            logger.info(f"Theme file deleted: {file_path} -> {theme_name}")
    
    def _execute_pending_reloads(self) -> None:
        """Execute all pending theme reloads."""
        for theme_name in self.pending_reloads:
            self.reload_theme(theme_name, ReloadTrigger.FILE_MODIFIED)
        
        self.pending_reloads.clear()
    
    def reload_theme(
        self, 
        theme_name: str, 
        trigger: ReloadTrigger = ReloadTrigger.MANUAL,
        force: bool = False
    ) -> bool:
        """Reload a specific theme.
        
        Args:
            theme_name: Name of theme to reload
            trigger: What triggered the reload
            force: Whether to force reload even if disabled
            
        Returns:
            True if reload was successful
        """
        if not force and not self.auto_reload_enabled:
            logger.debug(f"Skipping reload of '{theme_name}' - auto reload disabled")
            return False
        
        start_time = time.time()
        
        try:
            self.reload_started.emit(theme_name)
            
            # Clear theme from cache to force reload
            self.theme_engine.clear_cache()
            
            # Attempt to reload theme
            for attempt in range(self.max_reload_attempts):
                try:
                    # Load theme to validate it
                    theme = self.theme_engine.load_theme(theme_name)
                    
                    # If currently active theme, apply the reload
                    current_theme = self.theme_engine.get_current_theme()
                    if current_theme and current_theme.name == theme_name:
                        self.theme_engine.apply_theme(theme)
                    
                    # Record successful reload
                    reload_time = (time.time() - start_time) * 1000  # Convert to ms
                    
                    reload_event = ReloadEvent(
                        timestamp=time.time(),
                        theme_name=theme_name,
                        trigger=trigger,
                        success=True,
                        reload_time_ms=reload_time,
                        additional_data={'attempts': attempt + 1}
                    )
                    
                    self._record_reload_event(reload_event)
                    
                    # Notify callbacks
                    for callback in self.reload_callbacks:
                        try:
                            callback(theme_name, True)
                        except Exception as e:
                            logger.error(f"Reload callback error: {e}")
                    
                    self.reload_completed.emit(theme_name, reload_time)
                    logger.info(f"Successfully reloaded theme '{theme_name}' in {reload_time:.1f}ms")
                    
                    return True
                    
                except Exception as e:
                    if attempt < self.max_reload_attempts - 1:
                        logger.warning(f"Reload attempt {attempt + 1} failed for '{theme_name}': {e}")
                        time.sleep(0.1)  # Brief delay before retry
                    else:
                        raise
            
        except Exception as e:
            error_message = str(e)
            
            # Record failed reload
            reload_event = ReloadEvent(
                timestamp=time.time(),
                theme_name=theme_name,
                trigger=trigger,
                success=False,
                error_message=error_message,
                reload_time_ms=(time.time() - start_time) * 1000
            )
            
            self._record_reload_event(reload_event)
            
            # Notify callbacks
            for callback in self.reload_callbacks:
                try:
                    callback(theme_name, False)
                except Exception as callback_error:
                    logger.error(f"Reload callback error: {callback_error}")
            
            self.reload_failed.emit(theme_name, error_message)
            logger.error(f"Failed to reload theme '{theme_name}': {error_message}")
            
            return False
    
    def _record_reload_event(self, event: ReloadEvent) -> None:
        """Record a reload event in history.
        
        Args:
            event: Reload event to record
        """
        self.reload_history.append(event)
        
        # Trim history if too large
        if len(self.reload_history) > self.max_history_size:
            self.reload_history.pop(0)
    
    def register_reload_callback(self, callback: Callable[[str, bool], None]) -> None:
        """Register callback for theme reload events.
        
        Args:
            callback: Function to call on reload (theme_name, success)
        """
        if callback not in self.reload_callbacks:
            self.reload_callbacks.append(callback)
    
    def unregister_reload_callback(self, callback: Callable[[str, bool], None]) -> None:
        """Unregister reload callback.
        
        Args:
            callback: Function to remove from callbacks
        """
        if callback in self.reload_callbacks:
            self.reload_callbacks.remove(callback)
    
    def get_reload_history(self, theme_name: Optional[str] = None) -> List[ReloadEvent]:
        """Get reload history.
        
        Args:
            theme_name: Filter by specific theme (None for all)
            
        Returns:
            List of reload events
        """
        if theme_name:
            return [event for event in self.reload_history if event.theme_name == theme_name]
        return self.reload_history.copy()
    
    def get_reload_statistics(self) -> Dict[str, Any]:
        """Get reload statistics.
        
        Returns:
            Statistics about theme reloads
        """
        if not self.reload_history:
            return {}
        
        successful_reloads = [e for e in self.reload_history if e.success]
        failed_reloads = [e for e in self.reload_history if not e.success]
        
        reload_times = [e.reload_time_ms for e in successful_reloads]
        
        return {
            'total_reloads': len(self.reload_history),
            'successful_reloads': len(successful_reloads),
            'failed_reloads': len(failed_reloads),
            'success_rate': len(successful_reloads) / len(self.reload_history),
            'avg_reload_time_ms': sum(reload_times) / len(reload_times) if reload_times else 0,
            'max_reload_time_ms': max(reload_times) if reload_times else 0,
            'min_reload_time_ms': min(reload_times) if reload_times else 0,
            'themes_reloaded': len(set(e.theme_name for e in self.reload_history)),
            'watched_files': len(self.file_theme_mapping),
        }
    
    def set_auto_reload(self, enabled: bool) -> None:
        """Enable or disable automatic theme reloading.
        
        Args:
            enabled: Whether to enable auto reload
        """
        self.auto_reload_enabled = enabled
        logger.info(f"Auto reload {'enabled' if enabled else 'disabled'}")
    
    def set_reload_delay(self, delay_ms: int) -> None:
        """Set delay before executing reload after file change.
        
        Args:
            delay_ms: Delay in milliseconds
        """
        self.reload_delay = max(100, delay_ms)  # Minimum 100ms
        logger.debug(f"Reload delay set to {self.reload_delay}ms")
    
    def clear_history(self) -> None:
        """Clear reload history."""
        self.reload_history.clear()
        logger.debug("Reload history cleared")


class HotReloadEngine:
    """High-level hot reload engine coordinator."""
    
    def __init__(self, theme_engine: ThemeEngine):
        """Initialize hot reload engine.
        
        Args:
            theme_engine: Theme engine instance
        """
        self.theme_engine = theme_engine
        self.reload_manager: Optional[HotReloadManager] = None
        self.development_mode = False
        
    def enable_development_mode(
        self, 
        theme_paths: List[Path],
        auto_reload: bool = True,
        reload_delay: int = 1000
    ) -> None:
        """Enable development mode with hot reloading.
        
        Args:
            theme_paths: Paths to watch for changes
            auto_reload: Whether to enable automatic reloading
            reload_delay: Delay before reload after file change
        """
        if self.reload_manager:
            self.disable_development_mode()
        
        # Create reload manager
        self.reload_manager = HotReloadManager(self.theme_engine)
        self.reload_manager.set_auto_reload(auto_reload)
        self.reload_manager.set_reload_delay(reload_delay)
        
        # Start watching theme paths
        self.reload_manager.start_watching(theme_paths)
        
        self.development_mode = True
        logger.info("Development mode enabled with hot reloading")
    
    def disable_development_mode(self) -> None:
        """Disable development mode and stop hot reloading."""
        if self.reload_manager:
            self.reload_manager.stop_watching()
            self.reload_manager = None
        
        self.development_mode = False
        logger.info("Development mode disabled")
    
    def is_development_mode(self) -> bool:
        """Check if development mode is enabled.
        
        Returns:
            True if development mode is enabled
        """
        return self.development_mode
    
    def reload_current_theme(self) -> bool:
        """Manually reload the currently active theme.
        
        Returns:
            True if reload was successful
        """
        if not self.reload_manager:
            logger.warning("Hot reload not available - development mode not enabled")
            return False
        
        current_theme = self.theme_engine.get_current_theme()
        if not current_theme:
            logger.warning("No active theme to reload")
            return False
        
        return self.reload_manager.reload_theme(
            current_theme.name, 
            ReloadTrigger.MANUAL, 
            force=True
        )
    
    def get_reload_manager(self) -> Optional[HotReloadManager]:
        """Get the reload manager instance.
        
        Returns:
            Reload manager or None if not in development mode
        """
        return self.reload_manager