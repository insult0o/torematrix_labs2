# AGENT 3 - SELECTION TOOLS: Optimization & Advanced Features

## 🎯 Your Assignment
You are **Agent 3** in the 4-agent parallel development of the **Advanced Document Processing Pipeline Selection Tools Implementation**. Your focus is on **Optimization & Advanced Features** - making the selection tools production-ready with high performance and sophisticated capabilities.

## 📋 Your Specific Tasks
- [ ] Implement hit testing optimization with spatial indexing in `src/torematrix/ui/viewer/tools/hit_testing.py`
- [ ] Create magnetic snapping system for precision alignment in `src/torematrix/ui/viewer/tools/snapping.py`
- [ ] Implement selection persistence across view changes in `src/torematrix/ui/viewer/tools/persistence.py`
- [ ] Create selection history and undo/redo system in `src/torematrix/ui/viewer/tools/history.py`
- [ ] Implement tool manager with advanced state management in `src/torematrix/ui/viewer/tools/manager.py`
- [ ] Create performance monitoring and profiling system in `src/torematrix/ui/viewer/tools/profiling.py`
- [ ] Implement selection caching and optimization in `src/torematrix/ui/viewer/tools/caching.py`
- [ ] Create advanced selection algorithms for large documents in `src/torematrix/ui/viewer/tools/algorithms.py`
- [ ] Implement selection validation and quality assurance in `src/torematrix/ui/viewer/tools/validation.py`
- [ ] Create tool preference system and configuration management in `src/torematrix/ui/viewer/tools/preferences.py`

## 📁 Files to Create

```
src/torematrix/ui/viewer/tools/
├── hit_testing.py                  # Optimized hit testing with spatial indexing
├── snapping.py                     # Magnetic snapping system
├── persistence.py                  # Selection persistence across views
├── history.py                      # Undo/redo system
├── manager.py                      # Advanced tool manager
├── profiling.py                    # Performance monitoring
├── caching.py                      # Selection caching optimization
├── algorithms.py                   # Advanced selection algorithms
├── validation.py                   # Selection validation
└── preferences.py                  # Tool preferences and configuration

tests/unit/viewer/tools/
├── test_hit_testing.py             # Hit testing optimization tests
├── test_snapping.py                # Magnetic snapping tests
├── test_persistence.py             # Selection persistence tests
├── test_history.py                 # Undo/redo system tests
├── test_manager.py                 # Tool manager tests
├── test_profiling.py               # Performance monitoring tests
├── test_caching.py                 # Caching system tests
├── test_algorithms.py              # Advanced algorithm tests
├── test_validation.py              # Selection validation tests
└── test_preferences.py             # Preferences system tests
```

## 🔧 Technical Implementation Details

