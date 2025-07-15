"""
Advanced Search Engine for Element Management

Provides comprehensive search capabilities with indexing, query parsing,
result ranking, and performance optimization.
"""

import time
import asyncio
from typing import List, Dict, Set, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
import threading

from ....core.models.element import Element, ElementType
from ....core.state.store import StateStore
from .indexer import ElementIndexer, IndexStrategy, SearchIndex
from .query_parser import QueryParser, SearchQuery, QueryType, BooleanOperator


class SearchMode(Enum):
    """Search execution modes."""
    SYNCHRONOUS = "sync"      # Immediate search
    ASYNCHRONOUS = "async"    # Background search
    STREAMING = "streaming"   # Results as they arrive


class RankingStrategy(Enum):
    """Result ranking strategies."""
    RELEVANCE = "relevance"   # Text relevance scoring
    CONFIDENCE = "confidence" # Element confidence scoring
    RECENCY = "recency"      # Most recently modified
    POSITION = "position"    # Document position
    CUSTOM = "custom"        # Custom scoring function


@dataclass
class SearchResult:
    """Individual search result with metadata."""
    element_id: str
    element: Element
    score: float = 0.0
    match_info: Dict[str, Any] = field(default_factory=dict)
    highlighted_text: str = ""
    
    def __post_init__(self):
        if not self.highlighted_text:
            self.highlighted_text = self.element.text


@dataclass
class SearchResultSet:
    """Collection of search results with metadata."""
    results: List[SearchResult] = field(default_factory=list)
    total_count: int = 0
    search_time_ms: float = 0.0
    query: Optional[SearchQuery] = None
    has_more: bool = False
    offset: int = 0
    
    def get_element_ids(self) -> List[str]:
        """Get list of element IDs from results."""
        return [result.element_id for result in self.results]
    
    def get_elements(self) -> List[Element]:
        """Get list of elements from results."""
        return [result.element for result in self.results]
    
    def get_top_result(self) -> Optional[SearchResult]:
        """Get highest scoring result."""
        return self.results[0] if self.results else None


class SearchEngine:
    """Base search engine interface."""
    
    def __init__(self, state_store: StateStore):
        self.state_store = state_store
        self.query_parser = QueryParser()
    
    def search(self, query_string: str, **options) -> SearchResultSet:
        """Perform search and return results."""
        raise NotImplementedError
    
    def search_async(self, query_string: str, callback: Callable, **options) -> None:
        """Perform asynchronous search."""
        raise NotImplementedError
    
    def suggest(self, partial_query: str, limit: int = 10) -> List[str]:
        """Get search suggestions."""
        raise NotImplementedError


