"""Layout Management System for ToreMatrix V3.

This package provides a comprehensive layout management system with:
- Flexible layout templates (Document, Split, Tabbed, Multi-panel)
- Layout switching with smooth transitions
- Layout validation and error handling
- Component registration and tracking
- Layout persistence and restoration

Usage:
    from torematrix.ui.layouts import LayoutManager, LayoutType, create_document_layout
    
    # Create layout manager
    manager = LayoutManager(main_window, event_bus, config_manager, state_manager)
    
    # Register layout templates
    manager.register_template(LayoutType.DOCUMENT, create_document_layout)
    
    # Create and activate layout
    layout_id = manager.create_layout(LayoutType.DOCUMENT, "Main Document Layout")
    manager.activate_layout(layout_id)
"""

from .base import (
    # Core data classes
    LayoutType,
    LayoutState, 
    LayoutGeometry,
    LayoutItem,
    LayoutConfiguration,
    BaseLayout,
    LayoutProvider,
    LayoutItemRegistry,
)

from .manager import (
    # Main layout manager
    LayoutManager,
    LayoutTransitionError,
    LayoutValidationError,
)

from .templates import (
    # Layout template classes
    DocumentLayout,
    SplitLayout,
    TabbedLayout,
    MultiPanelLayout,
    
    # Template factory functions
    create_document_layout,
    create_split_horizontal_layout,
    create_split_vertical_layout,
    create_tabbed_layout,
    create_multi_panel_layout,
    
    # Template registry
    LAYOUT_TEMPLATES,
)

from .validation import (
    # Validation classes
    ValidationSeverity,
    ValidationMessage,
    ValidationResult,
    ValidationRule,
    LayoutValidator,
    
    # Validation functions
    validate_layout,
    validate_layout_quick,
    get_validator,
    add_validation_rule,
    
    # Built-in validation rules
    LayoutNameRule,
    LayoutGeometryRule,
    LayoutItemsRule,
    LayoutTypeSpecificRule,
    LayoutPerformanceRule,
)

# Agent 3: Responsive Design & Performance imports
from .responsive import (
    ResponsiveMode,
    LayoutDensity,
    TouchTarget,
    ScreenProperties,
    ResponsiveConstraints,
    ResponsiveStrategy,
    MobileFirstStrategy,
    DesktopStrategy,
    TabletStrategy,
    ResponsiveLayoutEngine,
    ResponsiveWidget,
)

from .breakpoints import (
    BreakpointType,
    DeviceClass,
    BreakpointDefinition,
    BreakpointEvent,
    DeviceProfile,
    BreakpointCalculator,
    BreakpointManager,
)

from .adaptive import (
    AdaptationStrategy,
    LayoutDirection,
    ContentPriority,
    LayoutConstraints,
    ContentItem,
    LayoutSolution,
    LayoutAlgorithm,
    StackedLayoutAlgorithm,
    SplitLayoutAlgorithm,
    GridLayoutAlgorithm,
    AdaptiveLayoutEngine,
    AdaptiveLayout,
)

from .performance import (
    PerformanceLevel,
    OptimizationType,
    PerformanceMetrics,
    PerformanceProfiler,
    performance_timer,
    LayoutCache,
    WidgetPool,
    LazyLoader,
    MemoryOptimizer,
    RenderOptimizer,
    PerformanceOptimizer,
)

from .monitoring import (
    AlertLevel,
    MetricType,
    PerformanceAlert,
    MetricThreshold,
    PerformanceReport,
    MetricCollector,
    AlertManager,
    BottleneckDetector,
    PerformanceMonitor,
)

# Version info
__version__ = "1.0.0"
__author__ = "ToreMatrix Labs V3 Team"

