"""
Element Grouping Manager for Hierarchical Element List

Provides advanced grouping capabilities with multiple strategies,
custom groupers, and group management for better data organization.
"""

import logging
from typing import List, Dict, Any, Optional, Callable, Set, Union
from dataclasses import dataclass, field
from enum import Enum
from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class GroupingStrategy(Enum):
    """Grouping strategy options"""
    FLAT = "flat"           # Single level groups
    HIERARCHICAL = "hierarchical"  # Multi-level nested groups
    NESTED = "nested"       # Groups within groups


class GroupSortOrder(Enum):
    """Group sorting options"""
    ALPHABETICAL = "alphabetical"
    SIZE_ASCENDING = "size_asc"
    SIZE_DESCENDING = "size_desc"
    CUSTOM = "custom"


@dataclass
class GroupingCriterion:
    """Represents a single grouping criterion"""
    field: str
    strategy: GroupingStrategy = GroupingStrategy.FLAT
    custom_grouper: Optional[Callable[[Any], str]] = None
    sort_order: GroupSortOrder = GroupSortOrder.ALPHABETICAL
    priority: int = 0
    enabled: bool = True
    max_groups: int = 50  # Limit number of groups for performance
    group_empty_values: bool = True
    empty_group_name: str = "(Ungrouped)"
    
    def __post_init__(self):
        """Validate grouping criterion"""
        if self.custom_grouper and not callable(self.custom_grouper):
            raise ValueError("Custom grouper must be callable")


@dataclass 
class ElementGroup:
    """Represents a group of elements"""
    group_id: str
    group_name: str
    group_key: Any
    element_ids: List[str] = field(default_factory=list)
    subgroups: Dict[str, 'ElementGroup'] = field(default_factory=dict)
    parent_group: Optional['ElementGroup'] = None
    depth: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def total_element_count(self) -> int:
        """Get total count including subgroups"""
        count = len(self.element_ids)
        for subgroup in self.subgroups.values():
            count += subgroup.total_element_count
        return count
    
    @property
    def is_leaf_group(self) -> bool:
        """Check if this is a leaf group (no subgroups)"""
        return not self.subgroups
    
    def add_element(self, element_id: str) -> None:
        """Add element to this group"""
        if element_id not in self.element_ids:
            self.element_ids.append(element_id)
    
    def remove_element(self, element_id: str) -> bool:
        """Remove element from this group"""
        try:
            self.element_ids.remove(element_id)
            return True
        except ValueError:
            return False
    
    def add_subgroup(self, subgroup: 'ElementGroup') -> None:
        """Add a subgroup"""
        subgroup.parent_group = self
        subgroup.depth = self.depth + 1
        self.subgroups[subgroup.group_id] = subgroup
    
    def get_all_element_ids(self) -> List[str]:
        """Get all element IDs including from subgroups"""
        all_ids = self.element_ids.copy()
        for subgroup in self.subgroups.values():
            all_ids.extend(subgroup.get_all_element_ids())
        return all_ids


@dataclass
class GroupingResult:
    """Results of a grouping operation"""
    groups: Dict[str, ElementGroup]
    criteria: List[GroupingCriterion]
    total_elements: int
    total_groups: int
    execution_time: float
    strategy: GroupingStrategy
    ungrouped_elements: List[str] = field(default_factory=list)


@dataclass
class GroupingPreset:
    """Predefined grouping configuration"""
    name: str
    description: str
    criteria: List[GroupingCriterion] = field(default_factory=list)
    icon: Optional[str] = None


