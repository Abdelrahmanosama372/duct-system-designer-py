"""Equal-friction sizing using a circular equivalent and Colebrook–White."""

from math import isfinite, log10, pi

from .duct_sizer import (
    CFM_TO_M3_S,
    IN_WG_PER_100_FT_TO_PA_M,
    DuctSizer,
    NoSolutionWithinBounds,
    NumericalConvergenceError,
)
from .duct_sizer_config import DuctSizerConfig
from .models import DuctDimension, SizingContext


class EqualFrictionDuctSizer(DuctSizer):
    def __init__(self, config: DuctSizerConfig) -> None:
        super().__init__(config)
        if config.required_head_loss is None:
            raise ValueError(
                "Equal friction sizing requires required_head_loss (in. w.g./100 ft)"
            )
        self._target_pa_m = config.required_head_loss * IN_WG_PER_100_FT_TO_PA_M

    def size_duct(self, context: SizingContext) -> DuctDimension:
        diameter = self.find_equivalent_diameter(context.flow)
        dimensions = self.find_eqv_rectangular_duct_dimensions(
            diameter, context.preferred_width
        )
        actual_diameter = self.equivalent_diameter(dimensions.width, dimensions.height)
        if self.pressure_loss_pa_m(context.flow, actual_diameter) > self._target_pa_m:
            raise NumericalConvergenceError(
                "Rounded dimensions do not meet the friction target"
            )
        return dimensions

    def find_equivalent_diameter(self, flow: float) -> float:
        """Flow in CFM; return a conservative circular diameter in mm."""
        SizingContext(flow)  # Validate standalone calls too.
        lower = 20.0
        upper = self.equivalent_diameter(self._maximum, self._maximum)
        if upper < lower or self.pressure_loss_pa_m(flow, upper) > self._target_pa_m:
            raise NoSolutionWithinBounds(
                "Maximum permitted duct cannot meet the friction target"
            )
        if self.pressure_loss_pa_m(flow, lower) <= self._target_pa_m:
            return lower
        _, upper = self._bisect(
            lower,
            upper,
            lambda diameter: self.pressure_loss_pa_m(flow, diameter)
            <= self._target_pa_m,
            epsilon=self.config.diameter_tolerance_mm,
            max_iterations=self.config.max_iterations,
        )
        return upper

    def pressure_loss_pa_m(self, flow: float, diameter: float) -> float:
        """Circular loss per metre; inputs are CFM and diameter in mm."""
        SizingContext(flow)
        if not isfinite(diameter) or diameter <= 0:
            raise ValueError("diameter must be positive and finite (mm)")
        diameter_m = diameter / 1000
        velocity = flow * CFM_TO_M3_S / (pi * diameter_m**2 / 4)
        reynolds = (
            self.config.air_density
            * velocity
            * diameter_m
            / self.config.dynamic_viscosity
        )
        friction = self.friction_factor(reynolds, diameter)
        return friction * self.config.air_density * velocity**2 / (2 * diameter_m)

    def friction_factor(self, reynolds: float, diameter: float) -> float:
        """Darcy friction factor; diameter is mm, roughness is configured in m."""
        if (
            not isfinite(reynolds)
            or reynolds <= 0
            or not isfinite(diameter)
            or diameter <= 0
        ):
            raise ValueError("Reynolds number and diameter must be positive and finite")
        if reynolds < 2300:
            return 64 / reynolds
        # Solve Colebrook for x=1/sqrt(f), whose residual is increasing.
        roughness_term = self.config.roughness / (3.7 * diameter / 1000)

        def residual(x: float) -> float:
            return x + 2 * log10(roughness_term + 2.51 * x / reynolds)

        lower, upper = 1e-12, 1.0
        if residual(lower) >= 0:
            raise NoSolutionWithinBounds(
                "Roughness is too large for the requested diameter"
            )
        for _ in range(self.config.friction_max_iterations):
            if residual(upper) >= 0:
                break
            upper *= 2
        else:
            raise NumericalConvergenceError(
                "Could not bracket the Colebrook friction factor"
            )
        lower, _ = self._bisect(
            lower,
            upper,
            lambda x: residual(x) >= 0,
            epsilon=self.config.friction_tolerance,
            max_iterations=self.config.friction_max_iterations,
        )
        # Lower x produces a conservative (larger) Darcy friction factor.
        return 1 / lower**2
