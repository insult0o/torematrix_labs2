"""
Comprehensive test suite for affine transformations.
Tests all classes and methods in src.torematrix.ui.viewer.transformations.
"""

import pytest
import numpy as np
import math
from unittest.mock import Mock, patch

from src.torematrix.ui.viewer.transformations import (
    TransformationMatrix, 
    AffineTransformation, 
    TransformationBuilder
)
from src.torematrix.utils.geometry import Point, Rect, Size


class TestTransformationMatrix:
    """Test TransformationMatrix class functionality."""
    
    def test_identity_matrix(self):
        """Test identity matrix creation."""
        identity = TransformationMatrix.identity()
        expected = np.eye(3, dtype=np.float64)
        
        assert np.allclose(identity.matrix, expected)
        assert identity.is_identity()
    
    def test_translation_matrix(self):
        """Test translation matrix creation."""
        tx, ty = 10.0, 20.0
        translation = TransformationMatrix.translation(tx, ty)
        
        # Test that translation is applied correctly
        point = (5.0, 15.0)
        result = translation.apply(point)
        
        assert abs(result[0] - 15.0) < 1e-10
        assert abs(result[1] - 35.0) < 1e-10
    
    def test_scaling_matrix(self):
        """Test scaling matrix creation."""
        sx, sy = 2.0, 3.0
        scaling = TransformationMatrix.scaling(sx, sy)
        
        # Test that scaling is applied correctly
        point = (10.0, 20.0)
        result = scaling.apply(point)
        
        assert abs(result[0] - 20.0) < 1e-10
        assert abs(result[1] - 60.0) < 1e-10
    
    def test_rotation_matrix(self):
        """Test rotation matrix creation."""
        angle = math.pi / 2  # 90 degrees
        rotation = TransformationMatrix.rotation(angle)
        
        # Test that rotation is applied correctly
        point = (1.0, 0.0)
        result = rotation.apply(point)
        
        assert abs(result[0]) < 1e-10
        assert abs(result[1] - 1.0) < 1e-10
    
    def test_shearing_matrix(self):
        """Test shearing matrix creation."""
        shx, shy = 0.5, 0.3
        shearing = TransformationMatrix.shearing(shx, shy)
        
        # Test that shearing is applied correctly
        point = (10.0, 20.0)
        result = shearing.apply(point)
        
        expected_x = 10.0 + shx * 20.0
        expected_y = 20.0 + shy * 10.0
        
        assert abs(result[0] - expected_x) < 1e-10
        assert abs(result[1] - expected_y) < 1e-10
    
    def test_matrix_composition(self):
        """Test matrix composition."""
        translation = TransformationMatrix.translation(10.0, 20.0)
        scaling = TransformationMatrix.scaling(2.0, 3.0)
        
        # Compose transformations
        composed = translation.compose(scaling)
        
        # Test on a point
        point = (5.0, 10.0)
        result = composed.apply(point)
        
        # Should scale first, then translate
        expected_x = 5.0 * 2.0 + 10.0  # 20.0
        expected_y = 10.0 * 3.0 + 20.0  # 50.0
        
        assert abs(result[0] - expected_x) < 1e-10
        assert abs(result[1] - expected_y) < 1e-10
    
    def test_matrix_inverse(self):
        """Test matrix inverse calculation."""
        # Create a non-trivial transformation
        translation = TransformationMatrix.translation(10.0, 20.0)
        scaling = TransformationMatrix.scaling(2.0, 3.0)
        rotation = TransformationMatrix.rotation(math.pi / 4)
        
        composed = translation.compose(scaling).compose(rotation)
        
        # Calculate inverse
        inverse = composed.inverse()
        
        # Test that inverse works correctly
        point = (100.0, 200.0)
        transformed = composed.apply(point)
        inverse_transformed = inverse.apply(transformed)
        
        assert abs(inverse_transformed[0] - point[0]) < 1e-10
        assert abs(inverse_transformed[1] - point[1]) < 1e-10
    
    def test_matrix_determinant(self):
        """Test determinant calculation."""
        # Identity matrix should have determinant 1
        identity = TransformationMatrix.identity()
        assert abs(identity.determinant() - 1.0) < 1e-10
        
        # Scaling matrix determinant should be product of scale factors
        scaling = TransformationMatrix.scaling(2.0, 3.0)
        assert abs(scaling.determinant() - 6.0) < 1e-10
        
        # Rotation matrix should have determinant 1
        rotation = TransformationMatrix.rotation(math.pi / 4)
        assert abs(rotation.determinant() - 1.0) < 1e-10
    
    def test_matrix_invertibility(self):
        """Test invertibility checks."""
        # Identity matrix is invertible
        identity = TransformationMatrix.identity()
        assert identity.is_invertible()
        
        # Scaling matrix with non-zero scale is invertible
        scaling = TransformationMatrix.scaling(2.0, 3.0)
        assert scaling.is_invertible()
        
        # Create a non-invertible matrix (zero determinant)
        singular_matrix = np.array([
            [1.0, 0.0, 0.0],
            [2.0, 0.0, 0.0],
            [0.0, 0.0, 1.0]
        ])
        singular = TransformationMatrix(singular_matrix)
        assert not singular.is_invertible()
    
    def test_batch_point_transformation(self):
        """Test efficient batch point transformation."""
        scaling = TransformationMatrix.scaling(2.0, 3.0)
        
        points = [(1.0, 2.0), (3.0, 4.0), (5.0, 6.0)]
        results = scaling.apply_to_points(points)
        
        expected = [(2.0, 6.0), (6.0, 12.0), (10.0, 18.0)]
        
        assert len(results) == len(expected)
        for result, expected_point in zip(results, expected):
            assert abs(result[0] - expected_point[0]) < 1e-10
            assert abs(result[1] - expected_point[1]) < 1e-10
    
    def test_matrix_extraction(self):
        """Test component extraction from matrix."""
        # Test translation extraction
        translation = TransformationMatrix.translation(10.0, 20.0)
        tx, ty = translation.extract_translation()
        assert abs(tx - 10.0) < 1e-10
        assert abs(ty - 20.0) < 1e-10
        
        # Test scale extraction
        scaling = TransformationMatrix.scaling(2.0, 3.0)
        sx, sy = scaling.extract_scale()
        assert abs(sx - 2.0) < 1e-10
        assert abs(sy - 3.0) < 1e-10
        
        # Test rotation extraction
        angle = math.pi / 4
        rotation = TransformationMatrix.rotation(angle)
        extracted_angle = rotation.extract_rotation()
        assert abs(extracted_angle - angle) < 1e-10
    
    def test_matrix_equality(self):
        """Test matrix equality comparison."""
        m1 = TransformationMatrix.translation(10.0, 20.0)
        m2 = TransformationMatrix.translation(10.0, 20.0)
        m3 = TransformationMatrix.translation(10.1, 20.0)
        
        assert m1 == m2
        assert m1 != m3
    
    def test_matrix_string_representation(self):
        """Test string representation of matrix."""
        matrix = TransformationMatrix.identity()
        
        str_repr = str(matrix)
        assert "TransformationMatrix" in str_repr
        
        repr_str = repr(matrix)
        assert "TransformationMatrix" in repr_str
    
    @patch('src.torematrix.ui.viewer.transformations.QT_AVAILABLE', True)
    def test_qt_transform_conversion(self):
        """Test conversion to Qt QTransform."""
        # Mock QTransform for testing
        mock_qtransform = Mock()
        
        with patch('src.torematrix.ui.viewer.transformations.QTransform', return_value=mock_qtransform):
            matrix = TransformationMatrix.translation(10.0, 20.0)
            qt_transform = matrix.to_qtransform()
            
            assert qt_transform == mock_qtransform
    
    def test_matrix_validation(self):
        """Test matrix validation."""
        # Valid matrix
        valid_matrix = np.array([
            [1.0, 0.0, 10.0],
            [0.0, 1.0, 20.0],
            [0.0, 0.0, 1.0]
        ])
        
        matrix = TransformationMatrix(valid_matrix)
        assert matrix.matrix.shape == (3, 3)
        assert matrix.matrix.dtype == np.float64
        
        # Test invalid matrix dimensions
        with pytest.raises(AssertionError):
            invalid_matrix = np.array([[1.0, 0.0], [0.0, 1.0]])
            TransformationMatrix(invalid_matrix)


