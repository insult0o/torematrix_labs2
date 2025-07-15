"""Search and filtering system for property panel

Provides advanced search capabilities with fuzzy matching, filtering,
and indexing for fast property discovery across multiple elements.
"""

from typing import Dict, List, Any, Optional, Set, Callable, NamedTuple
from dataclasses import dataclass, field
from enum import Enum
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, QLabel,
    QPushButton, QLineEdit, QComboBox, QCheckBox, QListWidget, QListWidgetItem,
    QTreeWidget, QTreeWidgetItem, QTabWidget, QSlider, QSpinBox, QDateEdit,
    QFrame, QSplitter, QScrollArea, QToolButton, QMenu, QWidgetAction,
    QButtonGroup, QRadioButton, QProgressBar, QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread, QObject, QDate
from PyQt6.QtGui import QFont, QIcon, QPixmap, QPalette, QColor, QAction

from .models import PropertyMetadata, PropertyValue
from .events import PropertyNotificationCenter, PropertyEventType


class SearchScope(Enum):
    """Scope of search operation"""
    ALL_ELEMENTS = "all_elements"
    SELECTED_ELEMENTS = "selected_elements"
    VISIBLE_ELEMENTS = "visible_elements"
    FILTERED_ELEMENTS = "filtered_elements"


class FilterType(Enum):
    """Type of property filter"""
    TEXT = "text"
    NUMERIC = "numeric"
    DATE = "date"
    BOOLEAN = "boolean"
    CATEGORY = "category"
    TYPE = "type"
    CUSTOM = "custom"


class SortOrder(Enum):
    """Sort order for search results"""
    RELEVANCE = "relevance"
    ALPHABETICAL = "alphabetical"
    MODIFIED_DATE = "modified_date"
    PROPERTY_COUNT = "property_count"
    ELEMENT_TYPE = "element_type"


@dataclass
class SearchResult:
    """Individual search result"""
    element_id: str
    property_name: str
    property_value: Any
    relevance_score: float
    match_positions: List[int] = field(default_factory=list)
    context: str = ""
    metadata: Optional[PropertyMetadata] = None


@dataclass
class SearchQuery:
    """Search query configuration"""
    text: str = ""
    scope: SearchScope = SearchScope.ALL_ELEMENTS
    case_sensitive: bool = False
    whole_words: bool = False
    regex: bool = False
    fuzzy: bool = True
    fuzzy_threshold: float = 0.6
    include_property_names: bool = True
    include_property_values: bool = True
    include_metadata: bool = False
    max_results: int = 100


@dataclass
class PropertyFilter:
    """Property filtering configuration"""
    filter_type: FilterType
    property_name: str = ""
    operator: str = "contains"  # contains, equals, starts_with, ends_with, greater_than, less_than
    value: Any = None
    case_sensitive: bool = False
    enabled: bool = True
    
    def matches(self, property_value: Any, property_metadata: Optional[PropertyMetadata] = None) -> bool:
        """Check if property value matches filter"""
        if not self.enabled:
            return True
        
        if self.filter_type == FilterType.TEXT:
            return self._match_text(property_value)
        elif self.filter_type == FilterType.NUMERIC:
            return self._match_numeric(property_value)
        elif self.filter_type == FilterType.DATE:
            return self._match_date(property_value)
        elif self.filter_type == FilterType.BOOLEAN:
            return self._match_boolean(property_value)
        elif self.filter_type == FilterType.CATEGORY:
            return self._match_category(property_metadata)
        elif self.filter_type == FilterType.TYPE:
            return self._match_type(property_value)
        
        return True
    
    def _match_text(self, value: Any) -> bool:
        """Match text values"""
        text_value = str(value)
        filter_value = str(self.value)
        
        if not self.case_sensitive:
            text_value = text_value.lower()
            filter_value = filter_value.lower()
        
        if self.operator == "contains":
            return filter_value in text_value
        elif self.operator == "equals":
            return text_value == filter_value
        elif self.operator == "starts_with":
            return text_value.startswith(filter_value)
        elif self.operator == "ends_with":
            return text_value.endswith(filter_value)
        elif self.operator == "not_contains":
            return filter_value not in text_value
        
        return False
    
    def _match_numeric(self, value: Any) -> bool:
        """Match numeric values"""
        try:
            num_value = float(value)
            filter_value = float(self.value)
            
            if self.operator == "equals":
                return abs(num_value - filter_value) < 1e-9
            elif self.operator == "greater_than":
                return num_value > filter_value
            elif self.operator == "less_than":
                return num_value < filter_value
            elif self.operator == "greater_equal":
                return num_value >= filter_value
            elif self.operator == "less_equal":
                return num_value <= filter_value
            elif self.operator == "between":
                if isinstance(self.value, (list, tuple)) and len(self.value) == 2:
                    return self.value[0] <= num_value <= self.value[1]
        except (ValueError, TypeError):
            return False
        
        return False
    
    def _match_date(self, value: Any) -> bool:
        """Match date values"""
        # Implementation would depend on date format
        return True
    
    def _match_boolean(self, value: Any) -> bool:
        """Match boolean values"""
        try:
            bool_value = bool(value)
            filter_value = bool(self.value)
            return bool_value == filter_value
        except (ValueError, TypeError):
            return False
    
    def _match_category(self, metadata: Optional[PropertyMetadata]) -> bool:
        """Match property category"""
        if not metadata:
            return True
        return metadata.category == self.value
    
    def _match_type(self, value: Any) -> bool:
        """Match property type"""
        value_type = type(value).__name__
        return value_type == self.value


