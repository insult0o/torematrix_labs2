"""Main Search Widget and UI Components

Modern, responsive search interface that integrates all search and filter
functionality with polished UI design and optimal user experience.
"""

import logging
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass
from enum import Enum
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel,
    QSplitter, QFrame, QProgressBar, QToolButton, QMenu, QAction,
    QStatusBar, QGroupBox, QTabWidget, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread, QSize
from PyQt6.QtGui import QIcon, QFont, QPalette, QPixmap, QKeySequence

from torematrix.core.models.element import Element
from ..search.cache import CacheManager
from ..search.analytics import SearchAnalyticsEngine, QueryMetrics, QueryType
from ..search.suggestions import SearchSuggestionEngine
from ..search.monitoring import PerformanceMonitor
from .highlighting import SearchHighlighter, HighlightConfig, create_highlighter, HighlightedElement

logger = logging.getLogger(__name__)


class SearchMode(Enum):
    """Search operation modes"""
    BASIC = "basic"
    ADVANCED = "advanced"
    FILTER = "filter"
    EXPERT = "expert"


@dataclass
class SearchState:
    """Current search state"""
    query: str = ""
    mode: SearchMode = SearchMode.BASIC
    active_filters: Dict[str, Any] = None
    result_count: int = 0
    execution_time: float = 0.0
    is_searching: bool = False
    
    def __post_init__(self):
        if self.active_filters is None:
            self.active_filters = {}


class SearchStatusWidget(QWidget):
    """Status display for search operations"""
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_ui()
        self._search_state = SearchState()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        
        # Result count label
        self.result_label = QLabel("No results")
        self.result_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(self.result_label)
        
        # Execution time label
        self.time_label = QLabel("")
        self.time_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.time_label)
        
        layout.addStretch()
        
        # Cache status indicator
        self.cache_indicator = QLabel("●")
        self.cache_indicator.setToolTip("Cache Status")
        self.cache_indicator.setStyleSheet("color: #28a745; font-size: 14px;")
        layout.addWidget(self.cache_indicator)
        
        # Performance indicator
        self.perf_indicator = QLabel("●")
        self.perf_indicator.setToolTip("Performance Status")
        self.perf_indicator.setStyleSheet("color: #28a745; font-size: 14px;")
        layout.addWidget(self.perf_indicator)
    
    def update_search_state(self, state: SearchState):
        """Update display with new search state"""
        self._search_state = state
        
        # Update result count
        if state.result_count == 0:
            self.result_label.setText("No results")
        elif state.result_count == 1:
            self.result_label.setText("1 result")
        else:
            self.result_label.setText(f"{state.result_count:,} results")
        
        # Update execution time
        if state.execution_time > 0:
            if state.execution_time < 0.001:
                self.time_label.setText("< 1ms")
            elif state.execution_time < 1.0:
                self.time_label.setText(f"{state.execution_time*1000:.0f}ms")
            else:
                self.time_label.setText(f"{state.execution_time:.2f}s")
        else:
            self.time_label.setText("")
    
    def update_cache_status(self, hit_ratio: float):
        """Update cache status indicator"""
        if hit_ratio >= 80:
            color = "#28a745"  # Green
            tooltip = f"Cache performing well ({hit_ratio:.1f}%)"
        elif hit_ratio >= 60:
            color = "#ffc107"  # Yellow
            tooltip = f"Cache performance moderate ({hit_ratio:.1f}%)"
        else:
            color = "#dc3545"  # Red
            tooltip = f"Cache performance poor ({hit_ratio:.1f}%)"
        
        self.cache_indicator.setStyleSheet(f"color: {color}; font-size: 14px;")
        self.cache_indicator.setToolTip(tooltip)
    
    def update_performance_status(self, avg_time: float):
        """Update performance status indicator"""
        if avg_time <= 50:  # <= 50ms
            color = "#28a745"  # Green
            tooltip = f"Excellent performance ({avg_time:.0f}ms)"
        elif avg_time <= 100:  # <= 100ms
            color = "#ffc107"  # Yellow
            tooltip = f"Good performance ({avg_time:.0f}ms)"
        else:
            color = "#dc3545"  # Red
            tooltip = f"Poor performance ({avg_time:.0f}ms)"
        
        self.perf_indicator.setStyleSheet(f"color: {color}; font-size: 14px;")
        self.perf_indicator.setToolTip(tooltip)


