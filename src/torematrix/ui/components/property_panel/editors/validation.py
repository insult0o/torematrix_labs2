"""Validation editors for the property panel

Provides validation-specific editors for elements that require
validation status, confidence scores, and quality metrics.
"""

from typing import Any, Optional, List, Dict, Callable
from dataclasses import dataclass
from enum import Enum, auto
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QSpinBox,
    QComboBox, QProgressBar, QGroupBox, QCheckBox, QFrame
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor, QPalette

from ..base import BasePropertyEditor


class ValidationStatus(Enum):
    """Validation status enumeration."""
    UNKNOWN = auto()
    VALID = auto()
    INVALID = auto()
    PENDING = auto()
    MANUAL_REVIEW = auto()


@dataclass
class ValidationResult:
    """Result of a validation check."""
    is_valid: bool
    confidence: float = 0.0
    status: ValidationStatus = ValidationStatus.UNKNOWN
    errors: List[str] = None
    warnings: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.metadata is None:
            self.metadata = {}


class ValidationStatusEditor(BasePropertyEditor):
    """Editor for validation status."""
    
    value_changed = pyqtSignal(object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_status = ValidationStatus.UNKNOWN
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup the validation status editor UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Status indicator
        self.status_indicator = QFrame()
        self.status_indicator.setFixedSize(16, 16)
        self.status_indicator.setFrameStyle(QFrame.Shape.Box)
        layout.addWidget(self.status_indicator)
        
        # Status combo box
        self.status_combo = QComboBox()
        for status in ValidationStatus:
            self.status_combo.addItem(status.name.replace('_', ' ').title(), status)
        self.status_combo.currentIndexChanged.connect(self._on_status_changed)
        layout.addWidget(self.status_combo)
        
        self._update_indicator()
        
    def _update_indicator(self):
        """Update the status indicator color."""
        status = self._current_status
        colors = {
            ValidationStatus.VALID: QColor(0, 200, 0),
            ValidationStatus.INVALID: QColor(200, 0, 0),
            ValidationStatus.PENDING: QColor(255, 165, 0),
            ValidationStatus.MANUAL_REVIEW: QColor(0, 0, 200),
            ValidationStatus.UNKNOWN: QColor(128, 128, 128)
        }
        
        color = colors.get(status, QColor(128, 128, 128))
        self.status_indicator.setStyleSheet(f"background-color: {color.name()};")
        
    def get_value(self) -> ValidationStatus:
        """Get the current validation status."""
        return self._current_status
        
    def set_value(self, value: ValidationStatus):
        """Set the validation status."""
        if isinstance(value, ValidationStatus) and value != self._current_status:
            self._current_status = value
            index = self.status_combo.findData(value)
            if index >= 0:
                self.status_combo.setCurrentIndex(index)
            self._update_indicator()
            
    def _on_status_changed(self):
        """Handle status change."""
        new_status = self.status_combo.currentData()
        if new_status != self._current_status:
            self._current_status = new_status
            self._update_indicator()
            self.value_changed.emit(new_status)


class ConfidenceEditor(BasePropertyEditor):
    """Editor for confidence scores (0-100%)."""
    
    value_changed = pyqtSignal(float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_confidence = 0.0
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup the confidence editor UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Confidence slider
        self.confidence_slider = QSlider(Qt.Orientation.Horizontal)
        self.confidence_slider.setRange(0, 100)
        self.confidence_slider.setValue(0)
        self.confidence_slider.valueChanged.connect(self._on_slider_changed)
        layout.addWidget(self.confidence_slider)
        
        # Confidence spinbox
        self.confidence_spinbox = QSpinBox()
        self.confidence_spinbox.setRange(0, 100)
        self.confidence_spinbox.setSuffix("%")
        self.confidence_spinbox.setValue(0)
        self.confidence_spinbox.valueChanged.connect(self._on_spinbox_changed)
        layout.addWidget(self.confidence_spinbox)
        
    def get_value(self) -> float:
        """Get the current confidence value (0.0 to 1.0)."""
        return self._current_confidence
        
    def set_value(self, value: float):
        """Set the confidence value (0.0 to 1.0)."""
        if isinstance(value, (int, float)):
            # Clamp to valid range
            value = max(0.0, min(1.0, float(value)))
            if value != self._current_confidence:
                self._current_confidence = value
                percentage = int(value * 100)
                self.confidence_slider.setValue(percentage)
                self.confidence_spinbox.setValue(percentage)
                
    def _on_slider_changed(self, percentage: int):
        """Handle slider value change."""
        confidence = percentage / 100.0
        if confidence != self._current_confidence:
            self._current_confidence = confidence
            self.confidence_spinbox.setValue(percentage)
            self.value_changed.emit(confidence)
            
    def _on_spinbox_changed(self, percentage: int):
        """Handle spinbox value change."""
        confidence = percentage / 100.0
        if confidence != self._current_confidence:
            self._current_confidence = confidence
            self.confidence_slider.setValue(percentage)
            self.value_changed.emit(confidence)


class QualityMetricsEditor(BasePropertyEditor):
    """Editor for quality metrics."""
    
    value_changed = pyqtSignal(object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_metrics = {}
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup the quality metrics editor UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Overall quality
        overall_group = QGroupBox("Overall Quality")
        overall_layout = QVBoxLayout(overall_group)
        
        self.overall_progress = QProgressBar()
        self.overall_progress.setRange(0, 100)
        self.overall_progress.setValue(0)
        overall_layout.addWidget(self.overall_progress)
        
        layout.addWidget(overall_group)
        
        # Individual metrics
        metrics_group = QGroupBox("Metrics")
        metrics_layout = QVBoxLayout(metrics_group)
        
        # Accuracy
        accuracy_layout = QHBoxLayout()
        accuracy_layout.addWidget(QLabel("Accuracy:"))
        self.accuracy_slider = QSlider(Qt.Orientation.Horizontal)
        self.accuracy_slider.setRange(0, 100)
        self.accuracy_slider.valueChanged.connect(self._update_metrics)
        accuracy_layout.addWidget(self.accuracy_slider)
        self.accuracy_label = QLabel("0%")
        accuracy_layout.addWidget(self.accuracy_label)
        metrics_layout.addLayout(accuracy_layout)
        
        # Completeness
        completeness_layout = QHBoxLayout()
        completeness_layout.addWidget(QLabel("Completeness:"))
        self.completeness_slider = QSlider(Qt.Orientation.Horizontal)
        self.completeness_slider.setRange(0, 100)
        self.completeness_slider.valueChanged.connect(self._update_metrics)
        completeness_layout.addWidget(self.completeness_slider)
        self.completeness_label = QLabel("0%")
        completeness_layout.addWidget(self.completeness_label)
        metrics_layout.addLayout(completeness_layout)
        
        # Consistency
        consistency_layout = QHBoxLayout()
        consistency_layout.addWidget(QLabel("Consistency:"))
        self.consistency_slider = QSlider(Qt.Orientation.Horizontal)
        self.consistency_slider.setRange(0, 100)
        self.consistency_slider.valueChanged.connect(self._update_metrics)
        consistency_layout.addWidget(self.consistency_slider)
        self.consistency_label = QLabel("0%")
        consistency_layout.addWidget(self.consistency_label)
        metrics_layout.addLayout(consistency_layout)
        
        layout.addWidget(metrics_group)
        
        # Validation flags
        flags_group = QGroupBox("Validation Flags")
        flags_layout = QVBoxLayout(flags_group)
        
        self.human_verified_cb = QCheckBox("Human Verified")
        self.human_verified_cb.toggled.connect(self._update_metrics)
        flags_layout.addWidget(self.human_verified_cb)
        
        self.auto_validated_cb = QCheckBox("Auto Validated")
        self.auto_validated_cb.toggled.connect(self._update_metrics)
        flags_layout.addWidget(self.auto_validated_cb)
        
        self.requires_review_cb = QCheckBox("Requires Review")
        self.requires_review_cb.toggled.connect(self._update_metrics)
        flags_layout.addWidget(self.requires_review_cb)
        
        layout.addWidget(flags_group)
        
    def get_value(self) -> Dict[str, Any]:
        """Get the current quality metrics."""
        return self._current_metrics.copy()
        
    def set_value(self, value: Dict[str, Any]):
        """Set the quality metrics."""
        if isinstance(value, dict):
            self._current_metrics = value.copy()
            
            # Update UI elements
            accuracy = value.get('accuracy', 0) * 100
            self.accuracy_slider.setValue(int(accuracy))
            
            completeness = value.get('completeness', 0) * 100
            self.completeness_slider.setValue(int(completeness))
            
            consistency = value.get('consistency', 0) * 100
            self.consistency_slider.setValue(int(consistency))
            
            self.human_verified_cb.setChecked(value.get('human_verified', False))
            self.auto_validated_cb.setChecked(value.get('auto_validated', False))
            self.requires_review_cb.setChecked(value.get('requires_review', False))
            
            self._update_overall_quality()
            
    def _update_metrics(self):
        """Update the metrics from UI values."""
        self._current_metrics = {
            'accuracy': self.accuracy_slider.value() / 100.0,
            'completeness': self.completeness_slider.value() / 100.0,
            'consistency': self.consistency_slider.value() / 100.0,
            'human_verified': self.human_verified_cb.isChecked(),
            'auto_validated': self.auto_validated_cb.isChecked(),
            'requires_review': self.requires_review_cb.isChecked()
        }
        
        # Update labels
        self.accuracy_label.setText(f"{self.accuracy_slider.value()}%")
        self.completeness_label.setText(f"{self.completeness_slider.value()}%")
        self.consistency_label.setText(f"{self.consistency_slider.value()}%")
        
        self._update_overall_quality()
        self.value_changed.emit(self._current_metrics)
        
    def _update_overall_quality(self):
        """Update overall quality score."""
        accuracy = self._current_metrics.get('accuracy', 0)
        completeness = self._current_metrics.get('completeness', 0)
        consistency = self._current_metrics.get('consistency', 0)
        
        # Calculate weighted average
        overall = (accuracy * 0.4 + completeness * 0.3 + consistency * 0.3) * 100
        self.overall_progress.setValue(int(overall))


class ValidationResultEditor(BasePropertyEditor):
    """Complete validation result editor."""
    
    value_changed = pyqtSignal(object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_result = ValidationResult(is_valid=False)
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup the validation result editor UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Status and confidence
        top_layout = QHBoxLayout()
        
        # Status
        status_group = QGroupBox("Status")
        status_layout = QVBoxLayout(status_group)
        self.status_editor = ValidationStatusEditor()
        self.status_editor.value_changed.connect(self._on_status_changed)
        status_layout.addWidget(self.status_editor)
        top_layout.addWidget(status_group)
        
        # Confidence
        confidence_group = QGroupBox("Confidence")
        confidence_layout = QVBoxLayout(confidence_group)
        self.confidence_editor = ConfidenceEditor()
        self.confidence_editor.value_changed.connect(self._on_confidence_changed)
        confidence_layout.addWidget(self.confidence_editor)
        top_layout.addWidget(confidence_group)
        
        layout.addLayout(top_layout)
        
        # Quality metrics
        self.metrics_editor = QualityMetricsEditor()
        self.metrics_editor.value_changed.connect(self._on_metrics_changed)
        layout.addWidget(self.metrics_editor)
        
    def get_value(self) -> ValidationResult:
        """Get the current validation result."""
        return self._current_result
        
    def set_value(self, value: ValidationResult):
        """Set the validation result."""
        if isinstance(value, ValidationResult):
            self._current_result = value
            
            # Update sub-editors
            self.status_editor.set_value(value.status)
            self.confidence_editor.set_value(value.confidence)
            
            # Update metrics
            if value.metadata:
                self.metrics_editor.set_value(value.metadata)
                
    def _on_status_changed(self, status: ValidationStatus):
        """Handle status change."""
        self._current_result.status = status
        self._current_result.is_valid = (status == ValidationStatus.VALID)
        self.value_changed.emit(self._current_result)
        
    def _on_confidence_changed(self, confidence: float):
        """Handle confidence change."""
        self._current_result.confidence = confidence
        self.value_changed.emit(self._current_result)
        
    def _on_metrics_changed(self, metrics: Dict[str, Any]):
        """Handle metrics change."""
        if not self._current_result.metadata:
            self._current_result.metadata = {}
        self._current_result.metadata.update(metrics)
        self.value_changed.emit(self._current_result)


# Export validation editors
__all__ = [
    'ValidationStatus',
    'ValidationResult',
    'ValidationStatusEditor',
    'ConfidenceEditor',
    'QualityMetricsEditor',
    'ValidationResultEditor'
]