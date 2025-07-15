"""
<<<<<<< HEAD
Drawing state management system for manual validation interface.

Agent 1 implementation for Issue #27 - Core drawing state management.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtGui import QPixmap, QColor

from ...viewer.coordinates import Rectangle
=======
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

>>>>>>> origin/main
from ....core.models import Element, ElementType


class DrawingMode(Enum):
    """Drawing modes for manual validation."""
    DISABLED = "disabled"
    SELECTION = "selection"
    DRAWING = "drawing"
    PREVIEW = "preview"
    CONFIRMING = "confirming"


class DrawingState(Enum):
<<<<<<< HEAD
    """Current state of the drawing process."""
    IDLE = "idle"
    SELECTING_AREA = "selecting_area"
    AREA_SELECTED = "area_selected"
    PROCESSING_OCR = "processing_ocr"
    EDITING_TEXT = "editing_text"
    CHOOSING_TYPE = "choosing_type"
    CREATING_ELEMENT = "creating_element"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class DrawingArea:
    """Represents a drawn area for element creation."""
    rectangle: Rectangle
    preview_image: Optional[QPixmap] = None
    ocr_result: Optional[Any] = None
    suggested_text: str = ""
    manual_text: str = ""
    element_type: Optional[ElementType] = None
    confidence: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    
    @property
    def final_text(self) -> str:
        """Get the final text (manual override or OCR result)."""
        return self.manual_text if self.manual_text else self.suggested_text


@dataclass
class DrawingSession:
    """Complete drawing session with multiple areas."""
    session_id: str
    areas: List[DrawingArea] = field(default_factory=list)
    batch_mode: bool = False
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    @property
    def is_complete(self) -> bool:
        """Check if all areas have been processed."""
        return all(area.element_type is not None for area in self.areas)
=======
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
>>>>>>> origin/main


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
<<<<<<< HEAD
        super().__init__(parent)
        self.logger = logging.getLogger("torematrix.ui.drawing_state")
        
        # Core state
        self._mode = DrawingMode.DISABLED
        self._state = DrawingState.IDLE
        self._current_session: Optional[DrawingSession] = None
        self._current_area: Optional[DrawingArea] = None
        
        # Configuration
        self._drawing_config = {
            "min_area_size": 10,
            "max_area_size": 2000,
            "auto_ocr": True,
            "batch_mode": False,
            "selection_color": QColor(255, 140, 0),
        }
        
        # Integration hooks for other agents
        self._ocr_engine = None
        self._area_validator = None
        self._element_creator = None
        self._session_handler = None
        
        # OCR processing timer
        self._ocr_timer = QTimer()
        self._ocr_timer.setSingleShot(True)
        self._ocr_timer.timeout.connect(self._process_ocr_delayed)
        
        self.logger.info("Drawing state manager initialized")
    
    # Properties for UI integration
    @property
    def mode(self) -> DrawingMode:
        return self._mode
    
    @property
    def state(self) -> DrawingState:
        return self._state
    
    @property
    def current_session(self) -> Optional[DrawingSession]:
        return self._current_session
    
    @property
    def current_area(self) -> Optional[DrawingArea]:
        return self._current_area
    
    # Core state management methods
    def activate_draw_mode(self, batch_mode: bool = False) -> bool:
        """Activate drawing mode for manual validation."""
        if self._mode != DrawingMode.DISABLED:
            return False
        
        self._mode = DrawingMode.SELECTION
        self._state = DrawingState.IDLE
        self._drawing_config["batch_mode"] = batch_mode
        
        # Create new session
        session_id = f"drawing_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self._current_session = DrawingSession(session_id=session_id, batch_mode=batch_mode)
        
        self.mode_changed.emit(self._mode)
        self.state_changed.emit(self._state)
        
        self.logger.info(f"Draw mode activated (batch: {batch_mode})")
        return True
    
    def deactivate_draw_mode(self) -> bool:
        """Deactivate drawing mode and cleanup."""
        if self._mode == DrawingMode.DISABLED:
            return False
        
        # Complete current session
        if self._current_session and not self._current_session.completed_at:
            self._current_session.completed_at = datetime.now()
            if self._session_handler:
                self._session_handler(self._current_session)
            self.session_completed.emit(self._current_session)
        
        # Reset state
        self._mode = DrawingMode.DISABLED
        self._state = DrawingState.IDLE
        self._current_session = None
        self._current_area = None
        
        self.mode_changed.emit(self._mode)
        self.state_changed.emit(self._state)
        
        self.logger.info("Draw mode deactivated")
        return True
    
    def start_area_selection(self) -> bool:
        """Start area selection process."""
        if self._mode != DrawingMode.SELECTION:
            return False
        
        self._state = DrawingState.SELECTING_AREA
        self._current_area = None
        
        self.state_changed.emit(self._state)
        self.logger.debug("Area selection started")
        return True
    
    def complete_area_selection(self, rectangle: Rectangle, preview_image: Optional[QPixmap] = None) -> bool:
        """Complete area selection with drawn rectangle."""
        if self._state != DrawingState.SELECTING_AREA:
            return False
        
        # Validate area size
        if (rectangle.width < self._drawing_config["min_area_size"] or 
            rectangle.height < self._drawing_config["min_area_size"]):
            self.logger.warning("Selected area too small")
            return False
        
        # Create drawing area
        self._current_area = DrawingArea(rectangle=rectangle, preview_image=preview_image)
        
        # Validate with custom validator if set
        if self._area_validator and not self._area_validator(self._current_area):
            return False
        
        self._state = DrawingState.AREA_SELECTED
        self._mode = DrawingMode.PREVIEW
        
        self.state_changed.emit(self._state)
        self.mode_changed.emit(self._mode)
        self.area_selected.emit(self._current_area)
        
        # Auto-start OCR if enabled
        if self._drawing_config["auto_ocr"] and self._ocr_engine:
            self._ocr_timer.start(100)
        
        self.logger.info(f"Area selection completed: {rectangle}")
        return True
    
    def set_element_type(self, element_type: ElementType) -> bool:
        """Set element type for current area."""
        if not self._current_area:
            return False
        
        self._current_area.element_type = element_type
        self._state = DrawingState.CREATING_ELEMENT
        
        self.state_changed.emit(self._state)
        self.logger.debug(f"Element type set: {element_type}")
        return True
    
    def create_element(self) -> bool:
        """Create element from current area."""
        if not self._current_area or not self._current_area.element_type:
            return False
        
        # Create element using callback or default method
        if self._element_creator:
            element = self._element_creator(self._current_area)
        else:
            element = Element(
                element_type=self._current_area.element_type,
                text=self._current_area.final_text
            )
        
        if element:
            # Add area to session
            if self._current_session:
                self._current_session.areas.append(self._current_area)
            
            self._state = DrawingState.COMPLETED
            self.state_changed.emit(self._state)
            self.element_created.emit(element)
            
            self.logger.info(f"Element created: {element.element_id}")
            
            # Handle batch mode
            if self._drawing_config["batch_mode"]:
                self._reset_to_idle()
            else:
                self.deactivate_draw_mode()
            
            return True
        
        return False
    
    def _reset_to_idle(self) -> None:
        """Reset state to idle for next operation."""
        self._state = DrawingState.IDLE
        self._mode = DrawingMode.SELECTION
        self._current_area = None
        
        self.state_changed.emit(self._state)
        self.mode_changed.emit(self._mode)
    
    def _process_ocr_delayed(self) -> None:
        """Process OCR with delay (called by timer)."""
        asyncio.create_task(self.process_ocr())
    
    async def process_ocr(self) -> bool:
        """Process OCR on current area - placeholder for Agent 2."""
        if not self._current_area:
            return False
        
        self._state = DrawingState.PROCESSING_OCR
        self.state_changed.emit(self._state)
        
        # Agent 2 will implement actual OCR processing
        # For now, simulate OCR completion
        self._state = DrawingState.EDITING_TEXT
        self.state_changed.emit(self._state)
        
        self.logger.info("OCR processing completed (placeholder)")
        return True
    
    # Integration hooks for other agents
    def set_callbacks(self, 
                     area_validator: Optional[Callable] = None,
                     element_creator: Optional[Callable] = None,
                     session_handler: Optional[Callable] = None) -> None:
        """Set callback functions for validation and creation."""
        self._area_validator = area_validator
        self._element_creator = element_creator
        self._session_handler = session_handler
        self.logger.debug("Callbacks configured")
    
    def initialize_ocr(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize OCR engine - hook for Agent 2."""
        self.logger.info("OCR initialization hook called")
        # Agent 2 will implement OCR engine initialization
        pass
    
    def set_manual_text(self, text: str) -> bool:
        """Set manual text override for current area."""
        if not self._current_area:
            return False
        
        self._current_area.manual_text = text
        self.logger.debug(f"Manual text set: {text}")
        return True
    
    def get_session_info(self) -> Dict[str, Any]:
        """Get current session information."""
=======
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
>>>>>>> origin/main
        if not self._current_session:
            return {}
        
        return {
            "session_id": self._current_session.session_id,
<<<<<<< HEAD
            "batch_mode": self._current_session.batch_mode,
            "areas_count": len(self._current_session.areas),
            "started_at": self._current_session.started_at.isoformat(),
            "completed_at": self._current_session.completed_at.isoformat() if self._current_session.completed_at else None,
            "is_complete": self._current_session.is_complete
        }
=======
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
>>>>>>> origin/main
