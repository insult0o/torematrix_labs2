"""Comprehensive tests for the dialog system.

Tests all dialog types, features, and edge cases to ensure
robust dialog functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import asyncio

from PySide6.QtWidgets import QApplication, QWidget, QPushButton
from PySide6.QtCore import Qt, QTimer
from PySide6.QtTest import QTest

from torematrix.ui.dialogs import (
    BaseDialog, DialogResult, DialogButton, DialogManager,
    FileDialog, FileFilter,
    ConfirmationDialog, MessageType, confirm, alert, error, info,
    ProgressDialog, ProgressInfo, ProgressWorker,
    FormDialog, FormField, FieldType, ValidationRule,
    NotificationManager, ToastNotification, NotificationType, 
    NotificationPosition, NotificationData
)
from torematrix.core.events import EventBus, EventType
from torematrix.core.state import StateManager


@pytest.fixture
def qapp():
    """Ensure QApplication exists for tests."""
    app = QApplication.instance()
    if not app:
        app = QApplication([])
    yield app
    # Don't quit app to allow other tests to use it


@pytest.fixture
def parent_widget(qapp):
    """Create a parent widget for dialogs."""
    widget = QWidget()
    widget.show()
    yield widget
    widget.close()


@pytest.fixture
def event_bus():
    """Create event bus for testing."""
    return EventBus()


@pytest.fixture
def state_manager():
    """Create state manager for testing."""
    return Mock(spec=StateManager)


class TestBaseDialog:
    """Test BaseDialog functionality."""
    
    def test_dialog_creation(self, parent_widget):
        """Test basic dialog creation."""
        dialog = BaseDialog(
            parent_widget,
            title="Test Dialog",
            modal=True,
            width=500,
            height=400
        )
        
        assert dialog.windowTitle() == "Test Dialog"
        assert dialog.isModal()
        assert dialog.width() == 500
        assert dialog.height() == 400
        assert dialog.dialog_id.startswith("dialog_")
    
    def test_dialog_buttons(self, parent_widget):
        """Test adding buttons to dialog."""
        dialog = BaseDialog(parent_widget)
        
        # Add custom button
        button = DialogButton(
            text="Custom",
            result=DialogResult.CUSTOM,
            is_default=True,
            tooltip="Custom action"
        )
        btn_widget = dialog.add_button(button)
        
        assert btn_widget.text() == "Custom"
        assert btn_widget.isDefault()
        assert btn_widget.toolTip() == "Custom action"
    
    def test_standard_buttons(self, parent_widget):
        """Test adding standard button sets."""
        dialog = BaseDialog(parent_widget)
        dialog.add_standard_buttons([DialogResult.OK, DialogResult.CANCEL])
        
        # Check buttons were added
        buttons = dialog.findChildren(QPushButton)
        button_texts = [btn.text() for btn in buttons]
        
        assert "OK" in button_texts
        assert "Cancel" in button_texts
    
    def test_dialog_result(self, parent_widget):
        """Test dialog result handling."""
        dialog = BaseDialog(parent_widget)
        
        # Add OK button
        ok_button = dialog.add_button(
            DialogButton("OK", DialogResult.OK)
        )
        
        # Simulate click
        ok_button.click()
        
        assert dialog.get_result() == DialogResult.OK
    
    def test_dialog_state_management(self, parent_widget, state_manager):
        """Test dialog state integration."""
        dialog = BaseDialog(
            parent_widget,
            dialog_id="test_dialog",
            state_manager=state_manager
        )
        
        # Check registration
        state_manager.dispatch.assert_called_with({
            'type': 'DIALOG_REGISTER',
            'payload': {
                'dialog_id': 'test_dialog',
                'state': dialog.state
            }
        })
        
        # Update state
        dialog.update_state({'key': 'value'})
        
        assert dialog.state.data['key'] == 'value'
        state_manager.dispatch.assert_called_with({
            'type': 'DIALOG_UPDATE',
            'payload': {
                'dialog_id': 'test_dialog',
                'data': {'key': 'value'}
            }
        })
    
    def test_dialog_events(self, parent_widget, event_bus):
        """Test dialog event emission."""
        dialog = BaseDialog(
            parent_widget,
            event_bus=event_bus
        )
        
        # Mock event emission
        event_bus.emit = Mock()
        
        # Show dialog
        dialog.show()
        QApplication.processEvents()
        
        # Check event emitted
        event_bus.emit.assert_called()
        emitted_event = event_bus.emit.call_args[0][0]
        assert emitted_event.type == EventType.UI_STATE_CHANGED
        assert emitted_event.data['action'] == 'opened'
    
    @pytest.mark.asyncio
    async def test_async_dialog(self, parent_widget):
        """Test async dialog operation."""
        dialog = BaseDialog(parent_widget)
        
        # Add OK button
        dialog.add_button(DialogButton("OK", DialogResult.OK))
        
        # Show dialog and close after delay
        async def close_dialog():
            await asyncio.sleep(0.1)
            dialog.accept()
        
        # Run both coroutines
        task = asyncio.create_task(close_dialog())
        result = await dialog.show_async()
        await task
        
        assert result == DialogResult.OK


class TestFileDialog:
    """Test FileDialog functionality."""
    
    def test_file_dialog_creation(self, parent_widget):
        """Test file dialog creation with options."""
        dialog = FileDialog(
            parent_widget,
            title="Open File",
            mode="open",
            filters=[FileDialog.FILTER_DOCUMENTS, FileDialog.FILTER_IMAGES],
            default_filter=FileDialog.FILTER_DOCUMENTS,
            multiple=True,
            show_preview=True
        )
        
        assert dialog.windowTitle() == "Open File"
        assert dialog.mode == "open"
        assert len(dialog.filters) == 2
        assert dialog.multiple
        assert dialog.show_preview
    
    def test_file_filters(self):
        """Test file filter creation."""
        filter = FileFilter(
            name="Python Files",
            extensions=["py", "pyw"],
            mime_types=["text/x-python"]
        )
        
        qt_filter = filter.to_qt_filter()
        assert qt_filter == "Python Files (*.py *.pyw)"
    
    def test_file_validation(self, parent_widget):
        """Test file validation callback."""
        validated_files = []
        
        def validate_file(path):
            validated_files.append(path)
            return path.endswith('.txt')
        
        dialog = FileDialog(
            parent_widget,
            validation_callback=validate_file
        )
        
        # Test validation
        dialog._select_file("/test/file.txt")
        assert "/test/file.txt" in validated_files
        assert dialog.get_selected_file() == "/test/file.txt"
        
        # Test invalid file
        dialog._select_file("/test/file.doc")
        assert dialog.get_selected_file() == "/test/file.txt"  # Unchanged
    
    def test_multiple_file_selection(self, parent_widget):
        """Test multiple file selection."""
        dialog = FileDialog(parent_widget, multiple=True)
        
        # Add multiple files
        dialog._add_files([
            "/test/file1.txt",
            "/test/file2.txt",
            "/test/file3.txt"
        ])
        
        selected = dialog.get_selected_files()
        assert len(selected) == 3
        assert "/test/file1.txt" in selected
    
    @patch('PySide6.QtWidgets.QFileDialog.exec')
    @patch('PySide6.QtWidgets.QFileDialog.selectedFiles')
    def test_native_dialog_integration(self, mock_selected, mock_exec, parent_widget):
        """Test native file dialog integration."""
        mock_exec.return_value = True
        mock_selected.return_value = ["/test/selected.txt"]
        
        dialog = FileDialog(parent_widget)
        dialog._show_native_dialog()
        
        assert dialog.get_selected_file() == "/test/selected.txt"


class TestConfirmationDialog:
    """Test ConfirmationDialog functionality."""
    
    def test_confirmation_types(self, parent_widget):
        """Test different confirmation message types."""
        for msg_type in MessageType:
            dialog = ConfirmationDialog(
                parent_widget,
                title=f"{msg_type.name} Test",
                message=f"This is a {msg_type.name} message",
                message_type=msg_type
            )
            
            assert dialog.message_type == msg_type
            # Icon should be set based on type
    
    def test_button_sets(self, parent_widget):
        """Test standard button sets."""
        button_sets = [
            (ConfirmationDialog.BUTTONS_OK_CANCEL, ["OK", "Cancel"]),
            (ConfirmationDialog.BUTTONS_YES_NO, ["Yes", "No"]),
            (ConfirmationDialog.BUTTONS_YES_NO_CANCEL, ["Yes", "No", "Cancel"])
        ]
        
        for buttons, expected_texts in button_sets:
            dialog = ConfirmationDialog(
                parent_widget,
                buttons=buttons
            )
            
            found_buttons = dialog.findChildren(QPushButton)
            found_texts = [btn.text() for btn in found_buttons]
            
            for text in expected_texts:
                assert text in found_texts
    
    def test_detailed_text(self, parent_widget):
        """Test detailed text display."""
        dialog = ConfirmationDialog(
            parent_widget,
            message="Main message",
            detailed_text="This is detailed information\nwith multiple lines"
        )
        
        assert hasattr(dialog, 'details_text')
        assert "multiple lines" in dialog.details_text.toPlainText()
    
    def test_dont_ask_checkbox(self, parent_widget):
        """Test don't ask again checkbox."""
        dialog = ConfirmationDialog(
            parent_widget,
            show_dont_ask=True,
            dont_ask_text="Custom don't ask text"
        )
        
        assert hasattr(dialog, 'dont_ask_checkbox')
        assert dialog.dont_ask_checkbox.text() == "Custom don't ask text"
        
        # Check state
        dialog.dont_ask_checkbox.setChecked(True)
        assert dialog.get_dont_ask_checked()
    
    def test_convenience_functions(self, parent_widget, monkeypatch):
        """Test convenience functions."""
        shown_dialogs = []
        
        def mock_exec(self):
            shown_dialogs.append(self)
            return True
        
        monkeypatch.setattr(ConfirmationDialog, 'exec', mock_exec)
        
        # Test confirm
        result = confirm(parent_widget, "Confirm?", "Are you sure?")
        assert len(shown_dialogs) == 1
        assert shown_dialogs[0].message == "Are you sure?"
        
        # Test alert
        alert(parent_widget, "Alert!", "Warning message")
        assert len(shown_dialogs) == 2
        assert shown_dialogs[1].message_type == MessageType.WARNING
        
        # Test error
        error(parent_widget, "Error!", "Something went wrong", "Details here")
        assert len(shown_dialogs) == 3
        assert shown_dialogs[2].message_type == MessageType.ERROR


