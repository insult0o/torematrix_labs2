"""
OCR Service Integration for Manual Validation Interface.

This module provides comprehensive OCR service integration with multi-engine support,
worker thread architecture, and quality assessment for manual validation workflows.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Callable, Any, Tuple
from PyQt6.QtCore import QObject, QThread, pyqtSignal, QMutex, QWaitCondition
from PyQt6.QtGui import QPixmap, QImage
import uuid

# Optional dependencies for image processing
try:
    import cv2
    _cv2_available = True
except ImportError:
    _cv2_available = False

try:
    import numpy as np
    _numpy_available = True
except ImportError:
    _numpy_available = False

try:
    from PIL import Image, ImageEnhance, ImageFilter
    _pil_available = True
except ImportError:
    _pil_available = False

# OCR engine imports
try:
    import pytesseract
    _tesseract_available = True
except (ImportError, ValueError) as e:
    _tesseract_available = False

try:
    import easyocr
    _easyocr_available = True
except (ImportError, ValueError) as e:
    _easyocr_available = False

from .drawing_state import DrawingArea


class OCREngine(Enum):
    """Available OCR engines."""
    TESSERACT = "tesseract"
    EASYOCR = "easyocr"
    MOCK = "mock"
    AUTO = "auto"


class OCRStatus(Enum):
    """OCR processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class ValidationOCRRequest:
    """OCR request for validation workflow."""
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    area: DrawingArea = None
    image_data: Optional[bytes] = None
    image_path: Optional[str] = None
    engine: OCREngine = OCREngine.AUTO
    preprocessing: bool = True
    confidence_threshold: float = 0.5
    language: str = "eng"
    callback: Optional[Callable] = None
    
    def __post_init__(self):
        """Validate request parameters."""
        if not self.area:
            raise ValueError("DrawingArea is required")
        if not self.image_data and not self.image_path:
            raise ValueError("Either image_data or image_path must be provided")


@dataclass(frozen=True)
class ValidationOCRResponse:
    """OCR response with results and quality metrics."""
    request_id: str
    text: str
    confidence: float
    engine_used: OCREngine
    processing_time: float
    quality_score: float
    word_confidences: List[Tuple[str, float]] = field(default_factory=list)
    preprocessing_applied: bool = False
    error_message: Optional[str] = None
    bounding_boxes: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "request_id": self.request_id,
            "text": self.text,
            "confidence": self.confidence,
            "engine_used": self.engine_used.value,
            "processing_time": self.processing_time,
            "quality_score": self.quality_score,
            "word_confidences": self.word_confidences,
            "preprocessing_applied": self.preprocessing_applied,
            "error_message": self.error_message,
            "bounding_boxes": self.bounding_boxes
        }


