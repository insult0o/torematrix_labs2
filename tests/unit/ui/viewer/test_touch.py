"""
Unit tests for the touch support and gesture recognition system.
Tests touch event handling, gesture recognition, and multi-touch capabilities.
"""
import pytest
import math
import time
from unittest.mock import Mock, MagicMock, patch

from PyQt6.QtGui import QTouchEvent
from PyQt6.QtCore import QPointF

from src.torematrix.ui.viewer.touch import (
    TouchManager, TouchPoint, TouchGesture, SwipeGesture, PinchGesture,
    GestureType, SwipeDirection, TouchState, TapGestureRecognizer,
    LongPressGestureRecognizer, SwipeGestureRecognizer, PinchGestureRecognizer,
    TouchEnabledMixin, is_touch_device, configure_widget_for_touch
)
from src.torematrix.ui.viewer.coordinates import Point


class TestTouchPoint:
    """Test touch point data structure."""
    
    def test_touch_point_creation(self):
        """Test basic touch point creation."""
        position = Point(10, 20)
        touch = TouchPoint(
            id=1,
            position=position,
            pressure=0.8,
            state=TouchState.BEGAN
        )
        
        assert touch.id == 1
        assert touch.position == position
        assert touch.pressure == 0.8
        assert touch.state == TouchState.BEGAN
        assert touch.start_position == position  # Auto-set in __post_init__
        assert touch.last_position == position
        assert isinstance(touch.timestamp, float)
    
    def test_touch_point_with_custom_positions(self):
        """Test touch point with custom start and last positions."""
        current_pos = Point(30, 40)
        start_pos = Point(10, 20)
        last_pos = Point(25, 35)
        
        touch = TouchPoint(
            id=2,
            position=current_pos,
            start_position=start_pos,
            last_position=last_pos,
            state=TouchState.MOVED
        )
        
        assert touch.position == current_pos
        assert touch.start_position == start_pos
        assert touch.last_position == last_pos
        assert touch.state == TouchState.MOVED


class TestTouchGesture:
    """Test touch gesture data structures."""
    
    def test_gesture_creation(self):
        """Test basic gesture creation."""
        touch_points = [
            TouchPoint(1, Point(10, 10)),
            TouchPoint(2, Point(20, 20))
        ]
        
        gesture = TouchGesture(
            gesture_type=GestureType.PINCH,
            touch_points=touch_points,
            start_time=time.time()
        )
        
        assert gesture.gesture_type == GestureType.PINCH
        assert len(gesture.touch_points) == 2
        assert gesture.start_time > 0
        assert gesture.end_time is None
        assert gesture.is_active
    
    def test_gesture_duration(self):
        """Test gesture duration calculation."""
        start_time = time.time()
        gesture = TouchGesture(
            gesture_type=GestureType.TAP,
            touch_points=[],
            start_time=start_time
        )
        
        # Active gesture duration
        duration1 = gesture.duration
        assert duration1 >= 0
        
        # Completed gesture duration
        gesture.end_time = start_time + 1.5
        duration2 = gesture.duration
        assert duration2 == 1.5
    
    def test_swipe_gesture(self):
        """Test swipe gesture creation."""
        swipe = SwipeGesture(
            gesture_type=GestureType.SWIPE,
            touch_points=[],
            start_time=time.time(),
            direction=SwipeDirection.RIGHT,
            distance=100.0,
            velocity=50.0
        )
        
        assert swipe.gesture_type == GestureType.SWIPE
        assert swipe.direction == SwipeDirection.RIGHT
        assert swipe.distance == 100.0
        assert swipe.velocity == 50.0
    
    def test_pinch_gesture(self):
        """Test pinch gesture creation."""
        pinch = PinchGesture(
            gesture_type=GestureType.PINCH,
            touch_points=[],
            start_time=time.time(),
            initial_distance=100.0,
            current_distance=150.0,
            scale_factor=1.5
        )
        
        assert pinch.gesture_type == GestureType.PINCH
        assert pinch.initial_distance == 100.0
        assert pinch.current_distance == 150.0
        assert pinch.scale_factor == 1.5


