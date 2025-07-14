# TORE Matrix Labs V3 - Complete System Design Document

## Table of Contents
1. [System Overview and Goals](#1-system-overview-and-goals)
2. [Document Ingestion and Supported Formats](#2-document-ingestion-and-supported-formats)
3. [Unstructured Integration and Element Parsing](#3-unstructured-integration-and-element-parsing)
4. [Internal Data and Metadata Model](#4-internal-data-and-metadata-model)
5. [Project Structure and State Management](#5-project-structure-and-state-management)
6. [GUI Design for Document Review](#6-gui-design-for-document-review)
7. [Element Navigation and Page Sync](#7-element-navigation-and-page-sync)
8. [Manual Editing and Annotation Interface](#8-manual-editing-and-annotation-interface)
9. [Metadata Editing and Structural Corrections](#9-metadata-editing-and-structural-corrections)
10. [Table and Image Review Tools](#10-table-and-image-review-tools)
11. [Signals, Events, and Interaction Flow](#11-signals-events-and-interaction-flow)
12. [Saving and Exporting (RAG JSON and Fine-tune Text)](#12-saving-and-exporting-rag-json-and-fine-tune-text)
13. [Extensibility and Modular Agent Architecture](#13-extensibility-and-modular-agent-architecture)

## 1. System Overview and Goals

### Primary Objectives
The TORE Matrix Labs V3 document processing system is designed to:

1. **Unified Document Ingestion**: Create projects and upload diverse document formats (PDFs, Word docs, HTML, emails, images, etc.) using Unstructured.io library
2. **Automated Content & Metadata Extraction**: Extract all textual content and metadata (hierarchy, page numbers, coordinates) into a uniform representation
3. **Human Verification and Editing**: Provide visual review interface for inspecting and correcting extracted elements
4. **Structure & Layout Preservation**: Store text, structural information, element types, hierarchical relationships, and layout coordinates
5. **LLM-Ready Export**: Export verified content in formats suitable for RAG (JSON) and fine-tuning (text)

### Technology Stack
- **Backend**: Python with FastAPI/Flask, Unstructured library
- **Frontend**: React/Vue with TypeScript
- **Document Viewing**: PDF.js for PDFs, custom viewers for other formats
- **Storage**: Multi-backend support (SQLite default, PostgreSQL, MongoDB)
- **Communication**: RESTful API with WebSocket for real-time updates

### User Workflow
1. Create/open project
2. Upload documents
3. System processes with Unstructured
4. Review extracted elements with visual interface
5. Make corrections (edit text, adjust types, modify structure)
6. Save project state
7. Export to RAG JSON or fine-tuning text

## 2. Document Ingestion and Supported Formats

### 2.1 Supported File Types
- **PDF files** (.pdf): Scanned or digital PDFs
- **Microsoft Office**: Word (.docx, .doc), Excel (.xlsx, .xls), PowerPoint (.pptx, .ppt)
- **OpenOffice/LibreOffice**: ODT, ODS, ODP
- **Web formats**: HTML, XML, Markdown (.md)
- **Plain text**: TXT, LOG, code files
- **Emails**: EML, MSG with attachments
- **Images**: PNG, JPG, JPEG, TIFF, BMP, HEIC (with OCR)
- **Other**: CSV, TSV, RTF, EPUB

### 2.2 Upload Interface
- Multi-file selection with drag-and-drop
- Progress indicators for each file
- Size limits and warnings for large files
- Batch processing support

### 2.3 Processing Pipeline
```python
def ingest_document(file_path):
    # Auto-detect file type
    elements = partition(filename=file_path, 
                        unique_element_ids=True,
                        strategy="hi_res",
                        extract_image_block_types=["Image", "Table"],
                        extract_image_block_to_payload=True)
    return process_elements(elements)
```

## 3. Unstructured Integration and Element Parsing

### 3.1 Element Structure
Each element contains:
- **type**: Semantic category (Title, NarrativeText, Table, Image, etc.)
- **element_id**: Unique identifier (UUID)
- **text**: Extracted text content
- **metadata**: Comprehensive metadata object

### 3.2 Metadata Fields
```python
{
    "page_number": 1,
    "coordinates": {
        "points": [[x1,y1], [x2,y2], [x3,y3], [x4,y4]],
        "bbox": [x_min, y_min, x_max, y_max]
    },
    "parent_id": "parent_element_id",
    "category_depth": 0,
    "detection_class_prob": 0.95,
    "languages": ["en"],
    "filename": "document.pdf",
    "filetype": "application/pdf",
    "text_as_html": "<table>...</table>",  # For tables
    "image_base64": "...",  # For images
    "image_path": "path/to/image.png"
}
```

### 3.3 Element Types
- **Text**: Title, NarrativeText, Header, Footer, PageNumber
- **Lists**: ListItem, UncategorizedText
- **Structured**: Table, Formula, CodeSnippet
- **Media**: Image, FigureCaption
- **Contact**: Address, EmailAddress
- **Layout**: PageBreak

## 4. Internal Data and Metadata Model

### 4.1 Data Model Hierarchy
```
Project
├── Documents[]
│   ├── id: string
│   ├── filename: string
│   ├── elements: Element[]
│   └── metadata: DocumentMetadata
└── settings: ProjectSettings
```

### 4.2 Element Model
```python
@dataclass
class UnifiedElement:
    id: str
    type: ElementType
    text: str
    metadata: Dict[str, Any]
    children: List[str] = field(default_factory=list)
    is_verified: bool = False
    is_edited: bool = False
    edit_history: List[Edit] = field(default_factory=list)
```

### 4.3 Hierarchical Structure
- Elements linked via parent_id
- Children lists computed for navigation
- Category depth for nesting levels
- Maintain reading order within hierarchy

## 5. Project Structure and State Management

### 5.1 Project Lifecycle
- **New**: Initialize empty project
- **Open**: Load from .tore file
- **Save**: Serialize to JSON/.tore format
- **Autosave**: Periodic saves with dirty tracking

### 5.2 State Management
- Backend maintains authoritative state
- Frontend requests/updates via API
- Dirty flag tracking for unsaved changes
- Change history for audit trail

### 5.3 Multi-Document Support
- Switch between documents in UI
- Maintain separate element lists
- Cross-document operations (future)

## 6. GUI Design for Document Review

### 6.1 Layout Structure
```
┌─────────────────────────────────────────────────────┐
│                   Main Toolbar                       │
├─────────────────────┬───────────────────────────────┤
│                     │                               │
│   Element List      │    Document Viewer           │
│   (Hierarchical)    │    (PDF/Image View)          │
│                     │                               │
├─────────────────────┴───────────────────────────────┤
│              Properties/Details Panel                │
└─────────────────────────────────────────────────────┘
```

### 6.2 Element List Features
- Hierarchical tree view with expand/collapse
- Type icons and color coding
- Text snippets for preview
- Search and filter capabilities
- Inline editing support

### 6.3 Document Viewer
- PDF.js integration for PDFs
- Image display for scanned documents
- Highlight overlays for elements
- Zoom and pan controls
- Selection tools (arrow, hand, zoom, mask, draw)

## 7. Element Navigation and Page Sync

### 7.1 Bidirectional Synchronization
- **List → Viewer**: Click element to highlight on page
- **Viewer → List**: Click highlight to select in list
- Smooth scrolling and transitions
- Page number indicators

### 7.2 Coordinate Mapping
```javascript
function mapCoordinates(element, viewerScale) {
    const scaled = {
        x: element.coordinates.bbox[0] * viewerScale,
        y: element.coordinates.bbox[1] * viewerScale,
        width: (element.coordinates.bbox[2] - element.coordinates.bbox[0]) * viewerScale,
        height: (element.coordinates.bbox[3] - element.coordinates.bbox[1]) * viewerScale
    };
    return scaled;
}
```

## 8. Manual Editing and Annotation Interface

### 8.1 Text Editing
- Double-click or F2 to edit
- Inline textarea for multi-line
- Spell check support
- Original text preservation

### 8.2 Element Operations
- **Add**: Draw region, select type, OCR/manual input
- **Delete**: Remove with confirmation
- **Merge**: Combine adjacent elements
- **Split**: Divide at cursor position
- **Reorder**: Drag-and-drop or move buttons

### 8.3 Type Changes
- Dropdown for element type selection
- Automatic hierarchy adjustments
- Validation for compatible types

## 9. Metadata Editing and Structural Corrections

### 9.1 Hierarchy Management
- Indent/outdent for nesting
- Drag-and-drop reparenting
- Section creation from titles
- List organization

### 9.2 Coordinate Adjustments
- Resize highlight boxes
- Drag to reposition
- Numerical input for precision

### 9.3 Structural Validation
- Warn about orphaned elements
- Suggest logical groupings
- Maintain reading order

## 10. Table and Image Review Tools

### 10.1 Table Editor
```html
<table-editor>
  <table contenteditable>
    <tr><th>Header 1</th><th>Header 2</th></tr>
    <tr><td>Cell 1</td><td>Cell 2</td></tr>
  </table>
  <button onclick="saveTable()">Save</button>
</table-editor>
```

### 10.2 Image Tools
- Preview with lightbox
- Caption/description editing
- Alt text for accessibility
- OCR for text in images

## 11. Signals, Events, and Interaction Flow

### 11.1 Event Types
```javascript
// Selection events
onElementSelected(elementId)
onViewerRegionClicked(coordinates)

// Edit events
onTextChanged(elementId, newText)
onTypeChanged(elementId, newType)
onStructureChanged(elementId, newParent)

// Document events
onDocumentLoaded(documentId)
onPageChanged(pageNumber)
```

### 11.2 API Endpoints
- `POST /api/projects` - Create project
- `GET /api/projects/:id` - Load project
- `POST /api/documents/upload` - Upload document
- `PATCH /api/elements/:id` - Update element
- `DELETE /api/elements/:id` - Delete element
- `POST /api/elements` - Add element
- `GET /api/export/:format` - Export project

## 12. Saving and Exporting

### 12.1 RAG JSON Format
```json
[
  {
    "id": "chunk-001",
    "text": "The company achieved 20% growth...",
    "metadata": {
      "source": "report.pdf",
      "page": 2,
      "section": "Executive Summary",
      "type": "NarrativeText",
      "confidence": 0.95
    }
  }
]
```

### 12.2 Fine-tuning Text Format
```markdown
# Document: Annual Report 2023

## Executive Summary

The company achieved 20% growth...

### Financial Highlights

| Quarter | Revenue | Growth |
|---------|---------|--------|
| Q1      | $10M    | 15%    |
| Q2      | $12M    | 20%    |

**Figure 1:** Revenue trends chart
```

## 13. Extensibility and Modular Agent Architecture

### 13.1 Module Structure
- **Core**: Data models, business logic
- **UI**: React components, state management
- **Integration**: Unstructured, export formats
- **Storage**: Multi-backend repositories

### 13.2 Extension Points
- Custom element types
- New export formats
- Additional OCR engines
- LLM integration hooks
- Plugin architecture

### 13.3 Agent Development
- Clear module boundaries
- Well-defined APIs
- Comprehensive logging
- Test coverage requirements