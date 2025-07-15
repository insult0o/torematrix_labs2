# AGENT 3 VALIDATION: UI Components & User Experience

## 🎯 Your Assignment
You are **Agent 3** responsible for creating comprehensive UI components for manual validation including wizard, toolbar, and OCR dialog.

## 🚨 CRITICAL: Agent Self-Awareness
- **Your Identity**: Agent 3 (Performance/Optimization)
- **Your Branch**: `feature/validation-agent3-issue27`
- **Your Sub-Issue**: #242 - UI Components & User Experience
- **Dependencies**: Agent 1 (DrawingStateManager), Agent 2 (OCR Service)

## 📋 Core Implementation Tasks

### 1. Validation Wizard (`src/torematrix/ui/tools/validation/wizard.py`)
```python
class ValidationWizard(QDialog):
    """Comprehensive wizard for element creation through manual validation."""
    
    # Required signals
    element_created = pyqtSignal(object)  # Element
    wizard_cancelled = pyqtSignal()
    step_changed = pyqtSignal(object)  # WizardStep
    text_changed = pyqtSignal(str)
    type_selected = pyqtSignal(object)  # ElementType
    
    def __init__(self, drawing_area: DrawingArea, 
                 ocr_response: Optional[ValidationOCRResponse] = None,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        # Initialize 6-step wizard workflow
        # - Area Preview
        # - OCR Review
        # - Text Editing
        # - Type Selection
        # - Validation
        # - Completion
```

### 2. Validation Toolbar (`src/torematrix/ui/tools/validation/toolbar.py`)
```python
class ValidationToolbar(QToolBar):
    """Comprehensive toolbar for manual validation operations."""
    
    # Required signals
    drawing_mode_changed = pyqtSignal(bool)  # enabled/disabled
    area_selection_started = pyqtSignal()
    ocr_requested = pyqtSignal()
    element_creation_requested = pyqtSignal()
    validation_requested = pyqtSignal()
    settings_changed = pyqtSignal(str, object)  # setting_name, value
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("Validation Tools", parent)
        # Create tool groups:
        # - Drawing tools
        # - OCR tools  
        # - Element tools
        # - Validation tools
        # - Settings tools
```

### 3. OCR Dialog (`src/torematrix/ui/tools/validation/ocr_dialog.py`)
```python
class OCRDialog(QDialog):
    """Comprehensive OCR dialog for text extraction and editing."""
    
    # Required signals
    text_accepted = pyqtSignal(str)
    text_rejected = pyqtSignal()
    ocr_completed = pyqtSignal(object)  # OCRResult
    
    def __init__(self, drawing_area: DrawingArea, 
                 ocr_service: Optional[ValidationOCRService] = None,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        # Multi-tab interface:
        # - OCR Results with confidence highlighting
        # - Word-by-word analysis
        # - Engine comparison
```

### 4. OCR Confidence Highlighter (`src/torematrix/ui/tools/validation/ocr_dialog.py`)
```python
class OCRConfidenceHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for OCR confidence visualization."""
    
    def __init__(self, parent: QTextDocument, word_confidences: List[float]):
        super().__init__(parent)
        self.word_confidences = word_confidences
        self.confidence_colors = {
            0.9: QColor(76, 175, 80),    # Green - high confidence
            0.7: QColor(255, 193, 7),    # Yellow - medium confidence
            0.5: QColor(255, 152, 0),    # Orange - low confidence
            0.0: QColor(244, 67, 54)     # Red - very low confidence
        }
    
    def highlightBlock(self, text: str):
        """Highlight text based on word confidence."""
        # Implement confidence-based highlighting
```

## 🎨 UI Design Requirements

### 1. Wizard Design (6 Steps)
```python
class WizardStep(Enum):
    AREA_PREVIEW = "area_preview"
    OCR_REVIEW = "ocr_review"
    TEXT_EDITING = "text_editing"
    TYPE_SELECTION = "type_selection"
    VALIDATION = "validation"
    COMPLETION = "completion"

# Each step should have:
# - Clear navigation
# - Progress indicators
# - Validation feedback
# - Professional styling
```

