"""
Tests for composite configuration loader.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch

from torematrix.core.config.loaders import (
    CompositeLoader, FileLoader, EnvironmentLoader, CLILoader
)
from torematrix.core.config.types import ConfigSource


class TestCompositeLoader:
    """Test composite loader functionality."""
    
    def test_empty_composite_loader(self):
        """Test composite loader with no loaders."""
        composite = CompositeLoader()
        
        assert composite.exists() is False
        assert composite.load() == {}
        assert len(composite) == 0
        assert composite.get_loading_stats()['total_loaders'] == 0
    
    def test_precedence_order(self):
        """Test configuration precedence is respected."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create test configuration file
            config_file = Path(tmp_dir) / "config.yaml"
            config_file.write_text("""
debug: false
database:
  host: file-host
  port: 5432
logging:
  level: INFO
""")
            
            # Set environment variable
            with patch.dict(os.environ, {
                'TOREMATRIX_DATABASE__HOST': 'env-host',
                'TOREMATRIX_LOGGING__LEVEL': 'DEBUG'
            }):
                # Create composite loader
                composite = CompositeLoader([
                    FileLoader(config_file),
                    EnvironmentLoader(),
                ])
                
                config = composite.load()
                
                # Environment should override file
                assert config['database']['host'] == 'env-host'
                assert config['database']['port'] == 5432  # From file
                assert config['debug'] is False  # From file
                assert config['logging']['level'] == 'DEBUG'  # From env
    
    def test_loader_management(self):
        """Test adding, removing, and inserting loaders."""
        composite = CompositeLoader()
        
        file_loader = Mock()
        file_loader.source = ConfigSource.FILE
        
        env_loader = Mock()  
        env_loader.source = ConfigSource.ENVIRONMENT
        
        # Test adding
        composite.add_loader(file_loader)
        assert len(composite) == 1
        assert file_loader in composite
        
        # Test inserting
        composite.insert_loader(0, env_loader)
        assert len(composite) == 2
        assert composite[0] == env_loader
        assert composite[1] == file_loader
        
        # Test removing
        composite.remove_loader(env_loader)
        assert len(composite) == 1
        assert env_loader not in composite
        assert composite[0] == file_loader
    
    def test_source_status(self):
        """Test getting status of all sources."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_file = Path(tmp_dir) / "config.yaml"
            config_file.write_text("debug: true")
            
            missing_file = Path(tmp_dir) / "missing.yaml"
            
            composite = CompositeLoader([
                FileLoader(config_file),
                FileLoader(missing_file),
                EnvironmentLoader()
            ])
            
            # Load to populate status
            composite.load()
            
            status = composite.get_source_status()
            
            # Check that all sources are reported
            assert ConfigSource.FILE in status
            assert ConfigSource.ENVIRONMENT in status
            
            # Check status details
            file_status = [s for s in status.values() 
                          if s.get('file_path') == str(config_file)][0]
            assert file_status['load_success'] is True
            assert file_status['file_exists'] is True
    
    def test_value_source_tracking(self):
        """Test tracking which source provides each value."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_file = Path(tmp_dir) / "config.yaml"
            config_file.write_text("""
database:
  host: file-host
  port: 5432
""")
            
            with patch.dict(os.environ, {'TOREMATRIX_DATABASE__HOST': 'env-host'}):
                composite = CompositeLoader([
                    FileLoader(config_file),
                    EnvironmentLoader()
                ])
                
                composite.load()
                
                # Check value sources
                host_value, host_source = composite.get_value_source('database.host')
                assert host_value == 'env-host'
                assert host_source == ConfigSource.ENVIRONMENT
                
                port_value, port_source = composite.get_value_source('database.port')
                assert port_value == 5432
                assert port_source == ConfigSource.FILE
                
                # Non-existent key
                missing_value, missing_source = composite.get_value_source('missing.key')
                assert missing_value is None
                assert missing_source is None
    
    def test_custom_precedence_order(self):
        """Test custom precedence order."""
        # Custom order: CLI > FILE > ENVIRONMENT  
        custom_order = [ConfigSource.ENVIRONMENT, ConfigSource.FILE, ConfigSource.CLI]
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_file = Path(tmp_dir) / "config.yaml"
            config_file.write_text("value: file")
            
            with patch.dict(os.environ, {'TOREMATRIX_VALUE': 'env'}):
                file_loader = FileLoader(config_file)
                env_loader = EnvironmentLoader()
                cli_loader = CLILoader(args=['--value', 'cli'])
                
                composite = CompositeLoader(
                    [file_loader, env_loader, cli_loader],
                    precedence_order=custom_order
                )
                
                config = composite.load()
                
                # With custom order, CLI should win
                assert config['value'] == 'cli'
    
    def test_error_isolation(self):
        """Test that failed loaders don't break others."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            good_file = Path(tmp_dir) / "good.yaml"
            good_file.write_text("good: value")
            
            bad_file = Path(tmp_dir) / "bad.yaml"
            bad_file.write_text("invalid: yaml: content: [")
            
            composite = CompositeLoader([
                FileLoader(good_file),
                FileLoader(bad_file)
            ])
            
            # Should succeed despite one loader failing
            config = composite.load()
            assert config == {"good": "value"}
            
            # Check that error is recorded
            status = composite.get_source_status()
            good_status = [s for s in status.values() 
                          if 'good.yaml' in str(s.get('file_path', ''))][0]
            bad_status = [s for s in status.values() 
                         if 'bad.yaml' in str(s.get('file_path', ''))][0]
            
            assert good_status['load_success'] is True
            assert bad_status['load_success'] is False
            assert bad_status['load_error'] is not None
    
    def test_loading_statistics(self):
        """Test loading statistics collection."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_file = Path(tmp_dir) / "config.yaml"
            config_file.write_text("""
app:
  name: test
  debug: true
database:
  host: localhost
""")
            
            composite = CompositeLoader([
                FileLoader(config_file),
                EnvironmentLoader()
            ])
            
            config = composite.load()
            stats = composite.get_loading_stats()
            
            assert stats['total_loaders'] == 2
            assert stats['successful_loads'] >= 1
            assert stats['loading_time_seconds'] >= 0
            assert stats['merged_keys'] > 0
    
    def test_validation_warnings(self):
        """Test precedence validation."""
        # Create loaders with duplicate sources
        file_loader1 = Mock()
        file_loader1.source = ConfigSource.FILE
        file_loader2 = Mock()
        file_loader2.source = ConfigSource.FILE
        
        composite = CompositeLoader([file_loader1, file_loader2])
        warnings = composite.validate_precedence()
        
        assert any("Duplicate source" in warning for warning in warnings)
    
    def test_reload_specific_source(self):
        """Test reloading specific configuration source."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_file = Path(tmp_dir) / "config.yaml"
            config_file.write_text("value: original")
            
            composite = CompositeLoader([FileLoader(config_file)])
            
            # Initial load
            config = composite.load()
            assert config['value'] == 'original'
            
            # Modify file
            config_file.write_text("value: modified")
            
            # Reload specific source
            config = composite.reload_source(ConfigSource.FILE)
            assert config['value'] == 'modified'