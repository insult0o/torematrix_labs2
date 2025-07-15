"""
Advanced Search and Filter System for Element Management

This module provides comprehensive search and filtering capabilities for document elements
with full-text search, indexing, type filtering, and advanced query processing.
"""

from .engine import SearchEngine, IndexedSearchEngine
from .indexer import ElementIndexer, SearchIndex
from .query_parser import QueryParser, SearchQuery
from .filters import FilterManager, FilterSet
from .highlighting import SearchHighlighter
from .statistics import SearchStatistics

__all__ = [
    'SearchEngine',
    'IndexedSearchEngine', 
    'ElementIndexer',
    'SearchIndex',
    'QueryParser',
    'SearchQuery',
    'FilterManager',
    'FilterSet',
    'SearchHighlighter',
    'SearchStatistics'
]