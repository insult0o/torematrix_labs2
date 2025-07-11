#!/usr/bin/env python3
"""
Text Extraction Service for TORE Matrix Labs V2

This service provides unified text extraction functionality, consolidating
the extraction logic from the original codebase into a clean, testable service.

Key improvements:
- Unified interface for all extraction methods
- Character-level coordinate mapping
- Performance optimization with caching
- Comprehensive error handling
- Strategy pattern integration

This consolidates functionality from:
- enhanced_pdf_extractor.py
- ocr_based_extractor.py
- unstructured_extractor.py
"""

import logging
import fitz  # PyMuPDF
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from abc import ABC, abstractmethod

from ..models.unified_document_model import UnifiedDocument
from .coordinate_mapping_service import CoordinateMappingService, Coordinates, CoordinateSystem, TextPosition


@dataclass
class ExtractionResult:
    """Result of text extraction operation."""
    
    # Extraction data
    text: str = ""
    pages: List[Dict[str, Any]] = field(default_factory=list)
    
    # Coordinate mapping
    character_coordinates: Dict[int, Coordinates] = field(default_factory=dict)
    page_text_mapping: Dict[int, str] = field(default_factory=dict)
    
    # Content analysis
    tables: List[Dict[str, Any]] = field(default_factory=list)
    images: List[Dict[str, Any]] = field(default_factory=list)
    diagrams: List[Dict[str, Any]] = field(default_factory=list)
    
    # Quality metrics
    extraction_confidence: float = 0.0
    character_count: int = 0
    word_count: int = 0
    
    # Metadata
    extraction_method: str = ""
    extraction_time: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    
    # Error information
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class TextExtractionService:
    """
    Unified text extraction service.
    
    This service provides a clean interface for text extraction from documents,
    with character-level coordinate mapping and comprehensive error handling.
    """
    
    def __init__(self, 
                 coordinate_service: CoordinateMappingService):
        """Initialize the text extraction service."""
        self.logger = logging.getLogger(__name__)
        self.coordinate_service = coordinate_service
        
        # Extraction cache
        self.extraction_cache: Dict[str, ExtractionResult] = {}
        self.cache_timeout = 3600  # 1 hour
        
        # Performance statistics
        self.stats = {
            "extractions_performed": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "average_extraction_time": 0.0,
            "total_characters_extracted": 0
        }
        
        self.logger.info("Text extraction service initialized")
    
    def extract_text(self, 
                    document: UnifiedDocument,
                    page_range: Optional[Tuple[int, int]] = None,
                    include_coordinates: bool = True,
                    include_content_analysis: bool = True) -> ExtractionResult:
        """
        Extract text from a document with full coordinate mapping.
        
        Args:
            document: Document to extract text from
            page_range: Optional page range (start, end) - 1-based
            include_coordinates: Whether to include character coordinates
            include_content_analysis: Whether to analyze tables/images
            
        Returns:
            Complete extraction result with coordinates and content analysis
        """
        start_time = datetime.now()
        
        try:
            self.logger.info(f"Extracting text from document: {document.id}")
            
            # Check cache first
            cache_key = self._generate_cache_key(document, page_range, include_coordinates)
            if cache_key in self.extraction_cache:
                self.stats["cache_hits"] += 1
                self.logger.debug("Using cached extraction result")
                return self.extraction_cache[cache_key]
            
            self.stats["cache_misses"] += 1
            
            # Perform extraction
            result = self._perform_extraction(
                document, page_range, include_coordinates, include_content_analysis
            )
            
            # Update statistics
            extraction_time = (datetime.now() - start_time).total_seconds()
            result.extraction_time = extraction_time
            
            self._update_stats(result, extraction_time)
            
            # Cache result
            self.extraction_cache[cache_key] = result
            
            self.logger.info(f"Text extraction completed: {len(result.text)} characters")
            return result
            
        except Exception as e:
            self.logger.error(f"Text extraction failed: {str(e)}")
            
            # Return error result
            result = ExtractionResult(
                extraction_method="failed",
                created_at=datetime.now()
            )
            result.errors.append(str(e))
            return result
    
    def extract_page_text(self,
                         document: UnifiedDocument,
                         page_number: int,
                         include_coordinates: bool = True) -> Dict[str, Any]:
        """
        Extract text from a specific page.
        
        Args:
            document: Document to extract from
            page_number: Page number (1-based)
            include_coordinates: Whether to include coordinates
            
        Returns:
            Page extraction data
        """
        try:
            self.logger.debug(f"Extracting page {page_number} from {document.id}")
            
            # Open document
            doc = fitz.open(document.file_path)
            
            if page_number < 1 or page_number > len(doc):
                raise ValueError(f"Invalid page number: {page_number}")
            
            page = doc[page_number - 1]  # Convert to 0-based
            
            # Extract page data
            page_data = self._extract_single_page(page, page_number, include_coordinates)
            
            doc.close()
            return page_data
            
        except Exception as e:
            self.logger.error(f"Page extraction failed: {str(e)}")
            return {
                "page": page_number,
                "text": "",
                "coordinates": {},
                "error": str(e)
            }
    
    def get_text_at_coordinates(self,
                               document: UnifiedDocument,
                               coordinates: Coordinates) -> Optional[str]:
        """
        Get text at specific coordinates.
        
        Args:
            document: Document to search in
            coordinates: Target coordinates
            
        Returns:
            Text at coordinates, or None if not found
        """
        try:
            # Convert coordinates to text position
            text_position = self.coordinate_service.pdf_to_text_position(document, coordinates)
            
            if not text_position:
                return None
            
            # Extract page text
            page_data = self.extract_page_text(document, coordinates.page, include_coordinates=False)
            page_text = page_data.get("text", "")
            
            # Get text around the position
            start_index = max(0, text_position.character_index - 50)
            end_index = min(len(page_text), text_position.character_index + 50)
            
            return page_text[start_index:end_index]
            
        except Exception as e:
            self.logger.error(f"Failed to get text at coordinates: {str(e)}")
            return None
    
    def search_text_in_document(self,
                               document: UnifiedDocument,
                               search_text: str,
                               case_sensitive: bool = False) -> List[Dict[str, Any]]:
        """
        Search for text in document and return locations with coordinates.
        
        Args:
            document: Document to search in
            search_text: Text to search for
            case_sensitive: Whether search is case sensitive
            
        Returns:
            List of search results with coordinates
        """
        results = []
        
        try:
            self.logger.debug(f"Searching for '{search_text}' in {document.id}")
            
            # Extract full document text
            extraction_result = self.extract_text(document, include_coordinates=True)
            
            # Search in each page
            for page_data in extraction_result.pages:
                page_number = page_data["page"]
                page_text = page_data["text"]
                coordinates = page_data.get("coordinates", {})
                
                # Perform search
                search_target = page_text if case_sensitive else page_text.lower()
                search_term = search_text if case_sensitive else search_text.lower()
                
                start_index = 0
                while True:
                    index = search_target.find(search_term, start_index)
                    if index == -1:
                        break
                    
                    # Get coordinates for this match
                    match_coordinates = None
                    if str(index) in coordinates:
                        char_coord = coordinates[str(index)]
                        match_coordinates = Coordinates(
                            x=char_coord["bbox"][0],
                            y=char_coord["bbox"][1],
                            width=char_coord["bbox"][2] - char_coord["bbox"][0],
                            height=char_coord["bbox"][3] - char_coord["bbox"][1],
                            system=CoordinateSystem.PDF,
                            page=page_number
                        )
                    
                    results.append({
                        "text": search_text,
                        "page": page_number,
                        "character_index": index,
                        "coordinates": match_coordinates,
                        "context": page_text[max(0, index-20):index+len(search_text)+20]
                    })
                    
                    start_index = index + 1
            
            self.logger.info(f"Found {len(results)} matches for '{search_text}'")
            return results
            
        except Exception as e:
            self.logger.error(f"Text search failed: {str(e)}")
            return []
    
    def _perform_extraction(self,
                           document: UnifiedDocument,
                           page_range: Optional[Tuple[int, int]],
                           include_coordinates: bool,
                           include_content_analysis: bool) -> ExtractionResult:
        """Perform the actual text extraction."""
        
        result = ExtractionResult(extraction_method="pymupdf")
        
        # Open document
        doc = fitz.open(document.file_path)
        
        # Determine page range
        start_page = page_range[0] if page_range else 1
        end_page = page_range[1] if page_range else len(doc)
        
        # Validate page range
        start_page = max(1, start_page)
        end_page = min(len(doc), end_page)
        
        all_text = []
        total_char_index = 0
        
        # Extract each page
        for page_num in range(start_page, end_page + 1):
            page = doc[page_num - 1]  # Convert to 0-based
            
            # Extract page data
            page_data = self._extract_single_page(page, page_num, include_coordinates)
            
            result.pages.append(page_data)
            all_text.append(page_data["text"])
            
            # Update page text mapping
            result.page_text_mapping[page_num] = page_data["text"]
            
            # Add character coordinates with global indexing
            if include_coordinates and "coordinates" in page_data:
                for local_index, coord_data in page_data["coordinates"].items():
                    global_index = total_char_index + int(local_index)
                    
                    coordinates = Coordinates(
                        x=coord_data["bbox"][0],
                        y=coord_data["bbox"][1],
                        width=coord_data["bbox"][2] - coord_data["bbox"][0],
                        height=coord_data["bbox"][3] - coord_data["bbox"][1],
                        system=CoordinateSystem.PDF,
                        page=page_num
                    )
                    
                    result.character_coordinates[global_index] = coordinates
            
            total_char_index += len(page_data["text"]) + 2  # +2 for page separator
        
        # Combine all text
        result.text = "\n\n".join(all_text)
        result.character_count = len(result.text)
        result.word_count = len(result.text.split())
        
        # Content analysis
        if include_content_analysis:
            self._analyze_content(doc, result, start_page, end_page)
        
        # Set confidence based on extraction method
        result.extraction_confidence = 0.8  # PyMuPDF default
        
        doc.close()
        return result
    
    def _extract_single_page(self,
                            page: fitz.Page,
                            page_number: int,
                            include_coordinates: bool) -> Dict[str, Any]:
        """Extract data from a single page."""
        
        page_data = {
            "page": page_number,
            "text": "",
            "coordinates": {},
            "metadata": {}
        }
        
        try:
            # Get page text
            page_data["text"] = page.get_text()
            
            # Get character-level coordinates if requested
            if include_coordinates:
                text_dict = page.get_text("dict")
                coordinates = {}
                char_index = 0
                
                for block in text_dict["blocks"]:
                    if "lines" not in block:
                        continue
                    
                    for line in block["lines"]:
                        for span in line["spans"]:
                            for char in span.get("chars", []):
                                coordinates[char_index] = {
                                    "bbox": char["bbox"],
                                    "char": char.get("c", ""),
                                    "font": span.get("font", ""),
                                    "size": span.get("size", 12)
                                }
                                char_index += 1
                
                page_data["coordinates"] = coordinates
            
            # Page metadata
            page_data["metadata"] = {
                "width": page.rect.width,
                "height": page.rect.height,
                "rotation": page.rotation
            }
            
        except Exception as e:
            self.logger.error(f"Failed to extract page {page_number}: {str(e)}")
            page_data["error"] = str(e)
        
        return page_data
    
    def _analyze_content(self,
                        doc: fitz.Document,
                        result: ExtractionResult,
                        start_page: int,
                        end_page: int):
        """Analyze document content for tables, images, and diagrams."""
        
        try:
            for page_num in range(start_page, end_page + 1):
                page = doc[page_num - 1]
                
                # Analyze tables (simplified detection)
                tables = self._detect_tables(page, page_num)
                result.tables.extend(tables)
                
                # Analyze images
                images = self._detect_images(page, page_num)
                result.images.extend(images)
                
                # Analyze diagrams (heuristic detection)
                diagrams = self._detect_diagrams(page, page_num)
                result.diagrams.extend(diagrams)
                
        except Exception as e:
            self.logger.warning(f"Content analysis failed: {str(e)}")
            result.warnings.append(f"Content analysis failed: {str(e)}")
    
    def _detect_tables(self, page: fitz.Page, page_number: int) -> List[Dict[str, Any]]:
        """Detect tables in a page."""
        tables = []
        
        try:
            # Simple table detection based on text patterns
            text = page.get_text()
            
            # Look for table indicators
            tab_count = text.count('\t')
            multiple_spaces = len([line for line in text.split('\n') if '   ' in line])
            
            if tab_count > 10 or multiple_spaces > 5:
                # Likely contains tables
                tables.append({
                    "page": page_number,
                    "type": "table",
                    "confidence": 0.7,
                    "bbox": [0, 0, page.rect.width, page.rect.height],
                    "detected_method": "text_pattern"
                })
                
        except Exception as e:
            self.logger.warning(f"Table detection failed for page {page_number}: {str(e)}")
        
        return tables
    
    def _detect_images(self, page: fitz.Page, page_number: int) -> List[Dict[str, Any]]:
        """Detect images in a page."""
        images = []
        
        try:
            # Get image list from PyMuPDF
            image_list = page.get_images()
            
            for img_index, img in enumerate(image_list):
                xref = img[0]
                
                # Get image bbox
                try:
                    img_bbox = page.get_image_bbox(img)
                    
                    images.append({
                        "page": page_number,
                        "type": "image",
                        "index": img_index,
                        "xref": xref,
                        "bbox": [img_bbox.x0, img_bbox.y0, img_bbox.x1, img_bbox.y1],
                        "detected_method": "pymupdf"
                    })
                except:
                    # Fallback if bbox detection fails
                    images.append({
                        "page": page_number,
                        "type": "image",
                        "index": img_index,
                        "xref": xref,
                        "bbox": [0, 0, 100, 100],  # Placeholder
                        "detected_method": "pymupdf_fallback"
                    })
                    
        except Exception as e:
            self.logger.warning(f"Image detection failed for page {page_number}: {str(e)}")
        
        return images
    
    def _detect_diagrams(self, page: fitz.Page, page_number: int) -> List[Dict[str, Any]]:
        """Detect diagrams in a page (heuristic approach)."""
        diagrams = []
        
        try:
            # Get page drawings/paths
            drawings = page.get_drawings()
            
            # If there are many vector drawings, likely contains diagrams
            if len(drawings) > 10:
                diagrams.append({
                    "page": page_number,
                    "type": "diagram",
                    "drawing_count": len(drawings),
                    "confidence": 0.6,
                    "bbox": [0, 0, page.rect.width, page.rect.height],
                    "detected_method": "vector_analysis"
                })
                
        except Exception as e:
            self.logger.warning(f"Diagram detection failed for page {page_number}: {str(e)}")
        
        return diagrams
    
    def _generate_cache_key(self,
                           document: UnifiedDocument,
                           page_range: Optional[Tuple[int, int]],
                           include_coordinates: bool) -> str:
        """Generate cache key for extraction result."""
        page_str = f"{page_range[0]}-{page_range[1]}" if page_range else "all"
        coord_str = "coords" if include_coordinates else "no_coords"
        
        return f"{document.id}_{page_str}_{coord_str}_{document.metadata.file_size}"
    
    def _update_stats(self, result: ExtractionResult, extraction_time: float):
        """Update performance statistics."""
        self.stats["extractions_performed"] += 1
        self.stats["total_characters_extracted"] += result.character_count
        
        # Update average extraction time
        total_extractions = self.stats["extractions_performed"]
        current_avg = self.stats["average_extraction_time"]
        self.stats["average_extraction_time"] = ((current_avg * (total_extractions - 1)) + extraction_time) / total_extractions
    
    def clear_cache(self, document_id: Optional[str] = None):
        """Clear extraction cache."""
        if document_id:
            # Clear cache for specific document
            keys_to_remove = [key for key in self.extraction_cache.keys() if key.startswith(document_id)]
            for key in keys_to_remove:
                del self.extraction_cache[key]
        else:
            # Clear all cache
            self.extraction_cache.clear()
        
        self.logger.info(f"Extraction cache cleared: {document_id or 'all'}")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        cache_total = self.stats["cache_hits"] + self.stats["cache_misses"]
        cache_hit_rate = (self.stats["cache_hits"] / cache_total) if cache_total > 0 else 0.0
        
        return {
            **self.stats,
            "cache_hit_rate": cache_hit_rate,
            "cache_size": len(self.extraction_cache)
        }