from __future__ import annotations

from dataclasses import replace

from .contracts import MemoryObjectNode, ObjectStatus


class ObjectGraphMemory:
    def __init__(self) -> None:
        self.nodes: dict[str, MemoryObjectNode] = {}
        self._next_id = 1

    def snapshot(self) -> dict[str, MemoryObjectNode]:
        return {key: replace(value) for key, value in self.nodes.items()}

    def next_object_id(self) -> str:
        object_id = f"obj-{self._next_id}"
        self._next_id += 1
        return object_id

    def create_node(self, *, descriptor: str, geometry_key: str, step_id: int) -> MemoryObjectNode:
        object_id = self.next_object_id()
        node = MemoryObjectNode(
            object_id=object_id,
            descriptor_fused=descriptor,
            descriptor_recent=descriptor,
            geometry_key=geometry_key,
            birth_step=step_id,
            last_seen_step=step_id,
        )
        self.nodes[object_id] = node
        return node

    def candidate_nodes(self, geometry_key: str, candidate_budget: int) -> list[MemoryObjectNode]:
        eligible = [
            node
            for node in self.nodes.values()
            if node.status != ObjectStatus.RETIRED
            and (node.geometry_key == geometry_key or node.status in {ObjectStatus.ACTIVE, ObjectStatus.OCCLUDED, ObjectStatus.DORMANT})
        ]
        eligible.sort(key=lambda node: (node.status != ObjectStatus.ACTIVE, node.miss_count, -node.last_seen_step))
        return eligible[:candidate_budget]
