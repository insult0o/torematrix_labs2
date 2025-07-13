"""Central parser manager with intelligent routing and monitoring."""

import asyncio
import time
import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass

from torematrix_parser.src.torematrix.core.models.element import Element as UnifiedElement
from ..factory import ParserFactory
from ..types import ProcessingHints
from ..base import ParserResult
from .cache import ParserCache
from .monitor import ParserMonitor
from .fallback_handler import FallbackHandler


@dataclass
class ParseRequest:
    """Request for parsing operation."""
    element: UnifiedElement
    priority: int = 0
    timeout: float = 30.0
    use_cache: bool = True
    hints: Optional[ProcessingHints] = None
    callback: Optional[Callable] = None


@dataclass
class ParseResponse:
    """Response from parsing operation."""
    success: bool
    result: Optional[ParserResult]
    error: Optional[str]
    processing_time: float
    cache_hit: bool = False
    parser_used: Optional[str] = None


class ParserManager:
    """Central manager for all parser operations."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.factory = ParserFactory()
        self.cache = ParserCache(config.get('cache', {}))
        self.monitor = ParserMonitor()
        self.fallback = FallbackHandler()
        self.logger = logging.getLogger("torematrix.parsers.manager")
        
        # Performance settings
        self.max_concurrent = config.get('max_concurrent', 10)
        self.default_timeout = config.get('default_timeout', 30.0)
        self.enable_caching = config.get('enable_caching', True)
        self.enable_monitoring = config.get('enable_monitoring', True)
        
        # Statistics
        self._stats = {
            'total_requests': 0,
            'successful_parses': 0,
            'cache_hits': 0,
            'errors': 0,
            'total_time': 0.0,
            'parser_usage': {}
        }
        
        # Request tracking
        self._active_requests = {}
        self._request_counter = 0
    
    async def parse_element(self, element: UnifiedElement, **kwargs) -> ParseResponse:
        """Parse a single element with full monitoring."""
        request = ParseRequest(element=element, **kwargs)
        return await self._execute_parse_request(request)
    
    async def parse_batch(self, elements: List[UnifiedElement], **kwargs) -> List[ParseResponse]:
        """Parse multiple elements concurrently."""
        requests = [ParseRequest(element=elem, **kwargs) for elem in elements]
        
        # Process in batches to respect concurrency limits
        results = []
        for i in range(0, len(requests), self.max_concurrent):
            batch = requests[i:i + self.max_concurrent]
            batch_results = await asyncio.gather(
                *[self._execute_parse_request(req) for req in batch],
                return_exceptions=True
            )
            
            # Handle exceptions
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    error_response = ParseResponse(
                        success=False,
                        result=None,
                        error=str(result),
                        processing_time=0.0
                    )
                    results.append(error_response)
                else:
                    results.append(result)
        
        return results
    
    async def _execute_parse_request(self, request: ParseRequest) -> ParseResponse:
        """Execute a single parse request with full monitoring."""
        start_time = time.time()
        request_id = self._get_request_id()
        
        try:
            # Track active request
            self._active_requests[request_id] = {
                'element_type': getattr(request.element, 'type', 'unknown'),
                'start_time': start_time
            }
            
            # Update statistics
            self._stats['total_requests'] += 1
            
            # Check cache first
            if request.use_cache and self.enable_caching:
                cached_result = await self.cache.get(request.element)
                if cached_result:
                    self._stats['cache_hits'] += 1
                    processing_time = time.time() - start_time
                    
                    return ParseResponse(
                        success=True,
                        result=cached_result,
                        error=None,
                        processing_time=processing_time,
                        cache_hit=True,
                        parser_used="cache"
                    )
            
            # Get appropriate parser
            parser = self.factory.get_parser(request.element, request.hints)
            if not parser:
                # Try fallback strategies
                fallback_response = await self.fallback.handle_no_parser(request.element)
                if fallback_response:
                    return fallback_response
                
                return ParseResponse(
                    success=False,
                    result=None,
                    error=f"No suitable parser found for element type: {getattr(request.element, 'type', 'unknown')}",
                    processing_time=time.time() - start_time
                )
            
            parser_name = parser.__class__.__name__
            
            # Execute parsing with timeout
            result = await asyncio.wait_for(
                parser.parse_with_monitoring(request.element, request.hints),
                timeout=request.timeout
            )
            
            # Cache successful results
            if result.success and self.enable_caching:
                await self.cache.set(request.element, result)
            
            # Update statistics
            self._stats['successful_parses'] += 1
            processing_time = time.time() - start_time
            self._stats['total_time'] += processing_time
            
            # Track parser usage
            if parser_name not in self._stats['parser_usage']:
                self._stats['parser_usage'][parser_name] = 0
            self._stats['parser_usage'][parser_name] += 1
            
            # Record metrics
            if self.enable_monitoring:
                await self.monitor.record_parse_metrics(
                    parser_type=parser_name,
                    element_type=getattr(request.element, 'type', 'unknown'),
                    success=result.success,
                    processing_time=processing_time,
                    confidence=result.metadata.confidence if result.metadata else 0.0
                )
            
            return ParseResponse(
                success=True,
                result=result,
                error=None,
                processing_time=processing_time,
                parser_used=parser_name
            )
            
        except asyncio.TimeoutError:
            error = f"Parsing timeout after {request.timeout}s"
            self._stats['errors'] += 1
            
            return ParseResponse(
                success=False,
                result=None,
                error=error,
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            error = f"Parsing error: {str(e)}"
            self._stats['errors'] += 1
            self.logger.error(f"Parse request {request_id} failed: {error}", exc_info=True)
            
            # Try fallback strategies
            fallback_response = await self.fallback.handle_error(request.element, e)
            if fallback_response:
                return fallback_response
            
            return ParseResponse(
                success=False,
                result=None,
                error=error,
                processing_time=time.time() - start_time
            )
        
        finally:
            # Remove from active requests
            if request_id in self._active_requests:
                del self._active_requests[request_id]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive parsing statistics."""
        stats = self._stats.copy()
        
        if stats['total_requests'] > 0:
            stats['success_rate'] = stats['successful_parses'] / stats['total_requests']
            stats['cache_hit_rate'] = stats['cache_hits'] / stats['total_requests']
            stats['average_time'] = stats['total_time'] / stats['total_requests']
            stats['error_rate'] = stats['errors'] / stats['total_requests']
        else:
            stats['success_rate'] = 0.0
            stats['cache_hit_rate'] = 0.0
            stats['average_time'] = 0.0
            stats['error_rate'] = 0.0
        
        # Add active request count
        stats['active_requests'] = len(self._active_requests)
        
        # Add parser performance
        stats['parser_performance'] = {}
        for parser_name in stats['parser_usage']:
            parser_instances = [p for p in self.factory.get_all_parsers() 
                             if p.__class__.__name__ == parser_name]
            if parser_instances:
                parser_stats = parser_instances[0].get_statistics()
                stats['parser_performance'][parser_name] = parser_stats
        
        return stats
    
    def get_active_requests(self) -> Dict[str, Any]:
        """Get information about currently active requests."""
        return self._active_requests.copy()
    
    def reset_statistics(self):
        """Reset all statistics."""
        self._stats = {
            'total_requests': 0,
            'successful_parses': 0,
            'cache_hits': 0,
            'errors': 0,
            'total_time': 0.0,
            'parser_usage': {}
        }
        
        # Reset parser statistics
        for parser in self.factory.get_all_parsers():
            parser.reset_statistics()
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform system health check."""
        health = {
            "status": "healthy",
            "timestamp": time.time(),
            "parsers_registered": len(self.factory.get_all_parsers()),
            "active_requests": len(self._active_requests),
            "cache_status": await self.cache.health_check(),
            "monitor_status": await self.monitor.health_check()
        }
        
        # Check for concerning metrics
        stats = self.get_statistics()
        if stats['error_rate'] > 0.1:  # > 10% error rate
            health['status'] = "degraded"
            health['issues'] = health.get('issues', [])
            health['issues'].append(f"High error rate: {stats['error_rate']:.1%}")
        
        if stats['average_time'] > 10.0:  # > 10s average
            health['status'] = "degraded"
            health['issues'] = health.get('issues', [])
            health['issues'].append(f"Slow parsing: {stats['average_time']:.1f}s average")
        
        return health
    
    async def configure_parser(self, parser_type: str, config: Dict[str, Any]) -> bool:
        """Configure a specific parser."""
        try:
            # Create new parser instance with config
            parser = self.factory.create_parser_instance(parser_type, config)
            if parser:
                # Re-register the parser
                self.factory.register_parser(parser_type, parser.__class__)
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to configure parser {parser_type}: {e}")
            return False
    
    async def shutdown(self):
        """Graceful shutdown of parser manager."""
        self.logger.info("Shutting down parser manager...")
        
        # Wait for active requests to complete (with timeout)
        timeout = 30.0
        start_time = time.time()
        
        while self._active_requests and (time.time() - start_time) < timeout:
            await asyncio.sleep(0.1)
        
        if self._active_requests:
            self.logger.warning(f"Shutdown timeout: {len(self._active_requests)} requests still active")
        
        # Shutdown components
        await self.cache.close()
        await self.monitor.close()
        
        self.logger.info("Parser manager shutdown complete")
    
    def _get_request_id(self) -> str:
        """Generate unique request ID."""
        self._request_counter += 1
        return f"req_{self._request_counter}_{int(time.time() * 1000) % 10000}"