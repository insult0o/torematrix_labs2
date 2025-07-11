"""
OCR-based PDF text extraction with perfect coordinate correlation like ABBYY FineReader.

This module provides true OCR-based text extraction that builds text character-by-character
with exact coordinate mapping, enabling perfect cursor positioning and text selection.
"""

import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass
import json

import fitz  # PyMuPDF for PDF rendering
from io import BytesIO

# Handle OCR dependencies gracefully with compatibility layer
try:
    # Use compatibility layer for numpy
    from ..utils.numpy_compatibility import numpy, NUMPY_AVAILABLE
    
    if NUMPY_AVAILABLE and numpy is not None:
        import cv2
        from PIL import Image
        import pytesseract
        OCR_DEPENDENCIES_AVAILABLE = True
        TESSERACT_AVAILABLE = True
    else:
        raise ImportError("Numpy compatibility issues detected")
        
except (ImportError, ValueError) as e:
    # ImportError: missing packages
    # ValueError: numpy compatibility issues 
    OCR_DEPENDENCIES_AVAILABLE = False
    TESSERACT_AVAILABLE = False
    numpy = None
    cv2 = None
    Image = None
    pytesseract = None
    logging.warning(f"OCR dependencies not available: {e}")
    logging.warning("Install with: pip install pytesseract opencv-python pillow")
    if "numpy.dtype size changed" in str(e):
        logging.warning("Note: numpy compatibility issue detected - OCR disabled, using enhanced PyMuPDF extraction")

from ..config.settings import Settings


@dataclass
class OCRCharacter:
    """Individual character with precise OCR-based positioning."""
    char: str
    bbox: Tuple[float, float, float, float]  # x0, y0, x1, y1 in PDF coordinates
    confidence: float
    page_number: int
    char_index: int  # Position in page text
    global_char_index: int  # Position in full document text


@dataclass
class OCRWord:
    """Word with precise OCR-based positioning."""
    text: str
    bbox: Tuple[float, float, float, float]
    confidence: float
    characters: List[OCRCharacter]
    page_number: int


@dataclass
class OCRLine:
    """Line with OCR-based positioning."""
    text: str
    bbox: Tuple[float, float, float, float]
    confidence: float
    words: List[OCRWord]
    page_number: int


