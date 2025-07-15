"""Bulk Type Operation Engine

Efficient bulk type modification system for large-scale type operations.
Provides thread-safe, memory-efficient processing with progress tracking.
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set, Callable, Any, Union
import threading
import time

from torematrix.core.models.types import TypeRegistry, TypeDefinition, ValidationResult
from torematrix.core.models.types.validation import TypeValidationEngine


logger = logging.getLogger(__name__)


class OperationStatus(Enum):
    """Status of bulk operations"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed" 
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIAL = "partial"


class ConflictResolution(Enum):
    """Conflict resolution strategies"""
    SKIP = "skip"
    OVERWRITE = "overwrite"
    MERGE = "merge"
    PROMPT = "prompt"
    FAIL = "fail"


@dataclass
class BulkOperationOptions:
    """Options for bulk type operations"""
    batch_size: int = 1000
    max_workers: int = 4
    validate_before: bool = True
    preserve_metadata: bool = True
    track_changes: bool = True
    conflict_resolution: ConflictResolution = ConflictResolution.SKIP
    timeout_seconds: Optional[int] = None
    rollback_on_error: bool = True
    dry_run: bool = False
    progress_callback: Optional[Callable[[int, int], None]] = None


@dataclass
class ElementChange:
    """Record of an element type change"""
    element_id: str
    old_type: str
    new_type: str
    timestamp: datetime
    metadata_changes: Dict[str, Any] = field(default_factory=dict)
    data_preserved: bool = True
    warnings: List[str] = field(default_factory=list)


@dataclass
class BulkOperationResult:
    """Result of a bulk type operation"""
    operation_id: str
    status: OperationStatus
    total_elements: int
    processed_elements: int
    successful_changes: int
    failed_changes: int
    skipped_elements: int
    warnings: List[str]
    errors: List[str]
    changes: List[ElementChange]
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.processed_elements == 0:
            return 0.0
        return (self.successful_changes / self.processed_elements) * 100.0
    
    @property
    def is_complete(self) -> bool:
        """Check if operation completed successfully"""
        return self.status == OperationStatus.COMPLETED and self.failed_changes == 0


@dataclass 
class BulkChangePreview:
    """Preview of bulk changes before execution"""
    target_type: str
    total_elements: int
    valid_conversions: int
    invalid_conversions: int
    data_loss_risk: int
    warnings: List[str]
    errors: List[str]
    estimated_duration: float
    memory_estimate: int
    affected_relationships: Set[str]
    
    @property
    def is_safe(self) -> bool:
        """Check if the bulk change is safe to execute"""
        return (self.invalid_conversions == 0 and 
                self.data_loss_risk == 0 and 
                len(self.errors) == 0)


