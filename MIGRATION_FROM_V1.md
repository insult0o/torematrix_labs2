# Migration from TORE Matrix Labs V1

## 📍 V1 Project Location
- **Directory**: `/home/insulto/tore_matrix_labs`
- **GitHub**: `https://github.com/insult0o/tore-matrix-labs`
- **Status**: ON HOLD - Development paused in favor of V3

## 🎯 Key Lessons from V1

### Architecture Issues Identified
1. **Complex Signal Chains** - 1,876 lines in main_window.py
2. **Scattered State Management** - State across multiple widgets
3. **Multiple Data Models** - VisualArea, DocumentElement, ExtractedContent
4. **Tight Coupling** - Components heavily dependent on each other
5. **Limited Scalability** - Performance issues with large documents

### Successful Features to Preserve
1. **Manual Validation Workflow** - Area selection and exclusion
2. **Page-by-Page Corrections** - Detailed review interface
3. **Project Persistence** - .tore format for saving work
4. **PDF Integration** - Coordinate mapping and highlighting
5. **Quality Assessment** - Validation and approval workflow

## 🔄 V3 Improvements

### Architecture
- **Event-Driven** instead of signal chains
- **Centralized State** with single source of truth
- **Unified Element Model** replacing multiple models
- **Loose Coupling** with dependency injection
- **Performance Optimized** for 10K+ elements

### Technology
- **PyQt6** instead of PyQt5
- **AsyncIO** for non-blocking operations
- **Type Hints** throughout
- **Modern Python** (3.11+) features
- **Better Testing** from ground up

## 📊 Feature Mapping V1 → V3

| V1 Feature | V3 Implementation | Status |
|------------|-------------------|---------|
| Manual Validation Widget | Modern area selection with unified elements | Planned |
| QA Validation Widget | Page-by-page review with rich rendering | Planned |
| Area Storage Manager | Multi-backend storage system | Planned |
| Enhanced Drag Select | Element interaction manager | Planned |
| Document Processor | Async processing pipeline | Planned |

## 🚀 Migration Path

### For Developers
1. Study V1 architecture in `/tore_matrix_labs`
2. Understand V3 improvements in this document
3. Implement features using V3 patterns
4. Ensure feature parity before deprecating V1

### For Users (Future)
1. Export projects from V1
2. Import into V3 with migration tool
3. Verify data integrity
4. Enjoy improved performance

## 📝 Important V1 Files for Reference

### Core Functionality
- `/tore_matrix_labs/core/document_processor.py` - Processing pipeline
- `/tore_matrix_labs/core/area_storage_manager.py` - Area persistence
- `/tore_matrix_labs/core/unstructured_extractor.py` - Unstructured integration

### UI Components  
- `/tore_matrix_labs/ui/components/enhanced_drag_select.py` - Area selection
- `/tore_matrix_labs/ui/components/page_validation_widget.py` - Corrections UI
- `/tore_matrix_labs/ui/components/manual_validation_widget.py` - Validation workflow

### Models
- `/tore_matrix_labs/models/visual_area_models.py` - Area data structures
- `/tore_matrix_labs/models/document_models.py` - Document structures

## 🔗 V1 Documentation
- Master Issue #80 - Architecture upgrade plan
- Issues #81-#107 - Detailed subtasks
- `/ENHANCED_UNSTRUCTURED_ANALYSIS.md` - Feature requirements
- `/tore_matrix_labs_v2/TORE_V1_VS_V2_ANALYSIS.md` - Architecture analysis

---
*Use V1 as reference, but implement with V3 patterns*