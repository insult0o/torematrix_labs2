# Agent 1: PDF.js Core Viewer Foundation
**Issue #16.1 | Sub-Issue #124 | Days 1-2 | Critical Path Foundation**

## 🎯 Your Mission
You are **Agent 1**, responsible for implementing the foundational PDF.js viewer integration with PyQt6. Your work is **critical path** - all other agents depend on your foundation. You will create the core PDF rendering system, basic controls, and establish the integration architecture that others will build upon.

## 📋 Your Specific Tasks

### Phase 1: PDF.js Bundle Setup & Integration
#### 1.1 Download and Setup PDF.js
```bash
# Create PDF.js resources directory
mkdir -p resources/pdfjs

# Download PDF.js v3.11.x (latest stable)
# Place these files in resources/pdfjs/:
# - pdf.min.js (main PDF.js library)
# - pdf.worker.min.js (Web Worker for PDF processing)
# - viewer.html (custom viewer template)
```

#### 1.2 Create Custom Viewer Template
Create `resources/pdfjs/viewer.html` with:
```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>TORE Matrix PDF Viewer</title>
    <style>
        body { margin: 0; padding: 0; font-family: Arial, sans-serif; }
        #viewerContainer { width: 100%; height: 100vh; overflow: auto; }
        #viewer { width: 100%; }
        .page { margin: 10px auto; box-shadow: 0 2px 10px rgba(0,0,0,0.3); }
        canvas { display: block; }
    </style>
</head>
<body>
    <div id="viewerContainer">
        <div id="viewer"></div>
    </div>
    
    <script src="pdf.min.js"></script>
    <script src="viewer.js"></script>
</body>
</html>
```

#### 1.3 Verify PDF.js Integration
```python
# Test script to verify PDF.js works
def test_pdfjs_integration():
    """Verify PDF.js can load and render a simple PDF."""
    # Load test PDF
    # Verify rendering works
    # Check error handling
```

### Phase 2: Core PDFViewer Implementation
Create `src/torematrix/integrations/pdf/viewer.py`:

