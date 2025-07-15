"""
Keyboard Shortcuts Manager for Hierarchical Element List

Provides comprehensive keyboard navigation and accessibility shortcuts
for efficient interaction without mouse usage.
"""

import logging
from typing import Dict, List, Optional, Callable, Any
from PyQt6.QtCore import QObject, pyqtSignal, Qt
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import QWidget

logger = logging.getLogger(__name__)


class KeyboardShortcutManager(QObject):
    """
    Keyboard shortcut manager for element list accessibility
    
    Provides comprehensive keyboard navigation and shortcuts
    following accessibility best practices.
    """
    
    # Signals
    shortcut_triggered = pyqtSignal(str, dict)  # action_name, context
    
    def __init__(self, element_list_widget: QWidget, parent: Optional[QObject] = None):
        super().__init__(parent)
        
        self.element_list = element_list_widget
        self.shortcuts: Dict[str, QShortcut] = {}
        
        # Setup default shortcuts
        self._setup_default_shortcuts()
        
        logger.info("KeyboardShortcutManager initialized")
    
    def _setup_default_shortcuts(self):
        """Setup default keyboard shortcuts"""
        shortcuts = {
            # Navigation
            "expand_element": ("Right", self._expand_current_element),
            "collapse_element": ("Left", self._collapse_current_element),
            "select_next": ("Down", self._select_next_element),
            "select_previous": ("Up", self._select_previous_element),
            "select_first": ("Home", self._select_first_element),
            "select_last": ("End", self._select_last_element),
            
            # Selection
            "select_element": ("Space", self._toggle_selection),
            "select_all": ("Ctrl+A", self._select_all),
            "clear_selection": ("Escape", self._clear_selection),
            
            # Search and filter
            "start_search": ("Ctrl+F", self._start_search),
            "next_search_result": ("F3", self._next_search_result),
            "previous_search_result": ("Shift+F3", self._previous_search_result),
            
            # View operations
            "expand_all": ("Ctrl+Right", self._expand_all),
            "collapse_all": ("Ctrl+Left", self._collapse_all),
            "refresh": ("F5", self._refresh_tree),
            
            # Accessibility helpers
            "describe_element": ("Ctrl+Shift+D", self._describe_current_element),
            "announce_position": ("Ctrl+Shift+P", self._announce_position),
        }
        
        for action_name, (key_sequence, callback) in shortcuts.items():
            self.add_shortcut(action_name, key_sequence, callback)
    
    def add_shortcut(self, action_name: str, key_sequence: str, callback: Callable):
        """Add a keyboard shortcut"""
        if action_name in self.shortcuts:
            logger.warning(f"Shortcut '{action_name}' already exists")
            return
        
        shortcut = QShortcut(QKeySequence(key_sequence), self.element_list)
        shortcut.activated.connect(callback)
        
        self.shortcuts[action_name] = shortcut
        logger.debug(f"Added shortcut {key_sequence} for {action_name}")
    
    def _expand_current_element(self):
        """Expand currently focused element"""
        if hasattr(self.element_list, 'expand_current_element'):
            self.element_list.expand_current_element()
        self.shortcut_triggered.emit("expand_element", {})
    
    def _collapse_current_element(self):
        """Collapse currently focused element"""
        if hasattr(self.element_list, 'collapse_current_element'):
            self.element_list.collapse_current_element()
        self.shortcut_triggered.emit("collapse_element", {})
    
    def _select_next_element(self):
        """Select next element"""
        if hasattr(self.element_list, 'select_next_element'):
            self.element_list.select_next_element()
        self.shortcut_triggered.emit("select_next", {})
    
    def _select_previous_element(self):
        """Select previous element"""
        if hasattr(self.element_list, 'select_previous_element'):
            self.element_list.select_previous_element()
        self.shortcut_triggered.emit("select_previous", {})
    
    def _select_first_element(self):
        """Select first element"""
        if hasattr(self.element_list, 'select_first_element'):
            self.element_list.select_first_element()
        self.shortcut_triggered.emit("select_first", {})
    
    def _select_last_element(self):
        """Select last element"""
        if hasattr(self.element_list, 'select_last_element'):
            self.element_list.select_last_element()
        self.shortcut_triggered.emit("select_last", {})
    
    def _toggle_selection(self):
        """Toggle selection of current element"""
        if hasattr(self.element_list, 'toggle_current_selection'):
            self.element_list.toggle_current_selection()
        self.shortcut_triggered.emit("select_element", {})
    
    def _select_all(self):
        """Select all elements"""
        if hasattr(self.element_list, 'select_all_elements'):
            self.element_list.select_all_elements()
        self.shortcut_triggered.emit("select_all", {})
    
    def _clear_selection(self):
        """Clear selection"""
        if hasattr(self.element_list, 'clear_selection'):
            self.element_list.clear_selection()
        self.shortcut_triggered.emit("clear_selection", {})
    
    def _start_search(self):
        """Start search mode"""
        if hasattr(self.element_list, 'start_search'):
            self.element_list.start_search()
        self.shortcut_triggered.emit("start_search", {})
    
    def _next_search_result(self):
        """Navigate to next search result"""
        if hasattr(self.element_list, 'next_search_result'):
            self.element_list.next_search_result()
        self.shortcut_triggered.emit("next_search_result", {})
    
    def _previous_search_result(self):
        """Navigate to previous search result"""
        if hasattr(self.element_list, 'previous_search_result'):
            self.element_list.previous_search_result()
        self.shortcut_triggered.emit("previous_search_result", {})
    
    def _expand_all(self):
        """Expand all elements"""
        if hasattr(self.element_list, 'expand_all'):
            self.element_list.expand_all()
        self.shortcut_triggered.emit("expand_all", {})
    
    def _collapse_all(self):
        """Collapse all elements"""
        if hasattr(self.element_list, 'collapse_all'):
            self.element_list.collapse_all()
        self.shortcut_triggered.emit("collapse_all", {})
    
    def _refresh_tree(self):
        """Refresh tree view"""
        if hasattr(self.element_list, 'refresh'):
            self.element_list.refresh()
        self.shortcut_triggered.emit("refresh", {})
    
    def _describe_current_element(self):
        """Describe current element for accessibility"""
        if hasattr(self.element_list, 'describe_current_element'):
            self.element_list.describe_current_element()
        self.shortcut_triggered.emit("describe_element", {})
    
    def _announce_position(self):
        """Announce current position in tree"""
        if hasattr(self.element_list, 'announce_position'):
            self.element_list.announce_position()
        self.shortcut_triggered.emit("announce_position", {})