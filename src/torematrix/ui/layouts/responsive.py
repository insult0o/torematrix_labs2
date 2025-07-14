"""Advanced Responsive Design System for TORE Matrix Labs V3.

This module provides a comprehensive responsive design system with intelligent
breakpoint management, adaptive layouts, and performance-optimized responsive behavior.
"""

from typing import Dict, List, Optional, Set, Callable, Any, Union, Tuple
from enum import Enum, auto
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import logging
import time
from functools import lru_cache
import weakref

from PyQt6.QtWidgets import (
    QWidget, QLayout, QSizePolicy, QApplication, QVBoxLayout, QHBoxLayout,
    QGridLayout, QSplitter, QScrollArea, QFrame, QStackedWidget
)
from PyQt6.QtCore import (
    QObject, QSize, QRect, QTimer, pyqtSignal, QMargins, QThread,
    QMutex, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup
)
from PyQt6.QtGui import QResizeEvent, QScreen

from ...core.events import EventBus
from ...core.config import ConfigManager  
from ...core.state import StateManager
from ..base import BaseUIComponent

logger = logging.getLogger(__name__)


class ResponsiveMode(Enum):
    """Responsive behavior modes."""
    ADAPTIVE = auto()      # Automatic adaptation based on screen size
    MANUAL = auto()        # Manual control over responsive behavior  
    HYBRID = auto()        # Combination of automatic and manual control
    PERFORMANCE = auto()   # Performance-optimized mode with minimal adaptation


class LayoutDensity(Enum):
    """Layout density levels for different screen sizes."""
    COMPACT = auto()       # Minimal spacing, compact elements
    COMFORTABLE = auto()   # Standard spacing for good usability
    SPACIOUS = auto()      # Extra spacing for large screens


class TouchTarget(Enum):
    """Touch target size categories."""
    SMALL = 32      # Small touch targets (desktop)
    MEDIUM = 44     # Standard touch targets (tablets)
    LARGE = 56      # Large touch targets (mobile)


@dataclass
class ResponsiveMetrics:
    """Performance metrics for responsive operations."""
    adaptation_time_ms: float = 0.0
    layout_calculation_time_ms: float = 0.0
    widget_update_time_ms: float = 0.0
    memory_usage_mb: float = 0.0
    cache_hit_ratio: float = 0.0
    total_adaptations: int = 0
    failed_adaptations: int = 0


@dataclass
class ScreenProperties:
    """Comprehensive screen properties for responsive design."""
    width: int
    height: int
    dpi: float
    scale_factor: float
    is_touch_enabled: bool = False
    is_high_dpi: bool = False
    orientation: str = "landscape"  # "landscape" or "portrait"
    screen_name: str = "primary"
    
    def __post_init__(self):
        """Calculate derived properties."""
        self.aspect_ratio = self.width / self.height if self.height > 0 else 1.0
        self.is_high_dpi = self.dpi > 150
        self.orientation = "portrait" if self.height > self.width else "landscape"


@dataclass
class ResponsiveConstraints:
    """Advanced constraints for responsive behavior."""
    min_width: Optional[int] = None
    max_width: Optional[int] = None
    min_height: Optional[int] = None  
    max_height: Optional[int] = None
    aspect_ratio_range: Optional[Tuple[float, float]] = None
    density_requirements: Optional[Set[LayoutDensity]] = None
    touch_requirements: Optional[Set[TouchTarget]] = None
    performance_level: int = 1  # 1=basic, 2=standard, 3=advanced
    
    def satisfies_constraints(self, properties: ScreenProperties) -> bool:
        """Check if screen properties satisfy these constraints."""
        if self.min_width and properties.width < self.min_width:
            return False
        if self.max_width and properties.width > self.max_width:
            return False
        if self.min_height and properties.height < self.min_height:
            return False
        if self.max_height and properties.height > self.max_height:
            return False
        if self.aspect_ratio_range:
            min_ratio, max_ratio = self.aspect_ratio_range
            if not (min_ratio <= properties.aspect_ratio <= max_ratio):
                return False
        return True


class ResponsiveStrategy(ABC):
    """Abstract base class for responsive adaptation strategies."""
    
    @abstractmethod
    def calculate_layout(self, properties: ScreenProperties) -> Dict[str, Any]:
        """Calculate layout parameters for given screen properties."""
        pass
    
    @abstractmethod
    def get_priority(self) -> int:
        """Get strategy priority (higher = more preferred)."""
        pass
    
    @abstractmethod
    def can_handle(self, properties: ScreenProperties) -> bool:
        """Check if this strategy can handle the given screen properties."""
        pass


