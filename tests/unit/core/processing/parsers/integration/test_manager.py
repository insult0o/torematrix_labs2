"""Tests for parser manager integration."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from src.torematrix.core.processing.parsers.integration.manager import (
    ParserManager, ParseRequest, ParseResponse
)
from src.torematrix.core.processing.parsers.base import ParserResult, ParserMetadata
from src.torematrix.core.processing.parsers.code import CodeParser
from src.torematrix.core.processing.parsers.table import TableParser
from src.torematrix.core.processing.parsers.image import ImageParser


class TestParserManager:
    """Test parser manager functionality."""
    
    def setup_method(self):
        """Setup test environment."""
        self.config = {
            'max_concurrent': 5,
            'default_timeout': 10.0,
            'enable_caching': True,
            'enable_monitoring': True
        }
        self.manager = ParserManager(self.config)
    
    def create_mock_element(self, element_type="CodeBlock", text="def hello(): pass"):
        """Create mock element for testing."""
        element = Mock()
        element.type = element_type
        element.text = text
        element.metadata = {}
        return element
    
    def create_mock_parser_result(self, success=True, confidence=0.8):
        """Create mock parser result."""
        return ParserResult(
            success=success,
            data={"test": "data"},
            metadata=ParserMetadata(confidence=confidence),
            validation_errors=[],
            extracted_content="test content"
        )
    
    @pytest.mark.asyncio
    async def test_parse_single_element(self):
        """Test parsing a single element."""
        element = self.create_mock_element("CodeBlock", "def test(): pass")
        
        # Mock parser factory to return a code parser
        with patch.object(self.manager.factory, 'get_parser') as mock_get_parser:
            mock_parser = Mock()
            mock_parser.__class__.__name__ = "CodeParser"
            mock_parser.parse_with_monitoring = AsyncMock(
                return_value=self.create_mock_parser_result()
            )
            mock_get_parser.return_value = mock_parser
            
            # Mock cache miss
            with patch.object(self.manager.cache, 'get', return_value=None):
                response = await self.manager.parse_element(element)
        
        assert response.success
        assert response.result is not None
        assert response.parser_used == "CodeParser"
        assert not response.cache_hit
    
    @pytest.mark.asyncio
    async def test_cache_hit(self):
        """Test cache hit scenario."""
        element = self.create_mock_element()
        cached_result = self.create_mock_parser_result()
        
        # Mock cache hit
        with patch.object(self.manager.cache, 'get', return_value=cached_result):
            response = await self.manager.parse_element(element)
        
        assert response.success
        assert response.cache_hit
        assert response.parser_used == "cache"
    
    @pytest.mark.asyncio
    async def test_no_parser_found(self):
        """Test when no suitable parser is found."""
        element = self.create_mock_element("UnknownType", "unknown content")
        
        # Mock no parser available
        with patch.object(self.manager.factory, 'get_parser', return_value=None):
            with patch.object(self.manager.fallback, 'handle_no_parser', return_value=None):
                response = await self.manager.parse_element(element)
        
        assert not response.success
        assert "No suitable parser found" in response.error
    
    @pytest.mark.asyncio
    async def test_parser_timeout(self):
        """Test parser timeout handling."""
        element = self.create_mock_element()
        
        # Mock parser that times out
        with patch.object(self.manager.factory, 'get_parser') as mock_get_parser:
            mock_parser = Mock()
            mock_parser.__class__.__name__ = "SlowParser"
            mock_parser.parse_with_monitoring = AsyncMock(
                side_effect=asyncio.TimeoutError()
            )
            mock_get_parser.return_value = mock_parser
            
            with patch.object(self.manager.cache, 'get', return_value=None):
                response = await self.manager.parse_element(element, timeout=0.1)
        
        assert not response.success
        assert "timeout" in response.error.lower()
    
    @pytest.mark.asyncio
    async def test_parser_error_with_fallback(self):
        """Test parser error with successful fallback."""
        element = self.create_mock_element()
        
        # Mock parser that raises an exception
        with patch.object(self.manager.factory, 'get_parser') as mock_get_parser:
            mock_parser = Mock()
            mock_parser.__class__.__name__ = "ErrorParser"
            mock_parser.parse_with_monitoring = AsyncMock(
                side_effect=ValueError("Parser error")
            )
            mock_get_parser.return_value = mock_parser
            
            # Mock successful fallback
            fallback_response = ParseResponse(
                success=True,
                result=self.create_mock_parser_result(),
                error=None,
                processing_time=0.1,
                parser_used="fallback"
            )
            
            with patch.object(self.manager.cache, 'get', return_value=None):
                with patch.object(self.manager.fallback, 'handle_error', return_value=fallback_response):
                    response = await self.manager.parse_element(element)
        
        assert response.success
        assert response.parser_used == "fallback"
    
    @pytest.mark.asyncio
    async def test_batch_parsing(self):
        """Test batch parsing functionality."""
        elements = [
            self.create_mock_element("CodeBlock", "def func1(): pass"),
            self.create_mock_element("Table", "| A | B |\n| 1 | 2 |"),
            self.create_mock_element("Image", "chart.png")
        ]
        
        # Mock parsers for different element types
        with patch.object(self.manager.factory, 'get_parser') as mock_get_parser:
            def get_parser_side_effect(element, hints=None):
                if element.type == "CodeBlock":
                    parser = Mock()
                    parser.__class__.__name__ = "CodeParser"
                elif element.type == "Table":
                    parser = Mock()
                    parser.__class__.__name__ = "TableParser"
                else:
                    parser = Mock()
                    parser.__class__.__name__ = "ImageParser"
                
                parser.parse_with_monitoring = AsyncMock(
                    return_value=self.create_mock_parser_result()
                )
                return parser
            
            mock_get_parser.side_effect = get_parser_side_effect
            
            with patch.object(self.manager.cache, 'get', return_value=None):
                responses = await self.manager.parse_batch(elements)
        
        assert len(responses) == 3
        assert all(response.success for response in responses)
        assert responses[0].parser_used == "CodeParser"
        assert responses[1].parser_used == "TableParser"
        assert responses[2].parser_used == "ImageParser"
    
    @pytest.mark.asyncio
    async def test_batch_parsing_with_concurrency_limit(self):
        """Test batch parsing respects concurrency limits."""
        # Create more elements than the concurrency limit
        elements = [
            self.create_mock_element(f"Element{i}", f"content {i}")
            for i in range(10)  # More than max_concurrent=5
        ]
        
        parse_times = []
        
        def track_parse_time(*args, **kwargs):
            import time
            parse_times.append(time.time())
            return self.create_mock_parser_result()
        
        with patch.object(self.manager.factory, 'get_parser') as mock_get_parser:
            mock_parser = Mock()
            mock_parser.__class__.__name__ = "TestParser"
            mock_parser.parse_with_monitoring = AsyncMock(
                side_effect=track_parse_time
            )
            mock_get_parser.return_value = mock_parser
            
            with patch.object(self.manager.cache, 'get', return_value=None):
                responses = await self.manager.parse_batch(elements)
        
        assert len(responses) == 10
        assert all(response.success for response in responses)
        
        # Should have been processed in batches
        assert len(parse_times) == 10
    
    def test_statistics(self):
        """Test statistics collection."""
        # Simulate some requests
        self.manager._stats['total_requests'] = 100
        self.manager._stats['successful_parses'] = 90
        self.manager._stats['cache_hits'] = 30
        self.manager._stats['errors'] = 10
        self.manager._stats['total_time'] = 50.0
        self.manager._stats['parser_usage'] = {'CodeParser': 60, 'TableParser': 40}
        
        stats = self.manager.get_statistics()
        
        assert stats['total_requests'] == 100
        assert stats['success_rate'] == 0.9
        assert stats['cache_hit_rate'] == 0.3
        assert stats['error_rate'] == 0.1
        assert stats['average_time'] == 0.5
        assert stats['parser_usage']['CodeParser'] == 60
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test system health check."""
        # Mock healthy subsystems
        with patch.object(self.manager.cache, 'health_check') as mock_cache_health:
            with patch.object(self.manager.monitor, 'health_check') as mock_monitor_health:
                mock_cache_health.return_value = {'status': 'healthy'}
                mock_monitor_health.return_value = {'status': 'healthy'}
                
                # Mock some statistics
                self.manager._stats['total_requests'] = 100
                self.manager._stats['successful_parses'] = 95
                self.manager._stats['errors'] = 5
                self.manager._stats['total_time'] = 50.0
                
                health = await self.manager.health_check()
        
        assert health['status'] == 'healthy'
        assert 'parsers_registered' in health
        assert 'active_requests' in health
    
    @pytest.mark.asyncio
    async def test_health_check_degraded(self):
        """Test health check with degraded performance."""
        # Simulate high error rate
        self.manager._stats['total_requests'] = 100
        self.manager._stats['successful_parses'] = 80  # 20% error rate
        self.manager._stats['errors'] = 20
        self.manager._stats['total_time'] = 1500.0  # 15s average
        
        with patch.object(self.manager.cache, 'health_check') as mock_cache_health:
            with patch.object(self.manager.monitor, 'health_check') as mock_monitor_health:
                mock_cache_health.return_value = {'status': 'healthy'}
                mock_monitor_health.return_value = {'status': 'healthy'}
                
                health = await self.manager.health_check()
        
        assert health['status'] == 'degraded'
        assert 'issues' in health
    
    @pytest.mark.asyncio
    async def test_configure_parser(self):
        """Test parser configuration."""
        config = {'max_lines': 5000, 'min_confidence': 0.9}
        
        with patch.object(self.manager.factory, 'create_parser_instance') as mock_create:
            with patch.object(self.manager.factory, 'register_parser') as mock_register:
                mock_parser = Mock()
                mock_parser.__class__ = CodeParser
                mock_create.return_value = mock_parser
                
                result = await self.manager.configure_parser('code', config)
        
        assert result
        mock_create.assert_called_once_with('code', config)
        mock_register.assert_called_once()
    
    def test_reset_statistics(self):
        """Test statistics reset."""
        # Set some statistics
        self.manager._stats['total_requests'] = 100
        self.manager._stats['successful_parses'] = 90
        
        # Mock parser statistics reset
        mock_parser = Mock()
        mock_parser.reset_statistics = Mock()
        
        with patch.object(self.manager.factory, 'get_all_parsers', return_value=[mock_parser]):
            self.manager.reset_statistics()
        
        # Check that statistics are reset
        assert self.manager._stats['total_requests'] == 0
        assert self.manager._stats['successful_parses'] == 0
        mock_parser.reset_statistics.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_shutdown(self):
        """Test graceful shutdown."""
        # Mock active requests
        self.manager._active_requests = {
            'req_1': {'element_type': 'Code', 'start_time': 12345}
        }
        
        with patch.object(self.manager.cache, 'close') as mock_cache_close:
            with patch.object(self.manager.monitor, 'close') as mock_monitor_close:
                await self.manager.shutdown()
        
        mock_cache_close.assert_called_once()
        mock_monitor_close.assert_called_once()


