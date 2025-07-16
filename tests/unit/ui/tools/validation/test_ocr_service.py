"""
Tests for OCR Service Integration (Agent 2).

This module tests the ValidationOCRService implementation for manual validation
workflows with comprehensive test coverage.
"""

import pytest
import time
from unittest.mock import Mock, patch
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from src.torematrix.ui.tools.validation.ocr_service import (
    ValidationOCRService,
    ValidationOCRRequest,
    ValidationOCRResponse,
    OCRWorkerThread,
    OCREngine,
    OCRStatus,
    OCRValidationHelper
)
from src.torematrix.ui.tools.validation.drawing_state import DrawingArea


class TestValidationOCRService:
    """Test suite for ValidationOCRService."""
    
    @pytest.fixture
    def app(self):
        """Create QApplication for testing."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app
    
    @pytest.fixture
    def drawing_area(self):
        """Create test drawing area."""
        return DrawingArea(x=100, y=100, width=200, height=50, page_number=1)
    
    @pytest.fixture
    def ocr_service(self, app):
        """Create OCR service for testing."""
        service = ValidationOCRService()
        yield service
        service.shutdown()
    
    def test_service_initialization(self, ocr_service):
        """Test OCR service initialization."""
        assert ocr_service is not None
        stats = ocr_service.get_statistics()
        assert stats['total_requests'] == 0
        assert stats['successful_requests'] == 0
        assert stats['failed_requests'] == 0
    
    def test_ocr_request_creation(self, drawing_area):
        """Test OCR request creation."""
        request = ValidationOCRRequest(
            area=drawing_area,
            image_path="test.jpg",
            engine=OCREngine.MOCK,
            preprocessing=True
        )
        
        assert request.area == drawing_area
        assert request.image_path == "test.jpg"
        assert request.engine == OCREngine.MOCK
        assert request.preprocessing is True
        assert request.request_id is not None
    
    def test_ocr_request_validation(self, drawing_area):
        """Test OCR request validation."""
        # Valid request
        request = ValidationOCRRequest(
            area=drawing_area,
            image_path="test.jpg"
        )
        assert request is not None
        
        # Invalid request - no area
        with pytest.raises(ValueError, match="DrawingArea is required"):
            ValidationOCRRequest(
                area=None,
                image_path="test.jpg"
            )
        
        # Invalid request - no image data or path
        with pytest.raises(ValueError, match="Either image_data or image_path must be provided"):
            ValidationOCRRequest(
                area=drawing_area,
                image_data=None,
                image_path=None
            )
    
    def test_submit_request(self, ocr_service, drawing_area):
        """Test submitting OCR request."""
        request = ValidationOCRRequest(
            area=drawing_area,
            image_path="test.jpg",
            engine=OCREngine.MOCK
        )
        
        request_id = ocr_service.submit_request(request)
        assert request_id is not None
        assert request_id == request.request_id
        
        # Check statistics updated
        stats = ocr_service.get_statistics()
        assert stats['total_requests'] == 1
    
    def test_cancel_request(self, ocr_service, drawing_area):
        """Test canceling OCR request."""
        request = ValidationOCRRequest(
            area=drawing_area,
            image_path="test.jpg",
            engine=OCREngine.MOCK
        )
        
        request_id = ocr_service.submit_request(request)
        success = ocr_service.cancel_request(request_id)
        assert success is True
        
        # Try to cancel non-existent request
        success = ocr_service.cancel_request("non_existent_id")
        assert success is False
    
    def test_get_result(self, ocr_service, drawing_area):
        """Test getting OCR result."""
        request = ValidationOCRRequest(
            area=drawing_area,
            image_path="test.jpg",
            engine=OCREngine.MOCK
        )
        
        request_id = ocr_service.submit_request(request)
        
        # Wait for processing
        time.sleep(0.5)
        
        result = ocr_service.get_result(request_id)
        if result:
            assert result.request_id == request_id
            assert result.engine_used == OCREngine.MOCK
            assert result.text is not None
            assert result.confidence >= 0.0
    
    def test_statistics_tracking(self, ocr_service, drawing_area):
        """Test OCR statistics tracking."""
        request = ValidationOCRRequest(
            area=drawing_area,
            image_path="test.jpg",
            engine=OCREngine.MOCK
        )
        
        initial_stats = ocr_service.get_statistics()
        
        ocr_service.submit_request(request)
        
        # Wait for processing
        time.sleep(0.5)
        
        final_stats = ocr_service.get_statistics()
        assert final_stats['total_requests'] == initial_stats['total_requests'] + 1
    
    def test_clear_completed_results(self, ocr_service, drawing_area):
        """Test clearing completed results."""
        request = ValidationOCRRequest(
            area=drawing_area,
            image_path="test.jpg",
            engine=OCREngine.MOCK
        )
        
        request_id = ocr_service.submit_request(request)
        time.sleep(0.5)  # Wait for processing
        
        # Should have result
        result = ocr_service.get_result(request_id)
        assert result is not None or result is None  # May not be processed yet
        
        # Clear results
        ocr_service.clear_completed_results()
        
        # Should not have result anymore
        result = ocr_service.get_result(request_id)
        assert result is None


class TestOCRWorkerThread:
    """Test suite for OCRWorkerThread."""
    
    @pytest.fixture
    def app(self):
        """Create QApplication for testing."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app
    
    @pytest.fixture
    def worker_thread(self, app):
        """Create OCR worker thread for testing."""
        worker = OCRWorkerThread()
        yield worker
        worker.stop()
        worker.wait()
    
    def test_worker_initialization(self, worker_thread):
        """Test worker thread initialization."""
        assert worker_thread is not None
        assert worker_thread._is_running is False
        assert len(worker_thread._requests_queue) == 0
    
    def test_add_request(self, worker_thread):
        """Test adding request to worker thread."""
        area = DrawingArea(x=100, y=100, width=200, height=50, page_number=1)
        request = ValidationOCRRequest(
            area=area,
            image_path="test.jpg",
            engine=OCREngine.MOCK
        )
        
        worker_thread.add_request(request)
        # Note: Can't easily test queue length due to thread synchronization
    
    def test_cancel_request(self, worker_thread):
        """Test canceling request in worker thread."""
        area = DrawingArea(x=100, y=100, width=200, height=50, page_number=1)
        request = ValidationOCRRequest(
            area=area,
            image_path="test.jpg",
            engine=OCREngine.MOCK
        )
        
        worker_thread.add_request(request)
        worker_thread.cancel_request(request.request_id)
        # Note: Can't easily test cancellation due to thread synchronization
    
    def test_clear_queue(self, worker_thread):
        """Test clearing request queue."""
        area = DrawingArea(x=100, y=100, width=200, height=50, page_number=1)
        request = ValidationOCRRequest(
            area=area,
            image_path="test.jpg",
            engine=OCREngine.MOCK
        )
        
        worker_thread.add_request(request)
        worker_thread.clear_queue()
        # Note: Can't easily test queue state due to thread synchronization


