"""Tests for property data models"""

import pytest
from datetime import datetime
from src.torematrix.ui.components.property_panel.models import (
    PropertyValue, PropertyMetadata, PropertyChange, PropertyHistory, ChangeType
)

class TestPropertyValue:
    def test_creation(self):
        """Test PropertyValue creation"""
        value = PropertyValue(value="test", property_type="string")
        assert value.value == "test"
        assert value.property_type == "string"
        assert isinstance(value.timestamp, datetime)
        assert value.user_id is None
        assert value.source == "user"
    
    def test_creation_with_user(self):
        """Test PropertyValue creation with user"""
        value = PropertyValue(
            value=42, 
            property_type="integer", 
            user_id="user123",
            source="import"
        )
        assert value.value == 42
        assert value.property_type == "integer"
        assert value.user_id == "user123"
        assert value.source == "import"
    
    def test_serialization(self):
        """Test PropertyValue serialization"""
        value = PropertyValue(value=42, property_type="integer")
        data = value.to_dict()
        
        assert data["value"] == 42
        assert data["property_type"] == "integer"
        assert "timestamp" in data
        assert data["user_id"] is None
        assert data["source"] == "user"
        
        # Test deserialization
        restored = PropertyValue.from_dict(data)
        assert restored.value == 42
        assert restored.property_type == "integer"
        assert restored.user_id is None
        assert restored.source == "user"
    
    def test_serialization_complex_value(self):
        """Test PropertyValue serialization with complex values"""
        complex_value = {"x": 10.5, "y": 20.3}
        value = PropertyValue(value=complex_value, property_type="coordinate")
        data = value.to_dict()
        restored = PropertyValue.from_dict(data)
        
        assert restored.value == complex_value
        assert restored.property_type == "coordinate"

class TestPropertyMetadata:
    def test_creation(self):
        """Test PropertyMetadata creation"""
        metadata = PropertyMetadata(
            name="text",
            display_name="Text Content",
            description="The text content of the element"
        )
        assert metadata.name == "text"
        assert metadata.display_name == "Text Content"
        assert metadata.description == "The text content of the element"
        assert metadata.category == "General"
        assert metadata.editable is True
        assert metadata.visible is True
        assert metadata.validation_rules == []
        assert metadata.custom_attributes == {}
    
    def test_creation_with_attributes(self):
        """Test PropertyMetadata creation with custom attributes"""
        metadata = PropertyMetadata(
            name="confidence",
            display_name="Confidence Score",
            description="AI confidence score",
            category="Analysis",
            editable=False,
            validation_rules=["range:0-1"],
            custom_attributes={"color_coded": True, "precision": 3}
        )
        assert metadata.category == "Analysis"
        assert metadata.editable is False
        assert metadata.validation_rules == ["range:0-1"]
        assert metadata.custom_attributes["color_coded"] is True
        assert metadata.custom_attributes["precision"] == 3
    
    def test_serialization(self):
        """Test PropertyMetadata serialization"""
        metadata = PropertyMetadata(
            name="x",
            display_name="X Coordinate",
            description="X position"
        )
        data = metadata.to_dict()
        
        assert data["name"] == "x"
        assert data["display_name"] == "X Coordinate"
        assert data["description"] == "X position"
        assert data["category"] == "General"
        assert data["editable"] is True

class TestPropertyChange:
    def test_creation(self):
        """Test PropertyChange creation"""
        change = PropertyChange(
            element_id="elem1",
            property_name="text",
            old_value="old text",
            new_value="new text",
            change_type=ChangeType.UPDATE
        )
        assert change.element_id == "elem1"
        assert change.property_name == "text"
        assert change.old_value == "old text"
        assert change.new_value == "new text"
        assert change.change_type == ChangeType.UPDATE
        assert isinstance(change.timestamp, datetime)
    
    def test_can_undo(self):
        """Test PropertyChange undo capability"""
        # Update change can be undone
        update_change = PropertyChange(
            element_id="elem1",
            property_name="text",
            old_value="old",
            new_value="new",
            change_type=ChangeType.UPDATE
        )
        assert update_change.can_undo() is True
        
        # Create change can be undone
        create_change = PropertyChange(
            element_id="elem1",
            property_name="text",
            old_value=None,
            new_value="new",
            change_type=ChangeType.CREATE
        )
        assert create_change.can_undo() is True
        
        # Delete change can be undone
        delete_change = PropertyChange(
            element_id="elem1",
            property_name="text",
            old_value="old",
            new_value=None,
            change_type=ChangeType.DELETE
        )
        assert delete_change.can_undo() is True
        
        # Reset change can be undone
        reset_change = PropertyChange(
            element_id="elem1",
            property_name="text",
            old_value="modified",
            new_value="original",
            change_type=ChangeType.RESET
        )
        assert reset_change.can_undo() is True
    
    def test_create_undo_change(self):
        """Test PropertyChange undo creation"""
        # Test UPDATE undo
        change = PropertyChange(
            element_id="elem1",
            property_name="text",
            old_value="old",
            new_value="new",
            change_type=ChangeType.UPDATE
        )
        undo_change = change.create_undo_change()
        assert undo_change.old_value == "new"
        assert undo_change.new_value == "old"
        assert undo_change.change_type == ChangeType.UPDATE
        assert "Undo:" in undo_change.description
        
        # Test CREATE undo
        create_change = PropertyChange(
            element_id="elem1",
            property_name="text",
            old_value=None,
            new_value="new",
            change_type=ChangeType.CREATE
        )
        undo_create = create_change.create_undo_change()
        assert undo_create.old_value == "new"
        assert undo_create.new_value is None
        assert undo_create.change_type == ChangeType.DELETE
        
        # Test DELETE undo
        delete_change = PropertyChange(
            element_id="elem1",
            property_name="text",
            old_value="old",
            new_value=None,
            change_type=ChangeType.DELETE
        )
        undo_delete = delete_change.create_undo_change()
        assert undo_delete.old_value is None
        assert undo_delete.new_value == "old"
        assert undo_delete.change_type == ChangeType.CREATE
    
    def test_serialization(self):
        """Test PropertyChange serialization"""
        change = PropertyChange(
            element_id="elem1",
            property_name="text",
            old_value="old",
            new_value="new",
            change_type=ChangeType.UPDATE,
            user_id="user123",
            description="Manual edit"
        )
        data = change.to_dict()
        
        assert data["element_id"] == "elem1"
        assert data["property_name"] == "text"
        assert data["old_value"] == "old"
        assert data["new_value"] == "new"
        assert data["change_type"] == "update"
        assert data["user_id"] == "user123"
        assert data["description"] == "Manual edit"
        assert "timestamp" in data

