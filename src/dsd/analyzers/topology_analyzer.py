"""Interpret each rooted duct network using only drawing X and Y coordinates."""

from collections import deque
from dataclasses import dataclass, field
from math import isfinite

from dsd.adapters.autocad.models import AutoCadInput, LineInfo
from dsd.geometry.primitives import Line, Point
from dsd.geometry.primitives.line import EPS
from dsd.system_type import SystemType

from .models import AirTerminalInfo, DuctInfo, SystemTopology


class TopologyError(ValueError):
    """The supplied geometry cannot represent an unambiguous rooted tree."""


class TopologyConflictError(TopologyError):
    """A connected network contains more than one registered system root."""


@dataclass
class _Segment:
    raw: Line
    source_index: int
    start_node: int
    end_node: int


@dataclass
class _SplitNetwork:
    """Temporary split geometry; this is not a domain fitting tree."""

    nodes: dict[Point, int] = field(default_factory=dict)
    adjacency: dict[int, list[int]] = field(default_factory=dict)
    segments: list[_Segment] = field(default_factory=list)

    def add_segment(self, raw: Line, source_index: int) -> None:
        start = self.nodes.setdefault(raw.start, len(self.nodes))
        end = self.nodes.setdefault(raw.end, len(self.nodes))
        if start == end:
            raise TopologyError("Segment endpoints collapse within geometry tolerance")
        edge = len(self.segments)
        self.segments.append(_Segment(raw, source_index, start, end))
        self.adjacency.setdefault(start, []).append(edge)
        self.adjacency.setdefault(end, []).append(edge)


def _line_2d(source: Line) -> Line:
    """Copy source geometry into XY so existing 3D helpers cannot use its Z."""
    return Line(
        Point(source.start.x, source.start.y),
        Point(source.end.x, source.end.y),
        id=source.id,
        line_type=source.line_type,
        style=source.style,
    )


def _snap_to_line_2d(line: Line, point: Point) -> Point:
    """Keep a terminal accepted within tolerance exactly on its source segment."""
    dx, dy = line.end.x - line.start.x, line.end.y - line.start.y
    fraction = ((point.x - line.start.x) * dx + (point.y - line.start.y) * dy) / (
        dx * dx + dy * dy
    )
    fraction = max(0.0, min(1.0, fraction))
    return Point(line.start.x + fraction * dx, line.start.y + fraction * dy)


def _intersection(first: Line, second: Line) -> Point | None:
    if first.length() <= EPS or second.length() <= EPS:
        return None
    hit, point = first.intersects_line_2D(second)
    if not hit or point is None:
        return None
    if not first.pass_through_point(point) or not second.pass_through_point(point):
        return None
    return point


def _reject_overlap(first: Line, second: Line) -> None:
    shared = [
        point
        for point in (first.start, first.end, second.start, second.end)
        if first.pass_through_point(point) and second.pass_through_point(point)
    ]
    if any(p.distance(q) > EPS for p in shared for q in shared):
        raise TopologyError("Overlapping CAD lines have ambiguous connectivity")


def _number(metadata: dict[str, str], key: str, required: bool = False) -> float | None:
    value = metadata.get(key)
    if value is None:
        if required:
            raise TopologyError(f"Terminal metadata requires {key!r}")
        return None
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise TopologyError(f"Invalid numeric metadata {key}={value!r}") from exc
    if not isfinite(result) or result < 0 or (key != "flow" and result == 0):
        raise TopologyError(f"Invalid numeric metadata {key}={value!r}")
    return result


def _dimensions(metadata: dict[str, str]) -> dict[str, float | None]:
    return {key: _number(metadata, key) for key in ("width", "height", "diameter")}


