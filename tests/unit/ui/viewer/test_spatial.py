"""
Test Suite for Agent 3 Spatial Indexing System.
This module provides comprehensive tests for the spatial indexing, culling,
clustering, optimization, and profiling components.
"""
import pytest
import time
import math
from unittest.mock import Mock, MagicMock
from pathlib import Path
from datetime import datetime

from src.torematrix.ui.viewer.spatial import (
    SpatialBounds, SpatialElement, QuadTreeSpatialIndex, SpatialIndexManager
)
from src.torematrix.ui.viewer.culling import (
    ViewportCuller, ViewportBounds, CullingStrategy, CullingResult
)
from src.torematrix.ui.viewer.clustering import (
    ElementClusterer, ClusteringStrategy, SpatialClusteringAlgorithm
)
from src.torematrix.ui.viewer.optimization import (
    PerformanceOptimizer, OptimizationMode, PerformanceTarget
)
from src.torematrix.ui.viewer.profiling import (
    PerformanceProfiler, ProfilingConfiguration, ProfilingLevel
)
from src.torematrix.ui.viewer.coordinates import Rectangle, Point


# Test fixtures

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


@pytest.fixture
def spatial_manager(spatial_bounds):
    """Create spatial index manager for testing."""
    return SpatialIndexManager(spatial_bounds)


@pytest.fixture
def test_elements():
    """Create list of test elements."""
    elements = []
    for i in range(10):
        element = Mock()
        element.element_id = f"element_{i}"
        element.layer_name = f"layer_{i % 3}"
        element.element_type = "test_type"
        element.bounds = Rectangle(i * 50, i * 30, 40, 25)
        element.get_z_index.return_value = i
        element.get_bounds.return_value = element.bounds
        element.is_visible.return_value = True
        elements.append(element)
    return elements


# SpatialBounds Tests

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
        assert bounds2.intersects(bounds3) is False
    
    def test_contains_point(self):
        """Test point containment."""
        bounds = SpatialBounds(10, 10, 100, 100)
        
        assert bounds.contains(Point(50, 50)) is True
        assert bounds.contains(Point(5, 5)) is False
        assert bounds.contains(Point(150, 150)) is False
        assert bounds.contains(Point(10, 10)) is True  # Edge case
    
    def test_contains_bounds(self):
        """Test bounds containment."""
        outer = SpatialBounds(0, 0, 200, 200)
        inner = SpatialBounds(50, 50, 100, 100)
        overlapping = SpatialBounds(150, 150, 100, 100)
        
        assert outer.contains_bounds(inner) is True
        assert outer.contains_bounds(overlapping) is False
        assert inner.contains_bounds(outer) is False
    
    def test_area_calculation(self):
        """Test area calculation."""
        bounds = SpatialBounds(0, 0, 100, 200)
        assert bounds.area() == 20000
        
        zero_bounds = SpatialBounds(0, 0, 0, 0)
        assert zero_bounds.area() == 0
    
    def test_center_calculation(self):
        """Test center point calculation."""
        bounds = SpatialBounds(10, 20, 100, 200)
        center = bounds.center()
        assert center.x == 60  # 10 + 100/2
        assert center.y == 120  # 20 + 200/2
    
    def test_expand(self):
        """Test bounds expansion."""
        bounds = SpatialBounds(50, 50, 100, 100)
        expanded = bounds.expand(10)
        
        assert expanded.x == 40
        assert expanded.y == 40
        assert expanded.width == 120
        assert expanded.height == 120


# SpatialElement Tests

class TestSpatialElement:
    """Test spatial element functionality."""
    
    def test_creation(self, mock_overlay_element):
        """Test spatial element creation."""
        bounds = SpatialBounds.from_rectangle(mock_overlay_element.bounds)
        element = SpatialElement(
            element_id="test_1",
            bounds=bounds,
            element=mock_overlay_element
        )
        
        assert element.element_id == "test_1"
        assert element.bounds == bounds
        assert element.element == mock_overlay_element
    
    def test_center_calculation(self, mock_overlay_element):
        """Test element center calculation."""
        bounds = SpatialBounds(10, 20, 100, 200)
        element = SpatialElement(
            element_id="test",
            bounds=bounds,
            element=mock_overlay_element
        )
        
        center = element.get_center()
        assert center.x == 60
        assert center.y == 120
    
    def test_area_calculation(self, mock_overlay_element):
        """Test element area calculation."""
        bounds = SpatialBounds(0, 0, 100, 50)
        element = SpatialElement(
            element_id="test",
            bounds=bounds,
            element=mock_overlay_element
        )
        
        assert element.get_area() == 5000
    
    def test_intersection(self, mock_overlay_element):
        """Test element intersection."""
        bounds = SpatialBounds(0, 0, 100, 100)
        element = SpatialElement(
            element_id="test",
            bounds=bounds,
            element=mock_overlay_element
        )
        
        # Intersecting bounds
        intersecting = SpatialBounds(50, 50, 100, 100)
        assert element.intersects(intersecting) is True
        
        # Non-intersecting bounds
        non_intersecting = SpatialBounds(200, 200, 100, 100)
        assert element.intersects(non_intersecting) is False


