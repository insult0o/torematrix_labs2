# Agent 2: Format Processors & Template System - Issue #32.2

## 🎯 Mission: Format Processors, Template System & Output Generation

**Branch**: `feature/export-formats-agent2-issue32.2`
**Dependencies**: Agent 1 Core Engine, Hierarchy Management (#29)
**Timeline**: Days 3-4 of 6-day development cycle

## 📋 Scope & Responsibilities

### Primary Objectives
1. **Format Processors Implementation**
   - Markdown format processor
   - Plain text with structure processor
   - JSONL format processor
   - Table-to-text conversion system

2. **Template System**
   - Template engine architecture
   - Custom format template support
   - Dynamic template compilation
   - Format customization interface

3. **Output Generation**
   - Format-specific text generation
   - Structure preservation in outputs
   - Quality validation system
   - Format preview capabilities

## 🏗️ Technical Implementation

### Core Files to Create
```
src/torematrix/integrations/export/
├── formatters/
│   ├── __init__.py
│   ├── base.py               # Base formatter class
│   ├── markdown.py           # Markdown formatter
│   ├── plaintext.py          # Plain text formatter
│   ├── jsonl.py              # JSONL formatter
│   └── table_converter.py    # Table-to-text conversion
├── templates/
│   ├── __init__.py
│   ├── engine.py             # Template engine
│   ├── compiler.py           # Template compiler
│   ├── renderer.py           # Template renderer
│   └── validators.py         # Template validation
├── generators/
│   ├── __init__.py
│   ├── output_generator.py   # Main output generator
│   ├── preview_generator.py  # Preview generation
│   └── quality_checker.py    # Output quality validation
└── formats/
    ├── __init__.py
    ├── markdown_templates/
    │   ├── default.md
    │   ├── academic.md
    │   └── training.md
    ├── text_templates/
    │   ├── structured.txt
    │   └── flat.txt
    └── jsonl_templates/
        ├── training.jsonl
        └── evaluation.jsonl
```

### Key Classes to Implement

#### 1. BaseFormatter (formatters/base.py)
```python
class BaseFormatter(ABC):
    """Base class for all format processors"""
    
    @abstractmethod
    def format_document(self, processed_doc: ProcessedDocument) -> FormattedOutput:
        pass
    
    @abstractmethod
    def format_element(self, element: Element, context: FormatContext) -> str:
        pass
    
    def validate_output(self, output: FormattedOutput) -> ValidationResult:
        pass
```

#### 2. MarkdownFormatter (formatters/markdown.py)
```python
class MarkdownFormatter(BaseFormatter):
    """Markdown format processor with structure preservation"""
    
    def __init__(self, flavor: str = "github"):
        self.flavor = flavor
        self.heading_processor = HeadingProcessor()
        self.table_processor = TableProcessor()
        self.list_processor = ListProcessor()
    
    def format_headings(self, element: Element) -> str:
        pass
    
    def format_tables(self, element: Element) -> str:
        pass
    
    def format_lists(self, element: Element) -> str:
        pass
```

#### 3. TemplateEngine (templates/engine.py)
```python
class TemplateEngine:
    """Template processing and rendering engine"""
    
    def __init__(self):
        self.compiler = TemplateCompiler()
        self.renderer = TemplateRenderer()
        self.validator = TemplateValidator()
    
    def load_template(self, template_path: str) -> Template:
        pass
    
    def compile_template(self, template_str: str) -> CompiledTemplate:
        pass
    
    def render(self, template: Template, data: dict) -> str:
        pass
```

#### 4. TableConverter (formatters/table_converter.py)
```python
class TableConverter:
    """Advanced table-to-text conversion system"""
    
    def convert_to_markdown(self, table: TableElement) -> str:
        pass
    
    def convert_to_text(self, table: TableElement, style: str = "aligned") -> str:
        pass
    
    def preserve_structure(self, table: TableElement) -> StructuredTable:
        pass
    
    def detect_table_type(self, table: TableElement) -> TableType:
        pass
```

## 🔧 Implementation Details

### Format Processors

#### Markdown Processor Features
- **GitHub Flavored Markdown** support
- **Academic Paper** format with citations
- **Training Data** format optimization
- **Heading hierarchy** preservation (H1-H6)
- **Table formatting** with alignment
- **List nesting** maintenance
- **Code block** handling
- **Link preservation**

#### Plain Text Processor Features
- **Structured layout** with visual hierarchy
- **ASCII table** generation
- **Indentation-based** structure
- **Reading flow** optimization
- **Character encoding** handling
- **Line length** control

#### JSONL Processor Features
- **Training format** compatibility
- **Metadata preservation**
- **Structured data** encoding
- **Token optimization**
- **Batch processing**
- **Validation rules**

### Template System Architecture

#### Template Types
1. **Static Templates**: Pre-defined format layouts
2. **Dynamic Templates**: Runtime customizable formats
3. **Conditional Templates**: Logic-based formatting
4. **Composite Templates**: Multi-format combinations

#### Template Variables
```jinja2
# Example template structure
{{ document.title }}
{% for section in document.sections %}
## {{ section.heading }}
{{ section.content | preserve_structure }}
{% if section.tables %}
{% for table in section.tables %}
{{ table | format_table(style="markdown") }}
{% endfor %}
{% endif %}
{% endfor %}
```

### Output Generation Pipeline
1. **Content Analysis**: Analyze processed document structure
2. **Template Selection**: Choose appropriate template
3. **Data Mapping**: Map document data to template variables
4. **Rendering**: Generate formatted output
5. **Validation**: Verify output quality and structure
6. **Post-processing**: Apply final formatting rules

## 🧪 Testing Requirements

### Unit Tests (tests/unit/export/test_formatters.py)
```python
class TestMarkdownFormatter:
    def test_heading_formatting()
    def test_table_conversion()
    def test_list_preservation()
    def test_structure_maintenance()

class TestTemplateEngine:
    def test_template_compilation()
    def test_variable_substitution()
    def test_conditional_logic()
    def test_error_handling()

class TestTableConverter:
    def test_markdown_conversion()
    def test_text_alignment()
    def test_structure_preservation()
    def test_complex_tables()
```

### Integration Tests
- Format processor integration with core engine
- Template system integration
- Output validation testing
- Performance testing with large documents

## 📊 Success Criteria

### Functional Requirements
- [ ] All format processors implemented and functional
- [ ] Template system operational with custom formats
- [ ] Table conversion working for all output formats
- [ ] Output generation pipeline complete
- [ ] Preview system functional

### Format Quality Requirements
- [ ] Markdown output validates with parsers
- [ ] Plain text maintains readability
- [ ] JSONL format follows training standards
- [ ] Table formatting preserves data integrity
- [ ] Structure preservation >95% accurate

### Performance Requirements
- [ ] Template compilation under 100ms
- [ ] Format processing under 5s for large documents
- [ ] Memory efficient template caching
- [ ] Concurrent format generation support

## 🔗 Integration Points

### Upstream Dependencies
- **Agent 1**: Core export engine and text processor
- **Hierarchy Management**: Structure information
- **Element Model**: Element type definitions

### Downstream Handoffs
- **Agent 3**: Formatted output for tokenization
- **Agent 4**: Complete format processors for integration

## 📈 Development Timeline

### Day 3: Format Processors
- Implement base formatter class
- Create markdown formatter
- Develop plain text formatter
- Basic template engine

### Day 4: Template System & Advanced Features
- Complete template system
- JSONL formatter implementation
- Table conversion system
- Output generation pipeline

## 🚨 Critical Dependencies

### Required Before Starting
1. Agent 1 core engine completion
2. Hierarchy management system access
3. Element model interface verification

### Blocking Issues
- Core engine interface changes
- Missing hierarchy information
- Template syntax conflicts

## 📝 Deliverables

### Code Components
- Complete format processor suite
- Template engine with custom format support
- Table conversion system
- Output generation pipeline

### Templates
- Default templates for all formats
- Academic paper templates
- Training data templates
- Custom template examples

### Documentation
- Format processor API documentation
- Template system guide
- Custom template creation tutorial

### Tests
- Comprehensive formatter test suite
- Template system tests
- Output validation tests
- Performance benchmarks

## 🎯 Format Specifications

### Markdown Output Features
- GitHub Flavored Markdown compatibility
- Academic paper formatting
- Citation preservation
- Code block handling
- Table alignment options

### Plain Text Features
- Structured layout with visual hierarchy
- ASCII table generation
- Configurable line width
- Indentation-based structure

### JSONL Features
- Training data format compatibility
- Metadata preservation
- Token-optimized output
- Batch processing support

---

**Ready for Deployment**: This specification is complete and ready for deployment after Agent 1.

**Next Agent**: Agent 3 will build tokenization and optimization features on this foundation.