"""
Tests for configuration runtime updates and notifications.
"""

import pytest
import tempfile
import json
import time
from pathlib import Path
from unittest.mock import Mock

from src.torematrix.core.config.runtime_updates import ConfigurationRuntimeManager, create_runtime_manager
from src.torematrix.core.config.exceptions import ConfigurationError


class TestConfigurationRuntimeManager:
    """Test runtime configuration manager functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.manager = ConfigurationRuntimeManager(
            enable_hot_reload=True,
            debounce_delay_ms=100,
            enable_audit_logging=True
        )
    
    def test_manager_initialization(self):
        """Test runtime manager initialization."""
        assert self.manager.enable_hot_reload == True
        assert self.manager.debounce_delay_ms == 100
        assert self.manager.enable_audit_logging == True
        assert len(self.manager._configurations) == 0
        assert len(self.manager._watchers) == 0
    
    def test_add_config_file_json(self):
        """Test adding JSON configuration file."""
        config_data = {"database": {"host": "localhost", "port": 5432}}
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(config_data, f)
            file_path = Path(f.name)
        
        try:
            self.manager.add_config_file(file_path, watch=True)
            
            # Check file was added
            assert file_path in self.manager._configurations
            assert self.manager._configurations[file_path] == config_data
            
            # Check watching was started
            assert file_path in self.manager._watchers
            
        finally:
            file_path.unlink()
    
    def test_add_config_file_non_json(self):
        """Test adding non-JSON configuration file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("test config content")
            file_path = Path(f.name)
        
        try:
            self.manager.add_config_file(file_path)
            
            # Should create default config structure
            assert file_path in self.manager._configurations
            config = self.manager._configurations[file_path]
            assert "file" in config
            assert "loaded_at" in config
            
        finally:
            file_path.unlink()
    
    def test_add_invalid_config_file(self):
        """Test adding invalid configuration file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            f.write("invalid json {")
            file_path = Path(f.name)
        
        try:
            with pytest.raises(ConfigurationError):
                self.manager.add_config_file(file_path)
        finally:
            file_path.unlink()
    
    def test_get_configuration_value(self):
        """Test getting configuration values by path."""
        config_data = {
            "database": {
                "host": "localhost",
                "port": 5432
            },
            "app": {
                "name": "test_app"
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(config_data, f)
            file_path = Path(f.name)
        
        try:
            self.manager.add_config_file(file_path)
            
            # Test nested path access
            assert self.manager.get("database.host") == "localhost"
            assert self.manager.get("database.port") == 5432
            assert self.manager.get("app.name") == "test_app"
            
            # Test default values
            assert self.manager.get("nonexistent.key", "default") == "default"
            assert self.manager.get("database.nonexistent", None) is None
            
        finally:
            file_path.unlink()
    
    def test_get_performance_tracking(self):
        """Test performance tracking for get operations."""
        # Add a config file
        config_data = {"test": "value"}
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(config_data, f)
            file_path = Path(f.name)
        
        try:
            self.manager.add_config_file(file_path)
            
            # Perform multiple reads
            for i in range(10):
                self.manager.get("test")
            
            stats = self.manager.get_performance_stats()
            assert stats["read_count"] == 10
            assert stats["avg_read_time_ms"] >= 0
            
        finally:
            file_path.unlink()
    
    def test_reload_file_success(self):
        """Test successful file reload."""
        config_data = {"version": 1, "feature": "enabled"}
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(config_data, f)
            file_path = Path(f.name)
        
        try:
            self.manager.add_config_file(file_path)
            
            # Verify initial config
            assert self.manager.get("version") == 1
            
            # Modify the file
            new_config = {"version": 2, "feature": "disabled"}
            with open(file_path, 'w') as f:
                json.dump(new_config, f)
            
            # Reload
            success = self.manager.reload_file(file_path)
            assert success == True
            
            # Verify updated config
            assert self.manager.get("version") == 2
            assert self.manager.get("feature") == "disabled"
            
            # Check performance metrics
            stats = self.manager.get_performance_stats()
            assert stats["reload_count"] == 1
            
        finally:
            file_path.unlink()
    
    def test_reload_file_failure_with_rollback(self):
        """Test file reload failure with automatic rollback."""
        config_data = {"valid": "config"}
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(config_data, f)
            file_path = Path(f.name)
        
        try:
            self.manager.add_config_file(file_path)
            
            # Verify initial config
            assert self.manager.get("valid") == "config"
            
            # Write invalid JSON
            with open(file_path, 'w') as f:
                f.write("invalid json {")
            
            # Reload should fail and rollback
            success = self.manager.reload_file(file_path)
            assert success == False
            
            # Original config should be preserved
            assert self.manager.get("valid") == "config"
            
            # Error count should be incremented
            stats = self.manager.get_performance_stats()
            assert stats["error_count"] > 0
            
        finally:
            file_path.unlink()
    
    def test_reload_nonexistent_file(self):
        """Test reloading non-existent file."""
        file_path = Path("/nonexistent/config.json")
        success = self.manager.reload_file(file_path)
        assert success == False
    
    def test_event_subscription(self):
        """Test event subscription and notification."""
        events_received = []
        
        def event_handler(event_type: str, event_data: dict):
            events_received.append((event_type, event_data))
        
        self.manager.subscribe_to_events(event_handler)
        
        # Add config file (should trigger event)
        config_data = {"test": "event"}
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(config_data, f)
            file_path = Path(f.name)
        
        try:
            self.manager.add_config_file(file_path)
            
            # Should have received config_loaded event
            assert len(events_received) == 1
            event_type, event_data = events_received[0]
            assert event_type == "config_loaded"
            assert "file_path" in event_data
            assert "config_size" in event_data
            
        finally:
            file_path.unlink()
    
    def test_hot_reload_events(self):
        """Test hot reload success and failure events."""
        events_received = []
        
        def event_handler(event_type: str, event_data: dict):
            events_received.append((event_type, event_data))
        
        self.manager.subscribe_to_events(event_handler)
        
        config_data = {"reload": "test"}
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(config_data, f)
            file_path = Path(f.name)
        
        try:
            self.manager.add_config_file(file_path)
            events_received.clear()  # Clear initial load event
            
            # Successful reload
            new_config = {"reload": "success"}
            with open(file_path, 'w') as f:
                json.dump(new_config, f)
            
            self.manager.reload_file(file_path)
            
            # Should have hot_reload_success event
            success_events = [e for e in events_received if e[0] == "hot_reload_success"]
            assert len(success_events) == 1
            
            # Failed reload
            with open(file_path, 'w') as f:
                f.write("invalid")
            
            self.manager.reload_file(file_path)
            
            # Should have hot_reload_failure event
            failure_events = [e for e in events_received if e[0] == "hot_reload_failure"]
            assert len(failure_events) == 1
            
            failure_event = failure_events[0][1]
            assert "error" in failure_event
            assert failure_event["rollback_performed"] == True
            
        finally:
            file_path.unlink()
    
    def test_event_callback_error_handling(self):
        """Test error handling in event callbacks."""
        def failing_callback(event_type: str, event_data: dict):
            raise ValueError("Callback error")
        
        def working_callback(event_type: str, event_data: dict):
            working_callback.called = True
        
        working_callback.called = False
        
        self.manager.subscribe_to_events(failing_callback)
        self.manager.subscribe_to_events(working_callback)
        
        # Trigger event - should not fail despite callback error
        self.manager._notify_event("test_event", {"test": "data"})
        
        # Working callback should still be called
        assert working_callback.called == True
    
    def test_get_performance_stats(self):
        """Test getting performance statistics."""
        config_data = {"stats": "test"}
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(config_data, f)
            file_path = Path(f.name)
        
        try:
            self.manager.add_config_file(file_path, watch=True)
            
            # Perform some operations
            self.manager.get("stats")
            self.manager.reload_file(file_path)
            
            stats = self.manager.get_performance_stats()
            
            # Verify stats structure
            assert "read_count" in stats
            assert "reload_count" in stats
            assert "error_count" in stats
            assert "avg_read_time_ms" in stats
            assert "avg_reload_time_ms" in stats
            assert "watched_files" in stats
            assert "total_configs" in stats
            assert "uptime_seconds" in stats
            
            # Verify some values
            assert stats["read_count"] >= 1
            assert stats["reload_count"] >= 1
            assert stats["watched_files"] == 1
            assert stats["total_configs"] == 1
            
        finally:
            file_path.unlink()
    
    def test_thread_safety(self):
        """Test thread safety of configuration operations."""
        import threading
        
        config_data = {"thread": "test"}
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(config_data, f)
            file_path = Path(f.name)
        
        try:
            self.manager.add_config_file(file_path)
            
            # Test concurrent reads
            results = []
            errors = []
            
            def read_config():
                try:
                    for i in range(50):
                        value = self.manager.get("thread")
                        results.append(value)
                except Exception as e:
                    errors.append(e)
            
            # Start multiple threads
            threads = []
            for _ in range(5):
                thread = threading.Thread(target=read_config)
                threads.append(thread)
                thread.start()
            
            # Wait for completion
            for thread in threads:
                thread.join()
            
            # Verify no errors and consistent results
            assert len(errors) == 0
            assert len(results) == 250  # 5 threads * 50 reads
            assert all(r == "test" for r in results)
            
        finally:
            file_path.unlink()


class TestRuntimeManagerFactory:
    """Test factory function for creating runtime managers."""
    
    def test_create_runtime_manager_defaults(self):
        """Test creating runtime manager with defaults."""
        manager = create_runtime_manager()
        
        assert isinstance(manager, ConfigurationRuntimeManager)
        assert manager.enable_hot_reload == True
        assert manager.debounce_delay_ms == 500
        assert manager.enable_audit_logging == True
    
    def test_create_runtime_manager_custom(self):
        """Test creating runtime manager with custom settings."""
        manager = create_runtime_manager(
            enable_hot_reload=False,
            debounce_delay_ms=1000,
            enable_audit_logging=False
        )
        
        assert manager.enable_hot_reload == False
        assert manager.debounce_delay_ms == 1000
        assert manager.enable_audit_logging == False


class TestPerformanceTargets:
    """Test performance targets for configuration runtime system."""
    
    def setup_method(self):
        """Set up performance test environment."""
        self.manager = ConfigurationRuntimeManager()
        
        # Add test configuration
        config_data = {
            "database": {"host": "localhost", "port": 5432},
            "cache": {"enabled": True, "ttl": 3600},
            "app": {"name": "test", "version": "1.0"}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(config_data, f)
            self.config_file = Path(f.name)
        
        self.manager.add_config_file(self.config_file)
    
    def teardown_method(self):
        """Clean up test environment."""
        if self.config_file.exists():
            self.config_file.unlink()
    
    def test_read_performance_target(self):
        """Test configuration read performance (<1ms per read)."""
        # Warm up
        for _ in range(100):
            self.manager.get("database.host")
        
        # Measure performance
        start_time = time.time()
        for _ in range(1000):
            self.manager.get("database.host")
        duration = time.time() - start_time
        
        avg_per_read_ms = (duration * 1000) / 1000
        
        print(f"Average read time: {avg_per_read_ms:.3f}ms")
        
        # Target: <1ms per read (should be much faster in practice)
        assert avg_per_read_ms < 1.0, f"Read time {avg_per_read_ms:.3f}ms exceeds 1ms target"
    
    def test_reload_performance_target(self):
        """Test configuration reload performance (<100ms)."""
        # Perform reload and measure time
        start_time = time.time()
        success = self.manager.reload_file(self.config_file)
        duration = (time.time() - start_time) * 1000  # Convert to ms
        
        print(f"Reload time: {duration:.1f}ms")
        
        assert success == True
        # Target: <100ms for reload
        assert duration < 100.0, f"Reload time {duration:.1f}ms exceeds 100ms target"
    
    def test_memory_efficiency(self):
        """Test memory efficiency with multiple configurations."""
        import sys
        
        # Measure initial memory
        initial_size = sys.getsizeof(self.manager._configurations)
        
        # Add multiple configurations
        configs = []
        for i in range(10):
            config_data = {f"config_{i}": {"value": i, "enabled": True}}
            
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
                json.dump(config_data, f)
                config_file = Path(f.name)
                configs.append(config_file)
            
            self.manager.add_config_file(config_file)
        
        # Measure final memory
        final_size = sys.getsizeof(self.manager._configurations)
        memory_growth = final_size - initial_size
        
        print(f"Memory growth for 10 configs: {memory_growth} bytes")
        
        # Clean up
        for config_file in configs:
            config_file.unlink()
        
        # Memory growth should be reasonable
        assert memory_growth < 10000, f"Memory growth {memory_growth} bytes too high"


if __name__ == '__main__':
    pytest.main([__file__])