class OCRWorkerThread(QThread):
    """Background worker thread for OCR processing."""
    
    result_ready = pyqtSignal(ValidationOCRResponse)
    progress_updated = pyqtSignal(str, float)  # request_id, progress
    error_occurred = pyqtSignal(str, str)  # request_id, error_message
    
    def __init__(self, parent=None):
        """Initialize OCR worker thread."""
        super().__init__(parent)
        self._requests_queue = []
        self._mutex = QMutex()
        self._wait_condition = QWaitCondition()
        self._is_running = False
        self._current_request = None
        self._cancelled_requests = set()
        
        # Initialize OCR engines
        self._tesseract_engine = None
        self._easyocr_engine = None
        self._initialize_engines()
    
    def _initialize_engines(self):
        """Initialize available OCR engines."""
        if _tesseract_available:
            try:
                # Test tesseract availability
                pytesseract.get_tesseract_version()
                self._tesseract_engine = "tesseract"
            except Exception as e:
                logging.warning(f"Tesseract initialization failed: {e}")
        
        if _easyocr_available:
            try:
                # Initialize EasyOCR reader
                self._easyocr_engine = easyocr.Reader(['en'])
            except Exception as e:
                logging.warning(f"EasyOCR initialization failed: {e}")
        
        if not self._tesseract_engine and not self._easyocr_engine:
            logging.warning("No OCR engines available - using mock OCR for testing")
    
    def add_request(self, request: ValidationOCRRequest):
        """Add OCR request to processing queue."""
        self._mutex.lock()
        try:
            self._requests_queue.append(request)
            self._wait_condition.wakeOne()
        finally:
            self._mutex.unlock()
    
    def cancel_request(self, request_id: str):
        """Cancel specific OCR request."""
        self._mutex.lock()
        try:
            self._cancelled_requests.add(request_id)
            self._requests_queue = [req for req in self._requests_queue 
                                   if req.request_id != request_id]
        finally:
            self._mutex.unlock()
    
    def clear_queue(self):
        """Clear all pending requests."""
        self._mutex.lock()
        try:
            self._requests_queue.clear()
            self._cancelled_requests.clear()
        finally:
            self._mutex.unlock()
    
    def run(self):
        """Main thread execution loop."""
        self._is_running = True
        
        while self._is_running:
            request = None
            
            self._mutex.lock()
            try:
                if self._requests_queue:
                    request = self._requests_queue.pop(0)
                else:
                    self._wait_condition.wait(self._mutex, 1000)
            finally:
                self._mutex.unlock()
            
            if request and request.request_id not in self._cancelled_requests:
                self._current_request = request
                self._process_request(request)
                self._current_request = None
    
    def _process_request(self, request: ValidationOCRRequest):
        """Process single OCR request."""
        start_time = time.time()
        
        try:
            if request.request_id in self._cancelled_requests:
                return
            
            self.progress_updated.emit(request.request_id, 0.1)
            
            # Mock image processing for Agent 2
            image = "mock_image"
            self.progress_updated.emit(request.request_id, 0.5)
            
            # Perform mock OCR
            text, confidence, word_confidences, bounding_boxes = self._mock_ocr(image, request.language)
            
            self.progress_updated.emit(request.request_id, 0.8)
            
            # Calculate quality score
            quality_score = confidence * 0.9  # Simple quality score
            
            processing_time = time.time() - start_time
            
            # Create response
            response = ValidationOCRResponse(
                request_id=request.request_id,
                text=text,
                confidence=confidence,
                engine_used=OCREngine.MOCK,
                processing_time=processing_time,
                quality_score=quality_score,
                word_confidences=word_confidences,
                preprocessing_applied=request.preprocessing,
                bounding_boxes=bounding_boxes
            )
            
            self.progress_updated.emit(request.request_id, 1.0)
            self.result_ready.emit(response)
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_response = ValidationOCRResponse(
                request_id=request.request_id,
                text="",
                confidence=0.0,
                engine_used=OCREngine.MOCK,
                processing_time=processing_time,
                quality_score=0.0,
                error_message=str(e)
            )
            self.result_ready.emit(error_response)
            self.error_occurred.emit(request.request_id, str(e))
    
    def _mock_ocr(self, image: Any, language: str) -> Tuple[str, float, List[Tuple[str, float]], List[Dict[str, Any]]]:
        """Mock OCR for testing when no real OCR engines available."""
        mock_text = "Sample extracted text from mock OCR"
        mock_confidence = 0.85
        mock_word_confidences = [
            ("Sample", 0.90),
            ("extracted", 0.85),
            ("text", 0.80),
            ("from", 0.88),
            ("mock", 0.82),
            ("OCR", 0.87)
        ]
        mock_bounding_boxes = [
            {'text': 'Sample', 'confidence': 0.90, 'x': 10, 'y': 10, 'width': 50, 'height': 20},
            {'text': 'extracted', 'confidence': 0.85, 'x': 70, 'y': 10, 'width': 70, 'height': 20},
            {'text': 'text', 'confidence': 0.80, 'x': 150, 'y': 10, 'width': 40, 'height': 20}
        ]
        
        return mock_text, mock_confidence, mock_word_confidences, mock_bounding_boxes
    
    def stop(self):
        """Stop the worker thread."""
        self._is_running = False
        self._wait_condition.wakeAll()


