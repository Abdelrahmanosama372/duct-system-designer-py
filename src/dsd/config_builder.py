"""Read one application YAML and construct the validated module configs."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml

from dsd.adapters.autocad.reader_config import ReaderConfig
from dsd.adapters.autocad.writer_config import WriterConfig
from dsd.ductsystem.duct_system_config import DuctSystemConfig
from dsd.ductsystem.sizing import DuctSizerConfig


class ConfigError(ValueError):
    """Application configuration is missing a required field or has an invalid value."""


@dataclass(frozen=True)
class ApplicationConfig:
    reader: ReaderConfig
    writer: WriterConfig
    ductsystem: DuctSystemConfig
    sizing: DuctSizerConfig


class ConfigBuilder:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def build(self) -> ApplicationConfig:
        try:
            with self.path.open(encoding="utf-8") as stream:
                data = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            raise ConfigError(f"Invalid YAML in {self.path}") from exc
        return self.from_mapping(data)

    @staticmethod
    def _mapping(value: Any, name: str) -> Mapping[str, Any]:
        if not isinstance(value, Mapping):
            raise ConfigError(f"{name} must be a mapping")
        return value

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> ApplicationConfig:
        data = cls._mapping(data, "Configuration")
        try:
            autocad = cls._mapping(data["autocad"], "autocad")
            input_config = cls._mapping(autocad["input"], "autocad.input")
            cls._mapping(
                input_config["line_network_layer"], "autocad.input.line_network_layer"
            )
            if "xdata" in input_config:
                cls._mapping(input_config["xdata"], "autocad.input.xdata")
            output = cls._mapping(autocad["output"], "autocad.output")
            if "clear" in output:
                cls._mapping(output["clear"], "autocad.output.clear")
            cls._mapping(data["ductsystem"], "ductsystem")
            sizing = cls._mapping(data["sizing"], "sizing")
            cls._mapping(sizing["air"], "sizing.air")
            return ApplicationConfig(
                ReaderConfig.from_mapping(data),
                WriterConfig.from_mapping(data),
                DuctSystemConfig.from_mapping(data),
                DuctSizerConfig.from_mapping(data),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ConfigError(f"Invalid application configuration: {exc}") from exc
