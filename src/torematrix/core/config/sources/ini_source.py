"""
INI configuration source implementation.
"""

from configparser import ConfigParser
from pathlib import Path
from typing import Dict, Any

from ..types import ConfigDict
from ..utils import substitute_env_vars
from ..exceptions import ConfigurationError


class INISource:
    """INI configuration source with environment variable substitution."""
    
    def __init__(self, file_path: Path):
        """
        Initialize INI source.
        
        Args:
            file_path: Path to INI configuration file
        """
        self.file_path = Path(file_path)
    
    def load(self) -> ConfigDict:
        """
        Load INI configuration.
        
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
            
            # Parse INI content
            parser = ConfigParser()
            parser.read_string(content)
            
            # Convert to dictionary
            config = {}
            for section_name in parser.sections():
                section = {}
                for key, value in parser.items(section_name):
                    # Try to parse values as appropriate types
                    section[key] = self._parse_value(value)
                config[section_name] = section
            
            return config
            
        except Exception as e:
            if "No section:" in str(e) or "No option:" in str(e):
                raise ConfigurationError(
                    f"Invalid INI format: {e}",
                    file_path=self.file_path
                )
            elif isinstance(e, FileNotFoundError):
                raise ConfigurationError(
                    f"INI file not found: {self.file_path}",
                    file_path=self.file_path
                )
            else:
                raise ConfigurationError(
                    f"Failed to load INI file: {e}",
                    file_path=self.file_path
                )
    
    def _parse_value(self, value: str) -> Any:
        """
        Parse INI value to appropriate Python type.
        
        Args:
            value: String value from INI file
            
        Returns:
            Parsed value with appropriate type
        """
        # Handle boolean values
        if value.lower() in ('true', 'yes', 'on', '1'):
            return True
        elif value.lower() in ('false', 'no', 'off', '0'):
            return False
        
        # Handle None/null values
        if value.lower() in ('none', 'null', ''):
            return None
        
        # Try to parse as number
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            pass
        
        # Return as string
        return value
    
    def save(self, config: ConfigDict) -> None:
        """
        Save configuration to INI.
        
        Args:
            config: Configuration dictionary to save
            
        Raises:
            ConfigurationError: If saving fails
        """
        try:
            # Ensure parent directory exists
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            
            parser = ConfigParser()
            
            # Convert dictionary to ConfigParser format
            for section_name, section_data in config.items():
                if isinstance(section_data, dict):
                    parser.add_section(section_name)
                    for key, value in section_data.items():
                        parser.set(section_name, key, str(value))
            
            with open(self.file_path, 'w', encoding='utf-8') as f:
                parser.write(f)
                
        except Exception as e:
            raise ConfigurationError(
                f"Failed to save INI file: {e}",
                file_path=self.file_path
            )
    
    def __str__(self) -> str:
        return f"INISource({self.file_path})"
    
    def __repr__(self) -> str:
        return f"INISource(file_path={self.file_path!r})"