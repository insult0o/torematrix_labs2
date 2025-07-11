#!/usr/bin/env python3
"""
Highlight Style for TORE Matrix Labs Highlighting System
Defines visual appearance of highlights with improved colors and accessibility.
"""

import logging
from typing import Dict, Any
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QTextCharFormat


class HighlightStyle:
    """Defines visual appearance of highlights with improved colors and accessibility."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # New color scheme - pure yellow backgrounds, no outlines
        self.COLORS = {
            'active_highlight': {
                'background': QColor(255, 255, 0, 180),  # Pure yellow with transparency
                'foreground': QColor(0, 0, 0),           # Black text for readability
                'border': None,                          # No outline
                'opacity': 0.7
            },
            'inactive_highlight': {
                'background': QColor(255, 255, 136, 100), # Light yellow
                'foreground': QColor(0, 0, 0),            # Black text
                'border': None,                           # No outline
                'opacity': 0.4
            },
            'cursor_highlight': {
                'background': QColor(255, 215, 0, 200),   # Gold
                'foreground': QColor(0, 0, 0),            # Black text
                'border': None,                           # No outline
                'opacity': 0.8
            },
            'error_highlight': {
                'background': QColor(255, 200, 200, 150), # Light red
                'foreground': QColor(150, 0, 0),          # Dark red text
                'border': None,                           # No outline
                'opacity': 0.6
            },
            'success_highlight': {
                'background': QColor(200, 255, 200, 150), # Light green
                'foreground': QColor(0, 100, 0),          # Dark green text
                'border': None,                           # No outline
                'opacity': 0.6
            },
            'warning_highlight': {
                'background': QColor(255, 235, 155, 150), # Light orange
                'foreground': QColor(100, 60, 0),         # Dark brown text
                'border': None,                           # No outline
                'opacity': 0.6
            }
        }
        
        # PDF-specific colors (converted to hex for PDF rendering)
        self.PDF_COLORS = {
            'active_highlight': {
                'background_color': '#FFFF00',  # Pure yellow
                'opacity': 0.7,
                'border_color': None,
                'border_width': 0
            },
            'inactive_highlight': {
                'background_color': '#FFFF88',  # Light yellow
                'opacity': 0.4,
                'border_color': None,
                'border_width': 0
            },
            'cursor_highlight': {
                'background_color': '#FFD700',  # Gold
                'opacity': 0.8,
                'border_color': None,
                'border_width': 0
            },
            'error_highlight': {
                'background_color': '#FFC8C8',  # Light red
                'opacity': 0.6,
                'border_color': None,
                'border_width': 0
            },
            'success_highlight': {
                'background_color': '#C8FFC8',  # Light green
                'opacity': 0.6,
                'border_color': None,
                'border_width': 0
            },
            'warning_highlight': {
                'background_color': '#FFEB9B',  # Light orange
                'opacity': 0.6,
                'border_color': None,
                'border_width': 0
            }
        }
        
        # Text formatting options
        self.TEXT_FORMATS = {
            'active_highlight': {
                'bold': False,
                'italic': False,
                'underline': False
            },
            'inactive_highlight': {
                'bold': False,
                'italic': False,
                'underline': False
            },
            'cursor_highlight': {
                'bold': False,
                'italic': False,
                'underline': False
            },
            'error_highlight': {
                'bold': True,
                'italic': False,
                'underline': False
            },
            'success_highlight': {
                'bold': False,
                'italic': False,
                'underline': False
            },
            'warning_highlight': {
                'bold': False,
                'italic': False,
                'underline': False
            }
        }
        
        self.logger.info("Highlight style initialized with pure yellow color scheme")
    
    def get_text_format(self, highlight_type: str) -> QTextCharFormat:
        """Get QTextCharFormat for text widget highlighting."""
        try:
            if highlight_type not in self.COLORS:
                highlight_type = 'active_highlight'
            
            color_config = self.COLORS[highlight_type]
            format_config = self.TEXT_FORMATS[highlight_type]
            
            # Create text format
            text_format = QTextCharFormat()
            
            # Set background color
            text_format.setBackground(color_config['background'])
            
            # Set foreground color
            if color_config['foreground']:
                text_format.setForeground(color_config['foreground'])
            
            # Set text formatting
            if format_config['bold']:
                text_format.setFontWeight(700)
            else:
                text_format.setFontWeight(400)
            
            if format_config['italic']:
                text_format.setFontItalic(True)
            
            if format_config['underline']:
                text_format.setUnderlineStyle(QTextCharFormat.SingleUnderline)
            
            return text_format
            
        except Exception as e:
            self.logger.error(f"HIGHLIGHT_STYLE: Error creating text format: {e}")
            # Return default format
            default_format = QTextCharFormat()
            default_format.setBackground(QColor(255, 255, 0, 180))
            return default_format
    
    def get_pdf_style(self, highlight_type: str) -> Dict[str, Any]:
        """Get style configuration for PDF highlighting."""
        try:
            if highlight_type not in self.PDF_COLORS:
                highlight_type = 'active_highlight'
            
            return self.PDF_COLORS[highlight_type].copy()
            
        except Exception as e:
            self.logger.error(f"HIGHLIGHT_STYLE: Error getting PDF style: {e}")
            # Return default style
            return {
                'background_color': '#FFFF00',
                'opacity': 0.7,
                'border_color': None,
                'border_width': 0
            }
    
    def get_cursor_color(self) -> str:
        """Get cursor highlight color."""
        return self.PDF_COLORS['cursor_highlight']['background_color']
    
    def get_color_for_type(self, highlight_type: str) -> QColor:
        """Get QColor for a specific highlight type."""
        try:
            if highlight_type not in self.COLORS:
                highlight_type = 'active_highlight'
            
            return self.COLORS[highlight_type]['background']
            
        except Exception as e:
            self.logger.error(f"HIGHLIGHT_STYLE: Error getting color: {e}")
            return QColor(255, 255, 0, 180)  # Default yellow
    
    def create_custom_style(self, background_color: str, opacity: float = 0.7, 
                          foreground_color: str = '#000000', 
                          bold: bool = False, italic: bool = False, 
                          underline: bool = False) -> Dict[str, Any]:
        """Create a custom highlight style."""
        try:
            # Parse colors
            bg_color = QColor(background_color)
            fg_color = QColor(foreground_color)
            
            # Set opacity
            bg_color.setAlphaF(opacity)
            
            # Create style configuration
            style = {
                'text_format': {
                    'background': bg_color,
                    'foreground': fg_color,
                    'bold': bold,
                    'italic': italic,
                    'underline': underline
                },
                'pdf_style': {
                    'background_color': background_color,
                    'opacity': opacity,
                    'border_color': None,
                    'border_width': 0
                }
            }
            
            return style
            
        except Exception as e:
            self.logger.error(f"HIGHLIGHT_STYLE: Error creating custom style: {e}")
            return None
    
    def update_color_scheme(self, new_colors: Dict[str, Dict[str, Any]]):
        """Update the color scheme with new colors."""
        try:
            for highlight_type, color_config in new_colors.items():
                if highlight_type in self.COLORS:
                    self.COLORS[highlight_type].update(color_config)
                    
                    # Update PDF colors if hex colors provided
                    if 'background_hex' in color_config:
                        if highlight_type in self.PDF_COLORS:
                            self.PDF_COLORS[highlight_type]['background_color'] = color_config['background_hex']
            
            self.logger.info("HIGHLIGHT_STYLE: Color scheme updated")
            
        except Exception as e:
            self.logger.error(f"HIGHLIGHT_STYLE: Error updating color scheme: {e}")
    
    def get_accessibility_compliant_colors(self) -> Dict[str, Dict[str, Any]]:
        """Get accessibility-compliant color scheme."""
        # High contrast colors for accessibility
        return {
            'active_highlight': {
                'background': QColor(255, 255, 0, 200),  # Bright yellow
                'foreground': QColor(0, 0, 0),           # Black text
                'background_hex': '#FFFF00',
                'opacity': 0.8
            },
            'inactive_highlight': {
                'background': QColor(255, 255, 200, 150), # Very light yellow
                'foreground': QColor(0, 0, 0),            # Black text
                'background_hex': '#FFFFC8',
                'opacity': 0.6
            },
            'cursor_highlight': {
                'background': QColor(255, 215, 0, 220),   # Gold
                'foreground': QColor(0, 0, 0),            # Black text
                'background_hex': '#FFD700',
                'opacity': 0.9
            },
            'error_highlight': {
                'background': QColor(255, 150, 150, 180), # Light red
                'foreground': QColor(100, 0, 0),          # Dark red text
                'background_hex': '#FF9696',
                'opacity': 0.7
            },
            'success_highlight': {
                'background': QColor(150, 255, 150, 180), # Light green
                'foreground': QColor(0, 80, 0),           # Dark green text
                'background_hex': '#96FF96',
                'opacity': 0.7
            },
            'warning_highlight': {
                'background': QColor(255, 220, 120, 180), # Light orange
                'foreground': QColor(80, 40, 0),          # Dark brown text
                'background_hex': '#FFDC78',
                'opacity': 0.7
            }
        }
    
    def enable_accessibility_mode(self):
        """Enable accessibility-compliant colors."""
        try:
            accessible_colors = self.get_accessibility_compliant_colors()
            
            # Update text colors
            for highlight_type, color_config in accessible_colors.items():
                if highlight_type in self.COLORS:
                    self.COLORS[highlight_type]['background'] = color_config['background']
                    self.COLORS[highlight_type]['foreground'] = color_config['foreground']
                    self.COLORS[highlight_type]['opacity'] = color_config['opacity']
                
                # Update PDF colors
                if highlight_type in self.PDF_COLORS:
                    self.PDF_COLORS[highlight_type]['background_color'] = color_config['background_hex']
                    self.PDF_COLORS[highlight_type]['opacity'] = color_config['opacity']
            
            self.logger.info("HIGHLIGHT_STYLE: Accessibility mode enabled")
            
        except Exception as e:
            self.logger.error(f"HIGHLIGHT_STYLE: Error enabling accessibility mode: {e}")
    
    def get_style_info(self) -> Dict[str, Any]:
        """Get information about current style configuration."""
        return {
            'available_types': list(self.COLORS.keys()),
            'color_scheme': 'pure_yellow',
            'accessibility_mode': False,
            'border_enabled': False,
            'opacity_range': (0.0, 1.0),
            'default_opacity': 0.7
        }