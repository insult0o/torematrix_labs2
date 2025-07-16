# AGENT 2 VALIDATION: OCR Service Integration

## 🎯 Your Assignment
You are **Agent 2** responsible for implementing comprehensive OCR service integration for manual validation with worker threads and quality assessment.

## 🚨 CRITICAL: Agent Self-Awareness
- **Your Identity**: Agent 2 (Data/Persistence)
- **Your Branch**: `feature/validation-agent2-issue27`
- **Your Sub-Issue**: #240 - OCR Service Integration
- **Dependencies**: Agent 1 (DrawingStateManager)

## 📋 Core Implementation Tasks

### 1. OCR Service (`src/torematrix/ui/tools/validation/ocr_service.py`)
```python
class ValidationOCRService(QObject):
    """OCR service for manual validation interface."""
    
    # Required signals
    ocr_completed = pyqtSignal(object)  # ValidationOCRResponse
    ocr_failed = pyqtSignal(str, str)  # request_id, error_message
    engine_ready = pyqtSignal()
    engine_error = pyqtSignal(str)
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._config = OCRConfiguration()
        self._worker_thread: Optional[OCRWorkerThread] = None
        self._pending_requests: Dict[str, ValidationOCRRequest] = {}
        self._stats = {
            "requests_processed": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "average_processing_time": 0.0,
            "total_processing_time": 0.0
        }
```

### 2. Worker Thread Architecture
```python
class OCRWorkerThread(QThread):
    """Worker thread for OCR processing."""
    
    result_ready = pyqtSignal(object)  # ValidationOCRResponse
    error_occurred = pyqtSignal(str, str)  # request_id, error_message
    
    def __init__(self):
        super().__init__()
        self.request_queue = []
        self.ocr_engine: Optional[OCREngine] = None
        self.mutex = QMutex()
        self.is_running = False
    
    def run(self):
        """Main worker thread loop."""
        # Process requests from queue
        # Handle OCR processing
        # Emit results or errors
```

### 3. Data Structures
```python
@dataclass
class ValidationOCRRequest:
    """OCR request for manual validation."""
    request_id: str
    image_data: Union[QPixmap, QImage, bytes, str]
    area: Rectangle
    config: Optional[OCRConfiguration] = None
    preprocessing_options: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class ValidationOCRResponse:
    """OCR response for manual validation."""
    request_id: str
    result: OCRResult
    processing_time: float
    preprocessing_applied: List[str] = field(default_factory=list)
    validation_metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def is_high_confidence(self) -> bool:
        """Check if OCR result has high confidence."""
        return self.result.confidence > 0.8
    
    @property
    def requires_manual_review(self) -> bool:
        """Check if result requires manual review."""
        return (self.result.confidence < 0.6 or 
                len(self.result.text.strip()) < 3 or
                not self.result.text.strip())
```

### 4. Quality Assessment Helper
```python
class OCRValidationHelper:
    """Helper class for OCR validation and quality assessment."""
    
    @staticmethod
    def assess_ocr_quality(response: ValidationOCRResponse) -> Dict[str, Any]:
        """Assess OCR quality and provide recommendations."""
        # Analyze confidence levels
        # Provide quality score
        # Generate recommendations
        
    @staticmethod
    def suggest_improvements(response: ValidationOCRResponse) -> List[str]:
        """Suggest improvements for OCR quality."""
        # Analyze preprocessing results
        # Suggest different engines
        # Recommend image improvements
```

### 5. Image Preprocessing Pipeline
```python
def _preprocess_image(self, image_data: Union[QPixmap, QImage, bytes, str], 
                     options: Dict[str, Any]) -> Tuple[bytes, List[str]]:
    """Preprocess image for OCR."""
    preprocessing_applied = []
    
    # Convert to QImage if needed
    # Apply contrast enhancement
    # Apply denoising
    # Apply sharpening
    # Resize for optimal OCR
    
    return image_bytes, preprocessing_applied
```

## 🧪 Testing Requirements (`tests/unit/ui/tools/validation/test_ocr_service.py`)

### Test Categories (>95% Coverage Required)
1. **Service Management Tests**
   - Service initialization
   - Configuration management
   - Statistics tracking

2. **Worker Thread Tests**
   - Thread lifecycle
   - Request processing
   - Error handling

3. **OCR Processing Tests**
   - Image preprocessing
   - Multi-engine support
   - Quality assessment

4. **Request Management Tests**
   - Request queuing
   - Cancellation
   - Timeout handling

