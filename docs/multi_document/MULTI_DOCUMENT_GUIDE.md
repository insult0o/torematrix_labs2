# Multi-Document Support User Guide

## Overview

TORE Matrix Labs provides comprehensive multi-document support with session continuity, allowing you to work with multiple documents simultaneously while maintaining state across sessions. This guide covers the complete workflow for managing multiple documents efficiently.

## Key Features

### ✅ Multi-Document Workflow
- **Batch Processing**: Process multiple documents in a single session
- **Session Continuity**: Resume work exactly where you left off
- **State Preservation**: Document progress and selections maintained
- **Project-Based Management**: Organize documents into coherent projects

### ✅ Enhanced Project Management
- **Auto-Loading**: Previously processed documents load automatically
- **Smart Navigation**: Jump between documents seamlessly
- **Progress Tracking**: Visual indicators for document completion status
- **Version Control**: Git integration with automatic commits

## Getting Started

### 1. Create a New Project

```bash
# Launch application
./scripts/project_operations.sh run

# Or directly
python main.py
```

1. Click **"New Project"** or press `Ctrl+N`
2. Enter project name (e.g., "ICAO Manual Processing")
3. Optionally add project description
4. Click **"Create"**

### 2. Import Multiple Documents

#### Method 1: Batch Import
1. Go to **"Ingestion"** tab
2. Click **"Add Files"** 
3. Select multiple PDF files (Ctrl+Click or Shift+Click)
4. Documents appear in the ingestion list

#### Method 2: Drag & Drop
1. Open file manager with PDF files
2. Select multiple files
3. Drag and drop onto the ingestion area
4. Files are automatically added to the project

#### Method 3: Directory Import
1. Click **"Add Folder"**
2. Select directory containing PDFs
3. All PDFs in the directory are imported
4. Subdirectories can be included optionally

### 3. Document Processing Workflow

#### Phase 1: Manual Validation (Required for each document)
1. **Select Document**: Click on document in ingestion list
2. **Review Content**: Document loads in PDF viewer (right panel)
3. **Mark Special Areas**:
   - **Images**: Drag to select charts, diagrams, photos
   - **Tables**: Select tabular data structures
   - **Diagrams**: Mark technical drawings, flowcharts
   - **Headers/Footers**: Select page headers and footers
4. **Save Selections**: Click **"Save Areas"** or `Ctrl+S`
5. **Complete Validation**: Click **"Complete Manual Validation"**

#### Phase 2: Automated Processing
1. **Text Extraction**: System processes text excluding marked areas
2. **Quality Analysis**: OCR errors and formatting issues detected
3. **Data Structure**: Content organized into structured format
4. **Project Update**: Document added to project with processing results

#### Phase 3: QA Validation
1. **Error Review**: Switch to **"QA Validation"** tab
2. **Page Navigation**: Use page controls to review each page
3. **Error Highlighting**: Issues highlighted in both text and PDF
4. **Make Corrections**: Edit text directly in the correction area
5. **Approve/Reject**: Mark corrections as approved or rejected

## Working with Multiple Documents

### Document Status Indicators

#### Ingestion Tab Status
- 🔴 **Not Started**: Document not yet processed
- 🟡 **In Progress**: Currently being processed
- 🔵 **Manual Validation**: Ready for manual area selection
- 🟢 **Processed**: Text extraction completed
- ✅ **Validated**: QA validation completed

#### Project Manager Status
- **Added**: Document imported but not processed
- **In Validation**: Manual validation in progress
- **Processed**: Text extraction completed
- **Validated**: QA validation completed
- **Exported**: Ready for export or already exported

### Navigation Between Documents

#### Quick Document Switching
1. **Project Tree**: Click any document in the project manager
2. **Tab History**: Use browser-like navigation (Alt+Left/Right)
3. **Search**: Find documents by name or content
4. **Recent Documents**: Access recently viewed documents

#### Smart Loading
- **Auto-Resume**: System automatically loads the last document you were working on
- **State Preservation**: Manual selections and corrections are preserved
- **Progress Tracking**: Visual indicators show completion status

### Batch Operations

#### Process Multiple Documents
```bash
# Process all documents in ingestion queue
1. Select multiple documents (Ctrl+Click)
2. Click "Process Selected" 
3. Documents process in sequence
4. Progress shown in status bar
```