class IndexedSearchEngine(SearchEngine):
    """High-performance search engine with indexing and advanced features."""
    
    def __init__(self, state_store: StateStore, index_strategy: IndexStrategy = IndexStrategy.BALANCED):
        super().__init__(state_store)
        
        # Core components
        self.indexer = ElementIndexer(state_store, index_strategy)
        self.ranking_strategy = RankingStrategy.RELEVANCE
        self.search_mode = SearchMode.SYNCHRONOUS
        
        # Execution
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="search")
        
        # Configuration
        self.max_results = 1000
        self.default_limit = 50
        self.enable_highlighting = True
        self.highlight_tags = ("<mark>", "</mark>")
        
        # Caching
        self.result_cache: Dict[str, Tuple[SearchResultSet, float]] = {}
        self.cache_ttl = 300  # 5 minutes
        self.cache_lock = threading.Lock()
        
        # Custom scoring functions
        self.custom_scorers: Dict[str, Callable[[Element, SearchQuery], float]] = {}
    
    def search(self, query_string: str, **options) -> SearchResultSet:
        """
        Perform comprehensive search with ranking and filtering.
        
        Args:
            query_string: Search query string
            **options: Search options including:
                - limit: Maximum results to return
                - offset: Result offset for pagination
                - ranking: Ranking strategy
                - filters: Additional filters
                - highlight: Enable result highlighting
        
        Returns:
            SearchResultSet with ranked results
        """
        start_time = time.time()
        
        # Check cache first
        cache_key = self._get_cache_key(query_string, options)
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            return cached_result
        
        try:
            # Parse query
            query = self.query_parser.parse(query_string)
            
            # Validate query
            errors = self.query_parser.validate_query(query)
            if errors:
                return SearchResultSet(
                    results=[],
                    total_count=0,
                    search_time_ms=(time.time() - start_time) * 1000,
                    query=query
                )
            
            # Execute search
            matching_ids = self._execute_search(query)
            
            # Apply additional filters
            matching_ids = self._apply_filters(matching_ids, options.get('filters', {}))
            
            # Get elements and create results
            elements = self._get_elements_by_ids(matching_ids)
            search_results = self._create_search_results(elements, query, options)
            
            # Rank results
            ranking = options.get('ranking', self.ranking_strategy)
            search_results = self._rank_results(search_results, query, ranking)
            
            # Apply pagination
            limit = options.get('limit', self.default_limit)
            offset = options.get('offset', 0)
            total_count = len(search_results)
            
            paginated_results = search_results[offset:offset + limit]
            has_more = offset + limit < total_count
            
            # Create result set
            result_set = SearchResultSet(
                results=paginated_results,
                total_count=total_count,
                search_time_ms=(time.time() - start_time) * 1000,
                query=query,
                has_more=has_more,
                offset=offset
            )
            
            # Cache result
            self._cache_result(cache_key, result_set)
            
            return result_set
            
        except Exception as e:
            # Return empty result set with error info
            return SearchResultSet(
                results=[],
                total_count=0,
                search_time_ms=(time.time() - start_time) * 1000,
                query=query if 'query' in locals() else None
            )
    
    def search_async(self, query_string: str, callback: Callable[[SearchResultSet], None], **options) -> None:
        """Perform asynchronous search with callback."""
        def search_task():
            result = self.search(query_string, **options)
            callback(result)
        
        self.executor.submit(search_task)
    
    def search_streaming(self, query_string: str, callback: Callable[[SearchResult], None], **options) -> None:
        """Perform streaming search with per-result callbacks."""
        def streaming_task():
            # Parse query
            query = self.query_parser.parse(query_string)
            
            # Execute search
            matching_ids = self._execute_search(query)
            
            # Stream results as they're processed
            for element_id in matching_ids:
                element = self._get_element_by_id(element_id)
                if element:
                    result = self._create_search_result(element, query, options)
                    callback(result)
        
        self.executor.submit(streaming_task)
    
    def suggest(self, partial_query: str, limit: int = 10) -> List[str]:
        """Get search suggestions for partial query."""
        suggestions = []
        
        # Get term suggestions from index
        term_suggestions = self.indexer.get_suggestions(partial_query, limit // 2)
        suggestions.extend(term_suggestions)
        
        # Get field suggestions
        if ':' not in partial_query:
            field_suggestions = self.query_parser.get_field_suggestions()
            matching_fields = [f"{field}:" for field in field_suggestions 
                             if field.startswith(partial_query.lower())]
            suggestions.extend(matching_fields[:limit // 2])
        
        return suggestions[:limit]
    
    def _execute_search(self, query: SearchQuery) -> Set[str]:
        """Execute search query against index."""
        if not query.tokens:
            return set()
        
        # Handle different query types
        if query.is_simple():
            # Simple text search
            token = query.tokens[0]
            return self.indexer.search(token.value, fuzzy=query.fuzzy_enabled)
        
        # Complex query with multiple tokens and operators
        result_sets = []
        
        for token in query.tokens:
            token_results = self._execute_token_search(token, query)
            result_sets.append(token_results)
        
        # Combine results with boolean logic
        if not result_sets:
            return set()
        
        final_results = result_sets[0]
        
        for i, operator in enumerate(query.boolean_operators):
            if i + 1 < len(result_sets):
                next_results = result_sets[i + 1]
                
                if operator == BooleanOperator.AND:
                    final_results = final_results.intersection(next_results)
                elif operator == BooleanOperator.OR:
                    final_results = final_results.union(next_results)
                elif operator == BooleanOperator.NOT:
                    final_results = final_results.difference(next_results)
        
        return final_results
    
    def _execute_token_search(self, token, query: SearchQuery) -> Set[str]:
        """Execute search for a single token."""
        if token.type == QueryType.SIMPLE:
            return self.indexer.search(token.value, fuzzy=query.fuzzy_enabled)
        
        elif token.type == QueryType.FIELD:
            if token.field == 'type':
                try:
                    element_type = ElementType(token.value.upper())
                    return self.indexer.search_by_type({element_type})
                except ValueError:
                    return set()
            elif token.field == 'page':
                try:
                    page_num = int(token.value)
                    return self.indexer.search_by_page({page_num})
                except ValueError:
                    return set()
            elif token.field == 'confidence':
                try:
                    confidence = float(token.value)
                    return self.indexer.search_by_confidence(confidence - 0.1, confidence + 0.1)
                except ValueError:
                    return set()
            else:
                # Generic field search
                return self.indexer.search(f"{token.field}:{token.value}")
        
        elif token.type == QueryType.PHRASE:
            return self.indexer.search(token.value, fuzzy=False)
        
        elif token.type == QueryType.WILDCARD:
            # Convert wildcard to fuzzy search
            return self.indexer.search(token.value, fuzzy=True)
        
        elif token.type == QueryType.FUZZY:
            return self.indexer.search(token.value, fuzzy=True)
        
        else:
            # Default to simple search
            return self.indexer.search(token.value, fuzzy=query.fuzzy_enabled)
    
    def _apply_filters(self, element_ids: Set[str], filters: Dict[str, Any]) -> Set[str]:
        """Apply additional filters to search results."""
        if not filters:
            return element_ids
        
        filtered_ids = element_ids.copy()
        
        # Confidence range filter
        if 'confidence_range' in filters:
            min_conf, max_conf = filters['confidence_range']
            confidence_matches = self.indexer.search_by_confidence(min_conf, max_conf)
            filtered_ids = filtered_ids.intersection(confidence_matches)
        
        # Page range filter
        if 'page_range' in filters:
            min_page, max_page = filters['page_range']
            page_matches = set()
            for page in range(min_page, max_page + 1):
                page_matches.update(self.indexer.search_by_page({page}))
            filtered_ids = filtered_ids.intersection(page_matches)
        
        # Element type filter
        if 'element_types' in filters:
            type_matches = self.indexer.search_by_type(set(filters['element_types']))
            filtered_ids = filtered_ids.intersection(type_matches)
        
        return filtered_ids
    
    def _get_elements_by_ids(self, element_ids: Set[str]) -> List[Element]:
        """Get elements by their IDs from state store."""
        state = self.state_store.get_state()
        elements_dict = state.get('elements', {})
        
        elements = []
        for element_id in element_ids:
            if element_id in elements_dict:
                elements.append(elements_dict[element_id])
        
        return elements
    
    def _get_element_by_id(self, element_id: str) -> Optional[Element]:
        """Get single element by ID."""
        state = self.state_store.get_state()
        elements_dict = state.get('elements', {})
        return elements_dict.get(element_id)
    
    def _create_search_results(self, elements: List[Element], query: SearchQuery, options: Dict[str, Any]) -> List[SearchResult]:
        """Create SearchResult objects from elements."""
        results = []
        
        for element in elements:
            result = self._create_search_result(element, query, options)
            results.append(result)
        
        return results
    
    def _create_search_result(self, element: Element, query: SearchQuery, options: Dict[str, Any]) -> SearchResult:
        """Create a single SearchResult."""
        # Calculate base score
        score = self._calculate_base_score(element, query)
        
        # Create match info
        match_info = self._create_match_info(element, query)
        
        # Create highlighted text
        highlighted_text = element.text
        if options.get('highlight', self.enable_highlighting):
            highlighted_text = self._highlight_matches(element.text, query)
        
        return SearchResult(
            element_id=element.element_id,
            element=element,
            score=score,
            match_info=match_info,
            highlighted_text=highlighted_text
        )
    
    def _calculate_base_score(self, element: Element, query: SearchQuery) -> float:
        """Calculate base relevance score for element."""
        score = 0.0
        
        # Text relevance scoring
        text_terms = query.get_text_terms()
        if text_terms and element.text:
            text_lower = element.text.lower()
            for term in text_terms:
                term_lower = term.lower()
                # Count occurrences
                count = text_lower.count(term_lower)
                if count > 0:
                    # TF-IDF inspired scoring
                    tf = count / len(text_lower.split())
                    score += tf * 10  # Base multiplier
        
        # Confidence bonus
        if element.metadata and element.metadata.confidence:
            score += element.metadata.confidence * 5
        
        # Element type bonus (some types might be more relevant)
        type_bonuses = {
            ElementType.TITLE: 3.0,
            ElementType.HEADER: 2.0,
            ElementType.NARRATIVE_TEXT: 1.0,
            ElementType.TABLE: 1.5,
            ElementType.LIST: 1.2
        }
        score += type_bonuses.get(element.element_type, 1.0)
        
        return score
    
    def _create_match_info(self, element: Element, query: SearchQuery) -> Dict[str, Any]:
        """Create match information for result."""
        match_info = {}
        
        # Field matches
        field_searches = query.get_field_searches()
        for field, terms in field_searches.items():
            match_info[f"{field}_matches"] = terms
        
        # Text matches
        text_terms = query.get_text_terms()
        if text_terms and element.text:
            text_lower = element.text.lower()
            matches = []
            for term in text_terms:
                if term.lower() in text_lower:
                    matches.append(term)
            match_info['text_matches'] = matches
        
        return match_info
    
    def _highlight_matches(self, text: str, query: SearchQuery) -> str:
        """Add highlighting to search matches in text."""
        if not text or not query.tokens:
            return text
        
        highlighted = text
        start_tag, end_tag = self.highlight_tags
        
        # Get all terms to highlight
        terms_to_highlight = set()
        for token in query.tokens:
            if token.type in (QueryType.SIMPLE, QueryType.PHRASE, QueryType.WILDCARD):
                terms_to_highlight.add(token.value.lower())
        
        # Apply highlighting (simple approach)
        for term in terms_to_highlight:
            if term in text.lower():
                # Case-insensitive replace with highlighting
                import re
                pattern = re.compile(re.escape(term), re.IGNORECASE)
                highlighted = pattern.sub(f"{start_tag}\\g<0>{end_tag}", highlighted)
        
        return highlighted
    
    def _rank_results(self, results: List[SearchResult], query: SearchQuery, strategy: RankingStrategy) -> List[SearchResult]:
        """Rank search results according to strategy."""
        if strategy == RankingStrategy.RELEVANCE:
            return sorted(results, key=lambda r: r.score, reverse=True)
        
        elif strategy == RankingStrategy.CONFIDENCE:
            return sorted(results, 
                         key=lambda r: r.element.metadata.confidence if r.element.metadata else 0.0,
                         reverse=True)
        
        elif strategy == RankingStrategy.RECENCY:
            # Sort by element_id (assuming newer elements have later IDs)
            return sorted(results, key=lambda r: r.element_id, reverse=True)
        
        elif strategy == RankingStrategy.POSITION:
            # Sort by page number, then by element order
            def position_key(result):
                page = result.element.metadata.page_number if result.element.metadata else 0
                return (page or 0, result.element_id)
            
            return sorted(results, key=position_key)
        
        elif strategy == RankingStrategy.CUSTOM:
            # Use custom scoring function if available
            custom_scorer = self.custom_scorers.get('default')
            if custom_scorer:
                for result in results:
                    result.score = custom_scorer(result.element, query)
                return sorted(results, key=lambda r: r.score, reverse=True)
        
        # Default to relevance
        return sorted(results, key=lambda r: r.score, reverse=True)
    
    def _get_cache_key(self, query_string: str, options: Dict[str, Any]) -> str:
        """Generate cache key for query and options."""
        import hashlib
        key_data = f"{query_string}:{str(sorted(options.items()))}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _get_cached_result(self, cache_key: str) -> Optional[SearchResultSet]:
        """Get cached search result if still valid."""
        with self.cache_lock:
            if cache_key in self.result_cache:
                result, timestamp = self.result_cache[cache_key]
                if time.time() - timestamp < self.cache_ttl:
                    return result
                else:
                    del self.result_cache[cache_key]
        return None
    
    def _cache_result(self, cache_key: str, result: SearchResultSet) -> None:
        """Cache search result."""
        with self.cache_lock:
            self.result_cache[cache_key] = (result, time.time())
            
            # Clean old cache entries
            if len(self.result_cache) > 100:  # Max cache size
                oldest_key = min(self.result_cache.keys(), 
                               key=lambda k: self.result_cache[k][1])
                del self.result_cache[oldest_key]
    
    def add_custom_scorer(self, name: str, scorer_func: Callable[[Element, SearchQuery], float]) -> None:
        """Add custom scoring function."""
        self.custom_scorers[name] = scorer_func
    
    def set_ranking_strategy(self, strategy: RankingStrategy) -> None:
        """Set default ranking strategy."""
        self.ranking_strategy = strategy
    
    def set_search_mode(self, mode: SearchMode) -> None:
        """Set search execution mode."""
        self.search_mode = mode
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get search engine statistics."""
        index_stats = self.indexer.get_statistics()
        
        return {
            'index_statistics': index_stats.__dict__,
            'cache_size': len(self.result_cache),
            'ranking_strategy': self.ranking_strategy.value,
            'search_mode': self.search_mode.value
        }
    
    def clear_cache(self) -> None:
        """Clear search result cache."""
        with self.cache_lock:
            self.result_cache.clear()
    
    def shutdown(self) -> None:
        """Shutdown search engine."""
        self.executor.shutdown(wait=True)
        self.indexer.shutdown()