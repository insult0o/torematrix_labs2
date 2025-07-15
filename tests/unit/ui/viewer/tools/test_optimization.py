"""
Comprehensive tests for selection tool optimization features.
Tests hit testing, snapping, persistence, history, and manager systems.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from typing import List

from PyQt6.QtCore import QObject, QPointF, QRectF
from PyQt6.QtGui import QPainter

from src.torematrix.ui.viewer.coordinates import Point, Rectangle
from src.torematrix.ui.viewer.layers import LayerElement
from src.torematrix.ui.viewer.tools.base import SelectionResult, ToolState
from src.torematrix.ui.viewer.tools.hit_testing import (
    SpatialIndex, QuadTreeNode, HitTestOptimizer, HitTestResult
)
from src.torematrix.ui.viewer.tools.snapping import (
    MagneticSnapping, SnapType, SnapPoint, SnapResult, SnapSettings
)
from src.torematrix.ui.viewer.tools.persistence import (
    SelectionPersistence, SelectionSnapshot, PersistenceScope, ViewState
)
from src.torematrix.ui.viewer.tools.history import (
    SelectionHistory, HistoryAction, HistoryActionType, HistoryBranch
)
from src.torematrix.ui.viewer.tools.manager import (
    SelectionToolManager, ToolRegistration, ToolPriority, ToolContext
)


class MockLayerElement:
    """Mock layer element for testing."""
    
    def __init__(self, element_id: str, bounds: Rectangle):
        self.id = element_id
        self.bounds = bounds
    
    def get_id(self) -> str:
        return self.id
    
    def get_bounds(self) -> Rectangle:
        return self.bounds


class MockSelectionTool:
    """Mock selection tool for testing."""
    
    def __init__(self, name: str):
        self.name = name
        self.state = ToolState.INACTIVE
        self.enabled = True
        self.visible = True
        self._config = {}
        self._metrics = {}
        
        # Mock signals
        self.selection_changed = Mock()
        self.error_occurred = Mock()
        self.state_changed = Mock()
        self.cursor_changed = Mock()
        self.preview_changed = Mock()
    
    def activate(self):
        self.state = ToolState.ACTIVE
    
    def deactivate(self):
        self.state = ToolState.INACTIVE
    
    def get_config(self, key: str):
        return self._config.get(key)
    
    def set_config(self, key: str, value):
        self._config[key] = value
    
    def get_metrics(self):
        return self._metrics.copy()
    
    def handle_mouse_press(self, point, modifiers):
        return True
    
    def handle_mouse_move(self, point, modifiers):
        return True
    
    def handle_mouse_release(self, point, modifiers):
        return True
    
    def render_overlay(self, painter, viewport_rect):
        pass


class TestSpatialIndex:
    """Test spatial indexing for hit testing optimization."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.bounds = Rectangle(0, 0, 1000, 1000)
        self.spatial_index = SpatialIndex(self.bounds)
        
        # Create test elements
        self.elements = [
            MockLayerElement("elem1", Rectangle(10, 10, 50, 50)),
            MockLayerElement("elem2", Rectangle(100, 100, 50, 50)),
            MockLayerElement("elem3", Rectangle(200, 200, 50, 50)),
            MockLayerElement("elem4", Rectangle(300, 300, 50, 50)),
            MockLayerElement("elem5", Rectangle(400, 400, 50, 50))
        ]
        
        # Add elements to index
        for element in self.elements:
            self.spatial_index.add_element(element)
    
    def test_spatial_index_creation(self):
        """Test spatial index creation."""
        assert self.spatial_index.quad_tree is not None
        assert len(self.spatial_index.element_cache) == 5
    
    def test_point_query(self):
        """Test point-based queries."""
        # Query point inside first element
        point = Point(35, 35)
        results = self.spatial_index.query_point(point, tolerance=5)
        
        assert len(results) == 1
        assert results[0].id == "elem1"
    
    def test_rectangle_query(self):
        """Test rectangle-based queries."""
        # Query rectangle that overlaps multiple elements
        query_bounds = Rectangle(0, 0, 150, 150)
        results = self.spatial_index.query_rectangle(query_bounds)
        
        assert len(results) >= 2
        element_ids = [e.id for e in results]
        assert "elem1" in element_ids
        assert "elem2" in element_ids
    
    def test_nearest_elements(self):
        """Test nearest element search."""
        point = Point(125, 125)  # Between elem2 and elem3
        results = self.spatial_index.nearest_elements(point, max_count=3)
        
        assert len(results) <= 3
        assert all(isinstance(r, HitTestResult) for r in results)
        
        # Results should be sorted by distance
        for i in range(1, len(results)):
            assert results[i-1].distance <= results[i].distance
    
    def test_performance_metrics(self):
        """Test performance metrics collection."""
        # Perform some queries
        for i in range(10):
            point = Point(i * 50, i * 50)
            self.spatial_index.query_point(point)
        
        metrics = self.spatial_index.get_performance_metrics()
        
        assert metrics['query_count'] >= 10
        assert metrics['avg_query_time'] >= 0
        assert metrics['element_count'] == 5
        assert 'meets_target' in metrics
    
    def test_element_updates(self):
        """Test element updates and removals."""
        # Update element
        updated_element = MockLayerElement("elem1", Rectangle(500, 500, 50, 50))
        self.spatial_index.update_element(updated_element)
        
        # Query old location
        old_point = Point(35, 35)
        old_results = self.spatial_index.query_point(old_point, tolerance=5)
        assert len(old_results) == 0
        
        # Query new location
        new_point = Point(525, 525)
        new_results = self.spatial_index.query_point(new_point, tolerance=5)
        assert len(new_results) == 1
        assert new_results[0].id == "elem1"
        
        # Remove element
        self.spatial_index.remove_element("elem2")
        assert "elem2" not in self.spatial_index.element_cache


