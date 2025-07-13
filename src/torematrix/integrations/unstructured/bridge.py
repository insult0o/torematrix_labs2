"""
Bridge integration between Agent 3's optimization system and Agent 1's parser infrastructure.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Type
from pathlib import Path

from ...infrastructure.parsers.parser_selector import ParserSelector, DocumentProfile
from ...infrastructure.parsers.pdf_parser_base import PDFParserBase
from .strategies.base import ParsingStrategyBase, StrategyMetrics
from .strategies.adaptive import AdaptiveStrategySelector, SelectionCriteria
from .optimization.memory_manager import MemoryManager, MemoryPriority
from .optimization.cache_manager import CacheManager, DocumentCache
from .analyzers.document_analyzer import DocumentAnalyzer, DocumentAnalysis
from .config import UnstructuredConfig

logger = logging.getLogger(__name__)


class InfrastructureParserStrategy(ParsingStrategyBase):
    """
    Adapter strategy that bridges Agent 1's parser infrastructure 
    with Agent 3's optimization system.
    """
    
    def __init__(self, parser_name: str, parser_class: Type[PDFParserBase]):
        super().__init__(f"infrastructure_{parser_name}")
        self.parser_name = parser_name
        self.parser_class = parser_class
        self._parser_instance = None
    
    async def parse(self, file_path: Path, progress_callback: Optional[callable] = None, **kwargs):
        """Parse document using Agent 1's parser infrastructure."""
        try:
            # Get parser instance
            if self._parser_instance is None:
                self._parser_instance = self.parser_class()
            
            # Use Agent 1's parser (synchronous) in executor
            loop = asyncio.get_event_loop()
            
            def sync_parse():
                # Agent 1's parsers return structured data
                result = self._parser_instance.parse(file_path)
                return self._convert_to_elements(result)
            
            elements = await loop.run_in_executor(None, sync_parse)
            
            if progress_callback:
                progress_callback(1.0)
            
            return elements
            
        except Exception as e:
            logger.error(f"Parser {self.parser_name} failed for {file_path}: {e}")
            raise
    
    def can_handle(self, file_path: Path, file_size_mb: float) -> bool:
        """Check if this parser can handle the file."""
        # Most parsers can handle reasonable sized PDFs
        if file_size_mb > 500:  # 500MB limit
            return False
        
        # Check file extension
        if file_path.suffix.lower() not in ['.pdf']:
            return False
        
        return True
    
    def estimate_resources(self, file_path: Path, file_size_mb: float) -> Dict[str, float]:
        """Estimate resource requirements."""
        # Base estimates for different parsers
        parser_factors = {
            'pdfplumber': {'memory': 3.0, 'time': 2.0},
            'pymupdf': {'memory': 2.0, 'time': 1.0},
            'pdfminer': {'memory': 4.0, 'time': 3.0},
            'pypdf2': {'memory': 1.5, 'time': 1.5}
        }
        
        factors = parser_factors.get(self.parser_name, {'memory': 2.5, 'time': 2.0})
        
        return {
            "memory_mb": max(file_size_mb * factors['memory'], 100),
            "time_seconds": max(file_size_mb * factors['time'] * 0.5, 1.0)
        }
    
    def _convert_to_elements(self, parser_result: Any) -> List[Any]:
        """Convert Agent 1's parser result to unified elements."""
        # This would integrate with the unified element model
        # For now, return mock elements
        from unittest.mock import Mock
        
        if hasattr(parser_result, 'elements'):
            return parser_result.elements
        elif isinstance(parser_result, list):
            return parser_result
        else:
            # Convert other formats to mock elements
            return [Mock(text=str(parser_result), type="text")]


