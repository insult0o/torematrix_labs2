"""
Unit tests for search indexer components.
"""

import pytest
import time
from unittest.mock import Mock, patch

from src.torematrix.core.models.element import Element, ElementType
from src.torematrix.core.models.metadata import ElementMetadata
from src.torematrix.core.models.coordinates import Coordinates
from src.torematrix.ui.components.search.indexer import (
    SearchIndex, ElementIndexer, IndexStrategy, IndexEntry, IndexStatistics
)


class TestIndexEntry:
    """Test IndexEntry functionality."""
    
    def test_index_entry_creation(self):
        """Test creating index entry."""
        entry = IndexEntry(
            element_id="test-1",
            element_type=ElementType.NARRATIVE_TEXT,
            terms={"hello", "world"},
            text_content="Hello world"
        )
        
        assert entry.element_id == "test-1"
        assert entry.element_type == ElementType.NARRATIVE_TEXT
        assert "hello" in entry.terms
        assert "world" in entry.terms
        assert entry.text_content == "Hello world"
    
    def test_matches_term_exact(self):
        """Test exact term matching."""
        entry = IndexEntry(
            element_id="test-1",
            element_type=ElementType.NARRATIVE_TEXT,
            terms={"hello", "world", "test"}
        )
        
        assert entry.matches_term("hello")
        assert entry.matches_term("world")
        assert not entry.matches_term("goodbye")
    
    def test_matches_term_fuzzy(self):
        """Test fuzzy term matching."""
        entry = IndexEntry(
            element_id="test-1", 
            element_type=ElementType.NARRATIVE_TEXT,
            terms={"hello", "world"}
        )
        
        # Should match with small edit distance
        assert entry.matches_term("helo", fuzzy=True)  # Missing 'l'
        assert entry.matches_term("wrold", fuzzy=True)  # Swapped letters
        
        # Should not match with large edit distance
        assert not entry.matches_term("xyz", fuzzy=True)


class TestSearchIndex:
    """Test SearchIndex functionality."""
    
    @pytest.fixture
    def search_index(self):
        """Create search index for testing."""
        return SearchIndex(IndexStrategy.BALANCED)
    
    @pytest.fixture
    def sample_elements(self):
        """Create sample elements for testing."""
        metadata1 = ElementMetadata(
            confidence=0.95,
            page_number=1,
            languages=["en"],
            detection_method="ml"
        )
        
        metadata2 = ElementMetadata(
            confidence=0.85,
            page_number=2,
            languages=["en"],
            detection_method="rule"
        )
        
        elements = [
            Element(
                element_id="elem-1",
                element_type=ElementType.TITLE,
                text="Document Title Here",
                metadata=metadata1
            ),
            Element(
                element_id="elem-2", 
                element_type=ElementType.NARRATIVE_TEXT,
                text="This is narrative text with important content",
                metadata=metadata2
            ),
            Element(
                element_id="elem-3",
                element_type=ElementType.TABLE,
                text="Table data rows and columns",
                metadata=metadata1
            )
        ]
        
        return elements
    
    def test_add_element(self, search_index, sample_elements):
        """Test adding elements to index."""
        element = sample_elements[0]
        search_index.add_element(element)
        
        assert element.element_id in search_index.entries
        assert search_index.get_element_count() == 1
        
        # Check term index
        assert len(search_index.term_index) > 0
        assert "document" in search_index.term_index
        assert element.element_id in search_index.term_index["document"]
    
    def test_remove_element(self, search_index, sample_elements):
        """Test removing elements from index."""
        element = sample_elements[0]
        search_index.add_element(element)
        
        assert search_index.remove_element(element.element_id)
        assert element.element_id not in search_index.entries
        assert search_index.get_element_count() == 0
        
        # Check term index cleaned up
        if "document" in search_index.term_index:
            assert element.element_id not in search_index.term_index["document"]
    
    def test_search_text_simple(self, search_index, sample_elements):
        """Test simple text search."""
        for element in sample_elements:
            search_index.add_element(element)
        
        # Search for "document"
        results = search_index.search_text("document")
        assert "elem-1" in results  # Title contains "Document"
        
        # Search for "narrative"
        results = search_index.search_text("narrative")
        assert "elem-2" in results
        
        # Search for non-existent term
        results = search_index.search_text("nonexistent")
        assert len(results) == 0
    
    def test_search_text_fuzzy(self, search_index, sample_elements):
        """Test fuzzy text search."""
        for element in sample_elements:
            search_index.add_element(element)
        
        # Fuzzy search should find close matches
        results = search_index.search_text("documnt", fuzzy=True)  # Missing 'e'
        assert len(results) > 0
    
    def test_search_by_type(self, search_index, sample_elements):
        """Test searching by element type."""
        for element in sample_elements:
            search_index.add_element(element)
        
        # Search for titles
        results = search_index.search_by_type({ElementType.TITLE})
        assert "elem-1" in results
        assert "elem-2" not in results
        
        # Search for multiple types
        results = search_index.search_by_type({ElementType.TITLE, ElementType.TABLE})
        assert "elem-1" in results
        assert "elem-3" in results
        assert "elem-2" not in results
    
    def test_search_by_page(self, search_index, sample_elements):
        """Test searching by page number."""
        for element in sample_elements:
            search_index.add_element(element)
        
        # Search page 1
        results = search_index.search_by_page({1})
        assert "elem-1" in results
        assert "elem-3" in results
        assert "elem-2" not in results
        
        # Search page 2
        results = search_index.search_by_page({2})
        assert "elem-2" in results
    
    def test_search_by_confidence(self, search_index, sample_elements):
        """Test searching by confidence range."""
        for element in sample_elements:
            search_index.add_element(element)
        
        # High confidence elements
        results = search_index.search_by_confidence(0.9, 1.0)
        assert "elem-1" in results
        assert "elem-3" in results
        assert "elem-2" not in results
        
        # Lower confidence elements  
        results = search_index.search_by_confidence(0.8, 0.9)
        assert "elem-2" in results
    
    def test_get_suggestions(self, search_index, sample_elements):
        """Test search suggestions."""
        for element in sample_elements:
            search_index.add_element(element)
        
        # Get suggestions for partial term
        suggestions = search_index.get_suggestions("doc")
        assert "document" in suggestions
        
        # Get suggestions for non-matching partial
        suggestions = search_index.get_suggestions("xyz")
        assert len(suggestions) == 0
    
    def test_statistics_update(self, search_index, sample_elements):
        """Test statistics tracking."""
        initial_stats = search_index.get_statistics()
        assert initial_stats.total_elements == 0
        assert initial_stats.total_terms == 0
        
        # Add elements
        for element in sample_elements:
            search_index.add_element(element)
        
        stats = search_index.get_statistics()
        assert stats.total_elements == 3
        assert stats.total_terms > 0
        assert stats.update_count > 0
        assert stats.average_terms_per_element > 0
    
    def test_clear_index(self, search_index, sample_elements):
        """Test clearing the index."""
        for element in sample_elements:
            search_index.add_element(element)
        
        assert search_index.get_element_count() > 0
        
        search_index.clear()
        
        assert search_index.get_element_count() == 0
        assert len(search_index.term_index) == 0
        assert len(search_index.type_index) == 0


