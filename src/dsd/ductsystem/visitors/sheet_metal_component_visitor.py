"""Typed visitor contract for the supported sheet-metal components."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Generic, TypeVar

if TYPE_CHECKING:
    from ..models.rectangular import (
        RectangularDuct,
        RectangularElbow,
        RectangularEndcap,
        RectangularReducer,
        RectangularShoeTakeoff,
    )
    from ..models.sheet_metal_component import SheetMetalComponent

ResultT = TypeVar("ResultT")


class SheetMetalComponentVisitor(ABC, Generic[ResultT]):
    def visit(self, component: SheetMetalComponent) -> ResultT:
        return component.accept(self)

    @abstractmethod
    def visit_rectangular_duct(self, component: RectangularDuct) -> ResultT:
        pass

    @abstractmethod
    def visit_rectangular_elbow(self, component: RectangularElbow) -> ResultT:
        pass

    @abstractmethod
    def visit_rectangular_shoetakeoff(
        self, component: RectangularShoeTakeoff
    ) -> ResultT:
        pass

    @abstractmethod
    def visit_rectangular_reducer(self, component: RectangularReducer) -> ResultT:
        pass

    @abstractmethod
    def visit_rectangular_endcap(self, component: RectangularEndcap) -> ResultT:
        pass