class MobileFirstStrategy(ResponsiveStrategy):
    """Mobile-first responsive strategy."""
    
    def calculate_layout(self, properties: ScreenProperties) -> Dict[str, Any]:
        """Calculate mobile-optimized layout."""
        return {
            'layout_type': 'stacked',
            'sidebar_collapsed': True,
            'toolbar_compact': True,
            'touch_targets': TouchTarget.LARGE,
            'density': LayoutDensity.COMPACT,
            'margins': QMargins(8, 8, 8, 8)
        }
    
    def get_priority(self) -> int:
        return 10
    
    def can_handle(self, properties: ScreenProperties) -> bool:
        return properties.width <= 768 or properties.is_touch_enabled


class DesktopStrategy(ResponsiveStrategy):
    """Desktop-optimized responsive strategy."""
    
    def calculate_layout(self, properties: ScreenProperties) -> Dict[str, Any]:
        """Calculate desktop-optimized layout."""
        return {
            'layout_type': 'split',
            'sidebar_collapsed': False,
            'toolbar_compact': False,
            'touch_targets': TouchTarget.SMALL,
            'density': LayoutDensity.COMFORTABLE,
            'margins': QMargins(12, 12, 12, 12)
        }
    
    def get_priority(self) -> int:
        return 5
    
    def can_handle(self, properties: ScreenProperties) -> bool:
        return properties.width > 1024 and not properties.is_touch_enabled


class TabletStrategy(ResponsiveStrategy):
    """Tablet-optimized responsive strategy."""
    
    def calculate_layout(self, properties: ScreenProperties) -> Dict[str, Any]:
        """Calculate tablet-optimized layout."""
        return {
            'layout_type': 'adaptive',
            'sidebar_collapsed': properties.orientation == 'portrait',
            'toolbar_compact': properties.orientation == 'portrait',
            'touch_targets': TouchTarget.MEDIUM,
            'density': LayoutDensity.COMFORTABLE,
            'margins': QMargins(10, 10, 10, 10)
        }
    
    def get_priority(self) -> int:
        return 7
    
    def can_handle(self, properties: ScreenProperties) -> bool:
        return (768 < properties.width <= 1024) and properties.is_touch_enabled


