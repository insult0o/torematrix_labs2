"""
Custom Delegates for Element Tree View

Provides rich rendering with custom painting and editing capabilities.
"""

from typing import Optional, Dict, Any, Tuple
from PyQt6.QtCore import QRect, QSize, Qt, QModelIndex, QStyleOptionViewItem, pyqtSignal
from PyQt6.QtGui import (QPainter, QFont, QFontMetrics, QColor, QPen, QBrush, 
                        QPalette, QPixmap, QIcon, QGradient, QLinearGradient)
from PyQt6.QtWidgets import (QStyledItemDelegate, QWidget, QStyleOptionButton, 
                            QApplication, QStyle, QLineEdit, QComboBox, QSpinBox)

from ..interfaces.tree_interfaces import ElementProtocol


class ElementColors:
    """Color scheme for different element types."""
    
    COLORS = {
        'text': QColor(50, 50, 50),
        'title': QColor(20, 80, 140),
        'header': QColor(40, 100, 160),
        'list': QColor(70, 120, 70),
        'list_item': QColor(90, 140, 90),
        'table': QColor(140, 70, 70),
        'table_cell': QColor(160, 90, 90),
        'image': QColor(120, 80, 140),
        'formula': QColor(140, 120, 70),
        'code': QColor(70, 70, 140),
        'footer': QColor(100, 100, 100),
        'page_break': QColor(200, 200, 200),
        'unknown': QColor(128, 128, 128)
    }
    
    BACKGROUND_COLORS = {
        'text': QColor(255, 255, 255),
        'title': QColor(240, 248, 255),
        'header': QColor(245, 250, 255),
        'list': QColor(248, 255, 248),
        'list_item': QColor(250, 255, 250),
        'table': QColor(255, 248, 248),
        'table_cell': QColor(255, 250, 250),
        'image': QColor(252, 248, 255),
        'formula': QColor(255, 252, 248),
        'code': QColor(248, 248, 255),
        'footer': QColor(250, 250, 250),
        'page_break': QColor(245, 245, 245),
        'unknown': QColor(248, 248, 248)
    }
    
    @classmethod
    def get_color(cls, element_type: str) -> QColor:
        """Get foreground color for element type."""
        return cls.COLORS.get(element_type, cls.COLORS['unknown'])
    
    @classmethod
    def get_background_color(cls, element_type: str) -> QColor:
        """Get background color for element type."""
        return cls.BACKGROUND_COLORS.get(element_type, cls.BACKGROUND_COLORS['unknown'])


class ConfidenceIndicator:
    """Renders confidence indicators."""
    
    @staticmethod
    def paint_confidence_bar(painter: QPainter, rect: QRect, confidence: float) -> None:
        """Paint confidence bar."""
        bar_rect = QRect(rect.right() - 60, rect.center().y() - 3, 50, 6)
        
        # Background
        painter.fillRect(bar_rect, QColor(230, 230, 230))
        
        # Confidence bar
        fill_width = int(bar_rect.width() * confidence)
        fill_rect = QRect(bar_rect.left(), bar_rect.top(), fill_width, bar_rect.height())
        
        # Color based on confidence level
        if confidence >= 0.8:
            color = QColor(50, 150, 50)
        elif confidence >= 0.6:
            color = QColor(200, 150, 50)
        elif confidence >= 0.4:
            color = QColor(200, 100, 50)
        else:
            color = QColor(150, 50, 50)
        
        painter.fillRect(fill_rect, color)
        
        # Border
        painter.setPen(QPen(QColor(180, 180, 180), 1))
        painter.drawRect(bar_rect)
    
    @staticmethod
    def paint_confidence_badge(painter: QPainter, rect: QRect, confidence: float) -> None:
        """Paint confidence badge."""
        badge_size = 16
        badge_rect = QRect(rect.right() - badge_size - 4, 
                          rect.center().y() - badge_size // 2,
                          badge_size, badge_size)
        
        # Badge color
        if confidence >= 0.8:
            color = QColor(50, 150, 50)
        elif confidence >= 0.6:
            color = QColor(200, 150, 50)
        elif confidence >= 0.4:
            color = QColor(200, 100, 50)
        else:
            color = QColor(150, 50, 50)
        
        # Draw circle
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(color.darker(120), 1))
        painter.drawEllipse(badge_rect)
        
        # Draw percentage text
        painter.setPen(QPen(Qt.GlobalColor.white))
        font = painter.font()
        font.setPointSize(8)
        font.setBold(True)
        painter.setFont(font)
        
        text = f"{int(confidence * 100)}"
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, text)


