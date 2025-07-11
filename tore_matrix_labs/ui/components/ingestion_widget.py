"""
Document ingestion widget for TORE Matrix Labs.
"""

import logging
from typing import List, Optional
from pathlib import Path

from ..qt_compat import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QProgressBar, QTextEdit,
    QListWidget, QListWidgetItem, QGroupBox,
    QCheckBox, QComboBox, QSpinBox, QDoubleSpinBox,
    QFileDialog, QMessageBox, QSplitter, QFrame,
    Qt, pyqtSignal, QThread, QTimer, QFont, QIcon
)

from ...config.settings import Settings
from ...config.constants import SUPPORTED_FILE_TYPES, DocumentType, ProcessingStatus


class DocumentListItem(QListWidgetItem):
    """Custom list item for documents."""
    
    def __init__(self, file_path: str, file_size: int, page_count: int = 0):
        super().__init__()
        self.file_path = file_path
        self.file_size = file_size
        self.page_count = page_count
        self.processing_status = ProcessingStatus.PENDING
        
        self._update_display()
    
    def _update_display(self):
        """Update item display text."""
        file_name = Path(self.file_path).name
        size_mb = self.file_size / (1024 * 1024)
        
        display_text = f"{file_name} ({size_mb:.1f} MB"
        if self.page_count > 0:
            display_text += f", {self.page_count} pages"
        display_text += f") - {self.processing_status.value.title()}"
        
        self.setText(display_text)
        
        # Set status color using QColor for cross-framework compatibility
        from ..qt_compat import QColor
        if self.processing_status == ProcessingStatus.PENDING:
            self.setBackground(QColor(211, 211, 211))  # lightGray
        elif self.processing_status == ProcessingStatus.PROCESSING:
            self.setBackground(QColor(255, 255, 0))    # yellow
        elif self.processing_status in [ProcessingStatus.EXTRACTED, ProcessingStatus.APPROVED]:
            self.setBackground(QColor(144, 238, 144))  # lightGreen
        elif self.processing_status == ProcessingStatus.FAILED:
            self.setBackground(QColor(255, 0, 0))      # red
    
    def update_status(self, status: ProcessingStatus):
        """Update processing status."""
        self.processing_status = status
        self._update_display()


