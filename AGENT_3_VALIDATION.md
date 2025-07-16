# Agent 3: UI Components & User Experience

## 🎯 **Mission Statement**
**Agent 3 Focus**: Create professional, intuitive UI components and comprehensive user experience workflows that integrate Agent 1's core framework and Agent 2's advanced selection tools into a cohesive manual validation system.

## 📋 **Sub-Issue Assignment**
- **GitHub Issue**: #26.3 - UI Components & User Experience
- **Branch**: `feature/validation-ui-agent3-issue26-3`
- **Dependencies**: Agent 1 core framework + Agent 2 advanced selection tools
- **Duration**: 4 days
- **Integration**: Build comprehensive UI on Agent 1-2 foundation, prepare for Agent 4 integration

---

## 🏗️ **Technical Architecture**

### **Core UI Components to Implement**

#### **1. Validation Wizard (`wizard.py`)**
```python
class ValidationWizard(QWizard):
    """Multi-step validation wizard with professional workflow."""
    
    # Wizard signals
    area_selected = pyqtSignal(DrawingArea)
    text_extracted = pyqtSignal(str, float)  # text, confidence
    element_created = pyqtSignal(Element)
    wizard_completed = pyqtSignal(dict)
    validation_cancelled = pyqtSignal()
    
    def __init__(self, state_manager: DrawingStateManager, 
                 snap_engine: SnapEngine, parent=None):
        super().__init__(parent)
        self.state_manager = state_manager
        self.snap_engine = snap_engine
        self.current_element = None
        self.wizard_data = {}
        
        self._setup_wizard_pages()
        self._setup_wizard_styling()
        self._connect_signals()
    
    def _setup_wizard_pages(self):
        """Setup 6-step validation workflow."""
        self.addPage(WelcomeStep(self))           # Step 1: Introduction
        self.addPage(AreaSelectionStep(self))     # Step 2: Area Selection  
        self.addPage(OCRProcessingStep(self))     # Step 3: OCR Processing
        self.addPage(TextReviewStep(self))        # Step 4: Text Review
        self.addPage(ElementTypeStep(self))       # Step 5: Element Type
        self.addPage(FinalReviewStep(self))       # Step 6: Final Review

class WelcomeStep(QWizardPage):
    """Welcome and configuration step."""
    
    def __init__(self, wizard: ValidationWizard):
        super().__init__()
        self.wizard = wizard
        self.setTitle("Manual Validation Wizard")
        self.setSubTitle("Configure validation settings and begin element selection")
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup welcome page UI."""
        layout = QVBoxLayout()
        
        # Validation mode selection
        mode_group = QGroupBox("Validation Mode")
        mode_layout = QVBoxLayout()
        
        self.manual_radio = QRadioButton("Manual Selection")
        self.assisted_radio = QRadioButton("OCR-Assisted")
        self.hybrid_radio = QRadioButton("Hybrid Workflow")
        
        mode_layout.addWidget(self.manual_radio)
        mode_layout.addWidget(self.assisted_radio)  
        mode_layout.addWidget(self.hybrid_radio)
        mode_group.setLayout(mode_layout)
        
        # Advanced options
        advanced_group = QGroupBox("Advanced Options")
        advanced_layout = QFormLayout()
        
        self.enable_snapping = QCheckBox("Enable Magnetic Snapping")
        self.enable_suggestions = QCheckBox("Enable Smart Suggestions")
        self.batch_mode = QCheckBox("Batch Processing Mode")
        
        advanced_layout.addRow("Snapping:", self.enable_snapping)
        advanced_layout.addRow("Suggestions:", self.enable_suggestions)
        advanced_layout.addRow("Batch Mode:", self.batch_mode)
        advanced_group.setLayout(advanced_layout)
        
        layout.addWidget(mode_group)
        layout.addWidget(advanced_group)
        self.setLayout(layout)

class AreaSelectionStep(QWizardPage):
    """Interactive area selection with real-time feedback."""
    
    def __init__(self, wizard: ValidationWizard):
        super().__init__()
        self.wizard = wizard
        self.setTitle("Select Validation Area")
        self.setSubTitle("Draw around the element to validate")
        
        self.selected_area = None
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup area selection interface."""
        layout = QVBoxLayout()
        
        # Selection tools toolbar
        tools_layout = QHBoxLayout()
        
        self.rectangle_btn = QPushButton("Rectangle")
        self.polygon_btn = QPushButton("Polygon")
        self.freehand_btn = QPushButton("Freehand")
        self.magic_btn = QPushButton("Magic Select")
        
        tools_layout.addWidget(self.rectangle_btn)
        tools_layout.addWidget(self.polygon_btn)
        tools_layout.addWidget(self.freehand_btn)
        tools_layout.addWidget(self.magic_btn)
        
        # Selection canvas
        self.selection_canvas = SelectionCanvasWidget(
            self.wizard.state_manager,
            self.wizard.snap_engine
        )
        
        # Status and feedback
        self.status_label = QLabel("Select a tool and draw around the element")
        self.feedback_widget = SelectionFeedbackWidget()
        
        layout.addLayout(tools_layout)
        layout.addWidget(self.selection_canvas, 1)
        layout.addWidget(self.status_label)
        layout.addWidget(self.feedback_widget)
        self.setLayout(layout)

class OCRProcessingStep(QWizardPage):
    """OCR processing with progress and options."""
    
    def __init__(self, wizard: ValidationWizard):
        super().__init__()
        self.wizard = wizard
        self.setTitle("OCR Processing")
        self.setSubTitle("Processing selected area with OCR")
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup OCR processing interface."""
        layout = QVBoxLayout()
        
        # OCR options
        options_group = QGroupBox("OCR Configuration")
        options_layout = QFormLayout()
        
        self.language_combo = QComboBox()
        self.language_combo.addItems(["English", "Spanish", "French", "German"])
        
        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(72, 600)
        self.dpi_spin.setValue(300)
        
        self.preprocessing_check = QCheckBox("Enable Image Preprocessing")
        
        options_layout.addRow("Language:", self.language_combo)
        options_layout.addRow("DPI:", self.dpi_spin)
        options_layout.addRow("Preprocessing:", self.preprocessing_check)
        options_group.setLayout(options_layout)
        
        # Progress tracking
        self.progress_bar = QProgressBar()
        self.progress_label = QLabel("Ready to process...")
        
        # OCR preview
        self.preview_widget = OCRPreviewWidget()
        
        layout.addWidget(options_group)
        layout.addWidget(self.progress_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.preview_widget, 1)
        self.setLayout(layout)

class TextReviewStep(QWizardPage):
    """Text review and correction interface."""
    
    def __init__(self, wizard: ValidationWizard):
        super().__init__()
        self.wizard = wizard
        self.setTitle("Review and Edit Text")
        self.setSubTitle("Review OCR results and make corrections")
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup text review interface."""
        layout = QVBoxLayout()
        
        # Original vs corrected text
        text_layout = QHBoxLayout()
        
        # Original text (read-only)
        original_group = QGroupBox("Original OCR Text")
        original_layout = QVBoxLayout()
        self.original_text = QTextEdit()
        self.original_text.setReadOnly(True)
        original_layout.addWidget(self.original_text)
        original_group.setLayout(original_layout)
        
        # Corrected text (editable)
        corrected_group = QGroupBox("Corrected Text")
        corrected_layout = QVBoxLayout()
        self.corrected_text = QTextEdit()
        corrected_layout.addWidget(self.corrected_text)
        corrected_group.setLayout(corrected_layout)
        
        text_layout.addWidget(original_group)
        text_layout.addWidget(corrected_group)
        
        # Confidence visualization
        confidence_group = QGroupBox("Confidence Analysis")
        confidence_layout = QVBoxLayout()
        self.confidence_widget = ConfidenceVisualizationWidget()
        confidence_layout.addWidget(self.confidence_widget)
        confidence_group.setLayout(confidence_layout)
        
        # Quick correction tools
        tools_layout = QHBoxLayout()
        self.spell_check_btn = QPushButton("Spell Check")
        self.reprocess_btn = QPushButton("Reprocess OCR")
        self.suggestions_btn = QPushButton("AI Suggestions")
        
        tools_layout.addWidget(self.spell_check_btn)
        tools_layout.addWidget(self.reprocess_btn)
        tools_layout.addWidget(self.suggestions_btn)
        
        layout.addLayout(text_layout)
        layout.addWidget(confidence_group)
        layout.addLayout(tools_layout)
        self.setLayout(layout)

class ElementTypeStep(QWizardPage):
    """Element type selection and metadata."""
    
    def __init__(self, wizard: ValidationWizard):
        super().__init__()
        self.wizard = wizard
        self.setTitle("Element Classification")
        self.setSubTitle("Classify the element type and add metadata")
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup element type selection interface."""
        layout = QVBoxLayout()
        
        # Element type selection
        type_group = QGroupBox("Element Type")
        type_layout = QGridLayout()
        
        self.type_buttons = {}
        element_types = [
            ("text", "Text Block", "📄"),
            ("paragraph", "Paragraph", "📝"),
            ("title", "Title/Header", "📋"),
            ("list", "List Item", "📌"),
            ("table", "Table", "📊"),
            ("image", "Image", "🖼️"),
            ("formula", "Formula", "🔢"),
            ("code", "Code Block", "💻")
        ]
        
        for i, (type_id, name, icon) in enumerate(element_types):
            btn = QPushButton(f"{icon} {name}")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, t=type_id: self._select_type(t))
            self.type_buttons[type_id] = btn
            type_layout.addWidget(btn, i // 4, i % 4)
        
        type_group.setLayout(type_layout)
        
        # Metadata configuration
        metadata_group = QGroupBox("Element Metadata")
        metadata_layout = QFormLayout()
        
        self.confidence_spin = QDoubleSpinBox()
        self.confidence_spin.setRange(0.0, 1.0)
        self.confidence_spin.setSingleStep(0.1)
        self.confidence_spin.setValue(0.9)
        
        self.importance_combo = QComboBox()
        self.importance_combo.addItems(["Low", "Medium", "High", "Critical"])
        
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("Enter comma-separated tags")
        
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(60)
        self.notes_edit.setPlaceholderText("Additional notes...")
        
        metadata_layout.addRow("Confidence:", self.confidence_spin)
        metadata_layout.addRow("Importance:", self.importance_combo)
        metadata_layout.addRow("Tags:", self.tags_edit)
        metadata_layout.addRow("Notes:", self.notes_edit)
        metadata_group.setLayout(metadata_layout)
        
        layout.addWidget(type_group)
        layout.addWidget(metadata_group)
        self.setLayout(layout)

class FinalReviewStep(QWizardPage):
    """Final review and validation confirmation."""
    
    def __init__(self, wizard: ValidationWizard):
        super().__init__()
        self.wizard = wizard
        self.setTitle("Final Review")
        self.setSubTitle("Review all validation data before confirmation")
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup final review interface."""
        layout = QVBoxLayout()
        
        # Summary card
        summary_group = QGroupBox("Validation Summary")
        summary_layout = QVBoxLayout()
        
        self.summary_widget = ValidationSummaryWidget()
        summary_layout.addWidget(self.summary_widget)
        summary_group.setLayout(summary_layout)
        
        # Preview of final element
        preview_group = QGroupBox("Element Preview")
        preview_layout = QVBoxLayout()
        
        self.element_preview = ElementPreviewWidget()
        preview_layout.addWidget(self.element_preview)
        preview_group.setLayout(preview_layout)
        
        # Validation actions
        actions_group = QGroupBox("Validation Actions")
        actions_layout = QHBoxLayout()
        
        self.save_continue_btn = QPushButton("Save & Continue")
        self.save_exit_btn = QPushButton("Save & Exit")
        self.discard_btn = QPushButton("Discard")
        
        actions_layout.addWidget(self.save_continue_btn)
        actions_layout.addWidget(self.save_exit_btn)
        actions_layout.addWidget(self.discard_btn)
        actions_group.setLayout(actions_layout)
        
        layout.addWidget(summary_group)
        layout.addWidget(preview_group)
        layout.addWidget(actions_group)
        self.setLayout(layout)
```

