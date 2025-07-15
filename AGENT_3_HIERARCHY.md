# Agent 3 - Hierarchy Management Reading Order Visualization

## 🎯 Your Assignment
You are **Agent 3** for Issue #243 - Reading Order Visualization. Your mission is to implement visual reading order management with graphics-based visualization, animated flow indicators, and comprehensive reordering capabilities.

## 📋 Specific Tasks

### 1. Graphics-Based Visualization
- Create `ReadingOrderVisualization` using QGraphicsView
- Implement `ReadingOrderItem` for element representation
- Build `ReadingOrderFlow` for animated flow arrows
- Add zoom, pan, and navigation controls
- Create visual hierarchy depth indicators

### 2. Reordering Interface
- Build `ReadingOrderPanel` with list-based reordering
- Implement drag-drop reordering within visualization
- Add move up/down controls with validation
- Create auto-sort functionality based on position
- Support bulk reordering operations

### 3. Order Validation System
- Implement spatial order validation algorithms
- Create issue detection for out-of-order elements
- Add reading flow analysis and suggestions
- Build validation feedback with highlighting
- Create correction suggestion system

### 4. Animation and Visual Effects
- Implement smooth element highlighting
- Create animated flow arrows between elements
- Add transition effects for reordering
- Build visual feedback for validation issues
- Create progressive disclosure for complex hierarchies

## 📁 Files to Create

### Primary Implementation
```
src/torematrix/ui/tools/validation/reading_order.py
├── ReadingOrderItem (200+ lines)
│   ├── __init__(element, order_index, parent)
│   ├── boundingRect()
│   ├── paint(painter, option, widget)
│   ├── mousePressEvent(event)
│   ├── hoverEnterEvent(event)
│   ├── hoverLeaveEvent(event)
│   ├── animate_highlight()
│   └── _animation_finished()
├── ReadingOrderFlow (150+ lines)
│   ├── __init__(start_item, end_item, parent)
│   ├── boundingRect()
│   ├── paint(painter, option, widget)
│   ├── _create_arrow_head(start, end)
│   └── highlight(highlight)
├── ReadingOrderVisualization (400+ lines)
│   ├── __init__(parent)
│   ├── load_hierarchy(hierarchy)
│   ├── _get_reading_order(hierarchy)
│   ├── _position_items()
│   ├── _create_flow_arrows()
│   ├── highlight_element(element_id)
│   ├── highlight_flow(from_element_id, to_element_id)
│   ├── clear_highlights()
│   └── wheelEvent(event)
├── ReadingOrderPanel (300+ lines)
│   ├── __init__(parent)
│   ├── set_hierarchy_manager(manager)
│   ├── load_reading_order(order, hierarchy)
│   ├── _on_order_changed()
│   ├── _move_up()
│   ├── _move_down()
│   ├── _auto_sort()
│   ├── _validate_order()
│   └── _find_reading_order_issues()
├── ReadingOrderWidget (200+ lines)
│   ├── __init__(state_store, event_bus, parent)
│   ├── _setup_ui()
│   ├── _setup_connections()
│   ├── _load_reading_order()
│   ├── _on_element_selected(element_id)
│   ├── _on_reorder_requested(new_order)
│   ├── _on_validation_requested()
│   ├── refresh()
│   ├── highlight_element(element_id)
│   ├── highlight_flow(from_element_id, to_element_id)
│   └── clear_highlights()
└── Supporting utility functions
```

### Testing Implementation
```
tests/unit/ui/tools/validation/test_reading_order.py
├── TestReadingOrderItem (graphics item tests)
├── TestReadingOrderFlow (flow arrow tests)
├── TestReadingOrderVisualization (visualization tests)
├── TestReadingOrderPanel (panel tests)
├── TestReadingOrderWidget (main widget tests)
└── Integration tests with Agents 1 & 2
```

## 🔧 Technical Implementation Details

### ReadingOrderVisualization Class Structure
```python
class ReadingOrderVisualization(QGraphicsView):
    element_selected = pyqtSignal(str)  # element_id
    order_changed = pyqtSignal(list)   # new_order
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.elements = []
        self.order_items = []
        self.flow_arrows = []
        self.current_hierarchy = None
        
    def load_hierarchy(self, hierarchy: ElementHierarchy):
        # Clear existing items
        # Get reading order from hierarchy
        # Create visual items for each element
        # Position items in scene
        # Create flow arrows
        # Fit view to content
```

### ReadingOrderItem Graphics Implementation
```python
class ReadingOrderItem(QGraphicsItem):
    def __init__(self, element: Element, order_index: int, parent=None):
        super().__init__(parent)
        self.element = element
        self.order_index = order_index
        self.is_selected = False
        self.is_highlighted = False
        self.animation = None
        
    def paint(self, painter: QPainter, option, widget=None):
        # Draw base rectangle with element type styling
        # Draw order number with background
        # Draw element text preview
        # Draw selection/highlight overlays
        # Apply visual effects
```