class BulkTypeOperationEngine:
    """Efficient bulk type modification system
    
    Provides thread-safe, memory-efficient bulk operations with:
    - Concurrent processing with configurable workers
    - Progress tracking and cancellation support
    - Automatic rollback on failures
    - Data preservation and validation
    - Comprehensive error handling and reporting
    """
    
    def __init__(self, 
                 registry: TypeRegistry, 
                 validator: TypeValidationEngine,
                 max_workers: int = 4):
        """Initialize bulk operation engine
        
        Args:
            registry: Type registry for type definitions
            validator: Validation engine for type checking
            max_workers: Maximum number of worker threads
        """
        self.registry = registry
        self.validator = validator
        self.max_workers = max_workers
        self._operations: Dict[str, BulkOperationResult] = {}
        self._cancel_events: Dict[str, threading.Event] = {}
        self._lock = threading.RLock()
        
        logger.info(f"BulkTypeOperationEngine initialized with {max_workers} workers")
    
    def bulk_change_types(self, 
                         element_ids: List[str], 
                         target_type: str,
                         options: Optional[BulkOperationOptions] = None) -> BulkOperationResult:
        """Execute bulk type changes on elements
        
        Args:
            element_ids: List of element IDs to modify
            target_type: Target type to change elements to
            options: Operation options and configuration
            
        Returns:
            BulkOperationResult with operation details and results
            
        Raises:
            ValueError: If target_type is invalid or elements list is empty
            RuntimeError: If operation fails to start
        """
        if not element_ids:
            raise ValueError("Element IDs list cannot be empty")
        
        if not self.registry.has_type(target_type):
            raise ValueError(f"Target type '{target_type}' not found in registry")
        
        options = options or BulkOperationOptions()
        operation_id = f"bulk_change_{int(time.time())}_{id(element_ids)}"
        
        logger.info(f"Starting bulk change operation {operation_id}: "
                   f"{len(element_ids)} elements -> {target_type}")
        
        # Create operation result
        result = BulkOperationResult(
            operation_id=operation_id,
            status=OperationStatus.PENDING,
            total_elements=len(element_ids),
            processed_elements=0,
            successful_changes=0,
            failed_changes=0,
            skipped_elements=0,
            warnings=[],
            errors=[],
            changes=[],
            start_time=datetime.now()
        )
        
        with self._lock:
            self._operations[operation_id] = result
            self._cancel_events[operation_id] = threading.Event()
        
        try:
            # Validate operation if requested
            if options.validate_before:
                validation_result = self.validate_bulk_operation(element_ids, target_type)
                if not validation_result.is_valid:
                    result.status = OperationStatus.FAILED
                    result.errors.extend(validation_result.errors)
                    return result
            
            # Preview changes if dry run
            if options.dry_run:
                preview = self.preview_bulk_change(element_ids, target_type)
                result.status = OperationStatus.COMPLETED
                result.warnings.extend(preview.warnings)
                result.errors.extend(preview.errors)
                return result
            
            # Execute bulk operation
            result.status = OperationStatus.RUNNING
            self._execute_bulk_changes(element_ids, target_type, options, result)
            
        except Exception as e:
            logger.error(f"Bulk operation {operation_id} failed: {e}")
            result.status = OperationStatus.FAILED
            result.errors.append(str(e))
            
            # Attempt rollback if enabled
            if options.rollback_on_error and result.changes:
                try:
                    self._rollback_changes(result.changes)
                    result.warnings.append("Changes rolled back due to error")
                except Exception as rollback_error:
                    result.errors.append(f"Rollback failed: {rollback_error}")
        
        finally:
            result.end_time = datetime.now()
            result.duration_seconds = (result.end_time - result.start_time).total_seconds()
            
            # Clean up
            with self._lock:
                self._cancel_events.pop(operation_id, None)
        
        logger.info(f"Bulk operation {operation_id} completed: {result.status}")
        return result
    
    def preview_bulk_change(self, 
                           element_ids: List[str], 
                           target_type: str) -> BulkChangePreview:
        """Preview bulk changes without executing them
        
        Args:
            element_ids: List of element IDs to analyze
            target_type: Target type for conversion
            
        Returns:
            BulkChangePreview with analysis results
        """
        logger.debug(f"Previewing bulk change: {len(element_ids)} elements -> {target_type}")
        
        target_def = self.registry.get_type(target_type)
        if not target_def:
            return BulkChangePreview(
                target_type=target_type,
                total_elements=len(element_ids),
                valid_conversions=0,
                invalid_conversions=len(element_ids),
                data_loss_risk=0,
                warnings=[],
                errors=[f"Target type '{target_type}' not found"],
                estimated_duration=0.0,
                memory_estimate=0,
                affected_relationships=set()
            )
        
        valid_conversions = 0
        invalid_conversions = 0
        data_loss_risk = 0
        warnings = []
        errors = []
        affected_relationships = set()
        
        # Analyze each element (simplified for demo)
        for element_id in element_ids[:100]:  # Sample first 100 for performance
            try:
                # Mock element analysis - in real implementation would fetch element data
                current_type = self._get_element_type(element_id)
                if current_type == target_type:
                    continue  # No change needed
                
                # Check conversion compatibility
                if self._is_conversion_safe(current_type, target_type):
                    valid_conversions += 1
                else:
                    invalid_conversions += 1
                    
                # Check for data loss risk
                if self._has_data_loss_risk(current_type, target_type):
                    data_loss_risk += 1
                    warnings.append(f"Data loss risk for element {element_id}")
                
                # Track affected relationships
                relationships = self._get_element_relationships(element_id)
                affected_relationships.update(relationships)
                
            except Exception as e:
                invalid_conversions += 1
                errors.append(f"Analysis failed for element {element_id}: {e}")
        
        # Extrapolate results for all elements
        sample_size = min(len(element_ids), 100)
        if sample_size > 0:
            scale_factor = len(element_ids) / sample_size
            valid_conversions = int(valid_conversions * scale_factor)
            invalid_conversions = int(invalid_conversions * scale_factor)
            data_loss_risk = int(data_loss_risk * scale_factor)
        
        # Estimate performance metrics
        estimated_duration = self._estimate_operation_duration(len(element_ids), target_type)
        memory_estimate = self._estimate_memory_usage(len(element_ids))
        
        return BulkChangePreview(
            target_type=target_type,
            total_elements=len(element_ids),
            valid_conversions=valid_conversions,
            invalid_conversions=invalid_conversions,
            data_loss_risk=data_loss_risk,
            warnings=warnings,
            errors=errors,
            estimated_duration=estimated_duration,
            memory_estimate=memory_estimate,
            affected_relationships=affected_relationships
        )
    
    def validate_bulk_operation(self, 
                               element_ids: List[str], 
                               target_type: str) -> ValidationResult:
        """Validate bulk operation before execution
        
        Args:
            element_ids: List of element IDs to validate
            target_type: Target type for validation
            
        Returns:
            ValidationResult indicating if operation is valid
        """
        logger.debug(f"Validating bulk operation: {len(element_ids)} elements -> {target_type}")
        
        errors = []
        warnings = []
        
        # Validate target type exists
        if not self.registry.has_type(target_type):
            errors.append(f"Target type '{target_type}' not found in registry")
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
        
        # Validate element IDs
        if not element_ids:
            errors.append("Element IDs list cannot be empty")
        elif len(element_ids) > 100000:  # Reasonable limit
            warnings.append(f"Large operation with {len(element_ids)} elements may impact performance")
        
        # Validate each element (sample for performance)
        sample_ids = element_ids[:50]  # Sample for validation
        for element_id in sample_ids:
            try:
                current_type = self._get_element_type(element_id)
                if current_type == target_type:
                    continue  # No validation needed
                
                # Validate conversion is possible
                if not self._is_conversion_valid(current_type, target_type):
                    errors.append(f"Invalid conversion from {current_type} to {target_type} for element {element_id}")
                
            except Exception as e:
                errors.append(f"Validation failed for element {element_id}: {e}")
        
        is_valid = len(errors) == 0
        return ValidationResult(is_valid=is_valid, errors=errors, warnings=warnings)
    
    def cancel_operation(self, operation_id: str) -> bool:
        """Cancel a running bulk operation
        
        Args:
            operation_id: ID of operation to cancel
            
        Returns:
            True if operation was cancelled, False if not found or already completed
        """
        with self._lock:
            if operation_id in self._cancel_events:
                self._cancel_events[operation_id].set()
                if operation_id in self._operations:
                    self._operations[operation_id].status = OperationStatus.CANCELLED
                logger.info(f"Bulk operation {operation_id} cancelled")
                return True
            return False
    
    def get_operation_status(self, operation_id: str) -> Optional[BulkOperationResult]:
        """Get status of a bulk operation
        
        Args:
            operation_id: ID of operation to check
            
        Returns:
            BulkOperationResult if found, None otherwise
        """
        with self._lock:
            return self._operations.get(operation_id)
    
    def list_active_operations(self) -> List[str]:
        """List all active operation IDs
        
        Returns:
            List of active operation IDs
        """
        with self._lock:
            return [op_id for op_id, result in self._operations.items() 
                   if result.status in (OperationStatus.PENDING, OperationStatus.RUNNING)]
    
    def _execute_bulk_changes(self, 
                             element_ids: List[str], 
                             target_type: str,
                             options: BulkOperationOptions,
                             result: BulkOperationResult) -> None:
        """Execute the actual bulk changes with threading"""
        
        # Split into batches
        batches = [element_ids[i:i + options.batch_size] 
                  for i in range(0, len(element_ids), options.batch_size)]
        
        logger.debug(f"Processing {len(batches)} batches with {options.max_workers} workers")
        
        with ThreadPoolExecutor(max_workers=options.max_workers) as executor:
            # Submit batch tasks
            future_to_batch = {
                executor.submit(self._process_batch, batch, target_type, options, result): batch
                for batch in batches
            }
            
            # Process completed batches
            for future in as_completed(future_to_batch):
                batch = future_to_batch[future]
                
                # Check for cancellation
                if self._is_cancelled(result.operation_id):
                    result.status = OperationStatus.CANCELLED
                    break
                
                try:
                    batch_result = future.result()
                    self._merge_batch_result(result, batch_result)
                    
                    # Update progress
                    if options.progress_callback:
                        options.progress_callback(result.processed_elements, result.total_elements)
                        
                except Exception as e:
                    logger.error(f"Batch processing failed: {e}")
                    result.errors.append(f"Batch processing failed: {e}")
                    result.failed_changes += len(batch)
        
        # Finalize result
        if result.status != OperationStatus.CANCELLED:
            if result.failed_changes == 0:
                result.status = OperationStatus.COMPLETED
            elif result.successful_changes > 0:
                result.status = OperationStatus.PARTIAL
            else:
                result.status = OperationStatus.FAILED
    
    def _process_batch(self, 
                      element_ids: List[str], 
                      target_type: str,
                      options: BulkOperationOptions,
                      result: BulkOperationResult) -> Dict[str, Any]:
        """Process a single batch of elements"""
        
        batch_result = {
            'successful_changes': 0,
            'failed_changes': 0,
            'skipped_elements': 0,
            'changes': [],
            'warnings': [],
            'errors': []
        }
        
        for element_id in element_ids:
            # Check for cancellation
            if self._is_cancelled(result.operation_id):
                break
            
            try:
                change = self._change_element_type(element_id, target_type, options)
                if change:
                    batch_result['changes'].append(change)
                    batch_result['successful_changes'] += 1
                else:
                    batch_result['skipped_elements'] += 1
                    
            except Exception as e:
                logger.warning(f"Failed to change type for element {element_id}: {e}")
                batch_result['failed_changes'] += 1
                batch_result['errors'].append(f"Element {element_id}: {e}")
        
        return batch_result
    
    def _change_element_type(self, 
                           element_id: str, 
                           target_type: str,
                           options: BulkOperationOptions) -> Optional[ElementChange]:
        """Change type of a single element"""
        
        # Get current element info (mock implementation)
        current_type = self._get_element_type(element_id)
        
        # Skip if already target type
        if current_type == target_type:
            return None
        
        # Create change record
        change = ElementChange(
            element_id=element_id,
            old_type=current_type,
            new_type=target_type,
            timestamp=datetime.now()
        )
        
        # Perform type change (mock implementation)
        if self._perform_type_change(element_id, current_type, target_type, options):
            # Preserve metadata if requested
            if options.preserve_metadata:
                change.metadata_changes = self._preserve_element_metadata(element_id)
            
            return change
        else:
            raise RuntimeError(f"Type change failed for element {element_id}")
    
    # Helper methods (mock implementations for demo)
    
    def _get_element_type(self, element_id: str) -> str:
        """Get current type of element (mock)"""
        # In real implementation, would query element storage
        return "text"  # Default mock type
    
    def _get_element_relationships(self, element_id: str) -> Set[str]:
        """Get relationships for element (mock)"""
        return set()  # Mock empty relationships
    
    def _is_conversion_safe(self, from_type: str, to_type: str) -> bool:
        """Check if conversion is safe (mock)"""
        return True  # Mock all conversions as safe
    
    def _is_conversion_valid(self, from_type: str, to_type: str) -> bool:
        """Check if conversion is valid (mock)"""
        return True  # Mock all conversions as valid
    
    def _has_data_loss_risk(self, from_type: str, to_type: str) -> bool:
        """Check if conversion has data loss risk (mock)"""
        return False  # Mock no data loss risk
    
    def _estimate_operation_duration(self, element_count: int, target_type: str) -> float:
        """Estimate operation duration in seconds"""
        # Simple estimation: 1000 elements per second
        return element_count / 1000.0
    
    def _estimate_memory_usage(self, element_count: int) -> int:
        """Estimate memory usage in bytes"""
        # Simple estimation: 1KB per element
        return element_count * 1024
    
    def _perform_type_change(self, 
                           element_id: str, 
                           from_type: str, 
                           to_type: str,
                           options: BulkOperationOptions) -> bool:
        """Perform actual type change (mock)"""
        # Mock implementation - would update element storage
        return True
    
    def _preserve_element_metadata(self, element_id: str) -> Dict[str, Any]:
        """Preserve element metadata during type change (mock)"""
        return {}  # Mock empty metadata
    
    def _is_cancelled(self, operation_id: str) -> bool:
        """Check if operation is cancelled"""
        with self._lock:
            cancel_event = self._cancel_events.get(operation_id)
            return cancel_event and cancel_event.is_set()
    
    def _merge_batch_result(self, 
                           result: BulkOperationResult, 
                           batch_result: Dict[str, Any]) -> None:
        """Merge batch result into overall result"""
        result.processed_elements += (batch_result['successful_changes'] + 
                                    batch_result['failed_changes'] + 
                                    batch_result['skipped_elements'])
        result.successful_changes += batch_result['successful_changes']
        result.failed_changes += batch_result['failed_changes']
        result.skipped_elements += batch_result['skipped_elements']
        result.changes.extend(batch_result['changes'])
        result.warnings.extend(batch_result['warnings'])
        result.errors.extend(batch_result['errors'])
    
    def _rollback_changes(self, changes: List[ElementChange]) -> None:
        """Rollback changes in case of error"""
        logger.info(f"Rolling back {len(changes)} changes")
        
        for change in reversed(changes):  # Rollback in reverse order
            try:
                # Mock rollback - would revert element type
                logger.debug(f"Rolling back element {change.element_id}: "
                           f"{change.new_type} -> {change.old_type}")
            except Exception as e:
                logger.error(f"Failed to rollback element {change.element_id}: {e}")
                raise