#### **2. Validation Toolbar (`toolbar.py`)**
```python
class ValidationToolbar(QToolBar):
    """Professional validation toolbar with contextual controls."""
    
    # Toolbar signals
    tool_selected = pyqtSignal(str)
    mode_changed = pyqtSignal(ToolbarMode)
    element_type_selected = pyqtSignal(ElementType)
    validation_action_triggered = pyqtSignal(str)
    
    def __init__(self, state_manager: DrawingStateManager, parent=None):
        super().__init__("Validation Tools", parent)
        self.state_manager = state_manager
        self.current_mode = ToolbarMode.SELECTION
        self.active_tool = None
        
        self._setup_toolbar()
        self._setup_styling()
        self._connect_signals()
    
    def _setup_toolbar(self):
        """Setup toolbar sections and tools."""
        # Selection tools section
        self._add_section_separator("Selection Tools")
        
        self.selection_tools = QActionGroup(self)
        
        self.rectangle_action = self._create_tool_action(
            "rectangle", "Rectangle Selection", "🔲",
            "Select rectangular areas"
        )
        self.polygon_action = self._create_tool_action(
            "polygon", "Polygon Selection", "🔶", 
            "Select polygonal areas"
        )
        self.freehand_action = self._create_tool_action(
            "freehand", "Freehand Selection", "✏️",
            "Draw freehand selections"
        )
        self.magic_action = self._create_tool_action(
            "magic", "Magic Select", "🪄",
            "Intelligent boundary detection"
        )
        
        # Mode controls section
        self._add_section_separator("Mode Controls")
        
        self.snapping_action = self._create_toggle_action(
            "snapping", "Enable Snapping", "🧲",
            "Toggle magnetic snapping"
        )
        self.multi_select_action = self._create_toggle_action(
            "multi_select", "Multi-Selection", "📋",
            "Enable multiple area selection"
        )
        
        # Validation actions section
        self._add_section_separator("Validation Actions")
        
        self.validate_action = self._create_action(
            "validate", "Validate Element", "✅",
            "Validate current selection"
        )
        self.correct_action = self._create_action(
            "correct", "Correct Text", "📝",
            "Open text correction dialog"
        )
        self.delete_action = self._create_action(
            "delete", "Delete Selection", "🗑️",
            "Delete current selection"
        )
        
        # Status section
        self._add_section_separator("Status")
        
        self.status_widget = ValidationStatusWidget()
        self.addWidget(self.status_widget)
    
    def _create_tool_action(self, tool_id: str, text: str, 
                           icon: str, tooltip: str) -> QAction:
        """Create a tool selection action."""
        action = QAction(f"{icon} {text}", self)
        action.setToolTip(tooltip)
        action.setCheckable(True)
        action.setData(tool_id)
        action.triggered.connect(lambda: self._select_tool(tool_id))
        
        self.selection_tools.addAction(action)
        self.addAction(action)
        return action
    
    def _create_toggle_action(self, action_id: str, text: str,
                             icon: str, tooltip: str) -> QAction:
        """Create a toggle action."""
        action = QAction(f"{icon} {text}", self)
        action.setToolTip(tooltip)
        action.setCheckable(True)
        action.toggled.connect(lambda checked: self._toggle_feature(action_id, checked))
        
        self.addAction(action)
        return action
    
    def _select_tool(self, tool_id: str):
        """Handle tool selection."""
        self.active_tool = tool_id
        self.tool_selected.emit(tool_id)
        self._update_context_actions()
    
    def _update_context_actions(self):
        """Update toolbar based on current context."""
        if self.active_tool == "magic":
            self.snapping_action.setEnabled(False)
        else:
            self.snapping_action.setEnabled(True)

class ValidationStatusWidget(QWidget):
    """Status widget showing current validation state."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup status display."""
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 2, 5, 2)
        
        # Current page indicator
        self.page_label = QLabel("Page: 1/10")
        
        # Progress indicator
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(100)
        self.progress_bar.setMaximumHeight(15)
        
        # Element count
        self.element_count_label = QLabel("Elements: 5")
        
        # Validation status
        self.status_icon = QLabel("🟢")
        self.status_text = QLabel("Ready")
        
        layout.addWidget(self.page_label)
        layout.addWidget(QLabel("|"))
        layout.addWidget(self.progress_bar)
        layout.addWidget(QLabel("|"))
        layout.addWidget(self.element_count_label)
        layout.addWidget(QLabel("|"))
        layout.addWidget(self.status_icon)
        layout.addWidget(self.status_text)
        
        self.setLayout(layout)
```

