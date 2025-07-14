# AGENT 4 - INTEGRATION, TESTING & PERFORMANCE

## 🎯 Your Mission (Agent 4)
You are **Agent 4** responsible for **Integration, Testing & Performance** of the complete TORE Matrix Labs V3 Document Viewer Zoom/Pan Controls system. You bring together all components from Agents 1, 2, and 3 into a production-ready, optimized, and fully tested system.

## 📋 Your Assignment: Sub-Issue #20.4
**GitHub Issue**: https://github.com/insult0o/torematrix_labs2/issues/[SUB_ISSUE_NUMBER]
**Parent Issue**: #20 - Document Viewer Zoom/Pan Controls
**Your Branch**: `feature/zoom-integration-agent4-issue204`

## 🎯 Key Responsibilities
1. **System Integration** - Unify all zoom/pan components into cohesive system
2. **Performance Optimization** - Profile and optimize for production workloads
3. **Cross-Platform Testing** - Verify compatibility across target platforms
4. **Accessibility Compliance** - Ensure WCAG 2.1 accessibility standards
5. **Error Handling** - Robust error management and edge case coverage
6. **Production Deployment** - Ready for real-world usage scenarios
7. **Documentation & Training** - Complete API documentation and usage guides

## 📁 Files You Must Create

### Integration & System Files
```
src/torematrix/ui/viewer/controls/
├── integration.py           # 🎯 YOUR MAIN FILE - System integration layer
├── performance.py           # Performance monitoring and optimization
├── accessibility.py         # Accessibility features and compliance
├── error_handler.py         # Comprehensive error management
├── config.py               # Configuration management
└── __init__.py             # Package integration exports
```

### Comprehensive Testing Suite
```
tests/integration/viewer/
├── test_zoom_pan_integration.py    # 🧪 YOUR MAIN TESTS - Full system tests
├── test_performance.py             # Performance benchmarks
├── test_accessibility.py           # Accessibility compliance tests
├── test_cross_browser.py           # Browser compatibility tests
├── test_error_handling.py          # Error scenarios and recovery
└── test_real_world_scenarios.py    # Production usage simulation
```

### Documentation & Deployment
```
docs/api/viewer/
├── zoom_pan_controls.md            # Complete API documentation
├── integration_guide.md            # Integration documentation
├── performance_guide.md            # Performance optimization guide
└── accessibility_guide.md          # Accessibility implementation guide
```

## 🔧 Technical Implementation Details

