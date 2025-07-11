#!/usr/bin/env python3
"""
Diagram processing toolset for technical drawings, flowcharts, and schematic diagrams.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
import time
import re
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont
import numpy as np

from .base_toolset import BaseToolset
from ...config.settings import Settings

# Optional libraries for advanced diagram analysis
try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    cv2 = None

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    nx = None


class DiagramToolset(BaseToolset):
    """Advanced diagram processing and analysis toolset."""
    
    def __init__(self, settings: Settings):
        super().__init__(settings)
        
        # Diagram-specific processing options
        self.processing_options.update({
            'diagram_type_detection': True,
            'element_extraction': True,
            'relationship_analysis': True,
            'text_extraction': True,
            'flow_analysis': True,
            'structure_analysis': True,
            'output_formats': ['json', 'graphml', 'dot', 'markdown']
        })
        
        # Diagram analysis capabilities
        self.analysis_capabilities = {
            'shape_detection': OPENCV_AVAILABLE,
            'graph_analysis': NETWORKX_AVAILABLE,
            'text_extraction': True,
            'flow_detection': True,
            'basic_analysis': True
        }
        
        # Diagram type patterns
        self.diagram_patterns = {
            'flowchart': {
                'keywords': ['start', 'end', 'process', 'decision', 'input', 'output'],
                'shapes': ['rectangle', 'diamond', 'oval', 'parallelogram'],
                'connectors': ['arrow', 'line', 'flow']
            },
            'organizational': {
                'keywords': ['manager', 'director', 'team', 'department', 'position'],
                'shapes': ['rectangle', 'box'],
                'connectors': ['line', 'hierarchy']
            },
            'technical': {
                'keywords': ['component', 'module', 'system', 'interface', 'connection'],
                'shapes': ['rectangle', 'circle', 'triangle'],
                'connectors': ['line', 'arrow', 'wire']
            },
            'network': {
                'keywords': ['node', 'server', 'client', 'router', 'switch', 'network'],
                'shapes': ['circle', 'rectangle', 'cloud'],
                'connectors': ['line', 'connection']
            }
        }
        
        self.logger.info(f"Diagram toolset initialized with capabilities: {self.analysis_capabilities}")
    
    def process_area(self, area_data: Dict, pdf_document: fitz.Document) -> Dict:
        """Process a diagram area with comprehensive analysis."""
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
            
            # Extract diagram content
            extraction_result = self.extract_content(area_data, pdf_document)
            
            # Enhance with additional analysis
            enhanced_result = self._enhance_diagram_analysis(extraction_result, area_data)
            
            # Postprocessing
            final_result = self.postprocess_result(enhanced_result, area_data)
            
            # Update timing
            self.metrics['processing_time'] += time.time() - start_time
            
            return final_result
            
        except Exception as e:
            self.logger.error(f"Diagram processing failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'content': None,
                'processing_time': time.time() - start_time
            }
    
    def extract_content(self, area_data: Dict, pdf_document: fitz.Document) -> Dict:
        """Extract and analyze diagram content."""
        try:
            # Get preprocessed image
            preprocessed = self.preprocess_area(area_data, pdf_document)
            if not preprocessed['preprocessing_success']:
                return {
                    'success': False,
                    'error': 'Diagram preprocessing failed',
                    'content': None
                }
            
            image = preprocessed['image']
            text_content = preprocessed['text_content']
            
            # Diagram type detection
            diagram_type = self._detect_diagram_type(image, text_content)
            
            # Element extraction
            elements = self._extract_diagram_elements(image, text_content)
            
            # Relationship analysis
            relationships = self._analyze_relationships(elements, image)
            
            # Flow analysis
            flow_analysis = self._analyze_flow(elements, relationships)
            
            # Structure analysis
            structure = self._analyze_structure(elements, relationships)
            
            # Generate description
            description = self._generate_diagram_description(diagram_type, elements, relationships, flow_analysis)
            
            return {
                'success': True,
                'content': {
                    'diagram_type': diagram_type,
                    'elements': elements,
                    'relationships': relationships,
                    'flow_analysis': flow_analysis,
                    'structure': structure,
                    'description': description
                },
                'raw_content': text_content,
                'structured_content': {
                    'type': 'diagram',
                    'subtype': diagram_type['detected_type'],
                    'elements': elements,
                    'connections': relationships,
                    'metadata': {
                        'element_count': len(elements),
                        'connection_count': len(relationships),
                        'complexity_score': self._calculate_complexity(elements, relationships)
                    }
                },
                'confidence_score': diagram_type['confidence']
            }
            
        except Exception as e:
            self.logger.error(f"Diagram content extraction failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'content': None
            }
    
    def _detect_diagram_type(self, image: Image.Image, text_content: str) -> Dict:
        """Detect the type of diagram."""
        type_scores = {}
        
        try:
            # Analyze text content for keywords
            text_lower = text_content.lower()
            
            for diagram_type, patterns in self.diagram_patterns.items():
                score = 0
                
                # Check for keywords
                keyword_matches = 0
                for keyword in patterns['keywords']:
                    if keyword in text_lower:
                        keyword_matches += 1
                
                score += keyword_matches * 10
                
                # Check for shape indicators in text
                for shape in patterns['shapes']:
                    if shape in text_lower:
                        score += 5
                
                # Check for connector indicators
                for connector in patterns['connectors']:
                    if connector in text_lower:
                        score += 3
                
                type_scores[diagram_type] = score
            
            # Visual analysis for additional clues
            visual_analysis = self._analyze_visual_patterns(image)
            
            # Adjust scores based on visual analysis
            for diagram_type, visual_score in visual_analysis.items():
                if diagram_type in type_scores:
                    type_scores[diagram_type] += visual_score
            
            # Determine best match
            if type_scores:
                best_type = max(type_scores, key=type_scores.get)
                confidence = min(type_scores[best_type] / 20.0 * 100, 100)
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
            self.logger.error(f"Diagram type detection failed: {e}")
            return {
                'detected_type': 'unknown',
                'confidence': 0,
                'error': str(e)
            }
    
    def _analyze_visual_patterns(self, image: Image.Image) -> Dict:
        """Analyze visual patterns in the diagram."""
        visual_scores = {
            'flowchart': 0,
            'organizational': 0,
            'technical': 0,
            'network': 0
        }
        
        try:
            if not OPENCV_AVAILABLE:
                return visual_scores
            
            # Convert to OpenCV format
            img_array = np.array(image)
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            
            # Detect shapes
            shapes = self._detect_shapes(gray)
            
            # Score based on shape patterns
            if shapes.get('rectangles', 0) > 3:
                visual_scores['flowchart'] += 10
                visual_scores['organizational'] += 8
                visual_scores['technical'] += 6
            
            if shapes.get('circles', 0) > 2:
                visual_scores['network'] += 10
                visual_scores['flowchart'] += 5
            
            if shapes.get('diamonds', 0) > 0:
                visual_scores['flowchart'] += 15
            
            # Detect lines/arrows
            lines = self._detect_lines(gray)
            if lines > 5:
                visual_scores['flowchart'] += 8
                visual_scores['network'] += 6
                visual_scores['technical'] += 5
            
            # Hierarchical patterns
            if self._detect_hierarchical_pattern(gray):
                visual_scores['organizational'] += 15
            
            return visual_scores
            
        except Exception as e:
            self.logger.error(f"Visual pattern analysis failed: {e}")
            return visual_scores
    
    def _detect_shapes(self, gray_image) -> Dict:
        """Detect basic shapes in the diagram."""
        shapes = {
            'rectangles': 0,
            'circles': 0,
            'diamonds': 0,
            'triangles': 0
        }
        
        try:
            if not OPENCV_AVAILABLE:
                return shapes
            
            # Edge detection
            edges = cv2.Canny(gray_image, 50, 150)
            
            # Find contours
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                # Filter small contours
                if cv2.contourArea(contour) < 500:
                    continue
                
                # Approximate contour
                epsilon = 0.02 * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)
                
                # Classify shape based on number of vertices
                if len(approx) == 3:
                    shapes['triangles'] += 1
                elif len(approx) == 4:
                    # Check if it's a square/rectangle or diamond
                    x, y, w, h = cv2.boundingRect(approx)
                    aspect_ratio = w / h
                    
                    if 0.8 <= aspect_ratio <= 1.2:
                        # Could be diamond, check orientation
                        if self._is_diamond_orientation(approx):
                            shapes['diamonds'] += 1
                        else:
                            shapes['rectangles'] += 1
                    else:
                        shapes['rectangles'] += 1
                elif len(approx) > 6:
                    # Likely a circle
                    shapes['circles'] += 1
            
            return shapes
            
        except Exception as e:
            self.logger.error(f"Shape detection failed: {e}")
            return shapes
    
    def _is_diamond_orientation(self, approx) -> bool:
        """Check if a 4-sided shape is diamond-oriented."""
        try:
            # Get the bounding box
            x, y, w, h = cv2.boundingRect(approx)
            
            # Check if any vertex is at the center of the bounding box edges
            center_x, center_y = x + w//2, y + h//2
            
            for point in approx:
                px, py = point[0]
                # Check if point is near the center of any edge
                if (abs(px - center_x) < 10 and (abs(py - y) < 10 or abs(py - (y + h)) < 10)) or \
                   (abs(py - center_y) < 10 and (abs(px - x) < 10 or abs(px - (x + w)) < 10)):
                    return True
            
            return False
            
        except Exception as e:
            return False
    
    def _detect_lines(self, gray_image) -> int:
        """Detect lines in the diagram."""
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
    
    def _detect_hierarchical_pattern(self, gray_image) -> bool:
        """Detect hierarchical organizational patterns."""
        try:
            if not OPENCV_AVAILABLE:
                return False
            
            # This is a simplified heuristic
            # Look for horizontal alignment and vertical connections
            height, width = gray_image.shape
            
            # Divide image into horizontal bands
            bands = 3
            band_height = height // bands
            
            elements_per_band = []
            for i in range(bands):
                band = gray_image[i*band_height:(i+1)*band_height, :]
                contours, _ = cv2.findContours(band, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                # Count significant contours
                significant_contours = [c for c in contours if cv2.contourArea(c) > 200]
                elements_per_band.append(len(significant_contours))
            
            # Check for hierarchical pattern (fewer elements at top)
            if len(elements_per_band) >= 2:
                return elements_per_band[0] < elements_per_band[-1]
            
            return False
            
        except Exception as e:
            self.logger.error(f"Hierarchical pattern detection failed: {e}")
            return False
    
    def _extract_diagram_elements(self, image: Image.Image, text_content: str) -> List[Dict]:
        """Extract individual elements from the diagram."""
        elements = []
        
        try:
            # Extract text elements
            text_elements = self._extract_text_elements(text_content)
            
            # Extract visual elements
            visual_elements = self._extract_visual_elements(image)
            
            # Combine and correlate elements
            element_id = 0
            
            # Add text elements
            for text_elem in text_elements:
                elements.append({
                    'id': f"text_{element_id}",
                    'type': 'text',
                    'content': text_elem['text'],
                    'position': text_elem.get('position', {}),
                    'properties': {
                        'word_count': len(text_elem['text'].split()),
                        'is_label': self._is_label(text_elem['text']),
                        'is_title': self._is_title(text_elem['text'])
                    }
                })
                element_id += 1
            
            # Add visual elements
            for visual_elem in visual_elements:
                elements.append({
                    'id': f"visual_{element_id}",
                    'type': 'visual',
                    'shape': visual_elem['shape'],
                    'position': visual_elem.get('position', {}),
                    'properties': {
                        'area': visual_elem.get('area', 0),
                        'color': visual_elem.get('color', 'unknown'),
                        'is_connector': visual_elem.get('is_connector', False)
                    }
                })
                element_id += 1
            
            return elements
            
        except Exception as e:
            self.logger.error(f"Element extraction failed: {e}")
            return []
    
    def _extract_text_elements(self, text_content: str) -> List[Dict]:
        """Extract text elements from the diagram."""
        elements = []
        
        try:
            # Split text into meaningful chunks
            lines = text_content.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Skip very short or very long lines (likely noise)
                if len(line) < 2 or len(line) > 100:
                    continue
                
                elements.append({
                    'text': line,
                    'position': {},  # Position would need OCR with coordinates
                    'length': len(line),
                    'word_count': len(line.split())
                })
            
            return elements
            
        except Exception as e:
            self.logger.error(f"Text element extraction failed: {e}")
            return []
    
    def _extract_visual_elements(self, image: Image.Image) -> List[Dict]:
        """Extract visual elements from the diagram."""
        elements = []
        
        try:
            if not OPENCV_AVAILABLE:
                return elements
            
            img_array = np.array(image)
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            
            # Detect shapes
            shapes = self._detect_shapes(gray)
            
            # Find contours for detailed analysis
            edges = cv2.Canny(gray, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                if cv2.contourArea(contour) < 200:
                    continue
                
                # Get bounding rectangle
                x, y, w, h = cv2.boundingRect(contour)
                
                # Determine shape type
                epsilon = 0.02 * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)
                
                if len(approx) == 3:
                    shape_type = 'triangle'
                elif len(approx) == 4:
                    if self._is_diamond_orientation(approx):
                        shape_type = 'diamond'
                    else:
                        shape_type = 'rectangle'
                elif len(approx) > 6:
                    shape_type = 'circle'
                else:
                    shape_type = 'polygon'
                
                # Check if it's a connector (line-like)
                aspect_ratio = w / h if h > 0 else 0
                is_connector = aspect_ratio > 5 or aspect_ratio < 0.2
                
                elements.append({
                    'shape': shape_type,
                    'position': {'x': x, 'y': y, 'width': w, 'height': h},
                    'area': cv2.contourArea(contour),
                    'is_connector': is_connector,
                    'vertices': len(approx)
                })
            
            return elements
            
        except Exception as e:
            self.logger.error(f"Visual element extraction failed: {e}")
            return []
    
    def _is_label(self, text: str) -> bool:
        """Determine if text is likely a label."""
        # Short, descriptive text
        return len(text.split()) <= 3 and len(text) <= 20
    
    def _is_title(self, text: str) -> bool:
        """Determine if text is likely a title."""
        # Check for title indicators
        title_indicators = ['diagram', 'flowchart', 'chart', 'process', 'system']
        text_lower = text.lower()
        
        return any(indicator in text_lower for indicator in title_indicators)
    
    def _analyze_relationships(self, elements: List[Dict], image: Image.Image) -> List[Dict]:
        """Analyze relationships between diagram elements."""
        relationships = []
        
        try:
            # Find potential connections based on proximity and visual cues
            visual_elements = [e for e in elements if e['type'] == 'visual']
            connectors = [e for e in visual_elements if e['properties'].get('is_connector', False)]
            
            # Simple relationship detection based on proximity
            relationship_id = 0
            
            for i, elem1 in enumerate(elements):
                for j, elem2 in enumerate(elements[i+1:], i+1):
                    # Calculate distance between elements
                    pos1 = elem1.get('position', {})
                    pos2 = elem2.get('position', {})
                    
                    if pos1 and pos2:
                        distance = self._calculate_distance(pos1, pos2)
                        
                        # If elements are close, they might be related
                        if distance < 100:  # Arbitrary threshold
                            relationships.append({
                                'id': f"rel_{relationship_id}",
                                'from': elem1['id'],
                                'to': elem2['id'],
                                'type': 'proximity',
                                'strength': max(0, 100 - distance),
                                'properties': {
                                    'distance': distance,
                                    'inferred': True
                                }
                            })
                            relationship_id += 1
            
            # Add connector-based relationships
            for connector in connectors:
                # Find elements that this connector might connect
                # This is a simplified approach
                conn_pos = connector.get('position', {})
                if conn_pos:
                    nearby_elements = []
                    for elem in elements:
                        if elem['id'] != connector['id']:
                            elem_pos = elem.get('position', {})
                            if elem_pos:
                                distance = self._calculate_distance(conn_pos, elem_pos)
                                if distance < 50:  # Close to connector
                                    nearby_elements.append((elem, distance))
                    
                    # Create relationships between nearby elements
                    if len(nearby_elements) >= 2:
                        nearby_elements.sort(key=lambda x: x[1])  # Sort by distance
                        elem1, elem2 = nearby_elements[0][0], nearby_elements[1][0]
                        
                        relationships.append({
                            'id': f"conn_{relationship_id}",
                            'from': elem1['id'],
                            'to': elem2['id'],
                            'type': 'connector',
                            'strength': 90,
                            'properties': {
                                'connector_id': connector['id'],
                                'connector_shape': connector['shape'],
                                'inferred': False
                            }
                        })
                        relationship_id += 1
            
            return relationships
            
        except Exception as e:
            self.logger.error(f"Relationship analysis failed: {e}")
            return []
    
    def _calculate_distance(self, pos1: Dict, pos2: Dict) -> float:
        """Calculate distance between two positions."""
        try:
            x1, y1 = pos1.get('x', 0), pos1.get('y', 0)
            x2, y2 = pos2.get('x', 0), pos2.get('y', 0)
            
            return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        except:
            return float('inf')
    
    def _analyze_flow(self, elements: List[Dict], relationships: List[Dict]) -> Dict:
        """Analyze flow patterns in the diagram."""
        flow_analysis = {
            'has_flow': False,
            'flow_direction': 'unknown',
            'entry_points': [],
            'exit_points': [],
            'flow_paths': [],
            'cycles': []
        }
        
        try:
            if not NETWORKX_AVAILABLE:
                return flow_analysis
            
            # Create a graph from relationships
            G = nx.DiGraph()
            
            # Add nodes
            for elem in elements:
                G.add_node(elem['id'], **elem)
            
            # Add edges
            for rel in relationships:
                G.add_edge(rel['from'], rel['to'], **rel)
            
            # Analyze flow
            if G.number_of_edges() > 0:
                flow_analysis['has_flow'] = True
                
                # Find entry points (nodes with no incoming edges)
                entry_points = [n for n in G.nodes() if G.in_degree(n) == 0]
                flow_analysis['entry_points'] = entry_points
                
                # Find exit points (nodes with no outgoing edges)
                exit_points = [n for n in G.nodes() if G.out_degree(n) == 0]
                flow_analysis['exit_points'] = exit_points
                
                # Find cycles
                try:
                    cycles = list(nx.simple_cycles(G))
                    flow_analysis['cycles'] = cycles
                except:
                    pass
                
                # Analyze flow direction
                if len(entry_points) == 1 and len(exit_points) == 1:
                    flow_analysis['flow_direction'] = 'linear'
                elif len(entry_points) > 1 or len(exit_points) > 1:
                    flow_analysis['flow_direction'] = 'branching'
                elif cycles:
                    flow_analysis['flow_direction'] = 'cyclic'
            
            return flow_analysis
            
        except Exception as e:
            self.logger.error(f"Flow analysis failed: {e}")
            return flow_analysis
    
    def _analyze_structure(self, elements: List[Dict], relationships: List[Dict]) -> Dict:
        """Analyze the overall structure of the diagram."""
        structure = {
            'complexity': 'low',
            'organization': 'unstructured',
            'hierarchy_levels': 0,
            'clustering': {},
            'connectivity': 'sparse'
        }
        
        try:
            # Calculate complexity
            element_count = len(elements)
            relationship_count = len(relationships)
            
            if element_count > 20 or relationship_count > 15:
                structure['complexity'] = 'high'
            elif element_count > 10 or relationship_count > 8:
                structure['complexity'] = 'medium'
            
            # Analyze organization
            visual_elements = [e for e in elements if e['type'] == 'visual']
            if visual_elements:
                # Check for hierarchical organization
                y_positions = []
                for elem in visual_elements:
                    pos = elem.get('position', {})
                    if pos.get('y') is not None:
                        y_positions.append(pos['y'])
                
                if y_positions:
                    # Group by approximate Y levels
                    y_positions.sort()
                    levels = []
                    current_level = [y_positions[0]]
                    
                    for y in y_positions[1:]:
                        if abs(y - current_level[-1]) < 30:  # Same level
                            current_level.append(y)
                        else:
                            levels.append(current_level)
                            current_level = [y]
                    
                    levels.append(current_level)
                    structure['hierarchy_levels'] = len(levels)
                    
                    if len(levels) > 2:
                        structure['organization'] = 'hierarchical'
                    elif len(levels) == 2:
                        structure['organization'] = 'layered'
            
            # Analyze connectivity
            if relationship_count > element_count * 0.8:
                structure['connectivity'] = 'dense'
            elif relationship_count > element_count * 0.3:
                structure['connectivity'] = 'moderate'
            
            return structure
            
        except Exception as e:
            self.logger.error(f"Structure analysis failed: {e}")
            return structure
    
    def _calculate_complexity(self, elements: List[Dict], relationships: List[Dict]) -> float:
        """Calculate complexity score for the diagram."""
        try:
            # Base complexity on number of elements and relationships
            element_count = len(elements)
            relationship_count = len(relationships)
            
            # Weight factors
            element_weight = 2
            relationship_weight = 3
            
            # Calculate raw score
            raw_score = (element_count * element_weight) + (relationship_count * relationship_weight)
            
            # Normalize to 0-100 scale
            # Assuming maximum reasonable complexity is 20 elements and 30 relationships
            max_score = (20 * element_weight) + (30 * relationship_weight)
            
            return min(100, (raw_score / max_score) * 100)
            
        except Exception as e:
            self.logger.error(f"Complexity calculation failed: {e}")
            return 50.0
    
    def _generate_diagram_description(self, diagram_type: Dict, elements: List[Dict], relationships: List[Dict], flow_analysis: Dict) -> Dict:
        """Generate comprehensive diagram description."""
        try:
            detected_type = diagram_type.get('detected_type', 'unknown')
            element_count = len(elements)
            relationship_count = len(relationships)
            
            descriptions = {}
            
            # Brief description
            descriptions['brief'] = f"A {detected_type} diagram with {element_count} elements and {relationship_count} connections."
            
            # Detailed description
            details = []
            details.append(f"This is a {detected_type} diagram")
            details.append(f"containing {element_count} elements")
            
            if relationship_count > 0:
                details.append(f"connected by {relationship_count} relationships")
            
            # Flow information
            if flow_analysis.get('has_flow'):
                flow_direction = flow_analysis.get('flow_direction', 'unknown')
                details.append(f"with {flow_direction} flow pattern")
                
                entry_points = flow_analysis.get('entry_points', [])
                exit_points = flow_analysis.get('exit_points', [])
                
                if entry_points:
                    details.append(f"starting from {len(entry_points)} entry point(s)")
                if exit_points:
                    details.append(f"ending at {len(exit_points)} exit point(s)")
            
            descriptions['detailed'] = '. '.join(details) + '.'
            
            # Comprehensive description
            comprehensive = []
            comprehensive.append(f"Diagram Analysis: {detected_type} type")
            comprehensive.append(f"Confidence: {diagram_type.get('confidence', 0):.1f}%")
            comprehensive.append(f"Structure: {element_count} elements, {relationship_count} relationships")
            
            # Element breakdown
            text_elements = len([e for e in elements if e['type'] == 'text'])
            visual_elements = len([e for e in elements if e['type'] == 'visual'])
            
            if text_elements > 0:
                comprehensive.append(f"Text elements: {text_elements}")
            if visual_elements > 0:
                comprehensive.append(f"Visual elements: {visual_elements}")
            
            # Flow analysis
            if flow_analysis.get('has_flow'):
                flow_info = []
                if flow_analysis.get('entry_points'):
                    flow_info.append(f"{len(flow_analysis['entry_points'])} entry points")
                if flow_analysis.get('exit_points'):
                    flow_info.append(f"{len(flow_analysis['exit_points'])} exit points")
                if flow_analysis.get('cycles'):
                    flow_info.append(f"{len(flow_analysis['cycles'])} cycles")
                
                if flow_info:
                    comprehensive.append(f"Flow analysis: {', '.join(flow_info)}")
            
            descriptions['comprehensive'] = '. '.join(comprehensive) + '.'
            
            return descriptions
            
        except Exception as e:
            self.logger.error(f"Description generation failed: {e}")
            return {
                'brief': 'Diagram analysis failed',
                'detailed': f'Unable to generate description: {str(e)}',
                'comprehensive': f'Description generation error: {str(e)}'
            }
    
    def _enhance_diagram_analysis(self, extraction_result: Dict, area_data: Dict) -> Dict:
        """Enhance diagram analysis with additional processing."""
        if not extraction_result.get('success'):
            return extraction_result
        
        try:
            # Add contextual information
            context = {
                'document_context': {
                    'page_number': area_data.get('page', 1),
                    'area_type': area_data.get('type', 'DIAGRAM'),
                    'processing_notes': area_data.get('special_notes', ''),
                    'high_priority': area_data.get('high_priority', False)
                },
                'diagram_metrics': self._calculate_diagram_metrics(extraction_result),
                'analysis_recommendations': self._generate_analysis_recommendations(extraction_result)
            }
            
            # Add context to result
            extraction_result['context'] = context
            
            # Generate output formats
            extraction_result['output_formats'] = self._generate_output_formats(extraction_result)
            
            return extraction_result
            
        except Exception as e:
            self.logger.error(f"Diagram enhancement failed: {e}")
            extraction_result['enhancement_error'] = str(e)
            return extraction_result
    
    def _calculate_diagram_metrics(self, extraction_result: Dict) -> Dict:
        """Calculate metrics for the diagram."""
        metrics = {
            'complexity_score': 0.0,
            'connectivity_ratio': 0.0,
            'flow_efficiency': 0.0,
            'structure_clarity': 0.0
        }
        
        try:
            content = extraction_result.get('content', {})
            elements = content.get('elements', [])
            relationships = content.get('relationships', [])
            
            # Complexity score
            metrics['complexity_score'] = self._calculate_complexity(elements, relationships)
            
            # Connectivity ratio
            if len(elements) > 0:
                metrics['connectivity_ratio'] = len(relationships) / len(elements)
            
            # Flow efficiency (simplified)
            flow_analysis = content.get('flow_analysis', {})
            if flow_analysis.get('has_flow'):
                entry_points = len(flow_analysis.get('entry_points', []))
                exit_points = len(flow_analysis.get('exit_points', []))
                cycles = len(flow_analysis.get('cycles', []))
                
                # Ideal flow: 1 entry, 1 exit, no cycles
                flow_score = 100
                if entry_points != 1:
                    flow_score -= abs(entry_points - 1) * 10
                if exit_points != 1:
                    flow_score -= abs(exit_points - 1) * 10
                if cycles > 0:
                    flow_score -= cycles * 15
                
                metrics['flow_efficiency'] = max(0, flow_score)
            
            # Structure clarity (based on organization)
            structure = content.get('structure', {})
            organization = structure.get('organization', 'unstructured')
            
            if organization == 'hierarchical':
                metrics['structure_clarity'] = 90.0
            elif organization == 'layered':
                metrics['structure_clarity'] = 75.0
            elif organization == 'structured':
                metrics['structure_clarity'] = 60.0
            else:
                metrics['structure_clarity'] = 40.0
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Metrics calculation failed: {e}")
            return metrics
    
    def _generate_analysis_recommendations(self, extraction_result: Dict) -> List[str]:
        """Generate recommendations for diagram analysis."""
        recommendations = []
        
        try:
            content = extraction_result.get('content', {})
            diagram_type = content.get('diagram_type', {})
            
            # Type-specific recommendations
            detected_type = diagram_type.get('detected_type', 'unknown')
            confidence = diagram_type.get('confidence', 0)
            
            if confidence < 70:
                recommendations.append("Consider manual verification of diagram type classification")
            
            # Structural recommendations
            elements = content.get('elements', [])
            relationships = content.get('relationships', [])
            
            if len(elements) > 20:
                recommendations.append("Complex diagram - consider breaking into smaller components")
            
            if len(relationships) < len(elements) * 0.2:
                recommendations.append("Low connectivity - verify all relationships are captured")
            
            # Flow recommendations
            flow_analysis = content.get('flow_analysis', {})
            if flow_analysis.get('cycles'):
                recommendations.append("Diagram contains cycles - verify this is intentional")
            
            if not flow_analysis.get('has_flow') and detected_type == 'flowchart':
                recommendations.append("Flowchart type detected but no flow pattern found")
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Recommendation generation failed: {e}")
            return ['Analysis recommendations unavailable due to error']
    
    def _generate_output_formats(self, extraction_result: Dict) -> Dict:
        """Generate diagram analysis in multiple output formats."""
        formats = {}
        
        try:
            content = extraction_result.get('content', {})
            
            # JSON format (default)
            formats['json'] = content
            
            # GraphML format (for network analysis tools)
            if NETWORKX_AVAILABLE:
                formats['graphml'] = self._generate_graphml(content)
            
            # DOT format (for Graphviz)
            formats['dot'] = self._generate_dot_format(content)
            
            # Markdown format
            formats['markdown'] = self._generate_markdown_format(content)
            
        except Exception as e:
            self.logger.error(f"Output format generation failed: {e}")
            formats['error'] = str(e)
        
        return formats
    
    def _generate_graphml(self, content: Dict) -> str:
        """Generate GraphML format for network analysis."""
        try:
            if not NETWORKX_AVAILABLE:
                return "GraphML format requires NetworkX library"
            
            G = nx.DiGraph()
            
            # Add nodes
            elements = content.get('elements', [])
            for elem in elements:
                G.add_node(elem['id'], **elem)
            
            # Add edges
            relationships = content.get('relationships', [])
            for rel in relationships:
                G.add_edge(rel['from'], rel['to'], **rel)
            
            # Convert to GraphML
            import io
            output = io.StringIO()
            nx.write_graphml(G, output)
            return output.getvalue()
            
        except Exception as e:
            return f"GraphML generation failed: {str(e)}"
    
    def _generate_dot_format(self, content: Dict) -> str:
        """Generate DOT format for Graphviz."""
        try:
            lines = ['digraph diagram {']
            lines.append('    rankdir=TB;')
            lines.append('    node [shape=box];')
            lines.append('')
            
            # Add nodes
            elements = content.get('elements', [])
            for elem in elements:
                node_id = elem['id'].replace('-', '_')
                label = elem.get('content', elem.get('shape', 'node'))
                lines.append(f'    {node_id} [label="{label}"];')
            
            lines.append('')
            
            # Add edges
            relationships = content.get('relationships', [])
            for rel in relationships:
                from_id = rel['from'].replace('-', '_')
                to_id = rel['to'].replace('-', '_')
                lines.append(f'    {from_id} -> {to_id};')
            
            lines.append('}')
            
            return '\n'.join(lines)
            
        except Exception as e:
            return f"DOT generation failed: {str(e)}"
    
    def _generate_markdown_format(self, content: Dict) -> str:
        """Generate Markdown format for documentation."""
        try:
            lines = []
            
            # Title
            diagram_type = content.get('diagram_type', {})
            detected_type = diagram_type.get('detected_type', 'unknown')
            lines.append(f"# {detected_type.title()} Diagram Analysis")
            lines.append("")
            
            # Description
            description = content.get('description', {})
            lines.append(f"**Description:** {description.get('detailed', 'No description available')}")
            lines.append("")
            
            # Elements
            elements = content.get('elements', [])
            lines.append(f"## Elements ({len(elements)})")
            lines.append("")
            
            for elem in elements:
                elem_type = elem.get('type', 'unknown')
                if elem_type == 'text':
                    lines.append(f"- **{elem['id']}**: {elem.get('content', 'No content')}")
                else:
                    lines.append(f"- **{elem['id']}**: {elem.get('shape', 'unknown shape')}")
            
            lines.append("")
            
            # Relationships
            relationships = content.get('relationships', [])
            if relationships:
                lines.append(f"## Relationships ({len(relationships)})")
                lines.append("")
                
                for rel in relationships:
                    lines.append(f"- {rel['from']} → {rel['to']} ({rel.get('type', 'unknown')})")
            
            return '\n'.join(lines)
            
        except Exception as e:
            return f"Markdown generation failed: {str(e)}"
    
    def validate_extraction(self, extracted_content: Dict) -> Dict:
        """Validate diagram extraction results."""
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
            if not content.get('elements'):
                validation['issues'].append('No elements detected')
            
            if not content.get('diagram_type'):
                validation['issues'].append('Diagram type not detected')
            
            # Check quality
            diagram_type = content.get('diagram_type', {})
            type_confidence = diagram_type.get('confidence', 0)
            
            if type_confidence < 50:
                validation['issues'].append('Low confidence in diagram type detection')
            
            # Calculate validation score
            validation['confidence'] = extracted_content.get('confidence_score', 0)
            validation['quality_score'] = type_confidence
            validation['is_valid'] = len(validation['issues']) == 0 and type_confidence > 30
            
        except Exception as e:
            validation['issues'].append(f'Validation error: {str(e)}')
        
        return validation
    
    def get_supported_formats(self) -> List[str]:
        """Get supported output formats."""
        formats = ['json', 'dot', 'markdown']
        if NETWORKX_AVAILABLE:
            formats.append('graphml')
        return formats