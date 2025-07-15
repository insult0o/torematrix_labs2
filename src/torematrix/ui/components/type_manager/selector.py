"""Enhanced Type Selector Widget

Advanced type selection widget with search, filtering, and preview capabilities.
Built for Agent 2 UI Components implementation.
"""

from typing import List, Optional, Dict, Any, Callable
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLineEdit, 
    QPushButton, QLabel, QFrame, QListWidget, QListWidgetItem,
    QCompleter, QCheckBox, QButtonGroup, QRadioButton, QGroupBox,
    QScrollArea, QSizePolicy, QToolTip
)
from PyQt6.QtCore import Qt, pyqtSignal, QStringListModel, QTimer, QSize
from PyQt6.QtGui import QFont, QIcon, QPixmap, QPalette

from torematrix.core.models.types import TypeRegistry, TypeDefinition, get_type_registry


class TypePreviewCard(QFrame):
    """Compact preview card for a type"""
    
    clicked = pyqtSignal(str)  # type_id
    
    def __init__(self, type_def: TypeDefinition, parent=None):
        super().__init__(parent)
        
        self.type_def = type_def
        self.setup_ui()
        self.apply_styles()
    
    def setup_ui(self):
        """Setup the preview card UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)
        
        # Icon and name row
        header_layout = QHBoxLayout()
        
        # Type icon (placeholder for now)
        icon_label = QLabel("📄")  # Default icon
        if hasattr(self.type_def, 'icon') and self.type_def.icon:
            icon_label.setText(self.type_def.icon)
        icon_label.setFont(QFont("", 14))
        header_layout.addWidget(icon_label)
        
        # Type name
        name_label = QLabel(self.type_def.name)
        name_label.setFont(QFont("", 10, QFont.Weight.Bold))
        header_layout.addWidget(name_label)
        
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Category
        category_label = QLabel(self.type_def.category.title())
        category_label.setFont(QFont("", 8))
        category_label.setStyleSheet("color: #666;")
        layout.addWidget(category_label)
        
        # Description (truncated)
        if self.type_def.description:
            desc = self.type_def.description
            if len(desc) > 60:
                desc = desc[:60] + "..."
            desc_label = QLabel(desc)
            desc_label.setFont(QFont("", 8))
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("color: #777;")
            layout.addWidget(desc_label)
    
    def apply_styles(self):
        """Apply card styling"""
        self.setFrameStyle(QFrame.Shape.Box)
        self.setFixedSize(180, 80)
        self.setStyleSheet("""
            QFrame {
                border: 1px solid #ddd;
                border-radius: 6px;
                background: white;
                padding: 4px;
            }
            QFrame:hover {
                border-color: #0078d4;
                background: #f8f9fa;
            }
        """)
        
        # Set tooltip
        tooltip = f"{self.type_def.name}\n{self.type_def.description}\nCategory: {self.type_def.category}"
        if self.type_def.tags:
            tooltip += f"\nTags: {', '.join(self.type_def.tags)}"
        self.setToolTip(tooltip)
    
    def mousePressEvent(self, event):
        """Handle mouse click"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.type_def.type_id)
        super().mousePressEvent(event)