```python
"""
Core PDF.js viewer integration with PyQt6.

This module provides the foundational PDFViewer class that embeds PDF.js
in a QWebEngineView for high-performance PDF rendering and basic controls.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin

from PyQt6.QtCore import QUrl, QTimer, pyqtSignal, QObject
from PyQt6.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage
from PyQt6.QtWidgets import QWidget

logger = logging.getLogger(__name__)


class PDFLoadError(Exception):
    """Exception raised when PDF loading fails."""
    pass


class PDFDocument:
    """Represents a loaded PDF document with metadata."""
    
    def __init__(self, file_path: Path, url: str = None):
        self.file_path = file_path
        self.url = url
        self.page_count: int = 0
        self.title: str = ""
        self.metadata: Dict[str, Any] = {}
        self.current_page: int = 1
        self.zoom_level: float = 1.0
        self.is_loaded: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize document state."""
        return {
            'file_path': str(self.file_path),
            'page_count': self.page_count,
            'title': self.title,
            'current_page': self.current_page,
            'zoom_level': self.zoom_level,
            'is_loaded': self.is_loaded
        }


class PDFViewer(QWebEngineView):
    """
    Core PDF.js viewer widget integrated with PyQt6.
    
    Provides high-performance PDF rendering using PDF.js embedded in
    QWebEngineView with support for basic navigation and controls.
    
    Signals:
        document_loaded: Emitted when PDF is successfully loaded
        load_error: Emitted when PDF loading fails
        page_changed: Emitted when current page changes
        zoom_changed: Emitted when zoom level changes
    """
    
    # Signals
    document_loaded = pyqtSignal(PDFDocument)
    load_error = pyqtSignal(str, str)  # error_code, error_message
    page_changed = pyqtSignal(int)  # new_page_number
    zoom_changed = pyqtSignal(float)  # new_zoom_level
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize PDF viewer."""
        super().__init__(parent)
        
        # Document management
        self.current_document: Optional[PDFDocument] = None
        self._temp_files: List[str] = []
        
        # Configuration
        self.min_zoom = 0.25
        self.max_zoom = 5.0
        self.zoom_step = 0.25
        
        # Initialize web engine
        self._setup_web_engine()
        
        # Initialize PDF.js
        self._initialize_pdfjs()
        
        logger.info("PDFViewer initialized")
    
    def _setup_web_engine(self) -> None:
        """Configure QWebEngine settings for optimal PDF viewing."""
        # Get profile and settings
        profile = QWebEngineProfile.defaultProfile()
        settings = self.settings()
        
        # Enable JavaScript (required for PDF.js)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        
        # Enable local file access
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True
        )
        
        # Optimize for PDF viewing
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, True
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.SpatialNavigationEnabled, False
        )
        
        # Performance settings
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.WebGLEnabled, True
        )
    
    def _initialize_pdfjs(self) -> None:
        """Initialize PDF.js viewer."""
        # Get viewer HTML path
        viewer_path = Path(__file__).parent.parent.parent.parent / "resources" / "pdfjs" / "viewer.html"
        
        if not viewer_path.exists():
            raise FileNotFoundError(f"PDF.js viewer not found at {viewer_path}")
        
        # Load viewer
        viewer_url = QUrl.fromLocalFile(str(viewer_path))
        self.setUrl(viewer_url)
        
        logger.info(f"PDF.js viewer loaded from {viewer_path}")
    
    def load_pdf(self, file_path: Path) -> None:
        """
        Load a PDF file for viewing.
        
        Args:
            file_path: Path to PDF file
            
        Raises:
            PDFLoadError: If PDF loading fails
        """
        if not file_path.exists():
            error_msg = f"PDF file not found: {file_path}"
            logger.error(error_msg)
            self.load_error.emit("FILE_NOT_FOUND", error_msg)
            raise PDFLoadError(error_msg)
        
        try:
            # Create document object
            document = PDFDocument(file_path)
            
            # Load PDF via JavaScript
            pdf_url = QUrl.fromLocalFile(str(file_path)).toString()
            js_code = f"""
                if (typeof loadPDF === 'function') {{
                    loadPDF('{pdf_url}');
                }} else {{
                    console.error('PDF.js not ready');
                }}
            """
            
            self.page().runJavaScript(js_code, self._on_pdf_load_result)
            
            # Store current document
            self.current_document = document
            
            logger.info(f"Loading PDF: {file_path}")
            
        except Exception as e:
            error_msg = f"Failed to load PDF: {e}"
            logger.error(error_msg)
            self.load_error.emit("LOAD_FAILED", error_msg)
            raise PDFLoadError(error_msg)
    
    def _on_pdf_load_result(self, result: Any) -> None:
        """Handle PDF load result from JavaScript."""
        if result and self.current_document:
            # Update document metadata
            self.current_document.is_loaded = True
            
            # Emit success signal
            self.document_loaded.emit(self.current_document)
            logger.info("PDF loaded successfully")
        else:
            error_msg = "PDF loading failed in JavaScript"
            logger.error(error_msg)
            self.load_error.emit("JS_LOAD_FAILED", error_msg)
    
    def close_document(self) -> None:
        """Close current document and cleanup resources."""
        if self.current_document:
            logger.info(f"Closing document: {self.current_document.file_path}")
            self.current_document = None
        
        # Cleanup temporary files
        self._cleanup_temp_files()
        
        # Clear viewer
        js_code = """
            if (typeof clearViewer === 'function') {
                clearViewer();
            }
        """
        self.page().runJavaScript(js_code)
    
    # Navigation methods
    def go_to_page(self, page_number: int) -> None:
        """Navigate to specific page."""
        if not self.current_document or not self.current_document.is_loaded:
            return
        
        js_code = f"if (typeof goToPage === 'function') {{ goToPage({page_number}); }}"
        self.page().runJavaScript(js_code)
        
        self.current_document.current_page = page_number
        self.page_changed.emit(page_number)
    
    def next_page(self) -> None:
        """Navigate to next page."""
        if self.current_document and self.current_document.current_page < self.current_document.page_count:
            self.go_to_page(self.current_document.current_page + 1)
    
    def previous_page(self) -> None:
        """Navigate to previous page."""
        if self.current_document and self.current_document.current_page > 1:
            self.go_to_page(self.current_document.current_page - 1)
    
    def first_page(self) -> None:
        """Navigate to first page."""
        self.go_to_page(1)
    
    def last_page(self) -> None:
        """Navigate to last page."""
        if self.current_document:
            self.go_to_page(self.current_document.page_count)
    
    # Zoom methods
    def set_zoom(self, zoom_level: float) -> None:
        """Set zoom level."""
        zoom_level = max(self.min_zoom, min(self.max_zoom, zoom_level))
        
        js_code = f"if (typeof setZoom === 'function') {{ setZoom({zoom_level}); }}"
        self.page().runJavaScript(js_code)
        
        if self.current_document:
            self.current_document.zoom_level = zoom_level
        
        self.zoom_changed.emit(zoom_level)
    
    def zoom_in(self) -> None:
        """Increase zoom level."""
        current_zoom = self.current_document.zoom_level if self.current_document else 1.0
        self.set_zoom(current_zoom + self.zoom_step)
    
    def zoom_out(self) -> None:
        """Decrease zoom level."""
        current_zoom = self.current_document.zoom_level if self.current_document else 1.0
        self.set_zoom(current_zoom - self.zoom_step)
    
    def fit_width(self) -> None:
        """Fit PDF to width."""
        js_code = "if (typeof fitWidth === 'function') { fitWidth(); }"
        self.page().runJavaScript(js_code)
    
    def fit_page(self) -> None:
        """Fit full page in view."""
        js_code = "if (typeof fitPage === 'function') { fitPage(); }"
        self.page().runJavaScript(js_code)
    
    # Integration interfaces for other agents
    def attach_bridge(self, bridge) -> None:
        """Interface for Agent 2 to attach communication bridge."""
        # Implementation will be added by Agent 2
        pass
    
    def set_performance_config(self, config) -> None:
        """Interface for Agent 3 to set performance configuration."""
        # Implementation will be added by Agent 3
        pass
    
    def enable_features(self, features) -> None:
        """Interface for Agent 4 to enable advanced features."""
        # Implementation will be added by Agent 4
        pass
    
    # Utility methods
    def get_document_info(self) -> Optional[Dict[str, Any]]:
        """Get current document information."""
        return self.current_document.to_dict() if self.current_document else None
    
    def _cleanup_temp_files(self) -> None:
        """Cleanup temporary files."""
        for temp_file in self._temp_files:
            try:
                Path(temp_file).unlink(missing_ok=True)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file {temp_file}: {e}")
        
        self._temp_files.clear()
    
    def closeEvent(self, event) -> None:
        """Handle widget close event."""
        self.close_document()
        super().closeEvent(event)
```

