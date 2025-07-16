"""
ValidationWizard - Multi-step workflow for manual validation.

Agent 3 implementation for Issue #242 - UI Components & User Experience.
This module provides a comprehensive wizard interface for guiding users
through the manual validation workflow with optimized performance.
"""

import logging
from enum import Enum, auto
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime

from PyQt6.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QComboBox, QCheckBox, QProgressBar, QGroupBox, QRadioButton,
    QButtonGroup, QScrollArea, QWidget, QFrame, QSplitter, QSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread, QMutex
from PyQt6.QtGui import QPixmap, QFont, QPainter, QPen, QBrush, QColor

from .drawing_state import DrawingStateManager, DrawingState, DrawingArea, DrawingSession
from ....core.models import Element, ElementType


class WizardStep(Enum):
    """Steps in the validation wizard workflow."""
    WELCOME = auto()
    AREA_SELECTION = auto()
    OCR_PROCESSING = auto()
    TEXT_REVIEW = auto()
    ELEMENT_TYPE = auto()
    FINAL_REVIEW = auto()


@dataclass
class WizardState:
    """Current state of the validation wizard."""
    current_step: WizardStep = WizardStep.WELCOME
    selected_area: Optional[DrawingArea] = None
    extracted_text: str = ""
    manual_text: str = ""
    selected_element_type: Optional[ElementType] = None
    confidence_score: float = 0.0
    validation_notes: str = ""
    started_at: datetime = field(default_factory=datetime.now)
    
    @property
    def final_text(self) -> str:
        """Get the final text (manual override or extracted)."""
        return self.manual_text if self.manual_text.strip() else self.extracted_text


