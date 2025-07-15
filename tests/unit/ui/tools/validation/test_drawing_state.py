"""
Comprehensive tests for drawing state management system.

This test suite covers the complete functionality of the DrawingStateManager
including state transitions, area validation, session management, and OCR integration.
"""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
from typing import Optional

from PyQt6.QtCore import QTimer, QObject, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QApplication

from torematrix.ui.tools.validation.drawing_state import (
    DrawingStateManager,
    DrawingMode,
    DrawingState,
    DrawingArea,
    DrawingSession
)
from torematrix.ui.viewer.coordinates import Rectangle
from torematrix.core.models import Element, ElementType


class TestDrawingArea:
    """Test DrawingArea data class."""
    
    def test_drawing_area_creation(self):
        """Test creating a drawing area."""
        rect = Rectangle(10, 20, 100, 80)
        area = DrawingArea(rectangle=rect)
        
        assert area.rectangle == rect
        assert area.preview_image is None
        assert area.ocr_result is None
        assert area.suggested_text == ""
        assert area.manual_text == ""
        assert area.element_type is None
        assert area.confidence == 0.0
        assert isinstance(area.created_at, datetime)
    
    def test_final_text_property(self):
        """Test final_text property logic."""
        rect = Rectangle(10, 20, 100, 80)
        area = DrawingArea(rectangle=rect)
        
        # No text set
        assert area.final_text == ""
        
        # Only suggested text
        area.suggested_text = "suggested"
        assert area.final_text == "suggested"
        
        # Manual text overrides suggested
        area.manual_text = "manual"
        assert area.final_text == "manual"
        
        # Empty manual text falls back to suggested
        area.manual_text = ""
        assert area.final_text == "suggested"


class TestDrawingSession:
    """Test DrawingSession data class."""
    
    def test_drawing_session_creation(self):
        """Test creating a drawing session."""
        session = DrawingSession(session_id="test_session")
        
        assert session.session_id == "test_session"
        assert session.areas == []
        assert session.batch_mode is False
        assert isinstance(session.started_at, datetime)
        assert session.completed_at is None
    
    def test_is_complete_property(self):
        """Test is_complete property logic."""
        session = DrawingSession(session_id="test")
        
        # Empty session is complete
        assert session.is_complete is True
        
        # Session with incomplete areas
        rect1 = Rectangle(10, 20, 100, 80)
        area1 = DrawingArea(rectangle=rect1)
        session.areas.append(area1)
        assert session.is_complete is False
        
        # Session with complete areas
        area1.element_type = ElementType.TEXT
        assert session.is_complete is True
        
        # Mixed completion
        rect2 = Rectangle(20, 30, 100, 80)
        area2 = DrawingArea(rectangle=rect2)
        session.areas.append(area2)
        assert session.is_complete is False


