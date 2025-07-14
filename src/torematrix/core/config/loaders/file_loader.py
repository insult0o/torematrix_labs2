"""
File-based configuration loaders supporting multiple formats.
"""

from typing import Dict, Any, Optional, Type
from pathlib import Path

from ..types import ConfigDict, ConfigFormat, ConfigSource
from ..sources import YAMLSource, JSONSource, TOMLSource, INISource
from .base import FileConfigLoader, ConfigurationError


class FileLoader(FileConfigLoader):
    """
    Generic file loader that detects format and delegates to appropriate source.
    
    Supports: YAML, JSON, TOML, INI
    """
    
    # Format detection mapping
    FORMAT_EXTENSIONS = {
        '.yaml': ConfigFormat.YAML,
        '.yml': ConfigFormat.YAML,
        '.json': ConfigFormat.JSON,
        '.toml': ConfigFormat.TOML,
        '.ini': ConfigFormat.INI,
        '.cfg': ConfigFormat.INI
    }
    
    # Source class mapping
    SOURCE_CLASSES = {
        ConfigFormat.YAML: YAMLSource,
        ConfigFormat.JSON: JSONSource,
        ConfigFormat.TOML: TOMLSource,
        ConfigFormat.INI: INISource
    }
    
    def __init__(self, file_path: Path, format: Optional[ConfigFormat] = None):
        """
        Initialize file loader.
        
        Args:
            file_path: Path to configuration file
            format: Optional format override (auto-detected if None)
            
        Raises:
            ConfigurationError: If format cannot be determined
        """
        super().__init__(file_path)
        self.format = format or self._detect_format()
        self._source = self._create_source()
    
    def _detect_format(self) -> ConfigFormat:
        """
        Detect configuration format from file extension.
        
        Returns:
            Detected configuration format
            
        Raises:
            ConfigurationError: If format cannot be determined
        """
        suffix = self.file_path.suffix.lower()
        if suffix in self.FORMAT_EXTENSIONS:
            return self.FORMAT_EXTENSIONS[suffix]
        
        raise ConfigurationError(
            f"Unknown configuration format for {self.file_path}. "
            f"Supported extensions: {list(self.FORMAT_EXTENSIONS.keys())}",
            source=self.source,
            file_path=self.file_path
        )
    
    def _create_source(self) -> Any:
        """
        Create appropriate source instance.
        
        Returns:
            Source instance for the detected format
            
        Raises:
            ConfigurationError: If no source is available for format
        """
        source_class = self.SOURCE_CLASSES.get(self.format)
        if not source_class:
            raise ConfigurationError(
                f"No source available for format {self.format}",
                source=self.source,
                file_path=self.file_path
            )
        
        return source_class(self.file_path)
    
    def load(self) -> ConfigDict:
        """
        Load configuration from file.
        
        Returns:
            Configuration dictionary
            
        Raises:
            ConfigurationError: If loading fails
        """
        # Use cached version if available and file hasn't changed
        if self._cache is not None and not self.has_changed():
            return self._cache
        
        # Return empty dict if file doesn't exist
        if not self.exists():
            return {}
        
        try:
            # Load using appropriate source
            self._cache = self._source.load()
            self.update_last_modified()
            self._loaded = True
            return self._cache
            
        except Exception as e:
            if isinstance(e, ConfigurationError):
                raise
            else:
                raise ConfigurationError(
                    f"Failed to load {self.file_path}: {e}",
                    source=self.source,
                    file_path=self.file_path
                )
    
    def save(self, config: ConfigDict) -> None:
        """
        Save configuration to file.
        
        Args:
            config: Configuration to save
            
        Raises:
            ConfigurationError: If saving fails
        """
        try:
            self._source.save(config)
            self._cache = config
            self.update_last_modified()
            
        except Exception as e:
            if isinstance(e, ConfigurationError):
                raise
            else:
                raise ConfigurationError(
                    f"Failed to save {self.file_path}: {e}",
                    source=self.source,
                    file_path=self.file_path
                )
    
    def get_source_info(self) -> Dict[str, Any]:
        """Get file loader specific information."""
        info = super().get_source_info()
        info.update({
            'format': self.format.name,
            'source_class': self._source.__class__.__name__
        })
        return info


