"""Lazy Loading for Large Result Sets

Efficiently load large result sets on demand with intelligent preloading,
virtual scrolling support, and memory optimization for massive datasets.
"""

import asyncio
import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, AsyncIterator, Set, Tuple
from uuid import uuid4
from weakref import WeakValueDictionary

from torematrix.core.models.element import Element
from torematrix.ui.components.search.filters import Filter


logger = logging.getLogger(__name__)


@dataclass
class ResultPage:
    """A page of search results with metadata"""
    page_number: int
    page_size: int
    elements: List[Element]
    total_count: int
    load_time: float
    cache_key: str
    timestamp: float = field(default_factory=time.time)
    access_count: int = 0
    is_complete: bool = True
    
    @property
    def start_index(self) -> int:
        """Starting index of this page in the full result set"""
        return self.page_number * self.page_size
    
    @property
    def end_index(self) -> int:
        """Ending index of this page in the full result set"""
        return min(self.start_index + len(self.elements), self.total_count)
    
    def update_access(self) -> None:
        """Update access statistics"""
        self.access_count += 1
        self.timestamp = time.time()


@dataclass
class LoadingTask:
    """Represents a background loading task"""
    task_id: str
    page_number: int
    priority: int
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    is_preload: bool = False
    task: Optional[asyncio.Task] = None
    
    @property
    def is_running(self) -> bool:
        """Check if task is currently running"""
        return self.task is not None and not self.task.done()
    
    @property
    def execution_time(self) -> Optional[float]:
        """Get execution time in seconds if completed"""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None


@dataclass
class LazyLoadingConfig:
    """Configuration for lazy loading behavior"""
    page_size: int = 50
    preload_pages: int = 2
    max_cached_pages: int = 20
    preload_threshold: float = 0.7  # Trigger preload when 70% through page
    cleanup_interval: int = 300  # seconds
    memory_limit_mb: int = 50
    enable_background_loading: bool = True
    enable_count_estimation: bool = True


