#!/usr/bin/env python3
"""
Table extraction and processing toolset with advanced table detection and correction capabilities.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
import re
import time
import io
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image
import numpy as np

from .base_toolset import BaseToolset
from ...config.settings import Settings

# Optional advanced table extraction libraries
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    pd = None

try:
    import camelot
    CAMELOT_AVAILABLE = True
except ImportError:
    CAMELOT_AVAILABLE = False
    camelot = None

try:
    import tabula
    TABULA_AVAILABLE = True
except ImportError:
    TABULA_AVAILABLE = False
    tabula = None


class TableToolset(BaseToolset):
    """Advanced table extraction and processing toolset."""
    
    def __init__(self, settings: Settings):
        super().__init__(settings)
        
        # Table-specific processing options
        self.processing_options.update({
            'table_detection_method': 'hybrid',  # 'lattice', 'stream', 'hybrid'
            'preserve_formatting': True,
            'include_headers': True,
            'include_footers': True,
            'merge_cells': True,
            'auto_detect_structure': True,
            'output_formats': ['json', 'csv', 'html', 'markdown']
        })
        
        # Table extraction strategies in order of preference
        self.extraction_strategies = []
        
        if CAMELOT_AVAILABLE:
            self.extraction_strategies.append('camelot')
        if TABULA_AVAILABLE:
            self.extraction_strategies.append('tabula')
        
        self.extraction_strategies.extend(['pymupdf', 'ocr_based'])
        
        self.logger.info(f"Table toolset initialized with strategies: {self.extraction_strategies}")
    
    def process_area(self, area_data: Dict, pdf_document: fitz.Document) -> Dict:
        """Process a table area with comprehensive extraction and validation."""
        start_time = time.time()
        
        try:
            # Preprocessing
            preprocessed = self.preprocess_area(area_data, pdf_document)
            if not preprocessed['preprocessing_success']:
                return {
                    'success': False,
                    'error': preprocessed.get('error', 'Preprocessing failed'),
                    'content': None
                }
            
            # Extract table content
            extraction_result = self.extract_content(area_data, pdf_document)
            
            # Enhance with additional processing
            enhanced_result = self._enhance_table_extraction(extraction_result, area_data)
            
            # Postprocessing
            final_result = self.postprocess_result(enhanced_result, area_data)
            
            # Update timing
            self.metrics['processing_time'] += time.time() - start_time
            
            return final_result
            
        except Exception as e:
            self.logger.error(f"Table processing failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'content': None,
                'processing_time': time.time() - start_time
            }
    
    def extract_content(self, area_data: Dict, pdf_document: fitz.Document) -> Dict:
        """Extract table content using multiple strategies."""
        page_num = area_data.get('page', 1) - 1
        bbox = area_data.get('bbox', [0, 0, 100, 100])
        
        extraction_results = []
        
        # Try each extraction strategy
        for strategy in self.extraction_strategies:
            try:
                result = self._extract_with_strategy(strategy, area_data, pdf_document)
                if result and result.get('success'):
                    extraction_results.append(result)
                    self.logger.info(f"Table extraction succeeded with {strategy}")
                else:
                    self.logger.warning(f"Table extraction failed with {strategy}")
                    
            except Exception as e:
                self.logger.error(f"Table extraction strategy {strategy} failed: {e}")
                continue
        
        # Select best result
        best_result = self._select_best_extraction(extraction_results)
        
        return best_result or {
            'success': False,
            'error': 'All extraction strategies failed',
            'content': None,
            'raw_content': '',
            'structured_content': None,
            'confidence_score': 0.0
        }
    
    def _extract_with_strategy(self, strategy: str, area_data: Dict, pdf_document: fitz.Document) -> Optional[Dict]:
        """Extract table using a specific strategy."""
        
        if strategy == 'camelot' and CAMELOT_AVAILABLE:
            return self._extract_with_camelot(area_data, pdf_document)
        elif strategy == 'tabula' and TABULA_AVAILABLE:
            return self._extract_with_tabula(area_data, pdf_document)
        elif strategy == 'pymupdf':
            return self._extract_with_pymupdf(area_data, pdf_document)
        elif strategy == 'ocr_based':
            return self._extract_with_ocr(area_data, pdf_document)
        else:
            return None
    
    def _extract_with_camelot(self, area_data: Dict, pdf_document: fitz.Document) -> Dict:
        """Extract table using Camelot library."""
        try:
            # Save area as temporary PDF for Camelot
            temp_pdf_path = Path("temp_table_area.pdf")
            
            # Create temporary PDF with just the table area
            page_num = area_data.get('page', 1) - 1
            bbox = area_data.get('bbox', [0, 0, 100, 100])
            
            page = pdf_document[page_num]
            area_rect = fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3])
            
            # Extract as PDF
            new_doc = fitz.open()
            new_page = new_doc.new_page(width=area_rect.width, height=area_rect.height)
            new_page.show_pdf_page(fitz.Rect(0, 0, area_rect.width, area_rect.height), 
                                  pdf_document, page_num, clip=area_rect)
            new_doc.save(temp_pdf_path)
            new_doc.close()
            
            # Extract with Camelot
            tables = camelot.read_pdf(str(temp_pdf_path), pages='1')
            
            # Clean up
            temp_pdf_path.unlink(missing_ok=True)
            
            if tables and len(tables) > 0:
                table = tables[0]
                df = table.df
                
                return {
                    'success': True,
                    'strategy': 'camelot',
                    'content': df.to_dict('records'),
                    'raw_content': df.to_string(),
                    'structured_content': {
                        'headers': df.columns.tolist(),
                        'rows': df.values.tolist(),
                        'shape': df.shape
                    },
                    'confidence_score': table.accuracy if hasattr(table, 'accuracy') else 85.0,
                    'metadata': {
                        'parsing_report': table.parsing_report if hasattr(table, 'parsing_report') else {}
                    }
                }
            else:
                return {'success': False, 'error': 'No tables found with Camelot'}
                
        except Exception as e:
            self.logger.error(f"Camelot extraction failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def _extract_with_tabula(self, area_data: Dict, pdf_document: fitz.Document) -> Dict:
        """Extract table using Tabula library."""
        try:
            # Save area as temporary PDF for Tabula
            temp_pdf_path = Path("temp_table_area.pdf")
            
            page_num = area_data.get('page', 1) - 1
            bbox = area_data.get('bbox', [0, 0, 100, 100])
            
            page = pdf_document[page_num]
            area_rect = fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3])
            
            # Create temporary PDF
            new_doc = fitz.open()
            new_page = new_doc.new_page(width=area_rect.width, height=area_rect.height)
            new_page.show_pdf_page(fitz.Rect(0, 0, area_rect.width, area_rect.height), 
                                  pdf_document, page_num, clip=area_rect)
            new_doc.save(temp_pdf_path)
            new_doc.close()
            
            # Extract with Tabula
            tables = tabula.read_pdf(str(temp_pdf_path), pages='1')
            
            # Clean up
            temp_pdf_path.unlink(missing_ok=True)
            
            if tables and len(tables) > 0:
                df = tables[0]
                
                return {
                    'success': True,
                    'strategy': 'tabula',
                    'content': df.to_dict('records'),
                    'raw_content': df.to_string(),
                    'structured_content': {
                        'headers': df.columns.tolist(),
                        'rows': df.values.tolist(),
                        'shape': df.shape
                    },
                    'confidence_score': 80.0
                }
            else:
                return {'success': False, 'error': 'No tables found with Tabula'}
                
        except Exception as e:
            self.logger.error(f"Tabula extraction failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def _extract_with_pymupdf(self, area_data: Dict, pdf_document: fitz.Document) -> Dict:
        """Extract table using PyMuPDF's built-in table detection."""
        try:
            page_num = area_data.get('page', 1) - 1
            bbox = area_data.get('bbox', [0, 0, 100, 100])
            
            page = pdf_document[page_num]
            area_rect = fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3])
            
            # Try PyMuPDF table detection
            tables = page.find_tables(clip=area_rect)
            
            if tables:
                table = tables[0]
                table_data = table.extract()
                
                # Convert to structured format
                headers = table_data[0] if table_data else []
                rows = table_data[1:] if len(table_data) > 1 else []
                
                return {
                    'success': True,
                    'strategy': 'pymupdf',
                    'content': [dict(zip(headers, row)) for row in rows],
                    'raw_content': '\n'.join(['\t'.join(row) for row in table_data]),
                    'structured_content': {
                        'headers': headers,
                        'rows': rows,
                        'shape': (len(rows), len(headers))
                    },
                    'confidence_score': 75.0
                }
            else:
                # Fallback to text extraction with table parsing
                return self._extract_table_from_text(area_data, pdf_document)
                
        except Exception as e:
            self.logger.error(f"PyMuPDF table extraction failed: {e}")
            return self._extract_table_from_text(area_data, pdf_document)
    
    def _extract_table_from_text(self, area_data: Dict, pdf_document: fitz.Document) -> Dict:
        """Extract table from plain text using pattern recognition."""
        try:
            page_num = area_data.get('page', 1) - 1
            bbox = area_data.get('bbox', [0, 0, 100, 100])
            
            page = pdf_document[page_num]
            area_rect = fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3])
            
            # Extract text
            text = page.get_text("text", clip=area_rect)
            
            # Parse text as table
            table_data = self._parse_text_as_table(text)
            
            if table_data:
                headers = table_data[0] if table_data else []
                rows = table_data[1:] if len(table_data) > 1 else []
                
                return {
                    'success': True,
                    'strategy': 'text_parsing',
                    'content': [dict(zip(headers, row)) for row in rows],
                    'raw_content': text,
                    'structured_content': {
                        'headers': headers,
                        'rows': rows,
                        'shape': (len(rows), len(headers))
                    },
                    'confidence_score': 60.0
                }
            else:
                return {'success': False, 'error': 'Could not parse text as table'}
                
        except Exception as e:
            self.logger.error(f"Text-based table extraction failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def _parse_text_as_table(self, text: str) -> List[List[str]]:
        """Parse plain text as table structure."""
        lines = text.strip().split('\n')
        table_data = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Try different delimiters
            if '\t' in line:
                cells = line.split('\t')
            elif '|' in line:
                cells = [cell.strip() for cell in line.split('|') if cell.strip()]
            elif re.search(r'\s{2,}', line):
                cells = re.split(r'\s{2,}', line)
            else:
                cells = [line]
            
            if cells and len(cells) > 1:
                table_data.append(cells)
        
        return table_data
    
    def _extract_with_ocr(self, area_data: Dict, pdf_document: fitz.Document) -> Dict:
        """Extract table using OCR-based approach."""
        try:
            # Get preprocessed image
            preprocessed = self.preprocess_area(area_data, pdf_document)
            if not preprocessed['preprocessing_success']:
                return {'success': False, 'error': 'Preprocessing failed'}
            
            image = preprocessed['image']
            
            # Convert to grayscale and enhance for table detection
            gray_image = image.convert('L')
            
            # Simple table structure detection
            # This is a placeholder - real implementation would use advanced OCR
            text_content = preprocessed['text_content']
            table_data = self._parse_text_as_table(text_content)
            
            if table_data:
                headers = table_data[0] if table_data else []
                rows = table_data[1:] if len(table_data) > 1 else []
                
                return {
                    'success': True,
                    'strategy': 'ocr_based',
                    'content': [dict(zip(headers, row)) for row in rows],
                    'raw_content': text_content,
                    'structured_content': {
                        'headers': headers,
                        'rows': rows,
                        'shape': (len(rows), len(headers))
                    },
                    'confidence_score': 50.0
                }
            else:
                return {'success': False, 'error': 'OCR could not detect table structure'}
                
        except Exception as e:
            self.logger.error(f"OCR-based table extraction failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def _select_best_extraction(self, results: List[Dict]) -> Optional[Dict]:
        """Select the best extraction result based on confidence and quality."""
        if not results:
            return None
        
        # Sort by confidence score
        sorted_results = sorted(results, key=lambda x: x.get('confidence_score', 0), reverse=True)
        
        # Return the highest confidence result
        return sorted_results[0]
    
    def _enhance_table_extraction(self, extraction_result: Dict, area_data: Dict) -> Dict:
        """Enhance table extraction with additional processing."""
        if not extraction_result.get('success'):
            return extraction_result
        
        try:
            # Add table analysis
            structured_content = extraction_result.get('structured_content', {})
            
            # Analyze table structure
            headers = structured_content.get('headers', [])
            rows = structured_content.get('rows', [])
            
            analysis = {
                'column_count': len(headers),
                'row_count': len(rows),
                'empty_cells': 0,
                'numeric_columns': [],
                'text_columns': [],
                'has_headers': bool(headers),
                'data_types': {}
            }
            
            # Analyze data types
            for i, header in enumerate(headers):
                column_values = [row[i] if i < len(row) else '' for row in rows]
                analysis['data_types'][header] = self._analyze_column_type(column_values)
                
                if analysis['data_types'][header] in ['numeric', 'percentage']:
                    analysis['numeric_columns'].append(header)
                else:
                    analysis['text_columns'].append(header)
                
                # Count empty cells
                analysis['empty_cells'] += sum(1 for val in column_values if not str(val).strip())
            
            # Add analysis to result
            extraction_result['table_analysis'] = analysis
            
            # Generate output in multiple formats
            extraction_result['output_formats'] = self._generate_output_formats(extraction_result)
            
            return extraction_result
            
        except Exception as e:
            self.logger.error(f"Table enhancement failed: {e}")
            extraction_result['enhancement_error'] = str(e)
            return extraction_result
    
    def _analyze_column_type(self, values: List[str]) -> str:
        """Analyze column data type."""
        if not values:
            return 'empty'
        
        numeric_count = 0
        percentage_count = 0
        date_count = 0
        
        for value in values:
            value_str = str(value).strip()
            if not value_str:
                continue
            
            # Check for numeric
            if re.match(r'^-?\d+(\.\d+)?$', value_str):
                numeric_count += 1
            elif re.match(r'^-?\d+(\.\d+)?%$', value_str):
                percentage_count += 1
            elif re.match(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', value_str):
                date_count += 1
        
        total_non_empty = len([v for v in values if str(v).strip()])
        
        if total_non_empty == 0:
            return 'empty'
        
        if numeric_count / total_non_empty > 0.8:
            return 'numeric'
        elif percentage_count / total_non_empty > 0.8:
            return 'percentage'
        elif date_count / total_non_empty > 0.8:
            return 'date'
        else:
            return 'text'
    
    def _generate_output_formats(self, extraction_result: Dict) -> Dict:
        """Generate table in multiple output formats."""
        formats = {}
        
        try:
            structured_content = extraction_result.get('structured_content', {})
            headers = structured_content.get('headers', [])
            rows = structured_content.get('rows', [])
            
            # JSON format
            formats['json'] = extraction_result.get('content', [])
            
            # CSV format
            csv_lines = []
            if headers:
                csv_lines.append(','.join(f'"{header}"' for header in headers))
            for row in rows:
                csv_lines.append(','.join(f'"{cell}"' for cell in row))
            formats['csv'] = '\n'.join(csv_lines)
            
            # HTML format
            html_lines = ['<table>']
            if headers:
                html_lines.append('<thead><tr>')
                for header in headers:
                    html_lines.append(f'<th>{header}</th>')
                html_lines.append('</tr></thead>')
            
            html_lines.append('<tbody>')
            for row in rows:
                html_lines.append('<tr>')
                for cell in row:
                    html_lines.append(f'<td>{cell}</td>')
                html_lines.append('</tr>')
            html_lines.append('</tbody></table>')
            formats['html'] = '\n'.join(html_lines)
            
            # Markdown format
            if headers and rows:
                markdown_lines = []
                markdown_lines.append('| ' + ' | '.join(headers) + ' |')
                markdown_lines.append('| ' + ' | '.join(['---'] * len(headers)) + ' |')
                for row in rows:
                    markdown_lines.append('| ' + ' | '.join(row) + ' |')
                formats['markdown'] = '\n'.join(markdown_lines)
            
        except Exception as e:
            self.logger.error(f"Format generation failed: {e}")
            formats['error'] = str(e)
        
        return formats
    
    def validate_extraction(self, extracted_content: Dict) -> Dict:
        """Validate table extraction results."""
        validation = {
            'is_valid': False,
            'confidence': 0.0,
            'issues': [],
            'quality_score': 0.0
        }
        
        try:
            if not extracted_content.get('success'):
                validation['issues'].append('Extraction failed')
                return validation
            
            structured_content = extracted_content.get('structured_content', {})
            headers = structured_content.get('headers', [])
            rows = structured_content.get('rows', [])
            
            # Check basic structure
            if not headers:
                validation['issues'].append('No headers detected')
            if not rows:
                validation['issues'].append('No data rows detected')
            
            # Check consistency
            if headers and rows:
                expected_columns = len(headers)
                inconsistent_rows = [i for i, row in enumerate(rows) if len(row) != expected_columns]
                if inconsistent_rows:
                    validation['issues'].append(f'Inconsistent row lengths: {len(inconsistent_rows)} rows')
            
            # Calculate quality score
            quality_factors = []
            
            # Structure quality
            if headers and rows:
                quality_factors.append(80)
            elif headers or rows:
                quality_factors.append(40)
            else:
                quality_factors.append(0)
            
            # Data quality
            if extracted_content.get('confidence_score'):
                quality_factors.append(extracted_content['confidence_score'])
            
            # Consistency quality
            if not inconsistent_rows:
                quality_factors.append(90)
            else:
                quality_factors.append(50)
            
            validation['quality_score'] = sum(quality_factors) / len(quality_factors) if quality_factors else 0
            validation['confidence'] = extracted_content.get('confidence_score', 0)
            validation['is_valid'] = validation['quality_score'] > 50 and len(validation['issues']) == 0
            
        except Exception as e:
            validation['issues'].append(f'Validation error: {str(e)}')
        
        return validation
    
    def get_supported_formats(self) -> List[str]:
        """Get supported output formats."""
        return ['json', 'csv', 'html', 'markdown', 'xlsx']
    
    def create_editable_table(self, extraction_result: Dict) -> Dict:
        """Create an editable table structure for the UI."""
        try:
            structured_content = extraction_result.get('structured_content', {})
            headers = structured_content.get('headers', [])
            rows = structured_content.get('rows', [])
            
            # Create editable structure
            editable_table = {
                'headers': [{'text': h, 'editable': True} for h in headers],
                'rows': [
                    [{'text': cell, 'editable': True} for cell in row]
                    for row in rows
                ],
                'operations': {
                    'add_row': True,
                    'delete_row': True,
                    'add_column': True,
                    'delete_column': True,
                    'merge_cells': True,
                    'split_cells': True
                }
            }
            
            return {
                'success': True,
                'editable_table': editable_table,
                'original_extraction': extraction_result
            }
            
        except Exception as e:
            self.logger.error(f"Editable table creation failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }