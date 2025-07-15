"""Auto-save functionality with configurable intervals and persistence"""

import json
import hashlib
import time
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, asdict
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QSettings
from PyQt6.QtWidgets import QApplication


@dataclass
class AutoSaveEntry:
    """Represents an auto-save entry"""
    session_id: str
    element_id: str
    element_type: str
    content: str
    timestamp: float
    version: int
    hash: str
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return asdict(self)
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AutoSaveEntry':
        """Create from dictionary"""
        return cls(**data)


class AutoSaveConfig:
    """Configuration for auto-save functionality"""
    
    def __init__(self):
        self.enabled = True
        self.interval_seconds = 30  # Auto-save every 30 seconds
        self.max_versions = 10      # Keep last 10 versions
        self.save_on_focus_loss = True
        self.save_on_idle = True
        self.idle_timeout_seconds = 120  # Save after 2 minutes of inactivity
        self.compression_enabled = False
        self.encryption_enabled = False
        self.backup_directory = None  # Use default
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'enabled': self.enabled,
            'interval_seconds': self.interval_seconds,
            'max_versions': self.max_versions,
            'save_on_focus_loss': self.save_on_focus_loss,
            'save_on_idle': self.save_on_idle,
            'idle_timeout_seconds': self.idle_timeout_seconds,
            'compression_enabled': self.compression_enabled,
            'encryption_enabled': self.encryption_enabled,
            'backup_directory': self.backup_directory
        }
        
    def from_dict(self, data: Dict[str, Any]):
        """Load from dictionary"""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)


