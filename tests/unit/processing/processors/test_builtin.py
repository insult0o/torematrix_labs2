"""Unit tests for built-in processors."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import tempfile
import os

from torematrix.processing.processors.base import (
    ProcessorContext,
    ProcessorResult,
    StageStatus
)
from torematrix.processing.processors.builtin.metadata_processor import MetadataExtractorProcessor
from torematrix.processing.processors.builtin.validation_processor import ValidationProcessor
from torematrix.processing.processors.builtin.transformation_processor import TransformationProcessor


@pytest.fixture
def temp_file():
    """Create temporary file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("This is test content for the file.\n")
        f.write("It has multiple lines.\n")
        f.write("And some more text here.")
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    try:
        os.unlink(temp_path)
    except FileNotFoundError:
        pass


@pytest.fixture
def basic_context(temp_file):
    """Create basic processing context."""
    return ProcessorContext(
        document_id="doc123",
        file_path=temp_file,
        mime_type="text/plain",
        metadata={"source": "test"}
    )


@pytest.fixture
def context_with_unstructured_result(basic_context):
    """Create context with mock unstructured results."""
    basic_context.previous_results = {
        "unstructured_processor": {
            "extracted_data": {
                "elements": [
                    {"type": "Title", "text": "Test Document"},
                    {"type": "NarrativeText", "text": "This is the main content."},
                    {"type": "Table", "text": "Table data"}
                ],
                "text": "Test Document\nThis is the main content.\nTable data",
                "tables": [{"rows": [["A", "B"], ["1", "2"]]}],
                "images": [{"path": "/tmp/image1.png"}]
            },
            "metadata": {
                "page_count": 2,
                "language": "en",
                "file_type": "pdf",
                "element_count": 3
            }
        }
    }
    return basic_context


class TestMetadataExtractorProcessor:
    """Test cases for MetadataExtractorProcessor."""
    
    @pytest.fixture
    def processor(self):
        """Create metadata extractor processor."""
        return MetadataExtractorProcessor()
    
    def test_processor_metadata(self, processor):
        """Test processor metadata."""
        metadata = processor.get_metadata()
        
        assert metadata.name == "metadata_extractor"
        assert metadata.version == "1.0.0"
        assert "*" in metadata.supported_formats  # Supports all formats
        assert not metadata.is_cpu_intensive
    
    @pytest.mark.asyncio
    async def test_basic_metadata_extraction(self, processor, basic_context):
        """Test basic metadata extraction."""
        await processor.initialize()
        result = await processor.process(basic_context)
        
        assert result.status == StageStatus.COMPLETED
        assert "metadata" in result.extracted_data
        
        metadata = result.extracted_data["metadata"]
        assert metadata["document_id"] == "doc123"
        assert metadata["mime_type"] == "text/plain"
        assert "file_size_bytes" in metadata
        assert "file_size_mb" in metadata
        assert "created_time" in metadata
        assert "modified_time" in metadata
        assert "processing_time" in metadata
    
    @pytest.mark.asyncio
    async def test_metadata_with_unstructured_results(self, processor, context_with_unstructured_result):
        """Test metadata extraction with unstructured results."""
        await processor.initialize()
        result = await processor.process(context_with_unstructured_result)
        
        assert result.status == StageStatus.COMPLETED
        metadata = result.extracted_data["metadata"]
        
        # Should include unstructured metadata
        assert metadata["page_count"] == 2
        assert metadata["language"] == "en"
        assert metadata["file_type"] == "pdf"
        assert metadata["element_count"] == 3
        
        # Should include text statistics
        assert metadata["text_length"] > 0
        assert metadata["word_count"] > 0
        assert metadata["line_count"] > 0
        assert metadata["table_count"] == 1
        assert metadata["image_count"] == 1
    
    @pytest.mark.asyncio
    async def test_document_categorization(self, processor, basic_context):
        """Test document categorization."""
        await processor.initialize()
        
        # Test with different file extensions
        test_cases = [
            ("/tmp/test.xlsx", "spreadsheet"),
            ("/tmp/test.pptx", "presentation"),
            ("/tmp/test.msg", "email"),
            ("/tmp/test.html", "web"),
            ("/tmp/test.md", "markup")
        ]
        
        for file_path, expected_category in test_cases:
            basic_context.file_path = file_path
            # Mock file stats for non-existent files
            with patch('pathlib.Path.stat') as mock_stat:
                mock_stat.return_value = Mock(
                    st_size=1024, 
                    st_ctime=datetime.now().timestamp(),
                    st_mtime=datetime.now().timestamp()
                )
                
                result = await processor.process(basic_context)
                metadata = result.extracted_data["metadata"]
                assert metadata["document_category"] == expected_category
    
    @pytest.mark.asyncio
    async def test_quality_metrics_calculation(self, processor, context_with_unstructured_result):
        """Test quality metrics calculation."""
        await processor.initialize()
        result = await processor.process(context_with_unstructured_result)
        
        metadata = result.extracted_data["metadata"]
        
        # Quality metrics should be present
        assert "content_completeness" in metadata
        assert "content_richness" in metadata
        assert "size_appropriateness" in metadata
        assert "overall_quality" in metadata
        
        # All metrics should be between 0 and 1
        for metric in ["content_completeness", "content_richness", "size_appropriateness", "overall_quality"]:
            assert 0.0 <= metadata[metric] <= 1.0
    
    @pytest.mark.asyncio
    async def test_context_metadata_inclusion(self, processor, basic_context):
        """Test inclusion of context metadata."""
        basic_context.metadata = {"custom_field": "custom_value", "priority": "high"}
        
        await processor.initialize()
        result = await processor.process(basic_context)
        
        metadata = result.extracted_data["metadata"]
        assert metadata["context_custom_field"] == "custom_value"
        assert metadata["context_priority"] == "high"
    
    @pytest.mark.asyncio
    async def test_file_not_found_handling(self, processor):
        """Test handling of non-existent files."""
        context = ProcessorContext(
            document_id="doc123",
            file_path="/nonexistent/file.txt",
            mime_type="text/plain"
        )
        
        await processor.initialize()
        result = await processor.process(context)
        
        # Should fail gracefully
        assert result.status == StageStatus.FAILED
        assert len(result.errors) > 0


