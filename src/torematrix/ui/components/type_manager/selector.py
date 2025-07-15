"""Type Selector Widget

Enhanced type selector with icons, search, and filtering capabilities.
Provides intuitive type selection with visual feedback and performance optimization.
"""

from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass
from PyQt6.QtWidgets import (
    QComboBox, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel,
    QCompleter, QListWidget, QListWidgetItem, QPushButton, QFrame,
    QScrollArea, QGridLayout, QToolButton, QMenu, QAction, QCheckBox
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QStringListModel, QTimer, QSize, QRect,
    QAbstractListModel, QModelIndex, QVariant
)
from PyQt6.QtGui import QIcon, QPixmap, QFont, QPainter, QColor, QPen

from torematrix.core.models.types import get_type_registry, TypeRegistry, TypeDefinition
from torematrix.core.models.types.metadata import TypeIcon, get_metadata_manager


@dataclass
class TypeSelectionData:
    """Data for type selection events"""
    type_id: str
    type_def: TypeDefinition
    previous_type_id: Optional[str] = None
    user_initiated: bool = True


class TypeListModel(QAbstractListModel):
    """Custom model for type list with icons and metadata"""
    
    def __init__(self, registry: TypeRegistry, parent=None):
        super().__init__(parent)
        self.registry = registry
        self.metadata_manager = get_metadata_manager()
        self.types: List[TypeDefinition] = []
        self.filtered_types: List[TypeDefinition] = []
        self.current_filter: Dict[str, Any] = {}
        self.search_text: str = ""
        
        # Load types
        self.refresh_types()
    
    def refresh_types(self):
        """Refresh type list from registry"""
        self.beginResetModel()
        self.types = list(self.registry.list_types().values())
        self.filtered_types = self.types.copy()
        self.endResetModel()
    
    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self.filtered_types)
    
    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> QVariant:
        if not index.isValid() or index.row() >= len(self.filtered_types):
            return QVariant()
        
        type_def = self.filtered_types[index.row()]
        
        if role == Qt.ItemDataRole.DisplayRole:
            return QVariant(type_def.name)
        elif role == Qt.ItemDataRole.ToolTipRole:
            tooltip = f"<b>{type_def.name}</b><br>"
            tooltip += f"ID: {type_def.type_id}<br>"
            tooltip += f"Category: {type_def.category}<br>"
            tooltip += f"Description: {type_def.description}"
            return QVariant(tooltip)
        elif role == Qt.ItemDataRole.DecorationRole:
            # Get icon for type
            icon_info = self.metadata_manager.get_type_icon(type_def.type_id)
            if icon_info and icon_info.icon_path:
                return QVariant(QIcon(icon_info.icon_path))
            else:
                # Default icon based on category
                return QVariant(self._get_default_icon(type_def.category))
        elif role == Qt.ItemDataRole.UserRole:
            return QVariant(type_def.type_id)
        elif role == Qt.ItemDataRole.UserRole + 1:
            return QVariant(type_def)
        
        return QVariant()
    
    def _get_default_icon(self, category: str) -> QIcon:
        """Get default icon for category"""
        # Create simple colored icon based on category
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        
        # Color map for categories
        color_map = {
            'content': QColor(52, 152, 219),    # Blue
            'layout': QColor(46, 204, 113),     # Green
            'media': QColor(155, 89, 182),      # Purple
            'interactive': QColor(241, 196, 15), # Yellow
            'metadata': QColor(231, 76, 60),    # Red
            'structure': QColor(149, 165, 166)  # Gray
        }
        
        color = color_map.get(category, QColor(149, 165, 166))
        painter.setBrush(color)
        painter.setPen(QPen(color.darker(120), 1))
        painter.drawEllipse(2, 2, 12, 12)
        painter.end()
        
        return QIcon(pixmap)
    
    def apply_filter(self, filter_criteria: Dict[str, Any], search_text: str = ""):
        """Apply filtering to type list"""
        self.beginResetModel()
        self.current_filter = filter_criteria
        self.search_text = search_text.lower()
        
        self.filtered_types = []
        for type_def in self.types:
            if self._matches_filter(type_def):
                self.filtered_types.append(type_def)
        
        self.endResetModel()
    
    def _matches_filter(self, type_def: TypeDefinition) -> bool:
        """Check if type matches current filter"""
        # Search text filter
        if self.search_text:
            search_fields = [
                type_def.name.lower(),
                type_def.type_id.lower(),
                type_def.description.lower(),
                type_def.category.lower()
            ]
            search_fields.extend([tag.lower() for tag in type_def.tags])
            
            if not any(self.search_text in field for field in search_fields):
                return False
        
        # Category filter
        if 'category' in self.current_filter:
            if type_def.category != self.current_filter['category']:
                return False
        
        # Tags filter
        if 'tags' in self.current_filter:
            required_tags = set(self.current_filter['tags'])
            type_tags = set(type_def.tags)
            if not required_tags.issubset(type_tags):
                return False
        
        # Custom filter function
        if 'filter_func' in self.current_filter:
            filter_func = self.current_filter['filter_func']
            if not filter_func(type_def):
                return False
        
        return True


