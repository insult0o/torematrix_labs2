"""
Advanced Sorting Manager

Provides comprehensive sorting capabilities for hierarchical element lists
with multiple sort criteria, custom sort orders, and performance optimization.
"""

import logging
from typing import List, Dict, Any, Optional, Callable, Union, Tuple
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QWidget, QComboBox, QHBoxLayout, QLabel, QPushButton, QMenu
from PyQt6.QtGui import QIcon, QAction
import operator

logger = logging.getLogger(__name__)


class SortOrder(Enum):
    """Sort order options"""
    ASCENDING = "asc"
    DESCENDING = "desc"


class SortField(Enum):
    """Available sort fields"""
    NAME = "name"
    TYPE = "type"
    SIZE = "size"
    CREATED = "created"
    MODIFIED = "modified"
    POSITION = "position"
    LEVEL = "level"
    CHILD_COUNT = "child_count"
    CUSTOM = "custom"


@dataclass
class SortCriterion:
    """Single sort criterion"""
    field: SortField
    order: SortOrder
    custom_key_func: Optional[Callable[[Any], Any]] = None
    display_name: Optional[str] = None
    priority: int = 0  # Higher priority = applied first
    
    def __post_init__(self):
        if self.display_name is None:
            self.display_name = self.field.value.replace('_', ' ').title()


@dataclass
class SortPreset:
    """Predefined sort configuration"""
    name: str
    description: str
    criteria: List[SortCriterion]
    icon: Optional[str] = None


@dataclass
class SortResult:
    """Result of a sort operation"""
    sorted_items: List[Any]
    sort_criteria: List[SortCriterion]
    execution_time: float
    item_count: int
    is_stable: bool = True


class SortKeyExtractor:
    """Extracts sort keys from element data"""
    
    @staticmethod
    def extract_key(item: Any, field: SortField, custom_func: Optional[Callable] = None) -> Any:
        """
        Extract sort key from item for given field
        
        Args:
            item: Item to extract key from
            field: Sort field to extract
            custom_func: Custom extraction function
            
        Returns:
            Sort key value
        """
        if custom_func:
            return custom_func(item)
        
        # Handle different item types
        if hasattr(item, 'element_data'):
            data = item.element_data
        elif isinstance(item, dict):
            data = item
        else:
            # Fallback to string representation
            return str(item)
        
        # Extract based on field type
        if field == SortField.NAME:
            return data.get('name', '').lower()
        elif field == SortField.TYPE:
            return data.get('type', '').lower()
        elif field == SortField.SIZE:
            return data.get('size', 0)
        elif field == SortField.CREATED:
            created = data.get('created')
            return SortKeyExtractor._parse_datetime(created) if created else datetime.min
        elif field == SortField.MODIFIED:
            modified = data.get('modified')
            return SortKeyExtractor._parse_datetime(modified) if modified else datetime.min
        elif field == SortField.POSITION:
            return data.get('position', 0)
        elif field == SortField.LEVEL:
            return data.get('level', 0)
        elif field == SortField.CHILD_COUNT:
            children = data.get('children', [])
            return len(children) if isinstance(children, list) else 0
        else:
            return str(data.get(field.value, ''))
    
    @staticmethod
    def _parse_datetime(dt_value: Union[str, datetime, int, float]) -> datetime:
        """Parse datetime value from various formats"""
        if isinstance(dt_value, datetime):
            return dt_value
        elif isinstance(dt_value, str):
            try:
                return datetime.fromisoformat(dt_value.replace('Z', '+00:00'))
            except ValueError:
                return datetime.min
        elif isinstance(dt_value, (int, float)):
            try:
                return datetime.fromtimestamp(dt_value)
            except (ValueError, OSError):
                return datetime.min
        else:
            return datetime.min


