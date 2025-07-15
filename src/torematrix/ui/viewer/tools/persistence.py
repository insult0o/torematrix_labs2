"""
Selection persistence system for maintaining selections across view changes.
Handles saving/restoring selections during zoom, pan, and document navigation.
"""

import json
import time
import weakref
from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from ..coordinates import Point, Rectangle
from ..layers import LayerElement
from .base import SelectionResult


class PersistenceScope(Enum):
    """Scope of selection persistence."""
    SESSION = "session"        # Persist for current session only
    DOCUMENT = "document"      # Persist across document sessions
    GLOBAL = "global"          # Persist across application sessions
    TEMPORARY = "temporary"    # Short-term persistence (10 minutes)


@dataclass
class SelectionSnapshot:
    """Snapshot of a selection state."""
    selection_id: str
    elements: List[str]  # Element IDs
    geometry: Optional[Dict[str, float]]  # Serialized Rectangle
    tool_type: str
    timestamp: float
    view_state: Dict[str, Any]  # Zoom, pan, etc.
    metadata: Dict[str, Any]
    scope: PersistenceScope
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SelectionSnapshot':
        """Create from dictionary."""
        # Handle enum conversion
        if isinstance(data.get('scope'), str):
            data['scope'] = PersistenceScope(data['scope'])
        return cls(**data)
    
    def is_valid(self) -> bool:
        """Check if snapshot is still valid."""
        current_time = time.time()
        
        if self.scope == PersistenceScope.TEMPORARY:
            # Temporary snapshots expire after 10 minutes
            return (current_time - self.timestamp) < 600
        
        return True


@dataclass
class ViewState:
    """State of the document view."""
    zoom_level: float
    pan_offset: Point
    viewport_bounds: Rectangle
    document_bounds: Rectangle
    rotation: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'zoom_level': self.zoom_level,
            'pan_offset': {'x': self.pan_offset.x, 'y': self.pan_offset.y},
            'viewport_bounds': {
                'x': self.viewport_bounds.x,
                'y': self.viewport_bounds.y,
                'width': self.viewport_bounds.width,
                'height': self.viewport_bounds.height
            },
            'document_bounds': {
                'x': self.document_bounds.x,
                'y': self.document_bounds.y,
                'width': self.document_bounds.width,
                'height': self.document_bounds.height
            },
            'rotation': self.rotation
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ViewState':
        """Create from dictionary."""
        return cls(
            zoom_level=data['zoom_level'],
            pan_offset=Point(data['pan_offset']['x'], data['pan_offset']['y']),
            viewport_bounds=Rectangle(
                data['viewport_bounds']['x'],
                data['viewport_bounds']['y'],
                data['viewport_bounds']['width'],
                data['viewport_bounds']['height']
            ),
            document_bounds=Rectangle(
                data['document_bounds']['x'],
                data['document_bounds']['y'],
                data['document_bounds']['width'],
                data['document_bounds']['height']
            ),
            rotation=data.get('rotation', 0.0)
        )


