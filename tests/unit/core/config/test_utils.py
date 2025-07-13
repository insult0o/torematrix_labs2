"""
Unit tests for configuration utilities.
"""

import pytest
import os
import tempfile
from pathlib import Path

from torematrix.core.config.utils import (
    merge_dicts, flatten_dict, unflatten_dict, substitute_env_vars,
    load_config_file, save_config_file, get_config_diff,
    mask_sensitive_values, validate_config_schema, resolve_path
)


class TestDictOperations:
    """Test dictionary operation utilities."""
    
    def test_merge_dicts_simple(self):
        """Test simple dictionary merging."""
        base = {"a": 1, "b": 2, "c": 3}
        override = {"b": 20, "d": 4}
        
        result = merge_dicts(base, override)
        
        assert result["a"] == 1  # Unchanged
        assert result["b"] == 20  # Overridden
        assert result["c"] == 3  # Unchanged
        assert result["d"] == 4  # Added
    
    def test_merge_dicts_nested(self):
        """Test deep merging of nested dictionaries."""
        base = {
            "server": {
                "host": "localhost",
                "port": 8080,
                "ssl": False
            },
            "debug": False
        }
        
        override = {
            "server": {
                "port": 9090,
                "ssl": True
            },
            "debug": True
        }
        
        result = merge_dicts(base, override)
        
        assert result["server"]["host"] == "localhost"  # Preserved
        assert result["server"]["port"] == 9090  # Overridden
        assert result["server"]["ssl"] is True  # Overridden
        assert result["debug"] is True  # Overridden
    
    def test_merge_dicts_with_none(self):
        """Test merging with None values."""
        base = {"a": 1, "b": {"c": 2}}
        override = {"a": None, "b": {"c": None, "d": 3}}
        
        result = merge_dicts(base, override)
        
        assert result["a"] is None  # Explicitly set to None
        assert result["b"]["c"] is None
        assert result["b"]["d"] == 3
    
    def test_flatten_dict(self):
        """Test dictionary flattening."""
        nested = {
            "database": {
                "host": "localhost",
                "port": 5432,
                "credentials": {
                    "username": "user",
                    "password": "pass"
                }
            },
            "debug": True
        }
        
        flat = flatten_dict(nested)
        
        assert flat["database.host"] == "localhost"
        assert flat["database.port"] == 5432
        assert flat["database.credentials.username"] == "user"
        assert flat["database.credentials.password"] == "pass"
        assert flat["debug"] is True
    
    def test_flatten_dict_custom_separator(self):
        """Test flattening with custom separator."""
        nested = {"a": {"b": {"c": 1}}}
        
        flat = flatten_dict(nested, separator="__")
        assert "a__b__c" in flat
        assert flat["a__b__c"] == 1
    
    def test_unflatten_dict(self):
        """Test dictionary unflattening."""
        flat = {
            "database.host": "localhost",
            "database.port": 5432,
            "database.credentials.username": "user",
            "logging.level": "INFO",
            "debug": True
        }
        
        nested = unflatten_dict(flat)
        
        assert nested["database"]["host"] == "localhost"
        assert nested["database"]["port"] == 5432
        assert nested["database"]["credentials"]["username"] == "user"
        assert nested["logging"]["level"] == "INFO"
        assert nested["debug"] is True
    
    def test_flatten_unflatten_roundtrip(self):
        """Test that flatten/unflatten is reversible."""
        original = {
            "a": {
                "b": {
                    "c": 1,
                    "d": [1, 2, 3]
                },
                "e": "value"
            },
            "f": None
        }
        
        flattened = flatten_dict(original)
        restored = unflatten_dict(flattened)
        
        assert restored == original


