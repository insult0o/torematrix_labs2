#!/usr/bin/env python3
"""Demo script for MainWindow implementation.

This demonstrates the core foundation of the ToreMatrix V3 UI framework,
showing how Agent 1's MainWindow provides the base structure for the
entire application.
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from PyQt6.QtWidgets import QLabel, QWidget, QVBoxLayout, QPushButton
from PyQt6.QtCore import Qt

from torematrix.ui.main_window import MainWindow, create_application
from torematrix.core.events import EventBus
from torematrix.core.config import ConfigManager
from torematrix.core.state import StateManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_demo_content() -> QWidget:
    """Create a demo content widget."""
    widget = QWidget()
    layout = QVBoxLayout(widget)
    
    # Title
    title = QLabel("ToreMatrix V3 - UI Framework Demo")
    title.setAlignment(Qt.AlignmentFlag.AlignCenter)
    title.setStyleSheet("""
        QLabel {
            font-size: 24px;
            font-weight: bold;
            color: #2c3e50;
            padding: 20px;
        }
    """)
    layout.addWidget(title)
    
    # Description
    description = QLabel(
        "This is the core MainWindow implementation by Agent 1.\n\n"
        "Features demonstrated:\n"
        "• Cross-platform window management\n"
        "• Event bus integration\n"
        "• State persistence\n"
        "• Container structure for UI components\n"
        "• High DPI support\n\n"
        "Agents 2, 3, and 4 will build upon this foundation."
    )
    description.setAlignment(Qt.AlignmentFlag.AlignCenter)
    description.setStyleSheet("""
        QLabel {
            font-size: 14px;
            color: #34495e;
            padding: 10px;
            line-height: 1.5;
        }
    """)
    layout.addWidget(description)
    
    # Test button
    test_button = QPushButton("Test Event System")
    test_button.setStyleSheet("""
        QPushButton {
            font-size: 16px;
            padding: 10px 20px;
            background-color: #3498db;
            color: white;
            border: none;
            border-radius: 5px;
        }
        QPushButton:hover {
            background-color: #2980b9;
        }
    """)
    layout.addWidget(test_button, alignment=Qt.AlignmentFlag.AlignCenter)
    
    # Add stretch
    layout.addStretch()
    
    return widget


def main():
    """Run the demo application."""
    # Create application
    app = create_application()
    
    # Initialize dependencies
    logger.info("Initializing dependencies...")
    event_bus = EventBus()
    config_manager = ConfigManager()
    state_manager = StateManager()
    
    # Create main window
    logger.info("Creating main window...")
    window = MainWindow(
        event_bus=event_bus,
        config_manager=config_manager,
        state_manager=state_manager
    )
    
    # Add demo content
    demo_content = create_demo_content()
    window.set_central_content(demo_content)
    
    # Set up event handlers
    def on_test_button():
        window.show_status_message("Event system working! ✨", 3000)
        event_bus.publish("demo.test", {"message": "Hello from demo!"})
    
    test_button = demo_content.findChild(QPushButton)
    if test_button:
        test_button.clicked.connect(on_test_button)
    
    # Subscribe to demo event
    def handle_demo_event(event_data):
        logger.info(f"Received demo event: {event_data}")
    
    event_bus.subscribe("demo.test", handle_demo_event)
    
    # Add menu placeholder
    menubar = window.get_menubar_container()
    file_menu = menubar.addMenu("&File")
    file_menu.addAction("&New Project", lambda: window.show_status_message("New Project (Agent 2 will implement)", 3000))
    file_menu.addAction("&Open Project", lambda: window.show_status_message("Open Project (Agent 2 will implement)", 3000))
    file_menu.addSeparator()
    file_menu.addAction("&Exit", window.close_application)
    
    # Add toolbar placeholder
    toolbar = window.get_toolbar_container()
    toolbar.addAction("🆕", lambda: window.show_status_message("New (Agent 2 will implement)", 3000))
    toolbar.addAction("📂", lambda: window.show_status_message("Open (Agent 2 will implement)", 3000))
    toolbar.addAction("💾", lambda: window.show_status_message("Save (Agent 2 will implement)", 3000))
    
    # Show window
    logger.info("Showing application window...")
    window.show_application()
    
    # Log window state
    state = window.get_window_state()
    logger.info(f"Window state: {state}")
    
    # Run application
    logger.info("Starting event loop...")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()