class TestTapGestureRecognizer:
    """Test tap gesture recognition."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.recognizer = TapGestureRecognizer()
    
    def test_can_recognize_single_touch(self):
        """Test recognizer can handle single touch."""
        touch = TouchPoint(1, Point(10, 10))
        
        assert self.recognizer.can_recognize([touch])
        assert not self.recognizer.can_recognize([touch, touch])  # Multiple touches
    
    def test_recognize_tap(self):
        """Test tap recognition."""
        start_time = time.time()
        touch = TouchPoint(
            id=1,
            position=Point(15, 15),
            start_position=Point(10, 10),
            timestamp=start_time + 0.1,  # Short duration
            state=TouchState.ENDED
        )
        
        gesture = self.recognizer.recognize([touch])
        
        assert gesture is not None
        assert gesture.gesture_type == GestureType.TAP
        assert len(gesture.touch_points) == 1
        assert gesture.center_point.x == 15
        assert gesture.center_point.y == 15
    
    def test_reject_long_tap(self):
        """Test rejection of long duration tap."""
        start_time = time.time()
        touch = TouchPoint(
            id=1,
            position=Point(10, 10),
            start_position=Point(10, 10),
            timestamp=start_time + 1.0,  # Too long
            state=TouchState.ENDED
        )
        
        gesture = self.recognizer.recognize([touch])
        
        assert gesture is None
    
    def test_reject_moved_tap(self):
        """Test rejection of tap with too much movement."""
        touch = TouchPoint(
            id=1,
            position=Point(50, 50),  # Moved 40+ pixels
            start_position=Point(10, 10),
            timestamp=time.time() + 0.1,
            state=TouchState.ENDED
        )
        
        gesture = self.recognizer.recognize([touch])
        
        assert gesture is None
    
    def test_double_tap_recognition(self):
        """Test double tap recognition."""
        # First tap
        touch1 = TouchPoint(
            id=1,
            position=Point(10, 10),
            start_position=Point(10, 10),
            timestamp=time.time() + 0.1,
            state=TouchState.ENDED
        )
        
        gesture1 = self.recognizer.recognize([touch1])
        assert gesture1.gesture_type == GestureType.TAP
        
        # Second tap close in time and position
        touch2 = TouchPoint(
            id=2,
            position=Point(12, 12),
            start_position=Point(12, 12),
            timestamp=time.time() + 0.3,
            state=TouchState.ENDED
        )
        
        # Mock time for consistent testing
        with patch('time.time', return_value=self.recognizer.last_tap_time + 0.2):
            gesture2 = self.recognizer.recognize([touch2])
            assert gesture2.gesture_type == GestureType.DOUBLE_TAP


class TestLongPressGestureRecognizer:
    """Test long press gesture recognition."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.recognizer = LongPressGestureRecognizer()
    
    def test_can_recognize_single_touch(self):
        """Test recognizer can handle single touch."""
        touch = TouchPoint(1, Point(10, 10))
        
        assert self.recognizer.can_recognize([touch])
        assert not self.recognizer.can_recognize([touch, touch])
    
    def test_recognize_long_press(self):
        """Test long press recognition."""
        start_time = time.time()
        touch = TouchPoint(
            id=1,
            position=Point(10, 10),
            start_position=Point(10, 10),
            timestamp=start_time
        )
        
        # Mock time to simulate long press duration
        with patch('time.time', return_value=start_time + 1.0):
            gesture = self.recognizer.recognize([touch])
            
            assert gesture is not None
            assert gesture.gesture_type == GestureType.LONG_PRESS
            assert gesture.center_point.x == 10
            assert gesture.center_point.y == 10
    
    def test_reject_short_press(self):
        """Test rejection of short press."""
        start_time = time.time()
        touch = TouchPoint(
            id=1,
            position=Point(10, 10),
            timestamp=start_time
        )
        
        # Too short duration
        with patch('time.time', return_value=start_time + 0.5):
            gesture = self.recognizer.recognize([touch])
            assert gesture is None
    
    def test_reject_moved_press(self):
        """Test rejection of press with movement."""
        start_time = time.time()
        touch = TouchPoint(
            id=1,
            position=Point(30, 30),  # Moved too far
            start_position=Point(10, 10),
            timestamp=start_time
        )
        
        with patch('time.time', return_value=start_time + 1.0):
            gesture = self.recognizer.recognize([touch])
            assert gesture is None


