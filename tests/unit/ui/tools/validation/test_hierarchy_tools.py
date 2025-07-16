"""
Comprehensive unit tests for Interactive Hierarchy UI Tools.

Tests Agent 2 implementation for Issue #241 - Interactive Hierarchy UI Tools.
Covers all components: HierarchyTreeWidget, HierarchyControlPanel, 
HierarchyMetricsWidget, and HierarchyToolsWidget.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import List, Dict, Any
from datetime import datetime

from PyQt6.QtWidgets import QApplication, QTreeWidgetItem, QMenu
from PyQt6.QtCore import Qt, QPoint, QMimeData
from PyQt6.QtTest import QTest
from PyQt6.QtGui import QDragEnterEvent, QDropEvent

from src.torematrix.ui.tools.validation.hierarchy_tools import (
    HierarchyTreeWidget,
    HierarchyControlPanel,
    HierarchyMetricsWidget,
    HierarchyToolsWidget,
    HierarchyOperation,
    ValidationLevel,
    HierarchyMetrics,
    HierarchyTreeDelegate
)
from src.torematrix.core.models.element import Element, ElementType
from src.torematrix.core.models.hierarchy import ElementHierarchy
from src.torematrix.core.state import Store
from src.torematrix.core.events import EventBus


@pytest.fixture
def qapp():
    """Qt application fixture"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def mock_state_manager():
    """Mock state manager"""
    return Mock(spec=Store)


@pytest.fixture
def mock_event_bus():
    """Mock event bus"""
    return Mock(spec=EventBus)


@pytest.fixture
def sample_elements():
    """Create sample elements for testing"""
    elements = []
    
    # Root element
    root = Element(
        element_id="root-1",
        element_type=ElementType.TITLE,
        text="Document Title",
        parent_id=None
    )
    elements.append(root)
    
    # Child elements
    child1 = Element(
        element_id="child-1", 
        element_type=ElementType.TEXT,
        text="First paragraph text",
        parent_id="root-1"
    )
    elements.append(child1)
    
    child2 = Element(
        element_id="child-2",
        element_type=ElementType.LIST,
        text="• List item 1\n• List item 2",
        parent_id="root-1"
    )
    elements.append(child2)
    
    # Grandchild element
    grandchild = Element(
        element_id="grandchild-1",
        element_type=ElementType.TEXT,
        text="Nested text element",
        parent_id="child-2"
    )
    elements.append(grandchild)
    
    # Orphaned element (for testing validation)
    orphaned = Element(
        element_id="orphaned-1",
        element_type=ElementType.TEXT,
        text="Orphaned element",
        parent_id="non-existent-parent"
    )
    elements.append(orphaned)
    
    return elements


@pytest.fixture
def sample_hierarchy(sample_elements):
    """Create sample hierarchy for testing"""
    return ElementHierarchy(sample_elements)


class TestHierarchyMetrics:
    """Test hierarchy metrics calculation and health scoring"""
    
    def test_empty_metrics(self):
        """Test empty metrics initialization"""
        metrics = HierarchyMetrics()
        assert metrics.total_elements == 0
        assert metrics.depth_levels == 0
        assert metrics.orphaned_elements == 0
        assert metrics.circular_references == 0
        assert metrics.validation_errors == 0
        assert metrics.reading_order_issues == 0
        assert metrics.health_score == 1.0
        assert isinstance(metrics.last_updated, datetime)
    
    def test_health_score_calculation(self):
        """Test health score calculation with various scenarios"""
        # Perfect health
        metrics = HierarchyMetrics(total_elements=10)
        assert metrics.health_score == 1.0
        
        # With orphaned elements
        metrics = HierarchyMetrics(total_elements=10, orphaned_elements=1)
        expected_score = 1.0 - (1/10 * 0.3)  # 30% penalty
        assert abs(metrics.health_score - expected_score) < 0.01
        
        # With validation errors
        metrics = HierarchyMetrics(total_elements=10, validation_errors=2)
        expected_score = 1.0 - (2/10 * 0.4)  # 40% penalty
        assert abs(metrics.health_score - expected_score) < 0.01
        
        # With circular references
        metrics = HierarchyMetrics(total_elements=10, circular_references=1)
        expected_score = 1.0 - (1/10 * 0.5)  # 50% penalty
        assert abs(metrics.health_score - expected_score) < 0.01
        
        # Multiple issues
        metrics = HierarchyMetrics(
            total_elements=10,
            orphaned_elements=1,
            validation_errors=1,
            circular_references=1,
            reading_order_issues=1
        )
        total_penalty = (1/10 * 0.3) + (1/10 * 0.4) + (1/10 * 0.5) + (1/10 * 0.2)
        expected_score = max(0.0, 1.0 - total_penalty)
        assert abs(metrics.health_score - expected_score) < 0.01
    
    def test_score_bounds(self):
        """Test health score stays within bounds"""
        # Extreme negative case
        metrics = HierarchyMetrics(
            total_elements=1,
            orphaned_elements=5,
            validation_errors=5,
            circular_references=5,
            reading_order_issues=5
        )
        assert metrics.health_score >= 0.0
        assert metrics.health_score <= 1.0


