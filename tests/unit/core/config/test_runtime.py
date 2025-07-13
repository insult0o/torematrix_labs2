"""
Tests for runtime configuration management with hot reload.
"""

import pytest
import asyncio
import tempfile
import json
import time
from pathlib import Path
from unittest.mock import Mock, patch, call
from datetime import datetime

from src.torematrix.core.config.runtime import (
    RuntimeConfigurationManager,
    ReloadAttempt,
    RuntimeConfiguration
)
from src.torematrix.core.config.types import ConfigSource
from src.torematrix.core.config.exceptions import ConfigurationError, ValidationError


class TestReloadAttempt:
    """Test ReloadAttempt data structure."""
    
    def test_reload_attempt_creation(self):
        """Test ReloadAttempt creation."""
        file_path = Path("/test/config.json")
        attempt = ReloadAttempt(
            timestamp=datetime.now(),
            file_path=file_path,
            success=True,
            duration_ms=150.5,
            config_size=1024
        )
        
        assert attempt.file_path == file_path
        assert attempt.success == True
        assert attempt.duration_ms == 150.5
        assert attempt.config_size == 1024
        assert attempt.error is None
        assert attempt.rollback_performed == False


class TestRuntimeConfiguration:
    """Test RuntimeConfiguration data structure."""
    
    def test_runtime_config_creation(self):
        """Test RuntimeConfiguration creation."""
        config = {"test": "data"}
        runtime_config = RuntimeConfiguration(config=config)
        
        assert runtime_config.config == config
        assert len(runtime_config.source_files) == 0
        assert runtime_config.last_reload is None
        assert runtime_config.reload_count == 0
        assert runtime_config.error_count == 0
        assert runtime_config.version == 0