class ElementTypeIcon:
    """Manages icons for different element types."""
    
    def __init__(self):
        self.icons: Dict[str, QIcon] = {}
        self._create_default_icons()
    
    def _create_default_icons(self) -> None:
        """Create default icons for element types."""
        # For now, we'll use simple colored rectangles
        # In a real implementation, you'd load actual icon files
        icon_size = QSize(16, 16)
        
        for element_type, color in ElementColors.COLORS.items():
            pixmap = QPixmap(icon_size)
            pixmap.fill(Qt.GlobalColor.transparent)
            
            painter = QPainter(pixmap)
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(color.darker(120), 1))
            painter.drawRect(2, 2, 12, 12)
            painter.end()
            
            self.icons[element_type] = QIcon(pixmap)
    
    def get_icon(self, element_type: str) -> QIcon:
        """Get icon for element type."""
        return self.icons.get(element_type, self.icons.get('unknown', QIcon()))


class RichElementDelegate(QStyledItemDelegate):
    """Rich delegate for element rendering with custom painting."""
    
    # Signals
    editingStarted = pyqtSignal(QModelIndex)
    editingFinished = pyqtSignal(QModelIndex, str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.icon_manager = ElementTypeIcon()
        self.show_confidence = True
        self.show_icons = True
        self.show_type_badges = True
        self.highlight_search = True
        self.search_query = ""
        
        # Rendering options
        self.margins = 4
        self.icon_size = QSize(16, 16)
        self.spacing = 6
    
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        """Custom paint method for rich rendering."""
        painter.save()
        
        # Get element data
        element_id = index.data(Qt.ItemDataRole.UserRole)
        model = index.model()
        element = None
        
        if model and hasattr(model, 'sourceModel'):
            # Proxy model
            source_model = model.sourceModel()
            if source_model and hasattr(source_model, 'get_element_by_id'):
                element = source_model.get_element_by_id(element_id)
        elif model and hasattr(model, 'get_element_by_id'):
            # Direct model
            element = model.get_element_by_id(element_id)
        
        if not element:
            # Fallback to default rendering
            super().paint(painter, option, index)
            painter.restore()
            return
        
        # Setup painting
        rect = option.rect
        is_selected = option.state & QStyle.StateFlag.State_Selected
        is_focused = option.state & QStyle.StateFlag.State_HasFocus
        
        # Draw background
        self._paint_background(painter, rect, element, is_selected, is_focused)
        
        # Calculate layout
        layout = self._calculate_layout(rect, element)
        
        # Draw components
        if self.show_icons:
            self._paint_icon(painter, layout['icon_rect'], element)
        
        self._paint_text(painter, layout['text_rect'], element, is_selected)
        
        if self.show_type_badges:
            self._paint_type_badge(painter, layout['type_rect'], element)
        
        if self.show_confidence and element.confidence is not None:
            self._paint_confidence(painter, layout['confidence_rect'], element.confidence)
        
        # Draw selection/focus indicators
        if is_selected or is_focused:
            self._paint_selection_indicator(painter, rect, is_selected, is_focused)
        
        painter.restore()
    
    def _paint_background(self, painter: QPainter, rect: QRect, element: ElementProtocol, 
                         is_selected: bool, is_focused: bool) -> None:
        """Paint background with element-specific color."""
        if is_selected:
            # Selected background
            palette = QApplication.palette()
            color = palette.color(QPalette.ColorRole.Highlight)
            painter.fillRect(rect, color)
        else:
            # Element-specific background
            bg_color = ElementColors.get_background_color(element.type)
            if bg_color != QColor(255, 255, 255):  # Only paint if not white
                painter.fillRect(rect, bg_color)
    
    def _calculate_layout(self, rect: QRect, element: ElementProtocol) -> Dict[str, QRect]:
        """Calculate layout rectangles for different components."""
        layout = {}
        
        current_x = rect.left() + self.margins
        y = rect.top()
        height = rect.height()
        
        # Icon area
        if self.show_icons:
            layout['icon_rect'] = QRect(current_x, y + (height - self.icon_size.height()) // 2,
                                       self.icon_size.width(), self.icon_size.height())
            current_x += self.icon_size.width() + self.spacing
        else:
            layout['icon_rect'] = QRect()
        
        # Calculate right-side components first (work backwards)
        right_x = rect.right() - self.margins
        
        # Confidence indicator
        if self.show_confidence and element.confidence is not None:
            conf_width = 60
            layout['confidence_rect'] = QRect(right_x - conf_width, y, conf_width, height)
            right_x -= conf_width + self.spacing
        else:
            layout['confidence_rect'] = QRect()
        
        # Type badge
        if self.show_type_badges:
            type_width = 80
            layout['type_rect'] = QRect(right_x - type_width, y, type_width, height)
            right_x -= type_width + self.spacing
        else:
            layout['type_rect'] = QRect()
        
        # Text area (remaining space)
        layout['text_rect'] = QRect(current_x, y, right_x - current_x, height)
        
        return layout
    
    def _paint_icon(self, painter: QPainter, rect: QRect, element: ElementProtocol) -> None:
        """Paint element type icon."""
        if rect.isEmpty():
            return
        
        icon = self.icon_manager.get_icon(element.type)
        icon.paint(painter, rect)
    
    def _paint_text(self, painter: QPainter, rect: QRect, element: ElementProtocol, 
                   is_selected: bool) -> None:
        """Paint element text with highlighting."""
        if rect.isEmpty():
            return
        
        # Setup text color
        if is_selected:
            palette = QApplication.palette()
            color = palette.color(QPalette.ColorRole.HighlightedText)
        else:
            color = ElementColors.get_color(element.type)
        
        painter.setPen(QPen(color))
        
        # Setup font based on element type
        font = painter.font()
        if element.type in ['title', 'header']:
            font.setBold(True)
            if element.type == 'title':
                font.setPointSize(font.pointSize() + 2)
        elif element.type == 'code':
            font.setFamily('Courier New')
        
        painter.setFont(font)
        
        # Get text to display
        text = element.text or "No content"
        
        # Truncate if necessary
        metrics = QFontMetrics(font)
        elided_text = metrics.elidedText(text, Qt.TextElideMode.ElideRight, 
                                        rect.width())
        
        # Highlight search terms if applicable
        if self.highlight_search and self.search_query:
            self._paint_highlighted_text(painter, rect, elided_text, color)
        else:
            painter.drawText(rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, 
                           elided_text)
    
    def _paint_highlighted_text(self, painter: QPainter, rect: QRect, text: str, 
                               base_color: QColor) -> None:
        """Paint text with search highlighting."""
        if not self.search_query:
            painter.drawText(rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)
            return
        
        # Simple highlighting - in a full implementation, you'd handle regex, case sensitivity, etc.
        query_lower = self.search_query.lower()
        text_lower = text.lower()
        
        if query_lower not in text_lower:
            painter.drawText(rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)
            return
        
        # Find highlight positions
        start_pos = text_lower.find(query_lower)
        if start_pos == -1:
            painter.drawText(rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)
            return
        
        end_pos = start_pos + len(self.search_query)
        
        # Split text into parts
        before = text[:start_pos]
        highlight = text[start_pos:end_pos]
        after = text[end_pos:]
        
        # Calculate positions
        metrics = QFontMetrics(painter.font())
        
        x = rect.left()
        y = rect.center().y() + metrics.height() // 2 - metrics.descent()
        
        # Draw before text
        if before:
            painter.setPen(QPen(base_color))
            painter.drawText(x, y, before)
            x += metrics.horizontalAdvance(before)
        
        # Draw highlighted text
        if highlight:
            # Highlight background
            highlight_rect = QRect(x, rect.top(), metrics.horizontalAdvance(highlight), rect.height())
            painter.fillRect(highlight_rect, QColor(255, 255, 0, 128))  # Yellow highlight
            
            # Highlight text
            painter.setPen(QPen(Qt.GlobalColor.black))
            painter.drawText(x, y, highlight)
            x += metrics.horizontalAdvance(highlight)
        
        # Draw after text
        if after:
            painter.setPen(QPen(base_color))
            painter.drawText(x, y, after)
    
    def _paint_type_badge(self, painter: QPainter, rect: QRect, element: ElementProtocol) -> None:
        """Paint element type badge."""
        if rect.isEmpty():
            return
        
        # Background
        bg_color = ElementColors.get_color(element.type).lighter(180)
        painter.fillRect(rect, bg_color)
        
        # Border
        border_color = ElementColors.get_color(element.type)
        painter.setPen(QPen(border_color, 1))
        painter.drawRect(rect)
        
        # Text
        painter.setPen(QPen(border_color.darker(120)))
        font = painter.font()
        font.setPointSize(max(8, font.pointSize() - 2))
        painter.setFont(font)
        
        type_text = element.type.replace('_', ' ').title()
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, type_text)
    
    def _paint_confidence(self, painter: QPainter, rect: QRect, confidence: float) -> None:
        """Paint confidence indicator."""
        if rect.isEmpty():
            return
        
        ConfidenceIndicator.paint_confidence_bar(painter, rect, confidence)
    
    def _paint_selection_indicator(self, painter: QPainter, rect: QRect, 
                                  is_selected: bool, is_focused: bool) -> None:
        """Paint selection and focus indicators."""
        if is_focused:
            # Focus rectangle
            painter.setPen(QPen(QColor(0, 120, 215), 2, Qt.PenStyle.DashLine))
            painter.drawRect(rect.adjusted(1, 1, -1, -1))
    
    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        """Return size hint for item."""
        # Base size
        base_size = super().sizeHint(option, index)
        
        # Minimum height for rich rendering
        min_height = max(base_size.height(), self.icon_size.height() + 2 * self.margins)
        
        return QSize(base_size.width(), min_height)
    
    def createEditor(self, parent: QWidget, option: QStyleOptionViewItem, 
                    index: QModelIndex) -> QWidget:
        """Create custom editor for element editing."""
        column = index.column()
        
        if column == 0:  # Content column
            editor = QLineEdit(parent)
            editor.setFrame(False)
            return editor
        elif column == 1:  # Type column
            editor = QComboBox(parent)
            editor.addItems([
                "text", "title", "header", "list", "list_item",
                "table", "table_cell", "image", "formula", "code"
            ])
            editor.setFrame(False)
            return editor
        elif column == 2:  # Confidence column
            editor = QSpinBox(parent)
            editor.setRange(0, 100)
            editor.setSuffix("%")
            editor.setFrame(False)
            return editor
        
        return super().createEditor(parent, option, index)
    
    def setEditorData(self, editor: QWidget, index: QModelIndex) -> None:
        """Set data in editor from model."""
        column = index.column()
        
        if column == 0 and isinstance(editor, QLineEdit):
            text = index.data(Qt.ItemDataRole.DisplayRole) or ""
            editor.setText(text)
        elif column == 1 and isinstance(editor, QComboBox):
            type_text = index.data(Qt.ItemDataRole.DisplayRole) or ""
            index_pos = editor.findText(type_text.lower())
            if index_pos >= 0:
                editor.setCurrentIndex(index_pos)
        elif column == 2 and isinstance(editor, QSpinBox):
            conf_text = index.data(Qt.ItemDataRole.DisplayRole) or "0%"
            try:
                value = int(conf_text.replace('%', ''))
                editor.setValue(value)
            except ValueError:
                editor.setValue(0)
        else:
            super().setEditorData(editor, index)
    
    def setModelData(self, editor: QWidget, model, index: QModelIndex) -> None:
        """Set data in model from editor."""
        column = index.column()
        
        if column == 0 and isinstance(editor, QLineEdit):
            text = editor.text()
            model.setData(index, text, Qt.ItemDataRole.EditRole)
            self.editingFinished.emit(index, text)
        elif column == 1 and isinstance(editor, QComboBox):
            type_text = editor.currentText()
            model.setData(index, type_text, Qt.ItemDataRole.EditRole)
            self.editingFinished.emit(index, type_text)
        elif column == 2 and isinstance(editor, QSpinBox):
            value = editor.value()
            conf_text = f"{value}%"
            model.setData(index, conf_text, Qt.ItemDataRole.EditRole)
            self.editingFinished.emit(index, conf_text)
        else:
            super().setModelData(editor, model, index)
    
    def updateEditorGeometry(self, editor: QWidget, option: QStyleOptionViewItem, 
                           index: QModelIndex) -> None:
        """Update editor geometry."""
        editor.setGeometry(option.rect)
    
    # Configuration methods
    
    def set_show_confidence(self, show: bool) -> None:
        """Enable/disable confidence indicators."""
        self.show_confidence = show
    
    def set_show_icons(self, show: bool) -> None:
        """Enable/disable type icons."""
        self.show_icons = show
    
    def set_show_type_badges(self, show: bool) -> None:
        """Enable/disable type badges."""
        self.show_type_badges = show
    
    def set_search_highlighting(self, enabled: bool, query: str = "") -> None:
        """Enable/disable search highlighting."""
        self.highlight_search = enabled
        self.search_query = query
    
    def set_icon_size(self, size: QSize) -> None:
        """Set icon size."""
        self.icon_size = size


