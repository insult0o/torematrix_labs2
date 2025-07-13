"""
Unit tests for configuration exceptions.
"""

import pytest
from torematrix.core.config.exceptions import (
    ConfigurationError, ValidationError, ConfigurationNotFoundError,
    ConfigurationLoadError, ConfigurationSaveError, ConfigurationAccessError,
    ConfigurationLockError
)


class TestConfigurationError:
    """Test base ConfigurationError."""
    
    def test_basic_error(self):
        """Test basic error creation."""
        error = ConfigurationError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert error.details == {}
    
    def test_error_with_details(self):
        """Test error with additional details."""
        details = {"file": "config.yaml", "line": 42}
        error = ConfigurationError("Parse error", details)
        
        assert str(error) == "Parse error"
        assert error.details == details
        assert error.details["file"] == "config.yaml"


class TestValidationError:
    """Test ValidationError."""
    
    def test_validation_error_no_errors(self):
        """Test validation error without specific errors."""
        error = ValidationError("Validation failed")
        assert str(error) == "Validation failed"
        assert error.errors == []
        assert error.details["validation_errors"] == []
    
    def test_validation_error_with_errors(self):
        """Test validation error with error list."""
        errors = [
            "Field 'username' is required",
            "Field 'age' must be positive"
        ]
        error = ValidationError("Multiple validation errors", errors)
        
        assert str(error) == "Multiple validation errors"
        assert error.errors == errors
        assert len(error.details["validation_errors"]) == 2
    
    def test_validation_error_inheritance(self):
        """Test that ValidationError inherits from ConfigurationError."""
        error = ValidationError("Test")
        assert isinstance(error, ConfigurationError)
        assert isinstance(error, Exception)


class TestConfigurationNotFoundError:
    """Test ConfigurationNotFoundError."""
    
    def test_not_found_error(self):
        """Test configuration not found error."""
        error = ConfigurationNotFoundError("/path/to/config.yaml")
        
        assert "Configuration not found: /path/to/config.yaml" in str(error)
        assert error.path == "/path/to/config.yaml"
        assert error.details["path"] == "/path/to/config.yaml"
    
    def test_not_found_inheritance(self):
        """Test inheritance."""
        error = ConfigurationNotFoundError("test.yaml")
        assert isinstance(error, ConfigurationError)


class TestConfigurationLoadError:
    """Test ConfigurationLoadError."""
    
    def test_load_error(self):
        """Test configuration load error."""
        error = ConfigurationLoadError("config.yaml", "Invalid YAML syntax")
        
        assert "Failed to load configuration from config.yaml: Invalid YAML syntax" in str(error)
        assert error.source == "config.yaml"
        assert error.reason == "Invalid YAML syntax"
        assert error.details["source"] == "config.yaml"
        assert error.details["reason"] == "Invalid YAML syntax"
    
    def test_load_error_different_sources(self):
        """Test load error with different source types."""
        # File source
        error = ConfigurationLoadError("config.json", "JSON decode error")
        assert "config.json" in str(error)
        
        # Environment source
        error = ConfigurationLoadError("environment", "Missing required variable")
        assert "environment" in str(error)
        
        # URL source
        error = ConfigurationLoadError("http://example.com/config", "Connection timeout")
        assert "http://example.com/config" in str(error)


class TestConfigurationSaveError:
    """Test ConfigurationSaveError."""
    
    def test_save_error(self):
        """Test configuration save error."""
        error = ConfigurationSaveError("/tmp/config.yaml", "Permission denied")
        
        assert "Failed to save configuration to /tmp/config.yaml: Permission denied" in str(error)
        assert error.destination == "/tmp/config.yaml"
        assert error.reason == "Permission denied"
        assert error.details["destination"] == "/tmp/config.yaml"
        assert error.details["reason"] == "Permission denied"
    
    def test_save_error_various_reasons(self):
        """Test save error with various reasons."""
        # Disk full
        error = ConfigurationSaveError("config.yaml", "No space left on device")
        assert "No space left on device" in str(error)
        
        # Invalid format
        error = ConfigurationSaveError("config.xyz", "Unsupported format")
        assert "Unsupported format" in str(error)


class TestConfigurationAccessError:
    """Test ConfigurationAccessError."""
    
    def test_access_error(self):
        """Test configuration access error."""
        error = ConfigurationAccessError("database.password", "Key not found")
        
        assert "Cannot access configuration key 'database.password': Key not found" in str(error)
        assert error.key == "database.password"
        assert error.reason == "Key not found"
        assert error.details["key"] == "database.password"
        assert error.details["reason"] == "Key not found"
    
    def test_access_error_various_reasons(self):
        """Test access error with various reasons."""
        # Type mismatch
        error = ConfigurationAccessError("port", "Expected integer, got string")
        assert "Expected integer, got string" in str(error)
        
        # Permission denied
        error = ConfigurationAccessError("security.secret_key", "Insufficient permissions")
        assert "Insufficient permissions" in str(error)
        
        # Invalid path
        error = ConfigurationAccessError("a.b.c.d.e", "Path too deep")
        assert "Path too deep" in str(error)


class TestConfigurationLockError:
    """Test ConfigurationLockError."""
    
    def test_lock_error(self):
        """Test configuration lock error."""
        error = ConfigurationLockError(5.0)
        
        assert "Failed to acquire configuration lock within 5.0s" in str(error)
        assert error.timeout == 5.0
        assert error.details["timeout"] == 5.0
    
    def test_lock_error_different_timeouts(self):
        """Test lock error with different timeout values."""
        # Short timeout
        error = ConfigurationLockError(0.1)
        assert "0.1s" in str(error)
        
        # Long timeout
        error = ConfigurationLockError(30.0)
        assert "30.0s" in str(error)


class TestExceptionHierarchy:
    """Test exception hierarchy and relationships."""
    
    def test_all_inherit_from_base(self):
        """Test all exceptions inherit from ConfigurationError."""
        exceptions = [
            ValidationError("test"),
            ConfigurationNotFoundError("test"),
            ConfigurationLoadError("test", "reason"),
            ConfigurationSaveError("test", "reason"),
            ConfigurationAccessError("test", "reason"),
            ConfigurationLockError(1.0)
        ]
        
        for exc in exceptions:
            assert isinstance(exc, ConfigurationError)
            assert isinstance(exc, Exception)
    
    def test_exception_catching(self):
        """Test exception catching patterns."""
        # Can catch specific exception
        with pytest.raises(ValidationError):
            raise ValidationError("test")
        
        # Can catch base exception
        with pytest.raises(ConfigurationError):
            raise ValidationError("test")
        
        # Can catch Exception
        with pytest.raises(Exception):
            raise ConfigurationError("test")
    
    def test_exception_type_checking(self):
        """Test exception type checking."""
        try:
            raise ValidationError("test", ["error1", "error2"])
        except ConfigurationError as e:
            # Can check specific type
            assert isinstance(e, ValidationError)
            # Can access specific attributes
            assert hasattr(e, 'errors')
            assert len(e.errors) == 2