"""
Drawing State Management for Manual Validation Interface.

Agent 1 implementation for Issue #26 - Core drawing state management.
This module provides the core drawing state management for the manual validation
workflow, including draw mode activation, area selection, and element creation.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any, Callable
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtGui import QPixmap, QColor
import uuid
import asyncio
import logging
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
    """Current state of the drawing process."""
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


@dataclass
class DrawingSession:
    """Represents a complete drawing session with multiple areas."""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    areas: List[DrawingArea] = field(default_factory=list)
    elements: List[Element] = field(default_factory=list)
    document_path: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    @property
    def is_complete(self) -> bool:
        """Check if all areas have been processed."""
        return all(area.element_type is not None for area in self.areas)
    
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
            "preview_color": QColor(0, 255, 0, 100),
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
        self._current_session = DrawingSession(session_id=session_id)
        
        self.mode_changed.emit(self._mode)
        self.state_changed.emit(self._state)
        
        self.logger.info(f"Draw mode activated (batch: {batch_mode})")
        return True
    
    def deactivate_draw_mode(self) -> bool:
        """
        Deactivate drawing mode and cleanup.
        
        Returns:
            True if successfully deactivated
        """
        try:
            if self._mode != DrawingMode.DISABLED:
                # Complete current session if active
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
            else:
                self.logger.warning("Draw mode already disabled")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to deactivate draw mode: {e}")
            self.error_occurred.emit(f"Failed to deactivate draw mode: {e}")
            return False
    
    def start_area_selection(self) -> bool:
        """
        Start area selection process.
        
        Returns:
            True if selection started successfully
        """
        if self._mode != DrawingMode.SELECTION:
            self.logger.warning("Not in selection mode")
            return False
        
        try:
            self._state = DrawingState.AREA_SELECTING
            self._current_area = None
            
            self.state_changed.emit(self._state)
            self.logger.debug("Area selection started")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start area selection: {e}")
            self.error_occurred.emit(f"Failed to start area selection: {e}")
            return False
    
    def complete_area_selection(self, x: int, y: int, width: int, height: int, 
                              page_number: int, preview_image: Optional[QPixmap] = None) -> bool:
        """
        Complete area selection with coordinates.
        
        Args:
            x: X coordinate of selection
            y: Y coordinate of selection
            width: Width of selection
            height: Height of selection
            page_number: Page number
            preview_image: Optional preview image of the area
            
        Returns:
            True if area selection completed successfully
        """
        if self._state != DrawingState.AREA_SELECTING:
            self.logger.warning("Not in area selection state")
            return False
        
        try:
            # Validate area size
            if (width < self._drawing_config["min_area_size"] or 
                height < self._drawing_config["min_area_size"]):
                self.logger.warning("Selected area too small")
                return False
            
            if (width > self._drawing_config["max_area_size"] or 
                height > self._drawing_config["max_area_size"]):
                self.logger.warning("Selected area too large")
                return False
            
            # Create drawing area
            self._current_area = DrawingArea(
                x=x, y=y, width=width, height=height, page_number=page_number
            )
            
            # Validate area if validator is set
            if self._area_validator and not self._area_validator(self._current_area):
                self.logger.warning("Area validation failed")
                return False
            
            self._state = DrawingState.AREA_SELECTED
            self._mode = DrawingMode.PREVIEW
            
            self.state_changed.emit(self._state)
            self.mode_changed.emit(self._mode)
            self.area_selected.emit(self._current_area)
            
            # Auto-start OCR if enabled
            if self._drawing_config["auto_ocr"] and self._ocr_engine:
                self._ocr_timer.start(100)  # Small delay to allow UI update
            
            self.logger.info(f"Area selection completed: ({x}, {y}, {width}, {height})")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to complete area selection: {e}")
            self.error_occurred.emit(f"Failed to complete area selection: {e}")
            return False
    
    def cancel_area_selection(self) -> bool:
        """
        Cancel current area selection.
        
        Returns:
            True if cancellation successful
        """
        try:
            if self._state in [DrawingState.AREA_SELECTING, DrawingState.AREA_SELECTED]:
                self._state = DrawingState.IDLE
                self._current_area = None
                
                self.state_changed.emit(self._state)
                self.logger.debug("Area selection cancelled")
                
                # Return to idle state
                self._reset_to_idle()
                return True
            else:
                self.logger.warning("No area selection to cancel")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to cancel area selection: {e}")
            self.error_occurred.emit(f"Failed to cancel area selection: {e}")
            return False
    
    def _process_ocr_delayed(self) -> None:
        """Process OCR with delay (called by timer)."""
        asyncio.create_task(self.process_ocr())
    
    async def process_ocr(self) -> bool:
        """
        Process OCR on current area - placeholder for Agent 2.
        
        Returns:
            True if OCR processing completed successfully
        """
        if not self._current_area:
            self.logger.warning("No area available for OCR")
            return False
        
        try:
            self._state = DrawingState.OCR_PROCESSING
            self.state_changed.emit(self._state)
            
            # Agent 2 will implement actual OCR processing
            # For now, simulate OCR completion
            self._state = DrawingState.OCR_COMPLETED
            self.state_changed.emit(self._state)
            
            self.logger.info("OCR processing completed (placeholder)")
            return True
            
        except Exception as e:
            self.logger.error(f"OCR processing failed: {e}")
            self.error_occurred.emit(f"OCR processing failed: {e}")
            return False
    
    def set_manual_text(self, text: str) -> bool:
        """
        Set manual text override for current area.
        
        Args:
            text: Manual text input
            
        Returns:
            True if text set successfully
        """
        if not self._current_area:
            self.logger.warning("No current area to set text")
            return False
        
        try:
            # Note: Since DrawingArea is frozen, we need to create a new one
            # This is a placeholder - Agent 2 will implement proper text handling
            self.logger.debug(f"Manual text set: {text}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to set manual text: {e}")
            self.error_occurred.emit(f"Failed to set manual text: {e}")
            return False
    
    def set_element_type(self, element_type: ElementType) -> bool:
        """
        Set element type for current area.
        
        Args:
            element_type: Type of element to create
            
        Returns:
            True if type set successfully
        """
        if not self._current_area:
            self.logger.warning("No current area to set element type")
            return False
        
        try:
            # Note: Since DrawingArea is frozen, we need to create a new one
            # This is a placeholder - Agent 2 will implement proper element type handling
            self._state = DrawingState.ELEMENT_CREATING
            self.state_changed.emit(self._state)
            
            self.logger.debug(f"Element type set: {element_type}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to set element type: {e}")
            self.error_occurred.emit(f"Failed to set element type: {e}")
            return False
    
    def create_element(self) -> bool:
        """
        Create element from current area.
        
        Returns:
            True if element created successfully
        """
        if not self._current_area:
            self.logger.warning("No area to create element")
            return False
        
        try:
            # Create element using callback or default method
            if self._element_creator:
                element = self._element_creator(self._current_area)
            else:
                element = self._create_default_element(self._current_area)
            
            if element:
                # Add area to session
                if self._current_session:
                    # Create new session with updated areas and elements
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
                
                self._state = DrawingState.ELEMENT_CREATED
                self.state_changed.emit(self._state)
                self.element_created.emit(element)
                
                self.logger.info(f"Element created: {element.element_id}")
                
                # Handle batch mode or complete session
                if self._drawing_config["batch_mode"]:
                    self._reset_to_idle()
                else:
                    self.deactivate_draw_mode()
                
                return True
            else:
                self.logger.error("Failed to create element")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to create element: {e}")
            self.error_occurred.emit(f"Failed to create element: {e}")
            return False
    
    def _create_default_element(self, area: DrawingArea) -> Optional[Element]:
        """
        Create default element from drawing area.
        
        Args:
            area: Drawing area with element data
            
        Returns:
            Created element or None if failed
        """
        try:
            # Create basic element
            element = Element(
                element_type=ElementType.TEXT,  # Default type
                text="",  # Will be set by Agent 2 with OCR or manual input
                metadata=None  # Will be set by Agent 2 with proper metadata
            )
            
            return element
            
        except Exception as e:
            self.logger.error(f"Failed to create default element: {e}")
            return None
    
    def _reset_to_idle(self) -> None:
        """Reset state to idle for next operation."""
        self._state = DrawingState.IDLE
        self._mode = DrawingMode.SELECTION
        self._current_area = None
        
        self.state_changed.emit(self._state)
        self.mode_changed.emit(self._mode)
    
    def get_session_info(self) -> Dict[str, Any]:
        """Get current session information."""
        if not self._current_session:
            return {}
        
        return {
            "session_id": self._current_session.session_id,
            "areas_count": len(self._current_session.areas),
            "elements_count": len(self._current_session.elements),
            "started_at": self._current_session.started_at.isoformat(),
            "completed_at": self._current_session.completed_at.isoformat() if self._current_session.completed_at else None,
            "is_complete": self._current_session.is_complete
        }
    
    def get_state_info(self) -> Dict[str, Any]:
        """Get current state information."""
        return {
            "mode": self._mode.value,
            "state": self._state.value,
            "has_session": self._current_session is not None,
            "has_area": self._current_area is not None,
            "ocr_available": self._ocr_engine is not None,
            "config": self._drawing_config.copy()
        }
    
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
        if self._state == DrawingState.ELEMENT_CREATING:
            self._state = DrawingState.OCR_PROCESSING
            self.state_changed.emit(self._state)
    
    def _complete_ocr_processing(self, extracted_text: str):
        """Complete OCR processing with results (called by Agent 2)."""
        if self._state == DrawingState.OCR_PROCESSING:
            self._state = DrawingState.OCR_COMPLETED
            self.state_changed.emit(self._state)
            return extracted_text
        return ""