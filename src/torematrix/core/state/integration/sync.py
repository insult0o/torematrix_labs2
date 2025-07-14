"""
State synchronization manager for multi-store coordination.
"""

from typing import Dict, Any, List, Optional, Callable, Set
import logging
import time
import threading
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class SyncMode(Enum):
    """State synchronization modes."""
    MANUAL = "manual"
    AUTOMATIC = "automatic"
    SELECTIVE = "selective"


@dataclass
class SyncRule:
    """Rule for selective synchronization."""
    path: str
    direction: str = "bidirectional"  # "bidirectional", "outbound", "inbound"
    transform: Optional[Callable] = None
    condition: Optional[Callable] = None


@dataclass
class SyncEvent:
    """Event representing a synchronization operation."""
    source_store: str
    target_stores: List[str]
    path: str
    value: Any
    timestamp: float = field(default_factory=time.time)
    sync_id: str = field(default="")
    
    def __post_init__(self):
        if not self.sync_id:
            self.sync_id = f"sync_{int(self.timestamp * 1000)}"


class StateSyncManager:
    """
    Manager for synchronizing state between multiple stores.
    
    Supports:
    - Multiple sync modes (manual, automatic, selective)
    - Conflict resolution strategies
    - Sync rules and transformations
    - Sync event tracking and replay
    """
    
    def __init__(self, sync_mode: SyncMode = SyncMode.AUTOMATIC):
        """
        Initialize sync manager.
        
        Args:
            sync_mode: Default synchronization mode
        """
        self.sync_mode = sync_mode
        self.stores: Dict[str, Any] = {}
        self.sync_rules: Dict[str, List[SyncRule]] = {}
        self.sync_history: List[SyncEvent] = []
        self.conflict_resolver: Optional[Callable] = None
        self._sync_lock = threading.RLock()
        self._sync_enabled = True
        self._stats = {
            'total_syncs': 0,
            'successful_syncs': 0,
            'failed_syncs': 0,
            'conflicts_resolved': 0
        }
    
    def register_store(self, name: str, store: Any, rules: Optional[List[SyncRule]] = None):
        """
        Register a store for synchronization.
        
        Args:
            name: Unique name for the store
            store: Store instance
            rules: Sync rules specific to this store
        """
        with self._sync_lock:
            self.stores[name] = store
            if rules:
                self.sync_rules[name] = rules
            
            # Set up middleware for automatic sync
            if self.sync_mode == SyncMode.AUTOMATIC:
                self._setup_auto_sync(name, store)
            
            logger.info(f"Registered store '{name}' for synchronization")
    
    def unregister_store(self, name: str):
        """Unregister a store from synchronization."""
        with self._sync_lock:
            if name in self.stores:
                del self.stores[name]
                if name in self.sync_rules:
                    del self.sync_rules[name]
                logger.info(f"Unregistered store '{name}'")
    
    def add_sync_rule(self, store_name: str, rule: SyncRule):
        """Add a synchronization rule for a store."""
        if store_name not in self.sync_rules:
            self.sync_rules[store_name] = []
        self.sync_rules[store_name].append(rule)
        logger.debug(f"Added sync rule for {store_name}: {rule.path}")
    
    def sync_stores(self, source_store: str, target_stores: Optional[List[str]] = None, 
                   paths: Optional[List[str]] = None):
        """
        Manually synchronize stores.
        
        Args:
            source_store: Name of source store
            target_stores: List of target stores (all others if None)
            paths: Specific paths to sync (all if None)
        """
        if not self._sync_enabled:
            logger.warning("Sync is disabled")
            return
        
        with self._sync_lock:
            if source_store not in self.stores:
                logger.error(f"Source store '{source_store}' not found")
                return
            
            if target_stores is None:
                target_stores = [name for name in self.stores.keys() if name != source_store]
            
            source = self.stores[source_store]
            source_state = source.get_state()
            
            for target_name in target_stores:
                if target_name not in self.stores:
                    logger.warning(f"Target store '{target_name}' not found")
                    continue
                
                try:
                    self._sync_to_target(source_store, target_name, source_state, paths)
                    self._stats['successful_syncs'] += 1
                except Exception as e:
                    logger.error(f"Error syncing to {target_name}: {e}")
                    self._stats['failed_syncs'] += 1
                
                self._stats['total_syncs'] += 1
    
    def _sync_to_target(self, source_name: str, target_name: str, 
                       source_state: Dict[str, Any], paths: Optional[List[str]] = None):
        """Sync state from source to target store."""
        target_store = self.stores[target_name]
        target_state = target_store.get_state()
        
        # Get applicable sync rules
        rules = self.sync_rules.get(source_name, [])
        
        if paths:
            # Sync specific paths
            for path in paths:
                value = self._get_nested_value(source_state, path)
                if value is not None:
                    self._apply_sync(source_name, target_name, path, value, rules)
        else:
            # Sync all applicable paths based on rules
            if rules:
                for rule in rules:
                    if rule.direction in ["bidirectional", "outbound"]:
                        value = self._get_nested_value(source_state, rule.path)
                        if value is not None and self._check_condition(rule, value, source_state):
                            self._apply_sync(source_name, target_name, rule.path, value, [rule])
            else:
                # No rules, sync everything
                self._sync_full_state(source_name, target_name, source_state)
    
    def _apply_sync(self, source_name: str, target_name: str, path: str, 
                   value: Any, rules: List[SyncRule]):
        """Apply synchronization for a specific path."""
        target_store = self.stores[target_name]
        target_state = target_store.get_state()
        target_value = self._get_nested_value(target_state, path)
        
        # Check for conflicts
        if target_value is not None and target_value != value:
            if self.conflict_resolver:
                try:
                    resolved_value = self.conflict_resolver(
                        source_value=value,
                        target_value=target_value,
                        path=path,
                        source_store=source_name,
                        target_store=target_name
                    )
                    value = resolved_value
                    self._stats['conflicts_resolved'] += 1
                except Exception as e:
                    logger.error(f"Conflict resolution failed for {path}: {e}")
                    return
        
        # Apply transformations
        applicable_rule = next((r for r in rules if r.path == path), None)
        if applicable_rule and applicable_rule.transform:
            try:
                value = applicable_rule.transform(value)
            except Exception as e:
                logger.error(f"Transform failed for {path}: {e}")
                return
        
        # Update target store
        action = self._create_update_action(path, value)
        target_store.dispatch(action)
        
        # Record sync event
        sync_event = SyncEvent(
            source_store=source_name,
            target_stores=[target_name],
            path=path,
            value=value
        )
        self.sync_history.append(sync_event)
        
        logger.debug(f"Synced {path} from {source_name} to {target_name}")
    
    def _setup_auto_sync(self, store_name: str, store: Any):
        """Set up automatic synchronization for a store."""
        def sync_middleware(store_instance):
            def middleware(next_dispatch):
                def dispatch(action):
                    result = next_dispatch(action)
                    
                    # Trigger sync after action
                    if self._sync_enabled and self.sync_mode == SyncMode.AUTOMATIC:
                        try:
                            self.sync_stores(store_name)
                        except Exception as e:
                            logger.error(f"Auto-sync failed for {store_name}: {e}")
                    
                    return result
                return dispatch
            return middleware
        
        # Add middleware to store
        if hasattr(store, 'use'):
            store.use(sync_middleware)
    
    def _get_nested_value(self, obj: Dict[str, Any], path: str) -> Any:
        """Get value from nested object using dot notation."""
        keys = path.split('.')
        current = obj
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        
        return current
    
    def _check_condition(self, rule: SyncRule, value: Any, state: Dict[str, Any]) -> bool:
        """Check if sync condition is met."""
        if rule.condition:
            try:
                return rule.condition(value, state)
            except Exception as e:
                logger.error(f"Condition check failed: {e}")
                return False
        return True
    
    def _create_update_action(self, path: str, value: Any):
        """Create an action to update state at path."""
        class UpdateAction:
            def __init__(self, path: str, value: Any):
                self.type = "UPDATE_STATE"
                self.payload = {'path': path, 'value': value}
        
        return UpdateAction(path, value)
    
    def _sync_full_state(self, source_name: str, target_name: str, source_state: Dict[str, Any]):
        """Sync entire state from source to target."""
        target_store = self.stores[target_name]
        
        # Create action to replace entire state
        class ReplaceStateAction:
            def __init__(self, state: Dict[str, Any]):
                self.type = "REPLACE_STATE"
                self.payload = state
        
        action = ReplaceStateAction(source_state)
        target_store.dispatch(action)
        
        logger.debug(f"Full state sync from {source_name} to {target_name}")
    
    def set_conflict_resolver(self, resolver: Callable):
        """Set conflict resolution strategy."""
        self.conflict_resolver = resolver
        logger.debug("Conflict resolver updated")
    
    def enable_sync(self):
        """Enable synchronization."""
        self._sync_enabled = True
        logger.info("State synchronization enabled")
    
    def disable_sync(self):
        """Disable synchronization."""
        self._sync_enabled = False
        logger.info("State synchronization disabled")
    
    def get_sync_stats(self) -> Dict[str, Any]:
        """Get synchronization statistics."""
        return dict(self._stats)
    
    def get_sync_history(self, limit: Optional[int] = None) -> List[SyncEvent]:
        """Get synchronization history."""
        if limit:
            return self.sync_history[-limit:]
        return list(self.sync_history)
    
    def clear_history(self):
        """Clear synchronization history."""
        self.sync_history.clear()
        logger.debug("Sync history cleared")


# Common conflict resolution strategies
def last_writer_wins(source_value, target_value, **kwargs):
    """Conflict resolution: source value always wins."""
    return source_value


def first_writer_wins(source_value, target_value, **kwargs):
    """Conflict resolution: target value always wins."""
    return target_value


def merge_objects(source_value, target_value, **kwargs):
    """Conflict resolution: merge objects if possible."""
    if isinstance(source_value, dict) and isinstance(target_value, dict):
        merged = dict(target_value)
        merged.update(source_value)
        return merged
    return source_value