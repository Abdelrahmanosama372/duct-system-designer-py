"""Rigid placement of normalized geometry in a two-dimensional drawing."""

from dataclasses import dataclass
from enum import StrEnum

from ..primitives import Transform2D


class ViewType(StrEnum):
    Plan = "plan"


@dataclass(frozen=True)
class PlacementContext:
    transform: Transform2D
    view_type: ViewType = ViewType.Plan
    elevation: float = 0.0
    length: float | None = None  # Final duct length after fitting connections.
