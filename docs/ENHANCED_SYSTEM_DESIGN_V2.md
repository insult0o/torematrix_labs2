# TORE Matrix Labs V3 - Enhanced System Design V2

## 📋 Document Version
- **Version**: 2.0
- **Updated**: Post PDF-to-LLM Best Practices Analysis
- **Previous**: COMPLETE_SYSTEM_DESIGN.md (V1)

## 🎯 Enhanced System Overview

TORE Matrix Labs V3 is an enterprise-grade document processing platform that implements state-of-the-art PDF-to-LLM pipeline practices. This enhanced design incorporates advanced parsing, OCR, layout analysis, and quality assurance based on industry best practices.

### Core Enhancements
1. **Multi-Strategy Parsing**: Fallback system with 4+ PDF libraries
2. **Comprehensive OCR**: Multiple engines with preprocessing pipeline
3. **Advanced Table Extraction**: Multiple extractors with spatial preservation
4. **Layout Intelligence**: Reading order, multi-column, structure detection
5. **LLM-Assisted Parsing**: Context-aware extraction with custom instructions
6. **Quality Assurance**: Ground truth validation and accuracy metrics
7. **Performance Optimization**: Caching, incremental processing, parallel execution
8. **Hybrid Search**: Vector + keyword search with fuzzy matching

## 🏗️ Enhanced Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Input Layer                               │
│           (Multi-format Documents + Quality Checks)              │
├─────────────────────────────────────────────────────────────────┤
│                    Preprocessing Layer                           │
│     (Format Detection, OCR Decision, Image Enhancement)          │
├─────────────────────────────────────────────────────────────────┤
│                    Multi-Parser Layer                            │
│   (Unstructured + pdfplumber + PyMuPDF + pdfminer + LlamaParse) │
├─────────────────────────────────────────────────────────────────┤
│                    Analysis Layer                                │
│     (Layout Analysis, Table Extraction, Form Detection)          │
├─────────────────────────────────────────────────────────────────┤
│                    Enhancement Layer                             │
│        (LLM Processing, Structure Correction, QA)                │
├─────────────────────────────────────────────────────────────────┤
│                    Storage Layer                                 │
│      (Multi-level Cache + Vector DB + Document Store)            │
├─────────────────────────────────────────────────────────────────┤
│                    Export Layer                                  │
│          (RAG JSON + Fine-tune Text + Custom Formats)           │
└─────────────────────────────────────────────────────────────────┘
```

## 📚 Enhanced Document Processing Pipeline

### Phase 1: Document Analysis and Routing
```python
class DocumentAnalyzer:
    def analyze(self, file_path: Path) -> DocumentProfile:
        """Analyze document to determine optimal processing strategy"""
        profile = DocumentProfile()
        
        # Check if PDF is scanned or native text
        profile.is_scanned = self._detect_scanned_pdf(file_path)
        
        # Detect document characteristics
        profile.has_tables = self._detect_tables(file_path)
        profile.has_forms = self._detect_forms(file_path)
        profile.has_multiple_columns = self._detect_columns(file_path)
        profile.complexity_score = self._calculate_complexity(file_path)
        
        # Select optimal parser strategy
        profile.recommended_parsers = self._select_parsers(profile)
        
        return profile
```

### Phase 2: Multi-Library Parsing System
```python
class MultiParserSystem:
    parsers = {
        'unstructured': UnstructuredParser(),
        'pdfplumber': PDFPlumberParser(),
        'pymupdf': PyMuPDFParser(),
        'pdfminer': PDFMinerParser(),
        'llamaparse': LlamaParseParser()
    }
    
    def parse_with_fallback(self, file_path: Path, profile: DocumentProfile):
        results = []
        
        for parser_name in profile.recommended_parsers:
            try:
                parser = self.parsers[parser_name]
                result = parser.parse(file_path)
                results.append(result)
                
                # If high-confidence result, can return early
                if result.confidence > 0.95:
                    return result
                    
            except Exception as e:
                logger.warning(f"Parser {parser_name} failed: {e}")
                continue
        
        # Merge results from multiple parsers
        return self._merge_results(results)
