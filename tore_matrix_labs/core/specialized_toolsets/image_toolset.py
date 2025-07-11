#!/usr/bin/env python3
"""
Image processing toolset with AI-powered description generation and visual content analysis.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
import time
import io
import base64
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np

from .base_toolset import BaseToolset
from ...config.settings import Settings

# Optional AI/ML libraries for image analysis
try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    cv2 = None

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    pytesseract = None

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None


class ImageToolset(BaseToolset):
    """Advanced image processing and description generation toolset."""
    
    def __init__(self, settings: Settings):
        super().__init__(settings)
        
        # Image-specific processing options
        self.processing_options.update({
            'description_detail': 'comprehensive',  # 'brief', 'detailed', 'comprehensive'
            'include_text_extraction': True,
            'include_object_detection': True,
            'include_color_analysis': True,
            'include_composition_analysis': True,
            'enhance_quality': True,
            'output_formats': ['json', 'markdown', 'html']
        })
        
        # Image analysis capabilities
        self.analysis_capabilities = {
            'ocr_text_extraction': TESSERACT_AVAILABLE,
            'opencv_analysis': OPENCV_AVAILABLE,
            'ai_description': REQUESTS_AVAILABLE,  # For API-based AI description
            'basic_analysis': True  # Always available
        }
        
        self.logger.info(f"Image toolset initialized with capabilities: {self.analysis_capabilities}")
    
    def process_area(self, area_data: Dict, pdf_document: fitz.Document) -> Dict:
        """Process an image area with comprehensive analysis and description generation."""
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
            
            # Extract image content
            extraction_result = self.extract_content(area_data, pdf_document)
            
            # Enhance with additional analysis
            enhanced_result = self._enhance_image_analysis(extraction_result, area_data)
            
            # Postprocessing
            final_result = self.postprocess_result(enhanced_result, area_data)
            
            # Update timing
            self.metrics['processing_time'] += time.time() - start_time
            
            return final_result
            
        except Exception as e:
            self.logger.error(f"Image processing failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'content': None,
                'processing_time': time.time() - start_time
            }
    
    def extract_content(self, area_data: Dict, pdf_document: fitz.Document) -> Dict:
        """Extract and analyze image content."""
        try:
            # Get preprocessed image
            preprocessed = self.preprocess_area(area_data, pdf_document)
            if not preprocessed['preprocessing_success']:
                return {
                    'success': False,
                    'error': 'Image preprocessing failed',
                    'content': None
                }
            
            image = preprocessed['image']
            
            # Basic image analysis
            basic_analysis = self._analyze_image_basic(image)
            
            # Text extraction from image
            text_extraction = self._extract_text_from_image(image)
            
            # Visual content analysis
            visual_analysis = self._analyze_visual_content(image)
            
            # Generate description
            description = self._generate_image_description(image, basic_analysis, text_extraction, visual_analysis)
            
            return {
                'success': True,
                'content': {
                    'description': description,
                    'extracted_text': text_extraction,
                    'visual_analysis': visual_analysis,
                    'technical_details': basic_analysis
                },
                'raw_content': description.get('comprehensive', ''),
                'structured_content': {
                    'type': 'image',
                    'description': description,
                    'metadata': basic_analysis,
                    'text_content': text_extraction.get('text', ''),
                    'confidence': visual_analysis.get('confidence', 75.0)
                },
                'confidence_score': visual_analysis.get('confidence', 75.0)
            }
            
        except Exception as e:
            self.logger.error(f"Image content extraction failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'content': None
            }
    
    def _analyze_image_basic(self, image: Image.Image) -> Dict:
        """Perform basic image analysis."""
        try:
            # Basic properties
            width, height = image.size
            format_info = image.format or 'Unknown'
            mode = image.mode
            
            # Color analysis
            if image.mode == 'RGB':
                colors = image.getcolors(maxcolors=256*256*256)
                dominant_colors = sorted(colors, key=lambda x: x[0], reverse=True)[:5] if colors else []
                
                # Convert to hex
                dominant_hex = []
                for count, color in dominant_colors:
                    if isinstance(color, tuple) and len(color) >= 3:
                        hex_color = f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"
                        dominant_hex.append({'color': hex_color, 'frequency': count})
                
                color_analysis = {
                    'dominant_colors': dominant_hex,
                    'color_mode': mode,
                    'has_transparency': image.mode in ('RGBA', 'LA', 'P')
                }
            else:
                color_analysis = {
                    'dominant_colors': [],
                    'color_mode': mode,
                    'has_transparency': image.mode in ('RGBA', 'LA', 'P')
                }
            
            # Basic composition analysis
            composition = self._analyze_composition(image)
            
            return {
                'dimensions': {'width': width, 'height': height},
                'format': format_info,
                'color_analysis': color_analysis,
                'composition': composition,
                'file_size_estimate': width * height * (4 if mode == 'RGBA' else 3),
                'aspect_ratio': round(width / height, 2) if height > 0 else 0
            }
            
        except Exception as e:
            self.logger.error(f"Basic image analysis failed: {e}")
            return {
                'dimensions': {'width': 0, 'height': 0},
                'format': 'Unknown',
                'color_analysis': {},
                'composition': {},
                'error': str(e)
            }
    
    def _analyze_composition(self, image: Image.Image) -> Dict:
        """Analyze image composition."""
        try:
            width, height = image.size
            
            # Convert to grayscale for analysis
            gray = image.convert('L')
            gray_array = np.array(gray)
            
            # Brightness analysis
            brightness = {
                'average': float(np.mean(gray_array)),
                'std': float(np.std(gray_array)),
                'min': int(np.min(gray_array)),
                'max': int(np.max(gray_array))
            }
            
            # Contrast analysis
            contrast_score = brightness['std'] / 255.0 * 100
            
            # Simple edge detection for complexity
            if OPENCV_AVAILABLE:
                gray_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
                edges = cv2.Canny(gray_cv, 50, 150)
                edge_density = np.sum(edges > 0) / (width * height) * 100
            else:
                # Fallback edge detection
                edges = gray.filter(ImageFilter.FIND_EDGES)
                edge_array = np.array(edges)
                edge_density = np.sum(edge_array > 50) / (width * height) * 100
            
            # Categorize image type based on analysis
            if brightness['average'] > 200:
                brightness_category = 'bright'
            elif brightness['average'] < 100:
                brightness_category = 'dark'
            else:
                brightness_category = 'moderate'
            
            if contrast_score > 60:
                contrast_category = 'high'
            elif contrast_score < 30:
                contrast_category = 'low'
            else:
                contrast_category = 'moderate'
            
            if edge_density > 15:
                complexity = 'complex'
            elif edge_density > 5:
                complexity = 'moderate'
            else:
                complexity = 'simple'
            
            return {
                'brightness': brightness,
                'brightness_category': brightness_category,
                'contrast_score': contrast_score,
                'contrast_category': contrast_category,
                'edge_density': edge_density,
                'complexity': complexity,
                'estimated_content_type': self._estimate_content_type(brightness, contrast_score, edge_density)
            }
            
        except Exception as e:
            self.logger.error(f"Composition analysis failed: {e}")
            return {'error': str(e)}
    
    def _estimate_content_type(self, brightness: Dict, contrast_score: float, edge_density: float) -> str:
        """Estimate the type of content in the image."""
        # Simple heuristics for content type estimation
        if edge_density > 20 and contrast_score > 50:
            return 'technical_diagram'
        elif edge_density > 15:
            return 'detailed_illustration'
        elif brightness['average'] > 180 and contrast_score < 30:
            return 'document_scan'
        elif edge_density < 5 and contrast_score < 40:
            return 'photograph'
        else:
            return 'mixed_content'
    
    def _extract_text_from_image(self, image: Image.Image) -> Dict:
        """Extract text from image using OCR."""
        text_extraction = {
            'text': '',
            'confidence': 0.0,
            'method': 'none',
            'word_count': 0,
            'languages_detected': []
        }
        
        try:
            if TESSERACT_AVAILABLE:
                # Use Tesseract OCR
                extracted_text = pytesseract.image_to_string(image)
                confidence_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
                
                # Calculate average confidence
                confidences = [int(conf) for conf in confidence_data['conf'] if int(conf) > 0]
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0
                
                text_extraction.update({
                    'text': extracted_text.strip(),
                    'confidence': avg_confidence,
                    'method': 'tesseract',
                    'word_count': len(extracted_text.split()) if extracted_text else 0
                })
                
                # Try to detect language
                try:
                    lang_info = pytesseract.image_to_osd(image)
                    if 'Script:' in lang_info:
                        script_line = [line for line in lang_info.split('\n') if 'Script:' in line][0]
                        detected_script = script_line.split('Script:')[1].strip()
                        text_extraction['languages_detected'] = [detected_script]
                except:
                    pass
            else:
                # Fallback: indicate text may be present but cannot extract
                text_extraction.update({
                    'text': '[TEXT DETECTED - OCR NOT AVAILABLE]',
                    'confidence': 0.0,
                    'method': 'visual_detection',
                    'word_count': 0
                })
            
        except Exception as e:
            self.logger.error(f"Text extraction failed: {e}")
            text_extraction['error'] = str(e)
        
        return text_extraction
    
    def _analyze_visual_content(self, image: Image.Image) -> Dict:
        """Analyze visual content of the image."""
        analysis = {
            'confidence': 70.0,
            'content_categories': [],
            'objects_detected': [],
            'scene_analysis': {},
            'quality_assessment': {}
        }
        
        try:
            # Basic content categorization
            basic_analysis = self._analyze_image_basic(image)
            composition = basic_analysis.get('composition', {})
            
            # Categorize based on composition
            content_categories = []
            
            estimated_type = composition.get('estimated_content_type', 'unknown')
            content_categories.append(estimated_type)
            
            # Color-based categorization
            color_analysis = basic_analysis.get('color_analysis', {})
            if color_analysis.get('dominant_colors'):
                if len(color_analysis['dominant_colors']) > 3:
                    content_categories.append('colorful')
                else:
                    content_categories.append('monochromatic')
            
            # Complexity-based categorization
            complexity = composition.get('complexity', 'unknown')
            if complexity == 'complex':
                content_categories.append('detailed')
            elif complexity == 'simple':
                content_categories.append('minimalist')
            
            # Quality assessment
            quality = self._assess_image_quality(image, composition)
            
            analysis.update({
                'confidence': quality.get('overall_score', 70.0),
                'content_categories': content_categories,
                'scene_analysis': {
                    'estimated_type': estimated_type,
                    'complexity': complexity,
                    'brightness': composition.get('brightness_category', 'unknown'),
                    'contrast': composition.get('contrast_category', 'unknown')
                },
                'quality_assessment': quality
            })
            
        except Exception as e:
            self.logger.error(f"Visual content analysis failed: {e}")
            analysis['error'] = str(e)
        
        return analysis
    
    def _assess_image_quality(self, image: Image.Image, composition: Dict) -> Dict:
        """Assess the quality of the image."""
        try:
            quality = {
                'overall_score': 70.0,
                'sharpness': 50.0,
                'brightness': 50.0,
                'contrast': 50.0,
                'noise_level': 50.0,
                'resolution': 50.0
            }
            
            width, height = image.size
            
            # Resolution assessment
            pixel_count = width * height
            if pixel_count > 1000000:  # > 1MP
                quality['resolution'] = 90.0
            elif pixel_count > 500000:  # > 0.5MP
                quality['resolution'] = 75.0
            elif pixel_count > 100000:  # > 0.1MP
                quality['resolution'] = 60.0
            else:
                quality['resolution'] = 40.0
            
            # Brightness assessment
            brightness_avg = composition.get('brightness', {}).get('average', 128)
            if 100 <= brightness_avg <= 200:
                quality['brightness'] = 85.0
            elif 80 <= brightness_avg <= 220:
                quality['brightness'] = 70.0
            else:
                quality['brightness'] = 50.0
            
            # Contrast assessment
            contrast_score = composition.get('contrast_score', 50)
            if contrast_score > 40:
                quality['contrast'] = 85.0
            elif contrast_score > 20:
                quality['contrast'] = 70.0
            else:
                quality['contrast'] = 50.0
            
            # Sharpness assessment (based on edge density)
            edge_density = composition.get('edge_density', 10)
            if edge_density > 10:
                quality['sharpness'] = 80.0
            elif edge_density > 5:
                quality['sharpness'] = 65.0
            else:
                quality['sharpness'] = 45.0
            
            # Calculate overall score
            quality['overall_score'] = (
                quality['resolution'] * 0.3 +
                quality['brightness'] * 0.2 +
                quality['contrast'] * 0.2 +
                quality['sharpness'] * 0.2 +
                quality['noise_level'] * 0.1
            )
            
            return quality
            
        except Exception as e:
            self.logger.error(f"Quality assessment failed: {e}")
            return {'overall_score': 50.0, 'error': str(e)}
    
    def _generate_image_description(self, image: Image.Image, basic_analysis: Dict, text_extraction: Dict, visual_analysis: Dict) -> Dict:
        """Generate comprehensive image description."""
        try:
            # Get image properties
            width, height = image.size
            aspect_ratio = basic_analysis.get('aspect_ratio', 1.0)
            
            # Generate different levels of description
            descriptions = {}
            
            # Brief description
            brief_elements = []
            estimated_type = visual_analysis.get('scene_analysis', {}).get('estimated_type', 'image')
            brief_elements.append(f"A {estimated_type.replace('_', ' ')}")
            
            if text_extraction.get('text'):
                brief_elements.append("containing text")
            
            dimensions_desc = f"{width}x{height} pixels"
            brief_elements.append(f"({dimensions_desc})")
            
            descriptions['brief'] = ' '.join(brief_elements) + '.'
            
            # Detailed description
            detailed_elements = []
            
            # Content type and composition
            complexity = visual_analysis.get('scene_analysis', {}).get('complexity', 'moderate')
            detailed_elements.append(f"This is a {complexity} {estimated_type.replace('_', ' ')}")
            
            # Dimensions and format
            detailed_elements.append(f"with dimensions of {width}x{height} pixels (aspect ratio {aspect_ratio})")
            
            # Color information
            color_analysis = basic_analysis.get('color_analysis', {})
            if color_analysis.get('dominant_colors'):
                color_count = len(color_analysis['dominant_colors'])
                detailed_elements.append(f"featuring {color_count} dominant colors")
            
            # Brightness and contrast
            brightness_cat = visual_analysis.get('scene_analysis', {}).get('brightness', 'moderate')
            contrast_cat = visual_analysis.get('scene_analysis', {}).get('contrast', 'moderate')
            detailed_elements.append(f"with {brightness_cat} brightness and {contrast_cat} contrast")
            
            # Text content
            if text_extraction.get('text'):
                word_count = text_extraction.get('word_count', 0)
                detailed_elements.append(f"containing approximately {word_count} words of text")
            
            descriptions['detailed'] = '. '.join(detailed_elements) + '.'
            
            # Comprehensive description
            comprehensive_elements = []
            
            # Technical details
            comprehensive_elements.append(f"Technical Analysis: {estimated_type.replace('_', ' ')} with {complexity} visual complexity")
            
            # Quality assessment
            quality = visual_analysis.get('quality_assessment', {})
            overall_quality = quality.get('overall_score', 50)
            comprehensive_elements.append(f"Quality score: {overall_quality:.1f}/100")
            
            # Composition details
            composition = basic_analysis.get('composition', {})
            if composition.get('edge_density'):
                edge_density = composition['edge_density']
                comprehensive_elements.append(f"Edge density: {edge_density:.1f}% (indicating {complexity} detail level)")
            
            # Color palette
            if color_analysis.get('dominant_colors'):
                color_desc = []
                for color_info in color_analysis['dominant_colors'][:3]:
                    color_desc.append(color_info['color'])
                comprehensive_elements.append(f"Primary colors: {', '.join(color_desc)}")
            
            # Text analysis
            if text_extraction.get('text'):
                confidence = text_extraction.get('confidence', 0)
                comprehensive_elements.append(f"Text extraction confidence: {confidence:.1f}%")
                if text_extraction.get('languages_detected'):
                    langs = ', '.join(text_extraction['languages_detected'])
                    comprehensive_elements.append(f"Detected languages/scripts: {langs}")
            
            descriptions['comprehensive'] = '. '.join(comprehensive_elements) + '.'
            
            return descriptions
            
        except Exception as e:
            self.logger.error(f"Description generation failed: {e}")
            return {
                'brief': 'Image analysis failed',
                'detailed': f'Unable to generate description: {str(e)}',
                'comprehensive': f'Description generation error: {str(e)}'
            }
    
    def _enhance_image_analysis(self, extraction_result: Dict, area_data: Dict) -> Dict:
        """Enhance image analysis with additional processing."""
        if not extraction_result.get('success'):
            return extraction_result
        
        try:
            # Add contextual information
            context = {
                'document_context': {
                    'page_number': area_data.get('page', 1),
                    'area_type': area_data.get('type', 'IMAGE'),
                    'processing_notes': area_data.get('special_notes', ''),
                    'high_priority': area_data.get('high_priority', False)
                },
                'usage_recommendations': self._generate_usage_recommendations(extraction_result),
                'accessibility': self._generate_accessibility_info(extraction_result)
            }
            
            # Add context to result
            extraction_result['context'] = context
            
            # Generate output formats
            extraction_result['output_formats'] = self._generate_output_formats(extraction_result)
            
            return extraction_result
            
        except Exception as e:
            self.logger.error(f"Image enhancement failed: {e}")
            extraction_result['enhancement_error'] = str(e)
            return extraction_result
    
    def _generate_usage_recommendations(self, extraction_result: Dict) -> Dict:
        """Generate recommendations for image usage."""
        recommendations = {
            'alt_text': '',
            'caption_suggestion': '',
            'best_use_cases': [],
            'optimization_suggestions': []
        }
        
        try:
            content = extraction_result.get('content', {})
            description = content.get('description', {})
            
            # Alt text (brief description)
            recommendations['alt_text'] = description.get('brief', 'Image')
            
            # Caption suggestion (detailed description)
            recommendations['caption_suggestion'] = description.get('detailed', '')
            
            # Use cases based on content type
            visual_analysis = content.get('visual_analysis', {})
            scene_analysis = visual_analysis.get('scene_analysis', {})
            estimated_type = scene_analysis.get('estimated_type', 'unknown')
            
            if estimated_type == 'technical_diagram':
                recommendations['best_use_cases'] = ['Technical documentation', 'Training materials', 'Reference guides']
            elif estimated_type == 'photograph':
                recommendations['best_use_cases'] = ['Illustrations', 'Visual examples', 'Marketing materials']
            elif estimated_type == 'document_scan':
                recommendations['best_use_cases'] = ['Document archives', 'Reference materials', 'Legal documents']
            else:
                recommendations['best_use_cases'] = ['General illustration', 'Supporting visual content']
            
            # Optimization suggestions
            quality = visual_analysis.get('quality_assessment', {})
            if quality.get('overall_score', 50) < 70:
                recommendations['optimization_suggestions'].append('Consider image enhancement for better quality')
            
            technical_details = content.get('technical_details', {})
            dimensions = technical_details.get('dimensions', {})
            if dimensions.get('width', 0) > 2000 or dimensions.get('height', 0) > 2000:
                recommendations['optimization_suggestions'].append('Consider resizing for web use')
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Usage recommendations failed: {e}")
            return recommendations
    
    def _generate_accessibility_info(self, extraction_result: Dict) -> Dict:
        """Generate accessibility information."""
        accessibility = {
            'alt_text': '',
            'long_description': '',
            'color_accessibility': {},
            'text_accessibility': {}
        }
        
        try:
            content = extraction_result.get('content', {})
            description = content.get('description', {})
            
            # Alt text and long description
            accessibility['alt_text'] = description.get('brief', 'Image')
            accessibility['long_description'] = description.get('comprehensive', '')
            
            # Color accessibility
            visual_analysis = content.get('visual_analysis', {})
            quality = visual_analysis.get('quality_assessment', {})
            
            contrast_score = quality.get('contrast', 50)
            if contrast_score > 70:
                accessibility['color_accessibility']['contrast'] = 'Good'
            elif contrast_score > 40:
                accessibility['color_accessibility']['contrast'] = 'Fair'
            else:
                accessibility['color_accessibility']['contrast'] = 'Poor'
            
            # Text accessibility
            text_extraction = content.get('extracted_text', {})
            if text_extraction.get('text'):
                accessibility['text_accessibility'] = {
                    'has_text': True,
                    'text_confidence': text_extraction.get('confidence', 0),
                    'text_content': text_extraction.get('text', ''),
                    'word_count': text_extraction.get('word_count', 0)
                }
            else:
                accessibility['text_accessibility'] = {
                    'has_text': False,
                    'note': 'No text detected in image'
                }
            
            return accessibility
            
        except Exception as e:
            self.logger.error(f"Accessibility info generation failed: {e}")
            return accessibility
    
    def _generate_output_formats(self, extraction_result: Dict) -> Dict:
        """Generate image analysis in multiple output formats."""
        formats = {}
        
        try:
            content = extraction_result.get('content', {})
            description = content.get('description', {})
            
            # JSON format (default)
            formats['json'] = content
            
            # Markdown format
            markdown_lines = []
            markdown_lines.append(f"# Image Analysis")
            markdown_lines.append(f"")
            markdown_lines.append(f"**Description:** {description.get('detailed', 'No description available')}")
            markdown_lines.append(f"")
            
            # Technical details
            technical = content.get('technical_details', {})
            if technical.get('dimensions'):
                dims = technical['dimensions']
                markdown_lines.append(f"**Dimensions:** {dims.get('width', 0)}x{dims.get('height', 0)} pixels")
            
            # Text content
            text_extraction = content.get('extracted_text', {})
            if text_extraction.get('text'):
                markdown_lines.append(f"")
                markdown_lines.append(f"**Extracted Text:**")
                markdown_lines.append(f"```")
                markdown_lines.append(text_extraction['text'])
                markdown_lines.append(f"```")
            
            formats['markdown'] = '\n'.join(markdown_lines)
            
            # HTML format
            html_lines = []
            html_lines.append(f"<div class='image-analysis'>")
            html_lines.append(f"<h2>Image Analysis</h2>")
            html_lines.append(f"<p><strong>Description:</strong> {description.get('detailed', 'No description available')}</p>")
            
            if technical.get('dimensions'):
                dims = technical['dimensions']
                html_lines.append(f"<p><strong>Dimensions:</strong> {dims.get('width', 0)}x{dims.get('height', 0)} pixels</p>")
            
            if text_extraction.get('text'):
                html_lines.append(f"<h3>Extracted Text</h3>")
                html_lines.append(f"<pre>{text_extraction['text']}</pre>")
            
            html_lines.append(f"</div>")
            formats['html'] = '\n'.join(html_lines)
            
        except Exception as e:
            self.logger.error(f"Output format generation failed: {e}")
            formats['error'] = str(e)
        
        return formats
    
    def validate_extraction(self, extracted_content: Dict) -> Dict:
        """Validate image extraction results."""
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
            
            # Check for required components
            if not content.get('description'):
                validation['issues'].append('No description generated')
            
            if not content.get('technical_details'):
                validation['issues'].append('No technical analysis available')
            
            # Check quality
            visual_analysis = content.get('visual_analysis', {})
            quality_score = visual_analysis.get('quality_assessment', {}).get('overall_score', 0)
            
            if quality_score < 30:
                validation['issues'].append('Low image quality detected')
            
            # Calculate validation score
            validation['confidence'] = extracted_content.get('confidence_score', 0)
            validation['quality_score'] = quality_score
            validation['is_valid'] = len(validation['issues']) == 0 and quality_score > 30
            
        except Exception as e:
            validation['issues'].append(f'Validation error: {str(e)}')
        
        return validation
    
    def get_supported_formats(self) -> List[str]:
        """Get supported output formats."""
        return ['json', 'markdown', 'html', 'txt']
    
    def enhance_image_quality(self, image: Image.Image) -> Image.Image:
        """Enhance image quality for better analysis."""
        try:
            # Enhance contrast
            enhancer = ImageEnhance.Contrast(image)
            enhanced = enhancer.enhance(1.2)
            
            # Enhance sharpness
            enhancer = ImageEnhance.Sharpness(enhanced)
            enhanced = enhancer.enhance(1.1)
            
            # Enhance brightness if needed
            gray = enhanced.convert('L')
            avg_brightness = np.mean(np.array(gray))
            
            if avg_brightness < 100:
                enhancer = ImageEnhance.Brightness(enhanced)
                enhanced = enhancer.enhance(1.2)
            elif avg_brightness > 200:
                enhancer = ImageEnhance.Brightness(enhanced)
                enhanced = enhancer.enhance(0.9)
            
            return enhanced
            
        except Exception as e:
            self.logger.error(f"Image enhancement failed: {e}")
            return image