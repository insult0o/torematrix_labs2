# 🔄 TORE Matrix Labs V2 - Complete Architecture Flowchart

## 📊 **System Overview Diagram**

```mermaid
graph TB
    %% Main Entry Point
    MAIN[🚀 main.py<br/>Entry Point] --> GUI{GUI Mode?}
    GUI -->|Yes| APP[📱 QApplication]
    GUI -->|No| CLI[💻 CLI Mode]
    
    %% GUI Application Flow
    APP --> MAIN_WINDOW[🏠 MainWindowV2]
    MAIN_WINDOW --> EVENT_BUS[📡 EventBus]
    MAIN_WINDOW --> STATE_MGR[🗃️ UIStateManager]
    MAIN_WINDOW --> CONTROLLER[🎮 ApplicationController]
    
    %% Core Services initialization
    CONTROLLER --> COORD_SRV[📍 CoordinateMappingService]
    CONTROLLER --> EXTRACT_SRV[📄 TextExtractionService]
    CONTROLLER --> VALID_SRV[✅ ValidationService]
    CONTROLLER --> QUALITY_ENG[⭐ QualityAssessmentEngine]
    CONTROLLER --> DOC_REPO[💾 DocumentRepository]
    CONTROLLER --> MIGRATION_MGR[🔄 MigrationManager]
    CONTROLLER --> DOC_PROCESSOR[⚙️ UnifiedDocumentProcessor]
    
    %% UI Components
    MAIN_WINDOW --> TAB_WIDGET[📑 TabWidget]
    TAB_WIDGET --> IMPORT_TAB[📥 Document Import]
    TAB_WIDGET --> VALIDATION_TAB[✅ Validation View]
    TAB_WIDGET --> PROJECT_TAB[📁 Project Manager]
    TAB_WIDGET --> EXPORT_TAB[📤 Export]
    
    %% Document Viewer
    IMPORT_TAB --> DOC_VIEWER[👁️ DocumentViewerV2]
    VALIDATION_TAB --> UNIFIED_VALID[🔍 UnifiedValidationView]
    PROJECT_TAB --> PROJECT_MGR[📋 ProjectManagerV2]
```

---

## 🎯 **Document Processing Pipeline Flow**

