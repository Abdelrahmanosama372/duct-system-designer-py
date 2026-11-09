import pytest

from dsd.ductsystem import DuctFittingTree, SheetMetalNode
from dsd.ductsystem.models.rectangular import RectangularDuct


def test_level_order_traversal_and_connected_components(properties):
    nodes = [
        SheetMetalNode(RectangularDuct(**{**properties, "id": n})) for n in range(4)
    ]
    nodes[0].add_child(nodes[1])
    nodes[0].add_child(nodes[2])
    nodes[1].add_child(nodes[3])
    tree = DuctFittingTree(nodes[0])
    assert list(tree.level_order_traversal()) == nodes
    assert tree.connected_components == nodes
    with pytest.raises(ValueError, match="root"):
        DuctFittingTree(nodes[1])


def test_duplicate_component_ids_are_rejected(properties):
    root = SheetMetalNode(RectangularDuct(**properties))
    root.add_child(SheetMetalNode(RectangularDuct(**properties)))
    with pytest.raises(ValueError, match="IDs"):
        list(DuctFittingTree(root).level_order_traversal())


def test_preorder_finishes_each_branch_before_next_sibling(properties):
    nodes = [
        SheetMetalNode(RectangularDuct(**{**properties, "id": n})) for n in range(6)
    ]
    nodes[0].add_child(nodes[1])
    nodes[0].add_child(nodes[2])
    nodes[1].add_child(nodes[3])
    nodes[1].add_child(nodes[4])
    nodes[2].add_child(nodes[5])
    tree = DuctFittingTree(nodes[0])
    assert [node.component.id for node in tree.preorder_traversal()] == [
        0,
        1,
        3,
        4,
        2,
        5,
    ]
    assert [node.component.id for node in tree.level_order_traversal()] == [
        0,
        1,
        2,
        3,
        4,
        5,
    ]
