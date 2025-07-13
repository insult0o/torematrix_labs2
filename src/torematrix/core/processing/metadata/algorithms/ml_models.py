"""ML models for semantic classification and relationship detection.

This module provides machine learning models for advanced semantic analysis
of document elements, including similarity calculation and classification.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from dataclasses import dataclass
from abc import ABC, abstractmethod

from ....models.element import UnifiedElement
from ..extractors.semantic import SemanticRole

logger = logging.getLogger(__name__)


@dataclass
class FeatureVector:
    """Feature vector for ML models."""
    text_features: np.ndarray
    spatial_features: np.ndarray
    contextual_features: np.ndarray
    combined_features: np.ndarray


class BaseMLModel(ABC):
    """Abstract base class for ML models."""
    
    def __init__(self, model_path: Optional[str] = None):
        """Initialize base ML model.
        
        Args:
            model_path: Path to saved model
        """
        self.model_path = model_path
        self.is_loaded = False
        self.feature_extractor = FeatureExtractor()
    
    @abstractmethod
    def predict(self, features: FeatureVector) -> Tuple[Any, float]:
        """Make prediction from features.
        
        Args:
            features: Input features
            
        Returns:
            Tuple of (prediction, confidence)
        """
        pass
    
    @abstractmethod
    def load_model(self, model_path: str):
        """Load model from file.
        
        Args:
            model_path: Path to model file
        """
        pass


class FeatureExtractor:
    """Extract features from document elements for ML models."""
    
    def __init__(self):
        """Initialize feature extractor."""
        self.text_vectorizer = None  # Placeholder for text vectorizer
        self.feature_dim = 128  # Default feature dimension
    
    def extract_features(
        self, 
        element: UnifiedElement,
        context: Dict[str, Any]
    ) -> FeatureVector:
        """Extract complete feature vector from element.
        
        Args:
            element: Element to extract features from
            context: Document context
            
        Returns:
            Complete feature vector
        """
        text_features = self._extract_text_features(element)
        spatial_features = self._extract_spatial_features(element, context)
        contextual_features = self._extract_contextual_features(element, context)
        
        # Combine all features
        combined_features = np.concatenate([
            text_features, 
            spatial_features, 
            contextual_features
        ])
        
        return FeatureVector(
            text_features=text_features,
            spatial_features=spatial_features,
            contextual_features=contextual_features,
            combined_features=combined_features
        )
    
    def _extract_text_features(self, element: UnifiedElement) -> np.ndarray:
        """Extract text-based features.
        
        Args:
            element: Element to extract from
            
        Returns:
            Text feature vector
        """
        text = element.text or ""
        
        # Basic text statistics
        features = [
            len(text),  # Text length
            len(text.split()),  # Word count
            len([c for c in text if c.isupper()]) / max(len(text), 1),  # Uppercase ratio
            len([c for c in text if c.isdigit()]) / max(len(text), 1),  # Digit ratio
            text.count('.') / max(len(text.split()), 1),  # Sentence density
            text.count(',') / max(len(text.split()), 1),  # Comma density
        ]
        
        # Text patterns
        features.extend([
            1.0 if text.isupper() else 0.0,  # All caps
            1.0 if text.istitle() else 0.0,  # Title case
            1.0 if text.startswith(('Figure', 'Table', 'Chart')) else 0.0,  # Caption start
            1.0 if any(char in text for char in '•·▪▫◦‣⁃-*+') else 0.0,  # Has bullets
            1.0 if text.strip().endswith(':') else 0.0,  # Ends with colon
        ])
        
        # Element type encoding (one-hot)
        element_types = ['Text', 'Title', 'Header', 'Paragraph', 'List', 'ListItem', 
                        'Table', 'Figure', 'Image', 'Formula']
        type_features = [1.0 if element.type == et else 0.0 for et in element_types]
        features.extend(type_features)
        
        # Pad or truncate to fixed size
        target_size = 32
        if len(features) < target_size:
            features.extend([0.0] * (target_size - len(features)))
        else:
            features = features[:target_size]
        
        return np.array(features, dtype=np.float32)
    
    def _extract_spatial_features(
        self, 
        element: UnifiedElement, 
        context: Dict[str, Any]
    ) -> np.ndarray:
        """Extract spatial features.
        
        Args:
            element: Element to extract from
            context: Document context
            
        Returns:
            Spatial feature vector
        """
        features = []
        
        # Get bounding box if available
        bbox = None
        if element.metadata and element.metadata.coordinates:
            bbox_coords = element.metadata.coordinates.layout_bbox
            if bbox_coords and len(bbox_coords) >= 4:
                bbox = {
                    'left': bbox_coords[0],
                    'top': bbox_coords[1], 
                    'right': bbox_coords[2],
                    'bottom': bbox_coords[3]
                }
        
        if bbox:
            # Absolute position features
            features.extend([
                bbox['left'],
                bbox['top'],
                bbox['right'] - bbox['left'],  # width
                bbox['bottom'] - bbox['top'],  # height
            ])
            
            # Relative position features (if page dimensions available)
            page_width = context.get('page_width', 1.0)
            page_height = context.get('page_height', 1.0)
            
            features.extend([
                bbox['left'] / page_width,  # Relative left
                bbox['top'] / page_height,  # Relative top
                (bbox['right'] - bbox['left']) / page_width,  # Relative width
                (bbox['bottom'] - bbox['top']) / page_height,  # Relative height
                (bbox['left'] + bbox['right']) / 2 / page_width,  # Center X
                (bbox['top'] + bbox['bottom']) / 2 / page_height,  # Center Y
            ])
            
            # Position indicators
            features.extend([
                1.0 if bbox['left'] < page_width * 0.1 else 0.0,  # Far left
                1.0 if bbox['right'] > page_width * 0.9 else 0.0,  # Far right
                1.0 if bbox['top'] < page_height * 0.1 else 0.0,  # Top of page
                1.0 if bbox['bottom'] > page_height * 0.9 else 0.0,  # Bottom of page
            ])
        else:
            # No spatial information available
            features.extend([0.0] * 14)
        
        # Page number
        page_num = element.metadata.page_number if element.metadata else 0
        features.append(page_num)
        
        # Element index in document
        element_index = context.get('element_index', 0)
        total_elements = context.get('total_elements', 1)
        features.extend([
            element_index,
            element_index / total_elements,  # Relative position in document
        ])
        
        return np.array(features, dtype=np.float32)
    
    def _extract_contextual_features(
        self, 
        element: UnifiedElement, 
        context: Dict[str, Any]
    ) -> np.ndarray:
        """Extract contextual features.
        
        Args:
            element: Element to extract from
            context: Document context
            
        Returns:
            Contextual feature vector
        """
        features = []
        
        # Document-level context
        features.extend([
            context.get('total_elements', 0),
            len(context.get('table_elements', [])),
            len(context.get('figure_elements', [])),
        ])
        
        # Element type distribution
        type_counts = context.get('element_type_counts', {})
        total_elements = context.get('total_elements', 1)
        
        for element_type in ['Text', 'Title', 'Header', 'Paragraph', 'List', 'Table', 'Figure']:
            count = type_counts.get(element_type, 0)
            features.append(count / total_elements)
        
        # Position context
        features.extend([
            1.0 if context.get('is_first_text', False) else 0.0,
            1.0 if context.get('is_last_text', False) else 0.0,
        ])
        
        # Proximity context (simplified)
        features.extend([
            1.0 if element.id in context.get('table_elements', []) else 0.0,
            1.0 if element.id in context.get('figure_elements', []) else 0.0,
        ])
        
        return np.array(features, dtype=np.float32)


class SemanticClassifier(BaseMLModel):
    """ML-based semantic role classifier."""
    
    def __init__(self, model_path: Optional[str] = None):
        """Initialize semantic classifier.
        
        Args:
            model_path: Path to trained model
        """
        super().__init__(model_path)
        self.role_mapping = {i: role for i, role in enumerate(SemanticRole)}
        self.inverse_role_mapping = {role: i for i, role in self.role_mapping.items()}
    
    def predict(self, features: FeatureVector) -> Tuple[SemanticRole, float]:
        """Predict semantic role from features.
        
        Args:
            features: Input features
            
        Returns:
            Tuple of (predicted_role, confidence)
        """
        if not self.is_loaded:
            # Return default prediction
            return SemanticRole.BODY_TEXT, 0.5
        
        # Placeholder for actual ML prediction
        # In real implementation, this would use trained model
        probabilities = self._mock_prediction(features.combined_features)
        
        # Get highest probability prediction
        predicted_class = np.argmax(probabilities)
        confidence = probabilities[predicted_class]
        
        predicted_role = self.role_mapping.get(predicted_class, SemanticRole.BODY_TEXT)
        
        return predicted_role, float(confidence)
    
    def _mock_prediction(self, features: np.ndarray) -> np.ndarray:
        """Mock prediction for demonstration.
        
        Args:
            features: Input features
            
        Returns:
            Mock probability distribution
        """
        # Simple heuristic based on features
        num_classes = len(SemanticRole)
        probabilities = np.random.rand(num_classes)
        
        # Add some logic based on text features
        if len(features) > 0:
            text_length = features[0] if features[0] < 1000 else 100
            
            # Boost title probability for short text
            if text_length < 50:
                title_idx = self.inverse_role_mapping.get(SemanticRole.TITLE, 0)
                probabilities[title_idx] *= 2
            
            # Boost paragraph probability for long text
            if text_length > 200:
                para_idx = self.inverse_role_mapping.get(SemanticRole.PARAGRAPH, 0)
                probabilities[para_idx] *= 3
        
        # Normalize probabilities
        probabilities = probabilities / np.sum(probabilities)
        
        return probabilities
    
    def load_model(self, model_path: str):
        """Load semantic classification model.
        
        Args:
            model_path: Path to model file
        """
        logger.info(f"Loading semantic classification model from {model_path}")
        # Placeholder for actual model loading
        self.is_loaded = True


class SimilarityCalculator:
    """Calculate semantic similarity between elements."""
    
    def __init__(self):
        """Initialize similarity calculator."""
        self.feature_extractor = FeatureExtractor()
    
    def calculate_similarity(
        self, 
        element1: UnifiedElement,
        element2: UnifiedElement,
        context: Dict[str, Any]
    ) -> float:
        """Calculate similarity between two elements.
        
        Args:
            element1: First element
            element2: Second element
            context: Document context
            
        Returns:
            Similarity score between 0 and 1
        """
        # Extract features for both elements
        features1 = self.feature_extractor.extract_features(element1, context)
        features2 = self.feature_extractor.extract_features(element2, context)
        
        # Calculate cosine similarity
        similarity = self._cosine_similarity(
            features1.combined_features,
            features2.combined_features
        )
        
        return float(similarity)
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors.
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            Cosine similarity score
        """
        # Handle zero vectors
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        # Calculate cosine similarity
        dot_product = np.dot(vec1, vec2)
        similarity = dot_product / (norm1 * norm2)
        
        # Ensure result is between 0 and 1
        return max(0.0, min(1.0, (similarity + 1.0) / 2.0))


