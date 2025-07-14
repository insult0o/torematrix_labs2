# AGENT 2 - TABLE & LIST PARSERS

## 🎯 Your Mission
You are Agent 2, the Data Structure Specialist for the Document Element Parser system. Your role is to implement sophisticated parsers for tables and lists with complete structure preservation.

## 📋 Your Assignment
Implement specialized parsers for tables and lists that preserve complex structures, detect hierarchies, and validate data integrity.

**Sub-Issue**: #97 - Table & List Parsers Implementation  
**Dependencies**: Agent 1 (Base Parser Framework)  
**Timeline**: Days 2-3 (after Agent 1 completion)

## 🏗️ Files You Will Create

```
src/torematrix/core/processing/parsers/
├── table.py                   # Advanced table structure parser
├── list.py                    # Hierarchical list parser
└── structural/
    ├── __init__.py
    ├── table_analyzer.py      # Table structure analysis algorithms
    ├── list_detector.py       # List hierarchy detection
    ├── cell_merger.py         # Handle merged cells and spans
    ├── data_typer.py          # Column data type detection
    └── validation.py          # Structure validation rules

tests/unit/core/processing/parsers/
├── test_table_parser.py       # Table parsing functionality
├── test_list_parser.py        # List parsing functionality
└── structural/
    ├── test_table_analyzer.py
    ├── test_list_detector.py
    ├── test_cell_merger.py
    ├── test_data_typer.py
    └── test_validation.py

tests/fixtures/parsers/
├── sample_tables.json         # Complex table test cases
├── sample_lists.json          # Hierarchical list examples
└── edge_cases/
    ├── malformed_tables.json
    └── complex_lists.json
```

## 💻 Technical Implementation

### 1. Table Parser (`table.py`)
```python
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from .base import BaseParser, ParserResult, ParserMetadata
from .structural.table_analyzer import TableAnalyzer
from .structural.cell_merger import CellMerger
from .structural.data_typer import DataTyper

@dataclass
class TableCell:
    content: str
    row_span: int = 1
    col_span: int = 1
    data_type: str = "text"
    confidence: float = 1.0

@dataclass
class TableStructure:
    headers: List[List[TableCell]]
    rows: List[List[TableCell]]
    metadata: Dict[str, Any]
    column_types: List[str]
    has_headers: bool = True

class TableParser(BaseParser):
    """Advanced table structure parser with data type detection."""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.analyzer = TableAnalyzer(config)
        self.cell_merger = CellMerger()
        self.data_typer = DataTyper()
        self.min_confidence = config.get('min_confidence', 0.7)
    
    def can_parse(self, element: 'UnifiedElement') -> bool:
        """Check if element is a table."""
        return (element.type == "Table" or 
                element.category == "table" or
                self._has_table_indicators(element))
    
    async def parse(self, element: 'UnifiedElement') -> ParserResult:
        """Parse table with complete structure preservation."""
        try:
            # Extract raw table data
            raw_data = self._extract_table_data(element)
            
            # Analyze structure
            structure = await self.analyzer.analyze_structure(raw_data)
            
            # Handle cell merging and spans
            structure = self.cell_merger.process_spans(structure)
            
            # Detect data types per column
            structure.column_types = self.data_typer.detect_types(structure)
            
            # Validate structure integrity
            validation_errors = self.validate_structure(structure)
            
            # Calculate confidence
            confidence = self._calculate_confidence(structure, validation_errors)
            
            return ParserResult(
                success=True,
                data={
                    "structure": structure,
                    "headers": [cell.content for row in structure.headers for cell in row],
                    "rows": [[cell.content for cell in row] for row in structure.rows],
                    "column_types": structure.column_types,
                    "dimensions": {
                        "rows": len(structure.rows),
                        "columns": len(structure.column_types)
                    }
                },
                metadata=ParserMetadata(
                    confidence=confidence,
                    parser_version=self.version,
                    warnings=validation_errors if confidence > self.min_confidence else []
                ),
                validation_errors=validation_errors if confidence <= self.min_confidence else [],
                structured_data=self._export_formats(structure)
            )
            
        except Exception as e:
            return ParserResult(
                success=False,
                data={},
                metadata=ParserMetadata(
                    confidence=0.0,
                    parser_version=self.version,
                    error_count=1,
                    warnings=[str(e)]
                ),
                validation_errors=[f"Table parsing failed: {str(e)}"]
            )
    
    def validate(self, result: ParserResult) -> List[str]:
        """Validate table parsing result."""
        errors = []
        
        if not result.success:
            return ["Table parsing failed"]
        
        structure = result.data.get("structure")
        if not structure:
            errors.append("No table structure found")
            return errors
        
        # Validate dimensions
        if len(structure.rows) == 0:
            errors.append("Table has no data rows")
        
        # Validate column consistency
        if structure.rows:
            expected_cols = len(structure.column_types)
            for i, row in enumerate(structure.rows):
                if len(row) != expected_cols:
                    errors.append(f"Row {i} has {len(row)} columns, expected {expected_cols}")
        
        return errors
    
    def _export_formats(self, structure: TableStructure) -> Dict[str, Any]:
        """Export table in multiple formats."""
        return {
            "csv": self._to_csv(structure),
            "json": self._to_json(structure),
            "html": self._to_html(structure)
        }
```

