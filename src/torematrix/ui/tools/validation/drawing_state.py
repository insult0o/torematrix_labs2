"""
Drawing state management system for manual validation interface.

Agent 1 implementation for Issue #26 - Core drawing state management.
This module provides the core drawing state management for the manual validation
workflow, including draw mode activation, area selection, and element creation.
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
    """Core drawing state management for manual validation interface."""
    
    # Signals for UI integration
    mode_changed = pyqtSignal(DrawingMode)
    state_changed = pyqtSignal(DrawingState)
    area_selected = pyqtSignal(DrawingArea)
    element_created = pyqtSignal(Element)
    session_completed = pyqtSignal(DrawingSession)
    error_occurred = pyqtSignal(str)
    
<<<<<<< HEAD
    def __init__(self, parent: Optional[QWidget] = None):
=======
    def __init__(self, parent=None):
<<<<<<< HEAD
>>>>>>> origin/main
        super().__init__(parent)
        self.logger = logging.getLogger("torematrix.ui.drawing_state")
        
        # Core state
        self._mode = DrawingMode.DISABLED
        self._state = DrawingState.IDLE
        self._current_session: Optional[DrawingSession] = None
        self._current_area: Optional[DrawingArea] = None
        
<<<<<<< HEAD
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
=======
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
>>>>>>> origin/main
        self._ocr_timer = QTimer()
        self._ocr_timer.setSingleShot(True)
        self._ocr_timer.timeout.connect(self._process_ocr_delayed)
        
        self.logger.info("Drawing state manager initialized")
    
<<<<<<< HEAD
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
=======
    # Properties for UI integration
    @property
    def mode(self) -> DrawingMode:
>>>>>>> origin/main
        return self._mode
    
    @property
    def state(self) -> DrawingState:
<<<<<<< HEAD
        """Get current drawing state."""
=======
>>>>>>> origin/main
        return self._state
    
    @property
    def current_session(self) -> Optional[DrawingSession]:
<<<<<<< HEAD
        """Get current drawing session."""
=======
>>>>>>> origin/main
        return self._current_session
    
    @property
    def current_area(self) -> Optional[DrawingArea]:
<<<<<<< HEAD
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
=======
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
>>>>>>> origin/main
    
    def _reset_to_idle(self) -> None:
        """Reset state to idle for next operation."""
        self._state = DrawingState.IDLE
        self._mode = DrawingMode.SELECTION
        self._current_area = None
        
        self.state_changed.emit(self._state)
        self.mode_changed.emit(self._mode)
    
<<<<<<< HEAD
    def get_session_info(self) -> Dict[str, Any]:
        """Get current session information."""
=======
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
>>>>>>> origin/main
        if not self._current_session:
            return {}
        
        return {
            "session_id": self._current_session.session_id,
<<<<<<< HEAD
=======
<<<<<<< HEAD
>>>>>>> origin/main
            "batch_mode": self._current_session.batch_mode,
            "areas_count": len(self._current_session.areas),
            "started_at": self._current_session.started_at.isoformat(),
            "completed_at": self._current_session.completed_at.isoformat() if self._current_session.completed_at else None,
            "is_complete": self._current_session.is_complete
        }
<<<<<<< HEAD
    
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
=======
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
>>>>>>> origin/main
