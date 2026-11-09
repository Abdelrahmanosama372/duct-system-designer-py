"""Rooted sheet-metal component tree with breadth-first traversal."""

from collections import deque
from dataclasses import dataclass
from typing import Iterator

from .sheet_metal_node import SheetMetalNode


@dataclass
class DuctFittingTree:
    root: SheetMetalNode

    def __post_init__(self) -> None:
        if self.root.parent is not None:
            raise ValueError("Tree root must not have a parent")

    def level_order_traversal(self) -> Iterator[SheetMetalNode]:
        return self._traverse(depth_first=False)

    def preorder_traversal(self) -> Iterator[SheetMetalNode]:
        return self._traverse(depth_first=True)

    def _traverse(self, depth_first: bool) -> Iterator[SheetMetalNode]:
        queue = deque([self.root])
        visited: set[int] = set()
        component_ids: set[int] = set()
        while queue:
            node = queue.pop() if depth_first else queue.popleft()
            if id(node) in visited:
                raise ValueError("Component tree contains a cycle or shared node")
            visited.add(id(node))
            if node.component.id in component_ids:
                raise ValueError("Component IDs must be unique within a system")
            component_ids.add(node.component.id)
            for child in node.children:
                if child.parent is not node:
                    raise ValueError("Child and parent links are inconsistent")
            yield node
            queue.extend(reversed(node.children) if depth_first else node.children)

    @property
    def connected_components(self) -> list[SheetMetalNode]:
        return list(self.level_order_traversal())
