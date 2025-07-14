"""
Base persistence interface and configuration for state management.

This module defines the abstract interface that all persistence backends must implement,
along with the configuration and middleware components.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class PersistenceStrategy(Enum):
    """Different strategies for when to persist state."""
    IMMEDIATE = "immediate"  # Persist after every action
    DEBOUNCED = "debounced"  # Persist after a delay with no new actions
    BATCH = "batch"         # Persist in batches at intervals
    MANUAL = "manual"       # Only persist when explicitly requested


@dataclass
class PersistenceConfig:
    """Configuration for persistence backends."""
    strategy: PersistenceStrategy = PersistenceStrategy.DEBOUNCED
    debounce_delay: float = 0.5  # Seconds to wait before persisting
    batch_size: int = 100        # Number of changes to batch
    batch_interval: float = 5.0  # Seconds between batch flushes
    compression_enabled: bool = True
    encryption_enabled: bool = False
    max_versions: int = 100      # Maximum number of versions to keep
    auto_prune: bool = True      # Automatically prune old versions
    retry_attempts: int = 3      # Number of retry attempts for failed saves
    retry_delay: float = 1.0     # Delay between retry attempts
    
    # Backend-specific settings
    backend_config: Dict[str, Any] = field(default_factory=dict)


class PersistenceBackend(ABC):
    """
    Abstract base class for state persistence backends.
    
    All persistence backends must implement these methods to provide
    consistent state saving and loading capabilities.
    """
    
    def __init__(self, config: PersistenceConfig):
        self.config = config
        self._initialized = False
        
    async def initialize(self) -> None:
        """Initialize the persistence backend."""
        if not self._initialized:
            await self._do_initialize()
            self._initialized = True
    
    @abstractmethod
    async def _do_initialize(self) -> None:
        """Backend-specific initialization logic."""
        pass
    
    @abstractmethod
    async def save_state(
        self, 
        state: Dict[str, Any], 
        version: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Save state to storage.
        
        Args:
            state: The state data to save
            version: Version identifier for this state
            metadata: Optional metadata associated with this state
        """
        pass
    
    @abstractmethod
    async def load_state(self, version: Optional[str] = None) -> Dict[str, Any]:
        """
        Load state from storage.
        
        Args:
            version: Specific version to load, or None for latest
            
        Returns:
            The loaded state data
        """
        pass
    
    @abstractmethod
    async def list_versions(self) -> List[str]:
        """
        List all saved state versions.
        
        Returns:
            List of version identifiers, sorted by creation time
        """
        pass
    
    @abstractmethod
    async def delete_version(self, version: str) -> bool:
        """
        Delete a specific state version.
        
        Args:
            version: Version identifier to delete
            
        Returns:
            True if version was deleted, False if it didn't exist
        """
        pass
    
    @abstractmethod
    async def get_metadata(self, version: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a specific version.
        
        Args:
            version: Version identifier
            
        Returns:
            Metadata dict or None if version doesn't exist
        """
        pass
    
    async def cleanup(self) -> None:
        """Clean up resources and close connections."""
        pass
    
    async def prune_old_versions(self) -> int:
        """
        Remove old versions according to configuration.
        
        Returns:
            Number of versions that were pruned
        """
        if not self.config.auto_prune:
            return 0
            
        versions = await self.list_versions()
        if len(versions) <= self.config.max_versions:
            return 0
            
        # Keep the most recent versions, delete the rest
        to_delete = versions[:-self.config.max_versions]
        deleted_count = 0
        
        for version in to_delete:
            try:
                if await self.delete_version(version):
                    deleted_count += 1
            except Exception as e:
                logger.warning(f"Failed to delete version {version}: {e}")
                
        return deleted_count


class PersistenceMiddleware:
    """
    Middleware for automatic state persistence.
    
    This middleware intercepts state changes and persists them according
    to the configured strategy.
    """
    
    def __init__(self, backend: PersistenceBackend, config: PersistenceConfig):
        self.backend = backend
        self.config = config
        self._save_queue: asyncio.Queue = asyncio.Queue()
        self._worker_task: Optional[asyncio.Task] = None
        self._last_save_time = 0.0
        self._pending_actions = 0
        self._debounce_task: Optional[asyncio.Task] = None
        
    async def start(self) -> None:
        """Start the persistence middleware."""
        await self.backend.initialize()
        
        if self.config.strategy in [PersistenceStrategy.DEBOUNCED, PersistenceStrategy.BATCH]:
            self._worker_task = asyncio.create_task(self._persistence_worker())
    
    async def stop(self) -> None:
        """Stop the persistence middleware and flush any pending saves."""
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
                
        if self._debounce_task:
            self._debounce_task.cancel()
            try:
                await self._debounce_task
            except asyncio.CancelledError:
                pass
                
        # Flush any remaining items in the queue
        while not self._save_queue.empty():
            try:
                save_data = self._save_queue.get_nowait()
                await self._save_state_with_retry(save_data)
            except asyncio.QueueEmpty:
                break
                
        await self.backend.cleanup()
    
    async def __call__(self, store, next_middleware: Callable, action: Any) -> Any:
        """
        Middleware function that intercepts actions and triggers persistence.
        
        Args:
            store: The state store
            next_middleware: The next middleware in the chain
            action: The action being dispatched
            
        Returns:
            The result of the action
        """
        # Execute the action first
        result = await next_middleware(action)
        
        # Check if we should persist this action
        if self._should_persist(action):
            state = store.get_state()
            version = self._generate_version()
            metadata = {
                "action_type": getattr(action, "__class__", {}).get("__name__", str(type(action))),
                "timestamp": time.time(),
                "action_id": getattr(action, "id", None),
            }
            
            save_data = {
                "state": state,
                "version": version,
                "metadata": metadata
            }
            
            await self._handle_persistence(save_data)
        
        return result
    
    def _should_persist(self, action: Any) -> bool:
        """
        Determine if an action should trigger state persistence.
        
        Args:
            action: The action to evaluate
            
        Returns:
            True if the action should trigger persistence
        """
        # Skip persistence for certain action types
        if hasattr(action, "_skip_persistence") and action._skip_persistence:
            return False
            
        # For now, persist all actions - could be configurable
        return True
    
    def _generate_version(self) -> str:
        """Generate a unique version identifier."""
        return f"v_{int(time.time() * 1000000)}"
    
    async def _handle_persistence(self, save_data: Dict[str, Any]) -> None:
        """Handle persistence based on the configured strategy."""
        if self.config.strategy == PersistenceStrategy.IMMEDIATE:
            await self._save_state_with_retry(save_data)
        elif self.config.strategy == PersistenceStrategy.DEBOUNCED:
            await self._save_queue.put(save_data)
            self._schedule_debounced_save()
        elif self.config.strategy == PersistenceStrategy.BATCH:
            await self._save_queue.put(save_data)
        # MANUAL strategy doesn't auto-persist
    
    def _schedule_debounced_save(self) -> None:
        """Schedule a debounced save operation."""
        if self._debounce_task:
            self._debounce_task.cancel()
            
        self._debounce_task = asyncio.create_task(self._debounced_save())
    
    async def _debounced_save(self) -> None:
        """Perform a debounced save after the configured delay."""
        try:
            await asyncio.sleep(self.config.debounce_delay)
            
            # Get the most recent state from the queue
            save_data = None
            while not self._save_queue.empty():
                try:
                    save_data = self._save_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
            
            if save_data:
                await self._save_state_with_retry(save_data)
                
        except asyncio.CancelledError:
            pass
    
    async def _persistence_worker(self) -> None:
        """Background worker for batch persistence."""
        try:
            while True:
                if self.config.strategy == PersistenceStrategy.BATCH:
                    await asyncio.sleep(self.config.batch_interval)
                    await self._flush_batch()
                else:
                    # For debounced strategy, just wait
                    await asyncio.sleep(1.0)
                    
        except asyncio.CancelledError:
            pass
    
    async def _flush_batch(self) -> None:
        """Flush a batch of pending saves."""
        batch = []
        
        # Collect up to batch_size items
        for _ in range(self.config.batch_size):
            try:
                save_data = self._save_queue.get_nowait()
                batch.append(save_data)
            except asyncio.QueueEmpty:
                break
        
        # Save the most recent state from the batch (skip intermediate states)
        if batch:
            latest_save = batch[-1]
            await self._save_state_with_retry(latest_save)
    
    async def _save_state_with_retry(self, save_data: Dict[str, Any]) -> None:
        """Save state with retry logic."""
        for attempt in range(self.config.retry_attempts):
            try:
                await self.backend.save_state(
                    save_data["state"],
                    save_data["version"], 
                    save_data["metadata"]
                )
                
                # Prune old versions if needed
                if self.config.auto_prune:
                    await self.backend.prune_old_versions()
                
                return
                
            except Exception as e:
                logger.warning(
                    f"Persistence attempt {attempt + 1} failed: {e}"
                )
                
                if attempt < self.config.retry_attempts - 1:
                    await asyncio.sleep(self.config.retry_delay)
                else:
                    logger.error(f"Failed to persist state after {self.config.retry_attempts} attempts")
                    raise
    
    async def save_manual(self, state: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Manually save state (for MANUAL strategy or forced saves).
        
        Args:
            state: State to save
            metadata: Optional metadata
            
        Returns:
            Version identifier of the saved state
        """
        version = self._generate_version()
        save_metadata = metadata or {}
        save_metadata.update({
            "manual_save": True,
            "timestamp": time.time(),
        })
        
        await self._save_state_with_retry({
            "state": state,
            "version": version,
            "metadata": save_metadata
        })
        
        return version