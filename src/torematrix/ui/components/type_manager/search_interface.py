"""Type Search Interface

Advanced search interface for finding and filtering types
with multiple criteria, saved searches, and quick filters.
"""

from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QLineEdit, QComboBox, QCheckBox, QGroupBox,
    QScrollArea, QFrame, QListWidget, QListWidgetItem,
    QSplitter, QTabWidget, QSpinBox, QDateEdit, QSlider,
    QButtonGroup, QRadioButton, QTextEdit, QCompleter
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QStringListModel, QTimer, QDate,
    QSortFilterProxyModel, QAbstractListModel, QModelIndex, QVariant
)
from PyQt6.QtGui import QFont, QIcon, QStandardItemModel, QStandardItem

from torematrix.core.models.types import TypeRegistry, TypeDefinition, get_type_registry
from torematrix.core.models.types.metadata import get_metadata_manager


@dataclass
class SearchCriteria:
    """Search criteria for type filtering"""
    
    text_query: str = ""
    categories: List[str] = None
    tags: List[str] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    has_children: Optional[bool] = None
    has_parents: Optional[bool] = None
    is_custom: Optional[bool] = None
    property_filters: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.categories is None:
            self.categories = []
        if self.tags is None:
            self.tags = []
        if self.property_filters is None:
            self.property_filters = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'text_query': self.text_query,
            'categories': self.categories,
            'tags': self.tags,
            'created_after': self.created_after.isoformat() if self.created_after else None,
            'created_before': self.created_before.isoformat() if self.created_before else None,
            'has_children': self.has_children,
            'has_parents': self.has_parents,
            'is_custom': self.is_custom,
            'property_filters': self.property_filters
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SearchCriteria':
        """Create from dictionary"""
        criteria = cls()
        criteria.text_query = data.get('text_query', '')
        criteria.categories = data.get('categories', [])
        criteria.tags = data.get('tags', [])
        
        if data.get('created_after'):
            criteria.created_after = datetime.fromisoformat(data['created_after'])
        if data.get('created_before'):
            criteria.created_before = datetime.fromisoformat(data['created_before'])
        
        criteria.has_children = data.get('has_children')
        criteria.has_parents = data.get('has_parents')
        criteria.is_custom = data.get('is_custom')
        criteria.property_filters = data.get('property_filters', {})
        
        return criteria


