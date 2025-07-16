"""
Comprehensive test suite for OCR Service Integration - Agent 2.

Tests all components of the ValidationOCRService including multi-threading,
quality assessment, and multi-engine support for Issue #240.
"""

import pytest
import time
import uuid
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtTest import QSignalSpy
import numpy as np

from src.torematrix.ui.tools.validation.ocr_service import (
    OCREngine,
    OCRStatus,
    ValidationOCRRequest,
    ValidationOCRResponse,
    OCRWorkerThread,
    ValidationOCRService,
    OCRValidationHelper
)
from src.torematrix.ui.tools.validation.drawing_state import DrawingArea


class TestOCREngine:
    """Test OCR engine enumeration."""
    
    def test_ocr_engine_values(self):
        """Test OCR engine enum values."""
        assert OCREngine.TESSERACT.value == "tesseract"
        assert OCREngine.EASYOCR.value == "easyocr"
        assert OCREngine.AUTO.value == "auto"


class TestOCRStatus:
    """Test OCR status enumeration."""
    
    def test_ocr_status_values(self):
        """Test OCR status enum values."""
        assert OCRStatus.PENDING.value == "pending"
        assert OCRStatus.PROCESSING.value == "processing"
        assert OCRStatus.COMPLETED.value == "completed"
        assert OCRStatus.ERROR.value == "error"
        assert OCRStatus.CANCELLED.value == "cancelled"


class TestValidationOCRRequest:
    """Test OCR request data structure."""
    
    def test_request_creation_with_defaults(self):
        """Test creating request with default values."""
        area = DrawingArea(x=10, y=20, width=100, height=50, page_number=1)
        request = ValidationOCRRequest(
            area=area,
            image_data=b"fake_image_data"
        )
        
        assert request.area == area
        assert request.image_data == b"fake_image_data"
        assert request.engine == OCREngine.AUTO
        assert request.preprocessing is True
        assert request.confidence_threshold == 0.5
        assert request.language == "eng"
        assert request.callback is None
        assert isinstance(request.request_id, str)
    
    def test_request_creation_with_custom_values(self):
        """Test creating request with custom values."""
        area = DrawingArea(x=5, y=15, width=200, height=100, page_number=1)
        callback = Mock()
        
        request = ValidationOCRRequest(
            area=area,
            image_path="/path/to/image.png",
            engine=OCREngine.TESSERACT,
            preprocessing=False,
            confidence_threshold=0.8,
            language="fra",
            callback=callback
        )
        
        assert request.area == area
        assert request.image_path == "/path/to/image.png"
        assert request.engine == OCREngine.TESSERACT
        assert request.preprocessing is False
        assert request.confidence_threshold == 0.8
        assert request.language == "fra"
        assert request.callback == callback
    
    def test_request_validation_missing_area(self):
        """Test request validation fails without area."""
        with pytest.raises(ValueError, match="DrawingArea is required"):
            ValidationOCRRequest(
                area=None,
                image_data=b"fake_data"
            )
    
    def test_request_validation_missing_image(self):
        """Test request validation fails without image data or path."""
        area = DrawingArea(x=0, y=0, width=100, height=50, page_number=1)
        
        with pytest.raises(ValueError, match="Either image_data or image_path must be provided"):
            ValidationOCRRequest(area=area)


class TestValidationOCRResponse:
    """Test OCR response data structure."""
    
    def test_response_creation(self):
        """Test creating OCR response."""
        response = ValidationOCRResponse(
            request_id="test-123",
            text="Hello World",
            confidence=0.95,
            engine_used=OCREngine.TESSERACT,
            processing_time=1.5,
            quality_score=0.87,
            word_confidences=[("Hello", 0.98), ("World", 0.92)],
            preprocessing_applied=True,
            error_message=None,
            bounding_boxes=[
                {"text": "Hello", "x": 10, "y": 20, "width": 50, "height": 15},
                {"text": "World", "x": 65, "y": 20, "width": 45, "height": 15}
            ]
        )
        
        assert response.request_id == "test-123"
        assert response.text == "Hello World"
        assert response.confidence == 0.95
        assert response.engine_used == OCREngine.TESSERACT
        assert response.processing_time == 1.5
        assert response.quality_score == 0.87
        assert len(response.word_confidences) == 2
        assert response.preprocessing_applied is True
        assert response.error_message is None
        assert len(response.bounding_boxes) == 2
    
    def test_response_to_dict(self):
        """Test converting response to dictionary."""
        response = ValidationOCRResponse(
            request_id="test-456",
            text="Test Text",
            confidence=0.85,
            engine_used=OCREngine.EASYOCR,
            processing_time=2.1,
            quality_score=0.78
        )
        
        result_dict = response.to_dict()
        
        assert result_dict["request_id"] == "test-456"
        assert result_dict["text"] == "Test Text"
        assert result_dict["confidence"] == 0.85
        assert result_dict["engine_used"] == "easyocr"
        assert result_dict["processing_time"] == 2.1
        assert result_dict["quality_score"] == 0.78


