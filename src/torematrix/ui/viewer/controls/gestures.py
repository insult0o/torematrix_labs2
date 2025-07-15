"""
Gesture Recognition System for Document Viewer

Provides touch gesture detection and handling for zoom and pan operations.
Supports pinch-to-zoom, swipe gestures, and multi-touch interactions.
"""

from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from dataclasses import dataclass
from PyQt6.QtCore import QObject, pyqtSignal, QPointF, QTimer
from PyQt6.QtGui import QTouchEvent
import time
import math


class GestureType(Enum):
    """Types of supported gestures"""
    PINCH = "pinch"
    SWIPE = "swipe"
    TAP = "tap"
    DOUBLE_TAP = "double_tap"
    LONG_PRESS = "long_press"


class GestureState(Enum):
    """Gesture recognition states"""
    IDLE = "idle"
    DETECTING = "detecting"
    RECOGNIZED = "recognized"
    CANCELLED = "cancelled"


@dataclass
class TouchPoint:
    """Touch point data"""
    id: int
    position: QPointF
    start_position: QPointF
    timestamp: float
    pressure: float = 1.0


@dataclass 
class GestureEvent:
    """Gesture event data"""
    gesture_type: GestureType
    center_point: QPointF
    scale_factor: float = 1.0
    rotation_angle: float = 0.0
    velocity: QPointF = None
    duration: float = 0.0
    
    def __post_init__(self):
        if self.velocity is None:
            self.velocity = QPointF(0, 0)


