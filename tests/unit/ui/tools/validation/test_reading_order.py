"""
Tests for reading order visualization.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtGui import QColor

from torematrix.ui.tools.validation.reading_order import (
    ReadingOrderWidget,
    ReadingOrderVisualization,
    ReadingOrderControlPanel,
    ReadingOrderItem,
    ReadingOrderFlow,
    ReadingOrderMode,
    ReadingOrderConfig,
    FlowDirection
)
from torematrix.core.models.element import Element, ElementType
from torematrix.core.operations.hierarchy import HierarchyManager
from torematrix.core.events import EventBus
from torematrix.core.state import StateStore
from torematrix.utils.geometry import Rect


@pytest.fixture
def qapp():
    """Create QApplication instance for testing."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def mock_hierarchy_manager():
    """Create mock hierarchy manager."""
    manager = Mock(spec=HierarchyManager)
    manager.get_reading_order.return_value = ['elem1', 'elem2', 'elem3']
    return manager


@pytest.fixture
def mock_state_store():
    """Create mock state store."""
    store = Mock(spec=StateStore)
    return store


@pytest.fixture
def sample_elements():
    """Create sample elements for testing."""
    return [
        Element(
            id='elem1',
            element_type=ElementType.TITLE,
            text='Element 1',
            bounds=Rect(0, 0, 100, 50),
            parent_id=None,
            children=[]
        ),
        Element(
            id='elem2',
            element_type=ElementType.NARRATIVE_TEXT,
            text='Element 2',
            bounds=Rect(0, 60, 100, 40),
            parent_id=None,
            children=[]
        ),
        Element(
            id='elem3',
            element_type=ElementType.LIST_ITEM,
            text='Element 3',
            bounds=Rect(0, 110, 100, 30),
            parent_id=None,
            children=[]
        )
    ]


