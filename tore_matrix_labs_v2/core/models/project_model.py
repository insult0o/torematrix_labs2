#!/usr/bin/env python3
"""
Project Model for TORE Matrix Labs V2

Simplified project structure consolidating project management
from the original codebase.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime


@dataclass
class ProjectSettings:
    """Project-level settings."""
    quality_threshold: float = 0.8
    auto_validation: bool = True
    processing_mode: str = "automatic"
    output_format: str = "json"
    custom_settings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProjectStats:
    """Project statistics."""
    total_documents: int = 0
    processed_documents: int = 0
    validated_documents: int = 0
    total_areas: int = 0
    processing_time: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class ProjectModel:
    """Project model for TORE Matrix Labs."""
    id: str
    name: str
    description: str = ""
    settings: ProjectSettings = field(default_factory=ProjectSettings)
    stats: ProjectStats = field(default_factory=ProjectStats)
    document_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)