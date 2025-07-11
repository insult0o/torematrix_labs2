#!/usr/bin/env python3
"""
Complex content toolset for multi-column layouts, mixed content, and special formatting.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
import time
import re
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image
import numpy as np

from .base_toolset import BaseToolset
from ...config.settings import Settings

# Optional libraries for advanced layout analysis
try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    cv2 = None


class ComplexToolset(BaseToolset):
    """Advanced toolset for complex document layouts and mixed content."""
    
    def __init__(self, settings: Settings):
        super().__init__(settings)
        
        # Complex content-specific processing options
        self.processing_options.update({
            'layout_analysis': True,
            'column_detection': True,
            'reading_order_analysis': True,
            'content_segmentation': True,
            'format_preservation': True,
            'structure_recognition': True,
            'mixed_content_handling': True,
            'output_formats': ['json', 'xml', 'html', 'markdown', 'structured_text']
        })
        
        # Layout analysis capabilities
        self.analysis_capabilities = {
            'column_detection': OPENCV_AVAILABLE,
            'text_block_detection': True,
            'reading_order_analysis': True,
            'structure_recognition': True,
            'format_analysis': True,
            'mixed_content_processing': True
        }
        
        # Layout patterns
        self.layout_patterns = {
            'multi_column': {
                'indicators': ['column', 'columns', 'multi-column'],
                'visual_cues': ['vertical_separation', 'aligned_text_blocks'],
                'characteristics': ['parallel_text', 'column_gaps', 'justified_text']
            },
            'mixed_content': {
                'indicators': ['figure', 'table', 'image', 'caption'],
                'visual_cues': ['text_image_mix', 'varied_formatting'],
                'characteristics': ['embedded_objects', 'wrapped_text', 'varied_spacing']
            },
            'hierarchical': {
                'indicators': ['heading', 'section', 'subsection', 'title'],
                'visual_cues': ['font_size_variation', 'indentation'],
                'characteristics': ['nested_structure', 'numbered_sections', 'bullet_points']
            },
            'tabular_text': {
                'indicators': ['aligned', 'tabulated', 'formatted'],
                'visual_cues': ['aligned_columns', 'consistent_spacing'],
                'characteristics': ['data_alignment', 'column_headers', 'row_structure']
            }
        }
        
        self.logger.info(f"Complex toolset initialized with capabilities: {self.analysis_capabilities}")
    
    def process_area(self, area_data: Dict, pdf_document: fitz.Document) -> Dict:
        """Process a complex content area with comprehensive layout analysis."""
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
            
            # Extract complex content
            extraction_result = self.extract_content(area_data, pdf_document)
            
            # Enhance with additional analysis
            enhanced_result = self._enhance_complex_analysis(extraction_result, area_data)
            
            # Postprocessing
            final_result = self.postprocess_result(enhanced_result, area_data)
            
            # Update timing
            self.metrics['processing_time'] += time.time() - start_time
            
            return final_result
            
        except Exception as e:
            self.logger.error(f"Complex content processing failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'content': None,
                'processing_time': time.time() - start_time
            }
    
    def extract_content(self, area_data: Dict, pdf_document: fitz.Document) -> Dict:
        """Extract and analyze complex content layout."""
        try:
            # Get preprocessed image and text
            preprocessed = self.preprocess_area(area_data, pdf_document)
            if not preprocessed['preprocessing_success']:
                return {
                    'success': False,
                    'error': 'Complex content preprocessing failed',
                    'content': None
                }
            
            image = preprocessed['image']
            text_content = preprocessed['text_content']
            
            # Layout analysis
            layout_analysis = self._analyze_layout(image, text_content, area_data, pdf_document)
            
            # Content segmentation
            content_segments = self._segment_content(image, text_content, layout_analysis)
            
            # Reading order analysis
            reading_order = self._analyze_reading_order(content_segments, layout_analysis)
            
            # Structure recognition
            structure = self._recognize_structure(content_segments, reading_order)
            
            # Format preservation
            formatting = self._preserve_formatting(content_segments, layout_analysis)
            
            # Generate comprehensive description
            description = self._generate_complex_description(layout_analysis, content_segments, structure)
            
            return {
                'success': True,
                'content': {
                    'layout_analysis': layout_analysis,
                    'content_segments': content_segments,
                    'reading_order': reading_order,
                    'structure': structure,
                    'formatting': formatting,
                    'description': description
                },
                'raw_content': text_content,
                'structured_content': {
                    'type': 'complex',
                    'layout_type': layout_analysis.get('detected_layout', 'unknown'),
                    'segments': content_segments,
                    'reading_order': reading_order,
                    'metadata': {
                        'segment_count': len(content_segments),
                        'layout_complexity': self._calculate_layout_complexity(layout_analysis),
                        'has_columns': layout_analysis.get('column_count', 0) > 1,
                        'has_mixed_content': layout_analysis.get('has_mixed_content', False)
                    }
                },
                'confidence_score': layout_analysis.get('confidence', 75.0)
            }
            
        except Exception as e:
            self.logger.error(f"Complex content extraction failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'content': None
            }
    
    def _analyze_layout(self, image: Image.Image, text_content: str, area_data: Dict, pdf_document: fitz.Document) -> Dict:
        """Analyze the layout of complex content."""
        layout_analysis = {
            'detected_layout': 'unknown',
            'confidence': 50.0,
            'column_count': 1,
            'has_mixed_content': False,
            'text_blocks': [],
            'layout_features': {},
            'spatial_structure': {}
        }
        
        try:
            # Detect layout type
            layout_type = self._detect_layout_type(image, text_content)
            layout_analysis.update(layout_type)
            
            # Analyze columns
            column_analysis = self._analyze_columns(image, text_content, area_data, pdf_document)
            layout_analysis.update(column_analysis)
            
            # Detect text blocks
            text_blocks = self._detect_text_blocks(image, text_content, area_data, pdf_document)
            layout_analysis['text_blocks'] = text_blocks
            
            # Analyze spatial structure
            spatial_structure = self._analyze_spatial_structure(image, text_blocks)
            layout_analysis['spatial_structure'] = spatial_structure
            
            # Detect mixed content
            mixed_content = self._detect_mixed_content(image, text_content)
            layout_analysis['has_mixed_content'] = mixed_content
            
            return layout_analysis
            
        except Exception as e:
            self.logger.error(f"Layout analysis failed: {e}")
            layout_analysis['error'] = str(e)
            return layout_analysis
    
    def _detect_layout_type(self, image: Image.Image, text_content: str) -> Dict:
        """Detect the type of layout."""
        type_scores = {}
        
        try:
            # Analyze text content for layout indicators
            text_lower = text_content.lower()
            
            for layout_type, patterns in self.layout_patterns.items():
                score = 0
                
                # Check for text indicators
                for indicator in patterns['indicators']:
                    if indicator in text_lower:
                        score += 10
                
                # Check for characteristic patterns
                for characteristic in patterns['characteristics']:
                    if characteristic.replace('_', ' ') in text_lower:
                        score += 5
                
                type_scores[layout_type] = score
            
            # Visual analysis
            visual_analysis = self._analyze_visual_layout(image)
            
            # Combine text and visual scores
            for layout_type, visual_score in visual_analysis.items():
                if layout_type in type_scores:
                    type_scores[layout_type] += visual_score
                else:
                    type_scores[layout_type] = visual_score
            
            # Determine best match
            if type_scores:
                best_type = max(type_scores, key=type_scores.get)
                confidence = min(type_scores[best_type] / 25.0 * 100, 100)
            else:
                best_type = 'unknown'
                confidence = 0
            
            return {
                'detected_layout': best_type,
                'confidence': confidence,
                'type_scores': type_scores
            }
            
        except Exception as e:
            self.logger.error(f"Layout type detection failed: {e}")
            return {
                'detected_layout': 'unknown',
                'confidence': 0,
                'error': str(e)
            }
    
    def _analyze_visual_layout(self, image: Image.Image) -> Dict:
        """Analyze visual layout patterns."""
        visual_scores = {
            'multi_column': 0,
            'mixed_content': 0,
            'hierarchical': 0,
            'tabular_text': 0
        }
        
        try:
            if not OPENCV_AVAILABLE:
                return visual_scores
            
            # Convert to OpenCV format
            img_array = np.array(image)
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            
            # Analyze layout features
            height, width = gray.shape
            
            # Column detection
            columns = self._detect_visual_columns(gray)
            if columns > 1:
                visual_scores['multi_column'] += 20
            
            # Mixed content detection
            shapes = self._detect_layout_shapes(gray)
            if shapes['rectangles'] > 2 and shapes['text_regions'] > 0:
                visual_scores['mixed_content'] += 15
            
            # Hierarchical structure detection
            if self._detect_hierarchical_structure(gray):
                visual_scores['hierarchical'] += 18
            
            # Tabular text detection
            if self._detect_tabular_alignment(gray):
                visual_scores['tabular_text'] += 16
            
            return visual_scores
            
        except Exception as e:
            self.logger.error(f"Visual layout analysis failed: {e}")
            return visual_scores
    
    def _detect_visual_columns(self, gray_image) -> int:
        """Detect number of columns visually."""
        try:
            if not OPENCV_AVAILABLE:
                return 1
            
            height, width = gray_image.shape
            
            # Analyze vertical white spaces
            vertical_profile = np.sum(gray_image, axis=0)
            
            # Smooth the profile
            kernel = np.ones(5) / 5
            smoothed = np.convolve(vertical_profile, kernel, mode='same')
            
            # Find valleys (potential column separators)
            threshold = np.mean(smoothed) * 1.2
            valleys = []
            
            for i in range(1, len(smoothed) - 1):
                if smoothed[i] < threshold and smoothed[i] < smoothed[i-1] and smoothed[i] < smoothed[i+1]:
                    valleys.append(i)
            
            # Filter valleys that are too close
            filtered_valleys = []
            min_distance = width * 0.1  # Minimum 10% of width between columns
            
            for valley in valleys:
                if not filtered_valleys or valley - filtered_valleys[-1] > min_distance:
                    filtered_valleys.append(valley)
            
            # Number of columns = number of valleys + 1
            return len(filtered_valleys) + 1 if filtered_valleys else 1
            
        except Exception as e:
            self.logger.error(f"Visual column detection failed: {e}")
            return 1
    
    def _detect_layout_shapes(self, gray_image) -> Dict:
        """Detect shapes that indicate layout structure."""
        shapes = {
            'rectangles': 0,
            'text_regions': 0,
            'lines': 0
        }
        
        try:
            if not OPENCV_AVAILABLE:
                return shapes
            
            # Edge detection
            edges = cv2.Canny(gray_image, 50, 150)
            
            # Find contours
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                area = cv2.contourArea(contour)
                if area < 200:  # Skip small contours
                    continue
                
                # Approximate contour
                epsilon = 0.02 * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)
                
                if len(approx) == 4:
                    # Rectangle
                    x, y, w, h = cv2.boundingRect(approx)
                    aspect_ratio = w / h
                    
                    if aspect_ratio > 2:  # Wide rectangle (potential text region)
                        shapes['text_regions'] += 1
                    else:
                        shapes['rectangles'] += 1
            
            # Detect lines
            lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50, minLineLength=30, maxLineGap=10)
            shapes['lines'] = len(lines) if lines is not None else 0
            
            return shapes
            
        except Exception as e:
            self.logger.error(f"Layout shape detection failed: {e}")
            return shapes
    
    def _detect_hierarchical_structure(self, gray_image) -> bool:
        """Detect hierarchical structure in layout."""
        try:
            if not OPENCV_AVAILABLE:
                return False
            
            height, width = gray_image.shape
            
            # Analyze horizontal structure
            horizontal_profile = np.sum(gray_image, axis=1)
            
            # Look for patterns that suggest hierarchical structure
            # (e.g., varying line heights, indentation patterns)
            
            # Calculate variance in line heights
            line_heights = []
            in_text = False
            current_line_start = 0
            
            threshold = np.mean(horizontal_profile) * 0.8
            
            for i, value in enumerate(horizontal_profile):
                if value < threshold and not in_text:
                    # Start of text line
                    in_text = True
                    current_line_start = i
                elif value >= threshold and in_text:
                    # End of text line
                    in_text = False
                    line_height = i - current_line_start
                    if line_height > 2:  # Minimum line height
                        line_heights.append(line_height)
            
            # Check for variation in line heights (suggests headings/hierarchy)
            if len(line_heights) > 3:
                height_variance = np.var(line_heights)
                mean_height = np.mean(line_heights)
                
                # High variance relative to mean suggests hierarchical structure
                return height_variance > (mean_height * 0.5)
            
            return False
            
        except Exception as e:
            self.logger.error(f"Hierarchical structure detection failed: {e}")
            return False
    
    def _detect_tabular_alignment(self, gray_image) -> bool:
        """Detect tabular alignment in text."""
        try:
            if not OPENCV_AVAILABLE:
                return False
            
            height, width = gray_image.shape
            
            # Analyze vertical alignment
            vertical_profile = np.sum(gray_image, axis=0)
            
            # Look for regular patterns that suggest columns
            # Find peaks in the profile (text columns)
            threshold = np.mean(vertical_profile) * 0.8
            peaks = []
            
            for i in range(1, len(vertical_profile) - 1):
                if (vertical_profile[i] > threshold and 
                    vertical_profile[i] > vertical_profile[i-1] and 
                    vertical_profile[i] > vertical_profile[i+1]):
                    peaks.append(i)
            
            # Check for regular spacing between peaks
            if len(peaks) >= 3:
                spacings = [peaks[i+1] - peaks[i] for i in range(len(peaks) - 1)]
                spacing_variance = np.var(spacings)
                mean_spacing = np.mean(spacings)
                
                # Low variance in spacing suggests tabular alignment
                return spacing_variance < (mean_spacing * 0.3)
            
            return False
            
        except Exception as e:
            self.logger.error(f"Tabular alignment detection failed: {e}")
            return False
    
    def _analyze_columns(self, image: Image.Image, text_content: str, area_data: Dict, pdf_document: fitz.Document) -> Dict:
        """Analyze column structure in detail."""
        column_analysis = {
            'column_count': 1,
            'column_boundaries': [],
            'column_text': [],
            'column_widths': [],
            'column_gaps': []
        }
        
        try:
            # Visual column detection
            if OPENCV_AVAILABLE:
                img_array = np.array(image)
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
                
                column_count = self._detect_visual_columns(gray)
                column_analysis['column_count'] = column_count
                
                if column_count > 1:
                    # Analyze column boundaries
                    boundaries = self._find_column_boundaries(gray, column_count)
                    column_analysis['column_boundaries'] = boundaries
                    
                    # Extract text from each column
                    column_texts = self._extract_column_texts(area_data, pdf_document, boundaries)
                    column_analysis['column_text'] = column_texts
                    
                    # Calculate column widths and gaps
                    if len(boundaries) > 1:
                        widths = []
                        gaps = []
                        
                        for i in range(len(boundaries) - 1):
                            if i == 0:
                                width = boundaries[i+1] - 0
                            else:
                                width = boundaries[i+1] - boundaries[i]
                                gap = boundaries[i] - boundaries[i-1] - widths[-1] if widths else 0
                                gaps.append(gap)
                            
                            widths.append(width)
                        
                        column_analysis['column_widths'] = widths
                        column_analysis['column_gaps'] = gaps
            
            return column_analysis
            
        except Exception as e:
            self.logger.error(f"Column analysis failed: {e}")
            return column_analysis
    
    def _find_column_boundaries(self, gray_image, column_count: int) -> List[int]:
        """Find the boundaries between columns."""
        boundaries = []
        
        try:
            height, width = gray_image.shape
            
            # Analyze vertical white spaces
            vertical_profile = np.sum(gray_image, axis=0)
            
            # Smooth the profile
            kernel = np.ones(5) / 5
            smoothed = np.convolve(vertical_profile, kernel, mode='same')
            
            # Find valleys (potential column separators)
            threshold = np.mean(smoothed) * 1.2
            valleys = []
            
            for i in range(1, len(smoothed) - 1):
                if smoothed[i] < threshold and smoothed[i] < smoothed[i-1] and smoothed[i] < smoothed[i+1]:
                    valleys.append((i, smoothed[i]))
            
            # Sort by depth (lower value = deeper valley)
            valleys.sort(key=lambda x: x[1])
            
            # Take the deepest valleys up to column_count - 1
            boundaries = [v[0] for v in valleys[:column_count-1]]
            boundaries.sort()
            
            return boundaries
            
        except Exception as e:
            self.logger.error(f"Column boundary detection failed: {e}")
            return []
    
    def _extract_column_texts(self, area_data: Dict, pdf_document: fitz.Document, boundaries: List[int]) -> List[str]:
        """Extract text from each column."""
        column_texts = []
        
        try:
            page_num = area_data.get('page', 1) - 1
            bbox = area_data.get('bbox', [0, 0, 100, 100])
            
            if page_num >= len(pdf_document):
                return column_texts
            
            page = pdf_document[page_num]
            area_rect = fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3])
            
            # Calculate column rectangles
            area_width = area_rect.width
            
            if not boundaries:
                # Single column
                column_texts.append(page.get_text("text", clip=area_rect))
            else:
                # Multiple columns
                prev_boundary = 0
                
                for i, boundary in enumerate(boundaries + [area_width]):
                    # Calculate column rectangle
                    col_x0 = area_rect.x0 + (prev_boundary / area_width) * area_rect.width
                    col_x1 = area_rect.x0 + (boundary / area_width) * area_rect.width
                    
                    col_rect = fitz.Rect(col_x0, area_rect.y0, col_x1, area_rect.y1)
                    
                    # Extract text from column
                    col_text = page.get_text("text", clip=col_rect)
                    column_texts.append(col_text)
                    
                    prev_boundary = boundary
            
            return column_texts
            
        except Exception as e:
            self.logger.error(f"Column text extraction failed: {e}")
            return []
    
    def _detect_text_blocks(self, image: Image.Image, text_content: str, area_data: Dict, pdf_document: fitz.Document) -> List[Dict]:
        """Detect individual text blocks within the area."""
        text_blocks = []
        
        try:
            page_num = area_data.get('page', 1) - 1
            bbox = area_data.get('bbox', [0, 0, 100, 100])
            
            if page_num >= len(pdf_document):
                return text_blocks
            
            page = pdf_document[page_num]
            area_rect = fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3])
            
            # Get text blocks from PyMuPDF
            blocks = page.get_text("dict", clip=area_rect)
            
            for block_idx, block in enumerate(blocks.get("blocks", [])):
                if "lines" in block:  # Text block
                    # Extract text from block
                    block_text = ""
                    for line in block["lines"]:
                        for span in line["spans"]:
                            block_text += span["text"] + " "
                    
                    # Get block bounding box
                    block_bbox = block["bbox"]
                    
                    text_blocks.append({
                        'id': f"block_{block_idx}",
                        'type': 'text',
                        'text': block_text.strip(),
                        'bbox': block_bbox,
                        'position': {
                            'x': block_bbox[0],
                            'y': block_bbox[1],
                            'width': block_bbox[2] - block_bbox[0],
                            'height': block_bbox[3] - block_bbox[1]
                        },
                        'properties': {
                            'line_count': len(block["lines"]),
                            'word_count': len(block_text.split()),
                            'char_count': len(block_text)
                        }
                    })
                else:  # Image block
                    block_bbox = block["bbox"]
                    
                    text_blocks.append({
                        'id': f"block_{block_idx}",
                        'type': 'image',
                        'text': '',
                        'bbox': block_bbox,
                        'position': {
                            'x': block_bbox[0],
                            'y': block_bbox[1],
                            'width': block_bbox[2] - block_bbox[0],
                            'height': block_bbox[3] - block_bbox[1]
                        },
                        'properties': {
                            'is_image': True,
                            'image_data': block.get('image', None)
                        }
                    })
            
            return text_blocks
            
        except Exception as e:
            self.logger.error(f"Text block detection failed: {e}")
            return []
    
    def _analyze_spatial_structure(self, image: Image.Image, text_blocks: List[Dict]) -> Dict:
        """Analyze spatial relationships between text blocks."""
        spatial_structure = {
            'block_relationships': [],
            'spatial_groups': [],
            'alignment_patterns': {},
            'proximity_clusters': []
        }
        
        try:
            if not text_blocks:
                return spatial_structure
            
            # Analyze relationships between blocks
            for i, block1 in enumerate(text_blocks):
                for j, block2 in enumerate(text_blocks[i+1:], i+1):
                    relationship = self._analyze_block_relationship(block1, block2)
                    if relationship:
                        spatial_structure['block_relationships'].append(relationship)
            
            # Detect alignment patterns
            alignment_patterns = self._detect_alignment_patterns(text_blocks)
            spatial_structure['alignment_patterns'] = alignment_patterns
            
            # Create proximity clusters
            proximity_clusters = self._create_proximity_clusters(text_blocks)
            spatial_structure['proximity_clusters'] = proximity_clusters
            
            return spatial_structure
            
        except Exception as e:
            self.logger.error(f"Spatial structure analysis failed: {e}")
            return spatial_structure
    
    def _analyze_block_relationship(self, block1: Dict, block2: Dict) -> Optional[Dict]:
        """Analyze relationship between two text blocks."""
        try:
            pos1 = block1['position']
            pos2 = block2['position']
            
            # Calculate distances
            center1 = (pos1['x'] + pos1['width'] / 2, pos1['y'] + pos1['height'] / 2)
            center2 = (pos2['x'] + pos2['width'] / 2, pos2['y'] + pos2['height'] / 2)
            
            distance = ((center2[0] - center1[0]) ** 2 + (center2[1] - center1[1]) ** 2) ** 0.5
            
            # Determine relationship type
            relationship_type = 'distant'
            
            if distance < 50:
                relationship_type = 'adjacent'
            elif distance < 100:
                relationship_type = 'nearby'
            
            # Determine spatial relationship
            dx = center2[0] - center1[0]
            dy = center2[1] - center1[1]
            
            if abs(dx) > abs(dy):
                spatial_relation = 'horizontal'
                if dx > 0:
                    direction = 'right'
                else:
                    direction = 'left'
            else:
                spatial_relation = 'vertical'
                if dy > 0:
                    direction = 'below'
                else:
                    direction = 'above'
            
            return {
                'block1_id': block1['id'],
                'block2_id': block2['id'],
                'distance': distance,
                'relationship_type': relationship_type,
                'spatial_relation': spatial_relation,
                'direction': direction,
                'overlap': self._calculate_overlap(pos1, pos2)
            }
            
        except Exception as e:
            self.logger.error(f"Block relationship analysis failed: {e}")
            return None
    
    def _calculate_overlap(self, pos1: Dict, pos2: Dict) -> float:
        """Calculate overlap between two rectangles."""
        try:
            # Calculate intersection
            x1 = max(pos1['x'], pos2['x'])
            y1 = max(pos1['y'], pos2['y'])
            x2 = min(pos1['x'] + pos1['width'], pos2['x'] + pos2['width'])
            y2 = min(pos1['y'] + pos1['height'], pos2['y'] + pos2['height'])
            
            if x2 > x1 and y2 > y1:
                intersection = (x2 - x1) * (y2 - y1)
                area1 = pos1['width'] * pos1['height']
                area2 = pos2['width'] * pos2['height']
                union = area1 + area2 - intersection
                
                return intersection / union if union > 0 else 0
            else:
                return 0
                
        except Exception as e:
            return 0
    
    def _detect_alignment_patterns(self, text_blocks: List[Dict]) -> Dict:
        """Detect alignment patterns in text blocks."""
        patterns = {
            'left_aligned': [],
            'right_aligned': [],
            'center_aligned': [],
            'top_aligned': [],
            'bottom_aligned': []
        }
        
        try:
            # Group blocks by alignment
            tolerance = 10  # pixels
            
            # Left alignment
            left_positions = {}
            for block in text_blocks:
                x = block['position']['x']
                
                # Find existing group or create new one
                found_group = False
                for group_x, group_blocks in left_positions.items():
                    if abs(x - group_x) <= tolerance:
                        group_blocks.append(block['id'])
                        found_group = True
                        break
                
                if not found_group:
                    left_positions[x] = [block['id']]
            
            # Keep only groups with multiple blocks
            for x, blocks in left_positions.items():
                if len(blocks) > 1:
                    patterns['left_aligned'].append({
                        'position': x,
                        'blocks': blocks
                    })
            
            # Similar logic for other alignments...
            # (Implementation would follow similar pattern)
            
            return patterns
            
        except Exception as e:
            self.logger.error(f"Alignment pattern detection failed: {e}")
            return patterns
    
    def _create_proximity_clusters(self, text_blocks: List[Dict]) -> List[Dict]:
        """Create clusters of nearby text blocks."""
        clusters = []
        
        try:
            # Simple clustering based on proximity
            used_blocks = set()
            cluster_id = 0
            
            for block in text_blocks:
                if block['id'] in used_blocks:
                    continue
                
                # Start new cluster
                cluster = {
                    'id': f"cluster_{cluster_id}",
                    'blocks': [block['id']],
                    'centroid': {
                        'x': block['position']['x'] + block['position']['width'] / 2,
                        'y': block['position']['y'] + block['position']['height'] / 2
                    },
                    'bounding_box': dict(block['position'])
                }
                
                used_blocks.add(block['id'])
                
                # Find nearby blocks
                for other_block in text_blocks:
                    if other_block['id'] in used_blocks:
                        continue
                    
                    # Calculate distance
                    center1 = (cluster['centroid']['x'], cluster['centroid']['y'])
                    center2 = (
                        other_block['position']['x'] + other_block['position']['width'] / 2,
                        other_block['position']['y'] + other_block['position']['height'] / 2
                    )
                    
                    distance = ((center2[0] - center1[0]) ** 2 + (center2[1] - center1[1]) ** 2) ** 0.5
                    
                    if distance < 100:  # Threshold for clustering
                        cluster['blocks'].append(other_block['id'])
                        used_blocks.add(other_block['id'])
                        
                        # Update cluster properties
                        self._update_cluster_properties(cluster, other_block)
                
                clusters.append(cluster)
                cluster_id += 1
            
            return clusters
            
        except Exception as e:
            self.logger.error(f"Proximity clustering failed: {e}")
            return []
    
    def _update_cluster_properties(self, cluster: Dict, new_block: Dict):
        """Update cluster properties when adding a new block."""
        try:
            # Update centroid
            block_center = (
                new_block['position']['x'] + new_block['position']['width'] / 2,
                new_block['position']['y'] + new_block['position']['height'] / 2
            )
            
            cluster_size = len(cluster['blocks'])
            cluster['centroid']['x'] = (cluster['centroid']['x'] * (cluster_size - 1) + block_center[0]) / cluster_size
            cluster['centroid']['y'] = (cluster['centroid']['y'] * (cluster_size - 1) + block_center[1]) / cluster_size
            
            # Update bounding box
            cluster['bounding_box']['x'] = min(cluster['bounding_box']['x'], new_block['position']['x'])
            cluster['bounding_box']['y'] = min(cluster['bounding_box']['y'], new_block['position']['y'])
            
            max_x = max(
                cluster['bounding_box']['x'] + cluster['bounding_box']['width'],
                new_block['position']['x'] + new_block['position']['width']
            )
            max_y = max(
                cluster['bounding_box']['y'] + cluster['bounding_box']['height'],
                new_block['position']['y'] + new_block['position']['height']
            )
            
            cluster['bounding_box']['width'] = max_x - cluster['bounding_box']['x']
            cluster['bounding_box']['height'] = max_y - cluster['bounding_box']['y']
            
        except Exception as e:
            self.logger.error(f"Cluster property update failed: {e}")
    
    def _segment_content(self, image: Image.Image, text_content: str, layout_analysis: Dict) -> List[Dict]:
        """Segment content into logical units."""
        segments = []
        
        try:
            text_blocks = layout_analysis.get('text_blocks', [])
            
            # Group text blocks into logical segments
            for i, block in enumerate(text_blocks):
                segment = {
                    'id': f"segment_{i}",
                    'type': self._classify_segment_type(block),
                    'content': block['text'],
                    'position': block['position'],
                    'properties': {
                        'block_id': block['id'],
                        'word_count': block['properties'].get('word_count', 0),
                        'char_count': block['properties'].get('char_count', 0),
                        'formatting': self._analyze_segment_formatting(block)
                    }
                }
                
                segments.append(segment)
            
            return segments
            
        except Exception as e:
            self.logger.error(f"Content segmentation failed: {e}")
            return []
    
    def _classify_segment_type(self, block: Dict) -> str:
        """Classify the type of content segment."""
        try:
            text = block.get('text', '').strip()
            
            if not text:
                return 'empty'
            
            # Check for heading patterns
            if self._is_heading(text):
                return 'heading'
            
            # Check for list items
            if self._is_list_item(text):
                return 'list_item'
            
            # Check for table-like content
            if self._is_tabular_content(text):
                return 'tabular'
            
            # Check for captions
            if self._is_caption(text):
                return 'caption'
            
            # Default to paragraph
            return 'paragraph'
            
        except Exception as e:
            self.logger.error(f"Segment type classification failed: {e}")
            return 'unknown'
    
    def _is_heading(self, text: str) -> bool:
        """Check if text is likely a heading."""
        # Simple heuristics for heading detection
        if len(text) > 100:  # Too long for heading
            return False
        
        # Check for heading indicators
        heading_patterns = [
            r'^\d+\.?\s+',  # Numbered headings
            r'^[A-Z][A-Z\s]+$',  # All caps
            r'^[A-Z][a-z]+:$',  # Title case with colon
        ]
        
        for pattern in heading_patterns:
            if re.match(pattern, text):
                return True
        
        return False
    
    def _is_list_item(self, text: str) -> bool:
        """Check if text is likely a list item."""
        list_patterns = [
            r'^\s*[\u2022\u2023\u25E6\u2043\u2219]\s+',  # Bullet points
            r'^\s*\d+[\.\)]\s+',  # Numbered lists
            r'^\s*[a-zA-Z][\.\)]\s+',  # Lettered lists
            r'^\s*[-\*\+]\s+',  # Dash/asterisk lists
        ]
        
        for pattern in list_patterns:
            if re.match(pattern, text):
                return True
        
        return False
    
    def _is_tabular_content(self, text: str) -> bool:
        """Check if text is likely tabular content."""
        # Look for patterns that suggest tabular data
        lines = text.split('\n')
        
        if len(lines) < 2:
            return False
        
        # Check for consistent column separators
        separators = ['\t', '  ', ' | ', '|']
        
        for sep in separators:
            if all(sep in line for line in lines if line.strip()):
                return True
        
        return False
    
    def _is_caption(self, text: str) -> bool:
        """Check if text is likely a caption."""
        caption_indicators = [
            r'^(figure|fig|table|chart|image)\s*\d*:',
            r'^(source|note):',
            r'^\([^)]+\)$',  # Text in parentheses
        ]
        
        text_lower = text.lower()
        
        for pattern in caption_indicators:
            if re.match(pattern, text_lower):
                return True
        
        return False
    
    def _analyze_segment_formatting(self, block: Dict) -> Dict:
        """Analyze formatting characteristics of a segment."""
        formatting = {
            'font_info': {},
            'alignment': 'left',
            'spacing': {},
            'style': 'normal'
        }
        
        try:
            # This would require more detailed font analysis
            # For now, provide basic formatting info
            
            position = block['position']
            text = block.get('text', '')
            
            # Estimate alignment based on position
            # (This is a simplified approach)
            if position['x'] < 50:
                formatting['alignment'] = 'left'
            elif position['x'] > 400:  # Assuming page width
                formatting['alignment'] = 'right'
            else:
                formatting['alignment'] = 'center'
            
            # Estimate style based on text characteristics
            if text.isupper():
                formatting['style'] = 'bold'
            elif text.islower():
                formatting['style'] = 'normal'
            elif text.istitle():
                formatting['style'] = 'title'
            
            return formatting
            
        except Exception as e:
            self.logger.error(f"Segment formatting analysis failed: {e}")
            return formatting
    
    def _analyze_reading_order(self, content_segments: List[Dict], layout_analysis: Dict) -> Dict:
        """Analyze and determine reading order of content segments."""
        reading_order = {
            'sequence': [],
            'confidence': 0.0,
            'method': 'position_based',
            'flow_patterns': []
        }
        
        try:
            if not content_segments:
                return reading_order
            
            # Sort segments by position (top-to-bottom, left-to-right)
            sorted_segments = sorted(content_segments, key=lambda s: (s['position']['y'], s['position']['x']))
            
            # Analyze for column-based reading order
            column_count = layout_analysis.get('column_count', 1)
            
            if column_count > 1:
                reading_order = self._analyze_column_reading_order(sorted_segments, layout_analysis)
            else:
                reading_order = self._analyze_single_column_reading_order(sorted_segments)
            
            return reading_order
            
        except Exception as e:
            self.logger.error(f"Reading order analysis failed: {e}")
            return reading_order
    
    def _analyze_column_reading_order(self, segments: List[Dict], layout_analysis: Dict) -> Dict:
        """Analyze reading order for multi-column layout."""
        reading_order = {
            'sequence': [],
            'confidence': 85.0,
            'method': 'column_based',
            'flow_patterns': []
        }
        
        try:
            column_boundaries = layout_analysis.get('column_boundaries', [])
            
            if not column_boundaries:
                return self._analyze_single_column_reading_order(segments)
            
            # Group segments by column
            columns = [[] for _ in range(len(column_boundaries) + 1)]
            
            for segment in segments:
                segment_x = segment['position']['x']
                
                # Determine which column this segment belongs to
                column_index = 0
                for i, boundary in enumerate(column_boundaries):
                    if segment_x > boundary:
                        column_index = i + 1
                    else:
                        break
                
                columns[column_index].append(segment)
            
            # Sort segments within each column by Y position
            for column in columns:
                column.sort(key=lambda s: s['position']['y'])
            
            # Create reading sequence (read each column top-to-bottom)
            sequence = []
            for column in columns:
                for segment in column:
                    sequence.append(segment['id'])
            
            reading_order['sequence'] = sequence
            
            return reading_order
            
        except Exception as e:
            self.logger.error(f"Column reading order analysis failed: {e}")
            return reading_order
    
    def _analyze_single_column_reading_order(self, segments: List[Dict]) -> Dict:
        """Analyze reading order for single-column layout."""
        reading_order = {
            'sequence': [],
            'confidence': 90.0,
            'method': 'top_to_bottom',
            'flow_patterns': []
        }
        
        try:
            # Simple top-to-bottom reading order
            sorted_segments = sorted(segments, key=lambda s: (s['position']['y'], s['position']['x']))
            
            sequence = [segment['id'] for segment in sorted_segments]
            reading_order['sequence'] = sequence
            
            return reading_order
            
        except Exception as e:
            self.logger.error(f"Single column reading order analysis failed: {e}")
            return reading_order
    
    def _recognize_structure(self, content_segments: List[Dict], reading_order: Dict) -> Dict:
        """Recognize document structure from content segments."""
        structure = {
            'hierarchy': [],
            'sections': [],
            'relationships': [],
            'document_type': 'unknown'
        }
        
        try:
            # Analyze segment types to build hierarchy
            sequence = reading_order.get('sequence', [])
            
            current_section = None
            hierarchy_level = 0
            
            for segment_id in sequence:
                segment = next((s for s in content_segments if s['id'] == segment_id), None)
                if not segment:
                    continue
                
                segment_type = segment.get('type', 'paragraph')
                
                if segment_type == 'heading':
                    # Start new section
                    if current_section:
                        structure['sections'].append(current_section)
                    
                    current_section = {
                        'id': f"section_{len(structure['sections'])}",
                        'title': segment['content'],
                        'level': hierarchy_level,
                        'segments': [segment_id]
                    }
                    
                    structure['hierarchy'].append({
                        'level': hierarchy_level,
                        'title': segment['content'],
                        'segment_id': segment_id
                    })
                    
                else:
                    # Add to current section
                    if current_section:
                        current_section['segments'].append(segment_id)
                    else:
                        # Create default section
                        current_section = {
                            'id': f"section_{len(structure['sections'])}",
                            'title': 'Content',
                            'level': 0,
                            'segments': [segment_id]
                        }
            
            # Add final section
            if current_section:
                structure['sections'].append(current_section)
            
            # Determine document type
            structure['document_type'] = self._classify_document_type(content_segments)
            
            return structure
            
        except Exception as e:
            self.logger.error(f"Structure recognition failed: {e}")
            return structure
    
    def _classify_document_type(self, content_segments: List[Dict]) -> str:
        """Classify the type of document based on content segments."""
        try:
            segment_types = [segment.get('type', 'paragraph') for segment in content_segments]
            
            # Count segment types
            type_counts = {}
            for seg_type in segment_types:
                type_counts[seg_type] = type_counts.get(seg_type, 0) + 1
            
            # Simple classification based on content
            if type_counts.get('tabular', 0) > len(content_segments) * 0.3:
                return 'data_report'
            elif type_counts.get('heading', 0) > 2:
                return 'structured_document'
            elif type_counts.get('list_item', 0) > len(content_segments) * 0.2:
                return 'procedural_document'
            else:
                return 'general_document'
                
        except Exception as e:
            self.logger.error(f"Document type classification failed: {e}")
            return 'unknown'
    
    def _preserve_formatting(self, content_segments: List[Dict], layout_analysis: Dict) -> Dict:
        """Preserve formatting information for content segments."""
        formatting = {
            'global_style': {},
            'segment_styles': {},
            'layout_properties': {}
        }
        
        try:
            # Analyze global formatting properties
            formatting['global_style'] = {
                'layout_type': layout_analysis.get('detected_layout', 'unknown'),
                'column_count': layout_analysis.get('column_count', 1),
                'has_mixed_content': layout_analysis.get('has_mixed_content', False)
            }
            
            # Preserve segment-specific formatting
            for segment in content_segments:
                segment_formatting = segment.get('properties', {}).get('formatting', {})
                formatting['segment_styles'][segment['id']] = segment_formatting
            
            # Layout properties
            formatting['layout_properties'] = {
                'spatial_structure': layout_analysis.get('spatial_structure', {}),
                'text_blocks': len(layout_analysis.get('text_blocks', [])),
                'complexity_score': self._calculate_layout_complexity(layout_analysis)
            }
            
            return formatting
            
        except Exception as e:
            self.logger.error(f"Formatting preservation failed: {e}")
            return formatting
    
    def _calculate_layout_complexity(self, layout_analysis: Dict) -> float:
        """Calculate complexity score for the layout."""
        try:
            complexity = 0
            
            # Base complexity on number of text blocks
            text_blocks = layout_analysis.get('text_blocks', [])
            complexity += len(text_blocks) * 3
            
            # Add complexity for columns
            column_count = layout_analysis.get('column_count', 1)
            complexity += (column_count - 1) * 10
            
            # Add complexity for mixed content
            if layout_analysis.get('has_mixed_content', False):
                complexity += 15
            
            # Add complexity for spatial relationships
            spatial_structure = layout_analysis.get('spatial_structure', {})
            relationships = spatial_structure.get('block_relationships', [])
            complexity += len(relationships) * 2
            
            # Normalize to 0-100 scale
            max_complexity = 100
            return min(100, (complexity / max_complexity) * 100)
            
        except Exception as e:
            self.logger.error(f"Layout complexity calculation failed: {e}")
            return 50.0
    
    def _generate_complex_description(self, layout_analysis: Dict, content_segments: List[Dict], structure: Dict) -> Dict:
        """Generate comprehensive description of complex content."""
        try:
            layout_type = layout_analysis.get('detected_layout', 'unknown')
            segment_count = len(content_segments)
            column_count = layout_analysis.get('column_count', 1)
            
            descriptions = {}
            
            # Brief description
            descriptions['brief'] = f"A {layout_type.replace('_', ' ')} layout with {segment_count} content segments"
            if column_count > 1:
                descriptions['brief'] += f" arranged in {column_count} columns"
            descriptions['brief'] += "."
            
            # Detailed description
            details = []
            details.append(f"This is a {layout_type.replace('_', ' ')} layout")
            details.append(f"containing {segment_count} content segments")
            
            if column_count > 1:
                details.append(f"arranged in {column_count} columns")
            
            # Add structure information
            sections = structure.get('sections', [])
            if sections:
                details.append(f"organized into {len(sections)} sections")
            
            # Add content type information
            segment_types = {}
            for segment in content_segments:
                seg_type = segment.get('type', 'paragraph')
                segment_types[seg_type] = segment_types.get(seg_type, 0) + 1
            
            type_desc = []
            for seg_type, count in segment_types.items():
                if count > 1:
                    type_desc.append(f"{count} {seg_type}s")
                else:
                    type_desc.append(f"{count} {seg_type}")
            
            if type_desc:
                details.append(f"including {', '.join(type_desc)}")
            
            descriptions['detailed'] = '. '.join(details) + '.'
            
            # Comprehensive description
            comprehensive = []
            comprehensive.append(f"Complex Layout Analysis: {layout_type.replace('_', ' ')}")
            comprehensive.append(f"Layout confidence: {layout_analysis.get('confidence', 0):.1f}%")
            comprehensive.append(f"Content segments: {segment_count}")
            
            if column_count > 1:
                comprehensive.append(f"Column structure: {column_count} columns")
            
            # Structure information
            doc_type = structure.get('document_type', 'unknown')
            comprehensive.append(f"Document type: {doc_type}")
            
            # Complexity information
            complexity = self._calculate_layout_complexity(layout_analysis)
            comprehensive.append(f"Layout complexity: {complexity:.1f}/100")
            
            # Mixed content information
            if layout_analysis.get('has_mixed_content', False):
                comprehensive.append("Contains mixed content types")
            
            descriptions['comprehensive'] = '. '.join(comprehensive) + '.'
            
            return descriptions
            
        except Exception as e:
            self.logger.error(f"Complex description generation failed: {e}")
            return {
                'brief': 'Complex content analysis failed',
                'detailed': f'Unable to generate description: {str(e)}',
                'comprehensive': f'Description generation error: {str(e)}'
            }
    
    def _enhance_complex_analysis(self, extraction_result: Dict, area_data: Dict) -> Dict:
        """Enhance complex content analysis with additional processing."""
        if not extraction_result.get('success'):
            return extraction_result
        
        try:
            # Add contextual information
            context = {
                'document_context': {
                    'page_number': area_data.get('page', 1),
                    'area_type': area_data.get('type', 'COMPLEX'),
                    'processing_notes': area_data.get('special_notes', ''),
                    'high_priority': area_data.get('high_priority', False)
                },
                'layout_recommendations': self._generate_layout_recommendations(extraction_result),
                'processing_guidelines': self._generate_processing_guidelines(extraction_result)
            }
            
            # Add context to result
            extraction_result['context'] = context
            
            # Generate output formats
            extraction_result['output_formats'] = self._generate_output_formats(extraction_result)
            
            return extraction_result
            
        except Exception as e:
            self.logger.error(f"Complex content enhancement failed: {e}")
            extraction_result['enhancement_error'] = str(e)
            return extraction_result
    
    def _generate_layout_recommendations(self, extraction_result: Dict) -> List[str]:
        """Generate recommendations for layout processing."""
        recommendations = []
        
        try:
            content = extraction_result.get('content', {})
            layout_analysis = content.get('layout_analysis', {})
            
            # Layout-specific recommendations
            layout_type = layout_analysis.get('detected_layout', 'unknown')
            confidence = layout_analysis.get('confidence', 0)
            
            if confidence < 70:
                recommendations.append("Consider manual verification of layout type")
            
            column_count = layout_analysis.get('column_count', 1)
            if column_count > 3:
                recommendations.append("Complex multi-column layout - verify reading order")
            
            # Content recommendations
            content_segments = content.get('content_segments', [])
            if len(content_segments) > 20:
                recommendations.append("High content density - consider segmentation")
            
            # Mixed content recommendations
            if layout_analysis.get('has_mixed_content', False):
                recommendations.append("Mixed content detected - verify content boundaries")
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Layout recommendations failed: {e}")
            return ['Layout recommendations unavailable due to error']
    
    def _generate_processing_guidelines(self, extraction_result: Dict) -> Dict:
        """Generate processing guidelines for complex content."""
        guidelines = {
            'reading_order': 'Follow detected sequence',
            'content_preservation': 'Maintain original formatting',
            'structure_handling': 'Preserve hierarchical structure',
            'special_considerations': []
        }
        
        try:
            content = extraction_result.get('content', {})
            layout_analysis = content.get('layout_analysis', {})
            
            # Layout-specific guidelines
            layout_type = layout_analysis.get('detected_layout', 'unknown')
            
            if layout_type == 'multi_column':
                guidelines['reading_order'] = 'Column-by-column, top-to-bottom'
                guidelines['special_considerations'].append('Maintain column boundaries')
            
            elif layout_type == 'mixed_content':
                guidelines['content_preservation'] = 'Preserve content type boundaries'
                guidelines['special_considerations'].append('Handle embedded objects carefully')
            
            elif layout_type == 'hierarchical':
                guidelines['structure_handling'] = 'Preserve section hierarchy'
                guidelines['special_considerations'].append('Maintain heading levels')
            
            return guidelines
            
        except Exception as e:
            self.logger.error(f"Processing guidelines generation failed: {e}")
            return guidelines
    
    def _generate_output_formats(self, extraction_result: Dict) -> Dict:
        """Generate complex content analysis in multiple output formats."""
        formats = {}
        
        try:
            content = extraction_result.get('content', {})
            
            # JSON format (default)
            formats['json'] = content
            
            # XML format
            formats['xml'] = self._generate_xml_format(content)
            
            # HTML format
            formats['html'] = self._generate_html_format(content)
            
            # Markdown format
            formats['markdown'] = self._generate_markdown_format(content)
            
            # Structured text format
            formats['structured_text'] = self._generate_structured_text_format(content)
            
        except Exception as e:
            self.logger.error(f"Output format generation failed: {e}")
            formats['error'] = str(e)
        
        return formats
    
    def _generate_xml_format(self, content: Dict) -> str:
        """Generate XML format for complex content."""
        try:
            lines = []
            lines.append('<?xml version="1.0" encoding="UTF-8"?>')
            lines.append('<complex_content>')
            
            # Layout information
            layout_analysis = content.get('layout_analysis', {})
            lines.append(f'<layout type="{layout_analysis.get("detected_layout", "unknown")}" columns="{layout_analysis.get("column_count", 1)}">')
            
            # Content segments
            content_segments = content.get('content_segments', [])
            for segment in content_segments:
                lines.append(f'<segment id="{segment["id"]}" type="{segment.get("type", "paragraph")}">')
                lines.append(f'<content><![CDATA[{segment.get("content", "")}]]></content>')
                lines.append('</segment>')
            
            lines.append('</layout>')
            lines.append('</complex_content>')
            
            return '\n'.join(lines)
            
        except Exception as e:
            return f'<!-- XML generation failed: {str(e)} -->'
    
    def _generate_html_format(self, content: Dict) -> str:
        """Generate HTML format for complex content."""
        try:
            lines = []
            lines.append('<div class="complex-content">')
            
            # Layout information
            layout_analysis = content.get('layout_analysis', {})
            layout_type = layout_analysis.get('detected_layout', 'unknown')
            column_count = layout_analysis.get('column_count', 1)
            
            lines.append(f'<div class="layout-info">')
            lines.append(f'<span class="layout-type">{layout_type.replace("_", " ").title()}</span>')
            if column_count > 1:
                lines.append(f'<span class="column-count">{column_count} columns</span>')
            lines.append('</div>')
            
            # Content segments
            content_segments = content.get('content_segments', [])
            
            if column_count > 1:
                lines.append(f'<div class="columns" style="columns: {column_count};">')
            
            for segment in content_segments:
                segment_type = segment.get('type', 'paragraph')
                content_text = segment.get('content', '')
                
                if segment_type == 'heading':
                    lines.append(f'<h3>{content_text}</h3>')
                elif segment_type == 'list_item':
                    lines.append(f'<li>{content_text}</li>')
                elif segment_type == 'caption':
                    lines.append(f'<div class="caption">{content_text}</div>')
                else:
                    lines.append(f'<p>{content_text}</p>')
            
            if column_count > 1:
                lines.append('</div>')
            
            lines.append('</div>')
            
            return '\n'.join(lines)
            
        except Exception as e:
            return f'<!-- HTML generation failed: {str(e)} -->'
    
    def _generate_markdown_format(self, content: Dict) -> str:
        """Generate Markdown format for complex content."""
        try:
            lines = []
            
            # Title
            layout_analysis = content.get('layout_analysis', {})
            layout_type = layout_analysis.get('detected_layout', 'unknown')
            lines.append(f"# {layout_type.replace('_', ' ').title()} Content Analysis")
            lines.append("")
            
            # Layout information
            column_count = layout_analysis.get('column_count', 1)
            if column_count > 1:
                lines.append(f"**Layout:** {column_count} columns")
                lines.append("")
            
            # Content segments
            content_segments = content.get('content_segments', [])
            
            for segment in content_segments:
                segment_type = segment.get('type', 'paragraph')
                content_text = segment.get('content', '')
                
                if segment_type == 'heading':
                    lines.append(f"## {content_text}")
                elif segment_type == 'list_item':
                    lines.append(f"- {content_text}")
                elif segment_type == 'caption':
                    lines.append(f"*{content_text}*")
                else:
                    lines.append(content_text)
                
                lines.append("")
            
            return '\n'.join(lines)
            
        except Exception as e:
            return f"Markdown generation failed: {str(e)}"
    
    def _generate_structured_text_format(self, content: Dict) -> str:
        """Generate structured text format for complex content."""
        try:
            lines = []
            
            # Reading order
            reading_order = content.get('reading_order', {})
            sequence = reading_order.get('sequence', [])
            
            content_segments = content.get('content_segments', [])
            segment_map = {s['id']: s for s in content_segments}
            
            for segment_id in sequence:
                segment = segment_map.get(segment_id)
                if segment:
                    content_text = segment.get('content', '')
                    lines.append(content_text)
                    lines.append("")  # Add spacing between segments
            
            return '\n'.join(lines)
            
        except Exception as e:
            return f"Structured text generation failed: {str(e)}"
    
    def validate_extraction(self, extracted_content: Dict) -> Dict:
        """Validate complex content extraction results."""
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
            
            content = extracted_content.get('content', {})
            
            # Check required components
            if not content.get('content_segments'):
                validation['issues'].append('No content segments detected')
            
            if not content.get('layout_analysis'):
                validation['issues'].append('Layout analysis not performed')
            
            # Check layout analysis quality
            layout_analysis = content.get('layout_analysis', {})
            layout_confidence = layout_analysis.get('confidence', 0)
            
            if layout_confidence < 50:
                validation['issues'].append('Low confidence in layout analysis')
            
            # Check content quality
            content_segments = content.get('content_segments', [])
            if len(content_segments) < 1:
                validation['issues'].append('Insufficient content segments')
            
            # Calculate validation score
            validation['confidence'] = extracted_content.get('confidence_score', 0)
            validation['quality_score'] = layout_confidence
            validation['is_valid'] = len(validation['issues']) == 0 and layout_confidence > 30
            
        except Exception as e:
            validation['issues'].append(f'Validation error: {str(e)}')
        
        return validation
    
    def get_supported_formats(self) -> List[str]:
        """Get supported output formats."""
        return ['json', 'xml', 'html', 'markdown', 'structured_text']