# AGENT 1 - CORE PARSER FRAMEWORK

## 🎯 Your Mission
You are Agent 1, the Foundation Builder for the Document Element Parser system. Your role is to create the core framework that all specialized parsers will inherit from.

## 📋 Your Assignment
Implement the foundational parser framework with abstract base classes, factory pattern, and configuration system that enables all other agents to build specialized parsers.

**Sub-Issue**: #96 - Core Parser Framework & Base Classes  
**Dependencies**: None (you are the foundation)  
**Timeline**: Days 1-2

## 🏗️ Files You Will Create

```
src/torematrix/core/processing/parsers/
├── __init__.py                 # Package initialization and exports
├── base.py                    # Abstract BaseParser class
├── factory.py                 # ParserFactory with registration
├── types.py                   # Parser types and enums
├── exceptions.py              # Parser-specific exceptions
└── config.py                  # Parser configuration system

tests/unit/core/processing/parsers/
├── __init__.py
├── test_base_parser.py        # BaseParser functionality tests
├── test_factory.py            # Factory registration tests
├── test_parser_types.py       # Type system tests
├── test_exceptions.py         # Exception handling tests
└── test_config.py             # Configuration system tests
```

## 💻 Technical Implementation

### 1. Abstract Parser Base Class (`base.py`)
```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Type
from datetime import datetime
from pydantic import BaseModel, Field
import time
import asyncio

class ParserMetadata(BaseModel):
    """Enhanced metadata for parser results."""
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score 0-1")
    processing_time: float = Field(ge=0.0, description="Processing time in seconds")
    parser_version: str = Field(description="Parser version used")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    error_count: int = Field(ge=0, default=0)
    warnings: List[str] = Field(default_factory=list)

class ParserResult(BaseModel):
    """Standardized parser result format."""
    success: bool
    data: Dict[str, Any]
    metadata: ParserMetadata
    validation_errors: List[str] = Field(default_factory=list)
    extracted_content: Optional[str] = None
    structured_data: Optional[Dict[str, Any]] = None

class BaseParser(ABC):
    """Abstract base class for all element parsers."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.name = self.__class__.__name__
        self.version = "1.0.0"
        self._performance_stats = {}
    
    @abstractmethod
    async def parse(self, element: 'UnifiedElement') -> ParserResult:
        """Parse an element and return structured result."""
        pass
    
    @abstractmethod
    def can_parse(self, element: 'UnifiedElement') -> bool:
        """Check if this parser can handle the given element."""
        pass
    
    @abstractmethod
    def validate(self, result: ParserResult) -> List[str]:
        """Validate the parsing result and return error list."""
        pass
    
    def get_supported_types(self) -> List[str]:
        """Return list of supported element types."""
        return []
    
    async def parse_with_monitoring(self, element: 'UnifiedElement') -> ParserResult:
        """Parse with performance monitoring."""
        start_time = time.time()
        try:
            result = await self.parse(element)
            processing_time = time.time() - start_time
            result.metadata.processing_time = processing_time
            return result
        except Exception as e:
            processing_time = time.time() - start_time
            return ParserResult(
                success=False,
                data={},
                metadata=ParserMetadata(
                    confidence=0.0,
                    processing_time=processing_time,
                    parser_version=self.version,
                    error_count=1,
                    warnings=[str(e)]
                ),
                validation_errors=[f"Parser error: {str(e)}"]
            )
```

### 2. Parser Factory (`factory.py`)
```python
from typing import Dict, Type, List, Optional
import importlib
import inspect
from pathlib import Path

class ParserFactory:
    """Factory for creating and managing parsers."""
    
    _parsers: Dict[str, Type[BaseParser]] = {}
    _initialized = False
    
    @classmethod
    def register_parser(cls, parser_type: str, parser_class: Type[BaseParser]):
        """Register a parser for a specific element type."""
        if not issubclass(parser_class, BaseParser):
            raise ValueError(f"Parser must inherit from BaseParser")
        cls._parsers[parser_type] = parser_class
    
    @classmethod
    def unregister_parser(cls, parser_type: str):
        """Unregister a parser."""
        cls._parsers.pop(parser_type, None)
    
    @classmethod
    def get_parser(cls, element: 'UnifiedElement') -> Optional[BaseParser]:
        """Get the best parser for an element."""
        if not cls._initialized:
            cls._discover_parsers()
        
        # Try registered parsers
        for parser_type, parser_class in cls._parsers.items():
            parser_instance = parser_class()
            if parser_instance.can_parse(element):
                return parser_instance
        
        return None
    
    @classmethod
    def get_available_parsers(cls) -> List[str]:
        """Get list of available parser types."""
        if not cls._initialized:
            cls._discover_parsers()
        return list(cls._parsers.keys())
    
    @classmethod
    def _discover_parsers(cls):
        """Auto-discover parsers in the parsers module."""
        try:
            parsers_path = Path(__file__).parent
            for parser_file in parsers_path.glob("*.py"):
                if parser_file.name.startswith("_") or parser_file.name == "base.py":
                    continue
                
                module_name = f"torematrix.core.processing.parsers.{parser_file.stem}"
                try:
                    module = importlib.import_module(module_name)
                    for name, obj in inspect.getmembers(module):
                        if (inspect.isclass(obj) and 
                            issubclass(obj, BaseParser) and 
                            obj is not BaseParser):
                            # Auto-register based on class name
                            parser_type = name.lower().replace("parser", "")
                            cls.register_parser(parser_type, obj)
                except ImportError:
                    continue
        except Exception:
            pass  # Fail silently for auto-discovery
        
        cls._initialized = True
```

