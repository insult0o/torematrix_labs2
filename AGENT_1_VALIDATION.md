# Agent 1: Core Validation Framework & State Management

## 🎯 **Mission Statement**
**Agent 1 Focus**: Build the foundational validation framework with comprehensive state management, basic area selection capabilities, and robust integration hooks that Agent 2, 3, and 4 will extend and build upon.

## 📋 **Sub-Issue Assignment**
- **GitHub Issue**: #26.1 - Core Validation Framework & State Management
- **Branch**: `feature/validation-core-agent1-issue26-1`
- **Dependencies**: None (Foundation agent)
- **Duration**: 4 days
- **Integration**: Provides foundation APIs for Agent 2 (advanced selection), Agent 3 (UI), Agent 4 (integration)

---

## 🏗️ **Technical Architecture**

### **Core Components to Implement**

#### **1. Enhanced Drawing State Management (`drawing_state.py`)**
```python
class DrawingStateManager(QObject):
    """Enhanced drawing state manager with comprehensive PyQt6 signals."""
    
    # State change signals
    mode_changed = pyqtSignal(DrawingMode)
    state_changed = pyqtSignal(DrawingState)
    area_selected = pyqtSignal(DrawingArea)
    selection_started = pyqtSignal(QPoint)
    selection_updated = pyqtSignal(QRect)
    selection_completed = pyqtSignal(DrawingArea)
    selection_cancelled = pyqtSignal()
    
    # Page and session signals
    page_changed = pyqtSignal(int, QPixmap)
    session_started = pyqtSignal(str)
    session_ended = pyqtSignal(str, dict)
    
    def __init__(self):
        super().__init__()
        self.current_mode = DrawingMode.IDLE
        self.current_state = DrawingState.READY
        self.active_session: Optional[DrawingSession] = None
        self.page_image: Optional[QPixmap] = None
        self.page_number = 0
        self.selected_areas: List[DrawingArea] = []
        
        self._setup_state_machine()
    
    def _setup_state_machine(self):
        """Setup comprehensive state machine with validation."""
        self.valid_transitions = {
            DrawingMode.IDLE: [DrawingMode.SELECTION, DrawingMode.PREVIEW],
            DrawingMode.SELECTION: [DrawingMode.IDLE, DrawingMode.DRAWING, DrawingMode.PREVIEW],
            DrawingMode.DRAWING: [DrawingMode.SELECTION, DrawingMode.CONFIRMING],
            DrawingMode.CONFIRMING: [DrawingMode.IDLE, DrawingMode.SELECTION],
            DrawingMode.PREVIEW: [DrawingMode.IDLE, DrawingMode.SELECTION]
        }
    
    def transition_to_mode(self, new_mode: DrawingMode) -> bool:
        """Safely transition between drawing modes."""
        if new_mode in self.valid_transitions.get(self.current_mode, []):
            old_mode = self.current_mode
            self.current_mode = new_mode
            self.mode_changed.emit(new_mode)
            logger.debug(f"Mode transition: {old_mode} -> {new_mode}")
            return True
        else:
            logger.warning(f"Invalid mode transition: {self.current_mode} -> {new_mode}")
            return False
    
    def start_area_selection(self, selection_type: str) -> bool:
        """Start area selection workflow."""
        if self.transition_to_mode(DrawingMode.SELECTION):
            self.current_state = DrawingState.SELECTING
            self.state_changed.emit(self.current_state)
            return True
        return False
    
    def complete_area_selection(self, area: DrawingArea) -> bool:
        """Complete area selection and transition to confirmation."""
        if self.current_mode == DrawingMode.SELECTION:
            self.selected_areas.append(area)
            self.area_selected.emit(area)
            self.transition_to_mode(DrawingMode.CONFIRMING)
            return True
        return False

class DrawingArea:
    """Enhanced drawing area with metadata and validation."""
    
    def __init__(self, shape: SelectionShape, metadata: Dict[str, Any] = None):
        self.area_id = str(uuid.uuid4())
        self.shape = shape
        self.metadata = metadata or {}
        self.created_at = datetime.now()
        self.page_number = 0
        self.confidence = 1.0
        self.validated = False
        
    def get_bounding_rect(self) -> QRect:
        """Get bounding rectangle for the area."""
        return self.shape.get_bounding_rect()
    
    def contains_point(self, point: QPoint) -> bool:
        """Check if point is within the selected area."""
        return self.shape.contains_point(point)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert area to dictionary for serialization."""
        return {
            'area_id': self.area_id,
            'shape_type': self.shape.__class__.__name__,
            'shape_data': self.shape.to_dict(),
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'page_number': self.page_number,
            'confidence': self.confidence,
            'validated': self.validated
        }

class DrawingSession:
    """Session container for validation workflow state."""
    
    def __init__(self, session_id: str, document_path: Path):
        self.session_id = session_id
        self.document_path = document_path
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None
        self.status = SessionStatus.ACTIVE
        
        # Session data
        self.pages_processed: Set[int] = set()
        self.areas_selected: List[DrawingArea] = []
        self.validation_results: Dict[str, Any] = {}
        self.configuration: Dict[str, Any] = {}
```

