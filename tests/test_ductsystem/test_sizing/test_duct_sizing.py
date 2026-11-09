import pytest

from dsd.ductsystem.models.rectangular import RectangularDuct
from dsd.ductsystem.sizing import SizingContext
from dsd.ductsystem.sizing.tree_helpers import DuctSizingError


def test_preorder_sizes_parent_before_children_across_fittings(
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
    system.size_ducts()
    assert sizer.calls == [
        SizingContext(1000),
        SizingContext(400, 450),
        SizingContext(600, 450),
    ]
    assert all(
        node.component.width is None
        for node in system.preorder_traversal()
        if node.is_duct_fitting()
    )


def test_supplied_sizes_are_preserved_and_used_as_parent_width(
    duct_info, system_factory, recording_sizer
):
    sizer = recording_sizer({500: (300, 175)})
    system = system_factory(
        [
            duct_info(0, None, (0, 0), (100, 0), 1000, 425, 225),
            duct_info(1, 0, (100, 0), (200, 0), 500),
        ],
        sizer,
    )
    system.size_ducts()
    assert sizer.calls == [SizingContext(500, 425)]
    assert (
        system.dftree.root.component.width,
        system.dftree.root.component.height,
    ) == (425, 225)


def test_terminal_junction_keeps_original_ducts_and_lengths(
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
    system.size_ducts()
    ducts = [
        node.component
        for node in system.preorder_traversal()
        if isinstance(node.component, RectangularDuct)
    ]
    assert [duct.id for duct in ducts] == [0, 1, 2]
    assert [duct.length for duct in ducts] == [100, 100, 100]
    assert [context.flow for context in sizer.calls] == [1000, 400, 600]


def test_partial_dimensions_rejected_even_after_construction(duct_info, system_factory):
    system = system_factory([duct_info(0, None, (0, 0), (100, 0))])
    system.dftree.root.component.width = 300
    with pytest.raises(DuctSizingError, match="together"):
        system.size_ducts()


def test_unsized_zero_flow_regular_duct_is_reported(duct_info, system_factory):
    system = system_factory([duct_info(0, None, (0, 0), (100, 0), 0)])
    with pytest.raises(DuctSizingError, match="positive airflow"):
        system.size_ducts()
