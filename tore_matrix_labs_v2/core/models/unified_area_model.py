#!/usr/bin/env python3
"""
Unified Area Model for TORE Matrix Labs V2

This model represents visual areas within documents, consolidating the
scattered area handling from the original codebase into a single, clean model.

Key features:
- Unified area representation across all document types
- Coordinate normalization and validation
- Area classification and status tracking
- Integration with document processing pipeline
- Optimized for performance and memory usage
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from enum import Enum
from datetime import datetime
import json


class AreaType(Enum):
    """Types of visual areas in documents."""
    
    # Content types
    TEXT = "text"
    IMAGE = "image"
    TABLE = "table"
    DIAGRAM = "diagram"
    CHART = "chart"
    FIGURE = "figure"
    
    # Layout types
    HEADER = "header"
    FOOTER = "footer"
    MARGIN = "margin"
    COLUMN = "column"
    
    # Special types
    ANNOTATION = "annotation"
    SIGNATURE = "signature"
    STAMP = "stamp"
    WATERMARK = "watermark"
    
    # Unknown/unclassified
    UNKNOWN = "unknown"


class AreaStatus(Enum):
    """Status of area processing and validation."""
    
    # Processing states
    CREATED = "created"
    EXTRACTING = "extracting"
    EXTRACTED = "extracted"
    PROCESSING = "processing"
    PROCESSED = "processed"
    
    # Validation states
    VALIDATING = "validating"
    VALIDATED = "validated"
    APPROVED = "approved"
    REJECTED = "rejected"
    
    # Modification states
    MODIFIED = "modified"
    CORRECTED = "corrected"
    
    # Error states
    FAILED = "failed"
    ERROR = "error"


@dataclass
class AreaCoordinates:
    """Normalized coordinates for an area."""
    
    # Bounding box coordinates (PDF coordinate system)
    x0: float
    y0: float
    x1: float
    y1: float
    
    # Page information
    page: int
    
    # Additional coordinate metadata
    width: Optional[float] = None
    height: Optional[float] = None
    rotation: float = 0.0
    
    # Confidence and quality metrics
    confidence: float = 1.0
    quality: float = 1.0
    
    def __post_init__(self):
        """Validate and normalize coordinates."""
        # Calculate width and height if not provided
        if self.width is None:
            self.width = abs(self.x1 - self.x0)
        if self.height is None:
            self.height = abs(self.y1 - self.y0)
        
        # Ensure coordinates are ordered correctly
        if self.x0 > self.x1:
            self.x0, self.x1 = self.x1, self.x0
        if self.y0 > self.y1:
            self.y0, self.y1 = self.y1, self.y0
    
    @property
    def bbox(self) -> Tuple[float, float, float, float]:
        """Get coordinates as bounding box tuple."""
        return (self.x0, self.y0, self.x1, self.y1)
    
    @property
    def center(self) -> Tuple[float, float]:
        """Get center point of the area."""
        return ((self.x0 + self.x1) / 2, (self.y0 + self.y1) / 2)
    
    @property
    def area(self) -> float:
        """Calculate area in square points."""
        return self.width * self.height
    
    def contains_point(self, x: float, y: float) -> bool:
        """Check if point is within this area."""
        return (self.x0 <= x <= self.x1) and (self.y0 <= y <= self.y1)
    
    def intersects(self, other: 'AreaCoordinates') -> bool:
        """Check if this area intersects with another."""
        if self.page != other.page:
            return False
        
        return not (self.x1 < other.x0 or self.x0 > other.x1 or
                   self.y1 < other.y0 or self.y0 > other.y1)
    
    def intersection_area(self, other: 'AreaCoordinates') -> float:
        """Calculate intersection area with another area."""
        if not self.intersects(other):
            return 0.0
        
        x_overlap = min(self.x1, other.x1) - max(self.x0, other.x0)
        y_overlap = min(self.y1, other.y1) - max(self.y0, other.y0)
        
        return x_overlap * y_overlap
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "x0": self.x0,
            "y0": self.y0,
            "x1": self.x1,
            "y1": self.y1,
            "page": self.page,
            "width": self.width,
            "height": self.height,
            "rotation": self.rotation,
            "confidence": self.confidence,
            "quality": self.quality
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AreaCoordinates':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class AreaContent:
    """Content extracted from an area."""
    
    # Raw content
    raw_text: str = ""
    processed_text: str = ""
    
    # Structured content
    tables: List[Dict[str, Any]] = field(default_factory=list)
    images: List[Dict[str, Any]] = field(default_factory=list)
    
    # Formatting information
    fonts: List[Dict[str, Any]] = field(default_factory=list)
    styles: Dict[str, Any] = field(default_factory=dict)
    
    # Content metadata
    language: Optional[str] = None
    encoding: Optional[str] = None
    
    # Quality metrics
    extraction_confidence: float = 1.0
    ocr_confidence: float = 1.0
    
    def __post_init__(self):
        """Validate content data."""
        # Ensure processed_text is set
        if not self.processed_text and self.raw_text:
            self.processed_text = self.raw_text.strip()
    
    @property
    def is_empty(self) -> bool:
        """Check if content is empty."""
        return not (self.raw_text or self.processed_text or 
                   self.tables or self.images)
    
    @property
    def word_count(self) -> int:
        """Count words in processed text."""
        if not self.processed_text:
            return 0
        return len(self.processed_text.split())
    
    @property
    def character_count(self) -> int:
        """Count characters in processed text."""
        return len(self.processed_text) if self.processed_text else 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "raw_text": self.raw_text,
            "processed_text": self.processed_text,
            "tables": self.tables,
            "images": self.images,
            "fonts": self.fonts,
            "styles": self.styles,
            "language": self.language,
            "encoding": self.encoding,
            "extraction_confidence": self.extraction_confidence,
            "ocr_confidence": self.ocr_confidence
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AreaContent':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class AreaValidation:
    """Validation results for an area."""
    
    # Validation status
    is_validated: bool = False
    is_approved: bool = False
    requires_review: bool = False
    
    # Issues found
    issues: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Quality scores
    content_quality: float = 1.0
    coordinate_quality: float = 1.0
    overall_quality: float = 1.0
    
    # Validation metadata
    validated_by: Optional[str] = None
    validated_at: Optional[datetime] = None
    validation_notes: str = ""
    
    # Corrections applied
    corrections: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_issue(self, issue_type: str, description: str, severity: str = "medium"):
        """Add a validation issue."""
        issue = {
            "type": issue_type,
            "description": description,
            "severity": severity,
            "detected_at": datetime.now().isoformat()
        }
        self.issues.append(issue)
        
        # Mark as requiring review for high severity issues
        if severity in ["high", "critical"]:
            self.requires_review = True
    
    def add_correction(self, correction_type: str, original_value: Any, 
                      corrected_value: Any, reason: str = ""):
        """Add a correction record."""
        correction = {
            "type": correction_type,
            "original_value": original_value,
            "corrected_value": corrected_value,
            "reason": reason,
            "applied_at": datetime.now().isoformat()
        }
        self.corrections.append(correction)
    
    @property
    def has_issues(self) -> bool:
        """Check if there are any validation issues."""
        return len(self.issues) > 0
    
    @property
    def critical_issues(self) -> List[Dict[str, Any]]:
        """Get critical issues only."""
        return [issue for issue in self.issues if issue["severity"] == "critical"]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "is_validated": self.is_validated,
            "is_approved": self.is_approved,
            "requires_review": self.requires_review,
            "issues": self.issues,
            "warnings": self.warnings,
            "content_quality": self.content_quality,
            "coordinate_quality": self.coordinate_quality,
            "overall_quality": self.overall_quality,
            "validated_by": self.validated_by,
            "validated_at": self.validated_at.isoformat() if self.validated_at else None,
            "validation_notes": self.validation_notes,
            "corrections": self.corrections
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AreaValidation':
        """Create from dictionary."""
        # Handle datetime conversion
        if data.get("validated_at"):
            data["validated_at"] = datetime.fromisoformat(data["validated_at"])
        
        return cls(**data)


@dataclass
class UnifiedArea:
    """
    Unified area model representing visual areas in documents.
    
    This consolidates all area handling from the original codebase
    into a single, clean model with proper separation of concerns.
    """
    
    # Identity
    id: str
    document_id: str
    
    # Classification
    area_type: AreaType
    subtype: Optional[str] = None
    
    # Spatial information
    coordinates: AreaCoordinates = None
    
    # Content
    content: AreaContent = field(default_factory=AreaContent)
    
    # Processing state
    status: AreaStatus = AreaStatus.CREATED
    
    # Validation
    validation: AreaValidation = field(default_factory=AreaValidation)
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)
    
    # Processing metadata
    extraction_method: Optional[str] = None
    processing_time: float = 0.0
    
    # User interaction
    user_notes: str = ""
    user_tags: List[str] = field(default_factory=list)
    
    # Relationships
    parent_area_id: Optional[str] = None
    child_area_ids: List[str] = field(default_factory=list)
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize area after creation."""
        # Ensure coordinates are set
        if self.coordinates is None:
            self.coordinates = AreaCoordinates(0, 0, 0, 0, 1)
        
        # Update modified time
        self.modified_at = datetime.now()
    
    @property
    def is_valid(self) -> bool:
        """Check if area has valid data."""
        return (self.coordinates is not None and 
                self.coordinates.area > 0 and
                self.area_type != AreaType.UNKNOWN)
    
    @property
    def has_content(self) -> bool:
        """Check if area has extractable content."""
        return not self.content.is_empty
    
    @property
    def needs_validation(self) -> bool:
        """Check if area needs validation."""
        return (not self.validation.is_validated or 
                self.validation.requires_review or
                self.validation.has_issues)
    
    @property
    def is_processed(self) -> bool:
        """Check if area is fully processed."""
        return self.status in [AreaStatus.PROCESSED, AreaStatus.VALIDATED, 
                              AreaStatus.APPROVED]
    
    def update_status(self, new_status: AreaStatus):
        """Update area status and timestamp."""
        self.status = new_status
        self.modified_at = datetime.now()
    
    def add_child_area(self, child_area: 'UnifiedArea'):
        """Add a child area."""
        child_area.parent_area_id = self.id
        if child_area.id not in self.child_area_ids:
            self.child_area_ids.append(child_area.id)
        self.modified_at = datetime.now()
    
    def remove_child_area(self, child_area_id: str):
        """Remove a child area."""
        if child_area_id in self.child_area_ids:
            self.child_area_ids.remove(child_area_id)
            self.modified_at = datetime.now()
    
    def get_area_hierarchy(self) -> Dict[str, Any]:
        """Get area hierarchy information."""
        return {
            "id": self.id,
            "parent_id": self.parent_area_id,
            "child_ids": self.child_area_ids,
            "level": 0 if not self.parent_area_id else 1,  # Simplified
            "has_children": len(self.child_area_ids) > 0
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "document_id": self.document_id,
            "area_type": self.area_type.value,
            "subtype": self.subtype,
            "coordinates": self.coordinates.to_dict() if self.coordinates else None,
            "content": self.content.to_dict(),
            "status": self.status.value,
            "validation": self.validation.to_dict(),
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat(),
            "extraction_method": self.extraction_method,
            "processing_time": self.processing_time,
            "user_notes": self.user_notes,
            "user_tags": self.user_tags,
            "parent_area_id": self.parent_area_id,
            "child_area_ids": self.child_area_ids,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UnifiedArea':
        """Create from dictionary."""
        # Handle enum conversions
        if "area_type" in data:
            data["area_type"] = AreaType(data["area_type"])
        if "status" in data:
            data["status"] = AreaStatus(data["status"])
        
        # Handle datetime conversions
        if "created_at" in data:
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if "modified_at" in data:
            data["modified_at"] = datetime.fromisoformat(data["modified_at"])
        
        # Handle nested objects
        if "coordinates" in data and data["coordinates"]:
            data["coordinates"] = AreaCoordinates.from_dict(data["coordinates"])
        if "content" in data:
            data["content"] = AreaContent.from_dict(data["content"])
        if "validation" in data:
            data["validation"] = AreaValidation.from_dict(data["validation"])
        
        return cls(**data)
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'UnifiedArea':
        """Create from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def __str__(self) -> str:
        """String representation."""
        return f"UnifiedArea(id={self.id}, type={self.area_type.value}, status={self.status.value})"
    
    def __repr__(self) -> str:
        """Detailed representation."""
        return (f"UnifiedArea(id='{self.id}', document_id='{self.document_id}', "
                f"type={self.area_type.value}, status={self.status.value}, "
                f"coordinates={self.coordinates.bbox if self.coordinates else None})")


# Utility functions for area management
def create_text_area(document_id: str, area_id: str, 
                    coordinates: AreaCoordinates, text: str) -> UnifiedArea:
    """Create a text area with content."""
    content = AreaContent(raw_text=text, processed_text=text.strip())
    
    return UnifiedArea(
        id=area_id,
        document_id=document_id,
        area_type=AreaType.TEXT,
        coordinates=coordinates,
        content=content,
        status=AreaStatus.EXTRACTED
    )


def create_image_area(document_id: str, area_id: str, 
                     coordinates: AreaCoordinates, image_data: Dict[str, Any]) -> UnifiedArea:
    """Create an image area."""
    content = AreaContent(images=[image_data])
    
    return UnifiedArea(
        id=area_id,
        document_id=document_id,
        area_type=AreaType.IMAGE,
        coordinates=coordinates,
        content=content,
        status=AreaStatus.EXTRACTED
    )


def create_table_area(document_id: str, area_id: str, 
                     coordinates: AreaCoordinates, table_data: Dict[str, Any]) -> UnifiedArea:
    """Create a table area."""
    content = AreaContent(tables=[table_data])
    
    return UnifiedArea(
        id=area_id,
        document_id=document_id,
        area_type=AreaType.TABLE,
        coordinates=coordinates,
        content=content,
        status=AreaStatus.EXTRACTED
    )


def merge_areas(areas: List[UnifiedArea], merged_id: str) -> UnifiedArea:
    """Merge multiple areas into one."""
    if not areas:
        raise ValueError("Cannot merge empty list of areas")
    
    # Use first area as base
    base_area = areas[0]
    
    # Calculate merged coordinates
    min_x0 = min(area.coordinates.x0 for area in areas)
    min_y0 = min(area.coordinates.y0 for area in areas)
    max_x1 = max(area.coordinates.x1 for area in areas)
    max_y1 = max(area.coordinates.y1 for area in areas)
    
    merged_coordinates = AreaCoordinates(
        x0=min_x0, y0=min_y0, x1=max_x1, y1=max_y1,
        page=base_area.coordinates.page
    )
    
    # Merge content
    merged_content = AreaContent()
    for area in areas:
        if area.content.raw_text:
            merged_content.raw_text += area.content.raw_text + "\n"
        if area.content.processed_text:
            merged_content.processed_text += area.content.processed_text + "\n"
        merged_content.tables.extend(area.content.tables)
        merged_content.images.extend(area.content.images)
    
    # Clean up merged text
    merged_content.raw_text = merged_content.raw_text.strip()
    merged_content.processed_text = merged_content.processed_text.strip()
    
    # Create merged area
    merged_area = UnifiedArea(
        id=merged_id,
        document_id=base_area.document_id,
        area_type=base_area.area_type,
        coordinates=merged_coordinates,
        content=merged_content,
        status=AreaStatus.MODIFIED
    )
    
    # Set child relationships
    merged_area.child_area_ids = [area.id for area in areas]
    
    return merged_area