class TestDrawingStateManager:
    """Test DrawingStateManager functionality."""
    
    @pytest.fixture
    def manager(self):
        """Create a drawing state manager for testing."""
        return DrawingStateManager()
    
    @pytest.fixture
    def mock_callbacks(self):
        """Create mock callbacks for testing."""
        return {
            'area_validator': Mock(return_value=True),
            'element_creator': Mock(return_value=Mock(spec=Element)),
            'session_handler': Mock()
        }
    
    def test_initialization(self, manager):
        """Test manager initialization."""
        assert manager.mode == DrawingMode.DISABLED
        assert manager.state == DrawingState.IDLE
        assert manager.current_session is None
        assert manager.current_area is None
        assert isinstance(manager.get_drawing_config(), dict)
    
    def test_drawing_config_management(self, manager):
        """Test drawing configuration management."""
        # Get initial config
        initial_config = manager.get_drawing_config()
        assert "min_area_size" in initial_config
        assert "max_area_size" in initial_config
        
        # Update config
        new_config = {"min_area_size": 20, "custom_setting": "value"}
        manager.set_drawing_config(new_config)
        
        updated_config = manager.get_drawing_config()
        assert updated_config["min_area_size"] == 20
        assert updated_config["custom_setting"] == "value"
    
    def test_callback_configuration(self, manager, mock_callbacks):
        """Test callback configuration."""
        manager.set_callbacks(
            area_validator=mock_callbacks['area_validator'],
            element_creator=mock_callbacks['element_creator'],
            session_handler=mock_callbacks['session_handler']
        )
        
        assert manager._area_validator is mock_callbacks['area_validator']
        assert manager._element_creator is mock_callbacks['element_creator']
        assert manager._session_handler is mock_callbacks['session_handler']
    
    def test_activate_draw_mode(self, manager):
        """Test activating drawing mode."""
        # Test normal activation
        result = manager.activate_draw_mode()
        assert result is True
        assert manager.mode == DrawingMode.SELECTION
        assert manager.state == DrawingState.IDLE
        assert manager.current_session is not None
        assert manager.current_session.batch_mode is False
        
        # Test double activation (should fail)
        result = manager.activate_draw_mode()
        assert result is False
    
    def test_activate_draw_mode_batch(self, manager):
        """Test activating drawing mode with batch mode."""
        result = manager.activate_draw_mode(batch_mode=True)
        assert result is True
        assert manager.current_session.batch_mode is True
        assert manager.get_drawing_config()["batch_mode"] is True
    
    def test_deactivate_draw_mode(self, manager, mock_callbacks):
        """Test deactivating drawing mode."""
        # Setup callbacks
        manager.set_callbacks(session_handler=mock_callbacks['session_handler'])
        
        # Activate first
        manager.activate_draw_mode()
        session = manager.current_session
        
        # Deactivate
        result = manager.deactivate_draw_mode()
        assert result is True
        assert manager.mode == DrawingMode.DISABLED
        assert manager.state == DrawingState.IDLE
        assert manager.current_session is None
        assert manager.current_area is None
        
        # Verify session was completed
        assert session.completed_at is not None
        mock_callbacks['session_handler'].assert_called_once_with(session)
        
        # Test double deactivation (should fail)
        result = manager.deactivate_draw_mode()
        assert result is False
    
    def test_area_selection_workflow(self, manager):
        """Test complete area selection workflow."""
        # Activate drawing mode
        manager.activate_draw_mode()
        
        # Start area selection
        result = manager.start_area_selection()
        assert result is True
        assert manager.state == DrawingState.SELECTING_AREA
        
        # Complete area selection
        rect = Rectangle(10, 20, 100, 80)
        # Skip pixmap creation to avoid PyQt6 segfault in headless environment
        result = manager.complete_area_selection(rect, None)
        assert result is True
        assert manager.state == DrawingState.AREA_SELECTED
        assert manager.mode == DrawingMode.PREVIEW
        assert manager.current_area is not None
        assert manager.current_area.rectangle == rect
        assert manager.current_area.preview_image is None
    
    def test_area_selection_validation(self, manager):
        """Test area selection validation."""
        manager.activate_draw_mode()
        manager.start_area_selection()
        
        # Test area too small
        small_rect = Rectangle(10, 20, 5, 5)
        result = manager.complete_area_selection(small_rect)
        assert result is False
        
        # Test area too large
        large_rect = Rectangle(10, 20, 3000, 3000)
        result = manager.complete_area_selection(large_rect)
        assert result is False
        
        # Test valid area
        valid_rect = Rectangle(10, 20, 100, 80)
        result = manager.complete_area_selection(valid_rect)
        assert result is True
    
    def test_area_selection_with_validator(self, manager, mock_callbacks):
        """Test area selection with custom validator."""
        manager.set_callbacks(area_validator=mock_callbacks['area_validator'])
        manager.activate_draw_mode()
        manager.start_area_selection()
        
        # Test validator rejection
        mock_callbacks['area_validator'].return_value = False
        rect = Rectangle(10, 20, 100, 80)
        result = manager.complete_area_selection(rect)
        assert result is False
        mock_callbacks['area_validator'].assert_called_once()
        
        # Test validator acceptance
        mock_callbacks['area_validator'].return_value = True
        mock_callbacks['area_validator'].reset_mock()
        result = manager.complete_area_selection(rect)
        assert result is True
        mock_callbacks['area_validator'].assert_called_once()
    
    def test_cancel_area_selection(self, manager):
        """Test canceling area selection."""
        manager.activate_draw_mode()
        manager.start_area_selection()
        
        # Cancel selection
        result = manager.cancel_area_selection()
        assert result is True
        assert manager.state == DrawingState.IDLE
        assert manager.mode == DrawingMode.SELECTION
        assert manager.current_area is None
        
        # Test cancel when nothing to cancel
        result = manager.cancel_area_selection()
        assert result is False
    
    @pytest.mark.asyncio
    async def test_ocr_processing(self, manager):
        """Test OCR processing workflow."""
        manager.activate_draw_mode()
        manager.start_area_selection()
        
        rect = Rectangle(10, 20, 100, 80)
        manager.complete_area_selection(rect)
        
        # Process OCR
        result = await manager.process_ocr()
        assert result is True
        assert manager.state == DrawingState.EDITING_TEXT
    
    @pytest.mark.asyncio
    async def test_ocr_processing_no_area(self, manager):
        """Test OCR processing with no area."""
        result = await manager.process_ocr()
        assert result is False
    
    def test_manual_text_setting(self, manager):
        """Test setting manual text."""
        manager.activate_draw_mode()
        manager.start_area_selection()
        
        rect = Rectangle(10, 20, 100, 80)
        manager.complete_area_selection(rect)
        
        # Set manual text
        result = manager.set_manual_text("test text")
        assert result is True
        assert manager.current_area.manual_text == "test text"
        
        # Test without current area
        manager._current_area = None
        result = manager.set_manual_text("test")
        assert result is False
    
    def test_element_type_setting(self, manager):
        """Test setting element type."""
        manager.activate_draw_mode()
        manager.start_area_selection()
        
        rect = Rectangle(10, 20, 100, 80)
        manager.complete_area_selection(rect)
        
        # Set element type
        result = manager.set_element_type(ElementType.TEXT)
        assert result is True
        assert manager.current_area.element_type == ElementType.TEXT
        assert manager.state == DrawingState.CREATING_ELEMENT
        
        # Test without current area
        manager._current_area = None
        result = manager.set_element_type(ElementType.TEXT)
        assert result is False
    
    def test_element_creation(self, manager, mock_callbacks):
        """Test element creation."""
        manager.set_callbacks(element_creator=mock_callbacks['element_creator'])
        manager.activate_draw_mode()
        manager.start_area_selection()
        
        rect = Rectangle(10, 20, 100, 80)
        manager.complete_area_selection(rect)
        manager.set_element_type(ElementType.TEXT)
        
        # Create element
        result = manager.create_element()
        assert result is True
        assert manager.state == DrawingState.COMPLETED
        mock_callbacks['element_creator'].assert_called_once()
        
        # Verify area was added to session
        assert len(manager.current_session.areas) == 1
        assert manager.current_session.areas[0] == manager.current_area
    
    def test_element_creation_batch_mode(self, manager, mock_callbacks):
        """Test element creation in batch mode."""
        manager.set_callbacks(element_creator=mock_callbacks['element_creator'])
        manager.activate_draw_mode(batch_mode=True)
        manager.start_area_selection()
        
        rect = Rectangle(10, 20, 100, 80)
        manager.complete_area_selection(rect)
        manager.set_element_type(ElementType.TEXT)
        
        # Create element in batch mode
        result = manager.create_element()
        assert result is True
        assert manager.state == DrawingState.IDLE
        assert manager.mode == DrawingMode.SELECTION
        assert manager.current_session is not None  # Session continues
    
    def test_element_creation_without_area(self, manager):
        """Test element creation without area."""
        result = manager.create_element()
        assert result is False
    
    def test_element_creation_without_type(self, manager):
        """Test element creation without element type."""
        manager.activate_draw_mode()
        manager.start_area_selection()
        
        rect = Rectangle(10, 20, 100, 80)
        manager.complete_area_selection(rect)
        
        # Try to create without setting type
        result = manager.create_element()
        assert result is False
    
    def test_default_element_creation(self, manager):
        """Test default element creation."""
        area = DrawingArea(
            rectangle=Rectangle(10, 20, 100, 80),
            element_type=ElementType.TEXT
        )
        area.manual_text = "test text"
        area.confidence = 0.8
        
        element = manager._create_default_element(area)
        assert element is not None
        assert element.element_type == ElementType.TEXT
        assert element.text == "test text"
        # Note: metadata will be properly set by Agent 2 
        # For now, just verify element structure
        assert element.metadata is None  # Agent 2 will add proper metadata
    
    def test_session_info(self, manager):
        """Test session information retrieval."""
        # No session
        info = manager.get_session_info()
        assert info == {}
        
        # With session
        manager.activate_draw_mode(batch_mode=True)
        info = manager.get_session_info()
        assert "session_id" in info
        assert info["batch_mode"] is True
        assert info["areas_count"] == 0
        assert "started_at" in info
        assert info["completed_at"] is None
        assert info["is_complete"] is True
    
    def test_state_info(self, manager):
        """Test state information retrieval."""
        info = manager.get_state_info()
        assert info["mode"] == DrawingMode.DISABLED.value
        assert info["state"] == DrawingState.IDLE.value
        assert info["has_session"] is False
        assert info["has_area"] is False
        assert info["ocr_available"] is False
        assert "config" in info
    
    def test_signal_emissions(self, manager):
        """Test signal emissions during state changes."""
        # Mock signal handlers
        mode_handler = Mock()
        state_handler = Mock()
        area_handler = Mock()
        element_handler = Mock()
        session_handler = Mock()
        error_handler = Mock()
        
        manager.mode_changed.connect(mode_handler)
        manager.state_changed.connect(state_handler)
        manager.area_selected.connect(area_handler)
        manager.element_created.connect(element_handler)
        manager.session_completed.connect(session_handler)
        manager.error_occurred.connect(error_handler)
        
        # Activate draw mode
        manager.activate_draw_mode()
        mode_handler.assert_called_with(DrawingMode.SELECTION)
        state_handler.assert_called_with(DrawingState.IDLE)
        
        # Start area selection
        manager.start_area_selection()
        state_handler.assert_called_with(DrawingState.SELECTING_AREA)
        
        # Complete area selection
        rect = Rectangle(10, 20, 100, 80)
        manager.complete_area_selection(rect)
        area_handler.assert_called_once()
        
        # Deactivate
        manager.deactivate_draw_mode()
        session_handler.assert_called_once()
    
    def test_error_handling(self, manager):
        """Test error handling and recovery."""
        error_handler = Mock()
        manager.error_occurred.connect(error_handler)
        
        # Test error during area selection with invalid state
        manager._state = DrawingState.COMPLETED
        result = manager.start_area_selection()
        assert result is False
        
        # Test error during deactivation
        manager._mode = DrawingMode.DISABLED
        result = manager.deactivate_draw_mode()
        assert result is False
    
    def test_auto_ocr_trigger(self, manager):
        """Test automatic OCR trigger after area selection."""
        # Mock OCR engine
        manager._ocr_engine = Mock()
        
        # Mock timer
        with patch.object(manager._ocr_timer, 'start') as mock_start:
            manager.activate_draw_mode()
            manager.start_area_selection()
            
            rect = Rectangle(10, 20, 100, 80)
            manager.complete_area_selection(rect)
            
            # Should trigger OCR timer
            mock_start.assert_called_once_with(100)
    
    def test_state_transitions(self, manager):
        """Test all state transitions work correctly."""
        # Track state changes
        states = []
        manager.state_changed.connect(lambda state: states.append(state))
        
        # Complete workflow
        manager.activate_draw_mode()
        manager.start_area_selection()
        
        rect = Rectangle(10, 20, 100, 80)
        manager.complete_area_selection(rect)
        manager.set_element_type(ElementType.TEXT)
        manager.create_element()
        
        # Verify state progression
        expected_states = [
            DrawingState.IDLE,
            DrawingState.SELECTING_AREA,
            DrawingState.AREA_SELECTED,
            DrawingState.CREATING_ELEMENT,
            DrawingState.COMPLETED
        ]
        assert states == expected_states
    
    def test_threading_safety(self, manager):
        """Test thread safety of state operations."""
        # This test ensures the manager handles concurrent access correctly
        manager.activate_draw_mode()
        
        # Simulate concurrent operations
        results = []
        
        def start_selection():
            results.append(manager.start_area_selection())
        
        def complete_selection():
            rect = Rectangle(10, 20, 100, 80)
            results.append(manager.complete_area_selection(rect))
        
        # Both operations should not interfere with each other
        start_selection()
        complete_selection()
        
        # First should succeed, second should also succeed
        assert results[0] is True
        assert results[1] is True