class TestQuadTree:
    """Test QuadTree implementation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.bounds = Rectangle(0, 0, 100, 100)
        self.quad_tree = QuadTreeNode(self.bounds, max_depth=4, max_elements=2)
    
    def test_quad_tree_insertion(self):
        """Test element insertion."""
        element = MockLayerElement("test", Rectangle(10, 10, 20, 20))
        
        result = self.quad_tree.insert(element)
        assert result is True
        assert len(self.quad_tree.elements) == 1
    
    def test_quad_tree_subdivision(self):
        """Test automatic subdivision."""
        # Add enough elements to trigger subdivision
        elements = [
            MockLayerElement("e1", Rectangle(5, 5, 10, 10)),
            MockLayerElement("e2", Rectangle(15, 15, 10, 10)),
            MockLayerElement("e3", Rectangle(25, 25, 10, 10))
        ]
        
        for element in elements:
            self.quad_tree.insert(element)
        
        # Should trigger subdivision
        assert not self.quad_tree.is_leaf
        assert len(self.quad_tree.children) == 4
    
    def test_quad_tree_query(self):
        """Test quad tree queries."""
        # Insert elements
        elements = [
            MockLayerElement("e1", Rectangle(10, 10, 10, 10)),
            MockLayerElement("e2", Rectangle(80, 80, 10, 10))
        ]
        
        for element in elements:
            self.quad_tree.insert(element)
        
        # Query first quadrant
        query_bounds = Rectangle(0, 0, 50, 50)
        results = self.quad_tree.query(query_bounds)
        
        assert len(results) == 1
        assert results[0].id == "e1"
    
    def test_quad_tree_statistics(self):
        """Test quad tree statistics."""
        # Add some elements
        for i in range(5):
            element = MockLayerElement(f"e{i}", Rectangle(i*10, i*10, 5, 5))
            self.quad_tree.insert(element)
        
        stats = self.quad_tree.get_statistics()
        
        assert 'total_elements' in stats
        assert 'depth' in stats
        assert 'is_leaf' in stats
        assert stats['total_elements'] >= 5


class TestMagneticSnapping:
    """Test magnetic snapping system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.spatial_index = SpatialIndex()
        self.snapping = MagneticSnapping(self.spatial_index)
        
        # Add test elements
        self.elements = [
            MockLayerElement("snap1", Rectangle(100, 100, 50, 50)),
            MockLayerElement("snap2", Rectangle(200, 200, 50, 50))
        ]
        
        for element in self.elements:
            self.spatial_index.add_element(element)
        
        # Set document bounds
        self.snapping.set_document_bounds(Rectangle(0, 0, 500, 500))
    
    def test_snap_settings(self):
        """Test snap settings configuration."""
        settings = self.snapping.settings
        
        assert settings.element_snap_distance > 0
        assert settings.grid_snap_distance > 0
        assert SnapType.ELEMENT_EDGE in settings.enabled_types
        
        # Test distance calculation
        distance = settings.get_snap_distance(SnapType.ELEMENT_EDGE)
        assert distance == settings.element_snap_distance
    
    def test_grid_snapping(self):
        """Test grid point snapping."""
        # Enable grid snapping
        self.snapping.settings.grid_enabled = True
        self.snapping.settings.grid_size = 20
        
        # Test point near grid
        point = Point(22, 22)  # Close to (20, 20) grid point
        result = self.snapping.snap_point(point)
        
        assert result.snapped is True
        assert result.snapped_point.x == 20
        assert result.snapped_point.y == 20
    
    def test_element_snapping(self):
        """Test element edge snapping."""
        # Point near element edge
        point = Point(98, 125)  # Close to left edge of first element (x=100)
        result = self.snapping.snap_point(point)
        
        assert result.snapped is True
        assert abs(result.snapped_point.x - 100) < 1  # Snapped to edge
    
    def test_guide_lines(self):
        """Test guide line snapping."""
        # Add guide lines
        self.snapping.add_guide_line(150, horizontal=True)  # Horizontal at y=150
        self.snapping.add_guide_line(250, horizontal=False)  # Vertical at x=250
        
        # Test horizontal guide snap
        point = Point(300, 148)  # Close to horizontal guide
        result = self.snapping.snap_point(point)
        
        assert result.snapped is True
        assert abs(result.snapped_point.y - 150) < 1
    
    def test_snap_candidates(self):
        """Test snap candidate generation."""
        point = Point(125, 125)  # Between elements
        candidates = self.snapping.get_snap_candidates(point, radius=50)
        
        assert len(candidates) > 0
        assert all(isinstance(c, SnapPoint) for c in candidates)
    
    def test_performance_metrics(self):
        """Test snapping performance tracking."""
        # Perform several snap operations
        for i in range(10):
            point = Point(100 + i, 100 + i)
            self.snapping.snap_point(point)
        
        metrics = self.snapping.get_performance_metrics()
        
        assert metrics['snap_operations'] >= 10
        assert metrics['average_snap_time'] >= 0


