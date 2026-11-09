from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..sheet_metal_component import VisitorResult

if TYPE_CHECKING:
    from ...visitors.sheet_metal_component_visitor import SheetMetalComponentVisitor
from typing import Literal

from ..sheet_metal_component import validate_dimension
from .rectangular_duct_fitting import RectangularDuctFitting


@dataclass(kw_only=True)
class RectangularShoeTakeoff(RectangularDuctFitting):
    side: Literal["left", "right"]
    branch_duct_id: int | None = None
    takeoff_length: float | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.side not in ("left", "right"):
            raise ValueError("Takeoff side must be left or right")
        validate_dimension(self.takeoff_length, "takeoff_length")

    @property
    def width1(self) -> float | None:
        """Bevel opening at the main duct; the child-side width is self.width."""
        if self.width is None or self.takeoff_length is None:
            return None
        return self.width + self.takeoff_length

    def accept(
        self, visitor: SheetMetalComponentVisitor[VisitorResult]
    ) -> VisitorResult:
        return visitor.visit_rectangular_shoetakeoff(self)
