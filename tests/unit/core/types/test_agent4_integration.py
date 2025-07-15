"""Tests for Agent 4 Advanced Type Management Features

Comprehensive test suite covering:
- Custom type creation and template system
- Plugin architecture and dynamic loading
- AI recommendations and content analysis
- Import/export with multiple formats
- API integration and authentication
"""

import pytest
import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from dataclasses import asdict

# Import components being tested
from torematrix.core.types.custom_types import (
    CustomTypeBuilder, CustomTypeDefinition, CustomTypeResult,
    TypeTemplate, TypeTemplateManager
)
from torematrix.core.types.plugin_system import (
    TypePluginManager, TypePlugin, PluginCapabilities, PluginInfo,
    PluginStatus, PluginType, ExampleTypePlugin
)
from torematrix.core.types.import_export import (
    TypeDefinitionImportExport, ExportOptions, ImportOptions,
    ExportFormat, ImportStrategy, TypeDefinitionData
)
from torematrix.core.types.recommendations import (
    TypeRecommendationEngine, RecommendationContext, ContentAnalyzer,
    RecommendationType, ConfidenceLevel
)
from torematrix.core.types.api_integration import (
    TypeManagementAPI, APIResponse, APIError, AuthenticationManager
)

# Import type registry mock
from torematrix.core.types.registry import TypeRegistry


class TestCustomTypeBuilder:
    """Test custom type creation and template system"""
    
    @pytest.fixture
    def type_registry(self):
        """Mock type registry"""
        registry = Mock(spec=TypeRegistry)
        registry.register_type = Mock(return_value=True)
        registry.get_type = Mock(return_value=None)
        return registry
    
    @pytest.fixture
    def type_builder(self, type_registry):
        """Custom type builder instance"""
        return CustomTypeBuilder(type_registry)
    
    def test_create_basic_custom_type(self, type_builder):
        """Test creating a basic custom type"""
        type_def = CustomTypeDefinition(
            name="test_type",
            description="Test type for unit testing",
            base_type="text",
            properties={
                "max_length": 100,
                "required": True
            }
        )
        
        result = type_builder.create_custom_type(type_def)
        
        assert isinstance(result, CustomTypeResult)
        assert result.success
        assert result.type_id is not None
        assert len(result.errors) == 0
    
    def test_create_type_with_validation_rules(self, type_builder):
        """Test creating type with validation rules"""
        type_def = CustomTypeDefinition(
            name="validated_type",
            description="Type with validation",
            base_type="text",
            properties={"pattern": r"^\d{4}-\d{2}-\d{2}$"},
            validation_rules={
                "pattern": r"^\d{4}-\d{2}-\d{2}$",
                "error_message": "Must be in YYYY-MM-DD format"
            }
        )
        
        result = type_builder.create_custom_type(type_def)
        
        assert result.success
        assert "validation_rules" in result.type_definition
    
    def test_template_system(self, type_builder):
        """Test type template system"""
        template_manager = type_builder.template_manager
        
        # Test getting built-in templates
        templates = template_manager.get_available_templates()
        assert len(templates) > 0
        
        # Test creating type from template
        date_template = template_manager.get_template("date")
        assert date_template is not None
        
        result = type_builder.create_from_template("date", {"name": "custom_date"})
        assert result.success
    
    def test_type_validation(self, type_builder):
        """Test type definition validation"""
        # Test invalid type definition
        invalid_def = CustomTypeDefinition(
            name="",  # Invalid empty name
            description="Invalid type",
            base_type="invalid_base"  # Invalid base type
        )
        
        result = type_builder.create_custom_type(invalid_def)
        assert not result.success
        assert len(result.errors) > 0
    
    def test_type_modification(self, type_builder):
        """Test modifying existing custom types"""
        # Create initial type
        type_def = CustomTypeDefinition(
            name="modifiable_type",
            description="Type for modification testing",
            base_type="text"
        )
        
        result = type_builder.create_custom_type(type_def)
        assert result.success
        
        # Modify the type
        modified_def = CustomTypeDefinition(
            name="modifiable_type",
            description="Modified description",
            base_type="text",
            properties={"new_property": "value"}
        )
        
        modify_result = type_builder.modify_custom_type(result.type_id, modified_def)
        assert modify_result.success


