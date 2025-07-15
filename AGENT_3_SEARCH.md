# AGENT 3 ASSIGNMENT: Performance Optimization & Caching

## 🎯 Your Mission (Agent 3)
You are **Agent 3** implementing high-performance optimization and intelligent caching for the Search and Filter System. Your role is to make everything blazingly fast with smart caching, lazy loading, and performance monitoring.

## 📋 Your Specific Tasks

### 1. Intelligent Search Result Caching
```python
# Create src/torematrix/ui/search/cache.py
class CacheManager:
    """LRU cache for search results with intelligent invalidation"""
    
    def __init__(self, max_size: int = 1000, ttl: int = 300):
        self.cache = LRUCache(max_size)
        self.ttl = ttl
        self.hit_stats = CacheStats()
    
    async def get_cached_results(self, cache_key: str) -> Optional[CachedResults]:
        """Get results from cache if available and valid"""
        
    async def cache_results(self, cache_key: str, results: SearchResults) -> None:
        """Cache search results with metadata"""
        
    async def invalidate_element_caches(self, element_id: str) -> None:
        """Invalidate caches when element changes"""
        
    def generate_cache_key(self, query: str, filters: List[Filter]) -> str:
        """Generate stable cache key for query + filters"""
```

### 2. Lazy Loading for Large Result Sets
```python
# Create src/torematrix/ui/search/lazy_loader.py
class LazyResultLoader:
    """Efficiently load large result sets on demand"""
    
    def __init__(self, page_size: int = 50):
        self.page_size = page_size
        self.loaded_pages = {}
        self.total_count = 0
    
    async def load_page(self, page_number: int) -> ResultPage:
        """Load specific page of results"""
        
    async def preload_next_pages(self, current_page: int, count: int = 2) -> None:
        """Preload upcoming pages in background"""
        
    def get_virtual_item(self, index: int) -> Optional[Element]:
        """Get item by index, loading page if needed"""
        
    async def estimate_total_count(self, query: str, filters: List[Filter]) -> int:
        """Fast estimation of total result count"""
```

### 3. Search Suggestions with Autocomplete
```python
# Create src/torematrix/ui/search/suggestions.py
class SearchSuggestionEngine:
    """Real-time search suggestions and autocomplete"""
    
    def __init__(self):
        self.suggestion_cache = {}
        self.popular_queries = PopularityTracker()
        self.typo_corrector = TypoCorrector()
    
    async def get_suggestions(self, partial_query: str, limit: int = 10) -> List[Suggestion]:
        """Get search suggestions for partial query (<50ms)"""
        
    async def get_completions(self, partial_query: str) -> List[str]:
        """Get query completions based on history and popularity"""
        
    async def correct_typos(self, query: str) -> List[str]:
        """Suggest typo corrections"""
        
    def update_popularity(self, query: str, results_count: int) -> None:
        """Update query popularity for better suggestions"""
```

### 4. Virtual Scrolling for Results
```python
# Create src/torematrix/ui/search/pagination.py
class VirtualScrollManager:
    """Virtual scrolling for massive result sets"""
    
    def __init__(self, viewport_height: int, item_height: int):
        self.viewport_height = viewport_height
        self.item_height = item_height
        self.visible_range = (0, 0)
        self.buffer_size = 10  # Items to buffer outside viewport
    
    def calculate_visible_range(self, scroll_position: int, total_items: int) -> Tuple[int, int]:
        """Calculate which items should be visible"""
        
    async def get_visible_items(self, scroll_position: int) -> List[Element]:
        """Get items for current scroll position"""
        
    def update_scroll_position(self, position: int) -> None:
        """Update scroll and trigger loading if needed"""
```

### 5. Background Indexing Optimization
```python
# Create src/torematrix/ui/search/optimization/indexing.py
class BackgroundIndexer:
    """Non-blocking background indexing for large datasets"""
    
    def __init__(self, search_indexer: SearchIndexer):
        self.indexer = search_indexer
        self.queue = asyncio.Queue()
        self.is_running = False
        self.batch_size = 100
    
    async def queue_for_indexing(self, elements: List[Element]) -> None:
        """Queue elements for background indexing"""
        
    async def process_indexing_queue(self) -> None:
        """Process indexing queue in background"""
        
    async def batch_index_elements(self, elements: List[Element]) -> None:
        """Index elements in optimized batches"""
        
    def get_indexing_progress(self) -> IndexingProgress:
        """Get current indexing progress"""
```

