# AGENT 1 ASSIGNMENT: Core Search Engine & Indexing Infrastructure

## 🎯 Your Mission (Agent 1)
You are **Agent 1** implementing the foundation of the Search and Filter System. Your role is to create the core search engine with high-performance indexing, real-time updates, and full-text search capabilities.

## 📋 Your Specific Tasks

### 1. Core Search Engine Architecture
```python
# Create src/torematrix/ui/search/engine.py
class SearchEngine:
    """Core search engine with full-text capabilities"""
    
    def __init__(self, indexer: SearchIndexer):
        self.indexer = indexer
        self.parser = QueryParser()
        self.ranker = SearchRanker()
    
    async def search(self, query: str, filters: Optional[Dict] = None) -> SearchResults:
        """Execute search with instant results (<100ms)"""
        
    async def search_fuzzy(self, query: str, tolerance: float = 0.8) -> SearchResults:
        """Fuzzy search for typo tolerance"""
        
    async def search_regex(self, pattern: str) -> SearchResults:
        """Regex search for advanced users"""
```

### 2. Real-Time Search Indexer
```python
# Create src/torematrix/ui/search/indexer.py
class SearchIndexer:
    """High-performance search indexer with real-time updates"""
    
    def __init__(self):
        self.index = {}  # In-memory inverted index
        self.element_store = {}
        self.stemmer = PorterStemmer()
    
    async def index_element(self, element: Element) -> None:
        """Index single element with <10ms performance"""
        
    async def update_element(self, element: Element) -> None:
        """Update indexed element in real-time"""
        
    async def remove_element(self, element_id: str) -> None:
        """Remove element from index"""
        
    def tokenize(self, text: str) -> List[str]:
        """Advanced tokenization with stemming"""
```

### 3. Query Parser and Validator
```python
# Create src/torematrix/ui/search/parser.py
class QueryParser:
    """Parse and validate search queries"""
    
    def parse(self, query: str) -> ParsedQuery:
        """Parse search query into structured format"""
        
    def validate(self, query: str) -> ValidationResult:
        """Validate query syntax and return errors"""
        
    def extract_terms(self, query: str) -> List[SearchTerm]:
        """Extract individual search terms"""
```

### 4. Search Result Ranking
```python
# Create src/torematrix/ui/search/ranker.py
class SearchRanker:
    """Rank search results by relevance"""
    
    def rank_results(self, results: List[Element], query: str) -> List[RankedResult]:
        """Rank results with TF-IDF and relevance scoring"""
        
    def calculate_relevance(self, element: Element, query: str) -> float:
        """Calculate relevance score for element"""
```

### 5. Search History Tracking
```python
# Create src/torematrix/ui/search/history.py
class SearchHistory:
    """Track and manage search history"""
    
    def add_search(self, query: str, results_count: int) -> None:
        """Add search to history with timestamp"""
        
    def get_recent_searches(self, limit: int = 10) -> List[SearchEntry]:
        """Get recent search queries"""
        
    def get_popular_searches(self, limit: int = 10) -> List[SearchEntry]:
        """Get most popular search queries"""
```

## 🔧 Files You Must Create

### Core Implementation Files
```
src/torematrix/ui/search/
├── __init__.py                    # Package initialization
├── engine.py                      # SearchEngine class (PRIMARY)
├── indexer.py                     # SearchIndexer with real-time updates (PRIMARY)
├── parser.py                      # QueryParser and validator (PRIMARY)
├── ranker.py                      # SearchRanker for relevance scoring
├── history.py                     # SearchHistory tracking
└── types.py                       # Search-related types and enums
```

### Test Files (MANDATORY >95% Coverage)
```
tests/unit/ui/search/
├── __init__.py
├── test_engine.py                 # SearchEngine tests (20+ tests)
├── test_indexer.py                # SearchIndexer tests (25+ tests)
├── test_parser.py                 # QueryParser tests (15+ tests)
├── test_ranker.py                 # Ranking tests (10+ tests)
└── test_history.py                # History tests (10+ tests)
```

## 🧪 Acceptance Criteria You Must Meet

### Performance Requirements
- [ ] **Search Performance**: <100ms for 10K+ elements
- [ ] **Index Update Time**: <10ms per element
- [ ] **Memory Usage**: <1MB for 1K elements indexed
- [ ] **Thread Safety**: All operations must be thread-safe

