"""Processor registry for dynamic loading and management.

This module provides the ProcessorRegistry class that manages the lifecycle
of document processors, including dynamic loading, dependency injection,
and instance management.
"""

import importlib
import importlib.util
import inspect
import asyncio
from typing import Dict, List, Type, Optional, Any, Callable
from pathlib import Path
import logging
from contextlib import asynccontextmanager

from .base import BaseProcessor, ProcessorMetadata, ProcessorCapability, ProcessorException

logger = logging.getLogger(__name__)


class ProcessorRegistry:
    """
    Registry for managing document processors.
    
    Supports dynamic loading, dependency injection, and lifecycle management.
    """
    
    def __init__(self):
        self._processors: Dict[str, Type[BaseProcessor]] = {}
        self._instances: Dict[str, BaseProcessor] = {}
        self._metadata_cache: Dict[str, ProcessorMetadata] = {}
        self._lock = asyncio.Lock()
        
        # Dependency injection
        self._dependencies: Dict[str, Any] = {}
        
        # Hooks
        self._load_hooks: List[Callable] = []
        self._unload_hooks: List[Callable] = []
    
    def register(
        self,
        processor_class: Type[BaseProcessor],
        name: Optional[str] = None
    ) -> None:
        """
        Register a processor class.
        
        Args:
            processor_class: Processor class to register
            name: Optional name override (uses metadata name by default)
        """
        metadata = processor_class.get_metadata()
        processor_name = name or metadata.name
        
        if processor_name in self._processors:
            logger.warning(f"Overwriting existing processor: {processor_name}")
        
        self._processors[processor_name] = processor_class
        self._metadata_cache[processor_name] = metadata
        
        logger.info(f"Registered processor: {processor_name} v{metadata.version}")
        
        # Call load hooks
        for hook in self._load_hooks:
            hook(processor_name, processor_class)
    
    def unregister(self, name: str) -> None:
        """Unregister a processor."""
        if name in self._processors:
            # Clean up instance if exists
            if name in self._instances:
                asyncio.create_task(self._cleanup_instance(name))
            
            del self._processors[name]
            del self._metadata_cache[name]
            
            # Call unload hooks
            for hook in self._unload_hooks:
                hook(name)
            
            logger.info(f"Unregistered processor: {name}")
    
    async def _cleanup_instance(self, name: str) -> None:
        """Clean up processor instance."""
        async with self._lock:
            if name in self._instances:
                await self._instances[name].cleanup()
                del self._instances[name]
    
    def get_processor_class(self, name: str) -> Type[BaseProcessor]:
        """Get processor class by name."""
        if name not in self._processors:
            raise ProcessorException(f"Unknown processor: {name}")
        return self._processors[name]
    
    async def get_processor(
        self,
        name: str,
        config: Optional[Dict[str, Any]] = None
    ) -> BaseProcessor:
        """
        Get initialized processor instance.
        
        Uses singleton pattern - returns same instance for same name/config.
        
        Args:
            name: Processor name
            config: Processor configuration
            
        Returns:
            Initialized processor instance
        """
        async with self._lock:
            # Check if instance exists
            instance_key = f"{name}:{hash(str(config))}"
            
            if instance_key not in self._instances:
                # Create new instance
                processor_class = self.get_processor_class(name)
                instance = processor_class(config)
                
                # Inject dependencies
                await self._inject_dependencies(instance)
                
                # Initialize
                await instance.initialize()
                
                self._instances[instance_key] = instance
            
            return self._instances[instance_key]
    
    async def _inject_dependencies(self, processor: BaseProcessor) -> None:
        """Inject dependencies into processor."""
        # Look for dependency markers in processor
        for attr_name in dir(processor):
            if attr_name.startswith("_inject_"):
                dep_name = attr_name[8:]  # Remove _inject_ prefix
                if dep_name in self._dependencies:
                    setattr(processor, dep_name, self._dependencies[dep_name])
    
    def register_dependency(self, name: str, dependency: Any) -> None:
        """Register a dependency for injection."""
        self._dependencies[name] = dependency
    
    def list_processors(self) -> List[str]:
        """List all registered processors."""
        return list(self._processors.keys())
    
    def get_metadata(self, name: str) -> ProcessorMetadata:
        """Get processor metadata."""
        if name not in self._metadata_cache:
            raise ProcessorException(f"Unknown processor: {name}")
        return self._metadata_cache[name]
    
    def find_by_capability(
        self,
        capability: ProcessorCapability
    ) -> List[str]:
        """Find processors with specific capability."""
        results = []
        for name, metadata in self._metadata_cache.items():
            if capability in metadata.capabilities:
                results.append(name)
        return results
    
    def find_by_format(self, format: str) -> List[str]:
        """Find processors supporting specific format."""
        results = []
        for name, metadata in self._metadata_cache.items():
            if format in metadata.supported_formats:
                results.append(name)
        return results
    
    def load_from_module(self, module_path: str) -> None:
        """
        Load processors from a Python module.
        
        Args:
            module_path: Module path (e.g., 'torematrix.processors.custom')
        """
        try:
            module = importlib.import_module(module_path)
            
            # Find all processor classes in module
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, BaseProcessor) and 
                    obj != BaseProcessor):
                    self.register(obj)
                    
        except ImportError as e:
            logger.error(f"Failed to load module {module_path}: {e}")
            raise ProcessorException(f"Cannot load module: {module_path}")
    
    def load_from_directory(self, directory: Path) -> None:
        """
        Load processors from a directory of Python files.
        
        Args:
            directory: Directory containing processor modules
        """
        for py_file in directory.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
                
            module_name = py_file.stem
            spec = importlib.util.spec_from_file_location(module_name, py_file)
            
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Find processor classes
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, BaseProcessor) and 
                        obj != BaseProcessor):
                        self.register(obj)
    
    def add_load_hook(self, hook: Callable) -> None:
        """Add hook called when processor is loaded."""
        self._load_hooks.append(hook)
    
    def add_unload_hook(self, hook: Callable) -> None:
        """Add hook called when processor is unloaded."""
        self._unload_hooks.append(hook)
    
    async def shutdown(self) -> None:
        """Shutdown registry and cleanup all processors."""
        logger.info("Shutting down processor registry")
        
        # Cleanup all instances
        async with self._lock:
            cleanup_tasks = []
            for instance in self._instances.values():
                cleanup_tasks.append(instance.cleanup())
            
            if cleanup_tasks:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            
            self._instances.clear()
    
    @asynccontextmanager
    async def processor_context(
        self,
        name: str,
        config: Optional[Dict[str, Any]] = None
    ):
        """Context manager for using a processor."""
        processor = await self.get_processor(name, config)
        try:
            yield processor
        finally:
            # Cleanup is handled by registry
            pass


# Global registry instance
_registry = ProcessorRegistry()


def get_registry() -> ProcessorRegistry:
    """Get the global processor registry."""
    return _registry