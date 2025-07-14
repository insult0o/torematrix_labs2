"""
System integration layer for zoom/pan control system.
Provides unified interface combining all zoom, pan, and navigation components.
"""

from typing import Dict, List, Optional, Tuple, Any, Callable, Union
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QThread, QRectF, QPointF, QSize
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PyQt6.QtGui import QKeyEvent, QMouseEvent, QWheelEvent, QTouchEvent
import time
import threading
from collections import deque
from dataclasses import dataclass
from enum import Enum

# Import all component modules with graceful fallbacks
try:
    from .zoom import ZoomEngine
    from .animation import AnimationEngine
except ImportError:
    # Mock classes for testing
    class ZoomEngine(QObject):
        zoom_changed = pyqtSignal(float)
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.current_zoom = 1.0
        def get_transform_matrix(self): return None
    
    class AnimationEngine(QObject):
        animation_finished = pyqtSignal()
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

try:
    from .pan import PanEngine
    from .momentum import MomentumEngine
    from .gestures import GestureRecognizer
    from .keyboard import KeyboardNavigator
except ImportError:
    # Mock classes for testing
    class PanEngine(QObject):
        pan_changed = pyqtSignal(QPointF)
        def __init__(self, zoom_engine, *args, **kwargs):
            super().__init__(*args, **kwargs)
    
    class MomentumEngine(QObject):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
    
    class GestureRecognizer(QObject):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
    
    class KeyboardNavigator(QObject):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

try:
    from .minimap import MinimapWidget
    from .zoom_presets import ZoomPresetWidget
    from .zoom_indicator import ZoomIndicatorWidget
    from .navigation_ui import NavigationToolbar
    from .zoom_history import ZoomHistoryManager
    from .selection_zoom import SelectionZoomEngine
except ImportError:
    # Mock classes for testing
    class MinimapWidget(QWidget):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
    
    class ZoomPresetWidget(QWidget):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
    
    class ZoomIndicatorWidget(QWidget):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
    
    class NavigationToolbar(QWidget):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
    
    class ZoomHistoryManager(QObject):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
    
    class SelectionZoomEngine(QObject):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)


class ControlMode(Enum):
    """Control interaction modes."""
    SELECT = "select"
    PAN = "pan"
    ZOOM = "zoom"
    ANNOTATION = "annotation"


@dataclass
class SystemState:
    """Complete system state for integration."""
    zoom_level: float
    pan_offset: QPointF
    viewport_rect: QRectF
    control_mode: ControlMode
    is_animating: bool
    timestamp: float


