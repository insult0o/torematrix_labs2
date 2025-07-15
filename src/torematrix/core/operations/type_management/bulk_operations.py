"""Bulk Type Operations Engine

Efficient bulk type modification system for large-scale type operations
with progress tracking, validation, and rollback capabilities.
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional, Set, Callable, Any, Union
from uuid import uuid4

from torematrix.core.models.types import TypeRegistry, TypeDefinition, get_type_registry
from torematrix.core.models.validation import TypeValidationEngine, ValidationResult
from .progress import ProgressTracker, OperationProgress
from .rollback import RollbackManager, RollbackOperation


class BulkOperationType(Enum):
    """Types of bulk operations"""
    TYPE_CHANGE = "type_change"
    PROPERTY_UPDATE = "property_update"
    METADATA_UPDATE = "metadata_update"
    BATCH_DELETE = "batch_delete"
    BULK_CREATE = "bulk_create"


class OperationStatus(Enum):
    """Status of bulk operations"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ROLLED_BACK = "rolled_back"


@dataclass
class BulkOperationOptions:
    """Configuration options for bulk operations"""
    batch_size: int = 1000
    max_workers: int = 4
    validate_before_execution: bool = True
    preserve_data: bool = True
    enable_rollback: bool = True
    progress_callback: Optional[Callable[[OperationProgress], None]] = None
    dry_run: bool = False
    timeout_seconds: Optional[int] = None
    fail_fast: bool = False
    skip_invalid: bool = False


@dataclass
class BulkOperationItem:
    """Individual item in a bulk operation"""
    element_id: str
    current_type: str
    target_type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    validation_result: Optional[ValidationResult] = None


@dataclass
class BulkOperationResult:
    """Result of a bulk operation"""
    operation_id: str
    operation_type: BulkOperationType
    status: OperationStatus
    total_items: int
    processed_items: int
    successful_items: int
    failed_items: int
    skipped_items: int
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    failed_element_ids: List[str] = field(default_factory=list)
    rollback_operation_id: Optional[str] = None
    performance_metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BulkChangePreview:
    """Preview of bulk change operation"""
    total_elements: int
    valid_elements: int
    invalid_elements: int
    conversion_warnings: List[str]
    estimated_duration: float
    memory_estimate_mb: float
    affected_types: Set[str]
    data_preservation_issues: List[str]


