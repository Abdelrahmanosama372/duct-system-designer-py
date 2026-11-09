"""Rectangular sizing by actual airflow area at a configured FPM limit."""

from math import sqrt

from .duct_sizer import CFM_TO_M3_S, FPM_TO_M_S, DuctSizer
from .duct_sizer_config import DuctSizerConfig
from .models import DuctDimension, SizingContext


class EqualVelocityDuctSizer(DuctSizer):
    def __init__(self, config: DuctSizerConfig) -> None:
        super().__init__(config)
        if config.required_velocity is None:
            raise ValueError("Equal velocity sizing requires required_velocity (FPM)")
        self._velocity_m_s = config.required_velocity * FPM_TO_M_S

    def size_duct(self, context: SizingContext) -> DuctDimension:
        area_mm2 = context.flow * CFM_TO_M3_S / self._velocity_m_s * 1e6
        root_width = sqrt(area_mm2 * self.config.aspect_ratio)
        return self._select_dimensions(
            root_width,
            context.preferred_width,
            lambda width: area_mm2 / width,
        )