class TestAffineTransformation:
    """Test AffineTransformation class functionality."""
    
    def test_identity_transformation(self):
        """Test identity transformation."""
        identity = AffineTransformation.identity()
        
        point = Point(10.0, 20.0)
        result = identity.transform_point_obj(point)
        
        assert abs(result.x - 10.0) < 1e-10
        assert abs(result.y - 20.0) < 1e-10
        assert identity.is_identity()
    
    def test_translation_transformation(self):
        """Test translation transformation."""
        translation = AffineTransformation.translation(10.0, 20.0)
        
        # Test tuple input
        result = translation.transform_point(5.0, 15.0)
        assert abs(result[0] - 15.0) < 1e-10
        assert abs(result[1] - 35.0) < 1e-10
        
        # Test Point object input
        point = Point(5.0, 15.0)
        result_point = translation.transform_point_obj(point)
        assert abs(result_point.x - 15.0) < 1e-10
        assert abs(result_point.y - 35.0) < 1e-10
    
    def test_scaling_transformation(self):
        """Test scaling transformation."""
        scaling = AffineTransformation.scaling(2.0, 3.0)
        
        point = Point(10.0, 20.0)
        result = scaling.transform_point_obj(point)
        
        assert abs(result.x - 20.0) < 1e-10
        assert abs(result.y - 60.0) < 1e-10
        
        # Test uniform scaling
        uniform_scaling = AffineTransformation.uniform_scaling(2.0)
        result_uniform = uniform_scaling.transform_point_obj(point)
        assert abs(result_uniform.x - 20.0) < 1e-10
        assert abs(result_uniform.y - 40.0) < 1e-10
    
    def test_rotation_transformation(self):
        """Test rotation transformation."""
        rotation = AffineTransformation.rotation(math.pi / 2)
        
        point = Point(1.0, 0.0)
        result = rotation.transform_point_obj(point)
        
        assert abs(result.x) < 1e-10
        assert abs(result.y - 1.0) < 1e-10
        
        # Test rotation in degrees
        rotation_deg = AffineTransformation.rotation_degrees(90.0)
        result_deg = rotation_deg.transform_point_obj(point)
        assert abs(result_deg.x) < 1e-10
        assert abs(result_deg.y - 1.0) < 1e-10
    
    def test_rectangle_transformation(self):
        """Test rectangle transformation."""
        scaling = AffineTransformation.scaling(2.0, 3.0)
        
        rect = Rect(0.0, 0.0, 10.0, 20.0)
        result = scaling.transform_rect(rect)
        
        # Check that all corners are transformed correctly
        assert abs(result.x - 0.0) < 1e-10
        assert abs(result.y - 0.0) < 1e-10
        assert abs(result.width - 20.0) < 1e-10
        assert abs(result.height - 60.0) < 1e-10
    
    def test_batch_point_transformation(self):
        """Test batch point transformation."""
        scaling = AffineTransformation.scaling(2.0, 3.0)
        
        # Test with tuples
        points = [(1.0, 2.0), (3.0, 4.0), (5.0, 6.0)]
        results = scaling.transform_points(points)
        
        expected = [(2.0, 6.0), (6.0, 12.0), (10.0, 18.0)]
        for result, expected_point in zip(results, expected):
            assert abs(result[0] - expected_point[0]) < 1e-10
            assert abs(result[1] - expected_point[1]) < 1e-10
        
        # Test with Point objects
        point_objects = [Point(1.0, 2.0), Point(3.0, 4.0), Point(5.0, 6.0)]
        point_results = scaling.transform_point_objects(point_objects)
        
        for result, expected_point in zip(point_results, expected):
            assert abs(result.x - expected_point[0]) < 1e-10
            assert abs(result.y - expected_point[1]) < 1e-10
    
    def test_transformation_composition(self):
        """Test transformation composition."""
        translation = AffineTransformation.translation(10.0, 20.0)
        scaling = AffineTransformation.scaling(2.0, 3.0)
        
        # Compose transformations
        composed = translation.compose(scaling)
        
        point = Point(5.0, 10.0)
        result = composed.transform_point_obj(point)
        
        # Should scale first, then translate
        expected_x = 5.0 * 2.0 + 10.0  # 20.0
        expected_y = 10.0 * 3.0 + 20.0  # 50.0
        
        assert abs(result.x - expected_x) < 1e-10
        assert abs(result.y - expected_y) < 1e-10
        
        # Test prepend (reverse order)
        prepended = translation.prepend(scaling)
        result_prepend = prepended.transform_point_obj(point)
        
        # Should translate first, then scale
        expected_x_prepend = (5.0 + 10.0) * 2.0  # 30.0
        expected_y_prepend = (10.0 + 20.0) * 3.0  # 90.0
        
        assert abs(result_prepend.x - expected_x_prepend) < 1e-10
        assert abs(result_prepend.y - expected_y_prepend) < 1e-10
    
    def test_transformation_inverse(self):
        """Test transformation inverse."""
        # Create a complex transformation
        translation = AffineTransformation.translation(10.0, 20.0)
        scaling = AffineTransformation.scaling(2.0, 3.0)
        rotation = AffineTransformation.rotation(math.pi / 4)
        
        composed = translation.compose(scaling).compose(rotation)
        inverse = composed.inverse()
        
        # Test that inverse works correctly
        point = Point(100.0, 200.0)
        transformed = composed.transform_point_obj(point)
        inverse_transformed = inverse.transform_point_obj(transformed)
        
        assert abs(inverse_transformed.x - point.x) < 1e-10
        assert abs(inverse_transformed.y - point.y) < 1e-10
    
    def test_transformation_from_points(self):
        """Test creating transformation from corresponding points."""
        # Create transformation from 3 point pairs
        src_points = [Point(0.0, 0.0), Point(1.0, 0.0), Point(0.0, 1.0)]
        dst_points = [Point(10.0, 20.0), Point(12.0, 23.0), Point(7.0, 23.0)]
        
        transformation = AffineTransformation.from_points(src_points, dst_points)
        
        # Test that source points map to destination points
        for src, dst in zip(src_points, dst_points):
            result = transformation.transform_point_obj(src)
            assert abs(result.x - dst.x) < 1e-10
            assert abs(result.y - dst.y) < 1e-10
    
    def test_transformation_properties(self):
        """Test transformation property extraction."""
        # Create transformation with known properties
        translation = AffineTransformation.translation(10.0, 20.0)
        
        # Test translation extraction
        extracted_translation = translation.extract_translation()
        assert abs(extracted_translation.x - 10.0) < 1e-10
        assert abs(extracted_translation.y - 20.0) < 1e-10
        
        # Test scale extraction
        scaling = AffineTransformation.scaling(2.0, 3.0)
        extracted_scale = scaling.extract_scale()
        assert abs(extracted_scale.width - 2.0) < 1e-10
        assert abs(extracted_scale.height - 3.0) < 1e-10
        
        # Test rotation extraction
        angle = math.pi / 4
        rotation = AffineTransformation.rotation(angle)
        extracted_rotation = rotation.extract_rotation()
        assert abs(extracted_rotation - angle) < 1e-10
        
        extracted_rotation_deg = rotation.extract_rotation_degrees()
        assert abs(extracted_rotation_deg - 45.0) < 1e-10
    
    def test_transformation_determinant(self):
        """Test determinant calculation with caching."""
        scaling = AffineTransformation.scaling(2.0, 3.0)
        
        # First call should calculate determinant
        det1 = scaling.determinant()
        assert abs(det1 - 6.0) < 1e-10
        
        # Second call should use cached value
        det2 = scaling.determinant()
        assert abs(det2 - 6.0) < 1e-10
        assert det1 == det2
    
    def test_transformation_cache_invalidation(self):
        """Test cache invalidation."""
        transformation = AffineTransformation.scaling(2.0, 3.0)
        
        # Calculate cached values
        _ = transformation.determinant()
        _ = transformation.inverse()
        
        # Invalidate cache
        transformation.invalidate_cache()
        
        # Should recalculate (test that it doesn't crash)
        det = transformation.determinant()
        inv = transformation.inverse()
        
        assert abs(det - 6.0) < 1e-10
        assert inv is not None
    
    def test_transformation_equality(self):
        """Test transformation equality."""
        t1 = AffineTransformation.translation(10.0, 20.0)
        t2 = AffineTransformation.translation(10.0, 20.0)
        t3 = AffineTransformation.translation(10.1, 20.0)
        
        assert t1 == t2
        assert t1 != t3
    
    def test_transformation_string_representation(self):
        """Test string representation."""
        transformation = AffineTransformation.identity()
        
        str_repr = str(transformation)
        assert "AffineTransformation" in str_repr
        
        repr_str = repr(transformation)
        assert "AffineTransformation" in repr_str