class TestPropertyHistory:
    def test_creation(self):
        """Test PropertyHistory creation"""
        history = PropertyHistory()
        assert history.get_history_count() == 0
        assert history.get_changes() == []
    
    def test_add_change(self):
        """Test adding changes to history"""
        history = PropertyHistory()
        change = PropertyChange(
            element_id="elem1",
            property_name="text",
            old_value="old",
            new_value="new",
            change_type=ChangeType.UPDATE
        )
        
        history.add_change(change)
        assert history.get_history_count() == 1
        changes = history.get_changes()
        assert len(changes) == 1
        assert changes[0] == change
    
    def test_filtered_changes(self):
        """Test filtered change retrieval"""
        history = PropertyHistory()
        
        # Add changes for different elements and properties
        change1 = PropertyChange("elem1", "text", "old1", "new1", ChangeType.UPDATE)
        change2 = PropertyChange("elem1", "x", 10, 20, ChangeType.UPDATE)
        change3 = PropertyChange("elem2", "text", "old2", "new2", ChangeType.UPDATE)
        
        history.add_change(change1)
        history.add_change(change2)
        history.add_change(change3)
        
        # Filter by element
        elem1_changes = history.get_changes(element_id="elem1")
        assert len(elem1_changes) == 2
        assert change1 in elem1_changes
        assert change2 in elem1_changes
        
        # Filter by property
        text_changes = history.get_changes(property_name="text")
        assert len(text_changes) == 2
        assert change1 in text_changes
        assert change3 in text_changes
        
        # Filter by both
        elem1_text_changes = history.get_changes(element_id="elem1", property_name="text")
        assert len(elem1_text_changes) == 1
        assert elem1_text_changes[0] == change1
    
    def test_get_last_change(self):
        """Test getting last change for a property"""
        history = PropertyHistory()
        
        change1 = PropertyChange("elem1", "text", "old1", "new1", ChangeType.UPDATE)
        change2 = PropertyChange("elem1", "text", "new1", "new2", ChangeType.UPDATE)
        
        history.add_change(change1)
        history.add_change(change2)
        
        last_change = history.get_last_change("elem1", "text")
        assert last_change == change2
        
        # Non-existent property
        no_change = history.get_last_change("elem1", "nonexistent")
        assert no_change is None
    
    def test_clear_history(self):
        """Test clearing history"""
        history = PropertyHistory()
        
        change1 = PropertyChange("elem1", "text", "old1", "new1", ChangeType.UPDATE)
        change2 = PropertyChange("elem2", "text", "old2", "new2", ChangeType.UPDATE)
        
        history.add_change(change1)
        history.add_change(change2)
        assert history.get_history_count() == 2
        
        # Clear specific element
        history.clear_history(element_id="elem1")
        assert history.get_history_count() == 1
        remaining = history.get_changes()
        assert remaining[0] == change2
        
        # Clear all
        history.clear_history()
        assert history.get_history_count() == 0
    
    def test_max_history_limit(self):
        """Test history size limit"""
        history = PropertyHistory(max_history=3)
        
        # Add more changes than limit
        for i in range(5):
            change = PropertyChange(
                f"elem{i}", "text", f"old{i}", f"new{i}", ChangeType.UPDATE
            )
            history.add_change(change)
        
        # Should only keep last 3
        assert history.get_history_count() == 3
        changes = history.get_changes()
        
        # Should have changes 2, 3, 4 (newest 3)
        assert changes[0].element_id == "elem2"
        assert changes[1].element_id == "elem3"
        assert changes[2].element_id == "elem4"