```

### Phase 3: OCR Pipeline
```python
class OCRPipeline:
    def process_scanned_document(self, file_path: Path):
        # 1. Convert PDF to images
        images = self._pdf_to_images(file_path)
        
        # 2. Preprocess each image
        processed_images = []
        for img in images:
            img = self._detect_and_correct_rotation(img)
            img = self._deskew(img)
            img = self._remove_noise(img)
            img = self._enhance_contrast(img)
            img = self._binarize(img)
            processed_images.append(img)
        
        # 3. Run OCR with multiple engines
        ocr_results = []
        
        # Try Tesseract
        tesseract_result = self._run_tesseract(processed_images)
        ocr_results.append(tesseract_result)
        
        # Try PaddleOCR for comparison
        paddle_result = self._run_paddle_ocr(processed_images)
        ocr_results.append(paddle_result)
        
        # Optionally use cloud services
        if self.config.use_cloud_ocr:
            cloud_result = self._run_cloud_ocr(processed_images)
            ocr_results.append(cloud_result)
        
        # 4. Merge and validate OCR results
        final_text = self._merge_ocr_results(ocr_results)
        
        # 5. Post-process OCR text
        final_text = self._correct_common_ocr_errors(final_text)
        final_text = self._restore_layout(final_text)
        
        return final_text
```

### Phase 4: Table Extraction System
```python
class TableExtractionSystem:
    def extract_tables(self, document):
        tables = []
        
        # Strategy 1: Line-based extraction (Camelot)
        if document.has_visible_table_lines:
            camelot_tables = self._extract_with_camelot(document)
            tables.extend(camelot_tables)
        
        # Strategy 2: Text-based extraction (Tabula)
        tabula_tables = self._extract_with_tabula(document)
        tables.extend(tabula_tables)
        
        # Strategy 3: Layout-based extraction (pdfplumber)
        plumber_tables = self._extract_with_pdfplumber(document)
        tables.extend(plumber_tables)
        
        # Strategy 4: Vision-based extraction for borderless tables
        if not tables or self._detect_borderless_tables(document):
            vision_tables = self._extract_with_vision_model(document)
            tables.extend(vision_tables)
        
        # Deduplicate and merge similar tables
        tables = self._deduplicate_tables(tables)
        
        # Format for LLM consumption
        formatted_tables = []
        for table in tables:
            # Preserve spatial layout with aligned columns
            spatial_format = self._format_table_spatial(table)
            
            # Also create structured formats
            csv_format = self._format_table_csv(table)
            html_format = self._format_table_html(table)
            markdown_format = self._format_table_markdown(table)
            
            formatted_tables.append({
                'spatial': spatial_format,  # For LLM understanding
                'csv': csv_format,          # For data analysis
                'html': html_format,        # For web display
                'markdown': markdown_format  # For documentation
            })
        
        return formatted_tables
```

### Phase 5: Layout Analysis
```python
class LayoutAnalyzer:
    def analyze_layout(self, document):
        # 1. Detect page structure
        layout = PageLayout()
        
        # 2. Column detection
        columns = self._detect_columns(document)
        layout.columns = columns
        
        # 3. Reading order determination
        if len(columns) > 1:
            reading_order = self._determine_reading_order(columns)
        else:
            reading_order = self._simple_top_to_bottom_order(document)
        
        layout.reading_order = reading_order
        
        # 4. Section identification
        sections = self._identify_sections(document)
        layout.sections = sections
        
        # 5. Special region detection
        layout.headers = self._detect_headers(document)
        layout.footers = self._detect_footers(document)
        layout.sidebars = self._detect_sidebars(document)
        layout.footnotes = self._detect_footnotes(document)
        
        # 6. Use LayoutLM for complex layouts
        if document.complexity_score > 0.7:
            layoutlm_results = self._apply_layoutlm(document)
            layout = self._merge_with_layoutlm(layout, layoutlm_results)
        
        return layout
