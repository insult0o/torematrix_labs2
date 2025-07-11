#!/usr/bin/env python3
"""
TORE Matrix Labs - Main entry point for package execution.
"""

import sys
import os
from pathlib import Path

# Add package root to path
package_root = Path(__file__).parent
sys.path.insert(0, str(package_root))

from tore_matrix_labs import main

if __name__ == "__main__":
    main()