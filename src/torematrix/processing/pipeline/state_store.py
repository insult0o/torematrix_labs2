"""
Simple state store interface for pipeline checkpointing.

This is a temporary implementation until the core StateStore is available.
"""

from typing import Any, Optional, Dict
import json
import asyncio
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class StateStore:
    """
    Simple in-memory state store for pipeline checkpoints.
    
    This will be replaced with the actual StateStore from Issue #3
    when it becomes available.
    """
    
    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get value from state store."""
        async with self._lock:
            if key in self._store:
                entry = self._store[key]
                # Check TTL
                if entry['ttl'] and datetime.utcnow() > entry['expires_at']:
                    del self._store[key]
                    return None
                return entry['value']
            return None
    
    async def set(
        self, 
        key: str, 
        value: Dict[str, Any], 
        ttl: Optional[int] = None
    ) -> None:
        """Set value in state store with optional TTL."""
        async with self._lock:
            entry = {
                'value': value,
                'ttl': ttl,
                'created_at': datetime.utcnow()
            }
            if ttl:
                entry['expires_at'] = datetime.utcnow() + timedelta(seconds=ttl)
            self._store[key] = entry
    
    async def delete(self, key: str) -> None:
        """Delete value from state store."""
        async with self._lock:
            self._store.pop(key, None)
    
    async def clear(self) -> None:
        """Clear all values from state store."""
        async with self._lock:
            self._store.clear()
    
    def is_healthy(self) -> bool:
        """Check if state store is healthy."""
        return True