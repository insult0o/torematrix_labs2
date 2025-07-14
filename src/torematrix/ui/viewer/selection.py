"""
Element Selection System for Document Viewer Overlay.
This module provides comprehensive element selection capabilities including
single, multi-element, and complex selection modes with state management.
"""
from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union, Protocol, Callable

from PyQt6.QtCore import QObject, pyqtSignal

from .coordinates import Rectangle, Point
from .layers import LayerElement


class SelectionMode(Enum):
    """Selection modes for different interaction patterns."""
    SINGLE = "single"           # Single element selection
    MULTI = "multi"             # Multiple element selection
    RECTANGULAR = "rectangular" # Rectangular region selection
    POLYGON = "polygon"         # Polygon region selection
    LASSO = "lasso"            # Lasso selection (freehand)
    LAYER = "layer"            # Layer-based selection
    TYPE = "type"              # Type-based selection


class SelectionOperation(Enum):
    """Operations for modifying selection state."""
    REPLACE = "replace"         # Replace current selection
    ADD = "add"                # Add to current selection
    REMOVE = "remove"          # Remove from current selection
    TOGGLE = "toggle"          # Toggle selection state
    INTERSECT = "intersect"    # Intersect with current selection


@dataclass
class SelectionCriteria:
    """Criteria for element selection."""
    element_types: Optional[List[str]] = None
    layers: Optional[List[str]] = None
    properties: Optional[Dict[str, Any]] = None
    bounds: Optional[Rectangle] = None
    min_size: Optional[float] = None
    max_size: Optional[float] = None


@dataclass
class SelectionState:
    """Represents the current selection state."""
    selected_elements: Set[LayerElement] = field(default_factory=set)
    selection_mode: SelectionMode = SelectionMode.SINGLE
    selection_bounds: Optional[Rectangle] = None
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    mode: SelectionMode = SelectionMode.SINGLE
    strategy: 'SelectionStrategy' = None
    
    def __post_init__(self):
        if self.strategy is None:
            from .multi_select import SelectionStrategy
            self.strategy = SelectionStrategy.CONTAINS
    
    def copy(self) -> SelectionState:
        """Create a copy of this selection state."""
        return SelectionState(
            selected_elements=self.selected_elements.copy(),
            selection_mode=self.selection_mode,
            selection_bounds=self.selection_bounds,
            timestamp=time.time(),
            metadata=self.metadata.copy(),
            mode=self.mode,
            strategy=self.strategy
        )


class SelectionValidator:
    """Validates selection operations and states."""
    
    def __init__(self):
        self.validation_rules = {}
    
    def add_rule(self, rule_name: str, validator: Callable[[List[str]], bool]) -> None:
        """Add a validation rule."""
        self.validation_rules[rule_name] = validator
    
    def validate_selection(self, element_ids: List[str]) -> Tuple[bool, List[str]]:
        """Validate a selection against all rules."""
        errors = []
        
        for rule_name, validator in self.validation_rules.items():
            try:
                if not validator(element_ids):
                    errors.append(f"Validation failed for rule: {rule_name}")
            except Exception as e:
                errors.append(f"Error in rule {rule_name}: {e}")
        
        return len(errors) == 0, errors


class SelectionAlgorithm(ABC):
    """Abstract base class for selection algorithms."""
    
    @abstractmethod
    def select(self, elements: List[LayerElement], criteria: SelectionCriteria) -> List[str]:
        """Select elements based on criteria."""
        pass


