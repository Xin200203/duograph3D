"""Experiment metadata and unified log schema (v2).

Provides ``ExperimentRunMetadata`` for reproducible experiment tracking and
``export_event_stream_jsonl`` for structured log export.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
import json
import time

from .events import EventLogger, EventRecord


LOG_SCHEMA_VERSION = "v2"


@dataclass
class ExperimentRunMetadata:
    """Single-experiment metadata for reproducible tracking.

    Every experiment run writes this alongside its event stream so downstream
    analysis tools can reconstruct the exact configuration and code version.
    """

    run_id: str
    branch_id: str
    scene_id: str
    temporal_variant: str
    config_snapshot: dict[str, object] = field(default_factory=dict)
    seed: int = 0
    timestamp: str = ""
    git_commit: str = ""
    log_schema_version: str = LOG_SCHEMA_VERSION
    custom_tags: dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def config_to_snapshot(config) -> dict[str, object]:
    """Convert a PipelineConfig to a JSON-serializable snapshot."""
    snapshot = {}
    for field_name in config.__dataclass_fields__:
        value = getattr(config, field_name)
        if isinstance(value, (int, float, str, bool, type(None))):
            snapshot[field_name] = value
        elif isinstance(value, (list, tuple)):
            snapshot[field_name] = [v if isinstance(v, (int, float, str, bool, type(None))) else str(v) for v in value]
        else:
            snapshot[field_name] = str(value)
    return snapshot


def export_event_stream_jsonl(
    logger: EventLogger,
    output_path: str | Path,
    *,
    metadata: ExperimentRunMetadata | None = None,
) -> Path:
    """Export the full event stream as newline-delimited JSON (JSONL).

    Each line is a JSON object with metadata fields merged for self-contained
    analysis.

    Returns the output path.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    meta_dict = asdict(metadata) if metadata else {}
    with output_path.open("w") as handle:
        for record in logger.records:
            row = {
                "schema_version": LOG_SCHEMA_VERSION,
                "sequence_id": record.sequence_id,
                "step_id": record.step_id,
                "branch_id": record.branch_id,
                "event_type": record.event_type,
                "owner_component": record.owner_component,
                **record.payload,
            }
            if metadata:
                row.update(
                    {
                        "run_id": meta_dict.get("run_id", ""),
                        "scene_id": meta_dict.get("scene_id", ""),
                        "temporal_variant": meta_dict.get("temporal_variant", ""),
                        "seed": meta_dict.get("seed", 0),
                        "timestamp": meta_dict.get("timestamp", ""),
                    }
                )
            handle.write(json.dumps(row, default=str) + "\n")

    return output_path


def load_event_stream(path: str | Path) -> list[dict[str, object]]:
    """Load a JSONL event stream into a list of dicts."""
    records = []
    with Path(path).open("r") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def count_event_types(records: list[dict[str, object]]) -> dict[str, int]:
    """Count occurrences of each event type."""
    counts: dict[str, int] = {}
    for record in records:
        event_type = str(record.get("event_type", "unknown"))
        counts[event_type] = counts.get(event_type, 0) + 1
    return counts


def filter_records(
    records: list[dict[str, object]],
    *,
    event_type: str | None = None,
    step_id: int | None = None,
    owner_component: str | None = None,
) -> list[dict[str, object]]:
    """Filter loaded event stream records."""
    result = records
    if event_type is not None:
        result = [r for r in result if r.get("event_type") == event_type]
    if step_id is not None:
        result = [r for r in result if r.get("step_id") == step_id]
    if owner_component is not None:
        result = [r for r in result if r.get("owner_component") == owner_component]
    return result
