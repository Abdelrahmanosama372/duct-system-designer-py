"""Dimension rules, external-unit targets, and SI air properties."""

from dataclasses import dataclass
from math import ceil, floor, isfinite
from typing import Any, Mapping


@dataclass(frozen=True)
class DuctSizerConfig:
    size_increment: int  # mm, grid anchored at zero
    minimum_duct_dimension: int  # mm
    maximum_duct_dimension: int  # mm
    aspect_ratio: float  # width / height upper limit
    air_density: float  # kg/m³
    dynamic_viscosity: float  # Pa·s
    roughness: float  # m; YAML provides roughness_mm
    required_velocity: float | None = None  # FPM
    required_head_loss: float | None = None  # in. w.g./100 ft
    diameter_tolerance_mm: float = 0.0001
    max_iterations: int = 30
    friction_tolerance: float = 1e-10
    friction_max_iterations: int = 80

    def __post_init__(self) -> None:
        for name in (
            "size_increment",
            "minimum_duct_dimension",
            "maximum_duct_dimension",
            "max_iterations",
            "friction_max_iterations",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        for name in (
            "aspect_ratio",
            "air_density",
            "dynamic_viscosity",
            "diameter_tolerance_mm",
            "friction_tolerance",
        ):
            self._positive(getattr(self, name), name)
        for name in ("required_velocity", "required_head_loss"):
            value = getattr(self, name)
            if value is not None:
                self._positive(value, name)
        if (
            isinstance(self.roughness, bool)
            or not isfinite(self.roughness)
            or self.roughness < 0
        ):
            raise ValueError("roughness must be finite and nonnegative (m)")
        if self.minimum_duct_dimension > self.maximum_duct_dimension:
            raise ValueError("minimum_duct_dimension exceeds maximum_duct_dimension")
        low = ceil(self.minimum_duct_dimension / self.size_increment)
        high = floor(self.maximum_duct_dimension / self.size_increment)
        if low > high:
            raise ValueError("Dimension bounds contain no permitted size increments")

    @staticmethod
    def _positive(value: float, name: str) -> None:
        if isinstance(value, bool) or not isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be positive and finite")

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "DuctSizerConfig":
        config = data["sizing"]
        air = config["air"]
        return cls(
            size_increment=config["size_increment"],
            minimum_duct_dimension=config["minimum_duct_dimension"],
            maximum_duct_dimension=config["maximum_duct_dimension"],
            aspect_ratio=config["aspect_ratio"],
            air_density=air["density_kg_m3"],
            dynamic_viscosity=air["dynamic_viscosity_pa_s"],
            roughness=air["roughness_mm"] / 1000,
            required_velocity=config.get("required_velocity"),
            required_head_loss=config.get("required_head_loss"),
            diameter_tolerance_mm=config.get("diameter_tolerance_mm", 0.0001),
            max_iterations=config.get("max_iterations", 30),
            friction_tolerance=config.get("friction_tolerance", 1e-10),
            friction_max_iterations=config.get("friction_max_iterations", 80),
        )
