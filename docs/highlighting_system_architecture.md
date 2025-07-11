# Advanced Highlighting System Architecture

## Overview
This document outlines the architecture for TORE Matrix Labs' advanced highlighting system that provides precise, multi-box text highlighting with perfect synchronization between extracted text and PDF display.

## Current Problem
The existing highlighting system has several limitations:
- Single-box highlighting fails for multi-line paragraphs
- Poor color choices (red outline + yellow) reduce readability
- Inaccurate positioning due to coordinate conversion issues
- No automated testing for highlighting accuracy
- Limited support for complex text layouts

## Solution Architecture

### Core Components

#### 1. Highlighting Engine (`HighlightingEngine`)
Central coordinator that manages all highlighting operations.

```python
class HighlightingEngine:
    def __init__(self, pdf_viewer, text_widget):
        self.pdf_viewer = pdf_viewer
        self.text_widget = text_widget
        self.coordinate_mapper = CoordinateMapper()
        self.multi_box_renderer = MultiBoxRenderer()
        self.position_tracker = PositionTracker()
        self.test_harness = HighlightingTestHarness()
```

#### 2. Coordinate Mapper (`CoordinateMapper`)
Handles precise coordinate conversion between text positions and PDF coordinates.

```python
class CoordinateMapper:
    def __init__(self):
        self.character_map = {}  # char_index -> pdf_coordinates
        self.word_boundaries = {}  # word_index -> (start, end) char positions
        self.line_boundaries = {}  # line_index -> (start, end) char positions
        
    def map_text_to_pdf(self, text_start, text_end, page):
        """Convert text selection to PDF coordinates with multi-box support."""
        pass
        
    def map_pdf_to_text(self, pdf_coords, page):
        """Convert PDF coordinates to text positions."""
        pass
```

#### 3. Multi-Box Renderer (`MultiBoxRenderer`)
Renders complex highlighting using multiple boxes for line wraps and formatting.

```python
class MultiBoxRenderer:
    def __init__(self):
        self.highlight_style = HighlightStyle()
        
    def render_text_highlight(self, text_widget, start_pos, end_pos):
        """Render highlighting in text widget with multi-box support."""
        pass
        
    def render_pdf_highlight(self, pdf_viewer, boxes, page):
        """Render highlighting in PDF viewer with multiple boxes."""
        pass
```

#### 4. Position Tracker (`PositionTracker`)
Tracks and synchronizes cursor/selection positions between text and PDF.

```python
class PositionTracker:
    def __init__(self):
        self.active_highlights = {}  # highlight_id -> highlight_info
        self.cursor_sync_enabled = True
        
    def track_cursor_position(self, text_pos):
        """Track cursor position and sync with PDF."""
        pass
        
    def track_selection_change(self, start_pos, end_pos):
        """Track selection changes and sync highlighting."""
        pass
```

#### 5. Highlight Style (`HighlightStyle`)
Defines visual appearance of highlights with improved colors and accessibility.

```python
class HighlightStyle:
    # New color scheme - pure yellow backgrounds, no outlines
    COLORS = {
        'active_highlight': {
            'background': '#FFFF00',  # Pure yellow
            'opacity': 0.7,
            'border': None  # No outline
        },
        'inactive_highlight': {
            'background': '#FFFF88',  # Light yellow
            'opacity': 0.4,
            'border': None
        },
        'cursor_highlight': {
            'background': '#FFD700',  # Gold
            'opacity': 0.8,
            'border': None
        }
    }
```

#### 6. Test Harness (`HighlightingTestHarness`)
Automated testing system for highlighting accuracy.

```python
class HighlightingTestHarness:
    def __init__(self):
        self.test_cases = []
        self.accuracy_metrics = {}
        
    def run_accuracy_tests(self):
        """Run comprehensive accuracy tests."""
        pass
        
    def verify_coordinate_mapping(self, test_data):
        """Verify coordinate mapping accuracy."""
        pass
```

## Implementation Strategy

### Phase 1: Core Infrastructure
1. **CoordinateMapper Implementation**
   - Character-level mapping using PyMuPDF
   - Word and line boundary detection
   - Robust error handling for edge cases

2. **MultiBoxRenderer Foundation**
   - Basic multi-box rendering logic
   - New color scheme implementation
   - Text widget highlighting improvements

### Phase 2: Advanced Features
1. **Position Tracking System**
   - Real-time cursor synchronization
   - Selection change tracking
   - Multi-highlight management

2. **PDF Integration**
   - Enhanced PDF viewer highlighting
   - Multi-page support
   - Zoom-level coordinate adjustment

### Phase 3: Testing & Validation
1. **Automated Test Suite**
   - Coordinate mapping accuracy tests
   - Visual rendering validation
   - Performance benchmarks

