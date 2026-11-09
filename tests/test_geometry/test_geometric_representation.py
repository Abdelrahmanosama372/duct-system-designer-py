from math import pi

import pytest

from dsd.geometry.geometric_representation import GeometricRepresentation
from dsd.geometry.primitives import Line, Point, Transform2D


def test_transform_copies_outline_and_skeleton_without_changing_normalized_input():
    line = Line(Point(0, 0), Point(100, 0))
    original = GeometricRepresentation(7, [line], [line])
    result = original.transformed(Transform2D(Point(10, 20), pi / 2))
    assert result.component_id == 7
    assert (result.primitives[0].end.x, result.primitives[0].end.y) == pytest.approx(
        (10, 120)
    )
    assert (
        result.layout_skeleton[0].end.x,
        result.layout_skeleton[0].end.y,
    ) == pytest.approx((10, 120))
    assert (original.primitives[0].end.x, original.primitives[0].end.y) == (100, 0)
