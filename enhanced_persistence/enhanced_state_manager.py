#!/usr/bin/env python3
"""
Enhanced State Manager for TORE Matrix Labs V1

This module provides centralized state management with V2 patterns for the V1 system,
enhancing the existing DocumentStateManager with modern state management capabilities
while maintaining backward compatibility.
"""

import logging
import threading
import json
import pickle
import time
from typing import Dict, Any, Optional, List, Set, Callable, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
from collections import defaultdict, deque

try:
    # Try to import V1 components for integration
    from tore_matrix_labs.ui.components.document_state_manager import DocumentStateManager
    from tore_matrix_labs.core.area_storage_manager import AreaStorageManager
    V1_AVAILABLE = True
except ImportError:
    V1_AVAILABLE = False


class StateCategory(Enum):
    """Categories of state for organization."""
    DOCUMENT = "document"
    PROJECT = "project"
    UI = "ui"
    VALIDATION = "validation"
    PROCESSING = "processing"
    USER_PREFERENCES = "user_preferences"
    SYSTEM = "system"
    TEMPORARY = "temporary"


class PersistenceLevel(Enum):
    """Levels of persistence for different state types."""
    MEMORY_ONLY = "memory_only"
    SESSION = "session"
    PROJECT = "project" 
    GLOBAL = "global"
    PERMANENT = "permanent"


@dataclass
class ComponentState:
    """State container for a component."""
    
    component_id: str
    category: StateCategory
    persistence_level: PersistenceLevel
    
    # State data
    state_data: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)
    version: int = 1
    
    # Change tracking
    dirty: bool = False
    last_saved: Optional[datetime] = None
    change_history: deque = field(default_factory=lambda: deque(maxlen=50))
    
    def update_state(self, updates: Dict[str, Any]):
        """Update state with change tracking."""
        old_state = self.state_data.copy()
        self.state_data.update(updates)
        
        # Track changes
        self.dirty = True
        self.modified_at = datetime.now()
        self.version += 1
        
        # Add to change history
        change_record = {
            'timestamp': self.modified_at,
            'version': self.version,
            'changes': updates,
            'old_values': {k: old_state.get(k) for k in updates.keys()}
        }
        self.change_history.append(change_record)
    
    def get_state(self, key: Optional[str] = None, default: Any = None) -> Any:
        """Get state value or entire state."""
        if key is None:
            return self.state_data.copy()
        return self.state_data.get(key, default)
    
    def mark_clean(self):
        """Mark state as saved/clean."""
        self.dirty = False
        self.last_saved = datetime.now()
    
    def is_dirty(self) -> bool:
        """Check if state has unsaved changes."""
        return self.dirty
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'component_id': self.component_id,
            'category': self.category.value,
            'persistence_level': self.persistence_level.value,
            'state_data': self.state_data,
            'created_at': self.created_at.isoformat(),
            'modified_at': self.modified_at.isoformat(),
            'version': self.version,
            'dirty': self.dirty,
            'last_saved': self.last_saved.isoformat() if self.last_saved else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ComponentState':
        """Create from dictionary."""
        state = cls(
            component_id=data['component_id'],
            category=StateCategory(data['category']),
            persistence_level=PersistenceLevel(data['persistence_level']),
            state_data=data.get('state_data', {}),
            version=data.get('version', 1),
            dirty=data.get('dirty', False)
        )
        
        # Parse timestamps
        if 'created_at' in data:
            state.created_at = datetime.fromisoformat(data['created_at'])
        if 'modified_at' in data:
            state.modified_at = datetime.fromisoformat(data['modified_at'])
        if data.get('last_saved'):
            state.last_saved = datetime.fromisoformat(data['last_saved'])
        
        return state


