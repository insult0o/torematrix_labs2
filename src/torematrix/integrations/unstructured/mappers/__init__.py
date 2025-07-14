"""
Mappers for converting unstructured elements to unified element model.

This module provides the mapping layer between unstructured.io elements 
and the TORE Matrix Labs unified element model.
"""

from .base import ElementMapper, MapperRegistry
from .element_factory import ElementFactory  
from .metadata_extractor import MetadataExtractor, MetadataNormalizer

__all__ = [
    "ElementMapper",
    "MapperRegistry", 
    "ElementFactory",
    "MetadataExtractor",
    "MetadataNormalizer",
]