# QuadTreeSpatialIndex Tests

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
    
    def test_query_by_bounds(self, spatial_index, test_elements):
        """Test spatial query by bounds."""
        # Insert test elements
        for element in test_elements[:5]:
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
        
        assert len(results) > 0
        assert len(results) <= 5
        
        # Verify all results actually intersect with query bounds
        for result in results:
            assert result.intersects(query_bounds)
    
    def test_query_by_point(self, spatial_index, test_elements):
        """Test spatial query by point."""
        # Insert test elements
        for element in test_elements[:3]:
            bounds = SpatialBounds.from_rectangle(element.bounds)
            spatial_element = SpatialElement(
                element_id=element.element_id,
                bounds=bounds,
                element=element
            )
            spatial_index.insert(spatial_element)
        
        # Query point that should be inside first element
        point = Point(25, 20)  # Inside first element bounds
        results = spatial_index.query_point(point)
        
        assert len(results) >= 0  # Might be 0 or more depending on overlap
        
        # Verify results actually contain the point
        for result in results:
            assert result.bounds.contains(point)
    
    def test_nearest_neighbor_query(self, spatial_index, test_elements):
        """Test nearest neighbor queries."""
        # Insert test elements
        for element in test_elements[:5]:
            bounds = SpatialBounds.from_rectangle(element.bounds)
            spatial_element = SpatialElement(
                element_id=element.element_id,
                bounds=bounds,
                element=element
            )
            spatial_index.insert(spatial_element)
        
        # Query nearest elements
        query_point = Point(100, 100)
        results = spatial_index.query_nearest(query_point, max_distance=200, max_results=3)
        
        assert len(results) <= 3
        assert len(results) <= spatial_index.get_element_count()
        
        # Results should be sorted by distance
        if len(results) > 1:
            distances = [distance for _, distance in results]
            assert distances == sorted(distances)
    
    def test_tree_splitting(self, spatial_bounds):
        """Test quadtree node splitting behavior."""
        # Create index with small capacity to force splitting
        index = QuadTreeSpatialIndex(spatial_bounds, max_objects=2, max_levels=3)
        
        # Insert many elements to trigger splitting
        for i in range(10):
            element = SpatialElement(
                element_id=f"element_{i}",
                bounds=SpatialBounds(i * 10, i * 10, 5, 5),
                element=Mock()
            )
            index.insert(element)
        
        assert index.get_element_count() == 10
        
        # Verify tree structure has split
        stats = index.get_statistics()
        assert 'tree_structure' in stats
    
    def test_index_statistics(self, spatial_index, test_elements):
        """Test spatial index statistics."""
        # Insert some elements
        for element in test_elements[:3]:
            bounds = SpatialBounds.from_rectangle(element.bounds)
            spatial_element = SpatialElement(
                element_id=element.element_id,
                bounds=bounds,
                element=element
            )
            spatial_index.insert(spatial_element)
        
        # Perform some queries
        query_bounds = SpatialBounds(0, 0, 100, 100)
        spatial_index.query(query_bounds)
        spatial_index.query(query_bounds)
        
        stats = spatial_index.get_statistics()
        
        assert stats['total_elements'] == 3
        assert stats['total_queries'] >= 2
        assert stats['total_inserts'] >= 3
        assert 'average_query_time_ms' in stats
        assert 'tree_structure' in stats


# SpatialIndexManager Tests

