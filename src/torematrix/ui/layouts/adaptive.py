"""Adaptive Layout Algorithms for TORE Matrix Labs V3.

This module provides intelligent adaptive layout algorithms that automatically
adjust UI layouts based on screen size, content requirements, user preferences,
and performance constraints.
"""

from typing import Dict, List, Optional, Set, Callable, Any, Union, Tuple, Protocol
from enum import Enum, auto
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import logging
import math
import time
from functools import lru_cache
import weakref

from PyQt6.QtWidgets import (
    QWidget, QLayout, QVBoxLayout, QHBoxLayout, QGridLayout, QSplitter,
    QStackedWidget, QScrollArea, QFrame, QSizePolicy, QSpacerItem
)
from PyQt6.QtCore import (
    QObject, QSize, QRect, QMargins, QTimer, pyqtSignal, QPropertyAnimation,
    QEasingCurve, QParallelAnimationGroup, QThread
)
from PyQt6.QtGui import QResizeEvent

from ...core.events import EventBus
from ...core.config import ConfigurationManager
from ...core.state import Store
from .responsive import ScreenProperties, LayoutDensity, TouchTarget
from .breakpoints import BreakpointManager, DeviceClass, BreakpointType

logger = logging.getLogger(__name__)


class AdaptationStrategy(Enum):
    """Strategies for layout adaptation."""
    CONTENT_FIRST = auto()      # Prioritize content visibility and usability
    PERFORMANCE_FIRST = auto()  # Prioritize performance and responsiveness
    USER_PREFERENCE = auto()    # Follow user preferences and settings
    BALANCED = auto()           # Balance all factors
    ACCESSIBILITY_FIRST = auto() # Prioritize accessibility requirements


class LayoutDirection(Enum):
    """Layout direction options."""
    LEFT_TO_RIGHT = auto()
    RIGHT_TO_LEFT = auto()
    TOP_TO_BOTTOM = auto()
    BOTTOM_TO_TOP = auto()


class ContentPriority(Enum):
    """Content priority levels for adaptive layouts."""
    CRITICAL = 100     # Always visible, never hidden
    HIGH = 80         # Visible on medium+ screens
    MEDIUM = 60       # Visible on large+ screens
    LOW = 40          # Visible only on extra large screens
    OPTIONAL = 20     # Can be hidden/collapsed as needed


@dataclass
class LayoutConstraints:
    """Constraints for adaptive layout calculations."""
    min_content_width: int = 200
    max_content_width: int = 2000
    min_sidebar_width: int = 150
    max_sidebar_width: int = 400
    min_touch_target_size: int = 44
    max_columns: int = 12
    min_margins: int = 4
    max_margins: int = 32
    aspect_ratio_tolerance: float = 0.1
    performance_budget_ms: float = 16.0  # 60fps frame budget


@dataclass
class ContentItem:
    """Represents a content item in the adaptive layout."""
    widget: QWidget
    priority: ContentPriority
    min_size: QSize
    preferred_size: QSize
    max_size: Optional[QSize] = None
    stretch_factor: int = 1
    can_collapse: bool = True
    can_hide: bool = True
    requires_scroll: bool = False
    custom_adaptation: Optional[Callable[['AdaptiveLayout'], None]] = None


@dataclass
class LayoutSolution:
    """Represents a solution for adaptive layout."""
    layout_type: str
    widget_placements: Dict[QWidget, QRect]
    visibility_states: Dict[QWidget, bool]
    scroll_requirements: Dict[QWidget, bool]
    performance_score: float
    usability_score: float
    accessibility_score: float
    total_score: float
    adaptation_time_ms: float


class LayoutAlgorithm(ABC):
    """Abstract base class for layout algorithms."""
    
    @abstractmethod
    def calculate_layout(
        self,
        content_items: List[ContentItem],
        container_size: QSize,
        constraints: LayoutConstraints,
        screen_properties: ScreenProperties
    ) -> LayoutSolution:
        """Calculate optimal layout for given parameters."""
        pass
    
    @abstractmethod
    def get_algorithm_name(self) -> str:
        """Get the name of this algorithm."""
        pass
    
    @abstractmethod
    def supports_constraints(self, constraints: LayoutConstraints) -> bool:
        """Check if this algorithm supports the given constraints."""
        pass


