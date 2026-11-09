"""Find fitting transforms, then connect ducts using placed fitting skeletons."""

from math import atan2, hypot
from typing import Mapping

from dsd.ductsystem.duct_fitting_tree import DuctFittingTree
from dsd.ductsystem.models.rectangular import (
    RectangularDuct,
    RectangularElbow,
    RectangularEndcap,
    RectangularReducer,
    RectangularShoeTakeoff,
)
from dsd.ductsystem.models.sheet_metal_component import SheetMetalComponent
from dsd.ductsystem.sheet_metal_node import SheetMetalNode

from ..geometric_representation import GeometricRepresentation
from ..primitives import Line, Point, Transform2D
from ..primitives.line import EPS
from .placement_context import PlacementContext
from .source_geometry_repository import SourceGeometryRepository


class PlacementError(ValueError):
    """Source geometry or available space cannot support the requested placement."""


class PlacementContextManager:
    def __init__(
        self, tree: DuctFittingTree, source_repo: SourceGeometryRepository
    ) -> None:
        self.tree = tree
        self.source_repo = source_repo
        self.layouts: dict[int, GeometricRepresentation] = {}

    def set_fitting_layouts(
        self, layouts: Mapping[int, GeometricRepresentation]
    ) -> None:
        self.layouts = dict(layouts)

    def _node(self, component: SheetMetalComponent) -> SheetMetalNode:
        for node in self.tree.preorder_traversal():
            if node.component is component:
                return node
        raise PlacementError(f"Component {component.id} is not in this tree")

    def _source(self, node: SheetMetalNode) -> Line:
        if not isinstance(node.component, RectangularDuct):
            raise PlacementError("A source line is required for a duct node")
        return self.source_repo.get_line(node.component.id)

    def _upstream(self, node: SheetMetalNode) -> SheetMetalNode:
        current = node.parent
        while current is not None:
            if isinstance(current.component, RectangularDuct):
                return current
            current = current.parent
        raise PlacementError("Fitting has no upstream duct")

    @staticmethod
    def _axis(line: Line) -> tuple[float, float, float]:
        dx, dy = line.end.x - line.start.x, line.end.y - line.start.y
        length = hypot(dx, dy)
        if length <= EPS:
            raise PlacementError("Source line has no usable XY length")
        return dx / length, dy / length, length

    @classmethod
    def _along(cls, line: Line, distance: float) -> Point:
        ux, uy, _ = cls._axis(line)
        return Point(line.start.x + distance * ux, line.start.y + distance * uy)

    def find_context(self, component: SheetMetalComponent) -> PlacementContext:
        node = self._node(component)
        if isinstance(component, RectangularDuct):
            return self._duct_context(node)
        upstream = self._upstream(node)
        line = self._source(upstream)
        ux, uy, length = self._axis(line)
        angle = atan2(uy, ux)
        if isinstance(component, RectangularElbow):
            origin = self._along(line, length)
        elif isinstance(component, RectangularReducer):
            if upstream.component.width is None:
                raise PlacementError("Reducer requires sized upstream duct")
            origin = self._along(line, length + 1.5 * upstream.component.width)
        elif isinstance(component, RectangularShoeTakeoff):
            if (
                len(node.children) != 1
                or node.children[0].component.id != component.branch_duct_id
            ):
                raise PlacementError("Shoe requires its sole branch duct child")
            if upstream.component.width is None:
                raise PlacementError("Shoe requires sized main duct")
            branch = self._source(node.children[0])
            bx, by, _ = self._axis(branch)
            origin = self._along(branch, upstream.component.width / 2)
            angle = atan2(by, bx)
        elif isinstance(component, RectangularEndcap):
            origin = self._along(line, length + self._extension(upstream))
        else:
            raise PlacementError(f"Unsupported component {type(component).__name__}")
        return PlacementContext(Transform2D(origin, angle))

    @staticmethod
    def _extension(node: SheetMetalNode) -> float:
        if not any(
            isinstance(child.component, RectangularEndcap) for child in node.children
        ):
            return 0.0
        shoes = [
            child.component
            for child in node.children
            if isinstance(child.component, RectangularShoeTakeoff)
        ]
        if not shoes:
            return 0.0
        if any(shoe.width is None for shoe in shoes):
            raise PlacementError("Terminal extension requires sized takeoffs")
        return 2 * max(shoe.width for shoe in shoes)

    def _skeleton_interval(
        self, fitting: SheetMetalNode, source: Line
    ) -> tuple[float, float]:
        try:
            skeleton = self.layouts[fitting.component.id].layout_skeleton
        except KeyError as exc:
            raise PlacementError(
                "Construct fitting geometry before connecting ducts"
            ) from exc
        ux, uy, _ = self._axis(source)
        distances = []
        for line in skeleton:
            points = (line.start, line.end)
            if all(
                abs((point.x - source.start.x) * uy - (point.y - source.start.y) * ux)
                <= EPS
                for point in points
            ):
                distances.extend(
                    (point.x - source.start.x) * ux + (point.y - source.start.y) * uy
                    for point in points
                )
        if not distances:
            raise PlacementError(
                f"Fitting {fitting.component.id} has no skeleton along duct {source.id}"
            )
        return min(distances), max(distances)

    def _duct_context(self, node: SheetMetalNode) -> PlacementContext:
        source = self._source(node)
        ux, uy, length = self._axis(source)
        start, end = 0.0, length + self._extension(node)
        if node.parent is not None and not isinstance(
            node.parent.component, RectangularDuct
        ):
            _, start = self._skeleton_interval(node.parent, source)
        for child in node.children:
            if isinstance(child.component, (RectangularElbow, RectangularReducer)):
                stop, _ = self._skeleton_interval(child, source)
                end = (
                    min(end, stop)
                    if isinstance(child.component, RectangularElbow)
                    else stop
                )
        if end - start <= EPS:
            raise PlacementError(
                f"Fittings leave no positive length for duct {node.component.id}"
            )
        return PlacementContext(
            Transform2D(self._along(source, start), atan2(uy, ux)), length=end - start
        )