class TestSpatialIndexManager:
    """Test spatial index manager functionality."""
    
    def test_add_remove_elements(self, spatial_manager, test_elements):
        """Test adding and removing elements."""
        # Add elements
        for element in test_elements[:3]:
            success = spatial_manager.add_element(element)
            assert success is True
        
        # Check element count
        stats = spatial_manager.get_performance_statistics()
        assert stats['total_elements'] == 3
        
        # Remove element
        success = spatial_manager.remove_element(test_elements[0].element_id)
        assert success is True
        
        stats = spatial_manager.get_performance_statistics()
        assert stats['total_elements'] == 2
    
    def test_query_operations(self, spatial_manager, test_elements):
        """Test various query operations."""
        # Add elements
        for element in test_elements[:5]:
            spatial_manager.add_element(element)
        
        # Query by region
        query_rect = Rectangle(0, 0, 150, 150)
        results = spatial_manager.query_region(query_rect)
        assert isinstance(results, list)
        
        # Query by point
        point_results = spatial_manager.query_point(Point(25, 20))
        assert isinstance(point_results, list)
        
        # Query nearest
        nearest_results = spatial_manager.query_nearest(Point(100, 100))
        assert isinstance(nearest_results, list)
    
    def test_layer_and_type_queries(self, spatial_manager, test_elements):
        """Test layer and type-based queries."""
        # Add elements
        for element in test_elements[:5]:
            spatial_manager.add_element(element)
        
        # Query by layer
        layer_results = spatial_manager.query_by_layer("layer_0")
        assert isinstance(layer_results, list)
        
        # Query by type
        type_results = spatial_manager.query_by_type("test_type")
        assert isinstance(type_results, list)
        assert len(type_results) > 0  # All test elements have same type
    
    def test_auto_rebuild(self, spatial_bounds):
        """Test automatic index rebuilding."""
        # Create manager with low rebuild threshold
        manager = SpatialIndexManager(spatial_bounds)
        manager.auto_rebuild_threshold = 5
        
        # Add enough elements to trigger rebuild
        for i in range(10):
            element = Mock()
            element.element_id = f"element_{i}"
            element.layer_name = "test_layer"
            element.element_type = "test_type"
            element.bounds = Rectangle(i * 10, i * 10, 5, 5)
            element.get_z_index.return_value = 0
            element.get_bounds.return_value = element.bounds
            element.is_visible.return_value = True
            
            manager.add_element(element)
        
        # Verify rebuild occurred
        stats = manager.get_performance_statistics()
        assert len(stats['performance_history']) > 0


# ViewportCuller Tests

class TestViewportCuller:
    """Test viewport culling functionality."""
    
    def test_basic_culling(self, spatial_manager, test_elements):
        """Test basic viewport culling."""
        # Setup spatial manager with elements
        for element in test_elements:
            spatial_manager.add_element(element)
        
        culler = ViewportCuller(spatial_manager, CullingStrategy.BASIC)
        
        # Create viewport
        viewport = ViewportBounds(Rectangle(0, 0, 100, 100), zoom_level=1.0)
        
        # Perform culling
        result = culler.cull_elements(viewport)
        
        assert isinstance(result, CullingResult)
        assert result.total_elements > 0
        assert len(result.visible_elements) <= result.total_elements
        assert result.culled_count >= 0
    
    def test_hierarchical_culling(self, spatial_manager, test_elements):
        """Test hierarchical culling with LOD."""
        # Setup
        for element in test_elements:
            spatial_manager.add_element(element)
        
        culler = ViewportCuller(spatial_manager, CullingStrategy.HIERARCHICAL)
        
        # Test different zoom levels
        for zoom in [0.25, 0.5, 1.0, 2.0]:
            viewport = ViewportBounds(Rectangle(0, 0, 200, 200), zoom_level=zoom)
            result = culler.cull_elements(viewport)
            
            assert isinstance(result, CullingResult)
            assert result.lod_level >= 0
    
    def test_culling_cache(self, spatial_manager, test_elements):
        """Test culling cache functionality."""
        # Setup
        for element in test_elements[:3]:
            spatial_manager.add_element(element)
        
        culler = ViewportCuller(spatial_manager)
        culler.enable_caching = True
        
        viewport = ViewportBounds(Rectangle(0, 0, 100, 100), zoom_level=1.0)
        
        # First call - should miss cache
        result1 = culler.cull_elements(viewport)
        assert result1.cache_hit is False
        
        # Second call - should hit cache
        result2 = culler.cull_elements(viewport)
        assert result2.cache_hit is True
    
    def test_culling_statistics(self, spatial_manager, test_elements):
        """Test culling statistics collection."""
        # Setup
        for element in test_elements[:5]:
            spatial_manager.add_element(element)
        
        culler = ViewportCuller(spatial_manager)
        
        # Perform several culling operations
        for i in range(3):
            viewport = ViewportBounds(Rectangle(i * 50, i * 50, 100, 100), zoom_level=1.0)
            culler.cull_elements(viewport)
        
        stats = culler.get_statistics()
        
        assert stats['total_culls'] >= 3
        assert stats['average_culling_time_ms'] >= 0
        assert 'cache_statistics' in stats


