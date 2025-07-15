"""
Virtual Scrolling Engine

Implements efficient virtual scrolling to handle large datasets by rendering
only the visible items and managing viewport updates efficiently.
"""

from typing import List, Dict, Optional, Tuple, Any, Callable
from dataclasses import dataclass
from PyQt6.QtCore import QObject, pyqtSignal, QRect, QTimer, QModelIndex, Qt
from PyQt6.QtWidgets import QAbstractScrollArea, QScrollBar, QWidget
from PyQt6.QtGui import QPainter, QFontMetrics

from ..models.tree_node import TreeNode
from ..interfaces.tree_interfaces import ElementProtocol


@dataclass
class ViewportItem:
    """Represents an item in the virtual viewport."""
    index: QModelIndex
    rect: QRect
    node: TreeNode
    level: int
    is_expanded: bool
    is_visible: bool
    cached_height: Optional[int] = None
    cached_content: Optional[Any] = None


@dataclass
class ViewportRange:
    """Defines a range in the virtual viewport."""
    start_index: int
    end_index: int
    start_y: int
    end_y: int
    item_count: int


class ViewportManager(QObject):
    """Manages the virtual viewport and visible item calculation."""
    
    # Signals
    viewportChanged = pyqtSignal(ViewportRange)
    itemsChanged = pyqtSignal(list)  # List of ViewportItem
    scrollPositionChanged = pyqtSignal(int, int)  # x, y
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Viewport state
        self.viewport_rect = QRect()
        self.scroll_position = (0, 0)
        self.item_height = 25  # Default item height
        self.indent_size = 20  # Indentation per level
        
        # Visible items cache
        self.visible_items: List[ViewportItem] = []
        self.item_positions: Dict[int, int] = {}  # row -> y_position
        self.total_height = 0
        
        # Performance settings
        self.buffer_size = 10  # Extra items to render outside viewport
        self.update_threshold = 5  # Minimum scroll distance for updates
        
        # Update management
        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self._delayed_update)
        self.pending_update = False
    
    def set_viewport_rect(self, rect: QRect) -> None:
        """Set the viewport rectangle."""
        if rect != self.viewport_rect:
            self.viewport_rect = rect
            self._schedule_update()
    
    def set_scroll_position(self, x: int, y: int) -> None:
        """Set scroll position and update viewport if needed."""
        old_x, old_y = self.scroll_position
        
        if abs(y - old_y) >= self.update_threshold or abs(x - old_x) >= self.update_threshold:
            self.scroll_position = (x, y)
            self.scrollPositionChanged.emit(x, y)
            self._schedule_update()
    
    def set_item_height(self, height: int) -> None:
        """Set default item height."""
        if height != self.item_height:
            self.item_height = height
            self._invalidate_positions()
            self._schedule_update()
    
    def calculate_visible_range(self, model, root_index: QModelIndex = QModelIndex()) -> ViewportRange:
        """Calculate which items should be visible in the current viewport."""
        if not self.viewport_rect.isValid() or not model:
            return ViewportRange(0, 0, 0, 0, 0)
        
        # Get viewport bounds with buffer
        scroll_x, scroll_y = self.scroll_position
        viewport_top = scroll_y - (self.buffer_size * self.item_height)
        viewport_bottom = scroll_y + self.viewport_rect.height() + (self.buffer_size * self.item_height)
        
        # Find visible items using binary search for efficiency
        start_index = self._find_item_at_position(viewport_top, model, root_index)
        end_index = self._find_item_at_position(viewport_bottom, model, root_index)
        
        # Calculate range bounds
        start_y = self._get_item_position(start_index)
        end_y = self._get_item_position(end_index) + self.item_height
        item_count = end_index - start_index + 1
        
        return ViewportRange(start_index, end_index, start_y, end_y, item_count)
    
    def get_visible_items(self, model, range_info: ViewportRange) -> List[ViewportItem]:
        """Get list of visible items for the given range."""
        if not model or range_info.item_count <= 0:
            return []
        
        visible_items = []
        current_row = 0
        current_y = 0
        
        # Traverse tree and collect visible items
        self._collect_visible_items(
            model, QModelIndex(), visible_items, 
            range_info, current_row, current_y, 0
        )
        
        return visible_items
    
    def _collect_visible_items(
        self, 
        model, 
        parent_index: QModelIndex, 
        visible_items: List[ViewportItem],
        range_info: ViewportRange,
        current_row: int,
        current_y: int,
        level: int
    ) -> Tuple[int, int]:
        """Recursively collect visible items from the tree."""
        row_count = model.rowCount(parent_index)
        
        for row in range(row_count):
            index = model.index(row, 0, parent_index)
            if not index.isValid():
                continue
            
            # Check if this item is in visible range
            if range_info.start_index <= current_row <= range_info.end_index:
                # Get node data
                node = model._node_from_index(index) if hasattr(model, '_node_from_index') else None
                is_expanded = model.hasChildren(index) and self._is_expanded(index)
                
                # Create viewport item
                item_rect = QRect(
                    level * self.indent_size,
                    current_y,
                    self.viewport_rect.width() - (level * self.indent_size),
                    self.item_height
                )
                
                viewport_item = ViewportItem(
                    index=index,
                    rect=item_rect,
                    node=node,
                    level=level,
                    is_expanded=is_expanded,
                    is_visible=True
                )
                
                visible_items.append(viewport_item)
            
            current_row += 1
            current_y += self.item_height
            
            # Recurse into children if expanded
            if self._is_expanded(index) and model.hasChildren(index):
                current_row, current_y = self._collect_visible_items(
                    model, index, visible_items, range_info,
                    current_row, current_y, level + 1
                )
        
        return current_row, current_y
    
    def _find_item_at_position(self, y_position: int, model, root_index: QModelIndex) -> int:
        """Find the item index at the given Y position using binary search."""
        if y_position <= 0:
            return 0
        
        # Simple calculation for uniform item height
        item_index = max(0, y_position // self.item_height)
        
        # TODO: Implement more sophisticated search for variable height items
        return item_index
    
    def _get_item_position(self, item_index: int) -> int:
        """Get Y position for item at given index."""
        return item_index * self.item_height
    
    def _is_expanded(self, index: QModelIndex) -> bool:
        """Check if item at index is expanded."""
        # This would integrate with the tree view's expansion state
        # For now, assume all items are collapsed
        return False
    
    def _invalidate_positions(self) -> None:
        """Invalidate cached position calculations."""
        self.item_positions.clear()
        self.total_height = 0
    
    def _schedule_update(self) -> None:
        """Schedule a delayed viewport update."""
        if not self.pending_update:
            self.pending_update = True
            self.update_timer.start(16)  # ~60 FPS updates
    
    def _delayed_update(self) -> None:
        """Perform delayed viewport update."""
        self.pending_update = False
        # This would trigger recalculation of visible items
        # Implementation depends on integration with tree view


class ItemRenderer(QObject):
    """Handles efficient rendering of virtual items."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Rendering cache
        self.render_cache: Dict[str, Any] = {}
        self.font_metrics: Optional[QFontMetrics] = None
        
        # Rendering settings
        self.use_cached_renders = True
        self.cache_max_size = 1000
        
        # Performance counters
        self.render_count = 0
        self.cache_hits = 0
        self.cache_misses = 0
    
    def render_item(self, painter: QPainter, item: ViewportItem, style_options: Dict[str, Any]) -> None:
        """Render a virtual item with caching."""
        if not item.is_visible:
            return
        
        # Generate cache key
        cache_key = self._generate_cache_key(item, style_options)
        
        # Check cache first
        if self.use_cached_renders and cache_key in self.render_cache:
            cached_render = self.render_cache[cache_key]
            self._apply_cached_render(painter, item, cached_render)
            self.cache_hits += 1
            return
        
        # Render item fresh
        render_data = self._render_item_fresh(painter, item, style_options)
        
        # Cache the render
        if self.use_cached_renders and len(self.render_cache) < self.cache_max_size:
            self.render_cache[cache_key] = render_data
        
        self.cache_misses += 1
        self.render_count += 1
    
    def _generate_cache_key(self, item: ViewportItem, style_options: Dict[str, Any]) -> str:
        """Generate cache key for render data."""
        # Include relevant style and content information
        element = item.node.element() if item.node else None
        content_hash = hash(element.text) if element and element.text else 0
        
        return f"{item.level}_{item.is_expanded}_{content_hash}_{hash(frozenset(style_options.items()))}"
    
    def _render_item_fresh(self, painter: QPainter, item: ViewportItem, style_options: Dict[str, Any]) -> Dict[str, Any]:
        """Render item without cache."""
        painter.save()
        
        # Get element data
        element = item.node.element() if item.node else None
        if not element:
            painter.restore()
            return {}
        
        # Draw background
        if style_options.get('selected', False):
            painter.fillRect(item.rect, style_options.get('selection_color', Qt.GlobalColor.blue))
        
        # Draw indentation
        indent_x = item.level * 20
        text_rect = item.rect.adjusted(indent_x + 5, 2, -5, -2)
        
        # Draw text
        text = element.text or "No content"
        if len(text) > 100:
            text = text[:97] + "..."
        
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)
        
        # Draw expansion indicator
        if item.node and item.node.child_count() > 0:
            indicator_rect = QRect(indent_x - 15, item.rect.y() + 5, 10, 10)
            if item.is_expanded:
                painter.drawText(indicator_rect, Qt.AlignmentFlag.AlignCenter, "−")
            else:
                painter.drawText(indicator_rect, Qt.AlignmentFlag.AlignCenter, "+")
        
        painter.restore()
        
        # Return render data for caching
        return {
            'text': text,
            'level': item.level,
            'expanded': item.is_expanded,
            'has_children': item.node.child_count() > 0 if item.node else False
        }
    
    def _apply_cached_render(self, painter: QPainter, item: ViewportItem, cached_data: Dict[str, Any]) -> None:
        """Apply cached render data."""
        # This would apply pre-rendered data more efficiently
        # For now, fall back to fresh render
        style_options = {}
        self._render_item_fresh(painter, item, style_options)
    
    def clear_cache(self) -> None:
        """Clear the render cache."""
        self.render_cache.clear()
        self.cache_hits = 0
        self.cache_misses = 0
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache performance statistics."""
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'cache_size': len(self.render_cache),
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'hit_rate': hit_rate,
            'total_renders': self.render_count
        }


