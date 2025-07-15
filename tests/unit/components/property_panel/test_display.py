"""Tests for property display widgets"""

import pytest
from unittest.mock import Mock, patch
from PyQt6.QtWidgets import QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QCheckBox, QComboBox, QProgressBar
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest

from src.torematrix.ui.components.property_panel.display import PropertyDisplayWidget, ConfidenceScoreWidget
from src.torematrix.ui.components.property_panel.models import PropertyMetadata


class TestPropertyDisplayWidget:
    @pytest.fixture
    def string_metadata(self):
        """Create string property metadata"""
        return PropertyMetadata(
            name="text",
            display_name="Text Content",
            description="The text content of the element",
            category="Content"
        )
    
    @pytest.fixture
    def confidence_metadata(self):
        """Create confidence property metadata"""
        return PropertyMetadata(
            name="confidence",
            display_name="Confidence Score",
            description="AI confidence score",
            category="Analysis",
            editable=False
        )
    
    def test_string_property_creation(self, qtbot, string_metadata):
        """Test creating string property widget"""
        widget = PropertyDisplayWidget("text", "Sample text", string_metadata)
        qtbot.addWidget(widget)
        
        assert widget._property_name == "text"
        assert widget._property_value == "Sample text"
        assert widget._metadata == string_metadata
        assert widget._name_label.text() == "Text Content"
        assert isinstance(widget._value_widget, QLineEdit)
        assert widget._value_widget.text() == "Sample text"
    
    def test_multiline_string_property(self, qtbot):
        """Test creating multiline string property widget"""
        long_text = "This is a very long text that should trigger multiline editor\n" * 3
        widget = PropertyDisplayWidget("content", long_text)
        qtbot.addWidget(widget)
        
        assert isinstance(widget._value_widget, QTextEdit)
        assert widget._value_widget.toPlainText() == long_text
    
    def test_integer_property_creation(self, qtbot):
        """Test creating integer property widget"""
        widget = PropertyDisplayWidget("page", 5)
        qtbot.addWidget(widget)
        
        assert isinstance(widget._value_widget, QSpinBox)
        assert widget._value_widget.value() == 5
    
    def test_float_property_creation(self, qtbot):
        """Test creating float property widget"""
        widget = PropertyDisplayWidget("x", 10.5)
        qtbot.addWidget(widget)
        
        assert isinstance(widget._value_widget, QDoubleSpinBox)
        assert widget._value_widget.value() == 10.5
    
    def test_confidence_property_creation(self, qtbot):
        """Test creating confidence property widget"""
        widget = PropertyDisplayWidget("confidence", 0.85)
        qtbot.addWidget(widget)
        
        # Should contain a progress bar
        progress_bars = widget.findChildren(QProgressBar)
        assert len(progress_bars) == 1
        progress_bar = progress_bars[0]
        assert progress_bar.value() == 85  # 0.85 * 100
    
    def test_coordinate_property_creation(self, qtbot):
        """Test creating coordinate property widget"""
        coord_value = {"x": 10.5, "y": 20.3}
        widget = PropertyDisplayWidget("position", coord_value)
        qtbot.addWidget(widget)
        
        # Should contain two double spin boxes
        spin_boxes = widget.findChildren(QDoubleSpinBox)
        assert len(spin_boxes) == 2
    
    def test_choice_property_creation(self, qtbot):
        """Test creating choice property widget"""
        widget = PropertyDisplayWidget("type", "Text")
        qtbot.addWidget(widget)
        
        assert isinstance(widget._value_widget, QComboBox)
        assert "Text" in [widget._value_widget.itemText(i) for i in range(widget._value_widget.count())]
    
    def test_property_type_inference(self, qtbot):
        """Test property type inference from name"""
        widget = PropertyDisplayWidget("unknown_prop", "value")
        qtbot.addWidget(widget)
        
        assert widget._get_property_type() == "string"
        assert widget._get_property_type_display() == "STRING"
    
    def test_display_name_generation(self, qtbot):
        """Test display name generation"""
        widget = PropertyDisplayWidget("property_name", "value")
        qtbot.addWidget(widget)
        
        assert widget._get_display_name() == "Property Name"
        
        # Test with metadata
        metadata = PropertyMetadata("prop", "Custom Display Name", "desc")
        widget_with_metadata = PropertyDisplayWidget("prop", "value", metadata)
        qtbot.addWidget(widget_with_metadata)
        
        assert widget_with_metadata._get_display_name() == "Custom Display Name"
    
    def test_value_changed_signal(self, qtbot):
        """Test value changed signal emission"""
        widget = PropertyDisplayWidget("text", "initial")
        qtbot.addWidget(widget)
        
        # Connect signal
        signal_emitted = []
        widget.value_changed.connect(
            lambda name, value: signal_emitted.append((name, value))
        )
        
        # Simulate value change
        widget._emit_value_changed("new_value")
        
        assert len(signal_emitted) == 1
        assert signal_emitted[0] == ("text", "new_value")
    
    def test_selection_handling(self, qtbot):
        """Test property selection"""
        widget = PropertyDisplayWidget("text", "value")
        qtbot.addWidget(widget)
        
        # Connect signal
        signal_emitted = []
        widget.selected.connect(lambda name: signal_emitted.append(name))
        
        # Test selection
        widget.set_selected(True)
        
        assert widget._is_selected is True
        assert len(signal_emitted) == 1
        assert signal_emitted[0] == "text"
    
    def test_compact_mode(self, qtbot):
        """Test compact mode setting"""
        widget = PropertyDisplayWidget("text", "value")
        qtbot.addWidget(widget)
        
        widget.set_compact_mode(True)
        assert widget._compact_mode is True
        
        widget.set_compact_mode(False)
        assert widget._compact_mode is False
    
    def test_metadata_visibility(self, qtbot):
        """Test metadata section visibility"""
        metadata = PropertyMetadata(
            "text", "Text", "Description", validation_rules=["required"]
        )
        widget = PropertyDisplayWidget("text", "value", metadata)
        qtbot.addWidget(widget)
        
        # Metadata should be visible by default
        assert widget._show_metadata is True
        assert widget._metadata_frame is not None
        
        # Hide metadata
        widget.set_show_metadata(False)
        assert widget._metadata_frame.isVisible() is False
    
    def test_validation_error_display(self, qtbot):
        """Test validation error display"""
        widget = PropertyDisplayWidget("text", "value")
        qtbot.addWidget(widget)
        
        # Show validation error
        widget.show_validation_error("Invalid value")
        
        assert widget._validation_error == "Invalid value"
        assert widget._validation_frame.isVisible() is True
        assert "Invalid value" in widget._validation_label.text()
    
    def test_validation_error_auto_hide(self, qtbot):
        """Test validation error auto-hide"""
        widget = PropertyDisplayWidget("text", "value")
        qtbot.addWidget(widget)
        
        widget.show_validation_error("Error")
        assert widget._validation_frame.isVisible() is True
        
        # Manually trigger hide (simulating timer)
        widget._hide_validation_error()
        assert widget._validation_frame.isVisible() is False
        assert widget._validation_error is None
    
    def test_update_value(self, qtbot):
        """Test updating property value"""
        widget = PropertyDisplayWidget("text", "initial")
        qtbot.addWidget(widget)
        
        widget.update_value("updated")
        assert widget._property_value == "updated"
    
    def test_mouse_press_selection(self, qtbot):
        """Test mouse press triggers selection"""
        widget = PropertyDisplayWidget("text", "value")
        qtbot.addWidget(widget)
        
        # Connect signal
        signal_emitted = []
        widget.selected.connect(lambda name: signal_emitted.append(name))
        
        # Simulate mouse press
        QTest.mousePress(widget, Qt.MouseButton.LeftButton)
        
        assert len(signal_emitted) == 1
        assert signal_emitted[0] == "text"
    
    def test_size_hint(self, qtbot):
        """Test size hint for compact and normal modes"""
        widget = PropertyDisplayWidget("text", "value")
        qtbot.addWidget(widget)
        
        # Normal mode
        normal_size = widget.sizeHint()
        assert normal_size.width() == 250
        assert normal_size.height() == 60
        
        # Compact mode
        widget.set_compact_mode(True)
        compact_size = widget.sizeHint()
        assert compact_size.width() == 200
        assert compact_size.height() == 30


