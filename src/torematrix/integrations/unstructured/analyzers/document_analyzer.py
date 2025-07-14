"""
Document analysis for intelligent processing strategy selection.
"""

import mimetypes
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class TechnicalFeatures:
    """Technical characteristics of a document."""
    file_size_mb: float
    file_extension: str
    mime_type: Optional[str]
    estimated_pages: int
    is_text_based: bool
    requires_ocr: bool
    has_images: bool
    has_tables: bool
    encoding: Optional[str] = None


@dataclass 
class ProcessingHints:
    """Hints for optimal processing strategy."""
    recommended_strategy: str
    estimated_processing_time: float
    estimated_memory_mb: float
    parallel_processing: bool
    ocr_required: bool
    special_handling: List[str]


@dataclass
class DocumentAnalysis:
    """Complete document analysis result."""
    file_path: Path
    technical_features: TechnicalFeatures
    processing_hints: ProcessingHints
    confidence_score: float
    analysis_time_ms: float


class DocumentAnalyzer:
    """Analyzes documents to provide processing recommendations."""
    
    def __init__(self):
        # File type classifications
        self.text_based_extensions = {
            '.txt', '.md', '.rst', '.csv', '.json', '.xml', '.html', '.htm'
        }
        
        self.office_extensions = {
            '.docx', '.doc', '.xlsx', '.xls', '.pptx', '.ppt', '.odt', '.ods', '.odp'
        }
        
        self.image_extensions = {
            '.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.tif', '.bmp', '.gif'
        }
        
        # Processing estimates (rough heuristics)
        self.processing_rates = {
            'text': 5.0,      # MB per second
            'office': 2.0,    # MB per second  
            'pdf': 1.0,       # MB per second
            'image': 0.5      # MB per second (OCR)
        }
    
    async def analyze_document(self, file_path: Path) -> DocumentAnalysis:
        """Perform comprehensive document analysis."""
        import time
        start_time = time.time()
        
        # Basic file information
        stat = file_path.stat()
        file_size_mb = stat.st_size / (1024 * 1024)
        extension = file_path.suffix.lower()
        mime_type, _ = mimetypes.guess_type(str(file_path))
        
        # Analyze technical features
        technical_features = self._analyze_technical_features(
            file_path, file_size_mb, extension, mime_type
        )
        
        # Generate processing hints
        processing_hints = self._generate_processing_hints(
            technical_features, file_size_mb
        )
        
        # Calculate confidence score
        confidence_score = self._calculate_confidence(technical_features)
        
        analysis_time_ms = (time.time() - start_time) * 1000
        
        return DocumentAnalysis(
            file_path=file_path,
            technical_features=technical_features,
            processing_hints=processing_hints,
            confidence_score=confidence_score,
            analysis_time_ms=analysis_time_ms
        )
    
    def _analyze_technical_features(self, 
                                  file_path: Path,
                                  file_size_mb: float,
                                  extension: str,
                                  mime_type: Optional[str]) -> TechnicalFeatures:
        """Analyze technical characteristics of the document."""
        
        # Determine file type characteristics
        is_text_based = extension in self.text_based_extensions
        requires_ocr = False
        has_images = False
        has_tables = False
        
        # Estimate pages based on file size and type
        if extension == '.pdf':
            estimated_pages = max(1, int(file_size_mb * 20))  # ~50KB per page
            requires_ocr = file_size_mb > 1.0  # Assume large PDFs might need OCR
            has_images = True
            has_tables = True
        elif extension in self.office_extensions:
            estimated_pages = max(1, int(file_size_mb * 10))  # ~100KB per page
            has_tables = extension in {'.xlsx', '.xls', '.ods'}
        elif extension in self.text_based_extensions:
            estimated_pages = max(1, int(file_size_mb * 100))  # ~10KB per page
        elif extension in self.image_extensions:
            estimated_pages = 1
            requires_ocr = True
            has_images = True
        else:
            estimated_pages = 1
        
        return TechnicalFeatures(
            file_size_mb=file_size_mb,
            file_extension=extension,
            mime_type=mime_type,
            estimated_pages=estimated_pages,
            is_text_based=is_text_based,
            requires_ocr=requires_ocr,
            has_images=has_images,
            has_tables=has_tables,
            encoding='utf-8' if is_text_based else None
        )
    
    def _generate_processing_hints(self, 
                                 features: TechnicalFeatures,
                                 file_size_mb: float) -> ProcessingHints:
        """Generate processing strategy hints based on analysis."""
        
        # Determine recommended strategy
        if features.requires_ocr:
            recommended_strategy = "hi_res"
        elif features.has_tables:
            recommended_strategy = "hi_res"
        elif features.is_text_based:
            recommended_strategy = "fast"
        elif file_size_mb > 50:
            recommended_strategy = "auto"  # Let unstructured decide
        else:
            recommended_strategy = "fast"
        
        # Estimate processing time
        if features.file_extension == '.pdf' and features.requires_ocr:
            processing_rate = self.processing_rates['image']
        elif features.file_extension in {'.docx', '.xlsx', '.pptx'}:
            processing_rate = self.processing_rates['office']
        elif features.is_text_based:
            processing_rate = self.processing_rates['text']
        else:
            processing_rate = self.processing_rates['pdf']
        
        estimated_time = max(1.0, file_size_mb / processing_rate)
        
        # Estimate memory usage
        base_memory = max(100, file_size_mb * 3)  # 3x file size as base
        if features.requires_ocr:
            base_memory *= 2  # OCR uses more memory
        if features.has_images:
            base_memory *= 1.5  # Image processing overhead
        
        # Special handling requirements
        special_handling = []
        if features.requires_ocr:
            special_handling.append("ocr_processing")
        if features.has_tables:
            special_handling.append("table_extraction")
        if file_size_mb > 100:
            special_handling.append("large_file_handling")
        if features.estimated_pages > 500:
            special_handling.append("chunked_processing")
        
        return ProcessingHints(
            recommended_strategy=recommended_strategy,
            estimated_processing_time=estimated_time,
            estimated_memory_mb=base_memory,
            parallel_processing=file_size_mb > 10,
            ocr_required=features.requires_ocr,
            special_handling=special_handling
        )
    
    def _calculate_confidence(self, features: TechnicalFeatures) -> float:
        """Calculate confidence score for analysis accuracy."""
        confidence = 0.8  # Base confidence
        
        # Higher confidence for known file types
        if features.file_extension in (
            self.text_based_extensions | 
            self.office_extensions | 
            self.image_extensions
        ):
            confidence += 0.15
        
        # Lower confidence for very large or very small files
        if features.file_size_mb > 500:
            confidence -= 0.1
        elif features.file_size_mb < 0.001:  # < 1KB
            confidence -= 0.2
        
        # Adjust based on complexity
        if features.has_images and features.has_tables:
            confidence -= 0.05  # More complex, less certain
        
        return max(0.1, min(1.0, confidence))  # Clamp to [0.1, 1.0]