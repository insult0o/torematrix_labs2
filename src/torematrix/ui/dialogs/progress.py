"""Progress dialog implementation.

Provides progress indication dialogs with cancellation support,
time estimation, and detailed progress information.
"""

from typing import Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio
import logging
from concurrent.futures import Future

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QPushButton, QTextEdit, QGroupBox, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal as Signal, QTimer, QThread, QObject
from PyQt6.QtGui import QCloseEvent

from .base import BaseDialog, DialogResult, DialogButton

logger = logging.getLogger(__name__)


@dataclass
class ProgressInfo:
    """Progress information container."""
    current: int = 0
    total: int = 100
    message: str = ""
    details: str = ""
    started_at: datetime = field(default_factory=datetime.now)
    elapsed: timedelta = field(default_factory=timedelta)
    estimated_remaining: Optional[timedelta] = None
    is_indeterminate: bool = False
    can_cancel: bool = True
    is_cancelled: bool = False


class ProgressWorker(QObject):
    """Worker for executing progress operations in separate thread."""
    
    # Signals
    progress_updated = Signal(ProgressInfo)
    message_updated = Signal(str)
    details_updated = Signal(str)
    finished = Signal(object)  # result
    error = Signal(Exception)
    
    def __init__(self, operation: Callable, *args, **kwargs):
        """Initialize progress worker.
        
        Args:
            operation: Callable to execute
            *args: Positional arguments for operation
            **kwargs: Keyword arguments for operation
        """
        super().__init__()
        self.operation = operation
        self.args = args
        self.kwargs = kwargs
        self._cancelled = False
    
    def run(self) -> None:
        """Execute the operation."""
        try:
            # Inject progress callback if operation supports it
            if 'progress_callback' in self.kwargs:
                self.kwargs['progress_callback'] = self._on_progress
            
            result = self.operation(*self.args, **self.kwargs)
            
            if not self._cancelled:
                self.finished.emit(result)
                
        except Exception as e:
            logger.error(f"Progress operation error: {e}")
            self.error.emit(e)
    
    def cancel(self) -> None:
        """Request cancellation."""
        self._cancelled = True
    
    def _on_progress(self, info: ProgressInfo) -> bool:
        """Handle progress update from operation.
        
        Args:
            info: Progress information
            
        Returns:
            False if cancelled, True to continue
        """
        if self._cancelled:
            info.is_cancelled = True
            return False
        
        self.progress_updated.emit(info)
        return True


