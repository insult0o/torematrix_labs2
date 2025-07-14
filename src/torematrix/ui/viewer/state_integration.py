"""
State Integration for Selection System.
This module provides integration between the selection system and state management,
handling automatic state persistence and recovery.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from .selection import SelectionManager, SelectionState, SelectionMode, SelectionStrategy
from .state import SelectionStateManager, SelectionStateSnapshot, StateScope, StatePersistenceMode
from .persistence import PersistenceManager, StorageOptions, StorageFormat
from .coordinates import Rectangle, Point


@dataclass
class StateIntegrationConfig:
    """Configuration for state integration."""
    auto_save_enabled: bool = True
    auto_save_interval: int = 30  # seconds
    max_undo_history: int = 50
    persist_viewport_state: bool = True
    persist_selection_mode: bool = True
    backup_on_major_changes: bool = True
    sync_with_project: bool = True


class StateIntegrationSignals(QObject):
    """Signals for state integration events."""
    state_restored = pyqtSignal(str)  # selection_id
    auto_save_completed = pyqtSignal()
    undo_state_changed = pyqtSignal(bool, bool)  # can_undo, can_redo
    selection_persisted = pyqtSignal(str)  # selection_id
    integration_error = pyqtSignal(str, str)  # operation, error_message


class SelectionStateIntegration:
    """
    Integration layer between selection system and state management.
    
    This class provides:
    - Automatic state persistence for selection operations
    - Undo/redo functionality for selections
    - Recovery from interrupted sessions
    - Synchronization with project state
    """
    
    def __init__(
        self,
        selection_manager: SelectionManager,
        state_manager: SelectionStateManager,
        config: Optional[StateIntegrationConfig] = None
    ):
        self.selection_manager = selection_manager
        self.state_manager = state_manager
        self.config = config or StateIntegrationConfig()
        self.signals = StateIntegrationSignals()
        
        # Undo/redo state
        self.undo_stack: List[SelectionStateSnapshot] = []
        self.redo_stack: List[SelectionStateSnapshot] = []
        self.current_state_id: Optional[str] = None
        
        # Auto-save timer
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self._perform_auto_save)
        if self.config.auto_save_enabled:
            self.auto_save_timer.start(self.config.auto_save_interval * 1000)
        
        # State tracking
        self.last_saved_state: Optional[SelectionStateSnapshot] = None
        self.pending_changes = False
        
        # Integration callbacks
        self.state_change_callbacks: List[Callable[[SelectionStateSnapshot], None]] = []
        
        # Setup integration
        self._setup_selection_monitoring()
        self._restore_previous_session()
    
    def _setup_selection_monitoring(self) -> None:
        """Setup monitoring of selection changes."""
        # Connect to selection manager events
        self.selection_manager.selection_changed.connect(self._on_selection_changed)
        self.selection_manager.mode_changed.connect(self._on_mode_changed)
        self.selection_manager.strategy_changed.connect(self._on_strategy_changed)
        
        # Connect to state manager events
        self.state_manager.signals.selection_saved.connect(self._on_state_saved)
        self.state_manager.signals.persistence_error.connect(self._on_persistence_error)
    
    def _restore_previous_session(self) -> None:
        """Restore state from previous session if available."""
        try:
            # Get current session state
            current_selection = self.state_manager.get_current_selection()
            if current_selection:
                self._restore_selection_state(current_selection)
                self.signals.state_restored.emit(current_selection.selection_id)
            
            # Restore viewport state if enabled
            if self.config.persist_viewport_state:
                viewport_state = self.state_manager.get_viewport_state()
                if viewport_state:
                    self._restore_viewport_state(viewport_state)
            
            # Restore selection mode if enabled
            if self.config.persist_selection_mode:
                mode = self.state_manager.get_user_preference('selection_mode')
                if mode:
                    self.selection_manager.set_selection_mode(SelectionMode(mode))
                
                strategy = self.state_manager.get_user_preference('selection_strategy')
                if strategy:
                    self.selection_manager.set_selection_strategy(SelectionStrategy(strategy))
                    
        except Exception as e:
            self.signals.integration_error.emit("restore_session", str(e))
    
    def _restore_selection_state(self, snapshot: SelectionStateSnapshot) -> None:
        """Restore selection state from snapshot."""
        try:
            # Set selection mode and strategy
            self.selection_manager.set_selection_mode(snapshot.selection_mode)
            self.selection_manager.set_selection_strategy(snapshot.selection_strategy)
            
            # Restore selected elements (this would need element lookup)
            # For now, we'll restore the bounds information
            self.selection_manager.restore_selection_bounds(snapshot.selection_bounds)
            
            self.current_state_id = snapshot.selection_id
            
        except Exception as e:
            self.signals.integration_error.emit("restore_selection", str(e))
    
    def _restore_viewport_state(self, viewport_state: Dict[str, Any]) -> None:
        """Restore viewport state."""
        try:
            # This would integrate with the viewport/overlay system
            # For now, we'll store it for later use
            self.last_viewport_state = viewport_state
            
        except Exception as e:
            self.signals.integration_error.emit("restore_viewport", str(e))
    
    def _on_selection_changed(self, selection_state: SelectionState) -> None:
        """Handle selection changes."""
        if not selection_state.selected_elements:
            return
        
        try:
            # Create snapshot
            snapshot = self._create_snapshot_from_selection(selection_state)
            
            # Add to undo stack
            self._add_to_undo_stack(snapshot)
            
            # Mark as pending change
            self.pending_changes = True
            
            # Notify callbacks
            for callback in self.state_change_callbacks:
                callback(snapshot)
                
        except Exception as e:
            self.signals.integration_error.emit("selection_changed", str(e))
    
    def _on_mode_changed(self, mode: SelectionMode) -> None:
        """Handle selection mode changes."""
        if self.config.persist_selection_mode:
            self.state_manager.set_user_preference('selection_mode', mode.value)
    
    def _on_strategy_changed(self, strategy: SelectionStrategy) -> None:
        """Handle selection strategy changes."""
        if self.config.persist_selection_mode:
            self.state_manager.set_user_preference('selection_strategy', strategy.value)
    
    def _on_state_saved(self, selection_id: str) -> None:
        """Handle state save completion."""
        self.signals.selection_persisted.emit(selection_id)
        if selection_id == self.current_state_id:
            self.pending_changes = False
    
    def _on_persistence_error(self, operation: str, error_message: str) -> None:
        """Handle persistence errors."""
        self.signals.integration_error.emit(operation, error_message)
    
    def _create_snapshot_from_selection(self, selection_state: SelectionState) -> SelectionStateSnapshot:
        """Create a snapshot from current selection state."""
        return SelectionStateSnapshot(
            selection_id=f"sel_{datetime.now().timestamp()}",
            timestamp=datetime.now(),
            selection_mode=selection_state.mode,
            selection_strategy=selection_state.strategy,
            selected_elements=[str(id(elem)) for elem in selection_state.selected_elements],
            selection_bounds=[elem.get_bounds() for elem in selection_state.selected_elements],
            metadata={
                'element_count': len(selection_state.selected_elements),
                'total_area': sum(
                    bounds.width * bounds.height 
                    for bounds in [elem.get_bounds() for elem in selection_state.selected_elements]
                )
            }
        )
    
    def _add_to_undo_stack(self, snapshot: SelectionStateSnapshot) -> None:
        """Add snapshot to undo stack."""
        # Clear redo stack when new action is performed
        self.redo_stack.clear()
        
        # Add to undo stack
        self.undo_stack.append(snapshot)
        
        # Limit stack size
        if len(self.undo_stack) > self.config.max_undo_history:
            self.undo_stack.pop(0)
        
        # Update current state
        self.current_state_id = snapshot.selection_id
        
        # Emit undo state change
        self.signals.undo_state_changed.emit(
            len(self.undo_stack) > 1,  # can_undo
            len(self.redo_stack) > 0   # can_redo
        )
    
    def _perform_auto_save(self) -> None:
        """Perform automatic save of current state."""
        if not self.pending_changes:
            return
        
        try:
            current_selection = self.selection_manager.get_current_state()
            if current_selection and current_selection.selected_elements:
                # Save to session scope
                selection_id = self.state_manager.save_selection_state(
                    current_selection,
                    scope=StateScope.SESSION
                )
                
                # Save viewport state if enabled
                if self.config.persist_viewport_state:
                    viewport_state = self._get_current_viewport_state()
                    if viewport_state:
                        self.state_manager.set_viewport_state(viewport_state)
                
                # Save to project scope if enabled
                if self.config.sync_with_project:
                    self.state_manager.save_selection_state(
                        current_selection,
                        scope=StateScope.PROJECT
                    )
                
                self.signals.auto_save_completed.emit()
                
        except Exception as e:
            self.signals.integration_error.emit("auto_save", str(e))
    
    def _get_current_viewport_state(self) -> Dict[str, Any]:
        """Get current viewport state."""
        # This would integrate with the viewport/overlay system
        # For now, return a placeholder
        return {
            'timestamp': datetime.now().isoformat(),
            'zoom_level': 1.0,
            'center_x': 0.0,
            'center_y': 0.0
        }
    
    def save_current_state(self, scope: StateScope = StateScope.SESSION) -> Optional[str]:
        """Manually save current selection state."""
        try:
            current_selection = self.selection_manager.get_current_state()
            if current_selection and current_selection.selected_elements:
                return self.state_manager.save_selection_state(
                    current_selection,
                    scope=scope
                )
            return None
            
        except Exception as e:
            self.signals.integration_error.emit("manual_save", str(e))
            return None
    
    def load_state(self, selection_id: str, scope: StateScope = StateScope.SESSION) -> bool:
        """Load a specific selection state."""
        try:
            snapshot = self.state_manager.load_selection_state(selection_id, scope)
            if snapshot:
                self._restore_selection_state(snapshot)
                self.signals.state_restored.emit(selection_id)
                return True
            return False
            
        except Exception as e:
            self.signals.integration_error.emit("load_state", str(e))
            return False
    
    def can_undo(self) -> bool:
        """Check if undo is possible."""
        return len(self.undo_stack) > 1
    
    def can_redo(self) -> bool:
        """Check if redo is possible."""
        return len(self.redo_stack) > 0
    
    def undo(self) -> bool:
        """Undo the last selection change."""
        if not self.can_undo():
            return False
        
        try:
            # Move current state to redo stack
            if self.undo_stack:
                current_state = self.undo_stack.pop()
                self.redo_stack.append(current_state)
            
            # Restore previous state
            if self.undo_stack:
                previous_state = self.undo_stack[-1]
                self._restore_selection_state(previous_state)
                
                # Update undo state
                self.signals.undo_state_changed.emit(
                    len(self.undo_stack) > 1,
                    len(self.redo_stack) > 0
                )
                
                return True
            
            return False
            
        except Exception as e:
            self.signals.integration_error.emit("undo", str(e))
            return False
    
    def redo(self) -> bool:
        """Redo the last undone selection change."""
        if not self.can_redo():
            return False
        
        try:
            # Move state from redo stack to undo stack
            next_state = self.redo_stack.pop()
            self.undo_stack.append(next_state)
            
            # Restore next state
            self._restore_selection_state(next_state)
            
            # Update undo state
            self.signals.undo_state_changed.emit(
                len(self.undo_stack) > 1,
                len(self.redo_stack) > 0
            )
            
            return True
            
        except Exception as e:
            self.signals.integration_error.emit("redo", str(e))
            return False
    
    def clear_undo_history(self) -> None:
        """Clear undo/redo history."""
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.signals.undo_state_changed.emit(False, False)
    
    def get_undo_history(self) -> List[SelectionStateSnapshot]:
        """Get undo history."""
        return self.undo_stack.copy()
    
    def get_redo_history(self) -> List[SelectionStateSnapshot]:
        """Get redo history."""
        return self.redo_stack.copy()
    
    def add_state_change_callback(self, callback: Callable[[SelectionStateSnapshot], None]) -> None:
        """Add callback for state changes."""
        self.state_change_callbacks.append(callback)
    
    def remove_state_change_callback(self, callback: Callable[[SelectionStateSnapshot], None]) -> None:
        """Remove callback for state changes."""
        if callback in self.state_change_callbacks:
            self.state_change_callbacks.remove(callback)
    
    def export_current_state(self, file_path: Path, format: StorageFormat = StorageFormat.JSON) -> bool:
        """Export current selection state to file."""
        try:
            current_selection = self.selection_manager.get_current_state()
            if current_selection and current_selection.selected_elements:
                snapshot = self._create_snapshot_from_selection(current_selection)
                
                persistence_manager = PersistenceManager(
                    StorageOptions(format=format)
                )
                
                return persistence_manager.save_selection_snapshot(snapshot, file_path)
            
            return False
            
        except Exception as e:
            self.signals.integration_error.emit("export_state", str(e))
            return False
    
    def import_state(self, file_path: Path, format: StorageFormat = StorageFormat.JSON) -> bool:
        """Import selection state from file."""
        try:
            persistence_manager = PersistenceManager(
                StorageOptions(format=format)
            )
            
            snapshot = persistence_manager.load_selection_snapshot(file_path)
            if snapshot:
                self._restore_selection_state(snapshot)
                self._add_to_undo_stack(snapshot)
                self.signals.state_restored.emit(snapshot.selection_id)
                return True
            
            return False
            
        except Exception as e:
            self.signals.integration_error.emit("import_state", str(e))
            return False
    
    def set_auto_save_enabled(self, enabled: bool) -> None:
        """Enable or disable auto-save."""
        self.config.auto_save_enabled = enabled
        
        if enabled:
            self.auto_save_timer.start(self.config.auto_save_interval * 1000)
        else:
            self.auto_save_timer.stop()
    
    def set_auto_save_interval(self, interval_seconds: int) -> None:
        """Set auto-save interval."""
        self.config.auto_save_interval = interval_seconds
        
        if self.config.auto_save_enabled:
            self.auto_save_timer.start(interval_seconds * 1000)
    
    def get_integration_statistics(self) -> Dict[str, Any]:
        """Get integration statistics."""
        return {
            'auto_save_enabled': self.config.auto_save_enabled,
            'auto_save_interval': self.config.auto_save_interval,
            'undo_stack_size': len(self.undo_stack),
            'redo_stack_size': len(self.redo_stack),
            'pending_changes': self.pending_changes,
            'current_state_id': self.current_state_id,
            'callbacks_registered': len(self.state_change_callbacks)
        }
    
    def cleanup(self) -> None:
        """Clean up resources."""
        # Stop auto-save timer
        if self.auto_save_timer.isActive():
            self.auto_save_timer.stop()
        
        # Perform final save if there are pending changes
        if self.pending_changes:
            self._perform_auto_save()
        
        # Clear state
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.state_change_callbacks.clear()
        self.current_state_id = None
        self.pending_changes = False