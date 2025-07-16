# AGENT 1 VALIDATION: Core Drawing State Management

## 🎯 Your Assignment
You are **Agent 1** responsible for implementing the foundational drawing state management system for manual validation element creation.

## 🚨 CRITICAL: Agent Self-Awareness
- **Your Identity**: Agent 1 (Core/Foundation)
- **Your Branch**: `feature/validation-agent1-issue27`
- **Your Sub-Issue**: #238 - Core Drawing State Management
- **Dependencies**: None (you are the foundation)

## 📋 Core Implementation Tasks

### 1. Drawing State Manager (`src/torematrix/ui/tools/validation/drawing.py`)
```python
class DrawingStateManager(QObject):
    """Core state management for manual validation drawing workflow."""
    
    # Drawing modes
    class DrawingMode(Enum):
        DISABLED = "disabled"
        SELECTION = "selection"
        DRAWING = "drawing"
        PREVIEW = "preview"
        CONFIRMING = "confirming"
    
    # Drawing states
    class DrawingState(Enum):
        IDLE = "idle"
        SELECTING_AREA = "selecting_area"
        AREA_SELECTED = "area_selected"
        PROCESSING_OCR = "processing_ocr"
        EDITING_TEXT = "editing_text"
        CHOOSING_TYPE = "choosing_type"
        CREATING_ELEMENT = "creating_element"
        COMPLETED = "completed"
        CANCELLED = "cancelled"
    
    # Required signals
    mode_changed = pyqtSignal(DrawingMode)
    state_changed = pyqtSignal(DrawingState)
    area_selected = pyqtSignal(object)  # DrawingArea
    element_created = pyqtSignal(object)  # Element
    session_completed = pyqtSignal(object)  # DrawingSession
    error_occurred = pyqtSignal(str)
```

### 2. Data Structures
```python
@dataclass
class DrawingArea:
    """Represents a drawn area for element creation."""
    rectangle: Rectangle
    preview_image: Optional[QPixmap] = None
    ocr_result: Optional[OCRResult] = None
    suggested_text: str = ""
    manual_text: str = ""
    element_type: Optional[ElementType] = None
    confidence: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    
    @property
    def final_text(self) -> str:
        """Get the final text (manual override or OCR result)."""
        return self.manual_text if self.manual_text else self.suggested_text

@dataclass
class DrawingSession:
    """Complete drawing session with multiple areas."""
    session_id: str
    areas: List[DrawingArea] = field(default_factory=list)
    batch_mode: bool = False
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    @property
    def is_complete(self) -> bool:
        """Check if all areas have been processed."""
        return all(area.element_type is not None for area in self.areas)
```

### 3. Core Methods to Implement
```python
def activate_draw_mode(self, batch_mode: bool = False) -> bool:
    """Activate drawing mode for manual validation."""
    
def deactivate_draw_mode(self) -> bool:
    """Deactivate drawing mode and cleanup."""
    
def start_area_selection(self) -> bool:
    """Start area selection process."""
    
def complete_area_selection(self, rectangle: Rectangle, preview_image: Optional[QPixmap] = None) -> bool:
    """Complete area selection with drawn rectangle."""
    
def cancel_area_selection(self) -> bool:
    """Cancel current area selection."""
    
def set_manual_text(self, text: str) -> bool:
    """Set manual text override for current area."""
    
def set_element_type(self, element_type: ElementType) -> bool:
    """Set element type for current area."""
    
def create_element(self) -> bool:
    """Create element from current area."""
    
async def process_ocr(self) -> bool:
    """Process OCR on current area."""
```

## 🧪 Testing Requirements (`tests/unit/ui/tools/validation/test_drawing.py`)

### Test Categories (>95% Coverage Required)
1. **State Management Tests**
   - Mode transitions
   - State transitions
   - Invalid state handling

2. **Area Selection Tests**
   - Area validation (min/max size)
   - Preview image handling
   - Selection cancellation

3. **Session Management Tests**
   - Session creation/completion
   - Batch mode operations
   - Element tracking

4. **OCR Integration Tests**
   - OCR processing hooks
   - Result handling
   - Error scenarios

5. **Signal Tests**
   - All signal emissions
   - Proper signal parameters
   - Signal sequence validation