```mermaid
flowchart TD
    %% Document Input
    START([🎬 User Action]) --> LOAD_DOC{Load Document?}
    
    %% Document Loading Branch
    LOAD_DOC -->|File Select| FILE_DIALOG[📂 File Dialog]
    LOAD_DOC -->|.tore File| TORE_LOAD[📋 .tore File Load]
    
    FILE_DIALOG --> VALIDATE_FORMAT{Valid Format?}
    VALIDATE_FORMAT -->|PDF/DOCX/ODT/RTF| CREATE_DOC[📄 Create UnifiedDocument]
    VALIDATE_FORMAT -->|Invalid| ERROR_FORMAT[❌ Format Error]
    
    TORE_LOAD --> MIGRATION_CHECK{Migration Needed?}
    MIGRATION_CHECK -->|V1→V2| MIGRATE[🔄 Migrate Data]
    MIGRATION_CHECK -->|V2| LOAD_EXISTING[📋 Load Existing]
    
    %% Document Creation
    CREATE_DOC --> SET_METADATA[📊 Set Metadata]
    SET_METADATA --> DOC_LOADED[✅ Document Loaded]
    MIGRATE --> DOC_LOADED
    LOAD_EXISTING --> DOC_LOADED
    
    %% Processing Pipeline
    DOC_LOADED --> PROCESS_REQ{Process Request?}
    PROCESS_REQ -->|Yes| EXTRACT_CONTENT[📄 Extract Content]
    PROCESS_REQ -->|No| DISPLAY_DOC[👁️ Display Document]
    
    %% Text Extraction
    EXTRACT_CONTENT --> STRATEGY_SELECT{Extraction Strategy}
    STRATEGY_SELECT -->|PyMuPDF| PYMUPDF[📄 PyMuPDF Extraction]
    STRATEGY_SELECT -->|OCR| OCR_EXTRACT[👁️ OCR Extraction]
    STRATEGY_SELECT -->|Unstructured| UNSTR_EXTRACT[🏗️ Unstructured Extraction]
    
    PYMUPDF --> COORD_MAP[📍 Coordinate Mapping]
    OCR_EXTRACT --> COORD_MAP
    UNSTR_EXTRACT --> COORD_MAP
    
    COORD_MAP --> CONTENT_ANALYSIS[🔍 Content Analysis]
    CONTENT_ANALYSIS --> TABLES[📊 Table Detection]
    CONTENT_ANALYSIS --> IMAGES[🖼️ Image Detection]
    CONTENT_ANALYSIS --> DIAGRAMS[📈 Diagram Detection]
    
    %% Quality Assessment
    TABLES --> QUALITY_ASSESS[⭐ Quality Assessment]
    IMAGES --> QUALITY_ASSESS
    DIAGRAMS --> QUALITY_ASSESS
    
    QUALITY_ASSESS --> QUALITY_SCORE[📊 Quality Score]
    QUALITY_SCORE --> VALIDATION_NEEDED{Validation Needed?}
    
    %% Validation Branch
    VALIDATION_NEEDED -->|Yes| MANUAL_VALIDATION[👤 Manual Validation]
    VALIDATION_NEEDED -->|No| PROCESSING_COMPLETE[✅ Processing Complete]
    
    MANUAL_VALIDATION --> PAGE_VALIDATION[📄 Page-by-Page Validation]
    PAGE_VALIDATION --> ISSUE_DETECTION[🔍 Issue Detection]
    ISSUE_DETECTION --> COORDINATE_HIGHLIGHT[📍 Coordinate Highlighting]
    COORDINATE_HIGHLIGHT --> USER_REVIEW[👤 User Review]
    USER_REVIEW --> APPROVE_REJECT{Approve/Reject?}
    APPROVE_REJECT -->|Approve| VALIDATION_COMPLETE[✅ Validation Complete]
    APPROVE_REJECT -->|Reject| ISSUE_CORRECTION[🔧 Issue Correction]
    ISSUE_CORRECTION --> USER_REVIEW
    
    %% Final Processing
    VALIDATION_COMPLETE --> PROCESSING_COMPLETE
    PROCESSING_COMPLETE --> SAVE_DOC[💾 Save Document]
    SAVE_DOC --> UPDATE_PROJECT[📁 Update Project]
    UPDATE_PROJECT --> EXPORT_READY[📤 Export Ready]
```

---

## 📡 **Event Bus Communication Flow**

```mermaid
sequenceDiagram
    participant UI as 🖥️ UI Components
    participant EB as 📡 EventBus
    participant CTRL as 🎮 Controller
    participant PROC as ⚙️ Processor
    participant REPO as 💾 Repository
    
    %% Document Loading Sequence
    UI->>EB: DOCUMENT_LOADED event
    EB->>CTRL: handle_document_load()
    CTRL->>PROC: load_document()
    PROC->>REPO: save_document()
    REPO-->>PROC: success/failure
    PROC-->>CTRL: document_info
    CTRL->>EB: DOCUMENT_LOADED response
    EB->>UI: update_document_display()
    
    %% Processing Sequence
    UI->>EB: DOCUMENT_PROCESSING_STARTED
    EB->>CTRL: handle_document_processing()
    CTRL->>PROC: process_document()
    PROC->>PROC: extract_content()
    PROC->>PROC: assess_quality()
    PROC->>PROC: validate_document()
    PROC-->>CTRL: processing_result
    CTRL->>EB: DOCUMENT_PROCESSING_COMPLETED
    EB->>UI: update_progress_display()
    
    %% Validation Sequence
    UI->>EB: VALIDATION_STARTED
    EB->>CTRL: handle_validation()
    CTRL->>PROC: perform_validation()
    PROC->>PROC: page_by_page_validation()
    PROC-->>CTRL: validation_results
    CTRL->>EB: VALIDATION_COMPLETED
    EB->>UI: show_validation_results()
    
    %% Project Operations
    UI->>EB: PROJECT_SAVED
    EB->>CTRL: handle_project_save()
    CTRL->>REPO: save_project()
    REPO-->>CTRL: save_path
    CTRL->>EB: PROJECT_SAVED response
    EB->>UI: update_project_status()
```

---

## 🏗️ **Service Architecture & Dependencies**

