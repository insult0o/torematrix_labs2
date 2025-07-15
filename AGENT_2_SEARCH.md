# AGENT 2 ASSIGNMENT: Advanced Filters & Query Processing

## 🎯 Your Mission (Agent 2)
You are **Agent 2** implementing advanced filtering and query processing capabilities. Your role is to create sophisticated filter management, visual query builder, and saved filter sets on top of Agent 1's search infrastructure.

## 📋 Your Specific Tasks

### 1. Filter Management System
```python
# Create src/torematrix/ui/search/filters.py
class FilterManager:
    """Manages all filtering operations and combinations"""
    
    def __init__(self, search_engine: SearchEngine):
        self.search_engine = search_engine
        self.active_filters = []
        self.saved_filters = {}
    
    async def apply_filters(self, filters: List[Filter]) -> FilteredResults:
        """Apply multiple filters with complex logic"""
        
    async def combine_filters(self, filters: List[Filter], operator: LogicalOperator) -> CompositeFilter:
        """Combine filters with AND, OR, NOT operations"""
        
    async def save_filter_set(self, name: str, filters: List[Filter]) -> None:
        """Save filter combination for reuse"""
        
    async def load_filter_set(self, name: str) -> List[Filter]:
        """Load saved filter set"""
```

### 2. Type-Based Filtering
```python
# Create src/torematrix/ui/search/filters/type_filter.py
class TypeFilter(Filter):
    """Filter elements by type"""
    
    def __init__(self, element_types: List[ElementType]):
        self.element_types = element_types
    
    async def apply(self, elements: List[Element]) -> List[Element]:
        """Filter elements by specified types"""
        
    def get_available_types(self) -> List[ElementType]:
        """Get all available element types for filtering"""
```

### 3. Property-Based Filtering
```python
# Create src/torematrix/ui/search/filters/property_filter.py
class PropertyFilter(Filter):
    """Filter elements by properties and attributes"""
    
    def __init__(self, property_name: str, operator: ComparisonOperator, value: Any):
        self.property_name = property_name
        self.operator = operator
        self.value = value
    
    async def apply(self, elements: List[Element]) -> List[Element]:
        """Filter by property comparison"""
        
    def validate_property(self, property_name: str) -> bool:
        """Validate property exists and is filterable"""
```

### 4. Visual Query Builder
```python
# Create src/torematrix/ui/search/query_builder.py
class QueryBuilder:
    """Visual interface for building complex queries"""
    
    def __init__(self):
        self.query_tree = QueryNode()
        self.filters = []
    
    def add_condition(self, condition: FilterCondition) -> None:
        """Add filter condition to query"""
        
    def add_logical_operator(self, operator: LogicalOperator) -> None:
        """Add AND, OR, NOT operator"""
        
    def build_query(self) -> ComplexQuery:
        """Build final query from visual components"""
        
    def validate_query(self) -> ValidationResult:
        """Validate query structure and logic"""
```

### 5. Domain-Specific Language (DSL)
```python
# Create src/torematrix/ui/search/dsl.py
class QueryDSL:
    """Parse domain-specific language for power users"""
    
    def parse(self, dsl_query: str) -> ParsedQuery:
        """Parse DSL query into filter operations"""
        
    def validate_syntax(self, dsl_query: str) -> bool:
        """Validate DSL syntax"""
        
    def get_suggestions(self, partial_query: str) -> List[str]:
        """Get query completion suggestions"""
        
# Example DSL syntax:
# type:paragraph AND content:"important" OR (author:"smith" AND date:>2023-01-01)
```

### 6. Quick Filter Presets
```python
# Create src/torematrix/ui/search/presets.py
class FilterPresets:
    """Predefined filter sets for common operations"""
    
    PRESET_DEFINITIONS = {
        "recent_documents": {"date": ">7d", "type": "document"},
        "long_paragraphs": {"type": "paragraph", "word_count": ">100"},
        "images_with_text": {"type": "image", "has_ocr": True},
        "tables_with_data": {"type": "table", "row_count": ">2"}
    }
    
    def get_preset(self, preset_name: str) -> List[Filter]:
        """Get predefined filter set"""
        
    def apply_preset(self, preset_name: str) -> FilteredResults:
        """Apply preset filter directly"""
```

## 🔧 Files You Must Create

### Core Implementation Files
```
src/torematrix/ui/search/
├── filters.py                     # FilterManager class (PRIMARY)
├── query_builder.py               # Visual QueryBuilder (PRIMARY)
├── dsl.py                        # Domain-specific language parser
├── presets.py                    # Quick filter presets
└── combinations.py               # Filter combination logic

src/torematrix/ui/search/filters/
├── __init__.py
├── type_filter.py                # Element type filtering
├── property_filter.py            # Property-based filtering
├── date_filter.py                # Date range filtering
├── text_filter.py                # Advanced text filtering
└── custom_filter.py              # User-defined filters
```

### Test Files (MANDATORY >95% Coverage)
```
tests/unit/ui/search/
├── test_filters.py               # FilterManager tests (25+ tests)
├── test_query_builder.py         # QueryBuilder tests (20+ tests)
├── test_dsl.py                   # DSL parser tests (15+ tests)
├── test_presets.py               # Preset tests (10+ tests)
└── test_combinations.py          # Filter combination tests (15+ tests)

tests/unit/ui/search/filters/
├── test_type_filter.py           # Type filter tests
├── test_property_filter.py       # Property filter tests
├── test_date_filter.py           # Date filter tests
├── test_text_filter.py           # Text filter tests
└── test_custom_filter.py         # Custom filter tests
```

## 🧪 Acceptance Criteria You Must Meet

