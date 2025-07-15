"""
Advanced Sorting Manager for Hierarchical Element List

Provides sophisticated sorting capabilities with multiple criteria,
custom sort orders, and performance optimization for large datasets.
"""

import logging
from typing import List, Dict, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QWidget

logger = logging.getLogger(__name__)


class SortOrder(Enum):
    """Sort order options"""
    ASCENDING = "asc"
    DESCENDING = "desc"


class SortDataType(Enum):
    """Data types for sorting"""
    STRING = "string"
    NUMBER = "number"
    DATE = "date"
    BOOLEAN = "boolean"
    CUSTOM = "custom"


@dataclass
class SortCriterion:
    """Represents a single sort criterion"""
    field: str
    order: SortOrder = SortOrder.ASCENDING
    data_type: SortDataType = SortDataType.STRING
    priority: int = 0
    enabled: bool = True
    custom_comparator: Optional[Callable[[Any, Any], int]] = None
    null_handling: str = "last"  # "first", "last", "ignore"
    case_sensitive: bool = False
    
    def __post_init__(self):
        """Validate sort criterion"""
        if self.custom_comparator and self.data_type != SortDataType.CUSTOM:
            self.data_type = SortDataType.CUSTOM


@dataclass
class SortResult:
    """Results of a sort operation"""
    sorted_items: List[str]  # List of element IDs in sorted order
    sort_criteria: List[SortCriterion]
    execution_time: float
    total_items: int
    comparisons_made: int
    stable_sort: bool = True


@dataclass
class SortPreset:
    """Predefined sort configuration"""
    name: str
    description: str
    criteria: List[SortCriterion] = field(default_factory=list)
    icon: Optional[str] = None
    shortcut: Optional[str] = None