class RectangularSelector(SelectionAlgorithm):
    """Rectangular selection algorithm."""
    
    def select(self, elements: List[LayerElement], criteria: SelectionCriteria) -> List[str]:
        """Select elements within a rectangular region."""
        if not criteria.bounds:
            return []
        
        selected = []
        selection_bounds = criteria.bounds
        
        for element in elements:
            if not element.is_visible():
                continue
                
            element_bounds = element.get_bounds()
            
            # Check intersection with selection bounds
            if selection_bounds.intersects(element_bounds):
                # Apply additional filters
                if self._passes_filters(element, criteria):
                    selected.append(element.get_id())
        
        return selected
    
    def _passes_filters(self, element: LayerElement, criteria: SelectionCriteria) -> bool:
        """Check if element passes additional filter criteria."""
        # Type filter
        if criteria.element_types:
            element_type = getattr(element, 'element_type', None)
            if element_type not in criteria.element_types:
                return False
        
        # Layer filter
        if criteria.layers:
            layer_name = getattr(element, 'layer_name', None)
            if layer_name not in criteria.layers:
                return False
        
        # Size filter
        if criteria.min_size or criteria.max_size:
            bounds = element.get_bounds()
            element_size = bounds.width * bounds.height
            
            if criteria.min_size and element_size < criteria.min_size:
                return False
            if criteria.max_size and element_size > criteria.max_size:
                return False
        
        # Property filter
        if criteria.properties:
            element_props = getattr(element, 'properties', {})
            for prop_key, prop_value in criteria.properties.items():
                if element_props.get(prop_key) != prop_value:
                    return False
        
        return True


class PolygonSelector(SelectionAlgorithm):
    """Polygon selection algorithm."""
    
    def select(self, elements: List[LayerElement], criteria: SelectionCriteria) -> List[str]:
        """Select elements within a polygon region."""
        # For now, implement as rectangular selection
        # TODO: Implement actual polygon point-in-polygon testing
        rectangular_selector = RectangularSelector()
        return rectangular_selector.select(elements, criteria)


class LassoSelector(SelectionAlgorithm):
    """Lasso (freehand) selection algorithm."""
    
    def __init__(self):
        self.lasso_points: List[Point] = []
    
    def set_lasso_points(self, points: List[Point]) -> None:
        """Set the lasso selection points."""
        self.lasso_points = points
    
    def select(self, elements: List[LayerElement], criteria: SelectionCriteria) -> List[str]:
        """Select elements within the lasso region."""
        if not self.lasso_points:
            return []
        
        # Convert lasso to bounding rectangle for now
        # TODO: Implement proper point-in-polygon testing
        min_x = min(p.x for p in self.lasso_points)
        max_x = max(p.x for p in self.lasso_points)
        min_y = min(p.y for p in self.lasso_points)
        max_y = max(p.y for p in self.lasso_points)
        
        criteria.bounds = Rectangle(min_x, min_y, max_x - min_x, max_y - min_y)
        
        rectangular_selector = RectangularSelector()
        return rectangular_selector.select(elements, criteria)


class LayerSelector(SelectionAlgorithm):
    """Layer-based selection algorithm."""
    
    def select(self, elements: List[LayerElement], criteria: SelectionCriteria) -> List[str]:
        """Select all elements in specified layers."""
        if not criteria.layers:
            return []
        
        selected = []
        for element in elements:
            if not element.is_visible():
                continue
                
            layer_name = getattr(element, 'layer_name', None)
            if layer_name in criteria.layers:
                selected.append(element.get_id())
        
        return selected


class TypeSelector(SelectionAlgorithm):
    """Type-based selection algorithm."""
    
    def select(self, elements: List[LayerElement], criteria: SelectionCriteria) -> List[str]:
        """Select all elements of specified types."""
        if not criteria.element_types:
            return []
        
        selected = []
        for element in elements:
            if not element.is_visible():
                continue
                
            element_type = getattr(element, 'element_type', None)
            if element_type in criteria.element_types:
                selected.append(element.get_id())
        
        return selected


