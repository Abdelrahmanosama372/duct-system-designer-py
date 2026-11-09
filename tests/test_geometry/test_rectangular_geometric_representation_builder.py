from math import pi

import pytest

from dsd.ductsystem.models.rectangular import (
    RectangularDuct,
    RectangularElbow,
    RectangularEndcap,
    RectangularReducer,
    RectangularShoeTakeoff,
)
from dsd.geometry.builders.rectangular import (
    GeometryConstructionError,
    RectangularGeometricRepresentationBuilder,
)
from dsd.geometry.placement import PlacementContext
from dsd.geometry.primitives import Arc, Line, LineType, Point, Transform2D


def xy(point):
    return point.x, point.y


def test_normalized_duct_has_four_edges_including_both_end_lines(
    fitting_config, component_properties
):
    builder = RectangularGeometricRepresentationBuilder(fitting_config)
    duct = RectangularDuct(**component_properties, width=200, height=100, length=1000)
    context = PlacementContext(Transform2D(Point(0, 0), 0))
    result = builder.build_duct(duct, context)
    assert [(xy(line.start), xy(line.end)) for line in result.primitives] == [
        ((0, -100), (1000, -100)),
        ((1000, -100), (1000, 100)),
        ((1000, 100), (0, 100)),
        ((0, 100), (0, -100)),
    ]
    assert [(xy(line.start), xy(line.end)) for line in result.layout_skeleton] == [
        ((0, 0), (1000, 0))
    ]
    assert result.layout_skeleton[0].line_type is LineType.CenterLine


@pytest.mark.parametrize("angle,side", [(pi / 2, 1), (-pi / 2, -1)])
def test_elbow_has_two_arcs_end_lines_and_intersecting_skeleton_legs(
    fitting_config, component_properties, angle, side
):
    builder = RectangularGeometricRepresentationBuilder(fitting_config)
    elbow = RectangularElbow(**component_properties, width=200, height=100, angle=angle)
    result = builder.build_elbow(elbow, PlacementContext(Transform2D(Point(0, 0), 0)))
    inner, outer, inlet, outlet = result.primitives
    assert isinstance(inner, Arc) and isinstance(outer, Arc)
    assert isinstance(inlet, Line) and isinstance(outlet, Line)
    assert xy(inner.center) == pytest.approx((-400, side * 400))
    assert xy(inner.start) == pytest.approx((-400, side * 100))
    assert xy(outer.start) == pytest.approx((-400, -side * 100))
    assert inner.angle == outer.angle == angle
    assert xy(outlet.start) == pytest.approx((-100, side * 400))
    assert xy(outlet.end) == pytest.approx((100, side * 400))
    first, second = result.layout_skeleton
    assert xy(first.start) == pytest.approx((-400, 0))
    assert xy(first.end) == xy(second.start) == (0, 0)
    assert xy(second.end) == pytest.approx((0, side * 400))


@pytest.mark.parametrize(
    "side,inlet_y", [("left", (-250, 100)), ("right", (-100, 250))]
)
def test_shoe_is_closed_45_degree_trapezoid(
    fitting_config, component_properties, side, inlet_y
):
    builder = RectangularGeometricRepresentationBuilder(fitting_config)
    shoe = RectangularShoeTakeoff(
        **component_properties, width=200, height=100, takeoff_length=150, side=side
    )
    result = builder.build_shoetakeoff(
        shoe, PlacementContext(Transform2D(Point(0, 0), 0))
    )
    assert len(result.primitives) == 4
    assert xy(result.primitives[0].start) == (0, inlet_y[0])
    assert xy(result.primitives[0].end) == (150, -100)
    assert xy(result.primitives[2].end) == (0, inlet_y[1])
    assert result.layout_skeleton[0].length() == 150


def test_reducer_is_centered_with_two_end_lines(fitting_config, component_properties):
    reducer = RectangularReducer(
        **component_properties,
        inlet_width=400,
        inlet_height=200,
        outlet_width=200,
        outlet_height=100,
        length=300
    )
    builder = RectangularGeometricRepresentationBuilder(fitting_config)
    result = builder.build_reducer(
        reducer, PlacementContext(Transform2D(Point(0, 0), 0))
    )
    assert [(xy(line.start), xy(line.end)) for line in result.primitives] == [
        ((0, -200), (300, -100)),
        ((300, -100), (300, 100)),
        ((300, 100), (0, 200)),
        ((0, 200), (0, -200)),
    ]
    assert result.layout_skeleton[0].length() == 300


def test_endcap_has_one_line_and_empty_skeleton(fitting_config, component_properties):
    cap = RectangularEndcap(**component_properties, width=400, height=200)
    builder = RectangularGeometricRepresentationBuilder(fitting_config)
    result = builder.build_endcap(cap, PlacementContext(Transform2D(Point(0, 0), 0)))
    assert len(result.primitives) == 1
    assert (xy(result.primitives[0].start), xy(result.primitives[0].end)) == (
        (0, -200),
        (0, 200),
    )
    assert result.layout_skeleton == []


def test_normalized_primitives_are_reused_and_only_placement_changes(
    fitting_config, component_properties
):
    builder = RectangularGeometricRepresentationBuilder(fitting_config)
    duct = RectangularDuct(**component_properties, width=200, height=100, length=1000)
    builder.build_duct(duct, PlacementContext(Transform2D(Point(0, 0), 0)))
    normalized = builder.normalized_representations[0]
    result = builder.build_duct(
        duct, PlacementContext(Transform2D(Point(10, 20), pi / 2))
    )
    assert builder.normalized_representations[0] is normalized
    assert xy(normalized.primitives[0].start) == (0, -100)
    assert xy(result.primitives[0].start) == pytest.approx((110, 20))
    assert xy(result.primitives[0].end) == pytest.approx((110, 1020))
    assert result.primitives[0] is not normalized.primitives[0]
    duct.width = 400
    builder.build_duct(duct, PlacementContext(Transform2D(Point(0, 0), 0)))
    assert builder.normalized_representations[0] is not normalized


def test_unsized_geometry_is_rejected(fitting_config, component_properties):
    with pytest.raises(GeometryConstructionError, match="width"):
        RectangularGeometricRepresentationBuilder(fitting_config).build_duct(
            RectangularDuct(**component_properties),
            PlacementContext(Transform2D(Point(0, 0), 0)),
        )


def test_180_degree_elbow_requires_a_different_placement_model(
    fitting_config, component_properties
):
    with pytest.raises(GeometryConstructionError, match="180 degrees"):
        RectangularGeometricRepresentationBuilder(fitting_config).build_elbow(
            RectangularElbow(**component_properties, width=200, height=100, angle=pi),
            PlacementContext(Transform2D(Point(0, 0), 0)),
        )
