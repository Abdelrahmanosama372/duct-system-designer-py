"""Explicit duct networks and expected results for the complete sizing pipeline."""

from copy import deepcopy
from math import pi
from pathlib import Path

import pytest

from dsd.analyzers.models import DuctInfo, SystemTopology
from dsd.config_builder import ConfigBuilder
from dsd.ductsystem import DuctSystem, SystemType
from dsd.ductsystem.models.rectangular import (
    RectangularDuct,
    RectangularElbow,
    RectangularEndcap,
    RectangularReducer,
    RectangularShoeTakeoff,
)
from dsd.ductsystem.sizing import EqualFrictionDuctSizer, EqualVelocityDuctSizer
from dsd.ductsystem.sizing.tree_helpers import DuctSizingError
from dsd.ductsystem.visitors import AreaCalculatorVisitor
from dsd.geometry.primitives import Line, Point


@pytest.fixture
def config():
    return ConfigBuilder(
        Path(__file__).parent / "fixtures" / "duct_system.yaml"
    ).build()


def build_main_network(system_type):
    """Main 1000 CFM -> branch 400 CFM with an elbow + main continuation 600 CFM."""
    return SystemTopology(
        system_name="Main with a side branch",
        system_type=system_type,
        duct_infos=[
            DuctInfo(
                id=0,
                parent_id=None,
                flow=1000,
                ref_line_id=100,
                raw=Line(Point(0, 0), Point(3000, 0), id=0),
            ),
            DuctInfo(
                id=1,
                parent_id=0,
                flow=600,
                ref_line_id=101,
                raw=Line(Point(3000, 0), Point(6000, 0), id=1),
            ),
            DuctInfo(
                id=2,
                parent_id=0,
                flow=400,
                ref_line_id=102,
                raw=Line(Point(3000, 0), Point(3000, 3000), id=2),
            ),
            DuctInfo(
                id=3,
                parent_id=2,
                flow=400,
                ref_line_id=103,
                raw=Line(Point(3000, 3000), Point(5000, 3000), id=3),
            ),
        ],
        air_terminal_infos=[],
    )


def build_terminal_network(system_type):
    """Main 1000 CFM ends in opposite branches: left 400 CFM and right 600 CFM."""
    return SystemTopology(
        system_name="Main ending in two branches",
        system_type=system_type,
        duct_infos=[
            DuctInfo(
                id=0,
                parent_id=None,
                flow=1000,
                ref_line_id=100,
                raw=Line(Point(0, 0), Point(3000, 0), id=0),
            ),
            DuctInfo(
                id=1,
                parent_id=0,
                flow=400,
                ref_line_id=101,
                raw=Line(Point(3000, 0), Point(3000, 3000), id=1),
            ),
            DuctInfo(
                id=2,
                parent_id=0,
                flow=600,
                ref_line_id=102,
                raw=Line(Point(3000, 0), Point(3000, -3000), id=2),
            ),
        ],
        air_terminal_infos=[],
    )


@pytest.mark.parametrize("system_type", [SystemType.Supply, SystemType.Return])
@pytest.mark.parametrize(
    "sizer_class,expected_dimensions",
    [
        (
            EqualVelocityDuctSizer,
            {
                # component ID: (width mm, height mm)
                0: (450, 225),
                1: (350, 175),
                2: (275, 150),
                3: (275, 150),
                4: (275, 150),
                5: (275, 150),
                6: (450, 225),
            },
        ),
        (
            EqualFrictionDuctSizer,
            {
                0: (450, 250),
                1: (400, 200),
                2: (350, 175),
                3: (350, 175),
                4: (350, 175),
                5: (350, 175),
                6: (450, 250),
            },
        ),
    ],
)
def test_main_network_sizing(config, system_type, sizer_class, expected_dimensions):
    topology = build_main_network(system_type)
    original_topology = deepcopy(topology)
    system = DuctSystem.from_topology(
        topology, config.ductsystem, sizer_class(config.sizing)
    )

    system.size()

    nodes = {node.component.id: node for node in system.preorder_traversal()}
    assert system.system_type is system_type
    assert {
        identifier: (
            type(node.component),
            None if node.parent is None else node.parent.component.id,
            [child.component.id for child in node.children],
        )
        for identifier, node in nodes.items()
    } == {
        # ID: (component type, parent ID, children IDs)
        0: (RectangularDuct, None, [4, 6]),
        4: (RectangularShoeTakeoff, 0, [2]),
        2: (RectangularDuct, 4, [5]),
        5: (RectangularElbow, 2, [3]),
        3: (RectangularDuct, 5, []),
        6: (RectangularReducer, 0, [1]),
        1: (RectangularDuct, 6, []),
    }
    assert {
        identifier: (node.component.width, node.component.height)
        for identifier, node in nodes.items()
    } == expected_dimensions
    assert {
        identifier: (
            node.component.flow,
            node.component.ref_line_id,
            node.component.length,
        )
        for identifier, node in nodes.items()
        if isinstance(node.component, RectangularDuct)
    } == {
        # Duct ID: (flow CFM, source line ID, length mm)
        0: (1000, 100, 3000),
        1: (600, 101, 3000),
        2: (400, 102, 3000),
        3: (400, 103, 2000),
    }
    shoe = nodes[4].component
    assert (shoe.side, shoe.branch_duct_id, shoe.flow) == ("left", 2, 400)
    assert nodes[6].parent is nodes[4].parent is nodes[0]

    assert (shoe.width, shoe.height) == expected_dimensions[2]
    assert shoe.takeoff_length == 150
    assert shoe.width1 == expected_dimensions[2][0] + 150

    elbow = nodes[5].component
    assert elbow.angle == -pi / 2
    assert (
        elbow.inside_radius(config.ductsystem.fittings.elbow_inside_radius_ratio)
        == expected_dimensions[2][0] * 1.5
    )
    assert (
        elbow.centerline_radius(config.ductsystem.fittings.elbow_inside_radius_ratio)
        == expected_dimensions[2][0] * 2
    )

    reducer = nodes[6].component
    assert (reducer.inlet_width, reducer.inlet_height) == expected_dimensions[0]
    assert (reducer.outlet_width, reducer.outlet_height) == expected_dimensions[1]
    assert (reducer.flow, reducer.length) == (600, 300)
    assert topology == original_topology

    # A second sizing run keeps the same nodes and dimensions, with one reducer.
    system.size()
    assert list(system.preorder_traversal()) == list(nodes.values())
    assert {
        node.component.id: (node.component.width, node.component.height)
        for node in system.preorder_traversal()
    } == expected_dimensions


