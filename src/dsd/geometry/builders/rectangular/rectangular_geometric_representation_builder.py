"""Retain sized local outlines and transform copies into drawing coordinates."""

from math import cos, isfinite, pi, sin, tan
from typing import Callable, TypeVar

from dsd.ductsystem.fitting_sizing_config import FittingSizingConfig
from dsd.ductsystem.models.rectangular import (
    RectangularDuct,
    RectangularElbow,
    RectangularEndcap,
    RectangularReducer,
    RectangularShoeTakeoff,
)
from dsd.ductsystem.models.sheet_metal_component import SheetMetalComponent

from ...geometric_representation import GeometricRepresentation
from ...placement.placement_context import PlacementContext
from ...primitives import Arc, Line, LineType, Point

ComponentT = TypeVar("ComponentT", bound=SheetMetalComponent)


class GeometryConstructionError(ValueError):
    """A normalized rectangular representation cannot be constructed."""


class RectangularGeometricRepresentationBuilder:
    def __init__(self, config: FittingSizingConfig) -> None:
        self.config = config
        self.normalized_representations: dict[int, GeometricRepresentation] = {}
        self._keys: dict[int, tuple[object, ...]] = {}

    @staticmethod
    def _dimension(component: SheetMetalComponent, name: str) -> float:
        value = getattr(component, name, None)
        if value is None or not isfinite(value) or value <= 0:
            raise GeometryConstructionError(
                f"Component {component.id} requires positive finite {name}"
            )
        return value

    @staticmethod
    def _polygon(points: list[Point]) -> list[Line]:
        return [Line(start, end) for start, end in zip(points, points[1:] + points[:1])]

    @staticmethod
    def _skeleton(start: Point, end: Point) -> Line:
        return Line(start, end, line_type=LineType.CenterLine)

    def _build(
        self,
        component: ComponentT,
        context: PlacementContext,
        factory: Callable[[ComponentT], GeometricRepresentation],
    ) -> GeometricRepresentation:
        key = (type(component), tuple(vars(component).items()), self.config)
        if self._keys.get(component.id) != key:
            self.normalized_representations[component.id] = factory(component)
            self._keys[component.id] = key
        return self.normalized_representations[component.id].transformed(
            context.transform
        )

    def build_duct(
        self, component: RectangularDuct, context: PlacementContext
    ) -> GeometricRepresentation:
        return self._build(component, context, self._duct)

    def build_elbow(
        self, component: RectangularElbow, context: PlacementContext
    ) -> GeometricRepresentation:
        return self._build(component, context, self._elbow)

    def build_shoetakeoff(
        self, component: RectangularShoeTakeoff, context: PlacementContext
    ) -> GeometricRepresentation:
        return self._build(component, context, self._shoe)

    def build_reducer(
        self, component: RectangularReducer, context: PlacementContext
    ) -> GeometricRepresentation:
        return self._build(component, context, self._reducer)

    def build_endcap(
        self, component: RectangularEndcap, context: PlacementContext
    ) -> GeometricRepresentation:
        return self._build(component, context, self._endcap)

    def _duct(self, component: RectangularDuct) -> GeometricRepresentation:
        width = self._dimension(component, "width")
        self._dimension(component, "height")
        length = self._dimension(component, "length")
        outline = self._polygon(
            [
                Point(0, -width / 2),
                Point(length, -width / 2),
                Point(length, width / 2),
                Point(0, width / 2),
            ]
        )
        return GeometricRepresentation(
            component.id, outline, [self._skeleton(Point(0, 0), Point(length, 0))]
        )

    def _elbow(self, component: RectangularElbow) -> GeometricRepresentation:
        width = self._dimension(component, "width")
        self._dimension(component, "height")
        angle = component.angle
        if not isfinite(angle) or not 0 < abs(angle) < pi:
            raise GeometryConstructionError(
                "Plan elbow requires a turn strictly between 0 and 180 degrees"
            )
        inside = self.config.elbow_inside_radius_ratio * width
        radius = inside + width / 2
        setback = radius * tan(abs(angle) / 2)
        side = 1 if angle > 0 else -1
        center = Point(-setback, side * radius)
        inner_start = Point(-setback, side * width / 2)
        outer_start = Point(-setback, -side * width / 2)

        def end_point(radial: float) -> Point:
            return Point(
                center.x + side * radial * sin(angle),
                center.y - side * radial * cos(angle),
            )

        inner_end, outer_end = end_point(inside), end_point(inside + width)
        outline = [
            Arc(inner_start, center, angle),
            Arc(outer_start, center, angle),
            Line(inner_start, outer_start),
            Line(inner_end, outer_end),
        ]
        skeleton = [
            self._skeleton(Point(-setback, 0), Point(0, 0)),
            self._skeleton(
                Point(0, 0), Point(setback * cos(angle), setback * sin(angle))
            ),
        ]
        return GeometricRepresentation(component.id, outline, skeleton)

    def _shoe(self, component: RectangularShoeTakeoff) -> GeometricRepresentation:
        width = self._dimension(component, "width")
        self._dimension(component, "height")
        length = self._dimension(component, "takeoff_length")
        if component.side not in ("left", "right"):
            raise GeometryConstructionError("Shoe side must be left or right")
        # Widen the main-side opening downstream along the main duct.
        low = -width / 2 - (length if component.side == "left" else 0)
        high = width / 2 + (length if component.side == "right" else 0)
        outline = self._polygon(
            [
                Point(0, low),
                Point(length, -width / 2),
                Point(length, width / 2),
                Point(0, high),
            ]
        )
        return GeometricRepresentation(
            component.id, outline, [self._skeleton(Point(0, 0), Point(length, 0))]
        )

    def _reducer(self, component: RectangularReducer) -> GeometricRepresentation:
        inlet = self._dimension(component, "inlet_width")
        outlet = self._dimension(component, "outlet_width")
        self._dimension(component, "inlet_height")
        self._dimension(component, "outlet_height")
        length = self._dimension(component, "length")
        outline = self._polygon(
            [
                Point(0, -inlet / 2),
                Point(length, -outlet / 2),
                Point(length, outlet / 2),
                Point(0, inlet / 2),
            ]
        )
        return GeometricRepresentation(
            component.id, outline, [self._skeleton(Point(0, 0), Point(length, 0))]
        )

    def _endcap(self, component: RectangularEndcap) -> GeometricRepresentation:
        width = self._dimension(component, "width")
        self._dimension(component, "height")
        return GeometricRepresentation(
            component.id, [Line(Point(0, -width / 2), Point(0, width / 2))], []
        )
