"""
Search and Filter System for Element Tree View

Provides real-time search and filtering capabilities with multiple criteria.
"""

import re
from typing import List, Dict, Any, Optional, Set, Callable
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QModelIndex, Qt, QSortFilterProxyModel
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, 
                            QComboBox, QPushButton, QLabel, QCheckBox, 
                            QSlider, QSpinBox, QFrame, QTreeView)
from PyQt6.QtGui import QKeySequence, QAction

from ..models.tree_node import TreeNode
from ..interfaces.tree_interfaces import ElementProtocol


class SearchCriteria:
    """Represents search/filter criteria."""
    
    def __init__(self):
        self.text_query: str = ""
        self.element_types: Set[str] = set()
        self.confidence_min: float = 0.0
        self.confidence_max: float = 1.0
        self.regex_enabled: bool = False
        self.case_sensitive: bool = False
        self.whole_words_only: bool = False
        self.include_children: bool = True
        self.custom_filters: Dict[str, Any] = {}
    
    def matches_element(self, element: ElementProtocol) -> bool:
        """Check if element matches criteria."""
        # Text query
        if self.text_query:
            text_to_search = element.text or ""
            query = self.text_query
            
            if not self.case_sensitive:
                text_to_search = text_to_search.lower()
                query = query.lower()
            
            if self.regex_enabled:
                try:
                    flags = 0 if self.case_sensitive else re.IGNORECASE
                    if not re.search(query, text_to_search, flags):
                        return False
                except re.error:
                    # Invalid regex - fall back to simple search
                    if query not in text_to_search:
                        return False
            else:
                if self.whole_words_only:
                    # Simple word boundary check
                    import re
                    pattern = r'\b' + re.escape(query) + r'\b'
                    flags = 0 if self.case_sensitive else re.IGNORECASE
                    if not re.search(pattern, text_to_search, flags):
                        return False
                else:
                    if query not in text_to_search:
                        return False
        
        # Element type
        if self.element_types and element.type not in self.element_types:
            return False
        
        # Confidence range
        if element.confidence is not None:
            if not (self.confidence_min <= element.confidence <= self.confidence_max):
                return False
        
        return True
    
    def is_empty(self) -> bool:
        """Check if criteria is empty (no filtering)."""
        return (not self.text_query and 
                not self.element_types and 
                self.confidence_min == 0.0 and 
                self.confidence_max == 1.0 and
                not self.custom_filters)


