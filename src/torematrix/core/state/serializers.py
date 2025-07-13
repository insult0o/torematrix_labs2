"""
State serialization utilities.

This module provides utilities for serializing and deserializing state data
across different formats and versions.
"""

import json
import pickle
import gzip
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class SerializationFormat(Enum):
    """Supported serialization formats."""
    JSON = "json"
    PICKLE = "pickle"
    JSON_COMPRESSED = "json_compressed"
    PICKLE_COMPRESSED = "pickle_compressed"


class StateSerializer(ABC):
    """Abstract base class for state serializers."""
    
    @abstractmethod
    def serialize(self, state: Dict[str, Any]) -> bytes:
        """Serialize state to bytes."""
        pass
    
    @abstractmethod
    def deserialize(self, data: bytes) -> Dict[str, Any]:
        """Deserialize bytes to state."""
        pass


class JSONSerializer(StateSerializer):
    """JSON-based state serializer."""
    
    def __init__(self, ensure_ascii: bool = False, sort_keys: bool = True):
        self.ensure_ascii = ensure_ascii
        self.sort_keys = sort_keys
    
    def serialize(self, state: Dict[str, Any]) -> bytes:
        """Serialize state to JSON bytes."""
        try:
            json_str = json.dumps(
                state,
                ensure_ascii=self.ensure_ascii,
                sort_keys=self.sort_keys,
                separators=(',', ':')  # Compact format
            )
            return json_str.encode('utf-8')
        except Exception as e:
            logger.error(f"JSON serialization failed: {e}")
            raise
    
    def deserialize(self, data: bytes) -> Dict[str, Any]:
        """Deserialize JSON bytes to state."""
        try:
            json_str = data.decode('utf-8')
            return json.loads(json_str)
        except Exception as e:
            logger.error(f"JSON deserialization failed: {e}")
            raise


class PickleSerializer(StateSerializer):
    """Pickle-based state serializer."""
    
    def __init__(self, protocol: int = pickle.HIGHEST_PROTOCOL):
        self.protocol = protocol
    
    def serialize(self, state: Dict[str, Any]) -> bytes:
        """Serialize state to pickle bytes."""
        try:
            return pickle.dumps(state, protocol=self.protocol)
        except Exception as e:
            logger.error(f"Pickle serialization failed: {e}")
            raise
    
    def deserialize(self, data: bytes) -> Dict[str, Any]:
        """Deserialize pickle bytes to state."""
        try:
            return pickle.loads(data)
        except Exception as e:
            logger.error(f"Pickle deserialization failed: {e}")
            raise


class CompressedJSONSerializer(StateSerializer):
    """Compressed JSON serializer using gzip."""
    
    def __init__(self, compression_level: int = 6):
        self.json_serializer = JSONSerializer()
        self.compression_level = compression_level
    
    def serialize(self, state: Dict[str, Any]) -> bytes:
        """Serialize state to compressed JSON bytes."""
        try:
            json_bytes = self.json_serializer.serialize(state)
            return gzip.compress(json_bytes, compresslevel=self.compression_level)
        except Exception as e:
            logger.error(f"Compressed JSON serialization failed: {e}")
            raise
    
    def deserialize(self, data: bytes) -> Dict[str, Any]:
        """Deserialize compressed JSON bytes to state."""
        try:
            json_bytes = gzip.decompress(data)
            return self.json_serializer.deserialize(json_bytes)
        except Exception as e:
            logger.error(f"Compressed JSON deserialization failed: {e}")
            raise


class CompressedPickleSerializer(StateSerializer):
    """Compressed pickle serializer using gzip."""
    
    def __init__(self, compression_level: int = 6):
        self.pickle_serializer = PickleSerializer()
        self.compression_level = compression_level
    
    def serialize(self, state: Dict[str, Any]) -> bytes:
        """Serialize state to compressed pickle bytes."""
        try:
            pickle_bytes = self.pickle_serializer.serialize(state)
            return gzip.compress(pickle_bytes, compresslevel=self.compression_level)
        except Exception as e:
            logger.error(f"Compressed pickle serialization failed: {e}")
            raise
    
    def deserialize(self, data: bytes) -> Dict[str, Any]:
        """Deserialize compressed pickle bytes to state."""
        try:
            pickle_bytes = gzip.decompress(data)
            return self.pickle_serializer.deserialize(pickle_bytes)
        except Exception as e:
            logger.error(f"Compressed pickle deserialization failed: {e}")
            raise


def get_serializer(format: SerializationFormat) -> StateSerializer:
    """Get serializer instance for the specified format."""
    if format == SerializationFormat.JSON:
        return JSONSerializer()
    elif format == SerializationFormat.PICKLE:
        return PickleSerializer()
    elif format == SerializationFormat.JSON_COMPRESSED:
        return CompressedJSONSerializer()
    elif format == SerializationFormat.PICKLE_COMPRESSED:
        return CompressedPickleSerializer()
    else:
        raise ValueError(f"Unsupported serialization format: {format}")