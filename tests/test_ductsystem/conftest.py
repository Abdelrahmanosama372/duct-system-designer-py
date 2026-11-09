import pytest

from dsd.ductsystem import DuctSystemConfig, FittingSizingConfig
from dsd.ductsystem.models import Material, PressureLevels


@pytest.fixture
def config():
    return DuctSystemConfig(
        Material.GalvanizedSteel,
        PressureLevels.LowPressure,
        FittingSizingConfig(150, 300, 1.5),
    )


@pytest.fixture
def properties(config):
    return dict(
        id=0, flow=100, material=config.material, pressure_level=config.pressure_level
    )


@pytest.fixture
def duct_sizer():
    from dsd.ductsystem.sizing import DuctSizerConfig, EqualVelocityDuctSizer

    return EqualVelocityDuctSizer(
        DuctSizerConfig(
            size_increment=25,
            minimum_duct_dimension=25,
            maximum_duct_dimension=2000,
            aspect_ratio=2,
            air_density=1.1180887435024176,
            dynamic_viscosity=1.8891414505869057e-5,
            roughness=0.000213,
            required_velocity=1000,
        )
    )


@pytest.fixture
def duct_info():
    from dsd.analyzers.models import DuctInfo
    from dsd.geometry.primitives import Line, Point

    def make(identifier, parent_id, start, end, flow=1000, width=None, height=None):
        return DuctInfo(
            id=identifier,
            parent_id=parent_id,
            raw=Line(Point(*start), Point(*end), id=identifier),
            ref_line_id=identifier + 100,
            flow=flow,
            width=width,
            height=height,
        )

    return make


@pytest.fixture
def system_factory(config, duct_sizer):
    from dsd.analyzers.models import SystemTopology
    from dsd.ductsystem import DuctSystem, SystemType

    def make(infos, sizer=None, system_type=SystemType.Supply):
        return DuctSystem.from_topology(
            SystemTopology("Network", infos, [], system_type),
            config,
            duct_sizer if sizer is None else sizer,
        )

    return make


@pytest.fixture
def recording_sizer(duct_sizer):
    from dsd.ductsystem.sizing import DuctDimension, DuctSizer

    class RecordingSizer(DuctSizer):
        def __init__(self, results):
            super().__init__(duct_sizer.config)
            self.results = results
            self.calls = []

        def size_duct(self, context):
            self.calls.append(context)
            return DuctDimension(*self.results[context.flow])

    return RecordingSizer