class ElementFilterProxyModel(QSortFilterProxyModel):
    """Proxy model for filtering element tree."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.criteria = SearchCriteria()
        self.visible_elements: Set[str] = set()
        
    def set_criteria(self, criteria: SearchCriteria) -> None:
        """Set filter criteria and refresh."""
        self.criteria = criteria
        self.invalidateFilter()
    
    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        """Check if row should be accepted by filter."""
        if self.criteria.is_empty():
            return True
        
        # Get source model and index
        source_model = self.sourceModel()
        if not source_model:
            return True
        
        source_index = source_model.index(source_row, 0, source_parent)
        if not source_index.isValid():
            return False
        
        # Get element
        element_id = source_model.data(source_index, Qt.ItemDataRole.UserRole)
        if not element_id:
            return False
        
        element = source_model.get_element_by_id(element_id)
        if not element:
            return False
        
        # Check if element matches criteria
        if self.criteria.matches_element(element):
            return True
        
        # Check children if include_children is enabled
        if self.criteria.include_children:
            return self._has_matching_children(source_index)
        
        return False
    
    def _has_matching_children(self, parent_index: QModelIndex) -> bool:
        """Check if any children match the criteria."""
        source_model = self.sourceModel()
        if not source_model:
            return False
        
        row_count = source_model.rowCount(parent_index)
        for row in range(row_count):
            child_index = source_model.index(row, 0, parent_index)
            if self.filterAcceptsRow(row, parent_index):
                return True
            
            # Recursive check
            if self._has_matching_children(child_index):
                return True
        
        return False


class SearchBar(QWidget):
    """Search bar widget with advanced options."""
    
    # Signals
    searchChanged = pyqtSignal(str)  # query
    criteriaChanged = pyqtSignal(object)  # SearchCriteria
    searchCleared = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.criteria = SearchCriteria()
        self.setup_ui()
        self.setup_connections()
    
    def setup_ui(self) -> None:
        """Setup user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # Main search row
        search_row = QHBoxLayout()
        
        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search elements...")
        self.search_input.setClearButtonEnabled(True)
        search_row.addWidget(self.search_input)
        
        # Search options button
        self.options_button = QPushButton("Options")
        self.options_button.setCheckable(True)
        search_row.addWidget(self.options_button)
        
        # Clear button
        self.clear_button = QPushButton("Clear")
        search_row.addWidget(self.clear_button)
        
        layout.addLayout(search_row)
        
        # Advanced options panel (initially hidden)
        self.options_panel = QFrame()
        self.options_panel.setFrameStyle(QFrame.Shape.StyledPanel)
        self.options_panel.setVisible(False)
        self._setup_options_panel()
        layout.addWidget(self.options_panel)
    
    def _setup_options_panel(self) -> None:
        """Setup advanced options panel."""
        layout = QVBoxLayout(self.options_panel)
        
        # Search options row 1
        options_row1 = QHBoxLayout()
        
        self.regex_checkbox = QCheckBox("Regex")
        options_row1.addWidget(self.regex_checkbox)
        
        self.case_sensitive_checkbox = QCheckBox("Case sensitive")
        options_row1.addWidget(self.case_sensitive_checkbox)
        
        self.whole_words_checkbox = QCheckBox("Whole words")
        options_row1.addWidget(self.whole_words_checkbox)
        
        options_row1.addStretch()
        layout.addLayout(options_row1)
        
        # Element type filter
        type_row = QHBoxLayout()
        type_row.addWidget(QLabel("Types:"))
        
        self.type_combo = QComboBox()
        self.type_combo.setEditable(False)
        self.type_combo.addItem("All Types", "")
        self.type_combo.addItems([
            "Text", "Title", "Header", "List", "List Item",
            "Table", "Table Cell", "Image", "Formula", "Code"
        ])
        type_row.addWidget(self.type_combo)
        
        type_row.addStretch()
        layout.addLayout(type_row)
        
        # Confidence filter
        conf_row = QHBoxLayout()
        conf_row.addWidget(QLabel("Confidence:"))
        
        self.conf_min_spin = QSpinBox()
        self.conf_min_spin.setRange(0, 100)
        self.conf_min_spin.setValue(0)
        self.conf_min_spin.setSuffix("%")
        conf_row.addWidget(self.conf_min_spin)
        
        conf_row.addWidget(QLabel("to"))
        
        self.conf_max_spin = QSpinBox()
        self.conf_max_spin.setRange(0, 100)
        self.conf_max_spin.setValue(100)
        self.conf_max_spin.setSuffix("%")
        conf_row.addWidget(self.conf_max_spin)
        
        conf_row.addStretch()
        layout.addLayout(conf_row)
        
        # Additional options
        misc_row = QHBoxLayout()
        
        self.include_children_checkbox = QCheckBox("Include children in results")
        self.include_children_checkbox.setChecked(True)
        misc_row.addWidget(self.include_children_checkbox)
        
        misc_row.addStretch()
        layout.addLayout(misc_row)
    
    def setup_connections(self) -> None:
        """Setup signal connections."""
        # Search input
        self.search_input.textChanged.connect(self._on_search_changed)
        self.search_input.returnPressed.connect(self._update_criteria)
        
        # Buttons
        self.options_button.toggled.connect(self.options_panel.setVisible)
        self.clear_button.clicked.connect(self.clear_search)
        
        # Options
        self.regex_checkbox.toggled.connect(self._update_criteria)
        self.case_sensitive_checkbox.toggled.connect(self._update_criteria)
        self.whole_words_checkbox.toggled.connect(self._update_criteria)
        self.type_combo.currentTextChanged.connect(self._update_criteria)
        self.conf_min_spin.valueChanged.connect(self._update_criteria)
        self.conf_max_spin.valueChanged.connect(self._update_criteria)
        self.include_children_checkbox.toggled.connect(self._update_criteria)
    
    def _on_search_changed(self, text: str) -> None:
        """Handle search text change."""
        self.searchChanged.emit(text)
        self._update_criteria()
    
    def _update_criteria(self) -> None:
        """Update search criteria from UI."""
        self.criteria.text_query = self.search_input.text()
        self.criteria.regex_enabled = self.regex_checkbox.isChecked()
        self.criteria.case_sensitive = self.case_sensitive_checkbox.isChecked()
        self.criteria.whole_words_only = self.whole_words_checkbox.isChecked()
        self.criteria.confidence_min = self.conf_min_spin.value() / 100.0
        self.criteria.confidence_max = self.conf_max_spin.value() / 100.0
        self.criteria.include_children = self.include_children_checkbox.isChecked()
        
        # Element types
        type_text = self.type_combo.currentText().lower()
        if type_text and type_text != "all types":
            self.criteria.element_types = {type_text}
        else:
            self.criteria.element_types = set()
        
        self.criteriaChanged.emit(self.criteria)
    
    def clear_search(self) -> None:
        """Clear search and reset criteria."""
        self.search_input.clear()
        self.regex_checkbox.setChecked(False)
        self.case_sensitive_checkbox.setChecked(False)
        self.whole_words_checkbox.setChecked(False)
        self.type_combo.setCurrentIndex(0)
        self.conf_min_spin.setValue(0)
        self.conf_max_spin.setValue(100)
        self.include_children_checkbox.setChecked(True)
        
        self.criteria = SearchCriteria()
        self.searchCleared.emit()
        self.criteriaChanged.emit(self.criteria)
    
    def set_search_text(self, text: str) -> None:
        """Set search text programmatically."""
        self.search_input.setText(text)
    
    def get_criteria(self) -> SearchCriteria:
        """Get current search criteria."""
        return self.criteria
    
    def set_criteria(self, criteria: SearchCriteria) -> None:
        """Set search criteria."""
        self.criteria = criteria
        
        # Update UI
        self.search_input.setText(criteria.text_query)
        self.regex_checkbox.setChecked(criteria.regex_enabled)
        self.case_sensitive_checkbox.setChecked(criteria.case_sensitive)
        self.whole_words_checkbox.setChecked(criteria.whole_words_only)
        self.conf_min_spin.setValue(int(criteria.confidence_min * 100))
        self.conf_max_spin.setValue(int(criteria.confidence_max * 100))
        self.include_children_checkbox.setChecked(criteria.include_children)
        
        # Set element type
        if criteria.element_types:
            type_text = next(iter(criteria.element_types)).title()
            index = self.type_combo.findText(type_text)
            if index >= 0:
                self.type_combo.setCurrentIndex(index)