@pytest.mark.parametrize("system_type", [SystemType.Supply, SystemType.Return])
@pytest.mark.parametrize(
    "sizer_class,expected_dimensions",
    [
        (
            EqualVelocityDuctSizer,
            {
                0: (450, 225),
                1: (275, 150),
                2: (350, 175),
                3: (275, 150),
                4: (350, 175),
                5: (450, 225),
            },
        ),
        (
            EqualFrictionDuctSizer,
            {
                0: (450, 250),
                1: (350, 175),
                2: (400, 200),
                3: (350, 175),
                4: (400, 200),
                5: (450, 250),
            },
        ),
    ],
)
def test_terminal_network_sizing(config, system_type, sizer_class, expected_dimensions):
    topology = build_terminal_network(system_type)
    original_topology = deepcopy(topology)
    system = DuctSystem.from_topology(
        topology, config.ductsystem, sizer_class(config.sizing)
    )

    system.size()

    nodes = {node.component.id: node for node in system.preorder_traversal()}
    assert system.system_type is system_type
    assert {
        identifier: (
            type(node.component),
            None if node.parent is None else node.parent.component.id,
            [child.component.id for child in node.children],
        )
        for identifier, node in nodes.items()
    } == {
        0: (RectangularDuct, None, [3, 4, 5]),
        3: (RectangularShoeTakeoff, 0, [1]),
        1: (RectangularDuct, 3, []),
        4: (RectangularShoeTakeoff, 0, [2]),
        2: (RectangularDuct, 4, []),
        5: (RectangularEndcap, 0, []),
    }
    assert {
        identifier: (node.component.width, node.component.height)
        for identifier, node in nodes.items()
    } == expected_dimensions
    assert {
        identifier: (
            node.component.flow,
            node.component.ref_line_id,
            node.component.length,
        )
        for identifier, node in nodes.items()
        if isinstance(node.component, RectangularDuct)
    } == {
        0: (1000, 100, 3000),
        1: (400, 101, 3000),
        2: (600, 102, 3000),
    }
    assert {
        identifier: (
            node.component.side,
            node.component.flow,
            node.component.branch_duct_id,
            node.component.width1,
            node.component.takeoff_length,
        )
        for identifier, node in nodes.items()
        if isinstance(node.component, RectangularShoeTakeoff)
    } == {
        3: ("left", 400, 1, expected_dimensions[1][0] + 150, 150),
        4: ("right", 600, 2, expected_dimensions[2][0] + 150, 150),
    }
    assert nodes[5].parent is nodes[0] and nodes[5].children == []
    assert nodes[5].component.flow == 0
    assert topology == original_topology

    # No extra duct, reducer, or main-length change on repeated sizing.
    system.size()
    assert list(system.preorder_traversal()) == list(nodes.values())
    assert {
        node.component.id: (node.component.width, node.component.height)
        for node in system.preorder_traversal()
    } == expected_dimensions


