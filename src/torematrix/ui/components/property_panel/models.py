"""Core property data models with serialization and validation support"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json

class ChangeType(Enum):
    CREATE = "create"
    UPDATE = "update" 
    DELETE = "delete"
    RESET = "reset"

@dataclass
class PropertyValue:
    """Type-safe property value container"""
    value: Any
    property_type: str
    timestamp: datetime = field(default_factory=datetime.now)
    user_id: Optional[str] = None
    source: str = "user"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "value": self.value,
            "property_type": self.property_type,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "source": self.source
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PropertyValue':
        """Create from dictionary"""
        return cls(
            value=data["value"],
            property_type=data["property_type"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            user_id=data.get("user_id"),
            source=data.get("source", "user")
        )

@dataclass
class PropertyMetadata:
    """Property metadata with validation rules"""
    name: str
    display_name: str
    description: str
    category: str = "General"
    editable: bool = True
    visible: bool = True
    validation_rules: List[str] = field(default_factory=list)
    custom_attributes: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "category": self.category,
            "editable": self.editable,
            "visible": self.visible,
            "validation_rules": self.validation_rules,
            "custom_attributes": self.custom_attributes
        }

@dataclass
class PropertyChange:
    """Property change event with undo/redo support"""
    element_id: str
    property_name: str
    old_value: Any
    new_value: Any
    change_type: ChangeType
    timestamp: datetime = field(default_factory=datetime.now)
    user_id: Optional[str] = None
    description: str = ""
    
    def can_undo(self) -> bool:
        """Check if this change can be undone"""
        return self.change_type in [ChangeType.UPDATE, ChangeType.CREATE, ChangeType.DELETE, ChangeType.RESET]
    
    def create_undo_change(self) -> 'PropertyChange':
        """Create the inverse change for undo"""
        if self.change_type == ChangeType.UPDATE:
            return PropertyChange(
                element_id=self.element_id,
                property_name=self.property_name,
                old_value=self.new_value,
                new_value=self.old_value,
                change_type=ChangeType.UPDATE,
                description=f"Undo: {self.description}"
            )
        elif self.change_type == ChangeType.CREATE:
            return PropertyChange(
                element_id=self.element_id,
                property_name=self.property_name,
                old_value=self.new_value,
                new_value=None,
                change_type=ChangeType.DELETE,
                description=f"Undo: {self.description}"
            )
        elif self.change_type == ChangeType.DELETE:
            return PropertyChange(
                element_id=self.element_id,
                property_name=self.property_name,
                old_value=None,
                new_value=self.old_value,
                change_type=ChangeType.CREATE,
                description=f"Undo: {self.description}"
            )
        else:
            raise ValueError(f"Cannot undo change type: {self.change_type}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "element_id": self.element_id,
            "property_name": self.property_name,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "change_type": self.change_type.value,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "description": self.description
        }

class PropertyHistory:
    """Property change history manager"""
    
    def __init__(self, max_history: int = 1000):
        self._changes: List[PropertyChange] = []
        self._max_history = max_history
    
    def add_change(self, change: PropertyChange) -> None:
        """Add a new change to history"""
        self._changes.append(change)
        if len(self._changes) > self._max_history:
            self._changes.pop(0)
    
    def get_changes(self, element_id: Optional[str] = None, 
                   property_name: Optional[str] = None) -> List[PropertyChange]:
        """Get filtered change history"""
        changes = self._changes
        if element_id:
            changes = [c for c in changes if c.element_id == element_id]
        if property_name:
            changes = [c for c in changes if c.property_name == property_name]
        return changes
    
    def get_last_change(self, element_id: str, property_name: str) -> Optional[PropertyChange]:
        """Get the most recent change for a property"""
        changes = self.get_changes(element_id, property_name)
        return changes[-1] if changes else None
    
    def clear_history(self, element_id: Optional[str] = None) -> None:
        """Clear history for specific element or all"""
        if element_id:
            self._changes = [c for c in self._changes if c.element_id != element_id]
        else:
            self._changes.clear()
    
    def get_history_count(self) -> int:
        """Get total number of changes in history"""
        return len(self._changes)