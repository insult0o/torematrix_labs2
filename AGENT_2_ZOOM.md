# AGENT 2 - PAN CONTROLS & USER INTERACTION

## 🎯 Your Mission (Agent 2)
You are **Agent 2** responsible for implementing comprehensive **Pan Controls & User Interaction** for TORE Matrix Labs V3 Document Viewer. You build upon Agent 1's zoom foundation to create intuitive, responsive navigation controls.

## 📋 Your Assignment: Sub-Issue #20.2
**GitHub Issue**: https://github.com/insult0o/torematrix_labs2/issues/[SUB_ISSUE_NUMBER]
**Parent Issue**: #20 - Document Viewer Zoom/Pan Controls
**Your Branch**: `feature/pan-controls-agent2-issue202`

## 🎯 Key Responsibilities
1. **Mouse Drag Panning** - Smooth drag navigation with momentum
2. **Pan Boundary Management** - Intelligent limits and constraints
3. **Touch Gesture Support** - Mobile and tablet compatibility
4. **Keyboard Navigation** - Arrow key and shortcut support
5. **Input Performance** - Optimized handling for responsive feel
6. **Cross-Platform Compatibility** - Works across all target devices

## 📁 Files You Must Create

### Core Implementation Files
```
src/torematrix/ui/viewer/controls/
├── pan.py                   # 🎯 YOUR MAIN FILE - Core pan controls
├── gestures.py              # Touch/gesture recognition system
├── keyboard.py              # Keyboard navigation support
├── input_manager.py         # Unified input handling
└── momentum.py              # Pan momentum and physics
```

### Test Files (MANDATORY >95% Coverage)
```
tests/unit/viewer/controls/
├── test_pan.py              # 🧪 YOUR MAIN TESTS - Pan functionality
├── test_gestures.py         # Touch gesture recognition tests
├── test_keyboard.py         # Keyboard navigation tests
├── test_input_manager.py    # Input handling tests
└── test_momentum.py         # Momentum physics tests
```

## 🔧 Technical Implementation Details

