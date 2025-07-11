#!/usr/bin/env python3
"""
Data models for manual validation workflow.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum
import uuid


class SnippetType(Enum):
    """Types of document snippets that can be classified."""
    IMAGE = "IMAGE"
    TABLE = "TABLE"
    DIAGRAM = "DIAGRAM"


class ValidationStatus(Enum):
    """Status of manual validation process."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SnippetMetadata:
    """Metadata for a classified snippet."""
    snippet_id: str
    snippet_type: SnippetType
    user_name: str = ""
    confidence: float = 1.0
    description: str = ""  # Auto-generated description for LLM
    context_text: str = ""  # Surrounding text for better understanding
    processing_notes: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at)
        if isinstance(self.updated_at, str):
            self.updated_at = datetime.fromisoformat(self.updated_at)
        if isinstance(self.snippet_type, str):
            self.snippet_type = SnippetType(self.snippet_type)


@dataclass
class SnippetLocation:
    """Location information for a snippet."""
    page: int
    bbox: List[float]  # [x1, y1, x2, y2] in PDF coordinates
    ui_coordinates: Dict[str, float] = field(default_factory=dict)  # For UI display
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'page': self.page,
            'bbox': self.bbox,
            'ui_coordinates': self.ui_coordinates
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SnippetLocation':
        """Create from dictionary."""
        return cls(
            page=data['page'],
            bbox=data['bbox'],
            ui_coordinates=data.get('ui_coordinates', {})
        )


@dataclass
class DocumentSnippet:
    """A classified snippet from manual validation."""
    id: str
    snippet_type: SnippetType
    location: SnippetLocation
    metadata: SnippetMetadata
    image_file: Optional[str] = None  # Path to extracted image file
    raw_data: Optional[bytes] = None  # Raw image data if needed
    
    def __post_init__(self):
        if isinstance(self.snippet_type, str):
            self.snippet_type = SnippetType(self.snippet_type)
        if isinstance(self.location, dict):
            self.location = SnippetLocation.from_dict(self.location)
        if isinstance(self.metadata, dict):
            self.metadata = SnippetMetadata(**self.metadata)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'type': self.snippet_type.value,
            'location': self.location.to_dict(),
            'metadata': {
                'snippet_id': self.metadata.snippet_id,
                'snippet_type': self.metadata.snippet_type.value,
                'user_name': self.metadata.user_name,
                'confidence': self.metadata.confidence,
                'description': self.metadata.description,
                'context_text': self.metadata.context_text,
                'processing_notes': self.metadata.processing_notes,
                'created_at': self.metadata.created_at.isoformat(),
                'updated_at': self.metadata.updated_at.isoformat()
            },
            'image_file': self.image_file
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DocumentSnippet':
        """Create from dictionary."""
        return cls(
            id=data['id'],
            snippet_type=SnippetType(data['type']),
            location=SnippetLocation.from_dict(data['location']),
            metadata=SnippetMetadata(**data['metadata']),
            image_file=data.get('image_file')
        )


@dataclass
class PageValidationResult:
    """Result of validating a single page."""
    page_number: int
    snippets: List[DocumentSnippet] = field(default_factory=list)
    validation_completed: bool = False
    validation_time: datetime = field(default_factory=datetime.now)
    validator_notes: str = ""
    
    def __post_init__(self):
        if isinstance(self.validation_time, str):
            self.validation_time = datetime.fromisoformat(self.validation_time)
    
    def get_snippets_by_type(self, snippet_type: SnippetType) -> List[DocumentSnippet]:
        """Get snippets of a specific type."""
        return [snippet for snippet in self.snippets if snippet.snippet_type == snippet_type]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'page_number': self.page_number,
            'snippets': [snippet.to_dict() for snippet in self.snippets],
            'validation_completed': self.validation_completed,
            'validation_time': self.validation_time.isoformat(),
            'validator_notes': self.validator_notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PageValidationResult':
        """Create from dictionary."""
        return cls(
            page_number=data['page_number'],
            snippets=[DocumentSnippet.from_dict(s) for s in data['snippets']],
            validation_completed=data['validation_completed'],
            validation_time=datetime.fromisoformat(data['validation_time']),
            validator_notes=data.get('validator_notes', '')
        )


