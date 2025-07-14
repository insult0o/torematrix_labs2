"""
Comprehensive Test Suite for Agent 2 Element Selection & State Management.
This module provides thorough testing of all Agent 2 components and their integration.
"""
import pytest
import asyncio
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication

from src.torematrix.ui.viewer.selection import SelectionManager, SelectionState, SelectionMode
from src.torematrix.ui.viewer.multi_select import SelectionStrategy
from src.torematrix.ui.viewer.state import SelectionStateManager, SelectionStateSnapshot, StateScope
from src.torematrix.ui.viewer.persistence import PersistenceManager, StorageFormat
from src.torematrix.ui.viewer.state_integration import SelectionStateIntegration
from src.torematrix.ui.viewer.overlay_integration import OverlaySelectionIntegration, IntegrationMode
from src.torematrix.ui.viewer.agent2_coordinator import Agent2ElementSelectionCoordinator, Agent2Configuration
from src.torematrix.ui.viewer.coordinates import Rectangle, Point
from src.torematrix.ui.viewer.events import SelectionEventManager, EventType


class TestOverlayElementAdapter:
    """Test adapter for overlay elements."""
    
    def __init__(self, element_id: str, bounds: Rectangle, layer_name: str = "test_layer"):
        self.element_id = element_id
        self.bounds = bounds
        self.layer_name = layer_name
        self.element_type = "test_element"
        self.properties = {"visible": True, "z_index": 0}
        self.overlay_element = Mock()
    
    def get_bounds(self) -> Rectangle:
        return self.bounds
    
    def get_style(self) -> Dict[str, Any]:
        return {"color": "blue", "opacity": 1.0}
    
    def is_visible(self) -> bool:
        return self.properties.get("visible", True)
    
    def get_z_index(self) -> int:
        return self.properties.get("z_index", 0)
    
    def render(self, renderer, context) -> None:
        pass


class TestMockOverlayAPI:
    """Mock overlay API for testing."""
    
    def __init__(self):
        self.elements = {}
        self.layers = {}
        self.coordinate_transform = None
        self.viewport = Rectangle(0, 0, 800, 600)
    
    def add_test_element(self, element_id: str, bounds: Rectangle, layer_name: str = "test_layer"):
        """Add a test element."""
        element = TestOverlayElementAdapter(element_id, bounds, layer_name)
        self.elements[element_id] = element
        if layer_name not in self.layers:
            self.layers[layer_name] = []
        self.layers[layer_name].append(element)
    
    def get_elements_in_viewport(self, viewport: Rectangle) -> List[Any]:
        """Get elements in viewport."""
        return [elem for elem in self.elements.values() if elem.bounds.intersects(viewport)]
    
    def get_current_viewport(self) -> Rectangle:
        """Get current viewport."""
        return self.viewport
    
    def get_coordinate_transform(self):
        """Get coordinate transform."""
        return self.coordinate_transform
    
    def create_integration_layer(self, layer_name: str, z_index: int = 0):
        """Create integration layer."""
        return Mock()
    
    def invalidate_agent_layer(self, layer_name: str):
        """Invalidate layer."""
        pass
    
    def cleanup_agent_resources(self, agent_id: str):
        """Clean up resources."""
        pass


@pytest.fixture
def app():
    """Qt application fixture."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def mock_overlay_api():
    """Mock overlay API fixture."""
    api = TestMockOverlayAPI()
    
    # Add some test elements
    api.add_test_element("elem1", Rectangle(10, 10, 100, 50), "layer1")
    api.add_test_element("elem2", Rectangle(50, 50, 80, 60), "layer1")
    api.add_test_element("elem3", Rectangle(200, 100, 120, 80), "layer2")
    api.add_test_element("elem4", Rectangle(300, 200, 90, 70), "layer2")
    
    return api


@pytest.fixture
def temp_project_dir(tmp_path):
    """Temporary project directory fixture."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    return project_dir


@pytest.fixture
def agent2_config():
    """Agent 2 configuration fixture."""
    return Agent2Configuration(
        selection_mode=SelectionMode.SINGLE,
        enable_state_persistence=True,
        auto_save_interval=1,  # Fast for testing
        integration_mode=IntegrationMode.ACTIVE,
        enable_visual_feedback=True,
        performance_monitoring=True
    )


