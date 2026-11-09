from dataclasses import dataclass

from ..sheet_metal_component import SheetMetalComponent, validate_dimension


@dataclass(kw_only=True)
class RectangularSheetMetalComponent(SheetMetalComponent):
    width: float | None = None
    height: float | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        validate_dimension(self.width, "width")
        validate_dimension(self.height, "height")