class StackedLayoutAlgorithm(LayoutAlgorithm):
    """Algorithm for stacked (vertical) layouts optimized for mobile."""
    
    def calculate_layout(
        self,
        content_items: List[ContentItem],
        container_size: QSize,
        constraints: LayoutConstraints,
        screen_properties: ScreenProperties
    ) -> LayoutSolution:
        """Calculate stacked layout solution."""
        start_time = time.perf_counter()
        
        widget_placements = {}
        visibility_states = {}
        scroll_requirements = {}
        
        available_height = container_size.height() - (constraints.min_margins * 2)
        current_y = constraints.min_margins
        total_content_height = 0
        
        # Sort items by priority (highest first)
        sorted_items = sorted(content_items, key=lambda x: x.priority.value, reverse=True)
        
        # Calculate placements
        for item in sorted_items:
            if current_y >= container_size.height():
                # No more space - hide or scroll
                if item.can_hide:
                    visibility_states[item.widget] = False
                    continue
                else:
                    scroll_requirements[item.widget] = True
            
            # Calculate item height
            preferred_height = item.preferred_size.height()
            available_width = container_size.width() - (constraints.min_margins * 2)
            
            # Place item
            placement = QRect(
                constraints.min_margins,
                current_y,
                available_width,
                preferred_height
            )
            
            widget_placements[item.widget] = placement
            visibility_states[item.widget] = True
            scroll_requirements[item.widget] = False
            
            current_y += preferred_height + constraints.min_margins
            total_content_height += preferred_height
        
        # Calculate scores
        performance_score = self._calculate_performance_score(len(widget_placements))
        usability_score = self._calculate_usability_score(content_items, visibility_states)
        accessibility_score = self._calculate_accessibility_score(screen_properties, constraints)
        
        adaptation_time = (time.perf_counter() - start_time) * 1000
        
        return LayoutSolution(
            layout_type="stacked",
            widget_placements=widget_placements,
            visibility_states=visibility_states,
            scroll_requirements=scroll_requirements,
            performance_score=performance_score,
            usability_score=usability_score,
            accessibility_score=accessibility_score,
            total_score=(performance_score + usability_score + accessibility_score) / 3,
            adaptation_time_ms=adaptation_time
        )
    
    def get_algorithm_name(self) -> str:
        return "StackedLayout"
    
    def supports_constraints(self, constraints: LayoutConstraints) -> bool:
        return True  # Stacked layout is always supported
    
    def _calculate_performance_score(self, widget_count: int) -> float:
        """Calculate performance score based on complexity."""
        # Fewer widgets = better performance
        return max(0, 100 - (widget_count * 2))
    
    def _calculate_usability_score(
        self,
        content_items: List[ContentItem],
        visibility_states: Dict[QWidget, bool]
    ) -> float:
        """Calculate usability score based on content visibility."""
        total_priority = sum(item.priority.value for item in content_items)
        visible_priority = sum(
            item.priority.value for item in content_items
            if visibility_states.get(item.widget, False)
        )
        
        return (visible_priority / total_priority * 100) if total_priority > 0 else 0
    
    def _calculate_accessibility_score(
        self,
        screen_properties: ScreenProperties,
        constraints: LayoutConstraints
    ) -> float:
        """Calculate accessibility score."""
        score = 80  # Base score
        
        # Bonus for touch-friendly sizing
        if screen_properties.is_touch_enabled and constraints.min_touch_target_size >= 44:
            score += 20
        
        return min(100, score)


