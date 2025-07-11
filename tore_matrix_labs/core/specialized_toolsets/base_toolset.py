#!/usr/bin/env python3
"""
Base toolset class for all specialized content processing tools.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import json
from datetime import datetime

import fitz  # PyMuPDF
from PIL import Image
import numpy as np

from ...config.settings import Settings


class BaseToolset(ABC):
    """Base class for all specialized content processing toolsets."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Common processing parameters
        self.processing_options = {
            'quality': 'high',
            'accuracy': 'maximum',
            'include_context': True,
            'preserve_formatting': True,
            'output_format': 'structured'
        }
        
        # Metrics tracking
        self.metrics = {
            'processed_count': 0,
            'success_count': 0,
            'error_count': 0,
            'processing_time': 0.0,
            'quality_scores': []
        }
        
        self.logger.info(f"{self.__class__.__name__} initialized")
    
    @abstractmethod
    def process_area(self, area_data: Dict, pdf_document: fitz.Document) -> Dict:
        """Process a specific area of content."""
        pass
    
    @abstractmethod
    def extract_content(self, area_data: Dict, pdf_document: fitz.Document) -> Dict:
        """Extract content from the area."""
        pass
    
    @abstractmethod
    def validate_extraction(self, extracted_content: Dict) -> Dict:
        """Validate the extracted content."""
        pass
    
    @abstractmethod
    def get_supported_formats(self) -> List[str]:
        """Get list of supported output formats."""
        pass
    
    def preprocess_area(self, area_data: Dict, pdf_document: fitz.Document) -> Dict:
        """Common preprocessing for all toolsets."""
        try:
            # Extract area image at high resolution
            page_num = area_data.get('page', 1) - 1  # Convert to 0-based
            bbox = area_data.get('bbox', [0, 0, 100, 100])
            
            if page_num >= len(pdf_document):
                raise ValueError(f"Page {page_num + 1} not found in document")
            
            page = pdf_document[page_num]
            area_rect = fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3])
            
            # High-resolution extraction
            matrix = fitz.Matrix(3.0, 3.0)  # 3x zoom for high quality
            pix = page.get_pixmap(matrix=matrix, clip=area_rect)
            
            # Convert to PIL Image
            img_data = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_data))
            
            # Extract text from area for context
            text_content = page.get_text("text", clip=area_rect)
            
            return {
                'image': image,
                'text_content': text_content,
                'area_rect': area_rect,
                'page_number': page_num + 1,
                'resolution': {'width': pix.width, 'height': pix.height},
                'preprocessing_success': True
            }
            
        except Exception as e:
            self.logger.error(f"Preprocessing failed: {e}")
            return {
                'image': None,
                'text_content': '',
                'area_rect': None,
                'page_number': area_data.get('page', 1),
                'resolution': {'width': 0, 'height': 0},
                'preprocessing_success': False,
                'error': str(e)
            }
    
    def postprocess_result(self, result: Dict, area_data: Dict) -> Dict:
        """Common postprocessing for all toolsets."""
        try:
            # Add metadata
            result['metadata'] = {
                'toolset': self.__class__.__name__,
                'processed_at': datetime.now().isoformat(),
                'area_type': area_data.get('type', 'unknown'),
                'page_number': area_data.get('page', 1),
                'processing_options': self.processing_options.copy(),
                'quality_metrics': self._calculate_quality_metrics(result)
            }
            
            # Add validation results
            validation_result = self.validate_extraction(result)
            result['validation'] = validation_result
            
            # Update metrics
            self.metrics['processed_count'] += 1
            if validation_result.get('is_valid', False):
                self.metrics['success_count'] += 1
            else:
                self.metrics['error_count'] += 1
            
            quality_score = result['metadata']['quality_metrics'].get('overall_score', 0)
            self.metrics['quality_scores'].append(quality_score)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Postprocessing failed: {e}")
            result['postprocessing_error'] = str(e)
            return result
    
    def _calculate_quality_metrics(self, result: Dict) -> Dict:
        """Calculate quality metrics for the extraction."""
        metrics = {
            'overall_score': 0.0,
            'completeness': 0.0,
            'accuracy': 0.0,
            'formatting': 0.0,
            'confidence': 0.0
        }
        
        try:
            # Basic completeness check
            if result.get('content'):
                metrics['completeness'] = 80.0
            
            # Basic accuracy check (no obvious errors)
            if not result.get('errors', []):
                metrics['accuracy'] = 90.0
            
            # Basic formatting check
            if result.get('structured_content'):
                metrics['formatting'] = 85.0
            
            # Basic confidence check
            if result.get('confidence_score'):
                metrics['confidence'] = result['confidence_score']
            else:
                metrics['confidence'] = 75.0
            
            # Calculate overall score
            metrics['overall_score'] = (
                metrics['completeness'] * 0.3 +
                metrics['accuracy'] * 0.3 +
                metrics['formatting'] * 0.2 +
                metrics['confidence'] * 0.2
            )
            
        except Exception as e:
            self.logger.error(f"Quality metrics calculation failed: {e}")
        
        return metrics
    
    def get_processing_statistics(self) -> Dict:
        """Get processing statistics for this toolset."""
        avg_quality = (
            sum(self.metrics['quality_scores']) / len(self.metrics['quality_scores'])
            if self.metrics['quality_scores'] else 0.0
        )
        
        return {
            'toolset': self.__class__.__name__,
            'total_processed': self.metrics['processed_count'],
            'successful': self.metrics['success_count'],
            'failed': self.metrics['error_count'],
            'success_rate': (
                self.metrics['success_count'] / self.metrics['processed_count']
                if self.metrics['processed_count'] > 0 else 0.0
            ),
            'average_quality': avg_quality,
            'total_processing_time': self.metrics['processing_time']
        }
    
    def reset_metrics(self):
        """Reset processing metrics."""
        self.metrics = {
            'processed_count': 0,
            'success_count': 0,
            'error_count': 0,
            'processing_time': 0.0,
            'quality_scores': []
        }
        self.logger.info(f"Metrics reset for {self.__class__.__name__}")
    
    def save_extraction_result(self, result: Dict, output_path: Path) -> bool:
        """Save extraction result to file."""
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False, default=str)
            
            self.logger.info(f"Extraction result saved to {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save extraction result: {e}")
            return False
    
    def load_extraction_result(self, input_path: Path) -> Optional[Dict]:
        """Load extraction result from file."""
        try:
            if not input_path.exists():
                self.logger.error(f"File not found: {input_path}")
                return None
            
            with open(input_path, 'r', encoding='utf-8') as f:
                result = json.load(f)
            
            self.logger.info(f"Extraction result loaded from {input_path}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to load extraction result: {e}")
            return None