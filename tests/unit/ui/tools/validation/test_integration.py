"""
Comprehensive tests for ValidationToolsIntegration.

Tests the unified integration layer that coordinates all validation components
including drawing state management, OCR services, UI components, and workflow management.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, MagicMock, patch, call
from pathlib import Path
from typing import Dict, Any

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtGui import QPixmap
from PyQt6.QtTest import QTest

from src.torematrix.ui.tools.validation.integration import (
    ValidationToolsIntegration,
    ValidationMode,
    IntegrationStatus,
    ValidationSession,
    ValidationStatistics,
    create_validation_integration,
    get_integration_statistics
)
from src.torematrix.ui.tools.validation.drawing_state import DrawingStateManager, DrawingAction
from src.torematrix.ui.tools.validation.area_select import AreaSelectTool
from src.torematrix.ui.tools.validation.shapes import ElementShape, ShapeType
from src.torematrix.ui.tools.validation.ocr_service import ValidationOCRService, OCRRequest, OCRResponse
from src.torematrix.ui.tools.validation.wizard import ValidationWizard
from src.torematrix.ui.tools.validation.toolbar import ValidationToolbar
from src.torematrix.ui.tools.validation.ocr_dialog import OCRDialog


@pytest.fixture
def app():
    """Create QApplication for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture 
def mock_drawing_manager():
    """Create mock drawing state manager."""
    manager = Mock(spec=DrawingStateManager)
    manager.action_performed = Mock()
    manager.error_occurred = Mock()
    manager.is_active = Mock(return_value=True)
    manager.start_session = Mock()
    manager.end_session = Mock()
    manager.set_page_image = Mock()
    return manager


@pytest.fixture
def mock_area_tool():
    """Create mock area selection tool."""
    tool = Mock(spec=AreaSelectTool)
    tool.is_active = Mock(return_value=False)
    return tool


@pytest.fixture
def mock_ocr_service():
    """Create mock OCR service."""
    service = Mock(spec=ValidationOCRService)
    service.processing_completed = Mock()
    service.error_occurred = Mock()
    service.is_processing = Mock(return_value=False)
    service.submit_request = Mock()
    service.configure = Mock()
    return service


@pytest.fixture
def mock_wizard():
    """Create mock validation wizard."""
    wizard = Mock(spec=ValidationWizard)
    wizard.step_completed = Mock()
    wizard.validation_completed = Mock()
    wizard.start_validation_session = Mock()
    wizard.complete_session = Mock()
    wizard.configure = Mock()
    return wizard


@pytest.fixture
def mock_toolbar():
    """Create mock validation toolbar."""
    toolbar = Mock(spec=ValidationToolbar)
    toolbar.tool_selected = Mock()
    toolbar.action_triggered = Mock()
    toolbar.set_current_page = Mock()
    return toolbar


@pytest.fixture
def mock_ocr_dialog():
    """Create mock OCR dialog."""
    dialog = Mock(spec=OCRDialog)
    return dialog


@pytest.fixture
def validation_integration(app, mock_drawing_manager, mock_area_tool, mock_ocr_service,
                          mock_wizard, mock_toolbar, mock_ocr_dialog):
    """Create ValidationToolsIntegration with mocked components."""
    integration = ValidationToolsIntegration()
    
    # Initialize with mock components
    integration.initialize_components(
        mock_drawing_manager, mock_area_tool, mock_ocr_service,
        mock_wizard, mock_toolbar, mock_ocr_dialog
    )
    
    return integration


@pytest.fixture
def sample_document_path():
    """Sample document path for testing."""
    return Path("/test/documents/sample.pdf")


@pytest.fixture
def sample_page_image():
    """Sample page image for testing."""
    pixmap = QPixmap(800, 600)
    pixmap.fill()
    return pixmap


