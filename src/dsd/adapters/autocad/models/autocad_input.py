"""Extracted CAD entities, without interpreted system membership."""

from dataclasses import dataclass

from .block_info import BlockInfo
from .line_info import LineInfo


@dataclass
class AutoCadInput:
    lines: list[LineInfo]
    blocks: list[BlockInfo]
    roots: list[LineInfo]