### Phase 3: JavaScript Viewer Implementation
Create `resources/pdfjs/viewer.js`:

```javascript
/**
 * PDF.js viewer integration for TORE Matrix Labs
 * Provides core PDF rendering and basic controls
 */

let pdfDoc = null;
let currentPage = 1;
let totalPages = 0;
let currentZoom = 1.0;
let renderTasks = [];

// Initialize PDF.js
pdfjsLib.GlobalWorkerOptions.workerSrc = 'pdf.worker.min.js';

/**
 * Load PDF from URL
 */
async function loadPDF(url) {
    try {
        console.log('Loading PDF:', url);
        
        const pdf = await pdfjsLib.getDocument(url).promise;
        pdfDoc = pdf;
        totalPages = pdf.numPages;
        currentPage = 1;
        
        console.log('PDF loaded, pages:', totalPages);
        
        // Render first page
        await renderPage(1);
        
        // Notify Qt about successful load
        if (typeof qt !== 'undefined' && qt.webChannelTransport) {
            // Bridge communication will be added by Agent 2
        }
        
        return { success: true, pages: totalPages };
        
    } catch (error) {
        console.error('Error loading PDF:', error);
        return { success: false, error: error.message };
    }
}

/**
 * Render specific page
 */
async function renderPage(pageNum) {
    if (!pdfDoc || pageNum < 1 || pageNum > totalPages) {
        return;
    }
    
    try {
        const page = await pdfDoc.getPage(pageNum);
        
        // Calculate viewport
        const viewport = page.getViewport({ scale: currentZoom });
        
        // Create canvas
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('2d');
        canvas.height = viewport.height;
        canvas.width = viewport.width;
        
        // Clear existing page
        const viewer = document.getElementById('viewer');
        const existingPage = viewer.querySelector(`[data-page="${pageNum}"]`);
        
        if (existingPage) {
            existingPage.remove();
        }
        
        // Create page container
        const pageDiv = document.createElement('div');
        pageDiv.className = 'page';
        pageDiv.setAttribute('data-page', pageNum);
        pageDiv.appendChild(canvas);
        
        viewer.appendChild(pageDiv);
        
        // Render PDF page
        const renderContext = {
            canvasContext: context,
            viewport: viewport
        };
        
        const renderTask = page.render(renderContext);
        renderTasks.push(renderTask);
        
        await renderTask.promise;
        
        currentPage = pageNum;
        console.log('Rendered page:', pageNum);
        
    } catch (error) {
        console.error('Error rendering page:', error);
    }
}

/**
 * Navigation functions
 */
function goToPage(pageNum) {
    if (pageNum >= 1 && pageNum <= totalPages) {
        renderPage(pageNum);
    }
}

function nextPage() {
    if (currentPage < totalPages) {
        goToPage(currentPage + 1);
    }
}

function prevPage() {
    if (currentPage > 1) {
        goToPage(currentPage - 1);
    }
}

/**
 * Zoom functions
 */
function setZoom(zoom) {
    currentZoom = zoom;
    renderPage(currentPage);
}

function zoomIn() {
    setZoom(currentZoom * 1.25);
}

function zoomOut() {
    setZoom(currentZoom / 1.25);
}

function fitWidth() {
    const container = document.getElementById('viewerContainer');
    const containerWidth = container.clientWidth - 40; // Account for margins
    
    if (pdfDoc) {
        pdfDoc.getPage(currentPage).then(page => {
            const viewport = page.getViewport({ scale: 1.0 });
            const scale = containerWidth / viewport.width;
            setZoom(scale);
        });
    }
}

function fitPage() {
    const container = document.getElementById('viewerContainer');
    const containerWidth = container.clientWidth - 40;
    const containerHeight = container.clientHeight - 40;
    
    if (pdfDoc) {
        pdfDoc.getPage(currentPage).then(page => {
            const viewport = page.getViewport({ scale: 1.0 });
            const scaleX = containerWidth / viewport.width;
            const scaleY = containerHeight / viewport.height;
            const scale = Math.min(scaleX, scaleY);
            setZoom(scale);
        });
    }
}

/**
 * Cleanup function
 */
function clearViewer() {
    // Cancel all render tasks
    renderTasks.forEach(task => {
        if (task && typeof task.cancel === 'function') {
            task.cancel();
        }
    });
    renderTasks = [];
    
    // Clear viewer
    const viewer = document.getElementById('viewer');
    if (viewer) {
        viewer.innerHTML = '';
    }
    
    // Reset state
    pdfDoc = null;
    currentPage = 1;
    totalPages = 0;
    currentZoom = 1.0;
    
    console.log('Viewer cleared');
}

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    if (!pdfDoc) return;
    
    switch(e.key) {
        case 'ArrowRight':
        case 'PageDown':
            nextPage();
            e.preventDefault();
            break;
        case 'ArrowLeft':
        case 'PageUp':
            prevPage();
            e.preventDefault();
            break;
        case 'Home':
            goToPage(1);
            e.preventDefault();
            break;
        case 'End':
            goToPage(totalPages);
            e.preventDefault();
            break;
        case '+':
        case '=':
            if (e.ctrlKey) {
                zoomIn();
                e.preventDefault();
            }
            break;
        case '-':
            if (e.ctrlKey) {
                zoomOut();
                e.preventDefault();
            }
            break;
    }
});

console.log('PDF.js viewer initialized');
```