class IngestionWidget(QWidget):
    """Widget for document ingestion and processing."""
    
    # Signals
    document_processed = pyqtSignal(str)  # document_id
    processing_progress = pyqtSignal(int)  # percentage
    status_message = pyqtSignal(str)
    active_document_changed = pyqtSignal(str, dict)  # document_id, metadata
    
    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # State
        self.document_items = []
        self.processing_thread = None
        self.active_document_id = None
        
        self._init_ui()
        self._setup_connections()
        
        self.logger.info("Ingestion widget initialized")
    
    def _init_ui(self):
        """Initialize user interface."""
        layout = QVBoxLayout(self)
        
        # Create main splitter
        splitter = QSplitter(Qt.Vertical)
        layout.addWidget(splitter)
        
        # Document selection section
        selection_group = self._create_selection_section()
        splitter.addWidget(selection_group)
        
        # Processing configuration section
        config_group = self._create_configuration_section()
        splitter.addWidget(config_group)
        
        # Processing status section
        status_group = self._create_status_section()
        splitter.addWidget(status_group)
        
        # Set splitter proportions
        splitter.setSizes([300, 200, 200])
    
    def _create_selection_section(self) -> QGroupBox:
        """Create document selection section."""
        group = QGroupBox("Document Selection")
        layout = QVBoxLayout(group)
        
        # Buttons row
        buttons_layout = QHBoxLayout()
        
        self.add_files_btn = QPushButton("Add Files")
        self.add_files_btn.clicked.connect(self._add_files)
        buttons_layout.addWidget(self.add_files_btn)
        
        self.add_folder_btn = QPushButton("Add Folder")
        self.add_folder_btn.clicked.connect(self._add_folder)
        buttons_layout.addWidget(self.add_folder_btn)
        
        self.remove_btn = QPushButton("Remove Selected")
        self.remove_btn.clicked.connect(self._remove_selected)
        buttons_layout.addWidget(self.remove_btn)
        
        self.clear_btn = QPushButton("Clear All")
        self.clear_btn.clicked.connect(self._clear_all)
        buttons_layout.addWidget(self.clear_btn)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        # Document list
        self.document_list = QListWidget()
        self.document_list.setSelectionMode(QListWidget.ExtendedSelection)
        layout.addWidget(self.document_list)
        
        # Info label
        self.info_label = QLabel("No documents loaded")
        self.info_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(self.info_label)
        
        return group
    
    def _create_configuration_section(self) -> QGroupBox:
        """Create processing configuration section."""
        group = QGroupBox("Processing Configuration")
        layout = QGridLayout(group)
        
        row = 0
        
        # Extract text checkbox
        self.extract_text_cb = QCheckBox("Extract Text")
        self.extract_text_cb.setChecked(True)
        layout.addWidget(self.extract_text_cb, row, 0)
        
        # Extract tables checkbox
        self.extract_tables_cb = QCheckBox("Extract Tables")
        self.extract_tables_cb.setChecked(True)
        layout.addWidget(self.extract_tables_cb, row, 1)
        
        # Extract images checkbox
        self.extract_images_cb = QCheckBox("Extract Images")
        self.extract_images_cb.setChecked(True)
        layout.addWidget(self.extract_images_cb, row, 2)
        row += 1
        
        # Apply OCR checkbox
        self.apply_ocr_cb = QCheckBox("Apply OCR")
        self.apply_ocr_cb.setChecked(False)
        layout.addWidget(self.apply_ocr_cb, row, 0)
        
        # Preserve formatting checkbox
        self.preserve_format_cb = QCheckBox("Preserve Formatting")
        self.preserve_format_cb.setChecked(True)
        layout.addWidget(self.preserve_format_cb, row, 1)
        
        # Auto-correct checkbox
        self.auto_correct_cb = QCheckBox("Auto-correct")
        self.auto_correct_cb.setChecked(True)
        layout.addWidget(self.auto_correct_cb, row, 2)
        row += 1
        
        # Quality threshold
        layout.addWidget(QLabel("Quality Threshold:"), row, 0)
        self.quality_threshold_spin = QDoubleSpinBox()
        self.quality_threshold_spin.setRange(0.1, 1.0)
        self.quality_threshold_spin.setSingleStep(0.1)
        self.quality_threshold_spin.setValue(self.settings.processing.quality_threshold)
        layout.addWidget(self.quality_threshold_spin, row, 1)
        
        # Document type
        layout.addWidget(QLabel("Document Type:"), row, 2)
        self.doc_type_combo = QComboBox()
        self.doc_type_combo.addItems([dt.value.title() for dt in DocumentType])
        layout.addWidget(self.doc_type_combo, row, 3)
        row += 1
        
        # Chunk size
        layout.addWidget(QLabel("Chunk Size:"), row, 0)
        self.chunk_size_spin = QSpinBox()
        self.chunk_size_spin.setRange(128, 2048)
        self.chunk_size_spin.setValue(self.settings.processing.chunk_size)
        layout.addWidget(self.chunk_size_spin, row, 1)
        
        # Chunk overlap
        layout.addWidget(QLabel("Chunk Overlap:"), row, 2)
        self.chunk_overlap_spin = QSpinBox()
        self.chunk_overlap_spin.setRange(0, 200)
        self.chunk_overlap_spin.setValue(self.settings.processing.chunk_overlap)
        layout.addWidget(self.chunk_overlap_spin, row, 3)
        
        return group
    
    def _create_status_section(self) -> QGroupBox:
        """Create processing status section."""
        group = QGroupBox("Processing Status")
        layout = QVBoxLayout(group)
        
        # Progress section
        progress_layout = QHBoxLayout()
        
        self.process_btn = QPushButton("Start Processing")
        self.process_btn.clicked.connect(self.process_documents)
        progress_layout.addWidget(self.process_btn)
        
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self._stop_processing)
        self.stop_btn.setEnabled(False)
        progress_layout.addWidget(self.stop_btn)
        
        progress_layout.addStretch()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)
        
        layout.addLayout(progress_layout)
        
        # Status text
        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(100)
        self.status_text.setReadOnly(True)
        layout.addWidget(self.status_text)
        
        return group
    
    def _setup_connections(self):
        """Setup signal connections."""
        self.document_list.itemSelectionChanged.connect(self._update_ui_state)
        self.document_list.itemClicked.connect(self._on_document_clicked)
        self.processing_progress.connect(self._update_progress)
        self.status_message.connect(self._add_status_message)
    
    def get_selected_files(self) -> List[str]:
        """Get list of selected file paths for processing."""
        files = []
        for i in range(self.document_list.count()):
            item = self.document_list.item(i)
            if isinstance(item, DocumentListItem):
                files.append(item.file_path)
        return files
    
    def get_all_documents(self) -> List[DocumentListItem]:
        """Get all document items in the list."""
        documents = []
        for i in range(self.document_list.count()):
            item = self.document_list.item(i)
            if isinstance(item, DocumentListItem):
                documents.append(item)
        return documents
    
    def _add_files(self):
        """Add files to document list."""
        file_types = ";;".join([f"{desc} (*{ext})" for ext, desc in SUPPORTED_FILE_TYPES.items()])
        file_types += ";;All Files (*)"
        
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Documents", "", file_types
        )
        
        if files:
            self._add_documents(files)
    
    def _add_folder(self):
        """Add all supported files from a folder."""
        folder = QFileDialog.getExistingDirectory(
            self, "Select Folder with Documents"
        )
        
        if folder:
            folder_path = Path(folder)
            files = []
            
            for ext in SUPPORTED_FILE_TYPES.keys():
                files.extend(folder_path.glob(f"*{ext}"))
                files.extend(folder_path.glob(f"**/*{ext}"))  # Recursive
            
            if files:
                self._add_documents([str(f) for f in files])
            else:
                QMessageBox.information(
                    self, "No Documents", 
                    "No supported documents found in the selected folder."
                )
    
    def _add_documents(self, file_paths: List[str]):
        """Add documents to the list."""
        added_count = 0
        
        for file_path in file_paths:
            # Check if already added
            if any(item.file_path == file_path for item in self.document_items):
                continue
            
            # Validate file
            if not Path(file_path).exists():
                continue
            
            # Get file info
            file_size = Path(file_path).stat().st_size
            
            # Create list item
            item = DocumentListItem(file_path, file_size)
            self.document_list.addItem(item)
            self.document_items.append(item)
            added_count += 1
        
        self._update_info_label()
        self._update_ui_state()
        
        if added_count > 0:
            self.status_message.emit(f"Added {added_count} documents")
    
    def _remove_selected(self):
        """Remove selected documents."""
        selected_items = self.document_list.selectedItems()
        
        for item in selected_items:
            row = self.document_list.row(item)
            self.document_list.takeItem(row)
            self.document_items.remove(item)
        
        self._update_info_label()
        self._update_ui_state()
        
        if selected_items:
            self.status_message.emit(f"Removed {len(selected_items)} documents")
    
    def _clear_all(self):
        """Clear all documents."""
        if self.document_items:
            reply = QMessageBox.question(
                self, "Clear All",
                "Are you sure you want to remove all documents?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.document_list.clear()
                self.document_items.clear()
                self._update_info_label()
                self._update_ui_state()
                self.status_message.emit("Cleared all documents")
    
    def _update_info_label(self):
        """Update info label with document statistics."""
        if not self.document_items:
            self.info_label.setText("No documents loaded")
            return
        
        total_size = sum(item.file_size for item in self.document_items)
        size_mb = total_size / (1024 * 1024)
        
        self.info_label.setText(
            f"{len(self.document_items)} documents, {size_mb:.1f} MB total"
        )
    
    def _update_ui_state(self):
        """Update UI state based on current selection and processing."""
        has_documents = len(self.document_items) > 0
        has_selection = len(self.document_list.selectedItems()) > 0
        is_processing = self.processing_thread is not None and self.processing_thread.isRunning()
        
        self.process_btn.setEnabled(has_documents and not is_processing)
        self.stop_btn.setEnabled(is_processing)
        self.remove_btn.setEnabled(has_selection and not is_processing)
        self.clear_btn.setEnabled(has_documents and not is_processing)
        self.add_files_btn.setEnabled(not is_processing)
        self.add_folder_btn.setEnabled(not is_processing)
    
    def _update_progress(self, percentage: int):
        """Update progress bar."""
        if percentage < 0:
            self.progress_bar.setVisible(False)
        else:
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(percentage)
    
    def _add_status_message(self, message: str):
        """Add message to status text."""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_text.append(f"[{timestamp}] {message}")
        
        # Auto-scroll to bottom
        cursor = self.status_text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.status_text.setTextCursor(cursor)
    
    def process_documents(self):
        """Start document processing."""
        if not self.document_items:
            QMessageBox.warning(self, "No Documents", "Please add documents first.")
            return
        
        self.status_message.emit("Starting document processing...")
        self.processing_progress.emit(0)
        
        # Implement actual processing
        self._process_documents_real()
    
    def _simulate_processing(self):
        """Simulate document processing (placeholder)."""
        # This is a placeholder - replace with actual processing logic
        from ..qt_compat import QTimer
        
        self.progress_timer = QTimer()
        self.progress_value = 0
        self.current_doc_index = 0
        
        def update_progress():
            self.progress_value += 2
            self.processing_progress.emit(self.progress_value)
            
            if self.progress_value >= 100:
                self.progress_timer.stop()
                self.processing_progress.emit(-1)
                self.status_message.emit("Processing completed successfully")
                self._update_ui_state()
                
                # Mark all documents as processed
                for item in self.document_items:
                    item.update_status(ProcessingStatus.EXTRACTED)
                
                # Emit signal for each document
                for item in self.document_items:
                    self.document_processed.emit(item.file_path)
            else:
                # Update current document status
                doc_progress = (self.progress_value / 100) * len(self.document_items)
                current_index = int(doc_progress)
                
                if current_index < len(self.document_items) and current_index != self.current_doc_index:
                    if self.current_doc_index < len(self.document_items):
                        self.document_items[self.current_doc_index].update_status(ProcessingStatus.EXTRACTED)
                    
                    self.current_doc_index = current_index
                    if current_index < len(self.document_items):
                        self.document_items[current_index].update_status(ProcessingStatus.PROCESSING)
                        file_name = Path(self.document_items[current_index].file_path).name
                        self.status_message.emit(f"Processing {file_name}...")
        
        self.progress_timer.timeout.connect(update_progress)
        self.progress_timer.start(100)  # Update every 100ms
        
        self._update_ui_state()
    
    def _stop_processing(self):
        """Stop document processing."""
        if hasattr(self, 'progress_timer'):
            self.progress_timer.stop()
        
        self.processing_progress.emit(-1)
        self.status_message.emit("Processing stopped by user")
        self._update_ui_state()
    
    def _process_documents_real(self):
        """Process documents using the actual document processor."""
        try:
            from ...core.document_processor import DocumentProcessor
            from ...config.settings import Settings
            
            # Initialize the document processor
            settings = Settings()
            processor = DocumentProcessor(settings)
            
            # Process each document
            total_docs = len(self.document_items)
            for i, item in enumerate(self.document_items):
                try:
                    # Update status
                    item.update_status(ProcessingStatus.PROCESSING)
                    self.status_message.emit(f"Processing {item.file_path}...")
                    
                    # Calculate progress
                    progress = int(((i + 0.5) / total_docs) * 100)
                    self.processing_progress.emit(progress)
                    
                    # Process the document
                    result = processor.process_document(item.file_path)
                    
                    if result:
                        item.update_status(ProcessingStatus.EXTRACTED)
                        self.status_message.emit(f"Successfully processed {Path(item.file_path).name}")
                        
                        # Emit signal that document was processed
                        self.document_processed.emit(item.file_path)
                    else:
                        item.update_status(ProcessingStatus.FAILED)
                        self.status_message.emit(f"Failed to process {Path(item.file_path).name}")
                        
                except Exception as e:
                    item.update_status(ProcessingStatus.FAILED)
                    self.status_message.emit(f"Error processing {Path(item.file_path).name}: {str(e)}")
                    self.logger.error(f"Document processing error: {str(e)}")
            
            # Complete processing
            self.processing_progress.emit(100)
            self.status_message.emit(f"Processing completed: {total_docs} documents processed")
            
            # Hide progress bar
            self.processing_progress.emit(-1)
            self._update_ui_state()
            
        except Exception as e:
            self.processing_progress.emit(-1)
            self.status_message.emit(f"Processing failed: {str(e)}")
            self.logger.error(f"Document processing failed: {str(e)}")
            self._update_ui_state()
    
    def import_documents(self, file_paths: List[str]):
        """Import documents (called from main window)."""
        self._add_documents(file_paths)
    
    def get_processing_config(self) -> dict:
        """Get current processing configuration."""
        return {
            'extract_text': self.extract_text_cb.isChecked(),
            'extract_tables': self.extract_tables_cb.isChecked(),
            'extract_images': self.extract_images_cb.isChecked(),
            'apply_ocr': self.apply_ocr_cb.isChecked(),
            'preserve_formatting': self.preserve_format_cb.isChecked(),
            'auto_correct': self.auto_correct_cb.isChecked(),
            'quality_threshold': self.quality_threshold_spin.value(),
            'document_type': self.doc_type_combo.currentText().lower(),
            'chunk_size': self.chunk_size_spin.value(),
            'chunk_overlap': self.chunk_overlap_spin.value()
        }
    
    def get_document_list(self) -> List[DocumentListItem]:
        """Get current document list."""
        return self.document_items.copy()
    
    def _on_document_clicked(self, item):
        """Handle single-click document activation."""
        if isinstance(item, DocumentListItem):
            # Set as active document
            self.active_document_id = getattr(item, 'document_id', None)
            if not self.active_document_id:
                # Generate document ID if not present
                import uuid
                self.active_document_id = f"doc_{uuid.uuid4().hex[:8]}"
                item.document_id = self.active_document_id
            
            # Get document metadata
            metadata = self._get_document_metadata(item)
            
            # Emit signal to notify other widgets
            self.active_document_changed.emit(self.active_document_id, metadata)
            
            self.logger.info(f"Document activated: {item.file_path}")
    
    def _get_document_metadata(self, item: DocumentListItem) -> dict:
        """Extract metadata from document item."""
        return {
            'id': getattr(item, 'document_id', None),
            'path': item.file_path,
            'name': Path(item.file_path).name,
            'file_path': item.file_path,
            'file_name': Path(item.file_path).name,
            'file_size': item.file_size,
            'page_count': item.page_count,
            'processing_status': item.processing_status.value,
            'status': item.processing_status.value,
            'corrections_count': 0,
            'corrections': [],
            'visual_areas': {}
        }
    
    def set_active_document_by_id(self, document_id: str):
        """Set active document by ID (for external calls)."""
        for i in range(self.document_list.count()):
            item = self.document_list.item(i)
            if isinstance(item, DocumentListItem):
                if getattr(item, 'document_id', None) == document_id:
                    self.document_list.setCurrentItem(item)
                    self._on_document_clicked(item)
                    break