class AutoSaveStorage:
    """Storage backend for auto-save data"""
    
    def __init__(self, storage_dir: Optional[Path] = None):
        if storage_dir is None:
            storage_dir = Path.home() / ".torematrix" / "autosave"
        
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.index_file = self.storage_dir / "index.json"
        self._load_index()
        
    def _load_index(self):
        """Load the auto-save index"""
        try:
            if self.index_file.exists():
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    self.index = json.load(f)
            else:
                self.index = {
                    'sessions': {},
                    'elements': {},
                    'metadata': {
                        'created': time.time(),
                        'version': '1.0'
                    }
                }
        except Exception:
            self.index = {'sessions': {}, 'elements': {}, 'metadata': {}}
            
    def _save_index(self):
        """Save the auto-save index"""
        try:
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(self.index, f, indent=2, ensure_ascii=False)
        except Exception:
            pass  # Handle silently to avoid disrupting user experience
            
    def save_entry(self, entry: AutoSaveEntry) -> bool:
        """Save an auto-save entry
        
        Args:
            entry: Auto-save entry to save
            
        Returns:
            True if saved successfully
        """
        try:
            # Create file path
            filename = f"{entry.element_id}_{entry.version}.json"
            filepath = self.storage_dir / filename
            
            # Save entry data
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(entry.to_dict(), f, indent=2, ensure_ascii=False)
                
            # Update index
            session_data = self.index['sessions'].setdefault(entry.session_id, {
                'created': entry.timestamp,
                'elements': []
            })
            
            element_data = self.index['elements'].setdefault(entry.element_id, {
                'type': entry.element_type,
                'versions': [],
                'latest_version': 0
            })
            
            # Add version info
            version_info = {
                'version': entry.version,
                'timestamp': entry.timestamp,
                'hash': entry.hash,
                'filename': filename,
                'size': len(entry.content)
            }
            
            element_data['versions'].append(version_info)
            element_data['latest_version'] = entry.version
            
            if entry.element_id not in session_data['elements']:
                session_data['elements'].append(entry.element_id)
                
            # Cleanup old versions
            self._cleanup_old_versions(entry.element_id)
            
            self._save_index()
            return True
            
        except Exception:
            return False
            
    def load_entry(self, element_id: str, version: Optional[int] = None) -> Optional[AutoSaveEntry]:
        """Load an auto-save entry
        
        Args:
            element_id: Element ID to load
            version: Specific version to load (latest if None)
            
        Returns:
            Auto-save entry or None if not found
        """
        try:
            element_data = self.index['elements'].get(element_id)
            if not element_data:
                return None
                
            if version is None:
                version = element_data['latest_version']
                
            # Find version info
            version_info = None
            for v_info in element_data['versions']:
                if v_info['version'] == version:
                    version_info = v_info
                    break
                    
            if not version_info:
                return None
                
            # Load entry file
            filepath = self.storage_dir / version_info['filename']
            if not filepath.exists():
                return None
                
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            return AutoSaveEntry.from_dict(data)
            
        except Exception:
            return None
            
    def list_versions(self, element_id: str) -> List[Dict[str, Any]]:
        """List all versions for an element
        
        Args:
            element_id: Element ID
            
        Returns:
            List of version information
        """
        element_data = self.index['elements'].get(element_id, {})
        return element_data.get('versions', [])
        
    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all auto-save sessions
        
        Returns:
            List of session information
        """
        sessions = []
        for session_id, data in self.index['sessions'].items():
            sessions.append({
                'session_id': session_id,
                'created': data['created'],
                'element_count': len(data['elements'])
            })
        return sessions
        
    def delete_entry(self, element_id: str, version: Optional[int] = None) -> bool:
        """Delete an auto-save entry
        
        Args:
            element_id: Element ID
            version: Specific version to delete (all if None)
            
        Returns:
            True if deleted successfully
        """
        try:
            element_data = self.index['elements'].get(element_id)
            if not element_data:
                return False
                
            if version is None:
                # Delete all versions
                for v_info in element_data['versions']:
                    filepath = self.storage_dir / v_info['filename']
                    if filepath.exists():
                        filepath.unlink()
                        
                del self.index['elements'][element_id]
            else:
                # Delete specific version
                versions = element_data['versions']
                element_data['versions'] = [v for v in versions if v['version'] != version]
                
                # Delete file
                for v_info in versions:
                    if v_info['version'] == version:
                        filepath = self.storage_dir / v_info['filename']
                        if filepath.exists():
                            filepath.unlink()
                        break
                        
            self._save_index()
            return True
            
        except Exception:
            return False
            
    def _cleanup_old_versions(self, element_id: str, max_versions: int = 10):
        """Cleanup old versions for an element
        
        Args:
            element_id: Element ID
            max_versions: Maximum versions to keep
        """
        element_data = self.index['elements'].get(element_id)
        if not element_data:
            return
            
        versions = element_data['versions']
        if len(versions) <= max_versions:
            return
            
        # Sort by version number and keep latest
        versions.sort(key=lambda x: x['version'])
        versions_to_delete = versions[:-max_versions]
        
        # Delete old files
        for v_info in versions_to_delete:
            filepath = self.storage_dir / v_info['filename']
            if filepath.exists():
                filepath.unlink()
                
        # Update index
        element_data['versions'] = versions[-max_versions:]
        
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics
        
        Returns:
            Dictionary with storage statistics
        """
        total_files = 0
        total_size = 0
        
        for file_path in self.storage_dir.glob("*.json"):
            if file_path != self.index_file:
                total_files += 1
                total_size += file_path.stat().st_size
                
        return {
            'total_files': total_files,
            'total_size_bytes': total_size,
            'total_size_mb': total_size / 1024 / 1024,
            'total_elements': len(self.index['elements']),
            'total_sessions': len(self.index['sessions'])
        }


