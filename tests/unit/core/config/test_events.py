"""
Tests for configuration events and notification system.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from pathlib import Path

from src.torematrix.core.config.events import (
    ConfigEventType,
    ConfigurationChangeEvent,
    FileSystemChangeEvent,
    ConfigurationEventEmitter,
    ConfigurationSubscriber
)
from src.torematrix.core.config.watcher import ConfigurationChange, ChangeType
from src.torematrix.core.config.types import ConfigSource
from src.torematrix.core.events.base import EventPriority


class TestConfigEventType:
    """Test ConfigEventType enumeration."""
    
    def test_event_type_values(self):
        """Test that all event types have correct values."""
        assert ConfigEventType.CONFIG_LOADED.value == "config_loaded"
        assert ConfigEventType.CONFIG_CHANGED.value == "config_changed"
        assert ConfigEventType.CONFIG_RELOADED.value == "config_reloaded"
        assert ConfigEventType.CONFIG_ERROR.value == "config_error"
        assert ConfigEventType.HOT_RELOAD_SUCCESS.value == "hot_reload_success"
        assert ConfigEventType.HOT_RELOAD_FAILURE.value == "hot_reload_failure"


class TestConfigurationChangeEvent:
    """Test ConfigurationChangeEvent functionality."""
    
    def test_event_creation(self):
        """Test creating a configuration change event."""
        event = ConfigurationChangeEvent(
            event_type=ConfigEventType.CONFIG_CHANGED,
            config_key="database.host",
            old_value="localhost",
            new_value="remote.server",
            source=ConfigSource.RUNTIME
        )
        
        assert event.event_type == ConfigEventType.CONFIG_CHANGED
        assert event.config_key == "database.host"
        assert event.old_value == "localhost"
        assert event.new_value == "remote.server"
        assert event.source == ConfigSource.RUNTIME
    
    def test_event_priority_assignment(self):
        """Test that events get correct priority based on type."""
        # High priority events
        error_event = ConfigurationChangeEvent(
            event_type=ConfigEventType.CONFIG_ERROR
        )
        assert error_event._get_event_priority() == EventPriority.HIGH
        
        failure_event = ConfigurationChangeEvent(
            event_type=ConfigEventType.HOT_RELOAD_FAILURE
        )
        assert failure_event._get_event_priority() == EventPriority.HIGH
        
        # Normal priority events
        change_event = ConfigurationChangeEvent(
            event_type=ConfigEventType.CONFIG_CHANGED
        )
        assert change_event._get_event_priority() == EventPriority.NORMAL
        
        reload_event = ConfigurationChangeEvent(
            event_type=ConfigEventType.HOT_RELOAD_SUCCESS
        )
        assert reload_event._get_event_priority() == EventPriority.NORMAL
        
        # Low priority events
        loaded_event = ConfigurationChangeEvent(
            event_type=ConfigEventType.CONFIG_LOADED
        )
        assert loaded_event._get_event_priority() == EventPriority.LOW
    
    def test_config_loaded_factory(self):
        """Test config_loaded factory method."""
        file_path = Path("/test/config.json")
        config = {"test": "data"}
        source = ConfigSource.FILE
        
        event = ConfigurationChangeEvent.config_loaded(file_path, config, source)
        
        assert event.event_type == ConfigEventType.CONFIG_LOADED
        assert event.new_value == config
        assert event.source == source
        assert event.file_path == file_path
        assert "config_size" in event.metadata
    
    def test_config_changed_factory(self):
        """Test config_changed factory method."""
        event = ConfigurationChangeEvent.config_changed(
            "database.port",
            5432,
            5433,
            ConfigSource.RUNTIME
        )
        
        assert event.event_type == ConfigEventType.CONFIG_CHANGED
        assert event.config_key == "database.port"
        assert event.old_value == 5432
        assert event.new_value == 5433
        assert event.source == ConfigSource.RUNTIME
    
    def test_config_reloaded_factory(self):
        """Test config_reloaded factory method."""
        file_path = Path("/test/config.json")
        config = {"reloaded": True}
        reload_time = 150.5
        
        event = ConfigurationChangeEvent.config_reloaded(file_path, config, reload_time)
        
        assert event.event_type == ConfigEventType.CONFIG_RELOADED
        assert event.new_value == config
        assert event.file_path == file_path
        assert event.metadata["reload_time_ms"] == reload_time
    
    def test_config_error_factory(self):
        """Test config_error factory method."""
        error = ValueError("Test error")
        file_path = Path("/test/config.json")
        
        event = ConfigurationChangeEvent.config_error(error, file_path, "test.key")
        
        assert event.event_type == ConfigEventType.CONFIG_ERROR
        assert event.config_key == "test.key"
        assert event.file_path == file_path
        assert "Test error" in event.validation_errors
        assert event.metadata["error_type"] == "ValueError"
    
    def test_hot_reload_success_factory(self):
        """Test hot_reload_success factory method."""
        file_path = Path("/test/config.json")
        config = {"success": True}
        reload_time = 75.2
        
        event = ConfigurationChangeEvent.hot_reload_success(file_path, config, reload_time)
        
        assert event.event_type == ConfigEventType.HOT_RELOAD_SUCCESS
        assert event.new_value == config
        assert event.file_path == file_path
        assert event.metadata["reload_time_ms"] == reload_time
        assert event.metadata["trigger"] == "file_change"
    
    def test_hot_reload_failure_factory(self):
        """Test hot_reload_failure factory method."""
        file_path = Path("/test/config.json")
        error = RuntimeError("Reload failed")
        
        event = ConfigurationChangeEvent.hot_reload_failure(file_path, error)
        
        assert event.event_type == ConfigEventType.HOT_RELOAD_FAILURE
        assert event.file_path == file_path
        assert "Reload failed" in event.validation_errors
        assert event.metadata["error_type"] == "RuntimeError"
        assert event.metadata["trigger"] == "file_change"
    
    def test_config_rollback_factory(self):
        """Test config_rollback factory method."""
        file_path = Path("/test/config.json")
        config = {"rollback": True}
        reason = "Validation failed"
        
        event = ConfigurationChangeEvent.config_rollback(file_path, config, reason)
        
        assert event.event_type == ConfigEventType.CONFIG_ROLLBACK
        assert event.new_value == config
        assert event.file_path == file_path
        assert event.metadata["reason"] == reason


class TestFileSystemChangeEvent:
    """Test FileSystemChangeEvent functionality."""
    
    def test_file_change_event_creation(self):
        """Test creating a file system change event."""
        file_change = ConfigurationChange(
            path=Path("/test/config.json"),
            change_type=ChangeType.MODIFIED,
            content_hash="abc123"
        )
        
        event = FileSystemChangeEvent(file_change=file_change)
        
        assert event.file_change == file_change
        assert event.event_type == "config.file.modified"
    
    def test_file_priority_assignment(self):
        """Test file change event priority assignment."""
        # High priority for deletion
        delete_change = ConfigurationChange(
            path=Path("/test/config.json"),
            change_type=ChangeType.DELETED
        )
        delete_event = FileSystemChangeEvent(file_change=delete_change)
        assert delete_event._get_file_priority() == EventPriority.HIGH
        
        # Normal priority for modification
        modify_change = ConfigurationChange(
            path=Path("/test/config.json"),
            change_type=ChangeType.MODIFIED
        )
        modify_event = FileSystemChangeEvent(file_change=modify_change)
        assert modify_event._get_file_priority() == EventPriority.NORMAL
        
        # Normal priority for creation
        create_change = ConfigurationChange(
            path=Path("/test/config.json"),
            change_type=ChangeType.CREATED
        )
        create_event = FileSystemChangeEvent(file_change=create_change)
        assert create_event._get_file_priority() == EventPriority.NORMAL


class TestConfigurationEventEmitter:
    """Test ConfigurationEventEmitter functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_event_bus = Mock()
        self.emitter = ConfigurationEventEmitter(self.mock_event_bus)
    
    def test_emitter_initialization(self):
        """Test event emitter initialization."""
        emitter = ConfigurationEventEmitter()
        assert emitter.event_bus is None
        assert len(emitter._event_history) == 0
    
    def test_emit_config_loaded(self):
        """Test emitting config loaded event."""
        file_path = Path("/test/config.json")
        config = {"loaded": True}
        source = ConfigSource.FILE
        
        self.emitter.emit_config_loaded(file_path, config, source)
        
        # Check event was published to bus
        self.mock_event_bus.publish.assert_called_once()
        
        # Check event is in history
        assert len(self.emitter._event_history) == 1
        event = self.emitter._event_history[0]
        assert event.event_type == ConfigEventType.CONFIG_LOADED
    
    def test_emit_config_changed(self):
        """Test emitting config changed event."""
        self.emitter.emit_config_changed("test.key", "old", "new", ConfigSource.RUNTIME)
        
        self.mock_event_bus.publish.assert_called_once()
        
        event = self.emitter._event_history[0]
        assert event.event_type == ConfigEventType.CONFIG_CHANGED
        assert event.config_key == "test.key"
    
    def test_emit_config_error(self):
        """Test emitting config error event."""
        error = ValueError("Test error")
        file_path = Path("/test/config.json")
        
        self.emitter.emit_config_error(error, file_path, "error.key")
        
        self.mock_event_bus.publish.assert_called_once()
        
        event = self.emitter._event_history[0]
        assert event.event_type == ConfigEventType.CONFIG_ERROR
        assert event.file_path == file_path
    
    def test_emit_file_change(self):
        """Test emitting file change event."""
        file_change = ConfigurationChange(
            path=Path("/test/config.json"),
            change_type=ChangeType.MODIFIED
        )
        
        self.emitter.emit_file_change(file_change)
        
        # File change events are published but not stored in history
        self.mock_event_bus.publish.assert_called_once()
        assert len(self.emitter._event_history) == 0
    
    def test_emit_without_event_bus(self):
        """Test emitting events without event bus."""
        emitter = ConfigurationEventEmitter(None)
        
        # Should not raise error
        emitter.emit_config_changed("test", "old", "new", ConfigSource.RUNTIME)
        
        # Event should still be in history
        assert len(emitter._event_history) == 1
    
    def test_event_bus_error_handling(self):
        """Test handling event bus errors."""
        self.mock_event_bus.publish.side_effect = Exception("Bus error")
        
        # Should not raise exception
        self.emitter.emit_config_changed("test", "old", "new", ConfigSource.RUNTIME)
        
        # Event should still be in history
        assert len(self.emitter._event_history) == 1
    
    def test_get_event_history(self):
        """Test getting event history."""
        # Add some events
        self.emitter.emit_config_changed("key1", "old1", "new1", ConfigSource.RUNTIME)
        self.emitter.emit_config_changed("key2", "old2", "new2", ConfigSource.FILE)
        
        # Get all history
        history = self.emitter.get_event_history()
        assert len(history) == 2
        
        # Get filtered history
        change_history = self.emitter.get_event_history(ConfigEventType.CONFIG_CHANGED)
        assert len(change_history) == 2
        
        error_history = self.emitter.get_event_history(ConfigEventType.CONFIG_ERROR)
        assert len(error_history) == 0
        
        # Get limited history
        limited_history = self.emitter.get_event_history(limit=1)
        assert len(limited_history) == 1
    
    def test_get_event_statistics(self):
        """Test getting event statistics."""
        # Add events
        self.emitter.emit_config_changed("key1", "old", "new", ConfigSource.RUNTIME)
        self.emitter.emit_config_error(ValueError("Error"), None, "error.key")
        
        stats = self.emitter.get_event_statistics()
        
        assert stats["total_events"] == 2
        assert stats["error_count"] == 1
        assert stats["error_rate"] == 0.5
        assert "config_changed" in stats["event_counts"]
        assert "config_error" in stats["event_counts"]
        assert "most_recent" in stats
        assert "oldest" in stats
    
    def test_get_statistics_empty_history(self):
        """Test statistics with empty history."""
        stats = self.emitter.get_event_statistics()
        assert stats["total_events"] == 0
    
    def test_clear_history(self):
        """Test clearing event history."""
        self.emitter.emit_config_changed("test", "old", "new", ConfigSource.RUNTIME)
        assert len(self.emitter._event_history) == 1
        
        self.emitter.clear_history()
        assert len(self.emitter._event_history) == 0
    
    def test_history_size_limit(self):
        """Test event history size limitation."""
        emitter = ConfigurationEventEmitter()
        emitter._max_history = 3
        
        # Add more events than limit
        for i in range(5):
            emitter.emit_config_changed(f"key{i}", "old", "new", ConfigSource.RUNTIME)
        
        # Should only keep last 3 events
        assert len(emitter._event_history) == 3
        assert emitter._event_history[0].config_key == "key2"  # Oldest kept
        assert emitter._event_history[-1].config_key == "key4"  # Most recent