### 1. System Integration Layer (`integration.py`)
```python
from typing import Dict, List, Optional, Tuple, Any, Callable
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QThread
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PyQt6.QtGui import QKeyEvent, QMouseEvent, QWheelEvent

from .zoom import ZoomEngine
from .pan import PanEngine
from .gestures import GestureRecognizer
from .keyboard import KeyboardNavigator
from .minimap import MinimapWidget
from .zoom_presets import ZoomPresetWidget
from .zoom_indicator import ZoomIndicatorWidget
from .navigation_ui import NavigationToolbar
from .performance import PerformanceMonitor
from .error_handler import ErrorHandler
from .accessibility import AccessibilityManager

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
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Initialize core engines
        self.zoom_engine = ZoomEngine(self)
        self.pan_engine = PanEngine(self.zoom_engine, self)
        
        # Initialize interaction systems
        self.gesture_recognizer = GestureRecognizer(self)
        self.keyboard_navigator = KeyboardNavigator(self)
        
        # Initialize UI components
        self.minimap = None  # Created on demand
        self.zoom_presets = None
        self.zoom_indicator = None
        self.navigation_toolbar = None
        
        # Initialize support systems
        self.performance_monitor = PerformanceMonitor(self)
        self.error_handler = ErrorHandler(self)
        self.accessibility_manager = AccessibilityManager(self)
        
        # System state
        self.is_initialized = False
        self.document_size = (1000, 800)  # Default size
        self.view_size = (800, 600)  # Default view
        
        # Configuration
        self.config = {
            'enable_gpu_acceleration': True,
            'enable_smooth_animations': True,
            'enable_touch_gestures': True,
            'enable_keyboard_shortcuts': True,
            'performance_monitoring': True,
            'accessibility_features': True,
            'error_recovery': True
        }
        
        # Initialize system
        self._initialize_system()
    
    def _initialize_system(self):
        """Initialize the complete zoom/pan control system."""
        try:
            # Connect core engines
            self._connect_core_engines()
            
            # Setup interaction handlers
            self._setup_interaction_handlers()
            
            # Initialize performance monitoring
            self.performance_monitor.start_monitoring()
            
            # Setup error handling
            self.error_handler.initialize()
            
            # Configure accessibility
            self.accessibility_manager.setup_accessibility()
            
            self.is_initialized = True
            
        except Exception as e:
            self.error_handler.handle_initialization_error(e)
    
    def _connect_core_engines(self):
        """Connect zoom and pan engines with proper event routing."""
        # Zoom engine connections
        self.zoom_engine.zoom_changed.connect(self._on_zoom_changed)
        self.zoom_engine.zoom_started.connect(self._on_zoom_started)
        self.zoom_engine.zoom_finished.connect(self._on_zoom_finished)
        
        # Pan engine connections
        self.pan_engine.pan_changed.connect(self._on_pan_changed)
        self.pan_engine.pan_started.connect(self._on_pan_started)
        self.pan_engine.pan_finished.connect(self._on_pan_finished)
        self.pan_engine.boundary_hit.connect(self._on_boundary_hit)
        
        # Cross-engine coordination
        self.zoom_engine.zoom_changed.connect(self.pan_engine.update_zoom_factor)
    
    def _setup_interaction_handlers(self):
        """Setup all user interaction handlers."""
        # Gesture recognition
        self.gesture_recognizer.pan_gesture.connect(self._handle_pan_gesture)
        self.gesture_recognizer.pinch_gesture.connect(self._handle_pinch_gesture)
        self.gesture_recognizer.tap_gesture.connect(self._handle_tap_gesture)
        self.gesture_recognizer.double_tap_gesture.connect(self._handle_double_tap)
        
        # Keyboard navigation
        self.keyboard_navigator.pan_requested.connect(self._handle_keyboard_pan)
        self.keyboard_navigator.zoom_requested.connect(self._handle_keyboard_zoom)
    
    def create_ui_components(self, parent_widget: QWidget) -> Dict[str, QWidget]:
        """
        Create and return all UI components for zoom/pan controls.
        
        Args:
            parent_widget: Parent widget for UI components
            
        Returns:
            Dictionary of UI components keyed by component name
        """
        components = {}
        
        try:
            # Create minimap
            self.minimap = MinimapWidget(self.zoom_engine, self.pan_engine, parent_widget)
            self.minimap.navigate_requested.connect(self._handle_minimap_navigation)
            components['minimap'] = self.minimap
            
            # Create zoom presets
            self.zoom_presets = ZoomPresetWidget(self.zoom_engine, parent_widget)
            self.zoom_presets.preset_activated.connect(self._handle_preset_activation)
            components['zoom_presets'] = self.zoom_presets
            
            # Create zoom indicator
            self.zoom_indicator = ZoomIndicatorWidget(self.zoom_engine, parent_widget)
            self.zoom_indicator.zoom_level_requested.connect(self._handle_manual_zoom)
            components['zoom_indicator'] = self.zoom_indicator
            
            # Create navigation toolbar
            self.navigation_toolbar = self._create_navigation_toolbar(parent_widget)
            components['navigation_toolbar'] = self.navigation_toolbar
            
            # Setup accessibility for all components
            self.accessibility_manager.setup_component_accessibility(components)
            
            return components
            
        except Exception as e:
            self.error_handler.handle_ui_creation_error(e)
            return {}
    
    def _create_navigation_toolbar(self, parent: QWidget) -> QWidget:
        """Create integrated navigation toolbar with all controls."""
        toolbar = QWidget(parent)
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)
        
        # Add zoom presets
        if self.zoom_presets:
            layout.addWidget(self.zoom_presets)
        
        # Add separator
        layout.addSpacing(16)
        
        # Add zoom indicator
        if self.zoom_indicator:
            layout.addWidget(self.zoom_indicator)
        
        # Add stretch and minimap
        layout.addStretch()
        if self.minimap:
            layout.addWidget(self.minimap)
        
        return toolbar
    
    def handle_mouse_event(self, event: QMouseEvent) -> bool:
        """
        Handle mouse events for zoom/pan operations.
        
        Args:
            event: Qt mouse event
            
        Returns:
            bool: True if event was handled
        """
        try:
            if event.type() == QMouseEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    self.pan_engine.start_pan(event.position())
                    return True
            
            elif event.type() == QMouseEvent.Type.MouseMove:
                if self.pan_engine.is_panning:
                    self.pan_engine.update_pan(event.position())
                    return True
            
            elif event.type() == QMouseEvent.Type.MouseButtonRelease:
                if event.button() == Qt.MouseButton.LeftButton and self.pan_engine.is_panning:
                    self.pan_engine.finish_pan(event.position())
                    return True
            
            return False
            
        except Exception as e:
            self.error_handler.handle_input_error('mouse', e)
            return False
    
    def handle_wheel_event(self, event: QWheelEvent) -> bool:
        """
        Handle mouse wheel events for zooming.
        
        Args:
            event: Qt wheel event
            
        Returns:
            bool: True if event was handled
        """
        try:
            # Get wheel delta and determine zoom direction
            delta = event.angleDelta().y()
            
            if delta > 0:
                # Zoom in
                self.zoom_engine.zoom_in(center=event.position())
            elif delta < 0:
                # Zoom out
                self.zoom_engine.zoom_out(center=event.position())
            
            return True
            
        except Exception as e:
            self.error_handler.handle_input_error('wheel', e)
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
            if event.type() == QKeyEvent.Type.KeyPress:
                return self.keyboard_navigator.handle_key_press(event)
            elif event.type() == QKeyEvent.Type.KeyRelease:
                return self.keyboard_navigator.handle_key_release(event)
            
            return False
            
        except Exception as e:
            self.error_handler.handle_input_error('keyboard', e)
            return False
    
    def set_document_size(self, width: float, height: float):
        """Set document size for all components."""
        try:
            self.document_size = (width, height)
            
            # Update all components
            self.pan_engine.set_document_size(width, height)
            
            if self.minimap:
                self.minimap.set_document_size(width, height)
            
        except Exception as e:
            self.error_handler.handle_configuration_error('document_size', e)
    
    def set_view_size(self, width: float, height: float):
        """Set view size for all components."""
        try:
            self.view_size = (width, height)
            
            # Update all components
            self.pan_engine.set_view_size(width, height)
            
        except Exception as e:
            self.error_handler.handle_configuration_error('view_size', e)
    
    def get_system_state(self) -> Dict[str, Any]:
        """Get complete system state for debugging/serialization."""
        return {
            'zoom_level': self.zoom_engine.current_zoom,
            'pan_offset': (self.pan_engine.current_offset.x(), 
                          self.pan_engine.current_offset.y()),
            'document_size': self.document_size,
            'view_size': self.view_size,
            'is_panning': self.pan_engine.is_panning,
            'is_zooming': self.zoom_engine.is_zooming,
            'performance_metrics': self.performance_monitor.get_current_metrics(),
            'error_count': self.error_handler.get_error_count(),
            'accessibility_enabled': self.accessibility_manager.is_enabled()
        }
    
    def optimize_performance(self):
        """Run performance optimization routines."""
        self.performance_monitor.optimize_system()
    
    def reset_to_defaults(self):
        """Reset system to default state."""
        try:
            self.zoom_engine.zoom_to_level(1.0, animated=True)
            self.pan_engine.pan_to_position(QPointF(0, 0), animated=True)
            
        except Exception as e:
            self.error_handler.handle_reset_error(e)
    
    # Event handlers
    def _on_zoom_changed(self, zoom_level: float):
        """Handle zoom level changes."""
        self.zoom_changed.emit(zoom_level)
        self._update_navigation_state()
    
    def _on_pan_changed(self, pan_offset: QPointF):
        """Handle pan offset changes."""
        self.pan_changed.emit(pan_offset)
        self._update_navigation_state()
    
    def _update_navigation_state(self):
        """Update complete navigation state."""
        state = {
            'zoom_level': self.zoom_engine.current_zoom,
            'pan_offset': self.pan_engine.current_offset,
            'timestamp': time.time()
        }
        self.navigation_changed.emit(state)
```

