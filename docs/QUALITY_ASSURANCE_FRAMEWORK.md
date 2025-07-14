# Quality Assurance Framework for Document Parsing

## 🎯 Overview

A comprehensive quality assurance (QA) framework ensures that document parsing maintains high accuracy, catches errors early, and provides confidence in the extracted data. This framework covers automated testing, ground truth validation, regression prevention, and continuous improvement.

## 🏗️ QA Architecture

### Multi-Layer Quality Checks
```
┌─────────────────────────────────────────────┐
│         Pre-Processing Validation            │
│    (File integrity, format detection)        │
├─────────────────────────────────────────────┤
│         Processing-Time Validation           │
│    (Extraction accuracy, completeness)       │
├─────────────────────────────────────────────┤
│         Post-Processing Validation           │
│    (Structure, consistency, readability)     │
├─────────────────────────────────────────────┤
│         Human Review & Feedback              │
│    (Manual validation, corrections)          │
└─────────────────────────────────────────────┘
```

## 📊 Ground Truth Dataset

### Ground Truth Structure
```python
@dataclass
class GroundTruthDocument:
    """Represents a document with verified correct extraction"""
    document_id: str
    file_path: Path
    metadata: DocumentMetadata
    
    # Expected extraction results
    expected_text: str
    expected_elements: List[GroundTruthElement]
    expected_tables: List[GroundTruthTable]
    expected_structure: DocumentStructure
    
    # Known values for validation
    known_values: Dict[str, Any] = field(default_factory=dict)
    
    # Quality metrics
    min_acceptable_accuracy: float = 0.95
    critical_elements: List[str] = field(default_factory=list)

@dataclass
class GroundTruthElement:
    """Single element with expected properties"""
    element_id: str
    element_type: str
    text: str
    page_number: int
    bbox: Optional[BoundingBox] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Validation rules
    must_exist: bool = True
    exact_match_required: bool = True
    position_tolerance: float = 5.0  # pixels

class GroundTruthRepository:
    """Manages ground truth test documents"""
    def __init__(self, ground_truth_dir: Path):
        self.ground_truth_dir = ground_truth_dir
        self.documents = self._load_ground_truth_documents()
    
    def _load_ground_truth_documents(self) -> Dict[str, GroundTruthDocument]:
        """Load all ground truth documents from directory"""
        documents = {}
        
        for gt_file in self.ground_truth_dir.glob("*.json"):
            with open(gt_file) as f:
                gt_data = json.load(f)
            
            doc = GroundTruthDocument(**gt_data)
            documents[doc.document_id] = doc
        
        return documents
    
    def get_document(self, document_id: str) -> Optional[GroundTruthDocument]:
        return self.documents.get(document_id)
    
    def add_document(self, document: GroundTruthDocument):
        """Add new ground truth document"""
        self.documents[document.document_id] = document
        self._save_document(document)
```

### Creating Ground Truth Data
```python
class GroundTruthGenerator:
    """Helper to create ground truth from manually verified documents"""
    
    def create_from_verified_extraction(self, 
                                      document_path: Path,
                                      verified_result: ProcessingResult) -> GroundTruthDocument:
        """Create ground truth from manually verified extraction"""
        ground_truth = GroundTruthDocument(
            document_id=self._generate_document_id(document_path),
            file_path=document_path,
            metadata=self._extract_metadata(document_path),
            expected_text=verified_result.full_text,
            expected_elements=[
                self._convert_to_ground_truth_element(elem)
                for elem in verified_result.elements
            ],
            expected_tables=[
                self._convert_to_ground_truth_table(table)
                for table in verified_result.tables
            ],
            expected_structure=verified_result.structure
        )
        
        # Add known values for validation
        ground_truth.known_values = self._extract_known_values(verified_result)
        
        # Identify critical elements
        ground_truth.critical_elements = self._identify_critical_elements(verified_result)
        
        return ground_truth
    
    def _extract_known_values(self, result: ProcessingResult) -> Dict[str, Any]:
        """Extract specific values that must be found"""
        known_values = {}
        
        # Extract key numbers, dates, names, etc.
        for element in result.elements:
            if element.type == 'Title' and element.page_number == 1:
                known_values['document_title'] = element.text
            
            # Extract specific patterns
            if numbers := self._extract_numbers(element.text):
                for num in numbers:
                    if self._is_significant_number(num):
                        known_values[f'number_{len(known_values)}'] = num
        
        return known_values
```

