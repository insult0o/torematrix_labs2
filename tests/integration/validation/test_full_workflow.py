"""
Full workflow integration tests for validation tools.

Tests complete end-to-end validation workflows including:
- Document loading and processing
- Element detection and validation
- OCR integration and quality assessment
- UI component interaction
- Error handling and recovery
"""

import pytest
import asyncio
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any

from PyQt6.QtCore import QTimer, QEventLoop
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPixmap, QPainter, QColor
from PyQt6.QtTest import QTest

from src.torematrix.ui.tools.validation.integration import (
    ValidationToolsIntegration,
    ValidationMode,
    IntegrationStatus,
    create_validation_integration
)
from src.torematrix.ui.tools.validation.drawing_state import DrawingStateManager
from src.torematrix.ui.tools.validation.area_select import AreaSelectTool
from src.torematrix.ui.tools.validation.ocr_service import ValidationOCRService
from src.torematrix.ui.tools.validation.wizard import ValidationWizard
from src.torematrix.ui.tools.validation.toolbar import ValidationToolbar
from src.torematrix.ui.tools.validation.ocr_dialog import OCRDialog


@pytest.fixture(scope="module")
def app():
    """Create QApplication for integration tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def temp_document():
    """Create temporary test document."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        document_path = Path(f.name)
    yield document_path
    # Cleanup
    if document_path.exists():
        document_path.unlink()


@pytest.fixture
def test_images():
    """Create test page images."""
    images = []
    for i in range(3):
        pixmap = QPixmap(800, 1000)
        pixmap.fill(QColor(255, 255, 255))
        
        # Draw some test content
        painter = QPainter(pixmap)
        painter.setPen(QColor(0, 0, 0))
        painter.drawText(50, 50 + i * 30, f"Test content page {i + 1}")
        painter.drawRect(100, 100 + i * 50, 200, 30)  # Text box
        painter.drawRect(100, 200 + i * 50, 300, 100)  # Larger element
        painter.end()
        
        images.append(pixmap)
    
    return images


@pytest.fixture
def full_integration(app):
    """Create full validation integration with real components."""
    # Create real component instances for integration testing
    drawing_manager = DrawingStateManager()
    area_tool = AreaSelectTool()
    ocr_service = ValidationOCRService()
    wizard = ValidationWizard()
    toolbar = ValidationToolbar()
    ocr_dialog = OCRDialog()
    
    integration = ValidationToolsIntegration()
    success = integration.initialize_components(
        drawing_manager, area_tool, ocr_service,
        wizard, toolbar, ocr_dialog
    )
    
    assert success, "Failed to initialize integration components"
    return integration


