from math import pi

import pytest

from dsd.ductsystem.models.rectangular import RectangularElbow


def test_angle_and_radius(properties):
    elbow = RectangularElbow(**properties, angle=-pi / 2)
    assert elbow.angle == -pi / 2
    assert elbow.centerline_radius(1.5) is None


@pytest.mark.parametrize("angle", [0, 4, float("nan")])
def test_invalid_angle(properties, angle):
    with pytest.raises(ValueError):
        RectangularElbow(**properties, angle=angle)


@pytest.mark.parametrize("ratio", [1, 1.5, 2])
def test_radii_are_derived_from_current_width(properties, ratio):
    elbow = RectangularElbow(**properties, angle=pi / 2, width=200, height=100)
    assert elbow.inside_radius(ratio) == 200 * ratio
    assert elbow.centerline_radius(ratio) == 200 * ratio + 100
    elbow.width = 300
    assert elbow.inside_radius(ratio) == 300 * ratio
