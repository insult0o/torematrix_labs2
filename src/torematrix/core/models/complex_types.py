"""
Complex element types for advanced document structures.

This module provides implementations for complex document elements including
tables, images, formulas, page breaks, and code blocks that require specialized
metadata and handling.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING
from enum import Enum

from .element import Element, ElementType

if TYPE_CHECKING:
    from .metadata import ElementMetadata


class FormulaType(Enum):
    """Types of mathematical formulas"""
    INLINE = "inline"
    DISPLAY = "display"
    EQUATION = "equation"


class CodeLanguage(Enum):
    """Supported programming languages for code blocks"""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    JAVA = "java"
    CPP = "cpp"
    C = "c"
    CSHARP = "csharp"
    SQL = "sql"
    HTML = "html"
    CSS = "css"
    XML = "xml"
    JSON = "json"
    YAML = "yaml"
    MARKDOWN = "markdown"
    SHELL = "shell"
    BASH = "bash"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class TableMetadata:
    """Specialized metadata for table elements"""
    num_rows: int = 0
    num_cols: int = 0
    has_header: bool = False
    table_type: str = "standard"
    cell_spans: Optional[Dict[str, Any]] = None
    table_alignment: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'num_rows': self.num_rows,
            'num_cols': self.num_cols,
            'has_header': self.has_header,
            'table_type': self.table_type,
            'cell_spans': self.cell_spans,
            'table_alignment': self.table_alignment
        }


@dataclass(frozen=True)
class ImageMetadata:
    """Specialized metadata for image elements"""
    width: Optional[int] = None
    height: Optional[int] = None
    format: Optional[str] = None
    dpi: Optional[int] = None
    color_mode: Optional[str] = None
    file_size: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'width': self.width,
            'height': self.height,
            'format': self.format,
            'dpi': self.dpi,
            'color_mode': self.color_mode,
            'file_size': self.file_size
        }


@dataclass(frozen=True)
class FormulaMetadata:
    """Specialized metadata for formula elements"""
    formula_type: FormulaType = FormulaType.INLINE
    complexity_level: str = "basic"
    variables: List[str] = field(default_factory=list)
    operators: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'formula_type': self.formula_type.value,
            'complexity_level': self.complexity_level,
            'variables': self.variables,
            'operators': self.operators
        }


@dataclass(frozen=True)
class CodeMetadata:
    """Specialized metadata for code block elements"""
    language: CodeLanguage = CodeLanguage.UNKNOWN
    line_count: int = 0
    syntax_valid: bool = True
    indentation_type: str = "spaces"
    complexity_score: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'language': self.language.value,
            'line_count': self.line_count,
            'syntax_valid': self.syntax_valid,
            'indentation_type': self.indentation_type,
            'complexity_score': self.complexity_score
        }


@dataclass(frozen=True)
class TableElement(Element):
    """
    Table element with structured data representation.
    
    Represents tables with cells, headers, and structure metadata.
    Supports complex table layouts with spanning cells.
    """
    cells: List[List[str]] = field(default_factory=list)
    headers: Optional[List[str]] = None
    table_metadata: TableMetadata = field(default_factory=TableMetadata)
    
    def __post_init__(self):
        """Validate table structure after initialization"""
        super().__post_init__()
        
        # Validate table structure
        if self.cells:
            row_lengths = [len(row) for row in self.cells]
            if len(set(row_lengths)) > 1:
                # Allow for ragged tables but log warning
                pass
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize table element to dictionary"""
        data = super().to_dict()
        data.update({
            'cells': self.cells,
            'headers': self.headers,
            'table_metadata': self.table_metadata.to_dict()
        })
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TableElement':
        """Deserialize table element from dictionary"""
        from torematrix.core.models import ElementMetadata
        
        # Handle base metadata
        metadata = None
        if "metadata" in data and data["metadata"]:
            metadata = ElementMetadata.from_dict(data["metadata"])
        
        # Handle table metadata
        table_metadata = TableMetadata()
        if "table_metadata" in data and data["table_metadata"]:
            tm_data = data["table_metadata"]
            table_metadata = TableMetadata(
                num_rows=tm_data.get("num_rows", 0),
                num_cols=tm_data.get("num_cols", 0),
                has_header=tm_data.get("has_header", False),
                table_type=tm_data.get("table_type", "standard"),
                cell_spans=tm_data.get("cell_spans"),
                table_alignment=tm_data.get("table_alignment")
            )
        
        return cls(
            element_id=data.get("element_id"),
            element_type=ElementType.TABLE,
            text=data.get("text", ""),
            metadata=metadata,
            parent_id=data.get("parent_id"),
            cells=data.get("cells", []),
            headers=data.get("headers"),
            table_metadata=table_metadata
        )
    
    def get_cell_text(self, row: int, col: int) -> Optional[str]:
        """Get text content of specific cell"""
        if 0 <= row < len(self.cells) and 0 <= col < len(self.cells[row]):
            return self.cells[row][col]
        return None
    
    def get_row_count(self) -> int:
        """Get number of rows in table"""
        return len(self.cells)
    
    def get_col_count(self) -> int:
        """Get maximum number of columns in table"""
        if not self.cells:
            return 0
        return max(len(row) for row in self.cells)


