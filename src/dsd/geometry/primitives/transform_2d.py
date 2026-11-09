"""2D rigid transform utilities for translation and rotation composition."""

from __future__ import annotations

from fnmatch import translate
from math import atan2, isclose

import numpy as np
from numpy.typing import NDArray

from .point import Point


class Transform2D:
    """Rigid 2D transform represented by translation and rotation."""

    def __init__(self, origin: Point, rotation: float):
        """Initialize from origin point and rotation angle in radians."""
        self._origin: Point = origin
        self._rotation: float = rotation

    @property
    def origin(self) -> Point:
        """Return the translation component of this transform."""
        return self._origin

    @property
    def angle(self) -> float:
        """Return the rotation angle in radians."""
        return self._rotation

    @angle.setter
    def angle(self, value: float):
        self._rotation = value

    @property
    def transform(self) -> NDArray[np.float64]:
        """Return a 3x3 homogeneous transformation matrix."""
        transform: NDArray[np.float64] = np.array(
            [
                [np.cos(self._rotation), -np.sin(self._rotation), self._origin.x],
                [np.sin(self._rotation), np.cos(self._rotation), self._origin.y],
                [0, 0, 1],
            ]
        )
        return transform

    def translated_local(self, dx: float, dy: float) -> Transform2D:
        """Return a new transform translated in the local frame by `(dx, dy)`."""
        translation = np.array([[dx, dy, 1]]).T
        new_transform: NDArray[np.float64] = np.dot(self.transform, translation)
        new_origin = Point(x=new_transform[0, 0], y=new_transform[1, 0], z=0)
        return Transform2D(origin=new_origin, rotation=self._rotation)

    def translate_local(self, dx: float, dy: float):
        """Mutate this transform by applying local-frame translation."""
        new_transform = self.translated_local(dx, dy)
        self._origin = new_transform.origin

    def rotated_local(self, angle: float) -> Transform2D:
        """Return a new transform with additional local rotation."""
        return Transform2D(origin=self.origin, rotation=self._rotation + angle)

    def rotate_local(self, angle: float):
        """Mutate this transform by increasing local rotation."""
        self._rotation += angle

    def __matmul__(self, other: Transform2D) -> Transform2D:
        """Compose this transform with another transform using matrix product."""
        composed = self.transform @ other.transform
        return Transform2D.from_array(composed)

    def __eq__(self, other: Transform2D) -> bool:
        return self._origin.__eq__(other.origin) and isclose(self.angle, other.angle)

    @staticmethod
    def from_array(transform: NDArray[np.float64]) -> Transform2D:
        """Construct a transform from a 3x3 homogeneous matrix."""
        c = transform[0, 0]
        s = transform[1, 0]
        rotation = atan2(s, c)
        origin = Point(x=transform[0, 2], y=transform[1, 2], z=0)
        return Transform2D(origin, rotation)
