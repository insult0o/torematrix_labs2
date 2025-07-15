"""
Unit tests for query parser components.
"""

import pytest

from src.torematrix.ui.components.search.query_parser import (
    QueryParser, QueryToken, SearchQuery, QueryType, BooleanOperator, QueryBuilder
)


class TestQueryToken:
    """Test QueryToken functionality."""
    
    def test_simple_token_creation(self):
        """Test creating simple query token."""
        token = QueryToken(type=QueryType.SIMPLE, value="hello")
        assert token.type == QueryType.SIMPLE
        assert token.value == "hello"
        assert token.field is None
        assert token.modifier is None
        assert token.boost == 1.0
    
    def test_field_token_creation(self):
        """Test creating field-specific token."""
        token = QueryToken(type=QueryType.FIELD, value="text", field="type")
        assert token.type == QueryType.FIELD
        assert token.value == "text"
        assert token.field == "type"
    
    def test_token_string_representation(self):
        """Test token string conversion."""
        # Simple token
        token = QueryToken(type=QueryType.SIMPLE, value="hello")
        assert str(token) == "hello"
        
        # Field token
        token = QueryToken(type=QueryType.FIELD, value="text", field="type")
        assert str(token) == "type:text"
        
        # Token with modifier
        token = QueryToken(type=QueryType.FUZZY, value="hello", modifier="~2")
        assert str(token) == "hello~2"
        
        # Token with boost
        token = QueryToken(type=QueryType.SIMPLE, value="hello", boost=2.0)
        assert str(token) == "hello^2.0"


class TestSearchQuery:
    """Test SearchQuery functionality."""
    
    def test_empty_query(self):
        """Test empty search query."""
        query = SearchQuery()
        assert len(query.tokens) == 0
        assert len(query.boolean_operators) == 0
        assert query.is_simple() == False
        assert query.has_field_searches() == False
        assert query.has_boolean_logic() == False
    
    def test_simple_query(self):
        """Test simple single-term query."""
        query = SearchQuery()
        query.tokens.append(QueryToken(type=QueryType.SIMPLE, value="hello"))
        
        assert query.is_simple() == True
        assert query.has_field_searches() == False
        assert query.has_boolean_logic() == False
        assert query.get_text_terms() == ["hello"]
    
    def test_field_search_query(self):
        """Test query with field searches."""
        query = SearchQuery()
        query.tokens.append(QueryToken(type=QueryType.FIELD, value="text", field="type"))
        
        assert query.has_field_searches() == True
        field_searches = query.get_field_searches()
        assert "type" in field_searches
        assert "text" in field_searches["type"]
    
    def test_boolean_query(self):
        """Test query with boolean operators."""
        query = SearchQuery()
        query.tokens.extend([
            QueryToken(type=QueryType.SIMPLE, value="hello"),
            QueryToken(type=QueryType.SIMPLE, value="world")
        ])
        query.boolean_operators.append(BooleanOperator.AND)
        
        assert query.has_boolean_logic() == True
        assert query.get_text_terms() == ["hello", "world"]
    
    def test_query_string_representation(self):
        """Test query string conversion."""
        query = SearchQuery()
        query.tokens.extend([
            QueryToken(type=QueryType.SIMPLE, value="hello"),
            QueryToken(type=QueryType.SIMPLE, value="world")
        ])
        query.boolean_operators.append(BooleanOperator.AND)
        
        query_str = str(query)
        assert "hello" in query_str
        assert "world" in query_str
        assert "AND" in query_str


