"""Tests for semantic role classification."""

import pytest
from unittest.mock import Mock, patch

from src.torematrix.core.processing.metadata.extractors.semantic import (
    SemanticRoleExtractor,
    RuleBasedClassifier,
    SemanticRole,
    SemanticConfig,
    ClassificationResult
)
from src.torematrix.core.models.element import UnifiedElement
from src.torematrix.core.models.metadata import ElementMetadata


@pytest.fixture
def semantic_config():
    """Create test semantic configuration."""
    return SemanticConfig(
        enable_ml_classification=True,
        enable_rule_based_classification=True,
        confidence_threshold=0.6,
        max_title_length=200,
        max_caption_length=500,
        min_paragraph_length=50
    )


@pytest.fixture
def sample_elements():
    """Create sample elements for semantic classification."""
    elements = []
    
    # Title element
    title = UnifiedElement(
        id="title_1",
        type="Title",
        text="DOCUMENT TITLE IN ALL CAPS",
        metadata=ElementMetadata(confidence=0.95, page_number=1)
    )
    elements.append(title)
    
    # Heading element
    heading = UnifiedElement(
        id="heading_1",
        type="Text",
        text="1. Introduction",
        metadata=ElementMetadata(confidence=0.9, page_number=1)
    )
    elements.append(heading)
    
    # Paragraph element
    paragraph = UnifiedElement(
        id="para_1",
        type="Text",
        text="This is a long paragraph with sufficient text content to be classified as a paragraph. It contains multiple sentences and provides detailed information about the topic.",
        metadata=ElementMetadata(confidence=0.85, page_number=1)
    )
    elements.append(paragraph)
    
    # Figure caption
    caption = UnifiedElement(
        id="caption_1",
        type="Text",
        text="Figure 1: Sample diagram showing the system architecture",
        metadata=ElementMetadata(confidence=0.8, page_number=1)
    )
    elements.append(caption)
    
    # List item
    list_item = UnifiedElement(
        id="list_1",
        type="ListItem",
        text="• First bullet point in the list",
        metadata=ElementMetadata(confidence=0.75, page_number=1)
    )
    elements.append(list_item)
    
    # Date metadata
    date_elem = UnifiedElement(
        id="date_1",
        type="Text",
        text="2024-01-15",
        metadata=ElementMetadata(confidence=0.7, page_number=1)
    )
    elements.append(date_elem)
    
    # Footer
    footer = UnifiedElement(
        id="footer_1",
        type="Text",
        text="© 2024 All rights reserved",
        metadata=ElementMetadata(confidence=0.6, page_number=1)
    )
    elements.append(footer)
    
    return elements


