"""
Environment variable configuration loaders.
"""

import os
import json
from typing import Dict, Any, Optional, List, Set
from pathlib import Path

from .base import ConfigLoader, FileConfigLoader, ConfigurationError
from ..types import ConfigDict, ConfigSource
from ..utils import unflatten_dict


class EnvironmentLoader(ConfigLoader):
    """
    Load configuration from environment variables.
    
    Features:
    - Prefix-based filtering
    - Automatic type conversion
    - Nested structure support via delimiter
    - JSON value parsing for complex types
    - Boolean and null value recognition
    """
    
    def __init__(self, prefix: str = "TOREMATRIX_", delimiter: str = "__"):
        """
        Initialize environment loader.
        
        Args:
            prefix: Environment variable prefix to filter on
            delimiter: Delimiter for nested keys (converts to dots)
        """
        super().__init__(ConfigSource.ENVIRONMENT)
        self.prefix = prefix.upper()
        self.delimiter = delimiter
        self._type_converters = {
            'true': True,
            'false': False,
            'none': None,
            'null': None
        }
    
    def exists(self) -> bool:
        """Check if any matching environment variables exist."""
        return any(key.startswith(self.prefix) for key in os.environ)
    
    def load(self) -> ConfigDict:
        """
        Load configuration from environment variables.
        
        Returns:
            Configuration dictionary with nested structure
        """
        if self._cache is not None:
            return self._cache
        
        env_config = {}
        
        for key, value in os.environ.items():
            if key.startswith(self.prefix):
                # Remove prefix and convert to lowercase
                config_key = key[len(self.prefix):].lower()
                
                # Convert delimiter to dots for nesting
                config_key = config_key.replace(self.delimiter, '.')
                
                # Parse value to appropriate type
                parsed_value = self._parse_value(value)
                
                # Add to flat dictionary
                env_config[config_key] = parsed_value
        
        # Convert flat dictionary to nested structure
        self._cache = unflatten_dict(env_config)
        self._loaded = True
        return self._cache
    
    def _parse_value(self, value: str) -> Any:
        """
        Parse environment variable value to appropriate type.
        
        Args:
            value: String value from environment variable
            
        Returns:
            Parsed value with appropriate type
        """
        # Handle empty strings
        if not value:
            return ""
        
        # Try to parse as JSON for complex types (lists, dicts)
        if value.startswith('[') or value.startswith('{'):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                # If JSON parsing fails, treat as string
                pass
        
        # Check for boolean/null values
        lower_value = value.lower()
        if lower_value in self._type_converters:
            return self._type_converters[lower_value]
        
        # Try to parse as number
        try:
            # Try integer first
            if '.' not in value and 'e' not in value.lower():
                return int(value)
            # Then try float
            return float(value)
        except ValueError:
            pass
        
        # Return as string
        return value
    
    def reload(self) -> ConfigDict:
        """Reload environment variables."""
        self.clear_cache()
        return self.load()
    
    def get_source_info(self) -> Dict[str, Any]:
        """Get environment loader specific information."""
        info = super().get_source_info()
        
        # Count matching environment variables
        matching_vars = [
            key for key in os.environ.keys() 
            if key.startswith(self.prefix)
        ]
        
        info.update({
            'prefix': self.prefix,
            'delimiter': self.delimiter,
            'matching_variables': len(matching_vars),
            'variable_names': matching_vars
        })
        return info


