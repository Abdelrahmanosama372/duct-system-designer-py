"""Common sheet-metal properties; dimensions and calculations are staged later."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from ..visitors.sheet_metal_component_visitor import SheetMetalComponentVisitor

VisitorResult = TypeVar("VisitorResult")


class PressureLevels(StrEnum):
    LowPressure = "lowpressure"
    MediumPressure = "mediumpressure"
    HighPressure = "highpressure"


class Material(StrEnum):
    GalvanizedSteel = "GalvanizedSteel"
    Aluminum = "Aluminum"


@dataclass(kw_only=True)
class SheetMetalComponent:
    id: int
    flow: float
    pressure_level: PressureLevels
    material: Material

    def accept(
        self, visitor: SheetMetalComponentVisitor[VisitorResult]
    ) -> VisitorResult:
        raise TypeError(f"Unsupported sheet-metal component: {type(self).__name__}")

    def __post_init__(self) -> None:
        if not isinstance(self.id, int) or isinstance(self.id, bool) or self.id < 0:
            raise ValueError("Component id must be a nonnegative integer")
        if not isfinite(self.flow) or self.flow < 0:
            raise ValueError("Component flow must be finite and nonnegative")
        if not isinstance(self.pressure_level, PressureLevels):
            raise ValueError("pressure_level must be a PressureLevels value")
        if not isinstance(self.material, Material):
            raise ValueError("material must be a Material value")


def validate_dimension(value: float | None, name: str) -> None:
    if value is not None and (not isfinite(value) or value <= 0):
        raise ValueError(f"{name} must be positive and finite when supplied")
