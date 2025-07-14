"""
Unit tests for pipeline templates.
"""

import pytest

from torematrix.processing.pipeline.templates import (
    PipelineTemplate,
    StandardDocumentPipeline,
    BatchProcessingPipeline,
    QualityAssurancePipeline,
    get_template,
    list_templates,
    create_pipeline_from_template,
    PIPELINE_TEMPLATES
)
from torematrix.processing.pipeline.config import StageType


class TestPipelineTemplates:
    """Test cases for pipeline template system."""
    
    def test_list_templates(self):
        """Test listing available templates."""
        templates = list_templates()
        
        assert "standard" in templates
        assert "batch" in templates
        assert "qa" in templates
        assert len(templates) == len(PIPELINE_TEMPLATES)
    
    def test_get_template_valid(self):
        """Test getting valid template."""
        template = get_template("standard")
        assert template == StandardDocumentPipeline
        
        template = get_template("batch")
        assert template == BatchProcessingPipeline
        
        template = get_template("qa")
        assert template == QualityAssurancePipeline
    
    def test_get_template_invalid(self):
        """Test getting invalid template."""
        with pytest.raises(ValueError) as exc:
            get_template("nonexistent")
        
        assert "Unknown template" in str(exc.value)
        assert "Available:" in str(exc.value)


class TestStandardDocumentPipeline:
    """Test cases for StandardDocumentPipeline template."""
    
    def test_minimal_configuration(self):
        """Test creating pipeline with minimal configuration."""
        config = StandardDocumentPipeline.create_config()
        
        assert config.name == "standard-document-pipeline"
        assert len(config.stages) >= 4  # At least validation, extraction, text processing, aggregation
        
        # Check stage types
        stage_names = [s.name for s in config.stages]
        assert "validation" in stage_names
        assert "extraction" in stage_names
        assert "text_processing" in stage_names
        assert "aggregation" in stage_names
    
    def test_with_ocr_enabled(self):
        """Test pipeline with OCR enabled."""
        config = StandardDocumentPipeline.create_config(enable_ocr=True)
        
        stage_names = [s.name for s in config.stages]
        assert "ocr" in stage_names
        
        # Check OCR stage configuration
        ocr_stage = next(s for s in config.stages if s.name == "ocr")
        assert ocr_stage.type == StageType.PROCESSOR
        assert ocr_stage.conditional == "has_images or low_text_quality"
        assert "language" in ocr_stage.config
    
    def test_with_ocr_disabled(self):
        """Test pipeline with OCR disabled."""
        config = StandardDocumentPipeline.create_config(enable_ocr=False)
        
        stage_names = [s.name for s in config.stages]
        assert "ocr" not in stage_names
    
    def test_with_translation_enabled(self):
        """Test pipeline with translation enabled."""
        config = StandardDocumentPipeline.create_config(
            enable_translation=True,
            target_language="es"
        )
        
        stage_names = [s.name for s in config.stages]
        assert "translation" in stage_names
        
        # Check translation stage
        translation_stage = next(s for s in config.stages if s.name == "translation")
        assert translation_stage.config["target_language"] == "es"
        assert translation_stage.dependencies == ["text_processing"]
    
    def test_with_pii_removal(self):
        """Test pipeline with PII removal."""
        config = StandardDocumentPipeline.create_config(
            enable_pii_removal=True,
            pii_confidence=0.9
        )
        
        stage_names = [s.name for s in config.stages]
        assert "pii_removal" in stage_names
        
        # Check PII stage
        pii_stage = next(s for s in config.stages if s.name == "pii_removal")
        assert pii_stage.config["detection_confidence"] == 0.9
        assert "PERSON" in pii_stage.config["entity_types"]
    
    def test_all_features_enabled(self):
        """Test pipeline with all features enabled."""
        config = StandardDocumentPipeline.create_config(
            name="full-featured-pipeline",
            enable_ocr=True,
            enable_translation=True,
            enable_pii_removal=True,
            target_language="fr",
            ocr_language="fra"
        )
        
        assert config.name == "full-featured-pipeline"
        
        stage_names = [s.name for s in config.stages]
        assert "ocr" in stage_names
        assert "translation" in stage_names
        assert "pii_removal" in stage_names
        
        # Check dependencies are correct
        translation_stage = next(s for s in config.stages if s.name == "translation")
        assert "pii_removal" in translation_stage.dependencies
        
        # Check aggregation depends on all processors
        aggregation_stage = next(s for s in config.stages if s.name == "aggregation")
        assert "translation" in aggregation_stage.dependencies
        assert "ocr" in aggregation_stage.dependencies
    
    def test_custom_parameters(self):
        """Test custom parameters."""
        config = StandardDocumentPipeline.create_config(
            max_size_mb=200,
            allowed_types=["pdf", "docx"],
            extraction_strategy="hi_res",
            max_parallel_stages=8,
            checkpoint_enabled=False,
            max_memory_mb=8192,
            output_format="xml"
        )
        
        # Check validation config
        validation_stage = next(s for s in config.stages if s.name == "validation")
        assert validation_stage.config["max_size_mb"] == 200
        assert validation_stage.config["allowed_types"] == ["pdf", "docx"]
        
        # Check extraction config
        extraction_stage = next(s for s in config.stages if s.name == "extraction")
        assert extraction_stage.config["strategy"] == "hi_res"
        
        # Check aggregation config
        aggregation_stage = next(s for s in config.stages if s.name == "aggregation")
        assert aggregation_stage.config["output_format"] == "xml"
        
        # Check pipeline config
        assert config.max_parallel_stages == 8
        assert config.checkpoint_enabled is False
        assert config.max_memory_mb == 8192