class SplitLayoutAlgorithm(LayoutAlgorithm):
    """Algorithm for split layouts optimized for desktop."""
    
    def calculate_layout(
        self,
        content_items: List[ContentItem],
        container_size: QSize,
        constraints: LayoutConstraints,
        screen_properties: ScreenProperties
    ) -> LayoutSolution:
        """Calculate split layout solution."""
        start_time = time.perf_counter()
        
        # Determine optimal split configuration
        split_config = self._calculate_optimal_split(content_items, container_size, constraints)
        
        widget_placements = {}
        visibility_states = {}
        scroll_requirements = {}
        
        # Calculate areas for each split region
        regions = self._calculate_split_regions(container_size, split_config, constraints)
        
        # Assign content to regions based on priority and size requirements
        content_assignments = self._assign_content_to_regions(content_items, regions, constraints)
        
        # Calculate final placements
        for region_name, items in content_assignments.items():
            region_rect = regions[region_name]
            self._layout_items_in_region(
                items, region_rect, widget_placements, visibility_states, 
                scroll_requirements, constraints
            )
        
        # Calculate scores
        performance_score = self._calculate_performance_score(split_config, len(widget_placements))
        usability_score = self._calculate_usability_score(content_items, visibility_states)
        accessibility_score = self._calculate_accessibility_score(screen_properties, constraints)
        
        adaptation_time = (time.perf_counter() - start_time) * 1000
        
        return LayoutSolution(
            layout_type="split",
            widget_placements=widget_placements,
            visibility_states=visibility_states,
            scroll_requirements=scroll_requirements,
            performance_score=performance_score,
            usability_score=usability_score,
            accessibility_score=accessibility_score,
            total_score=(performance_score + usability_score + accessibility_score) / 3,
            adaptation_time_ms=adaptation_time
        )
    
    def get_algorithm_name(self) -> str:
        return "SplitLayout"
    
    def supports_constraints(self, constraints: LayoutConstraints) -> bool:
        return constraints.min_content_width <= 600  # Needs reasonable minimum width
    
    def _calculate_optimal_split(
        self,
        content_items: List[ContentItem],
        container_size: QSize,
        constraints: LayoutConstraints
    ) -> Dict[str, Any]:
        """Calculate optimal split configuration."""
        # Determine if we should use 2-column or 3-column layout
        total_width = container_size.width()
        
        if total_width >= 1200:
            return {
                'type': '3-column',
                'left_ratio': 0.25,
                'center_ratio': 0.5,
                'right_ratio': 0.25
            }
        elif total_width >= 768:
            return {
                'type': '2-column',
                'left_ratio': 0.3,
                'right_ratio': 0.7
            }
        else:
            return {
                'type': '1-column',
                'main_ratio': 1.0
            }
    
    def _calculate_split_regions(
        self,
        container_size: QSize,
        split_config: Dict[str, Any],
        constraints: LayoutConstraints
    ) -> Dict[str, QRect]:
        """Calculate regions for split layout."""
        regions = {}
        margin = constraints.min_margins
        
        if split_config['type'] == '3-column':
            left_width = int(container_size.width() * split_config['left_ratio']) - margin
            center_width = int(container_size.width() * split_config['center_ratio']) - margin
            right_width = container_size.width() - left_width - center_width - (margin * 3)
            
            regions['left'] = QRect(margin, margin, left_width, container_size.height() - margin * 2)
            regions['center'] = QRect(left_width + margin * 2, margin, center_width, container_size.height() - margin * 2)
            regions['right'] = QRect(left_width + center_width + margin * 3, margin, right_width, container_size.height() - margin * 2)
            
        elif split_config['type'] == '2-column':
            left_width = int(container_size.width() * split_config['left_ratio']) - margin
            right_width = container_size.width() - left_width - (margin * 3)
            
            regions['left'] = QRect(margin, margin, left_width, container_size.height() - margin * 2)
            regions['right'] = QRect(left_width + margin * 2, margin, right_width, container_size.height() - margin * 2)
            
        else:  # 1-column
            main_width = container_size.width() - (margin * 2)
            regions['main'] = QRect(margin, margin, main_width, container_size.height() - margin * 2)
        
        return regions
    
    def _assign_content_to_regions(
        self,
        content_items: List[ContentItem],
        regions: Dict[str, QRect],
        constraints: LayoutConstraints
    ) -> Dict[str, List[ContentItem]]:
        """Assign content items to layout regions."""
        assignments = {region: [] for region in regions.keys()}
        
        # Sort items by priority
        sorted_items = sorted(content_items, key=lambda x: x.priority.value, reverse=True)
        
        # Simple assignment strategy - can be enhanced
        region_names = list(regions.keys())
        
        for i, item in enumerate(sorted_items):
            region_index = i % len(region_names)
            region_name = region_names[region_index]
            assignments[region_name].append(item)
        
        return assignments
    
    def _layout_items_in_region(
        self,
        items: List[ContentItem],
        region_rect: QRect,
        widget_placements: Dict[QWidget, QRect],
        visibility_states: Dict[QWidget, bool],
        scroll_requirements: Dict[QWidget, bool],
        constraints: LayoutConstraints
    ) -> None:
        """Layout items within a specific region."""
        if not items:
            return
        
        available_height = region_rect.height()
        item_height = available_height // len(items) if items else available_height
        
        current_y = region_rect.y()
        
        for item in items:
            placement = QRect(
                region_rect.x(),
                current_y,
                region_rect.width(),
                min(item_height, item.preferred_size.height())
            )
            
            widget_placements[item.widget] = placement
            visibility_states[item.widget] = True
            scroll_requirements[item.widget] = False
            
            current_y += placement.height()
    
    def _calculate_performance_score(self, split_config: Dict[str, Any], widget_count: int) -> float:
        """Calculate performance score for split layout."""
        base_score = 90
        
        # Penalty for complex layouts
        if split_config['type'] == '3-column':
            base_score -= 10
        
        # Penalty for too many widgets
        widget_penalty = min(30, widget_count * 1.5)
        
        return max(0, base_score - widget_penalty)
    
    def _calculate_usability_score(
        self,
        content_items: List[ContentItem],
        visibility_states: Dict[QWidget, bool]
    ) -> float:
        """Calculate usability score for split layout."""
        total_priority = sum(item.priority.value for item in content_items)
        visible_priority = sum(
            item.priority.value for item in content_items
            if visibility_states.get(item.widget, False)
        )
        
        base_score = (visible_priority / total_priority * 100) if total_priority > 0 else 0
        
        # Bonus for split layout usability
        return min(100, base_score + 10)
    
    def _calculate_accessibility_score(
        self,
        screen_properties: ScreenProperties,
        constraints: LayoutConstraints
    ) -> float:
        """Calculate accessibility score for split layout."""
        score = 85  # Base score for split layout
        
        # Bonus for adequate spacing
        if constraints.min_margins >= 8:
            score += 10
        
        # Penalty for touch devices (split layout can be hard on touch)
        if screen_properties.is_touch_enabled:
            score -= 15
        
        return max(0, min(100, score))