class RelationshipPredictor(BaseMLModel):
    """ML-based relationship prediction between elements."""
    
    def __init__(self, model_path: Optional[str] = None):
        """Initialize relationship predictor.
        
        Args:
            model_path: Path to trained model
        """
        super().__init__(model_path)
        from ..models.relationship import RelationshipType
        self.relationship_types = list(RelationshipType)
        self.type_mapping = {i: rel_type for i, rel_type in enumerate(self.relationship_types)}
    
    def predict_relationship(
        self,
        element1: UnifiedElement,
        element2: UnifiedElement,
        context: Dict[str, Any]
    ) -> Tuple[Optional[Any], float]:
        """Predict relationship between two elements.
        
        Args:
            element1: First element
            element2: Second element
            context: Document context
            
        Returns:
            Tuple of (relationship_type, confidence) or (None, 0.0)
        """
        # Extract features for both elements
        features1 = self.feature_extractor.extract_features(element1, context)
        features2 = self.feature_extractor.extract_features(element2, context)
        
        # Combine features for relationship prediction
        combined_features = self._combine_element_features(features1, features2)
        
        if not self.is_loaded:
            return None, 0.0
        
        # Predict relationship
        relationship_type, confidence = self.predict(
            FeatureVector(
                text_features=combined_features[:32],
                spatial_features=combined_features[32:64],
                contextual_features=combined_features[64:],
                combined_features=combined_features
            )
        )
        
        return relationship_type, confidence
    
    def _combine_element_features(
        self, 
        features1: FeatureVector, 
        features2: FeatureVector
    ) -> np.ndarray:
        """Combine features from two elements for relationship prediction.
        
        Args:
            features1: Features from first element
            features2: Features from second element
            
        Returns:
            Combined feature vector
        """
        # Concatenate features
        combined = np.concatenate([
            features1.combined_features,
            features2.combined_features
        ])
        
        # Add pairwise features
        pairwise = np.array([
            # Text similarity approximation
            self._cosine_similarity(features1.text_features, features2.text_features),
            # Spatial distance approximation
            self._spatial_distance(features1.spatial_features, features2.spatial_features),
            # Size ratio
            self._size_ratio(features1.spatial_features, features2.spatial_features),
        ])
        
        return np.concatenate([combined, pairwise])
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity."""
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(np.dot(vec1, vec2) / (norm1 * norm2))
    
    def _spatial_distance(self, spatial1: np.ndarray, spatial2: np.ndarray) -> float:
        """Calculate spatial distance between elements."""
        if len(spatial1) >= 4 and len(spatial2) >= 4:
            # Extract center positions
            center1 = spatial1[8:10] if len(spatial1) > 10 else spatial1[:2]
            center2 = spatial2[8:10] if len(spatial2) > 10 else spatial2[:2]
            
            # Calculate Euclidean distance
            distance = np.linalg.norm(center1 - center2)
            return float(distance)
        
        return 1.0  # Maximum distance if no spatial info
    
    def _size_ratio(self, spatial1: np.ndarray, spatial2: np.ndarray) -> float:
        """Calculate size ratio between elements."""
        if len(spatial1) >= 4 and len(spatial2) >= 4:
            # Extract dimensions
            area1 = spatial1[2] * spatial1[3]  # width * height
            area2 = spatial2[2] * spatial2[3]
            
            if area1 > 0 and area2 > 0:
                ratio = min(area1, area2) / max(area1, area2)
                return float(ratio)
        
        return 1.0  # Equal size if no spatial info
    
    def predict(self, features: FeatureVector) -> Tuple[Any, float]:
        """Predict relationship type from features."""
        # Mock prediction
        probabilities = np.random.rand(len(self.relationship_types))
        probabilities = probabilities / np.sum(probabilities)
        
        predicted_idx = np.argmax(probabilities)
        confidence = probabilities[predicted_idx]
        
        predicted_type = self.type_mapping[predicted_idx]
        
        return predicted_type, float(confidence)
    
    def load_model(self, model_path: str):
        """Load relationship prediction model."""
        logger.info(f"Loading relationship prediction model from {model_path}")
        self.is_loaded = True