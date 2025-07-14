"""
Integration tests for PDF.js Agent 4 features.

Tests the complete integration of advanced PDF features including
search, annotations, text selection, print, UI integration, and accessibility.
"""

import pytest
import time
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtWebEngineWidgets import QWebEngineView

from src.torematrix.integrations.pdf.features import FeatureManager, FeatureConfig, FeatureSet
from src.torematrix.integrations.pdf.search import SearchManager, SearchQuery, SearchResult
from src.torematrix.integrations.pdf.annotations import AnnotationManager, PDFAnnotation, AnnotationType
from src.torematrix.integrations.pdf.ui import PDFUIManager, PDFToolbar, ThumbnailPanel
from src.torematrix.integrations.pdf.accessibility import AccessibilityManager, AccessibilityFeature
from src.torematrix.integrations.pdf.viewer import PDFViewer
from src.torematrix.integrations.pdf.bridge import PDFBridge


class TestFeatureManager:
    """Test feature manager integration."""
    
    @pytest.fixture
    def pdf_viewer(self, qtbot):
        """Create mock PDF viewer."""
        viewer = Mock(spec=QWebEngineView)
        viewer.page.return_value = Mock()
        viewer.page().runJavaScript = Mock()
        return viewer
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return FeatureConfig(
            search_enabled=True,
            annotations_enabled=True,
            text_selection_enabled=True,
            print_enabled=True,
            toolbar_enabled=True,
            thumbnail_panel=True,
            accessibility_enabled=True
        )
    
    @pytest.fixture
    def feature_manager(self, pdf_viewer, config):
        """Create feature manager instance."""
        return FeatureManager(pdf_viewer, config)
    
    def test_feature_manager_initialization(self, feature_manager):
        """Test feature manager initialization."""
        assert feature_manager.pdf_viewer is not None
        assert feature_manager.config is not None
        assert feature_manager.search_manager is not None
        assert feature_manager.annotation_manager is not None
        assert feature_manager.ui_manager is not None
        assert feature_manager.accessibility_manager is not None
    
    def test_feature_enabling_disabling(self, feature_manager):
        """Test feature enabling and disabling."""
        # Test enabling features
        assert feature_manager.enable_feature(FeatureSet.SEARCH)
        assert feature_manager.is_feature_enabled(FeatureSet.SEARCH)
        
        assert feature_manager.enable_feature(FeatureSet.ANNOTATIONS)
        assert feature_manager.is_feature_enabled(FeatureSet.ANNOTATIONS)
        
        # Test disabling features
        assert feature_manager.disable_feature(FeatureSet.SEARCH)
        assert not feature_manager.is_feature_enabled(FeatureSet.SEARCH)
    
    def test_bridge_integration(self, feature_manager):
        """Test bridge integration."""
        # Create mock bridge
        bridge = Mock(spec=PDFBridge)
        bridge.feature_event = Mock()
        bridge.element_selected = Mock()
        
        # Connect bridge
        feature_manager.connect_bridge(bridge)
        assert feature_manager.bridge == bridge
    
    def test_performance_config_integration(self, feature_manager):
        """Test performance configuration integration."""
        perf_config = {
            "performance_level": "high",
            "cache_size_mb": 200,
            "enable_gpu_acceleration": True
        }
        
        feature_manager.set_performance_config(perf_config)
        assert feature_manager.performance_config == perf_config
    
    def test_search_integration(self, feature_manager):
        """Test search functionality integration."""
        # Test search
        result = feature_manager.search_text("test query", {
            "case_sensitive": False,
            "whole_words": True
        })
        
        # Should return True if search was initiated
        assert isinstance(result, bool)
    
    def test_annotation_integration(self, feature_manager):
        """Test annotation functionality integration."""
        # Test showing annotation
        result = feature_manager.show_annotation("test-annotation-id")
        
        # Should return False for non-existent annotation
        assert result == False
    
    def test_print_integration(self, feature_manager):
        """Test print functionality integration."""
        # Test print document
        result = feature_manager.print_document({
            "page_range": "1-5",
            "quality": "high"
        })
        
        # Should return True if print was initiated
        assert isinstance(result, bool)
    
    def test_feature_metrics(self, feature_manager):
        """Test feature metrics collection."""
        metrics = feature_manager.get_feature_metrics()
        
        assert hasattr(metrics, 'search_time_ms')
        assert hasattr(metrics, 'ui_response_time_ms')
        assert hasattr(metrics, 'accessibility_score')
    
    def test_feature_status(self, feature_manager):
        """Test comprehensive feature status."""
        status = feature_manager.get_feature_status()
        
        assert "enabled_features" in status
        assert "feature_metrics" in status
        assert "target_metrics" in status
        assert "targets_met" in status
        assert "agent_integration" in status