class QuickFilterWidget(QFrame):
    """Widget for quick filter buttons"""
    
    filter_applied = pyqtSignal(SearchCriteria)
    
    def __init__(self, registry: TypeRegistry, parent=None):
        super().__init__(parent)
        
        self.registry = registry
        self.setup_ui()
    
    def setup_ui(self):
        """Setup user interface"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        
        # Quick filter buttons
        filters = [
            ("All Types", self.show_all),
            ("Text Types", lambda: self.filter_by_category("text")),
            ("Media Types", lambda: self.filter_by_category("media")),
            ("Structure", lambda: self.filter_by_category("structure")),
            ("Custom Types", self.filter_custom),
            ("Root Types", self.filter_root),
            ("Leaf Types", self.filter_leaf),
            ("Recent", self.filter_recent)
        ]
        
        for label, handler in filters:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.clicked.connect(handler)
            btn.setStyleSheet("""
                QPushButton {
                    padding: 4px 8px;
                    border: 1px solid #ccc;
                    background: white;
                    border-radius: 3px;
                }
                QPushButton:checked {
                    background: #e3f2fd;
                    border-color: #0078d4;
                }
                QPushButton:hover {
                    background: #f0f0f0;
                }
            """)
            layout.addWidget(btn)
        
        layout.addStretch()
    
    def show_all(self):
        """Show all types"""
        self.filter_applied.emit(SearchCriteria())
    
    def filter_by_category(self, category: str):
        """Filter by category"""
        criteria = SearchCriteria(categories=[category])
        self.filter_applied.emit(criteria)
    
    def filter_custom(self):
        """Filter custom types"""
        criteria = SearchCriteria(is_custom=True)
        self.filter_applied.emit(criteria)
    
    def filter_root(self):
        """Filter root types (no parents)"""
        criteria = SearchCriteria(has_parents=False)
        self.filter_applied.emit(criteria)
    
    def filter_leaf(self):
        """Filter leaf types (no children)"""
        criteria = SearchCriteria(has_children=False)
        self.filter_applied.emit(criteria)
    
    def filter_recent(self):
        """Filter recent types (last 7 days)"""
        week_ago = datetime.now() - timedelta(days=7)
        criteria = SearchCriteria(created_after=week_ago)
        self.filter_applied.emit(criteria)


class AdvancedSearchWidget(QWidget):
    """Widget for advanced search criteria"""
    
    search_updated = pyqtSignal(SearchCriteria)
    
    def __init__(self, registry: TypeRegistry, parent=None):
        super().__init__(parent)
        
        self.registry = registry
        self.setup_ui()
        self.setup_connections()
    
    def setup_ui(self):
        """Setup user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Text search
        text_group = QGroupBox("Text Search")
        text_layout = QVBoxLayout(text_group)
        
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("Search in name, description, properties...")
        text_layout.addWidget(self.text_input)
        
        # Add autocomplete
        self.setup_autocomplete()
        
        layout.addWidget(text_group)
        
        # Categories
        category_group = QGroupBox("Categories")
        category_layout = QGridLayout(category_group)
        
        self.category_checkboxes = {}
        categories = self.get_available_categories()
        
        for i, category in enumerate(categories):
            checkbox = QCheckBox(category.title())
            self.category_checkboxes[category] = checkbox
            row = i // 3
            col = i % 3
            category_layout.addWidget(checkbox, row, col)
        
        layout.addWidget(category_group)
        
        # Tags
        tag_group = QGroupBox("Tags")
        tag_layout = QVBoxLayout(tag_group)
        
        self.tag_input = QLineEdit()
        self.tag_input.setPlaceholderText("Enter tags separated by commas")
        tag_layout.addWidget(self.tag_input)
        
        layout.addWidget(tag_group)
        
        # Properties
        prop_group = QGroupBox("Properties")
        prop_layout = QGridLayout(prop_group)
        
        # Hierarchy properties
        row = 0
        
        # Has children
        children_layout = QHBoxLayout()
        children_layout.addWidget(QLabel("Has Children:"))
        self.children_any = QRadioButton("Any")
        self.children_yes = QRadioButton("Yes")
        self.children_no = QRadioButton("No")
        self.children_any.setChecked(True)
        
        children_group = QButtonGroup()
        children_group.addButton(self.children_any, 0)
        children_group.addButton(self.children_yes, 1)
        children_group.addButton(self.children_no, 2)
        
        children_layout.addWidget(self.children_any)
        children_layout.addWidget(self.children_yes)
        children_layout.addWidget(self.children_no)
        children_layout.addStretch()
        
        prop_layout.addLayout(children_layout, row, 0, 1, 2)
        row += 1
        
        # Has parents
        parents_layout = QHBoxLayout()
        parents_layout.addWidget(QLabel("Has Parents:"))
        self.parents_any = QRadioButton("Any")
        self.parents_yes = QRadioButton("Yes")
        self.parents_no = QRadioButton("No")
        self.parents_any.setChecked(True)
        
        parents_group = QButtonGroup()
        parents_group.addButton(self.parents_any, 0)
        parents_group.addButton(self.parents_yes, 1)
        parents_group.addButton(self.parents_no, 2)
        
        parents_layout.addWidget(self.parents_any)
        parents_layout.addWidget(self.parents_yes)
        parents_layout.addWidget(self.parents_no)
        parents_layout.addStretch()
        
        prop_layout.addLayout(parents_layout, row, 0, 1, 2)
        row += 1
        
        # Is custom
        custom_layout = QHBoxLayout()
        custom_layout.addWidget(QLabel("Custom Type:"))
        self.custom_any = QRadioButton("Any")
        self.custom_yes = QRadioButton("Yes")
        self.custom_no = QRadioButton("No")
        self.custom_any.setChecked(True)
        
        custom_group = QButtonGroup()
        custom_group.addButton(self.custom_any, 0)
        custom_group.addButton(self.custom_yes, 1)
        custom_group.addButton(self.custom_no, 2)
        
        custom_layout.addWidget(self.custom_any)
        custom_layout.addWidget(self.custom_yes)
        custom_layout.addWidget(self.custom_no)
        custom_layout.addStretch()
        
        prop_layout.addLayout(custom_layout, row, 0, 1, 2)
        
        layout.addWidget(prop_group)
        
        # Date range
        date_group = QGroupBox("Creation Date")
        date_layout = QGridLayout(date_group)
        
        date_layout.addWidget(QLabel("Created After:"), 0, 0)
        self.date_after = QDateEdit()
        self.date_after.setDate(QDate.currentDate().addDays(-30))
        self.date_after.setCalendarPopup(True)
        self.date_after.setEnabled(False)
        date_layout.addWidget(self.date_after, 0, 1)
        
        self.date_after_enabled = QCheckBox("Enable")
        self.date_after_enabled.toggled.connect(self.date_after.setEnabled)
        date_layout.addWidget(self.date_after_enabled, 0, 2)
        
        date_layout.addWidget(QLabel("Created Before:"), 1, 0)
        self.date_before = QDateEdit()
        self.date_before.setDate(QDate.currentDate())
        self.date_before.setCalendarPopup(True)
        self.date_before.setEnabled(False)
        date_layout.addWidget(self.date_before, 1, 1)
        
        self.date_before_enabled = QCheckBox("Enable")
        self.date_before_enabled.toggled.connect(self.date_before.setEnabled)
        date_layout.addWidget(self.date_before_enabled, 1, 2)
        
        layout.addWidget(date_group)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self.perform_search)
        button_layout.addWidget(self.search_btn)
        
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_criteria)
        button_layout.addWidget(self.clear_btn)
        
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
    
    def setup_autocomplete(self):
        """Setup autocomplete for text search"""
        # Get all searchable terms
        terms = set()
        
        for type_def in self.registry.list_types():
            terms.add(type_def.name)
            terms.add(type_def.category)
            terms.update(type_def.tags)
            terms.update(type_def.properties.keys())
        
        # Setup completer
        completer = QCompleter(sorted(terms))
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.text_input.setCompleter(completer)
    
    def setup_connections(self):
        """Setup signal connections"""
        # Auto-search on text change (debounced)
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.perform_search)
        
        self.text_input.textChanged.connect(lambda: self.search_timer.start(300))
        
        # Auto-search on category change
        for checkbox in self.category_checkboxes.values():
            checkbox.toggled.connect(self.perform_search)
    
    def get_available_categories(self) -> List[str]:
        """Get available categories"""
        categories = set()
        for type_def in self.registry.list_types():
            categories.add(type_def.category)
        return sorted(categories)
    
    def build_criteria(self) -> SearchCriteria:
        """Build search criteria from UI"""
        criteria = SearchCriteria()
        
        # Text query
        criteria.text_query = self.text_input.text().strip()
        
        # Categories
        criteria.categories = [
            category for category, checkbox in self.category_checkboxes.items()
            if checkbox.isChecked()
        ]
        
        # Tags
        tag_text = self.tag_input.text().strip()
        if tag_text:
            criteria.tags = [tag.strip() for tag in tag_text.split(',') if tag.strip()]
        
        # Has children
        if self.children_yes.isChecked():
            criteria.has_children = True
        elif self.children_no.isChecked():
            criteria.has_children = False
        
        # Has parents
        if self.parents_yes.isChecked():
            criteria.has_parents = True
        elif self.parents_no.isChecked():
            criteria.has_parents = False
        
        # Is custom
        if self.custom_yes.isChecked():
            criteria.is_custom = True
        elif self.custom_no.isChecked():
            criteria.is_custom = False
        
        # Date range
        if self.date_after_enabled.isChecked():
            date = self.date_after.date().toPython()
            criteria.created_after = datetime.combine(date, datetime.min.time())
        
        if self.date_before_enabled.isChecked():
            date = self.date_before.date().toPython()
            criteria.created_before = datetime.combine(date, datetime.max.time())
        
        return criteria
    
    def perform_search(self):
        """Perform search with current criteria"""
        criteria = self.build_criteria()
        self.search_updated.emit(criteria)
    
    def clear_criteria(self):
        """Clear all search criteria"""
        self.text_input.clear()
        self.tag_input.clear()
        
        # Uncheck all categories
        for checkbox in self.category_checkboxes.values():
            checkbox.setChecked(False)
        
        # Reset radio buttons
        self.children_any.setChecked(True)
        self.parents_any.setChecked(True)
        self.custom_any.setChecked(True)
        
        # Reset dates
        self.date_after_enabled.setChecked(False)
        self.date_before_enabled.setChecked(False)
        
        self.perform_search()
    
    def set_criteria(self, criteria: SearchCriteria):
        """Set search criteria in UI"""
        self.text_input.setText(criteria.text_query)
        
        # Set categories
        for category, checkbox in self.category_checkboxes.items():
            checkbox.setChecked(category in criteria.categories)
        
        # Set tags
        if criteria.tags:
            self.tag_input.setText(', '.join(criteria.tags))
        
        # Set properties
        if criteria.has_children is True:
            self.children_yes.setChecked(True)
        elif criteria.has_children is False:
            self.children_no.setChecked(True)
        else:
            self.children_any.setChecked(True)
        
        if criteria.has_parents is True:
            self.parents_yes.setChecked(True)
        elif criteria.has_parents is False:
            self.parents_no.setChecked(True)
        else:
            self.parents_any.setChecked(True)
        
        if criteria.is_custom is True:
            self.custom_yes.setChecked(True)
        elif criteria.is_custom is False:
            self.custom_no.setChecked(True)
        else:
            self.custom_any.setChecked(True)
        
        # Set dates
        if criteria.created_after:
            self.date_after.setDate(QDate.fromString(criteria.created_after.date().isoformat(), Qt.DateFormat.ISODate))
            self.date_after_enabled.setChecked(True)
        
        if criteria.created_before:
            self.date_before.setDate(QDate.fromString(criteria.created_before.date().isoformat(), Qt.DateFormat.ISODate))
            self.date_before_enabled.setChecked(True)


