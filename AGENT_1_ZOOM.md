# AGENT 1 - CORE ZOOM ENGINE & ANIMATION FRAMEWORK

## 🎯 Your Mission (Agent 1)
You are **Agent 1** responsible for implementing the foundational **Core Zoom Engine & Animation Framework** for TORE Matrix Labs V3 Document Viewer. Your work creates the essential zoom infrastructure that Agents 2, 3, and 4 will build upon.

## 📋 Your Assignment: Sub-Issue #20.1
**GitHub Issue**: https://github.com/insult0o/torematrix_labs2/issues/[SUB_ISSUE_NUMBER]
**Parent Issue**: #20 - Document Viewer Zoom/Pan Controls
**Your Branch**: `feature/zoom-engine-agent1-issue201`

## 🎯 Key Responsibilities
1. **Core Zoom Engine** - Exponential scaling algorithms with precision
2. **GPU-Accelerated Animations** - Smooth 60fps zoom transitions
3. **Zoom Constraints** - Safe zoom level limits and validation
4. **Point-Based Zooming** - Accurate zoom-around-cursor calculations
5. **Performance Foundation** - Optimized for large documents
6. **Thread Safety** - Concurrent zoom operations support

## 📁 Files You Must Create

### Core Implementation Files
```
src/torematrix/ui/viewer/controls/
├── __init__.py              # Controls package initialization
├── zoom.py                  # 🎯 YOUR MAIN FILE - Core zoom engine
├── animation.py             # GPU-accelerated animation framework
└── base.py                  # Base classes for controls
```

### Test Files (MANDATORY >95% Coverage)
```
tests/unit/viewer/controls/
├── __init__.py              # Test package initialization  
├── test_zoom.py             # 🧪 YOUR MAIN TESTS - Comprehensive zoom tests
├── test_animation.py        # Animation framework tests
└── test_base.py             # Base classes tests
```

## 🔧 Technical Implementation Details

### 1. Core Zoom Engine (`zoom.py`)
```python
from typing import Optional, Tuple, Callable
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QPointF
from PyQt6.QtGui import QTransform
import math

class ZoomEngine(QObject):
    """
    Core zoom engine with GPU-accelerated scaling and smooth animations.
    Provides exponential zoom progression and point-based zoom calculations.
    """
    
    # Signals for zoom state changes
    zoom_changed = pyqtSignal(float)  # zoom_level
    zoom_started = pyqtSignal()
    zoom_finished = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Zoom configuration
        self.min_zoom = 0.1  # 10%
        self.max_zoom = 8.0  # 800%
        self.current_zoom = 1.0  # 100%
        self.zoom_factor = 1.2  # Exponential progression
        
        # Animation system
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self._animate_zoom)
        self.animation_duration = 300  # ms
        self.animation_fps = 60
        
        # Zoom state
        self.is_zooming = False
        self.target_zoom = 1.0
        self.zoom_center = QPointF(0, 0)
        
    def zoom_to_level(self, zoom_level: float, center: Optional[QPointF] = None, 
                     animated: bool = True) -> bool:
        """
        Zoom to specific level with optional animation.
        
        Args:
            zoom_level: Target zoom level (0.1 to 8.0)
            center: Point to zoom around (default: current view center)
            animated: Whether to animate the transition
            
        Returns:
            bool: True if zoom operation started successfully
        """
        # Validate zoom level
        zoom_level = self._clamp_zoom(zoom_level)
        
        if zoom_level == self.current_zoom:
            return True
            
        # Set zoom center
        if center is None:
            center = self._get_view_center()
        self.zoom_center = center
        
        if animated and abs(zoom_level - self.current_zoom) > 0.01:
            return self._start_animated_zoom(zoom_level)
        else:
            return self._set_zoom_immediate(zoom_level)
    
    def zoom_in(self, steps: int = 1, center: Optional[QPointF] = None) -> bool:
        """Zoom in by specified steps using exponential progression."""
        new_zoom = self.current_zoom * (self.zoom_factor ** steps)
        return self.zoom_to_level(new_zoom, center)
    
    def zoom_out(self, steps: int = 1, center: Optional[QPointF] = None) -> bool:
        """Zoom out by specified steps using exponential progression."""
        new_zoom = self.current_zoom / (self.zoom_factor ** steps)
        return self.zoom_to_level(new_zoom, center)
    
    def zoom_to_fit(self, content_size: Tuple[float, float], 
                   view_size: Tuple[float, float]) -> bool:
        """Calculate and apply zoom to fit content in view."""
        content_w, content_h = content_size
        view_w, view_h = view_size
        
        # Calculate zoom to fit both dimensions
        zoom_w = view_w / content_w
        zoom_h = view_h / content_h
        zoom_fit = min(zoom_w, zoom_h) * 0.95  # 5% padding
        
        return self.zoom_to_level(zoom_fit)
    
    def _clamp_zoom(self, zoom_level: float) -> float:
        """Ensure zoom level is within valid bounds."""
        return max(self.min_zoom, min(self.max_zoom, zoom_level))
    
    def _start_animated_zoom(self, target_zoom: float) -> bool:
        """Start smooth animated zoom transition."""
        if self.is_zooming:
            self.animation_timer.stop()
            
        self.target_zoom = target_zoom
        self.is_zooming = True
        self.zoom_started.emit()
        
        # Start animation timer
        interval = 1000 // self.animation_fps  # ms per frame
        self.animation_timer.start(interval)
        return True
    
    def _animate_zoom(self):
        """Animation frame callback for smooth zoom transitions."""
        if not self.is_zooming:
            return
            
        # Calculate animation progress (exponential easing)
        progress = self._calculate_animation_progress()
        
        if progress >= 1.0:
            # Animation complete
            self.current_zoom = self.target_zoom
            self._finish_zoom_animation()
        else:
            # Interpolate zoom level with easing
            start_zoom = self.current_zoom
            zoom_diff = self.target_zoom - start_zoom
            eased_progress = self._ease_out_cubic(progress)
            self.current_zoom = start_zoom + (zoom_diff * eased_progress)
        
        # Emit zoom change
        self.zoom_changed.emit(self.current_zoom)
    
    def _ease_out_cubic(self, t: float) -> float:
        """Cubic easing out function for smooth animation."""
        return 1 - pow(1 - t, 3)
    
    def get_transform_matrix(self) -> QTransform:
        """Get current zoom transformation matrix."""
        transform = QTransform()
        
        # Apply zoom around center point
        transform.translate(self.zoom_center.x(), self.zoom_center.y())
        transform.scale(self.current_zoom, self.current_zoom)
        transform.translate(-self.zoom_center.x(), -self.zoom_center.y())
        
        return transform
```

