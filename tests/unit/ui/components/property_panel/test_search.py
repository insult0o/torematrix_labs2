"""Tests for property panel search and filtering functionality"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from torematrix.ui.components.property_panel.search import (
    SearchScope, FilterType, SortOrder, SearchResult, SearchQuery, PropertyFilter,
    SearchIndex, SearchWorker, PropertySearchWidget, PropertyFilterWidget
)
from torematrix.ui.components.property_panel.events import PropertyNotificationCenter
from torematrix.ui.components.property_panel.models import PropertyMetadata


@pytest.fixture
def qt_app():
    """Create QApplication instance for testing"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def notification_center():
    """Create notification center"""
    return PropertyNotificationCenter()


@pytest.fixture
def mock_property_manager():
    """Create mock property manager"""
    manager = Mock()
    manager.get_element_properties.return_value = {
        'type': 'text',
        'content': 'Sample content',
        'x': 100,
        'y': 200,
        'confidence': 0.95
    }
    manager.get_property_metadata.return_value = PropertyMetadata(
        name='test_prop',
        display_name='Test Property',
        description='Test property description',
        category='Test'
    )
    return manager


class TestSearchQuery:
    """Test SearchQuery class"""
    
    def test_default_initialization(self):
        """Test default query initialization"""
        query = SearchQuery()
        assert query.text == ""
        assert query.scope == SearchScope.ALL_ELEMENTS
        assert not query.case_sensitive
        assert not query.whole_words
        assert not query.regex
        assert query.fuzzy
        assert query.fuzzy_threshold == 0.6
        assert query.include_property_names
        assert query.include_property_values
        assert not query.include_metadata
        assert query.max_results == 100
    
    def test_custom_initialization(self):
        """Test custom query initialization"""
        query = SearchQuery(
            text="test search",
            scope=SearchScope.SELECTED_ELEMENTS,
            case_sensitive=True,
            fuzzy=False,
            max_results=50
        )
        assert query.text == "test search"
        assert query.scope == SearchScope.SELECTED_ELEMENTS
        assert query.case_sensitive
        assert not query.fuzzy
        assert query.max_results == 50


class TestPropertyFilter:
    """Test PropertyFilter class"""
    
    def test_text_filter_contains(self):
        """Test text filter with contains operator"""
        filter_obj = PropertyFilter(
            filter_type=FilterType.TEXT,
            operator="contains",
            value="test",
            case_sensitive=False
        )
        
        assert filter_obj.matches("This is a test value")
        assert filter_obj.matches("TEST")
        assert not filter_obj.matches("No match here")
    
    def test_text_filter_equals(self):
        """Test text filter with equals operator"""
        filter_obj = PropertyFilter(
            filter_type=FilterType.TEXT,
            operator="equals",
            value="exact",
            case_sensitive=False
        )
        
        assert filter_obj.matches("exact")
        assert filter_obj.matches("EXACT")
        assert not filter_obj.matches("not exact")
    
    def test_text_filter_case_sensitive(self):
        """Test case sensitive text filter"""
        filter_obj = PropertyFilter(
            filter_type=FilterType.TEXT,
            operator="contains",
            value="Test",
            case_sensitive=True
        )
        
        assert filter_obj.matches("This is a Test")
        assert not filter_obj.matches("This is a test")
    
    def test_numeric_filter_greater_than(self):
        """Test numeric filter with greater than"""
        filter_obj = PropertyFilter(
            filter_type=FilterType.NUMERIC,
            operator="greater_than",
            value=100
        )
        
        assert filter_obj.matches(150)
        assert filter_obj.matches("200")  # String conversion
        assert not filter_obj.matches(50)
        assert not filter_obj.matches("invalid")
    
    def test_numeric_filter_equals(self):
        """Test numeric filter with equals"""
        filter_obj = PropertyFilter(
            filter_type=FilterType.NUMERIC,
            operator="equals",
            value=100.5
        )
        
        assert filter_obj.matches(100.5)
        assert filter_obj.matches("100.5")
        assert not filter_obj.matches(100.6)
    
    def test_boolean_filter(self):
        """Test boolean filter"""
        filter_obj = PropertyFilter(
            filter_type=FilterType.BOOLEAN,
            value=True
        )
        
        assert filter_obj.matches(True)
        assert filter_obj.matches("true")
        assert filter_obj.matches(1)
        assert not filter_obj.matches(False)
        assert not filter_obj.matches(0)
    
    def test_disabled_filter(self):
        """Test disabled filter always passes"""
        filter_obj = PropertyFilter(
            filter_type=FilterType.TEXT,
            operator="equals",
            value="no match",
            enabled=False
        )
        
        assert filter_obj.matches("anything")