### 2. Performance Monitoring (`performance.py`)
```python
import time
import psutil
import threading
from typing import Dict, List, Optional, Callable
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from dataclasses import dataclass
from collections import deque

@dataclass
class PerformanceMetrics:
    """Performance metrics data structure."""
    timestamp: float
    fps: float
    cpu_usage: float
    memory_usage: float  # MB
    zoom_operation_time: float  # ms
    pan_operation_time: float  # ms
    ui_response_time: float  # ms

class PerformanceMonitor(QObject):
    """
    Real-time performance monitoring and optimization system.
    Tracks frame rates, operation timing, and system resource usage.
    """
    
    # Performance alert signals
    performance_warning = pyqtSignal(str, dict)  # warning_type, metrics
    performance_critical = pyqtSignal(str, dict)  # critical_type, metrics
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Monitoring configuration
        self.monitoring_enabled = True
        self.sample_interval = 100  # ms
        self.history_size = 1000  # Keep last 1000 samples
        
        # Performance thresholds
        self.fps_warning_threshold = 30
        self.fps_critical_threshold = 15
        self.memory_warning_threshold = 500  # MB
        self.memory_critical_threshold = 1000  # MB
        self.operation_warning_threshold = 50  # ms
        self.operation_critical_threshold = 100  # ms
        
        # Metrics storage
        self.metrics_history = deque(maxlen=self.history_size)
        self.current_metrics = PerformanceMetrics(
            timestamp=time.time(),
            fps=60.0,
            cpu_usage=0.0,
            memory_usage=0.0,
            zoom_operation_time=0.0,
            pan_operation_time=0.0,
            ui_response_time=0.0
        )
        
        # Frame rate tracking
        self.frame_times = deque(maxlen=60)  # Last 60 frames
        self.last_frame_time = time.time()
        
        # Operation timing
        self.operation_times = {
            'zoom': deque(maxlen=100),
            'pan': deque(maxlen=100),
            'ui_update': deque(maxlen=100)
        }
        
        # Monitoring timer
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self._collect_metrics)
        
        # System process for resource monitoring
        self.process = psutil.Process()
    
    def start_monitoring(self):
        """Start performance monitoring."""
        if self.monitoring_enabled:
            self.monitor_timer.start(self.sample_interval)
    
    def stop_monitoring(self):
        """Stop performance monitoring."""
        self.monitor_timer.stop()
    
    def record_frame(self):
        """Record frame timing for FPS calculation."""
        current_time = time.time()
        frame_time = current_time - self.last_frame_time
        self.frame_times.append(frame_time)
        self.last_frame_time = current_time
    
    def record_operation_time(self, operation_type: str, duration_ms: float):
        """
        Record operation timing.
        
        Args:
            operation_type: Type of operation ('zoom', 'pan', 'ui_update')
            duration_ms: Operation duration in milliseconds
        """
        if operation_type in self.operation_times:
            self.operation_times[operation_type].append(duration_ms)
            
            # Check for performance warnings
            if duration_ms > self.operation_critical_threshold:
                self.performance_critical.emit(
                    f'{operation_type}_slow',
                    {'operation': operation_type, 'duration': duration_ms}
                )
            elif duration_ms > self.operation_warning_threshold:
                self.performance_warning.emit(
                    f'{operation_type}_slow',
                    {'operation': operation_type, 'duration': duration_ms}
                )
    
    def _collect_metrics(self):
        """Collect current performance metrics."""
        try:
            current_time = time.time()
            
            # Calculate FPS
            fps = self._calculate_fps()
            
            # Get system resource usage
            cpu_usage = self.process.cpu_percent()
            memory_info = self.process.memory_info()
            memory_usage = memory_info.rss / 1024 / 1024  # Convert to MB
            
            # Calculate average operation times
            zoom_time = self._average_operation_time('zoom')
            pan_time = self._average_operation_time('pan')
            ui_time = self._average_operation_time('ui_update')
            
            # Create metrics object
            metrics = PerformanceMetrics(
                timestamp=current_time,
                fps=fps,
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                zoom_operation_time=zoom_time,
                pan_operation_time=pan_time,
                ui_response_time=ui_time
            )
            
            # Store metrics
            self.current_metrics = metrics
            self.metrics_history.append(metrics)
            
            # Check for performance issues
            self._check_performance_thresholds(metrics)
            
        except Exception as e:
            # Don't let monitoring errors crash the system
            print(f"Performance monitoring error: {e}")
    
    def _calculate_fps(self) -> float:
        """Calculate current FPS from frame times."""
        if len(self.frame_times) < 2:
            return 60.0  # Default assumption
        
        # Calculate average frame time
        avg_frame_time = sum(self.frame_times) / len(self.frame_times)
        
        # Convert to FPS
        if avg_frame_time > 0:
            return 1.0 / avg_frame_time
        else:
            return 60.0
    
    def _average_operation_time(self, operation_type: str) -> float:
        """Calculate average operation time."""
        times = self.operation_times.get(operation_type, [])
        if not times:
            return 0.0
        return sum(times) / len(times)
    
    def _check_performance_thresholds(self, metrics: PerformanceMetrics):
        """Check metrics against performance thresholds."""
        # FPS checks
        if metrics.fps < self.fps_critical_threshold:
            self.performance_critical.emit('low_fps', {'fps': metrics.fps})
        elif metrics.fps < self.fps_warning_threshold:
            self.performance_warning.emit('low_fps', {'fps': metrics.fps})
        
        # Memory checks
        if metrics.memory_usage > self.memory_critical_threshold:
            self.performance_critical.emit('high_memory', {'memory': metrics.memory_usage})
        elif metrics.memory_usage > self.memory_warning_threshold:
            self.performance_warning.emit('high_memory', {'memory': metrics.memory_usage})
    
    def get_current_metrics(self) -> Dict:
        """Get current performance metrics as dictionary."""
        return {
            'fps': self.current_metrics.fps,
            'cpu_usage': self.current_metrics.cpu_usage,
            'memory_usage': self.current_metrics.memory_usage,
            'zoom_time': self.current_metrics.zoom_operation_time,
            'pan_time': self.current_metrics.pan_operation_time,
            'ui_time': self.current_metrics.ui_response_time,
            'timestamp': self.current_metrics.timestamp
        }
    
    def get_performance_report(self) -> Dict:
        """Generate comprehensive performance report."""
        if not self.metrics_history:
            return {}
        
        # Calculate statistics over history
        fps_values = [m.fps for m in self.metrics_history]
        memory_values = [m.memory_usage for m in self.metrics_history]
        zoom_times = [m.zoom_operation_time for m in self.metrics_history]
        pan_times = [m.pan_operation_time for m in self.metrics_history]
        
        return {
            'fps': {
                'current': self.current_metrics.fps,
                'average': sum(fps_values) / len(fps_values),
                'min': min(fps_values),
                'max': max(fps_values)
            },
            'memory': {
                'current': self.current_metrics.memory_usage,
                'average': sum(memory_values) / len(memory_values),
                'min': min(memory_values),
                'max': max(memory_values)
            },
            'zoom_performance': {
                'average_time': sum(zoom_times) / len(zoom_times) if zoom_times else 0,
                'operations_per_second': 1000 / (sum(zoom_times) / len(zoom_times)) if zoom_times else 0
            },
            'pan_performance': {
                'average_time': sum(pan_times) / len(pan_times) if pan_times else 0,
                'operations_per_second': 1000 / (sum(pan_times) / len(pan_times)) if pan_times else 0
            },
            'sample_count': len(self.metrics_history),
            'monitoring_duration': self.metrics_history[-1].timestamp - self.metrics_history[0].timestamp if len(self.metrics_history) > 1 else 0
        }
    
    def optimize_system(self):
        """Run automatic performance optimizations."""
        metrics = self.get_performance_report()
        
        # Implement optimization strategies based on metrics
        if metrics.get('fps', {}).get('average', 60) < 30:
            self._optimize_for_low_fps()
        
        if metrics.get('memory', {}).get('current', 0) > 500:
            self._optimize_for_high_memory()
    
    def _optimize_for_low_fps(self):
        """Optimize system for low FPS scenarios."""
        # Reduce animation quality, disable GPU effects, etc.
        pass
    
    def _optimize_for_high_memory(self):
        """Optimize system for high memory usage."""
        # Clear caches, reduce history size, etc.
        if len(self.metrics_history) > 500:
            # Reduce history size
            while len(self.metrics_history) > 500:
                self.metrics_history.popleft()
```

