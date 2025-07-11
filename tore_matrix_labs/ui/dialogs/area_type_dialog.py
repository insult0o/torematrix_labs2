"""
Area Type Selection Dialog for TORE Matrix Labs

Dialog for selecting the type of area during visual selection.
"""

import logging
from typing import Optional

from ..qt_compat import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QButtonGroup, QFrame, Qt, QFont, QIcon, QPixmap
)

from ...models.visual_area_models import AreaType


class AreaTypeDialog(QDialog):
    """Dialog for selecting area type with color preview."""
    
    AREA_TYPES = {
        AreaType.IMAGE: {
            "color": "#FF4444", 
            "name": "Image", 
            "description": "Photographs, illustrations, graphics",
            "icon": "🖼️"
        },
        AreaType.TABLE: {
            "color": "#44FF44", 
            "name": "Table", 
            "description": "Data tables, spreadsheets, grids",
            "icon": "📊"
        },
        AreaType.DIAGRAM: {
            "color": "#4444FF", 
            "name": "Diagram", 
            "description": "Charts, flowcharts, technical drawings",
            "icon": "📈"
        },
        AreaType.TEXT: {
            "color": "#FFFF44", 
            "name": "Text Block", 
            "description": "Special text areas, callouts, notes",
            "icon": "📝"
        },
        AreaType.CUSTOM: {
            "color": "#FF44FF", 
            "name": "Custom Area", 
            "description": "Other special content areas",
            "icon": "⭐"
        }
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_type: Optional[AreaType] = None
        self.logger = logging.getLogger(__name__)
        
        self._setup_ui()
        self._setup_connections()
        
        # Set dialog properties
        self.setModal(True)
        self.setWindowTitle("Select Area Type")
        self.resize(400, 300)
        
    def _setup_ui(self):
        """Create the user interface."""
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("Select the type of content in this area:")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Add spacing
        layout.addSpacing(20)
        
        # Button group for exclusive selection
        self.button_group = QButtonGroup(self)
        
        # Create buttons for each area type
        for area_type, type_data in self.AREA_TYPES.items():
            button = self._create_type_button(area_type, type_data)
            layout.addWidget(button)
            self.button_group.addButton(button)
            
        # Add spacing
        layout.addSpacing(20)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        button_layout.addStretch()
        
        self.ok_btn = QPushButton("Select")
        self.ok_btn.clicked.connect(self.accept)
        self.ok_btn.setEnabled(False)  # Disabled until selection made
        self.ok_btn.setDefault(True)
        button_layout.addWidget(self.ok_btn)
        
        layout.addLayout(button_layout)
        
    def _create_type_button(self, area_type: AreaType, type_data: dict) -> QPushButton:
        """Create a button for an area type."""
        button = QPushButton()
        button.setCheckable(True)
        button.setMinimumHeight(60)
        
        # Create button text with icon and description
        icon = type_data["icon"]
        name = type_data["name"]
        description = type_data["description"]
        color = type_data["color"]
        
        button.setText(f"{icon} {name}\n{description}")
        
        # Set button style with type color
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: white;
                border: 2px solid {color};
                border-radius: 8px;
                padding: 10px;
                text-align: left;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {color}20;
            }}
            QPushButton:checked {{
                background-color: {color};
                color: white;
                font-weight: bold;
            }}
        """)
        
        # Store area type in button
        button.area_type = area_type
        
        return button
        
    def _setup_connections(self):
        """Setup signal connections."""
        self.button_group.buttonClicked.connect(self._on_button_clicked)
        
    def _on_button_clicked(self, button):
        """Handle area type button click."""
        if hasattr(button, 'area_type'):
            self.selected_type = button.area_type
            self.ok_btn.setEnabled(True)
            
            type_data = self.AREA_TYPES[self.selected_type]
            self.logger.info(f"Selected area type: {type_data['name']}")
            
    def get_selected_type(self) -> Optional[AreaType]:
        """Get the selected area type."""
        return self.selected_type