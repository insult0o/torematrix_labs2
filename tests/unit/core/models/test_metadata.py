import pytest
import dataclasses
from src.torematrix.core.models.metadata import ElementMetadata
from src.torematrix.core.models.coordinates import Coordinates

def test_element_metadata_defaults():
    metadata = ElementMetadata()
    assert metadata.coordinates is None
    assert metadata.confidence == 1.0
    assert metadata.detection_method == "default"
    assert metadata.page_number is None
    assert metadata.languages == []
    assert metadata.custom_fields == {}

def test_element_metadata_with_coordinates():
    coords = Coordinates(
        layout_bbox=(0, 0, 100, 100),
        text_bbox=(10, 10, 90, 90),
        points=[(0, 0), (100, 100)],
        system="pixel"
    )
    metadata = ElementMetadata(coordinates=coords)
    assert metadata.coordinates == coords

def test_element_metadata_immutability():
    metadata = ElementMetadata()
    with pytest.raises(dataclasses.FrozenInstanceError):
        metadata.confidence = 0.5

def test_element_metadata_serialization():
    """Test metadata serialization and deserialization"""
    coords = Coordinates(
        layout_bbox=(10, 20, 100, 200),
        text_bbox=(15, 25, 95, 195),
        points=[(10, 20), (100, 200)],
        system="pixel"
    )
    
    metadata = ElementMetadata(
        coordinates=coords,
        confidence=0.85,
        detection_method="ml_hybrid",
        page_number=3,
        languages=["en", "es"],
        custom_fields={"source": "test.pdf", "complexity": "high"}
    )
    
    # Test serialization
    metadata_dict = metadata.to_dict()
    
    assert metadata_dict["confidence"] == 0.85
    assert metadata_dict["detection_method"] == "ml_hybrid"
    assert metadata_dict["page_number"] == 3
    assert metadata_dict["languages"] == ["en", "es"]
    assert metadata_dict["custom_fields"]["source"] == "test.pdf"
    assert metadata_dict["coordinates"]["layout_bbox"] == (10, 20, 100, 200)
    
    # Test deserialization
    restored_metadata = ElementMetadata.from_dict(metadata_dict)
    
    assert restored_metadata.confidence == 0.85
    assert restored_metadata.detection_method == "ml_hybrid"
    assert restored_metadata.page_number == 3
    assert restored_metadata.languages == ["en", "es"]
    assert restored_metadata.custom_fields["source"] == "test.pdf"
    assert restored_metadata.coordinates.layout_bbox == (10, 20, 100, 200)

def test_element_metadata_custom_fields():
    """Test custom fields functionality"""
    custom_fields = {
        "processing_time": 1.5,
        "model_version": "v2.1",
        "extraction_method": "deep_learning",
        "nested_data": {
            "confidence_scores": [0.9, 0.8, 0.95],
            "categories": ["text", "table"]
        },
        "boolean_flag": True,
        "null_value": None
    }
    
    metadata = ElementMetadata(custom_fields=custom_fields)
    
    assert metadata.custom_fields["processing_time"] == 1.5
    assert metadata.custom_fields["model_version"] == "v2.1"
    assert metadata.custom_fields["nested_data"]["confidence_scores"] == [0.9, 0.8, 0.95]
    assert metadata.custom_fields["boolean_flag"] is True
    assert metadata.custom_fields["null_value"] is None

def test_element_metadata_languages():
    """Test languages field functionality"""
    # Test single language
    metadata_single = ElementMetadata(languages=["en"])
    assert metadata_single.languages == ["en"]
    
    # Test multiple languages
    metadata_multi = ElementMetadata(languages=["en", "es", "fr", "de"])
    assert len(metadata_multi.languages) == 4
    assert "es" in metadata_multi.languages
    
    # Test empty languages
    metadata_empty = ElementMetadata(languages=[])
    assert metadata_empty.languages == []

def test_element_metadata_edge_cases():
    """Test edge cases and boundary conditions"""
    # Test minimum confidence
    metadata_min = ElementMetadata(confidence=0.0)
    assert metadata_min.confidence == 0.0
    
    # Test maximum confidence
    metadata_max = ElementMetadata(confidence=1.0)
    assert metadata_max.confidence == 1.0
    
    # Test large page number
    metadata_large_page = ElementMetadata(page_number=999999)
    assert metadata_large_page.page_number == 999999
    
    # Test very long detection method
    long_method = "a" * 1000
    metadata_long = ElementMetadata(detection_method=long_method)
    assert metadata_long.detection_method == long_method