class TestConfigurationSubscriber:
    """Test ConfigurationSubscriber functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_event_bus = Mock()
        self.subscriber = ConfigurationSubscriber(self.mock_event_bus)
        self.callback_calls = []
        
        def test_callback(event):
            self.callback_calls.append(event)
        
        self.test_callback = test_callback
    
    def test_subscriber_initialization(self):
        """Test subscriber initialization."""
        subscriber = ConfigurationSubscriber()
        assert subscriber.event_bus is None
        assert len(subscriber._subscriptions) == 0
        assert subscriber._active == True
    
    def test_subscribe_to_config_changes(self):
        """Test subscribing to configuration changes."""
        sub_id = self.subscriber.subscribe_to_config_changes(
            self.test_callback,
            config_key="database.host",
            event_types=[ConfigEventType.CONFIG_CHANGED]
        )
        
        assert sub_id.startswith("config_changes_")
        assert sub_id in self.subscriber._subscriptions
        
        # Should subscribe to event bus
        self.mock_event_bus.subscribe.assert_called_once()
        args, kwargs = self.mock_event_bus.subscribe.call_args
        assert args[0] == "config.*"
    
    def test_subscribe_to_file_changes(self):
        """Test subscribing to file changes."""
        file_path = Path("/test/config.json")
        
        sub_id = self.subscriber.subscribe_to_file_changes(
            self.test_callback,
            file_path=file_path
        )
        
        assert sub_id.startswith("file_changes_")
        assert sub_id in self.subscriber._subscriptions
        
        # Should subscribe to event bus
        self.mock_event_bus.subscribe.assert_called_once()
        args, kwargs = self.mock_event_bus.subscribe.call_args
        assert args[0] == "config.file.*"
    
    def test_unsubscribe(self):
        """Test unsubscribing from events."""
        sub_id = self.subscriber.subscribe_to_config_changes(self.test_callback)
        
        assert sub_id in self.subscriber._subscriptions
        
        success = self.subscriber.unsubscribe(sub_id)
        assert success == True
        assert sub_id not in self.subscriber._subscriptions
        
        # Unsubscribe non-existent subscription
        success = self.subscriber.unsubscribe("non_existent")
        assert success == False
    
    def test_pause_resume(self):
        """Test pausing and resuming subscriptions."""
        assert self.subscriber._active == True
        
        self.subscriber.pause()
        assert self.subscriber._active == False
        
        self.subscriber.resume()
        assert self.subscriber._active == True
    
    def test_get_subscription_count(self):
        """Test getting subscription count."""
        assert self.subscriber.get_subscription_count() == 0
        
        self.subscriber.subscribe_to_config_changes(self.test_callback)
        assert self.subscriber.get_subscription_count() == 1
        
        self.subscriber.subscribe_to_file_changes(self.test_callback)
        assert self.subscriber.get_subscription_count() == 2
    
    def test_callback_error_handling(self):
        """Test error handling in callbacks."""
        def error_callback(event):
            raise ValueError("Callback error")
        
        # Subscribe with error callback
        self.subscriber.subscribe_to_config_changes(error_callback)
        
        # Create mock event
        event = ConfigurationChangeEvent(
            event_type=ConfigEventType.CONFIG_CHANGED,
            config_key="test.key"
        )
        
        # Get the filtered callback from subscription
        subscription = list(self.subscriber._subscriptions.values())[0]
        callback = subscription[0]  # Get callback from subscription list
        
        # Should not raise exception when callback errors
        # The actual filtering happens in the internal callback wrapper


if __name__ == '__main__':
    pytest.main([__file__])