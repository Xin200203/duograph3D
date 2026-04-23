from __future__ import annotations

import hashlib
import json
import shutil
import struct
import zlib
from pathlib import Path

from .data import ReplicaSequence, _sample_evenly


def _jpeg_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        data = handle.read()
    if not data.startswith(b"\xff\xd8"):
        raise ValueError(f"not a jpeg: {path}")
    index = 2
    while index < len(data):
        while index < len(data) and data[index] != 0xFF:
            index += 1
        while index < len(data) and data[index] == 0xFF:
            index += 1
        if index >= len(data):
            break
        marker = data[index]
        index += 1
        if marker in {0xD8, 0xD9}:
            continue
        if index + 2 > len(data):
            break
        segment_length = struct.unpack(">H", data[index:index + 2])[0]
        index += 2
        if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC9, 0xCA, 0xCB}:
            if index + 5 > len(data):
                break
            _precision = data[index]
            height = struct.unpack(">H", data[index + 1:index + 3])[0]
            width = struct.unpack(">H", data[index + 3:index + 5])[0]
            return width, height
        index += max(segment_length - 2, 0)
    raise ValueError(f"jpeg size not found: {path}")


def _safe_contract_canvas(path: Path, *, allow_placeholder_canvas: bool) -> tuple[int, int]:
    try:
        return _jpeg_size(path)
    except ValueError:
        if not allow_placeholder_canvas:
            raise
        return 64, 64


def _png_chunk(chunk_type: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(payload)) + chunk_type + payload + struct.pack(">I", zlib.crc32(chunk_type + payload) & 0xFFFFFFFF)


def _write_palette_png(path: Path, width: int, height: int, pixels: bytes, palette: list[tuple[int, int, int]]) -> None:
    rows = []
    row_length = width
    for row in range(height):
        start = row * row_length
        rows.append(b"\x00" + pixels[start:start + row_length])
    raw = b"".join(rows)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 3, 0, 0, 0)
    plte = b"".join(bytes((r, g, b)) for r, g, b in palette)
    png = b"\x89PNG\r\n\x1a\n"
    png += _png_chunk(b"IHDR", ihdr)
    png += _png_chunk(b"PLTE", plte)
    png += _png_chunk(b"IDAT", zlib.compress(raw))
    png += _png_chunk(b"IEND", b"")
    path.write_bytes(png)


def _stable_ratio(*parts: str) -> float:
    text = "|".join(parts).encode("utf-8")
    digest = hashlib.md5(text).digest()
    return int.from_bytes(digest[:4], "big") / 0xFFFFFFFF


def _clamp(value: int, lower: int, upper: int) -> int:
    return max(lower, min(value, upper))


def _observation_bbox(observation, width: int, height: int, ordinal: int) -> tuple[int, int, int, int]:
    support = observation.support
    support_size = support.support_size if support else 0.1
    depth_scale = support.depth_scale if support else 1.0
    geometry_support = support.geometry_support if support else 0.5
    continuity_key = support.continuity_key if support else observation.observation_id
    appearance_key = support.appearance_key if support else observation.descriptor
    pose_token = support.pose_token if support else ""

    area_ratio = min(max(support_size / 3.5, 0.06), 0.28)
    aspect_ratio = min(max(depth_scale / max(geometry_support, 0.2), 0.6), 1.8)
    box_area = max(int(width * height * area_ratio), 4)
    box_width = max(int((box_area * aspect_ratio) ** 0.5), 2)
    box_height = max(int(box_area / max(box_width, 1)), 2)
    box_width = min(box_width, width)
    box_height = min(box_height, height)

    x_ratio = _stable_ratio(continuity_key, appearance_key, str(ordinal))
    y_ratio = _stable_ratio(pose_token, continuity_key, str(ordinal + 7))
    max_x0 = max(width - box_width, 0)
    max_y0 = max(height - box_height, 0)
    x0 = _clamp(int(x_ratio * max_x0), 0, max_x0)
    y0 = _clamp(int(y_ratio * max_y0), 0, max_y0)
    return x0, y0, x0 + box_width, y0 + box_height