@dataclass(frozen=True)
class ImageElement(Element):
    """
    Image element with embedded or referenced image data.
    
    Supports both base64 encoded image data and external URLs.
    Includes rich metadata for image properties.
    """
    image_data: Optional[str] = None  # base64 encoded data
    image_url: Optional[str] = None   # external URL
    alt_text: Optional[str] = None    # accessibility text
    caption: Optional[str] = None     # image caption
    image_metadata: ImageMetadata = field(default_factory=ImageMetadata)
    
    def __post_init__(self):
        """Validate image element after initialization"""
        super().__post_init__()
        
        # Ensure at least one image source is provided
        if not self.image_data and not self.image_url:
            # Allow empty for placeholder images
            pass
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize image element to dictionary"""
        data = super().to_dict()
        data.update({
            'image_data': self.image_data,
            'image_url': self.image_url,
            'alt_text': self.alt_text,
            'caption': self.caption,
            'image_metadata': self.image_metadata.to_dict()
        })
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ImageElement':
        """Deserialize image element from dictionary"""
        from torematrix.core.models import ElementMetadata
        
        # Handle base metadata
        metadata = None
        if "metadata" in data and data["metadata"]:
            metadata = ElementMetadata.from_dict(data["metadata"])
        
        # Handle image metadata
        image_metadata = ImageMetadata()
        if "image_metadata" in data and data["image_metadata"]:
            im_data = data["image_metadata"]
            image_metadata = ImageMetadata(
                width=im_data.get("width"),
                height=im_data.get("height"),
                format=im_data.get("format"),
                dpi=im_data.get("dpi"),
                color_mode=im_data.get("color_mode"),
                file_size=im_data.get("file_size")
            )
        
        return cls(
            element_id=data.get("element_id"),
            element_type=ElementType.IMAGE,
            text=data.get("text", ""),
            metadata=metadata,
            parent_id=data.get("parent_id"),
            image_data=data.get("image_data"),
            image_url=data.get("image_url"),
            alt_text=data.get("alt_text"),
            caption=data.get("caption"),
            image_metadata=image_metadata
        )
    
    def has_data(self) -> bool:
        """Check if image has actual data"""
        return bool(self.image_data or self.image_url)
    
    def get_display_text(self) -> str:
        """Get text representation for display"""
        if self.alt_text:
            return self.alt_text
        if self.caption:
            return self.caption
        return self.text or "[Image]"


@dataclass(frozen=True)
class FormulaElement(Element):
    """
    Mathematical formula element with LaTeX and MathML support.
    
    Represents mathematical expressions, equations, and formulas
    with multiple format representations.
    """
    latex: str = ""
    mathml: Optional[str] = None
    formula_metadata: FormulaMetadata = field(default_factory=FormulaMetadata)
    
    def __post_init__(self):
        """Validate formula element after initialization"""
        super().__post_init__()
        
        # Ensure LaTeX content is provided
        if not self.latex and not self.text:
            # Allow empty for placeholder formulas
            pass
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize formula element to dictionary"""
        data = super().to_dict()
        data.update({
            'latex': self.latex,
            'mathml': self.mathml,
            'formula_metadata': self.formula_metadata.to_dict()
        })
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FormulaElement':
        """Deserialize formula element from dictionary"""
        from torematrix.core.models import ElementMetadata
        
        # Handle base metadata
        metadata = None
        if "metadata" in data and data["metadata"]:
            metadata = ElementMetadata.from_dict(data["metadata"])
        
        # Handle formula metadata
        formula_metadata = FormulaMetadata()
        if "formula_metadata" in data and data["formula_metadata"]:
            fm_data = data["formula_metadata"]
            formula_type = FormulaType.INLINE
            if fm_data.get("formula_type"):
                formula_type = FormulaType(fm_data["formula_type"])
            
            formula_metadata = FormulaMetadata(
                formula_type=formula_type,
                complexity_level=fm_data.get("complexity_level", "basic"),
                variables=fm_data.get("variables", []),
                operators=fm_data.get("operators", [])
            )
        
        return cls(
            element_id=data.get("element_id"),
            element_type=ElementType.FORMULA,
            text=data.get("text", ""),
            metadata=metadata,
            parent_id=data.get("parent_id"),
            latex=data.get("latex", ""),
            mathml=data.get("mathml"),
            formula_metadata=formula_metadata
        )
    
    def get_display_formula(self) -> str:
        """Get best available formula representation"""
        if self.latex:
            return self.latex
        if self.mathml:
            return self.mathml
        return self.text


