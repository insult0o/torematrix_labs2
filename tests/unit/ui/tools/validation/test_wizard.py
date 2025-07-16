"""
Comprehensive tests for ValidationWizard component.

Agent 3 test implementation for Issue #242 - UI Components & User Experience.
Tests cover wizard workflow, state management, performance optimization,
and user experience features.
"""

import pytest
import sys
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime

from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtTest import QTest

# Import the components we're testing
from src.torematrix.ui.tools.validation.wizard import (
    ValidationWizard, WizardStep, WizardState, WelcomePage, AreaSelectionPage,
    OCRProcessingPage, TextReviewPage, ElementTypePage, FinalReviewPage
)
from src.torematrix.ui.tools.validation.drawing_state import (
    DrawingStateManager, DrawingState, DrawingArea, DrawingMode
)
from src.torematrix.core.models import Element, ElementType


class TestWizardState:
    """Test WizardState data class."""
    
    def test_wizard_state_initialization(self):
        """Test WizardState initialization with defaults."""
        state = WizardState()
        
        assert state.current_step == WizardStep.WELCOME
        assert state.selected_area is None
        assert state.extracted_text == ""
        assert state.manual_text == ""
        assert state.selected_element_type is None
        assert state.confidence_score == 0.0
        assert state.validation_notes == ""
        assert isinstance(state.started_at, datetime)
    
    def test_final_text_property(self):
        """Test final_text property logic."""
        state = WizardState()
        
        # Should return extracted text when no manual text
        state.extracted_text = "OCR extracted text"
        assert state.final_text == "OCR extracted text"
        
        # Should return manual text when available
        state.manual_text = "Manual override"
        assert state.final_text == "Manual override"
        
        # Should return extracted text when manual text is empty
        state.manual_text = "   "
        assert state.final_text == "OCR extracted text"