class DirectoryLoader(FileConfigLoader):
    """
    Load configurations from directory of files.
    
    Features:
    - Load all config files from directory
    - Merge configurations with file name precedence
    - Support for config.d/ style directories
    - Alphabetical loading order
    """
    
    def __init__(self, directory: Path, pattern: str = "*.yaml", 
                 nest_by_filename: bool = False):
        """
        Initialize directory loader.
        
        Args:
            directory: Directory containing configuration files
            pattern: Glob pattern for matching files
            nest_by_filename: If True, nest configs under filename keys
        """
        super().__init__(directory)
        self.directory = Path(directory)
        self.pattern = pattern
        self.nest_by_filename = nest_by_filename
        self._loaders: Dict[str, FileLoader] = {}
    
    def exists(self) -> bool:
        """Check if directory exists."""
        return self.directory.exists() and self.directory.is_dir()
    
    def has_changed(self) -> bool:
        """Check if any file in directory has changed."""
        if not self.exists():
            return False
        
        # Check if any existing loader has changed
        for loader in self._loaders.values():
            if loader.has_changed():
                return True
        
        # Check for new files
        current_files = set(
            str(f) for f in self.directory.glob(self.pattern) 
            if f.is_file()
        )
        existing_files = set(self._loaders.keys())
        
        return current_files != existing_files
    
    def load(self) -> ConfigDict:
        """
        Load and merge all configuration files.
        
        Returns:
            Merged configuration dictionary
            
        Raises:
            ConfigurationError: If loading fails
        """
        if not self.exists():
            return {}
        
        # Use cache if nothing has changed
        if self._cache is not None and not self.has_changed():
            return self._cache
        
        merged_config = {}
        new_loaders = {}
        
        # Find all matching files and sort them
        file_paths = sorted(
            f for f in self.directory.glob(self.pattern) 
            if f.is_file()
        )
        
        for file_path in file_paths:
            try:
                # Reuse existing loader or create new one
                file_key = str(file_path)
                if file_key in self._loaders:
                    loader = self._loaders[file_key]
                else:
                    loader = FileLoader(file_path)
                
                config = loader.load()
                new_loaders[file_key] = loader
                
                # Merge configuration
                if self.nest_by_filename:
                    # Nest under filename (without extension)
                    key = file_path.stem
                    merged_config[key] = config
                else:
                    # Merge at root level
                    from ..utils import merge_dicts
                    merged_config = merge_dicts(merged_config, config)
                    
            except Exception as e:
                # Log error but continue with other files
                print(f"Warning: Failed to load {file_path}: {e}")
                continue
        
        self._loaders = new_loaders
        self._cache = merged_config
        self._loaded = True
        
        return merged_config
    
    def get_source_info(self) -> Dict[str, Any]:
        """Get directory loader specific information."""
        info = super().get_source_info()
        info.update({
            'directory': str(self.directory),
            'pattern': self.pattern,
            'nest_by_filename': self.nest_by_filename,
            'loaded_files': len(self._loaders),
            'file_list': list(self._loaders.keys())
        })
        return info


class MultiFileLoader(FileConfigLoader):
    """
    Load configurations from multiple specific files.
    
    Features:
    - Load from specific file list
    - Merge in specified order
    - Skip missing files
    - Individual file caching
    """
    
    def __init__(self, file_paths: list[Path], merge_order: bool = True):
        """
        Initialize multi-file loader.
        
        Args:
            file_paths: List of configuration file paths
            merge_order: If True, merge in list order; if False, merge alphabetically
        """
        # Use first file as primary path for base class
        primary_path = file_paths[0] if file_paths else Path("multi-file")
        super().__init__(primary_path)
        
        self.file_paths = [Path(p) for p in file_paths]
        self.merge_order = merge_order
        self._loaders: Dict[str, FileLoader] = {}
    
    def exists(self) -> bool:
        """Check if any of the files exist."""
        return any(path.exists() for path in self.file_paths)
    
    def has_changed(self) -> bool:
        """Check if any file has changed."""
        for loader in self._loaders.values():
            if loader.has_changed():
                return True
        return False
    
    def load(self) -> ConfigDict:
        """
        Load and merge all configuration files.
        
        Returns:
            Merged configuration dictionary
        """
        if self._cache is not None and not self.has_changed():
            return self._cache
        
        merged_config = {}
        
        # Determine order
        paths = self.file_paths if self.merge_order else sorted(self.file_paths)
        
        for file_path in paths:
            if not file_path.exists():
                continue
                
            try:
                # Get or create loader
                file_key = str(file_path)
                if file_key not in self._loaders:
                    self._loaders[file_key] = FileLoader(file_path)
                
                config = self._loaders[file_key].load()
                
                # Merge configuration
                from ..utils import merge_dicts
                merged_config = merge_dicts(merged_config, config)
                
            except Exception as e:
                print(f"Warning: Failed to load {file_path}: {e}")
                continue
        
        self._cache = merged_config
        self._loaded = True
        
        return merged_config