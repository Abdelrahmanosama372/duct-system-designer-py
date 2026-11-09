"""Point primitive definition and coordinate utility methods."""

from __future__ import annotations

from dataclasses import dataclass
from math import isclose, sqrt
from typing import override

import numpy as np

from .base import Primitive2D, PrimitiveStyle

TOLERANCE_MM = 2


@dataclass(init=False)
class Point(Primitive2D):
    """Cartesian point used by 2D/3D geometry primitives."""

    x: float
    y: float
    z: float = 0.0

    def __init__(
        self,
        x: float,
        y: float,
        z: float = 0.0,
        id: int = -1,
        style: PrimitiveStyle | None = None,
    ) -> None:
        self.x = x
        self.y = y
        self.z = z
        super().__init__(id=id, style=style)

    def distance(self, other: Point):
        """Return Euclidean distance to another point."""
        return sqrt(
            (self.x - other.x) ** 2 + (self.y - other.y) ** 2 + (self.z - other.z) ** 2
        )

    def __add__(self, other: Point) -> Point:
        """Return coordinate-wise addition of two points."""
        return Point(
            x=self.x + other.x,
            y=self.y + other.y,
            z=self.z + other.z,
        )

    def __sub__(self, other: Point) -> Point:
        """Return coordinate-wise subtraction of two points."""
        return Point(
            x=self.x - other.x,
            y=self.y - other.y,
            z=self.z - other.z,
        )

    def _key(self):
        return (
            round(self.x / TOLERANCE_MM),
            round(self.y / TOLERANCE_MM),
            round(self.z / TOLERANCE_MM),
        )

    def __eq__(self, other: Point):
        return self._key() == other._key()

    def __hash__(self):
        """Allow points to be used as dictionary keys by coordinate identity."""
        return hash(self._key())

    def array(self) -> np.ndarray:
        """Return point coordinates as a NumPy array `[x, y, z]`."""
        return np.array([self.x, self.y, self.z])

    def to_list3d(self) -> list[float]:
        return [self.x, self.y, self.z]

    @override
    def transform_2d(self, transform: "Transform2D") -> Primitive2D:
        point_vec = self.array()
        point_vec[-1] = 1
        trans = np.dot(transform.transform, point_vec.reshape((3, 1)))
        return Point(x=float(trans[0, 0]), y=float(trans[1, 0]))

    @override
    def to_json(self) -> dict[str, str]:
        """Serialize this point to the project JSON format."""
        data: dict[str, str | dict[str, str | None]] = {
            "Point": f"{self.x}, {self.y}, {self.z}"
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
    def from_json(cls, data: dict[str, str]) -> Point:
        """Build a point instance from the project JSON format."""
        point_data = [float(i) for i in data["Point"].split(",")]
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
        return Point(
            x=point_data[0],
            y=point_data[1],
            z=point_data[2],
            style=style,
        )