```mermaid
graph LR
    %% Core Services Layer
    subgraph "🔧 Core Services"
        COORD[📍 CoordinateMappingService]
        EXTRACT[📄 TextExtractionService]
        VALID[✅ ValidationService]
        QUALITY[⭐ QualityAssessmentEngine]
    end
    
    %% Processing Layer
    subgraph "⚙️ Processing Layer"
        DOC_PROC[🔄 UnifiedDocumentProcessor]
        EXTRACT_STRAT[📋 ExtractionStrategies]
        PIPELINE[🏭 Pipeline Orchestrator]
    end
    
    %% Storage Layer
    subgraph "💾 Storage Layer"
        DOC_REPO[📄 DocumentRepository]
        AREA_REPO[🗺️ AreaRepository]
        MIGRATION[🔄 MigrationManager]
        REPO_BASE[🏗️ RepositoryBase]
    end
    
    %% UI Services Layer
    subgraph "🖥️ UI Services"
        EVENT_BUS[📡 EventBus]
        STATE_MGR[🗃️ UIStateManager]
        THEME_MGR[🎨 ThemeManager]
        HIGHLIGHT[🔆 HighlightingService]
    end
    
    %% Data Models
    subgraph "📊 Data Models"
        UNIFIED_DOC[📄 UnifiedDocument]
        UNIFIED_AREA[🗺️ UnifiedArea]
        VALIDATION_STATE[✅ ValidationState]
        PROJECT_MODEL[📁 ProjectModel]
    end
    
    %% Dependencies
    EXTRACT --> COORD
    VALID --> COORD
    VALID --> EXTRACT
    DOC_PROC --> COORD
    DOC_PROC --> EXTRACT
    DOC_PROC --> VALID
    DOC_PROC --> QUALITY
    
    DOC_REPO --> REPO_BASE
    AREA_REPO --> REPO_BASE
    MIGRATION --> DOC_REPO
    
    STATE_MGR --> EVENT_BUS
    HIGHLIGHT --> COORD
```

---

## 🔄 **Complete Function Call Flow**

```mermaid
flowchart TD
    %% Main Application Start
    START([🎬 Application Start]) --> MAIN_INIT[🚀 main.py initialization]
    MAIN_INIT --> CREATE_APP[📱 Create QApplication]
    CREATE_APP --> INIT_SERVICES[🔧 Initialize Services]
    
    %% Service Initialization
    INIT_SERVICES --> EVENT_BUS_INIT[📡 EventBus.__init__()]
    INIT_SERVICES --> STATE_INIT[🗃️ UIStateManager.__init__()]
    INIT_SERVICES --> CONTROLLER_INIT[🎮 ApplicationController.__init__()]
    
    %% Controller Service Setup
    CONTROLLER_INIT --> COORD_INIT[📍 CoordinateMappingService.__init__()]
    CONTROLLER_INIT --> EXTRACT_INIT[📄 TextExtractionService.__init__()]
    CONTROLLER_INIT --> VALID_INIT[✅ ValidationService.__init__()]
    CONTROLLER_INIT --> QUALITY_INIT[⭐ QualityAssessmentEngine.__init__()]
    CONTROLLER_INIT --> REPO_INIT[💾 DocumentRepository.__init__()]
    CONTROLLER_INIT --> MIGRATION_INIT[🔄 MigrationManager.__init__()]
    CONTROLLER_INIT --> PROCESSOR_INIT[⚙️ UnifiedDocumentProcessor.__init__()]
    
    %% UI Creation
    INIT_SERVICES --> MAIN_WINDOW_INIT[🏠 MainWindowV2.__init__()]
    MAIN_WINDOW_INIT --> CREATE_MENU[📋 _create_menu_bar()]
    MAIN_WINDOW_INIT --> CREATE_TOOLBAR[🔧 _create_tool_bar()]
    MAIN_WINDOW_INIT --> CREATE_TABS[📑 _create_tabs()]
    MAIN_WINDOW_INIT --> CREATE_DOCKS[🏠 _create_dock_widgets()]
    
    %% Tab Creation
    CREATE_TABS --> IMPORT_TAB_INIT[📥 _create_import_tab()]
    CREATE_TABS --> VALID_TAB_INIT[✅ UnifiedValidationView.__init__()]
    CREATE_TABS --> PROJECT_TAB_INIT[📁 ProjectManagerV2.__init__()]
    CREATE_TABS --> EXPORT_TAB_INIT[📤 _create_export_tab()]
    
    %% Import Tab Components
    IMPORT_TAB_INIT --> DOC_VIEWER_INIT[👁️ DocumentViewerV2.__init__()]
    IMPORT_TAB_INIT --> DOC_LIST_INIT[📋 _create_document_list()]
    
    %% Event Setup
    MAIN_WINDOW_INIT --> SETUP_EVENTS[📡 _setup_events()]
    SETUP_EVENTS --> EVENT_SUBSCRIPTIONS[📬 event_bus.subscribe()]
    
    %% Controller Event Binding
    INIT_SERVICES --> SETUP_CONTROLLER_EVENTS[🔗 _setup_controller_events()]
    SETUP_CONTROLLER_EVENTS --> BIND_DOC_LOAD[📄 handle_document_load]
    SETUP_CONTROLLER_EVENTS --> BIND_DOC_PROCESS[⚙️ handle_document_processing]
    SETUP_CONTROLLER_EVENTS --> BIND_PROJECT_OPS[📁 handle_project_operations]
    
    %% Application Ready
    EVENT_SUBSCRIPTIONS --> APP_SHOW[📺 main_window.show()]
    APP_SHOW --> APP_EXEC[🔄 app.exec_()]
```

