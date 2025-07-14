"""
Tests for complex element types.

Tests Table, Image, Formula, PageBreak, and CodeBlock elements
with their specialized metadata and functionality.
"""

import pytest
from dataclasses import asdict

from src.torematrix.core.models.complex_types import (
    TableElement, ImageElement, FormulaElement, PageBreakElement, CodeBlockElement,
    TableMetadata, ImageMetadata, FormulaMetadata, CodeMetadata,
    FormulaType, CodeLanguage,
    create_table, create_image, create_formula, create_page_break, create_code_block
)
from src.torematrix.core.models.element import ElementType
from src.torematrix.core.models.metadata import ElementMetadata


class TestTableElement:
    """Test TableElement functionality"""
    
    def test_table_creation(self):
        """Test basic table creation"""
        cells = [
            ["Name", "Age", "City"],
            ["Alice", "30", "New York"],
            ["Bob", "25", "Chicago"]
        ]
        headers = ["Name", "Age", "City"]
        
        table = create_table(cells=cells, headers=headers)
        
        assert table.element_type == ElementType.TABLE
        assert table.cells == cells
        assert table.headers == headers
        assert table.table_metadata.num_rows == 2  # Data rows only
        assert table.table_metadata.num_cols == 3
        assert table.table_metadata.has_header == True
    
    def test_table_without_headers(self):
        """Test table creation without headers"""
        cells = [["A", "B"], ["C", "D"]]
        
        table = create_table(cells=cells)
        
        assert table.headers is None
        assert table.table_metadata.has_header == False
        assert table.table_metadata.num_rows == 2
        assert table.table_metadata.num_cols == 2
    
    def test_table_cell_access(self):
        """Test table cell access methods"""
        cells = [["A", "B"], ["C", "D"]]
        table = create_table(cells=cells)
        
        assert table.get_cell_text(0, 0) == "A"
        assert table.get_cell_text(1, 1) == "D"
        assert table.get_cell_text(2, 0) is None  # Out of bounds
        assert table.get_cell_text(0, 2) is None  # Out of bounds
    
    def test_table_dimensions(self):
        """Test table dimension methods"""
        cells = [["A", "B", "C"], ["D", "E"]]  # Ragged table
        table = create_table(cells=cells)
        
        assert table.get_row_count() == 2
        assert table.get_col_count() == 3  # Max columns
    
    def test_table_serialization(self):
        """Test table serialization and deserialization"""
        cells = [["Name", "Value"], ["Test", "123"]]
        table = create_table(cells=cells)
        
        # Serialize
        data = table.to_dict()
        assert data['element_type'] == ElementType.TABLE.value
        assert data['cells'] == cells
        assert 'table_metadata' in data
        
        # Deserialize
        restored_table = TableElement.from_dict(data)
        assert restored_table.cells == cells
        assert restored_table.table_metadata.num_rows == 1
        assert restored_table.table_metadata.num_cols == 2


class TestImageElement:
    """Test ImageElement functionality"""
    
    def test_image_creation_with_data(self):
        """Test image creation with base64 data"""
        image_data = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
        alt_text = "Test image"
        
        image = create_image(
            alt_text=alt_text,
            image_data=image_data
        )
        
        assert image.element_type == ElementType.IMAGE
        assert image.image_data == image_data
        assert image.alt_text == alt_text
        assert image.text == alt_text
    
    def test_image_creation_with_url(self):
        """Test image creation with URL"""
        image_url = "https://example.com/image.png"
        alt_text = "Remote image"
        caption = "This is a test image"
        
        image = create_image(
            alt_text=alt_text,
            image_url=image_url,
            caption=caption
        )
        
        assert image.image_url == image_url
        assert image.caption == caption
        assert image.has_data() == True
    
    def test_image_without_data(self):
        """Test image placeholder creation"""
        image = create_image(alt_text="Placeholder")
        
        assert image.has_data() == False
        assert image.get_display_text() == "Placeholder"
    
    def test_image_display_text(self):
        """Test image display text logic"""
        # With alt text
        image1 = create_image(alt_text="Alt text")
        assert image1.get_display_text() == "Alt text"
        
        # With caption but no alt text
        image2 = create_image(alt_text="", caption="Caption")
        assert image2.get_display_text() == "Caption"
        
        # With neither
        image3 = create_image(alt_text="")
        assert image3.get_display_text() == "[Image]"
    
    def test_image_metadata(self):
        """Test image metadata handling"""
        image_metadata = ImageMetadata(
            width=800,
            height=600,
            format="PNG",
            dpi=300
        )
        
        image = ImageElement(
            alt_text="Test",
            image_metadata=image_metadata
        )
        
        assert image.image_metadata.width == 800
        assert image.image_metadata.height == 600
        assert image.image_metadata.format == "PNG"
    
    def test_image_serialization(self):
        """Test image serialization and deserialization"""
        image = create_image(
            alt_text="Test image",
            image_data="base64data",
            caption="Test caption"
        )
        
        # Serialize
        data = image.to_dict()
        assert data['alt_text'] == "Test image"
        assert data['image_data'] == "base64data"
        assert data['caption'] == "Test caption"
        
        # Deserialize
        restored_image = ImageElement.from_dict(data)
        assert restored_image.alt_text == "Test image"
        assert restored_image.image_data == "base64data"


