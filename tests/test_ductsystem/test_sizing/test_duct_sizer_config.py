from dataclasses import replace

import pytest

from dsd.config_builder import ConfigBuilder, ConfigError
from dsd.ductsystem.sizing import DuctSizerConfig


@pytest.mark.parametrize(
    "path,expected_roughness",
    [("config.yaml", 0.00015), ("examples/dsd_config.yaml", 0.000213)],
)
def test_yaml_air_and_external_targets(path, expected_roughness):
    config = ConfigBuilder(path).build().sizing
    assert config.roughness == pytest.approx(expected_roughness)
    assert config.air_density == pytest.approx(1.1180887435024176)
    assert config.dynamic_viscosity == pytest.approx(1.8891414505869057e-5, rel=1e-12)
    assert config.required_velocity == 1000
    assert config.required_head_loss == 0.1


@pytest.mark.parametrize(
    "key,value",
    [
        ("size_increment", 0),
        ("size_increment", 2.5),
        ("size_increment", True),
        ("minimum_duct_dimension", -1),
        ("maximum_duct_dimension", 24),
        ("aspect_ratio", 0),
        ("aspect_ratio", float("nan")),
        ("air_density", -1),
        ("dynamic_viscosity", 0),
        ("roughness", -1),
        ("required_velocity", 0),
        ("required_head_loss", -1),
        ("max_iterations", 0),
        ("friction_tolerance", 0),
        ("friction_max_iterations", 0),
    ],
)
def test_invalid_configuration(sizing_config, key, value):
    with pytest.raises(ValueError):
        replace(sizing_config, **{key: value})


def test_unaligned_bounds_without_any_increment_are_invalid(sizing_config):
    with pytest.raises(ValueError, match="increments"):
        replace(sizing_config, minimum_duct_dimension=101, maximum_duct_dimension=124)


def test_required_air_properties_cannot_be_omitted():
    with pytest.raises(KeyError, match="air"):
        DuctSizerConfig.from_mapping({"sizing": {}})


def test_fixture_uses_25mm_minimum_and_configured_air_properties(sizing_config):
    assert sizing_config.minimum_duct_dimension == 25
    assert sizing_config.air_density == pytest.approx(1.1180887435024176)
    assert sizing_config.dynamic_viscosity == pytest.approx(
        1.8891414505869057e-5, rel=1e-12
    )