### 3. Accessibility Manager (`accessibility.py`)
```python
from typing import Dict, List, Optional
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QWidget, QLabel
from PyQt6.QtGui import QKeySequence, QAction
from PyQt6.QtCore import Qt

class AccessibilityManager(QObject):
    """
    Accessibility compliance manager for WCAG 2.1 standards.
    Provides keyboard navigation, screen reader support, and accessible UI.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Accessibility configuration
        self.enabled = True
        self.screen_reader_support = True
        self.high_contrast_mode = False
        self.keyboard_only_mode = False
        
        # ARIA labels and descriptions
        self.aria_labels = {
            'zoom_in': 'Zoom in to document',
            'zoom_out': 'Zoom out from document',
            'zoom_reset': 'Reset zoom to 100%',
            'zoom_fit': 'Fit document to window',
            'pan_up': 'Pan document up',
            'pan_down': 'Pan document down',
            'pan_left': 'Pan document left',
            'pan_right': 'Pan document right',
            'minimap': 'Document overview minimap for navigation',
            'zoom_slider': 'Zoom level slider control',
            'zoom_input': 'Manual zoom level input'
        }
        
        # Keyboard shortcuts
        self.keyboard_shortcuts = {
            'zoom_in': [QKeySequence.StandardKey.ZoomIn, QKeySequence(Qt.Key.Key_Plus)],
            'zoom_out': [QKeySequence.StandardKey.ZoomOut, QKeySequence(Qt.Key.Key_Minus)],
            'zoom_reset': [QKeySequence(Qt.KeyboardModifier.ControlModifier | Qt.Key.Key_0)],
            'zoom_fit': [QKeySequence(Qt.Key.Key_F)],
            'pan_up': [QKeySequence(Qt.Key.Key_Up)],
            'pan_down': [QKeySequence(Qt.Key.Key_Down)],
            'pan_left': [QKeySequence(Qt.Key.Key_Left)],
            'pan_right': [QKeySequence(Qt.Key.Key_Right)]
        }
    
    def setup_accessibility(self):
        """Initialize accessibility features."""
        if self.enabled:
            self._setup_screen_reader_support()
            self._setup_keyboard_navigation()
            self._setup_focus_management()
    
    def setup_component_accessibility(self, components: Dict[str, QWidget]):
        """
        Setup accessibility for UI components.
        
        Args:
            components: Dictionary of UI components to make accessible
        """
        for component_name, widget in components.items():
            self._setup_widget_accessibility(component_name, widget)
    
    def _setup_widget_accessibility(self, component_name: str, widget: QWidget):
        """Setup accessibility for a specific widget."""
        # Set accessible name and description
        if component_name in self.aria_labels:
            widget.setAccessibleName(self.aria_labels[component_name])
            widget.setAccessibleDescription(self.aria_labels[component_name])
        
        # Setup keyboard navigation
        widget.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        
        # Add tooltips for screen readers
        if component_name in self.aria_labels:
            widget.setToolTip(self.aria_labels[component_name])
        
        # Setup specific component accessibility
        if 'zoom' in component_name:
            self._setup_zoom_accessibility(widget)
        elif 'pan' in component_name:
            self._setup_pan_accessibility(widget)
        elif 'minimap' in component_name:
            self._setup_minimap_accessibility(widget)
    
    def _setup_zoom_accessibility(self, widget: QWidget):
        """Setup zoom-specific accessibility features."""
        # Add keyboard shortcuts
        if hasattr(widget, 'addAction'):
            for action_name, shortcuts in self.keyboard_shortcuts.items():
                if 'zoom' in action_name:
                    for shortcut in shortcuts:
                        action = QAction(widget)
                        action.setShortcut(shortcut)
                        widget.addAction(action)
    
    def _setup_pan_accessibility(self, widget: QWidget):
        """Setup pan-specific accessibility features."""
        # Add arrow key navigation
        if hasattr(widget, 'addAction'):
            for action_name, shortcuts in self.keyboard_shortcuts.items():
                if 'pan' in action_name:
                    for shortcut in shortcuts:
                        action = QAction(widget)
                        action.setShortcut(shortcut)
                        widget.addAction(action)
    
    def _setup_minimap_accessibility(self, widget: QWidget):
        """Setup minimap-specific accessibility features."""
        # Provide text description of minimap content
        widget.setAccessibleDescription(
            "Minimap showing document overview with current view indicator. "
            "Click to navigate to different areas of the document."
        )
    
    def _setup_screen_reader_support(self):
        """Setup screen reader compatibility."""
        # This would integrate with platform-specific screen readers
        pass
    
    def _setup_keyboard_navigation(self):
        """Setup comprehensive keyboard navigation."""
        pass
    
    def _setup_focus_management(self):
        """Setup proper focus management for keyboard users."""
        pass
    
    def is_enabled(self) -> bool:
        """Check if accessibility features are enabled."""
        return self.enabled
    
    def enable_high_contrast_mode(self):
        """Enable high contrast mode for better visibility."""
        self.high_contrast_mode = True
        # Apply high contrast styles
    
    def enable_keyboard_only_mode(self):
        """Enable keyboard-only navigation mode."""
        self.keyboard_only_mode = True
        # Hide mouse-specific UI elements
```