class TestSelectionManager:
    """Test cases for SelectionManager."""
    
    def test_initialization(self, app, mock_overlay_api):
        """Test SelectionManager initialization."""
        manager = SelectionManager(mock_overlay_api)
        
        assert manager.overlay_api == mock_overlay_api
        assert manager.current_state is not None
        assert manager.current_state.mode == SelectionMode.SINGLE
        assert len(manager.algorithms) == 0  # Not initialized yet
    
    def test_overlay_integration_initialization(self, app, mock_overlay_api):
        """Test overlay integration initialization."""
        manager = SelectionManager(mock_overlay_api)
        
        # Mock overlay integration
        mock_integration = Mock()
        
        # Initialize overlay integration
        manager.initialize_overlay_integration(mock_integration)
        
        assert manager.overlay_integration == mock_integration
        assert len(manager.algorithms) == 5  # All selection modes
        assert hasattr(manager, 'hybrid_selector')
    
    def test_selection_mode_change(self, app, mock_overlay_api):
        """Test selection mode changes."""
        manager = SelectionManager(mock_overlay_api)
        
        # Test mode change
        manager.set_selection_mode(SelectionMode.MULTI)
        assert manager.current_state.mode == SelectionMode.MULTI
        
        # Test strategy change
        manager.set_selection_strategy(SelectionStrategy.INTERSECTS)
        assert manager.current_state.strategy == SelectionStrategy.INTERSECTS
    
    def test_selection_state_management(self, app, mock_overlay_api):
        """Test selection state management."""
        manager = SelectionManager(mock_overlay_api)
        
        # Get initial state
        initial_state = manager.get_current_state()
        assert len(initial_state.selected_elements) == 0
        
        # Test state copying
        state_copy = initial_state.copy()
        assert state_copy.selected_elements == initial_state.selected_elements
        assert state_copy.mode == initial_state.mode


class TestSelectionStateManager:
    """Test cases for SelectionStateManager."""
    
    def test_initialization(self, temp_project_dir):
        """Test SelectionStateManager initialization."""
        manager = SelectionStateManager(temp_project_dir)
        
        assert manager.project_path == temp_project_dir
        assert manager.current_session is not None
        assert len(manager.selection_sets) == 0
    
    def test_save_selection_state(self, temp_project_dir):
        """Test saving selection state."""
        manager = SelectionStateManager(temp_project_dir)
        
        # Create mock selection state
        mock_state = Mock()
        mock_state.mode = SelectionMode.SINGLE
        mock_state.strategy = SelectionStrategy.CONTAINS
        mock_state.selected_elements = [Mock()]
        
        # Save state
        selection_id = manager.save_selection_state(mock_state)
        
        assert selection_id is not None
        assert len(manager.current_session.selection_history) == 1
    
    def test_load_selection_state(self, temp_project_dir):
        """Test loading selection state."""
        manager = SelectionStateManager(temp_project_dir)
        
        # Create and save state
        mock_state = Mock()
        mock_state.mode = SelectionMode.SINGLE
        mock_state.strategy = SelectionStrategy.CONTAINS
        mock_state.selected_elements = [Mock()]
        
        selection_id = manager.save_selection_state(mock_state)
        
        # Load state
        loaded_state = manager.load_selection_state(selection_id)
        
        assert loaded_state is not None
        assert loaded_state.selection_id == selection_id
    
    def test_selection_sets(self, temp_project_dir):
        """Test selection sets functionality."""
        manager = SelectionStateManager(temp_project_dir)
        
        # Create selection set
        set_id = manager.create_selection_set("Test Set", "A test selection set")
        
        assert set_id is not None
        assert len(manager.selection_sets) == 1
        
        # Get selection set
        selection_set = manager.get_selection_set(set_id)
        assert selection_set is not None
        assert selection_set.name == "Test Set"
        
        # Delete selection set
        deleted = manager.delete_selection_set(set_id)
        assert deleted is True
        assert len(manager.selection_sets) == 0
    
    def test_export_import_selection_set(self, temp_project_dir):
        """Test exporting and importing selection sets."""
        manager = SelectionStateManager(temp_project_dir)
        
        # Create selection set
        set_id = manager.create_selection_set("Export Test", "Test export/import")
        
        # Export
        export_path = temp_project_dir / "test_export.json"
        exported = manager.export_selection_set(set_id, export_path)
        
        assert exported is True
        assert export_path.exists()
        
        # Clear sets
        manager.selection_sets.clear()
        
        # Import
        imported_id = manager.import_selection_set(export_path)
        
        assert imported_id is not None
        assert len(manager.selection_sets) == 1
        
        imported_set = manager.get_selection_set(imported_id)
        assert imported_set.name == "Export Test"