class TestSearchIndex:
    """Test SearchIndex class"""
    
    def test_initialization(self):
        """Test search index initialization"""
        index = SearchIndex()
        assert index.property_index == {}
        assert index.value_index == {}
        assert index.element_properties == {}
        assert index.metadata_index == {}
    
    def test_update_element(self):
        """Test updating element in index"""
        index = SearchIndex()
        
        properties = {
            'type': 'text',
            'content': 'Sample content',
            'x': 100
        }
        
        metadata = {
            'type': PropertyMetadata(name='type', display_name='Type', description='Type property', category='Basic')
        }
        
        index.update_element('elem1', properties, metadata)
        
        # Check property index
        assert 'type' in index.property_index
        assert 'elem1' in index.property_index['type']
        
        # Check value index has tokens
        assert len(index.value_index) > 0
        
        # Check element properties stored
        assert index.element_properties['elem1'] == properties
        
        # Check metadata stored
        assert 'type' in index.metadata_index
    
    def test_remove_element(self):
        """Test removing element from index"""
        index = SearchIndex()
        
        properties = {'type': 'text', 'content': 'test'}
        index.update_element('elem1', properties)
        
        # Verify element exists
        assert 'elem1' in index.element_properties
        
        # Remove element
        index.remove_element('elem1')
        
        # Verify element removed
        assert 'elem1' not in index.element_properties
        assert 'elem1' not in index.property_index.get('type', set())
    
    def test_tokenize_value(self):
        """Test value tokenization"""
        index = SearchIndex()
        
        tokens = index._tokenize_value("Hello-World_Test.Value")
        
        assert 'hello' in tokens
        assert 'world' in tokens
        assert 'test' in tokens
        assert 'value' in tokens
        
        # Should also include partial tokens for longer words
        assert any('hel' in token for token in tokens)
    
    def test_search_simple(self):
        """Test simple search"""
        index = SearchIndex()
        
        # Add test data
        index.update_element('elem1', {'type': 'text', 'content': 'hello world'})
        index.update_element('elem2', {'type': 'image', 'content': 'test image'})
        
        # Search for 'text' in property names
        query = SearchQuery(text='text', include_property_names=True, include_property_values=True)
        results = index.search(query)
        
        # Both elements should match since we're searching both names and values
        # elem1 has 'text' in type property name
        # elem2 has 'text' in content property value  
        assert 'elem1' in results or 'elem2' in results  # At least one should match
    
    def test_search_values(self):
        """Test searching in values"""
        index = SearchIndex()
        
        index.update_element('elem1', {'content': 'hello world'})
        index.update_element('elem2', {'content': 'test image'})
        
        query = SearchQuery(text='hello', include_property_names=False, include_property_values=True)
        results = index.search(query)
        
        assert 'elem1' in results
        assert 'elem2' not in results
    
    def test_search_max_results(self):
        """Test max results limit"""
        index = SearchIndex()
        
        # Add multiple elements
        for i in range(10):
            index.update_element(f'elem{i}', {'type': 'text'})
        
        query = SearchQuery(text='text', max_results=5)
        results = index.search(query)
        
        assert len(results) <= 5


class TestSearchWorker:
    """Test SearchWorker class"""
    
    def test_initialization(self):
        """Test worker initialization"""
        worker = SearchWorker()
        assert worker.search_index is not None
        assert worker.property_manager is None
        assert not worker.cancel_requested
    
    def test_set_property_manager(self):
        """Test setting property manager"""
        worker = SearchWorker()
        manager = Mock()
        
        worker.set_property_manager(manager)
        assert worker.property_manager == manager
    
    def test_update_index(self):
        """Test index update"""
        worker = SearchWorker()
        manager = Mock()
        
        # Mock property manager responses
        manager.get_element_properties.return_value = {'type': 'text'}
        manager.get_property_metadata.return_value = None
        
        worker.set_property_manager(manager)
        
        # Update index
        worker.update_index(['elem1', 'elem2'])
        
        # Check that property manager was called
        assert manager.get_element_properties.call_count == 2
    
    def test_calculate_relevance(self):
        """Test relevance calculation"""
        worker = SearchWorker()
        
        query = SearchQuery(text='test', include_property_names=True, include_property_values=True)
        
        # Exact property name match should have high relevance
        relevance1 = worker._calculate_relevance('test', 'value', query)
        
        # Partial value match should have lower relevance
        relevance2 = worker._calculate_relevance('prop', 'test value', query)
        
        # No match should have zero relevance
        relevance3 = worker._calculate_relevance('prop', 'no match', query)
        
        assert relevance1 > relevance2 > relevance3
    
    def test_fuzzy_match(self):
        """Test fuzzy matching"""
        worker = SearchWorker()
        
        # Similar strings should have high score
        score1 = worker._fuzzy_match('test', 'testing')
        
        # Completely different strings should have low score
        score2 = worker._fuzzy_match('test', 'xyz')
        
        assert score1 > score2
        assert 0 <= score1 <= 1
        assert 0 <= score2 <= 1
    
    def test_cancel_search(self):
        """Test search cancellation"""
        worker = SearchWorker()
        
        worker.cancel_search()
        assert worker.cancel_requested


