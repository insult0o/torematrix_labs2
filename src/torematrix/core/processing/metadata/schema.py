"""Metadata schema definitions with comprehensive validation."""

from typing import Dict, List, Optional, Any, Union, Literal
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator, computed_field
import uuid

from .types import (
    MetadataType, LanguageCode, EncodingType, ExtractionMethod,
    ConfidenceLevel, MetadataValidationResult, ExtractionContext
)


class BaseMetadata(BaseModel):
    """Base metadata model with common fields."""
    metadata_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    metadata_type: MetadataType
    extraction_timestamp: datetime = Field(default_factory=datetime.utcnow)
    confidence_score: float = Field(ge=0.0, le=1.0)
    source_extractor: str
    extraction_method: ExtractionMethod
    validation_result: Optional[MetadataValidationResult] = None
    custom_fields: Dict[str, Any] = Field(default_factory=dict)
    
    @computed_field
    @property
    def confidence_level(self) -> ConfidenceLevel:
        """Compute confidence level from confidence score."""
        if self.confidence_score >= 0.95:
            return ConfidenceLevel.VERY_HIGH
        elif self.confidence_score >= 0.85:
            return ConfidenceLevel.HIGH
        elif self.confidence_score >= 0.70:
            return ConfidenceLevel.MEDIUM
        elif self.confidence_score >= 0.50:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW
    
    model_config = {"arbitrary_types_allowed": True}


class DocumentMetadata(BaseMetadata):
    """Document-level metadata with comprehensive properties."""
    metadata_type: Literal[MetadataType.DOCUMENT] = MetadataType.DOCUMENT
    
    # Core document properties
    title: Optional[str] = None
    author: Optional[str] = None
    subject: Optional[str] = None
    creator: Optional[str] = None
    producer: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    
    # Document dates
    creation_date: Optional[datetime] = None
    modification_date: Optional[datetime] = None
    metadata_date: Optional[datetime] = None
    
    # Language and encoding
    language: LanguageCode = LanguageCode.UNKNOWN
    language_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    encoding: EncodingType = EncodingType.UTF8
    encoding_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Document structure
    page_count: int = Field(default=0, ge=0)
    total_elements: int = Field(default=0, ge=0)
    total_words: Optional[int] = Field(default=None, ge=0)
    total_characters: Optional[int] = Field(default=None, ge=0)
    
    # File properties
    file_size_bytes: Optional[int] = Field(default=None, ge=0)
    file_format: Optional[str] = None
    file_version: Optional[str] = None
    file_properties: Dict[str, Any] = Field(default_factory=dict)
    
    # Security properties
    is_encrypted: bool = False
    has_digital_signature: bool = False
    permissions: Dict[str, bool] = Field(default_factory=dict)
    
    # Quality metrics
    text_quality_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    structure_quality_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    overall_quality_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    
    @field_validator('page_count')
    @classmethod
    def validate_page_count(cls, v):
        if v < 0:
            raise ValueError('Page count cannot be negative')
        return v
    
    @model_validator(mode='after')
    def validate_document_consistency(self):
        """Validate document metadata consistency."""
        if self.page_count > 0 and self.total_elements == 0:
            self.total_elements = 1  # At least one element per page
            
        return self


class PageMetadata(BaseMetadata):
    """Page-level metadata with layout and content properties."""
    metadata_type: Literal[MetadataType.PAGE] = MetadataType.PAGE
    
    # Page identification
    page_number: int = Field(ge=1)
    document_id: str
    
    # Page dimensions
    width: Optional[float] = Field(default=None, gt=0)
    height: Optional[float] = Field(default=None, gt=0)
    rotation: float = Field(default=0.0, ge=0.0, lt=360.0)
    
    # Content metrics
    element_count: int = Field(default=0, ge=0)
    text_element_count: int = Field(default=0, ge=0)
    image_element_count: int = Field(default=0, ge=0)
    table_element_count: int = Field(default=0, ge=0)
    
    # Text properties
    word_count: Optional[int] = Field(default=None, ge=0)
    character_count: Optional[int] = Field(default=None, ge=0)
    paragraph_count: Optional[int] = Field(default=None, ge=0)
    
    # Layout properties
    column_count: Optional[int] = Field(default=None, ge=1)
    has_header: bool = False
    has_footer: bool = False
    has_margin_notes: bool = False
    
    # Quality metrics
    text_clarity_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    layout_quality_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    ocr_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    
    @field_validator('page_number')
    @classmethod
    def validate_page_number(cls, v):
        if v < 1:
            raise ValueError('Page number must be at least 1')
        return v


