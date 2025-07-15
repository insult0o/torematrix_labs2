"""
Advanced Query Parser for Search System

Provides sophisticated query parsing with support for complex expressions,
boolean operations, field-specific searches, and natural language queries.
"""

import re
from typing import List, Dict, Set, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod


class QueryType(Enum):
    """Types of search queries."""
    SIMPLE = "simple"          # Simple text search
    BOOLEAN = "boolean"        # Boolean AND/OR/NOT operations
    FIELD = "field"           # Field-specific search (type:text)
    PHRASE = "phrase"         # Exact phrase search ("quoted text")
    WILDCARD = "wildcard"     # Wildcard search (text*)
    REGEX = "regex"           # Regular expression search
    FUZZY = "fuzzy"           # Fuzzy search (text~)
    RANGE = "range"           # Range search (confidence:[0.5 TO 0.9])
    PROXIMITY = "proximity"   # Proximity search (word1 NEAR word2)


class BooleanOperator(Enum):
    """Boolean operators for query combination."""
    AND = "AND"
    OR = "OR"
    NOT = "NOT"


@dataclass
class QueryToken:
    """Individual token in a parsed query."""
    type: QueryType
    value: str
    field: Optional[str] = None
    modifier: Optional[str] = None  # ~, *, etc.
    boost: float = 1.0
    
    def __str__(self) -> str:
        field_prefix = f"{self.field}:" if self.field else ""
        modifier_suffix = self.modifier or ""
        boost_suffix = f"^{self.boost}" if self.boost != 1.0 else ""
        return f"{field_prefix}{self.value}{modifier_suffix}{boost_suffix}"


@dataclass
class SearchQuery:
    """Parsed and structured search query."""
    tokens: List[QueryToken] = field(default_factory=list)
    boolean_operators: List[BooleanOperator] = field(default_factory=list)
    filters: Dict[str, Any] = field(default_factory=dict)
    sort_fields: List[tuple] = field(default_factory=list)  # (field, desc)
    limit: Optional[int] = None
    offset: int = 0
    fuzzy_enabled: bool = False
    case_sensitive: bool = False
    
    def is_simple(self) -> bool:
        """Check if this is a simple text query."""
        return (len(self.tokens) == 1 and 
                self.tokens[0].type == QueryType.SIMPLE and
                not self.boolean_operators and
                not self.filters)
    
    def has_field_searches(self) -> bool:
        """Check if query contains field-specific searches."""
        return any(token.field for token in self.tokens)
    
    def has_boolean_logic(self) -> bool:
        """Check if query contains boolean operators."""
        return bool(self.boolean_operators)
    
    def get_text_terms(self) -> List[str]:
        """Get all text terms from the query."""
        return [token.value for token in self.tokens 
                if token.type in (QueryType.SIMPLE, QueryType.PHRASE, QueryType.WILDCARD)]
    
    def get_field_searches(self) -> Dict[str, List[str]]:
        """Get field-specific search terms."""
        field_searches = {}
        for token in self.tokens:
            if token.field:
                if token.field not in field_searches:
                    field_searches[token.field] = []
                field_searches[token.field].append(token.value)
        return field_searches
    
    def __str__(self) -> str:
        result = []
        for i, token in enumerate(self.tokens):
            if i > 0 and i <= len(self.boolean_operators):
                result.append(f" {self.boolean_operators[i-1].value} ")
            result.append(str(token))
        return "".join(result)


