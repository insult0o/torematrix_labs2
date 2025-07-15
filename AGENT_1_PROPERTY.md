# AGENT 1 - PROPERTY FRAMEWORK & DATA MODELS

## 🎯 Your Assignment
You are **Agent 1** responsible for building the foundational property framework with core data models, base classes, and event system. This is a focused 2-day task that establishes the foundation for all other property panel agents.

## 📋 Your Specific Tasks (2 Days)

### Day 1: Core Data Models
1. **PropertyValue Model** - Type-safe property value container
2. **PropertyMetadata Model** - Property metadata with validation rules  
3. **PropertyChange Model** - Change tracking with undo/redo support
4. **PropertyHistory Manager** - Change history management

### Day 2: Event System & Integration
1. **PropertyNotificationCenter** - Reactive update system
2. **PropertyManager Core** - Basic property management
3. **State Integration** - Connect with application state
4. **Comprehensive Testing** - >95% test coverage

## 🏗️ Files You Must Create

### Day 1 Files

**File**: `src/torematrix/ui/components/property_panel/models.py`
```python
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
        return {
            "value": self.value,
            "property_type": self.property_type,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "source": self.source
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PropertyValue':
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
        return self.change_type in [ChangeType.UPDATE, ChangeType.CREATE, ChangeType.DELETE]
    
    def create_undo_change(self) -> 'PropertyChange':
        if self.change_type == ChangeType.UPDATE:
            return PropertyChange(
                element_id=self.element_id,
                property_name=self.property_name,
                old_value=self.new_value,
                new_value=self.old_value,
                change_type=ChangeType.UPDATE,
                description=f"Undo: {self.description}"
            )
        # Add other undo logic...

class PropertyHistory:
    """Property change history manager"""
    
    def __init__(self, max_history: int = 1000):
        self._changes: List[PropertyChange] = []
        self._max_history = max_history
    
    def add_change(self, change: PropertyChange) -> None:
        self._changes.append(change)
        if len(self._changes) > self._max_history:
            self._changes.pop(0)
    
    def get_changes(self, element_id: Optional[str] = None, 
                   property_name: Optional[str] = None) -> List[PropertyChange]:
        changes = self._changes
        if element_id:
            changes = [c for c in changes if c.element_id == element_id]
        if property_name:
            changes = [c for c in changes if c.property_name == property_name]
        return changes
```

**File**: `tests/unit/components/property_panel/test_models.py`
```python
"""Tests for property data models"""

import pytest
from datetime import datetime
from src.torematrix.ui.components.property_panel.models import (
    PropertyValue, PropertyMetadata, PropertyChange, PropertyHistory, ChangeType
)

class TestPropertyValue:
    def test_creation(self):
        value = PropertyValue(value="test", property_type="string")
        assert value.value == "test"
        assert value.property_type == "string"
        assert isinstance(value.timestamp, datetime)
    
    def test_serialization(self):
        value = PropertyValue(value=42, property_type="integer")
        data = value.to_dict()
        restored = PropertyValue.from_dict(data)
        assert restored.value == 42
        assert restored.property_type == "integer"

class TestPropertyChange:
    def test_undo_creation(self):
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

class TestPropertyHistory:
    def test_add_and_retrieve(self):
        history = PropertyHistory()
        change = PropertyChange(
            element_id="elem1",
            property_name="text", 
            old_value="old",
            new_value="new",
            change_type=ChangeType.UPDATE
        )
        history.add_change(change)
        changes = history.get_changes("elem1")
        assert len(changes) == 1
        assert changes[0] == change
```

### Day 2 Files

**File**: `src/torematrix/ui/components/property_panel/events.py`
```python
"""Property event system for reactive updates"""

from typing import Dict, List, Callable, Any, Optional
from PyQt6.QtCore import QObject, pyqtSignal
from dataclasses import dataclass
from enum import Enum
from .models import PropertyChange

class PropertyEventType(Enum):
    VALUE_CHANGED = "value_changed"
    VALIDATION_FAILED = "validation_failed"
    PROPERTY_SELECTED = "property_selected"

@dataclass
class PropertyEvent:
    event_type: PropertyEventType
    element_id: str
    property_name: str
    old_value: Any = None
    new_value: Any = None
    metadata: Dict[str, Any] = None

class PropertyNotificationCenter(QObject):
    """Central hub for property change notifications"""
    
    property_changed = pyqtSignal(PropertyEvent)
    property_selected = pyqtSignal(str, str)  # element_id, property_name
    validation_failed = pyqtSignal(str, str, str)  # element_id, property_name, error
    
    def __init__(self):
        super().__init__()
        self._listeners: Dict[PropertyEventType, List[Callable]] = {}
    
    def register_listener(self, event_type: PropertyEventType, callback: Callable) -> None:
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(callback)
    
    def emit_property_event(self, event: PropertyEvent) -> None:
        self.property_changed.emit(event)
        
        if event.event_type in self._listeners:
            for callback in self._listeners[event.event_type]:
                try:
                    callback(event)
                except Exception as e:
                    print(f"Error in property event listener: {e}")
```