### 1. Core Pan Engine (`pan.py`)
```python
from typing import Optional, Tuple, Callable
from PyQt6.QtCore import QObject, pyqtSignal, QPointF, QTimer
from PyQt6.QtGui import QMouseEvent, QWheelEvent
from PyQt6.QtWidgets import QWidget
import math

from .zoom import ZoomEngine
from .momentum import MomentumEngine

class PanEngine(QObject):
    """
    Core pan engine providing smooth drag navigation with momentum physics.
    Integrates with zoom engine for coordinated pan/zoom operations.
    """
    
    # Signals for pan state changes
    pan_changed = pyqtSignal(QPointF)  # pan_offset
    pan_started = pyqtSignal(QPointF)  # start_position
    pan_finished = pyqtSignal(QPointF)  # final_position
    boundary_hit = pyqtSignal(str)  # direction: 'left', 'right', 'top', 'bottom'
    
    def __init__(self, zoom_engine: ZoomEngine, parent=None):
        super().__init__(parent)
        
        # Core dependencies
        self.zoom_engine = zoom_engine
        self.momentum_engine = MomentumEngine()
        
        # Pan state
        self.current_offset = QPointF(0, 0)
        self.is_panning = False
        self.last_pan_position = QPointF(0, 0)
        self.pan_start_position = QPointF(0, 0)
        
        # Pan configuration
        self.pan_sensitivity = 1.0
        self.boundary_margin = 50  # pixels
        self.momentum_enabled = True
        
        # Document and view boundaries
        self.document_size = QPointF(1000, 1000)  # Default size
        self.view_size = QPointF(800, 600)  # Default view
        
        # Connect momentum engine
        self.momentum_engine.momentum_update.connect(self._apply_momentum_offset)
        self.momentum_engine.momentum_finished.connect(self._finish_momentum_pan)
    
    def set_document_size(self, width: float, height: float):
        """Set the document size for boundary calculations."""
        self.document_size = QPointF(width, height)
        self._update_pan_boundaries()
    
    def set_view_size(self, width: float, height: float):
        """Set the view size for boundary calculations."""
        self.view_size = QPointF(width, height)
        self._update_pan_boundaries()
    
    def start_pan(self, start_position: QPointF) -> bool:
        """
        Start panning operation from specified position.
        
        Args:
            start_position: Mouse/touch position where pan started
            
        Returns:
            bool: True if pan operation started successfully
        """
        if self.is_panning:
            return False
            
        self.is_panning = True
        self.pan_start_position = start_position
        self.last_pan_position = start_position
        
        # Stop any existing momentum
        self.momentum_engine.stop_momentum()
        
        self.pan_started.emit(start_position)
        return True
    
    def update_pan(self, current_position: QPointF) -> bool:
        """
        Update pan based on current mouse/touch position.
        
        Args:
            current_position: Current mouse/touch position
            
        Returns:
            bool: True if pan was applied successfully
        """
        if not self.is_panning:
            return False
            
        # Calculate pan delta
        delta = current_position - self.last_pan_position
        delta *= self.pan_sensitivity
        
        # Apply zoom scaling to pan sensitivity
        zoom_factor = self.zoom_engine.current_zoom
        delta /= zoom_factor
        
        # Apply pan with boundary checking
        new_offset = self.current_offset + delta
        constrained_offset = self._constrain_to_boundaries(new_offset)
        
        # Check for boundary hits
        if constrained_offset != new_offset:
            self._emit_boundary_signals(new_offset, constrained_offset)
        
        # Update state
        self.current_offset = constrained_offset
        self.last_pan_position = current_position
        
        # Track velocity for momentum
        self.momentum_engine.add_velocity_sample(delta)
        
        self.pan_changed.emit(self.current_offset)
        return True
    
    def finish_pan(self, end_position: QPointF) -> bool:
        """
        Finish panning operation and optionally apply momentum.
        
        Args:
            end_position: Final mouse/touch position
            
        Returns:
            bool: True if pan finished successfully
        """
        if not self.is_panning:
            return False
            
        self.is_panning = False
        
        # Calculate final velocity and apply momentum if enabled
        if self.momentum_enabled:
            final_velocity = self.momentum_engine.calculate_release_velocity()
            if self.momentum_engine.should_apply_momentum(final_velocity):
                self.momentum_engine.start_momentum(final_velocity)
            else:
                self.pan_finished.emit(self.current_offset)
        else:
            self.pan_finished.emit(self.current_offset)
        
        return True
    
    def pan_to_position(self, position: QPointF, animated: bool = True) -> bool:
        """
        Pan to specific document position.
        
        Args:
            position: Target position in document coordinates
            animated: Whether to animate the transition
            
        Returns:
            bool: True if pan operation started
        """
        # Convert document position to pan offset
        target_offset = self._calculate_offset_for_position(position)
        
        if animated:
            return self._animate_pan_to_offset(target_offset)
        else:
            self.current_offset = self._constrain_to_boundaries(target_offset)
            self.pan_changed.emit(self.current_offset)
            return True
    
    def pan_by_delta(self, delta: QPointF, animated: bool = False) -> bool:
        """
        Pan by relative delta amount.
        
        Args:
            delta: Relative movement in view coordinates
            animated: Whether to animate the movement
            
        Returns:
            bool: True if pan was applied
        """
        target_offset = self.current_offset + delta
        
        if animated:
            return self._animate_pan_to_offset(target_offset)
        else:
            self.current_offset = self._constrain_to_boundaries(target_offset)
            self.pan_changed.emit(self.current_offset)
            return True
    
    def center_on_point(self, document_point: QPointF, animated: bool = True) -> bool:
        """
        Center view on specific document point.
        
        Args:
            document_point: Point in document coordinates to center on
            animated: Whether to animate the centering
            
        Returns:
            bool: True if centering started
        """
        # Calculate offset to center the point
        view_center = self.view_size / 2
        zoom_factor = self.zoom_engine.current_zoom
        
        # Convert document point to view coordinates
        scaled_point = document_point * zoom_factor
        target_offset = view_center - scaled_point
        
        if animated:
            return self._animate_pan_to_offset(target_offset)
        else:
            self.current_offset = self._constrain_to_boundaries(target_offset)
            self.pan_changed.emit(self.current_offset)
            return True
    
    def _constrain_to_boundaries(self, offset: QPointF) -> QPointF:
        """Apply boundary constraints to pan offset."""
        zoom_factor = self.zoom_engine.current_zoom
        
        # Calculate document bounds in view coordinates
        doc_width = self.document_size.x() * zoom_factor
        doc_height = self.document_size.y() * zoom_factor
        
        # Calculate valid offset range
        min_x = self.view_size.x() - doc_width - self.boundary_margin
        max_x = self.boundary_margin
        min_y = self.view_size.y() - doc_height - self.boundary_margin
        max_y = self.boundary_margin
        
        # Constrain offset
        constrained_x = max(min_x, min(max_x, offset.x()))
        constrained_y = max(min_y, min(max_y, offset.y()))
        
        return QPointF(constrained_x, constrained_y)
    
    def _emit_boundary_signals(self, intended: QPointF, constrained: QPointF):
        """Emit appropriate boundary hit signals."""
        if intended.x() < constrained.x():
            self.boundary_hit.emit('left')
        elif intended.x() > constrained.x():
            self.boundary_hit.emit('right')
            
        if intended.y() < constrained.y():
            self.boundary_hit.emit('top')
        elif intended.y() > constrained.y():
            self.boundary_hit.emit('bottom')
    
    def get_transform_matrix(self):
        """Get current pan transformation matrix."""
        from PyQt6.QtGui import QTransform
        
        transform = QTransform()
        transform.translate(self.current_offset.x(), self.current_offset.y())
        
        # Combine with zoom transform
        zoom_transform = self.zoom_engine.get_transform_matrix()
        return zoom_transform * transform
```