class AdvancedSortingManager(QObject):
    """
    Advanced sorting manager for hierarchical element list
    
    Provides multi-criteria sorting with performance optimization,
    custom comparators, and sort preset management.
    """
    
    # Signals
    sort_applied = pyqtSignal(object)  # SortResult
    sort_criteria_changed = pyqtSignal(list)  # List[SortCriterion]
    preset_applied = pyqtSignal(str)  # preset_name
    sort_progress = pyqtSignal(int)  # percentage
    
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        
        # Configuration
        self.enable_stable_sort = True
        self.max_sort_criteria = 5
        self.enable_progress_tracking = True
        self.chunk_size = 1000  # For large dataset processing
        
        # State
        self._sort_criteria: List[SortCriterion] = []
        self._sort_presets: Dict[str, SortPreset] = {}
        self._cached_results: Dict[str, SortResult] = {}
        self._cache_max_size = 10
        self._is_sorting = False
        self._data_provider = None
        
        # Performance tracking
        self._sort_stats = {
            "total_sorts": 0,
            "avg_execution_time": 0.0,
            "largest_dataset": 0
        }
        
        # Setup default presets
        self._setup_default_presets()
        
        # Progress timer for large sorts
        self._progress_timer = QTimer()
        self._progress_timer.timeout.connect(self._update_sort_progress)
        
        logger.info("AdvancedSortingManager initialized")
    
    def set_data_provider(self, provider: Callable[[str], Any]) -> None:
        """
        Set data provider function for retrieving element data
        
        Args:
            provider: Function that takes element_id and returns element data
        """
        self._data_provider = provider
        logger.debug("Data provider set")
    
    def add_sort_criterion(self, criterion: SortCriterion) -> bool:
        """
        Add a sort criterion
        
        Args:
            criterion: Sort criterion to add
            
        Returns:
            True if criterion was added successfully
        """
        if len(self._sort_criteria) >= self.max_sort_criteria:
            logger.warning(f"Cannot add more than {self.max_sort_criteria} sort criteria")
            return False
        
        # Check for duplicate field
        if any(c.field == criterion.field for c in self._sort_criteria):
            logger.warning(f"Sort criterion for field '{criterion.field}' already exists")
            return False
        
        # Set priority if not specified
        if criterion.priority == 0:
            criterion.priority = len(self._sort_criteria) + 1
        
        self._sort_criteria.append(criterion)
        self._sort_criteria.sort(key=lambda c: c.priority)
        
        self._clear_cache()
        self.sort_criteria_changed.emit(self._sort_criteria)
        
        logger.debug(f"Added sort criterion: {criterion.field}")
        return True
    
    def remove_sort_criterion(self, field: str) -> bool:
        """
        Remove a sort criterion by field name
        
        Args:
            field: Field name of criterion to remove
            
        Returns:
            True if criterion was removed
        """
        initial_count = len(self._sort_criteria)
        self._sort_criteria = [c for c in self._sort_criteria if c.field != field]
        
        if len(self._sort_criteria) < initial_count:
            self._clear_cache()
            self.sort_criteria_changed.emit(self._sort_criteria)
            logger.debug(f"Removed sort criterion: {field}")
            return True
        
        return False
    
    def update_sort_criterion(self, field: str, **updates) -> bool:
        """
        Update an existing sort criterion
        
        Args:
            field: Field name of criterion to update
            **updates: Fields to update (order, priority, etc.)
            
        Returns:
            True if criterion was updated
        """
        for criterion in self._sort_criteria:
            if criterion.field == field:
                for key, value in updates.items():
                    if hasattr(criterion, key):
                        setattr(criterion, key, value)
                
                # Re-sort by priority
                self._sort_criteria.sort(key=lambda c: c.priority)
                
                self._clear_cache()
                self.sort_criteria_changed.emit(self._sort_criteria)
                
                logger.debug(f"Updated sort criterion: {field}")
                return True
        
        return False
    
    def set_sort_criteria(self, criteria: List[SortCriterion]) -> None:
        """
        Set complete list of sort criteria
        
        Args:
            criteria: List of sort criteria
        """
        if len(criteria) > self.max_sort_criteria:
            criteria = criteria[:self.max_sort_criteria]
            logger.warning(f"Truncated sort criteria to {self.max_sort_criteria} items")
        
        self._sort_criteria = criteria.copy()
        self._sort_criteria.sort(key=lambda c: c.priority)
        
        self._clear_cache()
        self.sort_criteria_changed.emit(self._sort_criteria)
        
        logger.debug(f"Set {len(criteria)} sort criteria")
    
    def get_sort_criteria(self) -> List[SortCriterion]:
        """Get current sort criteria"""
        return self._sort_criteria.copy()
    
    def clear_sort_criteria(self) -> None:
        """Clear all sort criteria"""
        self._sort_criteria.clear()
        self._clear_cache()
        self.sort_criteria_changed.emit([])
        logger.debug("Cleared all sort criteria")
    
    def sort_elements(self, element_ids: List[str], use_cache: bool = True) -> SortResult:
        """
        Sort elements according to current criteria
        
        Args:
            element_ids: List of element IDs to sort
            use_cache: Whether to use cached results if available
            
        Returns:
            SortResult with sorted element IDs and metadata
        """
        if not element_ids:
            return SortResult(
                sorted_items=[],
                sort_criteria=[],
                execution_time=0.0,
                total_items=0,
                comparisons_made=0
            )
        
        # Check cache
        cache_key = self._generate_cache_key(element_ids)
        if use_cache and cache_key in self._cached_results:
            cached_result = self._cached_results[cache_key]
            logger.debug(f"Using cached sort result for {len(element_ids)} items")
            return cached_result
        
        if self._is_sorting:
            logger.warning("Sort operation already in progress")
            return self._cached_results.get(cache_key, SortResult([], [], 0.0, 0, 0))
        
        self._is_sorting = True
        
        try:
            import time
            start_time = time.time()
            
            # Prepare sorting
            if not self._sort_criteria:
                # No criteria - return original order
                result = SortResult(
                    sorted_items=element_ids.copy(),
                    sort_criteria=[],
                    execution_time=time.time() - start_time,
                    total_items=len(element_ids),
                    comparisons_made=0
                )
            else:
                # Perform multi-criteria sort
                result = self._perform_multi_criteria_sort(element_ids, start_time)
            
            # Cache result
            if use_cache:
                self._cache_result(cache_key, result)
            
            # Update statistics
            self._update_sort_stats(result)
            
            # Emit signals
            self.sort_applied.emit(result)
            
            logger.debug(f"Sorted {result.total_items} items in {result.execution_time:.3f}s")
            return result
            
        finally:
            self._is_sorting = False
    
    def _perform_multi_criteria_sort(self, element_ids: List[str], start_time: float) -> SortResult:
        """Perform multi-criteria sorting"""
        if not self._data_provider:
            logger.error("No data provider set for sorting")
            return SortResult(element_ids.copy(), self._sort_criteria, 0.0, len(element_ids), 0)
        
        # Get enabled criteria sorted by priority
        active_criteria = [c for c in self._sort_criteria if c.enabled]
        active_criteria.sort(key=lambda c: c.priority)
        
        if not active_criteria:
            return SortResult(element_ids.copy(), [], 0.0, len(element_ids), 0)
        
        # Prepare data for sorting
        element_data = []
        comparisons_made = 0
        
        for element_id in element_ids:
            try:
                data = self._data_provider(element_id)
                element_data.append((element_id, data))
            except Exception as e:
                logger.warning(f"Failed to get data for element {element_id}: {e}")
                element_data.append((element_id, {}))
        
        # Progress tracking for large datasets
        if self.enable_progress_tracking and len(element_data) > self.chunk_size:
            self._progress_timer.start(100)
        
        # Custom comparison function
        def multi_criteria_compare(item1, item2):
            nonlocal comparisons_made
            comparisons_made += 1
            
            element_id1, data1 = item1
            element_id2, data2 = item2
            
            for criterion in active_criteria:
                result = self._compare_by_criterion(data1, data2, criterion)
                if result != 0:
                    return result
            
            return 0  # Equal
        
        # Perform sort
        try:
            if self.enable_stable_sort:
                # Use stable sort algorithm
                sorted_data = sorted(element_data, key=lambda x: x, 
                                   cmp=lambda x, y: multi_criteria_compare(x, y))
            else:
                # Use regular sort for better performance
                element_data.sort(key=lambda x: x, 
                                cmp=lambda x, y: multi_criteria_compare(x, y))
                sorted_data = element_data
            
        except Exception as e:
            logger.error(f"Sort operation failed: {e}")
            return SortResult(element_ids.copy(), active_criteria, 0.0, len(element_ids), 0)
        
        finally:
            if self._progress_timer.isActive():
                self._progress_timer.stop()
        
        # Extract sorted IDs
        sorted_ids = [item[0] for item in sorted_data]
        execution_time = time.time() - start_time
        
        return SortResult(
            sorted_items=sorted_ids,
            sort_criteria=active_criteria,
            execution_time=execution_time,
            total_items=len(element_ids),
            comparisons_made=comparisons_made,
            stable_sort=self.enable_stable_sort
        )
    
    def _compare_by_criterion(self, data1: Dict[str, Any], data2: Dict[str, Any], 
                             criterion: SortCriterion) -> int:
        """Compare two data items by a specific criterion"""
        try:
            # Get values
            value1 = data1.get(criterion.field)
            value2 = data2.get(criterion.field)
            
            # Handle null values
            if value1 is None and value2 is None:
                return 0
            elif value1 is None:
                return 1 if criterion.null_handling == "last" else -1
            elif value2 is None:
                return -1 if criterion.null_handling == "last" else 1
            
            # Use custom comparator if provided
            if criterion.custom_comparator:
                result = criterion.custom_comparator(value1, value2)
            else:
                result = self._default_compare(value1, value2, criterion)
            
            # Apply sort order
            if criterion.order == SortOrder.DESCENDING:
                result = -result
            
            return result
            
        except Exception as e:
            logger.warning(f"Comparison failed for field {criterion.field}: {e}")
            return 0
    
    def _default_compare(self, value1: Any, value2: Any, criterion: SortCriterion) -> int:
        """Default comparison implementation"""
        if criterion.data_type == SortDataType.STRING:
            str1 = str(value1)
            str2 = str(value2)
            
            if not criterion.case_sensitive:
                str1 = str1.lower()
                str2 = str2.lower()
            
            if str1 < str2:
                return -1
            elif str1 > str2:
                return 1
            return 0
            
        elif criterion.data_type == SortDataType.NUMBER:
            try:
                num1 = float(value1)
                num2 = float(value2)
                
                if num1 < num2:
                    return -1
                elif num1 > num2:
                    return 1
                return 0
            except (ValueError, TypeError):
                # Fall back to string comparison
                return self._default_compare(value1, value2, 
                    SortCriterion(criterion.field, data_type=SortDataType.STRING))
        
        elif criterion.data_type == SortDataType.DATE:
            try:
                from datetime import datetime
                
                # Try to parse as datetime
                if isinstance(value1, str):
                    date1 = datetime.fromisoformat(value1.replace('Z', '+00:00'))
                else:
                    date1 = value1
                
                if isinstance(value2, str):
                    date2 = datetime.fromisoformat(value2.replace('Z', '+00:00'))
                else:
                    date2 = value2
                
                if date1 < date2:
                    return -1
                elif date1 > date2:
                    return 1
                return 0
                
            except Exception:
                # Fall back to string comparison
                return self._default_compare(value1, value2,
                    SortCriterion(criterion.field, data_type=SortDataType.STRING))
        
        elif criterion.data_type == SortDataType.BOOLEAN:
            bool1 = bool(value1)
            bool2 = bool(value2)
            
            if bool1 == bool2:
                return 0
            return -1 if bool1 < bool2 else 1
        
        # Default: string comparison
        return self._default_compare(value1, value2,
            SortCriterion(criterion.field, data_type=SortDataType.STRING))
    
    def _setup_default_presets(self) -> None:
        """Setup default sort presets"""
        presets = [
            SortPreset(
                name="Alphabetical",
                description="Sort by name alphabetically",
                criteria=[
                    SortCriterion("name", SortOrder.ASCENDING, SortDataType.STRING, 1)
                ],
                shortcut="Ctrl+1"
            ),
            SortPreset(
                name="Type then Name",
                description="Sort by element type, then by name",
                criteria=[
                    SortCriterion("type", SortOrder.ASCENDING, SortDataType.STRING, 1),
                    SortCriterion("name", SortOrder.ASCENDING, SortDataType.STRING, 2)
                ],
                shortcut="Ctrl+2"
            ),
            SortPreset(
                name="Creation Date",
                description="Sort by creation date (newest first)",
                criteria=[
                    SortCriterion("created_at", SortOrder.DESCENDING, SortDataType.DATE, 1)
                ],
                shortcut="Ctrl+3"
            ),
            SortPreset(
                name="Modified Date",
                description="Sort by modification date (newest first)",
                criteria=[
                    SortCriterion("modified_at", SortOrder.DESCENDING, SortDataType.DATE, 1)
                ],
                shortcut="Ctrl+4"
            ),
            SortPreset(
                name="Size",
                description="Sort by element size (largest first)",
                criteria=[
                    SortCriterion("size", SortOrder.DESCENDING, SortDataType.NUMBER, 1)
                ],
                shortcut="Ctrl+5"
            )
        ]
        
        for preset in presets:
            self._sort_presets[preset.name] = preset
        
        logger.debug(f"Setup {len(presets)} default sort presets")
    
    def add_sort_preset(self, preset: SortPreset) -> bool:
        """Add a custom sort preset"""
        if preset.name in self._sort_presets:
            logger.warning(f"Sort preset '{preset.name}' already exists")
            return False
        
        self._sort_presets[preset.name] = preset
        logger.debug(f"Added sort preset: {preset.name}")
        return True
    
    def apply_sort_preset(self, preset_name: str) -> bool:
        """Apply a sort preset"""
        if preset_name not in self._sort_presets:
            logger.warning(f"Sort preset '{preset_name}' not found")
            return False
        
        preset = self._sort_presets[preset_name]
        self.set_sort_criteria(preset.criteria)
        
        self.preset_applied.emit(preset_name)
        logger.debug(f"Applied sort preset: {preset_name}")
        return True
    
    def get_sort_presets(self) -> Dict[str, SortPreset]:
        """Get all available sort presets"""
        return self._sort_presets.copy()
    
    def _generate_cache_key(self, element_ids: List[str]) -> str:
        """Generate cache key for sort operation"""
        criteria_str = "|".join([
            f"{c.field}:{c.order.value}:{c.data_type.value}:{c.priority}"
            for c in self._sort_criteria if c.enabled
        ])
        
        # Use hash of element IDs for large lists
        if len(element_ids) > 100:
            import hashlib
            ids_hash = hashlib.md5("|".join(sorted(element_ids)).encode()).hexdigest()
            return f"{criteria_str}#{ids_hash}"
        else:
            return f"{criteria_str}#{len(element_ids)}"
    
    def _cache_result(self, cache_key: str, result: SortResult) -> None:
        """Cache a sort result"""
        if len(self._cached_results) >= self._cache_max_size:
            # Remove oldest entry
            oldest_key = next(iter(self._cached_results))
            del self._cached_results[oldest_key]
        
        self._cached_results[cache_key] = result
    
    def _clear_cache(self) -> None:
        """Clear sort result cache"""
        self._cached_results.clear()
        logger.debug("Sort cache cleared")
    
    def _update_sort_stats(self, result: SortResult) -> None:
        """Update sorting performance statistics"""
        self._sort_stats["total_sorts"] += 1
        
        # Update average execution time
        current_avg = self._sort_stats["avg_execution_time"]
        total_sorts = self._sort_stats["total_sorts"]
        self._sort_stats["avg_execution_time"] = (
            (current_avg * (total_sorts - 1) + result.execution_time) / total_sorts
        )
        
        # Update largest dataset
        if result.total_items > self._sort_stats["largest_dataset"]:
            self._sort_stats["largest_dataset"] = result.total_items
    
    def _update_sort_progress(self) -> None:
        """Update sort progress for large datasets"""
        # This would be implemented with actual progress tracking
        # For now, emit a generic progress signal
        if self._is_sorting:
            self.sort_progress.emit(50)  # Placeholder
    
    def get_sort_statistics(self) -> Dict[str, Any]:
        """Get sorting performance statistics"""
        return self._sort_stats.copy()
    
    def set_chunk_size(self, size: int) -> None:
        """Set chunk size for processing large datasets"""
        self.chunk_size = max(100, size)
    
    def set_cache_size(self, size: int) -> None:
        """Set maximum cache size"""
        self._cache_max_size = max(1, size)
        
        # Trim cache if needed
        while len(self._cached_results) > self._cache_max_size:
            oldest_key = next(iter(self._cached_results))
            del self._cached_results[oldest_key]