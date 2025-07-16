# Agent 2: Advanced Area Selection & Snapping Systems

## 🎯 **Mission Statement**
**Agent 2 Focus**: Enhance Agent 1's core foundation with advanced area selection tools, intelligent snapping algorithms, and performance-optimized selection capabilities for the TORE Matrix Labs manual validation system.

## 📋 **Sub-Issue Assignment**
- **GitHub Issue**: #26.2 - Advanced Area Selection Tools
- **Branch**: `feature/validation-selection-agent2-issue26-2`
- **Dependency**: Complete Agent 1 core framework implementation
- **Duration**: 4 days
- **Integration**: Build on Agent 1 APIs, prepare for Agent 3 UI components

---

## 🏗️ **Technical Architecture**

### **Core Components to Implement**

#### **1. Advanced Snapping System (`snapping.py`)**
```python
class SnapEngine:
    """Advanced snapping engine with magnetic field detection."""
    
    def __init__(self, configuration: SnapConfiguration):
        self.config = configuration
        self.snap_targets: List[SnapTarget] = []
        self.magnetic_fields: List[MagneticField] = []
        self.edge_detector = EdgeDetector()
    
    def update_snap_targets(self, elements: List[Element]) -> None:
        """Update available snap targets from document elements."""
        
    def find_snap_candidates(self, point: QPoint, tolerance: float) -> List[SnapResult]:
        """Find potential snap candidates for given point."""
        
    def apply_snap(self, point: QPoint, snap_type: SnapType) -> SnapResult:
        """Apply snapping to point and return result."""

class MagneticField:
    """Magnetic field for element edge attraction."""
    
    def __init__(self, element: Element, strength: float, radius: float):
        self.element = element
        self.strength = strength
        self.radius = radius
        self.active_edges = self._calculate_edges()
    
    def calculate_attraction(self, point: QPoint) -> Tuple[QPoint, float]:
        """Calculate magnetic attraction force for point."""

class EdgeDetector:
    """Intelligent edge detection for document elements."""
    
    def detect_element_edges(self, element: Element) -> List[Edge]:
        """Detect edges for element boundaries."""
        
    def find_alignment_guides(self, elements: List[Element]) -> List[AlignmentGuide]:
        """Find alignment guides between elements."""
```

#### **2. Enhanced Shape Tools (`enhanced_shapes.py`)**
```python
class FreehandShape(SelectionShape):
    """Advanced freehand selection with smoothing algorithms."""
    
    def __init__(self, smoothing_factor: float = 0.7):
        super().__init__()
        self.smoothing_factor = smoothing_factor
        self.raw_points: List[QPoint] = []
        self.smoothed_points: List[QPoint] = []
    
    def add_point(self, point: QPoint) -> None:
        """Add point with real-time smoothing."""
        
    def apply_smoothing_algorithm(self) -> None:
        """Apply Catmull-Rom spline smoothing."""

class AdvancedPolygonTool(PolygonSelectionTool):
    """Enhanced polygon tool with magnetic vertex snapping."""
    
    def __init__(self, snap_engine: SnapEngine):
        super().__init__()
        self.snap_engine = snap_engine
        self.magnetic_vertices = True
        self.auto_complete_threshold = 10.0
    
    def handle_vertex_placement(self, point: QPoint) -> QPoint:
        """Handle vertex placement with magnetic snapping."""
        
    def detect_shape_completion(self) -> bool:
        """Detect when polygon should auto-complete."""

class ShapeManipulator:
    """Advanced shape manipulation and editing tools."""
    
    def resize_shape(self, shape: SelectionShape, handle: ResizeHandle, delta: QPoint) -> None:
        """Resize shape maintaining proportions and snapping."""
        
    def rotate_shape(self, shape: SelectionShape, center: QPoint, angle: float) -> None:
        """Rotate shape around center point."""
        
    def move_shape(self, shape: SelectionShape, delta: QPoint) -> None:
        """Move shape with collision detection."""
```

#### **3. Selection Algorithms (`selection_algorithms.py`)**
```python
class SmartBoundaryDetector:
    """Intelligent boundary detection for content-aware selection."""
    
    def __init__(self, sensitivity: float = 0.8):
        self.sensitivity = sensitivity
        self.content_analyzer = ContentAnalyzer()
    
    def detect_element_boundaries(self, image: QPixmap, rough_area: QRect) -> QRect:
        """Detect precise element boundaries from rough selection."""
        
    def suggest_selection_improvements(self, selection: SelectionShape) -> List[SelectionSuggestion]:
        """Suggest improvements to current selection."""

class MultiAreaSelectionManager:
    """Manage multiple simultaneous area selections."""
    
    def __init__(self):
        self.active_selections: Dict[str, SelectionShape] = {}
        self.selection_groups: Dict[str, List[str]] = {}
    
    def add_selection(self, selection_id: str, shape: SelectionShape) -> None:
        """Add new selection to active set."""
        
    def merge_selections(self, selection_ids: List[str]) -> SelectionShape:
        """Merge multiple selections into single shape."""
        
    def group_selections(self, group_id: str, selection_ids: List[str]) -> None:
        """Group selections for batch operations."""

class SpatialIndex:
    """Spatial indexing for efficient collision detection in large documents."""
    
    def __init__(self, page_bounds: QRect, grid_size: int = 50):
        self.page_bounds = page_bounds
        self.grid_size = grid_size
        self.grid: Dict[Tuple[int, int], List[Element]] = {}
    
    def insert_element(self, element: Element) -> None:
        """Insert element into spatial index."""
        
    def query_region(self, region: QRect) -> List[Element]:
        """Query elements within region efficiently."""
```

