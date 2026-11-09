from dataclasses import replace
from math import log10, pi, sqrt

import pytest

from dsd.ductsystem.sizing import (
    DuctSizerConfig,
    EqualFrictionDuctSizer,
    NoSolutionWithinBounds,
    NumericalConvergenceError,
    SizingContext,
)


@pytest.mark.parametrize(
    "reynolds,roughness_m,expected_factor",
    [
        (100000, 0.00005, 0.01851386607747164),
        (100000, 0.0, 0.017989773084273838),
        (10000, 0.0005, 0.03238180636309272),
    ],
)
def test_known_colebrook_factors(sizing_config, reynolds, roughness_m, expected_factor):
    # Reference values evaluated with 50-digit decimal arithmetic at D=500 mm.
    sizer = EqualFrictionDuctSizer(replace(sizing_config, roughness=roughness_m))
    factor = sizer.friction_factor(reynolds, 500)
    assert factor == pytest.approx(expected_factor, rel=1e-10)
    residual = 1 / sqrt(factor) + 2 * log10(
        roughness_m / (3.7 * 0.5) + 2.51 / (reynolds * sqrt(factor))
    )
    assert abs(residual) < 1e-8


def test_laminar_factor(sizing_config):
    assert EqualFrictionDuctSizer(sizing_config).friction_factor(1000, 100) == 0.064


def test_transition_uses_colebrook_at_2300(sizing_config):
    sizer = EqualFrictionDuctSizer(sizing_config)
    assert sizer.friction_factor(2299, 100) == 64 / 2299
    assert sizer.friction_factor(2300, 100) == pytest.approx(
        0.048485832104955015,
        rel=1e-10,
    )


def test_laminar_loss_matches_poiseuille_equation(sizing_config):
    sizer = EqualFrictionDuctSizer(sizing_config)
    flow_cfm = 0.1
    q = flow_cfm * 0.0004719474432
    diameter_m = 0.1
    expected = 128 * sizing_config.dynamic_viscosity * q / (pi * diameter_m**4)
    assert sizer.pressure_loss_pa_m(flow_cfm, 100) == pytest.approx(expected, rel=1e-10)


def test_find_diameter_matches_independent_known_darcy_case(sizing_config):
    rho, mu, diameter = sizing_config.air_density, sizing_config.dynamic_viscosity, 0.5
    velocity = 100000 * mu / (rho * diameter)
    flow = velocity * pi * diameter**2 / 4 / 0.0004719474432
    loss_pa_m = 0.01851386607747164 * rho * velocity**2 / (2 * diameter)
    config = replace(
        sizing_config,
        roughness=0.00005,
        required_head_loss=loss_pa_m * 30.48 / 249.08891,
    )
    sizer = EqualFrictionDuctSizer(config)
    result = sizer.find_equivalent_diameter(flow)
    assert result == pytest.approx(500, abs=config.diameter_tolerance_mm)
    assert sizer.pressure_loss_pa_m(flow, result) <= loss_pa_m


@pytest.mark.parametrize(
    "flow,width", [(1, None), (100, None), (1000, None), (1000, 500), (5000, None)]
)
def test_selected_rectangle_meets_actual_friction_target(sizing_config, flow, width):
    sizer = EqualFrictionDuctSizer(sizing_config)
    result = sizer.size_duct(SizingContext(flow, width))
    equivalent = (
        1.3
        * (result.width * result.height) ** 0.625
        / (result.width + result.height) ** 0.25
    )
    assert (
        sizer.pressure_loss_pa_m(flow, equivalent)
        <= sizing_config.required_head_loss * 249.08891 / 30.48
    )
    assert result.width / result.height <= sizing_config.aspect_ratio
    assert result.width % 25 == result.height % 25 == 0
    if width is not None:
        assert result.width <= width


def test_larger_roughness_requires_larger_equivalent_diameter(sizing_config):
    smooth = EqualFrictionDuctSizer(replace(sizing_config, roughness=0))
    rough = EqualFrictionDuctSizer(sizing_config)
    assert rough.find_equivalent_diameter(1000) > smooth.find_equivalent_diameter(1000)


def test_maximum_size_cannot_meet_target(sizing_config):
    sizer = EqualFrictionDuctSizer(replace(sizing_config, maximum_duct_dimension=100))
    with pytest.raises(NoSolutionWithinBounds):
        sizer.size_duct(SizingContext(100000))


def test_small_flow_does_not_fail_when_minimum_size_is_already_sufficient(
    sizing_config,
):
    sizer = EqualFrictionDuctSizer(sizing_config)
    assert sizer.find_equivalent_diameter(0.00001) == 20
    assert sizer.size_duct(SizingContext(0.00001)).height == 25


