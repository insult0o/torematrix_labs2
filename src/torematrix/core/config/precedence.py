"""
Configuration precedence management.
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from .types import ConfigSource, ConfigDict
from .utils import merge_dicts


@dataclass
class PrecedenceRule:
    """Rule for configuration precedence."""
    source: ConfigSource
    priority: int
    conditions: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Validate rule after initialization."""
        if self.priority < 0:
            raise ValueError("Priority must be non-negative")


class PrecedenceManager:
    """
    Manage configuration source precedence with advanced features.
    
    Default precedence (lowest to highest):
    1. DEFAULT - Built-in defaults
    2. FILE - Configuration files  
    3. ENVIRONMENT - Environment variables
    4. RUNTIME - Runtime modifications
    5. CLI - Command-line arguments
    """
    
    def __init__(self, custom_precedence: Optional[List[ConfigSource]] = None):
        """
        Initialize precedence manager.
        
        Args:
            custom_precedence: Custom precedence order (uses default if None)
        """
        self.precedence = custom_precedence or [
            ConfigSource.DEFAULT,
            ConfigSource.FILE,
            ConfigSource.ENVIRONMENT, 
            ConfigSource.RUNTIME,
            ConfigSource.CLI
        ]
        
        self._source_configs: Dict[ConfigSource, ConfigDict] = {}
        self._precedence_rules: List[PrecedenceRule] = []
        self._merge_history: List[Dict[str, Any]] = []
    
    def set_precedence(self, precedence: List[ConfigSource]) -> None:
        """
        Set custom precedence order.
        
        Args:
            precedence: List of ConfigSource values in order
        """
        self.precedence = precedence
        self.clear_merge_history()
    
    def add_precedence_rule(self, rule: PrecedenceRule) -> None:
        """
        Add custom precedence rule.
        
        Args:
            rule: Precedence rule to add
        """
        self._precedence_rules.append(rule)
    
    def add_config(self, source: ConfigSource, config: ConfigDict, 
                   metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Add configuration for a source.
        
        Args:
            source: Configuration source
            config: Configuration dictionary
            metadata: Optional metadata about the configuration
        """
        self._source_configs[source] = config
        
        # Record in merge history
        self._merge_history.append({
            'action': 'add',
            'source': source,
            'timestamp': self._get_timestamp(),
            'config_keys': list(config.keys()) if config else [],
            'metadata': metadata or {}
        })
    
    def remove_config(self, source: ConfigSource) -> Optional[ConfigDict]:
        """
        Remove configuration for a source.
        
        Args:
            source: Configuration source to remove
            
        Returns:
            Removed configuration or None if not found
        """
        removed = self._source_configs.pop(source, None)
        
        if removed is not None:
            self._merge_history.append({
                'action': 'remove',
                'source': source,
                'timestamp': self._get_timestamp(),
                'config_keys': list(removed.keys())
            })
        
        return removed
    
    def get_merged_config(self) -> ConfigDict:
        """
        Get merged configuration respecting precedence.
        
        Returns:
            Merged configuration dictionary
        """
        merged = {}
        
        # Apply custom rules first if any
        effective_precedence = self._get_effective_precedence()
        
        # Merge in precedence order (lowest to highest)
        for source in effective_precedence:
            if source in self._source_configs:
                config = self._source_configs[source]
                if config:
                    merged = merge_dicts(merged, config)
        
        # Record merge operation
        self._merge_history.append({
            'action': 'merge',
            'timestamp': self._get_timestamp(),
            'source_count': len(self._source_configs),
            'merged_keys': len(self._flatten_config(merged)),
            'precedence_order': [s.name for s in effective_precedence]
        })
        
        return merged
    
    def _get_effective_precedence(self) -> List[ConfigSource]:
        """
        Get effective precedence order considering custom rules.
        
        Returns:
            List of ConfigSource values in effective order
        """
        if not self._precedence_rules:
            return self.precedence
        
        # For now, use simple precedence order
        # TODO: Implement complex rule evaluation if needed
        return self.precedence
    
    def get_value_source(self, key: str) -> Optional[Tuple[Any, ConfigSource]]:
        """
        Get value and its source for a configuration key.
        
        Args:
            key: Configuration key (dot-separated for nested)
            
        Returns:
            Tuple of (value, source) or (None, None) if not found
        """
        # Check sources in reverse precedence order (highest first)
        for source in reversed(self.precedence):
            if source in self._source_configs:
                config = self._source_configs[source]
                value = self._get_nested_value(config, key)
                if value is not None:
                    return value, source
        
        return None, None
    
    def _get_nested_value(self, config: Dict[str, Any], key: str) -> Any:
        """
        Navigate nested dictionary structure using dot notation.
        
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
    
    def get_conflicts(self) -> Dict[str, List[Tuple[ConfigSource, Any]]]:
        """
        Get configuration conflicts between sources.
        
        Returns:
            Dictionary mapping keys to list of (source, value) tuples
        """
        conflicts = {}
        all_keys = set()
        
        # Collect all keys from all sources
        for config in self._source_configs.values():
            flat_config = self._flatten_config(config)
            all_keys.update(flat_config.keys())
        
        # Check each key for conflicts
        for key in all_keys:
            values = []
            for source in self.precedence:
                if source in self._source_configs:
                    value = self._get_nested_value(self._source_configs[source], key)
                    if value is not None:
                        values.append((source, value))
            
            # If multiple sources define different values, it's a conflict
            if len(values) > 1:
                unique_values = set(str(v) for _, v in values)
                if len(unique_values) > 1:
                    conflicts[key] = values
        
        return conflicts
    
    def get_coverage_report(self) -> Dict[str, Any]:
        """
        Get coverage report showing which sources provide which keys.
        
        Returns:
            Coverage report dictionary
        """
        coverage = {}
        
        for source, config in self._source_configs.items():
            flat_config = self._flatten_config(config)
            coverage[source.name] = {
                'total_keys': len(flat_config),
                'keys': list(flat_config.keys()),
                'sample_values': dict(list(flat_config.items())[:5])  # First 5 for preview
            }
        
        return coverage
    
    def get_merge_history(self) -> List[Dict[str, Any]]:
        """
        Get history of merge operations.
        
        Returns:
            List of merge history entries
        """
        return self._merge_history.copy()
    
    def clear_merge_history(self) -> None:
        """Clear merge operation history."""
        self._merge_history.clear()
    
    def _flatten_config(self, config: Dict[str, Any], 
                       parent_key: str = '', separator: str = '.') -> Dict[str, Any]:
        """
        Flatten nested configuration dictionary.
        
        Args:
            config: Nested configuration
            parent_key: Parent key prefix
            separator: Key separator
            
        Returns:
            Flattened dictionary
        """
        items = []
        
        for key, value in config.items():
            new_key = f"{parent_key}{separator}{key}" if parent_key else key
            
            if isinstance(value, dict):
                items.extend(
                    self._flatten_config(value, new_key, separator).items()
                )
            else:
                items.append((new_key, value))
        
        return dict(items)
    
    def _get_timestamp(self) -> float:
        """Get current timestamp."""
        import time
        return time.time()
    
    def validate_precedence(self) -> List[str]:
        """
        Validate precedence configuration.
        
        Returns:
            List of validation issues
        """
        issues = []
        
        # Check for duplicate sources in precedence
        if len(set(self.precedence)) != len(self.precedence):
            issues.append("Duplicate sources in precedence order")
        
        # Check if all loaded sources are in precedence
        loaded_sources = set(self._source_configs.keys())
        precedence_sources = set(self.precedence)
        
        missing = loaded_sources - precedence_sources
        if missing:
            issues.append(f"Loaded sources not in precedence: {missing}")
        
        # Check for circular dependencies in rules
        if self._has_circular_dependencies():
            issues.append("Circular dependencies detected in precedence rules")
        
        return issues
    
    def _has_circular_dependencies(self) -> bool:
        """Check for circular dependencies in precedence rules."""
        # Simple implementation - just check for basic cycles
        # TODO: Implement proper cycle detection if complex rules are added
        return False
    
    def reset(self) -> None:
        """Reset all configurations and history."""
        self._source_configs.clear()
        self._precedence_rules.clear()
        self.clear_merge_history()
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about precedence management.
        
        Returns:
            Statistics dictionary
        """
        total_keys = 0
        for config in self._source_configs.values():
            total_keys += len(self._flatten_config(config))
        
        conflicts = self.get_conflicts()
        
        return {
            'source_count': len(self._source_configs),
            'total_configuration_keys': total_keys,
            'conflict_count': len(conflicts),
            'merge_operations': len(self._merge_history),
            'precedence_order': [s.name for s in self.precedence],
            'custom_rules': len(self._precedence_rules)
        }