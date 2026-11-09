from dataclasses import replace

import pytest

from dsd.ductsystem.sizing import (
    DuctDimension,
    EqualVelocityDuctSizer,
    NoSolutionWithinBounds,
    SizingContext,
)


def velocity_fpm(flow, size):
    # Independent imperial calculation: convert mm² to ft².
    return flow / (size.width * size.height / 304.8**2)


def test_root_uses_ratio_then_rounds_and_recalculates_height(sizing_config):
    result = EqualVelocityDuctSizer(sizing_config).size_duct(SizingContext(1000))
    assert result == DuctDimension(450, 225)
    assert velocity_fpm(1000, result) <= 1000


def test_parent_width_is_retained_when_ratio_is_acceptable(sizing_config):
    result = EqualVelocityDuctSizer(sizing_config).size_duct(SizingContext(1000, 400))
    assert result == DuctDimension(400, 250)


def test_parent_width_reduces_until_first_acceptable_ratio(sizing_config):
    result = EqualVelocityDuctSizer(sizing_config).size_duct(SizingContext(1000, 600))
    assert result == DuctDimension(450, 225)


def test_equal_flow_can_keep_parent_size(sizing_config):
    sizer = EqualVelocityDuctSizer(sizing_config)
    parent = sizer.size_duct(SizingContext(1000))
    child = sizer.size_duct(SizingContext(1000, parent.width))
    assert child == parent


def test_small_flow_uses_minimum_sizes_and_obeys_ratio(sizing_config):
    result = EqualVelocityDuctSizer(sizing_config).size_duct(SizingContext(1, 600))
    assert result == DuctDimension(50, 25)


def test_non_grid_bounds_and_parent_width_are_respected(sizing_config):
    config = replace(
        sizing_config, minimum_duct_dimension=110, maximum_duct_dimension=490
    )
    result = EqualVelocityDuctSizer(config).size_duct(SizingContext(1000, 499))
    assert 125 <= result.width <= 475 and 125 <= result.height <= 475
    assert result.width % 25 == result.height % 25 == 0
    assert result.width / result.height <= 2
    assert velocity_fpm(1000, result) <= 1000


@pytest.mark.parametrize("flow,width", [(1000000, None), (1000, 10), (1000000, 100)])
def test_no_solution_does_not_enlarge_parent(sizing_config, flow, width):
    with pytest.raises(NoSolutionWithinBounds):
        EqualVelocityDuctSizer(sizing_config).size_duct(SizingContext(flow, width))


def test_required_velocity_is_mandatory(sizing_config):
    with pytest.raises(ValueError, match="required_velocity"):
        EqualVelocityDuctSizer(replace(sizing_config, required_velocity=None))


@pytest.mark.parametrize("flow", [10, 100, 500, 1000, 5000, 15000])
def test_actual_area_meets_target_across_flow_range(sizing_config, flow):
    result = EqualVelocityDuctSizer(sizing_config).size_duct(SizingContext(flow))
    assert velocity_fpm(flow, result) <= 1000
    assert result.width / result.height <= 2
