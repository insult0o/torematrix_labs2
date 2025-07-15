"""Search Optimization Package

Advanced optimization techniques for search performance including:
- Background indexing and processing
- Memory usage optimization
- Parallel search processing
- Index compression techniques
- Performance monitoring and analytics
"""

from .indexing import (
    BackgroundIndexer, IndexingProgress, IndexingConfig,
    IndexingTask, IndexingResult, IndexingStatistics
)
from .memory import (
    MemoryOptimizer, MemoryStatus, MemoryConfig,
    MemoryUsageReport, cleanup_memory, monitor_memory_usage
)
from .parallel import (
    ParallelSearchProcessor, ParallelConfig, ParallelResult,
    ProcessingMode, WorkerPoolManager
)
from .compression import (
    IndexCompressor, CompressionConfig, CompressionResult,
    CompressionAlgorithm, compress_index, decompress_index
)

__all__ = [
    # Background Indexing
    'BackgroundIndexer',
    'IndexingProgress',
    'IndexingConfig',
    'IndexingTask',
    'IndexingResult',
    'IndexingStatistics',
    
    # Memory Optimization
    'MemoryOptimizer',
    'MemoryStatus',
    'MemoryConfig',
    'MemoryUsageReport',
    'cleanup_memory',
    'monitor_memory_usage',
    
    # Parallel Processing
    'ParallelSearchProcessor',
    'ParallelConfig',
    'ParallelResult',
    'ProcessingMode',
    'WorkerPoolManager',
    
    # Index Compression
    'IndexCompressor',
    'CompressionConfig',
    'CompressionResult',
    'CompressionAlgorithm',
    'compress_index',
    'decompress_index',
]

# Version info
__version__ = "1.0.0"
__author__ = "Agent 3 - Performance Optimization"
__description__ = "Advanced search optimization and performance enhancement"