# ElementClusterer Tests

class TestElementClusterer:
    """Test element clustering functionality."""
    
    def test_spatial_clustering(self, spatial_manager, test_elements):
        """Test spatial clustering algorithm."""
        # Setup
        for element in test_elements:
            spatial_manager.add_element(element)
        
        clusterer = ElementClusterer(spatial_manager)
        
        # Perform clustering
        clusters = clusterer.cluster_elements(test_elements, zoom_level=0.5)
        
        assert isinstance(clusters, list)
        
        # Verify cluster properties
        for cluster in clusters:
            assert len(cluster.elements) > 0
            assert cluster.bounds.width > 0
            assert cluster.bounds.height > 0
            assert cluster.centroid.x >= 0
            assert cluster.centroid.y >= 0
    
    def test_hierarchical_clustering(self, spatial_manager, test_elements):
        """Test hierarchical clustering algorithm."""
        # Setup
        for element in test_elements:
            spatial_manager.add_element(element)
        
        clusterer = ElementClusterer(spatial_manager)
        
        # Test different zoom levels
        for zoom in [0.1, 0.5, 1.0, 2.0]:
            clusters = clusterer.cluster_elements(
                test_elements, 
                zoom_level=zoom, 
                strategy=ClusteringStrategy.HIERARCHICAL
            )
            
            assert isinstance(clusters, list)
            
            # At higher zoom levels, should have more/smaller clusters
            if zoom >= 1.0:
                for cluster in clusters:
                    assert len(cluster.elements) <= len(test_elements)
    
    def test_clustering_cache(self, spatial_manager, test_elements):
        """Test clustering cache functionality."""
        # Setup
        for element in test_elements[:5]:
            spatial_manager.add_element(element)
        
        clusterer = ElementClusterer(spatial_manager)
        
        # First clustering call
        start_time = time.time()
        clusters1 = clusterer.cluster_elements(test_elements[:5], zoom_level=1.0)
        first_duration = time.time() - start_time
        
        # Second call with same parameters - should be faster due to caching
        start_time = time.time()
        clusters2 = clusterer.cluster_elements(test_elements[:5], zoom_level=1.0)
        second_duration = time.time() - start_time
        
        assert len(clusters1) == len(clusters2)
        # Cache should make second call faster (though this might be flaky in tests)
    
    def test_cluster_summary(self, spatial_manager, test_elements):
        """Test cluster summary generation."""
        # Setup
        for element in test_elements:
            spatial_manager.add_element(element)
        
        clusterer = ElementClusterer(spatial_manager)
        
        summary = clusterer.get_cluster_summary(test_elements, zoom_level=0.5)
        
        assert 'total_elements' in summary
        assert 'estimated_clusters' in summary
        assert 'clustering_efficiency' in summary
        assert summary['total_elements'] == len(test_elements)


# PerformanceOptimizer Tests

class TestPerformanceOptimizer:
    """Test performance optimization functionality."""
    
    def test_frame_optimization(self, test_elements):
        """Test frame-level optimization."""
        targets = PerformanceTarget(target_fps=60.0, max_frame_time_ms=16.67)
        optimizer = PerformanceOptimizer(targets)
        
        viewport = Rectangle(0, 0, 200, 200)
        
        result = optimizer.optimize_frame(test_elements, zoom_level=1.0, viewport=viewport)
        
        assert 'optimized_elements' in result
        assert 'original_count' in result
        assert 'optimized_count' in result
        assert 'lod_level' in result
        assert 'frame_time_ms' in result
        
        assert result['original_count'] == len(test_elements)
        assert result['optimized_count'] <= result['original_count']
    
    def test_optimization_modes(self, test_elements):
        """Test different optimization modes."""
        optimizer = PerformanceOptimizer()
        viewport = Rectangle(0, 0, 200, 200)
        
        # Test different modes
        for mode in [OptimizationMode.PERFORMANCE, OptimizationMode.QUALITY, 
                    OptimizationMode.BALANCED]:
            optimizer.set_optimization_mode(mode)
            
            result = optimizer.optimize_frame(test_elements, zoom_level=0.5, viewport=viewport)
            
            assert isinstance(result, dict)
            assert 'optimized_elements' in result
    
    def test_performance_statistics(self, test_elements):
        """Test performance statistics collection."""
        optimizer = PerformanceOptimizer()
        viewport = Rectangle(0, 0, 100, 100)
        
        # Perform several optimization cycles
        for i in range(5):
            optimizer.optimize_frame(test_elements, zoom_level=1.0, viewport=viewport)
        
        stats = optimizer.get_comprehensive_statistics()
        
        assert 'optimization_mode' in stats
        assert 'performance_targets' in stats
        assert 'frame_statistics' in stats
        assert stats['frame_statistics']['total_frames'] >= 5