---

## 📄 **Document Processing Function Calls**

```mermaid
sequenceDiagram
    participant USER as 👤 User
    participant UI as 🖥️ MainWindow
    participant EB as 📡 EventBus
    participant CTRL as 🎮 Controller
    participant PROC as ⚙️ Processor
    participant EXTRACT as 📄 ExtractService
    participant COORD as 📍 CoordService
    participant QUALITY as ⭐ QualityEngine
    participant VALID as ✅ ValidService
    participant REPO as 💾 Repository
    
    %% Document Loading Flow
    USER->>UI: Click "Import Documents"
    UI->>UI: _import_documents()
    UI->>EB: publish(DOCUMENT_LOADED)
    EB->>CTRL: handle_document_load()
    CTRL->>CTRL: load_document(file_path)
    CTRL->>CTRL: _create_document_from_file()
    CTRL->>CTRL: _extract_document_info()
    CTRL-->>EB: publish(DOCUMENT_LOADED response)
    EB->>UI: DocumentViewer.load_document()
    
    %% Content Retrieval
    UI->>CTRL: get_document_content(doc_id)
    CTRL->>EXTRACT: extract_text(document)
    EXTRACT->>EXTRACT: _perform_extraction()
    EXTRACT->>EXTRACT: _extract_single_page()
    EXTRACT->>COORD: pdf_to_widget()
    COORD-->>EXTRACT: coordinates
    EXTRACT-->>CTRL: ExtractionResult
    CTRL-->>UI: content_data
    
    %% Document Processing
    USER->>UI: Click "Process Documents"
    UI->>EB: publish(DOCUMENT_PROCESSING_STARTED)
    EB->>CTRL: handle_document_processing()
    CTRL->>PROC: process_document(doc_id)
    PROC->>PROC: _load_document()
    PROC->>PROC: _extract_content()
    PROC->>EXTRACT: extract(document)
    EXTRACT-->>PROC: extraction_result
    PROC->>QUALITY: assess_quality()
    QUALITY-->>PROC: quality_result
    PROC->>VALID: validate(document)
    VALID-->>PROC: validation_result
    PROC->>PROC: _generate_result()
    PROC-->>CTRL: ProcessingResult
    CTRL->>REPO: save(document)
    CTRL-->>EB: publish(PROCESSING_COMPLETED)
    
    %% Validation Flow
    USER->>UI: Start Validation
    UI->>EB: publish(VALIDATION_STARTED)
    EB->>CTRL: handle_validation()
    CTRL->>VALID: create_validation_session()
    VALID->>VALID: detect_issues()
    VALID->>COORD: map_issue_coordinates()
    VALID->>VALID: generate_validation_data()
    VALID-->>CTRL: ValidationSession
    CTRL-->>UI: validation_data
```

---

## 🗂️ **Data Flow & State Management**

