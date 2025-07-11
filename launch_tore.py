#!/usr/bin/env python3
import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from tore_matrix_labs.ui.main_window import MainWindow
from tore_matrix_labs.config.settings import Settings

app = QApplication(sys.argv)
settings = Settings()
window = MainWindow(settings)
window.move(100, 100)
window.resize(1200, 800)
window.setWindowState(Qt.WindowNoState)
window.show()
window.raise_()
window.activateWindow()
app.exec_()