#### **2. Core Area Selection Framework (`area_select.py`)**
```python
class ValidationAreaSelector(QWidget):
    """Core area selection widget with foundation capabilities."""
    
    # Selection signals for Agent 2-4 integration
    selection_started = pyqtSignal(QPoint, str)  # point, tool_type
    selection_updated = pyqtSignal(QRect, str)   # current_rect, tool_type
    selection_completed = pyqtSignal(DrawingArea)
    selection_cancelled = pyqtSignal()
    tool_changed = pyqtSignal(str)               # new_tool_type
    
    def __init__(self, state_manager: DrawingStateManager, parent=None):
        super().__init__(parent)
        
        self.state_manager = state_manager
        self.current_tool: Optional[SelectionTool] = None
        self.active_selection: Optional[SelectionShape] = None
        self.page_image: Optional[QPixmap] = None
        self.selection_constraints: List[SelectionConstraint] = []
        
        self._setup_ui()
        self._setup_tools()
        self._connect_signals()
    
    def _setup_tools(self):
        """Initialize selection tools."""
        self.available_tools = {
            'rectangle': RectangleSelectionTool(self),
            'polygon': PolygonSelectionTool(self),
            'freehand': FreehandSelectionTool(self)  # Basic implementation
        }
        
        # Set default tool
        self.set_active_tool('rectangle')
    
    def set_active_tool(self, tool_name: str) -> bool:
        """Set the active selection tool."""
        if tool_name in self.available_tools:
            old_tool = self.current_tool
            self.current_tool = self.available_tools[tool_name]
            
            # Configure tool
            self.current_tool.set_constraints(self.selection_constraints)
            
            self.tool_changed.emit(tool_name)
            logger.debug(f"Tool changed: {old_tool} -> {tool_name}")
            return True
        return False
    
    def start_selection(self, start_point: QPoint) -> bool:
        """Start area selection at given point."""
        if not self.current_tool or not self.page_image:
            return False
        
        # Check state manager
        if not self.state_manager.start_area_selection(self.current_tool.tool_type):
            return False
        
        # Initialize selection
        self.active_selection = self.current_tool.start_selection(start_point)
        self.selection_started.emit(start_point, self.current_tool.tool_type)
        
        return True
    
    def update_selection(self, current_point: QPoint) -> bool:
        """Update ongoing selection."""
        if not self.active_selection or not self.current_tool:
            return False
        
        # Update selection shape
        self.current_tool.update_selection(self.active_selection, current_point)
        
        # Emit update signal
        current_rect = self.active_selection.get_bounding_rect()
        self.selection_updated.emit(current_rect, self.current_tool.tool_type)
        
        # Trigger repaint
        self.update()
        return True
    
    def complete_selection(self) -> Optional[DrawingArea]:
        """Complete the current selection."""
        if not self.active_selection or not self.current_tool:
            return None
        
        # Finalize selection
        final_shape = self.current_tool.complete_selection(self.active_selection)
        if not final_shape:
            return None
        
        # Create drawing area
        area = DrawingArea(final_shape)
        area.page_number = self.state_manager.page_number
        
        # Update state manager
        if self.state_manager.complete_area_selection(area):
            self.selection_completed.emit(area)
            self.active_selection = None
            return area
        
        return None
    
    def cancel_selection(self):
        """Cancel the current selection."""
        if self.active_selection:
            self.active_selection = None
            self.state_manager.transition_to_mode(DrawingMode.IDLE)
            self.selection_cancelled.emit()
            self.update()

class SelectionConstraint:
    """Base class for selection constraints."""
    
    def __init__(self, constraint_type: str, parameters: Dict[str, Any]):
        self.constraint_type = constraint_type
        self.parameters = parameters
        self.enabled = True
    
    def validate_selection(self, shape: SelectionShape) -> bool:
        """Validate selection against constraint."""
        raise NotImplementedError
    
    def get_constraint_feedback(self, shape: SelectionShape) -> str:
        """Get user feedback for constraint violations."""
        raise NotImplementedError

class MinimumSizeConstraint(SelectionConstraint):
    """Constraint for minimum selection size."""
    
    def __init__(self, min_width: int, min_height: int):
        super().__init__('minimum_size', {
            'min_width': min_width,
            'min_height': min_height
        })
    
    def validate_selection(self, shape: SelectionShape) -> bool:
        rect = shape.get_bounding_rect()
        return (rect.width() >= self.parameters['min_width'] and 
                rect.height() >= self.parameters['min_height'])
```