### Hit Testing Optimization with Spatial Indexing
```python
from typing import List, Dict, Optional, Tuple, Any
from PyQt6.QtCore import QPoint, QRect, QRectF
from PyQt6.QtGui import QPolygonF
import numpy as np
from dataclasses import dataclass
import time

try:
    from rtree import index
    RTREE_AVAILABLE = True
except ImportError:
    RTREE_AVAILABLE = False

@dataclass
class ElementBounds:
    """Optimized element bounds representation"""
    element_id: str
    bounds: QRectF
    element_type: str
    z_index: int
    last_updated: float

class SpatialIndex:
    """R-tree based spatial index for efficient hit testing"""
    
    def __init__(self, use_rtree: bool = True):
        self._use_rtree = use_rtree and RTREE_AVAILABLE
        self._elements: Dict[int, ElementBounds] = {}
        self._element_counter = 0
        self._dirty = False
        
        if self._use_rtree:
            self._index = index.Index()
        else:
            self._fallback_index = []
        
        # Performance metrics
        self._query_count = 0
        self._hit_count = 0
        self._avg_query_time = 0.0
    
    def insert_element(self, element: Any, bounds: QRectF) -> int:
        """Insert element into spatial index"""
        element_id = self._element_counter
        element_bounds = ElementBounds(
            element_id=str(element_id),
            bounds=bounds,
            element_type=getattr(element, 'type', 'unknown'),
            z_index=getattr(element, 'z_index', 0),
            last_updated=time.time()
        )
        
        self._elements[element_id] = element_bounds
        
        if self._use_rtree:
            self._index.insert(element_id, (bounds.x(), bounds.y(), 
                                          bounds.right(), bounds.bottom()))
        else:
            self._fallback_index.append((element_id, bounds))
        
        self._element_counter += 1
        self._dirty = True
        return element_id
    
    def remove_element(self, element_id: int) -> bool:
        """Remove element from spatial index"""
        if element_id in self._elements:
            element_bounds = self._elements[element_id]
            bounds = element_bounds.bounds
            
            if self._use_rtree:
                self._index.delete(element_id, (bounds.x(), bounds.y(),
                                               bounds.right(), bounds.bottom()))
            else:
                self._fallback_index = [(eid, b) for eid, b in self._fallback_index 
                                       if eid != element_id]
            
            del self._elements[element_id]
            self._dirty = True
            return True
        return False
    
    def query_point(self, point: QPoint, tolerance: float = 0.0) -> List[ElementBounds]:
        """Find all elements intersecting with point"""
        start_time = time.time()
        self._query_count += 1
        
        bounds = (point.x() - tolerance, point.y() - tolerance,
                 point.x() + tolerance, point.y() + tolerance)
        
        candidates = []
        
        if self._use_rtree:
            candidate_ids = list(self._index.intersection(bounds))
            candidates = [self._elements[eid] for eid in candidate_ids 
                         if eid in self._elements]
        else:
            # Fallback linear search
            for element_id, element_bounds in self._fallback_index:
                if (element_bounds.contains(point.x(), point.y()) or
                    self._point_near_bounds(point, element_bounds, tolerance)):
                    candidates.append(self._elements[element_id])
        
        # Precise hit testing
        results = []
        for element_bounds in candidates:
            if self._precise_hit_test(point, element_bounds, tolerance):
                results.append(element_bounds)
                self._hit_count += 1
        
        # Update performance metrics
        query_time = (time.time() - start_time) * 1000
        self._avg_query_time = (self._avg_query_time + query_time) / 2
        
        # Sort by z-index (highest first)
        results.sort(key=lambda e: e.z_index, reverse=True)
        return results
    
    def query_rect(self, rect: QRect) -> List[ElementBounds]:
        """Find all elements intersecting with rectangle"""
        start_time = time.time()
        self._query_count += 1
        
        bounds = (rect.x(), rect.y(), rect.right(), rect.bottom())
        candidates = []
        
        if self._use_rtree:
            candidate_ids = list(self._index.intersection(bounds))
            candidates = [self._elements[eid] for eid in candidate_ids 
                         if eid in self._elements]
        else:
            # Fallback intersection test
            for element_id, element_bounds in self._fallback_index:
                if element_bounds.intersects(rect):
                    candidates.append(self._elements[element_id])
        
        results = []
        for element_bounds in candidates:
            if self._rect_intersects_element(rect, element_bounds):
                results.append(element_bounds)
                self._hit_count += 1
        
        query_time = (time.time() - start_time) * 1000
        self._avg_query_time = (self._avg_query_time + query_time) / 2
        
        return results
    
    def _precise_hit_test(self, point: QPoint, element_bounds: ElementBounds, 
                         tolerance: float) -> bool:
        """Perform precise hit testing"""
        bounds = element_bounds.bounds
        
        # Check if point is within bounds + tolerance
        return (point.x() >= bounds.x() - tolerance and
                point.x() <= bounds.right() + tolerance and
                point.y() >= bounds.y() - tolerance and
                point.y() <= bounds.bottom() + tolerance)
    
    def _rect_intersects_element(self, rect: QRect, element_bounds: ElementBounds) -> bool:
        """Check if rectangle intersects with element"""
        return rect.intersects(element_bounds.bounds.toRect())
    
    def _point_near_bounds(self, point: QPoint, bounds: QRectF, tolerance: float) -> bool:
        """Check if point is near bounds within tolerance"""
        return (abs(point.x() - bounds.center().x()) <= bounds.width()/2 + tolerance and
                abs(point.y() - bounds.center().y()) <= bounds.height()/2 + tolerance)
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        return {
            'query_count': self._query_count,
            'hit_count': self._hit_count,
            'hit_ratio': self._hit_count / max(self._query_count, 1),
            'avg_query_time_ms': self._avg_query_time,
            'element_count': len(self._elements),
            'index_type': 'rtree' if self._use_rtree else 'fallback',
            'memory_usage': len(self._elements) * 64  # Approximate bytes
        }
    
    def optimize(self) -> None:
        """Optimize the spatial index"""
        if self._dirty and self._use_rtree:
            # Rebuild index for better performance
            old_elements = self._elements.copy()
            self.clear()
            
            # Re-insert all elements
            for element_bounds in old_elements.values():
                self.insert_element(element_bounds, element_bounds.bounds)
            
            self._dirty = False
    
    def clear(self) -> None:
        """Clear all elements from index"""
        self._elements.clear()
        self._element_counter = 0
        self._dirty = False
        
        if self._use_rtree:
            self._index = index.Index()
        else:
            self._fallback_index.clear()

class HitTestOptimizer:
    """Optimized hit testing with caching and spatial indexing"""
    
    def __init__(self, cache_size: int = 1000):
        self._spatial_index = SpatialIndex()
        self._hit_cache: Dict[Tuple, List[ElementBounds]] = {}
        self._cache_size_limit = cache_size
        self._cache_hits = 0
        self._cache_misses = 0
        
        # Optimization settings
        self._enable_caching = True
        self._enable_clustering = True
        self._cluster_threshold = 100  # Elements before clustering
    
    def optimize_hit_testing(self, elements: List[Any]) -> None:
        """Build spatial index for efficient hit testing"""
        self._spatial_index.clear()
        self._hit_cache.clear()
        
        for element in elements:
            if hasattr(element, 'bounding_rect'):
                bounds = QRectF(element.bounding_rect)
                self._spatial_index.insert_element(element, bounds)
        
        # Optimize the index
        self._spatial_index.optimize()
    
    def find_elements_at_point(self, point: QPoint, tolerance: float = 5.0) -> List[Any]:
        """Optimized point-based element search"""
        cache_key = (point.x(), point.y(), tolerance)
        
        # Check cache first
        if self._enable_caching and cache_key in self._hit_cache:
            self._cache_hits += 1
            return [self._resolve_element(eb) for eb in self._hit_cache[cache_key]]
        
        self._cache_misses += 1
        
        # Query spatial index
        results = self._spatial_index.query_point(point, tolerance)
        
        # Cache results with LRU eviction
        if self._enable_caching:
            if len(self._hit_cache) >= self._cache_size_limit:
                # Remove oldest entry
                oldest_key = next(iter(self._hit_cache))
                del self._hit_cache[oldest_key]
            
            self._hit_cache[cache_key] = results
        
        return [self._resolve_element(eb) for eb in results]
    
    def find_elements_in_rect(self, rect: QRect) -> List[Any]:
        """Optimized rectangle-based element search"""
        results = self._spatial_index.query_rect(rect)
        return [self._resolve_element(eb) for eb in results]
    
    def _resolve_element(self, element_bounds: ElementBounds) -> Any:
        """Resolve element bounds back to original element"""
        # This would need to be implemented based on element storage
        # For now, return a placeholder
        return element_bounds
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        spatial_metrics = self._spatial_index.get_performance_metrics()
        
        cache_metrics = {
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'cache_hit_ratio': self._cache_hits / max(self._cache_hits + self._cache_misses, 1),
            'cache_size': len(self._hit_cache),
            'cache_enabled': self._enable_caching
        }
        
        return {**spatial_metrics, **cache_metrics}
    
    def clear_cache(self) -> None:
        """Clear the hit test cache"""
        self._hit_cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0
```

### Magnetic Snapping System
```python
class MagneticSnapping:
    """Precision alignment system with magnetic snapping"""
    
    def __init__(self):
        self._snap_distance = 10  # pixels
        self._snap_enabled = True
        self._snap_to_grid = True
        self._snap_to_elements = True
        self._snap_to_guides = True
        self._grid_size = 20
        self._guide_lines = []
        
        # Snapping history for better UX
        self._snap_history = []
        self._max_history = 10
        
        # Performance optimization
        self._snap_cache = {}
        self._cache_expiry = 1.0  # seconds
    
    def set_snap_distance(self, distance: int) -> None:
        """Set the magnetic snap distance"""
        self._snap_distance = max(1, distance)
        self._snap_cache.clear()
    
    def set_grid_size(self, size: int) -> None:
        """Set the grid size for grid snapping"""
        self._grid_size = max(1, size)
        self._snap_cache.clear()
    
    def add_guide_line(self, is_horizontal: bool, position: float) -> None:
        """Add a guide line for snapping"""
        self._guide_lines.append({
            'horizontal': is_horizontal,
            'position': position,
            'created': time.time()
        })
    
    def remove_guide_lines(self) -> None:
        """Remove all guide lines"""
        self._guide_lines.clear()
    
    def snap_point(self, point: QPoint, context_elements: List[Any] = None) -> QPoint:
        """Apply magnetic snapping to point"""
        if not self._snap_enabled:
            return point
        
        # Check cache first
        cache_key = (point.x(), point.y(), len(context_elements) if context_elements else 0)
        current_time = time.time()
        
        if cache_key in self._snap_cache:
            cached_result, cache_time = self._snap_cache[cache_key]
            if current_time - cache_time < self._cache_expiry:
                return cached_result
        
        snapped_point = point
        min_distance = float('inf')
        snap_info = None
        
        # Grid snapping
        if self._snap_to_grid:
            grid_point, grid_distance = self._snap_to_grid_point(point)
            if grid_distance < min_distance and grid_distance <= self._snap_distance:
                snapped_point = grid_point
                min_distance = grid_distance
                snap_info = {'type': 'grid', 'distance': grid_distance}
        
        # Guide line snapping
        if self._snap_to_guides:
            guide_point, guide_distance = self._snap_to_guide_lines(point)
            if guide_point and guide_distance < min_distance and guide_distance <= self._snap_distance:
                snapped_point = guide_point
                min_distance = guide_distance
                snap_info = {'type': 'guide', 'distance': guide_distance}
        
        # Element snapping
        if self._snap_to_elements and context_elements:
            element_point, element_distance = self._snap_to_element_edges(point, context_elements)
            if element_point and element_distance < min_distance and element_distance <= self._snap_distance:
                snapped_point = element_point
                min_distance = element_distance
                snap_info = {'type': 'element', 'distance': element_distance}
        
        # Cache the result
        self._snap_cache[cache_key] = (snapped_point, current_time)
        
        # Add to history
        if snap_info:
            self._add_to_history(point, snapped_point, snap_info)
        
        return snapped_point
    
    def _snap_to_grid_point(self, point: QPoint) -> Tuple[QPoint, float]:
        """Snap point to grid intersection"""
        grid_x = round(point.x() / self._grid_size) * self._grid_size
        grid_y = round(point.y() / self._grid_size) * self._grid_size
        grid_point = QPoint(grid_x, grid_y)
        
        distance = self._distance(point, grid_point)
        return grid_point, distance
    
    def _snap_to_guide_lines(self, point: QPoint) -> Tuple[Optional[QPoint], float]:
        """Snap point to guide lines"""
        best_point = None
        min_distance = float('inf')
        
        for guide in self._guide_lines:
            if guide['horizontal']:
                # Horizontal guide line
                guide_point = QPoint(point.x(), int(guide['position']))
                distance = abs(point.y() - guide['position'])
            else:
                # Vertical guide line
                guide_point = QPoint(int(guide['position']), point.y())
                distance = abs(point.x() - guide['position'])
            
            if distance < min_distance:
                min_distance = distance
                best_point = guide_point
        
        return best_point, min_distance
    
    def _snap_to_element_edges(self, point: QPoint, elements: List[Any]) -> Tuple[Optional[QPoint], float]:
        """Snap point to nearest element edge"""
        best_snap = None
        min_distance = float('inf')
        
        for element in elements:
            if not hasattr(element, 'bounding_rect'):
                continue
                
            rect = element.bounding_rect
            
            # Generate snap candidates
            snap_candidates = [
                # Edges
                QPoint(rect.left(), point.y()),      # Left edge
                QPoint(rect.right(), point.y()),     # Right edge
                QPoint(point.x(), rect.top()),       # Top edge
                QPoint(point.x(), rect.bottom()),    # Bottom edge
                
                # Corners
                rect.topLeft(),
                rect.topRight(),
                rect.bottomLeft(),
                rect.bottomRight(),
                
                # Centers
                QPoint(rect.center().x(), point.y()),  # Horizontal center
                QPoint(point.x(), rect.center().y()),  # Vertical center
                rect.center()                           # Both centers
            ]
            
            for snap_point in snap_candidates:
                distance = self._distance(point, snap_point)
                if distance < min_distance:
                    min_distance = distance
                    best_snap = snap_point
        
        return best_snap, min_distance
    
    def _distance(self, point1: QPoint, point2: QPoint) -> float:
        """Calculate distance between two points"""
        dx = point2.x() - point1.x()
        dy = point2.y() - point1.y()
        return (dx * dx + dy * dy) ** 0.5
    
    def _add_to_history(self, original: QPoint, snapped: QPoint, info: Dict) -> None:
        """Add snap operation to history"""
        self._snap_history.append({
            'original': original,
            'snapped': snapped,
            'info': info,
            'timestamp': time.time()
        })
        
        # Limit history size
        if len(self._snap_history) > self._max_history:
            self._snap_history.pop(0)
    
    def get_snap_history(self) -> List[Dict]:
        """Get snapping history"""
        return self._snap_history.copy()
    
    def get_snap_statistics(self) -> Dict[str, Any]:
        """Get snapping statistics"""
        if not self._snap_history:
            return {'total_snaps': 0}
        
        snap_types = {}
        total_distance_saved = 0
        
        for entry in self._snap_history:
            snap_type = entry['info']['type']
            snap_types[snap_type] = snap_types.get(snap_type, 0) + 1
            total_distance_saved += entry['info']['distance']
        
        return {
            'total_snaps': len(self._snap_history),
            'snap_types': snap_types,
            'avg_distance_saved': total_distance_saved / len(self._snap_history),
            'cache_size': len(self._snap_cache),
            'settings': {
                'snap_distance': self._snap_distance,
                'grid_size': self._grid_size,
                'snap_to_grid': self._snap_to_grid,
                'snap_to_elements': self._snap_to_elements,
                'snap_to_guides': self._snap_to_guides
            }
        }
    
    def clear_cache(self) -> None:
        """Clear the snapping cache"""
        self._snap_cache.clear()
    
    def enable_snapping(self, enabled: bool) -> None:
        """Enable or disable snapping globally"""
        self._snap_enabled = enabled
        if not enabled:
            self.clear_cache()
```

### Selection History and Undo/Redo System
```python
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
import time
import json

class HistoryActionType(Enum):
    SELECT = "select"
    DESELECT = "deselect"
    MULTI_SELECT = "multi_select"
    CLEAR = "clear"
    TOOL_CHANGE = "tool_change"

@dataclass
class HistoryAction:
    """Represents a single action in the selection history"""
    action_type: HistoryActionType
    timestamp: float
    selection_data: Dict[str, Any]
    tool_name: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def serialize(self) -> Dict[str, Any]:
        """Serialize action to dictionary"""
        return {
            'action_type': self.action_type.value,
            'timestamp': self.timestamp,
            'selection_data': self.selection_data,
            'tool_name': self.tool_name,
            'metadata': self.metadata
        }
    
    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> 'HistoryAction':
        """Deserialize action from dictionary"""
        return cls(
            action_type=HistoryActionType(data['action_type']),
            timestamp=data['timestamp'],
            selection_data=data['selection_data'],
            tool_name=data['tool_name'],
            metadata=data.get('metadata', {})
        )

class SelectionHistory:
    """Undo/redo system for selection operations"""
    
    def __init__(self, max_history: int = 50):
        self._history: List[HistoryAction] = []
        self._current_index = -1
        self._max_history = max_history
        self._auto_save_enabled = True
        self._compression_enabled = True
        
        # Performance metrics
        self._undo_count = 0
        self._redo_count = 0
        self._total_actions = 0
        
        # Memory management
        self._memory_limit = 10 * 1024 * 1024  # 10MB
        self._current_memory_usage = 0
    
    def add_action(self, action: HistoryAction) -> None:
        """Add action to history"""
        # Remove any future history when adding new action
        if self._current_index < len(self._history) - 1:
            # Remove future actions
            removed_actions = self._history[self._current_index + 1:]
            self._history = self._history[:self._current_index + 1]
            
            # Update memory usage
            for removed_action in removed_actions:
                self._current_memory_usage -= self._estimate_action_size(removed_action)
        
        # Add new action
        self._history.append(action)
        self._current_index += 1
        self._total_actions += 1
        self._current_memory_usage += self._estimate_action_size(action)
        
        # Limit history size
        while len(self._history) > self._max_history:
            removed_action = self._history.pop(0)
            self._current_index -= 1
            self._current_memory_usage -= self._estimate_action_size(removed_action)
        
        # Check memory limit
        if self._current_memory_usage > self._memory_limit:
            self._compress_history()
    
    def undo(self) -> Optional[HistoryAction]:
        """Undo to previous action"""
        if self._current_index > 0:
            self._current_index -= 1
            self._undo_count += 1
            return self._history[self._current_index]
        return None
    
    def redo(self) -> Optional[HistoryAction]:
        """Redo to next action"""
        if self._current_index < len(self._history) - 1:
            self._current_index += 1
            self._redo_count += 1
            return self._history[self._current_index]
        return None
    
    def can_undo(self) -> bool:
        """Check if undo is possible"""
        return self._current_index > 0
    
    def can_redo(self) -> bool:
        """Check if redo is possible"""
        return self._current_index < len(self._history) - 1
    
    def get_current_action(self) -> Optional[HistoryAction]:
        """Get current action"""
        if 0 <= self._current_index < len(self._history):
            return self._history[self._current_index]
        return None
    
    def get_undo_preview(self) -> Optional[HistoryAction]:
        """Get preview of what would be undone"""
        if self.can_undo():
            return self._history[self._current_index - 1]
        return None
    
    def get_redo_preview(self) -> Optional[HistoryAction]:
        """Get preview of what would be redone"""
        if self.can_redo():
            return self._history[self._current_index + 1]
        return None
    
    def clear(self) -> None:
        """Clear all history"""
        self._history.clear()
        self._current_index = -1
        self._current_memory_usage = 0
    
    def get_history_summary(self) -> List[Dict[str, Any]]:
        """Get summary of all actions in history"""
        return [
            {
                'index': i,
                'action_type': action.action_type.value,
                'tool_name': action.tool_name,
                'timestamp': action.timestamp,
                'is_current': i == self._current_index,
                'element_count': len(action.selection_data.get('elements', [])),
                'metadata': action.metadata
            }
            for i, action in enumerate(self._history)
        ]
    
    def _estimate_action_size(self, action: HistoryAction) -> int:
        """Estimate memory usage of an action"""
        # Rough estimate in bytes
        base_size = 200  # Base object overhead
        data_size = len(json.dumps(action.selection_data, default=str))
        metadata_size = len(json.dumps(action.metadata, default=str))
        return base_size + data_size + metadata_size
    
    def _compress_history(self) -> None:
        """Compress history to reduce memory usage"""
        if not self._compression_enabled:
            return
        
        # Remove every other action from the beginning (except recent ones)
        keep_recent = 20  # Keep last 20 actions uncompressed
        
        if len(self._history) > keep_recent * 2:
            # Compress older actions
            compressed_history = []
            for i in range(0, len(self._history) - keep_recent, 2):
                compressed_history.append(self._history[i])
            
            # Keep all recent actions
            compressed_history.extend(self._history[-keep_recent:])
            
            # Update memory usage
            self._current_memory_usage = sum(
                self._estimate_action_size(action) for action in compressed_history
            )
            
            # Update current index
            old_current = self._current_index
            self._history = compressed_history
            self._current_index = min(old_current, len(self._history) - 1)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get history statistics"""
        action_types = {}
        for action in self._history:
            action_type = action.action_type.value
            action_types[action_type] = action_types.get(action_type, 0) + 1
        
        return {
            'total_actions': self._total_actions,
            'current_history_size': len(self._history),
            'current_index': self._current_index,
            'undo_count': self._undo_count,
            'redo_count': self._redo_count,
            'memory_usage_bytes': self._current_memory_usage,
            'memory_limit_bytes': self._memory_limit,
            'action_types': action_types,
            'can_undo': self.can_undo(),
            'can_redo': self.can_redo(),
            'compression_enabled': self._compression_enabled
        }
    
    def export_history(self, filepath: str) -> bool:
        """Export history to file"""
        try:
            history_data = {
                'version': '1.0',
                'exported_at': time.time(),
                'history': [action.serialize() for action in self._history],
                'current_index': self._current_index,
                'statistics': self.get_statistics()
            }
            
            with open(filepath, 'w') as f:
                json.dump(history_data, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Failed to export history: {e}")
            return False
    
    def import_history(self, filepath: str) -> bool:
        """Import history from file"""
        try:
            with open(filepath, 'r') as f:
                history_data = json.load(f)
            
            # Validate version
            if history_data.get('version') != '1.0':
                print("Unsupported history file version")
                return False
            
            # Import actions
            self._history = [
                HistoryAction.deserialize(action_data)
                for action_data in history_data['history']
            ]
            
            self._current_index = history_data['current_index']
            
            # Recalculate memory usage
            self._current_memory_usage = sum(
                self._estimate_action_size(action) for action in self._history
            )
            
            return True
        except Exception as e:
            print(f"Failed to import history: {e}")
            return False
```

