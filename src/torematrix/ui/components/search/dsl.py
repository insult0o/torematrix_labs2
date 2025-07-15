"""
Domain-Specific Language (DSL) Parser for Search Queries

Provides a powerful text-based query language for advanced users with
natural language support and complex expression parsing.
"""

import re
import json
from typing import Dict, List, Set, Optional, Any, Union, Tuple
from dataclasses import dataclass
from enum import Enum

from .filters import (
    FilterSet, FilterGroup, FilterCondition, FilterType, 
    FilterOperator, FilterLogic, FilterValue
)
from ....core.models.element import ElementType


class TokenType(Enum):
    """Types of tokens in the DSL."""
    FIELD = "field"
    OPERATOR = "operator"
    VALUE = "value"
    LOGIC = "logic"
    PARENTHESIS_OPEN = "paren_open"
    PARENTHESIS_CLOSE = "paren_close"
    BRACKET_OPEN = "bracket_open"
    BRACKET_CLOSE = "bracket_close"
    COMMA = "comma"
    QUOTE = "quote"
    WHITESPACE = "whitespace"
    EOF = "eof"


@dataclass
class Token:
    """A token in the DSL."""
    type: TokenType
    value: str
    position: int
    
    def __str__(self) -> str:
        return f"{self.type.value}:{self.value}"


class DSLSyntaxError(Exception):
    """Exception raised for DSL syntax errors."""
    
    def __init__(self, message: str, position: int = -1, token: Optional[Token] = None):
        self.message = message
        self.position = position
        self.token = token
        super().__init__(self._format_message())
    
    def _format_message(self) -> str:
        """Format the error message with position information."""
        msg = self.message
        if self.position >= 0:
            msg += f" at position {self.position}"
        if self.token:
            msg += f" (token: {self.token})"
        return msg


class DSLLexer:
    """Lexical analyzer for the DSL."""
    
    def __init__(self):
        # Token patterns (order matters for proper matching)
        self.patterns = [
            (TokenType.LOGIC, r'\b(AND|OR|NOT)\b'),
            (TokenType.OPERATOR, r'(>=|<=|!=|==|>|<|~=|IN|NOT\s+IN|BETWEEN|LIKE|NOT\s+LIKE|IS\s+NULL|IS\s+NOT\s+NULL)'),
            (TokenType.FIELD, r'[a-zA-Z_][a-zA-Z0-9_]*'),
            (TokenType.PARENTHESIS_OPEN, r'\('),
            (TokenType.PARENTHESIS_CLOSE, r'\)'),
            (TokenType.BRACKET_OPEN, r'\['),
            (TokenType.BRACKET_CLOSE, r'\]'),
            (TokenType.COMMA, r','),
            (TokenType.QUOTE, r'["\']'),
            (TokenType.VALUE, r'[^\s\(\)\[\],]+'),
            (TokenType.WHITESPACE, r'\s+'),
        ]
        
        # Compile patterns
        self.compiled_patterns = [
            (token_type, re.compile(pattern, re.IGNORECASE))
            for token_type, pattern in self.patterns
        ]
    
    def tokenize(self, text: str) -> List[Token]:
        """Tokenize input text into tokens."""
        tokens = []
        position = 0
        
        while position < len(text):
            matched = False
            
            for token_type, pattern in self.compiled_patterns:
                match = pattern.match(text, position)
                if match:
                    value = match.group(0)
                    
                    # Skip whitespace tokens
                    if token_type != TokenType.WHITESPACE:
                        tokens.append(Token(token_type, value, position))
                    
                    position = match.end()
                    matched = True
                    break
            
            if not matched:
                raise DSLSyntaxError(f"Invalid character '{text[position]}'", position)
        
        # Add EOF token
        tokens.append(Token(TokenType.EOF, "", position))
        return tokens