## 🔍 Automated Validation

### Text Extraction Accuracy
```python
class TextAccuracyValidator:
    def validate_text_extraction(self, 
                               extracted: str, 
                               expected: str) -> ValidationResult:
        """Validate text extraction accuracy"""
        result = ValidationResult()
        
        # Calculate similarity metrics
        result.metrics['levenshtein_ratio'] = self._levenshtein_ratio(extracted, expected)
        result.metrics['word_accuracy'] = self._word_level_accuracy(extracted, expected)
        result.metrics['char_accuracy'] = self._character_accuracy(extracted, expected)
        
        # Check for missing content
        missing_content = self._find_missing_content(extracted, expected)
        if missing_content:
            result.add_issue(
                severity='critical',
                description=f"Missing content: {missing_content[:100]}..."
            )
        
        # Check for extra content (hallucinations)
        extra_content = self._find_extra_content(extracted, expected)
        if extra_content:
            result.add_issue(
                severity='warning',
                description=f"Extra content found: {extra_content[:100]}..."
            )
        
        # Calculate overall score
        result.score = self._calculate_overall_score(result.metrics)
        result.passed = result.score >= 0.95
        
        return result
    
    def _word_level_accuracy(self, extracted: str, expected: str) -> float:
        """Calculate word-level accuracy"""
        extracted_words = extracted.split()
        expected_words = expected.split()
        
        # Use sequence matcher for alignment
        matcher = SequenceMatcher(None, extracted_words, expected_words)
        matches = sum(block.size for block in matcher.get_matching_blocks())
        
        return matches / max(len(expected_words), 1)
```

### Table Structure Validation
```python
class TableStructureValidator:
    def validate_table(self, 
                      extracted_table: ExtractedTable,
                      expected_table: GroundTruthTable) -> ValidationResult:
        """Validate table extraction accuracy"""
        result = ValidationResult()
        
        # Check dimensions
        if (extracted_table.num_rows != expected_table.num_rows or
            extracted_table.num_cols != expected_table.num_cols):
            result.add_issue(
                severity='critical',
                description=f"Table dimensions mismatch: "
                          f"extracted {extracted_table.num_rows}x{extracted_table.num_cols}, "
                          f"expected {expected_table.num_rows}x{expected_table.num_cols}"
            )
        
        # Validate cell contents
        cell_accuracy = self._validate_cells(extracted_table, expected_table)
        result.metrics['cell_accuracy'] = cell_accuracy
        
        # Check numerical precision
        if expected_table.contains_numbers:
            num_accuracy = self._validate_numerical_values(extracted_table, expected_table)
            result.metrics['numerical_accuracy'] = num_accuracy
        
        # Validate structure preservation
        structure_score = self._validate_structure(extracted_table, expected_table)
        result.metrics['structure_score'] = structure_score
        
        result.score = self._calculate_table_score(result.metrics)
        result.passed = result.score >= 0.90
        
        return result
    
    def _validate_numerical_values(self, 
                                 extracted: ExtractedTable,
                                 expected: GroundTruthTable) -> float:
        """Validate numerical values in tables"""
        correct_count = 0
        total_count = 0
        
        for row_idx, row in enumerate(expected.data):
            for col_idx, expected_value in enumerate(row):
                if self._is_numerical(expected_value):
                    total_count += 1
                    extracted_value = extracted.data[row_idx][col_idx]
                    
                    if self._numbers_match(extracted_value, expected_value):
                        correct_count += 1
                    else:
                        logger.warning(
                            f"Numerical mismatch at ({row_idx}, {col_idx}): "
                            f"extracted '{extracted_value}', expected '{expected_value}'"
                        )
        
        return correct_count / max(total_count, 1)
```