## 🧪 Testing Requirements
- [ ] **Hit Testing** - Spatial indexing accuracy and performance
- [ ] **Magnetic Snapping** - Precision alignment in various scenarios
- [ ] **Selection Persistence** - Restoration across view changes
- [ ] **History System** - Undo/redo functionality and limits
- [ ] **Tool Manager** - Advanced state management and switching
- [ ] **Performance** - Monitoring and optimization validation
- [ ] **Caching** - Cache hit rates and memory management
- [ ] **Algorithms** - Large document handling and efficiency
- [ ] **Validation** - Selection quality and consistency
- [ ] **Preferences** - Configuration persistence and defaults

**Target:** 30+ comprehensive tests with >95% coverage

## 🔗 Integration Points

### Dependencies (From Agents 1 & 2)
- ✅ **Base Tool Interface** - Foundation for optimization
- ✅ **Tool Implementations** - Specific tools to optimize
- ✅ **User Interaction** - Mouse/keyboard handling to enhance
- ✅ **Visual Feedback** - Rendering to optimize

### Provides for Agent 4
- **Optimized Tools** - High-performance selection tools
- **Advanced Features** - Snapping, persistence, history
- **Performance Metrics** - Monitoring and profiling data
- **Configuration System** - Tool preferences and settings

### Integration Notes
- **Performance:** All optimizations must maintain <16ms response time
- **Memory:** Efficient caching without excessive memory usage
- **Scalability:** Systems must handle large documents (10k+ elements)
- **Reliability:** Robust error handling and recovery