class TestSelectionPersistence:
    """Test selection persistence system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.persistence = SelectionPersistence()
        
        # Create test selection
        self.test_elements = [
            MockLayerElement("persist1", Rectangle(10, 10, 50, 50)),
            MockLayerElement("persist2", Rectangle(100, 100, 50, 50))
        ]
        
        self.test_selection = SelectionResult(
            elements=self.test_elements,
            geometry=Rectangle(10, 10, 140, 140),
            tool_type="test_tool"
        )
    
    def test_save_selection(self):
        """Test selection saving."""
        result = self.persistence.save_selection(
            "test_selection",
            self.test_selection,
            scope=PersistenceScope.SESSION
        )
        
        assert result is True
        
        # Check that selection was saved
        selections = self.persistence.list_selections(PersistenceScope.SESSION)
        assert len(selections) == 1
        assert selections[0].selection_id == "test_selection"
    
    def test_restore_selection(self):
        """Test selection restoration."""
        # Save selection first
        self.persistence.save_selection("restore_test", self.test_selection)
        
        # Restore selection
        restored = self.persistence.restore_selection("restore_test", validate_elements=False)
        
        assert restored is not None
        assert restored.tool_type == "test_tool"
        assert len(restored.elements) == 2
    
    def test_persistence_scopes(self):
        """Test different persistence scopes."""
        # Save selections in different scopes
        self.persistence.save_selection("session", self.test_selection, PersistenceScope.SESSION)
        self.persistence.save_selection("document", self.test_selection, PersistenceScope.DOCUMENT)
        self.persistence.save_selection("global", self.test_selection, PersistenceScope.GLOBAL)
        
        # Check scope isolation
        session_selections = self.persistence.list_selections(PersistenceScope.SESSION)
        document_selections = self.persistence.list_selections(PersistenceScope.DOCUMENT)
        global_selections = self.persistence.list_selections(PersistenceScope.GLOBAL)
        
        assert len(session_selections) == 1
        assert len(document_selections) == 1
        assert len(global_selections) == 1
    
    def test_view_state_tracking(self):
        """Test view state compatibility."""
        view_state = ViewState(
            zoom_level=1.5,
            pan_offset=Point(100, 100),
            viewport_bounds=Rectangle(0, 0, 800, 600),
            document_bounds=Rectangle(0, 0, 1000, 1000)
        )
        
        self.persistence.update_view_state(view_state)
        
        # Save selection with current view state
        self.persistence.save_selection("view_test", self.test_selection)
        
        # Should restore successfully with compatible view
        restored = self.persistence.restore_selection("view_test", validate_view=True)
        assert restored is not None
    
    def test_export_import(self):
        """Test selection export/import."""
        # Save multiple selections
        for i in range(3):
            selection_id = f"export_test_{i}"
            self.persistence.save_selection(selection_id, self.test_selection)
        
        # Export selections
        exported_data = self.persistence.export_selections(PersistenceScope.SESSION)
        assert exported_data
        
        # Clear and import
        self.persistence.clear_scope(PersistenceScope.SESSION)
        imported_count = self.persistence.import_selections(exported_data, PersistenceScope.SESSION)
        
        assert imported_count == 3
    
    def test_optimization(self):
        """Test persistence optimization."""
        # Create many selections to test cleanup
        for i in range(20):
            selection_id = f"optimize_test_{i}"
            self.persistence.save_selection(selection_id, self.test_selection)
        
        # Run optimization
        results = self.persistence.optimize()
        
        assert 'expired_removed' in results
        assert 'duplicates_removed' in results
        assert 'orphaned_removed' in results


class TestSelectionHistory:
    """Test selection history and undo/redo system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.history = SelectionHistory()
        
        # Test selection states
        self.state1 = SelectionResult(
            elements=[MockLayerElement("hist1", Rectangle(10, 10, 50, 50))],
            tool_type="test_tool"
        )
        
        self.state2 = SelectionResult(
            elements=[MockLayerElement("hist2", Rectangle(100, 100, 50, 50))],
            tool_type="test_tool"
        )
    
    def test_record_action(self):
        """Test action recording."""
        result = self.history.record_action(
            HistoryActionType.SELECT,
            "Test selection",
            before_state=None,
            after_state=self.state1
        )
        
        assert result is True
        
        # Finalize pending action
        self.history.finalize_pending_action()
        
        # Check history
        history_list = self.history.get_history_list()
        assert len(history_list) >= 1
    
    def test_undo_redo(self):
        """Test undo/redo operations."""
        # Record multiple actions
        self.history.record_action(
            HistoryActionType.SELECT,
            "First selection",
            before_state=None,
            after_state=self.state1
        )
        self.history.finalize_pending_action()
        
        self.history.record_action(
            HistoryActionType.MODIFY_SELECTION,
            "Second selection",
            before_state=self.state1,
            after_state=self.state2
        )
        self.history.finalize_pending_action()
        
        # Test undo
        assert self.history.can_undo()
        undone_state = self.history.undo()
        assert undone_state is not None
        
        # Test redo
        assert self.history.can_redo()
        redone_state = self.history.redo()
        assert redone_state is not None
    
    def test_action_compression(self):
        """Test action compression."""
        # Enable compression
        self.history.update_config(compress_actions=True)
        
        # Record similar actions quickly
        for i in range(5):
            self.history.record_action(
                HistoryActionType.MODIFY_SELECTION,
                f"Modification {i}",
                before_state=self.state1,
                after_state=self.state2
            )
        
        self.history.finalize_pending_action()
        
        # Should have compressed actions
        metrics = self.history.get_statistics()
        assert metrics['metrics']['compressed_actions'] > 0
    
    def test_memory_optimization(self):
        """Test memory optimization."""
        # Record many actions
        for i in range(50):
            self.history.record_action(
                HistoryActionType.SELECT,
                f"Selection {i}",
                after_state=self.state1
            )
            self.history.finalize_pending_action()
        
        # Check memory usage
        memory_info = self.history.get_memory_usage()
        assert memory_info['total_actions'] > 0
        
        # Optimize
        results = self.history.optimize_memory()
        assert 'actions_removed' in results
    
    def test_branching(self):
        """Test history branching."""
        # Record initial action
        self.history.record_action(
            HistoryActionType.SELECT,
            "Initial selection",
            after_state=self.state1
        )
        self.history.finalize_pending_action()
        
        # Create branch
        branch_id = self.history.create_branch("Test branch")
        assert branch_id
        
        # Switch to branch
        result = self.history.switch_branch(branch_id)
        assert result is True
        
        # Get branches
        branches = self.history.get_branches()
        assert len(branches) >= 1