### 6. Search Analytics and Monitoring
```python
# Create src/torematrix/ui/search/analytics.py
class SearchAnalytics:
    """Track search performance and usage patterns"""
    
    def __init__(self):
        self.metrics = SearchMetrics()
        self.usage_patterns = UsageTracker()
    
    def record_search(self, query: str, results_count: int, duration_ms: int) -> None:
        """Record search execution metrics"""
        
    def record_filter_usage(self, filters: List[Filter], duration_ms: int) -> None:
        """Record filter performance"""
        
    def get_performance_report(self) -> PerformanceReport:
        """Generate performance analysis report"""
        
    def get_popular_queries(self, period: TimePeriod) -> List[PopularQuery]:
        """Get most popular search queries"""
        
    def detect_slow_queries(self, threshold_ms: int = 1000) -> List[SlowQuery]:
        """Identify slow-performing queries"""
```

### 7. Memory-Efficient Result Streaming
```python
# Create src/torematrix/ui/search/streaming.py
class ResultStreamer:
    """Stream large result sets efficiently"""
    
    async def stream_results(self, query: str, filters: List[Filter]) -> AsyncIterator[Element]:
        """Stream results without loading all into memory"""
        
    async def stream_filtered_results(self, base_stream: AsyncIterator[Element], 
                                    filters: List[Filter]) -> AsyncIterator[Element]:
        """Apply filters to result stream"""
        
    def create_result_buffer(self, buffer_size: int = 1000) -> ResultBuffer:
        """Create buffered result stream"""
```

## 🔧 Files You Must Create

### Core Optimization Files
```
src/torematrix/ui/search/
├── cache.py                      # CacheManager with LRU caching (PRIMARY)
├── lazy_loader.py                # LazyResultLoader for large datasets (PRIMARY)
├── suggestions.py                # SearchSuggestionEngine with autocomplete
├── pagination.py                 # VirtualScrollManager
├── streaming.py                  # ResultStreamer for memory efficiency
├── analytics.py                  # SearchAnalytics and monitoring
└── monitoring.py                 # Performance monitoring

src/torematrix/ui/search/optimization/
├── __init__.py
├── indexing.py                   # BackgroundIndexer optimization
├── memory.py                     # Memory usage optimization
├── parallel.py                   # Parallel search processing
└── compression.py                # Index compression techniques
```

### Test Files (MANDATORY >95% Coverage)
```
tests/unit/ui/search/
├── test_cache.py                 # Caching tests (20+ tests)
├── test_lazy_loader.py           # Lazy loading tests (15+ tests)
├── test_suggestions.py           # Suggestions tests (15+ tests)
├── test_pagination.py            # Pagination tests (10+ tests)
├── test_streaming.py             # Streaming tests (15+ tests)
├── test_analytics.py             # Analytics tests (10+ tests)
└── test_monitoring.py            # Monitoring tests (10+ tests)

tests/performance/search/
├── __init__.py
├── test_cache_performance.py     # Cache performance benchmarks
├── test_large_dataset.py         # Large dataset performance
└── test_memory_usage.py          # Memory usage testing
```

## 🧪 Acceptance Criteria You Must Meet

### Performance Requirements
- [ ] **Cache Hit Ratio**: >80% for typical usage patterns
- [ ] **Memory Usage**: <100MB for 1M indexed elements
- [ ] **Search Latency**: <50ms for cached results
- [ ] **Suggestion Speed**: <50ms response time
- [ ] **Background Indexing**: No UI blocking or stuttering
- [ ] **Virtual Scrolling**: Smooth scrolling for 100K+ results

### Optimization Requirements
- [ ] **Lazy Loading**: Support 100K+ element datasets efficiently
- [ ] **Result Caching**: Intelligent invalidation on data changes
- [ ] **Memory Streaming**: Process unlimited result sets
- [ ] **Performance Monitoring**: Detailed metrics collection
- [ ] **Background Processing**: Non-blocking indexing operations

### Quality Requirements
- [ ] **Cache Consistency**: Proper invalidation on data changes
- [ ] **Memory Leaks**: No memory leaks in long-running operations
- [ ] **Performance Regression**: 10x improvement over basic implementation
- [ ] **Stress Testing**: Handle extreme load scenarios

## 🔌 Integration Points

### Dependencies (What You Need From Agents 1 & 2)
- **SearchEngine**: Core search functionality to optimize
- **FilterManager**: Filter operations to cache and optimize
- **SearchIndexer**: Real-time index updates to monitor
- **Query Types**: Query structures for cache key generation

### What You Provide (For Agent 4)
- **OptimizedSearchEngine**: Performance-enhanced search
- **CacheManager**: Intelligent result caching
- **LazyLoader**: Efficient large dataset handling
- **PerformanceMonitor**: Real-time performance metrics