class TestValidationWizard:
    """Test ValidationWizard main component."""
    
    @pytest.fixture
    def app(self):
        """Create QApplication for testing."""
        if not QApplication.instance():
            return QApplication(sys.argv)
        return QApplication.instance()
    
    @pytest.fixture
    def mock_state_manager(self):
        """Create mock DrawingStateManager."""
        mock_manager = Mock(spec=DrawingStateManager)
        mock_manager.area_selected = Mock()
        mock_manager.state_changed = Mock()
        mock_manager.start_area_selection = Mock(return_value=True)
        return mock_manager
    
    @pytest.fixture
    def wizard(self, app, mock_state_manager):
        """Create ValidationWizard instance for testing."""
        return ValidationWizard(mock_state_manager)
    
    def test_wizard_initialization(self, wizard, mock_state_manager):
        """Test wizard initialization."""
        assert wizard.state_manager == mock_state_manager
        assert isinstance(wizard.wizard_state, WizardState)
        assert wizard.windowTitle() == "Manual Validation Wizard"
        assert wizard.minimumSize().width() == 800
        assert wizard.minimumSize().height() == 600
        
        # Check that pages are added
        assert wizard.pageCount() == 6
    
    def test_wizard_styling(self, wizard):
        """Test wizard has proper styling applied."""
        style_sheet = wizard.styleSheet()
        assert "QWizard" in style_sheet
        assert "background-color" in style_sheet
        assert "font-family" in style_sheet
    
    def test_page_creation(self, wizard):
        """Test that all wizard pages are created."""
        assert wizard.pageCount() == 6
        
        page_types = [
            WelcomePage, AreaSelectionPage, OCRProcessingPage,
            TextReviewPage, ElementTypePage, FinalReviewPage
        ]
        
        for i, expected_type in enumerate(page_types):
            page = wizard.page(i)
            assert isinstance(page, expected_type)
    
    def test_page_navigation(self, wizard):
        """Test wizard page navigation."""
        # Start at welcome page
        assert wizard.currentId() == 0
        
        # Test navigation to next page
        wizard.next()
        assert wizard.currentId() == 1
        
        # Test navigation back
        wizard.back()
        assert wizard.currentId() == 0
    
    def test_wizard_state_updates(self, wizard):
        """Test wizard state updates during navigation."""
        initial_state = wizard.wizard_state.current_step
        assert initial_state == WizardStep.WELCOME
        
        # Navigate to area selection
        wizard.next()
        
        # Check state is updated (need to trigger page change manually in test)
        wizard._page_changed(1)
        assert wizard.wizard_state.current_step == WizardStep.AREA_SELECTION
    
    def test_area_selection_signal_handling(self, wizard, mock_state_manager):
        """Test area selection signal handling."""
        # Create mock drawing area
        mock_area = Mock(spec=DrawingArea)
        mock_area.area_id = "test_area_123"
        
        # Simulate area selection signal
        wizard._on_area_selected(mock_area)
        
        assert wizard.wizard_state.selected_area == mock_area
    
    def test_state_change_signal_handling(self, wizard):
        """Test state change signal handling."""
        # This should not raise an exception
        wizard._on_state_changed(DrawingState.AREA_SELECTED)
    
    def test_performance_optimization_features(self, wizard):
        """Test performance optimization features."""
        # Check lazy loading is enabled
        assert wizard._lazy_loading is True
        
        # Check cache is enabled
        assert wizard._cache_enabled is True
        
        # Check render timer exists
        assert isinstance(wizard._render_timer, QTimer)
        assert wizard._render_timer.isSingleShot()
    
    def test_validation_summary(self, wizard):
        """Test validation summary generation."""
        # Set up some state
        wizard.wizard_state.extracted_text = "Sample text"
        wizard.wizard_state.confidence_score = 0.85
        
        summary = wizard.get_validation_summary()
        
        assert "wizard_state" in summary
        assert "performance_metrics" in summary
        assert summary["wizard_state"]["extracted_text"] == "Sample text"
        assert summary["wizard_state"]["confidence_score"] == 0.85
        assert summary["performance_metrics"]["cache_enabled"] is True
    
    def test_help_functionality(self, wizard):
        """Test help system."""
        # Mock current page with help text
        mock_page = Mock()
        mock_page.get_help_text = Mock(return_value="Test help text")
        
        with patch.object(wizard, 'currentPage', return_value=mock_page):
            wizard._show_help()
            mock_page.get_help_text.assert_called_once()


class TestWelcomePage:
    """Test WelcomePage component."""
    
    @pytest.fixture
    def app(self):
        """Create QApplication for testing."""
        if not QApplication.instance():
            return QApplication(sys.argv)
        return QApplication.instance()
    
    @pytest.fixture
    def wizard(self, app):
        """Create mock wizard for page testing."""
        mock_wizard = Mock(spec=ValidationWizard)
        return mock_wizard
    
    @pytest.fixture
    def welcome_page(self, wizard):
        """Create WelcomePage instance."""
        return WelcomePage(wizard)
    
    def test_welcome_page_initialization(self, welcome_page):
        """Test welcome page initialization."""
        assert welcome_page.title() == "Manual Validation Wizard"
        assert "Welcome to the comprehensive document validation workflow" in welcome_page.subTitle()
    
    def test_help_text(self, welcome_page):
        """Test welcome page help text."""
        help_text = welcome_page.get_help_text()
        assert "welcome page" in help_text.lower()
        assert "next" in help_text.lower()


