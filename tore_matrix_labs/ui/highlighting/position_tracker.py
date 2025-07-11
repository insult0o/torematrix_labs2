#!/usr/bin/env python3
"""
Position Tracker for TORE Matrix Labs Highlighting System
Tracks and synchronizes cursor/selection positions between text and PDF.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any, Callable
from PyQt5.QtCore import QObject, pyqtSignal, QTimer


class PositionTracker(QObject):
    """Tracks and synchronizes cursor/selection positions between text and PDF."""
    
    # Signals
    cursor_position_changed = pyqtSignal(int)  # text_position
    selection_changed = pyqtSignal(int, int)   # start_pos, end_pos
    highlight_activated = pyqtSignal(str)      # highlight_id
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # Core components
        self.highlighting_engine = None
        
        # State tracking
        self.active_highlights: Dict[str, Dict[str, Any]] = {}
        self.current_cursor_position = 0
        self.current_selection = (0, 0)
        self.cursor_sync_enabled = True
        self.selection_sync_enabled = True
        
        # Performance optimization
        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self._process_pending_updates)
        self.pending_updates = []
        self.update_delay = 50  # milliseconds
        
        # Statistics
        self.stats = {
            'cursor_updates': 0,
            'selection_updates': 0,
            'highlight_activations': 0,
            'sync_operations': 0
        }
        
        self.logger.info("Position tracker initialized")
    
    def set_engine(self, highlighting_engine):
        """Set the highlighting engine reference."""
        self.highlighting_engine = highlighting_engine
        self.logger.info("POSITION_TRACKER: Engine reference set")
    
    def track_highlight(self, highlight_id: str, highlight_info: Dict[str, Any]):
        """Track a new highlight."""
        try:
            self.active_highlights[highlight_id] = highlight_info.copy()
            self.logger.debug(f"POSITION_TRACKER: Tracking highlight {highlight_id}")
            
        except Exception as e:
            self.logger.error(f"POSITION_TRACKER: Error tracking highlight: {e}")
    
    def untrack_highlight(self, highlight_id: str):
        """Stop tracking a highlight."""
        try:
            if highlight_id in self.active_highlights:
                del self.active_highlights[highlight_id]
                self.logger.debug(f"POSITION_TRACKER: Stopped tracking highlight {highlight_id}")
            
        except Exception as e:
            self.logger.error(f"POSITION_TRACKER: Error untracking highlight: {e}")
    
    def track_cursor_position(self, text_position: int):
        """Track cursor position and sync with PDF."""
        try:
            if not self.cursor_sync_enabled:
                return
            
            if self.current_cursor_position != text_position:
                self.current_cursor_position = text_position
                self.stats['cursor_updates'] += 1
                
                # Queue update to avoid excessive processing
                self._queue_update('cursor', text_position)
                
                # Emit signal
                self.cursor_position_changed.emit(text_position)
                
        except Exception as e:
            self.logger.error(f"POSITION_TRACKER: Error tracking cursor position: {e}")
    
    def track_selection_change(self, start_pos: int, end_pos: int):
        """Track selection changes and sync highlighting."""
        try:
            if not self.selection_sync_enabled:
                return
            
            if self.current_selection != (start_pos, end_pos):
                self.current_selection = (start_pos, end_pos)
                self.stats['selection_updates'] += 1
                
                # Queue update to avoid excessive processing
                self._queue_update('selection', (start_pos, end_pos))
                
                # Emit signal
                self.selection_changed.emit(start_pos, end_pos)
                
        except Exception as e:
            self.logger.error(f"POSITION_TRACKER: Error tracking selection change: {e}")
    
    def _queue_update(self, update_type: str, data: Any):
        """Queue an update to be processed after a delay."""
        try:
            # Add to pending updates
            self.pending_updates.append({
                'type': update_type,
                'data': data,
                'timestamp': self._get_current_time()
            })
            
            # Start or restart timer
            if not self.update_timer.isActive():
                self.update_timer.start(self.update_delay)
            
        except Exception as e:
            self.logger.error(f"POSITION_TRACKER: Error queueing update: {e}")
    
    def _process_pending_updates(self):
        """Process all pending updates."""
        try:
            if not self.pending_updates:
                return
            
            # Process cursor updates
            cursor_updates = [u for u in self.pending_updates if u['type'] == 'cursor']
            if cursor_updates:
                # Use the most recent cursor position
                latest_cursor = cursor_updates[-1]['data']
                self._sync_cursor_position(latest_cursor)
            
            # Process selection updates
            selection_updates = [u for u in self.pending_updates if u['type'] == 'selection']
            if selection_updates:
                # Use the most recent selection
                latest_selection = selection_updates[-1]['data']
                self._sync_selection(*latest_selection)
            
            # Clear pending updates
            self.pending_updates.clear()
            
        except Exception as e:
            self.logger.error(f"POSITION_TRACKER: Error processing pending updates: {e}")
    
    def _sync_cursor_position(self, text_position: int):
        """Synchronize cursor position with PDF."""
        try:
            if self.highlighting_engine:
                self.highlighting_engine.sync_cursor_position(text_position)
                self.stats['sync_operations'] += 1
            
        except Exception as e:
            self.logger.error(f"POSITION_TRACKER: Error syncing cursor position: {e}")
    
    def _sync_selection(self, start_pos: int, end_pos: int):
        """Synchronize selection highlighting."""
        try:
            if not self.highlighting_engine:
                return
            
            # Check if selection is within any tracked highlight
            for highlight_id, highlight_info in self.active_highlights.items():
                h_start = highlight_info['text_start']
                h_end = highlight_info['text_end']
                
                # Check if selection overlaps with this highlight
                if (start_pos < h_end and end_pos > h_start):
                    # Activate this highlight
                    self._activate_highlight(highlight_id)
                    break
            
            self.stats['sync_operations'] += 1
            
        except Exception as e:
            self.logger.error(f"POSITION_TRACKER: Error syncing selection: {e}")
    
    def _activate_highlight(self, highlight_id: str):
        """Activate a specific highlight."""
        try:
            if highlight_id in self.active_highlights:
                highlight_info = self.active_highlights[highlight_id]
                
                # Update highlight to active state
                highlight_info['active'] = True
                highlight_info['last_activated'] = self._get_current_time()
                
                # Emit signal
                self.highlight_activated.emit(highlight_id)
                
                self.stats['highlight_activations'] += 1
                self.logger.debug(f"POSITION_TRACKER: Activated highlight {highlight_id}")
                
        except Exception as e:
            self.logger.error(f"POSITION_TRACKER: Error activating highlight: {e}")
    
    def on_cursor_position_changed(self):
        """Handle cursor position changed signal from text widget."""
        try:
            if self.highlighting_engine and self.highlighting_engine.text_widget:
                text_widget = self.highlighting_engine.text_widget
                cursor = text_widget.textCursor()
                position = cursor.position()
                
                self.track_cursor_position(position)
                
        except Exception as e:
            self.logger.error(f"POSITION_TRACKER: Error handling cursor position change: {e}")
    
    def on_selection_changed(self):
        """Handle selection changed signal from text widget."""
        try:
            if self.highlighting_engine and self.highlighting_engine.text_widget:
                text_widget = self.highlighting_engine.text_widget
                cursor = text_widget.textCursor()
                
                start_pos = cursor.selectionStart()
                end_pos = cursor.selectionEnd()
                
                self.track_selection_change(start_pos, end_pos)
                
        except Exception as e:
            self.logger.error(f"POSITION_TRACKER: Error handling selection change: {e}")
    
    def get_highlight_at_position(self, text_position: int) -> Optional[str]:
        """Get highlight ID at a specific text position."""
        try:
            for highlight_id, highlight_info in self.active_highlights.items():
                start = highlight_info['text_start']
                end = highlight_info['text_end']
                
                if start <= text_position < end:
                    return highlight_id
            
            return None
            
        except Exception as e:
            self.logger.error(f"POSITION_TRACKER: Error getting highlight at position: {e}")
            return None
    
    def get_highlights_in_range(self, start_pos: int, end_pos: int) -> List[str]:
        """Get all highlights that overlap with a text range."""
        try:
            overlapping_highlights = []
            
            for highlight_id, highlight_info in self.active_highlights.items():
                h_start = highlight_info['text_start']
                h_end = highlight_info['text_end']
                
                # Check if ranges overlap
                if start_pos < h_end and end_pos > h_start:
                    overlapping_highlights.append(highlight_id)
            
            return overlapping_highlights
            
        except Exception as e:
            self.logger.error(f"POSITION_TRACKER: Error getting highlights in range: {e}")
            return []
    
    def enable_cursor_sync(self):
        """Enable cursor position synchronization."""
        self.cursor_sync_enabled = True
        self.logger.info("POSITION_TRACKER: Cursor sync enabled")
    
    def disable_cursor_sync(self):
        """Disable cursor position synchronization."""
        self.cursor_sync_enabled = False
        self.logger.info("POSITION_TRACKER: Cursor sync disabled")
    
    def enable_selection_sync(self):
        """Enable selection synchronization."""
        self.selection_sync_enabled = True
        self.logger.info("POSITION_TRACKER: Selection sync enabled")
    
    def disable_selection_sync(self):
        """Disable selection synchronization."""
        self.selection_sync_enabled = False
        self.logger.info("POSITION_TRACKER: Selection sync disabled")
    
    def clear_tracking(self):
        """Clear all tracking data."""
        try:
            self.active_highlights.clear()
            self.current_cursor_position = 0
            self.current_selection = (0, 0)
            self.pending_updates.clear()
            
            if self.update_timer.isActive():
                self.update_timer.stop()
            
            self.logger.info("POSITION_TRACKER: Tracking data cleared")
            
        except Exception as e:
            self.logger.error(f"POSITION_TRACKER: Error clearing tracking: {e}")
    
    def _get_current_time(self) -> float:
        """Get current timestamp."""
        import time
        return time.time()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get position tracker statistics."""
        return {
            'active_highlights': len(self.active_highlights),
            'current_cursor_position': self.current_cursor_position,
            'current_selection': self.current_selection,
            'cursor_sync_enabled': self.cursor_sync_enabled,
            'selection_sync_enabled': self.selection_sync_enabled,
            'pending_updates': len(self.pending_updates),
            'update_delay': self.update_delay,
            'stats': self.stats.copy()
        }