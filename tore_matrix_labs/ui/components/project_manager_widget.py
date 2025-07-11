"""
Project manager widget with basic project save/load functionality.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from ..qt_compat import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTextEdit, QListWidget, QListWidgetItem, QGroupBox, 
    QMessageBox, QFileDialog, QInputDialog, QSplitter, Qt, pyqtSignal
)
from ...config.settings import Settings


class ProjectManagerWidget(QWidget):
    """Project manager widget with basic functionality."""
    
    # Signals
    document_selected = pyqtSignal(str)  # document_path
    project_loaded = pyqtSignal()  # project loaded signal
    
    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # Project state
        self.current_project: Optional[Dict[str, Any]] = None
        self.project_file_path: Optional[str] = None
        self.has_changes = False
        self.documents: List[Dict[str, Any]] = []
        
        self._init_ui()
        self.logger.info("Project manager widget initialized")
    
    def _init_ui(self):
        """Initialize user interface."""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("Project Management")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Project actions
        self.new_btn = QPushButton("New Project")
        self.new_btn.clicked.connect(self.create_new_project)
        header_layout.addWidget(self.new_btn)
        
        self.open_btn = QPushButton("Open Project")
        self.open_btn.clicked.connect(self._open_project_dialog)
        header_layout.addWidget(self.open_btn)
        
        self.save_btn = QPushButton("Save Project")
        self.save_btn.clicked.connect(self.save_current_project)
        header_layout.addWidget(self.save_btn)
        
        layout.addLayout(header_layout)
        
        # Main content area
        splitter = QSplitter(Qt.Horizontal)
        
        # Project info section
        info_group = QGroupBox("Project Information")
        info_layout = QVBoxLayout()
        
        self.project_name_label = QLabel("No project loaded")
        self.project_name_label.setStyleSheet("font-weight: bold;")
        info_layout.addWidget(self.project_name_label)
        
        self.project_status_label = QLabel("Status: Ready")
        info_layout.addWidget(self.project_status_label)
        
        self.project_description = QTextEdit()
        self.project_description.setMaximumHeight(100)
        self.project_description.setPlaceholderText("Project description...")
        self.project_description.textChanged.connect(self._mark_changed)
        info_layout.addWidget(self.project_description)
        
        info_group.setLayout(info_layout)
        splitter.addWidget(info_group)
        
        # Documents section
        docs_group = QGroupBox("Project Documents")
        docs_layout = QVBoxLayout()
        
        self.documents_list = QListWidget()
        self.documents_list.itemClicked.connect(self._on_document_clicked)
        docs_layout.addWidget(self.documents_list)
        
        # Document actions
        doc_actions_layout = QHBoxLayout()
        self.add_doc_btn = QPushButton("Add Document")
        self.add_doc_btn.clicked.connect(self._add_document_to_project)
        doc_actions_layout.addWidget(self.add_doc_btn)
        
        self.remove_doc_btn = QPushButton("Remove Selected")
        self.remove_doc_btn.clicked.connect(self._remove_document_from_project)
        doc_actions_layout.addWidget(self.remove_doc_btn)
        
        doc_actions_layout.addStretch()
        docs_layout.addLayout(doc_actions_layout)
        
        docs_group.setLayout(docs_layout)
        splitter.addWidget(docs_group)
        
        layout.addWidget(splitter)
        
        # Status
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("background-color: #ecf0f1; padding: 8px; border-radius: 4px;")
        layout.addWidget(self.status_label)
        
        # Initialize with empty project
        self._update_ui_state()
    
    def create_new_project(self):
        """Create new project."""
        try:
            # Get project name from user
            name, ok = QInputDialog.getText(
                self, "New Project", "Enter project name:"
            )
            
            if not ok or not name.strip():
                return
            
            # Check for unsaved changes
            if self.has_changes and not self._confirm_discard_changes():
                return
            
            # Create new project
            self.current_project = {
                'name': name.strip(),
                'description': '',
                'created_at': datetime.now().isoformat(),
                'modified_at': datetime.now().isoformat(),
                'version': '1.0.0',
                'documents': []
            }
            
            self.project_file_path = None
            self.has_changes = False  # Don't block project opening with unsaved changes flag
            self.documents = []
            
            self._update_ui_state()
            self.status_label.setText(f"Created new project: {name}")
            self.logger.info(f"Created new project: {name}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create new project: {str(e)}")
            self.logger.error(f"Failed to create new project: {str(e)}")
    
    def _open_project_dialog(self):
        """Show open project dialog."""
        print(f"🔵 PROJECT DIALOG: _open_project_dialog called")
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Project", "", "TORE Project Files (*.tore);;JSON Files (*.json);;All Files (*)"
        )
        
        print(f"🔵 PROJECT DIALOG: Selected file: {file_path}")
        
        if file_path:
            print(f"🔵 PROJECT DIALOG: Calling load_project with: {file_path}")
            self.load_project(file_path)
        else:
            print(f"🔴 PROJECT DIALOG: No file selected or dialog cancelled")
    
    def load_project(self, file_path: str):
        """Load project from file."""
        print(f"🔵 LOAD PROJECT: load_project called with: {file_path}")
        
        try:
            # Check for unsaved changes
            print(f"🔵 LOAD PROJECT: has_changes = {self.has_changes}")
            if self.has_changes and not self._confirm_discard_changes():
                print(f"🔴 LOAD PROJECT: User cancelled due to unsaved changes")
                return
            
            # Load project data
            print(f"🔵 LOAD PROJECT: Opening file: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                project_data = json.load(f)
            
            print(f"🔵 LOAD PROJECT: Project data loaded successfully")
            print(f"🔵 LOAD PROJECT: Project name: {project_data.get('name', 'Unknown')}")
            print(f"🔵 LOAD PROJECT: Documents count: {len(project_data.get('documents', []))}")
            
            # Ensure project has path field (add if missing)
            if 'path' not in project_data:
                project_data['path'] = file_path
                print(f"🟢 LOAD PROJECT: Added missing project path: {file_path}")
                self.logger.info(f"Added missing project path: {file_path}")
            
            self.current_project = project_data
            self.project_file_path = file_path
            self.has_changes = False
            self.documents = project_data.get('documents', [])
            
            print(f"🔵 LOAD PROJECT: Updating UI state...")
            self._update_ui_state()
            
            print(f"🔵 LOAD PROJECT: Setting status label...")
            self.status_label.setText(f"Loaded project: {project_data.get('name', 'Unknown')}")
            self.logger.info(f"Loaded project from: {file_path}")
            
            print(f"🔵 LOAD PROJECT: Emitting project_loaded signal...")
            # Emit signal to update main window project tree
            self._emit_project_loaded_signal()
            
            print(f"🟢 LOAD PROJECT: Project loading completed successfully!")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load project: {str(e)}")
            self.logger.error(f"Failed to load project from {file_path}: {str(e)}")
    
    def save_current_project(self):
        """Save current project."""
        print(f"🔵 SAVE PROJECT: save_current_project called")
        print(f"🔵 SAVE PROJECT: current_project exists: {self.current_project is not None}")
        print(f"🔵 SAVE PROJECT: documents count: {len(self.documents)}")
        
        if not self.current_project:
            print(f"🔴 SAVE PROJECT: No current project to save")
            QMessageBox.warning(self, "No Project", "No project to save.")
            return False
        
        try:
            # Get save path
            print(f"🔵 SAVE PROJECT: project_file_path = {self.project_file_path}")
            if not self.project_file_path:
                print(f"🔵 SAVE PROJECT: No file path, showing save dialog...")
                file_path, _ = QFileDialog.getSaveFileName(
                    self, "Save Project", 
                    f"{self.current_project['name']}.tore",
                    "TORE Project Files (*.tore);;JSON Files (*.json);;All Files (*)"
                )
                if not file_path:
                    print(f"🔴 SAVE PROJECT: User cancelled save dialog")
                    return False
                self.project_file_path = file_path
                print(f"🟢 SAVE PROJECT: Set file path to: {self.project_file_path}")
            
            # Update project data
            print(f"🔵 SAVE PROJECT: Updating project data...")
            self.current_project['description'] = self.project_description.toPlainText()
            self.current_project['modified_at'] = datetime.now().isoformat()
            self.current_project['documents'] = self.documents
            
            print(f"🔵 SAVE PROJECT: Final project data:")
            print(f"   📊 Name: {self.current_project.get('name', 'Unknown')}")
            print(f"   📊 Documents: {len(self.current_project.get('documents', []))}")
            print(f"   📊 Modified: {self.current_project.get('modified_at', 'Unknown')}")
            
            # Save to file
            print(f"🔵 SAVE PROJECT: Writing to file: {self.project_file_path}")
            with open(self.project_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.current_project, f, indent=2, ensure_ascii=False)
            
            print(f"🟢 SAVE PROJECT: File written successfully!")
            
            self.has_changes = False
            self._update_ui_state()
            self.status_label.setText("Project saved successfully")
            self.logger.info(f"Project saved to: {self.project_file_path}")
            
            print(f"🟢 SAVE PROJECT: Returning True (success)")
            return True
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save project: {str(e)}")
            self.logger.error(f"Failed to save project: {str(e)}")
            print(f"🔴 SAVE PROJECT: Returning False (error: {e})")
            return False
    
    def _add_document_to_project(self):
        """Add document to current project."""
        if not self.current_project:
            QMessageBox.warning(self, "No Project", "Please create or open a project first.")
            return
        
        # For now, show a simple input dialog for document path
        doc_path, ok = QInputDialog.getText(
            self, "Add Document", "Enter document path or ID:"
        )
        
        if ok and doc_path.strip():
            doc_info = {
                'id': f"doc_{len(self.documents)}",
                'path': doc_path.strip(),
                'name': Path(doc_path.strip()).name if Path(doc_path.strip()).exists() else doc_path.strip(),
                'added_at': datetime.now().isoformat(),
                'status': 'added'
            }
            
            self.documents.append(doc_info)
            self._update_documents_list()
            self._mark_changed()
            self.status_label.setText(f"Added document: {doc_info['name']}")
    
    def _remove_document_from_project(self):
        """Remove selected document from project."""
        current_item = self.documents_list.currentItem()
        if not current_item:
            QMessageBox.information(self, "No Selection", "Please select a document to remove.")
            return
        
        # Get document index
        row = self.documents_list.row(current_item)
        if 0 <= row < len(self.documents):
            doc_name = self.documents[row]['name']
            reply = QMessageBox.question(
                self, "Remove Document",
                f"Remove '{doc_name}' from the project?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.documents.pop(row)
                self._update_documents_list()
                self._mark_changed()
                self.status_label.setText(f"Removed document: {doc_name}")
    
    def _update_ui_state(self):
        """Update UI state based on current project."""
        if self.current_project:
            self.project_name_label.setText(f"Project: {self.current_project['name']}")
            self.project_description.setPlainText(self.current_project.get('description', ''))
            
            if self.has_changes:
                self.project_status_label.setText("Status: Modified")
            else:
                self.project_status_label.setText("Status: Saved")
                
            self.save_btn.setEnabled(True)
            self.add_doc_btn.setEnabled(True)
            self.remove_doc_btn.setEnabled(True)
            
        else:
            self.project_name_label.setText("No project loaded")
            self.project_description.clear()
            self.project_status_label.setText("Status: Ready")
            self.save_btn.setEnabled(False)
            self.add_doc_btn.setEnabled(False)
            self.remove_doc_btn.setEnabled(False)
        
        self._update_documents_list()
    
    def _update_documents_list(self):
        """Update documents list display."""
        self.documents_list.clear()
        
        for doc in self.documents:
            item = QListWidgetItem(f"{doc['name']} ({doc['status']})")
            item.setData(Qt.UserRole, doc)
            self.documents_list.addItem(item)
    
    def _mark_changed(self):
        """Mark project as changed."""
        if self.current_project:
            self.has_changes = True
            self.project_status_label.setText("Status: Modified")
    
    def _confirm_discard_changes(self) -> bool:
        """Confirm discarding unsaved changes."""
        reply = QMessageBox.question(
            self, "Unsaved Changes",
            "You have unsaved changes. Discard them?",
            QMessageBox.Yes | QMessageBox.No
        )
        return reply == QMessageBox.Yes
    
    def has_unsaved_changes(self) -> bool:
        """Check for unsaved changes."""
        return self.has_changes
    
    def get_current_project(self):
        """Get current project."""
        return self.current_project
    
    def get_selected_documents(self):
        """Get selected documents."""
        return self.documents
    
    def add_processed_document(self, document_data: Dict[str, Any]):
        """Add a processed document to the current project."""
        if not self.current_project:
            return
        
        # Store document in flat format that conversion can handle
        doc_info = {
            'id': document_data.get('id', 'unknown'),
            'path': document_data.get('file_path', ''),
            'name': document_data.get('file_name', 'Unknown'),
            'file_path': document_data.get('file_path', ''),           # For conversion compatibility
            'file_name': document_data.get('file_name', 'Unknown'),   # For conversion compatibility  
            'processing_status': document_data.get('processing_status', 'processed'),  # For conversion compatibility
            'status': document_data.get('processing_status', 'processed'),
            'file_size': document_data.get('file_size', 0),
            'file_type': document_data.get('file_type', 'unknown'),
            'page_count': document_data.get('page_count', 0),
            'quality_level': document_data.get('quality_level', 'unknown'),
            'quality_score': document_data.get('quality_score', 0.0),
            'document_type': document_data.get('document_type', 'unknown'),
            'validation_status': document_data.get('validation_status', 'unknown'),
            'added_at': datetime.now().isoformat(),
            'last_modified': datetime.now().isoformat(),
            'processing_data': document_data  # Keep full data for compatibility
        }
        
        # Check if document already exists
        existing_doc = next((d for d in self.documents if d['id'] == doc_info['id']), None)
        if existing_doc:
            existing_doc.update(doc_info)
        else:
            self.documents.append(doc_info)
        
        self._update_documents_list()
        self._mark_changed()
        
        # Auto-save the project when documents are added
        print(f"🟢 PROJECT: Document added, auto-saving project...")
        self.save_current_project()
        
        self.status_label.setText(f"Added document: {doc_info['name']}")
    
    def _on_document_clicked(self, item: QListWidgetItem):
        """Handle document list item click."""
        doc_data = item.data(Qt.UserRole)
        if doc_data and 'path' in doc_data:
            document_path = doc_data['path']
            if Path(document_path).exists():
                self.document_selected.emit(document_path)
                self.status_label.setText(f"Selected document: {doc_data['name']}")
            else:
                self.status_label.setText(f"Document not found: {doc_data['name']}")
                QMessageBox.warning(self, "File Not Found", f"Document file not found:\n{document_path}")
    
    def _emit_project_loaded_signal(self):
        """Emit signal that project has been loaded."""
        print(f"🔵 SIGNAL: _emit_project_loaded_signal called")
        print(f"🔵 SIGNAL: About to emit project_loaded signal...")
        self.project_loaded.emit()
        print(f"🟢 SIGNAL: project_loaded signal emitted successfully")
    
    def get_project_documents(self) -> List[Dict[str, Any]]:
        """Get all documents in the current project with format conversion."""
        converted_documents = []
        
        for doc in self.documents:
            # Convert from the project file format to the format expected by main window
            converted_doc = self._convert_document_format(doc)
            converted_documents.append(converted_doc)
        
        return converted_documents
    
    def _convert_document_format(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Convert document from project file format to main window format."""
        try:
            print(f"🔵 CONVERT: Converting document: {doc}")
            
            # Handle both old nested format AND new flat format
            metadata = doc.get('metadata', {})
            custom_metadata = doc.get('custom_metadata', {})
            processing_data = doc.get('processing_data', {})
            
            # Extract name - try multiple sources
            name = (
                doc.get('file_name') or           # New flat format
                metadata.get('file_name') or      # Old nested format  
                doc.get('name') or                # Direct name field
                'Unknown Document'
            )
            
            # Extract path - try multiple sources  
            path = (
                doc.get('file_path') or           # New flat format
                metadata.get('file_path') or      # Old nested format
                doc.get('path') or                # Direct path field
                ''
            )
            
            # Extract status - try multiple sources
            status = (
                doc.get('processing_status') or   # New format
                doc.get('status') or              # Alternative status field
                metadata.get('processing_status') or  # Old nested format
                'unknown'
            )
            
            print(f"🔵 CONVERT: Extracted - name: {name}, path: {path}, status: {status}")
            
            # Convert to expected format
            converted = {
                'id': doc.get('id', 'unknown'),
                'name': name,
                'path': path,
                'status': status,
                'processing_data': {
                    'file_size': (
                        doc.get('file_size') or 
                        metadata.get('file_size') or 
                        processing_data.get('file_size') or 
                        0
                    ),
                    'page_count': (
                        doc.get('page_count') or 
                        metadata.get('page_count') or 
                        processing_data.get('page_count') or 
                        0
                    ),
                    'file_type': (
                        doc.get('file_type') or 
                        metadata.get('file_type') or 
                        processing_data.get('file_type') or 
                        'unknown'
                    ),
                    'creation_date': metadata.get('creation_date', ''),
                    'modification_date': metadata.get('modification_date', ''),
                    'processing_status': status,
                    'quality_level': (
                        doc.get('quality_level') or 
                        processing_data.get('quality_level') or 
                        'unknown'
                    ),
                    'quality_score': (
                        doc.get('quality_score') or 
                        processing_data.get('quality_score') or 
                        0.0
                    ),
                    'document_type': (
                        doc.get('document_type') or 
                        processing_data.get('document_type') or 
                        'unknown'
                    ),
                    'corrections_count': (
                        doc.get('corrections_count') or
                        len(custom_metadata.get('corrections', [])) or
                        len(processing_data.get('corrections', []))
                    ),
                    'corrections': (
                        doc.get('corrections') or
                        custom_metadata.get('corrections', []) or
                        processing_data.get('corrections', [])
                    ),
                    'visual_areas': (
                        doc.get('visual_areas') or
                        processing_data.get('visual_areas', {}) or
                        custom_metadata.get('visual_areas', {})
                    )
                },
                'visual_areas': (
                    doc.get('visual_areas') or
                    processing_data.get('visual_areas', {}) or
                    custom_metadata.get('visual_areas', {})
                ),
                'added_at': (
                    doc.get('added_at') or 
                    doc.get('created_at') or 
                    ''
                ),
                'updated_at': (
                    doc.get('last_modified') or
                    doc.get('updated_at') or 
                    ''
                ),
                'tags': doc.get('tags', []),
                'original_data': doc  # Keep original for reference
            }
            
            print(f"🟢 CONVERT: Converted document: {converted['name']} ({converted['status']})")
            self.logger.debug(f"Converted document: {converted['name']} ({converted['status']})")
            return converted
            
        except Exception as e:
            print(f"🔴 CONVERT: Error converting document format: {e}")
            import traceback
            print(f"🔴 CONVERT: Traceback: {traceback.format_exc()}")
            self.logger.error(f"Error converting document format: {e}")
            # Return minimal fallback format
            return {
                'id': doc.get('id', 'unknown'),
                'name': f"Error Converting: {doc.get('file_name', doc.get('name', 'Unknown'))}",
                'path': doc.get('file_path', doc.get('path', '')),
                'status': 'error',
                'processing_data': {},
                'visual_areas': doc.get('visual_areas', {}),
                'original_data': doc
            }
    
    def create_new_project_with_name(self, name: str):
        """Create new project with specified name."""
        try:
            # Check for unsaved changes
            if self.has_changes and not self._confirm_discard_changes():
                return
            
            # Create new project
            self.current_project = {
                'name': name,
                'description': '',
                'created_at': datetime.now().isoformat(),
                'modified_at': datetime.now().isoformat(),
                'version': '1.0.0',
                'documents': []
            }
            
            self.project_file_path = None
            self.has_changes = False  # Don't block project opening with unsaved changes flag
            self.documents = []
            
            self._update_ui_state()
            self.status_label.setText(f"Created new project: {name}")
            self.logger.info(f"Created new project: {name}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create new project: {str(e)}")
            self.logger.error(f"Failed to create new project: {str(e)}")