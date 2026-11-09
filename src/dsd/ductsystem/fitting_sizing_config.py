"""Configured fitting lengths and elbow inside-radius multiplier."""

from dataclasses import dataclass
from math import isfinite
from typing import Any, Mapping


@dataclass(frozen=True)
class FittingSizingConfig:
    takeoff_length: float  # mm
    reducer_length: float  # mm
    elbow_inside_radius_ratio: float  # inside radius / duct width

    def __post_init__(self) -> None:
        for name in ("takeoff_length", "reducer_length", "elbow_inside_radius_ratio"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be positive and finite")

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "FittingSizingConfig":
        config = data["ductsystem"]["fittings"]
        if not isinstance(config, Mapping):
            raise ValueError("ductsystem.fittings must be a mapping")
        return cls(
            takeoff_length=config["takeoff_length"],
            reducer_length=config["reducer_length"],
            elbow_inside_radius_ratio=config["elbow_inside_radius_ratio"],
        )
