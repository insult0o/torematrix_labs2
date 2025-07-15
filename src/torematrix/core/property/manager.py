"""Core property management with state integration"""

from typing import Dict, List, Any, Optional
import asyncio
from ...core.state.manager import StateManager
from ...core.events.bus import EventBus
from ...ui.components.property_panel.models import PropertyValue, PropertyChange, PropertyHistory, ChangeType
from ...ui.components.property_panel.events import PropertyNotificationCenter, PropertyEventManager

class PropertyManager:
    """Core property management with state integration"""
    
    def __init__(self, state_manager: StateManager, event_bus: EventBus):
        self._state_manager = state_manager
        self._event_bus = event_bus
        self._notification_center = PropertyNotificationCenter()
        self._event_manager = PropertyEventManager(self._notification_center)
        self._property_history = PropertyHistory()
        self._element_properties: Dict[str, Dict[str, PropertyValue]] = {}
        self._validation_enabled = True
        self._auto_save = True
        
        # Connect to state changes
        self._event_bus.subscribe("element.created", self._on_element_created)
        self._event_bus.subscribe("element.deleted", self._on_element_deleted)
        self._event_bus.subscribe("element.updated", self._on_element_updated)
    
    async def update_property(self, element_id: str, property_name: str, 
                            value: Any, user_id: Optional[str] = None) -> bool:
        """Update property with validation and notification"""
        try:
            # Get current value
            old_value = await self.get_property_value(element_id, property_name)
            
            # Skip if value hasn't changed
            if old_value == value:
                return True
            
            # Validate new value if validation enabled
            if self._validation_enabled:
                validation_result = await self._validate_property_value(
                    element_id, property_name, value
                )
                if not validation_result:
                    self._event_manager.emit_validation_failed(
                        element_id, property_name, "Property validation failed"
                    )
                    return False
            
            # Create property value
            property_value = PropertyValue(
                value=value,
                property_type=self._get_property_type(property_name),
                user_id=user_id,
                source="user"
            )
            
            # Store property
            if element_id not in self._element_properties:
                self._element_properties[element_id] = {}
            self._element_properties[element_id][property_name] = property_value
            
            # Record change in history
            change = PropertyChange(
                element_id=element_id,
                property_name=property_name,
                old_value=old_value,
                new_value=value,
                change_type=ChangeType.UPDATE,
                user_id=user_id,
                description=f"Updated {property_name}"
            )
            self._property_history.add_change(change)
            
            # Emit change event
            self._event_manager.emit_value_change(
                element_id, property_name, old_value, value,
                {"user_id": user_id, "timestamp": property_value.timestamp.isoformat()}
            )
            
            # Auto-save if enabled
            if self._auto_save:
                await self._save_property_to_state(element_id, property_name, property_value)
            
            return True
            
        except Exception as e:
            print(f"Error updating property {property_name} for element {element_id}: {e}")
            return False
    
    async def get_property_value(self, element_id: str, property_name: str) -> Any:
        """Get current property value"""
        if (element_id in self._element_properties and 
            property_name in self._element_properties[element_id]):
            return self._element_properties[element_id][property_name].value
        
        # Load from state if not in memory
        return await self._load_property_from_state(element_id, property_name)
    
    async def get_property_metadata(self, element_id: str, property_name: str) -> Optional[PropertyValue]:
        """Get full property metadata"""
        if (element_id in self._element_properties and 
            property_name in self._element_properties[element_id]):
            return self._element_properties[element_id][property_name]
        return None
    
    async def get_element_properties(self, element_id: str) -> Dict[str, Any]:
        """Get all properties for an element"""
        if element_id not in self._element_properties:
            # Load from state
            await self._load_element_properties(element_id)
        
        return {
            name: prop_value.value 
            for name, prop_value in self._element_properties.get(element_id, {}).items()
        }
    
    async def get_property_history(self, element_id: str, property_name: str) -> List[PropertyChange]:
        """Get property change history"""
        return self._property_history.get_changes(element_id, property_name)
    
    async def reset_property(self, element_id: str, property_name: str, 
                           user_id: Optional[str] = None) -> bool:
        """Reset property to original value"""
        # Get original value from element data
        original_value = await self._get_original_property_value(element_id, property_name)
        if original_value is not None:
            return await self.update_property(element_id, property_name, original_value, user_id)
        return False
    
    async def batch_update_properties(self, updates: List[tuple], 
                                    user_id: Optional[str] = None) -> Dict[str, bool]:
        """Batch update multiple properties efficiently"""
        results = {}
        
        # Start batch mode for efficient notifications
        self._notification_center.start_batch_mode()
        
        try:
            for element_id, property_name, value in updates:
                success = await self.update_property(element_id, property_name, value, user_id)
                results[f"{element_id}.{property_name}"] = success
        finally:
            # End batch mode and flush notifications
            self._notification_center.end_batch_mode()
        
        return results
    
    async def delete_element_properties(self, element_id: str) -> bool:
        """Delete all properties for an element"""
        try:
            if element_id in self._element_properties:
                del self._element_properties[element_id]
            
            # Clear history for this element
            self._property_history.clear_history(element_id)
            
            return True
        except Exception as e:
            print(f"Error deleting properties for element {element_id}: {e}")
            return False
    
    def get_notification_center(self) -> PropertyNotificationCenter:
        """Get the property notification center"""
        return self._notification_center
    
    def get_event_manager(self) -> PropertyEventManager:
        """Get the property event manager"""
        return self._event_manager
    
    def get_property_history_manager(self) -> PropertyHistory:
        """Get the property history manager"""
        return self._property_history
    
    def set_validation_enabled(self, enabled: bool) -> None:
        """Enable or disable property validation"""
        self._validation_enabled = enabled
    
    def set_auto_save_enabled(self, enabled: bool) -> None:
        """Enable or disable auto-save to state"""
        self._auto_save = enabled
    
    async def _validate_property_value(self, element_id: str, property_name: str, value: Any) -> bool:
        """Validate property value (placeholder for Agent 6)"""
        # Basic validation - will be enhanced by Agent 6
        if value is None:
            return False
        
        # Type-specific validation
        property_type = self._get_property_type(property_name)
        if property_type == "float" and not isinstance(value, (int, float)):
            try:
                float(value)
            except (ValueError, TypeError):
                return False
        elif property_type == "string" and not isinstance(value, str):
            return False
        
        return True
    
    def _get_property_type(self, property_name: str) -> str:
        """Get property type for a property name"""
        # Property type mapping - will be enhanced by other agents
        type_mapping = {
            "text": "string",
            "content": "string",
            "x": "float",
            "y": "float",
            "width": "float",
            "height": "float",
            "confidence": "confidence",
            "type": "choice",
            "page": "integer"
        }
        return type_mapping.get(property_name, "string")
    
    async def _save_property_to_state(self, element_id: str, property_name: str, 
                                    property_value: PropertyValue) -> None:
        """Save property to state management system"""
        try:
            await self._state_manager.update_element_property(
                element_id, property_name, property_value.to_dict()
            )
        except Exception as e:
            print(f"Error saving property to state: {e}")
    
    async def _load_property_from_state(self, element_id: str, property_name: str) -> Any:
        """Load property from state management system"""
        try:
            property_data = await self._state_manager.get_element_property(element_id, property_name)
            if property_data:
                return PropertyValue.from_dict(property_data).value
        except Exception as e:
            print(f"Error loading property from state: {e}")
        return None
    
    async def _load_element_properties(self, element_id: str) -> None:
        """Load all properties for an element from state"""
        try:
            element_data = await self._state_manager.get_element(element_id)
            if element_data and "properties" in element_data:
                properties = {}
                for prop_name, prop_data in element_data["properties"].items():
                    if isinstance(prop_data, dict) and "value" in prop_data:
                        properties[prop_name] = PropertyValue.from_dict(prop_data)
                    else:
                        # Simple value, create PropertyValue
                        properties[prop_name] = PropertyValue(
                            value=prop_data,
                            property_type=self._get_property_type(prop_name)
                        )
                self._element_properties[element_id] = properties
        except Exception as e:
            print(f"Error loading element properties: {e}")
    
    async def _get_original_property_value(self, element_id: str, property_name: str) -> Any:
        """Get original property value from element data"""
        try:
            element_data = await self._state_manager.get_element(element_id)
            if element_data and property_name in element_data:
                return element_data[property_name]
        except Exception as e:
            print(f"Error getting original property value: {e}")
        return None
    
    async def _on_element_created(self, event_data: Dict[str, Any]) -> None:
        """Handle element creation event"""
        element_id = event_data.get("element_id")
        if element_id:
            self._element_properties[element_id] = {}
    
    async def _on_element_deleted(self, event_data: Dict[str, Any]) -> None:
        """Handle element deletion event"""
        element_id = event_data.get("element_id")
        if element_id:
            await self.delete_element_properties(element_id)
    
    async def _on_element_updated(self, event_data: Dict[str, Any]) -> None:
        """Handle element update event"""
        element_id = event_data.get("element_id")
        if element_id:
            # Reload properties from state
            await self._load_element_properties(element_id)