#### Batch Export
```bash
# Export all validated documents
1. Go to "Project Management" tab
2. Click "Export All"
3. Choose export format (JSON, JSONL, CSV)
4. Select output directory
5. All processed documents exported together
```

## Session Continuity Features

### Automatic State Saving
- **Document Progress**: Manual selections automatically saved
- **Session State**: Current document and tab position remembered
- **Project Configuration**: Settings and preferences preserved
- **Git Integration**: Changes automatically committed with descriptive messages

### Session Recovery
```bash
# Quick session recovery
./scripts/session_recovery.sh summary    # Show current state
./scripts/session_recovery.sh restore    # Restore configuration
./scripts/session_recovery.sh health     # Check project integrity
```

### Resume Workflow
When reopening TORE Matrix Labs:

1. **Auto-Detection**: System detects existing projects
2. **Smart Loading**: Last project loads automatically
3. **Priority Documents**: Documents with areas or corrections load first
4. **Tab Restoration**: Last active tab is selected
5. **Continue Work**: Resume exactly where you left off

## Advanced Multi-Document Features

### Document Comparison
1. **Load Two Documents**: Open documents in separate tabs
2. **Side-by-Side View**: Use window splitting features
3. **Content Comparison**: Compare extracted text and areas
4. **Quality Metrics**: Compare processing quality scores

### Cross-Document References
- **Link Detection**: System identifies references between documents
- **Navigation Aids**: Click references to jump to related documents
- **Dependency Tracking**: Track document processing dependencies

### Bulk Quality Control
1. **Quality Dashboard**: Overview of all document quality scores
2. **Error Summary**: Aggregate view of common issues across documents
3. **Batch Corrections**: Apply similar corrections to multiple documents
4. **Statistical Analysis**: Quality trends and improvement tracking

## Project Organization

### Folder Structure
```
project_name.tore
├── documents/           # Document metadata and progress
├── extracted_content/   # Processed text and data
├── visual_areas/       # Manual area selections
├── corrections/        # QA validation corrections
├── exports/           # Generated output files
└── metadata/          # Project configuration and logs
```

### Document Metadata
Each document maintains:
- **Processing Status**: Current stage in workflow
- **Quality Metrics**: OCR confidence, extraction accuracy
- **Manual Selections**: Visual areas marked by user
- **Correction History**: QA validation changes
- **Export Status**: Output generation status

### Version Control Integration
```bash
# Git operations for project tracking
./scripts/git_operations.sh status        # Check git status
./scripts/git_operations.sh commit "msg"  # Commit changes
./scripts/git_operations.sh sync "msg"    # Commit and push

# Automatic commits triggered by:
# - Document processing completion
# - Manual validation completion
# - QA validation approval
# - Project export
```

## Best Practices

### Efficient Multi-Document Processing

1. **Batch Import**: Import all documents at the beginning
2. **Consistent Naming**: Use descriptive document names
3. **Quality First**: Complete manual validation thoroughly
4. **Regular Saves**: Save progress frequently during manual validation
5. **Review in Batches**: Group similar documents for QA validation

### Performance Optimization

#### For Large Document Sets
- **Process in Chunks**: Work with 10-20 documents at a time
- **Memory Management**: Close unused documents when working with many files
- **Storage Optimization**: Use SSD storage for better performance
- **Network Considerations**: Keep projects on local storage during processing

#### Resource Management
```bash
# Monitor system resources
./scripts/project_operations.sh status

# Optimize performance
- Close other applications during processing
- Ensure adequate RAM (8GB+ recommended for large projects)
- Use fast storage (SSD preferred)
```

### Quality Assurance Workflow

#### Document Review Strategy
1. **First Pass**: Quick review for obvious errors
2. **Detailed Review**: Page-by-page validation
3. **Cross-Reference**: Check consistency across documents
4. **Final Approval**: Mark documents as validated

#### Error Management
- **Common Issues**: Create templates for frequent corrections
- **Error Categories**: Group similar errors for batch processing
- **Quality Metrics**: Track improvement over time
- **Validation Rules**: Develop consistency guidelines

## Troubleshooting

### Common Issues

#### "Project Won't Load"
```bash
# Check project integrity
./scripts/session_recovery.sh health

# Restore project configuration
./scripts/session_recovery.sh restore

# Check git status
./scripts/git_operations.sh status
```

