"""
Unit tests for the animation system and custom shapes.
Tests animation management, easing functions, and shape rendering.
"""
import pytest
import math
import time
from unittest.mock import Mock, MagicMock, patch

from PyQt6.QtCore import QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPolygonF

from src.torematrix.ui.viewer.animations import (
    AnimationManager, AnimationType, EasingType, AnimationConfig,
    PropertyAnimation, AnimationGroup, CustomEasingCurve,
    AnimationMixin, animate_element_selection
)
from src.torematrix.ui.viewer.shapes import (
    ShapeFactory, ShapeType, ArrowShape, CalloutShape, PolygonShape,
    BezierShape, ShapeStyle, ArrowParameters, CalloutParameters,
    PolygonParameters, BezierParameters, CustomShapeRenderer,
    ArrowStyle, CalloutStyle
)
from src.torematrix.ui.viewer.coordinates import Point, Rectangle


class MockAnimationTarget:
    """Mock target for animations."""
    
    def __init__(self):
        self.properties = {}
    
    def set_animation_property(self, property_name: str, value) -> None:
        self.properties[property_name] = value
    
    def get_animation_property(self, property_name: str):
        return self.properties.get(property_name, 0)


class TestAnimationConfig:
    """Test animation configuration."""
    
    def test_default_config(self):
        """Test default animation configuration."""
        config = AnimationConfig()
        
        assert config.duration == 300
        assert config.easing == EasingType.EASE_OUT
        assert config.delay == 0
        assert config.loop_count == 1
        assert not config.auto_reverse
        assert not config.performance_mode
    
    def test_custom_config(self):
        """Test custom animation configuration."""
        config = AnimationConfig(
            duration=500,
            easing=EasingType.EASE_IN_OUT,
            delay=100,
            loop_count=3,
            auto_reverse=True,
            performance_mode=True
        )
        
        assert config.duration == 500
        assert config.easing == EasingType.EASE_IN_OUT
        assert config.delay == 100
        assert config.loop_count == 3
        assert config.auto_reverse
        assert config.performance_mode


class TestCustomEasingCurve:
    """Test custom easing curve implementations."""
    
    def test_ease_in_back(self):
        """Test ease in back curve."""
        # Test at boundaries
        assert CustomEasingCurve.ease_in_back(0.0) == 0.0
        assert CustomEasingCurve.ease_in_back(1.0) == 1.0
        
        # Test intermediate value
        mid_value = CustomEasingCurve.ease_in_back(0.5)
        assert isinstance(mid_value, float)
    
    def test_ease_out_back(self):
        """Test ease out back curve."""
        assert CustomEasingCurve.ease_out_back(0.0) == 0.0
        assert CustomEasingCurve.ease_out_back(1.0) == 1.0
        
        mid_value = CustomEasingCurve.ease_out_back(0.5)
        assert isinstance(mid_value, float)
    
    def test_ease_in_out_back(self):
        """Test ease in-out back curve."""
        assert CustomEasingCurve.ease_in_out_back(0.0) == 0.0
        assert CustomEasingCurve.ease_in_out_back(1.0) == 1.0
        
        mid_value = CustomEasingCurve.ease_in_out_back(0.5)
        assert isinstance(mid_value, float)
    
    def test_ease_out_elastic(self):
        """Test ease out elastic curve."""
        # Boundary conditions
        assert CustomEasingCurve.ease_out_elastic(0.0) == 0.0
        assert CustomEasingCurve.ease_out_elastic(1.0) == 1.0
        
        # Test with different amplitudes and periods
        value1 = CustomEasingCurve.ease_out_elastic(0.5, 1.0, 0.3)
        value2 = CustomEasingCurve.ease_out_elastic(0.5, 2.0, 0.5)
        
        assert isinstance(value1, float)
        assert isinstance(value2, float)
    
    def test_ease_out_bounce(self):
        """Test ease out bounce curve."""
        assert CustomEasingCurve.ease_out_bounce(0.0) == 0.0
        assert abs(CustomEasingCurve.ease_out_bounce(1.0) - 1.0) < 0.001  # Close to 1.0
        
        # Test different segments
        early = CustomEasingCurve.ease_out_bounce(0.2)
        mid = CustomEasingCurve.ease_out_bounce(0.5)
        late = CustomEasingCurve.ease_out_bounce(0.8)
        
        assert all(isinstance(v, float) for v in [early, mid, late])


