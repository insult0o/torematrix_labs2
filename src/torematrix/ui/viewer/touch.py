"""
Touch Support and Gesture Recognition for Document Viewer Overlay.
This module provides comprehensive touch input handling including
multi-touch gestures, haptic feedback, and touch-friendly interactions.
"""
from __future__ import annotations

import math
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Callable, Tuple

from PyQt6.QtCore import QObject, QTimer, QPointF, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QTouchEvent
from PyQt6.QtWidgets import QWidget, QGestureEvent, QGesture

from .coordinates import Point, Rectangle


class GestureType(Enum):
    """Types of touch gestures."""
    TAP = "tap"                     # Single finger tap
    DOUBLE_TAP = "double_tap"       # Double tap
    LONG_PRESS = "long_press"       # Long press hold
    SWIPE = "swipe"                 # Swipe gesture
    PINCH = "pinch"                 # Pinch to zoom
    ROTATE = "rotate"               # Rotation gesture
    PAN = "pan"                     # Two-finger pan
    FLICK = "flick"                 # Quick flick gesture
    MULTI_TAP = "multi_tap"         # Multiple finger tap


class SwipeDirection(Enum):
    """Swipe gesture directions."""
    LEFT = "left"
    RIGHT = "right"
    UP = "up"
    DOWN = "down"
    UP_LEFT = "up_left"
    UP_RIGHT = "up_right"
    DOWN_LEFT = "down_left"
    DOWN_RIGHT = "down_right"


class TouchState(Enum):
    """Touch point states."""
    BEGAN = "began"
    MOVED = "moved"
    ENDED = "ended"
    CANCELLED = "cancelled"


@dataclass
class TouchPoint:
    """Enhanced touch point with additional tracking data."""
    id: int
    position: Point
    pressure: float = 1.0
    timestamp: float = field(default_factory=time.time)
    state: TouchState = TouchState.BEGAN
    start_position: Optional[Point] = None
    last_position: Optional[Point] = None
    velocity: Point = field(default_factory=lambda: Point(0, 0))
    
    def __post_init__(self):
        if self.start_position is None:
            self.start_position = self.position
        if self.last_position is None:
            self.last_position = self.position


@dataclass
class TouchGesture:
    """Detected touch gesture information."""
    gesture_type: GestureType
    touch_points: List[TouchPoint]
    start_time: float
    end_time: Optional[float] = None
    center_point: Optional[Point] = None
    properties: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration(self) -> float:
        """Get gesture duration in seconds."""
        end = self.end_time or time.time()
        return end - self.start_time
    
    @property
    def is_active(self) -> bool:
        """Check if gesture is still active."""
        return self.end_time is None


@dataclass
class SwipeGesture(TouchGesture):
    """Swipe gesture with direction and velocity."""
    direction: SwipeDirection = SwipeDirection.RIGHT
    distance: float = 0.0
    velocity: float = 0.0
    
    def __post_init__(self):
        self.gesture_type = GestureType.SWIPE


@dataclass
class PinchGesture(TouchGesture):
    """Pinch gesture with scale factor."""
    initial_distance: float = 0.0
    current_distance: float = 0.0
    scale_factor: float = 1.0
    
    def __post_init__(self):
        self.gesture_type = GestureType.PINCH


@dataclass
class RotateGesture(TouchGesture):
    """Rotation gesture with angle."""
    initial_angle: float = 0.0
    current_angle: float = 0.0
    rotation_delta: float = 0.0
    
    def __post_init__(self):
        self.gesture_type = GestureType.ROTATE


class GestureRecognizer(ABC):
    """Abstract base class for gesture recognizers."""
    
    @abstractmethod
    def can_recognize(self, touch_points: List[TouchPoint]) -> bool:
        """Check if this recognizer can handle the given touch points."""
        pass
    
    @abstractmethod
    def recognize(self, touch_points: List[TouchPoint]) -> Optional[TouchGesture]:
        """Attempt to recognize a gesture from touch points."""
        pass
    
    @abstractmethod
    def update(self, touch_points: List[TouchPoint], 
              existing_gesture: TouchGesture) -> Optional[TouchGesture]:
        """Update an existing gesture with new touch data."""
        pass


