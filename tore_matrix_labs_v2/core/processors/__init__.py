#!/usr/bin/env python3
"""
Document processing module for TORE Matrix Labs V2

This module consolidates all document processing functionality that was 
previously scattered across multiple processors. Key improvements:

- Single unified processor with strategy pattern
- Clean pipeline architecture  
- Proper error handling and recovery
- Performance optimization
- Bug-free implementation

Processors included:
- UnifiedDocumentProcessor: Main processing orchestrator
- ExtractionStrategy: Pluggable extraction methods
- QualityAssessmentEngine: Multi-dimensional quality scoring
- PipelineOrchestrator: Workflow management
"""

from .unified_document_processor import UnifiedDocumentProcessor
from .extraction_strategies import (
    ExtractionStrategy,
    PyMuPDFExtractionStrategy,
    OCRExtractionStrategy, 
    UnstructuredExtractionStrategy
)
from .quality_assessment_engine import QualityAssessmentEngine
from .pipeline_orchestrator import PipelineOrchestrator

__all__ = [
    "UnifiedDocumentProcessor",
    "ExtractionStrategy",
    "PyMuPDFExtractionStrategy",
    "OCRExtractionStrategy",
    "UnstructuredExtractionStrategy", 
    "QualityAssessmentEngine",
    "PipelineOrchestrator"
]