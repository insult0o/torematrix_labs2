# AGENT 4 ASSIGNMENT: Integration, UI Components & Polish

## 🎯 Your Mission (Agent 4)
You are **Agent 4** responsible for complete system integration with polished UI components. Your role is to create the final user interface, integrate all search and filter components, and deliver a production-ready search and filter system.

## 📋 Your Specific Tasks

### 1. Main Search Interface Widget
```python
# Create src/torematrix/ui/search/widgets.py
class SearchWidget(QWidget):
    """Main search interface combining all components"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.search_engine = None
        self.filter_manager = None
        self.cache_manager = None
        self.setup_ui()
        self.setup_connections()
    
    def setup_ui(self) -> None:
        """Setup complete search interface layout"""
        
    def setup_connections(self) -> None:
        """Connect all signals and slots"""
        
    async def perform_search(self, query: str) -> None:
        """Execute search with progress indication"""
        
    def update_results_display(self, results: SearchResults) -> None:
        """Update results view with highlighting"""
        
    def apply_filters(self, filters: List[Filter]) -> None:
        """Apply filters and update display"""
```

### 2. Advanced Search Bar Component
```python
# Create src/torematrix/ui/search/widgets/search_bar.py
class AdvancedSearchBar(QLineEdit):
    """Enhanced search bar with autocomplete and suggestions"""
    
    search_requested = pyqtSignal(str)
    filter_requested = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.suggestion_engine = None
        self.completer = None
        self.setup_autocomplete()
        self.setup_shortcuts()
    
    def setup_autocomplete(self) -> None:
        """Setup real-time search suggestions"""
        
    def setup_shortcuts(self) -> None:
        """Setup keyboard shortcuts"""
        
    def show_suggestions(self, suggestions: List[str]) -> None:
        """Display search suggestions dropdown"""
        
    def validate_query(self, query: str) -> bool:
        """Validate search query and show errors"""
```

### 3. Visual Filter Panel
```python
# Create src/torematrix/ui/search/widgets/filter_panel.py
class FilterPanel(QWidget):
    """Visual filter controls with drag-and-drop"""
    
    filters_changed = pyqtSignal(list)
    filter_saved = pyqtSignal(str, list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_filters = []
        self.saved_filters = {}
        self.setup_ui()
    
    def setup_ui(self) -> None:
        """Setup filter panel layout"""
        
    def add_filter_widget(self, filter_type: str) -> None:
        """Add new filter control widget"""
        
    def remove_filter_widget(self, widget: QWidget) -> None:
        """Remove filter control widget"""
        
    def build_filters_from_ui(self) -> List[Filter]:
        """Extract filters from UI controls"""
        
    def load_saved_filter_set(self, name: str) -> None:
        """Load and apply saved filter set"""
```

### 4. Search Results Display
```python
# Create src/torematrix/ui/search/widgets/results_view.py
class SearchResultsView(QAbstractItemView):
    """Optimized results view with virtual scrolling"""
    
    result_selected = pyqtSignal(str)  # element_id
    result_activated = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.lazy_loader = None
        self.highlighter = None
        self.virtual_scroller = None
        self.setup_virtual_scrolling()
    
    def setup_virtual_scrolling(self) -> None:
        """Setup virtual scrolling for large result sets"""
        
    def update_results(self, results: SearchResults) -> None:
        """Update displayed results with highlighting"""
        
    def highlight_search_terms(self, text: str, terms: List[str]) -> str:
        """Highlight search terms in result text"""
        
    def export_visible_results(self, format: str) -> None:
        """Export currently visible results"""
```

### 5. Search Highlighting System
```python
# Create src/torematrix/ui/search/highlighting.py
class SearchHighlighter:
    """Highlight search terms in results"""
    
    def __init__(self):
        self.highlight_style = "background-color: yellow; font-weight: bold;"
        self.case_sensitive = False
    
    def highlight_text(self, text: str, search_terms: List[str]) -> str:
        """Highlight search terms in HTML text"""
        
    def highlight_element(self, element: Element, search_terms: List[str]) -> HighlightedElement:
        """Create highlighted version of element"""
        
    def set_highlight_style(self, style: str) -> None:
        """Configure highlight appearance"""
        
    def clear_highlights(self, text: str) -> str:
        """Remove all highlighting from text"""
```

