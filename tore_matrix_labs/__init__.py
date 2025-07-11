#!/usr/bin/env python3
"""
TORE Matrix Labs - Ultimate AI Document Processing Pipeline
Package initialization and main entry point.
"""

import sys
import os
import logging
from pathlib import Path

__version__ = "1.0.0"
__author__ = "TORE AI"
__email__ = "contact@tore-ai.com"


def main():
    """Main application entry point."""
    try:
        # Try to import GUI components using compatibility layer
        from .ui.qt_compat import QApplication, QCoreApplication, exec_app
        gui_framework_available = True
    except ImportError:
        gui_framework_available = False
    
    # Check if we should run GUI or CLI
    import os
    force_gui = '--gui' in sys.argv
    has_display = (os.environ.get('DISPLAY') is not None or 
                   os.environ.get('WAYLAND_DISPLAY') is not None)
    
    if not gui_framework_available:
        print("Warning: No GUI framework available. Please install PyQt5 or PySide6.")
        print("Falling back to CLI mode...")
        gui_available = False
    elif force_gui:
        gui_available = True
        if '--gui' in sys.argv:
            sys.argv.remove('--gui')  # Remove --gui flag before processing
    elif not has_display and len(sys.argv) == 1:
        # No display and no arguments - default to CLI help
        print("No display detected. Running in CLI mode.")
        print("Use 'python -m tore_matrix_labs --help' for CLI commands.")
        gui_available = False
    elif len(sys.argv) > 1:
        # CLI arguments provided
        gui_available = False
    else:
        # GUI mode (has display and no CLI args)
        gui_available = True
    
    if not gui_available:
        # Run CLI version
        from .cli import main as cli_main
        return cli_main()
    
    # Import other components with relative imports
    from .config.settings import Settings
    from .config.logging_config import setup_logging
    from .ui.main_window import MainWindow

    # Set application metadata
    QCoreApplication.setApplicationName("TORE Matrix Labs")
    QCoreApplication.setApplicationVersion(__version__)
    QCoreApplication.setOrganizationName("TORE AI")
    QCoreApplication.setOrganizationDomain("tore-ai.com")
    
    # Initialize logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Fix QStandardPaths runtime directory permissions (WSL2 issue)
    try:
        import stat
        runtime_dir = f"/run/user/{os.getuid()}"
        if os.path.exists(runtime_dir):
            current_perms = os.stat(runtime_dir).st_mode & 0o777
            if current_perms != 0o700:
                os.chmod(runtime_dir, 0o700)
                logger.info(f"Fixed runtime directory permissions: {runtime_dir}")
    except Exception as e:
        logger.debug(f"Could not fix runtime directory permissions: {e}")
    
    # Create application
    app = QApplication(sys.argv)
    
    try:
        # Load settings
        settings = Settings()
        
        # Create main window
        main_window = MainWindow(settings)
        main_window.show()
        
        logger.info("TORE Matrix Labs started successfully")
        
        # Run application
        sys.exit(exec_app(app))
        
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()