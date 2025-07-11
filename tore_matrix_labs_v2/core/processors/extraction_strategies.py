#!/usr/bin/env python3
"""
Extraction Strategies for TORE Matrix Labs V2

This module implements the strategy pattern for document text extraction,
consolidating all extraction methods from the original codebase into
clean, testable strategies.

Strategies implemented:
- PyMuPDFExtractionStrategy: Standard PDF extraction (fallback)
- OCRExtractionStrategy: OCR-based extraction for images and poor PDFs
- UnstructuredExtractionStrategy: Advanced document structure detection

Key improvements:
- Strategy pattern for pluggable extraction methods
- Consistent interface across all strategies
- Comprehensive error handling
- Performance optimization
- Character-level coordinate mapping
"""

import logging
import fitz  # PyMuPDF
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path

# Import original extractors for strategy implementation
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../tore_matrix_labs'))

try:
    from core.enhanced_pdf_extractor import EnhancedPDFExtractor
    from core.ocr_based_extractor import OCRBasedExtractor, OCR_DEPENDENCIES_AVAILABLE
    from core.unstructured_extractor import UnstructuredExtractor, UNSTRUCTURED_AVAILABLE
except ImportError:
    # Fallback if original modules not available
    EnhancedPDFExtractor = None
    OCRBasedExtractor = None
    UnstructuredExtractor = None
    OCR_DEPENDENCIES_AVAILABLE = False
    UNSTRUCTURED_AVAILABLE = False

from ..models.unified_document_model import UnifiedDocument


class ExtractionStrategy(ABC):
    """Abstract base class for text extraction strategies."""
    
    def __init__(self, name: str):
        """Initialize extraction strategy."""
        self.name = name
        self.logger = logging.getLogger(f"{__name__}.{name}")
        self.performance_stats = {
            "documents_processed": 0,
            "total_processing_time": 0.0,
            "success_rate": 0.0,
            "average_quality": 0.0
        }
    
    @abstractmethod
    def extract(self, document: UnifiedDocument) -> Dict[str, Any]:
        """
        Extract text from document.
        
        Args:
            document: Document to extract text from
            
        Returns:
            Extraction result dictionary with:
            - success: bool
            - text: str (extracted text)
            - pages: List[Dict] (page-level data)
            - metadata: Dict (extraction metadata)
            - coordinates: Dict (character-level coordinate mapping)
            - quality_score: float
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this strategy is available for use."""
        pass
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for this strategy."""
        return self.performance_stats.copy()
    
    def _update_stats(self, processing_time: float, success: bool, quality_score: float = 0.0):
        """Update performance statistics."""
        self.performance_stats["documents_processed"] += 1
        self.performance_stats["total_processing_time"] += processing_time
        
        # Update success rate
        total_docs = self.performance_stats["documents_processed"]
        current_successes = (self.performance_stats["success_rate"] * (total_docs - 1)) + (1 if success else 0)
        self.performance_stats["success_rate"] = current_successes / total_docs
        
        # Update average quality
        current_avg_quality = self.performance_stats["average_quality"]
        self.performance_stats["average_quality"] = ((current_avg_quality * (total_docs - 1)) + quality_score) / total_docs


class PyMuPDFExtractionStrategy(ExtractionStrategy):
    """Standard PyMuPDF extraction strategy - reliable fallback method."""
    
    def __init__(self, settings=None):
        """Initialize PyMuPDF extraction strategy."""
        super().__init__("pymupdf")
        self.settings = settings
        
        # Initialize enhanced extractor if available
        if EnhancedPDFExtractor:
            try:
                self.extractor = EnhancedPDFExtractor(settings)
            except Exception as e:
                self.logger.warning(f"Failed to initialize enhanced extractor: {e}")
                self.extractor = None
        else:
            self.extractor = None
    
    def is_available(self) -> bool:
        """PyMuPDF is always available as it's a core dependency."""
        return True
    
    def extract(self, document: UnifiedDocument) -> Dict[str, Any]:
        """Extract text using PyMuPDF with enhanced processing."""
        start_time = datetime.now()
        
        try:
            self.logger.info(f"Extracting text with PyMuPDF: {document.file_name}")
            
            # Open document
            doc = fitz.open(document.file_path)
            
            # Extract text and metadata
            result = {
                "success": True,
                "text": "",
                "pages": [],
                "metadata": {
                    "extractor": "pymupdf",
                    "page_count": len(doc),
                    "extraction_time": 0.0
                },
                "coordinates": {},
                "quality_score": 0.8  # Default quality for PyMuPDF
            }
            
            full_text = []
            
            # Process each page
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Use enhanced extractor if available
                if self.extractor:
                    page_result = self._extract_page_enhanced(page, page_num + 1)
                else:
                    page_result = self._extract_page_basic(page, page_num + 1)
                
                result["pages"].append(page_result)
                full_text.append(page_result["text"])
                
                # Store character-level coordinates
                if "coordinates" in page_result:
                    result["coordinates"][page_num + 1] = page_result["coordinates"]
            
            # Combine all text
            result["text"] = "\n\n".join(full_text)
            
            # Update document metadata
            document.metadata.page_count = len(doc)
            document.metadata.extraction_method = "pymupdf"
            document.metadata.total_characters = len(result["text"])
            document.metadata.total_words = len(result["text"].split())
            
            doc.close()
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            result["metadata"]["extraction_time"] = processing_time
            
            # Update statistics
            self._update_stats(processing_time, True, result["quality_score"])
            
            self.logger.info(f"PyMuPDF extraction completed: {len(result['text'])} characters")
            return result
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            self._update_stats(processing_time, False)
            
            self.logger.error(f"PyMuPDF extraction failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "text": "",
                "pages": [],
                "metadata": {"extractor": "pymupdf", "error": str(e)},
                "coordinates": {},
                "quality_score": 0.0
            }
    
    def _extract_page_enhanced(self, page: fitz.Page, page_num: int) -> Dict[str, Any]:
        """Extract page content using enhanced extractor."""
        try:
            # Use enhanced extractor if available
            extraction_result = self.extractor.extract_text_with_coordinates(page)
            
            return {
                "page": page_num,
                "text": extraction_result.get("text", ""),
                "coordinates": extraction_result.get("coordinates", {}),
                "metadata": extraction_result.get("metadata", {}),
                "tables": extraction_result.get("tables", []),
                "images": extraction_result.get("images", [])
            }
            
        except Exception as e:
            self.logger.warning(f"Enhanced extraction failed for page {page_num}: {e}")
            return self._extract_page_basic(page, page_num)
    
    def _extract_page_basic(self, page: fitz.Page, page_num: int) -> Dict[str, Any]:
        """Extract page content using basic PyMuPDF."""
        try:
            # Get text with character details
            text_dict = page.get_text("dict")
            
            # Extract plain text
            text = page.get_text()
            
            # Build character-level coordinates
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
            
            return {
                "page": page_num,
                "text": text,
                "coordinates": coordinates,
                "metadata": {
                    "method": "basic_pymupdf",
                    "char_count": len(coordinates)
                },
                "tables": [],
                "images": []
            }
            
        except Exception as e:
            self.logger.error(f"Basic extraction failed for page {page_num}: {e}")
            return {
                "page": page_num,
                "text": "",
                "coordinates": {},
                "metadata": {"error": str(e)},
                "tables": [],
                "images": []
            }


