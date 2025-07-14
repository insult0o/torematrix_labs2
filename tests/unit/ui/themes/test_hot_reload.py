"""Tests for theme hot reload system."""

import pytest
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from src.torematrix.ui.themes.hot_reload import (
    ThemeFileWatcher, HotReloadManager, HotReloadEngine,
    ReloadEvent, ReloadTrigger
)
from src.torematrix.ui.themes.engine import ThemeEngine
from src.torematrix.core.config import ConfigManager
from src.torematrix.core.events import EventBus


class TestThemeFileWatcher:
    """Test ThemeFileWatcher class."""
    
    @pytest.fixture
    def app(self):
        """Create QApplication for testing."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app
    
    @pytest.fixture
    def watcher(self, app):
        """Create ThemeFileWatcher instance."""
        return ThemeFileWatcher()
    
    def test_watcher_initialization(self, watcher):
        """Test watcher initialization."""
        assert watcher.watcher is not None
        assert len(watcher.watched_files) == 0
        assert len(watcher.watched_directories) == 0
        assert watcher.debounce_delay == 500
        assert len(watcher.pending_changes) == 0
    
    def test_watch_existing_file(self, watcher):
        """Test watching an existing file."""
        with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False) as tmp:
            tmp_path = Path(tmp.name)
            
            try:
                # Watch the file
                success = watcher.watch_file(tmp_path)
                assert success is True
                assert str(tmp_path.resolve()) in watcher.watched_files
                
                # Try to watch same file again
                success = watcher.watch_file(tmp_path)
                assert success is True  # Should still succeed
                
                # Unwatch the file
                watcher.unwatch_file(tmp_path)
                assert str(tmp_path.resolve()) not in watcher.watched_files
                
            finally:
                tmp_path.unlink()
    
    def test_watch_nonexistent_file(self, watcher):
        """Test watching a non-existent file."""
        fake_path = Path("/nonexistent/theme.yaml")
        success = watcher.watch_file(fake_path)
        assert success is False
        assert str(fake_path.resolve()) not in watcher.watched_files
    
    def test_watch_directory(self, watcher):
        """Test watching a directory."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            
            # Create some theme files
            theme_file1 = tmp_path / "theme1.yaml"
            theme_file2 = tmp_path / "theme2.json"
            non_theme_file = tmp_path / "readme.txt"
            
            theme_file1.write_text("theme: data")
            theme_file2.write_text('{"theme": "data"}')
            non_theme_file.write_text("not a theme")
            
            # Watch directory
            success = watcher.watch_directory(tmp_path, recursive=False)
            assert success is True
            assert str(tmp_path.resolve()) in watcher.watched_directories
            
            # Should watch theme files but not non-theme files
            assert str(theme_file1.resolve()) in watcher.watched_files
            assert str(theme_file2.resolve()) in watcher.watched_files
            assert str(non_theme_file.resolve()) not in watcher.watched_files
    
    def test_watch_directory_recursive(self, watcher):
        """Test recursive directory watching."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            subdir = tmp_path / "subdir"
            subdir.mkdir()
            
            # Create theme file in subdirectory
            theme_file = subdir / "theme.yaml"
            theme_file.write_text("theme: data")
            
            # Watch directory recursively
            success = watcher.watch_directory(tmp_path, recursive=True)
            assert success is True
            
            # Should watch subdirectory and its theme file
            assert str(subdir.resolve()) in watcher.watched_directories
            assert str(theme_file.resolve()) in watcher.watched_files
    
    def test_file_change_debouncing(self, watcher):
        """Test file change debouncing."""
        # Mock the debounce timer
        with patch.object(watcher.debounce_timer, 'start') as mock_start:
            watcher._on_file_changed("/test/file.yaml")
            watcher._on_file_changed("/test/file.yaml")  # Rapid changes
            
            # Timer should be started for debouncing
            assert mock_start.call_count >= 1
            assert "/test/file.yaml" in watcher.pending_changes
    
    def test_clear_watches(self, watcher):
        """Test clearing all watches."""
        # Add some mock watches
        watcher.watched_files.add("/test/file.yaml")
        watcher.watched_directories.add("/test/dir")
        watcher.pending_changes["/test/file.yaml"] = "modified"
        
        watcher.clear_watches()
        
        assert len(watcher.watched_files) == 0
        assert len(watcher.watched_directories) == 0
        assert len(watcher.pending_changes) == 0


class TestHotReloadManager:
    """Test HotReloadManager class."""
    
    @pytest.fixture
    def app(self):
        """Create QApplication for testing."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app
    
    @pytest.fixture
    def mock_theme_engine(self):
        """Create mock theme engine."""
        engine = Mock(spec=ThemeEngine)
        engine.load_theme.return_value = Mock()
        engine.apply_theme.return_value = None
        engine.get_current_theme.return_value = Mock(name="current_theme")
        engine.clear_cache.return_value = None
        return engine
    
    @pytest.fixture
    def reload_manager(self, app, mock_theme_engine):
        """Create HotReloadManager instance."""
        return HotReloadManager(mock_theme_engine)
    
    def test_manager_initialization(self, reload_manager):
        """Test manager initialization."""
        assert reload_manager.theme_engine is not None
        assert reload_manager.file_watcher is not None
        assert reload_manager.auto_reload_enabled is True
        assert reload_manager.reload_delay == 1000
        assert reload_manager.max_reload_attempts == 3
        assert len(reload_manager.file_theme_mapping) == 0
        assert len(reload_manager.reload_history) == 0
    
    def test_theme_name_extraction(self, reload_manager):
        """Test extracting theme name from files."""
        with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False) as tmp:
            tmp_path = Path(tmp.name)
            
            try:
                # Test filename-based extraction
                test_path = tmp_path.parent / "dark_theme.yaml"
                test_path.write_text("content")
                
                theme_name = reload_manager._extract_theme_name_from_file(test_path)
                assert theme_name == "dark_theme"
                
                # Test content-based extraction
                yaml_content = """
                metadata:
                  name: "Custom Theme"
                  version: "1.0.0"
                """
                test_path.write_text(yaml_content)
                
                theme_name = reload_manager._extract_theme_name_from_file(test_path)
                assert theme_name == "Custom Theme"
                
                test_path.unlink()
                
            finally:
                if tmp_path.exists():
                    tmp_path.unlink()
    
    def test_start_watching(self, reload_manager):
        """Test starting to watch theme paths."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            
            # Create a theme file
            theme_file = tmp_path / "test_theme.yaml"
            theme_file.write_text("metadata:\n  name: Test Theme")
            
            # Start watching
            reload_manager.start_watching([theme_file, tmp_path])
            
            # Should map the theme file
            assert str(theme_file.resolve()) in reload_manager.file_theme_mapping
            
            # Stop watching
            reload_manager.stop_watching()
            assert len(reload_manager.file_theme_mapping) == 0
    
    def test_manual_theme_reload(self, reload_manager, mock_theme_engine):
        """Test manual theme reload."""
        theme_name = "test_theme"
        
        # Configure mock to return successful theme
        mock_theme = Mock()
        mock_theme.name = theme_name
        mock_theme_engine.load_theme.return_value = mock_theme
        mock_theme_engine.get_current_theme.return_value = mock_theme
        
        # Perform reload
        success = reload_manager.reload_theme(theme_name, ReloadTrigger.MANUAL)
        
        assert success is True
        mock_theme_engine.clear_cache.assert_called_once()
        mock_theme_engine.load_theme.assert_called_with(theme_name)
        mock_theme_engine.apply_theme.assert_called_with(mock_theme)
        
        # Check reload history
        assert len(reload_manager.reload_history) == 1
        event = reload_manager.reload_history[0]
        assert event.theme_name == theme_name
        assert event.trigger == ReloadTrigger.MANUAL
        assert event.success is True
    
    def test_failed_theme_reload(self, reload_manager, mock_theme_engine):
        """Test failed theme reload."""
        theme_name = "broken_theme"
        
        # Configure mock to fail
        mock_theme_engine.load_theme.side_effect = Exception("Theme load failed")
        
        # Perform reload
        success = reload_manager.reload_theme(theme_name, ReloadTrigger.MANUAL)
        
        assert success is False
        
        # Check reload history
        assert len(reload_manager.reload_history) == 1
        event = reload_manager.reload_history[0]
        assert event.theme_name == theme_name
        assert event.success is False
        assert event.error_message == "Theme load failed"
    
    def test_reload_with_retries(self, reload_manager, mock_theme_engine):
        """Test reload with retry mechanism."""
        theme_name = "flaky_theme"
        
        # Configure mock to fail twice then succeed
        mock_theme = Mock()
        mock_theme.name = theme_name
        mock_theme_engine.load_theme.side_effect = [
            Exception("First failure"),
            Exception("Second failure"),
            mock_theme  # Third attempt succeeds
        ]
        mock_theme_engine.get_current_theme.return_value = None
        
        success = reload_manager.reload_theme(theme_name, ReloadTrigger.MANUAL)
        
        assert success is True
        assert mock_theme_engine.load_theme.call_count == 3
        
        # Check reload history
        event = reload_manager.reload_history[0]
        assert event.success is True
        assert event.additional_data['attempts'] == 3
    
    def test_auto_reload_disable(self, reload_manager):
        """Test disabling auto reload."""
        reload_manager.set_auto_reload(False)
        assert reload_manager.auto_reload_enabled is False
        
        # Should skip reload when disabled
        success = reload_manager.reload_theme("test", ReloadTrigger.FILE_MODIFIED)
        assert success is False
        
        # But should work when forced
        reload_manager.theme_engine.load_theme.return_value = Mock(name="test")
        reload_manager.theme_engine.get_current_theme.return_value = None
        success = reload_manager.reload_theme("test", ReloadTrigger.MANUAL, force=True)
        assert success is True
    
    def test_reload_callbacks(self, reload_manager, mock_theme_engine):
        """Test reload callback system."""
        callback_calls = []
        
        def test_callback(theme_name, success):
            callback_calls.append((theme_name, success))
        
        # Register callback
        reload_manager.register_reload_callback(test_callback)
        
        # Perform successful reload
        mock_theme = Mock()
        mock_theme.name = "test_theme"
        mock_theme_engine.load_theme.return_value = mock_theme
        mock_theme_engine.get_current_theme.return_value = None
        
        reload_manager.reload_theme("test_theme", ReloadTrigger.MANUAL)
        
        assert len(callback_calls) == 1
        assert callback_calls[0] == ("test_theme", True)
        
        # Unregister callback
        reload_manager.unregister_reload_callback(test_callback)
        
        # Should not call callback after unregistering
        reload_manager.reload_theme("test_theme", ReloadTrigger.MANUAL)
        assert len(callback_calls) == 1  # Still 1, not 2
    
    def test_reload_statistics(self, reload_manager, mock_theme_engine):
        """Test reload statistics."""
        # Perform some reloads
        mock_theme = Mock()
        mock_theme.name = "test_theme"
        mock_theme_engine.load_theme.return_value = mock_theme
        mock_theme_engine.get_current_theme.return_value = None
        
        # Successful reload
        reload_manager.reload_theme("theme1", ReloadTrigger.MANUAL)
        
        # Failed reload
        mock_theme_engine.load_theme.side_effect = Exception("Failed")
        reload_manager.reload_theme("theme2", ReloadTrigger.MANUAL)
        
        stats = reload_manager.get_reload_statistics()
        
        assert stats['total_reloads'] == 2
        assert stats['successful_reloads'] == 1
        assert stats['failed_reloads'] == 1
        assert stats['success_rate'] == 0.5
        assert stats['themes_reloaded'] == 2


class TestHotReloadEngine:
    """Test HotReloadEngine class."""
    
    @pytest.fixture
    def mock_theme_engine(self):
        """Create mock theme engine."""
        return Mock(spec=ThemeEngine)
    
    @pytest.fixture
    def reload_engine(self, mock_theme_engine):
        """Create HotReloadEngine instance."""
        return HotReloadEngine(mock_theme_engine)
    
    def test_engine_initialization(self, reload_engine):
        """Test engine initialization."""
        assert reload_engine.theme_engine is not None
        assert reload_engine.reload_manager is None
        assert reload_engine.development_mode is False
    
    def test_enable_development_mode(self, reload_engine):
        """Test enabling development mode."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            
            reload_engine.enable_development_mode(
                theme_paths=[tmp_path],
                auto_reload=True,
                reload_delay=500
            )
            
            assert reload_engine.development_mode is True
            assert reload_engine.reload_manager is not None
            assert reload_engine.reload_manager.auto_reload_enabled is True
            assert reload_engine.reload_manager.reload_delay == 500
    
    def test_disable_development_mode(self, reload_engine):
        """Test disabling development mode."""
        # First enable it
        with tempfile.TemporaryDirectory() as tmp_dir:
            reload_engine.enable_development_mode([Path(tmp_dir)])
            assert reload_engine.development_mode is True
            
            # Then disable it
            reload_engine.disable_development_mode()
            assert reload_engine.development_mode is False
            assert reload_engine.reload_manager is None
    
    def test_reload_current_theme(self, reload_engine, mock_theme_engine):
        """Test reloading current theme."""
        # Without development mode enabled
        success = reload_engine.reload_current_theme()
        assert success is False
        
        # Enable development mode
        reload_engine.enable_development_mode([])
        
        # No current theme
        mock_theme_engine.get_current_theme.return_value = None
        success = reload_engine.reload_current_theme()
        assert success is False
        
        # With current theme
        mock_current_theme = Mock()
        mock_current_theme.name = "current_theme"
        mock_theme_engine.get_current_theme.return_value = mock_current_theme
        mock_theme_engine.load_theme.return_value = mock_current_theme
        
        success = reload_engine.reload_current_theme()
        assert success is True