class TapGestureRecognizer(GestureRecognizer):
    """Recognizer for tap gestures."""
    
    def __init__(self):
        self.tap_timeout = 0.3  # seconds
        self.tap_threshold = 10  # pixels
        self.double_tap_timeout = 0.5  # seconds
        self.last_tap_time = 0.0
        self.last_tap_position: Optional[Point] = None
    
    def can_recognize(self, touch_points: List[TouchPoint]) -> bool:
        """Check if this is a potential tap gesture."""
        return len(touch_points) == 1
    
    def recognize(self, touch_points: List[TouchPoint]) -> Optional[TouchGesture]:
        """Recognize tap gesture."""
        if not self.can_recognize(touch_points):
            return None
        
        touch = touch_points[0]
        
        # Check if touch has ended
        if touch.state != TouchState.ENDED:
            return None
        
        # Check duration
        if touch.timestamp - touch.start_position.timestamp > self.tap_timeout:
            return None
        
        # Check movement
        if touch.start_position:
            distance = self._calculate_distance(touch.position, touch.start_position)
            if distance > self.tap_threshold:
                return None
        
        # Check for double tap
        current_time = time.time()
        is_double_tap = False
        
        if (self.last_tap_time and 
            current_time - self.last_tap_time < self.double_tap_timeout and
            self.last_tap_position):
            
            distance_from_last = self._calculate_distance(touch.position, self.last_tap_position)
            if distance_from_last < self.tap_threshold:
                is_double_tap = True
        
        # Update last tap info
        self.last_tap_time = current_time
        self.last_tap_position = touch.position
        
        # Create gesture
        gesture_type = GestureType.DOUBLE_TAP if is_double_tap else GestureType.TAP
        
        return TouchGesture(
            gesture_type=gesture_type,
            touch_points=[touch],
            start_time=touch.timestamp,
            end_time=current_time,
            center_point=touch.position
        )
    
    def update(self, touch_points: List[TouchPoint], 
              existing_gesture: TouchGesture) -> Optional[TouchGesture]:
        """Tap gestures don't update."""
        return existing_gesture
    
    def _calculate_distance(self, p1: Point, p2: Point) -> float:
        """Calculate distance between two points."""
        return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)


class LongPressGestureRecognizer(GestureRecognizer):
    """Recognizer for long press gestures."""
    
    def __init__(self):
        self.long_press_duration = 0.8  # seconds
        self.movement_threshold = 10  # pixels
    
    def can_recognize(self, touch_points: List[TouchPoint]) -> bool:
        """Check if this is a potential long press."""
        return len(touch_points) == 1
    
    def recognize(self, touch_points: List[TouchPoint]) -> Optional[TouchGesture]:
        """Recognize long press gesture."""
        if not self.can_recognize(touch_points):
            return None
        
        touch = touch_points[0]
        current_time = time.time()
        
        # Check duration
        duration = current_time - touch.timestamp
        if duration < self.long_press_duration:
            return None
        
        # Check movement
        if touch.start_position:
            distance = self._calculate_distance(touch.position, touch.start_position)
            if distance > self.movement_threshold:
                return None
        
        return TouchGesture(
            gesture_type=GestureType.LONG_PRESS,
            touch_points=[touch],
            start_time=touch.timestamp,
            center_point=touch.position
        )
    
    def update(self, touch_points: List[TouchPoint], 
              existing_gesture: TouchGesture) -> Optional[TouchGesture]:
        """Update long press gesture."""
        if existing_gesture.gesture_type != GestureType.LONG_PRESS:
            return existing_gesture
        
        # Update with current touch point
        if touch_points:
            existing_gesture.touch_points = [touch_points[0]]
            existing_gesture.center_point = touch_points[0].position
        
        return existing_gesture
    
    def _calculate_distance(self, p1: Point, p2: Point) -> float:
        """Calculate distance between two points."""
        return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)


