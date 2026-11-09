from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..sheet_metal_component import VisitorResult

if TYPE_CHECKING:
    from ...visitors.sheet_metal_component_visitor import SheetMetalComponentVisitor

from ..sheet_metal_component import validate_dimension
from .rectangular_sheet_metal_component import RectangularSheetMetalComponent


@dataclass(kw_only=True)
class RectangularDuct(RectangularSheetMetalComponent):
    length: float | None = None
    ref_line_id: int | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        if (self.width is None) != (self.height is None):
            raise ValueError("Duct width and height must be supplied together")
        validate_dimension(self.length, "length")

    def accept(
        self, visitor: SheetMetalComponentVisitor[VisitorResult]
    ) -> VisitorResult:
        return visitor.visit_rectangular_duct(self)
