"""
Unit tests for pipeline configuration.
"""

import pytest
from pydantic import ValidationError

from torematrix.processing.pipeline.config import (
    PipelineConfig,
    StageConfig,
    StageType,
    ResourceRequirements
)


class TestResourceRequirements:
    """Test cases for ResourceRequirements."""
    
    def test_default_values(self):
        """Test default resource requirement values."""
        resources = ResourceRequirements()
        assert resources.cpu_cores == 1.0
        assert resources.memory_mb == 512
        assert resources.gpu_required is False
        assert resources.gpu_memory_mb is None
    
    def test_valid_resource_limits(self):
        """Test valid resource limit values."""
        resources = ResourceRequirements(
            cpu_cores=4.0,
            memory_mb=2048,
            gpu_required=True,
            gpu_memory_mb=8192
        )
        assert resources.cpu_cores == 4.0
        assert resources.memory_mb == 2048
        assert resources.gpu_memory_mb == 8192
    
    def test_cpu_cores_validation(self):
        """Test CPU cores validation."""
        # Too low
        with pytest.raises(ValidationError):
            ResourceRequirements(cpu_cores=0.05)
        
        # Too high
        with pytest.raises(ValidationError):
            ResourceRequirements(cpu_cores=20.0)
        
        # Valid edge cases
        ResourceRequirements(cpu_cores=0.1)
        ResourceRequirements(cpu_cores=16.0)
    
    def test_memory_validation(self):
        """Test memory validation."""
        # Too low
        with pytest.raises(ValidationError):
            ResourceRequirements(memory_mb=64)
        
        # Too high
        with pytest.raises(ValidationError):
            ResourceRequirements(memory_mb=100000)
        
        # Valid edge cases
        ResourceRequirements(memory_mb=128)
        ResourceRequirements(memory_mb=65536)
    
    def test_gpu_memory_validation(self):
        """Test GPU memory validation."""
        # GPU memory without GPU required is OK
        resources = ResourceRequirements(gpu_memory_mb=1024)
        assert resources.gpu_memory_mb == 1024
        
        # GPU required without memory specified
        with pytest.raises(ValidationError) as exc:
            ResourceRequirements(gpu_required=True)
        assert "GPU memory must be specified" in str(exc.value)
        
        # GPU required with memory
        resources = ResourceRequirements(gpu_required=True, gpu_memory_mb=2048)
        assert resources.gpu_memory_mb == 2048


class TestStageConfig:
    """Test cases for StageConfig."""
    
    def test_minimal_config(self):
        """Test minimal stage configuration."""
        stage = StageConfig(
            name="test_stage",
            type=StageType.PROCESSOR,
            processor="torematrix.processor.TestProcessor"
        )
        assert stage.name == "test_stage"
        assert stage.type == StageType.PROCESSOR
        assert stage.dependencies == []
        assert stage.timeout == 300
        assert stage.retries == 3
        assert stage.critical is True
    
    def test_full_config(self):
        """Test full stage configuration."""
        stage = StageConfig(
            name="test_stage",
            type=StageType.VALIDATOR,
            processor="torematrix.validator.TestValidator",
            dependencies=["stage1", "stage2"],
            config={"threshold": 0.8, "strict": True},
            timeout=600,
            retries=5,
            critical=False,
            conditional="has_images",
            resources=ResourceRequirements(cpu_cores=2.0, memory_mb=1024),
            max_parallel=4,
            batch_size=100
        )
        assert stage.name == "test_stage"
        assert stage.dependencies == ["stage1", "stage2"]
        assert stage.config["threshold"] == 0.8
        assert stage.timeout == 600
        assert stage.resources.cpu_cores == 2.0
    
    def test_stage_name_validation(self):
        """Test stage name validation."""
        # Empty name
        with pytest.raises(ValidationError):
            StageConfig(name="", type=StageType.PROCESSOR, processor="test")
        
        # Too long name
        with pytest.raises(ValidationError):
            StageConfig(
                name="a" * 65,
                type=StageType.PROCESSOR,
                processor="test"
            )
    
    def test_timeout_validation(self):
        """Test timeout validation."""
        # Too low
        with pytest.raises(ValidationError):
            StageConfig(
                name="test",
                type=StageType.PROCESSOR,
                processor="test",
                timeout=0
            )
        
        # Too high
        with pytest.raises(ValidationError):
            StageConfig(
                name="test",
                type=StageType.PROCESSOR,
                processor="test",
                timeout=4000
            )