## 🎯 Success Metrics
- **Performance:** >50% improvement in hit testing speed
- **Memory:** <100MB memory usage for large documents
- **Accuracy:** 99.9% accuracy in snap alignment
- **Scalability:** Handle 10k+ elements smoothly
- **Reliability:** Zero crashes in optimization systems

## 🚀 Getting Started

### Step 1: Create Feature Branch
```bash
git checkout main
git pull origin main
git checkout -b feature/selection-tools-agent3-issue159
```

### Step 2: Wait for Dependencies
- Monitor Agents 1 & 2 progress
- Coordinate on interface requirements
- Begin implementation once foundations are stable

### Step 3: Implement Optimizations
1. Start with hit testing optimization
2. Add magnetic snapping system
3. Implement selection persistence
4. Add history and undo/redo
5. Create performance monitoring

### Step 4: Performance Testing
1. Benchmark all optimizations
2. Test with large documents
3. Validate memory usage
4. Stress test all systems

**Related Issues:**
- Main Issue: #19 - Advanced Document Processing Pipeline Selection Tools
- Sub-Issue: #159 - Optimization & Advanced Features
- Dependencies: #157 (Agent 1), #158 (Agent 2)
- Next: #160 - Integration & Production Readiness (Agent 4)

**Timeline:** 2-3 days for complete optimization and testing.