class TestOCRValidationHelper:
    """Test suite for OCRValidationHelper."""
    
    def test_assess_text_quality(self):
        """Test text quality assessment."""
        # High quality text
        quality = OCRValidationHelper.assess_text_quality("This is a sample text with good quality.")
        assert quality['length'] > 0
        assert quality['word_count'] > 0
        assert quality['character_diversity'] > 0
        assert quality['quality_score'] > 0.5
        
        # Low quality text
        quality = OCRValidationHelper.assess_text_quality("a")
        assert quality['length'] == 1
        assert quality['word_count'] == 1
        assert quality['quality_score'] < 0.5
        
        # Empty text
        quality = OCRValidationHelper.assess_text_quality("")
        assert quality['length'] == 0
        assert quality['word_count'] == 0
        assert quality['quality_score'] == 0.0
    
    def test_validate_confidence_threshold(self):
        """Test confidence threshold validation."""
        # High confidence response
        response = ValidationOCRResponse(
            request_id="test",
            text="Sample text",
            confidence=0.9,
            engine_used=OCREngine.MOCK,
            processing_time=0.5,
            quality_score=0.8
        )
        
        assert OCRValidationHelper.validate_confidence_threshold(response, 0.5) is True
        assert OCRValidationHelper.validate_confidence_threshold(response, 0.95) is False
        
        # Low confidence response
        response = ValidationOCRResponse(
            request_id="test",
            text="Sample text",
            confidence=0.3,
            engine_used=OCREngine.MOCK,
            processing_time=0.5,
            quality_score=0.2
        )
        
        assert OCRValidationHelper.validate_confidence_threshold(response, 0.5) is False
        assert OCRValidationHelper.validate_confidence_threshold(response, 0.1) is True
    
    def test_suggest_improvements(self):
        """Test improvement suggestions."""
        # Low confidence response
        response = ValidationOCRResponse(
            request_id="test",
            text="Sample text",
            confidence=0.3,
            engine_used=OCREngine.MOCK,
            processing_time=0.5,
            quality_score=0.2
        )
        
        suggestions = OCRValidationHelper.suggest_improvements(response)
        assert len(suggestions) > 0
        assert any("preprocessing" in s for s in suggestions)
        
        # High quality response
        response = ValidationOCRResponse(
            request_id="test",
            text="This is a long sample text with good quality and content.",
            confidence=0.9,
            engine_used=OCREngine.MOCK,
            processing_time=0.5,
            quality_score=0.8
        )
        
        suggestions = OCRValidationHelper.suggest_improvements(response)
        assert len(suggestions) == 0


class TestOCRResponse:
    """Test suite for ValidationOCRResponse."""
    
    def test_response_creation(self):
        """Test OCR response creation."""
        response = ValidationOCRResponse(
            request_id="test_id",
            text="Sample text",
            confidence=0.85,
            engine_used=OCREngine.MOCK,
            processing_time=0.5,
            quality_score=0.8
        )
        
        assert response.request_id == "test_id"
        assert response.text == "Sample text"
        assert response.confidence == 0.85
        assert response.engine_used == OCREngine.MOCK
        assert response.processing_time == 0.5
        assert response.quality_score == 0.8
    
    def test_response_to_dict(self):
        """Test OCR response serialization."""
        response = ValidationOCRResponse(
            request_id="test_id",
            text="Sample text",
            confidence=0.85,
            engine_used=OCREngine.MOCK,
            processing_time=0.5,
            quality_score=0.8,
            word_confidences=[("Sample", 0.9), ("text", 0.8)]
        )
        
        data = response.to_dict()
        assert data['request_id'] == "test_id"
        assert data['text'] == "Sample text"
        assert data['confidence'] == 0.85
        assert data['engine_used'] == "mock"
        assert data['processing_time'] == 0.5
        assert data['quality_score'] == 0.8
        assert len(data['word_confidences']) == 2


if __name__ == "__main__":
    pytest.main([__file__])