class SearchBarWidget(QWidget):
    """Advanced search bar with suggestions and mode switching"""
    
    # Signals
    search_requested = pyqtSignal(str, object)  # query, search_mode
    mode_changed = pyqtSignal(object)  # SearchMode
    clear_requested = pyqtSignal()
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_ui()
        self._setup_connections()
        self._suggestion_engine: Optional[SearchSuggestionEngine] = None
        self._current_mode = SearchMode.BASIC
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        
        # Mode selector button
        self.mode_button = QToolButton()
        self.mode_button.setText("Basic")
        self.mode_button.setToolTip("Search Mode")
        self.mode_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self._setup_mode_menu()
        layout.addWidget(self.mode_button)
        
        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search elements...")
        self.search_input.setMinimumHeight(32)
        font = self.search_input.font()
        font.setPointSize(11)
        self.search_input.setFont(font)
        layout.addWidget(self.search_input)
        
        # Search button
        self.search_button = QPushButton("Search")
        self.search_button.setMinimumHeight(32)
        self.search_button.setMinimumWidth(80)
        self.search_button.setDefault(True)
        layout.addWidget(self.search_button)
        
        # Clear button
        self.clear_button = QPushButton("Clear")
        self.clear_button.setMinimumHeight(32)
        self.clear_button.setMinimumWidth(60)
        layout.addWidget(self.clear_button)
        
        # Progress indicator (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(0)  # Indeterminate
        self.progress_bar.setMaximumHeight(4)
        self.progress_bar.hide()
        
        # Add progress bar below main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        search_widget = QWidget()
        search_widget.setLayout(layout)
        main_layout.addWidget(search_widget)
        main_layout.addWidget(self.progress_bar)
        
        self.setLayout(main_layout)
    
    def _setup_mode_menu(self):
        """Setup search mode menu"""
        mode_menu = QMenu(self.mode_button)
        
        modes = [
            (SearchMode.BASIC, "Basic Search", "Simple text search"),
            (SearchMode.ADVANCED, "Advanced Search", "Complex queries with operators"),
            (SearchMode.FILTER, "Filter Mode", "Visual filter interface"),
            (SearchMode.EXPERT, "Expert Mode", "Raw query with full power")
        ]
        
        for mode, title, description in modes:
            action = QAction(title, mode_menu)
            action.setToolTip(description)
            action.setData(mode)
            action.triggered.connect(lambda checked, m=mode: self._set_search_mode(m))
            mode_menu.addAction(action)
        
        self.mode_button.setMenu(mode_menu)
    
    def _setup_connections(self):
        """Setup signal connections"""
        self.search_button.clicked.connect(self._perform_search)
        self.clear_button.clicked.connect(self._clear_search)
        self.search_input.returnPressed.connect(self._perform_search)
        self.search_input.textChanged.connect(self._on_text_changed)
    
    def _set_search_mode(self, mode: SearchMode):
        """Set search mode and update UI"""
        self._current_mode = mode
        self.mode_button.setText(mode.value.title())
        
        # Update placeholder text based on mode
        placeholders = {
            SearchMode.BASIC: "Search elements...",
            SearchMode.ADVANCED: "Search with operators (AND, OR, NOT)...",
            SearchMode.FILTER: "Quick filter...",
            SearchMode.EXPERT: "Expert query (regex, complex expressions)..."
        }
        
        self.search_input.setPlaceholderText(placeholders.get(mode, "Search..."))
        self.mode_changed.emit(mode)
    
    def _perform_search(self):
        """Perform search with current query and mode"""
        query = self.search_input.text().strip()
        if query:
            self.show_progress(True)
            self.search_requested.emit(query, self._current_mode)
    
    def _clear_search(self):
        """Clear search and reset UI"""
        self.search_input.clear()
        self.show_progress(False)
        self.clear_requested.emit()
    
    def _on_text_changed(self, text: str):
        """Handle text changes for suggestions"""
        # Enable/disable search button
        self.search_button.setEnabled(bool(text.strip()))
        
        # Trigger suggestions if available
        if self._suggestion_engine and len(text) >= 2:
            # TODO: Implement real-time suggestions
            pass
    
    def show_progress(self, show: bool):
        """Show or hide search progress indicator"""
        if show:
            self.progress_bar.show()
            self.search_button.setEnabled(False)
        else:
            self.progress_bar.hide()
            self.search_button.setEnabled(bool(self.search_input.text().strip()))
    
    def set_suggestion_engine(self, engine: SearchSuggestionEngine):
        """Set suggestion engine for autocomplete"""
        self._suggestion_engine = engine
    
    def get_current_query(self) -> str:
        """Get current search query"""
        return self.search_input.text().strip()
    
    def get_current_mode(self) -> SearchMode:
        """Get current search mode"""
        return self._current_mode
    
    def set_query(self, query: str):
        """Set search query programmatically"""
        self.search_input.setText(query)
    
    def focus_search(self):
        """Focus the search input"""
        self.search_input.setFocus()
        self.search_input.selectAll()