class GestureRecognizer(QObject):
    """Touch gesture recognition and processing"""
    
    # Gesture signals
    gesture_started = pyqtSignal(GestureEvent)
    gesture_updated = pyqtSignal(GestureEvent)
    gesture_finished = pyqtSignal(GestureEvent)
    gesture_cancelled = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Configuration
        self._min_pinch_distance = 20.0  # Minimum distance for pinch
        self._min_swipe_distance = 50.0  # Minimum distance for swipe
        self._tap_tolerance = 10.0       # Movement tolerance for tap
        self._double_tap_time = 500      # ms for double tap
        self._long_press_time = 800      # ms for long press
        
        # State tracking
        self._active_touches: Dict[int, TouchPoint] = {}
        self._gesture_state = GestureState.IDLE
        self._current_gesture: Optional[GestureType] = None
        self._last_tap_time = 0.0
        self._last_tap_position = QPointF()
        
        # Gesture data
        self._initial_distance = 0.0
        self._initial_center = QPointF()
        self._last_scale = 1.0
        self._accumulated_scale = 1.0
        
        # Timers
        self._long_press_timer = QTimer()
        self._long_press_timer.setSingleShot(True)
        self._long_press_timer.timeout.connect(self._on_long_press_timeout)
    
    def process_touch_event(self, event: QTouchEvent) -> bool:
        """Process touch event and recognize gestures"""
        try:
            if event.type() == QTouchEvent.Type.TouchBegin:
                return self._handle_touch_begin(event)
            elif event.type() == QTouchEvent.Type.TouchUpdate:
                return self._handle_touch_update(event)
            elif event.type() == QTouchEvent.Type.TouchEnd:
                return self._handle_touch_end(event)
            elif event.type() == QTouchEvent.Type.TouchCancel:
                return self._handle_touch_cancel(event)
        except Exception as e:
            print(f"Gesture recognition error: {e}")
            self._reset_gesture_state()
        
        return False
    
    def _handle_touch_begin(self, event: QTouchEvent) -> bool:
        """Handle touch begin event"""
        for touch_point in event.points():
            touch = TouchPoint(
                id=touch_point.id(),
                position=touch_point.position(),
                start_position=touch_point.position(),
                timestamp=time.time(),
                pressure=touch_point.pressure()
            )
            self._active_touches[touch.id] = touch
        
        if len(self._active_touches) == 1:
            # Single touch - potential tap or swipe
            self._start_single_touch_detection()
        elif len(self._active_touches) == 2:
            # Two touches - potential pinch
            self._start_pinch_detection()
        else:
            # More than 2 touches - cancel current gesture
            self._cancel_gesture()
        
        return True
    
    def _handle_touch_update(self, event: QTouchEvent) -> bool:
        """Handle touch update event"""
        # Update touch positions
        for touch_point in event.points():
            if touch_point.id() in self._active_touches:
                touch = self._active_touches[touch_point.id()]
                touch.position = touch_point.position()
                touch.pressure = touch_point.pressure()
        
        # Process based on current gesture
        if self._current_gesture == GestureType.PINCH:
            self._update_pinch_gesture()
        elif len(self._active_touches) == 1:
            self._update_single_touch_gesture()
        
        return True
    
    def _handle_touch_end(self, event: QTouchEvent) -> bool:
        """Handle touch end event"""
        # Remove ended touches
        for touch_point in event.points():
            if touch_point.id() in self._active_touches:
                del self._active_touches[touch_point.id()]
        
        if len(self._active_touches) == 0:
            # All touches ended
            self._finish_gesture()
        elif len(self._active_touches) == 1 and self._current_gesture == GestureType.PINCH:
            # One touch remaining after pinch
            self._finish_gesture()
        
        return True
    
    def _handle_touch_cancel(self, event: QTouchEvent) -> bool:
        """Handle touch cancel event"""
        self._cancel_gesture()
        return True
    
    def _start_single_touch_detection(self):
        """Start single touch gesture detection"""
        if len(self._active_touches) != 1:
            return
        
        touch = list(self._active_touches.values())[0]
        
        # Start long press timer
        self._long_press_timer.start(self._long_press_time)
        
        # Check for double tap
        current_time = time.time() * 1000
        if (current_time - self._last_tap_time < self._double_tap_time and
            self._distance_between_points(touch.position, self._last_tap_position) < self._tap_tolerance):
            
            self._recognize_double_tap(touch.position)
        
        self._gesture_state = GestureState.DETECTING
    
    def _start_pinch_detection(self):
        """Start pinch gesture detection"""
        if len(self._active_touches) != 2:
            return
        
        touches = list(self._active_touches.values())
        center = self._calculate_center_point(touches)
        distance = self._distance_between_points(touches[0].position, touches[1].position)
        
        if distance > self._min_pinch_distance:
            self._current_gesture = GestureType.PINCH
            self._gesture_state = GestureState.RECOGNIZED
            self._initial_distance = distance
            self._initial_center = center
            self._last_scale = 1.0
            self._accumulated_scale = 1.0
            
            # Emit gesture started
            gesture_event = GestureEvent(
                gesture_type=GestureType.PINCH,
                center_point=center,
                scale_factor=1.0
            )
            self.gesture_started.emit(gesture_event)
        
        # Cancel long press timer
        self._long_press_timer.stop()
    
    def _update_pinch_gesture(self):
        """Update pinch gesture"""
        if len(self._active_touches) != 2:
            return
        
        touches = list(self._active_touches.values())
        center = self._calculate_center_point(touches)
        current_distance = self._distance_between_points(touches[0].position, touches[1].position)
        
        if self._initial_distance > 0:
            scale_factor = current_distance / self._initial_distance
            
            # Emit gesture update
            gesture_event = GestureEvent(
                gesture_type=GestureType.PINCH,
                center_point=center,
                scale_factor=scale_factor
            )
            self.gesture_updated.emit(gesture_event)
            
            self._last_scale = scale_factor
    
    def _update_single_touch_gesture(self):
        """Update single touch gesture (swipe detection)"""
        if len(self._active_touches) != 1:
            return
        
        touch = list(self._active_touches.values())[0]
        distance = self._distance_between_points(touch.position, touch.start_position)
        
        # Check if moved enough to be a swipe
        if distance > self._min_swipe_distance:
            self._long_press_timer.stop()
            
            if self._current_gesture != GestureType.SWIPE:
                self._current_gesture = GestureType.SWIPE
                self._gesture_state = GestureState.RECOGNIZED
                
                # Calculate velocity
                duration = time.time() - touch.timestamp
                velocity = QPointF(
                    (touch.position.x() - touch.start_position.x()) / max(duration, 0.1),
                    (touch.position.y() - touch.start_position.y()) / max(duration, 0.1)
                )
                
                # Emit swipe start
                gesture_event = GestureEvent(
                    gesture_type=GestureType.SWIPE,
                    center_point=touch.position,
                    velocity=velocity,
                    duration=duration
                )
                self.gesture_started.emit(gesture_event)
    
    def _finish_gesture(self):
        """Finish current gesture"""
        if self._current_gesture == GestureType.PINCH:
            touches = list(self._active_touches.values())
            if len(touches) >= 2:
                center = self._calculate_center_point(touches[:2])
            else:
                center = self._initial_center
            
            gesture_event = GestureEvent(
                gesture_type=GestureType.PINCH,
                center_point=center,
                scale_factor=self._last_scale
            )
            self.gesture_finished.emit(gesture_event)
        
        elif self._current_gesture == GestureType.SWIPE:
            if len(self._active_touches) >= 1:
                touch = list(self._active_touches.values())[0]
                duration = time.time() - touch.timestamp
                velocity = QPointF(
                    (touch.position.x() - touch.start_position.x()) / max(duration, 0.1),
                    (touch.position.y() - touch.start_position.y()) / max(duration, 0.1)
                )
                
                gesture_event = GestureEvent(
                    gesture_type=GestureType.SWIPE,
                    center_point=touch.position,
                    velocity=velocity,
                    duration=duration
                )
                self.gesture_finished.emit(gesture_event)
        
        elif self._gesture_state == GestureState.DETECTING and len(self._active_touches) == 0:
            # Single tap
            self._recognize_tap()
        
        self._reset_gesture_state()
    
    def _cancel_gesture(self):
        """Cancel current gesture"""
        if self._gesture_state != GestureState.IDLE:
            self.gesture_cancelled.emit()
        self._reset_gesture_state()
    
    def _reset_gesture_state(self):
        """Reset gesture recognition state"""
        self._active_touches.clear()
        self._gesture_state = GestureState.IDLE
        self._current_gesture = None
        self._long_press_timer.stop()
        self._initial_distance = 0.0
        self._last_scale = 1.0
    
    def _recognize_tap(self):
        """Recognize single tap gesture"""
        if len(self._active_touches) == 0:
            return
        
        touch = list(self._active_touches.values())[0]
        gesture_event = GestureEvent(
            gesture_type=GestureType.TAP,
            center_point=touch.position
        )
        
        self.gesture_started.emit(gesture_event)
        self.gesture_finished.emit(gesture_event)
        
        # Store for double tap detection
        self._last_tap_time = time.time() * 1000
        self._last_tap_position = touch.position
    
    def _recognize_double_tap(self, position: QPointF):
        """Recognize double tap gesture"""
        gesture_event = GestureEvent(
            gesture_type=GestureType.DOUBLE_TAP,
            center_point=position
        )
        
        self.gesture_started.emit(gesture_event)
        self.gesture_finished.emit(gesture_event)
        
        self._last_tap_time = 0  # Reset to prevent triple tap
    
    def _on_long_press_timeout(self):
        """Handle long press timeout"""
        if len(self._active_touches) == 1:
            touch = list(self._active_touches.values())[0]
            
            # Check if touch hasn't moved too much
            distance = self._distance_between_points(touch.position, touch.start_position)
            if distance <= self._tap_tolerance:
                gesture_event = GestureEvent(
                    gesture_type=GestureType.LONG_PRESS,
                    center_point=touch.position
                )
                
                self.gesture_started.emit(gesture_event)
                self.gesture_finished.emit(gesture_event)
    
    def _calculate_center_point(self, touches: List[TouchPoint]) -> QPointF:
        """Calculate center point of touches"""
        if not touches:
            return QPointF()
        
        total_x = sum(touch.position.x() for touch in touches)
        total_y = sum(touch.position.y() for touch in touches)
        
        return QPointF(total_x / len(touches), total_y / len(touches))
    
    def _distance_between_points(self, p1: QPointF, p2: QPointF) -> float:
        """Calculate distance between two points"""
        dx = p1.x() - p2.x()
        dy = p1.y() - p2.y()
        return math.sqrt(dx * dx + dy * dy)


