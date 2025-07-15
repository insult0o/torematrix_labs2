"""
Search Indexing System for Element Management

Provides high-performance search indexing with real-time updates and fuzzy matching.
"""

import time
import uuid
from typing import Dict, List, Set, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum
import re
import hashlib
from concurrent.futures import ThreadPoolExecutor
import threading

from ....core.models.element import Element, ElementType
from ....core.state.store import StateStore


class IndexStrategy(Enum):
    """Search index optimization strategies."""
    SPEED = "speed"          # Optimized for search speed
    MEMORY = "memory"        # Optimized for memory usage
    BALANCED = "balanced"    # Balanced approach
    REALTIME = "realtime"    # Optimized for real-time updates


@dataclass
class IndexEntry:
    """Single index entry for an element."""
    element_id: str
    element_type: ElementType
    terms: Set[str] = field(default_factory=set)
    text_content: str = ""
    metadata_fields: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    page_number: Optional[int] = None
    languages: List[str] = field(default_factory=list)
    last_modified: float = field(default_factory=time.time)
    
    def matches_term(self, term: str, fuzzy: bool = False) -> bool:
        """Check if entry matches search term."""
        if not fuzzy:
            return term.lower() in self.terms
        
        # Fuzzy matching with edit distance
        for indexed_term in self.terms:
            if self._fuzzy_match(term.lower(), indexed_term):
                return True
        return False
    
    def _fuzzy_match(self, term: str, indexed_term: str, max_distance: int = 2) -> bool:
        """Simple fuzzy matching with Levenshtein distance."""
        if abs(len(term) - len(indexed_term)) > max_distance:
            return False
        
        # Simple edit distance calculation
        dp = [[0] * (len(indexed_term) + 1) for _ in range(len(term) + 1)]
        
        for i in range(len(term) + 1):
            dp[i][0] = i
        for j in range(len(indexed_term) + 1):
            dp[0][j] = j
        
        for i in range(1, len(term) + 1):
            for j in range(1, len(indexed_term) + 1):
                if term[i-1] == indexed_term[j-1]:
                    dp[i][j] = dp[i-1][j-1]
                else:
                    dp[i][j] = 1 + min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1])
        
        return dp[len(term)][len(indexed_term)] <= max_distance


@dataclass
class IndexStatistics:
    """Search index statistics."""
    total_elements: int = 0
    total_terms: int = 0
    index_size_bytes: int = 0
    last_update: float = field(default_factory=time.time)
    update_count: int = 0
    average_terms_per_element: float = 0.0
    most_common_terms: List[Tuple[str, int]] = field(default_factory=list)