class ResponsiveLayoutEngine(QObject):
    """Advanced responsive layout engine with strategy pattern and performance optimization."""
    
    # Signals
    layout_adapted = pyqtSignal(ScreenProperties, dict)
    strategy_changed = pyqtSignal(str)
    performance_warning = pyqtSignal(str, float)
    
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        
        # Core properties
        self._strategies: List[ResponsiveStrategy] = []
        self._current_strategy: Optional[ResponsiveStrategy] = None
        self._screen_properties: Optional[ScreenProperties] = None
        self._layout_cache: Dict[str, Dict[str, Any]] = {}
        self._performance_metrics = ResponsiveMetrics()
        
        # Performance optimization
        self._cache_enabled = True
        self._cache_max_size = 100
        self._adaptation_throttle_ms = 50
        self._last_adaptation_time = 0.0
        
        # Thread safety
        self._mutex = QMutex()
        
        # Adaptation timer
        self._adaptation_timer = QTimer()
        self._adaptation_timer.setSingleShot(True)
        self._adaptation_timer.timeout.connect(self._perform_adaptation)
        
        # Initialize default strategies
        self._initialize_default_strategies()
        
        logger.debug("ResponsiveLayoutEngine initialized")
    
    def _initialize_default_strategies(self) -> None:
        """Initialize default responsive strategies."""
        self.add_strategy(MobileFirstStrategy())
        self.add_strategy(TabletStrategy())
        self.add_strategy(DesktopStrategy())
    
    def add_strategy(self, strategy: ResponsiveStrategy) -> None:
        """Add a responsive strategy."""
        with self._mutex:
            self._strategies.append(strategy)
            # Sort by priority (highest first)
            self._strategies.sort(key=lambda s: s.get_priority(), reverse=True)
        
        logger.debug(f"Added responsive strategy: {strategy.__class__.__name__}")
    
    def remove_strategy(self, strategy_class: type) -> bool:
        """Remove a responsive strategy by class."""
        with self._mutex:
            for i, strategy in enumerate(self._strategies):
                if isinstance(strategy, strategy_class):
                    del self._strategies[i]
                    logger.debug(f"Removed responsive strategy: {strategy_class.__name__}")
                    return True
        return False
    
    def update_screen_properties(self, properties: ScreenProperties) -> None:
        """Update screen properties and trigger adaptation if needed."""
        start_time = time.perf_counter()
        
        # Check if properties have changed significantly
        if self._screen_properties and self._properties_similar(self._screen_properties, properties):
            return
        
        self._screen_properties = properties
        
        # Throttle adaptations for performance
        current_time = time.perf_counter() * 1000  # Convert to milliseconds
        if current_time - self._last_adaptation_time < self._adaptation_throttle_ms:
            # Schedule delayed adaptation
            self._adaptation_timer.start(self._adaptation_throttle_ms)
            return
        
        self._last_adaptation_time = current_time
        self._perform_adaptation()
        
        # Track performance
        adaptation_time = (time.perf_counter() - start_time) * 1000
        self._performance_metrics.adaptation_time_ms = adaptation_time
        self._performance_metrics.total_adaptations += 1
        
        if adaptation_time > 100:  # Performance warning threshold
            self.performance_warning.emit("Slow adaptation detected", adaptation_time)
    
    def _properties_similar(self, props1: ScreenProperties, props2: ScreenProperties) -> bool:
        """Check if two screen properties are similar enough to skip adaptation."""
        width_diff = abs(props1.width - props2.width)
        height_diff = abs(props1.height - props2.height)
        
        # Skip if changes are minimal (less than 10px)
        return (width_diff < 10 and height_diff < 10 and 
                props1.orientation == props2.orientation)
    
    def _perform_adaptation(self) -> None:
        """Perform the actual layout adaptation."""
        if not self._screen_properties:
            return
        
        start_time = time.perf_counter()
        
        try:
            # Select best strategy
            strategy = self._select_strategy(self._screen_properties)
            if not strategy:
                logger.warning("No suitable responsive strategy found")
                self._performance_metrics.failed_adaptations += 1
                return
            
            # Check cache first
            cache_key = self._generate_cache_key(self._screen_properties)
            if self._cache_enabled and cache_key in self._layout_cache:
                layout_params = self._layout_cache[cache_key]
                self._performance_metrics.cache_hit_ratio = (
                    self._performance_metrics.cache_hit_ratio * 0.9 + 0.1
                )
            else:
                # Calculate new layout
                layout_params = strategy.calculate_layout(self._screen_properties)
                
                # Cache the result
                if self._cache_enabled:
                    self._cache_layout_params(cache_key, layout_params)
                    self._performance_metrics.cache_hit_ratio *= 0.9
            
            # Update current strategy if changed
            if strategy != self._current_strategy:
                self._current_strategy = strategy
                self.strategy_changed.emit(strategy.__class__.__name__)
            
            # Emit adaptation signal
            self.layout_adapted.emit(self._screen_properties, layout_params)
            
        except Exception as e:
            logger.error(f"Error during layout adaptation: {e}")
            self._performance_metrics.failed_adaptations += 1
        
        # Update performance metrics
        calculation_time = (time.perf_counter() - start_time) * 1000
        self._performance_metrics.layout_calculation_time_ms = calculation_time
    
    def _select_strategy(self, properties: ScreenProperties) -> Optional[ResponsiveStrategy]:
        """Select the best strategy for given screen properties."""
        with self._mutex:
            for strategy in self._strategies:
                if strategy.can_handle(properties):
                    return strategy
        return None
    
    def _generate_cache_key(self, properties: ScreenProperties) -> str:
        """Generate cache key for screen properties."""
        # Round values for better cache hits
        width_rounded = (properties.width // 50) * 50
        height_rounded = (properties.height // 50) * 50
        
        return f"{width_rounded}x{height_rounded}_{properties.orientation}_{properties.is_touch_enabled}"
    
    def _cache_layout_params(self, key: str, params: Dict[str, Any]) -> None:
        """Cache layout parameters with size management."""
        if len(self._layout_cache) >= self._cache_max_size:
            # Remove oldest entry (simple LRU)
            oldest_key = next(iter(self._layout_cache))
            del self._layout_cache[oldest_key]
        
        self._layout_cache[key] = params.copy()
    
    @lru_cache(maxsize=32)
    def get_optimal_touch_targets(self, screen_properties: ScreenProperties) -> TouchTarget:
        """Get optimal touch target size for screen properties."""
        if not screen_properties.is_touch_enabled:
            return TouchTarget.SMALL
        
        if screen_properties.width <= 480:
            return TouchTarget.LARGE
        elif screen_properties.width <= 768:
            return TouchTarget.MEDIUM
        else:
            return TouchTarget.SMALL
    
    @lru_cache(maxsize=32)
    def get_optimal_density(self, screen_properties: ScreenProperties) -> LayoutDensity:
        """Get optimal layout density for screen properties."""
        if screen_properties.width <= 480:
            return LayoutDensity.COMPACT
        elif screen_properties.width >= 1400:
            return LayoutDensity.SPACIOUS
        else:
            return LayoutDensity.COMFORTABLE
    
    def clear_cache(self) -> None:
        """Clear the layout parameter cache."""
        self._layout_cache.clear()
        # Clear LRU caches
        self.get_optimal_touch_targets.cache_clear()
        self.get_optimal_density.cache_clear()
        
        logger.debug("Responsive layout cache cleared")
    
    def set_cache_enabled(self, enabled: bool) -> None:
        """Enable or disable layout parameter caching."""
        self._cache_enabled = enabled
        if not enabled:
            self.clear_cache()
    
    def set_adaptation_throttle(self, throttle_ms: int) -> None:
        """Set adaptation throttle time in milliseconds."""
        self._adaptation_throttle_ms = max(0, throttle_ms)
    
    def get_performance_metrics(self) -> ResponsiveMetrics:
        """Get current performance metrics."""
        return self._performance_metrics
    
    def reset_performance_metrics(self) -> None:
        """Reset performance metrics."""
        self._performance_metrics = ResponsiveMetrics()
    
    def get_current_strategy(self) -> Optional[ResponsiveStrategy]:
        """Get the currently active strategy."""
        return self._current_strategy
    
    def get_screen_properties(self) -> Optional[ScreenProperties]:
        """Get current screen properties."""
        return self._screen_properties


class ResponsiveWidget(QWidget):
    """Enhanced responsive widget with advanced adaptation capabilities."""
    
    # Signals
    responsive_changed = pyqtSignal(dict)
    adaptation_completed = pyqtSignal(float)  # Adaptation time in ms
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self._responsive_engine = ResponsiveLayoutEngine(self)
        self._adaptation_enabled = True
        self._constraints = ResponsiveConstraints()
        self._responsive_mode = ResponsiveMode.ADAPTIVE
        
        # Performance tracking
        self._adaptation_count = 0
        self._total_adaptation_time = 0.0
        
        # Connect signals
        self._responsive_engine.layout_adapted.connect(self._handle_layout_adapted)
        self._responsive_engine.performance_warning.connect(self._handle_performance_warning)
        
        # Initialize screen properties
        self._update_screen_properties()
    
    def _update_screen_properties(self) -> None:
        """Update screen properties from current display."""
        app = QApplication.instance()
        if not app:
            return
        
        screen = app.primaryScreen()
        if not screen:
            return
        
        geometry = screen.geometry()
        dpi = screen.logicalDotsPerInch()
        scale_factor = screen.devicePixelRatio()
        
        # Detect touch capability (basic heuristic)
        is_touch = self._detect_touch_capability()
        
        properties = ScreenProperties(
            width=geometry.width(),
            height=geometry.height(), 
            dpi=dpi,
            scale_factor=scale_factor,
            is_touch_enabled=is_touch,
            screen_name=screen.name() or "primary"
        )
        
        self._responsive_engine.update_screen_properties(properties)
    
    def _detect_touch_capability(self) -> bool:
        """Detect if the device has touch capability."""
        # Simple heuristic - this could be enhanced with platform-specific detection
        app = QApplication.instance()
        if app:
            # Check for touch devices based on screen size and DPI
            screen = app.primaryScreen()
            if screen:
                geometry = screen.geometry()
                dpi = screen.logicalDotsPerInch()
                
                # Heuristic: high DPI with smaller screen often indicates touch
                return dpi > 150 and geometry.width() <= 1366
        
        return False
    
    def _handle_layout_adapted(self, properties: ScreenProperties, layout_params: Dict[str, Any]) -> None:
        """Handle layout adaptation from the engine."""
        if not self._adaptation_enabled:
            return
        
        start_time = time.perf_counter()
        
        try:
            self._apply_layout_parameters(layout_params)
            
            # Track performance
            adaptation_time = (time.perf_counter() - start_time) * 1000
            self._adaptation_count += 1
            self._total_adaptation_time += adaptation_time
            
            # Emit signals
            self.responsive_changed.emit(layout_params)
            self.adaptation_completed.emit(adaptation_time)
            
        except Exception as e:
            logger.error(f"Error applying responsive layout: {e}")
    
    def _apply_layout_parameters(self, params: Dict[str, Any]) -> None:
        """Apply layout parameters to the widget."""
        # Apply margins
        if 'margins' in params and isinstance(params['margins'], QMargins):
            layout = self.layout()
            if layout:
                layout.setContentsMargins(params['margins'])
        
        # Apply touch targets
        if 'touch_targets' in params:
            self._apply_touch_targets(params['touch_targets'])
        
        # Apply density
        if 'density' in params:
            self._apply_density_settings(params['density'])
        
        # Custom parameter handling can be extended here
        self._apply_custom_parameters(params)
    
    def _apply_touch_targets(self, touch_target: TouchTarget) -> None:
        """Apply touch target sizing."""
        min_size = QSize(touch_target.value, touch_target.value)
        
        # Find all interactive widgets and adjust their size
        from PyQt6.QtWidgets import QPushButton, QToolButton, QCheckBox, QRadioButton
        
        interactive_widgets = (
            self.findChildren(QPushButton) +
            self.findChildren(QToolButton) +
            self.findChildren(QCheckBox) +
            self.findChildren(QRadioButton)
        )
        
        for widget in interactive_widgets:
            current_size = widget.sizeHint()
            new_size = QSize(
                max(current_size.width(), min_size.width()),
                max(current_size.height(), min_size.height())
            )
            widget.setMinimumSize(new_size)
    
    def _apply_density_settings(self, density: LayoutDensity) -> None:
        """Apply layout density settings."""
        spacing_map = {
            LayoutDensity.COMPACT: 4,
            LayoutDensity.COMFORTABLE: 8,
            LayoutDensity.SPACIOUS: 16
        }
        
        spacing = spacing_map.get(density, 8)
        
        # Apply to all layouts
        for layout in self.findChildren(QLayout):
            if hasattr(layout, 'setSpacing'):
                layout.setSpacing(spacing)
    
    def _apply_custom_parameters(self, params: Dict[str, Any]) -> None:
        """Apply custom layout parameters (override in subclasses)."""
        pass
    
    def _handle_performance_warning(self, message: str, time_ms: float) -> None:
        """Handle performance warnings from the responsive engine."""
        logger.warning(f"Responsive performance warning: {message} ({time_ms:.1f}ms)")
    
    def resizeEvent(self, event: QResizeEvent) -> None:
        """Handle resize events with responsive adaptation."""
        super().resizeEvent(event)
        
        if self._responsive_mode == ResponsiveMode.ADAPTIVE:
            self._update_screen_properties()
    
    def set_responsive_mode(self, mode: ResponsiveMode) -> None:
        """Set the responsive mode."""
        self._responsive_mode = mode
        
        if mode == ResponsiveMode.ADAPTIVE:
            self._update_screen_properties()
    
    def set_responsive_constraints(self, constraints: ResponsiveConstraints) -> None:
        """Set responsive constraints."""
        self._constraints = constraints
    
    def enable_responsive_adaptation(self, enabled: bool) -> None:
        """Enable or disable responsive adaptation."""
        self._adaptation_enabled = enabled
    
    def get_adaptation_statistics(self) -> Dict[str, Any]:
        """Get adaptation performance statistics."""
        avg_time = (self._total_adaptation_time / self._adaptation_count 
                   if self._adaptation_count > 0 else 0.0)
        
        return {
            'adaptation_count': self._adaptation_count,
            'total_adaptation_time_ms': self._total_adaptation_time,
            'average_adaptation_time_ms': avg_time,
            'engine_metrics': self._responsive_engine.get_performance_metrics()
        }
    
    def reset_adaptation_statistics(self) -> None:
        """Reset adaptation statistics."""
        self._adaptation_count = 0
        self._total_adaptation_time = 0.0
        self._responsive_engine.reset_performance_metrics()