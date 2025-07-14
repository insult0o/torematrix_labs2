"""
Pipeline configuration models using Pydantic for validation.

Provides configuration structures for pipeline, stages, and resource requirements.
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any, Optional
from enum import Enum


class StageType(str, Enum):
    """Types of pipeline stages."""
    PROCESSOR = "processor"
    VALIDATOR = "validator"
    TRANSFORMER = "transformer"
    ROUTER = "router"
    AGGREGATOR = "aggregator"


class ResourceRequirements(BaseModel):
    """Resource requirements for a stage."""
    cpu_cores: float = Field(default=1.0, ge=0.1, le=16.0)
    memory_mb: int = Field(default=512, ge=128, le=65536)
    gpu_required: bool = Field(default=False)
    gpu_memory_mb: Optional[int] = Field(default=None, ge=512)
    
    @field_validator('gpu_memory_mb')
    @classmethod
    def validate_gpu_memory(cls, v: Optional[int], info) -> Optional[int]:
        """Validate GPU memory is specified if GPU is required."""
        if info.data.get('gpu_required') and v is None:
            raise ValueError("GPU memory must be specified if GPU is required")
        return v


class StageConfig(BaseModel):
    """Configuration for a pipeline stage."""
    name: str = Field(..., min_length=1, max_length=64)
    type: StageType
    processor: str = Field(..., description="Processor class or module path")
    dependencies: List[str] = Field(default_factory=list)
    config: Dict[str, Any] = Field(default_factory=dict)
    
    # Execution settings
    timeout: int = Field(default=300, ge=1, le=3600, description="Timeout in seconds")
    retries: int = Field(default=3, ge=0, le=10)
    critical: bool = Field(default=True, description="Fail pipeline if stage fails")
    conditional: Optional[str] = Field(default=None, description="Condition expression")
    
    # Resource requirements
    resources: ResourceRequirements = Field(default_factory=ResourceRequirements)
    
    # Parallelism
    max_parallel: int = Field(default=1, ge=1, le=100)
    batch_size: Optional[int] = Field(default=None, ge=1, le=1000)


class PipelineConfig(BaseModel):
    """Configuration for a processing pipeline."""
    name: str = Field(..., min_length=1, max_length=128)
    version: str = Field(default="1.0.0")
    description: Optional[str] = None
    
    # Stages
    stages: List[StageConfig]
    
    # Global settings
    max_parallel_stages: int = Field(default=4, ge=1, le=20)
    checkpoint_enabled: bool = Field(default=True)
    checkpoint_ttl: int = Field(default=86400, description="Checkpoint TTL in seconds")
    
    # Resource limits
    max_memory_mb: int = Field(default=8192, ge=512)
    max_cpu_cores: float = Field(default=8.0, ge=1.0)
    
    # Timeouts
    global_timeout: int = Field(default=3600, ge=60, description="Global timeout in seconds")
    stage_timeout_multiplier: float = Field(default=1.0, ge=0.1, le=10.0)
    
    @field_validator('stages')
    @classmethod
    def validate_stage_names(cls, stages: List[StageConfig]) -> List[StageConfig]:
        """Validate stage names are unique."""
        names = [s.name for s in stages]
        if len(names) != len(set(names)):
            raise ValueError("Stage names must be unique")
        return stages
    
    @field_validator('stages')
    @classmethod
    def validate_dependencies(cls, stages: List[StageConfig]) -> List[StageConfig]:
        """Validate all dependencies exist."""
        stage_names = {s.name for s in stages}
        for stage in stages:
            for dep in stage.dependencies:
                if dep not in stage_names:
                    raise ValueError(f"Unknown dependency {dep} in stage {stage.name}")
        return stages
    
    @classmethod
    def from_yaml(cls, yaml_path: str) -> 'PipelineConfig':
        """Load configuration from YAML file."""
        import yaml
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_path: str) -> 'PipelineConfig':
        """Load configuration from JSON file."""
        import json
        with open(json_path, 'r') as f:
            data = json.load(f)
        return cls(**data)