# Public API - what gets imported with "from torematrix.ui.layouts import *"
__all__ = [
    # Core classes and enums
    "LayoutType",
    "LayoutState",
    "LayoutGeometry", 
    "LayoutItem",
    "LayoutConfiguration",
    "BaseLayout",
    "LayoutProvider",
    "LayoutItemRegistry",
    
    # Main manager
    "LayoutManager",
    "LayoutTransitionError",
    "LayoutValidationError",
    
    # Template classes
    "DocumentLayout",
    "SplitLayout", 
    "TabbedLayout",
    "MultiPanelLayout",
    
    # Template factories
    "create_document_layout",
    "create_split_horizontal_layout",
    "create_split_vertical_layout", 
    "create_tabbed_layout",
    "create_multi_panel_layout",
    "LAYOUT_TEMPLATES",
    
    # Validation
    "ValidationSeverity",
    "ValidationMessage",
    "ValidationResult",
    "ValidationRule",
    "LayoutValidator",
    "validate_layout",
    "validate_layout_quick",
    "get_validator",
    "add_validation_rule",
    
    # Built-in validation rules
    "LayoutNameRule",
    "LayoutGeometryRule", 
    "LayoutItemsRule",
    "LayoutTypeSpecificRule",
    "LayoutPerformanceRule",
    
    # Agent 3: Responsive Design & Performance
    # Responsive system
    "ResponsiveMode",
    "LayoutDensity",
    "TouchTarget",
    "ScreenProperties",
    "ResponsiveConstraints",
    "ResponsiveStrategy",
    "MobileFirstStrategy",
    "DesktopStrategy",
    "TabletStrategy",
    "ResponsiveLayoutEngine",
    "ResponsiveWidget",
    
    # Breakpoint system
    "BreakpointType",
    "DeviceClass",
    "BreakpointDefinition",
    "BreakpointEvent",
    "DeviceProfile",
    "BreakpointCalculator",
    "BreakpointManager",
    
    # Adaptive layouts
    "AdaptationStrategy",
    "LayoutDirection",
    "ContentPriority",
    "LayoutConstraints",
    "ContentItem",
    "LayoutSolution",
    "LayoutAlgorithm",
    "StackedLayoutAlgorithm",
    "SplitLayoutAlgorithm",
    "GridLayoutAlgorithm",
    "AdaptiveLayoutEngine",
    "AdaptiveLayout",
    
    # Performance optimization
    "PerformanceLevel",
    "OptimizationType",
    "PerformanceMetrics",
    "PerformanceProfiler",
    "performance_timer",
    "LayoutCache",
    "WidgetPool",
    "LazyLoader",
    "MemoryOptimizer",
    "RenderOptimizer",
    "PerformanceOptimizer",
    
    # Performance monitoring
    "AlertLevel",
    "MetricType",
    "PerformanceAlert",
    "MetricThreshold",
    "PerformanceReport",
    "MetricCollector",
    "AlertManager",
    "BottleneckDetector",
    "PerformanceMonitor",
]


def get_available_layout_types():
    """Get list of all available layout types."""
    return list(LayoutType)


def get_layout_template_names():
    """Get list of all available layout template names."""
    return list(LAYOUT_TEMPLATES.keys())


def create_layout_manager(main_window, event_bus, config_manager, state_manager):
    """Convenience function to create a fully configured layout manager.
    
    Args:
        main_window: QMainWindow instance
        event_bus: EventBus instance
        config_manager: ConfigManager instance  
        state_manager: StateManager instance
        
    Returns:
        LayoutManager: Configured layout manager with all default templates registered
    """
    manager = LayoutManager(main_window, event_bus, config_manager, state_manager)
    
    # Register all built-in templates
    for layout_type, template_factory in LAYOUT_TEMPLATES.items():
        manager.register_template(layout_type, template_factory)
    
    return manager


def create_default_layout_configuration(layout_type: LayoutType, name: str = None):
    """Create a default layout configuration for the specified type.
    
    Args:
        layout_type: Type of layout to create
        name: Optional name for the layout
        
    Returns:
        LayoutConfiguration: Default configuration for the layout type
    """
    if name is None:
        name = f"Default {layout_type.value.replace('_', ' ').title()} Layout"
    
    geometry = LayoutGeometry(width=1200, height=800)
    
    config = LayoutConfiguration(
        id="",  # Will be auto-generated
        name=name,
        layout_type=layout_type,
        geometry=geometry
    )
    
    # Add default properties based on layout type
    if layout_type == LayoutType.DOCUMENT:
        config.properties.update({
            "show_properties_panel": True,
            "show_corrections_panel": True,
            "main_splitter_ratio": [2, 1],
            "right_splitter_ratio": [1, 1]
        })
    elif layout_type in [LayoutType.SPLIT_HORIZONTAL, LayoutType.SPLIT_VERTICAL]:
        config.properties.update({
            "splitter_ratio": [1, 1],
            "allow_resize": True
        })
    elif layout_type == LayoutType.TABBED:
        config.properties.update({
            "tabs_closable": True,
            "tabs_movable": True,
            "current_tab": 0
        })
    elif layout_type == LayoutType.MULTI_PANEL:
        config.properties.update({
            "panel_structure": {
                "type": "horizontal_split",
                "panels": [
                    {"type": "panel", "name": "left", "size": 300},
                    {
                        "type": "vertical_split", 
                        "panels": [
                            {"type": "panel", "name": "top_right", "size": 400},
                            {"type": "panel", "name": "bottom_right", "size": 200}
                        ]
                    }
                ]
            }
        })
    
    return config


# Package initialization
def _initialize_package():
    """Initialize the layouts package."""
    import logging
    logger = logging.getLogger(__name__)
    logger.debug("ToreMatrix Layout Management System initialized")


# Initialize when imported
_initialize_package()
