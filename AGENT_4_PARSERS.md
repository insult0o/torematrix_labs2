# AGENT 4 - CODE PARSER & INTEGRATION SYSTEM

## 🎯 Your Mission
You are Agent 4, the Integration Specialist for the Document Element Parser system. Your role is to implement the code snippet parser and create the complete integration system with monitoring, caching, and production-ready features.

## 📋 Your Assignment
Implement the code snippet parser with language detection and build the comprehensive integration system that unifies all parser implementations into a production-ready service.

**Sub-Issue**: #101 - Code Parser & Integration System  
**Dependencies**: All Agents (1, 2, 3)  
**Timeline**: Days 4-6 (final integration phase)

## 🏗️ Files You Will Create

```
src/torematrix/core/processing/parsers/
├── code.py                    # Code snippet parser
├── registry.py                # Enhanced parser registry
└── integration/
    ├── __init__.py
    ├── manager.py             # Central parser manager
    ├── cache.py               # Intelligent result caching
    ├── monitor.py             # Performance monitoring
    ├── pipeline.py            # Main pipeline integration
    ├── batch_processor.py     # Batch processing optimization
    └── fallback_handler.py    # Error recovery strategies

tests/unit/core/processing/parsers/
├── test_code_parser.py        # Code parsing functionality
├── test_registry.py           # Registry system tests
└── integration/
    ├── test_manager.py
    ├── test_cache.py
    ├── test_monitor.py
    ├── test_pipeline.py
    ├── test_batch_processor.py
    └── test_fallback_handler.py

tests/integration/parsers/
├── test_end_to_end.py         # Complete system tests
├── test_performance.py        # Performance benchmarks
├── test_production_scenarios.py # Real-world scenarios
└── test_multi_parser_coordination.py

docs/parsers/
├── README.md                  # Complete system documentation
├── performance_benchmarks.md  # Performance analysis
├── api_reference.md           # API documentation
└── integration_guide.md       # Integration examples
```

## 💻 Technical Implementation

### 1. Code Parser (`code.py`)
```python
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
from enum import Enum
import re
import ast
from .base import BaseParser, ParserResult, ParserMetadata
from .integration.language_detector import LanguageDetector
from .integration.syntax_analyzer import SyntaxAnalyzer

class CodeLanguage(Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    JAVA = "java"
    CSHARP = "csharp"
    CPP = "cpp"
    C = "c"
    GO = "go"
    RUST = "rust"
    TYPESCRIPT = "typescript"
    PHP = "php"
    RUBY = "ruby"
    SWIFT = "swift"
    KOTLIN = "kotlin"
    SCALA = "scala"
    HTML = "html"
    CSS = "css"
    SQL = "sql"
    SHELL = "shell"
    DOCKERFILE = "dockerfile"
    YAML = "yaml"
    JSON = "json"
    UNKNOWN = "unknown"

@dataclass
class CodeElement:
    element_type: str  # function, class, variable, import, comment
    name: str
    line_start: int
    line_end: int
    content: str
    metadata: Dict[str, Any] = None

@dataclass
class CodeStructure:
    language: CodeLanguage
    elements: List[CodeElement]
    imports: List[str]
    functions: List[str]
    classes: List[str]
    variables: List[str]
    comments: List[str]
    complexity_score: float
    line_count: int

class CodeParser(BaseParser):
    """Advanced code snippet parser with language detection."""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.language_detector = LanguageDetector()
        self.syntax_analyzer = SyntaxAnalyzer()
        self.max_lines = config.get('max_lines', 10000)
        self.min_confidence = config.get('min_confidence', 0.8)
    
    def can_parse(self, element: 'UnifiedElement') -> bool:
        """Check if element contains code."""
        return (element.type in ["CodeBlock", "Code"] or
                element.category == "code" or
                self._has_code_indicators(element))
    
    async def parse(self, element: 'UnifiedElement') -> ParserResult:
        """Parse code with language detection and structure analysis."""
        try:
            # Extract code content
            code_content = self._extract_code_content(element)
            
            # Detect programming language
            language = await self.language_detector.detect(code_content)
            
            # Analyze code structure
            structure = await self.syntax_analyzer.analyze(code_content, language)
            
            # Extract code elements
            elements = self._extract_elements(code_content, language)
            structure.elements = elements
            
            # Apply syntax highlighting
            highlighted_code = self._apply_syntax_highlighting(code_content, language)
            
            # Validate syntax if possible
            syntax_valid, syntax_errors = self._validate_syntax(code_content, language)
            
            # Calculate confidence
            confidence = self._calculate_confidence(language, structure, syntax_valid)
            
            return ParserResult(
                success=True,
                data={
                    "language": language.value,
                    "structure": structure,
                    "highlighted_code": highlighted_code,
                    "syntax_valid": syntax_valid,
                    "elements": {
                        "functions": structure.functions,
                        "classes": structure.classes,
                        "imports": structure.imports,
                        "variables": structure.variables
                    },
                    "metrics": {
                        "line_count": structure.line_count,
                        "complexity": structure.complexity_score,
                        "element_count": len(structure.elements)
                    }
                },
                metadata=ParserMetadata(
                    confidence=confidence,
                    parser_version=self.version,
                    warnings=syntax_errors if syntax_valid else []
                ),
                validation_errors=syntax_errors if not syntax_valid else [],
                extracted_content=code_content,
                structured_data=self._export_formats(code_content, structure)
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
                validation_errors=[f"Code parsing failed: {str(e)}"]
            )
    
    def validate(self, result: ParserResult) -> List[str]:
        """Validate code parsing result."""
        errors = []
        
        if not result.success:
            return ["Code parsing failed"]
        
        # Validate language detection
        language = result.data.get("language")
        if language == "unknown":
            errors.append("Could not detect programming language")
        
        # Validate structure
        structure = result.data.get("structure")
        if not structure:
            errors.append("No code structure detected")
        
        return errors
    
    def get_supported_types(self) -> List[str]:
        """Return supported code languages."""
        return [lang.value for lang in CodeLanguage if lang != CodeLanguage.UNKNOWN]
```