class TestValidationSession:
    """Test ValidationSession dataclass."""
    
    def test_session_creation(self, sample_document_path):
        """Test validation session creation."""
        session = ValidationSession(
            session_id="test-123",
            document_path=sample_document_path,
            mode=ValidationMode.MANUAL_SELECTION,
            pages_total=5
        )
        
        assert session.session_id == "test-123"
        assert session.document_path == sample_document_path
        assert session.mode == ValidationMode.MANUAL_SELECTION
        assert session.pages_total == 5
        assert session.pages_completed == 0
        assert session.elements_detected == 0
        assert session.elements_validated == 0
        assert session.status == IntegrationStatus.IDLE
        assert len(session.errors) == 0
    
    def test_session_duration(self, sample_document_path):
        """Test session duration calculation."""
        session = ValidationSession(
            session_id="test-123",
            document_path=sample_document_path,
            mode=ValidationMode.MANUAL_SELECTION,
            pages_total=1
        )
        
        # Test duration without end time
        assert session.duration > 0
        
        # Test duration with end time
        session.end_time = session.start_time + 10.0
        assert session.duration == 10.0
    
    def test_progress_percentage(self, sample_document_path):
        """Test progress percentage calculation."""
        session = ValidationSession(
            session_id="test-123",
            document_path=sample_document_path,
            mode=ValidationMode.MANUAL_SELECTION,
            pages_total=10
        )
        
        # No progress
        assert session.progress_percentage == 0.0
        
        # Partial progress
        session.pages_completed = 3
        assert session.progress_percentage == 30.0
        
        # Complete
        session.pages_completed = 10
        assert session.progress_percentage == 100.0
        
        # Zero pages total
        session.pages_total = 0
        assert session.progress_percentage == 0.0


class TestValidationStatistics:
    """Test ValidationStatistics dataclass."""
    
    def test_statistics_creation(self):
        """Test statistics creation with defaults."""
        stats = ValidationStatistics()
        
        assert stats.total_sessions == 0
        assert stats.total_elements == 0
        assert stats.total_ocr_requests == 0
        assert stats.average_session_duration == 0.0
        assert stats.success_rate == 100.0
        assert stats.error_count == 0
        assert isinstance(stats.performance_metrics, dict)


