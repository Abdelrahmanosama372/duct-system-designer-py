"""Abstract base types for geometry primitives and JSON contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Type, TypeVar

T = TypeVar("T", bound="Primitive")


@dataclass
class PrimitiveStyle:
    layer: str | None = None
    color: str | None = None
    category: str | None = None


class Primitive(ABC):
    """Abstract base contract for serializable geometry primitives."""

    def __init__(self, id: int = -1, style: PrimitiveStyle | None = None):
        self._id = id
        self._style = style

    @property
    def id(self):
        """The id property."""
        return self._id

    @id.setter
    def id(self, value):
        self._id = value

    @property
    def style(self) -> PrimitiveStyle | None:
        return self._style

    @style.setter
    def style(self, value: PrimitiveStyle | None):
        if value is not None and not isinstance(value, PrimitiveStyle):
            raise TypeError("style must be an instance of PrimitiveStyle or None")
        self._style = value

    @abstractmethod
    def transform_2d(self, transform: "Transform2D") -> Primitive2D:
        pass

    @abstractmethod
    def to_json(self) -> dict[Any, Any]:
        """Serialize this primitive into a JSON-compatible dictionary."""
        pass

    @classmethod
    @abstractmethod
    def from_json(cls: Type[T], data: dict[Any, Any]) -> T:
        """Create a primitive instance from a JSON-compatible dictionary."""
        pass


class Primitive2D(Primitive, ABC):
    """Marker base class for geometric 2d primitives."""

    pass


class Primitive3D(Primitive, ABC):
    """Marker base class for geometric 3d primitives."""

    pass