class TestConfidenceScoreWidget:
    def test_confidence_widget_creation(self, qtbot):
        """Test creating confidence score widget"""
        widget = ConfidenceScoreWidget(0.75)
        qtbot.addWidget(widget)
        
        assert widget._confidence_score == 0.75
        assert "0.750" in widget._score_label.text()
        assert widget._progress_bar.value() == 75
    
    def test_confidence_score_clamping(self, qtbot):
        """Test confidence score is clamped to [0,1]"""
        # Test value > 1
        widget1 = ConfidenceScoreWidget(1.5)
        qtbot.addWidget(widget1)
        assert widget1._confidence_score == 1.0
        
        # Test value < 0
        widget2 = ConfidenceScoreWidget(-0.5)
        qtbot.addWidget(widget2)
        assert widget2._confidence_score == 0.0
    
    def test_confidence_color_coding(self, qtbot):
        """Test confidence score color coding"""
        # High confidence (green)
        high_widget = ConfidenceScoreWidget(0.9)
        qtbot.addWidget(high_widget)
        assert "#4CAF50" in high_widget.styleSheet()
        
        # Medium confidence (orange)
        medium_widget = ConfidenceScoreWidget(0.7)
        qtbot.addWidget(medium_widget)
        assert "#FF9800" in medium_widget.styleSheet()
        
        # Low confidence (red)
        low_widget = ConfidenceScoreWidget(0.3)
        qtbot.addWidget(low_widget)
        assert "#F44336" in low_widget.styleSheet()
    
    def test_update_confidence_score(self, qtbot):
        """Test updating confidence score"""
        widget = ConfidenceScoreWidget(0.5)
        qtbot.addWidget(widget)
        
        widget.update_confidence_score(0.8)
        
        assert widget._confidence_score == 0.8
        assert "0.800" in widget._score_label.text()
        assert widget._progress_bar.value() == 80
    
    def test_compact_mode(self, qtbot):
        """Test compact mode for confidence widget"""
        widget = ConfidenceScoreWidget(0.75)
        qtbot.addWidget(widget)
        
        # Enable compact mode
        widget.set_compact_mode(True)
        assert widget._compact_mode is True
        assert widget._score_label.isVisible() is False
        
        # Disable compact mode
        widget.set_compact_mode(False)
        assert widget._score_label.isVisible() is True
    
    def test_text_visibility(self, qtbot):
        """Test text visibility setting"""
        widget = ConfidenceScoreWidget(0.75)
        qtbot.addWidget(widget)
        
        widget.set_show_text(False)
        assert widget._show_text is False
        assert widget._score_label.isVisible() is False
        
        widget.set_show_text(True)
        assert widget._score_label.isVisible() is True
    
    def test_size_hint(self, qtbot):
        """Test size hint for compact and normal modes"""
        widget = ConfidenceScoreWidget(0.75)
        qtbot.addWidget(widget)
        
        # Normal mode
        normal_size = widget.sizeHint()
        assert normal_size.width() == 60
        assert normal_size.height() == 35
        
        # Compact mode
        widget.set_compact_mode(True)
        compact_size = widget.sizeHint()
        assert compact_size.width() == 40
        assert compact_size.height() == 20