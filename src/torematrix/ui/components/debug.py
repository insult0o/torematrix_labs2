"""
Debug Utilities for Reactive Components.

This module provides debugging tools for render tracking, performance analysis,
and visual inspection of reactive component behavior.
"""

import time
import json
import weakref
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import defaultdict, deque
from datetime import datetime
import threading

from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QTextEdit
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush

import logging

logger = logging.getLogger(__name__)


@dataclass
class RenderEvent:
    """Represents a single render event."""
    
    widget_id: int
    widget_type: str
    widget_name: str
    timestamp: float
    duration: float
    trigger: str  # What triggered the render
    props_changed: List[str] = field(default_factory=list)
    state_changed: List[str] = field(default_factory=list)
    patches_applied: int = 0
    error: Optional[str] = None
    stack_trace: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "widget_id": self.widget_id,
            "widget_type": self.widget_type,
            "widget_name": self.widget_name,
            "timestamp": self.timestamp,
            "duration_ms": round(self.duration * 1000, 2),
            "trigger": self.trigger,
            "props_changed": self.props_changed,
            "state_changed": self.state_changed,
            "patches_applied": self.patches_applied,
            "error": self.error,
            "stack_trace": self.stack_trace
        }


@dataclass
class ComponentTree:
    """Represents component hierarchy for debugging."""
    
    widget_id: int
    widget_type: str
    widget_name: str
    depth: int
    children: List['ComponentTree'] = field(default_factory=list)
    render_count: int = 0
    total_render_time: float = 0.0
    last_render_time: float = 0.0
    
    def add_child(self, child: 'ComponentTree') -> None:
        """Add child component."""
        self.children.append(child)
    
    def find_node(self, widget_id: int) -> Optional['ComponentTree']:
        """Find node by widget ID."""
        if self.widget_id == widget_id:
            return self
        
        for child in self.children:
            found = child.find_node(widget_id)
            if found:
                return found
        
        return None


