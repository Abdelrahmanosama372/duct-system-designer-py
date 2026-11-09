from dataclasses import dataclass

from .rectangular_sheet_metal_component import RectangularSheetMetalComponent


@dataclass(kw_only=True)
class RectangularDuctFitting(RectangularSheetMetalComponent):
    """Common type for fittings, whose dimensions are filled after duct sizing."""
