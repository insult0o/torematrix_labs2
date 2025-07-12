# New Components API Reference

## Overview

This document provides comprehensive API reference for the new components introduced in TORE Matrix Labs v2.0, including the highlighting system, multi-document support, and enhanced validation workflows.

## Table of Contents

1. [Highlighting System API](#highlighting-system-api)
2. [Page Validation API](#page-validation-api)
3. [Manual Validation API](#manual-validation-api)
4. [Document State Management API](#document-state-management-api)
5. [Area Storage Management API](#area-storage-management-api)
6. [Session Recovery API](#session-recovery-api)

## Highlighting System API

### HighlightingEngine

#### Class: `HighlightingEngine`

Central coordinator for all highlighting operations with multi-box rendering support.

```python
class HighlightingEngine:
    def __init__(self, pdf_viewer=None, text_widget=None):
        """Initialize highlighting engine.
        
        Args:
            pdf_viewer: PDF viewer widget for coordinate mapping
            text_widget: Text widget for highlighting synchronization
        """
```

#### Methods

##### `set_pdf_viewer(pdf_viewer)`
Set the PDF viewer for highlighting operations.

**Parameters:**
- `pdf_viewer` (PDFViewer): PDF viewer widget

**Returns:**
- None

**Example:**
```python
engine = HighlightingEngine()
engine.set_pdf_viewer(pdf_viewer)
```

##### `set_text_widget(text_widget)`
Set the text widget for highlighting synchronization.

**Parameters:**
- `text_widget` (QTextEdit): Text widget for highlighting

**Returns:**
- None

##### `highlight_text_range(text_start, text_end, highlight_type='active_highlight', page=None)`
Create a text-based highlight with multi-box rendering.

**Parameters:**
- `text_start` (int): Starting text position
- `text_end` (int): Ending text position
- `highlight_type` (str): Type of highlight ('active_highlight', 'issue', etc.)
- `page` (int, optional): Page number (1-based)

**Returns:**
- `str`: Unique highlight ID, or None if failed

**Example:**
```python
highlight_id = engine.highlight_text_range(
    text_start=100, 
    text_end=200, 
    highlight_type='active_issue',
    page=1
)
```

##### `highlight_area(page_number, bbox, search_text=None, highlight_type='issue')`
Create an area-based highlight on a specific page.

**Parameters:**
- `page_number` (int): Page number (1-based)
- `bbox` (list): Bounding box coordinates [x0, y0, x1, y1]
- `search_text` (str, optional): Associated text for precise location
- `highlight_type` (str): Type of highlight

**Returns:**
- `str`: Unique highlight ID, or None if failed

**Example:**
```python
highlight_id = engine.highlight_area(
    page_number=2,
    bbox=[150, 300, 450, 320],
    search_text="specific error text",
    highlight_type="active_issue"
)
```

##### `remove_highlight(highlight_id)`
Remove a specific highlight.

**Parameters:**
- `highlight_id` (str): Highlight ID to remove

**Returns:**
- `bool`: True if successfully removed

##### `clear_all_highlights()`
Remove all active highlights.

**Returns:**
- `bool`: True if successfully cleared

##### `sync_cursor_position(text_position)`
Synchronize cursor position between text and PDF.

**Parameters:**
- `text_position` (int): Text cursor position

**Returns:**
- None

##### `get_statistics()`
Get highlighting engine statistics.

**Returns:**
- `dict`: Statistics including active highlights, performance metrics

**Example:**
```python
stats = engine.get_statistics()
print(f"Active highlights: {stats['active_highlights']}")
print(f"Current page: {stats['current_page']}")
```

##### `run_accuracy_tests()`
Run comprehensive accuracy tests on the highlighting system.

**Returns:**
- `dict`: Test results with accuracy metrics and performance data

### CoordinateMapper

#### Class: `CoordinateMapper`

Handles precise coordinate conversion between text positions and PDF coordinates.

##### `map_text_to_pdf(text_start, text_end, page)`
Convert text selection to PDF coordinates.

**Parameters:**
- `text_start` (int): Starting text position
- `text_end` (int): Ending text position  
- `page` (int): Page number (1-based)

**Returns:**
- `list`: List of coordinate dictionaries with multi-box support

**Example:**
```python
mapper = CoordinateMapper()
boxes = mapper.map_text_to_pdf(text_start=100, text_end=200, page=1)
for box in boxes:
    print(f"Box: x={box['x']}, y={box['y']}, w={box['width']}, h={box['height']}")
```

##### `map_pdf_to_text(pdf_coords, page)`
Convert PDF coordinates to text position.

**Parameters:**
- `pdf_coords` (dict): PDF coordinates {'x': x, 'y': y}
- `page` (int): Page number (1-based)

**Returns:**
- `int`: Text position, or None if conversion failed

##### `get_character_info(text_position)`
Get detailed character coordinate information.

**Parameters:**
- `text_position` (int): Text position

**Returns:**
- `dict`: Character information including coordinates, font size, bbox

### MultiBoxRenderer

#### Class: `MultiBoxRenderer`

Renders complex highlighting using multiple boxes for line wraps and formatting.

##### `render_text_highlight(text_widget, text_start, text_end, highlight_type='active_highlight')`
Render highlighting in text widget.

**Parameters:**
- `text_widget` (QTextEdit): Text widget to highlight
- `text_start` (int): Starting position
- `text_end` (int): Ending position
- `highlight_type` (str): Highlight type

**Returns:**
- `bool`: True if successfully rendered

##### `render_pdf_highlight(pdf_viewer, boxes, page, highlight_type='active_highlight')`
Render highlighting in PDF viewer with multiple boxes.

**Parameters:**
- `pdf_viewer`: PDF viewer widget
- `boxes` (list): List of coordinate boxes
- `page` (int): Page number
- `highlight_type` (str): Highlight type

**Returns:**
- `bool`: True if successfully rendered

##### `apply_highlights_to_pixmap(pixmap, highlights, zoom_factor)`
Apply highlights directly to a pixmap for custom rendering.

**Parameters:**
- `pixmap` (QPixmap): Pixmap to draw on
- `highlights` (dict): Highlight information
- `zoom_factor` (float): Current zoom level

**Returns:**
- `QPixmap`: Modified pixmap with highlights applied

## Page Validation API

### PageValidationWidget

#### Class: `PageValidationWidget`

Enhanced page-by-page validation widget with precise error highlighting.

```python
class PageValidationWidget(QWidget):
    # Signals
    highlight_pdf_location = pyqtSignal(int, object, str, str)  # page, bbox, text, type
    log_message = pyqtSignal(str)  # message
    highlight_pdf_text_selection = pyqtSignal(int, object)  # page, bbox
    cursor_pdf_location = pyqtSignal(int, object)  # page, bbox
    navigate_pdf_page = pyqtSignal(int)  # page
```

##### `load_document_for_validation(document, post_processing_result=None)`
Load a document for validation with corrections.

**Parameters:**
- `document` (Document): Document object with metadata
- `post_processing_result` (optional): Processing results with corrections

**Returns:**
- None

**Example:**
```python
widget = PageValidationWidget(settings)
widget.load_document_for_validation(document, processing_result)
```

##### `handle_page_change(page_number)`
Handle page change events from PDF viewer.

**Parameters:**
- `page_number` (int): New page number (1-based)

**Returns:**
- None

##### `navigate_to_issue(issue_index)`
Navigate to a specific validation issue.

**Parameters:**
- `issue_index` (int): Index of issue to navigate to

**Returns:**
- None

##### `approve_correction(correction_id)`
Approve a specific correction.

**Parameters:**
- `correction_id` (str): Correction ID to approve

**Returns:**
- `bool`: True if successfully approved

##### `reject_correction(correction_id)`
Reject a specific correction.

**Parameters:**
- `correction_id` (str): Correction ID to reject

**Returns:**
- `bool`: True if successfully rejected

##### `get_validation_status()`
Get current validation status and statistics.

**Returns:**
- `dict`: Validation status with counts and progress

**Example:**
```python
status = widget.get_validation_status()
print(f"Total corrections: {status['total_corrections']}")
print(f"Approved: {status['approved']}")
print(f"Rejected: {status['rejected']}")
```

## Manual Validation API

### ManualValidationWidget

#### Class: `ManualValidationWidget`

Enhanced manual validation widget with drag-to-select area functionality.

##### `load_document(document, file_path)`
Load a document for manual validation.

**Parameters:**
- `document` (Document): Document object
- `file_path` (str): Path to document file

**Returns:**
- None

##### `complete_validation()`
Complete manual validation and return results.

**Returns:**
- `dict`: Validation results with selected areas and metadata

**Example:**
```python
widget = ManualValidationWidget(settings)
widget.load_document(document, "/path/to/document.pdf")

# User makes selections...

results = widget.complete_validation()
print(f"Selected {results['total_selections']} areas")
```

##### `add_area_selection(area_data)`
Programmatically add an area selection.

**Parameters:**
- `area_data` (dict): Area information with type, bbox, page

**Returns:**
- `str`: Area ID

##### `remove_area_selection(area_id)`
Remove a specific area selection.

**Parameters:**
- `area_id` (str): Area ID to remove

**Returns:**
- `bool`: True if successfully removed

##### `get_all_selections()`
Get all current area selections.

**Returns:**
- `dict`: All selections organized by page

##### `load_existing_areas_from_project(visual_areas)`
Load existing area selections from project data.

**Parameters:**
- `visual_areas` (dict): Visual areas data from project

**Returns:**
- None

### AreaType Enumeration

```python
from enum import Enum

class AreaType(Enum):
    IMAGE = "IMAGE"
    TABLE = "TABLE"
    DIAGRAM = "DIAGRAM"
    HEADER = "HEADER"
    FOOTER = "FOOTER"
    SIDEBAR = "SIDEBAR"
    ANNOTATION = "ANNOTATION"
    WATERMARK = "WATERMARK"
```

## Document State Management API

### DocumentStateManager

#### Class: `DocumentStateManager`

Manages document state across the application with multi-document support.

##### `load_project_documents(documents)`
Load multiple documents into state management.

**Parameters:**
- `documents` (list): List of document dictionaries

**Returns:**
- None

##### `set_active_document(document_id, metadata)`
Set the currently active document.

**Parameters:**
- `document_id` (str): Document identifier
- `metadata` (dict): Document metadata

**Returns:**
- None

##### `get_active_document()`
Get the currently active document.

**Returns:**
- `tuple`: (document_id, metadata) or (None, None)

##### `save_validation_result(document_id, validation_result)`
Save validation results for a document.

**Parameters:**
- `document_id` (str): Document identifier
- `validation_result` (dict): Validation results

**Returns:**
- None

##### `get_document_state(document_id)`
Get complete state information for a document.

**Parameters:**
- `document_id` (str): Document identifier

**Returns:**
- `dict`: Document state including progress, selections, corrections

## Area Storage Management API

### AreaStorageManager

#### Class: `AreaStorageManager`

Manages persistent storage of visual area selections.

##### `save_area(document_id, area)`
Save an area selection for a document.

**Parameters:**
- `document_id` (str): Document identifier
- `area` (VisualArea): Area object to save

**Returns:**
- `str`: Area ID

##### `load_areas(document_id)`
Load all areas for a specific document.

**Parameters:**
- `document_id` (str): Document identifier

**Returns:**
- `dict`: Dictionary mapping area IDs to VisualArea objects

##### `remove_area(document_id, area_id)`
Remove a specific area.

**Parameters:**
- `document_id` (str): Document identifier
- `area_id` (str): Area ID to remove

**Returns:**
- `bool`: True if successfully removed

##### `get_areas_for_page(document_id, page_number)`
Get all areas for a specific page.

**Parameters:**
- `document_id` (str): Document identifier
- `page_number` (int): Page number (1-based)

**Returns:**
- `list`: List of VisualArea objects

### VisualArea

#### Class: `VisualArea`

Represents a visual area selection with metadata.

```python
@dataclass
class VisualArea:
    id: str
    document_id: str
    page: int
    type: AreaType
    bbox: list  # [x0, y0, x1, y1]
    name: str
    description: str = ""
    created_at: str = ""
    confidence: float = 1.0
    
    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        
    @classmethod
    def from_dict(cls, data: dict) -> 'VisualArea':
        """Create from dictionary format."""
```

## Session Recovery API

### Session Recovery Functions

#### `get_session_state()`
Get current session state information.

**Returns:**
- `dict`: Session state including active project, documents, configuration

**Example:**
```python
from tore_matrix_labs.core.session_recovery import get_session_state

state = get_session_state()
print(f"Active project: {state['active_project']}")
print(f"Document count: {state['document_count']}")
```

#### `restore_session_state(state=None)`
Restore session state from saved data.

**Parameters:**
- `state` (dict, optional): State to restore, or None to restore from file

**Returns:**
- `bool`: True if successfully restored

#### `save_session_state(state)`
Save current session state.

**Parameters:**
- `state` (dict): State to save

**Returns:**
- `bool`: True if successfully saved

#### `check_session_health()`
Check the health of the current session.

**Returns:**
- `dict`: Health status with diagnostics

**Example:**
```python
from tore_matrix_labs.core.session_recovery import check_session_health

health = check_session_health()
print(f"Session healthy: {health['healthy']}")
print(f"Issues found: {health['issues']}")
```

## Error Handling

### Exception Classes

#### `HighlightingError`
Raised when highlighting operations fail.

```python
class HighlightingError(Exception):
    """Exception raised for highlighting system errors."""
    pass
```

#### `CoordinateMappingError`
Raised when coordinate mapping fails.

```python
class CoordinateMappingError(Exception):
    """Exception raised for coordinate mapping errors."""
    pass
```

#### `ValidationError`
Raised when validation operations fail.

```python
class ValidationError(Exception):
    """Exception raised for validation errors."""
    pass
```

### Error Handling Examples

```python
try:
    highlight_id = engine.highlight_text_range(100, 200)
    if not highlight_id:
        raise HighlightingError("Failed to create highlight")
except HighlightingError as e:
    logger.error(f"Highlighting failed: {e}")
    # Handle error appropriately

try:
    boxes = mapper.map_text_to_pdf(100, 200, page=1)
    if not boxes:
        raise CoordinateMappingError("No coordinates found for text range")
except CoordinateMappingError as e:
    logger.error(f"Coordinate mapping failed: {e}")
    # Fallback to approximate coordinates
```

## Performance Considerations

### Memory Management

```python
# Efficient highlighting for large documents
engine.disable_highlighting()  # Temporarily disable during batch operations

# Process large amount of data
for item in large_dataset:
    process_item(item)

engine.enable_highlighting()   # Re-enable when needed

# Clear memory when switching documents
engine.clear_all_highlights()
engine.coordinate_mapper.clear_cache()
```

### Batch Operations

```python
# Efficient batch highlighting
highlights_to_create = [
    (100, 150, 'issue'),
    (200, 250, 'issue'), 
    (300, 350, 'issue')
]

# Disable rendering during batch creation
engine.multi_box_renderer.disable_rendering()

highlight_ids = []
for start, end, type_ in highlights_to_create:
    highlight_id = engine.highlight_text_range(start, end, type_)
    if highlight_id:
        highlight_ids.append(highlight_id)

# Re-enable and refresh display
engine.multi_box_renderer.enable_rendering()
engine.update_display()
```

## Integration Examples

### Custom Validation Workflow

```python
class CustomValidationWidget(QWidget):
    def __init__(self):
        super().__init__()
        
        # Initialize components
        self.highlighting_engine = HighlightingEngine()
        self.area_storage = AreaStorageManager()
        self.document_state = DocumentStateManager()
        
        # Connect signals
        self.setup_connections()
    
    def setup_connections(self):
        """Set up signal connections."""
        self.highlighting_engine.highlight_activated.connect(
            self.on_highlight_activated
        )
    
    def process_document_with_validation(self, document_path):
        """Complete document processing with validation."""
        
        # Load document
        document = self.load_document(document_path)
        
        # Manual validation phase
        manual_results = self.run_manual_validation(document)
        
        # Process with exclusions
        processing_results = self.process_with_exclusions(
            document, manual_results['selections']
        )
        
        # QA validation phase
        qa_results = self.run_qa_validation(
            document, processing_results
        )
        
        return {
            'document': document,
            'manual_validation': manual_results,
            'processing': processing_results,
            'qa_validation': qa_results
        }
```

### Multi-Document Project Manager

```python
class ProjectManager:
    def __init__(self):
        self.documents = {}
        self.document_state = DocumentStateManager()
        self.area_storage = AreaStorageManager()
    
    def add_document(self, document_path):
        """Add document to project."""
        document_id = self.generate_document_id(document_path)
        
        # Load document
        document = Document.from_file(document_path)
        self.documents[document_id] = document
        
        # Initialize state
        self.document_state.set_active_document(
            document_id, document.metadata
        )
        
        return document_id
    
    def process_all_documents(self):
        """Process all documents in the project."""
        for document_id, document in self.documents.items():
            try:
                # Set as active
                self.document_state.set_active_document(
                    document_id, document.metadata
                )
                
                # Process document
                results = self.process_single_document(document)
                
                # Save results
                self.save_document_results(document_id, results)
                
            except Exception as e:
                logger.error(f"Failed to process {document_id}: {e}")
                continue
    
    def export_project(self, format='jsonl', output_path=None):
        """Export all processed documents."""
        exported_data = []
        
        for document_id, document in self.documents.items():
            # Get processing results
            state = self.document_state.get_document_state(document_id)
            
            if state and state.get('processed'):
                export_item = {
                    'document_id': document_id,
                    'content': state['extracted_content'],
                    'metadata': document.metadata,
                    'quality_metrics': state['quality_metrics']
                }
                exported_data.append(export_item)
        
        # Write to file
        if format == 'jsonl':
            self.write_jsonl(exported_data, output_path)
        elif format == 'json':
            self.write_json(exported_data, output_path)
        
        return len(exported_data)
```

## Version Compatibility

### API Versioning

The API follows semantic versioning:
- **Major Version**: Breaking changes
- **Minor Version**: New features, backward compatible
- **Patch Version**: Bug fixes, backward compatible

### Backward Compatibility

```python
# Check API version
from tore_matrix_labs import __version__, api_version

print(f"Library version: {__version__}")
print(f"API version: {api_version}")

# Version-specific feature detection
if api_version >= "2.0.0":
    # Use new highlighting system
    engine = HighlightingEngine()
else:
    # Fall back to legacy highlighting
    engine = LegacyHighlighter()
```

### Migration Guide

When upgrading from v1.x to v2.x:

1. **Update imports**: New highlighting system imports
2. **Replace methods**: Legacy highlighting methods deprecated
3. **Update configurations**: New configuration options available
4. **Test thoroughly**: Run compatibility tests

---

For the most up-to-date API documentation, visit our [GitHub repository](https://github.com/insult0o/tore-matrix-labs) or check the inline documentation in your IDE.