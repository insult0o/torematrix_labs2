"""
TORE Matrix Labs V3 - Next-Generation Document Processing Platform

A complete ground-up rewrite leveraging all lessons learned from V1.
"""

__version__ = "3.0.0"
__author__ = "TORE Matrix Labs Team"
__email__ = "team@torematrixlabs.com"

# Version information
VERSION_MAJOR = 3
VERSION_MINOR = 0
VERSION_PATCH = 0
VERSION_INFO = (VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH)

# Project metadata
PROJECT_NAME = "TORE Matrix Labs"
PROJECT_DESCRIPTION = "Enterprise Document Processing with Zero-Hallucination AI"

# API Version for backward compatibility
API_VERSION = "v3"

# Feature flags for gradual rollout
FEATURES = {
    "unified_elements": True,
    "async_processing": True,
    "multi_backend_storage": True,
    "advanced_filtering": True,
    "rich_visualization": True,
}

def get_version() -> str:
    """Get the current version string."""
    return __version__

def get_version_info() -> tuple:
    """Get the current version as a tuple."""
    return VERSION_INFO

def is_feature_enabled(feature: str) -> bool:
    """Check if a feature is enabled."""
    return FEATURES.get(feature, False)