class TestValidationToolsIntegration:
    """Test ValidationToolsIntegration class."""
    
    def test_integration_creation(self, app):
        """Test integration creation."""
        integration = ValidationToolsIntegration()
        
        assert integration.status == IntegrationStatus.IDLE
        assert integration.current_session is None
        assert len(integration.sessions) == 0
        assert isinstance(integration.statistics, ValidationStatistics)
        assert isinstance(integration.config, dict)
        assert integration.drawing_manager is None
        assert integration.ocr_service is None
    
    def test_component_initialization(self, app, mock_drawing_manager, mock_area_tool,
                                    mock_ocr_service, mock_wizard, mock_toolbar, mock_ocr_dialog):
        """Test component initialization."""
        integration = ValidationToolsIntegration()
        
        result = integration.initialize_components(
            mock_drawing_manager, mock_area_tool, mock_ocr_service,
            mock_wizard, mock_toolbar, mock_ocr_dialog
        )
        
        assert result is True
        assert integration.status == IntegrationStatus.IDLE
        assert integration.drawing_manager == mock_drawing_manager
        assert integration.area_tool == mock_area_tool
        assert integration.ocr_service == mock_ocr_service
        assert integration.wizard == mock_wizard
        assert integration.toolbar == mock_toolbar
        assert integration.ocr_dialog == mock_ocr_dialog
    
    def test_component_initialization_failure(self, app):
        """Test component initialization failure handling."""
        integration = ValidationToolsIntegration()
        
        # Pass invalid components to trigger failure
        with patch.object(integration, '_connect_component_signals', side_effect=Exception("Test error")):
            result = integration.initialize_components(
                None, None, None, None, None, None
            )
        
        assert result is False
        assert integration.status == IntegrationStatus.ERROR
    
    def test_start_validation_session(self, validation_integration, sample_document_path):
        """Test starting validation session."""
        session_id = validation_integration.start_validation_session(
            document_path=sample_document_path,
            mode=ValidationMode.HYBRID_WORKFLOW,
            pages_total=5
        )
        
        assert isinstance(session_id, str)
        assert len(session_id) > 0
        assert session_id in validation_integration.sessions
        assert validation_integration.current_session is not None
        assert validation_integration.current_session.session_id == session_id
        assert validation_integration.statistics.total_sessions == 1
        
        # Verify components were notified
        validation_integration.drawing_manager.start_session.assert_called_once_with(session_id)
        validation_integration.wizard.start_validation_session.assert_called_once_with(session_id)
    
    def test_process_page(self, validation_integration, sample_document_path, sample_page_image):
        """Test page processing."""
        session_id = validation_integration.start_validation_session(
            sample_document_path, pages_total=3
        )
        
        result = validation_integration.process_page(
            session_id=session_id,
            page_number=1,
            page_image=sample_page_image,
            auto_detect=True
        )
        
        assert result is True
        
        session = validation_integration.sessions[session_id]
        assert session.pages_completed == 1
        assert session.status == IntegrationStatus.PROCESSING
        
        # Verify components were called
        validation_integration.drawing_manager.set_page_image.assert_called_once_with(sample_page_image, 1)
        validation_integration.toolbar.set_current_page.assert_called_once_with(1)
        validation_integration.ocr_service.submit_request.assert_called_once()
    
    def test_process_page_invalid_session(self, validation_integration, sample_page_image):
        """Test page processing with invalid session."""
        result = validation_integration.process_page(
            session_id="invalid-session",
            page_number=1,
            page_image=sample_page_image
        )
        
        assert result is False
    
    def test_validate_element(self, validation_integration, sample_document_path):
        """Test element validation."""
        session_id = validation_integration.start_validation_session(sample_document_path)
        
        element_data = {
            'type': 'text',
            'content': 'Sample text',
            'bbox': [100, 100, 200, 150]
        }
        
        result = validation_integration.validate_element(
            session_id=session_id,
            element_data=element_data,
            use_ocr=False
        )
        
        assert result is True
        
        session = validation_integration.sessions[session_id]
        assert session.elements_validated == 1
        assert validation_integration.statistics.total_elements == 1
    
    def test_validate_element_with_ocr(self, validation_integration, sample_document_path):
        """Test element validation with OCR."""
        session_id = validation_integration.start_validation_session(sample_document_path)
        
        element_data = {
            'type': 'text',
            'bbox': [100, 100, 200, 150]
        }
        
        # Mock OCR result
        with patch.object(validation_integration, '_perform_element_ocr', return_value={'content': 'OCR text'}):
            result = validation_integration.validate_element(
                session_id=session_id,
                element_data=element_data,
                use_ocr=True
            )
        
        assert result is True
        assert element_data['content'] == 'OCR text'
        
        session = validation_integration.sessions[session_id]
        assert session.ocr_requests == 1
    
    def test_complete_session(self, validation_integration, sample_document_path):
        """Test session completion."""
        session_id = validation_integration.start_validation_session(sample_document_path)
        
        result = validation_integration.complete_session(session_id)
        
        assert result is True
        
        session = validation_integration.sessions[session_id]
        assert session.status == IntegrationStatus.COMPLETED
        assert session.end_time is not None
        assert validation_integration.current_session is None
        
        # Verify components were notified
        validation_integration.drawing_manager.end_session.assert_called_once_with(session_id)
        validation_integration.wizard.complete_session.assert_called_once_with(session_id)
    
    def test_complete_invalid_session(self, validation_integration):
        """Test completing invalid session."""
        result = validation_integration.complete_session("invalid-session")
        assert result is False
    
    def test_get_session_statistics(self, validation_integration, sample_document_path):
        """Test getting session statistics."""
        session_id = validation_integration.start_validation_session(sample_document_path, pages_total=5)
        
        # Process some pages and elements
        validation_integration.process_page(session_id, 1, QPixmap(100, 100))
        validation_integration.validate_element(session_id, {'type': 'text'})
        
        stats = validation_integration.get_session_statistics(session_id)
        
        assert stats['session_id'] == session_id
        assert stats['pages_completed'] == 1
        assert stats['pages_total'] == 5
        assert stats['progress_percentage'] == 20.0
        assert stats['elements_validated'] == 1
        assert stats['errors'] == 0
    
    def test_get_overall_statistics(self, validation_integration, sample_document_path):
        """Test getting overall statistics."""
        # Create and complete a session
        session_id = validation_integration.start_validation_session(sample_document_path)
        validation_integration.validate_element(session_id, {'type': 'text'})
        validation_integration.complete_session(session_id)
        
        stats = validation_integration.get_session_statistics()
        
        assert stats['total_sessions'] == 1
        assert stats['total_elements'] == 1
        assert stats['success_rate'] == 100.0
        assert stats['error_count'] == 0
    
    def test_configure_integration(self, validation_integration):
        """Test integration configuration."""
        new_config = {
            'auto_ocr_threshold': 0.9,
            'batch_size': 20,
            'debug_mode': True
        }
        
        validation_integration.configure_integration(new_config)
        
        assert validation_integration.config['auto_ocr_threshold'] == 0.9
        assert validation_integration.config['batch_size'] == 20
        assert validation_integration.config['debug_mode'] is True
        
        # Verify components were configured
        validation_integration.ocr_service.configure.assert_called()
        validation_integration.wizard.configure.assert_called()
    
    def test_get_active_tools(self, validation_integration):
        """Test getting active tools."""
        # Mock some tools as active
        validation_integration.drawing_manager.is_active.return_value = True
        validation_integration.area_tool.is_active.return_value = False
        validation_integration.ocr_service.is_processing.return_value = True
        
        active_tools = validation_integration.get_active_tools()
        
        assert 'drawing_manager' in active_tools
        assert 'area_tool' not in active_tools
        assert 'ocr_service' in active_tools
    
    def test_error_handling(self, validation_integration, sample_document_path):
        """Test error handling throughout integration."""
        session_id = validation_integration.start_validation_session(sample_document_path)
        
        # Simulate component error
        error_msg = "Test component error"
        validation_integration._on_component_error(error_msg)
        
        session = validation_integration.sessions[session_id]
        assert error_msg in session.errors
    
    @patch('src.torematrix.ui.tools.validation.integration.psutil')
    def test_performance_monitoring(self, mock_psutil, validation_integration):
        """Test performance monitoring."""
        # Mock psutil for memory usage
        mock_process = Mock()
        mock_process.memory_info.return_value.rss = 1024 * 1024 * 100  # 100MB
        mock_psutil.Process.return_value = mock_process
        
        validation_integration._update_performance_metrics()
        
        metrics = validation_integration.statistics.performance_metrics
        assert 'memory_usage' in metrics
        assert metrics['memory_usage'] == 100.0  # 100MB
    
    def test_signal_emissions(self, validation_integration, sample_document_path):
        """Test that appropriate signals are emitted."""
        # Connect mock slots to signals
        session_started_slot = Mock()
        progress_updated_slot = Mock()
        element_validated_slot = Mock()
        session_completed_slot = Mock()
        
        validation_integration.session_started.connect(session_started_slot)
        validation_integration.progress_updated.connect(progress_updated_slot)
        validation_integration.element_validated.connect(element_validated_slot)
        validation_integration.session_completed.connect(session_completed_slot)
        
        # Perform operations that should emit signals
        session_id = validation_integration.start_validation_session(sample_document_path, pages_total=2)
        validation_integration.process_page(session_id, 1, QPixmap(100, 100))
        validation_integration.validate_element(session_id, {'type': 'text'})
        validation_integration.complete_session(session_id)
        
        # Verify signals were emitted
        session_started_slot.assert_called_once_with(session_id)
        progress_updated_slot.assert_called_once_with(session_id, 50.0)
        element_validated_slot.assert_called_once()
        session_completed_slot.assert_called_once_with(session_id, True)


