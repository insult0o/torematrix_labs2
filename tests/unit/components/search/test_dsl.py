"""
Unit tests for DSL parser and generator components.
"""

import pytest

from src.torematrix.ui.components.search.dsl import (
    DSLLexer, DSLParser, DSLGenerator, DSLQueryHelper, DSLSyntaxError,
    Token, TokenType
)
from src.torematrix.ui.components.search.filters import (
    FilterSet, FilterGroup, FilterCondition, FilterType, FilterOperator, FilterLogic, FilterValue
)
from src.torematrix.core.models.element import ElementType


class TestDSLLexer:
    """Test DSL lexer functionality."""
    
    @pytest.fixture
    def lexer(self):
        """Create DSL lexer for testing."""
        return DSLLexer()
    
    def test_simple_tokenization(self, lexer):
        """Test tokenizing simple expressions."""
        tokens = lexer.tokenize("type == 'Title'")
        
        token_values = [token.value for token in tokens if token.type != TokenType.EOF]
        assert token_values == ["type", "==", "'", "Title", "'"]
        
        token_types = [token.type for token in tokens if token.type != TokenType.EOF]
        assert TokenType.FIELD in token_types
        assert TokenType.OPERATOR in token_types
        assert TokenType.VALUE in token_types
    
    def test_complex_tokenization(self, lexer):
        """Test tokenizing complex expressions."""
        query = 'confidence > 0.8 AND (type == "Title" OR page BETWEEN 1 AND 5)'
        tokens = lexer.tokenize(query)
        
        # Should have field names, operators, values, logic operators, and parentheses
        token_types = [token.type for token in tokens if token.type != TokenType.EOF]
        
        assert TokenType.FIELD in token_types
        assert TokenType.OPERATOR in token_types
        assert TokenType.VALUE in token_types
        assert TokenType.LOGIC in token_types
        assert TokenType.PARENTHESIS_OPEN in token_types
        assert TokenType.PARENTHESIS_CLOSE in token_types
    
    def test_quoted_strings(self, lexer):
        """Test handling quoted strings."""
        tokens = lexer.tokenize('"quoted string" AND \'single quoted\'')
        
        # Should properly identify quotes and content
        values = [token.value for token in tokens if token.type != TokenType.EOF]
        assert '"' in values
        assert "quoted" in values
        assert "string" in values
        assert "'" in values
        assert "single" in values
        assert "quoted" in values
    
    def test_operators(self, lexer):
        """Test various operators."""
        operators = ["==", "!=", ">=", "<=", ">", "<", "LIKE", "NOT LIKE", "IN", "NOT IN"]
        
        for op in operators:
            tokens = lexer.tokenize(f"field {op} value")
            operator_tokens = [token for token in tokens if token.type == TokenType.OPERATOR]
            assert len(operator_tokens) == 1
            assert operator_tokens[0].value == op
    
    def test_syntax_error(self, lexer):
        """Test syntax error handling."""
        with pytest.raises(DSLSyntaxError):
            lexer.tokenize("field @ value")  # Invalid character @