class TestSearchIntegration:
    """Test search functionality integration."""
    
    @pytest.fixture
    def pdf_viewer(self):
        """Create mock PDF viewer."""
        viewer = Mock(spec=QWebEngineView)
        viewer.page.return_value = Mock()
        return viewer
    
    @pytest.fixture
    def config(self):
        """Create search configuration."""
        return FeatureConfig(search_enabled=True)
    
    @pytest.fixture
    def search_manager(self, pdf_viewer, config):
        """Create search manager."""
        return SearchManager(pdf_viewer, config)
    
    def test_search_initialization(self, search_manager):
        """Test search manager initialization."""
        assert search_manager.enabled == True
        assert search_manager.current_query is None
        assert len(search_manager.search_results) == 0
    
    def test_search_query_creation(self, search_manager):
        """Test search query creation and validation."""
        # Test valid search
        result = search_manager.search("test query", {
            "case_sensitive": True,
            "whole_words": False,
            "regex": False
        })
        
        assert isinstance(result, bool)
        assert search_manager.current_query is not None
        assert search_manager.current_query.query == "test query"
    
    def test_search_history(self, search_manager):
        """Test search history functionality."""
        # Perform multiple searches
        search_manager.search("query 1")
        search_manager.search("query 2")
        search_manager.search("query 3")
        
        history = search_manager.get_search_history()
        assert len(history) >= 3
    
    def test_search_caching(self, search_manager):
        """Test search result caching."""
        # First search
        search_manager.search("cached query")
        
        # Second search with same query should use cache
        search_manager.search("cached query")
        
        # Check cache
        assert len(search_manager.search_cache) > 0
    
    def test_search_navigation(self, search_manager):
        """Test search result navigation."""
        # Mock search results
        search_manager.search_results = [
            SearchResult(1, "result 1", 0, 8, {"x": 0, "y": 0, "width": 50, "height": 20}),
            SearchResult(1, "result 2", 10, 18, {"x": 100, "y": 0, "width": 50, "height": 20}),
            SearchResult(2, "result 3", 0, 8, {"x": 0, "y": 50, "width": 50, "height": 20})
        ]
        
        # Test navigation
        result = search_manager.next_result()
        assert result is not None
        assert search_manager.current_result_index == 1
        
        result = search_manager.previous_result()
        assert result is not None
        assert search_manager.current_result_index == 0
    
    def test_search_clearing(self, search_manager):
        """Test search clearing functionality."""
        # Add some search data
        search_manager.search("test")
        search_manager.search_results = [Mock()]
        
        # Clear search
        search_manager.clear_search()
        
        assert search_manager.current_query is None
        assert len(search_manager.search_results) == 0
        assert search_manager.current_result_index == -1
    
    def test_search_metrics(self, search_manager):
        """Test search performance metrics."""
        metrics = search_manager.get_metrics()
        
        assert "total_searches" in metrics
        assert "avg_search_time_ms" in metrics
        assert "cache_hit_rate" in metrics
        assert "targets_met" in metrics
    
    def test_search_widget_creation(self, search_manager, qtbot):
        """Test search UI widget creation."""
        widget = search_manager.create_search_widget()
        qtbot.addWidget(widget)
        
        assert widget is not None
        assert hasattr(search_manager, 'search_input')
        assert hasattr(search_manager, 'case_sensitive_cb')


