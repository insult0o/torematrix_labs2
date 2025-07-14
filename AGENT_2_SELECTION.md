# AGENT 2 - SELECTION TOOLS: Tool Implementations & User Interaction

## 🎯 Your Assignment
You are **Agent 2** in the 4-agent parallel development of the **Advanced Document Processing Pipeline Selection Tools Implementation**. Your focus is on **Tool Implementations & User Interaction** - building the specific selection tools that users will interact with directly.

## 📋 Your Specific Tasks
- [ ] Create Pointer Tool implementation in `src/torematrix/ui/viewer/tools/pointer.py`
- [ ] Create Rectangle Tool implementation in `src/torematrix/ui/viewer/tools/rectangle.py`
- [ ] Create Lasso Tool implementation in `src/torematrix/ui/viewer/tools/lasso.py`
- [ ] Implement Element-Aware Tool with smart selection in `src/torematrix/ui/viewer/tools/element_aware.py`
- [ ] Create tool-specific visual feedback and rendering systems
- [ ] Implement multi-select functionality with modifier key support
- [ ] Create selection actions menu and context menu integration
- [ ] Implement tool switching animations and smooth transitions
- [ ] Create selection preview system with real-time feedback
- [ ] Implement tool-specific keyboard shortcuts and input handling

## 📁 Files to Create

```
src/torematrix/ui/viewer/tools/
├── pointer.py                      # Pointer tool implementation
├── rectangle.py                    # Rectangle selection tool
├── lasso.py                        # Lasso/freeform selection tool
├── element_aware.py                # Smart element-aware selection
├── multi_select.py                 # Multi-selection functionality
├── animations.py                   # Tool switching animations
├── preview.py                      # Selection preview system
├── actions.py                      # Selection actions and context menus
├── shortcuts.py                    # Keyboard shortcut handling
└── feedback.py                     # Visual feedback and rendering

tests/unit/viewer/tools/
├── test_pointer.py                 # Pointer tool tests
├── test_rectangle.py               # Rectangle tool tests
├── test_lasso.py                   # Lasso tool tests
├── test_element_aware.py           # Element-aware tool tests
├── test_multi_select.py            # Multi-selection tests
├── test_animations.py              # Animation system tests
├── test_preview.py                 # Preview system tests
├── test_actions.py                 # Actions and context menu tests
├── test_shortcuts.py               # Keyboard shortcut tests
└── test_feedback.py                # Visual feedback tests
```

## 🔧 Technical Implementation Details

