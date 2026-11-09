"""Explicit fitting skeletons and duct endpoints for a rectangular plan drawing."""

from math import cos, pi, sin
from pathlib import Path

import pytest

from dsd.analyzers.models import DuctInfo, SystemTopology
from dsd.config_builder import ConfigBuilder
from dsd.ductsystem import DuctSystem, SystemType
from dsd.ductsystem.sizing import EqualVelocityDuctSizer
from dsd.ductsystem.visitors import GeometryConstructorVisitor
from dsd.geometry.builders.rectangular import RectangularGeometricRepresentationBuilder
from dsd.geometry.placement import (
    PlacementContextManager,
    PlacementError,
    SourceGeometryRepository,
)
from dsd.geometry.primitives import Arc, Line, Point


@pytest.fixture
def config():
    return ConfigBuilder(
        Path(__file__).parent / "fixtures" / "duct_system.yaml"
    ).build()


def point(x, y, angle=0, offset=(0, 0)):
    return Point(
        offset[0] + x * cos(angle) - y * sin(angle),
        offset[1] + x * sin(angle) + y * cos(angle),
    )


def build_main_network(angle=0, offset=(0, 0)):
    return SystemTopology(
        "Geometry",
        [
            DuctInfo(
                id=0,
                parent_id=None,
                ref_line_id=100,
                flow=1000,
                width=400,
                height=200,
                raw=Line(
                    point(0, 0, angle, offset), point(3000, 0, angle, offset), id=0
                ),
            ),
            DuctInfo(
                id=1,
                parent_id=0,
                ref_line_id=101,
                flow=600,
                width=300,
                height=150,
                raw=Line(
                    point(3000, 0, angle, offset), point(6000, 0, angle, offset), id=1
                ),
            ),
            DuctInfo(
                id=2,
                parent_id=0,
                ref_line_id=102,
                flow=400,
                width=200,
                height=100,
                raw=Line(
                    point(3000, 0, angle, offset),
                    point(3000, 3000, angle, offset),
                    id=2,
                ),
            ),
            DuctInfo(
                id=3,
                parent_id=2,
                ref_line_id=103,
                flow=400,
                width=200,
                height=100,
                raw=Line(
                    point(3000, 3000, angle, offset),
                    point(5000, 3000, angle, offset),
                    id=3,
                ),
            ),
        ],
        [],
        SystemType.Supply,
    )


def segment(line):
    return line.start.x, line.start.y, line.end.x, line.end.y


@pytest.mark.parametrize("angle", [0, pi / 2, pi / 4, -pi / 2])
def test_fittings_first_then_ducts_connect_to_their_skeletons(config, angle):
    offset = (100, 200)
    topology = build_main_network(angle, offset)
    repo = SourceGeometryRepository.from_topology(topology)
    system = DuctSystem.from_topology(
        topology, config.ductsystem, EqualVelocityDuctSizer(config.sizing)
    )
    system.size()
    placement = PlacementContextManager(system.dftree, repo)
    builder = RectangularGeometricRepresentationBuilder(config.ductsystem.fittings)
    visitor = GeometryConstructorVisitor(placement, builder)

    representations = visitor.construct()

    # Reference coordinates before rotating/translating the complete network.
    expected_skeletons = {
        0: [(0, 0, 3600, 0)],
        1: [(3900, 0, 6000, 0)],
        2: [(3000, 350, 3000, 2600)],
        3: [(3400, 3000, 5000, 3000)],
        4: [(3000, 200, 3000, 350)],  # shoe starts at main side, then extends 150 mm
        5: [(3000, 2600, 3000, 3000), (3000, 3000, 3400, 3000)],
        6: [(3600, 0, 3900, 0)],  # reducer inlet: junction + 1.5*400
    }
    assert set(representations) == set(expected_skeletons)
    for identifier, expected in expected_skeletons.items():
        skeleton = representations[identifier].layout_skeleton
        assert len(skeleton) == len(expected)
        for line, (sx, sy, ex, ey) in zip(skeleton, expected):
            start, end = point(sx, sy, angle, offset), point(ex, ey, angle, offset)
            assert segment(line) == pytest.approx(
                (start.x, start.y, end.x, end.y), abs=1e-7
            )
    assert {
        node.component.id: node.component.length
        for node in system.preorder_traversal()
        if hasattr(node.component, "ref_line_id")
    } == pytest.approx({0: 3600, 1: 2100, 2: 2250, 3: 1600})
    assert {
        identifier: len(rep.primitives) for identifier, rep in representations.items()
    } == {
        0: 4,
        1: 4,
        2: 4,
        3: 4,
        4: 4,
        5: 4,
        6: 4,
    }
    # Original processed source lines stay unchanged despite connected duct lengths.
    assert repo.get_line(0).length() == pytest.approx(3000)
    assert topology.duct_infos[0].raw.length() == pytest.approx(3000)
    normalized_elbow = builder.normalized_representations[5]
    repeated = visitor.construct()
    assert builder.normalized_representations[5] is normalized_elbow
    for identifier in representations:
        for first, second in zip(
            representations[identifier].layout_skeleton,
            repeated[identifier].layout_skeleton,
        ):
            assert segment(first) == pytest.approx(segment(second), abs=1e-7)
    assert system.dftree.root.component.length == pytest.approx(3600)


