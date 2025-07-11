"""
Content extraction engine for TORE Matrix Labs.
"""

import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass
from io import BytesIO
import base64

import fitz  # PyMuPDF
import pdfplumber
from PIL import Image

# Use compatibility layer for pandas
try:
    from ..utils.numpy_compatibility import pandas, PANDAS_AVAILABLE
    if not PANDAS_AVAILABLE or pandas is None:
        # Create minimal pandas replacement
        class PandasFallback:
            @staticmethod
            def DataFrame(data=None):
                return data if data else {}
        pandas = PandasFallback()
        logging.warning("Pandas not available, using fallback implementation")
except ImportError:
    class PandasFallback:
        @staticmethod
        def DataFrame(data=None):
            return data if data else {}
    pandas = PandasFallback()
    logging.warning("Pandas compatibility layer not available, using fallback")

from ..config.constants import QualityLevel
from ..config.settings import Settings
from .document_analyzer import DocumentElement, PageAnalysis, ElementType


@dataclass
class ExtractedTable:
    """Represents an extracted table."""
    page_number: int
    bbox: Tuple[float, float, float, float]
    data: List[List[str]]
    headers: List[str]
    confidence: float
    metadata: Dict[str, Any]
    
    def to_dataframe(self):
        """Convert table to pandas DataFrame."""
        if self.headers and self.data:
            return pandas.DataFrame(self.data, columns=self.headers)
        elif self.data:
            return pandas.DataFrame(self.data)
        else:
            return pandas.DataFrame()


@dataclass
class ExtractedImage:
    """Represents an extracted image."""
    page_number: int
    bbox: Tuple[float, float, float, float]
    image_data: bytes
    format: str
    width: int
    height: int
    caption: Optional[str]
    metadata: Dict[str, Any]
    
    def to_base64(self) -> str:
        """Convert image to base64 string."""
        return base64.b64encode(self.image_data).decode('utf-8')
    
    def to_pil_image(self) -> Image.Image:
        """Convert to PIL Image."""
        return Image.open(BytesIO(self.image_data))


@dataclass
class ExtractedContent:
    """Complete extracted content from a document."""
    text_elements: List[DocumentElement]
    tables: List[ExtractedTable]
    images: List[ExtractedImage]
    metadata: Dict[str, Any]
    extraction_time: float
    quality_score: float
    auto_detected_conflicts: Optional[List[Dict[str, Any]]] = None
    
    def get_all_conflicts(self) -> List[Dict[str, Any]]:
        """Get all auto-detected conflicts from tables and images."""
        all_conflicts = []
        
        # Get conflicts from tables
        for table in self.tables:
            conflicts = table.metadata.get('auto_detected_conflicts', [])
            all_conflicts.extend(conflicts)
        
        # Get conflicts from images  
        for image in self.images:
            conflicts = image.metadata.get('auto_detected_conflicts', [])
            all_conflicts.extend(conflicts)
        
        # Add any stored conflicts
        if self.auto_detected_conflicts:
            all_conflicts.extend(self.auto_detected_conflicts)
        
        return all_conflicts
    
    def has_conflicts(self) -> bool:
        """Check if there are any auto-detected conflicts requiring resolution."""
        return len(self.get_all_conflicts()) > 0