class TopologyAnalyzer:
    def __init__(self, autocad_input: AutoCadInput) -> None:
        self.autocad_input = autocad_input

    def analyze(self, root: LineInfo) -> SystemTopology:
        """Run each interpretation stage without modifying source CAD entities."""
        root_index, system_type = self._validate_root(root)
        lines = [_line_2d(info.raw_line) for info in self.autocad_input.lines]
        cuts = self._discover_connected_lines(root_index, lines)
        terminal_points = self._add_terminal_cuts(lines, cuts)
        network = self._split_lines(lines, cuts)
        inlet = self._find_inlet(lines[root_index], network)
        ducts, incoming = self._orient_ducts(network, inlet)
        terminals = self._attach_terminals(
            network, incoming, terminal_points, len(ducts)
        )
        self._sum_downstream_flows(ducts, terminals)
        return SystemTopology(
            root.metadata["system-name"], ducts, terminals, system_type
        )

    def _validate_root(self, root: LineInfo) -> tuple[int, SystemType]:
        data = self.autocad_input
        if not any(root is candidate for candidate in data.roots):
            raise TopologyError("Supplied root is not a registered root")
        if not any(root is candidate for candidate in data.lines):
            raise TopologyError("Registered root is missing from input lines")
        if not root.metadata.get("system-name", "").strip():
            raise TopologyError("Root requires nonempty system-name metadata")
        try:
            system_type = SystemType(root.metadata.get("system-type"))
        except ValueError as exc:
            raise TopologyError(
                "Root requires system-type=supply or system-type=return"
            ) from exc
        source_ids = [info.raw_line.id for info in data.lines]
        if len(source_ids) != len(set(source_ids)):
            raise TopologyError("Source line IDs must be unique")
        block_ids = [info.raw_block.id for info in data.blocks]
        if len(block_ids) != len(set(block_ids)):
            raise TopologyError("Source block IDs must be unique")
        return next(i for i, info in enumerate(data.lines) if info is root), system_type

    def _discover_connected_lines(
        self,
        root_index: int,
        lines: list[Line],
    ) -> dict[int, list[Point]]:
        """Discover membership and collect junction cuts, visiting each pair once."""
        data = self.autocad_input
        registered = {
            i
            for i, info in enumerate(data.lines)
            if any(info is root for root in data.roots)
        }
        cuts: dict[int, list[Point]] = {root_index: []}
        pending = deque([root_index])
        checked: set[tuple[int, int]] = set()
        while pending:
            index = pending.popleft()
            if lines[index].length() <= EPS:
                raise TopologyError("Zero-length or sub-tolerance source line")
            for other_index, other in enumerate(lines):
                pair = (min(index, other_index), max(index, other_index))
                if index == other_index or pair in checked:
                    continue
                checked.add(pair)
                point = _intersection(lines[index], other)
                if point is None:
                    continue
                if other_index in registered and other_index != root_index:
                    raise TopologyConflictError(
                        f"System {data.lines[root_index].metadata['system-name']!r} "
                        f"connects to root {data.lines[other_index].metadata.get('system-name')!r}"
                    )
                _reject_overlap(lines[index], other)
                if other_index not in cuts:
                    cuts[other_index] = []
                    pending.append(other_index)
                cuts[index].append(point)
                cuts[other_index].append(point)
        return cuts

    def _add_terminal_cuts(
        self,
        lines: list[Line],
        cuts: dict[int, list[Point]],
    ) -> dict[int, list[Point]]:
        terminal_points: dict[int, list[Point]] = {}
        for block_index, info in enumerate(self.autocad_input.blocks):
            center = Point(info.raw_block.center.x, info.raw_block.center.y)
            for index in cuts:
                if lines[index].pass_through_point(center):
                    point = _snap_to_line_2d(lines[index], center)
                    cuts[index].append(point)
                    terminal_points.setdefault(block_index, []).append(point)
        return terminal_points

    @staticmethod
    def _split_lines(lines: list[Line], cuts: dict[int, list[Point]]) -> _SplitNetwork:
        network = _SplitNetwork()
        for index, points in cuts.items():
            source = lines[index]
            ordered = sorted(points, key=lambda point: source.start.distance(point))
            for segment in source.split_at_unchecked(ordered):
                network.add_segment(segment, index)
        return network

    @staticmethod
    def _find_inlet(root: Line, network: _SplitNetwork) -> int:
        start, end = network.nodes.get(root.start), network.nodes.get(root.end)
        if start is None or end is None:
            raise TopologyError("Root disappeared during splitting")
        start_connected = len(network.adjacency[start]) > 1
        end_connected = len(network.adjacency[end]) > 1
        if start_connected and end_connected:
            raise TopologyError(
                "Root has connections at both endpoints; inlet is ambiguous"
            )
        inlet = end if start_connected else start
        if len(network.adjacency[inlet]) != 1:
            raise TopologyError("Root inlet is ambiguous")
        return inlet

    def _orient_ducts(
        self,
        network: _SplitNetwork,
        inlet: int,
    ) -> tuple[list[DuctInfo], dict[int, int | None]]:
        """Traverse iteratively; parents receive IDs before their descendants."""
        ducts: list[DuctInfo] = []
        incoming: dict[int, int | None] = {inlet: None}
        visited: set[int] = set()
        queue = deque([inlet])
        while queue:
            current = queue.popleft()
            for edge in network.adjacency[current]:
                if edge in visited:
                    continue
                visited.add(edge)
                segment = network.segments[edge]
                forward = current == segment.start_node
                following = segment.end_node if forward else segment.start_node
                if following in incoming:
                    raise TopologyError("Cyclic duct networks are unsupported")
                duct = self._make_duct(segment, forward, len(ducts), incoming[current])
                ducts.append(duct)
                incoming[following] = duct.id
                queue.append(following)
        if len(visited) != len(network.segments):
            raise TopologyError("Splitting produced disconnected geometry")
        return ducts, incoming

    def _make_duct(
        self,
        segment: _Segment,
        forward: bool,
        identifier: int,
        parent_id: int | None,
    ) -> DuctInfo:
        source = self.autocad_input.lines[segment.source_index]
        line = segment.raw
        raw = Line(
            line.start if forward else line.end,
            line.end if forward else line.start,
            id=identifier,
            line_type=line.line_type,
            style=line.style,
        )
        return DuctInfo(
            id=identifier,
            parent_id=parent_id,
            raw=raw,
            ref_line_id=source.raw_line.id,
            metadata=dict(source.metadata),
            **_dimensions(source.metadata),
        )

    def _attach_terminals(
        self,
        network: _SplitNetwork,
        incoming: dict[int, int | None],
        terminal_points: dict[int, list[Point]],
        first_id: int,
    ) -> list[AirTerminalInfo]:
        terminals: list[AirTerminalInfo] = []
        for block_index, points in terminal_points.items():
            if any(point not in network.nodes for point in points):
                raise TopologyError(
                    "Terminal cut disappeared within geometry tolerance"
                )
            attachments = {network.nodes[point] for point in points}
            if len(attachments) != 1:
                raise TopologyError("Terminal has ambiguous attachments")
            parent = incoming[next(iter(attachments))]
            if parent is None:
                raise TopologyError("Terminal at root inlet has no upstream duct")
            source = self.autocad_input.blocks[block_index]
            flow = _number(source.metadata, "flow", required=True)
            assert flow is not None
            terminals.append(
                AirTerminalInfo(
                    id=first_id + len(terminals),
                    parent_id=parent,
                    ref_block_id=source.raw_block.id,
                    flow=flow,
                    metadata=dict(source.metadata),
                    **_dimensions(source.metadata),
                )
            )
        return terminals

    @staticmethod
    def _sum_downstream_flows(
        ducts: list[DuctInfo],
        terminals: list[AirTerminalInfo],
    ) -> None:
        for terminal in terminals:
            ducts[terminal.parent_id].flow += terminal.flow
        for duct in reversed(ducts):
            if duct.parent_id is not None:
                ducts[duct.parent_id].flow += duct.flow