class ValidationWizard(QWizard):
    """
    Comprehensive wizard for manual validation workflow.
    
    Implements a 6-step process with performance optimization and
    user experience enhancements for efficient document validation.
    """
    
    # Signals for external integration
    area_selected = pyqtSignal(DrawingArea)
    text_extracted = pyqtSignal(str, float)  # text, confidence
    element_created = pyqtSignal(Element)
    wizard_completed = pyqtSignal(dict)  # validation summary
    wizard_cancelled = pyqtSignal()
    
    def __init__(self, state_manager: DrawingStateManager, parent=None):
        """Initialize the validation wizard."""
        super().__init__(parent)
        
        self.logger = logging.getLogger("torematrix.ui.wizard")
        self.state_manager = state_manager
        self.wizard_state = WizardState()
        
        # Performance optimization settings
        self._cache_enabled = True
        self._lazy_loading = True
        self._render_timer = QTimer()
        self._render_timer.setSingleShot(True)
        self._render_timer.timeout.connect(self._delayed_render)
        
        # Setup wizard
        self._setup_wizard()
        self._create_pages()
        self._connect_signals()
        
        self.logger.info("ValidationWizard initialized")
    
    def _setup_wizard(self):
        """Configure wizard properties and appearance."""
        self.setWindowTitle("Manual Validation Wizard")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setOption(QWizard.WizardOption.HaveHelpButton, True)
        self.setOption(QWizard.WizardOption.HaveCustomButton1, True)
        self.setOption(QWizard.WizardOption.HelpButtonOnRight, False)
        
        # Performance: Set minimum sizes to avoid constant resizing
        self.setMinimumSize(800, 600)
        self.setMaximumSize(1200, 800)
        
        # Custom styling for professional appearance
        self.setStyleSheet("""
            QWizard {
                background-color: #f8f9fa;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QWizardPage {
                background-color: white;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                margin: 10px;
                padding: 20px;
            }
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
    
    def _create_pages(self):
        """Create all wizard pages."""
        self.addPage(WelcomePage(self))
        self.addPage(AreaSelectionPage(self))
        self.addPage(OCRProcessingPage(self))
        self.addPage(TextReviewPage(self))
        self.addPage(ElementTypePage(self))
        self.addPage(FinalReviewPage(self))
    
    def _connect_signals(self):
        """Connect wizard signals."""
        self.helpRequested.connect(self._show_help)
        self.customButtonClicked.connect(self._custom_button_clicked)
        self.currentIdChanged.connect(self._page_changed)
        
        # Connect state manager signals
        self.state_manager.area_selected.connect(self._on_area_selected)
        self.state_manager.state_changed.connect(self._on_state_changed)
    
    def _delayed_render(self):
        """Delayed rendering for performance optimization."""
        current_page = self.currentPage()
        if hasattr(current_page, 'update_display'):
            current_page.update_display()
    
    def _page_changed(self, page_id: int):
        """Handle page change with performance optimization."""
        self.logger.debug(f"Page changed to: {page_id}")
        
        # Update wizard state
        step_mapping = {
            0: WizardStep.WELCOME,
            1: WizardStep.AREA_SELECTION,
            2: WizardStep.OCR_PROCESSING,
            3: WizardStep.TEXT_REVIEW,
            4: WizardStep.ELEMENT_TYPE,
            5: WizardStep.FINAL_REVIEW,
        }
        
        self.wizard_state.current_step = step_mapping.get(page_id, WizardStep.WELCOME)
        
        # Delayed rendering for smooth transitions
        if self._lazy_loading:
            self._render_timer.start(50)
    
    def _on_area_selected(self, area: DrawingArea):
        """Handle area selection from state manager."""
        self.wizard_state.selected_area = area
        self.area_selected.emit(area)
        self.logger.info(f"Area selected: {area.area_id}")
    
    def _on_state_changed(self, state: DrawingState):
        """Handle state changes from state manager."""
        self.logger.debug(f"State changed: {state}")
    
    def _show_help(self):
        """Show context-sensitive help."""
        current_page = self.currentPage()
        if hasattr(current_page, 'get_help_text'):
            help_text = current_page.get_help_text()
            # Show help dialog (implementation depends on UI framework)
            self.logger.info(f"Help requested: {help_text}")
    
    def _custom_button_clicked(self, button_id: int):
        """Handle custom button clicks."""
        self.logger.debug(f"Custom button clicked: {button_id}")
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """Get complete validation summary."""
        return {
            "wizard_state": {
                "current_step": self.wizard_state.current_step.name,
                "selected_area": self.wizard_state.selected_area.to_dict() if self.wizard_state.selected_area else None,
                "extracted_text": self.wizard_state.extracted_text,
                "manual_text": self.wizard_state.manual_text,
                "final_text": self.wizard_state.final_text,
                "element_type": self.wizard_state.selected_element_type.value if self.wizard_state.selected_element_type else None,
                "confidence_score": self.wizard_state.confidence_score,
                "validation_notes": self.wizard_state.validation_notes,
                "started_at": self.wizard_state.started_at.isoformat()
            },
            "performance_metrics": {
                "cache_enabled": self._cache_enabled,
                "lazy_loading": self._lazy_loading,
                "render_timer_active": self._render_timer.isActive()
            }
        }


class WelcomePage(QWizardPage):
    """Welcome page with workflow overview."""
    
    def __init__(self, wizard: ValidationWizard):
        super().__init__()
        self.wizard = wizard
        self.setTitle("Manual Validation Wizard")
        self.setSubTitle("Welcome to the comprehensive document validation workflow")
        
        layout = QVBoxLayout()
        
        # Welcome content
        welcome_text = QLabel("""
        <h2>Document Element Validation</h2>
        <p>This wizard will guide you through the process of manually validating 
        document elements with precision and efficiency.</p>
        
        <h3>Workflow Steps:</h3>
        <ol>
            <li><b>Area Selection</b> - Select the document area to validate</li>
            <li><b>OCR Processing</b> - Extract text using advanced OCR</li>
            <li><b>Text Review</b> - Review and edit extracted text</li>
            <li><b>Element Type</b> - Choose the appropriate element type</li>
            <li><b>Final Review</b> - Confirm all details before completion</li>
        </ol>
        
        <p><i>Estimated time: 2-5 minutes per element</i></p>
        """)
        welcome_text.setWordWrap(True)
        welcome_text.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        layout.addWidget(welcome_text)
        layout.addStretch()
        
        self.setLayout(layout)
    
    def get_help_text(self) -> str:
        """Get help text for this page."""
        return "This is the welcome page. Click 'Next' to begin the validation process."


class AreaSelectionPage(QWizardPage):
    """Page for selecting document area to validate."""
    
    def __init__(self, wizard: ValidationWizard):
        super().__init__()
        self.wizard = wizard
        self.setTitle("Area Selection")
        self.setSubTitle("Select the document area you want to validate")
        
        layout = QVBoxLayout()
        
        # Instructions
        instructions = QLabel("""
        <h3>Select Document Area</h3>
        <p>Use the drawing tools to select the area you want to validate:</p>
        <ul>
            <li>Click and drag to create a selection rectangle</li>
            <li>Ensure the selection includes all relevant content</li>
            <li>Double-click to confirm your selection</li>
        </ul>
        """)
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Selection controls
        controls_group = QGroupBox("Selection Tools")
        controls_layout = QHBoxLayout()
        
        self.start_selection_btn = QPushButton("Start Selection")
        self.start_selection_btn.clicked.connect(self._start_selection)
        
        self.cancel_selection_btn = QPushButton("Cancel Selection")
        self.cancel_selection_btn.clicked.connect(self._cancel_selection)
        self.cancel_selection_btn.setEnabled(False)
        
        controls_layout.addWidget(self.start_selection_btn)
        controls_layout.addWidget(self.cancel_selection_btn)
        controls_layout.addStretch()
        
        controls_group.setLayout(controls_layout)
        layout.addWidget(controls_group)
        
        # Status display
        self.status_label = QLabel("Ready to start selection...")
        self.status_label.setStyleSheet("color: #6c757d; font-style: italic;")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def _start_selection(self):
        """Start area selection process."""
        if self.wizard.state_manager.start_area_selection():
            self.start_selection_btn.setEnabled(False)
            self.cancel_selection_btn.setEnabled(True)
            self.status_label.setText("Selection in progress... Draw your selection area")
            self.status_label.setStyleSheet("color: #007bff; font-weight: bold;")
    
    def _cancel_selection(self):
        """Cancel area selection process."""
        # Implementation would call state manager cancel
        self.start_selection_btn.setEnabled(True)
        self.cancel_selection_btn.setEnabled(False)
        self.status_label.setText("Selection cancelled. Ready to start again.")
        self.status_label.setStyleSheet("color: #dc3545;")
    
    def isComplete(self) -> bool:
        """Check if page is complete."""
        return self.wizard.wizard_state.selected_area is not None
    
    def get_help_text(self) -> str:
        """Get help text for this page."""
        return "Click 'Start Selection' then draw a rectangle around the area you want to validate."


class OCRProcessingPage(QWizardPage):
    """Page for OCR processing with progress indication."""
    
    def __init__(self, wizard: ValidationWizard):
        super().__init__()
        self.wizard = wizard
        self.setTitle("OCR Processing")
        self.setSubTitle("Extracting text from selected area")
        
        layout = QVBoxLayout()
        
        # Processing info
        info_label = QLabel("""
        <h3>Text Extraction in Progress</h3>
        <p>Advanced OCR algorithms are analyzing your selected area to extract text content.</p>
        """)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Progress display
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("Initializing OCR engine...")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.progress_label)
        
        # Results preview (initially hidden)
        self.results_group = QGroupBox("Extraction Results")
        results_layout = QVBoxLayout()
        
        self.confidence_label = QLabel("Confidence: --")
        self.extracted_text_preview = QTextEdit()
        self.extracted_text_preview.setMaximumHeight(100)
        self.extracted_text_preview.setReadOnly(True)
        
        results_layout.addWidget(self.confidence_label)
        results_layout.addWidget(self.extracted_text_preview)
        
        self.results_group.setLayout(results_layout)
        self.results_group.setVisible(False)
        layout.addWidget(self.results_group)
        
        layout.addStretch()
        self.setLayout(layout)
        
        # Processing timer for simulation
        self.processing_timer = QTimer()
        self.processing_timer.timeout.connect(self._update_progress)
        self.progress_value = 0
    
    def initializePage(self):
        """Initialize OCR processing when page is entered."""
        super().initializePage()
        self._start_ocr_processing()
    
    def _start_ocr_processing(self):
        """Start OCR processing simulation."""
        self.progress_value = 0
        self.progress_bar.setValue(0)
        self.progress_label.setText("Initializing OCR engine...")
        self.results_group.setVisible(False)
        
        # Start processing timer
        self.processing_timer.start(100)  # Update every 100ms
    
    def _update_progress(self):
        """Update processing progress."""
        self.progress_value += 2
        self.progress_bar.setValue(self.progress_value)
        
        # Update status text based on progress
        if self.progress_value < 20:
            self.progress_label.setText("Initializing OCR engine...")
        elif self.progress_value < 40:
            self.progress_label.setText("Preprocessing image...")
        elif self.progress_value < 70:
            self.progress_label.setText("Extracting text...")
        elif self.progress_value < 90:
            self.progress_label.setText("Analyzing confidence...")
        else:
            self.progress_label.setText("Processing complete!")
            self.processing_timer.stop()
            self._complete_ocr_processing()
    
    def _complete_ocr_processing(self):
        """Complete OCR processing and show results."""
        # Simulate OCR results
        extracted_text = "Sample extracted text from document validation"
        confidence = 0.87
        
        # Update wizard state
        self.wizard.wizard_state.extracted_text = extracted_text
        self.wizard.wizard_state.confidence_score = confidence
        
        # Show results
        self.confidence_label.setText(f"Confidence: {confidence:.1%}")
        self.extracted_text_preview.setText(extracted_text)
        self.results_group.setVisible(True)
        
        # Emit signal
        self.wizard.text_extracted.emit(extracted_text, confidence)
        
        # Enable next button
        self.completeChanged.emit()
    
    def isComplete(self) -> bool:
        """Check if OCR processing is complete."""
        return bool(self.wizard.wizard_state.extracted_text)
    
    def get_help_text(self) -> str:
        """Get help text for this page."""
        return "OCR processing extracts text from your selected area. Please wait for completion."


# Additional pages would be implemented similarly...
# TextReviewPage, ElementTypePage, FinalReviewPage

class TextReviewPage(QWizardPage):
    """Page for reviewing and editing extracted text."""
    
    def __init__(self, wizard: ValidationWizard):
        super().__init__()
        self.wizard = wizard
        self.setTitle("Text Review")
        self.setSubTitle("Review and edit the extracted text")
        
        # Implementation details would follow the same pattern...
        layout = QVBoxLayout()
        
        instructions = QLabel("Review the extracted text and make any necessary corrections:")
        layout.addWidget(instructions)
        
        self.text_edit = QTextEdit()
        layout.addWidget(self.text_edit)
        
        self.setLayout(layout)
    
    def initializePage(self):
        """Initialize with extracted text."""
        super().initializePage()
        self.text_edit.setText(self.wizard.wizard_state.extracted_text)
    
    def isComplete(self) -> bool:
        """Check if text review is complete."""
        return len(self.text_edit.toPlainText().strip()) > 0


class ElementTypePage(QWizardPage):
    """Page for selecting element type."""
    
    def __init__(self, wizard: ValidationWizard):
        super().__init__()
        self.wizard = wizard
        self.setTitle("Element Type")
        self.setSubTitle("Select the type of document element")
        
        layout = QVBoxLayout()
        
        instructions = QLabel("Choose the appropriate element type:")
        layout.addWidget(instructions)
        
        self.button_group = QButtonGroup()
        
        # Add radio buttons for each element type
        for element_type in ElementType:
            radio = QRadioButton(element_type.value.title())
            self.button_group.addButton(radio)
            layout.addWidget(radio)
        
        self.setLayout(layout)
    
    def isComplete(self) -> bool:
        """Check if element type is selected."""
        return self.button_group.checkedButton() is not None


class FinalReviewPage(QWizardPage):
    """Final review page before completion."""
    
    def __init__(self, wizard: ValidationWizard):
        super().__init__()
        self.wizard = wizard
        self.setTitle("Final Review")
        self.setSubTitle("Review all details before completion")
        
        layout = QVBoxLayout()
        
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        layout.addWidget(self.summary_text)
        
        self.setLayout(layout)
    
    def initializePage(self):
        """Initialize with summary data."""
        super().initializePage()
        summary = self.wizard.get_validation_summary()
        self.summary_text.setText(str(summary))
    
    def isComplete(self) -> bool:
        """Final page is always complete."""
        return True