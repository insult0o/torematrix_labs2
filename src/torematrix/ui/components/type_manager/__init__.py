"""Type Manager UI Components

Agent 2 implementation for Element Type Management Interface.
UI components for type selection, hierarchy display, statistics, and management.
"""

from .selector import TypeSelectorWidget
from .hierarchy_view import TypeHierarchyView
from .statistics import TypeStatisticsDashboard
from .icon_manager import TypeIconManager
from .search_interface import TypeSearchInterface
from .info_panel import TypeInfoPanel
from .comparison_view import TypeComparisonView
from .recommendation_ui import TypeRecommendationUI
from .type_manager_main import TypeManagerMainWidget

__all__ = [
    'TypeSelectorWidget',
    'TypeHierarchyView', 
    'TypeStatisticsDashboard',
    'TypeIconManager',
    'TypeSearchInterface',
    'TypeInfoPanel',
    'TypeComparisonView',
    'TypeRecommendationUI',
    'TypeManagerMainWidget'
]

# Version info
__version__ = "1.0.0"
__author__ = "Agent 2 - Type UI Components"