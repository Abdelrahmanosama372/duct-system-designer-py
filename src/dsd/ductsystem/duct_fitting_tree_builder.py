"""Construct unsized sheet-metal components from an interpreted system topology."""

from collections import deque
from itertools import count
from math import atan2, hypot, isclose, pi
from typing import Iterator

from dsd.analyzers.models import DuctInfo, SystemTopology
from dsd.geometry.primitives.line import EPS

from .duct_fitting_tree import DuctFittingTree
from .duct_system_config import DuctSystemConfig
from .models.rectangular import (
    RectangularDuct,
    RectangularElbow,
    RectangularEndcap,
    RectangularShoeTakeoff,
)
from .sheet_metal_node import SheetMetalNode


class DuctTreeError(ValueError):
    """Topology cannot be represented by the currently supported duct fittings."""


class DuctFittingTreeBuilder:
    def __init__(self, config: DuctSystemConfig) -> None:
        self.config = config

    def build(self, topology: SystemTopology) -> DuctFittingTree:
        root, children = self._validate_topology(topology)
        ducts = {
            info.id: SheetMetalNode(self._make_duct(info))
            for info in topology.duct_infos
        }
        identifiers = count(max(ducts) + 1)
        queue = deque([root])
        while queue:
            parent = queue.popleft()
            outgoing = children[parent.id]
            self._connect_junction(parent, outgoing, ducts, identifiers)
            queue.extend(outgoing)
        return DuctFittingTree(ducts[root.id])

    @staticmethod
    def _validate_topology(
        topology: SystemTopology,
    ) -> tuple[DuctInfo, dict[int, list[DuctInfo]]]:
        if not topology.system_name.strip():
            raise DuctTreeError("System name must not be empty")
        infos = {info.id: info for info in topology.duct_infos}
        if not infos:
            raise DuctTreeError("System topology contains no ducts")
        if len(infos) != len(topology.duct_infos):
            raise DuctTreeError("Duct topology IDs must be unique")
        roots = [info for info in infos.values() if info.parent_id is None]
        if len(roots) != 1:
            raise DuctTreeError("System topology must have exactly one root duct")
        children: dict[int, list[DuctInfo]] = {identifier: [] for identifier in infos}
        for info in infos.values():
            if info.diameter is not None:
                raise DuctTreeError(
                    "Circular ducts are not supported in the rectangular tree"
                )
            if (
                hypot(
                    info.raw.end.x - info.raw.start.x, info.raw.end.y - info.raw.start.y
                )
                <= EPS
            ):
                raise DuctTreeError("Duct source geometry must have positive XY length")
            if info.parent_id is None:
                continue
            if info.parent_id not in infos:
                raise DuctTreeError(f"Missing parent duct {info.parent_id}")
            parent = infos[info.parent_id]
            if (
                hypot(
                    parent.raw.end.x - info.raw.start.x,
                    parent.raw.end.y - info.raw.start.y,
                )
                > EPS
            ):
                raise DuctTreeError(
                    "Child duct must start at the upstream duct endpoint"
                )
            children[info.parent_id].append(info)
        visited: set[int] = set()
        queue = deque(roots)
        while queue:
            info = queue.popleft()
            if info.id in visited:
                raise DuctTreeError("Duct topology contains a cycle")
            visited.add(info.id)
            queue.extend(children[info.id])
        if len(visited) != len(infos):
            raise DuctTreeError("Duct topology contains disconnected or cyclic ducts")
        return roots[0], children

    def _make_duct(self, info: DuctInfo) -> RectangularDuct:
        return RectangularDuct(
            id=info.id,
            flow=info.flow,
            material=self.config.material,
            pressure_level=self.config.pressure_level,
            width=info.width,
            height=info.height,
            length=hypot(
                info.raw.end.x - info.raw.start.x,
                info.raw.end.y - info.raw.start.y,
            ),
            ref_line_id=info.ref_line_id,
        )

    @staticmethod
    def _turn(parent: DuctInfo, child: DuctInfo) -> float:
        ax, ay = (
            parent.raw.end.x - parent.raw.start.x,
            parent.raw.end.y - parent.raw.start.y,
        )
        bx, by = (
            child.raw.end.x - child.raw.start.x,
            child.raw.end.y - child.raw.start.y,
        )
        return atan2(ax * by - ay * bx, ax * bx + ay * by)

    def _connect_junction(
        self,
        parent: DuctInfo,
        outgoing: list[DuctInfo],
        ducts: dict[int, SheetMetalNode],
        identifiers: Iterator[int],
    ) -> None:
        if not outgoing:
            return
        if len(outgoing) == 1:
            child = outgoing[0]
            angle = self._turn(parent, child)
            upstream = ducts[parent.id]
            if not isclose(angle, 0.0, abs_tol=1e-9):
                elbow = RectangularElbow(
                    id=next(identifiers),
                    flow=child.flow,
                    angle=angle,
                    material=self.config.material,
                    pressure_level=self.config.pressure_level,
                )
                node = SheetMetalNode(elbow)
                upstream.add_child(node)
                upstream = node
            upstream.add_child(ducts[child.id])
            return
        straight, branches = self._classify_branches(parent, outgoing)
        upstream = ducts[parent.id]
        self._connect_takeoffs(upstream, branches, ducts, identifiers)
        if straight is not None:
            upstream.add_child(ducts[straight.id])
        else:
            upstream.add_child(
                SheetMetalNode(
                    RectangularEndcap(
                        id=next(identifiers),
                        flow=0.0,
                        material=self.config.material,
                        pressure_level=self.config.pressure_level,
                    )
                )
            )

    def _classify_branches(
        self,
        parent: DuctInfo,
        outgoing: list[DuctInfo],
    ) -> tuple[DuctInfo | None, dict[str, DuctInfo]]:
        straight = None
        branches: dict[str, DuctInfo] = {}
        for child in outgoing:
            angle = self._turn(parent, child)
            if isclose(angle, 0.0, abs_tol=1e-9):
                if straight is not None:
                    raise DuctTreeError("Junction has multiple straight continuations")
                straight = child
                continue
            if not isclose(abs(angle), pi / 2, abs_tol=1e-9):
                raise DuctTreeError(
                    "Branch junctions must be perpendicular to the main duct"
                )
            side = "left" if angle > 0 else "right"
            if side in branches:
                raise DuctTreeError(f"Junction has multiple {side} branches")
            branches[side] = child
        if not branches:
            raise DuctTreeError("Junction has no supported side branches")
        return straight, branches

    def _connect_takeoffs(
        self,
        upstream: SheetMetalNode,
        branches: dict[str, DuctInfo],
        ducts: dict[int, SheetMetalNode],
        identifiers: Iterator[int],
    ) -> None:
        for side in ("left", "right"):
            if side not in branches:
                continue
            branch = branches[side]
            takeoff = SheetMetalNode(
                RectangularShoeTakeoff(
                    id=next(identifiers),
                    flow=branch.flow,
                    side=side,
                    branch_duct_id=branch.id,
                    material=self.config.material,
                    pressure_level=self.config.pressure_level,
                )
            )
            upstream.add_child(takeoff)
            takeoff.add_child(ducts[branch.id])