class TestIntegrationConvenienceFunctions:
    """Test convenience functions for integration."""
    
    @patch('src.torematrix.ui.tools.validation.integration.DrawingStateManager')
    @patch('src.torematrix.ui.tools.validation.integration.AreaSelectTool')
    @patch('src.torematrix.ui.tools.validation.integration.ValidationOCRService')
    @patch('src.torematrix.ui.tools.validation.integration.ValidationWizard')
    @patch('src.torematrix.ui.tools.validation.integration.ValidationToolbar')
    @patch('src.torematrix.ui.tools.validation.integration.OCRDialog')
    def test_create_validation_integration(self, mock_ocr_dialog, mock_toolbar, mock_wizard,
                                         mock_ocr_service, mock_area_tool, mock_drawing_manager, app):
        """Test create_validation_integration convenience function."""
        # Mock the initialize_components to return True
        with patch.object(ValidationToolsIntegration, 'initialize_components', return_value=True):
            integration = create_validation_integration()
        
        assert isinstance(integration, ValidationToolsIntegration)
        
        # Verify all components were instantiated
        mock_drawing_manager.assert_called_once()
        mock_area_tool.assert_called_once()
        mock_ocr_service.assert_called_once()
        mock_wizard.assert_called_once()
        mock_toolbar.assert_called_once()
        mock_ocr_dialog.assert_called_once()
    
    @patch('src.torematrix.ui.tools.validation.integration.DrawingStateManager')
    def test_create_validation_integration_failure(self, mock_drawing_manager, app):
        """Test create_validation_integration failure handling."""
        # Mock initialization failure
        with patch.object(ValidationToolsIntegration, 'initialize_components', return_value=False):
            with pytest.raises(RuntimeError, match="Failed to initialize validation tools integration"):
                create_validation_integration()
    
    def test_get_integration_statistics(self):
        """Test get_integration_statistics function."""
        stats = get_integration_statistics()
        
        assert isinstance(stats, dict)
        assert 'total_integrations_created' in stats
        assert 'active_integrations' in stats
        assert 'total_sessions_processed' in stats