class SearchWidget(QWidget):
    """Main search widget integrating all search functionality"""
    
    # Signals
    search_completed = pyqtSignal(list, object)  # results, search_state
    element_selected = pyqtSignal(object)  # Element
    export_requested = pyqtSignal(list, str)  # results, format
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_ui()
        self._setup_connections()
        self._setup_search_components()
        
        # State
        self._current_results: List[Element] = []
        self._search_state = SearchState()
        self._search_thread: Optional[QThread] = None
        
        logger.info("SearchWidget initialized")
    
    def _setup_ui(self):
        """Setup the main UI layout"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Header with title and controls
        header_layout = QHBoxLayout()
        
        title = QLabel("Search & Filter")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Export button
        self.export_button = QPushButton("Export")
        self.export_button.setIcon(QIcon("📄"))  # Would use actual icon
        self.export_button.setEnabled(False)
        header_layout.addWidget(self.export_button)
        
        # Settings button
        self.settings_button = QToolButton()
        self.settings_button.setIcon(QIcon("⚙️"))  # Would use actual icon
        self.settings_button.setToolTip("Search Settings")
        header_layout.addWidget(self.settings_button)
        
        layout.addLayout(header_layout)
        
        # Search bar
        self.search_bar = SearchBarWidget()
        layout.addWidget(self.search_bar)
        
        # Main content area with splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - Filters (if available)
        self.filter_panel = QFrame()
        self.filter_panel.setFrameStyle(QFrame.Shape.StyledPanel)
        self.filter_panel.setMaximumWidth(250)
        self.filter_panel.setMinimumWidth(200)
        
        filter_layout = QVBoxLayout(self.filter_panel)
        filter_title = QLabel("Filters")
        filter_title.setFont(QFont("", 10, QFont.Weight.Bold))
        filter_layout.addWidget(filter_title)
        
        # TODO: Add actual filter widgets
        filter_placeholder = QLabel("Filter controls will be\nimplemented in panels.py")
        filter_placeholder.setStyleSheet("color: #888; font-style: italic;")
        filter_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        filter_layout.addWidget(filter_placeholder)
        
        filter_layout.addStretch()
        splitter.addWidget(self.filter_panel)
        
        # Right panel - Results
        results_widget = QWidget()
        results_layout = QVBoxLayout(results_widget)
        results_layout.setContentsMargins(4, 4, 4, 4)
        
        # Results header
        results_header = QHBoxLayout()
        results_title = QLabel("Results")
        results_title.setFont(QFont("", 10, QFont.Weight.Bold))
        results_header.addWidget(results_title)
        
        results_header.addStretch()
        
        # View mode buttons
        self.list_view_button = QToolButton()
        self.list_view_button.setIcon(QIcon("📋"))  # Would use actual icon
        self.list_view_button.setToolTip("List View")
        self.list_view_button.setCheckable(True)
        self.list_view_button.setChecked(True)
        results_header.addWidget(self.list_view_button)
        
        self.grid_view_button = QToolButton()
        self.grid_view_button.setIcon(QIcon("⊞"))  # Would use actual icon
        self.grid_view_button.setToolTip("Grid View")
        self.grid_view_button.setCheckable(True)
        results_header.addWidget(self.grid_view_button)
        
        results_layout.addLayout(results_header)
        
        # Results area (placeholder)
        self.results_area = QScrollArea()
        self.results_area.setWidgetResizable(True)
        self.results_area.setFrameStyle(QFrame.Shape.NoFrame)
        
        results_placeholder = QLabel("Search results will appear here\nImplemented in results_view.py")
        results_placeholder.setStyleSheet("color: #888; font-style: italic;")
        results_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        results_placeholder.setMinimumHeight(200)
        self.results_area.setWidget(results_placeholder)
        
        results_layout.addWidget(self.results_area)
        
        splitter.addWidget(results_widget)
        
        # Set splitter proportions
        splitter.setSizes([200, 600])
        layout.addWidget(splitter)
        
        # Status bar
        self.status_widget = SearchStatusWidget()
        layout.addWidget(self.status_widget)
    
    def _setup_connections(self):
        """Setup signal connections"""
        self.search_bar.search_requested.connect(self._handle_search_request)
        self.search_bar.clear_requested.connect(self._handle_clear_request)
        self.search_bar.mode_changed.connect(self._handle_mode_change)
        
        self.export_button.clicked.connect(self._handle_export_request)
        
        # View mode toggle
        self.list_view_button.toggled.connect(self._update_view_mode)
        self.grid_view_button.toggled.connect(self._update_view_mode)
    
    def _setup_search_components(self):
        """Initialize search engine components"""
        # Initialize performance monitoring
        self._performance_monitor = PerformanceMonitor()
        
        # Initialize analytics
        self._analytics_engine = SearchAnalyticsEngine()
        
        # Initialize cache
        self._cache_manager = CacheManager(max_size=1000, ttl=300)
        
        # Initialize highlighting system
        self._highlighter = create_highlighter()
        self._highlighter.highlighting_completed.connect(self._on_highlighting_completed)
        
        # State for highlighted results
        self._highlighted_results: List[HighlightedElement] = []
        
        # Status update timer
        self._status_timer = QTimer()
        self._status_timer.timeout.connect(self._update_status_indicators)
        self._status_timer.start(5000)  # Update every 5 seconds
        
        logger.debug("Search components initialized")
    
    def _handle_search_request(self, query: str, mode: SearchMode):
        """Handle search request from search bar"""
        logger.info(f"Search requested: '{query}' (mode: {mode.value})")
        
        # Update search state
        self._search_state.query = query
        self._search_state.mode = mode
        self._search_state.is_searching = True
        
        # TODO: Implement actual search logic
        # For now, simulate search completion
        QTimer.singleShot(1000, lambda: self._simulate_search_completion(query))
    
    def _simulate_search_completion(self, query: str):
        """Simulate search completion (placeholder)"""
        # Simulate results
        mock_results = []
        
        # Update search state
        self._search_state.result_count = len(mock_results)
        self._search_state.execution_time = 0.035  # 35ms
        self._search_state.is_searching = False
        
        # Update UI
        self.search_bar.show_progress(False)
        self.status_widget.update_search_state(self._search_state)
        self.export_button.setEnabled(len(mock_results) > 0)
        
        # Emit completion signal
        self.search_completed.emit(mock_results, self._search_state)
        
        logger.debug(f"Search completed: {len(mock_results)} results in {self._search_state.execution_time*1000:.0f}ms")
    
    def _handle_clear_request(self):
        """Handle clear request"""
        self._current_results.clear()
        self._search_state = SearchState()
        
        self.status_widget.update_search_state(self._search_state)
        self.export_button.setEnabled(False)
        
        logger.debug("Search cleared")
    
    def _handle_mode_change(self, mode: SearchMode):
        """Handle search mode change"""
        logger.debug(f"Search mode changed to: {mode.value}")
        
        # Show/hide filter panel based on mode
        if mode == SearchMode.FILTER:
            self.filter_panel.show()
        else:
            # Keep visible but could be minimized
            pass
    
    def _handle_export_request(self):
        """Handle export request"""
        if self._current_results:
            # TODO: Show export dialog
            self.export_requested.emit(self._current_results, "json")
            logger.info(f"Export requested for {len(self._current_results)} results")
    
    def _update_view_mode(self):
        """Update view mode based on button state"""
        if self.sender() == self.list_view_button and self.list_view_button.isChecked():
            self.grid_view_button.setChecked(False)
            logger.debug("Switched to list view")
        elif self.sender() == self.grid_view_button and self.grid_view_button.isChecked():
            self.list_view_button.setChecked(False)
            logger.debug("Switched to grid view")
    
    def _update_status_indicators(self):
        """Update status indicators with current metrics"""
        try:
            # Update cache status
            cache_stats = self._cache_manager.get_statistics()
            self.status_widget.update_cache_status(cache_stats['hit_ratio'])
            
            # Update performance status
            # TODO: Get actual performance metrics
            avg_time = 35.0  # Placeholder
            self.status_widget.update_performance_status(avg_time)
            
        except Exception as e:
            logger.error(f"Error updating status indicators: {e}")
    
    def set_results(self, results: List[Element]):
        """Set search results and update UI"""
        self._current_results = results
        self._search_state.result_count = len(results)
        
        self.status_widget.update_search_state(self._search_state)
        self.export_button.setEnabled(len(results) > 0)
        
        # TODO: Update results view
        logger.debug(f"Results updated: {len(results)} elements")
    
    def get_current_results(self) -> List[Element]:
        """Get current search results"""
        return self._current_results.copy()
    
    def get_search_state(self) -> SearchState:
        """Get current search state"""
        return self._search_state
    
    def focus_search(self):
        """Focus the search input"""
        self.search_bar.focus_search()
    
    def perform_search(self, query: str, mode: SearchMode = SearchMode.BASIC):
        """Perform search programmatically"""
        self.search_bar.set_query(query)
        self._handle_search_request(query, mode)


# Factory function for easy instantiation
def create_search_widget(parent: Optional[QWidget] = None) -> SearchWidget:
    """Create and configure a SearchWidget instance"""
    widget = SearchWidget(parent)
    return widget