class TestQueryParser:
    """Test QueryParser functionality."""
    
    @pytest.fixture
    def parser(self):
        """Create query parser for testing."""
        return QueryParser()
    
    def test_parse_simple_query(self, parser):
        """Test parsing simple text query."""
        query = parser.parse("hello world")
        
        assert len(query.tokens) == 2
        assert query.tokens[0].type == QueryType.SIMPLE
        assert query.tokens[0].value == "hello"
        assert query.tokens[1].type == QueryType.SIMPLE
        assert query.tokens[1].value == "world"
    
    def test_parse_field_search(self, parser):
        """Test parsing field-specific search."""
        query = parser.parse("type:text confidence:0.9")
        
        assert len(query.tokens) == 2
        
        type_token = query.tokens[0]
        assert type_token.type == QueryType.FIELD
        assert type_token.field == "type"
        assert type_token.value == "text"
        
        conf_token = query.tokens[1]
        assert conf_token.type == QueryType.FIELD
        assert conf_token.field == "confidence"
        assert conf_token.value == "0.9"
    
    def test_parse_phrase_search(self, parser):
        """Test parsing phrase search with quotes."""
        query = parser.parse('"hello world" test')
        
        assert len(query.tokens) == 2
        
        phrase_token = query.tokens[0]
        assert phrase_token.type == QueryType.PHRASE
        assert phrase_token.value == "hello world"
        
        simple_token = query.tokens[1]
        assert simple_token.type == QueryType.SIMPLE
        assert simple_token.value == "test"
    
    def test_parse_boolean_operators(self, parser):
        """Test parsing boolean operators."""
        query = parser.parse("hello AND world OR test")
        
        assert len(query.boolean_operators) == 2
        assert query.boolean_operators[0] == BooleanOperator.AND
        assert query.boolean_operators[1] == BooleanOperator.OR
    
    def test_parse_range_search(self, parser):
        """Test parsing range searches."""
        query = parser.parse("confidence:[0.5 TO 0.9]")
        
        assert "confidence_range" in query.filters
        assert query.filters["confidence_range"] == (0.5, 0.9)
    
    def test_parse_wildcard_search(self, parser):
        """Test parsing wildcard searches."""
        query = parser.parse("test* hello")
        
        wildcard_token = None
        for token in query.tokens:
            if token.type == QueryType.WILDCARD:
                wildcard_token = token
                break
        
        assert wildcard_token is not None
        assert wildcard_token.value == "test"
        assert wildcard_token.modifier == "*"
    
    def test_parse_fuzzy_search(self, parser):
        """Test parsing fuzzy searches."""
        query = parser.parse("hello~2 world")
        
        fuzzy_token = None
        for token in query.tokens:
            if token.type == QueryType.FUZZY:
                fuzzy_token = token
                break
        
        assert fuzzy_token is not None
        assert fuzzy_token.value == "hello"
        assert fuzzy_token.modifier == "~2"
        assert query.fuzzy_enabled == True
    
    def test_parse_proximity_search(self, parser):
        """Test parsing proximity searches."""
        query = parser.parse('"hello world"~5')
        
        proximity_token = None
        for token in query.tokens:
            if token.type == QueryType.PROXIMITY:
                proximity_token = token
                break
        
        assert proximity_token is not None
        assert proximity_token.value == "hello world"
        assert proximity_token.modifier == "~5"
    
    def test_parse_empty_query(self, parser):
        """Test parsing empty query."""
        query = parser.parse("")
        assert len(query.tokens) == 0
        
        query = parser.parse("   ")
        assert len(query.tokens) == 0
    
    def test_parse_complex_query(self, parser):
        """Test parsing complex multi-part query."""
        query_str = 'type:text "exact phrase" hello AND world~2 confidence:[0.8 TO 1.0]'
        query = parser.parse(query_str)
        
        # Should have multiple tokens
        assert len(query.tokens) > 2
        
        # Should have field search
        assert query.has_field_searches()
        
        # Should have boolean operators
        assert query.has_boolean_logic()
        
        # Should have range filter
        assert "confidence_range" in query.filters
        
        # Should have fuzzy enabled
        assert query.fuzzy_enabled == True
    
    def test_validate_query(self, parser):
        """Test query validation."""
        # Valid simple query
        query = parser.parse("hello world")
        errors = parser.validate_query(query)
        assert len(errors) == 0
        
        # Valid field query
        query = parser.parse("type:text")
        errors = parser.validate_query(query)
        assert len(errors) == 0
        
        # Empty query
        query = SearchQuery()
        errors = parser.validate_query(query)
        assert "empty" in errors[0].lower()
    
    def test_suggest_corrections(self, parser):
        """Test query correction suggestions."""
        # Test unmatched quotes
        suggestions = parser.suggest_corrections('hello "world')
        assert any("quote" in s.lower() for s in suggestions)
        
        # Test unmatched parentheses
        suggestions = parser.suggest_corrections('hello (world')
        assert any("parenthes" in s.lower() for s in suggestions)
        
        # Test field typos
        suggestions = parser.suggest_corrections('typ:text')
        assert any("type" in s for s in suggestions)
    
    def test_get_field_suggestions(self, parser):
        """Test getting field suggestions."""
        suggestions = parser.get_field_suggestions()
        assert "type" in suggestions
        assert "text" in suggestions
        assert "confidence" in suggestions
        assert "page" in suggestions
    
    def test_parse_natural_language(self, parser):
        """Test natural language query parsing."""
        # "find all X elements"
        query = parser.parse_natural_language("find all text elements")
        field_tokens = [t for t in query.tokens if t.type == QueryType.FIELD]
        assert len(field_tokens) > 0
        assert any(t.field == "type" and t.value == "text" for t in field_tokens)
        
        # "with confidence above X"
        query = parser.parse_natural_language("with confidence above 0.8")
        assert "confidence_range" in query.filters
        assert query.filters["confidence_range"][0] == 0.8
        
        # "on page X"
        query = parser.parse_natural_language("on page 5")
        page_tokens = [t for t in query.tokens if t.field == "page"]
        assert len(page_tokens) > 0
        assert page_tokens[0].value == "5"