#### **4. Performance Optimization (`performance.py`)**
```python
class SelectionPerformanceOptimizer:
    """Performance optimization for real-time selection feedback."""
    
    def __init__(self):
        self.frame_budget_ms = 16  # 60 FPS target
        self.optimization_cache = {}
        self.dirty_regions: Set[QRect] = set()
    
    def optimize_rendering(self, selections: List[SelectionShape]) -> RenderPlan:
        """Create optimized rendering plan for selections."""
        
    def cache_expensive_operations(self, operation: str, params: dict) -> Any:
        """Cache expensive operations for reuse."""
        
    def batch_collision_detection(self, shapes: List[SelectionShape]) -> CollisionResults:
        """Batch process collision detection efficiently."""

class MemoryManager:
    """Memory management for large document processing."""
    
    def __init__(self, max_cache_size_mb: int = 100):
        self.max_cache_size = max_cache_size_mb * 1024 * 1024
        self.current_cache_size = 0
        self.cache_items: Dict[str, CacheItem] = {}
    
    def cache_page_data(self, page_id: str, data: Any) -> None:
        """Cache page data with automatic eviction."""
        
    def evict_least_recently_used(self) -> None:
        """Evict LRU items when memory limit reached."""
```

---

## 🔗 **Integration with Agent 1**

### **Required Agent 1 Dependencies**
```python
# Import Agent 1 core components
from .drawing_state import DrawingStateManager, DrawingMode, DrawingArea
from .area_select import ValidationAreaSelector, AreaSelectionMode
from .shapes import SelectionShape, RectangleShape, PolygonShape

# Extend Agent 1 functionality
class EnhancedValidationAreaSelector(ValidationAreaSelector):
    """Enhanced selector with Agent 2 capabilities."""
    
    def __init__(self, state_manager: DrawingStateManager):
        super().__init__(state_manager)
        self.snap_engine = SnapEngine(SnapConfiguration())
        self.boundary_detector = SmartBoundaryDetector()
        self.multi_area_manager = MultiAreaSelectionManager()
    
    def enable_advanced_features(self) -> None:
        """Enable Agent 2 advanced features."""
        self.snap_engine.initialize()
        self.boundary_detector.calibrate()
```

### **Agent 1 API Extensions**
```python
# Extend DrawingStateManager for Agent 2 features
class AdvancedDrawingStateManager(DrawingStateManager):
    """Extended state manager with Agent 2 capabilities."""
    
    # Agent 2 signals
    snap_target_found = pyqtSignal(SnapResult)
    magnetic_field_activated = pyqtSignal(MagneticField)
    multi_selection_updated = pyqtSignal(dict)
    boundary_suggestion_available = pyqtSignal(SelectionSuggestion)
    
    def enable_snapping(self, snap_types: List[SnapType]) -> None:
        """Enable snapping with specified types."""
        
    def set_magnetic_sensitivity(self, sensitivity: float) -> None:
        """Configure magnetic field sensitivity."""
```

---

## 📊 **Implementation Timeline**

### **Day 1: Advanced Snapping Foundation**
- [ ] Implement SnapEngine core architecture
- [ ] Create MagneticField calculation system  
- [ ] Develop EdgeDetector for element boundaries
- [ ] Basic snap target detection
- [ ] Integration with Agent 1 selection framework

### **Day 2: Enhanced Shape Tools**
- [ ] Implement FreehandShape with smoothing
- [ ] Create AdvancedPolygonTool with magnetic vertices
- [ ] Develop ShapeManipulator for editing operations
- [ ] Add real-time visual feedback
- [ ] Integration testing with Agent 1 shapes

### **Day 3: Selection Algorithms & Multi-Area**
- [ ] Implement SmartBoundaryDetector
- [ ] Create MultiAreaSelectionManager
- [ ] Develop SpatialIndex for performance
- [ ] Add selection suggestion system
- [ ] Comprehensive algorithm testing

### **Day 4: Performance Optimization & Integration**
- [ ] Implement SelectionPerformanceOptimizer
- [ ] Create MemoryManager for large documents
- [ ] Optimize rendering pipeline
- [ ] Performance benchmarking
- [ ] Final integration with Agent 1
- [ ] Preparation for Agent 3 UI integration

---

## 🧪 **Testing Requirements**

