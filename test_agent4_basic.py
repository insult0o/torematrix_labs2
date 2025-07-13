#!/usr/bin/env python3
"""
Basic test for Agent 4 configuration management implementation.
"""

import sys
import tempfile
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_encryption():
    """Test configuration encryption functionality."""
    print("Testing encryption...")
    
    from torematrix.core.config.security.encryption import ConfigEncryption
    from torematrix.core.config.exceptions import ConfigurationError
    
    # Test key generation and basic encryption
    enc = ConfigEncryption()
    key = ConfigEncryption.generate_key()
    enc.set_key(key)
    
    # Test value encryption
    test_value = "secret_password"
    encrypted = enc.encrypt_value(test_value)
    decrypted = enc.decrypt_value(encrypted)
    
    assert decrypted == test_value, "Basic encryption/decryption failed"
    
    # Test config encryption
    config = {
        "database": {
            "host": "localhost",
            "password": "secret123"
        },
        "api_key": "key456",
        "public_setting": "not_secret"
    }
    
    encrypted_config = enc.encrypt_config(config)
    
    # Check that sensitive fields are encrypted
    assert encrypted_config["database"]["password"].startswith("ENC:")
    assert encrypted_config["api_key"].startswith("ENC:")
    assert encrypted_config["public_setting"] == "not_secret"  # Not encrypted
    
    # Test decryption
    decrypted_config = enc.decrypt_config(encrypted_config)
    assert decrypted_config["database"]["password"] == "secret123"
    assert decrypted_config["api_key"] == "key456"
    
    print("✓ Encryption tests passed")


def test_secret_management():
    """Test secret management functionality."""
    print("Testing secret management...")
    
    from torematrix.core.config.security.secrets import SecretManager, EnvironmentSecretProvider, FileSecretProvider
    import os
    
    # Test environment provider
    manager = SecretManager()
    env_provider = EnvironmentSecretProvider()
    manager.register_provider('env', env_provider, is_default=True)
    
    # Set and get environment secret
    test_key = "TEST_SECRET"
    test_value = "secret_value_123"
    
    manager.set_secret(test_key, test_value)
    retrieved = manager.get_secret(test_key)
    
    assert retrieved == test_value, "Environment secret storage failed"
    
    # Test secret interpolation
    config = {
        "database": {
            "password": "${secret:db_password}",
            "user": "admin"
        },
        "api_key": "${TEST_SECRET}"
    }
    
    # Set db_password secret
    manager.set_secret("db_password", "db_secret_123")
    
    interpolated = manager.interpolate_secrets(config)
    
    assert interpolated["database"]["password"] == "db_secret_123"
    assert interpolated["api_key"] == test_value
    assert interpolated["database"]["user"] == "admin"  # Not a secret reference
    
    print("✓ Secret management tests passed")


def test_profile_management():
    """Test profile management functionality."""
    print("Testing profile management...")
    
    from torematrix.core.config.profiles.manager import ProfileManager, ProfileType
    
    # Create temporary directory for profiles
    with tempfile.TemporaryDirectory() as temp_dir:
        profiles_dir = Path(temp_dir)
        manager = ProfileManager(profiles_dir)
        
        # Create base profile
        base_config = {
            "database": {
                "host": "localhost",
                "port": 5432
            },
            "debug": False
        }
        
        manager.create_profile(
            name="base",
            config=base_config,
            profile_type=ProfileType.ENVIRONMENT,
            description="Base configuration"
        )
        
        # Create development profile that inherits from base
        dev_config = {
            "database": {
                "host": "dev.localhost"
            },
            "debug": True
        }
        
        manager.create_profile(
            name="development",
            config=dev_config,
            profile_type=ProfileType.ENVIRONMENT,
            parent="base",
            description="Development environment"
        )
        
        # Test profile resolution
        manager.activate_profile("development")
        
        empty_base = {}
        resolved_config = manager.resolve_config(empty_base, "development")
        
        # Should have merged base and development configs
        assert resolved_config["database"]["host"] == "dev.localhost"  # From dev
        assert resolved_config["database"]["port"] == 5432  # From base
        assert resolved_config["debug"] is True  # From dev
        
        # Test profile listing
        profiles = manager.list_profiles()
        assert "base" in profiles
        assert "development" in profiles
        
        print("✓ Profile management tests passed")


def test_cli_functionality():
    """Test CLI functionality (basic import)."""
    print("Testing CLI...")
    
    # Just test that CLI module can be imported
    from torematrix.core.config.cli import cli
    
    # CLI module imports successfully
    assert cli is not None
    
    print("✓ CLI tests passed")


def main():
    """Run all tests."""
    print("TORE Matrix Configuration Management - Agent 4 Tests")
    print("=" * 60)
    
    try:
        test_encryption()
        test_secret_management() 
        test_profile_management()
        test_cli_functionality()
        
        print("\n" + "=" * 60)
        print("🎉 All Agent 4 tests passed! Configuration management system is working.")
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())