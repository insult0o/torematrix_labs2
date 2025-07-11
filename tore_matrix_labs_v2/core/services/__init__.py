#!/usr/bin/env python3
"""
Services module for TORE Matrix Labs V2

This module contains all the core services that provide shared functionality
across the application. These services implement the business logic that was
previously scattered throughout the codebase.

Key principles:
- Single responsibility per service
- Dependency injection for testability
- Clear interfaces and contracts
- Comprehensive error handling
- Performance optimization

Services included:
- CoordinateMappingService: Centralized coordinate transformations
- TextExtractionService: Unified text extraction logic
- HighlightingService: Multi-line highlighting functionality
- ValidationService: Document validation logic  
- AreaClassificationService: IMAGE/TABLE/DIAGRAM classification
"""

from .coordinate_mapping_service import CoordinateMappingService
from .text_extraction_service import TextExtractionService  
from .highlighting_service import HighlightingService
from .validation_service import ValidationService
from .area_classification_service import AreaClassificationService

__all__ = [
    "CoordinateMappingService",
    "TextExtractionService",
    "HighlightingService", 
    "ValidationService",
    "AreaClassificationService"
]