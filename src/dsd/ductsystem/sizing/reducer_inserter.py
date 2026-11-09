"""Insert reducer nodes in a dedicated traversal, independently of fitting sizing."""

from itertools import count

from ..duct_fitting_tree import DuctFittingTree
from ..models.rectangular import (
    RectangularDuct,
    RectangularReducer,
)
from ..sheet_metal_node import SheetMetalNode
from .tree_helpers import dimensions


class ReducerInserter:
    def apply(self, tree: DuctFittingTree) -> None:
        nodes = list(tree.preorder_traversal())
        identifiers = count(max(node.component.id for node in nodes) + 1)
        connections = []
        for parent in nodes:
            if not isinstance(parent.component, RectangularDuct):
                continue
            upstream = parent.component
            for child in parent.children:
                duct = child.component
                if not isinstance(duct, RectangularDuct):
                    continue
                if dimensions(upstream) != dimensions(duct):
                    connections.append((parent, child))
        for parent, child in connections:
            duct = child.component
            reducer = SheetMetalNode(
                RectangularReducer(
                    id=next(identifiers),
                    flow=duct.flow,
                    material=duct.material,
                    pressure_level=duct.pressure_level,
                )
            )
            parent.insert_between(child, reducer)