class LazyResultLoader:
    """Efficiently load large result sets on demand with intelligent preloading"""
    
    def __init__(self, 
                 search_function: Callable,
                 config: Optional[LazyLoadingConfig] = None):
        """Initialize lazy result loader
        
        Args:
            search_function: Function to perform actual search
            config: Loading configuration
        """
        self.search_function = search_function
        self.config = config or LazyLoadingConfig()
        
        # Page cache
        self.loaded_pages: Dict[int, ResultPage] = {}
        self.page_access_times: Dict[int, float] = {}
        
        # Loading state
        self.total_count: Optional[int] = None
        self.estimated_count: Optional[int] = None
        self.loading_tasks: Dict[str, LoadingTask] = {}
        self.active_query: str = ""
        self.active_filters: List[Filter] = []
        
        # Background loading
        self.preload_queue: asyncio.Queue = asyncio.Queue()
        self.background_loader_task: Optional[asyncio.Task] = None
        self.is_loading: bool = False
        
        # Performance tracking
        self.load_stats = {
            'total_loads': 0,
            'cache_hits': 0,
            'preload_hits': 0,
            'average_load_time': 0.0,
            'memory_usage_mb': 0.0
        }
        
        # Memory management
        self.memory_monitor_task: Optional[asyncio.Task] = None
        self.last_cleanup = time.time()
        
        logger.info(f"LazyResultLoader initialized with page_size={self.config.page_size}")
    
    async def initialize(self, query: str, filters: List[Filter]) -> None:
        """Initialize loader for new search query
        
        Args:
            query: Search query
            filters: Search filters
        """
        # Stop existing background tasks
        await self._stop_background_tasks()
        
        # Clear previous state
        self.loaded_pages.clear()
        self.page_access_times.clear()
        self.loading_tasks.clear()
        
        # Set new query
        self.active_query = query
        self.active_filters = filters.copy()
        self.total_count = None
        self.estimated_count = None
        
        # Start background loading if enabled
        if self.config.enable_background_loading:
            await self._start_background_loader()
        
        # Start memory monitoring
        if self.memory_monitor_task is None:
            self.memory_monitor_task = asyncio.create_task(self._monitor_memory())
        
        logger.info(f"LazyResultLoader initialized for query: '{query}' with {len(filters)} filters")
    
    async def load_page(self, page_number: int, priority: int = 0) -> ResultPage:
        """Load specific page of results
        
        Args:
            page_number: Page number to load (0-based)
            priority: Loading priority (higher = more urgent)
            
        Returns:
            ResultPage with results
        """
        # Check if page is already loaded
        if page_number in self.loaded_pages:
            page = self.loaded_pages[page_number]
            page.update_access()
            self.load_stats['cache_hits'] += 1
            logger.debug(f"Cache hit for page {page_number}")
            return page
        
        # Check if page is currently being loaded
        for task in self.loading_tasks.values():
            if task.page_number == page_number and task.is_running:
                logger.debug(f"Page {page_number} is already being loaded, waiting...")
                await task.task
                if page_number in self.loaded_pages:
                    return self.loaded_pages[page_number]
        
        # Load page directly
        return await self._load_page_direct(page_number, priority=priority)
    
    async def preload_next_pages(self, current_page: int, count: int = None) -> None:
        """Preload upcoming pages in background
        
        Args:
            current_page: Current page number
            count: Number of pages to preload (uses config default if None)
        """
        if not self.config.enable_background_loading:
            return
        
        count = count or self.config.preload_pages
        
        # Queue pages for preloading
        for i in range(1, count + 1):
            page_number = current_page + i
            
            # Don't preload if already loaded or loading
            if (page_number in self.loaded_pages or 
                any(task.page_number == page_number and task.is_running 
                    for task in self.loading_tasks.values())):
                continue
            
            # Add to preload queue
            task_id = str(uuid4())
            task = LoadingTask(
                task_id=task_id,
                page_number=page_number,
                priority=-i,  # Lower priority for preload
                is_preload=True
            )
            
            try:
                await self.preload_queue.put(task)
                self.loading_tasks[task_id] = task
                logger.debug(f"Queued page {page_number} for preloading")
            except asyncio.QueueFull:
                logger.warning(f"Preload queue full, skipping page {page_number}")
    
    def get_virtual_item(self, index: int) -> Optional[Element]:
        """Get item by index, loading page if needed (synchronous)
        
        Args:
            index: Global index in result set
            
        Returns:
            Element if found, None if index out of bounds
        """
        if self.total_count and index >= self.total_count:
            return None
        
        page_number = index // self.config.page_size
        page_index = index % self.config.page_size
        
        # Check if page is loaded
        if page_number in self.loaded_pages:
            page = self.loaded_pages[page_number]
            if page_index < len(page.elements):
                return page.elements[page_index]
        
        # Page not loaded - this would trigger async loading in a real implementation
        # For now, return None to indicate item needs to be loaded
        return None
    
    async def get_virtual_item_async(self, index: int) -> Optional[Element]:
        """Get item by index, loading page if needed (asynchronous)
        
        Args:
            index: Global index in result set
            
        Returns:
            Element if found, None if index out of bounds
        """
        if self.total_count and index >= self.total_count:
            return None
        
        page_number = index // self.config.page_size
        page_index = index % self.config.page_size
        
        # Load page if needed
        page = await self.load_page(page_number)
        
        if page_index < len(page.elements):
            return page.elements[page_index]
        
        return None
    
    async def estimate_total_count(self, query: str, filters: List[Filter]) -> int:
        """Fast estimation of total result count
        
        Args:
            query: Search query
            filters: Search filters
            
        Returns:
            Estimated total count
        """
        if self.total_count is not None:
            return self.total_count
        
        if self.estimated_count is not None:
            return self.estimated_count
        
        try:
            # Load first page to get actual count
            first_page = await self.load_page(0)
            if first_page.total_count > 0:
                self.total_count = first_page.total_count
                self.estimated_count = first_page.total_count
                return self.total_count
            
            # Fallback estimation based on first page
            if len(first_page.elements) == self.config.page_size:
                # Estimate based on full first page
                self.estimated_count = self.config.page_size * 10  # Conservative estimate
            else:
                # First page is partial, likely small result set
                self.estimated_count = len(first_page.elements)
            
            return self.estimated_count
            
        except Exception as e:
            logger.error(f"Error estimating total count: {e}")
            return 0
    
    def get_loading_progress(self) -> Dict[str, Any]:
        """Get current loading progress and statistics
        
        Returns:
            Dictionary with progress information
        """
        total_pages = 0
        if self.total_count:
            total_pages = math.ceil(self.total_count / self.config.page_size)
        
        active_tasks = sum(1 for task in self.loading_tasks.values() if task.is_running)
        completed_tasks = sum(1 for task in self.loading_tasks.values() if task.completed_at)
        
        return {
            'loaded_pages': len(self.loaded_pages),
            'total_pages': total_pages,
            'total_count': self.total_count,
            'estimated_count': self.estimated_count,
            'active_loading_tasks': active_tasks,
            'completed_loading_tasks': completed_tasks,
            'memory_usage_mb': self._calculate_memory_usage(),
            'cache_hit_ratio': self._calculate_cache_hit_ratio(),
            'stats': self.load_stats.copy()
        }
    
    def get_page_range(self, start_index: int, end_index: int) -> List[int]:
        """Get list of page numbers needed for index range
        
        Args:
            start_index: Starting index
            end_index: Ending index
            
        Returns:
            List of page numbers
        """
        start_page = start_index // self.config.page_size
        end_page = end_index // self.config.page_size
        return list(range(start_page, end_page + 1))
    
    async def load_page_range(self, start_index: int, end_index: int) -> List[Element]:
        """Load all elements in an index range
        
        Args:
            start_index: Starting index
            end_index: Ending index
            
        Returns:
            List of elements in range
        """
        page_numbers = self.get_page_range(start_index, end_index)
        elements = []
        
        # Load all required pages
        for page_number in page_numbers:
            page = await self.load_page(page_number)
            
            # Calculate which elements from this page we need
            page_start = page_number * self.config.page_size
            page_end = page_start + len(page.elements)
            
            # Find intersection with requested range
            range_start = max(start_index, page_start)
            range_end = min(end_index + 1, page_end)
            
            if range_start < range_end:
                # Extract elements from this page
                page_offset = range_start - page_start
                page_count = range_end - range_start
                page_elements = page.elements[page_offset:page_offset + page_count]
                elements.extend(page_elements)
        
        return elements
    
    async def clear_cache(self) -> None:
        """Clear all cached pages"""
        await self._stop_background_tasks()
        
        self.loaded_pages.clear()
        self.page_access_times.clear()
        self.loading_tasks.clear()
        
        # Reset stats
        self.load_stats = {
            'total_loads': 0,
            'cache_hits': 0,
            'preload_hits': 0,
            'average_load_time': 0.0,
            'memory_usage_mb': 0.0
        }
        
        logger.info("LazyResultLoader cache cleared")
    
    async def _load_page_direct(self, page_number: int, priority: int = 0) -> ResultPage:
        """Load page directly using search function
        
        Args:
            page_number: Page number to load
            priority: Loading priority
            
        Returns:
            Loaded ResultPage
        """
        start_time = time.time()
        
        try:
            # Calculate offset and limit
            offset = page_number * self.config.page_size
            limit = self.config.page_size
            
            # Perform search
            results = await self.search_function(
                query=self.active_query,
                filters=self.active_filters,
                offset=offset,
                limit=limit
            )
            
            # Extract results and total count
            if hasattr(results, 'elements'):
                elements = results.elements
                total_count = getattr(results, 'total_count', len(elements))
            else:
                elements = results if isinstance(results, list) else []
                total_count = len(elements)
            
            # Update total count if we got it
            if total_count > 0 and (self.total_count is None or total_count > self.total_count):
                self.total_count = total_count
            
            # Create page
            load_time = time.time() - start_time
            cache_key = f"{hash(self.active_query)}_{hash(tuple(f.filter_id for f in self.active_filters))}_{page_number}"
            
            page = ResultPage(
                page_number=page_number,
                page_size=self.config.page_size,
                elements=elements,
                total_count=total_count,
                load_time=load_time,
                cache_key=cache_key
            )
            
            # Cache the page
            self.loaded_pages[page_number] = page
            self.page_access_times[page_number] = time.time()
            
            # Update statistics
            self.load_stats['total_loads'] += 1
            self._update_average_load_time(load_time)
            
            # Trigger cleanup if needed
            if len(self.loaded_pages) > self.config.max_cached_pages:
                await self._cleanup_old_pages()
            
            logger.debug(f"Loaded page {page_number}: {len(elements)} elements in {load_time:.3f}s")
            
            return page
            
        except Exception as e:
            logger.error(f"Error loading page {page_number}: {e}")
            raise
    
    async def _start_background_loader(self) -> None:
        """Start background page loading task"""
        if self.background_loader_task and not self.background_loader_task.done():
            return
        
        self.background_loader_task = asyncio.create_task(self._background_loader())
        logger.debug("Started background page loader")
    
    async def _stop_background_tasks(self) -> None:
        """Stop all background tasks"""
        # Stop background loader
        if self.background_loader_task and not self.background_loader_task.done():
            self.background_loader_task.cancel()
            try:
                await self.background_loader_task
            except asyncio.CancelledError:
                pass
        
        # Stop memory monitor
        if self.memory_monitor_task and not self.memory_monitor_task.done():
            self.memory_monitor_task.cancel()
            try:
                await self.memory_monitor_task
            except asyncio.CancelledError:
                pass
        
        # Cancel running loading tasks
        for task in self.loading_tasks.values():
            if task.task and not task.task.done():
                task.task.cancel()
    
    async def _background_loader(self) -> None:
        """Background task for loading pages from queue"""
        while True:
            try:
                # Wait for loading task with timeout
                loading_task = await asyncio.wait_for(
                    self.preload_queue.get(),
                    timeout=1.0
                )
                
                # Skip if page already loaded
                if loading_task.page_number in self.loaded_pages:
                    continue
                
                # Start loading
                loading_task.started_at = time.time()
                loading_task.task = asyncio.create_task(
                    self._load_page_direct(loading_task.page_number, loading_task.priority)
                )
                
                # Wait for completion
                await loading_task.task
                loading_task.completed_at = time.time()
                
                if loading_task.is_preload:
                    self.load_stats['preload_hits'] += 1
                
                logger.debug(f"Background loaded page {loading_task.page_number}")
                
            except asyncio.TimeoutError:
                # No tasks in queue, continue
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in background loader: {e}")
    
    async def _monitor_memory(self) -> None:
        """Monitor memory usage and trigger cleanup if needed"""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                memory_mb = self._calculate_memory_usage()
                self.load_stats['memory_usage_mb'] = memory_mb
                
                if memory_mb > self.config.memory_limit_mb:
                    logger.warning(f"Memory usage ({memory_mb:.1f}MB) exceeds limit ({self.config.memory_limit_mb}MB)")
                    await self._cleanup_old_pages(aggressive=True)
                
                # Periodic cleanup
                if time.time() - self.last_cleanup > self.config.cleanup_interval:
                    await self._cleanup_old_pages()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in memory monitor: {e}")
    
    async def _cleanup_old_pages(self, aggressive: bool = False) -> None:
        """Clean up old cached pages to free memory
        
        Args:
            aggressive: If True, remove more pages
        """
        if not self.loaded_pages:
            return
        
        # Sort pages by access time (oldest first)
        pages_by_access = sorted(
            self.page_access_times.items(),
            key=lambda x: x[1]
        )
        
        # Determine how many pages to remove
        current_count = len(self.loaded_pages)
        target_count = self.config.max_cached_pages
        
        if aggressive:
            target_count = max(1, target_count // 2)  # Remove more aggressively
        
        remove_count = max(0, current_count - target_count)
        
        # Remove oldest pages
        removed = 0
        for page_number, _ in pages_by_access:
            if removed >= remove_count:
                break
            
            if page_number in self.loaded_pages:
                del self.loaded_pages[page_number]
                del self.page_access_times[page_number]
                removed += 1
        
        self.last_cleanup = time.time()
        
        if removed > 0:
            logger.debug(f"Cleaned up {removed} cached pages")
    
    def _calculate_memory_usage(self) -> float:
        """Calculate estimated memory usage in MB
        
        Returns:
            Memory usage in megabytes
        """
        total_bytes = 0
        
        for page in self.loaded_pages.values():
            # Estimate size of elements
            for element in page.elements:
                total_bytes += len(element.text) * 2  # Unicode characters
                total_bytes += 1000  # Metadata overhead
            
            # Page overhead
            total_bytes += 500
        
        return total_bytes / (1024 * 1024)
    
    def _calculate_cache_hit_ratio(self) -> float:
        """Calculate cache hit ratio
        
        Returns:
            Cache hit ratio as percentage
        """
        total_requests = self.load_stats['total_loads'] + self.load_stats['cache_hits']
        if total_requests == 0:
            return 0.0
        
        return (self.load_stats['cache_hits'] / total_requests) * 100.0
    
    def _update_average_load_time(self, load_time: float) -> None:
        """Update average load time statistic
        
        Args:
            load_time: Load time for this operation
        """
        current_avg = self.load_stats['average_load_time']
        total_loads = self.load_stats['total_loads']
        
        if total_loads > 1:
            new_avg = (current_avg * (total_loads - 1) + load_time) / total_loads
            self.load_stats['average_load_time'] = new_avg
        else:
            self.load_stats['average_load_time'] = load_time


# Factory functions for easy instantiation
def create_lazy_loader(search_function: Callable, 
                      page_size: int = 50,
                      max_cached_pages: int = 20) -> LazyResultLoader:
    """Create LazyResultLoader with custom configuration
    
    Args:
        search_function: Function to perform search
        page_size: Number of items per page
        max_cached_pages: Maximum pages to cache
        
    Returns:
        Configured LazyResultLoader
    """
    config = LazyLoadingConfig(
        page_size=page_size,
        max_cached_pages=max_cached_pages
    )
    return LazyResultLoader(search_function, config)


def create_performance_lazy_loader(search_function: Callable) -> LazyResultLoader:
    """Create LazyResultLoader optimized for performance
    
    Args:
        search_function: Function to perform search
        
    Returns:
        Performance-optimized LazyResultLoader
    """
    config = LazyLoadingConfig(
        page_size=100,  # Larger pages for fewer requests
        preload_pages=3,  # More aggressive preloading
        max_cached_pages=50,  # Larger cache
        preload_threshold=0.5,  # Earlier preload trigger
        memory_limit_mb=100,  # Higher memory limit
        enable_background_loading=True,
        enable_count_estimation=True
    )
    return LazyResultLoader(search_function, config)