class TestAreaSelectionPage:
    """Test AreaSelectionPage component."""
    
    @pytest.fixture
    def app(self):
        """Create QApplication for testing."""
        if not QApplication.instance():
            return QApplication(sys.argv)
        return QApplication.instance()
    
    @pytest.fixture
    def mock_wizard(self, app):
        """Create mock wizard with state manager."""
        mock_wizard = Mock(spec=ValidationWizard)
        mock_wizard.state_manager = Mock(spec=DrawingStateManager)
        mock_wizard.state_manager.start_area_selection = Mock(return_value=True)
        mock_wizard.wizard_state = Mock()
        mock_wizard.wizard_state.selected_area = None
        return mock_wizard
    
    @pytest.fixture
    def selection_page(self, mock_wizard):
        """Create AreaSelectionPage instance."""
        return AreaSelectionPage(mock_wizard)
    
    def test_selection_page_initialization(self, selection_page):
        """Test area selection page initialization."""
        assert selection_page.title() == "Area Selection"
        assert "Select the document area" in selection_page.subTitle()
    
    def test_start_selection_button(self, selection_page, mock_wizard):
        """Test start selection button functionality."""
        # Find the start selection button
        start_btn = selection_page.start_selection_btn
        assert start_btn is not None
        
        # Simulate button click
        selection_page._start_selection()
        
        # Verify state manager was called
        mock_wizard.state_manager.start_area_selection.assert_called_once()
        
        # Verify button states
        assert not start_btn.isEnabled()
        assert selection_page.cancel_selection_btn.isEnabled()
    
    def test_cancel_selection_button(self, selection_page):
        """Test cancel selection button functionality."""
        # First start selection
        selection_page._start_selection()
        
        # Then cancel
        selection_page._cancel_selection()
        
        # Verify button states are reset
        assert selection_page.start_selection_btn.isEnabled()
        assert not selection_page.cancel_selection_btn.isEnabled()
    
    def test_page_completion_status(self, selection_page, mock_wizard):
        """Test page completion status based on area selection."""
        # Initially not complete
        assert not selection_page.isComplete()
        
        # Set selected area
        mock_wizard.wizard_state.selected_area = Mock(spec=DrawingArea)
        
        # Now should be complete
        assert selection_page.isComplete()
    
    def test_help_text(self, selection_page):
        """Test area selection page help text."""
        help_text = selection_page.get_help_text()
        assert "start selection" in help_text.lower()
        assert "rectangle" in help_text.lower()


class TestOCRProcessingPage:
    """Test OCRProcessingPage component."""
    
    @pytest.fixture
    def app(self):
        """Create QApplication for testing."""
        if not QApplication.instance():
            return QApplication(sys.argv)
        return QApplication.instance()
    
    @pytest.fixture
    def mock_wizard(self, app):
        """Create mock wizard."""
        mock_wizard = Mock(spec=ValidationWizard)
        mock_wizard.wizard_state = Mock()
        mock_wizard.wizard_state.extracted_text = ""
        mock_wizard.text_extracted = Mock()
        return mock_wizard
    
    @pytest.fixture
    def ocr_page(self, mock_wizard):
        """Create OCRProcessingPage instance."""
        return OCRProcessingPage(mock_wizard)
    
    def test_ocr_page_initialization(self, ocr_page):
        """Test OCR processing page initialization."""
        assert ocr_page.title() == "OCR Processing"
        assert "Extracting text" in ocr_page.subTitle()
        
        # Check progress bar exists
        assert ocr_page.progress_bar is not None
        assert ocr_page.progress_bar.minimum() == 0
        assert ocr_page.progress_bar.maximum() == 100
    
    def test_progress_simulation(self, ocr_page, mock_wizard):
        """Test OCR progress simulation."""
        # Initialize the page to start processing
        ocr_page.initializePage()
        
        # Verify timer is started
        assert ocr_page.processing_timer.isActive()
        
        # Simulate progress updates
        initial_progress = ocr_page.progress_value
        ocr_page._update_progress()
        
        assert ocr_page.progress_value > initial_progress
        assert ocr_page.progress_bar.value() > 0
    
    def test_ocr_completion(self, ocr_page, mock_wizard):
        """Test OCR processing completion."""
        # Set progress to near completion
        ocr_page.progress_value = 95
        ocr_page._update_progress()
        
        # Should complete and update wizard state
        assert mock_wizard.wizard_state.extracted_text != ""
        assert mock_wizard.wizard_state.confidence_score > 0
    
    def test_page_completion_status(self, ocr_page, mock_wizard):
        """Test page completion status."""
        # Initially not complete
        assert not ocr_page.isComplete()
        
        # Set extracted text
        mock_wizard.wizard_state.extracted_text = "Sample text"
        
        # Now should be complete
        assert ocr_page.isComplete()
    
    def test_help_text(self, ocr_page):
        """Test OCR processing page help text."""
        help_text = ocr_page.get_help_text()
        assert "ocr processing" in help_text.lower()
        assert "wait" in help_text.lower()