### 2. Parser Manager (`integration/manager.py`)
```python
from typing import Dict, Any, List, Optional, Callable
import asyncio
import time
from dataclasses import dataclass
from ..factory import ParserFactory
from .cache import ParserCache
from .monitor import ParserMonitor
from .fallback_handler import FallbackHandler

@dataclass
class ParseRequest:
    element: 'UnifiedElement'
    priority: int = 0
    timeout: float = 30.0
    use_cache: bool = True
    callback: Optional[Callable] = None

@dataclass
class ParseResult:
    success: bool
    result: Optional['ParserResult']
    error: Optional[str]
    processing_time: float
    cache_hit: bool = False

class ParserManager:
    """Central manager for all parser operations."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.factory = ParserFactory()
        self.cache = ParserCache(config.get('cache', {}))
        self.monitor = ParserMonitor()
        self.fallback = FallbackHandler()
        
        # Performance settings
        self.max_concurrent = config.get('max_concurrent', 10)
        self.default_timeout = config.get('default_timeout', 30.0)
        self.enable_caching = config.get('enable_caching', True)
        
        # Statistics
        self._stats = {
            'total_requests': 0,
            'successful_parses': 0,
            'cache_hits': 0,
            'errors': 0,
            'total_time': 0.0
        }
    
    async def parse_element(self, element: 'UnifiedElement', **kwargs) -> ParseResult:
        """Parse a single element with full monitoring."""
        request = ParseRequest(element=element, **kwargs)
        return await self._execute_parse_request(request)
    
    async def parse_batch(self, elements: List['UnifiedElement'], **kwargs) -> List[ParseResult]:
        """Parse multiple elements concurrently."""
        requests = [ParseRequest(element=elem, **kwargs) for elem in elements]
        
        # Process in batches to respect concurrency limits
        results = []
        for i in range(0, len(requests), self.max_concurrent):
            batch = requests[i:i + self.max_concurrent]
            batch_results = await asyncio.gather(
                *[self._execute_parse_request(req) for req in batch],
                return_exceptions=True
            )
            results.extend(batch_results)
        
        return results
    
    async def _execute_parse_request(self, request: ParseRequest) -> ParseResult:
        """Execute a single parse request with monitoring."""
        start_time = time.time()
        self._stats['total_requests'] += 1
        
        try:
            # Check cache first
            if request.use_cache and self.enable_caching:
                cached_result = await self.cache.get(request.element)
                if cached_result:
                    self._stats['cache_hits'] += 1
                    return ParseResult(
                        success=True,
                        result=cached_result,
                        error=None,
                        processing_time=time.time() - start_time,
                        cache_hit=True
                    )
            
            # Get appropriate parser
            parser = self.factory.get_parser(request.element)
            if not parser:
                return await self.fallback.handle_no_parser(request.element)
            
            # Execute parsing with timeout
            result = await asyncio.wait_for(
                parser.parse_with_monitoring(request.element),
                timeout=request.timeout
            )
            
            # Cache successful results
            if result.success and self.enable_caching:
                await self.cache.set(request.element, result)
            
            # Update statistics
            self._stats['successful_parses'] += 1
            processing_time = time.time() - start_time
            self._stats['total_time'] += processing_time
            
            # Record metrics
            await self.monitor.record_parse_metrics(
                parser_type=parser.__class__.__name__,
                element_type=request.element.type,
                success=result.success,
                processing_time=processing_time,
                confidence=result.metadata.confidence
            )
            
            return ParseResult(
                success=True,
                result=result,
                error=None,
                processing_time=processing_time
            )
            
        except asyncio.TimeoutError:
            error = f"Parsing timeout after {request.timeout}s"
            self._stats['errors'] += 1
            return ParseResult(
                success=False,
                result=None,
                error=error,
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            error = f"Parsing error: {str(e)}"
            self._stats['errors'] += 1
            
            # Try fallback strategies
            fallback_result = await self.fallback.handle_error(request.element, e)
            if fallback_result:
                return fallback_result
            
            return ParseResult(
                success=False,
                result=None,
                error=error,
                processing_time=time.time() - start_time
            )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive parsing statistics."""
        stats = self._stats.copy()
        if stats['total_requests'] > 0:
            stats['success_rate'] = stats['successful_parses'] / stats['total_requests']
            stats['cache_hit_rate'] = stats['cache_hits'] / stats['total_requests']
            stats['average_time'] = stats['total_time'] / stats['total_requests']
        
        return stats
```

