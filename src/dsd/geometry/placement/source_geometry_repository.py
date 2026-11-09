"""Processed source centerlines, keyed by DuctInfo.raw.id within one system."""

from copy import deepcopy
from typing import Mapping

from dsd.analyzers.models import SystemTopology

from ..primitives import Line


class SourceGeometryRepository:
    def __init__(self, lines: Mapping[int, Line]) -> None:
        if any(identifier != line.id for identifier, line in lines.items()):
            raise ValueError("Repository keys must match processed line IDs")
        self.lines = deepcopy(dict(lines))

    @classmethod
    def from_topology(cls, topology: SystemTopology) -> "SourceGeometryRepository":
        if any(info.id != info.raw.id for info in topology.duct_infos):
            raise ValueError("Processed line IDs must match topology duct IDs")
        lines = {info.raw.id: info.raw for info in topology.duct_infos}
        if len(lines) != len(topology.duct_infos):
            raise ValueError("Processed line IDs must be unique")
        return cls(lines)

    def get_line(self, line_id: int) -> Line:
        try:
            return self.lines[line_id]
        except KeyError as exc:
            raise ValueError(f"Missing processed source line {line_id}") from exc
