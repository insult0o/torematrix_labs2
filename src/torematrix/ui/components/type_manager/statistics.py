"""Type Statistics Dashboard

Analytics and statistics for type usage, distribution, and performance.
Provides insights into type system usage patterns and trends.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
    QScrollArea, QFrame, QPushButton, QComboBox, QSpinBox,
    QProgressBar, QTextEdit, QSplitter, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread, pyqtSlot
from PyQt6.QtGui import QFont, QColor, QPainter, QPen, QBrush, QPixmap, QIcon
from PyQt6.QtCharts import QChart, QChartView, QPieSeries, QBarSeries, QBarSet, QLineSeries

from torematrix.core.models.types import get_type_registry, TypeRegistry, TypeDefinition
from torematrix.core.models.types.operations import TypeOperations
from torematrix.core.models.types.metadata import get_metadata_manager


@dataclass
class TypeStatistics:
    """Statistics for a specific type"""
    type_id: str
    type_name: str
    usage_count: int
    creation_count: int
    conversion_count: int
    error_count: int
    last_used: Optional[datetime] = None
    avg_performance: float = 0.0
    popularity_score: float = 0.0


@dataclass
class CategoryStatistics:
    """Statistics for a type category"""
    category: str
    type_count: int
    total_usage: int
    avg_usage_per_type: float
    most_popular_type: str
    least_popular_type: str


@dataclass
class SystemStatistics:
    """Overall system statistics"""
    total_types: int
    total_usage: int
    total_operations: int
    avg_operations_per_day: float
    active_types: int
    inactive_types: int
    error_rate: float
    uptime_days: int


class StatisticsCalculator(QThread):
    """Background thread for calculating statistics"""
    
    statistics_calculated = pyqtSignal(dict)
    progress_updated = pyqtSignal(int)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, registry: TypeRegistry, operations: TypeOperations, parent=None):
        super().__init__(parent)
        self.registry = registry
        self.operations = operations
        self.should_stop = False
    
    def stop(self):
        """Stop the calculation"""
        self.should_stop = True
    
    def run(self):
        """Calculate all statistics"""
        try:
            self.progress_updated.emit(0)
            
            # Get all types
            all_types = self.registry.list_types()
            total_types = len(all_types)
            
            # Calculate type statistics
            type_stats = {}
            for i, (type_id, type_def) in enumerate(all_types.items()):
                if self.should_stop:
                    return
                
                stats = self._calculate_type_statistics(type_def)
                type_stats[type_id] = stats
                
                # Update progress
                progress = int((i + 1) / total_types * 50)
                self.progress_updated.emit(progress)
            
            # Calculate category statistics
            category_stats = self._calculate_category_statistics(type_stats)
            self.progress_updated.emit(75)
            
            # Calculate system statistics
            system_stats = self._calculate_system_statistics(type_stats)
            self.progress_updated.emit(90)
            
            # Prepare results
            results = {
                'type_statistics': type_stats,
                'category_statistics': category_stats,
                'system_statistics': system_stats,
                'calculation_time': datetime.now()
            }
            
            self.progress_updated.emit(100)
            self.statistics_calculated.emit(results)
            
        except Exception as e:
            self.error_occurred.emit(str(e))
    
    def _calculate_type_statistics(self, type_def: TypeDefinition) -> TypeStatistics:
        """Calculate statistics for a single type"""
        # Get operation history for this type
        history = self.operations.get_operation_history(type_filter=type_def.type_id)
        
        # Count different operation types
        usage_count = len([op for op in history if op.operation_type.value == "use"])
        creation_count = len([op for op in history if op.operation_type.value == "create"])
        conversion_count = len([op for op in history if op.operation_type.value == "convert"])
        error_count = len([op for op in history if not op.success])
        
        # Find last usage
        last_used = None
        if history:
            last_used = max(op.timestamp for op in history)
        
        # Calculate average performance
        performance_times = [op.performance_metrics.get('duration', 0) for op in history 
                           if op.performance_metrics and 'duration' in op.performance_metrics]
        avg_performance = sum(performance_times) / len(performance_times) if performance_times else 0
        
        # Calculate popularity score (weighted combination of usage metrics)
        popularity_score = (
            usage_count * 1.0 +
            creation_count * 2.0 +
            conversion_count * 1.5 -
            error_count * 0.5
        )
        
        return TypeStatistics(
            type_id=type_def.type_id,
            type_name=type_def.name,
            usage_count=usage_count,
            creation_count=creation_count,
            conversion_count=conversion_count,
            error_count=error_count,
            last_used=last_used,
            avg_performance=avg_performance,
            popularity_score=max(0, popularity_score)
        )
    
    def _calculate_category_statistics(self, type_stats: Dict[str, TypeStatistics]) -> Dict[str, CategoryStatistics]:
        """Calculate statistics by category"""
        categories = {}
        
        # Group types by category
        for type_id, stats in type_stats.items():
            try:
                type_def = self.registry.get_type(type_id)
                category = type_def.category
                
                if category not in categories:
                    categories[category] = []
                categories[category].append(stats)
            except:
                continue
        
        # Calculate category statistics
        category_stats = {}
        for category, stats_list in categories.items():
            total_usage = sum(s.usage_count for s in stats_list)
            type_count = len(stats_list)
            avg_usage = total_usage / type_count if type_count > 0 else 0
            
            # Find most and least popular types
            most_popular = max(stats_list, key=lambda s: s.popularity_score) if stats_list else None
            least_popular = min(stats_list, key=lambda s: s.popularity_score) if stats_list else None
            
            category_stats[category] = CategoryStatistics(
                category=category,
                type_count=type_count,
                total_usage=total_usage,
                avg_usage_per_type=avg_usage,
                most_popular_type=most_popular.type_name if most_popular else "N/A",
                least_popular_type=least_popular.type_name if least_popular else "N/A"
            )
        
        return category_stats
    
    def _calculate_system_statistics(self, type_stats: Dict[str, TypeStatistics]) -> SystemStatistics:
        """Calculate overall system statistics"""
        total_types = len(type_stats)
        total_usage = sum(s.usage_count for s in type_stats.values())
        total_operations = sum(s.usage_count + s.creation_count + s.conversion_count 
                             for s in type_stats.values())
        total_errors = sum(s.error_count for s in type_stats.values())
        
        # Count active vs inactive types
        active_types = len([s for s in type_stats.values() if s.usage_count > 0])
        inactive_types = total_types - active_types
        
        # Calculate error rate
        error_rate = total_errors / total_operations if total_operations > 0 else 0
        
        # Estimate average operations per day (simplified)
        # In a real implementation, this would use actual time ranges
        avg_operations_per_day = total_operations / 30 if total_operations > 0 else 0
        
        # Estimate uptime (simplified)
        uptime_days = 30  # Placeholder
        
        return SystemStatistics(
            total_types=total_types,
            total_usage=total_usage,
            total_operations=total_operations,
            avg_operations_per_day=avg_operations_per_day,
            active_types=active_types,
            inactive_types=inactive_types,
            error_rate=error_rate,
            uptime_days=uptime_days
        )


class StatisticsCard(QFrame):
    """Card widget for displaying a single statistic"""
    
    def __init__(self, title: str, value: str, subtitle: str = "", color: str = "#0078d4", parent=None):
        super().__init__(parent)
        
        self.setup_ui(title, value, subtitle, color)
    
    def setup_ui(self, title: str, value: str, subtitle: str, color: str):
        """Setup the card UI"""
        self.setFixedSize(200, 120)
        self.setFrameStyle(QFrame.Shape.Box)
        self.setStyleSheet(f"""
            QFrame {{
                border: 1px solid #ddd;
                border-radius: 8px;
                background: white;
                padding: 8px;
            }}
            QFrame:hover {{
                border-color: {color};
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(4)
        
        # Title
        title_label = QLabel(title)
        title_label.setFont(QFont("", 9))
        title_label.setStyleSheet("color: #666;")
        layout.addWidget(title_label)
        
        # Value
        value_label = QLabel(value)
        value_label.setFont(QFont("", 18, QFont.Weight.Bold))
        value_label.setStyleSheet(f"color: {color};")
        layout.addWidget(value_label)
        
        # Subtitle
        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setFont(QFont("", 8))
            subtitle_label.setStyleSheet("color: #999;")
            layout.addWidget(subtitle_label)
        
        layout.addStretch()


class TypeStatisticsDashboard(QWidget):
    """Statistics and analytics dashboard for type usage"""
    
    refresh_requested = pyqtSignal()
    type_selected = pyqtSignal(str)  # type_id
    
    def __init__(self, registry: TypeRegistry = None, parent=None):
        super().__init__(parent)
        
        self.registry = registry or get_type_registry()
        self.operations = TypeOperations()
        self.metadata_manager = get_metadata_manager()
        
        # State
        self.statistics_data: Optional[Dict[str, Any]] = None
        self.calculator: Optional[StatisticsCalculator] = None
        self.auto_refresh_timer = QTimer()
        self.auto_refresh_timer.timeout.connect(self.refresh_statistics)
        
        self.setup_ui()
        self.setup_connections()
        self.refresh_statistics()
    
    def setup_ui(self):
        """Setup user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Header
        header_layout = QHBoxLayout()
        
        # Title
        title = QLabel("Type Statistics Dashboard")
        title.setFont(QFont("", 14, QFont.Weight.Bold))
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Auto-refresh controls
        header_layout.addWidget(QLabel("Auto-refresh:"))
        self.refresh_combo = QComboBox()
        self.refresh_combo.addItems(["Off", "30s", "1m", "5m", "15m"])
        self.refresh_combo.setCurrentText("5m")
        header_layout.addWidget(self.refresh_combo)
        
        # Refresh button
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setIcon(QIcon(":/icons/refresh.png"))
        header_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(header_layout)
        
        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Main content
        self.tab_widget = QTabWidget()
        
        # Overview tab
        self.overview_tab = self.create_overview_tab()
        self.tab_widget.addTab(self.overview_tab, "Overview")
        
        # Type details tab
        self.details_tab = self.create_details_tab()
        self.tab_widget.addTab(self.details_tab, "Type Details")
        
        # Category analysis tab
        self.category_tab = self.create_category_tab()
        self.tab_widget.addTab(self.category_tab, "Categories")
        
        # Trends tab
        self.trends_tab = self.create_trends_tab()
        self.tab_widget.addTab(self.trends_tab, "Trends")
        
        layout.addWidget(self.tab_widget)
    
    def create_overview_tab(self) -> QWidget:
        """Create overview tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # System statistics cards
        self.system_cards_layout = QHBoxLayout()
        layout.addLayout(self.system_cards_layout)
        
        # Charts section
        charts_layout = QHBoxLayout()
        
        # Category distribution chart
        self.category_chart_view = QChartView()
        self.category_chart_view.setMinimumSize(300, 250)
        charts_layout.addWidget(self.category_chart_view)
        
        # Usage trends chart
        self.usage_chart_view = QChartView()
        self.usage_chart_view.setMinimumSize(300, 250)
        charts_layout.addWidget(self.usage_chart_view)
        
        layout.addLayout(charts_layout)
        
        # Recent activity
        activity_group = QGroupBox("Recent Activity")
        activity_layout = QVBoxLayout(activity_group)
        
        self.activity_list = QTextEdit()
        self.activity_list.setMaximumHeight(150)
        self.activity_list.setReadOnly(True)
        activity_layout.addWidget(self.activity_list)
        
        layout.addWidget(activity_group)
        
        return widget
    
    def create_details_tab(self) -> QWidget:
        """Create type details tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        # Sort controls
        controls_layout.addWidget(QLabel("Sort by:"))
        self.sort_combo = QComboBox()
        self.sort_combo.addItems([
            "Popularity", "Usage Count", "Name", "Category", 
            "Last Used", "Error Rate", "Performance"
        ])
        controls_layout.addWidget(self.sort_combo)
        
        # Filter controls
        controls_layout.addWidget(QLabel("Filter:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All Types", "Active Only", "Unused", "High Errors"])
        controls_layout.addWidget(self.filter_combo)
        
        controls_layout.addStretch()
        
        layout.addLayout(controls_layout)
        
        # Types table
        self.types_table = QTableWidget()
        self.types_table.setColumnCount(8)
        self.types_table.setHorizontalHeaderLabels([
            "Type", "Category", "Usage", "Created", "Converted", 
            "Errors", "Last Used", "Performance"
        ])
        
        # Configure table
        header = self.types_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        
        self.types_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.types_table.setAlternatingRowColors(True)
        self.types_table.setSortingEnabled(True)
        
        layout.addWidget(self.types_table)
        
        return widget
    
    def create_category_tab(self) -> QWidget:
        """Create category analysis tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Category summary
        self.category_summary_layout = QGridLayout()
        layout.addLayout(self.category_summary_layout)
        
        # Category comparison chart
        self.category_comparison_view = QChartView()
        self.category_comparison_view.setMinimumHeight(300)
        layout.addWidget(self.category_comparison_view)
        
        return widget
    
    def create_trends_tab(self) -> QWidget:
        """Create trends analysis tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Time range controls
        controls_layout = QHBoxLayout()
        
        controls_layout.addWidget(QLabel("Time Range:"))
        self.time_range_combo = QComboBox()
        self.time_range_combo.addItems(["Last 7 Days", "Last 30 Days", "Last 90 Days", "All Time"])
        controls_layout.addWidget(self.time_range_combo)
        
        controls_layout.addStretch()
        
        layout.addLayout(controls_layout)
        
        # Trends chart
        self.trends_chart_view = QChartView()
        self.trends_chart_view.setMinimumHeight(400)
        layout.addWidget(self.trends_chart_view)
        
        return widget
    
    def setup_connections(self):
        """Setup signal connections"""
        self.refresh_btn.clicked.connect(self.refresh_statistics)
        self.refresh_combo.currentTextChanged.connect(self._update_auto_refresh)
        self.sort_combo.currentTextChanged.connect(self._update_type_table)
        self.filter_combo.currentTextChanged.connect(self._update_type_table)
        self.types_table.itemSelectionChanged.connect(self._on_type_selection_changed)
    
    def refresh_statistics(self):
        """Refresh all statistics"""
        if self.calculator and self.calculator.isRunning():
            self.calculator.stop()
            self.calculator.wait()
        
        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Start calculation
        self.calculator = StatisticsCalculator(self.registry, self.operations)
        self.calculator.statistics_calculated.connect(self._on_statistics_calculated)
        self.calculator.progress_updated.connect(self.progress_bar.setValue)
        self.calculator.error_occurred.connect(self._on_calculation_error)
        self.calculator.start()
    
    @pyqtSlot(dict)
    def _on_statistics_calculated(self, data: Dict[str, Any]):
        """Handle calculated statistics"""
        self.statistics_data = data
        self.progress_bar.setVisible(False)
        
        # Update all displays
        self._update_overview_tab()
        self._update_details_tab()
        self._update_category_tab()
        self._update_trends_tab()
    
    @pyqtSlot(str)
    def _on_calculation_error(self, error: str):
        """Handle calculation error"""
        self.progress_bar.setVisible(False)
        # Could show error message to user
        print(f"Statistics calculation error: {error}")
    
    def _update_overview_tab(self):
        """Update overview tab with new data"""
        if not self.statistics_data:
            return
        
        system_stats = self.statistics_data['system_statistics']
        
        # Clear existing cards
        for i in reversed(range(self.system_cards_layout.count())):
            self.system_cards_layout.itemAt(i).widget().setParent(None)
        
        # Create system statistics cards
        cards_data = [
            ("Total Types", str(system_stats.total_types), "Registered", "#0078d4"),
            ("Total Usage", f"{system_stats.total_usage:,}", "Operations", "#107c10"),
            ("Active Types", str(system_stats.active_types), f"{system_stats.inactive_types} inactive", "#ff8c00"),
            ("Error Rate", f"{system_stats.error_rate:.1%}", "Of all operations", "#d13438"),
            ("Avg/Day", f"{system_stats.avg_operations_per_day:.0f}", "Operations", "#5c2d91")
        ]
        
        for title, value, subtitle, color in cards_data:
            card = StatisticsCard(title, value, subtitle, color)
            self.system_cards_layout.addWidget(card)
        
        # Update charts
        self._update_category_distribution_chart()
        self._update_activity_list()
    
    def _update_details_tab(self):
        """Update type details tab"""
        if not self.statistics_data:
            return
        
        self._update_type_table()
    
    def _update_category_tab(self):
        """Update category analysis tab"""
        if not self.statistics_data:
            return
        
        category_stats = self.statistics_data['category_statistics']
        
        # Clear existing summary
        for i in reversed(range(self.category_summary_layout.count())):
            self.category_summary_layout.itemAt(i).widget().setParent(None)
        
        # Create category summary cards
        row = 0
        for category, stats in category_stats.items():
            card = StatisticsCard(
                category.title(),
                str(stats.type_count),
                f"{stats.total_usage} total usage",
                "#0078d4"
            )
            self.category_summary_layout.addWidget(card, row // 3, row % 3)
            row += 1
        
        # Update category comparison chart
        self._update_category_comparison_chart()
    
    def _update_trends_tab(self):
        """Update trends analysis tab"""
        if not self.statistics_data:
            return
        
        # Update trends chart
        self._update_trends_chart()
    
    def _update_type_table(self):
        """Update the type details table"""
        if not self.statistics_data:
            return
        
        type_stats = self.statistics_data['type_statistics']
        
        # Apply filtering
        filtered_stats = self._filter_type_statistics(type_stats)
        
        # Apply sorting
        sorted_stats = self._sort_type_statistics(filtered_stats)
        
        # Update table
        self.types_table.setRowCount(len(sorted_stats))
        
        for row, stats in enumerate(sorted_stats):
            # Type name
            self.types_table.setItem(row, 0, QTableWidgetItem(stats.type_name))
            
            # Category
            try:
                type_def = self.registry.get_type(stats.type_id)
                category = type_def.category.title()
            except:
                category = "Unknown"
            self.types_table.setItem(row, 1, QTableWidgetItem(category))
            
            # Usage count
            usage_item = QTableWidgetItem()
            usage_item.setData(Qt.ItemDataRole.DisplayRole, stats.usage_count)
            self.types_table.setItem(row, 2, usage_item)
            
            # Creation count
            creation_item = QTableWidgetItem()
            creation_item.setData(Qt.ItemDataRole.DisplayRole, stats.creation_count)
            self.types_table.setItem(row, 3, creation_item)
            
            # Conversion count
            conversion_item = QTableWidgetItem()
            conversion_item.setData(Qt.ItemDataRole.DisplayRole, stats.conversion_count)
            self.types_table.setItem(row, 4, conversion_item)
            
            # Error count
            error_item = QTableWidgetItem()
            error_item.setData(Qt.ItemDataRole.DisplayRole, stats.error_count)
            if stats.error_count > 0:
                error_item.setBackground(QColor(255, 235, 238))
            self.types_table.setItem(row, 5, error_item)
            
            # Last used
            last_used = stats.last_used.strftime("%Y-%m-%d %H:%M") if stats.last_used else "Never"
            self.types_table.setItem(row, 6, QTableWidgetItem(last_used))
            
            # Performance
            performance = f"{stats.avg_performance:.2f}ms" if stats.avg_performance > 0 else "N/A"
            self.types_table.setItem(row, 7, QTableWidgetItem(performance))
            
            # Store type ID for selection
            self.types_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, stats.type_id)
    
    def _filter_type_statistics(self, type_stats: Dict[str, TypeStatistics]) -> List[TypeStatistics]:
        """Filter type statistics based on current filter"""
        filter_type = self.filter_combo.currentText()
        stats_list = list(type_stats.values())
        
        if filter_type == "Active Only":
            return [s for s in stats_list if s.usage_count > 0]
        elif filter_type == "Unused":
            return [s for s in stats_list if s.usage_count == 0]
        elif filter_type == "High Errors":
            return [s for s in stats_list if s.error_count > 0]
        else:  # "All Types"
            return stats_list
    
    def _sort_type_statistics(self, stats_list: List[TypeStatistics]) -> List[TypeStatistics]:
        """Sort type statistics based on current sort option"""
        sort_type = self.sort_combo.currentText()
        
        if sort_type == "Popularity":
            return sorted(stats_list, key=lambda s: s.popularity_score, reverse=True)
        elif sort_type == "Usage Count":
            return sorted(stats_list, key=lambda s: s.usage_count, reverse=True)
        elif sort_type == "Name":
            return sorted(stats_list, key=lambda s: s.type_name)
        elif sort_type == "Category":
            return sorted(stats_list, key=lambda s: (
                self.registry.get_type(s.type_id).category if s.type_id in [t.type_id for t in self.registry.list_types().values()] else "zzz",
                s.type_name
            ))
        elif sort_type == "Last Used":
            return sorted(stats_list, key=lambda s: s.last_used or datetime.min, reverse=True)
        elif sort_type == "Error Rate":
            return sorted(stats_list, key=lambda s: s.error_count, reverse=True)
        elif sort_type == "Performance":
            return sorted(stats_list, key=lambda s: s.avg_performance, reverse=True)
        else:
            return stats_list
    
    def _update_category_distribution_chart(self):
        """Update category distribution pie chart"""
        if not self.statistics_data:
            return
        
        category_stats = self.statistics_data['category_statistics']
        
        # Create pie series
        series = QPieSeries()
        
        for category, stats in category_stats.items():
            slice = series.append(f"{category.title()} ({stats.type_count})", stats.type_count)
            
            # Set colors based on category
            color_map = {
                'content': QColor(52, 152, 219),
                'layout': QColor(46, 204, 113),
                'media': QColor(155, 89, 182),
                'interactive': QColor(241, 196, 15),
                'metadata': QColor(231, 76, 60),
                'structure': QColor(149, 165, 166)
            }
            
            if category in color_map:
                slice.setBrush(QBrush(color_map[category]))
        
        # Create chart
        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("Type Distribution by Category")
        chart.legend().setAlignment(Qt.AlignmentFlag.AlignRight)
        
        self.category_chart_view.setChart(chart)
    
    def _update_category_comparison_chart(self):
        """Update category comparison bar chart"""
        if not self.statistics_data:
            return
        
        category_stats = self.statistics_data['category_statistics']
        
        # Create bar series
        series = QBarSeries()
        
        type_count_set = QBarSet("Type Count")
        usage_set = QBarSet("Total Usage")
        
        categories = []
        for category, stats in category_stats.items():
            categories.append(category.title())
            type_count_set.append(stats.type_count)
            usage_set.append(stats.total_usage)
        
        series.append(type_count_set)
        series.append(usage_set)
        
        # Create chart
        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("Category Comparison")
        chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
        
        self.category_comparison_view.setChart(chart)
    
    def _update_trends_chart(self):
        """Update trends line chart"""
        # This would show usage trends over time
        # For now, create placeholder chart
        
        series = QLineSeries()
        series.setName("Usage Trend")
        
        # Placeholder data
        for i in range(30):
            series.append(i, i * 2 + (i % 5) * 10)
        
        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("Usage Trends Over Time")
        chart.createDefaultAxes()
        
        self.trends_chart_view.setChart(chart)
    
    def _update_activity_list(self):
        """Update recent activity list"""
        # Get recent operations
        recent_operations = self.operations.get_operation_history(limit=10)
        
        activity_text = ""
        for op in recent_operations:
            timestamp = op.timestamp.strftime("%H:%M:%S")
            activity_text += f"{timestamp} - {op.operation_type.value.title()} operation on {op.target_type_id}\n"
        
        if not activity_text:
            activity_text = "No recent activity"
        
        self.activity_list.setPlainText(activity_text)
    
    def _update_auto_refresh(self, interval: str):
        """Update auto-refresh interval"""
        self.auto_refresh_timer.stop()
        
        if interval == "30s":
            self.auto_refresh_timer.start(30000)
        elif interval == "1m":
            self.auto_refresh_timer.start(60000)
        elif interval == "5m":
            self.auto_refresh_timer.start(300000)
        elif interval == "15m":
            self.auto_refresh_timer.start(900000)
    
    def _on_type_selection_changed(self):
        """Handle type selection in table"""
        current_row = self.types_table.currentRow()
        if current_row >= 0:
            item = self.types_table.item(current_row, 0)
            if item:
                type_id = item.data(Qt.ItemDataRole.UserRole)
                if type_id:
                    self.type_selected.emit(type_id)
    
    def get_statistics_summary(self) -> Optional[Dict[str, Any]]:
        """Get current statistics summary"""
        return self.statistics_data
    
    def export_statistics(self, format: str = "csv") -> str:
        """Export statistics to file"""
        if not self.statistics_data:
            return ""
        
        # Implementation would export data in specified format
        # For now, return placeholder
        return "Statistics exported successfully"