@pytest.mark.integration
class TestParserManagerIntegration:
    """Integration tests for parser manager."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_parsing(self):
        """Test end-to-end parsing workflow."""
        # Create manager with real parsers
        manager = ParserManager({
            'enable_caching': False,  # Disable caching for predictable results
            'enable_monitoring': False  # Disable monitoring for simpler test
        })
        
        # Register real parsers
        from src.torematrix.core.processing.parsers.factory import ParserFactory
        ParserFactory.register_parser('code', CodeParser)
        ParserFactory.register_parser('table', TableParser)
        ParserFactory.register_parser('image', ImageParser)
        
        # Test different element types
        test_cases = [
            ("CodeBlock", "def hello(): return 'world'"),
            ("Table", "| Name | Age |\n| John | 25 |\n| Jane | 30 |"),
            ("Image", "A beautiful sunset over the mountains")
        ]
        
        for element_type, content in test_cases:
            element = Mock()
            element.type = element_type
            element.text = content
            element.metadata = {}
            
            response = await manager.parse_element(element)
            
            # All should succeed with real parsers
            assert response.success, f"Failed to parse {element_type}: {response.error}"
            assert response.result is not None
            assert response.parser_used is not None
    
    @pytest.mark.asyncio
    async def test_concurrent_parsing_stress(self):
        """Test concurrent parsing under load."""
        manager = ParserManager({'max_concurrent': 3})
        
        # Register code parser
        from src.torematrix.core.processing.parsers.factory import ParserFactory
        ParserFactory.register_parser('code', CodeParser)
        
        # Create multiple code elements
        elements = []
        for i in range(20):
            element = Mock()
            element.type = "CodeBlock"
            element.text = f"""
def function_{i}():
    \"\"\"Function number {i}\"\"\"
    result = {i} * 2
    return result

class Class_{i}:
    def __init__(self):
        self.value = {i}
    
    def get_value(self):
        return self.value
"""
            element.metadata = {}
            elements.append(element)
        
        import time
        start_time = time.time()
        
        responses = await manager.parse_batch(elements)
        
        processing_time = time.time() - start_time
        
        # All should succeed
        assert len(responses) == 20
        assert all(response.success for response in responses)
        
        # Should complete in reasonable time (concurrent processing)
        assert processing_time < 30.0  # Should be much faster with concurrency
        
        # Verify statistics
        stats = manager.get_statistics()
        assert stats['total_requests'] == 20
        assert stats['successful_parses'] == 20
        assert stats['error_rate'] == 0.0