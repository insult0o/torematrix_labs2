"""
Pipeline templates for common processing workflows.

Provides pre-configured pipeline templates that can be customized.
"""

from typing import Dict, Any, List, Optional
from .config import PipelineConfig, StageConfig, StageType


class PipelineTemplate:
    """Base class for pipeline templates."""
    
    @classmethod
    def create_config(cls, **kwargs) -> PipelineConfig:
        """Create pipeline configuration from template."""
        raise NotImplementedError


class StandardDocumentPipeline(PipelineTemplate):
    """Standard document processing pipeline template."""
    
    @classmethod
    def create_config(
        cls,
        name: str = "standard-document-pipeline",
        enable_ocr: bool = True,
        enable_translation: bool = False,
        enable_pii_removal: bool = False,
        **kwargs
    ) -> PipelineConfig:
        """
        Create standard document processing pipeline.
        
        Args:
            name: Pipeline name
            enable_ocr: Enable OCR processing for images
            enable_translation: Enable document translation
            enable_pii_removal: Enable PII detection and removal
            **kwargs: Additional configuration options
            
        Returns:
            Pipeline configuration
        """
        stages = []
        
        # Stage 1: Validation
        stages.append(StageConfig(
            name="validation",
            type=StageType.VALIDATOR,
            processor="torematrix.processing.validators.DocumentValidator",
            dependencies=[],
            config={
                "max_size_mb": kwargs.get("max_size_mb", 100),
                "allowed_types": kwargs.get("allowed_types", [
                    "pdf", "docx", "doc", "txt", "html", "odt", "rtf"
                ])
            }
        ))
        
        # Stage 2: Content Extraction
        stages.append(StageConfig(
            name="extraction",
            type=StageType.PROCESSOR,
            processor="torematrix.processing.processors.UnstructuredProcessor",
            dependencies=["validation"],
            config={
                "strategy": kwargs.get("extraction_strategy", "auto"),
                "include_metadata": True,
                "languages": kwargs.get("languages", ["en"])
            }
        ))
        
        # Stage 3: Text Processing
        stages.append(StageConfig(
            name="text_processing",
            type=StageType.PROCESSOR,
            processor="torematrix.processing.processors.TextProcessor",
            dependencies=["extraction"],
            config={
                "normalize_unicode": True,
                "fix_encoding": True,
                "remove_control_chars": True
            }
        ))
        
        # Optional: OCR Stage
        if enable_ocr:
            stages.append(StageConfig(
                name="ocr",
                type=StageType.PROCESSOR,
                processor="torematrix.processing.processors.OCRProcessor",
                dependencies=["extraction"],
                conditional="has_images or low_text_quality",
                config={
                    "language": kwargs.get("ocr_language", "eng"),
                    "enhance_quality": True,
                    "dpi": kwargs.get("ocr_dpi", 300)
                }
            ))
        
        # Optional: PII Removal
        if enable_pii_removal:
            stages.append(StageConfig(
                name="pii_removal",
                type=StageType.PROCESSOR,
                processor="torematrix.processing.processors.PIIProcessor",
                dependencies=["text_processing"],
                config={
                    "detection_confidence": kwargs.get("pii_confidence", 0.8),
                    "redaction_method": kwargs.get("pii_redaction", "mask"),
                    "entity_types": kwargs.get("pii_entities", [
                        "PERSON", "EMAIL", "PHONE", "SSN", "CREDIT_CARD"
                    ])
                }
            ))
        
        # Optional: Translation
        if enable_translation:
            stages.append(StageConfig(
                name="translation",
                type=StageType.PROCESSOR,
                processor="torematrix.processing.processors.TranslationProcessor",
                dependencies=["text_processing"] + (["pii_removal"] if enable_pii_removal else []),
                config={
                    "target_language": kwargs.get("target_language", "en"),
                    "source_language": kwargs.get("source_language", "auto"),
                    "preserve_formatting": True
                }
            ))
        
        # Final stage: Result Aggregation
        final_deps = ["text_processing"]
        if enable_ocr:
            final_deps.append("ocr")
        if enable_pii_removal:
            final_deps.append("pii_removal")
        if enable_translation:
            final_deps.append("translation")
        
        stages.append(StageConfig(
            name="aggregation",
            type=StageType.AGGREGATOR,
            processor="torematrix.processing.processors.ResultAggregator",
            dependencies=final_deps,
            config={
                "output_format": kwargs.get("output_format", "json"),
                "include_metadata": True,
                "include_statistics": True
            }
        ))
        
        return PipelineConfig(
            name=name,
            stages=stages,
            max_parallel_stages=kwargs.get("max_parallel_stages", 4),
            checkpoint_enabled=kwargs.get("checkpoint_enabled", True),
            max_memory_mb=kwargs.get("max_memory_mb", 4096),
            max_cpu_cores=kwargs.get("max_cpu_cores", 4.0)
        )