### Reading Order Validation
```python
class ReadingOrderValidator:
    def validate_reading_order(self,
                             extracted_elements: List[Element],
                             expected_elements: List[GroundTruthElement]) -> ValidationResult:
        """Validate that elements are in correct reading order"""
        result = ValidationResult()
        
        # Match extracted to expected elements
        matches = self._match_elements(extracted_elements, expected_elements)
        
        # Check order preservation
        order_errors = []
        for i in range(len(matches) - 1):
            curr_match = matches[i]
            next_match = matches[i + 1]
            
            if curr_match and next_match:
                curr_expected_idx = expected_elements.index(curr_match[1])
                next_expected_idx = expected_elements.index(next_match[1])
                
                if next_expected_idx < curr_expected_idx:
                    order_errors.append({
                        'position': i,
                        'element': curr_match[0].text[:50],
                        'should_come_after': next_match[0].text[:50]
                    })
        
        if order_errors:
            result.add_issue(
                severity='major',
                description=f"Reading order errors found: {len(order_errors)} elements out of order",
                details=order_errors
            )
        
        result.metrics['order_accuracy'] = 1 - (len(order_errors) / max(len(matches), 1))
        result.score = result.metrics['order_accuracy']
        result.passed = result.score >= 0.95
        
        return result
```

### OCR Quality Validation
```python
class OCRQualityValidator:
    def validate_ocr_quality(self, ocr_result: OCRResult) -> ValidationResult:
        """Validate OCR extraction quality"""
        result = ValidationResult()
        
        # Check confidence scores
        low_confidence_count = sum(
            1 for word in ocr_result.words 
            if word.confidence < 0.8
        )
        
        if low_confidence_count > 0:
            result.add_issue(
                severity='warning',
                description=f"{low_confidence_count} words with low confidence (<80%)"
            )
        
        # Check for common OCR errors
        ocr_errors = self._detect_common_ocr_errors(ocr_result.text)
        if ocr_errors:
            result.add_issue(
                severity='minor',
                description=f"Potential OCR errors detected: {ocr_errors}"
            )
        
        # Validate against dictionary
        misspellings = self._check_spelling(ocr_result.text)
        if len(misspellings) > len(ocr_result.words) * 0.05:  # >5% misspelled
            result.add_issue(
                severity='major',
                description=f"High misspelling rate: {len(misspellings)} words"
            )
        
        # Calculate overall OCR quality score
        result.metrics['avg_confidence'] = np.mean([w.confidence for w in ocr_result.words])
        result.metrics['misspelling_rate'] = len(misspellings) / max(len(ocr_result.words), 1)
        
        result.score = result.metrics['avg_confidence'] * (1 - result.metrics['misspelling_rate'])
        result.passed = result.score >= 0.85
        
        return result
    
    def _detect_common_ocr_errors(self, text: str) -> List[str]:
        """Detect common OCR error patterns"""
        errors = []
        
        # Common character substitutions
        patterns = [
            (r'\brn\b', 'm'),  # rn -> m
            (r'\bcl\b', 'd'),  # cl -> d
            (r'\bI\b(?![A-Z])', 'l'),  # I -> l (not at start of sentence)
            (r'0(?=[a-zA-Z])', 'O'),  # 0 -> O before letters
            (r'(?<=[a-zA-Z])O(?=\d)', '0'),  # O -> 0 between letter and digit
        ]
        
        for pattern, replacement in patterns:
            if re.search(pattern, text):
                errors.append(f"{pattern} -> {replacement}")
        
        return errors
```

## 📈 Regression Testing

### Test Suite Structure
```python
class ParsingRegressionTestSuite:
    def __init__(self, ground_truth_repo: GroundTruthRepository):
        self.ground_truth_repo = ground_truth_repo
        self.test_results = []
    
    def run_full_regression_test(self) -> TestReport:
        """Run regression tests on all ground truth documents"""
        report = TestReport()
        
        for doc_id, ground_truth in self.ground_truth_repo.documents.items():
            logger.info(f"Testing document: {doc_id}")
            
            try:
                # Parse document
                result = self._parse_document(ground_truth.file_path)
                
                # Run all validators
                validations = self._run_validators(result, ground_truth)
                
                # Record results
                test_result = TestResult(
                    document_id=doc_id,
                    validations=validations,
                    passed=all(v.passed for v in validations),
                    timestamp=datetime.now()
                )
                
                report.add_result(test_result)
                
            except Exception as e:
                report.add_error(doc_id, str(e))
        
        return report
    
    def run_targeted_test(self, 
                         component: str,
                         documents: List[str] = None) -> TestReport:
        """Run tests targeting specific component"""
        if documents is None:
            documents = list(self.ground_truth_repo.documents.keys())
        
        report = TestReport()
        
        for doc_id in documents:
            ground_truth = self.ground_truth_repo.get_document(doc_id)
            if not ground_truth:
                continue
            
            # Parse with specific component
            result = self._parse_with_component(ground_truth.file_path, component)
            
            # Validate
            validation = self._validate_component(result, ground_truth, component)
            
            report.add_result(TestResult(
                document_id=doc_id,
                validations=[validation],
                passed=validation.passed,
                component=component
            ))
        
        return report
```

