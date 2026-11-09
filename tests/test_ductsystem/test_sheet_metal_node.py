import pytest

from dsd.ductsystem import SheetMetalNode
from dsd.ductsystem.models.rectangular import RectangularDuct, RectangularElbow


def test_parent_child_links_and_root(properties):
    root = SheetMetalNode(RectangularDuct(**properties))
    child = SheetMetalNode(RectangularDuct(**{**properties, "id": 1}))
    assert root.parent is None
    root.add_child(child)
    assert child.parent is root
    assert root.children == [child]
    assert not root.is_duct_fitting()
    assert SheetMetalNode(RectangularElbow(angle=1, **properties)).is_duct_fitting()


def test_node_cannot_be_reparented_or_create_cycle(properties):
    root = SheetMetalNode(RectangularDuct(**properties))
    child = SheetMetalNode(RectangularDuct(**{**properties, "id": 1}))
    root.add_child(child)
    with pytest.raises(ValueError, match="cycle"):
        child.add_child(root)
    with pytest.raises(ValueError, match="already attached"):
        root.add_child(child)
    with pytest.raises(ValueError, match="cycle"):
        root.add_child(root)


def test_insert_between_preserves_siblings_and_parent_links(properties):
    from dsd.ductsystem.models.rectangular import RectangularReducer

    parent = SheetMetalNode(RectangularDuct(**properties))
    child = SheetMetalNode(RectangularDuct(**{**properties, "id": 1}))
    sibling = SheetMetalNode(RectangularDuct(**{**properties, "id": 2}))
    reducer = SheetMetalNode(RectangularReducer(**{**properties, "id": 3}))
    parent.add_child(child)
    parent.add_child(sibling)
    parent.insert_between(child, reducer)
    assert parent.children == [reducer, sibling]
    assert reducer.parent is parent
    assert reducer.children == [child]
    assert child.parent is reducer
    assert sibling.parent is parent
    with pytest.raises(ValueError, match="not attached"):
        parent.insert_between(
            child, SheetMetalNode(RectangularDuct(**{**properties, "id": 4}))
        )