class QueryParser:
    """Advanced query parser with support for complex search syntax."""
    
    def __init__(self):
        # Field mappings for element properties
        self.field_mappings = {
            'type': 'element_type',
            'text': 'text_content',
            'confidence': 'confidence',
            'page': 'page_number',
            'lang': 'languages',
            'method': 'detection_method'
        }
        
        # Regex patterns for different query types
        self.patterns = {
            'field_search': re.compile(r'(\w+):(["\']?)([^"\'\s]+|[^"\']*?)\2'),
            'phrase_search': re.compile(r'"([^"]*)"'),
            'boolean_ops': re.compile(r'\b(AND|OR|NOT)\b', re.IGNORECASE),
            'wildcard': re.compile(r'\w+\*'),
            'fuzzy': re.compile(r'\w+~(\d*\.?\d*)'),
            'boost': re.compile(r'\^(\d+\.?\d*)'),
            'range': re.compile(r'(\w+):\[([^\]]+)\s+TO\s+([^\]]+)\]'),
            'proximity': re.compile(r'"([^"]*?)"\s*~(\d+)'),
            'parentheses': re.compile(r'\([^)]+\)')
        }
    
    def parse(self, query_string: str) -> SearchQuery:
        """Parse query string into structured SearchQuery."""
        if not query_string or not query_string.strip():
            return SearchQuery()
        
        query_string = query_string.strip()
        
        # Create query object
        search_query = SearchQuery()
        
        # Extract special syntax first
        query_string = self._extract_ranges(query_string, search_query)
        query_string = self._extract_field_searches(query_string, search_query)
        query_string = self._extract_phrases(query_string, search_query)
        query_string = self._extract_proximity_searches(query_string, search_query)
        
        # Extract boolean operators
        self._extract_boolean_operators(query_string, search_query)
        
        # Extract remaining terms
        self._extract_simple_terms(query_string, search_query)
        
        # Post-process for modifiers
        self._apply_modifiers(search_query)
        
        return search_query
    
    def _extract_ranges(self, query: str, search_query: SearchQuery) -> str:
        """Extract range searches like confidence:[0.5 TO 0.9]."""
        for match in self.patterns['range'].finditer(query):
            field = match.group(1)
            start_value = match.group(2).strip()
            end_value = match.group(3).strip()
            
            # Convert to appropriate types
            try:
                start_val = float(start_value)
                end_val = float(end_value)
                search_query.filters[f"{field}_range"] = (start_val, end_val)
            except ValueError:
                # String range
                search_query.filters[f"{field}_range"] = (start_value, end_value)
            
            query = query.replace(match.group(0), '')
        
        return query
    
    def _extract_field_searches(self, query: str, search_query: SearchQuery) -> str:
        """Extract field-specific searches like type:text."""
        for match in self.patterns['field_search'].finditer(query):
            field = match.group(1)
            value = match.group(3)
            
            token = QueryToken(
                type=QueryType.FIELD,
                value=value,
                field=field
            )
            search_query.tokens.append(token)
            
            query = query.replace(match.group(0), '')
        
        return query
    
    def _extract_phrases(self, query: str, search_query: SearchQuery) -> str:
        """Extract phrase searches in quotes."""
        for match in self.patterns['phrase_search'].finditer(query):
            phrase = match.group(1)
            if phrase.strip():
                token = QueryToken(
                    type=QueryType.PHRASE,
                    value=phrase
                )
                search_query.tokens.append(token)
            
            query = query.replace(match.group(0), '')
        
        return query
    
    def _extract_proximity_searches(self, query: str, search_query: SearchQuery) -> str:
        """Extract proximity searches like \"word1 word2\"~5."""
        for match in self.patterns['proximity'].finditer(query):
            phrase = match.group(1)
            distance = int(match.group(2))
            
            token = QueryToken(
                type=QueryType.PROXIMITY,
                value=phrase,
                modifier=f"~{distance}"
            )
            search_query.tokens.append(token)
            
            query = query.replace(match.group(0), '')
        
        return query
    
    def _extract_boolean_operators(self, query: str, search_query: SearchQuery) -> None:
        """Extract boolean operators."""
        operators = []
        for match in self.patterns['boolean_ops'].finditer(query):
            op_text = match.group(1).upper()
            operators.append(BooleanOperator(op_text))
        
        search_query.boolean_operators = operators
    
    def _extract_simple_terms(self, query: str, search_query: SearchQuery) -> None:
        """Extract remaining simple search terms."""
        # Remove boolean operators for term extraction
        clean_query = self.patterns['boolean_ops'].sub(' ', query)
        
        # Split on whitespace and filter empty terms
        terms = [term.strip() for term in clean_query.split() if term.strip()]
        
        for term in terms:
            # Check for wildcards
            if '*' in term:
                token = QueryToken(
                    type=QueryType.WILDCARD,
                    value=term.replace('*', ''),
                    modifier='*'
                )
            # Check for fuzzy search
            elif '~' in term:
                fuzzy_match = self.patterns['fuzzy'].match(term)
                if fuzzy_match:
                    base_term = term.split('~')[0]
                    distance = fuzzy_match.group(1) or '2'
                    token = QueryToken(
                        type=QueryType.FUZZY,
                        value=base_term,
                        modifier=f"~{distance}"
                    )
                    search_query.fuzzy_enabled = True
                else:
                    token = QueryToken(type=QueryType.SIMPLE, value=term)
            else:
                token = QueryToken(type=QueryType.SIMPLE, value=term)
            
            search_query.tokens.append(token)
    
    def _apply_modifiers(self, search_query: SearchQuery) -> None:
        """Apply boost and other modifiers to query tokens."""
        for token in search_query.tokens:
            # Extract boost values
            boost_match = self.patterns['boost'].search(token.value)
            if boost_match:
                token.boost = float(boost_match.group(1))
                token.value = token.value.replace(boost_match.group(0), '')
    
    def validate_query(self, query: SearchQuery) -> List[str]:
        """Validate parsed query and return list of errors."""
        errors = []
        
        # Check for empty query
        if not query.tokens:
            errors.append("Query is empty")
            return errors
        
        # Validate boolean operator placement
        if len(query.boolean_operators) != max(0, len(query.tokens) - 1):
            errors.append("Invalid boolean operator placement")
        
        # Validate field names
        for token in query.tokens:
            if token.field and token.field not in self.field_mappings:
                errors.append(f"Unknown field: {token.field}")
        
        # Validate range queries
        for filter_name, filter_value in query.filters.items():
            if filter_name.endswith('_range'):
                field = filter_name[:-6]  # Remove '_range' suffix
                if field not in self.field_mappings:
                    errors.append(f"Unknown range field: {field}")
        
        return errors
    
    def suggest_corrections(self, query_string: str) -> List[str]:
        """Suggest corrections for query syntax."""
        suggestions = []
        
        # Check for common typos in field names
        field_suggestions = {
            'typ': 'type',
            'txt': 'text', 
            'conf': 'confidence',
            'pg': 'page'
        }
        
        for typo, correction in field_suggestions.items():
            if f"{typo}:" in query_string:
                suggestions.append(f"Did you mean '{correction}:' instead of '{typo}:'?")
        
        # Check for unmatched quotes
        if query_string.count('"') % 2 != 0:
            suggestions.append("Unmatched quote - phrase searches should be enclosed in quotes")
        
        # Check for unmatched parentheses
        if query_string.count('(') != query_string.count(')'):
            suggestions.append("Unmatched parentheses in query")
        
        return suggestions
    
    def get_field_suggestions(self) -> List[str]:
        """Get list of available field names for auto-completion."""
        return list(self.field_mappings.keys())
    
    def parse_natural_language(self, query: str) -> SearchQuery:
        """Parse natural language queries and convert to structured search."""
        # Simple natural language processing
        search_query = SearchQuery()
        
        # Convert common natural language patterns
        query = query.lower()
        
        # "find all X elements" -> type:X
        type_match = re.search(r'find.*?(\w+)\s+elements?', query)
        if type_match:
            element_type = type_match.group(1)
            token = QueryToken(type=QueryType.FIELD, value=element_type, field='type')
            search_query.tokens.append(token)
            query = re.sub(r'find.*?(\w+)\s+elements?', '', query)
        
        # "with confidence above/below X" -> confidence range
        conf_match = re.search(r'confidence\s+(above|below|over|under)\s+(\d*\.?\d+)', query)
        if conf_match:
            operator = conf_match.group(1)
            value = float(conf_match.group(2))
            
            if operator in ('above', 'over'):
                search_query.filters['confidence_range'] = (value, 1.0)
            else:
                search_query.filters['confidence_range'] = (0.0, value)
            
            query = re.sub(r'confidence\s+(above|below|over|under)\s+(\d*\.?\d+)', '', query)
        
        # "on page X" -> page:X
        page_match = re.search(r'on\s+page\s+(\d+)', query)
        if page_match:
            page_num = page_match.group(1)
            token = QueryToken(type=QueryType.FIELD, value=page_num, field='page')
            search_query.tokens.append(token)
            query = re.sub(r'on\s+page\s+(\d+)', '', query)
        
        # Remaining text as simple search
        remaining_text = query.strip()
        if remaining_text:
            # Remove common stop words
            stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
            words = remaining_text.split()
            words = [word for word in words if word not in stop_words]
            
            for word in words:
                if word:
                    token = QueryToken(type=QueryType.SIMPLE, value=word)
                    search_query.tokens.append(token)
        
        return search_query


