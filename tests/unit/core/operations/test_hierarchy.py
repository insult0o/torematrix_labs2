"""
Tests for hierarchy operations engine.
"""

import pytest
from unittest.mock import Mock, MagicMock
from dataclasses import dataclass
from typing import Dict, List, Optional

from torematrix.core.operations.hierarchy import (
    HierarchyManager,
    HierarchyOperation,
    HierarchyChange,
    HierarchyConstraint,
    ValidationResult,
    HierarchySnapshot,
    ReadingOrderValidator,
    TypeConstraintValidator,
    DepthConstraintValidator
)
from torematrix.core.models.element import Element, ElementType
from torematrix.core.events import EventBus
from torematrix.core.state import StateStore
from torematrix.utils.geometry import Rect


class TestHierarchyManager:
    """Test the HierarchyManager class."""
    
    @pytest.fixture
    def mock_state_store(self):
        """Create mock state store."""
        state_store = Mock(spec=StateStore)
        state_store.current_timestamp = 1000.0
        return state_store
    
    @pytest.fixture
    def mock_event_bus(self):
        """Create mock event bus."""
        event_bus = Mock(spec=EventBus)
        return event_bus
    
    @pytest.fixture
    def hierarchy_manager(self, mock_state_store, mock_event_bus):
        """Create hierarchy manager instance."""
        return HierarchyManager(mock_state_store, mock_event_bus)
    
    @pytest.fixture
    def sample_elements(self):
        """Create sample elements for testing."""
        return {
            'root': Element(
                id='root',
                element_type=ElementType.TITLE,
                text='Root Element',
                bounds=Rect(0, 0, 100, 50),
                parent_id=None,
                children=['child1', 'child2']
            ),
            'child1': Element(
                id='child1',
                element_type=ElementType.NARRATIVE_TEXT,
                text='Child 1',
                bounds=Rect(0, 60, 100, 30),
                parent_id='root',
                children=['grandchild1']
            ),
            'child2': Element(
                id='child2',
                element_type=ElementType.NARRATIVE_TEXT,
                text='Child 2',
                bounds=Rect(0, 100, 100, 30),
                parent_id='root',
                children=[]
            ),
            'grandchild1': Element(
                id='grandchild1',
                element_type=ElementType.LIST_ITEM,
                text='Grandchild 1',
                bounds=Rect(10, 140, 80, 20),
                parent_id='child1',
                children=[]
            )
        }
    
    def test_init(self, hierarchy_manager, mock_event_bus):
        """Test hierarchy manager initialization."""
        assert hierarchy_manager.state_store is not None
        assert hierarchy_manager.event_bus is not None
        assert len(hierarchy_manager._validators) == 3
        
        # Check event subscriptions
        mock_event_bus.subscribe.assert_any_call('element_created', hierarchy_manager._on_element_created)
        mock_event_bus.subscribe.assert_any_call('element_updated', hierarchy_manager._on_element_updated)
        mock_event_bus.subscribe.assert_any_call('element_deleted', hierarchy_manager._on_element_deleted)
    
    def test_move_element_success(self, hierarchy_manager, mock_state_store, sample_elements):
        """Test successful element move."""
        mock_state_store.get_all_elements.return_value = sample_elements
        mock_state_store.get_element.return_value = sample_elements['child1']
        
        result = hierarchy_manager.move_element('child1', 'child2', 0)
        
        assert result.is_valid
        assert len(result.errors) == 0
        assert mock_state_store.update_element.called
    
    def test_move_element_invalid_parent(self, hierarchy_manager, mock_state_store, sample_elements):
        """Test move element with invalid parent."""
        mock_state_store.get_all_elements.return_value = sample_elements
        
        # Try to move table cell under narrative text (invalid)
        table_cell = Element(
            id='table_cell',
            element_type=ElementType.TABLE_CELL,
            text='Table Cell',
            bounds=Rect(0, 0, 50, 20),
            parent_id=None,
            children=[]
        )
        
        elements_with_cell = {**sample_elements, 'table_cell': table_cell}
        mock_state_store.get_all_elements.return_value = elements_with_cell
        
        result = hierarchy_manager.move_element('table_cell', 'child1', 0)
        
        assert not result.is_valid
        assert len(result.errors) > 0
        assert "cannot be child of" in result.errors[0]
    
    def test_reorder_element(self, hierarchy_manager, mock_state_store, sample_elements):
        """Test element reordering."""
        mock_state_store.get_all_elements.return_value = sample_elements
        mock_state_store.get_element.return_value = sample_elements['child2']
        
        result = hierarchy_manager.reorder_element('child2', 0)
        
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_delete_element(self, hierarchy_manager, mock_state_store, sample_elements):
        """Test element deletion."""
        mock_state_store.get_all_elements.return_value = sample_elements
        mock_state_store.get_element.return_value = sample_elements['child1']
        
        result = hierarchy_manager.delete_element('child1')
        
        assert result.is_valid
        assert mock_state_store.delete_element.called
    
    def test_insert_element(self, hierarchy_manager, mock_state_store, sample_elements):
        """Test element insertion."""
        mock_state_store.get_all_elements.return_value = sample_elements
        
        new_element = Element(
            id='new_element',
            element_type=ElementType.NARRATIVE_TEXT,
            text='New Element',
            bounds=Rect(0, 200, 100, 30),
            parent_id=None,
            children=[]
        )
        
        result = hierarchy_manager.insert_element(new_element, 'root', 1)
        
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_validate_hierarchy_success(self, hierarchy_manager, mock_state_store, sample_elements):
        """Test successful hierarchy validation."""
        mock_state_store.get_all_elements.return_value = sample_elements
        
        result = hierarchy_manager.validate_hierarchy()
        
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_validate_hierarchy_with_cycle(self, hierarchy_manager, mock_state_store, sample_elements):
        """Test hierarchy validation with cycle."""
        # Create a cycle: root -> child1 -> grandchild1 -> root
        cyclic_elements = sample_elements.copy()
        cyclic_elements['root'].parent_id = 'grandchild1'
        cyclic_elements['grandchild1'].children = ['root']
        
        mock_state_store.get_all_elements.return_value = cyclic_elements
        
        result = hierarchy_manager.validate_hierarchy()
        
        assert not result.is_valid
        assert any("Cycle detected" in error for error in result.errors)
    
    def test_get_hierarchy_tree(self, hierarchy_manager, mock_state_store, sample_elements):
        """Test hierarchy tree generation."""
        mock_state_store.get_all_elements.return_value = sample_elements
        
        tree = hierarchy_manager.get_hierarchy_tree()
        
        assert 'roots' in tree
        assert 'total_elements' in tree
        assert 'max_depth' in tree
        assert tree['total_elements'] == 4
        assert tree['max_depth'] >= 2
        assert len(tree['roots']) == 1
        assert tree['roots'][0]['id'] == 'root'
        assert len(tree['roots'][0]['children']) == 2
    
    def test_get_reading_order(self, hierarchy_manager, mock_state_store, sample_elements):
        """Test reading order calculation."""
        mock_state_store.get_all_elements.return_value = sample_elements
        
        # Test root level reading order
        order = hierarchy_manager.get_reading_order()
        assert order == ['root']
        
        # Test child level reading order
        order = hierarchy_manager.get_reading_order('root')
        assert len(order) == 2
        assert 'child1' in order
        assert 'child2' in order
    
    def test_create_snapshot(self, hierarchy_manager, mock_state_store, sample_elements):
        """Test snapshot creation."""
        mock_state_store.get_all_elements.return_value = sample_elements
        
        snapshot = hierarchy_manager.create_snapshot()
        
        assert isinstance(snapshot, HierarchySnapshot)
        assert snapshot.timestamp == 1000.0
        assert len(snapshot.element_states) == 4
        assert 'root' in snapshot.element_states
        assert len(hierarchy_manager._snapshots) == 1
    
    def test_restore_snapshot(self, hierarchy_manager, mock_state_store, sample_elements):
        """Test snapshot restoration."""
        mock_state_store.get_all_elements.return_value = sample_elements
        mock_state_store.get_element.side_effect = lambda id: sample_elements.get(id)
        
        # Create snapshot
        snapshot = hierarchy_manager.create_snapshot()
        
        # Restore snapshot
        result = hierarchy_manager.restore_snapshot(snapshot)
        
        assert result is True
        assert mock_state_store.update_element.called
    
    def test_add_remove_validator(self, hierarchy_manager):
        """Test adding and removing validators."""
        initial_count = len(hierarchy_manager._validators)
        
        # Add validator
        custom_validator = Mock()
        hierarchy_manager.add_validator(custom_validator)
        
        assert len(hierarchy_manager._validators) == initial_count + 1
        assert custom_validator in hierarchy_manager._validators
        
        # Remove validator
        hierarchy_manager.remove_validator(custom_validator)
        
        assert len(hierarchy_manager._validators) == initial_count
        assert custom_validator not in hierarchy_manager._validators
    
    def test_event_handlers(self, hierarchy_manager):
        """Test event handlers."""
        # Test element created event
        hierarchy_manager._on_element_created({'element_id': 'test1', 'parent_id': 'root'})
        
        assert len(hierarchy_manager._change_history) == 1
        assert hierarchy_manager._change_history[0].operation == HierarchyOperation.INSERT
        assert hierarchy_manager._change_history[0].element_id == 'test1'
        
        # Test element updated event
        hierarchy_manager._on_element_updated({'element_id': 'test2', 'parent_id': 'new_parent'})
        
        assert len(hierarchy_manager._change_history) == 2
        assert hierarchy_manager._change_history[1].operation == HierarchyOperation.MOVE
        assert hierarchy_manager._change_history[1].element_id == 'test2'
        
        # Test element deleted event
        hierarchy_manager._on_element_deleted({'element_id': 'test3'})
        
        assert len(hierarchy_manager._change_history) == 3
        assert hierarchy_manager._change_history[2].operation == HierarchyOperation.DELETE
        assert hierarchy_manager._change_history[2].element_id == 'test3'


class TestReadingOrderValidator:
    """Test the ReadingOrderValidator class."""
    
    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return ReadingOrderValidator()
    
    @pytest.fixture
    def elements_with_order(self):
        """Create elements with spatial order."""
        return {
            'parent': Element(
                id='parent',
                element_type=ElementType.TITLE,
                text='Parent',
                bounds=Rect(0, 0, 100, 50),
                parent_id=None,
                children=['child1', 'child2', 'child3']
            ),
            'child1': Element(
                id='child1',
                element_type=ElementType.NARRATIVE_TEXT,
                text='Child 1',
                bounds=Rect(0, 60, 100, 30),
                parent_id='parent',
                children=[]
            ),
            'child2': Element(
                id='child2',
                element_type=ElementType.NARRATIVE_TEXT,
                text='Child 2',
                bounds=Rect(0, 100, 100, 30),
                parent_id='parent',
                children=[]
            ),
            'child3': Element(
                id='child3',
                element_type=ElementType.NARRATIVE_TEXT,
                text='Child 3',
                bounds=Rect(0, 140, 100, 30),
                parent_id='parent',
                children=[]
            )
        }
    
    def test_validate_good_order(self, validator, elements_with_order):
        """Test validation with good reading order."""
        change = HierarchyChange(
            operation=HierarchyOperation.REORDER,
            element_id='child2',
            new_position=1
        )
        
        result = validator.validate(elements_with_order, change)
        
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_validate_bad_order(self, validator, elements_with_order):
        """Test validation with bad reading order."""
        change = HierarchyChange(
            operation=HierarchyOperation.REORDER,
            element_id='child3',
            new_position=0  # Moving last element to first position
        )
        
        result = validator.validate(elements_with_order, change)
        
        assert result.is_valid  # Should be valid but with warnings
        assert len(result.warnings) > 0
        assert "Reading order may not follow" in result.warnings[0]
    
    def test_get_constraints(self, validator):
        """Test constraint retrieval."""
        constraints = validator.get_constraints()
        
        assert len(constraints) == 1
        assert constraints[0].constraint_type == "spatial_order"
        assert constraints[0].target_element == "*"
    
    def test_calculate_order_deviation(self, validator):
        """Test order deviation calculation."""
        actual = ['a', 'b', 'c', 'd']
        expected = ['a', 'b', 'c', 'd']
        
        deviation = validator._calculate_order_deviation(actual, expected)
        assert deviation == 0.0
        
        actual = ['d', 'c', 'b', 'a']
        expected = ['a', 'b', 'c', 'd']
        
        deviation = validator._calculate_order_deviation(actual, expected)
        assert deviation == 1.0