class MinimalElementDelegate(QStyledItemDelegate):
    """Minimal delegate for performance-critical scenarios."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.show_confidence = True
    
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        """Minimal paint implementation."""
        painter.save()
        
        # Use default painting for most elements
        super().paint(painter, option, index)
        
        # Add confidence indicator if needed
        if self.show_confidence:
            element_id = index.data(Qt.ItemDataRole.UserRole)
            model = index.model()
            
            if model and hasattr(model, 'get_element_by_id'):
                element = model.get_element_by_id(element_id)
                if element and element.confidence is not None:
                    ConfidenceIndicator.paint_confidence_badge(painter, option.rect, element.confidence)
        
        painter.restore()


class CompactElementDelegate(QStyledItemDelegate):
    """Compact delegate for displaying more items in less space."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.row_height = 20
    
    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        """Return compact size hint."""
        base_size = super().sizeHint(option, index)
        return QSize(base_size.width(), self.row_height)
    
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        """Compact paint implementation."""
        painter.save()
        
        # Simplified rendering
        rect = option.rect
        is_selected = option.state & QStyle.StateFlag.State_Selected
        
        # Background
        if is_selected:
            palette = QApplication.palette()
            painter.fillRect(rect, palette.color(QPalette.ColorRole.Highlight))
        
        # Text
        text = index.data(Qt.ItemDataRole.DisplayRole) or ""
        color = QApplication.palette().color(
            QPalette.ColorRole.HighlightedText if is_selected else QPalette.ColorRole.Text
        )
        painter.setPen(QPen(color))
        
        text_rect = rect.adjusted(4, 0, -4, 0)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)
        
        painter.restore()