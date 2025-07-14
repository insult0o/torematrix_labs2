# Table Extraction and Preservation Strategies

## 📊 Overview

Tables are one of the most challenging elements to extract from PDFs, yet they contain critical structured data. This guide outlines comprehensive strategies for extracting, preserving, and presenting tables for both human review and LLM consumption.

## 🎯 Table Types and Challenges

### Common Table Types
1. **Bordered Tables**: Clear cell boundaries with visible lines
2. **Borderless Tables**: No visible lines, rely on spacing
3. **Multi-page Tables**: Span across multiple pages
4. **Nested Tables**: Tables within tables
5. **Irregular Tables**: Merged cells, variable columns
6. **Form Tables**: Key-value pairs in table format

### Extraction Challenges
- **Layout Complexity**: Merged cells, spanning headers
- **Reading Order**: Column vs row-wise extraction
- **Formatting Preservation**: Alignment, spacing, emphasis
- **Data Type Recognition**: Numbers, dates, text, formulas
- **Cross-references**: Footnotes, annotations, references

## 🔧 Multi-Strategy Extraction System

### Strategy 1: Line-Based Extraction (Camelot)
Best for tables with clear borders:

```python
class CamelotExtractor:
    def extract_bordered_tables(self, pdf_path: Path, page_num: int):
        """Extract tables with visible lines using Camelot"""
        tables = camelot.read_pdf(
            str(pdf_path),
            pages=str(page_num),
            flavor='lattice',  # For bordered tables
            line_scale=50,     # Line detection sensitivity
            copy_text=['v'],   # Vertical text handling
            shift_text=['']    # Text shifting options
        )
        
        extracted_tables = []
        for table in tables:
            # Validate extraction quality
            if table.parsing_report['accuracy'] > 80:
                extracted_tables.append({
                    'data': table.df,
                    'accuracy': table.parsing_report['accuracy'],
                    'bbox': self._get_table_bbox(table),
                    'type': 'bordered'
                })
        
        return extracted_tables
```

### Strategy 2: Text-Based Extraction (Tabula)
Best for tables with consistent spacing:

```python
class TabulaExtractor:
    def extract_spaced_tables(self, pdf_path: Path, page_num: int):
        """Extract tables using spacing detection with Tabula"""
        # Try stream mode for borderless tables
        tables = tabula.read_pdf(
            pdf_path,
            pages=page_num,
            stream=True,      # For borderless tables
            guess=True,       # Auto-detect table areas
            multiple_tables=True,
            pandas_options={'header': None}  # Don't assume first row is header
        )
        
        extracted_tables = []
        for df in tables:
            # Clean and validate table
            cleaned_df = self._clean_table(df)
            if self._is_valid_table(cleaned_df):
                extracted_tables.append({
                    'data': cleaned_df,
                    'confidence': self._calculate_confidence(cleaned_df),
                    'type': 'spaced'
                })
        
        return extracted_tables
```

### Strategy 3: Layout-Based Extraction (pdfplumber)
Best for complex layouts and detailed control:

```python
class PDFPlumberExtractor:
    def extract_with_layout_analysis(self, pdf_path: Path, page_num: int):
        """Extract tables with detailed layout analysis"""
        with pdfplumber.open(pdf_path) as pdf:
            page = pdf.pages[page_num - 1]
            
            # Custom table detection settings
            table_settings = {
                'vertical_strategy': 'lines',
                'horizontal_strategy': 'text',
                'snap_tolerance': 3,
                'join_tolerance': 3,
                'edge_min_length': 50,
                'min_words_vertical': 3,
                'min_words_horizontal': 1,
                'text_tolerance': 3,
                'text_x_tolerance': None,
                'text_y_tolerance': None,
                'intersection_tolerance': 3,
            }
            
            tables = page.extract_tables(table_settings)
            
            extracted_tables = []
            for table_data in tables:
                # Get table metadata
                table_bbox = self._find_table_bbox(page, table_data)
                
                extracted_tables.append({
                    'data': table_data,
                    'bbox': table_bbox,
                    'cells': self._extract_cell_properties(page, table_bbox),
                    'type': 'layout_based'
                })
        
        return extracted_tables
```

### Strategy 4: Vision-Based Extraction
For complex or irregular tables:

