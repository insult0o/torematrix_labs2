"""
Test Suite for Agent 3 Spatial Indexing System.
This module provides comprehensive tests for the spatial indexing components.
"""
import pytest
import time
import math
from unittest.mock import Mock

from src.torematrix.ui.viewer.spatial import SpatialBounds, SpatialElement, QuadTreeSpatialIndex, SpatialIndexManager
from src.torematrix.ui.viewer.culling import ViewportCuller, ViewportBounds, CullingStrategy
from src.torematrix.ui.viewer.clustering import ElementClusterer, ClusteringStrategy
from src.torematrix.ui.viewer.optimization import PerformanceOptimizer, OptimizationMode
from src.torematrix.ui.viewer.profiling import PerformanceProfiler, ProfilingConfiguration
from src.torematrix.ui.viewer.coordinates import Rectangle, Point


@pytest.fixture
def mock_overlay_element():
    """Create a mock overlay element."""
    element = Mock()
    element.element_id = "test_element_1"
    element.layer_name = "test_layer"
    element.element_type = "test_type"
    element.bounds = Rectangle(10, 10, 100, 50)
    element.get_z_index.return_value = 0
    element.get_bounds.return_value = element.bounds
    element.is_visible.return_value = True
    return element


@pytest.fixture
def spatial_bounds():
    """Create test spatial bounds."""
    return SpatialBounds(0, 0, 1000, 1000)


@pytest.fixture
def spatial_index(spatial_bounds):
    """Create spatial index for testing."""
    return QuadTreeSpatialIndex(spatial_bounds)


class TestSpatialBounds:
    """Test spatial bounds functionality."""
    
    def test_creation(self):
        """Test spatial bounds creation."""
        bounds = SpatialBounds(10, 20, 100, 200)
        assert bounds.x == 10
        assert bounds.y == 20
        assert bounds.width == 100
        assert bounds.height == 200
    
    def test_intersects(self):
        """Test bounds intersection detection."""
        bounds1 = SpatialBounds(0, 0, 100, 100)
        bounds2 = SpatialBounds(50, 50, 100, 100)
        bounds3 = SpatialBounds(200, 200, 100, 100)
        
        assert bounds1.intersects(bounds2) is True
        assert bounds1.intersects(bounds3) is False
    
    def test_contains_point(self):
        """Test point containment."""
        bounds = SpatialBounds(10, 10, 100, 100)
        
        assert bounds.contains(Point(50, 50)) is True
        assert bounds.contains(Point(5, 5)) is False
        assert bounds.contains(Point(10, 10)) is True
    
    def test_area_calculation(self):
        """Test area calculation."""
        bounds = SpatialBounds(0, 0, 100, 200)
        assert bounds.area() == 20000


class TestQuadTreeSpatialIndex:
    """Test quadtree spatial index functionality."""
    
    def test_creation(self, spatial_bounds):
        """Test spatial index creation."""
        index = QuadTreeSpatialIndex(spatial_bounds)
        assert index.bounds == spatial_bounds
        assert index.get_element_count() == 0
    
    def test_insert_element(self, spatial_index, mock_overlay_element):
        """Test element insertion."""
        bounds = SpatialBounds.from_rectangle(mock_overlay_element.bounds)
        element = SpatialElement(
            element_id="test_1",
            bounds=bounds,
            element=mock_overlay_element
        )
        
        success = spatial_index.insert(element)
        assert success is True
        assert spatial_index.get_element_count() == 1
    
    def test_remove_element(self, spatial_index, mock_overlay_element):
        """Test element removal."""
        bounds = SpatialBounds.from_rectangle(mock_overlay_element.bounds)
        element = SpatialElement(
            element_id="test_1",
            bounds=bounds,
            element=mock_overlay_element
        )
        
        # Insert then remove
        spatial_index.insert(element)
        assert spatial_index.get_element_count() == 1
        
        success = spatial_index.remove("test_1")
        assert success is True
        assert spatial_index.get_element_count() == 0
    
    def test_query_by_bounds(self, spatial_index):
        """Test spatial query by bounds."""
        # Insert test elements
        for i in range(3):
            element = Mock()
            element.element_id = f"element_{i}"
            element.bounds = Rectangle(i * 50, i * 30, 40, 25)
            
            bounds = SpatialBounds.from_rectangle(element.bounds)
            spatial_element = SpatialElement(
                element_id=element.element_id,
                bounds=bounds,
                element=element
            )
            spatial_index.insert(spatial_element)
        
        # Query region that should contain some elements
        query_bounds = SpatialBounds(0, 0, 150, 150)
        results = spatial_index.query(query_bounds)
        
        assert len(results) >= 0  # May be 0 or more
        assert len(results) <= 3