```

### Phase 6: LLM-Assisted Enhancement
```python
class LLMEnhancementPipeline:
    def enhance_with_llm(self, document, custom_instructions=None):
        # 1. Prepare document for LLM processing
        llm_input = self._prepare_llm_input(document)
        
        # 2. Generate parsing instructions
        if custom_instructions:
            instructions = custom_instructions
        else:
            instructions = self._generate_instructions(document.type)
        
        # 3. Use LlamaParse for intelligent extraction
        llamaparse_result = LlamaParse.parse(
            document=llm_input,
            instructions=instructions,
            output_format='markdown',
            extract_tables=True,
            extract_images=True
        )
        
        # 4. Use vision-language model for complex elements
        if document.has_complex_layouts:
            vision_results = self._apply_vision_model(document)
            llamaparse_result = self._merge_vision_results(
                llamaparse_result, 
                vision_results
            )
        
        # 5. Generate structured output
        structured_elements = self._structure_elements(llamaparse_result)
        
        # 6. Validate and correct with LLM
        validated_elements = self._validate_with_llm(structured_elements)
        
        return validated_elements
```

### Phase 7: Intelligent Chunking
```python
class IntelligentChunker:
    def chunk_document(self, document):
        chunks = []
        
        # 1. Parse markdown structure if available
        if document.format == 'markdown':
            structure = self._parse_markdown_structure(document.content)
        else:
            structure = self._infer_structure(document)
        
        # 2. Create semantic chunks
        for section in structure.sections:
            # Keep sections together if under token limit
            if self._count_tokens(section) < self.max_chunk_tokens:
                chunks.append(self._create_chunk(section))
            else:
                # Split large sections intelligently
                sub_chunks = self._split_section(section)
                chunks.extend(sub_chunks)
        
        # 3. Preserve special elements
        for table in document.tables:
            # Never split tables
            chunks.append(self._create_table_chunk(table))
        
        for list_item in document.lists:
            # Keep lists together when possible
            chunks.append(self._create_list_chunk(list_item))
        
        # 4. Add metadata to each chunk
        for i, chunk in enumerate(chunks):
            chunk.metadata = {
                'chunk_id': f"{document.id}_chunk_{i}",
                'document_id': document.id,
                'section': chunk.section_title,
                'page_numbers': chunk.page_range,
                'chunk_type': chunk.type,
                'prev_chunk': chunks[i-1].id if i > 0 else None,
                'next_chunk': chunks[i+1].id if i < len(chunks)-1 else None
            }
        
        return chunks
```

### Phase 8: Caching System
```python
class MultiLevelCache:
    def __init__(self):
        self.memory_cache = TTLCache(maxsize=1000, ttl=3600)
        self.disk_cache = DiskCache('/var/cache/torematrix')
        self.redis_cache = Redis() if self.config.use_redis else None
    
    def cache_document_results(self, document_id, processing_stage, results):
        # Generate cache key
        cache_key = f"{document_id}:{processing_stage}:{self._hash_content(results)}"
        
        # Store in multiple cache levels
        self.memory_cache[cache_key] = results
        self.disk_cache.set(cache_key, results)
        
        if self.redis_cache:
            self.redis_cache.setex(
                cache_key, 
                timedelta(days=7), 
                pickle.dumps(results)
            )
    
    def get_cached_results(self, document_id, processing_stage):
        # Check memory first (fastest)
        cache_key_pattern = f"{document_id}:{processing_stage}:*"
        
        if result := self._check_memory_cache(cache_key_pattern):
            return result
        
        # Check disk cache
        if result := self._check_disk_cache(cache_key_pattern):
            # Promote to memory cache
            self.memory_cache[cache_key] = result
            return result
        
        # Check Redis (if available)
        if self.redis_cache:
            if result := self._check_redis_cache(cache_key_pattern):
                # Promote to faster caches
                self.memory_cache[cache_key] = result
                self.disk_cache.set(cache_key, result)
                return result
        
        return None