class EnhancedStateManager:
    """
    Enhanced state manager with V2 patterns for V1 system.
    
    Provides centralized state management while integrating with existing
    V1 state managers (DocumentStateManager, AreaStorageManager).
    """
    
    def __init__(self, storage_dir: Optional[Path] = None):
        """Initialize the enhanced state manager."""
        self.logger = logging.getLogger(__name__)
        
        # Storage configuration
        self.storage_dir = storage_dir or Path.home() / '.tore_matrix_labs' / 'state'
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # State storage
        self.component_states: Dict[str, ComponentState] = {}
        self.state_lock = threading.RLock()
        
        # State change tracking
        self.change_listeners: Dict[str, List[Callable]] = defaultdict(list)
        self.global_listeners: List[Callable] = []
        
        # Integration with V1 state managers
        self.v1_document_manager: Optional[DocumentStateManager] = None
        self.v1_area_manager: Optional[AreaStorageManager] = None
        
        # Performance and caching
        self.state_cache: Dict[str, Any] = {}
        self.cache_timeout = 300  # 5 minutes
        self.last_cache_cleanup = time.time()
        
        # Auto-save configuration
        self.auto_save_enabled = True
        self.auto_save_interval = 60  # seconds
        self.last_auto_save = time.time()
        
        # Statistics
        self.stats = {
            'state_updates': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'saves_performed': 0,
            'loads_performed': 0
        }
        
        # Load existing state
        self._load_persistent_state()
        
        # Start background maintenance
        self._start_maintenance_thread()
        
        self.logger.info("Enhanced state manager initialized")
    
    def integrate_v1_managers(self, 
                             document_manager: Optional[Any] = None,
                             area_manager: Optional[Any] = None):
        """Integrate with existing V1 state managers."""
        if V1_AVAILABLE:
            self.v1_document_manager = document_manager
            self.v1_area_manager = area_manager
            
            # Set up synchronization
            if document_manager:
                self._setup_document_manager_sync()
            if area_manager:
                self._setup_area_manager_sync()
            
            self.logger.info("Integrated with V1 state managers")
    
    def register_component(self,
                          component_id: str,
                          category: StateCategory,
                          persistence_level: PersistenceLevel = PersistenceLevel.SESSION,
                          initial_state: Optional[Dict[str, Any]] = None) -> ComponentState:
        """
        Register a component for state management.
        
        Args:
            component_id: Unique identifier for the component
            category: State category for organization
            persistence_level: How persistently to store the state
            initial_state: Initial state data
            
        Returns:
            ComponentState object
        """
        with self.state_lock:
            if component_id in self.component_states:
                # Update existing component
                component_state = self.component_states[component_id]
                if initial_state:
                    component_state.update_state(initial_state)
            else:
                # Create new component state
                component_state = ComponentState(
                    component_id=component_id,
                    category=category,
                    persistence_level=persistence_level,
                    state_data=initial_state or {}
                )
                self.component_states[component_id] = component_state
            
            self.logger.debug(f"Registered component: {component_id}")
            return component_state
    
    def update_component_state(self,
                              component_id: str,
                              updates: Dict[str, Any],
                              notify_listeners: bool = True) -> bool:
        """
        Update component state.
        
        Args:
            component_id: Component to update
            updates: State updates
            notify_listeners: Whether to notify change listeners
            
        Returns:
            True if updated successfully
        """
        with self.state_lock:
            if component_id not in self.component_states:
                self.logger.warning(f"Component {component_id} not registered")
                return False
            
            component_state = self.component_states[component_id]
            old_state = component_state.get_state()
            
            # Update state
            component_state.update_state(updates)
            self.stats['state_updates'] += 1
            
            # Invalidate cache
            if component_id in self.state_cache:
                del self.state_cache[component_id]
            
            # Notify listeners
            if notify_listeners:
                self._notify_state_change(component_id, old_state, component_state.get_state())
            
            # Sync with V1 managers if applicable
            self._sync_with_v1_managers(component_id, updates)
            
            self.logger.debug(f"Updated state for {component_id}")
            return True
    
    def get_component_state(self,
                           component_id: str,
                           key: Optional[str] = None,
                           default: Any = None,
                           use_cache: bool = True) -> Any:
        """
        Get component state.
        
        Args:
            component_id: Component to get state for
            key: Specific key to get (None for entire state)
            default: Default value if not found
            use_cache: Whether to use cached values
            
        Returns:
            State value or default
        """
        # Check cache first
        cache_key = f"{component_id}_{key}" if key else component_id
        if use_cache and cache_key in self.state_cache:
            self.stats['cache_hits'] += 1
            return self.state_cache[cache_key]
        
        self.stats['cache_misses'] += 1
        
        with self.state_lock:
            if component_id not in self.component_states:
                return default
            
            component_state = self.component_states[component_id]
            value = component_state.get_state(key, default)
            
            # Cache the value
            if use_cache:
                self.state_cache[cache_key] = value
            
            return value
    
    def get_states_by_category(self, category: StateCategory) -> Dict[str, ComponentState]:
        """Get all component states in a category."""
        with self.state_lock:
            return {
                comp_id: state for comp_id, state in self.component_states.items()
                if state.category == category
            }
    
    def save_component_state(self, component_id: str) -> bool:
        """Save a specific component's state to disk."""
        with self.state_lock:
            if component_id not in self.component_states:
                return False
            
            component_state = self.component_states[component_id]
            
            # Only save if persistence level allows it
            if component_state.persistence_level == PersistenceLevel.MEMORY_ONLY:
                return True  # Success but no actual save
            
            try:
                # Determine save path based on persistence level
                if component_state.persistence_level in [PersistenceLevel.GLOBAL, PersistenceLevel.PERMANENT]:
                    save_path = self.storage_dir / f"{component_id}_state.json"
                else:
                    # Session or project level - save to temporary location
                    temp_dir = self.storage_dir / "temp"
                    temp_dir.mkdir(exist_ok=True)
                    save_path = temp_dir / f"{component_id}_state.json"
                
                # Save state
                with open(save_path, 'w') as f:
                    json.dump(component_state.to_dict(), f, indent=2)
                
                component_state.mark_clean()
                self.stats['saves_performed'] += 1
                
                self.logger.debug(f"Saved state for {component_id}")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to save state for {component_id}: {e}")
                return False
    
    def load_component_state(self, component_id: str) -> bool:
        """Load a specific component's state from disk."""
        try:
            # Try different save locations
            save_paths = [
                self.storage_dir / f"{component_id}_state.json",
                self.storage_dir / "temp" / f"{component_id}_state.json"
            ]
            
            for save_path in save_paths:
                if save_path.exists():
                    with open(save_path, 'r') as f:
                        state_data = json.load(f)
                    
                    # Create component state from loaded data
                    component_state = ComponentState.from_dict(state_data)
                    
                    with self.state_lock:
                        self.component_states[component_id] = component_state
                    
                    self.stats['loads_performed'] += 1
                    self.logger.debug(f"Loaded state for {component_id}")
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to load state for {component_id}: {e}")
            return False
    
    def save_all_dirty_states(self) -> int:
        """Save all components with dirty state."""
        saved_count = 0
        
        with self.state_lock:
            dirty_components = [
                comp_id for comp_id, state in self.component_states.items()
                if state.is_dirty()
            ]
        
        for component_id in dirty_components:
            if self.save_component_state(component_id):
                saved_count += 1
        
        self.last_auto_save = time.time()
        self.logger.debug(f"Auto-saved {saved_count} dirty states")
        return saved_count
    
    def create_state_snapshot(self, components: Optional[List[str]] = None) -> Dict[str, Any]:
        """Create a snapshot of current state."""
        snapshot = {
            'timestamp': datetime.now().isoformat(),
            'version': '2.0.0',
            'components': {}
        }
        
        with self.state_lock:
            target_components = components or list(self.component_states.keys())
            
            for component_id in target_components:
                if component_id in self.component_states:
                    snapshot['components'][component_id] = self.component_states[component_id].to_dict()
        
        return snapshot
    
    def restore_state_snapshot(self, snapshot: Dict[str, Any]) -> bool:
        """Restore state from a snapshot."""
        try:
            with self.state_lock:
                for component_id, state_data in snapshot.get('components', {}).items():
                    component_state = ComponentState.from_dict(state_data)
                    self.component_states[component_id] = component_state
                    
                    # Clear cache for this component
                    cache_keys = [k for k in self.state_cache.keys() if k.startswith(component_id)]
                    for key in cache_keys:
                        del self.state_cache[key]
            
            self.logger.info(f"Restored state snapshot with {len(snapshot.get('components', {}))} components")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to restore state snapshot: {e}")
            return False
    
    def register_change_listener(self,
                                component_id: str,
                                callback: Callable[[str, Dict[str, Any], Dict[str, Any]], None]):
        """Register a callback for state changes."""
        self.change_listeners[component_id].append(callback)
        self.logger.debug(f"Registered change listener for {component_id}")
    
    def register_global_listener(self,
                                callback: Callable[[str, Dict[str, Any], Dict[str, Any]], None]):
        """Register a callback for all state changes."""
        self.global_listeners.append(callback)
        self.logger.debug("Registered global change listener")
    
    def _notify_state_change(self, component_id: str, old_state: Dict[str, Any], new_state: Dict[str, Any]):
        """Notify listeners of state changes."""
        # Component-specific listeners
        for callback in self.change_listeners.get(component_id, []):
            try:
                callback(component_id, old_state, new_state)
            except Exception as e:
                self.logger.error(f"Error in change listener for {component_id}: {e}")
        
        # Global listeners
        for callback in self.global_listeners:
            try:
                callback(component_id, old_state, new_state)
            except Exception as e:
                self.logger.error(f"Error in global change listener: {e}")
    
    def _setup_document_manager_sync(self):
        """Set up synchronization with V1 DocumentStateManager."""
        if not self.v1_document_manager:
            return
        
        # Register component for document state
        self.register_component(
            "v1_document_manager",
            StateCategory.DOCUMENT,
            PersistenceLevel.SESSION
        )
        
        # TODO: Set up signal connections to sync state changes
        self.logger.debug("Set up V1 DocumentStateManager synchronization")
    
    def _setup_area_manager_sync(self):
        """Set up synchronization with V1 AreaStorageManager."""
        if not self.v1_area_manager:
            return
        
        # Register component for area state
        self.register_component(
            "v1_area_manager",
            StateCategory.DOCUMENT,
            PersistenceLevel.PROJECT
        )
        
        # TODO: Set up synchronization with area storage
        self.logger.debug("Set up V1 AreaStorageManager synchronization")
    
    def _sync_with_v1_managers(self, component_id: str, updates: Dict[str, Any]):
        """Synchronize updates with V1 managers."""
        if component_id == "v1_document_manager" and self.v1_document_manager:
            # Sync document state updates
            pass  # TODO: Implement V1 sync
        elif component_id == "v1_area_manager" and self.v1_area_manager:
            # Sync area state updates
            pass  # TODO: Implement V1 sync
    
    def _load_persistent_state(self):
        """Load persistent state on startup."""
        if not self.storage_dir.exists():
            return
        
        # Load global and permanent states
        for state_file in self.storage_dir.glob("*_state.json"):
            component_id = state_file.stem.replace("_state", "")
            self.load_component_state(component_id)
        
        self.logger.debug("Loaded persistent state")
    
    def _start_maintenance_thread(self):
        """Start background maintenance thread."""
        def maintenance_loop():
            while True:
                try:
                    time.sleep(30)  # Run every 30 seconds
                    
                    # Auto-save if enabled
                    if (self.auto_save_enabled and 
                        time.time() - self.last_auto_save > self.auto_save_interval):
                        self.save_all_dirty_states()
                    
                    # Cache cleanup
                    if time.time() - self.last_cache_cleanup > self.cache_timeout:
                        self._cleanup_cache()
                    
                except Exception as e:
                    self.logger.error(f"Error in maintenance thread: {e}")
        
        maintenance_thread = threading.Thread(target=maintenance_loop, daemon=True)
        maintenance_thread.start()
        self.logger.debug("Started maintenance thread")
    
    def _cleanup_cache(self):
        """Clean up expired cache entries."""
        # Simple cache cleanup - clear all for now
        # TODO: Implement proper cache expiry tracking
        self.state_cache.clear()
        self.last_cache_cleanup = time.time()
        self.logger.debug("Cache cleaned up")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get state manager statistics."""
        with self.state_lock:
            return {
                **self.stats,
                'total_components': len(self.component_states),
                'dirty_components': sum(1 for state in self.component_states.values() if state.is_dirty()),
                'cache_size': len(self.state_cache),
                'categories': {
                    cat.value: sum(1 for state in self.component_states.values() if state.category == cat)
                    for cat in StateCategory
                }
            }
    
    def cleanup(self):
        """Clean up resources."""
        # Save all dirty states
        self.save_all_dirty_states()
        
        # Clear cache
        self.state_cache.clear()
        
        self.logger.info("Enhanced state manager cleanup complete")