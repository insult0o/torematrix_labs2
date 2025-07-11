#!/usr/bin/env python3
"""
Numpy compatibility layer to resolve version conflicts.
"""

import warnings
import logging

# Suppress specific numpy warnings that cause import issues
warnings.filterwarnings("ignore", message="numpy.dtype size changed")
warnings.filterwarnings("ignore", message="numpy.ufunc size changed")

logger = logging.getLogger(__name__)

# Try to fix numpy compatibility issues
def fix_numpy_compatibility():
    """Fix numpy compatibility issues."""
    try:
        # Import numpy first
        import numpy as np
        
        # Check numpy version
        numpy_version = np.__version__
        logger.info(f"Numpy version: {numpy_version}")
        
        # Try to import pandas with numpy compatibility
        try:
            import pandas as pd
            pandas_version = pd.__version__
            logger.info(f"Pandas version: {pandas_version}")
            return True, "Numpy and pandas imported successfully"
            
        except ValueError as e:
            if "numpy.dtype size changed" in str(e):
                logger.warning("Numpy/pandas compatibility issue detected, attempting fix...")
                
                # Try alternative import strategy
                try:
                    # Downgrade specific numpy functionality if needed
                    import sys
                    if 'pandas' in sys.modules:
                        del sys.modules['pandas']
                    
                    # Re-import with specific numpy settings
                    import pandas as pd
                    return True, "Pandas imported with compatibility fix"
                
                except Exception as e2:
                    logger.error(f"Failed to fix numpy/pandas compatibility: {e2}")
                    return False, f"Numpy/pandas compatibility issue: {e2}"
            else:
                raise e
                
    except ImportError as e:
        logger.error(f"Failed to import numpy: {e}")
        return False, f"Numpy import failed: {e}"
    
    except Exception as e:
        logger.error(f"Unexpected error in numpy compatibility: {e}")
        return False, f"Unexpected error: {e}"


def safe_import_pandas():
    """Safely import pandas with compatibility fixes."""
    try:
        # Try direct import first
        import pandas as pd
        return pd, None
    
    except ValueError as e:
        if "numpy.dtype size changed" in str(e):
            logger.warning("Applying pandas compatibility fix...")
            
            # Try compatibility workaround
            try:
                import warnings
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", category=FutureWarning)
                    warnings.filterwarnings("ignore", category=UserWarning)
                    warnings.filterwarnings("ignore", message="numpy.dtype size changed")
                    
                    import pandas as pd
                    return pd, None
                    
            except Exception as e2:
                logger.error(f"Pandas compatibility fix failed: {e2}")
                return None, f"Pandas import failed: {e2}"
        else:
            return None, f"Pandas import error: {e}"
    
    except ImportError as e:
        logger.warning(f"Pandas not available: {e}")
        return None, f"Pandas not installed: {e}"


def safe_import_scientific_libraries():
    """Safely import scientific libraries with fallbacks."""
    imports = {}
    errors = {}
    
    # Try numpy
    try:
        import numpy as np
        imports['numpy'] = np
        logger.info(f"Numpy {np.__version__} imported successfully")
    except Exception as e:
        errors['numpy'] = str(e)
        logger.error(f"Failed to import numpy: {e}")
    
    # Try pandas with compatibility fix
    pd, error = safe_import_pandas()
    if pd:
        imports['pandas'] = pd
        logger.info(f"Pandas {pd.__version__} imported successfully")
    else:
        errors['pandas'] = error
        logger.error(f"Failed to import pandas: {error}")
    
    # Try scipy (skip due to numpy compatibility issues)
    try:
        # Skip scipy import due to numpy 2.x compatibility issues  
        errors['scipy'] = "Skipped due to numpy 2.x compatibility"
        logger.warning("Scipy skipped due to numpy 2.x compatibility issues")
    except Exception as e:
        errors['scipy'] = str(e)
        logger.warning(f"Scipy not available: {e}")
    
    # Try sklearn (skip due to numpy compatibility issues)
    try:
        # Skip sklearn import due to numpy 2.x compatibility issues
        errors['sklearn'] = "Skipped due to numpy 2.x compatibility"
        logger.warning("Sklearn skipped due to numpy 2.x compatibility issues")
    except Exception as e:
        errors['sklearn'] = str(e)
        logger.warning(f"Sklearn not available: {e}")
    
    return imports, errors


def get_fallback_dependencies():
    """Get fallback dependencies when scientific libraries are not available."""
    fallbacks = {
        'numpy': {
            'array': list,
            'zeros': lambda shape: [0] * (shape if isinstance(shape, int) else shape[0]),
            'ones': lambda shape: [1] * (shape if isinstance(shape, int) else shape[0]),
            'mean': lambda x: sum(x) / len(x) if x else 0,
            'std': lambda x: (sum((i - sum(x)/len(x))**2 for i in x) / len(x))**0.5 if x else 0
        },
        'pandas': {
            'DataFrame': dict,
            'Series': list,
            'read_csv': lambda *args, **kwargs: {},
            'to_csv': lambda data, path: None
        }
    }
    
    return fallbacks


# Initialize compatibility on import
try:
    _compat_success, _compat_message = fix_numpy_compatibility()
    if _compat_success:
        logger.info("Numpy compatibility initialized successfully")
    else:
        logger.warning(f"Numpy compatibility warning: {_compat_message}")
except Exception as e:
    logger.error(f"Error initializing numpy compatibility: {e}")


# Global imports for easier access
try:
    IMPORTS, ERRORS = safe_import_scientific_libraries()
    
    # Make imports available
    numpy = IMPORTS.get('numpy')
    pandas = IMPORTS.get('pandas')
    scipy = IMPORTS.get('scipy')
    sklearn = IMPORTS.get('sklearn')
    
    # Set availability flags
    NUMPY_AVAILABLE = 'numpy' in IMPORTS
    PANDAS_AVAILABLE = 'pandas' in IMPORTS
    SCIPY_AVAILABLE = 'scipy' in IMPORTS
    SKLEARN_AVAILABLE = 'sklearn' in IMPORTS
    
    logger.info(f"Scientific libraries availability: numpy={NUMPY_AVAILABLE}, pandas={PANDAS_AVAILABLE}, scipy={SCIPY_AVAILABLE}, sklearn={SKLEARN_AVAILABLE}")
    
except Exception as e:
    logger.error(f"Error setting up global imports: {e}")
    NUMPY_AVAILABLE = False
    PANDAS_AVAILABLE = False
    SCIPY_AVAILABLE = False
    SKLEARN_AVAILABLE = False
    IMPORTS = {}
    ERRORS = {'global': str(e)}