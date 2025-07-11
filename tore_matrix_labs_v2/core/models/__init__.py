#!/usr/bin/env python3
"""
Models module for TORE Matrix Labs V2

This module contains all the unified data models that replace the scattered
model definitions in the original codebase. Key improvements:

- Single unified models for documents, areas, and projects
- Consistent serialization approach
- Simplified state management
- Better type safety with dataclasses
- Clear relationships between models

Models included:
- UnifiedDocument: Single document model for all document types
- UnifiedArea: Single area model for IMAGE/TABLE/DIAGRAM areas
- ValidationState: Simplified validation state management
- ProjectModel: Project structure and metadata
"""

from .unified_document_model import (
    UnifiedDocument, 
    ProcessingResult,
    DocumentStatus,
    ProcessingStage
)
from .unified_area_model import (
    UnifiedArea,
    AreaType, 
    AreaStatus,
    AreaCoordinates,
    AreaContent,
    AreaValidation
)
from .validation_state_model import (
    ValidationState,
    ValidationStatus,
    ValidationRule
)
from .project_model import (
    ProjectModel,
    ProjectSettings,
    ProjectStats
)

__all__ = [
    # Document models
    "UnifiedDocument",
    "ProcessingResult", 
    "DocumentStatus",
    "ProcessingStage",
    
    # Area models
    "UnifiedArea",
    "AreaType",
    "AreaStatus", 
    "AreaCoordinates",
    "AreaContent",
    "AreaValidation",
    
    # Validation models
    "ValidationState",
    "ValidationStatus",
    "ValidationRule",
    
    # Project models
    "ProjectModel",
    "ProjectSettings",
    "ProjectStats"
]