### Pointer Tool Implementation
```python
from PyQt6.QtCore import QPoint, QRect, pyqtSignal, QTimer
from PyQt6.QtGui import QPainter, QCursor, Qt, QPen, QColor
from .base import SelectionTool, ToolState, SelectionResult
import time

class PointerTool(SelectionTool):
    """Single-element selection tool with click-to-select behavior"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._click_tolerance = 5  # pixels
        self._double_click_timeout = 300  # milliseconds
        self._current_element = None
        self._hover_element = None
        self._last_click_time = 0
        self._click_count = 0
        
        # Hover detection timer
        self._hover_timer = QTimer()
        self._hover_timer.setSingleShot(True)
        self._hover_timer.timeout.connect(self._on_hover_timeout)
        
    def activate(self) -> None:
        """Activate pointer tool with appropriate cursor"""
        self._state = ToolState.ACTIVE
        self._cursor = QCursor(Qt.CursorShape.ArrowCursor)
        self.cursor_changed.emit(self._cursor)
        self.state_changed.emit(self._state)
        
    def deactivate(self) -> None:
        """Deactivate pointer tool"""
        self._state = ToolState.INACTIVE
        self._current_element = None
        self._hover_element = None
        self._hover_timer.stop()
        self.state_changed.emit(self._state)
    
    def handle_mouse_press(self, point: QPoint) -> bool:
        """Handle click selection"""
        if self._state != ToolState.ACTIVE:
            return False
        
        current_time = time.time() * 1000  # Convert to milliseconds
        
        # Check for double-click
        if (current_time - self._last_click_time) < self._double_click_timeout:
            self._click_count += 1
        else:
            self._click_count = 1
        
        self._last_click_time = current_time
        
        # Find element at click position
        element = self._find_element_at_point(point)
        if element:
            self._current_element = element
            self._state = ToolState.SELECTING
            
            # Handle double-click for extended selection
            if self._click_count >= 2:
                self._handle_double_click(element, point)
            
            return True
        else:
            # Clear selection if clicking empty space
            self._clear_selection()
            return False
    
    def handle_mouse_move(self, point: QPoint) -> bool:
        """Handle mouse movement for hover effects"""
        if self._state in [ToolState.ACTIVE, ToolState.SELECTED]:
            # Find element under cursor
            element = self._find_element_at_point(point)
            
            if element != self._hover_element:
                self._hover_element = element
                
                # Update cursor based on hover
                if element:
                    self._cursor = QCursor(Qt.CursorShape.PointingHandCursor)
                    self._state = ToolState.HOVER
                else:
                    self._cursor = QCursor(Qt.CursorShape.ArrowCursor)
                    self._state = ToolState.ACTIVE
                
                self.cursor_changed.emit(self._cursor)
                self.state_changed.emit(self._state)
                
                # Start hover timer for delayed effects
                self._hover_timer.start(500)
            
            return True
        return False
    
    def handle_mouse_release(self, point: QPoint) -> bool:
        """Complete selection on release"""
        if self._state == ToolState.SELECTING:
            if self._current_element:
                # Check if click was within tolerance
                if self._is_within_tolerance(point):
                    result = SelectionResult(
                        elements=[self._current_element],
                        geometry=self._current_element.bounding_rect,
                        tool_type="pointer",
                        timestamp=time.time(),
                        metadata={
                            "click_point": point,
                            "click_count": self._click_count,
                            "element_type": getattr(self._current_element, 'type', 'unknown')
                        }
                    )
                    self.selection_changed.emit(result)
                    self._state = ToolState.SELECTED
                    self.state_changed.emit(self._state)
                    return True
                else:
                    # Click was outside tolerance, cancel selection
                    self._current_element = None
                    self._state = ToolState.ACTIVE
                    self.state_changed.emit(self._state)
            return True
        return False
    
    def _handle_double_click(self, element: Any, point: QPoint) -> None:
        """Handle double-click for extended selection"""
        # For text elements, select whole word/paragraph
        if hasattr(element, 'type') and element.type == 'text':
            self._expand_text_selection(element, point)
        # For other elements, select related elements
        else:
            self._expand_related_selection(element)
    
    def _expand_text_selection(self, element: Any, point: QPoint) -> None:
        """Expand text selection to word or paragraph"""
        # Implementation would depend on text element structure
        pass
    
    def _expand_related_selection(self, element: Any) -> None:
        """Expand selection to related elements"""
        # Implementation would find related elements (e.g., table cells)
        pass
    
    def _find_element_at_point(self, point: QPoint) -> Optional[Any]:
        """Find element at given point using coordinate system"""
        # This would use the coordinate mapping system to find elements
        # For now, return None as placeholder
        return None
    
    def _is_within_tolerance(self, point: QPoint) -> bool:
        """Check if point is within click tolerance"""
        # Implementation depends on click tracking
        return True
    
    def _clear_selection(self) -> None:
        """Clear current selection"""
        self._current_element = None
        self._state = ToolState.ACTIVE
        self.state_changed.emit(self._state)
    
    def _on_hover_timeout(self) -> None:
        """Handle hover timeout for delayed effects"""
        if self._hover_element:
            # Show tooltip or highlight
            pass
    
    def render_overlay(self, painter: QPainter) -> None:
        """Render selection highlight and hover effects"""
        # Draw selection highlight
        if self._current_element and self._state == ToolState.SELECTED:
            painter.setPen(QPen(QColor(0, 120, 215), 2))
            painter.drawRect(self._current_element.bounding_rect)
        
        # Draw hover highlight
        if self._hover_element and self._state == ToolState.HOVER:
            painter.setPen(QPen(QColor(0, 120, 215, 100), 1))
            painter.drawRect(self._hover_element.bounding_rect)
```

