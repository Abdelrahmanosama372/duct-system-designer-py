import pytest

from dsd.ductsystem.sizing import DuctSizerConfig


@pytest.fixture
def sizing_config():
    return DuctSizerConfig(
        size_increment=25,
        minimum_duct_dimension=25,
        maximum_duct_dimension=2000,
        aspect_ratio=2,
        air_density=1.1180887435024176,
        dynamic_viscosity=1.8891414505869057e-5,
        roughness=0.00015,
        required_velocity=1000,
        required_head_loss=0.1,
    )
