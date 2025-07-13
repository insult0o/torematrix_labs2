"""
TOML configuration source implementation.
"""

import toml
from pathlib import Path
from typing import Dict, Any

from ..types import ConfigDict
from ..utils import substitute_env_vars
from ..exceptions import ConfigurationError


class TOMLSource:
    """TOML configuration source with environment variable substitution."""
    
    def __init__(self, file_path: Path):
        """
        Initialize TOML source.
        
        Args:
            file_path: Path to TOML configuration file
        """
        self.file_path = Path(file_path)
    
    def load(self) -> ConfigDict:
        """
        Load TOML configuration.
        
        Returns:
            Configuration dictionary
            
        Raises:
            ConfigurationError: If loading fails
        """
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Support for environment variable substitution
            content = substitute_env_vars(content)
            
            # Load TOML
            config = toml.loads(content)
            return config or {}
            
        except toml.TomlDecodeError as e:
            raise ConfigurationError(
                f"Invalid TOML syntax: {e}",
                file_path=self.file_path
            )
        except FileNotFoundError:
            raise ConfigurationError(
                f"TOML file not found: {self.file_path}",
                file_path=self.file_path
            )
        except Exception as e:
            raise ConfigurationError(
                f"Failed to load TOML file: {e}",
                file_path=self.file_path
            )
    
    def save(self, config: ConfigDict) -> None:
        """
        Save configuration to TOML.
        
        Args:
            config: Configuration dictionary to save
            
        Raises:
            ConfigurationError: If saving fails
        """
        try:
            # Ensure parent directory exists
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.file_path, 'w', encoding='utf-8') as f:
                toml.dump(config, f)
                
        except Exception as e:
            raise ConfigurationError(
                f"Failed to save TOML file: {e}",
                file_path=self.file_path
            )
    
    def __str__(self) -> str:
        return f"TOMLSource({self.file_path})"
    
    def __repr__(self) -> str:
        return f"TOMLSource(file_path={self.file_path!r})"