class ProgressDialog(BaseDialog):
    """Progress indication dialog with cancellation.
    
    Features:
    - Determinate and indeterminate progress
    - Time estimation
    - Cancellation support
    - Detailed progress messages
    - Async operation support
    - Auto-close option
    """
    
    # Signals
    cancelled = Signal()
    progress_updated = Signal(ProgressInfo)
    
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        title: str = "Progress",
        message: str = "Processing...",
        total: int = 100,
        can_cancel: bool = True,
        auto_close: bool = True,
        show_time: bool = True,
        show_details: bool = False,
        indeterminate: bool = False,
        **kwargs
    ):
        """Initialize progress dialog.
        
        Args:
            parent: Parent widget
            title: Dialog title
            message: Initial progress message
            total: Total progress value
            can_cancel: Allow cancellation
            auto_close: Close when complete
            show_time: Show time information
            show_details: Show details area
            indeterminate: Use indeterminate progress
            **kwargs: Additional BaseDialog arguments
        """
        super().__init__(parent, title, modal=True, **kwargs)
        
        self.message = message
        self.total = total
        self.can_cancel = can_cancel
        self.auto_close = auto_close
        self.show_time = show_time
        self.show_details = show_details
        self.indeterminate = indeterminate
        
        self._progress_info = ProgressInfo(
            total=total,
            message=message,
            is_indeterminate=indeterminate,
            can_cancel=can_cancel
        )
        
        self._worker: Optional[ProgressWorker] = None
        self._thread: Optional[QThread] = None
        self._update_timer: Optional[QTimer] = None
        self._future: Optional[Future] = None
        
        self._setup_progress_ui()
        self._start_update_timer()
    
    def _setup_progress_ui(self) -> None:
        """Setup the progress dialog UI."""
        # Message label
        self.message_label = QLabel(self.message)
        self.message_label.setWordWrap(True)
        self.content_layout.addWidget(self.message_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        if self.indeterminate:
            self.progress_bar.setRange(0, 0)
        else:
            self.progress_bar.setRange(0, self.total)
            self.progress_bar.setValue(0)
        self.content_layout.addWidget(self.progress_bar)
        
        # Progress text
        progress_layout = QHBoxLayout()
        self.progress_label = QLabel("0%")
        self.items_label = QLabel(f"0 / {self.total}")
        progress_layout.addWidget(self.progress_label)
        progress_layout.addStretch()
        progress_layout.addWidget(self.items_label)
        self.content_layout.addLayout(progress_layout)
        
        # Time information
        if self.show_time:
            time_group = QGroupBox("Time")
            time_layout = QHBoxLayout(time_group)
            
            self.elapsed_label = QLabel("Elapsed: 00:00:00")
            self.remaining_label = QLabel("Remaining: --:--:--")
            
            time_layout.addWidget(self.elapsed_label)
            time_layout.addStretch()
            time_layout.addWidget(self.remaining_label)
            
            self.content_layout.addWidget(time_group)
        
        # Details area
        if self.show_details:
            details_group = QGroupBox("Details")
            details_layout = QVBoxLayout(details_group)
            
            self.details_text = QTextEdit()
            self.details_text.setReadOnly(True)
            self.details_text.setMaximumHeight(150)
            details_layout.addWidget(self.details_text)
            
            self.content_layout.addWidget(details_group)
        
        # Add spacing
        self.content_layout.addStretch()
        
        # Buttons
        if self.can_cancel:
            self.cancel_button = self.add_button(
                DialogButton("Cancel", DialogResult.CANCEL)
            )
        else:
            # Disable close button
            self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)
    
    def _start_update_timer(self) -> None:
        """Start timer for updating time display."""
        if self.show_time:
            self._update_timer = QTimer()
            self._update_timer.timeout.connect(self._update_time_display)
            self._update_timer.start(1000)  # Update every second
    
    def _update_time_display(self) -> None:
        """Update elapsed and remaining time display."""
        if not self._progress_info:
            return
        
        # Calculate elapsed time
        self._progress_info.elapsed = datetime.now() - self._progress_info.started_at
        elapsed_str = str(self._progress_info.elapsed).split('.')[0]
        self.elapsed_label.setText(f"Elapsed: {elapsed_str}")
        
        # Estimate remaining time
        if (not self._progress_info.is_indeterminate and 
            self._progress_info.current > 0):
            
            progress_ratio = self._progress_info.current / self._progress_info.total
            if progress_ratio > 0:
                total_estimated = self._progress_info.elapsed / progress_ratio
                remaining = total_estimated - self._progress_info.elapsed
                self._progress_info.estimated_remaining = remaining
                
                remaining_str = str(remaining).split('.')[0]
                self.remaining_label.setText(f"Remaining: {remaining_str}")
    
    def set_progress(self, value: int) -> None:
        """Set progress value.
        
        Args:
            value: Progress value
        """
        self._progress_info.current = value
        
        if not self.indeterminate:
            self.progress_bar.setValue(value)
            
            # Update percentage
            percentage = int((value / self.total) * 100)
            self.progress_label.setText(f"{percentage}%")
            self.items_label.setText(f"{value} / {self.total}")
        
        self.progress_updated.emit(self._progress_info)
        
        # Auto-close if complete
        if self.auto_close and value >= self.total:
            QTimer.singleShot(500, self.accept)  # Close after delay
    
    def set_message(self, message: str) -> None:
        """Update progress message.
        
        Args:
            message: New message
        """
        self._progress_info.message = message
        self.message_label.setText(message)
    
    def add_details(self, text: str) -> None:
        """Add text to details area.
        
        Args:
            text: Text to add
        """
        if hasattr(self, 'details_text'):
            self._progress_info.details += text + "\n"
            self.details_text.append(text)
    
    def set_indeterminate(self, indeterminate: bool) -> None:
        """Set indeterminate mode.
        
        Args:
            indeterminate: Whether to use indeterminate progress
        """
        self.indeterminate = indeterminate
        self._progress_info.is_indeterminate = indeterminate
        
        if indeterminate:
            self.progress_bar.setRange(0, 0)
        else:
            self.progress_bar.setRange(0, self.total)
    
    def run_operation(
        self,
        operation: Callable[..., Any],
        *args,
        **kwargs
    ) -> None:
        """Run operation with progress tracking.
        
        Args:
            operation: Operation to run
            *args: Positional arguments
            **kwargs: Keyword arguments
        """
        # Create worker and thread
        self._worker = ProgressWorker(operation, *args, **kwargs)
        self._thread = QThread()
        
        # Move worker to thread
        self._worker.moveToThread(self._thread)
        
        # Connect signals
        self._thread.started.connect(self._worker.run)
        self._worker.progress_updated.connect(self._on_progress_update)
        self._worker.message_updated.connect(self.set_message)
        self._worker.details_updated.connect(self.add_details)
        self._worker.finished.connect(self._on_operation_finished)
        self._worker.error.connect(self._on_operation_error)
        self._thread.finished.connect(self._thread.deleteLater)
        
        # Start operation
        self._thread.start()
    
    async def run_async_operation(
        self,
        operation: Callable[..., Any],
        *args,
        **kwargs
    ) -> Any:
        """Run async operation with progress tracking.
        
        Args:
            operation: Async operation to run
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Operation result
        """
        # Show dialog
        self.show()
        
        try:
            # Inject progress callback
            if 'progress_callback' in kwargs:
                kwargs['progress_callback'] = self._async_progress_callback
            
            # Run operation
            result = await operation(*args, **kwargs)
            
            # Close dialog
            if self.auto_close:
                self.accept()
            
            return result
            
        except asyncio.CancelledError:
            self._progress_info.is_cancelled = True
            self.reject()
            raise
        except Exception as e:
            logger.error(f"Async operation error: {e}")
            self.reject()
            raise
    
    def _async_progress_callback(self, info: ProgressInfo) -> bool:
        """Async progress callback.
        
        Args:
            info: Progress information
            
        Returns:
            False if cancelled, True to continue
        """
        if self._progress_info.is_cancelled:
            return False
        
        # Update UI
        self.set_progress(info.current)
        self.set_message(info.message)
        
        if info.details:
            self.add_details(info.details)
        
        return True
    
    def _on_progress_update(self, info: ProgressInfo) -> None:
        """Handle progress update from worker.
        
        Args:
            info: Progress information
        """
        self._progress_info = info
        self.set_progress(info.current)
    
    def _on_operation_finished(self, result: Any) -> None:
        """Handle operation completion.
        
        Args:
            result: Operation result
        """
        if self._thread:
            self._thread.quit()
            self._thread.wait()
        
        self._result = DialogResult.OK
        
        if self.auto_close:
            self.accept()
    
    def _on_operation_error(self, error: Exception) -> None:
        """Handle operation error.
        
        Args:
            error: Exception that occurred
        """
        if self._thread:
            self._thread.quit()
            self._thread.wait()
        
        # Show error in details
        if hasattr(self, 'details_text'):
            self.add_details(f"ERROR: {str(error)}")
        
        # Update UI
        self.set_message("Operation failed")
        if hasattr(self, 'cancel_button'):
            self.cancel_button.setText("Close")
    
    def cancel(self) -> None:
        """Cancel the operation."""
        self._progress_info.is_cancelled = True
        
        if self._worker:
            self._worker.cancel()
        
        self.cancelled.emit()
        self.reject()
    
    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle close event.
        
        Args:
            event: Close event
        """
        if self.can_cancel:
            self.cancel()
        else:
            event.ignore()  # Prevent closing if can't cancel
    
    def keyPressEvent(self, event) -> None:
        """Handle key press events.
        
        Args:
            event: Key event
        """
        # Disable ESC if can't cancel
        if event.key() == Qt.Key.Key_Escape and not self.can_cancel:
            event.ignore()
        else:
            super().keyPressEvent(event)


def show_progress(
    parent: Optional[QWidget] = None,
    title: str = "Progress",
    message: str = "Processing...",
    operation: Optional[Callable] = None,
    **kwargs
) -> Optional[Any]:
    """Show progress dialog for an operation.
    
    Args:
        parent: Parent widget
        title: Dialog title
        message: Progress message
        operation: Operation to run
        **kwargs: Additional dialog arguments
        
    Returns:
        Operation result if successful, None if cancelled
    """
    dialog = ProgressDialog(parent, title, message, **kwargs)
    
    if operation:
        dialog.run_operation(operation)
    
    if dialog.exec() == BaseDialog.DialogCode.Accepted:
        return dialog.get_state().data.get('result')
    
    return None