### Rectangle Tool Implementation
```python
class RectangleTool(SelectionTool):
    """Area-based selection with drag-to-select rectangle"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._start_point = None
        self._current_point = None
        self._current_rect = None
        self._preview_elements = []
        self._drag_threshold = 3  # pixels
        
    def activate(self) -> None:
        """Activate rectangle tool"""
        self._state = ToolState.ACTIVE
        self._cursor = QCursor(Qt.CursorShape.CrossCursor)
        self.cursor_changed.emit(self._cursor)
        self.state_changed.emit(self._state)
    
    def deactivate(self) -> None:
        """Deactivate rectangle tool"""
        self._state = ToolState.INACTIVE
        self._reset_selection()
        self.state_changed.emit(self._state)
    
    def handle_mouse_press(self, point: QPoint) -> bool:
        """Start rectangle selection"""
        if self._state != ToolState.ACTIVE:
            return False
        
        self._start_point = point
        self._current_point = point
        self._current_rect = QRect(point, point)
        self._state = ToolState.SELECTING
        self.state_changed.emit(self._state)
        return True
    
    def handle_mouse_move(self, point: QPoint) -> bool:
        """Update rectangle during drag"""
        if self._state == ToolState.SELECTING and self._start_point:
            self._current_point = point
            self._current_rect = QRect(self._start_point, point).normalized()
            
            # Only start preview if we've moved beyond threshold
            if self._get_distance(self._start_point, point) > self._drag_threshold:
                # Update preview selection
                self._preview_elements = self._find_elements_in_rect(self._current_rect)
                
                # Update cursor for drag operation
                self._cursor = QCursor(Qt.CursorShape.SizeAllCursor)
                self.cursor_changed.emit(self._cursor)
            
            return True
        return False
    
    def handle_mouse_release(self, point: QPoint) -> bool:
        """Complete rectangle selection"""
        if self._state == ToolState.SELECTING and self._start_point:
            # Check if we actually dragged or just clicked
            if self._get_distance(self._start_point, point) <= self._drag_threshold:
                # Single click - clear selection
                self._reset_selection()
                return True
            
            # Find final elements in selection
            final_elements = self._find_elements_in_rect(self._current_rect)
            
            if final_elements:
                result = SelectionResult(
                    elements=final_elements,
                    geometry=self._current_rect,
                    tool_type="rectangle",
                    timestamp=time.time(),
                    metadata={
                        "start_point": self._start_point,
                        "end_point": point,
                        "area": self._current_rect.width() * self._current_rect.height(),
                        "element_count": len(final_elements)
                    }
                )
                self.selection_changed.emit(result)
                self._state = ToolState.SELECTED
                self.state_changed.emit(self._state)
                return True
            else:
                # No elements selected
                self._reset_selection()
                return True
        return False
    
    def _find_elements_in_rect(self, rect: QRect) -> List[Any]:
        """Find all elements that intersect with rectangle"""
        # This would use the geometry algorithms from Agent 1
        # For now, return empty list as placeholder
        return []
    
    def _get_distance(self, point1: QPoint, point2: QPoint) -> float:
        """Get distance between two points"""
        dx = point2.x() - point1.x()
        dy = point2.y() - point1.y()
        return (dx * dx + dy * dy) ** 0.5
    
    def _reset_selection(self) -> None:
        """Reset selection state"""
        self._start_point = None
        self._current_point = None
        self._current_rect = None
        self._preview_elements = []
        self._state = ToolState.ACTIVE
        self._cursor = QCursor(Qt.CursorShape.CrossCursor)
        self.cursor_changed.emit(self._cursor)
        self.state_changed.emit(self._state)
    
    def render_overlay(self, painter: QPainter) -> None:
        """Render selection rectangle and preview"""
        # Draw selection rectangle
        if self._current_rect and self._state == ToolState.SELECTING:
            painter.setPen(QPen(QColor(255, 140, 0), 1, Qt.PenStyle.DashLine))
            painter.setBrush(QColor(255, 140, 0, 30))
            painter.drawRect(self._current_rect)
        
        # Highlight preview elements
        if self._preview_elements:
            painter.setPen(QPen(QColor(255, 140, 0, 150), 1))
            for element in self._preview_elements:
                if hasattr(element, 'bounding_rect'):
                    painter.drawRect(element.bounding_rect)
        
        # Draw final selection
        if self._current_rect and self._state == ToolState.SELECTED:
            painter.setPen(QPen(QColor(255, 140, 0), 2))
            painter.drawRect(self._current_rect)
```