class TestTypeConstraintValidator:
    """Test the TypeConstraintValidator class."""
    
    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return TypeConstraintValidator()
    
    @pytest.fixture
    def elements_with_types(self):
        """Create elements with different types."""
        return {
            'title': Element(
                id='title',
                element_type=ElementType.TITLE,
                text='Title',
                bounds=Rect(0, 0, 100, 50),
                parent_id=None,
                children=[]
            ),
            'text': Element(
                id='text',
                element_type=ElementType.NARRATIVE_TEXT,
                text='Text',
                bounds=Rect(0, 60, 100, 30),
                parent_id=None,
                children=[]
            ),
            'table': Element(
                id='table',
                element_type=ElementType.TABLE,
                text='Table',
                bounds=Rect(0, 100, 100, 50),
                parent_id=None,
                children=[]
            ),
            'cell': Element(
                id='cell',
                element_type=ElementType.TABLE_CELL,
                text='Cell',
                bounds=Rect(10, 110, 80, 20),
                parent_id=None,
                children=[]
            )
        }
    
    def test_validate_valid_relationship(self, validator, elements_with_types):
        """Test validation with valid parent-child relationship."""
        change = HierarchyChange(
            operation=HierarchyOperation.REPARENT,
            element_id='text',
            new_parent_id='title'
        )
        
        result = validator.validate(elements_with_types, change)
        
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_validate_invalid_relationship(self, validator, elements_with_types):
        """Test validation with invalid parent-child relationship."""
        change = HierarchyChange(
            operation=HierarchyOperation.REPARENT,
            element_id='cell',
            new_parent_id='text'  # Table cell cannot be child of narrative text
        )
        
        result = validator.validate(elements_with_types, change)
        
        assert not result.is_valid
        assert len(result.errors) > 0
        assert "cannot be child of" in result.errors[0]
        assert len(result.violations) == 1
    
    def test_validate_table_cell_under_table(self, validator, elements_with_types):
        """Test valid table cell under table."""
        change = HierarchyChange(
            operation=HierarchyOperation.REPARENT,
            element_id='cell',
            new_parent_id='table'
        )
        
        result = validator.validate(elements_with_types, change)
        
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_get_constraints(self, validator):
        """Test constraint retrieval."""
        constraints = validator.get_constraints()
        
        assert len(constraints) > 0
        assert all(c.constraint_type == "type_constraint" for c in constraints)
    
    def test_missing_element(self, validator, elements_with_types):
        """Test validation with missing element."""
        change = HierarchyChange(
            operation=HierarchyOperation.REPARENT,
            element_id='nonexistent',
            new_parent_id='title'
        )
        
        result = validator.validate(elements_with_types, change)
        
        assert not result.is_valid
        assert "not found" in result.errors[0]
    
    def test_missing_parent(self, validator, elements_with_types):
        """Test validation with missing parent."""
        change = HierarchyChange(
            operation=HierarchyOperation.REPARENT,
            element_id='text',
            new_parent_id='nonexistent'
        )
        
        result = validator.validate(elements_with_types, change)
        
        assert not result.is_valid
        assert "not found" in result.errors[0]