class TestPropertyAnimation:
    """Test property animation functionality."""
    
    def test_animation_creation(self):
        """Test property animation creation."""
        target = MockAnimationTarget()
        animation = PropertyAnimation(target, "opacity")
        
        assert animation.target == target
        assert animation.property_name == "opacity"
        assert animation.custom_easing is None
    
    def test_set_custom_easing(self):
        """Test setting custom easing function."""
        target = MockAnimationTarget()
        animation = PropertyAnimation(target, "opacity")
        
        easing_func = lambda t: t * t
        animation.set_custom_easing(easing_func)
        
        assert animation.custom_easing == easing_func
    
    def test_interpolation_numeric(self):
        """Test numeric value interpolation."""
        target = MockAnimationTarget()
        animation = PropertyAnimation(target, "opacity")
        
        result = animation.interpolated(0.0, 100.0, 0.5)
        assert result == 50.0
    
    def test_interpolation_point(self):
        """Test Point value interpolation."""
        target = MockAnimationTarget()
        animation = PropertyAnimation(target, "position")
        
        start = Point(0, 0)
        end = Point(100, 200)
        result = animation.interpolated(start, end, 0.5)
        
        assert isinstance(result, Point)
        assert result.x == 50
        assert result.y == 100
    
    def test_interpolation_color(self):
        """Test QColor value interpolation."""
        target = MockAnimationTarget()
        animation = PropertyAnimation(target, "color")
        
        start = QColor(0, 0, 0, 255)
        end = QColor(255, 255, 255, 255)
        result = animation.interpolated(start, end, 0.5)
        
        assert isinstance(result, QColor)
        assert result.red() == 127
        assert result.green() == 127
        assert result.blue() == 127
        assert result.alpha() == 255


class TestAnimationGroup:
    """Test animation group functionality."""
    
    def test_parallel_group_creation(self):
        """Test parallel animation group creation."""
        group = AnimationGroup("test_group", parallel=True)
        
        assert group.name == "test_group"
        assert len(group.animations) == 0
        assert group.group is not None
    
    def test_sequential_group_creation(self):
        """Test sequential animation group creation."""
        group = AnimationGroup("test_group", parallel=False)
        
        assert group.name == "test_group"
        assert len(group.animations) == 0
        assert group.group is not None
    
    def test_add_animation(self):
        """Test adding animation to group."""
        group = AnimationGroup("test_group")
        target = MockAnimationTarget()
        animation = PropertyAnimation(target, "opacity")
        
        group.add_animation(animation)
        
        assert len(group.animations) == 1
        assert group.animations[0] == animation