### Phase 4: Testing & Validation
Create `tests/unit/pdf/test_viewer.py`:

```python
"""Tests for PDF.js core viewer functionality."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from PyQt6.QtWidgets import QApplication

from torematrix.integrations.pdf.viewer import PDFViewer, PDFDocument, PDFLoadError


class TestPDFDocument:
    """Test PDFDocument class."""
    
    def test_document_creation(self):
        """Test document object creation."""
        file_path = Path("test.pdf")
        doc = PDFDocument(file_path)
        
        assert doc.file_path == file_path
        assert doc.page_count == 0
        assert doc.current_page == 1
        assert doc.zoom_level == 1.0
        assert not doc.is_loaded
    
    def test_document_serialization(self):
        """Test document serialization."""
        file_path = Path("test.pdf")
        doc = PDFDocument(file_path)
        doc.page_count = 10
        doc.current_page = 5
        doc.is_loaded = True
        
        data = doc.to_dict()
        
        assert data['file_path'] == str(file_path)
        assert data['page_count'] == 10
        assert data['current_page'] == 5
        assert data['is_loaded'] is True


class TestPDFViewer:
    """Test PDFViewer class."""
    
    @pytest.fixture
    def app(self):
        """Create QApplication for testing."""
        if not QApplication.instance():
            return QApplication([])
        return QApplication.instance()
    
    @pytest.fixture
    def viewer(self, app):
        """Create PDFViewer instance."""
        return PDFViewer()
    
    def test_viewer_initialization(self, viewer):
        """Test viewer initialization."""
        assert viewer.min_zoom == 0.25
        assert viewer.max_zoom == 5.0
        assert viewer.zoom_step == 0.25
        assert viewer.current_document is None
    
    def test_zoom_controls(self, viewer):
        """Test zoom functionality."""
        # Create mock document
        viewer.current_document = PDFDocument(Path("test.pdf"))
        viewer.current_document.zoom_level = 1.0
        
        # Mock JavaScript execution
        with patch.object(viewer.page(), 'runJavaScript') as mock_js:
            viewer.set_zoom(1.5)
            mock_js.assert_called()
            assert viewer.current_document.zoom_level == 1.5
    
    def test_navigation_controls(self, viewer):
        """Test page navigation."""
        # Create mock document
        viewer.current_document = PDFDocument(Path("test.pdf"))
        viewer.current_document.page_count = 10
        viewer.current_document.current_page = 5
        
        # Mock JavaScript execution
        with patch.object(viewer.page(), 'runJavaScript') as mock_js:
            viewer.next_page()
            mock_js.assert_called()
            assert viewer.current_document.current_page == 6
    
    def test_load_nonexistent_file(self, viewer):
        """Test loading non-existent file."""
        with pytest.raises(PDFLoadError):
            viewer.load_pdf(Path("nonexistent.pdf"))
    
    def test_document_cleanup(self, viewer):
        """Test document cleanup."""
        viewer.current_document = PDFDocument(Path("test.pdf"))
        
        with patch.object(viewer.page(), 'runJavaScript') as mock_js:
            viewer.close_document()
            mock_js.assert_called()
            assert viewer.current_document is None
```

