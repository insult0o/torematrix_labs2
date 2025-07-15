"""
Context Menu System for Element Tree View

Provides dynamic context menus with element-specific actions.
"""

from typing import List, Dict, Any, Optional, Callable
from PyQt6.QtCore import QObject, pyqtSignal, QPoint, QModelIndex
from PyQt6.QtWidgets import QMenu, QTreeView, QApplication
from PyQt6.QtGui import QIcon, QKeySequence, QAction

from ..models.tree_node import TreeNode
from ..interfaces.tree_interfaces import ElementProtocol


class MenuAction:
    """Represents a context menu action."""
    
    def __init__(
        self,
        action_id: str,
        text: str,
        callback: Callable,
        icon: Optional[QIcon] = None,
        shortcut: Optional[QKeySequence] = None,
        enabled: bool = True,
        visible: bool = True,
        checkable: bool = False,
        checked: bool = False,
        separator_before: bool = False,
        separator_after: bool = False
    ):
        self.action_id = action_id
        self.text = text
        self.callback = callback
        self.icon = icon
        self.shortcut = shortcut
        self.enabled = enabled
        self.visible = visible
        self.checkable = checkable
        self.checked = checked
        self.separator_before = separator_before
        self.separator_after = separator_after


class MenuSection:
    """Represents a section of menu actions."""
    
    def __init__(self, section_id: str, title: Optional[str] = None):
        self.section_id = section_id
        self.title = title
        self.actions: List[MenuAction] = []
    
    def add_action(self, action: MenuAction) -> None:
        """Add action to this section."""
        self.actions.append(action)
    
    def remove_action(self, action_id: str) -> bool:
        """Remove action by ID."""
        for i, action in enumerate(self.actions):
            if action.action_id == action_id:
                del self.actions[i]
                return True
        return False
    
    def get_action(self, action_id: str) -> Optional[MenuAction]:
        """Get action by ID."""
        for action in self.actions:
            if action.action_id == action_id:
                return action
        return None


class ActionFilter:
    """Filters actions based on context."""
    
    @staticmethod
    def filter_by_element_type(actions: List[MenuAction], element_type: str) -> List[MenuAction]:
        """Filter actions based on element type."""
        # Define which actions are available for each element type
        type_restrictions = {
            'table': ['edit', 'copy', 'delete', 'export_table', 'format_table'],
            'list': ['edit', 'copy', 'delete', 'add_item', 'reorder'],
            'text': ['edit', 'copy', 'delete', 'format_text'],
            'image': ['view', 'copy', 'delete', 'export_image', 'ocr'],
            'title': ['edit', 'copy', 'delete', 'format_title'],
            'header': ['edit', 'copy', 'delete', 'format_header']
        }
        
        allowed_actions = type_restrictions.get(element_type, 
                                               ['edit', 'copy', 'delete'])  # Default actions
        
        return [action for action in actions 
                if any(allowed in action.action_id for allowed in allowed_actions)]
    
    @staticmethod
    def filter_by_selection_count(actions: List[MenuAction], count: int) -> List[MenuAction]:
        """Filter actions based on selection count."""
        if count == 0:
            # No selection - only general actions
            return [action for action in actions 
                   if action.action_id in ['paste', 'select_all', 'expand_all', 'collapse_all']]
        elif count == 1:
            # Single selection - all applicable actions
            return [action for action in actions 
                   if action.action_id not in ['group', 'merge']]  # Multi-only actions
        else:
            # Multi-selection - only multi-applicable actions
            return [action for action in actions 
                   if action.action_id in ['copy', 'delete', 'group', 'merge', 'export']]
    
    @staticmethod
    def filter_by_permissions(actions: List[MenuAction], permissions: Dict[str, bool]) -> List[MenuAction]:
        """Filter actions based on user permissions."""
        filtered = []
        for action in actions:
            # Check if action requires specific permission
            if action.action_id in ['delete', 'edit']:
                if permissions.get('can_modify', True):
                    filtered.append(action)
            elif action.action_id in ['export']:
                if permissions.get('can_export', True):
                    filtered.append(action)
            else:
                # Default: allow action
                filtered.append(action)
        return filtered


