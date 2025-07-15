"""Virtual Scrolling for Massive Result Sets

High-performance virtual scrolling manager that handles massive result sets
efficiently by only rendering visible items and maintaining smooth scrolling
performance for 100K+ results.
"""

import asyncio
import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Callable, Set
from abc import ABC, abstractmethod

from torematrix.core.models.element import Element


logger = logging.getLogger(__name__)


@dataclass
class ViewportInfo:
    """Information about the current viewport"""
    top: int = 0
    left: int = 0
    width: int = 0
    height: int = 0
    scroll_top: int = 0
    scroll_left: int = 0
    
    @property
    def bottom(self) -> int:
        """Bottom coordinate of viewport"""
        return self.top + self.height
    
    @property
    def right(self) -> int:
        """Right coordinate of viewport"""
        return self.left + self.width


@dataclass
class ItemDimensions:
    """Dimensions for virtual scroll items"""
    height: int = 50
    width: int = 200
    spacing: int = 2
    estimated_height: Optional[int] = None
    
    @property
    def total_height(self) -> int:
        """Total height including spacing"""
        return self.height + self.spacing
    
    @property
    def total_width(self) -> int:
        """Total width including spacing"""
        return self.width + self.spacing


@dataclass
class VisibleRange:
    """Range of visible items in virtual scroll"""
    start_index: int = 0
    end_index: int = 0
    buffer_start: int = 0
    buffer_end: int = 0
    total_items: int = 0
    
    @property
    def visible_count(self) -> int:
        """Number of visible items"""
        return max(0, self.end_index - self.start_index)
    
    @property
    def buffer_count(self) -> int:
        """Number of buffered items"""
        return max(0, self.buffer_end - self.buffer_start)
    
    def contains_index(self, index: int) -> bool:
        """Check if index is in visible range"""
        return self.buffer_start <= index < self.buffer_end


@dataclass
class VirtualScrollConfig:
    """Configuration for virtual scrolling"""
    item_height: int = 50
    item_width: int = 200
    buffer_size: int = 10  # Items to buffer outside viewport
    overscan: int = 5  # Additional items to render for smooth scrolling
    enable_horizontal_scroll: bool = False
    enable_dynamic_heights: bool = False
    enable_sticky_header: bool = False
    preload_threshold: float = 0.8  # Start loading when 80% through buffer
    cache_size: int = 1000  # Maximum cached items
    scroll_debounce_ms: int = 16  # ~60fps
    enable_smooth_scrolling: bool = True


class VirtualScrollItemProvider(ABC):
    """Abstract interface for providing items to virtual scroll"""
    
    @abstractmethod
    async def get_item_count(self) -> int:
        """Get total number of items"""
        pass
    
    @abstractmethod
    async def get_items(self, start_index: int, count: int) -> List[Element]:
        """Get items in specified range"""
        pass
    
    @abstractmethod
    async def get_item_height(self, index: int) -> int:
        """Get height of specific item (for dynamic heights)"""
        pass


class VirtualScrollRenderer(ABC):
    """Abstract interface for rendering virtual scroll items"""
    
    @abstractmethod
    def render_item(self, item: Element, index: int, bounds: Dict[str, int]) -> Any:
        """Render a single item"""
        pass
    
    @abstractmethod
    def update_item(self, item: Element, index: int, rendered_item: Any) -> None:
        """Update an existing rendered item"""
        pass
    
    @abstractmethod
    def remove_item(self, rendered_item: Any) -> None:
        """Remove a rendered item"""
        pass


