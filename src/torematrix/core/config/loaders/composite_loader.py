"""
Composite configuration loader with precedence management.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

from .base import ConfigLoader, ConfigurationError
from ..types import ConfigDict, ConfigSource
from ..utils import merge_dicts


@dataclass
class LoaderResult:
    """Result from loading a configuration source."""
    loader: ConfigLoader
    config: Optional[ConfigDict] = None
    error: Optional[Exception] = None
    loaded: bool = False
    
    @property
    def success(self) -> bool:
        """Check if loading was successful."""
        return self.loaded and self.error is None


class CompositeLoader(ConfigLoader):
    """
    Composite loader that manages multiple loaders with precedence.
    
    Features:
    - Precedence-based configuration merging
    - Lazy loading of sources
    - Source status tracking
    - Selective reloading
    - Error isolation (failed sources don't break others)
    - Detailed loading metrics
    """
    
    def __init__(self, loaders: Optional[List[ConfigLoader]] = None,
                 precedence_order: Optional[List[ConfigSource]] = None):
        """
        Initialize composite loader.
        
        Args:
            loaders: List of configuration loaders
            precedence_order: Custom precedence order (uses default if None)
        """
        super().__init__(ConfigSource.RUNTIME)
        self.loaders: List[ConfigLoader] = loaders or []
        
        # Default precedence order (lowest to highest)
        self.precedence_order = precedence_order or [
            ConfigSource.DEFAULT,
            ConfigSource.FILE,
            ConfigSource.ENVIRONMENT,
            ConfigSource.RUNTIME,
            ConfigSource.CLI
        ]
        
        self._source_configs: Dict[ConfigSource, ConfigDict] = {}
        self._loader_results: List[LoaderResult] = []
        self._loading_stats: Dict[str, Any] = {}
    
    def add_loader(self, loader: ConfigLoader) -> None:
        """
        Add loader to composite.
        
        Args:
            loader: Configuration loader to add
        """
        self.loaders.append(loader)
        self.clear_cache()
    
    def remove_loader(self, loader: ConfigLoader) -> None:
        """
        Remove loader from composite.
        
        Args:
            loader: Configuration loader to remove
        """
        if loader in self.loaders:
            self.loaders.remove(loader)
            self.clear_cache()
    
    def insert_loader(self, index: int, loader: ConfigLoader) -> None:
        """
        Insert loader at specific position.
        
        Args:
            index: Position to insert at
            loader: Configuration loader to insert
        """
        self.loaders.insert(index, loader)
        self.clear_cache()
    
    def set_precedence_order(self, order: List[ConfigSource]) -> None:
        """
        Set custom precedence order.
        
        Args:
            order: List of ConfigSource values in precedence order
        """
        self.precedence_order = order
        self.clear_cache()
    
    def exists(self) -> bool:
        """Check if any loader exists."""
        return any(loader.exists() for loader in self.loaders)
    
    def load(self) -> ConfigDict:
        """
        Load and merge configurations from all loaders.
        
        Returns:
            Merged configuration dictionary
            
        Raises:
            ConfigurationError: If all loaders fail
        """
        if self._cache is not None:
            return self._cache
        
        import time
        start_time = time.time()
        
        # Load configurations from all sources
        self._loader_results = []
        self._source_configs = {}
        successful_loads = 0
        
        for loader in self.loaders:
            result = LoaderResult(loader=loader)
            
            try:
                if loader.exists():
                    result.config = loader.load()
                    result.loaded = True
                    successful_loads += 1
                    
                    # Store by source type
                    self._source_configs[loader.source] = result.config
                else:
                    result.config = {}
                    result.loaded = True
                    
            except Exception as e:
                result.error = e
                # Log warning but continue with other loaders
                print(f"Warning: Failed to load from {loader.source}: {e}")
            
            self._loader_results.append(result)
        
        # Check if we have any successful loads
        if successful_loads == 0 and self.loaders:
            raise ConfigurationError(
                "All configuration loaders failed",
                source=self.source
            )
        
        # Merge configurations based on precedence
        merged_config = self._merge_by_precedence()
        
        # Update loading statistics
        self._loading_stats = {
            'total_loaders': len(self.loaders),
            'successful_loads': successful_loads,
            'failed_loads': len(self.loaders) - successful_loads,
            'loading_time_seconds': time.time() - start_time,
            'merged_keys': len(self._flatten_dict(merged_config))
        }
        
        self._cache = merged_config
        self._loaded = True
        return merged_config
    
    def _merge_by_precedence(self) -> ConfigDict:
        """
        Merge configurations based on precedence order.
        
        Returns:
            Merged configuration dictionary
        """
        merged_config = {}
        
        # Merge in precedence order (lowest to highest)
        for source in self.precedence_order:
            if source in self._source_configs:
                config = self._source_configs[source]
                if config:
                    merged_config = merge_dicts(merged_config, config)
        
        return merged_config
    
    def _flatten_dict(self, d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
        """Flatten nested dictionary for counting keys."""
        items = []
        for key, value in d.items():
            new_key = f"{parent_key}{sep}{key}" if parent_key else key
            if isinstance(value, dict):
                items.extend(self._flatten_dict(value, new_key, sep).items())
            else:
                items.append((new_key, value))
        return dict(items)
    
    def reload(self) -> ConfigDict:
        """Reload all configurations."""
        self.clear_cache()
        return self.load()
    
    def reload_source(self, source: ConfigSource) -> ConfigDict:
        """
        Reload specific source.
        
        Args:
            source: Configuration source to reload
            
        Returns:
            Merged configuration after reload
        """
        for loader in self.loaders:
            if loader.source == source:
                loader.clear_cache()
        
        return self.reload()
    
    def get_source_status(self) -> Dict[ConfigSource, Dict[str, Any]]:
        """
        Get status of all configuration sources.
        
        Returns:
            Dictionary mapping sources to their status
        """
        status = {}
        
        for result in self._loader_results:
            source_info = result.loader.get_source_info()
            source_info.update({
                'load_success': result.success,
                'load_error': str(result.error) if result.error else None,
                'has_config': result.config is not None,
                'config_keys': len(result.config) if result.config else 0
            })
            status[result.loader.source] = source_info
        
        return status
    
    def get_value_source(self, key: str) -> Optional[Tuple[Any, ConfigSource]]:
        """
        Get value and its source for a configuration key.
        
        Args:
            key: Configuration key (dot-separated for nested values)
            
        Returns:
            Tuple of (value, source) or (None, None) if not found
        """
        # Check sources in reverse precedence order (highest to lowest)
        for source in reversed(self.precedence_order):
            if source in self._source_configs:
                config = self._source_configs[source]
                value = self._get_nested_value(config, key)
                if value is not None:
                    return value, source
        
        return None, None
    
    def _get_nested_value(self, config: Dict[str, Any], key: str) -> Any:
        """
        Get nested value from configuration using dot notation.
        
        Args:
            config: Configuration dictionary
            key: Dot-separated key path
            
        Returns:
            Value if found, None otherwise
        """
        current = config
        
        for part in key.split('.'):
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        
        return current
    
    def get_loading_stats(self) -> Dict[str, Any]:
        """
        Get loading statistics.
        
        Returns:
            Dictionary with loading statistics
        """
        return self._loading_stats.copy()
    
    def get_config_by_source(self, source: ConfigSource) -> Optional[ConfigDict]:
        """
        Get configuration from specific source.
        
        Args:
            source: Configuration source
            
        Returns:
            Configuration dictionary or None if not loaded
        """
        return self._source_configs.get(source)
    
    def list_sources(self) -> List[ConfigSource]:
        """
        List all available configuration sources.
        
        Returns:
            List of configuration sources
        """
        return [loader.source for loader in self.loaders]
    
    def validate_precedence(self) -> List[str]:
        """
        Validate precedence configuration.
        
        Returns:
            List of validation warnings/errors
        """
        warnings = []
        
        # Check for duplicate sources
        sources = [loader.source for loader in self.loaders]
        seen = set()
        for source in sources:
            if source in seen:
                warnings.append(f"Duplicate source: {source}")
            seen.add(source)
        
        # Check if precedence order covers all sources
        loader_sources = set(sources)
        precedence_sources = set(self.precedence_order)
        
        missing_in_precedence = loader_sources - precedence_sources
        if missing_in_precedence:
            warnings.append(f"Sources not in precedence order: {missing_in_precedence}")
        
        unused_in_precedence = precedence_sources - loader_sources
        if unused_in_precedence:
            warnings.append(f"Precedence order includes unused sources: {unused_in_precedence}")
        
        return warnings
    
    def get_source_info(self) -> Dict[str, Any]:
        """Get composite loader specific information."""
        info = super().get_source_info()
        
        info.update({
            'loader_count': len(self.loaders),
            'precedence_order': [source.name for source in self.precedence_order],
            'loaded_sources': list(self._source_configs.keys()),
            'loading_stats': self.get_loading_stats(),
            'validation_warnings': self.validate_precedence()
        })
        
        return info
    
    def __len__(self) -> int:
        """Return number of loaders."""
        return len(self.loaders)
    
    def __iter__(self):
        """Iterate over loaders."""
        return iter(self.loaders)
    
    def __getitem__(self, index: int) -> ConfigLoader:
        """Get loader by index."""
        return self.loaders[index]