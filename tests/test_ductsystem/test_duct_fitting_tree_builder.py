from copy import deepcopy
from math import pi

import pytest

from dsd.analyzers.models import DuctInfo, SystemTopology
from dsd.ductsystem import DuctFittingTreeBuilder, DuctTreeError
from dsd.ductsystem.models.rectangular import (
    RectangularDuct,
    RectangularElbow,
    RectangularEndcap,
    RectangularReducer,
    RectangularShoeTakeoff,
)
from dsd.geometry.primitives import Line, Point
from dsd.system_type import SystemType


def info(identifier, parent, start, end, flow=100, **dimensions):
    return DuctInfo(
        id=identifier,
        parent_id=parent,
        raw=Line(Point(*start), Point(*end), id=identifier),
        ref_line_id=identifier + 100,
        flow=flow,
        **dimensions
    )


def build(config, infos):
    return DuctFittingTreeBuilder(config).build(
        SystemTopology("Supply", infos, [], system_type=SystemType.Supply)
    )


def components(tree, cls):
    return [
        node.component
        for node in tree.level_order_traversal()
        if isinstance(node.component, cls)
    ]


def test_single_duct_and_dimensions(config):
    source = info(0, None, (0, 0), (100, 0), width=400, height=200)
    tree = build(config, [source])
    duct = tree.root.component
    assert isinstance(duct, RectangularDuct)
    assert (duct.id, duct.flow, duct.width, duct.height, duct.length) == (
        0,
        100,
        400,
        200,
        100,
    )
    assert duct.ref_line_id == 100
    assert not hasattr(duct, "raw")
    assert duct.material is config.material
    assert duct.pressure_level is config.pressure_level
    assert tree.root.parent is None and tree.root.children == []


def test_straight_connection_needs_no_fitting_and_keeps_supplied_sizes(config):
    tree = build(
        config,
        [
            info(1, 0, (100, 0), (200, 0), width=300, height=200),
            info(0, None, (0, 0), (100, 0)),
        ],
    )
    nodes = tree.connected_components
    assert [node.component.id for node in nodes] == [0, 1]
    assert nodes[0].component.width is None
    assert nodes[1].component.width == 300 and nodes[1].component.height == 200
    assert nodes[1].parent is nodes[0]
    assert all(not node.is_duct_fitting() for node in nodes)


@pytest.mark.parametrize(
    "endpoint,angle",
    [((100, 100), pi / 2), ((100, -100), -pi / 2), ((200, 100), pi / 4)],
)
def test_turn_creates_unsized_elbow(config, endpoint, angle):
    tree = build(
        config, [info(0, None, (0, 0), (100, 0)), info(1, 0, (100, 0), endpoint)]
    )
    nodes = tree.connected_components
    assert len(nodes) == 3
    elbow = nodes[1].component
    assert isinstance(elbow, RectangularElbow)
    assert elbow.angle == pytest.approx(angle)
    assert elbow.centerline_radius(config.fittings.elbow_inside_radius_ratio) is None
    assert elbow.width is None and elbow.height is None
    assert nodes[2].component.id == 1
    assert nodes[2].parent is nodes[1]


@pytest.mark.parametrize("side,y", [("left", 100), ("right", -100)])
def test_perpendicular_branch_with_straight_continuation(config, side, y):
    tree = build(
        config,
        [
            info(0, None, (0, 0), (100, 0)),
            info(1, 0, (100, 0), (200, 0), flow=60),
            info(2, 0, (100, 0), (100, y), flow=40),
        ],
    )
    shoe, continuation = tree.root.children
    assert isinstance(shoe.component, RectangularShoeTakeoff)
    assert shoe.component.side == side and shoe.component.flow == 40
    assert [child.component.id for child in shoe.children] == [2]
    assert continuation.component.id == 1 and continuation.parent is tree.root
    assert components(tree, RectangularEndcap) == []
    assert components(tree, RectangularElbow) == []


def test_opposite_branches_use_two_sibling_takeoffs(config):
    tree = build(
        config,
        [
            info(0, None, (0, 0), (100, 0)),
            info(1, 0, (100, 0), (200, 0), flow=30),
            info(2, 0, (100, 0), (100, 100), flow=40),
            info(3, 0, (100, 0), (100, -100), flow=30),
        ],
    )
    left, right, continuation = tree.root.children
    assert [left.component.side, right.component.side] == ["left", "right"]
    assert [left.component.flow, right.component.flow] == [40, 30]
    assert left.parent is right.parent is continuation.parent is tree.root
    assert [child.component.id for child in left.children] == [2]
    assert [child.component.id for child in right.children] == [3]
    assert continuation.component.id == 1