class SearchIndex:
    """Fast search index for property data"""
    
    def __init__(self):
        self.property_index: Dict[str, Set[str]] = {}  # property_name -> element_ids
        self.value_index: Dict[str, Set[str]] = {}     # value_tokens -> element_ids
        self.element_properties: Dict[str, Dict[str, Any]] = {}  # element_id -> properties
        self.metadata_index: Dict[str, PropertyMetadata] = {}    # property_name -> metadata
        self.last_update = 0
    
    def update_element(self, element_id: str, properties: Dict[str, Any], 
                      metadata: Dict[str, PropertyMetadata] = None) -> None:
        """Update element in search index"""
        # Remove old entries
        self._remove_element(element_id)
        
        # Add new entries
        self.element_properties[element_id] = properties
        
        for prop_name, prop_value in properties.items():
            # Index property name
            if prop_name not in self.property_index:
                self.property_index[prop_name] = set()
            self.property_index[prop_name].add(element_id)
            
            # Index property value tokens
            value_tokens = self._tokenize_value(prop_value)
            for token in value_tokens:
                if token not in self.value_index:
                    self.value_index[token] = set()
                self.value_index[token].add(element_id)
            
            # Store metadata
            if metadata and prop_name in metadata:
                self.metadata_index[prop_name] = metadata[prop_name]
    
    def remove_element(self, element_id: str) -> None:
        """Remove element from search index"""
        self._remove_element(element_id)
    
    def _remove_element(self, element_id: str) -> None:
        """Internal method to remove element from all indices"""
        if element_id not in self.element_properties:
            return
        
        # Remove from property index
        for prop_name in self.element_properties[element_id]:
            if prop_name in self.property_index:
                self.property_index[prop_name].discard(element_id)
                if not self.property_index[prop_name]:
                    del self.property_index[prop_name]
        
        # Remove from value index
        for token_set in self.value_index.values():
            token_set.discard(element_id)
        
        # Clean up empty token entries
        self.value_index = {token: elements for token, elements in self.value_index.items() if elements}
        
        # Remove element properties
        del self.element_properties[element_id]
    
    def _tokenize_value(self, value: Any) -> List[str]:
        """Tokenize property value for indexing"""
        text = str(value).lower()
        # Simple tokenization - could be enhanced with proper NLP
        tokens = []
        
        # Split by common delimiters
        for delimiter in [' ', '-', '_', '.', ',', ';', ':', '/', '\\']:
            text = text.replace(delimiter, ' ')
        
        # Extract tokens
        for token in text.split():
            token = token.strip()
            if len(token) > 1:  # Ignore single character tokens
                tokens.append(token)
                
                # Add partial tokens for fuzzy matching
                if len(token) > 3:
                    for i in range(len(token) - 2):
                        tokens.append(token[i:i+3])
        
        return tokens
    
    def search(self, query: SearchQuery) -> List[str]:
        """Search for elements matching query"""
        if not query.text:
            return list(self.element_properties.keys())
        
        matching_elements = set()
        query_tokens = self._tokenize_value(query.text)
        
        # Search property names
        if query.include_property_names:
            for prop_name in self.property_index:
                if self._matches_query(prop_name, query.text, query):
                    matching_elements.update(self.property_index[prop_name])
        
        # Search property values
        if query.include_property_values:
            for token in query_tokens:
                if token in self.value_index:
                    matching_elements.update(self.value_index[token])
        
        # Convert to list and limit results
        results = list(matching_elements)
        if query.max_results > 0:
            results = results[:query.max_results]
        
        return results
    
    def _matches_query(self, text: str, query: str, search_query: SearchQuery) -> bool:
        """Check if text matches search query"""
        if not search_query.case_sensitive:
            text = text.lower()
            query = query.lower()
        
        if search_query.whole_words:
            # Implement whole word matching
            import re
            pattern = r'\b' + re.escape(query) + r'\b'
            return bool(re.search(pattern, text))
        else:
            return query in text


