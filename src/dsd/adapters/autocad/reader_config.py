"""Configuration for reading a DSD network from Model Space."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml


@dataclass(frozen=True)
class ReaderConfig:
    input_layer: str
    air_terminal_block_names: tuple[str, ...] = ()
    application_name: str = "DSD"

    def __post_init__(self) -> None:
        if not isinstance(self.input_layer, str) or not self.input_layer.strip():
            raise ValueError("input_layer must be a nonempty string")
        if isinstance(self.air_terminal_block_names, str) or any(
            not isinstance(name, str) or not name.strip()
            for name in self.air_terminal_block_names
        ):
            raise ValueError("air_terminal_block_names must contain nonempty names")
        if self.application_name != "DSD":
            raise ValueError("The XData application must be DSD")

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "ReaderConfig":
        config = data["autocad"]["input"]
        names = config.get("air_terminal_blocks", [])
        if not isinstance(names, list) or any(not isinstance(n, str) for n in names):
            raise ValueError("air_terminal_blocks must be a list of block names")
        return cls(
            input_layer=config["line_network_layer"]["name"],
            air_terminal_block_names=tuple(names),
            application_name=config.get("xdata", {}).get("application_name", "DSD"),
        )

    @classmethod
    def from_yaml(cls, path: str | Path) -> "ReaderConfig":
        with Path(path).open(encoding="utf-8") as stream:
            return cls.from_mapping(yaml.safe_load(stream))
