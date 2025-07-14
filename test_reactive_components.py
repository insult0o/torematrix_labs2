"""
Standalone test runner for reactive components.
This avoids importing conflicting PySide6 modules.
"""

import sys
import os

# Add project to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Run specific tests
if __name__ == "__main__":
    import subprocess
    
    # Run tests directly without full import chain
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        "tests/unit/ui/components/",
        "-v",
        "--cov=src/torematrix/ui/components",
        "--cov-report=term-missing",
        "--tb=short",
        "-p", "no:warnings"
    ])
    
    sys.exit(result.returncode)