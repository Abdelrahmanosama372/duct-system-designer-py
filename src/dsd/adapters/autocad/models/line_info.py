"""A source line and its string XData metadata."""
from dataclasses import dataclass, field

from dsd.geometry.primitives.line import Line


@dataclass
class LineInfo:
    raw_line: Line
    metadata: dict[str, str] = field(default_factory=dict)
