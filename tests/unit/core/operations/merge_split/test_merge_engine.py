"""
Tests for Merge Engine

Comprehensive tests for the merge operation functionality.
"""

import pytest
from unittest.mock import Mock, patch

from torematrix.core.operations.merge_split.merge import MergeOperation, MergeResult
from torematrix.core.operations.merge_split.split import SplitOperation, SplitResult
from torematrix.core.operations.merge_split.base_operation import OperationStatus
from torematrix.core.models.element import Element
from torematrix.core.models.metadata import ElementMetadata
from torematrix.core.models.coordinates import Coordinates


class TestMergeOperation:
    """Test cases for MergeOperation class."""
    
    def create_sample_element(self, element_id: str, text: str, element_type: str = "text") -> Element:
        """Create a sample element for testing."""
        metadata = ElementMetadata(
            confidence=0.9,
            page_number=1,
            coordinates=Coordinates(
                layout_bbox=[0.0, 0.0, 100.0, 20.0],
                coordinate_system="pixel"
            )
        )
        return Element(
            element_id=element_id,
            element_type=element_type,
            text=text,
            metadata=metadata,
            parent_id=None
        )
    
    def test_merge_operation_init(self):
        """Test MergeOperation initialization."""
        elements = [
            self.create_sample_element("1", "Hello"),
            self.create_sample_element("2", "World")
        ]
        
        operation = MergeOperation(elements)
        
        assert operation.elements == elements
        assert operation.status == OperationStatus.PENDING
        assert operation.operation_id is not None
    
    def test_validate_valid_merge(self):
        """Test validation with valid merge elements."""
        elements = [
            self.create_sample_element("1", "Hello world"),
            self.create_sample_element("2", "This is a test")
        ]
        
        operation = MergeOperation(elements)
        result = operation.validate()
        
        assert result is True
        assert operation.status == OperationStatus.VALIDATING
    
    def test_validate_empty_elements(self):
        """Test validation with empty elements list."""
        operation = MergeOperation([])
        result = operation.validate()
        
        assert result is False
    
    def test_validate_single_element(self):
        """Test validation with single element."""
        elements = [self.create_sample_element("1", "Hello")]
        
        operation = MergeOperation(elements)
        result = operation.validate()
        
        assert result is False
    
    def test_execute_successful(self):
        """Test successful merge execution."""
        elements = [
            self.create_sample_element("1", "First paragraph."),
            self.create_sample_element("2", "Second paragraph.")
        ]
        
        operation = MergeOperation(elements)
        result = operation.execute()
        
        assert isinstance(result, MergeResult)
        assert result.status == OperationStatus.COMPLETED
        assert result.merged_element is not None
        assert result.merged_element.text == "First paragraph. Second paragraph."
        assert result.execution_time_ms > 0
    
    def test_execute_validation_failure(self):
        """Test execution with validation failure."""
        operation = MergeOperation([])  # Empty elements
        result = operation.execute()
        
        assert isinstance(result, MergeResult)
        assert result.status == OperationStatus.FAILED
        assert result.error_message is not None
        assert result.merged_element is None
    
    def test_preview_successful(self):
        """Test successful preview generation."""
        elements = [
            self.create_sample_element("1", "Hello"),
            self.create_sample_element("2", "World")
        ]
        
        operation = MergeOperation(elements)
        result = operation.preview()
        
        assert isinstance(result, MergeResult)
        assert result.status == OperationStatus.COMPLETED
        assert result.merged_element is not None
        assert result.merged_element.text == "Hello World"
        assert result.metadata.get("preview") is True
    
    def test_rollback_successful(self):
        """Test successful rollback."""
        elements = [
            self.create_sample_element("1", "Hello"),
            self.create_sample_element("2", "World")
        ]
        
        operation = MergeOperation(elements)
        operation.execute()
        
        # Test rollback
        assert operation.can_rollback() is True
        result = operation.rollback()
        
        assert result is True
        assert operation.status == OperationStatus.PENDING
        assert operation._merged_element is None
    
    def test_rollback_not_possible(self):
        """Test rollback when not possible."""
        elements = [
            self.create_sample_element("1", "Hello"),
            self.create_sample_element("2", "World")
        ]
        
        operation = MergeOperation(elements)
        
        # Test rollback before execution
        assert operation.can_rollback() is False
        result = operation.rollback()
        
        assert result is False


class TestSplitOperation:
    """Test cases for SplitOperation class."""
    
    def create_sample_element(self, element_id: str, text: str, element_type: str = "text") -> Element:
        """Create a sample element for testing."""
        metadata = ElementMetadata(
            confidence=0.9,
            page_number=1,
            coordinates=Coordinates(
                layout_bbox=[0.0, 0.0, 200.0, 20.0],
                coordinate_system="pixel"
            )
        )
        return Element(
            element_id=element_id,
            element_type=element_type,
            text=text,
            metadata=metadata,
            parent_id=None
        )
    
    def test_split_operation_init(self):
        """Test SplitOperation initialization."""
        element = self.create_sample_element("1", "Hello World Test")
        split_points = [6, 12]
        
        operation = SplitOperation(element, split_points)
        
        assert operation.element == element
        assert operation.split_points == split_points
        assert operation.status == OperationStatus.PENDING
    
    def test_validate_valid_split(self):
        """Test validation with valid split parameters."""
        element = self.create_sample_element("1", "Hello World Test")
        split_points = [6, 12]
        
        operation = SplitOperation(element, split_points)
        result = operation.validate()
        
        assert result is True
        assert operation.status == OperationStatus.VALIDATING
    
    def test_validate_no_element(self):
        """Test validation with no element."""
        operation = SplitOperation(None, [5])
        result = operation.validate()
        
        assert result is False
    
    def test_validate_no_split_points(self):
        """Test validation with no split points."""
        element = self.create_sample_element("1", "Hello World")
        operation = SplitOperation(element, [])
        result = operation.validate()
        
        assert result is False
    
    def test_execute_successful(self):
        """Test successful split execution."""
        element = self.create_sample_element("1", "Hello World Test")
        split_points = [6, 12]
        
        operation = SplitOperation(element, split_points)
        result = operation.execute()
        
        assert isinstance(result, SplitResult)
        assert result.status == OperationStatus.COMPLETED
        assert len(result.split_elements) == 3
        assert result.split_elements[0].text == "Hello "
        assert result.split_elements[1].text == "World "
        assert result.split_elements[2].text == "Test"
    
    def test_preview_successful(self):
        """Test successful preview generation."""
        element = self.create_sample_element("1", "Hello World")
        split_points = [6]
        
        operation = SplitOperation(element, split_points)
        result = operation.preview()
        
        assert isinstance(result, SplitResult)
        assert result.status == OperationStatus.COMPLETED
        assert len(result.split_elements) == 2
        assert result.metadata.get("preview") is True
    
    def test_rollback_successful(self):
        """Test successful rollback."""
        element = self.create_sample_element("1", "Hello World")
        split_points = [6]
        
        operation = SplitOperation(element, split_points)
        operation.execute()
        
        # Test rollback
        assert operation.can_rollback() is True
        result = operation.rollback()
        
        assert result is True
        assert operation.status == OperationStatus.PENDING
        assert len(operation._split_elements) == 0
    
    def test_find_optimal_split_points(self):
        """Test finding optimal split points."""
        element = self.create_sample_element("1", "This is a test. This is another test.")
        
        operation = SplitOperation(element, [])
        optimal_points = operation.find_optimal_split_points(2)
        
        assert len(optimal_points) == 1
        assert optimal_points[0] > 0
        assert optimal_points[0] < len(element.text)