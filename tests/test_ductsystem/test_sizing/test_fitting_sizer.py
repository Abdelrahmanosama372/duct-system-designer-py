from dataclasses import replace

import pytest

from dsd.ductsystem.models.rectangular import (
    RectangularDuct,
    RectangularElbow,
    RectangularEndcap,
    RectangularReducer,
    RectangularShoeTakeoff,
)
from dsd.ductsystem.sizing.fitting_sizer import FittingSizingPass
from dsd.ductsystem.sizing.tree_helpers import DuctSizingError


def test_full_pipeline_sizes_main_reducer_and_shoe_branch(
    duct_info, system_factory, recording_sizer
):
    sizer = recording_sizer({1000: (450, 225), 400: (300, 150), 600: (350, 175)})
    system = system_factory(
        [
            duct_info(0, None, (0, 0), (100, 0), 1000),
            duct_info(1, 0, (100, 0), (200, 0), 600),
            duct_info(2, 0, (100, 0), (100, 100), 400),
        ],
        sizer,
    )
    system.size()
    nodes = list(system.preorder_traversal())
    shoe = next(
        node.component
        for node in nodes
        if isinstance(node.component, RectangularShoeTakeoff)
    )
    reducer = next(
        node.component
        for node in nodes
        if isinstance(node.component, RectangularReducer)
    )
    assert (shoe.width, shoe.height, shoe.takeoff_length, shoe.width1) == (
        300,
        150,
        150,
        450,
    )
    assert (
        reducer.inlet_width,
        reducer.inlet_height,
        reducer.outlet_width,
        reducer.outlet_height,
        reducer.length,
    ) == (450, 225, 350, 175, 300)
    before = [node.component.id for node in nodes]
    system.size()
    assert [node.component.id for node in system.preorder_traversal()] == before
    assert len(sizer.calls) == 3


def test_terminal_junction_sizes_direct_endcap_without_extending_main(
    duct_info, system_factory, recording_sizer
):
    sizer = recording_sizer({1000: (450, 225), 400: (300, 150), 600: (350, 175)})
    system = system_factory(
        [
            duct_info(0, None, (0, 0), (100, 0), 1000),
            duct_info(1, 0, (100, 0), (100, 100), 400),
            duct_info(2, 0, (100, 0), (100, -100), 600),
        ],
        sizer,
    )
    system.size()
    root = system.dftree.root
    cap_node = root.children[2]
    assert isinstance(cap_node.component, RectangularEndcap)
    assert cap_node.parent is root and cap_node.children == []
    assert (cap_node.component.width, cap_node.component.height) == (450, 225)
    assert root.component.length == 100
    assert (
        len(
            [
                node
                for node in system.preorder_traversal()
                if isinstance(node.component, RectangularDuct)
            ]
        )
        == 3
    )
    assert not any(
        isinstance(node.component, RectangularReducer)
        for node in system.preorder_traversal()
    )
    assert [node.component.flow for node in root.children] == [400, 600, 0]


def test_elbow_uses_unchanged_duct_dimensions_and_configured_radius(
    duct_info, system_factory
):
    system = system_factory(
        [
            duct_info(0, None, (0, 0), (100, 0), 1000, 400, 200),
            duct_info(1, 0, (100, 0), (100, 100), 1000, 400, 200),
        ]
    )
    system.size()
    elbow = next(
        node.component
        for node in system.preorder_traversal()
        if isinstance(node.component, RectangularElbow)
    )
    assert (elbow.width, elbow.height) == (400, 200)
    assert elbow.inside_radius(system.config.fittings.elbow_inside_radius_ratio) == 600
    assert (
        elbow.centerline_radius(system.config.fittings.elbow_inside_radius_ratio) == 800
    )


def test_reducing_elbow_is_reported(duct_info, system_factory):
    system = system_factory(
        [
            duct_info(0, None, (0, 0), (100, 0), 1000, 400, 200),
            duct_info(1, 0, (100, 0), (100, 100), 1000, 300, 150),
        ]
    )
    with pytest.raises(DuctSizingError, match="Reducing elbows"):
        system.size()
    assert len(list(system.preorder_traversal())) == 3


def test_fitting_lengths_follow_configuration(duct_info, system_factory):
    system = system_factory(
        [
            duct_info(0, None, (0, 0), (100, 0), 1000, 400, 200),
            duct_info(1, 0, (100, 0), (200, 0), 500, 300, 150),
        ]
    )
    system.insert_reducers()
    FittingSizingPass(replace(system.config.fittings, reducer_length=450)).apply(
        system.dftree
    )
    reducer = system.dftree.root.children[0].component
    assert reducer.length == 450


@pytest.mark.parametrize("method", ["friction", "velocity"])
@pytest.mark.parametrize("system_type", ["supply", "return"])
def test_real_sizers_integrate_for_both_system_types(
    duct_info, system_factory, method, system_type
):
    from dsd.config_builder import ConfigBuilder
    from dsd.ductsystem import SystemType
    from dsd.ductsystem.sizing import EqualFrictionDuctSizer, EqualVelocityDuctSizer

    sizing = ConfigBuilder("config.yaml").build().sizing
    sizer = (
        EqualFrictionDuctSizer(sizing)
        if method == "friction"
        else EqualVelocityDuctSizer(sizing)
    )
    system = system_factory(
        [
            duct_info(0, None, (0, 0), (100, 0), 1000),
            duct_info(1, 0, (100, 0), (200, 0), 600),
            duct_info(2, 0, (100, 0), (100, 100), 400),
        ],
        sizer,
        SystemType(system_type),
    )
    system.size()
    assert system.sizer is sizer
    for node in system.preorder_traversal():
        assert node.component.width > 0 and node.component.height > 0
        if isinstance(node.component, RectangularDuct):
            assert node.component.ref_line_id in (100, 101, 102)
            assert not hasattr(node.component, "raw")
