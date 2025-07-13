"""
YAML configuration source implementation.
"""

import yaml
from pathlib import Path
from typing import Dict, Any

from ..types import ConfigDict
from ..utils import substitute_env_vars
from ..exceptions import ConfigurationError


class YAMLSource:
    """YAML configuration source with environment variable substitution."""
    
    def __init__(self, file_path: Path):
        """
        Initialize YAML source.
        
        Args:
            file_path: Path to YAML configuration file
        """
        self.file_path = Path(file_path)
    
    def load(self) -> ConfigDict:
        """
        Load YAML configuration.
        
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
            
            # Load YAML with safe loader
            config = yaml.safe_load(content)
            return config or {}
            
        except yaml.YAMLError as e:
            raise ConfigurationError(
                f"Invalid YAML syntax: {e}",
                file_path=self.file_path
            )
        except FileNotFoundError:
            raise ConfigurationError(
                f"YAML file not found: {self.file_path}",
                file_path=self.file_path
            )
        except Exception as e:
            raise ConfigurationError(
                f"Failed to load YAML file: {e}",
                file_path=self.file_path
            )
    
    def save(self, config: ConfigDict) -> None:
        """
        Save configuration to YAML.
        
        Args:
            config: Configuration dictionary to save
            
        Raises:
            ConfigurationError: If saving fails
        """
        try:
            # Ensure parent directory exists
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.file_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(
                    config, 
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                    indent=2
                )
                
        except Exception as e:
            raise ConfigurationError(
                f"Failed to save YAML file: {e}",
                file_path=self.file_path
            )
    
    def __str__(self) -> str:
        return f"YAMLSource({self.file_path})"
    
    def __repr__(self) -> str:
        return f"YAMLSource(file_path={self.file_path!r})"