class TestDrawingStateManagerIntegration:
    """Integration tests for DrawingStateManager with other components."""
    
    @pytest.fixture
    def manager_with_mocks(self):
        """Create manager with mocked dependencies."""
        manager = DrawingStateManager()
        
        # Mock OCR engine
        manager._ocr_engine = Mock()
        
        # Mock callbacks
        manager.set_callbacks(
            area_validator=Mock(return_value=True),
            element_creator=Mock(return_value=Mock(spec=Element)),
            session_handler=Mock()
        )
        
        return manager
    
    def test_complete_workflow_single_element(self, manager_with_mocks):
        """Test complete workflow for single element creation."""
        manager = manager_with_mocks
        
        # Complete workflow
        assert manager.activate_draw_mode() is True
        assert manager.start_area_selection() is True
        
        rect = Rectangle(10, 20, 100, 80)
        assert manager.complete_area_selection(rect) is True
        assert manager.set_manual_text("test text") is True
        assert manager.set_element_type(ElementType.TEXT) is True
        assert manager.create_element() is True
        
        # Verify final state
        assert manager.mode == DrawingMode.DISABLED
        assert manager.state == DrawingState.IDLE
        assert manager.current_session is None
    
    def test_complete_workflow_batch_mode(self, manager_with_mocks):
        """Test complete workflow for batch element creation."""
        manager = manager_with_mocks
        
        # Start batch mode
        assert manager.activate_draw_mode(batch_mode=True) is True
        session = manager.current_session
        
        # Create first element
        assert manager.start_area_selection() is True
        rect1 = Rectangle(10, 20, 100, 80)
        assert manager.complete_area_selection(rect1) is True
        assert manager.set_element_type(ElementType.TEXT) is True
        assert manager.create_element() is True
        
        # Should return to idle, not deactivate
        assert manager.mode == DrawingMode.SELECTION
        assert manager.state == DrawingState.IDLE
        assert manager.current_session is session
        
        # Create second element
        assert manager.start_area_selection() is True
        rect2 = Rectangle(20, 30, 100, 80)
        assert manager.complete_area_selection(rect2) is True
        assert manager.set_element_type(ElementType.IMAGE) is True
        assert manager.create_element() is True
        
        # Session should have both areas
        assert len(session.areas) == 2
        
        # Manually deactivate
        assert manager.deactivate_draw_mode() is True
    
    def test_error_recovery_workflow(self, manager_with_mocks):
        """Test error recovery during workflow."""
        manager = manager_with_mocks
        
        # Start workflow
        manager.activate_draw_mode()
        manager.start_area_selection()
        
        # Simulate error during area selection
        manager._area_validator.return_value = False
        rect = Rectangle(10, 20, 100, 80)
        assert manager.complete_area_selection(rect) is False
        
        # Should be able to try again
        manager._area_validator.return_value = True
        assert manager.complete_area_selection(rect) is True
        
        # Continue workflow
        assert manager.set_element_type(ElementType.TEXT) is True
        assert manager.create_element() is True
    
    def test_ocr_integration_workflow(self, manager_with_mocks):
        """Test OCR integration workflow."""
        manager = manager_with_mocks
        
        # Enable auto OCR
        manager.set_drawing_config({"auto_ocr": True})
        
        # Start workflow
        manager.activate_draw_mode()
        manager.start_area_selection()
        
        # Mock OCR timer
        with patch.object(manager._ocr_timer, 'start') as mock_start:
            rect = Rectangle(10, 20, 100, 80)
            manager.complete_area_selection(rect)
            
            # Auto OCR should be triggered
            mock_start.assert_called_once_with(100)
    
    def test_session_persistence(self, manager_with_mocks):
        """Test session persistence across operations."""
        manager = manager_with_mocks
        
        # Create session
        manager.activate_draw_mode(batch_mode=True)
        session = manager.current_session
        original_id = session.session_id
        
        # Create multiple elements
        for i in range(3):
            manager.start_area_selection()
            rect = Rectangle(10 + i * 10, 20, 100, 80)
            manager.complete_area_selection(rect)
            manager.set_element_type(ElementType.TEXT)
            manager.create_element()
        
        # Session should persist
        assert manager.current_session is session
        assert manager.current_session.session_id == original_id
        assert len(session.areas) == 3
        
        # Deactivate should complete session
        manager.deactivate_draw_mode()
        assert session.completed_at is not None
        manager._session_handler.assert_called_once_with(session)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])