class DSLParser:
    """Parser for the DSL that converts tokens to filter sets."""
    
    def __init__(self):
        self.lexer = DSLLexer()
        self.tokens: List[Token] = []
        self.current_token_index = 0
        
        # Field mappings
        self.field_mappings = {
            'type': FilterType.ELEMENT_TYPE,
            'element_type': FilterType.ELEMENT_TYPE,
            'text': FilterType.TEXT_CONTENT,
            'content': FilterType.TEXT_CONTENT,
            'confidence': FilterType.CONFIDENCE,
            'conf': FilterType.CONFIDENCE,
            'page': FilterType.PAGE_NUMBER,
            'page_number': FilterType.PAGE_NUMBER,
            'method': FilterType.DETECTION_METHOD,
            'detection_method': FilterType.DETECTION_METHOD,
            'language': FilterType.LANGUAGE,
            'lang': FilterType.LANGUAGE,
        }
        
        # Operator mappings
        self.operator_mappings = {
            '==': FilterOperator.EQUALS,
            '=': FilterOperator.EQUALS,
            '!=': FilterOperator.NOT_EQUALS,
            '<>': FilterOperator.NOT_EQUALS,
            '>': FilterOperator.GREATER_THAN,
            '<': FilterOperator.LESS_THAN,
            '>=': FilterOperator.GREATER_EQUAL,
            '<=': FilterOperator.LESS_EQUAL,
            'LIKE': FilterOperator.CONTAINS,
            'NOT LIKE': FilterOperator.NOT_CONTAINS,
            '~=': FilterOperator.FUZZY,
            'BETWEEN': FilterOperator.BETWEEN,
            'IN': FilterOperator.IN,
            'NOT IN': FilterOperator.NOT_IN,
            'IS NULL': FilterOperator.IS_NULL,
            'IS NOT NULL': FilterOperator.IS_NOT_NULL,
        }
    
    def parse(self, query: str) -> FilterSet:
        """Parse a DSL query string into a FilterSet."""
        try:
            self.tokens = self.lexer.tokenize(query)
            self.current_token_index = 0
            
            filter_set = FilterSet(name="DSL Query")
            
            # Parse the expression
            expression = self.parse_expression()
            
            # Convert expression to filter groups
            groups = self._expression_to_groups(expression)
            filter_set.groups = groups
            
            return filter_set
            
        except Exception as e:
            if isinstance(e, DSLSyntaxError):
                raise e
            else:
                raise DSLSyntaxError(f"Parse error: {str(e)}")
    
    def current_token(self) -> Token:
        """Get the current token."""
        if self.current_token_index < len(self.tokens):
            return self.tokens[self.current_token_index]
        return self.tokens[-1]  # EOF token
    
    def consume_token(self, expected_type: Optional[TokenType] = None) -> Token:
        """Consume and return the current token."""
        token = self.current_token()
        
        if expected_type and token.type != expected_type:
            raise DSLSyntaxError(
                f"Expected {expected_type.value}, got {token.type.value}",
                token.position, token
            )
        
        self.current_token_index += 1
        return token
    
    def peek_token(self, offset: int = 1) -> Token:
        """Peek at a future token."""
        index = self.current_token_index + offset
        if index < len(self.tokens):
            return self.tokens[index]
        return self.tokens[-1]  # EOF token
    
    def parse_expression(self) -> Dict[str, Any]:
        """Parse a logical expression."""
        return self.parse_or_expression()
    
    def parse_or_expression(self) -> Dict[str, Any]:
        """Parse OR expressions (lowest precedence)."""
        left = self.parse_and_expression()
        
        while (self.current_token().type == TokenType.LOGIC and 
               self.current_token().value.upper() == 'OR'):
            self.consume_token()  # consume OR
            right = self.parse_and_expression()
            left = {
                'type': 'binary_op',
                'operator': 'OR',
                'left': left,
                'right': right
            }
        
        return left
    
    def parse_and_expression(self) -> Dict[str, Any]:
        """Parse AND expressions."""
        left = self.parse_not_expression()
        
        while (self.current_token().type == TokenType.LOGIC and 
               self.current_token().value.upper() == 'AND'):
            self.consume_token()  # consume AND
            right = self.parse_not_expression()
            left = {
                'type': 'binary_op',
                'operator': 'AND',
                'left': left,
                'right': right
            }
        
        return left
    
    def parse_not_expression(self) -> Dict[str, Any]:
        """Parse NOT expressions (highest precedence)."""
        if (self.current_token().type == TokenType.LOGIC and 
            self.current_token().value.upper() == 'NOT'):
            self.consume_token()  # consume NOT
            operand = self.parse_primary_expression()
            return {
                'type': 'unary_op',
                'operator': 'NOT',
                'operand': operand
            }
        
        return self.parse_primary_expression()
    
    def parse_primary_expression(self) -> Dict[str, Any]:
        """Parse primary expressions (conditions and parentheses)."""
        token = self.current_token()
        
        if token.type == TokenType.PARENTHESIS_OPEN:
            self.consume_token()  # consume (
            expr = self.parse_expression()
            self.consume_token(TokenType.PARENTHESIS_CLOSE)  # consume )
            return expr
        
        elif token.type == TokenType.FIELD:
            return self.parse_condition()
        
        else:
            raise DSLSyntaxError(
                f"Expected field name or '(', got {token.type.value}",
                token.position, token
            )
    
    def parse_condition(self) -> Dict[str, Any]:
        """Parse a single filter condition."""
        # Field name
        field_token = self.consume_token(TokenType.FIELD)
        field_name = field_token.value.lower()
        
        # Operator
        operator_token = self.consume_token(TokenType.OPERATOR)
        operator_str = operator_token.value.upper()
        
        # Value(s)
        if operator_str in ('IS NULL', 'IS NOT NULL'):
            # No value needed
            value = None
        elif operator_str == 'BETWEEN':
            # Two values
            value1 = self.parse_value()
            self.consume_token(TokenType.LOGIC)  # AND
            value2 = self.parse_value()
            value = [value1, value2]
        elif operator_str in ('IN', 'NOT IN'):
            # List of values
            self.consume_token(TokenType.PARENTHESIS_OPEN)
            values = []
            
            while self.current_token().type != TokenType.PARENTHESIS_CLOSE:
                values.append(self.parse_value())
                if self.current_token().type == TokenType.COMMA:
                    self.consume_token()
                elif self.current_token().type != TokenType.PARENTHESIS_CLOSE:
                    raise DSLSyntaxError("Expected ',' or ')'")
            
            self.consume_token(TokenType.PARENTHESIS_CLOSE)
            value = values
        else:
            # Single value
            value = self.parse_value()
        
        return {
            'type': 'condition',
            'field': field_name,
            'operator': operator_str,
            'value': value
        }
    
    def parse_value(self) -> Any:
        """Parse a value (string, number, or quoted string)."""
        token = self.current_token()
        
        if token.type == TokenType.QUOTE:
            # Quoted string
            quote_char = token.value
            self.consume_token()  # consume opening quote
            
            # Collect value until closing quote
            value_parts = []
            while (self.current_token().type != TokenType.QUOTE or 
                   self.current_token().value != quote_char):
                if self.current_token().type == TokenType.EOF:
                    raise DSLSyntaxError("Unterminated quoted string")
                value_parts.append(self.current_token().value)
                self.consume_token()
            
            self.consume_token()  # consume closing quote
            return ''.join(value_parts)
        
        elif token.type == TokenType.VALUE:
            value_str = self.consume_token().value
            
            # Try to convert to number
            try:
                if '.' in value_str:
                    return float(value_str)
                else:
                    return int(value_str)
            except ValueError:
                return value_str
        
        else:
            raise DSLSyntaxError(f"Expected value, got {token.type.value}", token.position, token)
    
    def _expression_to_groups(self, expression: Dict[str, Any]) -> List[FilterGroup]:
        """Convert parsed expression to filter groups."""
        if expression['type'] == 'condition':
            # Single condition -> single group
            condition = self._create_condition(expression)
            group = FilterGroup()
            group.add_condition(condition)
            return [group]
        
        elif expression['type'] == 'binary_op':
            operator = expression['operator']
            left_groups = self._expression_to_groups(expression['left'])
            right_groups = self._expression_to_groups(expression['right'])
            
            if operator == 'AND':
                # Combine all conditions into groups with AND logic
                if len(left_groups) == 1 and len(right_groups) == 1:
                    # Merge into single group
                    combined_group = FilterGroup(logic=FilterLogic.AND)
                    combined_group.conditions.extend(left_groups[0].conditions)
                    combined_group.conditions.extend(right_groups[0].conditions)
                    return [combined_group]
                else:
                    # Multiple groups with AND combination
                    return left_groups + right_groups
            
            elif operator == 'OR':
                # Create separate groups with OR combination
                return left_groups + right_groups
        
        elif expression['type'] == 'unary_op' and expression['operator'] == 'NOT':
            # NOT operation
            operand_groups = self._expression_to_groups(expression['operand'])
            for group in operand_groups:
                group.logic = FilterLogic.NOT
            return operand_groups
        
        return []
    
    def _create_condition(self, expr: Dict[str, Any]) -> FilterCondition:
        """Create a FilterCondition from a condition expression."""
        field_name = expr['field']
        operator_str = expr['operator']
        value = expr['value']
        
        # Map field name to FilterType
        filter_type = self.field_mappings.get(field_name)
        if not filter_type:
            filter_type = FilterType.CUSTOM_FIELD
        
        # Map operator
        operator = self.operator_mappings.get(operator_str)
        if not operator:
            raise DSLSyntaxError(f"Unknown operator: {operator_str}")
        
        # Create FilterValue
        if value is None:
            filter_value = FilterValue(None)
        elif isinstance(value, list):
            filter_value = FilterValue(value, "list")
        elif isinstance(value, (int, float)):
            filter_value = FilterValue(value, "number")
        else:
            filter_value = FilterValue(str(value), "string")
        
        return FilterCondition(
            filter_type=filter_type,
            field_name=field_name if filter_type == FilterType.CUSTOM_FIELD else "",
            operator=operator,
            value=filter_value
        )