## 🔗 Integration Points You Must Implement

### For Agent 2 (Bridge Integration)
```python
def attach_bridge(self, bridge) -> None:
    """Attach communication bridge - IMPLEMENT THIS INTERFACE."""
    self._bridge = bridge
    # Agent 2 will implement the actual bridge attachment
```

### For Agent 3 (Performance Integration)  
```python
def set_performance_config(self, config) -> None:
    """Set performance configuration - IMPLEMENT THIS INTERFACE."""
    self._performance_config = config
    # Agent 3 will implement performance optimizations
```

### For Agent 4 (Features Integration)
```python
def enable_features(self, features) -> None:
    """Enable advanced features - IMPLEMENT THIS INTERFACE."""
    self._enabled_features = features
    # Agent 4 will implement advanced features
```

## 📁 Files You Must Create

```
src/torematrix/integrations/pdf/
├── __init__.py                    # Package initialization
├── viewer.py                      # Main PDFViewer class (YOUR FOCUS)
└── exceptions.py                  # PDF-related exceptions

resources/pdfjs/
├── pdf.min.js                     # PDF.js library
├── pdf.worker.min.js              # PDF.js worker
├── viewer.html                    # Custom viewer template  
└── viewer.js                      # JavaScript viewer logic (YOUR FOCUS)

tests/unit/pdf/
├── __init__.py                    # Test package
├── test_viewer.py                 # Viewer tests (YOUR FOCUS)
└── conftest.py                    # Test configuration
```