### Functional Requirements
- [ ] **Type-based Filtering**: Support for all element types from unified model
- [ ] **Property-based Filters**: Comparison operators (=, !=, >, <, contains, etc.)
- [ ] **Visual Query Builder**: Drag-and-drop interface for building queries
- [ ] **Complex Combinations**: AND, OR, NOT operations with proper precedence
- [ ] **Saved Filter Sets**: User-defined filter combinations with persistence
- [ ] **DSL Support**: Text-based query language for power users
- [ ] **Quick Presets**: Common filter combinations ready to use
- [ ] **Filter Validation**: Error checking and user feedback

### Performance Requirements
- [ ] **Filter Processing**: <50ms for complex filter combinations
- [ ] **Query Building**: Real-time validation during construction
- [ ] **Filter Persistence**: <100ms save/load operations
- [ ] **Memory Efficiency**: Minimal memory overhead for filter objects

### Integration Requirements
- [ ] **Agent 1 Integration**: Seamless use of SearchEngine and SearchIndexer
- [ ] **Element Model Integration**: Support for all element properties
- [ ] **State Management**: Filter state persistence across sessions

## 🔌 Integration Points

### Dependencies (What You Need From Agent 1)
- **SearchEngine**: Core search functionality
- **SearchIndexer**: Access to indexed data
- **Query Types**: Parsed query structures
- **Search Results**: Result format from Agent 1

### What You Provide (For Agent 3 & 4)
- **FilterManager Interface**: Complete filtering system
- **QueryBuilder Interface**: Visual query construction
- **Filter Types**: All filter implementations
- **DSL Parser**: Text-based query parsing

## 🚀 Getting Started

### 1. Create Your Feature Branch
```bash
git checkout main
git pull origin main
git checkout -b feature/search-filters-agent2-issue214
```

### 2. Study Agent 1's Work
```bash
# Review Agent 1's interfaces
cat src/torematrix/ui/search/engine.py
cat src/torematrix/ui/search/types.py
```

### 3. Start with Filter Base Classes
```python
# Create base filter architecture first
from abc import ABC, abstractmethod

class Filter(ABC):
    """Base class for all filters"""
    
    @abstractmethod
    async def apply(self, elements: List[Element]) -> List[Element]:
        """Apply this filter to element list"""
        pass
    
    @abstractmethod
    def validate(self) -> bool:
        """Validate filter configuration"""
        pass
```

## 🎯 Success Metrics

### Performance Targets
- **Filter Speed**: <50ms for complex filter combinations
- **Query Building**: Real-time UI updates
- **Saved Filters**: Support for 1000+ saved filter sets
- **DSL Parsing**: <10ms for complex queries

### Usability Targets
- **Filter Types**: Support 20+ different filter types
- **Query Complexity**: Handle 10+ nested conditions
- **Preset Library**: 20+ useful filter presets
- **Error Handling**: Clear validation messages

## 📚 Technical Implementation Details

### Filter Combination Logic
```python
class CompositeFilter:
    """Combines multiple filters with logical operators"""
    
    def __init__(self, left_filter: Filter, operator: LogicalOperator, right_filter: Filter):
        self.left_filter = left_filter
        self.operator = operator
        self.right_filter = right_filter
    
    async def apply(self, elements: List[Element]) -> List[Element]:
        """Apply composite filter with proper precedence"""
        left_results = await self.left_filter.apply(elements)
        right_results = await self.right_filter.apply(elements)
        
        if self.operator == LogicalOperator.AND:
            return list(set(left_results) & set(right_results))
        elif self.operator == LogicalOperator.OR:
            return list(set(left_results) | set(right_results))
        elif self.operator == LogicalOperator.NOT:
            return [e for e in elements if e not in right_results]
```

### DSL Grammar Example
```
query := expression
expression := term | expression AND expression | expression OR expression | NOT expression | "(" expression ")"
term := property_filter | type_filter | text_filter
property_filter := PROPERTY OPERATOR VALUE
type_filter := "type:" TYPE_NAME
text_filter := "content:" QUOTED_STRING
```

### Visual Query Builder Architecture
```python
class QueryNode:
    """Node in visual query tree"""
    
    def __init__(self, node_type: NodeType):
        self.node_type = node_type  # FILTER, OPERATOR, GROUP
        self.children = []
        self.filter = None
        self.operator = None
    
    def to_filter(self) -> Filter:
        """Convert visual tree to executable filter"""
```

## 🔗 Communication Protocol

### Integration with Agent 1
```python
# Use Agent 1's SearchEngine like this:
search_engine = SearchEngine(indexer)
base_results = await search_engine.search(query_text)
filtered_results = await filter_manager.apply_filters(filters)
```

### Handoff to Agent 3
Provide clean interfaces for performance optimization:
- Well-defined Filter abstract base class
- Efficient filter combination algorithms
- Clear performance measurement points
- Cacheable filter results

## 🏁 Definition of Done

Your work is complete when:
1. ✅ All filter types implemented and tested
2. ✅ Visual query builder fully functional
3. ✅ DSL parser handles complex queries
4. ✅ Saved filter sets work with persistence
5. ✅ Integration with Agent 1's search engine verified
6. ✅ >95% test coverage achieved
7. ✅ Performance targets met
8. ✅ Ready for Agent 3 optimization

## 🤝 Handoff to Agent 3

When you're done, ensure:
- **FilterManager** is performant and extensible
- **Query complexity** is well-handled
- **Performance bottlenecks** are identified and documented
- **Caching opportunities** are noted for Agent 3
- **Memory usage patterns** are documented

Agent 3 will optimize your filtering system for high-performance scenarios!