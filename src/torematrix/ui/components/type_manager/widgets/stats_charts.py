"""Statistics Charts Widget"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCharts import QChartView


class StatisticsChartsWidget(QWidget):
    """Statistics charts display widget"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup charts UI"""
        pass