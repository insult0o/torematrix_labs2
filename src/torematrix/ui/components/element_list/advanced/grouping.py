"""
Element Grouping Manager

Provides advanced grouping capabilities for hierarchical element lists
with support for multiple grouping criteria, visual grouping, and performance optimization.
"""

import logging
from typing import List, Dict, Any, Optional, Callable, Union, Set, Tuple
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict, OrderedDict
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class GroupingStrategy(Enum):
    """Grouping strategy options"""
    FLAT = "flat"               # Flatten groups into single level
    HIERARCHICAL = "hierarchical"  # Maintain hierarchy within groups
    NESTED = "nested"           # Create nested groups


class GroupingField(Enum):
    """Available grouping fields"""
    TYPE = "type"
    CATEGORY = "category"
    STATUS = "status"
    DATE_CREATED = "date_created"
    DATE_MODIFIED = "date_modified"
    SIZE_RANGE = "size_range"
    LEVEL = "level"
    PARENT = "parent"
    CUSTOM = "custom"


@dataclass
class GroupingCriterion:
    """Single grouping criterion"""
    field: GroupingField
    display_name: str
    custom_grouper: Optional[Callable[[Any], str]] = None
    sort_groups: bool = True
    sort_items_within_groups: bool = True
    group_order: List[str] = field(default_factory=list)  # Custom group order
    
    def __post_init__(self):
        if not self.display_name:
            self.display_name = self.field.value.replace('_', ' ').title()


@dataclass
class ElementGroup:
    """Single group of elements"""
    group_key: str
    display_name: str
    items: List[Any] = field(default_factory=list)
    item_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    icon: Optional[str] = None
    color: Optional[str] = None
    is_expanded: bool = True
    subgroups: Dict[str, 'ElementGroup'] = field(default_factory=dict)
    
    def __post_init__(self):
        self.item_count = len(self.items)
    
    def add_item(self, item: Any):
        """Add item to this group"""
        self.items.append(item)
        self.item_count = len(self.items)
    
    def add_subgroup(self, subgroup: 'ElementGroup'):
        """Add subgroup to this group"""
        self.subgroups[subgroup.group_key] = subgroup
    
    def get_all_items(self) -> List[Any]:
        """Get all items including those in subgroups"""
        all_items = self.items.copy()
        for subgroup in self.subgroups.values():
            all_items.extend(subgroup.get_all_items())
        return all_items
    
    def get_total_count(self) -> int:
        """Get total count including subgroups"""
        total = len(self.items)
        for subgroup in self.subgroups.values():
            total += subgroup.get_total_count()
        return total


@dataclass
class GroupingResult:
    """Result of a grouping operation"""
    groups: OrderedDict[str, ElementGroup]
    grouping_criteria: List[GroupingCriterion]
    total_items: int
    total_groups: int
    execution_time: float
    strategy: GroupingStrategy
    ungrouped_items: List[Any] = field(default_factory=list)
    
    def get_all_items(self) -> List[Any]:
        """Get all items from all groups"""
        all_items = []
        for group in self.groups.values():
            all_items.extend(group.get_all_items())
        all_items.extend(self.ungrouped_items)
        return all_items


class GroupKeyExtractor:
    """Extracts grouping keys from element data"""
    
    @staticmethod
    def extract_key(item: Any, field: GroupingField, custom_func: Optional[Callable] = None) -> str:
        """
        Extract grouping key from item for given field
        
        Args:
            item: Item to extract key from
            field: Grouping field to extract
            custom_func: Custom extraction function
            
        Returns:
            Grouping key as string
        """
        if custom_func:
            result = custom_func(item)
            return str(result) if result is not None else "Unknown"
        
        # Handle different item types
        if hasattr(item, 'element_data'):
            data = item.element_data
        elif isinstance(item, dict):
            data = item
        else:
            return "Unknown"
        
        # Extract based on field type
        if field == GroupingField.TYPE:
            return data.get('type', 'Unknown Type')
        elif field == GroupingField.CATEGORY:
            return data.get('category', 'Uncategorized')
        elif field == GroupingField.STATUS:
            return data.get('status', 'Unknown Status')
        elif field == GroupingField.DATE_CREATED:
            return GroupKeyExtractor._extract_date_group(data.get('created'))
        elif field == GroupingField.DATE_MODIFIED:
            return GroupKeyExtractor._extract_date_group(data.get('modified'))
        elif field == GroupingField.SIZE_RANGE:
            return GroupKeyExtractor._extract_size_range(data.get('size', 0))
        elif field == GroupingField.LEVEL:
            level = data.get('level', 0)
            return f"Level {level}"
        elif field == GroupingField.PARENT:
            parent = data.get('parent_id')
            return f"Parent: {parent}" if parent else "No Parent"
        else:
            return data.get(field.value, 'Unknown')
    
    @staticmethod
    def _extract_date_group(date_value: Any) -> str:
        """Extract date-based grouping key"""
        if not date_value:
            return "Unknown Date"
        
        try:
            if isinstance(date_value, str):
                dt = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
            elif isinstance(date_value, datetime):
                dt = date_value
            elif isinstance(date_value, (int, float)):
                dt = datetime.fromtimestamp(date_value)
            else:
                return "Unknown Date"
            
            # Group by year-month
            return dt.strftime("%Y-%m")
            
        except (ValueError, OSError):
            return "Invalid Date"
    
    @staticmethod
    def _extract_size_range(size: Union[int, float]) -> str:
        """Extract size-based grouping key"""
        if size < 1024:  # < 1KB
            return "Small (< 1KB)"
        elif size < 1024 * 1024:  # < 1MB
            return "Medium (1KB - 1MB)"
        elif size < 1024 * 1024 * 100:  # < 100MB
            return "Large (1MB - 100MB)"
        else:
            return "Very Large (> 100MB)"