### Lasso Tool Implementation
```python
class LassoTool(SelectionTool):
    """Freeform selection with polygon-based selection"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._lasso_points = []
        self._closed_polygon = []
        self._min_points = 3
        self._min_distance = 5  # Minimum distance between points
        self._close_distance = 15  # Distance to close polygon
        self._smoothing_enabled = True
        
    def activate(self) -> None:
        """Activate lasso tool"""
        self._state = ToolState.ACTIVE
        self._cursor = QCursor(Qt.CursorShape.CrossCursor)
        self.cursor_changed.emit(self._cursor)
        self.state_changed.emit(self._state)
    
    def deactivate(self) -> None:
        """Deactivate lasso tool"""
        self._state = ToolState.INACTIVE
        self._reset_lasso()
        self.state_changed.emit(self._state)
    
    def handle_mouse_press(self, point: QPoint) -> bool:
        """Start lasso selection"""
        if self._state != ToolState.ACTIVE:
            return False
        
        self._lasso_points = [point]
        self._closed_polygon = []
        self._state = ToolState.SELECTING
        self.state_changed.emit(self._state)
        return True
    
    def handle_mouse_move(self, point: QPoint) -> bool:
        """Add points to lasso path"""
        if self._state == ToolState.SELECTING:
            # Check if we should close the polygon
            if len(self._lasso_points) >= self._min_points:
                distance_to_start = self._get_distance(point, self._lasso_points[0])
                if distance_to_start <= self._close_distance:
                    # Close polygon by connecting to start
                    self._closed_polygon = self._lasso_points + [self._lasso_points[0]]
                    self._cursor = QCursor(Qt.CursorShape.ClosedHandCursor)
                    self.cursor_changed.emit(self._cursor)
                    return True
            
            # Add point if it's far enough from the last point
            if not self._lasso_points or \
               self._get_distance(point, self._lasso_points[-1]) > self._min_distance:
                self._lasso_points.append(point)
                
                # Update cursor to show we're drawing
                self._cursor = QCursor(Qt.CursorShape.PointingHandCursor)
                self.cursor_changed.emit(self._cursor)
            
            return True
        return False
    
    def handle_mouse_release(self, point: QPoint) -> bool:
        """Complete lasso selection"""
        if self._state == ToolState.SELECTING:
            # Auto-close if we have enough points
            if len(self._lasso_points) >= self._min_points and not self._closed_polygon:
                self._closed_polygon = self._lasso_points + [self._lasso_points[0]]
            
            # Find elements in polygon
            if self._closed_polygon:
                # Apply smoothing if enabled
                if self._smoothing_enabled:
                    self._closed_polygon = self._smooth_polygon(self._closed_polygon)
                
                selected_elements = self._find_elements_in_polygon(self._closed_polygon)
                
                if selected_elements:
                    # Calculate bounding rect of polygon
                    polygon_rect = self._get_polygon_bounds(self._closed_polygon)
                    
                    result = SelectionResult(
                        elements=selected_elements,
                        geometry=polygon_rect,
                        tool_type="lasso",
                        timestamp=time.time(),
                        metadata={
                            "polygon_points": len(self._closed_polygon),
                            "element_count": len(selected_elements),
                            "polygon_area": self._calculate_polygon_area(self._closed_polygon)
                        }
                    )
                    self.selection_changed.emit(result)
                    self._state = ToolState.SELECTED
                    self.state_changed.emit(self._state)
                    return True
            
            # No valid selection
            self._reset_lasso()
            return True
        return False
    
    def _find_elements_in_polygon(self, polygon: List[QPoint]) -> List[Any]:
        """Find elements that intersect with polygon"""
        # This would use the geometry algorithms from Agent 1
        # For now, return empty list as placeholder
        return []
    
    def _smooth_polygon(self, polygon: List[QPoint]) -> List[QPoint]:
        """Apply smoothing to polygon points"""
        if len(polygon) < 3:
            return polygon
        
        smoothed = []
        for i in range(len(polygon)):
            prev_point = polygon[i-1]
            curr_point = polygon[i]
            next_point = polygon[(i+1) % len(polygon)]
            
            # Simple smoothing: average of adjacent points
            smooth_x = (prev_point.x() + curr_point.x() + next_point.x()) // 3
            smooth_y = (prev_point.y() + curr_point.y() + next_point.y()) // 3
            
            smoothed.append(QPoint(smooth_x, smooth_y))
        
        return smoothed
    
    def _get_polygon_bounds(self, polygon: List[QPoint]) -> QRect:
        """Get bounding rectangle of polygon"""
        if not polygon:
            return QRect()
        
        min_x = min(p.x() for p in polygon)
        min_y = min(p.y() for p in polygon)
        max_x = max(p.x() for p in polygon)
        max_y = max(p.y() for p in polygon)
        
        return QRect(min_x, min_y, max_x - min_x, max_y - min_y)
    
    def _calculate_polygon_area(self, polygon: List[QPoint]) -> float:
        """Calculate area of polygon using shoelace formula"""
        if len(polygon) < 3:
            return 0.0
        
        area = 0.0
        for i in range(len(polygon)):
            j = (i + 1) % len(polygon)
            area += polygon[i].x() * polygon[j].y()
            area -= polygon[j].x() * polygon[i].y()
        
        return abs(area) / 2.0
    
    def _get_distance(self, point1: QPoint, point2: QPoint) -> float:
        """Get distance between two points"""
        dx = point2.x() - point1.x()
        dy = point2.y() - point1.y()
        return (dx * dx + dy * dy) ** 0.5
    
    def _reset_lasso(self) -> None:
        """Reset lasso state"""
        self._lasso_points = []
        self._closed_polygon = []
        self._state = ToolState.ACTIVE
        self._cursor = QCursor(Qt.CursorShape.CrossCursor)
        self.cursor_changed.emit(self._cursor)
        self.state_changed.emit(self._state)
    
    def render_overlay(self, painter: QPainter) -> None:
        """Render lasso path and selection"""
        # Draw lasso path
        if self._lasso_points:
            painter.setPen(QPen(QColor(50, 205, 50), 2))
            for i in range(1, len(self._lasso_points)):
                painter.drawLine(self._lasso_points[i-1], self._lasso_points[i])
        
        # Draw closed polygon
        if self._closed_polygon:
            painter.setPen(QPen(QColor(50, 205, 50), 2))
            painter.setBrush(QColor(50, 205, 50, 30))
            painter.drawPolygon(self._closed_polygon)
        
        # Draw selection indicator
        if self._state == ToolState.SELECTED and self._closed_polygon:
            painter.setPen(QPen(QColor(50, 205, 50), 3))
            painter.drawPolygon(self._closed_polygon)
```

