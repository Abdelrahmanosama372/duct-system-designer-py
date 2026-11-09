from copy import deepcopy
from math import pi

import pytest

from dsd.ductsystem.models import SheetMetalComponent
from dsd.ductsystem.models.rectangular import (
    RectangularDuct,
    RectangularDuctFitting,
    RectangularElbow,
    RectangularEndcap,
    RectangularReducer,
    RectangularShoeTakeoff,
)
from dsd.ductsystem.visitors import AreaCalculationError, AreaCalculatorVisitor


@pytest.fixture
def visitor(config):
    return AreaCalculatorVisitor(config.fittings)


@pytest.mark.parametrize(
    "width,height,length,expected_m2",
    [
        (400, 200, 1000, 1.2),
        (1000, 1000, 1000, 4.0),
        (200, 100, 500, 0.3),
    ],
)
def test_duct_four_faces_exclude_open_ends(
    visitor, properties, width, height, length, expected_m2
):
    duct = RectangularDuct(**properties, width=width, height=height, length=length)
    assert duct.accept(visitor) == pytest.approx(expected_m2)
    assert visitor.areas_m2 == {0: pytest.approx(expected_m2)}


@pytest.mark.parametrize(
    "angle,expected_m2", [(pi / 2, 0.12 * pi), (-pi / 2, 0.12 * pi), (pi, 0.24 * pi)]
)
def test_elbow_curved_faces_and_annular_cheeks(visitor, properties, angle, expected_m2):
    elbow = RectangularElbow(**properties, width=200, height=100, angle=angle)
    assert visitor.visit(elbow) == pytest.approx(expected_m2)


@pytest.mark.parametrize(
    "ratio,expected_m2", [(1, 0.09 * pi), (1.5, 0.12 * pi), (2, 0.15 * pi)]
)
def test_elbow_uses_configured_inside_radius(config, properties, ratio, expected_m2):
    from dataclasses import replace

    visitor = AreaCalculatorVisitor(
        replace(config.fittings, elbow_inside_radius_ratio=ratio)
    )
    elbow = RectangularElbow(**properties, width=200, height=100, angle=pi / 2)
    assert elbow.accept(visitor) == pytest.approx(expected_m2)


@pytest.mark.parametrize("side", ["left", "right"])
def test_shoe_has_two_trapezoidal_cheeks_and_two_sides(visitor, properties, side):
    shoe = RectangularShoeTakeoff(
        **properties, width=200, height=100, takeoff_length=100, side=side
    )
    # Two 25000 mm² cheeks, a 10000 mm² side, and a 14142.1356 mm² bevel.
    assert shoe.accept(visitor) == pytest.approx(0.07414213562373095)


@pytest.mark.parametrize(
    "inlet,outlet,expected_m2",
    [
        ((400, 200), (200, 200), 0.3064911064067352),  # width only
        ((200, 400), (200, 200), 0.3064911064067352),  # height only
        ((600, 400), (200, 200), 0.4693152893413097),  # both
        ((200, 200), (600, 400), 0.4693152893413097),  # expansion
        ((400, 200), (400, 200), 0.36),  # parallel faces
    ],
)
def test_centered_reducer_four_sloping_faces(
    visitor, properties, inlet, outlet, expected_m2
):
    reducer = RectangularReducer(
        **properties,
        inlet_width=inlet[0],
        inlet_height=inlet[1],
        outlet_width=outlet[0],
        outlet_height=outlet[1],
        length=300
    )
    assert reducer.accept(visitor) == pytest.approx(expected_m2)


def test_endcap_is_one_flat_plate(visitor, properties):
    cap = RectangularEndcap(**properties, width=400, height=200)
    assert cap.accept(visitor) == pytest.approx(0.08)


def test_parent_duct_area_does_not_deduct_shoe_opening(visitor, properties):
    duct = RectangularDuct(**properties, width=400, height=200, length=1000)
    shoe = RectangularShoeTakeoff(
        **{**properties, "id": 1},
        width=200,
        height=100,
        takeoff_length=100,
        side="left"
    )
    assert duct.accept(visitor) == pytest.approx(1.2)
    assert shoe.accept(visitor) == pytest.approx(0.07414213562373095)
    assert visitor.total_area_m2 == pytest.approx(1.274142135623731)
    assert visitor.areas_m2[0] == pytest.approx(1.2)


def test_repeat_visits_update_results_without_double_counting(visitor, properties):
    duct = RectangularDuct(**properties, width=200, height=100, length=1000)
    cap = RectangularEndcap(**{**properties, "id": 1}, width=200, height=100)
    duct.accept(visitor)
    duct.accept(visitor)
    cap.accept(visitor)
    assert visitor.total_area_m2 == pytest.approx(0.62)
    duct.width = 400
    duct.accept(visitor)
    assert visitor.areas_m2 == {0: pytest.approx(1.0), 1: pytest.approx(0.02)}
    assert visitor.total_area_m2 == pytest.approx(1.02)
    visitor.reset()
    assert visitor.areas_m2 == {} and visitor.total_area_m2 == 0


@pytest.mark.parametrize(
    "kind,kwargs",
    [
        (RectangularDuct, dict()),
        (RectangularDuct, dict(width=200, height=100)),
        (RectangularElbow, dict(angle=pi / 2)),
        (RectangularShoeTakeoff, dict(side="left", width=200, height=100)),
        (RectangularReducer, dict(length=300)),
        (RectangularEndcap, dict()),
    ],
)
def test_missing_dimensions_are_reported_without_recording(
    visitor, properties, kind, kwargs
):
    component = kind(**properties, **kwargs)
    with pytest.raises(AreaCalculationError, match="requires positive finite"):
        component.accept(visitor)
    assert visitor.areas_m2 == {}


@pytest.mark.parametrize("value", [None, 0, -1, float("nan"), float("inf")])
def test_mutated_invalid_dimensions_are_reported(visitor, properties, value):
    duct = RectangularDuct(**properties, width=200, height=100, length=1000)
    duct.length = value
    with pytest.raises(AreaCalculationError, match="length"):
        visitor.visit(duct)


@pytest.mark.parametrize("kind", [SheetMetalComponent, RectangularDuctFitting])
def test_unsupported_components_are_reported(visitor, properties, kind):
    with pytest.raises(TypeError, match="Unsupported sheet-metal component"):
        visitor.visit(kind(**properties))


def test_calculation_does_not_change_components(visitor, properties):
    elbow = RectangularElbow(**properties, width=200, height=100, angle=pi / 2)
    before = deepcopy(elbow)
    elbow.accept(visitor)
    assert elbow == before