class TestSelectionToolManager:
    """Test selection tool manager."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.spatial_index = SpatialIndex()
        self.manager = SelectionToolManager(self.spatial_index)
        
        # Create test tools
        self.tool1 = MockSelectionTool("tool1")
        self.tool2 = MockSelectionTool("tool2")
    
    def test_tool_registration(self):
        """Test tool registration."""
        result = self.manager.register_tool(
            "test_tool1",
            self.tool1,
            priority=ToolPriority.HIGH,
            shortcuts=["Ctrl+1"]
        )
        
        assert result is True
        assert "test_tool1" in self.manager.list_tools()
        
        # Test duplicate registration
        duplicate_result = self.manager.register_tool("test_tool1", self.tool1)
        assert duplicate_result is False
    
    def test_tool_activation(self):
        """Test tool activation."""
        # Register tool
        self.manager.register_tool("activate_test", self.tool1)
        
        # Activate tool
        result = self.manager.activate_tool("activate_test")
        assert result is True
        assert self.manager.get_active_tool_name() == "activate_test"
        assert self.tool1.state == ToolState.ACTIVE
    
    def test_tool_switching(self):
        """Test tool switching."""
        # Register multiple tools
        self.manager.register_tool("switch_tool1", self.tool1)
        self.manager.register_tool("switch_tool2", self.tool2)
        
        # Activate first tool
        self.manager.activate_tool("switch_tool1")
        assert self.tool1.state == ToolState.ACTIVE
        
        # Switch to second tool
        self.manager.activate_tool("switch_tool2")
        assert self.tool1.state == ToolState.INACTIVE
        assert self.tool2.state == ToolState.ACTIVE
    
    def test_tool_shortcuts(self):
        """Test keyboard shortcuts."""
        # Register tool with shortcut
        self.manager.register_tool(
            "shortcut_tool",
            self.tool1,
            shortcuts=["Ctrl+T"]
        )
        
        # Handle shortcut
        result = self.manager.handle_shortcut("Ctrl+T")
        assert result is True
        assert self.manager.get_active_tool_name() == "shortcut_tool"
    
    def test_context_based_tool_suggestion(self):
        """Test context-based tool suggestions."""
        # Register tools with different priorities
        self.manager.register_tool("low_priority", self.tool1, ToolPriority.LOW)
        self.manager.register_tool("high_priority", self.tool2, ToolPriority.HIGH)
        
        # Create context
        context = ToolContext(
            mouse_position=Point(100, 100),
            zoom_level=1.0,
            selected_elements=[]
        )
        
        # Get suggestion
        suggested_tool = self.manager.suggest_tool(context)
        assert suggested_tool == "high_priority"  # Higher priority should be suggested
    
    def test_analytics(self):
        """Test analytics collection."""
        # Register and use tools
        self.manager.register_tool("analytics_tool", self.tool1)
        self.manager.activate_tool("analytics_tool")
        
        # Simulate tool usage
        self.tool1.selection_changed.emit(SelectionResult())
        
        # Get analytics
        analytics = self.manager.get_analytics()
        
        assert 'tool_usage' in analytics
        assert 'analytics_tool' in analytics['tool_usage']
        assert analytics['tool_usage']['analytics_tool']['activation_count'] > 0
    
    def test_configuration_export_import(self):
        """Test configuration export/import."""
        # Register tools with configuration
        self.manager.register_tool("config_tool", self.tool1, ToolPriority.HIGH)
        
        # Export configuration
        config = self.manager.export_configuration()
        assert 'tools' in config
        assert 'config_tool' in config['tools']
        
        # Modify and import
        config['tools']['config_tool']['enabled'] = False
        result = self.manager.import_configuration(config)
        assert result is True
    
    def test_performance_monitoring(self):
        """Test performance monitoring."""
        # Register tool
        self.manager.register_tool("perf_tool", self.tool1)
        self.manager.activate_tool("perf_tool")
        
        # Set up mock metrics
        self.tool1._metrics = {
            'average_operation_time': 150  # Above warning threshold
        }
        
        # Trigger performance monitoring
        self.manager._monitor_performance()
        
        # Should have recorded performance data
        analytics = self.manager.get_analytics()
        assert 'performance_data' in analytics
    
    @patch('PyQt6.QtGui.QPainter')
    def test_overlay_rendering(self, mock_painter):
        """Test overlay rendering."""
        # Register tool
        self.manager.register_tool("render_tool", self.tool1)
        
        # Mock viewport
        viewport_rect = Mock()
        
        # Render overlays
        self.manager.render_overlays(mock_painter, viewport_rect)
        
        # Tool's render_overlay should have been called
        # (We can't easily verify this with our mock, but the method should execute without error)


class TestIntegration:
    """Integration tests for optimization systems."""
    
    def setup_method(self):
        """Set up integrated test environment."""
        self.spatial_index = SpatialIndex()
        self.manager = SelectionToolManager(self.spatial_index)
        
        # Add test elements
        self.elements = [
            MockLayerElement("int1", Rectangle(10, 10, 50, 50)),
            MockLayerElement("int2", Rectangle(100, 100, 50, 50)),
            MockLayerElement("int3", Rectangle(200, 200, 50, 50))
        ]
        
        for element in self.elements:
            self.spatial_index.add_element(element)
    
    def test_full_workflow(self):
        """Test complete selection workflow with all optimizations."""
        # Register tool
        tool = MockSelectionTool("workflow_tool")
        self.manager.register_tool("workflow_tool", tool)
        
        # Activate tool
        self.manager.activate_tool("workflow_tool")
        
        # Create selection
        selection = SelectionResult(
            elements=self.elements[:2],
            geometry=Rectangle(10, 10, 140, 140),
            tool_type="workflow_tool"
        )
        
        # Simulate selection change
        tool.selection_changed.emit(selection)
        
        # Verify history recording
        assert self.manager.history.can_undo()
        
        # Verify persistence
        persistence_stats = self.manager.persistence.get_statistics()
        assert persistence_stats['session_count'] > 0
        
        # Test undo
        undone = self.manager.history.undo()
        assert undone is not None
    
    def test_performance_optimization(self):
        """Test performance with large datasets."""
        # Add many elements
        large_elements = []
        for i in range(1000):
            element = MockLayerElement(f"perf_{i}", Rectangle(i % 100 * 10, i // 100 * 10, 5, 5))
            large_elements.append(element)
            self.spatial_index.add_element(element)
        
        # Perform many queries
        start_time = time.time()
        for i in range(100):
            point = Point(i * 5, i * 5)
            results = self.spatial_index.query_point(point, tolerance=10)
        
        end_time = time.time()
        total_time = (end_time - start_time) * 1000  # Convert to ms
        
        # Should complete in reasonable time
        assert total_time < 1000  # Less than 1 second for 100 queries
        
        # Check performance metrics
        metrics = self.spatial_index.get_performance_metrics()
        assert metrics['meets_target'] is True
    
    def test_memory_management(self):
        """Test memory management under load."""
        # Create many selections to test memory limits
        tool = MockSelectionTool("memory_tool")
        self.manager.register_tool("memory_tool", tool)
        self.manager.activate_tool("memory_tool")
        
        # Generate many selections
        for i in range(200):
            selection = SelectionResult(
                elements=[self.elements[i % len(self.elements)]],
                tool_type="memory_tool"
            )
            
            # Record in history
            self.manager.history.record_action(
                HistoryActionType.SELECT,
                f"Selection {i}",
                after_state=selection
            )
            self.manager.history.finalize_pending_action()
            
            # Save in persistence
            self.manager.persistence.save_selection(f"mem_test_{i}", selection)
        
        # Check memory usage
        history_memory = self.manager.history.get_memory_usage()
        persistence_stats = self.manager.persistence.get_statistics()
        
        # Memory should be managed within limits
        assert history_memory['estimated_size_mb'] < 100  # Should be under 100MB
        assert persistence_stats['session_count'] <= 100  # Should enforce limits


if __name__ == "__main__":
    pytest.main([__file__])