class GestureHandler(QObject):
    """Handles gesture events and translates to viewer actions"""
    
    # Action signals
    zoom_requested = pyqtSignal(float, QPointF)  # scale, center
    pan_requested = pyqtSignal(QPointF)          # delta
    fit_to_view_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Configuration
        self._pinch_sensitivity = 1.0
        self._swipe_sensitivity = 1.0
        self._min_zoom_scale = 0.1
        self._max_zoom_scale = 10.0
        
        # State
        self._last_pinch_scale = 1.0
    
    def handle_gesture(self, event: GestureEvent):
        """Handle gesture event and emit appropriate actions"""
        try:
            if event.gesture_type == GestureType.PINCH:
                self._handle_pinch_gesture(event)
            elif event.gesture_type == GestureType.SWIPE:
                self._handle_swipe_gesture(event)
            elif event.gesture_type == GestureType.DOUBLE_TAP:
                self._handle_double_tap_gesture(event)
            elif event.gesture_type == GestureType.TAP:
                self._handle_tap_gesture(event)
            elif event.gesture_type == GestureType.LONG_PRESS:
                self._handle_long_press_gesture(event)
        except Exception as e:
            print(f"Gesture handling error: {e}")
    
    def _handle_pinch_gesture(self, event: GestureEvent):
        """Handle pinch gesture for zoom"""
        scale_delta = event.scale_factor / self._last_pinch_scale if self._last_pinch_scale != 0 else 1.0
        scale_delta = max(self._min_zoom_scale, min(self._max_zoom_scale, scale_delta))
        
        self.zoom_requested.emit(scale_delta * self._pinch_sensitivity, event.center_point)
        self._last_pinch_scale = event.scale_factor
    
    def _handle_swipe_gesture(self, event: GestureEvent):
        """Handle swipe gesture for pan"""
        # Scale velocity for pan delta
        pan_delta = QPointF(
            event.velocity.x() * self._swipe_sensitivity * 0.1,
            event.velocity.y() * self._swipe_sensitivity * 0.1
        )
        
        self.pan_requested.emit(pan_delta)
    
    def _handle_double_tap_gesture(self, event: GestureEvent):
        """Handle double tap gesture for fit to view"""
        self.fit_to_view_requested.emit()
    
    def _handle_tap_gesture(self, event: GestureEvent):
        """Handle single tap gesture"""
        # Could be used for selection or other actions
        pass
    
    def _handle_long_press_gesture(self, event: GestureEvent):
        """Handle long press gesture"""
        # Could be used for context menus or other actions
        pass
    
    def set_sensitivity(self, pinch_sensitivity: float, swipe_sensitivity: float):
        """Set gesture sensitivity values"""
        self._pinch_sensitivity = max(0.1, min(10.0, pinch_sensitivity))
        self._swipe_sensitivity = max(0.1, min(10.0, swipe_sensitivity))
    
    def set_zoom_limits(self, min_scale: float, max_scale: float):
        """Set zoom scale limits"""
        self._min_zoom_scale = max(0.01, min_scale)
        self._max_zoom_scale = max(min_scale, max_scale)