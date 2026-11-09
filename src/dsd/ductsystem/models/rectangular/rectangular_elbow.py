from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..sheet_metal_component import VisitorResult

if TYPE_CHECKING:
    from ...visitors.sheet_metal_component_visitor import SheetMetalComponentVisitor
from math import isfinite, pi

from ..sheet_metal_component import validate_dimension
from .rectangular_duct_fitting import RectangularDuctFitting


@dataclass(kw_only=True)
class RectangularElbow(RectangularDuctFitting):
    angle: float

    def __post_init__(self) -> None:
        super().__post_init__()
        if not isfinite(self.angle) or not 0 < abs(self.angle) <= pi:
            raise ValueError("Elbow angle must be nonzero radians between -pi and pi")

    def inside_radius(self, ratio: float) -> float | None:
        validate_dimension(ratio, "inside-radius ratio")
        return None if self.width is None else ratio * self.width

    def centerline_radius(self, ratio: float) -> float | None:
        inside = self.inside_radius(ratio)
        return None if inside is None else inside + self.width / 2

    def accept(
        self, visitor: SheetMetalComponentVisitor[VisitorResult]
    ) -> VisitorResult:
        return visitor.visit_rectangular_elbow(self)
