"""A tree node containing exactly one sheet-metal component."""

from dataclasses import dataclass, field

from .models.rectangular.rectangular_duct_fitting import RectangularDuctFitting
from .models.sheet_metal_component import SheetMetalComponent


@dataclass(eq=False)
class SheetMetalNode:
    component: SheetMetalComponent
    parent: "SheetMetalNode | None" = field(default=None, init=False, repr=False)
    children: list["SheetMetalNode"] = field(default_factory=list, init=False)

    def add_child(self, child: "SheetMetalNode") -> None:
        if child.parent is not None:
            raise ValueError("Child is already attached to a parent")
        ancestor: SheetMetalNode | None = self
        while ancestor is not None:
            if ancestor is child:
                raise ValueError("Attaching this child would create a cycle")
            ancestor = ancestor.parent
        self.children.append(child)
        child.parent = self

    def is_duct_fitting(self) -> bool:
        return isinstance(self.component, RectangularDuctFitting)

    def insert_between(
        self, child: "SheetMetalNode", intermediate: "SheetMetalNode"
    ) -> None:
        """Replace one child edge while preserving its position and both parent links."""
        if child.parent is not self or child not in self.children:
            raise ValueError("Child is not attached to this parent")
        if intermediate.parent is not None or intermediate.children:
            raise ValueError(
                "Intermediate node must be unattached and have no children"
            )
        if intermediate is self or intermediate is child:
            raise ValueError("Intermediate node would create a cycle")
        self.children[self.children.index(child)] = intermediate
        intermediate.parent = self
        intermediate.children.append(child)
        child.parent = intermediate