class VirtualScrollingEngine(QObject):
    """Main virtual scrolling engine that coordinates viewport and rendering."""
    
    # Signals
    renderRequested = pyqtSignal(list)  # List of ViewportItem to render
    scrollRequested = pyqtSignal(int, int)  # x, y scroll position
    performanceUpdate = pyqtSignal(dict)  # Performance metrics
    
    def __init__(self, tree_view, parent=None):
        super().__init__(parent)
        
        self.tree_view = tree_view
        self.viewport_manager = ViewportManager(self)
        self.item_renderer = ItemRenderer(self)
        
        # Performance tracking
        self.performance_metrics = {
            'visible_items': 0,
            'render_time': 0,
            'update_frequency': 0,
            'memory_usage': 0
        }
        
        # Configuration
        self.enabled = True
        self.debug_mode = False
        
        # Connect signals
        self._setup_connections()
    
    def _setup_connections(self) -> None:
        """Setup signal connections."""
        self.viewport_manager.viewportChanged.connect(self._on_viewport_changed)
        self.viewport_manager.itemsChanged.connect(self._on_items_changed)
        
        # Connect to tree view scroll events
        if hasattr(self.tree_view, 'verticalScrollBar'):
            scroll_bar = self.tree_view.verticalScrollBar()
            if scroll_bar:
                scroll_bar.valueChanged.connect(self._on_scroll_changed)
    
    def enable_virtual_scrolling(self, enabled: bool = True) -> None:
        """Enable or disable virtual scrolling."""
        self.enabled = enabled
        if enabled:
            self._update_viewport()
    
    def set_viewport_size(self, width: int, height: int) -> None:
        """Set viewport size."""
        viewport_rect = QRect(0, 0, width, height)
        self.viewport_manager.set_viewport_rect(viewport_rect)
    
    def update_scroll_position(self, x: int, y: int) -> None:
        """Update scroll position."""
        self.viewport_manager.set_scroll_position(x, y)
    
    def get_visible_items(self) -> List[ViewportItem]:
        """Get currently visible items."""
        return self.viewport_manager.visible_items.copy()
    
    def invalidate_cache(self) -> None:
        """Invalidate all caches."""
        self.item_renderer.clear_cache()
        self.viewport_manager._invalidate_positions()
    
    def render_items(self, painter: QPainter, items: List[ViewportItem]) -> None:
        """Render visible items."""
        if not self.enabled:
            return
        
        import time
        start_time = time.time()
        
        for item in items:
            if item.is_visible:
                style_options = self._get_style_options(item)
                self.item_renderer.render_item(painter, item, style_options)
        
        # Update performance metrics
        render_time = time.time() - start_time
        self.performance_metrics['render_time'] = render_time
        self.performance_metrics['visible_items'] = len(items)
        
        if self.debug_mode:
            self.performanceUpdate.emit(self.performance_metrics.copy())
    
    def _get_style_options(self, item: ViewportItem) -> Dict[str, Any]:
        """Get style options for rendering an item."""
        # This would integrate with the tree view's selection and styling
        return {
            'selected': False,  # Would check selection state
            'focused': False,   # Would check focus state
            'hover': False,     # Would check hover state
        }
    
    def _update_viewport(self) -> None:
        """Update viewport calculations."""
        if not self.enabled:
            return
        
        model = self.tree_view.model()
        if not model:
            return
        
        # Calculate visible range
        range_info = self.viewport_manager.calculate_visible_range(model)
        
        # Get visible items
        visible_items = self.viewport_manager.get_visible_items(model, range_info)
        
        # Update viewport manager
        self.viewport_manager.visible_items = visible_items
        
        # Request render
        self.renderRequested.emit(visible_items)
    
    def _on_viewport_changed(self, range_info: ViewportRange) -> None:
        """Handle viewport change."""
        self._update_viewport()
    
    def _on_items_changed(self, items: List[ViewportItem]) -> None:
        """Handle items change."""
        self.renderRequested.emit(items)
    
    def _on_scroll_changed(self, value: int) -> None:
        """Handle scroll position change."""
        # Convert scroll bar value to y position
        y_position = value
        x_position = 0  # Assume no horizontal scroll for now
        
        self.update_scroll_position(x_position, y_position)
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        metrics = self.performance_metrics.copy()
        metrics.update(self.item_renderer.get_cache_stats())
        return metrics
    
    def set_debug_mode(self, enabled: bool) -> None:
        """Enable or disable debug mode."""
        self.debug_mode = enabled