def test_terminal_junction_attaches_endcap_directly_to_main(config):
    tree = build(
        config,
        [
            info(0, None, (0, 0), (100, 0), flow=100),
            info(1, 0, (100, 0), (100, 100), flow=40, width=300, height=200),
            info(2, 0, (100, 0), (100, -100), flow=60, width=500, height=200),
        ],
    )
    left, right, endcap = tree.root.children
    assert isinstance(left.component, RectangularShoeTakeoff)
    assert isinstance(right.component, RectangularShoeTakeoff)
    assert isinstance(endcap.component, RectangularEndcap)
    assert endcap.parent is tree.root and endcap.children == []
    assert endcap.component.flow == 0
    assert [duct.id for duct in components(tree, RectangularDuct)] == [0, 1, 2]
    assert tree.root.component.length == 100


def test_perpendicular_sides_are_relative_to_main_direction(config):
    tree = build(
        config,
        [
            info(0, None, (0, 0), (0, 100)),
            info(1, 0, (0, 100), (0, 200), flow=60),
            info(2, 0, (0, 100), (-100, 100), flow=40),
        ],
    )
    assert components(tree, RectangularShoeTakeoff)[0].side == "left"


def test_no_reducers_inserted_before_sizing(config):
    tree = build(
        config,
        [
            info(0, None, (0, 0), (100, 0), width=400, height=200),
            info(1, 0, (100, 0), (200, 0), width=200, height=200),
        ],
    )
    assert components(tree, RectangularReducer) == []
    assert len(tree.connected_components) == 2


def test_rebuilding_is_repeatable_without_mutation(config):
    topology = SystemTopology(
        "Supply",
        [info(0, None, (0, 0), (100, 0)), info(1, 0, (100, 0), (100, 100))],
        [],
        system_type=SystemType.Supply,
    )
    original = deepcopy(topology)
    builder = DuctFittingTreeBuilder(config)
    first, second = builder.build(topology), builder.build(topology)
    assert [node.component.id for node in first.connected_components] == [
        node.component.id for node in second.connected_components
    ]
    assert len(set(node.component.id for node in first.connected_components)) == 3
    first.root.component.width = 999
    assert topology == original


@pytest.mark.parametrize(
    "infos,error",
    [
        ([], "no ducts"),
        ([info(0, None, (0, 0), (100, 0)), info(0, 0, (100, 0), (200, 0))], "unique"),
        (
            [info(0, None, (0, 0), (100, 0)), info(1, None, (100, 0), (200, 0))],
            "exactly one",
        ),
        (
            [info(0, None, (0, 0), (100, 0)), info(1, 55, (100, 0), (200, 0))],
            "Missing parent",
        ),
        ([info(0, None, (0, 0), (100, 0)), info(1, 0, (300, 0), (400, 0))], "endpoint"),
        ([info(0, None, (0, 0), (0, 0))], "positive XY"),
    ],
)
def test_invalid_topologies(config, infos, error):
    with pytest.raises(DuctTreeError, match=error):
        build(config, infos)


def test_angled_branch_junction_is_reported(config):
    with pytest.raises(DuctTreeError, match="perpendicular"):
        build(
            config,
            [
                info(0, None, (0, 0), (100, 0)),
                info(1, 0, (100, 0), (200, 0)),
                info(2, 0, (100, 0), (200, 100)),
            ],
        )


def test_circular_source_is_reported(config):
    with pytest.raises(DuctTreeError, match="Circular"):
        build(config, [info(0, None, (0, 0), (100, 0), diameter=200)])


def test_analyzer_output_builds_independent_duct_systems(config, duct_sizer):
    from dsd.adapters.autocad.models import AutoCadInput, LineInfo
    from dsd.analyzers import TopologyAnalyzer
    from dsd.ductsystem import DuctSystem

    a = LineInfo(
        Line(Point(0, 0), Point(100, 0), id=0),
        {"system-name": "A", "system-type": "supply"},
    )
    b = LineInfo(
        Line(Point(0, 1000), Point(100, 1000), id=1),
        {"system-name": "B", "system-type": "return"},
    )
    analyzer = TopologyAnalyzer(AutoCadInput([a, b], [], [a, b]))
    systems = [
        DuctSystem.from_topology(analyzer.analyze(root), config, duct_sizer)
        for root in (a, b)
    ]
    assert [system.system_name for system in systems] == ["A", "B"]
    assert [system.system_type for system in systems] == [
        SystemType.Supply,
        SystemType.Return,
    ]
    assert [system.dftree.root.component.ref_line_id for system in systems] == [0, 1]


def test_duct_length_uses_xy_without_storing_or_changing_source_geometry(config):
    source = info(0, None, (0, 0, 900), (300, 400, -900))
    tree = build(config, [source])
    duct = tree.root.component
    assert duct.length == 500
    assert duct.ref_line_id == source.ref_line_id
    assert not hasattr(duct, "raw")
    assert source.raw.start.to_list3d() == [0, 0, 900]
    assert source.raw.end.to_list3d() == [300, 400, -900]
