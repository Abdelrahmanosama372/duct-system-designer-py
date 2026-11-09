import pytest

from dsd.analyzers.models import DuctInfo, SystemTopology
from dsd.ductsystem import DuctSystem
from dsd.geometry.primitives import Line, Point
from dsd.system_type import SystemType


@pytest.mark.parametrize("system_type", list(SystemType))
def test_from_topology_and_traversal(config, system_type, duct_sizer):
    topology = SystemTopology(
        "Supply",
        [
            DuctInfo(
                id=0,
                parent_id=None,
                raw=Line(Point(0, 0), Point(100, 0), id=0),
                ref_line_id=42,
            )
        ],
        [],
        system_type=system_type,
    )
    system = DuctSystem.from_topology(topology, config, duct_sizer)
    assert system.system_name == "Supply"
    assert system.system_type is system_type
    assert system.config is config
    assert list(system.level_order_traversal()) == [system.dftree.root]


def test_invalid_direct_system_type_is_rejected(config, duct_sizer):
    from dsd.ductsystem import DuctFittingTree, SheetMetalNode
    from dsd.ductsystem.models.rectangular import RectangularDuct

    duct = RectangularDuct(
        id=0, flow=0, material=config.material, pressure_level=config.pressure_level
    )
    with pytest.raises(ValueError, match="system_type"):
        DuctSystem(
            "Supply",
            DuctFittingTree(SheetMetalNode(duct)),
            config,
            "exhaust",
            duct_sizer,
        )