### 2. Animation Framework (`animation.py`)
```python
from typing import Callable, Optional
from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtOpenGL import QOpenGLWidget
import time

class AnimationEngine(QObject):
    """
    GPU-accelerated animation framework for smooth transitions.
    Provides high-performance animation with proper frame timing.
    """
    
    frame_update = pyqtSignal(float)  # progress (0.0 to 1.0)
    animation_finished = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Animation configuration
        self.target_fps = 60
        self.frame_interval = 1000 // self.target_fps  # ms
        
        # Animation state
        self.is_animating = False
        self.start_time = 0.0
        self.duration = 300  # ms
        self.progress = 0.0
        
        # Timer for animation frames
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_frame)
        
        # Performance monitoring
        self.frame_count = 0
        self.dropped_frames = 0
        
    def start_animation(self, duration_ms: int = 300) -> bool:
        """
        Start animation with specified duration.
        
        Args:
            duration_ms: Animation duration in milliseconds
            
        Returns:
            bool: True if animation started successfully
        """
        if self.is_animating:
            self.stop_animation()
            
        self.duration = duration_ms
        self.start_time = time.time() * 1000  # Convert to ms
        self.is_animating = True
        self.progress = 0.0
        self.frame_count = 0
        self.dropped_frames = 0
        
        # Start high-frequency timer
        self.timer.start(self.frame_interval)
        return True
    
    def stop_animation(self):
        """Stop current animation immediately."""
        if self.is_animating:
            self.timer.stop()
            self.is_animating = False
            self.animation_finished.emit()
    
    def _update_frame(self):
        """Update animation frame with performance monitoring."""
        if not self.is_animating:
            return
            
        current_time = time.time() * 1000
        elapsed = current_time - self.start_time
        self.progress = min(elapsed / self.duration, 1.0)
        
        # Monitor frame performance
        self.frame_count += 1
        expected_frames = elapsed / self.frame_interval
        if self.frame_count < expected_frames * 0.9:  # 10% tolerance
            self.dropped_frames += 1
        
        # Emit frame update
        self.frame_update.emit(self.progress)
        
        # Check if animation complete
        if self.progress >= 1.0:
            self.stop_animation()
    
    def get_performance_stats(self) -> dict:
        """Get animation performance statistics."""
        return {
            'frame_count': self.frame_count,
            'dropped_frames': self.dropped_frames,
            'drop_rate': self.dropped_frames / max(self.frame_count, 1),
            'target_fps': self.target_fps
        }
```

## 🧪 Testing Requirements (MANDATORY >95% Coverage)

