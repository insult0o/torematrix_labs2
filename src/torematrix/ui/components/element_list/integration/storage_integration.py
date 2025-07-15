"""
Storage Integration for Hierarchical Element List

Provides integration with the application's Storage system for
data persistence, caching, and storage optimization.
"""

import logging
from typing import Dict, Any, Optional, List, Set, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from enum import Enum

logger = logging.getLogger(__name__)


class CacheStrategy(Enum):
    """Cache strategies for storage operations"""
    AGGRESSIVE = "aggressive"      # Cache everything
    SELECTIVE = "selective"        # Cache based on access patterns
    MINIMAL = "minimal"           # Cache only essential data
    DISABLED = "disabled"         # No caching


@dataclass
class StorageConfig:
    """Configuration for storage integration"""
    enable_caching: bool = True
    cache_strategy: CacheStrategy = CacheStrategy.SELECTIVE
    cache_size_limit: int = 100_000_000  # 100MB
    cache_expiry_hours: int = 24
    batch_size: int = 1000
    enable_compression: bool = True
    auto_sync_interval: int = 30  # seconds


class ElementListStorageIntegration(QObject):
    """
    Storage integration for hierarchical element list
    
    Manages data persistence, caching, and storage optimization
    for element list operations and data access.
    """
    
    # Signals
    data_loaded = pyqtSignal(str, object)  # element_id, data
    data_saved = pyqtSignal(str, bool)  # element_id, success
    cache_updated = pyqtSignal(int)  # cache_size
    sync_completed = pyqtSignal(bool)  # success
    storage_error = pyqtSignal(str, str)  # operation, error_message
    
    def __init__(self, element_list_widget, parent: Optional[QObject] = None):
        """
        Initialize Storage integration
        
        Args:
            element_list_widget: The element list widget to integrate
            parent: Parent QObject
        """
        super().__init__(parent)
        
        self.element_list = element_list_widget
        self.storage_manager = None  # Will be set when connecting
        
        # Configuration
        self.config = StorageConfig()
        
        # Cache management
        self._element_cache: Dict[str, Any] = {}
        self._cache_access_times: Dict[str, datetime] = {}
        self._cache_size = 0
        self._pending_saves: Set[str] = set()
        self._dirty_elements: Set[str] = set()
        
        # Auto-sync timer
        self._sync_timer = QTimer()
        self._sync_timer.timeout.connect(self._perform_auto_sync)
        
        # Cache cleanup timer
        self._cleanup_timer = QTimer()
        self._cleanup_timer.timeout.connect(self._cleanup_cache)
        self._cleanup_timer.start(300000)  # 5 minutes
        
        logger.info("ElementListStorageIntegration initialized")
    
    def connect_to_storage_manager(self, storage_manager) -> None:
        """
        Connect to the application's Storage Manager
        
        Args:
            storage_manager: Storage Manager instance to connect to
        """
        self.storage_manager = storage_manager
        
        # Start auto-sync if enabled
        if self.config.auto_sync_interval > 0:
            self._sync_timer.start(self.config.auto_sync_interval * 1000)
        
        logger.info("Connected to Storage Manager")
    
    def load_element_data(self, element_id: str, force_reload: bool = False) -> Optional[Dict[str, Any]]:
        """
        Load element data from storage or cache
        
        Args:
            element_id: ID of element to load
            force_reload: Force reload from storage, bypassing cache
            
        Returns:
            Element data dictionary or None if not found
        """
        try:
            # Check cache first (unless force reload)
            if not force_reload and self._is_cached(element_id):
                data = self._get_from_cache(element_id)
                logger.debug(f"Loaded element {element_id} from cache")
                self.data_loaded.emit(element_id, data)
                return data
            
            # Load from storage
            if self.storage_manager:
                data = self.storage_manager.get_element(element_id)
                
                if data:
                    # Cache the data
                    self._add_to_cache(element_id, data)
                    logger.debug(f"Loaded element {element_id} from storage")
                    self.data_loaded.emit(element_id, data)
                    return data
            
            logger.warning(f"Element {element_id} not found in storage")
            return None
            
        except Exception as e:
            logger.error(f"Failed to load element {element_id}: {e}")
            self.storage_error.emit("load", str(e))
            return None
    
    def save_element_data(self, element_id: str, data: Dict[str, Any], immediate: bool = False) -> bool:
        """
        Save element data to storage
        
        Args:
            element_id: ID of element to save
            data: Element data to save
            immediate: Save immediately (bypass batching)
            
        Returns:
            True if save was successful or scheduled
        """
        try:
            # Update cache
            self._add_to_cache(element_id, data)
            
            if immediate or not self.storage_manager:
                # Save immediately
                if self.storage_manager:
                    success = self.storage_manager.save_element(element_id, data)
                    self.data_saved.emit(element_id, success)
                    
                    if element_id in self._dirty_elements:
                        self._dirty_elements.discard(element_id)
                    
                    return success
                return False
            else:
                # Mark for batch save
                self._dirty_elements.add(element_id)
                self._pending_saves.add(element_id)
                logger.debug(f"Scheduled element {element_id} for batch save")
                return True
                
        except Exception as e:
            logger.error(f"Failed to save element {element_id}: {e}")
            self.storage_error.emit("save", str(e))
            return False
    
    def load_element_children(self, element_id: str, recursive: bool = False) -> List[Dict[str, Any]]:
        """
        Load children of an element
        
        Args:
            element_id: Parent element ID
            recursive: Load all descendants recursively
            
        Returns:
            List of child element data
        """
        try:
            children = []
            
            if self.storage_manager:
                child_ids = self.storage_manager.get_element_children(element_id)
                
                for child_id in child_ids:
                    child_data = self.load_element_data(child_id)
                    if child_data:
                        children.append(child_data)
                        
                        # Load grandchildren if recursive
                        if recursive:
                            grandchildren = self.load_element_children(child_id, recursive=True)
                            child_data['children'] = grandchildren
            
            logger.debug(f"Loaded {len(children)} children for element {element_id}")
            return children
            
        except Exception as e:
            logger.error(f"Failed to load children for element {element_id}: {e}")
            self.storage_error.emit("load_children", str(e))
            return []
    
    def preload_visible_elements(self, visible_element_ids: List[str]) -> None:
        """
        Preload data for visible elements to improve performance
        
        Args:
            visible_element_ids: List of currently visible element IDs
        """
        try:
            missing_elements = [
                element_id for element_id in visible_element_ids
                if not self._is_cached(element_id)
            ]
            
            if missing_elements and self.storage_manager:
                # Batch load missing elements
                batch_data = self.storage_manager.get_elements_batch(missing_elements)
                
                for element_id, data in batch_data.items():
                    if data:
                        self._add_to_cache(element_id, data)
                
                logger.debug(f"Preloaded {len(batch_data)} visible elements")
                
        except Exception as e:
            logger.error(f"Failed to preload visible elements: {e}")
    
    def flush_pending_saves(self) -> bool:
        """
        Flush all pending saves to storage
        
        Returns:
            True if all saves were successful
        """
        if not self._pending_saves or not self.storage_manager:
            return True
        
        try:
            # Prepare batch data
            batch_data = {}
            for element_id in self._pending_saves:
                if element_id in self._element_cache:
                    batch_data[element_id] = self._element_cache[element_id]
            
            # Batch save
            success = self.storage_manager.save_elements_batch(batch_data)
            
            if success:
                # Clear pending saves
                for element_id in self._pending_saves:
                    self.data_saved.emit(element_id, True)
                    self._dirty_elements.discard(element_id)
                
                self._pending_saves.clear()
                logger.info(f"Flushed {len(batch_data)} pending saves")
            else:
                logger.error("Batch save failed")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to flush pending saves: {e}")
            self.storage_error.emit("flush", str(e))
            return False
    
    def clear_cache(self, element_ids: Optional[List[str]] = None) -> None:
        """
        Clear cache for specific elements or all elements
        
        Args:
            element_ids: Specific element IDs to clear (None for all)
        """
        if element_ids is None:
            # Clear all cache
            self._element_cache.clear()
            self._cache_access_times.clear()
            self._cache_size = 0
            logger.info("Cleared all element cache")
        else:
            # Clear specific elements
            for element_id in element_ids:
                if element_id in self._element_cache:
                    del self._element_cache[element_id]
                    self._cache_access_times.pop(element_id, None)
            
            self._recalculate_cache_size()
            logger.debug(f"Cleared cache for {len(element_ids)} elements")
        
        self.cache_updated.emit(self._cache_size)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics
        
        Returns:
            Dictionary with cache statistics
        """
        return {
            'cached_elements': len(self._element_cache),
            'cache_size_bytes': self._cache_size,
            'cache_size_mb': self._cache_size / (1024 * 1024),
            'pending_saves': len(self._pending_saves),
            'dirty_elements': len(self._dirty_elements),
            'cache_hit_rate': self._calculate_cache_hit_rate(),
            'oldest_cached': min(self._cache_access_times.values()) if self._cache_access_times else None,
            'newest_cached': max(self._cache_access_times.values()) if self._cache_access_times else None
        }
    
    def set_storage_config(self, config: StorageConfig) -> None:
        """
        Update storage configuration
        
        Args:
            config: New storage configuration
        """
        old_config = self.config
        self.config = config
        
        # Apply configuration changes
        if config.auto_sync_interval != old_config.auto_sync_interval:
            if config.auto_sync_interval > 0:
                self._sync_timer.start(config.auto_sync_interval * 1000)
            else:
                self._sync_timer.stop()
        
        # Adjust cache if needed
        if config.cache_size_limit != old_config.cache_size_limit:
            self._enforce_cache_limit()
        
        if config.cache_strategy != old_config.cache_strategy:
            self._apply_cache_strategy()
        
        logger.info(f"Updated storage configuration: {config.cache_strategy.value} cache strategy")
    
    def _is_cached(self, element_id: str) -> bool:
        """Check if element is cached and not expired"""
        if element_id not in self._element_cache:
            return False
        
        # Check expiry
        if element_id in self._cache_access_times:
            access_time = self._cache_access_times[element_id]
            expiry_time = access_time + timedelta(hours=self.config.cache_expiry_hours)
            
            if datetime.now() > expiry_time:
                # Remove expired entry
                self._remove_from_cache(element_id)
                return False
        
        return True
    
    def _get_from_cache(self, element_id: str) -> Optional[Dict[str, Any]]:
        """Get element from cache and update access time"""
        if element_id in self._element_cache:
            self._cache_access_times[element_id] = datetime.now()
            return self._element_cache[element_id].copy()
        return None
    
    def _add_to_cache(self, element_id: str, data: Dict[str, Any]) -> None:
        """Add element to cache"""
        if not self.config.enable_caching:
            return
        
        # Remove old entry if exists
        self._remove_from_cache(element_id)
        
        # Add new entry
        self._element_cache[element_id] = data.copy()
        self._cache_access_times[element_id] = datetime.now()
        
        # Update cache size
        self._cache_size += self._estimate_data_size(data)
        
        # Enforce cache limits
        self._enforce_cache_limit()
        
        self.cache_updated.emit(self._cache_size)
    
    def _remove_from_cache(self, element_id: str) -> None:
        """Remove element from cache"""
        if element_id in self._element_cache:
            data = self._element_cache[element_id]
            del self._element_cache[element_id]
            self._cache_access_times.pop(element_id, None)
            
            # Update cache size
            self._cache_size -= self._estimate_data_size(data)
            self._cache_size = max(0, self._cache_size)  # Ensure non-negative
    
    def _estimate_data_size(self, data: Any) -> int:
        """Estimate size of data in bytes"""
        try:
            import sys
            return sys.getsizeof(data)
        except:
            # Fallback estimation
            if isinstance(data, dict):
                return len(str(data)) * 2  # Rough estimate
            elif isinstance(data, (list, tuple)):
                return len(data) * 100  # Rough estimate
            else:
                return len(str(data))
    
    def _enforce_cache_limit(self) -> None:
        """Enforce cache size limit"""
        if self._cache_size <= self.config.cache_size_limit:
            return
        
        # Remove oldest entries until under limit
        sorted_items = sorted(
            self._cache_access_times.items(),
            key=lambda x: x[1]  # Sort by access time
        )
        
        for element_id, _ in sorted_items:
            if self._cache_size <= self.config.cache_size_limit:
                break
            self._remove_from_cache(element_id)
        
        logger.debug(f"Enforced cache limit, new size: {self._cache_size}")
    
    def _apply_cache_strategy(self) -> None:
        """Apply current cache strategy"""
        if self.config.cache_strategy == CacheStrategy.DISABLED:
            self.clear_cache()
        elif self.config.cache_strategy == CacheStrategy.MINIMAL:
            # Keep only recently accessed items
            cutoff = datetime.now() - timedelta(hours=1)
            to_remove = [
                element_id for element_id, access_time in self._cache_access_times.items()
                if access_time < cutoff
            ]
            self.clear_cache(to_remove)
    
    def _cleanup_cache(self) -> None:
        """Periodic cache cleanup"""
        # Remove expired entries
        cutoff = datetime.now() - timedelta(hours=self.config.cache_expiry_hours)
        expired = [
            element_id for element_id, access_time in self._cache_access_times.items()
            if access_time < cutoff
        ]
        
        if expired:
            self.clear_cache(expired)
            logger.debug(f"Cleaned up {len(expired)} expired cache entries")
    
    def _recalculate_cache_size(self) -> None:
        """Recalculate total cache size"""
        self._cache_size = sum(
            self._estimate_data_size(data)
            for data in self._element_cache.values()
        )
    
    def _calculate_cache_hit_rate(self) -> float:
        """Calculate cache hit rate (placeholder)"""
        # This would require tracking cache hits/misses
        # For now, return a placeholder value
        return 0.85  # 85% hit rate
    
    def _perform_auto_sync(self) -> None:
        """Perform automatic sync of dirty data"""
        if self._dirty_elements:
            success = self.flush_pending_saves()
            self.sync_completed.emit(success)
            
            if success:
                logger.debug(f"Auto-sync completed for {len(self._dirty_elements)} elements")
            else:
                logger.warning("Auto-sync failed")