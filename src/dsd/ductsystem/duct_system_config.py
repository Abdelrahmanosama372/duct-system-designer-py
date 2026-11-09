"""System-wide material and pressure classification."""

from dataclasses import dataclass
from typing import Any, Mapping

from .fitting_sizing_config import FittingSizingConfig
from .models.sheet_metal_component import Material, PressureLevels


@dataclass(frozen=True)
class DuctSystemConfig:
    material: Material
    pressure_level: PressureLevels
    fittings: FittingSizingConfig

    def __post_init__(self) -> None:
        if not isinstance(self.fittings, FittingSizingConfig):
            raise ValueError("fittings must be a FittingSizingConfig value")
        if not isinstance(self.material, Material):
            raise ValueError("material must be a Material value")
        if not isinstance(self.pressure_level, PressureLevels):
            raise ValueError("pressure_level must be a PressureLevels value")

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "DuctSystemConfig":
        config = data["ductsystem"]
        material = config["material"]
        # Accept the spelling originally used in the requirements too.
        if material == "Alminum":
            material = "Aluminum"
        return cls(
            Material(material),
            PressureLevels(config["pressure_level"]),
            FittingSizingConfig.from_mapping(data),
        )