class TestSwipeGestureRecognizer:
    """Test swipe gesture recognition."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.recognizer = SwipeGestureRecognizer()
    
    def test_can_recognize_single_touch(self):
        """Test recognizer can handle single touch."""
        touch = TouchPoint(1, Point(10, 10))
        
        assert self.recognizer.can_recognize([touch])
        assert not self.recognizer.can_recognize([touch, touch])
    
    def test_recognize_right_swipe(self):
        """Test right swipe recognition."""
        start_time = time.time()
        touch = TouchPoint(
            id=1,
            position=Point(110, 10),  # Moved 100px right
            start_position=Point(10, 10),
            timestamp=start_time + 0.5,
            state=TouchState.ENDED
        )
        
        # Set start timestamp manually for testing
        touch.start_position.timestamp = start_time
        
        gesture = self.recognizer.recognize([touch])
        
        assert gesture is not None
        assert isinstance(gesture, SwipeGesture)
        assert gesture.direction == SwipeDirection.RIGHT
        assert gesture.distance == 100.0
        assert gesture.velocity == 200.0  # 100px / 0.5s
    
    def test_recognize_up_swipe(self):
        """Test upward swipe recognition."""
        touch = TouchPoint(
            id=1,
            position=Point(10, -40),  # Moved 50px up
            start_position=Point(10, 10),
            state=TouchState.ENDED
        )
        
        gesture = self.recognizer.recognize([touch])
        
        assert gesture is not None
        assert gesture.direction == SwipeDirection.UP
        assert gesture.distance == 50.0
    
    def test_calculate_diagonal_directions(self):
        """Test diagonal swipe direction calculation."""
        # Down-right swipe
        direction = self.recognizer._calculate_direction(
            Point(0, 0), Point(50, 50)
        )
        assert direction == SwipeDirection.DOWN_RIGHT
        
        # Up-left swipe
        direction = self.recognizer._calculate_direction(
            Point(50, 50), Point(0, 0)
        )
        assert direction == SwipeDirection.UP_LEFT
    
    def test_reject_short_swipe(self):
        """Test rejection of short swipe."""
        touch = TouchPoint(
            id=1,
            position=Point(30, 10),  # Only 20px movement
            start_position=Point(10, 10),
            state=TouchState.ENDED
        )
        
        gesture = self.recognizer.recognize([touch])
        assert gesture is None
    
    def test_reject_slow_swipe(self):
        """Test rejection of slow swipe."""
        start_time = time.time()
        touch = TouchPoint(
            id=1,
            position=Point(110, 10),
            start_position=Point(10, 10),
            timestamp=start_time + 2.0,  # Too slow
            state=TouchState.ENDED
        )
        
        gesture = self.recognizer.recognize([touch])
        assert gesture is None


class TestPinchGestureRecognizer:
    """Test pinch gesture recognition."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.recognizer = PinchGestureRecognizer()
    
    def test_can_recognize_two_touches(self):
        """Test recognizer requires two touches."""
        touch1 = TouchPoint(1, Point(10, 10))
        touch2 = TouchPoint(2, Point(20, 20))
        
        assert not self.recognizer.can_recognize([touch1])
        assert self.recognizer.can_recognize([touch1, touch2])
        assert not self.recognizer.can_recognize([touch1, touch2, touch1])
    
    def test_recognize_pinch_zoom_in(self):
        """Test pinch zoom in recognition."""
        # Two touches starting close, ending far apart
        touch1 = TouchPoint(
            id=1,
            position=Point(0, 10),  # Moved left from (10,10)
            start_position=Point(10, 10)
        )
        touch2 = TouchPoint(
            id=2,
            position=Point(30, 10),  # Moved right from (20,10)
            start_position=Point(20, 10)
        )
        
        gesture = self.recognizer.recognize([touch1, touch2])
        
        assert gesture is not None
        assert isinstance(gesture, PinchGesture)
        assert gesture.initial_distance == 10.0  # Distance between (10,10) and (20,10)
        assert gesture.current_distance == 30.0  # Distance between (0,10) and (30,10)
        assert gesture.scale_factor == 3.0  # 30/10
        assert gesture.center_point.x == 15.0  # Center between touches
        assert gesture.center_point.y == 10.0
    
    def test_recognize_pinch_zoom_out(self):
        """Test pinch zoom out recognition."""
        touch1 = TouchPoint(
            id=1,
            position=Point(15, 10),  # Moved right toward center
            start_position=Point(0, 10)
        )
        touch2 = TouchPoint(
            id=2,
            position=Point(25, 10),  # Moved left toward center
            start_position=Point(40, 10)
        )
        
        gesture = self.recognizer.recognize([touch1, touch2])
        
        assert gesture is not None
        assert gesture.initial_distance == 40.0
        assert gesture.current_distance == 10.0
        assert gesture.scale_factor == 0.25  # 10/40
    
    def test_update_pinch_gesture(self):
        """Test updating existing pinch gesture."""
        # Initial gesture
        touch1 = TouchPoint(1, Point(10, 10), start_position=Point(10, 10))
        touch2 = TouchPoint(2, Point(20, 10), start_position=Point(20, 10))
        
        initial_gesture = self.recognizer.recognize([touch1, touch2])
        assert initial_gesture.scale_factor == 1.0  # Same distance
        
        # Updated touches
        touch1_updated = TouchPoint(1, Point(5, 10), start_position=Point(10, 10))
        touch2_updated = TouchPoint(2, Point(25, 10), start_position=Point(20, 10))
        
        updated_gesture = self.recognizer.update([touch1_updated, touch2_updated], initial_gesture)
        
        assert updated_gesture is not None
        assert updated_gesture.current_distance == 20.0
        assert updated_gesture.scale_factor == 2.0  # 20/10
        assert updated_gesture.center_point.x == 15.0
    
    def test_reject_small_distance_change(self):
        """Test rejection of small distance changes."""
        touch1 = TouchPoint(1, Point(10, 10), start_position=Point(10, 10))
        touch2 = TouchPoint(2, Point(25, 10), start_position=Point(20, 10))  # Only 5px change
        
        gesture = self.recognizer.recognize([touch1, touch2])
        assert gesture is None  # Below minimum distance change threshold


