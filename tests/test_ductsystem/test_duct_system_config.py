import pytest

from dsd.ductsystem import DuctSystemConfig, FittingSizingConfig
from dsd.ductsystem.models import Material, PressureLevels


@pytest.mark.parametrize("material", list(Material))
@pytest.mark.parametrize("pressure", list(PressureLevels))
def test_supported_values(material, pressure):
    config = DuctSystemConfig.from_mapping(
        {
            "ductsystem": {
                "material": material.value,
                "pressure_level": pressure.value,
                "fittings": {
                    "takeoff_length": 150,
                    "reducer_length": 300,
                    "elbow_inside_radius_ratio": 1.5,
                },
            }
        }
    )
    assert config == DuctSystemConfig(
        material, pressure, FittingSizingConfig(150, 300, 1.5)
    )


def test_original_aluminum_spelling_is_accepted():
    config = DuctSystemConfig.from_mapping(
        {
            "ductsystem": {
                "material": "Alminum",
                "pressure_level": "lowpressure",
                "fittings": {
                    "takeoff_length": 150,
                    "reducer_length": 300,
                    "elbow_inside_radius_ratio": 1.5,
                },
            }
        }
    )
    assert config.material is Material.Aluminum


def test_invalid_config_values():
    with pytest.raises(ValueError):
        DuctSystemConfig(
            "steel", PressureLevels.LowPressure, FittingSizingConfig(150, 300, 1.5)
        )
    with pytest.raises(ValueError):
        DuctSystemConfig(Material.Aluminum, "low", FittingSizingConfig(150, 300, 1.5))
