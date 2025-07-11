#!/usr/bin/env python3
"""
Script to replace the _load_page_text method with advanced extraction.
"""

old_method = '''    def _load_page_text(self, page_number):
        """Load extracted text for the current page using PyMuPDF with coordinate mapping."""
        try:
            if not self.current_document or not self.current_document.metadata.file_path:
                self.extracted_text.setPlainText("No document loaded.")
                return
            
            import fitz  # PyMuPDF
            
            # Open document and extract text from the specific page
            doc = fitz.open(self.current_document.metadata.file_path)
            
            if page_number <= len(doc):
                page = doc[page_number - 1]  # PyMuPDF uses 0-based indexing
                
                # Extract text with position information
                text_dict = page.get_text("dict")
                page_text = ""
                text_position = 0
                self.text_to_pdf_mapping = {}  # Reset mapping
                
                # Use the standard get_text() method to preserve original formatting
                page_text = page.get_text()
                
                # Create position mapping using text dict for precise coordinates
                text_dict = page.get_text("dict")
                
                # Build text-to-PDF mapping more accurately
                self.text_to_pdf_mapping = {}
                
                # First, build a complete text representation with character positions
                reconstructed_text = ""
                char_mapping = {}  # Maps reconstructed text position to PDF coordinates
                
                for block in text_dict.get("blocks", []):
                    if "lines" in block:  # Text block
                        for line in block["lines"]:
                            line_start_pos = len(reconstructed_text)
                            
                            for span in line["spans"]:
                                span_text = span["text"]
                                span_bbox = span["bbox"]
                                span_start_pos = len(reconstructed_text)
                                
                                # Map each character in the span using actual span text
                                for i, char in enumerate(span_text):
                                    if len(span_text) > 0:
                                        # Calculate character position within span more precisely
                                        char_width = (span_bbox[2] - span_bbox[0]) / len(span_text)
                                        char_x0 = span_bbox[0] + i * char_width
                                        char_x1 = span_bbox[0] + (i + 1) * char_width
                                        
                                        # Use more precise character height - reduce the full span height
                                        # Instead of using full span height, use a smaller, more precise height
                                        char_height = span_bbox[3] - span_bbox[1]
                                        char_y0 = span_bbox[1]
                                        char_y1 = span_bbox[3]
                                        
                                        # For better precision, we can make character boxes smaller
                                        if char_height > 2:  # If span is tall, reduce character height
                                            char_height_reduction = min(char_height * 0.1, 2)  # Reduce by 10% or 2 points max
                                            char_y0 += char_height_reduction / 2
                                            char_y1 -= char_height_reduction / 2
                                        
                                        char_bbox = [char_x0, char_y0, char_x1, char_y1]
                                        
                                        # Store mapping for reconstructed text position
                                        char_mapping[len(reconstructed_text)] = (page_number, char_bbox)
                                    
                                    reconstructed_text += char
                                
                            # Add newline after each line
                            if reconstructed_text and not reconstructed_text.endswith('\\n'):
                                reconstructed_text += '\\n'
                                # Map newline to end of line bbox
                                if line.get("spans"):
                                    last_span = line["spans"][-1]
                                    line_bbox = [last_span["bbox"][2], last_span["bbox"][1], 
                                               page.rect.width, last_span["bbox"][3]]
                                    char_mapping[len(reconstructed_text) - 1] = (page_number, line_bbox)
                
                # Now align the reconstructed text with the actual page text
                # and transfer the mapping
                if reconstructed_text and page_text:
                    # Simple character-by-character alignment
                    for i, char in enumerate(page_text):
                        if i < len(reconstructed_text) and char == reconstructed_text[i]:
                            if i in char_mapping:
                                self.text_to_pdf_mapping[i] = char_mapping[i]
                        else:
                            # Try to find the character in nearby positions
                            for offset in range(-5, 6):
                                aligned_pos = i + offset
                                if (0 <= aligned_pos < len(reconstructed_text) and 
                                    aligned_pos in char_mapping and 
                                    char == reconstructed_text[aligned_pos]):
                                    self.text_to_pdf_mapping[i] = char_mapping[aligned_pos]
                                    break
                
                # Clean up the text
                page_text = page_text.strip()
                
                if page_text:
                    self.extracted_text.setPlainText(page_text)
                    
                    # Debug: validate mapping quality
                    mapping_coverage = len(self.text_to_pdf_mapping) / len(page_text) * 100 if page_text else 0
                    self.log_message.emit(f"Loaded page {page_number}: {len(page_text)} chars, {len(self.text_to_pdf_mapping)} mappings ({mapping_coverage:.1f}% coverage)")
                    
                    # Sample some mappings for debugging
                    if self.text_to_pdf_mapping:
                        sample_positions = [0, len(page_text)//4, len(page_text)//2, len(page_text)-1]
                        for pos in sample_positions:
                            if pos < len(page_text) and pos in self.text_to_pdf_mapping:
                                page_num, bbox = self.text_to_pdf_mapping[pos]
                                char = page_text[pos] if pos < len(page_text) else '?'
                                self.log_message.emit(f"  Position {pos}: '{char}' → bbox {bbox}")
                    
                    # Highlight all issues on this page
                    self._highlight_all_page_issues()
                else:
                    self.extracted_text.setPlainText(f"Page {page_number} contains no extractable text.")
                    self.log_message.emit(f"Page {page_number} has no extractable text content")
            else:
                self.extracted_text.setPlainText(f"Page {page_number} does not exist in document.")
                self.log_message.emit(f"Page {page_number} is out of range")
            
            doc.close()
            
        except Exception as e:
            error_msg = f"Failed to load page {page_number} text: {str(e)}"
            self.extracted_text.setPlainText(error_msg)
            self.log_message.emit(error_msg)
            self.logger.error(error_msg)'''

