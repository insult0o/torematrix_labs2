"""
Event Bus Integration for Hierarchical Element List

Provides comprehensive integration with the application's Event Bus system
for reactive updates, system-wide notifications, and event-driven workflows.
"""

import logging
from typing import Dict, Any, Optional, List, Callable, Set
from dataclasses import dataclass
from enum import Enum
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QWidget

logger = logging.getLogger(__name__)


class ElementListEventType(Enum):
    """Event types specific to element list operations"""
    ELEMENT_SELECTED = "element_list.element_selected"
    ELEMENT_EXPANDED = "element_list.element_expanded"
    ELEMENT_COLLAPSED = "element_list.element_collapsed"
    SELECTION_CHANGED = "element_list.selection_changed"
    TREE_STRUCTURE_CHANGED = "element_list.tree_structure_changed"
    FILTER_APPLIED = "element_list.filter_applied"
    SORT_APPLIED = "element_list.sort_applied"
    GROUP_APPLIED = "element_list.group_applied"
    NAVIGATION_OCCURRED = "element_list.navigation_occurred"
    BOOKMARK_ACCESSED = "element_list.bookmark_accessed"
    CONTEXT_MENU_REQUESTED = "element_list.context_menu_requested"


@dataclass
class ElementListEvent:
    """Event data for element list operations"""
    event_type: ElementListEventType
    element_id: Optional[str] = None
    element_ids: Optional[List[str]] = None
    data: Dict[str, Any] = None
    source_component: str = "element_list"
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.data is None:
            self.data = {}
        if self.timestamp == 0.0:
            import time
            self.timestamp = time.time()