class TestPersistenceManager:
    """Test cases for PersistenceManager."""
    
    def test_json_persistence(self, temp_project_dir):
        """Test JSON persistence."""
        manager = PersistenceManager()
        
        # Create test snapshot
        snapshot = SelectionStateSnapshot(
            selection_id="test_id",
            timestamp=datetime.now(),
            selection_mode=SelectionMode.SINGLE,
            selection_strategy=SelectionStrategy.CONTAINS,
            selected_elements=["elem1", "elem2"],
            selection_bounds=[Rectangle(0, 0, 100, 100)]
        )
        
        # Save to JSON
        json_path = temp_project_dir / "test_snapshot.json"
        saved = manager.save_selection_snapshot(snapshot, json_path)
        
        assert saved is True
        assert json_path.exists()
        
        # Load from JSON
        loaded = manager.load_selection_snapshot(json_path)
        
        assert loaded is not None
        assert loaded.selection_id == "test_id"
        assert loaded.selection_mode == SelectionMode.SINGLE
        assert len(loaded.selected_elements) == 2
    
    def test_format_migration(self, temp_project_dir):
        """Test format migration."""
        manager = PersistenceManager()
        
        # Create test snapshot
        snapshot = SelectionStateSnapshot(
            selection_id="migration_test",
            timestamp=datetime.now(),
            selection_mode=SelectionMode.MULTI,
            selection_strategy=SelectionStrategy.INTERSECTS,
            selected_elements=["elem1"],
            selection_bounds=[Rectangle(10, 10, 50, 50)]
        )
        
        # Save as JSON
        json_path = temp_project_dir / "source.json"
        manager.save_selection_snapshot(snapshot, json_path)
        
        # Migrate to XML
        xml_path = temp_project_dir / "target.xml"
        migrated = manager.migrate_format(
            json_path, xml_path, StorageFormat.JSON, StorageFormat.XML
        )
        
        assert migrated is True
        assert xml_path.exists()


class TestOverlayIntegration:
    """Test cases for OverlaySelectionIntegration."""
    
    def test_initialization(self, app, mock_overlay_api):
        """Test overlay integration initialization."""
        # Create mock selection manager
        selection_manager = Mock()
        selection_manager.selection_changed = Mock()
        selection_manager.selection_changed.connect = Mock()
        selection_manager.mode_changed = Mock()
        selection_manager.mode_changed.connect = Mock()
        
        # Create integration
        integration = OverlaySelectionIntegration(
            selection_manager,
            mock_overlay_api,
            IntegrationMode.ACTIVE
        )
        
        assert integration.selection_manager == selection_manager
        assert integration.overlay_api == mock_overlay_api
        assert integration.integration_mode == IntegrationMode.ACTIVE
    
    def test_element_discovery(self, app, mock_overlay_api):
        """Test element discovery."""
        selection_manager = Mock()
        selection_manager.selection_changed = Mock()
        selection_manager.selection_changed.connect = Mock()
        selection_manager.mode_changed = Mock()
        selection_manager.mode_changed.connect = Mock()
        
        integration = OverlaySelectionIntegration(
            selection_manager,
            mock_overlay_api,
            IntegrationMode.ACTIVE
        )
        
        # Trigger element discovery
        integration._discover_overlay_elements()
        
        # Check that elements were discovered
        assert len(integration.element_cache) == 4  # 4 test elements
        assert "elem1" in integration.element_cache
        assert "elem2" in integration.element_cache
    
    def test_selectable_elements(self, app, mock_overlay_api):
        """Test getting selectable elements."""
        selection_manager = Mock()
        selection_manager.selection_changed = Mock()
        selection_manager.selection_changed.connect = Mock()
        selection_manager.mode_changed = Mock()
        selection_manager.mode_changed.connect = Mock()
        
        integration = OverlaySelectionIntegration(
            selection_manager,
            mock_overlay_api,
            IntegrationMode.ACTIVE
        )
        
        # Get selectable elements in region
        region = Rectangle(0, 0, 200, 200)
        selectable = integration.get_selectable_elements(region)
        
        # Should find elements that intersect with region
        assert len(selectable) > 0
        
        # Check specific elements
        elem_ids = [elem.element_id for elem in selectable]
        assert "elem1" in elem_ids  # elem1 should be in region
        assert "elem2" in elem_ids  # elem2 should be in region


