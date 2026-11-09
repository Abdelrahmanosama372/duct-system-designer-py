"""Block primitive definition and JSON conversion utilities."""

from __future__ import annotations

from typing import Any, override

from .base import Primitive2D, PrimitiveStyle
from .point import Point


class Block(Primitive2D):
    """Named block entity positioned at a single point in 2D space."""

    def __init__(
        self,
        name: str,
        center: Point,
        id: int = -1,
        style: PrimitiveStyle | None = None,
    ) -> None:
        """Initialize a block with a display name and insertion position."""
        self._name: str = name
        self._center: Point = center
        super().__init__(id=id, style=style)

    @property
    def name(self) -> str:
        """Return the block name."""
        return self._name

    @property
    def center(self) -> Point:
        """Return the block insertion point."""
        return self._center

    @override
    def transform_2d(self, transform: "Transform2D") -> Primitive2D:
        return self._center.transform_2d()

    @override
    def to_json(self) -> dict[Any, Any]:
        """Serialize this block to the project JSON shape."""
        data = {"Block": {"name": self.name, "center": self.center.to_json()}}
        if self.style is not None:
            data["Block"]["style"] = {
                "layer": self.style.layer,
                "color": self.style.color,
                "category": self.style.category,
            }
        return data

    @override
    @classmethod
    def from_json(cls, data: dict[Any, Any]) -> Block:
        """Build a block instance from the project JSON shape."""
        block_props = data["Block"]
        name = str(block_props["name"])
        center = Point.from_json(block_props["center"])
        style_data = block_props.get("style")
        style = (
            PrimitiveStyle(
                layer=style_data.get("layer"),
                color=style_data.get("color"),
                category=style_data.get("category"),
            )
            if isinstance(style_data, dict)
            else None
        )
        return Block(name=name, center=center, style=style)
