from __future__ import annotations

from dataclasses import dataclass
from typing import override

from .base import Primitive2D, PrimitiveStyle
from .line import LineType
from .point import Point


@dataclass(init=False)
class Circle(Primitive2D):

    center: Point
    radius: float

    def __init__(
        self,
        center: Point,
        radius: float,
        line_type: LineType = LineType.Normal,
        id: int = -1,
        style: PrimitiveStyle | None = None,
    ) -> None:
        self.center = center
        self.radius = radius
        self.line_type = line_type
        self.id = id
        self.style = style
        super().__init__(id=id, style=style)

    @override
    def transform_2d(self, transform: "Transform2D") -> Primitive2D:
        return Circle(
            center=self.center.transform_2d(transform),
            radius=self.radius,
            line_type=self.line_type,
            id=self.id,
            style=self.style,
        )

    @override
    def to_json(self) -> dict[str, str]:
        data = {
            "Circle": {
                "center": self.center.to_json(),
                "radius": str(self.radius),
                "id": str(self.id),
            }
        }
        if self.style is not None:
            data["style"] = {
                "layer": self.style.layer,
                "color": self.style.color,
                "category": self.style.category,
            }
        return data

    @override
    @classmethod
    def from_json(cls, data: dict[str, str]) -> "Circle":
        """Build a circle instance from the project JSON format."""

        circle_data = data["Circle"]

        center = Point.from_json(circle_data["center"])

        style_data = data.get("style")
        style = (
            PrimitiveStyle(
                layer=style_data.get("layer"),
                color=style_data.get("color"),
                category=style_data.get("category"),
            )
            if isinstance(style_data, dict)
            else None
        )

        return cls(
            center=center,
            radius=float(circle_data["radius"]),
            id=int(circle_data["id"]),
            style=style,
        )
