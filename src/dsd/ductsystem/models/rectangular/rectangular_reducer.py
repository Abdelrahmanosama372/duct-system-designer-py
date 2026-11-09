from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..sheet_metal_component import VisitorResult

if TYPE_CHECKING:
    from ...visitors.sheet_metal_component_visitor import SheetMetalComponentVisitor

from ..sheet_metal_component import validate_dimension
from .rectangular_duct_fitting import RectangularDuctFitting


@dataclass(kw_only=True)
class RectangularReducer(RectangularDuctFitting):
    inlet_width: float | None = None
    inlet_height: float | None = None
    outlet_width: float | None = None
    outlet_height: float | None = None
    length: float | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        for name in (
            "inlet_width",
            "inlet_height",
            "outlet_width",
            "outlet_height",
            "length",
        ):
            validate_dimension(getattr(self, name), name)

    def accept(
        self, visitor: SheetMetalComponentVisitor[VisitorResult]
    ) -> VisitorResult:
        return visitor.visit_rectangular_reducer(self)
