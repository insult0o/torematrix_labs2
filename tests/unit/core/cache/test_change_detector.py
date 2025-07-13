"""Unit tests for change detection system."""

import time
import json
import pytest
from pathlib import Path
from datetime import datetime

from torematrix.core.cache.change_detector import ChangeDetector


@pytest.fixture
def detector():
    """Create a test change detector instance."""
    return ChangeDetector()


def test_file_change_detection(detector, tmp_path):
    """Test file change detection."""
    file_path = tmp_path / "test.txt"
    
    # Create initial file
    with open(file_path, "w") as f:
        f.write("initial content")
    
    # First check should indicate change
    assert detector.has_file_changed(file_path)
    
    # Second check with no changes should return False
    assert not detector.has_file_changed(file_path)
    
    # Modify file
    time.sleep(0.1)  # Ensure mtime changes
    with open(file_path, "w") as f:
        f.write("modified content")
    
    # Should detect change
    assert detector.has_file_changed(file_path)


def test_page_change_detection(detector):
    """Test page-level change detection."""
    document_id = "test_doc"
    initial_pages = [
        {
            'page_number': 1,
            'text': 'page 1',
            'bbox': [0, 0, 100, 100],
            'elements': []
        },
        {
            'page_number': 2,
            'text': 'page 2',
            'bbox': [0, 0, 100, 100],
            'elements': []
        }
    ]
    
    # First check should detect all pages as changed
    changed = detector.get_changed_pages(document_id, initial_pages)
    assert changed == [1, 2]
    
    # No changes should be detected
    changed = detector.get_changed_pages(document_id, initial_pages)
    assert not changed
    
    # Modify page 2
    modified_pages = initial_pages.copy()
    modified_pages[1]['text'] = 'modified page 2'
    
    changed = detector.get_changed_pages(document_id, modified_pages)
    assert changed == [2]


def test_section_change_detection(detector):
    """Test section-level change detection."""
    document_id = "test_doc"
    initial_sections = [
        {
            'id': 'section1',
            'title': 'Section 1',
            'content': 'content 1'
        },
        {
            'id': 'section2',
            'title': 'Section 2',
            'content': 'content 2'
        }
    ]
    
    # First check should detect all sections as changed
    changed = detector.get_changed_sections(document_id, initial_sections)
    assert changed == ['section1', 'section2']
    
    # No changes should be detected
    changed = detector.get_changed_sections(document_id, initial_sections)
    assert not changed
    
    # Modify section 1
    modified_sections = initial_sections.copy()
    modified_sections[0]['content'] = 'modified content 1'
    
    changed = detector.get_changed_sections(document_id, modified_sections)
    assert changed == ['section1']


def test_document_hash_computation(detector, tmp_path):
    """Test document hash computation."""
    file_path = tmp_path / "test.txt"
    with open(file_path, "w") as f:
        f.write("test content")
    
    document = {
        'path': str(file_path),
        'content': 'test content',
        'structure': {'type': 'text'},
        'metadata': {'author': 'test'},
        'pages': [
            {
                'page_number': 1,
                'text': 'page 1',
                'bbox': [0, 0, 100, 100],
                'elements': []
            }
        ]
    }
    
    hashes = detector.compute_document_hash(document)
    
    assert 'file' in hashes
    assert 'content' in hashes
    assert 'structure' in hashes
    assert 'metadata' in hashes
    assert 'page_hashes' in hashes
    assert len(hashes['page_hashes']) == 1


def test_change_detection(detector):
    """Test change detection between versions."""
    old_hashes = {
        'file': 'abc123',
        'content': 'def456',
        'structure': 'ghi789',
        'metadata': 'jkl012',
        'page_hashes': ['page1', 'page2']
    }
    
    # Test no changes
    new_hashes = old_hashes.copy()
    changes = detector.detect_changes(old_hashes, new_hashes)
    assert changes['type'] == 'none'
    assert not changes['affected_pages']
    assert not changes['metadata_changed']
    assert not changes['structure_changed']
    
    # Test page changes
    new_hashes = old_hashes.copy()
    new_hashes['content'] = 'modified'
    new_hashes['page_hashes'] = ['page1', 'modified']
    changes = detector.detect_changes(old_hashes, new_hashes)
    assert changes['type'] == 'partial'
    assert changes['affected_pages'] == [2]
    assert not changes['structure_changed']
    
    # Test structural changes
    new_hashes = old_hashes.copy()
    new_hashes['content'] = 'modified'
    new_hashes['structure'] = 'modified'
    changes = detector.detect_changes(old_hashes, new_hashes)
    assert changes['type'] == 'full'
    assert changes['structure_changed']
    
    # Test metadata changes
    new_hashes = old_hashes.copy()
    new_hashes['metadata'] = 'modified'
    changes = detector.detect_changes(old_hashes, new_hashes)
    assert changes['metadata_changed']