## 🧪 Comprehensive Testing Suite (MANDATORY >95% Coverage)

### Integration Test File (`test_zoom_pan_integration.py`)
```python
import pytest
import time
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QMouseEvent, QKeyEvent, QWheelEvent
from unittest.mock import Mock, patch

from torematrix.ui.viewer.controls.integration import ZoomPanControlSystem

class TestZoomPanIntegration:
    """Comprehensive integration tests for the complete zoom/pan system."""
    
    @pytest.fixture
    def control_system(self, qtbot):
        """Create zoom/pan control system for testing."""
        system = ZoomPanControlSystem()
        system.set_document_size(1000, 800)
        system.set_view_size(800, 600)
        yield system
        system.deleteLater()
    
    def test_system_initialization(self, control_system):
        """Test complete system initialization."""
        assert control_system.is_initialized
        assert control_system.zoom_engine is not None
        assert control_system.pan_engine is not None
        assert control_system.performance_monitor is not None
        assert control_system.error_handler is not None
    
    def test_zoom_pan_coordination(self, control_system):
        """Test zoom and pan work together correctly."""
        # Start at 100% zoom
        assert control_system.zoom_engine.current_zoom == 1.0
        
        # Zoom in to 200%
        control_system.zoom_engine.zoom_to_level(2.0, animated=False)
        assert control_system.zoom_engine.current_zoom == 2.0
        
        # Pan should be affected by zoom level
        initial_offset = control_system.pan_engine.current_offset
        control_system.pan_engine.pan_by_delta(QPointF(100, 100), animated=False)
        
        # Pan sensitivity should be reduced due to zoom
        final_offset = control_system.pan_engine.current_offset
        delta = final_offset - initial_offset
        
        # Due to 2x zoom, pan delta should be reduced
        assert abs(delta.x()) < 100  # Less than full delta due to zoom
    
    def test_mouse_event_handling(self, control_system):
        """Test complete mouse event handling pipeline."""
        # Test mouse press starts pan
        press_event = Mock()
        press_event.type.return_value = QMouseEvent.Type.MouseButtonPress
        press_event.button.return_value = Qt.MouseButton.LeftButton
        press_event.position.return_value = QPointF(400, 300)
        
        handled = control_system.handle_mouse_event(press_event)
        assert handled
        assert control_system.pan_engine.is_panning
        
        # Test mouse move updates pan
        move_event = Mock()
        move_event.type.return_value = QMouseEvent.Type.MouseMove
        move_event.position.return_value = QPointF(450, 350)
        
        handled = control_system.handle_mouse_event(move_event)
        assert handled
        
        # Test mouse release finishes pan
        release_event = Mock()
        release_event.type.return_value = QMouseEvent.Type.MouseButtonRelease
        release_event.button.return_value = Qt.MouseButton.LeftButton
        release_event.position.return_value = QPointF(450, 350)
        
        handled = control_system.handle_mouse_event(release_event)
        assert handled
        assert not control_system.pan_engine.is_panning
    
    def test_wheel_event_handling(self, control_system):
        """Test mouse wheel zoom handling."""
        # Mock wheel event for zoom in
        wheel_event = Mock()
        wheel_event.angleDelta.return_value.y.return_value = 120  # Positive delta
        wheel_event.position.return_value = QPointF(400, 300)
        
        initial_zoom = control_system.zoom_engine.current_zoom
        handled = control_system.handle_wheel_event(wheel_event)
        
        assert handled
        assert control_system.zoom_engine.current_zoom > initial_zoom
    
    def test_keyboard_event_handling(self, control_system):
        """Test keyboard navigation."""
        # Mock key press for zoom in
        key_event = Mock()
        key_event.type.return_value = QKeyEvent.Type.KeyPress
        key_event.key.return_value = Qt.Key.Key_Plus
        key_event.modifiers.return_value = Qt.KeyboardModifier.NoModifier
        
        initial_zoom = control_system.zoom_engine.current_zoom
        handled = control_system.handle_key_event(key_event)
        
        assert handled
        # Zoom level should increase (exact amount depends on implementation)
    
    def test_ui_component_creation(self, control_system, qtbot):
        """Test UI component creation and integration."""
        from PyQt6.QtWidgets import QWidget
        
        parent_widget = QWidget()
        components = control_system.create_ui_components(parent_widget)
        
        # Verify all expected components were created
        expected_components = ['minimap', 'zoom_presets', 'zoom_indicator', 'navigation_toolbar']
        for component_name in expected_components:
            assert component_name in components
            assert components[component_name] is not None
    
    def test_error_handling(self, control_system):
        """Test error handling and recovery."""
        # Force an error condition
        with patch.object(control_system.zoom_engine, 'zoom_to_level', side_effect=Exception("Test error")):
            # System should handle error gracefully
            try:
                control_system.zoom_engine.zoom_to_level(2.0)
                # Should not crash
            except Exception:
                pytest.fail("System did not handle error gracefully")
    
    def test_performance_monitoring(self, control_system):
        """Test performance monitoring integration."""
        # Performance monitor should be active
        assert control_system.performance_monitor.monitoring_enabled
        
        # Should collect metrics
        initial_metrics = control_system.performance_monitor.get_current_metrics()
        
        # Perform some operations
        control_system.zoom_engine.zoom_to_level(1.5, animated=False)
        control_system.pan_engine.pan_by_delta(QPointF(50, 50), animated=False)
        
        # Wait for metrics collection
        time.sleep(0.2)
        
        updated_metrics = control_system.performance_monitor.get_current_metrics()
        assert updated_metrics['timestamp'] > initial_metrics['timestamp']
    
    def test_accessibility_compliance(self, control_system):
        """Test accessibility features are properly configured."""
        assert control_system.accessibility_manager.is_enabled()
        
        # Create UI components and verify accessibility
        from PyQt6.QtWidgets import QWidget
        parent_widget = QWidget()
        components = control_system.create_ui_components(parent_widget)
        
        # Verify accessibility attributes
        for component in components.values():
            assert component.accessibleName() is not None or component.accessibleName() != ""
            assert component.focusPolicy() != Qt.FocusPolicy.NoFocus
    
    def test_system_state_management(self, control_system):
        """Test complete system state management."""
        # Get initial state
        initial_state = control_system.get_system_state()
        
        # Change system state
        control_system.zoom_engine.zoom_to_level(1.5, animated=False)
        control_system.pan_engine.pan_by_delta(QPointF(100, 100), animated=False)
        
        # Get updated state
        updated_state = control_system.get_system_state()
        
        # Verify state changes
        assert updated_state['zoom_level'] != initial_state['zoom_level']
        assert updated_state['pan_offset'] != initial_state['pan_offset']
    
    def test_reset_functionality(self, control_system):
        """Test system reset to defaults."""
        # Change system state
        control_system.zoom_engine.zoom_to_level(2.0, animated=False)
        control_system.pan_engine.pan_by_delta(QPointF(200, 200), animated=False)
        
        # Reset system
        control_system.reset_to_defaults()
        
        # Verify reset (may be animated, so check final state)
        time.sleep(0.5)  # Wait for animation
        assert abs(control_system.zoom_engine.current_zoom - 1.0) < 0.1
    
    def test_performance_requirements(self, control_system):
        """Test system meets all performance requirements."""
        import time
        
        # Test zoom operation timing
        zoom_times = []
        for _ in range(10):
            start = time.perf_counter()
            control_system.zoom_engine.zoom_to_level(1.5, animated=False)
            control_system.zoom_engine.zoom_to_level(1.0, animated=False)
            end = time.perf_counter()
            zoom_times.append((end - start) * 1000)  # Convert to ms
        
        avg_zoom_time = sum(zoom_times) / len(zoom_times)
        assert avg_zoom_time < 32.0, f"Zoom operations too slow: {avg_zoom_time}ms"
        
        # Test pan operation timing
        pan_times = []
        for _ in range(10):
            start = time.perf_counter()
            control_system.pan_engine.pan_by_delta(QPointF(50, 50), animated=False)
            control_system.pan_engine.pan_by_delta(QPointF(-50, -50), animated=False)
            end = time.perf_counter()
            pan_times.append((end - start) * 1000)  # Convert to ms
        
        avg_pan_time = sum(pan_times) / len(pan_times)
        assert avg_pan_time < 16.0, f"Pan operations too slow: {avg_pan_time}ms"
```