class AutoSaveManager(QObject):
    """Main auto-save manager
    
    Features:
    - Configurable auto-save intervals
    - Multiple storage backends
    - Version management
    - Recovery functionality
    - Performance monitoring
    """
    
    # Signals
    auto_saved = pyqtSignal(str, int)  # element_id, version
    save_failed = pyqtSignal(str, str)  # element_id, error_message
    recovery_available = pyqtSignal(str, list)  # element_id, versions
    config_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.config = AutoSaveConfig()
        self.storage = AutoSaveStorage()
        self.session_id = self._generate_session_id()
        
        # Active editors and their data
        self.active_editors: Dict[str, Dict[str, Any]] = {}
        self.version_counters: Dict[str, int] = {}
        
        # Timers
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self._perform_auto_save)
        
        self.idle_timer = QTimer()
        self.idle_timer.timeout.connect(self._on_idle_timeout)
        self.idle_timer.setSingleShot(True)
        
        # Load configuration
        self._load_config()
        
        # Start auto-save if enabled
        if self.config.enabled:
            self.start_auto_save()
            
    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
        timestamp = str(time.time())
        return hashlib.md5(timestamp.encode()).hexdigest()[:16]
        
    def _load_config(self):
        """Load configuration from settings"""
        settings = QSettings()
        config_data = settings.value("auto_save/config", {})
        
        if isinstance(config_data, dict):
            self.config.from_dict(config_data)
            
    def _save_config(self):
        """Save configuration to settings"""
        settings = QSettings()
        settings.setValue("auto_save/config", self.config.to_dict())
        
    def register_editor(self, element_id: str, element_type: str, 
                       content_getter: Callable[[], str],
                       metadata_getter: Optional[Callable[[], Dict[str, Any]]] = None):
        """Register an editor for auto-save
        
        Args:
            element_id: Unique element identifier
            element_type: Type of element (text, rich_text, etc.)
            content_getter: Function to get current content
            metadata_getter: Function to get metadata
        """
        self.active_editors[element_id] = {
            'element_type': element_type,
            'content_getter': content_getter,
            'metadata_getter': metadata_getter or (lambda: {}),
            'last_content': '',
            'last_save_time': 0,
            'is_dirty': False
        }
        
        # Initialize version counter
        if element_id not in self.version_counters:
            # Check existing versions in storage
            versions = self.storage.list_versions(element_id)
            if versions:
                self.version_counters[element_id] = max(v['version'] for v in versions) + 1
            else:
                self.version_counters[element_id] = 1
                
        # Check for recovery data
        self._check_recovery_data(element_id)
        
    def unregister_editor(self, element_id: str):
        """Unregister an editor from auto-save
        
        Args:
            element_id: Element identifier to unregister
        """
        if element_id in self.active_editors:
            # Perform final save if dirty
            editor_data = self.active_editors[element_id]
            if editor_data['is_dirty']:
                self._save_editor(element_id)
                
            del self.active_editors[element_id]
            
    def mark_dirty(self, element_id: str):
        """Mark an editor as having unsaved changes
        
        Args:
            element_id: Element identifier
        """
        if element_id in self.active_editors:
            self.active_editors[element_id]['is_dirty'] = True
            
            # Reset idle timer
            if self.config.save_on_idle:
                self.idle_timer.start(self.config.idle_timeout_seconds * 1000)
                
    def force_save(self, element_id: str) -> bool:
        """Force save an editor immediately
        
        Args:
            element_id: Element identifier
            
        Returns:
            True if saved successfully
        """
        return self._save_editor(element_id)
        
    def force_save_all(self) -> Dict[str, bool]:
        """Force save all registered editors
        
        Returns:
            Dictionary mapping element IDs to save success status
        """
        results = {}
        for element_id in self.active_editors:
            results[element_id] = self._save_editor(element_id)
        return results
        
    def _perform_auto_save(self):
        """Perform auto-save for all dirty editors"""
        if not self.config.enabled:
            return
            
        for element_id, editor_data in self.active_editors.items():
            if editor_data['is_dirty']:
                self._save_editor(element_id)
                
    def _save_editor(self, element_id: str) -> bool:
        """Save a specific editor
        
        Args:
            element_id: Element identifier
            
        Returns:
            True if saved successfully
        """
        if element_id not in self.active_editors:
            return False
            
        editor_data = self.active_editors[element_id]
        
        try:
            # Get current content
            current_content = editor_data['content_getter']()
            
            # Check if content actually changed
            if current_content == editor_data['last_content']:
                editor_data['is_dirty'] = False
                return True
                
            # Generate hash for content verification
            content_hash = hashlib.sha256(current_content.encode()).hexdigest()
            
            # Get metadata
            metadata = editor_data['metadata_getter']()
            
            # Create auto-save entry
            version = self.version_counters[element_id]
            entry = AutoSaveEntry(
                session_id=self.session_id,
                element_id=element_id,
                element_type=editor_data['element_type'],
                content=current_content,
                timestamp=time.time(),
                version=version,
                hash=content_hash,
                metadata=metadata
            )
            
            # Save to storage
            success = self.storage.save_entry(entry)
            
            if success:
                # Update tracking data
                editor_data['last_content'] = current_content
                editor_data['last_save_time'] = entry.timestamp
                editor_data['is_dirty'] = False
                self.version_counters[element_id] += 1
                
                self.auto_saved.emit(element_id, version)
                return True
            else:
                self.save_failed.emit(element_id, "Storage write failed")
                return False
                
        except Exception as e:
            self.save_failed.emit(element_id, str(e))
            return False
            
    def _on_idle_timeout(self):
        """Handle idle timeout"""
        if self.config.save_on_idle:
            self._perform_auto_save()
            
    def _check_recovery_data(self, element_id: str):
        """Check for recovery data for an element
        
        Args:
            element_id: Element identifier
        """
        versions = self.storage.list_versions(element_id)
        if versions:
            self.recovery_available.emit(element_id, versions)
            
    def start_auto_save(self):
        """Start auto-save timer"""
        if self.config.enabled and self.config.interval_seconds > 0:
            self.auto_save_timer.start(self.config.interval_seconds * 1000)
            
    def stop_auto_save(self):
        """Stop auto-save timer"""
        self.auto_save_timer.stop()
        self.idle_timer.stop()
        
    def set_config(self, config: AutoSaveConfig):
        """Set auto-save configuration
        
        Args:
            config: New configuration
        """
        self.config = config
        self._save_config()
        
        # Restart timer with new interval
        if self.config.enabled:
            self.start_auto_save()
        else:
            self.stop_auto_save()
            
        self.config_changed.emit()
        
    def get_recovery_versions(self, element_id: str) -> List[Dict[str, Any]]:
        """Get available recovery versions for an element
        
        Args:
            element_id: Element identifier
            
        Returns:
            List of version information
        """
        return self.storage.list_versions(element_id)
        
    def recover_version(self, element_id: str, version: int) -> Optional[str]:
        """Recover content from a specific version
        
        Args:
            element_id: Element identifier
            version: Version number to recover
            
        Returns:
            Recovered content or None if not found
        """
        entry = self.storage.load_entry(element_id, version)
        return entry.content if entry else None
        
    def delete_recovery_data(self, element_id: str) -> bool:
        """Delete all recovery data for an element
        
        Args:
            element_id: Element identifier
            
        Returns:
            True if deleted successfully
        """
        return self.storage.delete_entry(element_id)
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get auto-save statistics
        
        Returns:
            Dictionary with statistics
        """
        storage_stats = self.storage.get_storage_stats()
        
        return {
            'session_id': self.session_id,
            'active_editors': len(self.active_editors),
            'dirty_editors': sum(1 for data in self.active_editors.values() if data['is_dirty']),
            'auto_save_enabled': self.config.enabled,
            'save_interval': self.config.interval_seconds,
            'storage_stats': storage_stats
        }
        
    def cleanup_old_data(self, days_old: int = 30) -> int:
        """Cleanup old auto-save data
        
        Args:
            days_old: Delete data older than this many days
            
        Returns:
            Number of entries deleted
        """
        cutoff_time = time.time() - (days_old * 24 * 60 * 60)
        deleted_count = 0
        
        for element_id in list(self.storage.index['elements'].keys()):
            versions = self.storage.list_versions(element_id)
            
            for version_info in versions:
                if version_info['timestamp'] < cutoff_time:
                    if self.storage.delete_entry(element_id, version_info['version']):
                        deleted_count += 1
                        
        return deleted_count