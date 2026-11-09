from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from dsd.config_builder import ConfigBuilder, ConfigError
from dsd.ductsystem.models import Material, PressureLevels


def test_entire_example_config_is_built():
    config = ConfigBuilder("examples/dsd_config.yaml").build()
    assert config.reader.input_layer == "duct-network"
    assert config.writer.clear_layers == ("duct-output", "duct-annotations")
    assert config.ductsystem.material is Material.GalvanizedSteel
    assert config.ductsystem.pressure_level is PressureLevels.LowPressure


@pytest.mark.parametrize("section", ["autocad", "ductsystem", "sizing"])
def test_required_sections(section):
    data = yaml.safe_load(Path("examples/dsd_config.yaml").read_text())
    del data[section]
    with pytest.raises(ConfigError, match=section):
        ConfigBuilder.from_mapping(data)


@pytest.mark.parametrize(
    "section,key,value",
    [
        ("ductsystem", "material", "Copper"),
        ("ductsystem", "pressure_level", "unknown"),
        ("autocad", "input", []),
        ("autocad", "output", None),
    ],
)
def test_invalid_sections_and_values(section, key, value):
    data = yaml.safe_load(Path("examples/dsd_config.yaml").read_text())
    data[section][key] = value
    with pytest.raises(ConfigError):
        ConfigBuilder.from_mapping(data)


def test_invalid_and_empty_yaml(tmp_path):
    path = tmp_path / "config.yaml"
    for contents in ["", "autocad: [", "- invalid-root"]:
        path.write_text(contents)
        with pytest.raises(ConfigError):
            ConfigBuilder(path).build()


def test_module_validation_is_used():
    data = yaml.safe_load(Path("examples/dsd_config.yaml").read_text())
    data["autocad"]["input"]["line_network_layer"]["name"] = ""
    original = deepcopy(data)
    with pytest.raises(ConfigError):
        ConfigBuilder.from_mapping(data)
    assert data == original


def test_sizing_air_properties_are_validated():
    data = yaml.safe_load(Path("examples/dsd_config.yaml").read_text())
    data["sizing"]["air"]["density_kg_m3"] = 0
    with pytest.raises(ConfigError, match="air_density"):
        ConfigBuilder.from_mapping(data)
