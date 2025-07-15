"""
OCR Service Integration for Manual Validation Interface.

This module provides comprehensive OCR service integration with multi-engine support,
worker thread architecture, and quality assessment for manual validation workflows.
"""

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
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
    logging.warning(f"Tesseract not available: {e}")

try:
    import easyocr
    _easyocr_available = True
except (ImportError, ValueError) as e:
    _easyocr_available = False
    logging.warning(f"EasyOCR not available: {e}")

from .drawing_state import DrawingArea


class OCREngine(Enum):
    """Available OCR engines."""
    TESSERACT = "tesseract"
    EASYOCR = "easyocr"
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
            logging.warning("No OCR engines available - OCR functionality will be limited")
    
    def add_request(self, request: ValidationOCRRequest):
        """Add OCR request to processing queue."""
        with QMutex():
            self._requests_queue.append(request)
            self._wait_condition.wakeOne()
    
    def cancel_request(self, request_id: str):
        """Cancel specific OCR request."""
        with QMutex():
            self._cancelled_requests.add(request_id)
            # Remove from queue if pending
            self._requests_queue = [req for req in self._requests_queue 
                                   if req.request_id != request_id]
    
    def clear_queue(self):
        """Clear all pending requests."""
        with QMutex():
            self._requests_queue.clear()
            self._cancelled_requests.clear()
    
    def run(self):
        """Main thread execution loop."""
        self._is_running = True
        
        while self._is_running:
            request = None
            
            with QMutex():
                if self._requests_queue:
                    request = self._requests_queue.pop(0)
                else:
                    self._wait_condition.wait(self._mutex, 1000)  # Wait 1 second
            
            if request and request.request_id not in self._cancelled_requests:
                self._current_request = request
                self._process_request(request)
                self._current_request = None
    
    def _process_request(self, request: ValidationOCRRequest):
        """Process single OCR request."""
        start_time = time.time()
        
        try:
            # Check if request was cancelled
            if request.request_id in self._cancelled_requests:
                return
            
            self.progress_updated.emit(request.request_id, 0.1)
            
            # Load and preprocess image
            image = self._load_image(request)
            if image is None:
                raise ValueError("Failed to load image")
            
            self.progress_updated.emit(request.request_id, 0.3)
            
            # Apply preprocessing if requested
            if request.preprocessing:
                image = self._preprocess_image(image)
            
            self.progress_updated.emit(request.request_id, 0.5)
            
            # Select OCR engine
            engine = self._select_engine(request.engine)
            
            # Perform OCR
            text, confidence, word_confidences, bounding_boxes = self._perform_ocr(
                image, engine, request.language
            )
            
            self.progress_updated.emit(request.request_id, 0.8)
            
            # Calculate quality score
            quality_score = self._calculate_quality_score(
                text, confidence, word_confidences, image
            )
            
            processing_time = time.time() - start_time
            
            # Create response
            response = ValidationOCRResponse(
                request_id=request.request_id,
                text=text,
                confidence=confidence,
                engine_used=engine,
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
                engine_used=OCREngine.AUTO,
                processing_time=processing_time,
                quality_score=0.0,
                error_message=str(e)
            )
            self.result_ready.emit(error_response)
            self.error_occurred.emit(request.request_id, str(e))
    
    def _load_image(self, request: ValidationOCRRequest) -> Optional[np.ndarray]:
        """Load image from request data."""
        try:
            if request.image_data:
                # Convert bytes to numpy array
                nparr = np.frombuffer(request.image_data, np.uint8)
                image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            elif request.image_path:
                # Load from file path
                image = cv2.imread(request.image_path)
            else:
                return None
            
            # Extract area if specified
            if request.area:
                area = request.area
                image = image[area.y:area.y+area.height, area.x:area.x+area.width]
            
            return image
            
        except Exception as e:
            logging.error(f"Failed to load image: {e}")
            return None
    
    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Apply image preprocessing for better OCR results."""
        try:
            # Convert to PIL Image for processing
            if len(image.shape) == 3:
                pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            else:
                pil_image = Image.fromarray(image)
            
            # Apply preprocessing steps
            # 1. Enhance contrast
            enhancer = ImageEnhance.Contrast(pil_image)
            pil_image = enhancer.enhance(1.2)
            
            # 2. Apply sharpening
            pil_image = pil_image.filter(ImageFilter.SHARPEN)
            
            # 3. Convert to grayscale
            pil_image = pil_image.convert('L')
            
            # 4. Apply denoising
            pil_image = pil_image.filter(ImageFilter.MedianFilter(size=3))
            
            # Convert back to numpy array
            processed_image = np.array(pil_image)
            
            return processed_image
            
        except Exception as e:
            logging.warning(f"Image preprocessing failed: {e}")
            return image
    
    def _select_engine(self, requested_engine: OCREngine) -> OCREngine:
        """Select appropriate OCR engine."""
        if requested_engine == OCREngine.TESSERACT and self._tesseract_engine:
            return OCREngine.TESSERACT
        elif requested_engine == OCREngine.EASYOCR and self._easyocr_engine:
            return OCREngine.EASYOCR
        elif requested_engine == OCREngine.AUTO:
            # Prefer Tesseract for speed, fallback to EasyOCR
            if self._tesseract_engine:
                return OCREngine.TESSERACT
            elif self._easyocr_engine:
                return OCREngine.EASYOCR
        
        # Fallback to any available engine
        if self._tesseract_engine:
            return OCREngine.TESSERACT
        elif self._easyocr_engine:
            return OCREngine.EASYOCR
        else:
            raise RuntimeError("No OCR engines available")
    
    def _perform_ocr(self, image: np.ndarray, engine: OCREngine, language: str) -> Tuple[str, float, List[Tuple[str, float]], List[Dict[str, Any]]]:
        """Perform OCR using specified engine."""
        if engine == OCREngine.TESSERACT:
            return self._tesseract_ocr(image, language)
        elif engine == OCREngine.EASYOCR:
            return self._easyocr_ocr(image, language)
        else:
            raise ValueError(f"Unsupported OCR engine: {engine}")
    
    def _tesseract_ocr(self, image: np.ndarray, language: str) -> Tuple[str, float, List[Tuple[str, float]], List[Dict[str, Any]]]:
        """Perform OCR using Tesseract."""
        try:
            # Convert to PIL Image
            pil_image = Image.fromarray(image)
            
            # Get detailed data
            data = pytesseract.image_to_data(pil_image, output_type=pytesseract.Output.DICT, lang=language)
            
            # Extract text
            text = pytesseract.image_to_string(pil_image, lang=language).strip()
            
            # Calculate confidence and word confidences
            confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
            word_confidences = []
            bounding_boxes = []
            
            for i, word in enumerate(data['text']):
                if word.strip() and int(data['conf'][i]) > 0:
                    word_confidences.append((word, float(data['conf'][i]) / 100.0))
                    bounding_boxes.append({
                        'text': word,
                        'confidence': float(data['conf'][i]) / 100.0,
                        'x': int(data['left'][i]),
                        'y': int(data['top'][i]),
                        'width': int(data['width'][i]),
                        'height': int(data['height'][i])
                    })
            
            overall_confidence = sum(confidences) / len(confidences) / 100.0 if confidences else 0.0
            
            return text, overall_confidence, word_confidences, bounding_boxes
            
        except Exception as e:
            logging.error(f"Tesseract OCR failed: {e}")
            return "", 0.0, [], []
    
    def _easyocr_ocr(self, image: np.ndarray, language: str) -> Tuple[str, float, List[Tuple[str, float]], List[Dict[str, Any]]]:
        """Perform OCR using EasyOCR."""
        try:
            if not self._easyocr_engine:
                raise RuntimeError("EasyOCR engine not initialized")
            
            # Perform OCR
            results = self._easyocr_engine.readtext(image)
            
            # Extract text and confidences
            text_parts = []
            word_confidences = []
            bounding_boxes = []
            confidences = []
            
            for (bbox, text, confidence) in results:
                text_parts.append(text)
                confidences.append(confidence)
                word_confidences.append((text, confidence))
                
                # Calculate bounding box
                x_coords = [point[0] for point in bbox]
                y_coords = [point[1] for point in bbox]
                x, y = int(min(x_coords)), int(min(y_coords))
                width = int(max(x_coords) - min(x_coords))
                height = int(max(y_coords) - min(y_coords))
                
                bounding_boxes.append({
                    'text': text,
                    'confidence': confidence,
                    'x': x,
                    'y': y,
                    'width': width,
                    'height': height
                })
            
            text = ' '.join(text_parts)
            overall_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            return text, overall_confidence, word_confidences, bounding_boxes
            
        except Exception as e:
            logging.error(f"EasyOCR failed: {e}")
            return "", 0.0, [], []
    
    def _calculate_quality_score(self, text: str, confidence: float, 
                               word_confidences: List[Tuple[str, float]], 
                               image: np.ndarray) -> float:
        """Calculate quality score for OCR result."""
        try:
            # Base score from confidence
            quality_score = confidence
            
            # Adjust for text length (longer text might be more reliable)
            text_length_factor = min(len(text) / 100.0, 1.0)
            quality_score = quality_score * 0.7 + text_length_factor * 0.1
            
            # Adjust for word confidence variance (consistent confidence is better)
            if word_confidences:
                confidences = [conf for _, conf in word_confidences]
                variance = np.var(confidences)
                consistency_factor = max(0.0, 1.0 - variance)
                quality_score = quality_score * 0.8 + consistency_factor * 0.2
            
            # Adjust for image quality (simple brightness/contrast check)
            if image is not None:
                mean_brightness = np.mean(image)
                contrast = np.std(image)
                
                # Prefer moderate brightness and good contrast
                brightness_factor = 1.0 - abs(mean_brightness - 128) / 128
                contrast_factor = min(contrast / 50.0, 1.0)
                image_quality = (brightness_factor + contrast_factor) / 2.0
                
                quality_score = quality_score * 0.9 + image_quality * 0.1
            
            return min(max(quality_score, 0.0), 1.0)
            
        except Exception as e:
            logging.warning(f"Quality score calculation failed: {e}")
            return confidence
    
    def stop(self):
        """Stop the worker thread."""
        self._is_running = False
        self._wait_condition.wakeAll()


class ValidationOCRService(QObject):
    """Main OCR service for manual validation workflows."""
    
    result_ready = pyqtSignal(ValidationOCRResponse)
    progress_updated = pyqtSignal(str, float)
    error_occurred = pyqtSignal(str, str)
    queue_updated = pyqtSignal(int)  # queue size
    
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
        # Remove from active requests
        if response.request_id in self._active_requests:
            del self._active_requests[response.request_id]
        
        # Store result
        self._completed_requests[response.request_id] = response
        
        # Update statistics
        if response.error_message:
            self._statistics['failed_requests'] += 1
        else:
            self._statistics['successful_requests'] += 1
            self._statistics['total_processing_time'] += response.processing_time
            
            # Update average confidence
            successful = self._statistics['successful_requests']
            current_avg = self._statistics['average_confidence']
            self._statistics['average_confidence'] = (
                (current_avg * (successful - 1) + response.confidence) / successful
            )
        
        # Emit result
        self.result_ready.emit(response)
        self.queue_updated.emit(len(self._active_requests))
        
        # Execute callback if provided
        request = self._active_requests.get(response.request_id)
        if request and request.callback:
            try:
                request.callback(response)
            except Exception as e:
                logging.error(f"OCR callback failed: {e}")
    
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
        
        # Length factor (prefer reasonable length)
        if 10 <= assessment['length'] <= 1000:
            score += 0.2
        elif assessment['length'] > 0:
            score += 0.1
        
        # Word count factor
        if assessment['word_count'] > 1:
            score += 0.2
        
        # Character diversity
        if assessment['character_diversity'] > 5:
            score += 0.2
        
        # Content variety
        if assessment['has_numbers']:
            score += 0.1
        if assessment['has_uppercase'] and assessment['has_lowercase']:
            score += 0.1
        if assessment['has_punctuation']:
            score += 0.1
        
        # Readability (simple check)
        if assessment['word_count'] > 0:
            avg_word_length = assessment['length'] / assessment['word_count']
            if 3 <= avg_word_length <= 8:
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
            suggestions.append("Consider preprocessing the image (contrast, sharpening)")
        
        if response.quality_score < 0.6:
            suggestions.append("Try a different OCR engine")
        
        if len(response.text) < 10:
            suggestions.append("Ensure the selected area contains sufficient text")
        
        if response.processing_time > 5.0:
            suggestions.append("Consider using a faster OCR engine or reducing image size")
        
        return suggestions