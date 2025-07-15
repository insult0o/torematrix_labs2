"""
Drawing State Management for Manual Validation Interface.

This module provides the core state management system for the manual validation
drawing interface, implementing a state machine pattern with PyQt6 signals.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtGui import QPixmap
import uuid
import asyncio
from datetime import datetime

from ....core.models import Element, ElementType


class DrawingMode(Enum):
    """Drawing modes for manual validation."""
    DISABLED = "disabled"
    SELECTION = "selection"
    DRAWING = "drawing"
    PREVIEW = "preview"
    CONFIRMING = "confirming"


class DrawingState(Enum):
    """Current state of the drawing operation."""
    IDLE = "idle"
    AREA_SELECTING = "area_selecting"
    AREA_SELECTED = "area_selected"
    ELEMENT_CREATING = "element_creating"
    ELEMENT_CREATED = "element_created"
    OCR_PROCESSING = "ocr_processing"
    OCR_COMPLETED = "ocr_completed"
    ERROR = "error"


@dataclass(frozen=True)
class DrawingArea:
    """Represents a selected drawing area for element creation."""
    x: int
    y: int
    width: int
    height: int
    page_number: int
    area_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "page_number": self.page_number,
            "area_id": self.area_id,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass(frozen=True)
class DrawingSession:
    """Represents a complete drawing session with multiple areas."""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    areas: List[DrawingArea] = field(default_factory=list)
    elements: List[Element] = field(default_factory=list)
    document_path: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "areas": [area.to_dict() for area in self.areas],
            "elements": [element.to_dict() for element in self.elements],
            "document_path": self.document_path,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }


class DrawingStateManager(QObject):
    """Core drawing state management for manual validation interface."""
    
    # Signals for UI integration
    mode_changed = pyqtSignal(DrawingMode)
    state_changed = pyqtSignal(DrawingState)
    area_selected = pyqtSignal(DrawingArea)
    element_created = pyqtSignal(Element)
    session_completed = pyqtSignal(DrawingSession)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, parent=None):
        """Initialize the drawing state manager."""
        super().__init__(parent)
        self._current_mode = DrawingMode.DISABLED
        self._current_state = DrawingState.IDLE
        self._current_area: Optional[DrawingArea] = None
        self._current_element_type: Optional[ElementType] = None
        self._current_session: Optional[DrawingSession] = None
        self._error_message: Optional[str] = None
        
        # Timer for state transitions
        self._state_timer = QTimer()
        self._state_timer.timeout.connect(self._check_state_timeout)
        self._state_timer.setSingleShot(True)
    
    @property
    def current_mode(self) -> DrawingMode:
        """Get the current drawing mode."""
        return self._current_mode
    
    @property
    def current_state(self) -> DrawingState:
        """Get the current drawing state."""
        return self._current_state
    
    @property
    def current_area(self) -> Optional[DrawingArea]:
        """Get the currently selected area."""
        return self._current_area
    
    @property
    def current_session(self) -> Optional[DrawingSession]:
        """Get the current drawing session."""
        return self._current_session
    
    def start_drawing_mode(self) -> bool:
        """Start drawing mode for manual validation."""
        try:
            if self._current_mode == DrawingMode.DISABLED:
                self._current_mode = DrawingMode.SELECTION
                self._current_state = DrawingState.IDLE
                self._current_session = DrawingSession()
                
                self.mode_changed.emit(self._current_mode)
                self.state_changed.emit(self._current_state)
                return True
            return False
        except Exception as e:
            self._handle_error(f"Failed to start drawing mode: {str(e)}")
            return False
    
    def stop_drawing_mode(self) -> bool:
        """Stop drawing mode and complete session."""
        try:
            if self._current_mode != DrawingMode.DISABLED:
                if self._current_session:
                    # Complete the session
                    completed_session = DrawingSession(
                        session_id=self._current_session.session_id,
                        areas=self._current_session.areas,
                        elements=self._current_session.elements,
                        document_path=self._current_session.document_path,
                        started_at=self._current_session.started_at,
                        completed_at=datetime.now()
                    )
                    self.session_completed.emit(completed_session)
                
                self._current_mode = DrawingMode.DISABLED
                self._current_state = DrawingState.IDLE
                self._current_area = None
                self._current_session = None
                
                self.mode_changed.emit(self._current_mode)
                self.state_changed.emit(self._current_state)
                return True
            return False
        except Exception as e:
            self._handle_error(f"Failed to stop drawing mode: {str(e)}")
            return False
    
    def start_area_selection(self) -> bool:
        """Start area selection process."""
        try:
            if (self._current_mode == DrawingMode.SELECTION and 
                self._current_state == DrawingState.IDLE):
                
                self._current_state = DrawingState.AREA_SELECTING
                self._start_timeout(30000)  # 30 second timeout
                
                self.state_changed.emit(self._current_state)
                return True
            return False
        except Exception as e:
            self._handle_error(f"Failed to start area selection: {str(e)}")
            return False
    
    def complete_area_selection(self, x: int, y: int, width: int, height: int, page_number: int) -> bool:
        """Complete area selection with coordinates."""
        try:
            if self._current_state == DrawingState.AREA_SELECTING:
                self._current_area = DrawingArea(
                    x=x, y=y, width=width, height=height, page_number=page_number
                )
                self._current_state = DrawingState.AREA_SELECTED
                self._stop_timeout()
                
                self.area_selected.emit(self._current_area)
                self.state_changed.emit(self._current_state)
                return True
            return False
        except Exception as e:
            self._handle_error(f"Failed to complete area selection: {str(e)}")
            return False
    
    def set_element_type(self, element_type: ElementType) -> bool:
        """Set the element type for creation."""
        try:
            if self._current_state == DrawingState.AREA_SELECTED:
                self._current_element_type = element_type
                self._current_state = DrawingState.ELEMENT_CREATING
                
                self.state_changed.emit(self._current_state)
                return True
            return False
        except Exception as e:
            self._handle_error(f"Failed to set element type: {str(e)}")
            return False
    
    def create_element(self, text: str = "", additional_metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Create element with extracted text and metadata."""
        try:
            if (self._current_state == DrawingState.ELEMENT_CREATING and 
                self._current_area and self._current_element_type):
                
                # Create element with basic information
                element = Element(
                    element_type=self._current_element_type,
                    text=text,
                    metadata=additional_metadata
                )
                
                # Add to current session
                if self._current_session:
                    updated_areas = list(self._current_session.areas) + [self._current_area]
                    updated_elements = list(self._current_session.elements) + [element]
                    
                    self._current_session = DrawingSession(
                        session_id=self._current_session.session_id,
                        areas=updated_areas,
                        elements=updated_elements,
                        document_path=self._current_session.document_path,
                        started_at=self._current_session.started_at,
                        completed_at=None
                    )
                
                self._current_state = DrawingState.ELEMENT_CREATED
                self._current_area = None
                self._current_element_type = None
                
                self.element_created.emit(element)
                self.state_changed.emit(self._current_state)
                return True
            return False
        except Exception as e:
            self._handle_error(f"Failed to create element: {str(e)}")
            return False
    
    def reset_to_selection(self) -> bool:
        """Reset state back to selection mode."""
        try:
            if self._current_mode != DrawingMode.DISABLED:
                self._current_state = DrawingState.IDLE
                self._current_area = None
                self._current_element_type = None
                self._stop_timeout()
                
                self.state_changed.emit(self._current_state)
                return True
            return False
        except Exception as e:
            self._handle_error(f"Failed to reset to selection: {str(e)}")
            return False
    
    def _start_timeout(self, timeout_ms: int):
        """Start timeout timer for state transitions."""
        self._state_timer.start(timeout_ms)
    
    def _stop_timeout(self):
        """Stop timeout timer."""
        self._state_timer.stop()
    
    def _check_state_timeout(self):
        """Handle state timeout."""
        self._handle_error("Operation timed out")
    
    def _handle_error(self, error_message: str):
        """Handle error state."""
        self._error_message = error_message
        self._current_state = DrawingState.ERROR
        self._current_area = None
        self._current_element_type = None
        self._stop_timeout()
        
        self.error_occurred.emit(error_message)
        self.state_changed.emit(self._current_state)
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics about the current session."""
        if not self._current_session:
            return {}
        
        return {
            "session_id": self._current_session.session_id,
            "areas_count": len(self._current_session.areas),
            "elements_count": len(self._current_session.elements),
            "duration": (datetime.now() - self._current_session.started_at).total_seconds(),
            "document_path": self._current_session.document_path
        }
    
    # Integration hooks for other agents
    def get_ocr_integration_hook(self):
        """Get hook for OCR service integration (Agent 2)."""
        return {
            "start_ocr_processing": self._start_ocr_processing,
            "complete_ocr_processing": self._complete_ocr_processing,
            "current_area": self._current_area
        }
    
    def get_ui_integration_hook(self):
        """Get hook for UI component integration (Agent 3)."""
        return {
            "state_manager": self,
            "signals": {
                "mode_changed": self.mode_changed,
                "state_changed": self.state_changed,
                "area_selected": self.area_selected,
                "element_created": self.element_created,
                "error_occurred": self.error_occurred
            }
        }
    
    def _start_ocr_processing(self):
        """Start OCR processing (called by Agent 2)."""
        if self._current_state == DrawingState.ELEMENT_CREATING:
            self._current_state = DrawingState.OCR_PROCESSING
            self.state_changed.emit(self._current_state)
    
    def _complete_ocr_processing(self, extracted_text: str):
        """Complete OCR processing with results (called by Agent 2)."""
        if self._current_state == DrawingState.OCR_PROCESSING:
            self._current_state = DrawingState.OCR_COMPLETED
            self.state_changed.emit(self._current_state)
            return extracted_text
        return ""