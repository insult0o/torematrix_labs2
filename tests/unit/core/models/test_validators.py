import pytest
from src.torematrix.core.models.validators import validate_metadata

def test_validate_metadata_valid():
    valid_metadata = {
        "coordinates": {
            "layout_bbox": [0, 0, 100, 100],
            "text_bbox": [10, 10, 90, 90],
            "points": [[0, 0], [100, 100]],
            "system": "pixel"
        },
        "confidence": 0.95,
        "detection_method": "ml_model",
        "page_number": 1,
        "languages": ["en", "es"],
        "custom_fields": {"source": "document1"}
    }
    assert validate_metadata(valid_metadata) is True

def test_validate_metadata_invalid_confidence():
    invalid_metadata = {
        "confidence": 1.5,  # Invalid: > 1.0
        "detection_method": "ml_model"
    }
    assert validate_metadata(invalid_metadata) is False

def test_validate_metadata_invalid_coordinates():
    invalid_metadata = {
        "coordinates": {
            "layout_bbox": [0, 0, 100],  # Invalid: needs 4 values
            "system": "invalid_system"  # Invalid: not in enum
        }
    }
    assert validate_metadata(invalid_metadata) is False

def test_validate_metadata_comprehensive():
    """Comprehensive validation tests for metadata"""
    
    # Test all valid cases
    valid_cases = [
        # Minimal valid metadata
        {},
        
        # Full metadata
        {
            "coordinates": {
                "layout_bbox": [0, 0, 100, 100],
                "text_bbox": [5, 5, 95, 95],
                "points": [[0, 0], [100, 100]],
                "system": "pixel"
            },
            "confidence": 0.95,
            "detection_method": "advanced_ml",
            "page_number": 1,
            "languages": ["en"],
            "custom_fields": {"key": "value"}
        },
        
        # Edge cases
        {"confidence": 0.0},  # Minimum confidence
        {"confidence": 1.0},  # Maximum confidence
        {"page_number": 0},   # Page 0
        {"page_number": 9999}, # Large page number
        {"languages": []},    # Empty languages
        {"languages": ["en", "es", "fr", "de", "zh"]}, # Many languages
        {"custom_fields": {}}, # Empty custom fields
        {"custom_fields": {"nested": {"deep": {"value": 123}}}}, # Nested data
    ]
    
    for i, metadata in enumerate(valid_cases):
        assert validate_metadata(metadata) is True, f"Valid case {i} failed: {metadata}"
    
    # Test all invalid cases
    invalid_cases = [
        # Invalid confidence values
        {"confidence": -0.1},   # Below 0
        {"confidence": 1.1},    # Above 1
        {"confidence": "high"}, # Wrong type
        {"confidence": None},   # None value
        
        # Invalid page numbers
        {"page_number": -1},    # Negative page
        {"page_number": "one"}, # Wrong type
        
        # Invalid languages
        {"languages": "english"}, # Should be list
        {"languages": [123]},      # Wrong element type
        
        # Invalid coordinates
        {
            "coordinates": {
                "layout_bbox": [0, 0, 100],  # Wrong length
                "system": "pixel"
            }
        },
        {
            "coordinates": {
                "layout_bbox": [0, 0, 100, 100],
                "system": "invalid_system"    # Invalid system
            }
        },
        {
            "coordinates": {
                "layout_bbox": ["0", "0", "100", "100"],  # Wrong type
                "system": "pixel"
            }
        },
        {
            "coordinates": {
                "text_bbox": [0, 0, 100, 100, 50],  # Wrong length
                "system": "pixel"
            }
        },
        {
            "coordinates": {
                "points": [[0, 0], [100]],  # Invalid points format
                "system": "pixel"
            }
        },
    ]
    
    for i, metadata in enumerate(invalid_cases):
        assert validate_metadata(metadata) is False, f"Invalid case {i} should have failed: {metadata}"