#### **3. Selection Shape Infrastructure (`shapes.py`)**
```python
class SelectionShape(ABC):
    """Abstract base class for selection shapes with Agent 2-4 integration hooks."""
    
    def __init__(self):
        self.shape_id = str(uuid.uuid4())
        self.created_at = datetime.now()
        self.metadata: Dict[str, Any] = {}
        self.style = ShapeStyle()
    
    @abstractmethod
    def get_bounding_rect(self) -> QRect:
        """Get bounding rectangle of the shape."""
        pass
    
    @abstractmethod
    def contains_point(self, point: QPoint) -> bool:
        """Check if point is inside the shape."""
        pass
    
    @abstractmethod
    def draw(self, painter: QPainter, scale: float = 1.0):
        """Draw the shape with given painter."""
        pass
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Serialize shape to dictionary."""
        pass
    
    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SelectionShape':
        """Deserialize shape from dictionary."""
        pass
    
    # Agent 2 integration hooks
    def get_snap_points(self) -> List[QPoint]:
        """Get points suitable for snapping (Agent 2 extension point)."""
        return []
    
    def get_magnetic_edges(self) -> List[Tuple[QPoint, QPoint]]:
        """Get edges for magnetic snapping (Agent 2 extension point)."""
        return []

class RectangleShape(SelectionShape):
    """Rectangle selection shape with comprehensive functionality."""
    
    def __init__(self, top_left: QPoint, bottom_right: QPoint):
        super().__init__()
        self.top_left = top_left
        self.bottom_right = bottom_right
        self._normalize_coordinates()
    
    def _normalize_coordinates(self):
        """Ensure top_left is actually top-left and bottom_right is bottom-right."""
        x1, y1 = self.top_left.x(), self.top_left.y()
        x2, y2 = self.bottom_right.x(), self.bottom_right.y()
        
        self.top_left = QPoint(min(x1, x2), min(y1, y2))
        self.bottom_right = QPoint(max(x1, x2), max(y1, y2))
    
    def get_bounding_rect(self) -> QRect:
        """Get bounding rectangle."""
        return QRect(self.top_left, self.bottom_right)
    
    def contains_point(self, point: QPoint) -> bool:
        """Check if point is inside rectangle."""
        rect = self.get_bounding_rect()
        return rect.contains(point)
    
    def draw(self, painter: QPainter, scale: float = 1.0):
        """Draw rectangle with current style."""
        painter.save()
        
        # Apply style
        painter.setPen(self.style.get_pen(scale))
        painter.setBrush(self.style.get_brush())
        
        # Draw rectangle
        rect = QRect(
            QPoint(int(self.top_left.x() * scale), int(self.top_left.y() * scale)),
            QPoint(int(self.bottom_right.x() * scale), int(self.bottom_right.y() * scale))
        )
        painter.drawRect(rect)
        
        painter.restore()
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'shape_type': 'rectangle',
            'shape_id': self.shape_id,
            'top_left': [self.top_left.x(), self.top_left.y()],
            'bottom_right': [self.bottom_right.x(), self.bottom_right.y()],
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RectangleShape':
        """Deserialize from dictionary."""
        shape = cls(
            QPoint(*data['top_left']),
            QPoint(*data['bottom_right'])
        )
        shape.shape_id = data['shape_id']
        shape.metadata = data.get('metadata', {})
        return shape
    
    # Agent 2 integration points
    def get_snap_points(self) -> List[QPoint]:
        """Get corner and midpoint snap points."""
        rect = self.get_bounding_rect()
        return [
            rect.topLeft(), rect.topRight(),
            rect.bottomLeft(), rect.bottomRight(),
            QPoint(rect.center().x(), rect.top()),    # Top center
            QPoint(rect.center().x(), rect.bottom()), # Bottom center
            QPoint(rect.left(), rect.center().y()),   # Left center
            QPoint(rect.right(), rect.center().y())   # Right center
        ]

class PolygonShape(SelectionShape):
    """Polygon selection shape with Agent 2 integration hooks."""
    
    def __init__(self, points: List[QPoint]):
        super().__init__()
        self.points = points.copy() if points else []
        self._polygon = QPolygon(self.points)
    
    def add_point(self, point: QPoint):
        """Add point to polygon."""
        self.points.append(point)
        self._polygon = QPolygon(self.points)
    
    def complete_polygon(self):
        """Close the polygon by connecting last to first point."""
        if len(self.points) > 2:
            self._polygon = QPolygon(self.points)
    
    def get_bounding_rect(self) -> QRect:
        """Get bounding rectangle."""
        return self._polygon.boundingRect()
    
    def contains_point(self, point: QPoint) -> bool:
        """Check if point is inside polygon."""
        return self._polygon.containsPoint(point, Qt.FillRule.OddEvenFill)
    
    def draw(self, painter: QPainter, scale: float = 1.0):
        """Draw polygon with current style."""
        if len(self.points) < 2:
            return
        
        painter.save()
        
        # Apply style
        painter.setPen(self.style.get_pen(scale))
        painter.setBrush(self.style.get_brush())
        
        # Scale points
        scaled_points = [
            QPoint(int(p.x() * scale), int(p.y() * scale)) 
            for p in self.points
        ]
        scaled_polygon = QPolygon(scaled_points)
        
        # Draw polygon
        painter.drawPolygon(scaled_polygon)
        
        painter.restore()

class SelectionTool(ABC):
    """Abstract base class for selection tools."""
    
    def __init__(self, tool_type: str):
        self.tool_type = tool_type
        self.constraints: List[SelectionConstraint] = []
        self.enabled = True
    
    def set_constraints(self, constraints: List[SelectionConstraint]):
        """Set validation constraints for this tool."""
        self.constraints = constraints
    
    @abstractmethod
    def start_selection(self, start_point: QPoint) -> Optional[SelectionShape]:
        """Start new selection."""
        pass
    
    @abstractmethod
    def update_selection(self, shape: SelectionShape, current_point: QPoint) -> bool:
        """Update ongoing selection."""
        pass
    
    @abstractmethod
    def complete_selection(self, shape: SelectionShape) -> Optional[SelectionShape]:
        """Complete and validate selection."""
        pass

class RectangleSelectionTool(SelectionTool):
    """Rectangle selection tool implementation."""
    
    def __init__(self, parent=None):
        super().__init__('rectangle')
        self.parent = parent
        self.start_point: Optional[QPoint] = None
    
    def start_selection(self, start_point: QPoint) -> Optional[SelectionShape]:
        """Start rectangle selection."""
        self.start_point = start_point
        return RectangleShape(start_point, start_point)
    
    def update_selection(self, shape: SelectionShape, current_point: QPoint) -> bool:
        """Update rectangle selection."""
        if isinstance(shape, RectangleShape) and self.start_point:
            shape.bottom_right = current_point
            shape._normalize_coordinates()
            return True
        return False
    
    def complete_selection(self, shape: SelectionShape) -> Optional[SelectionShape]:
        """Complete rectangle selection with validation."""
        if not isinstance(shape, RectangleShape):
            return None
        
        # Validate constraints
        for constraint in self.constraints:
            if constraint.enabled and not constraint.validate_selection(shape):
                logger.warning(f"Selection failed constraint: {constraint.constraint_type}")
                return None
        
        return shape
```