class TestOCRWorkerThread:
    """Test OCR worker thread functionality."""
    
    @pytest.fixture
    def worker(self):
        """Create OCR worker thread for testing."""
        return OCRWorkerThread()
    
    def test_worker_initialization(self, worker):
        """Test worker thread initialization."""
        assert worker._requests_queue == []
        assert worker._is_running is False
        assert worker._current_request is None
        assert worker._cancelled_requests == set()
    
    def test_add_request(self, worker):
        """Test adding OCR request to queue."""
        area = DrawingArea(x=0, y=0, width=100, height=50, page_number=1)
        request = ValidationOCRRequest(
            area=area,
            image_data=b"test_data"
        )
        
        worker.add_request(request)
        
        assert len(worker._requests_queue) == 1
        assert worker._requests_queue[0] == request
    
    def test_cancel_request(self, worker):
        """Test cancelling OCR request."""
        area = DrawingArea(x=0, y=0, width=100, height=50, page_number=1)
        request1 = ValidationOCRRequest(area=area, image_data=b"data1")
        request2 = ValidationOCRRequest(area=area, image_data=b"data2")
        
        worker.add_request(request1)
        worker.add_request(request2)
        
        worker.cancel_request(request1.request_id)
        
        assert request1.request_id in worker._cancelled_requests
        assert len(worker._requests_queue) == 1
        assert worker._requests_queue[0] == request2
    
    def test_clear_queue(self, worker):
        """Test clearing request queue."""
        area = DrawingArea(x=0, y=0, width=100, height=50, page_number=1)
        request1 = ValidationOCRRequest(area=area, image_data=b"data1")
        request2 = ValidationOCRRequest(area=area, image_data=b"data2")
        
        worker.add_request(request1)
        worker.add_request(request2)
        worker.cancel_request(request1.request_id)
        
        worker.clear_queue()
        
        assert len(worker._requests_queue) == 0
        assert len(worker._cancelled_requests) == 0


class TestValidationOCRService:
    """Test main OCR service functionality."""
    
    @pytest.fixture
    def ocr_service(self):
        """Create OCR service for testing."""
        with patch.object(OCRWorkerThread, 'start'):
            service = ValidationOCRService()
        return service
    
    def test_service_initialization(self, ocr_service):
        """Test OCR service initialization."""
        assert ocr_service._active_requests == {}
        assert ocr_service._completed_requests == {}
        assert ocr_service._statistics['total_requests'] == 0
        assert ocr_service._statistics['successful_requests'] == 0
        assert ocr_service._statistics['failed_requests'] == 0
    
    def test_submit_request(self, ocr_service):
        """Test submitting OCR request."""
        area = DrawingArea(x=0, y=0, width=100, height=50, page_number=1)
        request = ValidationOCRRequest(
            area=area,
            image_data=b"test_data"
        )
        
        with patch.object(ocr_service._worker, 'add_request') as mock_add:
            request_id = ocr_service.submit_request(request)
        
        assert request_id == request.request_id
        assert request.request_id in ocr_service._active_requests
        assert ocr_service._statistics['total_requests'] == 1
        mock_add.assert_called_once_with(request)
    
    def test_cancel_request(self, ocr_service):
        """Test cancelling OCR request."""
        area = DrawingArea(x=0, y=0, width=100, height=50, page_number=1)
        request = ValidationOCRRequest(
            area=area,
            image_data=b"test_data"
        )
        
        # Submit request first
        with patch.object(ocr_service._worker, 'add_request'):
            request_id = ocr_service.submit_request(request)
        
        # Cancel request
        with patch.object(ocr_service._worker, 'cancel_request') as mock_cancel:
            result = ocr_service.cancel_request(request_id)
        
        assert result is True
        assert request_id not in ocr_service._active_requests
        mock_cancel.assert_called_once_with(request_id)
    
    def test_get_statistics(self, ocr_service):
        """Test getting service statistics."""
        stats = ocr_service.get_statistics()
        
        expected_keys = [
            'total_requests', 'successful_requests', 'failed_requests',
            'total_processing_time', 'average_confidence'
        ]
        
        for key in expected_keys:
            assert key in stats
        
        # Should be a copy, not reference
        stats['total_requests'] = 999
        assert ocr_service._statistics['total_requests'] != 999


