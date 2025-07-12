"""
Enhanced Drag Select Label with Visual Feedback and Persistence

Advanced area selection tool with visual feedback, persistent areas,
and resize/move functionality.
"""

import logging
from typing import Dict, Optional, Set, Tuple
from datetime import datetime
from pathlib import Path

from ..qt_compat import (
    QLabel, QPainter, QPen, QBrush, QColor, QRectF, QPointF,
    QMouseEvent, Qt, QCursor, pyqtSignal
)

from ...models.visual_area_models import VisualArea, AreaType, AreaStatus
from ...core.area_storage_manager import AreaStorageManager


class EnhancedDragSelectLabel(QLabel):
    """Enhanced QLabel with drag-to-select, visual persistence, and area management."""
    
    # Signals
    area_selected = pyqtSignal(dict)  # Enhanced area data
    area_modified = pyqtSignal(str, dict)  # area_id, new_data
    area_deleted = pyqtSignal(str)  # area_id
    area_activated = pyqtSignal(str)  # area_id
    area_preview_update = pyqtSignal(dict)  # Real-time preview during dragging
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pdf_viewer = parent
        self.logger = logging.getLogger(__name__)
        
        # Selection state
        self.is_selecting = False
        self.selection_start = None
        self.selection_end = None
        self.selection_rect = None
        
        # Persistent areas
        self.persistent_areas: Dict[str, VisualArea] = {}
        self.active_area_id: Optional[str] = None
        
        # Interaction state
        self.interaction_mode = "select"  # "select", "resize", "move"
        self.resize_handle: Optional[str] = None
        self.move_start_pos = None
        self.move_start_bbox = None
        
        # Visual properties
        self.handle_size = 8
        self.glow_effect = True
        
        # Storage manager
        self.area_storage_manager: Optional[AreaStorageManager] = None
        
        # Tab restriction
        self.main_window = None  # Will be set by main window
        self.cutting_enabled = True  # Default enabled, can be controlled
        
        self.setMouseTracking(True)  # Enable mouse tracking for hover effects
        
    def set_area_storage_manager(self, storage_manager: AreaStorageManager):
        """Set the area storage manager for persistence."""
        self.area_storage_manager = storage_manager
    
    def set_main_window(self, main_window):
        """Set reference to main window for tab checking."""
        self.main_window = main_window
    
    def is_manual_validation_active(self) -> bool:
        """Check if manual validation tab is currently active."""
        print(f"🔵 TAB CHECK: Checking if manual validation tab is active")
        
        if not self.main_window or not hasattr(self.main_window, 'tab_widget'):
            print(f"🔴 TAB CHECK: No main window or tab widget, defaulting to True")
            return True  # Default to allow if we can't check
            
        try:
            current_index = self.main_window.tab_widget.currentIndex()
            current_widget = self.main_window.tab_widget.widget(current_index)
            
            print(f"🔵 TAB CHECK: Current tab index: {current_index}")
            
            # Check if current widget is manual validation widget
            if hasattr(self.main_window, 'manual_validation_widget'):
                is_manual_validation = (current_widget == self.main_window.manual_validation_widget)
                print(f"🔵 TAB CHECK: Is manual validation widget? {is_manual_validation}")
                self.logger.debug(f"TAB CHECK: Is manual validation active? {is_manual_validation}")
                return is_manual_validation
            
            # Fallback: check by tab text
            tab_text = self.main_window.tab_widget.tabText(current_index)
            is_manual_validation = "Manual Validation" in tab_text
            print(f"🔵 TAB CHECK: Tab text '{tab_text}', is manual validation? {is_manual_validation}")
            self.logger.debug(f"TAB CHECK: Tab text '{tab_text}', is manual validation? {is_manual_validation}")
            return is_manual_validation
            
        except Exception as e:
            self.logger.error(f"Error checking active tab: {e}")
            return True  # Default to allow
    
    def enable_cutting(self, enabled: bool = True):
        """Enable or disable cutting tool."""
        print(f"🔧 CUTTING: Setting cutting_enabled to {enabled}")
        self.cutting_enabled = enabled
        print(f"🔧 CUTTING: Tool {'enabled' if enabled else 'disabled'}")
        self.logger.info(f"CUTTING: Tool {'enabled' if enabled else 'disabled'}")
        
    def load_persistent_areas(self, document_id: str, page: int):
        """Load persistent areas for a document page."""
        if not self.area_storage_manager:
            self.logger.warning("LOAD AREAS: No area storage manager available")
            return
            
        try:
            self.logger.info(f"LOAD AREAS: Requesting areas for document '{document_id}', page {page}")
            
            # First, check if we have any areas at all for this document
            all_areas = self.area_storage_manager.load_areas(document_id)
            self.logger.info(f"LOAD AREAS: Document '{document_id}' has {len(all_areas)} total areas")
            
            if all_areas:
                # Show what pages have areas
                page_counts = {}
                for area_id, area in all_areas.items():
                    page_counts[area.page] = page_counts.get(area.page, 0) + 1
                    self.logger.debug(f"LOAD AREAS: - Area {area_id} on page {area.page} at {area.bbox}")
                
                self.logger.info(f"LOAD AREAS: Areas by page: {page_counts}")
            
            # Now get areas for the specific page
            areas = self.area_storage_manager.get_areas_for_page(document_id, page)
            
            # Clear existing areas first
            old_count = len(self.persistent_areas)
            self.persistent_areas.clear()
            self.logger.debug(f"LOAD AREAS: Cleared {old_count} existing areas")
            
            # Load new areas
            self.persistent_areas = areas
            self.active_area_id = None  # Reset active area when loading new page
            
            self.logger.info(f"LOAD AREAS: Successfully loaded {len(areas)} areas for page {page}")
            if areas:
                for area_id, area in areas.items():
                    self.logger.info(f"LOAD AREAS: - Area {area_id} at {area.bbox} (type: {area.area_type.value})")
            else:
                self.logger.warning(f"LOAD AREAS: No areas found for page {page}")
            
            self.update()  # Force repaint to show areas
            
        except Exception as e:
            self.logger.error(f"Error loading persistent areas: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
    
    def on_page_changed(self, page: int):
        """Handle page change to reload areas atomically."""
        self.logger.info(f"PAGE CHANGE: Page changed to {page}")
        
        # Get document information
        document_id = getattr(self.pdf_viewer, 'current_document_id', None)
        document_path = getattr(self.pdf_viewer, 'current_document_path', None)
        current_page_0based = getattr(self.pdf_viewer, 'current_page', -1)
        
        self.logger.info(f"PAGE CHANGE: Document ID: '{document_id}'")
        self.logger.info(f"PAGE CHANGE: Document path: '{document_path}'")
        self.logger.info(f"PAGE CHANGE: PDF viewer current_page (0-based): {current_page_0based}")
        self.logger.info(f"PAGE CHANGE: Page signal received (1-based): {page}")
        
        old_count = len(self.persistent_areas)
        
        # Always clear areas first to ensure proper page filtering
        self.persistent_areas.clear()
        self.active_area_id = None
        
        if document_id and self.area_storage_manager:
            # Load areas for the new page
            try:
                page_areas = self.area_storage_manager.get_areas_for_page(document_id, page)
                self.persistent_areas = page_areas
                
                self.logger.info(f"PAGE CHANGE: Loaded {len(page_areas)} areas for page {page} (was {old_count})")
                
                if page_areas:
                    for area_id, area in page_areas.items():
                        self.logger.debug(f"PAGE CHANGE: - Area {area_id} at {area.bbox} on page {area.page}")
                
            except Exception as e:
                self.logger.error(f"PAGE CHANGE: Error loading areas for page {page}: {e}")
                # On error, leave areas empty to prevent showing wrong-page areas
                self.persistent_areas = {}
        else:
            # No document ID or storage manager - keep areas empty
            if not document_id:
                self.logger.warning("PAGE CHANGE: No document ID available")
            if not self.area_storage_manager:
                self.logger.warning("PAGE CHANGE: No area_storage_manager available")
            self.persistent_areas = {}
        
        # Always update UI to reflect page change
        self.update()
    
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press for selection, resize, or move."""
        print(f"🔵 MOUSE PRESS: Event received at position {event.pos()}")
        
        if event.button() == Qt.LeftButton:
            pos = event.pos()
            print(f"🔵 MOUSE PRESS: Left button clicked at {pos}")
            
            # Check if cutting is enabled and we're in the right tab
            if not self.cutting_enabled:
                print(f"🔴 MOUSE PRESS: Cutting disabled, ignoring mouse press")
                self.logger.debug("CUTTING: Tool disabled, ignoring mouse press")
                return
                
            print(f"🟢 MOUSE PRESS: Cutting enabled, processing event")
                
            if not self.is_manual_validation_active():
                print(f"🔴 MOUSE PRESS: Not in manual validation tab, cutting disabled")
                self.logger.info("CUTTING: Not in manual validation tab, cutting disabled")
                # Still allow area interaction (resize/move) but not new selections
                # Fall through to check for existing area interaction
                pass
            else:
                print(f"🟢 MOUSE PRESS: In manual validation tab, cutting enabled")
            
            # Check if clicking on existing area
            clicked_area = self._get_area_at_position(pos.x(), pos.y())
            
            if clicked_area:
                # Convert area to widget coordinates for handle detection
                widget_rect = self._pdf_to_widget_coordinates(clicked_area.bbox)
                if widget_rect:
                    # Check if clicking on resize handle (using widget coordinates)
                    handle = self._get_resize_handle_at_widget_pos(widget_rect, pos.x(), pos.y())
                    
                    if handle:
                        # Start resize operation
                        self.interaction_mode = "resize"
                        self.resize_handle = handle
                        self.active_area_id = clicked_area.id
                        self.setCursor(self._get_resize_cursor(handle))
                        self.logger.info(f"RESIZE: Started resize operation on handle {handle} for area {clicked_area.id}")
                        
                    else:
                        # Check if inside area for move operation or just activation
                        wx1, wy1, wx2, wy2 = widget_rect
                        if wx1 <= pos.x() <= wx2 and wy1 <= pos.y() <= wy2:
                            # Just activate the area (don't start move immediately)
                            # Only start move if user drags significantly
                            self.active_area_id = clicked_area.id
                            self.move_start_pos = pos
                            self.move_start_bbox = clicked_area.bbox
                            self.setCursor(Qt.OpenHandCursor)  # Open hand to indicate grabbable
                            self.logger.info(f"ACTIVATE: Activated area {clicked_area.id}")
                            
                            # Emit activation signal
                            self.area_activated.emit(clicked_area.id)
                    
            else:
                # Clicked outside any area - deactivate current active area first
                if self.active_area_id:
                    self.logger.info(f"DEACTIVATE: Deactivating area {self.active_area_id}")
                    self.active_area_id = None
                    self.update()  # Force repaint to remove highlight
                
                # Check if we can start new selection (manual validation tab only)
                if self.is_manual_validation_active():
                    print("🔵 MOUSE: In manual validation tab - checking workflow requirements...")
                    # WORKFLOW SAFEGUARD: Check project and document requirements
                    if not self._check_workflow_requirements():
                        self.logger.warning("WORKFLOW: Cannot create areas - requirements not met")
                        print("🔴 MOUSE: Workflow requirements failed - area creation blocked!")
                        return
                    print("🟢 MOUSE: Workflow requirements passed - proceeding with area creation")
                    
                    # Start new selection
                    self.interaction_mode = "select"
                    self.is_selecting = True
                    self.selection_start = pos
                    self.selection_end = pos
                    self.selection_rect = QRectF(pos, pos)
                    self.setCursor(Qt.CrossCursor)
                    self.logger.debug("CUTTING: Started new area selection")
                else:
                    self.logger.info("CUTTING: New area selection blocked - not in manual validation tab")
                    # Still allow deactivation of areas outside manual validation tab
                    return
                
            self.update()
        
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move for selection, resize, or move."""
        pos = event.pos()
        
        if self.interaction_mode == "select" and self.is_selecting:
            # Update selection rectangle
            self.selection_end = pos
            self.selection_rect = QRectF(self.selection_start, self.selection_end).normalized()
            
            # Emit real-time preview if large enough
            if self.selection_rect.width() > 20 and self.selection_rect.height() > 20:
                self._emit_preview_update()
            
        elif self.interaction_mode == "resize" and self.active_area_id:
            # Handle resize
            self._handle_resize(pos)
            
        elif self.interaction_mode == "move" and self.active_area_id:
            # Handle move
            self._handle_move(pos)
            
        else:
            # Check if we need to start move operation (when user drags from clicked area)
            if (self.active_area_id and self.move_start_pos and 
                self.interaction_mode == "select"):  # Area is active but not in move mode yet
                
                # Calculate distance moved
                dx = pos.x() - self.move_start_pos.x()
                dy = pos.y() - self.move_start_pos.y()
                distance = (dx**2 + dy**2)**0.5
                
                # Start move operation if moved significantly (>5 pixels)
                if distance > 5:
                    self.interaction_mode = "move"
                    self.setCursor(Qt.ClosedHandCursor)
                    self.logger.info(f"MOVE: Started move operation for area {self.active_area_id} after drag distance {distance:.1f}")
            
            # Update cursor based on hover (for non-active areas)
            if not self.active_area_id or self.interaction_mode != "select":
                self._update_hover_cursor(pos)
        
        self.update()
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release to complete action."""
        if event.button() == Qt.LeftButton:
            self.logger.info(f"Mouse release event - interaction_mode: {self.interaction_mode}, is_selecting: {self.is_selecting}")
            
            if self.interaction_mode == "select" and self.is_selecting:
                # Complete area selection
                self.is_selecting = False
                
                if (self.selection_rect and 
                    self.selection_rect.width() > 10 and 
                    self.selection_rect.height() > 10):
                    self.logger.info(f"Valid selection detected: {self.selection_rect.width()}x{self.selection_rect.height()}")
                    self._handle_area_selection()
                else:
                    self.logger.warning(f"Selection too small or invalid: {self.selection_rect}")
                
                # Don't clear selection_rect immediately - let _handle_area_selection do it
                
            elif self.interaction_mode == "resize" and self.active_area_id:
                # Complete resize
                self._complete_resize()
                
            elif self.interaction_mode == "move" and self.active_area_id:
                # Complete move
                self._complete_move()
            
            # Reset interaction state (but don't clear selection_rect here)
            self.interaction_mode = "select"
            self.resize_handle = None
            self.move_start_pos = None
            self.move_start_bbox = None
            self.setCursor(Qt.ArrowCursor)
            
        self.update()
        super().mouseReleaseEvent(event)
    
    def paintEvent(self, event):
        """Draw selection rectangle and persistent areas."""
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        try:
            # Get current page from PDF viewer
            current_page = getattr(self.pdf_viewer, 'current_page', None)
            if current_page is None:
                self.logger.debug("PAINT: No current page information available")
                current_page = 0  # Default to page 0
            else:
                # Convert 0-based to 1-based for area comparison
                current_page = current_page + 1
            
            # Draw persistent areas filtered by current page
            if self.persistent_areas:
                page_areas = []
                other_page_areas = []
                
                for area_id, area in self.persistent_areas.items():
                    if area.page == current_page:
                        page_areas.append((area_id, area))
                    else:
                        other_page_areas.append((area_id, area))
                
                self.logger.debug(f"PAINT: Page {current_page} has {len(page_areas)} areas, {len(other_page_areas)} areas on other pages")
                
                # Only draw areas for the current page
                for area_id, area in page_areas:
                    self.logger.debug(f"PAINT: Drawing area {area_id} at {area.bbox} on page {area.page}")
                    self._draw_persistent_area(painter, area)
                
                # Log areas being filtered out for debugging
                if other_page_areas:
                    self.logger.debug(f"PAINT: Filtering out {len(other_page_areas)} areas from other pages")
                    for area_id, area in other_page_areas:
                        self.logger.debug(f"PAINT: - Filtered area {area_id} from page {area.page}")
            else:
                self.logger.debug("PAINT: No persistent areas to draw")
            
            # Draw current selection
            if self.selection_rect and self.selection_rect.isValid():
                self.logger.debug(f"PAINT: Drawing selection rect {self.selection_rect}")
                self._draw_selection_rect(painter)
                
        except Exception as e:
            self.logger.error(f"Error in paintEvent: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
    
    def _draw_persistent_area(self, painter: QPainter, area: VisualArea):
        """Draw a persistent area with type-specific styling."""
        try:
            self.logger.debug(f"DRAW: Converting coordinates for area {area.id} from PDF {area.bbox}")
            
            # Convert PDF coordinates to widget coordinates for display
            widget_rect = self._pdf_to_widget_coordinates(area.bbox)
            if not widget_rect:
                self.logger.warning(f"DRAW: Coordinate conversion failed for area {area.id}, using fallback rendering")
                # Use fallback coordinates instead of skipping the area entirely
                widget_rect = self._get_fallback_coordinates(area.bbox)
                if not widget_rect:
                    self.logger.error(f"DRAW: Fallback coordinates also failed for area {area.id}, skipping")
                    return
                
            x1, y1, x2, y2 = widget_rect
            rect = QRectF(x1, y1, x2 - x1, y2 - y1)
            
            self.logger.debug(f"DRAW: Drawing area {area.id} at widget coords {widget_rect}, rect: {rect}")
            
            color = QColor(area.color)
            is_active = (area.id == self.active_area_id)
            
            # Draw filled area with transparency - ALWAYS maintain transparency
            # Use slightly higher opacity for active areas but keep them semi-transparent
            fill_opacity = area.fill_opacity
            if is_active:
                fill_opacity = min(0.6, area.fill_opacity + 0.2)  # Slightly more visible but still transparent
            
            painter.setOpacity(fill_opacity)
            painter.fillRect(rect, color)
            
            # Draw border
            painter.setOpacity(1.0)
            pen = QPen(color, area.border_width if not is_active else area.border_width + 1)
            
            if area.border_glow or is_active:
                pen.setStyle(Qt.SolidLine)
                if is_active:
                    # Slightly brighter color for active area border, but not too much
                    pen.setColor(color.lighter(130))  # Reduced from 150 to 130
            
            painter.setPen(pen)
            painter.drawRect(rect)
            
            self.logger.debug(f"DRAW: Successfully drew area {area.id} with color {area.color}")
            
            # Draw resize handles if active
            if is_active:
                self._draw_resize_handles(painter, widget_rect)
                
        except Exception as e:
            self.logger.error(f"Error drawing area {area.id}: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
    
    def _draw_selection_rect(self, painter: QPainter):
        """Draw current selection rectangle."""
        if not self.selection_rect:
            return
            
        # Red glowing selection
        color = QColor("#FF0000")
        painter.setOpacity(0.3)
        painter.fillRect(self.selection_rect, color)
        
        painter.setOpacity(1.0)
        pen = QPen(color, 2, Qt.DashLine)
        painter.setPen(pen)
        painter.drawRect(self.selection_rect)
    
    def _draw_resize_handles(self, painter: QPainter, bbox: Tuple[float, float, float, float]):
        """Draw resize handles around an area."""
        x1, y1, x2, y2 = bbox
        handle_size = self.handle_size
        
        # Handle positions
        handles = [
            (x1 - handle_size/2, y1 - handle_size/2),  # top-left
            (x2 - handle_size/2, y1 - handle_size/2),  # top-right
            (x1 - handle_size/2, y2 - handle_size/2),  # bottom-left
            (x2 - handle_size/2, y2 - handle_size/2),  # bottom-right
            ((x1 + x2)/2 - handle_size/2, y1 - handle_size/2),  # top-center
            ((x1 + x2)/2 - handle_size/2, y2 - handle_size/2),  # bottom-center
            (x1 - handle_size/2, (y1 + y2)/2 - handle_size/2),  # left-center
            (x2 - handle_size/2, (y1 + y2)/2 - handle_size/2),  # right-center
        ]
        
        # Draw handles
        painter.setOpacity(1.0)
        painter.setPen(QPen(QColor("#000000"), 1))
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        
        for hx, hy in handles:
            painter.drawRect(QRectF(hx, hy, handle_size, handle_size))
    
    def _handle_area_selection(self):
        """Handle completed area selection."""
        self.logger.info("=== Starting area selection handler ===")
        
        if not self.pdf_viewer:
            self.logger.error("No PDF viewer available")
            return
            
        if not self.selection_rect:
            self.logger.error("No selection rect available")
            return
        
        # Get document information with detailed logging
        document_id = getattr(self.pdf_viewer, 'current_document_id', None)
        document_path = getattr(self.pdf_viewer, 'current_document_path', None)
        current_page_0based = getattr(self.pdf_viewer, 'current_page', -1)
        current_page_1based = current_page_0based + 1 if current_page_0based >= 0 else 1
        
        self.logger.info(f"AREA_CREATE: Document ID: '{document_id}'")
        self.logger.info(f"AREA_CREATE: Document path: '{document_path}'")
        self.logger.info(f"AREA_CREATE: Page (0-based): {current_page_0based}")
        self.logger.info(f"AREA_CREATE: Page (1-based): {current_page_1based}")
        
        # CRITICAL GUI INTEGRATION CHECKPOINTS
        self.logger.info("=" * 50)
        self.logger.info("AREA_CREATE: GUI INTEGRATION CHECKPOINT ANALYSIS")
        self.logger.info("=" * 50)
        
        # Checkpoint 1: Storage manager availability
        storage_available = self.area_storage_manager is not None
        self.logger.info(f"CHECKPOINT 1: Storage manager available: {storage_available}")
        
        # Checkpoint 2: Project manager availability  
        project_manager_available = False
        if self.area_storage_manager and hasattr(self.area_storage_manager, 'project_manager'):
            project_manager_available = self.area_storage_manager.project_manager is not None
        self.logger.info(f"CHECKPOINT 2: Project manager available: {project_manager_available}")
        
        # Checkpoint 3: Current project exists
        current_project_exists = False
        current_project = None
        if project_manager_available:
            pm = self.area_storage_manager.project_manager
            if hasattr(pm, 'get_current_project'):
                current_project = pm.get_current_project()
                current_project_exists = current_project is not None
        self.logger.info(f"CHECKPOINT 3: Current project exists: {current_project_exists}")
        
        # Checkpoint 4: Document ID matches project
        document_id_matches = False
        if current_project_exists and document_id:
            documents = current_project.get('documents', [])
            doc_ids = [doc.get('id') for doc in documents]
            document_id_matches = document_id in doc_ids
            self.logger.info(f"CHECKPOINT 4: Document ID '{document_id}' matches project: {document_id_matches}")
            self.logger.info(f"CHECKPOINT 4: Project document IDs: {doc_ids}")
        else:
            self.logger.info(f"CHECKPOINT 4: Cannot check document ID match (no project or no document ID)")
        
        # OVERALL READINESS CHECK
        ready_to_save = storage_available and project_manager_available and current_project_exists and document_id_matches
        self.logger.info(f"🎯 OVERALL READINESS: Ready to save areas: {ready_to_save}")
        
        if not ready_to_save:
            self.logger.error("❌ AREA SAVE WILL FAIL - Missing requirements:")
            if not storage_available:
                self.logger.error("   - No area storage manager")
            if not project_manager_available:
                self.logger.error("   - No project manager")  
            if not current_project_exists:
                self.logger.error("   - No current project")
            if not document_id_matches:
                self.logger.error("   - Document ID mismatch")
        
        self.logger.info("=" * 50)
        
        if not document_id:
            self.logger.info("AREA_CREATE: No document ID set, finding the one that matches the displayed document")
            
            # Find the document ID in the project that corresponds to the currently displayed document
            if self.area_storage_manager and hasattr(self.area_storage_manager, 'project_manager'):
                try:
                    current_project = self.area_storage_manager.project_manager.get_current_project()
                    if current_project and document_path:
                        documents = current_project.get('documents', [])
                        
                        # Look for a document with matching file path
                        for doc in documents:
                            if doc.get('file_path') == document_path:
                                document_id = doc.get('id')
                                self.logger.info(f"AREA_CREATE: Found matching document ID: '{document_id}' for path: {document_path}")
                                break
                        
                        # If not found by exact path, try by filename
                        if not document_id and document_path:
                            filename = Path(document_path).name
                            for doc in documents:
                                doc_filename = Path(doc.get('file_path', '')).name
                                if doc_filename == filename:
                                    document_id = doc.get('id')
                                    self.logger.info(f"AREA_CREATE: Found matching document ID by filename: '{document_id}' for: {filename}")
                                    break
                        
                except Exception as e:
                    self.logger.error(f"AREA_CREATE: Error finding document ID: {e}")
            
            # If still no document ID found, create a simple fallback based on displayed document
            if not document_id:
                if document_path:
                    filename = Path(document_path).stem  # filename without extension
                    document_id = f"doc_{filename}"
                    self.logger.info(f"AREA_CREATE: Using fallback document ID based on filename: '{document_id}'")
                else:
                    document_id = "doc_current"
                    self.logger.warning("AREA_CREATE: Using generic fallback document ID: 'doc_current'")
        
        self.logger.info(f"AREA_CREATE: Using document ID: '{document_id}' for the currently displayed document")
        
        # Check if we should bypass dialog for testing
        import os
        bypass_dialog = os.environ.get('TORE_BYPASS_DIALOG', '').lower() == 'true'
        
        if bypass_dialog:
            self.logger.info("BYPASSING dialog for testing - creating IMAGE area")
            area_type = AreaType.IMAGE
            
            # Create new visual area
            self.logger.info("Creating visual area...")
            area = self._create_visual_area(area_type, document_id, document_path)
            self.logger.info(f"Visual area created: {area.id}")
            
            # Add to persistent areas
            self.persistent_areas[area.id] = area
            self.active_area_id = area.id
            self.logger.info(f"Area added to persistent areas. Total: {len(self.persistent_areas)}")
            
            # Save to storage with enhanced debugging
            if self.area_storage_manager:
                self.logger.info("=== CRITICAL SAVE OPERATION ===")
                self.logger.info(f"Saving area {area.id} to storage for document '{document_id}'")
                
                # Debug project state before save
                project_data = self.area_storage_manager.project_manager.get_current_project()
                if project_data:
                    docs = project_data.get('documents', [])
                    self.logger.info(f"Project has {len(docs)} documents before save")
                    for doc in docs:
                        if doc.get('id') == document_id:
                            existing_areas = doc.get('visual_areas', {})
                            self.logger.info(f"Document '{document_id}' has {len(existing_areas)} existing areas")
                            break
                else:
                    self.logger.error("No current project available for save!")
                
                # Attempt save
                save_success = self.area_storage_manager.save_area(document_id, area)
                self.logger.info(f"Area save result: {save_success}")
                
                # Debug project state after save
                if save_success:
                    project_data = self.area_storage_manager.project_manager.get_current_project()
                    if project_data:
                        docs = project_data.get('documents', [])
                        for doc in docs:
                            if doc.get('id') == document_id:
                                new_areas = doc.get('visual_areas', {})
                                self.logger.info(f"Document '{document_id}' now has {len(new_areas)} areas after save")
                                if area.id in new_areas:
                                    self.logger.info(f"✅ Area {area.id} successfully added to project data")
                                else:
                                    self.logger.error(f"❌ Area {area.id} NOT found in project data after save")
                                break
                
                # Force project save to disk
                if hasattr(self.area_storage_manager.project_manager, 'save_current_project'):
                    self.logger.info("Force saving project to disk...")
                    disk_save_result = self.area_storage_manager.project_manager.save_current_project()
                    self.logger.info(f"Project disk save result: {disk_save_result}")
                    
                    if not disk_save_result:
                        self.logger.error("❌ CRITICAL: Project failed to save to disk - areas will be lost!")
                
                self.logger.info("=== SAVE OPERATION COMPLETE ===")
            else:
                self.logger.warning("No area storage manager available")
            
            # Clear selection rect now that we've used it
            self.selection_rect = None
            
            # Force repaint to show the new area immediately
            self.logger.info("Forcing widget update...")
            self.update()
            
            # Emit signal
            print(f"🟢 AREA CREATION: About to emit area_selected signal")
            print(f"🟢 AREA CREATION: Area data: {area.to_dict()}")
            self.area_selected.emit(area.to_dict())
            print(f"🟢 AREA CREATION: Signal emitted successfully")
            self.logger.info(f"SUCCESS: Created area {area.id} of type {area_type.value} at {area.bbox}")
            
        else:
            # Show area type selection dialog
            self.logger.info("Showing area type selection dialog...")
            try:
                from ..dialogs.area_type_dialog import AreaTypeDialog
                dialog = AreaTypeDialog(self)
                self.logger.info("Dialog created successfully")
                
                result = dialog.exec_()
                self.logger.info(f"Dialog result: {result} (Accepted={dialog.Accepted})")
                
                if result == dialog.Accepted:
                    area_type = dialog.get_selected_type()
                    self.logger.info(f"Selected area type: {area_type}")
                    
                    if area_type:
                        # Create new visual area
                        self.logger.info("Creating visual area...")
                        area = self._create_visual_area(area_type, document_id, document_path)
                        self.logger.info(f"Visual area created: {area.id}")
                        
                        # Add to persistent areas
                        self.persistent_areas[area.id] = area
                        self.active_area_id = area.id
                        self.logger.info(f"Area added to persistent areas. Total: {len(self.persistent_areas)}")
                        
                        # Save to storage with enhanced debugging
                        if self.area_storage_manager:
                            self.logger.info("=== CRITICAL SAVE OPERATION (DIALOG) ===")
                            self.logger.info(f"Saving area {area.id} to storage for document '{document_id}'")
                            
                            save_success = self.area_storage_manager.save_area(document_id, area)
                            self.logger.info(f"Area save result: {save_success}")
                            
                            # Force project save to disk
                            if hasattr(self.area_storage_manager.project_manager, 'save_current_project'):
                                self.logger.info("Force saving project to disk...")
                                disk_save_result = self.area_storage_manager.project_manager.save_current_project()
                                self.logger.info(f"Project disk save result: {disk_save_result}")
                                
                                if not disk_save_result:
                                    self.logger.error("❌ CRITICAL: Project failed to save to disk - areas will be lost!")
                            
                            self.logger.info("=== SAVE OPERATION COMPLETE (DIALOG) ===")
                        else:
                            self.logger.warning("No area storage manager available")
                        
                        # Clear selection rect now that we've used it
                        self.selection_rect = None
                        
                        # Force repaint to show the new area immediately
                        self.logger.info("Forcing widget update...")
                        self.update()
                        
                        # Emit signal
                        self.area_selected.emit(area.to_dict())
                        self.logger.info(f"SUCCESS: Created area {area.id} of type {area_type.value} at {area.bbox}")
                    else:
                        self.logger.warning("No area type selected")
                        self.selection_rect = None
                else:
                    self.logger.info("Dialog was canceled or rejected")
                    self.selection_rect = None
                    
            except Exception as e:
                self.logger.error(f"Error in area selection handler: {e}")
                import traceback
                self.logger.error(f"Traceback: {traceback.format_exc()}")
                self.selection_rect = None
        
        self.logger.info("=== Area selection handler complete ===")
        self.update()  # Force final update
    
    def _create_visual_area(self, area_type: AreaType, document_id: str, document_path: str) -> VisualArea:
        """Create VisualArea from current selection."""
        import uuid
        
        # Convert selection to PDF coordinates
        bbox = self._convert_to_pdf_coordinates(self.selection_rect)
        
        # Calculate page number with detailed logging
        current_page_0based = self.pdf_viewer.current_page
        page_for_storage = current_page_0based + 1  # Convert to 1-based for storage
        
        # CRITICAL DEBUG for Issue #47
        self.logger.warning(f"AREA_CREATE PAGE DEBUG: pdf_viewer.current_page = {current_page_0based}")
        self.logger.warning(f"AREA_CREATE PAGE DEBUG: Page for storage = {page_for_storage}")
        self.logger.info(f"AREA_CREATE: Converting page: {current_page_0based} (0-based) → {page_for_storage} (1-based for storage)")
        
        area_data = {
            'id': f"area_{uuid.uuid4().hex[:8]}",
            'document_id': document_id,
            'type': area_type.value,
            'bbox': bbox,
            'page': page_for_storage,
            'selection_rect': [
                int(self.selection_rect.x()),
                int(self.selection_rect.y()),
                int(self.selection_rect.width()),
                int(self.selection_rect.height())
            ],
            'created_at': datetime.now().isoformat(),
            'status': 'selected'
        }
        
        self.logger.info(f"AREA_CREATE: Area will be stored with page={page_for_storage}")
        
        return VisualArea.from_area_data(area_data)
    
    def _convert_to_pdf_coordinates(self, rect: QRectF) -> Tuple[float, float, float, float]:
        """Convert widget coordinates to PDF coordinates."""
        if not self.pdf_viewer or not self.pdf_viewer.current_document:
            return (rect.x(), rect.y(), rect.x() + rect.width(), rect.y() + rect.height())
        
        try:
            # Use PDF viewer's coordinate conversion
            zoom_factor = getattr(self.pdf_viewer, 'current_zoom_factor', 1.0)
            
            x1 = rect.x() / zoom_factor
            y1 = rect.y() / zoom_factor
            x2 = (rect.x() + rect.width()) / zoom_factor
            y2 = (rect.y() + rect.height()) / zoom_factor
            
            return (x1, y1, x2, y2)
            
        except Exception as e:
            self.logger.error(f"Error converting coordinates: {e}")
            return (rect.x(), rect.y(), rect.x() + rect.width(), rect.y() + rect.height())
    
    def _pdf_to_widget_coordinates(self, bbox: Tuple[float, float, float, float]) -> Optional[Tuple[float, float, float, float]]:
        """Convert PDF coordinates back to widget coordinates for display."""
        # Log the input for debugging
        self.logger.debug(f"COORD_CONVERT: Input PDF bbox: {bbox}")
        
        if not self.pdf_viewer:
            self.logger.warning(f"COORD_CONVERT: No PDF viewer available")
            return self._get_fallback_coordinates(bbox)
            
        if not self.pdf_viewer.current_document:
            self.logger.warning(f"COORD_CONVERT: No current document in PDF viewer")
            return self._get_fallback_coordinates(bbox)
        
        try:
            # Use PDF viewer's zoom factor
            zoom_factor = getattr(self.pdf_viewer, 'current_zoom_factor', 1.0)
            
            # Log zoom factor for debugging
            self.logger.debug(f"COORD_CONVERT: Zoom factor: {zoom_factor}")
            
            x1, y1, x2, y2 = bbox
            
            # Convert back to widget coordinates
            widget_x1 = x1 * zoom_factor
            widget_y1 = y1 * zoom_factor
            widget_x2 = x2 * zoom_factor
            widget_y2 = y2 * zoom_factor
            
            widget_coords = (widget_x1, widget_y1, widget_x2, widget_y2)
            self.logger.debug(f"COORD_CONVERT: Output widget coords: {widget_coords}")
            
            # Validate that coordinates are reasonable
            if self._coords_within_reasonable_bounds(widget_coords):
                return widget_coords
            else:
                self.logger.warning(f"COORD_CONVERT: Coordinates outside reasonable bounds, using fallback")
                return self._get_fallback_coordinates(bbox)
            
        except Exception as e:
            self.logger.error(f"COORD_CONVERT: Error converting coordinates: {e}")
            import traceback
            self.logger.error(f"COORD_CONVERT: Traceback: {traceback.format_exc()}")
            return self._get_fallback_coordinates(bbox)
    
    def _get_area_at_position(self, x: float, y: float) -> Optional[VisualArea]:
        """Get area at given position."""
        for area in self.persistent_areas.values():
            # Convert area's PDF coordinates to widget coordinates for checking
            widget_rect = self._pdf_to_widget_coordinates(area.bbox)
            if widget_rect:
                wx1, wy1, wx2, wy2 = widget_rect
                if wx1 <= x <= wx2 and wy1 <= y <= wy2:
                    return area
        return None
    
    def _get_resize_handle_at_widget_pos(self, widget_rect: Tuple[float, float, float, float], 
                                       x: float, y: float) -> Optional[str]:
        """Get resize handle at given widget coordinates."""
        x1, y1, x2, y2 = widget_rect
        handle_size = self.handle_size
        
        # Check corners first
        if abs(x - x1) <= handle_size and abs(y - y1) <= handle_size:
            return "top_left"
        elif abs(x - x2) <= handle_size and abs(y - y1) <= handle_size:
            return "top_right"
        elif abs(x - x1) <= handle_size and abs(y - y2) <= handle_size:
            return "bottom_left"
        elif abs(x - x2) <= handle_size and abs(y - y2) <= handle_size:
            return "bottom_right"
        
        # Check edges
        elif abs(x - x1) <= handle_size and y1 <= y <= y2:
            return "left"
        elif abs(x - x2) <= handle_size and y1 <= y <= y2:
            return "right"
        elif abs(y - y1) <= handle_size and x1 <= x <= x2:
            return "top"
        elif abs(y - y2) <= handle_size and x1 <= x <= x2:
            return "bottom"
        
        return None
    
    def _get_resize_cursor(self, handle: str) -> Qt.CursorShape:
        """Get appropriate cursor for resize handle."""
        cursors = {
            "top_left": Qt.SizeFDiagCursor,
            "top_right": Qt.SizeBDiagCursor,
            "bottom_left": Qt.SizeBDiagCursor,
            "bottom_right": Qt.SizeFDiagCursor,
            "top": Qt.SizeVerCursor,
            "bottom": Qt.SizeVerCursor,
            "left": Qt.SizeHorCursor,
            "right": Qt.SizeHorCursor
        }
        return cursors.get(handle, Qt.ArrowCursor)
    
    def _update_hover_cursor(self, pos: QPointF):
        """Update cursor based on hover position."""
        area = self._get_area_at_position(pos.x(), pos.y())
        
        if area:
            handle = area.get_resize_handle_at(pos.x(), pos.y(), self.handle_size)
            if handle:
                self.setCursor(self._get_resize_cursor(handle))
            elif area.is_point_inside(pos.x(), pos.y()):
                self.setCursor(Qt.OpenHandCursor)
            else:
                self.setCursor(Qt.ArrowCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
    
    def _handle_resize(self, pos: QPointF):
        """Handle resize operation."""
        if not self.active_area_id or not self.resize_handle:
            return
            
        area = self.persistent_areas.get(self.active_area_id)
        if not area:
            return
        
        self.logger.debug(f"RESIZE: Handle {self.resize_handle} at widget pos {pos.x()}, {pos.y()}")
        
        # Convert current area bbox to widget coordinates
        widget_rect = self._pdf_to_widget_coordinates(area.bbox)
        if not widget_rect:
            return
            
        wx1, wy1, wx2, wy2 = widget_rect
        
        # Update widget coordinates based on resize handle
        if "left" in self.resize_handle:
            wx1 = pos.x()
        elif "right" in self.resize_handle:
            wx2 = pos.x()
            
        if "top" in self.resize_handle:
            wy1 = pos.y()
        elif "bottom" in self.resize_handle:
            wy2 = pos.y()
        
        # Ensure minimum size in widget coordinates
        min_size = 20
        if wx2 - wx1 < min_size:
            if "left" in self.resize_handle:
                wx1 = wx2 - min_size
            else:
                wx2 = wx1 + min_size
                
        if wy2 - wy1 < min_size:
            if "top" in self.resize_handle:
                wy1 = wy2 - min_size
            else:
                wy2 = wy1 + min_size
        
        # Convert back to PDF coordinates and update area
        zoom_factor = getattr(self.pdf_viewer, 'current_zoom_factor', 1.0)
        pdf_x1 = wx1 / zoom_factor
        pdf_y1 = wy1 / zoom_factor
        pdf_x2 = wx2 / zoom_factor
        pdf_y2 = wy2 / zoom_factor
        
        self.logger.debug(f"RESIZE: Updated PDF bbox to ({pdf_x1}, {pdf_y1}, {pdf_x2}, {pdf_y2})")
        area.update_bbox((pdf_x1, pdf_y1, pdf_x2, pdf_y2))
        
        # Force immediate widget refresh to show the new size and remove old visual
        self.update()
    
    def _handle_move(self, pos: QPointF):
        """Handle move operation."""
        if not self.active_area_id or not self.move_start_pos or not self.move_start_bbox:
            return
            
        area = self.persistent_areas.get(self.active_area_id)
        if not area:
            return
        
        # Calculate movement delta in widget coordinates
        dx = pos.x() - self.move_start_pos.x()
        dy = pos.y() - self.move_start_pos.y()
        
        self.logger.debug(f"MOVE: Delta ({dx}, {dy}) from start pos {self.move_start_pos.x()}, {self.move_start_pos.y()}")
        
        # Convert delta to PDF coordinates
        zoom_factor = getattr(self.pdf_viewer, 'current_zoom_factor', 1.0)
        pdf_dx = dx / zoom_factor
        pdf_dy = dy / zoom_factor
        
        # Apply to original PDF bbox
        x1, y1, x2, y2 = self.move_start_bbox
        new_bbox = (x1 + pdf_dx, y1 + pdf_dy, x2 + pdf_dx, y2 + pdf_dy)
        
        self.logger.debug(f"MOVE: Updated PDF bbox to {new_bbox}")
        area.update_bbox(new_bbox)
        
        # Force immediate widget refresh to show the new position and remove old visual
        self.update()
    
    def _complete_resize(self):
        """Complete resize operation and save."""
        if self.active_area_id and self.area_storage_manager:
            area = self.persistent_areas.get(self.active_area_id)
            if area:
                document_id = getattr(self.pdf_viewer, 'current_document_id', None)
                if document_id:
                    self.logger.info(f"RESIZE_COMPLETE: Saving resized area {area.id} with bbox {area.bbox}")
                    update_success = self.area_storage_manager.update_area(document_id, area)
                    self.logger.info(f"RESIZE_COMPLETE: Update result: {update_success}")
                    
                    if update_success:
                        self.area_modified.emit(area.id, area.to_dict())
                        self.logger.info(f"RESIZE_COMPLETE: ✅ Successfully updated area {area.id}")
                    else:
                        self.logger.error(f"RESIZE_COMPLETE: ❌ Failed to update area {area.id}")
                else:
                    self.logger.error("RESIZE_COMPLETE: No document ID available")
            else:
                self.logger.error(f"RESIZE_COMPLETE: Area {self.active_area_id} not found in persistent_areas")
        else:
            self.logger.error("RESIZE_COMPLETE: Missing active_area_id or area_storage_manager")
    
    def _complete_move(self):
        """Complete move operation and save."""
        if self.active_area_id and self.area_storage_manager:
            area = self.persistent_areas.get(self.active_area_id)
            if area:
                document_id = getattr(self.pdf_viewer, 'current_document_id', None)
                if document_id:
                    self.logger.info(f"MOVE_COMPLETE: Saving moved area {area.id} with bbox {area.bbox}")
                    update_success = self.area_storage_manager.update_area(document_id, area)
                    self.logger.info(f"MOVE_COMPLETE: Update result: {update_success}")
                    
                    if update_success:
                        self.area_modified.emit(area.id, area.to_dict())
                        self.logger.info(f"MOVE_COMPLETE: ✅ Successfully updated area {area.id}")
                    else:
                        self.logger.error(f"MOVE_COMPLETE: ❌ Failed to update area {area.id}")
                else:
                    self.logger.error("MOVE_COMPLETE: No document ID available")
            else:
                self.logger.error(f"MOVE_COMPLETE: Area {self.active_area_id} not found in persistent_areas")
        else:
            self.logger.error("MOVE_COMPLETE: Missing active_area_id or area_storage_manager")
    
    def _emit_preview_update(self):
        """Emit real-time preview update."""
        if self.selection_rect and self.pdf_viewer:
            # Get document information with page debugging
            document_id = getattr(self.pdf_viewer, 'current_document_id', None)
            document_path = getattr(self.pdf_viewer, 'current_document_path', None)
            current_page_0based = getattr(self.pdf_viewer, 'current_page', 0)
            current_page_1based = current_page_0based + 1
            
            self.logger.debug(f"PREVIEW: Page conversion: {current_page_0based} (0-based) → {current_page_1based} (1-based)")
            
            # Convert to PDF coordinates for preview
            bbox = self._convert_to_pdf_coordinates(self.selection_rect)
            
            preview_data = {
                'id': 'preview_area',
                'document_id': document_id,
                'document_path': document_path,
                'type': 'PREVIEW',
                'bbox': bbox,
                'page': current_page_1based,
                'selection_rect': [
                    int(self.selection_rect.x()),
                    int(self.selection_rect.y()),
                    int(self.selection_rect.width()),
                    int(self.selection_rect.height())
                ],
                'status': 'preview'
            }
            
            # Emit preview signal
            self.area_preview_update.emit(preview_data)
    
    def delete_active_area(self):
        """Delete the currently active area."""
        if not self.active_area_id:
            return
            
        area = self.persistent_areas.get(self.active_area_id)
        if area:
            # Remove from persistent areas
            del self.persistent_areas[self.active_area_id]
            
            # Delete from storage
            if self.area_storage_manager:
                document_id = getattr(self.pdf_viewer, 'current_document_id', None)
                if document_id:
                    self.area_storage_manager.delete_area(document_id, self.active_area_id)
            
            # Emit signal
            self.area_deleted.emit(self.active_area_id)
            self.active_area_id = None
            self.update()
    
    def keyPressEvent(self, event):
        """Handle key press events."""
        if event.key() == Qt.Key_Delete and self.active_area_id:
            self.delete_active_area()
        
        super().keyPressEvent(event)
    def _check_workflow_requirements(self) -> bool:
        """Check if essential requirements are met for area creation."""
        self.logger.info("🔍 WORKFLOW CHECK: Verifying essential requirements for area creation")
        
        # Check 1: Area storage manager available (essential for saving)
        self.logger.info(f"🔍 CHECK 1: Area storage manager = {self.area_storage_manager is not None}")
        if not self.area_storage_manager:
            self.logger.error("WORKFLOW: ❌ No area storage manager - technical issue")
            print("🔴 WORKFLOW FAILURE: No area storage manager available!")
            self._show_workflow_error("Technical Issue", 
                "Area storage system not available. Please restart the application.")
            return False
        
        # Check 2: Project manager available (essential for saving)
        has_project_manager = hasattr(self.area_storage_manager, 'project_manager') and self.area_storage_manager.project_manager
        self.logger.info(f"🔍 CHECK 2: Project manager = {has_project_manager}")
        if not has_project_manager:
            self.logger.error("WORKFLOW: ❌ No project manager - technical issue")
            print("🔴 WORKFLOW FAILURE: No project manager available!")
            self._show_workflow_error("Technical Issue",
                "Project management system not available. Please restart the application.")
            return False
        
        # Check 3: Current project loaded (needed for saving areas)
        try:
            current_project = self.area_storage_manager.project_manager.get_current_project()
            self.logger.info(f"🔍 CHECK 3: Current project = {current_project is not None}")
            if current_project:
                documents = current_project.get('documents', [])
                self.logger.info(f"🔍 CHECK 3: Project has {len(documents)} documents")
                print(f"🟢 WORKFLOW: Project loaded with {len(documents)} documents")
            
            if not current_project:
                self.logger.error("WORKFLOW: ❌ No project loaded")
                print("🔴 WORKFLOW FAILURE: No project is currently loaded!")
                self._show_workflow_error("No Project Loaded", 
                    "Please open a project before creating areas.\n\n" +
                    "Go to Project Management tab and open an existing project.")
                return False
        except Exception as e:
            self.logger.error(f"WORKFLOW: ❌ Error checking project: {e}")
            print(f"🔴 WORKFLOW FAILURE: Error checking project: {e}")
            return False
        
        # That's it! User can cut on whatever document is displayed
        # Document selection is just for navigation, not permission control
        self.logger.info("🟢 WORKFLOW: ✅ Essential requirements met - ready to create areas")
        self.logger.info("🟢 WORKFLOW: User can cut on whatever document is currently displayed")
        print("🟢 WORKFLOW SUCCESS: All checks passed - areas can be created!")
        return True
    
    def _show_workflow_error(self, title: str, message: str):
        """Show workflow error message to user."""
        try:
            from ..qt_compat import QMessageBox
            
            # Find the main window
            main_window = self.parent()
            while main_window and not hasattr(main_window, 'statusBar'):
                main_window = main_window.parent()
            
            if main_window:
                QMessageBox.warning(main_window, title, message)
            else:
                self.logger.error(f"WORKFLOW ERROR: {title} - {message}")
        except Exception as e:
            self.logger.error(f"Error showing workflow error: {e}")
    
    def _coords_within_reasonable_bounds(self, coords: Tuple[float, float, float, float]) -> bool:
        """Check if coordinates are within reasonable bounds for the widget."""
        try:
            x1, y1, x2, y2 = coords
            
            # Check for negative coordinates or extremely large values
            if x1 < -100 or y1 < -100 or x2 > 10000 or y2 > 10000:
                self.logger.warning(f"COORD_CHECK: Coordinates outside reasonable bounds: {coords}")
                return False
            
            # Check if rectangle has reasonable size
            width = abs(x2 - x1)
            height = abs(y2 - y1)
            
            if width < 1 or height < 1:
                self.logger.warning(f"COORD_CHECK: Rectangle too small: {width}x{height}")
                return False
            
            if width > 5000 or height > 5000:
                self.logger.warning(f"COORD_CHECK: Rectangle too large: {width}x{height}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"COORD_CHECK: Error checking coordinate bounds: {e}")
            return False
    
    def _get_fallback_coordinates(self, bbox: Tuple[float, float, float, float]) -> Optional[Tuple[float, float, float, float]]:
        """Get fallback coordinates when normal conversion fails."""
        try:
            self.logger.debug(f"FALLBACK: Attempting fallback coordinates for bbox: {bbox}")
            
            # Try to get widget dimensions
            widget_width = self.width()
            widget_height = self.height()
            
            if widget_width <= 0 or widget_height <= 0:
                self.logger.warning(f"FALLBACK: Invalid widget dimensions: {widget_width}x{widget_height}")
                return None
            
            # Assume standard PDF page size (612x792 points) and scale to widget
            pdf_width = 612.0
            pdf_height = 792.0
            
            scale_x = widget_width / pdf_width
            scale_y = widget_height / pdf_height
            
            x1, y1, x2, y2 = bbox
            
            # Scale coordinates
            fallback_x1 = x1 * scale_x
            fallback_y1 = y1 * scale_y
            fallback_x2 = x2 * scale_x
            fallback_y2 = y2 * scale_y
            
            fallback_coords = (fallback_x1, fallback_y1, fallback_x2, fallback_y2)
            
            # Validate fallback coordinates
            if self._coords_within_reasonable_bounds(fallback_coords):
                self.logger.debug(f"FALLBACK: Successfully generated fallback coordinates: {fallback_coords}")
                return fallback_coords
            else:
                self.logger.warning(f"FALLBACK: Fallback coordinates also invalid: {fallback_coords}")
                
                # Try a simple default rectangle in the center of the widget
                center_x = widget_width / 2
                center_y = widget_height / 2
                default_size = min(100, widget_width / 4, widget_height / 4)
                
                default_coords = (
                    center_x - default_size / 2,
                    center_y - default_size / 2,
                    center_x + default_size / 2,
                    center_y + default_size / 2
                )
                
                self.logger.debug(f"FALLBACK: Using default center rectangle: {default_coords}")
                return default_coords
            
        except Exception as e:
            self.logger.error(f"FALLBACK: Error generating fallback coordinates: {e}")
            return None