@dataclass(frozen=True)
class PageBreakElement(Element):
    """
    Page break element for document pagination.
    
    Represents explicit page breaks in documents, useful for
    maintaining document structure and pagination.
    """
    
    def __post_init__(self):
        """Validate page break element after initialization"""
        super().__post_init__()
        
        # Ensure element type is correct
        if self.element_type != ElementType.PAGE_BREAK:
            object.__setattr__(self, 'element_type', ElementType.PAGE_BREAK)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize page break element to dictionary"""
        data = super().to_dict()
        # Page breaks typically have minimal content
        if not data.get("text"):
            data["text"] = "[Page Break]"
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PageBreakElement':
        """Deserialize page break element from dictionary"""
        from torematrix.core.models import ElementMetadata
        
        # Handle base metadata
        metadata = None
        if "metadata" in data and data["metadata"]:
            metadata = ElementMetadata.from_dict(data["metadata"])
        
        return cls(
            element_id=data.get("element_id"),
            element_type=ElementType.PAGE_BREAK,
            text=data.get("text", "[Page Break]"),
            metadata=metadata,
            parent_id=data.get("parent_id")
        )


@dataclass(frozen=True)
class CodeBlockElement(Element):
    """
    Code block element for programming code and scripts.
    
    Represents code snippets with language detection and
    syntax highlighting support.
    """
    code_metadata: CodeMetadata = field(default_factory=CodeMetadata)
    
    def __post_init__(self):
        """Validate code block element after initialization"""
        super().__post_init__()
        
        # Count lines in code
        if self.text:
            line_count = len(self.text.split('\n'))
            object.__setattr__(
                self.code_metadata,
                'line_count',
                line_count
            )
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize code block element to dictionary"""
        data = super().to_dict()
        data.update({
            'code_metadata': self.code_metadata.to_dict()
        })
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CodeBlockElement':
        """Deserialize code block element from dictionary"""
        from torematrix.core.models import ElementMetadata
        
        # Handle base metadata
        metadata = None
        if "metadata" in data and data["metadata"]:
            metadata = ElementMetadata.from_dict(data["metadata"])
        
        # Handle code metadata
        code_metadata = CodeMetadata()
        if "code_metadata" in data and data["code_metadata"]:
            cm_data = data["code_metadata"]
            language = CodeLanguage.UNKNOWN
            if cm_data.get("language"):
                try:
                    language = CodeLanguage(cm_data["language"])
                except ValueError:
                    language = CodeLanguage.UNKNOWN
            
            code_metadata = CodeMetadata(
                language=language,
                line_count=cm_data.get("line_count", 0),
                syntax_valid=cm_data.get("syntax_valid", True),
                indentation_type=cm_data.get("indentation_type", "spaces"),
                complexity_score=cm_data.get("complexity_score")
            )
        
        return cls(
            element_id=data.get("element_id"),
            element_type=ElementType.CODE_BLOCK,
            text=data.get("text", ""),
            metadata=metadata,
            parent_id=data.get("parent_id"),
            code_metadata=code_metadata
        )
    
    def get_language_name(self) -> str:
        """Get human-readable language name"""
        return self.code_metadata.language.value
    
    def get_line_count(self) -> int:
        """Get number of lines in code"""
        return self.code_metadata.line_count


