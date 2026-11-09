import pytest

from dsd.ductsystem.models.rectangular import (
    RectangularDuct,
    RectangularElbow,
    RectangularEndcap,
    RectangularReducer,
    RectangularShoeTakeoff,
)
from dsd.ductsystem.visitors import SheetMetalComponentVisitor


class ComponentNameVisitor(SheetMetalComponentVisitor[str]):
    def visit_rectangular_duct(self, component):
        return "duct"

    def visit_rectangular_elbow(self, component):
        return "elbow"

    def visit_rectangular_shoetakeoff(self, component):
        return "shoe"

    def visit_rectangular_reducer(self, component):
        return "reducer"

    def visit_rectangular_endcap(self, component):
        return "endcap"


@pytest.mark.parametrize(
    "kind,kwargs,expected",
    [
        (RectangularDuct, {}, "duct"),
        (RectangularElbow, {"angle": 1}, "elbow"),
        (RectangularShoeTakeoff, {"side": "left"}, "shoe"),
        (RectangularReducer, {}, "reducer"),
        (RectangularEndcap, {}, "endcap"),
    ],
)
def test_components_dispatch_to_their_specific_visitor_method(
    properties, kind, kwargs, expected
):
    component = kind(**properties, **kwargs)
    visitor = ComponentNameVisitor()
    assert component.accept(visitor) == expected
    assert visitor.visit(component) == expected