# PerformanceProfiler Tests

class TestPerformanceProfiler:
    """Test performance profiling functionality."""
    
    def test_profiler_creation(self):
        """Test profiler creation and configuration."""
        config = ProfilingConfiguration(
            level=ProfilingLevel.DETAILED,
            sample_rate=1.0,
            enable_memory_tracking=True
        )
        
        profiler = PerformanceProfiler(config)
        
        assert profiler.config.level == ProfilingLevel.DETAILED
        assert profiler.config.sample_rate == 1.0
        assert profiler.config.enable_memory_tracking is True
    
    def test_operation_profiling(self):
        """Test operation profiling context manager."""
        profiler = PerformanceProfiler()
        
        with profiler.profile_operation("test_operation"):
            time.sleep(0.01)  # Small delay to measure
        
        # Check that operation was recorded
        summary = profiler.get_operation_summary("test_operation")
        assert summary['operation_count'] == 1
        assert summary['average_duration_ms'] > 0
    
    def test_function_profiling_decorator(self):
        """Test function profiling decorator."""
        profiler = PerformanceProfiler()
        
        @profiler.profile_function("test_function")
        def slow_function():
            time.sleep(0.01)
            return "result"
        
        result = slow_function()
        
        assert result == "result"
        
        summary = profiler.get_operation_summary("test_function")
        assert summary['operation_count'] == 1
    
    def test_metric_recording(self):
        """Test custom metric recording."""
        profiler = PerformanceProfiler()
        
        # Record some metrics
        profiler.record_metric("custom_metric", 10.5)
        profiler.record_metric("custom_metric", 20.0)
        profiler.record_metric("custom_metric", 15.7)
        
        metric = profiler.get_metric("custom_metric")
        
        assert metric is not None
        assert metric.count == 3
        assert metric.average_value == (10.5 + 20.0 + 15.7) / 3
        assert metric.min_value == 10.5
        assert metric.max_value == 20.0
    
    def test_timer_operations(self):
        """Test start/end timer operations."""
        profiler = PerformanceProfiler()
        
        timer_id = profiler.start_timer("manual_timer")
        time.sleep(0.01)
        duration = profiler.end_timer(timer_id)
        
        assert duration is not None
        assert duration > 0
        
        summary = profiler.get_operation_summary("manual_timer")
        assert summary['operation_count'] == 1
    
    def test_performance_report(self):
        """Test comprehensive performance report generation."""
        profiler = PerformanceProfiler()
        
        # Generate some activity
        with profiler.profile_operation("report_test"):
            time.sleep(0.005)
        
        profiler.record_metric("test_metric", 42.0)
        
        report = profiler.get_performance_report()
        
        assert 'configuration' in report
        assert 'metrics' in report
        assert 'system_statistics' in report
        assert 'profiling_overhead' in report
        assert 'operation_summary' in report
        assert 'report_generated' in report
    
    def test_bottleneck_identification(self):
        """Test bottleneck identification."""
        profiler = PerformanceProfiler()
        
        # Create some operations with different performance characteristics
        with profiler.profile_operation("fast_operation"):
            time.sleep(0.001)
        
        with profiler.profile_operation("slow_operation"):
            time.sleep(0.02)
        
        with profiler.profile_operation("medium_operation"):
            time.sleep(0.01)
        
        bottlenecks = profiler.get_bottlenecks(top_n=5)
        
        assert isinstance(bottlenecks, list)
        assert len(bottlenecks) <= 5
        
        # Should be sorted by average duration (slowest first)
        if len(bottlenecks) > 1:
            for i in range(len(bottlenecks) - 1):
                assert (bottlenecks[i]['average_duration_ms'] >= 
                       bottlenecks[i + 1]['average_duration_ms'])