class ElementGroupingManager(QObject):
    """
    Advanced grouping manager for hierarchical element list
    
    Provides sophisticated grouping capabilities with multiple strategies,
    custom groupers, and group preset management.
    """
    
    # Signals
    grouping_applied = pyqtSignal(object)  # GroupingResult
    grouping_criteria_changed = pyqtSignal(list)  # List[GroupingCriterion]
    group_expanded = pyqtSignal(str, bool)  # group_id, is_expanded
    preset_applied = pyqtSignal(str)  # preset_name
    
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        
        # Configuration
        self.max_grouping_criteria = 3
        self.default_strategy = GroupingStrategy.FLAT
        self.enable_group_caching = True
        self.cache_max_size = 5
        
        # State
        self._grouping_criteria: List[GroupingCriterion] = []
        self._grouping_presets: Dict[str, GroupingPreset] = {}
        self._cached_results: Dict[str, GroupingResult] = {}
        self._expanded_groups: Set[str] = set()
        self._data_provider = None
        
        # Performance tracking
        self._grouping_stats = {
            "total_groupings": 0,
            "avg_execution_time": 0.0,
            "largest_dataset": 0,
            "cache_hits": 0
        }
        
        # Setup default presets
        self._setup_default_presets()
        
        logger.info("ElementGroupingManager initialized")
    
    def set_data_provider(self, provider: Callable[[str], Any]) -> None:
        """
        Set data provider function for retrieving element data
        
        Args:
            provider: Function that takes element_id and returns element data
        """
        self._data_provider = provider
        logger.debug("Data provider set for grouping")
    
    def add_grouping_criterion(self, criterion: GroupingCriterion) -> bool:
        """
        Add a grouping criterion
        
        Args:
            criterion: Grouping criterion to add
            
        Returns:
            True if criterion was added successfully
        """
        if len(self._grouping_criteria) >= self.max_grouping_criteria:
            logger.warning(f"Cannot add more than {self.max_grouping_criteria} grouping criteria")
            return False
        
        # Check for duplicate field
        if any(c.field == criterion.field for c in self._grouping_criteria):
            logger.warning(f"Grouping criterion for field '{criterion.field}' already exists")
            return False
        
        # Set priority if not specified
        if criterion.priority == 0:
            criterion.priority = len(self._grouping_criteria) + 1
        
        self._grouping_criteria.append(criterion)
        self._grouping_criteria.sort(key=lambda c: c.priority)
        
        self._clear_cache()
        self.grouping_criteria_changed.emit(self._grouping_criteria)
        
        logger.debug(f"Added grouping criterion: {criterion.field}")
        return True
    
    def remove_grouping_criterion(self, field: str) -> bool:
        """
        Remove a grouping criterion by field name
        
        Args:
            field: Field name of criterion to remove
            
        Returns:
            True if criterion was removed
        """
        initial_count = len(self._grouping_criteria)
        self._grouping_criteria = [c for c in self._grouping_criteria if c.field != field]
        
        if len(self._grouping_criteria) < initial_count:
            self._clear_cache()
            self.grouping_criteria_changed.emit(self._grouping_criteria)
            logger.debug(f"Removed grouping criterion: {field}")
            return True
        
        return False
    
    def set_grouping_criteria(self, criteria: List[GroupingCriterion]) -> None:
        """
        Set complete list of grouping criteria
        
        Args:
            criteria: List of grouping criteria
        """
        if len(criteria) > self.max_grouping_criteria:
            criteria = criteria[:self.max_grouping_criteria]
            logger.warning(f"Truncated grouping criteria to {self.max_grouping_criteria} items")
        
        self._grouping_criteria = criteria.copy()
        self._grouping_criteria.sort(key=lambda c: c.priority)
        
        self._clear_cache()
        self.grouping_criteria_changed.emit(self._grouping_criteria)
        
        logger.debug(f"Set {len(criteria)} grouping criteria")
    
    def get_grouping_criteria(self) -> List[GroupingCriterion]:
        """Get current grouping criteria"""
        return self._grouping_criteria.copy()
    
    def clear_grouping_criteria(self) -> None:
        """Clear all grouping criteria"""
        self._grouping_criteria.clear()
        self._clear_cache()
        self.grouping_criteria_changed.emit([])
        logger.debug("Cleared all grouping criteria")
    
    def group_elements(self, element_ids: List[str], use_cache: bool = True) -> GroupingResult:
        """
        Group elements according to current criteria
        
        Args:
            element_ids: List of element IDs to group
            use_cache: Whether to use cached results if available
            
        Returns:
            GroupingResult with grouped elements and metadata
        """
        if not element_ids:
            return GroupingResult(
                groups={},
                criteria=[],
                total_elements=0,
                total_groups=0,
                execution_time=0.0,
                strategy=self.default_strategy
            )
        
        # Check cache
        cache_key = self._generate_cache_key(element_ids)
        if use_cache and cache_key in self._cached_results:
            cached_result = self._cached_results[cache_key]
            self._grouping_stats["cache_hits"] += 1
            logger.debug(f"Using cached grouping result for {len(element_ids)} items")
            return cached_result
        
        import time
        start_time = time.time()
        
        try:
            # Perform grouping
            if not self._grouping_criteria:
                # No criteria - create single group with all elements
                result = self._create_single_group_result(element_ids, start_time)
            else:
                # Perform multi-criteria grouping
                result = self._perform_multi_criteria_grouping(element_ids, start_time)
            
            # Cache result
            if use_cache:
                self._cache_result(cache_key, result)
            
            # Update statistics
            self._update_grouping_stats(result)
            
            # Emit signals
            self.grouping_applied.emit(result)
            
            logger.debug(f"Grouped {result.total_elements} items into {result.total_groups} groups in {result.execution_time:.3f}s")
            return result
            
        except Exception as e:
            logger.error(f"Grouping operation failed: {e}")
            return self._create_single_group_result(element_ids, start_time)
    
    def _perform_multi_criteria_grouping(self, element_ids: List[str], start_time: float) -> GroupingResult:
        """Perform multi-criteria grouping"""
        if not self._data_provider:
            logger.error("No data provider set for grouping")
            return self._create_single_group_result(element_ids, start_time)
        
        # Get enabled criteria sorted by priority
        active_criteria = [c for c in self._grouping_criteria if c.enabled]
        active_criteria.sort(key=lambda c: c.priority)
        
        if not active_criteria:
            return self._create_single_group_result(element_ids, start_time)
        
        # Determine overall strategy
        strategy = active_criteria[0].strategy
        if len(active_criteria) > 1:
            strategy = GroupingStrategy.HIERARCHICAL
        
        # Create groups based on strategy
        if strategy == GroupingStrategy.HIERARCHICAL:
            groups = self._create_hierarchical_groups(element_ids, active_criteria)
        elif strategy == GroupingStrategy.NESTED:
            groups = self._create_nested_groups(element_ids, active_criteria)
        else:
            groups = self._create_flat_groups(element_ids, active_criteria[0])
        
        execution_time = time.time() - start_time
        
        return GroupingResult(
            groups=groups,
            criteria=active_criteria,
            total_elements=len(element_ids),
            total_groups=len(groups),
            execution_time=execution_time,
            strategy=strategy
        )
    
    def _create_flat_groups(self, element_ids: List[str], criterion: GroupingCriterion) -> Dict[str, ElementGroup]:
        """Create flat groups using single criterion"""
        groups = {}
        ungrouped_elements = []
        
        for element_id in element_ids:
            try:
                data = self._data_provider(element_id)
                group_key = self._get_group_key(data, criterion)
                
                if group_key is None and not criterion.group_empty_values:
                    ungrouped_elements.append(element_id)
                    continue
                
                # Create group ID and name
                if group_key is None:
                    group_id = "ungrouped"
                    group_name = criterion.empty_group_name
                    group_key = None
                else:
                    group_id = f"{criterion.field}_{group_key}"
                    group_name = str(group_key)
                
                # Create or get group
                if group_id not in groups:
                    groups[group_id] = ElementGroup(
                        group_id=group_id,
                        group_name=group_name,
                        group_key=group_key,
                        metadata={"field": criterion.field, "criterion": criterion}
                    )
                
                groups[group_id].add_element(element_id)
                
            except Exception as e:
                logger.warning(f"Failed to group element {element_id}: {e}")
                ungrouped_elements.append(element_id)
        
        # Sort groups
        groups = self._sort_groups(groups, criterion.sort_order)
        
        return groups
    
    def _create_hierarchical_groups(self, element_ids: List[str], criteria: List[GroupingCriterion]) -> Dict[str, ElementGroup]:
        """Create hierarchical groups using multiple criteria"""
        root_groups = {}
        
        for element_id in element_ids:
            try:
                data = self._data_provider(element_id)
                current_groups = root_groups
                parent_group = None
                
                # Create nested group structure
                for depth, criterion in enumerate(criteria):
                    group_key = self._get_group_key(data, criterion)
                    
                    if group_key is None and not criterion.group_empty_values:
                        break
                    
                    # Create group ID and name
                    if group_key is None:
                        group_id = f"ungrouped_{depth}"
                        group_name = criterion.empty_group_name
                        group_key = None
                    else:
                        group_id = f"{criterion.field}_{group_key}_{depth}"
                        group_name = str(group_key)
                    
                    # Create or get group
                    if group_id not in current_groups:
                        group = ElementGroup(
                            group_id=group_id,
                            group_name=group_name,
                            group_key=group_key,
                            parent_group=parent_group,
                            depth=depth,
                            metadata={"field": criterion.field, "criterion": criterion}
                        )
                        current_groups[group_id] = group
                        
                        if parent_group:
                            parent_group.add_subgroup(group)
                    
                    group = current_groups[group_id]
                    
                    # For last criterion, add element
                    if depth == len(criteria) - 1:
                        group.add_element(element_id)
                    else:
                        # Move to subgroups for next level
                        current_groups = group.subgroups
                        parent_group = group
                
            except Exception as e:
                logger.warning(f"Failed to hierarchically group element {element_id}: {e}")
        
        return root_groups
    
    def _create_nested_groups(self, element_ids: List[str], criteria: List[GroupingCriterion]) -> Dict[str, ElementGroup]:
        """Create nested groups with all combinations"""
        # For nested strategy, create groups for each combination of criteria values
        groups = {}
        
        for element_id in element_ids:
            try:
                data = self._data_provider(element_id)
                group_keys = []
                
                # Get keys for all criteria
                for criterion in criteria:
                    key = self._get_group_key(data, criterion)
                    if key is None and not criterion.group_empty_values:
                        key = criterion.empty_group_name
                    group_keys.append(str(key) if key is not None else "None")
                
                # Create combined group
                group_id = "_".join(group_keys)
                group_name = " / ".join(group_keys)
                
                if group_id not in groups:
                    groups[group_id] = ElementGroup(
                        group_id=group_id,
                        group_name=group_name,
                        group_key=tuple(group_keys),
                        metadata={"criteria": criteria, "keys": group_keys}
                    )
                
                groups[group_id].add_element(element_id)
                
            except Exception as e:
                logger.warning(f"Failed to nested group element {element_id}: {e}")
        
        return groups
    
    def _get_group_key(self, data: Dict[str, Any], criterion: GroupingCriterion) -> Any:
        """Get grouping key for element data using criterion"""
        if criterion.custom_grouper:
            try:
                return criterion.custom_grouper(data)
            except Exception as e:
                logger.warning(f"Custom grouper failed: {e}")
                return None
        
        # Default grouping by field value
        value = data.get(criterion.field)
        
        if value is None:
            return None
        
        # Special handling for common field types
        if criterion.field in ['type', 'category', 'status']:
            return str(value).lower()
        elif criterion.field in ['size', 'length']:
            # Group by size ranges
            try:
                size = float(value)
                if size < 1024:
                    return "Small (< 1KB)"
                elif size < 1024 * 1024:
                    return "Medium (< 1MB)"
                else:
                    return "Large (≥ 1MB)"
            except (ValueError, TypeError):
                return str(value)
        elif criterion.field in ['created_at', 'modified_at']:
            # Group by date ranges
            try:
                from datetime import datetime
                if isinstance(value, str):
                    date = datetime.fromisoformat(value.replace('Z', '+00:00'))
                else:
                    date = value
                
                return date.strftime("%Y-%m")  # Group by month
            except Exception:
                return str(value)
        
        return str(value)
    
    def _sort_groups(self, groups: Dict[str, ElementGroup], sort_order: GroupSortOrder) -> Dict[str, ElementGroup]:
        """Sort groups according to sort order"""
        if sort_order == GroupSortOrder.ALPHABETICAL:
            sorted_items = sorted(groups.items(), key=lambda x: x[1].group_name.lower())
        elif sort_order == GroupSortOrder.SIZE_ASCENDING:
            sorted_items = sorted(groups.items(), key=lambda x: x[1].total_element_count)
        elif sort_order == GroupSortOrder.SIZE_DESCENDING:
            sorted_items = sorted(groups.items(), key=lambda x: x[1].total_element_count, reverse=True)
        else:  # CUSTOM or default
            sorted_items = list(groups.items())
        
        return dict(sorted_items)
    
    def _create_single_group_result(self, element_ids: List[str], start_time: float) -> GroupingResult:
        """Create result with single group containing all elements"""
        group = ElementGroup(
            group_id="all",
            group_name="All Elements",
            group_key="all",
            element_ids=element_ids.copy()
        )
        
        execution_time = time.time() - start_time
        
        return GroupingResult(
            groups={"all": group},
            criteria=[],
            total_elements=len(element_ids),
            total_groups=1,
            execution_time=execution_time,
            strategy=self.default_strategy
        )
    
    def _setup_default_presets(self) -> None:
        """Setup default grouping presets"""
        presets = [
            GroupingPreset(
                name="By Type",
                description="Group by element type",
                criteria=[
                    GroupingCriterion("type", GroupingStrategy.FLAT, sort_order=GroupSortOrder.ALPHABETICAL)
                ]
            ),
            GroupingPreset(
                name="By Status",
                description="Group by element status",
                criteria=[
                    GroupingCriterion("status", GroupingStrategy.FLAT, sort_order=GroupSortOrder.ALPHABETICAL)
                ]
            ),
            GroupingPreset(
                name="By Type and Status",
                description="Group by type, then by status",
                criteria=[
                    GroupingCriterion("type", GroupingStrategy.HIERARCHICAL, priority=1),
                    GroupingCriterion("status", GroupingStrategy.HIERARCHICAL, priority=2)
                ]
            ),
            GroupingPreset(
                name="By Creation Date",
                description="Group by creation date (month)",
                criteria=[
                    GroupingCriterion("created_at", GroupingStrategy.FLAT, sort_order=GroupSortOrder.ALPHABETICAL)
                ]
            ),
            GroupingPreset(
                name="By Size",
                description="Group by element size",
                criteria=[
                    GroupingCriterion("size", GroupingStrategy.FLAT, sort_order=GroupSortOrder.SIZE_DESCENDING)
                ]
            )
        ]
        
        for preset in presets:
            self._grouping_presets[preset.name] = preset
        
        logger.debug(f"Setup {len(presets)} default grouping presets")
    
    def add_grouping_preset(self, preset: GroupingPreset) -> bool:
        """Add a custom grouping preset"""
        if preset.name in self._grouping_presets:
            logger.warning(f"Grouping preset '{preset.name}' already exists")
            return False
        
        self._grouping_presets[preset.name] = preset
        logger.debug(f"Added grouping preset: {preset.name}")
        return True
    
    def apply_grouping_preset(self, preset_name: str) -> bool:
        """Apply a grouping preset"""
        if preset_name not in self._grouping_presets:
            logger.warning(f"Grouping preset '{preset_name}' not found")
            return False
        
        preset = self._grouping_presets[preset_name]
        self.set_grouping_criteria(preset.criteria)
        
        self.preset_applied.emit(preset_name)
        logger.debug(f"Applied grouping preset: {preset_name}")
        return True
    
    def get_grouping_presets(self) -> Dict[str, GroupingPreset]:
        """Get all available grouping presets"""
        return self._grouping_presets.copy()
    
    def set_group_expanded(self, group_id: str, expanded: bool) -> None:
        """Set group expansion state"""
        if expanded:
            self._expanded_groups.add(group_id)
        else:
            self._expanded_groups.discard(group_id)
        
        self.group_expanded.emit(group_id, expanded)
    
    def is_group_expanded(self, group_id: str) -> bool:
        """Check if group is expanded"""
        return group_id in self._expanded_groups
    
    def get_expanded_groups(self) -> Set[str]:
        """Get all expanded group IDs"""
        return self._expanded_groups.copy()
    
    def _generate_cache_key(self, element_ids: List[str]) -> str:
        """Generate cache key for grouping operation"""
        criteria_str = "|".join([
            f"{c.field}:{c.strategy.value}:{c.priority}"
            for c in self._grouping_criteria if c.enabled
        ])
        
        # Use hash of element IDs for large lists
        if len(element_ids) > 100:
            import hashlib
            ids_hash = hashlib.md5("|".join(sorted(element_ids)).encode()).hexdigest()
            return f"{criteria_str}#{ids_hash}"
        else:
            return f"{criteria_str}#{len(element_ids)}"
    
    def _cache_result(self, cache_key: str, result: GroupingResult) -> None:
        """Cache a grouping result"""
        if len(self._cached_results) >= self.cache_max_size:
            # Remove oldest entry
            oldest_key = next(iter(self._cached_results))
            del self._cached_results[oldest_key]
        
        self._cached_results[cache_key] = result
    
    def _clear_cache(self) -> None:
        """Clear grouping result cache"""
        self._cached_results.clear()
        logger.debug("Grouping cache cleared")
    
    def _update_grouping_stats(self, result: GroupingResult) -> None:
        """Update grouping performance statistics"""
        self._grouping_stats["total_groupings"] += 1
        
        # Update average execution time
        current_avg = self._grouping_stats["avg_execution_time"]
        total_groupings = self._grouping_stats["total_groupings"]
        self._grouping_stats["avg_execution_time"] = (
            (current_avg * (total_groupings - 1) + result.execution_time) / total_groupings
        )
        
        # Update largest dataset
        if result.total_elements > self._grouping_stats["largest_dataset"]:
            self._grouping_stats["largest_dataset"] = result.total_elements
    
    def get_grouping_statistics(self) -> Dict[str, Any]:
        """Get grouping performance statistics"""
        return self._grouping_stats.copy()