#### **3. OCR Dialog (`ocr_dialog.py`)**
```python
class OCRDialog(QDialog):
    """Advanced OCR dialog with confidence highlighting and editing."""
    
    # Dialog signals
    text_accepted = pyqtSignal(str)
    text_rejected = pyqtSignal()
    reprocess_requested = pyqtSignal(dict)
    word_selected = pyqtSignal(OCRWord)
    
    def __init__(self, ocr_result: OCRResponse, parent=None):
        super().__init__(parent)
        self.ocr_result = ocr_result
        self.edited_text = ocr_result.text
        self.word_confidences = ocr_result.word_confidences
        
        self.setWindowTitle("OCR Text Review")
        self.setMinimumSize(800, 600)
        
        self._setup_ui()
        self._setup_styling()
        self._connect_signals()
    
    def _setup_ui(self):
        """Setup OCR dialog interface."""
        layout = QVBoxLayout()
        
        # Header with confidence summary
        header_layout = QHBoxLayout()
        
        confidence_widget = QWidget()
        conf_layout = QHBoxLayout(confidence_widget)
        
        self.overall_confidence_label = QLabel("Overall Confidence:")
        self.confidence_bar = QProgressBar()
        self.confidence_bar.setRange(0, 100)
        self.confidence_bar.setValue(int(self.ocr_result.confidence * 100))
        
        conf_layout.addWidget(self.overall_confidence_label)
        conf_layout.addWidget(self.confidence_bar)
        
        header_layout.addWidget(confidence_widget)
        header_layout.addStretch()
        
        # Main content area with splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side - Original image with overlays
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        left_layout.addWidget(QLabel("Original Image:"))
        self.image_viewer = OCRImageViewer(self.ocr_result.source_image)
        left_layout.addWidget(self.image_viewer)
        
        # Image controls
        img_controls = QHBoxLayout()
        self.highlight_words_btn = QPushButton("Highlight Words")
        self.show_confidence_btn = QPushButton("Show Confidence")
        self.zoom_fit_btn = QPushButton("Zoom to Fit")
        
        img_controls.addWidget(self.highlight_words_btn)
        img_controls.addWidget(self.show_confidence_btn)
        img_controls.addWidget(self.zoom_fit_btn)
        left_layout.addLayout(img_controls)
        
        splitter.addWidget(left_widget)
        
        # Right side - Text editing and confidence analysis
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # Text editing area
        text_group = QGroupBox("Extracted Text")
        text_layout = QVBoxLayout(text_group)
        
        self.text_editor = ConfidenceTextEdit(
            self.ocr_result.text,
            self.word_confidences
        )
        text_layout.addWidget(self.text_editor)
        
        # Quick editing tools
        edit_tools = QHBoxLayout()
        self.spell_check_btn = QPushButton("Spell Check")
        self.ai_suggestions_btn = QPushButton("AI Suggestions")
        self.clear_formatting_btn = QPushButton("Clear Formatting")
        
        edit_tools.addWidget(self.spell_check_btn)
        edit_tools.addWidget(self.ai_suggestions_btn)
        edit_tools.addWidget(self.clear_formatting_btn)
        text_layout.addLayout(edit_tools)
        
        right_layout.addWidget(text_group)
        
        # Confidence analysis
        analysis_group = QGroupBox("Confidence Analysis")
        analysis_layout = QVBoxLayout(analysis_group)
        
        self.confidence_chart = ConfidenceChartWidget(self.word_confidences)
        analysis_layout.addWidget(self.confidence_chart)
        
        # Low confidence words list
        low_conf_label = QLabel("Low Confidence Words:")
        self.low_confidence_list = QListWidget()
        self._populate_low_confidence_words()
        
        analysis_layout.addWidget(low_conf_label)
        analysis_layout.addWidget(self.low_confidence_list)
        
        right_layout.addWidget(analysis_group)
        
        splitter.addWidget(right_widget)
        splitter.setSizes([400, 400])  # Equal split
        
        # Dialog buttons
        button_layout = QHBoxLayout()
        
        self.reprocess_btn = QPushButton("Reprocess OCR")
        self.reprocess_btn.setIcon(QIcon("🔄"))
        
        button_box = QDialogButtonBox()
        self.accept_btn = button_box.addButton("Accept", QDialogButtonBox.ButtonRole.AcceptRole)
        self.reject_btn = button_box.addButton("Reject", QDialogButtonBox.ButtonRole.RejectRole)
        self.preview_btn = button_box.addButton("Preview", QDialogButtonBox.ButtonRole.ActionRole)
        
        button_layout.addWidget(self.reprocess_btn)
        button_layout.addStretch()
        button_layout.addWidget(button_box)
        
        # Assemble main layout
        layout.addLayout(header_layout)
        layout.addWidget(splitter, 1)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)

class ConfidenceTextEdit(QTextEdit):
    """Text editor with confidence-based highlighting."""
    
    def __init__(self, text: str, word_confidences: Dict[str, float], parent=None):
        super().__init__(parent)
        self.word_confidences = word_confidences
        self.confidence_threshold = 0.8
        
        self._setup_editor()
        self._apply_confidence_highlighting(text)
    
    def _setup_editor(self):
        """Setup text editor features."""
        # Enable spell checking
        self.setAcceptRichText(True)
        
        # Create confidence-based formats
        self.high_confidence_format = QTextCharFormat()
        self.high_confidence_format.setBackground(QColor(200, 255, 200))  # Light green
        
        self.medium_confidence_format = QTextCharFormat()
        self.medium_confidence_format.setBackground(QColor(255, 255, 200))  # Light yellow
        
        self.low_confidence_format = QTextCharFormat()
        self.low_confidence_format.setBackground(QColor(255, 200, 200))  # Light red
    
    def _apply_confidence_highlighting(self, text: str):
        """Apply confidence-based highlighting to text."""
        self.setPlainText(text)
        cursor = self.textCursor()
        
        for word, confidence in self.word_confidences.items():
            # Find word positions in text
            start = 0
            while True:
                pos = text.find(word, start)
                if pos == -1:
                    break
                
                # Select word
                cursor.setPosition(pos)
                cursor.setPosition(pos + len(word), QTextCursor.MoveMode.KeepAnchor)
                
                # Apply confidence-based format
                if confidence >= 0.9:
                    cursor.setCharFormat(self.high_confidence_format)
                elif confidence >= 0.7:
                    cursor.setCharFormat(self.medium_confidence_format)
                else:
                    cursor.setCharFormat(self.low_confidence_format)
                
                start = pos + len(word)
```

