import pytest

from dsd.ductsystem.models.rectangular import RectangularReducer


def test_reducer_can_remain_unsized(properties):
    reducer = RectangularReducer(**properties)
    assert reducer.inlet_width is None and reducer.outlet_height is None
    assert reducer.length is None


def test_reject_invalid_dimension(properties):
    with pytest.raises(ValueError):
        RectangularReducer(**properties, outlet_width=-10)
