"""Advanced Breakpoint Management System for TORE Matrix Labs V3.

This module provides intelligent breakpoint detection, management, and optimization
for responsive layouts with support for custom breakpoints, device profiles, and
performance-optimized breakpoint calculations.
"""

from typing import Dict, List, Optional, Set, Callable, Any, Union, Tuple, NamedTuple
from enum import Enum, auto
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import logging
import json
import bisect
from functools import lru_cache
import weakref

from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import QObject, QSize, QTimer, pyqtSignal, QSettings
from PyQt6.QtGui import QScreen

from ...core.events import EventBus
from ...core.config import ConfigurationManager
from ...core.state import Store

logger = logging.getLogger(__name__)


class BreakpointType(Enum):
    """Types of breakpoints in the responsive system."""
    DEVICE_WIDTH = auto()      # Based on device screen width
    CONTAINER_WIDTH = auto()   # Based on container widget width
    VIEWPORT_WIDTH = auto()    # Based on viewport/window width
    ASPECT_RATIO = auto()      # Based on aspect ratio changes
    DPI_SCALING = auto()       # Based on DPI/scaling changes
    ORIENTATION = auto()       # Based on orientation changes


class DeviceClass(Enum):
    """Device classifications for responsive design."""
    MOBILE_PORTRAIT = "mobile_portrait"
    MOBILE_LANDSCAPE = "mobile_landscape"
    TABLET_PORTRAIT = "tablet_portrait"
    TABLET_LANDSCAPE = "tablet_landscape"
    DESKTOP_SMALL = "desktop_small"
    DESKTOP_MEDIUM = "desktop_medium"
    DESKTOP_LARGE = "desktop_large"
    DESKTOP_ULTRAWIDE = "desktop_ultrawide"