### 2. List Parser (`list.py`)
```python
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
from .base import BaseParser, ParserResult, ParserMetadata
from .structural.list_detector import ListDetector

class ListType(Enum):
    UNORDERED = "unordered"
    ORDERED = "ordered"
    DEFINITION = "definition"
    MIXED = "mixed"

@dataclass
class ListItem:
    content: str
    level: int
    item_type: str
    number: Optional[str] = None
    children: List['ListItem'] = None
    metadata: Dict[str, Any] = None

@dataclass
class ListStructure:
    items: List[ListItem]
    list_type: ListType
    max_depth: int
    total_items: int
    has_mixed_content: bool = False

class ListParser(BaseParser):
    """Hierarchical list parser with nested structure detection."""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.detector = ListDetector(config)
        self.max_depth = config.get('max_depth', 5)
        self.min_confidence = config.get('min_confidence', 0.8)
    
    def can_parse(self, element: 'UnifiedElement') -> bool:
        """Check if element is a list."""
        return (element.type in ["ListItem", "List"] or
                element.category == "list" or
                self._has_list_indicators(element))
    
    async def parse(self, element: 'UnifiedElement') -> ParserResult:
        """Parse list with hierarchy preservation."""
        try:
            # Extract list items
            raw_items = self._extract_list_items(element)
            
            # Detect hierarchy and structure
            structure = await self.detector.detect_hierarchy(raw_items)
            
            # Validate depth limits
            if structure.max_depth > self.max_depth:
                structure = self._truncate_depth(structure)
            
            # Build nested structure
            nested_items = self._build_hierarchy(structure.items)
            structure.items = nested_items
            
            # Validate structure
            validation_errors = self.validate_structure(structure)
            confidence = self._calculate_confidence(structure, validation_errors)
            
            return ParserResult(
                success=True,
                data={
                    "structure": structure,
                    "items": self._flatten_items(structure.items),
                    "hierarchy": self._export_hierarchy(structure.items),
                    "statistics": {
                        "total_items": structure.total_items,
                        "max_depth": structure.max_depth,
                        "list_type": structure.list_type.value
                    }
                },
                metadata=ParserMetadata(
                    confidence=confidence,
                    parser_version=self.version,
                    warnings=validation_errors if confidence > self.min_confidence else []
                ),
                validation_errors=validation_errors if confidence <= self.min_confidence else [],
                structured_data=self._export_formats(structure)
            )
            
        except Exception as e:
            return ParserResult(
                success=False,
                data={},
                metadata=ParserMetadata(
                    confidence=0.0,
                    parser_version=self.version,
                    error_count=1,
                    warnings=[str(e)]
                ),
                validation_errors=[f"List parsing failed: {str(e)}"]
            )
    
    def validate(self, result: ParserResult) -> List[str]:
        """Validate list parsing result."""
        errors = []
        
        if not result.success:
            return ["List parsing failed"]
        
        structure = result.data.get("structure")
        if not structure:
            errors.append("No list structure found")
            return errors
        
        # Validate depth
        if structure.max_depth > self.max_depth:
            errors.append(f"List depth {structure.max_depth} exceeds maximum {self.max_depth}")
        
        # Validate item count
        if structure.total_items == 0:
            errors.append("List has no items")
        
        return errors
```