class TestDSLParser:
    """Test DSL parser functionality."""
    
    @pytest.fixture
    def parser(self):
        """Create DSL parser for testing."""
        return DSLParser()
    
    def test_simple_condition(self, parser):
        """Test parsing simple conditions."""
        filter_set = parser.parse('type == "Title"')
        
        assert filter_set.name == "DSL Query"
        assert len(filter_set.groups) == 1
        
        group = filter_set.groups[0]
        assert len(group.conditions) == 1
        
        condition = group.conditions[0]
        assert condition.filter_type == FilterType.ELEMENT_TYPE
        assert condition.operator == FilterOperator.EQUALS
        assert condition.value.value == "Title"
    
    def test_numeric_condition(self, parser):
        """Test parsing numeric conditions."""
        filter_set = parser.parse('confidence > 0.8')
        
        condition = filter_set.groups[0].conditions[0]
        assert condition.filter_type == FilterType.CONFIDENCE
        assert condition.operator == FilterOperator.GREATER_THAN
        assert condition.value.value == 0.8
        assert condition.value.data_type == "number"
    
    def test_between_condition(self, parser):
        """Test parsing BETWEEN conditions."""
        filter_set = parser.parse('confidence BETWEEN 0.5 AND 0.9')
        
        condition = filter_set.groups[0].conditions[0]
        assert condition.filter_type == FilterType.CONFIDENCE
        assert condition.operator == FilterOperator.BETWEEN
        assert condition.value.value == [0.5, 0.9]
        assert condition.value.data_type == "list"
    
    def test_in_condition(self, parser):
        """Test parsing IN conditions."""
        filter_set = parser.parse('type IN ("Title", "Header")')
        
        condition = filter_set.groups[0].conditions[0]
        assert condition.filter_type == FilterType.ELEMENT_TYPE
        assert condition.operator == FilterOperator.IN
        assert condition.value.value == ["Title", "Header"]
        assert condition.value.data_type == "list"
    
    def test_null_condition(self, parser):
        """Test parsing NULL conditions."""
        filter_set = parser.parse('page IS NOT NULL')
        
        condition = filter_set.groups[0].conditions[0]
        assert condition.filter_type == FilterType.PAGE_NUMBER
        assert condition.operator == FilterOperator.IS_NOT_NULL
        assert condition.value.value is None
    
    def test_and_logic(self, parser):
        """Test parsing AND logic."""
        filter_set = parser.parse('confidence > 0.8 AND type == "Title"')
        
        # Should create one group with two conditions (AND logic)
        assert len(filter_set.groups) == 1
        group = filter_set.groups[0]
        assert len(group.conditions) == 2
        assert group.logic == FilterLogic.AND
    
    def test_or_logic(self, parser):
        """Test parsing OR logic."""
        filter_set = parser.parse('type == "Title" OR type == "Header"')
        
        # Should create separate groups for OR conditions
        assert len(filter_set.groups) >= 1
    
    def test_not_logic(self, parser):
        """Test parsing NOT logic."""
        filter_set = parser.parse('NOT (confidence < 0.5)')
        
        # Should create group with NOT logic
        assert len(filter_set.groups) == 1
        group = filter_set.groups[0]
        assert group.logic == FilterLogic.NOT
    
    def test_parentheses(self, parser):
        """Test parsing expressions with parentheses."""
        filter_set = parser.parse('(confidence > 0.8 AND type == "Title") OR page == 1')
        
        # Complex grouping should be handled correctly
        assert len(filter_set.groups) >= 1
    
    def test_custom_field(self, parser):
        """Test parsing custom field conditions."""
        filter_set = parser.parse('custom_field == "value"')
        
        condition = filter_set.groups[0].conditions[0]
        assert condition.filter_type == FilterType.CUSTOM_FIELD
        assert condition.field_name == "custom_field"
        assert condition.value.value == "value"
    
    def test_syntax_error_handling(self, parser):
        """Test syntax error handling."""
        with pytest.raises(DSLSyntaxError):
            parser.parse('type ==')  # Missing value
        
        with pytest.raises(DSLSyntaxError):
            parser.parse('(type == "Title"')  # Unmatched parenthesis
    
    def test_fuzzy_search(self, parser):
        """Test parsing fuzzy search."""
        filter_set = parser.parse('text ~= "machine learning"')
        
        condition = filter_set.groups[0].conditions[0]
        assert condition.filter_type == FilterType.TEXT_CONTENT
        assert condition.operator == FilterOperator.FUZZY
        assert condition.value.value == "machine learning"


