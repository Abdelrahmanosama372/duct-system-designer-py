"""Assign fitting dimensions after duct sizing and reducer insertion."""

from ..duct_fitting_tree import DuctFittingTree
from ..fitting_sizing_config import FittingSizingConfig
from ..models.rectangular import (
    RectangularDuct,
    RectangularElbow,
    RectangularEndcap,
    RectangularReducer,
    RectangularShoeTakeoff,
)
from .tree_helpers import (
    DuctSizingError,
    dimensions,
    downstream_main_duct,
    shoe_branch,
    upstream_duct,
)


class FittingSizingPass:
    def __init__(self, config: FittingSizingConfig) -> None:
        self.config = config

    def apply(self, tree: DuctFittingTree) -> None:
        for node in tree.preorder_traversal():
            fitting = node.component
            if isinstance(fitting, RectangularDuct):
                dimensions(fitting)
                continue
            upstream = upstream_duct(node)
            if upstream is None:
                raise DuctSizingError(f"Fitting {fitting.id} has no upstream duct")
            if isinstance(fitting, RectangularElbow):
                if len(node.children) != 1:
                    raise DuctSizingError("Elbow requires one downstream duct")
                downstream = downstream_main_duct(node.children[0])
                if dimensions(upstream) != dimensions(downstream):
                    raise DuctSizingError("Reducing elbows are not supported")
                fitting.width, fitting.height = dimensions(upstream)
            elif isinstance(fitting, RectangularShoeTakeoff):
                branch = shoe_branch(node)
                fitting.width, fitting.height = dimensions(branch)
                fitting.takeoff_length = self.config.takeoff_length
            elif isinstance(fitting, RectangularReducer):
                if len(node.children) != 1 or not isinstance(
                    node.children[0].component, RectangularDuct
                ):
                    raise DuctSizingError("Reducer requires one downstream duct")
                downstream = node.children[0].component
                fitting.width, fitting.height = dimensions(upstream)
                fitting.inlet_width, fitting.inlet_height = dimensions(upstream)
                fitting.outlet_width, fitting.outlet_height = dimensions(downstream)
                fitting.length = self.config.reducer_length
            elif isinstance(fitting, RectangularEndcap):
                if node.children:
                    raise DuctSizingError("Endcap must be a leaf component")
                fitting.width, fitting.height = dimensions(upstream)
            else:
                raise DuctSizingError(f"Unsupported fitting: {type(fitting).__name__}")