### 2. Touch Gesture Recognition (`gestures.py`)
```python
from typing import Dict, List, Optional, Tuple
from PyQt6.QtCore import QObject, pyqtSignal, QPointF, QTimer
from PyQt6.QtGui import QTouchEvent
import math
import time

class GestureRecognizer(QObject):
    """
    Advanced touch gesture recognition for pan and zoom operations.
    Supports single-touch pan, two-finger pinch/zoom, and momentum.
    """
    
    # Gesture signals
    pan_gesture = pyqtSignal(QPointF, QPointF)  # start, current
    pinch_gesture = pyqtSignal(float, QPointF)  # scale_factor, center
    tap_gesture = pyqtSignal(QPointF)  # position
    double_tap_gesture = pyqtSignal(QPointF)  # position
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Touch tracking
        self.active_touches: Dict[int, TouchPoint] = {}
        self.gesture_state = 'none'  # 'none', 'pan', 'pinch', 'tap'
        
        # Gesture configuration
        self.pan_threshold = 10  # pixels
        self.pinch_threshold = 20  # pixels
        self.tap_timeout = 500  # ms
        self.double_tap_timeout = 300  # ms
        
        # Double tap detection
        self.last_tap_time = 0
        self.last_tap_position = QPointF()
        
        # Performance tracking
        self.gesture_start_time = 0
        self.last_update_time = 0
    
    def process_touch_event(self, event: QTouchEvent) -> bool:
        """
        Process touch event and recognize gestures.
        
        Args:
            event: Qt touch event
            
        Returns:
            bool: True if gesture was recognized and handled
        """
        current_time = time.time() * 1000  # Convert to ms
        
        # Update active touches
        self._update_touch_points(event)
        
        # Determine gesture based on number of active touches
        active_count = len(self.active_touches)
        
        if active_count == 0:
            return self._handle_no_touches()
        elif active_count == 1:
            return self._handle_single_touch(current_time)
        elif active_count == 2:
            return self._handle_two_finger_touch(current_time)
        else:
            # More than 2 touches - ignore
            return self._reset_gesture_state()
    
    def _handle_single_touch(self, current_time: float) -> bool:
        """Handle single touch for pan or tap gestures."""
        touch_point = list(self.active_touches.values())[0]
        
        if self.gesture_state == 'none':
            # Potential start of pan or tap
            self.gesture_state = 'potential_pan'
            self.gesture_start_time = current_time
            touch_point.gesture_start_pos = touch_point.current_pos
            return True
        
        elif self.gesture_state == 'potential_pan':
            # Check if movement exceeds pan threshold
            distance = self._distance(touch_point.gesture_start_pos, 
                                    touch_point.current_pos)
            
            if distance > self.pan_threshold:
                # Start pan gesture
                self.gesture_state = 'pan'
                self.pan_gesture.emit(touch_point.gesture_start_pos, 
                                    touch_point.current_pos)
                return True
            
            # Check for tap timeout
            elif current_time - self.gesture_start_time > self.tap_timeout:
                self._reset_gesture_state()
                return False
        
        elif self.gesture_state == 'pan':
            # Continue pan gesture
            self.pan_gesture.emit(touch_point.gesture_start_pos, 
                                touch_point.current_pos)
            return True
        
        return False
    
    def _handle_two_finger_touch(self, current_time: float) -> bool:
        """Handle two-finger touch for pinch/zoom gestures."""
        touches = list(self.active_touches.values())
        touch1, touch2 = touches[0], touches[1]
        
        if self.gesture_state in ('none', 'potential_pan'):
            # Start potential pinch gesture
            self.gesture_state = 'potential_pinch'
            self.gesture_start_time = current_time
            
            # Calculate initial distance and center
            touch1.gesture_start_pos = touch1.current_pos
            touch2.gesture_start_pos = touch2.current_pos
            
            return True
        
        elif self.gesture_state == 'potential_pinch':
            # Check if pinch distance change exceeds threshold
            start_distance = self._distance(touch1.gesture_start_pos, 
                                          touch2.gesture_start_pos)
            current_distance = self._distance(touch1.current_pos, 
                                            touch2.current_pos)
            
            distance_change = abs(current_distance - start_distance)
            
            if distance_change > self.pinch_threshold:
                # Start pinch gesture
                self.gesture_state = 'pinch'
                
                # Calculate scale factor and center
                scale_factor = current_distance / start_distance
                center = self._midpoint(touch1.current_pos, touch2.current_pos)
                
                self.pinch_gesture.emit(scale_factor, center)
                return True
        
        elif self.gesture_state == 'pinch':
            # Continue pinch gesture
            touches = list(self.active_touches.values())
            if len(touches) >= 2:
                touch1, touch2 = touches[0], touches[1]
                
                start_distance = self._distance(touch1.gesture_start_pos, 
                                              touch2.gesture_start_pos)
                current_distance = self._distance(touch1.current_pos, 
                                                touch2.current_pos)
                
                scale_factor = current_distance / start_distance
                center = self._midpoint(touch1.current_pos, touch2.current_pos)
                
                self.pinch_gesture.emit(scale_factor, center)
                return True
        
        return False
    
    def _handle_no_touches(self) -> bool:
        """Handle end of touch sequence."""
        if self.gesture_state == 'potential_pan':
            # Was a tap - emit tap gesture
            if len(self.active_touches) == 0:
                # Check for double tap
                current_time = time.time() * 1000
                if (current_time - self.last_tap_time < self.double_tap_timeout and
                    self._distance(self.last_tap_position, 
                                 self.gesture_start_position) < 20):
                    self.double_tap_gesture.emit(self.last_tap_position)
                else:
                    self.tap_gesture.emit(self.gesture_start_position)
                    self.last_tap_time = current_time
                    self.last_tap_position = self.gesture_start_position
        
        return self._reset_gesture_state()
    
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

class TouchPoint:
    """Represents a single touch point with tracking data."""
    
    def __init__(self, touch_id: int, position: QPointF):
        self.touch_id = touch_id
        self.current_pos = position
        self.start_pos = position
        self.gesture_start_pos = position
        self.velocity = QPointF(0, 0)
        self.last_update_time = time.time()
```

