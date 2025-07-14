# AGENT 1 - SELECTION TOOLS: Core Infrastructure & Base Classes

## 🎯 Your Assignment
You are **Agent 1** in the 4-agent parallel development of the **Advanced Document Processing Pipeline Selection Tools Implementation**. Your focus is on **Core Infrastructure & Base Classes** - the foundational architecture that all other agents will build upon.

## 📋 Your Specific Tasks
- [ ] Create base selection tool architecture in `src/torematrix/ui/viewer/tools/base.py`
- [ ] Implement abstract base class `SelectionTool` with common interfaces
- [ ] Create tool state management system with enums and state tracking
- [ ] Implement core selection geometry algorithms (point-in-polygon, intersection testing)
- [ ] Create cursor management system for different tool states
- [ ] Implement tool lifecycle management (activate, deactivate, reset)
- [ ] Create selection result data structures and interfaces
- [ ] Implement basic event handling infrastructure for tools
- [ ] Create tool registration and discovery system
- [ ] Implement core selection validation and sanitization

## 📁 Files to Create

```
src/torematrix/ui/viewer/tools/
├── __init__.py                     # Tool package exports
├── base.py                         # Core base classes and interfaces
├── geometry.py                     # Selection geometry algorithms
├── state.py                        # Tool state management
├── cursor.py                       # Cursor management system
├── events.py                       # Tool event definitions
└── registry.py                     # Tool registration system

tests/unit/viewer/tools/
├── __init__.py
├── test_base.py                    # Base class tests
├── test_geometry.py                # Geometry algorithm tests
├── test_state.py                   # State management tests
├── test_cursor.py                  # Cursor management tests
├── test_events.py                  # Event system tests
└── test_registry.py                # Tool registry tests
```

## 🔧 Technical Implementation Details

### Core Base Class Structure
```python
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
from dataclasses import dataclass
from PyQt6.QtCore import QObject, pyqtSignal, QPoint, QRect
from PyQt6.QtGui import QCursor, QPainter, QPen, QBrush
import time

class ToolState(Enum):
    INACTIVE = "inactive"
    ACTIVE = "active"
    SELECTING = "selecting"
    SELECTED = "selected"
    HOVER = "hover"

@dataclass
class SelectionResult:
    elements: List[Any]
    geometry: QRect
    tool_type: str
    timestamp: float
    metadata: Dict[str, Any]

class SelectionTool(QObject, ABC):
    # Signals for tool events
    selection_changed = pyqtSignal(SelectionResult)
    state_changed = pyqtSignal(ToolState)
    cursor_changed = pyqtSignal(QCursor)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = ToolState.INACTIVE
        self._selection_result = None
        self._cursor = QCursor()
    
    @abstractmethod
    def activate(self) -> None:
        """Activate the tool"""
        pass
    
    @abstractmethod
    def deactivate(self) -> None:
        """Deactivate the tool"""
        pass
    
    @abstractmethod
    def handle_mouse_press(self, point: QPoint) -> bool:
        """Handle mouse press events"""
        pass
    
    @abstractmethod
    def handle_mouse_move(self, point: QPoint) -> bool:
        """Handle mouse move events"""
        pass
    
    @abstractmethod
    def handle_mouse_release(self, point: QPoint) -> bool:
        """Handle mouse release events"""
        pass
    
    @abstractmethod
    def render_overlay(self, painter: QPainter) -> None:
        """Render tool-specific overlay graphics"""
        pass
```

### Selection Geometry Algorithms
```python
class SelectionGeometry:
    @staticmethod
    def point_in_polygon(point: QPoint, polygon: List[QPoint]) -> bool:
        """Ray casting algorithm for point-in-polygon testing"""
        x, y = point.x(), point.y()
        n = len(polygon)
        inside = False
        
        p1x, p1y = polygon[0].x(), polygon[0].y()
        for i in range(1, n + 1):
            p2x, p2y = polygon[i % n].x(), polygon[i % n].y()
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        
        return inside
    
    @staticmethod
    def rect_intersects_elements(rect: QRect, elements: List[Any]) -> List[Any]:
        """Find elements that intersect with rectangle"""
        intersecting = []
        for element in elements:
            if hasattr(element, 'bounding_rect'):
                if rect.intersects(element.bounding_rect):
                    intersecting.append(element)
        return intersecting
    
    @staticmethod
    def polygon_intersects_elements(polygon: List[QPoint], elements: List[Any]) -> List[Any]:
        """Find elements that intersect with polygon"""
        intersecting = []
        for element in elements:
            if hasattr(element, 'bounding_rect'):
                # Check if any corner of element rect is inside polygon
                rect = element.bounding_rect
                corners = [
                    QPoint(rect.left(), rect.top()),
                    QPoint(rect.right(), rect.top()),
                    QPoint(rect.left(), rect.bottom()),
                    QPoint(rect.right(), rect.bottom())
                ]
                
                for corner in corners:
                    if SelectionGeometry.point_in_polygon(corner, polygon):
                        intersecting.append(element)
                        break
        return intersecting
```

