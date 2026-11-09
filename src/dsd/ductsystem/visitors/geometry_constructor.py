"""Build placed fittings first, then connect ducts using their layout skeletons."""

from dataclasses import replace

from dsd.geometry.builders.rectangular.rectangular_geometric_representation_builder import (
    GeometryConstructionError,
    RectangularGeometricRepresentationBuilder,
)
from dsd.geometry.geometric_representation import GeometricRepresentation
from dsd.geometry.placement.placement_context import PlacementContext
from dsd.geometry.placement.placement_context_manager import PlacementContextManager

from ..models.rectangular import (
    RectangularDuct,
    RectangularElbow,
    RectangularEndcap,
    RectangularReducer,
    RectangularShoeTakeoff,
)
from ..models.sheet_metal_component import SheetMetalComponent
from .sheet_metal_component_visitor import SheetMetalComponentVisitor


class GeometryConstructorVisitor(SheetMetalComponentVisitor[GeometricRepresentation]):
    def __init__(
        self,
        context_manager: PlacementContextManager,
        builder: RectangularGeometricRepresentationBuilder,
    ) -> None:
        self.context_manager = context_manager
        self.builder = builder
        self.representations: dict[int, GeometricRepresentation] = {}

    def construct(self) -> dict[int, GeometricRepresentation]:
        nodes = list(self.context_manager.tree.preorder_traversal())
        self.representations.clear()
        for node in nodes:
            if not isinstance(node.component, RectangularDuct):
                node.component.accept(self)
        self.context_manager.set_fitting_layouts(self.representations)
        # Validate all duct connections before changing any component lengths.
        contexts = {
            node.component.id: self.context_manager.find_context(node.component)
            for node in nodes
            if isinstance(node.component, RectangularDuct)
        }
        for node in nodes:
            if isinstance(node.component, RectangularDuct):
                self._duct(node.component, contexts[node.component.id])
        return dict(self.representations)

    def _record(
        self, component: SheetMetalComponent, representation: GeometricRepresentation
    ) -> GeometricRepresentation:
        self.representations[component.id] = representation
        return representation

    def _duct(
        self, component: RectangularDuct, context: PlacementContext
    ) -> GeometricRepresentation:
        if context.length is None:
            raise GeometryConstructionError("Duct placement requires a final length")
        sized = replace(component, length=context.length)
        representation = self.builder.build_duct(sized, context)
        component.length = context.length
        return self._record(component, representation)

    def visit_rectangular_duct(
        self, component: RectangularDuct
    ) -> GeometricRepresentation:
        return self._duct(component, self.context_manager.find_context(component))

    def visit_rectangular_elbow(
        self, component: RectangularElbow
    ) -> GeometricRepresentation:
        return self._record(
            component,
            self.builder.build_elbow(
                component, self.context_manager.find_context(component)
            ),
        )

    def visit_rectangular_shoetakeoff(
        self, component: RectangularShoeTakeoff
    ) -> GeometricRepresentation:
        return self._record(
            component,
            self.builder.build_shoetakeoff(
                component, self.context_manager.find_context(component)
            ),
        )

    def visit_rectangular_reducer(
        self, component: RectangularReducer
    ) -> GeometricRepresentation:
        return self._record(
            component,
            self.builder.build_reducer(
                component, self.context_manager.find_context(component)
            ),
        )

    def visit_rectangular_endcap(
        self, component: RectangularEndcap
    ) -> GeometricRepresentation:
        return self._record(
            component,
            self.builder.build_endcap(
                component, self.context_manager.find_context(component)
            ),
        )