class TestHierarchyTreeDelegate:
    """Test custom tree delegate rendering"""
    
    def test_delegate_initialization(self, qapp):
        """Test delegate initialization"""
        delegate = HierarchyTreeDelegate()
        assert len(delegate.validation_colors) == 4
        assert ValidationLevel.VALID in delegate.validation_colors
        assert ValidationLevel.WARNING in delegate.validation_colors
        assert ValidationLevel.ERROR in delegate.validation_colors
        assert ValidationLevel.CRITICAL in delegate.validation_colors
    
    def test_validation_colors(self, qapp):
        """Test validation color mapping"""
        delegate = HierarchyTreeDelegate()
        
        # Verify color assignments
        assert delegate.validation_colors[ValidationLevel.VALID].name() == "#2e7d32"  # Green
        assert delegate.validation_colors[ValidationLevel.WARNING].name() == "#ff9800"  # Orange
        assert delegate.validation_colors[ValidationLevel.ERROR].name() == "#d32f2f"  # Red
        assert delegate.validation_colors[ValidationLevel.CRITICAL].name() == "#880e4f"  # Purple


class TestHierarchyTreeWidget:
    """Test hierarchy tree widget functionality"""
    
    def test_initialization(self, qapp, mock_state_manager, mock_event_bus):
        """Test tree widget initialization"""
        tree = HierarchyTreeWidget(mock_state_manager, mock_event_bus)
        
        assert tree.state_manager == mock_state_manager
        assert tree.event_bus == mock_event_bus
        assert tree.hierarchy is None
        assert len(tree.element_items) == 0
        assert len(tree.validation_cache) == 0
        
        # Check UI setup
        assert tree.columnCount() == 4
        assert tree.headerItem().text(0) == "Element"
        assert tree.headerItem().text(1) == "Type"
        assert tree.headerItem().text(2) == "Status"
        assert tree.headerItem().text(3) == "Depth"
        
        # Check drag-drop configuration
        assert tree.dragEnabled()
        assert tree.acceptDrops()
        assert tree.dragDropMode() == tree.DragDropMode.InternalMove
    
    def test_load_hierarchy(self, qapp, mock_state_manager, mock_event_bus, sample_hierarchy):
        """Test loading hierarchy into tree"""
        tree = HierarchyTreeWidget(mock_state_manager, mock_event_bus)
        tree.load_hierarchy(sample_hierarchy)
        
        assert tree.hierarchy == sample_hierarchy
        assert len(tree.element_items) == len(sample_hierarchy.elements)
        
        # Check tree structure
        assert tree.topLevelItemCount() == 1  # Only root element at top level
        root_item = tree.topLevelItem(0)
        assert root_item.childCount() == 2  # Two direct children
    
    def test_create_tree_item(self, qapp, mock_state_manager, mock_event_bus, sample_elements):
        """Test tree item creation"""
        tree = HierarchyTreeWidget(mock_state_manager, mock_event_bus)
        element = sample_elements[0]  # Root element
        
        item = tree._create_tree_item(element)
        
        assert item.text(0) == element.text
        assert item.text(1) == element.element_type.value
        assert item.text(2) == "Valid"
        assert item.text(3) == "0"  # Root depth
        assert item.data(0, Qt.ItemDataRole.UserRole) == element.element_id
    
    def test_element_icon_creation(self, qapp, mock_state_manager, mock_event_bus):
        """Test element icon creation for different types"""
        tree = HierarchyTreeWidget(mock_state_manager, mock_event_bus)
        
        # Test different element types
        for element_type in ElementType:
            icon = tree._get_element_icon(element_type)
            assert icon is not None
            assert not icon.isNull()
    
    def test_hierarchy_validation(self, qapp, mock_state_manager, mock_event_bus, sample_hierarchy):
        """Test hierarchy validation"""
        tree = HierarchyTreeWidget(mock_state_manager, mock_event_bus)
        tree.load_hierarchy(sample_hierarchy)
        
        # Check validation cache
        assert len(tree.validation_cache) > 0
        
        # All elements should have validation status
        for element_id in sample_hierarchy.elements:
            assert element_id in tree.validation_cache
            assert tree.validation_cache[element_id] in [
                ValidationLevel.VALID, 
                ValidationLevel.WARNING, 
                ValidationLevel.ERROR,
                ValidationLevel.CRITICAL
            ]
    
    def test_selection_management(self, qapp, mock_state_manager, mock_event_bus, sample_hierarchy):
        """Test element selection"""
        tree = HierarchyTreeWidget(mock_state_manager, mock_event_bus)
        tree.load_hierarchy(sample_hierarchy)
        
        # Test selecting elements
        element_ids = ["root-1", "child-1"]
        tree.select_elements(element_ids)
        
        selected_ids = tree.get_selected_elements()
        assert len(selected_ids) == 2
        assert "root-1" in selected_ids
        assert "child-1" in selected_ids
    
    def test_hierarchy_operations(self, qapp, mock_state_manager, mock_event_bus, sample_hierarchy):
        """Test hierarchy operations"""
        tree = HierarchyTreeWidget(mock_state_manager, mock_event_bus)
        tree.load_hierarchy(sample_hierarchy)
        
        # Test various operations
        element_ids = ["child-1"]
        
        # Operations should complete without error
        tree.perform_operation(HierarchyOperation.INDENT, element_ids)
        tree.perform_operation(HierarchyOperation.OUTDENT, element_ids)
        tree.perform_operation(HierarchyOperation.VALIDATE, element_ids)
        tree.perform_operation(HierarchyOperation.REFRESH, element_ids)
    
    def test_signal_emissions(self, qapp, mock_state_manager, mock_event_bus, sample_hierarchy):
        """Test signal emissions"""
        tree = HierarchyTreeWidget(mock_state_manager, mock_event_bus)
        tree.load_hierarchy(sample_hierarchy)
        
        # Mock signal handlers
        hierarchy_changed_handler = Mock()
        selection_changed_handler = Mock()
        validation_changed_handler = Mock()
        
        tree.hierarchy_changed.connect(hierarchy_changed_handler)
        tree.selection_changed.connect(selection_changed_handler)
        tree.validation_changed.connect(validation_changed_handler)
        
        # Trigger selection change
        tree.select_elements(["root-1"])
        selection_changed_handler.assert_called_once()
        
        # Trigger hierarchy change
        tree.perform_operation(HierarchyOperation.VALIDATE, [])
        # Note: hierarchy_changed may not emit for VALIDATE operation
    
    def test_context_menu_creation(self, qapp, mock_state_manager, mock_event_bus, sample_hierarchy):
        """Test context menu creation"""
        tree = HierarchyTreeWidget(mock_state_manager, mock_event_bus)
        tree.load_hierarchy(sample_hierarchy)
        
        # Mock item at position
        with patch.object(tree, 'itemAt') as mock_item_at:
            mock_item = Mock()
            mock_item.data.return_value = "root-1"
            mock_item_at.return_value = mock_item
            
            with patch.object(tree, 'selectedItems') as mock_selected:
                mock_selected.return_value = [mock_item]
                
                with patch('PyQt6.QtWidgets.QMenu') as mock_menu:
                    tree._show_context_menu(QPoint(10, 10))
                    mock_menu.assert_called_once()
    
    def test_element_validation(self, qapp, mock_state_manager, mock_event_bus, sample_hierarchy):
        """Test individual element validation"""
        tree = HierarchyTreeWidget(mock_state_manager, mock_event_bus)
        tree.load_hierarchy(sample_hierarchy)
        
        # Test validating an element
        element_id = "root-1"
        
        with patch('PyQt6.QtWidgets.QMessageBox.information') as mock_msg:
            tree._validate_element(element_id)
            mock_msg.assert_called_once()
        
        # Element should have validation status
        assert element_id in tree.validation_cache
        assert tree.validation_cache[element_id] in [
            ValidationLevel.VALID, 
            ValidationLevel.WARNING, 
            ValidationLevel.ERROR,
            ValidationLevel.CRITICAL
        ]
    
    def test_element_details_display(self, qapp, mock_state_manager, mock_event_bus, sample_hierarchy):
        """Test element details dialog"""
        tree = HierarchyTreeWidget(mock_state_manager, mock_event_bus)
        tree.load_hierarchy(sample_hierarchy)
        
        element = sample_hierarchy.elements["root-1"]
        
        with patch('PyQt6.QtWidgets.QMessageBox.information') as mock_msg:
            tree._show_element_details(element)
            mock_msg.assert_called_once()
            
            # Check message contains element details
            call_args = mock_msg.call_args[0]
            assert "Element Details:" in call_args[2]
            assert "root-1" in call_args[2]