### Tool State Management
```python
class ToolStateManager:
    """Manages tool states and transitions"""
    
    def __init__(self):
        self._current_state = ToolState.INACTIVE
        self._previous_state = None
        self._valid_transitions = {
            ToolState.INACTIVE: [ToolState.ACTIVE],
            ToolState.ACTIVE: [ToolState.INACTIVE, ToolState.SELECTING, ToolState.HOVER],
            ToolState.SELECTING: [ToolState.ACTIVE, ToolState.SELECTED],
            ToolState.SELECTED: [ToolState.ACTIVE, ToolState.SELECTING],
            ToolState.HOVER: [ToolState.ACTIVE, ToolState.SELECTING]
        }
    
    def can_transition(self, new_state: ToolState) -> bool:
        """Check if transition to new state is valid"""
        return new_state in self._valid_transitions.get(self._current_state, [])
    
    def transition(self, new_state: ToolState) -> bool:
        """Transition to new state if valid"""
        if self.can_transition(new_state):
            self._previous_state = self._current_state
            self._current_state = new_state
            return True
        return False
    
    def get_current_state(self) -> ToolState:
        """Get current state"""
        return self._current_state
    
    def get_previous_state(self) -> Optional[ToolState]:
        """Get previous state"""
        return self._previous_state
    
    def reset(self) -> None:
        """Reset to inactive state"""
        self._previous_state = self._current_state
        self._current_state = ToolState.INACTIVE
```

### Cursor Management System
```python
from PyQt6.QtGui import QCursor, QPixmap, QPainter, QPen, QBrush
from PyQt6.QtCore import Qt

class CursorManager:
    """Manages cursors for different tool states"""
    
    def __init__(self):
        self._cursors = {}
        self._current_cursor = None
        self._create_default_cursors()
    
    def _create_default_cursors(self) -> None:
        """Create default cursors for different states"""
        self._cursors[ToolState.INACTIVE] = QCursor(Qt.CursorShape.ArrowCursor)
        self._cursors[ToolState.ACTIVE] = QCursor(Qt.CursorShape.CrossCursor)
        self._cursors[ToolState.SELECTING] = QCursor(Qt.CursorShape.ClosedHandCursor)
        self._cursors[ToolState.SELECTED] = QCursor(Qt.CursorShape.OpenHandCursor)
        self._cursors[ToolState.HOVER] = QCursor(Qt.CursorShape.PointingHandCursor)
    
    def get_cursor(self, state: ToolState) -> QCursor:
        """Get cursor for specific state"""
        return self._cursors.get(state, self._cursors[ToolState.INACTIVE])
    
    def set_cursor(self, state: ToolState, cursor: QCursor) -> None:
        """Set cursor for specific state"""
        self._cursors[state] = cursor
    
    def create_custom_cursor(self, size: int = 16, color: str = "blue") -> QCursor:
        """Create custom cursor"""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw custom cursor design
        pen = QPen(Qt.GlobalColor.blue, 2)
        painter.setPen(pen)
        painter.drawEllipse(2, 2, size-4, size-4)
        painter.drawLine(size//2, 0, size//2, size)
        painter.drawLine(0, size//2, size, size//2)
        
        painter.end()
        return QCursor(pixmap)
```

### Tool Registry System
```python
class ToolRegistry:
    """Registry for tool discovery and management"""
    
    def __init__(self):
        self._tools = {}
        self._tool_instances = {}
        self._active_tool = None
    
    def register_tool(self, name: str, tool_class: type) -> None:
        """Register a tool class"""
        self._tools[name] = tool_class
    
    def unregister_tool(self, name: str) -> bool:
        """Unregister a tool"""
        if name in self._tools:
            del self._tools[name]
            if name in self._tool_instances:
                del self._tool_instances[name]
            return True
        return False
    
    def get_tool(self, name: str) -> Optional[SelectionTool]:
        """Get tool instance"""
        if name not in self._tools:
            return None
        
        if name not in self._tool_instances:
            self._tool_instances[name] = self._tools[name]()
        
        return self._tool_instances[name]
    
    def get_available_tools(self) -> List[str]:
        """Get list of available tool names"""
        return list(self._tools.keys())
    
    def set_active_tool(self, name: str) -> bool:
        """Set active tool"""
        if name in self._tools:
            # Deactivate current tool
            if self._active_tool:
                current_tool = self.get_tool(self._active_tool)
                if current_tool:
                    current_tool.deactivate()
            
            # Activate new tool
            new_tool = self.get_tool(name)
            if new_tool:
                new_tool.activate()
                self._active_tool = name
                return True
        return False
    
    def get_active_tool(self) -> Optional[SelectionTool]:
        """Get active tool instance"""
        if self._active_tool:
            return self.get_tool(self._active_tool)
        return None
```

