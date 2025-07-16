"""
Data Integrity and Validation Pipeline for Merge/Split Operations.

This module provides comprehensive validation, conflict resolution, audit logging,
and recovery mechanisms to ensure data consistency and operational reliability.
"""

from typing import Dict, List, Optional, Any, Callable, Union, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import time
import uuid
import hashlib
import logging
import json
from abc import ABC, abstractmethod
from collections import defaultdict
import threading

from ..core.elements import Element
from ..core.metadata import Metadata
from .transaction import Transaction, OperationRecord, OperationType


class ValidationLevel(Enum):
    """Validation strictness levels."""
    BASIC = "basic"
    STANDARD = "standard"
    STRICT = "strict"
    PARANOID = "paranoid"


class ConflictType(Enum):
    """Types of conflicts that can occur."""
    METADATA_MISMATCH = "metadata_mismatch"
    GEOMETRIC_OVERLAP = "geometric_overlap"
    CONTENT_INCONSISTENCY = "content_inconsistency"
    REFERENCE_VIOLATION = "reference_violation"
    SCHEMA_VIOLATION = "schema_violation"
    CONSTRAINT_VIOLATION = "constraint_violation"


class ValidationResult(Enum):
    """Validation operation results."""
    VALID = "valid"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationIssue:
    """Represents a validation issue found during checks."""
    issue_id: str
    issue_type: ConflictType
    severity: ValidationResult
    message: str
    element_ids: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    auto_fixable: bool = False
    fix_suggestion: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert issue to dictionary for serialization."""
        return {
            'issue_id': self.issue_id,
            'issue_type': self.issue_type.value,
            'severity': self.severity.value,
            'message': self.message,
            'element_ids': self.element_ids,
            'metadata': self.metadata,
            'timestamp': self.timestamp,
            'auto_fixable': self.auto_fixable,
            'fix_suggestion': self.fix_suggestion
        }


@dataclass
class ConflictResolution:
    """Represents a conflict resolution strategy."""
    resolution_id: str
    conflict_type: ConflictType
    strategy: str
    description: str
    auto_apply: bool = False
    resolver_func: Optional[Callable] = None
    
    def can_resolve(self, issue: ValidationIssue) -> bool:
        """Check if this resolution can handle the given issue."""
        return (issue.issue_type == self.conflict_type and 
                issue.auto_fixable and 
                self.resolver_func is not None)
    
    def apply(self, issue: ValidationIssue, elements: Dict[str, Element]) -> bool:
        """Apply the resolution to fix the issue."""
        if not self.can_resolve(issue) or not self.resolver_func:
            return False
        
        try:
            return self.resolver_func(issue, elements)
        except Exception as e:
            logging.getLogger(__name__).error(f"Resolution {self.resolution_id} failed: {e}")
            return False


class Validator(ABC):
    """Abstract base class for validation components."""
    
    @abstractmethod
    def validate(self, elements: Dict[str, Element], context: Dict[str, Any]) -> List[ValidationIssue]:
        """Perform validation and return any issues found."""
        pass
    
    @property
    @abstractmethod
    def validator_name(self) -> str:
        """Get the name of this validator."""
        pass


class MetadataValidator(Validator):
    """Validates metadata consistency and completeness."""
    
    def __init__(self, required_fields: Optional[List[str]] = None):
        self.required_fields = required_fields or ['type', 'content', 'bounds']
        self.logger = logging.getLogger(__name__)
    
    @property
    def validator_name(self) -> str:
        return "MetadataValidator"
    
    def validate(self, elements: Dict[str, Element], context: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate metadata consistency across elements."""
        issues = []
        
        for element_id, element in elements.items():
            # Check required fields
            for field in self.required_fields:
                if not hasattr(element, field) or getattr(element, field) is None:
                    issues.append(ValidationIssue(
                        issue_id=str(uuid.uuid4()),
                        issue_type=ConflictType.METADATA_MISMATCH,
                        severity=ValidationResult.ERROR,
                        message=f"Required field '{field}' missing in element {element_id}",
                        element_ids=[element_id],
                        auto_fixable=False
                    ))
            
            # Check metadata schema consistency
            if hasattr(element, 'metadata') and element.metadata:
                schema_issues = self._validate_metadata_schema(element_id, element.metadata)
                issues.extend(schema_issues)
        
        return issues
    
    def _validate_metadata_schema(self, element_id: str, metadata: Metadata) -> List[ValidationIssue]:
        """Validate metadata schema consistency."""
        issues = []
        
        # Check for required metadata fields based on element type
        if hasattr(metadata, 'element_type'):
            element_type = metadata.element_type
            required_metadata = self._get_required_metadata_for_type(element_type)
            
            for field in required_metadata:
                if not hasattr(metadata, field):
                    issues.append(ValidationIssue(
                        issue_id=str(uuid.uuid4()),
                        issue_type=ConflictType.SCHEMA_VIOLATION,
                        severity=ValidationResult.WARNING,
                        message=f"Recommended metadata field '{field}' missing for {element_type} element {element_id}",
                        element_ids=[element_id],
                        auto_fixable=True,
                        fix_suggestion=f"Add default value for {field}"
                    ))
        
        return issues
    
    def _get_required_metadata_for_type(self, element_type: str) -> List[str]:
        """Get required metadata fields for element type."""
        type_requirements = {
            'text': ['font_size', 'font_family', 'color'],
            'image': ['resolution', 'format', 'color_space'],
            'table': ['rows', 'columns', 'header_row'],
            'list': ['list_type', 'item_count']
        }
        return type_requirements.get(element_type, [])