# Factory functions for complex types
def create_table(
    cells: List[List[str]],
    headers: Optional[List[str]] = None,
    metadata: Optional['ElementMetadata'] = None,
    **kwargs
) -> TableElement:
    """Create a Table element with validation"""
    # Generate table metadata
    table_metadata = TableMetadata(
        num_rows=len(cells),
        num_cols=max(len(row) for row in cells) if cells else 0,
        has_header=headers is not None,
        table_type="standard"
    )
    
    # Generate text representation
    text_rows = []
    if headers:
        text_rows.append(" | ".join(headers))
        text_rows.append("-" * len(" | ".join(headers)))
    
    for row in cells:
        text_rows.append(" | ".join(str(cell) for cell in row))
    
    text = "\n".join(text_rows)
    
    return TableElement(
        text=text,
        metadata=metadata,
        cells=cells,
        headers=headers,
        table_metadata=table_metadata,
        **kwargs
    )


def create_image(
    alt_text: str,
    image_data: Optional[str] = None,
    image_url: Optional[str] = None,
    caption: Optional[str] = None,
    metadata: Optional['ElementMetadata'] = None,
    **kwargs
) -> ImageElement:
    """Create an Image element"""
    return ImageElement(
        text=alt_text,
        metadata=metadata,
        image_data=image_data,
        image_url=image_url,
        alt_text=alt_text,
        caption=caption,
        **kwargs
    )


def create_formula(
    latex: str,
    formula_type: FormulaType = FormulaType.INLINE,
    mathml: Optional[str] = None,
    metadata: Optional['ElementMetadata'] = None,
    **kwargs
) -> FormulaElement:
    """Create a Formula element"""
    formula_metadata = FormulaMetadata(formula_type=formula_type)
    
    return FormulaElement(
        text=latex,
        metadata=metadata,
        latex=latex,
        mathml=mathml,
        formula_metadata=formula_metadata,
        **kwargs
    )


def create_page_break(
    metadata: Optional['ElementMetadata'] = None,
    **kwargs
) -> PageBreakElement:
    """Create a PageBreak element"""
    return PageBreakElement(
        text="[Page Break]",
        metadata=metadata,
        **kwargs
    )


def create_code_block(
    code: str,
    language: CodeLanguage = CodeLanguage.UNKNOWN,
    metadata: Optional['ElementMetadata'] = None,
    **kwargs
) -> CodeBlockElement:
    """Create a CodeBlock element"""
    code_metadata = CodeMetadata(
        language=language,
        line_count=len(code.split('\n')) if code else 0
    )
    
    return CodeBlockElement(
        text=code,
        metadata=metadata,
        code_metadata=code_metadata,
        **kwargs
    )