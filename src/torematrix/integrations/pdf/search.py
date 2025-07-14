"""
PDF.js Search Functionality.

This module provides comprehensive search capabilities for PDF documents
including full-text search, highlighting, navigation, and search history.

Agent 4 Implementation:
- Full-text search across PDF documents
- Search result highlighting and navigation
- Search options (case-sensitive, whole words, regex)
- Search history and bookmarks
- Performance optimization for large documents
"""

from __future__ import annotations

import re
import time
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union, Callable
from enum import Enum
from collections import deque

from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel, QCheckBox
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtWebEngineWidgets import QWebEngineView

logger = logging.getLogger(__name__)


class SearchMode(Enum):
    """Search modes."""
    NORMAL = "normal"
    CASE_SENSITIVE = "case_sensitive"
    WHOLE_WORDS = "whole_words"
    REGEX = "regex"


@dataclass
class SearchResult:
    """Represents a search result."""
    page_number: int
    text_content: str
    start_index: int
    end_index: int
    coordinates: Dict[str, float]  # x, y, width, height
    context_before: str = ""
    context_after: str = ""
    highlight_id: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "page_number": self.page_number,
            "text_content": self.text_content,
            "start_index": self.start_index,
            "end_index": self.end_index,
            "coordinates": self.coordinates,
            "context_before": self.context_before,
            "context_after": self.context_after,
            "highlight_id": self.highlight_id
        }