class TestIntegrationModes:
    """Test different validation modes."""
    
    def test_manual_selection_mode(self, validation_integration, sample_document_path):
        """Test manual selection validation mode."""
        session_id = validation_integration.start_validation_session(
            sample_document_path,
            mode=ValidationMode.MANUAL_SELECTION
        )
        
        session = validation_integration.sessions[session_id]
        assert session.mode == ValidationMode.MANUAL_SELECTION
    
    def test_ocr_assisted_mode(self, validation_integration, sample_document_path):
        """Test OCR assisted validation mode."""
        session_id = validation_integration.start_validation_session(
            sample_document_path,
            mode=ValidationMode.OCR_ASSISTED
        )
        
        session = validation_integration.sessions[session_id]
        assert session.mode == ValidationMode.OCR_ASSISTED
    
    def test_hybrid_workflow_mode(self, validation_integration, sample_document_path):
        """Test hybrid workflow validation mode."""
        session_id = validation_integration.start_validation_session(
            sample_document_path,
            mode=ValidationMode.HYBRID_WORKFLOW
        )
        
        session = validation_integration.sessions[session_id]
        assert session.mode == ValidationMode.HYBRID_WORKFLOW
    
    def test_batch_processing_mode(self, validation_integration, sample_document_path):
        """Test batch processing validation mode."""
        session_id = validation_integration.start_validation_session(
            sample_document_path,
            mode=ValidationMode.BATCH_PROCESSING
        )
        
        session = validation_integration.sessions[session_id]
        assert session.mode == ValidationMode.BATCH_PROCESSING


class TestIntegrationStressTests:
    """Stress tests for integration layer."""
    
    def test_multiple_concurrent_sessions(self, validation_integration, sample_document_path):
        """Test handling multiple concurrent sessions."""
        session_ids = []
        
        # Start multiple sessions
        for i in range(5):
            session_id = validation_integration.start_validation_session(
                sample_document_path,
                pages_total=3
            )
            session_ids.append(session_id)
        
        assert len(validation_integration.sessions) == 5
        assert validation_integration.statistics.total_sessions == 5
        
        # Process pages for all sessions
        for session_id in session_ids:
            for page in range(1, 4):
                validation_integration.process_page(session_id, page, QPixmap(100, 100))
        
        # Complete all sessions
        for session_id in session_ids:
            validation_integration.complete_session(session_id)
        
        # Verify all sessions completed
        for session_id in session_ids:
            session = validation_integration.sessions[session_id]
            assert session.status == IntegrationStatus.COMPLETED
    
    def test_large_element_processing(self, validation_integration, sample_document_path):
        """Test processing large number of elements."""
        session_id = validation_integration.start_validation_session(sample_document_path)
        
        # Validate many elements
        for i in range(100):
            element_data = {
                'type': 'text',
                'content': f'Element {i}',
                'bbox': [i, i, i+50, i+20]
            }
            validation_integration.validate_element(session_id, element_data)
        
        session = validation_integration.sessions[session_id]
        assert session.elements_validated == 100
        assert validation_integration.statistics.total_elements == 100
    
    def test_error_recovery(self, validation_integration, sample_document_path):
        """Test error recovery mechanisms."""
        session_id = validation_integration.start_validation_session(sample_document_path)
        
        # Simulate errors
        for i in range(3):
            validation_integration._on_component_error(f"Error {i}")
        
        session = validation_integration.sessions[session_id]
        assert len(session.errors) == 3
        
        # Verify session can still be completed
        result = validation_integration.complete_session(session_id)
        assert result is True
        assert session.status == IntegrationStatus.COMPLETED


if __name__ == '__main__':
    pytest.main([__file__])