class TestFullValidationWorkflow:
    """Test complete validation workflows."""
    
    def test_manual_validation_workflow(self, full_integration, temp_document, test_images):
        """Test complete manual validation workflow."""
        # Start validation session
        session_id = full_integration.start_validation_session(
            document_path=temp_document,
            mode=ValidationMode.MANUAL_SELECTION,
            pages_total=len(test_images)
        )
        
        assert session_id in full_integration.sessions
        session = full_integration.sessions[session_id]
        assert session.mode == ValidationMode.MANUAL_SELECTION
        
        # Process each page
        for page_num, image in enumerate(test_images, 1):
            success = full_integration.process_page(
                session_id=session_id,
                page_number=page_num,
                page_image=image,
                auto_detect=False  # Manual mode
            )
            assert success
        
        # Manually validate elements
        elements = [
            {'type': 'text', 'content': 'Header text', 'bbox': [50, 50, 200, 80]},
            {'type': 'paragraph', 'content': 'Body text', 'bbox': [100, 100, 300, 200]},
            {'type': 'table', 'content': 'Table data', 'bbox': [100, 300, 400, 500]}
        ]
        
        for element in elements:
            success = full_integration.validate_element(
                session_id=session_id,
                element_data=element,
                use_ocr=False
            )
            assert success
        
        # Complete session
        success = full_integration.complete_session(session_id)
        assert success
        
        # Verify final state
        assert session.status == IntegrationStatus.COMPLETED
        assert session.pages_completed == len(test_images)
        assert session.elements_validated == len(elements)
        assert session.end_time is not None
    
    def test_ocr_assisted_workflow(self, full_integration, temp_document, test_images):
        """Test OCR-assisted validation workflow."""
        # Start OCR-assisted session
        session_id = full_integration.start_validation_session(
            document_path=temp_document,
            mode=ValidationMode.OCR_ASSISTED,
            pages_total=len(test_images)
        )
        
        # Process pages with auto-detection
        for page_num, image in enumerate(test_images, 1):
            success = full_integration.process_page(
                session_id=session_id,
                page_number=page_num,
                page_image=image,
                auto_detect=True  # Enable auto-detection
            )
            assert success
        
        # Simulate OCR results by validating elements with OCR
        elements = [
            {'type': 'text', 'bbox': [50, 50, 200, 80]},
            {'type': 'paragraph', 'bbox': [100, 100, 300, 200]}
        ]
        
        for element in elements:
            success = full_integration.validate_element(
                session_id=session_id,
                element_data=element,
                use_ocr=True
            )
            assert success
        
        # Complete session
        success = full_integration.complete_session(session_id)
        assert success
        
        session = full_integration.sessions[session_id]
        assert session.status == IntegrationStatus.COMPLETED
        assert session.elements_validated == len(elements)
    
    def test_hybrid_workflow(self, full_integration, temp_document, test_images):
        """Test hybrid validation workflow combining manual and OCR."""
        # Start hybrid session
        session_id = full_integration.start_validation_session(
            document_path=temp_document,
            mode=ValidationMode.HYBRID_WORKFLOW,
            pages_total=len(test_images)
        )
        
        # Process pages
        for page_num, image in enumerate(test_images, 1):
            success = full_integration.process_page(
                session_id=session_id,
                page_number=page_num,
                page_image=image,
                auto_detect=True
            )
            assert success
        
        # Mix of manual and OCR validation
        manual_elements = [
            {'type': 'text', 'content': 'Manual text', 'bbox': [50, 50, 200, 80]}
        ]
        
        ocr_elements = [
            {'type': 'paragraph', 'bbox': [100, 100, 300, 200]},
            {'type': 'title', 'bbox': [100, 300, 400, 350]}
        ]
        
        # Manual validation
        for element in manual_elements:
            success = full_integration.validate_element(
                session_id=session_id,
                element_data=element,
                use_ocr=False
            )
            assert success
        
        # OCR validation
        for element in ocr_elements:
            success = full_integration.validate_element(
                session_id=session_id,
                element_data=element,
                use_ocr=True
            )
            assert success
        
        # Complete session
        success = full_integration.complete_session(session_id)
        assert success
        
        session = full_integration.sessions[session_id]
        assert session.status == IntegrationStatus.COMPLETED
        assert session.elements_validated == len(manual_elements) + len(ocr_elements)
    
    def test_batch_processing_workflow(self, full_integration, temp_document, test_images):
        """Test batch processing workflow."""
        # Configure for batch processing
        full_integration.configure_integration({
            'batch_size': 2,
            'max_concurrent_ocr': 2
        })
        
        # Start batch session
        session_id = full_integration.start_validation_session(
            document_path=temp_document,
            mode=ValidationMode.BATCH_PROCESSING,
            pages_total=len(test_images)
        )
        
        # Batch process all pages
        for page_num, image in enumerate(test_images, 1):
            success = full_integration.process_page(
                session_id=session_id,
                page_number=page_num,
                page_image=image,
                auto_detect=True
            )
            assert success
        
        # Batch validate elements
        elements = []
        for i in range(6):  # Multiple elements for batch processing
            elements.append({
                'type': 'text',
                'bbox': [50 + i * 10, 50 + i * 20, 200, 80],
                'batch_id': i // 2  # Group into batches
            })
        
        for element in elements:
            success = full_integration.validate_element(
                session_id=session_id,
                element_data=element,
                use_ocr=True
            )
            assert success
        
        # Complete session
        success = full_integration.complete_session(session_id)
        assert success
        
        session = full_integration.sessions[session_id]
        assert session.status == IntegrationStatus.COMPLETED
        assert session.elements_validated == len(elements)


