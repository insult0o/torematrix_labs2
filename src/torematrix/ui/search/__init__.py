"""Search and Filter System Package

Advanced search and filter system with performance optimization,
real-time highlighting, and comprehensive UI components.
"""

# Main UI components
from .widgets import (
    SearchWidget, SearchBarWidget, SearchStatusWidget,
    SearchMode, SearchState, create_search_widget
)

from .panels import (
    FilterPanel, FilterWidget, FilterInstance, FilterDefinition,
    FilterType, FilterOperator, create_filter_panel
)

from .highlighting import (
    SearchHighlighter, HighlightedElement, HighlightConfig,
    HighlightMode, HighlightStyle, HighlightMatch,
    create_highlighter, create_highlight_config, highlight_quick
)

from .export import (
    ExportDialog, ResultExporter, ExportConfiguration,
    ExportFormat, ExportStatus, ExportProgress,
    export_elements, show_export_dialog
)

# Performance and analytics components
from .cache import CacheManager, LRUCache, CacheInvalidationManager
from .analytics import SearchAnalyticsEngine, QueryMetrics, QueryType
from .monitoring import PerformanceMonitor, PerformanceMetrics
from .suggestions import SearchSuggestionEngine

# Version info
__version__ = "1.0.0"
__author__ = "TORE Matrix Labs Agent 4"

# Package metadata
__all__ = [
    # Main widgets
    'SearchWidget',
    'SearchBarWidget', 
    'SearchStatusWidget',
    'FilterPanel',
    'FilterWidget',
    
    # Data models
    'SearchMode',
    'SearchState',
    'FilterInstance',
    'FilterDefinition',
    'FilterType',
    'FilterOperator',
    'HighlightedElement',
    'HighlightConfig',
    'HighlightMode',
    'HighlightStyle',
    'HighlightMatch',
    
    # Core components
    'SearchHighlighter',
    'CacheManager',
    'SearchAnalyticsEngine',
    'PerformanceMonitor',
    'SearchSuggestionEngine',
    'ResultExporter',
    'ExportDialog',
    
    # Configuration classes
    'ExportConfiguration',
    'ExportFormat',
    'ExportStatus',
    'ExportProgress',
    
    # Factory functions
    'create_search_widget',
    'create_filter_panel',
    'create_highlighter',
    'create_highlight_config',
    'highlight_quick',
    'export_elements',
    'show_export_dialog',
]