```python
class VisionTableExtractor:
    def __init__(self):
        self.table_detector = self._load_table_detection_model()
        self.structure_recognizer = self._load_structure_model()
        
    def extract_with_vision(self, page_image: np.ndarray):
        """Extract tables using computer vision models"""
        # Detect table regions
        table_regions = self.table_detector.detect(page_image)
        
        extracted_tables = []
        for region in table_regions:
            # Crop table region
            table_image = self._crop_region(page_image, region.bbox)
            
            # Recognize table structure
            structure = self.structure_recognizer.analyze(table_image)
            
            # Extract cell contents
            cells = self._extract_cells_from_structure(table_image, structure)
            
            # Reconstruct table
            table_data = self._reconstruct_table(cells, structure)
            
            extracted_tables.append({
                'data': table_data,
                'structure': structure,
                'confidence': region.confidence,
                'type': 'vision_based'
            })
        
        return extracted_tables
```

### Strategy 5: LLM-Based Extraction
For understanding complex table semantics:

```python
class LLMTableExtractor:
    def extract_with_understanding(self, table_region, context):
        """Use LLM to understand and extract table with context"""
        prompt = f"""
        Given this table image and surrounding context:
        Context: {context}
        
        Please extract the table with the following requirements:
        1. Identify all column headers and their meanings
        2. Extract all row data maintaining relationships
        3. Handle merged cells and complex structures
        4. Identify units, currencies, or data types
        5. Note any footnotes or references
        
        Output as structured JSON with metadata.
        """
        
        result = self.llm.analyze_table(
            image=table_region,
            prompt=prompt,
            output_format='structured_json'
        )
        
        return {
            'data': result.table_data,
            'metadata': result.metadata,
            'relationships': result.identified_relationships,
            'confidence': result.confidence,
            'type': 'llm_extracted'
        }
```

## 📐 Table Format Preservation

### For LLM Consumption
Preserve spatial layout for LLM understanding:

```python
class TableFormatter:
    def format_for_llm(self, table_data):
        """Format table to preserve spatial relationships for LLM"""
        # Calculate column widths
        col_widths = self._calculate_column_widths(table_data)
        
        # Build formatted table
        formatted_lines = []
        
        # Add headers with alignment
        header_line = "|"
        separator_line = "|"
        for i, header in enumerate(table_data.columns):
            header_line += f" {header:<{col_widths[i]}} |"
            separator_line += f" {'-' * col_widths[i]} |"
        
        formatted_lines.append(header_line)
        formatted_lines.append(separator_line)
        
        # Add data rows
        for _, row in table_data.iterrows():
            row_line = "|"
            for i, value in enumerate(row):
                # Right-align numbers, left-align text
                if isinstance(value, (int, float)):
                    row_line += f" {value:>{col_widths[i]}} |"
                else:
                    row_line += f" {str(value):<{col_widths[i]}} |"
            formatted_lines.append(row_line)
        
        return "\n".join(formatted_lines)
    
    def format_as_markdown(self, table_data):
        """Convert to proper Markdown table"""
        return table_data.to_markdown(index=False)
    
    def format_as_structured_json(self, table_data, metadata):
        """Create structured JSON with full metadata"""
        return {
            'table_id': metadata.get('id'),
            'caption': metadata.get('caption'),
            'headers': table_data.columns.tolist(),
            'data': table_data.to_dict('records'),
            'metadata': {
                'num_rows': len(table_data),
                'num_cols': len(table_data.columns),
                'has_merged_cells': metadata.get('merged_cells', False),
                'spans_pages': metadata.get('multi_page', False),
                'extraction_method': metadata.get('method'),
                'confidence': metadata.get('confidence')
            }
        }
```

### Advanced Table Preservation
Handle complex table structures:

```python
class AdvancedTablePreserver:
    def preserve_complex_table(self, table_info):
        """Preserve complex table structures including merged cells"""
        preserved = {
            'structure': {
                'rows': table_info['num_rows'],
                'cols': table_info['num_cols'],
                'merged_cells': []
            },
            'cells': []
        }
        
        # Track merged cells
        for cell in table_info['cells']:
            if cell.get('rowspan', 1) > 1 or cell.get('colspan', 1) > 1:
                preserved['structure']['merged_cells'].append({
                    'row': cell['row'],
                    'col': cell['col'],
                    'rowspan': cell.get('rowspan', 1),
                    'colspan': cell.get('colspan', 1)
                })
            
            # Preserve cell properties
            preserved['cells'].append({
                'row': cell['row'],
                'col': cell['col'],
                'value': cell['value'],
                'type': self._infer_cell_type(cell['value']),
                'formatting': cell.get('formatting', {}),
                'alignment': cell.get('alignment', 'left')
            })
        
        return preserved
```

