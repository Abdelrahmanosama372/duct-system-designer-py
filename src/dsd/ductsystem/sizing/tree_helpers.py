"""Shared navigation and validation for component-tree sizing passes."""

from ..models.rectangular import RectangularDuct, RectangularShoeTakeoff
from ..sheet_metal_node import SheetMetalNode


class DuctSizingError(ValueError):
    """A component tree cannot be sized under the supported fitting rules."""


def upstream_duct(node: SheetMetalNode) -> RectangularDuct | None:
    parent = node.parent
    while parent is not None:
        if isinstance(parent.component, RectangularDuct):
            return parent.component
        parent = parent.parent
    return None


def dimensions(duct: RectangularDuct) -> tuple[float, float]:
    if duct.width is None or duct.height is None:
        raise DuctSizingError(f"Duct {duct.id} has not been sized")
    return duct.width, duct.height


def shoe_branch(node: SheetMetalNode) -> RectangularDuct:
    if (
        not isinstance(node.component, RectangularShoeTakeoff)
        or len(node.children) != 1
    ):
        raise DuctSizingError("Shoe takeoff must have exactly one branch duct child")
    branch = node.children[0].component
    if (
        not isinstance(branch, RectangularDuct)
        or branch.id != node.component.branch_duct_id
    ):
        raise DuctSizingError("Shoe takeoff requires its referenced branch duct child")
    return branch


def downstream_main_duct(node: SheetMetalNode) -> RectangularDuct:
    while not isinstance(node.component, RectangularDuct):
        if isinstance(node.component, RectangularShoeTakeoff):
            raise DuctSizingError(
                "A main continuation cannot run through a shoe takeoff"
            )
        if len(node.children) != 1:
            raise DuctSizingError("Fitting requires exactly one main continuation")
        node = node.children[0]
    return node.component