class TestHierarchyControlPanel:
    """Test hierarchy control panel functionality"""
    
    def test_initialization(self, qapp, mock_state_manager, mock_event_bus):
        """Test control panel initialization"""
        tree = HierarchyTreeWidget(mock_state_manager, mock_event_bus)
        panel = HierarchyControlPanel(tree)
        
        assert panel.tree_widget == tree
        assert len(panel.selected_elements) == 0
        
        # Check buttons exist
        assert hasattr(panel, 'indent_btn')
        assert hasattr(panel, 'outdent_btn')
        assert hasattr(panel, 'move_up_btn')
        assert hasattr(panel, 'move_down_btn')
        assert hasattr(panel, 'group_btn')
        assert hasattr(panel, 'ungroup_btn')
        assert hasattr(panel, 'delete_btn')
        assert hasattr(panel, 'duplicate_btn')
        assert hasattr(panel, 'validate_btn')
        assert hasattr(panel, 'refresh_btn')
    
    def test_button_states_no_selection(self, qapp, mock_state_manager, mock_event_bus):
        """Test button states with no selection"""
        tree = HierarchyTreeWidget(mock_state_manager, mock_event_bus)
        panel = HierarchyControlPanel(tree)
        
        panel._on_selection_changed([])
        
        # Most buttons should be disabled
        assert not panel.indent_btn.isEnabled()
        assert not panel.outdent_btn.isEnabled()
        assert not panel.move_up_btn.isEnabled()
        assert not panel.move_down_btn.isEnabled()
        assert not panel.group_btn.isEnabled()
        assert not panel.ungroup_btn.isEnabled()
        assert not panel.delete_btn.isEnabled()
        assert not panel.duplicate_btn.isEnabled()
        
        # Utility buttons should be enabled
        assert panel.validate_btn.isEnabled()
        assert panel.refresh_btn.isEnabled()
    
    def test_button_states_single_selection(self, qapp, mock_state_manager, mock_event_bus):
        """Test button states with single selection"""
        tree = HierarchyTreeWidget(mock_state_manager, mock_event_bus)
        panel = HierarchyControlPanel(tree)
        
        panel._on_selection_changed(["element-1"])
        
        # Basic operations should be enabled
        assert panel.indent_btn.isEnabled()
        assert panel.outdent_btn.isEnabled()
        assert panel.move_up_btn.isEnabled()
        assert panel.move_down_btn.isEnabled()
        assert panel.delete_btn.isEnabled()
        assert panel.duplicate_btn.isEnabled()
        assert panel.ungroup_btn.isEnabled()
        
        # Group should be disabled (need multiple)
        assert not panel.group_btn.isEnabled()
        
        # Utility buttons should be enabled
        assert panel.validate_btn.isEnabled()
        assert panel.refresh_btn.isEnabled()
    
    def test_button_states_multiple_selection(self, qapp, mock_state_manager, mock_event_bus):
        """Test button states with multiple selection"""
        tree = HierarchyTreeWidget(mock_state_manager, mock_event_bus)
        panel = HierarchyControlPanel(tree)
        
        panel._on_selection_changed(["element-1", "element-2"])
        
        # Basic operations should be enabled
        assert panel.indent_btn.isEnabled()
        assert panel.outdent_btn.isEnabled()
        assert panel.delete_btn.isEnabled()
        
        # Group should be enabled (multiple elements)
        assert panel.group_btn.isEnabled()
        
        # Ungroup should be disabled (not single selection)
        assert not panel.ungroup_btn.isEnabled()
    
    def test_operation_request(self, qapp, mock_state_manager, mock_event_bus):
        """Test operation request signals"""
        tree = HierarchyTreeWidget(mock_state_manager, mock_event_bus)
        panel = HierarchyControlPanel(tree)
        
        # Set up selection
        panel.selected_elements = ["element-1"]
        panel._update_button_states()
        
        # Mock signal connection
        signal_received = []
        panel.operation_requested.connect(
            lambda op, ids: signal_received.append((op, ids))
        )
        
        # Trigger operation
        panel._request_operation(HierarchyOperation.INDENT)
        
        assert len(signal_received) == 1
        assert signal_received[0][0] == HierarchyOperation.INDENT
        assert signal_received[0][1] == ["element-1"]
    
    def test_delete_confirmation(self, qapp, mock_state_manager, mock_event_bus):
        """Test delete operation confirmation"""
        tree = HierarchyTreeWidget(mock_state_manager, mock_event_bus)
        panel = HierarchyControlPanel(tree)
        
        panel.selected_elements = ["element-1"]
        
        # Mock signal connection
        signal_received = []
        panel.operation_requested.connect(
            lambda op, ids: signal_received.append((op, ids))
        )
        
        # Mock message box to return No
        with patch('PyQt6.QtWidgets.QMessageBox.question', return_value=QMessageBox.StandardButton.No):
            panel._request_operation(HierarchyOperation.DELETE)
            
        # Should not emit signal when user cancels
        assert len(signal_received) == 0
        
        # Mock message box to return Yes
        with patch('PyQt6.QtWidgets.QMessageBox.question', return_value=QMessageBox.StandardButton.Yes):
            panel._request_operation(HierarchyOperation.DELETE)
            
        # Should emit signal when user confirms
        assert len(signal_received) == 1
        assert signal_received[0][0] == HierarchyOperation.DELETE
    
    def test_selection_info_update(self, qapp, mock_state_manager, mock_event_bus):
        """Test selection info display"""
        tree = HierarchyTreeWidget(mock_state_manager, mock_event_bus)
        panel = HierarchyControlPanel(tree)
        
        # No selection
        panel._on_selection_changed([])
        assert "No elements selected" in panel.selection_label.text()
        
        # Single selection
        panel._on_selection_changed(["element-1"])
        assert "1 element selected" in panel.selection_label.text()
        
        # Multiple selection
        panel._on_selection_changed(["element-1", "element-2"])
        assert "2 elements selected" in panel.selection_label.text()


