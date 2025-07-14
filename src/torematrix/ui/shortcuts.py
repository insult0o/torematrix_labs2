"""Keyboard shortcut management system for ToreMatrix V3."""

import logging
from typing import Dict, List, Optional, Set, Callable
from dataclasses import dataclass
from enum import Enum

from PyQt6.QtWidgets import QWidget, QMainWindow
from PyQt6.QtCore import Qt, QObject, QSettings, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut, QAction

from ..core.events import EventBus
from ..core.config import ConfigManager
from ..core.state import StateManager
from .base import BaseUIComponent
from .actions import ActionManager

logger = logging.getLogger(__name__)


class ShortcutContext(Enum):
    """Shortcut activation contexts."""
    APPLICATION = Qt.ShortcutContext.ApplicationShortcut
    WINDOW = Qt.ShortcutContext.WindowShortcut
    WIDGET = Qt.ShortcutContext.WidgetShortcut


@dataclass
class ShortcutDefinition:
    """Definition for a keyboard shortcut."""
    name: str
    sequence: str
    description: str
    context: ShortcutContext = ShortcutContext.WINDOW
    enabled: bool = True
    action_name: Optional[str] = None
    handler: Optional[Callable] = None


class ShortcutManager(BaseUIComponent):
    """Advanced keyboard shortcut management with conflict detection."""
    
    # Signals
    shortcut_activated = pyqtSignal(str)  # shortcut_name
    shortcut_conflict = pyqtSignal(str, list)  # sequence, conflicting_names
    shortcut_changed = pyqtSignal(str, str, str)  # shortcut_name, old_sequence, new_sequence
    
    def __init__(
        self,
        main_window: QMainWindow,
        action_manager: Optional[ActionManager] = None,
        event_bus: Optional[EventBus] = None,
        config_manager: Optional[ConfigManager] = None,
        state_manager: Optional[StateManager] = None,
        parent: Optional[QObject] = None
    ):
        super().__init__(event_bus, config_manager, state_manager, parent)
        
        self._main_window = main_window
        self._action_manager = action_manager
        
        # Shortcut storage
        self._shortcuts: Dict[str, QShortcut] = {}
        self._definitions: Dict[str, ShortcutDefinition] = {}
        self._sequence_map: Dict[str, Set[str]] = {}  # sequence -> shortcut_names
        
        # Conflict tracking
        self._conflicts: Dict[str, List[str]] = {}  # sequence -> conflicting_names
        
        # Settings for persistence
        self._settings = QSettings("ToreMatrix", "ToreMatrixV3")
        
        # Default shortcuts
        self._setup_default_shortcuts()
    
    def _setup_component(self) -> None:
        """Setup the shortcut management system."""
        self._load_shortcut_customizations()
        self._validate_all_shortcuts()
    
    def _setup_default_shortcuts(self) -> None:
        """Setup default application shortcuts."""
        default_shortcuts = [
            # File operations
            ShortcutDefinition("file_new", "Ctrl+N", "Create new project", action_name="file_new"),
            ShortcutDefinition("file_open", "Ctrl+O", "Open existing project", action_name="file_open"),
            ShortcutDefinition("file_save", "Ctrl+S", "Save current project", action_name="file_save"),
            ShortcutDefinition("file_save_as", "Ctrl+Shift+S", "Save project as", action_name="file_save_as"),
            ShortcutDefinition("file_export", "Ctrl+E", "Export project data", action_name="file_export"),
            ShortcutDefinition("file_quit", "Ctrl+Q", "Quit application", action_name="file_exit"),
            
            # Edit operations
            ShortcutDefinition("edit_undo", "Ctrl+Z", "Undo last action", action_name="edit_undo"),
            ShortcutDefinition("edit_redo", "Ctrl+Y", "Redo last action", action_name="edit_redo"),
            ShortcutDefinition("edit_cut", "Ctrl+X", "Cut selection", action_name="edit_cut"),
            ShortcutDefinition("edit_copy", "Ctrl+C", "Copy selection", action_name="edit_copy"),
            ShortcutDefinition("edit_paste", "Ctrl+V", "Paste from clipboard", action_name="edit_paste"),
            ShortcutDefinition("edit_select_all", "Ctrl+A", "Select all", action_name="edit_select_all"),
            ShortcutDefinition("edit_preferences", "Ctrl+,", "Open preferences", action_name="edit_preferences"),
            
            # View operations
            ShortcutDefinition("view_zoom_in", "Ctrl++", "Zoom in", action_name="view_zoom_in"),
            ShortcutDefinition("view_zoom_out", "Ctrl+-", "Zoom out", action_name="view_zoom_out"),
            ShortcutDefinition("view_zoom_reset", "Ctrl+0", "Reset zoom", action_name="view_zoom_reset"),
            ShortcutDefinition("view_fullscreen", "F11", "Toggle fullscreen", action_name="view_fullscreen"),
            ShortcutDefinition("view_sidebar", "Ctrl+B", "Toggle sidebar", action_name="view_toggle_sidebar"),
            
            # Tool operations
            ShortcutDefinition("tools_process", "F5", "Process document", action_name="tools_process_document"),
            ShortcutDefinition("tools_validate", "F6", "Validate project", action_name="tools_validate_project"),
            ShortcutDefinition("tools_export", "F7", "Export data", action_name="tools_export_data"),
            
            # Help
            ShortcutDefinition("help_docs", "F1", "Open documentation", action_name="help_documentation"),
            ShortcutDefinition("help_shortcuts", "Ctrl+?", "Show shortcuts", action_name="help_keyboard_shortcuts"),
            
            # Navigation
            ShortcutDefinition("nav_next_tab", "Ctrl+Tab", "Next tab"),
            ShortcutDefinition("nav_prev_tab", "Ctrl+Shift+Tab", "Previous tab"),
            ShortcutDefinition("nav_close_tab", "Ctrl+W", "Close current tab"),
            
            # Search and find
            ShortcutDefinition("search_find", "Ctrl+F", "Find in document"),
            ShortcutDefinition("search_replace", "Ctrl+H", "Find and replace"),
            ShortcutDefinition("search_next", "F3", "Find next"),
            ShortcutDefinition("search_prev", "Shift+F3", "Find previous"),
            
            # Window management
            ShortcutDefinition("window_minimize", "Ctrl+M", "Minimize window"),
            ShortcutDefinition("window_maximize", "Ctrl+Shift+M", "Maximize window"),
            ShortcutDefinition("window_close", "Alt+F4", "Close window"),
        ]
        
        # Register default shortcuts
        for shortcut_def in default_shortcuts:
            self._definitions[shortcut_def.name] = shortcut_def
    
    def register_shortcut(
        self,
        name: str,
        sequence: str,
        description: str,
        context: ShortcutContext = ShortcutContext.WINDOW,
        action_name: Optional[str] = None,
        handler: Optional[Callable] = None,
        enabled: bool = True
    ) -> bool:
        """Register a new keyboard shortcut."""
        if name in self._shortcuts:
            logger.warning(f"Shortcut {name} already exists")
            return False
        
        # Create definition
        definition = ShortcutDefinition(
            name=name,
            sequence=sequence,
            description=description,
            context=context,
            enabled=enabled,
            action_name=action_name,
            handler=handler
        )
        
        return self._create_shortcut_from_definition(definition)
    
    def _create_shortcut_from_definition(self, definition: ShortcutDefinition) -> bool:
        """Create QShortcut from definition."""
        try:
            # Parse key sequence
            key_sequence = QKeySequence(definition.sequence)
            if key_sequence.isEmpty():
                logger.warning(f"Invalid key sequence: {definition.sequence}")
                return False
            
            # Check for conflicts
            sequence_str = key_sequence.toString()
            if self._has_conflict(sequence_str, definition.name):
                self._add_conflict(sequence_str, definition.name)
                self.shortcut_conflict.emit(sequence_str, self._conflicts[sequence_str])
            
            # Create shortcut
            parent_widget = self._get_context_widget(definition.context)
            shortcut = QShortcut(key_sequence, parent_widget)
            shortcut.setContext(definition.context.value)
            shortcut.setEnabled(definition.enabled)
            
            # Connect handler
            if definition.action_name and self._action_manager:
                action = self._action_manager.get_action(definition.action_name)
                if action:
                    shortcut.activated.connect(action.trigger)
                else:
                    logger.warning(f"Action {definition.action_name} not found for shortcut {definition.name}")
            elif definition.handler:
                shortcut.activated.connect(definition.handler)
            else:
                shortcut.activated.connect(lambda: self._handle_shortcut_activated(definition.name))
            
            # Store shortcut and definition
            self._shortcuts[definition.name] = shortcut
            self._definitions[definition.name] = definition
            self._add_to_sequence_map(sequence_str, definition.name)
            
            logger.debug(f"Registered shortcut: {definition.name} -> {sequence_str}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create shortcut {definition.name}: {e}")
            return False
    
    def _get_context_widget(self, context: ShortcutContext) -> QWidget:
        """Get appropriate parent widget for shortcut context."""
        if context == ShortcutContext.APPLICATION:
            return None  # Application-wide
        elif context == ShortcutContext.WINDOW:
            return self._main_window
        else:
            return self._main_window  # Default to window
    
    def _has_conflict(self, sequence: str, shortcut_name: str) -> bool:
        """Check if sequence conflicts with existing shortcuts."""
        if sequence in self._sequence_map:
            existing = self._sequence_map[sequence]
            return len(existing) > 0 and shortcut_name not in existing
        return False
    
    def _add_conflict(self, sequence: str, shortcut_name: str) -> None:
        """Add shortcut to conflict tracking."""
        if sequence not in self._conflicts:
            self._conflicts[sequence] = []
        
        # Add existing shortcuts to conflict list
        if sequence in self._sequence_map:
            for name in self._sequence_map[sequence]:
                if name not in self._conflicts[sequence]:
                    self._conflicts[sequence].append(name)
        
        # Add new shortcut to conflict list
        if shortcut_name not in self._conflicts[sequence]:
            self._conflicts[sequence].append(shortcut_name)
    
    def _add_to_sequence_map(self, sequence: str, shortcut_name: str) -> None:
        """Add shortcut to sequence mapping."""
        if sequence not in self._sequence_map:
            self._sequence_map[sequence] = set()
        self._sequence_map[sequence].add(shortcut_name)
    
    def _handle_shortcut_activated(self, shortcut_name: str) -> None:
        """Handle shortcut activation when no specific handler is set."""
        self.shortcut_activated.emit(shortcut_name)
        self.publish_event("shortcut.activated", {"shortcut_name": shortcut_name})
    
    def create_all_shortcuts(self) -> None:
        """Create all registered shortcuts."""
        for definition in self._definitions.values():
            if definition.name not in self._shortcuts:
                self._create_shortcut_from_definition(definition)
    
    def change_shortcut(self, shortcut_name: str, new_sequence: str) -> bool:
        """Change the key sequence for an existing shortcut."""
        if shortcut_name not in self._shortcuts:
            return False
        
        definition = self._definitions[shortcut_name]
        old_sequence = definition.sequence
        
        # Parse new sequence
        key_sequence = QKeySequence(new_sequence)
        if key_sequence.isEmpty():
            logger.warning(f"Invalid key sequence: {new_sequence}")
            return False
        
        sequence_str = key_sequence.toString()
        
        # Check for conflicts
        if self._has_conflict(sequence_str, shortcut_name):
            self._add_conflict(sequence_str, shortcut_name)
            self.shortcut_conflict.emit(sequence_str, self._conflicts[sequence_str])
            return False
        
        # Update shortcut
        shortcut = self._shortcuts[shortcut_name]
        shortcut.setKey(key_sequence)
        
        # Update definition
        definition.sequence = new_sequence
        
        # Update sequence mapping
        self._remove_from_sequence_map(old_sequence, shortcut_name)
        self._add_to_sequence_map(sequence_str, shortcut_name)
        
        # Save customization
        self._save_shortcut_customization(shortcut_name, new_sequence)
        
        # Emit signal
        self.shortcut_changed.emit(shortcut_name, old_sequence, new_sequence)
        
        logger.info(f"Changed shortcut {shortcut_name}: {old_sequence} -> {new_sequence}")
        return True
    
    def _remove_from_sequence_map(self, sequence: str, shortcut_name: str) -> None:
        """Remove shortcut from sequence mapping."""
        if sequence in self._sequence_map:
            self._sequence_map[sequence].discard(shortcut_name)
            if not self._sequence_map[sequence]:
                del self._sequence_map[sequence]
    
    def enable_shortcut(self, shortcut_name: str, enabled: bool = True) -> bool:
        """Enable or disable a shortcut."""
        if shortcut_name not in self._shortcuts:
            return False
        
        shortcut = self._shortcuts[shortcut_name]
        shortcut.setEnabled(enabled)
        
        # Update definition
        self._definitions[shortcut_name].enabled = enabled
        
        return True
    
    def disable_shortcut(self, shortcut_name: str) -> bool:
        """Disable a shortcut."""
        return self.enable_shortcut(shortcut_name, False)
    
    def remove_shortcut(self, shortcut_name: str) -> bool:
        """Remove a shortcut completely."""
        if shortcut_name not in self._shortcuts:
            return False
        
        shortcut = self._shortcuts[shortcut_name]
        definition = self._definitions[shortcut_name]
        
        # Remove from sequence mapping
        self._remove_from_sequence_map(definition.sequence, shortcut_name)
        
        # Delete shortcut
        shortcut.setEnabled(False)
        shortcut.deleteLater()
        
        # Remove from storage
        del self._shortcuts[shortcut_name]
        del self._definitions[shortcut_name]
        
        logger.debug(f"Removed shortcut: {shortcut_name}")
        return True
    
    def get_shortcut_conflicts(self) -> Dict[str, List[str]]:
        """Get all shortcut conflicts."""
        return self._conflicts.copy()
    
    def resolve_conflict(self, sequence: str, preferred_shortcut: str) -> bool:
        """Resolve shortcut conflict by disabling others."""
        if sequence not in self._conflicts:
            return False
        
        conflicting = self._conflicts[sequence]
        if preferred_shortcut not in conflicting:
            return False
        
        # Disable all conflicting shortcuts except preferred
        for shortcut_name in conflicting:
            if shortcut_name != preferred_shortcut:
                self.disable_shortcut(shortcut_name)
        
        # Remove from conflicts
        del self._conflicts[sequence]
        
        logger.info(f"Resolved conflict for {sequence}: {preferred_shortcut} enabled")
        return True
    
    def get_shortcut_info(self, shortcut_name: str) -> Optional[ShortcutDefinition]:
        """Get shortcut information."""
        return self._definitions.get(shortcut_name)
    
    def get_all_shortcuts(self) -> Dict[str, ShortcutDefinition]:
        """Get all shortcut definitions."""
        return self._definitions.copy()
    
    def get_shortcuts_by_context(self, context: ShortcutContext) -> Dict[str, ShortcutDefinition]:
        """Get shortcuts by context."""
        return {
            name: definition for name, definition in self._definitions.items()
            if definition.context == context
        }
    
    def find_shortcut_by_sequence(self, sequence: str) -> List[str]:
        """Find shortcuts using specific sequence."""
        return list(self._sequence_map.get(sequence, set()))
    
    def is_sequence_available(self, sequence: str, exclude_shortcut: Optional[str] = None) -> bool:
        """Check if a key sequence is available."""
        if sequence not in self._sequence_map:
            return True
        
        shortcuts = self._sequence_map[sequence]
        if exclude_shortcut:
            shortcuts = shortcuts - {exclude_shortcut}
        
        return len(shortcuts) == 0
    
    def _validate_all_shortcuts(self) -> None:
        """Validate all shortcuts and detect conflicts."""
        sequence_count = {}
        
        for name, definition in self._definitions.items():
            sequence = definition.sequence
            if sequence in sequence_count:
                sequence_count[sequence].append(name)
            else:
                sequence_count[sequence] = [name]
        
        # Find conflicts
        for sequence, shortcuts in sequence_count.items():
            if len(shortcuts) > 1:
                self._conflicts[sequence] = shortcuts
                self.shortcut_conflict.emit(sequence, shortcuts)
    
    def _save_shortcut_customization(self, shortcut_name: str, sequence: str) -> None:
        """Save customized shortcut to settings."""
        self._settings.beginGroup("shortcuts")
        self._settings.setValue(shortcut_name, sequence)
        self._settings.endGroup()
    
    def _load_shortcut_customizations(self) -> None:
        """Load customized shortcuts from settings."""
        self._settings.beginGroup("shortcuts")
        
        for shortcut_name in self._settings.childKeys():
            if shortcut_name in self._definitions:
                custom_sequence = self._settings.value(shortcut_name, "", str)
                if custom_sequence:
                    definition = self._definitions[shortcut_name]
                    definition.sequence = custom_sequence
        
        self._settings.endGroup()
    
    def reset_shortcut_to_default(self, shortcut_name: str) -> bool:
        """Reset shortcut to its default sequence."""
        # This would require storing original defaults
        # For now, we can't implement this without additional data structure
        logger.warning(f"Reset to default not implemented for {shortcut_name}")
        return False
    
    def reset_all_shortcuts(self) -> None:
        """Reset all shortcuts to defaults."""
        logger.warning("Reset all shortcuts not implemented")
    
    def export_shortcuts(self) -> Dict[str, str]:
        """Export all shortcuts as name -> sequence mapping."""
        return {name: definition.sequence for name, definition in self._definitions.items()}
    
    def import_shortcuts(self, shortcuts: Dict[str, str]) -> int:
        """Import shortcuts from mapping. Returns number of successfully imported."""
        imported = 0
        for name, sequence in shortcuts.items():
            if name in self._definitions and self.change_shortcut(name, sequence):
                imported += 1
        return imported