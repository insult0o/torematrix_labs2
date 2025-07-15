"""
Advanced Filter Management System

Provides sophisticated filtering capabilities with type-based filters,
property filters, saved filter sets, and filter combinations.
"""

import time
import uuid
from typing import Dict, List, Set, Optional, Any, Union, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import json
import re
from datetime import datetime, date

from ....core.models.element import Element, ElementType
from ....core.models.metadata import ElementMetadata


class FilterOperator(Enum):
    """Filter comparison operators."""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_EQUAL = "greater_equal"
    LESS_EQUAL = "less_equal"
    BETWEEN = "between"
    IN = "in"
    NOT_IN = "not_in"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"
    REGEX = "regex"
    FUZZY = "fuzzy"


class FilterLogic(Enum):
    """Filter combination logic."""
    AND = "and"
    OR = "or"
    NOT = "not"


class FilterType(Enum):
    """Types of filters available."""
    ELEMENT_TYPE = "element_type"
    TEXT_CONTENT = "text_content"
    CONFIDENCE = "confidence"
    PAGE_NUMBER = "page_number"
    DETECTION_METHOD = "detection_method"
    LANGUAGE = "language"
    CUSTOM_FIELD = "custom_field"
    DATE_RANGE = "date_range"
    COORDINATE = "coordinate"
    HIERARCHY = "hierarchy"


@dataclass
class FilterValue:
    """Represents a filter value with type information."""
    value: Any
    data_type: str = "string"  # string, number, boolean, date, list
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "value": self.value,
            "data_type": self.data_type
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FilterValue':
        """Deserialize from dictionary."""
        return cls(
            value=data["value"],
            data_type=data.get("data_type", "string")
        )