class DotEnvLoader(FileConfigLoader):
    """
    Load configuration from .env files.
    
    Features:
    - Support for .env file format
    - Variable expansion
    - Comments and empty lines handling
    - Integration with EnvironmentLoader for parsing
    """
    
    def __init__(self, env_file: Path = Path('.env'), 
                 prefix: str = "TOREMATRIX_", delimiter: str = "__"):
        """
        Initialize .env file loader.
        
        Args:
            env_file: Path to .env file
            prefix: Environment variable prefix for parsing
            delimiter: Delimiter for nested keys
        """
        super().__init__(env_file, ConfigSource.FILE)
        self.env_loader = EnvironmentLoader(prefix, delimiter)
        self._original_environ: Optional[Dict[str, str]] = None
    
    def load(self) -> ConfigDict:
        """
        Load .env file and parse variables.
        
        Returns:
            Configuration dictionary
            
        Raises:
            ConfigurationError: If loading fails
        """
        if not self.exists():
            return {}
        
        # Use cached version if file hasn't changed
        if self._cache is not None and not self.has_changed():
            return self._cache
        
        try:
            # Parse .env file
            env_vars = self._parse_env_file()
            
            # Temporarily modify environment
            self._original_environ = os.environ.copy()
            os.environ.update(env_vars)
            
            try:
                # Use environment loader to parse with type conversion
                config = self.env_loader.load()
            finally:
                # Restore original environment
                os.environ.clear()
                os.environ.update(self._original_environ)
                self._original_environ = None
            
            self._cache = config
            self.update_last_modified()
            self._loaded = True
            return config
            
        except Exception as e:
            raise ConfigurationError(
                f"Failed to load .env file: {e}",
                source=self.source,
                file_path=self.file_path
            )
    
    def _parse_env_file(self) -> Dict[str, str]:
        """
        Parse .env file format.
        
        Returns:
            Dictionary of environment variables
        """
        env_vars = {}
        
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse key=value pairs
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Remove quotes if present
                        if (value.startswith('"') and value.endswith('"')) or \
                           (value.startswith("'") and value.endswith("'")):
                            value = value[1:-1]
                        
                        # Expand environment variables in value
                        value = os.path.expandvars(value)
                        
                        env_vars[key] = value
                    else:
                        print(f"Warning: Invalid line {line_num} in {self.file_path}: {line}")
            
            return env_vars
            
        except Exception as e:
            raise ConfigurationError(
                f"Failed to parse .env file: {e}",
                source=self.source,
                file_path=self.file_path
            )
    
    def get_source_info(self) -> Dict[str, Any]:
        """Get .env loader specific information."""
        info = super().get_source_info()
        info.update({
            'env_loader_prefix': self.env_loader.prefix,
            'env_loader_delimiter': self.env_loader.delimiter
        })
        return info


class MultiEnvLoader(ConfigLoader):
    """
    Load from multiple .env files with precedence.
    
    Features:
    - Load from multiple .env files
    - Later files override earlier ones
    - Skip missing files
    - Combine with system environment variables
    """
    
    def __init__(self, env_files: List[Path], 
                 prefix: str = "TOREMATRIX_", delimiter: str = "__",
                 include_system_env: bool = True):
        """
        Initialize multi-env loader.
        
        Args:
            env_files: List of .env file paths (in precedence order)
            prefix: Environment variable prefix
            delimiter: Delimiter for nested keys  
            include_system_env: Whether to include system environment variables
        """
        super().__init__(ConfigSource.ENVIRONMENT)
        self.env_files = [Path(f) for f in env_files]
        self.prefix = prefix
        self.delimiter = delimiter
        self.include_system_env = include_system_env
        self._loaders: List[DotEnvLoader] = []
        self._system_loader: Optional[EnvironmentLoader] = None
        
        # Create loaders
        for env_file in self.env_files:
            self._loaders.append(DotEnvLoader(env_file, prefix, delimiter))
        
        if self.include_system_env:
            self._system_loader = EnvironmentLoader(prefix, delimiter)
    
    def exists(self) -> bool:
        """Check if any .env file exists or system vars are available."""
        file_exists = any(loader.exists() for loader in self._loaders)
        system_exists = self._system_loader.exists() if self._system_loader else False
        return file_exists or system_exists
    
    def load(self) -> ConfigDict:
        """
        Load and merge configurations from all sources.
        
        Returns:
            Merged configuration dictionary
        """
        if self._cache is not None:
            return self._cache
        
        merged_config = {}
        
        # Load from .env files first (in order)
        for loader in self._loaders:
            if loader.exists():
                try:
                    config = loader.load()
                    from ..utils import merge_dicts
                    merged_config = merge_dicts(merged_config, config)
                except Exception as e:
                    print(f"Warning: Failed to load {loader.file_path}: {e}")
        
        # Load from system environment last (highest precedence)
        if self._system_loader and self._system_loader.exists():
            try:
                system_config = self._system_loader.load()
                from ..utils import merge_dicts
                merged_config = merge_dicts(merged_config, system_config)
            except Exception as e:
                print(f"Warning: Failed to load system environment: {e}")
        
        self._cache = merged_config
        self._loaded = True
        return merged_config
    
    def reload(self) -> ConfigDict:
        """Reload all environment sources."""
        self.clear_cache()
        
        # Clear caches for all loaders
        for loader in self._loaders:
            loader.clear_cache()
        
        if self._system_loader:
            self._system_loader.clear_cache()
        
        return self.load()
    
    def get_source_info(self) -> Dict[str, Any]:
        """Get multi-env loader information."""
        info = super().get_source_info()
        
        file_info = []
        for loader in self._loaders:
            file_info.append({
                'path': str(loader.file_path),
                'exists': loader.exists(),
                'loaded': loader.is_loaded()
            })
        
        info.update({
            'prefix': self.prefix,
            'delimiter': self.delimiter,
            'include_system_env': self.include_system_env,
            'env_files': file_info,
            'system_env_available': self._system_loader.exists() if self._system_loader else False
        })
        return info