```mermaid
stateDiagram-v2
    [*] --> AppStartup: Application Launch
    
    AppStartup --> ServicesReady: Initialize Services
    ServicesReady --> UIReady: Create UI Components
    UIReady --> WaitingForInput: Setup Event Handlers
    
    state DocumentLifecycle {
        [*] --> DocumentSelected: User Selects File
        DocumentSelected --> DocumentLoading: Load Document
        DocumentLoading --> DocumentLoaded: Create UnifiedDocument
        DocumentLoaded --> ContentExtracted: Extract Text/Content
        ContentExtracted --> QualityAssessed: Assess Quality
        QualityAssessed --> ValidationRequired: Check Quality Score
        
        ValidationRequired --> ValidationInProgress: Quality < Threshold
        ValidationRequired --> ProcessingComplete: Quality >= Threshold
        
        ValidationInProgress --> PageValidation: Start Page-by-Page
        PageValidation --> IssueDetection: Detect Issues
        IssueDetection --> UserReview: Present to User
        UserReview --> IssueResolved: User Approves/Corrects
        IssueResolved --> ValidationComplete: All Issues Resolved
        ValidationComplete --> ProcessingComplete: Validation Done
        
        ProcessingComplete --> DocumentSaved: Save to Repository
        DocumentSaved --> [*]: Document Complete
    }
    
    state ProjectLifecycle {
        [*] --> ProjectCreated: Create/Load Project
        ProjectCreated --> DocumentsAdded: Add Documents
        DocumentsAdded --> ProcessingDocuments: Process All Documents
        ProcessingDocuments --> AllProcessed: All Documents Complete
        AllProcessed --> ProjectSaved: Save Project State
        ProjectSaved --> ExportReady: Ready for Export
        ExportReady --> [*]: Project Complete
    }
    
    WaitingForInput --> DocumentLifecycle: Document Operation
    WaitingForInput --> ProjectLifecycle: Project Operation
    DocumentLifecycle --> WaitingForInput: Operation Complete
    ProjectLifecycle --> WaitingForInput: Operation Complete
```

---

## 🎛️ **Event Types & Signal Flow**

```mermaid
mindmap
  root((📡 Event Types))
    🏠 Application Events
      APP_STARTED
      APP_CLOSING
      THEME_CHANGED
      STATUS_CHANGED
    📄 Document Events  
      DOCUMENT_LOADED
      DOCUMENT_PROCESSING_STARTED
      DOCUMENT_PROCESSING_COMPLETED
      DOCUMENT_SAVED
      DOCUMENT_DELETED
    ✅ Validation Events
      VALIDATION_STARTED
      VALIDATION_COMPLETED
      VALIDATION_CANCELLED
      ISSUE_DETECTED
      ISSUE_RESOLVED
    📁 Project Events
      PROJECT_CREATED
      PROJECT_LOADED
      PROJECT_SAVED
      PROJECT_DELETED
    🖥️ UI Events
      TAB_CHANGED
      PAGE_CHANGED
      AREA_SELECTED
      PROGRESS_UPDATED
    ❌ Error Events
      ERROR_OCCURRED
      WARNING_OCCURRED
      CRITICAL_ERROR
```

---

## 🔧 **Service Methods & Functions**

### **ApplicationController Methods:**
```mermaid
classDiagram
    class ApplicationController {
        +__init__()
        +load_document(file_path) Dict
        +process_document(doc_id, config) Dict
        +get_document_list() List
        +get_document_content(doc_id, page) Dict
        +get_validation_data(doc_id) Dict
        +create_new_project(name) Dict
        +load_project(path) Dict
        +save_project(path) Dict
        +get_processing_stats() Dict
        -_load_tore_file(path) Dict
        -_create_document_from_file(path) UnifiedDocument
        -_extract_document_info(doc) Dict
        -_update_document_with_results(doc, result)
        -_generate_project_id(name) str
    }
```

### **TextExtractionService Methods:**
```mermaid
classDiagram
    class TextExtractionService {
        +__init__(coordinate_service)
        +extract_text(document, page_range, coords, analysis) ExtractionResult
        +extract_page_text(document, page, coords) Dict
        +get_text_at_coordinates(document, coords) str
        +search_text_in_document(document, text, case_sensitive) List
        +clear_cache(doc_id)
        +get_performance_stats() Dict
        -_perform_extraction(document, range, coords, analysis) ExtractionResult
        -_extract_single_page(page, page_num, coords) Dict
        -_analyze_content(doc, result, start, end)
        -_detect_tables(page, page_num) List
        -_detect_images(page, page_num) List
        -_detect_diagrams(page, page_num) List
        -_generate_cache_key(document, range, coords) str
        -_update_stats(result, time)
    }
```