---

## 🔗 **Integration with Agent 1 & 2**

### **Required Dependencies**
```python
# Agent 1 dependencies
from .drawing_state import DrawingStateManager, DrawingMode, DrawingArea
from .area_select import ValidationAreaSelector

# Agent 2 dependencies  
from .snapping import SnapEngine, SnapResult
from .enhanced_shapes import FreehandShape, AdvancedPolygonTool
from .selection_algorithms import SmartBoundaryDetector

# Agent 3 integration layer
class ValidationUIIntegration:
    """Integration layer connecting UI components with validation engine."""
    
    def __init__(self, state_manager: DrawingStateManager, snap_engine: SnapEngine):
        self.state_manager = state_manager
        self.snap_engine = snap_engine
        self.wizard = None
        self.toolbar = None
        self.active_dialogs = {}
    
    def create_validation_wizard(self) -> ValidationWizard:
        """Create wizard with full integration."""
        self.wizard = ValidationWizard(self.state_manager, self.snap_engine)
        self._connect_wizard_signals()
        return self.wizard
    
    def create_validation_toolbar(self) -> ValidationToolbar:
        """Create toolbar with full integration."""
        self.toolbar = ValidationToolbar(self.state_manager)
        self._connect_toolbar_signals()
        return self.toolbar
```

