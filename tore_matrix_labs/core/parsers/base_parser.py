"""
Base Parser Classes for TORE Matrix Labs Document Processing

This module defines the abstract base classes and core data structures
for the document parsing framework.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple

from ...models.document_models import (
    Document,
    ProcessingStatus,
    DocumentMetadata
)


logger = logging.getLogger(__name__)


class ParsingStrategy(Enum):
    """Available parsing strategies"""
    PYMUPDF = "pymupdf"
    UNSTRUCTURED = "unstructured"
    OCR = "ocr"
    HYBRID = "hybrid"
    AUTO = "auto"


class ElementConfidence(Enum):
    """Confidence levels for parsed elements"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


@dataclass
class ParserConfiguration:
    """Configuration for document parsing"""
    strategy: ParsingStrategy = ParsingStrategy.AUTO
    enable_ocr: bool = True
    ocr_languages: List[str] = field(default_factory=lambda: ["eng"])
    extract_tables: bool = True
    extract_images: bool = True
    extract_metadata: bool = True
    preserve_formatting: bool = True
    chunk_size: int = 1000
    overlap_size: int = 200
    quality_threshold: float = 0.8
    timeout_seconds: Optional[int] = None
    custom_options: Dict[str, Any] = field(default_factory=dict)
    
    def merge(self, other: 'ParserConfiguration') -> 'ParserConfiguration':
        """Merge two configurations, with other taking precedence"""
        merged = ParserConfiguration()
        for field_name in self.__dataclass_fields__:
            other_value = getattr(other, field_name)
            if other_value is not None and other_value != getattr(ParserConfiguration(), field_name):
                setattr(merged, field_name, other_value)
            else:
                setattr(merged, field_name, getattr(self, field_name))
        return merged


@dataclass
class ParseQuality:
    """Quality metrics for parsing results"""
    overall_score: float
    text_extraction_score: float
    structure_preservation_score: float
    element_detection_score: float
    metadata_completeness: float
    confidence_distribution: Dict[ElementConfidence, int]
    issues_found: List[Dict[str, Any]]
    processing_time: float
    
    @property
    def is_acceptable(self) -> bool:
        """Check if quality meets minimum standards"""
        return self.overall_score >= 0.7
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'overall_score': self.overall_score,
            'text_extraction_score': self.text_extraction_score,
            'structure_preservation_score': self.structure_preservation_score,
            'element_detection_score': self.element_detection_score,
            'metadata_completeness': self.metadata_completeness,
            'confidence_distribution': {k.value: v for k, v in self.confidence_distribution.items()},
            'issues_found': self.issues_found,
            'processing_time': self.processing_time
        }


@dataclass
class ParseResult:
    """Result of document parsing operation"""
    success: bool
    document: Optional[Document] = None
    elements: List['ParsedElement'] = field(default_factory=list)
    metadata: Optional[DocumentMetadata] = None
    quality: Optional[ParseQuality] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    strategy_used: Optional[ParsingStrategy] = None
    processing_time: float = 0.0
    
    def add_error(self, error: str) -> None:
        """Add an error message"""
        self.errors.append(error)
        self.success = False
    
    def add_warning(self, warning: str) -> None:
        """Add a warning message"""
        self.warnings.append(warning)
    
    def get_elements_by_type(self, element_type: str) -> List['ParsedElement']:
        """Get all elements of a specific type"""
        return [e for e in self.elements if e.element_type == element_type]


class BaseDocumentParser(ABC):
    """Abstract base class for document parsers"""
    
    def __init__(self, config: Optional[ParserConfiguration] = None):
        """Initialize parser with configuration"""
        self.config = config or ParserConfiguration()
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def parse(self, file_path: Path) -> ParseResult:
        """
        Parse a document file and extract its content and structure
        
        Args:
            file_path: Path to the document file
            
        Returns:
            ParseResult containing parsed document and metadata
        """
        pass
    
    @abstractmethod
    def supports_format(self, file_path: Path) -> bool:
        """
        Check if this parser supports the given file format
        
        Args:
            file_path: Path to check
            
        Returns:
            True if format is supported
        """
        pass
    
    @abstractmethod
    def get_strategy(self) -> ParsingStrategy:
        """Get the parsing strategy used by this parser"""
        pass
    
    def validate_file(self, file_path: Path) -> Tuple[bool, Optional[str]]:
        """
        Validate that file exists and is readable
        
        Args:
            file_path: Path to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not file_path.exists():
            return False, f"File not found: {file_path}"
        
        if not file_path.is_file():
            return False, f"Not a file: {file_path}"
        
        if not self.supports_format(file_path):
            return False, f"Unsupported format: {file_path.suffix}"
        
        try:
            with open(file_path, 'rb') as f:
                f.read(1)
            return True, None
        except Exception as e:
            return False, f"File not readable: {str(e)}"
    
    def preprocess(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Optional preprocessing step before parsing
        
        Args:
            file_path: Path to preprocess
            
        Returns:
            Preprocessing results or None
        """
        return None
    
    def postprocess(self, result: ParseResult) -> ParseResult:
        """
        Optional postprocessing step after parsing
        
        Args:
            result: Initial parse result
            
        Returns:
            Processed parse result
        """
        return result
    
    def extract_metadata(self, file_path: Path) -> Optional[DocumentMetadata]:
        """
        Extract document metadata
        
        Args:
            file_path: Path to document
            
        Returns:
            Document metadata or None
        """
        try:
            stat = file_path.stat()
            return DocumentMetadata(
                filename=file_path.name,
                file_size=stat.st_size,
                created_date=datetime.fromtimestamp(stat.st_ctime),
                modified_date=datetime.fromtimestamp(stat.st_mtime),
                format=file_path.suffix.lstrip('.')
            )
        except Exception as e:
            self.logger.error(f"Failed to extract metadata: {e}")
            return None


class BaseElementParser(ABC):
    """Abstract base class for parsing specific element types"""
    
    def __init__(self):
        """Initialize element parser"""
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def parse_element(self, raw_data: Any) -> Optional['ParsedElement']:
        """
        Parse raw element data into a ParsedElement
        
        Args:
            raw_data: Raw element data from document
            
        Returns:
            Parsed element or None if parsing fails
        """
        pass
    
    @abstractmethod
    def supports_element_type(self, element_type: str) -> bool:
        """
        Check if this parser supports the given element type
        
        Args:
            element_type: Type to check
            
        Returns:
            True if type is supported
        """
        pass
    
    def validate_element(self, element: 'ParsedElement') -> Tuple[bool, Optional[str]]:
        """
        Validate a parsed element
        
        Args:
            element: Element to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not element.content:
            return False, "Element has no content"
        
        if element.confidence == ElementConfidence.LOW:
            return True, "Low confidence element"
        
        return True, None