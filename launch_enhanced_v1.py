#!/usr/bin/env python3
"""
Enhanced V1 Launcher for TORE Matrix Labs

This launcher starts the V1 application with all the V2-style enhancements:
- Enhanced event system with unified event bus
- Global signal processor for coordinated workflows  
- Enhanced persistence with state management and auto-save
- Progress persistence for recovery capabilities
- Signal bridge for V1 ↔ V2 compatibility

Usage:
    python launch_enhanced_v1.py
"""

import sys
import logging
from pathlib import Path
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

# Setup enhanced logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('enhanced_v1.log')
    ]
)

logger = logging.getLogger(__name__)

def setup_enhanced_systems():
    """Setup the V2-style enhancement systems for V1."""
    logger.info("Setting up enhanced systems...")
    
    # Import enhancement systems
    try:
        from enhanced_event_system import UnifiedEventBus, SignalBridge, GlobalSignalProcessor
        from enhanced_persistence import (
            PersistenceService, PersistenceConfig, PersistenceMode,
            StateCategory, PersistenceLevel
        )
        
        logger.info("✅ Enhancement modules imported successfully")
    except ImportError as e:
        logger.error(f"❌ Failed to import enhancement modules: {e}")
        logger.info("Running without enhancements...")
        return None, None, None
    
    try:
        # 1. Initialize Unified Event Bus
        event_bus = UnifiedEventBus()
        logger.info("✅ Unified Event Bus initialized")
        
        # 2. Initialize Global Signal Processor  
        signal_processor = GlobalSignalProcessor(event_bus)
        logger.info("✅ Global Signal Processor initialized")
        
        # 3. Initialize Signal Bridge for V1 ↔ V2 compatibility
        signal_bridge = SignalBridge(event_bus)
        logger.info("✅ Signal Bridge initialized")
        
        # 4. Initialize Enhanced Persistence Service
        persistence_config = PersistenceConfig(
            mode=PersistenceMode.PRODUCTION,
            base_storage_dir=Path.home() / '.tore_matrix_labs_enhanced',
            enable_state_management=True,
            enable_progress_persistence=True, 
            enable_backups=True,
            enable_auto_save=True,
            integrate_with_v1_managers=True
        )
        persistence_service = PersistenceService(persistence_config)
        logger.info("✅ Enhanced Persistence Service initialized")
        
        # 5. Register core V1 components for state management
        persistence_service.register_component(
            "main_window", 
            StateCategory.UI, 
            PersistenceLevel.SESSION
        )
        
        persistence_service.register_component(
            "document_processor",
            StateCategory.PROCESSING,
            PersistenceLevel.PROJECT
        )
        
        persistence_service.register_component(
            "pdf_viewer",
            StateCategory.UI,
            PersistenceLevel.SESSION
        )
        
        persistence_service.register_component(
            "area_storage",
            StateCategory.DOCUMENT, 
            PersistenceLevel.PROJECT
        )
        
        logger.info("✅ Core V1 components registered with enhanced state management")
        
        return {
            'event_bus': event_bus,
            'signal_processor': signal_processor,
            'signal_bridge': signal_bridge,
            'persistence_service': persistence_service
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to setup enhanced systems: {e}")
        logger.info("Running without enhancements...")
        return None


def integrate_with_main_window(main_window, enhanced_systems):
    """Integrate enhanced systems with the V1 main window."""
    if not enhanced_systems:
        return
    
    logger.info("Integrating enhanced systems with V1 main window...")
    
    try:
        event_bus = enhanced_systems['event_bus']
        signal_bridge = enhanced_systems['signal_bridge']
        persistence_service = enhanced_systems['persistence_service']
        
        # Auto-connect V1 widget signals to V2 events
        connected_signals = signal_bridge.auto_connect_widget(main_window)
        logger.info(f"✅ Auto-connected {connected_signals} V1 signals to V2 events")
        
        # Integrate V1 state managers with enhanced persistence
        try:
            # Get V1 state managers if they exist
            document_state_manager = getattr(main_window, 'document_state_manager', None)
            area_storage_manager = getattr(main_window, 'area_storage_manager', None)
            
            if document_state_manager or area_storage_manager:
                persistence_service.integrate_v1_managers(
                    document_manager=document_state_manager,
                    area_manager=area_storage_manager
                )
                logger.info("✅ Integrated with existing V1 state managers")
        except Exception as e:
            logger.warning(f"Could not integrate V1 state managers: {e}")
        
        # Set up enhanced event handling for main window
        if hasattr(main_window, 'setup_enhanced_events'):
            main_window.setup_enhanced_events(enhanced_systems)
            logger.info("✅ Main window enhanced events configured")
        
        # Store enhanced systems in main window for access
        main_window.enhanced_systems = enhanced_systems
        logger.info("✅ Enhanced systems integrated with main window")
        
    except Exception as e:
        logger.error(f"❌ Failed to integrate enhanced systems: {e}")


def setup_enhanced_recovery():
    """Setup recovery from previous sessions if available."""
    logger.info("Checking for recoverable sessions...")
    
    try:
        from enhanced_persistence import ProgressPersistence
        
        progress_persistence = ProgressPersistence()
        recoverable_sessions = progress_persistence.get_recoverable_sessions()
        
        if recoverable_sessions:
            logger.info(f"Found {len(recoverable_sessions)} recoverable sessions")
            
            # For demo purposes, just log the sessions
            # In a real implementation, you'd show a recovery dialog
            for session in recoverable_sessions:
                logger.info(f"  - Session {session.session_id}: {session.project_path}")
                logger.info(f"    Status: {session.status.value}, Progress: {session.calculate_progress():.1f}%")
        else:
            logger.info("No recoverable sessions found")
            
    except Exception as e:
        logger.warning(f"Could not check for recoverable sessions: {e}")


def main():
    """Main launcher function with enhanced V1 integration."""
    logger.info("🚀 Starting Enhanced TORE Matrix Labs V1...")
    logger.info("=" * 60)
    
    # Create QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("TORE Matrix Labs Enhanced V1")
    app.setApplicationVersion("1.0-Enhanced")
    
    # Setup enhanced systems first
    enhanced_systems = setup_enhanced_systems()
    
    # Check for recovery opportunities
    setup_enhanced_recovery()
    
    # Import and create V1 components
    try:
        from tore_matrix_labs.ui.main_window import MainWindow
        from tore_matrix_labs.config.settings import Settings
        
        logger.info("✅ V1 components imported successfully")
        
        # Create V1 application
        settings = Settings()
        main_window = MainWindow(settings)
        
        # Integrate enhanced systems
        integrate_with_main_window(main_window, enhanced_systems)
        
        # Configure window
        main_window.move(100, 100)
        main_window.resize(1400, 900)  # Slightly larger for enhanced features
        main_window.setWindowState(Qt.WindowNoState)
        
        # Show window
        main_window.show()
        main_window.raise_()
        main_window.activateWindow()
        
        logger.info("✅ Enhanced V1 application started successfully!")
        logger.info("=" * 60)
        logger.info("Enhanced Features Available:")
        if enhanced_systems:
            logger.info("  ✅ Unified Event System with V2 patterns")
            logger.info("  ✅ Global Signal Processing and Coordination")
            logger.info("  ✅ Enhanced State Management with Auto-Save")
            logger.info("  ✅ Progress Persistence for Recovery")
            logger.info("  ✅ Automatic Backups and Versioning")
            logger.info("  ✅ V1 ↔ V2 Signal Bridge Compatibility")
        else:
            logger.info("  ⚠️  Running in V1-only mode (enhancements unavailable)")
        logger.info("=" * 60)
        
        # Run application
        exit_code = app.exec_()
        
        # Cleanup enhanced systems
        if enhanced_systems:
            logger.info("Cleaning up enhanced systems...")
            try:
                enhanced_systems['persistence_service'].cleanup()
                enhanced_systems['signal_processor'].shutdown()
                logger.info("✅ Enhanced systems cleanup complete")
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")
        
        logger.info("🏁 Enhanced V1 application shutdown complete")
        return exit_code
        
    except ImportError as e:
        logger.error(f"❌ Failed to import V1 components: {e}")
        logger.error("Please ensure TORE Matrix Labs V1 is properly installed")
        return 1
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())