def test_required_friction_target_is_mandatory(sizing_config):
    with pytest.raises(ValueError, match="required_head_loss"):
        EqualFrictionDuctSizer(replace(sizing_config, required_head_loss=None))


@pytest.mark.parametrize(
    "options", [dict(max_iterations=1), dict(friction_max_iterations=1)]
)
def test_numerical_exhaustion_is_reported(sizing_config, options):
    sizer = EqualFrictionDuctSizer(replace(sizing_config, **options))
    with pytest.raises(NumericalConvergenceError):
        sizer.size_duct(SizingContext(1000))


# Regression cases: flow CFM, target loss Pa/m, expected (width, height) mm,
# and expected equivalent diameter of that selected rectangle in mm.
# All cases size a root duct (no parent width), with the fixed settings below.
EQUAL_FRICTION_SIZING_CASES = [
    (100, 0.5, (225, 125), 181.388259),
    (100, 0.8, (200, 100), 152.337487),
    (100, 1.2, (200, 100), 152.337487),
    (500, 0.5, (400, 200), 304.674973),
    (500, 0.8, (350, 200), 286.443489),
    (500, 1.2, (350, 175), 266.590602),
    (1000, 0.5, (500, 275), 400.919438),
    (1000, 0.8, (450, 250), 362.776519),
    (1000, 1.2, (425, 225), 333.865980),
    (2500, 0.5, (725, 375), 562.439712),
    (2500, 0.8, (650, 325), 495.096831),
    (2500, 1.2, (600, 300), 457.012460),
    (5000, 0.5, (950, 475), 723.603061),
    (5000, 0.8, (850, 425), 647.434318),
    (5000, 1.2, (800, 400), 609.349946),
]


@pytest.mark.parametrize(
    "flow_cfm,head_loss_pa_m,expected_size_mm,expected_equivalent_diameter_mm",
    EQUAL_FRICTION_SIZING_CASES,
    ids=[
        f"{flow}CFM-{loss}Pa_per_m-{size[0]}x{size[1]}mm"
        for flow, loss, size, _ in EQUAL_FRICTION_SIZING_CASES
    ],
)
def test_equal_friction_duct_sizes(
    flow_cfm, head_loss_pa_m, expected_size_mm, expected_equivalent_diameter_mm
):
    """Verify rectangular duct sizes for specified airflow and friction-loss targets.

    Settings: width/height <= 2; 25 mm increments; 25–2000 mm dimensions;
    density 1.1180887435024176 kg/m³; viscosity 1.8891414505869057e-5 Pa·s; roughness 0.213 mm;
    Colebrook–White circular-equivalent friction; no parent width or velocity cap.
    """
    config = DuctSizerConfig(
        size_increment=25,
        minimum_duct_dimension=25,
        maximum_duct_dimension=2000,
        aspect_ratio=2,
        air_density=1.1180887435024176,
        dynamic_viscosity=1.8891414505869057e-5,
        roughness=0.000213,
        # Public configuration takes in. w.g./100 ft; table inputs stay in Pa/m.
        required_head_loss=head_loss_pa_m * 30.48 / 249.08891,
    )
    sizer = EqualFrictionDuctSizer(config)
    result = sizer.size_duct(SizingContext(flow=flow_cfm))
    actual_size_mm = (result.width, result.height)
    equivalent_diameter = sizer.equivalent_diameter(result.width, result.height)
    actual_loss = sizer.pressure_loss_pa_m(flow_cfm, equivalent_diameter)
    print(
        f"{flow_cfm} CFM | target {head_loss_pa_m:g} Pa/m | "
        f"{result.width} x {result.height} mm | "
        f"equivalent diameter {equivalent_diameter:.3f} mm | "
        f"actual loss {actual_loss:.6f} Pa/m"
    )
    assert actual_size_mm == expected_size_mm, (
        f"{flow_cfm} CFM at {head_loss_pa_m:g} Pa/m: "
        f"expected {expected_size_mm} mm, got {actual_size_mm} mm"
    )
    assert equivalent_diameter == pytest.approx(
        expected_equivalent_diameter_mm, abs=0.001, rel=0
    ), (
        f"{flow_cfm} CFM at {head_loss_pa_m:g} Pa/m: "
        f"expected equivalent diameter {expected_equivalent_diameter_mm} mm, "
        f"got {equivalent_diameter} mm"
    )
    assert actual_loss <= head_loss_pa_m * (1 + 1e-12)
