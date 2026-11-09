"""Parent-first duct sizing; fittings and source duct lengths are left unchanged."""

from ..duct_fitting_tree import DuctFittingTree
from ..models.rectangular import RectangularDuct
from ..models.sheet_metal_component import validate_dimension
from .duct_sizer import DuctSizer
from .models import SizingContext
from .tree_helpers import DuctSizingError, dimensions, upstream_duct


class DuctSizingPass:
    def __init__(self, sizer: DuctSizer) -> None:
        self.sizer = sizer

    def apply(self, tree: DuctFittingTree) -> None:
        nodes = list(tree.preorder_traversal())
        ducts = {
            node.component.id: node.component
            for node in nodes
            if isinstance(node.component, RectangularDuct)
        }
        for duct in ducts.values():
            if (duct.width is None) != (duct.height is None):
                raise DuctSizingError(
                    f"Duct {duct.id}: width and height must be supplied together"
                )
            validate_dimension(duct.width, "width")
            validate_dimension(duct.height, "height")
        for node in nodes:
            duct = node.component
            if not isinstance(duct, RectangularDuct):
                continue
            parent = upstream_duct(node)
            if duct.width is None:
                if duct.flow <= 0:
                    raise DuctSizingError(
                        f"Unsized duct {duct.id} requires positive airflow"
                    )
                preferred_width = None if parent is None else dimensions(parent)[0]
                result = self.sizer.size_duct(SizingContext(duct.flow, preferred_width))
                duct.width, duct.height = result.width, result.height
