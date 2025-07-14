"""Advanced splash screen system for ToreMatrix V3.

This module provides a sophisticated splash screen with progress tracking,
animations, and branding for application startup.
"""

from typing import Optional, List, Callable, Dict, Any
from pathlib import Path
import logging
import time

from PyQt6.QtWidgets import (
    QSplashScreen, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QProgressBar, QApplication, QFrame
)
from PyQt6.QtCore import (
    Qt, QTimer, pyqtSignal, QObject, QPropertyAnimation,
    QEasingCurve, QRect, QSize, QThread, QMutex
)
from PyQt6.QtGui import (
    QPixmap, QPainter, QFont, QColor, QLinearGradient,
    QBrush, QPen, QFontMetrics
)

logger = logging.getLogger(__name__)


class SplashScreen(QSplashScreen):
    """Advanced splash screen with progress tracking and animations."""
    
    # Signals
    progress_changed = pyqtSignal(int, str)  # progress, message
    splash_finished = pyqtSignal()
    
    def __init__(
        self,
        pixmap: Optional[QPixmap] = None,
        flags: Qt.WindowType = Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.SplashScreen
    ):
        if pixmap is None:
            pixmap = self._create_default_pixmap()
        
        super().__init__(pixmap, flags)
        
        # Progress tracking
        self.current_progress = 0
        self.max_progress = 100
        self.current_message = "Loading..."
        
        # UI customization
        self.progress_bar_rect = QRect(50, pixmap.height() - 80, pixmap.width() - 100, 20)
        self.message_rect = QRect(50, pixmap.height() - 50, pixmap.width() - 100, 30)
        
        # Fonts
        self.title_font = QFont("Arial", 24, QFont.Weight.Bold)
        self.message_font = QFont("Arial", 10)
        self.version_font = QFont("Arial", 8)
        
        # Colors
        self.bg_color = QColor(45, 45, 45)
        self.accent_color = QColor(14, 99, 156)
        self.text_color = QColor(255, 255, 255)
        self.progress_bg_color = QColor(60, 60, 60)
        
        # Animation
        self.opacity_animation = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_animation.setDuration(500)
        self.opacity_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        # Auto-hide timer
        self.auto_hide_timer = QTimer()
        self.auto_hide_timer.setSingleShot(True)
        self.auto_hide_timer.timeout.connect(self.finish_with_animation)
        
        logger.debug("SplashScreen initialized")
    
    def _create_default_pixmap(self) -> QPixmap:
        """Create default splash screen pixmap."""
        width, height = 600, 400
        pixmap = QPixmap(width, height)
        pixmap.fill(self.bg_color)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Background gradient
        gradient = QLinearGradient(0, 0, 0, height)
        gradient.setColorAt(0, QColor(45, 45, 45))
        gradient.setColorAt(1, QColor(30, 30, 30))
        painter.fillRect(pixmap.rect(), QBrush(gradient))
        
        # Title
        painter.setFont(self.title_font)
        painter.setPen(self.text_color)
        title_rect = QRect(50, 100, width - 100, 60)
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignCenter, "ToreMatrix V3")
        
        # Subtitle
        painter.setFont(QFont("Arial", 14))
        painter.setPen(QColor(200, 200, 200))
        subtitle_rect = QRect(50, 160, width - 100, 30)
        painter.drawText(subtitle_rect, Qt.AlignmentFlag.AlignCenter, "Document Processing Platform")
        
        # Version
        painter.setFont(self.version_font)
        painter.setPen(QColor(150, 150, 150))
        version_rect = QRect(width - 150, height - 30, 140, 20)
        painter.drawText(version_rect, Qt.AlignmentFlag.AlignRight, "Version 3.0.0")
        
        # Logo placeholder (if needed)
        logo_rect = QRect(250, 50, 100, 40)
        painter.setPen(QPen(self.accent_color, 2))
        painter.drawRect(logo_rect)
        painter.drawText(logo_rect, Qt.AlignmentFlag.AlignCenter, "LOGO")
        
        painter.end()
        return pixmap
    
    def set_progress(self, progress: int, message: str = "") -> None:
        """Set progress value and message."""
        self.current_progress = max(0, min(progress, self.max_progress))
        if message:
            self.current_message = message
        
        self.progress_changed.emit(self.current_progress, self.current_message)
        self.repaint()
        
        # Process events to keep UI responsive
        QApplication.processEvents()
    
    def increment_progress(self, increment: int = 1, message: str = "") -> None:
        """Increment progress by given amount."""
        self.set_progress(self.current_progress + increment, message)
    
    def set_max_progress(self, max_progress: int) -> None:
        """Set maximum progress value."""
        self.max_progress = max(1, max_progress)
    
    def show_message(self, message: str, alignment: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter, color: QColor = QColor(255, 255, 255)) -> None:
        """Show message on splash screen."""
        self.current_message = message
        self.repaint()
        QApplication.processEvents()
    
    def show_with_animation(self) -> None:
        """Show splash screen with fade-in animation."""
        self.setWindowOpacity(0.0)
        self.show()
        
        self.opacity_animation.setStartValue(0.0)
        self.opacity_animation.setEndValue(1.0)
        self.opacity_animation.start()
    
    def finish_with_animation(self) -> None:
        """Finish splash screen with fade-out animation."""
        self.opacity_animation.finished.connect(self._on_fade_out_finished)
        self.opacity_animation.setStartValue(1.0)
        self.opacity_animation.setEndValue(0.0)
        self.opacity_animation.start()
    
    def _on_fade_out_finished(self) -> None:
        """Handle fade-out animation finished."""
        self.splash_finished.emit()
        self.close()
    
    def auto_finish(self, delay_ms: int = 2000) -> None:
        """Automatically finish splash screen after delay."""
        self.auto_hide_timer.start(delay_ms)
    
    def drawContents(self, painter: QPainter) -> None:
        """Draw custom content on splash screen."""
        super().drawContents(painter)
        
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw progress bar background
        painter.setBrush(QBrush(self.progress_bg_color))
        painter.setPen(QPen(QColor(80, 80, 80), 1))
        painter.drawRoundedRect(self.progress_bar_rect, 5, 5)
        
        # Draw progress bar fill
        if self.current_progress > 0:
            progress_width = int((self.current_progress / self.max_progress) * self.progress_bar_rect.width())
            progress_rect = QRect(
                self.progress_bar_rect.x(),
                self.progress_bar_rect.y(),
                progress_width,
                self.progress_bar_rect.height()
            )
            
            # Gradient for progress bar
            gradient = QLinearGradient(progress_rect.topLeft(), progress_rect.bottomLeft())
            gradient.setColorAt(0, self.accent_color.lighter(120))
            gradient.setColorAt(1, self.accent_color)
            
            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(progress_rect, 5, 5)
        
        # Draw progress percentage
        painter.setFont(QFont("Arial", 8))
        painter.setPen(self.text_color)
        percentage_text = f"{self.current_progress}%"
        painter.drawText(
            self.progress_bar_rect,
            Qt.AlignmentFlag.AlignCenter,
            percentage_text
        )
        
        # Draw status message
        painter.setFont(self.message_font)
        painter.setPen(self.text_color)
        painter.drawText(
            self.message_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self.current_message
        )


