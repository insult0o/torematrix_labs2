#!/usr/bin/env python3
"""
Validation State Model for TORE Matrix Labs V2

Simplified validation state management consolidating the complex
validation logic from the original codebase.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
from datetime import datetime


class ValidationStatus(Enum):
    """Validation status options."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    REQUIRES_REVIEW = "requires_review"


@dataclass
class ValidationRule:
    """A validation rule."""
    id: str
    name: str
    description: str
    rule_type: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True


@dataclass
class ValidationState:
    """Validation state for documents and areas."""
    status: ValidationStatus = ValidationStatus.NOT_STARTED
    rules_applied: List[str] = field(default_factory=list)
    issues_found: List[Dict[str, Any]] = field(default_factory=list)
    quality_score: float = 0.0
    validated_at: Optional[datetime] = None
    validated_by: Optional[str] = None
    notes: str = ""