## 📊 Performance Requirements & Benchmarks

### System Performance Targets
- **Overall System Response**: <16ms for 60fps UI responsiveness
- **Zoom Operations**: Complete zoom transitions in <300ms
- **Pan Operations**: <8ms response time for smooth dragging
- **UI Updates**: All UI components update in <10ms
- **Memory Usage**: Total system memory <200MB under normal load
- **CPU Usage**: <25% CPU usage during active zoom/pan operations
- **Cross-Platform**: Consistent performance across Windows, macOS, Linux

### Benchmark Test Implementation
```python
def test_comprehensive_performance_benchmarks(control_system):
    """Comprehensive performance benchmark tests."""
    
    # System responsiveness benchmark
    response_times = []
    for _ in range(100):
        start = time.perf_counter()
        
        # Simulate user interaction
        control_system.zoom_engine.zoom_to_level(1.2, animated=False)
        control_system.pan_engine.pan_by_delta(QPointF(10, 10), animated=False)
        
        end = time.perf_counter()
        response_times.append((end - start) * 1000)
    
    avg_response = sum(response_times) / len(response_times)
    assert avg_response < 16.0, f"System response too slow: {avg_response}ms"
    
    # Memory usage benchmark
    import psutil
    process = psutil.Process()
    memory_before = process.memory_info().rss / 1024 / 1024  # MB
    
    # Perform intensive operations
    for _ in range(1000):
        control_system.zoom_engine.zoom_to_level(random.uniform(0.5, 3.0), animated=False)
    
    memory_after = process.memory_info().rss / 1024 / 1024  # MB
    memory_increase = memory_after - memory_before
    
    assert memory_increase < 50, f"Memory leak detected: {memory_increase}MB increase"
```