@dataclass
class BreakpointDefinition:
    """Definition of a responsive breakpoint."""
    name: str
    type: BreakpointType
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    device_classes: Set[DeviceClass] = field(default_factory=set)
    priority: int = 0
    custom_condition: Optional[Callable[[Dict[str, Any]], bool]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate breakpoint definition."""
        if self.min_value is not None and self.max_value is not None:
            if self.min_value >= self.max_value:
                raise ValueError(f"Invalid breakpoint range: {self.min_value} >= {self.max_value}")
    
    def matches(self, value: float, context: Dict[str, Any] = None) -> bool:
        """Check if a value matches this breakpoint."""
        # Check value range
        if self.min_value is not None and value < self.min_value:
            return False
        if self.max_value is not None and value > self.max_value:
            return False
        
        # Check custom condition
        if self.custom_condition and context:
            try:
                return self.custom_condition(context)
            except Exception as e:
                logger.warning(f"Error in custom breakpoint condition: {e}")
                return False
        
        return True


class BreakpointEvent(NamedTuple):
    """Event triggered when a breakpoint changes."""
    old_breakpoint: Optional[str]
    new_breakpoint: str
    breakpoint_type: BreakpointType
    trigger_value: float
    timestamp: float
    context: Dict[str, Any]


@dataclass
class DeviceProfile:
    """Profile for different device types with optimal breakpoints."""
    name: str
    device_class: DeviceClass
    typical_widths: List[int]
    typical_heights: List[int]
    typical_dpi_range: Tuple[int, int]
    touch_enabled: bool
    preferred_breakpoints: List[str]
    optimization_hints: Dict[str, Any] = field(default_factory=dict)


class BreakpointCalculator:
    """Calculates optimal breakpoints based on content and constraints."""
    
    def __init__(self):
        self._content_analysis_cache: Dict[str, List[int]] = {}
        self._calculation_cache: Dict[str, List[BreakpointDefinition]] = {}
    
    def calculate_content_breakpoints(
        self,
        content_widths: List[int],
        min_items_per_row: int = 1,
        max_items_per_row: int = 6,
        margin: int = 16
    ) -> List[int]:
        """Calculate breakpoints based on content layout requirements."""
        if not content_widths:
            return []
        
        cache_key = f"{hash(tuple(content_widths))}_{min_items_per_row}_{max_items_per_row}_{margin}"
        if cache_key in self._content_analysis_cache:
            return self._content_analysis_cache[cache_key]
        
        breakpoints = []
        typical_content_width = sum(content_widths) / len(content_widths)
        
        # Calculate breakpoints for different numbers of items per row
        for items_per_row in range(min_items_per_row, max_items_per_row + 1):
            total_width = (typical_content_width * items_per_row + 
                          margin * (items_per_row + 1))
            breakpoints.append(int(total_width))
        
        # Remove duplicates and sort
        breakpoints = sorted(set(breakpoints))
        
        self._content_analysis_cache[cache_key] = breakpoints
        return breakpoints
    
    def calculate_natural_breakpoints(
        self,
        widget_sizes: List[QSize],
        container_constraints: Optional[Tuple[int, int]] = None
    ) -> List[BreakpointDefinition]:
        """Calculate natural breakpoints based on widget sizing requirements."""
        if not widget_sizes:
            return []
        
        # Analyze widget size patterns
        widths = [size.width() for size in widget_sizes]
        heights = [size.height() for size in widget_sizes]
        
        # Find natural clustering points
        width_clusters = self._find_clusters(widths)
        
        breakpoints = []
        for i, cluster_width in enumerate(width_clusters):
            breakpoint = BreakpointDefinition(
                name=f"natural_{i}",
                type=BreakpointType.CONTAINER_WIDTH,
                min_value=cluster_width * 0.9,
                max_value=cluster_width * 1.1 if i < len(width_clusters) - 1 else None,
                priority=i,
                metadata={'cluster_width': cluster_width, 'auto_generated': True}
            )
            breakpoints.append(breakpoint)
        
        return breakpoints
    
    def _find_clusters(self, values: List[float], tolerance: float = 0.1) -> List[float]:
        """Find natural clusters in a list of values."""
        if not values:
            return []
        
        sorted_values = sorted(values)
        clusters = [sorted_values[0]]
        
        for value in sorted_values[1:]:
            # Check if value is close to any existing cluster
            close_to_existing = any(
                abs(value - cluster) / cluster <= tolerance 
                for cluster in clusters
            )
            
            if not close_to_existing:
                clusters.append(value)
        
        return clusters


class BreakpointManager(QObject):
    """Comprehensive breakpoint management system."""
    
    # Signals
    breakpoint_changed = pyqtSignal(BreakpointEvent)
    breakpoints_updated = pyqtSignal()
    device_profile_changed = pyqtSignal(DeviceProfile)
    
    def __init__(self, config_manager: ConfigurationManager, parent: Optional[QObject] = None):
        super().__init__(parent)
        
        self._config_manager = config_manager
        self._breakpoints: Dict[str, BreakpointDefinition] = {}
        self._device_profiles: Dict[DeviceClass, DeviceProfile] = {}
        self._current_breakpoints: Dict[BreakpointType, str] = {}
        self._active_device_profile: Optional[DeviceProfile] = None
        
        # Performance optimization
        self._breakpoint_cache: Dict[str, str] = {}
        self._calculation_enabled = True
        
        # Monitoring
        self._change_history: List[BreakpointEvent] = []
        self._max_history_size = 100
        
        # Calculator
        self._calculator = BreakpointCalculator()
        
        # Initialize default configurations
        self._initialize_default_breakpoints()
        self._initialize_device_profiles()
        
        logger.debug("BreakpointManager initialized")
    
    def _initialize_default_breakpoints(self) -> None:
        """Initialize default responsive breakpoints."""
        default_breakpoints = [
            BreakpointDefinition(
                name="xs",
                type=BreakpointType.CONTAINER_WIDTH,
                max_value=575,
                device_classes={DeviceClass.MOBILE_PORTRAIT},
                priority=100,
                metadata={'description': 'Extra small devices (phones)'}
            ),
            BreakpointDefinition(
                name="sm",
                type=BreakpointType.CONTAINER_WIDTH,
                min_value=576,
                max_value=767,
                device_classes={DeviceClass.MOBILE_LANDSCAPE},
                priority=90,
                metadata={'description': 'Small devices (landscape phones)'}
            ),
            BreakpointDefinition(
                name="md",
                type=BreakpointType.CONTAINER_WIDTH,
                min_value=768,
                max_value=991,
                device_classes={DeviceClass.TABLET_PORTRAIT, DeviceClass.TABLET_LANDSCAPE},
                priority=80,
                metadata={'description': 'Medium devices (tablets)'}
            ),
            BreakpointDefinition(
                name="lg",
                type=BreakpointType.CONTAINER_WIDTH,
                min_value=992,
                max_value=1199,
                device_classes={DeviceClass.DESKTOP_SMALL},
                priority=70,
                metadata={'description': 'Large devices (small desktops)'}
            ),
            BreakpointDefinition(
                name="xl",
                type=BreakpointType.CONTAINER_WIDTH,
                min_value=1200,
                max_value=1399,
                device_classes={DeviceClass.DESKTOP_MEDIUM},
                priority=60,
                metadata={'description': 'Extra large devices (large desktops)'}
            ),
            BreakpointDefinition(
                name="xxl",
                type=BreakpointType.CONTAINER_WIDTH,
                min_value=1400,
                device_classes={DeviceClass.DESKTOP_LARGE, DeviceClass.DESKTOP_ULTRAWIDE},
                priority=50,
                metadata={'description': 'Extra extra large devices (larger desktops)'}
            )
        ]
        
        for breakpoint in default_breakpoints:
            self._breakpoints[breakpoint.name] = breakpoint
    
    def _initialize_device_profiles(self) -> None:
        """Initialize device profiles with optimal breakpoint configurations."""
        profiles = [
            DeviceProfile(
                name="Mobile Portrait",
                device_class=DeviceClass.MOBILE_PORTRAIT,
                typical_widths=[320, 375, 414],
                typical_heights=[568, 667, 736, 812],
                typical_dpi_range=(150, 400),
                touch_enabled=True,
                preferred_breakpoints=["xs"],
                optimization_hints={
                    'layout_type': 'stacked',
                    'touch_targets': 'large',
                    'margins': 'minimal'
                }
            ),
            DeviceProfile(
                name="Mobile Landscape",
                device_class=DeviceClass.MOBILE_LANDSCAPE,
                typical_widths=[568, 667, 736, 812],
                typical_heights=[320, 375, 414],
                typical_dpi_range=(150, 400),
                touch_enabled=True,
                preferred_breakpoints=["sm"],
                optimization_hints={
                    'layout_type': 'horizontal',
                    'touch_targets': 'medium',
                    'margins': 'compact'
                }
            ),
            DeviceProfile(
                name="Tablet Portrait",
                device_class=DeviceClass.TABLET_PORTRAIT,
                typical_widths=[768, 820, 834],
                typical_heights=[1024, 1180, 1194],
                typical_dpi_range=(130, 250),
                touch_enabled=True,
                preferred_breakpoints=["md"],
                optimization_hints={
                    'layout_type': 'split',
                    'touch_targets': 'medium',
                    'margins': 'comfortable'
                }
            ),
            DeviceProfile(
                name="Desktop Small",
                device_class=DeviceClass.DESKTOP_SMALL,
                typical_widths=[992, 1024, 1152],
                typical_heights=[768, 864, 900],
                typical_dpi_range=(90, 150),
                touch_enabled=False,
                preferred_breakpoints=["lg"],
                optimization_hints={
                    'layout_type': 'multi_panel',
                    'touch_targets': 'small',
                    'margins': 'standard'
                }
            ),
            DeviceProfile(
                name="Desktop Large",
                device_class=DeviceClass.DESKTOP_LARGE,
                typical_widths=[1400, 1440, 1600, 1920],
                typical_heights=[900, 1024, 1080, 1200],
                typical_dpi_range=(90, 150),
                touch_enabled=False,
                preferred_breakpoints=["xxl"],
                optimization_hints={
                    'layout_type': 'advanced_multi_panel',
                    'touch_targets': 'small',
                    'margins': 'spacious'
                }
            )
        ]
        
        for profile in profiles:
            self._device_profiles[profile.device_class] = profile
    
    def add_breakpoint(self, breakpoint: BreakpointDefinition) -> None:
        """Add a new breakpoint definition."""
        self._breakpoints[breakpoint.name] = breakpoint
        self._invalidate_cache()
        self.breakpoints_updated.emit()
        
        logger.debug(f"Added breakpoint: {breakpoint.name}")
    
    def remove_breakpoint(self, name: str) -> bool:
        """Remove a breakpoint definition."""
        if name in self._breakpoints:
            del self._breakpoints[name]
            self._invalidate_cache()
            self.breakpoints_updated.emit()
            logger.debug(f"Removed breakpoint: {name}")
            return True
        return False
    
    def get_breakpoint(self, name: str) -> Optional[BreakpointDefinition]:
        """Get a breakpoint definition by name."""
        return self._breakpoints.get(name)
    
    def get_all_breakpoints(self) -> Dict[str, BreakpointDefinition]:
        """Get all breakpoint definitions."""
        return self._breakpoints.copy()
    
    def get_breakpoints_by_type(self, breakpoint_type: BreakpointType) -> List[BreakpointDefinition]:
        """Get all breakpoints of a specific type."""
        return [bp for bp in self._breakpoints.values() if bp.type == breakpoint_type]
    
    def evaluate_breakpoint(
        self,
        value: float,
        breakpoint_type: BreakpointType,
        context: Dict[str, Any] = None
    ) -> Optional[str]:
        """Evaluate which breakpoint matches the given value and context."""
        if not self._calculation_enabled:
            return None
        
        # Check cache first
        cache_key = f"{breakpoint_type.name}_{value}_{hash(str(context))}"
        if cache_key in self._breakpoint_cache:
            return self._breakpoint_cache[cache_key]
        
        # Find matching breakpoints
        matching_breakpoints = []
        for name, breakpoint in self._breakpoints.items():
            if (breakpoint.type == breakpoint_type and 
                breakpoint.matches(value, context)):
                matching_breakpoints.append((name, breakpoint))
        
        # Sort by priority (highest first)
        matching_breakpoints.sort(key=lambda x: x[1].priority, reverse=True)
        
        result = matching_breakpoints[0][0] if matching_breakpoints else None
        
        # Cache the result
        self._breakpoint_cache[cache_key] = result
        
        return result
    
    def update_breakpoint_state(
        self,
        breakpoint_type: BreakpointType,
        value: float,
        context: Dict[str, Any] = None
    ) -> bool:
        """Update the current breakpoint state and emit change events if needed."""
        new_breakpoint = self.evaluate_breakpoint(value, breakpoint_type, context)
        old_breakpoint = self._current_breakpoints.get(breakpoint_type)
        
        if new_breakpoint != old_breakpoint:
            # Update state
            if new_breakpoint:
                self._current_breakpoints[breakpoint_type] = new_breakpoint
            elif breakpoint_type in self._current_breakpoints:
                del self._current_breakpoints[breakpoint_type]
            
            # Create and emit event
            event = BreakpointEvent(
                old_breakpoint=old_breakpoint,
                new_breakpoint=new_breakpoint,
                breakpoint_type=breakpoint_type,
                trigger_value=value,
                timestamp=time.time(),
                context=context or {}
            )
            
            self._add_to_history(event)
            self.breakpoint_changed.emit(event)
            
            logger.debug(f"Breakpoint changed: {old_breakpoint} -> {new_breakpoint}")
            return True
        
        return False
    
    def get_current_breakpoint(self, breakpoint_type: BreakpointType) -> Optional[str]:
        """Get the current breakpoint for a specific type."""
        return self._current_breakpoints.get(breakpoint_type)
    
    def get_all_current_breakpoints(self) -> Dict[BreakpointType, str]:
        """Get all current breakpoint states."""
        return self._current_breakpoints.copy()
    
    def detect_device_profile(self, screen_properties: Dict[str, Any]) -> Optional[DeviceProfile]:
        """Detect the most appropriate device profile based on screen properties."""
        width = screen_properties.get('width', 0)
        height = screen_properties.get('height', 0)
        dpi = screen_properties.get('dpi', 100)
        is_touch = screen_properties.get('is_touch_enabled', False)
        
        best_profile = None
        best_score = 0
        
        for profile in self._device_profiles.values():
            score = self._calculate_profile_score(profile, width, height, dpi, is_touch)
            if score > best_score:
                best_score = score
                best_profile = profile
        
        if best_profile and best_profile != self._active_device_profile:
            self._active_device_profile = best_profile
            self.device_profile_changed.emit(best_profile)
            logger.debug(f"Device profile changed to: {best_profile.name}")
        
        return best_profile
    
    def _calculate_profile_score(
        self,
        profile: DeviceProfile,
        width: int,
        height: int,
        dpi: float,
        is_touch: bool
    ) -> float:
        """Calculate how well a device profile matches the current environment."""
        score = 0.0
        
        # Width matching
        width_distances = [abs(width - w) for w in profile.typical_widths]
        if width_distances:
            min_width_distance = min(width_distances)
            score += max(0, 100 - min_width_distance / 10)
        
        # Height matching
        height_distances = [abs(height - h) for h in profile.typical_heights]
        if height_distances:
            min_height_distance = min(height_distances)
            score += max(0, 50 - min_height_distance / 20)
        
        # DPI matching
        dpi_min, dpi_max = profile.typical_dpi_range
        if dpi_min <= dpi <= dpi_max:
            score += 30
        else:
            dpi_distance = min(abs(dpi - dpi_min), abs(dpi - dpi_max))
            score += max(0, 30 - dpi_distance / 10)
        
        # Touch capability
        if profile.touch_enabled == is_touch:
            score += 20
        
        return score
    
    def create_custom_breakpoints_from_content(
        self,
        content_analysis: Dict[str, Any]
    ) -> List[BreakpointDefinition]:
        """Create custom breakpoints based on content analysis."""
        widget_sizes = content_analysis.get('widget_sizes', [])
        content_widths = content_analysis.get('content_widths', [])
        
        custom_breakpoints = []
        
        # Generate content-based breakpoints
        if content_widths:
            content_breakpoint_values = self._calculator.calculate_content_breakpoints(
                content_widths,
                content_analysis.get('min_items_per_row', 1),
                content_analysis.get('max_items_per_row', 6),
                content_analysis.get('margin', 16)
            )
            
            for i, value in enumerate(content_breakpoint_values):
                breakpoint = BreakpointDefinition(
                    name=f"content_{i}",
                    type=BreakpointType.CONTAINER_WIDTH,
                    min_value=value * 0.95,
                    max_value=value * 1.05,
                    priority=200 + i,
                    metadata={
                        'auto_generated': True,
                        'based_on': 'content_analysis',
                        'target_value': value
                    }
                )
                custom_breakpoints.append(breakpoint)
        
        # Generate natural breakpoints from widget sizes
        if widget_sizes:
            natural_breakpoints = self._calculator.calculate_natural_breakpoints(widget_sizes)
            custom_breakpoints.extend(natural_breakpoints)
        
        return custom_breakpoints
    
    def optimize_breakpoints_for_performance(self) -> None:
        """Optimize breakpoint calculations for better performance."""
        # Remove rarely used breakpoints
        usage_stats = self._analyze_breakpoint_usage()
        threshold = 0.05  # Remove breakpoints used less than 5% of the time
        
        to_remove = []
        for name, usage_ratio in usage_stats.items():
            if usage_ratio < threshold and self._breakpoints[name].metadata.get('auto_generated'):
                to_remove.append(name)
        
        for name in to_remove:
            self.remove_breakpoint(name)
            logger.debug(f"Removed underused breakpoint: {name}")
        
        # Clear cache to force recalculation
        self._invalidate_cache()
    
    def _analyze_breakpoint_usage(self) -> Dict[str, float]:
        """Analyze usage statistics for all breakpoints."""
        usage_counts = {}
        total_events = len(self._change_history)
        
        if total_events == 0:
            return {}
        
        for event in self._change_history:
            if event.new_breakpoint:
                usage_counts[event.new_breakpoint] = usage_counts.get(event.new_breakpoint, 0) + 1
        
        # Convert to ratios
        return {name: count / total_events for name, count in usage_counts.items()}
    
    def _add_to_history(self, event: BreakpointEvent) -> None:
        """Add event to change history with size management."""
        self._change_history.append(event)
        
        # Limit history size
        if len(self._change_history) > self._max_history_size:
            self._change_history = self._change_history[-self._max_history_size:]
    
    def _invalidate_cache(self) -> None:
        """Invalidate all caches."""
        self._breakpoint_cache.clear()
        self._calculator._content_analysis_cache.clear()
        self._calculator._calculation_cache.clear()
    
    def save_configuration(self) -> None:
        """Save breakpoint configuration to settings."""
        config_data = {
            'breakpoints': {},
            'current_breakpoints': {k.name: v for k, v in self._current_breakpoints.items()},
            'active_device_profile': self._active_device_profile.name if self._active_device_profile else None
        }
        
        # Serialize breakpoints (excluding custom conditions)
        for name, bp in self._breakpoints.items():
            config_data['breakpoints'][name] = {
                'name': bp.name,
                'type': bp.type.name,
                'min_value': bp.min_value,
                'max_value': bp.max_value,
                'device_classes': [dc.value for dc in bp.device_classes],
                'priority': bp.priority,
                'metadata': bp.metadata
            }
        
        self._config_manager.set('ui.responsive.breakpoints', config_data)
        logger.debug("Breakpoint configuration saved")
    
    def load_configuration(self) -> None:
        """Load breakpoint configuration from settings."""
        config_data = self._config_manager.get('ui.responsive.breakpoints', {})
        
        if 'breakpoints' in config_data:
            for name, bp_data in config_data['breakpoints'].items():
                try:
                    breakpoint = BreakpointDefinition(
                        name=bp_data['name'],
                        type=BreakpointType[bp_data['type']],
                        min_value=bp_data.get('min_value'),
                        max_value=bp_data.get('max_value'),
                        device_classes={DeviceClass(dc) for dc in bp_data.get('device_classes', [])},
                        priority=bp_data.get('priority', 0),
                        metadata=bp_data.get('metadata', {})
                    )
                    self._breakpoints[name] = breakpoint
                except (KeyError, ValueError) as e:
                    logger.warning(f"Failed to load breakpoint {name}: {e}")
        
        logger.debug("Breakpoint configuration loaded")
    
    def get_breakpoint_statistics(self) -> Dict[str, Any]:
        """Get comprehensive breakpoint usage and performance statistics."""
        usage_stats = self._analyze_breakpoint_usage()
        
        return {
            'total_breakpoints': len(self._breakpoints),
            'active_breakpoints': len(self._current_breakpoints),
            'usage_statistics': usage_stats,
            'change_history_size': len(self._change_history),
            'cache_size': len(self._breakpoint_cache),
            'device_profile': self._active_device_profile.name if self._active_device_profile else None,
            'auto_generated_count': sum(1 for bp in self._breakpoints.values() 
                                      if bp.metadata.get('auto_generated', False))
        }
    
    def enable_calculation(self, enabled: bool) -> None:
        """Enable or disable breakpoint calculations."""
        self._calculation_enabled = enabled
        if enabled:
            logger.debug("Breakpoint calculations enabled")
        else:
            logger.debug("Breakpoint calculations disabled")
    
    def clear_history(self) -> None:
        """Clear the breakpoint change history."""
        self._change_history.clear()
        logger.debug("Breakpoint change history cleared")


# Import for time module
import time