### 3. Table Structure Analyzer (`structural/table_analyzer.py`)
```python
class TableAnalyzer:
    """Advanced table structure analysis."""
    
    async def analyze_structure(self, raw_data: Any) -> TableStructure:
        """Analyze table structure with header detection."""
        
        # Detect headers using multiple strategies
        headers = self._detect_headers(raw_data)
        
        # Extract data rows
        rows = self._extract_data_rows(raw_data, headers)
        
        # Analyze column patterns
        column_patterns = self._analyze_columns(rows)
        
        return TableStructure(
            headers=headers,
            rows=rows,
            metadata={"patterns": column_patterns},
            column_types=[],  # Will be filled by DataTyper
            has_headers=len(headers) > 0
        )
    
    def _detect_headers(self, raw_data: Any) -> List[List[TableCell]]:
        """Multi-strategy header detection."""
        strategies = [
            self._detect_by_formatting,
            self._detect_by_position,
            self._detect_by_content_pattern,
            self._detect_by_data_type_difference
        ]
        
        for strategy in strategies:
            headers = strategy(raw_data)
            if headers:
                return headers
        
        return []
```

## 🧪 Testing Requirements

### Test Coverage Goals
- **>95% code coverage** for all table and list parsing functionality
- **Edge case testing** for malformed and complex structures
- **Performance benchmarks** for large tables and deep hierarchies

### Key Test Scenarios
1. **Table Structure Tests**
   - Simple tables with clear headers
   - Complex tables with merged cells
   - Tables with mixed data types
   - Malformed tables with missing cells

2. **List Hierarchy Tests**
   - Simple ordered/unordered lists
   - Deeply nested lists (5+ levels)
   - Mixed content lists
   - Definition lists and complex structures

## 🔗 Integration Points

### With Agent 1 (Base Framework)
```python
# Inherit from the base classes
from .base import BaseParser, ParserResult

class TableParser(BaseParser):
    # Your implementation
```

### With Agent 3 (Image/Formula)
- Share validation patterns for embedded content
- Coordinate on mixed content handling

### With Agent 4 (Integration)
- Provide performance metrics for optimization
- Support batch processing for multiple tables/lists

## 🚀 GitHub Workflow

1. **Wait for Agent 1** completion of base framework
2. **Create Branch**: `feature/table-list-parsers`
3. **Implement parsers** with comprehensive structure analysis
4. **Add test suite** with complex scenarios
5. **Performance optimization** for large datasets
6. **Create PR** with structure preservation examples

## ✅ Success Criteria

- [ ] Table parser preserves complete structure including spans
- [ ] Header detection with >90% accuracy
- [ ] Cell merging and spanning fully supported
- [ ] Data type detection for all columns
- [ ] List hierarchy extraction up to 5 levels deep
- [ ] Mixed content handling in lists
- [ ] Comprehensive validation rules
- [ ] Performance: <100ms for standard tables
- [ ] Export to multiple formats (CSV, JSON, HTML)
- [ ] >95% test coverage with edge cases

**Your structure parsers will handle the most complex document layouts!**