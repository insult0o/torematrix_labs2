"""
Keyboard Navigation System for Element Tree View

Provides comprehensive keyboard navigation and shortcuts.
"""

from typing import Dict, List, Optional, Callable, Any
from PyQt6.QtCore import QObject, pyqtSignal, QModelIndex, Qt, QKeyCombination
from PyQt6.QtWidgets import QTreeView, QApplication
from PyQt6.QtGui import QKeyEvent, QKeySequence, QAction

from ..models.tree_node import TreeNode


class NavigationCommand:
    """Represents a navigation command."""
    
    def __init__(
        self,
        command_id: str,
        name: str,
        key_sequence: QKeySequence,
        handler: Callable,
        description: str = "",
        enabled: bool = True
    ):
        self.command_id = command_id
        self.name = name
        self.key_sequence = key_sequence
        self.handler = handler
        self.description = description
        self.enabled = enabled


class NavigationState:
    """Tracks navigation state and history."""
    
    def __init__(self):
        self.current_index: Optional[QModelIndex] = None
        self.navigation_history: List[QModelIndex] = []
        self.history_position = -1
        self.max_history_size = 50
        
        # Navigation modes
        self.type_ahead_mode = False
        self.type_ahead_buffer = ""
        self.quick_nav_mode = False
        
        # Bookmarks
        self.bookmarks: Dict[str, QModelIndex] = {}
    
    def add_to_history(self, index: QModelIndex) -> None:
        """Add index to navigation history."""
        if not index.isValid():
            return
        
        # Remove from current position onwards
        self.navigation_history = self.navigation_history[:self.history_position + 1]
        
        # Add new index
        self.navigation_history.append(index)
        self.history_position = len(self.navigation_history) - 1
        
        # Limit history size
        if len(self.navigation_history) > self.max_history_size:
            self.navigation_history.pop(0)
            self.history_position -= 1
    
    def can_go_back(self) -> bool:
        """Check if can navigate back."""
        return self.history_position > 0
    
    def can_go_forward(self) -> bool:
        """Check if can navigate forward."""
        return self.history_position < len(self.navigation_history) - 1
    
    def go_back(self) -> Optional[QModelIndex]:
        """Go back in history."""
        if self.can_go_back():
            self.history_position -= 1
            return self.navigation_history[self.history_position]
        return None
    
    def go_forward(self) -> Optional[QModelIndex]:
        """Go forward in history."""
        if self.can_go_forward():
            self.history_position += 1
            return self.navigation_history[self.history_position]
        return None
    
    def set_bookmark(self, key: str, index: QModelIndex) -> None:
        """Set bookmark for quick navigation."""
        if index.isValid():
            self.bookmarks[key] = index
    
    def get_bookmark(self, key: str) -> Optional[QModelIndex]:
        """Get bookmark by key."""
        return self.bookmarks.get(key)
    
    def clear_bookmarks(self) -> None:
        """Clear all bookmarks."""
        self.bookmarks.clear()


class TypeAheadSearch:
    """Implements type-ahead search functionality."""
    
    def __init__(self, tree_view: QTreeView):
        self.tree_view = tree_view
        self.search_buffer = ""
        self.last_search_time = 0
        self.search_timeout = 1000  # 1 second
    
    def handle_character(self, char: str) -> bool:
        """Handle typed character for type-ahead search."""
        import time
        current_time = int(time.time() * 1000)
        
        # Reset buffer if timeout exceeded
        if current_time - self.last_search_time > self.search_timeout:
            self.search_buffer = ""
        
        self.search_buffer += char.lower()
        self.last_search_time = current_time
        
        # Find matching item
        return self._find_and_select_match()
    
    def _find_and_select_match(self) -> bool:
        """Find and select item matching search buffer."""
        model = self.tree_view.model()
        if not model:
            return False
        
        # Start from current item or root
        start_index = self.tree_view.currentIndex()
        if not start_index.isValid():
            start_index = model.index(0, 0)
        
        # Search for match
        match_index = self._search_from_index(start_index, self.search_buffer)
        
        if match_index.isValid():
            self.tree_view.setCurrentIndex(match_index)
            self.tree_view.scrollTo(match_index)
            return True
        
        return False
    
    def _search_from_index(self, start_index: QModelIndex, search_text: str) -> QModelIndex:
        """Search for text starting from given index."""
        model = self.tree_view.model()
        if not model:
            return QModelIndex()
        
        # Get all visible indices
        indices = self._get_all_visible_indices()
        
        # Find start position
        start_pos = 0
        for i, index in enumerate(indices):
            if index == start_index:
                start_pos = i
                break
        
        # Search from start position onwards
        for i in range(len(indices)):
            check_pos = (start_pos + i) % len(indices)
            index = indices[check_pos]
            
            text = model.data(index, Qt.ItemDataRole.DisplayRole) or ""
            if text.lower().startswith(search_text):
                return index
        
        return QModelIndex()
    
    def _get_all_visible_indices(self) -> List[QModelIndex]:
        """Get all visible indices in tree order."""
        indices = []
        model = self.tree_view.model()
        if not model:
            return indices
        
        def collect_indices(parent_index: QModelIndex, level: int = 0):
            row_count = model.rowCount(parent_index)
            for row in range(row_count):
                index = model.index(row, 0, parent_index)
                if index.isValid():
                    indices.append(index)
                    
                    # Recurse if expanded
                    if self.tree_view.isExpanded(index):
                        collect_indices(index, level + 1)
        
        collect_indices(QModelIndex())
        return indices
    
    def clear_buffer(self) -> None:
        """Clear search buffer."""
        self.search_buffer = ""