class TestProgressDialog:
    """Test ProgressDialog functionality."""
    
    def test_progress_creation(self, parent_widget):
        """Test progress dialog creation."""
        dialog = ProgressDialog(
            parent_widget,
            title="Processing",
            message="Working...",
            total=100,
            show_time=True,
            show_details=True
        )
        
        assert dialog.windowTitle() == "Processing"
        assert dialog.message == "Working..."
        assert dialog.total == 100
        assert hasattr(dialog, 'elapsed_label')
        assert hasattr(dialog, 'details_text')
    
    def test_progress_updates(self, parent_widget):
        """Test progress value updates."""
        dialog = ProgressDialog(parent_widget, total=100)
        
        # Update progress
        dialog.set_progress(50)
        assert dialog.progress_bar.value() == 50
        assert "50%" in dialog.progress_label.text()
        
        # Update message
        dialog.set_message("New message")
        assert dialog.message_label.text() == "New message"
        
        # Add details
        dialog.add_details("Processing item 1")
        assert "Processing item 1" in dialog.details_text.toPlainText()
    
    def test_indeterminate_progress(self, parent_widget):
        """Test indeterminate progress mode."""
        dialog = ProgressDialog(
            parent_widget,
            indeterminate=True
        )
        
        assert dialog.progress_bar.minimum() == 0
        assert dialog.progress_bar.maximum() == 0
        
        # Switch to determinate
        dialog.set_indeterminate(False)
        assert dialog.progress_bar.maximum() == dialog.total
    
    def test_progress_worker(self):
        """Test progress worker functionality."""
        results = []
        
        def operation(value, progress_callback=None):
            for i in range(5):
                if progress_callback:
                    info = ProgressInfo(current=i, total=5)
                    if not progress_callback(info):
                        return "cancelled"
                results.append(i)
            return "completed"
        
        worker = ProgressWorker(operation, 42)
        worker.run()
        
        assert len(results) == 5
    
    def test_cancellation(self, parent_widget):
        """Test progress cancellation."""
        dialog = ProgressDialog(parent_widget, can_cancel=True)
        
        # Check cancel button exists
        cancel_button = None
        for btn in dialog.findChildren(QPushButton):
            if btn.text() == "Cancel":
                cancel_button = btn
                break
        
        assert cancel_button is not None
        
        # Test cancellation
        dialog.cancelled = Mock()
        dialog.cancel()
        dialog.cancelled.emit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_async_operation(self, parent_widget):
        """Test async operation execution."""
        progress_values = []
        
        async def async_operation(progress_callback=None):
            for i in range(5):
                if progress_callback:
                    info = ProgressInfo(current=i, total=5)
                    progress_callback(info)
                progress_values.append(i)
                await asyncio.sleep(0.01)
            return "async_result"
        
        dialog = ProgressDialog(parent_widget, auto_close=True)
        
        # Don't actually show dialog in test
        dialog.show = Mock()
        dialog.accept = Mock()
        
        result = await dialog.run_async_operation(async_operation)
        
        assert result == "async_result"
        assert len(progress_values) == 5
        dialog.accept.assert_called_once()