class SelectionPersistence(QObject):
    """
    Advanced selection persistence system.
    
    Features:
    - Multiple persistence scopes (session, document, global, temporary)
    - View state tracking for context-aware restoration
    - Automatic cleanup of expired selections
    - Conflict resolution for overlapping selections
    - Performance optimization with lazy loading
    - Export/import functionality for sharing selections
    """
    
    # Signals
    selection_saved = pyqtSignal(str, object)  # selection_id, snapshot
    selection_restored = pyqtSignal(str, object)  # selection_id, selection_result
    selection_removed = pyqtSignal(str)  # selection_id
    cleanup_performed = pyqtSignal(int)  # number of items cleaned
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Storage for different scopes
        self._session_storage: Dict[str, SelectionSnapshot] = {}
        self._document_storage: Dict[str, SelectionSnapshot] = {}
        self._global_storage: Dict[str, SelectionSnapshot] = {}
        self._temporary_storage: Dict[str, SelectionSnapshot] = {}
        
        # Current view state
        self._current_view_state: Optional[ViewState] = None
        
        # Element registry (weak references to avoid memory leaks)
        self._element_registry: weakref.WeakValueDictionary = weakref.WeakValueDictionary()
        
        # Configuration
        self._config = {
            'max_session_selections': 100,
            'max_document_selections': 50,
            'max_global_selections': 200,
            'max_temporary_selections': 20,
            'cleanup_interval': 60000,  # 1 minute in ms
            'auto_cleanup': True,
            'view_tolerance': 0.1,  # 10% tolerance for view state matching
            'element_validation': True
        }
        
        # Performance tracking
        self._metrics = {
            'save_operations': 0,
            'restore_operations': 0,
            'cleanup_operations': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        # Auto-cleanup timer
        self._cleanup_timer = QTimer()
        self._cleanup_timer.timeout.connect(self._auto_cleanup)
        if self._config['auto_cleanup']:
            self._cleanup_timer.start(self._config['cleanup_interval'])
    
    def save_selection(self, selection_id: str, selection_result: SelectionResult,
                      scope: PersistenceScope = PersistenceScope.SESSION,
                      metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Save a selection with the specified scope.
        
        Args:
            selection_id: Unique identifier for the selection
            selection_result: Selection data to save
            scope: Persistence scope
            metadata: Additional metadata
            
        Returns:
            True if saved successfully
        """
        try:
            # Register elements in weak registry
            for element in selection_result.elements:
                if hasattr(element, 'id'):
                    self._element_registry[element.id] = element
            
            # Create snapshot
            snapshot = SelectionSnapshot(
                selection_id=selection_id,
                elements=[elem.id for elem in selection_result.elements 
                         if hasattr(elem, 'id')],
                geometry=self._serialize_geometry(selection_result.geometry),
                tool_type=selection_result.tool_type,
                timestamp=time.time(),
                view_state=self._serialize_view_state(),
                metadata=metadata or {},
                scope=scope
            )
            
            # Store in appropriate storage
            storage = self._get_storage(scope)
            storage[selection_id] = snapshot
            
            # Enforce size limits
            self._enforce_storage_limits(scope)
            
            self._metrics['save_operations'] += 1
            self.selection_saved.emit(selection_id, snapshot)
            
            return True
            
        except Exception as e:
            print(f"Error saving selection {selection_id}: {e}")
            return False
    
    def restore_selection(self, selection_id: str,
                         validate_view: bool = True,
                         validate_elements: bool = None) -> Optional[SelectionResult]:
        """
        Restore a selection by ID.
        
        Args:
            selection_id: Selection identifier
            validate_view: Whether to validate view state compatibility
            validate_elements: Whether to validate element existence
            
        Returns:
            Restored SelectionResult or None if not found/invalid
        """
        if validate_elements is None:
            validate_elements = self._config['element_validation']
        
        try:
            # Find snapshot across all storages
            snapshot = self._find_snapshot(selection_id)
            if not snapshot:
                self._metrics['cache_misses'] += 1
                return None
            
            # Validate snapshot
            if not snapshot.is_valid():
                self.remove_selection(selection_id)
                return None
            
            # Validate view state if requested
            if validate_view and not self._is_view_compatible(snapshot.view_state):
                return None
            
            # Restore elements
            elements = []
            if validate_elements:
                for element_id in snapshot.elements:
                    element = self._element_registry.get(element_id)
                    if element:
                        elements.append(element)
            else:
                # Create placeholder elements if validation disabled
                elements = [self._create_placeholder_element(eid) 
                           for eid in snapshot.elements]
            
            # Restore geometry
            geometry = self._deserialize_geometry(snapshot.geometry)
            
            # Create selection result
            selection_result = SelectionResult(
                elements=elements,
                geometry=geometry,
                tool_type=snapshot.tool_type,
                timestamp=snapshot.timestamp,
                metadata=snapshot.metadata.copy()
            )
            
            self._metrics['restore_operations'] += 1
            self._metrics['cache_hits'] += 1
            self.selection_restored.emit(selection_id, selection_result)
            
            return selection_result
            
        except Exception as e:
            print(f"Error restoring selection {selection_id}: {e}")
            return None
    
    def remove_selection(self, selection_id: str) -> bool:
        """Remove a selection from all storages."""
        removed = False
        
        for storage in [self._session_storage, self._document_storage,
                       self._global_storage, self._temporary_storage]:
            if selection_id in storage:
                del storage[selection_id]
                removed = True
        
        if removed:
            self.selection_removed.emit(selection_id)
        
        return removed
    
    def list_selections(self, scope: Optional[PersistenceScope] = None,
                       valid_only: bool = True) -> List[SelectionSnapshot]:
        """
        List selections, optionally filtered by scope.
        
        Args:
            scope: Scope to filter by (None for all)
            valid_only: Whether to return only valid selections
            
        Returns:
            List of selection snapshots
        """
        selections = []
        
        if scope is None:
            # All scopes
            for storage in [self._session_storage, self._document_storage,
                           self._global_storage, self._temporary_storage]:
                selections.extend(storage.values())
        else:
            storage = self._get_storage(scope)
            selections.extend(storage.values())
        
        if valid_only:
            selections = [s for s in selections if s.is_valid()]
        
        return sorted(selections, key=lambda s: s.timestamp, reverse=True)
    
    def clear_scope(self, scope: PersistenceScope) -> int:
        """Clear all selections in a scope."""
        storage = self._get_storage(scope)
        count = len(storage)
        storage.clear()
        return count
    
    def clear_all(self) -> int:
        """Clear all selections from all scopes."""
        total = (len(self._session_storage) + len(self._document_storage) +
                len(self._global_storage) + len(self._temporary_storage))
        
        self._session_storage.clear()
        self._document_storage.clear()
        self._global_storage.clear()
        self._temporary_storage.clear()
        
        return total
    
    def update_view_state(self, view_state: ViewState) -> None:
        """Update current view state for context tracking."""
        self._current_view_state = view_state
    
    def find_selections_by_elements(self, element_ids: Set[str],
                                   scope: Optional[PersistenceScope] = None) -> List[SelectionSnapshot]:
        """Find selections containing specific elements."""
        all_selections = self.list_selections(scope)
        
        matching = []
        for snapshot in all_selections:
            snapshot_elements = set(snapshot.elements)
            if snapshot_elements.intersection(element_ids):
                matching.append(snapshot)
        
        return matching
    
    def find_selections_in_area(self, area: Rectangle,
                               scope: Optional[PersistenceScope] = None) -> List[SelectionSnapshot]:
        """Find selections within a geometric area."""
        all_selections = self.list_selections(scope)
        
        matching = []
        for snapshot in all_selections:
            if snapshot.geometry:
                geometry = self._deserialize_geometry(snapshot.geometry)
                if geometry and geometry.intersects(area):
                    matching.append(snapshot)
        
        return matching
    
    def export_selections(self, scope: Optional[PersistenceScope] = None) -> str:
        """Export selections to JSON string."""
        selections = self.list_selections(scope, valid_only=True)
        data = {
            'version': '1.0',
            'timestamp': time.time(),
            'selections': [s.to_dict() for s in selections]
        }
        return json.dumps(data, indent=2)
    
    def import_selections(self, json_data: str, 
                         scope: PersistenceScope = PersistenceScope.SESSION,
                         overwrite: bool = False) -> int:
        """Import selections from JSON string."""
        try:
            data = json.loads(json_data)
            selections = data.get('selections', [])
            
            imported_count = 0
            for selection_data in selections:
                snapshot = SelectionSnapshot.from_dict(selection_data)
                
                # Check for conflicts
                if not overwrite and self._find_snapshot(snapshot.selection_id):
                    continue  # Skip existing
                
                # Update scope
                snapshot.scope = scope
                
                # Store
                storage = self._get_storage(scope)
                storage[snapshot.selection_id] = snapshot
                imported_count += 1
            
            return imported_count
            
        except Exception as e:
            print(f"Error importing selections: {e}")
            return 0
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get persistence statistics."""
        return {
            'session_count': len(self._session_storage),
            'document_count': len(self._document_storage),
            'global_count': len(self._global_storage),
            'temporary_count': len(self._temporary_storage),
            'total_count': (len(self._session_storage) + len(self._document_storage) +
                           len(self._global_storage) + len(self._temporary_storage)),
            'element_registry_size': len(self._element_registry),
            'metrics': self._metrics.copy()
        }
    
    def optimize(self) -> Dict[str, int]:
        """Optimize persistence storage."""
        results = {
            'expired_removed': 0,
            'duplicates_removed': 0,
            'orphaned_removed': 0
        }
        
        # Remove expired temporary selections
        current_time = time.time()
        expired_ids = []
        
        for selection_id, snapshot in self._temporary_storage.items():
            if not snapshot.is_valid():
                expired_ids.append(selection_id)
        
        for selection_id in expired_ids:
            del self._temporary_storage[selection_id]
            results['expired_removed'] += 1
        
        # Remove duplicates (same elements and geometry)
        results['duplicates_removed'] = self._remove_duplicates()
        
        # Remove orphaned selections (elements no longer exist)
        if self._config['element_validation']:
            results['orphaned_removed'] = self._remove_orphaned()
        
        return results
    
    # Private methods
    
    def _get_storage(self, scope: PersistenceScope) -> Dict[str, SelectionSnapshot]:
        """Get storage for scope."""
        storages = {
            PersistenceScope.SESSION: self._session_storage,
            PersistenceScope.DOCUMENT: self._document_storage,
            PersistenceScope.GLOBAL: self._global_storage,
            PersistenceScope.TEMPORARY: self._temporary_storage
        }
        return storages[scope]
    
    def _find_snapshot(self, selection_id: str) -> Optional[SelectionSnapshot]:
        """Find snapshot across all storages."""
        for storage in [self._session_storage, self._document_storage,
                       self._global_storage, self._temporary_storage]:
            if selection_id in storage:
                return storage[selection_id]
        return None
    
    def _serialize_geometry(self, geometry: Optional[Rectangle]) -> Optional[Dict[str, float]]:
        """Serialize geometry to dictionary."""
        if geometry is None:
            return None
        
        return {
            'x': geometry.x,
            'y': geometry.y,
            'width': geometry.width,
            'height': geometry.height
        }
    
    def _deserialize_geometry(self, data: Optional[Dict[str, float]]) -> Optional[Rectangle]:
        """Deserialize geometry from dictionary."""
        if data is None:
            return None
        
        return Rectangle(
            data['x'], data['y'],
            data['width'], data['height']
        )
    
    def _serialize_view_state(self) -> Dict[str, Any]:
        """Serialize current view state."""
        if self._current_view_state is None:
            return {}
        
        return self._current_view_state.to_dict()
    
    def _is_view_compatible(self, view_state_data: Dict[str, Any]) -> bool:
        """Check if view state is compatible with current view."""
        if not view_state_data or self._current_view_state is None:
            return True  # No validation possible
        
        try:
            saved_view = ViewState.from_dict(view_state_data)
            current_view = self._current_view_state
            
            tolerance = self._config['view_tolerance']
            
            # Check zoom level
            zoom_diff = abs(saved_view.zoom_level - current_view.zoom_level) / current_view.zoom_level
            if zoom_diff > tolerance:
                return False
            
            # Check pan offset
            pan_diff = ((saved_view.pan_offset.x - current_view.pan_offset.x) ** 2 +
                       (saved_view.pan_offset.y - current_view.pan_offset.y) ** 2) ** 0.5
            viewport_size = max(current_view.viewport_bounds.width, current_view.viewport_bounds.height)
            
            if pan_diff > viewport_size * tolerance:
                return False
            
            return True
            
        except Exception:
            return False  # Invalid view state data
    
    def _create_placeholder_element(self, element_id: str) -> Any:
        """Create placeholder element for missing elements."""
        # This would normally create a proper placeholder
        # For now, return a simple object with the ID
        class PlaceholderElement:
            def __init__(self, element_id):
                self.id = element_id
                self.is_placeholder = True
        
        return PlaceholderElement(element_id)
    
    def _enforce_storage_limits(self, scope: PersistenceScope) -> None:
        """Enforce storage size limits for scope."""
        storage = self._get_storage(scope)
        limits = {
            PersistenceScope.SESSION: self._config['max_session_selections'],
            PersistenceScope.DOCUMENT: self._config['max_document_selections'],
            PersistenceScope.GLOBAL: self._config['max_global_selections'],
            PersistenceScope.TEMPORARY: self._config['max_temporary_selections']
        }
        
        limit = limits.get(scope)
        if limit and len(storage) > limit:
            # Remove oldest selections
            sorted_items = sorted(storage.items(), key=lambda x: x[1].timestamp)
            remove_count = len(storage) - limit
            
            for i in range(remove_count):
                selection_id = sorted_items[i][0]
                del storage[selection_id]
    
    def _auto_cleanup(self) -> None:
        """Automatic cleanup of expired selections."""
        if not self._config['auto_cleanup']:
            return
        
        results = self.optimize()
        total_cleaned = sum(results.values())
        
        if total_cleaned > 0:
            self._metrics['cleanup_operations'] += 1
            self.cleanup_performed.emit(total_cleaned)
    
    def _remove_duplicates(self) -> int:
        """Remove duplicate selections."""
        removed_count = 0
        
        for storage in [self._session_storage, self._document_storage,
                       self._global_storage, self._temporary_storage]:
            
            # Group by element sets and geometry
            groups = {}
            for selection_id, snapshot in storage.items():
                key = (tuple(sorted(snapshot.elements)), 
                       str(snapshot.geometry) if snapshot.geometry else None)
                
                if key not in groups:
                    groups[key] = []
                groups[key].append((selection_id, snapshot))
            
            # Remove duplicates (keep newest)
            for group in groups.values():
                if len(group) > 1:
                    # Sort by timestamp, keep newest
                    group.sort(key=lambda x: x[1].timestamp, reverse=True)
                    
                    # Remove all but the newest
                    for selection_id, _ in group[1:]:
                        del storage[selection_id]
                        removed_count += 1
        
        return removed_count
    
    def _remove_orphaned(self) -> int:
        """Remove selections with missing elements."""
        removed_count = 0
        
        for storage in [self._session_storage, self._document_storage,
                       self._global_storage, self._temporary_storage]:
            
            orphaned_ids = []
            for selection_id, snapshot in storage.items():
                # Check if any elements still exist
                has_valid_elements = False
                for element_id in snapshot.elements:
                    if element_id in self._element_registry:
                        has_valid_elements = True
                        break
                
                if not has_valid_elements and snapshot.elements:
                    orphaned_ids.append(selection_id)
            
            for selection_id in orphaned_ids:
                del storage[selection_id]
                removed_count += 1
        
        return removed_count