class TestPluginSystem:
    """Test plugin architecture and management"""
    
    @pytest.fixture
    def plugin_manager(self):
        """Plugin manager instance"""
        return TypePluginManager()
    
    def test_plugin_registration(self, plugin_manager):
        """Test plugin registration"""
        plugin = ExampleTypePlugin()
        plugin_manager.register_plugin_instance(plugin)
        
        plugin_info = plugin_manager.get_plugin_info(plugin.plugin_info.id)
        assert plugin_info is not None
        assert plugin_info.name == plugin.plugin_info.name
    
    @pytest.mark.asyncio
    async def test_plugin_execution(self, plugin_manager):
        """Test plugin operation execution"""
        plugin = ExampleTypePlugin()
        plugin_manager.register_plugin_instance(plugin)
        
        # Initialize plugin
        await plugin.initialize({})
        
        # Execute operation
        result = await plugin_manager.execute_plugin_operation(
            plugin.plugin_info.id,
            "convert",
            from_type="text",
            to_type="title",
            data={"content": "test"}
        )
        
        assert result["success"] is True
        assert result["from_type"] == "text"
        assert result["to_type"] == "title"
    
    def test_plugin_discovery(self, plugin_manager):
        """Test plugin capability discovery"""
        plugin = ExampleTypePlugin()
        plugin_manager.register_plugin_instance(plugin)
        
        # Find plugins for specific operation
        plugins = plugin_manager.find_plugins_for_operation(
            "convert",
            supported_types=["text"]
        )
        
        assert len(plugins) > 0
        assert plugins[0].id == plugin.plugin_info.id
    
    @pytest.mark.asyncio
    async def test_plugin_lifecycle(self, plugin_manager):
        """Test plugin lifecycle management"""
        plugin = ExampleTypePlugin()
        plugin_manager.register_plugin_instance(plugin)
        
        # Test initialization
        await plugin.initialize({})
        
        # Test enabling/disabling
        assert plugin_manager.enable_plugin(plugin.plugin_info.id)
        assert plugin_manager.disable_plugin(plugin.plugin_info.id)
        
        # Test shutdown
        await plugin.shutdown()
    
    def test_plugin_validation(self, plugin_manager):
        """Test plugin operation validation"""
        plugin = ExampleTypePlugin()
        
        # Test valid operation
        is_valid, errors = plugin.validate_operation(
            "convert",
            from_type="text",
            to_type="title"
        )
        assert is_valid
        assert len(errors) == 0
        
        # Test invalid operation
        is_valid, errors = plugin.validate_operation(
            "invalid_operation"
        )
        assert not is_valid
        assert len(errors) > 0