class TestValidationProcessor:
    """Test cases for ValidationProcessor."""
    
    @pytest.fixture
    def processor(self):
        """Create validation processor."""
        return ValidationProcessor()
    
    def test_processor_metadata(self, processor):
        """Test processor metadata."""
        metadata = processor.get_metadata()
        
        assert metadata.name == "validation_processor"
        assert metadata.version == "1.0.0"
        assert "*" in metadata.supported_formats
        assert not metadata.is_cpu_intensive
    
    @pytest.mark.asyncio
    async def test_basic_validation(self, processor, basic_context):
        """Test basic validation without previous results."""
        await processor.initialize()
        result = await processor.process(basic_context)
        
        assert result.status == StageStatus.COMPLETED
        assert "validation_results" in result.extracted_data
        assert "is_valid" in result.extracted_data
        assert "validation_summary" in result.extracted_data
    
    @pytest.mark.asyncio
    async def test_validation_with_unstructured_results(self, processor, context_with_unstructured_result):
        """Test validation with unstructured results."""
        await processor.initialize()
        result = await processor.process(context_with_unstructured_result)
        
        assert result.status == StageStatus.COMPLETED
        
        validation_results = result.extracted_data["validation_results"]
        
        # Should have validation checks
        check_types = [r["check"] for r in validation_results]
        assert "content_extraction" in check_types
        assert "text_content" in check_types
    
    @pytest.mark.asyncio
    async def test_validation_rules_configuration(self, processor, context_with_unstructured_result):
        """Test validation with custom rules."""
        # Configure validation rules
        processor.config = {
            "validation_rules": {
                "min_text_length": 100,
                "max_file_size_mb": 10,
                "min_file_size_bytes": 100,
                "expect_tables": True,
                "expect_images": True,
                "required_metadata_fields": ["file_name", "file_size_bytes"],
                "min_quality_score": 0.8
            }
        }
        
        # Add metadata processor results
        context_with_unstructured_result.previous_results["metadata_extractor"] = {
            "extracted_data": {
                "metadata": {
                    "file_name": "test.txt",
                    "file_size_bytes": 1024,
                    "overall_quality": 0.9
                }
            }
        }
        
        await processor.initialize()
        result = await processor.process(context_with_unstructured_result)
        
        validation_results = result.extracted_data["validation_results"]
        
        # Should have checks for configured rules
        check_types = [r["check"] for r in validation_results]
        assert any("required_metadata" in check for check in check_types)
        assert any("quality" in check for check in check_types)
    
    @pytest.mark.asyncio
    async def test_validation_score_calculation(self, processor, context_with_unstructured_result):
        """Test validation score calculation."""
        await processor.initialize()
        result = await processor.process(context_with_unstructured_result)
        
        validation_score = result.metadata["validation_score"]
        assert 0.0 <= validation_score <= 1.0
    
    @pytest.mark.asyncio
    async def test_empty_content_validation(self, processor, basic_context):
        """Test validation with empty content."""
        # Mock empty unstructured results
        basic_context.previous_results = {
            "unstructured_processor": {
                "extracted_data": {
                    "elements": [],
                    "text": "",
                    "tables": [],
                    "images": []
                }
            }
        }
        
        await processor.initialize()
        result = await processor.process(basic_context)
        
        # Should detect empty content
        validation_results = result.extracted_data["validation_results"]
        error_results = [r for r in validation_results if r["level"] == "error"]
        
        assert len(error_results) > 0
        assert any("No content extracted" in r["message"] for r in error_results)
    
    @pytest.mark.asyncio
    async def test_file_size_validation(self, processor, basic_context):
        """Test file size validation."""
        processor.config = {
            "validation_rules": {
                "max_file_size_mb": 0.001,  # Very small limit
                "min_file_size_bytes": 10000  # Large minimum
            }
        }
        
        await processor.initialize()
        result = await processor.process(basic_context)
        
        validation_results = result.extracted_data["validation_results"]
        
        # Should have file size violations
        size_checks = [r for r in validation_results if "file_size" in r["check"]]
        assert len(size_checks) > 0


