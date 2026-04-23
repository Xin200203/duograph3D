from __future__ import annotations

from dataclasses import replace
import random

from .contracts import FrameInput, Observation, TemporalVariant
from .events import BRANCH_DUOGRAPH3D
from .metrics import summarize_run
from .pipeline import DuoGraph3DPipeline


def ensure_temporal_bridge(frames: list[FrameInput], *, min_frames: int = 3) -> list[FrameInput]:
    if len(frames) >= min_frames:
        return [replace(frame, observations=list(frame.observations)) for frame in frames]
    if not frames:
        return []
    bridged = [replace(frame, observations=list(frame.observations)) for frame in frames]
    while len(bridged) < min_frames:
        insert_at = max(1, len(bridged) // 2)
        anchor = bridged[insert_at - 1]
        bridged.insert(insert_at, FrameInput(frame_id=f"{anchor.frame_id}:bridge{len(bridged)}", observations=[]))
    return bridged


def apply_observation_dropout(
    frames: list[FrameInput], *, drop_every: int = 0, offset: int = 1, keep_first_last: bool = True
) -> list[FrameInput]:
    if drop_every <= 0:
        return [replace(frame, observations=list(frame.observations)) for frame in frames]
    drop_indices: set[int] = set()
    for idx, _frame in enumerate(frames):
        should_drop = (idx + offset) % drop_every == 0
        if keep_first_last and idx in {0, len(frames) - 1}:
            should_drop = False
        if should_drop:
            drop_indices.add(idx)
    if not drop_indices and len(frames) >= 3:
        midpoint = len(frames) // 2
        if midpoint not in {0, len(frames) - 1}:
            drop_indices.add(midpoint)
    dropped: list[FrameInput] = []
    for idx, frame in enumerate(frames):
        observations = [] if idx in drop_indices else list(frame.observations)
        dropped.append(FrameInput(frame_id=frame.frame_id, observations=observations))
    return dropped


def apply_random_occlusion(
    frames: list[FrameInput], *, drop_probability: float = 0.35, seed: int = 0, keep_first_last: bool = True
) -> list[FrameInput]:
    rng = random.Random(seed)
    drop_indices: set[int] = set()
    for idx, _frame in enumerate(frames):
        if keep_first_last and idx in {0, len(frames) - 1}:
            continue
        if rng.random() < drop_probability:
            drop_indices.add(idx)
    if not drop_indices and len(frames) >= 3:
        midpoint = len(frames) // 2
        if midpoint not in {0, len(frames) - 1}:
            drop_indices.add(midpoint)
    dropped: list[FrameInput] = []
    for idx, frame in enumerate(frames):
        observations = [] if idx in drop_indices else list(frame.observations)
        dropped.append(FrameInput(frame_id=frame.frame_id, observations=observations))
    return dropped


def apply_burst_occlusion(
    frames: list[FrameInput], *, burst_size: int = 2, start_index: int = 1, keep_first_last: bool = True
) -> list[FrameInput]:
    if burst_size <= 0:
        return [replace(frame, observations=list(frame.observations)) for frame in frames]
    drop_indices: set[int] = set(range(start_index, min(start_index + burst_size, len(frames))))
    if keep_first_last:
        drop_indices.discard(0)
        drop_indices.discard(len(frames) - 1)
    if not drop_indices and len(frames) >= 4:
        mid = len(frames) // 2
        drop_indices.update({mid - 1, mid})
        drop_indices.discard(0)
        drop_indices.discard(len(frames) - 1)
    dropped: list[FrameInput] = []
    for idx, frame in enumerate(frames):
        observations = [] if idx in drop_indices else list(frame.observations)
        dropped.append(FrameInput(frame_id=frame.frame_id, observations=observations))
    return dropped


def apply_occlusion_regime(
    frames: list[FrameInput], *, mode: str = "alternate", drop_every: int = 0, drop_offset: int = 1, burst_size: int = 2, burst_start_index: int = 1, drop_probability: float = 0.35, random_seed: int = 0
) -> list[FrameInput]:
    prepared = ensure_temporal_bridge(frames) if mode != "none" else [replace(frame, observations=list(frame.observations)) for frame in frames]
    if mode == "none":
        return prepared
    if mode == "burst":
        return apply_burst_occlusion(prepared, burst_size=burst_size, start_index=burst_start_index)
    if mode == "random":
        return apply_random_occlusion(prepared, drop_probability=drop_probability, seed=random_seed)
    return apply_observation_dropout(prepared, drop_every=drop_every, offset=drop_offset)


def run_temporal_triplet(sequence_id: str, frames: list[FrameInput]) -> dict[str, dict[str, object]]:
    pipeline = DuoGraph3DPipeline()
    variants = {
        TemporalVariant.NONE.value: TemporalVariant.NONE,
        TemporalVariant.NAIVE_FRAMEWISE.value: TemporalVariant.NAIVE_FRAMEWISE,
        TemporalVariant.DEVA_STYLE.value: TemporalVariant.DEVA_STYLE,
    }
    report: dict[str, dict[str, object]] = {}
    for branch_name, variant in variants.items():
        result, logger = pipeline.run_sequence(
            sequence_id=sequence_id,
            frames=frames,
            temporal_variant=variant,
            branch_id=f"{BRANCH_DUOGRAPH3D}:{branch_name}",
        )
        report[branch_name] = summarize_run(result, logger)
    return report
