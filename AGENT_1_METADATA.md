# AGENT 1 - Metadata Extraction Engine: Core Framework

## 🎯 Your Assignment
You are **Agent 1** responsible for building the foundational metadata extraction engine with schema definition and core extraction algorithms for the TORE Matrix Labs V3 project.

## 📋 Specific Tasks

### 1. Core Metadata Schema Design
- Create unified metadata schema supporting all 15+ element types
- Design extensible schema with validation rules
- Implement metadata inheritance hierarchy
- Add confidence scoring framework
- Support custom metadata fields

### 2. Core Extraction Engine
- Build `MetadataExtractionEngine` with async processing
- Implement pluggable extractor architecture
- Add document-level metadata extraction
- Create page-level property extraction
- Support incremental extraction capabilities

### 3. Base Extractor Framework
- Design `BaseExtractor` interface for all extractors
- Implement extractor registration system
- Add validation and error handling
- Create extractor lifecycle management
- Support configurable extraction strategies

### 4. Language & Encoding Detection
- Implement automatic language detection
- Add encoding detection and normalization
- Support multilingual documents
- Create language-specific extraction rules
- Add confidence scoring for detection

## 🏗️ Files to Create

```
src/torematrix/core/processing/metadata/
├── __init__.py                    # Package initialization and exports
├── engine.py                      # MetadataExtractionEngine (main class)
├── schema.py                      # Metadata schema definitions
├── confidence.py                  # Confidence scoring system
├── extractors/                    # Extractor implementations
│   ├── __init__.py               # Extractor package
│   ├── base.py                   # BaseExtractor interface
│   ├── document.py               # DocumentMetadataExtractor
│   └── page.py                   # PageMetadataExtractor
└── types.py                      # Type definitions and enums

tests/unit/core/processing/metadata/
├── test_engine.py                # Engine tests (25+ tests)
├── test_schema.py                # Schema validation tests (20+ tests)
├── test_confidence.py            # Confidence scoring tests (15+ tests)
├── extractors/
│   ├── test_base.py              # Base extractor tests (20+ tests)
│   ├── test_document.py          # Document extractor tests (25+ tests)
│   └── test_page.py              # Page extractor tests (20+ tests)
└── test_types.py                 # Type definition tests (10+ tests)
```

## 🔧 Technical Implementation Details

### MetadataExtractionEngine Class
```python
from typing import Dict, List, Optional, Any, Type
from pydantic import BaseModel
import asyncio
from pathlib import Path

class MetadataExtractionEngine:
    """Core metadata extraction engine with pluggable extractors."""
    
    def __init__(self, config: MetadataConfig):
        self.config = config
        self.extractors: Dict[str, BaseExtractor] = {}
        self.confidence_scorer = ConfidenceScorer()
        
    async def extract_metadata(
        self, 
        document: ProcessedDocument,
        extraction_types: Optional[List[str]] = None
    ) -> DocumentMetadata:
        """Extract comprehensive metadata from document."""
        
    def register_extractor(self, name: str, extractor: BaseExtractor):
        """Register a metadata extractor."""
        
    async def extract_incremental(
        self, 
        document: ProcessedDocument,
        previous_metadata: DocumentMetadata
    ) -> DocumentMetadata:
        """Perform incremental metadata extraction."""
```

### Metadata Schema Design
```python
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, validator
from datetime import datetime
from enum import Enum

class MetadataType(str, Enum):
    DOCUMENT = "document"
    PAGE = "page" 
    ELEMENT = "element"
    RELATIONSHIP = "relationship"

class BaseMetadata(BaseModel):
    """Base metadata model with common fields."""
    metadata_type: MetadataType
    extraction_timestamp: datetime
    confidence_score: float
    source_extractor: str
    custom_fields: Dict[str, Any] = {}
    
class DocumentMetadata(BaseMetadata):
    """Document-level metadata."""
    title: Optional[str]
    author: Optional[str]
    creation_date: Optional[datetime]
    language: Optional[str]
    encoding: str
    page_count: int
    total_elements: int
    file_properties: Dict[str, Any]
```

### Base Extractor Interface
```python
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

class BaseExtractor(ABC):
    """Base interface for all metadata extractors."""
    
    def __init__(self, config: ExtractorConfig):
        self.config = config
        self.name = self.__class__.__name__
        
    @abstractmethod
    async def extract(
        self, 
        document: ProcessedDocument,
        context: ExtractionContext
    ) -> Dict[str, Any]:
        """Extract metadata from document."""
        
    @abstractmethod
    def validate_metadata(self, metadata: Dict[str, Any]) -> bool:
        """Validate extracted metadata."""
        
    def get_confidence_factors(self) -> List[str]:
        """Return factors used for confidence scoring."""
        return ["extraction_method", "data_quality", "validation_result"]
```