class TypeSelectorWidget(QComboBox):
    """Enhanced type selector with icons, search, and filtering"""
    
    # Signals
    type_selected = pyqtSignal(TypeSelectionData)
    type_changed = pyqtSignal(str, str)  # old_type_id, new_type_id
    type_double_clicked = pyqtSignal(str)  # type_id
    filter_requested = pyqtSignal(dict)  # filter_criteria
    
    def __init__(self, registry: TypeRegistry = None, parent=None):
        super().__init__(parent)
        
        self.registry = registry or get_type_registry()
        self.metadata_manager = get_metadata_manager()
        
        # State
        self.current_type_id: Optional[str] = None
        self.recent_types: List[str] = []
        self.max_recent_types = 10
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._perform_search)
        
        # UI setup
        self.setup_ui()
        self.setup_model()
        self.setup_connections()
        self.load_types()
    
    def setup_ui(self):
        """Setup user interface"""
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.setMaxVisibleItems(20)
        self.setMinimumWidth(200)
        
        # Enable completer for search
        self.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.completer().setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        
        # Styling
        self.setStyleSheet("""
            QComboBox {
                padding: 4px 8px;
                border: 1px solid #ccc;
                border-radius: 4px;
                background: white;
            }
            QComboBox:hover {
                border-color: #0078d4;
            }
            QComboBox:focus {
                border-color: #0078d4;
                outline: none;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid #666;
                margin-right: 2px;
            }
        """)
    
    def setup_model(self):
        """Setup type list model"""
        self.model = TypeListModel(self.registry, self)
        self.setModel(self.model)
    
    def setup_connections(self):
        """Setup signal connections"""
        self.currentIndexChanged.connect(self._on_selection_changed)
        self.lineEdit().textChanged.connect(self._on_search_text_changed)
        
        # Registry change notifications
        self.registry.add_change_listener(self._on_registry_changed)
    
    def load_types(self):
        """Load types into selector"""
        self.model.refresh_types()
        
        # Update completer
        type_names = [type_def.name for type_def in self.model.types]
        self.completer().setModel(QStringListModel(type_names))
    
    def set_current_type(self, type_id: str) -> bool:
        """Set current selected type
        
        Args:
            type_id: Type ID to select
            
        Returns:
            True if type was found and selected
        """
        if not type_id:
            self.setCurrentIndex(-1)
            self.current_type_id = None
            return True
        
        # Find type in model
        for i in range(self.model.rowCount()):
            index = self.model.index(i, 0)
            model_type_id = self.model.data(index, Qt.ItemDataRole.UserRole)
            if model_type_id == type_id:
                old_type_id = self.current_type_id
                self.setCurrentIndex(i)
                self.current_type_id = type_id
                
                # Add to recent types
                self.add_recent_type(type_id)
                
                # Emit signal if type actually changed
                if old_type_id != type_id:
                    self.type_changed.emit(old_type_id or "", type_id)
                
                return True
        
        return False
    
    def get_selected_type(self) -> Optional[str]:
        """Get currently selected type ID"""
        return self.current_type_id
    
    def get_selected_type_definition(self) -> Optional[TypeDefinition]:
        """Get currently selected type definition"""
        if not self.current_type_id:
            return None
        
        try:
            return self.registry.get_type(self.current_type_id)
        except:
            return None
    
    def filter_types(self, criteria: Dict[str, Any]) -> None:
        """Apply filter to type list
        
        Args:
            criteria: Filter criteria dictionary
                - category: Filter by category
                - tags: Filter by tags (list)
                - filter_func: Custom filter function
        """
        search_text = self.lineEdit().text() if self.isEditable() else ""
        self.model.apply_filter(criteria, search_text)
        self.filter_requested.emit(criteria)
    
    def clear_filter(self) -> None:
        """Clear all filters"""
        self.filter_types({})
    
    def add_recent_type(self, type_id: str) -> None:
        """Add type to recent types list"""
        if type_id in self.recent_types:
            self.recent_types.remove(type_id)
        
        self.recent_types.insert(0, type_id)
        
        # Trim to max recent types
        if len(self.recent_types) > self.max_recent_types:
            self.recent_types = self.recent_types[:self.max_recent_types]
    
    def get_recent_types(self) -> List[str]:
        """Get list of recently used types"""
        return self.recent_types.copy()
    
    def set_search_text(self, text: str) -> None:
        """Set search text"""
        if self.isEditable():
            self.lineEdit().setText(text)
    
    def get_search_text(self) -> str:
        """Get current search text"""
        if self.isEditable():
            return self.lineEdit().text()
        return ""
    
    def refresh(self) -> None:
        """Refresh type list from registry"""
        current_type = self.current_type_id
        self.load_types()
        
        # Restore selection if possible
        if current_type:
            self.set_current_type(current_type)
    
    # Event handlers
    
    def _on_selection_changed(self, index: int):
        """Handle selection change"""
        if index < 0:
            self.current_type_id = None
            return
        
        model_index = self.model.index(index, 0)
        type_id = self.model.data(model_index, Qt.ItemDataRole.UserRole)
        type_def = self.model.data(model_index, Qt.ItemDataRole.UserRole + 1)
        
        if type_id and type_id != self.current_type_id:
            old_type_id = self.current_type_id
            self.current_type_id = type_id
            
            # Create selection data
            selection_data = TypeSelectionData(
                type_id=type_id,
                type_def=type_def,
                previous_type_id=old_type_id,
                user_initiated=True
            )
            
            # Emit signals
            self.type_selected.emit(selection_data)
            self.type_changed.emit(old_type_id or "", type_id)
            
            # Add to recent types
            self.add_recent_type(type_id)
    
    def _on_search_text_changed(self, text: str):
        """Handle search text change with debouncing"""
        self.search_timer.stop()
        self.search_timer.start(300)  # 300ms debounce
    
    def _perform_search(self):
        """Perform search with current text"""
        search_text = self.lineEdit().text() if self.isEditable() else ""
        current_filter = getattr(self.model, 'current_filter', {})
        self.model.apply_filter(current_filter, search_text)
    
    def _on_registry_changed(self, action: str, type_id: str, type_def: TypeDefinition):
        """Handle registry changes"""
        # Refresh model when registry changes
        self.load_types()
        
        # If current type was deleted, clear selection
        if action == "unregister" and type_id == self.current_type_id:
            self.setCurrentIndex(-1)
            self.current_type_id = None
    
    # Context menu
    
    def contextMenuEvent(self, event):
        """Show context menu"""
        menu = QMenu(self)
        
        # Recent types submenu
        if self.recent_types:
            recent_menu = menu.addMenu("Recent Types")
            for type_id in self.recent_types[:5]:  # Show top 5
                try:
                    type_def = self.registry.get_type(type_id)
                    action = recent_menu.addAction(type_def.name)
                    action.triggered.connect(lambda checked, tid=type_id: self.set_current_type(tid))
                except:
                    continue
        
        menu.addSeparator()
        
        # Filter actions
        filter_menu = menu.addMenu("Filter by Category")
        categories = set(type_def.category for type_def in self.model.types)
        for category in sorted(categories):
            action = filter_menu.addAction(category.title())
            action.triggered.connect(lambda checked, cat=category: self.filter_types({'category': cat}))
        
        # Clear filter
        clear_action = menu.addAction("Clear Filter")
        clear_action.triggered.connect(self.clear_filter)
        
        menu.addSeparator()
        
        # Refresh
        refresh_action = menu.addAction("Refresh")
        refresh_action.triggered.connect(self.refresh)
        
        menu.exec(event.globalPos())