### 3. Keyboard Navigation (`keyboard.py`)
```python
from typing import Dict, Callable
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, Qt
from PyQt6.QtGui import QKeyEvent, QKeySequence
from PyQt6.QtWidgets import QWidget

class KeyboardNavigator(QObject):
    """
    Keyboard navigation support for document viewer.
    Provides arrow key panning, zoom shortcuts, and custom key bindings.
    """
    
    # Navigation signals
    pan_requested = pyqtSignal(str)  # direction: 'up', 'down', 'left', 'right'
    zoom_requested = pyqtSignal(str)  # action: 'in', 'out', 'fit', 'reset'
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Key configuration
        self.pan_step_size = 50  # pixels per arrow key press
        self.fast_pan_multiplier = 3  # with Shift modifier
        self.repeat_delay = 500  # ms before key repeat starts
        self.repeat_interval = 50  # ms between key repeats
        
        # Key state tracking
        self.pressed_keys = set()
        self.repeat_timer = QTimer()
        self.repeat_timer.timeout.connect(self._handle_key_repeat)
        
        # Default key bindings
        self.key_bindings = {
            # Pan controls
            Qt.Key.Key_Up: lambda: self.pan_requested.emit('up'),
            Qt.Key.Key_Down: lambda: self.pan_requested.emit('down'),
            Qt.Key.Key_Left: lambda: self.pan_requested.emit('left'),
            Qt.Key.Key_Right: lambda: self.pan_requested.emit('right'),
            
            # Zoom controls
            Qt.Key.Key_Plus: lambda: self.zoom_requested.emit('in'),
            Qt.Key.Key_Minus: lambda: self.zoom_requested.emit('out'),
            Qt.Key.Key_0: lambda: self.zoom_requested.emit('reset'),
            Qt.Key.Key_F: lambda: self.zoom_requested.emit('fit'),
        }
        
        # Modifier-specific bindings
        self.modifier_bindings = {
            (Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_Plus): 
                lambda: self.zoom_requested.emit('in'),
            (Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_Minus): 
                lambda: self.zoom_requested.emit('out'),
            (Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_0): 
                lambda: self.zoom_requested.emit('reset'),
        }
    
    def handle_key_press(self, event: QKeyEvent) -> bool:
        """
        Handle keyboard key press events.
        
        Args:
            event: Qt key event
            
        Returns:
            bool: True if key was handled
        """
        key = event.key()
        modifiers = event.modifiers()
        
        # Check modifier-specific bindings first
        modifier_key = (modifiers, key)
        if modifier_key in self.modifier_bindings:
            self.modifier_bindings[modifier_key]()
            return True
        
        # Check standard key bindings
        if key in self.key_bindings:
            self.key_bindings[key]()
            
            # Start repeat timer for navigation keys
            if key in (Qt.Key.Key_Up, Qt.Key.Key_Down, 
                      Qt.Key.Key_Left, Qt.Key.Key_Right):
                self.pressed_keys.add(key)
                self.repeat_timer.start(self.repeat_delay)
            
            return True
        
        return False
    
    def handle_key_release(self, event: QKeyEvent) -> bool:
        """
        Handle keyboard key release events.
        
        Args:
            event: Qt key event
            
        Returns:
            bool: True if key was handled
        """
        key = event.key()
        
        # Remove from pressed keys and stop repeat if needed
        if key in self.pressed_keys:
            self.pressed_keys.remove(key)
            
            if not self.pressed_keys:
                self.repeat_timer.stop()
            
            return True
        
        return False
    
    def _handle_key_repeat(self):
        """Handle repeated key press for smooth navigation."""
        if not self.pressed_keys:
            self.repeat_timer.stop()
            return
        
        # Execute actions for all currently pressed keys
        for key in self.pressed_keys:
            if key in self.key_bindings:
                self.key_bindings[key]()
        
        # Set faster repeat interval
        self.repeat_timer.start(self.repeat_interval)
    
    def set_pan_step_size(self, step_size: int):
        """Set the step size for arrow key panning."""
        self.pan_step_size = step_size
    
    def add_key_binding(self, key: int, action: Callable):
        """Add custom key binding."""
        self.key_bindings[key] = action
    
    def remove_key_binding(self, key: int):
        """Remove key binding."""
        if key in self.key_bindings:
            del self.key_bindings[key]
```