2. **Integration Testing**
   - End-to-end highlighting workflows
   - Cross-widget synchronization tests
   - Edge case handling validation

## Technical Implementation Details

### Character-Level Mapping
```python
def build_character_map(self, pdf_page):
    """Build precise character-to-coordinate mapping."""
    # Extract text with character-level coordinates
    text_dict = pdf_page.get_text("dict")
    
    char_map = {}
    char_index = 0
    
    for block in text_dict["blocks"]:
        for line in block["lines"]:
            for span in line["spans"]:
                text = span["text"]
                bbox = span["bbox"]
                
                # Calculate character positions within span
                for i, char in enumerate(text):
                    char_x = bbox[0] + (i / len(text)) * (bbox[2] - bbox[0])
                    char_y = bbox[1]
                    
                    char_map[char_index] = {
                        'x': char_x,
                        'y': char_y,
                        'width': (bbox[2] - bbox[0]) / len(text),
                        'height': bbox[3] - bbox[1],
                        'page': pdf_page.number
                    }
                    char_index += 1
    
    return char_map
```

### Multi-Box Rendering
```python
def render_multiline_highlight(self, text_start, text_end, page):
    """Render highlighting across multiple lines with separate boxes."""
    char_map = self.get_character_map(page)
    
    # Group characters by line
    line_groups = self.group_characters_by_line(char_map, text_start, text_end)
    
    highlight_boxes = []
    for line_chars in line_groups:
        if line_chars:
            # Create box for this line segment
            start_char = line_chars[0]
            end_char = line_chars[-1]
            
            box = {
                'x': start_char['x'],
                'y': start_char['y'],
                'width': end_char['x'] + end_char['width'] - start_char['x'],
                'height': start_char['height'],
                'page': page
            }
            highlight_boxes.append(box)
    
    return highlight_boxes
```

### Test Validation
```python
def test_highlighting_accuracy(self):
    """Test highlighting accuracy with known test cases."""
    test_cases = [
        {
            'text': 'Single line highlight',
            'expected_boxes': 1,
            'tolerance': 2.0  # pixels
        },
        {
            'text': 'Multi-line paragraph\nwith line breaks',
            'expected_boxes': 2,
            'tolerance': 2.0
        },
        {
            'text': 'Complex text with special characters: äöü',
            'expected_boxes': 1,
            'tolerance': 3.0
        }
    ]
    
    for test_case in test_cases:
        result = self.run_highlight_test(test_case)
        assert result.accuracy > 0.95, f"Accuracy too low: {result.accuracy}"
```

## Integration Points

### 1. PDF Viewer Integration
- Enhance `PDFViewer` class to support multi-box highlighting
- Add coordinate transformation methods
- Implement zoom-level adjustments

### 2. Text Widget Integration
- Extend `QTextEdit` highlighting capabilities
- Add precise cursor position tracking
- Implement selection change notifications

### 3. Validation Widget Integration
- Connect highlighting system to validation workflows
- Add error location highlighting
- Implement issue navigation with highlighting

## Performance Considerations

### 1. Coordinate Mapping Cache
- Cache character maps for each page
- Invalidate cache on document changes
- Optimize for large documents

### 2. Rendering Optimization
- Batch highlight operations
- Use efficient drawing primitives
- Minimize redraws

### 3. Memory Management
- Limit active highlight count
- Clean up unused highlights
- Optimize coordinate data structures

## Error Handling & Edge Cases

### 1. Coordinate Conversion Errors
- Handle invalid coordinates gracefully
- Provide fallback highlighting methods
- Log errors for debugging

### 2. Text Extraction Issues
- Handle missing character coordinates
- Deal with non-standard text layouts
- Support right-to-left text

### 3. Multi-Page Documents
- Handle page transitions
- Maintain highlight state across pages
- Support cross-page selections

## Future Enhancements

### 1. Advanced Features
- Annotation system integration
- Collaborative highlighting
- Export/import highlight data

### 2. Performance Improvements
- GPU-accelerated rendering
- Incremental coordinate mapping
- Lazy loading for large documents

### 3. Accessibility
- High contrast mode support
- Screen reader compatibility
- Keyboard navigation

## Implementation Timeline

### Week 1: Core Infrastructure
- Implement CoordinateMapper
- Basic MultiBoxRenderer
- New color scheme

### Week 2: Advanced Features
- Position tracking system
- PDF integration
- Multi-box rendering

### Week 3: Testing & Validation
- Automated test suite
- Integration testing
- Performance optimization

### Week 4: Polish & Documentation
- Bug fixes
- Documentation
- User acceptance testing

## Success Metrics
- **Accuracy**: >95% correct highlighting position
- **Performance**: <100ms highlight rendering time
- **Reliability**: <1% highlighting failures
- **Usability**: User satisfaction >90%