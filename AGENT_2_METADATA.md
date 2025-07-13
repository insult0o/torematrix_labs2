# AGENT 2 - Metadata Extraction Engine: Relationship Detection & Graph Construction

## 🎯 Your Assignment
You are **Agent 2** responsible for building advanced relationship detection system with graph-based storage and semantic analysis capabilities for the TORE Matrix Labs V3 metadata extraction engine.

## 📋 Specific Tasks

### 1. Relationship Graph Data Structures
- Design graph-based relationship model
- Implement graph operations (add, remove, query)
- Create relationship types and hierarchy
- Add graph traversal algorithms
- Support relationship constraints and validation

### 2. Element Relationship Detection
- Build algorithms for spatial relationship detection
- Implement content-based relationship analysis
- Create parent-child relationship detection
- Add sibling relationship identification
- Support custom relationship detection rules

### 3. Reading Order Determination
- Implement reading order algorithms (left-to-right, top-to-bottom)
- Add column detection and ordering
- Create table reading order logic
- Support multi-language reading patterns
- Add reading order validation and correction

### 4. Semantic Role Classification
- Build ML-based semantic role classifier
- Implement rule-based semantic analysis
- Create role hierarchy and inheritance
- Add context-aware role assignment
- Support custom semantic roles

## 🏗️ Files to Create

```
src/torematrix/core/processing/metadata/
├── relationships.py               # Core relationship detection engine
├── graph.py                      # Graph structure and operations
├── extractors/
│   ├── relationships.py          # RelationshipExtractor
│   ├── reading_order.py          # ReadingOrderExtractor
│   └── semantic.py               # SemanticRoleExtractor
├── storage/
│   ├── __init__.py               # Storage package
│   ├── graph_storage.py          # Graph persistence layer
│   └── validators.py             # Relationship validation
├── algorithms/
│   ├── __init__.py               # Algorithms package
│   ├── spatial.py                # Spatial relationship algorithms
│   ├── content.py                # Content-based algorithms
│   └── ml_models.py              # ML model implementations
└── models/                       # Relationship models
    ├── __init__.py
    ├── relationship.py           # Relationship data models
    └── graph_nodes.py            # Graph node definitions

tests/unit/core/processing/metadata/
├── test_relationships.py         # Core relationship tests (30+ tests)
├── test_graph.py                 # Graph structure tests (25+ tests)
├── extractors/
│   ├── test_relationships.py     # Relationship extractor tests (25+ tests)
│   ├── test_reading_order.py     # Reading order tests (30+ tests)
│   └── test_semantic.py          # Semantic classification tests (20+ tests)
├── storage/
│   ├── test_graph_storage.py     # Storage tests (20+ tests)
│   └── test_validators.py        # Validation tests (15+ tests)
└── algorithms/
    ├── test_spatial.py           # Spatial algorithm tests (25+ tests)
    ├── test_content.py           # Content algorithm tests (20+ tests)
    └── test_ml_models.py         # ML model tests (15+ tests)
```

## 🔧 Technical Implementation Details

### Relationship Detection Engine
```python
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
import networkx as nx
from enum import Enum

class RelationshipType(str, Enum):
    PARENT_CHILD = "parent_child"
    SIBLING = "sibling"
    SPATIAL_ADJACENT = "spatial_adjacent"
    CONTENT_RELATED = "content_related"
    READING_ORDER = "reading_order"
    SEMANTIC_GROUP = "semantic_group"

class RelationshipDetectionEngine:
    """Core engine for detecting element relationships."""
    
    def __init__(self, config: RelationshipConfig):
        self.config = config
        self.graph = ElementRelationshipGraph()
        self.spatial_analyzer = SpatialAnalyzer()
        self.content_analyzer = ContentAnalyzer()
        
    async def detect_relationships(
        self, 
        elements: List[UnifiedElement],
        context: DocumentContext
    ) -> RelationshipGraph:
        """Detect all relationships between elements."""
        
    async def detect_spatial_relationships(
        self, 
        elements: List[UnifiedElement]
    ) -> List[Relationship]:
        """Detect spatial relationships (containment, adjacency)."""
        
    async def detect_content_relationships(
        self, 
        elements: List[UnifiedElement]
    ) -> List[Relationship]:
        """Detect content-based relationships."""
```