---

## 📊 **Implementation Timeline**

### **Day 1: Validation Wizard Foundation**
- [ ] Implement ValidationWizard base class and workflow
- [ ] Create WelcomeStep and AreaSelectionStep pages
- [ ] Integrate with Agent 1 state management
- [ ] Integrate with Agent 2 selection tools
- [ ] Basic wizard navigation and validation

### **Day 2: Advanced Wizard Steps & OCR Dialog**
- [ ] Implement OCRProcessingStep and TextReviewStep
- [ ] Create ElementTypeStep and FinalReviewStep
- [ ] Implement OCRDialog with confidence visualization
- [ ] Add ConfidenceTextEdit with highlighting
- [ ] Wizard completion workflow and data handling

### **Day 3: Validation Toolbar & Status Components**
- [ ] Implement ValidationToolbar with contextual controls
- [ ] Create ValidationStatusWidget for state display
- [ ] Add tool selection and mode switching
- [ ] Integrate toolbar with Agent 1-2 selection tools
- [ ] Professional styling and responsive design

### **Day 4: Integration & UX Polish**
- [ ] Create ValidationUIIntegration coordination layer
- [ ] Implement advanced UI components (charts, previews)
- [ ] Add accessibility features and keyboard shortcuts
- [ ] Performance optimization for UI responsiveness
- [ ] Comprehensive UI testing and polish