class TestTextReviewPage:
    """Test TextReviewPage component."""
    
    @pytest.fixture
    def app(self):
        """Create QApplication for testing."""
        if not QApplication.instance():
            return QApplication(sys.argv)
        return QApplication.instance()
    
    @pytest.fixture
    def mock_wizard(self, app):
        """Create mock wizard."""
        mock_wizard = Mock(spec=ValidationWizard)
        mock_wizard.wizard_state = Mock()
        mock_wizard.wizard_state.extracted_text = "Sample extracted text"
        return mock_wizard
    
    @pytest.fixture
    def review_page(self, mock_wizard):
        """Create TextReviewPage instance."""
        return TextReviewPage(mock_wizard)
    
    def test_review_page_initialization(self, review_page):
        """Test text review page initialization."""
        assert review_page.title() == "Text Review"
        assert "Review and edit" in review_page.subTitle()
        
        # Check text edit widget exists
        assert review_page.text_edit is not None
    
    def test_page_initialization_with_text(self, review_page, mock_wizard):
        """Test page initialization with extracted text."""
        review_page.initializePage()
        
        # Should populate text edit with extracted text
        assert review_page.text_edit.toPlainText() == "Sample extracted text"
    
    def test_page_completion_status(self, review_page):
        """Test page completion status based on text content."""
        # Initially not complete (empty text)
        review_page.text_edit.setPlainText("")
        assert not review_page.isComplete()
        
        # Add text content
        review_page.text_edit.setPlainText("Some text content")
        assert review_page.isComplete()
        
        # Whitespace only should not be complete
        review_page.text_edit.setPlainText("   \n   ")
        assert not review_page.isComplete()


class TestElementTypePage:
    """Test ElementTypePage component."""
    
    @pytest.fixture
    def app(self):
        """Create QApplication for testing."""
        if not QApplication.instance():
            return QApplication(sys.argv)
        return QApplication.instance()
    
    @pytest.fixture
    def mock_wizard(self, app):
        """Create mock wizard."""
        return Mock(spec=ValidationWizard)
    
    @pytest.fixture
    def element_page(self, mock_wizard):
        """Create ElementTypePage instance."""
        return ElementTypePage(mock_wizard)
    
    def test_element_page_initialization(self, element_page):
        """Test element type page initialization."""
        assert element_page.title() == "Element Type"
        assert "Select the type" in element_page.subTitle()
        
        # Check button group exists
        assert element_page.button_group is not None
    
    def test_page_completion_status(self, element_page):
        """Test page completion status based on selection."""
        # Initially not complete
        assert not element_page.isComplete()
        
        # Select a radio button (simulate user selection)
        buttons = element_page.button_group.buttons()
        if buttons:
            buttons[0].setChecked(True)
            assert element_page.isComplete()