### Reading Order Validation
```python
def _find_reading_order_issues(self) -> List[str]:
    # Check for elements out of spatial order
    # Validate page-by-page ordering
    # Check for vertical/horizontal inconsistencies
    # Identify potential grouping issues
    # Return list of human-readable issues
```

## 🎨 Visual Design Specifications

### Element Representation
- **Color Coding**: Consistent with Agent 2 tree widget
- **Order Numbers**: Prominent numbering with background
- **Element Preview**: Truncated text with type indicators
- **Size Scaling**: Responsive to content length
- **Visual Hierarchy**: Depth indicators and grouping

### Flow Arrows
- **Animated Arrows**: Smooth directional flow indicators
- **Highlight States**: Different colors for normal/highlighted
- **Curved Paths**: Smooth curves avoiding overlaps
- **Interactive**: Clickable for flow highlighting
- **Adaptive**: Adjust to element positioning

### Layout Algorithm
- **Grid-Based**: Organized grid layout with proper spacing
- **Reading Flow**: Left-to-right, top-to-bottom arrangement
- **Zoom Support**: Smooth zooming with level-of-detail
- **Pan Support**: Smooth panning with bounds checking
- **Auto-Fit**: Automatic fitting to content bounds

## 🧪 Testing Requirements

### Graphics Component Tests
- **ReadingOrderItem Tests**: Rendering, interaction, animation
- **ReadingOrderFlow Tests**: Arrow drawing, highlighting
- **Visualization Tests**: Loading, positioning, zoom/pan
- **Panel Tests**: List operations, validation feedback
- **Integration Tests**: With Agents 1 & 2 components

### Test Structure
```python
class TestReadingOrderVisualization:
    def setup_method(self):
        # Create test hierarchy
        # Mock hierarchy manager
        # Setup visualization widget
        
    def test_load_hierarchy(self):
        # Test hierarchy loading and positioning
        
    def test_element_highlighting(self):
        # Test element highlighting system
        
    def test_flow_visualization(self):
        # Test flow arrow display
        
    def test_reordering_operations(self):
        # Test drag-drop reordering
```

## 🔗 Integration Points

### Agent 1 Dependencies
- Use `HierarchyManager.get_reading_order()` for order calculation
- Use validation functions for order checking
- Subscribe to hierarchy change events
- Use metrics for order analysis

### Agent 2 Dependencies
- Coordinate with tree widget for element selection
- Share selection state between components
- Use consistent styling and theming
- Integrate with validation feedback system

### State Management Integration
- Subscribe to state changes for order updates
- Update visualization when hierarchy changes
- Maintain order state across operations

### Event Bus Integration
- Listen for `EventType.HIERARCHY_CHANGED` events
- Emit reading order specific events
- Handle validation events from Agent 1

## 🚀 GitHub Workflow

### Branch Management
```bash
# Create your unique branch from main
git checkout main
git pull origin main
git checkout -b feature/reading-order-agent3-issue243
```

### Development Process
1. Implement ReadingOrderItem with graphics rendering
2. Create ReadingOrderFlow with animated arrows
3. Build ReadingOrderVisualization with scene management
4. Implement ReadingOrderPanel with reordering controls
5. Add validation and issue detection
6. Create comprehensive animation system
7. Write comprehensive tests (>95% coverage)

### Completion Workflow
1. Ensure all graphics components render correctly
2. Test reordering operations thoroughly
3. Verify validation and issue detection
4. Test performance with large documents
5. Run all tests and ensure they pass
6. Create detailed PR with screenshots/demos
7. Update issue #243 with all checkboxes ticked

## ✅ Success Criteria

### Implementation Checklist
- [ ] ReadingOrderVisualization with graphics scene
- [ ] ReadingOrderItem with proper rendering and interaction
- [ ] ReadingOrderFlow with animated arrows
- [ ] ReadingOrderPanel with reordering controls
- [ ] Spatial order validation and issue detection
- [ ] Smooth animations and visual effects
- [ ] Zoom and pan functionality
- [ ] Integration with Agents 1 & 2

### Testing Checklist
- [ ] >95% code coverage achieved
- [ ] All graphics components tested
- [ ] Animation system verified
- [ ] Reordering functionality tested
- [ ] Validation algorithms tested
- [ ] Performance tested with large documents
- [ ] Integration with other agents verified

### Quality Checklist
- [ ] Smooth and responsive graphics performance
- [ ] Professional visual design
- [ ] Intuitive user interactions
- [ ] Accessibility features where applicable
- [ ] Consistent styling with other components
- [ ] Error handling for all operations

## 📊 Performance Targets
- Smooth graphics rendering at 60fps
- Support for 500+ elements in visualization
- Zoom/pan operations responsive and smooth
- Animation effects at 60fps
- Memory efficient graphics item management
- Quick validation feedback (<100ms)

## 🗣️ Communication Protocol
- Update issue #243 with progress regularly
- Share screenshots and demos of visual components
- Coordinate with Agents 1 & 2 on integration
- Report any performance or rendering issues

This reading order visualization system will provide intuitive visual management of document reading flow, enabling users to identify and correct order issues through interactive graphics and comprehensive validation feedback.