class SelectionManager(QObject):
    """
    Core selection management system for document viewer overlay.
    
    Handles all selection operations including single, multi, and complex
    selection modes with state management and validation.
    """
    
    # PyQt signals
    selection_changed = pyqtSignal(object)  # SelectionState
    mode_changed = pyqtSignal(object)  # SelectionMode
    strategy_changed = pyqtSignal(object)  # SelectionStrategy
    
    def __init__(self, overlay_integration_api=None):
        super().__init__()
        self.overlay_api = overlay_integration_api
        self.current_state = SelectionState()
        
        # Selection algorithms - will be initialized with overlay integration
        self.algorithms = {}
        self.overlay_integration = None
        
        # Validation and callbacks
        self.validator = SelectionValidator()
        self.selection_callbacks: List[Callable] = []
        
        # Element lookup cache
        self.element_cache: Dict[str, LayerElement] = {}
        self.cache_timestamp = 0
        
        # Performance tracking
        self.selection_metrics = {
            'selection_count': 0,
            'average_selection_time': 0.0,
            'last_selection_time': 0.0,
            'cache_hits': 0,
            'cache_misses': 0
        }
    
    def set_selection_mode(self, mode: SelectionMode) -> None:
        """Set the current selection mode."""
        self.current_state.selection_mode = mode
        self._notify_mode_changed(mode)
    
    def get_selection_mode(self) -> SelectionMode:
        """Get the current selection mode."""
        return self.current_state.selection_mode
    
    def select_element(self, element_id: str, operation: SelectionOperation = SelectionOperation.REPLACE) -> bool:
        """Select a single element."""
        start_time = time.time()
        
        try:
            # Validate element exists
            if not self._element_exists(element_id):
                return False
            
            # Apply selection operation
            if operation == SelectionOperation.REPLACE:
                self.current_state.selected_elements = {element_id}
            elif operation == SelectionOperation.ADD:
                self.current_state.selected_elements.add(element_id)
            elif operation == SelectionOperation.REMOVE:
                self.current_state.selected_elements.discard(element_id)
            elif operation == SelectionOperation.TOGGLE:
                if element_id in self.current_state.selected_elements:
                    self.current_state.selected_elements.remove(element_id)
                else:
                    self.current_state.selected_elements.add(element_id)
            
            # Validate selection
            valid, errors = self.validator.validate_selection(list(self.current_state.selected_elements))
            if not valid:
                # Revert selection if validation fails
                # TODO: Implement proper state rollback
                return False
            
            # Update timestamp and notify
            self.current_state.timestamp = time.time()
            self._notify_selection_changed()
            
            return True
            
        finally:
            # Update metrics
            selection_time = time.time() - start_time
            self._update_selection_metrics(selection_time)
    
    def select_elements(self, element_ids: List[str], operation: SelectionOperation = SelectionOperation.REPLACE) -> bool:
        """Select multiple elements."""
        start_time = time.time()
        
        try:
            # Validate all elements exist
            for element_id in element_ids:
                if not self._element_exists(element_id):
                    return False
            
            # Apply selection operation
            new_selection = set(element_ids)
            
            if operation == SelectionOperation.REPLACE:
                self.current_state.selected_elements = new_selection
            elif operation == SelectionOperation.ADD:
                self.current_state.selected_elements.update(new_selection)
            elif operation == SelectionOperation.REMOVE:
                self.current_state.selected_elements.difference_update(new_selection)
            elif operation == SelectionOperation.TOGGLE:
                for element_id in element_ids:
                    if element_id in self.current_state.selected_elements:
                        self.current_state.selected_elements.remove(element_id)
                    else:
                        self.current_state.selected_elements.add(element_id)
            elif operation == SelectionOperation.INTERSECT:
                self.current_state.selected_elements.intersection_update(new_selection)
            
            # Validate selection
            valid, errors = self.validator.validate_selection(list(self.current_state.selected_elements))
            if not valid:
                return False
            
            # Update timestamp and notify
            self.current_state.timestamp = time.time()
            self._notify_selection_changed()
            
            return True
            
        finally:
            selection_time = time.time() - start_time
            self._update_selection_metrics(selection_time)
    
    def select_in_region(self, bounds: Rectangle, operation: SelectionOperation = SelectionOperation.REPLACE) -> bool:
        """Select elements within a rectangular region."""
        if not self.overlay_api:
            return False
        
        start_time = time.time()
        
        try:
            # Get selectable elements in region
            elements = self.overlay_api.get_selectable_elements(bounds)
            
            # Use rectangular selector
            criteria = SelectionCriteria(bounds=bounds)
            selector = self.algorithms[SelectionMode.RECTANGULAR]
            selected_ids = selector.select(elements, criteria)
            
            # Apply selection
            return self.select_elements(selected_ids, operation)
            
        finally:
            selection_time = time.time() - start_time
            self._update_selection_metrics(selection_time)
    
    def select_by_criteria(self, criteria: SelectionCriteria, operation: SelectionOperation = SelectionOperation.REPLACE) -> bool:
        """Select elements based on complex criteria."""
        if not self.overlay_api:
            return False
        
        start_time = time.time()
        
        try:
            # Get all elements for criteria-based selection
            all_elements = self._get_all_elements()
            
            # Determine selection algorithm
            if criteria.bounds:
                selector = self.algorithms[SelectionMode.RECTANGULAR]
            elif criteria.layers:
                selector = self.algorithms[SelectionMode.LAYER]
            elif criteria.element_types:
                selector = self.algorithms[SelectionMode.TYPE]
            else:
                # Default to rectangular with no bounds (select all)
                selector = self.algorithms[SelectionMode.RECTANGULAR]
            
            # Execute selection
            selected_ids = selector.select(all_elements, criteria)
            
            # Apply selection
            return self.select_elements(selected_ids, operation)
            
        finally:
            selection_time = time.time() - start_time
            self._update_selection_metrics(selection_time)
    
    def clear_selection(self) -> None:
        """Clear all selected elements."""
        if self.current_state.selected_elements:
            self.current_state.selected_elements.clear()
            self.current_state.timestamp = time.time()
            self._notify_selection_changed()
    
    def get_selected_elements(self) -> Set[str]:
        """Get the currently selected element IDs."""
        return self.current_state.selected_elements.copy()
    
    def get_selection_count(self) -> int:
        """Get the number of selected elements."""
        return len(self.current_state.selected_elements)
    
    def is_element_selected(self, element_id: str) -> bool:
        """Check if an element is selected."""
        return element_id in self.current_state.selected_elements
    
    def get_selection_bounds(self) -> Optional[Rectangle]:
        """Get the bounding rectangle of all selected elements."""
        if not self.current_state.selected_elements:
            return None
        
        bounds_list = []
        for element_id in self.current_state.selected_elements:
            element = self._get_element_by_id(element_id)
            if element:
                bounds_list.append(element.get_bounds())
        
        if not bounds_list:
            return None
        
        # Calculate union of all bounds
        min_x = min(b.x for b in bounds_list)
        min_y = min(b.y for b in bounds_list)
        max_x = max(b.x + b.width for b in bounds_list)
        max_y = max(b.y + b.height for b in bounds_list)
        
        return Rectangle(min_x, min_y, max_x - min_x, max_y - min_y)
    
    def add_selection_callback(self, callback: Callable) -> None:
        """Add a callback for selection change events."""
        self.selection_callbacks.append(callback)
    
    def remove_selection_callback(self, callback: Callable) -> None:
        """Remove a selection change callback."""
        if callback in self.selection_callbacks:
            self.selection_callbacks.remove(callback)
    
    def get_selection_metrics(self) -> Dict[str, Any]:
        """Get selection performance metrics."""
        return self.selection_metrics.copy()
    
    def _element_exists(self, element_id: str) -> bool:
        """Check if an element exists."""
        # Try cache first
        if element_id in self.element_cache:
            self.selection_metrics['cache_hits'] += 1
            return True
        
        # Check with overlay API
        if self.overlay_api:
            # This would need to be implemented in the overlay API
            # For now, assume element exists
            self.selection_metrics['cache_misses'] += 1
            return True
        
        return False
    
    def _get_element_by_id(self, element_id: str) -> Optional[LayerElement]:
        """Get an element by its ID."""
        # Try cache first
        if element_id in self.element_cache:
            return self.element_cache[element_id]
        
        # Would need to query from overlay API
        return None
    
    def _get_all_elements(self) -> List[LayerElement]:
        """Get all available elements."""
        if self.overlay_api:
            # Get all elements from all layers
            all_elements = []
            # This would need to be implemented in the overlay API
            return all_elements
        return []
    
    def _notify_selection_changed(self) -> None:
        """Notify all callbacks of selection changes."""
        for callback in self.selection_callbacks:
            try:
                callback(self.current_state)
            except Exception as e:
                # Log error but don't fail the selection
                print(f"Selection callback error: {e}")
    
    def _notify_mode_changed(self, mode: SelectionMode) -> None:
        """Notify callbacks of mode changes."""
        # TODO: Implement mode change notifications
        pass
    
    def _update_selection_metrics(self, selection_time: float) -> None:
        """Update selection performance metrics."""
        self.selection_metrics['selection_count'] += 1
        self.selection_metrics['last_selection_time'] = selection_time
        
        # Update average selection time
        count = self.selection_metrics['selection_count']
        current_avg = self.selection_metrics['average_selection_time']
        self.selection_metrics['average_selection_time'] = (
            (current_avg * (count - 1) + selection_time) / count
        )
    
    # Additional methods needed for state integration
    
    def get_current_state(self) -> SelectionState:
        """Get the current selection state."""
        return self.current_state.copy()
    
    def set_selection_mode(self, mode: SelectionMode) -> None:
        """Set the selection mode."""
        if self.current_state.mode != mode:
            self.current_state.mode = mode
            self.current_state.selection_mode = mode
            self._notify_mode_changed(mode)
    
    def set_selection_strategy(self, strategy) -> None:
        """Set the selection strategy."""
        if self.current_state.strategy != strategy:
            self.current_state.strategy = strategy
            self._notify_strategy_changed(strategy)
    
    def restore_selection_bounds(self, bounds_list: List[Rectangle]) -> None:
        """Restore selection from bounds list."""
        # Clear current selection
        self.current_state.selected_elements.clear()
        
        # Find elements that match the bounds
        for bounds in bounds_list:
            # This would need to query the overlay system for elements at these bounds
            matching_elements = self._find_elements_at_bounds(bounds)
            self.current_state.selected_elements.update(matching_elements)
        
        # Update selection bounds
        if bounds_list:
            # Calculate union of all bounds
            union_bounds = bounds_list[0]
            for bounds in bounds_list[1:]:
                union_bounds = union_bounds.union(bounds)
            self.current_state.selection_bounds = union_bounds
        
        self._notify_selection_changed()
    
    def _find_elements_at_bounds(self, bounds: Rectangle) -> Set[LayerElement]:
        """Find elements at the given bounds."""
        # This would need to query the overlay system
        # For now, return empty set
        return set()
    
    def _notify_strategy_changed(self, strategy) -> None:
        """Notify callbacks of strategy changes."""
        self.strategy_changed.emit(strategy)
    
    def initialize_overlay_integration(self, overlay_integration) -> None:
        """Initialize overlay integration and selection algorithms."""
        self.overlay_integration = overlay_integration
        
        # Import and initialize overlay-aware algorithms
        from .selection_algorithms import (
            RectangularSelector, PolygonSelector, LassoSelector,
            LayerSelector, TypeSelector, HybridSelector
        )
        
        self.algorithms = {
            SelectionMode.RECTANGULAR: RectangularSelector(overlay_integration),
            SelectionMode.POLYGON: PolygonSelector(overlay_integration),
            SelectionMode.LASSO: LassoSelector(overlay_integration),
            SelectionMode.LAYER: LayerSelector(overlay_integration),
            SelectionMode.TYPE: TypeSelector(overlay_integration)
        }
        
        # Initialize hybrid selector
        self.hybrid_selector = HybridSelector(overlay_integration)
    
    def select_with_overlay(self, selection_criteria: Dict[str, Any]) -> List[str]:
        """Select elements using overlay-aware algorithms."""
        if not self.overlay_integration:
            return []
        
        # Use hybrid selector for complex selections
        if hasattr(self, 'hybrid_selector'):
            selected_elements = self.hybrid_selector.select_hybrid(selection_criteria)
            
            # Convert to element IDs
            element_ids = [element.element_id for element in selected_elements]
            
            # Update current state
            self.current_state.selected_elements = set(selected_elements)
            self.current_state.timestamp = time.time()
            
            # Notify callbacks
            self._notify_selection_changed()
            
            return element_ids
        
        return []
    
    def _notify_selection_changed(self) -> None:
        """Notify all callbacks of selection changes."""
        for callback in self.selection_callbacks:
            try:
                callback(self.current_state)
            except Exception as e:
                # Log error but don't fail the selection
                print(f"Selection callback error: {e}")
        
        # Emit PyQt signal
        self.selection_changed.emit(self.current_state)
    
    def _notify_mode_changed(self, mode: SelectionMode) -> None:
        """Notify callbacks of mode changes."""
        self.mode_changed.emit(mode)
    
    def _notify_strategy_changed(self, strategy) -> None:
        """Notify callbacks of strategy changes."""
        self.strategy_changed.emit(strategy)