### 2. Toolbar Design (5 Tool Groups)
```python
class ToolbarMode(Enum):
    COLLAPSED = "collapsed"
    DRAWING = "drawing"
    OCR = "ocr"
    VALIDATION = "validation"

# Tool groups:
# - Drawing: Mode toggle, area selection, settings
# - OCR: Engine selection, language, auto-OCR toggle
# - Element: Quick type buttons, wizard launcher
# - Validation: Mode selection, batch toggle, validate button
# - Settings: Color picker, thickness slider, options
```

### 3. OCR Dialog Design (3 Tabs)
```python
# Tab 1: OCR Results
# - Original text with confidence highlighting
# - Editable text area
# - Statistics and formatting options

# Tab 2: Word Analysis
# - Word-by-word confidence display
# - Individual word editing
# - Confidence color coding

# Tab 3: Engine Comparison
# - Multiple engine results
# - Performance comparison
# - Best result selection
```

## 🧪 Testing Requirements

### Test Files Required (>95% Coverage)
- `tests/unit/ui/tools/validation/test_wizard.py`
- `tests/unit/ui/tools/validation/test_toolbar.py`
- `tests/unit/ui/tools/validation/test_ocr_dialog.py`

### Test Categories
1. **Widget Creation Tests**
   - Proper initialization
   - UI component setup
   - Signal connections

2. **Wizard Workflow Tests**
   - Step transitions
   - Data persistence
   - Validation logic

3. **Toolbar Functionality Tests**
   - Tool activation/deactivation
   - Settings management
   - Mode switching

4. **OCR Dialog Tests**
   - Text editing
   - Confidence highlighting
   - Engine comparison

5. **Integration Tests**
   - Drawing manager integration
   - OCR service integration
   - Signal propagation

### Example Test Structure
```python
class TestValidationWizard:
    @pytest.fixture
    def wizard(self):
        area = DrawingArea(rectangle=Rectangle(10, 20, 100, 80))
        return ValidationWizard(area)
    
    def test_wizard_creation(self, wizard):
        assert wizard.current_step == WizardStep.AREA_PREVIEW
        assert wizard.element_data is not None
    
    def test_step_navigation(self, wizard):
        # Test forward navigation
        wizard._go_next()
        assert wizard.current_step == WizardStep.OCR_REVIEW
        
        # Test backward navigation
        wizard._go_back()
        assert wizard.current_step == WizardStep.AREA_PREVIEW
```

## 🔗 Integration Points

### With Agent 1 (Drawing Manager)
```python
# Connect to drawing manager signals
def connect_drawing_manager(self, manager: DrawingStateManager):
    """Connect UI components to drawing manager."""
    manager.mode_changed.connect(self._on_drawing_mode_changed)
    manager.state_changed.connect(self._on_drawing_state_changed)
    manager.area_selected.connect(self._on_area_selected)
    manager.element_created.connect(self._on_element_created)
```

### With Agent 2 (OCR Service)
```python
# Connect to OCR service
def connect_ocr_service(self, service: ValidationOCRService):
    """Connect UI components to OCR service."""
    service.ocr_completed.connect(self._on_ocr_completed)
    service.ocr_failed.connect(self._on_ocr_failed)
    service.engine_ready.connect(self._on_ocr_ready)
```

## 🎨 Styling Requirements

### Professional Theme
```python
def _apply_styling(self):
    """Apply professional styling to components."""
    self.setStyleSheet("""
        QDialog {
            background-color: #f8f9fa;
        }
        
        QGroupBox {
            font-weight: bold;
            border: 2px solid #e9ecef;
            border-radius: 5px;
            margin-top: 10px;
            padding-top: 10px;
            background-color: white;
        }
        
        QPushButton {
            background-color: #007bff;
            color: white;
            border: none;
            border-radius: 5px;
            padding: 8px 16px;
            font-weight: bold;
        }
        
        QPushButton:hover {
            background-color: #0056b3;
        }
        
        QPushButton:disabled {
            background-color: #6c757d;
        }
        
        QTextEdit, QLineEdit {
            border: 2px solid #e9ecef;
            border-radius: 5px;
            padding: 8px;
            background-color: white;
        }
        
        QTextEdit:focus, QLineEdit:focus {
            border-color: #007bff;
        }
    """)
```