@dataclass
class ManualValidationSession:
    """Complete manual validation session for a document."""
    document_id: str
    document_path: str
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: ValidationStatus = ValidationStatus.PENDING
    validator_id: str = ""
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    page_results: Dict[int, PageValidationResult] = field(default_factory=dict)
    total_pages: int = 0
    validated_pages: List[int] = field(default_factory=list)
    
    def __post_init__(self):
        if isinstance(self.status, str):
            self.status = ValidationStatus(self.status)
        if isinstance(self.started_at, str):
            self.started_at = datetime.fromisoformat(self.started_at)
        if self.completed_at and isinstance(self.completed_at, str):
            self.completed_at = datetime.fromisoformat(self.completed_at)
    
    def add_page_result(self, page_result: PageValidationResult):
        """Add a page validation result."""
        self.page_results[page_result.page_number] = page_result
        if page_result.page_number not in self.validated_pages:
            self.validated_pages.append(page_result.page_number)
            self.validated_pages.sort()
    
    def get_all_snippets(self) -> List[DocumentSnippet]:
        """Get all snippets from all pages."""
        all_snippets = []
        for page_result in self.page_results.values():
            all_snippets.extend(page_result.snippets)
        return all_snippets
    
    def get_snippets_by_type(self, snippet_type: SnippetType) -> List[DocumentSnippet]:
        """Get all snippets of a specific type."""
        return [snippet for snippet in self.get_all_snippets() 
                if snippet.snippet_type == snippet_type]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get validation statistics."""
        all_snippets = self.get_all_snippets()
        
        type_counts = {
            'IMAGE': len(self.get_snippets_by_type(SnippetType.IMAGE)),
            'TABLE': len(self.get_snippets_by_type(SnippetType.TABLE)),
            'DIAGRAM': len(self.get_snippets_by_type(SnippetType.DIAGRAM))
        }
        
        return {
            'total_snippets': len(all_snippets),
            'total_pages': self.total_pages,
            'validated_pages': len(self.validated_pages),
            'pages_with_snippets': len(self.page_results),
            'type_counts': type_counts,
            'completion_percentage': (len(self.validated_pages) / max(self.total_pages, 1)) * 100
        }
    
    def mark_completed(self):
        """Mark the validation session as completed."""
        self.status = ValidationStatus.COMPLETED
        self.completed_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'document_id': self.document_id,
            'document_path': self.document_path,
            'session_id': self.session_id,
            'status': self.status.value,
            'validator_id': self.validator_id,
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'page_results': {
                str(page_num): result.to_dict() 
                for page_num, result in self.page_results.items()
            },
            'total_pages': self.total_pages,
            'validated_pages': self.validated_pages,
            'statistics': self.get_statistics()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ManualValidationSession':
        """Create from dictionary."""
        session = cls(
            document_id=data['document_id'],
            document_path=data['document_path'],
            session_id=data['session_id'],
            status=ValidationStatus(data['status']),
            validator_id=data.get('validator_id', ''),
            started_at=datetime.fromisoformat(data['started_at']),
            completed_at=datetime.fromisoformat(data['completed_at']) if data.get('completed_at') else None,
            total_pages=data['total_pages'],
            validated_pages=data['validated_pages']
        )
        
        # Load page results
        for page_num_str, result_data in data.get('page_results', {}).items():
            page_num = int(page_num_str)
            session.page_results[page_num] = PageValidationResult.from_dict(result_data)
        
        return session


@dataclass
class ManualValidationConfig:
    """Configuration for manual validation process."""
    require_all_pages: bool = False  # Require validation of all pages
    min_snippet_size: int = 100  # Minimum size for snippets in pixels
    auto_save_interval: int = 300  # Auto-save interval in seconds
    snippet_image_format: str = "PNG"  # Format for extracted snippet images
    snippet_image_quality: int = 95  # Quality for extracted images
    enable_context_extraction: bool = True  # Extract surrounding text for context
    context_window_size: int = 200  # Characters around snippet for context
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'require_all_pages': self.require_all_pages,
            'min_snippet_size': self.min_snippet_size,
            'auto_save_interval': self.auto_save_interval,
            'snippet_image_format': self.snippet_image_format,
            'snippet_image_quality': self.snippet_image_quality,
            'enable_context_extraction': self.enable_context_extraction,
            'context_window_size': self.context_window_size
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ManualValidationConfig':
        """Create from dictionary."""
        return cls(**data)


# LLM-compatible metadata schemas
def get_llm_snippet_schema() -> Dict[str, Any]:
    """Get LLM-compatible schema for snippet metadata."""
    return {
        "snippet_id": "string",
        "type": "enum[IMAGE, TABLE, DIAGRAM]",
        "description": "string",
        "context": "string",
        "location": {
            "page": "integer",
            "bbox": "array[float]",
            "coordinates": "object"
        },
        "metadata": {
            "user_name": "string",
            "confidence": "float",
            "created_at": "datetime",
            "processing_notes": "string"
        },
        "image_file": "string"
    }


def convert_snippet_to_llm_format(snippet: DocumentSnippet) -> Dict[str, Any]:
    """Convert a snippet to LLM-compatible format."""
    return {
        "snippet_id": snippet.id,
        "type": snippet.snippet_type.value,
        "description": snippet.metadata.description,
        "context": snippet.metadata.context_text,
        "location": {
            "page": snippet.location.page,
            "bbox": snippet.location.bbox,
            "coordinates": snippet.location.ui_coordinates
        },
        "metadata": {
            "user_name": snippet.metadata.user_name,
            "confidence": snippet.metadata.confidence,
            "created_at": snippet.metadata.created_at.isoformat(),
            "processing_notes": snippet.metadata.processing_notes
        },
        "image_file": snippet.image_file
    }


def convert_session_to_llm_format(session: ManualValidationSession) -> Dict[str, Any]:
    """Convert a validation session to LLM-compatible format."""
    return {
        "document_id": session.document_id,
        "document_path": session.document_path,
        "validation_status": session.status.value,
        "statistics": session.get_statistics(),
        "snippets": [convert_snippet_to_llm_format(snippet) for snippet in session.get_all_snippets()],
        "snippets_by_type": {
            "images": [convert_snippet_to_llm_format(snippet) 
                      for snippet in session.get_snippets_by_type(SnippetType.IMAGE)],
            "tables": [convert_snippet_to_llm_format(snippet) 
                      for snippet in session.get_snippets_by_type(SnippetType.TABLE)],
            "diagrams": [convert_snippet_to_llm_format(snippet) 
                        for snippet in session.get_snippets_by_type(SnippetType.DIAGRAM)]
        }
    }