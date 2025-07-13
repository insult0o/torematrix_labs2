# AGENT 1 - UI Framework Core Foundation

## 🎯 Mission: Core Main Window & Foundation Components
**Timeline: Day 1 | Focus: Solid Architectural Foundation**

## 📋 Your Sub-Issue: #109
[UI Framework] Sub-Issue #11.1: Core Main Window & Foundation Components

## 🏗️ Core Responsibilities
1. **QMainWindow Foundation** - Implement robust base window class
2. **Layout Architecture** - Create flexible layout system foundation  
3. **Window Lifecycle** - Handle initialization, show, close properly
4. **Base Patterns** - Establish reusable UI component patterns
5. **Resource Management** - Set up foundation for asset loading

## 📁 Files You'll Create/Modify
```
src/torematrix/ui/
├── __init__.py                    # UI package initialization
├── main_window.py                 # 🎯 YOUR MAIN FOCUS - Core window class
├── base.py                        # Base UI component classes
└── exceptions.py                  # UI-specific exceptions

tests/unit/ui/
├── __init__.py
├── test_main_window_core.py       # 🎯 YOUR TESTS
└── conftest.py                    # PyQt test fixtures
```

## 🔧 Technical Implementation Details

### MainWindow Class Structure
```python
class MainWindow(QMainWindow):
    """Core application main window with modern PyQt6 patterns."""
    
    # Core lifecycle methods
    def __init__(self, config_manager, event_bus, state_store)
    def setup_ui(self)
    def show_application(self)
    def close_application(self)
    
    # Foundation methods for other agents
    def get_central_widget(self) -> QWidget
    def get_menubar_container(self) -> QMenuBar  
    def get_toolbar_container(self) -> QToolBar
    def get_statusbar_container(self) -> QStatusBar
```

### Key Technical Requirements
- **PyQt6 QMainWindow** as base class
- **Modern Python patterns** (type hints, dataclasses, async where applicable)
- **Dependency injection** for config, event bus, state store
- **Cross-platform compatibility** (Windows, macOS, Linux)
- **High DPI support** foundation
- **Proper resource cleanup** on close

## 🔗 Integration Points for Other Agents
- **Agent 2 (Actions/Menus)**: Provide menubar/toolbar containers
- **Agent 3 (Performance/Themes)**: Expose theming hooks and layout containers  
- **Agent 4 (Integration/Panels)**: Provide docking areas and state persistence hooks

## 🧪 Testing Requirements
- **Unit tests** for all core methods
- **Window lifecycle** testing (init, show, close)
- **Cross-platform** compatibility tests
- **Memory leak** prevention tests
- **>95% code coverage** requirement

## ⚡ Success Criteria Checklist
- [ ] MainWindow class displays correctly on all platforms
- [ ] Basic layout structure functional
- [ ] Clean separation of concerns established
- [ ] Foundation hooks ready for other agents
- [ ] Comprehensive unit test suite
- [ ] Memory management verified
- [ ] Documentation complete

## 🎯 Day 1 Completion Target
By end of Day 1, other agents should be able to:
- Instantiate MainWindow successfully
- Access menubar/toolbar/statusbar containers
- Hook into window lifecycle events
- Build upon your foundation classes

## 📞 Dependencies You Can Use
- ✅ **Configuration Management** (#5) - Use for window settings
- ✅ **Event Bus System** (#1) - Use for window events  
- ✅ **State Management** (#3) - Use for window state

Focus on creating a rock-solid foundation that other agents can build upon!