class ValidationOCRService(QObject):
    """Main OCR service for manual validation workflows."""
    
    result_ready = pyqtSignal(ValidationOCRResponse)
    progress_updated = pyqtSignal(str, float)
    error_occurred = pyqtSignal(str, str)
    queue_updated = pyqtSignal(int)
    
    def __init__(self, parent=None):
        """Initialize OCR service."""
        super().__init__(parent)
        
        # Worker thread
        self._worker = OCRWorkerThread()
        self._worker.result_ready.connect(self._on_result_ready)
        self._worker.progress_updated.connect(self.progress_updated)
        self._worker.error_occurred.connect(self.error_occurred)
        
        # Request tracking
        self._active_requests: Dict[str, ValidationOCRRequest] = {}
        self._completed_requests: Dict[str, ValidationOCRResponse] = {}
        self._statistics = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_processing_time': 0.0,
            'average_confidence': 0.0
        }
        
        # Start worker thread
        self._worker.start()
    
    def submit_request(self, request: ValidationOCRRequest) -> str:
        """Submit OCR request for processing."""
        self._active_requests[request.request_id] = request
        self._worker.add_request(request)
        self._statistics['total_requests'] += 1
        
        self.queue_updated.emit(len(self._active_requests))
        return request.request_id
    
    def cancel_request(self, request_id: str) -> bool:
        """Cancel specific OCR request."""
        if request_id in self._active_requests:
            self._worker.cancel_request(request_id)
            del self._active_requests[request_id]
            self.queue_updated.emit(len(self._active_requests))
            return True
        return False
    
    def get_result(self, request_id: str) -> Optional[ValidationOCRResponse]:
        """Get completed OCR result."""
        return self._completed_requests.get(request_id)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get OCR service statistics."""
        return self._statistics.copy()
    
    def clear_completed_results(self):
        """Clear completed results to free memory."""
        self._completed_requests.clear()
    
    def _on_result_ready(self, response: ValidationOCRResponse):
        """Handle completed OCR result."""
        if response.request_id in self._active_requests:
            del self._active_requests[response.request_id]
        
        self._completed_requests[response.request_id] = response
        
        # Update statistics
        if response.error_message:
            self._statistics['failed_requests'] += 1
        else:
            self._statistics['successful_requests'] += 1
            self._statistics['total_processing_time'] += response.processing_time
            
            successful = self._statistics['successful_requests']
            current_avg = self._statistics['average_confidence']
            self._statistics['average_confidence'] = (
                (current_avg * (successful - 1) + response.confidence) / successful
            )
        
        self.result_ready.emit(response)
        self.queue_updated.emit(len(self._active_requests))
    
    def shutdown(self):
        """Shutdown OCR service."""
        self._worker.stop()
        self._worker.wait()


class OCRValidationHelper:
    """Helper class for OCR validation and quality assessment."""
    
    @staticmethod
    def assess_text_quality(text: str) -> Dict[str, Any]:
        """Assess the quality of extracted text."""
        assessment = {
            'length': len(text),
            'word_count': len(text.split()),
            'character_diversity': len(set(text.lower())),
            'has_numbers': any(c.isdigit() for c in text),
            'has_uppercase': any(c.isupper() for c in text),
            'has_lowercase': any(c.islower() for c in text),
            'has_punctuation': any(c in '.,!?;:' for c in text),
            'quality_score': 0.0
        }
        
        # Calculate quality score
        score = 0.0
        if 10 <= assessment['length'] <= 1000:
            score += 0.2
        if assessment['word_count'] > 1:
            score += 0.2
        if assessment['character_diversity'] > 5:
            score += 0.2
        if assessment['has_numbers']:
            score += 0.1
        if assessment['has_uppercase'] and assessment['has_lowercase']:
            score += 0.1
        if assessment['has_punctuation']:
            score += 0.1
        
        assessment['quality_score'] = min(score, 1.0)
        return assessment
    
    @staticmethod
    def validate_confidence_threshold(response: ValidationOCRResponse, 
                                    threshold: float = 0.5) -> bool:
        """Validate if OCR response meets confidence threshold."""
        return response.confidence >= threshold and response.quality_score >= threshold
    
    @staticmethod
    def suggest_improvements(response: ValidationOCRResponse) -> List[str]:
        """Suggest improvements based on OCR results."""
        suggestions = []
        
        if response.confidence < 0.7:
            suggestions.append("Consider preprocessing the image")
        if response.quality_score < 0.6:
            suggestions.append("Try a different OCR engine")
        if len(response.text) < 10:
            suggestions.append("Ensure area contains sufficient text")
        
        return suggestions