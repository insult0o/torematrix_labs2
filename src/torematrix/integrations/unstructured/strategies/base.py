"""
Base parsing strategy interface and metrics.
"""

import time
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable


@dataclass
class StrategyMetrics:
    """Metrics for parsing strategy performance."""
    processing_time: float
    memory_used_mb: float
    elements_extracted: int
    error_count: int
    strategy_name: str
    file_size_mb: float
    success: bool = True
    cache_hit: bool = False
    
    @property
    def elements_per_second(self) -> float:
        """Calculate elements processed per second."""
        if self.processing_time <= 0:
            return 0.0
        return self.elements_extracted / self.processing_time
    
    @property
    def memory_efficiency(self) -> float:
        """Calculate memory efficiency (elements per MB)."""
        if self.memory_used_mb <= 0:
            return 0.0
        return self.elements_extracted / self.memory_used_mb


class ParsingStrategyBase(ABC):
    """Abstract base class for parsing strategies."""
    
    def __init__(self, name: str):
        self.name = name
        self._metrics_history: List[StrategyMetrics] = []
    
    @abstractmethod
    async def parse(self, file_path: Path, progress_callback: Optional[Callable] = None, **kwargs) -> List[Any]:
        """Parse document and return elements."""
        pass
    
    @abstractmethod
    def can_handle(self, file_path: Path, file_size_mb: float) -> bool:
        """Check if this strategy can handle the file."""
        pass
    
    @abstractmethod
    def estimate_resources(self, file_path: Path, file_size_mb: float) -> Dict[str, float]:
        """Estimate resource requirements for parsing."""
        pass
    
    async def parse_with_metrics(self, file_path: Path, **kwargs) -> tuple[List[Any], StrategyMetrics]:
        """Parse with comprehensive metrics collection."""
        start_time = time.time()
        start_memory = self._get_process_memory_mb()
        
        try:
            elements = await self.parse(file_path, **kwargs)
            success = True
            error_count = 0
        except Exception as e:
            elements = []
            success = False
            error_count = 1
            raise
        finally:
            processing_time = time.time() - start_time
            end_memory = self._get_process_memory_mb()
            memory_used = max(0, end_memory - start_memory)
            
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            
            metrics = StrategyMetrics(
                processing_time=processing_time,
                memory_used_mb=memory_used,
                elements_extracted=len(elements),
                error_count=error_count,
                strategy_name=self.name,
                file_size_mb=file_size_mb,
                success=success
            )
            
            self._metrics_history.append(metrics)
            
        return elements, metrics
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary from metrics history."""
        if not self._metrics_history:
            return {"strategy": self.name, "total_runs": 0}
        
        successful_runs = [m for m in self._metrics_history if m.success]
        
        if not successful_runs:
            return {
                "strategy": self.name,
                "total_runs": len(self._metrics_history),
                "success_rate": 0.0
            }
        
        avg_time = sum(m.processing_time for m in successful_runs) / len(successful_runs)
        avg_memory = sum(m.memory_used_mb for m in successful_runs) / len(successful_runs)
        avg_elements = sum(m.elements_extracted for m in successful_runs) / len(successful_runs)
        
        return {
            "strategy": self.name,
            "total_runs": len(self._metrics_history),
            "successful_runs": len(successful_runs),
            "success_rate": len(successful_runs) / len(self._metrics_history),
            "avg_processing_time": avg_time,
            "avg_memory_used_mb": avg_memory,
            "avg_elements_extracted": avg_elements,
            "avg_elements_per_second": avg_elements / avg_time if avg_time > 0 else 0
        }
    
    def _get_process_memory_mb(self) -> float:
        """Get current process memory usage in MB."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / (1024 * 1024)
        except ImportError:
            # Fallback if psutil not available
            return 0.0