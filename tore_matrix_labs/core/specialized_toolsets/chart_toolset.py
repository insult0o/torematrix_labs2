#!/usr/bin/env python3
"""
Chart processing toolset for graphs, plots, statistical charts, and data visualizations.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
import time
import re
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image, ImageDraw
import numpy as np

from .base_toolset import BaseToolset
from ...config.settings import Settings

# Optional libraries for advanced chart analysis
try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    cv2 = None

try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    plt = None
    patches = None


class ChartToolset(BaseToolset):
    """Advanced chart processing and data extraction toolset."""
    
    def __init__(self, settings: Settings):
        super().__init__(settings)
        
        # Chart-specific processing options
        self.processing_options.update({
            'chart_type_detection': True,
            'axis_extraction': True,
            'legend_extraction': True,
            'data_point_extraction': True,
            'trend_analysis': True,
            'statistical_analysis': True,
            'color_analysis': True,
            'output_formats': ['json', 'csv', 'matplotlib', 'plotly', 'markdown']
        })
        
        # Chart analysis capabilities
        self.analysis_capabilities = {
            'color_detection': True,
            'shape_detection': OPENCV_AVAILABLE,
            'text_extraction': True,
            'statistical_analysis': True,
            'trend_analysis': True,
            'data_reconstruction': True
        }
        
        # Chart type patterns
        self.chart_patterns = {
            'bar_chart': {
                'visual_indicators': ['rectangular bars', 'vertical bars', 'horizontal bars'],
                'text_indicators': ['bar', 'frequency', 'count', 'amount'],
                'structural_features': ['categorical axis', 'numerical axis', 'discrete values']
            },
            'line_chart': {
                'visual_indicators': ['connected points', 'trend lines', 'curves'],
                'text_indicators': ['time', 'trend', 'series', 'over time'],
                'structural_features': ['continuous data', 'x-y coordinates', 'temporal axis']
            },
            'pie_chart': {
                'visual_indicators': ['circular segments', 'wedges', 'slices'],
                'text_indicators': ['percentage', 'proportion', 'share', 'distribution'],
                'structural_features': ['parts of whole', 'percentages', 'categories']
            },
            'scatter_plot': {
                'visual_indicators': ['scattered points', 'dots', 'markers'],
                'text_indicators': ['correlation', 'relationship', 'distribution', 'scatter'],
                'structural_features': ['x-y coordinates', 'point clusters', 'continuous variables']
            },
            'histogram': {
                'visual_indicators': ['adjacent bars', 'frequency bars', 'distribution bars'],
                'text_indicators': ['frequency', 'distribution', 'histogram', 'bins'],
                'structural_features': ['continuous ranges', 'frequency counts', 'bins']
            },
            'area_chart': {
                'visual_indicators': ['filled areas', 'stacked areas', 'shaded regions'],
                'text_indicators': ['area', 'cumulative', 'stacked', 'filled'],
                'structural_features': ['filled regions', 'stacked data', 'continuous areas']
            }
        }
        
        self.logger.info(f"Chart toolset initialized with capabilities: {self.analysis_capabilities}")
    
    def process_area(self, area_data: Dict, pdf_document: fitz.Document) -> Dict:
        """Process a chart area with comprehensive analysis and data extraction."""
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
            
            # Extract chart content
            extraction_result = self.extract_content(area_data, pdf_document)
            
            # Enhance with additional analysis
            enhanced_result = self._enhance_chart_analysis(extraction_result, area_data)
            
            # Postprocessing
            final_result = self.postprocess_result(enhanced_result, area_data)
            
            # Update timing
            self.metrics['processing_time'] += time.time() - start_time
            
            return final_result
            
        except Exception as e:
            self.logger.error(f"Chart processing failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'content': None,
                'processing_time': time.time() - start_time
            }
    
    def extract_content(self, area_data: Dict, pdf_document: fitz.Document) -> Dict:
        """Extract and analyze chart content."""
        try:
            # Get preprocessed image
            preprocessed = self.preprocess_area(area_data, pdf_document)
            if not preprocessed['preprocessing_success']:
                return {
                    'success': False,
                    'error': 'Chart preprocessing failed',
                    'content': None
                }
            
            image = preprocessed['image']
            text_content = preprocessed['text_content']
            
            # Chart type detection
            chart_type = self._detect_chart_type(image, text_content)
            
            # Extract chart components
            components = self._extract_chart_components(image, text_content, chart_type)
            
            # Extract data points
            data_points = self._extract_data_points(image, components, chart_type)
            
            # Analyze trends and patterns
            analysis = self._analyze_chart_data(data_points, chart_type)
            
            # Generate description
            description = self._generate_chart_description(chart_type, components, data_points, analysis)
            
            return {
                'success': True,
                'content': {
                    'chart_type': chart_type,
                    'components': components,
                    'data_points': data_points,
                    'analysis': analysis,
                    'description': description
                },
                'raw_content': text_content,
                'structured_content': {
                    'type': 'chart',
                    'subtype': chart_type['detected_type'],
                    'data': data_points,
                    'metadata': {
                        'data_point_count': len(data_points),
                        'chart_complexity': self._calculate_chart_complexity(components, data_points),
                        'has_legend': components.get('legend', {}).get('detected', False),
                        'has_title': components.get('title', {}).get('detected', False)
                    }
                },
                'confidence_score': chart_type['confidence']
            }
            
        except Exception as e:
            self.logger.error(f"Chart content extraction failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'content': None
            }
    
    def _detect_chart_type(self, image: Image.Image, text_content: str) -> Dict:
        """Detect the type of chart."""
        type_scores = {}
        
        try:
            # Analyze text content for indicators
            text_lower = text_content.lower()
            
            for chart_type, patterns in self.chart_patterns.items():
                score = 0
                
                # Check text indicators
                for indicator in patterns['text_indicators']:
                    if indicator in text_lower:
                        score += 15
                
                # Check structural feature mentions
                for feature in patterns['structural_features']:
                    if feature in text_lower:
                        score += 10
                
                type_scores[chart_type] = score
            
            # Visual analysis
            visual_analysis = self._analyze_visual_chart_patterns(image)
            
            # Combine text and visual scores
            for chart_type, visual_score in visual_analysis.items():
                if chart_type in type_scores:
                    type_scores[chart_type] += visual_score
                else:
                    type_scores[chart_type] = visual_score
            
            # Determine best match
            if type_scores:
                best_type = max(type_scores, key=type_scores.get)
                max_score = type_scores[best_type]
                confidence = min(max_score / 30.0 * 100, 100)
            else:
                best_type = 'unknown'
                confidence = 0
            
            return {
                'detected_type': best_type,
                'confidence': confidence,
                'type_scores': type_scores,
                'visual_analysis': visual_analysis
            }
            
        except Exception as e:
            self.logger.error(f"Chart type detection failed: {e}")
            return {
                'detected_type': 'unknown',
                'confidence': 0,
                'error': str(e)
            }
    
    def _analyze_visual_chart_patterns(self, image: Image.Image) -> Dict:
        """Analyze visual patterns to identify chart type."""
        pattern_scores = {
            'bar_chart': 0,
            'line_chart': 0,
            'pie_chart': 0,
            'scatter_plot': 0,
            'histogram': 0,
            'area_chart': 0
        }
        
        try:
            if not OPENCV_AVAILABLE:
                return pattern_scores
            
            # Convert to OpenCV format
            img_array = np.array(image)
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            
            # Detect shapes and patterns
            shapes = self._detect_chart_shapes(gray)
            
            # Bar chart detection
            if shapes.get('rectangles', 0) > 3:
                pattern_scores['bar_chart'] += 20
                pattern_scores['histogram'] += 15
            
            # Line chart detection
            lines = self._detect_chart_lines(gray)
            if lines > 2:
                pattern_scores['line_chart'] += 15
                pattern_scores['area_chart'] += 10
            
            # Pie chart detection
            circles = self._detect_circles(gray)
            if circles > 0:
                pattern_scores['pie_chart'] += 25
            
            # Scatter plot detection
            points = self._detect_scattered_points(gray)
            if points > 10:
                pattern_scores['scatter_plot'] += 20
            
            # Color analysis for chart type hints
            color_analysis = self._analyze_chart_colors(image)
            
            # Multiple colors suggest categorical data
            if color_analysis.get('distinct_colors', 0) > 3:
                pattern_scores['bar_chart'] += 5
                pattern_scores['pie_chart'] += 10
                pattern_scores['scatter_plot'] += 5
            
            # Gradients suggest continuous data
            if color_analysis.get('has_gradients', False):
                pattern_scores['area_chart'] += 10
                pattern_scores['line_chart'] += 5
            
            return pattern_scores
            
        except Exception as e:
            self.logger.error(f"Visual pattern analysis failed: {e}")
            return pattern_scores
    
    def _detect_chart_shapes(self, gray_image) -> Dict:
        """Detect shapes relevant to chart analysis."""
        shapes = {
            'rectangles': 0,
            'circles': 0,
            'lines': 0,
            'points': 0
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
                if area < 100:  # Skip very small contours
                    continue
                
                # Approximate contour
                epsilon = 0.02 * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)
                
                if len(approx) == 4:
                    # Check if it's a rectangle
                    x, y, w, h = cv2.boundingRect(approx)
                    aspect_ratio = w / h
                    
                    if 0.2 <= aspect_ratio <= 5.0:  # Reasonable aspect ratio for chart bars
                        shapes['rectangles'] += 1
                
                elif len(approx) > 8:
                    # Likely a circle
                    shapes['circles'] += 1
                
                elif area < 500:  # Small area could be a point
                    shapes['points'] += 1
            
            return shapes
            
        except Exception as e:
            self.logger.error(f"Shape detection failed: {e}")
            return shapes
    
    def _detect_chart_lines(self, gray_image) -> int:
        """Detect lines in chart (for line charts, axes, etc.)."""
        try:
            if not OPENCV_AVAILABLE:
                return 0
            
            # Edge detection
            edges = cv2.Canny(gray_image, 50, 150)
            
            # Line detection
            lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50, minLineLength=30, maxLineGap=10)
            
            return len(lines) if lines is not None else 0
            
        except Exception as e:
            self.logger.error(f"Line detection failed: {e}")
            return 0
    
    def _detect_circles(self, gray_image) -> int:
        """Detect circles in chart (for pie charts, scatter plots)."""
        try:
            if not OPENCV_AVAILABLE:
                return 0
            
            # Circle detection using HoughCircles
            circles = cv2.HoughCircles(
                gray_image,
                cv2.HOUGH_GRADIENT,
                dp=1,
                minDist=30,
                param1=50,
                param2=30,
                minRadius=10,
                maxRadius=200
            )
            
            return len(circles[0]) if circles is not None else 0
            
        except Exception as e:
            self.logger.error(f"Circle detection failed: {e}")
            return 0
    
    def _detect_scattered_points(self, gray_image) -> int:
        """Detect scattered points (for scatter plots)."""
        try:
            if not OPENCV_AVAILABLE:
                return 0
            
            # Use blob detection for points
            params = cv2.SimpleBlobDetector_Params()
            
            # Filter by Area
            params.filterByArea = True
            params.minArea = 10
            params.maxArea = 100
            
            # Filter by Circularity
            params.filterByCircularity = True
            params.minCircularity = 0.5
            
            # Create detector
            detector = cv2.SimpleBlobDetector_create(params)
            
            # Detect blobs
            keypoints = detector.detect(gray_image)
            
            return len(keypoints)
            
        except Exception as e:
            self.logger.error(f"Scattered point detection failed: {e}")
            return 0
    
    def _analyze_chart_colors(self, image: Image.Image) -> Dict:
        """Analyze color patterns in the chart."""
        color_analysis = {
            'distinct_colors': 0,
            'dominant_colors': [],
            'has_gradients': False,
            'color_distribution': {}
        }
        
        try:
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Get color histogram
            colors = image.getcolors(maxcolors=256*256*256)
            
            if colors:
                # Sort by frequency
                colors.sort(key=lambda x: x[0], reverse=True)
                
                # Count distinct colors (ignoring very rare ones)
                min_frequency = max(1, len(colors) // 100)  # At least 1% of pixels
                distinct_colors = [c for c in colors if c[0] > min_frequency]
                
                color_analysis['distinct_colors'] = len(distinct_colors)
                
                # Get dominant colors
                dominant_colors = []
                for count, color in distinct_colors[:5]:  # Top 5 colors
                    if isinstance(color, tuple) and len(color) >= 3:
                        hex_color = f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"
                        dominant_colors.append({
                            'color': hex_color,
                            'frequency': count,
                            'percentage': count / sum(c[0] for c in colors) * 100
                        })
                
                color_analysis['dominant_colors'] = dominant_colors
                
                # Simple gradient detection (very basic)
                img_array = np.array(image)
                
                # Check for gradients by analyzing color variance
                r_var = np.var(img_array[:, :, 0])
                g_var = np.var(img_array[:, :, 1])
                b_var = np.var(img_array[:, :, 2])
                
                avg_variance = (r_var + g_var + b_var) / 3
                color_analysis['has_gradients'] = avg_variance > 1000  # Threshold for gradient detection
            
            return color_analysis
            
        except Exception as e:
            self.logger.error(f"Color analysis failed: {e}")
            return color_analysis
    
    def _extract_chart_components(self, image: Image.Image, text_content: str, chart_type: Dict) -> Dict:
        """Extract chart components like title, axes, legend."""
        components = {
            'title': {'detected': False, 'text': '', 'position': {}},
            'x_axis': {'detected': False, 'label': '', 'scale': []},
            'y_axis': {'detected': False, 'label': '', 'scale': []},
            'legend': {'detected': False, 'items': []},
            'annotations': []
        }
        
        try:
            # Extract text components
            text_lines = text_content.strip().split('\n')
            
            # Simple heuristics for component detection
            for line in text_lines:
                line = line.strip()
                if not line:
                    continue
                
                # Title detection (usually first line or contains chart-related words)
                if not components['title']['detected']:
                    title_indicators = ['chart', 'graph', 'plot', 'figure', 'analysis']
                    if any(indicator in line.lower() for indicator in title_indicators) or len(line) > 20:
                        components['title']['detected'] = True
                        components['title']['text'] = line
                
                # Axis label detection
                if any(word in line.lower() for word in ['axis', 'scale', 'range']):
                    if 'x' in line.lower() or 'horizontal' in line.lower():
                        components['x_axis']['detected'] = True
                        components['x_axis']['label'] = line
                    elif 'y' in line.lower() or 'vertical' in line.lower():
                        components['y_axis']['detected'] = True
                        components['y_axis']['label'] = line
                
                # Legend detection
                if any(word in line.lower() for word in ['legend', 'key', 'series']):
                    components['legend']['detected'] = True
                    components['legend']['items'].append(line)
                
                # Numeric values could be scale indicators
                if re.search(r'\d+\.?\d*', line):
                    # Could be scale values
                    numbers = re.findall(r'\d+\.?\d*', line)
                    if numbers:
                        # Add to both axes for now (more sophisticated logic could determine which axis)
                        components['x_axis']['scale'].extend(numbers)
                        components['y_axis']['scale'].extend(numbers)
            
            # Remove duplicates from scales
            components['x_axis']['scale'] = list(set(components['x_axis']['scale']))
            components['y_axis']['scale'] = list(set(components['y_axis']['scale']))
            
            return components
            
        except Exception as e:
            self.logger.error(f"Component extraction failed: {e}")
            return components
    
    def _extract_data_points(self, image: Image.Image, components: Dict, chart_type: Dict) -> List[Dict]:
        """Extract data points from the chart."""
        data_points = []
        
        try:
            detected_type = chart_type.get('detected_type', 'unknown')
            
            # Type-specific data extraction
            if detected_type == 'bar_chart':
                data_points = self._extract_bar_data(image, components)
            elif detected_type == 'line_chart':
                data_points = self._extract_line_data(image, components)
            elif detected_type == 'pie_chart':
                data_points = self._extract_pie_data(image, components)
            elif detected_type == 'scatter_plot':
                data_points = self._extract_scatter_data(image, components)
            elif detected_type == 'histogram':
                data_points = self._extract_histogram_data(image, components)
            elif detected_type == 'area_chart':
                data_points = self._extract_area_data(image, components)
            else:
                # Generic data extraction
                data_points = self._extract_generic_data(image, components)
            
            return data_points
            
        except Exception as e:
            self.logger.error(f"Data point extraction failed: {e}")
            return []
    
    def _extract_bar_data(self, image: Image.Image, components: Dict) -> List[Dict]:
        """Extract data from bar charts."""
        data_points = []
        
        try:
            if not OPENCV_AVAILABLE:
                return self._extract_generic_data(image, components)
            
            # Convert to OpenCV format
            img_array = np.array(image)
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            
            # Detect rectangular bars
            edges = cv2.Canny(gray, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            bars = []
            for contour in contours:
                area = cv2.contourArea(contour)
                if area < 500:  # Skip small contours
                    continue
                
                # Check if it's rectangular
                epsilon = 0.02 * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)
                
                if len(approx) == 4:
                    x, y, w, h = cv2.boundingRect(approx)
                    
                    # Check aspect ratio for bar-like shapes
                    aspect_ratio = w / h
                    if 0.2 <= aspect_ratio <= 5.0:
                        bars.append({
                            'x': x,
                            'y': y,
                            'width': w,
                            'height': h,
                            'area': area,
                            'aspect_ratio': aspect_ratio
                        })
            
            # Sort bars by position (left to right for vertical bars, top to bottom for horizontal)
            if bars:
                # Determine orientation
                avg_aspect = sum(bar['aspect_ratio'] for bar in bars) / len(bars)
                
                if avg_aspect > 1:  # Horizontal bars
                    bars.sort(key=lambda b: b['y'])
                    orientation = 'horizontal'
                else:  # Vertical bars
                    bars.sort(key=lambda b: b['x'])
                    orientation = 'vertical'
                
                # Convert to data points
                for i, bar in enumerate(bars):
                    if orientation == 'vertical':
                        value = bar['height']  # Height represents value
                        category = f"Category_{i+1}"
                    else:
                        value = bar['width']  # Width represents value
                        category = f"Category_{i+1}"
                    
                    data_points.append({
                        'category': category,
                        'value': value,
                        'position': {'x': bar['x'], 'y': bar['y']},
                        'dimensions': {'width': bar['width'], 'height': bar['height']},
                        'type': 'bar'
                    })
            
            return data_points
            
        except Exception as e:
            self.logger.error(f"Bar data extraction failed: {e}")
            return []
    
    def _extract_line_data(self, image: Image.Image, components: Dict) -> List[Dict]:
        """Extract data from line charts."""
        data_points = []
        
        try:
            if not OPENCV_AVAILABLE:
                return self._extract_generic_data(image, components)
            
            # Convert to OpenCV format
            img_array = np.array(image)
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            
            # Detect lines
            edges = cv2.Canny(gray, 50, 150)
            lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50, minLineLength=30, maxLineGap=10)
            
            if lines is not None:
                # Group lines into continuous segments
                line_segments = []
                for line in lines:
                    x1, y1, x2, y2 = line[0]
                    line_segments.append({
                        'start': (x1, y1),
                        'end': (x2, y2),
                        'length': ((x2-x1)**2 + (y2-y1)**2)**0.5,
                        'angle': np.arctan2(y2-y1, x2-x1)
                    })
                
                # Sort by x-coordinate for time series
                line_segments.sort(key=lambda l: l['start'][0])
                
                # Convert to data points
                for i, segment in enumerate(line_segments):
                    data_points.append({
                        'x': segment['start'][0],
                        'y': segment['start'][1],
                        'value': segment['start'][1],  # Y-coordinate as value
                        'type': 'line_point',
                        'segment_id': i
                    })
            
            return data_points
            
        except Exception as e:
            self.logger.error(f"Line data extraction failed: {e}")
            return []
    
    def _extract_pie_data(self, image: Image.Image, components: Dict) -> List[Dict]:
        """Extract data from pie charts."""
        data_points = []
        
        try:
            if not OPENCV_AVAILABLE:
                return self._extract_generic_data(image, components)
            
            # Convert to OpenCV format
            img_array = np.array(image)
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            
            # Detect circles (pie chart outline)
            circles = cv2.HoughCircles(
                gray,
                cv2.HOUGH_GRADIENT,
                dp=1,
                minDist=30,
                param1=50,
                param2=30,
                minRadius=50,
                maxRadius=200
            )
            
            if circles is not None:
                circles = np.round(circles[0, :]).astype("int")
                
                for (x, y, r) in circles:
                    # Analyze color segments within the circle
                    color_analysis = self._analyze_pie_segments(image, x, y, r)
                    
                    # Convert to data points
                    for i, segment in enumerate(color_analysis):
                        data_points.append({
                            'category': f"Segment_{i+1}",
                            'value': segment.get('percentage', 0),
                            'color': segment.get('color', 'unknown'),
                            'angle': segment.get('angle', 0),
                            'type': 'pie_segment'
                        })
            
            return data_points
            
        except Exception as e:
            self.logger.error(f"Pie data extraction failed: {e}")
            return []
    
    def _analyze_pie_segments(self, image: Image.Image, center_x: int, center_y: int, radius: int) -> List[Dict]:
        """Analyze pie chart segments."""
        segments = []
        
        try:
            # This is a simplified approach
            # A more sophisticated method would use edge detection and color analysis
            
            # Sample colors at regular intervals around the circle
            num_samples = 36  # Every 10 degrees
            angle_step = 2 * np.pi / num_samples
            
            colors_at_angles = []
            for i in range(num_samples):
                angle = i * angle_step
                sample_x = int(center_x + radius * 0.7 * np.cos(angle))
                sample_y = int(center_y + radius * 0.7 * np.sin(angle))
                
                # Ensure coordinates are within image bounds
                if 0 <= sample_x < image.width and 0 <= sample_y < image.height:
                    color = image.getpixel((sample_x, sample_y))
                    colors_at_angles.append({
                        'angle': angle,
                        'color': color,
                        'hex': f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}" if isinstance(color, tuple) else str(color)
                    })
            
            # Group similar colors into segments
            if colors_at_angles:
                # Simple grouping by color similarity
                current_segment = None
                
                for color_info in colors_at_angles:
                    if current_segment is None:
                        current_segment = {
                            'start_angle': color_info['angle'],
                            'end_angle': color_info['angle'],
                            'color': color_info['hex'],
                            'sample_count': 1
                        }
                    elif self._colors_similar(current_segment['color'], color_info['hex']):
                        current_segment['end_angle'] = color_info['angle']
                        current_segment['sample_count'] += 1
                    else:
                        # Finish current segment
                        angle_span = current_segment['end_angle'] - current_segment['start_angle']
                        if angle_span < 0:
                            angle_span += 2 * np.pi
                        
                        segments.append({
                            'color': current_segment['color'],
                            'angle': angle_span,
                            'percentage': (angle_span / (2 * np.pi)) * 100,
                            'sample_count': current_segment['sample_count']
                        })
                        
                        # Start new segment
                        current_segment = {
                            'start_angle': color_info['angle'],
                            'end_angle': color_info['angle'],
                            'color': color_info['hex'],
                            'sample_count': 1
                        }
                
                # Don't forget the last segment
                if current_segment:
                    angle_span = current_segment['end_angle'] - current_segment['start_angle']
                    if angle_span < 0:
                        angle_span += 2 * np.pi
                    
                    segments.append({
                        'color': current_segment['color'],
                        'angle': angle_span,
                        'percentage': (angle_span / (2 * np.pi)) * 100,
                        'sample_count': current_segment['sample_count']
                    })
            
            return segments
            
        except Exception as e:
            self.logger.error(f"Pie segment analysis failed: {e}")
            return []
    
    def _colors_similar(self, color1: str, color2: str, threshold: int = 50) -> bool:
        """Check if two hex colors are similar."""
        try:
            # Convert hex to RGB
            def hex_to_rgb(hex_color):
                hex_color = hex_color.lstrip('#')
                return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            
            rgb1 = hex_to_rgb(color1)
            rgb2 = hex_to_rgb(color2)
            
            # Calculate Euclidean distance
            distance = sum((a - b) ** 2 for a, b in zip(rgb1, rgb2)) ** 0.5
            
            return distance < threshold
            
        except Exception as e:
            return False
    
    def _extract_scatter_data(self, image: Image.Image, components: Dict) -> List[Dict]:
        """Extract data from scatter plots."""
        data_points = []
        
        try:
            if not OPENCV_AVAILABLE:
                return self._extract_generic_data(image, components)
            
            # Convert to OpenCV format
            img_array = np.array(image)
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            
            # Detect scattered points using blob detection
            params = cv2.SimpleBlobDetector_Params()
            
            # Filter by Area
            params.filterByArea = True
            params.minArea = 10
            params.maxArea = 100
            
            # Filter by Circularity
            params.filterByCircularity = True
            params.minCircularity = 0.5
            
            # Create detector
            detector = cv2.SimpleBlobDetector_create(params)
            
            # Detect blobs
            keypoints = detector.detect(gray)
            
            # Convert to data points
            for i, keypoint in enumerate(keypoints):
                data_points.append({
                    'x': keypoint.pt[0],
                    'y': keypoint.pt[1],
                    'size': keypoint.size,
                    'type': 'scatter_point',
                    'point_id': i
                })
            
            return data_points
            
        except Exception as e:
            self.logger.error(f"Scatter data extraction failed: {e}")
            return []
    
    def _extract_histogram_data(self, image: Image.Image, components: Dict) -> List[Dict]:
        """Extract data from histograms."""
        # Histograms are similar to bar charts but with continuous bins
        return self._extract_bar_data(image, components)
    
    def _extract_area_data(self, image: Image.Image, components: Dict) -> List[Dict]:
        """Extract data from area charts."""
        # Area charts are similar to line charts but with filled areas
        return self._extract_line_data(image, components)
    
    def _extract_generic_data(self, image: Image.Image, components: Dict) -> List[Dict]:
        """Generic data extraction for unknown chart types."""
        data_points = []
        
        try:
            # Basic approach: look for numeric values in components
            x_scale = components.get('x_axis', {}).get('scale', [])
            y_scale = components.get('y_axis', {}).get('scale', [])
            
            # Create generic data points from scale values
            for i, x_val in enumerate(x_scale):
                for j, y_val in enumerate(y_scale):
                    if i < len(y_scale) and j < len(x_scale):  # Avoid duplicate combinations
                        data_points.append({
                            'x': float(x_val) if x_val.replace('.', '').isdigit() else i,
                            'y': float(y_val) if y_val.replace('.', '').isdigit() else j,
                            'type': 'generic_point',
                            'source': 'scale_values'
                        })
            
            return data_points
            
        except Exception as e:
            self.logger.error(f"Generic data extraction failed: {e}")
            return []
    
    def _analyze_chart_data(self, data_points: List[Dict], chart_type: Dict) -> Dict:
        """Analyze extracted chart data for trends and patterns."""
        analysis = {
            'statistical_summary': {},
            'trends': {},
            'patterns': {},
            'anomalies': []
        }
        
        try:
            if not data_points:
                return analysis
            
            # Extract numeric values
            values = []
            for point in data_points:
                if 'value' in point:
                    try:
                        values.append(float(point['value']))
                    except (ValueError, TypeError):
                        pass
                elif 'y' in point:
                    try:
                        values.append(float(point['y']))
                    except (ValueError, TypeError):
                        pass
            
            # Statistical summary
            if values:
                analysis['statistical_summary'] = {
                    'count': len(values),
                    'min': min(values),
                    'max': max(values),
                    'mean': sum(values) / len(values),
                    'median': sorted(values)[len(values) // 2],
                    'range': max(values) - min(values),
                    'std_dev': (sum((x - sum(values) / len(values)) ** 2 for x in values) / len(values)) ** 0.5
                }
            
            # Trend analysis
            if len(values) > 1:
                # Simple trend detection
                increasing = sum(1 for i in range(1, len(values)) if values[i] > values[i-1])
                decreasing = sum(1 for i in range(1, len(values)) if values[i] < values[i-1])
                
                if increasing > decreasing:
                    trend = 'increasing'
                elif decreasing > increasing:
                    trend = 'decreasing'
                else:
                    trend = 'stable'
                
                analysis['trends'] = {
                    'overall_trend': trend,
                    'increasing_points': increasing,
                    'decreasing_points': decreasing,
                    'stable_points': len(values) - 1 - increasing - decreasing
                }
            
            # Pattern detection
            analysis['patterns'] = self._detect_patterns(values)
            
            # Anomaly detection (simple approach)
            if len(values) > 3:
                mean_val = sum(values) / len(values)
                std_val = (sum((x - mean_val) ** 2 for x in values) / len(values)) ** 0.5
                
                for i, val in enumerate(values):
                    if abs(val - mean_val) > 2 * std_val:  # 2 standard deviations
                        analysis['anomalies'].append({
                            'index': i,
                            'value': val,
                            'type': 'outlier',
                            'deviation': abs(val - mean_val) / std_val
                        })
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Chart data analysis failed: {e}")
            return analysis
    
    def _detect_patterns(self, values: List[float]) -> Dict:
        """Detect patterns in data values."""
        patterns = {
            'cyclic': False,
            'seasonal': False,
            'linear': False,
            'exponential': False
        }
        
        try:
            if len(values) < 4:
                return patterns
            
            # Linear pattern detection
            # Check if values follow a roughly linear trend
            n = len(values)
            x_vals = list(range(n))
            
            # Calculate correlation coefficient
            mean_x = sum(x_vals) / n
            mean_y = sum(values) / n
            
            numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(x_vals, values))
            denominator = (sum((x - mean_x) ** 2 for x in x_vals) * sum((y - mean_y) ** 2 for y in values)) ** 0.5
            
            if denominator != 0:
                correlation = abs(numerator / denominator)
                patterns['linear'] = correlation > 0.8
            
            # Cyclic pattern detection (very simple)
            # Look for repeating patterns
            if len(values) >= 6:
                for period in range(2, len(values) // 2):
                    matches = 0
                    for i in range(period, len(values)):
                        if abs(values[i] - values[i - period]) < 0.1 * (max(values) - min(values)):
                            matches += 1
                    
                    if matches / (len(values) - period) > 0.7:
                        patterns['cyclic'] = True
                        break
            
            return patterns
            
        except Exception as e:
            self.logger.error(f"Pattern detection failed: {e}")
            return patterns
    
    def _calculate_chart_complexity(self, components: Dict, data_points: List[Dict]) -> float:
        """Calculate complexity score for the chart."""
        try:
            complexity = 0
            
            # Base complexity on data points
            complexity += len(data_points) * 2
            
            # Add complexity for components
            if components.get('title', {}).get('detected'):
                complexity += 5
            if components.get('x_axis', {}).get('detected'):
                complexity += 5
            if components.get('y_axis', {}).get('detected'):
                complexity += 5
            if components.get('legend', {}).get('detected'):
                complexity += 10
            
            # Add complexity for scale values
            x_scale_count = len(components.get('x_axis', {}).get('scale', []))
            y_scale_count = len(components.get('y_axis', {}).get('scale', []))
            complexity += (x_scale_count + y_scale_count) * 1
            
            # Normalize to 0-100 scale
            max_complexity = 100  # Arbitrary maximum
            return min(100, (complexity / max_complexity) * 100)
            
        except Exception as e:
            self.logger.error(f"Complexity calculation failed: {e}")
            return 50.0
    
    def _generate_chart_description(self, chart_type: Dict, components: Dict, data_points: List[Dict], analysis: Dict) -> Dict:
        """Generate comprehensive chart description."""
        try:
            detected_type = chart_type.get('detected_type', 'unknown')
            confidence = chart_type.get('confidence', 0)
            
            descriptions = {}
            
            # Brief description
            data_count = len(data_points)
            descriptions['brief'] = f"A {detected_type.replace('_', ' ')} with {data_count} data points."
            
            # Detailed description
            details = []
            details.append(f"This is a {detected_type.replace('_', ' ')}")
            details.append(f"containing {data_count} data points")
            
            # Add component information
            if components.get('title', {}).get('detected'):
                details.append(f"with title '{components['title']['text']}'")
            
            if components.get('legend', {}).get('detected'):
                legend_items = len(components['legend']['items'])
                details.append(f"including a legend with {legend_items} items")
            
            # Add statistical information
            stats = analysis.get('statistical_summary', {})
            if stats:
                min_val = stats.get('min', 0)
                max_val = stats.get('max', 0)
                details.append(f"with values ranging from {min_val:.2f} to {max_val:.2f}")
            
            descriptions['detailed'] = '. '.join(details) + '.'
            
            # Comprehensive description
            comprehensive = []
            comprehensive.append(f"Chart Analysis: {detected_type.replace('_', ' ')}")
            comprehensive.append(f"Type confidence: {confidence:.1f}%")
            comprehensive.append(f"Data points: {data_count}")
            
            # Statistical summary
            if stats:
                comprehensive.append(f"Statistical summary: mean={stats.get('mean', 0):.2f}, std={stats.get('std_dev', 0):.2f}")
            
            # Trend information
            trends = analysis.get('trends', {})
            if trends.get('overall_trend'):
                comprehensive.append(f"Overall trend: {trends['overall_trend']}")
            
            # Pattern information
            patterns = analysis.get('patterns', {})
            pattern_types = [k for k, v in patterns.items() if v]
            if pattern_types:
                comprehensive.append(f"Detected patterns: {', '.join(pattern_types)}")
            
            # Anomaly information
            anomalies = analysis.get('anomalies', [])
            if anomalies:
                comprehensive.append(f"Anomalies detected: {len(anomalies)} outliers")
            
            descriptions['comprehensive'] = '. '.join(comprehensive) + '.'
            
            return descriptions
            
        except Exception as e:
            self.logger.error(f"Description generation failed: {e}")
            return {
                'brief': 'Chart analysis failed',
                'detailed': f'Unable to generate description: {str(e)}',
                'comprehensive': f'Description generation error: {str(e)}'
            }
    
    def _enhance_chart_analysis(self, extraction_result: Dict, area_data: Dict) -> Dict:
        """Enhance chart analysis with additional processing."""
        if not extraction_result.get('success'):
            return extraction_result
        
        try:
            # Add contextual information
            context = {
                'document_context': {
                    'page_number': area_data.get('page', 1),
                    'area_type': area_data.get('type', 'CHART'),
                    'processing_notes': area_data.get('special_notes', ''),
                    'high_priority': area_data.get('high_priority', False)
                },
                'chart_metrics': self._calculate_chart_metrics(extraction_result),
                'visualization_recommendations': self._generate_visualization_recommendations(extraction_result)
            }
            
            # Add context to result
            extraction_result['context'] = context
            
            # Generate output formats
            extraction_result['output_formats'] = self._generate_output_formats(extraction_result)
            
            return extraction_result
            
        except Exception as e:
            self.logger.error(f"Chart enhancement failed: {e}")
            extraction_result['enhancement_error'] = str(e)
            return extraction_result
    
    def _calculate_chart_metrics(self, extraction_result: Dict) -> Dict:
        """Calculate metrics for the chart."""
        metrics = {
            'data_quality': 0.0,
            'visualization_clarity': 0.0,
            'information_density': 0.0,
            'accessibility_score': 0.0
        }
        
        try:
            content = extraction_result.get('content', {})
            data_points = content.get('data_points', [])
            components = content.get('components', {})
            
            # Data quality
            if data_points:
                metrics['data_quality'] = 85.0  # Base score
                
                # Check for missing values
                missing_values = sum(1 for point in data_points if not point.get('value'))
                if missing_values > 0:
                    metrics['data_quality'] -= (missing_values / len(data_points)) * 20
            
            # Visualization clarity
            clarity_score = 70.0  # Base score
            
            if components.get('title', {}).get('detected'):
                clarity_score += 10
            if components.get('x_axis', {}).get('detected'):
                clarity_score += 5
            if components.get('y_axis', {}).get('detected'):
                clarity_score += 5
            if components.get('legend', {}).get('detected'):
                clarity_score += 10
            
            metrics['visualization_clarity'] = min(100, clarity_score)
            
            # Information density
            if data_points:
                metrics['information_density'] = min(100, len(data_points) * 2)
            
            # Accessibility score
            accessibility = 60.0  # Base score
            if components.get('title', {}).get('detected'):
                accessibility += 20
            if components.get('legend', {}).get('detected'):
                accessibility += 20
            
            metrics['accessibility_score'] = min(100, accessibility)
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Chart metrics calculation failed: {e}")
            return metrics
    
    def _generate_visualization_recommendations(self, extraction_result: Dict) -> List[str]:
        """Generate recommendations for chart visualization."""
        recommendations = []
        
        try:
            content = extraction_result.get('content', {})
            chart_type = content.get('chart_type', {})
            components = content.get('components', {})
            data_points = content.get('data_points', [])
            
            # Type-specific recommendations
            detected_type = chart_type.get('detected_type', 'unknown')
            confidence = chart_type.get('confidence', 0)
            
            if confidence < 70:
                recommendations.append("Consider manual verification of chart type")
            
            # Component recommendations
            if not components.get('title', {}).get('detected'):
                recommendations.append("Add a descriptive title for better accessibility")
            
            if not components.get('legend', {}).get('detected') and len(data_points) > 1:
                recommendations.append("Consider adding a legend for data series identification")
            
            # Data recommendations
            if len(data_points) > 20:
                recommendations.append("Large dataset - consider data aggregation or filtering")
            
            if len(data_points) < 3:
                recommendations.append("Limited data points - verify all data is captured")
            
            # Type-specific recommendations
            if detected_type == 'pie_chart' and len(data_points) > 7:
                recommendations.append("Pie chart with many segments - consider using bar chart instead")
            
            if detected_type == 'line_chart':
                recommendations.append("For line charts, ensure time series data is properly ordered")
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Visualization recommendations failed: {e}")
            return ['Recommendations unavailable due to error']
    
    def _generate_output_formats(self, extraction_result: Dict) -> Dict:
        """Generate chart analysis in multiple output formats."""
        formats = {}
        
        try:
            content = extraction_result.get('content', {})
            data_points = content.get('data_points', [])
            
            # JSON format (default)
            formats['json'] = content
            
            # CSV format
            if data_points:
                csv_lines = []
                
                # Header
                if data_points[0].get('category'):
                    csv_lines.append('Category,Value')
                    for point in data_points:
                        category = point.get('category', 'Unknown')
                        value = point.get('value', 0)
                        csv_lines.append(f'"{category}",{value}')
                elif data_points[0].get('x') is not None:
                    csv_lines.append('X,Y')
                    for point in data_points:
                        x = point.get('x', 0)
                        y = point.get('y', 0)
                        csv_lines.append(f'{x},{y}')
                
                formats['csv'] = '\n'.join(csv_lines)
            
            # Markdown format
            formats['markdown'] = self._generate_markdown_format(content)
            
            # Matplotlib code (basic)
            formats['matplotlib'] = self._generate_matplotlib_code(content)
            
            # Plotly code (basic)
            formats['plotly'] = self._generate_plotly_code(content)
            
        except Exception as e:
            self.logger.error(f"Output format generation failed: {e}")
            formats['error'] = str(e)
        
        return formats
    
    def _generate_markdown_format(self, content: Dict) -> str:
        """Generate Markdown format for chart documentation."""
        try:
            lines = []
            
            # Title
            chart_type = content.get('chart_type', {})
            detected_type = chart_type.get('detected_type', 'unknown')
            lines.append(f"# {detected_type.replace('_', ' ').title()} Analysis")
            lines.append("")
            
            # Description
            description = content.get('description', {})
            lines.append(f"**Description:** {description.get('detailed', 'No description available')}")
            lines.append("")
            
            # Data points
            data_points = content.get('data_points', [])
            if data_points:
                lines.append(f"## Data Points ({len(data_points)})")
                lines.append("")
                
                # Table format
                if data_points[0].get('category'):
                    lines.append("| Category | Value |")
                    lines.append("|----------|-------|")
                    for point in data_points:
                        category = point.get('category', 'Unknown')
                        value = point.get('value', 0)
                        lines.append(f"| {category} | {value} |")
                elif data_points[0].get('x') is not None:
                    lines.append("| X | Y |")
                    lines.append("|---|---|")
                    for point in data_points:
                        x = point.get('x', 0)
                        y = point.get('y', 0)
                        lines.append(f"| {x} | {y} |")
                
                lines.append("")
            
            # Analysis
            analysis = content.get('analysis', {})
            stats = analysis.get('statistical_summary', {})
            if stats:
                lines.append("## Statistical Summary")
                lines.append("")
                lines.append(f"- Count: {stats.get('count', 0)}")
                lines.append(f"- Mean: {stats.get('mean', 0):.2f}")
                lines.append(f"- Min: {stats.get('min', 0):.2f}")
                lines.append(f"- Max: {stats.get('max', 0):.2f}")
                lines.append("")
            
            return '\n'.join(lines)
            
        except Exception as e:
            return f"Markdown generation failed: {str(e)}"
    
    def _generate_matplotlib_code(self, content: Dict) -> str:
        """Generate basic Matplotlib code to recreate the chart."""
        try:
            chart_type = content.get('chart_type', {})
            detected_type = chart_type.get('detected_type', 'unknown')
            data_points = content.get('data_points', [])
            
            if not data_points:
                return "# No data points available"
            
            lines = []
            lines.append("import matplotlib.pyplot as plt")
            lines.append("import numpy as np")
            lines.append("")
            
            # Data preparation
            if data_points[0].get('category'):
                categories = [point.get('category', f'Cat_{i}') for i, point in enumerate(data_points)]
                values = [point.get('value', 0) for point in data_points]
                
                lines.append(f"categories = {categories}")
                lines.append(f"values = {values}")
            elif data_points[0].get('x') is not None:
                x_values = [point.get('x', 0) for point in data_points]
                y_values = [point.get('y', 0) for point in data_points]
                
                lines.append(f"x_values = {x_values}")
                lines.append(f"y_values = {y_values}")
            
            lines.append("")
            
            # Plot type
            if detected_type == 'bar_chart':
                lines.append("plt.bar(categories, values)")
            elif detected_type == 'line_chart':
                lines.append("plt.plot(x_values, y_values)")
            elif detected_type == 'scatter_plot':
                lines.append("plt.scatter(x_values, y_values)")
            elif detected_type == 'pie_chart':
                lines.append("plt.pie(values, labels=categories)")
            else:
                lines.append("plt.plot(x_values, y_values)  # Default line plot")
            
            # Labels and title
            components = content.get('components', {})
            if components.get('title', {}).get('detected'):
                title = components['title']['text']
                lines.append(f"plt.title('{title}')")
            
            lines.append("plt.show()")
            
            return '\n'.join(lines)
            
        except Exception as e:
            return f"# Matplotlib code generation failed: {str(e)}"
    
    def _generate_plotly_code(self, content: Dict) -> str:
        """Generate basic Plotly code to recreate the chart."""
        try:
            chart_type = content.get('chart_type', {})
            detected_type = chart_type.get('detected_type', 'unknown')
            data_points = content.get('data_points', [])
            
            if not data_points:
                return "# No data points available"
            
            lines = []
            lines.append("import plotly.graph_objects as go")
            lines.append("import plotly.express as px")
            lines.append("")
            
            # Data preparation
            if data_points[0].get('category'):
                categories = [point.get('category', f'Cat_{i}') for i, point in enumerate(data_points)]
                values = [point.get('value', 0) for point in data_points]
                
                if detected_type == 'bar_chart':
                    lines.append("fig = go.Figure(data=[go.Bar(x=categories, y=values)])")
                elif detected_type == 'pie_chart':
                    lines.append("fig = go.Figure(data=[go.Pie(labels=categories, values=values)])")
                else:
                    lines.append("fig = go.Figure(data=[go.Scatter(x=categories, y=values)])")
            
            elif data_points[0].get('x') is not None:
                x_values = [point.get('x', 0) for point in data_points]
                y_values = [point.get('y', 0) for point in data_points]
                
                if detected_type == 'line_chart':
                    lines.append("fig = go.Figure(data=[go.Scatter(x=x_values, y=y_values, mode='lines')])")
                elif detected_type == 'scatter_plot':
                    lines.append("fig = go.Figure(data=[go.Scatter(x=x_values, y=y_values, mode='markers')])")
                else:
                    lines.append("fig = go.Figure(data=[go.Scatter(x=x_values, y=y_values)])")
            
            # Title
            components = content.get('components', {})
            if components.get('title', {}).get('detected'):
                title = components['title']['text']
                lines.append(f"fig.update_layout(title='{title}')")
            
            lines.append("fig.show()")
            
            return '\n'.join(lines)
            
        except Exception as e:
            return f"# Plotly code generation failed: {str(e)}"
    
    def validate_extraction(self, extracted_content: Dict) -> Dict:
        """Validate chart extraction results."""
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
            if not content.get('data_points'):
                validation['issues'].append('No data points extracted')
            
            if not content.get('chart_type'):
                validation['issues'].append('Chart type not detected')
            
            # Check data quality
            data_points = content.get('data_points', [])
            if len(data_points) < 2:
                validation['issues'].append('Insufficient data points for meaningful analysis')
            
            # Check type confidence
            chart_type = content.get('chart_type', {})
            type_confidence = chart_type.get('confidence', 0)
            
            if type_confidence < 50:
                validation['issues'].append('Low confidence in chart type detection')
            
            # Calculate validation score
            validation['confidence'] = extracted_content.get('confidence_score', 0)
            validation['quality_score'] = type_confidence
            validation['is_valid'] = len(validation['issues']) == 0 and type_confidence > 30
            
        except Exception as e:
            validation['issues'].append(f'Validation error: {str(e)}')
        
        return validation
    
    def get_supported_formats(self) -> List[str]:
        """Get supported output formats."""
        return ['json', 'csv', 'matplotlib', 'plotly', 'markdown']