class TestWorkflowErrorHandling:
    """Test error handling in complete workflows."""
    
    def test_component_failure_recovery(self, full_integration, temp_document, test_images):
        """Test recovery from component failures."""
        session_id = full_integration.start_validation_session(temp_document)
        
        # Simulate component failures
        with patch.object(full_integration.drawing_manager, 'set_page_image', side_effect=Exception("Drawing error")):
            # Should still process despite drawing manager error
            success = full_integration.process_page(
                session_id=session_id,
                page_number=1,
                page_image=test_images[0]
            )
            # Processing continues despite component error
            assert success
        
        # Verify error was recorded
        session = full_integration.sessions[session_id]
        assert len(session.errors) > 0
    
    def test_ocr_service_failure_recovery(self, full_integration, temp_document, test_images):
        """Test recovery from OCR service failures."""
        session_id = full_integration.start_validation_session(temp_document)
        
        # Process page normally
        full_integration.process_page(session_id, 1, test_images[0])
        
        # Simulate OCR failure
        with patch.object(full_integration, '_perform_element_ocr', side_effect=Exception("OCR error")):
            element = {'type': 'text', 'bbox': [100, 100, 200, 150]}
            success = full_integration.validate_element(
                session_id=session_id,
                element_data=element,
                use_ocr=True
            )
            # Should fail gracefully
            assert not success
        
        # Verify error handling
        session = full_integration.sessions[session_id]
        assert len(session.errors) > 0
    
    def test_session_timeout_handling(self, full_integration, temp_document):
        """Test session timeout handling."""
        # Configure short timeout for testing
        full_integration.configure_integration({'session_timeout': 1})
        
        session_id = full_integration.start_validation_session(temp_document)
        session = full_integration.sessions[session_id]
        
        # Simulate long processing time
        import time
        time.sleep(2)  # Exceed timeout
        
        # Complete session should still work
        success = full_integration.complete_session(session_id)
        assert success


class TestWorkflowStatistics:
    """Test statistics collection during workflows."""
    
    def test_statistics_accumulation(self, full_integration, temp_document, test_images):
        """Test that statistics accumulate correctly across workflows."""
        initial_stats = full_integration.get_session_statistics()
        
        # Run multiple sessions
        session_ids = []
        for i in range(3):
            session_id = full_integration.start_validation_session(
                temp_document,
                pages_total=2
            )
            session_ids.append(session_id)
            
            # Process pages
            for page_num in range(1, 3):
                full_integration.process_page(session_id, page_num, test_images[0])
            
            # Validate elements
            for j in range(2):
                full_integration.validate_element(
                    session_id,
                    {'type': 'text', 'content': f'Element {j}'}
                )
            
            full_integration.complete_session(session_id)
        
        # Check accumulated statistics
        final_stats = full_integration.get_session_statistics()
        
        assert final_stats['total_sessions'] == initial_stats['total_sessions'] + 3
        assert final_stats['total_elements'] == initial_stats['total_elements'] + 6
        assert final_stats['success_rate'] <= 100.0
    
    def test_performance_metrics_collection(self, full_integration, temp_document, test_images):
        """Test performance metrics collection during workflow."""
        session_id = full_integration.start_validation_session(temp_document)
        
        # Enable performance monitoring
        full_integration.configure_integration({'performance_monitoring': True})
        
        # Process pages and elements
        for i, image in enumerate(test_images):
            full_integration.process_page(session_id, i + 1, image)
            full_integration.validate_element(
                session_id,
                {'type': 'text', 'content': f'Content {i}'}
            )
        
        full_integration.complete_session(session_id)
        
        # Check performance metrics
        stats = full_integration.get_session_statistics()
        assert 'performance_metrics' in stats
        performance_metrics = stats['performance_metrics']
        
        # Should have collected some metrics
        assert len(performance_metrics) > 0