class SearchHighlighter:
    """Highlights search matches in tree view."""
    
    def __init__(self, tree_view: QTreeView):
        self.tree_view = tree_view
        self.search_query = ""
        self.case_sensitive = False
        
    def set_search_query(self, query: str, case_sensitive: bool = False) -> None:
        """Set search query for highlighting."""
        self.search_query = query
        self.case_sensitive = case_sensitive
        self.tree_view.viewport().update()
    
    def clear_highlighting(self) -> None:
        """Clear search highlighting."""
        self.search_query = ""
        self.tree_view.viewport().update()


class SearchNavigator:
    """Navigates through search results."""
    
    def __init__(self, tree_view: QTreeView):
        self.tree_view = tree_view
        self.results: List[QModelIndex] = []
        self.current_index = -1
    
    def set_results(self, results: List[QModelIndex]) -> None:
        """Set search results for navigation."""
        self.results = results
        self.current_index = -1
    
    def next_result(self) -> bool:
        """Navigate to next search result."""
        if not self.results:
            return False
        
        self.current_index = (self.current_index + 1) % len(self.results)
        self._navigate_to_current()
        return True
    
    def previous_result(self) -> bool:
        """Navigate to previous search result."""
        if not self.results:
            return False
        
        self.current_index = (self.current_index - 1) % len(self.results)
        self._navigate_to_current()
        return True
    
    def first_result(self) -> bool:
        """Navigate to first search result."""
        if not self.results:
            return False
        
        self.current_index = 0
        self._navigate_to_current()
        return True
    
    def last_result(self) -> bool:
        """Navigate to last search result."""
        if not self.results:
            return False
        
        self.current_index = len(self.results) - 1
        self._navigate_to_current()
        return True
    
    def _navigate_to_current(self) -> None:
        """Navigate to current result index."""
        if 0 <= self.current_index < len(self.results):
            index = self.results[self.current_index]
            self.tree_view.scrollTo(index)
            self.tree_view.setCurrentIndex(index)
    
    def get_current_position(self) -> tuple:
        """Get current position (current, total)."""
        if not self.results:
            return (0, 0)
        return (self.current_index + 1, len(self.results))