## 🔄 Table Extraction Pipeline

### Complete Pipeline Implementation
```python
class TableExtractionPipeline:
    def __init__(self):
        self.extractors = {
            'camelot': CamelotExtractor(),
            'tabula': TabulaExtractor(),
            'pdfplumber': PDFPlumberExtractor(),
            'vision': VisionTableExtractor(),
            'llm': LLMTableExtractor()
        }
        
    def extract_all_tables(self, document):
        """Extract all tables using multiple strategies"""
        all_tables = []
        
        for page_num in range(1, document.num_pages + 1):
            page_tables = []
            
            # Try each extraction method
            for method_name, extractor in self.extractors.items():
                try:
                    tables = extractor.extract(document, page_num)
                    page_tables.extend(tables)
                except Exception as e:
                    logger.warning(f"{method_name} failed on page {page_num}: {e}")
            
            # Deduplicate and merge results
            merged_tables = self._merge_table_results(page_tables)
            
            # Validate and score each table
            for table in merged_tables:
                table['quality_score'] = self._assess_table_quality(table)
                table['page'] = page_num
            
            all_tables.extend(merged_tables)
        
        return all_tables
    
    def _merge_table_results(self, tables):
        """Merge results from different extractors"""
        # Group similar tables by location
        grouped = self._group_by_location(tables)
        
        merged = []
        for group in grouped:
            if len(group) == 1:
                merged.append(group[0])
            else:
                # Merge multiple extractions of same table
                best_table = self._select_best_extraction(group)
                
                # Enhance with data from other extractions
                enhanced = self._enhance_table(best_table, group)
                merged.append(enhanced)
        
        return merged
```

## 📊 Quality Assessment

### Table Quality Metrics
```python
class TableQualityAssessor:
    def assess_table(self, table):
        """Calculate quality score for extracted table"""
        scores = {
            'completeness': self._check_completeness(table),
            'consistency': self._check_consistency(table),
            'alignment': self._check_alignment(table),
            'data_types': self._check_data_types(table),
            'structure': self._check_structure(table)
        }
        
        # Weight scores
        weights = {
            'completeness': 0.3,
            'consistency': 0.2,
            'alignment': 0.2,
            'data_types': 0.15,
            'structure': 0.15
        }
        
        overall_score = sum(
            scores[metric] * weights[metric] 
            for metric in scores
        )
        
        return {
            'overall': overall_score,
            'details': scores,
            'issues': self._identify_issues(scores)
        }
```

## 🚀 Best Practices

### 1. **Extraction Strategy Selection**
```python
def select_extraction_strategy(page_analysis):
    if page_analysis.has_visible_borders:
        return 'camelot'
    elif page_analysis.has_consistent_spacing:
        return 'tabula'
    elif page_analysis.is_complex_layout:
        return 'vision'
    else:
        return 'llm'  # Most flexible
```

### 2. **Result Validation**
```python
def validate_extracted_table(table):
    # Check for common issues
    if table.empty:
        return False
    
    # Verify reasonable dimensions
    if len(table) > 10000 or len(table.columns) > 100:
        return False
    
    # Check for data consistency
    if table.isnull().all().any():  # Any column all null
        return False
    
    return True
```

### 3. **Format Selection for Use Case**
```python
def select_output_format(use_case, table):
    if use_case == 'llm_qa':
        # Spatial format for LLM understanding
        return format_for_llm(table)
    elif use_case == 'data_analysis':
        # Structured JSON or CSV
        return table.to_json(orient='records')
    elif use_case == 'human_review':
        # HTML with styling
        return format_as_html(table)
    elif use_case == 'document_export':
        # Markdown for readability
        return table.to_markdown()
```

## 📈 Performance Optimization

### Parallel Processing
```python
async def extract_tables_parallel(document):
    tasks = []
    for page_num in range(1, document.num_pages + 1):
        task = asyncio.create_task(
            extract_page_tables(document, page_num)
        )
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    return flatten(results)
```

### Caching Strategy
```python
class TableExtractionCache:
    def get_or_extract(self, document_id, page_num):
        cache_key = f"tables:{document_id}:page:{page_num}"
        
        if cached := self.cache.get(cache_key):
            return cached
        
        tables = self.extract_tables(document_id, page_num)
        self.cache.set(cache_key, tables, ttl=86400)  # 24 hours
        
        return tables
```

---

*This comprehensive guide ensures accurate table extraction and preservation for all use cases in TORE Matrix Labs V3*