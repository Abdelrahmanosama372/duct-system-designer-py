"""Standalone sizer input and output; no duct-system objects are required."""

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class SizingContext:
    flow: float  # CFM
    preferred_width: float | None = None  # mm; supplied by the caller

    def __post_init__(self) -> None:
        if isinstance(self.flow, bool) or not isfinite(self.flow) or self.flow <= 0:
            raise ValueError("flow must be positive and finite (CFM)")
        if self.preferred_width is not None and (
            isinstance(self.preferred_width, bool)
            or not isfinite(self.preferred_width)
            or self.preferred_width <= 0
        ):
            raise ValueError("preferred_width must be positive and finite (mm)")


@dataclass(frozen=True)
class DuctDimension:
    width: int  # mm
    height: int  # mm