---

## 🧪 **Testing Requirements**

### **UI Component Tests**
```python
class TestValidationWizard:
    """Test validation wizard functionality."""
    
    def test_wizard_workflow_completion(self, qtbot):
        """Test complete wizard workflow."""
        
    def test_wizard_step_navigation(self, qtbot):
        """Test step-by-step navigation."""
        
    def test_wizard_data_persistence(self, qtbot):
        """Test data persistence across steps."""

class TestValidationToolbar:
    """Test validation toolbar functionality."""
    
    def test_tool_selection_and_switching(self, qtbot):
        """Test tool selection and mode switching."""
        
    def test_contextual_controls(self, qtbot):
        """Test contextual control updates."""
        
    def test_status_widget_updates(self, qtbot):
        """Test status widget real-time updates."""

class TestOCRDialog:
    """Test OCR dialog functionality."""
    
    def test_confidence_visualization(self, qtbot):
        """Test confidence highlighting and visualization."""
        
    def test_text_editing_workflow(self, qtbot):
        """Test text editing and correction workflow."""
        
    def test_reprocessing_workflow(self, qtbot):
        """Test OCR reprocessing functionality."""
```

### **Integration Tests**
```python
class TestAgent1Integration:
    """Test integration with Agent 1 components."""
    
    def test_state_manager_integration(self):
        """Test state manager signal integration."""
        
    def test_drawing_state_synchronization(self):
        """Test drawing state synchronization."""

class TestAgent2Integration:
    """Test integration with Agent 2 components."""
    
    def test_snap_engine_ui_integration(self):
        """Test snap engine UI feedback."""
        
    def test_advanced_selection_ui(self):
        """Test advanced selection tool UI integration."""
```

