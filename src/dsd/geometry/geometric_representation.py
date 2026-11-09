"""A component outline and its finite layout centerlines, in mm."""

from dataclasses import dataclass, field
from typing import cast

from .primitives import Line, Primitive2D, Transform2D


@dataclass
class GeometricRepresentation:
    component_id: int
    primitives: list[Primitive2D] = field(default_factory=list)
    layout_skeleton: list[Line] = field(default_factory=list)

    def transformed(self, transform: Transform2D) -> "GeometricRepresentation":
        return GeometricRepresentation(
            self.component_id,
            [primitive.transform_2d(transform) for primitive in self.primitives],
            [cast(Line, line.transform_2d(transform)) for line in self.layout_skeleton],
        )
