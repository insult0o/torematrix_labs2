"""
State Management Integration for Hierarchical Element List

Provides integration with the application's State Management system for
persistent state, undo/redo operations, and state synchronization.
"""

import logging
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, asdict
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

logger = logging.getLogger(__name__)


@dataclass
class ElementListState:
    """State data for element list"""
    expanded_elements: Set[str]
    selected_elements: List[str]
    sort_criteria: List[Dict[str, Any]]
    grouping_criteria: List[Dict[str, Any]]
    filter_config: Dict[str, Any]
    view_position: Dict[str, Any]
    bookmarks: List[Dict[str, Any]]
    last_updated: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['expanded_elements'] = list(self.expanded_elements)
        data['last_updated'] = self.last_updated.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ElementListState':
        """Create from dictionary"""
        if isinstance(data.get('expanded_elements'), list):
            data['expanded_elements'] = set(data['expanded_elements'])
        if isinstance(data.get('last_updated'), str):
            data['last_updated'] = datetime.fromisoformat(data['last_updated'])
        return cls(**data)


class ElementListStateIntegration(QObject):
    """
    State Management integration for hierarchical element list
    
    Manages persistent state, state synchronization, and provides
    undo/redo functionality for element list operations.
    """
    
    # Signals
    state_restored = pyqtSignal(object)  # ElementListState
    state_saved = pyqtSignal(object)  # ElementListState
    undo_available = pyqtSignal(bool)
    redo_available = pyqtSignal(bool)
    
    def __init__(self, element_list_widget, parent: Optional[QObject] = None):
        """
        Initialize State Management integration
        
        Args:
            element_list_widget: The element list widget to integrate
            parent: Parent QObject
        """
        super().__init__(parent)
        
        self.element_list = element_list_widget
        self.state_manager = None  # Will be set when connecting
        
        # Configuration
        self.auto_save_interval = 5000  # 5 seconds
        self.max_undo_states = 50
        self.enable_state_persistence = True
        
        # State tracking
        self._current_state: Optional[ElementListState] = None
        self._state_history: List[ElementListState] = []
        self._history_index = -1
        self._last_save_time = datetime.now()
        
        # Auto-save timer
        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._save_current_state)
        
        logger.info("ElementListStateIntegration initialized")
    
    def connect_to_state_manager(self, state_manager) -> None:
        """
        Connect to the application's State Manager
        
        Args:
            state_manager: State Manager instance to connect to
        """
        self.state_manager = state_manager
        
        # Restore saved state if available
        self._restore_saved_state()
        
        logger.info("Connected to State Manager")
    
    def save_current_state(self) -> bool:
        """
        Save current element list state
        
        Returns:
            True if state was saved successfully
        """
        try:
            current_state = self._capture_current_state()
            
            if self.state_manager and self.enable_state_persistence:
                # Save to state manager
                state_data = current_state.to_dict()
                success = self.state_manager.save_component_state('element_list', state_data)
                
                if success:
                    self._current_state = current_state
                    self._last_save_time = datetime.now()
                    
                    logger.debug("Element list state saved")
                    self.state_saved.emit(current_state)
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to save element list state: {e}")
            return False
    
    def restore_state(self, state: ElementListState) -> bool:
        """
        Restore element list to specified state
        
        Args:
            state: State to restore to
            
        Returns:
            True if state was restored successfully
        """
        try:
            # Restore expanded elements
            if hasattr(self.element_list, 'set_expanded_elements'):
                self.element_list.set_expanded_elements(state.expanded_elements)
            
            # Restore selection
            if hasattr(self.element_list, 'set_selected_elements'):
                self.element_list.set_selected_elements(state.selected_elements)
            
            # Restore sort criteria
            if hasattr(self.element_list, 'set_sort_criteria') and state.sort_criteria:
                self.element_list.set_sort_criteria(state.sort_criteria)
            
            # Restore grouping criteria
            if hasattr(self.element_list, 'set_grouping_criteria') and state.grouping_criteria:
                self.element_list.set_grouping_criteria(state.grouping_criteria)
            
            # Restore filter
            if hasattr(self.element_list, 'apply_filter') and state.filter_config:
                self.element_list.apply_filter(state.filter_config)
            
            # Restore view position
            if hasattr(self.element_list, 'set_view_position') and state.view_position:
                self.element_list.set_view_position(state.view_position)
            
            self._current_state = state
            
            logger.debug("Element list state restored")
            self.state_restored.emit(state)
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore element list state: {e}")
            return False
    
    def create_undo_point(self) -> None:
        """Create an undo point with current state"""
        try:
            current_state = self._capture_current_state()
            
            # Remove future states if we're not at the end
            if self._history_index < len(self._state_history) - 1:
                self._state_history = self._state_history[:self._history_index + 1]
            
            # Add current state
            self._state_history.append(current_state)
            self._history_index = len(self._state_history) - 1
            
            # Limit history size
            if len(self._state_history) > self.max_undo_states:
                self._state_history.pop(0)
                self._history_index -= 1
            
            self._update_undo_redo_availability()
            
            logger.debug(f"Created undo point, history size: {len(self._state_history)}")
            
        except Exception as e:
            logger.error(f"Failed to create undo point: {e}")
    
    def undo(self) -> bool:
        """
        Undo to previous state
        
        Returns:
            True if undo was successful
        """
        if not self.can_undo():
            return False
        
        try:
            self._history_index -= 1
            previous_state = self._state_history[self._history_index]
            
            success = self.restore_state(previous_state)
            
            if success:
                self._update_undo_redo_availability()
                logger.debug(f"Undo successful, index: {self._history_index}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to undo: {e}")
            return False
    
    def redo(self) -> bool:
        """
        Redo to next state
        
        Returns:
            True if redo was successful
        """
        if not self.can_redo():
            return False
        
        try:
            self._history_index += 1
            next_state = self._state_history[self._history_index]
            
            success = self.restore_state(next_state)
            
            if success:
                self._update_undo_redo_availability()
                logger.debug(f"Redo successful, index: {self._history_index}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to redo: {e}")
            return False
    
    def can_undo(self) -> bool:
        """Check if undo is available"""
        return self._history_index > 0
    
    def can_redo(self) -> bool:
        """Check if redo is available"""
        return self._history_index < len(self._state_history) - 1
    
    def clear_history(self) -> None:
        """Clear undo/redo history"""
        self._state_history.clear()
        self._history_index = -1
        self._update_undo_redo_availability()
        logger.debug("Undo/redo history cleared")
    
    def schedule_auto_save(self) -> None:
        """Schedule automatic state save"""
        if self.auto_save_interval > 0:
            self._save_timer.start(self.auto_save_interval)
    
    def get_current_state(self) -> Optional[ElementListState]:
        """Get current element list state"""
        return self._current_state
    
    def _capture_current_state(self) -> ElementListState:
        """Capture current element list state"""
        # Get expanded elements
        expanded_elements = set()
        if hasattr(self.element_list, 'get_expanded_elements'):
            expanded_elements = self.element_list.get_expanded_elements()
        
        # Get selected elements
        selected_elements = []
        if hasattr(self.element_list, 'get_selected_elements'):
            selected_elements = self.element_list.get_selected_elements()
        
        # Get sort criteria
        sort_criteria = []
        if hasattr(self.element_list, 'get_sort_criteria'):
            sort_criteria = self.element_list.get_sort_criteria()
        
        # Get grouping criteria
        grouping_criteria = []
        if hasattr(self.element_list, 'get_grouping_criteria'):
            grouping_criteria = self.element_list.get_grouping_criteria()
        
        # Get filter config
        filter_config = {}
        if hasattr(self.element_list, 'get_filter_config'):
            filter_config = self.element_list.get_filter_config()
        
        # Get view position
        view_position = {}
        if hasattr(self.element_list, 'get_view_position'):
            view_position = self.element_list.get_view_position()
        
        # Get bookmarks
        bookmarks = []
        if hasattr(self.element_list, 'get_bookmarks'):
            bookmarks = self.element_list.get_bookmarks()
        
        return ElementListState(
            expanded_elements=expanded_elements,
            selected_elements=selected_elements,
            sort_criteria=sort_criteria,
            grouping_criteria=grouping_criteria,
            filter_config=filter_config,
            view_position=view_position,
            bookmarks=bookmarks,
            last_updated=datetime.now()
        )
    
    def _restore_saved_state(self) -> None:
        """Restore previously saved state from state manager"""
        if not self.state_manager:
            return
        
        try:
            state_data = self.state_manager.get_component_state('element_list')
            
            if state_data:
                state = ElementListState.from_dict(state_data)
                self.restore_state(state)
                logger.info("Restored saved element list state")
            
        except Exception as e:
            logger.warning(f"Failed to restore saved state: {e}")
    
    def _save_current_state(self) -> None:
        """Timer callback to save current state"""
        self.save_current_state()
    
    def _update_undo_redo_availability(self) -> None:
        """Update undo/redo availability signals"""
        self.undo_available.emit(self.can_undo())
        self.redo_available.emit(self.can_redo())