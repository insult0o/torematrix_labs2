#!/usr/bin/env python3
"""
Project Manager V2 for TORE Matrix Labs V2

A simplified project management interface that consolidates project
functionality from the original codebase.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLabel, 
    QPushButton, QListWidget, QFrame, QSplitter, QListWidgetItem
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from typing import Optional, Dict, Any, List
import logging

from ..services.event_bus import EventBus, EventType
from ..services.ui_state_manager import UIStateManager


class ProjectManagerV2(QWidget):
    """Project manager for V2 system."""
    
    # Signals
    project_selected = pyqtSignal(dict)
    project_created = pyqtSignal(dict)
    project_deleted = pyqtSignal(str)
    
    def __init__(self, 
                 event_bus: EventBus,
                 state_manager: UIStateManager,
                 parent: Optional[QWidget] = None):
        """Initialize the project manager."""
        super().__init__(parent)
        
        self.event_bus = event_bus
        self.state_manager = state_manager
        self.logger = logging.getLogger(__name__)
        
        self.current_project = None
        self.projects = []
        
        self._setup_ui()
        self._setup_events()
        self._load_sample_projects()
        
        self.logger.info("Project manager V2 initialized")
    
    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Project Manager")
        title_label.setFont(QFont("", 14, QFont.Bold))
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Project controls
        self.new_project_btn = QPushButton("New Project")
        self.new_project_btn.clicked.connect(self._create_project)
        header_layout.addWidget(self.new_project_btn)
        
        self.open_project_btn = QPushButton("Open Project")
        self.open_project_btn.clicked.connect(self._open_project)
        header_layout.addWidget(self.open_project_btn)
        
        layout.addLayout(header_layout)
        
        # Main content area
        main_splitter = QSplitter(Qt.Horizontal)
        
        # Left side - Project list
        projects_panel = self._create_projects_panel()
        main_splitter.addWidget(projects_panel)
        
        # Right side - Project details
        details_panel = self._create_details_panel()
        main_splitter.addWidget(details_panel)
        
        # Set splitter proportions
        main_splitter.setSizes([400, 600])
        layout.addWidget(main_splitter)
    
    def _create_projects_panel(self) -> QWidget:
        """Create the projects list panel."""
        panel = QFrame()
        panel.setFrameStyle(QFrame.StyledPanel)
        layout = QVBoxLayout(panel)
        
        # Panel header
        projects_label = QLabel("Recent Projects")
        projects_label.setFont(QFont("", 12, QFont.Bold))
        layout.addWidget(projects_label)
        
        # Projects list
        self.projects_list = QListWidget()
        self.projects_list.itemClicked.connect(self._on_project_selected)
        layout.addWidget(self.projects_list)
        
        # Project actions
        actions_layout = QHBoxLayout()
        
        self.delete_project_btn = QPushButton("Delete")
        self.delete_project_btn.clicked.connect(self._delete_project)
        self.delete_project_btn.setEnabled(False)
        actions_layout.addWidget(self.delete_project_btn)
        
        actions_layout.addStretch()
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._refresh_projects)
        actions_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(actions_layout)
        
        return panel
    
    def _create_details_panel(self) -> QWidget:
        """Create the project details panel."""
        panel = QFrame()
        panel.setFrameStyle(QFrame.StyledPanel)
        layout = QVBoxLayout(panel)
        
        # Panel header
        details_label = QLabel("Project Details")
        details_label.setFont(QFont("", 12, QFont.Bold))
        layout.addWidget(details_label)
        
        # Project info
        self.project_info_display = QTextEdit()
        self.project_info_display.setReadOnly(True)
        self.project_info_display.setMaximumHeight(200)
        self.project_info_display.setPlaceholderText("Select a project to view details...")
        layout.addWidget(self.project_info_display)
        
        # Documents section
        documents_label = QLabel("Documents")
        documents_label.setFont(QFont("", 11, QFont.Bold))
        layout.addWidget(documents_label)
        
        self.documents_display = QTextEdit()
        self.documents_display.setReadOnly(True)
        self.documents_display.setPlaceholderText("No documents in selected project...")
        layout.addWidget(self.documents_display)
        
        # Project actions
        project_actions_layout = QHBoxLayout()
        
        self.import_docs_btn = QPushButton("Import Documents")
        self.import_docs_btn.clicked.connect(self._import_documents)
        self.import_docs_btn.setEnabled(False)
        project_actions_layout.addWidget(self.import_docs_btn)
        
        self.export_project_btn = QPushButton("Export Project")
        self.export_project_btn.clicked.connect(self._export_project)
        self.export_project_btn.setEnabled(False)
        project_actions_layout.addWidget(self.export_project_btn)
        
        project_actions_layout.addStretch()
        
        layout.addLayout(project_actions_layout)
        
        return panel
    
    def _setup_events(self):
        """Set up event handlers."""
        self.event_bus.subscribe(
            EventType.PROJECT_CREATED,
            self._handle_project_created
        )
        
        self.event_bus.subscribe(
            EventType.PROJECT_LOADED,
            self._handle_project_loaded
        )
        
        self.event_bus.subscribe(
            EventType.PROJECT_SAVED,
            self._handle_project_saved
        )
    
    def _load_sample_projects(self):
        """Load sample projects for demonstration."""
        sample_projects = [
            {
                "id": "project_001",
                "name": "Aviation Manual Analysis",
                "description": "Analysis of ICAO aviation procedures manual",
                "created_at": "2025-01-15T10:30:00",
                "document_count": 12,
                "status": "active",
                "documents": [
                    {"name": "ICAO_Procedures.pdf", "pages": 54, "status": "processed"},
                    {"name": "Safety_Guidelines.docx", "pages": 23, "status": "validated"},
                    {"name": "Training_Manual.pdf", "pages": 87, "status": "processing"}
                ]
            },
            {
                "id": "project_002", 
                "name": "Technical Documentation Review",
                "description": "Review of technical documentation for compliance",
                "created_at": "2025-02-01T14:15:00",
                "document_count": 8,
                "status": "completed",
                "documents": [
                    {"name": "Tech_Spec_v2.pdf", "pages": 45, "status": "completed"},
                    {"name": "User_Manual.docx", "pages": 32, "status": "completed"}
                ]
            },
            {
                "id": "project_003",
                "name": "Regulatory Compliance Check",
                "description": "Checking documents for regulatory compliance",
                "created_at": "2025-02-10T09:00:00", 
                "document_count": 5,
                "status": "in_progress",
                "documents": [
                    {"name": "Regulations_2025.pdf", "pages": 76, "status": "validating"}
                ]
            }
        ]
        
        self.projects = sample_projects
        self._update_projects_list()
    
    def _update_projects_list(self):
        """Update the projects list display."""
        self.projects_list.clear()
        
        for project in self.projects:
            project_name = project.get("name", "Unknown Project")
            status = project.get("status", "unknown")
            doc_count = project.get("document_count", 0)
            
            item_text = f"{project_name} ({status}) - {doc_count} docs"
            
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, project)
            self.projects_list.addItem(item)
    
    def _on_project_selected(self, item: QListWidgetItem):
        """Handle project selection."""
        project_data = item.data(Qt.UserRole)
        if project_data:
            self.current_project = project_data
            self._update_project_details()
            
            # Enable project-specific buttons
            self.delete_project_btn.setEnabled(True)
            self.import_docs_btn.setEnabled(True)
            self.export_project_btn.setEnabled(True)
            
            # Emit signal
            self.project_selected.emit(project_data)
            
            self.logger.info(f"Project selected: {project_data.get('name')}")
    
    def _update_project_details(self):
        """Update the project details display."""
        if not self.current_project:
            return
        
        project = self.current_project
        
        # Update project info
        info_text = f"""Project Information:

Name: {project.get('name', 'Unknown')}
Description: {project.get('description', 'No description')}
Status: {project.get('status', 'unknown')}
Created: {project.get('created_at', 'unknown')}
Document Count: {project.get('document_count', 0)}
Project ID: {project.get('id', 'unknown')}
        """
        
        self.project_info_display.setText(info_text)
        
        # Update documents list
        documents = project.get("documents", [])
        if documents:
            docs_text = "Documents in Project:\n\n"
            for i, doc in enumerate(documents, 1):
                doc_name = doc.get("name", "Unknown Document")
                doc_pages = doc.get("pages", 0)
                doc_status = doc.get("status", "unknown")
                
                docs_text += f"{i}. {doc_name}\n"
                docs_text += f"   Pages: {doc_pages}, Status: {doc_status}\n\n"
        else:
            docs_text = "No documents in this project yet."
        
        self.documents_display.setText(docs_text)
    
    def _create_project(self):
        """Create a new project."""
        # In a real implementation, this would open a dialog
        new_project = {
            "id": f"project_{len(self.projects) + 1:03d}",
            "name": f"New Project {len(self.projects) + 1}",
            "description": "A new project created in TORE Matrix Labs V2",
            "created_at": "2025-07-10T19:30:00",
            "document_count": 0,
            "status": "new",
            "documents": []
        }
        
        self.projects.append(new_project)
        self._update_projects_list()
        
        # Emit signal
        self.project_created.emit(new_project)
        
        self.logger.info(f"New project created: {new_project['name']}")
    
    def _open_project(self):
        """Open an existing project file."""
        # In a real implementation, this would open a file dialog
        self.logger.info("Open project dialog would appear here")
        
        # Publish event
        self.event_bus.publish(
            EventType.PROJECT_LOADED,
            sender="project_manager",
            data={"action": "open_project_dialog"}
        )
    
    def _delete_project(self):
        """Delete the selected project."""
        if not self.current_project:
            return
        
        project_id = self.current_project.get("id")
        project_name = self.current_project.get("name", "Unknown")
        
        # Remove from list
        self.projects = [p for p in self.projects if p.get("id") != project_id]
        self._update_projects_list()
        
        # Clear details
        self.current_project = None
        self.project_info_display.clear()
        self.documents_display.clear()
        
        # Disable buttons
        self.delete_project_btn.setEnabled(False)
        self.import_docs_btn.setEnabled(False)
        self.export_project_btn.setEnabled(False)
        
        # Emit signal
        self.project_deleted.emit(project_id)
        
        self.logger.info(f"Project deleted: {project_name}")
    
    def _refresh_projects(self):
        """Refresh the projects list."""
        self._update_projects_list()
        self.logger.info("Projects list refreshed")
    
    def _import_documents(self):
        """Import documents into the current project."""
        if not self.current_project:
            return
        
        # In a real implementation, this would open file dialogs
        self.logger.info("Import documents dialog would appear here")
        
        # Publish event
        self.event_bus.publish(
            EventType.DOCUMENT_LOADED,
            sender="project_manager",
            data={"project_id": self.current_project.get("id")}
        )
    
    def _export_project(self):
        """Export the current project."""
        if not self.current_project:
            return
        
        project_name = self.current_project.get("name", "Unknown")
        self.logger.info(f"Export project dialog would appear for: {project_name}")
        
        # Publish event
        self.event_bus.publish(
            EventType.STATUS_CHANGED,
            sender="project_manager",
            data={"action": "export_project", "project": self.current_project}
        )
    
    def _handle_project_created(self, event):
        """Handle project created event."""
        project_data = event.get_data("project_data", {})
        if project_data and project_data not in self.projects:
            self.projects.append(project_data)
            self._update_projects_list()
    
    def _handle_project_loaded(self, event):
        """Handle project loaded event."""
        project_data = event.get_data("project_data", {})
        if project_data:
            self.current_project = project_data
            self._update_project_details()
    
    def _handle_project_saved(self, event):
        """Handle project saved event."""
        project_data = event.get_data("project_data", {})
        if project_data:
            self.logger.info(f"Project saved: {project_data.get('name')}")
    
    def get_current_project(self) -> Optional[Dict[str, Any]]:
        """Get the currently selected project."""
        return self.current_project
    
    def get_projects_list(self) -> List[Dict[str, Any]]:
        """Get list of all projects."""
        return self.projects.copy()