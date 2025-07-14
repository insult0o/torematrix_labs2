"""
Integration example demonstrating complete loader system.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch

from torematrix.core.config.loaders import (
    CompositeLoader, FileLoader, EnvironmentLoader, CLILoader, DirectoryLoader
)
from torematrix.core.config.types import ConfigSource


def test_complete_integration_example():
    """
    Complete integration example showing all loaders working together.
    
    This demonstrates the full Agent 2 deliverable:
    - Multi-format file loading (YAML, JSON, TOML, INI)
    - Environment variable loading with nesting
    - CLI argument parsing
    - Precedence management
    - Error handling and source tracking
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        
        # Create configuration files in different formats
        yaml_file = tmp_path / "base.yaml"
        yaml_file.write_text("""
app:
  name: "TORE Matrix Labs"
  version: "3.0.0"
  debug: false

database:
  host: "localhost"
  port: 5432
  name: "torematrix"

cache:
  enabled: true
  type: "memory"
  ttl_seconds: 3600
""")
        
        json_file = tmp_path / "overrides.json"
        json_file.write_text("""
{
  "app": {
    "debug": true
  },
  "database": {
    "host": "db.example.com"
  },
  "processing": {
    "max_workers": 4
  }
}
""")
        
        # Create directory with multiple config files
        config_dir = tmp_path / "config.d"
        config_dir.mkdir()
        
        (config_dir / "00-defaults.yaml").write_text("""
performance:
  worker_threads: 2
  max_memory_usage_percent: 80
""")
        
        (config_dir / "logging.yaml").write_text("""
logging:
  level: "INFO"
  console: true
  file: "/var/log/torematrix.log"
""")
        
        # Set environment variables
        env_vars = {
            'TOREMATRIX_APP__DEBUG': 'false',  # Should override JSON
            'TOREMATRIX_DATABASE__PASSWORD': 'secret123',
            'TOREMATRIX_CACHE__TYPE': 'redis',
            'TOREMATRIX_CACHE__REDIS__HOST': 'redis.example.com',
            'TOREMATRIX_LOGGING__LEVEL': 'WARNING'  # Should override file
        }
        
        with patch.dict(os.environ, env_vars):
            # Create composite loader with all source types
            composite = CompositeLoader([
                FileLoader(yaml_file),           # Base configuration
                FileLoader(json_file),           # JSON overrides  
                DirectoryLoader(config_dir),     # Directory of configs
                EnvironmentLoader(),             # Environment variables
                CLILoader(args=[                 # CLI arguments (highest precedence)
                    '--debug',                   # Boolean flag
                    '--database-host', 'cli-host',
                    '--max-workers', '8'
                ])
            ])
            
            # Load merged configuration
            config = composite.load()
            
            # Verify precedence works correctly
            # CLI should override everything else
            assert config['debug'] is True  # From CLI flag
            assert config['database']['host'] == 'cli-host'  # From CLI
            assert config['processing']['max_workers'] == 8  # From CLI
            
            # Environment should override files
            assert config['database']['password'] == 'secret123'  # From env
            assert config['cache']['type'] == 'redis'  # From env
            assert config['cache']['redis']['host'] == 'redis.example.com'  # From env
            assert config['logging']['level'] == 'WARNING'  # From env override
            
            # File values should be preserved where not overridden
            assert config['app']['name'] == 'TORE Matrix Labs'  # From YAML
            assert config['app']['version'] == '3.0.0'  # From YAML
            assert config['database']['port'] == 5432  # From YAML
            assert config['cache']['enabled'] is True  # From YAML
            assert config['cache']['ttl_seconds'] == 3600  # From YAML
            assert config['performance']['worker_threads'] == 2  # From directory
            assert config['logging']['console'] is True  # From directory
            
            # Test source tracking
            value, source = composite.get_value_source('database.host')
            assert value == 'cli-host'
            assert source == ConfigSource.CLI
            
            value, source = composite.get_value_source('database.password')
            assert value == 'secret123'
            assert source == ConfigSource.ENVIRONMENT
            
            value, source = composite.get_value_source('app.name')
            assert value == 'TORE Matrix Labs'
            assert source == ConfigSource.FILE
            
            # Test loading statistics
            stats = composite.get_loading_stats()
            assert stats['total_loaders'] == 5
            assert stats['successful_loads'] >= 4  # At least 4 sources should work
            assert stats['merged_keys'] > 10  # Should have many configuration keys
            
            # Test source status
            status = composite.get_source_status()
            assert len(status) == 5  # All 5 loaders should be tracked
            
            # Verify all sources loaded successfully
            file_sources = [s for s in status.values() if s.get('file_exists')]
            assert len(file_sources) >= 2  # At least YAML and JSON files
            
            env_sources = [s for s in status.values() if 'matching_variables' in s]
            assert len(env_sources) == 1  # Environment loader
            assert env_sources[0]['matching_variables'] > 0
            
            cli_sources = [s for s in status.values() if 'argument_count' in s]
            assert len(cli_sources) == 1  # CLI loader
            assert cli_sources[0]['argument_count'] > 0
            
            print("✅ Complete integration test passed!")
            print(f"✅ Loaded {stats['merged_keys']} configuration keys from {stats['total_loaders']} sources")
            print(f"✅ Final debug setting: {config['debug']} (from CLI)")
            print(f"✅ Final database host: {config['database']['host']} (from CLI)")
            print(f"✅ Final cache type: {config['cache']['type']} (from environment)")
            
            return config


if __name__ == "__main__":
    # Run the integration test
    test_complete_integration_example()