class ElementGroupingManager(QObject):
    """
    Advanced grouping manager for hierarchical element lists
    
    Provides multi-criteria grouping, custom groupers, performance optimization,
    and integration with tree view components.
    """
    
    # Signals
    grouping_applied = pyqtSignal(object)  # GroupingResult
    grouping_criteria_changed = pyqtSignal(list)  # List[GroupingCriterion]
    group_expanded = pyqtSignal(str, bool)  # group_key, is_expanded
    grouping_started = pyqtSignal(int)  # item_count
    grouping_progress = pyqtSignal(int)  # progress_percentage
    
    def __init__(self, parent: Optional[QObject] = None):
        """
        Initialize element grouping manager
        
        Args:
            parent: Parent QObject
        """
        super().__init__(parent)
        
        # Configuration
        self.default_strategy = GroupingStrategy.HIERARCHICAL
        self.enable_nested_grouping = True
        self.max_groups_per_level = 50  # Limit for performance
        
        # State
        self._current_criteria: List[GroupingCriterion] = []
        self._custom_groupers: Dict[str, Callable] = {}
        self._group_presets: Dict[str, List[GroupingCriterion]] = {}
        self._group_expansion_state: Dict[str, bool] = {}
        self._last_grouping_result: Optional[GroupingResult] = None
        
        # Initialize defaults
        self._initialize_default_groupers()
        self._initialize_default_presets()
        
        logger.info("ElementGroupingManager initialized")
    
    def add_grouping_criterion(self, criterion: GroupingCriterion) -> None:
        """
        Add a grouping criterion
        
        Args:
            criterion: Grouping criterion to add
        """
        # Remove existing criterion for same field
        self._current_criteria = [c for c in self._current_criteria if c.field != criterion.field]
        
        # Add new criterion
        self._current_criteria.append(criterion)
        
        logger.debug(f"Added grouping criterion: {criterion.field.value}")
        self.grouping_criteria_changed.emit(self._current_criteria)
    
    def remove_grouping_criterion(self, field: GroupingField) -> None:
        """
        Remove grouping criterion for specified field
        
        Args:
            field: Grouping field to remove
        """
        original_count = len(self._current_criteria)
        self._current_criteria = [c for c in self._current_criteria if c.field != field]
        
        if len(self._current_criteria) < original_count:
            logger.debug(f"Removed grouping criterion: {field.value}")
            self.grouping_criteria_changed.emit(self._current_criteria)
    
    def set_grouping_criteria(self, criteria: List[GroupingCriterion]) -> None:
        """
        Set complete grouping criteria list
        
        Args:
            criteria: List of grouping criteria
        """
        self._current_criteria = criteria.copy()
        logger.debug(f"Set grouping criteria: {len(criteria)} criteria")
        self.grouping_criteria_changed.emit(self._current_criteria)
    
    def clear_grouping_criteria(self) -> None:
        """Clear all grouping criteria"""
        self._current_criteria.clear()
        logger.debug("Cleared all grouping criteria")
        self.grouping_criteria_changed.emit(self._current_criteria)
    
    def register_custom_grouper(self, name: str, grouper: Callable[[Any], str]) -> None:
        """
        Register a custom grouping function
        
        Args:
            name: Name for the grouper
            grouper: Function to extract group key from item
        """
        self._custom_groupers[name] = grouper
        logger.debug(f"Registered custom grouper: {name}")
    
    def register_preset(self, name: str, criteria: List[GroupingCriterion]) -> None:
        """
        Register a grouping preset
        
        Args:
            name: Preset name
            criteria: List of grouping criteria
        """
        self._group_presets[name] = criteria
        logger.debug(f"Registered grouping preset: {name}")
    
    def apply_preset(self, preset_name: str) -> bool:
        """
        Apply a grouping preset
        
        Args:
            preset_name: Name of preset to apply
            
        Returns:
            True if preset was applied successfully
        """
        if preset_name not in self._group_presets:
            logger.warning(f"Grouping preset not found: {preset_name}")
            return False
        
        criteria = self._group_presets[preset_name]
        self.set_grouping_criteria(criteria)
        
        logger.info(f"Applied grouping preset: {preset_name}")
        return True
    
    def group_items(self, 
                   items: List[Any], 
                   criteria: Optional[List[GroupingCriterion]] = None,
                   strategy: Optional[GroupingStrategy] = None) -> GroupingResult:
        """
        Group items using current or provided criteria
        
        Args:
            items: Items to group
            criteria: Optional criteria to use (uses current if None)
            strategy: Grouping strategy to use
            
        Returns:
            GroupingResult with grouped items and metadata
        """
        start_time = datetime.now()
        
        # Use provided criteria or current
        grouping_criteria = criteria or self._current_criteria
        grouping_strategy = strategy or self.default_strategy
        
        if not grouping_criteria:
            # No grouping criteria - return single group with all items
            single_group = ElementGroup(
                group_key="all",
                display_name="All Items",
                items=items.copy()
            )
            
            groups = OrderedDict([("all", single_group)])
            
            return GroupingResult(
                groups=groups,
                grouping_criteria=[],
                total_items=len(items),
                total_groups=1,
                execution_time=0.0,
                strategy=grouping_strategy
            )
        
        logger.debug(f"Grouping {len(items)} items with {len(grouping_criteria)} criteria")
        self.grouping_started.emit(len(items))
        
        try:
            # Perform grouping based on strategy
            if len(grouping_criteria) == 1:
                groups = self._group_single_criterion(items, grouping_criteria[0])
            else:
                if grouping_strategy == GroupingStrategy.NESTED:
                    groups = self._group_nested(items, grouping_criteria)
                else:
                    groups = self._group_multi_criteria(items, grouping_criteria)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            result = GroupingResult(
                groups=groups,
                grouping_criteria=grouping_criteria.copy(),
                total_items=len(items),
                total_groups=len(groups),
                execution_time=execution_time,
                strategy=grouping_strategy
            )
            
            self._last_grouping_result = result
            
            logger.debug(f"Grouping completed in {execution_time:.3f}s, created {len(groups)} groups")
            self.grouping_applied.emit(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Grouping operation failed: {e}")
            # Return single group on error
            error_group = ElementGroup(
                group_key="error",
                display_name="Grouping Error",
                items=items.copy()
            )
            
            return GroupingResult(
                groups=OrderedDict([("error", error_group)]),
                grouping_criteria=grouping_criteria.copy(),
                total_items=len(items),
                total_groups=1,
                execution_time=0.0,
                strategy=grouping_strategy
            )
    
    def expand_group(self, group_key: str, expanded: bool = True) -> None:
        """
        Set expansion state for a group
        
        Args:
            group_key: Key of group to expand/collapse
            expanded: Whether group should be expanded
        """
        self._group_expansion_state[group_key] = expanded
        self.group_expanded.emit(group_key, expanded)
    
    def is_group_expanded(self, group_key: str) -> bool:
        """
        Check if group is expanded
        
        Args:
            group_key: Group key to check
            
        Returns:
            True if group is expanded
        """
        return self._group_expansion_state.get(group_key, True)
    
    def get_available_presets(self) -> List[str]:
        """
        Get list of available grouping presets
        
        Returns:
            List of preset names
        """
        return list(self._group_presets.keys())
    
    def get_current_criteria(self) -> List[GroupingCriterion]:
        """
        Get current grouping criteria
        
        Returns:
            List of current grouping criteria
        """
        return self._current_criteria.copy()
    
    def get_last_grouping_result(self) -> Optional[GroupingResult]:
        """
        Get the last grouping result
        
        Returns:
            Last grouping result or None
        """
        return self._last_grouping_result
    
    def _group_single_criterion(self, items: List[Any], criterion: GroupingCriterion) -> OrderedDict[str, ElementGroup]:
        """Group items by single criterion"""
        groups = defaultdict(list)
        
        # Group items
        for item in items:
            group_key = GroupKeyExtractor.extract_key(item, criterion.field, criterion.custom_grouper)
            groups[group_key].append(item)
        
        # Create ElementGroup objects
        result_groups = OrderedDict()
        
        # Sort group keys if needed
        group_keys = list(groups.keys())
        if criterion.sort_groups:
            if criterion.group_order:
                # Use custom order
                ordered_keys = []
                for key in criterion.group_order:
                    if key in group_keys:
                        ordered_keys.append(key)
                        group_keys.remove(key)
                # Add remaining keys
                ordered_keys.extend(sorted(group_keys))
                group_keys = ordered_keys
            else:
                group_keys.sort()
        
        # Create groups
        for group_key in group_keys:
            group_items = groups[group_key]
            
            # Sort items within group if needed
            if criterion.sort_items_within_groups:
                group_items.sort(key=lambda x: self._get_item_sort_key(x))
            
            group = ElementGroup(
                group_key=group_key,
                display_name=self._format_group_display_name(group_key, criterion.field),
                items=group_items,
                metadata={'criterion': criterion.field.value},
                is_expanded=self.is_group_expanded(group_key)
            )
            
            result_groups[group_key] = group
        
        return result_groups
    
    def _group_multi_criteria(self, items: List[Any], criteria: List[GroupingCriterion]) -> OrderedDict[str, ElementGroup]:
        """Group items by multiple criteria (flattened)"""
        groups = defaultdict(list)
        
        # Group items by combination of criteria
        for item in items:
            group_keys = []
            for criterion in criteria:
                key = GroupKeyExtractor.extract_key(item, criterion.field, criterion.custom_grouper)
                group_keys.append(key)
            
            combined_key = " | ".join(group_keys)
            groups[combined_key].append(item)
        
        # Create ElementGroup objects
        result_groups = OrderedDict()
        
        for group_key, group_items in sorted(groups.items()):
            group = ElementGroup(
                group_key=group_key,
                display_name=group_key,
                items=group_items,
                metadata={'criteria': [c.field.value for c in criteria]},
                is_expanded=self.is_group_expanded(group_key)
            )
            
            result_groups[group_key] = group
        
        return result_groups
    
    def _group_nested(self, items: List[Any], criteria: List[GroupingCriterion]) -> OrderedDict[str, ElementGroup]:
        """Group items by multiple criteria (nested groups)"""
        if not criteria:
            return OrderedDict()
        
        # Start with first criterion
        first_criterion = criteria[0]
        groups = self._group_single_criterion(items, first_criterion)
        
        # Apply remaining criteria recursively
        if len(criteria) > 1:
            remaining_criteria = criteria[1:]
            
            for group in groups.values():
                if group.items:
                    subgroups = self._group_nested(group.items, remaining_criteria)
                    group.subgroups = subgroups
                    # Clear items from parent group since they're now in subgroups
                    group.items = []
        
        return groups
    
    def _get_item_sort_key(self, item: Any) -> str:
        """Get sort key for item (used for sorting within groups)"""
        if hasattr(item, 'element_data'):
            return item.element_data.get('name', '').lower()
        elif isinstance(item, dict):
            return item.get('name', '').lower()
        else:
            return str(item).lower()
    
    def _format_group_display_name(self, group_key: str, field: GroupingField) -> str:
        """Format display name for group"""
        if field == GroupingField.TYPE:
            return f"{group_key} Elements"
        elif field == GroupingField.SIZE_RANGE:
            return group_key
        elif field == GroupingField.DATE_CREATED or field == GroupingField.DATE_MODIFIED:
            return f"Created in {group_key}" if field == GroupingField.DATE_CREATED else f"Modified in {group_key}"
        else:
            return group_key
    
    def _initialize_default_groupers(self) -> None:
        """Initialize default custom groupers"""
        
        # File extension grouper
        def extension_grouper(item):
            if hasattr(item, 'element_data'):
                name = item.element_data.get('name', '')
            elif isinstance(item, dict):
                name = item.get('name', '')
            else:
                name = str(item)
            
            if '.' in name:
                ext = name.split('.')[-1].lower()
                return f".{ext} files"
            else:
                return "No extension"
        
        self.register_custom_grouper("extension", extension_grouper)
        
        # Has children grouper
        def has_children_grouper(item):
            if hasattr(item, 'element_data'):
                children = item.element_data.get('children', [])
                return "Has Children" if children else "No Children"
            return "Unknown"
        
        self.register_custom_grouper("has_children", has_children_grouper)
    
    def _initialize_default_presets(self) -> None:
        """Initialize default grouping presets"""
        
        # By type
        self.register_preset("by_type", [
            GroupingCriterion(GroupingField.TYPE, "By Type")
        ])
        
        # By category
        self.register_preset("by_category", [
            GroupingCriterion(GroupingField.CATEGORY, "By Category")
        ])
        
        # By date modified
        self.register_preset("by_date_modified", [
            GroupingCriterion(GroupingField.DATE_MODIFIED, "By Date Modified")
        ])
        
        # By size range
        self.register_preset("by_size", [
            GroupingCriterion(GroupingField.SIZE_RANGE, "By Size Range")
        ])
        
        # By type and category (nested)
        self.register_preset("type_category", [
            GroupingCriterion(GroupingField.TYPE, "By Type"),
            GroupingCriterion(GroupingField.CATEGORY, "By Category")
        ])