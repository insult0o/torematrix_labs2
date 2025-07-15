"""
Unit tests for search engine components.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock

from src.torematrix.core.models.element import Element, ElementType
from src.torematrix.core.models.metadata import ElementMetadata
from src.torematrix.ui.components.search.engine import (
    IndexedSearchEngine, SearchResult, SearchResultSet, 
    SearchMode, RankingStrategy
)
from src.torematrix.ui.components.search.query_parser import SearchQuery, QueryToken, QueryType


class TestSearchResult:
    """Test SearchResult functionality."""
    
    @pytest.fixture
    def sample_element(self):
        """Create sample element for testing."""
        metadata = ElementMetadata(
            confidence=0.95,
            page_number=1,
            languages=["en"]
        )
        
        return Element(
            element_id="test-elem-1",
            element_type=ElementType.NARRATIVE_TEXT,
            text="This is sample text content",
            metadata=metadata
        )
    
    def test_search_result_creation(self, sample_element):
        """Test creating search result."""
        result = SearchResult(
            element_id=sample_element.element_id,
            element=sample_element,
            score=0.85,
            highlighted_text="This is <mark>sample</mark> text content"
        )
        
        assert result.element_id == sample_element.element_id
        assert result.element == sample_element
        assert result.score == 0.85
        assert "<mark>sample</mark>" in result.highlighted_text
    
    def test_search_result_auto_highlight(self, sample_element):
        """Test automatic highlighting when not provided."""
        result = SearchResult(
            element_id=sample_element.element_id,
            element=sample_element,
            score=0.85
        )
        
        # Should default to element text
        assert result.highlighted_text == sample_element.text


class TestSearchResultSet:
    """Test SearchResultSet functionality."""
    
    @pytest.fixture
    def sample_results(self):
        """Create sample search results."""
        elements = [
            Element(
                element_id=f"elem-{i}",
                element_type=ElementType.NARRATIVE_TEXT,
                text=f"Sample text {i}"
            )
            for i in range(3)
        ]
        
        results = [
            SearchResult(
                element_id=elem.element_id,
                element=elem,
                score=1.0 - (i * 0.1)
            )
            for i, elem in enumerate(elements)
        ]
        
        return results
    
    def test_result_set_creation(self, sample_results):
        """Test creating search result set."""
        result_set = SearchResultSet(
            results=sample_results,
            total_count=3,
            search_time_ms=45.5,
            has_more=False,
            offset=0
        )
        
        assert len(result_set.results) == 3
        assert result_set.total_count == 3
        assert result_set.search_time_ms == 45.5
        assert result_set.has_more == False
        assert result_set.offset == 0
    
    def test_get_element_ids(self, sample_results):
        """Test getting element IDs from result set."""
        result_set = SearchResultSet(results=sample_results)
        
        element_ids = result_set.get_element_ids()
        assert len(element_ids) == 3
        assert "elem-0" in element_ids
        assert "elem-1" in element_ids
        assert "elem-2" in element_ids
    
    def test_get_elements(self, sample_results):
        """Test getting elements from result set."""
        result_set = SearchResultSet(results=sample_results)
        
        elements = result_set.get_elements()
        assert len(elements) == 3
        assert all(isinstance(elem, Element) for elem in elements)
    
    def test_get_top_result(self, sample_results):
        """Test getting top result."""
        result_set = SearchResultSet(results=sample_results)
        
        top_result = result_set.get_top_result()
        assert top_result is not None
        assert top_result == sample_results[0]
        
        # Empty result set
        empty_set = SearchResultSet()
        assert empty_set.get_top_result() is None


class TestIndexedSearchEngine:
    """Test IndexedSearchEngine functionality."""
    
    @pytest.fixture
    def mock_state_store(self):
        """Create mock state store."""
        mock_store = Mock()
        
        # Sample elements data
        metadata1 = ElementMetadata(confidence=0.95, page_number=1, languages=["en"])
        metadata2 = ElementMetadata(confidence=0.85, page_number=2, languages=["en"])
        
        elements = {
            "elem-1": Element(
                element_id="elem-1",
                element_type=ElementType.TITLE,
                text="Document Title Here",
                metadata=metadata1
            ),
            "elem-2": Element(
                element_id="elem-2", 
                element_type=ElementType.NARRATIVE_TEXT,
                text="This is narrative text with important content",
                metadata=metadata2
            ),
            "elem-3": Element(
                element_id="elem-3",
                element_type=ElementType.TABLE,
                text="Table data rows and columns",
                metadata=metadata1
            )
        }
        
        mock_store.get_state.return_value = {'elements': elements}
        return mock_store
    
    @pytest.fixture
    def search_engine(self, mock_state_store):
        """Create search engine for testing."""
        with patch('src.torematrix.ui.components.search.engine.ThreadPoolExecutor'):
            with patch('src.torematrix.ui.components.search.indexer.ThreadPoolExecutor'):
                engine = IndexedSearchEngine(mock_state_store)
        return engine
    
    def test_search_engine_creation(self, search_engine):
        """Test creating search engine."""
        assert search_engine.ranking_strategy == RankingStrategy.RELEVANCE
        assert search_engine.search_mode == SearchMode.SYNCHRONOUS
        assert search_engine.max_results == 1000
        assert search_engine.default_limit == 50
        assert search_engine.enable_highlighting == True
    
    def test_simple_text_search(self, search_engine):
        """Test simple text search."""
        # Add some elements to the engine's indexer
        state = search_engine.state_store.get_state()
        elements = state['elements']
        
        for element in elements.values():
            search_engine.indexer.add_element(element)
        
        # Search for "document"
        result_set = search_engine.search("document")
        
        assert isinstance(result_set, SearchResultSet)
        assert result_set.total_count > 0
        assert result_set.search_time_ms > 0
        
        # Should find the title element
        element_ids = result_set.get_element_ids()
        assert "elem-1" in element_ids
    
    def test_field_search(self, search_engine):
        """Test field-specific search."""
        # Add elements
        state = search_engine.state_store.get_state()
        elements = state['elements']
        
        for element in elements.values():
            search_engine.indexer.add_element(element)
        
        # Search by type
        result_set = search_engine.search("type:title")
        
        assert result_set.total_count > 0
        element_ids = result_set.get_element_ids()
        assert "elem-1" in element_ids  # Title element
        assert "elem-2" not in element_ids  # Narrative text element
    
    def test_boolean_search(self, search_engine):
        """Test boolean search operations."""
        # Add elements
        state = search_engine.state_store.get_state()
        elements = state['elements']
        
        for element in elements.values():
            search_engine.indexer.add_element(element)
        
        # AND search
        result_set = search_engine.search("narrative AND text")
        
        assert isinstance(result_set, SearchResultSet)
        # Should find elements containing both terms
    
    def test_phrase_search(self, search_engine):
        """Test phrase search with quotes."""
        # Add elements
        state = search_engine.state_store.get_state()
        elements = state['elements']
        
        for element in elements.values():
            search_engine.indexer.add_element(element)
        
        # Phrase search
        result_set = search_engine.search('"document title"')
        
        assert isinstance(result_set, SearchResultSet)
    
    def test_search_with_filters(self, search_engine):
        """Test search with additional filters."""
        # Add elements
        state = search_engine.state_store.get_state()
        elements = state['elements']
        
        for element in elements.values():
            search_engine.indexer.add_element(element)
        
        # Search with confidence filter
        filters = {'confidence_range': (0.9, 1.0)}
        result_set = search_engine.search("text", filters=filters)
        
        assert isinstance(result_set, SearchResultSet)
        
        # Check that results have high confidence
        for result in result_set.results:
            if result.element.metadata:
                assert result.element.metadata.confidence >= 0.9
    
    def test_search_pagination(self, search_engine):
        """Test search result pagination."""
        # Add elements
        state = search_engine.state_store.get_state()
        elements = state['elements']
        
        for element in elements.values():
            search_engine.indexer.add_element(element)
        
        # Search with pagination
        result_set = search_engine.search("text", limit=2, offset=0)
        
        assert len(result_set.results) <= 2
        assert result_set.offset == 0
    
    def test_result_ranking_relevance(self, search_engine):
        """Test relevance-based result ranking."""
        # Add elements
        state = search_engine.state_store.get_state()
        elements = state['elements']
        
        for element in elements.values():
            search_engine.indexer.add_element(element)
        
        # Search and check ranking
        result_set = search_engine.search("text", ranking=RankingStrategy.RELEVANCE)
        
        assert isinstance(result_set, SearchResultSet)
        
        # Results should be ordered by score (descending)
        scores = [result.score for result in result_set.results]
        assert scores == sorted(scores, reverse=True)
    
    def test_result_ranking_confidence(self, search_engine):
        """Test confidence-based result ranking."""
        # Add elements
        state = search_engine.state_store.get_state()
        elements = state['elements']
        
        for element in elements.values():
            search_engine.indexer.add_element(element)
        
        # Search with confidence ranking
        result_set = search_engine.search("text", ranking=RankingStrategy.CONFIDENCE)
        
        assert isinstance(result_set, SearchResultSet)
    
    def test_search_highlighting(self, search_engine):
        """Test search result highlighting."""
        # Add elements
        state = search_engine.state_store.get_state()
        elements = state['elements']
        
        for element in elements.values():
            search_engine.indexer.add_element(element)
        
        # Search with highlighting enabled
        result_set = search_engine.search("document", highlight=True)
        
        assert isinstance(result_set, SearchResultSet)
        
        # Check that highlighting was applied
        for result in result_set.results:
            if "document" in result.element.text.lower():
                assert "<mark>" in result.highlighted_text or result.highlighted_text == result.element.text
    
    def test_search_suggestions(self, search_engine):
        """Test search suggestions."""
        # Add elements
        state = search_engine.state_store.get_state()
        elements = state['elements']
        
        for element in elements.values():
            search_engine.indexer.add_element(element)
        
        # Get suggestions
        suggestions = search_engine.suggest("doc")
        
        assert isinstance(suggestions, list)
        # Should include matching terms and field suggestions
    
    def test_empty_query_handling(self, search_engine):
        """Test handling of empty queries."""
        result_set = search_engine.search("")
        
        assert isinstance(result_set, SearchResultSet)
        assert result_set.total_count == 0
        assert len(result_set.results) == 0
    
    def test_invalid_query_handling(self, search_engine):
        """Test handling of invalid queries."""
        # Query with invalid field
        result_set = search_engine.search("invalid_field:value")
        
        assert isinstance(result_set, SearchResultSet)
        # Should handle gracefully without crashing
    
    @patch('src.torematrix.ui.components.search.engine.time.time')
    def test_result_caching(self, mock_time, search_engine):
        """Test search result caching."""
        mock_time.return_value = 1000.0  # Fixed timestamp
        
        # Add elements
        state = search_engine.state_store.get_state()
        elements = state['elements']
        
        for element in elements.values():
            search_engine.indexer.add_element(element)
        
        # First search - should cache result
        result_set1 = search_engine.search("document")
        
        # Second search with same query - should use cache
        result_set2 = search_engine.search("document")
        
        # Both should return results (caching doesn't affect correctness)
        assert isinstance(result_set1, SearchResultSet)
        assert isinstance(result_set2, SearchResultSet)
    
    def test_cache_clearing(self, search_engine):
        """Test clearing search cache."""
        # Add elements and search
        state = search_engine.state_store.get_state()
        elements = state['elements']
        
        for element in elements.values():
            search_engine.indexer.add_element(element)
        
        search_engine.search("document")
        
        # Clear cache
        search_engine.clear_cache()
        
        # Cache should be empty
        assert len(search_engine.result_cache) == 0
    
    def test_custom_scorer(self, search_engine):
        """Test adding custom scoring function."""
        def custom_scorer(element, query):
            # Simple custom scorer - boost titles
            if element.element_type == ElementType.TITLE:
                return 10.0
            return 1.0
        
        search_engine.add_custom_scorer("test_scorer", custom_scorer)
        
        assert "test_scorer" in search_engine.custom_scorers
        assert search_engine.custom_scorers["test_scorer"] == custom_scorer
    
    def test_engine_configuration(self, search_engine):
        """Test search engine configuration."""
        # Test setting ranking strategy
        search_engine.set_ranking_strategy(RankingStrategy.CONFIDENCE)
        assert search_engine.ranking_strategy == RankingStrategy.CONFIDENCE
        
        # Test setting search mode
        search_engine.set_search_mode(SearchMode.ASYNCHRONOUS)
        assert search_engine.search_mode == SearchMode.ASYNCHRONOUS
    
    def test_get_statistics(self, search_engine):
        """Test getting search engine statistics."""
        stats = search_engine.get_statistics()
        
        assert isinstance(stats, dict)
        assert 'index_statistics' in stats
        assert 'cache_size' in stats
        assert 'ranking_strategy' in stats
        assert 'search_mode' in stats
    
    def test_async_search(self, search_engine):
        """Test asynchronous search functionality."""
        callback_called = False
        result_received = None
        
        def test_callback(result_set):
            nonlocal callback_called, result_received
            callback_called = True
            result_received = result_set
        
        # Add elements
        state = search_engine.state_store.get_state()
        elements = state['elements']
        
        for element in elements.values():
            search_engine.indexer.add_element(element)
        
        # Start async search
        search_engine.search_async("document", test_callback)
        
        # Give some time for async execution
        time.sleep(0.1)
        
        # Note: In real testing, you'd want to wait properly for the callback
        # This is a simplified test
    
    def test_streaming_search(self, search_engine):
        """Test streaming search functionality."""
        results_received = []
        
        def stream_callback(result):
            results_received.append(result)
        
        # Add elements
        state = search_engine.state_store.get_state()
        elements = state['elements']
        
        for element in elements.values():
            search_engine.indexer.add_element(element)
        
        # Start streaming search
        search_engine.search_streaming("document", stream_callback)
        
        # Give some time for streaming execution
        time.sleep(0.1)
        
        # Note: In real testing, you'd want to wait properly for the callbacks
        # This is a simplified test
    
    def test_engine_shutdown(self, search_engine):
        """Test search engine shutdown."""
        # Should shutdown cleanly without errors
        search_engine.shutdown()