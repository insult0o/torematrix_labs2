#!/usr/bin/env python3
"""
TORE Matrix Labs V2 - Streamlined Enterprise Document Processing Pipeline

A completely refactored version of TORE Matrix Labs with:
- Bug-free architecture
- Simplified codebase
- All original features preserved
- All future plans implemented
- Enterprise-grade reliability

Version: 2.0.0
Author: TORE Matrix Labs Team
License: MIT
"""

__version__ = "2.0.0"
__author__ = "TORE Matrix Labs Team"
__license__ = "MIT"

# Core modules
from .core import *
from .ui import *
from .integrations import *

# Version info
VERSION_INFO = {
    "major": 2,
    "minor": 0,
    "patch": 0,
    "pre_release": None,
    "build": None
}

def get_version():
    """Get the current version string."""
    version = f"{VERSION_INFO['major']}.{VERSION_INFO['minor']}.{VERSION_INFO['patch']}"
    if VERSION_INFO['pre_release']:
        version += f"-{VERSION_INFO['pre_release']}"
    if VERSION_INFO['build']:
        version += f"+{VERSION_INFO['build']}"
    return version

# Public API
__all__ = [
    "__version__",
    "__author__", 
    "__license__",
    "VERSION_INFO",
    "get_version"
]