class ZoomPanControlSystem(QObject):
    """
    Unified zoom/pan control system integrating all components.
    Provides single interface for document viewer zoom/pan functionality.
    """
    
    # System-wide signals
    zoom_changed = pyqtSignal(float)  # zoom_level
    pan_changed = pyqtSignal(QPointF)  # pan_offset
    navigation_changed = pyqtSignal(dict)  # full_state
    error_occurred = pyqtSignal(str, str)  # error_type, error_message
    performance_warning = pyqtSignal(str, dict)  # warning_type, metrics
    mode_changed = pyqtSignal(ControlMode)  # new_mode
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Initialize core engines
        self.zoom_engine = ZoomEngine(self)
        self.animation_engine = AnimationEngine(self)
        self.pan_engine = PanEngine(self.zoom_engine, self)
        
        # Initialize interaction systems
        self.gesture_recognizer = GestureRecognizer(self)
        self.keyboard_navigator = KeyboardNavigator(self)
        
        # Initialize UI components
        self.minimap = None  # Created on demand
        self.zoom_presets = None
        self.zoom_indicator = None
        self.navigation_toolbar = None
        
        # Initialize management systems
        self.history_manager = ZoomHistoryManager(self)
        self.selection_zoom = SelectionZoomEngine(self)
        
        # System state
        self.current_mode = ControlMode.SELECT
        self.is_initialized = False
        self.document_size = QSize(1000, 800)
        self.viewport_size = QSize(800, 600)
        
        # Performance monitoring
        self.operation_times = deque(maxlen=1000)
        self.error_count = 0
        self.performance_timer = QTimer()
        self.performance_timer.timeout.connect(self._check_performance)
        self.performance_timer.setInterval(1000)  # Check every second
        
        # Thread safety
        self._system_lock = threading.RLock()
        
        # Setup signal connections
        self._connect_signals()
        
        # Start performance monitoring
        self.performance_timer.start()
    
    def initialize_system(self, document_size: QSize, viewport_size: QSize) -> bool:
        """
        Initialize the control system with document and viewport dimensions.
        
        Args:
            document_size: Size of the document
            viewport_size: Size of the viewport
            
        Returns:
            bool: True if initialization successful
        """
        start_time = time.perf_counter()
        
        try:
            with self._system_lock:
                self.document_size = document_size
                self.viewport_size = viewport_size
                
                # Configure engines
                self.pan_engine.set_document_size(document_size.width(), document_size.height())
                self.pan_engine.set_view_size(viewport_size.width(), viewport_size.height())
                
                self.selection_zoom.set_document_size(document_size.width(), document_size.height())
                self.selection_zoom.set_viewport_size(viewport_size.width(), viewport_size.height())
                
                # Initialize UI components if needed
                if self.minimap:
                    self.minimap.set_document_size(document_size.width(), document_size.height())
                
                self.is_initialized = True
                return True
                
        except Exception as e:
            self.error_occurred.emit("initialization_error", str(e))
            return False
        
        finally:
            # Record initialization time
            end_time = time.perf_counter()
            init_time = (end_time - start_time) * 1000
            self.operation_times.append(init_time)
    
    def create_ui_components(self, parent_widget: QWidget = None) -> Dict[str, QWidget]:
        """
        Create and return UI components for integration.
        
        Args:
            parent_widget: Parent widget for components
            
        Returns:
            Dict of component name to widget
        """
        components = {}
        
        try:
            # Create minimap
            self.minimap = MinimapWidget(parent_widget)
            components['minimap'] = self.minimap
            
            # Create zoom presets
            self.zoom_presets = ZoomPresetWidget(parent_widget)
            components['zoom_presets'] = self.zoom_presets
            
            # Create zoom indicator
            self.zoom_indicator = ZoomIndicatorWidget(parent_widget)
            components['zoom_indicator'] = self.zoom_indicator
            
            # Create navigation toolbar
            self.navigation_toolbar = NavigationToolbar(parent_widget)
            components['navigation_toolbar'] = self.navigation_toolbar
            
            # Connect UI signals
            self._connect_ui_signals()
            
            return components
            
        except Exception as e:
            self.error_occurred.emit("ui_creation_error", str(e))
            return {}
    
    def handle_mouse_event(self, event: QMouseEvent) -> bool:
        """
        Handle mouse events for zoom/pan operations.
        
        Args:
            event: Qt mouse event
            
        Returns:
            bool: True if event was handled
        """
        start_time = time.perf_counter()
        
        try:
            with self._system_lock:
                handled = False
                
                if self.current_mode == ControlMode.PAN:
                    handled = self._handle_pan_mouse_event(event)
                elif self.current_mode == ControlMode.ZOOM:
                    handled = self._handle_zoom_mouse_event(event)
                elif self.current_mode == ControlMode.SELECT:
                    handled = self._handle_select_mouse_event(event)
                
                return handled
                
        except Exception as e:
            self.error_occurred.emit("mouse_event_error", str(e))
            return False
        
        finally:
            # Record operation time
            end_time = time.perf_counter()
            operation_time = (end_time - start_time) * 1000
            self.operation_times.append(operation_time)
    
    def handle_wheel_event(self, event: QWheelEvent) -> bool:
        """
        Handle mouse wheel events for zooming.
        
        Args:
            event: Qt wheel event
            
        Returns:
            bool: True if event was handled
        """
        try:
            with self._system_lock:
                # Get wheel delta
                delta = event.angleDelta().y() / 120.0
                zoom_factor = 1.1 if delta > 0 else 1.0 / 1.1
                
                # Calculate new zoom level
                new_zoom = self.zoom_engine.current_zoom * zoom_factor
                
                # Apply zoom at cursor position
                cursor_pos = QPointF(event.position())
                return self.zoom_at_point(new_zoom, cursor_pos, animated=True)
                
        except Exception as e:
            self.error_occurred.emit("wheel_event_error", str(e))
            return False
    
    def handle_key_event(self, event: QKeyEvent) -> bool:
        """
        Handle keyboard events for navigation.
        
        Args:
            event: Qt key event
            
        Returns:
            bool: True if event was handled
        """
        try:
            return self.keyboard_navigator.handle_key_press(event)
        except Exception as e:
            self.error_occurred.emit("key_event_error", str(e))
            return False
    
    def handle_touch_event(self, event: QTouchEvent) -> bool:
        """
        Handle touch events for gesture recognition.
        
        Args:
            event: Qt touch event
            
        Returns:
            bool: True if event was handled
        """
        try:
            return self.gesture_recognizer.process_touch_event(event)
        except Exception as e:
            self.error_occurred.emit("touch_event_error", str(e))
            return False
    
    def set_zoom_level(self, zoom: float, animated: bool = True, center: QPointF = None) -> bool:
        """
        Set zoom level with optional animation and center point.
        
        Args:
            zoom: Target zoom level
            animated: Whether to animate the change
            center: Center point for zoom (viewport center if None)
            
        Returns:
            bool: True if zoom was applied successfully
        """
        try:
            with self._system_lock:
                if center is None:
                    center = QPointF(self.viewport_size.width() / 2, self.viewport_size.height() / 2)
                
                # Record current state for history
                self._record_state("Manual zoom")
                
                # Apply zoom
                success = self.zoom_engine.zoom_to_level(zoom, center, animated)
                
                if success:
                    self.zoom_changed.emit(zoom)
                    self._update_ui_components()
                
                return success
                
        except Exception as e:
            self.error_occurred.emit("zoom_error", str(e))
            return False
    
    def zoom_at_point(self, zoom: float, point: QPointF, animated: bool = True) -> bool:
        """
        Zoom at specific point maintaining that point's position.
        
        Args:
            zoom: Target zoom level
            point: Point to zoom at
            animated: Whether to animate
            
        Returns:
            bool: True if successful
        """
        try:
            return self.zoom_engine.zoom_at_point(zoom, point, animated)
        except Exception as e:
            self.error_occurred.emit("zoom_at_point_error", str(e))
            return False
    
    def pan_to_position(self, position: QPointF, animated: bool = True) -> bool:
        """
        Pan to specific document position.
        
        Args:
            position: Target position in document coordinates
            animated: Whether to animate
            
        Returns:
            bool: True if successful
        """
        try:
            self._record_state("Manual pan")
            success = self.pan_engine.pan_to_position(position, animated)
            
            if success:
                self.pan_changed.emit(self.pan_engine.current_offset)
                self._update_ui_components()
            
            return success
            
        except Exception as e:
            self.error_occurred.emit("pan_error", str(e))
            return False
    
    def fit_to_page(self, animated: bool = True) -> bool:
        """Fit document to viewport."""
        try:
            fit_zoom = self._calculate_fit_zoom()
            center = QPointF(self.document_size.width() / 2, self.document_size.height() / 2)
            return self.set_zoom_level(fit_zoom, animated, center)
        except Exception as e:
            self.error_occurred.emit("fit_page_error", str(e))
            return False
    
    def fit_to_width(self, animated: bool = True) -> bool:
        """Fit document width to viewport."""
        try:
            fit_zoom = self.viewport_size.width() / self.document_size.width()
            center = QPointF(self.document_size.width() / 2, self.viewport_size.height() / (2 * fit_zoom))
            return self.set_zoom_level(fit_zoom, animated, center)
        except Exception as e:
            self.error_occurred.emit("fit_width_error", str(e))
            return False
    
    def zoom_to_selection(self, selection_rect: QRectF, animated: bool = True) -> bool:
        """Zoom to specific selection rectangle."""
        try:
            return self.selection_zoom.zoom_to_rectangle(selection_rect, animated)
        except Exception as e:
            self.error_occurred.emit("selection_zoom_error", str(e))
            return False
    
    def set_control_mode(self, mode: ControlMode):
        """Set current control interaction mode."""
        if mode != self.current_mode:
            self.current_mode = mode
            self.mode_changed.emit(mode)
    
    def get_current_state(self) -> SystemState:
        """Get complete current system state."""
        return SystemState(
            zoom_level=self.zoom_engine.current_zoom,
            pan_offset=self.pan_engine.current_offset,
            viewport_rect=self._get_current_viewport_rect(),
            control_mode=self.current_mode,
            is_animating=self.animation_engine.is_animating if hasattr(self.animation_engine, 'is_animating') else False,
            timestamp=time.time()
        )
    
    def undo_navigation(self) -> bool:
        """Undo last navigation change."""
        try:
            return self.history_manager.undo()
        except Exception as e:
            self.error_occurred.emit("undo_error", str(e))
            return False
    
    def redo_navigation(self) -> bool:
        """Redo last undone navigation change."""
        try:
            return self.history_manager.redo()
        except Exception as e:
            self.error_occurred.emit("redo_error", str(e))
            return False
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive system performance metrics."""
        if not self.operation_times:
            return self._empty_metrics()
        
        avg_time = sum(self.operation_times) / len(self.operation_times)
        max_time = max(self.operation_times)
        
        # Get component metrics
        component_metrics = {}
        
        try:
            if hasattr(self.zoom_engine, 'get_performance_metrics'):
                component_metrics['zoom'] = self.zoom_engine.get_performance_metrics()
            if hasattr(self.pan_engine, 'get_performance_metrics'):
                component_metrics['pan'] = self.pan_engine.get_performance_metrics()
            if self.minimap and hasattr(self.minimap, 'get_performance_metrics'):
                component_metrics['minimap'] = self.minimap.get_performance_metrics()
        except Exception:
            pass  # Graceful fallback if metrics unavailable
        
        return {
            'system': {
                'avg_operation_time': avg_time,
                'max_operation_time': max_time,
                'operation_count': len(self.operation_times),
                'error_count': self.error_count,
                'meets_target': avg_time < 16.0,  # 60fps target
                'is_initialized': self.is_initialized
            },
            'components': component_metrics
        }
    
    def cleanup(self):
        """Clean up system resources."""
        try:
            self.performance_timer.stop()
            
            # Clear performance data
            self.operation_times.clear()
            
            # Disconnect signals
            self._disconnect_signals()
            
        except Exception as e:
            self.error_occurred.emit("cleanup_error", str(e))
    
    # Private methods
    
    def _connect_signals(self):
        """Connect internal signal routing."""
        # Zoom engine signals
        if hasattr(self.zoom_engine, 'zoom_changed'):
            self.zoom_engine.zoom_changed.connect(self._on_zoom_changed)
        
        # Pan engine signals
        if hasattr(self.pan_engine, 'pan_changed'):
            self.pan_engine.pan_changed.connect(self._on_pan_changed)
        
        # Keyboard navigation signals
        if hasattr(self.keyboard_navigator, 'pan_requested'):
            self.keyboard_navigator.pan_requested.connect(self._on_keyboard_pan)
        if hasattr(self.keyboard_navigator, 'zoom_requested'):
            self.keyboard_navigator.zoom_requested.connect(self._on_keyboard_zoom)
        
        # Gesture signals
        if hasattr(self.gesture_recognizer, 'pan_gesture_updated'):
            self.gesture_recognizer.pan_gesture_updated.connect(self._on_gesture_pan)
        if hasattr(self.gesture_recognizer, 'pinch_gesture_updated'):
            self.gesture_recognizer.pinch_gesture_updated.connect(self._on_gesture_pinch)
    
    def _connect_ui_signals(self):
        """Connect UI component signals."""
        if self.zoom_presets and hasattr(self.zoom_presets, 'zoom_to_level_requested'):
            self.zoom_presets.zoom_to_level_requested.connect(self.set_zoom_level)
        
        if self.minimap and hasattr(self.minimap, 'navigation_requested'):
            self.minimap.navigation_requested.connect(self._on_minimap_navigation)
    
    def _disconnect_signals(self):
        """Disconnect all signals."""
        # This would disconnect all connected signals
        # Implementation depends on specific signal connections
        pass
    
    def _on_zoom_changed(self, zoom: float):
        """Handle zoom change from engine."""
        self.zoom_changed.emit(zoom)
        self._record_state(f"Zoom to {zoom:.0%}")
        self._update_ui_components()
    
    def _on_pan_changed(self, offset: QPointF):
        """Handle pan change from engine."""
        self.pan_changed.emit(offset)
        self._update_ui_components()
    
    def _on_keyboard_pan(self, direction: str, distance: float):
        """Handle keyboard pan request."""
        delta = QPointF(0, 0)
        if direction == 'up':
            delta.setY(-distance)
        elif direction == 'down':
            delta.setY(distance)
        elif direction == 'left':
            delta.setX(-distance)
        elif direction == 'right':
            delta.setX(distance)
        
        self.pan_engine.pan_by_delta(delta)
    
    def _on_keyboard_zoom(self, action: str):
        """Handle keyboard zoom request."""
        current_zoom = self.zoom_engine.current_zoom
        
        if action == 'in':
            new_zoom = current_zoom * 1.2
        elif action == 'out':
            new_zoom = current_zoom / 1.2
        elif action == 'reset':
            new_zoom = 1.0
        elif action == 'fit':
            self.fit_to_page()
            return
        else:
            return
        
        self.set_zoom_level(new_zoom)
    
    def _on_gesture_pan(self, start: QPointF, current: QPointF):
        """Handle gesture pan update."""
        delta = current - start
        self.pan_engine.pan_by_delta(delta)
    
    def _on_gesture_pinch(self, scale: float, center: QPointF):
        """Handle gesture pinch update."""
        new_zoom = self.zoom_engine.current_zoom * scale
        self.zoom_at_point(new_zoom, center)
    
    def _on_minimap_navigation(self, position: QPointF):
        """Handle minimap navigation request."""
        self.pan_to_position(position)
    
    def _handle_pan_mouse_event(self, event: QMouseEvent) -> bool:
        """Handle mouse event in pan mode."""
        # Implementation would depend on specific pan interaction design
        return False
    
    def _handle_zoom_mouse_event(self, event: QMouseEvent) -> bool:
        """Handle mouse event in zoom mode."""
        # Implementation would depend on specific zoom interaction design
        return False
    
    def _handle_select_mouse_event(self, event: QMouseEvent) -> bool:
        """Handle mouse event in select mode."""
        # Implementation would depend on specific selection interaction design
        return False
    
    def _update_ui_components(self):
        """Update all UI components with current state."""
        current_state = self.get_current_state()
        
        if self.zoom_indicator:
            self.zoom_indicator.set_zoom_level(current_state.zoom_level)
        
        if self.minimap:
            self.minimap.update_viewport(
                current_state.viewport_rect,
                current_state.zoom_level,
                current_state.pan_offset
            )
        
        if self.zoom_presets:
            self.zoom_presets.set_current_zoom(current_state.zoom_level)
    
    def _record_state(self, description: str):
        """Record current state to history."""
        current_state = self.get_current_state()
        self.history_manager.push_state(
            current_state.zoom_level,
            current_state.pan_offset,
            current_state.viewport_rect,
            description
        )
    
    def _get_current_viewport_rect(self) -> QRectF:
        """Calculate current viewport rectangle in document coordinates."""
        zoom = self.zoom_engine.current_zoom
        pan_offset = self.pan_engine.current_offset
        
        # Convert viewport to document coordinates
        doc_x = -pan_offset.x() / zoom
        doc_y = -pan_offset.y() / zoom
        doc_width = self.viewport_size.width() / zoom
        doc_height = self.viewport_size.height() / zoom
        
        return QRectF(doc_x, doc_y, doc_width, doc_height)
    
    def _calculate_fit_zoom(self) -> float:
        """Calculate zoom level to fit document to viewport."""
        zoom_x = self.viewport_size.width() / self.document_size.width()
        zoom_y = self.viewport_size.height() / self.document_size.height()
        return min(zoom_x, zoom_y)
    
    def _check_performance(self):
        """Check system performance and emit warnings if needed."""
        if not self.operation_times:
            return
        
        recent_times = list(self.operation_times)[-100:]  # Last 100 operations
        avg_time = sum(recent_times) / len(recent_times)
        
        if avg_time > 32.0:  # More than 32ms (30fps)
            warning_data = {
                'avg_time': avg_time,
                'max_time': max(recent_times),
                'operation_count': len(recent_times)
            }
            self.performance_warning.emit("slow_operations", warning_data)
    
    def _empty_metrics(self) -> Dict[str, Any]:
        """Return empty metrics structure."""
        return {
            'system': {
                'avg_operation_time': 0.0,
                'max_operation_time': 0.0,
                'operation_count': 0,
                'error_count': 0,
                'meets_target': True,
                'is_initialized': self.is_initialized
            },
            'components': {}
        }