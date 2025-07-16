"""
Validation Tools Integration Layer.

This module provides a unified interface for all validation components,
integrating drawing state management, OCR services, UI components, and workflow management.
"""

from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
from pathlib import Path
import asyncio
import time
from collections import defaultdict

from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QThread
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar
from PyQt6.QtGui import QPixmap

from .drawing_state import DrawingStateManager, DrawingAction
from .area_select import AreaSelectTool
from .shapes import ElementShape, ShapeType
from .ocr_service import ValidationOCRService, OCRRequest, OCRResponse
from .wizard import ValidationWizard
from .toolbar import ValidationToolbar  
from .ocr_dialog import OCRDialog


class ValidationMode(Enum):
    """Validation workflow modes."""
    MANUAL_SELECTION = "manual_selection"
    OCR_ASSISTED = "ocr_assisted" 
    HYBRID_WORKFLOW = "hybrid_workflow"
    BATCH_PROCESSING = "batch_processing"


class IntegrationStatus(Enum):
    """Integration status tracking."""
    IDLE = "idle"
    INITIALIZING = "initializing"
    PROCESSING = "processing"
    VALIDATING = "validating"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class ValidationSession:
    """Validation session tracking."""
    session_id: str
    document_path: Path
    mode: ValidationMode
    pages_total: int
    pages_completed: int = 0
    elements_detected: int = 0
    elements_validated: int = 0
    ocr_requests: int = 0
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    status: IntegrationStatus = IntegrationStatus.IDLE
    errors: List[str] = field(default_factory=list)
    
    @property
    def duration(self) -> float:
        """Get session duration in seconds."""
        end = self.end_time if self.end_time else time.time()
        return end - self.start_time
    
    @property
    def progress_percentage(self) -> float:
        """Get overall progress percentage."""
        if self.pages_total == 0:
            return 0.0
        return (self.pages_completed / self.pages_total) * 100


@dataclass 
class ValidationStatistics:
    """Validation performance statistics."""
    total_sessions: int = 0
    total_elements: int = 0
    total_ocr_requests: int = 0
    average_session_duration: float = 0.0
    success_rate: float = 100.0
    error_count: int = 0
    performance_metrics: Dict[str, float] = field(default_factory=dict)