class TestEnvironmentSubstitution:
    """Test environment variable substitution."""
    
    def test_substitute_env_vars_basic(self):
        """Test basic environment variable substitution."""
        os.environ["TEST_VAR"] = "test_value"
        
        text = "The value is ${TEST_VAR}"
        result = substitute_env_vars(text)
        assert result == "The value is test_value"
        
        # Simple format
        text = "The value is $TEST_VAR"
        result = substitute_env_vars(text)
        assert result == "The value is test_value"
    
    def test_substitute_env_vars_with_default(self):
        """Test substitution with default values."""
        # Variable doesn't exist
        text = "${MISSING_VAR:-default_value}"
        result = substitute_env_vars(text)
        assert result == "default_value"
        
        # Variable exists
        os.environ["EXISTING_VAR"] = "actual_value"
        text = "${EXISTING_VAR:-default_value}"
        result = substitute_env_vars(text)
        assert result == "actual_value"
    
    def test_substitute_env_vars_multiple(self):
        """Test multiple substitutions."""
        os.environ["HOST"] = "localhost"
        os.environ["PORT"] = "8080"
        
        text = "Server running at ${HOST}:${PORT}"
        result = substitute_env_vars(text)
        assert result == "Server running at localhost:8080"
    
    def test_substitute_env_vars_mixed_formats(self):
        """Test mixed substitution formats."""
        os.environ["VAR1"] = "value1"
        os.environ["VAR2"] = "value2"
        
        text = "Mix of ${VAR1} and $VAR2 formats"
        result = substitute_env_vars(text)
        assert result == "Mix of value1 and value2 formats"
    
    def test_substitute_env_vars_no_substitution(self):
        """Test text without variables."""
        text = "No variables here"
        result = substitute_env_vars(text)
        assert result == text


class TestConfigFileOperations:
    """Test configuration file loading and saving."""
    
    def test_load_yaml_file(self):
        """Test loading YAML configuration."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
database:
  host: localhost
  port: 5432
debug: true
""")
            f.flush()
            
            config = load_config_file(Path(f.name))
            
            assert config["database"]["host"] == "localhost"
            assert config["database"]["port"] == 5432
            assert config["debug"] is True
            
            os.unlink(f.name)
    
    def test_load_json_file(self):
        """Test loading JSON configuration."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"database": {"host": "localhost"}, "debug": true}')
            f.flush()
            
            config = load_config_file(Path(f.name))
            
            assert config["database"]["host"] == "localhost"
            assert config["debug"] is True
            
            os.unlink(f.name)
    
    def test_load_toml_file(self):
        """Test loading TOML configuration."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write("""
debug = true

[database]
host = "localhost"
port = 5432
""")
            f.flush()
            
            config = load_config_file(Path(f.name))
            
            assert config["database"]["host"] == "localhost"
            assert config["database"]["port"] == 5432
            assert config["debug"] is True
            
            os.unlink(f.name)
    
    def test_load_ini_file(self):
        """Test loading INI configuration."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write("""
[database]
host = localhost
port = 5432

