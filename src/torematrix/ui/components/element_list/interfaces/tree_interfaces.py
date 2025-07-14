"""
Tree Interfaces and Type Definitions

Type definitions and protocols for tree components.
"""

from typing import Protocol, Any, List, Optional, Dict
from abc import abstractmethod


class ElementProtocol(Protocol):
    """Protocol for element objects used in the tree."""
    
    @property
    def id(self) -> str:
        """Unique element identifier."""
        ...
    
    @property
    def text(self) -> str:
        """Element text content."""
        ...
    
    @property
    def type(self) -> str:
        """Element type (text, title, list, etc.)."""
        ...
    
    @property
    def confidence(self) -> float:
        """Element confidence score (0.0-1.0)."""
        ...
    
    @property
    def metadata(self) -> Dict[str, Any]:
        """Element metadata dictionary."""
        ...


class TreeNodeProtocol(Protocol):
    """Protocol for tree node objects."""
    
    @abstractmethod
    def element(self) -> Optional[ElementProtocol]:
        """Get the element associated with this node."""
        ...
    
    @abstractmethod
    def parent(self) -> Optional['TreeNodeProtocol']:
        """Get parent node."""
        ...
    
    @abstractmethod
    def children(self) -> List['TreeNodeProtocol']:
        """Get list of child nodes."""
        ...
    
    @abstractmethod
    def child_count(self) -> int:
        """Get number of children."""
        ...
    
    @abstractmethod
    def add_child(self, child: 'TreeNodeProtocol') -> None:
        """Add child node."""
        ...
    
    @abstractmethod
    def remove_child(self, child: 'TreeNodeProtocol') -> bool:
        """Remove child node."""
        ...


class ElementProvider(Protocol):
    """Protocol for objects that provide elements to the tree."""
    
    @abstractmethod
    def get_root_elements(self) -> List[ElementProtocol]:
        """Get root level elements."""
        ...
    
    @abstractmethod
    def get_child_elements(self, parent_id: str) -> List[ElementProtocol]:
        """Get child elements for a parent."""
        ...
    
    @abstractmethod
    def get_element_by_id(self, element_id: str) -> Optional[ElementProtocol]:
        """Get element by ID."""
        ...


class TreeModelInterface(Protocol):
    """Interface for tree model implementations."""
    
    @abstractmethod
    def get_node_by_element_id(self, element_id: str) -> Optional[TreeNodeProtocol]:
        """Get tree node by element ID."""
        ...
    
    @abstractmethod
    def refresh_element(self, element_id: str) -> bool:
        """Refresh specific element in tree."""
        ...
    
    @abstractmethod
    def add_element(self, element: ElementProtocol, parent_id: Optional[str] = None) -> bool:
        """Add new element to tree."""
        ...
    
    @abstractmethod
    def remove_element(self, element_id: str) -> bool:
        """Remove element from tree."""
        ...