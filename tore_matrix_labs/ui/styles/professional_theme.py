"""
Professional theme for TORE Matrix Labs.
"""


class ProfessionalTheme:
    """Professional application theme."""
    
    def __init__(self):
        self.colors = {
            'primary': '#2C3E50',
            'secondary': '#34495E',
            'accent': '#3498DB',
            'background': '#ECF0F1',
            'text': '#2C3E50',
            'success': '#27AE60',
            'warning': '#F39C12',
            'error': '#E74C3C',
            'border': '#BDC3C7'
        }
    
    def get_stylesheet(self) -> str:
        """Get QSS stylesheet for the theme."""
        return f"""
        QMainWindow {{
            background-color: {self.colors['background']};
            color: {self.colors['text']};
        }}
        
        QWidget {{
            background-color: {self.colors['background']};
            color: {self.colors['text']};
        }}
        
        QPushButton {{
            background-color: {self.colors['primary']};
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: bold;
        }}
        
        QPushButton:hover {{
            background-color: {self.colors['secondary']};
        }}
        
        QPushButton:pressed {{
            background-color: {self.colors['accent']};
        }}
        
        QPushButton:disabled {{
            background-color: #95A5A6;
            color: #7F8C8D;
        }}
        
        QGroupBox {{
            font-weight: bold;
            border: 2px solid {self.colors['border']};
            border-radius: 8px;
            margin-top: 10px;
            padding-top: 10px;
        }}
        
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }}
        
        QTabWidget::pane {{
            border: 1px solid {self.colors['border']};
            background-color: white;
        }}
        
        QTabBar::tab {{
            background-color: {self.colors['background']};
            padding: 8px 16px;
            margin-right: 2px;
        }}
        
        QTabBar::tab:selected {{
            background-color: {self.colors['primary']};
            color: white;
        }}
        
        QStatusBar {{
            background-color: {self.colors['secondary']};
            color: white;
        }}
        
        QProgressBar {{
            border: 2px solid {self.colors['border']};
            border-radius: 5px;
            text-align: center;
        }}
        
        QProgressBar::chunk {{
            background-color: {self.colors['success']};
            width: 20px;
        }}
        
        QListWidget {{
            border: 1px solid {self.colors['border']};
            background-color: white;
            alternate-background-color: #F8F9FA;
        }}
        
        QTextEdit {{
            border: 1px solid {self.colors['border']};
            background-color: white;
        }}
        
        QLineEdit {{
            border: 1px solid {self.colors['border']};
            padding: 4px;
            border-radius: 4px;
        }}
        
        QComboBox {{
            border: 1px solid {self.colors['border']};
            padding: 4px;
            border-radius: 4px;
        }}
        
        QSpinBox, QDoubleSpinBox {{
            border: 1px solid {self.colors['border']};
            padding: 4px;
            border-radius: 4px;
        }}
        
        QCheckBox {{
            spacing: 5px;
        }}
        
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
        }}
        
        QCheckBox::indicator:unchecked {{
            border: 2px solid {self.colors['border']};
            background-color: white;
        }}
        
        QCheckBox::indicator:checked {{
            border: 2px solid {self.colors['success']};
            background-color: {self.colors['success']};
        }}
        """