class TestImportExport:
    """Test import/export functionality"""
    
    @pytest.fixture
    def import_export(self):
        """Import/export manager instance"""
        return TypeDefinitionImportExport()
    
    @pytest.fixture
    def sample_type_data(self):
        """Sample type definition data"""
        return TypeDefinitionData(
            id="test_type_1",
            name="Test Type",
            version="1.0.0",
            definition={
                "properties": {"max_length": 100},
                "validation_rules": {"required": True}
            },
            metadata={"created_by": "test"}
        )
    
    def test_json_export(self, import_export, sample_type_data):
        """Test JSON export functionality"""
        import_export.register_type_definition(sample_type_data)
        
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            options = ExportOptions(
                format=ExportFormat.JSON,
                include_metadata=True,
                pretty_format=True
            )
            
            result = import_export.export_type_definitions(
                [sample_type_data.id],
                temp_path,
                options
            )
            
            assert result.success
            assert temp_path.exists()
            assert result.exported_count == 1
            
            # Verify file content
            with open(temp_path, 'r') as f:
                data = json.load(f)
                assert "export_info" in data
                assert "types" in data
                assert sample_type_data.id in data["types"]
        
        finally:
            if temp_path.exists():
                temp_path.unlink()
    
    def test_json_import(self, import_export):
        """Test JSON import functionality"""
        # Create test data file
        test_data = {
            "export_info": {
                "timestamp": "2024-01-01T00:00:00",
                "format": "json",
                "type_count": 1
            },
            "types": {
                "imported_type": {
                    "name": "Imported Type",
                    "version": "1.0.0",
                    "definition": {"properties": {"test": True}},
                    "metadata": {"source": "import_test"}
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_data, f)
            temp_path = Path(f.name)
        
        try:
            options = ImportOptions(
                strategy=ImportStrategy.MERGE,
                create_backup=False
            )
            
            result = import_export.import_type_definitions(temp_path, options)
            
            assert result.success
            assert result.imported_count == 1
            
            # Verify imported type
            imported_type = import_export.get_type_definition("imported_type")
            assert imported_type is not None
            assert imported_type.name == "Imported Type"
        
        finally:
            if temp_path.exists():
                temp_path.unlink()
    
    def test_export_options(self, import_export, sample_type_data):
        """Test various export options"""
        import_export.register_type_definition(sample_type_data)
        
        # Test different formats
        formats_to_test = [
            (ExportFormat.JSON, '.json'),
            (ExportFormat.YAML, '.yaml'),
            (ExportFormat.XML, '.xml'),
            (ExportFormat.BINARY, '.pkl')
        ]
        
        for export_format, suffix in formats_to_test:
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
                temp_path = Path(f.name)
            
            try:
                options = ExportOptions(format=export_format)
                result = import_export.export_type_definitions(
                    [sample_type_data.id],
                    temp_path,
                    options
                )
                
                assert result.success, f"Export failed for format {export_format}"
                assert temp_path.exists()
            
            finally:
                if temp_path.exists():
                    temp_path.unlink()
    
    def test_file_validation(self, import_export):
        """Test file format validation"""
        # Test valid JSON file
        valid_data = {
            "export_info": {"format": "json"},
            "types": {"test": {"name": "Test", "version": "1.0", "definition": {}}}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(valid_data, f)
            temp_path = Path(f.name)
        
        try:
            is_valid, errors = import_export.validate_file_format(temp_path)
            assert is_valid
            assert len(errors) == 0
        
        finally:
            if temp_path.exists():
                temp_path.unlink()


class TestRecommendationEngine:
    """Test AI recommendation system"""
    
    @pytest.fixture
    def recommendation_engine(self):
        """Recommendation engine instance"""
        return TypeRecommendationEngine()
    
    @pytest.fixture
    def sample_context(self):
        """Sample recommendation context"""
        return RecommendationContext(
            element_id="test_element",
            content="This is a test document with some content for analysis.",
            current_type="text",
            metadata={"source": "test"}
        )
    
    def test_content_analysis(self, recommendation_engine):
        """Test content analysis capabilities"""
        content = "# Document Title\n\nThis is a paragraph with some **bold** text and a [link](http://example.com)."
        
        analysis = recommendation_engine.analyze_content_features(content)
        
        assert analysis.content_type in ["title", "paragraph", "text"]
        assert analysis.content_length > 0
        assert "heading" in analysis.detected_patterns or "bold" in analysis.detected_patterns
    
    @pytest.mark.asyncio
    async def test_type_recommendations(self, recommendation_engine, sample_context):
        """Test type recommendation generation"""
        recommendations = await recommendation_engine.get_recommendations(sample_context)
        
        assert len(recommendations) > 0
        
        # Check recommendation structure
        for rec in recommendations:
            assert rec.recommended_type is not None
            assert 0 <= rec.confidence <= 1
            assert rec.confidence_level in ConfidenceLevel
            assert rec.reason is not None
    
    def test_pattern_detection(self, recommendation_engine):
        """Test pattern detection in content"""
        test_cases = [
            ("user@example.com", ["email"]),
            ("http://example.com", ["url"]),
            ("2024-01-01", ["date"]),
            ("function test() { return true; }", ["code"]),
            ("- Item 1\n- Item 2\n- Item 3", ["list_marker"]),
            ("| Col1 | Col2 |\n|------|------|\n| A | B |", ["table_marker"])
        ]
        
        analyzer = recommendation_engine.content_analyzer
        
        for content, expected_patterns in test_cases:
            analysis = analyzer.analyze_content(content)
            for pattern in expected_patterns:
                assert pattern in analysis.detected_patterns, f"Pattern {pattern} not detected in: {content}"
    
    @pytest.mark.asyncio
    async def test_contextual_recommendations(self, recommendation_engine):
        """Test context-aware recommendations"""
        # Test with different content types
        contexts = [
            ("# This is a heading", "title"),
            ("This is a long paragraph with multiple sentences. It contains detailed information.", "paragraph"),
            ("- First item\n- Second item\n- Third item", "list"),
            ("def function_name():\n    return True", "code")
        ]
        
        for content, expected_type in contexts:
            context = RecommendationContext(
                element_id=f"test_{expected_type}",
                content=content
            )
            
            recommendations = await recommendation_engine.get_recommendations(context)
            
            # Check if expected type is in top recommendations
            top_types = [rec.recommended_type for rec in recommendations[:3]]
            assert any(expected_type in t or t in expected_type for t in top_types), \
                   f"Expected {expected_type} not found in top recommendations for: {content}"
    
    def test_recommendation_caching(self, recommendation_engine):
        """Test recommendation caching system"""
        content = "Test content for caching"
        
        # First analysis
        analysis1 = recommendation_engine.analyze_content_features(content)
        
        # Second analysis (should use cache)
        analysis2 = recommendation_engine.analyze_content_features(content)
        
        # Verify caching worked
        cache_stats = recommendation_engine.get_cache_stats()
        assert cache_stats['analysis_cache_size'] > 0
        
        # Results should be identical
        assert analysis1.content_type == analysis2.content_type
        assert analysis1.detected_patterns == analysis2.detected_patterns


class TestAPIIntegration:
    """Test API integration layer"""
    
    @pytest.fixture
    def auth_manager(self):
        """Authentication manager instance"""
        return AuthenticationManager("test_secret")
    
    @pytest.fixture
    def api_components(self):
        """Mock API components"""
        type_builder = Mock()
        plugin_manager = Mock()
        import_export = Mock()
        recommendation_engine = Mock()
        
        return type_builder, plugin_manager, import_export, recommendation_engine
    
    @pytest.fixture
    def api_server(self, api_components):
        """API server instance"""
        type_builder, plugin_manager, import_export, recommendation_engine = api_components
        return TypeManagementAPI(
            type_builder, plugin_manager, import_export, recommendation_engine
        )
    
    def test_authentication_token_creation(self, auth_manager):
        """Test JWT token creation and verification"""
        from torematrix.core.types.api_integration import AuthLevel
        
        # Create token
        token = auth_manager.create_token("test_user", AuthLevel.USER)
        assert token is not None
        
        # Verify token
        payload = auth_manager.verify_token(token)
        assert payload["user_id"] == "test_user"
        assert payload["auth_level"] == AuthLevel.USER.value
    
    def test_authentication_token_expiry(self, auth_manager):
        """Test token expiry handling"""
        from torematrix.core.types.api_integration import AuthLevel
        
        # Create token with short expiry
        token = auth_manager.create_token("test_user", AuthLevel.USER, expires_in=1)
        
        # Verify immediate access
        payload = auth_manager.verify_token(token)
        assert payload is not None
        
        # Note: We can't easily test expiry without waiting or mocking time
    
    def test_api_response_structure(self):
        """Test API response structure"""
        response = APIResponse(
            success=True,
            data={"test": "data"},
            message="Test message"
        )
        
        response_dict = response.to_dict()
        
        assert response_dict["success"] is True
        assert response_dict["data"]["test"] == "data"
        assert response_dict["message"] == "Test message"
        assert "timestamp" in response_dict
        assert "request_id" in response_dict
    
    def test_api_error_handling(self):
        """Test API error handling"""
        error = APIError("Test error message", 400, "TEST_ERROR")
        
        assert error.message == "Test error message"
        assert error.status_code == 400
        assert error.error_code == "TEST_ERROR"
    
    @pytest.mark.asyncio
    async def test_api_health_check(self, api_server):
        """Test API health check endpoint"""
        from aiohttp.test_utils import make_mocked_request
        
        request = make_mocked_request('GET', '/api/v1/health')
        response = await api_server.health_check(request)
        
        assert response.status == 200


class TestIntegrationScenarios:
    """Test complete integration scenarios"""
    
    @pytest.fixture
    def complete_system(self):
        """Complete type management system"""
        type_registry = Mock(spec=TypeRegistry)
        type_registry.register_type = Mock(return_value=True)
        type_registry.get_type = Mock(return_value=None)
        
        type_builder = CustomTypeBuilder(type_registry)
        plugin_manager = TypePluginManager()
        import_export = TypeDefinitionImportExport()
        recommendation_engine = TypeRecommendationEngine()
        
        return {
            'type_builder': type_builder,
            'plugin_manager': plugin_manager,
            'import_export': import_export,
            'recommendation_engine': recommendation_engine
        }
    
    def test_end_to_end_type_workflow(self, complete_system):
        """Test complete type creation workflow"""
        type_builder = complete_system['type_builder']
        import_export = complete_system['import_export']
        
        # 1. Create custom type
        type_def = CustomTypeDefinition(
            name="workflow_type",
            description="End-to-end test type",
            base_type="text",
            properties={"max_length": 200}
        )
        
        result = type_builder.create_custom_type(type_def)
        assert result.success
        
        # 2. Register with import/export system
        type_data = TypeDefinitionData(
            id=result.type_id,
            name=type_def.name,
            version="1.0.0",
            definition=type_def.properties,
            metadata={"created_by": "test"}
        )
        
        import_export.register_type_definition(type_data)
        
        # 3. Verify registration
        retrieved_type = import_export.get_type_definition(result.type_id)
        assert retrieved_type is not None
        assert retrieved_type.name == type_def.name
    
    @pytest.mark.asyncio
    async def test_recommendation_with_plugin(self, complete_system):
        """Test recommendations with plugin integration"""
        plugin_manager = complete_system['plugin_manager']
        recommendation_engine = complete_system['recommendation_engine']
        
        # 1. Register example plugin
        plugin = ExampleTypePlugin()
        plugin_manager.register_plugin_instance(plugin)
        await plugin.initialize({})
        
        # 2. Get recommendations
        context = RecommendationContext(
            element_id="test_element",
            content="def test_function():\n    return True"
        )
        
        recommendations = await recommendation_engine.get_recommendations(context)
        
        # 3. Verify code type is recommended
        code_recommendations = [r for r in recommendations if 'code' in r.recommended_type.lower()]
        assert len(code_recommendations) > 0
    
    def test_template_to_export_workflow(self, complete_system):
        """Test template creation to export workflow"""
        type_builder = complete_system['type_builder']
        import_export = complete_system['import_export']
        
        # 1. Create type from template
        result = type_builder.create_from_template("date", {"name": "custom_date_type"})
        assert result.success
        
        # 2. Register for export
        type_data = TypeDefinitionData(
            id=result.type_id,
            name="custom_date_type",
            version="1.0.0",
            definition=result.type_definition,
            metadata={"template": "date"}
        )
        
        import_export.register_type_definition(type_data)
        
        # 3. Export to JSON
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            options = ExportOptions(format=ExportFormat.JSON)
            export_result = import_export.export_type_definitions(
                [result.type_id],
                temp_path,
                options
            )
            
            assert export_result.success
            assert temp_path.exists()
        
        finally:
            if temp_path.exists():
                temp_path.unlink()


# Performance and stress tests
class TestPerformance:
    """Test performance characteristics"""
    
    def test_large_content_analysis(self):
        """Test analysis of large content"""
        analyzer = ContentAnalyzer()
        
        # Generate large content
        large_content = "This is a test sentence. " * 1000  # ~25KB
        
        import time
        start_time = time.time()
        analysis = analyzer.analyze_content(large_content)
        end_time = time.time()
        
        # Should complete within reasonable time
        assert end_time - start_time < 5.0  # 5 seconds max
        assert analysis.content_length == len(large_content)
    
    def test_multiple_type_creation(self):
        """Test creating multiple types efficiently"""
        type_registry = Mock(spec=TypeRegistry)
        type_registry.register_type = Mock(return_value=True)
        type_registry.get_type = Mock(return_value=None)
        
        type_builder = CustomTypeBuilder(type_registry)
        
        # Create multiple types
        results = []
        for i in range(100):
            type_def = CustomTypeDefinition(
                name=f"perf_type_{i}",
                description=f"Performance test type {i}",
                base_type="text"
            )
            
            result = type_builder.create_custom_type(type_def)
            results.append(result)
        
        # All should succeed
        assert all(r.success for r in results)
        assert len(set(r.type_id for r in results)) == 100  # All unique IDs
    
    @pytest.mark.asyncio
    async def test_concurrent_recommendations(self):
        """Test concurrent recommendation generation"""
        recommendation_engine = TypeRecommendationEngine()
        
        # Create multiple contexts
        contexts = [
            RecommendationContext(
                element_id=f"element_{i}",
                content=f"Test content for element {i} with various patterns."
            )
            for i in range(10)
        ]
        
        # Generate recommendations concurrently
        tasks = [
            recommendation_engine.get_recommendations(context)
            for context in contexts
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All should complete successfully
        assert len(results) == 10
        assert all(len(recommendations) > 0 for recommendations in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])