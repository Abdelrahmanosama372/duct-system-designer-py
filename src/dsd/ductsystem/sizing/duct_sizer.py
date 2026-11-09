"""Common rectangular selection rules and conservative bounded bisection."""

from abc import ABC, abstractmethod
from math import ceil, floor, isfinite
from typing import Callable

from .duct_sizer_config import DuctSizerConfig
from .models import DuctDimension, SizingContext

# International foot = 0.3048 m; conventional inch of water = 249.08891 Pa.
CFM_TO_M3_S = 0.3048**3 / 60
FPM_TO_M_S = 0.3048 / 60
IN_WG_PER_100_FT_TO_PA_M = 249.08891 / 30.48


class NoSolutionWithinBounds(ValueError):
    """No permitted rectangular size meets the requested criterion."""


class NumericalConvergenceError(RuntimeError):
    """A bounded numerical solve exhausted its configured iteration limit."""


class DuctSizer(ABC):
    def __init__(self, config: DuctSizerConfig) -> None:
        self.config = config

    @abstractmethod
    def size_duct(self, context: SizingContext) -> DuctDimension:
        """Return dimensions only; leave source contexts and domain objects untouched."""

    @property
    def _minimum(self) -> int:
        return self._round_up(self.config.minimum_duct_dimension)

    @property
    def _maximum(self) -> int:
        return (
            floor(self.config.maximum_duct_dimension / self.config.size_increment)
            * self.config.size_increment
        )

    def _round_up(self, value: float) -> int:
        return ceil(value / self.config.size_increment) * self.config.size_increment

    @staticmethod
    def equivalent_diameter(width: float, height: float) -> float:
        """Equal-friction circular equivalent diameter, in the same units as W/H."""
        if not isfinite(width) or not isfinite(height) or min(width, height) <= 0:
            raise ValueError("Equivalent diameter requires positive finite dimensions")
        return 1.30 * (width * height) ** 0.625 / (width + height) ** 0.25

    def _select_dimensions(
        self,
        root_width: float,
        preferred_width: float | None,
        required_height: Callable[[int], float | None],
    ) -> DuctDimension:
        if preferred_width is None:
            width = min(self._maximum, max(self._minimum, self._round_up(root_width)))
        else:
            if not isfinite(preferred_width) or preferred_width <= 0:
                raise ValueError("preferred_width must be positive and finite (mm)")
            # A supplied parent width is a starting ceiling, never enlarged here.
            width = min(
                self._maximum,
                floor(preferred_width / self.config.size_increment)
                * self.config.size_increment,
            )
        while width >= self._minimum:
            needed = required_height(width)
            if needed is not None:
                height = max(self._minimum, self._round_up(needed))
                if (
                    height <= self._maximum
                    and width / height <= self.config.aspect_ratio
                ):
                    return DuctDimension(width, height)
            width -= self.config.size_increment
        raise NoSolutionWithinBounds(
            "No size satisfies dimension, increment, aspect-ratio, and sizing constraints"
        )

    def find_eqv_rectangular_duct_dimensions(
        self,
        equivalent_diameter: float,
        preferred_width: float | None = None,
    ) -> DuctDimension:
        """Select a rectangle by equal-friction diameter, not equal-velocity area."""
        if not isfinite(equivalent_diameter) or equivalent_diameter <= 0:
            raise ValueError("equivalent_diameter must be positive and finite (mm)")
        ratio = self.config.aspect_ratio
        height = equivalent_diameter * (ratio + 1) ** 0.25 / (1.30 * ratio**0.625)
        return self._select_dimensions(
            ratio * height,
            preferred_width,
            lambda width: self._height_for_equivalent_diameter(
                width, equivalent_diameter
            ),
        )

    def _height_for_equivalent_diameter(
        self, width: int, diameter: float
    ) -> float | None:
        if self.equivalent_diameter(width, self._minimum) >= diameter:
            return float(self._minimum)
        if self.equivalent_diameter(width, self._maximum) < diameter:
            return None
        _, upper = self._bisect(
            float(self._minimum),
            float(self._maximum),
            lambda height: self.equivalent_diameter(width, height) >= diameter,
            epsilon=self.config.diameter_tolerance_mm,
            max_iterations=self.config.max_iterations,
        )
        return upper

    @staticmethod
    def _bisect(
        lower: float,
        upper: float,
        is_upper_half: Callable[[float], bool],
        *,
        epsilon: float,
        max_iterations: int,
    ) -> tuple[float, float]:
        """Narrow a bracket whose predicate changes from False to True.

        Return both bounds so the caller can choose the conservative side.
        The caller establishes the bracket and supplies tolerance in its units.
        """
        for _ in range(max_iterations):
            if upper - lower <= epsilon:
                return lower, upper
            middle = (lower + upper) / 2
            if is_upper_half(middle):
                upper = middle
            else:
                lower = middle
        if upper - lower <= epsilon:
            return lower, upper
        raise NumericalConvergenceError(
            "Bisection did not reach the configured tolerance"
        )
