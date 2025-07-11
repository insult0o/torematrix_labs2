"""
Quality assurance validation widget with content validation and correction interface.
"""

import logging
from typing import Optional, Dict, Any

from ..qt_compat import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, pyqtSignal, QMessageBox
from ...config.settings import Settings
from ...models.document_models import Document
from .validation_widget import ValidationWidget


class QAValidationWidget(QWidget):
    """Enhanced QA validation widget with content validation and correction capabilities."""
    
    validation_completed = pyqtSignal(str, bool)
    status_message = pyqtSignal(str)
    highlight_pdf_location = pyqtSignal(int, object, str)  # Forward signal for PDF highlighting with search text
    
    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # Current state
        self.current_document: Optional[Document] = None
        self.post_processing_result = None
        self.manual_validation_result = None
        
        self._init_ui()
        self.logger.info("QA validation widget initialized")
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Quality Assurance & Content Validation")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Quick actions
        self.quick_validate_btn = QPushButton("Quick Validate")
        self.quick_validate_btn.clicked.connect(self._quick_validate)
        self.quick_validate_btn.setStyleSheet("background-color: #3498db; color: white; padding: 8px;")
        header_layout.addWidget(self.quick_validate_btn)
        
        self.export_report_btn = QPushButton("Export Report")
        self.export_report_btn.clicked.connect(self._export_validation_report)
        header_layout.addWidget(self.export_report_btn)
        
        layout.addLayout(header_layout)
        
        # Status bar
        self.status_label = QLabel("Ready for quality validation")
        self.status_label.setStyleSheet("background-color: #ecf0f1; padding: 8px; border-radius: 4px;")
        layout.addWidget(self.status_label)
        
        # Main validation interface
        self.validation_widget = ValidationWidget(self.settings)
        
        # Connect PDF highlighting signal
        self.validation_widget.highlight_pdf_location.connect(self.highlight_pdf_location.emit)
        
        layout.addWidget(self.validation_widget)
        
        self.setLayout(layout)
    
    def load_document_for_validation(self, document: Document, post_processing_result=None):
        """Load a document for quality validation."""
        self.current_document = document
        self.post_processing_result = post_processing_result
        
        # Check if manual validation was already completed
        self._check_manual_validation_state()
        
        # Load into validation widget
        self.validation_widget.load_document(document, post_processing_result)
        
        # Update status
        if post_processing_result:
            validation_session = getattr(post_processing_result, 'validation_session', None)
            if validation_session:
                corrections_count = validation_session.corrections_applied + validation_session.corrections_rejected
                self.status_label.setText(
                    f"Document loaded: {corrections_count} corrections available for review"
                )
            else:
                self.status_label.setText("Document loaded: Ready for validation")
        else:
            self.status_label.setText("Document loaded: No post-processing data available")
        
        self.status_message.emit(f"Document {document.metadata.file_name} loaded for validation")
        self.logger.info(f"Document loaded for validation: {document.id}")
    
    def _check_manual_validation_state(self):
        """Check if manual validation was already completed for this document."""
        try:
            if not self.current_document:
                return
            
            # Get main window to access document state manager
            main_window = self.parent()
            while main_window and not hasattr(main_window, 'document_state_manager'):
                main_window = main_window.parent()
            
            if not main_window:
                self.logger.warning("QA_VALIDATION_STATE: Cannot find main window")
                return
            
            # Check if validation result exists
            validation_result = main_window.document_state_manager.get_validation_result(self.current_document.id)
            
            if validation_result:
                self.logger.info(f"QA_VALIDATION_STATE: Found existing validation result for {self.current_document.id}")
                self.logger.info(f"QA_VALIDATION_STATE: Manual validation completed at {validation_result.get('completed_at')}")
                
                # Update status to show manual validation was completed
                completed_at = validation_result.get('completed_at', 'unknown time')
                total_selections = validation_result.get('total_selections', 0)
                
                self.status_label.setText(
                    f"Manual validation completed at {completed_at[:19]} with {total_selections} selections"
                )
                
                # Store the validation result for use by the validation widget
                self.manual_validation_result = validation_result
                
            else:
                self.logger.info(f"QA_VALIDATION_STATE: No existing validation result found for {self.current_document.id}")
                self.manual_validation_result = None
                
        except Exception as e:
            self.logger.error(f"QA_VALIDATION_STATE: Error checking manual validation state: {e}")
            self.manual_validation_result = None
    
    def start_validation(self):
        """Start the validation process."""
        if not self.current_document:
            QMessageBox.warning(self, "No Document", "Please load a document first.")
            return
        
        try:
            self.status_label.setText("Starting validation process...")
            self.status_message.emit("Starting document validation...")
            
            # Start validation in the validation widget
            self.validation_widget._start_validation()
            
            self.status_label.setText("Validation in progress - review corrections below")
            self.logger.info("Validation process started")
            
        except Exception as e:
            error_msg = f"Validation failed: {str(e)}"
            self.status_label.setText("Validation failed")
            QMessageBox.critical(self, "Validation Error", error_msg)
            self.logger.error(error_msg)
    
    def _quick_validate(self):
        """Perform quick validation with minimal user interaction."""
        if not self.current_document:
            QMessageBox.warning(self, "No Document", "Please load a document first.")
            return
        
        try:
            # Auto-approve high confidence corrections
            corrections_data = self.current_document.custom_metadata.get('corrections', [])
            auto_approved = 0
            
            for correction in corrections_data:
                if correction.get('confidence', 0) >= 0.9 and correction.get('status') == 'suggested':
                    correction['status'] = 'approved'
                    auto_approved += 1
            
            self.validation_widget._update_statistics()
            
            # Emit completion signal
            success = auto_approved > 0
            self.validation_completed.emit(self.current_document.id, success)
            
            self.status_label.setText(f"Quick validation complete: {auto_approved} corrections auto-approved")
            self.status_message.emit(f"Quick validation completed for {self.current_document.metadata.file_name}")
            
            if success:
                QMessageBox.information(
                    self, 
                    "Quick Validation Complete",
                    f"Auto-approved {auto_approved} high-confidence corrections.\n"
                    "Review remaining corrections manually if needed."
                )
            else:
                QMessageBox.information(
                    self, 
                    "Quick Validation Complete",
                    "No high-confidence corrections found for auto-approval.\n"
                    "Manual review recommended."
                )
                
        except Exception as e:
            error_msg = f"Quick validation failed: {str(e)}"
            QMessageBox.critical(self, "Quick Validation Error", error_msg)
            self.logger.error(error_msg)
    
    def _export_validation_report(self):
        """Export validation report."""
        if not self.current_document:
            QMessageBox.warning(self, "No Document", "Please load a document first.")
            return
        
        try:
            # Get validation summary
            summary = self.validation_widget.get_validation_summary()
            
            # Generate report
            report_lines = [
                "TORE Matrix Labs - Validation Report",
                "=" * 40,
                f"Document: {self.current_document.metadata.file_name}",
                f"Document ID: {self.current_document.id}",
                f"Validation Date: {summary.get('validation_date', 'Not completed')}",
                "",
                "Correction Summary:",
                f"  Total Corrections: {summary.get('total_corrections', 0)}",
                f"  Approved: {summary.get('approved_corrections', 0)}",
                f"  Rejected: {summary.get('rejected_corrections', 0)}",
                f"  Pending: {summary.get('pending_corrections', 0)}",
                "",
                f"Validation Status: {'Complete' if summary.get('validation_complete', False) else 'In Progress'}",
                "",
                "Generated by TORE Matrix Labs Content Validation System"
            ]
            
            report_text = "\n".join(report_lines)
            
            # For now, show in message box (could be extended to save to file)
            QMessageBox.information(self, "Validation Report", report_text)
            
            self.status_message.emit("Validation report generated")
            
        except Exception as e:
            error_msg = f"Failed to generate report: {str(e)}"
            QMessageBox.critical(self, "Export Error", error_msg)
            self.logger.error(error_msg)
    
    def get_validation_status(self) -> Dict[str, Any]:
        """Get current validation status."""
        if not self.current_document:
            return {'status': 'no_document'}
        
        summary = self.validation_widget.get_validation_summary()
        
        return {
            'document_id': self.current_document.id,
            'document_name': self.current_document.metadata.file_name,
            'validation_summary': summary,
            'has_pending_corrections': summary.get('pending_corrections', 0) > 0,
            'validation_complete': summary.get('validation_complete', False)
        }
    
    def finalize_validation(self) -> bool:
        """Finalize the validation process."""
        if not self.current_document:
            return False
        
        try:
            # Finalize validation in validation widget
            self.validation_widget._finalize_validation()
            
            # Emit completion signal
            self.validation_completed.emit(self.current_document.id, True)
            
            self.status_label.setText("Validation finalized successfully")
            self.status_message.emit(f"Validation finalized for {self.current_document.metadata.file_name}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to finalize validation: {str(e)}")
            return False