class LoadingTask:
    """Represents a loading task for the splash screen."""
    
    def __init__(
        self,
        name: str,
        description: str,
        weight: int = 1,
        task_func: Optional[Callable[[], None]] = None
    ):
        self.name = name
        self.description = description
        self.weight = weight
        self.task_func = task_func
        self.completed = False
        self.error: Optional[Exception] = None


class SplashManager(QObject):
    """Manager for splash screen with task progression."""
    
    # Signals
    task_started = pyqtSignal(str)  # task_name
    task_completed = pyqtSignal(str, bool)  # task_name, success
    all_tasks_completed = pyqtSignal(bool)  # success
    
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.splash: Optional[SplashScreen] = None
        self.tasks: List[LoadingTask] = []
        self.current_task_index = 0
        self.total_weight = 0
        self.completed_weight = 0
        
        # Task execution
        self.task_timer = QTimer()
        self.task_timer.setSingleShot(True)
        self.task_timer.timeout.connect(self._execute_next_task)
        
        logger.debug("SplashManager initialized")
    
    def create_splash(self, pixmap: Optional[QPixmap] = None) -> SplashScreen:
        """Create and return splash screen."""
        self.splash = SplashScreen(pixmap)
        self.splash.splash_finished.connect(self._on_splash_finished)
        return self.splash
    
    def add_task(
        self,
        name: str,
        description: str,
        weight: int = 1,
        task_func: Optional[Callable[[], None]] = None
    ) -> None:
        """Add a loading task."""
        task = LoadingTask(name, description, weight, task_func)
        self.tasks.append(task)
        self.total_weight += weight
        logger.debug(f"Added task: {name} (weight: {weight})")
    
    def start_loading(self, delay_between_tasks: int = 100) -> None:
        """Start the loading process."""
        if not self.splash:
            self.create_splash()
        
        if not self.tasks:
            logger.warning("No tasks to execute")
            return
        
        self.current_task_index = 0
        self.completed_weight = 0
        
        # Reset task states
        for task in self.tasks:
            task.completed = False
            task.error = None
        
        # Show splash screen
        self.splash.show_with_animation()
        self.splash.set_max_progress(100)
        self.splash.set_progress(0, "Initializing...")
        
        # Start task execution
        self.task_timer.setInterval(delay_between_tasks)
        self._execute_next_task()
    
    def _execute_next_task(self) -> None:
        """Execute the next task in the queue."""
        if self.current_task_index >= len(self.tasks):
            # All tasks completed
            self._on_all_tasks_completed()
            return
        
        task = self.tasks[self.current_task_index]
        
        try:
            # Update splash screen
            progress = int((self.completed_weight / self.total_weight) * 100)
            self.splash.set_progress(progress, f"Loading {task.description}...")
            
            self.task_started.emit(task.name)
            logger.debug(f"Executing task: {task.name}")
            
            # Execute task function
            if task.task_func:
                task.task_func()
            else:
                # Simulate task execution
                time.sleep(0.1)
            
            # Mark task as completed
            task.completed = True
            self.completed_weight += task.weight
            
            self.task_completed.emit(task.name, True)
            logger.debug(f"Completed task: {task.name}")
            
        except Exception as e:
            task.error = e
            self.task_completed.emit(task.name, False)
            logger.error(f"Task failed: {task.name} - {e}")
        
        # Move to next task
        self.current_task_index += 1
        
        # Schedule next task execution
        if self.current_task_index < len(self.tasks):
            self.task_timer.start()
        else:
            self._on_all_tasks_completed()
    
    def _on_all_tasks_completed(self) -> None:
        """Handle completion of all tasks."""
        # Check if any tasks failed
        failed_tasks = [task for task in self.tasks if task.error is not None]
        success = len(failed_tasks) == 0
        
        # Update splash screen to 100%
        if self.splash:
            self.splash.set_progress(100, "Ready!" if success else "Completed with errors")
        
        self.all_tasks_completed.emit(success)
        
        if success:
            logger.info("All loading tasks completed successfully")
        else:
            logger.warning(f"{len(failed_tasks)} tasks failed during loading")
        
        # Auto-finish splash screen
        if self.splash:
            self.splash.auto_finish(1500)  # 1.5 seconds delay
    
    def _on_splash_finished(self) -> None:
        """Handle splash screen finished."""
        logger.debug("Splash screen finished")
    
    def get_task_status(self) -> Dict[str, Any]:
        """Get current task execution status."""
        return {
            'total_tasks': len(self.tasks),
            'completed_tasks': len([t for t in self.tasks if t.completed]),
            'failed_tasks': len([t for t in self.tasks if t.error is not None]),
            'current_task': self.current_task_index,
            'progress_percentage': int((self.completed_weight / self.total_weight) * 100) if self.total_weight > 0 else 0
        }
    
    def add_standard_tasks(self) -> None:
        """Add standard application loading tasks."""
        standard_tasks = [
            ("init_config", "Configuration system", 2),
            ("init_events", "Event bus", 1),
            ("init_state", "State management", 2),
            ("init_storage", "Storage backend", 3),
            ("init_ui", "User interface", 4),
            ("init_themes", "Theme system", 2),
            ("init_panels", "Panel system", 2),
            ("init_plugins", "Plugin system", 3),
            ("final_setup", "Final setup", 1)
        ]
        
        for name, description, weight in standard_tasks:
            self.add_task(name, description, weight)


# Convenience functions
def create_splash_screen(pixmap_path: Optional[str] = None) -> SplashScreen:
    """Create a splash screen with optional custom pixmap."""
    pixmap = None
    if pixmap_path and Path(pixmap_path).exists():
        pixmap = QPixmap(pixmap_path)
    
    return SplashScreen(pixmap)


def show_splash_with_tasks(tasks: List[tuple], pixmap_path: Optional[str] = None) -> SplashManager:
    """Show splash screen and execute tasks.
    
    Args:
        tasks: List of (name, description, weight, func) tuples
        pixmap_path: Optional path to custom splash image
    
    Returns:
        SplashManager instance
    """
    manager = SplashManager()
    manager.create_splash(QPixmap(pixmap_path) if pixmap_path else None)
    
    for task_data in tasks:
        if len(task_data) >= 3:
            name, description, weight = task_data[:3]
            task_func = task_data[3] if len(task_data) > 3 else None
            manager.add_task(name, description, weight, task_func)
    
    manager.start_loading()
    return manager