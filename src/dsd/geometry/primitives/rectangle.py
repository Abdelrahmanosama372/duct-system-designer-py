from __future__ import annotations

from dataclasses import dataclass
from math import atan2
from typing import Any, override

from .base import Primitive2D, PrimitiveStyle
from .line import Line, LineType
from .point import Point


@dataclass(init=False)
class Rectangle(Primitive2D):
    point1: Point
    point2: Point
    point3: Point
    point4: Point
    line_type: LineType = LineType.Normal

    def __init__(
        self,
        point1: Point,
        point2: Point,
        point3: Point,
        point4: Point,
        line_type: LineType = LineType.Normal,
        id: int = -1,
        style: PrimitiveStyle | None = None,
    ) -> None:
        self.point1 = point1
        self.point2 = point2
        self.point3 = point3
        self.point4 = point4
        self.line_type = line_type
        super().__init__(id=id, style=style)

    @classmethod
    def from_bounds(
        cls,
        point1: Point,
        point2: Point,
        line_type: LineType = LineType.Normal,
        id: int = -1,
        style: PrimitiveStyle | None = None,
    ) -> "Rectangle":
        x_min = min(point1.x, point2.x)
        x_max = max(point1.x, point2.x)
        y_min = min(point1.y, point2.y)
        y_max = max(point1.y, point2.y)
        return cls(
            point1=Point(x=x_min, y=y_min),
            point2=Point(x=x_max, y=y_min),
            point3=Point(x=x_max, y=y_max),
            point4=Point(x=x_min, y=y_max),
            line_type=line_type,
            id=id,
            style=style,
        )

    @override
    def transform_2d(self, transform: "Transform2D") -> Primitive2D:
        return Rectangle(
            point1=self.point1.transform_2d(transform),
            point2=self.point2.transform_2d(transform),
            point3=self.point3.transform_2d(transform),
            point4=self.point4.transform_2d(transform),
            line_type=self.line_type,
            id=self.id,
            style=self.style,
        )

    def edges(self) -> list[Line]:
        points = [self.point1, self.point2, self.point3, self.point4]
        return [
            Line(start=start, end=end, line_type=self.line_type, style=self.style)
            for start, end in zip(points, points[1:] + points[:1])
        ]

    def bounds(self) -> tuple[float, float, float, float]:
        points = [self.point1, self.point2, self.point3, self.point4]
        xs = [p.x for p in points]
        ys = [p.y for p in points]
        return min(xs), max(xs), min(ys), max(ys)

    def intersection(self, other: "Rectangle") -> "Rectangle | None":
        epsilon = 1e-6

        def cross(a: Point, b: Point, c: Point) -> float:
            return (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)

        def point_on_left_of_edge(
            point: Point, edge_start: Point, edge_end: Point
        ) -> bool:
            return cross(edge_start, edge_end, point) >= -epsilon

        def line_intersection(
            p1: Point, p2: Point, q1: Point, q2: Point
        ) -> Point | None:
            r_x = p2.x - p1.x
            r_y = p2.y - p1.y
            s_x = q2.x - q1.x
            s_y = q2.y - q1.y
            denominator = r_x * s_y - r_y * s_x
            if abs(denominator) <= epsilon:
                return None
            t = ((q1.x - p1.x) * s_y - (q1.y - p1.y) * s_x) / denominator
            return Point(x=p1.x + t * r_x, y=p1.y + t * r_y)

        def deduplicate(points: list[Point]) -> list[Point]:
            unique: list[Point] = []
            for point in points:
                if any(existing.distance(point) <= epsilon for existing in unique):
                    continue
                unique.append(point)
            return unique

        def sort_ccw(points: list[Point]) -> list[Point]:
            center_x = sum(point.x for point in points) / len(points)
            center_y = sum(point.y for point in points) / len(points)
            return sorted(
                points,
                key=lambda point: atan2(point.y - center_y, point.x - center_x),
            )

        # Sutherland-Hodgman clipping: clip self by other's edges.
        subject = [self.point1, self.point2, self.point3, self.point4]
        clipper = [other.point1, other.point2, other.point3, other.point4]

        output = subject
        for edge_start, edge_end in zip(clipper, clipper[1:] + clipper[:1]):
            if not output:
                return None
            input_points = output
            output = []
            previous = input_points[-1]
            for current in input_points:
                current_inside = point_on_left_of_edge(current, edge_start, edge_end)
                previous_inside = point_on_left_of_edge(previous, edge_start, edge_end)
                if current_inside:
                    if not previous_inside:
                        intersection_point = line_intersection(
                            previous, current, edge_start, edge_end
                        )
                        if intersection_point is not None:
                            output.append(intersection_point)
                    output.append(current)
                elif previous_inside:
                    intersection_point = line_intersection(
                        previous, current, edge_start, edge_end
                    )
                    if intersection_point is not None:
                        output.append(intersection_point)
                previous = current

        output = deduplicate(output)
        if len(output) < 3:
            return None

        output = sort_ccw(output)
        if len(output) == 4:
            return Rectangle(
                point1=output[0],
                point2=output[1],
                point3=output[2],
                point4=output[3],
                line_type=self.line_type,
            )

        # Fallback for degenerate/non-rectangular overlap.
        x_values = [point.x for point in output]
        y_values = [point.y for point in output]
        return Rectangle.from_bounds(
            point1=Point(x=min(x_values), y=min(y_values)),
            point2=Point(x=max(x_values), y=max(y_values)),
            line_type=self.line_type,
        )

    @override
    def to_json(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "Rectangle": {
                "point1": self.point1.to_json(),
                "point2": self.point2.to_json(),
                "point3": self.point3.to_json(),
                "point4": self.point4.to_json(),
                "line type": self.line_type.value,
            }
        }
        if self.style is not None:
            data["Rectangle"]["style"] = {
                "layer": self.style.layer,
                "color": self.style.color,
                "category": self.style.category,
            }
        return data

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "Rectangle":
        props = data["Rectangle"]
        point1 = Point.from_json(props["point1"])
        point2 = Point.from_json(props["point2"])
        line_type = LineType(props["line type"])
        style_data = props.get("style")
        style = (
            PrimitiveStyle(
                layer=style_data.get("layer"),
                color=style_data.get("color"),
                category=style_data.get("category"),
            )
            if isinstance(style_data, dict)
            else None
        )
        if "point3" not in props or "point4" not in props:
            return Rectangle.from_bounds(
                point1=point1,
                point2=point2,
                line_type=line_type,
                style=style,
            )
        point3 = Point.from_json(props["point3"])
        point4 = Point.from_json(props["point4"])
        return Rectangle(
            point1=point1,
            point2=point2,
            point3=point3,
            point4=point4,
            line_type=line_type,
            style=style,
        )