5. **Integration Tests**
   - Drawing manager integration
   - Signal handling
   - Error propagation

### Example Test Structure
```python
class TestValidationOCRService:
    @pytest.fixture
    def ocr_service(self):
        return ValidationOCRService()
    
    def test_initialization(self, ocr_service):
        assert isinstance(ocr_service._config, OCRConfiguration)
        assert ocr_service._worker_thread is None
        assert ocr_service._pending_requests == {}
    
    def test_process_area(self, ocr_service):
        # Mock worker thread
        ocr_service._worker_thread = Mock()
        
        image_data = QPixmap(100, 80)
        area = Rectangle(10, 20, 100, 80)
        
        request_id = ocr_service.process_area(image_data, area)
        
        assert isinstance(request_id, str)
        assert request_id in ocr_service._pending_requests
```

## 🔗 Integration Points

### With Agent 1 (Drawing Manager)
```python
# Integrate with drawing manager OCR hooks
def integrate_with_drawing_manager(self, drawing_manager: DrawingStateManager):
    """Integrate OCR service with drawing manager."""
    drawing_manager.initialize_ocr(self.get_config().__dict__)
    
    # Connect signals for automatic OCR processing
    drawing_manager.area_selected.connect(self._on_area_selected)
```

### With Agent 3 (UI Components)
```python
# Provide clean API for UI components
def process_area(self, image_data: Union[QPixmap, QImage, bytes, str], 
                area: Rectangle, 
                preprocessing_options: Optional[Dict[str, Any]] = None) -> str:
    """Process OCR for a specific area."""
    
def get_statistics(self) -> Dict[str, Any]:
    """Get OCR service statistics."""
    
def get_pending_requests(self) -> List[str]:
    """Get list of pending request IDs."""
```

## 📊 Success Criteria

### Functionality Requirements
- [ ] Multi-threaded OCR processing works correctly
- [ ] Image preprocessing improves OCR quality
- [ ] Quality assessment provides reliable confidence scores
- [ ] Request management handles concurrent operations
- [ ] Error handling prevents crashes
- [ ] Statistics tracking is comprehensive
- [ ] Multi-engine support works seamlessly

### Technical Requirements
- [ ] Thread-safe operations
- [ ] Proper Qt signal/slot usage
- [ ] Efficient image processing
- [ ] Robust error handling
- [ ] Comprehensive logging
- [ ] >95% test coverage

## 🚀 Implementation Steps

1. **Setup Branch**: `git checkout -b feature/validation-agent2-issue27`
2. **Create Data Structures**: ValidationOCRRequest, ValidationOCRResponse
3. **Implement Worker Thread**: OCRWorkerThread with request processing
4. **Create OCR Service**: ValidationOCRService with queue management
5. **Add Image Preprocessing**: Contrast, denoising, sharpening pipeline
6. **Implement Quality Assessment**: OCRValidationHelper with recommendations
7. **Add Multi-Engine Support**: Tesseract, EasyOCR integration
8. **Create Statistics**: Comprehensive tracking and reporting
9. **Implement Integration**: Drawing manager hooks and UI APIs
10. **Add Error Handling**: Comprehensive error recovery
11. **Create Tests**: >95% coverage with all scenarios
12. **Verify Integration**: Test with Agent 1 components

## 📋 GitHub Workflow

### Branch Management
```bash
git checkout main
git pull origin main
git checkout -b feature/validation-agent2-issue27
```

### Commit and PR Process
Follow the standard "end work" routine:
1. Run all tests: `python -m pytest tests/unit/ui/tools/validation/test_ocr_service.py -v`
2. Commit changes with standardized message
3. Push branch: `git push -u origin feature/validation-agent2-issue27`
4. Create PR referencing Issue #240
5. Update main issue #27 with progress
6. Tick all checkboxes in Issue #240
7. Close Issue #240 with completion summary

## 🎯 Final Deliverables

### Code Files
- `src/torematrix/ui/tools/validation/ocr_service.py` - Complete implementation
- `tests/unit/ui/tools/validation/test_ocr_service.py` - Comprehensive tests

### Documentation
- API documentation for all public methods
- Integration examples for drawing manager
- Configuration options and preprocessing settings

### GitHub Updates
- PR with detailed implementation description
- Issue #240 fully completed with all checkboxes ticked
- Main issue #27 updated with Agent 2 completion

Remember: You provide the **data processing backbone** - ensure your OCR service is fast, accurate, and reliable!