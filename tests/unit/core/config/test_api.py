"""
Tests for runtime configuration API with path-based access.
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path
from typing import Dict, Any

from src.torematrix.core.config.api import (
    ConfigurationAPI,
    ConfigQuery,
    QueryOperator,
    ConfigSubscription,
    TypedConfigurationAPI
)
from src.torematrix.core.config.runtime import RuntimeConfigurationManager
from src.torematrix.core.config.types import ConfigSource
from src.torematrix.core.config.exceptions import ConfigurationAccessError


class TestConfigQuery:
    """Test ConfigQuery functionality."""
    
    def test_query_creation(self):
        """Test creating a configuration query."""
        query = ConfigQuery(
            path="database.*",
            operator=QueryOperator.EQUALS,
            value="localhost",
            case_sensitive=True
        )
        
        assert query.path == "database.*"
        assert query.operator == QueryOperator.EQUALS
        assert query.value == "localhost"
        assert query.case_sensitive == True
    
    def test_query_equals(self):
        """Test equals operator."""
        query = ConfigQuery("test", QueryOperator.EQUALS, "value")
        
        assert query.matches("value") == True
        assert query.matches("different") == False
        assert query.matches(None) == False
    
    def test_query_not_equals(self):
        """Test not equals operator."""
        query = ConfigQuery("test", QueryOperator.NOT_EQUALS, "value")
        
        assert query.matches("different") == True
        assert query.matches("value") == False
        assert query.matches(None) == False
    
    def test_query_exists(self):
        """Test exists operator."""
        query = ConfigQuery("test", QueryOperator.EXISTS)
        
        assert query.matches("any_value") == True
        assert query.matches(0) == True
        assert query.matches(False) == True
        assert query.matches(None) == False
    
    def test_query_type_is(self):
        """Test type_is operator."""
        query = ConfigQuery("test", QueryOperator.TYPE_IS, "str")
        
        assert query.matches("string") == True
        assert query.matches(123) == False
        assert query.matches(None) == False
    
    def test_query_numeric_operators(self):
        """Test numeric comparison operators."""
        gt_query = ConfigQuery("test", QueryOperator.GREATER_THAN, 10)
        assert gt_query.matches(15) == True
        assert gt_query.matches(5) == False
        
        lt_query = ConfigQuery("test", QueryOperator.LESS_THAN, 10)
        assert lt_query.matches(5) == True
        assert lt_query.matches(15) == False
        
        gte_query = ConfigQuery("test", QueryOperator.GREATER_EQUAL, 10)
        assert gte_query.matches(10) == True
        assert gte_query.matches(15) == True
        assert gte_query.matches(5) == False
        
        lte_query = ConfigQuery("test", QueryOperator.LESS_EQUAL, 10)
        assert lte_query.matches(10) == True
        assert lte_query.matches(5) == True
        assert lte_query.matches(15) == False
    
    def test_query_in_operators(self):
        """Test in/not_in operators."""
        in_query = ConfigQuery("test", QueryOperator.IN, ["a", "b", "c"])
        assert in_query.matches("a") == True
        assert in_query.matches("d") == False
        
        not_in_query = ConfigQuery("test", QueryOperator.NOT_IN, ["a", "b", "c"])
        assert not_in_query.matches("d") == True
        assert not_in_query.matches("a") == False
    
    def test_query_string_operators(self):
        """Test string-specific operators."""
        contains_query = ConfigQuery("test", QueryOperator.CONTAINS, "sub")
        assert contains_query.matches("substring") == True
        assert contains_query.matches("different") == False
        
        starts_query = ConfigQuery("test", QueryOperator.STARTS_WITH, "pre")
        assert starts_query.matches("prefix") == True
        assert starts_query.matches("suffix") == False
        
        ends_query = ConfigQuery("test", QueryOperator.ENDS_WITH, "fix")
        assert ends_query.matches("suffix") == True
        assert ends_query.matches("prefix") == False
    
    def test_query_case_sensitivity(self):
        """Test case sensitivity in string operations."""
        case_sensitive = ConfigQuery("test", QueryOperator.CONTAINS, "SUB", case_sensitive=True)
        case_insensitive = ConfigQuery("test", QueryOperator.CONTAINS, "SUB", case_sensitive=False)
        
        assert case_sensitive.matches("substring") == False
        assert case_insensitive.matches("substring") == True
    
    def test_query_regex(self):
        """Test regex operator."""
        regex_query = ConfigQuery("test", QueryOperator.REGEX, r"\d+")
        
        assert regex_query.matches("123") == True
        assert regex_query.matches("abc") == False
        
        # Test case insensitive regex
        regex_case_query = ConfigQuery("test", QueryOperator.REGEX, r"[A-Z]+", case_sensitive=False)
        assert regex_case_query.matches("abc") == True


class TestConfigSubscription:
    """Test ConfigSubscription data structure."""
    
    def test_subscription_creation(self):
        """Test creating a configuration subscription."""
        callback = Mock()
        query = ConfigQuery("test", QueryOperator.EQUALS, "value")
        
        subscription = ConfigSubscription(
            id="sub_1",
            path_pattern="database.*",
            callback=callback,
            query=query
        )
        
        assert subscription.id == "sub_1"
        assert subscription.path_pattern == "database.*"
        assert subscription.callback == callback
        assert subscription.query == query
        assert subscription.active == True
        assert subscription.trigger_count == 0


class TestConfigurationAPI:
    """Test ConfigurationAPI functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_runtime_manager = Mock(spec=RuntimeConfigurationManager)
        self.mock_runtime_manager._runtime_config = Mock()
        self.mock_runtime_manager._runtime_config.config = {
            "database": {
                "host": "localhost",
                "port": 5432,
                "ssl": True
            },
            "cache": {
                "enabled": True,
                "ttl": 3600
            },
            "app": {
                "name": "test_app",
                "version": "1.0.0"
            }
        }
        
        # Mock event emitter
        self.mock_runtime_manager._event_emitter = Mock()
        self.mock_runtime_manager._event_emitter.add_change_callback = Mock()
        
        self.api = ConfigurationAPI(self.mock_runtime_manager)
    
    def test_api_initialization(self):
        """Test ConfigurationAPI initialization."""
        api = ConfigurationAPI(self.mock_runtime_manager)
        
        assert api._runtime_manager == self.mock_runtime_manager
        assert len(api._subscriptions) == 0
        assert api._subscription_counter == 0
        assert api._cache_valid == True
    
    def test_get_configuration_value(self):
        """Test getting configuration values."""
        self.mock_runtime_manager.get.return_value = "localhost"
        
        value = self.api.get("database.host")
        assert value == "localhost"
        
        self.mock_runtime_manager.get.assert_called_with("database.host", None)
    
    def test_get_with_default(self):
        """Test getting configuration with default value."""
        self.mock_runtime_manager.get.return_value = "default_value"
        
        value = self.api.get("nonexistent.key", "default_value")
        assert value == "default_value"
    
    def test_get_with_type_hint(self):
        """Test getting configuration with type validation."""
        self.mock_runtime_manager.get.return_value = "localhost"
        
        # Valid type
        value = self.api.get("database.host", type_hint=str)
        assert value == "localhost"
        
        # Invalid type
        self.mock_runtime_manager.get.return_value = 123
        with pytest.raises(ConfigurationAccessError):
            self.api.get("database.port", type_hint=str)
    
    def test_set_configuration_value(self):
        """Test setting configuration values."""
        self.api.set("database.host", "remote.server")
        
        self.mock_runtime_manager.set.assert_called_with(
            "database.host", "remote.server", ConfigSource.RUNTIME
        )
    
    def test_exists(self):
        """Test checking if configuration path exists."""
        # Mock return values for exists check
        def mock_get(path, default):
            if path == "database.host":
                return "localhost"
            return default
        
        self.mock_runtime_manager.get.side_effect = mock_get
        
        assert self.api.exists("database.host") == True
        assert self.api.exists("nonexistent.key") == False
    
    def test_delete(self):
        """Test deleting configuration values."""
        # Mock exists
        def mock_get(path, default):
            if path == "test.key":
                return "value"
            return default
        
        self.mock_runtime_manager.get.side_effect = mock_get
        
        success = self.api.delete("test.key")
        assert success == True
        
        # Should call set with None
        self.mock_runtime_manager.set.assert_called_with("test.key", None)
    
    def test_get_paths(self):
        """Test getting configuration paths."""
        # Build path cache
        self.api._path_cache = {
            "database.host": "localhost",
            "database.port": 5432,
            "cache.enabled": True,
            "app.name": "test"
        }
        self.api._cache_valid = True
        
        # Get all paths
        all_paths = self.api.get_paths()
        assert len(all_paths) == 4
        assert "database.host" in all_paths
        
        # Get filtered paths
        db_paths = self.api.get_paths("database.*")
        assert len(db_paths) == 2
        assert "database.host" in db_paths
        assert "database.port" in db_paths
    
    def test_query_configuration(self):
        """Test querying configuration values."""
        # Setup path cache
        self.api._path_cache = {
            "database.host": "localhost",
            "database.port": 5432,
            "cache.enabled": True,
            "cache.ttl": 3600
        }
        self.api._cache_valid = True
        
        # Query for localhost values
        query = ConfigQuery("database.*", QueryOperator.EQUALS, "localhost")
        results = self.api.query(query)
        
        assert "database.host" in results
        assert results["database.host"] == "localhost"
        assert "database.port" not in results
    
    def test_query_multiple(self):
        """Test querying with multiple queries."""
        self.api._path_cache = {
            "database.host": "localhost",
            "database.port": 5432,
            "cache.enabled": True
        }
        self.api._cache_valid = True
        
        queries = [
            ConfigQuery("database.*", QueryOperator.EQUALS, "localhost"),
            ConfigQuery("cache.*", QueryOperator.EQUALS, True)
        ]
        
        results = self.api.query(queries)
        assert "database.host" in results
        assert "cache.enabled" in results
    
    def test_get_section(self):
        """Test getting configuration section."""
        self.api._path_cache = {
            "database.host": "localhost",
            "database.port": 5432,
            "database.ssl": True,
            "cache.enabled": True
        }
        self.api._cache_valid = True
        
        section = self.api.get_section("database")
        
        assert "host" in section
        assert "port" in section
        assert "ssl" in section
        assert section["host"] == "localhost"
        assert "enabled" not in section  # Not in database section
    
    def test_get_typed(self):
        """Test getting typed configuration values."""
        self.mock_runtime_manager.get.return_value = "5432"
        
        # Successful conversion
        port = self.api.get_typed("database.port", int)
        assert port == 5432
        assert isinstance(port, int)
        
        # Failed conversion
        self.mock_runtime_manager.get.return_value = "invalid"
        with pytest.raises(ConfigurationAccessError):
            self.api.get_typed("database.port", int)
    
    def test_get_typed_boolean_conversion(self):
        """Test boolean conversion in get_typed."""
        test_cases = [
            ("true", True),
            ("1", True),
            ("yes", True),
            ("on", True),
            ("false", False),
            ("0", False),
            ("no", False),
            ("off", False)
        ]
        
        for string_value, expected_bool in test_cases:
            self.mock_runtime_manager.get.return_value = string_value
            result = self.api.get_typed("test.bool", bool)
            assert result == expected_bool
    
    def test_subscribe(self):
        """Test subscribing to configuration changes."""
        callback = Mock()
        
        sub_id = self.api.subscribe("database.*", callback)
        
        assert sub_id.startswith("sub_")
        assert sub_id in self.api._subscriptions
        
        subscription = self.api._subscriptions[sub_id]
        assert subscription.path_pattern == "database.*"
        assert subscription.callback == callback
    
    def test_subscribe_with_query(self):
        """Test subscribing with query filter."""
        callback = Mock()
        query = ConfigQuery("database.*", QueryOperator.EQUALS, "localhost")
        
        sub_id = self.api.subscribe("database.*", callback, query)
        
        subscription = self.api._subscriptions[sub_id]
        assert subscription.query == query
    
    def test_unsubscribe(self):
        """Test unsubscribing from configuration changes."""
        callback = Mock()
        sub_id = self.api.subscribe("database.*", callback)
        
        assert sub_id in self.api._subscriptions
        
        success = self.api.unsubscribe(sub_id)
        assert success == True
        assert sub_id not in self.api._subscriptions
        
        # Unsubscribe non-existent
        success = self.api.unsubscribe("invalid_id")
        assert success == False
    
    def test_pause_resume_subscription(self):
        """Test pausing and resuming subscriptions."""
        callback = Mock()
        sub_id = self.api.subscribe("database.*", callback)
        
        subscription = self.api._subscriptions[sub_id]
        assert subscription.active == True
        
        # Pause
        success = self.api.pause_subscription(sub_id)
        assert success == True
        assert subscription.active == False
        
        # Resume
        success = self.api.resume_subscription(sub_id)
        assert success == True
        assert subscription.active == True
        
        # Invalid subscription
        assert self.api.pause_subscription("invalid") == False
    
    def test_get_subscriptions(self):
        """Test getting subscription information."""
        callback1 = Mock()
        callback2 = Mock()
        
        sub1 = self.api.subscribe("database.*", callback1)
        sub2 = self.api.subscribe("cache.*", callback2)
        
        subscriptions = self.api.get_subscriptions()
        
        assert len(subscriptions) == 2
        
        sub_info = subscriptions[0]
        assert "id" in sub_info
        assert "path_pattern" in sub_info
        assert "active" in sub_info
        assert "created_at" in sub_info
        assert "trigger_count" in sub_info
        assert "has_query" in sub_info
    
    def test_validate_path(self):
        """Test path validation."""
        # Valid path
        errors = self.api.validate_path("database.host", "localhost")
        assert len(errors) == 0
        
        # Invalid path - empty
        errors = self.api.validate_path("", "value")
        assert len(errors) > 0
        
        # Invalid path - dots
        errors = self.api.validate_path(".invalid.path.", "value")
        assert len(errors) > 0
        
        # Invalid path - double dots
        errors = self.api.validate_path("invalid..path", "value")
        assert len(errors) > 0
    
    def test_get_schema(self):
        """Test getting configuration schema."""
        self.api._path_cache = {
            "database.host": "localhost",
            "database.port": 5432,
            "cache.enabled": True
        }
        self.api._cache_valid = True
        
        # Get all schema
        schema = self.api.get_schema()
        assert len(schema) == 3
        
        # Check schema structure
        host_schema = schema["database.host"]
        assert host_schema["type"] == "str"
        assert host_schema["value"] == "localhost"
        assert host_schema["exists"] == True
        
        # Get filtered schema
        db_schema = self.api.get_schema("database.*")
        assert len(db_schema) == 2
        assert "database.host" in db_schema
        assert "cache.enabled" not in db_schema
    
    def test_export_config(self):
        """Test exporting configuration."""
        self.api._path_cache = {
            "database.host": "localhost",
            "database.port": 5432
        }
        self.api._cache_valid = True
        
        # Export without metadata
        exported = self.api.export_config("database.*")
        assert exported["database.host"] == "localhost"
        assert exported["database.port"] == 5432
        
        # Export with metadata
        exported_meta = self.api.export_config("database.*", include_metadata=True)
        host_meta = exported_meta["database.host"]
        assert host_meta["value"] == "localhost"
        assert host_meta["type"] == "str"
        assert host_meta["path"] == "database.host"
    
    def test_import_config(self):
        """Test importing configuration."""
        config_data = {
            "new.key1": "value1",
            "new.key2": "value2"
        }
        
        count = self.api.import_config(config_data)
        assert count == 2
        
        # Should have called set for each key
        assert self.mock_runtime_manager.set.call_count == 2
    
    def test_get_api_stats(self):
        """Test getting API statistics."""
        # Add some subscriptions
        self.api.subscribe("test.*", Mock())
        self.api.subscribe("other.*", Mock())
        self.api.pause_subscription(list(self.api._subscriptions.keys())[0])
        
        stats = self.api.get_api_stats()
        
        assert stats["total_subscriptions"] == 2
        assert stats["active_subscriptions"] == 1
        assert "cache_valid" in stats
        assert "runtime_info" in stats
    
    def test_cache_invalidation(self):
        """Test cache invalidation on changes."""
        assert self.api._cache_valid == True
        
        # Trigger change handler
        mock_event = Mock()
        mock_event.config_key = "test.key"
        mock_event.old_value = "old"
        mock_event.new_value = "new"
        
        self.api._handle_config_change(mock_event)
        
        assert self.api._cache_valid == False
    
    def test_subscription_notification(self):
        """Test subscription notification on changes."""
        callback = Mock()
        sub_id = self.api.subscribe("database.*", callback)
        
        # Trigger notification
        self.api._notify_subscriptions("database.host", "old", "new")
        
        callback.assert_called_once_with("database.host", "old", "new")
        
        # Check trigger count
        subscription = self.api._subscriptions[sub_id]
        assert subscription.trigger_count == 1
    
    def test_subscription_with_query_filter(self):
        """Test subscription notification with query filtering."""
        callback = Mock()
        query = ConfigQuery("database.*", QueryOperator.EQUALS, "localhost")
        
        self.api.subscribe("database.*", callback, query)
        
        # Should trigger (matches query)
        self.api._notify_subscriptions("database.host", "old", "localhost")
        callback.assert_called_once()
        
        callback.reset_mock()
        
        # Should not trigger (doesn't match query)
        self.api._notify_subscriptions("database.host", "old", "remote")
        callback.assert_not_called()
    
    def test_flatten_config(self):
        """Test configuration flattening."""
        config = {
            "level1": {
                "level2": {
                    "key": "value"
                },
                "key": "value1"
            },
            "key": "value2"
        }
        
        cache = {}
        self.api._flatten_config(config, "", cache)
        
        assert "level1.level2.key" in cache
        assert "level1.key" in cache
        assert "key" in cache
        assert cache["level1.level2.key"] == "value"
        assert cache["level1.key"] == "value1"
        assert cache["key"] == "value2"