class BulkTypeOperationEngine:
    """Efficient bulk type modification system with enterprise features"""
    
    def __init__(self, 
                 registry: TypeRegistry = None,
                 validator: TypeValidationEngine = None,
                 rollback_manager: RollbackManager = None):
        """Initialize bulk operations engine
        
        Args:
            registry: Type registry for type operations
            validator: Validation engine for pre-operation checks
            rollback_manager: Rollback manager for undo operations
        """
        self.registry = registry or get_type_registry()
        self.validator = validator or TypeValidationEngine(self.registry)
        self.rollback_manager = rollback_manager or RollbackManager()
        self.progress_tracker = ProgressTracker()
        
        # Active operations tracking
        self.active_operations: Dict[str, BulkOperationResult] = {}
        self.operation_futures: Dict[str, asyncio.Future] = {}
        
        # Performance tracking
        self.operation_stats: Dict[str, List[float]] = {
            'processing_time_per_item': [],
            'memory_usage': [],
            'batch_completion_time': []
        }
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
    
    async def bulk_change_types(self, 
                               element_ids: List[str], 
                               target_type: str,
                               options: BulkOperationOptions = None) -> BulkOperationResult:
        """Execute bulk type changes for multiple elements
        
        Args:
            element_ids: List of element IDs to change
            target_type: Target type ID to change to
            options: Operation configuration options
            
        Returns:
            BulkOperationResult with operation details and results
        """
        options = options or BulkOperationOptions()
        operation_id = str(uuid4())
        
        # Initialize operation result
        result = BulkOperationResult(
            operation_id=operation_id,
            operation_type=BulkOperationType.TYPE_CHANGE,
            status=OperationStatus.PENDING,
            total_items=len(element_ids),
            processed_items=0,
            successful_items=0,
            failed_items=0,
            skipped_items=0,
            start_time=datetime.now()
        )
        
        self.active_operations[operation_id] = result
        
        try:
            # Validate target type exists
            if not self.registry.type_exists(target_type):
                result.status = OperationStatus.FAILED
                result.errors.append(f"Target type '{target_type}' does not exist")
                return result
            
            # Prepare operation items
            operation_items = await self._prepare_operation_items(
                element_ids, target_type, options
            )
            
            # Pre-operation validation
            if options.validate_before_execution:
                validation_result = await self._validate_bulk_operation(
                    operation_items, options
                )
                if not validation_result.is_valid and options.fail_fast:
                    result.status = OperationStatus.FAILED
                    result.errors.extend(validation_result.errors)
                    return result
                
                # Filter out invalid items if skip_invalid is enabled
                if options.skip_invalid:
                    operation_items = [
                        item for item in operation_items 
                        if item.validation_result and item.validation_result.is_valid
                    ]
                    result.skipped_items = result.total_items - len(operation_items)
            
            # Dry run mode - return preview only
            if options.dry_run:
                result.status = OperationStatus.COMPLETED
                result.warnings.append("Dry run mode - no actual changes made")
                return result
            
            # Setup rollback if enabled
            rollback_operation = None
            if options.enable_rollback:
                rollback_operation = await self._prepare_rollback_operation(
                    operation_items, operation_id
                )
                result.rollback_operation_id = rollback_operation.operation_id
            
            # Execute bulk operation
            result.status = OperationStatus.RUNNING
            await self._execute_bulk_operation(operation_items, result, options)
            
            # Finalize operation
            result.end_time = datetime.now()
            result.duration_seconds = (
                result.end_time - result.start_time
            ).total_seconds()
            
            if result.failed_items == 0:
                result.status = OperationStatus.COMPLETED
            elif result.successful_items > 0:
                result.status = OperationStatus.COMPLETED
                result.warnings.append(
                    f"Partial success: {result.failed_items} items failed"
                )
            else:
                result.status = OperationStatus.FAILED
                
            self.logger.info(
                f"Bulk operation {operation_id} completed: "
                f"{result.successful_items}/{result.total_items} successful"
            )
            
        except asyncio.CancelledError:
            result.status = OperationStatus.CANCELLED
            self.logger.warning(f"Bulk operation {operation_id} was cancelled")
        except Exception as e:
            result.status = OperationStatus.FAILED
            result.errors.append(f"Unexpected error: {str(e)}")
            self.logger.error(f"Bulk operation {operation_id} failed: {e}")
        finally:
            # Cleanup
            if operation_id in self.operation_futures:
                del self.operation_futures[operation_id]
        
        return result
    
    async def preview_bulk_change(self, 
                                 element_ids: List[str], 
                                 target_type: str) -> BulkChangePreview:
        """Generate preview of bulk change operation
        
        Args:
            element_ids: List of element IDs to change
            target_type: Target type ID to change to
            
        Returns:
            BulkChangePreview with analysis and estimates
        """
        preview = BulkChangePreview(
            total_elements=len(element_ids),
            valid_elements=0,
            invalid_elements=0,
            conversion_warnings=[],
            estimated_duration=0.0,
            memory_estimate_mb=0.0,
            affected_types=set(),
            data_preservation_issues=[]
        )
        
        # Validate target type
        if not self.registry.type_exists(target_type):
            preview.conversion_warnings.append(
                f"Target type '{target_type}' does not exist"
            )
            return preview
        
        # Analyze each element
        for element_id in element_ids:
            try:
                # Get current element type (simulated - would come from actual element)
                current_type = self._get_element_type(element_id)
                if current_type:
                    preview.affected_types.add(current_type)
                    
                    # Validate conversion
                    validation = await self._validate_type_conversion(
                        element_id, current_type, target_type
                    )
                    
                    if validation.is_valid:
                        preview.valid_elements += 1
                    else:
                        preview.invalid_elements += 1
                        preview.conversion_warnings.extend(validation.errors)
                
            except Exception as e:
                preview.invalid_elements += 1
                preview.conversion_warnings.append(
                    f"Error analyzing element {element_id}: {str(e)}"
                )
        
        # Estimate performance metrics
        preview.estimated_duration = self._estimate_operation_duration(
            len(element_ids)
        )
        preview.memory_estimate_mb = self._estimate_memory_usage(
            len(element_ids)
        )
        
        return preview
    
    async def cancel_operation(self, operation_id: str) -> bool:
        """Cancel an active bulk operation
        
        Args:
            operation_id: ID of operation to cancel
            
        Returns:
            True if cancellation was successful
        """
        if operation_id not in self.active_operations:
            return False
        
        if operation_id in self.operation_futures:
            future = self.operation_futures[operation_id]
            future.cancel()
        
        result = self.active_operations[operation_id]
        result.status = OperationStatus.CANCELLED
        result.end_time = datetime.now()
        
        self.logger.info(f"Cancelled bulk operation {operation_id}")
        return True
    
    async def rollback_operation(self, operation_id: str) -> bool:
        """Rollback a completed bulk operation
        
        Args:
            operation_id: ID of operation to rollback
            
        Returns:
            True if rollback was successful
        """
        if operation_id not in self.active_operations:
            return False
        
        result = self.active_operations[operation_id]
        if not result.rollback_operation_id:
            self.logger.warning(
                f"No rollback data available for operation {operation_id}"
            )
            return False
        
        try:
            success = await self.rollback_manager.execute_rollback(
                result.rollback_operation_id
            )
            
            if success:
                result.status = OperationStatus.ROLLED_BACK
                self.logger.info(f"Successfully rolled back operation {operation_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to rollback operation {operation_id}: {e}")
            return False
    
    def get_operation_status(self, operation_id: str) -> Optional[BulkOperationResult]:
        """Get status of bulk operation
        
        Args:
            operation_id: ID of operation
            
        Returns:
            BulkOperationResult if found, None otherwise
        """
        return self.active_operations.get(operation_id)
    
    def list_active_operations(self) -> List[BulkOperationResult]:
        """Get list of all active operations
        
        Returns:
            List of active BulkOperationResult objects
        """
        return [
            result for result in self.active_operations.values()
            if result.status in [OperationStatus.PENDING, OperationStatus.RUNNING]
        ]
    
    async def _prepare_operation_items(self, 
                                     element_ids: List[str], 
                                     target_type: str,
                                     options: BulkOperationOptions) -> List[BulkOperationItem]:
        """Prepare operation items for bulk processing"""
        items = []
        
        for element_id in element_ids:
            current_type = self._get_element_type(element_id)
            
            item = BulkOperationItem(
                element_id=element_id,
                current_type=current_type or "unknown",
                target_type=target_type
            )
            
            items.append(item)
        
        return items
    
    async def _validate_bulk_operation(self, 
                                     items: List[BulkOperationItem],
                                     options: BulkOperationOptions) -> ValidationResult:
        """Validate bulk operation before execution"""
        errors = []
        warnings = []
        
        for item in items:
            validation = await self._validate_type_conversion(
                item.element_id, item.current_type, item.target_type
            )
            item.validation_result = validation
            
            if not validation.is_valid:
                errors.extend(validation.errors)
            if validation.warnings:
                warnings.extend(validation.warnings)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    async def _execute_bulk_operation(self, 
                                    items: List[BulkOperationItem],
                                    result: BulkOperationResult,
                                    options: BulkOperationOptions):
        """Execute the actual bulk operation"""
        batch_size = options.batch_size
        total_batches = (len(items) + batch_size - 1) // batch_size
        
        # Process in batches
        for batch_idx in range(total_batches):
            batch_start = batch_idx * batch_size
            batch_end = min(batch_start + batch_size, len(items))
            batch_items = items[batch_start:batch_end]
            
            # Process batch
            batch_results = await self._process_batch(batch_items, options)
            
            # Update results
            for item_result in batch_results:
                result.processed_items += 1
                if item_result['success']:
                    result.successful_items += 1
                else:
                    result.failed_items += 1
                    result.failed_element_ids.append(item_result['element_id'])
                    result.errors.append(item_result['error'])
            
            # Update progress
            progress = OperationProgress(
                operation_id=result.operation_id,
                total_items=result.total_items,
                processed_items=result.processed_items,
                successful_items=result.successful_items,
                failed_items=result.failed_items,
                current_batch=batch_idx + 1,
                total_batches=total_batches,
                percentage=result.processed_items / result.total_items * 100
            )
            
            self.progress_tracker.update_progress(result.operation_id, progress)
            
            if options.progress_callback:
                options.progress_callback(progress)
    
    async def _process_batch(self, 
                           items: List[BulkOperationItem],
                           options: BulkOperationOptions) -> List[Dict[str, Any]]:
        """Process a batch of operation items"""
        results = []
        
        # Use thread pool for concurrent processing
        with ThreadPoolExecutor(max_workers=options.max_workers) as executor:
            # Submit all batch items
            futures = {
                executor.submit(self._process_single_item, item): item
                for item in items
            }
            
            # Collect results as they complete
            for future in as_completed(futures):
                item = futures[future]
                try:
                    success = future.result()
                    results.append({
                        'element_id': item.element_id,
                        'success': success,
                        'error': None
                    })
                except Exception as e:
                    results.append({
                        'element_id': item.element_id,
                        'success': False,
                        'error': str(e)
                    })
        
        return results
    
    def _process_single_item(self, item: BulkOperationItem) -> bool:
        """Process a single operation item"""
        try:
            # Simulate type change operation
            # In real implementation, this would update the actual element
            success = self._change_element_type(
                item.element_id, 
                item.current_type, 
                item.target_type
            )
            return success
        except Exception as e:
            self.logger.error(
                f"Failed to process item {item.element_id}: {e}"
            )
            raise
    
    def _change_element_type(self, element_id: str, from_type: str, to_type: str) -> bool:
        """Change type of a single element (placeholder implementation)"""
        # This would be implemented to actually change element types
        # For now, simulate success/failure
        import random
        return random.random() > 0.05  # 95% success rate
    
    def _get_element_type(self, element_id: str) -> Optional[str]:
        """Get current type of element (placeholder implementation)"""
        # This would retrieve actual element type from storage
        # For now, return a simulated type
        return "text"  # Default type
    
    async def _validate_type_conversion(self, 
                                      element_id: str, 
                                      from_type: str, 
                                      to_type: str) -> ValidationResult:
        """Validate type conversion for single element"""
        errors = []
        warnings = []
        
        # Check if types exist
        if not self.registry.type_exists(from_type):
            errors.append(f"Source type '{from_type}' does not exist")
        
        if not self.registry.type_exists(to_type):
            errors.append(f"Target type '{to_type}' does not exist")
        
        # Check if conversion is valid
        if from_type == to_type:
            warnings.append("Source and target types are the same")
        
        # Add more validation logic here
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    async def _prepare_rollback_operation(self, 
                                        items: List[BulkOperationItem],
                                        operation_id: str) -> RollbackOperation:
        """Prepare rollback operation data"""
        rollback_data = {
            'original_operation_id': operation_id,
            'items': [
                {
                    'element_id': item.element_id,
                    'original_type': item.current_type,
                    'changed_type': item.target_type
                }
                for item in items
            ]
        }
        
        rollback_operation = RollbackOperation(
            operation_id=str(uuid4()),
            operation_type="bulk_type_change_rollback",
            rollback_data=rollback_data,
            created_at=datetime.now()
        )
        
        await self.rollback_manager.save_rollback_operation(rollback_operation)
        return rollback_operation
    
    def _estimate_operation_duration(self, item_count: int) -> float:
        """Estimate operation duration based on item count"""
        # Base time per item (in seconds)
        base_time_per_item = 0.001
        
        # Add overhead for batching and coordination
        overhead = 0.1
        
        return item_count * base_time_per_item + overhead
    
    def _estimate_memory_usage(self, item_count: int) -> float:
        """Estimate memory usage in MB"""
        # Estimate memory per item (in MB)
        memory_per_item = 0.001
        
        # Base memory overhead
        base_overhead = 10.0
        
        return item_count * memory_per_item + base_overhead