### 3. Performance Cache (`integration/cache.py`)
```python
import asyncio
import json
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

@dataclass
class CacheEntry:
    result: 'ParserResult'
    timestamp: datetime
    access_count: int = 0
    ttl_seconds: int = 3600

class ParserCache:
    """Intelligent caching system for parser results."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.max_size = config.get('max_size', 10000)
        self.default_ttl = config.get('default_ttl', 3600)
        self.enable_persistence = config.get('enable_persistence', False)
        
        self._cache: Dict[str, CacheEntry] = {}
        self._access_times = {}
        
        # Start cleanup task
        asyncio.create_task(self._cleanup_expired())
    
    async def get(self, element: 'UnifiedElement') -> Optional['ParserResult']:
        """Get cached result for element."""
        cache_key = self._generate_key(element)
        
        entry = self._cache.get(cache_key)
        if not entry:
            return None
        
        # Check if expired
        if self._is_expired(entry):
            del self._cache[cache_key]
            return None
        
        # Update access statistics
        entry.access_count += 1
        self._access_times[cache_key] = datetime.utcnow()
        
        return entry.result
    
    async def set(self, element: 'UnifiedElement', result: 'ParserResult', ttl: int = None):
        """Cache parser result."""
        cache_key = self._generate_key(element)
        
        # Evict old entries if at capacity
        if len(self._cache) >= self.max_size:
            await self._evict_oldest()
        
        entry = CacheEntry(
            result=result,
            timestamp=datetime.utcnow(),
            ttl_seconds=ttl or self.default_ttl
        )
        
        self._cache[cache_key] = entry
        self._access_times[cache_key] = datetime.utcnow()
    
    def _generate_key(self, element: 'UnifiedElement') -> str:
        """Generate cache key for element."""
        content = f"{element.type}:{element.content_hash if hasattr(element, 'content_hash') else element.text}"
        return hashlib.md5(content.encode()).hexdigest()
```

## 🧪 Testing Requirements

### Test Coverage Goals
- **>95% code coverage** across all integration components
- **End-to-end testing** with all parser types
- **Performance stress testing** with 1000+ concurrent requests
- **Production scenario simulation**

### Key Test Scenarios
1. **Code Parser Tests**
   - 20+ programming languages
   - Syntax validation and highlighting
   - Complex code structure extraction

2. **Integration System Tests**
   - Multi-parser coordination
   - Cache performance and eviction
   - Error recovery and fallbacks
   - Performance under load

## 🔗 Integration Points

### With All Previous Agents
```python
# Integrates all parser implementations
from .table import TableParser
from .image import ImageParser
from .formula import FormulaParser
from .code import CodeParser

# Unified through manager
manager = ParserManager()
results = await manager.parse_batch(elements)
```

### With Main Processing Pipeline
- Event system integration for parser notifications
- Batch processing optimization
- Monitoring and observability integration

## 🚀 GitHub Workflow

1. **Wait for all agents** to complete their implementations
2. **Create Branch**: `feature/code-parser-integration`
3. **Implement code parser** with 20+ languages
4. **Build integration system** with caching and monitoring
5. **Comprehensive testing** with all parser types
6. **Performance optimization** and benchmarking
7. **Create PR** with complete system documentation

## ✅ Success Criteria

- [ ] Code parser supports 20+ programming languages
- [ ] Language detection >95% accuracy
- [ ] Syntax highlighting and validation
- [ ] Function/class extraction from code
- [ ] Complete parser registry with auto-discovery
- [ ] Intelligent caching with >80% hit ratio
- [ ] Performance monitoring and metrics
- [ ] System handles 1000+ elements/minute
- [ ] Production error handling and recovery
- [ ] Complete API documentation
- [ ] End-to-end integration tests
- [ ] >95% test coverage across all components

**Your integration system will bring together all parsers into a production-ready service!**