class SearchIndex:
    """High-performance search index for document elements."""
    
    def __init__(self, strategy: IndexStrategy = IndexStrategy.BALANCED):
        self.strategy = strategy
        self.entries: Dict[str, IndexEntry] = {}
        self.term_index: Dict[str, Set[str]] = defaultdict(set)  # term -> element_ids
        self.type_index: Dict[ElementType, Set[str]] = defaultdict(set)  # type -> element_ids
        self.page_index: Dict[int, Set[str]] = defaultdict(set)  # page -> element_ids
        self.confidence_ranges: Dict[Tuple[float, float], Set[str]] = {}  # confidence range -> element_ids
        
        # Synchronization
        self._lock = threading.RLock()
        
        # Statistics
        self.statistics = IndexStatistics()
        
        # Configuration based on strategy
        self._configure_strategy()
    
    def _configure_strategy(self) -> None:
        """Configure index based on optimization strategy."""
        if self.strategy == IndexStrategy.SPEED:
            self.max_term_length = 50
            self.min_term_length = 2
            self.enable_stemming = False
            self.enable_fuzzy = True
        elif self.strategy == IndexStrategy.MEMORY:
            self.max_term_length = 20
            self.min_term_length = 3
            self.enable_stemming = True
            self.enable_fuzzy = False
        elif self.strategy == IndexStrategy.REALTIME:
            self.max_term_length = 30
            self.min_term_length = 2
            self.enable_stemming = False
            self.enable_fuzzy = False
        else:  # BALANCED
            self.max_term_length = 30
            self.min_term_length = 2
            self.enable_stemming = True
            self.enable_fuzzy = True
    
    def add_element(self, element: Element) -> None:
        """Add or update element in index."""
        with self._lock:
            # Remove existing entry if present
            if element.element_id in self.entries:
                self.remove_element(element.element_id)
            
            # Extract searchable terms
            terms = self._extract_terms(element)
            
            # Create metadata fields
            metadata_fields = {}
            if element.metadata:
                metadata_fields = {
                    'confidence': element.metadata.confidence,
                    'detection_method': element.metadata.detection_method,
                    'page_number': element.metadata.page_number,
                    'languages': element.metadata.languages,
                    'custom_fields': element.metadata.custom_fields
                }
            
            # Create index entry
            entry = IndexEntry(
                element_id=element.element_id,
                element_type=element.element_type,
                terms=terms,
                text_content=element.text,
                metadata_fields=metadata_fields,
                confidence=element.metadata.confidence if element.metadata else 1.0,
                page_number=element.metadata.page_number if element.metadata else None,
                languages=element.metadata.languages if element.metadata else []
            )
            
            # Add to main index
            self.entries[element.element_id] = entry
            
            # Update term index
            for term in terms:
                self.term_index[term].add(element.element_id)
            
            # Update type index
            self.type_index[element.element_type].add(element.element_id)
            
            # Update page index
            if entry.page_number is not None:
                self.page_index[entry.page_number].add(element.element_id)
            
            # Update confidence ranges
            self._update_confidence_index(element.element_id, entry.confidence)
            
            # Update statistics
            self._update_statistics()
    
    def remove_element(self, element_id: str) -> bool:
        """Remove element from index."""
        with self._lock:
            if element_id not in self.entries:
                return False
            
            entry = self.entries[element_id]
            
            # Remove from term index
            for term in entry.terms:
                self.term_index[term].discard(element_id)
                if not self.term_index[term]:
                    del self.term_index[term]
            
            # Remove from type index
            self.type_index[entry.element_type].discard(element_id)
            if not self.type_index[entry.element_type]:
                del self.type_index[entry.element_type]
            
            # Remove from page index
            if entry.page_number is not None:
                self.page_index[entry.page_number].discard(element_id)
                if not self.page_index[entry.page_number]:
                    del self.page_index[entry.page_number]
            
            # Remove from confidence ranges
            self._remove_from_confidence_index(element_id, entry.confidence)
            
            # Remove main entry
            del self.entries[element_id]
            
            # Update statistics
            self._update_statistics()
            return True
    
    def search_text(self, query: str, fuzzy: bool = False) -> Set[str]:
        """Search for elements by text content."""
        with self._lock:
            if not query:
                return set()
            
            query_terms = self._extract_query_terms(query)
            if not query_terms:
                return set()
            
            # Find matching elements for each term
            matching_sets = []
            for term in query_terms:
                term_matches = set()
                
                if fuzzy and self.enable_fuzzy:
                    # Fuzzy search - check all entries
                    for entry in self.entries.values():
                        if entry.matches_term(term, fuzzy=True):
                            term_matches.add(entry.element_id)
                else:
                    # Exact search using index
                    term_matches = self.term_index.get(term.lower(), set()).copy()
                
                matching_sets.append(term_matches)
            
            # Intersect all term matches (AND operation)
            if matching_sets:
                result = matching_sets[0]
                for match_set in matching_sets[1:]:
                    result = result.intersection(match_set)
                return result
            
            return set()
    
    def search_by_type(self, element_types: Set[ElementType]) -> Set[str]:
        """Search for elements by type."""
        with self._lock:
            result = set()
            for element_type in element_types:
                result.update(self.type_index.get(element_type, set()))
            return result
    
    def search_by_page(self, page_numbers: Set[int]) -> Set[str]:
        """Search for elements by page number."""
        with self._lock:
            result = set()
            for page_num in page_numbers:
                result.update(self.page_index.get(page_num, set()))
            return result
    
    def search_by_confidence(self, min_confidence: float, max_confidence: float) -> Set[str]:
        """Search for elements by confidence range."""
        with self._lock:
            result = set()
            for element_id, entry in self.entries.items():
                if min_confidence <= entry.confidence <= max_confidence:
                    result.add(element_id)
            return result
    
    def get_suggestions(self, partial_query: str, limit: int = 10) -> List[str]:
        """Get search suggestions for partial query."""
        with self._lock:
            if len(partial_query) < self.min_term_length:
                return []
            
            partial_lower = partial_query.lower()
            suggestions = []
            
            # Find terms starting with partial query
            for term in self.term_index:
                if term.startswith(partial_lower):
                    suggestions.append(term)
                    if len(suggestions) >= limit:
                        break
            
            return sorted(suggestions)
    
    def _extract_terms(self, element: Element) -> Set[str]:
        """Extract searchable terms from element."""
        terms = set()
        
        # Extract from text content
        if element.text:
            text_terms = self._tokenize_text(element.text)
            terms.update(text_terms)
        
        # Extract from metadata
        if element.metadata:
            # Add detection method
            if element.metadata.detection_method:
                terms.add(element.metadata.detection_method.lower())
            
            # Add languages
            for lang in element.metadata.languages:
                terms.add(f"lang:{lang.lower()}")
            
            # Add custom fields
            for key, value in element.metadata.custom_fields.items():
                if isinstance(value, str):
                    terms.add(f"{key}:{value.lower()}")
                elif isinstance(value, (int, float)):
                    terms.add(f"{key}:{str(value)}")
        
        # Add element type
        terms.add(f"type:{element.element_type.value.lower()}")
        
        return terms
    
    def _extract_query_terms(self, query: str) -> Set[str]:
        """Extract terms from search query."""
        return set(self._tokenize_text(query))
    
    def _tokenize_text(self, text: str) -> List[str]:
        """Tokenize text into searchable terms."""
        if not text:
            return []
        
        # Basic tokenization
        # Remove special characters and split on whitespace
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        tokens = text.split()
        
        # Filter by length
        tokens = [
            token for token in tokens 
            if self.min_term_length <= len(token) <= self.max_term_length
        ]
        
        # Apply stemming if enabled
        if self.enable_stemming:
            tokens = [self._simple_stem(token) for token in tokens]
        
        return tokens
    
    def _simple_stem(self, word: str) -> str:
        """Simple stemming algorithm."""
        # Very basic stemming - remove common suffixes
        suffixes = ['ing', 'ed', 'er', 's']
        for suffix in suffixes:
            if word.endswith(suffix) and len(word) > len(suffix) + 2:
                return word[:-len(suffix)]
        return word
    
    def _update_confidence_index(self, element_id: str, confidence: float) -> None:
        """Update confidence range index."""
        # Remove from old ranges
        self._remove_from_confidence_index(element_id, confidence)
        
        # Add to appropriate range
        confidence_bucket = int(confidence * 10) / 10.0  # Round to nearest 0.1
        range_key = (confidence_bucket, confidence_bucket + 0.1)
        
        if range_key not in self.confidence_ranges:
            self.confidence_ranges[range_key] = set()
        self.confidence_ranges[range_key].add(element_id)
    
    def _remove_from_confidence_index(self, element_id: str, confidence: float) -> None:
        """Remove element from confidence range index."""
        ranges_to_remove = []
        for range_key, element_ids in self.confidence_ranges.items():
            element_ids.discard(element_id)
            if not element_ids:
                ranges_to_remove.append(range_key)
        
        for range_key in ranges_to_remove:
            del self.confidence_ranges[range_key]
    
    def _update_statistics(self) -> None:
        """Update index statistics."""
        self.statistics.total_elements = len(self.entries)
        self.statistics.total_terms = len(self.term_index)
        self.statistics.last_update = time.time()
        self.statistics.update_count += 1
        
        # Calculate average terms per element
        if self.statistics.total_elements > 0:
            total_terms_in_elements = sum(len(entry.terms) for entry in self.entries.values())
            self.statistics.average_terms_per_element = total_terms_in_elements / self.statistics.total_elements
        
        # Calculate most common terms
        term_counts = [(term, len(element_ids)) for term, element_ids in self.term_index.items()]
        self.statistics.most_common_terms = sorted(term_counts, key=lambda x: x[1], reverse=True)[:10]
    
    def get_element_count(self) -> int:
        """Get total number of indexed elements."""
        return len(self.entries)
    
    def get_term_count(self) -> int:
        """Get total number of indexed terms."""
        return len(self.term_index)
    
    def get_statistics(self) -> IndexStatistics:
        """Get index statistics."""
        return self.statistics
    
    def clear(self) -> None:
        """Clear all index data."""
        with self._lock:
            self.entries.clear()
            self.term_index.clear()
            self.type_index.clear()
            self.page_index.clear()
            self.confidence_ranges.clear()
            self.statistics = IndexStatistics()