class TreeNavigator:
    """Handles tree-specific navigation operations."""
    
    def __init__(self, tree_view: QTreeView):
        self.tree_view = tree_view
    
    def navigate_to_parent(self) -> bool:
        """Navigate to parent item."""
        current = self.tree_view.currentIndex()
        if current.isValid():
            parent = current.parent()
            if parent.isValid():
                self.tree_view.setCurrentIndex(parent)
                return True
        return False
    
    def navigate_to_first_child(self) -> bool:
        """Navigate to first child item."""
        current = self.tree_view.currentIndex()
        if current.isValid():
            model = self.tree_view.model()
            if model and model.rowCount(current) > 0:
                first_child = model.index(0, 0, current)
                if first_child.isValid():
                    self.tree_view.setCurrentIndex(first_child)
                    return True
        return False
    
    def navigate_to_last_child(self) -> bool:
        """Navigate to last child item."""
        current = self.tree_view.currentIndex()
        if current.isValid():
            model = self.tree_view.model()
            if model:
                row_count = model.rowCount(current)
                if row_count > 0:
                    last_child = model.index(row_count - 1, 0, current)
                    if last_child.isValid():
                        self.tree_view.setCurrentIndex(last_child)
                        return True
        return False
    
    def navigate_to_next_sibling(self) -> bool:
        """Navigate to next sibling item."""
        current = self.tree_view.currentIndex()
        if current.isValid():
            model = self.tree_view.model()
            parent = current.parent()
            if model:
                row_count = model.rowCount(parent)
                next_row = current.row() + 1
                if next_row < row_count:
                    next_sibling = model.index(next_row, 0, parent)
                    if next_sibling.isValid():
                        self.tree_view.setCurrentIndex(next_sibling)
                        return True
        return False
    
    def navigate_to_previous_sibling(self) -> bool:
        """Navigate to previous sibling item."""
        current = self.tree_view.currentIndex()
        if current.isValid():
            model = self.tree_view.model()
            parent = current.parent()
            if model:
                prev_row = current.row() - 1
                if prev_row >= 0:
                    prev_sibling = model.index(prev_row, 0, parent)
                    if prev_sibling.isValid():
                        self.tree_view.setCurrentIndex(prev_sibling)
                        return True
        return False
    
    def navigate_to_first_item(self) -> bool:
        """Navigate to first item in tree."""
        model = self.tree_view.model()
        if model and model.rowCount() > 0:
            first_item = model.index(0, 0)
            if first_item.isValid():
                self.tree_view.setCurrentIndex(first_item)
                return True
        return False
    
    def navigate_to_last_item(self) -> bool:
        """Navigate to last visible item in tree."""
        indices = self._get_all_visible_indices()
        if indices:
            last_item = indices[-1]
            self.tree_view.setCurrentIndex(last_item)
            return True
        return False
    
    def _get_all_visible_indices(self) -> List[QModelIndex]:
        """Get all visible indices in display order."""
        indices = []
        model = self.tree_view.model()
        if not model:
            return indices
        
        def collect_indices(parent_index: QModelIndex):
            row_count = model.rowCount(parent_index)
            for row in range(row_count):
                index = model.index(row, 0, parent_index)
                if index.isValid():
                    indices.append(index)
                    if self.tree_view.isExpanded(index):
                        collect_indices(index)
        
        collect_indices(QModelIndex())
        return indices
    
    def expand_current(self) -> bool:
        """Expand current item."""
        current = self.tree_view.currentIndex()
        if current.isValid():
            if not self.tree_view.isExpanded(current):
                self.tree_view.expand(current)
                return True
        return False
    
    def collapse_current(self) -> bool:
        """Collapse current item."""
        current = self.tree_view.currentIndex()
        if current.isValid():
            if self.tree_view.isExpanded(current):
                self.tree_view.collapse(current)
                return True
        return False
    
    def toggle_current(self) -> bool:
        """Toggle expansion of current item."""
        current = self.tree_view.currentIndex()
        if current.isValid():
            if self.tree_view.isExpanded(current):
                self.tree_view.collapse(current)
            else:
                self.tree_view.expand(current)
            return True
        return False