### Example Test Structure
```python
class TestDrawingStateManager:
    @pytest.fixture
    def manager(self):
        return DrawingStateManager()
    
    def test_activate_draw_mode(self, manager):
        result = manager.activate_draw_mode()
        assert result is True
        assert manager.mode == DrawingMode.SELECTION
        assert manager.state == DrawingState.IDLE
    
    def test_area_selection_validation(self, manager):
        manager.activate_draw_mode()
        manager.start_area_selection()
        
        # Test area too small
        small_rect = Rectangle(10, 20, 5, 5)
        result = manager.complete_area_selection(small_rect)
        assert result is False
        
        # Test valid area
        valid_rect = Rectangle(10, 20, 100, 80)
        result = manager.complete_area_selection(valid_rect)
        assert result is True
```

## 🔗 Integration Points

### For Agent 2 (OCR Service)
```python
# Provide these hooks for OCR integration
def initialize_ocr(self, config: Optional[Dict[str, Any]] = None) -> None:
    """Initialize OCR engine with configuration."""

def set_callbacks(self, 
                 area_validator: Optional[Callable[[DrawingArea], bool]] = None,
                 element_creator: Optional[Callable[[DrawingArea], Element]] = None,
                 session_handler: Optional[Callable[[DrawingSession], None]] = None) -> None:
    """Set callback functions for validation and creation."""
```

### For Agent 3 (UI Components)
```python
# Provide these properties for UI integration
@property
def mode(self) -> DrawingMode:
    """Get current drawing mode."""

@property
def state(self) -> DrawingState:
    """Get current drawing state."""

@property
def current_area(self) -> Optional[DrawingArea]:
    """Get current drawing area."""

@property
def current_session(self) -> Optional[DrawingSession]:
    """Get current drawing session."""
```

## 📊 Success Criteria

### Functionality Requirements
- [ ] All drawing mode transitions work correctly
- [ ] Area selection validation prevents invalid selections
- [ ] OCR processing integrates seamlessly
- [ ] Element creation flows properly
- [ ] Session management supports batch operations
- [ ] Error handling is comprehensive
- [ ] All signals emit correctly

### Technical Requirements
- [ ] Full type hints throughout
- [ ] Async OCR processing support
- [ ] PyQt6 signal integration
- [ ] Session persistence capability
- [ ] Error recovery mechanisms
- [ ] >95% test coverage

## 🚀 Implementation Steps

1. **Setup Branch**: `git checkout -b feature/validation-agent1-issue27`
2. **Create Core Classes**: DrawingStateManager, DrawingArea, DrawingSession
3. **Implement State Machine**: All modes and states with transitions
4. **Add Area Selection**: With validation and preview support
5. **Create OCR Hooks**: For Agent 2 integration
6. **Add Session Management**: Batch mode and completion tracking
7. **Implement Callbacks**: For element creation and validation
8. **Add Error Handling**: Comprehensive error recovery
9. **Create Comprehensive Tests**: >95% coverage required
10. **Verify Integration Points**: Ensure clean APIs for other agents

## 📋 GitHub Workflow

### Branch Management
```bash
git checkout main
git pull origin main
git checkout -b feature/validation-agent1-issue27
```

### Commit and PR Process
Follow the standard "end work" routine:
1. Run all tests: `python -m pytest tests/unit/ui/tools/validation/test_drawing.py -v`
2. Commit changes with standardized message
3. Push branch: `git push -u origin feature/validation-agent1-issue27`
4. Create PR referencing Issue #238
5. Update main issue #27 with progress
6. Tick all checkboxes in Issue #238
7. Close Issue #238 with completion summary

## 🎯 Final Deliverables

### Code Files
- `src/torematrix/ui/tools/validation/drawing.py` - Complete implementation
- `tests/unit/ui/tools/validation/test_drawing.py` - Comprehensive tests

### Documentation
- API documentation for all public methods
- Integration examples for other agents
- Configuration options and usage

### GitHub Updates
- PR with detailed implementation description
- Issue #238 fully completed with all checkboxes ticked
- Main issue #27 updated with Agent 1 completion

Remember: You are the **foundation** - other agents depend on your clean, well-tested API!