@dataclass
class SearchQuery:
    """Represents a search query with options."""
    query: str
    mode: SearchMode = SearchMode.NORMAL
    case_sensitive: bool = False
    whole_words: bool = False
    regex_enabled: bool = False
    max_results: int = 1000
    context_chars: int = 50
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JavaScript."""
        return {
            "query": self.query,
            "mode": self.mode.value,
            "case_sensitive": self.case_sensitive,
            "whole_words": self.whole_words,
            "regex_enabled": self.regex_enabled,
            "max_results": self.max_results,
            "context_chars": self.context_chars
        }


@dataclass
class SearchMetrics:
    """Search performance metrics."""
    total_searches: int = 0
    avg_search_time_ms: float = 0.0
    last_search_time_ms: float = 0.0
    total_results_found: int = 0
    cache_hit_rate: float = 0.0
    last_updated: float = field(default_factory=time.time)


class SearchManager(QObject):
    """
    Advanced PDF search functionality manager.
    
    Provides comprehensive search capabilities including:
    - Full-text search across PDF documents
    - Multiple search modes (normal, case-sensitive, regex)
    - Search result highlighting and navigation
    - Search history and caching
    - Performance monitoring and optimization
    
    Signals:
        search_started: Emitted when search begins
        search_completed: Emitted when search completes
        result_selected: Emitted when search result is selected
        search_cleared: Emitted when search is cleared
        metrics_updated: Emitted when search metrics are updated
    """
    
    # Signals
    search_started = pyqtSignal(str)  # query
    search_completed = pyqtSignal(str, list)  # query, results
    result_selected = pyqtSignal(SearchResult)
    search_cleared = pyqtSignal()
    metrics_updated = pyqtSignal(SearchMetrics)
    
    def __init__(self, pdf_viewer: QWebEngineView, config: Any):
        """Initialize search manager.
        
        Args:
            pdf_viewer: PDF viewer instance
            config: Feature configuration
        """
        super().__init__()
        
        self.pdf_viewer = pdf_viewer
        self.config = config
        
        # Search state
        self.current_query: Optional[SearchQuery] = None
        self.search_results: List[SearchResult] = []
        self.current_result_index: int = -1
        self.is_searching: bool = False
        
        # Search history and caching
        self.search_history: deque = deque(maxlen=config.search_history_size)
        self.search_cache: Dict[str, List[SearchResult]] = {}
        self.cache_max_size = 100
        
        # Performance monitoring
        self.metrics = SearchMetrics()
        self.search_times: deque = deque(maxlen=50)  # Last 50 search times
        
        # JavaScript communication
        self.bridge = None
        self.performance_config = None
        
        # UI components (optional)
        self.search_widget: Optional[QWidget] = None
        self.enabled = True
        
        logger.info("SearchManager initialized")
    
    def connect_bridge(self, bridge) -> None:
        """Connect to PDF bridge for JavaScript communication.
        
        Args:
            bridge: PDFBridge instance
        """
        self.bridge = bridge
        logger.info("Search manager connected to bridge")
    
    def set_performance_config(self, config: Dict[str, Any]) -> None:
        """Set performance configuration from Agent 3.
        
        Args:
            config: Performance configuration
        """
        self.performance_config = config
        
        # Adjust search behavior based on performance config
        if config.get("performance_level") == "low":
            self.cache_max_size = 50
        elif config.get("performance_level") == "high":
            self.cache_max_size = 200
        
        logger.debug("Search performance configuration updated")
    
    def enable(self) -> None:
        """Enable search functionality."""
        self.enabled = True
        logger.info("Search functionality enabled")
    
    def disable(self) -> None:
        """Disable search functionality."""
        self.enabled = False
        self.clear_search()
        logger.info("Search functionality disabled")
    
    def search(self, query: str, options: Optional[Dict[str, Any]] = None) -> bool:
        """Perform search in PDF document.
        
        Args:
            query: Search query string
            options: Search options
            
        Returns:
            True if search was initiated successfully
        """
        if not self.enabled or not query.strip():
            return False
        
        if self.is_searching:
            logger.warning("Search already in progress")
            return False
        
        try:
            # Create search query object
            search_query = SearchQuery(
                query=query.strip(),
                case_sensitive=options.get("case_sensitive", self.config.search_case_sensitive),
                whole_words=options.get("whole_words", self.config.search_whole_words),
                regex_enabled=options.get("regex", self.config.search_regex_enabled),
                max_results=options.get("max_results", 1000),
                context_chars=options.get("context_chars", 50)
            )
            
            # Check cache first
            cache_key = self._get_cache_key(search_query)
            if cache_key in self.search_cache:
                self.search_results = self.search_cache[cache_key]
                self.current_query = search_query
                self.current_result_index = 0
                self.search_completed.emit(query, [r.to_dict() for r in self.search_results])
                self._update_cache_hit_rate(True)
                logger.debug(f"Search results retrieved from cache: {len(self.search_results)} results")
                return True
            
            # Start new search
            self.is_searching = True
            self.current_query = search_query
            self.search_results.clear()
            self.current_result_index = -1
            
            # Add to search history
            self.search_history.append(search_query)
            
            # Emit search started signal
            self.search_started.emit(query)
            
            # Send search command to JavaScript
            if self.bridge:
                self.bridge.send_feature_command("search", "find_text", search_query.to_dict())
                logger.info(f"Search initiated: '{query}' with {len(options or {})} options")
                return True
            else:
                # Fallback: direct JavaScript execution
                js_code = f"""
                    if (typeof window.searchText === 'function') {{
                        window.searchText({search_query.to_dict()});
                    }}
                """
                self.pdf_viewer.page().runJavaScript(js_code)
                return True
                
        except Exception as e:
            self.is_searching = False
            logger.error(f"Search initiation failed: {e}")
            return False
    
    def handle_js_event(self, data: Dict[str, Any]) -> None:
        """Handle search events from JavaScript.
        
        Args:
            data: Event data from JavaScript
        """
        try:
            event_type = data.get("type")
            
            if event_type == "search_results":
                self._handle_search_results(data)
            elif event_type == "search_progress":
                self._handle_search_progress(data)
            elif event_type == "search_error":
                self._handle_search_error(data)
            
        except Exception as e:
            logger.error(f"Error handling search event: {e}")
    
    def _handle_search_results(self, data: Dict[str, Any]) -> None:
        """Handle search results from JavaScript.
        
        Args:
            data: Search results data
        """
        try:
            results_data = data.get("results", [])
            query = data.get("query", "")
            search_time_ms = data.get("search_time_ms", 0)
            
            # Convert results to SearchResult objects
            self.search_results = []
            for result_data in results_data:
                result = SearchResult(
                    page_number=result_data.get("page", 1),
                    text_content=result_data.get("text", ""),
                    start_index=result_data.get("start", 0),
                    end_index=result_data.get("end", 0),
                    coordinates=result_data.get("coordinates", {}),
                    context_before=result_data.get("context_before", ""),
                    context_after=result_data.get("context_after", ""),
                    highlight_id=result_data.get("highlight_id", "")
                )
                self.search_results.append(result)
            
            # Update metrics
            self.metrics.total_searches += 1
            self.metrics.last_search_time_ms = search_time_ms
            self.metrics.total_results_found += len(self.search_results)
            self.search_times.append(search_time_ms)
            self._update_average_search_time()
            self._update_cache_hit_rate(False)
            
            # Cache results
            if self.current_query:
                cache_key = self._get_cache_key(self.current_query)
                self.search_cache[cache_key] = self.search_results
                self._cleanup_cache()
            
            # Update result index
            if self.search_results:
                self.current_result_index = 0
            
            # Mark search as complete
            self.is_searching = False
            
            # Emit completion signal
            self.search_completed.emit(query, [r.to_dict() for r in self.search_results])
            self.metrics_updated.emit(self.metrics)
            
            logger.info(f"Search completed: {len(self.search_results)} results in {search_time_ms:.1f}ms")
            
        except Exception as e:
            self.is_searching = False
            logger.error(f"Error handling search results: {e}")
    
    def _handle_search_progress(self, data: Dict[str, Any]) -> None:
        """Handle search progress from JavaScript.
        
        Args:
            data: Progress data
        """
        progress = data.get("progress", 0)
        logger.debug(f"Search progress: {progress}%")
    
    def _handle_search_error(self, data: Dict[str, Any]) -> None:
        """Handle search error from JavaScript.
        
        Args:
            data: Error data
        """
        error_message = data.get("error", "Unknown search error")
        self.is_searching = False
        logger.error(f"Search error: {error_message}")
    
    def next_result(self) -> Optional[SearchResult]:
        """Navigate to next search result.
        
        Returns:
            Next search result or None
        """
        if not self.search_results:
            return None
        
        if self.current_result_index < len(self.search_results) - 1:
            self.current_result_index += 1
            result = self.search_results[self.current_result_index]
            self._navigate_to_result(result)
            return result
        
        return None
    
    def previous_result(self) -> Optional[SearchResult]:
        """Navigate to previous search result.
        
        Returns:
            Previous search result or None
        """
        if not self.search_results:
            return None
        
        if self.current_result_index > 0:
            self.current_result_index -= 1
            result = self.search_results[self.current_result_index]
            self._navigate_to_result(result)
            return result
        
        return None
    
    def go_to_result(self, index: int) -> Optional[SearchResult]:
        """Navigate to specific search result.
        
        Args:
            index: Result index
            
        Returns:
            Search result at index or None
        """
        if not self.search_results or index < 0 or index >= len(self.search_results):
            return None
        
        self.current_result_index = index
        result = self.search_results[index]
        self._navigate_to_result(result)
        return result
    
    def _navigate_to_result(self, result: SearchResult) -> None:
        """Navigate to a specific search result.
        
        Args:
            result: Search result to navigate to
        """
        try:
            # Send navigation command to JavaScript
            if self.bridge:
                self.bridge.send_feature_command("search", "navigate_to_result", {
                    "page": result.page_number,
                    "coordinates": result.coordinates,
                    "highlight_id": result.highlight_id
                })
            
            # Emit result selected signal
            self.result_selected.emit(result)
            
            logger.debug(f"Navigated to search result on page {result.page_number}")
            
        except Exception as e:
            logger.error(f"Error navigating to search result: {e}")
    
    def clear_search(self) -> None:
        """Clear current search and results."""
        try:
            # Clear search state
            self.current_query = None
            self.search_results.clear()
            self.current_result_index = -1
            self.is_searching = False
            
            # Clear highlights in JavaScript
            if self.bridge:
                self.bridge.send_feature_command("search", "clear_highlights", {})
            
            # Emit cleared signal
            self.search_cleared.emit()
            
            logger.debug("Search cleared")
            
        except Exception as e:
            logger.error(f"Error clearing search: {e}")
    
    def get_search_history(self) -> List[SearchQuery]:
        """Get search history.
        
        Returns:
            List of recent search queries
        """
        return list(self.search_history)
    
    def get_current_results(self) -> List[SearchResult]:
        """Get current search results.
        
        Returns:
            List of current search results
        """
        return self.search_results.copy()
    
    def get_current_result(self) -> Optional[SearchResult]:
        """Get currently selected search result.
        
        Returns:
            Currently selected result or None
        """
        if self.search_results and 0 <= self.current_result_index < len(self.search_results):
            return self.search_results[self.current_result_index]
        return None
    
    def get_result_count(self) -> int:
        """Get total number of search results.
        
        Returns:
            Number of search results
        """
        return len(self.search_results)
    
    def get_current_result_index(self) -> int:
        """Get current result index.
        
        Returns:
            Current result index (0-based) or -1 if no results
        """
        return self.current_result_index
    
    def _get_cache_key(self, query: SearchQuery) -> str:
        """Generate cache key for search query.
        
        Args:
            query: Search query
            
        Returns:
            Cache key string
        """
        return f"{query.query}:{query.case_sensitive}:{query.whole_words}:{query.regex_enabled}"
    
    def _cleanup_cache(self) -> None:
        """Clean up search cache if it exceeds maximum size."""
        while len(self.search_cache) > self.cache_max_size:
            # Remove oldest cache entry
            oldest_key = next(iter(self.search_cache))
            del self.search_cache[oldest_key]
    
    def _update_average_search_time(self) -> None:
        """Update average search time metric."""
        if self.search_times:
            self.metrics.avg_search_time_ms = sum(self.search_times) / len(self.search_times)
        self.metrics.last_updated = time.time()
    
    def _update_cache_hit_rate(self, cache_hit: bool) -> None:
        """Update cache hit rate metric.
        
        Args:
            cache_hit: True if search result came from cache
        """
        # Simple running average calculation
        if cache_hit:
            self.metrics.cache_hit_rate = (self.metrics.cache_hit_rate * 0.9) + (1.0 * 0.1)
        else:
            self.metrics.cache_hit_rate = (self.metrics.cache_hit_rate * 0.9) + (0.0 * 0.1)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get search performance metrics.
        
        Returns:
            Dictionary containing search metrics
        """
        return {
            "total_searches": self.metrics.total_searches,
            "avg_search_time_ms": self.metrics.avg_search_time_ms,
            "last_search_time_ms": self.metrics.last_search_time_ms,
            "total_results_found": self.metrics.total_results_found,
            "cache_hit_rate": self.metrics.cache_hit_rate,
            "cache_size": len(self.search_cache),
            "history_size": len(self.search_history),
            "current_results": len(self.search_results),
            "targets_met": {
                "search_speed": self.metrics.avg_search_time_ms <= 2000.0  # 2s target
            }
        }
    
    def create_search_widget(self, parent: Optional[QWidget] = None) -> QWidget:
        """Create search UI widget.
        
        Args:
            parent: Parent widget
            
        Returns:
            Search widget
        """
        if self.search_widget:
            return self.search_widget
        
        # Create main widget
        widget = QWidget(parent)
        layout = QVBoxLayout(widget)
        
        # Search input row
        search_row = QHBoxLayout()
        
        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search in PDF...")
        self.search_input.returnPressed.connect(self._on_search_input)
        search_row.addWidget(self.search_input)
        
        # Search button
        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self._on_search_input)
        search_row.addWidget(search_btn)
        
        # Clear button
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_search)
        search_row.addWidget(clear_btn)
        
        layout.addLayout(search_row)
        
        # Options row
        options_row = QHBoxLayout()
        
        self.case_sensitive_cb = QCheckBox("Case sensitive")
        self.case_sensitive_cb.setChecked(self.config.search_case_sensitive)
        options_row.addWidget(self.case_sensitive_cb)
        
        self.whole_words_cb = QCheckBox("Whole words")
        self.whole_words_cb.setChecked(self.config.search_whole_words)
        options_row.addWidget(self.whole_words_cb)
        
        self.regex_cb = QCheckBox("Regex")
        self.regex_cb.setChecked(self.config.search_regex_enabled)
        options_row.addWidget(self.regex_cb)
        
        layout.addLayout(options_row)
        
        # Navigation row
        nav_row = QHBoxLayout()
        
        prev_btn = QPushButton("Previous")
        prev_btn.clicked.connect(self.previous_result)
        nav_row.addWidget(prev_btn)
        
        self.result_label = QLabel("No results")
        nav_row.addWidget(self.result_label)
        
        next_btn = QPushButton("Next")
        next_btn.clicked.connect(self.next_result)
        nav_row.addWidget(next_btn)
        
        layout.addLayout(nav_row)
        
        # Connect signals
        self.search_completed.connect(self._update_result_label)
        self.search_cleared.connect(lambda: self.result_label.setText("No results"))
        self.result_selected.connect(self._update_result_position)
        
        self.search_widget = widget
        return widget
    
    def _on_search_input(self) -> None:
        """Handle search input."""
        query = self.search_input.text().strip()
        if query:
            options = {
                "case_sensitive": self.case_sensitive_cb.isChecked(),
                "whole_words": self.whole_words_cb.isChecked(),
                "regex": self.regex_cb.isChecked()
            }
            self.search(query, options)
    
    def _update_result_label(self, query: str, results: List[Dict]) -> None:
        """Update result count label.
        
        Args:
            query: Search query
            results: Search results
        """
        count = len(results)
        if count == 0:
            self.result_label.setText("No results")
        else:
            self.result_label.setText(f"1 of {count}")
    
    def _update_result_position(self, result: SearchResult) -> None:
        """Update result position label.
        
        Args:
            result: Current search result
        """
        if self.search_results:
            current = self.current_result_index + 1
            total = len(self.search_results)
            self.result_label.setText(f"{current} of {total}")
    
    def cleanup(self) -> None:
        """Clean up resources."""
        try:
            self.clear_search()
            self.search_cache.clear()
            self.search_history.clear()
            
            if self.search_widget:
                self.search_widget.deleteLater()
                self.search_widget = None
            
            logger.info("SearchManager cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during search cleanup: {e}")