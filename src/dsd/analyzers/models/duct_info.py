"""An interpreted duct segment, independent of AutoCAD APIs."""

from dataclasses import dataclass, field

from dsd.geometry.primitives.line import Line


@dataclass
class DuctInfo:
    id: int
    parent_id: int | None
    raw: Line
    ref_line_id: int
    flow: float = 0.0
    width: float | None = None
    height: float | None = None
    diameter: float | None = None
    metadata: dict[str, str] = field(default_factory=dict)

    @property
    def length(self) -> float:
        return self.raw.length()