class TestHierarchyMetricsWidget:
    """Test hierarchy metrics widget"""
    
    def test_initialization(self, qapp):
        """Test metrics widget initialization"""
        widget = HierarchyMetricsWidget()
        
        assert isinstance(widget.metrics, HierarchyMetrics)
        assert hasattr(widget, 'health_bar')
        assert hasattr(widget, 'total_label')
        assert hasattr(widget, 'depth_label')
        assert hasattr(widget, 'orphans_label')
        assert hasattr(widget, 'errors_label')
        assert hasattr(widget, 'updated_label')
    
    def test_metrics_update(self, qapp):
        """Test metrics display update"""
        widget = HierarchyMetricsWidget()
        
        # Create test metrics
        test_time = datetime.now()
        metrics = HierarchyMetrics(
            total_elements=50,
            depth_levels=4,
            orphaned_elements=2,
            validation_errors=1,
            last_updated=test_time
        )
        
        widget.update_metrics(metrics)
        
        assert widget.metrics == metrics
        assert "50" in widget.total_label.text()
        assert "4" in widget.depth_label.text()
        assert "2" in widget.orphans_label.text()
        assert "1" in widget.errors_label.text()
        assert test_time.strftime("%H:%M:%S") in widget.updated_label.text()
        
        # Check health bar
        expected_health = int(metrics.health_score * 100)
        assert widget.health_bar.value() == expected_health
    
    def test_health_bar_styling(self, qapp):
        """Test health bar color changes"""
        widget = HierarchyMetricsWidget()
        
        # High health score (green)
        metrics = HierarchyMetrics(total_elements=10)
        widget.update_metrics(metrics)
        assert "#4caf50" in widget.health_bar.styleSheet()  # Green
        
        # Low health score (red/purple)
        metrics = HierarchyMetrics(
            total_elements=10,
            validation_errors=8
        )
        widget.update_metrics(metrics)
        # Should be red or purple color
        style = widget.health_bar.styleSheet()
        assert ("#f44336" in style or "#9c27b0" in style)


