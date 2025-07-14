"""
Debug visualization and validation for coordinate mapping system.

This module provides comprehensive debugging tools, coordinate validation,
and visual debugging overlays for the multi-page coordinate system.
"""

from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
import time
import math

try:
    from PyQt6.QtCore import QObject, pyqtSignal
    from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QFont
    from PyQt6.QtWidgets import QWidget
    PyQt6_available = True
except ImportError:
    class QObject:
        pass
    def pyqtSignal(*args):
        return None
    class QPainter:
        pass
    class QWidget:
        pass
    PyQt6_available = False

from .coordinates import CoordinateMapper
from .multipage import MultiPageCoordinateSystem


@dataclass
class DebugInfo:
    """Debug information for coordinate mapping."""
    coordinate_points: List[Tuple['Point', str]]  # (point, label)
    transformation_matrices: Dict[str, str]  # transformation_name -> matrix_string
    performance_metrics: Dict[str, float]
    page_boundaries: List['Rect']
    coordinate_spaces: List[str]


class CoordinateDebugger(QObject):
    """Debug visualization for coordinate mapping system."""
    
    # Signals
    debug_info_updated = pyqtSignal(DebugInfo) if PyQt6_available else None
    
    def __init__(self, multipage_system: MultiPageCoordinateSystem):
        if PyQt6_available:
            super().__init__()
        self.multipage_system = multipage_system
        self._debug_enabled = False
        self._debug_info = DebugInfo([], {}, {}, [], [])
        self._performance_monitor = PerformanceMonitor()
        
    def enable_debug(self, enabled: bool):
        """Enable or disable debug visualization."""
        self._debug_enabled = enabled
        if enabled:
            self._update_debug_info()
            
    def is_debug_enabled(self) -> bool:
        """Check if debug is enabled."""
        return self._debug_enabled
        
    def add_debug_point(self, point: 'Point', label: str):
        """Add a debug point to visualize."""
        if self._debug_enabled:
            self._debug_info.coordinate_points.append((point, label))
            self._update_debug_info()
            
    def clear_debug_points(self):
        """Clear all debug points."""
        self._debug_info.coordinate_points.clear()
        self._update_debug_info()
        
    def draw_debug_overlay(self, painter: QPainter, widget: QWidget):
        """Draw debug overlay on widget."""
        if not self._debug_enabled or not PyQt6_available:
            return
            
        # Set up painter
        painter.save()
        
        # Draw coordinate grid
        self._draw_coordinate_grid(painter, widget)
        
        # Draw page boundaries
        self._draw_page_boundaries(painter)
        
        # Draw debug points
        self._draw_debug_points(painter)
        
        # Draw transformation info
        self._draw_transformation_info(painter, widget)
        
        # Draw performance metrics
        self._draw_performance_metrics(painter, widget)
        
        painter.restore()
        
    def get_debug_info(self) -> DebugInfo:
        """Get current debug information."""
        return self._debug_info
        
    def log_coordinate_transformation(self, from_point: 'Point', to_point: 'Point', 
                                    transformation_name: str):
        """Log a coordinate transformation for debugging."""
        if self._debug_enabled:
            print(f"Transform {transformation_name}: {from_point} -> {to_point}")
            
    def validate_coordinate_accuracy(self, expected: 'Point', actual: 'Point', 
                                   tolerance: float = 0.01) -> bool:
        """Validate coordinate transformation accuracy."""
        distance = expected.distance_to(actual)
        is_accurate = distance <= tolerance
        
        if not is_accurate and self._debug_enabled:
            print(f"Coordinate accuracy warning: expected {expected}, got {actual}, "
                  f"distance {distance}, tolerance {tolerance}")
                  
        return is_accurate
        
    def benchmark_transformation_performance(self, transform_func, points: List['Point'], 
                                           iterations: int = 1000) -> Dict[str, float]:
        """Benchmark coordinate transformation performance."""
        return self._performance_monitor.benchmark_function(
            transform_func, points, iterations
        )
        
    def _update_debug_info(self):
        """Update debug information."""
        if not self._debug_enabled:
            return
            
        # Update page boundaries
        self._debug_info.page_boundaries.clear()
        for page_num in range(self.multipage_system.get_page_count()):
            bounds = self.multipage_system.get_page_bounds(page_num)
            if bounds:
                self._debug_info.page_boundaries.append(bounds)
                
        # Update coordinate spaces
        self._debug_info.coordinate_spaces = [
            f"Page {i}" for i in range(self.multipage_system.get_page_count())
        ]
        
        # Update performance metrics
        self._debug_info.performance_metrics = self._performance_monitor.get_metrics()
        
        if self.debug_info_updated and PyQt6_available:
            self.debug_info_updated.emit(self._debug_info)
        
    def _draw_coordinate_grid(self, painter: QPainter, widget: QWidget):
        """Draw coordinate grid."""
        if not PyQt6_available:
            return
            
        grid_color = QColor(100, 100, 100, 100)
        grid_pen = QPen(grid_color, 1)
        painter.setPen(grid_pen)
        
        # Draw grid lines every 50 pixels
        grid_spacing = 50
        
        for x in range(0, widget.width(), grid_spacing):
            painter.drawLine(x, 0, x, widget.height())
            
        for y in range(0, widget.height(), grid_spacing):
            painter.drawLine(0, y, widget.width(), y)
            
    def _draw_page_boundaries(self, painter: QPainter):
        """Draw page boundaries."""
        if not PyQt6_available:
            return
            
        boundary_color = QColor(255, 0, 0, 150)
        boundary_pen = QPen(boundary_color, 2)
        painter.setPen(boundary_pen)
        
        for rect in self._debug_info.page_boundaries:
            painter.drawRect(int(rect.x), int(rect.y), 
                           int(rect.width), int(rect.height))
            
    def _draw_debug_points(self, painter: QPainter):
        """Draw debug points."""
        if not PyQt6_available:
            return
            
        point_color = QColor(0, 255, 0, 200)
        point_brush = QBrush(point_color)
        painter.setBrush(point_brush)
        
        text_color = QColor(0, 0, 0, 255)
        text_pen = QPen(text_color)
        painter.setPen(text_pen)
        
        font = QFont("Arial", 8)
        painter.setFont(font)
        
        for point, label in self._debug_info.coordinate_points:
            # Draw point
            painter.drawEllipse(int(point.x - 3), int(point.y - 3), 6, 6)
            
            # Draw label
            painter.drawText(int(point.x + 5), int(point.y - 5), label)
            
    def _draw_transformation_info(self, painter: QPainter, widget: QWidget):
        """Draw transformation information."""
        if not PyQt6_available or not self._debug_info.transformation_matrices:
            return
            
        text_color = QColor(0, 0, 0, 200)
        text_pen = QPen(text_color)
        painter.setPen(text_pen)
        
        font = QFont("Courier", 8)
        painter.setFont(font)
        
        y_offset = 20
        for name, matrix_str in self._debug_info.transformation_matrices.items():
            painter.drawText(10, y_offset, f"{name}: {matrix_str}")
            y_offset += 15
            
    def _draw_performance_metrics(self, painter: QPainter, widget: QWidget):
        """Draw performance metrics."""
        if not PyQt6_available or not self._debug_info.performance_metrics:
            return
            
        text_color = QColor(0, 0, 255, 200)
        text_pen = QPen(text_color)
        painter.setPen(text_pen)
        
        font = QFont("Arial", 8)
        painter.setFont(font)
        
        y_offset = widget.height() - 80
        for metric, value in self._debug_info.performance_metrics.items():
            painter.drawText(10, y_offset, f"{metric}: {value:.2f}")
            y_offset += 15


