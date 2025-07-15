"""Tests for batch editing functionality"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QThread

from torematrix.ui.components.property_panel.batch_editing import (
    BatchOperation,
    BatchEditContext,
    BatchEditWorker,
    BatchEditingPanel,
    BatchPreviewDialog
)
from torematrix.ui.components.property_panel.events import PropertyNotificationCenter


@pytest.fixture
def qt_app():
    """Create QApplication instance for testing"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def notification_center():
    """Create notification center"""
    return PropertyNotificationCenter()


@pytest.fixture
def batch_panel(qt_app, notification_center):
    """Create batch editing panel"""
    panel = BatchEditingPanel(notification_center)
    panel.show()
    return panel


class TestBatchOperation:
    """Test batch operation data class"""
    
    def test_initialization(self):
        """Test batch operation initialization"""
        operation = BatchOperation(
            property_name="test_prop",
            operation_type="set",
            new_value="test_value",
            target_elements=["elem1", "elem2"]
        )
        
        assert operation.property_name == "test_prop"
        assert operation.operation_type == "set"
        assert operation.new_value == "test_value"
        assert operation.target_elements == ["elem1", "elem2"]
    
    def test_can_apply_to_element(self):
        """Test element application check"""
        operation = BatchOperation(
            property_name="test_prop",
            operation_type="set",
            new_value="test_value",
            target_elements=["elem1", "elem2"]
        )
        
        # Element in target list
        assert operation.can_apply_to_element("elem1", "current_value")
        
        # Element not in target list
        assert not operation.can_apply_to_element("elem3", "current_value")
    
    def test_condition_function(self):
        """Test condition function"""
        condition_func = lambda x: x == "specific_value"
        
        operation = BatchOperation(
            property_name="test_prop",
            operation_type="set",
            new_value="test_value",
            target_elements=["elem1"],
            condition_func=condition_func
        )
        
        # Condition met
        assert operation.can_apply_to_element("elem1", "specific_value")
        
        # Condition not met
        assert not operation.can_apply_to_element("elem1", "other_value")


class TestBatchEditContext:
    """Test batch edit context"""
    
    def test_initialization(self):
        """Test context initialization"""
        context = BatchEditContext(
            selected_elements=["elem1", "elem2"],
            common_properties={"prop1", "prop2"},
            property_summaries={
                "prop1": {"value_counts": {"value1": 1, "value2": 1}},
                "prop2": {"value_counts": {"value3": 2}}
            },
            total_elements=2
        )
        
        assert len(context.selected_elements) == 2
        assert len(context.common_properties) == 2
        assert context.total_elements == 2
    
    def test_property_value_counts(self):
        """Test property value counts"""
        context = BatchEditContext(
            selected_elements=["elem1", "elem2"],
            common_properties={"prop1"},
            property_summaries={
                "prop1": {"value_counts": {"value1": 1, "value2": 1}}
            },
            total_elements=2
        )
        
        counts = context.get_property_value_counts("prop1")
        assert counts == {"value1": 1, "value2": 1}
        
        # Non-existent property
        counts = context.get_property_value_counts("nonexistent")
        assert counts == {}
    
    def test_is_property_uniform(self):
        """Test property uniformity check"""
        context = BatchEditContext(
            selected_elements=["elem1", "elem2"],
            common_properties={"uniform_prop", "varied_prop"},
            property_summaries={
                "uniform_prop": {"value_counts": {"same_value": 2}},
                "varied_prop": {"value_counts": {"value1": 1, "value2": 1}}
            },
            total_elements=2
        )
        
        assert context.is_property_uniform("uniform_prop")
        assert not context.is_property_uniform("varied_prop")


class TestBatchEditWorker:
    """Test batch edit worker"""
    
    def test_initialization(self):
        """Test worker initialization"""
        worker = BatchEditWorker()
        assert worker.operations == []
        assert worker.property_manager is None
        assert not worker.cancel_requested
    
    def test_add_clear_operations(self):
        """Test adding and clearing operations"""
        worker = BatchEditWorker()
        
        operation = BatchOperation(
            property_name="test_prop",
            operation_type="set",
            new_value="test_value",
            target_elements=["elem1"]
        )
        
        worker.add_operation(operation)
        assert len(worker.operations) == 1
        
        worker.clear_operations()
        assert len(worker.operations) == 0
    
    def test_calculate_new_value(self):
        """Test new value calculation"""
        worker = BatchEditWorker()
        
        # Set operation
        operation = BatchOperation("prop", "set", "new_value", [])
        new_value = worker._calculate_new_value(operation, "old_value")
        assert new_value == "new_value"
        
        # Append operation (string)
        operation = BatchOperation("prop", "append", "_suffix", [])
        new_value = worker._calculate_new_value(operation, "prefix")
        assert new_value == "prefix_suffix"
        
        # Append operation (list)
        operation = BatchOperation("prop", "append", "item3", [])
        new_value = worker._calculate_new_value(operation, ["item1", "item2"])
        assert new_value == ["item1", "item2", "item3"]
        
        # Clear operation
        operation = BatchOperation("prop", "clear", None, [])
        new_value = worker._calculate_new_value(operation, "some_value")
        assert new_value == ""


