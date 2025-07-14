"""
Agent 2 Coordinator for Element Selection & State Management.
This module provides the main coordination class that brings together all Agent 2 components
and integrates them with Agent 1's overlay system.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from .selection import SelectionManager, SelectionState, SelectionMode, SelectionStrategy
from .multi_select import SelectionCriteria, SelectionAlgorithm
from .events import SelectionEventManager, SelectionEvent, EventType
from .state import SelectionStateManager, SelectionStateSnapshot, StateScope
from .persistence import PersistenceManager, StorageOptions, StorageFormat
from .state_integration import SelectionStateIntegration, StateIntegrationConfig
from .overlay_integration import OverlaySelectionIntegration, IntegrationMode, SelectionVisualFeedback
from .integration_api import OverlayIntegrationAPI
from .coordinates import Rectangle, Point


@dataclass
class Agent2Configuration:
    """Configuration for Agent 2 system."""
    # Selection configuration
    selection_mode: SelectionMode = SelectionMode.SINGLE
    selection_strategy: SelectionStrategy = None
    enable_multi_select: bool = True
    selection_tolerance: float = 5.0
    
    # State management configuration
    enable_state_persistence: bool = True
    auto_save_interval: int = 30  # seconds
    max_undo_history: int = 50
    state_storage_format: StorageFormat = StorageFormat.JSON
    
    # Overlay integration configuration
    integration_mode: IntegrationMode = IntegrationMode.ACTIVE
    sync_interval: int = 100  # milliseconds
    enable_visual_feedback: bool = True
    
    # Event system configuration
    enable_event_throttling: bool = True
    event_throttle_interval: int = 16  # milliseconds (~60fps)
    max_event_queue_size: int = 1000
    
    # Performance configuration
    enable_element_caching: bool = True
    cache_refresh_interval: int = 1000  # milliseconds
    performance_monitoring: bool = True
    
    def __post_init__(self):
        if self.selection_strategy is None:
            from .multi_select import SelectionStrategy
            self.selection_strategy = SelectionStrategy.CONTAINS


class Agent2Signals(QObject):
    """Signals for Agent 2 system events."""
    initialized = pyqtSignal()
    selection_changed = pyqtSignal(object)  # SelectionState
    state_saved = pyqtSignal(str)  # selection_id
    state_restored = pyqtSignal(str)  # selection_id
    overlay_synced = pyqtSignal()
    error_occurred = pyqtSignal(str, str)  # component, error_message
    performance_update = pyqtSignal(object)  # performance metrics


class Agent2ElementSelectionCoordinator:
    """
    Main coordinator for Agent 2 Element Selection & State Management system.
    
    This class coordinates all Agent 2 components and provides a unified interface
    for element selection operations with full state management and overlay integration.
    """
    
    def __init__(
        self,
        overlay_api: OverlayIntegrationAPI,
        project_path: Optional[Path] = None,
        config: Optional[Agent2Configuration] = None
    ):
        self.overlay_api = overlay_api
        self.project_path = project_path
        self.config = config or Agent2Configuration()
        self.signals = Agent2Signals()
        
        # Core components
        self.selection_manager: Optional[SelectionManager] = None
        self.state_manager: Optional[SelectionStateManager] = None
        self.event_manager: Optional[SelectionEventManager] = None
        self.overlay_integration: Optional[OverlaySelectionIntegration] = None
        self.state_integration: Optional[SelectionStateIntegration] = None
        self.persistence_manager: Optional[PersistenceManager] = None
        
        # Status tracking
        self.is_initialized = False
        self.last_sync_time: Optional[datetime] = None
        
        # Performance monitoring
        self.performance_metrics = {
            'selection_count': 0,
            'state_saves': 0,
            'overlay_syncs': 0,
            'average_selection_time': 0.0,
            'last_performance_check': datetime.now()
        }
        
        # Initialize the system
        self._initialize_system()
    
    def _initialize_system(self) -> None:
        """Initialize all Agent 2 components."""
        try:
            # Initialize core components
            self._initialize_selection_manager()
            self._initialize_state_manager()
            self._initialize_event_manager()
            self._initialize_persistence_manager()
            
            # Initialize integration components
            self._initialize_overlay_integration()
            self._initialize_state_integration()
            
            # Setup cross-component connections
            self._setup_component_connections()
            
            # Start performance monitoring
            if self.config.performance_monitoring:
                self._start_performance_monitoring()
            
            self.is_initialized = True
            self.signals.initialized.emit()
            
        except Exception as e:
            self.signals.error_occurred.emit("initialization", str(e))
            raise
    
    def _initialize_selection_manager(self) -> None:
        """Initialize the selection manager."""
        self.selection_manager = SelectionManager(self.overlay_api)
        
        # Configure selection manager
        self.selection_manager.set_selection_mode(self.config.selection_mode)
        self.selection_manager.set_selection_strategy(self.config.selection_strategy)
        
        # Connect signals
        self.selection_manager.selection_changed.connect(self._on_selection_changed)
        self.selection_manager.mode_changed.connect(self._on_mode_changed)
        self.selection_manager.strategy_changed.connect(self._on_strategy_changed)
    
    def _initialize_state_manager(self) -> None:
        """Initialize the state manager."""
        self.state_manager = SelectionStateManager(self.project_path)
        
        # Configure state manager
        if self.config.enable_state_persistence:
            from .state import StatePersistenceMode
            self.state_manager.set_persistence_mode(StatePersistenceMode.BATCHED)
        
        # Connect signals
        self.state_manager.signals.selection_saved.connect(self._on_state_saved)
        self.state_manager.signals.state_loaded.connect(self._on_state_loaded)
        self.state_manager.signals.persistence_error.connect(self._on_persistence_error)
    
    def _initialize_event_manager(self) -> None:
        """Initialize the event manager."""
        self.event_manager = SelectionEventManager()
        
        # Configure event manager
        if self.config.enable_event_throttling:
            self.event_manager.set_throttling_enabled(True)
            self.event_manager.set_throttle_interval(self.config.event_throttle_interval)
        
        # Set queue size limit
        self.event_manager.set_max_queue_size(self.config.max_event_queue_size)
    
    def _initialize_persistence_manager(self) -> None:
        """Initialize the persistence manager."""
        storage_options = StorageOptions(
            format=self.config.state_storage_format,
            include_metadata=True,
            validate_on_load=True
        )
        
        self.persistence_manager = PersistenceManager(storage_options)
    
    def _initialize_overlay_integration(self) -> None:
        """Initialize overlay integration."""
        self.overlay_integration = OverlaySelectionIntegration(
            self.selection_manager,
            self.overlay_api,
            self.config.integration_mode
        )
        
        # Configure visual feedback
        if self.config.enable_visual_feedback:
            feedback = SelectionVisualFeedback()
            self.overlay_integration.set_visual_feedback(feedback)
        
        # Initialize selection manager with overlay integration
        self.selection_manager.initialize_overlay_integration(self.overlay_integration)
        
        # Connect signals
        self.overlay_integration.signals.elements_discovered.connect(self._on_elements_discovered)
        self.overlay_integration.signals.selection_rendered.connect(self._on_selection_rendered)
        self.overlay_integration.signals.integration_error.connect(self._on_integration_error)
    
    def _initialize_state_integration(self) -> None:
        """Initialize state integration."""
        integration_config = StateIntegrationConfig(
            auto_save_enabled=self.config.enable_state_persistence,
            auto_save_interval=self.config.auto_save_interval,
            max_undo_history=self.config.max_undo_history
        )
        
        self.state_integration = SelectionStateIntegration(
            self.selection_manager,
            self.state_manager,
            integration_config
        )
        
        # Connect signals
        self.state_integration.signals.state_restored.connect(self._on_state_restored)
        self.state_integration.signals.auto_save_completed.connect(self._on_auto_save_completed)
        self.state_integration.signals.undo_state_changed.connect(self._on_undo_state_changed)
    
    def _setup_component_connections(self) -> None:
        """Setup connections between components."""
        # Connect selection manager to event manager
        self.selection_manager.selection_changed.connect(self._publish_selection_event)
        
        # Connect state manager to event manager
        self.state_manager.signals.selection_saved.connect(self._publish_state_event)
        
        # Connect overlay integration to event manager
        self.overlay_integration.signals.selection_rendered.connect(self._publish_render_event)
    
    def _start_performance_monitoring(self) -> None:
        """Start performance monitoring."""
        self.performance_timer = QTimer()
        self.performance_timer.timeout.connect(self._update_performance_metrics)
        self.performance_timer.start(5000)  # Update every 5 seconds
    
    # Event handlers
    
    def _on_selection_changed(self, selection_state: SelectionState) -> None:
        """Handle selection changes."""
        self.performance_metrics['selection_count'] += 1
        self.signals.selection_changed.emit(selection_state)
    
    def _on_mode_changed(self, mode: SelectionMode) -> None:
        """Handle mode changes."""
        # Update configuration
        self.config.selection_mode = mode
    
    def _on_strategy_changed(self, strategy: SelectionStrategy) -> None:
        """Handle strategy changes."""
        # Update configuration
        self.config.selection_strategy = strategy
    
    def _on_state_saved(self, selection_id: str) -> None:
        """Handle state save completion."""
        self.performance_metrics['state_saves'] += 1
        self.signals.state_saved.emit(selection_id)
    
    def _on_state_loaded(self, scope: str, selection_id: str) -> None:
        """Handle state load completion."""
        pass
    
    def _on_state_restored(self, selection_id: str) -> None:
        """Handle state restoration."""
        self.signals.state_restored.emit(selection_id)
    
    def _on_auto_save_completed(self) -> None:
        """Handle auto-save completion."""
        pass
    
    def _on_undo_state_changed(self, can_undo: bool, can_redo: bool) -> None:
        """Handle undo state changes."""
        pass
    
    def _on_elements_discovered(self, count: int) -> None:
        """Handle element discovery."""
        pass
    
    def _on_selection_rendered(self, selection_id: str) -> None:
        """Handle selection rendering."""
        self.performance_metrics['overlay_syncs'] += 1
        self.signals.overlay_synced.emit()
    
    def _on_integration_error(self, operation: str, error: str) -> None:
        """Handle integration errors."""
        self.signals.error_occurred.emit(f"overlay_{operation}", error)
    
    def _on_persistence_error(self, operation: str, error: str) -> None:
        """Handle persistence errors."""
        self.signals.error_occurred.emit(f"persistence_{operation}", error)
    
    def _publish_selection_event(self, selection_state: SelectionState) -> None:
        """Publish selection change event."""
        event = SelectionEvent(
            event_type=EventType.SELECTION_CHANGED,
            selection_state=selection_state,
            timestamp=datetime.now()
        )
        self.event_manager.publish(event)
    
    def _publish_state_event(self, selection_id: str) -> None:
        """Publish state save event."""
        event = SelectionEvent(
            event_type=EventType.STATE_SAVED,
            selection_id=selection_id,
            timestamp=datetime.now()
        )
        self.event_manager.publish(event)
    
    def _publish_render_event(self, selection_id: str) -> None:
        """Publish render event."""
        event = SelectionEvent(
            event_type=EventType.SELECTION_RENDERED,
            selection_id=selection_id,
            timestamp=datetime.now()
        )
        self.event_manager.publish(event)
    
    def _update_performance_metrics(self) -> None:
        """Update performance metrics."""
        current_time = datetime.now()
        
        # Update last performance check
        self.performance_metrics['last_performance_check'] = current_time
        
        # Get additional metrics from components
        if self.selection_manager:
            selection_metrics = self.selection_manager.selection_metrics
            self.performance_metrics['average_selection_time'] = selection_metrics.get('average_selection_time', 0.0)
        
        if self.state_manager:
            state_metrics = self.state_manager.get_state_statistics()
            self.performance_metrics.update(state_metrics)
        
        if self.overlay_integration:
            overlay_metrics = self.overlay_integration.get_integration_statistics()
            self.performance_metrics.update(overlay_metrics)
        
        # Emit performance update
        self.signals.performance_update.emit(self.performance_metrics)
    
    # Public API
    
    def select_elements(
        self,
        selection_criteria: Union[Rectangle, List[Point], Dict[str, Any]],
        operation: str = "replace"
    ) -> List[str]:
        """
        Select elements using various criteria.
        
        Args:
            selection_criteria: Rectangular bounds, polygon points, or complex criteria
            operation: Selection operation ("replace", "add", "remove", "toggle")
            
        Returns:
            List of selected element IDs
        """
        if not self.is_initialized:
            return []
        
        try:
            # Convert criteria to standard format
            if isinstance(selection_criteria, Rectangle):
                criteria = {"bounds": selection_criteria}
            elif isinstance(selection_criteria, list):
                criteria = {"polygon": selection_criteria}
            elif isinstance(selection_criteria, dict):
                criteria = selection_criteria
            else:
                return []
            
            # Perform selection
            selected_ids = self.selection_manager.select_with_overlay(criteria)
            
            return selected_ids
            
        except Exception as e:
            self.signals.error_occurred.emit("selection", str(e))
            return []
    
    def get_current_selection(self) -> SelectionState:
        """Get the current selection state."""
        if self.selection_manager:
            return self.selection_manager.get_current_state()
        return SelectionState()
    
    def clear_selection(self) -> None:
        """Clear the current selection."""
        if self.selection_manager:
            self.selection_manager.clear_selection()
    
    def set_selection_mode(self, mode: SelectionMode) -> None:
        """Set the selection mode."""
        if self.selection_manager:
            self.selection_manager.set_selection_mode(mode)
    
    def set_selection_strategy(self, strategy: SelectionStrategy) -> None:
        """Set the selection strategy."""
        if self.selection_manager:
            self.selection_manager.set_selection_strategy(strategy)
    
    def save_current_selection(self, selection_id: Optional[str] = None) -> Optional[str]:
        """Save the current selection state."""
        if self.state_integration:
            return self.state_integration.save_current_state()
        return None
    
    def load_selection(self, selection_id: str) -> bool:
        """Load a saved selection state."""
        if self.state_integration:
            return self.state_integration.load_state(selection_id)
        return False
    
    def can_undo(self) -> bool:
        """Check if undo is possible."""
        if self.state_integration:
            return self.state_integration.can_undo()
        return False
    
    def can_redo(self) -> bool:
        """Check if redo is possible."""
        if self.state_integration:
            return self.state_integration.can_redo()
        return False
    
    def undo(self) -> bool:
        """Undo the last selection change."""
        if self.state_integration:
            return self.state_integration.undo()
        return False
    
    def redo(self) -> bool:
        """Redo the last undone selection change."""
        if self.state_integration:
            return self.state_integration.redo()
        return False
    
    def export_selection(self, file_path: Path, format: StorageFormat = StorageFormat.JSON) -> bool:
        """Export current selection to file."""
        if self.state_integration:
            return self.state_integration.export_current_state(file_path, format)
        return False
    
    def import_selection(self, file_path: Path, format: StorageFormat = StorageFormat.JSON) -> bool:
        """Import selection from file."""
        if self.state_integration:
            return self.state_integration.import_state(file_path, format)
        return False
    
    def get_selectable_elements(self, region: Rectangle) -> List[Any]:
        """Get selectable elements in a region."""
        if self.overlay_integration:
            return self.overlay_integration.get_selectable_elements(region)
        return []
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get system performance metrics."""
        return self.performance_metrics.copy()
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        return {
            'initialized': self.is_initialized,
            'selection_manager': self.selection_manager is not None,
            'state_manager': self.state_manager is not None,
            'overlay_integration': self.overlay_integration is not None,
            'state_integration': self.state_integration is not None,
            'last_sync_time': self.last_sync_time,
            'performance_metrics': self.performance_metrics,
            'configuration': {
                'selection_mode': self.config.selection_mode.value,
                'integration_mode': self.config.integration_mode.value,
                'state_persistence': self.config.enable_state_persistence,
                'visual_feedback': self.config.enable_visual_feedback
            }
        }
    
    def cleanup(self) -> None:
        """Clean up all resources."""
        # Stop performance monitoring
        if hasattr(self, 'performance_timer'):
            self.performance_timer.stop()
        
        # Clean up components
        if self.state_integration:
            self.state_integration.cleanup()
        
        if self.overlay_integration:
            self.overlay_integration.cleanup()
        
        if self.state_manager:
            self.state_manager.cleanup()
        
        if self.event_manager:
            self.event_manager.cleanup()
        
        # Reset state
        self.is_initialized = False
        self.last_sync_time = None