class OCRExtractionStrategy(ExtractionStrategy):
    """OCR-based extraction strategy for images and poor-quality PDFs."""
    
    def __init__(self, settings=None):
        """Initialize OCR extraction strategy."""
        super().__init__("ocr")
        self.settings = settings
        
        # Initialize OCR extractor if available
        if OCRBasedExtractor and OCR_DEPENDENCIES_AVAILABLE:
            try:
                self.extractor = OCRBasedExtractor(settings)
            except Exception as e:
                self.logger.warning(f"Failed to initialize OCR extractor: {e}")
                self.extractor = None
        else:
            self.extractor = None
    
    def is_available(self) -> bool:
        """Check if OCR dependencies are available."""
        return OCR_DEPENDENCIES_AVAILABLE and self.extractor is not None
    
    def extract(self, document: UnifiedDocument) -> Dict[str, Any]:
        """Extract text using OCR with coordinate mapping."""
        if not self.is_available():
            return {
                "success": False,
                "error": "OCR dependencies not available",
                "text": "",
                "pages": [],
                "metadata": {"extractor": "ocr", "error": "dependencies_missing"},
                "coordinates": {},
                "quality_score": 0.0
            }
        
        start_time = datetime.now()
        
        try:
            self.logger.info(f"Extracting text with OCR: {document.file_name}")
            
            # Use original OCR extractor
            extraction_result = self.extractor.extract_content(document.file_path)
            
            if not extraction_result or not extraction_result.get("success", False):
                raise Exception("OCR extraction failed")
            
            # Process OCR results
            result = {
                "success": True,
                "text": extraction_result.get("text", ""),
                "pages": extraction_result.get("pages", []),
                "metadata": {
                    "extractor": "ocr",
                    "page_count": len(extraction_result.get("pages", [])),
                    "extraction_time": 0.0,
                    "confidence": extraction_result.get("confidence", 0.0)
                },
                "coordinates": extraction_result.get("coordinates", {}),
                "quality_score": extraction_result.get("confidence", 0.0) / 100.0  # Convert to 0-1 scale
            }
            
            # Update document metadata
            document.metadata.extraction_method = "ocr"
            document.metadata.total_characters = len(result["text"])
            document.metadata.total_words = len(result["text"].split())
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            result["metadata"]["extraction_time"] = processing_time
            
            # Update statistics
            self._update_stats(processing_time, True, result["quality_score"])
            
            self.logger.info(f"OCR extraction completed: {len(result['text'])} characters")
            return result
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            self._update_stats(processing_time, False)
            
            self.logger.error(f"OCR extraction failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "text": "",
                "pages": [],
                "metadata": {"extractor": "ocr", "error": str(e)},
                "coordinates": {},
                "quality_score": 0.0
            }