class TestTypedConfigurationAPI:
    """Test TypedConfigurationAPI functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_api = Mock(spec=ConfigurationAPI)
        self.mock_api._runtime_manager = Mock()
        
        # Mock config type
        class TestConfig:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)
        
        self.test_config_type = TestConfig
        self.typed_api = TypedConfigurationAPI(self.mock_api, TestConfig)
    
    def test_typed_api_initialization(self):
        """Test TypedConfigurationAPI initialization."""
        assert self.typed_api._api == self.mock_api
        assert self.typed_api._config_type == self.test_config_type
    
    def test_get_typed_config(self):
        """Test getting fully typed configuration."""
        self.mock_api._runtime_manager._runtime_config.config = {
            "name": "test",
            "version": "1.0"
        }
        
        config = self.typed_api.get_typed_config()
        
        assert isinstance(config, self.test_config_type)
        assert config.name == "test"
        assert config.version == "1.0"
    
    def test_get_section_typed(self):
        """Test getting typed configuration section."""
        class DatabaseConfig:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)
        
        self.mock_api.get_section.return_value = {
            "host": "localhost",
            "port": 5432
        }
        
        db_config = self.typed_api.get_section_typed("database", DatabaseConfig)
        
        assert isinstance(db_config, DatabaseConfig)
        assert db_config.host == "localhost"
        assert db_config.port == 5432
    
    def test_validate_against_type(self):
        """Test validating configuration against type."""
        # Valid configuration
        self.mock_api._runtime_manager._runtime_config.config = {
            "name": "test",
            "version": "1.0"
        }
        
        errors = self.typed_api.validate_against_type()
        assert len(errors) == 0
        
        # Invalid configuration (missing required field)
        self.mock_api._runtime_manager._runtime_config.config = {}
        
        # Mock the config type to require fields
        class StrictConfig:
            def __init__(self, name, version):
                self.name = name
                self.version = version
        
        strict_api = TypedConfigurationAPI(self.mock_api, StrictConfig)
        
        errors = strict_api.validate_against_type()
        assert len(errors) > 0


if __name__ == '__main__':
    pytest.main([__file__])