"""
Document structure analysis engine for TORE Matrix Labs.
"""

import logging
import time
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import fitz  # PyMuPDF
import pdfplumber
from dataclasses import dataclass
from enum import Enum

from ..config.constants import DocumentType, QualityLevel
from ..config.settings import Settings


class ElementType(Enum):
    """Document element types."""
    TEXT = "text"
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    TABLE = "table"
    IMAGE = "image"
    FIGURE = "figure"
    CAPTION = "caption"
    HEADER = "header"
    FOOTER = "footer"
    LIST = "list"
    QUOTE = "quote"
    CODE = "code"


@dataclass
class DocumentElement:
    """Represents a document element."""
    element_type: ElementType
    content: str
    bbox: Tuple[float, float, float, float]  # x0, y0, x1, y1
    page_number: int
    confidence: float
    metadata: Dict[str, Any]
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class PageAnalysis:
    """Analysis results for a single page."""
    page_number: int
    elements: List[DocumentElement]
    layout_type: str
    column_count: int
    has_tables: bool
    has_images: bool
    text_regions: List[Dict[str, Any]]
    reading_order: List[int]
    quality_score: float
    
    def __post_init__(self):
        if self.elements is None:
            self.elements = []
        if self.text_regions is None:
            self.text_regions = []
        if self.reading_order is None:
            self.reading_order = []


@dataclass
class DocumentAnalysis:
    """Complete document analysis results."""
    file_path: str
    document_type: DocumentType
    total_pages: int
    page_analyses: List[PageAnalysis]
    structure_hierarchy: Dict[str, Any]
    metadata: Dict[str, Any]
    overall_quality: QualityLevel
    processing_time: float
    
    def __post_init__(self):
        if self.page_analyses is None:
            self.page_analyses = []
        if self.structure_hierarchy is None:
            self.structure_hierarchy = {}
        if self.metadata is None:
            self.metadata = {}


