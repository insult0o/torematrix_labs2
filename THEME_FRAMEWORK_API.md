# Theme Framework API Documentation

## Overview

The Theme Framework provides a comprehensive system for managing UI themes in TORE Matrix Labs V3. This document describes the APIs available for other agents to build upon.

## Core Components

### ThemeEngine - Main Interface

The `ThemeEngine` is the primary interface for theme management:

```python
from torematrix.ui.themes import ThemeEngine

# Initialize (requires ConfigManager and EventBus)
engine = ThemeEngine(config_manager, event_bus)

# Load and switch themes
theme = engine.load_theme('dark')
success = engine.switch_theme('light')

# Get current state
current_theme = engine.get_current_theme()
available_themes = engine.get_available_themes()

# Register providers and callbacks
engine.register_theme_provider(custom_provider)
engine.register_theme_change_callback(my_callback)
```

### Theme Class - Theme Data Access

Access theme data through the `Theme` class:

```python
# Get color palette and typography
color_palette = theme.get_color_palette()
typography = theme.get_typography()

# Access properties by path
primary_color = theme.get_property('colors.primary')
font_size = theme.get_property('typography.default.font_size')

# Generate stylesheets
stylesheet = theme.generate_stylesheet()

# Component-specific styles
main_window_styles = theme.get_component_styles(ComponentType.MAIN_WINDOW)
```

### ColorPalette - Color Management

Work with colors through the `ColorPalette` class:

```python
palette = theme.get_color_palette()

# Get colors as QColor objects
primary_qcolor = palette.get_color('primary')
background_qcolor = palette.get_color('background', '#ffffff')

# Get raw color values
primary_hex = palette.get_color_value('primary')

# Check accessibility
accessibility_results = palette.validate_accessibility()
```

### Typography - Font Management

Manage fonts through the `Typography` class:

```python
typography = theme.get_typography()

# Get fonts as QFont objects
default_font = typography.get_font('default')
heading_font = typography.get_font('heading', scale_factor=1.2)

# Control scaling
typography.set_scale_factor(1.5)
current_scale = typography.get_scale_factor()
```

## Integration Points for Other Agents

### Agent 2: Color Palettes & Typography System

**What you can use from Agent 1:**
```python
# Hook into theme loading
engine.register_theme_change_callback(on_theme_change)

# Extend color palette functionality
class AdvancedColorPalette(ColorPalette):
    def calculate_variations(self): ...
    def ensure_accessibility(self): ...

# Register custom typography providers
class TypographyProvider(ThemeProvider):
    def load_theme(self, name): ...

engine.register_theme_provider(TypographyProvider())
```

**APIs you should implement:**
- Advanced color management with WCAG compliance
- Color theory algorithms (HSV, contrast calculation)
- Typography scaling and font loading
- Built-in professional color palettes

### Agent 3: StyleSheet Generation & Performance

**What you can use from Agent 1:**
```python
# Access theme data for stylesheet generation
theme_data = theme._data
colors = theme.get_color_palette()
typography = theme.get_typography()

# Override stylesheet generation
class AdvancedTheme(Theme):
    def generate_stylesheet(self) -> str:
        # Your advanced generation logic
        return super_advanced_stylesheet

# Hook into theme application
def on_theme_applied(theme_name):
    # Trigger hot reload or cache invalidation
    pass

engine.register_theme_change_callback(on_theme_applied)
```

**APIs you should implement:**
- Advanced Qt StyleSheet generation
- CSS preprocessing with variables
- Hot reload file watching
- Performance optimization and caching

### Agent 4: Icon Theming & Integration

**What you can use from Agent 1:**
```python
# Access current theme for icon selection
current_theme = engine.get_current_theme()
theme_category = current_theme.metadata.category

# Register for theme changes
def update_icons_on_theme_change(theme):
    if theme.metadata.requires_icons:
        # Update all themed icons
        pass

engine.register_theme_change_callback(update_icons_on_theme_change)

# Access component styles for integration
button_styles = theme.get_component_styles(ComponentType.BUTTON)
```

**APIs you should implement:**
- SVG icon theming and colorization
- UI component integration
- Accessibility enhancements
- Custom theme creation tools

## Theme File Format