class ValidationToolsIntegration(QObject):
    """
    Unified integration layer for all validation tools.
    
    Provides a single interface for:
    - Drawing state management
    - OCR service integration  
    - UI component coordination
    - Workflow management
    - Performance monitoring
    - Error handling
    """
    
    # Signals
    session_started = pyqtSignal(str)  # session_id
    session_completed = pyqtSignal(str, bool)  # session_id, success
    progress_updated = pyqtSignal(str, float)  # session_id, percentage
    element_validated = pyqtSignal(str, dict)  # session_id, element_data
    error_occurred = pyqtSignal(str, str)  # session_id, error_message
    status_changed = pyqtSignal(IntegrationStatus)
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        # Core components
        self.drawing_manager: Optional[DrawingStateManager] = None
        self.area_tool: Optional[AreaSelectTool] = None  
        self.ocr_service: Optional[ValidationOCRService] = None
        self.wizard: Optional[ValidationWizard] = None
        self.toolbar: Optional[ValidationToolbar] = None
        self.ocr_dialog: Optional[OCRDialog] = None
        
        # State management
        self.current_session: Optional[ValidationSession] = None
        self.sessions: Dict[str, ValidationSession] = {}
        self.statistics = ValidationStatistics()
        self.status = IntegrationStatus.IDLE
        
        # Configuration
        self.config = {
            'auto_ocr_threshold': 0.8,
            'batch_size': 10,
            'max_concurrent_ocr': 3,
            'session_timeout': 3600,  # 1 hour
            'performance_monitoring': True,
            'debug_mode': False
        }
        
        # Performance monitoring
        self.performance_timer = QTimer()
        self.performance_timer.timeout.connect(self._update_performance_metrics)
        self.performance_timer.start(1000)  # Update every second
        
        # Error handling
        self.logger = logging.getLogger(__name__)
        self._setup_error_handling()
    
    def initialize_components(self, 
                            drawing_manager: DrawingStateManager,
                            area_tool: AreaSelectTool,
                            ocr_service: ValidationOCRService,
                            wizard: ValidationWizard,
                            toolbar: ValidationToolbar,
                            ocr_dialog: OCRDialog) -> bool:
        """
        Initialize all validation components.
        
        Args:
            drawing_manager: Drawing state management
            area_tool: Area selection tool
            ocr_service: OCR processing service
            wizard: Validation workflow wizard
            toolbar: Validation toolbar
            ocr_dialog: OCR configuration dialog
            
        Returns:
            True if initialization successful
        """
        try:
            self.status = IntegrationStatus.INITIALIZING
            self.status_changed.emit(self.status)
            
            # Store component references
            self.drawing_manager = drawing_manager
            self.area_tool = area_tool
            self.ocr_service = ocr_service
            self.wizard = wizard
            self.toolbar = toolbar
            self.ocr_dialog = ocr_dialog
            
            # Connect component signals
            self._connect_component_signals()
            
            # Initialize component configurations
            self._configure_components()
            
            self.status = IntegrationStatus.IDLE
            self.status_changed.emit(self.status)
            
            self.logger.info("Validation tools integration initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize validation tools: {e}")
            self.status = IntegrationStatus.ERROR
            self.status_changed.emit(self.status)
            return False
    
    def start_validation_session(self,
                                document_path: Path,
                                mode: ValidationMode = ValidationMode.HYBRID_WORKFLOW,
                                pages_total: int = 1) -> str:
        """
        Start a new validation session.
        
        Args:
            document_path: Path to document being validated
            mode: Validation workflow mode
            pages_total: Total number of pages
            
        Returns:
            Session ID for tracking
        """
        import uuid
        session_id = str(uuid.uuid4())
        
        # Create session
        session = ValidationSession(
            session_id=session_id,
            document_path=document_path,
            mode=mode,
            pages_total=pages_total
        )
        
        self.current_session = session
        self.sessions[session_id] = session
        
        # Initialize components for session
        if self.drawing_manager:
            self.drawing_manager.start_session(session_id)
        
        if self.wizard:
            self.wizard.start_validation_session(session_id)
        
        # Update statistics
        self.statistics.total_sessions += 1
        
        self.logger.info(f"Started validation session {session_id} for {document_path}")
        self.session_started.emit(session_id)
        
        return session_id
    
    def configure_integration(self, config: Dict[str, Any]) -> None:
        """
        Update integration configuration.
        
        Args:
            config: Configuration dictionary
        """
        self.config.update(config)
        self._configure_components()
        self.logger.info("Integration configuration updated")
    
    def get_session_statistics(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics for a session or overall.
        
        Args:
            session_id: Specific session ID, or None for overall stats
            
        Returns:
            Statistics dictionary
        """
        if session_id and session_id in self.sessions:
            session = self.sessions[session_id]
            return {
                'session_id': session_id,
                'duration': session.duration,
                'pages_completed': session.pages_completed,
                'pages_total': session.pages_total,
                'progress_percentage': session.progress_percentage,
                'elements_detected': session.elements_detected,
                'elements_validated': session.elements_validated,
                'ocr_requests': session.ocr_requests,
                'errors': len(session.errors),
                'status': session.status.value
            }
        else:
            return {
                'total_sessions': self.statistics.total_sessions,
                'total_elements': self.statistics.total_elements,
                'total_ocr_requests': self.statistics.total_ocr_requests,
                'average_duration': self.statistics.average_session_duration,
                'success_rate': self.statistics.success_rate,
                'error_count': self.statistics.error_count,
                'performance_metrics': self.statistics.performance_metrics.copy()
            }
    
    # Private methods
    
    def _connect_component_signals(self) -> None:
        """Connect signals from all components."""
        if self.drawing_manager:
            self.drawing_manager.action_performed.connect(self._on_drawing_action)
            self.drawing_manager.error_occurred.connect(self._on_component_error)
        
        if self.ocr_service:
            self.ocr_service.processing_completed.connect(self._on_ocr_completed)
            self.ocr_service.error_occurred.connect(self._on_component_error)
    
    def _configure_components(self) -> None:
        """Configure all components with current settings."""
        if self.ocr_service:
            self.ocr_service.configure({
                'max_concurrent': self.config.get('max_concurrent_ocr', 3),
                'quality_threshold': self.config.get('auto_ocr_threshold', 0.8)
            })
        
        if self.wizard:
            self.wizard.configure({
                'batch_size': self.config.get('batch_size', 10),
                'timeout': self.config.get('session_timeout', 3600)
            })
    
    def _setup_error_handling(self) -> None:
        """Setup comprehensive error handling."""
        self.logger.setLevel(logging.DEBUG if self.config.get('debug_mode') else logging.INFO)
    
    def _update_performance_metrics(self) -> None:
        """Update performance metrics."""
        if not self.config.get('performance_monitoring'):
            return
        
        # Collect current performance data
        metrics = {
            'memory_usage': self._get_memory_usage(),
            'processing_time': self._get_average_processing_time()
        }
        
        self.statistics.performance_metrics.update(metrics)
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return 0.0
    
    def _get_average_processing_time(self) -> float:
        """Get average processing time for recent operations."""
        if self.current_session:
            return self.current_session.duration / max(1, self.current_session.pages_completed)
        return 0.0
    
    # Signal handlers
    
    def _on_drawing_action(self, action: DrawingAction) -> None:
        """Handle drawing manager actions."""
        if self.current_session:
            self.current_session.elements_detected += 1
    
    def _on_ocr_completed(self, response: OCRResponse) -> None:
        """Handle OCR completion."""
        if self.current_session:
            self.statistics.total_ocr_requests += 1
    
    def _on_component_error(self, error_msg: str) -> None:
        """Handle component errors."""
        if self.current_session:
            self.current_session.errors.append(error_msg)
            self.error_occurred.emit(self.current_session.session_id, error_msg)
        
        self.logger.error(f"Component error: {error_msg}")


def create_validation_integration(parent: Optional[QWidget] = None) -> ValidationToolsIntegration:
    """
    Create a fully configured validation tools integration.
    
    Args:
        parent: Parent widget
        
    Returns:
        Configured ValidationToolsIntegration instance
    """
    integration = ValidationToolsIntegration(parent)
    
    # Create component instances
    drawing_manager = DrawingStateManager()
    area_tool = AreaSelectTool() 
    ocr_service = ValidationOCRService()
    wizard = ValidationWizard()
    toolbar = ValidationToolbar()
    ocr_dialog = OCRDialog()
    
    # Initialize integration
    success = integration.initialize_components(
        drawing_manager, area_tool, ocr_service,
        wizard, toolbar, ocr_dialog
    )
    
    if not success:
        raise RuntimeError("Failed to initialize validation tools integration")
    
    return integration


def get_integration_statistics() -> Dict[str, Any]:
    """
    Get global integration statistics.
    
    Returns:
        Statistics dictionary
    """
    return {
        'total_integrations_created': 0,
        'active_integrations': 0,
        'total_sessions_processed': 0
    }