class TypeFilterWidget(QWidget):
    """Advanced filtering widget for types"""
    
    filter_changed = pyqtSignal()
    
    def __init__(self, registry: TypeRegistry, parent=None):
        super().__init__(parent)
        
        self.registry = registry
        self.setup_ui()
        self.connect_signals()
    
    def setup_ui(self):
        """Setup filter UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Category filter
        category_group = QGroupBox("Categories")
        category_layout = QVBoxLayout(category_group)
        
        self.category_checkboxes = {}
        categories = self.get_available_categories()
        
        for category in categories:
            checkbox = QCheckBox(category.title())
            checkbox.setChecked(True)  # Start with all selected
            self.category_checkboxes[category] = checkbox
            category_layout.addWidget(checkbox)
        
        layout.addWidget(category_group)
        
        # Type properties filter
        props_group = QGroupBox("Type Properties")
        props_layout = QVBoxLayout(props_group)
        
        # Custom types only
        self.custom_only = QCheckBox("Custom Types Only")
        props_layout.addWidget(self.custom_only)
        
        # Has children
        self.has_children = QCheckBox("Has Child Types")
        props_layout.addWidget(self.has_children)
        
        # Has parents
        self.has_parents = QCheckBox("Has Parent Types")
        props_layout.addWidget(self.has_parents)
        
        layout.addWidget(props_group)
        
        # Quick filters
        quick_group = QGroupBox("Quick Filters")
        quick_layout = QVBoxLayout(quick_group)
        
        self.recently_used = QCheckBox("Recently Used")
        quick_layout.addWidget(self.recently_used)
        
        self.frequently_used = QCheckBox("Frequently Used")
        quick_layout.addWidget(self.frequently_used)
        
        layout.addWidget(quick_group)
        
        # Reset button
        reset_btn = QPushButton("Reset Filters")
        reset_btn.clicked.connect(self.reset_filters)
        layout.addWidget(reset_btn)
        
        layout.addStretch()
    
    def get_available_categories(self) -> List[str]:
        """Get all available categories"""
        categories = set()
        for type_def in self.registry.list_types().values():
            categories.add(type_def.category)
        return sorted(categories)
    
    def connect_signals(self):
        """Connect filter signals"""
        # Connect all checkboxes to filter change
        for checkbox in self.category_checkboxes.values():
            checkbox.toggled.connect(self.filter_changed.emit)
        
        self.custom_only.toggled.connect(self.filter_changed.emit)
        self.has_children.toggled.connect(self.filter_changed.emit)
        self.has_parents.toggled.connect(self.filter_changed.emit)
        self.recently_used.toggled.connect(self.filter_changed.emit)
        self.frequently_used.toggled.connect(self.filter_changed.emit)
    
    def get_filter_criteria(self) -> Dict[str, Any]:
        """Get current filter criteria"""
        return {
            'categories': [cat for cat, cb in self.category_checkboxes.items() if cb.isChecked()],
            'custom_only': self.custom_only.isChecked(),
            'has_children': self.has_children.isChecked() if self.has_children.isChecked() else None,
            'has_parents': self.has_parents.isChecked() if self.has_parents.isChecked() else None,
            'recently_used': self.recently_used.isChecked(),
            'frequently_used': self.frequently_used.isChecked()
        }
    
    def reset_filters(self):
        """Reset all filters to default"""
        # Reset category checkboxes
        for checkbox in self.category_checkboxes.values():
            checkbox.setChecked(True)
        
        # Reset property filters
        self.custom_only.setChecked(False)
        self.has_children.setChecked(False)
        self.has_parents.setChecked(False)
        self.recently_used.setChecked(False)
        self.frequently_used.setChecked(False)
        
        self.filter_changed.emit()


class TypeSelectorWidget(QWidget):
    """Enhanced type selector with search, filtering, and preview"""
    
    # Signals
    type_selected = pyqtSignal(str)  # type_id
    type_hover = pyqtSignal(str)     # type_id for preview
    selection_cleared = pyqtSignal()
    
    def __init__(self, registry: TypeRegistry = None, parent=None):
        super().__init__(parent)
        
        self.registry = registry or get_type_registry()
        self.current_type_id: Optional[str] = None
        self.search_results: List[TypeDefinition] = []
        self.display_mode = "list"  # "list" or "grid"
        
        self.setup_ui()
        self.connect_signals()
        self.populate_types()
    
    def setup_ui(self):
        """Setup the selector UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Search and controls header
        header_layout = QVBoxLayout()
        
        # Search input with autocomplete
        search_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search types by name, category, or description...")
        self.setup_autocomplete()
        search_layout.addWidget(self.search_input)
        
        # Clear search button
        clear_btn = QPushButton("✕")
        clear_btn.setFixedSize(24, 24)
        clear_btn.clicked.connect(self.clear_search)
        search_layout.addWidget(clear_btn)
        
        header_layout.addLayout(search_layout)
        
        # View controls
        controls_layout = QHBoxLayout()
        
        # Display mode toggle
        self.list_btn = QPushButton("📋")
        self.list_btn.setCheckable(True)
        self.list_btn.setChecked(True)
        self.list_btn.setToolTip("List View")
        controls_layout.addWidget(self.list_btn)
        
        self.grid_btn = QPushButton("⊞")
        self.grid_btn.setCheckable(True)
        self.grid_btn.setToolTip("Grid View")
        controls_layout.addWidget(self.grid_btn)
        
        # Button group for exclusive selection
        self.view_group = QButtonGroup()
        self.view_group.addButton(self.list_btn, 0)
        self.view_group.addButton(self.grid_btn, 1)
        
        controls_layout.addStretch()
        
        # Filter toggle
        self.filter_btn = QPushButton("🔍 Filters")
        self.filter_btn.setCheckable(True)
        controls_layout.addWidget(self.filter_btn)
        
        header_layout.addLayout(controls_layout)
        layout.addLayout(header_layout)
        
        # Main content area
        content_layout = QHBoxLayout()
        
        # Filter panel (initially hidden)
        self.filter_widget = TypeFilterWidget(self.registry)
        self.filter_widget.setVisible(False)
        self.filter_widget.setFixedWidth(200)
        content_layout.addWidget(self.filter_widget)
        
        # Types display area
        self.types_scroll = QScrollArea()
        self.types_widget = QWidget()
        
        # Start with list layout
        self.types_layout = QVBoxLayout(self.types_widget)
        self.types_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.types_scroll.setWidget(self.types_widget)
        self.types_scroll.setWidgetResizable(True)
        content_layout.addWidget(self.types_scroll)
        
        layout.addLayout(content_layout)
        
        # Status/info bar
        self.info_label = QLabel("0 types loaded")
        self.info_label.setStyleSheet("color: #666; font-style: italic; padding: 4px;")
        layout.addWidget(self.info_label)
    
    def setup_autocomplete(self):
        """Setup autocomplete for search"""
        terms = set()
        
        # Collect searchable terms
        for type_def in self.registry.list_types().values():
            terms.add(type_def.name)
            terms.add(type_def.category)
            terms.update(type_def.tags)
            if type_def.description:
                # Add description words
                terms.update(type_def.description.split())
        
        # Setup completer
        completer = QCompleter(sorted(terms))
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.search_input.setCompleter(completer)
    
    def connect_signals(self):
        """Connect UI signals"""
        # Search with debouncing
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.perform_search)
        self.search_input.textChanged.connect(lambda: self.search_timer.start(300))
        
        # View mode buttons
        self.view_group.buttonClicked.connect(self.change_view_mode)
        
        # Filter toggle
        self.filter_btn.toggled.connect(self.filter_widget.setVisible)
        self.filter_widget.filter_changed.connect(self.apply_filters)
    
    def populate_types(self):
        """Populate with all types initially"""
        all_types = list(self.registry.list_types().values())
        self.search_results = all_types
        self.update_display()
    
    def perform_search(self):
        """Perform search based on current input"""
        query = self.search_input.text().strip().lower()
        all_types = list(self.registry.list_types().values())
        
        if not query:
            self.search_results = all_types
        else:
            # Search in name, category, description, and tags
            self.search_results = []
            for type_def in all_types:
                if self.matches_search_query(type_def, query):
                    self.search_results.append(type_def)
        
        self.apply_filters()
    
    def matches_search_query(self, type_def: TypeDefinition, query: str) -> bool:
        """Check if type matches search query"""
        searchable_text = " ".join([
            type_def.name.lower(),
            type_def.category.lower(),
            type_def.description.lower() if type_def.description else "",
            " ".join(type_def.tags).lower()
        ])
        
        # Support multiple search terms
        query_terms = query.split()
        return all(term in searchable_text for term in query_terms)
    
    def apply_filters(self):
        """Apply current filters to search results"""
        if not hasattr(self.filter_widget, 'get_filter_criteria'):
            self.update_display()
            return
        
        criteria = self.filter_widget.get_filter_criteria()
        filtered_results = []
        
        for type_def in self.search_results:
            if self.matches_filter_criteria(type_def, criteria):
                filtered_results.append(type_def)
        
        self.filtered_results = filtered_results
        self.update_display(filtered_results)
    
    def matches_filter_criteria(self, type_def: TypeDefinition, criteria: Dict[str, Any]) -> bool:
        """Check if type matches filter criteria"""
        # Category filter
        if criteria['categories'] and type_def.category not in criteria['categories']:
            return False
        
        # Custom types only
        if criteria['custom_only'] and not type_def.is_custom:
            return False
        
        # Has children filter
        if criteria['has_children'] and not type_def.child_types:
            return False
        
        # Has parents filter  
        if criteria['has_parents'] and not type_def.parent_types:
            return False
        
        # Note: recently_used and frequently_used would need usage tracking
        
        return True
    
    def update_display(self, types: List[TypeDefinition] = None):
        """Update the types display"""
        if types is None:
            types = self.search_results
        
        # Clear existing items
        for i in reversed(range(self.types_layout.count())):
            child = self.types_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        # Update info
        count = len(types)
        self.info_label.setText(f"{count} type{'s' if count != 1 else ''} found")
        
        if self.display_mode == "list":
            self.update_list_display(types)
        else:
            self.update_grid_display(types)
    
    def update_list_display(self, types: List[TypeDefinition]):
        """Update list view display"""
        for type_def in types:
            item_widget = self.create_list_item(type_def)
            self.types_layout.addWidget(item_widget)
    
    def update_grid_display(self, types: List[TypeDefinition]):
        """Update grid view display"""
        # Convert to grid layout
        self.clear_layout()
        
        from PyQt6.QtWidgets import QGridLayout
        grid_layout = QGridLayout(self.types_widget)
        grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        cols = 2  # Two columns for grid
        for i, type_def in enumerate(types):
            row = i // cols
            col = i % cols
            
            card = TypePreviewCard(type_def)
            card.clicked.connect(self.on_type_selected)
            grid_layout.addWidget(card, row, col)
        
        self.types_layout = grid_layout
    
    def create_list_item(self, type_def: TypeDefinition) -> QWidget:
        """Create a list item widget for a type"""
        item = QFrame()
        item.setFrameStyle(QFrame.Shape.Box)
        item.setStyleSheet("""
            QFrame {
                border: 1px solid #eee;
                border-radius: 4px;
                background: white;
                margin: 1px;
                padding: 8px;
            }
            QFrame:hover {
                border-color: #0078d4;
                background: #f8f9fa;
            }
        """)
        
        layout = QHBoxLayout(item)
        layout.setContentsMargins(8, 4, 8, 4)
        
        # Icon
        icon_label = QLabel("📄")
        if hasattr(type_def, 'icon') and type_def.icon:
            icon_label.setText(type_def.icon)
        icon_label.setFont(QFont("", 12))
        layout.addWidget(icon_label)
        
        # Type info
        info_layout = QVBoxLayout()
        
        # Name and category
        name_label = QLabel(f"{type_def.name}")
        name_label.setFont(QFont("", 10, QFont.Weight.Bold))
        info_layout.addWidget(name_label)
        
        category_label = QLabel(type_def.category.title())
        category_label.setFont(QFont("", 8))
        category_label.setStyleSheet("color: #666;")
        info_layout.addWidget(category_label)
        
        layout.addLayout(info_layout)
        layout.addStretch()
        
        # Custom badge
        if type_def.is_custom:
            custom_badge = QLabel("Custom")
            custom_badge.setStyleSheet("""
                background: #17a2b8;
                color: white;
                padding: 2px 6px;
                border-radius: 10px;
                font-size: 8px;
            """)
            layout.addWidget(custom_badge)
        
        # Store type_id for selection
        item.type_id = type_def.type_id
        item.mousePressEvent = lambda event: self.on_type_selected(type_def.type_id)
        
        return item
    
    def clear_layout(self):
        """Clear the current layout"""
        # Remove all widgets from current layout
        for i in reversed(range(self.types_layout.count())):
            child = self.types_layout.itemAt(i)
            if child.widget():
                child.widget().setParent(None)
        
        # If it's a grid layout, replace with VBox
        if isinstance(self.types_layout, QVBoxLayout):
            pass  # Already VBox
        else:
            # Replace with VBox layout
            self.types_layout.setParent(None)
            self.types_layout = QVBoxLayout(self.types_widget)
            self.types_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    
    def change_view_mode(self, button):
        """Change display mode"""
        if button == self.list_btn:
            self.display_mode = "list"
            self.clear_layout()
        else:
            self.display_mode = "grid"
        
        # Re-apply current display
        current_types = getattr(self, 'filtered_results', self.search_results)
        self.update_display(current_types)
    
    def on_type_selected(self, type_id: str):
        """Handle type selection"""
        self.current_type_id = type_id
        self.type_selected.emit(type_id)
        
        # Update selection visual state
        # This could be enhanced to highlight selected item
    
    def clear_search(self):
        """Clear search input"""
        self.search_input.clear()
        self.perform_search()
    
    def get_selected_type_id(self) -> Optional[str]:
        """Get currently selected type ID"""
        return self.current_type_id
    
    def set_selected_type(self, type_id: str):
        """Programmatically set selected type"""
        if type_id in [t.type_id for t in self.registry.list_types().values()]:
            self.on_type_selected(type_id)
    
    def refresh(self):
        """Refresh the type list"""
        self.populate_types()
        self.setup_autocomplete()  # Refresh autocomplete data