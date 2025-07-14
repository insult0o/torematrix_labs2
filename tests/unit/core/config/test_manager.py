"""
Unit tests for configuration manager.
"""

import pytest
import threading
import time
from unittest.mock import Mock, patch

from torematrix.core.config.manager import ConfigurationManager
from torematrix.core.config.models import ApplicationConfig
from torematrix.core.config.types import ConfigSource, ConfigUpdatePolicy
from torematrix.core.config.exceptions import (
    ConfigurationError, ValidationError, ConfigurationAccessError
)


class TestConfigurationManager:
    """Test ConfigurationManager class."""
    
    def test_initialization(self):
        """Test manager initialization."""
        # Test with default config
        manager = ConfigurationManager()
        assert isinstance(manager._config, ApplicationConfig)
        assert manager._config.app_name == "TORE Matrix Labs V3"
        
        # Test with custom config
        custom_config = ApplicationConfig(app_name="Custom App")
        manager = ConfigurationManager(custom_config)
        assert manager._config.app_name == "Custom App"
    
    def test_get_value(self):
        """Test getting configuration values."""
        manager = ConfigurationManager()
        
        # Test simple value
        assert manager.get("app_name") == "TORE Matrix Labs V3"
        
        # Test nested value
        assert manager.get("database.type") == "sqlite"
        assert manager.get("logging.level") == "INFO"
        
        # Test non-existent value with default
        assert manager.get("non.existent", "default") == "default"
        
        # Test deep nesting
        assert manager.get("cache.redis_port") == 6379
    
    def test_set_value(self):
        """Test setting configuration values."""
        manager = ConfigurationManager()
        
        # Test simple value
        manager.set("debug", True)
        assert manager.get("debug") is True
        
        # Test nested value
        manager.set("database.port", 3306)
        assert manager.get("database.port") == 3306
        
        # Test setting invalid key
        with pytest.raises(ConfigurationAccessError):
            manager.set("non.existent.key", "value")
    
    def test_validation_on_set(self):
        """Test validation when setting values."""
        manager = ConfigurationManager()
        
        # Test invalid value that fails validation
        with pytest.raises(ValidationError):
            manager.set("database.port", 70000)  # Port too high
        
        # Ensure value wasn't changed
        assert manager.get("database.port") == 5432
    
    def test_update_batch(self):
        """Test batch configuration updates."""
        manager = ConfigurationManager()
        
        updates = {
            "debug": True,
            "logging": {
                "level": "DEBUG",
                "console": False
            }
        }
        
        manager.update(updates)
        
        assert manager.get("debug") is True
        assert manager.get("logging.level") == "DEBUG"
        assert manager.get("logging.console") is False
    
    def test_update_policies(self):
        """Test different update policies."""
        manager = ConfigurationManager()
        
        # Test MERGE policy
        manager.update(
            {"database": {"port": 3306}},
            policy=ConfigUpdatePolicy.MERGE
        )
        assert manager.get("database.port") == 3306
        assert manager.get("database.type") == "sqlite"  # Not replaced
        
        # Test REPLACE policy (should replace entire config)
        new_config = ApplicationConfig(
            app_name="New App",
            environment="production"
        ).to_dict()
        
        manager.update(new_config, policy=ConfigUpdatePolicy.REPLACE)
        assert manager.get("app_name") == "New App"
        assert manager.get("environment") == "production"
    
    def test_freeze_unfreeze(self):
        """Test configuration freezing."""
        manager = ConfigurationManager()
        
        # Normal operation
        manager.set("debug", True)
        assert manager.get("debug") is True
        
        # Freeze configuration
        manager.freeze()
        assert manager.is_frozen() is True
        
        # Try to modify frozen config
        with pytest.raises(ConfigurationError):
            manager.set("debug", False)
        
        with pytest.raises(ConfigurationError):
            manager.update({"debug": False})
        
        with pytest.raises(ConfigurationError):
            manager.reset()
        
        # Unfreeze and modify
        manager.unfreeze()
        assert manager.is_frozen() is False
        
        manager.set("debug", False)
        assert manager.get("debug") is False
    
    def test_reset(self):
        """Test configuration reset."""
        manager = ConfigurationManager()
        
        # Modify configuration
        manager.set("debug", True)
        manager.set("logging.level", "DEBUG")
        
        # Reset
        manager.reset()
        
        # Check defaults restored
        assert manager.get("debug") is False
        assert manager.get("logging.level") == "INFO"
        assert len(manager._sources) == 0
    
    def test_observer_pattern(self):
        """Test observer notifications."""
        manager = ConfigurationManager()
        
        # Track changes
        changes = []
        
        def observer(key, old_value, new_value):
            changes.append((key, old_value, new_value))
        
        manager.add_observer(observer)
        
        # Make changes
        manager.set("debug", True)
        manager.set("logging.level", "DEBUG")
        
        assert len(changes) == 2
        assert changes[0] == ("debug", False, True)
        assert changes[1] == ("logging.level", "INFO", "DEBUG")
        
        # Remove observer
        manager.remove_observer(observer)
        manager.set("debug", False)
        
        assert len(changes) == 2  # No new changes recorded
    
    def test_history_tracking(self):
        """Test configuration change history."""
        manager = ConfigurationManager()
        
        # Make some changes
        manager.set("debug", True, ConfigSource.CLI)
        manager.set("logging.level", "DEBUG", ConfigSource.ENVIRONMENT)
        
        history = manager.get_history()
        assert len(history) == 2
        
        # Check history entries
        assert history[0]["key"] == "debug"
        assert history[0]["old_value"] is False
        assert history[0]["new_value"] is True
        assert history[0]["source"] == "CLI"
        
        # Test history limit
        for i in range(200):
            manager.set("debug", i % 2 == 0)
        
        history = manager.get_history()
        assert len(history) <= 100  # Max history size
        
        # Clear history
        manager.clear_history()
        assert len(manager.get_history()) == 0
    
    def test_source_tracking(self):
        """Test configuration source tracking."""
        manager = ConfigurationManager()
        
        # Set values from different sources
        manager.merge({"debug": True}, ConfigSource.FILE)
        manager.merge({"logging": {"level": "DEBUG"}}, ConfigSource.ENVIRONMENT)
        manager.set("ui.theme", "dark", ConfigSource.CLI)
        
        # Check source info
        assert manager.get_source_info("debug") == ConfigSource.FILE
        assert manager.get_source_info("logging.level") == ConfigSource.ENVIRONMENT
        assert manager.get_source_info("ui.theme") == ConfigSource.CLI
        assert manager.get_source_info("non.existent") is None
    
    def test_metadata(self):
        """Test configuration metadata."""
        manager = ConfigurationManager()
        
        metadata = manager.get_metadata()
        assert "created_at" in metadata
        assert "last_modified" in metadata
        assert metadata["modification_count"] == 0
        
        # Make changes
        manager.set("debug", True)
        time.sleep(0.01)  # Ensure time difference
        
        new_metadata = manager.get_metadata()
        assert new_metadata["modification_count"] == 1
        assert new_metadata["last_modified"] > metadata["last_modified"]
    
    def test_export_formats(self):
        """Test configuration export."""
        manager = ConfigurationManager()
        manager.set("debug", True)
        
        # Test dict export
        config_dict = manager.to_dict()
        assert isinstance(config_dict, dict)
        assert config_dict["debug"] is True
        
        # Test JSON export
        json_str = manager.to_json()
        assert isinstance(json_str, str)
        assert '"debug": true' in json_str
        
        # Test compact JSON
        compact_json = manager.to_json(pretty=False)
        assert len(compact_json) < len(json_str)
        assert '\n' not in compact_json
    
    def test_thread_safety(self):
        """Test thread-safe operations."""
        manager = ConfigurationManager()
        errors = []
        
        def worker(thread_id):
            try:
                for i in range(100):
                    # Concurrent reads and writes
                    manager.set(f"performance.worker_threads", thread_id)
                    value = manager.get("performance.worker_threads")
                    
                    # Update nested values
                    manager.update({
                        "logging": {"level": f"THREAD_{thread_id}"}
                    })
                    
                    # Add to history
                    manager.get_history()
                    
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # No errors should occur
        assert len(errors) == 0
    
    def test_validation_method(self):
        """Test explicit validation."""
        manager = ConfigurationManager()
        
        # Valid configuration
        errors = manager.validate()
        assert isinstance(errors, list)
        
        # Create invalid configuration
        manager._config.database.type = "postgresql"
        manager._config.database.password = None
        
        errors = manager.validate()
        assert len(errors) > 0
        assert any("password required" in err for err in errors)
    
    def test_error_handling(self):
        """Test error handling in various scenarios."""
        manager = ConfigurationManager()
        
        # Test observer error handling
        def failing_observer(key, old, new):
            raise RuntimeError("Observer failed")
        
        manager.add_observer(failing_observer)
        
        # Should not raise, just print error
        manager.set("debug", True)  # Observer fails but operation continues
        assert manager.get("debug") is True
        
        # Test rollback on validation failure
        original_port = manager.get("database.port")
        
        with pytest.raises(ValidationError):
            manager.set("database.port", -1)  # Invalid port
        
        # Value should be rolled back
        assert manager.get("database.port") == original_port
    
    def test_complex_scenarios(self):
        """Test complex configuration scenarios."""
        manager = ConfigurationManager()
        
        # Scenario 1: Multi-source configuration with precedence
        manager.merge({"debug": False}, ConfigSource.FILE)
        manager.merge({"debug": True}, ConfigSource.ENVIRONMENT)
        
        # Environment should override file
        assert manager.get("debug") is True
        
        # Scenario 2: Deep nested updates
        complex_update = {
            "processing": {
                "max_file_size_mb": 200,
                "ocr_settings": {
                    "language": "fra",
                    "dpi": 400
                }
            }
        }
        
        manager.update(complex_update, policy=ConfigUpdatePolicy.MERGE_DEEP)
        assert manager.get("processing.max_file_size_mb") == 200
        
        # Scenario 3: Configuration inheritance
        base_config = manager.to_dict()
        
        # Create child manager with modified config
        child_config = ApplicationConfig(**base_config)
        child_config.environment = "production"
        
        child_manager = ConfigurationManager(child_config)
        assert child_manager.get("environment") == "production"
        assert child_manager.get("debug") is False  # Forced by production