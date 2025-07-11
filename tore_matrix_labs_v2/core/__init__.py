#!/usr/bin/env python3
"""
Core module for TORE Matrix Labs V2

This module contains the core functionality including:
- Document processing pipeline
- Text extraction services  
- Quality assessment engine
- Coordinate mapping services
- Validation services
- Storage repositories

All core services are designed with:
- Clear separation of concerns
- Dependency injection
- Comprehensive error handling
- Performance optimization
- Bug-free implementation
"""

from .processors import *
from .services import *
from .models import *
from .storage import *
from .validation import *

__all__ = [
    # Processors
    "UnifiedDocumentProcessor",
    "ExtractionStrategy",
    "QualityAssessmentEngine", 
    "PipelineOrchestrator",
    
    # Services
    "CoordinateMappingService",
    "TextExtractionService",
    "HighlightingService",
    "ValidationService",
    "AreaClassificationService",
    
    # Models
    "UnifiedDocument",
    "UnifiedArea", 
    "ValidationState",
    "ProjectModel",
    
    # Storage
    "RepositoryBase",
    "DocumentRepository",
    "AreaRepository",
    "MigrationManager",
    
    # Validation
    "QualityValidator",
    "ContentValidator",
    "ComplianceValidator"
]