class SwipeGestureRecognizer(GestureRecognizer):
    """Recognizer for swipe gestures."""
    
    def __init__(self):
        self.min_distance = 50  # pixels
        self.max_duration = 1.0  # seconds
        self.direction_threshold = 30  # degrees
    
    def can_recognize(self, touch_points: List[TouchPoint]) -> bool:
        """Check if this is a potential swipe."""
        return len(touch_points) == 1
    
    def recognize(self, touch_points: List[TouchPoint]) -> Optional[TouchGesture]:
        """Recognize swipe gesture."""
        if not self.can_recognize(touch_points):
            return None
        
        touch = touch_points[0]
        
        # Check if touch has ended
        if touch.state != TouchState.ENDED:
            return None
        
        # Check duration
        duration = touch.timestamp - touch.start_position.timestamp
        if duration > self.max_duration:
            return None
        
        # Check distance
        if not touch.start_position:
            return None
        
        distance = self._calculate_distance(touch.position, touch.start_position)
        if distance < self.min_distance:
            return None
        
        # Calculate direction
        direction = self._calculate_direction(touch.start_position, touch.position)
        velocity = distance / duration if duration > 0 else 0
        
        return SwipeGesture(
            gesture_type=GestureType.SWIPE,
            touch_points=[touch],
            start_time=touch.timestamp,
            end_time=time.time(),
            center_point=touch.position,
            direction=direction,
            distance=distance,
            velocity=velocity
        )
    
    def update(self, touch_points: List[TouchPoint], 
              existing_gesture: TouchGesture) -> Optional[TouchGesture]:
        """Swipe gestures don't update after recognition."""
        return existing_gesture
    
    def _calculate_distance(self, p1: Point, p2: Point) -> float:
        """Calculate distance between two points."""
        return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)
    
    def _calculate_direction(self, start: Point, end: Point) -> SwipeDirection:
        """Calculate swipe direction."""
        dx = end.x - start.x
        dy = end.y - start.y
        
        angle = math.atan2(dy, dx) * 180 / math.pi
        
        # Normalize angle to 0-360
        if angle < 0:
            angle += 360
        
        # Determine direction
        if 337.5 <= angle or angle < 22.5:
            return SwipeDirection.RIGHT
        elif 22.5 <= angle < 67.5:
            return SwipeDirection.DOWN_RIGHT
        elif 67.5 <= angle < 112.5:
            return SwipeDirection.DOWN
        elif 112.5 <= angle < 157.5:
            return SwipeDirection.DOWN_LEFT
        elif 157.5 <= angle < 202.5:
            return SwipeDirection.LEFT
        elif 202.5 <= angle < 247.5:
            return SwipeDirection.UP_LEFT
        elif 247.5 <= angle < 292.5:
            return SwipeDirection.UP
        else:  # 292.5 <= angle < 337.5
            return SwipeDirection.UP_RIGHT


