"""
Event replay manager for state reconstruction and debugging.
"""

from typing import Dict, Any, List, Optional, Callable
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class ReplayableEvent:
    """An event that can be replayed."""
    event_id: str
    event_type: str
    timestamp: float
    data: Dict[str, Any]
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def datetime(self) -> datetime:
        """Get event timestamp as datetime."""
        return datetime.fromtimestamp(self.timestamp)


@dataclass
class ReplaySession:
    """A replay session configuration."""
    session_id: str
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    event_types: Optional[List[str]] = None
    event_sources: Optional[List[str]] = None
    filters: Optional[List[Callable]] = None
    transform: Optional[Callable] = None
    created_at: float = field(default_factory=time.time)


class EventReplayManager:
    """
    Manager for replaying events to reconstruct state or debug issues.
    
    Features:
    - Event capture and storage
    - Time-based event filtering
    - Custom replay sessions
    - State reconstruction from events
    - Debugging and analysis tools
    """
    
    def __init__(self, max_events: int = 10000):
        """
        Initialize replay manager.
        
        Args:
            max_events: Maximum number of events to keep in memory
        """
        self.max_events = max_events
        self.events: List[ReplayableEvent] = []
        self.sessions: Dict[str, ReplaySession] = {}
        self.capture_enabled = True
        self._stats = {
            'events_captured': 0,
            'events_replayed': 0,
            'replay_sessions': 0,
            'replay_errors': 0
        }
    
    def capture_event(self, event_id: str, event_type: str, data: Dict[str, Any], 
                     source: str = "", metadata: Optional[Dict[str, Any]] = None):
        """
        Capture an event for potential replay.
        
        Args:
            event_id: Unique identifier for the event
            event_type: Type/category of the event
            data: Event data payload
            source: Source of the event
            metadata: Additional metadata
        """
        if not self.capture_enabled:
            return
        
        event = ReplayableEvent(
            event_id=event_id,
            event_type=event_type,
            timestamp=time.time(),
            data=data,
            source=source,
            metadata=metadata or {}
        )
        
        self.events.append(event)
        self._stats['events_captured'] += 1
        
        # Maintain max events limit
        if len(self.events) > self.max_events:
            self.events.pop(0)
        
        logger.debug(f"Captured event: {event_type} ({event_id})")
    
    def create_replay_session(self, session_id: str, 
                             start_time: Optional[float] = None,
                             end_time: Optional[float] = None,
                             event_types: Optional[List[str]] = None,
                             event_sources: Optional[List[str]] = None,
                             filters: Optional[List[Callable]] = None,
                             transform: Optional[Callable] = None) -> ReplaySession:
        """
        Create a new replay session with filtering criteria.
        
        Args:
            session_id: Unique identifier for the session
            start_time: Start timestamp for event filtering
            end_time: End timestamp for event filtering
            event_types: List of event types to include
            event_sources: List of event sources to include
            filters: Custom filter functions
            transform: Transform function for events
            
        Returns:
            Created replay session
        """
        session = ReplaySession(
            session_id=session_id,
            start_time=start_time,
            end_time=end_time,
            event_types=event_types,
            event_sources=event_sources,
            filters=filters,
            transform=transform
        )
        
        self.sessions[session_id] = session
        self._stats['replay_sessions'] += 1
        
        logger.info(f"Created replay session: {session_id}")
        return session
    
    def get_events_for_session(self, session_id: str) -> List[ReplayableEvent]:
        """
        Get filtered events for a replay session.
        
        Args:
            session_id: ID of the replay session
            
        Returns:
            List of filtered events
        """
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session = self.sessions[session_id]
        filtered_events = []
        
        for event in self.events:
            # Time filtering
            if session.start_time and event.timestamp < session.start_time:
                continue
            if session.end_time and event.timestamp > session.end_time:
                continue
            
            # Event type filtering
            if session.event_types and event.event_type not in session.event_types:
                continue
            
            # Source filtering
            if session.event_sources and event.source not in session.event_sources:
                continue
            
            # Custom filters
            if session.filters:
                if not all(f(event) for f in session.filters):
                    continue
            
            # Apply transform if specified
            if session.transform:
                try:
                    transformed_event = session.transform(event)
                    if transformed_event:
                        filtered_events.append(transformed_event)
                except Exception as e:
                    logger.error(f"Transform error for event {event.event_id}: {e}")
            else:
                filtered_events.append(event)
        
        return filtered_events
    
    def replay_to_store(self, session_id: str, store: Any, 
                       action_converter: Callable[[ReplayableEvent], Any]) -> Dict[str, Any]:
        """
        Replay events to a store by converting them to actions.
        
        Args:
            session_id: ID of the replay session
            store: Target store for replay
            action_converter: Function to convert events to actions
            
        Returns:
            Replay statistics and results
        """
        events = self.get_events_for_session(session_id)
        
        replay_stats = {
            'total_events': len(events),
            'successful_replays': 0,
            'failed_replays': 0,
            'start_time': time.time(),
            'errors': []
        }
        
        logger.info(f"Starting replay of {len(events)} events to store")
        
        for event in events:
            try:
                # Convert event to action
                action = action_converter(event)
                
                if action:
                    # Dispatch action to store
                    store.dispatch(action)
                    replay_stats['successful_replays'] += 1
                    self._stats['events_replayed'] += 1
                
            except Exception as e:
                error_msg = f"Replay error for event {event.event_id}: {e}"
                logger.error(error_msg)
                replay_stats['errors'].append(error_msg)
                replay_stats['failed_replays'] += 1
                self._stats['replay_errors'] += 1
        
        replay_stats['duration'] = time.time() - replay_stats['start_time']
        
        logger.info(f"Replay completed: {replay_stats['successful_replays']}/{replay_stats['total_events']} events")
        return replay_stats
    
    def reconstruct_state(self, session_id: str, 
                         initial_state: Dict[str, Any],
                         state_reducer: Callable[[Dict[str, Any], ReplayableEvent], Dict[str, Any]]) -> Dict[str, Any]:
        """
        Reconstruct state by replaying events through a reducer.
        
        Args:
            session_id: ID of the replay session
            initial_state: Starting state
            state_reducer: Function to apply events to state
            
        Returns:
            Reconstructed state
        """
        events = self.get_events_for_session(session_id)
        current_state = dict(initial_state)
        
        logger.info(f"Reconstructing state from {len(events)} events")
        
        for event in events:
            try:
                current_state = state_reducer(current_state, event)
            except Exception as e:
                logger.error(f"State reconstruction error for event {event.event_id}: {e}")
                # Continue with next event
        
        logger.info("State reconstruction completed")
        return current_state
    
    def get_events_by_time_range(self, start_time: float, end_time: float) -> List[ReplayableEvent]:
        """Get events within a specific time range."""
        return [
            event for event in self.events
            if start_time <= event.timestamp <= end_time
        ]
    
    def get_events_by_type(self, event_type: str) -> List[ReplayableEvent]:
        """Get events of a specific type."""
        return [
            event for event in self.events
            if event.event_type == event_type
        ]
    
    def get_events_by_source(self, source: str) -> List[ReplayableEvent]:
        """Get events from a specific source."""
        return [
            event for event in self.events
            if event.source == source
        ]
    
    def analyze_event_patterns(self) -> Dict[str, Any]:
        """Analyze patterns in captured events."""
        if not self.events:
            return {'message': 'No events to analyze'}
        
        # Event type distribution
        type_counts = {}
        source_counts = {}
        hourly_counts = {}
        
        for event in self.events:
            # Count by type
            type_counts[event.event_type] = type_counts.get(event.event_type, 0) + 1
            
            # Count by source
            source_counts[event.source] = source_counts.get(event.source, 0) + 1
            
            # Count by hour
            hour = datetime.fromtimestamp(event.timestamp).hour
            hourly_counts[hour] = hourly_counts.get(hour, 0) + 1
        
        # Calculate statistics
        timestamps = [event.timestamp for event in self.events]
        time_span = max(timestamps) - min(timestamps) if timestamps else 0
        
        return {
            'total_events': len(self.events),
            'event_types': type_counts,
            'event_sources': source_counts,
            'hourly_distribution': hourly_counts,
            'time_span_seconds': time_span,
            'events_per_second': len(self.events) / time_span if time_span > 0 else 0,
            'first_event': datetime.fromtimestamp(min(timestamps)).isoformat() if timestamps else None,
            'last_event': datetime.fromtimestamp(max(timestamps)).isoformat() if timestamps else None
        }
    
    def export_events(self, session_id: Optional[str] = None, 
                     format: str = 'json') -> str:
        """
        Export events in various formats.
        
        Args:
            session_id: Session to export (all events if None)
            format: Export format ('json', 'csv')
            
        Returns:
            Serialized events data
        """
        if session_id:
            events = self.get_events_for_session(session_id)
        else:
            events = self.events
        
        if format == 'json':
            import json
            return json.dumps([
                {
                    'event_id': event.event_id,
                    'event_type': event.event_type,
                    'timestamp': event.timestamp,
                    'datetime': event.datetime.isoformat(),
                    'data': event.data,
                    'source': event.source,
                    'metadata': event.metadata
                }
                for event in events
            ], indent=2)
        
        elif format == 'csv':
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow(['event_id', 'event_type', 'timestamp', 'datetime', 'source', 'data', 'metadata'])
            
            # Write events
            for event in events:
                writer.writerow([
                    event.event_id,
                    event.event_type,
                    event.timestamp,
                    event.datetime.isoformat(),
                    event.source,
                    str(event.data),
                    str(event.metadata)
                ])
            
            return output.getvalue()
        
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def clear_events(self):
        """Clear all captured events."""
        self.events.clear()
        logger.info("Cleared all captured events")
    
    def clear_sessions(self):
        """Clear all replay sessions."""
        self.sessions.clear()
        logger.info("Cleared all replay sessions")
    
    def enable_capture(self):
        """Enable event capture."""
        self.capture_enabled = True
        logger.info("Event capture enabled")
    
    def disable_capture(self):
        """Disable event capture."""
        self.capture_enabled = False
        logger.info("Event capture disabled")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get replay manager statistics."""
        return dict(self._stats)