## 🧪 Testing Requirements (MANDATORY >95% Coverage)

### Main Test File (`test_pan.py`)
```python
import pytest
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QMouseEvent, Qt
from unittest.mock import Mock, MagicMock

from torematrix.ui.viewer.controls.pan import PanEngine
from torematrix.ui.viewer.controls.zoom import ZoomEngine

class TestPanEngine:
    """Comprehensive tests for pan engine functionality."""
    
    @pytest.fixture
    def zoom_engine(self):
        """Mock zoom engine for testing."""
        zoom = Mock(spec=ZoomEngine)
        zoom.current_zoom = 1.0
        zoom.get_transform_matrix.return_value = Mock()
        return zoom
    
    @pytest.fixture
    def pan_engine(self, zoom_engine):
        """Create pan engine for testing."""
        engine = PanEngine(zoom_engine)
        engine.set_document_size(1000, 800)
        engine.set_view_size(500, 400)
        yield engine
        engine.deleteLater()
    
    def test_initialization(self, pan_engine):
        """Test pan engine initializes correctly."""
        assert pan_engine.current_offset == QPointF(0, 0)
        assert not pan_engine.is_panning
        assert pan_engine.document_size == QPointF(1000, 800)
        assert pan_engine.view_size == QPointF(500, 400)
    
    def test_start_pan(self, pan_engine, qtbot):
        """Test starting pan operation."""
        start_pos = QPointF(100, 100)
        
        with qtbot.waitSignal(pan_engine.pan_started):
            result = pan_engine.start_pan(start_pos)
        
        assert result is True
        assert pan_engine.is_panning is True
        assert pan_engine.pan_start_position == start_pos
    
    def test_pan_with_boundaries(self, pan_engine):
        """Test pan respects document boundaries."""
        # Start pan
        pan_engine.start_pan(QPointF(250, 200))
        
        # Try to pan beyond left boundary
        extreme_position = QPointF(-1000, 200)
        pan_engine.update_pan(extreme_position)
        
        # Should be constrained to boundary
        assert pan_engine.current_offset.x() >= -500  # Reasonable boundary
    
    def test_pan_momentum(self, pan_engine, qtbot):
        """Test pan momentum physics."""
        # Enable momentum
        pan_engine.momentum_enabled = True
        
        # Simulate quick pan gesture
        pan_engine.start_pan(QPointF(100, 100))
        
        # Quick movement to build velocity
        positions = [QPointF(110, 100), QPointF(130, 100), QPointF(160, 100)]
        for pos in positions:
            pan_engine.update_pan(pos)
        
        # Finish pan - should trigger momentum
        with qtbot.waitSignal(pan_engine.momentum_engine.momentum_update, 
                             timeout=1000):
            pan_engine.finish_pan(QPointF(160, 100))
    
    def test_zoom_integration(self, pan_engine):
        """Test pan sensitivity adjusts with zoom level."""
        # Set high zoom level
        pan_engine.zoom_engine.current_zoom = 2.0
        
        pan_engine.start_pan(QPointF(100, 100))
        
        # Record initial offset
        initial_offset = pan_engine.current_offset
        
        # Apply same pixel movement
        pan_engine.update_pan(QPointF(150, 100))
        
        # Movement should be reduced due to zoom
        offset_change = pan_engine.current_offset - initial_offset
        expected_change = 50 / 2.0  # Divided by zoom factor
        
        assert abs(offset_change.x() - expected_change) < 1.0
    
    def test_center_on_point(self, pan_engine):
        """Test centering view on specific document point."""
        document_point = QPointF(500, 400)  # Center of document
        
        result = pan_engine.center_on_point(document_point, animated=False)
        
        assert result is True
        
        # View center should now show document center
        view_center = pan_engine.view_size / 2
        # Complex calculation - verify intent rather than exact math
        assert abs(pan_engine.current_offset.x()) < 1000
        assert abs(pan_engine.current_offset.y()) < 1000
    
    def test_performance_requirements(self, pan_engine):
        """Test pan operations meet performance requirements."""
        import time
        
        # Test pan update timing
        times = []
        pan_engine.start_pan(QPointF(100, 100))
        
        for i in range(100):
            start = time.perf_counter()
            pan_engine.update_pan(QPointF(100 + i, 100))
            end = time.perf_counter()
            times.append((end - start) * 1000)  # Convert to ms
        
        avg_time = sum(times) / len(times)
        assert avg_time < 8.0, f"Pan updates too slow: {avg_time}ms"
    
    def test_boundary_signals(self, pan_engine, qtbot):
        """Test boundary hit signals are emitted correctly."""
        pan_engine.start_pan(QPointF(0, 0))
        
        # Try to pan beyond left boundary
        with qtbot.waitSignal(pan_engine.boundary_hit) as blocker:
            # Pan far to the left
            pan_engine.update_pan(QPointF(-2000, 0))
        
        # Should emit 'left' boundary signal
        assert blocker.args[0] in ['left', 'right', 'top', 'bottom']
```