### Continuous Integration Tests
```python
# tests/test_parsing_quality.py
import pytest
from pathlib import Path
from torematrix.qa import ParsingRegressionTestSuite, GroundTruthRepository

class TestParsingQuality:
    @pytest.fixture
    def test_suite(self):
        ground_truth_dir = Path(__file__).parent / "ground_truth"
        repo = GroundTruthRepository(ground_truth_dir)
        return ParsingRegressionTestSuite(repo)
    
    def test_text_extraction_accuracy(self, test_suite):
        """Test text extraction meets accuracy requirements"""
        report = test_suite.run_targeted_test('text_extraction')
        
        assert report.overall_pass_rate >= 0.95, \
            f"Text extraction accuracy {report.overall_pass_rate} below threshold"
        
        # Check specific metrics
        for result in report.results:
            text_validation = result.get_validation('text_accuracy')
            assert text_validation.metrics['word_accuracy'] >= 0.98
    
    def test_table_extraction_accuracy(self, test_suite):
        """Test table extraction accuracy"""
        report = test_suite.run_targeted_test('table_extraction')
        
        for result in report.results:
            table_validations = result.get_validations('table_structure')
            for validation in table_validations:
                assert validation.metrics['cell_accuracy'] >= 0.95
                assert validation.metrics.get('numerical_accuracy', 1.0) >= 0.99
    
    def test_ocr_quality(self, test_suite):
        """Test OCR quality for scanned documents"""
        scanned_docs = ['scanned_invoice', 'scanned_report', 'handwritten_form']
        report = test_suite.run_targeted_test('ocr', documents=scanned_docs)
        
        for result in report.results:
            ocr_validation = result.get_validation('ocr_quality')
            assert ocr_validation.metrics['avg_confidence'] >= 0.85
            assert ocr_validation.metrics['misspelling_rate'] <= 0.05
    
    @pytest.mark.slow
    def test_full_regression(self, test_suite):
        """Run full regression test suite"""
        report = test_suite.run_full_regression_test()
        
        # Generate detailed report
        report.save_html_report("test_results/regression_report.html")
        
        assert report.overall_pass_rate >= 0.95
        assert len(report.errors) == 0
```

## 🎨 Visual Validation Tools

### Visual Diff Generator
```python
class VisualDiffGenerator:
    def generate_visual_diff(self,
                           extracted: ProcessingResult,
                           expected: GroundTruthDocument) -> VisualDiff:
        """Generate visual comparison of extraction results"""
        diff = VisualDiff()
        
        # Text diff with highlighting
        text_diff = self._generate_text_diff(
            extracted.full_text,
            expected.expected_text
        )
        diff.text_diff_html = text_diff
        
        # Element-by-element comparison
        element_diff = self._generate_element_diff(
            extracted.elements,
            expected.expected_elements
        )
        diff.element_diff_html = element_diff
        
        # Visual overlay on PDF
        if extracted.source_pdf:
            overlay = self._generate_pdf_overlay(
                extracted.source_pdf,
                extracted.elements,
                expected.expected_elements
            )
            diff.pdf_overlay = overlay
        
        return diff
    
    def _generate_pdf_overlay(self, 
                            pdf_path: Path,
                            extracted_elements: List[Element],
                            expected_elements: List[GroundTruthElement]) -> bytes:
        """Create PDF with visual overlay showing differences"""
        import fitz  # PyMuPDF
        
        doc = fitz.open(pdf_path)
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Draw extracted elements in green
            for elem in extracted_elements:
                if elem.page_number == page_num + 1 and elem.bbox:
                    rect = fitz.Rect(elem.bbox)
                    page.draw_rect(rect, color=(0, 1, 0), width=1)
            
            # Draw missing elements in red
            for expected in expected_elements:
                if expected.page_number == page_num + 1:
                    if not self._element_found(expected, extracted_elements):
                        if expected.bbox:
                            rect = fitz.Rect(expected.bbox)
                            page.draw_rect(rect, color=(1, 0, 0), width=2)
        
        return doc.write()
```

