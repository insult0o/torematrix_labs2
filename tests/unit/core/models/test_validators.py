import pytest
from torematrix.core.models.validators import validate_metadata

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