### **Accessibility Tests**
```python
class TestAccessibility:
    """Test accessibility compliance."""
    
    def test_keyboard_navigation(self, qtbot):
        """Test complete keyboard navigation."""
        
    def test_screen_reader_compatibility(self):
        """Test screen reader compatibility."""
        
    def test_color_contrast_compliance(self):
        """Test WCAG color contrast compliance."""
```

---

## 🎯 **Success Criteria**

### **User Experience Metrics**
- [ ] **Wizard Completion**: <5 minutes average completion time
- [ ] **UI Responsiveness**: <100ms response to all user interactions
- [ ] **Error Recovery**: Graceful handling of all error conditions
- [ ] **Learning Curve**: New users productive within 10 minutes
- [ ] **Accessibility**: Full WCAG 2.1 AA compliance

### **Technical Quality**
- [ ] **Test Coverage**: >95% UI component test coverage
- [ ] **Performance**: 60 FPS on all animations and interactions
- [ ] **Memory**: <20MB additional overhead for UI components
- [ ] **Integration**: Seamless integration with Agent 1-2 foundation
- [ ] **Styling**: Professional, consistent visual design

### **Integration Quality**
- [ ] **Signal Compatibility**: All PyQt6 signals properly connected
- [ ] **State Synchronization**: Real-time state sync across components
- [ ] **Data Flow**: Clean data flow from UI to validation engine
- [ ] **Error Handling**: Comprehensive error handling and user feedback