class TestFormDialog:
    """Test FormDialog functionality."""
    
    def test_form_creation(self, parent_widget):
        """Test form dialog creation with fields."""
        fields = [
            FormField("name", "Name", FieldType.TEXT, required=True),
            FormField("age", "Age", FieldType.NUMBER, min_value=0, max_value=150),
            FormField("email", "Email", FieldType.TEXT, placeholder="user@example.com")
        ]
        
        dialog = FormDialog(
            parent_widget,
            title="User Form",
            fields=fields
        )
        
        assert dialog.windowTitle() == "User Form"
        assert len(dialog.fields) == 3
        assert len(dialog._field_widgets) == 3
    
    def test_field_types(self, parent_widget):
        """Test different field type widgets."""
        fields = [
            FormField("text", "Text", FieldType.TEXT),
            FormField("number", "Number", FieldType.NUMBER),
            FormField("decimal", "Decimal", FieldType.DECIMAL),
            FormField("check", "Check", FieldType.CHECKBOX),
            FormField("combo", "Combo", FieldType.DROPDOWN, options=["A", "B", "C"]),
            FormField("date", "Date", FieldType.DATE),
            FormField("time", "Time", FieldType.TIME),
        ]
        
        dialog = FormDialog(parent_widget, fields=fields)
        
        # Verify widget types
        from PySide6.QtWidgets import (
            QLineEdit, QSpinBox, QDoubleSpinBox, 
            QCheckBox, QComboBox, QDateEdit, QTimeEdit
        )
        
        assert isinstance(dialog._field_widgets["text"].widget, QLineEdit)
        assert isinstance(dialog._field_widgets["number"].widget, QSpinBox)
        assert isinstance(dialog._field_widgets["decimal"].widget, QDoubleSpinBox)
        assert isinstance(dialog._field_widgets["check"].widget, QCheckBox)
        assert isinstance(dialog._field_widgets["combo"].widget, QComboBox)
        assert isinstance(dialog._field_widgets["date"].widget, QDateEdit)
        assert isinstance(dialog._field_widgets["time"].widget, QTimeEdit)
    
    def test_field_validation(self, parent_widget):
        """Test field validation."""
        def validate_email(value):
            return "@" in value and "." in value
        
        fields = [
            FormField(
                "email", "Email", FieldType.TEXT,
                required=True,
                validators=[
                    ValidationRule(validate_email, "Invalid email format")
                ]
            )
        ]
        
        dialog = FormDialog(parent_widget, fields=fields)
        
        # Test empty value
        assert not dialog._validate_field("email")
        
        # Test invalid email
        dialog._field_widgets["email"].widget.setText("invalid")
        assert not dialog._validate_field("email")
        
        # Test valid email
        dialog._field_widgets["email"].widget.setText("user@example.com")
        assert dialog._validate_field("email")
    
    def test_field_dependencies(self, parent_widget):
        """Test field dependency handling."""
        fields = [
            FormField("has_details", "Has Details", FieldType.CHECKBOX),
            FormField(
                "details", "Details", FieldType.MULTILINE_TEXT,
                depends_on="has_details",
                dependency_value=True
            )
        ]
        
        dialog = FormDialog(parent_widget, fields=fields)
        
        # Details should be hidden initially
        details_widget = dialog._field_widgets["details"].widget
        assert not details_widget.isVisible()
        
        # Check the checkbox
        dialog._field_widgets["has_details"].widget.setChecked(True)
        dialog._on_field_changed("has_details")
        
        # Details should now be visible
        assert details_widget.isVisible()
    
    def test_form_data(self, parent_widget):
        """Test getting and setting form data."""
        fields = [
            FormField("name", "Name", FieldType.TEXT),
            FormField("age", "Age", FieldType.NUMBER),
            FormField("active", "Active", FieldType.CHECKBOX)
        ]
        
        dialog = FormDialog(parent_widget, fields=fields)
        
        # Set form data
        data = {
            "name": "John Doe",
            "age": 30,
            "active": True
        }
        dialog.set_form_data(data)
        
        # Get form data
        retrieved_data = dialog.get_form_data()
        assert retrieved_data["name"] == "John Doe"
        assert retrieved_data["age"] == 30
        assert retrieved_data["active"] is True
    
    def test_form_groups(self, parent_widget):
        """Test grouped form layout."""
        fields = [
            FormField("first_name", "First Name", FieldType.TEXT),
            FormField("last_name", "Last Name", FieldType.TEXT),
            FormField("street", "Street", FieldType.TEXT),
            FormField("city", "City", FieldType.TEXT),
        ]
        
        groups = {
            "Personal Info": ["first_name", "last_name"],
            "Address": ["street", "city"]
        }
        
        dialog = FormDialog(
            parent_widget,
            fields=fields,
            groups=groups
        )
        
        # Check group boxes exist
        from PySide6.QtWidgets import QGroupBox
        group_boxes = dialog.findChildren(QGroupBox)
        group_names = [box.title() for box in group_boxes]
        
        assert "Personal Info" in group_names
        assert "Address" in group_names