class TestDSLGenerator:
    """Test DSL generator functionality."""
    
    @pytest.fixture
    def generator(self):
        """Create DSL generator for testing."""
        return DSLGenerator()
    
    def test_simple_condition_generation(self, generator):
        """Test generating simple conditions."""
        filter_set = FilterSet(name="Test")
        group = FilterGroup()
        group.add_condition(FilterCondition(
            filter_type=FilterType.ELEMENT_TYPE,
            operator=FilterOperator.EQUALS,
            value=FilterValue(ElementType.TITLE.value, "string")
        ))
        filter_set.add_group(group)
        
        query = generator.generate(filter_set)
        assert "type ==" in query
        assert "Title" in query
    
    def test_numeric_condition_generation(self, generator):
        """Test generating numeric conditions."""
        filter_set = FilterSet(name="Test")
        group = FilterGroup()
        group.add_condition(FilterCondition(
            filter_type=FilterType.CONFIDENCE,
            operator=FilterOperator.GREATER_THAN,
            value=FilterValue(0.8, "number")
        ))
        filter_set.add_group(group)
        
        query = generator.generate(filter_set)
        assert "confidence >" in query
        assert "0.8" in query
    
    def test_between_condition_generation(self, generator):
        """Test generating BETWEEN conditions."""
        filter_set = FilterSet(name="Test")
        group = FilterGroup()
        group.add_condition(FilterCondition(
            filter_type=FilterType.CONFIDENCE,
            operator=FilterOperator.BETWEEN,
            value=FilterValue([0.5, 0.9], "list")
        ))
        filter_set.add_group(group)
        
        query = generator.generate(filter_set)
        assert "BETWEEN" in query
        assert "0.5" in query
        assert "0.9" in query
        assert "AND" in query
    
    def test_in_condition_generation(self, generator):
        """Test generating IN conditions."""
        filter_set = FilterSet(name="Test")
        group = FilterGroup()
        group.add_condition(FilterCondition(
            filter_type=FilterType.ELEMENT_TYPE,
            operator=FilterOperator.IN,
            value=FilterValue(["Title", "Header"], "list")
        ))
        filter_set.add_group(group)
        
        query = generator.generate(filter_set)
        assert "IN" in query
        assert "Title" in query
        assert "Header" in query
        assert "(" in query and ")" in query
    
    def test_null_condition_generation(self, generator):
        """Test generating NULL conditions."""
        filter_set = FilterSet(name="Test")
        group = FilterGroup()
        group.add_condition(FilterCondition(
            filter_type=FilterType.PAGE_NUMBER,
            operator=FilterOperator.IS_NOT_NULL,
            value=FilterValue(None)
        ))
        filter_set.add_group(group)
        
        query = generator.generate(filter_set)
        assert "IS NOT NULL" in query
    
    def test_multiple_conditions_generation(self, generator):
        """Test generating multiple conditions."""
        filter_set = FilterSet(name="Test")
        group = FilterGroup(logic=FilterLogic.AND)
        
        group.add_condition(FilterCondition(
            filter_type=FilterType.CONFIDENCE,
            operator=FilterOperator.GREATER_THAN,
            value=FilterValue(0.8, "number")
        ))
        
        group.add_condition(FilterCondition(
            filter_type=FilterType.ELEMENT_TYPE,
            operator=FilterOperator.EQUALS,
            value=FilterValue(ElementType.TITLE.value, "string")
        ))
        
        filter_set.add_group(group)
        
        query = generator.generate(filter_set)
        assert "confidence >" in query
        assert "type ==" in query
        assert "AND" in query
    
    def test_string_quoting(self, generator):
        """Test proper string quoting."""
        filter_set = FilterSet(name="Test")
        group = FilterGroup()
        group.add_condition(FilterCondition(
            filter_type=FilterType.TEXT_CONTENT,
            operator=FilterOperator.CONTAINS,
            value=FilterValue("machine learning", "string")
        ))
        filter_set.add_group(group)
        
        query = generator.generate(filter_set)
        # String with space should be quoted
        assert '"machine learning"' in query