class ElementListEventIntegration(QObject):
    """
    Event Bus integration for hierarchical element list
    
    Manages bi-directional communication between the element list and the
    application's Event Bus system for reactive updates and notifications.
    """
    
    # Internal signals for Qt integration
    element_updated = pyqtSignal(str, dict)  # element_id, update_data
    tree_refresh_requested = pyqtSignal()
    selection_sync_requested = pyqtSignal(list)  # element_ids
    filter_update_requested = pyqtSignal(dict)  # filter_config
    
    def __init__(self, element_list_widget: QWidget, parent: Optional[QObject] = None):
        """
        Initialize Event Bus integration
        
        Args:
            element_list_widget: The element list widget to integrate
            parent: Parent QObject
        """
        super().__init__(parent)
        
        self.element_list = element_list_widget
        self.event_bus = None  # Will be set when connecting to event bus
        
        # Configuration
        self.enable_auto_sync = True
        self.debounce_delay = 100  # ms
        self.batch_events = True
        
        # Event tracking
        self._subscribed_events: Set[str] = set()
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._pending_events: List[ElementListEvent] = []
        self._last_selection_sync = []
        
        # Debouncing timers
        self._selection_timer = QTimer()
        self._selection_timer.setSingleShot(True)
        self._selection_timer.timeout.connect(self._emit_pending_selection_change)
        
        self._batch_timer = QTimer()
        self._batch_timer.setSingleShot(True)
        self._batch_timer.timeout.connect(self._process_batched_events)
        
        # Setup internal connections
        self._setup_internal_connections()
        
        logger.info("ElementListEventIntegration initialized")
    
    def connect_to_event_bus(self, event_bus) -> None:
        """
        Connect to the application's Event Bus
        
        Args:
            event_bus: Event Bus instance to connect to
        """
        self.event_bus = event_bus
        
        # Subscribe to relevant system events
        self._subscribe_to_system_events()
        
        logger.info("Connected to Event Bus")
    
    def disconnect_from_event_bus(self) -> None:
        """Disconnect from the Event Bus"""
        if self.event_bus:
            # Unsubscribe from all events
            for event_type in self._subscribed_events:
                try:
                    self.event_bus.unsubscribe(event_type, self._handle_system_event)
                except Exception as e:
                    logger.warning(f"Failed to unsubscribe from {event_type}: {e}")
            
            self._subscribed_events.clear()
            self.event_bus = None
            
            logger.info("Disconnected from Event Bus")
    
    def emit_element_selected(self, element_id: str, additional_data: Optional[Dict[str, Any]] = None) -> None:
        """
        Emit element selection event
        
        Args:
            element_id: ID of selected element
            additional_data: Additional event data
        """
        event = ElementListEvent(
            event_type=ElementListEventType.ELEMENT_SELECTED,
            element_id=element_id,
            data=additional_data or {}
        )
        
        self._emit_event(event)
    
    def emit_selection_changed(self, element_ids: List[str], additional_data: Optional[Dict[str, Any]] = None) -> None:
        """
        Emit selection change event (with debouncing)
        
        Args:
            element_ids: List of selected element IDs
            additional_data: Additional event data
        """
        # Store pending selection change
        self._pending_selection_event = ElementListEvent(
            event_type=ElementListEventType.SELECTION_CHANGED,
            element_ids=element_ids.copy(),
            data=additional_data or {}
        )
        
        # Start/restart debounce timer
        self._selection_timer.start(self.debounce_delay)
    
    def emit_element_expanded(self, element_id: str, is_expanded: bool, additional_data: Optional[Dict[str, Any]] = None) -> None:
        """
        Emit element expansion/collapse event
        
        Args:
            element_id: ID of element that was expanded/collapsed
            is_expanded: True if expanded, False if collapsed
            additional_data: Additional event data
        """
        event_type = ElementListEventType.ELEMENT_EXPANDED if is_expanded else ElementListEventType.ELEMENT_COLLAPSED
        
        event = ElementListEvent(
            event_type=event_type,
            element_id=element_id,
            data={**(additional_data or {}), 'is_expanded': is_expanded}
        )
        
        self._emit_event(event)
    
    def emit_tree_structure_changed(self, change_type: str, affected_elements: List[str], additional_data: Optional[Dict[str, Any]] = None) -> None:
        """
        Emit tree structure change event
        
        Args:
            change_type: Type of change (added, removed, moved, etc.)
            affected_elements: List of affected element IDs
            additional_data: Additional event data
        """
        event = ElementListEvent(
            event_type=ElementListEventType.TREE_STRUCTURE_CHANGED,
            element_ids=affected_elements,
            data={
                'change_type': change_type,
                **(additional_data or {})
            }
        )
        
        self._emit_event(event)
    
    def emit_filter_applied(self, filter_config: Dict[str, Any], result_count: int) -> None:
        """
        Emit filter applied event
        
        Args:
            filter_config: Applied filter configuration
            result_count: Number of results after filtering
        """
        event = ElementListEvent(
            event_type=ElementListEventType.FILTER_APPLIED,
            data={
                'filter_config': filter_config,
                'result_count': result_count
            }
        )
        
        self._emit_event(event)
    
    def emit_sort_applied(self, sort_criteria: List[Dict[str, Any]], result_order: List[str]) -> None:
        """
        Emit sort applied event
        
        Args:
            sort_criteria: Applied sort criteria
            result_order: Ordered list of element IDs after sorting
        """
        event = ElementListEvent(
            event_type=ElementListEventType.SORT_APPLIED,
            element_ids=result_order,
            data={'sort_criteria': sort_criteria}
        )
        
        self._emit_event(event)
    
    def emit_navigation_occurred(self, navigation_type: str, target_element: str, source_element: Optional[str] = None) -> None:
        """
        Emit navigation event
        
        Args:
            navigation_type: Type of navigation (click, keyboard, bookmark, etc.)
            target_element: Target element ID
            source_element: Source element ID (if applicable)
        """
        event = ElementListEvent(
            event_type=ElementListEventType.NAVIGATION_OCCURRED,
            element_id=target_element,
            data={
                'navigation_type': navigation_type,
                'source_element': source_element
            }
        )
        
        self._emit_event(event)
    
    def emit_bookmark_accessed(self, bookmark_id: str, element_id: str, bookmark_data: Dict[str, Any]) -> None:
        """
        Emit bookmark access event
        
        Args:
            bookmark_id: ID of accessed bookmark
            element_id: Element ID that was navigated to
            bookmark_data: Bookmark data
        """
        event = ElementListEvent(
            event_type=ElementListEventType.BOOKMARK_ACCESSED,
            element_id=element_id,
            data={
                'bookmark_id': bookmark_id,
                'bookmark_data': bookmark_data
            }
        )
        
        self._emit_event(event)
    
    def register_event_handler(self, event_type: ElementListEventType, handler: Callable[[ElementListEvent], None]) -> None:
        """
        Register a custom event handler
        
        Args:
            event_type: Type of event to handle
            handler: Handler function
        """
        event_key = event_type.value
        if event_key not in self._event_handlers:
            self._event_handlers[event_key] = []
        
        self._event_handlers[event_key].append(handler)
        logger.debug(f"Registered event handler for {event_type.value}")
    
    def unregister_event_handler(self, event_type: ElementListEventType, handler: Callable[[ElementListEvent], None]) -> None:
        """
        Unregister an event handler
        
        Args:
            event_type: Type of event to stop handling
            handler: Handler function to remove
        """
        event_key = event_type.value
        if event_key in self._event_handlers:
            try:
                self._event_handlers[event_key].remove(handler)
                logger.debug(f"Unregistered event handler for {event_type.value}")
            except ValueError:
                pass  # Handler not in list
    
    def _setup_internal_connections(self) -> None:
        """Setup connections to element list widget signals"""
        if hasattr(self.element_list, 'elementSelected'):
            self.element_list.elementSelected.connect(self.emit_element_selected)
        
        if hasattr(self.element_list, 'selectionChanged'):
            self.element_list.selectionChanged.connect(self.emit_selection_changed)
        
        if hasattr(self.element_list, 'elementExpanded'):
            self.element_list.elementExpanded.connect(lambda eid: self.emit_element_expanded(eid, True))
        
        if hasattr(self.element_list, 'elementCollapsed'):
            self.element_list.elementCollapsed.connect(lambda eid: self.emit_element_expanded(eid, False))
        
        # Connect internal signals
        self.element_updated.connect(self._handle_element_update)
        self.tree_refresh_requested.connect(self._handle_tree_refresh)
        self.selection_sync_requested.connect(self._handle_selection_sync)
        self.filter_update_requested.connect(self._handle_filter_update)
    
    def _subscribe_to_system_events(self) -> None:
        """Subscribe to relevant system events from Event Bus"""
        if not self.event_bus:
            return
        
        # Document-related events
        system_events = [
            "document.loaded",
            "document.updated", 
            "document.element_added",
            "document.element_removed",
            "document.element_modified",
            "document.structure_changed",
            "document.metadata_updated",
            
            # Application events
            "app.theme_changed",
            "app.preferences_updated",
            "app.zoom_changed",
            
            # Selection synchronization events
            "selection.element_selected",
            "selection.multiple_selected",
            "selection.cleared",
            
            # View synchronization events
            "view.focus_element",
            "view.scroll_to_element",
            "view.highlight_elements",
            
            # Filter and search events
            "search.results_updated",
            "filter.applied",
            "filter.cleared"
        ]
        
        for event_type in system_events:
            try:
                self.event_bus.subscribe(event_type, self._handle_system_event)
                self._subscribed_events.add(event_type)
            except Exception as e:
                logger.warning(f"Failed to subscribe to {event_type}: {e}")
        
        logger.debug(f"Subscribed to {len(self._subscribed_events)} system events")
    
    def _emit_event(self, event: ElementListEvent) -> None:
        """
        Emit an event to the Event Bus and internal handlers
        
        Args:
            event: Event to emit
        """
        # Handle internally first
        self._handle_internal_event(event)
        
        # Emit to Event Bus if connected
        if self.event_bus:
            try:
                # Convert to Event Bus format
                event_data = {
                    'source': 'element_list',
                    'element_id': event.element_id,
                    'element_ids': event.element_ids,
                    'timestamp': event.timestamp,
                    **event.data
                }
                
                if self.batch_events:
                    # Add to batch
                    self._pending_events.append(event)
                    self._batch_timer.start(self.debounce_delay)
                else:
                    # Emit immediately
                    self.event_bus.emit(event.event_type.value, event_data)
                
            except Exception as e:
                logger.error(f"Failed to emit event {event.event_type.value}: {e}")
    
    def _handle_internal_event(self, event: ElementListEvent) -> None:
        """Handle event with internal handlers"""
        event_key = event.event_type.value
        handlers = self._event_handlers.get(event_key, [])
        
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Error in event handler for {event_key}: {e}")
    
    def _handle_system_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """
        Handle system event from Event Bus
        
        Args:
            event_type: Type of system event
            event_data: Event data
        """
        try:
            if event_type.startswith("document."):
                self._handle_document_event(event_type, event_data)
            elif event_type.startswith("selection."):
                self._handle_selection_event(event_type, event_data)
            elif event_type.startswith("view."):
                self._handle_view_event(event_type, event_data)
            elif event_type.startswith("app."):
                self._handle_app_event(event_type, event_data)
            elif event_type.startswith(("search.", "filter.")):
                self._handle_search_filter_event(event_type, event_data)
            
        except Exception as e:
            logger.error(f"Error handling system event {event_type}: {e}")
    
    def _handle_document_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """Handle document-related events"""
        if event_type in ("document.loaded", "document.structure_changed"):
            # Refresh tree
            self.tree_refresh_requested.emit()
        elif event_type in ("document.element_added", "document.element_removed", "document.element_modified"):
            # Update specific element
            element_id = event_data.get('element_id')
            if element_id:
                self.element_updated.emit(element_id, event_data)
        elif event_type == "document.metadata_updated":
            # Refresh if metadata affects display
            if self._affects_element_display(event_data):
                self.tree_refresh_requested.emit()
    
    def _handle_selection_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """Handle selection synchronization events"""
        if not self.enable_auto_sync:
            return
        
        if event_type == "selection.element_selected":
            element_id = event_data.get('element_id')
            if element_id:
                self.selection_sync_requested.emit([element_id])
        elif event_type == "selection.multiple_selected":
            element_ids = event_data.get('element_ids', [])
            if element_ids:
                self.selection_sync_requested.emit(element_ids)
        elif event_type == "selection.cleared":
            self.selection_sync_requested.emit([])
    
    def _handle_view_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """Handle view-related events"""
        if event_type == "view.focus_element":
            element_id = event_data.get('element_id')
            if element_id and hasattr(self.element_list, 'focus_element'):
                self.element_list.focus_element(element_id)
        elif event_type == "view.scroll_to_element":
            element_id = event_data.get('element_id')
            if element_id and hasattr(self.element_list, 'scroll_to_element'):
                self.element_list.scroll_to_element(element_id)
        elif event_type == "view.highlight_elements":
            element_ids = event_data.get('element_ids', [])
            if element_ids and hasattr(self.element_list, 'highlight_elements'):
                self.element_list.highlight_elements(element_ids)
    
    def _handle_app_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """Handle application-level events"""
        if event_type == "app.theme_changed":
            # Refresh styling
            if hasattr(self.element_list, 'update_theme'):
                self.element_list.update_theme(event_data.get('theme'))
        elif event_type == "app.preferences_updated":
            # Update preferences
            if hasattr(self.element_list, 'update_preferences'):
                self.element_list.update_preferences(event_data.get('preferences'))
    
    def _handle_search_filter_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """Handle search and filter events"""
        if event_type in ("search.results_updated", "filter.applied"):
            filter_config = event_data.get('filter_config', {})
            self.filter_update_requested.emit(filter_config)
        elif event_type == "filter.cleared":
            self.filter_update_requested.emit({})
    
    def _affects_element_display(self, event_data: Dict[str, Any]) -> bool:
        """Check if metadata update affects element display"""
        # Check if updated metadata affects tree display
        updated_fields = event_data.get('updated_fields', [])
        display_fields = ['name', 'type', 'icon', 'color', 'status', 'visible']
        
        return any(field in display_fields for field in updated_fields)
    
    def _emit_pending_selection_change(self) -> None:
        """Emit pending selection change event"""
        if hasattr(self, '_pending_selection_event'):
            event = self._pending_selection_event
            
            # Avoid duplicate events
            if event.element_ids != self._last_selection_sync:
                self._last_selection_sync = event.element_ids.copy() if event.element_ids else []
                self._emit_event(event)
            
            delattr(self, '_pending_selection_event')
    
    def _process_batched_events(self) -> None:
        """Process batched events"""
        if not self._pending_events or not self.event_bus:
            return
        
        # Group events by type
        event_groups = {}
        for event in self._pending_events:
            event_type = event.event_type.value
            if event_type not in event_groups:
                event_groups[event_type] = []
            event_groups[event_type].append(event)
        
        # Emit grouped events
        for event_type, events in event_groups.items():
            try:
                if len(events) == 1:
                    # Single event
                    event = events[0]
                    event_data = {
                        'source': 'element_list',
                        'element_id': event.element_id,
                        'element_ids': event.element_ids,
                        'timestamp': event.timestamp,
                        **event.data
                    }
                    self.event_bus.emit(event_type, event_data)
                else:
                    # Batch event
                    all_element_ids = []
                    combined_data = {'batch_size': len(events), 'events': []}
                    
                    for event in events:
                        if event.element_id:
                            all_element_ids.append(event.element_id)
                        if event.element_ids:
                            all_element_ids.extend(event.element_ids)
                        
                        combined_data['events'].append({
                            'element_id': event.element_id,
                            'element_ids': event.element_ids,
                            'timestamp': event.timestamp,
                            **event.data
                        })
                    
                    batch_event_data = {
                        'source': 'element_list',
                        'element_ids': all_element_ids,
                        'timestamp': events[-1].timestamp,
                        **combined_data
                    }
                    
                    self.event_bus.emit(f"{event_type}.batch", batch_event_data)
                
            except Exception as e:
                logger.error(f"Failed to emit batched event {event_type}: {e}")
        
        # Clear pending events
        self._pending_events.clear()
    
    # Qt slot handlers for internal signals
    
    def _handle_element_update(self, element_id: str, update_data: Dict[str, Any]) -> None:
        """Handle element update signal"""
        if hasattr(self.element_list, 'update_element'):
            self.element_list.update_element(element_id, update_data)
    
    def _handle_tree_refresh(self) -> None:
        """Handle tree refresh signal"""
        if hasattr(self.element_list, 'refresh_tree'):
            self.element_list.refresh_tree()
    
    def _handle_selection_sync(self, element_ids: List[str]) -> None:
        """Handle selection sync signal"""
        if hasattr(self.element_list, 'sync_selection'):
            self.element_list.sync_selection(element_ids)
    
    def _handle_filter_update(self, filter_config: Dict[str, Any]) -> None:
        """Handle filter update signal"""
        if hasattr(self.element_list, 'apply_filter'):
            self.element_list.apply_filter(filter_config)