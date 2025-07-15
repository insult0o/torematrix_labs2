# AGENT 1 - MERGE/SPLIT OPERATIONS ENGINE: CORE OPERATIONS & ALGORITHMS

## 🎯 **Your Assignment: Core Operations & Algorithms**

**GitHub Issue:** #234 - Merge/Split Operations Engine Sub-Issue #28.1: Core Operations & Algorithms  
**Parent Issue:** #28 - Merge/Split Operations Engine  
**Agent Role:** Foundation & Core Logic Specialist  
**Dependencies:** None (Foundation Agent)

## 📋 **Your Specific Tasks**

### 🔧 **Core Algorithm Implementation**
1. **Merge Algorithm**: Implement element merging with coordinate recalculation
2. **Split Algorithm**: Implement element splitting with boundary detection
3. **Coordinate Engine**: Handle coordinate transformations and validations
4. **Element Processing**: Core element manipulation and validation

### 🛠️ **Technical Implementation Requirements**

#### Files You Must Create:
```
src/torematrix/ui/dialogs/merge_split/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── merge_engine.py             # Core merge operations
│   ├── split_engine.py             # Core split operations
│   ├── coordinate_processor.py     # Coordinate calculations
│   └── element_processor.py        # Element manipulation
└── algorithms/
    ├── __init__.py
    ├── merge_algorithms.py         # Merge strategy implementations
    ├── split_algorithms.py         # Split strategy implementations
    ├── coordinate_algorithms.py    # Coordinate transformation math
    └── validation_algorithms.py    # Validation logic
```

#### Tests You Must Create:
```
tests/unit/ui/dialogs/merge_split/
├── test_merge_engine.py
├── test_split_engine.py
├── test_coordinate_processor.py
├── test_element_processor.py
├── test_merge_algorithms.py
├── test_split_algorithms.py
├── test_coordinate_algorithms.py
└── test_validation_algorithms.py
```

### 🎯 **Success Criteria - CHECK ALL BOXES**

#### Core Merge Operations
- [ ] Implement element merging with coordinate recalculation
- [ ] Handle different merge strategies (adjacent, overlapping, contained)
- [ ] Preserve element metadata during merge operations
- [ ] Validate merge feasibility before execution

#### Core Split Operations
- [ ] Implement element splitting with boundary detection
- [ ] Handle different split methods (horizontal, vertical, custom)
- [ ] Maintain element relationships after split
- [ ] Validate split points and boundaries

#### Coordinate Processing
- [ ] Implement coordinate transformation algorithms
- [ ] Handle coordinate validation and normalization
- [ ] Support different coordinate systems (absolute, relative)
- [ ] Optimize coordinate calculations for performance

#### Element Processing
- [ ] Core element manipulation functions
- [ ] Element validation and integrity checks
- [ ] Metadata preservation and updates
- [ ] Error handling for malformed elements

#### Testing Requirements
- [ ] Unit tests with >95% coverage
- [ ] Algorithm correctness verification
- [ ] Performance benchmarks for large elements
- [ ] Edge case testing (empty elements, invalid coordinates)

## 🔗 **Integration Points**
- **Event System**: Emit merge/split events for other components
- **Element Model**: Work with core element data structures
- **Coordinate System**: Interface with document coordinate systems
- **Validation System**: Integrate with element validation framework

## 📊 **Performance Targets**
- **Merge Speed**: <50ms for typical elements
- **Split Speed**: <30ms for typical elements
- **Coordinate Calculation**: <10ms for complex transformations
- **Memory Usage**: <50MB for 1000 elements

## 🚀 **Implementation Strategy**

### Phase 1: Core Engines (Day 1-2)
1. Implement `merge_engine.py` with basic merge operations
2. Implement `split_engine.py` with basic split operations
3. Create `coordinate_processor.py` for coordinate handling
4. Develop `element_processor.py` for element manipulation

### Phase 2: Advanced Algorithms (Day 3-4)
1. Implement merge algorithms for different strategies
2. Implement split algorithms for different methods
3. Create coordinate transformation algorithms
4. Develop validation algorithms

### Phase 3: Testing & Optimization (Day 5-6)
1. Create comprehensive unit tests
2. Performance testing and optimization
3. Edge case testing
4. Integration preparation

## 🧪 **Testing Requirements**

### Unit Tests (>95% coverage required)
- Test all merge strategies with various element types
- Test all split methods with different boundaries
- Test coordinate transformations and validations
- Test element processing with edge cases

### Performance Tests
- Benchmark merge operations with large elements
- Benchmark split operations with complex boundaries
- Test coordinate calculation performance
- Memory usage profiling

### Integration Tests
- Test event emission for merge/split operations
- Test integration with element model
- Test coordinate system compatibility
- Test validation system integration

## 🔧 **Technical Specifications**

### Merge Engine API
```python
class MergeEngine:
    def merge_elements(self, elements: List[Element]) -> MergeResult
    def can_merge(self, elements: List[Element]) -> bool
    def calculate_merged_coordinates(self, elements: List[Element]) -> Coordinates
    def merge_metadata(self, elements: List[Element]) -> Dict[str, Any]
```

### Split Engine API
```python
class SplitEngine:
    def split_element(self, element: Element, split_points: List[Point]) -> SplitResult
    def can_split(self, element: Element, split_points: List[Point]) -> bool
    def calculate_split_coordinates(self, element: Element, split_points: List[Point]) -> List[Coordinates]
    def distribute_metadata(self, element: Element, split_count: int) -> List[Dict[str, Any]]
```

## 🎯 **Ready to Start Command**
```bash
# Create your feature branch
git checkout main
git pull origin main  
git checkout -b feature/merge-split-core-agent1-issue234

# Begin your implementation
# Focus on creating the core merge/split engines first
```

## 📝 **Daily Progress Updates**
Post daily updates on GitHub Issue #234 with:
- Components completed
- Tests implemented
- Performance metrics
- Issues encountered
- Next day plans

## 🤝 **Agent Coordination**
- **Agent 2 Dependency**: Your core engines will be used by Agent 2's UI components
- **Agent 3 Dependency**: Your operations will be managed by Agent 3's state system
- **Agent 4 Dependency**: Your engines will be integrated by Agent 4's integration layer

---
**Agent 1 Mission**: Create the foundational merge/split operations engine that all other agents will build upon. Focus on correctness, performance, and reliability.