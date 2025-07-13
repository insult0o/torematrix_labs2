# AGENT 3 - Theme Framework StyleSheet Generation & Performance

## 🎯 Mission: StyleSheet Generation & Performance Optimization
**Timeline: Day 3 | Focus: Performance & Development Tools**

## 📋 Your Sub-Issue: #122
[Theme Framework] Sub-Issue #14.3: StyleSheet Generation & Performance Optimization

## 🏗️ Core Responsibilities
1. **Qt StyleSheet Generation** - Convert theme data to efficient Qt stylesheets
2. **Hot Reload System** - Real-time theme updates for development
3. **Performance Optimization** - Fast theme application and memory efficiency
4. **CSS Preprocessing** - Advanced stylesheet compilation and features
5. **Theme Caching** - Intelligent caching and invalidation system

## 📁 Files You'll Create/Modify
```
src/torematrix/ui/themes/
├── styles.py                      # 🎯 YOUR MAIN FOCUS - StyleSheet generation
├── compiler.py                    # Theme compilation and preprocessing
├── performance.py                 # Performance optimization utilities
├── hot_reload.py                  # Development hot reload system
├── cache.py                       # Theme caching system
└── preprocessor.py                # CSS-like preprocessing

tools/theme_dev/
├── __init__.py
├── theme_watcher.py               # File system watching for hot reload
├── performance_profiler.py       # Theme performance profiling
└── style_inspector.py            # StyleSheet debugging tools

tests/unit/ui/themes/
├── test_styles.py                 # 🎯 YOUR TESTS
├── test_compiler.py
├── test_performance.py
└── test_hot_reload.py
```

## 🔧 Technical Implementation Details

### StyleSheet Generator Structure
```python
class StyleSheetGenerator:
    """Advanced Qt StyleSheet generation from theme data."""
    
    def __init__(self, theme_engine, performance_optimizer)
    def generate_stylesheet(self, theme: Theme, target_widgets: List[str] = None) -> str
    def compile_component_styles(self, theme: Theme, component: str) -> str
    def optimize_stylesheet(self, stylesheet: str) -> str
    def validate_stylesheet_syntax(self, stylesheet: str) -> ValidationResult
    def get_generation_metrics(self) -> PerformanceMetrics
```

### Hot Reload System Structure
```python
class HotReloadManager:
    """Real-time theme updates for development workflow."""
    
    def __init__(self, theme_engine, style_generator)
    def start_watching(self, theme_paths: List[str])
    def stop_watching(self)
    def reload_theme(self, theme_name: str, force: bool = False)
    def register_reload_callback(self, callback: Callable)
    def get_reload_history(self) -> List[ReloadEvent]
```

### Key Technical Requirements
- **Efficient Qt StyleSheet** generation with minimal overhead
- **CSS preprocessing** with variables, mixins, and functions
- **Hot reload** with file system watching
- **Theme compilation** with optimization and minification
- **Performance profiling** and optimization tools
- **Memory efficient** caching with smart invalidation

## 🎨 StyleSheet Generation System

### Component-Based Generation
```python
COMPONENT_GENERATORS = {
    'main_window': MainWindowStyleGenerator,
    'menu_bar': MenuBarStyleGenerator,
    'tool_bar': ToolBarStyleGenerator,
    'dock_widget': DockWidgetStyleGenerator,
    'status_bar': StatusBarStyleGenerator,
    'button': ButtonStyleGenerator,
    'input_field': InputFieldStyleGenerator,
    'table': TableStyleGenerator,
    'tree': TreeStyleGenerator,
    'tab_widget': TabWidgetStyleGenerator
}

class ComponentStyleGenerator:
    """Base class for component-specific stylesheet generation."""
    
    def generate(self, theme: Theme, component_config: Dict) -> str:
        """Generate stylesheet for specific component."""
        pass
        
    def get_default_config(self) -> Dict:
        """Get default configuration for this component."""
        pass
        
    def validate_config(self, config: Dict) -> bool:
        """Validate component configuration."""
        pass
```

### CSS Preprocessing Features
```python
class CSSPreprocessor:
    """Advanced CSS preprocessing with theme-aware features."""
    
    def __init__(self, theme: Theme)
    def process_variables(self, css: str) -> str
    def process_mixins(self, css: str) -> str
    def process_functions(self, css: str) -> str
    def process_conditionals(self, css: str) -> str
    def optimize_output(self, css: str) -> str

# Example preprocessed stylesheet
PREPROCESSED_EXAMPLE = """
/* Theme variables */
@primary-color: ${theme.colors.primary};
@background-color: ${theme.colors.background};
@border-radius: ${theme.geometry.border_radius};

/* Mixins */
@mixin button-base {
    border-radius: @border-radius;
    padding: 8px 16px;
    font-weight: 500;
}

/* Component styles with preprocessing */
QPushButton {
    @include button-base;
    background-color: @primary-color;
    color: contrast(@primary-color);
    
    &:hover {
        background-color: lighten(@primary-color, 10%);
    }
    
    &:pressed {
        background-color: darken(@primary-color, 10%);
    }
}
"""
```

