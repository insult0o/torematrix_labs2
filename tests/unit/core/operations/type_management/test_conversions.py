"""Tests for Type Conversion Engine

Comprehensive test suite for type conversion system including:
- Safe type conversions with data preservation
- Conversion rule validation and application
- Data mapping and transformation
- Risk assessment and mitigation
- Performance optimization for conversions
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

from torematrix.core.operations.type_management.conversions import (
    TypeConversionEngine, ConversionRule, ConversionAnalysis, ConversionResult,
    ConversionStrategy, ConversionRisk, DataMappingRule
)
from torematrix.core.models.types import TypeRegistry, TypeDefinition


class TestConversionStrategy:
    """Test ConversionStrategy enum"""
    
    def test_conversion_strategies(self):
        """Test all conversion strategy values"""
        assert ConversionStrategy.PRESERVE_ALL.value == "preserve_all"
        assert ConversionStrategy.PRESERVE_COMPATIBLE.value == "preserve_compatible"
        assert ConversionStrategy.TRANSFORM.value == "transform"
        assert ConversionStrategy.MINIMAL.value == "minimal"
        assert ConversionStrategy.CUSTOM.value == "custom"


class TestConversionRisk:
    """Test ConversionRisk enum"""
    
    def test_risk_levels(self):
        """Test all risk level values"""
        assert ConversionRisk.NONE.value == "none"
        assert ConversionRisk.LOW.value == "low" 
        assert ConversionRisk.MEDIUM.value == "medium"
        assert ConversionRisk.HIGH.value == "high"
        assert ConversionRisk.CRITICAL.value == "critical"


class TestDataMappingRule:
    """Test DataMappingRule data class"""
    
    def test_mapping_rule_creation(self):
        """Test creating data mapping rule"""
        rule = DataMappingRule(
            source_field="old_field",
            target_field="new_field",
            transformation="uppercase",
            required=True,
            default_value="default",
            validation_pattern=r"^[A-Z]+$"
        )
        
        assert rule.source_field == "old_field"
        assert rule.target_field == "new_field"
        assert rule.transformation == "uppercase"
        assert rule.required is True
        assert rule.default_value == "default"
        assert rule.validation_pattern == r"^[A-Z]+$"
    
    def test_mapping_rule_defaults(self):
        """Test default values for mapping rule"""
        rule = DataMappingRule(
            source_field="source",
            target_field="target"
        )
        
        assert rule.transformation is None
        assert rule.required is False
        assert rule.default_value is None
        assert rule.validation_pattern is None


class TestConversionRule:
    """Test ConversionRule data class"""
    
    def test_rule_creation(self):
        """Test creating conversion rule"""
        mapping_rules = [
            DataMappingRule("field1", "new_field1"),
            DataMappingRule("field2", "new_field2")
        ]
        
        rule = ConversionRule(
            from_type="text",
            to_type="title",
            strategy=ConversionStrategy.PRESERVE_COMPATIBLE,
            risk_level=ConversionRisk.LOW,
            mapping_rules=mapping_rules,
            preserve_metadata=True,
            validation_required=True,
            custom_processor="title_processor"
        )
        
        assert rule.from_type == "text"
        assert rule.to_type == "title"
        assert rule.strategy == ConversionStrategy.PRESERVE_COMPATIBLE
        assert rule.risk_level == ConversionRisk.LOW
        assert rule.mapping_rules == mapping_rules
        assert rule.preserve_metadata is True
        assert rule.validation_required is True
        assert rule.custom_processor == "title_processor"
    
    def test_rule_defaults(self):
        """Test default values for conversion rule"""
        rule = ConversionRule(
            from_type="text",
            to_type="title"
        )
        
        assert rule.strategy == ConversionStrategy.PRESERVE_COMPATIBLE
        assert rule.risk_level == ConversionRisk.MEDIUM
        assert rule.mapping_rules == []
        assert rule.preserve_metadata is True
        assert rule.validation_required is True
        assert rule.custom_processor is None


class TestConversionAnalysis:
    """Test ConversionAnalysis data class"""
    
    def test_analysis_creation(self):
        """Test creating conversion analysis"""
        analysis = ConversionAnalysis(
            from_type="text",
            to_type="title",
            is_safe=True,
            risk_level=ConversionRisk.LOW,
            data_loss_fields=["formatting"],
            preserved_fields=["content", "position"],
            required_transformations=["capitalize"],
            estimated_success_rate=95.5,
            warnings=["Minor formatting loss"],
            recommendations=["Backup original data"]
        )
        
        assert analysis.from_type == "text"
        assert analysis.to_type == "title"
        assert analysis.is_safe is True
        assert analysis.risk_level == ConversionRisk.LOW
        assert analysis.data_loss_fields == ["formatting"]
        assert analysis.preserved_fields == ["content", "position"]
        assert analysis.required_transformations == ["capitalize"]
        assert analysis.estimated_success_rate == 95.5
        assert analysis.warnings == ["Minor formatting loss"]
        assert analysis.recommendations == ["Backup original data"]
    
    def test_analysis_defaults(self):
        """Test default values for analysis"""
        analysis = ConversionAnalysis(
            from_type="text",
            to_type="title"
        )
        
        assert analysis.is_safe is False
        assert analysis.risk_level == ConversionRisk.MEDIUM
        assert analysis.data_loss_fields == []
        assert analysis.preserved_fields == []
        assert analysis.required_transformations == []
        assert analysis.estimated_success_rate == 0.0
        assert analysis.warnings == []
        assert analysis.recommendations == []


class TestConversionResult:
    """Test ConversionResult data class"""
    
    def test_result_creation(self):
        """Test creating conversion result"""
        timestamp = datetime.now()
        result = ConversionResult(
            element_id="elem_001",
            from_type="text",
            to_type="title",
            success=True,
            preserved_data={"content": "Hello World"},
            transformed_data={"title": "HELLO WORLD"},
            lost_data={"font_style": "italic"},
            warnings=["Font style lost"],
            errors=[],
            timestamp=timestamp,
            processing_time=0.05
        )
        
        assert result.element_id == "elem_001"
        assert result.from_type == "text"
        assert result.to_type == "title"
        assert result.success is True
        assert result.preserved_data == {"content": "Hello World"}
        assert result.transformed_data == {"title": "HELLO WORLD"}
        assert result.lost_data == {"font_style": "italic"}
        assert result.warnings == ["Font style lost"]
        assert result.errors == []
        assert result.timestamp == timestamp
        assert result.processing_time == 0.05
    
    def test_result_defaults(self):
        """Test default values for result"""
        result = ConversionResult(
            element_id="elem_001",
            from_type="text",
            to_type="title"
        )
        
        assert result.success is False
        assert result.preserved_data == {}
        assert result.transformed_data == {}
        assert result.lost_data == {}
        assert result.warnings == []
        assert result.errors == []
        assert result.timestamp is not None
        assert result.processing_time == 0.0


class TestTypeConversionEngine:
    """Test TypeConversionEngine functionality"""
    
    @pytest.fixture
    def mock_registry(self):
        """Mock type registry"""
        registry = Mock(spec=TypeRegistry)
        
        # Setup mock type definitions
        text_type = Mock(spec=TypeDefinition)
        text_type.type_id = "text"
        text_type.name = "Text"
        text_type.properties = {"content": str, "formatting": dict}
        
        title_type = Mock(spec=TypeDefinition)
        title_type.type_id = "title"
        title_type.name = "Title"
        title_type.properties = {"content": str, "level": int}
        
        registry.get_type.side_effect = lambda type_id: {
            "text": text_type,
            "title": title_type
        }.get(type_id)
        
        registry.has_type.side_effect = lambda type_id: type_id in ["text", "title"]
        
        return registry
    
    @pytest.fixture
    def engine(self, mock_registry):
        """Create engine instance for testing"""
        return TypeConversionEngine(mock_registry)
    
    def test_engine_initialization(self, mock_registry):
        """Test engine initialization"""
        engine = TypeConversionEngine(mock_registry)
        
        assert engine.registry == mock_registry
        assert engine.conversion_rules == {}
        assert engine.custom_processors == {}
        assert engine._lock is not None
    
    def test_add_conversion_rule(self, engine):
        """Test adding conversion rule"""
        rule = ConversionRule(
            from_type="text",
            to_type="title",
            strategy=ConversionStrategy.PRESERVE_COMPATIBLE,
            risk_level=ConversionRisk.LOW
        )
        
        engine.add_conversion_rule(rule)
        
        assert ("text", "title") in engine.conversion_rules
        assert engine.conversion_rules[("text", "title")] == rule
    
    def test_get_conversion_rule_exists(self, engine):
        """Test getting existing conversion rule"""
        rule = ConversionRule(from_type="text", to_type="title")
        engine.conversion_rules[("text", "title")] = rule
        
        retrieved_rule = engine.get_conversion_rule("text", "title")
        assert retrieved_rule == rule
    
    def test_get_conversion_rule_not_exists(self, engine):
        """Test getting non-existent conversion rule"""
        rule = engine.get_conversion_rule("text", "title")
        assert rule is None
    
    def test_register_custom_processor(self, engine):
        """Test registering custom processor"""
        def custom_processor(data):
            return {"processed": True}
        
        engine.register_custom_processor("test_processor", custom_processor)
        
        assert "test_processor" in engine.custom_processors
        assert engine.custom_processors["test_processor"] == custom_processor
    
    def test_analyze_conversion_with_rule(self, engine):
        """Test conversion analysis with existing rule"""
        # Setup conversion rule
        rule = ConversionRule(
            from_type="text",
            to_type="title",
            strategy=ConversionStrategy.PRESERVE_COMPATIBLE,
            risk_level=ConversionRisk.LOW
        )
        engine.add_conversion_rule(rule)
        
        analysis = engine.analyze_conversion("text", "title")
        
        assert analysis.from_type == "text"
        assert analysis.to_type == "title"
        assert analysis.risk_level == ConversionRisk.LOW
        assert analysis.is_safe is True  # LOW risk should be safe
    
    def test_analyze_conversion_without_rule(self, engine):
        """Test conversion analysis without existing rule"""
        analysis = engine.analyze_conversion("text", "title")
        
        assert analysis.from_type == "text"
        assert analysis.to_type == "title"
        assert analysis.risk_level == ConversionRisk.MEDIUM  # Default
        assert analysis.is_safe is False  # Unknown conversion
    
    def test_analyze_conversion_invalid_types(self, engine, mock_registry):
        """Test conversion analysis with invalid types"""
        mock_registry.has_type.side_effect = lambda type_id: type_id == "text"
        
        analysis = engine.analyze_conversion("text", "invalid_type")
        
        assert analysis.from_type == "text"
        assert analysis.to_type == "invalid_type"
        assert analysis.is_safe is False
        assert "Target type 'invalid_type' not found" in analysis.warnings
    
    def test_convert_element_type_success(self, engine):
        """Test successful element type conversion"""
        # Setup conversion rule
        rule = ConversionRule(
            from_type="text",
            to_type="title",
            strategy=ConversionStrategy.PRESERVE_COMPATIBLE,
            risk_level=ConversionRisk.LOW,
            mapping_rules=[
                DataMappingRule("content", "content"),
                DataMappingRule("formatting", None)  # This field will be lost
            ]
        )
        engine.add_conversion_rule(rule)
        
        element_data = {
            "content": "Hello World",
            "formatting": {"bold": True}
        }
        
        result = engine.convert_element_type(
            "elem_001", "text", "title", element_data, preserve_data=True
        )
        
        assert result.element_id == "elem_001"
        assert result.from_type == "text"
        assert result.to_type == "title"
        assert result.success is True
        assert "content" in result.preserved_data
        assert result.preserved_data["content"] == "Hello World"
        assert "formatting" in result.lost_data
    
    def test_convert_element_type_invalid_source(self, engine, mock_registry):
        """Test conversion with invalid source type"""
        mock_registry.has_type.side_effect = lambda type_id: type_id == "title"
        
        result = engine.convert_element_type("elem_001", "invalid", "title")
        
        assert result.success is False
        assert "Source type 'invalid' not found" in result.errors
    
    def test_convert_element_type_invalid_target(self, engine, mock_registry):
        """Test conversion with invalid target type"""
        mock_registry.has_type.side_effect = lambda type_id: type_id == "text"
        
        result = engine.convert_element_type("elem_001", "text", "invalid")
        
        assert result.success is False
        assert "Target type 'invalid' not found" in result.errors
    
    def test_convert_element_type_same_type(self, engine):
        """Test conversion when source and target are same"""
        result = engine.convert_element_type("elem_001", "text", "text")
        
        assert result.success is True
        assert result.from_type == "text"
        assert result.to_type == "text"
        assert "No conversion needed" in result.warnings
    
    def test_convert_element_type_with_custom_processor(self, engine):
        """Test conversion with custom processor"""
        # Register custom processor
        def title_processor(data):
            if "content" in data:
                data["content"] = data["content"].upper()
            return data
        
        engine.register_custom_processor("title_processor", title_processor)
        
        # Setup conversion rule with custom processor
        rule = ConversionRule(
            from_type="text",
            to_type="title",
            custom_processor="title_processor"
        )
        engine.add_conversion_rule(rule)
        
        element_data = {"content": "hello world"}
        
        result = engine.convert_element_type(
            "elem_001", "text", "title", element_data
        )
        
        assert result.success is True
        assert result.transformed_data["content"] == "HELLO WORLD"
    
    def test_convert_element_type_custom_processor_error(self, engine):
        """Test conversion with failing custom processor"""
        # Register custom processor that fails
        def failing_processor(data):
            raise ValueError("Processing failed")
        
        engine.register_custom_processor("failing_processor", failing_processor)
        
        rule = ConversionRule(
            from_type="text",
            to_type="title",
            custom_processor="failing_processor"
        )
        engine.add_conversion_rule(rule)
        
        result = engine.convert_element_type("elem_001", "text", "title")
        
        assert result.success is False
        assert "Custom processor failed" in result.errors[0]
    
    def test_apply_data_mapping_preserve_all(self, engine):
        """Test data mapping with preserve all strategy"""
        rule = ConversionRule(
            from_type="text",
            to_type="title",
            strategy=ConversionStrategy.PRESERVE_ALL
        )
        
        element_data = {
            "content": "Hello",
            "formatting": {"bold": True},
            "extra_field": "value"
        }
        
        preserved, transformed, lost = engine._apply_data_mapping(
            element_data, rule, {}, {}
        )
        
        # With PRESERVE_ALL, everything should be preserved
        assert "content" in preserved
        assert "formatting" in preserved
        assert "extra_field" in preserved
        assert len(lost) == 0
    
    def test_apply_data_mapping_with_rules(self, engine):
        """Test data mapping with specific mapping rules"""
        mapping_rules = [
            DataMappingRule("content", "title_content"),
            DataMappingRule("level", "level", default_value=1)
        ]
        
        rule = ConversionRule(
            from_type="text",
            to_type="title",
            strategy=ConversionStrategy.TRANSFORM,
            mapping_rules=mapping_rules
        )
        
        element_data = {
            "content": "Hello World",
            "formatting": {"bold": True}
        }
        
        source_props = {"content": str, "formatting": dict}
        target_props = {"title_content": str, "level": int}
        
        preserved, transformed, lost = engine._apply_data_mapping(
            element_data, rule, source_props, target_props
        )
        
        assert "title_content" in transformed
        assert transformed["title_content"] == "Hello World"
        assert "level" in transformed
        assert transformed["level"] == 1  # Default value
        assert "formatting" in lost
    
    def test_validate_converted_data_success(self, engine):
        """Test validation of converted data"""
        converted_data = {
            "content": "Hello World",
            "level": 1
        }
        
        target_props = {
            "content": str,
            "level": int
        }
        
        is_valid, errors = engine._validate_converted_data(converted_data, target_props)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_converted_data_type_mismatch(self, engine):
        """Test validation with type mismatch"""
        converted_data = {
            "content": "Hello World",
            "level": "not_an_int"  # Wrong type
        }
        
        target_props = {
            "content": str,
            "level": int
        }
        
        is_valid, errors = engine._validate_converted_data(converted_data, target_props)
        
        assert is_valid is False
        assert len(errors) > 0
        assert "level" in errors[0]
    
    def test_validate_converted_data_missing_required(self, engine):
        """Test validation with missing required field"""
        converted_data = {
            "content": "Hello World"
            # Missing level field
        }
        
        target_props = {
            "content": str,
            "level": int  # Required but missing
        }
        
        is_valid, errors = engine._validate_converted_data(converted_data, target_props)
        
        assert is_valid is False
        assert len(errors) > 0
        assert "level" in errors[0]
    
    def test_thread_safety(self, engine):
        """Test thread safety of conversion operations"""
        import threading
        import time
        
        results = []
        errors = []
        
        def worker(worker_id):
            try:
                # Add conversion rule
                rule = ConversionRule(
                    from_type="text",
                    to_type=f"title_{worker_id}",
                    strategy=ConversionStrategy.PRESERVE_ALL
                )
                engine.add_conversion_rule(rule)
                
                # Perform conversion
                result = engine.convert_element_type(
                    f"elem_{worker_id}",
                    "text",
                    f"title_{worker_id}",
                    {"content": f"Content {worker_id}"}
                )
                results.append(result)
                
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            thread.start()
            threads.append(thread)
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Check results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 5
        
        # Check that all conversions succeeded
        for result in results:
            assert result.success is True
        
        # Check that rules were added safely
        assert len(engine.conversion_rules) == 5


class TestConversionIntegration:
    """Integration tests for type conversion system"""
    
    def test_end_to_end_conversion_workflow(self):
        """Test complete conversion workflow"""
        # Setup
        registry = Mock(spec=TypeRegistry)
        engine = TypeConversionEngine(registry)
        
        # Configure mock types
        text_type = Mock(spec=TypeDefinition)
        text_type.type_id = "text"
        text_type.properties = {"content": str, "formatting": dict}
        
        title_type = Mock(spec=TypeDefinition)
        title_type.type_id = "title"
        title_type.properties = {"content": str, "level": int}
        
        registry.get_type.side_effect = lambda type_id: {
            "text": text_type,
            "title": title_type
        }.get(type_id)
        
        registry.has_type.side_effect = lambda type_id: type_id in ["text", "title"]
        
        # Register custom processor
        def title_processor(data):
            if "content" in data:
                data["content"] = data["content"].title()
            return data
        
        engine.register_custom_processor("title_processor", title_processor)
        
        # Add conversion rule
        rule = ConversionRule(
            from_type="text",
            to_type="title",
            strategy=ConversionStrategy.TRANSFORM,
            risk_level=ConversionRisk.LOW,
            mapping_rules=[
                DataMappingRule("content", "content"),
                DataMappingRule("level", "level", default_value=1)
            ],
            custom_processor="title_processor"
        )
        engine.add_conversion_rule(rule)
        
        # Analyze conversion
        analysis = engine.analyze_conversion("text", "title")
        assert analysis.is_safe is True
        assert analysis.risk_level == ConversionRisk.LOW
        
        # Perform conversion
        element_data = {
            "content": "hello world",
            "formatting": {"bold": True}
        }
        
        result = engine.convert_element_type(
            "elem_001", "text", "title", element_data, preserve_data=True
        )
        
        # Verify result
        assert result.success is True
        assert result.transformed_data["content"] == "Hello World"  # Processed by custom processor
        assert result.transformed_data["level"] == 1  # Default value applied
        assert "formatting" in result.lost_data  # Not mapped to target
        assert result.element_id == "elem_001"
        assert result.from_type == "text"
        assert result.to_type == "title"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])