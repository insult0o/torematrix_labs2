"""Tests for Type Conversion Engine

Test suite for type conversion functionality including:
- Element type conversions with data preservation
- Conversion compatibility analysis
- Batch conversion operations
- Data mapping and transformation
"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any, List

from torematrix.core.operations.type_management.conversions import (
    TypeConversionEngine, ConversionResult, ConversionAnalysis,
    DataPreservationStrategy, ConversionStrategy
)
from torematrix.core.type_system.registry import TypeRegistry


class TestTypeConversionEngine:
    """Test suite for TypeConversionEngine"""
    
    @pytest.fixture
    def mock_registry(self):
        """Mock type registry with test definitions"""
        registry = Mock(spec=TypeRegistry)
        
        # Mock type definitions
        type_definitions = {
            'text': {
                'name': 'text',
                'fields': {
                    'content': {'type': 'string', 'required': True},
                    'language': {'type': 'string', 'default': 'en'}
                }
            },
            'title': {
                'name': 'title',
                'fields': {
                    'content': {'type': 'string', 'required': True},
                    'level': {'type': 'integer', 'default': 1}
                }
            },
            'paragraph': {
                'name': 'paragraph',
                'fields': {
                    'content': {'type': 'string', 'required': True},
                    'style': {'type': 'string', 'default': 'normal'}
                }
            }
        }
        
        def get_type_definition(type_name):
            return type_definitions.get(type_name)
        
        registry.get_type_definition.side_effect = get_type_definition
        registry.get_all_types.return_value = list(type_definitions.keys())
        
        return registry
    
    @pytest.fixture
    def conversion_engine(self, mock_registry):
        """Create conversion engine instance"""
        return TypeConversionEngine(registry=mock_registry)
    
    def test_engine_initialization(self, conversion_engine):
        """Test conversion engine initialization"""
        assert conversion_engine.registry is not None
        assert len(conversion_engine.conversion_rules) == 0
        assert len(conversion_engine.custom_strategies) == 0
    
    def test_convert_element_type_basic(self, conversion_engine):
        """Test basic element type conversion"""
        element_data = {
            'content': 'This is test content',
            'language': 'en',
            'metadata': {'source': 'test'}
        }
        
        result = conversion_engine.convert_element_type(
            element_id='elem1',
            from_type='text',
            to_type='paragraph',
            element_data=element_data,
            preserve_data=True
        )
        
        assert isinstance(result, ConversionResult)
        assert result.success
        assert result.element_id == 'elem1'
        assert result.from_type == 'text'
        assert result.to_type == 'paragraph'
        assert result.converted_data is not None
        assert 'content' in result.converted_data
        assert result.converted_data['content'] == 'This is test content'
    
    def test_convert_element_type_with_data_loss(self, conversion_engine):
        """Test conversion with potential data loss"""
        element_data = {
            'content': 'Test content',
            'special_field': 'unique_data',  # This field doesn't exist in target type
            'metadata': {'source': 'test'}
        }
        
        result = conversion_engine.convert_element_type(
            element_id='elem1',
            from_type='text',
            to_type='title',
            element_data=element_data,
            preserve_data=True
        )
        
        assert result.success
        assert len(result.data_loss_warnings) > 0
        assert 'special_field' in str(result.data_loss_warnings[0])
    
    def test_convert_element_type_without_preservation(self, conversion_engine):
        """Test conversion without data preservation"""
        element_data = {
            'content': 'Test content',
            'special_field': 'unique_data'
        }
        
        result = conversion_engine.convert_element_type(
            element_id='elem1',
            from_type='text',
            to_type='title',
            element_data=element_data,
            preserve_data=False
        )
        
        assert result.success
        assert 'special_field' not in result.converted_data
        assert len(result.data_loss_warnings) == 0  # No warnings when not preserving
    
    def test_analyze_conversion_compatibility(self, conversion_engine):
        """Test conversion compatibility analysis"""
        analysis = conversion_engine.analyze_conversion_compatibility(
            from_type='text',
            to_type='paragraph'
        )
        
        assert isinstance(analysis, ConversionAnalysis)
        assert analysis.from_type == 'text'
        assert analysis.to_type == 'paragraph'
        assert isinstance(analysis.compatibility_score, float)
        assert 0 <= analysis.compatibility_score <= 1
        assert len(analysis.compatible_fields) > 0
        assert 'content' in analysis.compatible_fields
    
    def test_analyze_incompatible_conversion(self, conversion_engine):
        """Test analysis of incompatible types"""
        # Mock an incompatible type
        conversion_engine.registry.get_type_definition.side_effect = lambda name: (
            {'name': 'incompatible', 'fields': {'different_field': {'type': 'integer'}}}
            if name == 'incompatible' else
            {'name': 'text', 'fields': {'content': {'type': 'string'}}}
        )
        
        analysis = conversion_engine.analyze_conversion_compatibility(
            from_type='text',
            to_type='incompatible'
        )
        
        assert analysis.compatibility_score < 0.5
        assert len(analysis.incompatible_fields) > 0
        assert len(analysis.potential_data_loss) > 0
    
    def test_batch_convert_elements(self, conversion_engine):
        """Test batch element conversion"""
        conversions = [
            ('elem1', 'text', 'paragraph'),
            ('elem2', 'text', 'title'),
            ('elem3', 'paragraph', 'text')
        ]
        
        element_data = {
            'elem1': {'content': 'Content 1'},
            'elem2': {'content': 'Content 2'},
            'elem3': {'content': 'Content 3'}
        }
        
        results = conversion_engine.batch_convert_elements(
            conversions=conversions,
            element_data=element_data
        )
        
        assert len(results) == 3
        for result in results:
            assert isinstance(result, ConversionResult)
            assert result.success
    
    def test_batch_convert_with_failures(self, conversion_engine):
        """Test batch conversion with some failures"""
        conversions = [
            ('elem1', 'text', 'paragraph'),
            ('elem2', 'invalid_type', 'title'),  # This should fail
            ('elem3', 'text', 'paragraph')
        ]
        
        element_data = {
            'elem1': {'content': 'Content 1'},
            'elem2': {'content': 'Content 2'},
            'elem3': {'content': 'Content 3'}
        }
        
        results = conversion_engine.batch_convert_elements(
            conversions=conversions,
            element_data=element_data
        )
        
        assert len(results) == 3
        assert results[0].success  # elem1 success
        assert not results[1].success  # elem2 failure
        assert results[2].success  # elem3 success
    
    def test_get_conversion_suggestions(self, conversion_engine):
        """Test getting conversion suggestions"""
        suggestions = conversion_engine.get_conversion_suggestions('text')
        
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        
        for suggestion in suggestions:
            assert 'target_type' in suggestion
            assert 'compatibility_score' in suggestion
            assert 'reasoning' in suggestion
    
    def test_register_conversion_rule(self, conversion_engine):
        """Test registering custom conversion rules"""
        def custom_rule(from_data, to_type_def):
            return {'content': from_data.get('content', '').upper()}
        
        conversion_engine.register_conversion_rule(
            from_type='text',
            to_type='title',
            rule_function=custom_rule
        )
        
        element_data = {'content': 'test content'}
        
        result = conversion_engine.convert_element_type(
            element_id='elem1',
            from_type='text',
            to_type='title',
            element_data=element_data
        )
        
        assert result.success
        assert result.converted_data['content'] == 'TEST CONTENT'
    
    def test_validate_conversion_data(self, conversion_engine):
        """Test conversion data validation"""
        valid_data = {'content': 'Valid content'}
        invalid_data = {'invalid_field': 'Invalid'}
        
        # Test valid data
        is_valid, errors = conversion_engine.validate_conversion_data(
            data=valid_data,
            target_type='paragraph'
        )
        assert is_valid
        assert len(errors) == 0
        
        # Test invalid data
        is_valid, errors = conversion_engine.validate_conversion_data(
            data=invalid_data,
            target_type='paragraph'
        )
        assert not is_valid
        assert len(errors) > 0
    
    def test_estimate_conversion_time(self, conversion_engine):
        """Test conversion time estimation"""
        conversions = [('elem1', 'text', 'paragraph')] * 100
        
        estimated_time = conversion_engine.estimate_conversion_time(conversions)
        
        assert isinstance(estimated_time, float)
        assert estimated_time > 0
    
    def test_get_conversion_statistics(self, conversion_engine):
        """Test getting conversion statistics"""
        # Perform some conversions
        conversions = [
            ('elem1', 'text', 'paragraph'),
            ('elem2', 'text', 'title'),
            ('elem3', 'paragraph', 'text')
        ]
        
        conversion_engine.batch_convert_elements(conversions)
        
        stats = conversion_engine.get_conversion_statistics()
        
        assert isinstance(stats, dict)
        assert 'total_conversions' in stats
        assert 'successful_conversions' in stats
        assert 'failed_conversions' in stats
        assert 'conversion_types' in stats
    
    def test_data_preservation_strategies(self, conversion_engine):
        """Test different data preservation strategies"""
        element_data = {
            'content': 'Test content',
            'extra_field': 'Extra data',
            'metadata': {'source': 'test'}
        }
        
        # Test with MERGE strategy
        result_merge = conversion_engine.convert_element_type(
            element_id='elem1',
            from_type='text',
            to_type='paragraph',
            element_data=element_data,
            preservation_strategy=DataPreservationStrategy.MERGE
        )
        
        assert result_merge.success
        assert 'extra_field' in result_merge.converted_data  # Extra data preserved
        
        # Test with STRICT strategy
        result_strict = conversion_engine.convert_element_type(
            element_id='elem2',
            from_type='text',
            to_type='paragraph',
            element_data=element_data,
            preservation_strategy=DataPreservationStrategy.STRICT
        )
        
        assert result_strict.success
        assert 'extra_field' not in result_strict.converted_data  # Extra data not preserved
    
    def test_conversion_rollback_data(self, conversion_engine):
        """Test generation of rollback data"""
        element_data = {'content': 'Original content'}
        
        result = conversion_engine.convert_element_type(
            element_id='elem1',
            from_type='text',
            to_type='paragraph',
            element_data=element_data
        )
        
        assert result.success
        assert result.rollback_data is not None
        assert 'original_type' in result.rollback_data
        assert 'original_data' in result.rollback_data
        assert result.rollback_data['original_type'] == 'text'


class TestConversionAnalysis:
    """Test ConversionAnalysis functionality"""
    
    def test_analysis_creation(self):
        """Test creation of conversion analysis"""
        analysis = ConversionAnalysis(
            from_type='text',
            to_type='paragraph',
            compatibility_score=0.85,
            compatible_fields=['content'],
            incompatible_fields=[],
            potential_data_loss=[],
            recommended_strategy=ConversionStrategy.DIRECT
        )
        
        assert analysis.from_type == 'text'
        assert analysis.to_type == 'paragraph'
        assert analysis.compatibility_score == 0.85
        assert analysis.is_recommended
    
    def test_analysis_not_recommended(self):
        """Test analysis for non-recommended conversion"""
        analysis = ConversionAnalysis(
            from_type='text',
            to_type='incompatible',
            compatibility_score=0.2,
            compatible_fields=[],
            incompatible_fields=['content'],
            potential_data_loss=['content'],
            recommended_strategy=ConversionStrategy.CUSTOM
        )
        
        assert not analysis.is_recommended
        assert len(analysis.potential_data_loss) > 0


class TestConversionResult:
    """Test ConversionResult functionality"""
    
    def test_successful_result(self):
        """Test successful conversion result"""
        result = ConversionResult(
            success=True,
            element_id='elem1',
            from_type='text',
            to_type='paragraph',
            converted_data={'content': 'Test'},
            data_loss_warnings=[],
            rollback_data={'original_type': 'text', 'original_data': {}}
        )
        
        assert result.success
        assert result.element_id == 'elem1'
        assert len(result.data_loss_warnings) == 0
        assert result.has_rollback_data
    
    def test_failed_result(self):
        """Test failed conversion result"""
        result = ConversionResult(
            success=False,
            element_id='elem1',
            from_type='text',
            to_type='invalid',
            error_message='Invalid target type'
        )
        
        assert not result.success
        assert result.error_message == 'Invalid target type'
        assert not result.has_rollback_data


if __name__ == '__main__':
    pytest.main([__file__, '-v'])