---

## 🔗 **Integration Architecture for Agent 2-4**

### **API Extension Points**
```python
# Agent 2 will extend these classes
class EnhancedValidationAreaSelector(ValidationAreaSelector):
    """Agent 2 will add snapping and advanced selection."""
    pass

class AdvancedDrawingStateManager(DrawingStateManager):
    """Agent 2 will add performance monitoring and advanced state tracking."""
    pass

# Agent 3 will use these signals
validation_ui_signals = [
    'selection_started', 'selection_completed', 'tool_changed',
    'mode_changed', 'state_changed', 'area_selected'
]

# Agent 4 will coordinate through these interfaces
class ValidationIntegrationHooks:
    """Integration hooks for Agent 4 coordination."""
    
    def register_state_manager(self, state_manager: DrawingStateManager):
        """Register state manager for integration."""
        pass
    
    def register_area_selector(self, area_selector: ValidationAreaSelector):
        """Register area selector for integration."""
        pass
```

---

## 📊 **Implementation Timeline**

### **Day 1: State Management Foundation**
- [ ] Implement enhanced DrawingStateManager with complete state machine
- [ ] Create DrawingArea and DrawingSession data models
- [ ] Setup PyQt6 signal framework for Agent 2-4 integration
- [ ] Basic state transition validation and error handling