class TestRuntimeConfigurationManager:
    """Test RuntimeConfigurationManager functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_event_bus = Mock()
        self.manager = RuntimeConfigurationManager(
            base_config={"app": {"name": "test"}},
            event_bus=self.mock_event_bus,
            enable_hot_reload=True,
            reload_debounce_ms=100,
            rollback_on_error=True
        )
    
    def teardown_method(self):
        """Clean up after tests."""
        self.manager.stop()
    
    def test_manager_initialization(self):
        """Test runtime manager initialization."""
        manager = RuntimeConfigurationManager(
            base_config={"test": "config"},
            enable_hot_reload=False,
            reload_debounce_ms=500,
            max_reload_attempts=5
        )
        
        assert manager.enable_hot_reload == False
        assert manager.reload_debounce_ms == 500
        assert manager.max_reload_attempts == 5
        assert manager.rollback_on_error == True
        assert "test" in manager._runtime_config.config
        
        manager.stop()
    
    def test_add_config_file(self):
        """Test adding a configuration file."""
        config_data = {"database": {"host": "localhost", "port": 5432}}
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(config_data, f)
            file_path = Path(f.name)
        
        try:
            self.manager.add_config_file(file_path, ConfigSource.FILE, watch=True)
            
            # Check file was added
            assert file_path in self.manager._runtime_config.source_files
            
            # Check configuration was merged
            assert "database" in self.manager._runtime_config.config
            assert self.manager.get("database.host") == "localhost"
            
            # Check version was incremented
            assert self.manager._runtime_config.version > 0
            
        finally:
            file_path.unlink()
    
    def test_add_config_file_invalid(self):
        """Test adding invalid configuration file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            f.write("invalid json {")
            file_path = Path(f.name)
        
        try:
            with pytest.raises(ConfigurationError):
                self.manager.add_config_file(file_path)
        finally:
            file_path.unlink()
    
    def test_remove_config_file(self):
        """Test removing a configuration file."""
        config_data = {"temp": "config"}
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(config_data, f)
            file_path = Path(f.name)
        
        try:
            self.manager.add_config_file(file_path)
            assert file_path in self.manager._runtime_config.source_files
            
            self.manager.remove_config_file(file_path)
            assert file_path not in self.manager._runtime_config.source_files
            
        finally:
            if file_path.exists():
                file_path.unlink()
    
    def test_get_set_configuration(self):
        """Test getting and setting configuration values."""
        # Test getting existing value
        assert self.manager.get("app.name") == "test"
        
        # Test getting with default
        assert self.manager.get("nonexistent.key", "default") == "default"
        
        # Test setting new value
        self.manager.set("app.version", "1.0.0")
        assert self.manager.get("app.version") == "1.0.0"
        
        # Check version was incremented
        assert self.manager._runtime_config.version > 0
    
    def test_get_runtime_info(self):
        """Test getting runtime information."""
        info = self.manager.get_runtime_info()
        
        assert "version" in info
        assert "source_files" in info
        assert "reload_count" in info
        assert "error_count" in info
        assert "config_size" in info
        assert "hot_reload_enabled" in info
        assert "performance" in info
        
        assert info["hot_reload_enabled"] == True
    
    def test_get_performance_stats(self):
        """Test getting performance statistics."""
        stats = self.manager.get_performance_stats()
        
        assert "total_reloads" in stats
        assert "successful_reloads" in stats
        assert "failed_reloads" in stats
        assert "success_rate" in stats
        assert "avg_reload_time_ms" in stats
        assert "total_reload_time_ms" in stats
    
    def test_reload_file_success(self):
        """Test successful file reload."""
        config_data = {"reload": {"test": True}}
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(config_data, f)
            file_path = Path(f.name)
        
        try:
            self.manager.add_config_file(file_path)
            
            # Modify the file
            new_config = {"reload": {"test": True, "updated": True}}
            with open(file_path, 'w') as f:
                json.dump(new_config, f)
            
            # Reload
            success = self.manager.reload_file(file_path)
            assert success == True
            
            # Check configuration was updated
            assert self.manager.get("reload.updated") == True
            
        finally:
            file_path.unlink()
    
    def test_reload_file_failure(self):
        """Test file reload failure and rollback."""
        config_data = {"valid": "config"}
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(config_data, f)
            file_path = Path(f.name)
        
        try:
            self.manager.add_config_file(file_path)
            original_value = self.manager.get("valid")
            
            # Write invalid JSON
            with open(file_path, 'w') as f:
                f.write("invalid json {")
            
            # Reload should fail
            success = self.manager.reload_file(file_path)
            assert success == False
            
            # Original configuration should remain
            assert self.manager.get("valid") == original_value
            
        finally:
            file_path.unlink()
    
    def test_reload_nonexistent_file(self):
        """Test reloading non-existent file."""
        file_path = Path("/nonexistent/config.json")
        success = self.manager.reload_file(file_path)
        assert success == False
    
    def test_reload_all(self):
        """Test reloading all configuration files."""
        config1 = {"file1": "data1"}
        config2 = {"file2": "data2"}
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f1:
            json.dump(config1, f1)
            file1_path = Path(f1.name)
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f2:
            json.dump(config2, f2)
            file2_path = Path(f2.name)
        
        try:
            self.manager.add_config_file(file1_path)
            self.manager.add_config_file(file2_path)
            
            # Modify both files
            new_config1 = {"file1": "updated1"}
            new_config2 = {"file2": "updated2"}
            
            with open(file1_path, 'w') as f:
                json.dump(new_config1, f)
            with open(file2_path, 'w') as f:
                json.dump(new_config2, f)
            
            # Reload all
            success = self.manager.reload_all()
            assert success == True
            
            # Check both were updated
            assert self.manager.get("file1") == "updated1"
            assert self.manager.get("file2") == "updated2"
            
        finally:
            file1_path.unlink()
            file2_path.unlink()
    
    @pytest.mark.asyncio
    async def test_reload_file_async(self):
        """Test asynchronous file reload."""
        config_data = {"async": "test"}
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(config_data, f)
            file_path = Path(f.name)
        
        try:
            self.manager.add_config_file(file_path)
            
            # Modify the file
            new_config = {"async": "test", "reloaded": True}
            with open(file_path, 'w') as f:
                json.dump(new_config, f)
            
            # Async reload
            success = await self.manager.reload_file_async(file_path)
            assert success == True
            
            # Check configuration was updated
            assert self.manager.get("reloaded") == True
            
        finally:
            file_path.unlink()
    
    @pytest.mark.asyncio
    async def test_reload_file_async_cancellation(self):
        """Test async reload cancellation."""
        config_data = {"cancel": "test"}
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(config_data, f)
            file_path = Path(f.name)
        
        try:
            self.manager.add_config_file(file_path)
            
            # Start first reload
            task1 = asyncio.create_task(self.manager.reload_file_async(file_path))
            
            # Start second reload (should cancel first)
            task2 = asyncio.create_task(self.manager.reload_file_async(file_path))
            
            # Wait for completion
            await task2
            
            # First task should be cancelled
            assert task1.cancelled()
            
        finally:
            file_path.unlink()
    
    def test_validate_configuration(self):
        """Test configuration validation."""
        # Should have no errors initially
        errors = self.manager.validate_configuration()
        assert len(errors) == 0
    
    def test_create_checkpoint(self):
        """Test creating configuration checkpoint."""
        checkpoint_id = self.manager.create_checkpoint()
        
        assert checkpoint_id.startswith("checkpoint_")
        assert hasattr(self.manager, '_checkpoints')
        assert checkpoint_id in self.manager._checkpoints
    
    def test_rollback_to_checkpoint(self):
        """Test rolling back to checkpoint."""
        # Create checkpoint
        checkpoint_id = self.manager.create_checkpoint()
        original_version = self.manager._runtime_config.version
        
        # Make changes
        self.manager.set("test.new", "value")
        assert self.manager.get("test.new") == "value"
        
        # Rollback
        success = self.manager.rollback_to_checkpoint(checkpoint_id)
        assert success == True
        
        # Should be back to original state
        assert self.manager._runtime_config.version == original_version
    
    def test_rollback_invalid_checkpoint(self):
        """Test rollback with invalid checkpoint."""
        success = self.manager.rollback_to_checkpoint("invalid_checkpoint")
        assert success == False
    
    def test_safe_update_context(self):
        """Test safe update context manager."""
        original_value = self.manager.get("app.name")
        
        # Successful update
        with self.manager.safe_update():
            self.manager.set("app.name", "updated")
            assert self.manager.get("app.name") == "updated"
        
        # Should still be updated after context
        assert self.manager.get("app.name") == "updated"
    
    def test_safe_update_with_error(self):
        """Test safe update with error and rollback."""
        original_value = self.manager.get("app.name")
        
        # Update with error
        with pytest.raises(ValueError):
            with self.manager.safe_update():
                self.manager.set("app.name", "temp")
                raise ValueError("Test error")
        
        # Should be rolled back
        assert self.manager.get("app.name") == original_value
    
    def test_get_reload_history(self):
        """Test getting reload history."""
        config_data = {"history": "test"}
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(config_data, f)
            file_path = Path(f.name)
        
        try:
            self.manager.add_config_file(file_path)
            
            # Trigger some reloads
            self.manager.reload_file(file_path)
            
            # Get history
            history = self.manager.get_reload_history()
            assert len(history) >= 1
            
            # Test with limit
            limited_history = self.manager.get_reload_history(limit=1)
            assert len(limited_history) <= 1
            
        finally:
            file_path.unlink()
    
    def test_hot_reload_integration(self):
        """Test hot reload integration with file changes."""
        config_data = {"hot": "reload"}
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(config_data, f)
            file_path = Path(f.name)
        
        try:
            self.manager.add_config_file(file_path, watch=True)
            
            # Mock file change
            from src.torematrix.core.config.watcher import ConfigurationChange, ChangeType
            change = ConfigurationChange(
                path=file_path,
                change_type=ChangeType.MODIFIED
            )
            
            # Trigger file change handler
            self.manager._handle_file_change(change)
            
            # Should create async reload task
            # Note: In real usage, this would be triggered by file system events
            
        finally:
            file_path.unlink()
    
    def test_performance_tracking(self):
        """Test performance metrics tracking."""
        config_data = {"perf": "test"}
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(config_data, f)
            file_path = Path(f.name)
        
        try:
            self.manager.add_config_file(file_path)
            
            # Perform reload
            self.manager.reload_file(file_path)
            
            # Check performance stats were updated
            stats = self.manager.get_performance_stats()
            assert stats["total_reloads"] > 0
            assert stats["successful_reloads"] > 0
            
        finally:
            file_path.unlink()
    
    def test_error_tracking(self):
        """Test error tracking in reloads."""
        config_data = {"error": "test"}
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(config_data, f)
            file_path = Path(f.name)
        
        try:
            self.manager.add_config_file(file_path)
            
            # Create invalid JSON
            with open(file_path, 'w') as f:
                f.write("invalid")
            
            # Attempt reload
            self.manager.reload_file(file_path)
            
            # Check error was tracked
            assert self.manager._runtime_config.error_count > 0
            stats = self.manager.get_performance_stats()
            assert stats["failed_reloads"] > 0
            
        finally:
            file_path.unlink()
    
    def test_callback_integration(self):
        """Test integration with watcher callbacks."""
        reload_successes = []
        reload_errors = []
        
        def success_callback(file_path, config):
            reload_successes.append((file_path, config))
        
        def error_callback(file_path, error):
            reload_errors.append((file_path, error))
        
        self.manager._watcher.add_reload_callback(success_callback)
        self.manager._watcher.add_error_callback(error_callback)
        
        # Test would need actual file changes to trigger callbacks
        # This tests the callback setup
        assert len(self.manager._watcher._reload_callbacks) > 0
        assert len(self.manager._watcher._error_callbacks) > 0


if __name__ == '__main__':
    pytest.main([__file__])