class TestDSLQueryHelper:
    """Test DSL query helper functionality."""
    
    @pytest.fixture
    def helper(self):
        """Create DSL query helper for testing."""
        return DSLQueryHelper()
    
    def test_validate_valid_query(self, helper):
        """Test validating valid queries."""
        valid, error = helper.validate_query('type == "Title"')
        assert valid == True
        assert error is None
        
        valid, error = helper.validate_query('confidence > 0.8 AND page == 1')
        assert valid == True
        assert error is None
    
    def test_validate_invalid_query(self, helper):
        """Test validating invalid queries."""
        valid, error = helper.validate_query('type ==')  # Missing value
        assert valid == False
        assert error is not None
        
        valid, error = helper.validate_query('(type == "Title"')  # Unmatched parenthesis
        assert valid == False
        assert error is not None
    
    def test_get_suggestions(self, helper):
        """Test getting auto-completion suggestions."""
        suggestions = helper.get_suggestions("con")
        assert "confidence" in suggestions
        
        suggestions = helper.get_suggestions("type ")
        # Should suggest operators
        assert any("==" in s for s in suggestions)
        assert any("!=" in s for s in suggestions)
    
    def test_format_query(self, helper):
        """Test query formatting."""
        # Should format and normalize query
        formatted = helper.format_query('type=="Title"AND confidence>0.8')
        assert formatted != 'type=="Title"AND confidence>0.8'
        # Should be more readable
    
    def test_get_examples(self, helper):
        """Test getting example queries."""
        examples = helper.get_examples()
        assert len(examples) > 0
        
        # Each example should have query and description
        for query, description in examples:
            assert isinstance(query, str)
            assert isinstance(description, str)
            assert len(query) > 0
            assert len(description) > 0


class TestDSLIntegration:
    """Test DSL integration with filter system."""
    
    @pytest.fixture
    def parser(self):
        return DSLParser()
    
    @pytest.fixture
    def generator(self):
        return DSLGenerator()
    
    def test_round_trip_conversion(self, parser, generator):
        """Test parsing and then generating should produce equivalent results."""
        original_query = 'confidence > 0.8 AND type == "Title"'
        
        # Parse to FilterSet
        filter_set = parser.parse(original_query)
        
        # Generate back to DSL
        generated_query = generator.generate(filter_set)
        
        # Parse again to compare
        filter_set2 = parser.parse(generated_query)
        
        # Should have same structure
        assert len(filter_set.groups) == len(filter_set2.groups)
        
        if filter_set.groups:
            group1 = filter_set.groups[0]
            group2 = filter_set2.groups[0]
            assert len(group1.conditions) == len(group2.conditions)
    
    def test_complex_query_parsing(self, parser):
        """Test parsing complex real-world queries."""
        queries = [
            'confidence > 0.8',
            'type IN ("Title", "Header")',
            'page BETWEEN 1 AND 10',
            'confidence > 0.9 AND (type == "Title" OR type == "Header")',
            'NOT (confidence < 0.5)',
            'text LIKE "machine learning"',
            'method ~= "ml" AND confidence > 0.8'
        ]
        
        for query in queries:
            filter_set = parser.parse(query)
            assert len(filter_set.groups) > 0
            assert all(len(group.conditions) > 0 for group in filter_set.groups)
    
    def test_field_mapping(self, parser):
        """Test field name mapping."""
        field_tests = [
            ('type', FilterType.ELEMENT_TYPE),
            ('element_type', FilterType.ELEMENT_TYPE),
            ('text', FilterType.TEXT_CONTENT),
            ('content', FilterType.TEXT_CONTENT),
            ('confidence', FilterType.CONFIDENCE),
            ('conf', FilterType.CONFIDENCE),
            ('page', FilterType.PAGE_NUMBER),
            ('method', FilterType.DETECTION_METHOD),
            ('language', FilterType.LANGUAGE),
        ]
        
        for field_name, expected_type in field_tests:
            filter_set = parser.parse(f'{field_name} == "test"')
            condition = filter_set.groups[0].conditions[0]
            assert condition.filter_type == expected_type