class QueryBuilder:
    """Helper class for programmatically building search queries."""
    
    def __init__(self):
        self.query = SearchQuery()
    
    def text(self, term: str) -> 'QueryBuilder':
        """Add text search term."""
        token = QueryToken(type=QueryType.SIMPLE, value=term)
        self.query.tokens.append(token)
        return self
    
    def phrase(self, phrase: str) -> 'QueryBuilder':
        """Add exact phrase search."""
        token = QueryToken(type=QueryType.PHRASE, value=phrase)
        self.query.tokens.append(token)
        return self
    
    def field(self, field_name: str, value: str) -> 'QueryBuilder':
        """Add field-specific search."""
        token = QueryToken(type=QueryType.FIELD, value=value, field=field_name)
        self.query.tokens.append(token)
        return self
    
    def wildcard(self, term: str) -> 'QueryBuilder':
        """Add wildcard search."""
        token = QueryToken(type=QueryType.WILDCARD, value=term, modifier='*')
        self.query.tokens.append(token)
        return self
    
    def fuzzy(self, term: str, distance: int = 2) -> 'QueryBuilder':
        """Add fuzzy search."""
        token = QueryToken(type=QueryType.FUZZY, value=term, modifier=f"~{distance}")
        self.query.tokens.append(token)
        self.query.fuzzy_enabled = True
        return self
    
    def range_filter(self, field: str, min_val: float, max_val: float) -> 'QueryBuilder':
        """Add range filter."""
        self.query.filters[f"{field}_range"] = (min_val, max_val)
        return self
    
    def and_operator(self) -> 'QueryBuilder':
        """Add AND operator."""
        self.query.boolean_operators.append(BooleanOperator.AND)
        return self
    
    def or_operator(self) -> 'QueryBuilder':
        """Add OR operator."""
        self.query.boolean_operators.append(BooleanOperator.OR)
        return self
    
    def not_operator(self) -> 'QueryBuilder':
        """Add NOT operator."""
        self.query.boolean_operators.append(BooleanOperator.NOT)
        return self
    
    def boost(self, factor: float) -> 'QueryBuilder':
        """Add boost to last token."""
        if self.query.tokens:
            self.query.tokens[-1].boost = factor
        return self
    
    def sort_by(self, field: str, descending: bool = False) -> 'QueryBuilder':
        """Add sort criteria."""
        self.query.sort_fields.append((field, descending))
        return self
    
    def limit(self, count: int) -> 'QueryBuilder':
        """Set result limit."""
        self.query.limit = count
        return self
    
    def offset(self, start: int) -> 'QueryBuilder':
        """Set result offset."""
        self.query.offset = start
        return self
    
    def case_sensitive(self, enabled: bool = True) -> 'QueryBuilder':
        """Enable case-sensitive search."""
        self.query.case_sensitive = enabled
        return self
    
    def build(self) -> SearchQuery:
        """Build and return the search query."""
        return self.query
    
    def reset(self) -> 'QueryBuilder':
        """Reset the builder for a new query."""
        self.query = SearchQuery()
        return self