class BatchProcessingPipeline(PipelineTemplate):
    """Pipeline template for batch document processing."""
    
    @classmethod
    def create_config(
        cls,
        name: str = "batch-processing-pipeline",
        batch_size: int = 10,
        **kwargs
    ) -> PipelineConfig:
        """Create batch processing pipeline configuration."""
        stages = [
            # Batch validation
            StageConfig(
                name="batch_validation",
                type=StageType.VALIDATOR,
                processor="torematrix.processing.validators.BatchValidator",
                dependencies=[],
                config={
                    "batch_size": batch_size,
                    "fail_fast": kwargs.get("fail_fast", False)
                }
            ),
            
            # Parallel extraction
            StageConfig(
                name="batch_extraction",
                type=StageType.PROCESSOR,
                processor="torematrix.processing.processors.BatchExtractor",
                dependencies=["batch_validation"],
                config={
                    "parallel_workers": kwargs.get("parallel_workers", 4),
                    "batch_size": batch_size
                },
                resources=ResourceRequirements(
                    cpu_cores=kwargs.get("batch_cpu_cores", 4.0),
                    memory_mb=kwargs.get("batch_memory_mb", 2048)
                )
            ),
            
            # Batch aggregation
            StageConfig(
                name="batch_aggregation",
                type=StageType.AGGREGATOR,
                processor="torematrix.processing.processors.BatchAggregator",
                dependencies=["batch_extraction"],
                config={
                    "output_format": kwargs.get("output_format", "jsonl"),
                    "compression": kwargs.get("compression", "gzip")
                }
            )
        ]
        
        return PipelineConfig(
            name=name,
            stages=stages,
            max_parallel_stages=kwargs.get("max_parallel_stages", 2),
            checkpoint_enabled=True,
            checkpoint_ttl=kwargs.get("checkpoint_ttl", 7200)  # 2 hours
        )


class QualityAssurancePipeline(PipelineTemplate):
    """Pipeline template for document quality assurance."""
    
    @classmethod
    def create_config(
        cls,
        name: str = "qa-pipeline",
        **kwargs
    ) -> PipelineConfig:
        """Create QA pipeline configuration."""
        stages = [
            # Initial extraction
            StageConfig(
                name="extraction",
                type=StageType.PROCESSOR,
                processor="torematrix.processing.processors.UnstructuredProcessor",
                dependencies=[],
                config={
                    "strategy": "hi_res",  # High resolution for QA
                    "include_metadata": True
                }
            ),
            
            # Quality analysis
            StageConfig(
                name="quality_analysis",
                type=StageType.VALIDATOR,
                processor="torematrix.processing.validators.QualityAnalyzer",
                dependencies=["extraction"],
                config={
                    "min_text_quality": kwargs.get("min_text_quality", 0.8),
                    "check_formatting": True,
                    "check_structure": True
                }
            ),
            
            # Enhancement (conditional)
            StageConfig(
                name="enhancement",
                type=StageType.PROCESSOR,
                processor="torematrix.processing.processors.QualityEnhancer",
                dependencies=["quality_analysis"],
                conditional="quality_score < 0.8",
                config={
                    "enhance_ocr": True,
                    "fix_formatting": True,
                    "repair_structure": True
                }
            ),
            
            # Final validation
            StageConfig(
                name="final_validation",
                type=StageType.VALIDATOR,
                processor="torematrix.processing.validators.FinalValidator",
                dependencies=["enhancement", "quality_analysis"],
                config={
                    "strict_mode": kwargs.get("strict_mode", True)
                }
            ),
            
            # QA report generation
            StageConfig(
                name="qa_report",
                type=StageType.AGGREGATOR,
                processor="torematrix.processing.processors.QAReportGenerator",
                dependencies=["final_validation"],
                config={
                    "include_metrics": True,
                    "include_recommendations": True,
                    "format": kwargs.get("report_format", "html")
                }
            )
        ]
        
        return PipelineConfig(
            name=name,
            stages=stages,
            max_parallel_stages=2,  # QA needs sequential processing
            checkpoint_enabled=True
        )


# Template registry
PIPELINE_TEMPLATES = {
    "standard": StandardDocumentPipeline,
    "batch": BatchProcessingPipeline,
    "qa": QualityAssurancePipeline
}


def get_template(template_name: str) -> PipelineTemplate:
    """
    Get pipeline template by name.
    
    Args:
        template_name: Name of the template
        
    Returns:
        Pipeline template class
        
    Raises:
        ValueError: If template not found
    """
    if template_name not in PIPELINE_TEMPLATES:
        available = ", ".join(PIPELINE_TEMPLATES.keys())
        raise ValueError(f"Unknown template: {template_name}. Available: {available}")
    return PIPELINE_TEMPLATES[template_name]


def list_templates() -> List[str]:
    """Get list of available template names."""
    return list(PIPELINE_TEMPLATES.keys())


def create_pipeline_from_template(
    template_name: str,
    **kwargs
) -> PipelineConfig:
    """
    Create pipeline configuration from a template.
    
    Args:
        template_name: Name of the template to use
        **kwargs: Template-specific configuration options
        
    Returns:
        Pipeline configuration
    """
    template_class = get_template(template_name)
    return template_class.create_config(**kwargs)