class DSLGenerator:
    """Generates DSL query strings from FilterSets."""
    
    def __init__(self):
        # Reverse mappings for generation
        self.type_to_field = {
            FilterType.ELEMENT_TYPE: 'type',
            FilterType.TEXT_CONTENT: 'text',
            FilterType.CONFIDENCE: 'confidence',
            FilterType.PAGE_NUMBER: 'page',
            FilterType.DETECTION_METHOD: 'method',
            FilterType.LANGUAGE: 'language',
        }
        
        self.operator_to_dsl = {
            FilterOperator.EQUALS: '==',
            FilterOperator.NOT_EQUALS: '!=',
            FilterOperator.GREATER_THAN: '>',
            FilterOperator.LESS_THAN: '<',
            FilterOperator.GREATER_EQUAL: '>=',
            FilterOperator.LESS_EQUAL: '<=',
            FilterOperator.CONTAINS: 'LIKE',
            FilterOperator.NOT_CONTAINS: 'NOT LIKE',
            FilterOperator.FUZZY: '~=',
            FilterOperator.BETWEEN: 'BETWEEN',
            FilterOperator.IN: 'IN',
            FilterOperator.NOT_IN: 'NOT IN',
            FilterOperator.IS_NULL: 'IS NULL',
            FilterOperator.IS_NOT_NULL: 'IS NOT NULL',
        }
    
    def generate(self, filter_set: FilterSet) -> str:
        """Generate DSL query string from FilterSet."""
        if not filter_set.groups:
            return ""
        
        group_expressions = []
        
        for group in filter_set.groups:
            if not group.enabled or not group.conditions:
                continue
            
            condition_expressions = []
            
            for condition in group.conditions:
                if not condition.enabled:
                    continue
                
                expr = self._generate_condition(condition)
                if expr:
                    condition_expressions.append(expr)
            
            if condition_expressions:
                if len(condition_expressions) == 1:
                    group_expr = condition_expressions[0]
                else:
                    logic_op = ' AND ' if group.logic == FilterLogic.AND else ' OR '
                    group_expr = logic_op.join(condition_expressions)
                    if len(condition_expressions) > 1:
                        group_expr = f"({group_expr})"
                
                if group.logic == FilterLogic.NOT:
                    group_expr = f"NOT ({group_expr})"
                
                group_expressions.append(group_expr)
        
        if not group_expressions:
            return ""
        
        # Combine groups
        if len(group_expressions) == 1:
            return group_expressions[0]
        else:
            logic_op = ' AND ' if filter_set.combination_logic == FilterLogic.AND else ' OR '
            return logic_op.join(group_expressions)
    
    def _generate_condition(self, condition: FilterCondition) -> str:
        """Generate DSL expression for a single condition."""
        # Get field name
        if condition.filter_type == FilterType.CUSTOM_FIELD:
            field_name = condition.field_name
        else:
            field_name = self.type_to_field.get(condition.filter_type, 'unknown')
        
        # Get operator
        operator_str = self.operator_to_dsl.get(condition.operator, '==')
        
        # Format value
        value = condition.value.value
        
        if condition.operator in (FilterOperator.IS_NULL, FilterOperator.IS_NOT_NULL):
            return f"{field_name} {operator_str}"
        
        elif condition.operator == FilterOperator.BETWEEN:
            if isinstance(value, list) and len(value) == 2:
                return f"{field_name} BETWEEN {self._format_value(value[0])} AND {self._format_value(value[1])}"
        
        elif condition.operator in (FilterOperator.IN, FilterOperator.NOT_IN):
            if isinstance(value, list):
                formatted_values = [self._format_value(v) for v in value]
                values_str = ', '.join(formatted_values)
                return f"{field_name} {operator_str} ({values_str})"
        
        else:
            return f"{field_name} {operator_str} {self._format_value(value)}"
        
        return ""
    
    def _format_value(self, value: Any) -> str:
        """Format a value for DSL output."""
        if value is None:
            return "NULL"
        elif isinstance(value, str):
            # Quote strings that contain spaces or special characters
            if ' ' in value or any(c in value for c in '()[],"\''):
                return f'"{value}"'
            return value
        else:
            return str(value)


