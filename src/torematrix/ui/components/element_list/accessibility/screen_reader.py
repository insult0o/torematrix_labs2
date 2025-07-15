"""
Screen Reader Support for Hierarchical Element List

Provides comprehensive screen reader accessibility including
announcements, focus management, and structured navigation.
"""

import logging
from typing import Optional, Dict, Any, List
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QAccessible

logger = logging.getLogger(__name__)


class ScreenReaderSupport(QObject):
    """
    Screen reader support for hierarchical element list
    
    Provides announcements, focus management, and accessible navigation
    for users with screen readers and other assistive technologies.
    """
    
    # Signals
    announcement_requested = pyqtSignal(str, int)  # message, priority
    focus_changed = pyqtSignal(str)  # element_id
    
    def __init__(self, element_list_widget: QWidget, parent: Optional[QObject] = None):
        super().__init__(parent)
        
        self.element_list = element_list_widget
        self.enable_announcements = True
        self.announcement_delay = 500  # ms
        
        # State tracking
        self._last_announced_element = None
        self._pending_announcements = []
        self._announcement_timer = QTimer()
        self._announcement_timer.setSingleShot(True)
        self._announcement_timer.timeout.connect(self._process_announcements)
        
        # Setup accessibility
        self._setup_accessibility()
        
        logger.info("ScreenReaderSupport initialized")
    
    def _setup_accessibility(self):
        """Setup accessibility features"""
        if hasattr(self.element_list, 'setAccessibleName'):
            self.element_list.setAccessibleName("Hierarchical Element List")
        
        if hasattr(self.element_list, 'setAccessibleDescription'):
            self.element_list.setAccessibleDescription(
                "Tree view of document elements. Use arrow keys to navigate, "
                "Space to select, Enter to expand/collapse."
            )
    
    def announce_element_selected(self, element_id: str, element_data: Dict[str, Any]):
        """Announce element selection to screen reader"""
        if not self.enable_announcements:
            return
        
        element_type = element_data.get('type', 'element')
        element_name = element_data.get('name', element_id)
        level = element_data.get('depth', 0)
        
        message = f"Selected {element_type}: {element_name}, level {level + 1}"
        
        # Add state information
        if element_data.get('has_children'):
            expanded = element_data.get('expanded', False)
            state = "expanded" if expanded else "collapsed"
            message += f", {state}"
        
        self._queue_announcement(message, QAccessible.Announcement)
    
    def announce_tree_structure_change(self, change_type: str, affected_count: int):
        """Announce changes to tree structure"""
        if not self.enable_announcements:
            return
        
        if change_type == "expanded":
            message = f"Expanded showing {affected_count} child elements"
        elif change_type == "collapsed":
            message = f"Collapsed hiding {affected_count} child elements"
        elif change_type == "filtered":
            message = f"Filter applied, showing {affected_count} elements"
        else:
            message = f"Tree updated, {affected_count} elements visible"
        
        self._queue_announcement(message, QAccessible.Announcement)
    
    def announce_navigation_context(self, element_path: List[str]):
        """Announce current navigation context"""
        if not self.enable_announcements or not element_path:
            return
        
        if len(element_path) == 1:
            message = f"At root level: {element_path[0]}"
        else:
            parent_path = " > ".join(element_path[:-1])
            current = element_path[-1]
            message = f"In {parent_path}: {current}"
        
        self._queue_announcement(message, QAccessible.Announcement)
    
    def _queue_announcement(self, message: str, priority: int):
        """Queue announcement for processing"""
        self._pending_announcements.append((message, priority))
        
        if not self._announcement_timer.isActive():
            self._announcement_timer.start(self.announcement_delay)
    
    def _process_announcements(self):
        """Process queued announcements"""
        if not self._pending_announcements:
            return
        
        # Get highest priority announcement
        message, priority = max(self._pending_announcements, key=lambda x: x[1])
        self._pending_announcements.clear()
        
        # Emit announcement
        self.announcement_requested.emit(message, priority)
        
        # Use QAccessible to announce
        try:
            QAccessible.updateAccessibility(self.element_list, 0, QAccessible.Event.Announcement)
        except Exception as e:
            logger.warning(f"Failed to send accessibility announcement: {e}")