class VirtualScrollManager:
    """Virtual scrolling manager for massive result sets"""
    
    def __init__(self,
                 item_provider: VirtualScrollItemProvider,
                 renderer: VirtualScrollRenderer,
                 config: Optional[VirtualScrollConfig] = None):
        """Initialize virtual scroll manager
        
        Args:
            item_provider: Provider for scroll items
            renderer: Renderer for scroll items
            config: Virtual scroll configuration
        """
        self.item_provider = item_provider
        self.renderer = renderer
        self.config = config or VirtualScrollConfig()
        
        # State
        self.viewport = ViewportInfo()
        self.visible_range = VisibleRange()
        self.total_items = 0
        self.rendered_items: Dict[int, Any] = {}  # index -> rendered_item
        self.item_cache: Dict[int, Element] = {}  # index -> element
        self.item_heights: Dict[int, int] = {}  # index -> height (for dynamic heights)
        
        # Performance tracking
        self.scroll_position = 0
        self.last_scroll_time = 0.0
        self.scroll_velocity = 0.0
        self.render_count = 0
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Loading state
        self.is_loading = False
        self.loading_ranges: Set[Tuple[int, int]] = set()
        self.last_preload_trigger = 0
        
        # Scroll debouncing
        self.scroll_timer: Optional[asyncio.Handle] = None
        self.pending_scroll_update = False
        
        logger.info(f"VirtualScrollManager initialized: buffer_size={self.config.buffer_size}")
    
    async def initialize(self) -> None:
        """Initialize virtual scroll with item count"""
        self.total_items = await self.item_provider.get_item_count()
        self.visible_range.total_items = self.total_items
        
        logger.info(f"Virtual scroll initialized with {self.total_items} items")
    
    def update_viewport(self, viewport: ViewportInfo) -> None:
        """Update viewport information
        
        Args:
            viewport: New viewport information
        """
        self.viewport = viewport
        self._schedule_scroll_update()
    
    def update_scroll_position(self, position: int) -> None:
        """Update scroll position
        
        Args:
            position: New scroll position
        """
        current_time = time.time()
        
        # Calculate scroll velocity
        if self.last_scroll_time > 0:
            time_delta = current_time - self.last_scroll_time
            if time_delta > 0:
                position_delta = position - self.scroll_position
                self.scroll_velocity = position_delta / time_delta
        
        self.scroll_position = position
        self.last_scroll_time = current_time
        
        self._schedule_scroll_update()
    
    async def get_visible_items(self) -> List[Tuple[int, Element, Any]]:
        """Get currently visible items with their rendered representations
        
        Returns:
            List of (index, element, rendered_item) tuples
        """
        visible_items = []
        
        for index in range(self.visible_range.buffer_start, self.visible_range.buffer_end):
            if index in self.item_cache and index in self.rendered_items:
                element = self.item_cache[index]
                rendered_item = self.rendered_items[index]
                visible_items.append((index, element, rendered_item))
        
        return visible_items
    
    def get_scroll_info(self) -> Dict[str, Any]:
        """Get scroll information for UI updates
        
        Returns:
            Dictionary with scroll information
        """
        total_height = self._calculate_total_height()
        scroll_percentage = 0.0
        
        if total_height > 0:
            scroll_percentage = (self.scroll_position / total_height) * 100
        
        return {
            'scroll_position': self.scroll_position,
            'scroll_percentage': min(100.0, max(0.0, scroll_percentage)),
            'total_height': total_height,
            'visible_range': {
                'start': self.visible_range.start_index,
                'end': self.visible_range.end_index,
                'count': self.visible_range.visible_count
            },
            'total_items': self.total_items,
            'scroll_velocity': self.scroll_velocity,
            'is_loading': self.is_loading,
            'cache_stats': {
                'hits': self.cache_hits,
                'misses': self.cache_misses,
                'hit_ratio': self._calculate_cache_hit_ratio()
            }
        }
    
    def get_item_bounds(self, index: int) -> Dict[str, int]:
        """Get bounds for specific item
        
        Args:
            index: Item index
            
        Returns:
            Dictionary with item bounds
        """
        y_position = self._calculate_item_position(index)
        height = self._get_item_height(index)
        
        return {
            'top': y_position,
            'left': 0,
            'width': self.config.item_width,
            'height': height,
            'bottom': y_position + height,
            'right': self.config.item_width
        }
    
    async def scroll_to_index(self, index: int, alignment: str = 'start') -> None:
        """Scroll to specific item index
        
        Args:
            index: Index to scroll to
            alignment: Alignment ('start', 'center', 'end')
        """
        if index < 0 or index >= self.total_items:
            return
        
        target_position = self._calculate_item_position(index)
        
        if alignment == 'center':
            target_position -= self.viewport.height // 2
        elif alignment == 'end':
            target_position -= self.viewport.height - self._get_item_height(index)
        
        target_position = max(0, target_position)
        
        self.update_scroll_position(target_position)
        await self._update_visible_items()
        
        logger.debug(f"Scrolled to index {index} at position {target_position}")
    
    async def refresh_items(self, start_index: int = None, end_index: int = None) -> None:
        """Refresh items in specified range
        
        Args:
            start_index: Start index (None for all)
            end_index: End index (None for all)
        """
        if start_index is None:
            start_index = 0
        if end_index is None:
            end_index = self.total_items
        
        # Clear cache for range
        for index in range(start_index, min(end_index, self.total_items)):
            if index in self.item_cache:
                del self.item_cache[index]
            if index in self.rendered_items:
                self.renderer.remove_item(self.rendered_items[index])
                del self.rendered_items[index]
        
        # Trigger re-render
        await self._update_visible_items()
        
        logger.debug(f"Refreshed items {start_index} to {end_index}")
    
    def set_item_height(self, index: int, height: int) -> None:
        """Set height for specific item (for dynamic heights)
        
        Args:
            index: Item index
            height: Item height
        """
        if self.config.enable_dynamic_heights:
            self.item_heights[index] = height
            
            # Trigger layout update if item is visible
            if self.visible_range.contains_index(index):
                self._schedule_scroll_update()
    
    def clear_cache(self) -> None:
        """Clear all cached items"""
        # Remove rendered items
        for rendered_item in self.rendered_items.values():
            self.renderer.remove_item(rendered_item)
        
        self.item_cache.clear()
        self.rendered_items.clear()
        self.item_heights.clear()
        
        # Reset statistics
        self.cache_hits = 0
        self.cache_misses = 0
        
        logger.info("Virtual scroll cache cleared")
    
    async def preload_range(self, start_index: int, end_index: int) -> None:
        """Preload items in specified range
        
        Args:
            start_index: Start index
            end_index: End index
        """
        if self.is_loading:
            return
        
        # Check if range is already loading
        range_tuple = (start_index, end_index)
        if range_tuple in self.loading_ranges:
            return
        
        self.loading_ranges.add(range_tuple)
        
        try:
            # Load items that aren't already cached
            items_to_load = []
            indices_to_load = []
            
            for index in range(start_index, min(end_index, self.total_items)):
                if index not in self.item_cache:
                    indices_to_load.append(index)
            
            if indices_to_load:
                items = await self.item_provider.get_items(
                    indices_to_load[0], 
                    len(indices_to_load)
                )
                
                # Cache loaded items
                for i, item in enumerate(items):
                    cache_index = indices_to_load[i]
                    self.item_cache[cache_index] = item
                
                logger.debug(f"Preloaded {len(items)} items from {start_index} to {end_index}")
        
        finally:
            self.loading_ranges.discard(range_tuple)
    
    def _schedule_scroll_update(self) -> None:
        """Schedule a debounced scroll update"""
        if self.scroll_timer:
            self.scroll_timer.cancel()
        
        self.scroll_timer = asyncio.get_event_loop().call_later(
            self.config.scroll_debounce_ms / 1000.0,
            lambda: asyncio.create_task(self._update_visible_items())
        )
    
    async def _update_visible_items(self) -> None:
        """Update visible items based on current scroll position"""
        if self.is_loading:
            return
        
        self.is_loading = True
        
        try:
            # Calculate new visible range
            new_range = self._calculate_visible_range()
            
            # Check if range changed significantly
            if (abs(new_range.start_index - self.visible_range.start_index) < 5 and
                abs(new_range.end_index - self.visible_range.end_index) < 5):
                return  # Skip update for small changes
            
            # Update visible range
            old_range = self.visible_range
            self.visible_range = new_range
            
            # Remove items that are no longer visible
            await self._remove_invisible_items(old_range, new_range)
            
            # Load and render new visible items
            await self._load_and_render_items(new_range)
            
            # Trigger preloading if needed
            await self._check_preload_trigger(new_range)
            
            # Cleanup cache if too large
            self._cleanup_cache()
            
            self.render_count += 1
            
        finally:
            self.is_loading = False
    
    def _calculate_visible_range(self) -> VisibleRange:
        """Calculate visible item range based on scroll position"""
        if self.total_items == 0:
            return VisibleRange()
        
        # Calculate visible items based on scroll position
        if self.config.enable_dynamic_heights:
            start_index, end_index = self._calculate_range_dynamic_heights()
        else:
            start_index, end_index = self._calculate_range_fixed_heights()
        
        # Add buffer
        buffer_start = max(0, start_index - self.config.buffer_size)
        buffer_end = min(self.total_items, end_index + self.config.buffer_size)
        
        # Add overscan for smooth scrolling
        overscan_start = max(0, buffer_start - self.config.overscan)
        overscan_end = min(self.total_items, buffer_end + self.config.overscan)
        
        return VisibleRange(
            start_index=start_index,
            end_index=end_index,
            buffer_start=overscan_start,
            buffer_end=overscan_end,
            total_items=self.total_items
        )
    
    def _calculate_range_fixed_heights(self) -> Tuple[int, int]:
        """Calculate visible range for fixed height items"""
        item_height = self.config.item_height
        
        start_index = max(0, self.scroll_position // item_height)
        visible_count = math.ceil(self.viewport.height / item_height) + 1
        end_index = min(self.total_items, start_index + visible_count)
        
        return start_index, end_index
    
    def _calculate_range_dynamic_heights(self) -> Tuple[int, int]:
        """Calculate visible range for dynamic height items"""
        # For dynamic heights, we need to iterate through items
        # This is a simplified implementation
        current_position = 0
        start_index = 0
        end_index = 0
        
        # Find start index
        for i in range(self.total_items):
            item_height = self._get_item_height(i)
            if current_position + item_height > self.scroll_position:
                start_index = i
                break
            current_position += item_height
        
        # Find end index
        viewport_bottom = self.scroll_position + self.viewport.height
        for i in range(start_index, self.total_items):
            item_height = self._get_item_height(i)
            if current_position > viewport_bottom:
                end_index = i
                break
            current_position += item_height
        else:
            end_index = self.total_items
        
        return start_index, end_index
    
    async def _remove_invisible_items(self, old_range: VisibleRange, new_range: VisibleRange) -> None:
        """Remove items that are no longer visible"""
        # Find items to remove
        items_to_remove = []
        
        for index in self.rendered_items:
            if not new_range.contains_index(index):
                items_to_remove.append(index)
        
        # Remove items
        for index in items_to_remove:
            if index in self.rendered_items:
                self.renderer.remove_item(self.rendered_items[index])
                del self.rendered_items[index]
    
    async def _load_and_render_items(self, visible_range: VisibleRange) -> None:
        """Load and render items in visible range"""
        # Find items that need to be loaded
        items_to_load = []
        for index in range(visible_range.buffer_start, visible_range.buffer_end):
            if index not in self.item_cache:
                items_to_load.append(index)
        
        # Load missing items
        if items_to_load:
            start_index = min(items_to_load)
            count = max(items_to_load) - start_index + 1
            
            try:
                items = await self.item_provider.get_items(start_index, count)
                
                # Cache loaded items
                for i, item in enumerate(items):
                    cache_index = start_index + i
                    if cache_index in items_to_load:
                        self.item_cache[cache_index] = item
                        self.cache_misses += 1
                
            except Exception as e:
                logger.error(f"Error loading items {start_index}-{start_index + count}: {e}")
                return
        
        # Render items that need rendering
        for index in range(visible_range.buffer_start, visible_range.buffer_end):
            if index in self.item_cache and index not in self.rendered_items:
                element = self.item_cache[index]
                bounds = self.get_item_bounds(index)
                
                try:
                    rendered_item = self.renderer.render_item(element, index, bounds)
                    self.rendered_items[index] = rendered_item
                    self.cache_hits += 1
                    
                except Exception as e:
                    logger.error(f"Error rendering item {index}: {e}")
    
    async def _check_preload_trigger(self, visible_range: VisibleRange) -> None:
        """Check if preloading should be triggered"""
        if not self.config.preload_threshold:
            return
        
        # Calculate if we're near the end of loaded content
        current_position = visible_range.end_index / max(1, self.total_items)
        
        if (current_position > self.config.preload_threshold and
            time.time() - self.last_preload_trigger > 1.0):  # Rate limit preloading
            
            # Preload next batch
            preload_start = visible_range.buffer_end
            preload_count = self.config.buffer_size * 2
            
            if preload_start < self.total_items:
                asyncio.create_task(
                    self.preload_range(preload_start, preload_start + preload_count)
                )
                self.last_preload_trigger = time.time()
    
    def _cleanup_cache(self) -> None:
        """Clean up cache if it's too large"""
        if len(self.item_cache) <= self.config.cache_size:
            return
        
        # Remove items that are furthest from visible range
        visible_center = (self.visible_range.start_index + self.visible_range.end_index) // 2
        
        # Sort cached items by distance from visible center
        cached_items = list(self.item_cache.keys())
        cached_items.sort(key=lambda idx: abs(idx - visible_center), reverse=True)
        
        # Remove furthest items
        items_to_remove = len(cached_items) - self.config.cache_size + 10  # Remove a few extra
        
        for i in range(items_to_remove):
            index = cached_items[i]
            if index not in self.rendered_items:  # Don't remove rendered items
                del self.item_cache[index]
    
    def _calculate_total_height(self) -> int:
        """Calculate total height of all items"""
        if self.config.enable_dynamic_heights:
            total_height = 0
            for i in range(self.total_items):
                total_height += self._get_item_height(i)
            return total_height
        else:
            return self.total_items * self.config.item_height
    
    def _calculate_item_position(self, index: int) -> int:
        """Calculate position of specific item"""
        if self.config.enable_dynamic_heights:
            position = 0
            for i in range(index):
                position += self._get_item_height(i)
            return position
        else:
            return index * self.config.item_height
    
    def _get_item_height(self, index: int) -> int:
        """Get height of specific item"""
        if self.config.enable_dynamic_heights and index in self.item_heights:
            return self.item_heights[index]
        return self.config.item_height
    
    def _calculate_cache_hit_ratio(self) -> float:
        """Calculate cache hit ratio"""
        total_requests = self.cache_hits + self.cache_misses
        if total_requests == 0:
            return 0.0
        return (self.cache_hits / total_requests) * 100.0


# Utility functions and factory methods
def create_virtual_scroll_manager(item_provider: VirtualScrollItemProvider,
                                renderer: VirtualScrollRenderer,
                                item_height: int = 50,
                                buffer_size: int = 10) -> VirtualScrollManager:
    """Create virtual scroll manager with basic configuration
    
    Args:
        item_provider: Provider for scroll items
        renderer: Renderer for scroll items
        item_height: Height of each item
        buffer_size: Buffer size for smooth scrolling
        
    Returns:
        Configured VirtualScrollManager
    """
    config = VirtualScrollConfig(
        item_height=item_height,
        buffer_size=buffer_size
    )
    
    return VirtualScrollManager(item_provider, renderer, config)


def create_performance_virtual_scroll(item_provider: VirtualScrollItemProvider,
                                    renderer: VirtualScrollRenderer) -> VirtualScrollManager:
    """Create virtual scroll manager optimized for performance
    
    Args:
        item_provider: Provider for scroll items
        renderer: Renderer for scroll items
        
    Returns:
        Performance-optimized VirtualScrollManager
    """
    config = VirtualScrollConfig(
        item_height=40,  # Smaller items for more visible
        buffer_size=20,  # Larger buffer
        overscan=10,  # More overscan
        preload_threshold=0.7,  # Earlier preloading
        cache_size=2000,  # Larger cache
        scroll_debounce_ms=8,  # Higher frame rate
        enable_smooth_scrolling=True
    )
    
    return VirtualScrollManager(item_provider, renderer, config)


def create_responsive_virtual_scroll(item_provider: VirtualScrollItemProvider,
                                   renderer: VirtualScrollRenderer) -> VirtualScrollManager:
    """Create virtual scroll manager optimized for responsiveness
    
    Args:
        item_provider: Provider for scroll items
        renderer: Renderer for scroll items
        
    Returns:
        Responsiveness-optimized VirtualScrollManager
    """
    config = VirtualScrollConfig(
        item_height=60,  # Larger items for easier interaction
        buffer_size=5,  # Smaller buffer for less work
        overscan=2,  # Minimal overscan
        preload_threshold=0.9,  # Conservative preloading
        cache_size=500,  # Smaller cache
        scroll_debounce_ms=32,  # Lower frame rate for responsiveness
        enable_smooth_scrolling=False
    )
    
    return VirtualScrollManager(item_provider, renderer, config)