class TestHierarchyToolsWidget:
    """Test main hierarchy tools widget integration"""
    
    def test_initialization(self, qapp, mock_state_manager, mock_event_bus):
        """Test main widget initialization"""
        widget = HierarchyToolsWidget(mock_state_manager, mock_event_bus)
        
        assert widget.state_manager == mock_state_manager
        assert widget.event_bus == mock_event_bus
        assert widget.hierarchy is None
        
        # Check components
        assert hasattr(widget, 'tree_widget')
        assert hasattr(widget, 'control_panel')
        assert hasattr(widget, 'metrics_widget')
        assert hasattr(widget, 'validation_text')
        assert isinstance(widget.tree_widget, HierarchyTreeWidget)
        assert isinstance(widget.control_panel, HierarchyControlPanel)
        assert isinstance(widget.metrics_widget, HierarchyMetricsWidget)
    
    def test_load_hierarchy(self, qapp, mock_state_manager, mock_event_bus, sample_hierarchy):
        """Test hierarchy loading"""
        widget = HierarchyToolsWidget(mock_state_manager, mock_event_bus)
        widget.load_hierarchy(sample_hierarchy)
        
        assert widget.hierarchy == sample_hierarchy
        assert widget.tree_widget.hierarchy == sample_hierarchy
        
        # Metrics should be calculated
        assert widget.metrics_widget.metrics.total_elements > 0
    
    def test_metrics_calculation(self, qapp, mock_state_manager, mock_event_bus, sample_hierarchy):
        """Test metrics calculation"""
        widget = HierarchyToolsWidget(mock_state_manager, mock_event_bus)
        
        metrics = widget._calculate_metrics(sample_hierarchy)
        
        assert metrics.total_elements == len(sample_hierarchy.elements)
        assert metrics.depth_levels >= 0
        assert metrics.orphaned_elements >= 0
        assert metrics.validation_errors >= 0
        assert isinstance(metrics.last_updated, datetime)
    
    def test_validation_feedback_update(self, qapp, mock_state_manager, mock_event_bus, sample_hierarchy):
        """Test validation feedback update"""
        widget = HierarchyToolsWidget(mock_state_manager, mock_event_bus)
        widget.load_hierarchy(sample_hierarchy)
        
        # Check validation text was updated
        validation_text = widget.validation_text.toPlainText()
        assert len(validation_text) > 0
        assert ("validation" in validation_text.lower() or 
                "hierarchy" in validation_text.lower())
    
    def test_event_handling(self, qapp, mock_state_manager, mock_event_bus):
        """Test event bus integration"""
        widget = HierarchyToolsWidget(mock_state_manager, mock_event_bus)
        
        # Check event subscriptions
        mock_event_bus.subscribe.assert_any_call("hierarchy_updated", widget._on_hierarchy_updated)
        mock_event_bus.subscribe.assert_any_call("elements_changed", widget._on_elements_changed)
    
    def test_hierarchy_change_handling(self, qapp, mock_state_manager, mock_event_bus, sample_hierarchy):
        """Test hierarchy change event handling"""
        widget = HierarchyToolsWidget(mock_state_manager, mock_event_bus)
        widget.load_hierarchy(sample_hierarchy)
        
        # Simulate hierarchy change
        widget._on_hierarchy_changed("element-1", "indent")
        
        # Should emit state change event
        mock_event_bus.emit.assert_called_with("hierarchy_modified", {
            "element_id": "element-1",
            "operation": "indent"
        })
    
    def test_signal_emissions(self, qapp, mock_state_manager, mock_event_bus, sample_hierarchy):
        """Test signal emissions"""
        widget = HierarchyToolsWidget(mock_state_manager, mock_event_bus)
        widget.load_hierarchy(sample_hierarchy)
        
        # Mock signal handlers
        element_selected_handler = Mock()
        hierarchy_modified_handler = Mock()
        
        widget.element_selected.connect(element_selected_handler)
        widget.hierarchy_modified.connect(hierarchy_modified_handler)
        
        # Trigger selection change
        widget._on_selection_changed(["root-1"])
        element_selected_handler.assert_called_once_with("root-1")
        
        # Trigger hierarchy change
        widget._on_hierarchy_changed("element-1", "test_operation")
        hierarchy_modified_handler.assert_called_once()
        
        # Check call arguments
        call_args = hierarchy_modified_handler.call_args[0][0]
        assert call_args["element_id"] == "element-1"
        assert call_args["operation"] == "test_operation"
        assert "timestamp" in call_args
    
    def test_operation_handling(self, qapp, mock_state_manager, mock_event_bus, sample_hierarchy):
        """Test operation request handling"""
        widget = HierarchyToolsWidget(mock_state_manager, mock_event_bus)
        widget.load_hierarchy(sample_hierarchy)
        
        # Simulate operation request
        element_ids = ["element-1"]
        widget._on_operation_requested(HierarchyOperation.INDENT, element_ids)
        
        # Should trigger tree widget operation
        # This would require more complex mocking to verify
        # For now, just ensure no exceptions are raised
    
    def test_empty_hierarchy_handling(self, qapp, mock_state_manager, mock_event_bus):
        """Test handling of empty hierarchy"""
        widget = HierarchyToolsWidget(mock_state_manager, mock_event_bus)
        
        # Test loading None hierarchy
        widget.load_hierarchy(None)
        assert widget.hierarchy is None
        
        # Test loading empty hierarchy
        empty_hierarchy = ElementHierarchy([])
        widget.load_hierarchy(empty_hierarchy)
        assert widget.hierarchy == empty_hierarchy
        
        # Metrics should be calculated safely
        metrics = widget._calculate_metrics(empty_hierarchy)
        assert metrics.total_elements == 0