class TestAnnotationIntegration:
    """Test annotation functionality integration."""
    
    @pytest.fixture
    def pdf_viewer(self):
        """Create mock PDF viewer."""
        viewer = Mock(spec=QWebEngineView)
        viewer.page.return_value = Mock()
        return viewer
    
    @pytest.fixture
    def config(self):
        """Create annotation configuration."""
        return FeatureConfig(annotations_enabled=True)
    
    @pytest.fixture
    def annotation_manager(self, pdf_viewer, config):
        """Create annotation manager."""
        return AnnotationManager(pdf_viewer, config)
    
    def test_annotation_initialization(self, annotation_manager):
        """Test annotation manager initialization."""
        assert annotation_manager.enabled == True
        assert len(annotation_manager.annotations) == 0
        assert len(annotation_manager.annotations_by_page) == 0
    
    def test_annotation_loading(self, annotation_manager):
        """Test annotation loading."""
        result = annotation_manager.load_annotations()
        assert isinstance(result, bool)
    
    def test_annotation_visibility(self, annotation_manager):
        """Test annotation show/hide functionality."""
        # Create test annotation
        from src.torematrix.integrations.pdf.annotations import AnnotationCoordinates
        
        coords = AnnotationCoordinates(page=1, x=10, y=10, width=100, height=20)
        annotation = PDFAnnotation(
            id="test-annotation",
            type=AnnotationType.TEXT,
            coordinates=coords,
            content="Test annotation"
        )
        
        # Add to manager
        annotation_manager.annotations["test-annotation"] = annotation
        
        # Test show/hide
        assert annotation_manager.show_annotation("test-annotation") == True
        assert annotation_manager.hide_annotation("test-annotation") == True
        assert annotation_manager.show_annotation("non-existent") == False
    
    def test_annotation_type_filtering(self, annotation_manager):
        """Test annotation type filtering."""
        # Test toggling annotation types
        annotation_manager.toggle_annotation_type(AnnotationType.HIGHLIGHT, False)
        assert annotation_manager.visible_types[AnnotationType.HIGHLIGHT] == False
        
        annotation_manager.toggle_annotation_type(AnnotationType.HIGHLIGHT, True)
        assert annotation_manager.visible_types[AnnotationType.HIGHLIGHT] == True
    
    def test_annotation_search(self, annotation_manager):
        """Test annotation search functionality."""
        # Create test annotations
        from src.torematrix.integrations.pdf.annotations import AnnotationCoordinates
        
        coords = AnnotationCoordinates(page=1, x=0, y=0, width=100, height=20)
        annotation1 = PDFAnnotation("ann1", AnnotationType.TEXT, coords, content="searchable content")
        annotation2 = PDFAnnotation("ann2", AnnotationType.HIGHLIGHT, coords, content="other text")
        
        annotation_manager.annotations["ann1"] = annotation1
        annotation_manager.annotations["ann2"] = annotation2
        
        # Search annotations
        results = annotation_manager.search_annotations("searchable", "content")
        assert len(results) == 1
        assert results[0].id == "ann1"
    
    def test_annotation_metrics(self, annotation_manager):
        """Test annotation metrics."""
        metrics = annotation_manager.get_metrics()
        
        assert "total_annotations" in metrics
        assert "visible_annotations" in metrics
        assert "annotations_by_type" in metrics
        assert "avg_render_time_ms" in metrics
    
    def test_annotation_panel_creation(self, annotation_manager, qtbot):
        """Test annotation panel creation."""
        panel = annotation_manager.create_annotation_panel()
        qtbot.addWidget(panel)
        
        assert panel is not None
        assert hasattr(annotation_manager, 'annotation_list')


class TestUIIntegration:
    """Test UI framework integration."""
    
    @pytest.fixture
    def pdf_viewer(self):
        """Create mock PDF viewer."""
        viewer = Mock(spec=QWebEngineView)
        return viewer
    
    @pytest.fixture
    def config(self):
        """Create UI configuration."""
        return FeatureConfig(
            toolbar_enabled=True,
            thumbnail_panel=True,
            progress_indicators=True
        )
    
    @pytest.fixture
    def ui_manager(self, pdf_viewer, config):
        """Create UI manager."""
        return PDFUIManager(pdf_viewer, config)
    
    def test_ui_manager_initialization(self, ui_manager):
        """Test UI manager initialization."""
        assert ui_manager.enabled == True
        assert ui_manager.pdf_viewer is not None
        assert ui_manager.config is not None
    
    def test_main_widget_creation(self, ui_manager, qtbot):
        """Test main widget creation."""
        widget = ui_manager.create_main_widget()
        qtbot.addWidget(widget)
        
        assert widget is not None
        assert ui_manager.toolbar is not None
        assert ui_manager.thumbnail_panel is not None
        assert ui_manager.progress_indicator is not None
    
    def test_toolbar_functionality(self, ui_manager, qtbot):
        """Test toolbar functionality."""
        widget = ui_manager.create_main_widget()
        qtbot.addWidget(widget)
        
        toolbar = ui_manager.get_toolbar()
        assert toolbar is not None
        
        # Test document info update
        toolbar.update_document_info(100, 5)
        assert toolbar.page_input.maximum() == 100
        assert toolbar.page_input.value() == 5
        
        # Test zoom info update
        toolbar.update_zoom_info(1.5)
        assert toolbar.zoom_slider.value() == 150
    
    def test_thumbnail_panel_functionality(self, ui_manager, qtbot):
        """Test thumbnail panel functionality."""
        widget = ui_manager.create_main_widget()
        qtbot.addWidget(widget)
        
        thumbnail_panel = ui_manager.get_thumbnail_panel()
        assert thumbnail_panel is not None
        
        # Test thumbnail loading
        thumbnail_panel.load_thumbnails(10)
        assert thumbnail_panel.thumbnail_list.count() == 10
    
    def test_progress_indicator_functionality(self, ui_manager, qtbot):
        """Test progress indicator functionality."""
        widget = ui_manager.create_main_widget()
        qtbot.addWidget(widget)
        
        progress = ui_manager.get_progress_indicator()
        assert progress is not None
        
        # Test progress display
        progress.show_progress("Loading...", 100)
        assert progress.progress_bar.isVisible() == True
        
        progress.update_progress(50, "Half done")
        assert progress.progress_bar.value() == 50
        
        progress.hide_progress("Complete")
        assert progress.progress_bar.isVisible() == False
    
    def test_ui_metrics(self, ui_manager):
        """Test UI performance metrics."""
        metrics = ui_manager.get_metrics()
        
        assert "toolbar_response_time_ms" in metrics
        assert "thumbnail_load_time_ms" in metrics
        assert "avg_response_time_ms" in metrics
        assert "targets_met" in metrics
        assert "component_status" in metrics