```

### Phase 9: Quality Assurance
```python
class ParsingQualityAssurance:
    def __init__(self):
        self.ground_truth = self._load_ground_truth_dataset()
        self.metrics = ParsingMetrics()
    
    def validate_parsing_result(self, document, parsed_result):
        qa_report = QAReport()
        
        # 1. Text extraction accuracy
        if document.id in self.ground_truth:
            text_accuracy = self._calculate_text_accuracy(
                parsed_result.text,
                self.ground_truth[document.id].text
            )
            qa_report.text_accuracy = text_accuracy
        
        # 2. Table structure preservation
        table_scores = []
        for table in parsed_result.tables:
            score = self._validate_table_structure(table)
            table_scores.append(score)
        qa_report.table_accuracy = np.mean(table_scores)
        
        # 3. Reading order correctness
        order_score = self._validate_reading_order(parsed_result)
        qa_report.reading_order_score = order_score
        
        # 4. Metadata completeness
        metadata_score = self._validate_metadata(parsed_result)
        qa_report.metadata_score = metadata_score
        
        # 5. Known value verification
        known_values_found = self._check_known_values(
            parsed_result,
            self.ground_truth[document.id].known_values
        )
        qa_report.known_values_score = known_values_found
        
        # 6. Visual diff for debugging
        if qa_report.overall_score < 0.9:
            visual_diff = self._generate_visual_diff(
                parsed_result,
                self.ground_truth[document.id]
            )
            qa_report.visual_diff = visual_diff
        
        return qa_report
```

### Phase 10: Hybrid Search
```python
class HybridSearchSystem:
    def __init__(self):
        self.vector_index = VectorIndex()
        self.bm25_index = BM25Index()
        self.fuzzy_matcher = FuzzyMatcher()
    
    def search(self, query, filters=None):
        # 1. Vector search for semantic similarity
        vector_results = self.vector_index.search(
            query_embedding=self._embed_query(query),
            top_k=50
        )
        
        # 2. BM25 keyword search for exact matches
        keyword_results = self.bm25_index.search(
            query=query,
            top_k=50
        )
        
        # 3. Fuzzy search for OCR errors and variations
        fuzzy_results = self.fuzzy_matcher.search(
            query=query,
            max_distance=2,
            top_k=20
        )
        
        # 4. Combine and re-rank results
        combined_results = self._combine_results(
            vector_results,
            keyword_results,
            fuzzy_results,
            weights={'vector': 0.5, 'keyword': 0.3, 'fuzzy': 0.2}
        )
        
        # 5. Apply metadata filters
        if filters:
            combined_results = self._apply_filters(combined_results, filters)
        
        # 6. Re-rank with cross-encoder if available
        if self.config.use_reranking:
            combined_results = self._rerank_with_cross_encoder(
                query, 
                combined_results
            )
        
        return combined_results
```

## 📊 Enhanced Data Models

### Unified Element Model V2
```python
@dataclass
class UnifiedElementV2:
    # Core fields (unchanged)
    id: str
    type: ElementType
    text: str
    
    # Enhanced metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Parsing provenance
    parser_source: str  # Which parser extracted this
    parser_confidence: float  # Confidence score
    alternate_texts: List[str]  # From other parsers
    
    # OCR-specific fields
    ocr_confidence: Optional[float] = None
    ocr_language: Optional[str] = None
    preprocessing_applied: List[str] = field(default_factory=list)
    
    # Layout information
    reading_order: int
    column_number: Optional[int] = None
    section_hierarchy: List[str] = field(default_factory=list)
    
    # Quality assurance
    qa_status: str = "pending"  # pending, validated, corrected
    qa_score: Optional[float] = None
    manual_corrections: List[Edit] = field(default_factory=list)
    
    # Relationships
    parent_id: Optional[str] = None
    children: List[str] = field(default_factory=list)
    related_elements: List[str] = field(default_factory=list)
    
    # Caching
    cache_key: Optional[str] = None
    last_processed: Optional[datetime] = None