Themes use YAML/JSON format with the following structure:

```yaml
metadata:
  name: "Professional Dark"
  version: "1.0.0"
  description: "Professional dark theme"
  author: "TORE Matrix Labs"
  category: "dark"
  accessibility_compliant: true

colors:
  primary: "#2196F3"
  secondary: "#FF9800"
  background: "#121212"
  surface: "#1E1E1E"
  text_primary: "#FFFFFF"
  # ... more colors

typography:
  default:
    font_family: "Segoe UI"
    font_size: 12
    font_weight: 400
    line_height: 1.4
  heading:
    font_family: "Segoe UI"
    font_size: 16
    font_weight: 600

components:
  main_window:
    background: "${colors.background}"
    border: "none"
  menu_bar:
    background: "${colors.surface}"
    color: "${colors.text_primary}"

variables:
  border_radius: "4px"
  animation_duration: "200ms"
```

## Events and Signals

### Qt Signals
```python
# Theme engine signals
engine.theme_loading.connect(on_theme_loading)     # str: theme_name
engine.theme_loaded.connect(on_theme_loaded)       # str: theme_name  
engine.theme_changed.connect(on_theme_changed)     # str: new_theme, str: previous_theme
engine.theme_error.connect(on_theme_error)         # str: theme_name, str: error_message
```

### Event Bus Events
```python
# Listen for theme events
event_bus.subscribe('theme.changed', handle_theme_change)
event_bus.subscribe('theme.applied', handle_theme_applied)

# Event data structure
{
    'theme_name': 'dark',
    'previous_theme': 'light',
    'timestamp': 1234567890.0
}
```

## Custom Theme Providers

Create custom theme providers by implementing the `ThemeProvider` interface:

```python
from torematrix.ui.themes.base import ThemeProvider

class DatabaseThemeProvider(ThemeProvider):
    def load_theme(self, theme_name: str) -> Theme:
        # Load from database
        theme_data = self.db.get_theme(theme_name)
        return self._create_theme(theme_name, theme_data)
    
    def get_available_themes(self) -> List[str]:
        return self.db.list_themes()
    
    def theme_exists(self, theme_name: str) -> bool:
        return self.db.theme_exists(theme_name)

# Register with engine
engine.register_theme_provider(DatabaseThemeProvider())
```

## Error Handling

Use the provided exception types for consistent error handling:

```python
from torematrix.ui.themes.exceptions import (
    ThemeNotFoundError, ThemeValidationError, 
    ThemeLoadError, StyleSheetGenerationError
)

try:
    theme = engine.load_theme('custom_theme')
except ThemeNotFoundError as e:
    print(f"Theme not found: {e.theme_name}")
except ThemeValidationError as e:
    print(f"Validation error in {e.field}: {e}")
except ThemeLoadError as e:
    print(f"Load error: {e.reason}")
```

## Performance Considerations

- Themes are cached automatically by default
- Use `engine.get_performance_stats()` to monitor loading times
- Clear cache when needed: `engine.clear_cache()`
- Theme providers should implement their own caching

## Testing Utilities

Mock objects are available for testing:

```python
# Test fixtures available in conftest.py
def test_my_feature(theme_engine, sample_theme, qapp):
    # Use provided fixtures
    theme_engine.switch_theme('light')
    assert theme_engine.current_theme is not None
```

## Migration Guide

For existing code using the old theme system:

```python
# Old way
theme_manager = ThemeManager(...)
theme_manager.load_theme('dark')

# New way  
theme_engine = ThemeEngine(config_manager, event_bus)
theme_engine.switch_theme('dark')
```

## Best Practices

1. **Always handle exceptions** when loading themes
2. **Use callbacks** for theme change notifications rather than polling
3. **Cache expensive operations** in your theme extensions
4. **Validate theme data** before using it
5. **Test with multiple themes** to ensure compatibility
6. **Use the event bus** for loose coupling between components

## Agent Coordination Notes

- **Agent 1** provides the foundation and core theme loading
- **Agent 2** extends with advanced color/typography features
- **Agent 3** adds sophisticated stylesheet generation and performance
- **Agent 4** completes with icons, UI integration, and production features

Each agent should build upon the previous work while maintaining backward compatibility.