class TestTransformationBuilder:
    """Test TransformationBuilder class functionality."""
    
    def test_builder_identity(self):
        """Test builder starts with identity."""
        builder = TransformationBuilder()
        transformation = builder.build()
        
        assert transformation.is_identity()
    
    def test_builder_chaining(self):
        """Test builder method chaining."""
        builder = TransformationBuilder()
        
        # Chain operations
        transformation = (builder
                         .translate(10.0, 20.0)
                         .scale(2.0, 3.0)
                         .rotate(math.pi / 4)
                         .build())
        
        # Test that transformation is applied correctly
        point = Point(1.0, 0.0)
        result = transformation.transform_point_obj(point)
        
        # Should be non-trivial transformation
        assert not transformation.is_identity()
        assert result.x != point.x or result.y != point.y
    
    def test_builder_individual_operations(self):
        """Test individual builder operations."""
        builder = TransformationBuilder()
        
        # Test translation
        transform = builder.translate(10.0, 20.0).build()
        point = Point(5.0, 10.0)
        result = transform.transform_point_obj(point)
        assert abs(result.x - 15.0) < 1e-10
        assert abs(result.y - 30.0) < 1e-10
        
        # Reset and test scaling
        builder.reset()
        transform = builder.scale(2.0, 3.0).build()
        result = transform.transform_point_obj(point)
        assert abs(result.x - 10.0) < 1e-10
        assert abs(result.y - 30.0) < 1e-10
        
        # Reset and test uniform scaling
        builder.reset()
        transform = builder.uniform_scale(2.0).build()
        result = transform.transform_point_obj(point)
        assert abs(result.x - 10.0) < 1e-10
        assert abs(result.y - 20.0) < 1e-10
        
        # Reset and test rotation
        builder.reset()
        transform = builder.rotate(math.pi / 2).build()
        unit_point = Point(1.0, 0.0)
        result = transform.transform_point_obj(unit_point)
        assert abs(result.x) < 1e-10
        assert abs(result.y - 1.0) < 1e-10
        
        # Reset and test rotation in degrees
        builder.reset()
        transform = builder.rotate_degrees(90.0).build()
        result = transform.transform_point_obj(unit_point)
        assert abs(result.x) < 1e-10
        assert abs(result.y - 1.0) < 1e-10
    
    def test_builder_transform_around_point(self):
        """Test transformation around a specific point."""
        builder = TransformationBuilder()
        center = Point(10.0, 20.0)
        
        # Scale around center
        transform = builder.scale_around_point(center, 2.0, 3.0).build()
        
        # Center should remain unchanged
        result_center = transform.transform_point_obj(center)
        assert abs(result_center.x - center.x) < 1e-10
        assert abs(result_center.y - center.y) < 1e-10
        
        # Point offset from center should be scaled
        offset_point = Point(15.0, 25.0)  # 5 units right, 5 units up from center
        result_offset = transform.transform_point_obj(offset_point)
        expected_x = center.x + (offset_point.x - center.x) * 2.0  # 20.0
        expected_y = center.y + (offset_point.y - center.y) * 3.0  # 35.0
        assert abs(result_offset.x - expected_x) < 1e-10
        assert abs(result_offset.y - expected_y) < 1e-10
    
    def test_builder_rotate_around_point(self):
        """Test rotation around a specific point."""
        builder = TransformationBuilder()
        center = Point(10.0, 20.0)
        
        # Rotate 90 degrees around center
        transform = builder.rotate_around_point(center, math.pi / 2).build()
        
        # Center should remain unchanged
        result_center = transform.transform_point_obj(center)
        assert abs(result_center.x - center.x) < 1e-10
        assert abs(result_center.y - center.y) < 1e-10
        
        # Point to the right of center should move up
        right_point = Point(15.0, 20.0)  # 5 units right of center
        result_right = transform.transform_point_obj(right_point)
        expected_x = center.x  # Should be at same x as center
        expected_y = center.y + 5.0  # Should be 5 units up from center
        assert abs(result_right.x - expected_x) < 1e-10
        assert abs(result_right.y - expected_y) < 1e-10
    
    def test_builder_reset(self):
        """Test builder reset functionality."""
        builder = TransformationBuilder()
        
        # Apply some transformations
        builder.translate(10.0, 20.0).scale(2.0, 3.0).rotate(math.pi / 4)
        
        # Reset
        builder.reset()
        
        # Should be back to identity
        transform = builder.build()
        assert transform.is_identity()
    
    def test_builder_complex_transformation(self):
        """Test complex transformation building."""
        builder = TransformationBuilder()
        
        # Create a complex transformation
        center = Point(100.0, 200.0)
        transform = (builder
                    .translate(50.0, 100.0)
                    .scale_around_point(center, 2.0, 2.0)
                    .rotate_around_point(center, math.pi / 4)
                    .translate(-25.0, -50.0)
                    .build())
        
        # Test that it's a non-trivial transformation
        assert not transform.is_identity()
        assert transform.is_invertible()
        
        # Test that it can be inverted
        inverse = transform.inverse()
        
        # Test round-trip
        test_point = Point(150.0, 250.0)
        transformed = transform.transform_point_obj(test_point)
        back_transformed = inverse.transform_point_obj(transformed)
        
        assert abs(back_transformed.x - test_point.x) < 1e-10
        assert abs(back_transformed.y - test_point.y) < 1e-10