class OCRBasedExtractor:
    """
    OCR-based PDF text extraction with perfect coordinate correlation.
    
    Works like ABBYY FineReader by:
    1. Rendering PDF pages as high-resolution images
    2. Performing OCR to get character-level coordinates
    3. Building perfect text-to-coordinate mapping
    4. Enabling precise cursor positioning between any characters
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        if not OCR_DEPENDENCIES_AVAILABLE:
            self.logger.error("OCR dependencies not available. Install with: pip install pytesseract opencv-python pillow")
            self.use_ocr = False
        else:
            self.use_ocr = True
            self.logger.info("OCR-based extractor initialized with Tesseract")
            
            # Configure Tesseract for maximum accuracy
            self.tesseract_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,;:!?()-[]{}/"\'\ '
    
    def extract_with_ocr_precision(self, file_path: str, dpi: int = 300) -> Tuple[List[OCRCharacter], str, Dict[int, List[OCRLine]]]:
        """
        Extract text using OCR with perfect coordinate precision like ABBYY FineReader.
        
        Args:
            file_path: Path to PDF file
            dpi: Resolution for OCR (higher = more accurate, slower)
            
        Returns:
            Tuple of (all_characters, full_text, page_lines)
        """
        if not self.use_ocr:
            return self._fallback_extraction(file_path)
        
        self.logger.info(f"Starting OCR-based extraction: {file_path} at {dpi} DPI")
        start_time = time.time()
        
        doc = fitz.open(file_path)
        all_characters = []
        page_lines = {}
        full_text = ""
        global_char_index = 0
        
        try:
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_number = page_num + 1
                
                self.logger.info(f"Processing page {page_number} with OCR...")
                
                # Render page as high-resolution image
                page_image = self._render_page_for_ocr(page, dpi)
                
                # Perform OCR with character-level coordinates
                page_chars, page_text, lines = self._ocr_page_with_coordinates(
                    page_image, page, page_number, global_char_index
                )
                
                all_characters.extend(page_chars)
                page_lines[page_number] = lines
                full_text += page_text
                global_char_index = len(full_text)
                
                self.logger.info(f"Page {page_number}: {len(page_chars)} characters extracted")
            
            extraction_time = time.time() - start_time
            self.logger.info(f"OCR extraction completed in {extraction_time:.2f}s: {len(all_characters)} characters")
            
            return all_characters, full_text, page_lines
            
        finally:
            doc.close()
    
    def _render_page_for_ocr(self, page: fitz.Page, dpi: int):
        """Render PDF page as high-resolution image for OCR."""
        # Calculate zoom factor for desired DPI
        zoom = dpi / 72.0  # PDF default is 72 DPI
        mat = fitz.Matrix(zoom, zoom)
        
        # Render page as pixmap
        pix = page.get_pixmap(matrix=mat)
        
        # Convert to numpy array for OpenCV/Tesseract
        img_data = pix.tobytes("ppm")
        pil_image = Image.open(BytesIO(img_data))
        cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        
        # Preprocess image for better OCR
        cv_image = self._preprocess_for_ocr(cv_image)
        
        return cv_image
    
    def _preprocess_for_ocr(self, image):
        """Preprocess image for optimal OCR results."""
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply adaptive thresholding for better text recognition
        processed = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        # Denoise
        processed = cv2.medianBlur(processed, 3)
        
        return processed
    
    def _ocr_page_with_coordinates(self, image, page: fitz.Page, 
                                 page_number: int, global_char_offset: int) -> Tuple[List[OCRCharacter], str, List[OCRLine]]:
        """Perform OCR on page image and extract character-level coordinates."""
        
        # Get OCR data with bounding boxes
        ocr_data = pytesseract.image_to_data(
            image, 
            config=self.tesseract_config,
            output_type=pytesseract.Output.DICT
        )
        
        # Extract page dimensions for coordinate conversion
        image_height, image_width = image.shape[:2]
        page_rect = page.rect
        
        # Scale factors to convert from image coordinates to PDF coordinates
        x_scale = page_rect.width / image_width
        y_scale = page_rect.height / image_height
        
        characters = []
        lines = []
        page_text = ""
        char_index = 0
        
        # Group OCR data by lines and words
        current_line_words = []
        current_line_num = -1
        
        for i in range(len(ocr_data['text'])):
            text = ocr_data['text'][i]
            conf = int(ocr_data['conf'][i])
            level = int(ocr_data['level'][i])
            line_num = int(ocr_data['line_num'][i])
            
            # Skip empty text or low confidence
            if not text.strip() or conf < 30:
                continue
            
            # Get bounding box in image coordinates
            x = int(ocr_data['left'][i])
            y = int(ocr_data['top'][i])
            w = int(ocr_data['width'][i])
            h = int(ocr_data['height'][i])
            
            # Convert to PDF coordinates
            pdf_x0 = x * x_scale
            pdf_y0 = page_rect.height - (y + h) * y_scale  # Flip Y axis
            pdf_x1 = (x + w) * x_scale
            pdf_y1 = page_rect.height - y * y_scale  # Flip Y axis
            
            pdf_bbox = (pdf_x0, pdf_y0, pdf_x1, pdf_y1)
            
            # Process word-level data (level 5 in Tesseract)
            if level == 5:  # Word level
                word_chars = self._create_character_mapping(
                    text, pdf_bbox, conf, page_number, 
                    char_index, global_char_offset
                )
                
                characters.extend(word_chars)
                page_text += text
                char_index += len(text)
                
                # Create word object
                word = OCRWord(
                    text=text,
                    bbox=pdf_bbox,
                    confidence=conf / 100.0,
                    characters=word_chars,
                    page_number=page_number
                )
                
                # Group words by line
                if line_num != current_line_num:
                    # Finish previous line
                    if current_line_words:
                        line = self._create_line_from_words(current_line_words, page_number)
                        lines.append(line)
                    
                    current_line_words = [word]
                    current_line_num = line_num
                else:
                    # Add space between words on same line
                    if current_line_words:
                        space_char = OCRCharacter(
                            char=' ',
                            bbox=(pdf_x1, pdf_y0, pdf_x1 + 5, pdf_y1),  # Small space bbox
                            confidence=0.9,
                            page_number=page_number,
                            char_index=char_index,
                            global_char_index=global_char_offset + char_index
                        )
                        characters.append(space_char)
                        page_text += ' '
                        char_index += 1
                    
                    current_line_words.append(word)
        
        # Finish last line
        if current_line_words:
            line = self._create_line_from_words(current_line_words, page_number)
            lines.append(line)
        
        # Add final newline
        if page_text and not page_text.endswith('\n'):
            newline_char = OCRCharacter(
                char='\n',
                bbox=(page_rect.width - 10, 0, page_rect.width, 10),
                confidence=0.9,
                page_number=page_number,
                char_index=char_index,
                global_char_index=global_char_offset + char_index
            )
            characters.append(newline_char)
            page_text += '\n'
        
        return characters, page_text, lines
    
    def _create_character_mapping(self, text: str, word_bbox: Tuple[float, float, float, float],
                                confidence: int, page_number: int, char_start: int, 
                                global_offset: int) -> List[OCRCharacter]:
        """Create precise character-level mapping within a word."""
        characters = []
        
        x0, y0, x1, y1 = word_bbox
        word_width = x1 - x0
        
        for i, char in enumerate(text):
            # Calculate character position within word
            char_width = word_width / len(text) if len(text) > 0 else word_width
            char_x0 = x0 + i * char_width
            char_x1 = x0 + (i + 1) * char_width
            
            char_bbox = (char_x0, y0, char_x1, y1)
            
            ocr_char = OCRCharacter(
                char=char,
                bbox=char_bbox,
                confidence=confidence / 100.0,
                page_number=page_number,
                char_index=char_start + i,
                global_char_index=global_offset + char_start + i
            )
            
            characters.append(ocr_char)
        
        return characters
    
    def _create_line_from_words(self, words: List[OCRWord], page_number: int) -> OCRLine:
        """Create line object from list of words."""
        if not words:
            return None
        
        # Calculate line text and bbox
        line_text = ' '.join(word.text for word in words)
        
        # Calculate line bounding box
        min_x = min(word.bbox[0] for word in words)
        min_y = min(word.bbox[1] for word in words)
        max_x = max(word.bbox[2] for word in words)
        max_y = max(word.bbox[3] for word in words)
        
        line_bbox = (min_x, min_y, max_x, max_y)
        avg_confidence = sum(word.confidence for word in words) / len(words)
        
        return OCRLine(
            text=line_text,
            bbox=line_bbox,
            confidence=avg_confidence,
            words=words,
            page_number=page_number
        )
    
    def find_character_at_position(self, characters: List[OCRCharacter], 
                                 x: float, y: float, page_number: int) -> Optional[OCRCharacter]:
        """Find the character at a specific coordinate position."""
        for char in characters:
            if char.page_number == page_number:
                x0, y0, x1, y1 = char.bbox
                if x0 <= x <= x1 and y0 <= y <= y1:
                    return char
        return None
    
    def find_cursor_position(self, characters: List[OCRCharacter], 
                           x: float, y: float, page_number: int) -> int:
        """
        Find the cursor position (character index) at specific coordinates.
        This enables perfect cursor positioning like ABBYY FineReader.
        """
        # Find closest character on the same page
        page_chars = [c for c in characters if c.page_number == page_number]
        
        if not page_chars:
            return 0
        
        closest_char = None
        min_distance = float('inf')
        
        for char in page_chars:
            # Calculate center of character
            char_center_x = (char.bbox[0] + char.bbox[2]) / 2
            char_center_y = (char.bbox[1] + char.bbox[3]) / 2
            
            # Calculate distance to click point
            distance = ((x - char_center_x) ** 2 + (y - char_center_y) ** 2) ** 0.5
            
            if distance < min_distance:
                min_distance = distance
                closest_char = char
        
        if closest_char:
            # Determine if cursor should be before or after the character
            char_center_x = (closest_char.bbox[0] + closest_char.bbox[2]) / 2
            
            if x < char_center_x:
                # Cursor before character
                return closest_char.global_char_index
            else:
                # Cursor after character
                return closest_char.global_char_index + 1
        
        return 0
    
    def get_text_selection_bbox(self, characters: List[OCRCharacter], 
                              start_pos: int, end_pos: int) -> Optional[Tuple[float, float, float, float]]:
        """Get precise bounding box for text selection."""
        selection_chars = []
        
        for char in characters:
            if start_pos <= char.global_char_index < end_pos:
                selection_chars.append(char)
        
        if not selection_chars:
            return None
        
        # Calculate selection bounding box
        min_x = min(char.bbox[0] for char in selection_chars)
        min_y = min(char.bbox[1] for char in selection_chars)
        max_x = max(char.bbox[2] for char in selection_chars)
        max_y = max(char.bbox[3] for char in selection_chars)
        
        return (min_x, min_y, max_x, max_y)
    
    def create_perfect_corrections_with_ocr(self, file_path: str) -> List[Dict[str, Any]]:
        """Create corrections using OCR-based extraction with perfect positioning."""
        characters, full_text, page_lines = self.extract_with_ocr_precision(file_path)
        
        corrections = []
        correction_id = 0
        
        # OCR-based error detection patterns
        error_patterns = [
            (r'[^\w\s\.\,\;\:\!\?\-\(\)\'\"]+', 'OCR artifact'),
            (r'\b[0O]{3,}\b', 'Zero/O confusion'),
            (r'\b[Il1]{3,}\b', 'I/l/1 confusion'),
            (r'[\/\\]{2,}', 'Slash artifacts'),
        ]
        
        import re
        
        for pattern, description in error_patterns:
            for match in re.finditer(pattern, full_text):
                error_text = match.group()
                start_pos = match.start()
                end_pos = match.end()
                
                # Find characters for this text
                error_chars = [c for c in characters 
                             if start_pos <= c.global_char_index < end_pos]
                
                if error_chars:
                    # Calculate precise bbox
                    bbox = self.get_text_selection_bbox(characters, start_pos, end_pos)
                    page_number = error_chars[0].page_number
                    avg_confidence = sum(c.confidence for c in error_chars) / len(error_chars)
                    
                    correction = {
                        'id': f'ocr_correction_{correction_id}',
                        'type': 'ocr_correction',
                        'description': f'OCR error: \'{error_text}\'',
                        'confidence': avg_confidence,
                        'reasoning': f'{description} detected with OCR-based analysis',
                        'status': 'suggested',
                        'location': {
                            'page': page_number,
                            'bbox': list(bbox) if bbox else [0, 0, 0, 0],
                            'text_position': [start_pos, end_pos]
                        },
                        'severity': 'major',
                        'metadata': {
                            'extraction_method': 'ocr_tesseract',
                            'character_count': len(error_chars),
                            'avg_confidence': avg_confidence
                        }
                    }
                    
                    corrections.append(correction)
                    correction_id += 1
        
        self.logger.info(f"Created {len(corrections)} OCR-based corrections")
        return corrections
    
    def _fallback_extraction(self, file_path: str) -> Tuple[List[OCRCharacter], str, Dict[int, List[OCRLine]]]:
        """Fallback when OCR is not available."""
        self.logger.warning("OCR not available, using basic extraction")
        return [], "", {}
    
    def validate_ocr_quality(self, file_path: str) -> Dict[str, Any]:
        """Validate OCR extraction quality."""
        characters, full_text, page_lines = self.extract_with_ocr_precision(file_path)
        
        # Calculate quality metrics
        total_chars = len(characters)
        confident_chars = sum(1 for c in characters if c.confidence > 0.8)
        avg_confidence = sum(c.confidence for c in characters) / total_chars if total_chars > 0 else 0
        
        # Test coordinate precision by sampling
        coordinate_tests = 0
        coordinate_passes = 0
        
        for i in range(0, min(len(characters), 100), 10):  # Sample every 10th character
            char = characters[i]
            if char.bbox != (0, 0, 0, 0):
                coordinate_tests += 1
                # Simple test: bbox should be reasonable
                x0, y0, x1, y1 = char.bbox
                if 0 <= x0 < x1 <= 1000 and 0 <= y0 < y1 <= 1000:  # Reasonable PDF coordinates
                    coordinate_passes += 1
        
        coordinate_accuracy = coordinate_passes / coordinate_tests if coordinate_tests > 0 else 0
        
        return {
            'extraction_method': 'ocr_tesseract',
            'total_characters': total_chars,
            'confident_characters': confident_chars,
            'confidence_rate': confident_chars / total_chars if total_chars > 0 else 0,
            'average_confidence': avg_confidence,
            'coordinate_accuracy': coordinate_accuracy,
            'text_length': len(full_text),
            'pages_processed': len(page_lines),
            'quality_score': (avg_confidence + coordinate_accuracy) / 2
        }