### **Day 2: Core Area Selection Framework**
- [ ] Implement ValidationAreaSelector base functionality
- [ ] Create SelectionConstraint system
- [ ] Add tool switching and configuration
- [ ] Integration with DrawingStateManager

### **Day 3: Selection Shape Infrastructure**
- [ ] Implement SelectionShape abstract base class
- [ ] Create RectangleShape and PolygonShape implementations
- [ ] Build SelectionTool framework (Rectangle, Polygon, basic Freehand)
- [ ] Add shape serialization and validation

### **Day 4: Integration Hooks & Testing**
- [ ] Create Agent 2-4 integration points and APIs
- [ ] Implement comprehensive unit testing (>95% coverage)
- [ ] Performance benchmarking and optimization
- [ ] Documentation and API specification

---

## 🧪 **Testing Requirements**

### **Unit Tests (Target: >95% Coverage)**
```python
class TestDrawingStateManager:
    """Test drawing state management functionality."""
    
    def test_state_transitions(self):
        """Test valid and invalid state transitions."""
        
    def test_mode_changes_with_signals(self):
        """Test mode changes emit correct signals."""
        
    def test_area_selection_workflow(self):
        """Test complete area selection workflow."""

class TestValidationAreaSelector:
    """Test area selection functionality."""
    
    def test_tool_switching(self):
        """Test switching between selection tools."""
        
    def test_selection_constraints(self):
        """Test selection constraint validation."""
        
    def test_signal_emission(self):
        """Test signal emission during selection."""

class TestSelectionShapes:
    """Test selection shape implementations."""
    
    def test_rectangle_operations(self):
        """Test rectangle creation, validation, serialization."""
        
    def test_polygon_operations(self):
        """Test polygon creation, validation, serialization."""
        
    def test_shape_serialization(self):
        """Test shape to_dict/from_dict methods."""
```

