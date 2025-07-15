"""Tests for Rollback Management System

Comprehensive test suite for rollback functionality including:
- Transaction rollback with operation history
- Undo/redo capabilities for bulk operations
- State restoration and data recovery
- Error handling and consistency checks
- Performance optimization for rollback operations
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, List, Any

from torematrix.core.operations.type_management.rollback import (
    RollbackManager, RollbackOperation, RollbackAction, RollbackResult,
    RollbackState, OperationType
)


class TestOperationType:
    """Test OperationType enum"""
    
    def test_operation_types(self):
        """Test all operation type values"""
        assert OperationType.BULK_CHANGE.value == "bulk_change"
        assert OperationType.TYPE_CONVERSION.value == "type_conversion"
        assert OperationType.PROPERTY_UPDATE.value == "property_update"
        assert OperationType.METADATA_CHANGE.value == "metadata_change"
        assert OperationType.STRUCTURE_CHANGE.value == "structure_change"


class TestRollbackState:
    """Test RollbackState enum"""
    
    def test_rollback_states(self):
        """Test all rollback state values"""
        assert RollbackState.PENDING.value == "pending"
        assert RollbackState.IN_PROGRESS.value == "in_progress"
        assert RollbackState.COMPLETED.value == "completed"
        assert RollbackState.FAILED.value == "failed"
        assert RollbackState.CANCELLED.value == "cancelled"


class TestRollbackAction:
    """Test RollbackAction data class"""
    
    def test_action_creation(self):
        """Test creating rollback action"""
        timestamp = datetime.now()
        action = RollbackAction(
            element_id="elem_001",
            operation_type=OperationType.TYPE_CONVERSION,
            previous_state={"type": "text", "content": "Hello"},
            new_state={"type": "title", "content": "HELLO"},
            timestamp=timestamp,
            metadata={"user": "admin", "batch": 1}
        )
        
        assert action.element_id == "elem_001"
        assert action.operation_type == OperationType.TYPE_CONVERSION
        assert action.previous_state == {"type": "text", "content": "Hello"}
        assert action.new_state == {"type": "title", "content": "HELLO"}
        assert action.timestamp == timestamp
        assert action.metadata == {"user": "admin", "batch": 1}
    
    def test_action_defaults(self):
        """Test default values for rollback action"""
        action = RollbackAction(
            element_id="elem_001",
            operation_type=OperationType.BULK_CHANGE
        )
        
        assert action.previous_state == {}
        assert action.new_state == {}
        assert action.timestamp is not None
        assert action.metadata == {}
    
    def test_action_serialization(self):
        """Test action serialization to dict"""
        action = RollbackAction(
            element_id="elem_001",
            operation_type=OperationType.TYPE_CONVERSION,
            previous_state={"type": "text"},
            new_state={"type": "title"}
        )
        
        data = action.to_dict()
        
        assert data["element_id"] == "elem_001"
        assert data["operation_type"] == "type_conversion"
        assert data["previous_state"] == {"type": "text"}
        assert data["new_state"] == {"type": "title"}
        assert "timestamp" in data
        assert data["metadata"] == {}
    
    def test_action_deserialization(self):
        """Test action deserialization from dict"""
        timestamp = datetime.now()
        data = {
            "element_id": "elem_001",
            "operation_type": "type_conversion",
            "previous_state": {"type": "text"},
            "new_state": {"type": "title"},
            "timestamp": timestamp.isoformat(),
            "metadata": {"user": "admin"}
        }
        
        action = RollbackAction.from_dict(data)
        
        assert action.element_id == "elem_001"
        assert action.operation_type == OperationType.TYPE_CONVERSION
        assert action.previous_state == {"type": "text"}
        assert action.new_state == {"type": "title"}
        assert action.metadata == {"user": "admin"}


class TestRollbackOperation:
    """Test RollbackOperation data class"""
    
    def test_operation_creation(self):
        """Test creating rollback operation"""
        timestamp = datetime.now()
        actions = [
            RollbackAction("elem_001", OperationType.TYPE_CONVERSION),
            RollbackAction("elem_002", OperationType.PROPERTY_UPDATE)
        ]
        
        operation = RollbackOperation(
            operation_id="rollback_001",
            original_operation_id="bulk_op_001",
            actions=actions,
            state=RollbackState.COMPLETED,
            created_at=timestamp,
            metadata={"reason": "user_request"}
        )
        
        assert operation.operation_id == "rollback_001"
        assert operation.original_operation_id == "bulk_op_001"
        assert operation.actions == actions
        assert operation.state == RollbackState.COMPLETED
        assert operation.created_at == timestamp
        assert operation.metadata == {"reason": "user_request"}
    
    def test_operation_defaults(self):
        """Test default values for rollback operation"""
        operation = RollbackOperation(
            operation_id="rollback_001",
            original_operation_id="bulk_op_001"
        )
        
        assert operation.actions == []
        assert operation.state == RollbackState.PENDING
        assert operation.created_at is not None
        assert operation.completed_at is None
        assert operation.error_message is None
        assert operation.metadata == {}
    
    def test_operation_duration(self):
        """Test operation duration calculation"""
        start_time = datetime.now() - timedelta(seconds=30)
        end_time = datetime.now()
        
        operation = RollbackOperation(
            operation_id="rollback_001",
            original_operation_id="bulk_op_001",
            created_at=start_time,
            completed_at=end_time
        )
        
        duration = operation.duration
        assert duration.total_seconds() >= 29
        assert duration.total_seconds() <= 31
    
    def test_operation_duration_not_completed(self):
        """Test duration when operation not completed"""
        operation = RollbackOperation(
            operation_id="rollback_001",
            original_operation_id="bulk_op_001"
        )
        
        duration = operation.duration
        assert duration.total_seconds() >= 0
    
    def test_operation_is_complete_true(self):
        """Test is_complete when operation finished"""
        operation = RollbackOperation(
            operation_id="rollback_001",
            original_operation_id="bulk_op_001",
            state=RollbackState.COMPLETED
        )
        
        assert operation.is_complete is True
    
    def test_operation_is_complete_false(self):
        """Test is_complete when operation in progress"""
        operation = RollbackOperation(
            operation_id="rollback_001",
            original_operation_id="bulk_op_001",
            state=RollbackState.IN_PROGRESS
        )
        
        assert operation.is_complete is False


class TestRollbackResult:
    """Test RollbackResult data class"""
    
    def test_result_creation(self):
        """Test creating rollback result"""
        result = RollbackResult(
            operation_id="rollback_001",
            success=True,
            restored_elements=["elem_001", "elem_002"],
            failed_elements=["elem_003"],
            errors=["Element elem_003 not found"],
            warnings=["Some metadata lost"],
            execution_time=5.5
        )
        
        assert result.operation_id == "rollback_001"
        assert result.success is True
        assert result.restored_elements == ["elem_001", "elem_002"]
        assert result.failed_elements == ["elem_003"]
        assert result.errors == ["Element elem_003 not found"]
        assert result.warnings == ["Some metadata lost"]
        assert result.execution_time == 5.5
    
    def test_result_defaults(self):
        """Test default values for rollback result"""
        result = RollbackResult(operation_id="rollback_001")
        
        assert result.success is False
        assert result.restored_elements == []
        assert result.failed_elements == []
        assert result.errors == []
        assert result.warnings == []
        assert result.execution_time == 0.0
    
    def test_result_success_rate(self):
        """Test success rate calculation"""
        result = RollbackResult(
            operation_id="rollback_001",
            restored_elements=["elem_001", "elem_002", "elem_003"],
            failed_elements=["elem_004"]
        )
        
        assert result.success_rate == 75.0  # 3 success out of 4 total
    
    def test_result_success_rate_no_elements(self):
        """Test success rate with no elements"""
        result = RollbackResult(operation_id="rollback_001")
        
        assert result.success_rate == 0.0
    
    def test_result_total_elements(self):
        """Test total elements calculation"""
        result = RollbackResult(
            operation_id="rollback_001",
            restored_elements=["elem_001", "elem_002"],
            failed_elements=["elem_003", "elem_004"]
        )
        
        assert result.total_elements == 4


class TestRollbackManager:
    """Test RollbackManager functionality"""
    
    @pytest.fixture
    def manager(self):
        """Create manager instance for testing"""
        return RollbackManager()
    
    def test_manager_initialization(self):
        """Test manager initialization"""
        manager = RollbackManager()
        
        assert manager.operations == {}
        assert manager.operation_history == {}
        assert manager._lock is not None
    
    def test_record_operation_action(self, manager):
        """Test recording operation action"""
        action = RollbackAction(
            element_id="elem_001",
            operation_type=OperationType.TYPE_CONVERSION,
            previous_state={"type": "text"},
            new_state={"type": "title"}
        )
        
        manager.record_operation_action("bulk_op_001", action)
        
        assert "bulk_op_001" in manager.operation_history
        assert len(manager.operation_history["bulk_op_001"]) == 1
        assert manager.operation_history["bulk_op_001"][0] == action
    
    def test_record_multiple_actions(self, manager):
        """Test recording multiple actions for same operation"""
        actions = [
            RollbackAction("elem_001", OperationType.TYPE_CONVERSION),
            RollbackAction("elem_002", OperationType.PROPERTY_UPDATE),
            RollbackAction("elem_003", OperationType.METADATA_CHANGE)
        ]
        
        for action in actions:
            manager.record_operation_action("bulk_op_001", action)
        
        assert len(manager.operation_history["bulk_op_001"]) == 3
        assert manager.operation_history["bulk_op_001"] == actions
    
    @pytest.mark.asyncio
    async def test_create_rollback_operation(self, manager):
        """Test creating rollback operation"""
        # Record some actions first
        actions = [
            RollbackAction("elem_001", OperationType.TYPE_CONVERSION),
            RollbackAction("elem_002", OperationType.PROPERTY_UPDATE)
        ]
        
        for action in actions:
            manager.record_operation_action("bulk_op_001", action)
        
        operation = await manager.create_rollback_operation("bulk_op_001")
        
        assert operation.original_operation_id == "bulk_op_001"
        assert len(operation.actions) == 2
        assert operation.state == RollbackState.PENDING
        assert operation.operation_id in manager.operations
    
    @pytest.mark.asyncio
    async def test_create_rollback_no_history(self, manager):
        """Test creating rollback for operation with no history"""
        with pytest.raises(ValueError, match="No recorded actions found"):
            await manager.create_rollback_operation("non_existent")
    
    @pytest.mark.asyncio
    async def test_execute_rollback_success(self, manager):
        """Test successful rollback execution"""
        # Setup mock element restoration
        manager._restore_element_state = AsyncMock(return_value=True)
        
        # Record actions
        actions = [
            RollbackAction("elem_001", OperationType.TYPE_CONVERSION, 
                         previous_state={"type": "text"}, new_state={"type": "title"}),
            RollbackAction("elem_002", OperationType.PROPERTY_UPDATE,
                         previous_state={"prop": "old"}, new_state={"prop": "new"})
        ]
        
        for action in actions:
            manager.record_operation_action("bulk_op_001", action)
        
        # Create and execute rollback
        operation = await manager.create_rollback_operation("bulk_op_001")
        result = await manager.execute_rollback(operation.operation_id)
        
        assert result.success is True
        assert len(result.restored_elements) == 2
        assert len(result.failed_elements) == 0
        assert "elem_001" in result.restored_elements
        assert "elem_002" in result.restored_elements
        
        # Check operation state
        updated_operation = manager.get_rollback_operation(operation.operation_id)
        assert updated_operation.state == RollbackState.COMPLETED
        assert updated_operation.completed_at is not None
    
    @pytest.mark.asyncio
    async def test_execute_rollback_partial_failure(self, manager):
        """Test rollback execution with partial failures"""
        # Setup mock with some failures
        async def mock_restore(element_id, state):
            return element_id != "elem_002"  # elem_002 fails
        
        manager._restore_element_state = mock_restore
        
        # Record actions
        actions = [
            RollbackAction("elem_001", OperationType.TYPE_CONVERSION),
            RollbackAction("elem_002", OperationType.TYPE_CONVERSION),  # This will fail
            RollbackAction("elem_003", OperationType.PROPERTY_UPDATE)
        ]
        
        for action in actions:
            manager.record_operation_action("bulk_op_001", action)
        
        # Execute rollback
        operation = await manager.create_rollback_operation("bulk_op_001")
        result = await manager.execute_rollback(operation.operation_id)
        
        assert result.success is False  # Overall failure due to partial failure
        assert len(result.restored_elements) == 2
        assert len(result.failed_elements) == 1
        assert "elem_001" in result.restored_elements
        assert "elem_003" in result.restored_elements
        assert "elem_002" in result.failed_elements
        assert result.success_rate == 66.67  # 2/3 success
    
    @pytest.mark.asyncio
    async def test_execute_rollback_not_found(self, manager):
        """Test executing non-existent rollback"""
        with pytest.raises(ValueError, match="Rollback operation 'non_existent' not found"):
            await manager.execute_rollback("non_existent")
    
    def test_get_rollback_operation_exists(self, manager):
        """Test getting existing rollback operation"""
        operation = RollbackOperation("rollback_001", "bulk_op_001")
        manager.operations["rollback_001"] = operation
        
        retrieved = manager.get_rollback_operation("rollback_001")
        assert retrieved == operation
    
    def test_get_rollback_operation_not_exists(self, manager):
        """Test getting non-existent rollback operation"""
        result = manager.get_rollback_operation("non_existent")
        assert result is None
    
    def test_list_rollback_operations(self, manager):
        """Test listing rollback operations"""
        operations = [
            RollbackOperation("rollback_001", "bulk_op_001"),
            RollbackOperation("rollback_002", "bulk_op_002"),
            RollbackOperation("rollback_003", "bulk_op_003")
        ]
        
        for op in operations:
            manager.operations[op.operation_id] = op
        
        listed = manager.list_rollback_operations()
        
        assert len(listed) == 3
        for op in operations:
            assert op in listed
    
    def test_list_rollback_operations_for_original(self, manager):
        """Test listing rollback operations for specific original operation"""
        operations = [
            RollbackOperation("rollback_001", "bulk_op_001"),
            RollbackOperation("rollback_002", "bulk_op_001"),  # Same original
            RollbackOperation("rollback_003", "bulk_op_002")   # Different original
        ]
        
        for op in operations:
            manager.operations[op.operation_id] = op
        
        listed = manager.list_rollback_operations("bulk_op_001")
        
        assert len(listed) == 2
        assert all(op.original_operation_id == "bulk_op_001" for op in listed)
    
    def test_can_rollback_true(self, manager):
        """Test can_rollback returns True when history exists"""
        action = RollbackAction("elem_001", OperationType.TYPE_CONVERSION)
        manager.record_operation_action("bulk_op_001", action)
        
        assert manager.can_rollback("bulk_op_001") is True
    
    def test_can_rollback_false(self, manager):
        """Test can_rollback returns False when no history"""
        assert manager.can_rollback("bulk_op_001") is False
    
    def test_clear_operation_history(self, manager):
        """Test clearing operation history"""
        # Record some actions
        actions = [
            RollbackAction("elem_001", OperationType.TYPE_CONVERSION),
            RollbackAction("elem_002", OperationType.PROPERTY_UPDATE)
        ]
        
        for action in actions:
            manager.record_operation_action("bulk_op_001", action)
        
        assert len(manager.operation_history["bulk_op_001"]) == 2
        
        manager.clear_operation_history("bulk_op_001")
        
        assert "bulk_op_001" not in manager.operation_history
    
    def test_get_operation_history_exists(self, manager):
        """Test getting operation history that exists"""
        actions = [
            RollbackAction("elem_001", OperationType.TYPE_CONVERSION),
            RollbackAction("elem_002", OperationType.PROPERTY_UPDATE)
        ]
        
        for action in actions:
            manager.record_operation_action("bulk_op_001", action)
        
        history = manager.get_operation_history("bulk_op_001")
        
        assert len(history) == 2
        assert history == actions
    
    def test_get_operation_history_not_exists(self, manager):
        """Test getting operation history that doesn't exist"""
        history = manager.get_operation_history("non_existent")
        assert history == []
    
    @pytest.mark.asyncio
    async def test_rollback_statistics(self, manager):
        """Test getting rollback statistics"""
        # Create some rollback operations
        operations = [
            RollbackOperation("rollback_001", "bulk_op_001", state=RollbackState.COMPLETED),
            RollbackOperation("rollback_002", "bulk_op_002", state=RollbackState.COMPLETED),
            RollbackOperation("rollback_003", "bulk_op_003", state=RollbackState.FAILED),
            RollbackOperation("rollback_004", "bulk_op_004", state=RollbackState.IN_PROGRESS)
        ]
        
        for op in operations:
            manager.operations[op.operation_id] = op
        
        stats = manager.get_rollback_statistics()
        
        assert stats["total_rollbacks"] == 4
        assert stats["completed_rollbacks"] == 2
        assert stats["failed_rollbacks"] == 1
        assert stats["in_progress_rollbacks"] == 1
        assert stats["success_rate"] == 50.0  # 2/4 completed
    
    @pytest.mark.asyncio
    async def test_concurrent_rollback_operations(self, manager):
        """Test concurrent rollback operations"""
        import asyncio
        
        # Setup mock restoration
        async def mock_restore(element_id, state):
            await asyncio.sleep(0.01)  # Simulate work
            return True
        
        manager._restore_element_state = mock_restore
        
        # Record actions for multiple operations
        for op_id in ["bulk_op_001", "bulk_op_002", "bulk_op_003"]:
            for i in range(5):
                action = RollbackAction(f"elem_{op_id}_{i}", OperationType.TYPE_CONVERSION)
                manager.record_operation_action(op_id, action)
        
        # Create rollback operations
        rollback_ops = []
        for op_id in ["bulk_op_001", "bulk_op_002", "bulk_op_003"]:
            rollback_op = await manager.create_rollback_operation(op_id)
            rollback_ops.append(rollback_op)
        
        # Execute rollbacks concurrently
        tasks = [
            manager.execute_rollback(op.operation_id) 
            for op in rollback_ops
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Verify results
        assert len(results) == 3
        for result in results:
            assert result.success is True
            assert len(result.restored_elements) == 5
            assert len(result.failed_elements) == 0
        
        # Verify all operations completed
        for op in rollback_ops:
            final_op = manager.get_rollback_operation(op.operation_id)
            assert final_op.state == RollbackState.COMPLETED


class TestRollbackIntegration:
    """Integration tests for rollback system"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_rollback_workflow(self):
        """Test complete rollback workflow"""
        manager = RollbackManager()
        
        # Mock element restoration
        async def mock_restore(element_id, state):
            # Simulate successful restoration
            return True
        
        manager._restore_element_state = mock_restore
        
        # Simulate a bulk operation that changes multiple elements
        original_operation_id = "bulk_change_20241215_001"
        
        # Record the actions that were performed
        actions = [
            RollbackAction(
                element_id="elem_001",
                operation_type=OperationType.TYPE_CONVERSION,
                previous_state={"type": "text", "content": "Hello"},
                new_state={"type": "title", "content": "HELLO"},
                metadata={"user": "admin", "reason": "bulk_conversion"}
            ),
            RollbackAction(
                element_id="elem_002",
                operation_type=OperationType.PROPERTY_UPDATE,
                previous_state={"font_size": "12px", "color": "black"},
                new_state={"font_size": "18px", "color": "blue"},
                metadata={"user": "admin", "reason": "style_update"}
            ),
            RollbackAction(
                element_id="elem_003",
                operation_type=OperationType.METADATA_CHANGE,
                previous_state={"tags": ["text"], "importance": "low"},
                new_state={"tags": ["title", "heading"], "importance": "high"},
                metadata={"user": "admin", "reason": "metadata_enhancement"}
            )
        ]
        
        # Record all actions
        for action in actions:
            manager.record_operation_action(original_operation_id, action)
        
        # Verify we can rollback
        assert manager.can_rollback(original_operation_id) is True
        
        # Get operation history
        history = manager.get_operation_history(original_operation_id)
        assert len(history) == 3
        
        # Create rollback operation
        rollback_operation = await manager.create_rollback_operation(original_operation_id)
        
        assert rollback_operation.original_operation_id == original_operation_id
        assert len(rollback_operation.actions) == 3
        assert rollback_operation.state == RollbackState.PENDING
        
        # Execute rollback
        result = await manager.execute_rollback(rollback_operation.operation_id)
        
        # Verify rollback result
        assert result.success is True
        assert len(result.restored_elements) == 3
        assert len(result.failed_elements) == 0
        assert result.success_rate == 100.0
        assert "elem_001" in result.restored_elements
        assert "elem_002" in result.restored_elements
        assert "elem_003" in result.restored_elements
        
        # Verify rollback operation state
        final_operation = manager.get_rollback_operation(rollback_operation.operation_id)
        assert final_operation.state == RollbackState.COMPLETED
        assert final_operation.completed_at is not None
        assert final_operation.is_complete is True
        
        # Verify statistics
        stats = manager.get_rollback_statistics()
        assert stats["total_rollbacks"] == 1
        assert stats["completed_rollbacks"] == 1
        assert stats["failed_rollbacks"] == 0
        assert stats["success_rate"] == 100.0
        
        # Test that we can list the rollback operation
        rollback_ops = manager.list_rollback_operations(original_operation_id)
        assert len(rollback_ops) == 1
        assert rollback_ops[0].operation_id == rollback_operation.operation_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])