"""
Tests for configuration encryption functionality.
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, mock_open
from src.torematrix.core.config.security.encryption import ConfigEncryption
from src.torematrix.core.config.exceptions import ConfigurationError


class TestConfigEncryption:
    """Test configuration encryption and decryption."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.encryption = ConfigEncryption()
        self.test_key = ConfigEncryption.generate_key()
        self.encryption.set_key(self.test_key)
    
    def test_key_generation(self):
        """Test encryption key generation."""
        key = ConfigEncryption.generate_key()
        assert isinstance(key, bytes)
        assert len(key) == 44  # Fernet key length in base64
    
    def test_key_derivation(self):
        """Test key derivation from password."""
        password = "test_password"
        key1, salt1 = ConfigEncryption.derive_key(password)
        key2, salt2 = ConfigEncryption.derive_key(password, salt1)
        
        assert isinstance(key1, bytes)
        assert isinstance(salt1, bytes)
        assert key1 == key2  # Same password + salt = same key
        assert len(salt1) == 16  # Salt length
    
    def test_encrypt_decrypt_value(self):
        """Test basic value encryption and decryption."""
        test_value = "secret_password"
        
        encrypted = self.encryption.encrypt_value(test_value)
        assert isinstance(encrypted, str)
        assert encrypted != test_value
        
        decrypted = self.encryption.decrypt_value(encrypted)
        assert decrypted == test_value
    
    def test_encrypt_decrypt_complex_value(self):
        """Test encryption of complex data types."""
        test_values = [
            {"nested": {"password": "secret"}},
            [1, 2, 3, "test"],
            42,
            3.14,
            True,
            None
        ]
        
        for value in test_values:
            encrypted = self.encryption.encrypt_value(value)
            decrypted = self.encryption.decrypt_value(encrypted)
            assert decrypted == value
    
    def test_encrypt_field(self):
        """Test field-level encryption."""
        config = {
            "database": {
                "host": "localhost",
                "password": "secret123"
            },
            "api_key": "key123"
        }
        
        # Encrypt database password
        result = self.encryption.encrypt_field(config, "database.password")
        
        assert result["database"]["host"] == "localhost"  # Unchanged
        assert result["database"]["password"].startswith("ENC:")
        assert result["api_key"] == "key123"  # Unchanged
        
        # Verify field is tracked
        assert "database.password" in self.encryption.get_encrypted_fields()
    
    def test_decrypt_field(self):
        """Test field-level decryption."""
        config = {
            "database": {
                "password": "ENC:" + self.encryption.encrypt_value("secret123")
            }
        }
        
        result = self.encryption.decrypt_field(config, "database.password")
        assert result["database"]["password"] == "secret123"
    
    def test_encrypt_config(self):
        """Test full configuration encryption."""
        config = {
            "database": {
                "host": "localhost",
                "password": "secret123",
                "user": "admin"
            },
            "api_key": "key123",
            "secret_token": "token456",
            "public_value": "not_secret"
        }
        
        result = self.encryption.encrypt_config(config)
        
        # Sensitive fields should be encrypted
        assert result["database"]["password"].startswith("ENC:")
        assert result["api_key"].startswith("ENC:")
        assert result["secret_token"].startswith("ENC:")
        
        # Non-sensitive fields unchanged
        assert result["database"]["host"] == "localhost"
        assert result["database"]["user"] == "admin"
        assert result["public_value"] == "not_secret"
    
    def test_decrypt_config(self):
        """Test full configuration decryption."""
        # First encrypt a config
        original_config = {
            "database": {
                "password": "secret123"
            },
            "api_key": "key123"
        }
        
        encrypted_config = self.encryption.encrypt_config(original_config)
        decrypted_config = self.encryption.decrypt_config(encrypted_config)
        
        assert decrypted_config["database"]["password"] == "secret123"
        assert decrypted_config["api_key"] == "key123"
    
    def test_is_encrypted(self):
        """Test encrypted value detection."""
        assert self.encryption.is_encrypted("ENC:abcd1234")
        assert not self.encryption.is_encrypted("regular_value")
        assert not self.encryption.is_encrypted(123)
        assert not self.encryption.is_encrypted(None)
    
    def test_save_load_key(self):
        """Test key saving and loading."""
        with tempfile.TemporaryDirectory() as temp_dir:
            key_path = Path(temp_dir) / "test.key"
            
            # Save key
            self.encryption.save_key(key_path)
            assert key_path.exists()
            
            # Load key in new instance
            new_encryption = ConfigEncryption()
            new_encryption.load_key(key_path)
            
            # Test they work the same
            test_value = "test_secret"
            encrypted = self.encryption.encrypt_value(test_value)
            decrypted = new_encryption.decrypt_value(encrypted)
            assert decrypted == test_value
    
    def test_no_key_error(self):
        """Test operations without key raise appropriate errors."""
        no_key_encryption = ConfigEncryption()
        
        with pytest.raises(ConfigurationError, match="No encryption key set"):
            no_key_encryption.encrypt_value("test")
        
        with pytest.raises(ConfigurationError, match="No encryption key set"):
            no_key_encryption.decrypt_value("ENC:test")
    
    def test_invalid_field_path(self):
        """Test encryption with invalid field paths."""
        config = {"test": "value"}
        
        with pytest.raises(ConfigurationError, match="Field path.*not found"):
            self.encryption.encrypt_field(config, "nonexistent.field")
        
        with pytest.raises(ConfigurationError, match="Field.*not found"):
            self.encryption.encrypt_field(config, "test.nested")
    
    def test_decrypt_invalid_value(self):
        """Test decryption of invalid encrypted values."""
        with pytest.raises(ConfigurationError, match="Failed to decrypt value"):
            self.encryption.decrypt_value("invalid_base64")
        
        with pytest.raises(ConfigurationError, match="Failed to decrypt value"):
            self.encryption.decrypt_value("dGVzdA==")  # Valid base64 but not encrypted
    
    def test_custom_field_patterns(self):
        """Test encryption with custom field patterns."""
        config = {
            "custom_secret": "value1",
            "my_credential": "value2",
            "regular_field": "value3"
        }
        
        patterns = ["custom", "credential"]
        result = self.encryption.encrypt_config(config, patterns)
        
        assert result["custom_secret"].startswith("ENC:")
        assert result["my_credential"].startswith("ENC:")
        assert result["regular_field"] == "value3"  # Not encrypted
    
    def test_find_encrypted_fields(self):
        """Test finding encrypted fields in configuration."""
        config = {
            "field1": "ENC:encrypted1",
            "nested": {
                "field2": "ENC:encrypted2",
                "field3": "regular_value"
            },
            "field4": "regular_value"
        }
        
        encrypted_fields = self.encryption._find_encrypted_fields(config)
        assert "field1" in encrypted_fields
        assert "nested.field2" in encrypted_fields
        assert "nested.field3" not in encrypted_fields
        assert "field4" not in encrypted_fields
    
    def test_encrypted_fields_tracking(self):
        """Test tracking of encrypted fields."""
        config = {"password": "secret"}
        
        # Initially no encrypted fields
        assert len(self.encryption.get_encrypted_fields()) == 0
        
        # Encrypt field
        self.encryption.encrypt_field(config, "password")
        assert "password" in self.encryption.get_encrypted_fields()
        
        # Decrypt field
        encrypted_config = {"password": "ENC:" + self.encryption.encrypt_value("secret")}
        self.encryption.decrypt_field(encrypted_config, "password")
        assert "password" not in self.encryption.get_encrypted_fields()


if __name__ == '__main__':
    pytest.main([__file__])