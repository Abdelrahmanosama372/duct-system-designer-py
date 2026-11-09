"""An interpreted terminal and the source block reference."""

from dataclasses import dataclass, field


@dataclass
class AirTerminalInfo:
    id: int
    parent_id: int
    flow: float
    ref_block_id: int
    width: float | None = None
    height: float | None = None
    diameter: float | None = None
    metadata: dict[str, str] = field(default_factory=dict)