### Graph Structure Implementation
```python
import networkx as nx
from typing import Dict, List, Optional, Any, Iterator

class ElementRelationshipGraph:
    """Graph structure for element relationships."""
    
    def __init__(self):
        self.graph = nx.MultiDiGraph()
        self.element_index: Dict[str, UnifiedElement] = {}
        
    def add_element(self, element: UnifiedElement):
        """Add element as graph node."""
        
    def add_relationship(
        self, 
        source_id: str, 
        target_id: str,
        relationship: Relationship
    ):
        """Add relationship as graph edge."""
        
    def get_relationships(
        self, 
        element_id: str,
        relationship_type: Optional[RelationshipType] = None
    ) -> List[Relationship]:
        """Get all relationships for an element."""
        
    def find_path(
        self, 
        source_id: str, 
        target_id: str,
        max_length: int = 5
    ) -> Optional[List[str]]:
        """Find path between elements."""
        
    def get_connected_components(self) -> List[Set[str]]:
        """Get connected component groups."""
```

### Reading Order Detection
```python
from typing import List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

class ReadingDirection(str, Enum):
    LEFT_TO_RIGHT = "ltr"
    RIGHT_TO_LEFT = "rtl"
    TOP_TO_BOTTOM = "ttb"
    BOTTOM_TO_TOP = "btt"

class ReadingOrderExtractor:
    """Extract reading order from document layout."""
    
    def __init__(self, config: ReadingOrderConfig):
        self.config = config
        self.column_detector = ColumnDetector()
        
    async def extract_reading_order(
        self, 
        elements: List[UnifiedElement],
        page_layout: PageLayout
    ) -> ReadingOrder:
        """Extract complete reading order for page."""
        
    def detect_columns(
        self, 
        elements: List[UnifiedElement]
    ) -> List[Column]:
        """Detect column structure in layout."""
        
    def order_within_column(
        self, 
        elements: List[UnifiedElement],
        direction: ReadingDirection
    ) -> List[str]:
        """Order elements within a column."""
        
    def validate_reading_order(
        self, 
        order: ReadingOrder,
        elements: List[UnifiedElement]
    ) -> ValidationResult:
        """Validate reading order makes sense."""
```

### Semantic Role Classification
```python
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import torch
from transformers import AutoTokenizer, AutoModel

class SemanticRole(str, Enum):
    TITLE = "title"
    HEADING = "heading"
    BODY_TEXT = "body_text"
    CAPTION = "caption"
    FOOTER = "footer"
    HEADER = "header"
    SIDEBAR = "sidebar"
    METADATA = "metadata"

class SemanticRoleExtractor:
    """ML-based semantic role classification."""
    
    def __init__(self, config: SemanticConfig):
        self.config = config
        self.model = self._load_model()
        self.rule_engine = RuleBasedClassifier()
        
    async def extract_semantic_roles(
        self, 
        elements: List[UnifiedElement],
        context: DocumentContext
    ) -> Dict[str, SemanticRole]:
        """Extract semantic roles for all elements."""
        
    def _classify_with_ml(
        self, 
        element: UnifiedElement,
        context: DocumentContext
    ) -> Tuple[SemanticRole, float]:
        """ML-based classification."""
        
    def _classify_with_rules(
        self, 
        element: UnifiedElement,
        context: DocumentContext
    ) -> Optional[SemanticRole]:
        """Rule-based classification."""
```

### Graph Storage Layer
```python
from typing import Dict, List, Optional, Any
import sqlite3
import json
from pathlib import Path

class GraphStorage:
    """Persistent storage for relationship graphs."""
    
    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        self.db_path = storage_path / "relationships.db"
        self._init_database()
        
    async def save_graph(
        self, 
        document_id: str,
        graph: ElementRelationshipGraph
    ):
        """Save relationship graph to storage."""
        
    async def load_graph(
        self, 
        document_id: str
    ) -> Optional[ElementRelationshipGraph]:
        """Load relationship graph from storage."""
        
    async def update_relationships(
        self, 
        document_id: str,
        relationships: List[Relationship]
    ):
        """Update specific relationships."""
        
    def query_relationships(
        self, 
        query: RelationshipQuery
    ) -> List[Relationship]:
        """Query relationships with filters."""
```

## 🧪 Testing Requirements