class SearchWorker(QObject):
    """Worker thread for search operations"""
    
    # Signals
    search_started = pyqtSignal()
    search_progress = pyqtSignal(int, str)  # percentage, status
    search_completed = pyqtSignal(list)     # search results
    search_error = pyqtSignal(str)          # error message
    
    def __init__(self):
        super().__init__()
        self.search_index = SearchIndex()
        self.property_manager = None
        self.cancel_requested = False
    
    def set_property_manager(self, manager) -> None:
        """Set property manager"""
        self.property_manager = manager
    
    def update_index(self, element_ids: List[str]) -> None:
        """Update search index for elements"""
        if not self.property_manager:
            return
        
        total = len(element_ids)
        for i, element_id in enumerate(element_ids):
            if self.cancel_requested:
                break
            
            # Update progress
            progress = int((i / total) * 100) if total > 0 else 100
            self.search_progress.emit(progress, f"Indexing element {i+1}/{total}")
            
            # Get element properties
            properties = self.property_manager.get_element_properties(element_id)
            metadata = {}
            
            # Get metadata for each property
            for prop_name in properties:
                prop_metadata = self.property_manager.get_property_metadata(element_id, prop_name)
                if prop_metadata:
                    metadata[prop_name] = prop_metadata
            
            # Update index
            self.search_index.update_element(element_id, properties, metadata)
    
    def search(self, query: SearchQuery) -> None:
        """Perform search operation"""
        self.cancel_requested = False
        self.search_started.emit()
        
        try:
            # Get matching elements
            self.search_progress.emit(25, "Searching elements...")
            matching_elements = self.search_index.search(query)
            
            # Calculate relevance scores and create results
            self.search_progress.emit(50, "Calculating relevance...")
            results = []
            
            for element_id in matching_elements:
                if self.cancel_requested:
                    break
                
                element_results = self._create_element_results(element_id, query)
                results.extend(element_results)
            
            # Sort results by relevance
            self.search_progress.emit(75, "Sorting results...")
            results.sort(key=lambda r: r.relevance_score, reverse=True)
            
            # Limit results
            if query.max_results > 0:
                results = results[:query.max_results]
            
            self.search_progress.emit(100, "Search completed")
            self.search_completed.emit(results)
            
        except Exception as e:
            self.search_error.emit(str(e))
    
    def _create_element_results(self, element_id: str, query: SearchQuery) -> List[SearchResult]:
        """Create search results for element"""
        results = []
        properties = self.search_index.element_properties.get(element_id, {})
        
        for prop_name, prop_value in properties.items():
            # Calculate relevance score
            relevance = self._calculate_relevance(prop_name, prop_value, query)
            
            if relevance > 0:
                metadata = self.search_index.metadata_index.get(prop_name)
                
                result = SearchResult(
                    element_id=element_id,
                    property_name=prop_name,
                    property_value=prop_value,
                    relevance_score=relevance,
                    metadata=metadata,
                    context=self._get_context(prop_name, prop_value, query)
                )
                results.append(result)
        
        return results
    
    def _calculate_relevance(self, prop_name: str, prop_value: Any, query: SearchQuery) -> float:
        """Calculate relevance score for property"""
        score = 0.0
        query_text = query.text.lower() if not query.case_sensitive else query.text
        
        # Check property name match
        if query.include_property_names:
            prop_name_lower = prop_name.lower() if not query.case_sensitive else prop_name
            if query_text in prop_name_lower:
                score += 1.0
                if prop_name_lower == query_text:
                    score += 2.0  # Exact match bonus
        
        # Check property value match
        if query.include_property_values:
            value_text = str(prop_value)
            value_lower = value_text.lower() if not query.case_sensitive else value_text
            if query_text in value_lower:
                score += 0.8
                if value_lower == query_text:
                    score += 1.5  # Exact match bonus
        
        # Fuzzy matching
        if query.fuzzy and score == 0:
            fuzzy_score = self._fuzzy_match(query_text, prop_name + " " + str(prop_value))
            if fuzzy_score >= query.fuzzy_threshold:
                score += fuzzy_score * 0.5
        
        return score
    
    def _fuzzy_match(self, query: str, text: str) -> float:
        """Calculate fuzzy match score using simple algorithm"""
        if not query or not text:
            return 0.0
        
        query = query.lower()
        text = text.lower()
        
        # Simple fuzzy matching based on character overlap
        query_chars = set(query)
        text_chars = set(text)
        overlap = len(query_chars & text_chars)
        total = len(query_chars | text_chars)
        
        return overlap / total if total > 0 else 0.0
    
    def _get_context(self, prop_name: str, prop_value: Any, query: SearchQuery) -> str:
        """Get context string for search result"""
        return f"{prop_name}: {prop_value}"
    
    def cancel_search(self) -> None:
        """Cancel current search operation"""
        self.cancel_requested = True