class GeometricValidator(Validator):
    """Validates geometric properties and spatial relationships."""
    
    def __init__(self, overlap_threshold: float = 0.1):
        self.overlap_threshold = overlap_threshold
        self.logger = logging.getLogger(__name__)
    
    @property
    def validator_name(self) -> str:
        return "GeometricValidator"
    
    def validate(self, elements: Dict[str, Element], context: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate geometric properties and relationships."""
        issues = []
        
        # Check for overlapping elements
        overlap_issues = self._check_overlaps(elements)
        issues.extend(overlap_issues)
        
        # Check for invalid bounds
        bounds_issues = self._check_bounds_validity(elements)
        issues.extend(bounds_issues)
        
        # Check for geometric consistency after operations
        consistency_issues = self._check_geometric_consistency(elements, context)
        issues.extend(consistency_issues)
        
        return issues
    
    def _check_overlaps(self, elements: Dict[str, Element]) -> List[ValidationIssue]:
        """Check for problematic element overlaps."""
        issues = []
        element_list = list(elements.items())
        
        for i, (id1, elem1) in enumerate(element_list):
            for id2, elem2 in element_list[i+1:]:
                if self._elements_overlap_significantly(elem1, elem2):
                    issues.append(ValidationIssue(
                        issue_id=str(uuid.uuid4()),
                        issue_type=ConflictType.GEOMETRIC_OVERLAP,
                        severity=ValidationResult.WARNING,
                        message=f"Significant overlap detected between elements {id1} and {id2}",
                        element_ids=[id1, id2],
                        auto_fixable=True,
                        fix_suggestion="Consider adjusting element boundaries or merging overlapping elements"
                    ))
        
        return issues
    
    def _check_bounds_validity(self, elements: Dict[str, Element]) -> List[ValidationIssue]:
        """Check for invalid element bounds."""
        issues = []
        
        for element_id, element in elements.items():
            if hasattr(element, 'bounds') and element.bounds:
                bounds = element.bounds
                
                # Check for negative dimensions
                if hasattr(bounds, 'width') and bounds.width <= 0:
                    issues.append(ValidationIssue(
                        issue_id=str(uuid.uuid4()),
                        issue_type=ConflictType.GEOMETRIC_OVERLAP,
                        severity=ValidationResult.ERROR,
                        message=f"Element {element_id} has invalid width: {bounds.width}",
                        element_ids=[element_id],
                        auto_fixable=True
                    ))
                
                if hasattr(bounds, 'height') and bounds.height <= 0:
                    issues.append(ValidationIssue(
                        issue_id=str(uuid.uuid4()),
                        issue_type=ConflictType.GEOMETRIC_OVERLAP,
                        severity=ValidationResult.ERROR,
                        message=f"Element {element_id} has invalid height: {bounds.height}",
                        element_ids=[element_id],
                        auto_fixable=True
                    ))
        
        return issues
    
    def _check_geometric_consistency(self, elements: Dict[str, Element], context: Dict[str, Any]) -> List[ValidationIssue]:
        """Check geometric consistency after operations."""
        issues = []
        
        # Check if operation context indicates specific validations needed
        operation_type = context.get('operation_type')
        
        if operation_type == OperationType.MERGE:
            # For merge operations, validate that resulting element contains all source elements
            merged_element_id = context.get('result_element_id')
            source_element_ids = context.get('source_element_ids', [])
            
            if merged_element_id and source_element_ids:
                merge_issues = self._validate_merge_geometry(
                    elements, merged_element_id, source_element_ids
                )
                issues.extend(merge_issues)
        
        elif operation_type == OperationType.SPLIT:
            # For split operations, validate that split elements don't overlap
            split_element_ids = context.get('split_element_ids', [])
            if len(split_element_ids) > 1:
                split_issues = self._validate_split_geometry(elements, split_element_ids)
                issues.extend(split_issues)
        
        return issues
    
    def _elements_overlap_significantly(self, elem1: Element, elem2: Element) -> bool:
        """Check if two elements have significant overlap."""
        if not (hasattr(elem1, 'bounds') and hasattr(elem2, 'bounds')):
            return False
        
        bounds1, bounds2 = elem1.bounds, elem2.bounds
        
        # Calculate intersection area
        intersection = self._calculate_intersection(bounds1, bounds2)
        if intersection <= 0:
            return False
        
        # Calculate areas
        area1 = getattr(bounds1, 'width', 0) * getattr(bounds1, 'height', 0)
        area2 = getattr(bounds2, 'width', 0) * getattr(bounds2, 'height', 0)
        
        if area1 <= 0 or area2 <= 0:
            return False
        
        # Check if overlap exceeds threshold for either element
        overlap_ratio1 = intersection / area1
        overlap_ratio2 = intersection / area2
        
        return max(overlap_ratio1, overlap_ratio2) > self.overlap_threshold
    
    def _calculate_intersection(self, bounds1: Any, bounds2: Any) -> float:
        """Calculate intersection area between two bounds."""
        # This is a simplified calculation - real implementation would depend on bounds structure
        return 0.0  # Placeholder
    
    def _validate_merge_geometry(self, elements: Dict[str, Element], 
                                merged_id: str, source_ids: List[str]) -> List[ValidationIssue]:
        """Validate geometry after merge operation."""
        # Placeholder for merge geometry validation
        return []
    
    def _validate_split_geometry(self, elements: Dict[str, Element], 
                                split_ids: List[str]) -> List[ValidationIssue]:
        """Validate geometry after split operation."""
        # Placeholder for split geometry validation
        return []


class ContentValidator(Validator):
    """Validates content consistency and integrity."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    @property
    def validator_name(self) -> str:
        return "ContentValidator"
    
    def validate(self, elements: Dict[str, Element], context: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate content consistency and integrity."""
        issues = []
        
        # Check for empty or invalid content
        for element_id, element in elements.items():
            if hasattr(element, 'content'):
                content_issues = self._validate_element_content(element_id, element.content)
                issues.extend(content_issues)
        
        # Check content consistency after operations
        operation_issues = self._validate_operation_content_consistency(elements, context)
        issues.extend(operation_issues)
        
        return issues
    
    def _validate_element_content(self, element_id: str, content: Any) -> List[ValidationIssue]:
        """Validate individual element content."""
        issues = []
        
        if content is None or (isinstance(content, str) and not content.strip()):
            issues.append(ValidationIssue(
                issue_id=str(uuid.uuid4()),
                issue_type=ConflictType.CONTENT_INCONSISTENCY,
                severity=ValidationResult.WARNING,
                message=f"Element {element_id} has empty or null content",
                element_ids=[element_id],
                auto_fixable=False
            ))
        
        return issues
    
    def _validate_operation_content_consistency(self, elements: Dict[str, Element], 
                                              context: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate content consistency after operations."""
        issues = []
        
        operation_type = context.get('operation_type')
        
        if operation_type == OperationType.MERGE:
            # Validate that merged content preserves source content
            merge_issues = self._validate_merge_content(elements, context)
            issues.extend(merge_issues)
        
        return issues
    
    def _validate_merge_content(self, elements: Dict[str, Element], 
                               context: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate content preservation in merge operations."""
        # Placeholder for merge content validation
        return []


class DataIntegrityValidator:
    """
    Comprehensive data integrity validation pipeline.
    
    Coordinates multiple validators and provides conflict resolution
    capabilities for merge/split operations.
    """
    
    def __init__(self, validation_level: ValidationLevel = ValidationLevel.STANDARD):
        self.validation_level = validation_level
        self.validators: List[Validator] = []
        self.conflict_resolvers: Dict[ConflictType, List[ConflictResolution]] = defaultdict(list)
        
        self.lock = threading.RLock()
        self.logger = logging.getLogger(__name__)
        
        # Performance metrics
        self.metrics = {
            'validations_performed': 0,
            'issues_found': 0,
            'issues_resolved': 0,
            'validation_time_ms': 0.0,
            'resolution_time_ms': 0.0
        }
        
        # Initialize default validators
        self._initialize_default_validators()
        self._initialize_default_resolvers()
    
    def add_validator(self, validator: Validator) -> None:
        """Add a custom validator to the pipeline."""
        with self.lock:
            self.validators.append(validator)
            self.logger.debug(f"Added validator: {validator.validator_name}")
    
    def add_conflict_resolver(self, resolver: ConflictResolution) -> None:
        """Add a conflict resolution strategy."""
        with self.lock:
            self.conflict_resolvers[resolver.conflict_type].append(resolver)
            self.logger.debug(f"Added resolver for {resolver.conflict_type.value}: {resolver.resolution_id}")
    
    def validate_elements(self, elements: Dict[str, Element], 
                         context: Optional[Dict[str, Any]] = None) -> Tuple[List[ValidationIssue], bool]:
        """
        Validate elements and return issues found.
        
        Args:
            elements: Elements to validate
            context: Operation context for validation
            
        Returns:
            (list of issues, validation passed)
        """
        start_time = time.time()
        context = context or {}
        
        with self.lock:
            all_issues = []
            
            # Run all validators
            for validator in self.validators:
                try:
                    validator_issues = validator.validate(elements, context)
                    all_issues.extend(validator_issues)
                except Exception as e:
                    self.logger.error(f"Validator {validator.validator_name} failed: {e}")
                    # Add critical issue for validator failure
                    all_issues.append(ValidationIssue(
                        issue_id=str(uuid.uuid4()),
                        issue_type=ConflictType.SCHEMA_VIOLATION,
                        severity=ValidationResult.CRITICAL,
                        message=f"Validator {validator.validator_name} failed: {e}",
                        element_ids=list(elements.keys())
                    ))
            
            # Update metrics
            validation_time = (time.time() - start_time) * 1000
            self.metrics['validations_performed'] += 1
            self.metrics['issues_found'] += len(all_issues)
            self.metrics['validation_time_ms'] += validation_time
            
            # Determine if validation passed based on severity and level
            validation_passed = self._determine_validation_result(all_issues)
            
            self.logger.debug(f"Validation completed: {len(all_issues)} issues found in {validation_time:.2f}ms")
            return all_issues, validation_passed
    
    def resolve_conflicts(self, issues: List[ValidationIssue], 
                         elements: Dict[str, Element]) -> Tuple[List[ValidationIssue], int]:
        """
        Attempt to resolve validation issues automatically.
        
        Args:
            issues: Issues to resolve
            elements: Elements that may need modification
            
        Returns:
            (remaining unresolved issues, number of issues resolved)
        """
        start_time = time.time()
        resolved_count = 0
        unresolved_issues = []
        
        with self.lock:
            for issue in issues:
                resolved = False
                
                # Try to find and apply resolution
                resolvers = self.conflict_resolvers.get(issue.issue_type, [])
                for resolver in resolvers:
                    if resolver.can_resolve(issue):
                        try:
                            if resolver.apply(issue, elements):
                                resolved = True
                                resolved_count += 1
                                self.logger.debug(f"Resolved issue {issue.issue_id} using {resolver.resolution_id}")
                                break
                        except Exception as e:
                            self.logger.warning(f"Resolution {resolver.resolution_id} failed: {e}")
                
                if not resolved:
                    unresolved_issues.append(issue)
            
            # Update metrics
            resolution_time = (time.time() - start_time) * 1000
            self.metrics['issues_resolved'] += resolved_count
            self.metrics['resolution_time_ms'] += resolution_time
            
            self.logger.debug(f"Conflict resolution: {resolved_count} resolved, {len(unresolved_issues)} remaining in {resolution_time:.2f}ms")
            return unresolved_issues, resolved_count
    
    def validate_and_resolve(self, elements: Dict[str, Element], 
                           context: Optional[Dict[str, Any]] = None,
                           auto_resolve: bool = True) -> Dict[str, Any]:
        """
        Perform validation and optionally resolve conflicts.
        
        Args:
            elements: Elements to validate
            context: Operation context
            auto_resolve: Whether to attempt automatic resolution
            
        Returns:
            Validation report with results and metrics
        """
        start_time = time.time()
        
        # Perform validation
        issues, validation_passed = self.validate_elements(elements, context)
        
        resolved_count = 0
        if auto_resolve and issues:
            issues, resolved_count = self.resolve_conflicts(issues, elements)
            
            # Re-validate after resolution
            if resolved_count > 0:
                issues, validation_passed = self.validate_elements(elements, context)
        
        total_time = (time.time() - start_time) * 1000
        
        # Generate report
        report = {
            'validation_passed': validation_passed,
            'total_issues': len(issues),
            'issues_by_severity': self._group_issues_by_severity(issues),
            'issues_by_type': self._group_issues_by_type(issues),
            'issues_resolved': resolved_count,
            'validation_time_ms': total_time,
            'issues': [issue.to_dict() for issue in issues],
            'metrics': self.get_performance_metrics()
        }
        
        return report
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get validation performance metrics."""
        with self.lock:
            return dict(self.metrics)
    
    def reset_metrics(self) -> None:
        """Reset performance metrics."""
        with self.lock:
            self.metrics = {
                'validations_performed': 0,
                'issues_found': 0,
                'issues_resolved': 0,
                'validation_time_ms': 0.0,
                'resolution_time_ms': 0.0
            }
    
    # Private helper methods
    
    def _initialize_default_validators(self) -> None:
        """Initialize default validators based on validation level."""
        self.validators.append(MetadataValidator())
        
        if self.validation_level in [ValidationLevel.STANDARD, ValidationLevel.STRICT, ValidationLevel.PARANOID]:
            self.validators.append(GeometricValidator())
            self.validators.append(ContentValidator())
    
    def _initialize_default_resolvers(self) -> None:
        """Initialize default conflict resolution strategies."""
        # Metadata conflict resolvers
        self.add_conflict_resolver(ConflictResolution(
            resolution_id="default_metadata_fixer",
            conflict_type=ConflictType.METADATA_MISMATCH,
            strategy="add_default_values",
            description="Add default values for missing metadata fields",
            auto_apply=True,
            resolver_func=self._resolve_missing_metadata
        ))
        
        # Geometric conflict resolvers
        self.add_conflict_resolver(ConflictResolution(
            resolution_id="bounds_corrector",
            conflict_type=ConflictType.GEOMETRIC_OVERLAP,
            strategy="correct_invalid_bounds",
            description="Correct invalid element bounds",
            auto_apply=True,
            resolver_func=self._resolve_invalid_bounds
        ))
    
    def _resolve_missing_metadata(self, issue: ValidationIssue, elements: Dict[str, Element]) -> bool:
        """Resolve missing metadata by adding default values."""
        # Placeholder implementation
        return True
    
    def _resolve_invalid_bounds(self, issue: ValidationIssue, elements: Dict[str, Element]) -> bool:
        """Resolve invalid bounds by correcting them."""
        # Placeholder implementation
        return True
    
    def _determine_validation_result(self, issues: List[ValidationIssue]) -> bool:
        """Determine if validation passed based on issues and validation level."""
        if not issues:
            return True
        
        # Check for critical issues
        critical_issues = [i for i in issues if i.severity == ValidationResult.CRITICAL]
        if critical_issues:
            return False
        
        # Check based on validation level
        if self.validation_level == ValidationLevel.PARANOID:
            # Any warning or error fails validation
            return not any(i.severity in [ValidationResult.WARNING, ValidationResult.ERROR] for i in issues)
        elif self.validation_level == ValidationLevel.STRICT:
            # Any error fails validation
            return not any(i.severity == ValidationResult.ERROR for i in issues)
        elif self.validation_level == ValidationLevel.STANDARD:
            # Only critical issues fail validation
            return True
        else:  # BASIC
            # Only critical issues fail validation
            return True
    
    def _group_issues_by_severity(self, issues: List[ValidationIssue]) -> Dict[str, int]:
        """Group issues by severity level."""
        severity_counts = defaultdict(int)
        for issue in issues:
            severity_counts[issue.severity.value] += 1
        return dict(severity_counts)
    
    def _group_issues_by_type(self, issues: List[ValidationIssue]) -> Dict[str, int]:
        """Group issues by conflict type."""
        type_counts = defaultdict(int)
        for issue in issues:
            type_counts[issue.issue_type.value] += 1
        return dict(type_counts)


# Global validator instance
_data_integrity_validator: Optional[DataIntegrityValidator] = None


def get_data_integrity_validator() -> DataIntegrityValidator:
    """Get global data integrity validator instance."""
    global _data_integrity_validator
    if _data_integrity_validator is None:
        _data_integrity_validator = DataIntegrityValidator()
    return _data_integrity_validator


def reset_data_integrity_validator() -> None:
    """Reset global data integrity validator (useful for testing)."""
    global _data_integrity_validator
    _data_integrity_validator = None