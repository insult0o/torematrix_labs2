import pytest
from pathlib import Path
import tempfile
import shutil
from unittest.mock import Mock, patch
from torematrix.infrastructure.parsers.parser_cache import PDFParserCache, CacheConfig
from torematrix.infrastructure.parsers.pdf_parser_base import ParseResult

@pytest.fixture
def temp_cache_dir():
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def cache_config(temp_cache_dir):
    return CacheConfig(
        memory_cache_size=100,
        memory_cache_ttl=3600,
        disk_cache_path=temp_cache_dir,
        disk_cache_size=1_000_000,  # 1MB for testing
        use_redis=False
    )

@pytest.fixture
def parser_cache(cache_config):
    return PDFParserCache(cache_config)

@pytest.fixture
def sample_result():
    return ParseResult(
        text="sample text",
        confidence=0.8,
        page_count=1,
        has_tables=False,
        has_forms=False,
        has_images=False,
        pages=["sample text"]
    )

def test_generate_key(parser_cache):
    file_path = Path("test.pdf")
    parser_name = "test_parser"
    
    with patch.object(file_path, 'read_bytes') as mock_read:
        mock_read.return_value = b"test content"
        key = parser_cache.generate_key(file_path, parser_name)
        
        assert key.startswith("parse:test_parser:test.pdf:")
        assert len(key) > len("parse:test_parser:test.pdf:")  # Should include hash

def test_cache_get_and_set(parser_cache, sample_result):
    key = "test_key"
    
    # Test set
    parser_cache.set(key, sample_result)
    
    # Test get from memory cache
    result = parser_cache.get(key)
    assert result == sample_result
    
    # Clear memory cache to test disk cache
    parser_cache.memory_cache.clear()
    
    # Test get from disk cache
    result = parser_cache.get(key)
    assert result == sample_result
    assert key in parser_cache.memory_cache  # Should be promoted to memory

def test_cache_with_ttl(parser_cache, sample_result):
    key = "test_key_ttl"
    
    # Set with TTL
    parser_cache.set(key, sample_result, ttl=1)
    
    # Should be in cache initially
    assert parser_cache.get(key) == sample_result
    
    # Wait for TTL to expire
    import time
    time.sleep(2)
    
    # Should be expired from memory cache
    assert key not in parser_cache.memory_cache

def test_get_or_parse(parser_cache, sample_result):
    file_path = Path("test.pdf")
    parser_name = "test_parser"
    mock_parser = Mock(return_value=sample_result)
    
    with patch.object(file_path, 'read_bytes') as mock_read:
        mock_read.return_value = b"test content"
        
        # First call should parse
        result = parser_cache.get_or_parse(file_path, parser_name, mock_parser)
        assert result == sample_result
        assert mock_parser.call_count == 1
        
        # Second call should use cache
        result = parser_cache.get_or_parse(file_path, parser_name, mock_parser)
        assert result == sample_result
        assert mock_parser.call_count == 1  # Should not call parser again