class DSLQueryHelper:
    """Helper class for DSL query assistance and validation."""
    
    def __init__(self):
        self.parser = DSLParser()
        self.generator = DSLGenerator()
    
    def validate_query(self, query: str) -> Tuple[bool, Optional[str]]:
        """Validate a DSL query string."""
        try:
            self.parser.parse(query)
            return True, None
        except DSLSyntaxError as e:
            return False, str(e)
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def get_suggestions(self, partial_query: str) -> List[str]:
        """Get auto-completion suggestions for partial query."""
        suggestions = []
        
        # Basic field suggestions
        fields = ['type', 'text', 'confidence', 'page', 'method', 'language']
        
        # If query ends with a field name, suggest operators
        words = partial_query.strip().split()
        if words and words[-1].lower() in fields:
            operators = ['==', '!=', '>', '<', '>=', '<=', 'LIKE', 'IN', 'BETWEEN']
            suggestions.extend([f"{partial_query} {op}" for op in operators])
        
        # Otherwise suggest fields
        else:
            last_word = words[-1].lower() if words else ""
            matching_fields = [f for f in fields if f.startswith(last_word)]
            if words:
                base = ' '.join(words[:-1])
                suggestions.extend([f"{base} {field}" if base else field for field in matching_fields])
            else:
                suggestions.extend(matching_fields)
        
        return suggestions[:10]  # Limit to 10 suggestions
    
    def format_query(self, query: str) -> str:
        """Format a DSL query string for better readability."""
        try:
            filter_set = self.parser.parse(query)
            return self.generator.generate(filter_set)
        except Exception:
            return query  # Return original if formatting fails
    
    def get_examples(self) -> List[Tuple[str, str]]:
        """Get example DSL queries with descriptions."""
        return [
            ('type == "Title"', 'Find all title elements'),
            ('confidence > 0.8', 'Find high-confidence elements'),
            ('page BETWEEN 1 AND 5', 'Find elements from pages 1-5'),
            ('text LIKE "machine learning"', 'Find elements containing "machine learning"'),
            ('type IN ("Title", "Header")', 'Find titles and headers'),
            ('confidence > 0.9 AND page < 10', 'High-confidence elements from early pages'),
            ('(type == "Text" OR type == "Title") AND confidence > 0.8', 'High-confidence text or title elements'),
            ('NOT (confidence < 0.5)', 'Exclude low-confidence elements'),
        ]