class OptimizedInfrastructureBridge:
    """
    Main bridge class that integrates Agent 3's optimization system
    with Agent 1's parser infrastructure for maximum performance.
    """
    
    def __init__(self, config: Optional[UnstructuredConfig] = None):
        self.config = config or UnstructuredConfig()
        
        # Initialize optimization components
        self.memory_manager = MemoryManager(
            limit_mb=self.config.performance.memory_limit_mb,
            warning_threshold=0.8,
            pressure_threshold=0.9
        )
        
        self.cache_manager = CacheManager(
            memory_cache_mb=self.config.performance.cache_size_mb // 4,
            disk_cache_mb=self.config.performance.cache_size_mb,
            default_ttl=self.config.performance.cache_ttl
        )
        
        self.document_cache = DocumentCache(self.cache_manager)
        self.document_analyzer = DocumentAnalyzer()
        
        # Initialize Agent 1's parser selector
        self.parser_selector = ParserSelector()
        
        # Create adaptive selector and register infrastructure strategies
        self.adaptive_selector = AdaptiveStrategySelector(
            self.config, self.memory_manager
        )
        
        self._register_infrastructure_strategies()
        
        logger.info("Optimized infrastructure bridge initialized")
    
    def _register_infrastructure_strategies(self) -> None:
        """Register Agent 1's parsers as optimization strategies."""
        for parser_name, parser_class in self.parser_selector.parsers.items():
            strategy = InfrastructureParserStrategy(parser_name, parser_class)
            self.adaptive_selector.register_strategy(strategy)
            logger.debug(f"Registered parser strategy: {parser_name}")
    
    async def parse_document_optimized(self, 
                                     file_path: Path,
                                     selection_criteria: SelectionCriteria = SelectionCriteria.BALANCED,
                                     use_cache: bool = True) -> tuple[List[Any], StrategyMetrics, DocumentAnalysis]:
        """
        Parse document using optimized strategy selection with Agent 1's infrastructure.
        
        Args:
            file_path: Path to document
            selection_criteria: Strategy selection criteria
            use_cache: Whether to use caching
            
        Returns:
            Tuple of (elements, metrics, analysis)
        """
        try:
            # Step 1: Analyze document with Agent 3's analyzer
            logger.info(f"Analyzing document: {file_path.name}")
            analysis = await self.document_analyzer.analyze_document(file_path)
            
            # Step 2: Check cache first if enabled
            if use_cache:
                config_hash = self._generate_config_hash(selection_criteria)
                cached_elements = await self.document_cache.get_parsed_elements(
                    file_path, "optimized", config_hash
                )
                
                if cached_elements:
                    logger.info(f"Cache hit for {file_path.name}")
                    # Create metrics for cache hit
                    cache_metrics = StrategyMetrics(
                        processing_time=0.001,
                        memory_used_mb=0.0,
                        elements_extracted=len(cached_elements),
                        error_count=0,
                        strategy_name="cache_hit",
                        file_size_mb=analysis.technical_features.file_size_mb
                    )
                    return cached_elements, cache_metrics, analysis
            
            # Step 3: Use Agent 3's optimization for strategy selection
            selection_result = await self.adaptive_selector.select_strategy(
                file_path=file_path,
                criteria=selection_criteria,
                constraints=self._create_constraints_from_analysis(analysis)
            )
            
            selected_strategy = selection_result.selected_strategy
            logger.info(f"Selected optimized strategy: {selected_strategy.name}")
            
            # Step 4: Parse with selected strategy and collect metrics
            elements, metrics = await selected_strategy.parse_with_metrics(file_path)
            
            # Step 5: Store in cache if successful
            if use_cache and metrics.success:
                config_hash = self._generate_config_hash(selection_criteria)
                await self.document_cache.store_parsed_elements(
                    file_path, "optimized", config_hash, elements,
                    ttl=self.config.performance.cache_ttl
                )
                logger.debug(f"Cached results for {file_path.name}")
            
            # Step 6: Log performance metrics
            logger.info(
                f"Parsed {file_path.name}: {len(elements)} elements, "
                f"{metrics.processing_time:.2f}s, {metrics.memory_used_mb:.1f}MB"
            )
            
            return elements, metrics, analysis
            
        except Exception as e:
            logger.error(f"Optimized parsing failed for {file_path}: {e}")
            raise
    
    async def parse_document_fallback(self, file_path: Path) -> tuple[List[Any], StrategyMetrics]:
        """
        Fallback parsing using Agent 1's original selector without optimization.
        Used when optimization fails or for comparison.
        """
        try:
            # Use Agent 1's parser selector
            parser_names = self.parser_selector.select_parsers(file_path)
            
            for parser_name in parser_names:
                try:
                    parser_class = self.parser_selector.parsers[parser_name]
                    strategy = InfrastructureParserStrategy(parser_name, parser_class)
                    
                    elements, metrics = await strategy.parse_with_metrics(file_path)
                    
                    logger.info(f"Fallback parsing successful with {parser_name}")
                    return elements, metrics
                    
                except Exception as e:
                    logger.warning(f"Parser {parser_name} failed: {e}")
                    continue
            
            raise RuntimeError("All fallback parsers failed")
            
        except Exception as e:
            logger.error(f"Fallback parsing failed for {file_path}: {e}")
            raise
    
    def _create_constraints_from_analysis(self, analysis: DocumentAnalysis) -> Dict[str, Any]:
        """Create optimization constraints from document analysis."""
        constraints = {}
        
        if analysis.processing_hints:
            # Memory constraints
            estimated_memory = analysis.processing_hints.estimated_memory_mb
            constraints["memory_limit_mb"] = int(estimated_memory * 1.5)  # 50% buffer
            
            # Time constraints
            estimated_time = analysis.processing_hints.estimated_processing_time
            constraints["time_limit_seconds"] = int(estimated_time * 3)  # 3x buffer
        
        # File size constraints
        file_size_mb = analysis.technical_features.file_size_mb
        if file_size_mb > 100:
            constraints["memory_limit_mb"] = min(
                constraints.get("memory_limit_mb", 2048), 
                4096  # Max 4GB for very large files
            )
        
        return constraints
    
    def _generate_config_hash(self, criteria: SelectionCriteria) -> str:
        """Generate configuration hash for caching."""
        import hashlib
        config_string = f"{criteria.value}_{self.config.model_dump_json()}"
        return hashlib.sha256(config_string.encode()).hexdigest()[:16]
    
    async def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        # Get optimization stats
        adaptive_stats = self.adaptive_selector.get_selection_statistics()
        cache_stats = await self.cache_manager.get_combined_stats()
        memory_stats = self.memory_manager.get_memory_stats()
        
        return {
            "strategy_selection": adaptive_stats,
            "cache_performance": {
                "hit_rate": cache_stats.hit_rate,
                "total_entries": cache_stats.entries,
                "memory_usage_mb": cache_stats.memory_usage_mb,
                "disk_usage_mb": cache_stats.disk_usage_mb
            },
            "memory_usage": {
                "total_mb": memory_stats.total_system_mb,
                "available_mb": memory_stats.available_mb,
                "process_mb": memory_stats.process_mb,
                "pressure_level": memory_stats.pressure_level
            },
            "infrastructure_integration": {
                "registered_parsers": len(self.parser_selector.parsers),
                "available_strategies": len(self.adaptive_selector.strategies)
            }
        }
    
    async def shutdown(self) -> None:
        """Clean shutdown of optimization components."""
        logger.info("Shutting down optimized infrastructure bridge")
        self.memory_manager.shutdown()
        await self.cache_manager.clear()
        logger.info("Shutdown complete")