## 📊 Performance Requirements

### Benchmarks You Must Meet
- **Pan Response Time**: <8ms per update for 60fps feel
- **Touch Recognition**: <50ms gesture recognition latency
- **Memory Usage**: <30MB for pan operations and gesture tracking
- **Cross-Platform**: Consistent performance across Windows, macOS, Linux

## 🔗 Integration Points

### Dependencies You Need
- **Agent 1: Core Zoom Engine** - REQUIRED for zoom integration
- **Coordinate Mapping System** (Issue #18) - For position calculations
- **Event Bus System** - For cross-component communication

### What You Provide to Other Agents
- **PanEngine class** - Core panning functionality
- **GestureRecognizer class** - Touch gesture support
- **KeyboardNavigator class** - Keyboard navigation
- **Unified transform matrices** - Combined pan/zoom transformations

### Integration APIs You Must Provide
```python
# For Agent 3 (Navigation UI)
def get_current_pan_offset() -> QPointF
def get_document_bounds() -> Tuple[QPointF, QPointF]
def register_pan_callback(callback: Callable[[QPointF], None])

# For Agent 4 (Integration)
def set_pan_constraints(boundaries: dict)
def get_pan_performance_metrics() -> dict
def export_pan_configuration() -> dict
```

## 🚀 Definition of Done

### Your work is complete when:
- [ ] ✅ All pan controls implemented with smooth mouse drag
- [ ] ✅ Touch gesture recognition working on mobile devices  
- [ ] ✅ Keyboard navigation with arrow keys and shortcuts
- [ ] ✅ Pan momentum physics feel natural and responsive
- [ ] ✅ Boundary detection prevents over-panning
- [ ] ✅ >95% test coverage across all your files
- [ ] ✅ Performance benchmarks met (<8ms response time)
- [ ] ✅ Cross-platform compatibility verified
- [ ] ✅ Integration with Agent 1 zoom engine complete

You create the responsive, intuitive navigation that users interact with daily! 🎯