### Element-Aware Tool Implementation
```python
class ElementAwareTool(SelectionTool):
    """Smart selection that adapts to document element types"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._element_type_priority = ["text", "image", "table", "formula", "shape"]
        self._smart_selection_enabled = True
        self._context_radius = 20  # pixels
        self._selection_hierarchy = []
        
    def activate(self) -> None:
        """Activate element-aware tool"""
        self._state = ToolState.ACTIVE
        self._cursor = QCursor(Qt.CursorShape.PointingHandCursor)
        self.cursor_changed.emit(self._cursor)
        self.state_changed.emit(self._state)
    
    def deactivate(self) -> None:
        """Deactivate element-aware tool"""
        self._state = ToolState.INACTIVE
        self._selection_hierarchy = []
        self.state_changed.emit(self._state)
    
    def handle_mouse_press(self, point: QPoint) -> bool:
        """Smart element selection"""
        if self._state != ToolState.ACTIVE:
            return False
        
        element = self._find_best_element(point)
        if element:
            self._state = ToolState.SELECTING
            
            # Build selection hierarchy
            self._selection_hierarchy = self._build_selection_hierarchy(element, point)
            
            # Handle selection based on element type
            if element.type == "text":
                self._handle_text_selection(element, point)
            elif element.type == "table":
                self._handle_table_selection(element, point)
            elif element.type == "image":
                self._handle_image_selection(element, point)
            else:
                self._handle_generic_selection(element, point)
            
            return True
        return False
    
    def handle_mouse_move(self, point: QPoint) -> bool:
        """Handle smart hover and preview"""
        if self._state == ToolState.ACTIVE:
            element = self._find_best_element(point)
            if element:
                # Show preview of what would be selected
                preview_selection = self._get_preview_selection(element, point)
                # Update cursor based on element type
                self._update_cursor_for_element(element)
            return True
        return False
    
    def handle_mouse_release(self, point: QPoint) -> bool:
        """Complete smart selection"""
        if self._state == ToolState.SELECTING and self._selection_hierarchy:
            # Use the current selection from hierarchy
            current_selection = self._selection_hierarchy[0]  # Top of hierarchy
            
            result = SelectionResult(
                elements=current_selection['elements'],
                geometry=current_selection['geometry'],
                tool_type="element_aware",
                timestamp=time.time(),
                metadata={
                    "element_type": current_selection['type'],
                    "smart_selection": True,
                    "hierarchy_levels": len(self._selection_hierarchy),
                    "selection_context": current_selection.get('context', {})
                }
            )
            self.selection_changed.emit(result)
            self._state = ToolState.SELECTED
            self.state_changed.emit(self._state)
            return True
        return False
    
    def _find_best_element(self, point: QPoint) -> Optional[Any]:
        """Find the most appropriate element at point"""
        candidates = self._find_elements_at_point(point)
        
        if not candidates:
            return None
        
        # Sort by priority and proximity
        def element_score(element):
            type_priority = self._element_type_priority.index(element.type) \
                           if element.type in self._element_type_priority else 99
            distance = self._distance_to_element(point, element)
            size_factor = self._get_element_size_factor(element)
            return (type_priority, distance, size_factor)
        
        return min(candidates, key=element_score)
    
    def _build_selection_hierarchy(self, element: Any, point: QPoint) -> List[Dict]:
        """Build hierarchy of possible selections"""
        hierarchy = []
        
        # Level 1: Exact element
        hierarchy.append({
            'type': element.type,
            'elements': [element],
            'geometry': element.bounding_rect,
            'context': {'level': 'exact', 'click_point': point}
        })
        
        # Level 2: Contextual selection (e.g., word for text)
        if element.type == "text":
            word_selection = self._get_word_selection(element, point)
            if word_selection:
                hierarchy.append(word_selection)
        
        # Level 3: Container selection (e.g., paragraph, table row)
        container_selection = self._get_container_selection(element, point)
        if container_selection:
            hierarchy.append(container_selection)
        
        return hierarchy
    
    def _handle_text_selection(self, element: Any, point: QPoint) -> None:
        """Handle text-specific selection logic"""
        # Could expand to word, sentence, or paragraph based on context
        pass
    
    def _handle_table_selection(self, element: Any, point: QPoint) -> None:
        """Handle table-specific selection logic"""
        # Could select cell, row, column, or entire table
        pass
    
    def _handle_image_selection(self, element: Any, point: QPoint) -> None:
        """Handle image-specific selection logic"""
        # Could include caption or grouped elements
        pass
    
    def _handle_generic_selection(self, element: Any, point: QPoint) -> None:
        """Handle generic element selection"""
        # Default selection behavior
        pass
    
    def _update_cursor_for_element(self, element: Any) -> None:
        """Update cursor based on element type"""
        cursor_map = {
            "text": Qt.CursorShape.IBeamCursor,
            "image": Qt.CursorShape.OpenHandCursor,
            "table": Qt.CursorShape.PointingHandCursor,
            "formula": Qt.CursorShape.CrossCursor
        }
        
        cursor_shape = cursor_map.get(element.type, Qt.CursorShape.PointingHandCursor)
        self._cursor = QCursor(cursor_shape)
        self.cursor_changed.emit(self._cursor)
    
    def render_overlay(self, painter: QPainter) -> None:
        """Render smart selection with context"""
        if self._selection_hierarchy:
            current_selection = self._selection_hierarchy[0]
            
            # Use different colors for different element types
            color_map = {
                "text": QColor(138, 43, 226),
                "image": QColor(255, 69, 0),
                "table": QColor(0, 191, 255),
                "formula": QColor(255, 215, 0)
            }
            
            color = color_map.get(current_selection['type'], QColor(138, 43, 226))
            painter.setPen(QPen(color, 3))
            painter.drawRect(current_selection['geometry'])
            
            # Draw hierarchy indicators
            if len(self._selection_hierarchy) > 1:
                for i, level in enumerate(self._selection_hierarchy[1:], 1):
                    fade_color = QColor(color)
                    fade_color.setAlpha(255 - (i * 50))
                    painter.setPen(QPen(fade_color, 1))
                    painter.drawRect(level['geometry'])
```

