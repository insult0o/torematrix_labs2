"""
Conflict resolution system for optimistic updates.
"""

from typing import Dict, Any, List, Optional, Callable, Tuple
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
import copy

logger = logging.getLogger(__name__)


class ConflictStrategy(Enum):
    """Strategies for resolving conflicts."""
    LAST_WRITER_WINS = "last_writer_wins"
    FIRST_WRITER_WINS = "first_writer_wins"
    MERGE = "merge"
    MANUAL = "manual"
    CUSTOM = "custom"


@dataclass
class Conflict:
    """Represents a conflict between states."""
    path: str
    local_value: Any
    remote_value: Any
    base_value: Any = None
    timestamp: float = field(default_factory=time.time)
    resolved: bool = False
    resolution: Any = None
    strategy_used: Optional[ConflictStrategy] = None
    
    @property
    def age(self) -> float:
        """Get age of conflict in seconds."""
        return time.time() - self.timestamp


@dataclass
class ConflictResolution:
    """Result of conflict resolution."""
    conflict: Conflict
    resolved_value: Any
    strategy: ConflictStrategy
    success: bool
    error: Optional[str] = None


class ConflictResolver:
    """
    Resolves conflicts between optimistic updates and actual state.
    
    Features:
    - Multiple resolution strategies
    - Custom conflict handlers
    - Three-way merge capabilities
    - Conflict tracking and analysis
    """
    
    def __init__(self, default_strategy: ConflictStrategy = ConflictStrategy.LAST_WRITER_WINS):
        """
        Initialize conflict resolver.
        
        Args:
            default_strategy: Default strategy for resolving conflicts
        """
        self.default_strategy = default_strategy
        self._custom_handlers: Dict[str, Callable] = {}
        self._path_strategies: Dict[str, ConflictStrategy] = {}
        self._conflict_history: List[Conflict] = []
        
        self._stats = {
            'conflicts_detected': 0,
            'conflicts_resolved': 0,
            'conflicts_failed': 0,
            'automatic_resolutions': 0,
            'manual_resolutions': 0,
        }
    
    def detect_conflicts(self, 
                        local_state: Dict[str, Any],
                        remote_state: Dict[str, Any],
                        base_state: Optional[Dict[str, Any]] = None) -> List[Conflict]:
        """
        Detect conflicts between local and remote states.
        
        Args:
            local_state: Local (optimistic) state
            remote_state: Remote (actual) state
            base_state: Base state for three-way comparison
            
        Returns:
            List of detected conflicts
        """
        conflicts = []
        
        # Flatten states for comparison
        local_flat = self._flatten_dict(local_state)
        remote_flat = self._flatten_dict(remote_state)
        base_flat = self._flatten_dict(base_state) if base_state else {}
        
        # Find all paths that exist in either state
        all_paths = set(local_flat.keys()) | set(remote_flat.keys())
        
        for path in all_paths:
            local_value = local_flat.get(path)
            remote_value = remote_flat.get(path)
            base_value = base_flat.get(path)
            
            # Check for conflict
            if self._is_conflict(local_value, remote_value, base_value):
                conflict = Conflict(
                    path=path,
                    local_value=local_value,
                    remote_value=remote_value,
                    base_value=base_value
                )
                
                conflicts.append(conflict)
                self._conflict_history.append(conflict)
                self._stats['conflicts_detected'] += 1
                
                logger.debug(f"Conflict detected at path: {path}")
        
        return conflicts
    
    def resolve_conflicts(self, conflicts: List[Conflict]) -> List[ConflictResolution]:
        """
        Resolve a list of conflicts.
        
        Args:
            conflicts: List of conflicts to resolve
            
        Returns:
            List of conflict resolutions
        """
        resolutions = []
        
        for conflict in conflicts:
            resolution = self.resolve_conflict(conflict)
            resolutions.append(resolution)
            
            if resolution.success:
                conflict.resolved = True
                conflict.resolution = resolution.resolved_value
                conflict.strategy_used = resolution.strategy
                self._stats['conflicts_resolved'] += 1
            else:
                self._stats['conflicts_failed'] += 1
        
        return resolutions
    
    def resolve_conflict(self, conflict: Conflict) -> ConflictResolution:
        """
        Resolve a single conflict.
        
        Args:
            conflict: Conflict to resolve
            
        Returns:
            Conflict resolution result
        """
        try:
            # Check for custom handler
            if conflict.path in self._custom_handlers:
                return self._apply_custom_handler(conflict)
            
            # Check for path-specific strategy
            strategy = self._get_strategy_for_path(conflict.path)
            
            # Apply resolution strategy
            if strategy == ConflictStrategy.LAST_WRITER_WINS:
                return self._resolve_last_writer_wins(conflict)
            elif strategy == ConflictStrategy.FIRST_WRITER_WINS:
                return self._resolve_first_writer_wins(conflict)
            elif strategy == ConflictStrategy.MERGE:
                return self._resolve_merge(conflict)
            elif strategy == ConflictStrategy.MANUAL:
                return self._resolve_manual(conflict)
            else:
                raise ValueError(f"Unknown strategy: {strategy}")
                
        except Exception as e:
            logger.error(f"Conflict resolution failed for {conflict.path}: {e}")
            return ConflictResolution(
                conflict=conflict,
                resolved_value=conflict.remote_value,  # Fallback to remote
                strategy=self.default_strategy,
                success=False,
                error=str(e)
            )
    
    def _is_conflict(self, local_value: Any, remote_value: Any, base_value: Any = None) -> bool:
        """Check if values represent a conflict."""
        # No conflict if values are the same
        if local_value == remote_value:
            return False
        
        # No conflict if one value is None (creation/deletion)
        if local_value is None or remote_value is None:
            return False
        
        # Three-way conflict detection
        if base_value is not None:
            # No conflict if only one side changed
            if local_value == base_value and remote_value != base_value:
                return False
            if remote_value == base_value and local_value != base_value:
                return False
        
        # Conflict exists
        return True
    
    def _get_strategy_for_path(self, path: str) -> ConflictStrategy:
        """Get resolution strategy for a specific path."""
        # Check for exact path match
        if path in self._path_strategies:
            return self._path_strategies[path]
        
        # Check for pattern matches
        for pattern, strategy in self._path_strategies.items():
            if pattern in path or path.startswith(pattern):
                return strategy
        
        return self.default_strategy
    
    def _apply_custom_handler(self, conflict: Conflict) -> ConflictResolution:
        """Apply custom conflict handler."""
        handler = self._custom_handlers[conflict.path]
        
        try:
            resolved_value = handler(conflict.local_value, conflict.remote_value, conflict.base_value)
            
            return ConflictResolution(
                conflict=conflict,
                resolved_value=resolved_value,
                strategy=ConflictStrategy.CUSTOM,
                success=True
            )
            
        except Exception as e:
            return ConflictResolution(
                conflict=conflict,
                resolved_value=conflict.remote_value,
                strategy=ConflictStrategy.CUSTOM,
                success=False,
                error=str(e)
            )
    
    def _resolve_last_writer_wins(self, conflict: Conflict) -> ConflictResolution:
        """Resolve using last writer wins strategy."""
        return ConflictResolution(
            conflict=conflict,
            resolved_value=conflict.remote_value,  # Remote is "last" in this context
            strategy=ConflictStrategy.LAST_WRITER_WINS,
            success=True
        )
    
    def _resolve_first_writer_wins(self, conflict: Conflict) -> ConflictResolution:
        """Resolve using first writer wins strategy."""
        return ConflictResolution(
            conflict=conflict,
            resolved_value=conflict.local_value,  # Local was "first" optimistic update
            strategy=ConflictStrategy.FIRST_WRITER_WINS,
            success=True
        )
    
    def _resolve_merge(self, conflict: Conflict) -> ConflictResolution:
        """Resolve using merge strategy."""
        try:
            merged_value = self._merge_values(conflict.local_value, conflict.remote_value, conflict.base_value)
            
            return ConflictResolution(
                conflict=conflict,
                resolved_value=merged_value,
                strategy=ConflictStrategy.MERGE,
                success=True
            )
            
        except Exception as e:
            # Fallback to last writer wins
            return ConflictResolution(
                conflict=conflict,
                resolved_value=conflict.remote_value,
                strategy=ConflictStrategy.MERGE,
                success=False,
                error=f"Merge failed: {e}"
            )
    
    def _resolve_manual(self, conflict: Conflict) -> ConflictResolution:
        """Resolve using manual strategy (requires external intervention)."""
        # For now, fallback to remote value
        # In a real implementation, this would queue for manual resolution
        return ConflictResolution(
            conflict=conflict,
            resolved_value=conflict.remote_value,
            strategy=ConflictStrategy.MANUAL,
            success=True
        )
    
    def _merge_values(self, local_value: Any, remote_value: Any, base_value: Any = None) -> Any:
        """Merge conflicting values."""
        # Dictionary merge
        if isinstance(local_value, dict) and isinstance(remote_value, dict):
            return self._merge_dictionaries(local_value, remote_value, base_value)
        
        # List merge
        elif isinstance(local_value, list) and isinstance(remote_value, list):
            return self._merge_lists(local_value, remote_value, base_value)
        
        # String merge (if both are strings)
        elif isinstance(local_value, str) and isinstance(remote_value, str):
            return self._merge_strings(local_value, remote_value, base_value)
        
        # Numeric merge
        elif isinstance(local_value, (int, float)) and isinstance(remote_value, (int, float)):
            return self._merge_numbers(local_value, remote_value, base_value)
        
        # Fallback to remote value
        else:
            return remote_value
    
    def _merge_dictionaries(self, local: Dict[str, Any], remote: Dict[str, Any], base: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Merge dictionary values."""
        merged = dict(remote)  # Start with remote
        
        if base:
            # Three-way merge
            for key in set(local.keys()) | set(remote.keys()) | set(base.keys()):
                local_val = local.get(key)
                remote_val = remote.get(key)
                base_val = base.get(key) if base else None
                
                # Only local changed
                if local_val != base_val and remote_val == base_val:
                    merged[key] = local_val
                # Both changed differently - recurse
                elif local_val != base_val and remote_val != base_val and local_val != remote_val:
                    if isinstance(local_val, dict) and isinstance(remote_val, dict):
                        merged[key] = self._merge_dictionaries(local_val, remote_val, base_val)
                    else:
                        merged[key] = remote_val  # Prefer remote
        else:
            # Two-way merge - add local keys that don't conflict
            for key, value in local.items():
                if key not in remote:
                    merged[key] = value
        
        return merged
    
    def _merge_lists(self, local: List[Any], remote: List[Any], base: Optional[List[Any]] = None) -> List[Any]:
        """Merge list values."""
        if base:
            # Three-way merge - combine unique additions
            local_additions = set(local) - set(base)
            remote_additions = set(remote) - set(base)
            base_items = set(base)
            
            # Start with base, add unique items
            merged = list(base_items | local_additions | remote_additions)
            return merged
        else:
            # Two-way merge - combine unique items
            return list(set(local) | set(remote))
    
    def _merge_strings(self, local: str, remote: str, base: Optional[str] = None) -> str:
        """Merge string values."""
        if base:
            # Simple three-way text merge
            if local == base:
                return remote
            elif remote == base:
                return local
            else:
                # Both changed - combine if possible
                return f"{local}\n{remote}"
        else:
            # Two-way merge - combine
            return f"{local}\n{remote}"
    
    def _merge_numbers(self, local: float, remote: float, base: Optional[float] = None) -> float:
        """Merge numeric values."""
        if base is not None:
            # Take the larger change
            local_change = abs(local - base)
            remote_change = abs(remote - base)
            return local if local_change > remote_change else remote
        else:
            # Average the values
            return (local + remote) / 2
    
    def register_custom_handler(self, path: str, handler: Callable):
        """Register a custom conflict handler for a specific path."""
        self._custom_handlers[path] = handler
        logger.debug(f"Registered custom conflict handler for path: {path}")
    
    def set_strategy_for_path(self, path: str, strategy: ConflictStrategy):
        """Set resolution strategy for a specific path."""
        self._path_strategies[path] = strategy
        logger.debug(f"Set strategy {strategy} for path: {path}")
    
    def apply_resolutions_to_state(self, 
                                  state: Dict[str, Any],
                                  resolutions: List[ConflictResolution]) -> Dict[str, Any]:
        """Apply conflict resolutions to a state."""
        resolved_state = copy.deepcopy(state)
        
        for resolution in resolutions:
            if resolution.success:
                self._set_nested_value(resolved_state, resolution.conflict.path, resolution.resolved_value)
        
        return resolved_state
    
    def get_conflict_stats(self) -> Dict[str, Any]:
        """Get conflict resolution statistics."""
        return {
            **self._stats,
            'resolution_rate': (
                self._stats['conflicts_resolved'] / max(self._stats['conflicts_detected'], 1)
            ),
            'pending_conflicts': len([c for c in self._conflict_history if not c.resolved]),
        }
    
    def get_unresolved_conflicts(self) -> List[Conflict]:
        """Get list of unresolved conflicts."""
        return [c for c in self._conflict_history if not c.resolved]
    
    def clear_conflict_history(self):
        """Clear conflict history."""
        self._conflict_history.clear()
        logger.debug("Cleared conflict history")
    
    # Utility methods
    def _flatten_dict(self, d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
        """Flatten nested dictionary."""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)
    
    def _set_nested_value(self, obj: Dict[str, Any], path: str, value: Any):
        """Set value in nested object using dot notation."""
        keys = path.split('.')
        current = obj
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value


# Common conflict handlers
def prefer_larger_number(local_val, remote_val, base_val=None):
    """Conflict handler that prefers larger numeric values."""
    if isinstance(local_val, (int, float)) and isinstance(remote_val, (int, float)):
        return max(local_val, remote_val)
    return remote_val


def prefer_longer_string(local_val, remote_val, base_val=None):
    """Conflict handler that prefers longer string values."""
    if isinstance(local_val, str) and isinstance(remote_val, str):
        return local_val if len(local_val) > len(remote_val) else remote_val
    return remote_val


def concatenate_strings(local_val, remote_val, base_val=None):
    """Conflict handler that concatenates string values."""
    if isinstance(local_val, str) and isinstance(remote_val, str):
        return f"{local_val} | {remote_val}"
    return remote_val


def merge_lists_unique(local_val, remote_val, base_val=None):
    """Conflict handler that merges lists with unique values."""
    if isinstance(local_val, list) and isinstance(remote_val, list):
        return list(set(local_val) | set(remote_val))
    return remote_val