import pytest
from torematrix.core.models.metadata import ElementMetadata
from torematrix.core.models.coordinates import Coordinates

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