class TestElementIndexer:
    """Test ElementIndexer functionality."""
    
    @pytest.fixture
    def mock_state_store(self):
        """Create mock state store."""
        mock_store = Mock()
        mock_store.get_state.return_value = {'elements': {}}
        return mock_store
    
    @pytest.fixture
    def element_indexer(self, mock_state_store):
        """Create element indexer for testing."""
        with patch('src.torematrix.ui.components.search.indexer.ThreadPoolExecutor'):
            indexer = ElementIndexer(mock_state_store, IndexStrategy.SPEED)
        return indexer
    
    def test_indexer_creation(self, element_indexer):
        """Test creating element indexer."""
        assert element_indexer.strategy == IndexStrategy.SPEED
        assert element_indexer.search_index is not None
    
    def test_add_element_to_indexer(self, element_indexer):
        """Test adding element to indexer."""
        element = Element(
            element_id="test-elem",
            element_type=ElementType.NARRATIVE_TEXT,
            text="Test content for indexing"
        )
        
        element_indexer.add_element(element)
        
        # Verify element was added to index
        assert element.element_id in element_indexer.search_index.entries
    
    def test_remove_element_from_indexer(self, element_indexer):
        """Test removing element from indexer."""
        element = Element(
            element_id="test-elem",
            element_type=ElementType.NARRATIVE_TEXT,
            text="Test content for indexing"
        )
        
        element_indexer.add_element(element)
        assert element_indexer.remove_element(element.element_id)
        assert element.element_id not in element_indexer.search_index.entries
    
    def test_search_through_indexer(self, element_indexer):
        """Test searching through indexer."""
        element = Element(
            element_id="test-elem",
            element_type=ElementType.NARRATIVE_TEXT,
            text="Test content for searching"
        )
        
        element_indexer.add_element(element)
        
        # Search for text
        results = element_indexer.search("content")
        assert element.element_id in results
        
        # Search by type
        results = element_indexer.search_by_type({ElementType.NARRATIVE_TEXT})
        assert element.element_id in results
    
    def test_get_suggestions_from_indexer(self, element_indexer):
        """Test getting suggestions from indexer."""
        element = Element(
            element_id="test-elem",
            element_type=ElementType.NARRATIVE_TEXT,
            text="Test content for suggestions"
        )
        
        element_indexer.add_element(element)
        
        suggestions = element_indexer.get_suggestions("con")
        assert "content" in suggestions
    
    def test_get_statistics_from_indexer(self, element_indexer):
        """Test getting statistics from indexer."""
        stats = element_indexer.get_statistics()
        assert isinstance(stats, IndexStatistics)
        assert stats.total_elements >= 0


class TestIndexStrategies:
    """Test different indexing strategies."""
    
    def test_speed_strategy(self):
        """Test speed-optimized strategy."""
        index = SearchIndex(IndexStrategy.SPEED)
        assert index.strategy == IndexStrategy.SPEED
        assert index.max_term_length == 50
        assert not index.enable_stemming
        assert index.enable_fuzzy
    
    def test_memory_strategy(self):
        """Test memory-optimized strategy.""" 
        index = SearchIndex(IndexStrategy.MEMORY)
        assert index.strategy == IndexStrategy.MEMORY
        assert index.max_term_length == 20
        assert index.enable_stemming
        assert not index.enable_fuzzy
    
    def test_realtime_strategy(self):
        """Test real-time optimized strategy."""
        index = SearchIndex(IndexStrategy.REALTIME)
        assert index.strategy == IndexStrategy.REALTIME
        assert index.max_term_length == 30
        assert not index.enable_stemming
        assert not index.enable_fuzzy
    
    def test_balanced_strategy(self):
        """Test balanced strategy."""
        index = SearchIndex(IndexStrategy.BALANCED)
        assert index.strategy == IndexStrategy.BALANCED
        assert index.max_term_length == 30
        assert index.enable_stemming
        assert index.enable_fuzzy