"""
Core hierarchy operations engine for document element management.

This module provides the fundamental operations for managing document element
hierarchies, including parent-child relationships, ordering, and validation.
"""

from typing import Dict, List, Optional, Set, Tuple, Union, Any
from dataclasses import dataclass, field
from enum import Enum
import logging
from abc import ABC, abstractmethod

from torematrix.core.models.element import Element, ElementType
from torematrix.core.events import EventBus
from torematrix.core.state import StateStore
from torematrix.utils.geometry import Point, Rect


logger = logging.getLogger(__name__)


class HierarchyOperation(Enum):
    """Types of hierarchy operations."""
    MOVE = "move"
    REORDER = "reorder"
    REPARENT = "reparent"
    DELETE = "delete"
    INSERT = "insert"
    VALIDATE = "validate"
    ANALYZE = "analyze"


@dataclass
class HierarchyConstraint:
    """Represents a constraint on hierarchy operations."""
    constraint_type: str
    target_element: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    error_message: str = ""


@dataclass
class ValidationResult:
    """Result of hierarchy validation."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    violations: List[HierarchyConstraint] = field(default_factory=list)


@dataclass
class HierarchyChange:
    """Represents a change in hierarchy."""
    operation: HierarchyOperation
    element_id: str
    old_parent_id: Optional[str] = None
    new_parent_id: Optional[str] = None
    old_position: Optional[int] = None
    new_position: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HierarchySnapshot:
    """Snapshot of hierarchy state for undo/redo."""
    timestamp: float
    changes: List[HierarchyChange] = field(default_factory=list)
    element_states: Dict[str, Dict[str, Any]] = field(default_factory=dict)


class HierarchyValidator(ABC):
    """Abstract base class for hierarchy validators."""
    
    @abstractmethod
    def validate(self, elements: Dict[str, Element], change: HierarchyChange) -> ValidationResult:
        """Validate a hierarchy change."""
        pass
    
    @abstractmethod
    def get_constraints(self) -> List[HierarchyConstraint]:
        """Get validation constraints."""
        pass


class ReadingOrderValidator(HierarchyValidator):
    """Validates reading order constraints."""
    
    def validate(self, elements: Dict[str, Element], change: HierarchyChange) -> ValidationResult:
        """Validate reading order constraints."""
        result = ValidationResult(is_valid=True)
        
        if change.operation == HierarchyOperation.REORDER:
            element = elements.get(change.element_id)
            if not element:
                result.is_valid = False
                result.errors.append(f"Element {change.element_id} not found")
                return result
            
            # Check spatial ordering
            if element.parent_id:
                parent = elements.get(element.parent_id)
                if parent and parent.children:
                    siblings = [elements[child_id] for child_id in parent.children 
                              if child_id in elements]
                    
                    # Sort siblings by position
                    sorted_siblings = sorted(siblings, key=lambda e: (e.bounds.y, e.bounds.x))
                    expected_order = [s.id for s in sorted_siblings]
                    
                    if change.new_position is not None:
                        current_order = list(parent.children)
                        # Simulate the move
                        current_order.remove(change.element_id)
                        current_order.insert(change.new_position, change.element_id)
                        
                        # Check if new order deviates too much from spatial order
                        deviation_score = self._calculate_order_deviation(
                            current_order, expected_order
                        )
                        
                        if deviation_score > 0.5:  # 50% deviation threshold
                            result.warnings.append(
                                f"Reading order may not follow spatial layout (deviation: {deviation_score:.1%})"
                            )
        
        return result
    
    def get_constraints(self) -> List[HierarchyConstraint]:
        """Get reading order constraints."""
        return [
            HierarchyConstraint(
                constraint_type="spatial_order",
                target_element="*",
                parameters={"max_deviation": 0.5},
                error_message="Reading order should follow spatial layout"
            )
        ]
    
    def _calculate_order_deviation(self, actual: List[str], expected: List[str]) -> float:
        """Calculate deviation between actual and expected order."""
        if not actual or not expected:
            return 0.0
        
        # Calculate Kendall's tau distance
        inversions = 0
        total_pairs = 0
        
        for i in range(len(actual)):
            for j in range(i + 1, len(actual)):
                if actual[i] in expected and actual[j] in expected:
                    expected_i = expected.index(actual[i])
                    expected_j = expected.index(actual[j])
                    
                    if (expected_i > expected_j):  # Inversion
                        inversions += 1
                    total_pairs += 1
        
        return inversions / total_pairs if total_pairs > 0 else 0.0


class TypeConstraintValidator(HierarchyValidator):
    """Validates element type constraints."""
    
    # Define valid parent-child relationships
    VALID_RELATIONSHIPS = {
        ElementType.TITLE: [ElementType.NARRATIVE_TEXT, ElementType.LIST_ITEM],
        ElementType.NARRATIVE_TEXT: [ElementType.NARRATIVE_TEXT, ElementType.LIST_ITEM],
        ElementType.LIST_ITEM: [ElementType.NARRATIVE_TEXT, ElementType.LIST_ITEM],
        ElementType.TABLE: [ElementType.TABLE_CELL],
        ElementType.TABLE_CELL: [ElementType.NARRATIVE_TEXT, ElementType.LIST_ITEM],
        ElementType.FIGURE: [ElementType.FIGURE_CAPTION, ElementType.IMAGE],
        ElementType.FIGURE_CAPTION: [ElementType.NARRATIVE_TEXT],
        ElementType.HEADER: [ElementType.NARRATIVE_TEXT],
        ElementType.FOOTER: [ElementType.NARRATIVE_TEXT],
        ElementType.PAGE_BREAK: [],
        ElementType.FORM: [ElementType.FORM_FIELD],
        ElementType.FORM_FIELD: [ElementType.NARRATIVE_TEXT],
        ElementType.UNCATEGORIZED: []
    }
    
    def validate(self, elements: Dict[str, Element], change: HierarchyChange) -> ValidationResult:
        """Validate type constraints."""
        result = ValidationResult(is_valid=True)
        
        if change.operation == HierarchyOperation.REPARENT:
            element = elements.get(change.element_id)
            if not element:
                result.is_valid = False
                result.errors.append(f"Element {change.element_id} not found")
                return result
            
            if change.new_parent_id:
                parent = elements.get(change.new_parent_id)
                if not parent:
                    result.is_valid = False
                    result.errors.append(f"Parent {change.new_parent_id} not found")
                    return result
                
                # Check if parent can contain this child type
                allowed_children = self.VALID_RELATIONSHIPS.get(parent.element_type, [])
                if element.element_type not in allowed_children:
                    result.is_valid = False
                    result.errors.append(
                        f"Element type {element.element_type.value} cannot be child of {parent.element_type.value}"
                    )
                    result.violations.append(
                        HierarchyConstraint(
                            constraint_type="type_constraint",
                            target_element=element.id,
                            parameters={"parent_type": parent.element_type.value},
                            error_message=f"Invalid parent-child relationship"
                        )
                    )
        
        return result
    
    def get_constraints(self) -> List[HierarchyConstraint]:
        """Get type constraints."""
        constraints = []
        for parent_type, child_types in self.VALID_RELATIONSHIPS.items():
            constraints.append(
                HierarchyConstraint(
                    constraint_type="type_constraint",
                    target_element=parent_type.value,
                    parameters={"allowed_children": [ct.value for ct in child_types]},
                    error_message=f"Invalid child type for {parent_type.value}"
                )
            )
        return constraints


class DepthConstraintValidator(HierarchyValidator):
    """Validates hierarchy depth constraints."""
    
    MAX_DEPTH = 10  # Maximum nesting depth
    
    def validate(self, elements: Dict[str, Element], change: HierarchyChange) -> ValidationResult:
        """Validate depth constraints."""
        result = ValidationResult(is_valid=True)
        
        if change.operation in [HierarchyOperation.REPARENT, HierarchyOperation.INSERT]:
            element = elements.get(change.element_id)
            if not element:
                result.is_valid = False
                result.errors.append(f"Element {change.element_id} not found")
                return result
            
            if change.new_parent_id:
                # Calculate depth after the change
                depth = self._calculate_depth(elements, change.new_parent_id)
                if depth >= self.MAX_DEPTH:
                    result.is_valid = False
                    result.errors.append(
                        f"Maximum hierarchy depth ({self.MAX_DEPTH}) would be exceeded"
                    )
                    result.violations.append(
                        HierarchyConstraint(
                            constraint_type="depth_constraint",
                            target_element=element.id,
                            parameters={"max_depth": self.MAX_DEPTH, "current_depth": depth},
                            error_message="Hierarchy too deep"
                        )
                    )
        
        return result
    
    def get_constraints(self) -> List[HierarchyConstraint]:
        """Get depth constraints."""
        return [
            HierarchyConstraint(
                constraint_type="depth_constraint",
                target_element="*",
                parameters={"max_depth": self.MAX_DEPTH},
                error_message=f"Maximum hierarchy depth is {self.MAX_DEPTH}"
            )
        ]
    
    def _calculate_depth(self, elements: Dict[str, Element], element_id: str) -> int:
        """Calculate depth of an element in the hierarchy."""
        depth = 0
        current_id = element_id
        visited = set()
        
        while current_id and current_id not in visited:
            visited.add(current_id)
            element = elements.get(current_id)
            if element and element.parent_id:
                depth += 1
                current_id = element.parent_id
            else:
                break
        
        return depth


class HierarchyManager:
    """Manages document element hierarchy operations."""
    
    def __init__(self, state_store: StateStore, event_bus: EventBus):
        """Initialize hierarchy manager."""
        self.state_store = state_store
        self.event_bus = event_bus
        self._validators: List[HierarchyValidator] = []
        self._change_history: List[HierarchyChange] = []
        self._snapshots: List[HierarchySnapshot] = []
        self._max_history_size = 1000
        
        # Initialize default validators
        self._init_validators()
        
        # Subscribe to state changes
        self.event_bus.subscribe('element_created', self._on_element_created)
        self.event_bus.subscribe('element_updated', self._on_element_updated)
        self.event_bus.subscribe('element_deleted', self._on_element_deleted)
    
    def _init_validators(self):
        """Initialize default validators."""
        self._validators = [
            ReadingOrderValidator(),
            TypeConstraintValidator(),
            DepthConstraintValidator()
        ]
    
    def add_validator(self, validator: HierarchyValidator):
        """Add a custom validator."""
        self._validators.append(validator)
    
    def remove_validator(self, validator: HierarchyValidator):
        """Remove a validator."""
        if validator in self._validators:
            self._validators.remove(validator)
    
    def move_element(self, element_id: str, new_parent_id: Optional[str], 
                    new_position: Optional[int] = None) -> ValidationResult:
        """Move element to new parent and position."""
        change = HierarchyChange(
            operation=HierarchyOperation.REPARENT,
            element_id=element_id,
            new_parent_id=new_parent_id,
            new_position=new_position
        )
        
        return self._execute_change(change)
    
    def reorder_element(self, element_id: str, new_position: int) -> ValidationResult:
        """Reorder element within its parent."""
        change = HierarchyChange(
            operation=HierarchyOperation.REORDER,
            element_id=element_id,
            new_position=new_position
        )
        
        return self._execute_change(change)
    
    def delete_element(self, element_id: str) -> ValidationResult:
        """Delete element and handle children."""
        change = HierarchyChange(
            operation=HierarchyOperation.DELETE,
            element_id=element_id
        )
        
        return self._execute_change(change)
    
    def insert_element(self, element: Element, parent_id: Optional[str] = None, 
                      position: Optional[int] = None) -> ValidationResult:
        """Insert new element into hierarchy."""
        change = HierarchyChange(
            operation=HierarchyOperation.INSERT,
            element_id=element.id,
            new_parent_id=parent_id,
            new_position=position
        )
        
        return self._execute_change(change)
    
    def validate_hierarchy(self, elements: Optional[Dict[str, Element]] = None) -> ValidationResult:
        """Validate entire hierarchy."""
        if elements is None:
            elements = self.state_store.get_all_elements()
        
        result = ValidationResult(is_valid=True)
        
        # Check for cycles
        cycle_check = self._check_for_cycles(elements)
        if not cycle_check.is_valid:
            result.is_valid = False
            result.errors.extend(cycle_check.errors)
        
        # Check orphaned elements
        orphan_check = self._check_for_orphans(elements)
        if orphan_check.warnings:
            result.warnings.extend(orphan_check.warnings)
        
        # Run all validators
        for validator in self._validators:
            # Create a dummy change for validation
            dummy_change = HierarchyChange(
                operation=HierarchyOperation.VALIDATE,
                element_id=""
            )
            
            validator_result = validator.validate(elements, dummy_change)
            if not validator_result.is_valid:
                result.is_valid = False
                result.errors.extend(validator_result.errors)
            result.warnings.extend(validator_result.warnings)
            result.violations.extend(validator_result.violations)
        
        return result
    
    def get_hierarchy_tree(self, root_id: Optional[str] = None) -> Dict[str, Any]:
        """Get hierarchy as nested tree structure."""
        elements = self.state_store.get_all_elements()
        
        if root_id:
            roots = [elements[root_id]] if root_id in elements else []
        else:
            roots = [e for e in elements.values() if not e.parent_id]
        
        def build_tree(element: Element) -> Dict[str, Any]:
            tree = {
                'id': element.id,
                'type': element.element_type.value,
                'text': element.text[:50] + '...' if len(element.text) > 50 else element.text,
                'bounds': {
                    'x': element.bounds.x,
                    'y': element.bounds.y,
                    'width': element.bounds.width,
                    'height': element.bounds.height
                },
                'children': []
            }
            
            if element.children:
                for child_id in element.children:
                    if child_id in elements:
                        child_tree = build_tree(elements[child_id])
                        tree['children'].append(child_tree)
            
            return tree
        
        return {
            'roots': [build_tree(root) for root in roots],
            'total_elements': len(elements),
            'max_depth': self._calculate_max_depth(elements)
        }
    
    def get_reading_order(self, parent_id: Optional[str] = None) -> List[str]:
        """Get reading order for elements."""
        elements = self.state_store.get_all_elements()
        
        if parent_id:
            parent = elements.get(parent_id)
            if parent and parent.children:
                children = [elements[child_id] for child_id in parent.children 
                          if child_id in elements]
            else:
                children = []
        else:
            children = [e for e in elements.values() if not e.parent_id]
        
        # Sort by position (top-left to bottom-right)
        sorted_children = sorted(children, key=lambda e: (e.bounds.y, e.bounds.x))
        return [child.id for child in sorted_children]
    
    def create_snapshot(self) -> HierarchySnapshot:
        """Create a snapshot of current hierarchy state."""
        elements = self.state_store.get_all_elements()
        
        element_states = {}
        for element_id, element in elements.items():
            element_states[element_id] = {
                'parent_id': element.parent_id,
                'children': list(element.children) if element.children else [],
                'element_type': element.element_type.value,
                'bounds': {
                    'x': element.bounds.x,
                    'y': element.bounds.y,
                    'width': element.bounds.width,
                    'height': element.bounds.height
                }
            }
        
        snapshot = HierarchySnapshot(
            timestamp=self.state_store.current_timestamp,
            changes=list(self._change_history),
            element_states=element_states
        )
        
        self._snapshots.append(snapshot)
        
        # Limit snapshot history
        if len(self._snapshots) > 50:
            self._snapshots = self._snapshots[-50:]
        
        return snapshot
    
    def restore_snapshot(self, snapshot: HierarchySnapshot) -> bool:
        """Restore hierarchy from snapshot."""
        try:
            # Restore element states
            for element_id, state in snapshot.element_states.items():
                element = self.state_store.get_element(element_id)
                if element:
                    element.parent_id = state['parent_id']
                    element.children = state['children']
                    element.element_type = ElementType(state['element_type'])
                    element.bounds = Rect(
                        state['bounds']['x'],
                        state['bounds']['y'],
                        state['bounds']['width'],
                        state['bounds']['height']
                    )
                    
                    self.state_store.update_element(element)
            
            # Restore change history
            self._change_history = list(snapshot.changes)
            
            # Emit restoration event
            self.event_bus.emit('hierarchy_restored', {
                'timestamp': snapshot.timestamp,
                'element_count': len(snapshot.element_states)
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore snapshot: {e}")
            return False
    
    def _execute_change(self, change: HierarchyChange) -> ValidationResult:
        """Execute a hierarchy change."""
        elements = self.state_store.get_all_elements()
        
        # Store old values
        element = elements.get(change.element_id)
        if element:
            change.old_parent_id = element.parent_id
            if element.parent_id:
                old_parent = elements.get(element.parent_id)
                if old_parent and old_parent.children:
                    change.old_position = old_parent.children.index(change.element_id)
        
        # Validate change
        validation_result = self._validate_change(elements, change)
        if not validation_result.is_valid:
            return validation_result
        
        # Apply change
        try:
            self._apply_change(elements, change)
            
            # Add to history
            self._change_history.append(change)
            if len(self._change_history) > self._max_history_size:
                self._change_history = self._change_history[-self._max_history_size:]
            
            # Emit change event
            self.event_bus.emit('hierarchy_changed', {
                'operation': change.operation.value,
                'element_id': change.element_id,
                'old_parent_id': change.old_parent_id,
                'new_parent_id': change.new_parent_id,
                'old_position': change.old_position,
                'new_position': change.new_position
            })
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Failed to execute change: {e}")
            validation_result.is_valid = False
            validation_result.errors.append(f"Execution failed: {e}")
            return validation_result
    
    def _validate_change(self, elements: Dict[str, Element], change: HierarchyChange) -> ValidationResult:
        """Validate a hierarchy change."""
        result = ValidationResult(is_valid=True)
        
        # Run all validators
        for validator in self._validators:
            validator_result = validator.validate(elements, change)
            if not validator_result.is_valid:
                result.is_valid = False
                result.errors.extend(validator_result.errors)
            result.warnings.extend(validator_result.warnings)
            result.violations.extend(validator_result.violations)
        
        return result
    
    def _apply_change(self, elements: Dict[str, Element], change: HierarchyChange):
        """Apply a hierarchy change."""
        element = elements.get(change.element_id)
        if not element:
            raise ValueError(f"Element {change.element_id} not found")
        
        if change.operation == HierarchyOperation.REPARENT:
            # Remove from old parent
            if element.parent_id:
                old_parent = elements.get(element.parent_id)
                if old_parent and old_parent.children:
                    old_parent.children.remove(change.element_id)
                    self.state_store.update_element(old_parent)
            
            # Add to new parent
            if change.new_parent_id:
                new_parent = elements.get(change.new_parent_id)
                if new_parent:
                    if not new_parent.children:
                        new_parent.children = []
                    
                    if change.new_position is not None:
                        new_parent.children.insert(change.new_position, change.element_id)
                    else:
                        new_parent.children.append(change.element_id)
                    
                    self.state_store.update_element(new_parent)
            
            # Update element's parent
            element.parent_id = change.new_parent_id
            self.state_store.update_element(element)
        
        elif change.operation == HierarchyOperation.REORDER:
            if element.parent_id:
                parent = elements.get(element.parent_id)
                if parent and parent.children:
                    parent.children.remove(change.element_id)
                    parent.children.insert(change.new_position, change.element_id)
                    self.state_store.update_element(parent)
        
        elif change.operation == HierarchyOperation.DELETE:
            # Remove from parent
            if element.parent_id:
                parent = elements.get(element.parent_id)
                if parent and parent.children:
                    parent.children.remove(change.element_id)
                    self.state_store.update_element(parent)
            
            # Handle children (move to parent's parent)
            if element.children:
                for child_id in element.children:
                    child = elements.get(child_id)
                    if child:
                        child.parent_id = element.parent_id
                        self.state_store.update_element(child)
            
            # Delete element
            self.state_store.delete_element(change.element_id)
    
    def _check_for_cycles(self, elements: Dict[str, Element]) -> ValidationResult:
        """Check for cycles in hierarchy."""
        result = ValidationResult(is_valid=True)
        
        def has_cycle(element_id: str, visited: Set[str], path: Set[str]) -> bool:
            if element_id in path:
                return True
            if element_id in visited:
                return False
            
            visited.add(element_id)
            path.add(element_id)
            
            element = elements.get(element_id)
            if element and element.children:
                for child_id in element.children:
                    if has_cycle(child_id, visited, path):
                        return True
            
            path.remove(element_id)
            return False
        
        visited = set()
        for element_id in elements:
            if element_id not in visited:
                if has_cycle(element_id, visited, set()):
                    result.is_valid = False
                    result.errors.append(f"Cycle detected involving element {element_id}")
        
        return result
    
    def _check_for_orphans(self, elements: Dict[str, Element]) -> ValidationResult:
        """Check for orphaned elements."""
        result = ValidationResult(is_valid=True)
        
        all_children = set()
        for element in elements.values():
            if element.children:
                all_children.update(element.children)
        
        # Elements with parents that don't exist
        for element in elements.values():
            if element.parent_id and element.parent_id not in elements:
                result.warnings.append(f"Element {element.id} has missing parent {element.parent_id}")
        
        # Elements referenced as children but don't exist
        for element in elements.values():
            if element.children:
                for child_id in element.children:
                    if child_id not in elements:
                        result.warnings.append(f"Element {element.id} references missing child {child_id}")
        
        return result
    
    def _calculate_max_depth(self, elements: Dict[str, Element]) -> int:
        """Calculate maximum depth of hierarchy."""
        max_depth = 0
        
        def calculate_depth(element_id: str, current_depth: int = 0) -> int:
            nonlocal max_depth
            max_depth = max(max_depth, current_depth)
            
            element = elements.get(element_id)
            if element and element.children:
                for child_id in element.children:
                    calculate_depth(child_id, current_depth + 1)
            
            return max_depth
        
        # Start from root elements
        for element in elements.values():
            if not element.parent_id:
                calculate_depth(element.id)
        
        return max_depth
    
    def _on_element_created(self, event_data: Dict[str, Any]):
        """Handle element created event."""
        element_id = event_data.get('element_id')
        if element_id:
            change = HierarchyChange(
                operation=HierarchyOperation.INSERT,
                element_id=element_id,
                new_parent_id=event_data.get('parent_id'),
                new_position=event_data.get('position')
            )
            self._change_history.append(change)
    
    def _on_element_updated(self, event_data: Dict[str, Any]):
        """Handle element updated event."""
        # Track updates that affect hierarchy
        if 'parent_id' in event_data or 'children' in event_data:
            element_id = event_data.get('element_id')
            if element_id:
                change = HierarchyChange(
                    operation=HierarchyOperation.MOVE,
                    element_id=element_id,
                    metadata=event_data
                )
                self._change_history.append(change)
    
    def _on_element_deleted(self, event_data: Dict[str, Any]):
        """Handle element deleted event."""
        element_id = event_data.get('element_id')
        if element_id:
            change = HierarchyChange(
                operation=HierarchyOperation.DELETE,
                element_id=element_id
            )
            self._change_history.append(change)