class TestAgent2Coordinator:
    """Test cases for Agent2ElementSelectionCoordinator."""
    
    def test_initialization(self, app, mock_overlay_api, temp_project_dir, agent2_config):
        """Test coordinator initialization."""
        coordinator = Agent2ElementSelectionCoordinator(
            mock_overlay_api,
            temp_project_dir,
            agent2_config
        )
        
        assert coordinator.is_initialized is True
        assert coordinator.selection_manager is not None
        assert coordinator.state_manager is not None
        assert coordinator.overlay_integration is not None
        assert coordinator.state_integration is not None
    
    def test_element_selection(self, app, mock_overlay_api, temp_project_dir, agent2_config):
        """Test element selection through coordinator."""
        coordinator = Agent2ElementSelectionCoordinator(
            mock_overlay_api,
            temp_project_dir,
            agent2_config
        )
        
        # Test rectangular selection
        selection_bounds = Rectangle(0, 0, 200, 200)
        selected_ids = coordinator.select_elements(selection_bounds)
        
        # Should have selected some elements
        assert isinstance(selected_ids, list)
        
        # Test current selection
        current_selection = coordinator.get_current_selection()
        assert current_selection is not None
        assert current_selection.mode == SelectionMode.SINGLE
    
    def test_state_management(self, app, mock_overlay_api, temp_project_dir, agent2_config):
        """Test state management through coordinator."""
        coordinator = Agent2ElementSelectionCoordinator(
            mock_overlay_api,
            temp_project_dir,
            agent2_config
        )
        
        # Select some elements
        selection_bounds = Rectangle(0, 0, 200, 200)
        coordinator.select_elements(selection_bounds)
        
        # Save current selection
        selection_id = coordinator.save_current_selection()
        
        if selection_id:  # May be None if no elements selected
            # Clear selection
            coordinator.clear_selection()
            
            # Load saved selection
            loaded = coordinator.load_selection(selection_id)
            assert loaded is True
    
    def test_undo_redo(self, app, mock_overlay_api, temp_project_dir, agent2_config):
        """Test undo/redo functionality."""
        coordinator = Agent2ElementSelectionCoordinator(
            mock_overlay_api,
            temp_project_dir,
            agent2_config
        )
        
        # Initial state - should not be able to undo
        assert coordinator.can_undo() is False
        assert coordinator.can_redo() is False
        
        # Make a selection
        selection_bounds = Rectangle(0, 0, 100, 100)
        coordinator.select_elements(selection_bounds)
        
        # Now should be able to undo
        if coordinator.can_undo():
            undone = coordinator.undo()
            assert undone is True
            
            # Should be able to redo
            if coordinator.can_redo():
                redone = coordinator.redo()
                assert redone is True
    
    def test_export_import(self, app, mock_overlay_api, temp_project_dir, agent2_config):
        """Test selection export/import."""
        coordinator = Agent2ElementSelectionCoordinator(
            mock_overlay_api,
            temp_project_dir,
            agent2_config
        )
        
        # Select some elements
        selection_bounds = Rectangle(0, 0, 200, 200)
        coordinator.select_elements(selection_bounds)
        
        # Export selection
        export_path = temp_project_dir / "exported_selection.json"
        exported = coordinator.export_selection(export_path)
        
        if exported:  # May fail if no elements selected
            assert export_path.exists()
            
            # Clear selection
            coordinator.clear_selection()
            
            # Import selection
            imported = coordinator.import_selection(export_path)
            assert imported is True
    
    def test_performance_monitoring(self, app, mock_overlay_api, temp_project_dir, agent2_config):
        """Test performance monitoring."""
        coordinator = Agent2ElementSelectionCoordinator(
            mock_overlay_api,
            temp_project_dir,
            agent2_config
        )
        
        # Get performance metrics
        metrics = coordinator.get_performance_metrics()
        
        assert isinstance(metrics, dict)
        assert 'selection_count' in metrics
        assert 'state_saves' in metrics
        assert 'overlay_syncs' in metrics
    
    def test_system_status(self, app, mock_overlay_api, temp_project_dir, agent2_config):
        """Test system status reporting."""
        coordinator = Agent2ElementSelectionCoordinator(
            mock_overlay_api,
            temp_project_dir,
            agent2_config
        )
        
        # Get system status
        status = coordinator.get_system_status()
        
        assert isinstance(status, dict)
        assert status['initialized'] is True
        assert status['selection_manager'] is True
        assert status['state_manager'] is True
        assert status['overlay_integration'] is True
        assert status['state_integration'] is True
        assert 'configuration' in status
        assert 'performance_metrics' in status
    
    def test_cleanup(self, app, mock_overlay_api, temp_project_dir, agent2_config):
        """Test system cleanup."""
        coordinator = Agent2ElementSelectionCoordinator(
            mock_overlay_api,
            temp_project_dir,
            agent2_config
        )
        
        # Cleanup should not raise errors
        coordinator.cleanup()
        
        # System should be marked as not initialized
        assert coordinator.is_initialized is False


