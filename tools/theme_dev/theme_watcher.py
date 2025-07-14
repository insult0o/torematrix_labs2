"""Theme file watching utility for development.

Provides a command-line tool for watching theme files and triggering reloads.
"""

import argparse
import logging
import time
from pathlib import Path
from typing import List

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

# Import theme system components
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from torematrix.ui.themes.engine import ThemeEngine
from torematrix.ui.themes.hot_reload import HotReloadEngine
from torematrix.core.config import ConfigManager
from torematrix.core.events import EventBus

logger = logging.getLogger(__name__)


class ThemeWatcher:
    """Command-line theme file watcher for development."""
    
    def __init__(self):
        """Initialize theme watcher."""
        self.app = None
        self.theme_engine = None
        self.hot_reload_engine = None
        self.reload_count = 0
        
    def setup_theme_system(self) -> None:
        """Setup theme system components."""
        # Create minimal Qt application
        self.app = QApplication.instance() or QApplication([])
        
        # Create core components
        event_bus = EventBus()
        config_manager = ConfigManager()
        
        # Initialize theme engine
        self.theme_engine = ThemeEngine(config_manager, event_bus)
        
        # Initialize hot reload engine
        self.hot_reload_engine = HotReloadEngine(self.theme_engine)
    
    def watch_themes(
        self, 
        theme_paths: List[Path], 
        auto_reload: bool = True,
        reload_delay: int = 1000,
        verbose: bool = False
    ) -> None:
        """Start watching theme files.
        
        Args:
            theme_paths: Paths to watch
            auto_reload: Enable automatic reloading
            reload_delay: Delay before reload in milliseconds
            verbose: Enable verbose logging
        """
        if verbose:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)
        
        # Setup theme system
        self.setup_theme_system()
        
        # Enable development mode
        self.hot_reload_engine.enable_development_mode(
            theme_paths=theme_paths,
            auto_reload=auto_reload,
            reload_delay=reload_delay
        )
        
        # Get reload manager for event connections
        reload_manager = self.hot_reload_engine.get_reload_manager()
        if reload_manager:
            reload_manager.reload_completed.connect(self._on_reload_completed)
            reload_manager.reload_failed.connect(self._on_reload_failed)
            reload_manager.theme_file_detected.connect(self._on_file_detected)
        
        logger.info(f"🔍 Watching {len(theme_paths)} theme paths for changes...")
        logger.info(f"📁 Paths: {[str(p) for p in theme_paths]}")
        logger.info(f"⚡ Auto-reload: {'enabled' if auto_reload else 'disabled'}")
        logger.info(f"⏱️  Reload delay: {reload_delay}ms")
        logger.info("Press Ctrl+C to stop watching")
        
        try:
            # Run Qt event loop
            self.app.exec()
        except KeyboardInterrupt:
            logger.info("\n👋 Stopping theme watcher...")
            self.cleanup()
    
    def _on_reload_completed(self, theme_name: str, time_taken: float) -> None:
        """Handle successful theme reload."""
        self.reload_count += 1
        logger.info(f"✅ Reloaded '{theme_name}' in {time_taken:.1f}ms (#{self.reload_count})")
    
    def _on_reload_failed(self, theme_name: str, error_message: str) -> None:
        """Handle failed theme reload."""
        logger.error(f"❌ Failed to reload '{theme_name}': {error_message}")
    
    def _on_file_detected(self, file_path: str) -> None:
        """Handle new theme file detection."""
        logger.info(f"📄 New theme file detected: {file_path}")
    
    def cleanup(self) -> None:
        """Cleanup resources."""
        if self.hot_reload_engine:
            self.hot_reload_engine.disable_development_mode()
        
        if self.app:
            self.app.quit()


def main():
    """Main entry point for theme watcher CLI."""
    parser = argparse.ArgumentParser(
        description="Watch theme files for changes and automatically reload them"
    )
    
    parser.add_argument(
        'paths',
        nargs='+',
        type=Path,
        help='Theme files or directories to watch'
    )
    
    parser.add_argument(
        '--no-auto-reload',
        action='store_true',
        help='Disable automatic reloading (manual reload only)'
    )
    
    parser.add_argument(
        '--delay',
        type=int,
        default=1000,
        help='Delay before reload in milliseconds (default: 1000)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Validate paths
    valid_paths = []
    for path in args.paths:
        if path.exists():
            valid_paths.append(path)
        else:
            logger.warning(f"Path does not exist: {path}")
    
    if not valid_paths:
        logger.error("No valid paths to watch!")
        return 1
    
    # Start watching
    watcher = ThemeWatcher()
    try:
        watcher.watch_themes(
            theme_paths=valid_paths,
            auto_reload=not args.no_auto_reload,
            reload_delay=args.delay,
            verbose=args.verbose
        )
    except Exception as e:
        logger.error(f"Theme watcher failed: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())