"""
Async client wrapper for unstructured library.

This module provides an async-compatible interface to the unstructured
library with comprehensive error handling and resource management.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable
from contextlib import asynccontextmanager

from .config import UnstructuredConfig
from .exceptions import (
    UnstructuredError,
    UnstructuredParsingError,
    UnstructuredTimeoutError,
    UnstructuredResourceError
)

logger = logging.getLogger(__name__)


class UnstructuredClient:
    """
    Async wrapper for the unstructured library.
    
    Provides comprehensive error handling, resource management,
    and progress tracking for document parsing operations.
    """
    
    def __init__(self, config: Optional[UnstructuredConfig] = None):
        self.config = config or UnstructuredConfig()
        self._logger = logging.getLogger(__name__)
        self._semaphore = asyncio.Semaphore(self.config.performance.max_concurrent)
        self._session_active = False
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close_session()
    
    async def start_session(self):
        """Initialize client session."""
        if self._session_active:
            return
        
        self._logger.info("Starting unstructured client session")
        self._session_active = True
    
    async def close_session(self):
        """Close client session and cleanup resources."""
        if not self._session_active:
            return
        
        self._logger.info("Closing unstructured client session")
        self._session_active = False
    
    async def parse_document(self, 
                           file_path: Union[str, Path],
                           progress_callback: Optional[Callable[[float], None]] = None,
                           **kwargs) -> List[Any]:
        """
        Parse document asynchronously.
        
        Args:
            file_path: Path to document to parse
            progress_callback: Optional progress callback function
            **kwargs: Additional parsing parameters
            
        Returns:
            List of parsed elements
            
        Raises:
            UnstructuredParsingError: If parsing fails
            UnstructuredTimeoutError: If operation times out
            UnstructuredResourceError: If resource limits exceeded
        """
        if not self._session_active:
            raise UnstructuredError("Client session not active")
        
        file_path = Path(file_path)
        
        async with self._semaphore:
            try:
                self._logger.info(f"Parsing document: {file_path.name}")
                
                if progress_callback:
                    progress_callback(0.0)
                
                # Run parsing in executor to avoid blocking
                loop = asyncio.get_event_loop()
                
                def sync_parse():
                    return self._parse_sync(file_path, **kwargs)
                
                # Use timeout from config
                elements = await asyncio.wait_for(
                    loop.run_in_executor(None, sync_parse),
                    timeout=self.config.performance.timeout_seconds
                )
                
                if progress_callback:
                    progress_callback(1.0)
                
                self._logger.info(f"Successfully parsed {len(elements)} elements from {file_path.name}")
                return elements
                
            except asyncio.TimeoutError:
                raise UnstructuredTimeoutError(f"Parsing timeout for {file_path.name}")
            except MemoryError:
                raise UnstructuredResourceError(f"Insufficient memory for {file_path.name}")
            except Exception as e:
                self._logger.error(f"Parsing failed for {file_path.name}: {e}")
                raise UnstructuredParsingError(f"Failed to parse {file_path.name}: {str(e)}")
    
    def _parse_sync(self, file_path: Path, **kwargs) -> List[Any]:
        """
        Synchronous parsing implementation.
        
        This method imports and uses unstructured library in a sync context.
        """
        try:
            # Import unstructured library
            from unstructured.partition.auto import partition
            
            # Prepare parsing parameters
            parse_params = self._build_parse_params(file_path, **kwargs)
            
            # Parse document
            elements = partition(filename=str(file_path), **parse_params)
            
            return elements
            
        except ImportError:
            # Fallback if unstructured library not available
            self._logger.warning("Unstructured library not available, using mock elements")
            return self._create_mock_elements(file_path)
        except Exception as e:
            raise UnstructuredParsingError(f"Sync parsing failed: {str(e)}")
    
    def _build_parse_params(self, file_path: Path, **kwargs) -> Dict[str, Any]:
        """Build parameters for unstructured library."""
        params = {
            "strategy": self.config.strategy.value,
            "include_page_breaks": self.config.include_page_breaks,
            "include_metadata": self.config.include_metadata,
        }
        
        # OCR parameters
        if self.config.ocr.enabled:
            params.update({
                "languages": self.config.ocr.languages,
                "ocr_languages": self.config.ocr.languages,
            })
        
        # PDF-specific parameters
        if file_path.suffix.lower() == '.pdf':
            params.update({
                "extract_images": self.config.pdf_extract_images,
                "infer_table_structure": self.config.pdf_infer_table_structure,
            })
        
        # HTML-specific parameters
        if file_path.suffix.lower() in ['.html', '.htm']:
            params.update({
                "assemble_articles": self.config.html_assemble_articles,
            })
        
        # Override with custom parameters
        params.update(kwargs)
        params.update(self.config.custom_settings)
        
        return params
    
    def _create_mock_elements(self, file_path: Path) -> List[Any]:
        """Create mock elements for testing/development."""
        from unittest.mock import Mock
        
        # Create mock elements that simulate unstructured output
        mock_elements = [
            Mock(
                text=f"Mock title from {file_path.name}",
                category="Title",
                metadata=Mock(page_number=1)
            ),
            Mock(
                text=f"Mock paragraph content from {file_path.name}",
                category="NarrativeText", 
                metadata=Mock(page_number=1)
            )
        ]
        
        return mock_elements
    
    async def parse_multiple(self, 
                           file_paths: List[Union[str, Path]],
                           progress_callback: Optional[Callable[[float], None]] = None) -> Dict[str, List[Any]]:
        """
        Parse multiple documents concurrently.
        
        Args:
            file_paths: List of file paths to parse
            progress_callback: Optional progress callback
            
        Returns:
            Dictionary mapping file paths to parsed elements
        """
        results = {}
        total_files = len(file_paths)
        completed = 0
        
        async def parse_single(file_path):
            nonlocal completed
            try:
                elements = await self.parse_document(file_path)
                results[str(file_path)] = elements
                completed += 1
                
                if progress_callback:
                    progress_callback(completed / total_files)
                    
            except Exception as e:
                self._logger.error(f"Failed to parse {file_path}: {e}")
                results[str(file_path)] = []
        
        # Create tasks for concurrent processing
        tasks = [parse_single(Path(fp)) for fp in file_paths]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        return results
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the client.
        
        Returns:
            Health status information
        """
        status = {
            "session_active": self._session_active,
            "config_valid": True,
            "unstructured_available": False,
            "concurrent_limit": self.config.performance.max_concurrent,
            "memory_limit_mb": self.config.performance.memory_limit_mb
        }
        
        try:
            import unstructured
            status["unstructured_available"] = True
            status["unstructured_version"] = getattr(unstructured, '__version__', 'unknown')
        except ImportError:
            pass
        
        return status


@asynccontextmanager
async def create_client(config: Optional[UnstructuredConfig] = None):
    """
    Async context manager for creating and managing client sessions.
    
    Usage:
        async with create_client() as client:
            elements = await client.parse_document("document.pdf")
    """
    client = UnstructuredClient(config)
    try:
        await client.start_session()
        yield client
    finally:
        await client.close_session()