class RenderTracker(QObject):
    """Tracks and records render events for debugging."""
    
    # Signals
    render_recorded = pyqtSignal(dict)  # Render event dict
    
    def __init__(self, max_events: int = 1000):
        """Initialize render tracker."""
        super().__init__()
        
        self.max_events = max_events
        self._events: deque[RenderEvent] = deque(maxlen=max_events)
        self._component_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "render_count": 0,
            "total_time": 0.0,
            "average_time": 0.0,
            "min_time": float('inf'),
            "max_time": 0.0
        })
        self._active_renders: Dict[int, RenderEvent] = {}
        self._component_tree: Optional[ComponentTree] = None
        self._lock = threading.RLock()
        
        # Recording state
        self._is_recording = True
        self._filters = {
            "min_duration": 0.0,
            "widget_types": set(),
            "exclude_types": set()
        }
    
    def start_render(
        self,
        widget: QWidget,
        trigger: str = "unknown",
        props_changed: Optional[List[str]] = None,
        state_changed: Optional[List[str]] = None
    ) -> None:
        """Start tracking a render."""
        if not self._is_recording:
            return
        
        widget_id = id(widget)
        widget_type = widget.__class__.__name__
        widget_name = widget.objectName() or f"{widget_type}_{widget_id}"
        
        # Apply filters
        if self._should_filter(widget_type):
            return
        
        with self._lock:
            event = RenderEvent(
                widget_id=widget_id,
                widget_type=widget_type,
                widget_name=widget_name,
                timestamp=time.time(),
                duration=0.0,
                trigger=trigger,
                props_changed=props_changed or [],
                state_changed=state_changed or []
            )
            
            self._active_renders[widget_id] = event
    
    def end_render(
        self,
        widget: QWidget,
        patches_applied: int = 0,
        error: Optional[str] = None
    ) -> None:
        """End tracking a render."""
        if not self._is_recording:
            return
        
        widget_id = id(widget)
        
        with self._lock:
            if widget_id not in self._active_renders:
                return
            
            event = self._active_renders.pop(widget_id)
            event.duration = time.time() - event.timestamp
            event.patches_applied = patches_applied
            event.error = error
            
            # Apply duration filter
            if event.duration < self._filters["min_duration"]:
                return
            
            # Record event
            self._events.append(event)
            self._update_stats(event)
            
            # Update component tree
            self._update_component_tree(widget, event)
            
            # Emit signal
            self.render_recorded.emit(event.to_dict())
    
    def _should_filter(self, widget_type: str) -> bool:
        """Check if widget type should be filtered."""
        # Exclude types
        if widget_type in self._filters["exclude_types"]:
            return True
        
        # Include only specific types if set
        if self._filters["widget_types"]:
            return widget_type not in self._filters["widget_types"]
        
        return False
    
    def _update_stats(self, event: RenderEvent) -> None:
        """Update component statistics."""
        stats = self._component_stats[event.widget_type]
        
        stats["render_count"] += 1
        stats["total_time"] += event.duration
        stats["average_time"] = stats["total_time"] / stats["render_count"]
        stats["min_time"] = min(stats["min_time"], event.duration)
        stats["max_time"] = max(stats["max_time"], event.duration)
    
    def _update_component_tree(self, widget: QWidget, event: RenderEvent) -> None:
        """Update component tree structure."""
        if not self._component_tree:
            # Create root
            self._component_tree = ComponentTree(
                widget_id=id(widget),
                widget_type=event.widget_type,
                widget_name=event.widget_name,
                depth=0
            )
        
        # Find or create node
        node = self._component_tree.find_node(id(widget))
        if node:
            node.render_count += 1
            node.total_render_time += event.duration
            node.last_render_time = event.timestamp
    
    def get_recent_events(self, count: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get recent render events."""
        with self._lock:
            events = list(self._events)
            if count:
                events = events[-count:]
            return [event.to_dict() for event in events]
    
    def get_component_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get render statistics by component type."""
        with self._lock:
            return {
                comp_type: {
                    **stats,
                    "average_time_ms": round(stats["average_time"] * 1000, 2),
                    "total_time_ms": round(stats["total_time"] * 1000, 2),
                    "min_time_ms": round(stats["min_time"] * 1000, 2),
                    "max_time_ms": round(stats["max_time"] * 1000, 2)
                }
                for comp_type, stats in self._component_stats.items()
            }
    
    def get_hot_components(self, top_n: int = 10) -> List[Tuple[str, int]]:
        """Get components with most renders."""
        with self._lock:
            components = [
                (comp_type, stats["render_count"])
                for comp_type, stats in self._component_stats.items()
            ]
            components.sort(key=lambda x: x[1], reverse=True)
            return components[:top_n]
    
    def set_filter(self, filter_type: str, value: Any) -> None:
        """Set a filter for render tracking."""
        with self._lock:
            if filter_type in self._filters:
                self._filters[filter_type] = value
    
    def start_recording(self) -> None:
        """Start recording render events."""
        self._is_recording = True
    
    def stop_recording(self) -> None:
        """Stop recording render events."""
        self._is_recording = False
    
    def clear(self) -> None:
        """Clear all recorded events."""
        with self._lock:
            self._events.clear()
            self._component_stats.clear()
            self._active_renders.clear()
            self._component_tree = None


class RenderDebugWidget(QWidget):
    """Visual widget for debugging render performance."""
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize debug widget."""
        super().__init__(parent)
        
        self.tracker = get_render_tracker()
        self._setup_ui()
        
        # Update timer
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._update_display)
        self._update_timer.start(100)  # Update every 100ms
    
    def _setup_ui(self) -> None:
        """Set up the UI."""
        layout = QVBoxLayout(self)
        
        # Component tree
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels([
            "Component", "Renders", "Avg Time (ms)", "Total Time (ms)"
        ])
        layout.addWidget(self.tree_widget)
        
        # Event log
        self.event_log = QTextEdit()
        self.event_log.setReadOnly(True)
        self.event_log.setMaximumHeight(200)
        layout.addWidget(self.event_log)
    
    def _update_display(self) -> None:
        """Update the display with latest data."""
        # Update component tree
        self._update_component_tree()
        
        # Update event log
        self._update_event_log()
    
    def _update_component_tree(self) -> None:
        """Update component tree display."""
        self.tree_widget.clear()
        
        stats = self.tracker.get_component_stats()
        
        for comp_type, comp_stats in stats.items():
            item = QTreeWidgetItem([
                comp_type,
                str(comp_stats["render_count"]),
                f"{comp_stats['average_time_ms']:.2f}",
                f"{comp_stats['total_time_ms']:.2f}"
            ])
            
            # Color code by performance
            if comp_stats["average_time_ms"] > 16:  # Slower than 60 FPS
                item.setBackground(2, QBrush(QColor(255, 200, 200)))
            elif comp_stats["average_time_ms"] > 8:  # Slower than 120 FPS
                item.setBackground(2, QBrush(QColor(255, 255, 200)))
            
            self.tree_widget.addTopLevelItem(item)
    
    def _update_event_log(self) -> None:
        """Update event log display."""
        recent_events = self.tracker.get_recent_events(10)
        
        if recent_events:
            # Only update if new events
            log_text = []
            for event in reversed(recent_events):
                timestamp = datetime.fromtimestamp(event["timestamp"]).strftime("%H:%M:%S.%f")[:-3]
                duration = event["duration_ms"]
                
                # Color code
                if duration > 16:
                    color = "red"
                elif duration > 8:
                    color = "orange"
                else:
                    color = "green"
                
                log_text.append(
                    f'<span style="color: {color};">[{timestamp}] '
                    f'{event["widget_type"]} - {duration:.2f}ms - '
                    f'{event["trigger"]}</span>'
                )
            
            self.event_log.setHtml("<br>".join(log_text))


class RenderHighlighter:
    """Highlights widgets being rendered for visual debugging."""
    
    def __init__(self):
        """Initialize highlighter."""
        self._highlights: Dict[int, Tuple[QWidget, QColor, float]] = {}
        self._lock = threading.Lock()
        
        # Update timer
        self._timer = QTimer()
        self._timer.timeout.connect(self._update_highlights)
        self._timer.start(50)  # 20 FPS update
    
    def highlight_render(
        self,
        widget: QWidget,
        duration: float = 0.5,
        color: Optional[QColor] = None
    ) -> None:
        """Highlight a widget render."""
        if not color:
            # Choose color based on render time
            if hasattr(widget, "_last_render_time"):
                render_time = widget._last_render_time
                if render_time > 0.016:  # >16ms
                    color = QColor(255, 0, 0, 100)  # Red
                elif render_time > 0.008:  # >8ms
                    color = QColor(255, 165, 0, 100)  # Orange
                else:
                    color = QColor(0, 255, 0, 100)  # Green
            else:
                color = QColor(0, 0, 255, 100)  # Blue default
        
        with self._lock:
            self._highlights[id(widget)] = (
                widget,
                color,
                time.time() + duration
            )
    
    def _update_highlights(self) -> None:
        """Update highlight overlays."""
        current_time = time.time()
        
        with self._lock:
            # Remove expired highlights
            expired = [
                widget_id for widget_id, (_, _, end_time) in self._highlights.items()
                if end_time < current_time
            ]
            
            for widget_id in expired:
                del self._highlights[widget_id]
            
            # Update remaining highlights
            for widget, color, _ in self._highlights.values():
                if widget and not widget.isHidden():
                    self._draw_highlight(widget, color)
    
    def _draw_highlight(self, widget: QWidget, color: QColor) -> None:
        """Draw highlight overlay on widget."""
        # This would need custom painting implementation
        # For now, just change style temporarily
        original_style = widget.styleSheet()
        widget.setStyleSheet(f"border: 2px solid {color.name()};")
        
        # Restore after short delay
        QTimer.singleShot(50, lambda: widget.setStyleSheet(original_style))


# Global instances
_render_tracker: Optional[RenderTracker] = None
_render_highlighter: Optional[RenderHighlighter] = None


def get_render_tracker() -> RenderTracker:
    """Get the global render tracker."""
    global _render_tracker
    if _render_tracker is None:
        _render_tracker = RenderTracker()
    return _render_tracker


def get_render_highlighter() -> RenderHighlighter:
    """Get the global render highlighter."""
    global _render_highlighter
    if _render_highlighter is None:
        _render_highlighter = RenderHighlighter()
    return _render_highlighter


# Debug decorators
def track_render(trigger: str = "manual"):
    """Decorator to track widget renders."""
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            tracker = get_render_tracker()
            
            # Track render
            tracker.start_render(self, trigger)
            
            try:
                result = func(self, *args, **kwargs)
                tracker.end_render(self)
                return result
            except Exception as e:
                tracker.end_render(self, error=str(e))
                raise
        
        return wrapper
    return decorator


def highlight_render(duration: float = 0.5, color: Optional[QColor] = None):
    """Decorator to highlight widget renders."""
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            highlighter = get_render_highlighter()
            
            # Highlight widget
            highlighter.highlight_render(self, duration, color)
            
            return func(self, *args, **kwargs)
        
        return wrapper
    return decorator