"""Tests for Bulk Type Operations Engine

Comprehensive test suite for bulk type operations including:
- Bulk type changes with various configurations
- Progress tracking and cancellation
- Error handling and rollback functionality
- Performance and memory optimization
- Thread safety verification
"""

import pytest
import asyncio
import threading
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from concurrent.futures import ThreadPoolExecutor

from torematrix.core.operations.type_management.bulk_operations import (
    BulkTypeOperationEngine, BulkOperationOptions, BulkOperationResult,
    BulkChangePreview, ElementChange, OperationStatus, ConflictResolution
)
from torematrix.core.models.types import TypeRegistry, TypeDefinition, ValidationResult
from torematrix.core.models.types.validation import TypeValidationEngine


class TestBulkOperationOptions:
    """Test BulkOperationOptions configuration"""
    
    def test_default_options(self):
        """Test default option values"""
        options = BulkOperationOptions()
        
        assert options.batch_size == 1000
        assert options.max_workers == 4
        assert options.validate_before is True
        assert options.preserve_metadata is True
        assert options.track_changes is True
        assert options.conflict_resolution == ConflictResolution.SKIP
        assert options.timeout_seconds is None
        assert options.rollback_on_error is True
        assert options.dry_run is False
        assert options.progress_callback is None
    
    def test_custom_options(self):
        """Test custom option configuration"""
        def progress_callback(current, total):
            pass
        
        options = BulkOperationOptions(
            batch_size=500,
            max_workers=8,
            validate_before=False,
            preserve_metadata=False,
            track_changes=False,
            conflict_resolution=ConflictResolution.OVERWRITE,
            timeout_seconds=300,
            rollback_on_error=False,
            dry_run=True,
            progress_callback=progress_callback
        )
        
        assert options.batch_size == 500
        assert options.max_workers == 8
        assert options.validate_before is False
        assert options.preserve_metadata is False
        assert options.track_changes is False
        assert options.conflict_resolution == ConflictResolution.OVERWRITE
        assert options.timeout_seconds == 300
        assert options.rollback_on_error is False
        assert options.dry_run is True
        assert options.progress_callback == progress_callback


class TestElementChange:
    """Test ElementChange data class"""
    
    def test_element_change_creation(self):
        """Test creating element change record"""
        timestamp = datetime.now()
        change = ElementChange(
            element_id="elem_001",
            old_type="text",
            new_type="title",
            timestamp=timestamp,
            metadata_changes={"font_size": "16px"},
            data_preserved=True,
            warnings=["Minor formatting loss"]
        )
        
        assert change.element_id == "elem_001"
        assert change.old_type == "text"
        assert change.new_type == "title"
        assert change.timestamp == timestamp
        assert change.metadata_changes == {"font_size": "16px"}
        assert change.data_preserved is True
        assert change.warnings == ["Minor formatting loss"]
    
    def test_element_change_defaults(self):
        """Test default values for ElementChange"""
        timestamp = datetime.now()
        change = ElementChange(
            element_id="elem_001",
            old_type="text",
            new_type="title",
            timestamp=timestamp
        )
        
        assert change.metadata_changes == {}
        assert change.data_preserved is True
        assert change.warnings == []


