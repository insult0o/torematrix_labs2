"""
State Management System for Document Viewer Selection.
This module provides comprehensive state management for selection operations,
including persistence, session management, and project-level state coordination.
"""
from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
import threading
from collections import defaultdict

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from .coordinates import Rectangle, Point
from .selection import SelectionState, SelectionMode, SelectionStrategy


class StateScope(Enum):
    """Scope of state storage."""
    SESSION = "session"        # Current session only
    PROJECT = "project"        # Project-level persistence
    GLOBAL = "global"          # Global application state
    TEMPORARY = "temporary"    # Temporary state (cleared on exit)


class StatePersistenceMode(Enum):
    """How state should be persisted."""
    IMMEDIATE = "immediate"    # Save immediately on change
    BATCHED = "batched"       # Save in batches periodically
    MANUAL = "manual"         # Save only when explicitly requested
    NONE = "none"            # No persistence


@dataclass
class SelectionStateSnapshot:
    """Snapshot of selection state at a point in time."""
    selection_id: str
    timestamp: datetime
    selection_mode: SelectionMode
    selection_strategy: SelectionStrategy
    selected_elements: List[str]  # Element IDs
    selection_bounds: List[Rectangle]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'selection_id': self.selection_id,
            'timestamp': self.timestamp.isoformat(),
            'selection_mode': self.selection_mode.value,
            'selection_strategy': self.selection_strategy.value,
            'selected_elements': self.selected_elements,
            'selection_bounds': [
                {
                    'x': bounds.x,
                    'y': bounds.y,
                    'width': bounds.width,
                    'height': bounds.height
                }
                for bounds in self.selection_bounds
            ],
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SelectionStateSnapshot:
        """Create from dictionary."""
        return cls(
            selection_id=data['selection_id'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            selection_mode=SelectionMode(data['selection_mode']),
            selection_strategy=SelectionStrategy(data['selection_strategy']),
            selected_elements=data['selected_elements'],
            selection_bounds=[
                Rectangle(
                    bounds['x'],
                    bounds['y'],
                    bounds['width'],
                    bounds['height']
                )
                for bounds in data['selection_bounds']
            ],
            metadata=data.get('metadata', {})
        )


@dataclass
class SelectionSet:
    """Named collection of selection states."""
    set_id: str
    name: str
    description: str
    snapshots: List[SelectionStateSnapshot] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)
    tags: Set[str] = field(default_factory=set)
    
    def add_snapshot(self, snapshot: SelectionStateSnapshot) -> None:
        """Add a snapshot to the set."""
        self.snapshots.append(snapshot)
        self.modified_at = datetime.now()
    
    def remove_snapshot(self, selection_id: str) -> bool:
        """Remove a snapshot by ID."""
        for i, snapshot in enumerate(self.snapshots):
            if snapshot.selection_id == selection_id:
                del self.snapshots[i]
                self.modified_at = datetime.now()
                return True
        return False
    
    def get_snapshot(self, selection_id: str) -> Optional[SelectionStateSnapshot]:
        """Get a snapshot by ID."""
        for snapshot in self.snapshots:
            if snapshot.selection_id == selection_id:
                return snapshot
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'set_id': self.set_id,
            'name': self.name,
            'description': self.description,
            'snapshots': [snapshot.to_dict() for snapshot in self.snapshots],
            'created_at': self.created_at.isoformat(),
            'modified_at': self.modified_at.isoformat(),
            'tags': list(self.tags)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SelectionSet:
        """Create from dictionary."""
        return cls(
            set_id=data['set_id'],
            name=data['name'],
            description=data['description'],
            snapshots=[
                SelectionStateSnapshot.from_dict(snapshot_data)
                for snapshot_data in data['snapshots']
            ],
            created_at=datetime.fromisoformat(data['created_at']),
            modified_at=datetime.fromisoformat(data['modified_at']),
            tags=set(data.get('tags', []))
        )


@dataclass
class SessionState:
    """Current session state information."""
    session_id: str
    started_at: datetime
    last_activity: datetime
    current_selection: Optional[SelectionStateSnapshot] = None
    selection_history: List[SelectionStateSnapshot] = field(default_factory=list)
    viewport_state: Dict[str, Any] = field(default_factory=dict)
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    
    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.now()
    
    def add_to_history(self, snapshot: SelectionStateSnapshot) -> None:
        """Add selection to history."""
        self.selection_history.append(snapshot)
        self.current_selection = snapshot
        self.update_activity()
        
        # Limit history size
        if len(self.selection_history) > 100:
            self.selection_history = self.selection_history[-100:]