class TestWorkflowIntegration:
    """Test integration between different workflow components."""
    
    def test_wizard_integration(self, full_integration, temp_document, test_images):
        """Test integration with validation wizard."""
        session_id = full_integration.start_validation_session(temp_document)
        
        # Wizard should be notified of session start
        assert full_integration.wizard.start_validation_session.called
        
        # Process workflow steps
        for i, image in enumerate(test_images):
            full_integration.process_page(session_id, i + 1, image)
        
        # Complete session
        full_integration.complete_session(session_id)
        
        # Wizard should be notified of completion
        assert full_integration.wizard.complete_session.called
    
    def test_toolbar_integration(self, full_integration, temp_document, test_images):
        """Test integration with validation toolbar."""
        session_id = full_integration.start_validation_session(temp_document)
        
        # Process pages
        for i, image in enumerate(test_images):
            full_integration.process_page(session_id, i + 1, image)
            # Toolbar should be updated with current page
            assert full_integration.toolbar.set_current_page.called
        
        full_integration.complete_session(session_id)
    
    def test_drawing_manager_integration(self, full_integration, temp_document, test_images):
        """Test integration with drawing state manager."""
        session_id = full_integration.start_validation_session(temp_document)
        
        # Drawing manager should be notified of session
        assert full_integration.drawing_manager.start_session.called
        
        # Process pages
        for i, image in enumerate(test_images):
            full_integration.process_page(session_id, i + 1, image)
            # Drawing manager should receive page images
            assert full_integration.drawing_manager.set_page_image.called
        
        full_integration.complete_session(session_id)
        
        # Drawing manager should be notified of session end
        assert full_integration.drawing_manager.end_session.called


class TestConcurrentWorkflows:
    """Test handling of concurrent validation workflows."""
    
    def test_multiple_concurrent_sessions(self, full_integration, temp_document, test_images):
        """Test running multiple validation sessions concurrently."""
        session_ids = []
        
        # Start multiple sessions
        for i in range(3):
            session_id = full_integration.start_validation_session(
                temp_document,
                mode=ValidationMode.MANUAL_SELECTION,
                pages_total=2
            )
            session_ids.append(session_id)
        
        # Process all sessions concurrently
        for session_id in session_ids:
            for page_num, image in enumerate(test_images[:2], 1):
                success = full_integration.process_page(session_id, page_num, image)
                assert success
            
            # Validate elements for each session
            for i in range(2):
                success = full_integration.validate_element(
                    session_id,
                    {'type': 'text', 'content': f'Element {i}'}
                )
                assert success
        
        # Complete all sessions
        for session_id in session_ids:
            success = full_integration.complete_session(session_id)
            assert success
        
        # Verify all sessions completed successfully
        for session_id in session_ids:
            session = full_integration.sessions[session_id]
            assert session.status == IntegrationStatus.COMPLETED
    
    def test_session_isolation(self, full_integration, temp_document, test_images):
        """Test that sessions are properly isolated from each other."""
        # Start two sessions
        session1 = full_integration.start_validation_session(temp_document, pages_total=1)
        session2 = full_integration.start_validation_session(temp_document, pages_total=1)
        
        # Process different content for each session
        full_integration.process_page(session1, 1, test_images[0])
        full_integration.validate_element(session1, {'type': 'text', 'content': 'Session 1 content'})
        
        full_integration.process_page(session2, 1, test_images[1])
        full_integration.validate_element(session2, {'type': 'paragraph', 'content': 'Session 2 content'})
        
        # Complete sessions
        full_integration.complete_session(session1)
        full_integration.complete_session(session2)
        
        # Verify sessions have independent data
        stats1 = full_integration.get_session_statistics(session1)
        stats2 = full_integration.get_session_statistics(session2)
        
        assert stats1['session_id'] != stats2['session_id']
        assert stats1['elements_validated'] == 1
        assert stats2['elements_validated'] == 1


if __name__ == '__main__':
    pytest.main([__file__])