class TestBatchEditingPanel:
    """Test batch editing panel"""
    
    def test_initialization(self, batch_panel):
        """Test panel initialization"""
        assert batch_panel.selected_elements == []
        assert batch_panel.batch_context is None
        assert batch_panel.pending_operations == []
    
    def test_set_selected_elements(self, batch_panel):
        """Test setting selected elements"""
        # Mock property manager
        mock_manager = Mock()
        mock_manager.get_element_properties.return_value = {
            "prop1": "value1",
            "prop2": "value2"
        }
        batch_panel.set_property_manager(mock_manager)
        
        # Set elements
        element_ids = ["elem1", "elem2"]
        batch_panel.set_selected_elements(element_ids)
        
        assert batch_panel.selected_elements == element_ids
        assert batch_panel.batch_context is not None
        assert batch_panel.batch_context.total_elements == 2
    
    def test_update_batch_context(self, batch_panel):
        """Test batch context update"""
        # Mock property manager
        mock_manager = Mock()
        mock_manager.get_element_properties.side_effect = [
            {"prop1": "value1", "prop2": "value2"},
            {"prop1": "value1", "prop3": "value3"}
        ]
        batch_panel.set_property_manager(mock_manager)
        
        # Set elements
        batch_panel.selected_elements = ["elem1", "elem2"]
        batch_panel._update_batch_context()
        
        assert batch_panel.batch_context is not None
        # Common properties should be intersection
        assert "prop1" in batch_panel.batch_context.common_properties
        assert "prop2" not in batch_panel.batch_context.common_properties
        assert "prop3" not in batch_panel.batch_context.common_properties
    
    def test_collect_operations(self, batch_panel):
        """Test operation collection"""
        # Setup mock context
        batch_panel.selected_elements = ["elem1", "elem2"]
        batch_panel.batch_context = BatchEditContext(
            selected_elements=["elem1", "elem2"],
            common_properties={"prop1"},
            property_summaries={},
            total_elements=2
        )
        
        # Mock editor widget in layout
        mock_editor = Mock()
        mock_editor.get_value.return_value = "new_value"
        mock_editor.property.return_value = "prop1"
        
        # Mock group widget
        mock_group = Mock()
        mock_group.findChildren.return_value = [mock_editor]
        
        # Mock layout
        mock_layout_item = Mock()
        mock_layout_item.widget.return_value = mock_group
        batch_panel.editor_layout = Mock()
        batch_panel.editor_layout.count.return_value = 1
        batch_panel.editor_layout.itemAt.return_value = mock_layout_item
        
        operations = batch_panel._collect_operations()
        assert len(operations) == 1
        assert operations[0].property_name == "prop1"
        assert operations[0].new_value == "new_value"
    
    def test_worker_connections(self, batch_panel):
        """Test worker signal connections"""
        # Test that worker signals are connected
        worker = batch_panel.worker
        
        # Mock slots
        batch_panel._on_progress_updated = Mock()
        batch_panel._on_operation_completed = Mock()
        batch_panel._on_batch_completed = Mock()
        batch_panel._on_error_occurred = Mock()
        
        # Reconnect signals to mocks
        worker.progress_updated.connect(batch_panel._on_progress_updated)
        worker.operation_completed.connect(batch_panel._on_operation_completed)
        worker.batch_completed.connect(batch_panel._on_batch_completed)
        worker.error_occurred.connect(batch_panel._on_error_occurred)
        
        # Emit signals
        worker.progress_updated.emit(50, "Test progress")
        worker.operation_completed.emit("op1", True, "Success")
        worker.batch_completed.emit({"total": 1, "successful": 1})
        worker.error_occurred.emit("elem1", "Test error")
        
        # Verify calls
        batch_panel._on_progress_updated.assert_called_once_with(50, "Test progress")
        batch_panel._on_operation_completed.assert_called_once_with("op1", True, "Success")
        batch_panel._on_batch_completed.assert_called_once_with({"total": 1, "successful": 1})
        batch_panel._on_error_occurred.assert_called_once_with("elem1", "Test error")


class TestBatchPreviewDialog:
    """Test batch preview dialog"""
    
    def test_initialization(self, qt_app):
        """Test dialog initialization"""
        operations = [
            BatchOperation("prop1", "set", "value1", ["elem1"]),
            BatchOperation("prop2", "set", "value2", ["elem2"])
        ]
        
        context = BatchEditContext(
            selected_elements=["elem1", "elem2"],
            common_properties={"prop1", "prop2"},
            property_summaries={},
            total_elements=2
        )
        
        dialog = BatchPreviewDialog(operations, context)
        dialog.show()
        
        assert dialog.operations == operations
        assert dialog.context == context
        assert dialog.windowTitle() == "Preview Batch Changes"


@pytest.mark.integration
class TestBatchEditingIntegration:
    """Integration tests for batch editing"""
    
    def test_complete_batch_workflow(self, batch_panel):
        """Test complete batch editing workflow"""
        # Setup mock property manager
        mock_manager = Mock()
        mock_manager.get_element_properties.return_value = {
            "test_prop": "old_value"
        }
        mock_manager.get_property_value.return_value = "old_value"
        batch_panel.set_property_manager(mock_manager)
        
        # Set selected elements
        element_ids = ["elem1", "elem2"]
        batch_panel.set_selected_elements(element_ids)
        
        # Verify context created
        assert batch_panel.batch_context is not None
        assert batch_panel.batch_context.total_elements == 2
        
        # Create mock operation
        operation = BatchOperation(
            property_name="test_prop",
            operation_type="set",
            new_value="new_value",
            target_elements=element_ids
        )
        
        # Test worker execution
        worker = batch_panel.worker
        worker.add_operation(operation)
        
        # Mock property manager for worker
        worker.set_property_manager(mock_manager)
        
        # Test operation execution
        success = worker._execute_operation(operation)
        
        # Should have attempted to set property values
        assert mock_manager.set_property_value.call_count == len(element_ids)