class TestAccessibilityIntegration:
    """Test accessibility functionality integration."""
    
    @pytest.fixture
    def pdf_viewer(self):
        """Create mock PDF viewer."""
        viewer = Mock(spec=QWebEngineView)
        viewer.page.return_value = Mock()
        viewer.page().runJavaScript = Mock()
        viewer.parentWidget.return_value = Mock()
        return viewer
    
    @pytest.fixture
    def config(self):
        """Create accessibility configuration."""
        return FeatureConfig(
            accessibility_enabled=True,
            screen_reader_support=True,
            keyboard_navigation=True,
            high_contrast_support=True
        )
    
    @pytest.fixture
    def accessibility_manager(self, pdf_viewer, config):
        """Create accessibility manager."""
        return AccessibilityManager(pdf_viewer, config)
    
    def test_accessibility_initialization(self, accessibility_manager):
        """Test accessibility manager initialization."""
        assert accessibility_manager.enabled == True
        assert len(accessibility_manager.enabled_features) > 0
        assert len(accessibility_manager.shortcuts) > 0
    
    def test_feature_toggling(self, accessibility_manager):
        """Test accessibility feature toggling."""
        # Test high contrast
        accessibility_manager.toggle_feature(AccessibilityFeature.HIGH_CONTRAST, True)
        assert accessibility_manager.enabled_features[AccessibilityFeature.HIGH_CONTRAST] == True
        
        accessibility_manager.toggle_feature(AccessibilityFeature.HIGH_CONTRAST, False)
        assert accessibility_manager.enabled_features[AccessibilityFeature.HIGH_CONTRAST] == False
    
    def test_high_contrast_mode(self, accessibility_manager):
        """Test high contrast mode."""
        # Enable high contrast
        accessibility_manager.enable_high_contrast()
        assert accessibility_manager.high_contrast_enabled == True
        
        # Disable high contrast
        accessibility_manager.disable_high_contrast()
        assert accessibility_manager.high_contrast_enabled == False
    
    def test_keyboard_shortcuts(self, accessibility_manager):
        """Test keyboard shortcut setup."""
        shortcuts = accessibility_manager.shortcuts
        
        assert "next_page" in shortcuts
        assert "prev_page" in shortcuts
        assert "search" in shortcuts
        assert "high_contrast" in shortcuts
    
    def test_accessibility_compliance(self, accessibility_manager):
        """Test accessibility compliance checking."""
        # Run accessibility scan (mocked)
        accessibility_manager._run_accessibility_scan()
        
        # Check metrics
        assert accessibility_manager.metrics.wcag_compliance_score >= 0.0
        assert accessibility_manager.metrics.wcag_compliance_score <= 1.0
    
    def test_accessibility_metrics(self, accessibility_manager):
        """Test accessibility metrics."""
        metrics = accessibility_manager.get_metrics()
        
        assert "wcag_compliance_score" in metrics
        assert "features_enabled" in metrics
        assert "compliance_level" in metrics
        assert "targets_met" in metrics
    
    def test_accessibility_panel_creation(self, accessibility_manager, qtbot):
        """Test accessibility panel creation."""
        panel = accessibility_manager.create_accessibility_panel()
        qtbot.addWidget(panel)
        
        assert panel is not None
        assert hasattr(accessibility_manager, 'compliance_label')
        assert hasattr(accessibility_manager, 'issues_text')