class PropertySearchWidget(QWidget):
    """Main search widget for property panel"""
    
    # Signals
    search_requested = pyqtSignal(object)  # SearchQuery
    search_results_changed = pyqtSignal(list)  # SearchResult list
    filter_changed = pyqtSignal()
    element_selected = pyqtSignal(str)  # element_id
    
    def __init__(self, notification_center: PropertyNotificationCenter):
        super().__init__()
        self.notification_center = notification_center
        self.property_manager = None
        
        # Search state
        self.current_query = SearchQuery()
        self.search_results: List[SearchResult] = []
        self.active_filters: List[PropertyFilter] = []
        
        # Worker thread for search
        self.search_thread = QThread()
        self.search_worker = SearchWorker()
        self.search_worker.moveToThread(self.search_thread)
        
        # Setup UI
        self._setup_ui()
        self._setup_worker_connections()
        
        # Search timer for delayed search
        self.search_timer = QTimer()
        self.search_timer.timeout.connect(self._perform_search)
        self.search_timer.setSingleShot(True)
    
    def _setup_ui(self) -> None:
        """Setup search widget UI"""
        layout = QVBoxLayout(self)
        
        # Search input section
        search_section = self._create_search_section()
        layout.addWidget(search_section)
        
        # Filter section
        filter_section = self._create_filter_section()
        layout.addWidget(filter_section)
        
        # Results section
        results_section = self._create_results_section()
        layout.addWidget(results_section)
        
        # Progress section
        progress_section = self._create_progress_section()
        layout.addWidget(progress_section)
    
    def _create_search_section(self) -> QWidget:
        """Create search input section"""
        section = QGroupBox("Search Properties")
        layout = QVBoxLayout(section)
        
        # Main search input
        search_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search properties and values...")
        self.search_input.textChanged.connect(self._on_search_text_changed)
        self.search_input.returnPressed.connect(self._perform_search)
        search_layout.addWidget(self.search_input)
        
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self._perform_search)
        search_layout.addWidget(self.search_button)
        
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self._clear_search)
        search_layout.addWidget(self.clear_button)
        
        layout.addLayout(search_layout)
        
        # Search options
        options_layout = QGridLayout()
        
        self.case_sensitive_cb = QCheckBox("Case sensitive")
        options_layout.addWidget(self.case_sensitive_cb, 0, 0)
        
        self.whole_words_cb = QCheckBox("Whole words")
        options_layout.addWidget(self.whole_words_cb, 0, 1)
        
        self.fuzzy_search_cb = QCheckBox("Fuzzy search")
        self.fuzzy_search_cb.setChecked(True)
        options_layout.addWidget(self.fuzzy_search_cb, 0, 2)
        
        self.regex_cb = QCheckBox("Regular expression")
        options_layout.addWidget(self.regex_cb, 1, 0)
        
        self.include_names_cb = QCheckBox("Property names")
        self.include_names_cb.setChecked(True)
        options_layout.addWidget(self.include_names_cb, 1, 1)
        
        self.include_values_cb = QCheckBox("Property values")
        self.include_values_cb.setChecked(True)
        options_layout.addWidget(self.include_values_cb, 1, 2)
        
        layout.addLayout(options_layout)
        
        # Scope selection
        scope_layout = QHBoxLayout()
        scope_layout.addWidget(QLabel("Search scope:"))
        
        self.scope_combo = QComboBox()
        for scope in SearchScope:
            self.scope_combo.addItem(scope.value.replace('_', ' ').title(), scope)
        scope_layout.addWidget(self.scope_combo)
        
        scope_layout.addStretch()
        
        # Max results
        scope_layout.addWidget(QLabel("Max results:"))
        self.max_results_spin = QSpinBox()
        self.max_results_spin.setRange(10, 1000)
        self.max_results_spin.setValue(100)
        scope_layout.addWidget(self.max_results_spin)
        
        layout.addLayout(scope_layout)
        
        return section
    
    def _create_filter_section(self) -> QWidget:
        """Create filter section"""
        section = QGroupBox("Filters")
        layout = QVBoxLayout(section)
        
        # Filter controls
        controls_layout = QHBoxLayout()
        
        self.add_filter_btn = QPushButton("Add Filter")
        self.add_filter_btn.clicked.connect(self._add_filter)
        controls_layout.addWidget(self.add_filter_btn)
        
        self.clear_filters_btn = QPushButton("Clear All")
        self.clear_filters_btn.clicked.connect(self._clear_filters)
        controls_layout.addWidget(self.clear_filters_btn)
        
        controls_layout.addStretch()
        
        layout.addLayout(controls_layout)
        
        # Filter list
        self.filter_scroll = QScrollArea()
        self.filter_scroll.setWidgetResizable(True)
        self.filter_scroll.setMaximumHeight(150)
        
        self.filter_container = QWidget()
        self.filter_layout = QVBoxLayout(self.filter_container)
        self.filter_layout.addStretch()
        
        self.filter_scroll.setWidget(self.filter_container)
        layout.addWidget(self.filter_scroll)
        
        return section
    
    def _create_results_section(self) -> QWidget:
        """Create results section"""
        section = QGroupBox("Search Results")
        layout = QVBoxLayout(section)
        
        # Results header
        header_layout = QHBoxLayout()
        
        self.results_label = QLabel("No results")
        header_layout.addWidget(self.results_label)
        
        header_layout.addStretch()
        
        # Sort options
        header_layout.addWidget(QLabel("Sort by:"))
        self.sort_combo = QComboBox()
        for sort_order in SortOrder:
            self.sort_combo.addItem(sort_order.value.replace('_', ' ').title(), sort_order)
        self.sort_combo.currentTextChanged.connect(self._sort_results)
        header_layout.addWidget(self.sort_combo)
        
        layout.addLayout(header_layout)
        
        # Results list
        self.results_list = QListWidget()
        self.results_list.itemClicked.connect(self._on_result_selected)
        self.results_list.itemDoubleClicked.connect(self._on_result_activated)
        layout.addWidget(self.results_list)
        
        return section
    
    def _create_progress_section(self) -> QWidget:
        """Create progress section"""
        section = QFrame()
        layout = QHBoxLayout(section)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self._cancel_search)
        self.cancel_button.setVisible(False)
        layout.addWidget(self.cancel_button)
        
        return section
    
    def _setup_worker_connections(self) -> None:
        """Setup worker thread connections"""
        self.search_worker.search_started.connect(self._on_search_started)
        self.search_worker.search_progress.connect(self._on_search_progress)
        self.search_worker.search_completed.connect(self._on_search_completed)
        self.search_worker.search_error.connect(self._on_search_error)
        
        self.search_thread.started.connect(lambda: self.search_worker.search(self.current_query))
    
    def set_property_manager(self, manager) -> None:
        """Set property manager"""
        self.property_manager = manager
        self.search_worker.set_property_manager(manager)
    
    def _on_search_text_changed(self, text: str) -> None:
        """Handle search text change"""
        # Delayed search for better performance
        self.search_timer.start(300)  # 300ms delay
    
    def _perform_search(self) -> None:
        """Perform search operation"""
        # Update query from UI
        self._update_query_from_ui()
        
        # Start search
        if not self.search_thread.isRunning():
            self.search_thread.start()
        
        self.search_requested.emit(self.current_query)
    
    def _update_query_from_ui(self) -> None:
        """Update search query from UI controls"""
        self.current_query.text = self.search_input.text()
        self.current_query.case_sensitive = self.case_sensitive_cb.isChecked()
        self.current_query.whole_words = self.whole_words_cb.isChecked()
        self.current_query.regex = self.regex_cb.isChecked()
        self.current_query.fuzzy = self.fuzzy_search_cb.isChecked()
        self.current_query.include_property_names = self.include_names_cb.isChecked()
        self.current_query.include_property_values = self.include_values_cb.isChecked()
        self.current_query.scope = self.scope_combo.currentData()
        self.current_query.max_results = self.max_results_spin.value()
    
    def _clear_search(self) -> None:
        """Clear search input and results"""
        self.search_input.clear()
        self.search_results.clear()
        self._update_results_display()
    
    def _add_filter(self) -> None:
        """Add new filter"""
        filter_widget = PropertyFilterWidget()
        filter_widget.filter_changed.connect(self._on_filter_changed)
        filter_widget.filter_removed.connect(self._remove_filter)
        
        # Insert before stretch
        self.filter_layout.insertWidget(self.filter_layout.count() - 1, filter_widget)
        
        # Update filters list
        self._update_active_filters()
    
    def _remove_filter(self, filter_widget) -> None:
        """Remove filter widget"""
        filter_widget.setParent(None)
        filter_widget.deleteLater()
        self._update_active_filters()
    
    def _clear_filters(self) -> None:
        """Clear all filters"""
        # Remove all filter widgets
        while self.filter_layout.count() > 1:  # Keep the stretch
            item = self.filter_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.active_filters.clear()
        self.filter_changed.emit()
    
    def _update_active_filters(self) -> None:
        """Update active filters list"""
        self.active_filters.clear()
        
        for i in range(self.filter_layout.count() - 1):  # Exclude stretch
            item = self.filter_layout.itemAt(i)
            if item and isinstance(item.widget(), PropertyFilterWidget):
                filter_widget = item.widget()
                filter_obj = filter_widget.get_filter()
                if filter_obj and filter_obj.enabled:
                    self.active_filters.append(filter_obj)
        
        self.filter_changed.emit()
    
    def _on_filter_changed(self) -> None:
        """Handle filter change"""
        self._update_active_filters()
    
    def _sort_results(self) -> None:
        """Sort search results"""
        if not self.search_results:
            return
        
        sort_order = self.sort_combo.currentData()
        
        if sort_order == SortOrder.RELEVANCE:
            self.search_results.sort(key=lambda r: r.relevance_score, reverse=True)
        elif sort_order == SortOrder.ALPHABETICAL:
            self.search_results.sort(key=lambda r: r.property_name)
        elif sort_order == SortOrder.ELEMENT_TYPE:
            self.search_results.sort(key=lambda r: r.element_id)
        
        self._update_results_display()
    
    def _update_results_display(self) -> None:
        """Update results display"""
        self.results_list.clear()
        
        # Update results label
        count = len(self.search_results)
        self.results_label.setText(f"{count} results found")
        
        # Apply filters
        filtered_results = self._apply_filters(self.search_results)
        
        # Add results to list
        for result in filtered_results:
            item = QListWidgetItem()
            item.setText(f"{result.element_id}: {result.property_name} = {result.property_value}")
            item.setData(Qt.ItemDataRole.UserRole, result)
            
            # Add relevance score as tooltip
            item.setToolTip(f"Relevance: {result.relevance_score:.2f}\nContext: {result.context}")
            
            self.results_list.addItem(item)
        
        self.search_results_changed.emit(filtered_results)
    
    def _apply_filters(self, results: List[SearchResult]) -> List[SearchResult]:
        """Apply active filters to results"""
        if not self.active_filters:
            return results
        
        filtered = []
        for result in results:
            # Check if result passes all filters
            passes_all = True
            for filter_obj in self.active_filters:
                if not filter_obj.matches(result.property_value, result.metadata):
                    passes_all = False
                    break
            
            if passes_all:
                filtered.append(result)
        
        return filtered
    
    def _on_result_selected(self, item: QListWidgetItem) -> None:
        """Handle result selection"""
        result = item.data(Qt.ItemDataRole.UserRole)
        if result:
            # Could highlight the property in the panel
            pass
    
    def _on_result_activated(self, item: QListWidgetItem) -> None:
        """Handle result activation (double-click)"""
        result = item.data(Qt.ItemDataRole.UserRole)
        if result:
            self.element_selected.emit(result.element_id)
    
    def _on_search_started(self) -> None:
        """Handle search start"""
        self.progress_bar.setVisible(True)
        self.cancel_button.setVisible(True)
        self.search_button.setEnabled(False)
    
    def _on_search_progress(self, percentage: int, message: str) -> None:
        """Handle search progress"""
        self.progress_bar.setValue(percentage)
        self.status_label.setText(message)
    
    def _on_search_completed(self, results: List[SearchResult]) -> None:
        """Handle search completion"""
        self.search_results = results
        self._update_results_display()
        
        self.progress_bar.setVisible(False)
        self.cancel_button.setVisible(False)
        self.search_button.setEnabled(True)
        self.status_label.setText("Search completed")
    
    def _on_search_error(self, error_message: str) -> None:
        """Handle search error"""
        self.progress_bar.setVisible(False)
        self.cancel_button.setVisible(False)
        self.search_button.setEnabled(True)
        self.status_label.setText(f"Search error: {error_message}")
    
    def _cancel_search(self) -> None:
        """Cancel current search"""
        self.search_worker.cancel_search()
        self.status_label.setText("Search cancelled")