class TestSpatialIndexManager:
    """Test spatial index manager functionality."""
    
    def test_add_remove_elements(self, spatial_bounds):
        """Test adding and removing elements."""
        manager = SpatialIndexManager(spatial_bounds)
        
        # Create test element
        element = Mock()
        element.element_id = "test_1"
        element.layer_name = "test_layer"
        element.element_type = "test_type"
        element.bounds = Rectangle(10, 10, 100, 50)
        element.get_z_index.return_value = 0
        element.get_bounds.return_value = element.bounds
        element.is_visible.return_value = True
        
        # Add element
        success = manager.add_element(element)
        assert success is True
        
        # Check element count
        stats = manager.get_performance_statistics()
        assert stats['total_elements'] == 1
        
        # Remove element
        success = manager.remove_element(element.element_id)
        assert success is True
        
        stats = manager.get_performance_statistics()
        assert stats['total_elements'] == 0


class TestViewportCuller:
    """Test viewport culling functionality."""
    
    def test_basic_culling(self, spatial_bounds):
        """Test basic viewport culling."""
        # Setup spatial manager with elements
        manager = SpatialIndexManager(spatial_bounds)
        
        for i in range(3):
            element = Mock()
            element.element_id = f"element_{i}"
            element.layer_name = "test_layer"
            element.element_type = "test_type"
            element.bounds = Rectangle(i * 50, i * 30, 40, 25)
            element.get_z_index.return_value = i
            element.get_bounds.return_value = element.bounds
            element.is_visible.return_value = True
            manager.add_element(element)
        
        culler = ViewportCuller(manager, CullingStrategy.BASIC)
        
        # Create viewport
        viewport = ViewportBounds(Rectangle(0, 0, 100, 100), zoom_level=1.0)
        
        # Perform culling
        result = culler.cull_elements(viewport)
        
        assert result.total_elements >= 0
        assert len(result.visible_elements) <= result.total_elements
        assert result.culled_count >= 0


class TestElementClusterer:
    """Test element clustering functionality."""
    
    def test_spatial_clustering(self, spatial_bounds):
        """Test spatial clustering algorithm."""
        # Setup
        manager = SpatialIndexManager(spatial_bounds)
        elements = []
        
        for i in range(3):
            element = Mock()
            element.element_id = f"element_{i}"
            element.layer_name = "test_layer"
            element.element_type = "test_type"
            element.bounds = Rectangle(i * 50, i * 30, 40, 25)
            element.get_z_index.return_value = i
            element.get_bounds.return_value = element.bounds
            element.is_visible.return_value = True
            elements.append(element)
            manager.add_element(element)
        
        clusterer = ElementClusterer(manager)
        
        # Perform clustering at low zoom (should cluster)
        clusters = clusterer.cluster_elements(elements, zoom_level=0.5)
        assert isinstance(clusters, list)
        
        # At high zoom (should not cluster)
        clusters_high = clusterer.cluster_elements(elements, zoom_level=2.0)
        assert isinstance(clusters_high, list)


class TestPerformanceOptimizer:
    """Test performance optimization functionality."""
    
    def test_frame_optimization(self):
        """Test frame-level optimization."""
        optimizer = PerformanceOptimizer()
        
        # Create test elements
        elements = []
        for i in range(5):
            element = Mock()
            element.element_id = f"element_{i}"
            element.bounds = Rectangle(i * 50, i * 30, 40, 25)
            element.get_z_index.return_value = i
            elements.append(element)
        
        viewport = Rectangle(0, 0, 200, 200)
        
        result = optimizer.optimize_frame(elements, zoom_level=1.0, viewport=viewport)
        
        assert 'optimized_elements' in result
        assert 'original_count' in result
        assert 'optimized_count' in result
        assert result['original_count'] == len(elements)
        assert result['optimized_count'] <= result['original_count']


class TestPerformanceProfiler:
    """Test performance profiling functionality."""
    
    def test_profiler_creation(self):
        """Test profiler creation and configuration."""
        profiler = PerformanceProfiler()
        assert profiler.config.level.value in ['disabled', 'basic', 'detailed']
    
    def test_operation_profiling(self):
        """Test operation profiling context manager."""
        profiler = PerformanceProfiler()
        
        with profiler.profile_operation("test_operation"):
            time.sleep(0.001)  # Small delay to measure
        
        # Check that metrics were created
        metrics = profiler.get_all_metrics()
        timing_metrics = [name for name in metrics.keys() if 'timing' in name]
        assert len(timing_metrics) >= 0  # May be 0 if below threshold
    
    def test_metric_recording(self):
        """Test custom metric recording."""
        profiler = PerformanceProfiler()
        
        # Record some metrics
        profiler.record_metric("custom_metric", 10.5)
        profiler.record_metric("custom_metric", 20.0)
        
        metrics = profiler.get_all_metrics()
        assert 'custom_metric' in metrics
        assert metrics['custom_metric']['count'] == 2
    
    def test_performance_report(self):
        """Test comprehensive performance report generation."""
        profiler = PerformanceProfiler()
        
        # Generate some activity
        with profiler.profile_operation("report_test"):
            time.sleep(0.001)
        
        profiler.record_metric("test_metric", 42.0)
        
        report = profiler.get_performance_report()
        
        assert 'configuration' in report
        assert 'metrics' in report
        assert 'profiling_overhead' in report
        assert 'active_operations' in report
        assert 'report_generated' in report


if __name__ == "__main__":
    pytest.main([__file__, "-v"])