class TestQueryBuilder:
    """Test QueryBuilder functionality."""
    
    def test_build_simple_query(self):
        """Test building simple query."""
        builder = QueryBuilder()
        query = builder.text("hello").build()
        
        assert len(query.tokens) == 1
        assert query.tokens[0].type == QueryType.SIMPLE
        assert query.tokens[0].value == "hello"
    
    def test_build_field_query(self):
        """Test building field query."""
        builder = QueryBuilder()
        query = builder.field("type", "text").build()
        
        assert len(query.tokens) == 1
        assert query.tokens[0].type == QueryType.FIELD
        assert query.tokens[0].field == "type"
        assert query.tokens[0].value == "text"
    
    def test_build_phrase_query(self):
        """Test building phrase query."""
        builder = QueryBuilder()
        query = builder.phrase("hello world").build()
        
        assert len(query.tokens) == 1
        assert query.tokens[0].type == QueryType.PHRASE
        assert query.tokens[0].value == "hello world"
    
    def test_build_boolean_query(self):
        """Test building boolean query."""
        builder = QueryBuilder()
        query = (builder.text("hello")
                       .and_operator()
                       .text("world")
                       .build())
        
        assert len(query.tokens) == 2
        assert len(query.boolean_operators) == 1
        assert query.boolean_operators[0] == BooleanOperator.AND
    
    def test_build_wildcard_query(self):
        """Test building wildcard query."""
        builder = QueryBuilder()
        query = builder.wildcard("test").build()
        
        assert len(query.tokens) == 1
        assert query.tokens[0].type == QueryType.WILDCARD
        assert query.tokens[0].value == "test"
        assert query.tokens[0].modifier == "*"
    
    def test_build_fuzzy_query(self):
        """Test building fuzzy query."""
        builder = QueryBuilder()
        query = builder.fuzzy("hello", 2).build()
        
        assert len(query.tokens) == 1
        assert query.tokens[0].type == QueryType.FUZZY
        assert query.tokens[0].value == "hello"
        assert query.tokens[0].modifier == "~2"
        assert query.fuzzy_enabled == True
    
    def test_build_range_filter(self):
        """Test building range filter."""
        builder = QueryBuilder()
        query = builder.range_filter("confidence", 0.5, 0.9).build()
        
        assert "confidence_range" in query.filters
        assert query.filters["confidence_range"] == (0.5, 0.9)
    
    def test_build_with_boost(self):
        """Test building query with boost."""
        builder = QueryBuilder()
        query = builder.text("hello").boost(2.0).build()
        
        assert len(query.tokens) == 1
        assert query.tokens[0].boost == 2.0
    
    def test_build_with_sort(self):
        """Test building query with sort."""
        builder = QueryBuilder()
        query = builder.text("hello").sort_by("confidence", True).build()
        
        assert len(query.sort_fields) == 1
        assert query.sort_fields[0] == ("confidence", True)
    
    def test_build_with_pagination(self):
        """Test building query with pagination."""
        builder = QueryBuilder()
        query = builder.text("hello").limit(20).offset(10).build()
        
        assert query.limit == 20
        assert query.offset == 10
    
    def test_build_case_sensitive(self):
        """Test building case-sensitive query."""
        builder = QueryBuilder()
        query = builder.text("hello").case_sensitive(True).build()
        
        assert query.case_sensitive == True
    
    def test_builder_reset(self):
        """Test resetting builder."""
        builder = QueryBuilder()
        query1 = builder.text("hello").build()
        
        builder.reset()
        query2 = builder.text("world").build()
        
        assert len(query1.tokens) == 1
        assert query1.tokens[0].value == "hello"
        
        assert len(query2.tokens) == 1
        assert query2.tokens[0].value == "world"
    
    def test_build_complex_query(self):
        """Test building complex query with multiple features."""
        builder = QueryBuilder()
        query = (builder.field("type", "text")
                       .and_operator()
                       .phrase("hello world")
                       .or_operator()
                       .fuzzy("test", 2)
                       .range_filter("confidence", 0.8, 1.0)
                       .sort_by("confidence", True)
                       .limit(50)
                       .case_sensitive(False)
                       .build())
        
        # Check tokens
        assert len(query.tokens) == 3
        assert query.tokens[0].type == QueryType.FIELD
        assert query.tokens[1].type == QueryType.PHRASE
        assert query.tokens[2].type == QueryType.FUZZY
        
        # Check operators
        assert len(query.boolean_operators) == 2
        assert query.boolean_operators[0] == BooleanOperator.AND
        assert query.boolean_operators[1] == BooleanOperator.OR
        
        # Check filters and options
        assert "confidence_range" in query.filters
        assert len(query.sort_fields) == 1
        assert query.limit == 50
        assert query.case_sensitive == False
        assert query.fuzzy_enabled == True