class PropertyFilterWidget(QWidget):
    """Widget for configuring individual property filter"""
    
    # Signals
    filter_changed = pyqtSignal()
    filter_removed = pyqtSignal(object)  # self
    
    def __init__(self):
        super().__init__()
        self.filter = PropertyFilter(FilterType.TEXT)
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Setup filter widget UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        
        # Enable checkbox
        self.enabled_cb = QCheckBox()
        self.enabled_cb.setChecked(True)
        self.enabled_cb.toggled.connect(self._on_filter_changed)
        layout.addWidget(self.enabled_cb)
        
        # Filter type
        self.type_combo = QComboBox()
        for filter_type in FilterType:
            self.type_combo.addItem(filter_type.value.title(), filter_type)
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
        layout.addWidget(self.type_combo)
        
        # Property name
        self.property_input = QLineEdit()
        self.property_input.setPlaceholderText("Property name")
        self.property_input.textChanged.connect(self._on_filter_changed)
        layout.addWidget(self.property_input)
        
        # Operator
        self.operator_combo = QComboBox()
        self._update_operators()
        self.operator_combo.currentTextChanged.connect(self._on_filter_changed)
        layout.addWidget(self.operator_combo)
        
        # Value
        self.value_input = QLineEdit()
        self.value_input.setPlaceholderText("Filter value")
        self.value_input.textChanged.connect(self._on_filter_changed)
        layout.addWidget(self.value_input)
        
        # Remove button
        self.remove_btn = QPushButton("×")
        self.remove_btn.setMaximumSize(25, 25)
        self.remove_btn.clicked.connect(lambda: self.filter_removed.emit(self))
        layout.addWidget(self.remove_btn)
    
    def _update_operators(self) -> None:
        """Update operator options based on filter type"""
        self.operator_combo.clear()
        
        filter_type = self.type_combo.currentData()
        
        if filter_type == FilterType.TEXT:
            operators = ["contains", "equals", "starts_with", "ends_with", "not_contains"]
        elif filter_type == FilterType.NUMERIC:
            operators = ["equals", "greater_than", "less_than", "greater_equal", "less_equal", "between"]
        elif filter_type == FilterType.BOOLEAN:
            operators = ["equals"]
        else:
            operators = ["equals"]
        
        for op in operators:
            self.operator_combo.addItem(op.replace('_', ' ').title(), op)
    
    def _on_type_changed(self) -> None:
        """Handle filter type change"""
        self._update_operators()
        self._on_filter_changed()
    
    def _on_filter_changed(self) -> None:
        """Handle filter change"""
        self._update_filter()
        self.filter_changed.emit()
    
    def _update_filter(self) -> None:
        """Update filter object from UI"""
        self.filter.filter_type = self.type_combo.currentData()
        self.filter.property_name = self.property_input.text()
        self.filter.operator = self.operator_combo.currentData()
        self.filter.value = self.value_input.text()
        self.filter.enabled = self.enabled_cb.isChecked()
    
    def get_filter(self) -> PropertyFilter:
        """Get current filter configuration"""
        self._update_filter()
        return self.filter


# Export search components
__all__ = [
    'SearchScope',
    'FilterType', 
    'SortOrder',
    'SearchResult',
    'SearchQuery',
    'PropertyFilter',
    'SearchIndex',
    'SearchWorker',
    'PropertySearchWidget',
    'PropertyFilterWidget'
]