class TestBulkOperationResult:
    """Test BulkOperationResult data class"""
    
    def test_result_creation(self):
        """Test creating operation result"""
        start_time = datetime.now()
        result = BulkOperationResult(
            operation_id="op_001",
            status=OperationStatus.COMPLETED,
            total_elements=1000,
            processed_elements=1000,
            successful_changes=980,
            failed_changes=20,
            skipped_elements=0,
            warnings=["Some warnings"],
            errors=["Some errors"],
            changes=[],
            start_time=start_time
        )
        
        assert result.operation_id == "op_001"
        assert result.status == OperationStatus.COMPLETED
        assert result.total_elements == 1000
        assert result.processed_elements == 1000
        assert result.successful_changes == 980
        assert result.failed_changes == 20
        assert result.skipped_elements == 0
    
    def test_success_rate_calculation(self):
        """Test success rate calculation"""
        result = BulkOperationResult(
            operation_id="op_001",
            status=OperationStatus.COMPLETED,
            total_elements=1000,
            processed_elements=1000,
            successful_changes=980,
            failed_changes=20,
            skipped_elements=0,
            warnings=[],
            errors=[],
            changes=[],
            start_time=datetime.now()
        )
        
        assert result.success_rate == 98.0
    
    def test_success_rate_zero_processed(self):
        """Test success rate with zero processed elements"""
        result = BulkOperationResult(
            operation_id="op_001",
            status=OperationStatus.PENDING,
            total_elements=1000,
            processed_elements=0,
            successful_changes=0,
            failed_changes=0,
            skipped_elements=0,
            warnings=[],
            errors=[],
            changes=[],
            start_time=datetime.now()
        )
        
        assert result.success_rate == 0.0
    
    def test_is_complete_success(self):
        """Test is_complete for successful operation"""
        result = BulkOperationResult(
            operation_id="op_001",
            status=OperationStatus.COMPLETED,
            total_elements=1000,
            processed_elements=1000,
            successful_changes=1000,
            failed_changes=0,
            skipped_elements=0,
            warnings=[],
            errors=[],
            changes=[],
            start_time=datetime.now()
        )
        
        assert result.is_complete is True
    
    def test_is_complete_with_failures(self):
        """Test is_complete with failures"""
        result = BulkOperationResult(
            operation_id="op_001",
            status=OperationStatus.COMPLETED,
            total_elements=1000,
            processed_elements=1000,
            successful_changes=980,
            failed_changes=20,
            skipped_elements=0,
            warnings=[],
            errors=[],
            changes=[],
            start_time=datetime.now()
        )
        
        assert result.is_complete is False


class TestBulkChangePreview:
    """Test BulkChangePreview data class"""
    
    def test_preview_creation(self):
        """Test creating change preview"""
        preview = BulkChangePreview(
            target_type="title",
            total_elements=1000,
            valid_conversions=980,
            invalid_conversions=20,
            data_loss_risk=5,
            warnings=["Some warnings"],
            errors=[],
            estimated_duration=10.5,
            memory_estimate=1024000,
            affected_relationships={"parent_001", "child_002"}
        )
        
        assert preview.target_type == "title"
        assert preview.total_elements == 1000
        assert preview.valid_conversions == 980
        assert preview.invalid_conversions == 20
        assert preview.data_loss_risk == 5
        assert preview.estimated_duration == 10.5
        assert preview.memory_estimate == 1024000
        assert preview.affected_relationships == {"parent_001", "child_002"}
    
    def test_is_safe_true(self):
        """Test is_safe returns True for safe operations"""
        preview = BulkChangePreview(
            target_type="title",
            total_elements=1000,
            valid_conversions=1000,
            invalid_conversions=0,
            data_loss_risk=0,
            warnings=[],
            errors=[],
            estimated_duration=10.5,
            memory_estimate=1024000,
            affected_relationships=set()
        )
        
        assert preview.is_safe is True
    
    def test_is_safe_false_invalid_conversions(self):
        """Test is_safe returns False with invalid conversions"""
        preview = BulkChangePreview(
            target_type="title",
            total_elements=1000,
            valid_conversions=980,
            invalid_conversions=20,
            data_loss_risk=0,
            warnings=[],
            errors=[],
            estimated_duration=10.5,
            memory_estimate=1024000,
            affected_relationships=set()
        )
        
        assert preview.is_safe is False
    
    def test_is_safe_false_data_loss_risk(self):
        """Test is_safe returns False with data loss risk"""
        preview = BulkChangePreview(
            target_type="title",
            total_elements=1000,
            valid_conversions=1000,
            invalid_conversions=0,
            data_loss_risk=5,
            warnings=[],
            errors=[],
            estimated_duration=10.5,
            memory_estimate=1024000,
            affected_relationships=set()
        )
        
        assert preview.is_safe is False
    
    def test_is_safe_false_errors(self):
        """Test is_safe returns False with errors"""
        preview = BulkChangePreview(
            target_type="title",
            total_elements=1000,
            valid_conversions=1000,
            invalid_conversions=0,
            data_loss_risk=0,
            warnings=[],
            errors=["Some error"],
            estimated_duration=10.5,
            memory_estimate=1024000,
            affected_relationships=set()
        )
        
        assert preview.is_safe is False


