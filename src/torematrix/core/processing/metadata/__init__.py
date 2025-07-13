"""Metadata processing and relationship detection for document elements.

This package provides comprehensive metadata extraction and relationship detection
capabilities for document processing, including spatial, content-based, and
semantic relationship analysis.

Note: Import modules individually to avoid dependency issues during testing.
"""

# Import modules individually as needed to avoid loading all dependencies
# from .relationships import RelationshipDetectionEngine, RelationshipConfig, DocumentContext
# from .graph import ElementRelationshipGraph
# from .models.relationship import Relationship, RelationshipType
# from .extractors.reading_order import ReadingOrderExtractor, ReadingOrder, Column
# from .extractors.semantic import SemanticRoleExtractor, SemanticRole, SemanticConfig
# from .algorithms.spatial import SpatialAnalyzer
# from .algorithms.content import ContentAnalyzer
# from .storage.graph_storage import GraphStorage, RelationshipQuery
# from .storage.validators import RelationshipValidator, ValidationResult

__all__ = [
    # Core engine
    'RelationshipDetectionEngine',
    'RelationshipConfig',
    'DocumentContext',
    
    # Graph structure
    'ElementRelationshipGraph',
    'Relationship',
    'RelationshipType',
    
    # Extractors
    'ReadingOrderExtractor',
    'ReadingOrder',
    'Column',
    'SemanticRoleExtractor',
    'SemanticRole',
    'SemanticConfig',
    
    # Analyzers
    'SpatialAnalyzer',
    'ContentAnalyzer',
    
    # Storage
    'GraphStorage',
    'RelationshipQuery',
    'RelationshipValidator',
    'ValidationResult'
]