class TestIntegration:
    """Integration tests for hierarchy tools"""
    
    def test_component_communication(self, qapp, mock_state_manager, mock_event_bus, sample_hierarchy):
        """Test communication between components"""
        widget = HierarchyToolsWidget(mock_state_manager, mock_event_bus)
        widget.load_hierarchy(sample_hierarchy)
        
        # Test tree selection affecting control panel
        element_ids = ["root-1"]
        widget.tree_widget.select_elements(element_ids)
        
        # Control panel should update
        assert widget.control_panel.selected_elements == element_ids
        
        # Buttons should be enabled
        assert widget.control_panel.indent_btn.isEnabled()
    
    def test_metrics_update_on_changes(self, qapp, mock_state_manager, mock_event_bus, sample_hierarchy):
        """Test metrics update when hierarchy changes"""
        widget = HierarchyToolsWidget(mock_state_manager, mock_event_bus)
        widget.load_hierarchy(sample_hierarchy)
        
        initial_metrics = widget.metrics_widget.metrics
        initial_updated = initial_metrics.last_updated
        
        # Simulate hierarchy change
        widget._on_hierarchy_changed("element-1", "delete")
        
        # Metrics should be recalculated
        updated_metrics = widget.metrics_widget.metrics
        assert updated_metrics.last_updated >= initial_updated
    
    def test_validation_feedback_integration(self, qapp, mock_state_manager, mock_event_bus, sample_hierarchy):
        """Test validation feedback system"""
        widget = HierarchyToolsWidget(mock_state_manager, mock_event_bus)
        widget.load_hierarchy(sample_hierarchy)
        
        # Trigger validation on tree
        widget.tree_widget._validate_hierarchy()
        
        # Validation cache should be populated
        assert len(widget.tree_widget.validation_cache) > 0
        
        # Tree items should have validation status
        for element_id, item in widget.tree_widget.element_items.items():
            validation_level = item.data(0, Qt.ItemDataRole.UserRole + 1)
            if validation_level:
                assert isinstance(validation_level, ValidationLevel)
    
    def test_end_to_end_workflow(self, qapp, mock_state_manager, mock_event_bus, sample_hierarchy):
        """Test complete workflow from load to operation"""
        widget = HierarchyToolsWidget(mock_state_manager, mock_event_bus)
        
        # Load hierarchy
        widget.load_hierarchy(sample_hierarchy)
        assert widget.hierarchy == sample_hierarchy
        
        # Select elements
        element_ids = ["child-1"]
        widget.tree_widget.select_elements(element_ids)
        assert widget.control_panel.selected_elements == element_ids
        
        # Perform operation
        with patch.object(widget.tree_widget, 'perform_operation') as mock_perform:
            widget.control_panel._request_operation(HierarchyOperation.INDENT)
            mock_perform.assert_called_once_with(HierarchyOperation.INDENT, element_ids)
        
        # Check metrics were calculated
        assert widget.metrics_widget.metrics.total_elements > 0