class TestAnimationManager:
    """Test main animation manager functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.manager = AnimationManager()
    
    def test_initialization(self):
        """Test manager initialization."""
        assert len(self.manager.active_animations) == 0
        assert len(self.manager.animation_groups) == 0
        assert self.manager.global_config is not None
        assert not self.manager.performance_mode
        assert self.manager.animations_enabled
        assert len(self.manager.animation_presets) > 0
        assert self.manager.max_concurrent_animations == 20
    
    def test_animation_presets(self):
        """Test predefined animation presets."""
        presets = self.manager.animation_presets
        
        required_presets = ["fast", "normal", "slow", "bounce", "elastic", "selection", "hover"]
        for preset in required_presets:
            assert preset in presets
            assert isinstance(presets[preset], AnimationConfig)
        
        # Test preset differences
        fast = presets["fast"]
        slow = presets["slow"]
        assert fast.duration < slow.duration
    
    def test_animate_property(self):
        """Test property animation."""
        target = MockAnimationTarget()
        config = AnimationConfig(duration=100)
        
        animation_id = self.manager.animate_property(
            target, "opacity", 0.0, 1.0, config
        )
        
        assert animation_id != ""
        assert animation_id in self.manager.active_animations
    
    def test_animate_selection(self):
        """Test selection state animation."""
        target = MockAnimationTarget()
        
        # Animate to selected
        animation_id = self.manager.animate_selection(target, True)
        assert animation_id != ""
        
        # Animate to unselected
        animation_id = self.manager.animate_selection(target, False)
        assert animation_id != ""
    
    def test_animate_hover(self):
        """Test hover state animation."""
        target = MockAnimationTarget()
        
        # Animate to hover
        animation_id = self.manager.animate_hover(target, True)
        assert animation_id != ""
        
        # Animate from hover
        animation_id = self.manager.animate_hover(target, False)
        assert animation_id != ""
    
    def test_animate_fade_in(self):
        """Test fade in animation."""
        target = MockAnimationTarget()
        
        animation_id = self.manager.animate_fade_in(target)
        assert animation_id != ""
    
    def test_animate_fade_out(self):
        """Test fade out animation."""
        target = MockAnimationTarget()
        
        animation_id = self.manager.animate_fade_out(target)
        assert animation_id != ""
    
    def test_animate_scale(self):
        """Test scale animation."""
        target = MockAnimationTarget()
        
        animation_id = self.manager.animate_scale(target, 1.0, 2.0)
        assert animation_id != ""
    
    def test_animate_translate(self):
        """Test translation animation."""
        target = MockAnimationTarget()
        
        animation_id = self.manager.animate_translate(
            target, Point(0, 0), Point(100, 100)
        )
        assert animation_id != ""
    
    def test_animate_color(self):
        """Test color animation."""
        target = MockAnimationTarget()
        
        animation_id = self.manager.animate_color(
            target, QColor(255, 0, 0), QColor(0, 255, 0)
        )
        assert animation_id != ""
    
    def test_create_animation_sequence(self):
        """Test creating sequential animation group."""
        group = self.manager.create_animation_sequence("test_sequence")
        
        assert group.name == "test_sequence"
        assert "test_sequence" in self.manager.animation_groups
    
    def test_create_animation_parallel(self):
        """Test creating parallel animation group."""
        group = self.manager.create_animation_parallel("test_parallel")
        
        assert group.name == "test_parallel"
        assert "test_parallel" in self.manager.animation_groups
    
    def test_stop_animation(self):
        """Test stopping specific animation."""
        target = MockAnimationTarget()
        animation_id = self.manager.animate_property(target, "opacity", 0.0, 1.0)
        
        assert animation_id in self.manager.active_animations
        
        result = self.manager.stop_animation(animation_id)
        assert result
        assert animation_id not in self.manager.active_animations
    
    def test_stop_all_animations(self):
        """Test stopping all animations."""
        target = MockAnimationTarget()
        
        # Create multiple animations
        id1 = self.manager.animate_property(target, "opacity", 0.0, 1.0)
        id2 = self.manager.animate_property(target, "scale", 1.0, 2.0)
        
        assert len(self.manager.active_animations) == 2
        
        self.manager.stop_all_animations()
        assert len(self.manager.active_animations) == 0
    
    def test_set_performance_mode(self):
        """Test setting performance mode."""
        assert not self.manager.performance_mode
        
        self.manager.set_performance_mode(True)
        assert self.manager.performance_mode
        
        # Performance mode should reduce durations
        normal_preset = self.manager.animation_presets["normal"]
        assert normal_preset.performance_mode
    
    def test_set_animations_enabled(self):
        """Test enabling/disabling animations."""
        assert self.manager.animations_enabled
        
        self.manager.set_animations_enabled(False)
        assert not self.manager.animations_enabled
        
        # Should stop all active animations
        assert len(self.manager.active_animations) == 0
    
    def test_register_animation_preset(self):
        """Test registering custom animation preset."""
        custom_config = AnimationConfig(duration=750, easing=EasingType.BOUNCE)
        
        self.manager.register_animation_preset("custom", custom_config)
        
        assert "custom" in self.manager.animation_presets
        assert self.manager.animation_presets["custom"] == custom_config
    
    def test_get_animation_preset(self):
        """Test getting animation preset."""
        preset = self.manager.get_animation_preset("normal")
        
        assert preset is not None
        assert isinstance(preset, AnimationConfig)
        
        # Non-existent preset
        assert self.manager.get_animation_preset("nonexistent") is None


class TestAnimationMixin:
    """Test animation mixin functionality."""
    
    def test_mixin_initialization(self):
        """Test mixin initialization."""
        
        class TestWidget(AnimationMixin):
            def __init__(self):
                super().__init__()
        
        widget = TestWidget()
        
        assert widget.animation_manager is None
        assert len(widget.animated_properties) == 0
    
    def test_set_animation_manager(self):
        """Test setting animation manager."""
        
        class TestWidget(AnimationMixin):
            def __init__(self):
                super().__init__()
        
        widget = TestWidget()
        manager = AnimationManager()
        
        widget.set_animation_manager(manager)
        
        assert widget.animation_manager == manager
    
    def test_set_animation_property(self):
        """Test setting animated property."""
        
        class TestWidget(AnimationMixin):
            def __init__(self):
                super().__init__()
                self.applied_properties = {}
            
            def _apply_animation_property(self, property_name: str, value) -> None:
                self.applied_properties[property_name] = value
        
        widget = TestWidget()
        
        widget.set_animation_property("opacity", 0.5)
        
        assert widget.animated_properties["opacity"] == 0.5
        assert widget.applied_properties["opacity"] == 0.5
    
    def test_animate_to(self):
        """Test animating to target value."""
        
        class TestWidget(AnimationMixin):
            def __init__(self):
                super().__init__()
            
            def _apply_animation_property(self, property_name: str, value) -> None:
                pass
        
        widget = TestWidget()
        manager = AnimationManager()
        widget.set_animation_manager(manager)
        widget.set_animation_property("opacity", 0.0)
        
        animation_id = widget.animate_to("opacity", 1.0)
        
        assert animation_id != ""


# Shape Tests

class TestShapeStyle:
    """Test shape styling configuration."""
    
    def test_default_style(self):
        """Test default shape style."""
        style = ShapeStyle()
        
        assert style.fill_color.alpha() == 128  # Semi-transparent white
        assert style.border_color.alpha() == 255  # Opaque black
        assert style.border_width == 1.0
        assert style.border_style == "solid"
        assert not style.shadow_enabled
        assert style.shadow_color.alpha() == 64
        assert style.shadow_offset.x == 2
        assert style.shadow_offset.y == 2
        assert style.shadow_blur == 4.0
        assert not style.gradient_enabled
        assert style.gradient_start_color is None
        assert style.gradient_end_color is None
        assert style.gradient_direction == "vertical"
        assert style.opacity == 1.0
    
    def test_custom_style(self):
        """Test custom shape style."""
        custom_fill = QColor(255, 0, 0, 200)
        custom_border = QColor(0, 255, 0)
        gradient_start = QColor(255, 255, 255)
        gradient_end = QColor(0, 0, 0)
        
        style = ShapeStyle(
            fill_color=custom_fill,
            border_color=custom_border,
            border_width=3.0,
            border_style="dashed",
            shadow_enabled=True,
            gradient_enabled=True,
            gradient_start_color=gradient_start,
            gradient_end_color=gradient_end,
            gradient_direction="horizontal",
            opacity=0.8
        )
        
        assert style.fill_color == custom_fill
        assert style.border_color == custom_border
        assert style.border_width == 3.0
        assert style.border_style == "dashed"
        assert style.shadow_enabled
        assert style.gradient_enabled
        assert style.gradient_start_color == gradient_start
        assert style.gradient_end_color == gradient_end
        assert style.gradient_direction == "horizontal"
        assert style.opacity == 0.8


class TestArrowShape:
    """Test arrow shape functionality."""
    
    def test_arrow_creation(self):
        """Test arrow shape creation."""
        params = ArrowParameters(
            bounds=Rectangle(0, 0, 200, 50),
            start_point=Point(0, 25),
            end_point=Point(200, 25),
            head_style=ArrowStyle.TRIANGLE,
            head_size=15.0,
            shaft_width=3.0
        )
        
        arrow = ArrowShape(params)
        
        assert arrow.parameters == params
        assert arrow.cached_path is None
        assert not arrow.cache_valid
    
    def test_arrow_path_creation(self):
        """Test arrow path creation."""
        params = ArrowParameters(
            bounds=Rectangle(0, 0, 100, 20),
            start_point=Point(10, 10),
            end_point=Point(90, 10),
            head_style=ArrowStyle.TRIANGLE,
            head_size=10.0,
            shaft_width=2.0
        )
        
        arrow = ArrowShape(params)
        path = arrow.create_path()
        
        assert isinstance(path, QPainterPath)
        assert not path.isEmpty()
    
    def test_curved_arrow(self):
        """Test curved arrow creation."""
        params = ArrowParameters(
            bounds=Rectangle(0, 0, 100, 100),
            start_point=Point(10, 50),
            end_point=Point(90, 50),
            curved=True,
            curve_amount=0.5
        )
        
        arrow = ArrowShape(params)
        path = arrow.create_path()
        
        assert isinstance(path, QPainterPath)
    
    def test_different_arrow_styles(self):
        """Test different arrow head styles."""
        base_params = ArrowParameters(
            bounds=Rectangle(0, 0, 100, 20),
            start_point=Point(10, 10),
            end_point=Point(90, 10),
            head_size=10.0
        )
        
        styles = [ArrowStyle.TRIANGLE, ArrowStyle.DIAMOND, ArrowStyle.CIRCLE, ArrowStyle.NONE]
        
        for style in styles:
            base_params.head_style = style
            arrow = ArrowShape(base_params)
            path = arrow.create_path()
            
            assert isinstance(path, QPainterPath)


class TestCalloutShape:
    """Test callout shape functionality."""
    
    def test_callout_creation(self):
        """Test callout shape creation."""
        params = CalloutParameters(
            bounds=Rectangle(10, 10, 200, 100),
            text="Test callout",
            callout_style=CalloutStyle.ROUNDED,
            pointer_position=Point(150, 150),
            corner_radius=8.0
        )
        
        callout = CalloutShape(params)
        
        assert callout.parameters == params
        assert callout.parameters.text == "Test callout"
    
    def test_callout_path_creation(self):
        """Test callout path creation."""
        params = CalloutParameters(
            bounds=Rectangle(10, 10, 150, 80),
            callout_style=CalloutStyle.ROUNDED,
            pointer_position=Point(200, 100),
            corner_radius=5.0
        )
        
        callout = CalloutShape(params)
        path = callout.create_path()
        
        assert isinstance(path, QPainterPath)
        assert not path.isEmpty()
    
    def test_cloud_callout(self):
        """Test cloud-style callout."""
        params = CalloutParameters(
            bounds=Rectangle(10, 10, 100, 60),
            callout_style=CalloutStyle.CLOUD,
            corner_radius=10.0
        )
        
        callout = CalloutShape(params)
        path = callout.create_path()
        
        assert isinstance(path, QPainterPath)


class TestPolygonShape:
    """Test polygon shape functionality."""
    
    def test_polygon_creation(self):
        """Test polygon shape creation."""
        points = [
            Point(0, 0),
            Point(100, 0),
            Point(100, 100),
            Point(0, 100)
        ]
        
        params = PolygonParameters(
            bounds=Rectangle(0, 0, 100, 100),
            points=points,
            closed=True
        )
        
        polygon = PolygonShape(params)
        
        assert polygon.parameters.points == points
        assert polygon.parameters.closed
    
    def test_polygon_path_creation(self):
        """Test polygon path creation."""
        points = [Point(10, 10), Point(50, 10), Point(30, 50)]
        
        params = PolygonParameters(
            bounds=Rectangle(10, 10, 40, 40),
            points=points,
            closed=True
        )
        
        polygon = PolygonShape(params)
        path = polygon.create_path()
        
        assert isinstance(path, QPainterPath)
        assert not path.isEmpty()
    
    def test_smooth_polygon(self):
        """Test smooth polygon creation."""
        points = [Point(0, 50), Point(50, 0), Point(100, 50), Point(50, 100)]
        
        params = PolygonParameters(
            bounds=Rectangle(0, 0, 100, 100),
            points=points,
            smooth=True,
            closed=True
        )
        
        polygon = PolygonShape(params)
        path = polygon.create_path()
        
        assert isinstance(path, QPainterPath)


class TestBezierShape:
    """Test bezier curve shape functionality."""
    
    def test_bezier_creation(self):
        """Test bezier shape creation."""
        control_points = [
            Point(0, 50),
            Point(25, 0),
            Point(75, 100),
            Point(100, 50)
        ]
        
        params = BezierParameters(
            bounds=Rectangle(0, 0, 100, 100),
            control_points=control_points,
            closed=False
        )
        
        bezier = BezierShape(params)
        
        assert bezier.parameters.control_points == control_points
        assert not bezier.parameters.closed
    
    def test_bezier_path_creation(self):
        """Test bezier path creation."""
        control_points = [Point(0, 0), Point(50, -50), Point(100, 0)]
        
        params = BezierParameters(
            bounds=Rectangle(0, -50, 100, 50),
            control_points=control_points
        )
        
        bezier = BezierShape(params)
        path = bezier.create_path()
        
        assert isinstance(path, QPainterPath)
        assert not path.isEmpty()
    
    def test_cubic_bezier(self):
        """Test cubic bezier curve."""
        control_points = [Point(0, 50), Point(25, 0), Point(75, 100), Point(100, 50)]
        
        params = BezierParameters(
            bounds=Rectangle(0, 0, 100, 100),
            control_points=control_points
        )
        
        bezier = BezierShape(params)
        path = bezier.create_path()
        
        assert isinstance(path, QPainterPath)


class TestShapeFactory:
    """Test shape factory functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.factory = ShapeFactory()
    
    def test_factory_initialization(self):
        """Test factory initialization."""
        assert ShapeType.ARROW in self.factory.shape_classes
        assert ShapeType.CALLOUT in self.factory.shape_classes
        assert ShapeType.POLYGON in self.factory.shape_classes
        assert ShapeType.BEZIER in self.factory.shape_classes
    
    def test_create_arrow(self):
        """Test arrow creation through factory."""
        start = Point(0, 0)
        end = Point(100, 0)
        
        arrow = self.factory.create_arrow(start, end)
        
        assert isinstance(arrow, ArrowShape)
        assert arrow.parameters.start_point == start
        assert arrow.parameters.end_point == end
    
    def test_create_callout(self):
        """Test callout creation through factory."""
        bounds = Rectangle(10, 10, 100, 60)
        pointer_pos = Point(150, 80)
        text = "Test callout"
        
        callout = self.factory.create_callout(bounds, pointer_pos, text)
        
        assert isinstance(callout, CalloutShape)
        assert callout.parameters.bounds == bounds
        assert callout.parameters.pointer_position == pointer_pos
        assert callout.parameters.text == text
    
    def test_create_polygon(self):
        """Test polygon creation through factory."""
        points = [Point(0, 0), Point(50, 0), Point(25, 50)]
        
        polygon = self.factory.create_polygon(points, True)
        
        assert isinstance(polygon, PolygonShape)
        assert polygon.parameters.points == points
        assert polygon.parameters.closed
    
    def test_register_custom_shape(self):
        """Test registering custom shape class."""
        class CustomShape:
            pass
        
        self.factory.register_shape_class(ShapeType.STAR, CustomShape)
        
        assert self.factory.shape_classes[ShapeType.STAR] == CustomShape
    
    def test_unknown_shape_type(self):
        """Test creating unknown shape type raises error."""
        with pytest.raises(ValueError, match="Unknown shape type"):
            # Create a mock ShapeType that doesn't exist
            fake_type = Mock()
            fake_type.value = "unknown_shape"
            self.factory.create_shape(fake_type, Mock())


