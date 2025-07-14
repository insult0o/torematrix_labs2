"""Parser factory for auto-discovery and instantiation."""

import logging
import importlib
import inspect
from typing import Dict, Type, List, Optional, Set
from pathlib import Path

from ...models.element import Element as UnifiedElement
from .base import BaseParser
from .types import ElementType, ParserConfig, ProcessingHints
from .exceptions import ParserError, UnsupportedElementError


class ParserFactory:
    """Factory for parser discovery, registration and instantiation."""
    
    _parsers: Dict[str, Type[BaseParser]] = {}
    _parser_instances: Dict[str, BaseParser] = {}
    _type_to_parsers: Dict[ElementType, List[str]] = {}
    _auto_discovery_enabled = True
    
    def __init__(self, config: Optional[ParserConfig] = None):
        self.config = config or ParserConfig()
        self.logger = logging.getLogger("torematrix.parsers.factory")
        
        # Auto-discover parsers if enabled
        if self._auto_discovery_enabled:
            self._discover_parsers()
    
    @classmethod
    def register_parser(cls, parser_type: str, parser_class: Type[BaseParser], 
                       auto_instantiate: bool = True) -> None:
        """Register a parser class.
        
        Args:
            parser_type: Unique identifier for the parser
            parser_class: Parser class (must inherit from BaseParser)
            auto_instantiate: Whether to create instance immediately
        """
        if not issubclass(parser_class, BaseParser):
            raise ValueError(f"Parser class {parser_class} must inherit from BaseParser")
        
        cls._parsers[parser_type] = parser_class
        
        if auto_instantiate:
            try:
                instance = parser_class()
                cls._parser_instances[parser_type] = instance
                
                # Map supported types to this parser
                for element_type in instance.get_supported_types():
                    if element_type not in cls._type_to_parsers:
                        cls._type_to_parsers[element_type] = []
                    if parser_type not in cls._type_to_parsers[element_type]:
                        cls._type_to_parsers[element_type].append(parser_type)
                        
            except Exception as e:
                logging.warning(f"Failed to instantiate parser {parser_type}: {e}")
    
    @classmethod
    def unregister_parser(cls, parser_type: str) -> None:
        """Unregister a parser."""
        if parser_type in cls._parsers:
            del cls._parsers[parser_type]
        if parser_type in cls._parser_instances:
            del cls._parser_instances[parser_type]
        
        # Remove from type mappings
        for element_type, parsers in cls._type_to_parsers.items():
            if parser_type in parsers:
                parsers.remove(parser_type)
    
    @classmethod
    def get_parser(cls, element: UnifiedElement, 
                   hints: Optional[ProcessingHints] = None) -> Optional[BaseParser]:
        """Get the best parser for a given element.
        
        Args:
            element: Element to parse
            hints: Optional processing hints
            
        Returns:
            Best parser instance or None if no suitable parser found
        """
        if not cls._parser_instances:
            return None
        
        # Get candidate parsers
        candidates = cls._get_candidate_parsers(element, hints)
        
        if not candidates:
            return None
        
        # Select best parser based on priority and confidence
        best_parser = None
        best_score = -1
        
        for parser in candidates:
            if parser.can_parse(element):
                score = parser.get_priority(element)
                if score > best_score:
                    best_score = score
                    best_parser = parser
        
        return best_parser
    
    @classmethod
    def get_all_parsers(cls) -> List[BaseParser]:
        """Get all registered parser instances."""
        return list(cls._parser_instances.values())
    
    @classmethod
    def get_parsers_for_type(cls, element_type: ElementType) -> List[BaseParser]:
        """Get all parsers that support a specific element type."""
        parser_names = cls._type_to_parsers.get(element_type, [])
        return [cls._parser_instances[name] for name in parser_names 
                if name in cls._parser_instances]
    
    @classmethod
    def list_registered_parsers(cls) -> Dict[str, Dict[str, any]]:
        """List all registered parsers with their capabilities."""
        result = {}
        for name, parser in cls._parser_instances.items():
            result[name] = {
                "class": parser.__class__.__name__,
                "supported_types": [t.value for t in parser.get_supported_types()],
                "capabilities": parser.capabilities.dict() if hasattr(parser, 'capabilities') else {},
                "statistics": parser.get_statistics()
            }
        return result
    
    @classmethod
    def clear_all_parsers(cls) -> None:
        """Clear all registered parsers (useful for testing)."""
        cls._parsers.clear()
        cls._parser_instances.clear()
        cls._type_to_parsers.clear()
    
    @classmethod
    def _get_candidate_parsers(cls, element: UnifiedElement, 
                              hints: Optional[ProcessingHints] = None) -> List[BaseParser]:
        """Get candidate parsers for an element."""
        candidates = []
        
        # If hints provide expected type, start with those parsers
        if hints and hints.expected_type:
            candidates.extend(cls.get_parsers_for_type(hints.expected_type))
        
        # Add parsers based on element's actual type
        if hasattr(element, 'type'):
            try:
                element_type = ElementType(element.type)
                type_parsers = cls.get_parsers_for_type(element_type)
                candidates.extend([p for p in type_parsers if p not in candidates])
            except ValueError:
                # Unknown element type, use all parsers
                candidates = cls.get_all_parsers()
        else:
            # No type information, use all parsers
            candidates = cls.get_all_parsers()
        
        return candidates
    
    @classmethod
    def _discover_parsers(cls) -> None:
        """Auto-discover parsers in the parsers package."""
        try:
            # Discover parsers in current package
            parser_modules = [
                'table', 'list', 'image', 'formula', 'code'
            ]
            
            for module_name in parser_modules:
                try:
                    module = importlib.import_module(f".{module_name}", 
                                                   package="torematrix.core.processing.parsers")
                    cls._discover_parsers_in_module(module)
                except ImportError:
                    # Module doesn't exist yet, skip
                    continue
                    
        except Exception as e:
            logging.warning(f"Parser auto-discovery failed: {e}")
    
    @classmethod
    def _discover_parsers_in_module(cls, module) -> None:
        """Discover parsers in a specific module."""
        for name, obj in inspect.getmembers(module):
            if (inspect.isclass(obj) and 
                issubclass(obj, BaseParser) and 
                obj != BaseParser and
                not inspect.isabstract(obj)):
                
                parser_type = name.lower().replace('parser', '')
                if parser_type not in cls._parsers:
                    try:
                        cls.register_parser(parser_type, obj)
                        logging.info(f"Auto-discovered parser: {parser_type}")
                    except Exception as e:
                        logging.warning(f"Failed to register auto-discovered parser {name}: {e}")
    
    @classmethod
    def enable_auto_discovery(cls, enabled: bool = True) -> None:
        """Enable or disable auto-discovery of parsers."""
        cls._auto_discovery_enabled = enabled
        if enabled:
            cls._discover_parsers()
    
    def create_parser_instance(self, parser_type: str, 
                              config: Optional[ParserConfig] = None) -> Optional[BaseParser]:
        """Create a new parser instance with specific configuration.
        
        Args:
            parser_type: Type of parser to create
            config: Optional configuration override
            
        Returns:
            New parser instance or None if parser type not found
        """
        if parser_type not in self._parsers:
            return None
        
        parser_class = self._parsers[parser_type]
        parser_config = config or self.config
        
        try:
            return parser_class(parser_config)
        except Exception as e:
            self.logger.error(f"Failed to create parser instance {parser_type}: {e}")
            return None