class PinchGestureRecognizer(GestureRecognizer):
    """Recognizer for pinch/zoom gestures."""
    
    def __init__(self):
        self.min_distance_change = 20  # pixels
    
    def can_recognize(self, touch_points: List[TouchPoint]) -> bool:
        """Check if this is a potential pinch gesture."""
        return len(touch_points) == 2
    
    def recognize(self, touch_points: List[TouchPoint]) -> Optional[TouchGesture]:
        """Recognize pinch gesture."""
        if not self.can_recognize(touch_points):
            return None
        
        touch1, touch2 = touch_points
        
        # Calculate initial distance
        initial_distance = self._calculate_distance(
            touch1.start_position, touch2.start_position
        )
        
        current_distance = self._calculate_distance(
            touch1.position, touch2.position
        )
        
        # Check if there's significant distance change
        distance_change = abs(current_distance - initial_distance)
        if distance_change < self.min_distance_change:
            return None
        
        # Calculate center point
        center = Point(
            (touch1.position.x + touch2.position.x) / 2,
            (touch1.position.y + touch2.position.y) / 2
        )
        
        scale_factor = current_distance / initial_distance if initial_distance > 0 else 1.0
        
        return PinchGesture(
            gesture_type=GestureType.PINCH,
            touch_points=touch_points,
            start_time=min(touch1.timestamp, touch2.timestamp),
            center_point=center,
            initial_distance=initial_distance,
            current_distance=current_distance,
            scale_factor=scale_factor
        )
    
    def update(self, touch_points: List[TouchPoint], 
              existing_gesture: TouchGesture) -> Optional[TouchGesture]:
        """Update pinch gesture."""
        if (not isinstance(existing_gesture, PinchGesture) or 
            not self.can_recognize(touch_points)):
            return existing_gesture
        
        touch1, touch2 = touch_points
        
        # Update current distance
        current_distance = self._calculate_distance(
            touch1.position, touch2.position
        )
        
        # Update center point
        center = Point(
            (touch1.position.x + touch2.position.x) / 2,
            (touch1.position.y + touch2.position.y) / 2
        )
        
        # Update scale factor
        scale_factor = (current_distance / existing_gesture.initial_distance 
                       if existing_gesture.initial_distance > 0 else 1.0)
        
        # Update gesture
        existing_gesture.current_distance = current_distance
        existing_gesture.scale_factor = scale_factor
        existing_gesture.center_point = center
        existing_gesture.touch_points = touch_points
        
        return existing_gesture
    
    def _calculate_distance(self, p1: Point, p2: Point) -> float:
        """Calculate distance between two points."""
        return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)


class TouchSignals(QObject):
    """Signals for touch events."""
    gesture_started = pyqtSignal(object)  # TouchGesture
    gesture_updated = pyqtSignal(object)  # TouchGesture
    gesture_ended = pyqtSignal(object)    # TouchGesture
    touch_point_added = pyqtSignal(object)  # TouchPoint
    touch_point_moved = pyqtSignal(object)  # TouchPoint
    touch_point_removed = pyqtSignal(object)  # TouchPoint