class KeyboardNavigationHandler(QObject):
    """Main keyboard navigation handler."""
    
    # Signals
    navigationPerformed = pyqtSignal(str, QModelIndex)  # command_id, target_index
    historyChanged = pyqtSignal(bool, bool)  # can_go_back, can_go_forward
    bookmarkSet = pyqtSignal(str, QModelIndex)  # key, index
    typeAheadActivated = pyqtSignal(str)  # search_buffer
    
    def __init__(self, tree_view: QTreeView, parent=None):
        super().__init__(parent)
        self.tree_view = tree_view
        self.state = NavigationState()
        self.type_ahead = TypeAheadSearch(tree_view)
        self.navigator = TreeNavigator(tree_view)
        
        # Commands registry
        self.commands: Dict[str, NavigationCommand] = {}
        
        # Setup default commands
        self._setup_default_commands()
        
        # Install event filter
        self.tree_view.installEventFilter(self)
        
        # Connect signals
        self.tree_view.currentChanged.connect(self._on_current_changed)
    
    def _setup_default_commands(self) -> None:
        """Setup default navigation commands."""
        commands = [
            # Basic navigation
            NavigationCommand("nav_up", "Move Up", QKeySequence(Qt.Key.Key_Up), 
                            self._nav_up, "Move to previous item"),
            NavigationCommand("nav_down", "Move Down", QKeySequence(Qt.Key.Key_Down), 
                            self._nav_down, "Move to next item"),
            NavigationCommand("nav_left", "Move Left", QKeySequence(Qt.Key.Key_Left), 
                            self._nav_left, "Collapse or move to parent"),
            NavigationCommand("nav_right", "Move Right", QKeySequence(Qt.Key.Key_Right), 
                            self._nav_right, "Expand or move to first child"),
            
            # Tree navigation
            NavigationCommand("nav_parent", "Go to Parent", 
                            QKeySequence(Qt.KeyboardModifier.ControlModifier | Qt.Key.Key_Up),
                            self._nav_to_parent, "Navigate to parent item"),
            NavigationCommand("nav_first_child", "Go to First Child",
                            QKeySequence(Qt.KeyboardModifier.ControlModifier | Qt.Key.Key_Down),
                            self._nav_to_first_child, "Navigate to first child"),
            NavigationCommand("nav_next_sibling", "Next Sibling",
                            QKeySequence(Qt.KeyboardModifier.ControlModifier | Qt.Key.Key_Right),
                            self._nav_to_next_sibling, "Navigate to next sibling"),
            NavigationCommand("nav_prev_sibling", "Previous Sibling",
                            QKeySequence(Qt.KeyboardModifier.ControlModifier | Qt.Key.Key_Left),
                            self._nav_to_prev_sibling, "Navigate to previous sibling"),
            
            # Expansion
            NavigationCommand("expand", "Expand", QKeySequence(Qt.Key.Key_Plus),
                            self._expand_current, "Expand current item"),
            NavigationCommand("collapse", "Collapse", QKeySequence(Qt.Key.Key_Minus),
                            self._collapse_current, "Collapse current item"),
            NavigationCommand("toggle", "Toggle", QKeySequence(Qt.Key.Key_Space),
                            self._toggle_current, "Toggle expansion"),
            NavigationCommand("expand_all", "Expand All",
                            QKeySequence(Qt.KeyboardModifier.ControlModifier | Qt.Key.Key_Plus),
                            self._expand_all, "Expand all items"),
            NavigationCommand("collapse_all", "Collapse All",
                            QKeySequence(Qt.KeyboardModifier.ControlModifier | Qt.Key.Key_Minus),
                            self._collapse_all, "Collapse all items"),
            
            # Jump navigation
            NavigationCommand("nav_home", "Go to Top", QKeySequence(Qt.Key.Key_Home),
                            self._nav_to_first, "Go to first item"),
            NavigationCommand("nav_end", "Go to Bottom", QKeySequence(Qt.Key.Key_End),
                            self._nav_to_last, "Go to last visible item"),
            NavigationCommand("page_up", "Page Up", QKeySequence(Qt.Key.Key_PageUp),
                            self._page_up, "Scroll page up"),
            NavigationCommand("page_down", "Page Down", QKeySequence(Qt.Key.Key_PageDown),
                            self._page_down, "Scroll page down"),
            
            # History navigation
            NavigationCommand("history_back", "Go Back",
                            QKeySequence(Qt.KeyboardModifier.AltModifier | Qt.Key.Key_Left),
                            self._history_back, "Go back in navigation history"),
            NavigationCommand("history_forward", "Go Forward",
                            QKeySequence(Qt.KeyboardModifier.AltModifier | Qt.Key.Key_Right),
                            self._history_forward, "Go forward in navigation history"),
            
            # Bookmarks (Ctrl+number to set, number to go)
            NavigationCommand("bookmark_1", "Bookmark 1", QKeySequence(Qt.Key.Key_1),
                            lambda: self._goto_bookmark("1"), "Go to bookmark 1"),
            NavigationCommand("set_bookmark_1", "Set Bookmark 1",
                            QKeySequence(Qt.KeyboardModifier.ControlModifier | Qt.Key.Key_1),
                            lambda: self._set_bookmark("1"), "Set bookmark 1"),
            
            # Type-ahead search
            NavigationCommand("clear_search", "Clear Type-ahead",
                            QKeySequence(Qt.Key.Key_Escape),
                            self._clear_type_ahead, "Clear type-ahead search buffer"),
        ]
        
        # Add more bookmark commands
        for i in range(2, 10):
            commands.append(
                NavigationCommand(f"bookmark_{i}", f"Bookmark {i}", 
                                QKeySequence(getattr(Qt.Key, f"Key_{i}")),
                                lambda n=i: self._goto_bookmark(str(n)), f"Go to bookmark {i}")
            )
            commands.append(
                NavigationCommand(f"set_bookmark_{i}", f"Set Bookmark {i}",
                                QKeySequence(Qt.KeyboardModifier.ControlModifier | getattr(Qt.Key, f"Key_{i}")),
                                lambda n=i: self._set_bookmark(str(n)), f"Set bookmark {i}")
            )
        
        # Register all commands
        for command in commands:
            self.register_command(command)
    
    def register_command(self, command: NavigationCommand) -> None:
        """Register a navigation command."""
        self.commands[command.command_id] = command
    
    def unregister_command(self, command_id: str) -> bool:
        """Unregister a navigation command."""
        if command_id in self.commands:
            del self.commands[command_id]
            return True
        return False
    
    def get_command(self, command_id: str) -> Optional[NavigationCommand]:
        """Get command by ID."""
        return self.commands.get(command_id)
    
    def get_all_commands(self) -> List[NavigationCommand]:
        """Get all registered commands."""
        return list(self.commands.values())
    
    def eventFilter(self, obj, event) -> bool:
        """Filter keyboard events for navigation."""
        if obj != self.tree_view or event.type() != event.Type.KeyPress:
            return False
        
        key_event = event
        
        # Handle type-ahead search for printable characters
        if self._is_printable_key(key_event):
            char = key_event.text()
            if char and char.isprintable() and not key_event.modifiers():
                if self.type_ahead.handle_character(char):
                    self.typeAheadActivated.emit(self.type_ahead.search_buffer)
                    return True
        
        # Handle navigation commands
        key_sequence = QKeySequence(key_event.key() | int(key_event.modifiers()))
        
        for command in self.commands.values():
            if command.enabled and command.key_sequence == key_sequence:
                try:
                    result = command.handler()
                    if result:
                        self.navigationPerformed.emit(command.command_id, self.tree_view.currentIndex())
                        return True
                except Exception as e:
                    print(f"Error executing command {command.command_id}: {e}")
                    return False
        
        return False
    
    def _is_printable_key(self, event: QKeyEvent) -> bool:
        """Check if key event represents a printable character."""
        # Exclude special keys and modified keys (except Shift for uppercase)
        if event.modifiers() & ~Qt.KeyboardModifier.ShiftModifier:
            return False
        
        key = event.key()
        
        # Exclude special keys
        special_keys = [
            Qt.Key.Key_Escape, Qt.Key.Key_Tab, Qt.Key.Key_Return, Qt.Key.Key_Enter,
            Qt.Key.Key_Backspace, Qt.Key.Key_Delete, Qt.Key.Key_Insert,
            Qt.Key.Key_Home, Qt.Key.Key_End, Qt.Key.Key_PageUp, Qt.Key.Key_PageDown,
            Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down,
            Qt.Key.Key_F1, Qt.Key.Key_F2, Qt.Key.Key_F3, Qt.Key.Key_F4,
            Qt.Key.Key_F5, Qt.Key.Key_F6, Qt.Key.Key_F7, Qt.Key.Key_F8,
            Qt.Key.Key_F9, Qt.Key.Key_F10, Qt.Key.Key_F11, Qt.Key.Key_F12
        ]
        
        return key not in special_keys
    
    def _on_current_changed(self, current: QModelIndex, previous: QModelIndex) -> None:
        """Handle current item change."""
        if current.isValid() and current != previous:
            self.state.add_to_history(current)
            self.state.current_index = current
            self.historyChanged.emit(self.state.can_go_back(), self.state.can_go_forward())
    
    # Navigation command handlers
    
    def _nav_up(self) -> bool:
        """Move to previous item."""
        current = self.tree_view.currentIndex()
        if current.isValid():
            model = self.tree_view.model()
            if model:
                # Try previous sibling first
                if current.row() > 0:
                    prev_sibling = model.index(current.row() - 1, 0, current.parent())
                    if prev_sibling.isValid():
                        # If previous sibling is expanded, go to its last visible child
                        while self.tree_view.isExpanded(prev_sibling):
                            child_count = model.rowCount(prev_sibling)
                            if child_count > 0:
                                prev_sibling = model.index(child_count - 1, 0, prev_sibling)
                            else:
                                break
                        self.tree_view.setCurrentIndex(prev_sibling)
                        return True
                else:
                    # Go to parent
                    parent = current.parent()
                    if parent.isValid():
                        self.tree_view.setCurrentIndex(parent)
                        return True
        return False
    
    def _nav_down(self) -> bool:
        """Move to next item."""
        current = self.tree_view.currentIndex()
        if current.isValid():
            model = self.tree_view.model()
            if model:
                # If current is expanded and has children, go to first child
                if self.tree_view.isExpanded(current) and model.rowCount(current) > 0:
                    first_child = model.index(0, 0, current)
                    if first_child.isValid():
                        self.tree_view.setCurrentIndex(first_child)
                        return True
                
                # Otherwise, find next sibling or next sibling of ancestor
                while current.isValid():
                    parent = current.parent()
                    next_row = current.row() + 1
                    
                    if model.rowCount(parent) > next_row:
                        next_sibling = model.index(next_row, 0, parent)
                        if next_sibling.isValid():
                            self.tree_view.setCurrentIndex(next_sibling)
                            return True
                    
                    current = parent
        return False
    
    def _nav_left(self) -> bool:
        """Collapse or move to parent."""
        current = self.tree_view.currentIndex()
        if current.isValid():
            if self.tree_view.isExpanded(current):
                self.tree_view.collapse(current)
                return True
            else:
                return self.navigator.navigate_to_parent()
        return False
    
    def _nav_right(self) -> bool:
        """Expand or move to first child."""
        current = self.tree_view.currentIndex()
        if current.isValid():
            if not self.tree_view.isExpanded(current):
                model = self.tree_view.model()
                if model and model.rowCount(current) > 0:
                    self.tree_view.expand(current)
                    return True
            else:
                return self.navigator.navigate_to_first_child()
        return False
    
    def _nav_to_parent(self) -> bool:
        """Navigate to parent."""
        return self.navigator.navigate_to_parent()
    
    def _nav_to_first_child(self) -> bool:
        """Navigate to first child."""
        return self.navigator.navigate_to_first_child()
    
    def _nav_to_next_sibling(self) -> bool:
        """Navigate to next sibling."""
        return self.navigator.navigate_to_next_sibling()
    
    def _nav_to_prev_sibling(self) -> bool:
        """Navigate to previous sibling."""
        return self.navigator.navigate_to_previous_sibling()
    
    def _expand_current(self) -> bool:
        """Expand current item."""
        return self.navigator.expand_current()
    
    def _collapse_current(self) -> bool:
        """Collapse current item."""
        return self.navigator.collapse_current()
    
    def _toggle_current(self) -> bool:
        """Toggle current item expansion."""
        return self.navigator.toggle_current()
    
    def _expand_all(self) -> bool:
        """Expand all items."""
        self.tree_view.expandAll()
        return True
    
    def _collapse_all(self) -> bool:
        """Collapse all items."""
        self.tree_view.collapseAll()
        return True
    
    def _nav_to_first(self) -> bool:
        """Navigate to first item."""
        return self.navigator.navigate_to_first_item()
    
    def _nav_to_last(self) -> bool:
        """Navigate to last item."""
        return self.navigator.navigate_to_last_item()
    
    def _page_up(self) -> bool:
        """Page up navigation."""
        # Default Qt handling
        return False
    
    def _page_down(self) -> bool:
        """Page down navigation."""
        # Default Qt handling
        return False
    
    def _history_back(self) -> bool:
        """Go back in history."""
        index = self.state.go_back()
        if index and index.isValid():
            self.tree_view.setCurrentIndex(index)
            self.historyChanged.emit(self.state.can_go_back(), self.state.can_go_forward())
            return True
        return False
    
    def _history_forward(self) -> bool:
        """Go forward in history."""
        index = self.state.go_forward()
        if index and index.isValid():
            self.tree_view.setCurrentIndex(index)
            self.historyChanged.emit(self.state.can_go_back(), self.state.can_go_forward())
            return True
        return False
    
    def _set_bookmark(self, key: str) -> bool:
        """Set bookmark."""
        current = self.tree_view.currentIndex()
        if current.isValid():
            self.state.set_bookmark(key, current)
            self.bookmarkSet.emit(key, current)
            return True
        return False
    
    def _goto_bookmark(self, key: str) -> bool:
        """Go to bookmark."""
        index = self.state.get_bookmark(key)
        if index and index.isValid():
            self.tree_view.setCurrentIndex(index)
            self.tree_view.scrollTo(index)
            return True
        return False
    
    def _clear_type_ahead(self) -> bool:
        """Clear type-ahead buffer."""
        self.type_ahead.clear_buffer()
        return True
    
    # Public interface
    
    def execute_command(self, command_id: str) -> bool:
        """Execute command by ID."""
        command = self.commands.get(command_id)
        if command and command.enabled:
            try:
                result = command.handler()
                if result:
                    self.navigationPerformed.emit(command_id, self.tree_view.currentIndex())
                return result
            except Exception as e:
                print(f"Error executing command {command_id}: {e}")
        return False
    
    def get_navigation_state(self) -> NavigationState:
        """Get current navigation state."""
        return self.state
    
    def can_go_back(self) -> bool:
        """Check if can go back in history."""
        return self.state.can_go_back()
    
    def can_go_forward(self) -> bool:
        """Check if can go forward in history."""
        return self.state.can_go_forward()
    
    def get_bookmarks(self) -> Dict[str, QModelIndex]:
        """Get all bookmarks."""
        return self.state.bookmarks.copy()
    
    def clear_history(self) -> None:
        """Clear navigation history."""
        self.state.navigation_history.clear()
        self.state.history_position = -1
        self.historyChanged.emit(False, False)
    
    def clear_bookmarks(self) -> None:
        """Clear all bookmarks."""
        self.state.clear_bookmarks()
    
    def set_command_enabled(self, command_id: str, enabled: bool) -> bool:
        """Enable/disable command."""
        command = self.commands.get(command_id)
        if command:
            command.enabled = enabled
            return True
        return False