class TestSemanticRoleExtractor:
    """Test cases for SemanticRoleExtractor."""
    
    def test_init(self, semantic_config):
        """Test extractor initialization."""
        extractor = SemanticRoleExtractor(semantic_config)
        
        assert extractor.config == semantic_config
        assert extractor.rule_classifier is not None
        assert extractor.ml_classifier is not None
    
    @pytest.mark.asyncio
    async def test_extract_semantic_roles(self, semantic_config, sample_elements):
        """Test semantic role extraction for multiple elements."""
        extractor = SemanticRoleExtractor(semantic_config)
        context = {"total_elements": len(sample_elements)}
        
        roles = await extractor.extract_semantic_roles(sample_elements, context)
        
        assert isinstance(roles, dict)
        assert len(roles) == len(sample_elements)
        
        # Check that all elements got classified
        for element in sample_elements:
            assert element.id in roles
            assert isinstance(roles[element.id], SemanticRole)
    
    @pytest.mark.asyncio
    async def test_title_classification(self, semantic_config, sample_elements):
        """Test title classification."""
        extractor = SemanticRoleExtractor(semantic_config)
        title_element = sample_elements[0]  # Title element
        
        roles = await extractor.extract_semantic_roles([title_element], {})
        
        assert roles[title_element.id] == SemanticRole.TITLE
    
    @pytest.mark.asyncio
    async def test_caption_classification(self, semantic_config, sample_elements):
        """Test caption classification."""
        extractor = SemanticRoleExtractor(semantic_config)
        caption_element = sample_elements[3]  # Caption element
        
        roles = await extractor.extract_semantic_roles([caption_element], {})
        
        assert roles[caption_element.id] in [SemanticRole.FIGURE_CAPTION, SemanticRole.CAPTION]
    
    @pytest.mark.asyncio
    async def test_list_item_classification(self, semantic_config, sample_elements):
        """Test list item classification."""
        extractor = SemanticRoleExtractor(semantic_config)
        list_element = sample_elements[4]  # List item element
        
        roles = await extractor.extract_semantic_roles([list_element], {})
        
        assert roles[list_element.id] == SemanticRole.LIST_ITEM
    
    @pytest.mark.asyncio
    async def test_date_classification(self, semantic_config, sample_elements):
        """Test date classification."""
        extractor = SemanticRoleExtractor(semantic_config)
        date_element = sample_elements[5]  # Date element
        
        roles = await extractor.extract_semantic_roles([date_element], {})
        
        assert roles[date_element.id] == SemanticRole.DATE
    
    @pytest.mark.asyncio
    async def test_low_confidence_threshold(self, sample_elements):
        """Test behavior with low confidence threshold."""
        config = SemanticConfig(confidence_threshold=0.95)  # Very high threshold
        extractor = SemanticRoleExtractor(config)
        
        roles = await extractor.extract_semantic_roles(sample_elements, {})
        
        # Should default to body text for low confidence classifications
        body_text_count = sum(1 for role in roles.values() if role == SemanticRole.BODY_TEXT)
        assert body_text_count > 0
    
    def test_enhance_context(self, semantic_config, sample_elements):
        """Test context enhancement."""
        extractor = SemanticRoleExtractor(semantic_config)
        base_context = {"language": "en"}
        
        enhanced = extractor._enhance_context(sample_elements, base_context)
        
        assert "element_type_counts" in enhanced
        assert "total_elements" in enhanced
        assert "table_elements" in enhanced
        assert "figure_elements" in enhanced
        assert enhanced["total_elements"] == len(sample_elements)
        assert "language" in enhanced  # Original context preserved
    
    def test_combine_results_agreement(self, semantic_config):
        """Test combining results when ML and rules agree."""
        extractor = SemanticRoleExtractor(semantic_config)
        
        ml_result = ClassificationResult(
            role=SemanticRole.TITLE,
            confidence=0.8,
            method="ml",
            metadata={}
        )
        
        rule_result = ClassificationResult(
            role=SemanticRole.TITLE,
            confidence=0.7,
            method="rules",
            metadata={}
        )
        
        combined = extractor._combine_results(ml_result, rule_result)
        
        assert combined.role == SemanticRole.TITLE
        assert combined.confidence > 0.7  # Should be boosted for agreement
        assert combined.method == "combined"
        assert combined.metadata["agreement"] is True
    
    def test_combine_results_disagreement(self, semantic_config):
        """Test combining results when ML and rules disagree."""
        extractor = SemanticRoleExtractor(semantic_config)
        
        ml_result = ClassificationResult(
            role=SemanticRole.TITLE,
            confidence=0.9,
            method="ml",
            metadata={}
        )
        
        rule_result = ClassificationResult(
            role=SemanticRole.HEADING,
            confidence=0.7,
            method="rules",
            metadata={}
        )
        
        combined = extractor._combine_results(ml_result, rule_result)
        
        assert combined.role == SemanticRole.TITLE  # Higher confidence wins
        assert combined.confidence < 0.9  # Should be penalized for disagreement
        assert combined.method == "ml_priority"
        assert combined.metadata["agreement"] is False
    
    def test_combine_results_single_result(self, semantic_config):
        """Test combining results when only one is available."""
        extractor = SemanticRoleExtractor(semantic_config)
        
        ml_result = ClassificationResult(
            role=SemanticRole.TITLE,
            confidence=0.8,
            method="ml",
            metadata={}
        )
        
        # Only ML result
        combined = extractor._combine_results(ml_result, None)
        assert combined == ml_result
        
        # Only rule result
        combined = extractor._combine_results(None, ml_result)
        assert combined == ml_result
        
        # No results
        combined = extractor._combine_results(None, None)
        assert combined is None


