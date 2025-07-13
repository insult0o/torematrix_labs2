"""Unit tests for incremental processor."""

import time
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime

from torematrix.core.cache.incremental_processor import IncrementalProcessor
from torematrix.core.cache.multi_level_cache import MultiLevelCache


class TestProcessor(IncrementalProcessor):
    """Test implementation of incremental processor."""
    
    def _extract_page_info(self, document_path: Path) -> list:
        """Mock page extraction."""
        return [
            {
                'page_number': 1,
                'text': 'page 1',
                'bbox': [0, 0, 100, 100]
            },
            {
                'page_number': 2,
                'text': 'page 2',
                'bbox': [0, 0, 100, 100]
            }
        ]
    
    def _extract_page(self, document_path: Path, page_num: int) -> dict:
        """Mock single page extraction."""
        return {
            'page_number': page_num,
            'text': f'page {page_num}',
            'bbox': [0, 0, 100, 100]
        }
    
    def _process_page(self, page_data: dict) -> dict:
        """Mock page processing."""
        return {
            'page_number': page_data['page_number'],
            'processed_text': f"processed {page_data['text']}",
            'layout': {'bbox': page_data['bbox']}
        }


@pytest.fixture
def cache():
    """Create a mock cache."""
    return Mock(spec=MultiLevelCache)


@pytest.fixture
def processor(cache):
    """Create a test processor instance."""
    return TestProcessor(cache)


def test_full_processing(processor, cache, tmp_path):
    """Test full document processing."""
    file_path = tmp_path / "test.txt"
    with open(file_path, "w") as f:
        f.write("test content")
    
    # No cached result
    cache.get.return_value = None
    
    result = processor.process_document_incremental(file_path)
    
    assert len(result['pages']) == 2
    assert result['metadata']['page_count'] == 2
    assert not result['metadata']['incremental_update']
    
    # Verify cache operations
    assert cache.set.call_count == 3  # Full result + 2 pages


def test_unchanged_document(processor, cache, tmp_path):
    """Test processing unchanged document."""
    file_path = tmp_path / "test.txt"
    with open(file_path, "w") as f:
        f.write("test content")
    
    # Process once to populate cache
    cached_result = {
        'document_id': 'test',
        'pages': [{'page_number': 1}, {'page_number': 2}],
        'metadata': {'page_count': 2}
    }
    cache.get.return_value = cached_result
    
    # Process again without changes
    result = processor.process_document_incremental(file_path)
    
    assert result == cached_result
    assert cache.set.call_count == 0  # No new cache entries


def test_partial_changes(processor, cache, tmp_path):
    """Test processing document with partial changes."""
    file_path = tmp_path / "test.txt"
    with open(file_path, "w") as f:
        f.write("initial content")
    
    # Previous result with two pages
    previous_result = {
        'document_id': 'test',
        'pages': [
            {'page_number': 1, 'content': 'old page 1'},
            {'page_number': 2, 'content': 'old page 2'}
        ],
        'metadata': {'page_count': 2}
    }
    
    def mock_cache_get(key: str):
        if key == 'result:test':
            return previous_result
        return None
    
    cache.get.side_effect = mock_cache_get
    
    # Modify file to trigger change detection
    time.sleep(0.1)  # Ensure mtime changes
    with open(file_path, "w") as f:
        f.write("modified content")
    
    # Mock change detector to report only page 2 changed
    with patch('torematrix.core.cache.change_detector.ChangeDetector') as mock:
        mock.return_value.get_changed_pages.return_value = [2]
        mock.return_value.has_file_changed.return_value = True
        processor.change_detector = mock.return_value
        
        result = processor.process_document_incremental(file_path)
    
    assert result['metadata']['incremental_update']
    assert result['metadata']['changed_pages'] == [2]
    assert cache.set.call_count == 2  # Updated page + full result


def test_force_full_processing(processor, cache, tmp_path):
    """Test forced full processing."""
    file_path = tmp_path / "test.txt"
    with open(file_path, "w") as f:
        f.write("test content")
    
    # Cached result exists
    cache.get.return_value = {
        'document_id': 'test',
        'pages': [{'page_number': 1}, {'page_number': 2}],
        'metadata': {'page_count': 2}
    }
    
    # Force full processing
    result = processor.process_document_incremental(file_path, force_full=True)
    
    assert not result['metadata']['incremental_update']
    assert cache.set.call_count == 3  # Full result + 2 pages


def test_too_many_changes(processor, cache, tmp_path):
    """Test fallback to full processing when too many changes."""
    file_path = tmp_path / "test.txt"
    with open(file_path, "w") as f:
        f.write("initial content")
    
    # Previous result exists
    cache.get.return_value = {
        'document_id': 'test',
        'pages': [{'page_number': i} for i in range(1, 11)],
        'metadata': {'page_count': 10}
    }
    
    # Mock change detector to report many changes
    with patch('torematrix.core.cache.change_detector.ChangeDetector') as mock:
        mock.return_value.get_changed_pages.return_value = [1, 2, 3, 4]  # >30%
        mock.return_value.has_file_changed.return_value = True
        processor.change_detector = mock.return_value
        
        result = processor.process_document_incremental(file_path)
    
    assert not result['metadata']['incremental_update']
    assert cache.set.call_count > len(result['pages'])  # Full reprocess