class TestCustomShapeRenderer:
    """Test custom shape renderer functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.mock_overlay_engine = Mock()
        self.renderer = CustomShapeRenderer(self.mock_overlay_engine)
    
    def test_renderer_initialization(self):
        """Test renderer initialization."""
        assert self.renderer.overlay_engine == self.mock_overlay_engine
        assert isinstance(self.renderer.shape_factory, ShapeFactory)
        assert len(self.renderer.rendered_shapes) == 0
    
    def test_add_persistent_shape(self):
        """Test adding persistent shape."""
        mock_shape = Mock()
        shape_id = "test_shape"
        
        self.renderer.add_persistent_shape(shape_id, mock_shape)
        
        assert shape_id in self.renderer.rendered_shapes
        assert self.renderer.rendered_shapes[shape_id] == mock_shape
    
    def test_remove_persistent_shape(self):
        """Test removing persistent shape."""
        mock_shape = Mock()
        shape_id = "test_shape"
        
        self.renderer.add_persistent_shape(shape_id, mock_shape)
        result = self.renderer.remove_persistent_shape(shape_id)
        
        assert result
        assert shape_id not in self.renderer.rendered_shapes
        
        # Try removing non-existent shape
        result = self.renderer.remove_persistent_shape("nonexistent")
        assert not result
    
    def test_get_persistent_shape(self):
        """Test getting persistent shape."""
        mock_shape = Mock()
        shape_id = "test_shape"
        
        self.renderer.add_persistent_shape(shape_id, mock_shape)
        retrieved = self.renderer.get_persistent_shape(shape_id)
        
        assert retrieved == mock_shape
        
        # Non-existent shape
        assert self.renderer.get_persistent_shape("nonexistent") is None
    
    def test_clear_persistent_shapes(self):
        """Test clearing all persistent shapes."""
        self.renderer.add_persistent_shape("shape1", Mock())
        self.renderer.add_persistent_shape("shape2", Mock())
        
        assert len(self.renderer.rendered_shapes) == 2
        
        self.renderer.clear_persistent_shapes()
        
        assert len(self.renderer.rendered_shapes) == 0
    
    def test_register_custom_shape(self):
        """Test registering custom shape with renderer."""
        class CustomShape:
            pass
        
        self.renderer.register_custom_shape(ShapeType.STAR, CustomShape)
        
        # Verify it was registered with the factory
        assert self.renderer.shape_factory.shape_classes[ShapeType.STAR] == CustomShape


if __name__ == "__main__":
    pytest.main([__file__])