class SearchFilterManager(QObject):
    """Manages search and filter functionality for tree view."""
    
    # Signals
    searchStarted = pyqtSignal(str)  # query
    searchCompleted = pyqtSignal(int)  # result_count
    filterChanged = pyqtSignal(object)  # criteria
    resultsNavigated = pyqtSignal(int, int)  # current, total
    
    def __init__(self, tree_view: QTreeView, parent=None):
        super().__init__(parent)
        self.tree_view = tree_view
        
        # Components
        self.search_bar = SearchBar()
        self.proxy_model = ElementFilterProxyModel()
        self.highlighter = SearchHighlighter(tree_view)
        self.navigator = SearchNavigator(tree_view)
        
        # Timers for delayed search
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._perform_search)
        
        # Setup
        self._setup_connections()
        self._setup_shortcuts()
    
    def _setup_connections(self) -> None:
        """Setup signal connections."""
        # Search bar
        self.search_bar.searchChanged.connect(self._on_search_changed)
        self.search_bar.criteriaChanged.connect(self._on_criteria_changed)
        self.search_bar.searchCleared.connect(self._on_search_cleared)
    
    def _setup_shortcuts(self) -> None:
        """Setup keyboard shortcuts."""
        # Find shortcuts
        find_action = QAction(self.tree_view)
        find_action.setShortcut(QKeySequence.StandardKey.Find)
        find_action.triggered.connect(self.focus_search)
        self.tree_view.addAction(find_action)
        
        # Find next/previous
        find_next_action = QAction(self.tree_view)
        find_next_action.setShortcut(QKeySequence.StandardKey.FindNext)
        find_next_action.triggered.connect(self.next_result)
        self.tree_view.addAction(find_next_action)
        
        find_prev_action = QAction(self.tree_view)
        find_prev_action.setShortcut(QKeySequence.StandardKey.FindPrevious)
        find_prev_action.triggered.connect(self.previous_result)
        self.tree_view.addAction(find_prev_action)
    
    def setup_with_model(self, source_model) -> None:
        """Setup with source model."""
        self.proxy_model.setSourceModel(source_model)
        self.tree_view.setModel(self.proxy_model)
    
    def get_search_bar(self) -> SearchBar:
        """Get search bar widget."""
        return self.search_bar
    
    def _on_search_changed(self, query: str) -> None:
        """Handle search query change."""
        # Delay search to avoid too frequent updates
        self.search_timer.stop()
        self.search_timer.start(300)  # 300ms delay
        
        # Update highlighter immediately
        criteria = self.search_bar.get_criteria()
        self.highlighter.set_search_query(query, criteria.case_sensitive)
    
    def _on_criteria_changed(self, criteria: SearchCriteria) -> None:
        """Handle search criteria change."""
        self.proxy_model.set_criteria(criteria)
        self.filterChanged.emit(criteria)
        
        # Update search results
        self._update_search_results()
    
    def _on_search_cleared(self) -> None:
        """Handle search cleared."""
        self.highlighter.clear_highlighting()
        self.navigator.set_results([])
        self.resultsNavigated.emit(0, 0)
    
    def _perform_search(self) -> None:
        """Perform the actual search."""
        query = self.search_bar.search_input.text()
        if not query:
            return
        
        self.searchStarted.emit(query)
        self._update_search_results()
    
    def _update_search_results(self) -> None:
        """Update search results for navigation."""
        # Get visible matching items
        results = []
        model = self.tree_view.model()
        
        if model:
            # Collect all visible matching indices
            self._collect_matching_indices(QModelIndex(), results)
        
        # Update navigator
        self.navigator.set_results(results)
        
        # Emit completion signal
        self.searchCompleted.emit(len(results))
        
        # Navigate to first result if available
        if results:
            self.navigator.first_result()
            self.resultsNavigated.emit(*self.navigator.get_current_position())
    
    def _collect_matching_indices(self, parent: QModelIndex, results: List[QModelIndex]) -> None:
        """Recursively collect matching indices."""
        model = self.tree_view.model()
        if not model:
            return
        
        row_count = model.rowCount(parent)
        for row in range(row_count):
            index = model.index(row, 0, parent)
            if index.isValid():
                # Check if this index is visible (passes filter)
                if self._index_matches_search(index):
                    results.append(index)
                
                # Recurse into children
                self._collect_matching_indices(index, results)
    
    def _index_matches_search(self, index: QModelIndex) -> bool:
        """Check if index matches current search."""
        model = self.tree_view.model()
        if not model or not index.isValid():
            return False
        
        # Get element data
        if hasattr(model, 'sourceModel'):
            # Proxy model - get source index
            source_index = model.mapToSource(index)
            source_model = model.sourceModel()
            element_id = source_model.data(source_index, Qt.ItemDataRole.UserRole)
            element = source_model.get_element_by_id(element_id) if element_id else None
        else:
            # Direct model
            element_id = model.data(index, Qt.ItemDataRole.UserRole)
            element = model.get_element_by_id(element_id) if element_id else None
        
        if not element:
            return False
        
        # Check if element matches current criteria
        criteria = self.search_bar.get_criteria()
        return criteria.matches_element(element)
    
    def focus_search(self) -> None:
        """Focus the search input."""
        self.search_bar.search_input.setFocus()
        self.search_bar.search_input.selectAll()
    
    def next_result(self) -> None:
        """Navigate to next search result."""
        if self.navigator.next_result():
            self.resultsNavigated.emit(*self.navigator.get_current_position())
    
    def previous_result(self) -> None:
        """Navigate to previous search result."""
        if self.navigator.previous_result():
            self.resultsNavigated.emit(*self.navigator.get_current_position())
    
    def clear_search(self) -> None:
        """Clear current search."""
        self.search_bar.clear_search()
    
    def get_result_count(self) -> int:
        """Get number of search results."""
        return len(self.navigator.results)
    
    def get_current_result_position(self) -> tuple:
        """Get current result position (current, total)."""
        return self.navigator.get_current_position()