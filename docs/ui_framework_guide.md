# ToreMatrix V3 UI Framework Guide

## Overview

The ToreMatrix V3 UI Framework is a comprehensive, enterprise-grade user interface system built on PyQt6. It provides a complete set of components for building professional document processing applications with advanced features like dockable panels, theme management, state persistence, and cross-platform compatibility.

## Architecture

### Core Components

The UI Framework consists of four main layers:

1. **Foundation Layer (Agent 1)** - Core window and base components
2. **Data Layer (Agent 2)** - Actions, menus, and resource management  
3. **Presentation Layer (Agent 3)** - Themes, layouts, and performance optimization
4. **Integration Layer (Agent 4)** - Panels, persistence, and production features

### Component Integration

```
┌─────────────────────────────────────────────────────┐
│                 Main Window                          │
├─────────────────────────────────────────────────────┤
│  Panel Manager  │  Status Bar  │  Window Manager    │
├─────────────────────────────────────────────────────┤
│  Theme Manager  │  Performance │  Layout System     │
├─────────────────────────────────────────────────────┤
│  Action System  │  Menu Builder│  Resource Manager  │
├─────────────────────────────────────────────────────┤
│              Foundation Components                  │
└─────────────────────────────────────────────────────┘
```

## Key Features

### 1. Dockable Panel System

- **Flexible docking** - Panels can be docked to any side or floated
- **State persistence** - Panel layouts are saved and restored
- **Custom panels** - Easy to create application-specific panels
- **Standard panels** - Project explorer, properties, console, log viewer

```python
from torematrix.ui.panels import PanelManager, PanelConfig

# Create panel manager
panel_manager = PanelManager(main_window, config_manager, event_bus)

# Create custom panel
config = PanelConfig(
    panel_id="my_panel",
    title="My Panel",
    default_area=Qt.DockWidgetArea.RightDockWidgetArea
)
panel_manager.register_panel(config)
panel_manager.show_panel("my_panel")
```

### 2. Advanced Status Bar

- **Progress tracking** - Built-in progress indicators with cancellation
- **Status indicators** - LED, text, icon, and custom indicators  
- **System monitoring** - Memory usage, connection status, etc.
- **Event integration** - Responds to application events

```python
from torematrix.ui.statusbar import StatusBarManager

status_manager = StatusBarManager(main_window, event_bus)

# Show progress
status_manager.show_progress("operation_1", 50, 100, "Processing...")

# Update indicator
status_manager.update_indicator("memory_usage", "45.2MB")
```

### 3. Window State Persistence

- **Complete state saving** - Window geometry, panel layouts, splitter states
- **Multiple scopes** - Global, project, session, and temporary persistence
- **Cross-platform** - Handles different screen configurations
- **Automatic tracking** - Widgets can be automatically tracked

```python
from torematrix.ui.persistence import WindowPersistence, PersistenceScope

persistence = WindowPersistence(main_window, config_manager, PersistenceScope.GLOBAL)

# Save current state
persistence.save_window_state()

# Restore previous state
persistence.restore_window_state()
```

### 4. Window Management

- **Multi-window support** - Manage multiple application windows
- **Dialog management** - Standard and custom dialogs
- **System tray** - System tray icon with notifications
- **Window arrangement** - Cascade and tile window layouts

```python
from torematrix.ui.window_manager import WindowManager

window_manager = WindowManager(main_window, event_bus)

# Show message box
result = window_manager.show_message_box("Title", "Message")

# Create secondary window
window = window_manager.create_window(MyWindowClass, "secondary_1")
```

### 5. Theme System

- **Dark/Light themes** - Professional built-in themes
- **Smooth transitions** - Animated theme switching
- **Custom themes** - Support for custom theme creation
- **System integration** - Auto-detection of system theme

### 6. Splash Screen

- **Professional startup** - Branded splash screen with progress
- **Task management** - Organized loading task execution
- **Animations** - Smooth fade in/out animations
- **Customizable** - Custom graphics and branding

## Usage Examples

### Basic Setup

```python
from PyQt6.QtWidgets import QApplication, QMainWindow
from torematrix.ui.main_window import MainWindow
from torematrix.ui.panels import PanelManager
from torematrix.ui.statusbar import StatusBarManager
from torematrix.ui.themes import ThemeManager

class MyApplication:
    def __init__(self):
        self.app = QApplication([])
        
        # Create main window
        self.main_window = MainWindow()
        
        # Initialize UI managers
        self.setup_ui_managers()
        
        # Show application
        self.main_window.show()
    
    def setup_ui_managers(self):
        # Panel system
        self.panel_manager = PanelManager(
            self.main_window, 
            self.config_manager, 
            self.event_bus
        )
        
        # Status bar
        self.status_manager = StatusBarManager(
            self.main_window,
            self.event_bus
        )
        
        # Theme system
        self.theme_manager = ThemeManager(
            self.event_bus,
            self.config_manager,
            self.state_manager
        )
        self.theme_manager.apply_theme(ThemeType.DARK)
```

### Custom Panel Creation