### Functional Requirements
- [ ] **Full-text Search**: Support for complex text queries
- [ ] **Real-time Updates**: Index updates on element changes
- [ ] **Query Parsing**: Parse complex search expressions
- [ ] **Fuzzy Search**: Typo tolerance with configurable threshold
- [ ] **Regex Search**: Advanced pattern matching
- [ ] **Search History**: Persistent history with timestamps
- [ ] **Result Ranking**: TF-IDF based relevance scoring

### Quality Requirements
- [ ] **Test Coverage**: >95% across all components
- [ ] **Type Safety**: Full type annotations
- [ ] **Documentation**: 100% API documentation
- [ ] **Error Handling**: Comprehensive error management
- [ ] **Performance Benchmarks**: Documented performance metrics

## 🔌 Integration Points

### Dependencies (What You Need)
- **Element Model** (#2): Access to unified element structure
- **State Management** (#3): Integration with application state
- **Event Bus**: For real-time index updates

### What You Provide (For Other Agents)
- **SearchEngine Interface**: Core search functionality
- **SearchIndexer Interface**: Indexing and updating
- **Query Types**: Parsed query structures
- **Search Results Format**: Standardized result format

## 🚀 Getting Started

### 1. Create Your Feature Branch
```bash
git checkout main
git pull origin main
git checkout -b feature/search-engine-agent1-issue213
```

### 2. Set Up Package Structure
```bash
mkdir -p src/torematrix/ui/search
mkdir -p tests/unit/ui/search
touch src/torematrix/ui/search/__init__.py
touch tests/unit/ui/search/__init__.py
```

### 3. Start with Core Engine
Begin with `engine.py` as the central component, then build supporting classes.

## 🎯 Success Metrics

### Performance Targets
- **Search Latency**: <100ms for complex queries
- **Index Performance**: 1000 elements/second indexing
- **Memory Efficiency**: <1MB per 1000 indexed elements
- **Concurrency**: Support 10+ concurrent searches

### Quality Targets
- **Test Coverage**: >95% line coverage
- **Type Coverage**: 100% type annotations
- **Documentation**: Every public method documented
- **Error Handling**: Graceful handling of all edge cases

## 📚 Technical Implementation Details

### Search Index Structure
```python
# Inverted index structure
{
    "term": {
        "documents": {
            "element_id": {
                "positions": [1, 15, 23],  # Term positions in text
                "frequency": 3,             # Term frequency
                "weight": 0.85             # TF-IDF weight
            }
        },
        "document_count": 125,  # Number of documents containing term
        "total_frequency": 387  # Total occurrences across all documents
    }
}
```

### Query Processing Pipeline
1. **Parse** → Convert query string to structured format
2. **Validate** → Check syntax and constraints
3. **Execute** → Search inverted index
4. **Rank** → Apply relevance scoring
5. **Return** → Structured results with metadata

### Real-Time Update Strategy
- **Incremental Updates**: Update only changed elements
- **Batch Processing**: Group updates for efficiency
- **Lock-Free Design**: Minimize blocking operations
- **Version Control**: Track index versions for consistency

## 🔗 Communication Protocol

### Daily Standup Format
```markdown
## Agent 1 Progress Report - Day X

### ✅ Completed Today
- [List specific accomplishments]

### 🚧 In Progress
- [Current work items]

### 🔄 Integration Points Used
- [Which dependencies you integrated with]

### 📊 Performance Metrics Achieved
- [Specific measurements]

### 🚨 Blockers/Issues
- [Any impediments]

### 📋 Tomorrow's Plan
- [Next day's focus]
```

## 🏁 Definition of Done

Your work is complete when:
1. ✅ All acceptance criteria met and tested
2. ✅ >95% test coverage achieved
3. ✅ Performance benchmarks documented
4. ✅ Integration points working with existing systems
5. ✅ API documentation complete
6. ✅ Code review passed
7. ✅ All tests passing in CI
8. ✅ Ready for Agent 2 integration

## 🤝 Handoff to Agent 2

When you're done, ensure:
- **SearchEngine** is fully functional and tested
- **SearchIndexer** handles real-time updates
- **Interfaces are clean** and well-documented
- **Performance metrics** are documented
- **Integration guide** is provided for Agent 2

Agent 2 will build advanced filtering on top of your search infrastructure!