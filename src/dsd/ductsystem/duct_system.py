"""One duct system and its sheet-metal component tree."""

from dataclasses import dataclass
from typing import Iterator

from dsd.analyzers.models import SystemTopology
from dsd.system_type import SystemType

from .duct_fitting_tree import DuctFittingTree
from .duct_fitting_tree_builder import DuctFittingTreeBuilder
from .duct_system_config import DuctSystemConfig
from .sheet_metal_node import SheetMetalNode
from .sizing.duct_sizer import DuctSizer
from .sizing.duct_sizing import DuctSizingPass
from .sizing.fitting_sizer import FittingSizingPass
from .sizing.reducer_inserter import ReducerInserter


@dataclass
class DuctSystem:
    system_name: str
    dftree: DuctFittingTree
    config: DuctSystemConfig
    system_type: SystemType
    sizer: DuctSizer

    def __post_init__(self) -> None:
        if not isinstance(self.system_type, SystemType):
            raise ValueError("system_type must be a SystemType value")

    @classmethod
    def from_topology(
        cls, topology: SystemTopology, config: DuctSystemConfig, sizer: DuctSizer
    ) -> "DuctSystem":
        return cls(
            topology.system_name,
            DuctFittingTreeBuilder(config).build(topology),
            config,
            topology.system_type,
            sizer,
        )

    def level_order_traversal(self) -> Iterator[SheetMetalNode]:
        return self.dftree.level_order_traversal()

    def preorder_traversal(self) -> Iterator[SheetMetalNode]:
        return self.dftree.preorder_traversal()

    def size_ducts(self) -> None:
        DuctSizingPass(self.sizer).apply(self.dftree)

    def insert_reducers(self) -> None:
        ReducerInserter().apply(self.dftree)

    def size_fittings(self) -> None:
        FittingSizingPass(self.config.fittings).apply(self.dftree)

    def size(self) -> None:
        self.size_ducts()
        self.insert_reducers()
        self.size_fittings()