class TestFinalReviewPage:
    """Test FinalReviewPage component."""
    
    @pytest.fixture
    def app(self):
        """Create QApplication for testing."""
        if not QApplication.instance():
            return QApplication(sys.argv)
        return QApplication.instance()
    
    @pytest.fixture
    def mock_wizard(self, app):
        """Create mock wizard."""
        mock_wizard = Mock(spec=ValidationWizard)
        mock_wizard.get_validation_summary = Mock(return_value={"test": "summary"})
        return mock_wizard
    
    @pytest.fixture
    def final_page(self, mock_wizard):
        """Create FinalReviewPage instance."""
        return FinalReviewPage(mock_wizard)
    
    def test_final_page_initialization(self, final_page):
        """Test final review page initialization."""
        assert final_page.title() == "Final Review"
        assert "Review all details" in final_page.subTitle()
        
        # Check summary text widget exists
        assert final_page.summary_text is not None
        assert final_page.summary_text.isReadOnly()
    
    def test_page_initialization_with_summary(self, final_page, mock_wizard):
        """Test page initialization with summary data."""
        final_page.initializePage()
        
        # Should call get_validation_summary
        mock_wizard.get_validation_summary.assert_called_once()
        
        # Should populate summary text
        assert final_page.summary_text.toPlainText() != ""
    
    def test_page_completion_status(self, final_page):
        """Test page completion status (always complete)."""
        assert final_page.isComplete()


class TestWizardIntegration:
    """Integration tests for wizard components."""
    
    @pytest.fixture
    def app(self):
        """Create QApplication for testing."""
        if not QApplication.instance():
            return QApplication(sys.argv)
        return QApplication.instance()
    
    @pytest.fixture
    def full_wizard(self, app):
        """Create full wizard with real state manager for integration testing."""
        # Use a mock state manager for testing
        mock_state_manager = Mock(spec=DrawingStateManager)
        mock_state_manager.area_selected = Mock()
        mock_state_manager.state_changed = Mock()
        return ValidationWizard(mock_state_manager)
    
    def test_complete_wizard_workflow(self, full_wizard):
        """Test complete wizard workflow simulation."""
        # Start at welcome page
        assert full_wizard.currentId() == 0
        
        # Navigate through all pages
        for i in range(full_wizard.pageCount() - 1):
            # Set up conditions for page completion
            current_page = full_wizard.currentPage()
            
            # Simulate completion conditions
            if hasattr(current_page, 'wizard'):
                if isinstance(current_page, AreaSelectionPage):
                    # Simulate area selection
                    mock_area = Mock(spec=DrawingArea)
                    mock_area.area_id = "test_area"
                    full_wizard.wizard_state.selected_area = mock_area
                elif isinstance(current_page, OCRProcessingPage):
                    # Simulate OCR completion
                    full_wizard.wizard_state.extracted_text = "Extracted text"
                elif isinstance(current_page, ElementTypePage):
                    # Simulate element type selection
                    if hasattr(current_page, 'button_group'):
                        buttons = current_page.button_group.buttons()
                        if buttons:
                            buttons[0].setChecked(True)
            
            # Navigate to next page
            if full_wizard.hasNextPage():
                full_wizard.next()
        
        # Should reach final page
        assert full_wizard.currentId() == full_wizard.pageCount() - 1
    
    def test_wizard_signals_connectivity(self, full_wizard):
        """Test wizard signals are properly connected."""
        # Test that signals exist and are callable
        assert hasattr(full_wizard, 'area_selected')
        assert hasattr(full_wizard, 'text_extracted')
        assert hasattr(full_wizard, 'element_created')
        assert hasattr(full_wizard, 'wizard_completed')
        assert hasattr(full_wizard, 'wizard_cancelled')
    
    def test_performance_under_load(self, full_wizard):
        """Test wizard performance with rapid navigation."""
        # Simulate rapid page changes
        for _ in range(10):
            for i in range(full_wizard.pageCount()):
                full_wizard._page_changed(i)
        
        # Should still be responsive
        assert full_wizard.currentId() >= 0
        assert full_wizard.wizard_state.current_step in WizardStep
    
    @patch('PyQt6.QtCore.QTimer.start')
    def test_delayed_rendering_optimization(self, mock_timer_start, full_wizard):
        """Test delayed rendering optimization."""
        # Trigger page change
        full_wizard._page_changed(1)
        
        # Should start render timer for optimization
        mock_timer_start.assert_called_with(50)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])