class VirtualScrollArea(QAbstractScrollArea):
    """Custom scroll area that integrates with virtual scrolling engine."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.virtual_engine = VirtualScrollingEngine(self, self)
        self.total_height = 0
        self.item_height = 25
        
        # Setup scroll area
        self._setup_scroll_area()
        
        # Connect virtual engine
        self.virtual_engine.renderRequested.connect(self._on_render_requested)
    
    def _setup_scroll_area(self) -> None:
        """Setup scroll area properties."""
        # Configure scroll bars
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Connect scroll bar signals
        v_bar = self.verticalScrollBar()
        h_bar = self.horizontalScrollBar()
        
        v_bar.valueChanged.connect(self._on_vertical_scroll)
        h_bar.valueChanged.connect(self._on_horizontal_scroll)
    
    def set_model(self, model) -> None:
        """Set the data model."""
        self.model = model
        self._update_scroll_range()
    
    def _update_scroll_range(self) -> None:
        """Update scroll bar range based on model size."""
        if hasattr(self, 'model') and self.model:
            # Calculate total height (simplified)
            total_items = self._count_total_items()
            self.total_height = total_items * self.item_height
            
            # Update vertical scroll bar
            v_bar = self.verticalScrollBar()
            v_bar.setRange(0, max(0, self.total_height - self.viewport().height()))
            v_bar.setPageStep(self.viewport().height())
            v_bar.setSingleStep(self.item_height)
    
    def _count_total_items(self) -> int:
        """Count total items in model (simplified)."""
        if not hasattr(self, 'model') or not self.model:
            return 0
        
        # This would recursively count all visible items in the tree
        # For now, return a simple count
        return self.model.rowCount()
    
    def paintEvent(self, event) -> None:
        """Paint the virtual scroll area."""
        painter = QPainter(self.viewport())
        
        # Get visible items from virtual engine
        visible_items = self.virtual_engine.get_visible_items()
        
        # Render items
        self.virtual_engine.render_items(painter, visible_items)
        
        painter.end()
    
    def resizeEvent(self, event) -> None:
        """Handle resize event."""
        super().resizeEvent(event)
        
        # Update virtual engine viewport
        viewport_rect = self.viewport().rect()
        self.virtual_engine.set_viewport_size(viewport_rect.width(), viewport_rect.height())
        
        # Update scroll range
        self._update_scroll_range()
    
    def _on_vertical_scroll(self, value: int) -> None:
        """Handle vertical scroll."""
        h_value = self.horizontalScrollBar().value()
        self.virtual_engine.update_scroll_position(h_value, value)
        self.viewport().update()
    
    def _on_horizontal_scroll(self, value: int) -> None:
        """Handle horizontal scroll."""
        v_value = self.verticalScrollBar().value()
        self.virtual_engine.update_scroll_position(value, v_value)
        self.viewport().update()
    
    def _on_render_requested(self, items: List[ViewportItem]) -> None:
        """Handle render request from virtual engine."""
        self.viewport().update()
    
    def wheelEvent(self, event) -> None:
        """Handle mouse wheel events."""
        # Smooth scrolling
        delta = event.angleDelta().y()
        scroll_amount = -delta // 8  # Convert to scroll units
        
        v_bar = self.verticalScrollBar()
        new_value = v_bar.value() + scroll_amount
        v_bar.setValue(new_value)
        
        event.accept()


# Performance testing utilities
class VirtualScrollingBenchmark:
    """Benchmark virtual scrolling performance."""
    
    def __init__(self, virtual_engine: VirtualScrollingEngine):
        self.virtual_engine = virtual_engine
        self.results = {}
    
    def benchmark_render_performance(self, item_counts: List[int]) -> Dict[str, List[float]]:
        """Benchmark rendering performance with different item counts."""
        results = {'item_counts': item_counts, 'render_times': []}
        
        for count in item_counts:
            # Create test items
            test_items = self._create_test_items(count)
            
            # Measure render time
            import time
            start_time = time.time()
            
            # Simulate rendering
            painter = None  # Would need actual QPainter
            # self.virtual_engine.render_items(painter, test_items)
            
            render_time = time.time() - start_time
            results['render_times'].append(render_time)
        
        return results
    
    def _create_test_items(self, count: int) -> List[ViewportItem]:
        """Create test viewport items."""
        items = []
        for i in range(count):
            # Create mock items for testing
            item = ViewportItem(
                index=QModelIndex(),
                rect=QRect(0, i * 25, 200, 25),
                node=None,
                level=0,
                is_expanded=False,
                is_visible=True
            )
            items.append(item)
        return items