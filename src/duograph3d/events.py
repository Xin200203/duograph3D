from __future__ import annotations

from dataclasses import dataclass, field


BRANCH_DUOGRAPH3D = "duograph3d_full"
BRANCH_SINGLE_LAYER = "single_layer_rival"
BRANCH_DENSE_EXPORT = "dense_authority_export_rival"
BRANCH_COUNTERFACTUAL = "full_fair_counterfactual"


@dataclass
class EventRecord:
    sequence_id: str
    step_id: int
    branch_id: str
    event_type: str
    owner_component: str
    payload: dict[str, object] = field(default_factory=dict)


class EventLogger:
    def __init__(self) -> None:
        self.records: list[EventRecord] = []

    def log(
        self,
        *,
        sequence_id: str,
        step_id: int,
        branch_id: str,
        event_type: str,
        owner_component: str,
        **payload: object,
    ) -> None:
        self.records.append(
            EventRecord(
                sequence_id=sequence_id,
                step_id=step_id,
                branch_id=branch_id,
                event_type=event_type,
                owner_component=owner_component,
                payload=payload,
            )
        )

    def count(self, event_type: str, branch_id: str | None = None) -> int:
        return sum(
            1
            for record in self.records
            if record.event_type == event_type and (branch_id is None or record.branch_id == branch_id)
        )

    def filter(self, event_type: str | None = None, branch_id: str | None = None) -> list[EventRecord]:
        return [
            record
            for record in self.records
            if (event_type is None or record.event_type == event_type)
            and (branch_id is None or record.branch_id == branch_id)
        ]