class TestReadingOrderConfig:
    """Test the ReadingOrderConfig class."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = ReadingOrderConfig()
        
        assert config.mode == ReadingOrderMode.FLOW_ARROWS
        assert config.flow_direction == FlowDirection.LEFT_TO_RIGHT
        assert config.show_numbers == True
        assert config.show_connections == True
        assert config.highlight_current == True
        assert config.animate_flow == True
        assert config.arrow_size == 12.0
        assert config.number_size == 16.0
        assert config.connection_width == 2.0
        assert isinstance(config.highlight_color, QColor)
        assert isinstance(config.arrow_color, QColor)
        assert isinstance(config.number_color, QColor)
        assert isinstance(config.connection_color, QColor)
    
    def test_custom_values(self):
        """Test custom configuration values."""
        config = ReadingOrderConfig(
            mode=ReadingOrderMode.NUMBERED_SEQUENCE,
            flow_direction=FlowDirection.RIGHT_TO_LEFT,
            show_numbers=False,
            show_connections=False,
            animate_flow=False,
            arrow_size=16.0,
            number_size=20.0,
            connection_width=3.0
        )
        
        assert config.mode == ReadingOrderMode.NUMBERED_SEQUENCE
        assert config.flow_direction == FlowDirection.RIGHT_TO_LEFT
        assert config.show_numbers == False
        assert config.show_connections == False
        assert config.animate_flow == False
        assert config.arrow_size == 16.0
        assert config.number_size == 20.0
        assert config.connection_width == 3.0


class TestReadingOrderItem:
    """Test the ReadingOrderItem class."""
    
    def test_init(self, qapp, sample_elements):
        """Test reading order item initialization."""
        element = sample_elements[0]
        config = ReadingOrderConfig()
        
        item = ReadingOrderItem(element, 0, config)
        
        assert item.element == element
        assert item.order_index == 0
        assert item.config == config
        assert item.is_highlighted == False
        assert item.is_current == False
        assert item.isSelectable()
        assert item.pos() == QPointF(element.bounds.x, element.bounds.y)
    
    def test_bounding_rect(self, qapp, sample_elements):
        """Test bounding rectangle calculation."""
        element = sample_elements[0]
        config = ReadingOrderConfig()
        
        item = ReadingOrderItem(element, 0, config)
        
        bounding_rect = item.boundingRect()
        assert bounding_rect.width() == element.bounds.width
        assert bounding_rect.height() == element.bounds.height
    
    def test_set_highlighted(self, qapp, sample_elements):
        """Test highlight state changes."""
        element = sample_elements[0]
        config = ReadingOrderConfig()
        
        item = ReadingOrderItem(element, 0, config)
        
        # Initially not highlighted
        assert item.is_highlighted == False
        
        # Set highlighted
        item.set_highlighted(True)
        assert item.is_highlighted == True
        
        # Set not highlighted
        item.set_highlighted(False)
        assert item.is_highlighted == False
    
    def test_set_current(self, qapp, sample_elements):
        """Test current state changes."""
        element = sample_elements[0]
        config = ReadingOrderConfig()
        
        item = ReadingOrderItem(element, 0, config)
        
        # Initially not current
        assert item.is_current == False
        
        # Set current
        item.set_current(True)
        assert item.is_current == True
        
        # Set not current
        item.set_current(False)
        assert item.is_current == False


class TestReadingOrderFlow:
    """Test the ReadingOrderFlow class."""
    
    def test_init(self, qapp, sample_elements):
        """Test reading order flow initialization."""
        element1 = sample_elements[0]
        element2 = sample_elements[1]
        config = ReadingOrderConfig()
        
        item1 = ReadingOrderItem(element1, 0, config)
        item2 = ReadingOrderItem(element2, 1, config)
        
        flow = ReadingOrderFlow(item1, item2, config)
        
        assert flow.from_item == item1
        assert flow.to_item == item2
        assert flow.config == config
        assert flow.is_animated == False
        assert flow.animation_progress == 0.0
        assert isinstance(flow.start_point, QPointF)
        assert isinstance(flow.end_point, QPointF)
    
    def test_bounding_rect(self, qapp, sample_elements):
        """Test bounding rectangle calculation."""
        element1 = sample_elements[0]
        element2 = sample_elements[1]
        config = ReadingOrderConfig()
        
        item1 = ReadingOrderItem(element1, 0, config)
        item2 = ReadingOrderItem(element2, 1, config)
        
        flow = ReadingOrderFlow(item1, item2, config)
        
        bounding_rect = flow.boundingRect()
        assert bounding_rect.width() > 0
        assert bounding_rect.height() > 0


class TestReadingOrderVisualization:
    """Test the ReadingOrderVisualization class."""
    
    def test_init(self, qapp):
        """Test visualization initialization."""
        viz = ReadingOrderVisualization()
        
        assert viz.hierarchy_manager is None
        assert viz.state_store is None
        assert isinstance(viz.config, ReadingOrderConfig)
        assert viz.scene is not None
        assert len(viz.order_items) == 0
        assert len(viz.flow_items) == 0
        assert len(viz.current_elements) == 0
        assert len(viz.current_order) == 0
        assert viz.selected_element_id is None
    
    def test_set_managers(self, qapp, mock_hierarchy_manager, mock_state_store):
        """Test setting managers."""
        viz = ReadingOrderVisualization()
        
        viz.set_hierarchy_manager(mock_hierarchy_manager)
        assert viz.hierarchy_manager == mock_hierarchy_manager
        
        viz.set_state_store(mock_state_store)
        assert viz.state_store == mock_state_store
    
    def test_set_config(self, qapp):
        """Test configuration setting."""
        viz = ReadingOrderVisualization()
        
        new_config = ReadingOrderConfig(
            mode=ReadingOrderMode.NUMBERED_SEQUENCE,
            show_numbers=False
        )
        
        viz.set_config(new_config)
        assert viz.config == new_config
    
    def test_show_reading_order(self, qapp, sample_elements):
        """Test showing reading order."""
        viz = ReadingOrderVisualization()
        
        order = ['elem1', 'elem2', 'elem3']
        viz.show_reading_order(sample_elements, order)
        
        assert viz.current_elements == sample_elements
        assert viz.current_order == order
        assert len(viz.order_items) == 3
        assert 'elem1' in viz.order_items
        assert 'elem2' in viz.order_items
        assert 'elem3' in viz.order_items
    
    def test_highlight_element(self, qapp, sample_elements):
        """Test element highlighting."""
        viz = ReadingOrderVisualization()
        
        order = ['elem1', 'elem2', 'elem3']
        viz.show_reading_order(sample_elements, order)
        
        # Highlight element
        viz.highlight_element('elem2')
        
        assert viz.selected_element_id == 'elem2'
        assert viz.order_items['elem2'].is_highlighted == True
        assert viz.order_items['elem1'].is_highlighted == False
        assert viz.order_items['elem3'].is_highlighted == False
    
    def test_set_current_element(self, qapp, sample_elements):
        """Test setting current element."""
        viz = ReadingOrderVisualization()
        
        order = ['elem1', 'elem2', 'elem3']
        viz.show_reading_order(sample_elements, order)
        
        # Set current element
        viz.set_current_element('elem2')
        
        assert viz.order_items['elem2'].is_current == True
        assert viz.order_items['elem1'].is_current == False
        assert viz.order_items['elem3'].is_current == False
    
    def test_empty_elements(self, qapp):
        """Test with empty elements."""
        viz = ReadingOrderVisualization()
        
        viz.show_reading_order([], [])
        
        assert len(viz.order_items) == 0
        assert len(viz.flow_items) == 0


class TestReadingOrderControlPanel:
    """Test the ReadingOrderControlPanel class."""
    
    def test_init(self, qapp):
        """Test control panel initialization."""
        panel = ReadingOrderControlPanel()
        
        assert isinstance(panel.config, ReadingOrderConfig)
        assert panel.mode_combo is not None
        assert panel.show_numbers_cb is not None
        assert panel.show_connections_cb is not None
        assert panel.animate_flow_cb is not None
        assert panel.arrow_size_slider is not None
        assert panel.number_size_slider is not None
    
    def test_mode_change(self, qapp):
        """Test mode change handling."""
        panel = ReadingOrderControlPanel()
        
        # Mock signal
        panel.mode_changed = Mock()
        
        # Change mode
        panel.mode_combo.setCurrentIndex(1)  # NUMBERED_SEQUENCE
        
        assert panel.config.mode == ReadingOrderMode.NUMBERED_SEQUENCE
        panel.mode_changed.emit.assert_called_once()
    
    def test_config_changes(self, qapp):
        """Test configuration changes."""
        panel = ReadingOrderControlPanel()
        
        # Mock signal
        panel.config_changed = Mock()
        
        # Change show numbers
        panel.show_numbers_cb.setChecked(False)
        assert panel.config.show_numbers == False
        panel.config_changed.emit.assert_called()
        
        # Change show connections
        panel.show_connections_cb.setChecked(False)
        assert panel.config.show_connections == False
        
        # Change arrow size
        panel.arrow_size_slider.setValue(20)
        assert panel.config.arrow_size == 20.0
        
        # Change number size
        panel.number_size_slider.setValue(18)
        assert panel.config.number_size == 18.0
    
    def test_animation_toggle(self, qapp):
        """Test animation toggle."""
        panel = ReadingOrderControlPanel()
        
        # Mock signal
        panel.animation_toggled = Mock()
        
        # Toggle animation
        panel.animate_flow_cb.setChecked(False)
        
        assert panel.config.animate_flow == False
        panel.animation_toggled.emit.assert_called_once_with(False)


class TestReadingOrderWidget:
    """Test the ReadingOrderWidget class."""
    
    def test_init(self, qapp):
        """Test widget initialization."""
        widget = ReadingOrderWidget()
        
        assert widget.hierarchy_manager is None
        assert widget.state_store is None
        assert len(widget.current_elements) == 0
        assert widget.visualization is not None
        assert widget.control_panel is not None
        assert isinstance(widget.visualization, ReadingOrderVisualization)
        assert isinstance(widget.control_panel, ReadingOrderControlPanel)
    
    def test_set_managers(self, qapp, mock_hierarchy_manager, mock_state_store):
        """Test setting managers."""
        widget = ReadingOrderWidget()
        
        widget.set_hierarchy_manager(mock_hierarchy_manager)
        assert widget.hierarchy_manager == mock_hierarchy_manager
        assert widget.visualization.hierarchy_manager == mock_hierarchy_manager
        
        widget.set_state_store(mock_state_store)
        assert widget.state_store == mock_state_store
        assert widget.visualization.state_store == mock_state_store
    
    def test_show_elements(self, qapp, mock_hierarchy_manager, sample_elements):
        """Test showing elements."""
        widget = ReadingOrderWidget()
        widget.set_hierarchy_manager(mock_hierarchy_manager)
        
        # Mock reading order
        mock_hierarchy_manager.get_reading_order.return_value = ['elem1', 'elem2', 'elem3']
        
        widget.show_elements(sample_elements)
        
        assert widget.current_elements == sample_elements
        mock_hierarchy_manager.get_reading_order.assert_called_once()
    
    def test_highlight_element(self, qapp, sample_elements):
        """Test element highlighting."""
        widget = ReadingOrderWidget()
        
        # Mock visualization
        widget.visualization.highlight_element = Mock()
        
        widget.highlight_element('elem1')
        
        widget.visualization.highlight_element.assert_called_once_with('elem1')
    
    def test_set_current_element(self, qapp, sample_elements):
        """Test setting current element."""
        widget = ReadingOrderWidget()
        
        # Mock visualization
        widget.visualization.set_current_element = Mock()
        
        widget.set_current_element('elem1')
        
        widget.visualization.set_current_element.assert_called_once_with('elem1')
    
    def test_element_selection_signal(self, qapp):
        """Test element selection signal."""
        widget = ReadingOrderWidget()
        
        # Mock element selected signal
        widget.element_selected = Mock()
        
        # Simulate element selection from visualization
        widget._on_element_selected('elem1')
        
        widget.element_selected.emit.assert_called_once_with('elem1')
    
    def test_order_changed_signal(self, qapp):
        """Test order changed signal."""
        widget = ReadingOrderWidget()
        
        # Mock order changed signal
        widget.order_changed = Mock()
        
        # Simulate order change from visualization
        widget._on_order_changed(['elem2', 'elem1', 'elem3'])
        
        widget.order_changed.emit.assert_called_once_with(['elem2', 'elem1', 'elem3'])
    
    def test_config_change_integration(self, qapp):
        """Test configuration change integration."""
        widget = ReadingOrderWidget()
        
        # Mock visualization config setting
        widget.visualization.set_config = Mock()
        
        # Simulate config change from control panel
        new_config = ReadingOrderConfig(show_numbers=False)
        widget._on_config_changed(new_config)
        
        widget.visualization.set_config.assert_called_once_with(new_config)


class TestReadingOrderModes:
    """Test different reading order modes."""
    
    def test_flow_arrows_mode(self):
        """Test flow arrows mode."""
        mode = ReadingOrderMode.FLOW_ARROWS
        assert mode.value == "flow_arrows"
    
    def test_numbered_sequence_mode(self):
        """Test numbered sequence mode."""
        mode = ReadingOrderMode.NUMBERED_SEQUENCE
        assert mode.value == "numbered_sequence"
    
    def test_highlighted_path_mode(self):
        """Test highlighted path mode."""
        mode = ReadingOrderMode.HIGHLIGHTED_PATH
        assert mode.value == "highlighted_path"
    
    def test_spatial_grouping_mode(self):
        """Test spatial grouping mode."""
        mode = ReadingOrderMode.SPATIAL_GROUPING
        assert mode.value == "spatial_grouping"


class TestFlowDirections:
    """Test different flow directions."""
    
    def test_left_to_right(self):
        """Test left to right direction."""
        direction = FlowDirection.LEFT_TO_RIGHT
        assert direction.value == "left_to_right"
    
    def test_right_to_left(self):
        """Test right to left direction."""
        direction = FlowDirection.RIGHT_TO_LEFT
        assert direction.value == "right_to_left"
    
    def test_top_to_bottom(self):
        """Test top to bottom direction."""
        direction = FlowDirection.TOP_TO_BOTTOM
        assert direction.value == "top_to_bottom"
    
    def test_bottom_to_top(self):
        """Test bottom to top direction."""
        direction = FlowDirection.BOTTOM_TO_TOP
        assert direction.value == "bottom_to_top"


if __name__ == '__main__':
    pytest.main([__file__])