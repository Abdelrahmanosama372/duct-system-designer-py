import pytest

from dsd.ductsystem.models.rectangular import RectangularShoeTakeoff


def test_unsized_shoe(properties):
    fitting = RectangularShoeTakeoff(**properties, side="left")
    assert fitting.width1 is None and not hasattr(fitting, "width2")
    assert fitting.takeoff_length is None


def test_invalid_side(properties):
    with pytest.raises(ValueError):
        RectangularShoeTakeoff(**properties, side="up")


def test_bevel_opening_is_derived_from_child_width_and_length(properties):
    fitting = RectangularShoeTakeoff(
        **properties, side="left", width=200, height=150, takeoff_length=150
    )
    assert fitting.width1 == 350
    fitting.width = 250
    assert fitting.width1 == 400
