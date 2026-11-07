"""Write primitives to existing layers in the active drawing."""

from array import array
from math import atan2, hypot, isfinite, tau
from typing import Any

from dsd.geometry.primitives import Arc, Circle, Line, Point, Rectangle
from dsd.geometry.primitives.base import Primitive

from .writer_config import WriterConfig


class AutoCadWriter:
    def __init__(self, autocad: Any, config: WriterConfig) -> None:
        self.autocad = autocad
        self.config = config

    @staticmethod
    def _point(point: Point) -> array:
        # AutoCAD accepts a SAFEARRAY of doubles for a WCS point.
        return array("d", [point.x, point.y, point.z])

    def _require_layer(self, name: str) -> None:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("A nonempty output layer name is required")
        for layer in self.autocad.doc.Layers:
            if layer.Name.casefold() == name.casefold():
                return
        raise ValueError(f"Output layer does not exist: {name!r}")

    def write_primitive(self, primitive: Primitive, layer_name: str) -> None:
        self._require_layer(layer_name)
        model = self.autocad.model
        if isinstance(primitive, Line):
            entities = [
                model.AddLine(self._point(primitive.start), self._point(primitive.end))
            ]
        elif isinstance(primitive, Rectangle):
            entities = [
                model.AddLine(self._point(edge.start), self._point(edge.end))
                for edge in primitive.edges()
            ]
        elif isinstance(primitive, Circle):
            if not isfinite(primitive.radius) or primitive.radius <= 0:
                raise ValueError("Circle radius must be positive and finite")
            entities = [
                model.AddCircle(self._point(primitive.center), primitive.radius)
            ]
        elif isinstance(primitive, Arc):
            dx = primitive.start.x - primitive.center.x
            dy = primitive.start.y - primitive.center.y
            radius = hypot(dx, dy)
            sweep = primitive.angle
            if (
                not isfinite(radius)
                or radius <= 0
                or not isfinite(sweep)
                or not 0 < abs(sweep) < tau
            ):
                raise ValueError(
                    "Arc requires a positive radius and a sweep between -2π and 2π, excluding zero"
                )
            start = atan2(dy, dx)
            end = start + sweep
            if sweep < 0:
                start, end = end, start
            entities = [model.AddArc(self._point(primitive.center), radius, start, end)]
        else:
            raise TypeError(f"Unsupported primitive: {type(primitive).__name__}")
        for entity in entities:
            entity.Layer = layer_name

    def write_text(
        self,
        text: str,
        position: Point,
        height: float,
        layer_name: str,
        rotation: float = 0.0,
    ) -> None:
        self._require_layer(layer_name)
        if not isfinite(height) or height <= 0:
            raise ValueError("Text height must be positive and finite")
        if not isfinite(rotation):
            raise ValueError("Text rotation must be finite")
        if "\n" in text or "\r" in text:
            raise ValueError("Only single-line text is supported")
        entity = self.autocad.model.AddText(text, self._point(position), height)
        entity.Rotation = rotation
        entity.Layer = layer_name

    def clear_output_layers(self) -> None:
        """Delete all Model Space and Paper Space entities on configured layers."""
        names = {name.casefold() for name in self.config.clear_layers}
        if not names:
            return
        for name in self.config.clear_layers:
            self._require_layer(name)
        # Layout blocks cover Model Space and all paper layouts without touching
        # reusable block definitions. Snapshot before deleting from COM collections.
        entities = [
            entity
            for layout in self.autocad.doc.Layouts
            for entity in layout.Block
            if entity.Layer.casefold() in names
        ]
        for entity in entities:
            entity.Delete()