class TestTransformationProcessor:
    """Test cases for TransformationProcessor."""
    
    @pytest.fixture
    def processor(self):
        """Create transformation processor."""
        return TransformationProcessor()
    
    def test_processor_metadata(self, processor):
        """Test processor metadata."""
        metadata = processor.get_metadata()
        
        assert metadata.name == "transformation_processor"
        assert metadata.version == "1.0.0"
        assert metadata.is_cpu_intensive
    
    @pytest.mark.asyncio
    async def test_no_unstructured_results_error(self, processor, basic_context):
        """Test error when no unstructured results available."""
        await processor.initialize()
        result = await processor.process(basic_context)
        
        assert result.status == StageStatus.FAILED
        assert any("unstructured_processor required" in error for error in result.errors)
    
    @pytest.mark.asyncio
    async def test_normalize_whitespace_transformation(self, processor, context_with_unstructured_result):
        """Test whitespace normalization transformation."""
        # Add whitespace to elements
        elements = context_with_unstructured_result.previous_results["unstructured_processor"]["extracted_data"]["elements"]
        elements[1]["text"] = "This   has    multiple   spaces\n\n\nand   newlines"
        
        processor.config = {"transformations": ["normalize_whitespace"]}
        
        await processor.initialize()
        result = await processor.process(context_with_unstructured_result)
        
        assert result.status == StageStatus.COMPLETED
        transformed_elements = result.extracted_data["elements"]
        
        # Should normalize whitespace
        assert transformed_elements[1]["text"] == "This has multiple spaces and newlines"
    
    @pytest.mark.asyncio
    async def test_remove_empty_elements_transformation(self, processor, context_with_unstructured_result):
        """Test removing empty elements."""
        # Add empty element
        elements = context_with_unstructured_result.previous_results["unstructured_processor"]["extracted_data"]["elements"]
        elements.append({"type": "NarrativeText", "text": "   "})  # Empty/whitespace only
        elements.append({"type": "NarrativeText", "text": ""})     # Completely empty
        
        original_count = len(elements)
        processor.config = {"transformations": ["remove_empty_elements"]}
        
        await processor.initialize()
        result = await processor.process(context_with_unstructured_result)
        
        transformed_elements = result.extracted_data["elements"]
        
        # Should remove empty elements
        assert len(transformed_elements) < original_count
        assert all(elem.get("text", "").strip() or elem.get("type") in ["Table", "Image", "Figure"] 
                  for elem in transformed_elements)
    
    @pytest.mark.asyncio
    async def test_lowercase_transformation(self, processor, context_with_unstructured_result):
        """Test lowercase transformation."""
        processor.config = {"transformations": ["lowercase_text"]}
        
        await processor.initialize()
        result = await processor.process(context_with_unstructured_result)
        
        transformed_elements = result.extracted_data["elements"]
        
        # All text should be lowercase
        for elem in transformed_elements:
            if "text" in elem and elem["text"]:
                assert elem["text"].islower()
    
    @pytest.mark.asyncio
    async def test_remove_special_chars_transformation(self, processor, context_with_unstructured_result):
        """Test special character removal."""
        # Add special characters
        elements = context_with_unstructured_result.previous_results["unstructured_processor"]["extracted_data"]["elements"]
        elements[1]["text"] = "Text with @#$% special chars & symbols!!!"
        
        processor.config = {"transformations": ["remove_special_chars"]}
        
        await processor.initialize()
        result = await processor.process(context_with_unstructured_result)
        
        transformed_elements = result.extracted_data["elements"]
        
        # Should remove special characters
        text = transformed_elements[1]["text"]
        assert "@#$%" not in text
        assert "&" not in text
        assert "!!!" in text  # Exclamation marks should remain
    
    @pytest.mark.asyncio
    async def test_merge_similar_elements_transformation(self, processor, context_with_unstructured_result):
        """Test merging similar elements."""
        # Add consecutive similar elements
        elements = context_with_unstructured_result.previous_results["unstructured_processor"]["extracted_data"]["elements"]
        elements.extend([
            {"type": "NarrativeText", "text": "First paragraph."},
            {"type": "NarrativeText", "text": "Second paragraph."},
            {"type": "NarrativeText", "text": "Third paragraph."}
        ])
        
        original_count = len(elements)
        processor.config = {"transformations": ["merge_similar_elements"]}
        
        await processor.initialize()
        result = await processor.process(context_with_unstructured_result)
        
        transformed_elements = result.extracted_data["elements"]
        
        # Should merge consecutive NarrativeText elements
        assert len(transformed_elements) < original_count
        
        # Find merged element
        merged_element = None
        for elem in transformed_elements:
            if "First paragraph. Second paragraph. Third paragraph." in elem.get("text", ""):
                merged_element = elem
                break
        
        assert merged_element is not None
    
    @pytest.mark.asyncio
    async def test_extract_numbers_transformation(self, processor, context_with_unstructured_result):
        """Test number extraction."""
        # Add numbers to text
        elements = context_with_unstructured_result.previous_results["unstructured_processor"]["extracted_data"]["elements"]
        elements[1]["text"] = "The price is $123.45 and quantity is 100 items."
        
        processor.config = {"transformations": ["extract_numbers"]}
        
        await processor.initialize()
        result = await processor.process(context_with_unstructured_result)
        
        transformed_elements = result.extracted_data["elements"]
        
        # Should extract numbers
        elem_with_numbers = transformed_elements[1]
        assert "metadata" in elem_with_numbers
        assert "extracted_numbers" in elem_with_numbers["metadata"]
        assert "123.45" in elem_with_numbers["metadata"]["extracted_numbers"]
        assert "100" in elem_with_numbers["metadata"]["extracted_numbers"]
    
    @pytest.mark.asyncio
    async def test_standardize_headers_transformation(self, processor, context_with_unstructured_result):
        """Test header standardization."""
        # Modify title element
        elements = context_with_unstructured_result.previous_results["unstructured_processor"]["extracted_data"]["elements"]
        elements[0]["text"] = "  test document title  "  # With extra spaces
        
        processor.config = {"transformations": ["standardize_headers"]}
        
        await processor.initialize()
        result = await processor.process(context_with_unstructured_result)
        
        transformed_elements = result.extracted_data["elements"]
        
        # Should standardize header
        title_elem = transformed_elements[0]
        assert title_elem["text"] == "Test Document Title"  # Title case, trimmed
        assert "metadata" in title_elem
        assert "header_level" in title_elem["metadata"]
    
    @pytest.mark.asyncio
    async def test_multiple_transformations(self, processor, context_with_unstructured_result):
        """Test applying multiple transformations in sequence."""
        processor.config = {
            "transformations": [
                "normalize_whitespace",
                "remove_empty_elements", 
                "lowercase_text"
            ]
        }
        
        await processor.initialize()
        result = await processor.process(context_with_unstructured_result)
        
        assert result.status == StageStatus.COMPLETED
        assert result.metadata["transformations_applied"] == 3
    
    @pytest.mark.asyncio
    async def test_unknown_transformation(self, processor, context_with_unstructured_result):
        """Test handling of unknown transformations."""
        processor.config = {"transformations": ["unknown_transformation"]}
        
        await processor.initialize()
        result = await processor.process(context_with_unstructured_result)
        
        # Should complete but log warning (not test the logging here)
        assert result.status == StageStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_transformation_statistics(self, processor, context_with_unstructured_result):
        """Test transformation statistics calculation."""
        processor.config = {"transformations": ["lowercase_text"]}
        
        await processor.initialize()
        result = await processor.process(context_with_unstructured_result)
        
        stats = result.extracted_data["transformation_stats"]
        
        assert "original_text_length" in stats
        assert "transformed_text_length" in stats
        assert "text_length_change" in stats
        assert "elements_modified" in stats
        assert "success_rate" in stats
        assert "element_count_change" in stats