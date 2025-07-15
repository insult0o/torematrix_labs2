"""
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
        if not self._current_session:
            return {}
        
        return {
            "session_id": self._current_session.session_id,
            "batch_mode": self._current_session.batch_mode,
            "areas_count": len(self._current_session.areas),
            "started_at": self._current_session.started_at.isoformat(),
            "completed_at": self._current_session.completed_at.isoformat() if self._current_session.completed_at else None,
            "is_complete": self._current_session.is_complete
        }