### **Unit Tests (Target: >95% Coverage)**
```python
class TestSnapEngine:
    """Test snapping engine functionality."""
    
    def test_snap_target_detection(self):
        """Test snap target finding accuracy."""
        
    def test_magnetic_field_calculation(self):
        """Test magnetic field attraction forces."""
        
    def test_edge_detection_accuracy(self):
        """Test edge detection on various element types."""

class TestEnhancedShapes:
    """Test enhanced shape tools."""
    
    def test_freehand_smoothing(self):
        """Test freehand smoothing algorithms."""
        
    def test_polygon_magnetic_snapping(self):
        """Test polygon vertex magnetic snapping."""
        
    def test_shape_manipulation_operations(self):
        """Test resize, rotate, move operations."""

class TestSelectionAlgorithms:
    """Test selection algorithms performance."""
    
    def test_boundary_detection_accuracy(self):
        """Test boundary detection accuracy."""
        
    def test_multi_area_management(self):
        """Test multi-area selection coordination."""
        
    def test_spatial_index_performance(self):
        """Test spatial indexing performance."""
```

### **Performance Benchmarks**
- **Snap Detection**: <5ms for 1000+ targets
- **Boundary Detection**: <50ms for complex elements  
- **Multi-Area Operations**: <100ms for 50+ selections
- **Memory Usage**: <10MB for 10,000+ elements
- **Rendering Performance**: 60 FPS with 100+ active selections

### **Integration Tests**
```python
class TestAgent1Integration:
    """Test integration with Agent 1 components."""
    
    def test_state_manager_extension(self):
        """Test enhanced state manager functionality."""
        
    def test_selection_tool_enhancement(self):
        """Test enhanced selection tool operations."""
        
    def test_signal_compatibility(self):
        """Test PyQt6 signal compatibility."""
```

---

## 🎯 **Success Criteria**

### **Technical Achievements**
- [ ] **Snapping System**: Sub-5ms snap detection with 99% accuracy
- [ ] **Enhanced Shapes**: Smooth freehand and magnetic polygon tools
- [ ] **Multi-Area Support**: Efficient management of 50+ simultaneous selections
- [ ] **Performance**: 60 FPS operation on 10,000+ element documents
- [ ] **Integration**: Seamless extension of Agent 1 foundation

### **Quality Metrics**
- [ ] **Test Coverage**: >95% unit test coverage
- [ ] **Performance**: All operations under target benchmarks
- [ ] **Memory**: <10MB overhead for advanced features
- [ ] **Compatibility**: Full PyQt6 6.6+ support
- [ ] **Documentation**: Complete API documentation

### **User Experience**
- [ ] **Responsive Feedback**: <16ms selection response time
- [ ] **Intelligent Assistance**: Smart boundary detection and suggestions
- [ ] **Professional Feel**: Smooth animations and visual feedback
- [ ] **Error Handling**: Graceful degradation for edge cases

---

## 🔌 **API Interface for Agent 3**

### **UI Component Integration Points**
```python
# Agent 3 will integrate these enhanced capabilities
class AdvancedSelectionAPI:
    """API interface for Agent 3 UI components."""
    
    def get_snap_engine(self) -> SnapEngine:
        """Get snap engine for UI integration."""
        
    def get_selection_suggestions(self) -> List[SelectionSuggestion]:
        """Get current selection suggestions for UI display."""
        
    def configure_magnetic_sensitivity(self, sensitivity: float) -> None:
        """Configure magnetic sensitivity from UI controls."""
        
    def enable_multi_area_mode(self, enabled: bool) -> None:
        """Enable/disable multi-area selection from UI."""

# Signals for Agent 3 UI components
snap_feedback_needed = pyqtSignal(QPoint, SnapResult)
selection_suggestion_available = pyqtSignal(SelectionSuggestion) 
multi_selection_status_changed = pyqtSignal(dict)
performance_warning = pyqtSignal(str, float)
```

---

## 📈 **Performance Monitoring**

### **Real-time Metrics**
```python
class Agent2PerformanceMonitor:
    """Monitor Agent 2 performance metrics."""
    
    def track_snap_performance(self):
        """Track snapping operation performance."""
        
    def monitor_memory_usage(self):
        """Monitor memory usage for optimization."""
        
    def measure_selection_responsiveness(self):
        """Measure selection response times."""
```

---

## 🚀 **Deployment Instructions**

### **Agent 2 Deployment Command**
```bash
# After Agent 1 completion, deploy Agent 2 with:
"I need you to work on Sub-Issue #26.2 - Advanced Area Selection Tools. Build enhanced snapping systems, advanced shape tools, and performance optimization on top of Agent 1's core validation framework. Focus on magnetic edge detection, freehand smoothing, multi-area selection, and real-time performance optimization."
```

### **Branch Management**
```bash
git checkout -b feature/validation-selection-agent2-issue26-2
git checkout feature/validation-core-agent1-issue26-1  # Merge Agent 1 work
git merge feature/validation-selection-agent2-issue26-2
```

### **Integration Checklist**
- [ ] Agent 1 foundation completely implemented
- [ ] All Agent 1 tests passing
- [ ] Agent 1 APIs stable and documented
- [ ] Performance benchmarks established
- [ ] Agent 2 branch created and ready

---

**Agent 2 Ready for Deployment** 🎯

This specification provides Agent 2 with comprehensive requirements for building advanced area selection capabilities that enhance Agent 1's foundation while preparing integration points for Agent 3's UI components.