class ContentExtractor:
    """Main content extraction engine."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        self._init_processors()
    
    def _init_processors(self):
        """Initialize extraction processors."""
        self.text_extractors = {
            'pymupdf': self._extract_text_pymupdf,
            'pdfplumber': self._extract_text_pdfplumber
        }
        
        self.table_extractors = {
            'pdfplumber': self._extract_tables_pdfplumber,
            'pymupdf': self._extract_tables_pymupdf
        }
        
        self.image_extractors = {
            'pymupdf': self._extract_images_pymupdf
        }
    
    def extract_content(self, file_path: str, page_analyses: List[PageAnalysis], 
                       exclusion_zones: Optional[Dict[int, List[Dict[str, Any]]]] = None) -> ExtractedContent:
        """
        Extract all content from document.
        
        Args:
            file_path: Path to the document
            page_analyses: Pre-computed page analyses
            exclusion_zones: Optional exclusion zones to skip during text extraction
            
        Returns:
            ExtractedContent with all extracted data
        """
        self.logger.info(f"Starting content extraction: {file_path}")
        start_time = time.time()
        
        try:
            # Extract different content types
            text_elements = self._extract_text_content(file_path, page_analyses, exclusion_zones)
            tables = self._extract_table_content(file_path, exclusion_zones)
            images = self._extract_image_content(file_path, exclusion_zones)
            
            # Calculate quality score
            quality_score = self._calculate_extraction_quality(text_elements, tables, images)
            
            # Collect metadata
            metadata = self._collect_extraction_metadata(file_path, len(text_elements), len(tables), len(images))
            
            extraction_time = time.time() - start_time
            
            content = ExtractedContent(
                text_elements=text_elements,
                tables=tables,
                images=images,
                metadata=metadata,
                extraction_time=extraction_time,
                quality_score=quality_score
            )
            
            self.logger.info(f"Content extraction completed in {extraction_time:.2f}s")
            return content
            
        except Exception as e:
            self.logger.error(f"Content extraction failed: {str(e)}")
            raise
    
    def _extract_text_content(self, file_path: str, page_analyses: List[PageAnalysis], 
                             exclusion_zones: Optional[Dict[int, List[Dict[str, Any]]]] = None) -> List[DocumentElement]:
        """Extract text content from document."""
        from .exclusion_zones import ExclusionZoneManager, ExclusionZone
        
        text_elements = []
        
        # Initialize exclusion zone manager if zones provided
        exclusion_manager = None
        if exclusion_zones:
            exclusion_manager = ExclusionZoneManager()
            for page_num, zones_data in exclusion_zones.items():
                for zone_data in zones_data:
                    zone = ExclusionZone(
                        page=page_num,
                        bbox=zone_data['bbox'],
                        zone_type=zone_data['type'],
                        snippet_id=zone_data.get('snippet_id', 'unknown'),
                        priority=zone_data.get('priority', 1)
                    )
                    exclusion_manager.add_zone(zone)
            
            self.logger.info(f"Loaded {len(exclusion_zones)} pages with exclusion zones")
        
        # Use pre-analyzed elements
        for page_analysis in page_analyses:
            page_elements = []
            
            for element in page_analysis.elements:
                # Check exclusion zones if available
                if exclusion_manager:
                    should_exclude, overlapping_zone = exclusion_manager.should_exclude_text_element(
                        element.page_number, list(element.bbox)
                    )
                    
                    if should_exclude:
                        self.logger.debug(f"Excluded text element in {overlapping_zone.zone_type} zone: {element.content[:50]}...")
                        continue
                
                page_elements.append(element)
            
            text_elements.extend(page_elements)
        
        # Apply text cleaning and normalization
        text_elements = self._clean_text_elements(text_elements)
        
        # Log exclusion statistics
        if exclusion_manager:
            stats = exclusion_manager.get_exclusion_statistics()
            self.logger.info(f"Text extraction completed with exclusions: {stats['total_zones']} zones across {stats['pages_with_zones']} pages")
        
        return text_elements
    
    def _extract_table_content(self, file_path: str, 
                              exclusion_zones: Optional[Dict[int, List[Dict[str, Any]]]] = None) -> List[ExtractedTable]:
        """Extract tables from document."""
        from .exclusion_zones import ExclusionZoneManager, ExclusionZone
        
        tables = []
        auto_detected_conflicts = []
        
        # Initialize exclusion zone manager if zones provided
        exclusion_manager = None
        if exclusion_zones:
            exclusion_manager = ExclusionZoneManager()
            for page_num, zones_data in exclusion_zones.items():
                for zone_data in zones_data:
                    zone = ExclusionZone(
                        page=page_num,
                        bbox=zone_data['bbox'],
                        zone_type=zone_data['type'],
                        snippet_id=zone_data.get('snippet_id', 'unknown'),
                        priority=zone_data.get('priority', 1)
                    )
                    exclusion_manager.add_zone(zone)
        
        try:
            # Use pdfplumber for better table extraction
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    page_tables = page.extract_tables()
                    
                    for table_data in page_tables:
                        if table_data and len(table_data) > 1:
                            # Extract headers and data
                            headers = table_data[0] if table_data[0] else []
                            data = table_data[1:] if len(table_data) > 1 else []
                            
                            # Clean empty cells
                            data = [[cell or '' for cell in row] for row in data]
                            
                            # Calculate table bbox (approximation)
                            bbox = self._estimate_table_bbox(page, table_data)
                            
                            # Check if this table overlaps with manual validation zones
                            should_exclude = False
                            conflict_zone = None
                            if exclusion_manager:
                                should_exclude, conflict_zone = exclusion_manager.should_exclude_text_element(page_num, bbox)
                            
                            # Calculate confidence
                            confidence = self._calculate_table_confidence(table_data)
                            
                            table = ExtractedTable(
                                page_number=page_num,
                                bbox=bbox,
                                data=data,
                                headers=headers,
                                confidence=confidence,
                                metadata={
                                    'rows': len(data),
                                    'columns': len(headers) if headers else (len(data[0]) if data else 0),
                                    'extraction_method': 'pdfplumber',
                                    'excluded_by_manual_validation': should_exclude,
                                    'conflict_zone_type': conflict_zone.zone_type if conflict_zone else None,
                                    'conflict_snippet_id': conflict_zone.snippet_id if conflict_zone else None
                                }
                            )
                            
                            if should_exclude:
                                # Flag as auto-detected conflict (user should resolve)
                                if conflict_zone.zone_type != 'TABLE':
                                    auto_detected_conflicts.append({
                                        'type': 'TABLE',
                                        'bbox': bbox,
                                        'page': page_num,
                                        'conflict_with': conflict_zone.zone_type,
                                        'manual_snippet_id': conflict_zone.snippet_id,
                                        'auto_confidence': confidence,
                                        'resolution_needed': True,
                                        'suggestion': f'Auto-detected TABLE conflicts with manually classified {conflict_zone.zone_type}'
                                    })
                                    self.logger.warning(f"TABLE detection conflict on page {page_num}: auto-detected TABLE conflicts with manual {conflict_zone.zone_type}")
                                else:
                                    # Same type, just skip (already manually validated)
                                    self.logger.debug(f"Skipped auto-detected TABLE on page {page_num}: already manually validated")
                            else:
                                tables.append(table)
                            
        except Exception as e:
            self.logger.warning(f"Table extraction failed: {str(e)}")
        
        # Store auto-detected conflicts for later resolution
        if auto_detected_conflicts:
            self.logger.warning(f"Found {len(auto_detected_conflicts)} auto-detected TABLE conflicts requiring user resolution")
            # Store conflicts in table metadata for later retrieval
            for table in tables:
                table.metadata['auto_detected_conflicts'] = auto_detected_conflicts
        
        return tables
    
    def _extract_image_content(self, file_path: str, 
                              exclusion_zones: Optional[Dict[int, List[Dict[str, Any]]]] = None) -> List[ExtractedImage]:
        """Extract images from document."""
        from .exclusion_zones import ExclusionZoneManager, ExclusionZone
        
        images = []
        auto_detected_conflicts = []
        
        # Initialize exclusion zone manager if zones provided
        exclusion_manager = None
        if exclusion_zones:
            exclusion_manager = ExclusionZoneManager()
            for page_num, zones_data in exclusion_zones.items():
                for zone_data in zones_data:
                    zone = ExclusionZone(
                        page=page_num,
                        bbox=zone_data['bbox'],
                        zone_type=zone_data['type'],
                        snippet_id=zone_data.get('snippet_id', 'unknown'),
                        priority=zone_data.get('priority', 1)
                    )
                    exclusion_manager.add_zone(zone)
        
        try:
            doc = fitz.open(file_path)
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                image_list = page.get_images()
                
                for img_index, img in enumerate(image_list):
                    try:
                        # Get image data
                        xref = img[0]
                        pix = fitz.Pixmap(doc, xref)
                        
                        # Convert to PNG if CMYK
                        if pix.n - pix.alpha < 4:
                            img_data = pix.tobytes("png")
                            img_format = "PNG"
                        else:
                            pix1 = fitz.Pixmap(fitz.csRGB, pix)
                            img_data = pix1.tobytes("png")
                            img_format = "PNG"
                            pix1 = None
                        
                        # Get image bbox
                        img_bbox = page.get_image_bbox(img)
                        
                        # Check if this image overlaps with manual validation zones
                        should_exclude = False
                        conflict_zone = None
                        if exclusion_manager:
                            should_exclude, conflict_zone = exclusion_manager.should_exclude_text_element(page_num, list(img_bbox))
                        
                        # Find associated caption
                        caption = self._find_image_caption(page, img_bbox)
                        
                        extracted_image = ExtractedImage(
                            page_number=page_num,
                            bbox=img_bbox,
                            image_data=img_data,
                            format=img_format,
                            width=pix.width,
                            height=pix.height,
                            caption=caption,
                            metadata={
                                'xref': xref,
                                'colorspace': pix.colorspace.name if pix.colorspace else 'unknown',
                                'bits_per_component': pix.stride,
                                'extraction_method': 'pymupdf',
                                'excluded_by_manual_validation': should_exclude,
                                'conflict_zone_type': conflict_zone.zone_type if conflict_zone else None,
                                'conflict_snippet_id': conflict_zone.snippet_id if conflict_zone else None
                            }
                        )
                        
                        if should_exclude:
                            # Flag as auto-detected conflict (user should resolve)
                            if conflict_zone.zone_type not in ['IMAGE', 'DIAGRAM']:
                                auto_detected_conflicts.append({
                                    'type': 'IMAGE',
                                    'bbox': list(img_bbox),
                                    'page': page_num,
                                    'conflict_with': conflict_zone.zone_type,
                                    'manual_snippet_id': conflict_zone.snippet_id,
                                    'auto_confidence': 0.9,  # High confidence for image detection
                                    'resolution_needed': True,
                                    'suggestion': f'Auto-detected IMAGE conflicts with manually classified {conflict_zone.zone_type}'
                                })
                                self.logger.warning(f"IMAGE detection conflict on page {page_num}: auto-detected IMAGE conflicts with manual {conflict_zone.zone_type}")
                            else:
                                # Same or similar type, just skip (already manually validated)
                                self.logger.debug(f"Skipped auto-detected IMAGE on page {page_num}: already manually validated as {conflict_zone.zone_type}")
                        else:
                            images.append(extracted_image)
                        pix = None
                        
                    except Exception as e:
                        self.logger.warning(f"Failed to extract image {img_index} from page {page_num}: {str(e)}")
                        continue
            
            doc.close()
            
        except Exception as e:
            self.logger.warning(f"Image extraction failed: {str(e)}")
        
        # Store auto-detected conflicts for later resolution
        if auto_detected_conflicts:
            self.logger.warning(f"Found {len(auto_detected_conflicts)} auto-detected IMAGE conflicts requiring user resolution")
            # Store conflicts in image metadata for later retrieval
            for image in images:
                image.metadata['auto_detected_conflicts'] = auto_detected_conflicts
        
        return images
    
    def _clean_text_elements(self, elements: List[DocumentElement]) -> List[DocumentElement]:
        """Clean and normalize text elements."""
        cleaned_elements = []
        
        for element in elements:
            # Clean text content
            cleaned_text = self._clean_text(element.content)
            
            if cleaned_text.strip():  # Only keep non-empty text
                # Create new element with cleaned text
                cleaned_element = DocumentElement(
                    element_type=element.element_type,
                    content=cleaned_text,
                    bbox=element.bbox,
                    page_number=element.page_number,
                    confidence=element.confidence,
                    metadata=element.metadata
                )
                cleaned_elements.append(cleaned_element)
        
        return cleaned_elements
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Fix common OCR errors
        text = text.replace('ﬁ', 'fi')
        text = text.replace('ﬂ', 'fl')
        text = text.replace('–', '-')
        text = text.replace('—', '-')
        text = text.replace(''', "'")
        text = text.replace(''', "'")
        text = text.replace('"', '"')
        text = text.replace('"', '"')
        
        # Remove non-printable characters
        text = ''.join(char for char in text if char.isprintable() or char.isspace())
        
        return text
    
    def _estimate_table_bbox(self, page, table_data: List[List]) -> Tuple[float, float, float, float]:
        """Estimate table bounding box."""
        # This is a simplified estimation
        # In practice, you'd use the actual table detection coordinates
        page_width = page.width
        page_height = page.height
        
        # Assume table takes up a portion of the page
        return (50, 100, page_width - 50, page_height - 100)
    
    def _calculate_table_confidence(self, table_data: List[List]) -> float:
        """Calculate confidence score for table extraction."""
        if not table_data:
            return 0.0
        
        # Calculate based on data completeness
        total_cells = sum(len(row) for row in table_data)
        empty_cells = sum(1 for row in table_data for cell in row if not cell or not str(cell).strip())
        
        if total_cells == 0:
            return 0.0
        
        completeness = 1.0 - (empty_cells / total_cells)
        
        # Penalize very small tables
        size_factor = min(len(table_data) / 3, 1.0)
        
        return completeness * size_factor
    
    def _find_image_caption(self, page: fitz.Page, img_bbox: Tuple[float, float, float, float]) -> Optional[str]:
        """Find caption text near an image."""
        # Look for text elements near the image
        text_dict = page.get_text("dict")
        
        # Search area below the image
        search_area = (
            img_bbox[0] - 50,  # x0
            img_bbox[3],       # y0 (bottom of image)
            img_bbox[2] + 50,  # x1
            img_bbox[3] + 100  # y1 (100 points below image)
        )
        
        caption_candidates = []
        
        for block in text_dict.get("blocks", []):
            if "lines" in block:
                for line in block["lines"]:
                    line_bbox = line.get("bbox", (0, 0, 0, 0))
                    
                    # Check if line is in search area
                    if (line_bbox[0] >= search_area[0] and
                        line_bbox[1] >= search_area[1] and
                        line_bbox[2] <= search_area[2] and
                        line_bbox[3] <= search_area[3]):
                        
                        line_text = ""
                        for span in line.get("spans", []):
                            line_text += span.get("text", "")
                        
                        if line_text.strip():
                            caption_candidates.append(line_text.strip())
        
        # Return the first candidate that looks like a caption
        for candidate in caption_candidates:
            if any(keyword in candidate.lower() for keyword in ['figure', 'fig', 'image', 'diagram', 'chart']):
                return candidate
        
        # Return first candidate if no specific caption keywords found
        return caption_candidates[0] if caption_candidates else None
    
    def _calculate_extraction_quality(self, text_elements: List[DocumentElement], 
                                    tables: List[ExtractedTable], 
                                    images: List[ExtractedImage]) -> float:
        """Calculate overall extraction quality score."""
        scores = []
        
        # Text quality
        if text_elements:
            text_quality = sum(elem.confidence for elem in text_elements) / len(text_elements)
            scores.append(text_quality)
        
        # Table quality
        if tables:
            table_quality = sum(table.confidence for table in tables) / len(tables)
            scores.append(table_quality)
        
        # Image quality (assume high quality for successful extractions)
        if images:
            scores.append(0.9)
        
        return sum(scores) / len(scores) if scores else 0.0
    
    def _collect_extraction_metadata(self, file_path: str, text_count: int, 
                                   table_count: int, image_count: int) -> Dict[str, Any]:
        """Collect extraction metadata."""
        return {
            'file_path': file_path,
            'extraction_timestamp': time.time(),
            'text_elements_count': text_count,
            'tables_count': table_count,
            'images_count': image_count,
            'extraction_methods': {
                'text': 'pymupdf',
                'tables': 'pdfplumber',
                'images': 'pymupdf'
            }
        }
    
    def _extract_text_pymupdf(self, file_path: str) -> List[DocumentElement]:
        """Extract text using PyMuPDF."""
        # Alternative text extraction method
        pass
    
    def _extract_text_pdfplumber(self, file_path: str) -> List[DocumentElement]:
        """Extract text using pdfplumber."""
        # Alternative text extraction method
        pass
    
    def _extract_tables_pdfplumber(self, file_path: str) -> List[ExtractedTable]:
        """Extract tables using pdfplumber."""
        # Already implemented in main method
        pass
    
    def _extract_tables_pymupdf(self, file_path: str) -> List[ExtractedTable]:
        """Extract tables using PyMuPDF."""
        # Alternative table extraction method
        pass
    
    def _extract_images_pymupdf(self, file_path: str) -> List[ExtractedImage]:
        """Extract images using PyMuPDF."""
        # Already implemented in main method
        pass