class ContextMenuManager(QObject):
    """Manages context menus for the tree view."""
    
    # Signals
    actionTriggered = pyqtSignal(str, list)  # action_id, selected_element_ids
    menuAboutToShow = pyqtSignal(QPoint, list)  # position, selected_element_ids
    menuClosed = pyqtSignal()
    
    def __init__(self, tree_view: QTreeView, parent=None):
        super().__init__(parent)
        self.tree_view = tree_view
        self.sections: Dict[str, MenuSection] = {}
        self.permissions: Dict[str, bool] = {
            'can_modify': True,
            'can_export': True,
            'can_delete': True
        }
        
        # Context state
        self.last_context_point = QPoint()
        self.last_context_elements: List[str] = []
        
        # Initialize default sections and actions
        self._setup_default_sections()
        
        # Connect tree view
        self.tree_view.setContextMenuPolicy(self.tree_view.contextMenuPolicy() or 
                                           self.tree_view.ContextMenuPolicy.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self._show_context_menu)
    
    def _setup_default_sections(self) -> None:
        """Setup default menu sections and actions."""
        # Edit section
        edit_section = MenuSection('edit', 'Edit')
        edit_section.add_action(MenuAction(
            'cut', 'Cut', self._handle_cut,
            shortcut=QKeySequence.StandardKey.Cut
        ))
        edit_section.add_action(MenuAction(
            'copy', 'Copy', self._handle_copy,
            shortcut=QKeySequence.StandardKey.Copy
        ))
        edit_section.add_action(MenuAction(
            'paste', 'Paste', self._handle_paste,
            shortcut=QKeySequence.StandardKey.Paste
        ))
        edit_section.add_action(MenuAction(
            'delete', 'Delete', self._handle_delete,
            shortcut=QKeySequence.StandardKey.Delete
        ))
        self.add_section(edit_section)
        
        # Selection section
        selection_section = MenuSection('selection', 'Selection')
        selection_section.add_action(MenuAction(
            'select_all', 'Select All', self._handle_select_all,
            shortcut=QKeySequence.StandardKey.SelectAll
        ))
        selection_section.add_action(MenuAction(
            'select_children', 'Select Children', self._handle_select_children
        ))
        selection_section.add_action(MenuAction(
            'select_siblings', 'Select Siblings', self._handle_select_siblings
        ))
        self.add_section(selection_section)
        
        # View section
        view_section = MenuSection('view', 'View')
        view_section.add_action(MenuAction(
            'expand', 'Expand', self._handle_expand
        ))
        view_section.add_action(MenuAction(
            'collapse', 'Collapse', self._handle_collapse
        ))
        view_section.add_action(MenuAction(
            'expand_all', 'Expand All', self._handle_expand_all
        ))
        view_section.add_action(MenuAction(
            'collapse_all', 'Collapse All', self._handle_collapse_all
        ))
        self.add_section(view_section)
        
        # Element-specific section
        element_section = MenuSection('element', 'Element')
        element_section.add_action(MenuAction(
            'edit_element', 'Edit Element...', self._handle_edit_element
        ))
        element_section.add_action(MenuAction(
            'view_properties', 'Properties...', self._handle_view_properties
        ))
        element_section.add_action(MenuAction(
            'duplicate', 'Duplicate', self._handle_duplicate
        ))
        self.add_section(element_section)
        
        # Export section
        export_section = MenuSection('export', 'Export')
        export_section.add_action(MenuAction(
            'export_text', 'Export as Text...', self._handle_export_text
        ))
        export_section.add_action(MenuAction(
            'export_json', 'Export as JSON...', self._handle_export_json
        ))
        export_section.add_action(MenuAction(
            'export_html', 'Export as HTML...', self._handle_export_html
        ))
        self.add_section(export_section)
    
    def add_section(self, section: MenuSection) -> None:
        """Add menu section."""
        self.sections[section.section_id] = section
    
    def remove_section(self, section_id: str) -> bool:
        """Remove menu section."""
        if section_id in self.sections:
            del self.sections[section_id]
            return True
        return False
    
    def get_section(self, section_id: str) -> Optional[MenuSection]:
        """Get menu section by ID."""
        return self.sections.get(section_id)
    
    def add_action_to_section(self, section_id: str, action: MenuAction) -> bool:
        """Add action to existing section."""
        section = self.sections.get(section_id)
        if section:
            section.add_action(action)
            return True
        return False
    
    def remove_action(self, section_id: str, action_id: str) -> bool:
        """Remove action from section."""
        section = self.sections.get(section_id)
        if section:
            return section.remove_action(action_id)
        return False
    
    def set_action_enabled(self, action_id: str, enabled: bool) -> bool:
        """Enable/disable action by ID."""
        for section in self.sections.values():
            action = section.get_action(action_id)
            if action:
                action.enabled = enabled
                return True
        return False
    
    def set_action_visible(self, action_id: str, visible: bool) -> bool:
        """Show/hide action by ID."""
        for section in self.sections.values():
            action = section.get_action(action_id)
            if action:
                action.visible = visible
                return True
        return False
    
    def set_permissions(self, permissions: Dict[str, bool]) -> None:
        """Set user permissions."""
        self.permissions.update(permissions)
    
    def _show_context_menu(self, position: QPoint) -> None:
        """Show context menu at specified position."""
        # Get selected elements
        selected_elements = self._get_selected_elements()
        
        # Store context
        self.last_context_point = position
        self.last_context_elements = selected_elements
        
        # Get element at position
        index = self.tree_view.indexAt(position)
        context_element = None
        if index.isValid():
            model = self.tree_view.model()
            if model:
                element_id = model.data(index, self.tree_view.UserRole)
                if element_id:
                    context_element = model.get_element_by_id(element_id)
        
        # Build menu
        menu = self._build_menu(selected_elements, context_element)
        
        if menu and menu.actions():
            # Emit signal before showing
            self.menuAboutToShow.emit(position, selected_elements)
            
            # Show menu
            global_pos = self.tree_view.mapToGlobal(position)
            menu.exec(global_pos)
            
            self.menuClosed.emit()
    
    def _build_menu(self, selected_elements: List[str], context_element: Optional[ElementProtocol]) -> QMenu:
        """Build context menu based on current context."""
        menu = QMenu(self.tree_view)
        
        # Determine element type for filtering
        element_type = context_element.type if context_element else 'unknown'
        
        # Get all actions from all sections
        all_actions = []
        for section in self.sections.values():
            all_actions.extend(section.actions)
        
        # Apply filters
        filtered_actions = ActionFilter.filter_by_element_type(all_actions, element_type)
        filtered_actions = ActionFilter.filter_by_selection_count(filtered_actions, len(selected_elements))
        filtered_actions = ActionFilter.filter_by_permissions(filtered_actions, self.permissions)
        
        # Group actions by section
        sections_with_actions = {}
        for action in filtered_actions:
            if action.visible:
                for section_id, section in self.sections.items():
                    if action in section.actions:
                        if section_id not in sections_with_actions:
                            sections_with_actions[section_id] = []
                        sections_with_actions[section_id].append(action)
                        break
        
        # Build menu sections
        first_section = True
        for section_id in ['edit', 'selection', 'view', 'element', 'export']:  # Desired order
            if section_id in sections_with_actions:
                section = self.sections[section_id]
                actions = sections_with_actions[section_id]
                
                # Add separator before section (except first)
                if not first_section:
                    menu.addSeparator()
                first_section = False
                
                # Add section title if specified
                if section.title:
                    title_action = menu.addAction(section.title)
                    title_action.setEnabled(False)
                    menu.addSeparator()
                
                # Add actions
                for action in actions:
                    self._add_action_to_menu(menu, action)
        
        return menu
    
    def _add_action_to_menu(self, menu: QMenu, menu_action: MenuAction) -> QAction:
        """Add menu action to Qt menu."""
        # Add separator before if requested
        if menu_action.separator_before:
            menu.addSeparator()
        
        # Create Qt action
        qt_action = QAction(menu_action.text, menu)
        
        # Configure action
        if menu_action.icon:
            qt_action.setIcon(menu_action.icon)
        if menu_action.shortcut:
            qt_action.setShortcut(menu_action.shortcut)
        
        qt_action.setEnabled(menu_action.enabled)
        qt_action.setVisible(menu_action.visible)
        qt_action.setCheckable(menu_action.checkable)
        if menu_action.checkable:
            qt_action.setChecked(menu_action.checked)
        
        # Connect callback
        qt_action.triggered.connect(lambda checked: self._trigger_action(menu_action.action_id))
        
        # Add to menu
        menu.addAction(qt_action)
        
        # Add separator after if requested
        if menu_action.separator_after:
            menu.addSeparator()
        
        return qt_action
    
    def _trigger_action(self, action_id: str) -> None:
        """Trigger action with current context."""
        self.actionTriggered.emit(action_id, self.last_context_elements)
    
    def _get_selected_elements(self) -> List[str]:
        """Get currently selected element IDs."""
        selected = []
        selection_model = self.tree_view.selectionModel()
        model = self.tree_view.model()
        
        if selection_model and model:
            for index in selection_model.selectedIndexes():
                if index.column() == 0:  # Only first column
                    element_id = model.data(index, self.tree_view.UserRole)
                    if element_id:
                        selected.append(element_id)
        
        return selected
    
    # Default action handlers
    
    def _handle_cut(self) -> None:
        """Handle cut action."""
        # Implementation would integrate with clipboard
        print(f"Cut elements: {self.last_context_elements}")
    
    def _handle_copy(self) -> None:
        """Handle copy action."""
        # Implementation would integrate with clipboard
        print(f"Copy elements: {self.last_context_elements}")
    
    def _handle_paste(self) -> None:
        """Handle paste action."""
        # Implementation would integrate with clipboard
        print("Paste elements")
    
    def _handle_delete(self) -> None:
        """Handle delete action."""
        # Implementation would delete selected elements
        print(f"Delete elements: {self.last_context_elements}")
    
    def _handle_select_all(self) -> None:
        """Handle select all action."""
        # Implementation would select all elements
        print("Select all elements")
    
    def _handle_select_children(self) -> None:
        """Handle select children action."""
        print(f"Select children of: {self.last_context_elements}")
    
    def _handle_select_siblings(self) -> None:
        """Handle select siblings action."""
        print(f"Select siblings of: {self.last_context_elements}")
    
    def _handle_expand(self) -> None:
        """Handle expand action."""
        for element_id in self.last_context_elements:
            model = self.tree_view.model()
            if model:
                index = model.get_index_by_element_id(element_id)
                if index.isValid():
                    self.tree_view.expand(index)
    
    def _handle_collapse(self) -> None:
        """Handle collapse action."""
        for element_id in self.last_context_elements:
            model = self.tree_view.model()
            if model:
                index = model.get_index_by_element_id(element_id)
                if index.isValid():
                    self.tree_view.collapse(index)
    
    def _handle_expand_all(self) -> None:
        """Handle expand all action."""
        self.tree_view.expandAll()
    
    def _handle_collapse_all(self) -> None:
        """Handle collapse all action."""
        self.tree_view.collapseAll()
    
    def _handle_edit_element(self) -> None:
        """Handle edit element action."""
        print(f"Edit elements: {self.last_context_elements}")
    
    def _handle_view_properties(self) -> None:
        """Handle view properties action."""
        print(f"View properties of: {self.last_context_elements}")
    
    def _handle_duplicate(self) -> None:
        """Handle duplicate action."""
        print(f"Duplicate elements: {self.last_context_elements}")
    
    def _handle_export_text(self) -> None:
        """Handle export as text action."""
        print(f"Export as text: {self.last_context_elements}")
    
    def _handle_export_json(self) -> None:
        """Handle export as JSON action."""
        print(f"Export as JSON: {self.last_context_elements}")
    
    def _handle_export_html(self) -> None:
        """Handle export as HTML action."""
        print(f"Export as HTML: {self.last_context_elements}")


class ContextMenuBuilder:
    """Builder for creating custom context menus."""
    
    def __init__(self):
        self.sections: List[MenuSection] = []
    
    def add_section(self, section_id: str, title: Optional[str] = None) -> 'ContextMenuBuilder':
        """Add new section."""
        section = MenuSection(section_id, title)
        self.sections.append(section)
        return self
    
    def add_action(
        self,
        section_id: str,
        action_id: str,
        text: str,
        callback: Callable,
        **kwargs
    ) -> 'ContextMenuBuilder':
        """Add action to section."""
        # Find section
        section = None
        for s in self.sections:
            if s.section_id == section_id:
                section = s
                break
        
        if not section:
            section = MenuSection(section_id)
            self.sections.append(section)
        
        # Create action
        action = MenuAction(action_id, text, callback, **kwargs)
        section.add_action(action)
        
        return self
    
    def build(self, tree_view: QTreeView) -> ContextMenuManager:
        """Build context menu manager."""
        manager = ContextMenuManager(tree_view)
        
        # Clear default sections if we have custom ones
        if self.sections:
            manager.sections.clear()
            for section in self.sections:
                manager.add_section(section)
        
        return manager