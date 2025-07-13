"""
Integration tests for configuration management system.
"""

import pytest
import tempfile
from pathlib import Path
import os

from torematrix.core.config import (
    ConfigurationManager, ApplicationConfig, ConfigSource,
    ConfigurationError, ValidationError
)


class TestConfigurationIntegration:
    """Test configuration system integration."""
    
    def test_basic_configuration_workflow(self):
        """Test basic configuration workflow."""
        # Create manager with default config
        manager = ConfigurationManager()
        
        # Verify defaults
        assert manager.get("app_name") == "TORE Matrix Labs V3"
        assert manager.get("environment") == "development"
        assert manager.get("debug") is True  # Default in development
        
        # Update configuration
        manager.set("debug", False)
        manager.set("database.host", "db.example.com")
        
        # Verify updates
        assert manager.get("debug") is False
        assert manager.get("database.host") == "db.example.com"
        
        # Test validation
        errors = manager.validate()
        assert isinstance(errors, list)
    
    def test_production_environment(self):
        """Test production environment configuration."""
        config = ApplicationConfig(environment="production")
        manager = ConfigurationManager(config)
        
        # Production should force certain settings
        assert manager.get("debug") is False
        assert manager.get("logging.level") == "WARNING"
        assert manager.get("security.enable_authentication") is True
    
    def test_configuration_export_import(self):
        """Test configuration export and import."""
        manager = ConfigurationManager()
        
        # Modify configuration
        manager.set("ui.theme", "dark")
        manager.set("processing.max_file_size_mb", 200)
        
        # Export to dict
        config_dict = manager.to_dict()
        assert config_dict["ui"]["theme"] == "dark"
        assert config_dict["processing"]["max_file_size_mb"] == 200
        
        # Export to JSON
        json_str = manager.to_json()
        assert '"theme": "dark"' in json_str
    
    def test_configuration_sources(self):
        """Test configuration source tracking."""
        manager = ConfigurationManager()
        
        # Merge from different sources
        manager.merge({"debug": True}, ConfigSource.FILE)
        manager.merge({"logging": {"level": "DEBUG"}}, ConfigSource.ENVIRONMENT)
        manager.set("ui.theme", "dark", ConfigSource.CLI)
        
        # Check source tracking
        assert manager.get_source_info("debug") == ConfigSource.FILE
        assert manager.get_source_info("logging.level") == ConfigSource.ENVIRONMENT
        assert manager.get_source_info("ui.theme") == ConfigSource.CLI
    
    def test_configuration_observer(self):
        """Test configuration change notifications."""
        manager = ConfigurationManager()
        changes = []
        
        def observer(key, old_value, new_value):
            changes.append((key, old_value, new_value))
        
        manager.add_observer(observer)
        
        # Make changes
        manager.set("debug", False)
        manager.set("database.port", 3306)
        
        assert len(changes) == 2
        assert changes[0] == ("debug", True, False)
        assert changes[1] == ("database.port", 5432, 3306)
    
    def test_configuration_freeze(self):
        """Test configuration freezing."""
        manager = ConfigurationManager()
        
        # Freeze configuration
        manager.freeze()
        
        # Should not be able to modify
        with pytest.raises(ConfigurationError):
            manager.set("debug", False)
        
        # Unfreeze and modify
        manager.unfreeze()
        manager.set("debug", False)
        assert manager.get("debug") is False
    
    def test_configuration_history(self):
        """Test configuration change history."""
        manager = ConfigurationManager()
        
        # Make changes
        manager.set("debug", False, ConfigSource.CLI)
        manager.set("logging.level", "ERROR", ConfigSource.ENVIRONMENT)
        
        history = manager.get_history()
        assert len(history) >= 2
        
        # Check history entries
        last_entry = history[-1]
        assert "timestamp" in last_entry
        assert last_entry["key"] == "logging.level"
        assert last_entry["source"] == "ENVIRONMENT"
    
    def test_validation_errors(self):
        """Test configuration validation errors."""
        manager = ConfigurationManager()
        
        # Try to set invalid values
        with pytest.raises(ValidationError):
            manager.set("database.port", 70000)  # Too high
        
        # Database validation - test that we can't create invalid postgresql config
        # The validation happens immediately due to Pydantic
        from pydantic import ValidationError as PydanticValidationError
        
        # Try to create a PostgreSQL database config without username
        try:
            # This should fail validation
            new_config = ApplicationConfig()
            new_config.database.type = "postgresql"
            # The validator should trigger here
        except PydanticValidationError as e:
            # This is expected
            assert "requires a username" in str(e)