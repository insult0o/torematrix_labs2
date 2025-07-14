"""Fallback handler for parser error recovery."""

import logging
from typing import Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .manager import ParseResponse

from ....models.element import Element as UnifiedElement
from ..base import ParserResult, ParserMetadata
# ParseResponse will be imported where needed to avoid circular imports


class FallbackHandler:
    """Handles parser failures and provides fallback strategies."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger("torematrix.parsers.fallback")
        
        # Fallback strategies configuration
        self.enable_text_extraction = config.get('enable_text_extraction', True)
        self.enable_basic_classification = config.get('enable_basic_classification', True)
        self.enable_metadata_extraction = config.get('enable_metadata_extraction', True)
        self.min_confidence_threshold = config.get('min_confidence_threshold', 0.3)
    
    async def handle_no_parser(self, element: UnifiedElement) -> Optional['ParseResponse']:
        """Handle case when no suitable parser is found."""
        self.logger.warning(f"No parser found for element type: {getattr(element, 'type', 'unknown')}")
        
        # Try fallback strategies
        if self.enable_text_extraction:
            result = await self._extract_basic_content(element)
            if result:
                # Import here to avoid circular imports
                from .manager import ParseResponse
                from .manager import ParseResponse
            return ParseResponse(
                    success=True,
                    result=result,
                    error=None,
                    processing_time=0.0,
                    parser_used="fallback_text_extraction"
                )
        
        return None
    
    async def handle_error(self, element: UnifiedElement, error: Exception) -> Optional['ParseResponse']:
        """Handle parser errors with fallback strategies."""
        self.logger.warning(f"Parser error for element: {str(error)}")
        
        # Try different fallback strategies based on error type
        if "timeout" in str(error).lower():
            return await self._handle_timeout_error(element)
        elif "memory" in str(error).lower():
            return await self._handle_memory_error(element)
        else:
            return await self._handle_generic_error(element, error)
    
    async def _extract_basic_content(self, element: UnifiedElement) -> Optional[ParserResult]:
        """Extract basic content as fallback."""
        try:
            # Extract text content
            text_content = ""
            if hasattr(element, 'text') and element.text:
                text_content = element.text.strip()
            
            if not text_content:
                return None
            
            # Basic classification
            element_type = getattr(element, 'type', 'unknown')
            classification = await self._classify_element_basic(element)
            
            # Extract basic metadata
            metadata = await self._extract_basic_metadata(element)
            
            return ParserResult(
                success=True,
                data={
                    "content": text_content,
                    "classification": classification,
                    "element_type": element_type,
                    "length": len(text_content),
                    "word_count": len(text_content.split()),
                    "fallback": True
                },
                metadata=ParserMetadata(
                    confidence=self.min_confidence_threshold,
                    parser_name="fallback",
                    element_metadata=metadata,
                    warnings=["Using fallback content extraction"]
                ),
                extracted_content=text_content,
                structured_data={
                    "type": "text",
                    "content": text_content,
                    "classification": classification
                }
            )
            
        except Exception as e:
            self.logger.error(f"Fallback content extraction failed: {e}")
            return None
    
    async def _classify_element_basic(self, element: UnifiedElement) -> str:
        """Basic element classification."""
        if not self.enable_basic_classification:
            return "unknown"
        
        element_type = getattr(element, 'type', '').lower()
        text = getattr(element, 'text', '').lower()
        
        # Basic classification rules
        if element_type in ['table', 'list']:
            return element_type
        elif element_type in ['image', 'figure']:
            return "image"
        elif element_type in ['code', 'codeblock']:
            return "code"
        elif 'table' in text or '|' in text:
            return "table_like"
        elif any(keyword in text for keyword in ['def ', 'function', 'class ', 'import']):
            return "code_like"
        elif len(text.split('\n')) > 5:
            return "multiline_text"
        else:
            return "text"
    
    async def _extract_basic_metadata(self, element: UnifiedElement) -> Dict[str, Any]:
        """Extract basic metadata."""
        metadata = {}
        
        if not self.enable_metadata_extraction:
            return metadata
        
        # Extract from element metadata if available
        if hasattr(element, 'metadata') and element.metadata:
            metadata.update(element.metadata)
        
        # Add basic computed metadata
        if hasattr(element, 'text') and element.text:
            text = element.text
            metadata.update({
                'character_count': len(text),
                'word_count': len(text.split()),
                'line_count': len(text.splitlines()),
                'has_numbers': any(char.isdigit() for char in text),
                'has_special_chars': any(not char.isalnum() and not char.isspace() for char in text)
            })
        
        return metadata
    
    async def _handle_timeout_error(self, element: UnifiedElement) -> Optional['ParseResponse']:
        """Handle timeout errors with faster fallback."""
        self.logger.info("Attempting fast fallback for timeout error")
        
        # Quick text extraction without complex processing
        try:
            text = getattr(element, 'text', '')[:1000]  # Limit to first 1000 chars
            
            if text:
                result = ParserResult(
                    success=True,
                    data={
                        "content": text,
                        "truncated": len(getattr(element, 'text', '')) > 1000,
                        "fallback_reason": "timeout"
                    },
                    metadata=ParserMetadata(
                        confidence=0.2,
                        parser_name="timeout_fallback",
                        warnings=["Content truncated due to timeout"]
                    ),
                    extracted_content=text
                )
                
                # Import here to avoid circular imports
                from .manager import ParseResponse
                from .manager import ParseResponse
            return ParseResponse(
                    success=True,
                    result=result,
                    error=None,
                    processing_time=0.0,
                    parser_used="timeout_fallback"
                )
                
        except Exception as e:
            self.logger.error(f"Timeout fallback failed: {e}")
        
        return None
    
    async def _handle_memory_error(self, element: UnifiedElement) -> Optional['ParseResponse']:
        """Handle memory errors with lightweight fallback."""
        self.logger.info("Attempting lightweight fallback for memory error")
        
        try:
            # Minimal processing to avoid memory issues
            element_type = getattr(element, 'type', 'unknown')
            text_length = len(getattr(element, 'text', ''))
            
            result = ParserResult(
                success=True,
                data={
                    "element_type": element_type,
                    "size": text_length,
                    "fallback_reason": "memory_limit",
                    "processed": False
                },
                metadata=ParserMetadata(
                    confidence=0.1,
                    parser_name="memory_fallback",
                    warnings=["Minimal processing due to memory constraints"]
                ),
                extracted_content=f"[{element_type} - {text_length} characters]"
            )
            
            from .manager import ParseResponse
            return ParseResponse(
                success=True,
                result=result,
                error=None,
                processing_time=0.0,
                parser_used="memory_fallback"
            )
            
        except Exception as e:
            self.logger.error(f"Memory fallback failed: {e}")
        
        return None
    
    async def _handle_generic_error(self, element: UnifiedElement, error: Exception) -> Optional['ParseResponse']:
        """Handle generic errors with safe fallback."""
        self.logger.info(f"Attempting safe fallback for error: {type(error).__name__}")
        
        try:
            # Safe minimal extraction
            data = {
                "element_type": getattr(element, 'type', 'unknown'),
                "has_text": hasattr(element, 'text') and bool(element.text),
                "has_metadata": hasattr(element, 'metadata') and bool(element.metadata),
                "error_type": type(error).__name__,
                "fallback_reason": "parser_error"
            }
            
            # Try to get some basic info safely
            try:
                if hasattr(element, 'text') and element.text:
                    text = element.text[:100]  # First 100 chars only
                    data["preview"] = text
                    data["text_length"] = len(element.text)
            except:
                pass
            
            result = ParserResult(
                success=True,
                data=data,
                metadata=ParserMetadata(
                    confidence=0.1,
                    parser_name="error_fallback",
                    warnings=[f"Parser failed: {str(error)}"]
                ),
                extracted_content=data.get("preview", f"[{data['element_type']}]")
            )
            
            from .manager import ParseResponse
            return ParseResponse(
                success=True,
                result=result,
                error=None,
                processing_time=0.0,
                parser_used="error_fallback"
            )
            
        except Exception as e:
            self.logger.error(f"Generic fallback failed: {e}")
        
        return None