#### "Documents Not Loading"
1. **Check File Paths**: Ensure PDF files still exist at original locations
2. **File Permissions**: Verify read access to document files
3. **Project Corruption**: Use session recovery to restore state
4. **Memory Issues**: Close other applications to free up RAM

#### "Manual Selections Lost"
1. **Auto-Save**: Check if auto-save is enabled in settings
2. **Project Save**: Manually save project with `Ctrl+S`
3. **Backup Recovery**: Use git history to recover previous state
4. **Re-Selection**: Re-do manual validation if necessary

### Performance Issues

#### Slow Processing
- **Reduce Batch Size**: Process fewer documents simultaneously
- **Check Resources**: Monitor CPU and memory usage
- **Storage Speed**: Move project to faster storage
- **Network Issues**: Ensure stable file access

#### Memory Problems
- **Close Documents**: Close unused document viewers
- **Restart Application**: Fresh start can free up memory
- **System Resources**: Check available RAM
- **Large Files**: Split very large documents if possible

### Recovery Procedures

#### Project Recovery
```bash
# Complete project recovery workflow
1. ./scripts/session_recovery.sh summary     # Assess situation
2. ./scripts/session_recovery.sh restore     # Restore configuration
3. ./scripts/project_operations.sh status    # Check project health
4. ./scripts/git_operations.sh status        # Check version control
```

#### Data Recovery
1. **Git History**: Use git log to find previous working state
2. **Backup Files**: Check for automatic backup files
3. **Manual Reconstruction**: Re-import documents if necessary
4. **Support Contact**: Contact support for complex recovery scenarios

## Integration with Other Systems

### Export Formats for Multi-Document Projects

#### RAG Systems
```json
{
  "project": "project_name",
  "documents": [
    {
      "id": "doc_1",
      "content": "extracted_text",
      "metadata": {
        "quality_score": 0.95,
        "areas_excluded": 5,
        "corrections_applied": 3
      }
    }
  ]
}
```

#### Fine-Tuning Datasets
```jsonl
{"text": "document_content", "source": "doc_1", "quality": 0.95}
{"text": "document_content", "source": "doc_2", "quality": 0.98}
```

#### Data Analytics
```csv
document_id,quality_score,page_count,corrections,areas_excluded,processing_time
doc_1,0.95,25,3,5,45.2
doc_2,0.98,18,1,2,32.1
```

### API Integration
```python
# Python API for multi-document processing
from tore_matrix_labs import ProjectManager, DocumentProcessor

# Load project
project = ProjectManager.load_project("project_name.tore")

# Get all documents
documents = project.get_documents()

# Process specific document
processor = DocumentProcessor()
result = processor.process_document(documents[0])

# Export all processed documents
project.export_all(format="jsonl", output_dir="exports/")
```

## Advanced Features

### Parallel Processing
- **Multi-Threading**: Process multiple documents simultaneously
- **Queue Management**: Smart queueing of processing tasks
- **Resource Allocation**: Automatic distribution of system resources
- **Progress Monitoring**: Real-time status of all processing tasks

### Machine Learning Integration
- **Quality Prediction**: ML models predict document processing quality
- **Error Pattern Recognition**: Automatic detection of common issues
- **Processing Optimization**: AI-driven processing parameter tuning
- **Content Classification**: Automatic document type detection

### Collaboration Features
- **Shared Projects**: Multi-user access to the same project
- **Role-Based Access**: Different permissions for different users
- **Change Tracking**: Full audit trail of all modifications
- **Comments and Notes**: Collaborative annotation features

## Support and Resources

### Documentation
- [Installation Guide](../installation/INSTALLATION.md)
- [User Manual](../user_guide/USER_MANUAL.md)
- [API Reference](../api/API_REFERENCE.md)
- [Troubleshooting](../troubleshooting/TROUBLESHOOTING.md)

### Community
- [GitHub Issues](https://github.com/insult0o/tore-matrix-labs/issues)
- [User Forum](https://forum.tore-matrix-labs.com)
- [Video Tutorials](https://tutorials.tore-matrix-labs.com)

### Professional Support
- Email: support@tore-matrix-labs.com
- Enterprise Support: enterprise@tore-matrix-labs.com
- Training Services: training@tore-matrix-labs.com

---

**Happy Multi-Document Processing! 🚀**

For the latest updates and features, visit our [GitHub repository](https://github.com/insult0o/tore-matrix-labs).