### Accessibility Features
```python
def _setup_accessibility(self):
    """Setup accessibility features."""
    # Keyboard shortcuts
    # Screen reader support
    # High contrast mode
    # Focus indicators
    # Tooltips and help text
```

## 📊 Success Criteria

### Functionality Requirements
- [ ] Wizard guides users through complete validation workflow
- [ ] Toolbar provides all necessary drawing and OCR controls
- [ ] OCR dialog offers advanced text extraction and editing
- [ ] Confidence highlighting helps users understand OCR quality
- [ ] All UI components are responsive and professionally styled
- [ ] Keyboard shortcuts improve productivity
- [ ] Error handling provides clear user feedback

### Technical Requirements
- [ ] PyQt6 advanced UI components
- [ ] Multi-step wizard workflow
- [ ] Real-time OCR visualization
- [ ] Responsive design patterns
- [ ] Professional styling and animations
- [ ] Comprehensive accessibility features
- [ ] >95% test coverage

## 🚀 Implementation Steps

1. **Setup Branch**: `git checkout -b feature/validation-agent3-issue27`
2. **Create Wizard Framework**: 6-step workflow with navigation
3. **Implement Wizard Steps**: All steps with proper validation
4. **Create Toolbar**: 5 tool groups with collapsible design
5. **Implement OCR Dialog**: 3-tab interface with highlighting
6. **Add Confidence Highlighter**: Real-time confidence visualization
7. **Create Professional Styling**: Consistent theme across components
8. **Add Accessibility Features**: Keyboard shortcuts and screen reader support
9. **Implement Integration**: Connect with Agent 1 and 2 components
10. **Add Error Handling**: User-friendly error messages and recovery
11. **Create Comprehensive Tests**: >95% coverage with UI testing
12. **Polish and Optimize**: Performance tuning and final polish

## 📋 GitHub Workflow

### Branch Management
```bash
git checkout main
git pull origin main
git checkout -b feature/validation-agent3-issue27
```

### Commit and PR Process
Follow the standard "end work" routine:
1. Run all tests: `python -m pytest tests/unit/ui/tools/validation/test_wizard.py tests/unit/ui/tools/validation/test_toolbar.py tests/unit/ui/tools/validation/test_ocr_dialog.py -v`
2. Commit changes with standardized message
3. Push branch: `git push -u origin feature/validation-agent3-issue27`
4. Create PR referencing Issue #242
5. Update main issue #27 with progress
6. Tick all checkboxes in Issue #242
7. Close Issue #242 with completion summary

## 🎯 Final Deliverables

### Code Files
- `src/torematrix/ui/tools/validation/wizard.py` - Complete wizard implementation
- `src/torematrix/ui/tools/validation/toolbar.py` - Complete toolbar implementation
- `src/torematrix/ui/tools/validation/ocr_dialog.py` - Complete OCR dialog implementation
- `tests/unit/ui/tools/validation/test_wizard.py` - Comprehensive wizard tests
- `tests/unit/ui/tools/validation/test_toolbar.py` - Comprehensive toolbar tests
- `tests/unit/ui/tools/validation/test_ocr_dialog.py` - Comprehensive OCR dialog tests

### Documentation
- UI component API documentation
- Integration examples with other agents
- Styling and theming guidelines
- Accessibility features documentation

### GitHub Updates
- PR with detailed implementation description
- Issue #242 fully completed with all checkboxes ticked
- Main issue #27 updated with Agent 3 completion

Remember: You provide the **user experience** - ensure your UI is intuitive, responsive, and professionally polished!