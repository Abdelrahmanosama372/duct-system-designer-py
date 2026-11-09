import pytest

from dsd.ductsystem.models.rectangular import RectangularDuct


def test_optional_dimensions_and_length(properties):
    duct = RectangularDuct(**properties)
    assert duct.width is None and duct.height is None and duct.length is None


def test_invalid_length(properties):
    with pytest.raises(ValueError):
        RectangularDuct(**properties, length=-1)


def test_duct_stores_geometry_reference_only(properties):
    duct = RectangularDuct(**properties, ref_line_id=42, length=100)
    assert duct.ref_line_id == 42
    assert not hasattr(duct, "raw")


@pytest.mark.parametrize("dimensions", [dict(width=200), dict(height=100)])
def test_supplied_duct_dimensions_must_come_together(properties, dimensions):
    with pytest.raises(ValueError, match="together"):
        RectangularDuct(**properties, **dimensions)
