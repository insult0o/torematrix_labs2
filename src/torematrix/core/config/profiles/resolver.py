"""
Configuration profile resolution.

This module provides utilities for resolving and merging configuration
profiles with different strategies and conflict resolution.
"""

from typing import Dict, Any, List, Optional, Union, Callable
import copy
from enum import Enum
from ..types import ConfigDict
from ..exceptions import ConfigurationError


class MergeStrategy(Enum):
    """Strategies for merging configuration values."""
    REPLACE = "replace"      # Replace entire value
    MERGE = "merge"          # Deep merge dictionaries
    APPEND = "append"        # Append to lists
    PREPEND = "prepend"      # Prepend to lists
    UNION = "union"          # Union of sets/lists (unique values)


class ConflictResolution(Enum):
    """Strategies for resolving configuration conflicts."""
    CHILD_WINS = "child_wins"    # Child profile overrides parent
    PARENT_WINS = "parent_wins"  # Parent profile takes precedence
    ERROR = "error"              # Raise error on conflict
    MERGE = "merge"              # Attempt to merge conflicting values


class ProfileResolver:
    """
    Resolve configuration profiles with customizable merge strategies.
    
    Features:
    - Multiple merge strategies
    - Conflict resolution
    - Type-aware merging
    - Custom merge functions
    """
    
    def __init__(
        self,
        default_strategy: MergeStrategy = MergeStrategy.MERGE,
        conflict_resolution: ConflictResolution = ConflictResolution.CHILD_WINS
    ):
        """
        Initialize resolver.
        
        Args:
            default_strategy: Default merge strategy
            conflict_resolution: How to resolve conflicts
        """
        self.default_strategy = default_strategy
        self.conflict_resolution = conflict_resolution
        self.custom_mergers: Dict[str, Callable] = {}
        self.field_strategies: Dict[str, MergeStrategy] = {}
    
    def merge_config(
        self,
        base: ConfigDict,
        override: ConfigDict,
        strategy: Optional[MergeStrategy] = None
    ) -> ConfigDict:
        """
        Merge override configuration into base configuration.
        
        Args:
            base: Base configuration
            override: Override configuration
            strategy: Merge strategy (uses default if None)
            
        Returns:
            Merged configuration
        """
        if strategy is None:
            strategy = self.default_strategy
        
        result = copy.deepcopy(base)
        
        for key, value in override.items():
            if key in result:
                # Handle conflict
                result[key] = self._merge_values(
                    key, result[key], value, strategy
                )
            else:
                # No conflict, just add
                result[key] = copy.deepcopy(value)
        
        return result
    
    def merge_multiple(
        self,
        configs: List[ConfigDict],
        strategy: Optional[MergeStrategy] = None
    ) -> ConfigDict:
        """
        Merge multiple configurations in order.
        
        Args:
            configs: List of configurations to merge
            strategy: Merge strategy
            
        Returns:
            Merged configuration
        """
        if not configs:
            return {}
        
        result = copy.deepcopy(configs[0])
        
        for config in configs[1:]:
            result = self.merge_config(result, config, strategy)
        
        return result
    
    def set_field_strategy(self, field_path: str, strategy: MergeStrategy) -> None:
        """
        Set merge strategy for a specific field path.
        
        Args:
            field_path: Dot-separated field path
            strategy: Merge strategy for this field
        """
        self.field_strategies[field_path] = strategy
    
    def set_custom_merger(self, field_path: str, merger: Callable) -> None:
        """
        Set custom merge function for a specific field path.
        
        Args:
            field_path: Dot-separated field path
            merger: Custom merge function (base_value, override_value) -> merged_value
        """
        self.custom_mergers[field_path] = merger
    
    def _merge_values(
        self,
        key: str,
        base_value: Any,
        override_value: Any,
        strategy: MergeStrategy,
        path: str = ""
    ) -> Any:
        """Merge two values according to strategy."""
        current_path = f"{path}.{key}" if path else key
        
        # Check for custom merger
        if current_path in self.custom_mergers:
            return self.custom_mergers[current_path](base_value, override_value)
        
        # Check for field-specific strategy
        field_strategy = self.field_strategies.get(current_path, strategy)
        
        # Handle based on strategy
        if field_strategy == MergeStrategy.REPLACE:
            return copy.deepcopy(override_value)
        
        elif field_strategy == MergeStrategy.MERGE:
            return self._deep_merge(base_value, override_value, current_path)
        
        elif field_strategy == MergeStrategy.APPEND:
            return self._append_values(base_value, override_value)
        
        elif field_strategy == MergeStrategy.PREPEND:
            return self._prepend_values(base_value, override_value)
        
        elif field_strategy == MergeStrategy.UNION:
            return self._union_values(base_value, override_value)
        
        else:
            # Default to replace
            return copy.deepcopy(override_value)
    
    def _deep_merge(self, base_value: Any, override_value: Any, path: str) -> Any:
        """Perform deep merge of values."""
        # If types don't match, handle based on conflict resolution
        if type(base_value) != type(override_value):
            return self._resolve_type_conflict(base_value, override_value, path)
        
        # Both are dictionaries - merge recursively
        if isinstance(base_value, dict) and isinstance(override_value, dict):
            result = copy.deepcopy(base_value)
            
            for key, value in override_value.items():
                if key in result:
                    result[key] = self._merge_values(
                        key, result[key], value, MergeStrategy.MERGE, path
                    )
                else:
                    result[key] = copy.deepcopy(value)
            
            return result
        
        # Both are lists - merge based on strategy
        elif isinstance(base_value, list) and isinstance(override_value, list):
            return self._merge_lists(base_value, override_value)
        
        # For other types, use conflict resolution
        else:
            return self._resolve_value_conflict(base_value, override_value, path)
    
    def _append_values(self, base_value: Any, override_value: Any) -> Any:
        """Append override value to base value."""
        if isinstance(base_value, list):
            result = copy.deepcopy(base_value)
            if isinstance(override_value, list):
                result.extend(override_value)
            else:
                result.append(override_value)
            return result
        else:
            # Convert to list and append
            return [base_value, override_value]
    
    def _prepend_values(self, base_value: Any, override_value: Any) -> Any:
        """Prepend override value to base value."""
        if isinstance(base_value, list):
            result = copy.deepcopy(base_value)
            if isinstance(override_value, list):
                result = override_value + result
            else:
                result.insert(0, override_value)
            return result
        else:
            # Convert to list and prepend
            return [override_value, base_value]
    
    def _union_values(self, base_value: Any, override_value: Any) -> Any:
        """Create union of base and override values."""
        if isinstance(base_value, list) and isinstance(override_value, list):
            # Create list with unique values, preserving order
            seen = set()
            result = []
            
            for item in base_value + override_value:
                # Handle unhashable types
                try:
                    if item not in seen:
                        seen.add(item)
                        result.append(item)
                except TypeError:
                    # Item is unhashable, just add it
                    if item not in result:
                        result.append(item)
            
            return result
        
        elif isinstance(base_value, set) and isinstance(override_value, set):
            return base_value.union(override_value)
        
        else:
            # Convert to list and create union
            base_list = [base_value] if not isinstance(base_value, list) else base_value
            override_list = [override_value] if not isinstance(override_value, list) else override_value
            return self._union_values(base_list, override_list)
    
    def _merge_lists(self, base_list: List[Any], override_list: List[Any]) -> List[Any]:
        """Merge two lists based on default list merge strategy."""
        # For now, default to append strategy for lists
        return base_list + override_list
    
    def _resolve_type_conflict(self, base_value: Any, override_value: Any, path: str) -> Any:
        """Resolve conflict when values have different types."""
        if self.conflict_resolution == ConflictResolution.CHILD_WINS:
            return copy.deepcopy(override_value)
        elif self.conflict_resolution == ConflictResolution.PARENT_WINS:
            return copy.deepcopy(base_value)
        elif self.conflict_resolution == ConflictResolution.ERROR:
            raise ConfigurationError(
                f"Type conflict at {path}: {type(base_value)} vs {type(override_value)}"
            )
        else:  # MERGE
            # Try to find a compatible merge
            if isinstance(base_value, (int, float)) and isinstance(override_value, (int, float)):
                return override_value  # Numbers: use override
            elif isinstance(base_value, str) and isinstance(override_value, str):
                return override_value  # Strings: use override
            else:
                return copy.deepcopy(override_value)  # Default to override
    
    def _resolve_value_conflict(self, base_value: Any, override_value: Any, path: str) -> Any:
        """Resolve conflict when values are different but same type."""
        if self.conflict_resolution == ConflictResolution.CHILD_WINS:
            return copy.deepcopy(override_value)
        elif self.conflict_resolution == ConflictResolution.PARENT_WINS:
            return copy.deepcopy(base_value)
        elif self.conflict_resolution == ConflictResolution.ERROR:
            raise ConfigurationError(
                f"Value conflict at {path}: {base_value} vs {override_value}"
            )
        else:  # MERGE
            return copy.deepcopy(override_value)  # Default to override
    
    def validate_merge_result(self, result: ConfigDict) -> List[str]:
        """
        Validate the result of a merge operation.
        
        Args:
            result: Merged configuration
            
        Returns:
            List of validation errors
        """
        errors = []
        
        # Check for empty required fields
        if not result:
            errors.append("Merged configuration is empty")
        
        # Additional validation can be added here
        # For example, checking for required fields, valid values, etc.
        
        return errors
    
    def get_merge_trace(
        self,
        base: ConfigDict,
        override: ConfigDict
    ) -> Dict[str, Any]:
        """
        Get detailed trace of merge operation.
        
        Args:
            base: Base configuration
            override: Override configuration
            
        Returns:
            Merge trace information
        """
        trace = {
            "conflicts": [],
            "additions": [],
            "unchanged": [],
            "strategies_used": {}
        }
        
        # Analyze what would happen in merge
        for key, value in override.items():
            if key in base:
                if base[key] != value:
                    trace["conflicts"].append({
                        "field": key,
                        "base_value": base[key],
                        "override_value": value,
                        "strategy": self.field_strategies.get(key, self.default_strategy).value
                    })
                else:
                    trace["unchanged"].append(key)
            else:
                trace["additions"].append(key)
        
        return trace