class CoordinateValidator:
    """Validates coordinate transformations for correctness."""
    
    def __init__(self, multipage_system: MultiPageCoordinateSystem):
        self.multipage_system = multipage_system
        self._validation_enabled = True
        self._validation_tolerance = 0.01
        self._validation_history: List[Dict[str, Any]] = []
        
    def enable_validation(self, enabled: bool):
        """Enable or disable coordinate validation."""
        self._validation_enabled = enabled
        
    def set_tolerance(self, tolerance: float):
        """Set validation tolerance."""
        self._validation_tolerance = tolerance
        
    def validate_round_trip(self, point: 'Point', page_number: int) -> bool:
        """Validate round-trip coordinate transformation."""
        if not self._validation_enabled:
            return True
            
        start_time = time.time()
        
        # Document -> Viewer -> Document
        viewer_point = self.multipage_system.document_to_viewer(point, page_number)
        if not viewer_point:
            self._log_validation_failure("document_to_viewer returned None", point, page_number)
            return False
            
        back_to_document = self.multipage_system.viewer_to_document(viewer_point, page_number)
        if not back_to_document:
            self._log_validation_failure("viewer_to_document returned None", point, page_number)
            return False
            
        # Check if we got back to the original point
        distance = point.distance_to(back_to_document)
        is_valid = distance <= self._validation_tolerance
        
        # Log validation result
        validation_time = time.time() - start_time
        self._log_validation_result(
            "round_trip", point, page_number, is_valid, distance, validation_time
        )
        
        return is_valid
        
    def validate_coordinate_consistency(self) -> Dict[str, bool]:
        """Validate coordinate system consistency."""
        results = {}
        
        # Test points for validation
        test_points = [
            Point(0, 0), Point(100, 100), Point(500, 300),
            Point(-50, 200), Point(1000, 1000)
        ]
        
        for page_num in range(self.multipage_system.get_page_count()):
            for i, point in enumerate(test_points):
                test_name = f"page_{page_num}_point_{i}"
                results[test_name] = self.validate_round_trip(point, page_num)
                
        return results
        
    def validate_page_boundaries(self) -> Dict[str, bool]:
        """Validate page boundary calculations."""
        results = {}
        
        for page_num in range(self.multipage_system.get_page_count()):
            bounds = self.multipage_system.get_page_bounds(page_num)
            
            # Check if bounds are valid
            if bounds:
                valid_bounds = (bounds.width > 0 and bounds.height > 0 and
                              bounds.x >= 0 and bounds.y >= 0)
                results[f"page_{page_num}_bounds"] = valid_bounds
            else:
                results[f"page_{page_num}_bounds"] = False
                
        return results
        
    def validate_layout_modes(self) -> Dict[str, bool]:
        """Validate different layout modes."""
        results = {}
        original_mode = self.multipage_system.get_layout_mode()
        
        for mode in ['single', 'continuous', 'spread']:
            try:
                self.multipage_system.set_layout_mode(mode)
                
                # Check if layout is valid
                total_size = self.multipage_system.get_total_document_size()
                valid_layout = total_size.width >= 0 and total_size.height >= 0
                
                results[f"layout_{mode}"] = valid_layout
                
            except Exception as e:
                print(f"Layout mode {mode} validation failed: {e}")
                results[f"layout_{mode}"] = False
                
        # Restore original mode
        self.multipage_system.set_layout_mode(original_mode)
        
        return results
        
    def run_validation_suite(self) -> Dict[str, Any]:
        """Run complete validation suite."""
        suite_start = time.time()
        
        results = {
            'round_trip_tests': self.validate_coordinate_consistency(),
            'page_boundary_tests': self.validate_page_boundaries(),
            'layout_mode_tests': self.validate_layout_modes(),
            'tolerance': self._validation_tolerance,
            'enabled': self._validation_enabled,
            'test_timestamp': suite_start
        }
        
        # Calculate summary statistics
        total_tests = 0
        passed_tests = 0
        
        for test_category in ['round_trip_tests', 'page_boundary_tests', 'layout_mode_tests']:
            if test_category in results:
                for test_result in results[test_category].values():
                    total_tests += 1
                    if test_result:
                        passed_tests += 1
        
        results['summary'] = {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': total_tests - passed_tests,
            'pass_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            'suite_duration': time.time() - suite_start
        }
        
        return results
        
    def _log_validation_failure(self, reason: str, point: 'Point', page_number: int):
        """Log validation failure."""
        if self._validation_enabled:
            print(f"Validation failure: {reason} for point {point} on page {page_number}")
            
    def _log_validation_result(self, test_type: str, point: 'Point', page_number: int,
                             is_valid: bool, distance: float, duration: float):
        """Log validation result."""
        result = {
            'test_type': test_type,
            'point': {'x': point.x, 'y': point.y},
            'page_number': page_number,
            'is_valid': is_valid,
            'distance': distance,
            'duration': duration,
            'timestamp': time.time()
        }
        
        self._validation_history.append(result)
        
        # Limit history size
        if len(self._validation_history) > 1000:
            self._validation_history.pop(0)


