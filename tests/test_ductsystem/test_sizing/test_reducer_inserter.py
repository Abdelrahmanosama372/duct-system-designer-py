import pytest

from dsd.ductsystem.models.rectangular import (
    RectangularDuct,
    RectangularReducer,
    RectangularShoeTakeoff,
)
from dsd.ductsystem.sizing.tree_helpers import DuctSizingError


def test_reducers_rewire_each_changed_dimension_and_are_idempotent(
    duct_info, system_factory
):
    system = system_factory(
        [
            duct_info(0, None, (0, 0), (100, 0), 1000, 400, 200),
            duct_info(1, 0, (100, 0), (200, 0), 700, 300, 200),
            duct_info(2, 1, (200, 0), (300, 0), 400, 300, 150),
        ]
    )
    system.insert_reducers()
    nodes = list(system.preorder_traversal())
    assert [type(node.component) for node in nodes] == [
        RectangularDuct,
        RectangularReducer,
        RectangularDuct,
        RectangularReducer,
        RectangularDuct,
    ]
    assert [node.parent for node in nodes] == [None, *nodes[:-1]]
    assert len({node.component.id for node in nodes}) == 5
    assert [
        node.component.ref_line_id
        for node in nodes
        if isinstance(node.component, RectangularDuct)
    ] == [100, 101, 102]
    assert all(
        node.component.length is None
        for node in nodes
        if isinstance(node.component, RectangularReducer)
    )
    system.insert_reducers()
    assert list(system.preorder_traversal()) == nodes


def test_matching_adjacent_ducts_need_no_reducer(duct_info, system_factory):
    system = system_factory(
        [
            duct_info(0, None, (0, 0), (100, 0), 1000, 400, 200),
            duct_info(1, 0, (100, 0), (200, 0), 500, 400, 200),
        ]
    )
    system.insert_reducers()
    assert len(list(system.preorder_traversal())) == 2


def test_real_main_continuation_gets_reducer_but_side_branch_does_not(
    duct_info, system_factory
):
    system = system_factory(
        [
            duct_info(0, None, (0, 0), (100, 0), 1000, 450, 225),
            duct_info(1, 0, (100, 0), (200, 0), 600, 350, 175),
            duct_info(2, 0, (100, 0), (100, 100), 400, 300, 150),
        ]
    )
    system.insert_reducers()
    shoe = system.dftree.root.children[0]
    assert isinstance(shoe.component, RectangularShoeTakeoff)
    assert shoe.children[0].component.id == 2
    assert len(shoe.children) == 1
    reducer = system.dftree.root.children[1]
    assert reducer.parent is shoe.parent is system.dftree.root
    assert isinstance(reducer.component, RectangularReducer)
    assert reducer.children[0].component.id == 1
    assert reducer.children[0].parent is reducer
    system.insert_reducers()
    assert (
        len(
            [
                node
                for node in system.preorder_traversal()
                if isinstance(node.component, RectangularReducer)
            ]
        )
        == 1
    )


def test_unsized_ducts_are_rejected_before_rewiring(duct_info, system_factory):
    system = system_factory(
        [duct_info(0, None, (0, 0), (100, 0)), duct_info(1, 0, (100, 0), (200, 0))]
    )
    with pytest.raises(DuctSizingError, match="not been sized"):
        system.insert_reducers()
    assert system.dftree.root.children[0].component.id == 1