class SavedSearchesWidget(QWidget):
    """Widget for managing saved searches"""
    
    search_loaded = pyqtSignal(SearchCriteria)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.saved_searches: Dict[str, SearchCriteria] = {}
        self.setup_ui()
        self.load_saved_searches()
    
    def setup_ui(self):
        """Setup user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Saved Searches"))
        header_layout.addStretch()
        
        self.save_btn = QPushButton("Save Current")
        self.save_btn.clicked.connect(self.save_current_search)
        header_layout.addWidget(self.save_btn)
        
        layout.addLayout(header_layout)
        
        # Search list
        self.search_list = QListWidget()
        self.search_list.itemDoubleClicked.connect(self.load_search)
        layout.addWidget(self.search_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.load_btn = QPushButton("Load")
        self.load_btn.clicked.connect(self.load_selected_search)
        button_layout.addWidget(self.load_btn)
        
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self.delete_selected_search)
        button_layout.addWidget(self.delete_btn)
        
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
    
    def save_current_search(self):
        """Save current search"""
        # This would be connected to the main search interface
        pass
    
    def load_search(self, item: QListWidgetItem):
        """Load search from list item"""
        search_name = item.text()
        if search_name in self.saved_searches:
            criteria = self.saved_searches[search_name]
            self.search_loaded.emit(criteria)
    
    def load_selected_search(self):
        """Load currently selected search"""
        current_item = self.search_list.currentItem()
        if current_item:
            self.load_search(current_item)
    
    def delete_selected_search(self):
        """Delete selected search"""
        current_item = self.search_list.currentItem()
        if current_item:
            search_name = current_item.text()
            if search_name in self.saved_searches:
                del self.saved_searches[search_name]
                self.search_list.takeItem(self.search_list.row(current_item))
                self.save_searches_to_file()
    
    def add_saved_search(self, name: str, criteria: SearchCriteria):
        """Add a saved search"""
        self.saved_searches[name] = criteria
        
        item = QListWidgetItem(name)
        item.setToolTip(f"Categories: {', '.join(criteria.categories) if criteria.categories else 'Any'}")
        self.search_list.addItem(item)
        
        self.save_searches_to_file()
    
    def load_saved_searches(self):
        """Load saved searches from file"""
        # Placeholder for file loading
        pass
    
    def save_searches_to_file(self):
        """Save searches to file"""
        # Placeholder for file saving
        pass


class TypeSearchInterface(QWidget):
    """Complete type search interface"""
    
    # Signals
    search_results_changed = pyqtSignal(list)  # List of matching type IDs
    type_selected = pyqtSignal(str)  # type_id
    
    def __init__(self, registry: TypeRegistry = None, parent=None):
        super().__init__(parent)
        
        self.registry = registry or get_type_registry()
        self.current_criteria: Optional[SearchCriteria] = None
        self.search_results: List[str] = []
        
        self.setup_ui()
        self.connect_signals()
        
        # Perform initial search
        self.perform_search(SearchCriteria())
    
    def setup_ui(self):
        """Setup user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Quick filters
        self.quick_filters = QuickFilterWidget(self.registry)
        layout.addWidget(self.quick_filters)
        
        # Main content in splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side - search controls
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Search tabs
        search_tabs = QTabWidget()
        
        # Advanced search tab
        self.advanced_search = AdvancedSearchWidget(self.registry)
        search_tabs.addTab(self.advanced_search, "Advanced")
        
        # Saved searches tab
        self.saved_searches = SavedSearchesWidget()
        search_tabs.addTab(self.saved_searches, "Saved")
        
        left_layout.addWidget(search_tabs)
        splitter.addWidget(left_widget)
        
        # Right side - results
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Results header
        results_header = QHBoxLayout()
        results_header.addWidget(QLabel("Search Results"))
        
        self.results_count = QLabel("0 types found")
        self.results_count.setStyleSheet("color: #666; font-style: italic;")
        results_header.addWidget(self.results_count)
        results_header.addStretch()
        
        right_layout.addLayout(results_header)
        
        # Results list
        self.results_list = QListWidget()
        self.results_list.itemDoubleClicked.connect(self.on_result_selected)
        right_layout.addWidget(self.results_list)
        
        splitter.addWidget(right_widget)
        
        # Set splitter proportions
        splitter.setSizes([300, 200])
        layout.addWidget(splitter)
    
    def connect_signals(self):
        """Connect signals"""
        self.quick_filters.filter_applied.connect(self.perform_search)
        self.advanced_search.search_updated.connect(self.perform_search)
        self.saved_searches.search_loaded.connect(self.load_search_criteria)
    
    def perform_search(self, criteria: SearchCriteria):
        """Perform search with given criteria"""
        self.current_criteria = criteria
        
        # Get all types
        all_types = self.registry.list_types()
        
        # Filter types based on criteria
        matching_types = []
        
        for type_def in all_types:
            if self.matches_criteria(type_def, criteria):
                matching_types.append(type_def.type_id)
        
        self.search_results = matching_types
        self.update_results_display()
        self.search_results_changed.emit(self.search_results)
    
    def matches_criteria(self, type_def: TypeDefinition, criteria: SearchCriteria) -> bool:
        """Check if type matches search criteria"""
        # Text query
        if criteria.text_query:
            query = criteria.text_query.lower()
            searchable_text = ' '.join([
                type_def.name.lower(),
                type_def.description.lower(),
                type_def.category.lower(),
                ' '.join(type_def.tags).lower(),
                ' '.join(type_def.properties.keys()).lower()
            ])
            
            if query not in searchable_text:
                return False
        
        # Categories
        if criteria.categories and type_def.category not in criteria.categories:
            return False
        
        # Tags
        if criteria.tags:
            type_tags = set(type_def.tags)
            required_tags = set(criteria.tags)
            if not required_tags.issubset(type_tags):
                return False
        
        # Has children
        if criteria.has_children is not None:
            has_children = bool(type_def.child_types)
            if has_children != criteria.has_children:
                return False
        
        # Has parents
        if criteria.has_parents is not None:
            has_parents = bool(type_def.parent_types)
            if has_parents != criteria.has_parents:
                return False
        
        # Is custom
        if criteria.is_custom is not None:
            if type_def.is_custom != criteria.is_custom:
                return False
        
        # Date range
        if criteria.created_after and type_def.created_at < criteria.created_after:
            return False
        
        if criteria.created_before and type_def.created_at > criteria.created_before:
            return False
        
        return True
    
    def update_results_display(self):
        """Update results display"""
        self.results_list.clear()
        
        # Update count
        count = len(self.search_results)
        self.results_count.setText(f"{count} type{'s' if count != 1 else ''} found")
        
        # Add results to list
        for type_id in self.search_results:
            try:
                type_def = self.registry.get_type(type_id)
                
                item = QListWidgetItem()
                item.setText(type_def.name)
                item.setData(Qt.ItemDataRole.UserRole, type_id)
                
                # Set tooltip
                tooltip = f"{type_def.name}\n{type_def.description}\nCategory: {type_def.category}"
                if type_def.tags:
                    tooltip += f"\nTags: {', '.join(type_def.tags)}"
                item.setToolTip(tooltip)
                
                self.results_list.addItem(item)
                
            except Exception as e:
                print(f"Error loading type {type_id}: {e}")
    
    def on_result_selected(self, item: QListWidgetItem):
        """Handle result selection"""
        type_id = item.data(Qt.ItemDataRole.UserRole)
        if type_id:
            self.type_selected.emit(type_id)
    
    def load_search_criteria(self, criteria: SearchCriteria):
        """Load search criteria into interface"""
        self.advanced_search.set_criteria(criteria)
        self.perform_search(criteria)
    
    def get_current_criteria(self) -> Optional[SearchCriteria]:
        """Get current search criteria"""
        return self.current_criteria
    
    def get_search_results(self) -> List[str]:
        """Get current search results"""
        return self.search_results.copy()
    
    def save_current_search(self, name: str):
        """Save current search with given name"""
        if self.current_criteria:
            self.saved_searches.add_saved_search(name, self.current_criteria)
    
    def clear_search(self):
        """Clear current search"""
        self.advanced_search.clear_criteria()
        self.perform_search(SearchCriteria())