class ElementIndexer:
    """Manages search indexing for document elements with real-time updates."""
    
    def __init__(self, state_store: StateStore, strategy: IndexStrategy = IndexStrategy.BALANCED):
        self.state_store = state_store
        self.strategy = strategy
        self.search_index = SearchIndex(strategy)
        
        # Background processing
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="indexer")
        self.update_queue: List[Element] = []
        self.queue_lock = threading.Lock()
        
        # Subscribe to state changes
        self._setup_state_subscription()
        
        # Initial indexing
        self._perform_initial_indexing()
    
    def _setup_state_subscription(self) -> None:
        """Setup subscription to state changes for real-time updates."""
        def on_elements_changed(elements: Dict[str, Element]) -> None:
            self._queue_index_update(elements)
        
        # Subscribe to element changes
        self.state_store.subscribe("elements", on_elements_changed)
    
    def _perform_initial_indexing(self) -> None:
        """Perform initial indexing of all elements."""
        state = self.state_store.get_state()
        elements = state.get('elements', {})
        
        if elements:
            # Index all elements in background
            self.executor.submit(self._index_elements_batch, list(elements.values()))
    
    def _queue_index_update(self, elements: Dict[str, Element]) -> None:
        """Queue elements for index update."""
        with self.queue_lock:
            self.update_queue.extend(elements.values())
        
        # Process queue in background
        self.executor.submit(self._process_update_queue)
    
    def _process_update_queue(self) -> None:
        """Process queued index updates."""
        with self.queue_lock:
            if not self.update_queue:
                return
            
            elements_to_process = self.update_queue.copy()
            self.update_queue.clear()
        
        # Update index
        for element in elements_to_process:
            self.search_index.add_element(element)
    
    def _index_elements_batch(self, elements: List[Element]) -> None:
        """Index a batch of elements."""
        for element in elements:
            self.search_index.add_element(element)
    
    def search(self, query: str, fuzzy: bool = False) -> Set[str]:
        """Search for elements by text."""
        return self.search_index.search_text(query, fuzzy)
    
    def search_by_type(self, element_types: Set[ElementType]) -> Set[str]:
        """Search for elements by type."""
        return self.search_index.search_by_type(element_types)
    
    def search_by_page(self, page_numbers: Set[int]) -> Set[str]:
        """Search for elements by page number."""
        return self.search_index.search_by_page(page_numbers)
    
    def search_by_confidence(self, min_confidence: float, max_confidence: float) -> Set[str]:
        """Search for elements by confidence range."""
        return self.search_index.search_by_confidence(min_confidence, max_confidence)
    
    def get_suggestions(self, partial_query: str, limit: int = 10) -> List[str]:
        """Get search suggestions."""
        return self.search_index.get_suggestions(partial_query, limit)
    
    def add_element(self, element: Element) -> None:
        """Add element to index immediately."""
        self.search_index.add_element(element)
    
    def remove_element(self, element_id: str) -> bool:
        """Remove element from index."""
        return self.search_index.remove_element(element_id)
    
    def get_statistics(self) -> IndexStatistics:
        """Get indexing statistics."""
        return self.search_index.get_statistics()
    
    def shutdown(self) -> None:
        """Shutdown the indexer."""
        self.executor.shutdown(wait=True)