class TestFormulaElement:
    """Test FormulaElement functionality"""
    
    def test_formula_creation_inline(self):
        """Test inline formula creation"""
        latex = "x^2 + y^2 = z^2"
        
        formula = create_formula(
            latex=latex,
            formula_type=FormulaType.INLINE
        )
        
        assert formula.element_type == ElementType.FORMULA
        assert formula.latex == latex
        assert formula.formula_metadata.formula_type == FormulaType.INLINE
        assert formula.text == latex
    
    def test_formula_creation_display(self):
        """Test display formula creation"""
        latex = r"\int_{-\infty}^{\infty} e^{-x^2} dx = \sqrt{\pi}"
        mathml = "<math><mrow><mi>x</mi><mo>=</mo><mi>y</mi></mrow></math>"
        
        formula = create_formula(
            latex=latex,
            formula_type=FormulaType.DISPLAY,
            mathml=mathml
        )
        
        assert formula.formula_metadata.formula_type == FormulaType.DISPLAY
        assert formula.mathml == mathml
    
    def test_formula_display(self):
        """Test formula display logic"""
        # With LaTeX
        formula1 = create_formula(latex="x + y")
        assert formula1.get_display_formula() == "x + y"
        
        # With MathML but no LaTeX
        formula2 = FormulaElement(
            latex="",
            mathml="<math><mi>x</mi></math>"
        )
        assert formula2.get_display_formula() == "<math><mi>x</mi></math>"
        
        # With neither
        formula3 = FormulaElement(text="fallback text")
        assert formula3.get_display_formula() == "fallback text"
    
    def test_formula_metadata(self):
        """Test formula metadata handling"""
        formula_metadata = FormulaMetadata(
            formula_type=FormulaType.EQUATION,
            complexity_level="advanced",
            variables=["x", "y", "z"],
            operators=["+", "^", "="]
        )
        
        formula = FormulaElement(
            latex="x^2 + y^2 = z^2",
            formula_metadata=formula_metadata
        )
        
        assert formula.formula_metadata.complexity_level == "advanced"
        assert formula.formula_metadata.variables == ["x", "y", "z"]
    
    def test_formula_serialization(self):
        """Test formula serialization and deserialization"""
        formula = create_formula(
            latex="E = mc^2",
            formula_type=FormulaType.EQUATION
        )
        
        # Serialize
        data = formula.to_dict()
        assert data['latex'] == "E = mc^2"
        assert data['formula_metadata']['formula_type'] == FormulaType.EQUATION.value
        
        # Deserialize
        restored_formula = FormulaElement.from_dict(data)
        assert restored_formula.latex == "E = mc^2"
        assert restored_formula.formula_metadata.formula_type == FormulaType.EQUATION


class TestPageBreakElement:
    """Test PageBreakElement functionality"""
    
    def test_page_break_creation(self):
        """Test page break creation"""
        page_break = create_page_break()
        
        assert page_break.element_type == ElementType.PAGE_BREAK
        assert page_break.text == "[Page Break]"
    
    def test_page_break_with_metadata(self):
        """Test page break with metadata"""
        metadata = ElementMetadata(page_number=5)
        page_break = create_page_break(metadata=metadata)
        
        assert page_break.metadata.page_number == 5
    
    def test_page_break_serialization(self):
        """Test page break serialization"""
        page_break = create_page_break()
        
        # Serialize
        data = page_break.to_dict()
        assert data['element_type'] == ElementType.PAGE_BREAK.value
        assert data['text'] == "[Page Break]"
        
        # Deserialize
        restored_page_break = PageBreakElement.from_dict(data)
        assert restored_page_break.element_type == ElementType.PAGE_BREAK