```

### Document Profile Model
```python
@dataclass
class DocumentProfile:
    # Document characteristics
    is_scanned: bool
    has_tables: bool
    has_forms: bool
    has_multiple_columns: bool
    has_images: bool
    has_mathematical_formulas: bool
    
    # Complexity metrics
    complexity_score: float
    layout_complexity: float
    text_density: float
    
    # Processing recommendations
    recommended_parsers: List[str]
    recommended_ocr_settings: Dict[str, Any]
    recommended_chunk_size: int
    
    # Quality metrics
    expected_accuracy: float
    processing_time_estimate: float
```

## 🚀 Performance Optimizations

### Parallel Processing
```python
class ParallelProcessor:
    def process_document_batch(self, documents: List[Path]):
        with ProcessPoolExecutor(max_workers=cpu_count()) as executor:
            # Submit all documents for processing
            futures = {
                executor.submit(self.process_single_document, doc): doc
                for doc in documents
            }
            
            # Process results as they complete
            for future in as_completed(futures):
                document = futures[future]
                try:
                    result = future.result()
                    yield document, result
                except Exception as e:
                    logger.error(f"Failed to process {document}: {e}")
                    yield document, None
```

### GPU Acceleration
```python
class GPUAcceleratedOCR:
    def __init__(self):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.ocr_model = self._load_gpu_model()
    
    def batch_ocr(self, images: List[np.ndarray]):
        # Process images in batches on GPU
        batch_size = 32
        results = []
        
        for i in range(0, len(images), batch_size):
            batch = images[i:i+batch_size]
            batch_tensor = self._images_to_tensor(batch).to(self.device)
            
            with torch.no_grad():
                ocr_output = self.ocr_model(batch_tensor)
                texts = self._decode_output(ocr_output)
                results.extend(texts)
        
        return results
```

## 📈 Monitoring and Observability

### Processing Metrics
```python
class ProcessingMetrics:
    def __init__(self):
        self.prometheus_client = PrometheusClient()
        
    def record_processing_time(self, stage: str, duration: float):
        self.prometheus_client.histogram(
            'document_processing_duration_seconds',
            duration,
            labels={'stage': stage}
        )
    
    def record_parsing_accuracy(self, parser: str, accuracy: float):
        self.prometheus_client.gauge(
            'parsing_accuracy_score',
            accuracy,
            labels={'parser': parser}
        )
    
    def record_cache_hit_rate(self, cache_level: str, hit_rate: float):
        self.prometheus_client.gauge(
            'cache_hit_rate',
            hit_rate,
            labels={'level': cache_level}
        )
```

## 🔄 Updated Processing Flow

1. **Document Intake** → Profile Analysis → Parser Selection
2. **Multi-Parser Execution** → Result Merging → Confidence Scoring
3. **OCR Pipeline** (if needed) → Preprocessing → Multi-Engine OCR → Post-processing
4. **Layout Analysis** → Column Detection → Reading Order → Structure Recognition
5. **Table Extraction** → Multi-Strategy Extraction → Format Preservation
6. **LLM Enhancement** → Custom Instructions → Context-Aware Parsing
7. **Quality Assurance** → Accuracy Validation → Visual Verification
8. **Intelligent Chunking** → Semantic Segmentation → Metadata Addition
9. **Caching** → Multi-Level Storage → Incremental Updates
10. **Export** → RAG JSON / Fine-tune Text / Custom Formats

## 🎯 Implementation Priorities

### Phase 1: Foundation Enhancement (Weeks 1-2)
- Implement multi-parser system (#41)
- Set up caching infrastructure (#48)
- Create QA framework (#49)

### Phase 2: OCR and Layout (Weeks 3-4)
- Build OCR pipeline (#42)
- Implement layout analysis (#44)
- Add table extraction (#43)

### Phase 3: Intelligence Layer (Weeks 5-6)
- Integrate LLM-assisted parsing (#45)
- Implement intelligent chunking (#47)
- Add forms extraction (#46)

### Phase 4: Search and Export (Weeks 7-8)
- Build hybrid search system (#50)
- Enhance export formats
- Performance optimization

### Phase 5: Polish and Scale (Weeks 9-10)
- Complete testing suite
- Performance benchmarking
- Documentation and deployment

---

*This enhanced design incorporates all PDF-to-LLM best practices for maximum accuracy and maintainability*