def test_validate_metadata_coordinates_systems():
    """Test coordinate system validation"""
    valid_systems = ["pixel", "normalized", "page"]
    
    for system in valid_systems:
        metadata = {
            "coordinates": {
                "layout_bbox": [0, 0, 100, 100],
                "system": system
            }
        }
        assert validate_metadata(metadata) is True, f"System '{system}' should be valid"
    
    invalid_systems = ["invalid", "pixels", "PIXEL", "", None, 123]
    
    for system in invalid_systems:
        metadata = {
            "coordinates": {
                "layout_bbox": [0, 0, 100, 100],
                "system": system
            }
        }
        assert validate_metadata(metadata) is False, f"System '{system}' should be invalid"

def test_validate_metadata_bbox_formats():
    """Test bounding box format validation"""
    # Valid bbox formats
    valid_bboxes = [
        [0, 0, 100, 100],           # Integers
        [0.0, 0.0, 100.5, 100.5],   # Floats
        [0, 0, 1000, 2000],         # Large values
    ]
    
    for bbox in valid_bboxes:
        metadata = {
            "coordinates": {
                "layout_bbox": bbox,
                "system": "pixel"
            }
        }
        assert validate_metadata(metadata) is True, f"BBox {bbox} should be valid"
    
    # Invalid bbox formats
    invalid_bboxes = [
        [0, 0, 100],              # Too few values
        [0, 0, 100, 100, 50],     # Too many values
        ["0", "0", "100", "100"], # String values
        [None, 0, 100, 100],      # None values
        [],                       # Empty
        None,                     # None bbox
    ]
    
    for bbox in invalid_bboxes:
        metadata = {
            "coordinates": {
                "layout_bbox": bbox,
                "system": "pixel"
            }
        }
        assert validate_metadata(metadata) is False, f"BBox {bbox} should be invalid"

def test_validate_metadata_points_format():
    """Test points format validation"""
    # Valid points formats
    valid_points = [
        [[0, 0], [100, 100]],                    # Simple rectangle
        [[0, 0], [50, 0], [50, 100], [0, 100]], # Complex polygon
        [[10.5, 20.5], [90.5, 180.5]],          # Float coordinates
    ]
    
    for points in valid_points:
        metadata = {
            "coordinates": {
                "points": points,
                "system": "pixel"
            }
        }
        assert validate_metadata(metadata) is True, f"Points {points} should be valid"
    
    # Invalid points formats
    invalid_points = [
        [[0, 0], [100]],           # Incomplete point
        [[0], [100, 100]],         # Incomplete point
        [["0", "0"], [100, 100]],  # String coordinates
        [[0, 0, 0], [100, 100]],   # 3D coordinates
        [],                        # Empty points
        [[0, 0]],                  # Single point
        None,                      # None points
    ]
    
    for points in invalid_points:
        metadata = {
            "coordinates": {
                "points": points,
                "system": "pixel"
            }
        }
        assert validate_metadata(metadata) is False, f"Points {points} should be invalid"

def test_validate_metadata_custom_fields():
    """Test custom fields validation"""
    # Valid custom fields
    valid_custom_fields = [
        {},                                           # Empty
        {"simple": "value"},                         # Simple string
        {"number": 123},                             # Number
        {"boolean": True},                           # Boolean
        {"null": None},                              # None value
        {"list": [1, 2, 3]},                        # List
        {"nested": {"key": "value"}},                # Nested dict
        {"complex": {"list": [{"key": "value"}]}},   # Complex nesting
    ]
    
    for custom_fields in valid_custom_fields:
        metadata = {"custom_fields": custom_fields}
        assert validate_metadata(metadata) is True, f"Custom fields {custom_fields} should be valid"

def test_validate_metadata_detection_methods():
    """Test detection method validation"""
    # Valid detection methods (strings)
    valid_methods = [
        "manual",
        "ml_model",
        "rule_based",
        "hybrid",
        "advanced_ml_v2.1",
        "a" * 1000,  # Very long method name
        "",          # Empty string
    ]
    
    for method in valid_methods:
        metadata = {"detection_method": method}
        assert validate_metadata(metadata) is True, f"Method '{method}' should be valid"
    
    # Invalid detection methods
    invalid_methods = [
        123,     # Number
        None,    # None
        [],      # List
        {},      # Dict
        True,    # Boolean
    ]
    
    for method in invalid_methods:
        metadata = {"detection_method": method}
        assert validate_metadata(metadata) is False, f"Method '{method}' should be invalid"