class TestPipelineConfig:
    """Test cases for PipelineConfig."""
    
    def test_minimal_pipeline(self):
        """Test minimal pipeline configuration."""
        config = PipelineConfig(
            name="test_pipeline",
            stages=[
                StageConfig(
                    name="stage1",
                    type=StageType.PROCESSOR,
                    processor="test.processor"
                )
            ]
        )
        assert config.name == "test_pipeline"
        assert config.version == "1.0.0"
        assert len(config.stages) == 1
        assert config.checkpoint_enabled is True
    
    def test_complex_pipeline(self):
        """Test complex pipeline configuration."""
        config = PipelineConfig(
            name="complex_pipeline",
            version="2.0.0",
            description="A complex test pipeline",
            stages=[
                StageConfig(
                    name="validation",
                    type=StageType.VALIDATOR,
                    processor="validator"
                ),
                StageConfig(
                    name="extraction",
                    type=StageType.PROCESSOR,
                    processor="extractor",
                    dependencies=["validation"]
                ),
                StageConfig(
                    name="transformation",
                    type=StageType.TRANSFORMER,
                    processor="transformer",
                    dependencies=["extraction"]
                )
            ],
            max_parallel_stages=2,
            checkpoint_enabled=False,
            max_memory_mb=4096,
            max_cpu_cores=4.0,
            global_timeout=7200
        )
        assert config.name == "complex_pipeline"
        assert len(config.stages) == 3
        assert config.max_parallel_stages == 2
        assert config.checkpoint_enabled is False
    
    def test_duplicate_stage_names(self):
        """Test that duplicate stage names are rejected."""
        with pytest.raises(ValidationError) as exc:
            PipelineConfig(
                name="test",
                stages=[
                    StageConfig(name="stage1", type=StageType.PROCESSOR, processor="p1"),
                    StageConfig(name="stage1", type=StageType.PROCESSOR, processor="p2")
                ]
            )
        assert "Stage names must be unique" in str(exc.value)
    
    def test_invalid_dependencies(self):
        """Test that invalid dependencies are rejected."""
        with pytest.raises(ValidationError) as exc:
            PipelineConfig(
                name="test",
                stages=[
                    StageConfig(
                        name="stage1",
                        type=StageType.PROCESSOR,
                        processor="p1",
                        dependencies=["nonexistent"]
                    )
                ]
            )
        assert "Unknown dependency" in str(exc.value)
    
    def test_valid_dependencies(self):
        """Test valid dependency configuration."""
        config = PipelineConfig(
            name="test",
            stages=[
                StageConfig(name="stage1", type=StageType.PROCESSOR, processor="p1"),
                StageConfig(
                    name="stage2",
                    type=StageType.PROCESSOR,
                    processor="p2",
                    dependencies=["stage1"]
                ),
                StageConfig(
                    name="stage3",
                    type=StageType.AGGREGATOR,
                    processor="p3",
                    dependencies=["stage1", "stage2"]
                )
            ]
        )
        assert config.stages[1].dependencies == ["stage1"]
        assert config.stages[2].dependencies == ["stage1", "stage2"]
    
    def test_from_yaml(self, tmp_path):
        """Test loading configuration from YAML."""
        yaml_content = """
name: yaml_pipeline
version: 1.0.0
stages:
  - name: stage1
    type: processor
    processor: test.processor
    dependencies: []
  - name: stage2
    type: validator
    processor: test.validator
    dependencies: [stage1]
"""
        yaml_file = tmp_path / "pipeline.yaml"
        yaml_file.write_text(yaml_content)
        
        config = PipelineConfig.from_yaml(str(yaml_file))
        assert config.name == "yaml_pipeline"
        assert len(config.stages) == 2
        assert config.stages[1].dependencies == ["stage1"]
    
    def test_from_json(self, tmp_path):
        """Test loading configuration from JSON."""
        json_content = """
{
    "name": "json_pipeline",
    "version": "2.0.0",
    "stages": [
        {
            "name": "stage1",
            "type": "processor",
            "processor": "test.processor",
            "dependencies": []
        },
        {
            "name": "stage2",
            "type": "transformer",
            "processor": "test.transformer",
            "dependencies": ["stage1"]
        }
    ]
}
"""
        json_file = tmp_path / "pipeline.json"
        json_file.write_text(json_content)
        
        config = PipelineConfig.from_json(str(json_file))
        assert config.name == "json_pipeline"
        assert config.version == "2.0.0"
        assert len(config.stages) == 2
    
    def test_pipeline_name_validation(self):
        """Test pipeline name validation."""
        # Empty name
        with pytest.raises(ValidationError):
            PipelineConfig(name="", stages=[])
        
        # Too long name
        with pytest.raises(ValidationError):
            PipelineConfig(name="a" * 129, stages=[])
    
    def test_resource_limit_validation(self):
        """Test resource limit validation."""
        # Valid limits
        config = PipelineConfig(
            name="test",
            stages=[],
            max_memory_mb=16384,
            max_cpu_cores=16.0
        )
        assert config.max_memory_mb == 16384
        assert config.max_cpu_cores == 16.0
        
        # Invalid memory
        with pytest.raises(ValidationError):
            PipelineConfig(name="test", stages=[], max_memory_mb=256)
        
        # Invalid CPU
        with pytest.raises(ValidationError):
            PipelineConfig(name="test", stages=[], max_cpu_cores=0.5)