class TouchManager(QObject):
    """
    Main touch input manager for the overlay system.
    Handles touch events, gesture recognition, and haptic feedback.
    """
    
    def __init__(self, interaction_manager: Optional[Any] = None):
        super().__init__()
        
        # Dependencies
        self.interaction_manager = interaction_manager
        
        # Touch state
        self.active_touches: Dict[int, TouchPoint] = {}
        self.active_gestures: List[TouchGesture] = []
        
        # Gesture recognizers
        self.recognizers: List[GestureRecognizer] = [
            TapGestureRecognizer(),
            LongPressGestureRecognizer(),
            SwipeGestureRecognizer(),
            PinchGestureRecognizer(),
        ]
        
        # Configuration
        self.gesture_enabled = True
        self.haptic_feedback_enabled = True
        self.touch_sensitivity = 1.0
        
        # Signals
        self.signals = TouchSignals()
        
        # Performance tracking
        self.touch_metrics: Dict[str, List[float]] = {}
        
        # Gesture update timer
        self.gesture_timer = QTimer()
        self.gesture_timer.setInterval(16)  # ~60fps
        self.gesture_timer.timeout.connect(self._update_gestures)
    
    def handle_touch_event(self, event: QTouchEvent) -> bool:
        """Handle Qt touch events."""
        start_time = time.time()
        
        # Convert Qt touch points to our format
        touch_points = []
        for qt_touch in event.touchPoints():
            touch_point = self._qt_to_touch_point(qt_touch)
            touch_points.append(touch_point)
            
            # Update active touches
            if touch_point.state == TouchState.BEGAN:
                self.active_touches[touch_point.id] = touch_point
                self.signals.touch_point_added.emit(touch_point)
            elif touch_point.state == TouchState.MOVED:
                if touch_point.id in self.active_touches:
                    # Update velocity
                    old_touch = self.active_touches[touch_point.id]
                    if old_touch.last_position:
                        dt = touch_point.timestamp - old_touch.timestamp
                        if dt > 0:
                            touch_point.velocity = Point(
                                (touch_point.position.x - old_touch.position.x) / dt,
                                (touch_point.position.y - old_touch.position.y) / dt
                            )
                    
                    self.active_touches[touch_point.id] = touch_point
                    self.signals.touch_point_moved.emit(touch_point)
            elif touch_point.state in (TouchState.ENDED, TouchState.CANCELLED):
                if touch_point.id in self.active_touches:
                    del self.active_touches[touch_point.id]
                    self.signals.touch_point_removed.emit(touch_point)
        
        # Recognize gestures
        if self.gesture_enabled:
            self._recognize_gestures(touch_points)
        
        # Start gesture update timer if we have active gestures
        if self.active_gestures and not self.gesture_timer.isActive():
            self.gesture_timer.start()
        elif not self.active_gestures and self.gesture_timer.isActive():
            self.gesture_timer.stop()
        
        # Track performance
        duration = (time.time() - start_time) * 1000
        self._track_touch_metric("touch_event", duration)
        
        return True
    
    def _qt_to_touch_point(self, qt_touch) -> TouchPoint:
        """Convert Qt touch point to our format."""
        # Determine state
        if qt_touch.state() == qt_touch.State.Pressed:
            state = TouchState.BEGAN
        elif qt_touch.state() == qt_touch.State.Moved:
            state = TouchState.MOVED
        elif qt_touch.state() == qt_touch.State.Released:
            state = TouchState.ENDED
        else:
            state = TouchState.CANCELLED
        
        # Create touch point
        position = Point(qt_touch.position().x(), qt_touch.position().y())
        start_pos = Point(qt_touch.startPos().x(), qt_touch.startPos().y())
        last_pos = Point(qt_touch.lastPos().x(), qt_touch.lastPos().y())
        
        return TouchPoint(
            id=qt_touch.id(),
            position=position,
            pressure=qt_touch.pressure(),
            timestamp=time.time(),
            state=state,
            start_position=start_pos,
            last_position=last_pos
        )
    
    def _recognize_gestures(self, touch_points: List[TouchPoint]) -> None:
        """Recognize gestures from touch points."""
        # Update existing gestures
        updated_gestures = []
        for gesture in self.active_gestures:
            updated_gesture = None
            for recognizer in self.recognizers:
                if recognizer.can_recognize(touch_points):
                    updated_gesture = recognizer.update(touch_points, gesture)
                    if updated_gesture:
                        break
            
            if updated_gesture:
                updated_gestures.append(updated_gesture)
                self.signals.gesture_updated.emit(updated_gesture)
            else:
                # Gesture ended
                gesture.end_time = time.time()
                self.signals.gesture_ended.emit(gesture)
        
        self.active_gestures = updated_gestures
        
        # Try to recognize new gestures
        for recognizer in self.recognizers:
            if recognizer.can_recognize(touch_points):
                new_gesture = recognizer.recognize(touch_points)
                if new_gesture and not self._is_gesture_duplicate(new_gesture):
                    self.active_gestures.append(new_gesture)
                    self.signals.gesture_started.emit(new_gesture)
                    
                    # Trigger haptic feedback
                    if self.haptic_feedback_enabled:
                        self._trigger_haptic_feedback(new_gesture.gesture_type)
    
    def _update_gestures(self) -> None:
        """Update active gestures (called by timer)."""
        if not self.active_gestures:
            return
        
        # Get current touch points
        current_touches = list(self.active_touches.values())
        
        # Update gestures
        self._recognize_gestures(current_touches)
    
    def _is_gesture_duplicate(self, new_gesture: TouchGesture) -> bool:
        """Check if a gesture is a duplicate of an existing one."""
        for existing in self.active_gestures:
            if (existing.gesture_type == new_gesture.gesture_type and
                abs(existing.start_time - new_gesture.start_time) < 0.1):
                return True
        return False
    
    def _trigger_haptic_feedback(self, gesture_type: GestureType) -> None:
        """Trigger haptic feedback for gesture."""
        # Platform-specific haptic feedback implementation
        # This would need to be implemented per platform
        pass
    
    def set_gesture_enabled(self, enabled: bool) -> None:
        """Enable or disable gesture recognition."""
        self.gesture_enabled = enabled
    
    def set_haptic_feedback_enabled(self, enabled: bool) -> None:
        """Enable or disable haptic feedback."""
        self.haptic_feedback_enabled = enabled
    
    def set_touch_sensitivity(self, sensitivity: float) -> None:
        """Set touch sensitivity (0.1 to 2.0)."""
        self.touch_sensitivity = max(0.1, min(2.0, sensitivity))
        
        # Update recognizer thresholds
        for recognizer in self.recognizers:
            if hasattr(recognizer, 'tap_threshold'):
                recognizer.tap_threshold = int(10 / sensitivity)
            if hasattr(recognizer, 'movement_threshold'):
                recognizer.movement_threshold = int(10 / sensitivity)
            if hasattr(recognizer, 'min_distance'):
                recognizer.min_distance = int(50 / sensitivity)
    
    def register_gesture_recognizer(self, recognizer: GestureRecognizer) -> None:
        """Register a custom gesture recognizer."""
        self.recognizers.append(recognizer)
    
    def get_active_gestures(self) -> List[TouchGesture]:
        """Get currently active gestures."""
        return self.active_gestures.copy()
    
    def get_active_touches(self) -> List[TouchPoint]:
        """Get currently active touch points."""
        return list(self.active_touches.values())
    
    def _track_touch_metric(self, metric_name: str, duration: float) -> None:
        """Track touch performance metrics."""
        if metric_name not in self.touch_metrics:
            self.touch_metrics[metric_name] = []
        
        self.touch_metrics[metric_name].append(duration)
        
        # Keep only last 100 measurements
        if len(self.touch_metrics[metric_name]) > 100:
            self.touch_metrics[metric_name] = self.touch_metrics[metric_name][-100:]
    
    def get_touch_metrics(self) -> Dict[str, Dict[str, float]]:
        """Get touch performance metrics."""
        metrics = {}
        
        for metric_name, durations in self.touch_metrics.items():
            if durations:
                metrics[metric_name] = {
                    "average": sum(durations) / len(durations),
                    "min": min(durations),
                    "max": max(durations),
                    "count": len(durations)
                }
        
        return metrics