## 📊 Quality Metrics Dashboard

### Metrics Collection
```python
class QualityMetricsCollector:
    def __init__(self):
        self.metrics_db = MetricsDatabase()
    
    def collect_parsing_metrics(self, 
                              document_id: str,
                              result: ProcessingResult,
                              validations: List[ValidationResult]):
        """Collect and store quality metrics"""
        metrics = {
            'document_id': document_id,
            'timestamp': datetime.now(),
            'processing_time': result.processing_time,
            'num_elements': len(result.elements),
            'num_tables': len(result.tables),
            'validations': {}
        }
        
        # Aggregate validation scores
        for validation in validations:
            metrics['validations'][validation.name] = {
                'score': validation.score,
                'passed': validation.passed,
                'issues': len(validation.issues)
            }
        
        # Calculate overall quality score
        metrics['overall_quality_score'] = np.mean([
            v.score for v in validations
        ])
        
        # Store in database
        self.metrics_db.insert(metrics)
    
    def get_quality_trends(self, 
                         days: int = 30) -> QualityTrends:
        """Get quality trends over time"""
        since = datetime.now() - timedelta(days=days)
        metrics = self.metrics_db.query(since=since)
        
        return QualityTrends(
            average_quality=self._calculate_average_quality(metrics),
            quality_by_component=self._group_by_component(metrics),
            failure_patterns=self._identify_failure_patterns(metrics),
            improvement_areas=self._suggest_improvements(metrics)
        )
```

## 🔧 Configuration

### QA Configuration
```yaml
quality_assurance:
  ground_truth:
    directory: "tests/ground_truth"
    auto_update: false
    
  validation:
    text_accuracy_threshold: 0.95
    table_accuracy_threshold: 0.90
    ocr_confidence_threshold: 0.85
    
  regression_testing:
    run_on_commit: true
    full_test_schedule: "0 2 * * *"  # Daily at 2 AM
    
  metrics:
    collect_metrics: true
    retention_days: 90
    dashboard_update_interval: 300  # 5 minutes
    
  visual_validation:
    generate_diffs: true
    save_artifacts: true
    artifact_retention_days: 7
```

## 🚀 Best Practices

### 1. **Continuous Improvement**
```python
def analyze_failures_and_improve(test_report: TestReport):
    """Analyze test failures to improve parsing"""
    failure_patterns = defaultdict(list)
    
    for result in test_report.failed_results:
        for validation in result.validations:
            if not validation.passed:
                failure_patterns[validation.failure_reason].append({
                    'document': result.document_id,
                    'details': validation.issues
                })
    
    # Generate improvement recommendations
    for pattern, failures in failure_patterns.items():
        if len(failures) > 3:  # Repeated failure pattern
            create_improvement_ticket(pattern, failures)
```

### 2. **Test Data Management**
```python
class TestDataManager:
    def add_edge_case(self, document_path: Path, issue_description: str):
        """Add new edge case to test suite"""
        # Process document to create ground truth
        result = process_document_with_manual_review(document_path)
        
        # Create ground truth entry
        ground_truth = create_ground_truth(document_path, result)
        ground_truth.tags.append('edge_case')
        ground_truth.notes = issue_description
        
        # Add to repository
        self.ground_truth_repo.add_document(ground_truth)
```

### 3. **Performance Benchmarking**
```python
@pytest.mark.benchmark
def test_parsing_performance(benchmark, test_document):
    """Benchmark parsing performance"""
    result = benchmark(parse_document, test_document)
    
    # Check performance requirements
    assert benchmark.stats['mean'] < 5.0  # <5 seconds average
    assert benchmark.stats['max'] < 10.0  # <10 seconds worst case
```

---

*This comprehensive QA framework ensures high-quality, reliable document parsing in TORE Matrix Labs V3*