### 3. Parser Types (`types.py`)
```python
from enum import Enum
from typing import Dict, Any, List
from pydantic import BaseModel

class ElementType(Enum):
    """Supported element types for parsing."""
    TABLE = "table"
    IMAGE = "image"
    FORMULA = "formula"
    LIST = "list"
    CODE = "code"
    TEXT = "text"
    HEADER = "header"
    PARAGRAPH = "paragraph"
    UNKNOWN = "unknown"

class ParserPriority(Enum):
    """Parser priority levels."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class ParserConfig(BaseModel):
    """Configuration model for parsers."""
    enabled: bool = True
    priority: ParserPriority = ParserPriority.MEDIUM
    timeout_seconds: float = 30.0
    max_retries: int = 3
    cache_results: bool = True
    custom_settings: Dict[str, Any] = {}

class ParserCapabilities(BaseModel):
    """Parser capability description."""
    supported_types: List[ElementType]
    confidence_threshold: float = 0.5
    requires_network: bool = False
    supports_batch: bool = False
    max_element_size: Optional[int] = None
```

## 🧪 Testing Requirements

### Test Coverage Goals
- **>95% code coverage** across all base framework components
- **Unit tests** for all abstract methods and factory functionality
- **Integration tests** for parser registration and discovery
- **Performance tests** for parser instantiation and basic operations

### Key Test Scenarios
1. **BaseParser Abstract Functionality**
   - Abstract method enforcement
   - Configuration handling
   - Performance monitoring
   - Error handling and recovery

2. **Factory Pattern Testing**
   - Parser registration and unregistration
   - Auto-discovery mechanism
   - Best parser selection logic
   - Error handling for invalid parsers

3. **Type System Validation**
   - Element type enumeration
   - Configuration model validation
   - Parser capability descriptions

## 🔗 Integration Points

### For Agent 2 (Table/List Parsers)
```python
# Your base classes will be inherited like this:
class TableParser(BaseParser):
    def can_parse(self, element: UnifiedElement) -> bool:
        return element.type == ElementType.TABLE
```

### For Agent 3 (Image/Formula Parsers)
```python
# Factory registration will work like this:
ParserFactory.register_parser("image", ImageParser)
ParserFactory.register_parser("formula", FormulaParser)
```

### For Agent 4 (Integration)
```python
# Manager will use your factory like this:
parser = ParserFactory.get_parser(element)
result = await parser.parse_with_monitoring(element)
```

## 🚀 GitHub Workflow

1. **Create Branch**: `feature/parser-framework-base`
2. **Implement Core Framework** with all abstract classes
3. **Add Comprehensive Tests** with >95% coverage
4. **Document APIs** with examples
5. **Create PR** with detailed implementation report

## ✅ Success Criteria

- [ ] BaseParser abstract class with all required methods
- [ ] ParserFactory with registration and auto-discovery
- [ ] Complete type system for all parser configurations
- [ ] Custom exceptions for all error scenarios
- [ ] Configuration system supporting all parser types
- [ ] Full async/await support throughout
- [ ] Complete type hints using Pydantic models
- [ ] >95% test coverage with comprehensive scenarios
- [ ] Performance monitoring framework integrated
- [ ] API documentation with usage examples

## 📚 Documentation Required

Create comprehensive documentation showing:
- How to inherit from BaseParser
- Factory registration examples
- Configuration system usage
- Performance monitoring setup
- Error handling patterns

**Your foundation will enable all other agents to build specialized parsers efficiently!**