@pytest.mark.parametrize("system_type", [SystemType.Supply, SystemType.Return])
@pytest.mark.parametrize(
    "sizer_class", [EqualVelocityDuctSizer, EqualFrictionDuctSizer]
)
def test_supplied_parent_dimensions_are_preserved(config, system_type, sizer_class):
    topology = build_main_network(system_type)
    topology.duct_infos[0].width = 300
    topology.duct_infos[0].height = 400
    system = DuctSystem.from_topology(
        topology, config.ductsystem, sizer_class(config.sizing)
    )

    system.size()

    ducts = {
        node.component.id: node.component
        for node in system.preorder_traversal()
        if isinstance(node.component, RectangularDuct)
    }
    assert (ducts[0].width, ducts[0].height) == (300, 400)
    assert ducts[1].width == 300
    assert ducts[2].width <= 300
    assert (ducts[3].width, ducts[3].height) == (ducts[2].width, ducts[2].height)


@pytest.mark.parametrize("system_type", [SystemType.Supply, SystemType.Return])
@pytest.mark.parametrize(
    "sizer_class", [EqualVelocityDuctSizer, EqualFrictionDuctSizer]
)
@pytest.mark.parametrize("single_dimension", ["width", "height"])
def test_partial_supplied_dimensions_are_rejected(
    config, system_type, sizer_class, single_dimension
):
    topology = build_main_network(system_type)
    setattr(topology.duct_infos[0], single_dimension, 300)

    with pytest.raises(ValueError, match="width and height must be supplied together"):
        DuctSystem.from_topology(
            topology, config.ductsystem, sizer_class(config.sizing)
        )


@pytest.mark.parametrize("system_type", [SystemType.Supply, SystemType.Return])
@pytest.mark.parametrize(
    "sizer_class", [EqualVelocityDuctSizer, EqualFrictionDuctSizer]
)
def test_incompatible_elbow_dimensions_are_rejected(config, system_type, sizer_class):
    topology = SystemTopology(
        system_name="Elbow with incompatible ducts",
        system_type=system_type,
        duct_infos=[
            DuctInfo(
                id=0,
                parent_id=None,
                flow=1000,
                width=400,
                height=200,
                ref_line_id=100,
                raw=Line(Point(0, 0), Point(3000, 0), id=0),
            ),
            DuctInfo(
                id=1,
                parent_id=0,
                flow=1000,
                width=300,
                height=150,
                ref_line_id=101,
                raw=Line(Point(3000, 0), Point(3000, 3000), id=1),
            ),
        ],
        air_terminal_infos=[],
    )
    system = DuctSystem.from_topology(
        topology, config.ductsystem, sizer_class(config.sizing)
    )

    with pytest.raises(DuctSizingError, match="Reducing elbows are not supported"):
        system.size()

    assert [type(node.component) for node in system.preorder_traversal()] == [
        RectangularDuct,
        RectangularElbow,
        RectangularDuct,
    ]
    assert [
        (node.component.width, node.component.height)
        for node in system.preorder_traversal()
        if isinstance(node.component, RectangularDuct)
    ] == [
        (400, 200),
        (300, 150),
    ]


def test_main_network_sheet_metal_areas(config):
    topology = build_main_network(SystemType.Supply)
    for info, (width, height) in zip(
        topology.duct_infos, [(400, 200), (300, 150), (200, 100), (200, 100)]
    ):
        info.width, info.height = width, height
    system = DuctSystem.from_topology(
        topology, config.ductsystem, EqualVelocityDuctSizer(config.sizing)
    )
    system.size()
    visitor = AreaCalculatorVisitor(config.ductsystem.fittings)

    assert {
        node.component.id: node.component.accept(visitor)
        for node in system.preorder_traversal()
    } == pytest.approx(
        {
            # Component ID: net sheet-metal area in m².
            0: 3.6,
            1: 2.7,
            2: 1.8,
            3: 1.2,
            4: 0.11871320343559643,  # open shoe
            5: 0.3769911184307752,  # smooth elbow
            6: 0.317176249409084,  # centered reducer
        }
    )
    assert visitor.total_area_m2 == pytest.approx(10.112880571275455)


def test_terminal_network_sheet_metal_areas_include_endcap(config):
    topology = build_terminal_network(SystemType.Supply)
    for info, (width, height) in zip(
        topology.duct_infos, [(400, 200), (200, 100), (300, 150)]
    ):
        info.width, info.height = width, height
    system = DuctSystem.from_topology(
        topology, config.ductsystem, EqualVelocityDuctSizer(config.sizing)
    )
    system.size()
    visitor = AreaCalculatorVisitor(config.ductsystem.fittings)

    assert {
        node.component.id: node.component.accept(visitor)
        for node in system.preorder_traversal()
    } == pytest.approx(
        {
            0: 3.6,  # full main area, with no shoe-opening deduction
            1: 1.8,
            2: 2.7,
            3: 0.11871320343559643,
            4: 0.16681980515339464,
            5: 0.08,  # flat endcap
        }
    )
    assert visitor.total_area_m2 == pytest.approx(8.465533008588992)