class AdvancedSortingManager(QObject):
    """
    Advanced sorting manager for hierarchical element lists
    
    Provides multi-criteria sorting, sort presets, performance optimization,
    and integration with tree view components.
    """
    
    # Signals
    sort_applied = pyqtSignal(object)  # SortResult
    sort_criteria_changed = pyqtSignal(list)  # List[SortCriterion]
    preset_applied = pyqtSignal(str)  # preset_name
    sort_started = pyqtSignal(int)  # item_count
    sort_progress = pyqtSignal(int)  # progress_percentage
    
    def __init__(self, parent: Optional[QObject] = None):
        """
        Initialize advanced sorting manager
        
        Args:
            parent: Parent QObject
        """
        super().__init__(parent)
        
        # Configuration
        self.enable_stable_sort = True
        self.enable_async_sort = True
        self.max_sort_items = 10000  # Switch to async for larger datasets
        
        # State
        self._current_criteria: List[SortCriterion] = []
        self._sort_presets: Dict[str, SortPreset] = {}
        self._custom_extractors: Dict[str, Callable] = {}
        self._sort_cache: Dict[str, Any] = {}
        self._last_sort_result: Optional[SortResult] = None
        
        # Performance tracking
        self._sort_timer = QTimer()
        self._sort_timer.setSingleShot(True)
        self._sort_timer.timeout.connect(self._perform_deferred_sort)
        
        # Initialize default presets and extractors
        self._initialize_default_presets()
        self._initialize_default_extractors()
        
        logger.info("AdvancedSortingManager initialized")
    
    def add_sort_criterion(self, criterion: SortCriterion) -> None:
        """
        Add a sort criterion to the current criteria list
        
        Args:
            criterion: Sort criterion to add
        """
        # Remove existing criterion for same field
        self._current_criteria = [c for c in self._current_criteria if c.field != criterion.field]
        
        # Add new criterion
        self._current_criteria.append(criterion)
        
        # Sort by priority (higher priority first)
        self._current_criteria.sort(key=lambda c: c.priority, reverse=True)
        
        logger.debug(f"Added sort criterion: {criterion.field.value} {criterion.order.value}")
        self.sort_criteria_changed.emit(self._current_criteria)
    
    def remove_sort_criterion(self, field: SortField) -> None:
        """
        Remove sort criterion for specified field
        
        Args:
            field: Sort field to remove
        """
        original_count = len(self._current_criteria)
        self._current_criteria = [c for c in self._current_criteria if c.field != field]
        
        if len(self._current_criteria) < original_count:
            logger.debug(f"Removed sort criterion: {field.value}")
            self.sort_criteria_changed.emit(self._current_criteria)
    
    def set_sort_criteria(self, criteria: List[SortCriterion]) -> None:
        """
        Set complete sort criteria list
        
        Args:
            criteria: List of sort criteria
        """
        self._current_criteria = criteria.copy()
        
        # Sort by priority
        self._current_criteria.sort(key=lambda c: c.priority, reverse=True)
        
        logger.debug(f"Set sort criteria: {len(criteria)} criteria")
        self.sort_criteria_changed.emit(self._current_criteria)
    
    def clear_sort_criteria(self) -> None:
        """Clear all sort criteria"""
        self._current_criteria.clear()
        logger.debug("Cleared all sort criteria")
        self.sort_criteria_changed.emit(self._current_criteria)
    
    def apply_preset(self, preset_name: str) -> bool:
        """
        Apply a sort preset
        
        Args:
            preset_name: Name of preset to apply
            
        Returns:
            True if preset was applied successfully
        """
        if preset_name not in self._sort_presets:
            logger.warning(f"Sort preset not found: {preset_name}")
            return False
        
        preset = self._sort_presets[preset_name]
        self.set_sort_criteria(preset.criteria)
        
        logger.info(f"Applied sort preset: {preset_name}")
        self.preset_applied.emit(preset_name)
        return True
    
    def register_preset(self, preset: SortPreset) -> None:
        """
        Register a new sort preset
        
        Args:
            preset: Sort preset to register
        """
        self._sort_presets[preset.name] = preset
        logger.debug(f"Registered sort preset: {preset.name}")
    
    def register_custom_extractor(self, name: str, extractor: Callable[[Any], Any]) -> None:
        """
        Register a custom sort key extractor
        
        Args:
            name: Name for the extractor
            extractor: Function to extract sort key from item
        """
        self._custom_extractors[name] = extractor
        logger.debug(f"Registered custom extractor: {name}")
    
    def sort_items(self, items: List[Any], criteria: Optional[List[SortCriterion]] = None) -> SortResult:
        """
        Sort items using current or provided criteria
        
        Args:
            items: Items to sort
            criteria: Optional criteria to use (uses current if None)
            
        Returns:
            SortResult with sorted items and metadata
        """
        start_time = datetime.now()
        
        # Use provided criteria or current
        sort_criteria = criteria or self._current_criteria
        
        if not sort_criteria:
            # No sorting criteria - return items as-is
            return SortResult(
                sorted_items=items.copy(),
                sort_criteria=[],
                execution_time=0.0,
                item_count=len(items),
                is_stable=True
            )
        
        logger.debug(f"Sorting {len(items)} items with {len(sort_criteria)} criteria")
        self.sort_started.emit(len(items))
        
        try:
            # Create sort key function
            def multi_key_func(item):
                keys = []
                for criterion in sort_criteria:
                    key = SortKeyExtractor.extract_key(item, criterion.field, criterion.custom_key_func)
                    
                    # Handle None values
                    if key is None:
                        key = ""
                    
                    # Reverse key for descending order
                    if criterion.order == SortOrder.DESCENDING:
                        if isinstance(key, str):
                            # For strings, use negative comparison
                            key = ReverseString(key)
                        elif isinstance(key, (int, float)):
                            key = -key
                        elif isinstance(key, datetime):
                            key = datetime.max - key
                    
                    keys.append(key)
                
                return tuple(keys)
            
            # Perform sort
            if self.enable_stable_sort:
                sorted_items = sorted(items, key=multi_key_func)
            else:
                sorted_items = items.copy()
                sorted_items.sort(key=multi_key_func)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            result = SortResult(
                sorted_items=sorted_items,
                sort_criteria=sort_criteria.copy(),
                execution_time=execution_time,
                item_count=len(items),
                is_stable=self.enable_stable_sort
            )
            
            self._last_sort_result = result
            
            logger.debug(f"Sort completed in {execution_time:.3f}s")
            self.sort_applied.emit(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Sort operation failed: {e}")
            # Return original items on error
            return SortResult(
                sorted_items=items.copy(),
                sort_criteria=sort_criteria.copy(),
                execution_time=0.0,
                item_count=len(items),
                is_stable=False
            )
    
    def get_available_presets(self) -> List[SortPreset]:
        """
        Get list of available sort presets
        
        Returns:
            List of available sort presets
        """
        return list(self._sort_presets.values())
    
    def get_current_criteria(self) -> List[SortCriterion]:
        """
        Get current sort criteria
        
        Returns:
            List of current sort criteria
        """
        return self._current_criteria.copy()
    
    def get_last_sort_result(self) -> Optional[SortResult]:
        """
        Get the last sort result
        
        Returns:
            Last sort result or None
        """
        return self._last_sort_result
    
    def _initialize_default_presets(self) -> None:
        """Initialize default sort presets"""
        
        # Name ascending
        self.register_preset(SortPreset(
            name="name_asc",
            description="Sort by name (A-Z)",
            criteria=[SortCriterion(SortField.NAME, SortOrder.ASCENDING, priority=100)],
            icon="sort-alpha-asc"
        ))
        
        # Name descending
        self.register_preset(SortPreset(
            name="name_desc",
            description="Sort by name (Z-A)",
            criteria=[SortCriterion(SortField.NAME, SortOrder.DESCENDING, priority=100)],
            icon="sort-alpha-desc"
        ))
        
        # Type, then name
        self.register_preset(SortPreset(
            name="type_name",
            description="Sort by type, then name",
            criteria=[
                SortCriterion(SortField.TYPE, SortOrder.ASCENDING, priority=100),
                SortCriterion(SortField.NAME, SortOrder.ASCENDING, priority=90)
            ],
            icon="sort-type"
        ))
        
        # Date modified (newest first)
        self.register_preset(SortPreset(
            name="modified_desc",
            description="Sort by modified date (newest first)",
            criteria=[SortCriterion(SortField.MODIFIED, SortOrder.DESCENDING, priority=100)],
            icon="sort-time-desc"
        ))
        
        # Size (largest first)
        self.register_preset(SortPreset(
            name="size_desc",
            description="Sort by size (largest first)",
            criteria=[SortCriterion(SortField.SIZE, SortOrder.DESCENDING, priority=100)],
            icon="sort-size-desc"
        ))
        
        # Hierarchical (level, then position)
        self.register_preset(SortPreset(
            name="hierarchical",
            description="Sort hierarchically (level, then position)",
            criteria=[
                SortCriterion(SortField.LEVEL, SortOrder.ASCENDING, priority=100),
                SortCriterion(SortField.POSITION, SortOrder.ASCENDING, priority=90)
            ],
            icon="sort-hierarchy"
        ))
    
    def _initialize_default_extractors(self) -> None:
        """Initialize default custom extractors"""
        
        # Element path depth
        def path_depth_extractor(item):
            if hasattr(item, 'element_data'):
                path = item.element_data.get('path', '')
                return path.count('/') if path else 0
            return 0
        
        self.register_custom_extractor("path_depth", path_depth_extractor)
        
        # Has children
        def has_children_extractor(item):
            if hasattr(item, 'element_data'):
                children = item.element_data.get('children', [])
                return len(children) > 0
            return False
        
        self.register_custom_extractor("has_children", has_children_extractor)
    
    def _perform_deferred_sort(self):
        """Perform deferred sort operation (for async sorting)"""
        # Implementation for async sorting if needed
        pass


class ReverseString:
    """Wrapper for string to enable reverse sorting"""
    
    def __init__(self, string: str):
        self.string = string
    
    def __lt__(self, other):
        if isinstance(other, ReverseString):
            return self.string > other.string
        return self.string > str(other)
    
    def __eq__(self, other):
        if isinstance(other, ReverseString):
            return self.string == other.string
        return self.string == str(other)
    
    def __str__(self):
        return self.string


class SortingControlWidget(QWidget):
    """
    UI widget for sorting controls
    
    Provides dropdown menus and buttons for selecting sort criteria and presets.
    """
    
    # Signals
    sort_preset_selected = pyqtSignal(str)  # preset_name
    custom_sort_requested = pyqtSignal()
    sort_cleared = pyqtSignal()
    
    def __init__(self, sorting_manager: AdvancedSortingManager, parent: Optional[QWidget] = None):
        """
        Initialize sorting control widget
        
        Args:
            sorting_manager: Associated sorting manager
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.sorting_manager = sorting_manager
        self._setup_ui()
        self._setup_connections()
    
    def _setup_ui(self):
        """Setup the user interface"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        
        # Sort label
        sort_label = QLabel("Sort:")
        layout.addWidget(sort_label)
        
        # Preset dropdown
        self.preset_combo = QComboBox()
        self.preset_combo.setMinimumWidth(150)
        self._populate_presets()
        layout.addWidget(self.preset_combo)
        
        # Custom sort button
        self.custom_button = QPushButton("Custom...")
        self.custom_button.setToolTip("Configure custom sort criteria")
        layout.addWidget(self.custom_button)
        
        # Clear sort button
        self.clear_button = QPushButton("Clear")
        self.clear_button.setToolTip("Clear all sort criteria")
        layout.addWidget(self.clear_button)
        
        layout.addStretch()
    
    def _setup_connections(self):
        """Setup signal connections"""
        self.preset_combo.currentTextChanged.connect(self._on_preset_selected)
        self.custom_button.clicked.connect(self.custom_sort_requested.emit)
        self.clear_button.clicked.connect(self.sort_cleared.emit)
    
    def _populate_presets(self):
        """Populate the preset dropdown"""
        self.preset_combo.clear()
        self.preset_combo.addItem("No Sort", None)
        
        for preset in self.sorting_manager.get_available_presets():
            self.preset_combo.addItem(preset.description, preset.name)
    
    def _on_preset_selected(self, text: str):
        """Handle preset selection"""
        preset_name = self.preset_combo.currentData()
        if preset_name:
            self.sort_preset_selected.emit(preset_name)