def test_terminal_main_extends_and_endcap_has_no_skeleton(config):
    topology = SystemTopology(
        "Terminal",
        [
            DuctInfo(
                id=0,
                parent_id=None,
                ref_line_id=100,
                flow=1000,
                width=400,
                height=200,
                raw=Line(Point(0, 0), Point(3000, 0), id=0),
            ),
            DuctInfo(
                id=1,
                parent_id=0,
                ref_line_id=101,
                flow=400,
                width=200,
                height=100,
                raw=Line(Point(3000, 0), Point(3000, 3000), id=1),
            ),
            DuctInfo(
                id=2,
                parent_id=0,
                ref_line_id=102,
                flow=600,
                width=300,
                height=150,
                raw=Line(Point(3000, 0), Point(3000, -3000), id=2),
            ),
        ],
        [],
        SystemType.Return,
    )
    repo = SourceGeometryRepository.from_topology(topology)
    system = DuctSystem.from_topology(
        topology, config.ductsystem, EqualVelocityDuctSizer(config.sizing)
    )
    system.size()
    visitor = GeometryConstructorVisitor(
        PlacementContextManager(system.dftree, repo),
        RectangularGeometricRepresentationBuilder(config.ductsystem.fittings),
    )

    representations = visitor.construct()

    assert segment(representations[0].layout_skeleton[0]) == (0, 0, 3600, 0)
    assert segment(representations[1].layout_skeleton[0]) == pytest.approx(
        (3000, 350, 3000, 3000)
    )
    assert segment(representations[2].layout_skeleton[0]) == pytest.approx(
        (3000, -350, 3000, -3000)
    )
    assert representations[5].layout_skeleton == []
    assert segment(representations[5].primitives[0]) == (3600, -200, 3600, 200)
    assert system.dftree.root.component.length == 3000 + 2 * 300
    assert repo.get_line(0).end.x == 3000
    assert (
        len(
            [
                node
                for node in system.preorder_traversal()
                if hasattr(node.component, "ref_line_id")
            ]
        )
        == 3
    )
    # Both bevels widen downstream along the main +X direction.
    assert max(line.start.x for line in representations[3].primitives) == pytest.approx(
        3250
    )
    assert max(line.start.x for line in representations[4].primitives) == pytest.approx(
        3300
    )


def test_fittings_that_consume_a_duct_report_error_before_lengths_change(config):
    topology = SystemTopology(
        "Too short",
        [
            DuctInfo(
                id=0,
                parent_id=None,
                ref_line_id=100,
                flow=1000,
                width=200,
                height=100,
                raw=Line(Point(0, 0), Point(100, 0), id=0),
            ),
            DuctInfo(
                id=1,
                parent_id=0,
                ref_line_id=101,
                flow=1000,
                width=200,
                height=100,
                raw=Line(Point(100, 0), Point(100, 100), id=1),
            ),
        ],
        [],
        SystemType.Supply,
    )
    system = DuctSystem.from_topology(
        topology, config.ductsystem, EqualVelocityDuctSizer(config.sizing)
    )
    system.size()
    visitor = GeometryConstructorVisitor(
        PlacementContextManager(
            system.dftree, SourceGeometryRepository.from_topology(topology)
        ),
        RectangularGeometricRepresentationBuilder(config.ductsystem.fittings),
    )
    with pytest.raises(PlacementError, match="no positive length"):
        visitor.construct()
    assert system.dftree.root.component.length == 100
    assert system.dftree.root.children[0].children[0].component.length == 100


def test_direct_duct_visit_requires_its_fittings_to_be_constructed(config):
    topology = build_main_network()
    system = DuctSystem.from_topology(
        topology, config.ductsystem, EqualVelocityDuctSizer(config.sizing)
    )
    system.size()
    manager = PlacementContextManager(
        system.dftree, SourceGeometryRepository.from_topology(topology)
    )
    with pytest.raises(PlacementError, match="fitting geometry"):
        manager.find_context(system.dftree.root.component)