## 🚀 Getting Started

### 1. Create Your Feature Branch
```bash
git checkout main
git pull origin main
git checkout -b feature/search-optimization-agent3-issue215
```

### 2. Analyze Current Performance
```bash
# Profile Agent 1 & 2's implementations
python -m cProfile -o search_profile.stats test_search_performance.py
```

### 3. Start with Cache Architecture
Begin with the caching layer as it provides immediate performance gains.

## 🎯 Success Metrics

### Performance Targets
- **10x Performance Improvement**: Over basic implementation
- **Cache Hit Ratio**: >80% in realistic usage scenarios
- **Memory Efficiency**: <100MB for 1M elements
- **Response Time**: <50ms for 90% of operations
- **Throughput**: 1000+ searches/second sustained

### Technical Targets
- **Zero Memory Leaks**: In 24-hour stress testing
- **Graceful Degradation**: Performance under extreme load
- **Resource Usage**: <5% CPU for background operations
- **Cache Efficiency**: >90% relevant cache entries

## 📚 Technical Implementation Details

### LRU Cache Implementation
```python
class LRUCache:
    """Memory-efficient LRU cache with TTL support"""
    
    def __init__(self, max_size: int, ttl: int = 300):
        self.max_size = max_size
        self.ttl = ttl
        self.cache = OrderedDict()
        self.timestamps = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Get item, moving to end if found and valid"""
        if key in self.cache:
            if time.time() - self.timestamps[key] < self.ttl:
                self.cache.move_to_end(key)
                return self.cache[key]
            else:
                self._evict(key)
        return None
    
    def put(self, key: str, value: Any) -> None:
        """Put item, evicting oldest if necessary"""
        if len(self.cache) >= self.max_size:
            oldest_key = next(iter(self.cache))
            self._evict(oldest_key)
        
        self.cache[key] = value
        self.timestamps[key] = time.time()
```

### Virtual Scrolling Algorithm
```python
def calculate_visible_range(scroll_position: int, viewport_height: int, 
                          item_height: int, total_items: int) -> Tuple[int, int]:
    """Calculate which items need to be rendered"""
    
    start_index = max(0, (scroll_position // item_height) - buffer_size)
    visible_count = (viewport_height // item_height) + (2 * buffer_size)
    end_index = min(total_items, start_index + visible_count)
    
    return start_index, end_index
```

### Memory Usage Optimization
```python
class MemoryOptimizer:
    """Monitor and optimize memory usage"""
    
    def __init__(self):
        self.memory_threshold = 100 * 1024 * 1024  # 100MB
    
    def check_memory_usage(self) -> MemoryStatus:
        """Check current memory usage"""
        current_usage = psutil.Process().memory_info().rss
        return MemoryStatus(
            current=current_usage,
            threshold=self.memory_threshold,
            percentage=(current_usage / self.memory_threshold) * 100
        )
    
    async def cleanup_if_needed(self) -> None:
        """Cleanup memory if approaching threshold"""
        if self.check_memory_usage().percentage > 80:
            await self._perform_cleanup()
```

## 🔗 Communication Protocol

### Performance Monitoring Setup
```python
# Instrument existing search operations
@performance_monitor
async def optimized_search(query: str, filters: List[Filter]) -> SearchResults:
    # Check cache first
    cache_key = generate_cache_key(query, filters)
    cached_results = await cache_manager.get_cached_results(cache_key)
    
    if cached_results:
        analytics.record_cache_hit(cache_key)
        return cached_results
    
    # Execute search with monitoring
    start_time = time.time()
    results = await original_search(query, filters)
    duration = (time.time() - start_time) * 1000
    
    # Cache and record metrics
    await cache_manager.cache_results(cache_key, results)
    analytics.record_search(query, len(results), duration)
    
    return results
```

## 🏁 Definition of Done

Your work is complete when:
1. ✅ Cache hit ratio >80% achieved in realistic scenarios
2. ✅ Memory usage <100MB for 1M elements verified
3. ✅ Background indexing doesn't block UI
4. ✅ Virtual scrolling handles 100K+ items smoothly
5. ✅ Performance monitoring provides actionable insights
6. ✅ 10x performance improvement documented
7. ✅ Stress testing passes for 24-hour runs
8. ✅ Ready for Agent 4 integration

## 🤝 Handoff to Agent 4

When you're done, ensure:
- **Performance improvements** are measurable and documented
- **Caching system** is stable and predictable
- **Memory usage** is optimized and monitored
- **Background operations** don't interfere with UI
- **Performance APIs** are ready for integration into UI components

Agent 4 will integrate your optimizations into the final user interface!