### **Performance Benchmarks**
- **State Transitions**: <5ms per transition
- **Selection Response**: <100ms for tool changes
- **Shape Rendering**: 60 FPS with 100+ shapes
- **Memory Usage**: <5MB for 1000+ areas
- **Signal Processing**: <1ms per signal emission

### **Integration Tests**
```python
class TestAgent2Integration:
    """Test Agent 2 integration points."""
    
    def test_snap_point_extension(self):
        """Test snap point extension interface."""
        
    def test_magnetic_edge_hooks(self):
        """Test magnetic edge detection hooks."""

class TestAgent3Integration:
    """Test Agent 3 UI integration points."""
    
    def test_signal_connectivity(self):
        """Test PyQt6 signal connectivity for UI."""
        
    def test_state_synchronization(self):
        """Test state synchronization with UI components."""
```

---

## 🎯 **Success Criteria**

### **Technical Achievements**
- [ ] **Complete State Machine**: All drawing modes and transitions implemented
- [ ] **Selection Framework**: Rectangle, polygon, and basic freehand selection functional
- [ ] **Shape Infrastructure**: Serializable, scalable shape system
- [ ] **Integration APIs**: Clean extension points for Agent 2-4
- [ ] **Signal Framework**: Complete PyQt6 signal system operational

### **Quality Metrics**
- [ ] **Test Coverage**: >95% unit test coverage achieved
- [ ] **Performance**: All benchmarks met consistently
- [ ] **Memory Efficiency**: <5MB memory footprint
- [ ] **API Stability**: Documented, stable interfaces for extension
- [ ] **Error Handling**: Comprehensive error handling and validation

### **Integration Readiness**
- [ ] **Agent 2 APIs**: Selection enhancement interfaces ready
- [ ] **Agent 3 Signals**: UI integration signals functional
- [ ] **Agent 4 Hooks**: Integration coordination hooks implemented
- [ ] **Documentation**: Complete API documentation with examples

---

## 🚀 **Deployment Instructions**

### **Agent 1 Deployment Command**
```bash
# Create and switch to Agent 1 branch
git checkout -b feature/validation-core-agent1-issue26-1

# Deploy Agent 1 with this prompt:
"I need you to work on Sub-Issue #26.1 - Core Validation Framework. Implement the foundational drawing state management, basic area selection, and shape infrastructure that Agent 2 and Agent 3 will build upon."
```

### **Pre-Deployment Checklist**
- [ ] Clean working directory
- [ ] GitHub Issue #26.1 created
- [ ] Branch strategy confirmed
- [ ] Dependencies verified (PyQt6 6.6+)

### **Post-Completion Handoff**
- [ ] All core APIs implemented and tested
- [ ] Agent 2 extension points documented
- [ ] Agent 3 signal interfaces ready
- [ ] Agent 4 integration hooks functional
- [ ] Performance benchmarks established

---

**Agent 1 Foundation Ready for Implementation** 🚀

This specification provides Agent 1 with comprehensive requirements for building the core validation framework that serves as the foundation for the entire Issue #26 implementation.