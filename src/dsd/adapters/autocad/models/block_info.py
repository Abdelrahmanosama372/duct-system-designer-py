"""A source block and its string XData metadata."""

from dataclasses import dataclass, field

from dsd.geometry.primitives.block import Block


@dataclass
class BlockInfo:
    raw_block: Block
    metadata: dict[str, str] = field(default_factory=dict)
