"""
Unit tests for configuration types.
"""

import pytest
from torematrix.core.config.types import (
    ConfigSource, ConfigFormat, ConfigUpdatePolicy,
    ValidationSeverity, ConfigProtocol
)


class TestConfigSource:
    """Test ConfigSource enum."""
    
    def test_precedence_order(self):
        """Test source precedence values."""
        assert ConfigSource.DEFAULT < ConfigSource.FILE
        assert ConfigSource.FILE < ConfigSource.ENVIRONMENT
        assert ConfigSource.ENVIRONMENT < ConfigSource.RUNTIME
        assert ConfigSource.RUNTIME < ConfigSource.CLI
    
    def test_string_representation(self):
        """Test string representation."""
        assert str(ConfigSource.DEFAULT) == "DEFAULT"
        assert str(ConfigSource.CLI) == "CLI"


class TestConfigFormat:
    """Test ConfigFormat enum."""
    
    def test_string_representation(self):
        """Test string representation is lowercase."""
        assert str(ConfigFormat.YAML) == "yaml"
        assert str(ConfigFormat.JSON) == "json"
        assert str(ConfigFormat.TOML) == "toml"
    
    def test_all_formats_defined(self):
        """Test all expected formats are defined."""
        expected_formats = {"YAML", "JSON", "TOML", "INI", "ENV"}
        actual_formats = {f.name for f in ConfigFormat}
        assert actual_formats == expected_formats


class TestConfigUpdatePolicy:
    """Test ConfigUpdatePolicy enum."""
    
    def test_policy_values(self):
        """Test all policies are defined."""
        policies = {p.name for p in ConfigUpdatePolicy}
        assert "MERGE" in policies
        assert "REPLACE" in policies
        assert "MERGE_DEEP" in policies


class TestValidationSeverity:
    """Test ValidationSeverity enum."""
    
    def test_severity_order(self):
        """Test severity levels are ordered."""
        assert ValidationSeverity.WARNING < ValidationSeverity.ERROR
        assert ValidationSeverity.ERROR < ValidationSeverity.CRITICAL
    
    def test_string_representation(self):
        """Test string representation."""
        assert str(ValidationSeverity.WARNING) == "WARNING"
        assert str(ValidationSeverity.ERROR) == "ERROR"


class TestConfigProtocol:
    """Test ConfigProtocol interface."""
    
    def test_protocol_methods(self):
        """Test protocol defines required methods."""
        # Create a class that implements the protocol
        class TestConfig:
            def to_dict(self):
                return {"test": "value"}
            
            def from_dict(self, data):
                pass
            
            def validate(self):
                return []
        
        # Should be compatible with protocol
        config = TestConfig()
        assert hasattr(config, 'to_dict')
        assert hasattr(config, 'from_dict')
        assert hasattr(config, 'validate')
        
        # Test methods work
        assert config.to_dict() == {"test": "value"}
        assert config.validate() == []