# Agent 1 - Hierarchy Management Core Operations Engine

## 🎯 Your Assignment
You are **Agent 1** for Issue #239 - Core Operations Engine. Your mission is to implement the foundational hierarchy management engine that provides core operations for document element hierarchy manipulation.

## 📋 Specific Tasks

### 1. Core Architecture
- Create `HierarchyManager` class as the main orchestrator
- Implement event-driven architecture with State Management integration
- Build comprehensive error handling and validation system
- Create operation types and change tracking structures

### 2. Hierarchy Operations
- Implement `move_element()` with validation
- Create `indent_element()` and `outdent_element()` functions
- Build `reorder_elements()` for bulk reordering
- Add `create_section_from_title()` functionality
- Support bulk operations with progress tracking

### 3. Validation Engine
- Create `ValidationResult` class for structured feedback
- Implement `HierarchyConstraints` with pluggable rules
- Add default constraints (max depth, list consistency, etc.)
- Build real-time validation with constraint checking

### 4. Change Tracking
- Create `HierarchyChange` class for operation history
- Implement undo/redo support with change stack
- Add change event emission for UI updates
- Support change batching for bulk operations

### 5. Metrics and Analysis
- Implement `get_hierarchy_metrics()` with comprehensive stats
- Add `get_reading_order()` with spatial analysis
- Create performance optimization for large hierarchies
- Build hierarchy analysis utilities

## 📁 Files to Create

### Primary Implementation
```
src/torematrix/core/operations/hierarchy.py
├── HierarchyManager (600+ lines)
│   ├── __init__(state_store, event_bus)
│   ├── get_current_hierarchy()
│   ├── move_element(element_id, new_parent_id, position)
│   ├── indent_element(element_id)
│   ├── outdent_element(element_id)
│   ├── reorder_elements(element_ids, new_positions)
│   ├── create_section_from_title(title_element_id)
│   ├── validate_hierarchy(hierarchy)
│   ├── get_reading_order(hierarchy)
│   ├── apply_hierarchy_template(template_name, element_ids)
│   ├── bulk_operation(operation, element_ids, **kwargs)
│   ├── get_hierarchy_metrics(hierarchy)
│   └── Private helper methods
├── HierarchyOperation (enum)
├── HierarchyChange (dataclass)
├── ValidationResult (dataclass)
├── HierarchyConstraints (class)
└── Default constraint functions
```

### Testing Implementation
```
tests/unit/operations/test_hierarchy.py
├── TestHierarchyManager (comprehensive test suite)
├── TestHierarchyConstraints (constraint testing)
├── TestHierarchyChange (change tracking tests)
├── TestValidationResult (validation tests)
└── Integration tests with mocked dependencies
```

## 🔧 Technical Implementation Details

### HierarchyManager Class Structure
```python
class HierarchyManager:
    def __init__(self, state_store: StateStore, event_bus: EventBus):
        self.state_store = state_store
        self.event_bus = event_bus
        self._validation_rules = []
        self._change_history = []
        self.max_depth = 10
        self.min_depth = 0
        
    def move_element(self, element_id: str, new_parent_id: Optional[str], 
                    position: Optional[int] = None) -> ValidationResult:
        # Validate move operation
        # Update element parent
        # Update state store
        # Emit change event
        # Record change for undo/redo
        
    def validate_hierarchy(self, hierarchy: Optional[ElementHierarchy] = None) -> ValidationResult:
        # Run basic hierarchy validation
        # Apply depth constraints
        # Check type-specific rules
        # Validate reading order
        # Apply custom validation rules
```

### ValidationResult Structure
```python
@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    suggestions: List[str]
```

### HierarchyConstraints Integration
```python
class HierarchyConstraints:
    def __init__(self):
        self.constraints = {}
    
    def add_constraint(self, name: str, constraint_func) -> None:
        self.constraints[name] = constraint_func
    
    def validate_constraints(self, hierarchy: ElementHierarchy) -> ValidationResult:
        # Apply all registered constraints
        # Collect errors, warnings, suggestions
        # Return consolidated result
```

## 🧪 Testing Requirements

### Unit Tests (>95% Coverage)
- **HierarchyManager Tests**: All operations with various scenarios
- **Validation Tests**: All constraint types and edge cases
- **Change Tracking Tests**: Undo/redo functionality
- **Performance Tests**: Large hierarchy handling
- **Integration Tests**: State store and event bus integration

### Test Structure
```python
class TestHierarchyManager:
    def setup_method(self):
        # Mock state store and event bus
        # Create test elements and hierarchy
        
    def test_move_element_validation(self):
        # Test move operation validation
        
    def test_indent_element(self):
        # Test indentation functionality
        
    def test_bulk_operation(self):
        # Test bulk operations
        
    def test_hierarchy_metrics(self):
        # Test metrics generation
```

## 🔗 Integration Points

### State Management Integration
- Subscribe to state changes for hierarchy updates
- Update state store with hierarchy modifications
- Maintain consistency with centralized state

### Event Bus Integration
- Emit `EventType.HIERARCHY_CHANGED` events
- Emit `EventType.HIERARCHY_VALIDATION_FAILED` events
- Listen for relevant document events

### Agent Dependencies
- **Agent 2**: Will use HierarchyManager for UI operations
- **Agent 3**: Will use reading order and validation functions
- **Agent 4**: Will use metrics and template functions

## 🚀 GitHub Workflow

### Branch Management
```bash
# Create your unique branch
git checkout main
git pull origin main
git checkout -b feature/hierarchy-operations-agent1-issue239
```

### Development Process
1. Implement HierarchyManager with all operations
2. Create comprehensive validation system
3. Add change tracking and undo/redo
4. Implement metrics and analysis
5. Write comprehensive tests (>95% coverage)
6. Verify all acceptance criteria

### Completion Workflow
1. Run all tests and ensure they pass
2. Stage and commit with standardized message
3. Push branch and create detailed PR
4. Update issue #239 with all checkboxes ticked
5. Close issue with completion summary

## ✅ Success Criteria

### Implementation Checklist
- [ ] HierarchyManager class with all operations implemented
- [ ] Comprehensive validation engine with constraints
- [ ] Change tracking with undo/redo support
- [ ] Bulk operations with progress tracking
- [ ] Hierarchy metrics and analysis functions
- [ ] Event-driven integration with state management
- [ ] Performance optimization for large hierarchies
- [ ] Comprehensive error handling

### Testing Checklist
- [ ] >95% code coverage achieved
- [ ] All hierarchy operations tested
- [ ] Validation engine thoroughly tested
- [ ] Change tracking verified
- [ ] Performance tests for large hierarchies
- [ ] Integration tests with mocked dependencies
- [ ] Edge cases and error conditions covered

### Quality Checklist
- [ ] Full type hints throughout
- [ ] Comprehensive docstrings
- [ ] Clean, maintainable code structure
- [ ] Proper error handling and logging
- [ ] Performance optimizations applied
- [ ] Memory efficient implementations

## 📊 Performance Targets
- Support hierarchies with 10,000+ elements
- Operations complete in <100ms for typical hierarchies
- Memory usage <100MB for large hierarchies
- Change tracking history limited to 100 operations
- Validation feedback in <50ms

## 🗣️ Communication Protocol
- Update issue #239 with progress regularly
- Comment on implementation decisions
- Report any blocking issues immediately
- Coordinate with planning on integration points

This foundation will enable Agents 2, 3, and 4 to build the complete hierarchy management system. Focus on creating a robust, well-tested core that can handle all the requirements efficiently.