import pytest

from dsd.ductsystem.models.rectangular import RectangularSheetMetalComponent


def test_dimensions_are_optional(properties):
    component = RectangularSheetMetalComponent(**properties)
    assert component.width is None and component.height is None
    assert RectangularSheetMetalComponent(**properties, width=400).width == 400


@pytest.mark.parametrize("dimension", [0, -1, float("inf")])
def test_invalid_dimension(properties, dimension):
    with pytest.raises(ValueError):
        RectangularSheetMetalComponent(**properties, height=dimension)