### Main Test File (`test_zoom.py`)
```python
import pytest
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QTransform
from unittest.mock import Mock, patch
import time

from torematrix.ui.viewer.controls.zoom import ZoomEngine

class TestZoomEngine:
    """Comprehensive tests for the core zoom engine."""
    
    @pytest.fixture
    def zoom_engine(self):
        """Create a ZoomEngine instance for testing."""
        engine = ZoomEngine()
        yield engine
        engine.deleteLater()
    
    def test_initialization(self, zoom_engine):
        """Test zoom engine initializes with correct defaults."""
        assert zoom_engine.current_zoom == 1.0
        assert zoom_engine.min_zoom == 0.1
        assert zoom_engine.max_zoom == 8.0
        assert zoom_engine.zoom_factor == 1.2
        assert not zoom_engine.is_zooming
    
    def test_zoom_to_level_immediate(self, zoom_engine):
        """Test immediate zoom to specific level."""
        # Test valid zoom level
        result = zoom_engine.zoom_to_level(2.0, animated=False)
        assert result is True
        assert zoom_engine.current_zoom == 2.0
        
        # Test zoom level clamping
        zoom_engine.zoom_to_level(10.0, animated=False)  # Above max
        assert zoom_engine.current_zoom == zoom_engine.max_zoom
        
        zoom_engine.zoom_to_level(0.05, animated=False)  # Below min
        assert zoom_engine.current_zoom == zoom_engine.min_zoom
    
    def test_zoom_in_progression(self, zoom_engine):
        """Test zoom in with exponential progression."""
        initial_zoom = zoom_engine.current_zoom
        
        # Single step zoom in
        zoom_engine.zoom_in(1, animated=False)
        expected_zoom = initial_zoom * zoom_engine.zoom_factor
        assert abs(zoom_engine.current_zoom - expected_zoom) < 0.001
        
        # Multiple step zoom in
        zoom_engine.current_zoom = 1.0  # Reset
        zoom_engine.zoom_in(3, animated=False)
        expected_zoom = initial_zoom * (zoom_engine.zoom_factor ** 3)
        assert abs(zoom_engine.current_zoom - expected_zoom) < 0.001
    
    def test_zoom_out_progression(self, zoom_engine):
        """Test zoom out with exponential progression."""
        zoom_engine.current_zoom = 2.0  # Start zoomed in
        initial_zoom = zoom_engine.current_zoom
        
        # Single step zoom out
        zoom_engine.zoom_out(1, animated=False)
        expected_zoom = initial_zoom / zoom_engine.zoom_factor
        assert abs(zoom_engine.current_zoom - expected_zoom) < 0.001
    
    def test_zoom_to_fit_calculation(self, zoom_engine):
        """Test zoom to fit calculations."""
        # Content larger than view
        content_size = (1000, 800)
        view_size = (500, 400)
        
        zoom_engine.zoom_to_fit(content_size, view_size)
        
        # Should fit the smaller dimension with padding
        expected_zoom = min(500/1000, 400/800) * 0.95
        assert abs(zoom_engine.current_zoom - expected_zoom) < 0.01
    
    def test_animated_zoom_signals(self, zoom_engine, qtbot):
        """Test zoom animation signals are emitted correctly."""
        with qtbot.waitSignal(zoom_engine.zoom_started, timeout=1000):
            zoom_engine.zoom_to_level(2.0, animated=True)
        
        assert zoom_engine.is_zooming is True
        
        # Wait for animation to complete
        with qtbot.waitSignal(zoom_engine.zoom_finished, timeout=1000):
            pass
        
        assert zoom_engine.is_zooming is False
        assert abs(zoom_engine.current_zoom - 2.0) < 0.01
    
    def test_transform_matrix_calculation(self, zoom_engine):
        """Test transformation matrix calculations."""
        zoom_engine.current_zoom = 2.0
        zoom_engine.zoom_center = QPointF(100, 100)
        
        transform = zoom_engine.get_transform_matrix()
        
        # Verify transform maintains zoom center
        center_transformed = transform.map(QPointF(100, 100))
        expected_center = QPointF(100, 100)  # Should remain at center
        
        # Allow small floating point differences
        assert abs(center_transformed.x() - expected_center.x()) < 0.1
        assert abs(center_transformed.y() - expected_center.y()) < 0.1
    
    def test_performance_requirements(self, zoom_engine):
        """Test zoom operations meet performance requirements."""
        # Test zoom operation timing
        start_time = time.time()
        
        for _ in range(100):
            zoom_engine.zoom_to_level(1.5, animated=False)
            zoom_engine.zoom_to_level(1.0, animated=False)
        
        elapsed = time.time() - start_time
        avg_time_per_op = elapsed / 200  # 200 operations total
        
        # Should complete in under 1ms per operation
        assert avg_time_per_op < 0.001
    
    def test_thread_safety(self, zoom_engine):
        """Test zoom engine is thread-safe for concurrent operations."""
        import threading
        import time
        
        results = []
        errors = []
        
        def zoom_worker(zoom_level):
            try:
                result = zoom_engine.zoom_to_level(zoom_level, animated=False)
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=zoom_worker, args=(1.0 + i * 0.1,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify no errors and all operations successful
        assert len(errors) == 0
        assert len(results) == 10
        assert all(results)
```

