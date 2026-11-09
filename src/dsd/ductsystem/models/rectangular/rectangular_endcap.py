from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..sheet_metal_component import VisitorResult

if TYPE_CHECKING:
    from ...visitors.sheet_metal_component_visitor import SheetMetalComponentVisitor

from .rectangular_duct_fitting import RectangularDuctFitting


@dataclass(kw_only=True)
class RectangularEndcap(RectangularDuctFitting):
    """Closes the main duct at a terminal branch junction."""

    def accept(
        self, visitor: SheetMetalComponentVisitor[VisitorResult]
    ) -> VisitorResult:
        return visitor.visit_rectangular_endcap(self)