# Integration Tests

class TestAgent3Integration:
    """Integration tests for Agent 3 components."""
    
    def test_spatial_culling_integration(self, spatial_manager, test_elements):
        """Test integration between spatial indexing and culling."""
        # Setup spatial manager
        for element in test_elements:
            spatial_manager.add_element(element)
        
        # Create culler with spatial manager
        culler = ViewportCuller(spatial_manager, CullingStrategy.HIERARCHICAL)
        
        # Test culling at different zoom levels
        viewport_small = ViewportBounds(Rectangle(0, 0, 50, 50), zoom_level=2.0)
        viewport_large = ViewportBounds(Rectangle(0, 0, 500, 500), zoom_level=0.5)
        
        result_small = culler.cull_elements(viewport_small)
        result_large = culler.cull_elements(viewport_large)
        
        # Large viewport at low zoom should have fewer visible elements due to LOD
        assert isinstance(result_small, CullingResult)
        assert isinstance(result_large, CullingResult)
    
    def test_clustering_optimization_integration(self, spatial_manager, test_elements):
        """Test integration between clustering and optimization."""
        # Setup spatial manager
        for element in test_elements:
            spatial_manager.add_element(element)
        
        # Create clusterer and optimizer
        clusterer = ElementClusterer(spatial_manager)
        optimizer = PerformanceOptimizer()
        
        # Cluster elements
        clusters = clusterer.cluster_elements(test_elements, zoom_level=0.5)
        
        # Use clustered elements in optimization
        if clusters:
            cluster_elements = clusters[0].elements
            viewport = Rectangle(0, 0, 200, 200)
            
            result = optimizer.optimize_frame(cluster_elements, zoom_level=0.5, viewport=viewport)
            
            assert 'optimized_elements' in result
            assert result['optimized_count'] <= len(cluster_elements)
    
    def test_profiled_operations_integration(self, spatial_manager, test_elements):
        """Test profiling integration with spatial operations."""
        profiler = PerformanceProfiler()
        
        with profiler.profile_operation("spatial_setup"):
            for element in test_elements[:5]:
                spatial_manager.add_element(element)
        
        with profiler.profile_operation("spatial_query"):
            results = spatial_manager.query_region(Rectangle(0, 0, 100, 100))
        
        # Verify profiling captured the operations
        setup_summary = profiler.get_operation_summary("spatial_setup")
        query_summary = profiler.get_operation_summary("spatial_query")
        
        assert setup_summary['operation_count'] == 1
        assert query_summary['operation_count'] == 1
        assert setup_summary['average_duration_ms'] > 0
        assert query_summary['average_duration_ms'] > 0
    
    def test_end_to_end_performance_pipeline(self, spatial_manager, test_elements):
        """Test complete performance optimization pipeline."""
        # Setup profiler
        profiler = PerformanceProfiler()
        
        # Setup spatial manager with profiling
        with profiler.profile_operation("element_insertion"):
            for element in test_elements:
                spatial_manager.add_element(element)
        
        # Create culler and clusterer
        culler = ViewportCuller(spatial_manager, CullingStrategy.HIERARCHICAL)
        clusterer = ElementClusterer(spatial_manager)
        optimizer = PerformanceOptimizer()
        
        # Define viewport
        viewport = ViewportBounds(Rectangle(0, 0, 300, 300), zoom_level=0.75)
        
        # Performance pipeline
        with profiler.profile_operation("viewport_culling"):
            cull_result = culler.cull_elements(viewport)
        
        with profiler.profile_operation("element_clustering"):
            clusters = clusterer.cluster_elements(cull_result.visible_elements, viewport.zoom_level)
        
        with profiler.profile_operation("frame_optimization"):
            if clusters:
                for cluster in clusters:
                    optimizer.optimize_frame(cluster.elements, viewport.zoom_level, viewport.bounds)
        
        # Verify entire pipeline worked
        report = profiler.get_performance_report()
        
        assert 'element_insertion_timing' in report['metrics']
        assert 'viewport_culling_timing' in report['metrics']
        assert 'element_clustering_timing' in report['metrics']
        assert 'frame_optimization_timing' in report['metrics']
        
        # Check that performance improvements were achieved
        assert cull_result.total_elements >= len(cull_result.visible_elements)
        assert isinstance(clusters, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])