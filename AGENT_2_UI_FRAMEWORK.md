# AGENT 2 - UI Framework Actions & Resource Management

## 🎯 Mission: Actions, Menus & Resource Management
**Timeline: Day 2 | Focus: Data Structures & Persistence**

## 📋 Your Sub-Issue: #110
[UI Framework] Sub-Issue #11.2: Actions, Menus & Resource Management

## 🏗️ Core Responsibilities
1. **Action System** - Complete QAction management with shortcuts
2. **Menu Construction** - Build comprehensive menubar system
3. **Resource Management** - Implement .qrc system and asset loading
4. **Toolbar System** - Create configurable toolbar with icons
5. **Settings Persistence** - Save/restore action states and preferences

## 📁 Files You'll Create/Modify
```
src/torematrix/ui/
├── actions.py                     # 🎯 YOUR MAIN FOCUS - Action management
├── menus.py                       # Menu construction and organization
├── resources.qrc                  # Resource file definitions
├── shortcuts.py                   # Keyboard shortcut management
└── icons/                         # Icon assets directory
    ├── app_icon.svg
    ├── toolbar/
    └── menu/

tests/unit/ui/
├── test_actions.py                # 🎯 YOUR TESTS
├── test_menus.py
└── test_resources.py
```

## 🔧 Technical Implementation Details

### Action Manager Structure
```python
class ActionManager:
    """Centralized action management with shortcuts and persistence."""
    
    def __init__(self, main_window, config_manager, event_bus)
    def create_action(self, name: str, text: str, shortcut: str = None) -> QAction
    def register_action_group(self, group_name: str, actions: List[QAction])
    def setup_shortcuts(self)
    def save_action_states(self)
    def restore_action_states(self)
```

### Menu System Structure  
```python
class MenuBuilder:
    """Dynamic menu construction with proper organization."""
    
    def __init__(self, action_manager, main_window)
    def build_file_menu(self) -> QMenu
    def build_edit_menu(self) -> QMenu
    def build_view_menu(self) -> QMenu
    def build_tools_menu(self) -> QMenu
    def build_help_menu(self) -> QMenu
```

### Key Technical Requirements
- **QAction and QActionGroup** for organized action management
- **Keyboard shortcuts** with conflict detection
- **Resource compilation** (.qrc to .py)
- **Icon loading** with fallbacks and caching
- **Dynamic menu construction** based on context
- **Action state persistence** using QSettings

## 🔗 Integration Points
- **Agent 1 (Core Window)**: Use menubar/toolbar containers from Day 1
- **Agent 3 (Performance/Themes)**: Provide theming hooks for icons/menus
- **Agent 4 (Integration/Panels)**: Expose action system for panel integration

## 🎨 Resource System Requirements
```
resources.qrc structure:
- Application icons (16x16, 32x32, 64x64, 128x128)
- Toolbar icons (24x24 standard, 32x32 high DPI)
- Menu icons (16x16 standard, 24x24 high DPI)  
- Status indicators
- Theme-aware icons (light/dark variants)
```

## 🎹 Standard Application Actions
```python
STANDARD_ACTIONS = {
    'file_new': ('&New', 'Ctrl+N', 'Create new project'),
    'file_open': ('&Open...', 'Ctrl+O', 'Open existing project'),
    'file_save': ('&Save', 'Ctrl+S', 'Save current project'),
    'file_save_as': ('Save &As...', 'Ctrl+Shift+S', 'Save project with new name'),
    'file_export': ('&Export...', 'Ctrl+E', 'Export project data'),
    'file_exit': ('E&xit', 'Alt+F4', 'Exit application'),
    
    'edit_undo': ('&Undo', 'Ctrl+Z', 'Undo last action'),
    'edit_redo': ('&Redo', 'Ctrl+Y', 'Redo last undone action'),
    'edit_cut': ('Cu&t', 'Ctrl+X', 'Cut selection'),
    'edit_copy': ('&Copy', 'Ctrl+C', 'Copy selection'),
    'edit_paste': ('&Paste', 'Ctrl+V', 'Paste from clipboard'),
    'edit_preferences': ('&Preferences...', 'Ctrl+,', 'Open preferences'),
    
    'view_zoom_in': ('Zoom &In', 'Ctrl++', 'Increase zoom level'),
    'view_zoom_out': ('Zoom &Out', 'Ctrl+-', 'Decrease zoom level'),
    'view_zoom_reset': ('&Reset Zoom', 'Ctrl+0', 'Reset zoom to 100%'),
    'view_fullscreen': ('&Full Screen', 'F11', 'Toggle full screen mode'),
    
    'help_about': ('&About', '', 'About this application'),
    'help_documentation': ('&Documentation', 'F1', 'Open documentation'),
}
```

## 🧪 Testing Requirements
- **Action creation** and registration tests
- **Keyboard shortcut** conflict detection tests
- **Menu construction** and hierarchy tests
- **Resource loading** and caching tests
- **Settings persistence** tests
- **>95% code coverage** requirement

## ⚡ Success Criteria Checklist
- [ ] Complete action system with all standard actions
- [ ] Full menubar with proper organization
- [ ] Configurable toolbar working
- [ ] All keyboard shortcuts functional
- [ ] Resource system loading icons correctly
- [ ] Action states persist between sessions
- [ ] Comprehensive test coverage

## 📅 Day 2 Completion Target
By end of Day 2, Agent 3 and 4 should have:
- Complete action system to work with
- Fully functional menus and toolbars
- Resource system ready for theming
- Action persistence foundation

## 📞 Dependencies You'll Use
- ✅ **Agent 1 Output** - MainWindow containers (Day 1)
- ✅ **Configuration Management** (#5) - For action settings
- ✅ **Event Bus System** (#1) - For action triggers

Focus on creating a comprehensive, extensible action and resource system!