### Confidence Scoring System
```python
from typing import Dict, List, Any
import statistics

class ConfidenceScorer:
    """Advanced confidence scoring for metadata extraction."""
    
    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or self._default_weights()
        
    def calculate_confidence(
        self, 
        metadata: Dict[str, Any],
        extraction_context: ExtractionContext
    ) -> float:
        """Calculate confidence score for extracted metadata."""
        
    def _default_weights(self) -> Dict[str, float]:
        return {
            "extraction_method": 0.3,
            "data_quality": 0.4, 
            "validation_result": 0.2,
            "source_reliability": 0.1
        }
```

## 🧪 Testing Requirements

### Test Coverage Targets
- **Engine tests**: 25+ tests covering all extraction scenarios
- **Schema tests**: 20+ tests for validation and inheritance
- **Extractor tests**: 20+ tests per extractor type
- **Confidence tests**: 15+ tests for scoring algorithms
- **Integration tests**: 10+ tests with mock documents

### Key Test Scenarios
```python
# Test examples to implement
async def test_metadata_extraction_engine_basic():
    """Test basic metadata extraction functionality."""
    
async def test_incremental_extraction():
    """Test incremental metadata updates."""
    
def test_schema_validation():
    """Test metadata schema validation rules."""
    
async def test_confidence_scoring():
    """Test confidence score calculation."""
    
def test_extractor_registration():
    """Test extractor plugin system."""
```

## 🔗 Integration Points

### With Other Agents
- **Agent 2**: Provide metadata schema for relationship storage
- **Agent 3**: Expose extraction engine for optimization
- **Agent 4**: Define integration interfaces for pipeline

### With Existing Systems
- **Element Models**: Use existing UnifiedElement structure
- **Processing Pipeline**: Integrate with document processing flow
- **Storage System**: Connect to metadata persistence layer
- **Event Bus**: Emit metadata extraction events

## 📊 Success Criteria

### Functional Requirements ✅
1. ✅ MetadataExtractionEngine with async processing
2. ✅ Comprehensive metadata schema with validation  
3. ✅ Document and page-level extractors implemented
4. ✅ Confidence scoring for all metadata
5. ✅ Language/encoding detection working
6. ✅ Extensible extractor plugin system

### Technical Requirements ✅
1. ✅ >95% test coverage across all components
2. ✅ Full type annotations with mypy validation
3. ✅ Async/await throughout for performance
4. ✅ Comprehensive error handling
5. ✅ API documentation with examples
6. ✅ Performance benchmarks documented

### Integration Requirements ✅
1. ✅ Clean interfaces for other agents
2. ✅ Integration with existing element models
3. ✅ Event bus integration for notifications
4. ✅ Storage system compatibility
5. ✅ Pipeline integration points defined

## 📈 Performance Targets
- **Extraction Speed**: <100ms per document for basic metadata
- **Memory Usage**: <50MB for 1000-page documents
- **Concurrency**: Support 10+ parallel extractions
- **Accuracy**: >95% for standard document properties

## 🚀 GitHub Workflow

### Branch Strategy
```bash
# Create feature branch
git checkout -b feature/metadata-extraction-core

# Regular commits with clear messages
git commit -m "feat(metadata): implement core extraction engine

- Add MetadataExtractionEngine with async processing
- Implement comprehensive metadata schema
- Add confidence scoring framework
- Create base extractor interface

🤖 Generated with [Claude Code](https://claude.ai/code)
Co-Authored-By: Claude <noreply@anthropic.com>"
```

### Pull Request
- Title: `🚀 FEATURE: Core Metadata Extraction Engine (#98)`
- Link to sub-issue #98
- Include performance benchmarks
- Document all APIs with examples

## 💬 Communication Protocol

### Daily Updates
Comment on issue #98 with:
- Progress summary (% complete)
- Completed components
- Current focus area
- Any blockers or questions
- Updated timeline if needed

### Completion Criteria
Before marking as complete, ensure:
1. All tests passing (>95% coverage)
2. Type checking passes (mypy)
3. Performance benchmarks documented
4. API documentation complete
5. Integration interfaces defined
6. Code review ready

## 🔥 Ready to Start!

You have **comprehensive specifications** for building the core metadata extraction engine. Your focus is on:

1. **Solid Foundation** - Clean, extensible architecture
2. **Performance** - Async processing throughout  
3. **Quality** - Comprehensive testing and validation
4. **Integration** - Clear interfaces for other agents

**Start with the MetadataExtractionEngine class and build systematically!**

This is foundational work that other agents depend on - make it robust! 🚀