class StateManagerSignals(QObject):
    """Signals for state management events."""
    state_saved = pyqtSignal(str, str)  # scope, state_id
    state_loaded = pyqtSignal(str, str)  # scope, state_id
    state_cleared = pyqtSignal(str)  # scope
    selection_saved = pyqtSignal(str)  # selection_id
    selection_set_created = pyqtSignal(str)  # set_id
    session_started = pyqtSignal(str)  # session_id
    session_ended = pyqtSignal(str)  # session_id
    persistence_error = pyqtSignal(str, str)  # operation, error_message


class SelectionStateManager:
    """
    Comprehensive state management for selection operations.
    
    This manager handles:
    - Selection state persistence across sessions
    - Project-level selection state management
    - Session state tracking and recovery
    - Selection history and undo/redo functionality
    - Export/import of selection sets
    """
    
    def __init__(self, project_path: Optional[Path] = None):
        self.signals = StateManagerSignals()
        self.project_path = project_path
        
        # Core state storage
        self.selection_sets: Dict[str, SelectionSet] = {}
        self.current_session: Optional[SessionState] = None
        self.state_storage: Dict[StateScope, Dict[str, Any]] = {
            scope: {} for scope in StateScope
        }
        
        # Persistence configuration
        self.persistence_mode = StatePersistenceMode.BATCHED
        self.batch_save_interval = 30  # seconds
        self.max_history_size = 1000
        self.max_session_duration = timedelta(hours=24)
        
        # Auto-save timer
        self.autosave_timer = QTimer()
        self.autosave_timer.timeout.connect(self._perform_batch_save)
        self.autosave_timer.start(self.batch_save_interval * 1000)
        
        # Thread safety
        self.state_lock = threading.RLock()
        self.pending_saves: Set[str] = set()
        
        # Initialize session
        self._initialize_session()
        
        # Load existing state
        self._load_project_state()
    
    def _initialize_session(self) -> None:
        """Initialize a new session."""
        session_id = str(uuid.uuid4())
        self.current_session = SessionState(
            session_id=session_id,
            started_at=datetime.now(),
            last_activity=datetime.now()
        )
        self.signals.session_started.emit(session_id)
    
    def _load_project_state(self) -> None:
        """Load state from project files."""
        if not self.project_path:
            return
        
        try:
            # Load selection sets
            selection_sets_file = self.project_path / ".torematrix" / "selection_sets.json"
            if selection_sets_file.exists():
                with open(selection_sets_file, 'r') as f:
                    data = json.load(f)
                    
                for set_data in data.get('selection_sets', []):
                    selection_set = SelectionSet.from_dict(set_data)
                    self.selection_sets[selection_set.set_id] = selection_set
            
            # Load session state
            session_file = self.project_path / ".torematrix" / "last_session.json"
            if session_file.exists():
                with open(session_file, 'r') as f:
                    session_data = json.load(f)
                    
                # Check if session is recent enough to restore
                last_activity = datetime.fromisoformat(session_data['last_activity'])
                if datetime.now() - last_activity < self.max_session_duration:
                    self._restore_session_state(session_data)
                    
        except Exception as e:
            self.signals.persistence_error.emit("load", str(e))
    
    def _restore_session_state(self, session_data: Dict[str, Any]) -> None:
        """Restore session state from data."""
        if not self.current_session:
            return
        
        try:
            # Restore selection history
            for snapshot_data in session_data.get('selection_history', []):
                snapshot = SelectionStateSnapshot.from_dict(snapshot_data)
                self.current_session.selection_history.append(snapshot)
            
            # Restore current selection
            if session_data.get('current_selection'):
                self.current_session.current_selection = SelectionStateSnapshot.from_dict(
                    session_data['current_selection']
                )
            
            # Restore viewport state
            self.current_session.viewport_state = session_data.get('viewport_state', {})
            
            # Restore user preferences
            self.current_session.user_preferences = session_data.get('user_preferences', {})
            
        except Exception as e:
            self.signals.persistence_error.emit("restore_session", str(e))
    
    def save_selection_state(
        self,
        selection_state: SelectionState,
        selection_id: Optional[str] = None,
        scope: StateScope = StateScope.SESSION,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Save current selection state.
        
        Args:
            selection_state: Current selection state
            selection_id: Optional ID for the selection
            scope: Scope of persistence
            metadata: Additional metadata
            
        Returns:
            Generated or provided selection ID
        """
        with self.state_lock:
            if not selection_id:
                selection_id = str(uuid.uuid4())
            
            # Create snapshot
            snapshot = SelectionStateSnapshot(
                selection_id=selection_id,
                timestamp=datetime.now(),
                selection_mode=selection_state.mode,
                selection_strategy=selection_state.strategy,
                selected_elements=[str(id(elem)) for elem in selection_state.selected_elements],
                selection_bounds=[elem.get_bounds() for elem in selection_state.selected_elements],
                metadata=metadata or {}
            )
            
            # Store in appropriate scope
            if scope == StateScope.SESSION and self.current_session:
                self.current_session.add_to_history(snapshot)
            else:
                if scope not in self.state_storage:
                    self.state_storage[scope] = {}
                self.state_storage[scope][selection_id] = snapshot
            
            # Mark for persistence
            if self.persistence_mode == StatePersistenceMode.IMMEDIATE:
                self._save_immediately(scope, selection_id)
            elif self.persistence_mode == StatePersistenceMode.BATCHED:
                self.pending_saves.add(f"{scope.value}:{selection_id}")
            
            self.signals.selection_saved.emit(selection_id)
            return selection_id
    
    def load_selection_state(
        self,
        selection_id: str,
        scope: StateScope = StateScope.SESSION
    ) -> Optional[SelectionStateSnapshot]:
        """
        Load selection state by ID.
        
        Args:
            selection_id: ID of the selection to load
            scope: Scope to load from
            
        Returns:
            Selection state snapshot or None if not found
        """
        with self.state_lock:
            if scope == StateScope.SESSION and self.current_session:
                return self.current_session.get_snapshot(selection_id)
            
            if scope in self.state_storage:
                snapshot = self.state_storage[scope].get(selection_id)
                if snapshot:
                    self.signals.state_loaded.emit(scope.value, selection_id)
                    return snapshot
            
            return None
    
    def create_selection_set(
        self,
        name: str,
        description: str = "",
        selection_ids: Optional[List[str]] = None,
        tags: Optional[Set[str]] = None
    ) -> str:
        """
        Create a named selection set.
        
        Args:
            name: Name of the selection set
            description: Description of the set
            selection_ids: List of selection IDs to include
            tags: Tags for the set
            
        Returns:
            Generated set ID
        """
        with self.state_lock:
            set_id = str(uuid.uuid4())
            selection_set = SelectionSet(
                set_id=set_id,
                name=name,
                description=description,
                tags=tags or set()
            )
            
            # Add selections to set
            if selection_ids:
                for sel_id in selection_ids:
                    # Try to find snapshot in session first
                    snapshot = None
                    if self.current_session:
                        snapshot = self.current_session.get_snapshot(sel_id)
                    
                    # Search other scopes
                    if not snapshot:
                        for scope in StateScope:
                            if scope in self.state_storage:
                                snapshot = self.state_storage[scope].get(sel_id)
                                if snapshot:
                                    break
                    
                    if snapshot:
                        selection_set.add_snapshot(snapshot)
            
            self.selection_sets[set_id] = selection_set
            
            # Mark for persistence
            if self.persistence_mode == StatePersistenceMode.IMMEDIATE:
                self._save_selection_sets()
            elif self.persistence_mode == StatePersistenceMode.BATCHED:
                self.pending_saves.add(f"selection_sets:{set_id}")
            
            self.signals.selection_set_created.emit(set_id)
            return set_id
    
    def get_selection_set(self, set_id: str) -> Optional[SelectionSet]:
        """Get a selection set by ID."""
        with self.state_lock:
            return self.selection_sets.get(set_id)
    
    def get_all_selection_sets(self) -> List[SelectionSet]:
        """Get all selection sets."""
        with self.state_lock:
            return list(self.selection_sets.values())
    
    def delete_selection_set(self, set_id: str) -> bool:
        """Delete a selection set."""
        with self.state_lock:
            if set_id in self.selection_sets:
                del self.selection_sets[set_id]
                self._save_selection_sets()
                return True
            return False
    
    def get_selection_history(self, limit: Optional[int] = None) -> List[SelectionStateSnapshot]:
        """Get selection history from current session."""
        with self.state_lock:
            if not self.current_session:
                return []
            
            history = self.current_session.selection_history
            if limit:
                return history[-limit:]
            return history.copy()
    
    def clear_selection_history(self) -> None:
        """Clear selection history."""
        with self.state_lock:
            if self.current_session:
                self.current_session.selection_history.clear()
                self.current_session.current_selection = None
    
    def get_current_selection(self) -> Optional[SelectionStateSnapshot]:
        """Get current selection snapshot."""
        with self.state_lock:
            if self.current_session:
                return self.current_session.current_selection
            return None
    
    def export_selection_set(self, set_id: str, export_path: Path) -> bool:
        """
        Export a selection set to file.
        
        Args:
            set_id: ID of the set to export
            export_path: Path to export to
            
        Returns:
            True if successful
        """
        with self.state_lock:
            selection_set = self.selection_sets.get(set_id)
            if not selection_set:
                return False
            
            try:
                export_data = {
                    'format_version': '1.0',
                    'exported_at': datetime.now().isoformat(),
                    'selection_set': selection_set.to_dict()
                }
                
                with open(export_path, 'w') as f:
                    json.dump(export_data, f, indent=2)
                
                return True
                
            except Exception as e:
                self.signals.persistence_error.emit("export", str(e))
                return False
    
    def import_selection_set(self, import_path: Path) -> Optional[str]:
        """
        Import a selection set from file.
        
        Args:
            import_path: Path to import from
            
        Returns:
            Imported set ID or None if failed
        """
        with self.state_lock:
            try:
                with open(import_path, 'r') as f:
                    data = json.load(f)
                
                # Validate format
                if data.get('format_version') != '1.0':
                    raise ValueError("Unsupported format version")
                
                # Import selection set
                selection_set = SelectionSet.from_dict(data['selection_set'])
                
                # Generate new ID to avoid conflicts
                new_set_id = str(uuid.uuid4())
                selection_set.set_id = new_set_id
                
                self.selection_sets[new_set_id] = selection_set
                
                # Mark for persistence
                if self.persistence_mode != StatePersistenceMode.NONE:
                    self._save_selection_sets()
                
                self.signals.selection_set_created.emit(new_set_id)
                return new_set_id
                
            except Exception as e:
                self.signals.persistence_error.emit("import", str(e))
                return None
    
    def set_viewport_state(self, state: Dict[str, Any]) -> None:
        """Set viewport state in current session."""
        with self.state_lock:
            if self.current_session:
                self.current_session.viewport_state = state
                self.current_session.update_activity()
    
    def get_viewport_state(self) -> Dict[str, Any]:
        """Get viewport state from current session."""
        with self.state_lock:
            if self.current_session:
                return self.current_session.viewport_state.copy()
            return {}
    
    def set_user_preference(self, key: str, value: Any) -> None:
        """Set user preference."""
        with self.state_lock:
            if self.current_session:
                self.current_session.user_preferences[key] = value
                self.current_session.update_activity()
    
    def get_user_preference(self, key: str, default: Any = None) -> Any:
        """Get user preference."""
        with self.state_lock:
            if self.current_session:
                return self.current_session.user_preferences.get(key, default)
            return default
    
    def clear_state(self, scope: StateScope) -> None:
        """Clear state for a specific scope."""
        with self.state_lock:
            if scope == StateScope.SESSION and self.current_session:
                self.current_session.selection_history.clear()
                self.current_session.current_selection = None
                self.current_session.viewport_state.clear()
            elif scope in self.state_storage:
                self.state_storage[scope].clear()
            
            self.signals.state_cleared.emit(scope.value)
    
    def _save_immediately(self, scope: StateScope, state_id: str) -> None:
        """Save state immediately."""
        if scope == StateScope.PROJECT:
            self._save_project_state()
        elif scope == StateScope.SESSION:
            self._save_session_state()
    
    def _perform_batch_save(self) -> None:
        """Perform batched save of pending changes."""
        if not self.pending_saves:
            return
        
        with self.state_lock:
            # Group saves by type
            save_groups = defaultdict(list)
            for save_key in self.pending_saves:
                scope, item_id = save_key.split(':', 1)
                save_groups[scope].append(item_id)
            
            # Perform saves
            for scope, item_ids in save_groups.items():
                if scope == StateScope.PROJECT.value:
                    self._save_project_state()
                elif scope == StateScope.SESSION.value:
                    self._save_session_state()
                elif scope == "selection_sets":
                    self._save_selection_sets()
            
            self.pending_saves.clear()
    
    def _save_project_state(self) -> None:
        """Save project-level state."""
        if not self.project_path:
            return
        
        try:
            # Ensure directory exists
            state_dir = self.project_path / ".torematrix"
            state_dir.mkdir(exist_ok=True)
            
            # Save project state
            project_state = {
                'project_selections': {
                    state_id: snapshot.to_dict()
                    for state_id, snapshot in self.state_storage[StateScope.PROJECT].items()
                }
            }
            
            with open(state_dir / "project_state.json", 'w') as f:
                json.dump(project_state, f, indent=2)
                
        except Exception as e:
            self.signals.persistence_error.emit("save_project", str(e))
    
    def _save_session_state(self) -> None:
        """Save session state."""
        if not self.project_path or not self.current_session:
            return
        
        try:
            # Ensure directory exists
            state_dir = self.project_path / ".torematrix"
            state_dir.mkdir(exist_ok=True)
            
            # Save session state
            session_data = {
                'session_id': self.current_session.session_id,
                'started_at': self.current_session.started_at.isoformat(),
                'last_activity': self.current_session.last_activity.isoformat(),
                'selection_history': [
                    snapshot.to_dict() for snapshot in self.current_session.selection_history
                ],
                'current_selection': (
                    self.current_session.current_selection.to_dict()
                    if self.current_session.current_selection else None
                ),
                'viewport_state': self.current_session.viewport_state,
                'user_preferences': self.current_session.user_preferences
            }
            
            with open(state_dir / "last_session.json", 'w') as f:
                json.dump(session_data, f, indent=2)
                
        except Exception as e:
            self.signals.persistence_error.emit("save_session", str(e))
    
    def _save_selection_sets(self) -> None:
        """Save selection sets."""
        if not self.project_path:
            return
        
        try:
            # Ensure directory exists
            state_dir = self.project_path / ".torematrix"
            state_dir.mkdir(exist_ok=True)
            
            # Save selection sets
            sets_data = {
                'selection_sets': [
                    selection_set.to_dict()
                    for selection_set in self.selection_sets.values()
                ]
            }
            
            with open(state_dir / "selection_sets.json", 'w') as f:
                json.dump(sets_data, f, indent=2)
                
        except Exception as e:
            self.signals.persistence_error.emit("save_selection_sets", str(e))
    
    def set_persistence_mode(self, mode: StatePersistenceMode) -> None:
        """Set persistence mode."""
        self.persistence_mode = mode
        
        if mode == StatePersistenceMode.NONE:
            self.autosave_timer.stop()
        elif mode == StatePersistenceMode.BATCHED:
            self.autosave_timer.start(self.batch_save_interval * 1000)
        else:
            self.autosave_timer.stop()
    
    def get_state_statistics(self) -> Dict[str, Any]:
        """Get state management statistics."""
        with self.state_lock:
            stats = {
                'selection_sets_count': len(self.selection_sets),
                'total_snapshots': sum(len(s.snapshots) for s in self.selection_sets.values()),
                'session_selections': len(self.current_session.selection_history) if self.current_session else 0,
                'pending_saves': len(self.pending_saves),
                'persistence_mode': self.persistence_mode.value
            }
            
            # Add scope statistics
            for scope in StateScope:
                stats[f'{scope.value}_states'] = len(self.state_storage[scope])
            
            return stats
    
    def cleanup(self) -> None:
        """Clean up resources and save final state."""
        with self.state_lock:
            # Stop autosave timer
            if self.autosave_timer.isActive():
                self.autosave_timer.stop()
            
            # Perform final save
            self._perform_batch_save()
            
            # Save session state
            if self.current_session:
                self._save_session_state()
                self.signals.session_ended.emit(self.current_session.session_id)
            
            # Clear all state
            self.selection_sets.clear()
            self.current_session = None
            for scope_storage in self.state_storage.values():
                scope_storage.clear()
            self.pending_saves.clear()