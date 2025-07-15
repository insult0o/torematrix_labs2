"""
Drawing state management system for manual validation interface.

This module provides the core drawing state management for the manual validation
workflow, including draw mode activation, area selection, and element creation.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from PyQt6.QtCore import QObject, pyqtSignal, QPoint, QRect, QTimer
from PyQt6.QtGui import QPixmap, QImage, QPainter, QPen, QColor, QBrush
from PyQt6.QtWidgets import QWidget

from ...viewer.coordinates import Point, Rectangle
from ...viewer.layers import LayerElement
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
    ocr_result: Optional[Any] = None  # OCRResult will be defined by Agent 2
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
    """
    Manages the drawing state for manual validation interface.
    
    This class handles the complete workflow of manual element creation:
    1. Draw mode activation
    2. Area selection and drawing
    3. OCR processing of selected areas
    4. Text editing and element type selection
    5. Element creation and validation
    """
    
    # Signals
    mode_changed = pyqtSignal(DrawingMode)
    state_changed = pyqtSignal(DrawingState)
    area_selected = pyqtSignal(DrawingArea)
    element_created = pyqtSignal(Element)
    session_completed = pyqtSignal(DrawingSession)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.logger = logging.getLogger("torematrix.ui.drawing_state")
        
        # Core state
        self._mode = DrawingMode.DISABLED
        self._state = DrawingState.IDLE
        self._current_session: Optional[DrawingSession] = None
        self._current_area: Optional[DrawingArea] = None
        
        # Drawing configuration
        self._drawing_config = {
            "min_area_size": 10,  # Minimum area size in pixels
            "max_area_size": 2000,  # Maximum area size in pixels
            "preview_scale": 1.0,  # Preview image scale
            "auto_ocr": True,  # Automatically run OCR on area selection
            "ocr_confidence_threshold": 0.6,  # Minimum OCR confidence
            "batch_mode": False,  # Enable batch processing
            "selection_color": QColor(255, 140, 0),  # Orange selection color
            "preview_color": QColor(0, 255, 0, 100),  # Semi-transparent green
        }
        
        # OCR engine - will be set by Agent 2
        self._ocr_engine: Optional[Any] = None
        
        # Callbacks
        self._area_validator: Optional[Callable[[DrawingArea], bool]] = None
        self._element_creator: Optional[Callable[[DrawingArea], Element]] = None
        self._session_handler: Optional[Callable[[DrawingSession], None]] = None
        
        # Timers
        self._ocr_timer = QTimer()
        self._ocr_timer.setSingleShot(True)
        self._ocr_timer.timeout.connect(self._process_ocr_delayed)
        
        self.logger.info("Drawing state manager initialized")
    
    def set_drawing_config(self, config: Dict[str, Any]) -> None:
        """Update drawing configuration."""
        self._drawing_config.update(config)
        self.logger.debug(f"Drawing config updated: {config}")
    
    def get_drawing_config(self) -> Dict[str, Any]:
        """Get current drawing configuration."""
        return self._drawing_config.copy()
    
    def set_callbacks(self, 
                     area_validator: Optional[Callable[[DrawingArea], bool]] = None,
                     element_creator: Optional[Callable[[DrawingArea], Element]] = None,
                     session_handler: Optional[Callable[[DrawingSession], None]] = None) -> None:
        """Set callback functions for validation and creation."""
        self._area_validator = area_validator
        self._element_creator = element_creator
        self._session_handler = session_handler
        self.logger.debug("Callbacks configured")
    
    def initialize_ocr(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize OCR engine - will be implemented by Agent 2."""
        self.logger.info("OCR initialization hook called")
        # Agent 2 will implement OCR engine initialization
        pass
    
    @property
    def mode(self) -> DrawingMode:
        """Get current drawing mode."""
        return self._mode
    
    @property
    def state(self) -> DrawingState:
        """Get current drawing state."""
        return self._state
    
    @property
    def current_session(self) -> Optional[DrawingSession]:
        """Get current drawing session."""
        return self._current_session
    
    @property
    def current_area(self) -> Optional[DrawingArea]:
        """Get current drawing area."""
        return self._current_area
    
    def activate_draw_mode(self, batch_mode: bool = False) -> bool:
        """
        Activate drawing mode for manual validation.
        
        Args:
            batch_mode: Enable batch processing mode
            
        Returns:
            True if successfully activated
        """
        try:
            if self._mode == DrawingMode.DISABLED:
                self._mode = DrawingMode.SELECTION
                self._state = DrawingState.IDLE
                self._drawing_config["batch_mode"] = batch_mode
                
                # Create new session
                session_id = f"drawing_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                self._current_session = DrawingSession(
                    session_id=session_id,
                    batch_mode=batch_mode
                )
                
                self.mode_changed.emit(self._mode)
                self.state_changed.emit(self._state)
                
                self.logger.info(f"Draw mode activated (batch: {batch_mode})")
                return True
            else:
                self.logger.warning("Draw mode already active")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to activate draw mode: {e}")
            self.error_occurred.emit(f"Failed to activate draw mode: {e}")
            return False
    
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
            self._state = DrawingState.SELECTING_AREA
            self._current_area = None
            
            self.state_changed.emit(self._state)
            self.logger.debug("Area selection started")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start area selection: {e}")
            self.error_occurred.emit(f"Failed to start area selection: {e}")
            return False
    
    def complete_area_selection(self, rectangle: Rectangle, preview_image: Optional[QPixmap] = None) -> bool:
        """
        Complete area selection with drawn rectangle.
        
        Args:
            rectangle: Selected area rectangle
            preview_image: Optional preview image of the area
            
        Returns:
            True if area selection completed successfully
        """
        if self._state != DrawingState.SELECTING_AREA:
            self.logger.warning("Not in area selection state")
            return False
        
        try:
            # Validate area size
            if (rectangle.width < self._drawing_config["min_area_size"] or 
                rectangle.height < self._drawing_config["min_area_size"]):
                self.logger.warning("Selected area too small")
                return False
            
            if (rectangle.width > self._drawing_config["max_area_size"] or 
                rectangle.height > self._drawing_config["max_area_size"]):
                self.logger.warning("Selected area too large")
                return False
            
            # Create drawing area
            self._current_area = DrawingArea(
                rectangle=rectangle,
                preview_image=preview_image
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
            
            self.logger.info(f"Area selection completed: {rectangle}")
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
            if self._state in [DrawingState.SELECTING_AREA, DrawingState.AREA_SELECTED]:
                self._state = DrawingState.CANCELLED
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
            self._state = DrawingState.PROCESSING_OCR
            self.state_changed.emit(self._state)
            
            # Agent 2 will implement actual OCR processing
            # For now, simulate OCR completion
            self._state = DrawingState.EDITING_TEXT
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
            self._current_area.manual_text = text
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
            self._current_area.element_type = element_type
            self._state = DrawingState.CREATING_ELEMENT
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
        if not self._current_area or not self._current_area.element_type:
            self.logger.warning("No area or element type to create element")
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
                    self._current_session.areas.append(self._current_area)
                
                self._state = DrawingState.COMPLETED
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
                element_type=area.element_type,
                text=area.final_text,
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
            "batch_mode": self._current_session.batch_mode,
            "areas_count": len(self._current_session.areas),
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