## ⚡ Performance Optimization System

### Caching Strategy
```python
class ThemeCache:
    """Intelligent theme caching with performance optimization."""
    
    def __init__(self, max_size: int = 100)
    def get_cached_stylesheet(self, theme_id: str, component: str) -> Optional[str]
    def cache_stylesheet(self, theme_id: str, component: str, stylesheet: str)
    def invalidate_theme(self, theme_id: str)
    def get_cache_stats(self) -> CacheStats
    def optimize_cache(self) -> OptimizationReport

PERFORMANCE_TARGETS = {
    'stylesheet_generation_time': 100,  # milliseconds
    'theme_switch_time': 200,           # milliseconds
    'hot_reload_time': 500,             # milliseconds
    'memory_usage_per_theme': 5,        # megabytes
    'cache_hit_ratio': 0.85,            # 85% cache hits
}
```

### Hot Reload Implementation
```python
class ThemeFileWatcher:
    """File system watcher for theme development."""
    
    def __init__(self, hot_reload_manager)
    def watch_directory(self, path: str, recursive: bool = True)
    def watch_file(self, path: str)
    def handle_file_change(self, event: FileSystemEvent)
    def debounce_changes(self, delay: float = 0.5)

class HotReloadEngine:
    """Core hot reload functionality."""
    
    def reload_theme_file(self, file_path: str):
        """Reload specific theme file and update UI."""
        # Parse changed file
        # Update theme data
        # Regenerate affected stylesheets
        # Apply to UI components
        # Notify development tools
```

## 🚀 Development Tools

### Performance Profiler
```python
class ThemePerformanceProfiler:
    """Profile theme performance and identify bottlenecks."""
    
    def start_profiling(self, theme_name: str)
    def stop_profiling(self) -> PerformanceReport
    def profile_stylesheet_generation(self, theme: Theme) -> GenerationProfile
    def profile_theme_application(self, theme: Theme) -> ApplicationProfile
    def generate_optimization_suggestions(self) -> List[OptimizationSuggestion]
```

### Style Inspector
```python
class StyleInspector:
    """Debug and inspect generated stylesheets."""
    
    def inspect_widget_styles(self, widget: QWidget) -> StyleInspection
    def trace_style_inheritance(self, widget: QWidget) -> InheritanceTrace
    def validate_style_conflicts(self, stylesheet: str) -> ConflictReport
    def suggest_style_improvements(self, stylesheet: str) -> List[Suggestion]
```

## 🔗 Integration Points
- **Agent 1 (Core Engine)**: Use theme engine for stylesheet generation
- **Agent 2 (Palettes/Typography)**: Convert color and font data to CSS
- **Agent 4 (Icons/Integration)**: Provide optimized stylesheet system

## 🧪 Testing Requirements
- **StyleSheet generation** speed and correctness tests
- **Hot reload** functionality and reliability tests
- **Performance benchmarks** for all optimization targets
- **CSS preprocessing** feature tests
- **Cache efficiency** and invalidation tests
- **>95% code coverage** requirement

## ⚡ Success Criteria Checklist
- [ ] Fast stylesheet generation (< 100ms)
- [ ] Hot reload working perfectly in development
- [ ] CSS preprocessing features functional
- [ ] Performance targets met consistently
- [ ] Theme caching optimized and reliable
- [ ] Development tools operational
- [ ] Comprehensive test coverage

## 📅 Day 3 Completion Target
By end of Day 3, Agent 4 should have:
- Optimized stylesheet generation system
- Hot reload ready for development workflow
- Performance-optimized theme application
- Development tools for theme creation

## 📞 Dependencies You'll Use
- ✅ **Agent 1 Output** - Theme engine foundation (Day 1)
- ✅ **Agent 2 Output** - Color palettes and typography (Day 2)

## 🎯 Example StyleSheet Generation
```python
def generate_optimized_stylesheet(theme: Theme) -> str:
    """Generate optimized Qt StyleSheet from theme data."""
    
    # Start performance profiling
    profiler = ThemePerformanceProfiler()
    profiler.start_profiling(theme.name)
    
    # Generate component stylesheets
    generator = StyleSheetGenerator(theme_engine, performance_optimizer)
    stylesheets = []
    
    for component in SUPPORTED_COMPONENTS:
        component_css = generator.compile_component_styles(theme, component)
        optimized_css = generator.optimize_stylesheet(component_css)
        stylesheets.append(optimized_css)
    
    # Combine and final optimization
    combined_stylesheet = '\n'.join(stylesheets)
    final_stylesheet = generator.optimize_stylesheet(combined_stylesheet)
    
    # Cache for future use
    cache.cache_stylesheet(theme.id, 'complete', final_stylesheet)
    
    # Complete profiling
    performance_report = profiler.stop_profiling()
    
    return final_stylesheet
```

Focus on creating lightning-fast, developer-friendly theme generation and application!