class TestDepthConstraintValidator:
    """Test the DepthConstraintValidator class."""
    
    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return DepthConstraintValidator()
    
    @pytest.fixture
    def deep_elements(self):
        """Create elements with deep hierarchy."""
        elements = {}
        parent_id = None
        
        # Create chain of 15 elements (exceeds max depth of 10)
        for i in range(15):
            element_id = f'element_{i}'
            elements[element_id] = Element(
                id=element_id,
                element_type=ElementType.NARRATIVE_TEXT,
                text=f'Element {i}',
                bounds=Rect(0, i * 20, 100, 20),
                parent_id=parent_id,
                children=[]
            )
            
            if parent_id:
                elements[parent_id].children = [element_id]
            
            parent_id = element_id
        
        return elements
    
    def test_validate_acceptable_depth(self, validator, deep_elements):
        """Test validation with acceptable depth."""
        # Use only first 8 elements (within depth limit)
        shallow_elements = {k: v for k, v in list(deep_elements.items())[:8]}
        
        change = HierarchyChange(
            operation=HierarchyOperation.REPARENT,
            element_id='element_7',
            new_parent_id='element_6'
        )
        
        result = validator.validate(shallow_elements, change)
        
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_validate_excessive_depth(self, validator, deep_elements):
        """Test validation with excessive depth."""
        change = HierarchyChange(
            operation=HierarchyOperation.REPARENT,
            element_id='element_14',
            new_parent_id='element_13'
        )
        
        result = validator.validate(deep_elements, change)
        
        assert not result.is_valid
        assert len(result.errors) > 0
        assert "Maximum hierarchy depth" in result.errors[0]
        assert len(result.violations) == 1
    
    def test_get_constraints(self, validator):
        """Test constraint retrieval."""
        constraints = validator.get_constraints()
        
        assert len(constraints) == 1
        assert constraints[0].constraint_type == "depth_constraint"
        assert constraints[0].target_element == "*"
        assert constraints[0].parameters["max_depth"] == 10
    
    def test_calculate_depth(self, validator, deep_elements):
        """Test depth calculation."""
        # Element 5 should be at depth 5
        depth = validator._calculate_depth(deep_elements, 'element_5')
        assert depth == 5
        
        # Element 0 (root) should be at depth 0
        depth = validator._calculate_depth(deep_elements, 'element_0')
        assert depth == 0
    
    def test_calculate_depth_with_cycle(self, validator, deep_elements):
        """Test depth calculation with cycle protection."""
        # Create a cycle
        deep_elements['element_0'].parent_id = 'element_5'
        deep_elements['element_5'].children = ['element_0']
        
        depth = validator._calculate_depth(deep_elements, 'element_3')
        
        # Should terminate and return some depth
        assert isinstance(depth, int)
        assert depth >= 0