## 🧪 Testing Requirements
- [ ] **Base class functionality** - Abstract interface compliance
- [ ] **State management** - State transitions and validation
- [ ] **Geometry algorithms** - Point-in-polygon, intersection testing
- [ ] **Cursor management** - Cursor changes and restoration
- [ ] **Event handling** - Signal emission and handling
- [ ] **Tool registration** - Discovery and instantiation
- [ ] **Error handling** - Invalid state transitions and edge cases
- [ ] **Performance** - Geometry calculations under load
- [ ] **Thread safety** - Concurrent access to tool state
- [ ] **Memory management** - Proper cleanup and resource management

**Target:** 20+ comprehensive tests with >95% coverage

## 🔗 Integration Points

### Dependencies (Available)
- ✅ **Event Bus System** - For tool state broadcasting
- ✅ **Coordinate Mapping** - For accurate transformations
- ✅ **Overlay System** - For visual feedback rendering

### Provides for Other Agents
- **Base Tool Interface** - Common interface for all tools
- **State Management** - Tool state tracking and transitions
- **Geometry Algorithms** - Selection calculation utilities
- **Event System** - Tool event definitions and handling
- **Cursor Management** - Cursor state and appearance

### Integration Notes
- **Thread Safety:** All base classes must support concurrent access
- **Performance:** Geometry calculations must be optimized for real-time use
- **Extensibility:** Base classes should support future tool types
- **Event Consistency:** All tools must emit consistent event signatures

## 📊 Success Criteria
- [ ] Complete abstract base class with all required methods
- [ ] Functional state management system with proper transitions
- [ ] Accurate geometry algorithms with comprehensive testing
- [ ] Proper cursor management with visual feedback
- [ ] Robust event handling system with type safety
- [ ] Tool registration system supporting dynamic discovery
- [ ] Error handling for all edge cases and invalid states
- [ ] Performance benchmarks meet real-time requirements
- [ ] Documentation covers all public APIs and usage patterns
- [ ] Integration tests with existing overlay and coordinate systems

## 🎯 Acceptance Criteria
- [ ] All base classes and interfaces implemented and tested
- [ ] State management system handles all tool lifecycles
- [ ] Geometry algorithms provide accurate selection calculations
- [ ] Cursor system provides appropriate visual feedback
- [ ] Event system supports all tool interactions
- [ ] Registry system enables dynamic tool discovery
- [ ] Error handling prevents crashes from invalid operations
- [ ] Performance meets real-time interaction requirements
- [ ] Full integration with existing coordinate and overlay systems
- [ ] Comprehensive documentation and API examples

## 📋 Definition of Done
- [ ] All implementation tasks completed and tested
- [ ] >95% test coverage achieved
- [ ] All acceptance criteria met and verified
- [ ] Integration tests passing with existing systems
- [ ] Performance benchmarks meet requirements
- [ ] Documentation complete with examples
- [ ] Code review passed with team standards
- [ ] Ready for Agent 2 to build specific tools

## 🚀 Getting Started

### Step 1: Create Feature Branch
```bash
git checkout main
git pull origin main
git checkout -b feature/selection-tools-agent1-issue157
```

### Step 2: Create Directory Structure
```bash
mkdir -p src/torematrix/ui/viewer/tools
mkdir -p tests/unit/viewer/tools
```

### Step 3: Implement Base Architecture
1. Start with `src/torematrix/ui/viewer/tools/base.py`
2. Implement core interfaces and abstract classes
3. Add comprehensive type hints and documentation
4. Create test files alongside implementation

### Step 4: Testing Strategy
1. Write tests for each component as you implement
2. Ensure >95% test coverage
3. Test thread safety and performance
4. Validate integration with existing systems

### Step 5: Documentation
1. Document all public APIs
2. Include usage examples
3. Cover integration patterns
4. Document performance characteristics

## 🔄 Communication Protocol

### Progress Updates
- Comment on sub-issue #157 with daily progress
- Use GitHub issue checkboxes to track completion
- Report any blockers or dependency issues immediately

### Integration Coordination
- Your work enables all other agents
- Ensure APIs are stable before other agents start
- Coordinate with Agent 2 on interface requirements

### Quality Assurance
- All tests must pass before completion
- Performance benchmarks must be met
- Documentation must be comprehensive
- Code review must pass team standards

## 🎯 Success Metrics
- **Code Quality:** >95% test coverage, no critical issues
- **Performance:** Geometry algorithms <1ms response time
- **Documentation:** Complete API documentation with examples
- **Integration:** Seamless integration with existing systems
- **Architecture:** Clean, extensible design supporting future tools

This is the foundation for the entire selection tools system. Your work quality directly impacts all other agents' success.

**Related Issues:**
- Main Issue: #19 - Advanced Document Processing Pipeline Selection Tools
- Sub-Issue: #157 - Core Infrastructure & Base Classes
- Next: #158 - Tool Implementations (Agent 2)

**Timeline:** 2-3 days for complete implementation, testing, and documentation.