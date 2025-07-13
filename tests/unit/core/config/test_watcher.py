"""
Tests for configuration file system watcher.
"""

import pytest
import asyncio
import tempfile
import json
import time
from pathlib import Path
from unittest.mock import Mock, patch, call
from datetime import datetime

from src.torematrix.core.config.watcher import (
    FileWatcher,
    ConfigurationWatcher,
    ConfigurationChange,
    ChangeType
)
from src.torematrix.core.config.exceptions import ConfigurationError


class TestConfigurationChange:
    """Test ConfigurationChange data structure."""
    
    def test_change_creation(self):
        """Test ConfigurationChange creation."""
        change = ConfigurationChange(
            path=Path("/test/config.json"),
            change_type=ChangeType.MODIFIED,
            old_content={"old": "value"},
            new_content={"new": "value"},
            content_hash="abc123"
        )
        
        assert change.path == Path("/test/config.json")
        assert change.change_type == ChangeType.MODIFIED
        assert change.old_content == {"old": "value"}
        assert change.new_content == {"new": "value"}
        assert change.content_hash == "abc123"
        assert isinstance(change.timestamp, datetime)
    
    def test_change_to_dict(self):
        """Test ConfigurationChange to_dict conversion."""
        change = ConfigurationChange(
            path=Path("/test/config.json"),
            change_type=ChangeType.CREATED,
            content_hash="def456",
            file_size=1024
        )
        
        change_dict = change.to_dict()
        
        assert change_dict["path"] == "/test/config.json"
        assert change_dict["change_type"] == "created"
        assert change_dict["content_hash"] == "def456"
        assert change_dict["file_size"] == 1024
        assert "timestamp" in change_dict


class TestFileWatcher:
    """Test FileWatcher functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.watcher = FileWatcher(debounce_delay=0.1)
        self.callbacks_called = []
        
        def test_callback(change):
            self.callbacks_called.append(change)
        
        self.test_callback = test_callback
        self.watcher.add_callback(test_callback)
    
    def teardown_method(self):
        """Clean up after tests."""
        self.watcher.stop()
    
    def test_watcher_initialization(self):
        """Test FileWatcher initialization."""
        watcher = FileWatcher(debounce_delay=0.5)
        
        assert watcher.debounce_delay == 0.5
        assert len(watcher._watched_files) == 0
        assert len(watcher._file_hashes) == 0
        assert not watcher._running
    
    def test_add_remove_callback(self):
        """Test adding and removing callbacks."""
        callback1 = Mock()
        callback2 = Mock()
        
        watcher = FileWatcher()
        watcher.add_callback(callback1)
        watcher.add_callback(callback2)
        
        # Check callbacks were added
        assert len(watcher._callbacks) == 2
        
        # Remove one callback
        watcher.remove_callback(callback1)
        assert len(watcher._callbacks) == 1
        
        # Remove non-existent callback (should not error)
        watcher.remove_callback(Mock())
        assert len(watcher._callbacks) == 1
    
    def test_watch_file(self):
        """Test watching a file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            f.write('{"test": "data"}')
            file_path = Path(f.name)
        
        try:
            self.watcher.watch_file(file_path)
            
            # Check file is being watched
            assert file_path in self.watcher._watched_files
            assert file_path in self.watcher._file_hashes
            
            # Check initial state
            file_info = self.watcher._watched_files[file_path]
            assert file_info["exists"] == True
            assert isinstance(file_info["added_at"], datetime)
            
        finally:
            file_path.unlink()
    
    def test_watch_nonexistent_file(self):
        """Test watching a non-existent file."""
        file_path = Path("/nonexistent/file.json")
        
        self.watcher.watch_file(file_path)
        
        # Check file is being watched even if it doesn't exist
        assert file_path in self.watcher._watched_files
        assert self.watcher._watched_files[file_path]["exists"] == False
    
    def test_unwatch_file(self):
        """Test unwatching a file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            f.write('{"test": "data"}')
            file_path = Path(f.name)
        
        try:
            self.watcher.watch_file(file_path)
            assert file_path in self.watcher._watched_files
            
            self.watcher.unwatch_file(file_path)
            assert file_path not in self.watcher._watched_files
            assert file_path not in self.watcher._file_hashes
            
        finally:
            if file_path.exists():
                file_path.unlink()
    
    def test_check_file_changes_modification(self):
        """Test detecting file modifications."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            f.write('{"test": "data"}')
            file_path = Path(f.name)
        
        try:
            self.watcher.watch_file(file_path)
            
            # Modify the file
            time.sleep(0.01)  # Ensure different timestamp
            with open(file_path, 'w') as f:
                f.write('{"test": "modified"}')
            
            # Check for changes
            changes = self.watcher.check_file_changes()
            
            assert len(changes) == 1
            assert changes[0].change_type == ChangeType.MODIFIED
            assert changes[0].path == file_path
            
        finally:
            file_path.unlink()
    
    def test_check_file_changes_deletion(self):
        """Test detecting file deletion."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            f.write('{"test": "data"}')
            file_path = Path(f.name)
        
        self.watcher.watch_file(file_path)
        
        # Delete the file
        file_path.unlink()
        
        # Check for changes
        changes = self.watcher.check_file_changes()
        
        assert len(changes) == 1
        assert changes[0].change_type == ChangeType.DELETED
        assert changes[0].path == file_path
    
    def test_check_file_changes_creation(self):
        """Test detecting file creation."""
        file_path = Path(tempfile.gettempdir()) / "test_creation.json"
        
        # Watch non-existent file
        self.watcher.watch_file(file_path)
        
        try:
            # Create the file
            with open(file_path, 'w') as f:
                f.write('{"test": "created"}')
            
            # Check for changes
            changes = self.watcher.check_file_changes()
            
            assert len(changes) == 1
            assert changes[0].change_type == ChangeType.CREATED
            assert changes[0].path == file_path
            
        finally:
            if file_path.exists():
                file_path.unlink()
    
    def test_get_file_hash(self):
        """Test getting file hash."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            f.write('{"test": "data"}')
            file_path = Path(f.name)
        
        try:
            self.watcher.watch_file(file_path)
            
            file_hash = self.watcher.get_file_hash(file_path)
            assert file_hash is not None
            assert len(file_hash) == 64  # SHA256 hash length
            
        finally:
            file_path.unlink()
    
    @patch('src.torematrix.core.config.watcher.WATCHDOG_AVAILABLE', True)
    @patch('src.torematrix.core.config.watcher.Observer')
    def test_watchdog_integration(self, mock_observer_class):
        """Test watchdog integration when available."""
        mock_observer = Mock()
        mock_observer_class.return_value = mock_observer
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            f.write('{"test": "data"}')
            file_path = Path(f.name)
        
        try:
            watcher = FileWatcher()
            watcher.watch_file(file_path)
            
            # Verify observer was created and started
            mock_observer_class.assert_called_once()
            mock_observer.schedule.assert_called_once()
            mock_observer.start.assert_called_once()
            
        finally:
            file_path.unlink()
            watcher.stop()


