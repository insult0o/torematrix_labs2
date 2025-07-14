"""
Base configuration loader interfaces and abstract classes.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pathlib import Path

from ..types import ConfigDict, ConfigSource
from ..exceptions import ConfigurationError


class ConfigLoader(ABC):
    """Abstract base class for configuration loaders."""
    
    def __init__(self, source: ConfigSource):
        """
        Initialize loader with configuration source.
        
        Args:
            source: Configuration source type
        """
        self.source = source
        self._cache: Optional[ConfigDict] = None
        self._loaded = False
    
    @abstractmethod
    def load(self) -> ConfigDict:
        """
        Load configuration from source.
        
        Returns:
            Configuration dictionary
            
        Raises:
            ConfigurationError: If loading fails
        """
        pass
    
    @abstractmethod
    def reload(self) -> ConfigDict:
        """
        Reload configuration from source.
        
        Returns:
            Configuration dictionary
            
        Raises:
            ConfigurationError: If reloading fails
        """
        pass
    
    @abstractmethod
    def exists(self) -> bool:
        """
        Check if configuration source exists.
        
        Returns:
            True if source exists, False otherwise
        """
        pass
    
    def get_source_info(self) -> Dict[str, Any]:
        """
        Get information about the configuration source.
        
        Returns:
            Dictionary with source information
        """
        return {
            'source': self.source.name,
            'loaded': self._loaded,
            'exists': self.exists()
        }
    
    def clear_cache(self) -> None:
        """Clear cached configuration."""
        self._cache = None
        self._loaded = False
    
    def is_loaded(self) -> bool:
        """Check if configuration has been loaded."""
        return self._loaded
    
    def get_cached_config(self) -> Optional[ConfigDict]:
        """Get cached configuration without reloading."""
        return self._cache


class FileConfigLoader(ConfigLoader):
    """Base class for file-based configuration loaders."""
    
    def __init__(self, file_path: Path, source: ConfigSource = ConfigSource.FILE):
        """
        Initialize file-based loader.
        
        Args:
            file_path: Path to configuration file
            source: Configuration source type
        """
        super().__init__(source)
        self.file_path = Path(file_path)
        self._last_modified: Optional[float] = None
    
    def exists(self) -> bool:
        """Check if configuration file exists."""
        return self.file_path.exists() and self.file_path.is_file()
    
    def has_changed(self) -> bool:
        """
        Check if file has changed since last load.
        
        Returns:
            True if file has changed or was never loaded
        """
        if not self.exists():
            return False
        
        try:
            current_mtime = self.file_path.stat().st_mtime
            if self._last_modified is None:
                return True
            
            return current_mtime > self._last_modified
        except OSError:
            # If we can't stat the file, assume it changed
            return True
    
    def update_last_modified(self) -> None:
        """Update the last modified timestamp."""
        if self.exists():
            try:
                self._last_modified = self.file_path.stat().st_mtime
            except OSError:
                pass
    
    def reload(self) -> ConfigDict:
        """Reload configuration if file has changed."""
        if self.has_changed():
            self.clear_cache()
        return self.load()
    
    def get_source_info(self) -> Dict[str, Any]:
        """Get file-specific source information."""
        info = super().get_source_info()
        info.update({
            'file_path': str(self.file_path),
            'file_exists': self.exists(),
            'last_modified': self._last_modified,
            'has_changed': self.has_changed() if self.exists() else None
        })
        return info


class ConfigurationError(Exception):
    """Base exception for configuration-related errors."""
    
    def __init__(self, message: str, source: Optional[ConfigSource] = None, 
                 file_path: Optional[Path] = None):
        """
        Initialize configuration error.
        
        Args:
            message: Error message
            source: Configuration source where error occurred
            file_path: File path if applicable
        """
        self.source = source
        self.file_path = file_path
        
        # Build descriptive error message
        parts = []
        if source:
            parts.append(f"[{source.name}]")
        if file_path:
            parts.append(f"({file_path})")
        parts.append(message)
        
        super().__init__(" ".join(parts))


class LoaderNotFoundError(ConfigurationError):
    """Raised when no suitable loader is found for a configuration source."""
    pass


class SourceNotFoundError(ConfigurationError):
    """Raised when a configuration source does not exist."""
    pass


class ValidationError(ConfigurationError):
    """Raised when configuration validation fails."""
    pass