## 🎯 Success Criteria

### Functional Requirements ✅
- [ ] PDF.js v3.11.x integrated and functional
- [ ] PDFViewer class loads and displays PDFs
- [ ] Basic zoom controls working (25%-500%)
- [ ] Page navigation functional (next/prev/goto)
- [ ] Keyboard shortcuts implemented
- [ ] Error handling for invalid PDFs

### Performance Requirements ✅
- [ ] Load time <2s for 10MB PDFs
- [ ] Memory usage <50MB baseline
- [ ] Zoom response <100ms
- [ ] Page navigation <50ms

### Code Quality Requirements ✅
- [ ] Full type hints throughout
- [ ] Comprehensive docstrings
- [ ] Unit test coverage >95%
- [ ] Integration interfaces implemented
- [ ] Clean separation of concerns

### Integration Requirements ✅
- [ ] Bridge attachment interface ready
- [ ] Performance configuration interface ready
- [ ] Feature enablement interface ready
- [ ] Event signals properly implemented

## ⚠️ Critical Dependencies

### PDF.js Files Required
You **must** download and verify these files work:
- `pdf.min.js` - Main PDF.js library
- `pdf.worker.min.js` - Web Worker for PDF processing
- Compatible with v3.11.x (latest stable)

### PyQt6 Requirements
- QWebEngineView properly configured
- JavaScript enabled and working
- Local file access permissions set
- Web channel ready for Agent 2

## 🚀 Getting Started

### Step 1: Environment Setup
```bash
# Create your branch
git checkout -b feature/pdfjs-core-viewer

# Create directory structure
mkdir -p src/torematrix/integrations/pdf
mkdir -p resources/pdfjs
mkdir -p tests/unit/pdf
```

### Step 2: Download PDF.js
```bash
# Download from https://github.com/mozilla/pdf.js/releases
# Extract pdf.min.js and pdf.worker.min.js to resources/pdfjs/
```

### Step 3: Implement Core Classes
1. Start with `PDFDocument` class
2. Implement `PDFViewer` initialization
3. Add PDF loading functionality  
4. Implement basic controls
5. Add JavaScript integration

### Step 4: Test & Validate
```bash
# Run tests
python -m pytest tests/unit/pdf/ -v

# Test with real PDFs
python -c "
from torematrix.integrations.pdf.viewer import PDFViewer
# Manual testing code
"
```

## 📊 Daily Progress Tracking

### Day 1 Goals
- [ ] PDF.js bundle downloaded and integrated
- [ ] PDFViewer class structure complete
- [ ] Basic PDF loading functional
- [ ] JavaScript viewer foundation ready

### Day 2 Goals  
- [ ] All navigation controls working
- [ ] Zoom functionality complete
- [ ] Error handling robust
- [ ] Tests passing >95% coverage
- [ ] **Ready for Agent 2 handoff**

## 🤝 Coordination Notes

### Your Role in Agent Workflow
- **You are the foundation** - everyone depends on your work
- **Quality is critical** - bugs here affect all agents
- **Document your interfaces** - others need clear integration points
- **Test thoroughly** - your tests validate the foundation

### Handoff to Agent 2
After Day 2, Agent 2 needs:
- Working PDFViewer class with PDF loading
- Bridge attachment interface implemented
- JavaScript viewer functional
- Clear documentation of integration points

### Communication
- Update sub-issue #124 daily with progress
- Tag any blockers immediately  
- Document any architecture decisions
- Ensure your code is well-commented for other agents

---

**You are Agent 1. Your mission is the critical foundation that enables all PDF.js integration. Build it well, test it thoroughly, and enable the team's success!**