### Test Coverage Targets
- **Relationship detection**: 30+ tests covering all relationship types
- **Graph operations**: 25+ tests for graph structure and queries
- **Reading order**: 30+ tests for various layout patterns
- **Semantic classification**: 20+ tests for ML and rule-based methods
- **Storage layer**: 20+ tests for persistence operations

### Key Test Scenarios
```python
# Test examples to implement
async def test_spatial_relationship_detection():
    """Test detection of spatial relationships."""
    
async def test_reading_order_extraction():
    """Test reading order for multi-column layouts."""
    
async def test_semantic_role_classification():
    """Test semantic role assignment accuracy."""
    
async def test_graph_persistence():
    """Test saving and loading relationship graphs."""
    
def test_relationship_validation():
    """Test relationship constraint validation."""
```

## 🔗 Integration Points

### With Agent 1 (Core Engine)
- Use metadata schema from Agent 1
- Integrate with confidence scoring system
- Extend base extractor interface
- Share extraction context and configuration

### With Agent 3 (Performance)
- Provide graph for caching optimization
- Support parallel relationship detection
- Enable incremental graph updates
- Optimize memory usage for large graphs

### With Agent 4 (Integration)
- Define relationship API endpoints
- Integrate with monitoring system
- Support relationship queries
- Enable relationship visualization

### With Existing Systems
- **Storage System**: Persist relationship graphs
- **Element Models**: Use UnifiedElement structure
- **Event Bus**: Emit relationship detection events
- **Processing Pipeline**: Integrate with document flow

## 📊 Success Criteria

### Functional Requirements ✅
1. ✅ RelationshipDetectionEngine with graph construction
2. ✅ Reading order algorithm implementation
3. ✅ Semantic role classification system (ML + rules)
4. ✅ Graph-based relationship storage
5. ✅ Relationship validation framework
6. ✅ Query interface for relationships

### Technical Requirements ✅
1. ✅ >95% test coverage across all components
2. ✅ Relationship detection accuracy >90%
3. ✅ Graph construction performance optimized
4. ✅ Full type annotations and documentation
5. ✅ Async/await throughout for performance
6. ✅ Comprehensive error handling

### Integration Requirements ✅
1. ✅ Clean integration with Agent 1 metadata engine
2. ✅ Performance optimization hooks for Agent 3
3. ✅ API interfaces ready for Agent 4
4. ✅ Storage system compatibility
5. ✅ Event bus integration for notifications

## 📈 Performance Targets
- **Relationship Detection**: <500ms for 1000 elements
- **Graph Construction**: <200ms for typical documents
- **Reading Order**: <100ms per page
- **Semantic Classification**: <50ms per element
- **Memory Usage**: <100MB for large documents

## 🚀 GitHub Workflow

### Branch Strategy
```bash
# Create feature branch (after Agent 1 completion)
git checkout -b feature/metadata-relationships

# Regular commits with clear messages
git commit -m "feat(metadata): implement relationship detection system

- Add RelationshipDetectionEngine with graph construction
- Implement reading order determination algorithms
- Add semantic role classification (ML + rules)
- Create graph storage and persistence layer

Depends on: #98 (Agent 1 - Core Engine)

🤖 Generated with [Claude Code](https://claude.ai/code)
Co-Authored-By: Claude <noreply@anthropic.com>"
```

### Pull Request
- Title: `🚀 FEATURE: Relationship Detection & Graph System (#100)`
- Link to sub-issue #100
- Include accuracy benchmarks
- Document relationship types and algorithms

## 💬 Communication Protocol

### Daily Updates
Comment on issue #100 with:
- Progress summary (% complete)
- Completed relationship detection features
- Current focus area (spatial, semantic, etc.)
- Integration status with Agent 1
- Any blockers or questions

### Coordination with Other Agents
- **Wait for Agent 1**: Need core metadata schema before starting
- **Notify Agent 3**: Share graph structure for optimization
- **Prepare for Agent 4**: Document integration interfaces

## 🔥 Ready to Start!

You have **comprehensive specifications** for building the relationship detection system. Your focus is on:

1. **Graph Foundation** - Robust graph structure and operations
2. **Smart Detection** - Accurate relationship algorithms
3. **Performance** - Optimized for large documents
4. **Integration** - Clean interfaces with other agents

**Wait for Agent 1 completion, then build the relationship detection engine!** 🚀