class DocumentAnalyzer:
    """Main document analysis engine."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        self._init_processors()
    
    def _init_processors(self):
        """Initialize document processors."""
        self.processors = {
            'pymupdf': self._analyze_with_pymupdf,
            'pdfplumber': self._analyze_with_pdfplumber
        }
    
    def analyze_document(self, file_path: str) -> DocumentAnalysis:
        """
        Analyze document structure and content.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            DocumentAnalysis object with complete analysis
        """
        self.logger.info(f"Starting document analysis: {file_path}")
        
        start_time = time.time()
        
        try:
            # Basic file validation
            if not Path(file_path).exists():
                raise FileNotFoundError(f"Document not found: {file_path}")
            
            # Detect document type
            doc_type = self._detect_document_type(file_path)
            
            # Open document
            doc = fitz.open(file_path)
            
            # Analyze each page
            page_analyses = []
            for page_num in range(len(doc)):
                page_analysis = self._analyze_page(doc, page_num)
                page_analyses.append(page_analysis)
            
            # Build document structure
            structure_hierarchy = self._build_structure_hierarchy(page_analyses)
            
            # Extract metadata
            metadata = self._extract_metadata(doc, file_path)
            
            # Calculate overall quality
            overall_quality = self._calculate_overall_quality(page_analyses)
            
            processing_time = time.time() - start_time
            
            analysis = DocumentAnalysis(
                file_path=file_path,
                document_type=doc_type,
                total_pages=len(doc),
                page_analyses=page_analyses,
                structure_hierarchy=structure_hierarchy,
                metadata=metadata,
                overall_quality=overall_quality,
                processing_time=processing_time
            )
            
            doc.close()
            
            self.logger.info(f"Document analysis completed in {processing_time:.2f}s")
            return analysis
            
        except Exception as e:
            self.logger.error(f"Document analysis failed: {str(e)}")
            raise
    
    def _detect_document_type(self, file_path: str) -> DocumentType:
        """Detect document type based on content and metadata."""
        # Simple heuristic-based detection
        # In a real implementation, this would use ML classification
        
        file_name = Path(file_path).name.lower()
        
        if any(keyword in file_name for keyword in ['icao', 'aviation', 'aircraft']):
            return DocumentType.ICAO
        elif any(keyword in file_name for keyword in ['atc', 'air traffic', 'control']):
            return DocumentType.ATC
        elif any(keyword in file_name for keyword in ['regulation', 'compliance', 'standard']):
            return DocumentType.REGULATORY
        elif any(keyword in file_name for keyword in ['manual', 'handbook', 'guide']):
            return DocumentType.MANUAL
        elif any(keyword in file_name for keyword in ['technical', 'specification', 'tech']):
            return DocumentType.TECHNICAL
        else:
            return DocumentType.UNKNOWN
    
    def _analyze_page(self, doc: fitz.Document, page_num: int) -> PageAnalysis:
        """Analyze a single page."""
        page = doc[page_num]
        
        # Extract text blocks
        text_blocks = page.get_text("dict")
        
        # Analyze layout
        layout_type = self._detect_layout_type(text_blocks)
        column_count = self._count_columns(text_blocks)
        
        # Extract elements
        elements = self._extract_page_elements(page, text_blocks)
        
        # Detect tables and images
        has_tables = self._has_tables(page)
        has_images = self._has_images(page)
        
        # Analyze text regions
        text_regions = self._analyze_text_regions(text_blocks)
        
        # Determine reading order
        reading_order = self._determine_reading_order(elements)
        
        # Calculate page quality
        quality_score = self._calculate_page_quality(elements, text_blocks)
        
        return PageAnalysis(
            page_number=page_num,
            elements=elements,
            layout_type=layout_type,
            column_count=column_count,
            has_tables=has_tables,
            has_images=has_images,
            text_regions=text_regions,
            reading_order=reading_order,
            quality_score=quality_score
        )
    
    def _extract_page_elements(self, page: fitz.Page, text_blocks: Dict) -> List[DocumentElement]:
        """Extract structured elements from a page."""
        elements = []
        
        for block in text_blocks.get("blocks", []):
            if "lines" in block:  # Text block
                for line in block["lines"]:
                    for span in line["spans"]:
                        element = self._create_text_element(span, page.number)
                        elements.append(element)
        
        return elements
    
    def _create_text_element(self, span: Dict, page_num: int) -> DocumentElement:
        """Create a document element from a text span."""
        text = span.get("text", "")
        bbox = span.get("bbox", (0, 0, 0, 0))
        
        # Determine element type based on formatting
        element_type = self._classify_text_element(span)
        
        # Calculate confidence based on OCR quality indicators
        confidence = self._calculate_text_confidence(span)
        
        return DocumentElement(
            element_type=element_type,
            content=text,
            bbox=bbox,
            page_number=page_num,
            confidence=confidence,
            metadata={
                'font': span.get('font', ''),
                'size': span.get('size', 0),
                'flags': span.get('flags', 0),
                'color': span.get('color', 0)
            }
        )
    
    def _classify_text_element(self, span: Dict) -> ElementType:
        """Classify text element type based on formatting."""
        size = span.get('size', 0)
        flags = span.get('flags', 0)
        text = span.get('text', '').strip()
        
        # Check for headings (larger font, bold)
        if size > 14 and (flags & 2**4):  # Bold flag
            return ElementType.HEADING
        
        # Check for lists
        if text.startswith(('•', '-', '*', '1.', '2.', '3.')):
            return ElementType.LIST
        
        # Default to paragraph
        return ElementType.PARAGRAPH
    
    def _calculate_text_confidence(self, span: Dict) -> float:
        """Calculate confidence score for text extraction."""
        # Simple confidence calculation based on text characteristics
        text = span.get('text', '')
        
        if not text.strip():
            return 0.0
        
        # Higher confidence for longer text
        length_factor = min(len(text) / 100, 1.0)
        
        # Lower confidence for text with many special characters
        special_chars = sum(1 for c in text if not c.isalnum() and c not in ' .,!?;:')
        special_factor = max(0.5, 1.0 - (special_chars / len(text)))
        
        return length_factor * special_factor
    
    def _detect_layout_type(self, text_blocks: Dict) -> str:
        """Detect page layout type."""
        # Simple layout detection
        blocks = text_blocks.get("blocks", [])
        
        if len(blocks) == 0:
            return "empty"
        elif len(blocks) == 1:
            return "single_column"
        else:
            return "multi_column"
    
    def _count_columns(self, text_blocks: Dict) -> int:
        """Count number of columns in the page."""
        # Simple column counting based on x-coordinates
        blocks = text_blocks.get("blocks", [])
        
        if not blocks:
            return 0
        
        x_positions = set()
        for block in blocks:
            if "bbox" in block:
                x_positions.add(int(block["bbox"][0] / 100) * 100)  # Group by 100pt intervals
        
        return len(x_positions)
    
    def _has_tables(self, page: fitz.Page) -> bool:
        """Check if page contains tables."""
        # Simple table detection based on text layout
        # In a real implementation, this would be more sophisticated
        text_dict = page.get_text("dict")
        
        for block in text_dict.get("blocks", []):
            if "lines" in block:
                # Look for aligned text that might indicate tables
                y_positions = []
                for line in block["lines"]:
                    if line.get("bbox"):
                        y_positions.append(line["bbox"][1])
                
                # If we have multiple lines at similar y-positions, might be a table
                if len(set(int(y) for y in y_positions)) < len(y_positions) * 0.8:
                    return True
        
        return False
    
    def _has_images(self, page: fitz.Page) -> bool:
        """Check if page contains images."""
        image_list = page.get_images()
        return len(image_list) > 0
    
    def _analyze_text_regions(self, text_blocks: Dict) -> List[Dict[str, Any]]:
        """Analyze text regions on the page."""
        regions = []
        
        for block in text_blocks.get("blocks", []):
            if "lines" in block:
                region = {
                    'bbox': block.get('bbox', (0, 0, 0, 0)),
                    'line_count': len(block['lines']),
                    'text_length': sum(len(line.get('text', '')) for line in block['lines']),
                    'type': 'text'
                }
                regions.append(region)
        
        return regions
    
    def _determine_reading_order(self, elements: List[DocumentElement]) -> List[int]:
        """Determine reading order of elements."""
        # Simple reading order based on position (top to bottom, left to right)
        indexed_elements = [(i, elem) for i, elem in enumerate(elements)]
        
        # Sort by y-coordinate (top to bottom), then x-coordinate (left to right)
        sorted_elements = sorted(indexed_elements, key=lambda x: (x[1].bbox[1], x[1].bbox[0]))
        
        return [i for i, _ in sorted_elements]
    
    def _calculate_page_quality(self, elements: List[DocumentElement], text_blocks: Dict) -> float:
        """Calculate quality score for a page."""
        if not elements:
            return 0.0
        
        # Average confidence of all elements
        avg_confidence = sum(elem.confidence for elem in elements) / len(elements)
        
        # Text coverage (how much of the page has text)
        total_text_area = sum(
            (elem.bbox[2] - elem.bbox[0]) * (elem.bbox[3] - elem.bbox[1])
            for elem in elements
        )
        
        # Normalize by page area (assuming A4 page: 595 x 842 points)
        page_area = 595 * 842
        coverage_factor = min(total_text_area / page_area, 1.0)
        
        return avg_confidence * coverage_factor
    
    def _build_structure_hierarchy(self, page_analyses: List[PageAnalysis]) -> Dict[str, Any]:
        """Build document structure hierarchy."""
        hierarchy = {
            'type': 'document',
            'children': []
        }
        
        current_section = None
        
        for page_analysis in page_analyses:
            for element in page_analysis.elements:
                if element.element_type == ElementType.HEADING:
                    # Start new section
                    section = {
                        'type': 'section',
                        'title': element.content,
                        'page': element.page_number,
                        'children': []
                    }
                    hierarchy['children'].append(section)
                    current_section = section
                elif current_section is not None:
                    # Add to current section
                    current_section['children'].append({
                        'type': element.element_type.value,
                        'content': element.content,
                        'page': element.page_number
                    })
        
        return hierarchy
    
    def _extract_metadata(self, doc: fitz.Document, file_path: str) -> Dict[str, Any]:
        """Extract document metadata."""
        metadata = doc.metadata
        
        return {
            'file_path': file_path,
            'file_size': Path(file_path).stat().st_size,
            'page_count': len(doc),
            'title': metadata.get('title', ''),
            'author': metadata.get('author', ''),
            'subject': metadata.get('subject', ''),
            'creator': metadata.get('creator', ''),
            'producer': metadata.get('producer', ''),
            'creation_date': metadata.get('creationDate', ''),
            'modification_date': metadata.get('modDate', ''),
            'encrypted': doc.needs_pass,
            'pdf_version': getattr(doc, 'pdf_version', lambda: 'unknown')()
        }
    
    def _calculate_overall_quality(self, page_analyses: List[PageAnalysis]) -> QualityLevel:
        """Calculate overall document quality."""
        if not page_analyses:
            return QualityLevel.UNACCEPTABLE
        
        avg_quality = sum(page.quality_score for page in page_analyses) / len(page_analyses)
        
        if avg_quality >= 0.95:
            return QualityLevel.EXCELLENT
        elif avg_quality >= 0.85:
            return QualityLevel.GOOD
        elif avg_quality >= 0.75:
            return QualityLevel.ACCEPTABLE
        elif avg_quality >= 0.60:
            return QualityLevel.POOR
        else:
            return QualityLevel.UNACCEPTABLE
    
    def _analyze_with_pymupdf(self, file_path: str) -> Dict[str, Any]:
        """Analyze document using PyMuPDF."""
        # Alternative analysis method
        pass
    
    def _analyze_with_pdfplumber(self, file_path: str) -> Dict[str, Any]:
        """Analyze document using pdfplumber."""
        # Alternative analysis method for better table detection
        pass


import time  # Import missing at the top