def export_replica_deva_contract(
    scene_root: str | Path,
    output_root: str | Path,
    *,
    limit: int = 6,
    allow_placeholder_canvas: bool = False,
) -> dict[str, object]:
    sequence = ReplicaSequence.from_root(scene_root)
    output_root = Path(output_root)
    image_dir = output_root / "img_path" / sequence.scene_name
    mask_dir = output_root / "mask_path" / sequence.scene_name
    image_dir.mkdir(parents=True, exist_ok=True)
    mask_dir.mkdir(parents=True, exist_ok=True)

    pairs = sequence.paired_frames()
    selected_pairs = _sample_evenly(pairs, limit)
    frame_inputs = sequence.to_frame_inputs(limit=limit)
    if len(selected_pairs) != len(frame_inputs):
        raise ValueError(
            f"selected pair count ({len(selected_pairs)}) does not match frame input count ({len(frame_inputs)}) for {sequence.scene_name}"
        )

    exported_frames = 0
    total_objects = 0
    placeholder_canvas_frames = 0
    total_mask_pixels = 0
    for pair, frame in zip(selected_pairs, frame_inputs):
        shutil.copy2(pair.rgb_path, image_dir / pair.rgb_path.name)
        try:
            width, height = _jpeg_size(pair.rgb_path)
        except ValueError:
            width, height = _safe_contract_canvas(
                pair.rgb_path,
                allow_placeholder_canvas=allow_placeholder_canvas,
            )
            placeholder_canvas_frames += 1
        observations = list(frame.observations) if frame else []
        total_objects += len(observations)

        pixels = bytearray(width * height)
        segments = []
        for index, observation in enumerate(observations, start=1):
            x0, y0, x1, y1 = _observation_bbox(observation, width, height, index)
            for y in range(y0, y1):
                base = y * width
                for x in range(x0, x1):
                    pixels[base + x] = index
            mask_area = max((x1 - x0) * (y1 - y0), 0)
            total_mask_pixels += mask_area
            segments.append(
                {
                    "id": index,
                    "isthing": True,
                    "category_id": index,
                    "score": round(observation.confidence, 3),
                    "label": observation.descriptor,
                    "bbox": [x0, y0, x1, y1],
                    "mask_area": mask_area,
                    "support_size": round(observation.support.support_size, 3) if observation.support else 0.0,
                    "depth_scale": round(observation.support.depth_scale, 3) if observation.support else 1.0,
                    "geometry_support": round(observation.support.geometry_support, 3) if observation.support else 0.0,
                }
            )
        palette = [(0, 0, 0)] + [((index * 53) % 255, (index * 97) % 255, (index * 193) % 255) for index in range(1, max(len(observations), 1) + 1)]
        png_path = mask_dir / f"{pair.rgb_path.stem}.png"
        json_path = mask_dir / f"{pair.rgb_path.stem}.json"
        _write_palette_png(png_path, width, height, bytes(pixels), palette)
        json_path.write_text(json.dumps(segments, indent=2) + "\n")
        exported_frames += 1

    return {
        "scene": sequence.scene_name,
        "exported_frames": exported_frames,
        "total_objects": total_objects,
        "image_dir": str(image_dir),
        "mask_dir": str(mask_dir),
        "mode": "contract_scaffold",
        "placeholder_canvas_frames": placeholder_canvas_frames,
        "avg_mask_pixels_per_frame": round(total_mask_pixels / max(exported_frames, 1), 2),
    }


def export_replica_deva_contract_batch(
    scene_roots: list[str | Path],
    output_root: str | Path,
    *,
    limit: int = 6,
    allow_placeholder_canvas: bool = False,
) -> dict[str, object]:
    output_root = Path(output_root)
    scenes = []
    total_frames = 0
    total_objects = 0
    total_placeholder_frames = 0
    avg_mask_pixels_per_frame = 0.0
    for scene_root in scene_roots:
        summary = export_replica_deva_contract(
            scene_root,
            output_root,
            limit=limit,
            allow_placeholder_canvas=allow_placeholder_canvas,
        )
        scenes.append(summary)
        total_frames += int(summary["exported_frames"])
        total_objects += int(summary["total_objects"])
        total_placeholder_frames += int(summary["placeholder_canvas_frames"])
        avg_mask_pixels_per_frame += float(summary["avg_mask_pixels_per_frame"])
    return {
        "scene_count": len(scenes),
        "total_frames": total_frames,
        "total_objects": total_objects,
        "total_placeholder_canvas_frames": total_placeholder_frames,
        "avg_mask_pixels_per_scene_frame": round(avg_mask_pixels_per_frame / max(len(scenes), 1), 2),
        "scenes": scenes,
    }