## 🧪 Testing Requirements
- [ ] **Pointer Tool** - Single element selection accuracy
- [ ] **Rectangle Tool** - Area selection with drag behavior
- [ ] **Lasso Tool** - Freeform polygon selection
- [ ] **Element-Aware Tool** - Smart selection prioritization
- [ ] **Multi-Select** - Modifier key combinations
- [ ] **Animations** - Smooth tool transitions
- [ ] **Preview System** - Real-time feedback
- [ ] **Actions Menu** - Context menu integration
- [ ] **Shortcuts** - Keyboard input handling
- [ ] **Visual Feedback** - Overlay rendering accuracy

**Target:** 25+ comprehensive tests with >95% coverage

## 🔗 Integration Points

### Dependencies (From Agent 1)
- ✅ **Base Tool Interface** - Common tool architecture
- ✅ **State Management** - Tool state tracking
- ✅ **Geometry Algorithms** - Selection calculations
- ✅ **Event System** - Tool event handling
- ✅ **Cursor Management** - Cursor state control

### Provides for Other Agents
- **Tool Implementations** - Working selection tools
- **User Interaction** - Mouse and keyboard handling
- **Visual Feedback** - Tool-specific rendering
- **Multi-Select** - Selection combination logic
- **Actions System** - Context menu and tool actions