```python
from torematrix.ui.panels import BasePanelWidget, PanelConfig

class MyCustomPanel(BasePanelWidget):
    def __init__(self, panel_id: str, parent=None):
        super().__init__(panel_id, parent)
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        label = QLabel("My Custom Panel")
        layout.addWidget(label)
    
    def save_state(self):
        return {"custom_data": "value"}
    
    def restore_state(self, state):
        # Restore panel state
        pass

# Register custom panel
config = PanelConfig(
    panel_id="custom_panel",
    title="Custom Panel",
    default_area=Qt.DockWidgetArea.LeftDockWidgetArea,
    widget_factory=lambda: MyCustomPanel("custom_panel")
)
panel_manager.register_panel(config)
```

### Progress Tracking

```python
# Long running operation with progress
def long_operation():
    total_steps = 100
    
    for i in range(total_steps):
        # Update progress
        status_manager.show_progress(
            "long_op", 
            i + 1, 
            total_steps, 
            f"Step {i + 1} of {total_steps}"
        )
        
        # Do work
        time.sleep(0.1)
    
    # Hide progress when done
    status_manager.hide_progress()
```

## Configuration

### Theme Configuration

```python
# Theme settings
theme_config = {
    'default_theme': 'dark',
    'enable_transitions': True,
    'transition_duration': 200,
    'custom_accent_color': '#0e639c'
}
```

### Panel Configuration

```python
# Panel layout configuration
panel_config = {
    'default_layout': 'standard',
    'auto_save_layout': True,
    'save_interval': 5000,
    'enable_floating': True
}
```

### Performance Configuration

```python
# Performance settings
performance_config = {
    'enable_caching': True,
    'cache_size_mb': 512,
    'enable_profiling': False,
    'optimization_level': 'high'
}
```

## Best Practices

### 1. Component Initialization Order

Always initialize components in this order:
1. Event bus and configuration
2. Main window
3. Panel manager
4. Status bar manager
5. Theme manager
6. Window manager

### 2. Memory Management

- Use weak references for parent-child relationships
- Implement proper cleanup in `closeEvent`
- Track and untrack widgets appropriately
- Use `deleteLater()` for proper Qt object cleanup

### 3. Event Handling

- Use the event bus for cross-component communication
- Implement proper signal-slot connections
- Avoid direct component dependencies
- Use typed events with proper data structures

### 4. State Persistence

- Choose appropriate persistence scope
- Implement `save_state` and `restore_state` for custom widgets
- Test state restoration across application restarts
- Handle missing or corrupted state gracefully

### 5. Cross-Platform Compatibility

- Test on multiple platforms (Windows, macOS, Linux)
- Use platform-specific features appropriately
- Handle different screen DPI settings
- Respect platform UI conventions

## Troubleshooting

### Common Issues

1. **Panels not showing** - Check panel visibility and dock area
2. **State not persisting** - Verify persistence scope and settings
3. **Theme not applying** - Ensure theme manager is initialized
4. **Memory leaks** - Check widget cleanup and references

### Debug Mode

Enable debug mode for additional logging:

```python
import logging
logging.getLogger('torematrix.ui').setLevel(logging.DEBUG)
```

### Performance Monitoring

Use the built-in performance tools:

```python
from torematrix.ui.performance import PerformanceOptimizer

optimizer = PerformanceOptimizer()
optimizer.enable_profiling()
optimizer.start_monitoring()
```

## API Reference

### Core Classes

- `MainWindow` - Main application window
- `PanelManager` - Dockable panel management
- `StatusBarManager` - Status bar and progress tracking
- `WindowPersistence` - State persistence management
- `WindowManager` - Multi-window and dialog management
- `ThemeManager` - Theme and styling management
- `SplashScreen` - Application startup screen

### Configuration Classes

- `PanelConfig` - Panel configuration
- `StatusIndicatorConfig` - Status indicator configuration
- `WindowInfo` - Window information tracking

### Base Classes

- `BaseUIComponent` - Base for all UI components
- `BasePanelWidget` - Base for custom panels
- `ManagedWindow` - Base for managed windows
- `ManagedDialog` - Base for managed dialogs

## Migration Guide

### From V2 to V3

The V3 UI Framework is a complete rewrite with breaking changes:

1. **New architecture** - Component-based instead of monolithic
2. **PyQt6** - Upgraded from PyQt5
3. **Async support** - Full async/await integration
4. **Type hints** - Complete type coverage
5. **Modern styling** - New theme system

### Migration Steps

1. Update imports to new module structure
2. Replace old window management with new managers
3. Update theme configuration format
4. Test all custom panels and dialogs
5. Verify state persistence works correctly

## Contributing

### Development Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Run tests: `pytest tests/`
3. Check coverage: `pytest --cov=torematrix.ui`
4. Run linting: `flake8 src/torematrix/ui/`

### Code Standards

- Follow PEP 8 style guidelines
- Use type hints for all public APIs
- Write comprehensive docstrings
- Include unit and integration tests
- Maintain >95% test coverage

### Submitting Changes

1. Create feature branch from main
2. Implement changes with tests
3. Update documentation
4. Submit pull request with detailed description
5. Ensure all CI checks pass

---

*For more information, see the [API Documentation](api_reference.md) and [Examples](examples/) directory.*