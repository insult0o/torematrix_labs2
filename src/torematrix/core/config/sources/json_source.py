"""
JSON configuration source implementation.
"""

import json
from pathlib import Path
from typing import Dict, Any

from ..types import ConfigDict
from ..utils import substitute_env_vars
from ..exceptions import ConfigurationError


class JSONSource:
    """JSON configuration source with environment variable substitution."""
    
    def __init__(self, file_path: Path):
        """
        Initialize JSON source.
        
        Args:
            file_path: Path to JSON configuration file
        """
        self.file_path = Path(file_path)
    
    def load(self) -> ConfigDict:
        """
        Load JSON configuration.
        
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
            
            # Load JSON
            config = json.loads(content)
            return config or {}
            
        except json.JSONDecodeError as e:
            raise ConfigurationError(
                f"Invalid JSON syntax: {e}",
                file_path=self.file_path
            )
        except FileNotFoundError:
            raise ConfigurationError(
                f"JSON file not found: {self.file_path}",
                file_path=self.file_path
            )
        except Exception as e:
            raise ConfigurationError(
                f"Failed to load JSON file: {e}",
                file_path=self.file_path
            )
    
    def save(self, config: ConfigDict) -> None:
        """
        Save configuration to JSON.
        
        Args:
            config: Configuration dictionary to save
            
        Raises:
            ConfigurationError: If saving fails
        """
        try:
            # Ensure parent directory exists
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(
                    config,
                    f,
                    indent=2,
                    ensure_ascii=False,
                    sort_keys=False
                )
                
        except Exception as e:
            raise ConfigurationError(
                f"Failed to save JSON file: {e}",
                file_path=self.file_path
            )
    
    def __str__(self) -> str:
        return f"JSONSource({self.file_path})"
    
    def __repr__(self) -> str:
        return f"JSONSource(file_path={self.file_path!r})"