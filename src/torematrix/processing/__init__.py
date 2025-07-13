"""
TORE Matrix Labs V3 - Processing Pipeline Module

A comprehensive document processing pipeline system with async architecture,
monitoring, and enterprise-grade reliability features.

Features:
- Multi-stage pipeline execution
- Processor plugin system  
- Worker pool management
- Resource monitoring
- Progress tracking
- Prometheus metrics
- Health checks
- Performance benchmarks

Example usage:

```python
import asyncio
from torematrix.processing import ProcessingSystem, create_default_config

async def main():
    config = create_default_config()
    
    async with ProcessingSystem(config).processing_context() as system:
        pipeline_id = await system.process_document(
            document_path=Path("document.pdf"),
            metadata={"priority": "high"}
        )
        
        # Monitor progress
        status = system.get_pipeline_status(pipeline_id)
        print(f"Pipeline status: {status}")

asyncio.run(main())
```
"""

# Integration components (will be added by Agent 4)
# from .integration import (
#     ProcessingSystem,
#     ProcessingSystemConfig,
#     create_default_config,
#     create_high_throughput_config,
#     create_memory_efficient_config
# )

# Main monitoring (will be added by Agent 4)  
# from .monitoring import (
#     MonitoringService,
#     MetricsSummary,
#     Alert,
#     export_prometheus_metrics,
#     create_monitoring_dashboard_data
# )

from .processors.base import (
    BaseProcessor,
    ProcessorMetadata,
    ProcessorContext,
    ProcessorResult,
    ProcessorCapability,
    ProcessorPriority,
    ProcessorException
)

from .processors.registry import (
    ProcessorRegistry,
    get_registry
)

__version__ = "3.0.0"
__author__ = "TORE Matrix Labs"
__email__ = "contact@torematrix.labs"

__all__ = [
    # Processors (Agent 2 implementation)
    "BaseProcessor",
    "ProcessorMetadata",
    "ProcessorContext",
    "ProcessorResult",
    "ProcessorCapability",
    "ProcessorPriority",
    "ProcessorException",
    "ProcessorRegistry",
    "get_registry",
    
    # Integration will be added by Agent 4
    # "ProcessingSystem",
    # "ProcessingSystemConfig",
    # "create_default_config", 
    # "create_high_throughput_config",
    # "create_memory_efficient_config",
    # "MonitoringService",
    # "MetricsSummary",
    # "Alert",
    # "export_prometheus_metrics",
    # "create_monitoring_dashboard_data",
]