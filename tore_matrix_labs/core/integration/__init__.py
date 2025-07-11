#!/usr/bin/env python3
"""
Integration module for merging special area extractions with original text.
"""

from .content_integrator import (
    ContentIntegrator, 
    IntegrationMethod, 
    ContentType, 
    IntegrationPoint, 
    IntegrationResult
)

__all__ = [
    'ContentIntegrator',
    'IntegrationMethod',
    'ContentType',
    'IntegrationPoint',
    'IntegrationResult'
]