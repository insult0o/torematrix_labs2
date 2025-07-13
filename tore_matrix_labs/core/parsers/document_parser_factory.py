"""
Document Parser Factory for TORE Matrix Labs

This module provides a factory for creating appropriate document parsers
based on file type and configuration.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Type

from .base_parser import BaseDocumentParser, ParsingStrategy, ParserConfiguration


logger = logging.getLogger(__name__)


class DocumentParserFactory:
    """Factory for creating document parsers"""
    
    # Registry of available parsers
    _parsers: Dict[str, Type[BaseDocumentParser]] = {}
    
    # File extension to parser strategy mapping
    _extension_strategy_map = {
        '.pdf': [ParsingStrategy.PYMUPDF, ParsingStrategy.UNSTRUCTURED, ParsingStrategy.OCR],
        '.docx': [ParsingStrategy.UNSTRUCTURED, ParsingStrategy.PYMUPDF],
        '.doc': [ParsingStrategy.UNSTRUCTURED],
        '.odt': [ParsingStrategy.UNSTRUCTURED],
        '.rtf': [ParsingStrategy.UNSTRUCTURED],
        '.txt': [ParsingStrategy.UNSTRUCTURED],
        '.html': [ParsingStrategy.UNSTRUCTURED],
        '.htm': [ParsingStrategy.UNSTRUCTURED],
        '.xml': [ParsingStrategy.UNSTRUCTURED],
        '.epub': [ParsingStrategy.UNSTRUCTURED],
    }
    
    @classmethod
    def register_parser(cls, strategy: ParsingStrategy, parser_class: Type[BaseDocumentParser]) -> None:
        """
        Register a parser implementation
        
        Args:
            strategy: Parsing strategy
            parser_class: Parser class to register
        """
        if not issubclass(parser_class, BaseDocumentParser):
            raise ValueError(f"{parser_class} must be a subclass of BaseDocumentParser")
        
        cls._parsers[strategy.value] = parser_class
        logger.info(f"Registered parser {parser_class.__name__} for strategy {strategy.value}")
    
    @classmethod
    def create_parser(
        cls,
        file_path: Path,
        config: Optional[ParserConfiguration] = None
    ) -> Optional[BaseDocumentParser]:
        """
        Create appropriate parser for file
        
        Args:
            file_path: Path to document file
            config: Parser configuration
            
        Returns:
            Document parser instance or None if no suitable parser
        """
        config = config or ParserConfiguration()
        
        # Determine strategy
        if config.strategy == ParsingStrategy.AUTO:
            strategy = cls._determine_strategy(file_path, config)
        else:
            strategy = config.strategy
        
        # Get parser class
        parser_class = cls._parsers.get(strategy.value)
        if not parser_class:
            logger.error(f"No parser registered for strategy {strategy.value}")
            return None
        
        # Create parser instance
        try:
            parser = parser_class(config)
            logger.info(f"Created {parser_class.__name__} for {file_path}")
            return parser
        except Exception as e:
            logger.error(f"Failed to create parser: {e}")
            return None
    
    @classmethod
    def _determine_strategy(
        cls,
        file_path: Path,
        config: ParserConfiguration
    ) -> ParsingStrategy:
        """
        Determine best parsing strategy for file
        
        Args:
            file_path: Path to document
            config: Parser configuration
            
        Returns:
            Selected parsing strategy
        """
        extension = file_path.suffix.lower()
        
        # Get strategies for extension
        strategies = cls._extension_strategy_map.get(extension, [])
        
        if not strategies:
            logger.warning(f"No strategies for extension {extension}, using UNSTRUCTURED")
            return ParsingStrategy.UNSTRUCTURED
        
        # Filter based on available parsers
        available_strategies = [s for s in strategies if s.value in cls._parsers]
        
        if not available_strategies:
            logger.warning(f"No available parsers for {extension}, using first registered")
            if cls._parsers:
                return ParsingStrategy(list(cls._parsers.keys())[0])
            return ParsingStrategy.UNSTRUCTURED
        
        # Select based on configuration preferences
        if config.enable_ocr and ParsingStrategy.OCR in available_strategies:
            # Prefer OCR if enabled and available
            return ParsingStrategy.OCR
        
        # Return first available strategy
        return available_strategies[0]
    
    @classmethod
    def get_supported_extensions(cls) -> List[str]:
        """Get list of supported file extensions"""
        return list(cls._extension_strategy_map.keys())
    
    @classmethod
    def get_strategies_for_extension(cls, extension: str) -> List[ParsingStrategy]:
        """
        Get available strategies for file extension
        
        Args:
            extension: File extension (with dot)
            
        Returns:
            List of available strategies
        """
        return cls._extension_strategy_map.get(extension.lower(), [])
    
    @classmethod
    def get_registered_parsers(cls) -> Dict[str, Type[BaseDocumentParser]]:
        """Get all registered parsers"""
        return cls._parsers.copy()
    
    @classmethod
    def is_extension_supported(cls, extension: str) -> bool:
        """
        Check if file extension is supported
        
        Args:
            extension: File extension to check
            
        Returns:
            True if supported
        """
        return extension.lower() in cls._extension_strategy_map
    
    @classmethod
    def clear_registry(cls) -> None:
        """Clear all registered parsers (mainly for testing)"""
        cls._parsers.clear()
        logger.info("Cleared parser registry")