class ElementMetadata(BaseMetadata):
    """Element-level metadata for document components."""
    metadata_type: Literal[MetadataType.ELEMENT] = MetadataType.ELEMENT
    
    # Element identification
    element_id: str
    element_type: str
    page_number: int = Field(ge=1)
    document_id: str
    
    # Position and layout
    bbox: Optional[List[float]] = None  # [x1, y1, x2, y2]
    reading_order: Optional[int] = Field(default=None, ge=0)
    column_index: Optional[int] = Field(default=None, ge=0)
    
    # Content properties
    text_content: Optional[str] = None
    text_length: Optional[int] = Field(default=None, ge=0)
    word_count: Optional[int] = Field(default=None, ge=0)
    
    # Semantic properties
    semantic_role: Optional[str] = None
    heading_level: Optional[int] = Field(default=None, ge=1, le=6)
    list_item_level: Optional[int] = Field(default=None, ge=0)
    
    # Formatting properties
    font_name: Optional[str] = None
    font_size: Optional[float] = Field(default=None, gt=0)
    is_bold: bool = False
    is_italic: bool = False
    is_underlined: bool = False
    text_color: Optional[str] = None
    
    # Quality and confidence
    extraction_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    ocr_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    
    @field_validator('bbox')
    @classmethod
    def validate_bbox(cls, v):
        if v is not None and len(v) != 4:
            raise ValueError('Bounding box must contain exactly 4 coordinates')
        return v


class RelationshipMetadata(BaseMetadata):
    """Relationship metadata between document elements."""
    metadata_type: Literal[MetadataType.RELATIONSHIP] = MetadataType.RELATIONSHIP
    
    # Relationship identification
    source_element_id: str
    target_element_id: str
    relationship_type: str
    relationship_strength: float = Field(default=1.0, ge=0.0, le=1.0)
    
    # Spatial relationships
    spatial_relationship: Optional[str] = None
    distance: Optional[float] = Field(default=None, ge=0.0)
    
    # Semantic relationships
    semantic_relationship: Optional[str] = None
    context_similarity: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    
    # Directional properties
    is_bidirectional: bool = False
    reading_flow_direction: Optional[str] = None
    
    # Quality metrics
    detection_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    validation_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class MetadataSchema(BaseModel):
    """Complete metadata schema container."""
    schema_version: str = "1.0.0"
    document_metadata: Optional[DocumentMetadata] = None
    page_metadata: List[PageMetadata] = Field(default_factory=list)
    element_metadata: List[ElementMetadata] = Field(default_factory=list)
    relationship_metadata: List[RelationshipMetadata] = Field(default_factory=list)
    extraction_context: Optional[ExtractionContext] = None
    
    # Schema-level metrics
    total_confidence_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    completeness_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    consistency_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    
    @model_validator(mode='after')
    def validate_schema_consistency(self):
        """Validate cross-metadata consistency."""
        if self.document_metadata and self.page_metadata:
            # Validate page count consistency
            if self.document_metadata.page_count != len(self.page_metadata):
                self.document_metadata.page_count = len(self.page_metadata)
        
        if self.document_metadata and self.element_metadata:
            # Validate element count consistency
            if self.document_metadata.total_elements != len(self.element_metadata):
                self.document_metadata.total_elements = len(self.element_metadata)
                
        return self
    
    def calculate_overall_confidence(self) -> float:
        """Calculate overall confidence score across all metadata."""
        scores = []
        
        if self.document_metadata:
            scores.append(self.document_metadata.confidence_score)
            
        for page_meta in self.page_metadata:
            scores.append(page_meta.confidence_score)
            
        for element_meta in self.element_metadata:
            scores.append(element_meta.confidence_score)
            
        for rel_meta in self.relationship_metadata:
            scores.append(rel_meta.confidence_score)
            
        return sum(scores) / len(scores) if scores else 0.0
    
    def get_metadata_summary(self) -> Dict[str, Any]:
        """Get summary statistics for the metadata schema."""
        return {
            "schema_version": self.schema_version,
            "has_document_metadata": self.document_metadata is not None,
            "page_count": len(self.page_metadata),
            "element_count": len(self.element_metadata),
            "relationship_count": len(self.relationship_metadata),
            "overall_confidence": self.calculate_overall_confidence(),
            "completeness_score": self.completeness_score,
            "consistency_score": self.consistency_score
        }