### Integration Notes
- **Performance:** Tools must respond within 16ms for smooth interaction
- **Consistency:** All tools must follow the same interaction patterns
- **Extensibility:** New tool types should be easy to add
- **Accessibility:** Tools must support keyboard navigation

## 🎯 Success Metrics
- **User Experience:** Smooth, intuitive tool interactions
- **Performance:** <16ms response time for all operations
- **Accuracy:** Precise selection with appropriate feedback
- **Consistency:** Uniform behavior across all tools
- **Extensibility:** Easy to add new tool types

## 🚀 Getting Started

### Step 1: Create Feature Branch
```bash
git checkout main
git pull origin main
git checkout -b feature/selection-tools-agent2-issue158
```

### Step 2: Wait for Agent 1 Foundation
- Agent 1 must complete base interfaces first
- Monitor Agent 1's progress on issue #157
- Coordinate on interface requirements

### Step 3: Implement Tool Classes
1. Start with Pointer Tool (simplest)
2. Implement Rectangle Tool
3. Add Lasso Tool
4. Complete Element-Aware Tool
5. Add multi-select and animations

### Step 4: User Experience Testing
1. Test all mouse interactions
2. Verify visual feedback
3. Test keyboard shortcuts
4. Validate performance

**Related Issues:**
- Main Issue: #19 - Advanced Document Processing Pipeline Selection Tools
- Sub-Issue: #158 - Tool Implementations & User Interaction
- Dependency: #157 - Core Infrastructure (Agent 1)
- Next: #159 - Optimization & Advanced Features (Agent 3)

**Timeline:** 2-3 days for complete implementation and testing.