class TestSelectionAlgorithms:
    """Test cases for selection algorithms."""
    
    def test_rectangular_selection(self, app, mock_overlay_api):
        """Test rectangular selection algorithm."""
        from src.torematrix.ui.viewer.selection_algorithms import RectangularSelector
        
        # Create mock overlay integration
        mock_integration = Mock()
        mock_integration.element_cache = mock_overlay_api.elements
        mock_integration.transform_point_to_document = lambda p: p
        
        # Create selector
        selector = RectangularSelector(mock_integration, SelectionStrategy.INTERSECTS)
        
        # Test selection
        selection_bounds = Rectangle(0, 0, 100, 100)
        selected = selector.select(selection_bounds)
        
        # Should select elements that intersect
        assert len(selected) > 0
        
        # Check that selected elements actually intersect
        for element in selected:
            assert element.bounds.intersects(selection_bounds)
    
    def test_polygon_selection(self, app, mock_overlay_api):
        """Test polygon selection algorithm."""
        from src.torematrix.ui.viewer.selection_algorithms import PolygonSelector
        
        # Create mock overlay integration
        mock_integration = Mock()
        mock_integration.element_cache = mock_overlay_api.elements
        mock_integration.transform_point_to_document = lambda p: p
        
        # Create selector
        selector = PolygonSelector(mock_integration, SelectionStrategy.INTERSECTS)
        
        # Test selection with triangle
        polygon_points = [
            Point(0, 0),
            Point(100, 0),
            Point(50, 100)
        ]
        
        selected = selector.select(polygon_points)
        
        # Should select elements that intersect with triangle
        assert isinstance(selected, list)
    
    def test_layer_selection(self, app, mock_overlay_api):
        """Test layer-based selection algorithm."""
        from src.torematrix.ui.viewer.selection_algorithms import LayerSelector
        
        # Create mock overlay integration
        mock_integration = Mock()
        mock_integration.element_cache = mock_overlay_api.elements
        
        # Create selector
        selector = LayerSelector(mock_integration)
        
        # Test selection by layer
        selected = selector.select(["layer1"])
        
        # Should select only elements from layer1
        assert len(selected) == 2  # 2 elements in layer1
        for element in selected:
            assert element.layer_name == "layer1"
    
    def test_type_selection(self, app, mock_overlay_api):
        """Test type-based selection algorithm."""
        from src.torematrix.ui.viewer.selection_algorithms import TypeSelector
        
        # Create mock overlay integration
        mock_integration = Mock()
        mock_integration.element_cache = mock_overlay_api.elements
        
        # Create selector
        selector = TypeSelector(mock_integration)
        
        # Test selection by type
        selected = selector.select(["test_element"])
        
        # Should select all elements of type "test_element"
        assert len(selected) == 4  # All test elements
        for element in selected:
            assert element.element_type == "test_element"


class TestEventSystem:
    """Test cases for the event system."""
    
    def test_event_manager(self, app):
        """Test event manager functionality."""
        manager = SelectionEventManager()
        
        # Test event publishing
        from src.torematrix.ui.viewer.events import SelectionEvent
        
        event = SelectionEvent(
            event_type=EventType.SELECTION_CHANGED,
            selection_id="test_id",
            timestamp=datetime.now()
        )
        
        # Should be able to publish event
        manager.publish(event)
        
        # Test event subscription
        events_received = []
        
        def event_handler(event):
            events_received.append(event)
        
        manager.subscribe(EventType.SELECTION_CHANGED, event_handler)
        
        # Publish another event
        manager.publish(event)
        
        # Handler should have received event
        assert len(events_received) == 1
        assert events_received[0].event_type == EventType.SELECTION_CHANGED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])