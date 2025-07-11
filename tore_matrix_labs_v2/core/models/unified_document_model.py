#!/usr/bin/env python3
"""
Unified Document Model for TORE Matrix Labs V2

This model consolidates all document-related data structures from the original
codebase into a single, comprehensive model. It replaces multiple scattered
document models and provides a clean, consistent interface.

Key improvements:
- Single document model for all document types
- Clear status and processing stage tracking
- Comprehensive metadata storage
- Consistent serialization
- Type safety with dataclasses
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path


class DocumentStatus(Enum):
    """Document processing status."""
    CREATED = "created"
    LOADING = "loading"
    LOADED = "loaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    VALIDATING = "validating"
    VALIDATED = "validated"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


class ProcessingStage(Enum):
    """Current processing stage."""
    INITIAL = "initial"
    EXTRACTION = "extraction"
    QUALITY_ASSESSMENT = "quality_assessment"
    VALIDATION = "validation"
    FINALIZATION = "finalization"
    EXPORT = "export"


@dataclass
class DocumentMetadata:
    """Document metadata information."""
    
    # File information
    file_size: int = 0
    file_type: str = ""
    mime_type: str = ""
    
    # Document properties
    page_count: int = 0
    language: str = "en"
    encoding: str = "utf-8"
    
    # Processing information
    extraction_method: str = ""
    quality_score: float = 0.0
    processing_time: float = 0.0
    
    # Document classification
    document_type: str = "unknown"  # ICAO, ATC, general, etc.
    classification_confidence: float = 0.0
    
    # Content statistics
    total_characters: int = 0
    total_words: int = 0
    total_paragraphs: int = 0
    total_tables: int = 0
    total_images: int = 0
    total_diagrams: int = 0
    
    # Additional metadata
    custom_fields: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessingConfig:
    """Configuration for document processing."""
    
    # Quality requirements
    min_quality_score: float = 0.8
    require_manual_validation: bool = True
    
    # Processing options
    extract_text: bool = True
    extract_images: bool = True
    extract_tables: bool = True
    extract_diagrams: bool = True
    
    # Export options
    export_formats: List[str] = field(default_factory=lambda: ["jsonl", "json"])
    chunk_size: int = 512
    chunk_overlap: int = 50
    
    # Advanced options
    use_ocr: bool = False
    ocr_language: str = "eng"
    preserve_formatting: bool = True


@dataclass
class UnifiedDocument:
    """
    Unified document model that handles all document types and processing states.
    
    This model replaces the scattered document models from the original codebase
    and provides a single, comprehensive representation of a document throughout
    its processing lifecycle.
    """
    
    # Identity
    id: str
    project_id: Optional[str] = None
    
    # File information
    file_path: str = ""
    file_name: str = ""
    original_filename: str = ""
    
    # Status tracking
    status: DocumentStatus = DocumentStatus.CREATED
    processing_stage: ProcessingStage = ProcessingStage.INITIAL
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)
    processed_at: Optional[datetime] = None
    
    # Content
    extracted_text: str = ""
    extracted_content: Dict[str, Any] = field(default_factory=dict)
    
    # Areas and regions
    areas: Dict[str, Any] = field(default_factory=dict)
    visual_areas: Dict[str, Any] = field(default_factory=dict)
    exclusion_zones: List[Dict[str, Any]] = field(default_factory=list)
    
    # Processing results
    extraction_results: Dict[str, Any] = field(default_factory=dict)
    quality_assessment: Dict[str, Any] = field(default_factory=dict)
    validation_results: Dict[str, Any] = field(default_factory=dict)
    
    # Configuration
    processing_config: ProcessingConfig = field(default_factory=ProcessingConfig)
    
    # Metadata
    metadata: DocumentMetadata = field(default_factory=DocumentMetadata)
    
    # Error tracking
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize document after creation."""
        if not self.original_filename and self.file_name:
            self.original_filename = self.file_name
        
        # Ensure file_type is set
        if not self.metadata.file_type and self.file_path:
            self.metadata.file_type = Path(self.file_path).suffix.lower()
    
    def update_status(self, status: DocumentStatus, stage: Optional[ProcessingStage] = None):
        """Update document status and processing stage."""
        self.status = status
        if stage:
            self.processing_stage = stage
        self.modified_at = datetime.now()
        
        # Set processed timestamp when completed
        if status in [DocumentStatus.COMPLETED, DocumentStatus.VALIDATED]:
            self.processed_at = datetime.now()
    
    def add_error(self, error_type: str, message: str, details: Optional[Dict[str, Any]] = None):
        """Add an error to the document."""
        error = {
            "type": error_type,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        }
        self.errors.append(error)
        
        # Update status to failed if critical error
        if error_type in ["extraction_failed", "processing_failed"]:
            self.update_status(DocumentStatus.FAILED)
    
    def add_warning(self, warning_type: str, message: str, details: Optional[Dict[str, Any]] = None):
        """Add a warning to the document."""
        warning = {
            "type": warning_type,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        }
        self.warnings.append(warning)
    
    def get_page_count(self) -> int:
        """Get the number of pages in the document."""
        return self.metadata.page_count
    
    def get_area_count(self) -> int:
        """Get the total number of areas in the document."""
        return len(self.areas) + len(self.visual_areas)
    
    def get_quality_score(self) -> float:
        """Get the overall quality score."""
        return self.metadata.quality_score
    
    def is_processed(self) -> bool:
        """Check if document has been processed."""
        return self.status in [
            DocumentStatus.PROCESSED,
            DocumentStatus.VALIDATED,
            DocumentStatus.COMPLETED
        ]
    
    def requires_validation(self) -> bool:
        """Check if document requires manual validation."""
        if self.processing_config.require_manual_validation:
            return self.get_quality_score() < self.processing_config.min_quality_score
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert document to dictionary for serialization."""
        data = asdict(self)
        
        # Convert enums to strings
        data["status"] = self.status.value
        data["processing_stage"] = self.processing_stage.value
        
        # Convert datetimes to ISO format
        data["created_at"] = self.created_at.isoformat()
        data["modified_at"] = self.modified_at.isoformat()
        if self.processed_at:
            data["processed_at"] = self.processed_at.isoformat()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UnifiedDocument':
        """Create document from dictionary."""
        # Convert string enums back to enum values
        if "status" in data:
            data["status"] = DocumentStatus(data["status"])
        if "processing_stage" in data:
            data["processing_stage"] = ProcessingStage(data["processing_stage"])
        
        # Convert ISO datetime strings back to datetime objects
        for field_name in ["created_at", "modified_at", "processed_at"]:
            if field_name in data and data[field_name]:
                if isinstance(data[field_name], str):
                    data[field_name] = datetime.fromisoformat(data[field_name])
        
        # Handle nested objects
        if "processing_config" in data and isinstance(data["processing_config"], dict):
            data["processing_config"] = ProcessingConfig(**data["processing_config"])
        
        if "metadata" in data and isinstance(data["metadata"], dict):
            data["metadata"] = DocumentMetadata(**data["metadata"])
        
        return cls(**data)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the document for display."""
        return {
            "id": self.id,
            "name": self.file_name,
            "status": self.status.value,
            "stage": self.processing_stage.value,
            "pages": self.get_page_count(),
            "areas": self.get_area_count(),
            "quality": self.get_quality_score(),
            "created": self.created_at.isoformat(),
            "modified": self.modified_at.isoformat(),
            "errors": len(self.errors),
            "warnings": len(self.warnings)
        }


@dataclass
class ProcessingResult:
    """Result of document processing operation."""
    
    # Identity
    document_id: str
    operation: str = "process"
    
    # Status
    success: bool = False
    
    # Results
    extraction_data: Dict[str, Any] = field(default_factory=dict)
    quality_assessment: Dict[str, Any] = field(default_factory=dict)
    validation_data: Optional[Dict[str, Any]] = None
    
    # Performance metrics
    processing_time: float = 0.0
    memory_usage: float = 0.0
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    
    # Error information
    error_message: Optional[str] = None
    error_details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProcessingResult':
        """Create result from dictionary."""
        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        return cls(**data)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the processing result."""
        return {
            "document_id": self.document_id,
            "operation": self.operation,
            "success": self.success,
            "processing_time": self.processing_time,
            "has_validation": self.validation_data is not None,
            "error": self.error_message,
            "created_at": self.created_at.isoformat()
        }