**File**: `src/torematrix/core/property/manager.py`
```python
"""Core property management with state integration"""

from typing import Dict, List, Any, Optional
import asyncio
from ...core.state.manager import StateManager
from ...core.events.bus import EventBus
from ..ui.components.property_panel.models import PropertyValue, PropertyChange, PropertyHistory, ChangeType
from ..ui.components.property_panel.events import PropertyNotificationCenter, PropertyEvent, PropertyEventType

class PropertyManager:
    """Core property management with state integration"""
    
    def __init__(self, state_manager: StateManager, event_bus: EventBus):
        self._state_manager = state_manager
        self._event_bus = event_bus
        self._notification_center = PropertyNotificationCenter()
        self._property_history = PropertyHistory()
        self._element_properties: Dict[str, Dict[str, PropertyValue]] = {}
        
        # Connect to state changes
        self._event_bus.subscribe("element.created", self._on_element_created)
        self._event_bus.subscribe("element.deleted", self._on_element_deleted)
    
    async def update_property(self, element_id: str, property_name: str, 
                            value: Any, user_id: Optional[str] = None) -> bool:
        """Update property with validation and notification"""
        try:
            # Get current value
            old_value = await self.get_property_value(element_id, property_name)
            
            # Create property value
            property_value = PropertyValue(
                value=value,
                property_type=self._get_property_type(property_name),
                user_id=user_id
            )
            
            # Store property
            if element_id not in self._element_properties:
                self._element_properties[element_id] = {}
            self._element_properties[element_id][property_name] = property_value
            
            # Record change
            change = PropertyChange(
                element_id=element_id,
                property_name=property_name,
                old_value=old_value,
                new_value=value,
                change_type=ChangeType.UPDATE,
                user_id=user_id
            )
            self._property_history.add_change(change)
            
            # Emit event
            event = PropertyEvent(
                event_type=PropertyEventType.VALUE_CHANGED,
                element_id=element_id,
                property_name=property_name,
                old_value=old_value,
                new_value=value
            )
            self._notification_center.emit_property_event(event)
            
            return True
            
        except Exception as e:
            print(f"Error updating property: {e}")
            return False
    
    async def get_property_value(self, element_id: str, property_name: str) -> Any:
        """Get current property value"""
        if (element_id in self._element_properties and 
            property_name in self._element_properties[element_id]):
            return self._element_properties[element_id][property_name].value
        return None
    
    def get_notification_center(self) -> PropertyNotificationCenter:
        return self._notification_center
    
    def _get_property_type(self, property_name: str) -> str:
        """Get property type for a property name"""
        type_mapping = {
            "text": "string",
            "x": "float", 
            "y": "float",
            "confidence": "confidence"
        }
        return type_mapping.get(property_name, "string")
    
    async def _on_element_created(self, event_data: Dict[str, Any]) -> None:
        element_id = event_data.get("element_id")
        if element_id:
            self._element_properties[element_id] = {}
    
    async def _on_element_deleted(self, event_data: Dict[str, Any]) -> None:
        element_id = event_data.get("element_id")
        if element_id in self._element_properties:
            del self._element_properties[element_id]
```

**File**: `tests/unit/components/property_panel/test_events.py`
```python
"""Tests for property event system"""

import pytest
from unittest.mock import Mock
from PyQt6.QtCore import QObject
from src.torematrix.ui.components.property_panel.events import (
    PropertyNotificationCenter, PropertyEvent, PropertyEventType
)

class TestPropertyNotificationCenter:
    def test_listener_registration(self):
        center = PropertyNotificationCenter()
        callback = Mock()
        
        center.register_listener(PropertyEventType.VALUE_CHANGED, callback)
        
        event = PropertyEvent(
            event_type=PropertyEventType.VALUE_CHANGED,
            element_id="elem1",
            property_name="text",
            new_value="test"
        )
        
        center.emit_property_event(event)
        callback.assert_called_once_with(event)
```

## 🎯 Success Criteria
- [ ] Property data models serialize/deserialize correctly
- [ ] Property changes tracked with full history  
- [ ] Event system broadcasts property updates
- [ ] Integration with state management works
- [ ] All tests pass with >95% coverage

## 🚀 Getting Started

1. **Create your feature branch**: `git checkout -b feature/property-framework-agent1-issue190`
2. **Day 1**: Focus on data models and basic property management
3. **Day 2**: Build event system and state integration
4. **Test thoroughly**: Aim for >95% test coverage
5. **Keep it simple**: Focus only on core framework - other agents will extend it

## 📊 Performance Targets
- Property updates <50ms response time
- Memory usage <20MB for 1000+ properties  
- Zero memory leaks in property operations

Your foundation enables all other property panel agents to build their features!