class TestCodeBlockElement:
    """Test CodeBlockElement functionality"""
    
    def test_code_block_creation(self):
        """Test code block creation"""
        code = "def hello():\n    print('Hello, World!')"
        
        code_block = create_code_block(
            code=code,
            language=CodeLanguage.PYTHON
        )
        
        assert code_block.element_type == ElementType.CODE_BLOCK
        assert code_block.text == code
        assert code_block.code_metadata.language == CodeLanguage.PYTHON
        assert code_block.code_metadata.line_count == 2
    
    def test_code_block_line_counting(self):
        """Test line counting in code blocks"""
        # Single line
        code1 = "print('hello')"
        block1 = create_code_block(code=code1)
        assert block1.get_line_count() == 1
        
        # Multiple lines
        code2 = "line1\nline2\nline3"
        block2 = create_code_block(code=code2)
        assert block2.get_line_count() == 3
        
        # Empty code
        block3 = create_code_block(code="")
        assert block3.get_line_count() == 0
    
    def test_code_block_language(self):
        """Test code block language handling"""
        code_block = create_code_block(
            code="console.log('test');",
            language=CodeLanguage.JAVASCRIPT
        )
        
        assert code_block.get_language_name() == "javascript"
    
    def test_code_block_metadata(self):
        """Test code block metadata"""
        code_metadata = CodeMetadata(
            language=CodeLanguage.PYTHON,
            line_count=5,
            syntax_valid=True,
            indentation_type="spaces",
            complexity_score=3.5
        )
        
        code_block = CodeBlockElement(
            text="test code",
            code_metadata=code_metadata
        )
        
        assert code_block.code_metadata.complexity_score == 3.5
        assert code_block.code_metadata.indentation_type == "spaces"
    
    def test_code_block_serialization(self):
        """Test code block serialization and deserialization"""
        code = "print('test')"
        code_block = create_code_block(
            code=code,
            language=CodeLanguage.PYTHON
        )
        
        # Serialize
        data = code_block.to_dict()
        assert data['text'] == code
        assert data['code_metadata']['language'] == CodeLanguage.PYTHON.value
        
        # Deserialize
        restored_code_block = CodeBlockElement.from_dict(data)
        assert restored_code_block.text == code
        assert restored_code_block.code_metadata.language == CodeLanguage.PYTHON


class TestComplexTypeIntegration:
    """Test integration between complex types"""
    
    def test_all_types_creation(self):
        """Test creating all complex types"""
        # Table
        table = create_table(cells=[["A", "B"]])
        
        # Image
        image = create_image(alt_text="Test")
        
        # Formula
        formula = create_formula(latex="x = y")
        
        # Page break
        page_break = create_page_break()
        
        # Code block
        code_block = create_code_block(code="test", language=CodeLanguage.PYTHON)
        
        elements = [table, image, formula, page_break, code_block]
        
        # Verify all are Element instances
        for element in elements:
            assert hasattr(element, 'element_id')
            assert hasattr(element, 'element_type')
            assert hasattr(element, 'text')
    
    def test_complex_type_hierarchy(self):
        """Test complex types with parent-child relationships"""
        # Create parent table
        table = create_table(cells=[["Header1", "Header2"]])
        
        # Create child image
        image = create_image(
            alt_text="Table chart",
            parent_id=table.element_id
        )
        
        assert image.parent_id == table.element_id
    
    def test_complex_type_serialization_roundtrip(self):
        """Test serialization roundtrip for all complex types"""
        elements = [
            create_table(cells=[["A", "B"]], headers=["Col1", "Col2"]),
            create_image(alt_text="Test", image_data="base64"),
            create_formula(latex="x^2", formula_type=FormulaType.DISPLAY),
            create_page_break(),
            create_code_block(code="print()", language=CodeLanguage.PYTHON)
        ]
        
        for element in elements:
            # Serialize
            data = element.to_dict()
            
            # Deserialize based on type
            if element.element_type == ElementType.TABLE:
                restored = TableElement.from_dict(data)
            elif element.element_type == ElementType.IMAGE:
                restored = ImageElement.from_dict(data)
            elif element.element_type == ElementType.FORMULA:
                restored = FormulaElement.from_dict(data)
            elif element.element_type == ElementType.PAGE_BREAK:
                restored = PageBreakElement.from_dict(data)
            elif element.element_type == ElementType.CODE_BLOCK:
                restored = CodeBlockElement.from_dict(data)
            
            # Verify equality
            assert restored.element_id == element.element_id
            assert restored.element_type == element.element_type
            assert restored.text == element.text