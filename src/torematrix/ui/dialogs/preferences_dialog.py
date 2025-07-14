"""Preferences dialog for ToreMatrix V3."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTabWidget, QWidget, QFormLayout, QComboBox, QSpinBox,
    QCheckBox, QLineEdit, QGroupBox, QSlider, QColorDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

class PreferencesDialog(QDialog):
    """Comprehensive preferences dialog for application settings."""
    
    # Signals
    settings_changed = pyqtSignal(dict)  # settings_dict
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.setModal(True)
        self.resize(600, 500)
        
        # Settings storage
        self.settings = {}
        
        self.setup_ui()
        self.load_default_settings()
    
    def setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        
        # Tabs for different preference categories
        self.tabs = QTabWidget()
        
        self.setup_general_tab()
        self.setup_appearance_tab()
        self.setup_performance_tab()
        self.setup_advanced_tab()
        
        layout.addWidget(self.tabs)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.defaults_button = QPushButton("Restore Defaults")
        self.defaults_button.clicked.connect(self.restore_defaults)
        
        button_layout.addWidget(self.defaults_button)
        button_layout.addStretch()
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        self.apply_button = QPushButton("Apply")
        self.apply_button.clicked.connect(self.apply_settings)
        
        self.ok_button = QPushButton("OK")
        self.ok_button.setDefault(True)
        self.ok_button.clicked.connect(self.accept_settings)
        
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.apply_button)
        button_layout.addWidget(self.ok_button)
        
        layout.addLayout(button_layout)
    
    def setup_general_tab(self):
        """Setup general preferences tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Application settings
        app_group = QGroupBox("Application")
        app_layout = QFormLayout(app_group)
        
        self.startup_option = QComboBox()
        self.startup_option.addItems(["Show splash screen", "Show main window", "Restore session"])
        app_layout.addRow("Startup behavior:", self.startup_option)
        
        self.auto_save = QCheckBox("Enable auto-save")
        app_layout.addRow(self.auto_save)
        
        self.auto_save_interval = QSpinBox()
        self.auto_save_interval.setRange(1, 60)
        self.auto_save_interval.setSuffix(" minutes")
        app_layout.addRow("Auto-save interval:", self.auto_save_interval)
        
        layout.addWidget(app_group)
        
        # File handling
        file_group = QGroupBox("File Handling")
        file_layout = QFormLayout(file_group)
        
        self.default_export_format = QComboBox()
        self.default_export_format.addItems(["JSON", "XML", "CSV", "PDF", "HTML"])
        file_layout.addRow("Default export format:", self.default_export_format)
        
        self.max_recent_files = QSpinBox()
        self.max_recent_files.setRange(5, 50)
        file_layout.addRow("Recent files count:", self.max_recent_files)
        
        layout.addWidget(file_group)
        layout.addStretch()
        
        self.tabs.addTab(widget, "General")
    
    def setup_appearance_tab(self):
        """Setup appearance preferences tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Theme settings
        theme_group = QGroupBox("Theme")
        theme_layout = QFormLayout(theme_group)
        
        self.theme_option = QComboBox()
        self.theme_option.addItems(["Light", "Dark", "Auto"])
        theme_layout.addRow("Theme:", self.theme_option)
        
        self.accent_color_button = QPushButton("Choose Accent Color")
        self.accent_color_button.clicked.connect(self.choose_accent_color)
        theme_layout.addRow("Accent color:", self.accent_color_button)
        
        layout.addWidget(theme_group)
        
        # Font settings
        font_group = QGroupBox("Fonts")
        font_layout = QFormLayout(font_group)
        
        self.ui_font_size = QSpinBox()
        self.ui_font_size.setRange(8, 24)
        self.ui_font_size.setSuffix(" pt")
        font_layout.addRow("UI font size:", self.ui_font_size)
        
        self.editor_font_size = QSpinBox()
        self.editor_font_size.setRange(8, 24)
        self.editor_font_size.setSuffix(" pt")
        font_layout.addRow("Editor font size:", self.editor_font_size)
        
        layout.addWidget(font_group)
        
        # UI settings
        ui_group = QGroupBox("Interface")
        ui_layout = QFormLayout(ui_group)
        
        self.show_tooltips = QCheckBox("Show tooltips")
        ui_layout.addRow(self.show_tooltips)
        
        self.show_status_bar = QCheckBox("Show status bar")
        ui_layout.addRow(self.show_status_bar)
        
        self.animate_ui = QCheckBox("Enable UI animations")
        ui_layout.addRow(self.animate_ui)
        
        layout.addWidget(ui_group)
        layout.addStretch()
        
        self.tabs.addTab(widget, "Appearance")
    
    def setup_performance_tab(self):
        """Setup performance preferences tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Processing settings
        processing_group = QGroupBox("Processing")
        processing_layout = QFormLayout(processing_group)
        
        self.worker_threads = QSpinBox()
        self.worker_threads.setRange(1, 16)
        processing_layout.addRow("Worker threads:", self.worker_threads)
        
        self.batch_size = QSpinBox()
        self.batch_size.setRange(10, 1000)
        processing_layout.addRow("Batch size:", self.batch_size)
        
        self.enable_parallel_processing = QCheckBox("Enable parallel processing")
        processing_layout.addRow(self.enable_parallel_processing)
        
        layout.addWidget(processing_group)
        
        # Memory settings
        memory_group = QGroupBox("Memory")
        memory_layout = QFormLayout(memory_group)
        
        self.cache_size = QSlider(Qt.Orientation.Horizontal)
        self.cache_size.setRange(64, 2048)
        self.cache_size_label = QLabel("512 MB")
        self.cache_size.valueChanged.connect(
            lambda v: self.cache_size_label.setText(f"{v} MB")
        )
        cache_layout = QHBoxLayout()
        cache_layout.addWidget(self.cache_size)
        cache_layout.addWidget(self.cache_size_label)
        memory_layout.addRow("Cache size:", cache_layout)
        
        self.auto_cleanup = QCheckBox("Automatic memory cleanup")
        memory_layout.addRow(self.auto_cleanup)
        
        layout.addWidget(memory_group)
        layout.addStretch()
        
        self.tabs.addTab(widget, "Performance")
    
    def setup_advanced_tab(self):
        """Setup advanced preferences tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Debug settings
        debug_group = QGroupBox("Debug")
        debug_layout = QFormLayout(debug_group)
        
        self.log_level = QComboBox()
        self.log_level.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        debug_layout.addRow("Log level:", self.log_level)
        
        self.enable_profiling = QCheckBox("Enable profiling")
        debug_layout.addRow(self.enable_profiling)
        
        self.debug_mode = QCheckBox("Debug mode")
        debug_layout.addRow(self.debug_mode)
        
        layout.addWidget(debug_group)
        
        # Network settings
        network_group = QGroupBox("Network")
        network_layout = QFormLayout(network_group)
        
        self.proxy_host = QLineEdit()
        network_layout.addRow("Proxy host:", self.proxy_host)
        
        self.proxy_port = QSpinBox()
        self.proxy_port.setRange(1, 65535)
        network_layout.addRow("Proxy port:", self.proxy_port)
        
        self.timeout = QSpinBox()
        self.timeout.setRange(5, 300)
        self.timeout.setSuffix(" seconds")
        network_layout.addRow("Request timeout:", self.timeout)
        
        layout.addWidget(network_group)
        layout.addStretch()
        
        self.tabs.addTab(widget, "Advanced")
    
    def load_default_settings(self):
        """Load default settings values."""
        defaults = {
            # General
            'startup_option': 0,
            'auto_save': True,
            'auto_save_interval': 5,
            'default_export_format': 0,
            'max_recent_files': 10,
            
            # Appearance
            'theme_option': 0,
            'accent_color': '#0e639c',
            'ui_font_size': 10,
            'editor_font_size': 11,
            'show_tooltips': True,
            'show_status_bar': True,
            'animate_ui': True,
            
            # Performance
            'worker_threads': 4,
            'batch_size': 100,
            'enable_parallel_processing': True,
            'cache_size': 512,
            'auto_cleanup': True,
            
            # Advanced
            'log_level': 1,  # INFO
            'enable_profiling': False,
            'debug_mode': False,
            'proxy_host': '',
            'proxy_port': 8080,
            'timeout': 30
        }
        
        self.apply_settings_to_ui(defaults)
        self.settings = defaults.copy()
    
    def apply_settings_to_ui(self, settings):
        """Apply settings dictionary to UI controls."""
        # General
        self.startup_option.setCurrentIndex(settings.get('startup_option', 0))
        self.auto_save.setChecked(settings.get('auto_save', True))
        self.auto_save_interval.setValue(settings.get('auto_save_interval', 5))
        self.default_export_format.setCurrentIndex(settings.get('default_export_format', 0))
        self.max_recent_files.setValue(settings.get('max_recent_files', 10))
        
        # Appearance
        self.theme_option.setCurrentIndex(settings.get('theme_option', 0))
        self.ui_font_size.setValue(settings.get('ui_font_size', 10))
        self.editor_font_size.setValue(settings.get('editor_font_size', 11))
        self.show_tooltips.setChecked(settings.get('show_tooltips', True))
        self.show_status_bar.setChecked(settings.get('show_status_bar', True))
        self.animate_ui.setChecked(settings.get('animate_ui', True))
        
        # Performance
        self.worker_threads.setValue(settings.get('worker_threads', 4))
        self.batch_size.setValue(settings.get('batch_size', 100))
        self.enable_parallel_processing.setChecked(settings.get('enable_parallel_processing', True))
        self.cache_size.setValue(settings.get('cache_size', 512))
        self.auto_cleanup.setChecked(settings.get('auto_cleanup', True))
        
        # Advanced
        self.log_level.setCurrentIndex(settings.get('log_level', 1))
        self.enable_profiling.setChecked(settings.get('enable_profiling', False))
        self.debug_mode.setChecked(settings.get('debug_mode', False))
        self.proxy_host.setText(settings.get('proxy_host', ''))
        self.proxy_port.setValue(settings.get('proxy_port', 8080))
        self.timeout.setValue(settings.get('timeout', 30))
    
    def collect_settings_from_ui(self):
        """Collect current settings from UI controls."""
        return {
            # General
            'startup_option': self.startup_option.currentIndex(),
            'auto_save': self.auto_save.isChecked(),
            'auto_save_interval': self.auto_save_interval.value(),
            'default_export_format': self.default_export_format.currentIndex(),
            'max_recent_files': self.max_recent_files.value(),
            
            # Appearance
            'theme_option': self.theme_option.currentIndex(),
            'accent_color': getattr(self, '_accent_color', '#0e639c'),
            'ui_font_size': self.ui_font_size.value(),
            'editor_font_size': self.editor_font_size.value(),
            'show_tooltips': self.show_tooltips.isChecked(),
            'show_status_bar': self.show_status_bar.isChecked(),
            'animate_ui': self.animate_ui.isChecked(),
            
            # Performance
            'worker_threads': self.worker_threads.value(),
            'batch_size': self.batch_size.value(),
            'enable_parallel_processing': self.enable_parallel_processing.isChecked(),
            'cache_size': self.cache_size.value(),
            'auto_cleanup': self.auto_cleanup.isChecked(),
            
            # Advanced
            'log_level': self.log_level.currentIndex(),
            'enable_profiling': self.enable_profiling.isChecked(),
            'debug_mode': self.debug_mode.isChecked(),
            'proxy_host': self.proxy_host.text(),
            'proxy_port': self.proxy_port.value(),
            'timeout': self.timeout.value()
        }
    
    def choose_accent_color(self):
        """Open color dialog to choose accent color."""
        current_color = QColor(getattr(self, '_accent_color', '#0e639c'))
        color = QColorDialog.getColor(current_color, self, "Choose Accent Color")
        
        if color.isValid():
            self._accent_color = color.name()
            self.accent_color_button.setStyleSheet(
                f"background-color: {color.name()}; color: white;"
            )
    
    def restore_defaults(self):
        """Restore default settings."""
        self.load_default_settings()
    
    def apply_settings(self):
        """Apply current settings without closing dialog."""
        self.settings = self.collect_settings_from_ui()
        self.settings_changed.emit(self.settings)
    
    def accept_settings(self):
        """Accept and apply settings."""
        self.apply_settings()
        self.accept()
    
    def get_settings(self):
        """Get current settings dictionary."""
        return self.settings.copy()