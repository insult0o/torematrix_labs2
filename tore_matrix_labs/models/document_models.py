"""
Document data models for TORE Matrix Labs.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum
import uuid

from ..config.constants import DocumentType, ProcessingStatus, QualityLevel, ValidationState


@dataclass
class DocumentMetadata:
    """Document metadata information."""
    file_name: str
    file_path: str
    file_size: int
    file_type: str
    creation_date: datetime
    modification_date: datetime
    page_count: int
    author: str = ""
    title: str = ""
    subject: str = ""
    keywords: List[str] = field(default_factory=list)
    language: str = "en"
    
    def __post_init__(self):
        if isinstance(self.creation_date, str):
            self.creation_date = datetime.fromisoformat(self.creation_date)
        if isinstance(self.modification_date, str):
            self.modification_date = datetime.fromisoformat(self.modification_date)


@dataclass
class ProcessingConfiguration:
    """Configuration for document processing."""
    extract_text: bool = True
    extract_tables: bool = True
    extract_images: bool = True
    preserve_formatting: bool = True
    apply_ocr: bool = False
    ocr_language: str = "eng"
    quality_threshold: float = 0.8
    chunk_size: int = 512
    chunk_overlap: int = 50
    custom_settings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Result of document validation."""
    validator_id: str
    validation_date: datetime
    state: ValidationState
    confidence: float
    notes: str = ""
    issues_found: List[str] = field(default_factory=list)
    corrections_made: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if isinstance(self.validation_date, str):
            self.validation_date = datetime.fromisoformat(self.validation_date)


@dataclass
class ProcessingHistory:
    """History of document processing steps."""
    step_id: str
    step_name: str
    timestamp: datetime
    status: str
    duration: float
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    error_message: str = ""
    
    def __post_init__(self):
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)


@dataclass
class Document:
    """Main document model."""
    id: str
    metadata: DocumentMetadata
    document_type: DocumentType
    processing_status: ProcessingStatus
    processing_config: ProcessingConfiguration
    quality_level: QualityLevel
    quality_score: float
    validation_results: List[ValidationResult] = field(default_factory=list)
    processing_history: List[ProcessingHistory] = field(default_factory=list)
    extracted_content: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)
    custom_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at)
        if isinstance(self.updated_at, str):
            self.updated_at = datetime.fromisoformat(self.updated_at)
    
    def update_status(self, new_status: ProcessingStatus):
        """Update processing status and timestamp."""
        self.processing_status = new_status
        self.updated_at = datetime.now()
    
    def add_validation_result(self, result: ValidationResult):
        """Add validation result."""
        self.validation_results.append(result)
        self.updated_at = datetime.now()
    
    def add_processing_step(self, step: ProcessingHistory):
        """Add processing step to history."""
        self.processing_history.append(step)
        self.updated_at = datetime.now()
    
    def get_latest_validation(self) -> Optional[ValidationResult]:
        """Get the most recent validation result."""
        if self.validation_results:
            return max(self.validation_results, key=lambda x: x.validation_date)
        return None
    
    def is_approved(self) -> bool:
        """Check if document is approved for export."""
        latest_validation = self.get_latest_validation()
        if latest_validation:
            return latest_validation.state == ValidationState.APPROVED
        return False
    
    def get_processing_time(self) -> float:
        """Calculate total processing time."""
        return sum(step.duration for step in self.processing_history)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'metadata': {
                'file_name': self.metadata.file_name,
                'file_path': self.metadata.file_path,
                'file_size': self.metadata.file_size,
                'file_type': self.metadata.file_type,
                'creation_date': self.metadata.creation_date.isoformat(),
                'modification_date': self.metadata.modification_date.isoformat(),
                'page_count': self.metadata.page_count,
                'author': self.metadata.author,
                'title': self.metadata.title,
                'subject': self.metadata.subject,
                'keywords': self.metadata.keywords,
                'language': self.metadata.language
            },
            'document_type': self.document_type.value,
            'processing_status': self.processing_status.value,
            'quality_level': self.quality_level.value,
            'quality_score': self.quality_score,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'tags': self.tags,
            'custom_metadata': self.custom_metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Document':
        """Create document from dictionary."""
        metadata = DocumentMetadata(
            file_name=data['metadata']['file_name'],
            file_path=data['metadata']['file_path'],
            file_size=data['metadata']['file_size'],
            file_type=data['metadata']['file_type'],
            creation_date=datetime.fromisoformat(data['metadata']['creation_date']),
            modification_date=datetime.fromisoformat(data['metadata']['modification_date']),
            page_count=data['metadata']['page_count'],
            author=data['metadata'].get('author', ''),
            title=data['metadata'].get('title', ''),
            subject=data['metadata'].get('subject', ''),
            keywords=data['metadata'].get('keywords', []),
            language=data['metadata'].get('language', 'en')
        )
        
        return cls(
            id=data['id'],
            metadata=metadata,
            document_type=DocumentType(data['document_type']),
            processing_status=ProcessingStatus(data['processing_status']),
            processing_config=ProcessingConfiguration(),
            quality_level=QualityLevel(data['quality_level']),
            quality_score=data['quality_score'],
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            tags=data.get('tags', []),
            custom_metadata=data.get('custom_metadata', {})
        )


@dataclass
class DocumentChunk:
    """Represents a chunk of document content."""
    id: str
    document_id: str
    chunk_index: int
    content: str
    content_type: str  # 'text', 'table', 'image_caption'
    page_number: int
    bbox: Optional[tuple] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    embedding_model: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at)
    
    def has_embedding(self) -> bool:
        """Check if chunk has embedding."""
        return self.embedding is not None and len(self.embedding) > 0
    
    def get_word_count(self) -> int:
        """Get word count of content."""
        return len(self.content.split())
    
    def get_char_count(self) -> int:
        """Get character count of content."""
        return len(self.content)


@dataclass
class DocumentCollection:
    """Collection of related documents."""
    id: str
    name: str
    description: str
    documents: List[str] = field(default_factory=list)  # Document IDs
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at)
        if isinstance(self.updated_at, str):
            self.updated_at = datetime.fromisoformat(self.updated_at)
    
    def add_document(self, document_id: str):
        """Add document to collection."""
        if document_id not in self.documents:
            self.documents.append(document_id)
            self.updated_at = datetime.now()
    
    def remove_document(self, document_id: str):
        """Remove document from collection."""
        if document_id in self.documents:
            self.documents.remove(document_id)
            self.updated_at = datetime.now()
    
    def get_document_count(self) -> int:
        """Get number of documents in collection."""
        return len(self.documents)


@dataclass
class DocumentVersion:
    """Version information for document."""
    id: str
    document_id: str
    version_number: int
    created_at: datetime
    created_by: str
    changes: List[str] = field(default_factory=list)
    snapshot_data: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at)


@dataclass
class DocumentAnnotation:
    """Annotation on document content."""
    id: str
    document_id: str
    page_number: int
    bbox: tuple
    annotation_type: str  # 'note', 'correction', 'highlight', 'question'
    content: str
    created_by: str
    created_at: datetime = field(default_factory=datetime.now)
    resolved: bool = False
    resolved_by: str = ""
    resolved_at: Optional[datetime] = None
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at)
        if isinstance(self.resolved_at, str):
            self.resolved_at = datetime.fromisoformat(self.resolved_at)
    
    def resolve(self, resolved_by: str):
        """Mark annotation as resolved."""
        self.resolved = True
        self.resolved_by = resolved_by
        self.resolved_at = datetime.now()


# Type aliases for convenience
DocumentID = str
ChunkID = str
CollectionID = str
AnnotationID = str