### 6. Export Functionality
```python
# Create src/torematrix/ui/search/export.py
class ResultExporter:
    """Export filtered results to various formats"""
    
    def __init__(self):
        self.supported_formats = ['json', 'csv', 'pdf', 'html', 'xlsx']
    
    async def export_results(self, results: List[Element], 
                           format: str, output_path: str) -> bool:
        """Export results to specified format"""
        
    async def export_to_json(self, results: List[Element], output_path: str) -> None:
        """Export to JSON format"""
        
    async def export_to_csv(self, results: List[Element], output_path: str) -> None:
        """Export to CSV format"""
        
    async def export_to_pdf(self, results: List[Element], output_path: str) -> None:
        """Export to PDF format with formatting"""
        
    def get_export_progress(self) -> ExportProgress:
        """Get current export progress"""
```

### 7. Statistics and Summary Panel
```python
# Create src/torematrix/ui/search/widgets/stats_panel.py
class StatisticsPanel(QWidget):
    """Display search result statistics and summaries"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self) -> None:
        """Setup statistics display layout"""
        
    def update_statistics(self, results: SearchResults) -> None:
        """Update displayed statistics"""
        
    def show_type_distribution(self, results: List[Element]) -> None:
        """Show element type distribution chart"""
        
    def show_performance_metrics(self, metrics: PerformanceMetrics) -> None:
        """Display search performance metrics"""
        
    def show_filter_summary(self, active_filters: List[Filter]) -> None:
        """Display summary of active filters"""
```

## 🔧 Files You Must Create

### Main UI Components
```
src/torematrix/ui/search/
├── widgets.py                    # Main SearchWidget class (PRIMARY)
├── panels.py                     # Filter panel and controls
├── highlighting.py               # Search result highlighting (PRIMARY)
├── export.py                     # Export filtered results
├── statistics.py                 # Result statistics and summaries
├── shortcuts.py                  # Keyboard shortcuts
└── accessibility.py              # Accessibility features

src/torematrix/ui/search/widgets/
├── __init__.py
├── search_bar.py                 # AdvancedSearchBar component
├── filter_panel.py               # Visual filter controls
├── results_view.py               # SearchResultsView with virtual scrolling
├── stats_panel.py                # Statistics panel
└── export_dialog.py              # Export options dialog
```

### Integration and Polish
```
src/torematrix/ui/search/
├── integration.py                # System integration layer
├── themes.py                     # Search UI theming
├── validation.py                 # User input validation
└── help.py                      # Contextual help system

src/torematrix/ui/search/dialogs/
├── __init__.py
├── advanced_search.py            # Advanced search dialog
├── filter_builder.py             # Visual filter builder dialog
├── export_options.py             # Export configuration dialog
└── search_history.py             # Search history browser
```

### Test Files (MANDATORY >95% Coverage)
```
tests/unit/ui/search/
├── test_widgets.py               # Widget tests (30+ tests)
├── test_panels.py                # Panel tests (20+ tests)
├── test_highlighting.py          # Highlighting tests (15+ tests)
├── test_export.py                # Export tests (20+ tests)
├── test_statistics.py            # Statistics tests (10+ tests)
├── test_shortcuts.py             # Keyboard shortcuts tests (10+ tests)
└── test_accessibility.py         # Accessibility tests (15+ tests)

tests/integration/search/
├── __init__.py
├── test_full_search.py           # Complete search workflow (20+ tests)
├── test_filter_integration.py    # Filter integration (15+ tests)
├── test_performance_integration.py # Performance tests (10+ tests)
├── test_export_integration.py    # Export integration (10+ tests)
└── test_ui_integration.py        # Full UI integration (25+ tests)

tests/e2e/search/
├── __init__.py
├── test_search_workflows.py      # End-to-end search scenarios
├── test_filter_workflows.py      # End-to-end filter scenarios
└── test_export_workflows.py      # End-to-end export scenarios
```

## 🧪 Acceptance Criteria You Must Meet

### UI/UX Requirements
- [ ] **Complete Search Interface**: Modern, intuitive design
- [ ] **Visual Filter Panel**: Drag-and-drop filter construction
- [ ] **Search Highlighting**: Configurable highlighting styles
- [ ] **Export Functionality**: Multiple formats (JSON, CSV, PDF, HTML)
- [ ] **Real-time Statistics**: Live result summaries and metrics
- [ ] **Keyboard Navigation**: Full keyboard accessibility
- [ ] **Responsive Design**: Works at different window sizes