class BridgeFactory:
    """Factory for creating optimized bridge instances."""
    
    @staticmethod
    def create_production_bridge() -> OptimizedInfrastructureBridge:
        """Create bridge optimized for production use."""
        config = UnstructuredConfig()
        config.performance.memory_limit_mb = 4096  # 4GB
        config.performance.cache_size_mb = 2048    # 2GB cache
        config.performance.max_concurrent = 8      # 8 concurrent
        
        return OptimizedInfrastructureBridge(config)
    
    @staticmethod
    def create_development_bridge() -> OptimizedInfrastructureBridge:
        """Create bridge optimized for development use."""
        config = UnstructuredConfig()
        config.performance.memory_limit_mb = 1024  # 1GB
        config.performance.cache_size_mb = 512     # 512MB cache
        config.performance.max_concurrent = 4      # 4 concurrent
        
        return OptimizedInfrastructureBridge(config)
    
    @staticmethod
    def create_testing_bridge() -> OptimizedInfrastructureBridge:
        """Create bridge optimized for testing."""
        config = UnstructuredConfig()
        config.performance.memory_limit_mb = 256   # 256MB
        config.performance.cache_size_mb = 128     # 128MB cache
        config.performance.max_concurrent = 2      # 2 concurrent
        config.performance.cache_ttl = 60          # Short TTL for testing
        
        return OptimizedInfrastructureBridge(config)