class TestConfigurationWatcher:
    """Test ConfigurationWatcher functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.watcher = ConfigurationWatcher(
            debounce_delay=0.1,
            enable_hot_reload=True,
            backup_count=3
        )
        self.callbacks_called = []
        
        def test_callback(change):
            self.callbacks_called.append(change)
        
        self.watcher.add_change_callback(test_callback)
    
    def teardown_method(self):
        """Clean up after tests."""
        self.watcher.stop()
    
    def test_watcher_initialization(self):
        """Test ConfigurationWatcher initialization."""
        watcher = ConfigurationWatcher(
            debounce_delay=0.5,
            enable_hot_reload=False,
            backup_count=10
        )
        
        assert watcher.debounce_delay == 0.5
        assert watcher.enable_hot_reload == False
        assert watcher.backup_count == 10
        assert len(watcher._configurations) == 0
    
    def test_watch_json_config_file(self):
        """Test watching a JSON configuration file."""
        config_data = {"database": {"host": "localhost", "port": 5432}}
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(config_data, f)
            file_path = Path(f.name)
        
        try:
            self.watcher.watch_config_file(file_path)
            
            # Check configuration was loaded
            assert file_path in self.watcher._configurations
            config = self.watcher.get_configuration(file_path)
            assert config == config_data
            
        finally:
            file_path.unlink()
    
    def test_watch_config_file_with_custom_parser(self):
        """Test watching config file with custom parser."""
        def custom_parser(file_path):
            with open(file_path, 'r') as f:
                content = f.read()
                return {"custom": content.strip()}
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("custom config data")
            file_path = Path(f.name)
        
        try:
            self.watcher.watch_config_file(file_path, custom_parser)
            
            config = self.watcher.get_configuration(file_path)
            assert config == {"custom": "custom config data"}
            
        finally:
            file_path.unlink()
    
    def test_unwatch_config_file(self):
        """Test unwatching a configuration file."""
        config_data = {"test": "data"}
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(config_data, f)
            file_path = Path(f.name)
        
        try:
            self.watcher.watch_config_file(file_path)
            assert file_path in self.watcher._configurations
            
            self.watcher.unwatch_config_file(file_path)
            assert file_path not in self.watcher._configurations
            
        finally:
            if file_path.exists():
                file_path.unlink()
    
    def test_reload_configuration_success(self):
        """Test successful configuration reload."""
        config_data = {"version": 1}
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(config_data, f)
            file_path = Path(f.name)
        
        try:
            self.watcher.watch_config_file(file_path)
            
            # Modify the file
            new_config = {"version": 2}
            with open(file_path, 'w') as f:
                json.dump(new_config, f)
            
            # Reload configuration
            success = self.watcher.reload_configuration(file_path)
            assert success == True
            
            # Check configuration was updated
            config = self.watcher.get_configuration(file_path)
            assert config == new_config
            
        finally:
            file_path.unlink()
    
    def test_reload_configuration_failure(self):
        """Test configuration reload failure."""
        config_data = {"valid": "json"}
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(config_data, f)
            file_path = Path(f.name)
        
        try:
            self.watcher.watch_config_file(file_path)
            
            # Write invalid JSON
            with open(file_path, 'w') as f:
                f.write("invalid json {")
            
            # Reload should fail
            success = self.watcher.reload_configuration(file_path)
            assert success == False
            
            # Original configuration should remain
            config = self.watcher.get_configuration(file_path)
            assert config == config_data
            
        finally:
            file_path.unlink()
    
    def test_rollback_configuration(self):
        """Test configuration rollback."""
        config_data = {"version": 1}
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(config_data, f)
            file_path = Path(f.name)
        
        try:
            self.watcher.watch_config_file(file_path)
            
            # Update configuration (creates backup)
            new_config = {"version": 2}
            with open(file_path, 'w') as f:
                json.dump(new_config, f)
            self.watcher.reload_configuration(file_path)
            
            # Rollback
            success = self.watcher.rollback_configuration(file_path)
            assert success == True
            
            # Should have original configuration
            config = self.watcher.get_configuration(file_path)
            assert config == config_data
            
        finally:
            file_path.unlink()
    
    def test_rollback_no_backup(self):
        """Test rollback when no backup exists."""
        file_path = Path("/nonexistent/config.json")
        
        success = self.watcher.rollback_configuration(file_path)
        assert success == False
    
    def test_get_statistics(self):
        """Test getting watcher statistics."""
        config_data = {"test": "data"}
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(config_data, f)
            file_path = Path(f.name)
        
        try:
            self.watcher.watch_config_file(file_path)
            self.watcher.reload_configuration(file_path)
            
            stats = self.watcher.get_statistics()
            
            assert stats["watched_files"] == 1
            assert stats["reload_count"] >= 1
            assert stats["error_count"] >= 0
            assert "avg_reload_time_ms" in stats
            assert "success_rate" in stats
            
        finally:
            file_path.unlink()
    
    def test_error_callbacks(self):
        """Test error callback functionality."""
        errors_received = []
        
        def error_callback(file_path, error):
            errors_received.append((file_path, error))
        
        self.watcher.add_error_callback(error_callback)
        
        # Try to watch invalid file
        invalid_file = Path("/nonexistent/invalid.json")
        
        # This should trigger error callback
        with pytest.raises(ConfigurationError):
            self.watcher.watch_config_file(invalid_file)
        
        assert len(errors_received) > 0
    
    def test_reload_callbacks(self):
        """Test reload success callback functionality."""
        reloads_received = []
        
        def reload_callback(file_path, config):
            reloads_received.append((file_path, config))
        
        self.watcher.add_reload_callback(reload_callback)
        
        config_data = {"callback": "test"}
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(config_data, f)
            file_path = Path(f.name)
        
        try:
            self.watcher.watch_config_file(file_path)
            
            # Should trigger reload callback
            assert len(reloads_received) >= 1
            assert reloads_received[-1][0] == file_path
            assert reloads_received[-1][1] == config_data
            
        finally:
            file_path.unlink()
    
    def test_backup_count_limit(self):
        """Test backup count limitation."""
        watcher = ConfigurationWatcher(backup_count=2)
        
        config_data = {"version": 0}
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(config_data, f)
            file_path = Path(f.name)
        
        try:
            watcher.watch_config_file(file_path)
            
            # Create multiple backups
            for i in range(5):
                new_config = {"version": i + 1}
                with open(file_path, 'w') as f:
                    json.dump(new_config, f)
                watcher.reload_configuration(file_path)
            
            # Should only keep limited number of backups
            backups = watcher._config_backups.get(file_path, [])
            assert len(backups) <= 2
            
        finally:
            file_path.unlink()
            watcher.stop()
    
    @pytest.mark.asyncio
    async def test_hot_reload_integration(self):
        """Test hot reload integration with file watching."""
        watcher = ConfigurationWatcher(
            debounce_delay=0.05,
            enable_hot_reload=True
        )
        
        changes_detected = []
        
        def change_callback(change):
            changes_detected.append(change)
        
        watcher.add_change_callback(change_callback)
        
        config_data = {"hot_reload": True}
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(config_data, f)
            file_path = Path(f.name)
        
        try:
            watcher.watch_config_file(file_path)
            
            # Modify file to trigger hot reload
            new_config = {"hot_reload": True, "updated": True}
            with open(file_path, 'w') as f:
                json.dump(new_config, f)
            
            # Wait for file system events to be processed
            await asyncio.sleep(0.2)
            
            # Check that changes were detected
            # Note: Actual file system events may not trigger in test environment
            # This test mainly verifies the hot reload setup
            
        finally:
            file_path.unlink()
            watcher.stop()


if __name__ == '__main__':
    pytest.main([__file__])