# Performance tests
class TestPerformance:
    """Performance tests for hierarchy tools"""
    
    def test_large_hierarchy_loading(self, qapp, mock_state_manager, mock_event_bus):
        """Test performance with large hierarchy"""
        # Create large hierarchy
        elements = []
        for i in range(100):
            element = Element(
                element_id=f"element-{i}",
                element_type=ElementType.TEXT,
                text=f"Element {i} text content",
                parent_id=f"element-{i//10}" if i > 9 else None
            )
            elements.append(element)
        
        hierarchy = ElementHierarchy(elements)
        
        widget = HierarchyToolsWidget(mock_state_manager, mock_event_bus)
        
        # Time the loading operation
        import time
        start_time = time.time()
        widget.load_hierarchy(hierarchy)
        end_time = time.time()
        
        # Should load reasonably quickly (< 1 second for 100 elements)
        assert (end_time - start_time) < 1.0
        assert widget.tree_widget.hierarchy == hierarchy
        assert len(widget.tree_widget.element_items) == 100
    
    def test_metrics_calculation_performance(self, qapp, mock_state_manager, mock_event_bus):
        """Test metrics calculation performance"""
        # Create hierarchy with complex structure
        elements = []
        for i in range(500):
            parent_id = f"element-{i//5}" if i > 4 else None
            element = Element(
                element_id=f"element-{i}",
                element_type=ElementType.TEXT,
                text=f"Element {i}",
                parent_id=parent_id
            )
            elements.append(element)
        
        hierarchy = ElementHierarchy(elements)
        widget = HierarchyToolsWidget(mock_state_manager, mock_event_bus)
        
        import time
        start_time = time.time()
        metrics = widget._calculate_metrics(hierarchy)
        end_time = time.time()
        
        # Metrics calculation should be fast
        assert (end_time - start_time) < 0.5
        assert metrics.total_elements == 500
    
    def test_tree_update_performance(self, qapp, mock_state_manager, mock_event_bus):
        """Test tree update performance"""
        # Create moderate hierarchy
        elements = []
        for i in range(50):
            element = Element(
                element_id=f"element-{i}",
                element_type=ElementType.TEXT,
                text=f"Element {i}",
                parent_id=f"element-{i//10}" if i > 9 else None
            )
            elements.append(element)
        
        hierarchy = ElementHierarchy(elements)
        widget = HierarchyToolsWidget(mock_state_manager, mock_event_bus)
        
        # Time multiple loads
        import time
        start_time = time.time()
        for _ in range(10):
            widget.load_hierarchy(hierarchy)
        end_time = time.time()
        
        # Should handle multiple updates efficiently
        assert (end_time - start_time) < 2.0


