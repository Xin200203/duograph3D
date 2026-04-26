from __future__ import annotations

from dataclasses import replace

from .contracts import MemoryObjectNode, MemoryRelationEdge, ObjectStatus


class ObjectGraphMemory:
    def __init__(self) -> None:
        self.nodes: dict[str, MemoryObjectNode] = {}
        self.relation_edges: dict[tuple[str, str], MemoryRelationEdge] = {}
        self._next_id = 1

    def snapshot(self) -> dict[str, MemoryObjectNode]:
        return {key: replace(value) for key, value in self.nodes.items()}

    def relation_snapshot(self) -> dict[tuple[str, str], MemoryRelationEdge]:
        return {key: replace(value) for key, value in self.relation_edges.items()}

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

    @staticmethod
    def _relation_key(source_object_id: str, target_object_id: str) -> tuple[str, str]:
        return tuple(sorted((source_object_id, target_object_id)))

    def register_co_visibility(self, object_ids: list[str], *, step_id: int) -> None:
        unique_ids = sorted(set(object_ids))
        for index, source_object_id in enumerate(unique_ids):
            for target_object_id in unique_ids[index + 1:]:
                relation_key = self._relation_key(source_object_id, target_object_id)
                edge = self.relation_edges.get(
                    relation_key,
                    MemoryRelationEdge(
                        source_object_id=relation_key[0],
                        target_object_id=relation_key[1],
                    ),
                )
                edge.co_visibility_count += 1
                edge.last_seen_step = step_id
                edge.strength = round(min(edge.co_visibility_count / 5.0, 1.0), 3)
                self.relation_edges[relation_key] = edge

    def relation_bonus(self, source_object_id: str, target_object_id: str) -> float:
        edge = self.relation_edges.get(self._relation_key(source_object_id, target_object_id))
        return edge.strength if edge is not None else 0.0
