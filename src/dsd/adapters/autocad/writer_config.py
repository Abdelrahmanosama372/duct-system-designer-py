"""Configuration for explicit output-layer cleanup."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml


@dataclass(frozen=True)
class WriterConfig:
    clear_layers: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if isinstance(self.clear_layers, str) or any(
            not isinstance(name, str) or not name.strip() for name in self.clear_layers
        ):
            raise ValueError("clear_layers must contain nonempty layer names")

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "WriterConfig":
        names = data["autocad"]["output"].get("clear", {}).get("include", [])
        if not isinstance(names, list):
            raise ValueError("clear.include must be a list of layer names")
        return cls(clear_layers=tuple(names))

    @classmethod
    def from_yaml(cls, path: str | Path) -> "WriterConfig":
        with Path(path).open(encoding="utf-8") as stream:
            return cls.from_mapping(yaml.safe_load(stream))