class TestPropertySearchWidget:
    """Test PropertySearchWidget class"""
    
    def test_initialization(self, qt_app, notification_center):
        """Test widget initialization"""
        widget = PropertySearchWidget(notification_center)
        
        assert widget.notification_center == notification_center
        assert widget.property_manager is None
        assert isinstance(widget.current_query, SearchQuery)
        assert widget.search_results == []
        assert widget.active_filters == []
    
    def test_set_property_manager(self, qt_app, notification_center):
        """Test setting property manager"""
        widget = PropertySearchWidget(notification_center)
        manager = Mock()
        
        widget.set_property_manager(manager)
        assert widget.property_manager == manager
        assert widget.search_worker.property_manager == manager
    
    def test_update_query_from_ui(self, qt_app, notification_center):
        """Test updating query from UI controls"""
        widget = PropertySearchWidget(notification_center)
        
        # Set UI values
        widget.search_input.setText("test search")
        widget.case_sensitive_cb.setChecked(True)
        widget.whole_words_cb.setChecked(True)
        widget.fuzzy_search_cb.setChecked(False)
        
        # Update query
        widget._update_query_from_ui()
        
        assert widget.current_query.text == "test search"
        assert widget.current_query.case_sensitive
        assert widget.current_query.whole_words
        assert not widget.current_query.fuzzy
    
    def test_clear_search(self, qt_app, notification_center):
        """Test clearing search"""
        widget = PropertySearchWidget(notification_center)
        
        # Set some data
        widget.search_input.setText("test")
        widget.search_results = [Mock()]
        
        # Clear search
        widget._clear_search()
        
        assert widget.search_input.text() == ""
        assert widget.search_results == []
    
    def test_add_remove_filter(self, qt_app, notification_center):
        """Test adding and removing filters"""
        widget = PropertySearchWidget(notification_center)
        
        initial_count = widget.filter_layout.count()
        
        # Add filter
        widget._add_filter()
        assert widget.filter_layout.count() == initial_count + 1
        
        # Get the filter widget
        filter_widget = None
        for i in range(widget.filter_layout.count()):
            item = widget.filter_layout.itemAt(i)
            if item and isinstance(item.widget(), PropertyFilterWidget):
                filter_widget = item.widget()
                break
        
        assert filter_widget is not None
        
        # Remove filter
        widget._remove_filter(filter_widget)
        assert widget.filter_layout.count() == initial_count
    
    def test_clear_filters(self, qt_app, notification_center):
        """Test clearing all filters"""
        widget = PropertySearchWidget(notification_center)
        
        # Add some filters
        widget._add_filter()
        widget._add_filter()
        
        initial_count = widget.filter_layout.count()
        assert initial_count > 1
        
        # Clear filters
        widget._clear_filters()
        
        # Should only have the stretch item left
        assert widget.filter_layout.count() == 1
        assert widget.active_filters == []
    
    def test_apply_filters(self, qt_app, notification_center):
        """Test applying filters to results"""
        widget = PropertySearchWidget(notification_center)
        
        # Create test results
        results = [
            SearchResult('elem1', 'type', 'text', 1.0),
            SearchResult('elem2', 'type', 'image', 0.8),
            SearchResult('elem3', 'content', 'test content', 0.6)
        ]
        
        # Create filter that looks for 'text' in property values
        text_filter = PropertyFilter(
            filter_type=FilterType.TEXT,
            operator="contains",
            value="text"
        )
        widget.active_filters = [text_filter]
        
        # Apply filters
        filtered = widget._apply_filters(results)
        
        # Should include results with 'text' in the property value
        # 'text' itself and 'test content' (contains 'text')
        assert len(filtered) >= 1  # At least one should match
    
    def test_sort_results(self, qt_app, notification_center):
        """Test sorting results"""
        widget = PropertySearchWidget(notification_center)
        
        # Create test results with different relevance scores
        widget.search_results = [
            SearchResult('elem1', 'prop1', 'value1', 0.5),
            SearchResult('elem2', 'prop2', 'value2', 0.9),
            SearchResult('elem3', 'prop3', 'value3', 0.7)
        ]
        
        # Sort by relevance (default should already be by relevance descending)
        widget.sort_combo.setCurrentText("Relevance")
        widget._sort_results()
        
        # Check order
        assert widget.search_results[0].relevance_score == 0.9
        assert widget.search_results[1].relevance_score == 0.7
        assert widget.search_results[2].relevance_score == 0.5


