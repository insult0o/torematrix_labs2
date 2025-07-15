"""Property Panel Help System

Provides comprehensive in-application help, tooltips, and guidance for the property panel
with contextual assistance and interactive tutorials.
"""

from typing import Dict, List, Any, Optional, Callable
from enum import Enum
from dataclasses import dataclass
from PyQt6.QtWidgets import (
    QWidget, QDialog, QVBoxLayout, QHBoxLayout, QTextBrowser, QLabel,
    QPushButton, QTabWidget, QTreeWidget, QTreeWidgetItem, QSplitter,
    QLineEdit, QFrame, QScrollArea, QToolTip, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QTimer, QPoint, QRect, QUrl
from PyQt6.QtGui import QFont, QPixmap, QIcon, QKeySequence, QCursor


class HelpTopicType(Enum):
    """Types of help topics"""
    OVERVIEW = "overview"
    TUTORIAL = "tutorial"
    REFERENCE = "reference"
    TROUBLESHOOTING = "troubleshooting"
    SHORTCUT = "shortcut"
    TIP = "tip"


@dataclass
class HelpTopic:
    """Help topic definition"""
    id: str
    title: str
    content: str
    topic_type: HelpTopicType
    keywords: List[str]
    related_topics: List[str] = None
    difficulty: str = "beginner"  # beginner, intermediate, advanced
    estimated_time: int = 5  # minutes
    
    def __post_init__(self):
        if self.related_topics is None:
            self.related_topics = []


class PropertyPanelHelpSystem(QObject):
    """Comprehensive help system for the property panel"""
    
    # Signals
    help_requested = pyqtSignal(str)  # topic_id
    tutorial_started = pyqtSignal(str)  # tutorial_id
    tooltip_shown = pyqtSignal(str, QPoint)  # content, position
    
    def __init__(self, property_panel: QWidget):
        super().__init__()
        self.property_panel = property_panel
        self.help_topics: Dict[str, HelpTopic] = {}
        self.contextual_tips: Dict[str, str] = {}
        self.help_dialog: Optional['PropertyPanelHelpDialog'] = None
        
        # Tooltip settings
        self.tooltip_enabled = True
        self.tooltip_delay = 1000  # milliseconds
        self.tooltip_timer = QTimer()
        self.tooltip_timer.setSingleShot(True)
        self.tooltip_timer.timeout.connect(self._show_contextual_tooltip)
        
        # Help content
        self._setup_help_content()
        self._setup_contextual_tips()
        
        # Install event filter for contextual help
        if self.property_panel:
            self.property_panel.installEventFilter(self)
    
    def _setup_help_content(self) -> None:
        """Setup help content topics"""
        # Overview topics
        self.add_help_topic(HelpTopic(
            id="overview",
            title="Property Panel Overview",
            content="""
            <h2>Property Panel Overview</h2>
            <p>The Property Panel provides a comprehensive interface for viewing and editing document element properties.</p>
            
            <h3>Key Features:</h3>
            <ul>
                <li><strong>Multi-element Selection:</strong> Edit properties across multiple elements simultaneously</li>
                <li><strong>Batch Operations:</strong> Apply changes to many elements at once</li>
                <li><strong>Import/Export:</strong> Share property data in multiple formats</li>
                <li><strong>Accessibility:</strong> Full keyboard navigation and screen reader support</li>
                <li><strong>Theming:</strong> Customizable appearance with light, dark, and high contrast modes</li>
            </ul>
            
            <h3>Getting Started:</h3>
            <ol>
                <li>Select one or more elements from the document viewer or element list</li>
                <li>Properties will automatically appear in the property panel</li>
                <li>Click on any property value to edit it</li>
                <li>Use keyboard shortcuts for efficient navigation</li>
            </ol>
            """,
            topic_type=HelpTopicType.OVERVIEW,
            keywords=["overview", "introduction", "getting started", "features"],
            difficulty="beginner",
            estimated_time=3
        ))
        
        # Tutorial topics
        self.add_help_topic(HelpTopic(
            id="basic_editing",
            title="Basic Property Editing Tutorial",
            content="""
            <h2>Basic Property Editing</h2>
            <p>Learn how to edit element properties effectively.</p>
            
            <h3>Step 1: Select Elements</h3>
            <p>Click on an element in the document viewer or element list to select it. Hold Ctrl to select multiple elements.</p>
            
            <h3>Step 2: Navigate Properties</h3>
            <p>Use Tab/Shift+Tab to move between properties, or click directly on a property name.</p>
            
            <h3>Step 3: Edit Values</h3>
            <p>Double-click a property value or press F2 to start editing. Different property types have specialized editors:</p>
            <ul>
                <li><strong>Text:</strong> Direct text input with validation</li>
                <li><strong>Numbers:</strong> Numeric input with range validation</li>
                <li><strong>Boolean:</strong> Checkbox or toggle switch</li>
                <li><strong>Choice:</strong> Dropdown selection or radio buttons</li>
            </ul>
            
            <h3>Step 4: Save Changes</h3>
            <p>Press Enter to save changes or Escape to cancel. Changes are automatically validated.</p>
            """,
            topic_type=HelpTopicType.TUTORIAL,
            keywords=["editing", "tutorial", "properties", "basic"],
            difficulty="beginner",
            estimated_time=5
        ))
        
        self.add_help_topic(HelpTopic(
            id="batch_editing",
            title="Batch Editing Tutorial",
            content="""
            <h2>Batch Editing Multiple Elements</h2>
            <p>Learn how to efficiently edit multiple elements at once.</p>
            
            <h3>Step 1: Select Multiple Elements</h3>
            <p>Hold Ctrl and click multiple elements, or use Ctrl+A to select all elements.</p>
            
            <h3>Step 2: Open Batch Editor</h3>
            <p>Press Ctrl+B or click the "Batch Edit" button when multiple elements are selected.</p>
            
            <h3>Step 3: Configure Operation</h3>
            <p>Choose the operation type:</p>
            <ul>
                <li><strong>Set Value:</strong> Replace property values across all elements</li>
                <li><strong>Append:</strong> Add text to existing property values</li>
                <li><strong>Replace:</strong> Find and replace text within properties</li>
                <li><strong>Clear:</strong> Remove property values</li>
            </ul>
            
            <h3>Step 4: Set Conditions (Optional)</h3>
            <p>Add conditions to control which elements are affected:
            <code>value != null && value.length > 0</code></p>
            
            <h3>Step 5: Execute</h3>
            <p>Click "Apply" to execute the batch operation with progress tracking.</p>
            """,
            topic_type=HelpTopicType.TUTORIAL,
            keywords=["batch", "editing", "multiple", "elements"],
            difficulty="intermediate",
            estimated_time=8
        ))
        
        # Reference topics
        self.add_help_topic(HelpTopic(
            id="keyboard_shortcuts",
            title="Keyboard Shortcuts Reference",
            content="""
            <h2>Keyboard Shortcuts</h2>
            
            <h3>Panel Management</h3>
            <table>
                <tr><td><kbd>F4</kbd></td><td>Toggle property panel visibility</td></tr>
                <tr><td><kbd>Ctrl+P</kbd></td><td>Focus property panel</td></tr>
                <tr><td><kbd>Ctrl+Shift+P</kbd></td><td>Pin/unpin panel</td></tr>
                <tr><td><kbd>Ctrl+Alt+←</kbd></td><td>Dock panel to left</td></tr>
                <tr><td><kbd>Ctrl+Alt+→</kbd></td><td>Dock panel to right</td></tr>
                <tr><td><kbd>Ctrl+Alt+↓</kbd></td><td>Dock panel to bottom</td></tr>
                <tr><td><kbd>Ctrl+Alt+F</kbd></td><td>Float panel</td></tr>
            </table>
            
            <h3>Navigation</h3>
            <table>
                <tr><td><kbd>Tab</kbd></td><td>Next property</td></tr>
                <tr><td><kbd>Shift+Tab</kbd></td><td>Previous property</td></tr>
                <tr><td><kbd>Ctrl+Home</kbd></td><td>First property</td></tr>
                <tr><td><kbd>Ctrl+End</kbd></td><td>Last property</td></tr>
                <tr><td><kbd>Ctrl+F</kbd></td><td>Focus search</td></tr>
            </table>
            
            <h3>Editing</h3>
            <table>
                <tr><td><kbd>F2</kbd></td><td>Start editing property</td></tr>
                <tr><td><kbd>Enter</kbd></td><td>Commit changes</td></tr>
                <tr><td><kbd>Escape</kbd></td><td>Cancel editing</td></tr>
                <tr><td><kbd>Ctrl+Z</kbd></td><td>Undo last change</td></tr>
                <tr><td><kbd>Ctrl+Y</kbd></td><td>Redo change</td></tr>
            </table>
            
            <h3>Batch Operations</h3>
            <table>
                <tr><td><kbd>Ctrl+A</kbd></td><td>Select all elements</td></tr>
                <tr><td><kbd>Ctrl+B</kbd></td><td>Open batch editor</td></tr>
                <tr><td><kbd>Ctrl+Enter</kbd></td><td>Execute batch operation</td></tr>
            </table>
            
            <h3>Accessibility</h3>
            <table>
                <tr><td><kbd>Ctrl+Shift+Space</kbd></td><td>Announce current focus</td></tr>
                <tr><td><kbd>Ctrl+Alt+H</kbd></td><td>Toggle high contrast</td></tr>
                <tr><td><kbd>Ctrl++</kbd></td><td>Increase font size</td></tr>
                <tr><td><kbd>Ctrl+-</kbd></td><td>Decrease font size</td></tr>
            </table>
            """,
            topic_type=HelpTopicType.REFERENCE,
            keywords=["shortcuts", "keyboard", "hotkeys", "reference"],
            difficulty="all",
            estimated_time=2
        ))
        
        # Troubleshooting topics
        self.add_help_topic(HelpTopic(
            id="troubleshooting",
            title="Common Issues and Solutions",
            content="""
            <h2>Troubleshooting Guide</h2>
            
            <h3>Property Panel Not Visible</h3>
            <p><strong>Solution:</strong></p>
            <ol>
                <li>Press <kbd>F4</kbd> to toggle panel visibility</li>
                <li>Check View menu → Property Panel → Show Property Panel</li>
                <li>If panel is floating, look for it outside the main window</li>
                <li>Reset workspace layout: View → Reset Layout</li>
            </ol>
            
            <h3>Keyboard Shortcuts Not Working</h3>
            <p><strong>Solution:</strong></p>
            <ol>
                <li>Ensure property panel has focus (click on it or press <kbd>Ctrl+P</kbd>)</li>
                <li>Check for conflicting shortcuts in other applications</li>
                <li>Verify shortcuts in Help → Keyboard Shortcuts</li>
                <li>Restart application if shortcuts are completely unresponsive</li>
            </ol>
            
            <h3>Batch Operations Failing</h3>
            <p><strong>Solution:</strong></p>
            <ol>
                <li>Verify multiple elements are selected</li>
                <li>Check operation conditions for syntax errors</li>
                <li>Ensure property names are spelled correctly</li>
                <li>Review error messages in the batch editor</li>
            </ol>
            
            <h3>Import/Export Issues</h3>
            <p><strong>Solution:</strong></p>
            <ol>
                <li>Verify file format is supported (JSON, CSV, XML, Pickle, Excel, YAML)</li>
                <li>Check file permissions and disk space</li>
                <li>Validate data structure matches expected format</li>
                <li>Try exporting to same format first to see expected structure</li>
            </ol>
            
            <h3>Performance Issues</h3>
            <p><strong>Solution:</strong></p>
            <ol>
                <li>Reduce number of visible properties by collapsing groups</li>
                <li>Use batch operations instead of individual edits for large datasets</li>
                <li>Enable pagination for large element lists</li>
                <li>Consider disabling animations in settings</li>
            </ol>
            """,
            topic_type=HelpTopicType.TROUBLESHOOTING,
            keywords=["troubleshooting", "problems", "issues", "solutions", "help"],
            difficulty="all",
            estimated_time=5
        ))
    
    def _setup_contextual_tips(self) -> None:
        """Setup contextual tips for UI elements"""
        self.contextual_tips = {
            "property_editor": "Double-click to edit this property value. Use Tab to navigate between properties.",
            "batch_editor": "Select multiple elements to enable batch editing operations.",
            "import_button": "Import property data from JSON, CSV, XML, or Excel files.",
            "export_button": "Export current property data to various formats for backup or sharing.",
            "search_box": "Type to search properties by name or value. Use wildcards (*) for pattern matching.",
            "property_group": "Click to expand/collapse property group. Use Ctrl+Shift+Plus to expand all.",
            "accessibility_toggle": "Enable accessibility features including screen reader support and high contrast mode.",
            "theme_selector": "Choose from light, dark, high contrast, or automatic theme based on system settings."
        }
    
    def add_help_topic(self, topic: HelpTopic) -> None:
        """Add a help topic to the system"""
        self.help_topics[topic.id] = topic
    
    def show_help_dialog(self, topic_id: Optional[str] = None) -> None:
        """Show the main help dialog"""
        if not self.help_dialog:
            self.help_dialog = PropertyPanelHelpDialog(self, self.property_panel)
        
        if topic_id and topic_id in self.help_topics:
            self.help_dialog.show_topic(topic_id)
        
        self.help_dialog.show()
        self.help_dialog.raise_()
        self.help_dialog.activateWindow()
    
    def show_contextual_help(self, widget: QWidget) -> None:
        """Show contextual help for a specific widget"""
        widget_type = self._identify_widget_type(widget)
        if widget_type in self.contextual_tips:
            tip_text = self.contextual_tips[widget_type]
            QToolTip.showText(QCursor.pos(), tip_text, widget, QRect(), 5000)
            self.tooltip_shown.emit(tip_text, QCursor.pos())
    
    def search_help(self, query: str) -> List[HelpTopic]:
        """Search help topics by query"""
        results = []
        query_lower = query.lower()
        
        for topic in self.help_topics.values():
            # Search in title, keywords, and content
            if (query_lower in topic.title.lower() or
                any(query_lower in keyword.lower() for keyword in topic.keywords) or
                query_lower in topic.content.lower()):
                results.append(topic)
        
        # Sort by relevance (simple scoring based on title match)
        results.sort(key=lambda t: 0 if query_lower in t.title.lower() else 1)
        return results
    
    def get_topic_by_id(self, topic_id: str) -> Optional[HelpTopic]:
        """Get help topic by ID"""
        return self.help_topics.get(topic_id)
    
    def get_topics_by_type(self, topic_type: HelpTopicType) -> List[HelpTopic]:
        """Get all topics of a specific type"""
        return [topic for topic in self.help_topics.values() if topic.topic_type == topic_type]
    
    def set_tooltip_enabled(self, enabled: bool) -> None:
        """Enable or disable contextual tooltips"""
        self.tooltip_enabled = enabled
    
    def set_tooltip_delay(self, delay: int) -> None:
        """Set tooltip delay in milliseconds"""
        self.tooltip_delay = delay
    
    def eventFilter(self, obj: QObject, event) -> bool:
        """Handle events for contextual help"""
        if not self.tooltip_enabled:
            return False
        
        if event.type() == event.Type.Enter:
            if isinstance(obj, QWidget):
                self.tooltip_timer.stop()
                self.tooltip_timer.start(self.tooltip_delay)
                self._hovered_widget = obj
        elif event.type() == event.Type.Leave:
            self.tooltip_timer.stop()
            
        return False
    
    def _show_contextual_tooltip(self) -> None:
        """Show contextual tooltip for hovered widget"""
        if hasattr(self, '_hovered_widget'):
            self.show_contextual_help(self._hovered_widget)
    
    def _identify_widget_type(self, widget: QWidget) -> str:
        """Identify widget type for contextual help"""
        widget_name = widget.objectName().lower()
        class_name = widget.__class__.__name__.lower()
        
        # Map widget characteristics to help context
        if "editor" in widget_name or "edit" in class_name:
            return "property_editor"
        elif "batch" in widget_name:
            return "batch_editor"
        elif "import" in widget_name:
            return "import_button"
        elif "export" in widget_name:
            return "export_button"
        elif "search" in widget_name:
            return "search_box"
        elif "group" in widget_name or "groupbox" in class_name:
            return "property_group"
        else:
            return "general"


class PropertyPanelHelpDialog(QDialog):
    """Main help dialog for the property panel"""
    
    def __init__(self, help_system: PropertyPanelHelpSystem, parent=None):
        super().__init__(parent)
        self.help_system = help_system
        self.current_topic = None
        
        self.setWindowTitle("Property Panel Help")
        self.setModal(False)
        self.resize(800, 600)
        
        self._setup_ui()
        self._populate_topics()
    
    def _setup_ui(self) -> None:
        """Setup help dialog UI"""
        layout = QVBoxLayout(self)
        
        # Create splitter for navigation and content
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)
        
        # Left panel: Navigation
        nav_panel = self._create_navigation_panel()
        splitter.addWidget(nav_panel)
        
        # Right panel: Content
        content_panel = self._create_content_panel()
        splitter.addWidget(content_panel)
        
        # Set splitter proportions
        splitter.setSizes([250, 550])
        
        # Button box
        button_layout = QHBoxLayout()
        
        self.print_btn = QPushButton("Print")
        self.print_btn.clicked.connect(self._print_help)
        button_layout.addWidget(self.print_btn)
        
        button_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def _create_navigation_panel(self) -> QWidget:
        """Create navigation panel with topic tree and search"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Search box
        search_label = QLabel("Search Help:")
        layout.addWidget(search_label)
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Enter search terms...")
        self.search_edit.textChanged.connect(self._search_topics)
        layout.addWidget(self.search_edit)
        
        # Topic tree
        self.topic_tree = QTreeWidget()
        self.topic_tree.setHeaderLabel("Help Topics")
        self.topic_tree.itemClicked.connect(self._on_topic_selected)
        layout.addWidget(self.topic_tree)
        
        return panel
    
    def _create_content_panel(self) -> QWidget:
        """Create content panel with topic display"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Topic title
        self.topic_title = QLabel()
        self.topic_title.setFont(QFont("", 14, QFont.Weight.Bold))
        layout.addWidget(self.topic_title)
        
        # Topic metadata
        self.topic_meta = QLabel()
        self.topic_meta.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(self.topic_meta)
        
        # Content browser
        self.content_browser = QTextBrowser()
        self.content_browser.setOpenExternalLinks(True)
        layout.addWidget(self.content_browser)
        
        # Related topics
        self.related_label = QLabel("Related Topics:")
        self.related_label.setFont(QFont("", 10, QFont.Weight.Bold))
        layout.addWidget(self.related_label)
        
        self.related_list = QTreeWidget()
        self.related_list.setHeaderLabel("Related")
        self.related_list.setMaximumHeight(100)
        self.related_list.itemClicked.connect(self._on_related_topic_selected)
        layout.addWidget(self.related_list)
        
        return panel
    
    def _populate_topics(self) -> None:
        """Populate topic tree with help topics"""
        self.topic_tree.clear()
        
        # Group topics by type
        topic_groups = {}
        for topic in self.help_system.help_topics.values():
            group_name = topic.topic_type.value.title()
            if group_name not in topic_groups:
                topic_groups[group_name] = []
            topic_groups[group_name].append(topic)
        
        # Create tree items
        for group_name, topics in topic_groups.items():
            group_item = QTreeWidgetItem([group_name])
            group_item.setExpanded(True)
            self.topic_tree.addTopLevelItem(group_item)
            
            for topic in sorted(topics, key=lambda t: t.title):
                topic_item = QTreeWidgetItem([topic.title])
                topic_item.setData(0, Qt.ItemDataRole.UserRole, topic.id)
                group_item.addChild(topic_item)
    
    def _search_topics(self, query: str) -> None:
        """Search and filter topics"""
        if not query.strip():
            self._populate_topics()
            return
        
        self.topic_tree.clear()
        results = self.help_system.search_help(query)
        
        if results:
            search_item = QTreeWidgetItem([f"Search Results ({len(results)})"])
            search_item.setExpanded(True)
            self.topic_tree.addTopLevelItem(search_item)
            
            for topic in results:
                topic_item = QTreeWidgetItem([topic.title])
                topic_item.setData(0, Qt.ItemDataRole.UserRole, topic.id)
                search_item.addChild(topic_item)
        else:
            no_results_item = QTreeWidgetItem(["No results found"])
            self.topic_tree.addTopLevelItem(no_results_item)
    
    def _on_topic_selected(self, item: QTreeWidgetItem, column: int) -> None:
        """Handle topic selection"""
        topic_id = item.data(0, Qt.ItemDataRole.UserRole)
        if topic_id:
            self.show_topic(topic_id)
    
    def _on_related_topic_selected(self, item: QTreeWidgetItem, column: int) -> None:
        """Handle related topic selection"""
        topic_id = item.data(0, Qt.ItemDataRole.UserRole)
        if topic_id:
            self.show_topic(topic_id)
    
    def show_topic(self, topic_id: str) -> None:
        """Display a specific help topic"""
        topic = self.help_system.get_topic_by_id(topic_id)
        if not topic:
            return
        
        self.current_topic = topic
        
        # Update title and metadata
        self.topic_title.setText(topic.title)
        meta_text = f"Type: {topic.topic_type.value.title()} | "
        meta_text += f"Difficulty: {topic.difficulty.title()} | "
        meta_text += f"Estimated time: {topic.estimated_time} minutes"
        self.topic_meta.setText(meta_text)
        
        # Update content
        self.content_browser.setHtml(topic.content)
        
        # Update related topics
        self.related_list.clear()
        if topic.related_topics:
            for related_id in topic.related_topics:
                related_topic = self.help_system.get_topic_by_id(related_id)
                if related_topic:
                    related_item = QTreeWidgetItem([related_topic.title])
                    related_item.setData(0, Qt.ItemDataRole.UserRole, related_id)
                    self.related_list.addTopLevelItem(related_item)
        
        self.help_system.help_requested.emit(topic_id)
    
    def _print_help(self) -> None:
        """Print current help topic"""
        if self.current_topic:
            # This would implement printing functionality
            print(f"Printing help topic: {self.current_topic.title}")


# Export help system components
__all__ = [
    'HelpTopicType',
    'HelpTopic', 
    'PropertyPanelHelpSystem',
    'PropertyPanelHelpDialog'
]