class TestRuleBasedClassifier:
    """Test cases for RuleBasedClassifier."""
    
    def test_init(self, semantic_config):
        """Test classifier initialization."""
        classifier = RuleBasedClassifier(semantic_config)
        
        assert classifier.config == semantic_config
        assert len(classifier.title_patterns) > 0
        assert len(classifier.heading_patterns) > 0
        assert len(classifier.caption_patterns) > 0
        assert len(classifier.metadata_patterns) > 0
        assert len(classifier.footer_patterns) > 0
        assert len(classifier.header_patterns) > 0
    
    def test_classify_title_by_type(self, semantic_config):
        """Test title classification by element type."""
        classifier = RuleBasedClassifier(semantic_config)
        
        title_element = UnifiedElement(
            id="title_1",
            type="Title",
            text="Document Title",
            metadata=ElementMetadata()
        )
        
        result = classifier.classify(title_element, {})
        
        assert result is not None
        assert result.role == SemanticRole.TITLE
        assert result.confidence == 0.9
        assert result.method == "rules"
        assert result.metadata["reason"] == "element_type"
    
    def test_classify_title_by_pattern(self, semantic_config):
        """Test title classification by pattern matching."""
        classifier = RuleBasedClassifier(semantic_config)
        
        title_element = UnifiedElement(
            id="title_1",
            type="Text",
            text="DOCUMENT TITLE ALL CAPS",
            metadata=ElementMetadata()
        )
        
        result = classifier.classify(title_element, {})
        
        assert result is not None
        assert result.role == SemanticRole.TITLE
        assert result.method == "rules"
        assert "pattern_match" in result.metadata["reason"]
    
    def test_classify_heading_by_pattern(self, semantic_config):
        """Test heading classification by pattern."""
        classifier = RuleBasedClassifier(semantic_config)
        
        heading_element = UnifiedElement(
            id="heading_1",
            type="Text",
            text="1.1 Introduction to the Topic",
            metadata=ElementMetadata()
        )
        
        result = classifier.classify(heading_element, {})
        
        assert result is not None
        assert result.role in [SemanticRole.HEADING, SemanticRole.SUBHEADING]
        assert result.method == "rules"
    
    def test_classify_caption_figure(self, semantic_config):
        """Test figure caption classification."""
        classifier = RuleBasedClassifier(semantic_config)
        
        caption_element = UnifiedElement(
            id="caption_1",
            type="Text",
            text="Figure 1: System architecture diagram",
            metadata=ElementMetadata()
        )
        
        result = classifier.classify(caption_element, {})
        
        assert result is not None
        assert result.role == SemanticRole.FIGURE_CAPTION
        assert result.confidence == 0.9
        assert result.method == "rules"
    
    def test_classify_caption_table(self, semantic_config):
        """Test table caption classification."""
        classifier = RuleBasedClassifier(semantic_config)
        
        caption_element = UnifiedElement(
            id="caption_1",
            type="Text",
            text="Table 2: Performance comparison results",
            metadata=ElementMetadata()
        )
        
        result = classifier.classify(caption_element, {})
        
        assert result is not None
        assert result.role == SemanticRole.TABLE_CAPTION
        assert result.method == "rules"
    
    def test_classify_date_iso(self, semantic_config):
        """Test ISO date classification."""
        classifier = RuleBasedClassifier(semantic_config)
        
        date_element = UnifiedElement(
            id="date_1",
            type="Text",
            text="2024-01-15",
            metadata=ElementMetadata()
        )
        
        result = classifier.classify(date_element, {})
        
        assert result is not None
        assert result.role == SemanticRole.DATE
        assert result.method == "rules"
    
    def test_classify_date_standard(self, semantic_config):
        """Test standard date format classification."""
        classifier = RuleBasedClassifier(semantic_config)
        
        date_element = UnifiedElement(
            id="date_1",
            type="Text",
            text="01/15/2024",
            metadata=ElementMetadata()
        )
        
        result = classifier.classify(date_element, {})
        
        assert result is not None
        assert result.role == SemanticRole.DATE
        assert result.method == "rules"
    
    def test_classify_page_number(self, semantic_config):
        """Test page number classification."""
        classifier = RuleBasedClassifier(semantic_config)
        
        page_element = UnifiedElement(
            id="page_1",
            type="Text",
            text="Page 15",
            metadata=ElementMetadata()
        )
        
        result = classifier.classify(page_element, {})
        
        assert result is not None
        assert result.role == SemanticRole.PAGE_NUMBER
        assert result.method == "rules"
    
    def test_classify_author(self, semantic_config):
        """Test author classification."""
        classifier = RuleBasedClassifier(semantic_config)
        
        author_element = UnifiedElement(
            id="author_1",
            type="Text",
            text="Author: John Smith",
            metadata=ElementMetadata()
        )
        
        result = classifier.classify(author_element, {})
        
        assert result is not None
        assert result.role == SemanticRole.AUTHOR
        assert result.method == "rules"
    
    def test_classify_footer_copyright(self, semantic_config):
        """Test footer classification with copyright."""
        classifier = RuleBasedClassifier(semantic_config)
        
        footer_element = UnifiedElement(
            id="footer_1",
            type="Text",
            text="© 2024 Company Name",
            metadata=ElementMetadata()
        )
        
        result = classifier.classify(footer_element, {})
        
        assert result is not None
        assert result.role == SemanticRole.FOOTER
        assert result.method == "rules"
    
    def test_classify_list_item_by_type(self, semantic_config):
        """Test list item classification by element type."""
        classifier = RuleBasedClassifier(semantic_config)
        
        list_element = UnifiedElement(
            id="list_1",
            type="ListItem",
            text="First item in the list",
            metadata=ElementMetadata()
        )
        
        result = classifier.classify(list_element, {})
        
        assert result is not None
        assert result.role == SemanticRole.LIST_ITEM
        assert result.confidence == 0.9
        assert result.method == "rules"
    
    def test_classify_list_item_by_bullet(self, semantic_config):
        """Test list item classification by bullet pattern."""
        classifier = RuleBasedClassifier(semantic_config)
        
        list_element = UnifiedElement(
            id="list_1",
            type="Text",
            text="• First bullet point",
            metadata=ElementMetadata()
        )
        
        result = classifier.classify(list_element, {})
        
        assert result is not None
        assert result.role == SemanticRole.LIST_ITEM
        assert result.method == "rules"
    
    def test_classify_numbered_list(self, semantic_config):
        """Test numbered list item classification."""
        classifier = RuleBasedClassifier(semantic_config)
        
        list_element = UnifiedElement(
            id="list_1",
            type="Text",
            text="1. First numbered item",
            metadata=ElementMetadata()
        )
        
        result = classifier.classify(list_element, {})
        
        assert result is not None
        assert result.role == SemanticRole.LIST_ITEM
        assert result.method == "rules"
    
    def test_classify_table_element(self, semantic_config):
        """Test table element classification."""
        classifier = RuleBasedClassifier(semantic_config)
        
        table_element = UnifiedElement(
            id="table_1",
            type="TableCell",
            text="Cell content",
            metadata=ElementMetadata()
        )
        
        result = classifier.classify(table_element, {})
        
        assert result is not None
        assert result.role == SemanticRole.TABLE_CELL
        assert result.confidence == 0.9
        assert result.method == "rules"
    
    def test_default_classification_paragraph(self, semantic_config):
        """Test default classification for long text."""
        classifier = RuleBasedClassifier(semantic_config)
        
        long_text_element = UnifiedElement(
            id="para_1",
            type="Text",
            text="This is a long paragraph with enough text content to be classified as a paragraph by default. It contains multiple sentences and detailed information.",
            metadata=ElementMetadata()
        )
        
        result = classifier.classify(long_text_element, {})
        
        assert result is not None
        assert result.role == SemanticRole.PARAGRAPH
        assert result.method == "rules"
        assert result.metadata["reason"] == "length_and_type"
    
    def test_default_classification_short_text(self, semantic_config):
        """Test default classification for short text."""
        classifier = RuleBasedClassifier(semantic_config)
        
        short_text_element = UnifiedElement(
            id="short_1",
            type="Text",
            text="Short text",
            metadata=ElementMetadata()
        )
        
        result = classifier.classify(short_text_element, {})
        
        assert result is not None
        assert result.role == SemanticRole.METADATA
        assert result.method == "rules"
        assert result.metadata["reason"] == "short_text"
    
    def test_classify_empty_text(self, semantic_config):
        """Test classification of element with no text."""
        classifier = RuleBasedClassifier(semantic_config)
        
        empty_element = UnifiedElement(
            id="empty_1",
            type="Text",
            text="",
            metadata=ElementMetadata()
        )
        
        result = classifier.classify(empty_element, {})
        
        assert result is not None
        # Should get default classification
        assert result.role in [SemanticRole.METADATA, SemanticRole.BODY_TEXT]
        assert result.method == "rules"


class TestSemanticConfig:
    """Test cases for SemanticConfig."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = SemanticConfig()
        
        assert config.enable_ml_classification is True
        assert config.enable_rule_based_classification is True
        assert config.confidence_threshold == 0.6
        assert config.max_title_length == 200
        assert config.max_caption_length == 500
        assert config.min_paragraph_length == 50
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = SemanticConfig(
            enable_ml_classification=False,
            confidence_threshold=0.8,
            max_title_length=100
        )
        
        assert config.enable_ml_classification is False
        assert config.confidence_threshold == 0.8
        assert config.max_title_length == 100
        assert config.enable_rule_based_classification is True  # Default


class TestClassificationResult:
    """Test cases for ClassificationResult."""
    
    def test_classification_result_creation(self):
        """Test creating classification result."""
        result = ClassificationResult(
            role=SemanticRole.TITLE,
            confidence=0.85,
            method="rules",
            metadata={"reason": "pattern_match"}
        )
        
        assert result.role == SemanticRole.TITLE
        assert result.confidence == 0.85
        assert result.method == "rules"
        assert result.metadata["reason"] == "pattern_match"