---

## 🔌 **API Interface for Agent 4**

### **Integration Points for Agent 4**
```python
# Agent 4 will integrate these UI components
class ValidationUIAPI:
    """API interface for Agent 4 integration layer."""
    
    def get_wizard_instance(self) -> ValidationWizard:
        """Get wizard instance for integration testing."""
        
    def get_toolbar_instance(self) -> ValidationToolbar:
        """Get toolbar instance for coordination."""
        
    def get_active_dialogs(self) -> Dict[str, QDialog]:
        """Get active dialog instances."""
        
    def register_validation_session(self, session_id: str) -> None:
        """Register validation session with UI components."""

# UI coordination signals for Agent 4
ui_workflow_started = pyqtSignal(str)  # workflow_type
ui_workflow_completed = pyqtSignal(dict)  # workflow_data
ui_error_occurred = pyqtSignal(str, Exception)  # component, error
ui_performance_warning = pyqtSignal(str, float)  # operation, duration
```

---

## 🚀 **Deployment Instructions**

### **Agent 3 Deployment Command**
```bash
# After Agent 1-2 completion, deploy Agent 3 with:
"I need you to work on Sub-Issue #26.3 - UI Components & User Experience. Create professional validation wizard, toolbar, OCR dialog, and complete user experience workflows that integrate Agent 1's core framework and Agent 2's advanced selection tools into a cohesive manual validation system."
```

### **Branch Management**
```bash
git checkout -b feature/validation-ui-agent3-issue26-3
git merge feature/validation-core-agent1-issue26-1
git merge feature/validation-selection-agent2-issue26-2
```

### **Integration Checklist**
- [ ] Agent 1 core framework fully implemented and tested
- [ ] Agent 2 advanced selection tools completed and integrated  
- [ ] All Agent 1-2 APIs stable and documented
- [ ] PyQt6 signal interfaces established
- [ ] UI integration points identified and prepared

---

**Agent 3 Ready for Deployment** 🎨

This specification provides Agent 3 with comprehensive requirements for building professional UI components that create an intuitive, accessible, and efficient user experience for the manual validation system.