### Integration Requirements
- [ ] **Agent 1 Integration**: Seamless use of search engine
- [ ] **Agent 2 Integration**: Complete filter system integration
- [ ] **Agent 3 Integration**: Performance optimizations active
- [ ] **State Management**: Proper state persistence
- [ ] **Event Bus**: Proper event handling throughout

### Accessibility Requirements
- [ ] **Screen Reader Support**: ARIA labels and descriptions
- [ ] **Keyboard Navigation**: Tab order and keyboard shortcuts
- [ ] **High Contrast**: Support for accessibility themes
- [ ] **Font Scaling**: Responsive to system font size changes

### Performance Requirements
- [ ] **UI Responsiveness**: <100ms for all user interactions
- [ ] **Export Performance**: 10K elements in <5 seconds
- [ ] **Memory Usage**: Efficient UI memory management
- [ ] **Smooth Scrolling**: No stuttering with large result sets

## 🔌 Integration Points

### What You Integrate (From Previous Agents)
- **Agent 1**: SearchEngine, SearchIndexer, QueryParser
- **Agent 2**: FilterManager, QueryBuilder, DSL parser
- **Agent 3**: CacheManager, LazyLoader, PerformanceMonitor

### What You Connect To
- **Element List (#21)**: Display search results in context
- **State Management (#3)**: Persist search and filter state
- **Theme System (#14)**: Apply consistent theming

### What You Provide (Final System)
- **Complete Search Interface**: Ready-to-use search system
- **Search and Filter APIs**: For other components to use
- **Export Capabilities**: For external data extraction
- **Performance Monitoring**: For system administrators

## 🚀 Getting Started

### 1. Create Your Feature Branch
```bash
git checkout main
git pull origin main
git checkout -b feature/search-integration-agent4-issue216
```

### 2. Study All Previous Work
```bash
# Review all agent implementations
find src/torematrix/ui/search -name "*.py" -exec head -20 {} \;
```

### 3. Start with Main Widget Integration
Begin with the main SearchWidget that orchestrates all components.

## 🎯 Success Metrics

### User Experience Targets
- **Intuitive Interface**: Users can search without training
- **Fast Response**: <100ms for all UI interactions
- **Comprehensive Features**: All search/filter needs met
- **Accessibility**: 100% WCAG 2.1 AA compliance

### Technical Targets
- **Integration Quality**: Seamless component interaction
- **Error Handling**: Graceful handling of all error conditions
- **Performance**: No performance regressions
- **Maintainability**: Clean, documented, testable code

## 📚 Technical Implementation Details

### Main Widget Architecture
```python
class SearchWidget(QWidget):
    """Central coordinator for all search functionality"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Initialize all agents' components
        self.search_engine = SearchEngine(search_indexer)
        self.filter_manager = FilterManager(self.search_engine)
        self.cache_manager = CacheManager()
        self.lazy_loader = LazyResultLoader()
        
        # UI components
        self.search_bar = AdvancedSearchBar(self)
        self.filter_panel = FilterPanel(self)
        self.results_view = SearchResultsView(self)
        self.stats_panel = StatisticsPanel(self)
        
        self.setup_layout()
        self.connect_signals()
    
    def setup_layout(self) -> None:
        """Create responsive layout"""
        layout = QVBoxLayout(self)
        
        # Top: Search bar
        layout.addWidget(self.search_bar)
        
        # Middle: Horizontal split
        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.addWidget(self.filter_panel)
        main_splitter.addWidget(self.results_view)
        main_splitter.setSizes([300, 700])  # 30/70 split
        layout.addWidget(main_splitter)
        
        # Bottom: Statistics
        layout.addWidget(self.stats_panel)
    
    async def handle_search(self, query: str) -> None:
        """Coordinate search across all components"""
        try:
            # Get active filters
            filters = self.filter_panel.build_filters_from_ui()
            
            # Execute search with caching
            results = await self.search_engine.search(query, filters)
            
            # Update all displays
            self.results_view.update_results(results)
            self.stats_panel.update_statistics(results)
            
        except Exception as e:
            self.handle_search_error(e)
```

### Export Integration
```python
class ExportDialog(QDialog):
    """Export configuration dialog"""
    
    def __init__(self, results: List[Element], parent=None):
        super().__init__(parent)
        self.results = results
        self.exporter = ResultExporter()
        self.setup_ui()
    
    def setup_ui(self) -> None:
        """Setup export options interface"""
        layout = QVBoxLayout(self)
        
        # Format selection
        format_group = QGroupBox("Export Format")
        format_layout = QVBoxLayout(format_group)
        
        self.format_buttons = {}
        for format in self.exporter.supported_formats:
            button = QRadioButton(format.upper())
            self.format_buttons[format] = button
            format_layout.addWidget(button)
        
        layout.addWidget(format_group)
        
        # Options based on format
        self.options_widget = QWidget()
        layout.addWidget(self.options_widget)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.start_export)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    async def start_export(self) -> None:
        """Start export process with progress tracking"""
```

### Accessibility Implementation
```python
class AccessibilityManager:
    """Manage accessibility features throughout search UI"""
    
    def __init__(self, search_widget: SearchWidget):
        self.search_widget = search_widget
        self.setup_accessibility()
    
    def setup_accessibility(self) -> None:
        """Configure accessibility for all components"""
        
        # Search bar accessibility
        search_bar = self.search_widget.search_bar
        search_bar.setAccessibleName("Search query input")
        search_bar.setAccessibleDescription("Enter search terms or use advanced query syntax")
        
        # Filter panel accessibility
        filter_panel = self.search_widget.filter_panel
        filter_panel.setAccessibleName("Filter controls")
        filter_panel.setAccessibleDescription("Configure search filters")
        
        # Results view accessibility
        results_view = self.search_widget.results_view
        results_view.setAccessibleName("Search results")
        results_view.setAccessibleDescription("Browse search results, use arrow keys to navigate")
        
        # Keyboard shortcuts
        self.setup_keyboard_shortcuts()
    
    def setup_keyboard_shortcuts(self) -> None:
        """Setup comprehensive keyboard shortcuts"""
        shortcuts = {
            'Ctrl+F': 'focus_search_bar',
            'Ctrl+Shift+F': 'open_advanced_search',
            'F3': 'find_next',
            'Shift+F3': 'find_previous',
            'Ctrl+E': 'toggle_filter_panel',
            'Ctrl+Shift+E': 'export_results',
            'Escape': 'clear_search'
        }
        
        for key_combo, action in shortcuts.items():
            shortcut = QShortcut(QKeySequence(key_combo), self.search_widget)
            shortcut.activated.connect(getattr(self, action))
```

## 🔗 Communication Protocol

### Error Handling Strategy
```python
class SearchErrorHandler:
    """Centralized error handling for search operations"""
    
    def handle_search_error(self, error: Exception) -> None:
        """Handle search-related errors with user feedback"""
        if isinstance(error, QuerySyntaxError):
            self.show_query_error(error.message, error.position)
        elif isinstance(error, FilterValidationError):
            self.show_filter_error(error.filter_name, error.message)
        elif isinstance(error, PerformanceError):
            self.show_performance_warning(error.message)
        else:
            self.show_generic_error("Search failed", str(error))
    
    def show_query_error(self, message: str, position: int) -> None:
        """Show query syntax error with position highlighting"""
        
    def show_filter_error(self, filter_name: str, message: str) -> None:
        """Show filter validation error"""
        
    def show_performance_warning(self, message: str) -> None:
        """Show performance-related warning"""
```

## 🏁 Definition of Done

Your work is complete when:
1. ✅ Complete search interface with all features working
2. ✅ All three agents' work seamlessly integrated
3. ✅ Export functionality working for all supported formats
4. ✅ Full accessibility compliance (WCAG 2.1 AA)
5. ✅ Comprehensive error handling and user feedback
6. ✅ >95% test coverage including integration and e2e tests
7. ✅ Performance requirements met (<100ms UI response)
8. ✅ Production-ready documentation and user guide

## 🎉 Final Integration Success

When you complete this work, the Search and Filter System will be:
- **Fully Functional**: Complete search and filter capabilities
- **High Performance**: Optimized for large datasets
- **User Friendly**: Intuitive interface with excellent UX
- **Accessible**: Full accessibility support
- **Production Ready**: Comprehensive testing and error handling
- **Well Integrated**: Seamless integration with existing systems

This represents the culmination of all four agents' coordinated work into a world-class search and filter system!