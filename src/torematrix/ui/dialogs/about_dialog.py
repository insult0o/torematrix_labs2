"""About dialog for ToreMatrix V3."""

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QTabWidget, QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QFont

class AboutDialog(QDialog):
    """Professional about dialog with application information."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About ToreMatrix V3")
        self.setFixedSize(500, 400)
        self.setModal(True)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        
        # Header with logo and title
        header_layout = QHBoxLayout()
        
        # Logo placeholder
        logo_label = QLabel()
        logo_label.setFixedSize(64, 64)
        logo_label.setStyleSheet("border: 2px solid #ccc; background: #f0f0f0;")
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_label.setText("LOGO")
        header_layout.addWidget(logo_label)
        
        # Title and version
        title_layout = QVBoxLayout()
        title_label = QLabel("ToreMatrix V3")
        title_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        version_label = QLabel("Version 3.0.0")
        subtitle_label = QLabel("Enterprise Document Processing Platform")
        
        title_layout.addWidget(title_label)
        title_layout.addWidget(version_label)
        title_layout.addWidget(subtitle_label)
        title_layout.addStretch()
        
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Tabs for different information
        tabs = QTabWidget()
        
        # About tab
        about_widget = QWidget()
        about_layout = QVBoxLayout(about_widget)
        about_text = QTextEdit()
        about_text.setReadOnly(True)
        about_text.setHtml("""
        <h3>About ToreMatrix V3</h3>
        <p>ToreMatrix V3 is a comprehensive document processing platform designed for enterprise use. 
        It provides advanced document analysis, quality assurance, and export capabilities with 
        zero-hallucination processing for RAG systems and LLM fine-tuning.</p>
        
        <h4>Key Features:</h4>
        <ul>
        <li>Advanced document analysis (PDF, DOCX, ODT, RTF)</li>
        <li>Quality assurance engine with human validation</li>
        <li>Production-ready pipeline with batch processing</li>
        <li>AI integration with multiple embedding models</li>
        <li>Complete traceability and audit logging</li>
        </ul>
        """)
        about_layout.addWidget(about_text)
        tabs.addTab(about_widget, "About")
        
        # Credits tab
        credits_widget = QWidget()
        credits_layout = QVBoxLayout(credits_widget)
        credits_text = QTextEdit()
        credits_text.setReadOnly(True)
        credits_text.setHtml("""
        <h3>Credits</h3>
        <p><b>Development Team:</b></p>
        <ul>
        <li>Core Architecture: ToreMatrix Labs</li>
        <li>UI Framework: PyQt6 Development Team</li>
        <li>Document Processing: Unstructured.io</li>
        </ul>
        
        <p><b>Third-Party Libraries:</b></p>
        <ul>
        <li>PyQt6 - Cross-platform GUI toolkit</li>
        <li>SQLAlchemy - Database ORM</li>
        <li>Pydantic - Data validation</li>
        <li>AsyncIO - Asynchronous programming</li>
        </ul>
        """)
        credits_layout.addWidget(credits_text)
        tabs.addTab(credits_widget, "Credits")
        
        # License tab
        license_widget = QWidget()
        license_layout = QVBoxLayout(license_widget)
        license_text = QTextEdit()
        license_text.setReadOnly(True)
        license_text.setPlainText("""ToreMatrix V3 License

Copyright (c) 2025 ToreMatrix Labs

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.""")
        license_layout.addWidget(license_text)
        tabs.addTab(license_widget, "License")
        
        layout.addWidget(tabs)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        ok_button = QPushButton("OK")
        ok_button.setDefault(True)
        ok_button.clicked.connect(self.accept)
        button_layout.addWidget(ok_button)
        
        layout.addLayout(button_layout)