class TestOCRValidationHelper:
    """Test OCR validation helper functionality."""
    
    def test_assess_text_quality_good_text(self):
        """Test quality assessment of good text."""
        text = "This is a well-formatted text with numbers 123 and punctuation!"
        
        assessment = OCRValidationHelper.assess_text_quality(text)
        
        assert assessment['length'] == len(text)
        assert assessment['word_count'] == 10  # Corrected count
        assert assessment['has_numbers'] is True
        assert assessment['has_uppercase'] is True
        assert assessment['has_lowercase'] is True
        assert assessment['has_punctuation'] is True
        assert assessment['quality_score'] > 0.7
    
    def test_assess_text_quality_empty_text(self):
        """Test quality assessment of empty text."""
        text = ""
        
        assessment = OCRValidationHelper.assess_text_quality(text)
        
        assert assessment['length'] == 0
        assert assessment['word_count'] == 0
        assert assessment['quality_score'] == 0.0
    
    def test_validate_confidence_threshold_pass(self):
        """Test confidence threshold validation (passing)."""
        response = ValidationOCRResponse(
            request_id="test",
            text="Good text",
            confidence=0.8,
            engine_used=OCREngine.TESSERACT,
            processing_time=1.0,
            quality_score=0.75
        )
        
        result = OCRValidationHelper.validate_confidence_threshold(response, 0.7)
        assert result is True
    
    def test_validate_confidence_threshold_fail_confidence(self):
        """Test confidence threshold validation (failing confidence)."""
        response = ValidationOCRResponse(
            request_id="test",
            text="Poor text",
            confidence=0.4,
            engine_used=OCREngine.TESSERACT,
            processing_time=1.0,
            quality_score=0.75
        )
        
        result = OCRValidationHelper.validate_confidence_threshold(response, 0.5)
        assert result is False
    
    def test_suggest_improvements_low_confidence(self):
        """Test improvement suggestions for low confidence."""
        response = ValidationOCRResponse(
            request_id="test",
            text="Some text",
            confidence=0.6,
            engine_used=OCREngine.TESSERACT,
            processing_time=1.0,
            quality_score=0.4
        )
        
        suggestions = OCRValidationHelper.suggest_improvements(response)
        
        assert "Consider preprocessing the image" in suggestions[0]
        assert "Try a different OCR engine" in suggestions[1]
    
    def test_suggest_improvements_no_issues(self):
        """Test improvement suggestions when no issues detected."""
        response = ValidationOCRResponse(
            request_id="test",
            text="This is a perfect text with good length and quality",
            confidence=0.95,
            engine_used=OCREngine.TESSERACT,
            processing_time=2.0,
            quality_score=0.9
        )
        
        suggestions = OCRValidationHelper.suggest_improvements(response)
        
        assert len(suggestions) == 0


@pytest.mark.integration
class TestOCRServiceIntegration:
    """Integration tests for the complete OCR service."""
    
    def test_full_workflow_simulation(self):
        """Test complete OCR workflow simulation."""
        # Create service
        with patch.object(OCRWorkerThread, 'start'):
            service = ValidationOCRService()
        
        # Create request
        area = DrawingArea(x=10, y=20, width=100, height=50, page_number=1)
        request = ValidationOCRRequest(
            area=area,
            image_data=b"fake_image_data",
            engine=OCREngine.AUTO,
            preprocessing=True
        )
        
        # Submit request
        request_id = service.submit_request(request)
        
        # Simulate successful processing
        response = ValidationOCRResponse(
            request_id=request_id,
            text="Integration Test Text",
            confidence=0.92,
            engine_used=OCREngine.TESSERACT,
            processing_time=1.8,
            quality_score=0.87,
            word_confidences=[("Integration", 0.95), ("Test", 0.89), ("Text", 0.92)],
            preprocessing_applied=True
        )
        
        # Trigger result processing
        service._on_result_ready(response)
        
        # Verify result storage
        stored_result = service.get_result(request_id)
        assert stored_result == response
        
        # Verify statistics
        stats = service.get_statistics()
        assert stats['successful_requests'] == 1
        assert stats['average_confidence'] == 0.92
        
        # Cleanup
        service.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])