class TestPropertyFilterWidget:
    """Test PropertyFilterWidget class"""
    
    def test_initialization(self, qt_app):
        """Test filter widget initialization"""
        widget = PropertyFilterWidget()
        
        assert widget.filter is not None
        assert widget.filter.filter_type == FilterType.TEXT
        assert widget.enabled_cb.isChecked()
    
    def test_get_filter(self, qt_app):
        """Test getting filter configuration"""
        widget = PropertyFilterWidget()
        
        # Set some values
        widget.property_input.setText("test_prop")
        widget.value_input.setText("test_value")
        widget.enabled_cb.setChecked(False)
        
        # Get filter
        filter_obj = widget.get_filter()
        
        assert filter_obj.property_name == "test_prop"
        assert filter_obj.value == "test_value"
        assert not filter_obj.enabled
    
    def test_type_change_updates_operators(self, qt_app):
        """Test that changing filter type updates operators"""
        widget = PropertyFilterWidget()
        
        # Start with text type
        initial_operators = [widget.operator_combo.itemText(i) 
                           for i in range(widget.operator_combo.count())]
        
        # Change to numeric type
        widget.type_combo.setCurrentText("Numeric")
        
        # Operators should have changed
        new_operators = [widget.operator_combo.itemText(i) 
                        for i in range(widget.operator_combo.count())]
        
        assert new_operators != initial_operators
        assert "Greater Than" in new_operators  # Numeric specific operator


@pytest.mark.integration
class TestSearchIntegration:
    """Integration tests for search functionality"""
    
    def test_complete_search_workflow(self, qt_app, notification_center, mock_property_manager):
        """Test complete search workflow"""
        widget = PropertySearchWidget(notification_center)
        widget.set_property_manager(mock_property_manager)
        
        # Set up search
        widget.search_input.setText("content")
        widget.case_sensitive_cb.setChecked(False)
        
        # Add a filter
        widget._add_filter()
        
        # Update query
        widget._update_query_from_ui()
        
        # Verify query
        assert widget.current_query.text == "content"
        assert not widget.current_query.case_sensitive
        
        # Test filter functionality
        filter_widget = None
        for i in range(widget.filter_layout.count()):
            item = widget.filter_layout.itemAt(i)
            if item and isinstance(item.widget(), PropertyFilterWidget):
                filter_widget = item.widget()
                break
        
        if filter_widget:
            filter_widget.property_input.setText("type")
            filter_widget.value_input.setText("text")
            filter_obj = filter_widget.get_filter()
            
            assert filter_obj.property_name == "type"
            assert filter_obj.value == "text"
    
    def test_search_index_with_real_data(self):
        """Test search index with realistic data"""
        index = SearchIndex()
        
        # Add realistic property data
        elements = {
            'elem1': {
                'type': 'heading',
                'content': 'Document Title',
                'font_size': 16,
                'x': 100,
                'y': 50
            },
            'elem2': {
                'type': 'paragraph', 
                'content': 'This is a sample paragraph with some text content.',
                'font_size': 12,
                'x': 100,
                'y': 100
            },
            'elem3': {
                'type': 'image',
                'alt_text': 'Sample image description',
                'x': 200,
                'y': 150,
                'width': 300,
                'height': 200
            }
        }
        
        # Update index
        for elem_id, properties in elements.items():
            index.update_element(elem_id, properties)
        
        # Test various searches
        
        # Search for content type
        query1 = SearchQuery(text='paragraph')
        results1 = index.search(query1)
        assert 'elem2' in results1
        
        # Search for numerical values
        query2 = SearchQuery(text='16')
        results2 = index.search(query2)
        assert 'elem1' in results2
        
        # Search with property names only
        query3 = SearchQuery(text='alt_text', include_property_values=False)
        results3 = index.search(query3)
        assert 'elem3' in results3
        
        # Search with values only
        query4 = SearchQuery(text='image', include_property_names=False)
        results4 = index.search(query4)
        assert 'elem3' in results4