# Utility functions for touch integration
def is_touch_device() -> bool:
    """Check if the current device supports touch input."""
    from PyQt6.QtGui import QTouchDevice
    return len(QTouchDevice.devices()) > 0


def configure_widget_for_touch(widget: QWidget) -> None:
    """Configure a widget to accept touch input."""
    widget.setAttribute(widget.Attribute.WA_AcceptTouchEvents)
    widget.setAcceptDrops(True)


class TouchEnabledMixin:
    """Mixin to add touch support to widgets."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.touch_manager: Optional[TouchManager] = None
        self._setup_touch_support()
    
    def _setup_touch_support(self) -> None:
        """Setup touch support for this widget."""
        if hasattr(self, 'setAttribute'):
            configure_widget_for_touch(self)
    
    def set_touch_manager(self, touch_manager: TouchManager) -> None:
        """Set the touch manager for this widget."""
        self.touch_manager = touch_manager
    
    def event(self, event) -> bool:
        """Override event handling to capture touch events."""
        if event.type() == event.Type.TouchBegin or \
           event.type() == event.Type.TouchUpdate or \
           event.type() == event.Type.TouchEnd:
            
            if self.touch_manager:
                return self.touch_manager.handle_touch_event(event)
        
        return super().event(event) if hasattr(super(), 'event') else False