# Error handling tests
class TestErrorHandling:
    """Test error handling in hierarchy tools"""
    
    def test_invalid_hierarchy_handling(self, qapp, mock_state_manager, mock_event_bus):
        """Test handling of invalid hierarchy"""
        widget = HierarchyToolsWidget(mock_state_manager, mock_event_bus)
        
        # Test loading None hierarchy
        widget.load_hierarchy(None)
        assert widget.hierarchy is None
        
        # Test loading empty hierarchy
        empty_hierarchy = ElementHierarchy([])
        widget.load_hierarchy(empty_hierarchy)
        assert widget.hierarchy == empty_hierarchy
    
    def test_operation_error_handling(self, qapp, mock_state_manager, mock_event_bus, sample_hierarchy):
        """Test error handling in operations"""
        tree = HierarchyTreeWidget(mock_state_manager, mock_event_bus)
        tree.load_hierarchy(sample_hierarchy)
        
        # Test operation with invalid element IDs
        invalid_ids = ["non-existent-1", "non-existent-2"]
        
        # Should not crash
        tree.perform_operation(HierarchyOperation.INDENT, invalid_ids)
        tree.perform_operation(HierarchyOperation.DELETE, invalid_ids)
    
    def test_context_menu_error_handling(self, qapp, mock_state_manager, mock_event_bus):
        """Test context menu error handling"""
        tree = HierarchyTreeWidget(mock_state_manager, mock_event_bus)
        
        # Test context menu with no item at position
        tree._show_context_menu(QPoint(10, 10))  # Should not crash
        
        # Test with no hierarchy loaded
        assert tree.hierarchy is None
        tree._show_context_menu(QPoint(10, 10))  # Should not crash
    
    def test_validation_error_handling(self, qapp, mock_state_manager, mock_event_bus):
        """Test validation error handling"""
        tree = HierarchyTreeWidget(mock_state_manager, mock_event_bus)
        
        # Test validation with no hierarchy
        tree._validate_hierarchy()  # Should not crash
        
        # Test element validation with invalid ID
        tree._validate_element("non-existent-id")  # Should not crash


if __name__ == '__main__':
    pytest.main([__file__, '-v'])