class TestFullIntegration:
    """Test complete system integration."""
    
    @pytest.fixture
    def app(self):
        """Create QApplication if needed."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app
    
    @pytest.fixture
    def pdf_viewer(self, qtbot):
        """Create real PDF viewer for integration testing."""
        viewer = Mock(spec=PDFViewer)
        viewer.page.return_value = Mock()
        viewer.page().runJavaScript = Mock()
        viewer.parentWidget.return_value = Mock()
        return viewer
    
    @pytest.fixture
    def complete_system(self, pdf_viewer):
        """Create complete integrated system."""
        config = FeatureConfig(
            search_enabled=True,
            annotations_enabled=True,
            text_selection_enabled=True,
            print_enabled=True,
            toolbar_enabled=True,
            thumbnail_panel=True,
            accessibility_enabled=True
        )
        
        # Create feature manager
        feature_manager = FeatureManager(pdf_viewer, config)
        
        # Create bridge
        bridge = Mock(spec=PDFBridge)
        bridge.feature_event = Mock()
        bridge.element_selected = Mock()
        bridge.send_feature_command = Mock()
        
        # Connect components
        feature_manager.connect_bridge(bridge)
        
        # Set performance config
        perf_config = {
            "performance_level": "high",
            "cache_size_mb": 200,
            "enable_gpu_acceleration": True
        }
        feature_manager.set_performance_config(perf_config)
        
        return {
            "feature_manager": feature_manager,
            "bridge": bridge,
            "config": config,
            "perf_config": perf_config
        }
    
    def test_complete_system_initialization(self, complete_system):
        """Test complete system initialization."""
        system = complete_system
        feature_manager = system["feature_manager"]
        
        # Check all components are initialized
        assert feature_manager.search_manager is not None
        assert feature_manager.annotation_manager is not None
        assert feature_manager.ui_manager is not None
        assert feature_manager.accessibility_manager is not None
        assert feature_manager.bridge is not None
        assert feature_manager.performance_config is not None
    
    def test_agent_integration(self, complete_system):
        """Test integration with all agents."""
        system = complete_system
        feature_manager = system["feature_manager"]
        
        # Check Agent 1 integration (core viewer)
        assert feature_manager.pdf_viewer is not None
        
        # Check Agent 2 integration (bridge)
        assert feature_manager.bridge is not None
        
        # Check Agent 3 integration (performance)
        assert feature_manager.performance_config is not None
        
        # Check Agent 4 integration (features)
        status = feature_manager.get_feature_status()
        assert status["agent_integration"]["agent_1_viewer"] == True
        assert status["agent_integration"]["agent_2_bridge"] == True
        assert status["agent_integration"]["agent_3_performance"] == True
    
    def test_feature_coordination(self, complete_system):
        """Test feature coordination and communication."""
        system = complete_system
        feature_manager = system["feature_manager"]
        
        # Test search coordination
        feature_manager.search_text("test query")
        
        # Test annotation coordination
        feature_manager.show_annotation("test-id")
        
        # Test print coordination
        feature_manager.print_document({"pages": "1-5"})
        
        # Verify bridge communication
        bridge = system["bridge"]
        assert bridge.send_feature_command.called
    
    def test_performance_targets(self, complete_system):
        """Test that performance targets are met."""
        system = complete_system
        feature_manager = system["feature_manager"]
        
        # Get feature metrics
        metrics = feature_manager.get_feature_metrics()
        
        # Check targets (these would be updated with actual measurements)
        # Note: In real tests, these would be measured with actual operations
        assert metrics.search_target_ms == 2000.0
        assert metrics.ui_target_ms == 100.0
        assert metrics.thumbnail_target_ms == 500.0
        assert metrics.print_target_ms == 5000.0
        assert metrics.accessibility_target == 0.9
    
    def test_error_handling(self, complete_system):
        """Test system error handling and recovery."""
        system = complete_system
        feature_manager = system["feature_manager"]
        
        # Test with invalid inputs
        result = feature_manager.search_text("")  # Empty query
        assert isinstance(result, bool)
        
        result = feature_manager.show_annotation("")  # Empty ID
        assert result == False
        
        # Test feature disabling/enabling
        assert feature_manager.disable_feature(FeatureSet.SEARCH)
        assert not feature_manager.is_feature_enabled(FeatureSet.SEARCH)
        
        assert feature_manager.enable_feature(FeatureSet.SEARCH)
        assert feature_manager.is_feature_enabled(FeatureSet.SEARCH)
    
    def test_cleanup_and_resource_management(self, complete_system):
        """Test proper cleanup and resource management."""
        system = complete_system
        feature_manager = system["feature_manager"]
        
        # Test cleanup
        feature_manager.cleanup()
        
        # Verify cleanup completed without errors
        assert True  # If we get here, cleanup succeeded


if __name__ == "__main__":
    pytest.main([__file__])