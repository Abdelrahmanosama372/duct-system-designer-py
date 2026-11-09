from dataclasses import replace
from math import sqrt

import pytest

from dsd.ductsystem.sizing import (
    DuctSizer,
    EqualVelocityDuctSizer,
    NoSolutionWithinBounds,
    NumericalConvergenceError,
)
from dsd.ductsystem.sizing.duct_sizer import (
    CFM_TO_M3_S,
    FPM_TO_M_S,
    IN_WG_PER_100_FT_TO_PA_M,
)


def test_external_to_si_conversions():
    assert CFM_TO_M3_S == pytest.approx(0.0004719474432, rel=1e-12)
    assert FPM_TO_M_S == pytest.approx(0.00508, rel=1e-12)
    assert IN_WG_PER_100_FT_TO_PA_M == pytest.approx(8.172208333333334, rel=1e-8)


def test_equal_friction_equivalent_diameter_formula(sizing_config):
    sizer = EqualVelocityDuctSizer(sizing_config)
    assert sizer.equivalent_diameter(600, 300) == pytest.approx(457.01246, rel=1e-7)
    assert sizer.equivalent_diameter(600, 300) == sizer.equivalent_diameter(300, 600)


def test_equivalent_rectangle_respects_discrete_constraints(sizing_config):
    sizer = EqualVelocityDuctSizer(sizing_config)
    result = sizer.find_eqv_rectangular_duct_dimensions(400)
    assert sizer.equivalent_diameter(result.width, result.height) >= 400
    assert result.width % 25 == result.height % 25 == 0
    assert result.width / result.height <= 2


def test_unavailable_equivalent_rectangle(sizing_config):
    with pytest.raises(NoSolutionWithinBounds):
        EqualVelocityDuctSizer(sizing_config).find_eqv_rectangular_duct_dimensions(
            10000
        )


def test_height_bisection_reports_iteration_exhaustion(sizing_config):
    sizer = EqualVelocityDuctSizer(replace(sizing_config, max_iterations=1))
    with pytest.raises(NumericalConvergenceError):
        sizer.find_eqv_rectangular_duct_dimensions(400)


@pytest.mark.parametrize("epsilon", [1e-3, 1e-9])
def test_bisection_uses_supplied_epsilon_and_preserves_both_bounds(epsilon):
    lower, upper = DuctSizer._bisect(
        0.0,
        2.0,
        lambda x: x * x >= 2,
        epsilon=epsilon,
        max_iterations=40,
    )
    assert lower <= sqrt(2) <= upper
    assert upper - lower <= epsilon
    assert lower * lower <= 2 <= upper * upper


def test_bisection_accepts_convergence_on_last_iteration():
    lower, upper = DuctSizer._bisect(
        0.0,
        2.0,
        lambda x: x * x >= 2,
        epsilon=1.0,
        max_iterations=1,
    )
    assert (lower, upper) == (1.0, 2.0)


def test_bisection_reports_exhaustion_with_supplied_budget():
    with pytest.raises(NumericalConvergenceError):
        DuctSizer._bisect(
            0.0,
            2.0,
            lambda x: x * x >= 2,
            epsilon=1e-9,
            max_iterations=1,
        )
