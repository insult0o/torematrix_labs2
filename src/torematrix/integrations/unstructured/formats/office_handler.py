"""
Office Handler for Agent 4 - Microsoft Office document processing.
"""

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Any, Optional, Dict, Tuple

logger = logging.getLogger(__name__)


@dataclass
class OfficeFeatures:
    """Features detected in Office documents."""
    document_type: str = "unknown"  # docx, xlsx, pptx
    has_images: bool = False
    has_tables: bool = False
    has_charts: bool = False
    has_headers_footers: bool = False
    has_comments: bool = False
    has_track_changes: bool = False
    page_count: int = 0
    slide_count: int = 0
    sheet_count: int = 0
    word_count: int = 0


class OfficeHandler:
    """Microsoft Office document handler."""
    
    def __init__(self, client=None):
        self.client = client
        
    async def process(self, file_path: Path, **kwargs) -> Tuple[List[Any], OfficeFeatures]:
        """Process Office documents with format-specific handling."""
        try:
            # Analyze document features
            features = await self._analyze_office_features(file_path)
            
            # Process based on document type
            if features.document_type == "docx":
                elements = await self._process_word_document(file_path, features, **kwargs)
            elif features.document_type == "xlsx":
                elements = await self._process_excel_document(file_path, features, **kwargs)
            elif features.document_type == "pptx":
                elements = await self._process_powerpoint_document(file_path, features, **kwargs)
            else:
                elements = await self._process_generic_office(file_path, features, **kwargs)
            
            logger.info(f"Office document processed: {features.document_type}, {len(elements)} elements")
            return elements, features
            
        except Exception as e:
            logger.error(f"Office processing failed for {file_path}: {e}")
            return [self._create_fallback_element(file_path, str(e))], OfficeFeatures()
    
    async def _analyze_office_features(self, file_path: Path) -> OfficeFeatures:
        """Analyze Office document to detect features."""
        features = OfficeFeatures()
        
        try:
            suffix = file_path.suffix.lower()
            
            if suffix == '.docx':
                features.document_type = "docx"
                features = await self._analyze_word_features(file_path, features)
            elif suffix == '.xlsx':
                features.document_type = "xlsx"
                features = await self._analyze_excel_features(file_path, features)
            elif suffix == '.pptx':
                features.document_type = "pptx"
                features = await self._analyze_powerpoint_features(file_path, features)
            elif suffix in ['.doc', '.xls', '.ppt']:
                features.document_type = suffix[1:]  # Remove dot
                features = await self._analyze_legacy_features(file_path, features)
            
            return features
            
        except Exception as e:
            logger.warning(f"Office analysis failed: {e}")
            return OfficeFeatures()
    
    async def _analyze_word_features(self, file_path: Path, features: OfficeFeatures) -> OfficeFeatures:
        """Analyze Word document features."""
        # Simulate analysis (would use python-docx in production)
        file_size = file_path.stat().st_size
        
        features.page_count = max(1, file_size // (20 * 1024))  # Rough estimate
        features.word_count = max(100, file_size // 10)  # Rough estimate
        
        # Feature detection based on filename patterns
        filename = file_path.name.lower()
        if 'table' in filename:
            features.has_tables = True
        if 'image' in filename or 'photo' in filename:
            features.has_images = True
        if 'comment' in filename or 'review' in filename:
            features.has_comments = True
            
        return features
    
    async def _analyze_excel_features(self, file_path: Path, features: OfficeFeatures) -> OfficeFeatures:
        """Analyze Excel document features."""
        file_size = file_path.stat().st_size
        
        features.sheet_count = max(1, min(10, file_size // (50 * 1024)))  # Estimate sheets
        
        # Most Excel files have tables by nature
        features.has_tables = True
        
        filename = file_path.name.lower()
        if 'chart' in filename or 'graph' in filename:
            features.has_charts = True
            
        return features
    
    async def _analyze_powerpoint_features(self, file_path: Path, features: OfficeFeatures) -> OfficeFeatures:
        """Analyze PowerPoint document features."""
        file_size = file_path.stat().st_size
        
        features.slide_count = max(1, file_size // (100 * 1024))  # Rough estimate
        
        # PowerPoint files commonly have images
        features.has_images = True
        
        filename = file_path.name.lower()
        if 'chart' in filename:
            features.has_charts = True
        if 'table' in filename:
            features.has_tables = True
            
        return features
    
    async def _analyze_legacy_features(self, file_path: Path, features: OfficeFeatures) -> OfficeFeatures:
        """Analyze legacy Office formats."""
        # Legacy formats require special handling
        logger.warning(f"Legacy Office format detected: {file_path.suffix}")
        features.has_track_changes = True  # Assume complexity
        return features
    
    async def _process_word_document(self, file_path: Path, features: OfficeFeatures, **kwargs) -> List[Any]:
        """Process Word documents."""
        if self.client:
            return await self.client.parse_document(
                file_path,
                strategy="hi_res",
                extract_tables=features.has_tables,
                **kwargs
            )
        else:
            # Fallback Word processing
            elements = [
                self._create_element("Title", f"Word Document: {file_path.stem}"),
                self._create_element("NarrativeText", f"Document with {features.page_count} pages"),
                self._create_element("NarrativeText", f"Estimated {features.word_count} words")
            ]
            
            if features.has_tables:
                elements.extend([
                    self._create_element("Table", "Table detected in document"),
                    self._create_element("TableCell", "Header 1"),
                    self._create_element("TableCell", "Data 1")
                ])
                
            if features.has_images:
                elements.append(self._create_element("Image", "Image detected in document"))
                
            if features.has_comments:
                elements.append(self._create_element("Comment", "Comments found in document"))
                
            return elements
    
    async def _process_excel_document(self, file_path: Path, features: OfficeFeatures, **kwargs) -> List[Any]:
        """Process Excel documents."""
        if self.client:
            return await self.client.parse_document(
                file_path,
                strategy="hi_res",
                extract_tables=True,
                **kwargs
            )
        else:
            # Fallback Excel processing
            elements = [
                self._create_element("Title", f"Excel Workbook: {file_path.stem}"),
                self._create_element("NarrativeText", f"Workbook with {features.sheet_count} sheets")
            ]
            
            # Simulate sheets
            for i in range(features.sheet_count):
                elements.extend([
                    self._create_element("SheetTitle", f"Sheet {i+1}"),
                    self._create_element("Table", f"Data table in Sheet {i+1}"),
                    self._create_element("TableCell", f"A1: Header {i+1}"),
                    self._create_element("TableCell", f"B1: Data {i+1}")
                ])
                
            if features.has_charts:
                elements.append(self._create_element("Chart", "Chart detected in workbook"))
                
            return elements
    
    async def _process_powerpoint_document(self, file_path: Path, features: OfficeFeatures, **kwargs) -> List[Any]:
        """Process PowerPoint documents."""
        if self.client:
            return await self.client.parse_document(
                file_path,
                strategy="hi_res",
                extract_images=True,
                **kwargs
            )
        else:
            # Fallback PowerPoint processing
            elements = [
                self._create_element("Title", f"PowerPoint Presentation: {file_path.stem}"),
                self._create_element("NarrativeText", f"Presentation with {features.slide_count} slides")
            ]
            
            # Simulate slides
            for i in range(min(features.slide_count, 5)):  # Limit for demo
                elements.extend([
                    self._create_element("SlideTitle", f"Slide {i+1}"),
                    self._create_element("NarrativeText", f"Content from slide {i+1}"),
                ])
                
                if features.has_images:
                    elements.append(self._create_element("Image", f"Image on slide {i+1}"))
                    
                if features.has_tables:
                    elements.append(self._create_element("Table", f"Table on slide {i+1}"))
                    
                if features.has_charts:
                    elements.append(self._create_element("Chart", f"Chart on slide {i+1}"))
                    
            return elements
    
    async def _process_generic_office(self, file_path: Path, features: OfficeFeatures, **kwargs) -> List[Any]:
        """Process generic Office documents."""
        if self.client:
            return await self.client.parse_document(file_path, **kwargs)
        else:
            return [
                self._create_element("Title", f"Office Document: {file_path.stem}"),
                self._create_element("NarrativeText", f"Document type: {features.document_type}"),
                self._create_element("NarrativeText", "Content extracted from Office document")
            ]
    
    def _create_element(self, element_type: str, text: str) -> Any:
        """Create a mock element for fallback processing."""
        from unittest.mock import Mock
        element = Mock()
        element.category = element_type
        element.text = text
        element.metadata = {"agent": "Agent 4 Office Handler"}
        return element
    
    def _create_fallback_element(self, file_path: Path, error: str) -> Any:
        """Create fallback element when processing fails."""
        return self._create_element("Error", f"Office processing failed for {file_path.name}: {error}")