class TestTouchManager:
    """Test main touch manager functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.mock_interaction_manager = Mock()
        self.manager = TouchManager(self.mock_interaction_manager)
    
    def test_initialization(self):
        """Test manager initialization."""
        assert self.manager.interaction_manager == self.mock_interaction_manager
        assert len(self.manager.active_touches) == 0
        assert len(self.manager.active_gestures) == 0
        assert len(self.manager.recognizers) == 4  # 4 default recognizers
        assert self.manager.gesture_enabled
        assert self.manager.haptic_feedback_enabled
        assert self.manager.touch_sensitivity == 1.0
    
    def test_qt_touch_conversion(self):
        """Test Qt touch point conversion."""
        # Create mock Qt touch point
        qt_touch = Mock()
        qt_touch.id.return_value = 1
        qt_touch.position.return_value = QPointF(10, 20)
        qt_touch.startPos.return_value = QPointF(5, 15)
        qt_touch.lastPos.return_value = QPointF(8, 18)
        qt_touch.pressure.return_value = 0.8
        qt_touch.state.return_value = Mock()
        qt_touch.state.return_value.Pressed = Mock()
        qt_touch.State = Mock()
        qt_touch.State.Pressed = qt_touch.state.return_value.Pressed
        
        # Mock the state comparison
        qt_touch.state.return_value = qt_touch.State.Pressed
        
        touch_point = self.manager._qt_to_touch_point(qt_touch)
        
        assert touch_point.id == 1
        assert touch_point.position.x == 10
        assert touch_point.position.y == 20
        assert touch_point.start_position.x == 5
        assert touch_point.start_position.y == 15
        assert touch_point.pressure == 0.8
    
    def test_gesture_recognition_workflow(self):
        """Test gesture recognition workflow."""
        # Create mock touch points
        touch1 = TouchPoint(1, Point(10, 10), state=TouchState.BEGAN)
        touch2 = TouchPoint(2, Point(20, 10), state=TouchState.BEGAN)
        
        # Test gesture recognition
        self.manager._recognize_gestures([touch1, touch2])
        
        # Should attempt recognition with all recognizers
        # Results depend on recognizer implementation
    
    def test_set_gesture_enabled(self):
        """Test enabling/disabling gesture recognition."""
        assert self.manager.gesture_enabled
        
        self.manager.set_gesture_enabled(False)
        assert not self.manager.gesture_enabled
        
        self.manager.set_gesture_enabled(True)
        assert self.manager.gesture_enabled
    
    def test_set_haptic_feedback_enabled(self):
        """Test enabling/disabling haptic feedback."""
        assert self.manager.haptic_feedback_enabled
        
        self.manager.set_haptic_feedback_enabled(False)
        assert not self.manager.haptic_feedback_enabled
    
    def test_set_touch_sensitivity(self):
        """Test setting touch sensitivity."""
        self.manager.set_touch_sensitivity(0.5)
        assert self.manager.touch_sensitivity == 0.5
        
        # Test bounds
        self.manager.set_touch_sensitivity(0.05)  # Below minimum
        assert self.manager.touch_sensitivity == 0.1
        
        self.manager.set_touch_sensitivity(3.0)  # Above maximum
        assert self.manager.touch_sensitivity == 2.0
    
    def test_register_custom_recognizer(self):
        """Test registering custom gesture recognizer."""
        custom_recognizer = Mock()
        initial_count = len(self.manager.recognizers)
        
        self.manager.register_gesture_recognizer(custom_recognizer)
        
        assert len(self.manager.recognizers) == initial_count + 1
        assert custom_recognizer in self.manager.recognizers
    
    def test_get_active_gestures(self):
        """Test getting active gestures."""
        mock_gesture = Mock()
        self.manager.active_gestures = [mock_gesture]
        
        gestures = self.manager.get_active_gestures()
        
        assert len(gestures) == 1
        assert gestures[0] == mock_gesture
        assert gestures is not self.manager.active_gestures  # Should be copy
    
    def test_get_active_touches(self):
        """Test getting active touches."""
        touch = TouchPoint(1, Point(10, 10))
        self.manager.active_touches = {1: touch}
        
        touches = self.manager.get_active_touches()
        
        assert len(touches) == 1
        assert touches[0] == touch
    
    def test_touch_metrics_tracking(self):
        """Test touch performance metrics tracking."""
        self.manager._track_touch_metric("test_touch", 15.5)
        self.manager._track_touch_metric("test_touch", 20.0)
        
        metrics = self.manager.get_touch_metrics()
        
        assert "test_touch" in metrics
        assert metrics["test_touch"]["count"] == 2
        assert metrics["test_touch"]["average"] == 17.75
        assert metrics["test_touch"]["min"] == 15.5
        assert metrics["test_touch"]["max"] == 20.0


class TestTouchEnabledMixin:
    """Test touch enabled mixin functionality."""
    
    def test_mixin_initialization(self):
        """Test mixin initialization."""
        
        class TestWidget(TouchEnabledMixin):
            def __init__(self):
                super().__init__()
                # Mock widget attributes
                self.Attribute = Mock()
                self.Attribute.WA_AcceptTouchEvents = Mock()
            
            def setAttribute(self, attr):
                pass
            
            def setAcceptDrops(self, accept):
                pass
        
        widget = TestWidget()
        
        assert widget.touch_manager is None
    
    def test_set_touch_manager(self):
        """Test setting touch manager."""
        
        class TestWidget(TouchEnabledMixin):
            def __init__(self):
                super().__init__()
            
            def setAttribute(self, attr):
                pass
            
            def setAcceptDrops(self, accept):
                pass
        
        widget = TestWidget()
        mock_manager = Mock()
        
        widget.set_touch_manager(mock_manager)
        
        assert widget.touch_manager == mock_manager


class TestUtilityFunctions:
    """Test utility functions."""
    
    @patch('src.torematrix.ui.viewer.touch.QTouchDevice')
    def test_is_touch_device(self, mock_touch_device):
        """Test touch device detection."""
        # Mock device list
        mock_touch_device.devices.return_value = [Mock(), Mock()]
        
        assert is_touch_device()
        
        # No devices
        mock_touch_device.devices.return_value = []
        assert not is_touch_device()
    
    def test_configure_widget_for_touch(self):
        """Test widget touch configuration."""
        mock_widget = Mock()
        mock_widget.Attribute = Mock()
        mock_widget.Attribute.WA_AcceptTouchEvents = "WA_AcceptTouchEvents"
        
        configure_widget_for_touch(mock_widget)
        
        mock_widget.setAttribute.assert_called_once_with("WA_AcceptTouchEvents")
        mock_widget.setAcceptDrops.assert_called_once_with(True)


if __name__ == "__main__":
    pytest.main([__file__])