class TestBulkTypeOperationEngine:
    """Test BulkTypeOperationEngine functionality"""
    
    @pytest.fixture
    def mock_registry(self):
        """Mock type registry"""
        registry = Mock(spec=TypeRegistry)
        registry.has_type.return_value = True
        registry.get_type.return_value = Mock(spec=TypeDefinition)
        return registry
    
    @pytest.fixture
    def mock_validator(self):
        """Mock validation engine"""
        validator = Mock(spec=TypeValidationEngine)
        return validator
    
    @pytest.fixture
    def engine(self, mock_registry, mock_validator):
        """Create engine instance for testing"""
        return BulkTypeOperationEngine(mock_registry, mock_validator, max_workers=2)
    
    def test_engine_initialization(self, mock_registry, mock_validator):
        """Test engine initialization"""
        engine = BulkTypeOperationEngine(mock_registry, mock_validator, max_workers=4)
        
        assert engine.registry == mock_registry
        assert engine.validator == mock_validator
        assert engine.max_workers == 4
        assert engine._operations == {}
        assert engine._cancel_events == {}
        assert engine._lock is not None
    
    def test_bulk_change_types_empty_list(self, engine):
        """Test bulk change with empty element list"""
        with pytest.raises(ValueError, match="Element IDs list cannot be empty"):
            engine.bulk_change_types([], "target_type")
    
    def test_bulk_change_types_invalid_target(self, engine, mock_registry):
        """Test bulk change with invalid target type"""
        mock_registry.has_type.return_value = False
        
        with pytest.raises(ValueError, match="Target type 'invalid_type' not found"):
            engine.bulk_change_types(["elem_001"], "invalid_type")
    
    def test_bulk_change_types_validation_failure(self, engine, mock_validator):
        """Test bulk change with validation failure"""
        mock_validator.validate_bulk_operation = Mock(return_value=ValidationResult(
            is_valid=False,
            errors=["Validation error"],
            warnings=[]
        ))
        
        # Mock the validate_bulk_operation method
        engine.validate_bulk_operation = mock_validator.validate_bulk_operation
        
        element_ids = ["elem_001", "elem_002"]
        options = BulkOperationOptions(validate_before=True)
        
        result = engine.bulk_change_types(element_ids, "target_type", options)
        
        assert result.status == OperationStatus.FAILED
        assert "Validation error" in result.errors
        assert result.successful_changes == 0
    
    @patch('torematrix.core.operations.type_management.bulk_operations.ThreadPoolExecutor')
    def test_bulk_change_types_dry_run(self, mock_executor, engine):
        """Test bulk change in dry run mode"""
        element_ids = ["elem_001", "elem_002"]
        options = BulkOperationOptions(dry_run=True, validate_before=False)
        
        # Mock preview method
        engine.preview_bulk_change = Mock(return_value=BulkChangePreview(
            target_type="target_type",
            total_elements=2,
            valid_conversions=2,
            invalid_conversions=0,
            data_loss_risk=0,
            warnings=["Preview warning"],
            errors=[],
            estimated_duration=1.0,
            memory_estimate=2048,
            affected_relationships=set()
        ))
        
        result = engine.bulk_change_types(element_ids, "target_type", options)
        
        assert result.status == OperationStatus.COMPLETED
        assert "Preview warning" in result.warnings
        assert result.total_elements == 2
        # Executor should not be used in dry run
        mock_executor.assert_not_called()
    
    def test_preview_bulk_change_invalid_target(self, engine, mock_registry):
        """Test preview with invalid target type"""
        mock_registry.get_type.return_value = None
        
        preview = engine.preview_bulk_change(["elem_001"], "invalid_type")
        
        assert preview.target_type == "invalid_type"
        assert preview.total_elements == 1
        assert preview.valid_conversions == 0
        assert preview.invalid_conversions == 1
        assert "Target type 'invalid_type' not found" in preview.errors
    
    def test_preview_bulk_change_success(self, engine):
        """Test successful preview generation"""
        # Mock helper methods
        engine._get_element_type = Mock(return_value="text")
        engine._is_conversion_safe = Mock(return_value=True)
        engine._has_data_loss_risk = Mock(return_value=False)
        engine._get_element_relationships = Mock(return_value={"rel_001"})
        engine._estimate_operation_duration = Mock(return_value=5.0)
        engine._estimate_memory_usage = Mock(return_value=1024)
        
        element_ids = ["elem_001", "elem_002"]
        preview = engine.preview_bulk_change(element_ids, "title")
        
        assert preview.target_type == "title"
        assert preview.total_elements == 2
        assert preview.valid_conversions == 2
        assert preview.invalid_conversions == 0
        assert preview.data_loss_risk == 0
        assert preview.estimated_duration == 5.0
        assert preview.memory_estimate == 1024
        assert "rel_001" in preview.affected_relationships
    
    def test_validate_bulk_operation_invalid_target(self, engine, mock_registry):
        """Test validation with invalid target type"""
        mock_registry.has_type.return_value = False
        
        result = engine.validate_bulk_operation(["elem_001"], "invalid_type")
        
        assert result.is_valid is False
        assert "Target type 'invalid_type' not found" in result.errors
    
    def test_validate_bulk_operation_empty_elements(self, engine):
        """Test validation with empty element list"""
        result = engine.validate_bulk_operation([], "target_type")
        
        assert result.is_valid is False
        assert "Element IDs list cannot be empty" in result.errors
    
    def test_validate_bulk_operation_large_operation(self, engine):
        """Test validation with large element list"""
        large_element_list = [f"elem_{i:06d}" for i in range(100001)]
        
        result = engine.validate_bulk_operation(large_element_list, "target_type")
        
        # Should have performance warning
        assert any("may impact performance" in warning for warning in result.warnings)
    
    def test_validate_bulk_operation_success(self, engine):
        """Test successful validation"""
        engine._get_element_type = Mock(return_value="text")
        engine._is_conversion_valid = Mock(return_value=True)
        
        result = engine.validate_bulk_operation(["elem_001", "elem_002"], "title")
        
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_cancel_operation_success(self, engine):
        """Test successful operation cancellation"""
        # Setup operation
        operation_id = "test_op"
        cancel_event = threading.Event()
        result = BulkOperationResult(
            operation_id=operation_id,
            status=OperationStatus.RUNNING,
            total_elements=100,
            processed_elements=50,
            successful_changes=45,
            failed_changes=5,
            skipped_elements=0,
            warnings=[],
            errors=[],
            changes=[],
            start_time=datetime.now()
        )
        
        engine._operations[operation_id] = result
        engine._cancel_events[operation_id] = cancel_event
        
        success = engine.cancel_operation(operation_id)
        
        assert success is True
        assert cancel_event.is_set()
        assert result.status == OperationStatus.CANCELLED
    
    def test_cancel_operation_not_found(self, engine):
        """Test cancelling non-existent operation"""
        success = engine.cancel_operation("non_existent")
        assert success is False
    
    def test_get_operation_status_exists(self, engine):
        """Test getting status of existing operation"""
        operation_id = "test_op"
        result = BulkOperationResult(
            operation_id=operation_id,
            status=OperationStatus.COMPLETED,
            total_elements=100,
            processed_elements=100,
            successful_changes=100,
            failed_changes=0,
            skipped_elements=0,
            warnings=[],
            errors=[],
            changes=[],
            start_time=datetime.now()
        )
        
        engine._operations[operation_id] = result
        
        retrieved_result = engine.get_operation_status(operation_id)
        assert retrieved_result == result
    
    def test_get_operation_status_not_found(self, engine):
        """Test getting status of non-existent operation"""
        result = engine.get_operation_status("non_existent")
        assert result is None
    
    def test_list_active_operations(self, engine):
        """Test listing active operations"""
        # Add various operations
        engine._operations = {
            "op_pending": BulkOperationResult(
                operation_id="op_pending",
                status=OperationStatus.PENDING,
                total_elements=100,
                processed_elements=0,
                successful_changes=0,
                failed_changes=0,
                skipped_elements=0,
                warnings=[],
                errors=[],
                changes=[],
                start_time=datetime.now()
            ),
            "op_running": BulkOperationResult(
                operation_id="op_running",
                status=OperationStatus.RUNNING,
                total_elements=100,
                processed_elements=50,
                successful_changes=50,
                failed_changes=0,
                skipped_elements=0,
                warnings=[],
                errors=[],
                changes=[],
                start_time=datetime.now()
            ),
            "op_completed": BulkOperationResult(
                operation_id="op_completed",
                status=OperationStatus.COMPLETED,
                total_elements=100,
                processed_elements=100,
                successful_changes=100,
                failed_changes=0,
                skipped_elements=0,
                warnings=[],
                errors=[],
                changes=[],
                start_time=datetime.now()
            )
        }
        
        active_ops = engine.list_active_operations()
        
        assert "op_pending" in active_ops
        assert "op_running" in active_ops
        assert "op_completed" not in active_ops
        assert len(active_ops) == 2
    
    def test_thread_safety(self, engine):
        """Test thread safety of engine operations"""
        import threading
        import time
        
        results = []
        errors = []
        
        def worker(worker_id):
            try:
                element_ids = [f"elem_{worker_id}_{i}" for i in range(10)]
                result = engine.bulk_change_types(
                    element_ids, 
                    "target_type",
                    BulkOperationOptions(validate_before=False)
                )
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            thread.start()
            threads.append(thread)
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Check results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 5
        
        # Check that operations were tracked properly
        assert len(engine._operations) == 5
        
        # All operations should be completed or failed
        for result in results:
            assert result.status in (OperationStatus.COMPLETED, OperationStatus.FAILED, OperationStatus.PARTIAL)
    
    def test_progress_callback(self, engine):
        """Test progress callback functionality"""
        progress_updates = []
        
        def progress_callback(current, total):
            progress_updates.append((current, total))
        
        options = BulkOperationOptions(
            progress_callback=progress_callback,
            validate_before=False,
            batch_size=2
        )
        
        element_ids = ["elem_001", "elem_002", "elem_003", "elem_004"]
        
        # Mock the necessary methods
        engine._get_element_type = Mock(return_value="text")
        engine._perform_type_change = Mock(return_value=True)
        engine._preserve_element_metadata = Mock(return_value={})
        
        result = engine.bulk_change_types(element_ids, "target_type", options)
        
        # Should have progress updates
        assert len(progress_updates) > 0
        
        # Final update should show completion
        final_current, final_total = progress_updates[-1]
        assert final_current <= final_total
        assert final_total == len(element_ids)


