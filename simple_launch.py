#!/usr/bin/env python3
import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt

# Simple test to see if we can get a TORE window visible
app = QApplication(sys.argv)

# Create a simple window
window = QMainWindow()
window.setWindowTitle("TORE Matrix Labs - Test")
window.setGeometry(200, 200, 800, 600)

# Add some content
central_widget = QWidget()
layout = QVBoxLayout()
label = QLabel("TORE Matrix Labs is running!\nIf you can see this, the display is working.")
label.setAlignment(Qt.AlignCenter)
layout.addWidget(label)
central_widget.setLayout(layout)
window.setCentralWidget(central_widget)

# Force window to be visible and on top
window.show()
window.raise_()
window.activateWindow()
window.setWindowState(Qt.WindowActive)

print("Simple TORE window should be visible now...")
app.exec_()