class TestTransformationPerformance:
    """Test transformation performance characteristics."""
    
    def test_batch_transformation_performance(self):
        """Test that batch transformations are efficient."""
        scaling = AffineTransformation.scaling(2.0, 3.0)
        
        # Create many points
        points = [(i * 0.1, i * 0.2) for i in range(1000)]
        
        # Batch transformation should complete without issues
        results = scaling.transform_points(points)
        
        # Verify correctness
        assert len(results) == len(points)
        for i, (result, original) in enumerate(zip(results, points)):
            expected_x = original[0] * 2.0
            expected_y = original[1] * 3.0
            assert abs(result[0] - expected_x) < 1e-10
            assert abs(result[1] - expected_y) < 1e-10
    
    def test_transformation_caching(self):
        """Test that transformation caching works correctly."""
        transformation = AffineTransformation.scaling(2.0, 3.0)
        
        # First inverse calculation
        inv1 = transformation.inverse()
        
        # Second inverse calculation should use cache
        inv2 = transformation.inverse()
        
        # Should be the same object (cached)
        assert inv1.matrix is inv2.matrix
        
        # Test determinant caching
        det1 = transformation.determinant()
        det2 = transformation.determinant()
        
        assert det1 == det2
    
    def test_matrix_operations_precision(self):
        """Test numerical precision of matrix operations."""
        # Create transformation with known inverse
        angle = math.pi / 6  # 30 degrees
        rotation = AffineTransformation.rotation(angle)
        
        # Apply rotation and its inverse
        point = Point(1.0, 0.0)
        rotated = rotation.transform_point_obj(point)
        back_rotated = rotation.inverse().transform_point_obj(rotated)
        
        # Should be very close to original
        assert abs(back_rotated.x - point.x) < 1e-14
        assert abs(back_rotated.y - point.y) < 1e-14
    
    def test_transformation_edge_cases(self):
        """Test transformation edge cases."""
        # Very small scaling
        small_scale = AffineTransformation.scaling(1e-10, 1e-10)
        assert small_scale.is_invertible()
        
        # Very large scaling
        large_scale = AffineTransformation.scaling(1e10, 1e10)
        assert large_scale.is_invertible()
        
        # Zero scaling (should not be invertible)
        zero_scale = AffineTransformation.scaling(0.0, 1.0)
        assert not zero_scale.is_invertible()
        
        # Test with very small rotation
        small_rotation = AffineTransformation.rotation(1e-10)
        assert small_rotation.is_invertible()
        
        # Test with large rotation
        large_rotation = AffineTransformation.rotation(100.0 * math.pi)
        assert large_rotation.is_invertible()


