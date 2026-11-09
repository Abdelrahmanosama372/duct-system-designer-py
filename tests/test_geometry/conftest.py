import pytest

from dsd.ductsystem import FittingSizingConfig
from dsd.ductsystem.models import Material, PressureLevels


@pytest.fixture
def fitting_config():
    return FittingSizingConfig(150, 300, 1.5)


@pytest.fixture
def component_properties():
    return dict(
        id=0,
        flow=1000,
        material=Material.GalvanizedSteel,
        pressure_level=PressureLevels.LowPressure,
    )