class TestBulkOperationIntegration:
    """Integration tests for bulk operations"""
    
    def test_end_to_end_bulk_operation(self):
        """Test complete bulk operation workflow"""
        # Setup
        registry = Mock(spec=TypeRegistry)
        validator = Mock(spec=TypeValidationEngine)
        engine = BulkTypeOperationEngine(registry, validator)
        
        # Configure mocks
        registry.has_type.return_value = True
        registry.get_type.return_value = Mock(spec=TypeDefinition)
        
        engine._get_element_type = Mock(side_effect=lambda x: "text")
        engine._perform_type_change = Mock(return_value=True)
        engine._preserve_element_metadata = Mock(return_value={"preserved": True})
        engine._is_conversion_safe = Mock(return_value=True)
        engine._is_conversion_valid = Mock(return_value=True)
        engine._has_data_loss_risk = Mock(return_value=False)
        engine._get_element_relationships = Mock(return_value=set())
        
        # Test data
        element_ids = [f"elem_{i:03d}" for i in range(100)]
        target_type = "title"
        
        # Execute operation
        options = BulkOperationOptions(
            batch_size=25,
            max_workers=2,
            validate_before=True,
            preserve_metadata=True
        )
        
        result = engine.bulk_change_types(element_ids, target_type, options)
        
        # Verify results
        assert result.status == OperationStatus.COMPLETED
        assert result.total_elements == 100
        assert result.successful_changes == 100
        assert result.failed_changes == 0
        assert len(result.changes) == 100
        assert result.success_rate == 100.0
        assert result.is_complete is True
        
        # Verify all changes recorded properly
        for change in result.changes:
            assert change.old_type == "text"
            assert change.new_type == "title"
            assert change.data_preserved is True
            assert change.metadata_changes == {"preserved": True}
    
    def test_bulk_operation_with_failures(self):
        """Test bulk operation with some failures"""
        # Setup
        registry = Mock(spec=TypeRegistry)
        validator = Mock(spec=TypeValidationEngine)
        engine = BulkTypeOperationEngine(registry, validator)
        
        # Configure mocks
        registry.has_type.return_value = True
        registry.get_type.return_value = Mock(spec=TypeDefinition)
        
        engine._get_element_type = Mock(side_effect=lambda x: "text")
        
        # Make some operations fail
        def mock_perform_change(element_id, from_type, to_type, options):
            if "fail" in element_id:
                raise RuntimeError(f"Conversion failed for {element_id}")
            return True
        
        engine._perform_type_change = Mock(side_effect=mock_perform_change)
        engine._preserve_element_metadata = Mock(return_value={})
        
        # Test data - mix of success and failure elements
        element_ids = ["elem_001", "elem_fail_002", "elem_003", "elem_fail_004", "elem_005"]
        
        # Execute operation
        options = BulkOperationOptions(
            batch_size=2,
            validate_before=False,
            rollback_on_error=False
        )
        
        result = engine.bulk_change_types(element_ids, "title", options)
        
        # Verify results
        assert result.status == OperationStatus.PARTIAL
        assert result.total_elements == 5
        assert result.processed_elements == 5
        assert result.successful_changes == 3
        assert result.failed_changes == 2
        assert result.success_rate == 60.0
        assert result.is_complete is False
        assert len(result.errors) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])