## 🔗 Integration Points & Dependencies

### What You Integrate
- **Agent 1: Core Zoom Engine** - Zoom calculations and animations
- **Agent 2: Pan Controls** - Navigation and gesture handling
- **Agent 3: Navigation UI** - User interface components
- **Document Viewer System** (Issue #17) - Host viewer integration
- **Coordinate Mapping** (Issue #18) - Position transformations

### APIs You Provide to the Viewer
```python
class ZoomPanControlSystem:
    def create_zoom_pan_controls(parent: QWidget) -> Dict[str, QWidget]
    def handle_viewer_events(event_type: str, event_data: dict) -> bool
    def get_current_transform_matrix() -> QTransform
    def set_document_content(document_data: dict)
    def configure_zoom_pan_settings(config: dict)
    def get_performance_metrics() -> dict
    def optimize_for_document_size(size_mb: float)
```

## 🚀 Definition of Done

### Your work is complete when:
- [ ] ✅ Complete system integration with all Agent 1-3 components working together
- [ ] ✅ Performance benchmarks met across all target platforms
- [ ] ✅ Cross-browser compatibility verified (Chrome, Firefox, Safari, Edge)
- [ ] ✅ WCAG 2.1 AA accessibility compliance achieved
- [ ] ✅ Comprehensive error handling covers all edge cases
- [ ] ✅ Real-time performance monitoring operational
- [ ] ✅ >95% test coverage across entire zoom/pan system
- [ ] ✅ Complete API documentation with usage examples
- [ ] ✅ Production deployment configuration ready
- [ ] ✅ Integration tests passing with document viewer system

You are the final piece that makes the entire zoom/pan system production-ready! 🎯