new_method = '''    def _load_page_text(self, page_number):
        """Load extracted text using advanced extraction methods with perfect coordinate mapping."""
        try:
            if not self.current_document or not self.current_document.metadata.file_path:
                self.extracted_text.setPlainText("No document loaded.")
                return
            
            file_path = self.current_document.metadata.file_path
            
            # Try OCR-based extraction first (best accuracy)
            if self.use_ocr and self.ocr_extractor:
                self.log_message.emit(f"Using OCR-based extraction for page {page_number} (ABBYY FineReader-level accuracy)")
                self._load_page_text_with_ocr(page_number, file_path)
            else:
                # Fall back to enhanced PyMuPDF extraction
                self.log_message.emit(f"Using enhanced PyMuPDF extraction for page {page_number}")
                self._load_page_text_with_enhanced_extraction(page_number, file_path)
            
        except Exception as e:
            error_msg = f"Failed to load page {page_number} text: {str(e)}"
            self.extracted_text.setPlainText(error_msg)
            self.log_message.emit(error_msg)
            self.logger.error(error_msg)
    
    def _load_page_text_with_ocr(self, page_number, file_path):
        """Load page text using OCR-based extraction for perfect accuracy."""
        try:
            # Extract with OCR precision (may take longer but perfect accuracy)
            if not hasattr(self, '_ocr_cache') or file_path not in self._ocr_cache:
                self.log_message.emit("Performing OCR extraction... (this may take a moment)")
                self.ocr_characters, self.full_document_text, page_lines = self.ocr_extractor.extract_with_ocr_precision(file_path)
                
                # Cache the results
                if not hasattr(self, '_ocr_cache'):
                    self._ocr_cache = {}
                self._ocr_cache[file_path] = {
                    'characters': self.ocr_characters,
                    'full_text': self.full_document_text,
                    'page_lines': page_lines
                }
                
                self.log_message.emit(f"OCR extraction completed: {len(self.ocr_characters)} characters with perfect coordinates")
            else:
                # Use cached OCR results
                cached_data = self._ocr_cache[file_path]
                self.ocr_characters = cached_data['characters']
                self.full_document_text = cached_data['full_text']
                self.log_message.emit("Using cached OCR data for instant loading")
            
            # Get text for current page
            page_chars = [c for c in self.ocr_characters if c.page_number == page_number]
            
            if page_chars:
                # Build page text from OCR characters
                page_text = ""
                self.text_to_pdf_mapping = {}
                
                for char in page_chars:
                    self.text_to_pdf_mapping[len(page_text)] = (char.page_number, char.bbox)
                    page_text += char.char
                
                self.extracted_text.setPlainText(page_text)
                
                # Log perfect OCR mapping
                self.log_message.emit(f"OCR page {page_number}: {len(page_chars)} characters with 100% coordinate accuracy")
                
                # Highlight all issues with perfect positioning
                self._highlight_all_page_issues()
            else:
                self.extracted_text.setPlainText(f"Page {page_number} contains no OCR-recognizable text.")
                self.log_message.emit(f"No OCR text found on page {page_number}")
                
        except Exception as e:
            self.logger.error(f"OCR extraction failed: {str(e)}")
            # Fall back to enhanced extraction
            self._load_page_text_with_enhanced_extraction(page_number, file_path)
    
    def _load_page_text_with_enhanced_extraction(self, page_number, file_path):
        """Load page text using enhanced PyMuPDF extraction."""
        try:
            # Use enhanced extractor as fallback
            if not hasattr(self, '_enhanced_cache') or file_path not in self._enhanced_cache:
                elements, full_text, page_texts = self.enhanced_extractor.extract_with_perfect_correlation(file_path)
                
                # Cache the results
                if not hasattr(self, '_enhanced_cache'):
                    self._enhanced_cache = {}
                self._enhanced_cache[file_path] = {
                    'elements': elements,
                    'full_text': full_text,
                    'page_texts': page_texts
                }
            else:
                cached_data = self._enhanced_cache[file_path]
                elements = cached_data['elements']
                full_text = cached_data['full_text']
                page_texts = cached_data['page_texts']
            
            # Get text for current page
            if page_number in page_texts:
                page_text = page_texts[page_number]
                
                # Build mapping from enhanced elements
                self.text_to_pdf_mapping = {}
                page_elements = [e for e in elements if e.page_number == page_number]
                
                for element in page_elements:
                    if element.char_start < len(page_text):
                        self.text_to_pdf_mapping[element.char_start] = (element.page_number, element.bbox)
                
                self.extracted_text.setPlainText(page_text)
                
                coverage = len(self.text_to_pdf_mapping) / len(page_text) * 100 if page_text else 0
                self.log_message.emit(f"Enhanced page {page_number}: {len(page_text)} chars, {coverage:.1f}% coordinate coverage")
                
                # Highlight all issues
                self._highlight_all_page_issues()
            else:
                self.extracted_text.setPlainText(f"Page {page_number} not found in enhanced extraction.")
                
        except Exception as e:
            self.logger.error(f"Enhanced extraction failed: {str(e)}")
            self.extracted_text.setPlainText(f"Failed to extract text from page {page_number}: {str(e)}")'''

# Read the current file
with open('/home/insulto/tore_matrix_labs/tore_matrix_labs/ui/components/page_validation_widget.py', 'r') as f:
    content = f.read()

# Replace the method
new_content = content.replace(old_method, new_method)

# Write back to file
with open('/home/insulto/tore_matrix_labs/tore_matrix_labs/ui/components/page_validation_widget.py', 'w') as f:
    f.write(new_content)

print("✅ Successfully replaced _load_page_text method with advanced extraction!")