class TestHierarchyDataClasses:
    """Test hierarchy data classes."""
    
    def test_hierarchy_constraint(self):
        """Test HierarchyConstraint creation."""
        constraint = HierarchyConstraint(
            constraint_type="test_constraint",
            target_element="test_element",
            parameters={"param1": "value1"},
            error_message="Test error"
        )
        
        assert constraint.constraint_type == "test_constraint"
        assert constraint.target_element == "test_element"
        assert constraint.parameters == {"param1": "value1"}
        assert constraint.error_message == "Test error"
    
    def test_validation_result(self):
        """Test ValidationResult creation."""
        result = ValidationResult(
            is_valid=False,
            errors=["Error 1", "Error 2"],
            warnings=["Warning 1"],
            violations=[HierarchyConstraint("test", "element")]
        )
        
        assert not result.is_valid
        assert len(result.errors) == 2
        assert len(result.warnings) == 1
        assert len(result.violations) == 1
    
    def test_hierarchy_change(self):
        """Test HierarchyChange creation."""
        change = HierarchyChange(
            operation=HierarchyOperation.REPARENT,
            element_id="test_element",
            old_parent_id="old_parent",
            new_parent_id="new_parent",
            old_position=1,
            new_position=2,
            metadata={"key": "value"}
        )
        
        assert change.operation == HierarchyOperation.REPARENT
        assert change.element_id == "test_element"
        assert change.old_parent_id == "old_parent"
        assert change.new_parent_id == "new_parent"
        assert change.old_position == 1
        assert change.new_position == 2
        assert change.metadata == {"key": "value"}
    
    def test_hierarchy_snapshot(self):
        """Test HierarchySnapshot creation."""
        snapshot = HierarchySnapshot(
            timestamp=1234.5,
            changes=[HierarchyChange(HierarchyOperation.MOVE, "test")],
            element_states={"element1": {"parent_id": "parent1"}}
        )
        
        assert snapshot.timestamp == 1234.5
        assert len(snapshot.changes) == 1
        assert len(snapshot.element_states) == 1
        assert snapshot.element_states["element1"]["parent_id"] == "parent1"


if __name__ == '__main__':
    pytest.main([__file__])