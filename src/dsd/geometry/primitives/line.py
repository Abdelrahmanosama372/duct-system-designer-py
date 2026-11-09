"""Line primitive types and 2D segment intersection helpers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import acos, atan2, cos, degrees, isclose, sin, sqrt
from typing import Any, Optional, Tuple, override

import numpy as np

from .base import Primitive2D, PrimitiveStyle
from .point import Point

EPS = 1


def cross_2d(ax: float, ay: float, bx: float, by: float) -> float:
    """Return the result of the 2D cross product."""
    return ax * by - ay * bx


def dot_2d(ax: float, ay: float, bx: float, by: float) -> float:
    """Return the result of the 2D dot product."""
    return ax * bx + ay * by


class LineType(StrEnum):
    """Supported semantic types for a line segment."""

    Normal = "Normal"
    CenterLine = "CenterLine"
    Hidden = "Hidden"


@dataclass(init=False)
class Line(Primitive2D):
    """Finite 2D line segment with optional semantic type metadata."""

    start: Point
    end: Point
    line_type: LineType = LineType.Normal

    def __init__(
        self,
        start: Point,
        end: Point,
        line_type: LineType = LineType.Normal,
        id: int = -1,
        style: PrimitiveStyle | None = None,
    ) -> None:
        self.start = start
        self.end = end
        self.line_type = line_type
        super().__init__(id=id, style=style)

    def __eq__(self, other):
        if not isinstance(other, Line):
            return NotImplemented
        return (
            self.start == other.start
            and self.end == other.end
            and self.line_type == other.line_type
        )

    def length(self):
        return self.start.distance(self.end)

    def swap_end_points(self) -> None:
        """Swap the segment start and end points in place."""
        self.start, self.end = self.end, self.start

    def split_at_unchecked(
        self, points: list[Point], min_length: float = EPS
    ) -> list[Line]:
        """Split this line at ordered points that are assumed to lie on the segment."""
        split_points = [self.start]

        for point in points:
            if point == split_points[-1]:
                continue
            split_points.append(point)

        if split_points[-1] != self.end:
            split_points.append(self.end)

        split_lines: list[Line] = []
        for index, (start, end) in enumerate(
            zip(split_points, split_points[1:]), start=1
        ):
            line = Line(
                id=index,
                start=start,
                end=end,
                line_type=self.line_type,
                style=self.style,
            )

            if line.length() <= min_length:
                continue

            split_lines.append(line)

        return split_lines

    def angle_to(self, line: Line) -> float:
        """Return the angle in degrees between this line and another."""
        first_vector = (
            self.end.x - self.start.x,
            self.end.y - self.start.y,
        )
        second_vector = (
            line.end.x - line.start.x,
            line.end.y - line.start.y,
        )

        dot_product = dot_2d(
            first_vector[0],
            first_vector[1],
            second_vector[0],
            second_vector[1],
        )
        first_norm = sqrt(first_vector[0] ** 2 + first_vector[1] ** 2)
        second_norm = sqrt(second_vector[0] ** 2 + second_vector[1] ** 2)
        cosine = max(-1.0, min(1.0, dot_product / (first_norm * second_norm)))
        return degrees(acos(cosine))

    def is_collinear_to(self, line: Line, tol_deg: float = 1.0) -> bool:
        """Return whether this line is collinear to another line within tolerance."""
        angle = abs(self.angle_to(line))
        return angle <= tol_deg or abs(angle - 180.0) <= tol_deg

    def pass_through_point(self, point: Point, tol: float = EPS) -> bool:
        """Return whether a point lies on this segment within tolerance."""
        P = point.array()
        A = self.start.array()
        B = self.end.array()

        AB = B - A
        AP = P - A

        cross = np.cross(AB, AP)
        distance = np.linalg.norm(cross) / np.linalg.norm(AB)
        if distance > tol:
            return False

        dot = np.dot(AP, AB)
        dot_offset = tol * np.linalg.norm(AB)
        if dot < -dot_offset:
            return False
        if dot > np.dot(AB, AB) + dot_offset:
            return False

        return True

    def intersects_line_2D(self, line: Line) -> Tuple[bool, Optional[Point]]:
        """Compute segment-segment intersection and return hit flag and point."""
        A = self.start
        B = self.end
        C = line.start
        D = line.end

        # r = B - A
        rx = B.x - A.x
        ry = B.y - A.y

        # s = D - C
        sx = D.x - C.x
        sy = D.y - C.y

        # w = C - A
        wx = C.x - A.x
        wy = C.y - A.y

        denom = cross_2d(rx, ry, sx, sy)

        # -------------------------------------------------
        # Case 1: Not parallel
        # -------------------------------------------------
        if abs(denom) > EPS:

            t = cross_2d(wx, wy, sx, sy) / denom
            u = cross_2d(wx, wy, rx, ry) / denom

            eps = 1e-5
            if -eps <= t <= 1.0 + eps and -eps <= u <= 1.0 + eps:
                intersection_x = A.x + t * rx
                intersection_y = A.y + t * ry
                return True, Point(x=intersection_x, y=intersection_y)

            return False, None

        # -------------------------------------------------
        # Case 2: Parallel
        # -------------------------------------------------
        # Check collinearity
        if abs(cross_2d(wx, wy, rx, ry)) > EPS:
            return False, None  # Parallel but not collinear

        # -------------------------------------------------
        # Case 3: Collinear - check overlap
        # -------------------------------------------------
        def within(a: float, b: float, c: float) -> bool:
            """Return whether c lies within inclusive range [a, b] with epsilon."""
            return min(a, b) - EPS <= c <= max(a, b) + EPS

        if within(A.x, B.x, C.x) and within(A.y, B.y, C.y):
            return True, C

        if within(A.x, B.x, D.x) and within(A.y, B.y, D.y):
            return True, D

        if within(C.x, D.x, A.x) and within(C.y, D.y, A.y):
            return True, A

        if within(C.x, D.x, B.x) and within(C.y, D.y, B.y):
            return True, B

        return False, None

    def direction(self) -> float:
        dx = self.end.x - self.start.x
        dy = self.end.y - self.start.y
        return atan2(dy, dx)

    def point_from(self, point: Point, offset: float):
        theta = self.direction()
        return Point(point.x + offset * cos(theta), point.y + offset * sin(theta))

    def point_from_start(self, offset: float):
        return self.point_from(self.start, offset)

    def point_from_end(self, offset: float):
        # move backwards from end
        return self.point_from(self.end, -offset)

    def middle_point(self) -> Point:
        return Point(
            x=(self.start.x + self.end.x) / 2.0,
            y=(self.start.y + self.end.y) / 2.0,
            z=(self.start.z + self.end.z) / 2.0,
        )

    @override
    def transform_2d(self, transform: "Transform2D") -> Primitive2D:
        start_trans = self.start.transform_2d(transform)
        end_trans = self.end.transform_2d(transform)
        return Line(start=start_trans, end=end_trans, line_type=self.line_type)

    def subtract_lines(self, lines: list["Line"]) -> list["Line"]:

        points = [self.start, self.end]

        for line in lines:

            if not self.is_collinear_to(line):
                continue

            if self.pass_through_point(line.start):
                points.append(line.start)

            if self.pass_through_point(line.end):
                points.append(line.end)

        # sort points along self
        points = sorted(
            set(points),
            key=lambda p: (self.start.distance(p)),
        )

        result: list[Line] = []

        for p1, p2 in zip(points, points[1:]):

            mid = Point(
                (p1.x + p2.x) / 2,
                (p1.y + p2.y) / 2,
            )

            # if midpoint belongs to any cut line -> skip
            if any(line.pass_through_point(mid) for line in lines):
                continue

            line = Line(
                start=p1,
                end=p2,
                line_type=self.line_type,
                style=self.style,
            )

            if line.length() < EPS:
                continue

            result.append(line)

        return result

    @override
    def to_json(self) -> dict[str, Any]:
        """Serialize this line to the project JSON format."""
        data = {
            "Line": {
                "start": self.start.to_json(),
                "end": self.end.to_json(),
                "line type": self.line_type.value,
            }
        }
        if self.style is not None:
            data["Line"]["style"] = {
                "layer": self.style.layer,
                "color": self.style.color,
                "category": self.style.category,
            }
        return data

    def __hash__(self) -> int:
        """Allow points to be used as dictionary keys by coordinate identity."""
        return hash(self.start) + hash(self.end)

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Line:
        """Build a line instance from the project JSON format."""
        line_props = data["Line"]
        start = Point.from_json(line_props["start"])
        end = Point.from_json(line_props["end"])
        line_type = LineType(line_props["line type"])
        style_data = line_props.get("style")
        style = (
            PrimitiveStyle(
                layer=style_data.get("layer"),
                color=style_data.get("color"),
                category=style_data.get("category"),
            )
            if isinstance(style_data, dict)
            else None
        )
        return Line(start=start, end=end, line_type=line_type, style=style)