### **ValidationService Methods:**
```mermaid
classDiagram
    class ValidationService {
        +__init__(coord_service, extract_service)
        +create_validation_session(document, config) ValidationSession
        +validate_document(document, extraction_result) Dict
        +detect_issues(document, content) List
        +validate_page(session, page_num) List
        +approve_issue(session_id, issue_id) bool
        +reject_issue(session_id, issue_id) bool
        +get_validation_progress(session_id) Dict
        +save_validation_session(session) bool
        +load_validation_session(session_id) ValidationSession
        -_analyze_text_quality(text) List
        -_detect_ocr_errors(text, coords) List
        -_validate_coordinates(coords, page_bounds) List
        -_check_formatting_issues(content) List
        -_calculate_confidence_scores(issues) Dict
        -_generate_session_id() str
    }
```

---

## 📊 **Complete System Data Flow**

```mermaid
flowchart LR
    %% Input Sources
    subgraph "📥 Input Sources"
        USER_FILES[📄 User Files<br/>PDF/DOCX/ODT/RTF]
        TORE_FILES[📋 .tore Files<br/>V1.0/V1.1/V2.0]
        USER_ACTIONS[👤 User Actions<br/>UI Interactions]
    end
    
    %% Processing Pipeline
    subgraph "⚙️ Processing Pipeline"
        LOAD[📂 Document Loading]
        EXTRACT[📄 Text Extraction]
        ANALYZE[🔍 Content Analysis] 
        ASSESS[⭐ Quality Assessment]
        VALIDATE[✅ Validation]
        PROCESS[🔄 Final Processing]
    end
    
    %% Storage & State
    subgraph "💾 Storage & State"
        MEMORY[🧠 In-Memory Storage]
        PROJECTS[📁 Project Files]
        CACHE[⚡ Extraction Cache]
        STATE[🗃️ UI State]
    end
    
    %% Output & UI
    subgraph "📤 Output & Display"
        DOCUMENT_VIEW[👁️ Document Viewer]
        VALIDATION_UI[✅ Validation Interface]
        PROJECT_MGR[📋 Project Manager]
        EXPORT[📊 Export Formats]
    end
    
    %% Data Flow Connections
    USER_FILES --> LOAD
    TORE_FILES --> LOAD
    USER_ACTIONS --> LOAD
    
    LOAD --> EXTRACT
    EXTRACT --> ANALYZE
    ANALYZE --> ASSESS
    ASSESS --> VALIDATE
    VALIDATE --> PROCESS
    
    PROCESS --> MEMORY
    PROCESS --> PROJECTS
    EXTRACT --> CACHE
    USER_ACTIONS --> STATE
    
    MEMORY --> DOCUMENT_VIEW
    MEMORY --> VALIDATION_UI
    PROJECTS --> PROJECT_MGR
    PROCESS --> EXPORT
    
    %% Feedback Loops
    VALIDATION_UI -.-> VALIDATE
    PROJECT_MGR -.-> PROJECTS
    DOCUMENT_VIEW -.-> STATE
```

---

## 🎯 **Study Guide: Key Areas for Improvement**

### **🔍 Performance Optimization Areas:**
1. **Text Extraction Caching** - Improve cache hit rates
2. **Coordinate Mapping** - Optimize coordinate calculations
3. **Memory Management** - Better document lifecycle management
4. **Batch Processing** - Parallel document processing

### **🔧 Functionality Enhancements:**
1. **Advanced OCR** - Better OCR error detection
2. **Machine Learning** - AI-powered quality assessment
3. **Real-time Validation** - Live validation feedback
4. **Cloud Integration** - Remote processing capabilities

### **🖥️ UI/UX Improvements:**
1. **Progressive Loading** - Better user feedback during processing
2. **Advanced Filtering** - Better document organization
3. **Keyboard Shortcuts** - Power user features
4. **Accessibility** - Screen reader support

### **🔄 Architecture Enhancements:**
1. **Plugin System** - Extensible extraction strategies
2. **Microservices** - Distributed processing
3. **Event Sourcing** - Better audit trails
4. **CQRS Pattern** - Separate read/write models

---

*This flowchart provides a complete visual representation of the TORE Matrix Labs V2 system for study and improvement planning.*