class UnstructuredExtractionStrategy(ExtractionStrategy):
    """Unstructured.io extraction strategy for advanced document structure detection."""
    
    def __init__(self, settings=None):
        """Initialize Unstructured extraction strategy."""
        super().__init__("unstructured")
        self.settings = settings
        
        # Initialize Unstructured extractor if available
        if UnstructuredExtractor and UNSTRUCTURED_AVAILABLE:
            try:
                self.extractor = UnstructuredExtractor(settings)
            except Exception as e:
                self.logger.warning(f"Failed to initialize Unstructured extractor: {e}")
                self.extractor = None
        else:
            self.extractor = None
    
    def is_available(self) -> bool:
        """Check if Unstructured dependencies are available."""
        return UNSTRUCTURED_AVAILABLE and self.extractor is not None
    
    def extract(self, document: UnifiedDocument) -> Dict[str, Any]:
        """Extract text using Unstructured with advanced document understanding."""
        if not self.is_available():
            return {
                "success": False,
                "error": "Unstructured dependencies not available",
                "text": "",
                "pages": [],
                "metadata": {"extractor": "unstructured", "error": "dependencies_missing"},
                "coordinates": {},
                "quality_score": 0.0
            }
        
        start_time = datetime.now()
        
        try:
            self.logger.info(f"Extracting text with Unstructured: {document.file_name}")
            
            # Use original Unstructured extractor
            extraction_result = self.extractor.extract_content(document.file_path)
            
            if not extraction_result or not extraction_result.get("success", False):
                raise Exception("Unstructured extraction failed")
            
            # Process Unstructured results
            result = {
                "success": True,
                "text": extraction_result.get("text", ""),
                "pages": extraction_result.get("pages", []),
                "metadata": {
                    "extractor": "unstructured",
                    "page_count": len(extraction_result.get("pages", [])),
                    "extraction_time": 0.0,
                    "elements": extraction_result.get("elements", [])
                },
                "coordinates": extraction_result.get("coordinates", {}),
                "quality_score": 0.9  # Unstructured typically provides high quality
            }
            
            # Update document metadata with detected elements
            elements = extraction_result.get("elements", [])
            document.metadata.extraction_method = "unstructured"
            document.metadata.total_characters = len(result["text"])
            document.metadata.total_words = len(result["text"].split())
            
            # Count different element types
            element_counts = {}
            for element in elements:
                element_type = element.get("type", "unknown")
                element_counts[element_type] = element_counts.get(element_type, 0) + 1
            
            # Update specific counts
            document.metadata.total_tables = element_counts.get("Table", 0)
            document.metadata.total_images = element_counts.get("Image", 0)
            document.metadata.total_paragraphs = element_counts.get("NarrativeText", 0)
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            result["metadata"]["extraction_time"] = processing_time
            
            # Update statistics
            self._update_stats(processing_time, True, result["quality_score"])
            
            self.logger.info(f"Unstructured extraction completed: {len(result['text'])} characters")
            return result
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            self._update_stats(processing_time, False)
            
            self.logger.error(f"Unstructured extraction failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "text": "",
                "pages": [],
                "metadata": {"extractor": "unstructured", "error": str(e)},
                "coordinates": {},
                "quality_score": 0.0
            }


def get_available_strategies(settings=None) -> Dict[str, ExtractionStrategy]:
    """Get all available extraction strategies."""
    strategies = {}
    
    # PyMuPDF is always available
    strategies["pymupdf"] = PyMuPDFExtractionStrategy(settings)
    
    # OCR if dependencies available
    ocr_strategy = OCRExtractionStrategy(settings)
    if ocr_strategy.is_available():
        strategies["ocr"] = ocr_strategy
    
    # Unstructured if dependencies available
    unstructured_strategy = UnstructuredExtractionStrategy(settings)
    if unstructured_strategy.is_available():
        strategies["unstructured"] = unstructured_strategy
    
    return strategies


def get_best_strategy_for_document(document: UnifiedDocument, 
                                 available_strategies: Dict[str, ExtractionStrategy]) -> Optional[ExtractionStrategy]:
    """
    Select the best extraction strategy for a document based on its characteristics.
    
    Args:
        document: Document to analyze
        available_strategies: Available extraction strategies
        
    Returns:
        Best strategy for the document, or None if none available
    """
    file_type = document.metadata.file_type.lower()
    
    # Strategy preference based on file type
    if file_type == ".pdf":
        # For PDFs, prefer Unstructured > OCR > PyMuPDF
        for strategy_name in ["unstructured", "ocr", "pymupdf"]:
            if strategy_name in available_strategies:
                return available_strategies[strategy_name]
    
    elif file_type in [".docx", ".odt", ".rtf"]:
        # For Office documents, prefer Unstructured > PyMuPDF
        for strategy_name in ["unstructured", "pymupdf"]:
            if strategy_name in available_strategies:
                return available_strategies[strategy_name]
    
    else:
        # For other formats, try OCR first
        for strategy_name in ["ocr", "unstructured", "pymupdf"]:
            if strategy_name in available_strategies:
                return available_strategies[strategy_name]
    
    # Fallback to any available strategy
    if available_strategies:
        return next(iter(available_strategies.values()))
    
    return None