@dataclass
class FilterCondition:
    """Single filter condition."""
    filter_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    filter_type: FilterType = FilterType.TEXT_CONTENT
    field_name: str = ""
    operator: FilterOperator = FilterOperator.CONTAINS
    value: FilterValue = field(default_factory=lambda: FilterValue(""))
    enabled: bool = True
    
    def matches(self, element: Element) -> bool:
        """Check if element matches this filter condition."""
        if not self.enabled:
            return True
        
        try:
            element_value = self._extract_element_value(element)
            return self._compare_values(element_value, self.value.value)
        except Exception:
            return False
    
    def _extract_element_value(self, element: Element) -> Any:
        """Extract the relevant value from element for comparison."""
        if self.filter_type == FilterType.ELEMENT_TYPE:
            return element.element_type.value
        
        elif self.filter_type == FilterType.TEXT_CONTENT:
            return element.text or ""
        
        elif self.filter_type == FilterType.CONFIDENCE:
            return element.metadata.confidence if element.metadata else 1.0
        
        elif self.filter_type == FilterType.PAGE_NUMBER:
            return element.metadata.page_number if element.metadata else None
        
        elif self.filter_type == FilterType.DETECTION_METHOD:
            return element.metadata.detection_method if element.metadata else ""
        
        elif self.filter_type == FilterType.LANGUAGE:
            return element.metadata.languages if element.metadata else []
        
        elif self.filter_type == FilterType.CUSTOM_FIELD:
            if element.metadata and element.metadata.custom_fields:
                return element.metadata.custom_fields.get(self.field_name)
            return None
        
        else:
            return None
    
    def _compare_values(self, element_value: Any, filter_value: Any) -> bool:
        """Compare element value with filter value using the operator."""
        if element_value is None:
            return self.operator in (FilterOperator.IS_NULL, FilterOperator.NOT_EQUALS)
        
        if self.operator == FilterOperator.IS_NULL:
            return element_value is None
        
        elif self.operator == FilterOperator.IS_NOT_NULL:
            return element_value is not None
        
        elif self.operator == FilterOperator.EQUALS:
            return element_value == filter_value
        
        elif self.operator == FilterOperator.NOT_EQUALS:
            return element_value != filter_value
        
        elif self.operator == FilterOperator.CONTAINS:
            return str(filter_value).lower() in str(element_value).lower()
        
        elif self.operator == FilterOperator.NOT_CONTAINS:
            return str(filter_value).lower() not in str(element_value).lower()
        
        elif self.operator == FilterOperator.STARTS_WITH:
            return str(element_value).lower().startswith(str(filter_value).lower())
        
        elif self.operator == FilterOperator.ENDS_WITH:
            return str(element_value).lower().endswith(str(filter_value).lower())
        
        elif self.operator == FilterOperator.GREATER_THAN:
            return float(element_value) > float(filter_value)
        
        elif self.operator == FilterOperator.LESS_THAN:
            return float(element_value) < float(filter_value)
        
        elif self.operator == FilterOperator.GREATER_EQUAL:
            return float(element_value) >= float(filter_value)
        
        elif self.operator == FilterOperator.LESS_EQUAL:
            return float(element_value) <= float(filter_value)
        
        elif self.operator == FilterOperator.BETWEEN:
            if isinstance(filter_value, (list, tuple)) and len(filter_value) == 2:
                min_val, max_val = filter_value
                return float(min_val) <= float(element_value) <= float(max_val)
            return False
        
        elif self.operator == FilterOperator.IN:
            if isinstance(filter_value, (list, tuple, set)):
                return element_value in filter_value
            return element_value == filter_value
        
        elif self.operator == FilterOperator.NOT_IN:
            if isinstance(filter_value, (list, tuple, set)):
                return element_value not in filter_value
            return element_value != filter_value
        
        elif self.operator == FilterOperator.REGEX:
            try:
                pattern = re.compile(str(filter_value), re.IGNORECASE)
                return bool(pattern.search(str(element_value)))
            except re.error:
                return False
        
        elif self.operator == FilterOperator.FUZZY:
            # Simple fuzzy matching - can be enhanced
            element_str = str(element_value).lower()
            filter_str = str(filter_value).lower()
            return self._fuzzy_match(element_str, filter_str)
        
        return False
    
    def _fuzzy_match(self, text1: str, text2: str, threshold: float = 0.7) -> bool:
        """Simple fuzzy string matching."""
        if len(text2) == 0:
            return len(text1) == 0
        
        # Calculate simple similarity based on common characters
        common_chars = 0
        for char in text2:
            if char in text1:
                common_chars += 1
        
        similarity = common_chars / len(text2)
        return similarity >= threshold
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize filter condition to dictionary."""
        return {
            "filter_id": self.filter_id,
            "filter_type": self.filter_type.value,
            "field_name": self.field_name,
            "operator": self.operator.value,
            "value": self.value.to_dict(),
            "enabled": self.enabled
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FilterCondition':
        """Deserialize filter condition from dictionary."""
        return cls(
            filter_id=data.get("filter_id", str(uuid.uuid4())),
            filter_type=FilterType(data["filter_type"]),
            field_name=data.get("field_name", ""),
            operator=FilterOperator(data["operator"]),
            value=FilterValue.from_dict(data["value"]),
            enabled=data.get("enabled", True)
        )


@dataclass
class FilterGroup:
    """Group of filter conditions with combination logic."""
    group_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    conditions: List[FilterCondition] = field(default_factory=list)
    logic: FilterLogic = FilterLogic.AND
    enabled: bool = True
    
    def matches(self, element: Element) -> bool:
        """Check if element matches this filter group."""
        if not self.enabled or not self.conditions:
            return True
        
        if self.logic == FilterLogic.AND:
            return all(condition.matches(element) for condition in self.conditions if condition.enabled)
        
        elif self.logic == FilterLogic.OR:
            return any(condition.matches(element) for condition in self.conditions if condition.enabled)
        
        elif self.logic == FilterLogic.NOT:
            # NOT logic - element must NOT match any condition
            return not any(condition.matches(element) for condition in self.conditions if condition.enabled)
        
        return True
    
    def add_condition(self, condition: FilterCondition) -> None:
        """Add a filter condition to this group."""
        self.conditions.append(condition)
    
    def remove_condition(self, condition_id: str) -> bool:
        """Remove a filter condition by ID."""
        initial_count = len(self.conditions)
        self.conditions = [c for c in self.conditions if c.filter_id != condition_id]
        return len(self.conditions) < initial_count
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize filter group to dictionary."""
        return {
            "group_id": self.group_id,
            "conditions": [condition.to_dict() for condition in self.conditions],
            "logic": self.logic.value,
            "enabled": self.enabled
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FilterGroup':
        """Deserialize filter group from dictionary."""
        return cls(
            group_id=data.get("group_id", str(uuid.uuid4())),
            conditions=[FilterCondition.from_dict(c) for c in data.get("conditions", [])],
            logic=FilterLogic(data.get("logic", "and")),
            enabled=data.get("enabled", True)
        )


@dataclass
class FilterSet:
    """Complete filter set with multiple groups and metadata."""
    filter_set_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    groups: List[FilterGroup] = field(default_factory=list)
    combination_logic: FilterLogic = FilterLogic.AND
    created_date: float = field(default_factory=time.time)
    modified_date: float = field(default_factory=time.time)
    is_preset: bool = False
    tags: List[str] = field(default_factory=list)
    
    def matches(self, element: Element) -> bool:
        """Check if element matches this filter set."""
        if not self.groups:
            return True
        
        enabled_groups = [g for g in self.groups if g.enabled]
        if not enabled_groups:
            return True
        
        if self.combination_logic == FilterLogic.AND:
            return all(group.matches(element) for group in enabled_groups)
        
        elif self.combination_logic == FilterLogic.OR:
            return any(group.matches(element) for group in enabled_groups)
        
        elif self.combination_logic == FilterLogic.NOT:
            return not any(group.matches(element) for group in enabled_groups)
        
        return True
    
    def add_group(self, group: FilterGroup) -> None:
        """Add a filter group to this set."""
        self.groups.append(group)
        self.modified_date = time.time()
    
    def remove_group(self, group_id: str) -> bool:
        """Remove a filter group by ID."""
        initial_count = len(self.groups)
        self.groups = [g for g in self.groups if g.group_id != group_id]
        if len(self.groups) < initial_count:
            self.modified_date = time.time()
            return True
        return False
    
    def get_group(self, group_id: str) -> Optional[FilterGroup]:
        """Get a filter group by ID."""
        for group in self.groups:
            if group.group_id == group_id:
                return group
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize filter set to dictionary."""
        return {
            "filter_set_id": self.filter_set_id,
            "name": self.name,
            "description": self.description,
            "groups": [group.to_dict() for group in self.groups],
            "combination_logic": self.combination_logic.value,
            "created_date": self.created_date,
            "modified_date": self.modified_date,
            "is_preset": self.is_preset,
            "tags": self.tags
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FilterSet':
        """Deserialize filter set from dictionary."""
        return cls(
            filter_set_id=data.get("filter_set_id", str(uuid.uuid4())),
            name=data.get("name", ""),
            description=data.get("description", ""),
            groups=[FilterGroup.from_dict(g) for g in data.get("groups", [])],
            combination_logic=FilterLogic(data.get("combination_logic", "and")),
            created_date=data.get("created_date", time.time()),
            modified_date=data.get("modified_date", time.time()),
            is_preset=data.get("is_preset", False),
            tags=data.get("tags", [])
        )


class FilterManager:
    """Manages filter sets, presets, and filter operations."""
    
    def __init__(self):
        self.filter_sets: Dict[str, FilterSet] = {}
        self.presets: Dict[str, FilterSet] = {}
        self.active_filter_set: Optional[FilterSet] = None
        
        # Initialize with default presets
        self._initialize_presets()
    
    def create_filter_set(self, name: str, description: str = "") -> FilterSet:
        """Create a new filter set."""
        filter_set = FilterSet(name=name, description=description)
        self.filter_sets[filter_set.filter_set_id] = filter_set
        return filter_set
    
    def save_filter_set(self, filter_set: FilterSet) -> None:
        """Save a filter set."""
        filter_set.modified_date = time.time()
        self.filter_sets[filter_set.filter_set_id] = filter_set
    
    def delete_filter_set(self, filter_set_id: str) -> bool:
        """Delete a filter set."""
        if filter_set_id in self.filter_sets:
            del self.filter_sets[filter_set_id]
            if self.active_filter_set and self.active_filter_set.filter_set_id == filter_set_id:
                self.active_filter_set = None
            return True
        return False
    
    def get_filter_set(self, filter_set_id: str) -> Optional[FilterSet]:
        """Get a filter set by ID."""
        return self.filter_sets.get(filter_set_id)
    
    def list_filter_sets(self, include_presets: bool = True) -> List[FilterSet]:
        """List all filter sets."""
        sets = list(self.filter_sets.values())
        if include_presets:
            sets.extend(self.presets.values())
        return sorted(sets, key=lambda x: x.modified_date, reverse=True)
    
    def set_active_filter_set(self, filter_set: Optional[FilterSet]) -> None:
        """Set the active filter set."""
        self.active_filter_set = filter_set
    
    def get_active_filter_set(self) -> Optional[FilterSet]:
        """Get the currently active filter set."""
        return self.active_filter_set
    
    def filter_elements(self, elements: List[Element], filter_set: Optional[FilterSet] = None) -> List[Element]:
        """Filter elements using a filter set."""
        if filter_set is None:
            filter_set = self.active_filter_set
        
        if filter_set is None:
            return elements
        
        return [element for element in elements if filter_set.matches(element)]
    
    def get_element_ids(self, elements: List[Element], filter_set: Optional[FilterSet] = None) -> Set[str]:
        """Get element IDs that match the filter set."""
        filtered_elements = self.filter_elements(elements, filter_set)
        return {element.element_id for element in filtered_elements}
    
    def search_filter_sets(self, query: str) -> List[FilterSet]:
        """Search filter sets by name, description, or tags."""
        query_lower = query.lower()
        results = []
        
        for filter_set in self.list_filter_sets():
            if (query_lower in filter_set.name.lower() or
                query_lower in filter_set.description.lower() or
                any(query_lower in tag.lower() for tag in filter_set.tags)):
                results.append(filter_set)
        
        return results
    
    def duplicate_filter_set(self, filter_set_id: str, new_name: str) -> Optional[FilterSet]:
        """Duplicate an existing filter set."""
        original = self.get_filter_set(filter_set_id)
        if not original:
            return None
        
        # Create a deep copy
        data = original.to_dict()
        data["filter_set_id"] = str(uuid.uuid4())
        data["name"] = new_name
        data["created_date"] = time.time()
        data["modified_date"] = time.time()
        data["is_preset"] = False
        
        duplicate = FilterSet.from_dict(data)
        self.filter_sets[duplicate.filter_set_id] = duplicate
        return duplicate
    
    def export_filter_set(self, filter_set_id: str) -> str:
        """Export filter set to JSON string."""
        filter_set = self.get_filter_set(filter_set_id)
        if not filter_set:
            raise ValueError(f"Filter set {filter_set_id} not found")
        
        return json.dumps(filter_set.to_dict(), indent=2)
    
    def import_filter_set(self, json_data: str) -> FilterSet:
        """Import filter set from JSON string."""
        data = json.loads(json_data)
        filter_set = FilterSet.from_dict(data)
        
        # Ensure unique ID
        filter_set.filter_set_id = str(uuid.uuid4())
        filter_set.is_preset = False
        
        self.filter_sets[filter_set.filter_set_id] = filter_set
        return filter_set
    
    def get_filter_statistics(self) -> Dict[str, Any]:
        """Get statistics about filter usage."""
        total_sets = len(self.filter_sets)
        total_presets = len(self.presets)
        
        # Count conditions across all sets
        total_conditions = 0
        total_groups = 0
        for filter_set in self.filter_sets.values():
            total_groups += len(filter_set.groups)
            for group in filter_set.groups:
                total_conditions += len(group.conditions)
        
        return {
            "total_filter_sets": total_sets,
            "total_presets": total_presets,
            "total_groups": total_groups,
            "total_conditions": total_conditions,
            "active_filter": self.active_filter_set.name if self.active_filter_set else None
        }
    
    def _initialize_presets(self) -> None:
        """Initialize default filter presets."""
        # High Confidence Elements
        high_confidence = FilterSet(
            name="High Confidence Elements",
            description="Elements with confidence > 0.8",
            is_preset=True,
            tags=["confidence", "quality"]
        )
        group = FilterGroup()
        group.add_condition(FilterCondition(
            filter_type=FilterType.CONFIDENCE,
            operator=FilterOperator.GREATER_THAN,
            value=FilterValue(0.8, "number")
        ))
        high_confidence.add_group(group)
        self.presets[high_confidence.filter_set_id] = high_confidence
        
        # Title Elements Only
        titles_only = FilterSet(
            name="Title Elements Only",
            description="Filter to show only title elements",
            is_preset=True,
            tags=["type", "titles"]
        )
        group = FilterGroup()
        group.add_condition(FilterCondition(
            filter_type=FilterType.ELEMENT_TYPE,
            operator=FilterOperator.EQUALS,
            value=FilterValue(ElementType.TITLE.value, "string")
        ))
        titles_only.add_group(group)
        self.presets[titles_only.filter_set_id] = titles_only
        
        # Recent Elements (Page 1-3)
        recent_elements = FilterSet(
            name="Recent Elements",
            description="Elements from the first 3 pages",
            is_preset=True,
            tags=["page", "recent"]
        )
        group = FilterGroup()
        group.add_condition(FilterCondition(
            filter_type=FilterType.PAGE_NUMBER,
            operator=FilterOperator.BETWEEN,
            value=FilterValue([1, 3], "list")
        ))
        recent_elements.add_group(group)
        self.presets[recent_elements.filter_set_id] = recent_elements
        
        # Text Elements with Content
        text_with_content = FilterSet(
            name="Text Elements with Content",
            description="Non-empty text elements",
            is_preset=True,
            tags=["text", "content"]
        )
        group = FilterGroup()
        group.add_condition(FilterCondition(
            filter_type=FilterType.TEXT_CONTENT,
            operator=FilterOperator.IS_NOT_NULL,
            value=FilterValue("", "string")
        ))
        group.add_condition(FilterCondition(
            filter_type=FilterType.ELEMENT_TYPE,
            operator=FilterOperator.IN,
            value=FilterValue([ElementType.NARRATIVE_TEXT.value, ElementType.TEXT.value], "list")
        ))
        text_with_content.add_group(group)
        self.presets[text_with_content.filter_set_id] = text_with_content