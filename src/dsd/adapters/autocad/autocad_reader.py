"""Read line and terminal primitives without interpreting network topology."""

from typing import Any

from dsd.geometry.primitives import Block, Line, Point

from .models.block_info import BlockInfo
from .models.line_info import LineInfo
from .reader_config import ReaderConfig


class AutoCadReader:
    def __init__(self, autocad: Any, config: ReaderConfig) -> None:
        self.autocad = autocad
        self.config = config
        self.system_roots: dict[str, int] = {}
        self._lines: list[LineInfo] | None = None
        self._blocks: list[BlockInfo] | None = None

    def _read_entity_xdata(self, entity: Any) -> dict[str, str]:
        codes, values = entity.GetXData(self.config.application_name)
        metadata: dict[str, str] = {}
        for code, value in zip(codes or (), values or ()):
            if code != 1000 or not isinstance(value, str) or "=" not in value:
                continue
            key, value = value.split("=", 1)
            if not key:
                continue
            if key == "system-name" and key in metadata:
                raise ValueError("Duplicate system-name key in entity XData")
            metadata[key] = value
        return metadata

    def _construct_line_info(self, entity: Any) -> LineInfo:
        return LineInfo(
            raw_line=Line(Point(*entity.StartPoint), Point(*entity.EndPoint)),
            metadata=self._read_entity_xdata(entity),
        )

    def _construct_block_info(self, entity: Any) -> BlockInfo:
        name = getattr(entity, "EffectiveName", None) or entity.Name
        return BlockInfo(
            raw_block=Block(name=name, center=Point(*entity.InsertionPoint)),
            metadata=self._read_entity_xdata(entity),
        )

    def refresh(self) -> None:
        """Read a fresh snapshot; IDs remain stable until the next refresh."""
        roots: list[LineInfo] = []
        others: list[LineInfo] = []
        blocks: list[BlockInfo] = []
        systems: dict[str, int] = {}
        block_names = {name.casefold() for name in self.config.air_terminal_block_names}
        for entity in self.autocad.iter_objects(block=self.autocad.model):
            if entity.Layer.casefold() != self.config.input_layer.casefold():
                continue
            if entity.ObjectName == "AcDbLine":
                info = self._construct_line_info(entity)
                if "system-name" in info.metadata:
                    name = info.metadata["system-name"]
                    if not name.strip():
                        raise ValueError("system-name cannot be empty")
                    if name in systems:
                        raise ValueError(f"Duplicate system-name: {name!r}")
                    systems[name] = len(roots)
                    roots.append(info)
                else:
                    others.append(info)
            elif entity.ObjectName == "AcDbBlockReference":
                name = getattr(entity, "EffectiveName", None) or entity.Name
                if name.casefold() in block_names:
                    blocks.append(self._construct_block_info(entity))
        lines = roots + others
        for identifier, line in enumerate(lines):
            line.raw_line.id = identifier
        for identifier, block in enumerate(blocks, start=len(lines)):
            block.raw_block.id = identifier
        self._lines, self._blocks, self.system_roots = lines, blocks, systems

    def read_duct_network_lines(self) -> list[LineInfo]:
        if self._lines is None:
            self.refresh()
        return list(self._lines or [])

    def read_duct_network_blocks(self) -> list[BlockInfo]:
        if self._blocks is None:
            self.refresh()
        return list(self._blocks or [])
