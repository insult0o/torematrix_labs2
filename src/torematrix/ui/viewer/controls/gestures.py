"""
Touch gesture recognition for pan and zoom operations.
Supports single-touch pan, two-finger pinch/zoom, and tap gestures.
"""

from typing import Dict, List, Optional, Tuple
from PyQt6.QtCore import QObject, pyqtSignal, QPointF, QTimer
from PyQt6.QtGui import QTouchEvent
import math
import time


class TouchPoint:
    """Represents a single touch point with tracking data."""
    
    def __init__(self, touch_id: int, position: QPointF):
        self.touch_id = touch_id
        self.current_pos = position
        self.start_pos = position
        self.gesture_start_pos = position
        self.velocity = QPointF(0, 0)
        self.last_update_time = time.time()


class GestureRecognizer(QObject):
    """
    Advanced touch gesture recognition for pan and zoom operations.
    Supports single-touch pan, two-finger pinch/zoom, and momentum.
    """
    
    # Gesture signals
    pan_gesture_started = pyqtSignal(QPointF)  # start_position
    pan_gesture_updated = pyqtSignal(QPointF, QPointF)  # start, current
    pan_gesture_finished = pyqtSignal(QPointF, QPointF)  # start, end
    
    pinch_gesture_started = pyqtSignal(float, QPointF)  # initial_scale, center
    pinch_gesture_updated = pyqtSignal(float, QPointF)  # scale_factor, center
    pinch_gesture_finished = pyqtSignal(float, QPointF)  # final_scale, center
    
    tap_gesture = pyqtSignal(QPointF)  # position
    double_tap_gesture = pyqtSignal(QPointF)  # position
    long_press_gesture = pyqtSignal(QPointF)  # position
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Touch tracking
        self.active_touches: Dict[int, TouchPoint] = {}
        self.gesture_state = 'none'  # 'none', 'pan', 'pinch', 'tap', 'long_press'
        
        # Gesture configuration
        self.pan_threshold = 10  # pixels
        self.pinch_threshold = 20  # pixels
        self.tap_timeout = 500  # ms
        self.double_tap_timeout = 300  # ms
        self.long_press_timeout = 1000  # ms
        
        # Double tap detection
        self.last_tap_time = 0
        self.last_tap_position = QPointF()
        self.double_tap_distance_threshold = 30  # pixels
        
        # Long press detection
        self.long_press_timer = QTimer()
        self.long_press_timer.timeout.connect(self._handle_long_press)
        self.long_press_timer.setSingleShot(True)
        
        # Gesture tracking
        self.gesture_start_time = 0
        self.initial_pinch_distance = 0.0
        self.initial_pinch_center = QPointF()
        
        # Performance tracking
        self.last_update_time = 0
        self.gesture_recognition_times = []
    
    def process_touch_event(self, event: QTouchEvent) -> bool:
        """
        Process touch event and recognize gestures.
        
        Args:
            event: Qt touch event
            
        Returns:
            bool: True if gesture was recognized and handled
        """
        start_time = time.perf_counter()
        current_time = time.time() * 1000  # Convert to ms
        
        try:
            # Update active touches
            self._update_touch_points(event)
            
            # Determine gesture based on number of active touches
            active_count = len(self.active_touches)
            
            result = False
            if active_count == 0:
                result = self._handle_no_touches()
            elif active_count == 1:
                result = self._handle_single_touch(current_time)
            elif active_count == 2:
                result = self._handle_two_finger_touch(current_time)
            else:
                # More than 2 touches - ignore
                result = self._reset_gesture_state()
            
            return result
        
        finally:
            # Record performance metrics
            end_time = time.perf_counter()
            recognition_time = (end_time - start_time) * 1000
            self.gesture_recognition_times.append(recognition_time)
            
            # Keep only recent timing data
            if len(self.gesture_recognition_times) > 100:
                self.gesture_recognition_times.pop(0)
    
    def _update_touch_points(self, event: QTouchEvent):
        """Update active touch points from touch event."""
        current_touches = {}
        
        for touch_point in event.points():
            touch_id = touch_point.id()
            position = touch_point.position()
            
            if touch_id in self.active_touches:
                # Update existing touch
                touch = self.active_touches[touch_id]
                touch.current_pos = position
                touch.last_update_time = time.time()
                current_touches[touch_id] = touch
            else:
                # New touch
                touch = TouchPoint(touch_id, position)
                current_touches[touch_id] = touch
        
        self.active_touches = current_touches
    
    def _handle_single_touch(self, current_time: float) -> bool:
        """Handle single touch for pan or tap gestures."""
        if not self.active_touches:
            return False
        
        touch_point = list(self.active_touches.values())[0]
        
        if self.gesture_state == 'none':
            # Potential start of pan or tap
            self.gesture_state = 'potential_pan'
            self.gesture_start_time = current_time
            touch_point.gesture_start_pos = touch_point.current_pos
            
            # Start long press timer
            self.long_press_timer.start(self.long_press_timeout)
            return True
        
        elif self.gesture_state == 'potential_pan':
            # Check if movement exceeds pan threshold
            distance = self._distance(touch_point.gesture_start_pos, 
                                    touch_point.current_pos)
            
            if distance > self.pan_threshold:
                # Start pan gesture
                self.gesture_state = 'pan'
                self.long_press_timer.stop()
                self.pan_gesture_started.emit(touch_point.gesture_start_pos)
                self.pan_gesture_updated.emit(touch_point.gesture_start_pos,
                                            touch_point.current_pos)
                return True
            
            # Check for tap timeout
            elif current_time - self.gesture_start_time > self.tap_timeout:
                self._reset_gesture_state()
                return False
        
        elif self.gesture_state == 'pan':
            # Continue pan gesture
            self.pan_gesture_updated.emit(touch_point.gesture_start_pos,
                                        touch_point.current_pos)
            return True
        
        elif self.gesture_state == 'long_press':
            # Long press is active, ignore movement
            return True
        
        return False
    
    def _handle_two_finger_touch(self, current_time: float) -> bool:
        """Handle two-finger touch for pinch/zoom gestures."""
        if len(self.active_touches) < 2:
            return False
        
        touches = list(self.active_touches.values())
        touch1, touch2 = touches[0], touches[1]
        
        if self.gesture_state in ('none', 'potential_pan'):
            # Start potential pinch gesture
            self.gesture_state = 'potential_pinch'
            self.gesture_start_time = current_time
            
            # Calculate initial distance and center
            touch1.gesture_start_pos = touch1.current_pos
            touch2.gesture_start_pos = touch2.current_pos
            
            self.initial_pinch_distance = self._distance(touch1.current_pos, 
                                                       touch2.current_pos)
            self.initial_pinch_center = self._midpoint(touch1.current_pos, 
                                                     touch2.current_pos)
            
            # Stop any other gesture timers
            self.long_press_timer.stop()
            return True
        
        elif self.gesture_state == 'potential_pinch':
            # Check if pinch distance change exceeds threshold
            current_distance = self._distance(touch1.current_pos, touch2.current_pos)
            distance_change = abs(current_distance - self.initial_pinch_distance)
            
            if distance_change > self.pinch_threshold:
                # Start pinch gesture
                self.gesture_state = 'pinch'
                
                scale_factor = current_distance / self.initial_pinch_distance
                center = self._midpoint(touch1.current_pos, touch2.current_pos)
                
                self.pinch_gesture_started.emit(1.0, self.initial_pinch_center)
                self.pinch_gesture_updated.emit(scale_factor, center)
                return True
        
        elif self.gesture_state == 'pinch':
            # Continue pinch gesture
            current_distance = self._distance(touch1.current_pos, touch2.current_pos)
            scale_factor = current_distance / self.initial_pinch_distance
            center = self._midpoint(touch1.current_pos, touch2.current_pos)
            
            self.pinch_gesture_updated.emit(scale_factor, center)
            return True
        
        return False
    
    def _handle_no_touches(self) -> bool:
        """Handle end of touch sequence."""
        if self.gesture_state == 'potential_pan':
            # Was a tap - emit tap gesture and check for double tap
            current_time = time.time() * 1000
            
            if hasattr(self, 'gesture_start_position'):
                tap_position = self.gesture_start_position
            else:
                # Fallback to last known position
                if self.active_touches:
                    touch = list(self.active_touches.values())[0]
                    tap_position = touch.start_pos
                else:
                    tap_position = QPointF(0, 0)
            
            # Check for double tap
            time_since_last = current_time - self.last_tap_time
            distance_from_last = self._distance(self.last_tap_position, tap_position)
            
            if (time_since_last < self.double_tap_timeout and 
                distance_from_last < self.double_tap_distance_threshold):
                self.double_tap_gesture.emit(tap_position)
            else:
                self.tap_gesture.emit(tap_position)
                self.last_tap_time = current_time
                self.last_tap_position = tap_position
        
        elif self.gesture_state == 'pan':
            # Finish pan gesture
            if self.active_touches:
                touch = list(self.active_touches.values())[0]
                self.pan_gesture_finished.emit(touch.gesture_start_pos, 
                                             touch.current_pos)
        
        elif self.gesture_state == 'pinch':
            # Finish pinch gesture
            touches = list(self.active_touches.values())
            if len(touches) >= 2:
                touch1, touch2 = touches[0], touches[1]
                current_distance = self._distance(touch1.current_pos, touch2.current_pos)
                final_scale = current_distance / self.initial_pinch_distance
                center = self._midpoint(touch1.current_pos, touch2.current_pos)
                
                self.pinch_gesture_finished.emit(final_scale, center)
        
        return self._reset_gesture_state()
    
    def _handle_long_press(self):
        """Handle long press timeout."""
        if self.gesture_state == 'potential_pan' and self.active_touches:
            self.gesture_state = 'long_press'
            touch = list(self.active_touches.values())[0]
            self.long_press_gesture.emit(touch.current_pos)
    
    def _reset_gesture_state(self) -> bool:
        """Reset gesture state to none."""
        self.gesture_state = 'none'
        self.long_press_timer.stop()
        return True
    
    @staticmethod
    def _distance(p1: QPointF, p2: QPointF) -> float:
        """Calculate distance between two points."""
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        return math.sqrt(dx*dx + dy*dy)
    
    @staticmethod
    def _midpoint(p1: QPointF, p2: QPointF) -> QPointF:
        """Calculate midpoint between two points."""
        return QPointF((p1.x() + p2.x()) / 2, (p1.y() + p2.y()) / 2)
    
    def get_performance_metrics(self) -> Dict[str, float]:
        """Get gesture recognition performance metrics."""
        if not self.gesture_recognition_times:
            return {
                'avg_recognition_time': 0.0,
                'max_recognition_time': 0.0,
                'gesture_count': 0,
                'meets_target': True
            }
        
        avg_time = sum(self.gesture_recognition_times) / len(self.gesture_recognition_times)
        max_time = max(self.gesture_recognition_times)
        meets_target = avg_time < 50.0  # 50ms target for gesture recognition
        
        return {
            'avg_recognition_time': avg_time,
            'max_recognition_time': max_time,
            'gesture_count': len(self.gesture_recognition_times),
            'meets_target': meets_target
        }
    
    def set_gesture_thresholds(self, pan_threshold: float = None, 
                              pinch_threshold: float = None):
        """Set gesture recognition thresholds."""
        if pan_threshold is not None and pan_threshold > 0:
            self.pan_threshold = pan_threshold
        
        if pinch_threshold is not None and pinch_threshold > 0:
            self.pinch_threshold = pinch_threshold
    
    def set_timing_thresholds(self, tap_timeout: int = None, 
                             double_tap_timeout: int = None,
                             long_press_timeout: int = None):
        """Set gesture timing thresholds."""
        if tap_timeout is not None and tap_timeout > 0:
            self.tap_timeout = tap_timeout
        
        if double_tap_timeout is not None and double_tap_timeout > 0:
            self.double_tap_timeout = double_tap_timeout
        
        if long_press_timeout is not None and long_press_timeout > 0:
            self.long_press_timeout = long_press_timeout