class PerformanceMonitor:
    """Monitors coordinate transformation performance."""
    
    def __init__(self):
        self._metrics: Dict[str, float] = {}
        self._history: List[Dict[str, float]] = []
        self._benchmarks: Dict[str, List[float]] = {}
        
    def start_timing(self, operation_name: str) -> float:
        """Start timing an operation."""
        start_time = time.time()
        self._metrics[f"{operation_name}_start"] = start_time
        return start_time
        
    def end_timing(self, operation_name: str) -> float:
        """End timing an operation and record duration."""
        end_time = time.time()
        start_time = self._metrics.get(f"{operation_name}_start", end_time)
        duration = end_time - start_time
        
        self._metrics[f"{operation_name}_duration"] = duration
        self._record_benchmark(operation_name, duration)
        
        return duration
        
    def record_metric(self, name: str, value: float):
        """Record a performance metric."""
        self._metrics[name] = value
        
    def get_metrics(self) -> Dict[str, float]:
        """Get current performance metrics."""
        return self._metrics.copy()
        
    def benchmark_function(self, func, args: List[Any], iterations: int = 1000) -> Dict[str, float]:
        """Benchmark a function with given arguments."""
        durations = []
        
        for _ in range(iterations):
            start_time = time.time()
            try:
                func(*args)
                end_time = time.time()
                durations.append((end_time - start_time) * 1000)  # Convert to ms
            except Exception as e:
                print(f"Benchmark error: {e}")
                continue
                
        if not durations:
            return {'error': 'No successful iterations'}
            
        return {
            'min_ms': min(durations),
            'max_ms': max(durations),
            'avg_ms': sum(durations) / len(durations),
            'median_ms': sorted(durations)[len(durations) // 2],
            'iterations': len(durations),
            'total_time_ms': sum(durations)
        }
        
    def _record_benchmark(self, operation_name: str, duration: float):
        """Record benchmark data."""
        if operation_name not in self._benchmarks:
            self._benchmarks[operation_name] = []
            
        self._benchmarks[operation_name].append(duration)
        
        # Limit benchmark history
        if len(self._benchmarks[operation_name]) > 1000:
            self._benchmarks[operation_name].pop(0)


# Import geometry classes to support type hints
try:
    from ..utils.geometry import Point, Rect, Size
except ImportError:
    # Fallback classes for testing environment
    @dataclass
    class Point:
        x: float
        y: float
        
        def distance_to(self, other: 'Point') -> float:
            return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)
    
    @dataclass 
    class Rect:
        x: float
        y: float
        width: float
        height: float
        
        @property
        def center(self) -> Point:
            return Point(self.x + self.width / 2, self.y + self.height / 2)
        
        def contains(self, point: Point) -> bool:
            return (self.x <= point.x <= self.x + self.width and
                    self.y <= point.y <= self.y + self.height)
        
        def intersects(self, other: 'Rect') -> bool:
            return not (self.x + self.width < other.x or
                       other.x + other.width < self.x or
                       self.y + self.height < other.y or
                       other.y + other.height < self.y)
    
    @dataclass
    class Size:
        width: float
        height: float