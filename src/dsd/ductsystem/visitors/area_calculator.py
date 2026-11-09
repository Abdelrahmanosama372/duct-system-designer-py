"""Net sheet-metal areas in m², with component dimensions supplied in mm."""

from math import fsum, hypot, isfinite, pi, sqrt

from ..fitting_sizing_config import FittingSizingConfig
from ..models.rectangular import (
    RectangularDuct,
    RectangularElbow,
    RectangularEndcap,
    RectangularReducer,
    RectangularShoeTakeoff,
)
from ..models.sheet_metal_component import SheetMetalComponent
from .sheet_metal_component_visitor import SheetMetalComponentVisitor


class AreaCalculationError(ValueError):
    """A required dimension is missing or invalid for surface-area calculation."""


class AreaCalculatorVisitor(SheetMetalComponentVisitor[float]):
    def __init__(self, config: FittingSizingConfig) -> None:
        self.config = config
        self.areas_m2: dict[int, float] = {}

    @property
    def total_area_m2(self) -> float:
        return fsum(self.areas_m2.values())

    def reset(self) -> None:
        self.areas_m2.clear()

    @staticmethod
    def _dimension(component: SheetMetalComponent, name: str) -> float:
        value = getattr(component, name, None)
        if (
            value is None
            or isinstance(value, bool)
            or not isfinite(value)
            or value <= 0
        ):
            raise AreaCalculationError(
                f"{type(component).__name__} {component.id} requires positive finite {name}"
            )
        return value

    def _record(self, component: SheetMetalComponent, area_mm2: float) -> float:
        if not isfinite(area_mm2) or area_mm2 < 0:
            raise AreaCalculationError(
                f"Invalid surface area for component {component.id}"
            )
        area_m2 = area_mm2 / 1_000_000
        # Visiting the same component again updates its result without double counting.
        self.areas_m2[component.id] = area_m2
        return area_m2

    def visit_rectangular_duct(self, component: RectangularDuct) -> float:
        width = self._dimension(component, "width")
        height = self._dimension(component, "height")
        length = self._dimension(component, "length")
        return self._record(component, 2 * (width + height) * length)

    def visit_rectangular_elbow(self, component: RectangularElbow) -> float:
        width = self._dimension(component, "width")
        height = self._dimension(component, "height")
        angle = abs(component.angle)
        if not isfinite(angle) or not 0 < angle <= pi:
            raise AreaCalculationError(
                "Elbow requires a nonzero angle between -pi and pi"
            )
        inside = component.inside_radius(self.config.elbow_inside_radius_ratio)
        outside = inside + width
        # Two annular-sector cheeks plus the inner and outer curved surfaces.
        area = angle * (outside**2 - inside**2) + height * angle * (inside + outside)
        return self._record(component, area)

    def visit_rectangular_shoetakeoff(self, component: RectangularShoeTakeoff) -> float:
        width = self._dimension(component, "width")
        height = self._dimension(component, "height")
        length = self._dimension(component, "takeoff_length")
        opening = component.width1
        # Two trapezoidal cheeks, one straight side and one 45-degree bevel side.
        area = (width + opening) * length + height * length * (1 + sqrt(2))
        return self._record(component, area)

    def visit_rectangular_reducer(self, component: RectangularReducer) -> float:
        inlet_width = self._dimension(component, "inlet_width")
        inlet_height = self._dimension(component, "inlet_height")
        outlet_width = self._dimension(component, "outlet_width")
        outlet_height = self._dimension(component, "outlet_height")
        length = self._dimension(component, "length")
        # Centered ports: each face slopes through half the dimension difference.
        top_slant = hypot(length, (inlet_height - outlet_height) / 2)
        side_slant = hypot(length, (inlet_width - outlet_width) / 2)
        area = (inlet_width + outlet_width) * top_slant + (
            inlet_height + outlet_height
        ) * side_slant
        return self._record(component, area)

    def visit_rectangular_endcap(self, component: RectangularEndcap) -> float:
        width = self._dimension(component, "width")
        height = self._dimension(component, "height")
        return self._record(component, width * height)