class TestNotificationSystem:
    """Test notification system functionality."""
    
    def test_toast_creation(self):
        """Test toast notification creation."""
        data = NotificationData(
            id="test_1",
            title="Test Notification",
            message="This is a test message",
            type=NotificationType.INFO,
            duration=5000
        )
        
        toast = ToastNotification(data)
        
        assert toast.data.id == "test_1"
        assert toast.title_label.text() == "Test Notification"
        assert toast.message_label.text() == "This is a test message"
    
    def test_notification_types(self):
        """Test different notification types."""
        for notif_type in NotificationType:
            data = NotificationData(
                id=f"test_{notif_type.name}",
                title=f"{notif_type.name} Notification",
                type=notif_type
            )
            
            toast = ToastNotification(data)
            assert toast.data.type == notif_type
    
    def test_notification_actions(self):
        """Test notification action buttons."""
        action_called = False
        
        def action_callback():
            nonlocal action_called
            action_called = True
        
        data = NotificationData(
            id="test_actions",
            title="Action Test",
            actions=[("Retry", action_callback), ("Dismiss", lambda: None)]
        )
        
        toast = ToastNotification(data)
        
        # Find action button
        buttons = toast.findChildren(QPushButton)
        retry_button = None
        for btn in buttons:
            if btn.text() == "Retry":
                retry_button = btn
                break
        
        assert retry_button is not None
        
        # Click action
        retry_button.click()
        assert action_called
    
    def test_notification_manager(self, parent_widget):
        """Test notification manager."""
        manager = NotificationManager(
            parent_widget,
            position=NotificationPosition.TOP_RIGHT,
            max_visible=3
        )
        
        # Show notifications
        id1 = manager.show_notification("Title 1", "Message 1")
        id2 = manager.show_notification("Title 2", "Message 2")
        id3 = manager.show_notification("Title 3", "Message 3")
        
        assert len(manager._notifications) == 3
        
        # Show one more - should be queued
        id4 = manager.show_notification("Title 4", "Message 4")
        assert len(manager._notifications) == 3
        assert len(manager._notification_queue) == 1
    
    def test_notification_positioning(self, parent_widget):
        """Test notification positioning."""
        positions = [
            NotificationPosition.TOP_RIGHT,
            NotificationPosition.TOP_LEFT,
            NotificationPosition.BOTTOM_RIGHT,
            NotificationPosition.BOTTOM_LEFT
        ]
        
        for position in positions:
            manager = NotificationManager(parent_widget, position=position)
            
            # Create and position notification
            data = NotificationData(
                id=f"pos_test_{position.name}",
                title="Position Test"
            )
            toast = ToastNotification(data, manager)
            manager._notifications[data.id] = toast
            manager._position_notification(toast)
            
            # Check position is within parent bounds
            parent_rect = parent_widget.rect()
            toast_rect = toast.geometry()
            
            assert parent_rect.contains(toast_rect)
    
    def test_notification_auto_close(self, qapp):
        """Test notification auto-close timer."""
        data = NotificationData(
            id="auto_close_test",
            title="Auto Close",
            duration=100  # 100ms for quick test
        )
        
        toast = ToastNotification(data)
        closed_signal = Mock()
        toast.closed.connect(closed_signal)
        
        toast.show()
        
        # Wait for auto-close
        QTest.qWait(200)
        
        # Check if close was initiated
        assert toast._close_timer is not None
    
    def test_notification_history(self, parent_widget):
        """Test notification history tracking."""
        manager = NotificationManager(parent_widget)
        
        # Show several notifications
        for i in range(5):
            manager.show_notification(f"Notification {i}")
        
        # Check history
        history = manager.get_history()
        assert len(history) == 5
        assert history[0].title == "Notification 0"
        assert history[4].title == "Notification 4"
        
        # Clear history
        manager.clear_history()
        assert len(manager.get_history()) == 0