[logging]
level = INFO
""")
            f.flush()
            
            config = load_config_file(Path(f.name))
            
            assert config["database"]["host"] == "localhost"
            assert config["database"]["port"] == "5432"  # INI values are strings
            assert config["logging"]["level"] == "INFO"
            
            os.unlink(f.name)
    
    def test_load_with_env_substitution(self):
        """Test loading with environment variable substitution."""
        os.environ["DB_HOST"] = "prod-server"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
database:
  host: ${DB_HOST}
  port: ${DB_PORT:-5432}
""")
            f.flush()
            
            config = load_config_file(Path(f.name))
            
            assert config["database"]["host"] == "prod-server"
            assert config["database"]["port"] == "5432"  # Default value
            
            os.unlink(f.name)
    
    def test_load_nonexistent_file(self):
        """Test loading non-existent file."""
        with pytest.raises(FileNotFoundError):
            load_config_file(Path("/non/existent/file.yaml"))
    
    def test_load_unsupported_format(self):
        """Test loading unsupported file format."""
        with tempfile.NamedTemporaryFile(suffix='.xyz', delete=False) as f:
            f.write("content")
            f.flush()
            
            with pytest.raises(ValueError) as exc:
                load_config_file(Path(f.name))
            
            assert "Unsupported" in str(exc.value)
            
            os.unlink(f.name)
    
    def test_save_yaml_file(self):
        """Test saving YAML configuration."""
        config = {
            "database": {"host": "localhost", "port": 5432},
            "debug": True
        }
        
        with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False) as f:
            save_config_file(config, Path(f.name))
            
            # Read back and verify
            loaded = load_config_file(Path(f.name))
            assert loaded == config
            
            os.unlink(f.name)
    
    def test_save_json_file(self):
        """Test saving JSON configuration."""
        config = {"server": {"host": "0.0.0.0", "port": 8080}}
        
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            save_config_file(config, Path(f.name))
            
            # Verify JSON formatting
            content = Path(f.name).read_text()
            assert '"server"' in content
            assert '"host"' in content
            
            os.unlink(f.name)
    
    def test_save_creates_directory(self):
        """Test that save creates parent directory if needed."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "subdir" / "config.yaml"
            config = {"test": "value"}
            
            save_config_file(config, file_path)
            
            assert file_path.exists()
            assert file_path.parent.exists()


class TestConfigDiff:
    """Test configuration difference detection."""
    
    def test_config_diff_simple(self):
        """Test simple configuration differences."""
        old = {"a": 1, "b": 2, "c": 3}
        new = {"a": 1, "b": 20, "d": 4}
        
        diff = get_config_diff(old, new)
        
        assert diff["added"] == {"d": 4}
        assert diff["modified"] == {"b": {"old": 2, "new": 20}}
        assert diff["removed"] == {"c": 3}
    
    def test_config_diff_nested(self):
        """Test nested configuration differences."""
        old = {
            "server": {"host": "localhost", "port": 8080},
            "debug": False
        }
        
        new = {
            "server": {"host": "0.0.0.0", "port": 8080, "ssl": True},
            "debug": True
        }
        
        diff = get_config_diff(old, new)
        
        assert diff["added"]["server.ssl"] is True
        assert diff["modified"]["server.host"]["old"] == "localhost"
        assert diff["modified"]["server.host"]["new"] == "0.0.0.0"
        assert diff["modified"]["debug"]["old"] is False
        assert diff["modified"]["debug"]["new"] is True
    
    def test_config_diff_no_changes(self):
        """Test diff with no changes."""
        config = {"a": 1, "b": {"c": 2}}
        diff = get_config_diff(config, config)
        
        assert len(diff["added"]) == 0
        assert len(diff["modified"]) == 0
        assert len(diff["removed"]) == 0


class TestSensitiveValueMasking:
    """Test masking of sensitive configuration values."""
    
    def test_mask_sensitive_values_default(self):
        """Test masking with default sensitive keys."""
        config = {
            "database": {
                "host": "localhost",
                "password": "super_secret",
                "port": 5432
            },
            "api_key": "abc123xyz",
            "debug": True
        }
        
        masked = mask_sensitive_values(config)
        
        assert masked["database"]["host"] == "localhost"  # Not sensitive
        assert masked["database"]["password"] == "********"  # Masked
        assert masked["api_key"] == "********"  # Masked
        assert masked["debug"] is True  # Not sensitive
    
    def test_mask_sensitive_values_custom(self):
        """Test masking with custom sensitive keys."""
        config = {
            "custom_secret": "hidden",
            "password": "visible"
        }
        
        masked = mask_sensitive_values(config, ["custom"])
        
        assert masked["custom_secret"] == "********"
        assert masked["password"] == "visible"  # Not in custom list
    
    def test_mask_sensitive_values_none(self):
        """Test masking handles None values."""
        config = {
            "password": None,
            "api_key": "value"
        }
        
        masked = mask_sensitive_values(config)
        
        assert masked["password"] is None  # None not masked
        assert masked["api_key"] == "*****"  # Normal masking
    
    def test_mask_sensitive_values_non_string(self):
        """Test masking non-string sensitive values."""
        config = {
            "password": 12345,
            "secret_number": 42
        }
        
        masked = mask_sensitive_values(config)
        
        assert masked["password"] == "***"  # Non-string masked as ***
        assert masked["secret_number"] == "***"


class TestPathResolution:
    """Test path resolution utilities."""
    
    def test_resolve_absolute_path(self):
        """Test resolving absolute paths."""
        abs_path = Path("/usr/local/bin")
        resolved = resolve_path(abs_path)
        assert resolved == abs_path
        assert resolved.is_absolute()
    
    def test_resolve_relative_path_with_base(self):
        """Test resolving relative paths with base."""
        base = Path("/home/user")
        rel_path = Path("config/app.yaml")
        
        resolved = resolve_path(rel_path, base)
        assert resolved == Path("/home/user/config/app.yaml")
        assert resolved.is_absolute()
    
    def test_resolve_relative_path_no_base(self):
        """Test resolving relative paths without base."""
        rel_path = Path("./config.yaml")
        resolved = resolve_path(rel_path)
        
        # Should resolve to current directory
        assert resolved.is_absolute()
        assert resolved.name == "config.yaml"
    
    def test_resolve_string_path(self):
        """Test resolving string paths."""
        resolved = resolve_path("config/app.yaml", Path("/app"))
        assert resolved == Path("/app/config/app.yaml")