class TestReloadEvent:
    """Test ReloadEvent data structure."""
    
    def test_reload_event_creation(self):
        """Test creating reload event."""
        event = ReloadEvent(
            timestamp=time.time(),
            theme_name="test_theme",
            trigger=ReloadTrigger.FILE_MODIFIED,
            file_path=Path("/test/theme.yaml"),
            success=True,
            reload_time_ms=150.5
        )
        
        assert event.theme_name == "test_theme"
        assert event.trigger == ReloadTrigger.FILE_MODIFIED
        assert event.file_path == Path("/test/theme.yaml")
        assert event.success is True
        assert event.reload_time_ms == 150.5
        assert event.error_message is None
    
    def test_failed_reload_event(self):
        """Test creating failed reload event."""
        event = ReloadEvent(
            timestamp=time.time(),
            theme_name="broken_theme",
            trigger=ReloadTrigger.MANUAL,
            success=False,
            error_message="Theme parsing failed",
            reload_time_ms=50.0
        )
        
        assert event.success is False
        assert event.error_message == "Theme parsing failed"


@pytest.mark.integration
class TestHotReloadIntegration:
    """Integration tests for hot reload system."""
    
    @pytest.fixture
    def app(self):
        """Create QApplication for testing."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app
    
    def test_file_change_trigger_reload(self, app):
        """Test that file changes trigger theme reloads."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            theme_file = tmp_path / "test_theme.yaml"
            
            # Create initial theme file
            theme_content = """
            metadata:
              name: "Test Theme"
              version: "1.0.0"
            colors:
              primary: "#007bff"
            """
            theme_file.write_text(theme_content)
            
            # Setup mock theme engine
            mock_engine = Mock(spec=ThemeEngine)
            mock_theme = Mock()
            mock_theme.name = "Test Theme"
            mock_engine.load_theme.return_value = mock_theme
            mock_engine.get_current_theme.return_value = mock_theme
            
            # Create reload manager
            reload_manager = HotReloadManager(mock_engine)
            reload_manager.set_reload_delay(100)  # Short delay for testing
            
            # Track reload calls
            reload_calls = []
            def track_reload(theme_name, success):
                reload_calls.append((theme_name, success))
            
            reload_manager.register_reload_callback(track_reload)
            
            # Start watching
            reload_manager.start_watching([theme_file])
            
            # Verify theme file is mapped
            assert str(theme_file.resolve()) in reload_manager.file_theme_mapping
            
            # Simulate file change by writing new content
            new_content = theme_content.replace("#007bff", "#ff0000")
            theme_file.write_text(new_content)
            
            # Manually trigger file change (since we can't wait for filesystem events in tests)
            reload_manager._on_file_changed(str(theme_file.resolve()))
            
            # Process pending reloads
            reload_manager._execute_pending_reloads()
            
            # Should have triggered a reload
            assert len(reload_calls) > 0
            assert reload_calls[0][0] == "Test Theme"
            assert reload_calls[0][1] is True  # Successful reload
            
            # Cleanup
            reload_manager.stop_watching()
    
    def test_complete_development_workflow(self, app):
        """Test complete development workflow."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            
            # Create theme files
            light_theme = tmp_path / "light.yaml"
            dark_theme = tmp_path / "dark.yaml"
            
            light_theme.write_text("""
            metadata:
              name: "Light Theme"
            colors:
              background: "#ffffff"
            """)
            
            dark_theme.write_text("""
            metadata:
              name: "Dark Theme"
            colors:
              background: "#000000"
            """)
            
            # Setup theme engine
            config_manager = ConfigManager()
            event_bus = EventBus()
            theme_engine = ThemeEngine(config_manager, event_bus)
            
            # Create hot reload engine
            reload_engine = HotReloadEngine(theme_engine)
            
            # Enable development mode
            reload_engine.enable_development_mode(
                theme_paths=[tmp_path],
                auto_reload=True,
                reload_delay=100
            )
            
            assert reload_engine.is_development_mode() is True
            
            # Get reload manager
            reload_manager = reload_engine.get_reload_manager()
            assert reload_manager is not None
            
            # Should have mapped theme files
            theme_files_mapped = len(reload_manager.file_theme_mapping)
            assert theme_files_mapped >= 2
            
            # Test manual reload
            with patch.object(theme_engine, 'load_theme') as mock_load, \
                 patch.object(theme_engine, 'apply_theme') as mock_apply:
                
                mock_theme = Mock()
                mock_theme.name = "Light Theme"
                mock_load.return_value = mock_theme
                
                success = reload_manager.reload_theme("Light Theme", ReloadTrigger.MANUAL)
                assert success is True
                
                mock_load.assert_called_with("Light Theme")
            
            # Get statistics
            stats = reload_manager.get_reload_statistics()
            assert stats['total_reloads'] >= 1
            
            # Disable development mode
            reload_engine.disable_development_mode()
            assert reload_engine.is_development_mode() is False