"""
Command-line argument configuration loaders.
"""

import argparse
import sys
from typing import Dict, Any, Optional, List, Union

from .base import ConfigLoader, ConfigurationError
from ..types import ConfigDict, ConfigSource
from ..utils import unflatten_dict


class CLILoader(ConfigLoader):
    """
    Load configuration from command-line arguments.
    
    Features:
    - Integration with argparse
    - Automatic config mapping
    - Type preservation
    - Nested argument support via underscores
    - Custom argument parser support
    """
    
    def __init__(self, parser: Optional[argparse.ArgumentParser] = None,
                 args: Optional[List[str]] = None):
        """
        Initialize CLI loader.
        
        Args:
            parser: Optional ArgumentParser instance (creates default if None)
            args: Optional argument list (uses sys.argv if None)
        """
        super().__init__(ConfigSource.CLI)
        self.parser = parser or self._create_default_parser()
        self.args = args
        self._parsed_args: Optional[argparse.Namespace] = None
    
    def _create_default_parser(self) -> argparse.ArgumentParser:
        """
        Create default argument parser with common options.
        
        Returns:
            Configured ArgumentParser instance
        """
        parser = argparse.ArgumentParser(
            description="TORE Matrix Labs Configuration",
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        
        # Common configuration arguments
        parser.add_argument(
            '--debug', 
            action='store_true',
            help='Enable debug mode'
        )
        
        parser.add_argument(
            '--config', 
            type=str,
            help='Configuration file path'
        )
        
        parser.add_argument(
            '--environment', 
            type=str,
            choices=['development', 'testing', 'staging', 'production'],
            help='Environment name'
        )
        
        # Database settings
        parser.add_argument(
            '--database-host', 
            type=str,
            help='Database host'
        )
        
        parser.add_argument(
            '--database-port', 
            type=int,
            help='Database port'
        )
        
        parser.add_argument(
            '--database-name', 
            type=str,
            help='Database name'
        )
        
        # Logging settings
        parser.add_argument(
            '--log-level', 
            type=str,
            choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
            help='Logging level'
        )
        
        parser.add_argument(
            '--log-file', 
            type=str,
            help='Log file path'
        )
        
        # Processing settings
        parser.add_argument(
            '--max-workers', 
            type=int,
            help='Maximum number of worker threads'
        )
        
        parser.add_argument(
            '--max-file-size', 
            type=int,
            help='Maximum file size in MB'
        )
        
        # Cache settings
        parser.add_argument(
            '--cache-enabled', 
            action='store_true',
            help='Enable caching'
        )
        
        parser.add_argument(
            '--cache-type', 
            type=str,
            choices=['memory', 'disk', 'redis'],
            help='Cache type'
        )
        
        return parser
    
    def add_argument(self, *args, **kwargs) -> None:
        """
        Add argument to parser.
        
        Args:
            *args: Positional arguments for add_argument
            **kwargs: Keyword arguments for add_argument
        """
        self.parser.add_argument(*args, **kwargs)
        # Clear cached args since parser changed
        self._parsed_args = None
        self.clear_cache()
    
    def exists(self) -> bool:
        """CLI arguments always exist (even if empty)."""
        return True
    
    def load(self) -> ConfigDict:
        """
        Load configuration from CLI arguments.
        
        Returns:
            Configuration dictionary with nested structure
            
        Raises:
            ConfigurationError: If parsing fails
        """
        if self._cache is not None:
            return self._cache
        
        try:
            # Parse arguments if not already parsed
            if self._parsed_args is None:
                if self.args is not None:
                    self._parsed_args = self.parser.parse_args(self.args)
                else:
                    self._parsed_args = self.parser.parse_args()
            
            # Convert namespace to dictionary
            args_dict = vars(self._parsed_args)
            
            # Filter out None values and convert underscores to dots
            config_dict = {}
            for key, value in args_dict.items():
                if value is not None and not key.startswith('_'):
                    # Convert underscore to dot for nesting
                    config_key = key.replace('_', '.')
                    config_dict[config_key] = value
            
            # Convert flat dictionary to nested structure
            self._cache = unflatten_dict(config_dict)
            self._loaded = True
            return self._cache
            
        except SystemExit:
            # argparse calls sys.exit on --help or errors
            raise ConfigurationError(
                "Command-line argument parsing failed",
                source=self.source
            )
        except Exception as e:
            raise ConfigurationError(
                f"Failed to parse command-line arguments: {e}",
                source=self.source
            )
    
    def reload(self) -> ConfigDict:
        """CLI arguments don't change during runtime, return cached value."""
        return self.load()
    
    def get_source_info(self) -> Dict[str, Any]:
        """Get CLI loader specific information."""
        info = super().get_source_info()
        
        # Get argument count and names
        arg_names = []
        if self._parsed_args:
            arg_names = [
                key for key, value in vars(self._parsed_args).items()
                if value is not None and not key.startswith('_')
            ]
        
        info.update({
            'parser_description': self.parser.description,
            'argument_count': len(arg_names),
            'argument_names': arg_names,
            'custom_args_provided': self.args is not None
        })
        return info


class ClickLoader(ConfigLoader):
    """
    Load configuration from Click framework context.
    
    Features:
    - Integration with Click options
    - Context-based configuration
    - Automatic type mapping
    - Click parameter extraction
    """
    
    def __init__(self, ctx: Optional[Any] = None):
        """
        Initialize Click loader.
        
        Args:
            ctx: Click context object
        """
        super().__init__(ConfigSource.CLI)
        self.ctx = ctx
    
    def exists(self) -> bool:
        """Check if Click context exists."""
        return self.ctx is not None
    
    def load(self) -> ConfigDict:
        """
        Load configuration from Click context.
        
        Returns:
            Configuration dictionary with nested structure
            
        Raises:
            ConfigurationError: If loading fails
        """
        if not self.exists():
            return {}
        
        if self._cache is not None:
            return self._cache
        
        try:
            # Extract parameters from context
            config_dict = {}
            
            if hasattr(self.ctx, 'params'):
                for key, value in self.ctx.params.items():
                    if value is not None:
                        # Convert underscore to dot for nesting
                        config_key = key.replace('_', '.')
                        config_dict[config_key] = value
            
            # Also check for Click options and arguments
            if hasattr(self.ctx, 'command') and hasattr(self.ctx.command, 'params'):
                for param in self.ctx.command.params:
                    if hasattr(param, 'name'):
                        value = self.ctx.params.get(param.name)
                        if value is not None:
                            config_key = param.name.replace('_', '.')
                            config_dict[config_key] = value
            
            # Convert flat dictionary to nested structure
            self._cache = unflatten_dict(config_dict)
            self._loaded = True
            return self._cache
            
        except Exception as e:
            raise ConfigurationError(
                f"Failed to load Click context: {e}",
                source=self.source
            )
    
    def reload(self) -> ConfigDict:
        """Click context doesn't change during runtime."""
        return self.load()
    
    def get_source_info(self) -> Dict[str, Any]:
        """Get Click loader specific information."""
        info = super().get_source_info()
        
        if self.ctx:
            command_name = None
            param_count = 0
            
            if hasattr(self.ctx, 'command'):
                command_name = getattr(self.ctx.command, 'name', None)
                if hasattr(self.ctx.command, 'params'):
                    param_count = len(self.ctx.command.params)
            
            info.update({
                'command_name': command_name,
                'parameter_count': param_count,
                'context_available': True
            })
        else:
            info.update({
                'context_available': False
            })
        
        return info


class ArgumentBuilder:
    """
    Helper class for building CLI argument parsers dynamically.
    
    Features:
    - Build parser from configuration schema
    - Type-aware argument generation
    - Nested configuration support
    - Default value handling
    """
    
    def __init__(self):
        """Initialize argument builder."""
        self.parser = argparse.ArgumentParser()
        self._type_mapping = {
            str: str,
            int: int,
            float: float,
            bool: self._bool_type,
            list: str,  # Will be parsed as JSON
            dict: str   # Will be parsed as JSON
        }
    
    def _bool_type(self, value: str) -> bool:
        """
        Parse boolean values from strings.
        
        Args:
            value: String value to parse
            
        Returns:
            Boolean value
        """
        if value.lower() in ('true', 'yes', '1', 'on'):
            return True
        elif value.lower() in ('false', 'no', '0', 'off'):
            return False
        else:
            raise argparse.ArgumentTypeError(f"Boolean value expected, got: {value}")
    
    def add_from_schema(self, schema: Dict[str, Any], prefix: str = "") -> None:
        """
        Add arguments from configuration schema.
        
        Args:
            schema: Configuration schema dictionary
            prefix: Prefix for nested arguments
        """
        for key, value in schema.items():
            arg_name = f"--{prefix}{key}".replace('_', '-')
            
            if isinstance(value, dict):
                # Nested configuration - add with prefix
                if 'type' in value:
                    # Schema definition
                    self._add_schema_argument(arg_name, value)
                else:
                    # Nested object - recurse
                    new_prefix = f"{prefix}{key}-" if prefix else f"{key}-"
                    self.add_from_schema(value, new_prefix)
            else:
                # Simple value - infer type
                self._add_simple_argument(arg_name, value)
    
    def _add_schema_argument(self, arg_name: str, schema: Dict[str, Any]) -> None:
        """Add argument from schema definition."""
        kwargs = {}
        
        # Handle type
        if 'type' in schema:
            arg_type = schema['type']
            if arg_type in self._type_mapping:
                kwargs['type'] = self._type_mapping[arg_type]
        
        # Handle help
        if 'description' in schema:
            kwargs['help'] = schema['description']
        
        # Handle default
        if 'default' in schema:
            kwargs['default'] = schema['default']
        
        # Handle choices
        if 'choices' in schema:
            kwargs['choices'] = schema['choices']
        
        # Handle boolean flags
        if schema.get('type') == bool and schema.get('default') is False:
            kwargs['action'] = 'store_true'
            kwargs.pop('type', None)
        
        self.parser.add_argument(arg_name, **kwargs)
    
    def _add_simple_argument(self, arg_name: str, default_value: Any) -> None:
        """Add argument with inferred type from default value."""
        kwargs = {
            'default': default_value,
            'type': type(default_value)
        }
        
        # Handle boolean flags
        if isinstance(default_value, bool) and not default_value:
            kwargs = {'action': 'store_true'}
        
        self.parser.add_argument(arg_name, **kwargs)
    
    def build_loader(self, args: Optional[List[str]] = None) -> CLILoader:
        """
        Build CLI loader with configured parser.
        
        Args:
            args: Optional argument list
            
        Returns:
            Configured CLILoader
        """
        return CLILoader(self.parser, args)