class TypeSelectorPanel(QWidget):
    """Type selector panel with additional controls"""
    
    type_selected = pyqtSignal(TypeSelectionData)
    type_changed = pyqtSignal(str, str)
    
    def __init__(self, registry: TypeRegistry = None, parent=None):
        super().__init__(parent)
        
        self.registry = registry or get_type_registry()
        self.setup_ui()
        self.setup_connections()
    
    def setup_ui(self):
        """Setup user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header
        header_layout = QHBoxLayout()
        header_label = QLabel("Element Type:")
        header_label.setFont(QFont("", 9, QFont.Weight.Bold))
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        
        # Filter button
        self.filter_btn = QToolButton()
        self.filter_btn.setText("🔧")
        self.filter_btn.setToolTip("Filter Types")
        self.filter_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        header_layout.addWidget(self.filter_btn)
        
        layout.addLayout(header_layout)
        
        # Type selector
        self.type_selector = TypeSelectorWidget(self.registry, self)
        layout.addWidget(self.type_selector)
        
        # Type info
        self.info_label = QLabel()
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("color: #666; font-size: 11px; padding: 4px;")
        layout.addWidget(self.info_label)
        
        # Setup filter menu
        self.setup_filter_menu()
    
    def setup_filter_menu(self):
        """Setup filter menu"""
        menu = QMenu(self)
        
        # Category filters
        categories = set()
        for type_def in self.registry.list_types().values():
            categories.add(type_def.category)
        
        category_menu = menu.addMenu("Category")
        for category in sorted(categories):
            action = category_menu.addAction(category.title())
            action.setCheckable(True)
            action.triggered.connect(
                lambda checked, cat=category: self._apply_category_filter(cat, checked)
            )
        
        menu.addSeparator()
        
        # Clear filters
        clear_action = menu.addAction("Clear All Filters")
        clear_action.triggered.connect(self.type_selector.clear_filter)
        
        self.filter_btn.setMenu(menu)
    
    def setup_connections(self):
        """Setup signal connections"""
        self.type_selector.type_selected.connect(self.type_selected.emit)
        self.type_selector.type_changed.connect(self.type_changed.emit)
        self.type_selector.type_selected.connect(self._update_info)
    
    def set_current_type(self, type_id: str) -> bool:
        """Set current type"""
        return self.type_selector.set_current_type(type_id)
    
    def get_selected_type(self) -> Optional[str]:
        """Get selected type"""
        return self.type_selector.get_selected_type()
    
    def _apply_category_filter(self, category: str, enabled: bool):
        """Apply category filter"""
        if enabled:
            self.type_selector.filter_types({'category': category})
        else:
            self.type_selector.clear_filter()
    
    def _update_info(self, selection_data: TypeSelectionData):
        """Update type information display"""
        type_def = selection_data.type_def
        if type_def:
            info_text = f"<b>{type_def.category.title()}</b> • {type_def.description}"
            if type_def.tags:
                info_text += f"<br>Tags: {', '.join(type_def.tags)}"
            self.info_label.setText(info_text)
        else:
            self.info_label.setText("")