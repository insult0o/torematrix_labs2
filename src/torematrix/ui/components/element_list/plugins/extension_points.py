"""
Extension Points for Hierarchical Element List

Defines extension interfaces and hooks for plugins to customize
element list behavior and add new functionality.
"""

import logging
from typing import Dict, List, Optional, Any, Callable
from abc import ABC, abstractmethod
from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class ElementRenderer(ABC):
    """Base class for custom element renderers"""
    
    @abstractmethod
    def render(self, element_data: Dict[str, Any], widget) -> None:
        """Render element in the tree widget"""
        pass
    
    @abstractmethod
    def update(self, element_data: Dict[str, Any], widget) -> None:
        """Update existing rendered element"""
        pass


class ElementAction(ABC):
    """Base class for custom element actions"""
    
    @abstractmethod
    def execute(self, element_ids: List[str], context: Dict[str, Any]) -> bool:
        """Execute the action on selected elements"""
        pass
    
    @abstractmethod
    def is_available(self, element_ids: List[str], context: Dict[str, Any]) -> bool:
        """Check if action is available for current selection"""
        pass


class ElementListExtensionPoints(QObject):
    """
    Extension points for element list customization
    
    Provides hooks and interfaces for plugins to extend
    element list functionality in a controlled manner.
    """
    
    # Signals
    extension_registered = pyqtSignal(str, str)  # extension_type, extension_name
    extension_unregistered = pyqtSignal(str, str)  # extension_type, extension_name
    
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        
        # Extension registries
        self._renderers: Dict[str, ElementRenderer] = {}
        self._actions: Dict[str, ElementAction] = {}
        self._filters: Dict[str, Callable] = {}
        self._sorters: Dict[str, Callable] = {}
        
        logger.info("ElementListExtensionPoints initialized")
    
    def register_renderer(self, element_type: str, renderer: ElementRenderer) -> bool:
        """Register a custom element renderer"""
        if element_type in self._renderers:
            logger.warning(f"Renderer for '{element_type}' already registered")
            return False
        
        self._renderers[element_type] = renderer
        self.extension_registered.emit("renderer", element_type)
        logger.debug(f"Registered renderer for element type: {element_type}")
        return True
    
    def unregister_renderer(self, element_type: str) -> bool:
        """Unregister a custom element renderer"""
        if element_type not in self._renderers:
            return False
        
        del self._renderers[element_type]
        self.extension_unregistered.emit("renderer", element_type)
        logger.debug(f"Unregistered renderer for element type: {element_type}")
        return True
    
    def get_renderer(self, element_type: str) -> Optional[ElementRenderer]:
        """Get renderer for element type"""
        return self._renderers.get(element_type)
    
    def register_action(self, action_name: str, action: ElementAction) -> bool:
        """Register a custom element action"""
        if action_name in self._actions:
            logger.warning(f"Action '{action_name}' already registered")
            return False
        
        self._actions[action_name] = action
        self.extension_registered.emit("action", action_name)
        logger.debug(f"Registered action: {action_name}")
        return True
    
    def unregister_action(self, action_name: str) -> bool:
        """Unregister a custom element action"""
        if action_name not in self._actions:
            return False
        
        del self._actions[action_name]
        self.extension_unregistered.emit("action", action_name)
        logger.debug(f"Unregistered action: {action_name}")
        return True
    
    def get_action(self, action_name: str) -> Optional[ElementAction]:
        """Get action by name"""
        return self._actions.get(action_name)
    
    def get_available_actions(self, element_ids: List[str], context: Dict[str, Any]) -> List[str]:
        """Get list of available actions for current selection"""
        available = []
        for action_name, action in self._actions.items():
            try:
                if action.is_available(element_ids, context):
                    available.append(action_name)
            except Exception as e:
                logger.warning(f"Error checking availability of action '{action_name}': {e}")
        
        return available