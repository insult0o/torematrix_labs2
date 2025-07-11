#!/usr/bin/env python3
"""
Validation Service for TORE Matrix Labs V2

This service provides comprehensive document validation functionality,
consolidating validation logic from the original codebase into a clean,
testable service with proper error handling and state management.

Key improvements:
- Unified validation interface
- Page-by-page validation workflow
- Issue detection and tracking
- Quality assessment integration
- State management and persistence
- Performance optimization

This consolidates functionality from:
- page_validation_widget.py
- qa_validation_widget.py
- manual_validation_widget.py
"""

import logging
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

from ..models.unified_document_model import UnifiedDocument
from .coordinate_mapping_service import CoordinateMappingService, Coordinates, TextPosition
from .text_extraction_service import TextExtractionService, ExtractionResult


class ValidationStatus(Enum):
    """Status of validation."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    APPROVED = "approved"
    REJECTED = "rejected"
    REQUIRES_REVIEW = "requires_review"


class IssueSeverity(Enum):
    """Severity levels for validation issues."""
    CRITICAL = "critical"
    MAJOR = "major"
    MEDIUM = "medium"
    MINOR = "minor"
    INFO = "info"


class IssueType(Enum):
    """Types of validation issues."""
    OCR_ERROR = "ocr_error"
    FORMATTING_ERROR = "formatting_error"
    TABLE_ERROR = "table_error"
    IMAGE_ERROR = "image_error"
    ENCODING_ERROR = "encoding_error"
    STRUCTURE_ERROR = "structure_error"
    CONTENT_ERROR = "content_error"
    COORDINATE_ERROR = "coordinate_error"


@dataclass
class ValidationIssue:
    """Represents a validation issue."""
    
    # Identity
    issue_id: str
    issue_type: IssueType
    severity: IssueSeverity
    
    # Location
    page: int
    coordinates: Optional[Coordinates] = None
    text_position: Optional[TextPosition] = None
    
    # Issue details
    title: str = ""
    description: str = ""
    suggested_fix: str = ""
    
    # Content
    original_text: str = ""
    corrected_text: str = ""
    context_text: str = ""
    
    # Status
    status: ValidationStatus = ValidationStatus.NOT_STARTED
    resolution_notes: str = ""
    
    # Metadata
    detected_by: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    
    # Additional data
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationSession:
    """Represents a validation session."""
    
    # Identity
    session_id: str
    document_id: str
    validator_id: str
    
    # Session state
    status: ValidationStatus = ValidationStatus.NOT_STARTED
    current_page: int = 1
    current_issue_index: int = 0
    
    # Issues
    issues: List[ValidationIssue] = field(default_factory=list)
    resolved_issues: List[ValidationIssue] = field(default_factory=list)
    
    # Progress
    pages_validated: List[int] = field(default_factory=list)
    total_pages: int = 0
    
    # Session metadata
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    # Configuration
    validation_mode: str = "page_by_page"  # page_by_page, issue_by_issue
    auto_approve_threshold: float = 0.9
    require_manual_review: bool = True
    
    # Statistics
    stats: Dict[str, Any] = field(default_factory=dict)


class ValidationService:
    """
    Comprehensive validation service for document processing.
    
    This service manages the complete validation workflow, from issue detection
    to resolution tracking, with support for multiple validation modes.
    """
    
    def __init__(self,
                 coordinate_service: CoordinateMappingService,
                 extraction_service: TextExtractionService):
        """Initialize the validation service."""
        self.logger = logging.getLogger(__name__)
        
        # Core services
        self.coordinate_service = coordinate_service
        self.extraction_service = extraction_service
        
        # Active validation sessions
        self.active_sessions: Dict[str, ValidationSession] = {}
        self.session_history: List[ValidationSession] = []
        
        # Issue detection rules
        self.detection_rules: Dict[IssueType, Dict[str, Any]] = {}
        self._initialize_detection_rules()
        
        # Performance statistics
        self.stats = {
            "sessions_created": 0,
            "sessions_completed": 0,
            "issues_detected": 0,
            "issues_resolved": 0,
            "average_session_time": 0.0
        }
        
        self.logger.info("Validation service initialized")
    
    def create_validation_session(self,
                                 document: UnifiedDocument,
                                 validator_id: str,
                                 validation_mode: str = "page_by_page") -> str:
        """
        Create a new validation session.
        
        Args:
            document: Document to validate
            validator_id: ID of the validator
            validation_mode: Validation mode (page_by_page, issue_by_issue)
            
        Returns:
            Session ID
        """
        try:
            session_id = f"session_{document.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Create session
            session = ValidationSession(
                session_id=session_id,
                document_id=document.id,
                validator_id=validator_id,
                validation_mode=validation_mode,
                total_pages=document.metadata.page_count or 1
            )
            
            # Detect issues in the document
            self._detect_issues(document, session)
            
            # Register session
            self.active_sessions[session_id] = session
            self.stats["sessions_created"] += 1
            
            self.logger.info(f"Validation session created: {session_id} with {len(session.issues)} issues")
            return session_id
            
        except Exception as e:
            self.logger.error(f"Failed to create validation session: {str(e)}")
            raise
    
    def get_validation_session(self, session_id: str) -> Optional[ValidationSession]:
        """Get a validation session by ID."""
        return self.active_sessions.get(session_id)
    
    def get_page_issues(self, session_id: str, page: int) -> List[ValidationIssue]:
        """Get all issues for a specific page."""
        session = self.active_sessions.get(session_id)
        if not session:
            return []
        
        return [issue for issue in session.issues if issue.page == page]
    
    def get_current_issue(self, session_id: str) -> Optional[ValidationIssue]:
        """Get the current issue being validated."""
        session = self.active_sessions.get(session_id)
        if not session or not session.issues:
            return None
        
        if session.current_issue_index < len(session.issues):
            return session.issues[session.current_issue_index]
        
        return None
    
    def navigate_to_page(self, session_id: str, page: int) -> bool:
        """
        Navigate to a specific page in validation.
        
        Args:
            session_id: Validation session ID
            page: Page number to navigate to
            
        Returns:
            True if navigation successful
        """
        session = self.active_sessions.get(session_id)
        if not session:
            return False
        
        if 1 <= page <= session.total_pages:
            session.current_page = page
            
            # Find first issue on this page
            page_issues = self.get_page_issues(session_id, page)
            if page_issues:
                # Find index of first issue on this page
                for i, issue in enumerate(session.issues):
                    if issue.page == page:
                        session.current_issue_index = i
                        break
            
            self.logger.debug(f"Navigated to page {page} in session {session_id}")
            return True
        
        return False
    
    def navigate_to_issue(self, session_id: str, issue_index: int) -> bool:
        """
        Navigate to a specific issue.
        
        Args:
            session_id: Validation session ID
            issue_index: Index of issue to navigate to
            
        Returns:
            True if navigation successful
        """
        session = self.active_sessions.get(session_id)
        if not session:
            return False
        
        if 0 <= issue_index < len(session.issues):
            session.current_issue_index = issue_index
            
            # Update current page to match issue page
            issue = session.issues[issue_index]
            session.current_page = issue.page
            
            self.logger.debug(f"Navigated to issue {issue_index} in session {session_id}")
            return True
        
        return False
    
    def approve_issue(self, session_id: str, issue_id: str, notes: str = "") -> bool:
        """
        Approve an issue (mark as correctly detected and resolved).
        
        Args:
            session_id: Validation session ID
            issue_id: Issue ID to approve
            notes: Optional resolution notes
            
        Returns:
            True if approval successful
        """
        return self._resolve_issue(session_id, issue_id, ValidationStatus.APPROVED, notes)
    
    def reject_issue(self, session_id: str, issue_id: str, notes: str = "") -> bool:
        """
        Reject an issue (mark as incorrectly detected).
        
        Args:
            session_id: Validation session ID
            issue_id: Issue ID to reject
            notes: Optional resolution notes
            
        Returns:
            True if rejection successful
        """
        return self._resolve_issue(session_id, issue_id, ValidationStatus.REJECTED, notes)
    
    def correct_issue(self, 
                     session_id: str, 
                     issue_id: str, 
                     corrected_text: str,
                     notes: str = "") -> bool:
        """
        Provide a correction for an issue.
        
        Args:
            session_id: Validation session ID
            issue_id: Issue ID to correct
            corrected_text: Corrected text
            notes: Optional resolution notes
            
        Returns:
            True if correction successful
        """
        session = self.active_sessions.get(session_id)
        if not session:
            return False
        
        # Find the issue
        issue = None
        for i in session.issues:
            if i.issue_id == issue_id:
                issue = i
                break
        
        if not issue:
            return False
        
        try:
            # Update issue with correction
            issue.corrected_text = corrected_text
            issue.status = ValidationStatus.COMPLETED
            issue.resolution_notes = notes
            issue.resolved_at = datetime.now()
            issue.resolved_by = session.validator_id
            
            # Move to resolved issues
            session.issues.remove(issue)
            session.resolved_issues.append(issue)
            
            self.stats["issues_resolved"] += 1
            
            self.logger.info(f"Issue corrected: {issue_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to correct issue {issue_id}: {str(e)}")
            return False
    
    def complete_page_validation(self, session_id: str, page: int) -> bool:
        """
        Mark a page as validated.
        
        Args:
            session_id: Validation session ID
            page: Page number to mark as validated
            
        Returns:
            True if marking successful
        """
        session = self.active_sessions.get(session_id)
        if not session:
            return False
        
        if page not in session.pages_validated:
            session.pages_validated.append(page)
            
            # Check if all issues on this page are resolved
            page_issues = self.get_page_issues(session_id, page)
            unresolved = [i for i in page_issues if i.status in [ValidationStatus.NOT_STARTED, ValidationStatus.IN_PROGRESS]]
            
            if unresolved:
                self.logger.warning(f"Page {page} marked as validated but has {len(unresolved)} unresolved issues")
            
            self.logger.info(f"Page {page} validation completed in session {session_id}")
            return True
        
        return False
    
    def complete_validation_session(self, session_id: str) -> bool:
        """
        Complete a validation session.
        
        Args:
            session_id: Validation session ID
            
        Returns:
            True if completion successful
        """
        session = self.active_sessions.get(session_id)
        if not session:
            return False
        
        try:
            # Update session status
            session.status = ValidationStatus.COMPLETED
            session.completed_at = datetime.now()
            
            # Calculate statistics
            session_time = (session.completed_at - session.started_at).total_seconds()
            session.stats = {
                "session_duration": session_time,
                "total_issues": len(session.issues) + len(session.resolved_issues),
                "resolved_issues": len(session.resolved_issues),
                "pages_validated": len(session.pages_validated),
                "resolution_rate": len(session.resolved_issues) / (len(session.issues) + len(session.resolved_issues)) if (len(session.issues) + len(session.resolved_issues)) > 0 else 0.0
            }
            
            # Move to history
            self.session_history.append(session)
            del self.active_sessions[session_id]
            
            # Update global statistics
            self.stats["sessions_completed"] += 1
            total_sessions = self.stats["sessions_completed"]
            current_avg = self.stats["average_session_time"]
            self.stats["average_session_time"] = ((current_avg * (total_sessions - 1)) + session_time) / total_sessions
            
            self.logger.info(f"Validation session completed: {session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to complete validation session {session_id}: {str(e)}")
            return False
    
    def _detect_issues(self, document: UnifiedDocument, session: ValidationSession):
        """Detect validation issues in a document."""
        try:
            self.logger.info(f"Detecting issues in document: {document.id}")
            
            # Extract text for analysis
            extraction_result = self.extraction_service.extract_text(
                document, include_coordinates=True, include_content_analysis=True
            )
            
            # Detect different types of issues
            self._detect_ocr_issues(document, extraction_result, session)
            self._detect_formatting_issues(document, extraction_result, session)
            self._detect_table_issues(document, extraction_result, session)
            self._detect_structure_issues(document, extraction_result, session)
            
            # Sort issues by page and position
            session.issues.sort(key=lambda x: (x.page, x.text_position.character_index if x.text_position else 0))
            
            self.stats["issues_detected"] += len(session.issues)
            
            self.logger.info(f"Detected {len(session.issues)} issues in document {document.id}")
            
        except Exception as e:
            self.logger.error(f"Issue detection failed: {str(e)}")
    
    def _detect_ocr_issues(self, 
                          document: UnifiedDocument,
                          extraction_result: ExtractionResult,
                          session: ValidationSession):
        """Detect OCR-related issues."""
        
        for page_data in extraction_result.pages:
            page_num = page_data["page"]
            page_text = page_data["text"]
            coordinates = page_data.get("coordinates", {})
            
            # Look for OCR error patterns
            issues = []
            
            # Pattern 1: Unusual character sequences
            import re
            unusual_patterns = [
                r'[^\w\s.,!?;:()"\'"-]{3,}',  # 3+ consecutive special chars
                r'\w{20,}',  # Very long words (likely OCR errors)
                r'[A-Za-z][0-9][A-Za-z][0-9]',  # Alternating letter-number
            ]
            
            for pattern in unusual_patterns:
                matches = re.finditer(pattern, page_text)
                for match in matches:
                    start_pos = match.start()
                    
                    # Get coordinates for this position
                    coords = None
                    if str(start_pos) in coordinates:
                        coord_data = coordinates[str(start_pos)]
                        coords = Coordinates(
                            x=coord_data["bbox"][0],
                            y=coord_data["bbox"][1],
                            width=coord_data["bbox"][2] - coord_data["bbox"][0],
                            height=coord_data["bbox"][3] - coord_data["bbox"][1],
                            page=page_num
                        )
                    
                    issue = ValidationIssue(
                        issue_id=f"ocr_{page_num}_{start_pos}",
                        issue_type=IssueType.OCR_ERROR,
                        severity=IssueSeverity.MEDIUM,
                        page=page_num,
                        coordinates=coords,
                        text_position=TextPosition(start_pos, page=page_num),
                        title="Potential OCR Error",
                        description=f"Unusual character sequence detected: '{match.group()}'",
                        original_text=match.group(),
                        context_text=page_text[max(0, start_pos-20):start_pos+len(match.group())+20],
                        detected_by="ocr_pattern_detector"
                    )
                    
                    session.issues.append(issue)
    
    def _detect_formatting_issues(self,
                                 document: UnifiedDocument,
                                 extraction_result: ExtractionResult,
                                 session: ValidationSession):
        """Detect formatting-related issues."""
        
        for page_data in extraction_result.pages:
            page_num = page_data["page"]
            page_text = page_data["text"]
            
            # Look for formatting issues
            lines = page_text.split('\n')
            
            for line_num, line in enumerate(lines):
                # Check for inconsistent spacing
                if '  ' in line and len(line.strip()) > 10:  # Multiple spaces in substantial lines
                    issue = ValidationIssue(
                        issue_id=f"format_{page_num}_{line_num}",
                        issue_type=IssueType.FORMATTING_ERROR,
                        severity=IssueSeverity.MINOR,
                        page=page_num,
                        title="Inconsistent Spacing",
                        description="Multiple spaces detected in text line",
                        original_text=line.strip(),
                        detected_by="formatting_detector"
                    )
                    
                    session.issues.append(issue)
    
    def _detect_table_issues(self,
                            document: UnifiedDocument,
                            extraction_result: ExtractionResult,
                            session: ValidationSession):
        """Detect table-related issues."""
        
        for table in extraction_result.tables:
            page_num = table["page"]
            
            # Check table detection confidence
            if table.get("confidence", 1.0) < 0.8:
                issue = ValidationIssue(
                    issue_id=f"table_{page_num}_{table.get('index', 0)}",
                    issue_type=IssueType.TABLE_ERROR,
                    severity=IssueSeverity.MAJOR,
                    page=page_num,
                    title="Low Confidence Table Detection",
                    description=f"Table detected with low confidence: {table.get('confidence', 0):.2f}",
                    detected_by="table_detector"
                )
                
                session.issues.append(issue)
    
    def _detect_structure_issues(self,
                               document: UnifiedDocument,
                               extraction_result: ExtractionResult,
                               session: ValidationSession):
        """Detect document structure issues."""
        
        # Check for missing pages or very short pages
        for page_data in extraction_result.pages:
            page_num = page_data["page"]
            page_text = page_data["text"]
            
            if len(page_text.strip()) < 50:  # Very short page content
                issue = ValidationIssue(
                    issue_id=f"structure_{page_num}",
                    issue_type=IssueType.STRUCTURE_ERROR,
                    severity=IssueSeverity.MAJOR,
                    page=page_num,
                    title="Minimal Page Content",
                    description=f"Page contains very little text: {len(page_text)} characters",
                    original_text=page_text[:100],
                    detected_by="structure_detector"
                )
                
                session.issues.append(issue)
    
    def _resolve_issue(self, 
                      session_id: str, 
                      issue_id: str, 
                      status: ValidationStatus,
                      notes: str) -> bool:
        """Resolve an issue with given status."""
        session = self.active_sessions.get(session_id)
        if not session:
            return False
        
        # Find the issue
        issue = None
        for i in session.issues:
            if i.issue_id == issue_id:
                issue = i
                break
        
        if not issue:
            return False
        
        try:
            # Update issue
            issue.status = status
            issue.resolution_notes = notes
            issue.resolved_at = datetime.now()
            issue.resolved_by = session.validator_id
            
            # Move to resolved issues
            session.issues.remove(issue)
            session.resolved_issues.append(issue)
            
            self.stats["issues_resolved"] += 1
            
            self.logger.debug(f"Issue {issue_id} resolved with status {status.value}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to resolve issue {issue_id}: {str(e)}")
            return False
    
    def _initialize_detection_rules(self):
        """Initialize issue detection rules."""
        self.detection_rules = {
            IssueType.OCR_ERROR: {
                "patterns": [
                    r'[^\w\s.,!?;:()"\'"-]{3,}',
                    r'\w{20,}',
                    r'[A-Za-z][0-9][A-Za-z][0-9]'
                ],
                "confidence_threshold": 0.7
            },
            IssueType.FORMATTING_ERROR: {
                "patterns": [r'  +'],  # Multiple spaces
                "confidence_threshold": 0.8
            },
            IssueType.TABLE_ERROR: {
                "confidence_threshold": 0.8
            },
            IssueType.STRUCTURE_ERROR: {
                "min_page_length": 50
            }
        }
    
    def get_session_statistics(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a validation session."""
        session = self.active_sessions.get(session_id)
        if not session:
            # Check history
            for hist_session in self.session_history:
                if hist_session.session_id == session_id:
                    session = hist_session
                    break
        
        if not session:
            return None
        
        total_issues = len(session.issues) + len(session.resolved_issues)
        progress = len(session.pages_validated) / session.total_pages if session.total_pages > 0 else 0.0
        
        return {
            "session_id": session_id,
            "status": session.status.value,
            "total_issues": total_issues,
            "resolved_issues": len(session.resolved_issues),
            "pending_issues": len(session.issues),
            "pages_validated": len(session.pages_validated),
            "total_pages": session.total_pages,
            "progress": progress,
            "current_page": session.current_page,
            "current_issue_index": session.current_issue_index
        }
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get validation service performance statistics."""
        return {
            **self.stats,
            "active_sessions": len(self.active_sessions),
            "session_history_size": len(self.session_history)
        }