## 📊 Performance Requirements

### Benchmarks You Must Meet
- **Zoom Operations**: Complete in <16ms (60fps requirement)
- **Memory Usage**: <50MB for zoom calculations
- **CPU Usage**: <15% during zoom animations
- **Frame Rate**: Maintain 60fps during smooth zoom transitions
- **Thread Safety**: Support concurrent zoom operations without conflicts

### Performance Test Implementation
```python
def test_performance_benchmarks(zoom_engine):
    """Verify all performance requirements are met."""
    
    # Test zoom operation timing
    times = []
    for _ in range(100):
        start = time.perf_counter()
        zoom_engine.zoom_to_level(2.0, animated=False)
        end = time.perf_counter()
        times.append((end - start) * 1000)  # Convert to ms
    
    avg_time = sum(times) / len(times)
    assert avg_time < 16.0, f"Zoom operations too slow: {avg_time}ms"
    
    # Test memory usage (implementation specific)
    # Test CPU usage during animation (implementation specific)
```

## 🔗 Integration Points

### Dependencies You Need
- **Layout Management System** (Issue #13) - ✅ COMPLETED
- **Event Bus System** - ✅ COMPLETED  
- **PyQt6** - For UI framework and GPU acceleration

### What You Provide to Other Agents
- **ZoomEngine class** - Core zoom functionality
- **AnimationEngine class** - GPU-accelerated animations
- **Zoom transformation matrices** - For coordinate calculations
- **Performance monitoring** - Frame rate and optimization metrics

### Integration APIs You Must Provide
```python
# For Agent 2 (Pan Controls)
def get_current_zoom_level() -> float
def get_zoom_transform() -> QTransform
def is_zoom_animation_active() -> bool

# For Agent 3 (Navigation UI)
def set_zoom_constraints(min_zoom: float, max_zoom: float)
def get_zoom_presets() -> List[float]
def register_zoom_callback(callback: Callable[[float], None])

# For Agent 4 (Integration)
def get_performance_metrics() -> dict
def reset_zoom_state()
def export_zoom_configuration() -> dict
```

## 🚀 GitHub Workflow

### Branch Management
```bash
# Create your unique branch
git checkout main
git pull origin main
git checkout -b feature/zoom-engine-agent1-issue201

# Work on your implementation
git add -A
git commit -m "🚀 FEATURE: Core Zoom Engine Implementation

Implemented foundational zoom engine with GPU-accelerated animations

## Core Features:
- ✅ Exponential zoom scaling with precision calculations
- ✅ GPU-accelerated smooth animations at 60fps
- ✅ Point-based zoom with accurate transformations
- ✅ Thread-safe zoom operations
- ✅ Performance optimized for large documents

## Technical Implementation:
- ZoomEngine class with signal-based architecture
- AnimationEngine with high-performance frame timing
- Comprehensive zoom constraints and validation
- Transform matrix calculations for coordinate mapping

## Testing:
- 45+ tests across 3 test files
- >95% code coverage achieved
- Performance benchmarks verified
- Thread safety confirmed

Fixes #[sub-issue-number]

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# Push and create PR
git push -u origin feature/zoom-engine-agent1-issue201
gh pr create --title "🚀 FEATURE: Core Zoom Engine & Animation Framework (#[sub-issue-number])" --body "[Detailed PR description]"
```

## ✅ Definition of Done

### Your work is complete when:
- [ ] ✅ All zoom engine functionality implemented and tested
- [ ] ✅ GPU-accelerated animations working at 60fps
- [ ] ✅ >95% test coverage across all your files
- [ ] ✅ Performance benchmarks met (documented in tests)
- [ ] ✅ Thread safety verified with concurrent operation tests
- [ ] ✅ Integration APIs provided for other agents
- [ ] ✅ All tests passing in CI/CD pipeline
- [ ] ✅ Pull request created and ready for review
- [ ] ✅ Sub-issue closed with completion summary

## 🎯 Success Metrics
- **Performance**: 60fps zoom animations consistently
- **Accuracy**: Sub-pixel precision in zoom calculations
- **Reliability**: Zero crashes under stress testing
- **Integration**: Clean APIs for other agents to build upon

You are the foundation that makes the entire zoom/pan system possible. Build it well! 🚀