class TestBatchProcessingPipeline:
    """Test cases for BatchProcessingPipeline template."""
    
    def test_default_configuration(self):
        """Test default batch processing configuration."""
        config = BatchProcessingPipeline.create_config()
        
        assert config.name == "batch-processing-pipeline"
        assert len(config.stages) == 3
        
        stage_names = [s.name for s in config.stages]
        assert "batch_validation" in stage_names
        assert "batch_extraction" in stage_names
        assert "batch_aggregation" in stage_names
    
    def test_custom_batch_size(self):
        """Test custom batch size configuration."""
        config = BatchProcessingPipeline.create_config(
            batch_size=50,
            parallel_workers=8
        )
        
        # Check batch validation
        validation_stage = next(s for s in config.stages if s.name == "batch_validation")
        assert validation_stage.config["batch_size"] == 50
        
        # Check batch extraction
        extraction_stage = next(s for s in config.stages if s.name == "batch_extraction")
        assert extraction_stage.config["batch_size"] == 50
        assert extraction_stage.config["parallel_workers"] == 8
    
    def test_resource_configuration(self):
        """Test resource configuration for batch processing."""
        config = BatchProcessingPipeline.create_config(
            batch_cpu_cores=8.0,
            batch_memory_mb=4096
        )
        
        extraction_stage = next(s for s in config.stages if s.name == "batch_extraction")
        assert extraction_stage.resources.cpu_cores == 8.0
        assert extraction_stage.resources.memory_mb == 4096
    
    def test_output_configuration(self):
        """Test output configuration."""
        config = BatchProcessingPipeline.create_config(
            output_format="csv",
            compression="bzip2"
        )
        
        aggregation_stage = next(s for s in config.stages if s.name == "batch_aggregation")
        assert aggregation_stage.config["output_format"] == "csv"
        assert aggregation_stage.config["compression"] == "bzip2"


class TestQualityAssurancePipeline:
    """Test cases for QualityAssurancePipeline template."""
    
    def test_default_configuration(self):
        """Test default QA pipeline configuration."""
        config = QualityAssurancePipeline.create_config()
        
        assert config.name == "qa-pipeline"
        assert len(config.stages) == 5
        
        stage_names = [s.name for s in config.stages]
        assert "extraction" in stage_names
        assert "quality_analysis" in stage_names
        assert "enhancement" in stage_names
        assert "final_validation" in stage_names
        assert "qa_report" in stage_names
    
    def test_quality_thresholds(self):
        """Test quality threshold configuration."""
        config = QualityAssurancePipeline.create_config(
            min_text_quality=0.9,
            strict_mode=False
        )
        
        # Check quality analysis
        analysis_stage = next(s for s in config.stages if s.name == "quality_analysis")
        assert analysis_stage.config["min_text_quality"] == 0.9
        
        # Check final validation
        validation_stage = next(s for s in config.stages if s.name == "final_validation")
        assert validation_stage.config["strict_mode"] is False
    
    def test_conditional_enhancement(self):
        """Test conditional enhancement stage."""
        config = QualityAssurancePipeline.create_config()
        
        enhancement_stage = next(s for s in config.stages if s.name == "enhancement")
        assert enhancement_stage.conditional == "quality_score < 0.8"
        assert enhancement_stage.dependencies == ["quality_analysis"]
    
    def test_report_format(self):
        """Test QA report format configuration."""
        config = QualityAssurancePipeline.create_config(report_format="pdf")
        
        report_stage = next(s for s in config.stages if s.name == "qa_report")
        assert report_stage.config["format"] == "pdf"
        assert report_stage.config["include_metrics"] is True
        assert report_stage.config["include_recommendations"] is True
    
    def test_pipeline_settings(self):
        """Test QA pipeline settings."""
        config = QualityAssurancePipeline.create_config()
        
        # QA should use limited parallelism for sequential processing
        assert config.max_parallel_stages == 2
        assert config.checkpoint_enabled is True


class TestCreatePipelineFromTemplate:
    """Test cases for create_pipeline_from_template function."""
    
    def test_create_standard_pipeline(self):
        """Test creating standard pipeline from template."""
        config = create_pipeline_from_template(
            "standard",
            enable_ocr=True,
            max_memory_mb=8192
        )
        
        assert config.name == "standard-document-pipeline"
        assert config.max_memory_mb == 8192
        
        stage_names = [s.name for s in config.stages]
        assert "ocr" in stage_names
    
    def test_create_batch_pipeline(self):
        """Test creating batch pipeline from template."""
        config = create_pipeline_from_template(
            "batch",
            batch_size=25,
            name="custom-batch-pipeline"
        )
        
        assert config.name == "custom-batch-pipeline"
        
        validation_stage = next(s for s in config.stages if s.name == "batch_validation")
        assert validation_stage.config["batch_size"] == 25
    
    def test_create_qa_pipeline(self):
        """Test creating QA pipeline from template."""
        config = create_pipeline_from_template(
            "qa",
            min_text_quality=0.95,
            report_format="json"
        )
        
        assert config.name == "qa-pipeline"
        
        analysis_stage = next(s for s in config.stages if s.name == "quality_analysis")
        assert analysis_stage.config["min_text_quality"] == 0.95
    
    def test_create_invalid_template(self):
        """Test creating pipeline from invalid template."""
        with pytest.raises(ValueError) as exc:
            create_pipeline_from_template("invalid_template")
        
        assert "Unknown template" in str(exc.value)