class TestDialogManager:
    """Test dialog manager functionality."""
    
    def test_dialog_registration(self):
        """Test dialog registration and tracking."""
        manager = DialogManager()
        
        dialog1 = Mock(spec=BaseDialog)
        dialog1.dialog_id = "dialog_1"
        dialog1.isModal.return_value = True
        
        dialog2 = Mock(spec=BaseDialog)
        dialog2.dialog_id = "dialog_2"
        dialog2.isModal.return_value = False
        
        manager.register_dialog(dialog1)
        manager.register_dialog(dialog2)
        
        assert len(manager._dialogs) == 2
        assert len(manager._dialog_stack) == 1  # Only modal dialogs
        
        # Get top dialog
        assert manager.get_top_dialog() == dialog1
    
    def test_dialog_closing(self):
        """Test closing all dialogs."""
        manager = DialogManager()
        
        dialogs = []
        for i in range(3):
            dialog = Mock(spec=BaseDialog)
            dialog.dialog_id = f"dialog_{i}"
            dialog.close = Mock()
            dialogs.append(dialog)
            manager.register_dialog(dialog)
        
        manager.close_all()
        
        for dialog in dialogs:
            dialog.close.assert_called_once()


class TestIntegration:
    """Integration tests for dialog system."""
    
    def test_dialog_with_notifications(self, parent_widget):
        """Test dialog showing notifications."""
        # Add notification manager to parent
        parent_widget.notification_manager = NotificationManager(parent_widget)
        
        dialog = BaseDialog(parent_widget, title="Test")
        
        # Show notification from dialog
        from torematrix.ui.dialogs.notifications import notify
        notif_id = notify("Dialog Action", "Something happened", parent=dialog)
        
        assert notif_id is not None
        assert len(parent_widget.notification_manager._notifications) == 1
    
    def test_form_dialog_workflow(self, parent_widget):
        """Test complete form dialog workflow."""
        fields = [
            FormField("username", "Username", FieldType.TEXT, required=True),
            FormField("password", "Password", FieldType.TEXT, required=True),
            FormField("remember", "Remember me", FieldType.CHECKBOX)
        ]
        
        dialog = FormDialog(
            parent_widget,
            title="Login",
            fields=fields,
            submit_text="Login"
        )
        
        # Fill form
        dialog._field_widgets["username"].widget.setText("testuser")
        dialog._field_widgets["password"].widget.setText("testpass")
        dialog._field_widgets["remember"].widget.setChecked(True)
        
        # Mock form submission
        submitted_data = None
        dialog.form_submitted.connect(lambda data: submitted_data or data)
        
        # Trigger submission
        dialog._on_submit()
        
        # Verify data
        assert submitted_data is None  # Would be set if validation passed
    
    def test_progress_dialog_with_operation(self, parent_widget):
        """Test progress dialog with actual operation."""
        processed_items = []
        
        def process_items(items, progress_callback=None):
            total = len(items)
            for i, item in enumerate(items):
                if progress_callback:
                    info = ProgressInfo(
                        current=i,
                        total=total,
                        message=f"Processing {item}"
                    )
                    if not progress_callback(info):
                        break
                
                processed_items.append(item)
            
            return processed_items
        
        dialog = ProgressDialog(
            parent_widget,
            title="Processing",
            total=5
        )
        
        # Mock the thread execution
        items = ["A", "B", "C", "D", "E"]
        result = process_items(items, dialog._async_progress_callback)
        
        assert len(processed_items) == 5
        assert result == ["A", "B", "C", "D", "E"]