class TestTransformationIntegration:
    """Test integration with other system components."""
    
    def test_coordinate_system_integration(self):
        """Test integration with coordinate system."""
        # Create transformation that mimics viewer coordinate mapping
        document_size = Size(1000.0, 800.0)
        viewer_size = Size(500.0, 400.0)
        
        # Scale to fit document in viewer
        scale_x = viewer_size.width / document_size.width
        scale_y = viewer_size.height / document_size.height
        scale = min(scale_x, scale_y)  # Uniform scaling to fit
        
        # Center in viewer
        scaled_width = document_size.width * scale
        scaled_height = document_size.height * scale
        offset_x = (viewer_size.width - scaled_width) / 2
        offset_y = (viewer_size.height - scaled_height) / 2
        
        # Create transformation
        transform = (TransformationBuilder()
                    .scale(scale, scale)
                    .translate(offset_x, offset_y)
                    .build())
        
        # Test that document bounds map to viewer bounds
        doc_rect = Rect(0.0, 0.0, document_size.width, document_size.height)
        viewer_rect = transform.transform_rect(doc_rect)
        
        # Should be centered in viewer
        assert viewer_rect.x >= 0.0
        assert viewer_rect.y >= 0.0
        assert viewer_rect.x + viewer_rect.width <= viewer_size.width
        assert viewer_rect.y + viewer_rect.height <= viewer_size.height
    
    def test_qt_integration(self):
        """Test Qt integration capabilities."""
        transformation = AffineTransformation.translation(10.0, 20.0)
        
        # Test that Qt conversion exists (even if mocked)
        try:
            qt_transform = transformation.to_qtransform()
            # If it doesn't raise an import error, that's good
        except ImportError:
            # Expected if PyQt6 is not available
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])