class GridLayoutAlgorithm(LayoutAlgorithm):
    """Algorithm for grid-based layouts."""
    
    def calculate_layout(
        self,
        content_items: List[ContentItem],
        container_size: QSize,
        constraints: LayoutConstraints,
        screen_properties: ScreenProperties
    ) -> LayoutSolution:
        """Calculate grid layout solution."""
        start_time = time.perf_counter()
        
        # Calculate optimal grid configuration
        grid_config = self._calculate_optimal_grid(content_items, container_size, constraints)
        
        widget_placements = {}
        visibility_states = {}
        scroll_requirements = {}
        
        # Calculate cell size
        cell_width = container_size.width() // grid_config['columns']
        cell_height = container_size.height() // grid_config['rows']
        
        # Place items in grid
        for i, item in enumerate(content_items):
            if i >= grid_config['columns'] * grid_config['rows']:
                # Not enough grid space
                if item.can_hide:
                    visibility_states[item.widget] = False
                    continue
                else:
                    scroll_requirements[item.widget] = True
            
            row = i // grid_config['columns']
            col = i % grid_config['columns']
            
            placement = QRect(
                col * cell_width,
                row * cell_height,
                cell_width - constraints.min_margins,
                cell_height - constraints.min_margins
            )
            
            widget_placements[item.widget] = placement
            visibility_states[item.widget] = True
            scroll_requirements[item.widget] = False
        
        # Calculate scores
        performance_score = self._calculate_performance_score(grid_config)
        usability_score = self._calculate_usability_score(content_items, visibility_states)
        accessibility_score = self._calculate_accessibility_score(screen_properties, constraints)
        
        adaptation_time = (time.perf_counter() - start_time) * 1000
        
        return LayoutSolution(
            layout_type="grid",
            widget_placements=widget_placements,
            visibility_states=visibility_states,
            scroll_requirements=scroll_requirements,
            performance_score=performance_score,
            usability_score=usability_score,
            accessibility_score=accessibility_score,
            total_score=(performance_score + usability_score + accessibility_score) / 3,
            adaptation_time_ms=adaptation_time
        )
    
    def get_algorithm_name(self) -> str:
        return "GridLayout"
    
    def supports_constraints(self, constraints: LayoutConstraints) -> bool:
        return constraints.max_columns >= 2
    
    def _calculate_optimal_grid(
        self,
        content_items: List[ContentItem],
        container_size: QSize,
        constraints: LayoutConstraints
    ) -> Dict[str, int]:
        """Calculate optimal grid dimensions."""
        item_count = len(content_items)
        
        # Calculate columns based on container width
        min_item_width = min((item.min_size.width() for item in content_items), default=200)
        max_columns = min(constraints.max_columns, container_size.width() // min_item_width)
        
        # Calculate optimal columns (try to make grid roughly square)
        optimal_columns = min(max_columns, math.ceil(math.sqrt(item_count)))
        optimal_rows = math.ceil(item_count / optimal_columns)
        
        return {
            'columns': max(1, optimal_columns),
            'rows': max(1, optimal_rows)
        }
    
    def _calculate_performance_score(self, grid_config: Dict[str, int]) -> float:
        """Calculate performance score for grid layout."""
        total_cells = grid_config['columns'] * grid_config['rows']
        
        # Grid layout performance decreases with cell count
        return max(0, 100 - (total_cells * 2))
    
    def _calculate_usability_score(
        self,
        content_items: List[ContentItem],
        visibility_states: Dict[QWidget, bool]
    ) -> float:
        """Calculate usability score for grid layout."""
        total_priority = sum(item.priority.value for item in content_items)
        visible_priority = sum(
            item.priority.value for item in content_items
            if visibility_states.get(item.widget, False)
        )
        
        return (visible_priority / total_priority * 100) if total_priority > 0 else 0
    
    def _calculate_accessibility_score(
        self,
        screen_properties: ScreenProperties,
        constraints: LayoutConstraints
    ) -> float:
        """Calculate accessibility score for grid layout."""
        score = 75  # Base score
        
        # Bonus for touch-friendly grids
        if screen_properties.is_touch_enabled and constraints.min_touch_target_size >= 44:
            score += 15
        
        return min(100, score)


class AdaptiveLayoutEngine(QObject):
    """Main engine for adaptive layout calculations and management."""
    
    # Signals
    layout_calculated = pyqtSignal(LayoutSolution)
    algorithm_changed = pyqtSignal(str)
    adaptation_failed = pyqtSignal(str)
    
    def __init__(
        self,
        breakpoint_manager: BreakpointManager,
        parent: Optional[QObject] = None
    ):
        super().__init__(parent)
        
        self._breakpoint_manager = breakpoint_manager
        self._algorithms: Dict[str, LayoutAlgorithm] = {}
        self._current_algorithm: Optional[LayoutAlgorithm] = None
        self._adaptation_strategy = AdaptationStrategy.BALANCED
        
        # Performance tracking
        self._solution_cache: Dict[str, LayoutSolution] = {}
        self._cache_max_size = 50
        self._performance_metrics: Dict[str, float] = {}
        
        # Content management
        self._content_items: List[ContentItem] = []
        self._layout_constraints = LayoutConstraints()
        
        # Initialize algorithms
        self._initialize_algorithms()
        
        logger.debug("AdaptiveLayoutEngine initialized")
    
    def _initialize_algorithms(self) -> None:
        """Initialize layout algorithms."""
        self.add_algorithm(StackedLayoutAlgorithm())
        self.add_algorithm(SplitLayoutAlgorithm())
        self.add_algorithm(GridLayoutAlgorithm())
    
    def add_algorithm(self, algorithm: LayoutAlgorithm) -> None:
        """Add a layout algorithm."""
        self._algorithms[algorithm.get_algorithm_name()] = algorithm
        logger.debug(f"Added layout algorithm: {algorithm.get_algorithm_name()}")
    
    def remove_algorithm(self, algorithm_name: str) -> bool:
        """Remove a layout algorithm."""
        if algorithm_name in self._algorithms:
            del self._algorithms[algorithm_name]
            logger.debug(f"Removed layout algorithm: {algorithm_name}")
            return True
        return False
    
    def set_content_items(self, content_items: List[ContentItem]) -> None:
        """Set the content items to be laid out."""
        self._content_items = content_items.copy()
        self._invalidate_cache()
    
    def add_content_item(self, content_item: ContentItem) -> None:
        """Add a content item."""
        self._content_items.append(content_item)
        self._invalidate_cache()
    
    def remove_content_item(self, widget: QWidget) -> bool:
        """Remove a content item by widget."""
        for i, item in enumerate(self._content_items):
            if item.widget == widget:
                del self._content_items[i]
                self._invalidate_cache()
                return True
        return False
    
    def set_layout_constraints(self, constraints: LayoutConstraints) -> None:
        """Set layout constraints."""
        self._layout_constraints = constraints
        self._invalidate_cache()
    
    def set_adaptation_strategy(self, strategy: AdaptationStrategy) -> None:
        """Set the adaptation strategy."""
        self._adaptation_strategy = strategy
        logger.debug(f"Adaptation strategy set to: {strategy.name}")
    
    def calculate_adaptive_layout(
        self,
        container_size: QSize,
        screen_properties: ScreenProperties
    ) -> Optional[LayoutSolution]:
        """Calculate the best adaptive layout for current conditions."""
        if not self._content_items:
            return None
        
        # Check cache first
        cache_key = self._generate_cache_key(container_size, screen_properties)
        if cache_key in self._solution_cache:
            return self._solution_cache[cache_key]
        
        start_time = time.perf_counter()
        
        try:
            # Select best algorithm
            algorithm = self._select_best_algorithm(container_size, screen_properties)
            if not algorithm:
                self.adaptation_failed.emit("No suitable algorithm found")
                return None
            
            # Calculate layout
            solution = algorithm.calculate_layout(
                self._content_items,
                container_size,
                self._layout_constraints,
                screen_properties
            )
            
            # Apply strategy-specific adjustments
            solution = self._apply_strategy_adjustments(solution, screen_properties)
            
            # Cache the solution
            self._cache_solution(cache_key, solution)
            
            # Update current algorithm
            if algorithm != self._current_algorithm:
                self._current_algorithm = algorithm
                self.algorithm_changed.emit(algorithm.get_algorithm_name())
            
            # Update performance metrics
            total_time = (time.perf_counter() - start_time) * 1000
            self._performance_metrics[algorithm.get_algorithm_name()] = total_time
            
            self.layout_calculated.emit(solution)
            return solution
            
        except Exception as e:
            logger.error(f"Error calculating adaptive layout: {e}")
            self.adaptation_failed.emit(str(e))
            return None
    
    def _select_best_algorithm(
        self,
        container_size: QSize,
        screen_properties: ScreenProperties
    ) -> Optional[LayoutAlgorithm]:
        """Select the best algorithm for current conditions."""
        # Evaluate all algorithms
        algorithm_scores = {}
        
        for name, algorithm in self._algorithms.items():
            if not algorithm.supports_constraints(self._layout_constraints):
                continue
            
            score = self._evaluate_algorithm_fitness(algorithm, container_size, screen_properties)
            algorithm_scores[name] = (algorithm, score)
        
        if not algorithm_scores:
            return None
        
        # Select algorithm with highest score
        best_name = max(algorithm_scores.keys(), key=lambda k: algorithm_scores[k][1])
        return algorithm_scores[best_name][0]
    
    def _evaluate_algorithm_fitness(
        self,
        algorithm: LayoutAlgorithm,
        container_size: QSize,
        screen_properties: ScreenProperties
    ) -> float:
        """Evaluate how well an algorithm fits current conditions."""
        score = 0.0
        
        # Base scores for different screen sizes
        if isinstance(algorithm, StackedLayoutAlgorithm):
            if screen_properties.width <= 768:
                score += 50  # Excellent for mobile
            elif screen_properties.is_touch_enabled:
                score += 30  # Good for touch
            else:
                score += 10  # Poor for desktop
        
        elif isinstance(algorithm, SplitLayoutAlgorithm):
            if screen_properties.width >= 1024:
                score += 50  # Excellent for desktop
            elif screen_properties.width >= 768:
                score += 30  # Good for tablets
            else:
                score += 5   # Poor for mobile
        
        elif isinstance(algorithm, GridLayoutAlgorithm):
            if 768 <= screen_properties.width <= 1200:
                score += 40  # Good for medium screens
            else:
                score += 20  # Decent for others
        
        # Adjust based on adaptation strategy
        if self._adaptation_strategy == AdaptationStrategy.PERFORMANCE_FIRST:
            # Prefer simpler algorithms
            if isinstance(algorithm, StackedLayoutAlgorithm):
                score += 20
        elif self._adaptation_strategy == AdaptationStrategy.ACCESSIBILITY_FIRST:
            # Prefer touch-friendly algorithms
            if screen_properties.is_touch_enabled:
                if isinstance(algorithm, StackedLayoutAlgorithm):
                    score += 25
        
        return score
    
    def _apply_strategy_adjustments(
        self,
        solution: LayoutSolution,
        screen_properties: ScreenProperties
    ) -> LayoutSolution:
        """Apply strategy-specific adjustments to the layout solution."""
        # Create a copy of the solution for modifications
        adjusted_solution = LayoutSolution(
            layout_type=solution.layout_type,
            widget_placements=solution.widget_placements.copy(),
            visibility_states=solution.visibility_states.copy(),
            scroll_requirements=solution.scroll_requirements.copy(),
            performance_score=solution.performance_score,
            usability_score=solution.usability_score,
            accessibility_score=solution.accessibility_score,
            total_score=solution.total_score,
            adaptation_time_ms=solution.adaptation_time_ms
        )
        
        # Apply strategy-specific modifications
        if self._adaptation_strategy == AdaptationStrategy.PERFORMANCE_FIRST:
            # Hide less important items to improve performance
            self._optimize_for_performance(adjusted_solution)
        
        elif self._adaptation_strategy == AdaptationStrategy.ACCESSIBILITY_FIRST:
            # Ensure all items meet accessibility standards
            self._optimize_for_accessibility(adjusted_solution, screen_properties)
        
        elif self._adaptation_strategy == AdaptationStrategy.CONTENT_FIRST:
            # Prioritize content visibility
            self._optimize_for_content(adjusted_solution)
        
        # Recalculate total score
        adjusted_solution.total_score = (
            adjusted_solution.performance_score +
            adjusted_solution.usability_score +
            adjusted_solution.accessibility_score
        ) / 3
        
        return adjusted_solution
    
    def _optimize_for_performance(self, solution: LayoutSolution) -> None:
        """Optimize solution for performance."""
        # Hide low-priority items if there are too many visible items
        visible_count = sum(1 for visible in solution.visibility_states.values() if visible)
        
        if visible_count > 10:  # Performance threshold
            # Find low-priority items to hide
            low_priority_items = [
                item for item in self._content_items
                if (item.priority.value < ContentPriority.MEDIUM.value and
                    solution.visibility_states.get(item.widget, True) and
                    item.can_hide)
            ]
            
            # Hide some low-priority items
            items_to_hide = min(5, len(low_priority_items))
            for item in low_priority_items[:items_to_hide]:
                solution.visibility_states[item.widget] = False
                if item.widget in solution.widget_placements:
                    del solution.widget_placements[item.widget]
        
        # Increase performance score
        solution.performance_score = min(100, solution.performance_score + 10)
    
    def _optimize_for_accessibility(self, solution: LayoutSolution, screen_properties: ScreenProperties) -> None:
        """Optimize solution for accessibility."""
        # Ensure touch targets are large enough
        if screen_properties.is_touch_enabled:
            min_touch_size = QSize(44, 44)
            
            for widget, rect in solution.widget_placements.items():
                if rect.width() < min_touch_size.width() or rect.height() < min_touch_size.height():
                    # Expand touch target
                    new_rect = QRect(rect)
                    new_rect.setWidth(max(rect.width(), min_touch_size.width()))
                    new_rect.setHeight(max(rect.height(), min_touch_size.height()))
                    solution.widget_placements[widget] = new_rect
        
        # Increase accessibility score
        solution.accessibility_score = min(100, solution.accessibility_score + 15)
    
    def _optimize_for_content(self, solution: LayoutSolution) -> None:
        """Optimize solution for content visibility."""
        # Ensure high-priority content is always visible
        for item in self._content_items:
            if item.priority.value >= ContentPriority.HIGH.value:
                solution.visibility_states[item.widget] = True
                
                # If not placed, add basic placement
                if item.widget not in solution.widget_placements:
                    # Simple placement at bottom
                    solution.widget_placements[item.widget] = QRect(
                        0, 0, item.preferred_size.width(), item.preferred_size.height()
                    )
        
        # Increase usability score
        solution.usability_score = min(100, solution.usability_score + 10)
    
    def _generate_cache_key(self, container_size: QSize, screen_properties: ScreenProperties) -> str:
        """Generate cache key for layout solutions."""
        content_hash = hash(tuple(id(item.widget) for item in self._content_items))
        constraints_hash = hash(str(self._layout_constraints))
        
        return (f"{container_size.width()}x{container_size.height()}_"
                f"{screen_properties.width}x{screen_properties.height}_"
                f"{content_hash}_{constraints_hash}_{self._adaptation_strategy.name}")
    
    def _cache_solution(self, key: str, solution: LayoutSolution) -> None:
        """Cache a layout solution."""
        if len(self._solution_cache) >= self._cache_max_size:
            # Remove oldest entry
            oldest_key = next(iter(self._solution_cache))
            del self._solution_cache[oldest_key]
        
        self._solution_cache[key] = solution
    
    def _invalidate_cache(self) -> None:
        """Invalidate the solution cache."""
        self._solution_cache.clear()
    
    def get_performance_metrics(self) -> Dict[str, float]:
        """Get performance metrics for all algorithms."""
        return self._performance_metrics.copy()
    
    def get_current_algorithm(self) -> Optional[LayoutAlgorithm]:
        """Get the currently active algorithm."""
        return self._current_algorithm
    
    def get_available_algorithms(self) -> List[str]:
        """Get list of available algorithm names."""
        return list(self._algorithms.keys())


class AdaptiveLayout(QObject):
    """High-level adaptive layout manager that integrates with the Qt layout system."""
    
    def __init__(
        self,
        container: QWidget,
        breakpoint_manager: BreakpointManager,
        parent: Optional[QObject] = None
    ):
        super().__init__(parent)
        
        self._container = container
        self._breakpoint_manager = breakpoint_manager
        self._engine = AdaptiveLayoutEngine(breakpoint_manager, self)
        
        # Current state
        self._current_solution: Optional[LayoutSolution] = None
        self._adaptation_enabled = True
        
        # Connect signals
        self._engine.layout_calculated.connect(self._apply_layout_solution)
        self._breakpoint_manager.breakpoint_changed.connect(self._on_breakpoint_changed)
        
        logger.debug("AdaptiveLayout initialized")
    
    def add_widget(
        self,
        widget: QWidget,
        priority: ContentPriority = ContentPriority.MEDIUM,
        can_collapse: bool = True,
        can_hide: bool = True
    ) -> None:
        """Add a widget to the adaptive layout."""
        content_item = ContentItem(
            widget=widget,
            priority=priority,
            min_size=widget.minimumSizeHint(),
            preferred_size=widget.sizeHint(),
            max_size=widget.maximumSize() if widget.maximumSize().isValid() else None,
            can_collapse=can_collapse,
            can_hide=can_hide
        )
        
        self._engine.add_content_item(content_item)
        
        # Trigger layout update
        if self._adaptation_enabled:
            self._update_layout()
    
    def remove_widget(self, widget: QWidget) -> bool:
        """Remove a widget from the adaptive layout."""
        success = self._engine.remove_content_item(widget)
        
        if success and self._adaptation_enabled:
            self._update_layout()
        
        return success
    
    def set_adaptation_strategy(self, strategy: AdaptationStrategy) -> None:
        """Set the adaptation strategy."""
        self._engine.set_adaptation_strategy(strategy)
        
        if self._adaptation_enabled:
            self._update_layout()
    
    def enable_adaptation(self, enabled: bool) -> None:
        """Enable or disable adaptive layout."""
        self._adaptation_enabled = enabled
        
        if enabled:
            self._update_layout()
    
    def _update_layout(self) -> None:
        """Update the adaptive layout."""
        if not self._container:
            return
        
        # Get current screen properties
        container_size = self._container.size()
        
        # Create screen properties from current display
        app = QApplication.instance()
        screen = app.primaryScreen() if app else None
        
        if screen:
            screen_properties = ScreenProperties(
                width=container_size.width(),
                height=container_size.height(),
                dpi=screen.logicalDotsPerInch(),
                scale_factor=screen.devicePixelRatio(),
                is_touch_enabled=False  # Could be enhanced with touch detection
            )
        else:
            screen_properties = ScreenProperties(
                width=container_size.width(),
                height=container_size.height(),
                dpi=96.0,
                scale_factor=1.0
            )
        
        # Calculate layout
        self._engine.calculate_adaptive_layout(container_size, screen_properties)
    
    def _apply_layout_solution(self, solution: LayoutSolution) -> None:
        """Apply a calculated layout solution."""
        self._current_solution = solution
        
        # Apply widget placements
        for widget, rect in solution.widget_placements.items():
            widget.setGeometry(rect)
        
        # Apply visibility states
        for widget, visible in solution.visibility_states.items():
            widget.setVisible(visible)
        
        # Handle scroll requirements (could be enhanced)
        for widget, needs_scroll in solution.scroll_requirements.items():
            if needs_scroll:
                # Could wrap widget in scroll area
                pass
        
        logger.debug(f"Applied {solution.layout_type} layout with score: {solution.total_score:.1f}")
    
    def _on_breakpoint_changed(self, event) -> None:
        """Handle breakpoint changes."""
        if self._adaptation_enabled:
            self._update_layout()
    
    def get_current_solution(self) -> Optional[LayoutSolution]:
        """Get the current layout solution."""
        return self._current_solution
    
    def force_layout_update(self) -> None:
        """Force a layout update."""
        self._update_layout()