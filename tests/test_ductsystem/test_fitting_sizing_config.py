from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from dsd.config_builder import ConfigBuilder, ConfigError
from dsd.ductsystem import FittingSizingConfig


def test_fitting_config_loaded_from_yaml():
    config = ConfigBuilder("config.yaml").build().ductsystem.fittings
    assert config == FittingSizingConfig(150, 300, 1.5)


@pytest.mark.parametrize(
    "field", ["takeoff_length", "reducer_length", "elbow_inside_radius_ratio"]
)
@pytest.mark.parametrize("value", [0, -1, float("nan"), float("inf"), True])
def test_invalid_fitting_settings(field, value):
    with pytest.raises(ValueError):
        replace(FittingSizingConfig(150, 300, 1.5), **{field: value})


def test_missing_fitting_setting_is_reported_by_config_builder():
    data = yaml.safe_load(Path("config.yaml").read_text())
    del data["ductsystem"]["fittings"]["reducer_length"]
    with pytest.raises(ConfigError, match="reducer_length"):
        ConfigBuilder.from_mapping(data)
