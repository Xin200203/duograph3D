# DuoGraph3D coverage-preserving export repair — 2026-04-28

## Decision

Official Replica mIoU is a dense semantic-map metric, so the default ConceptGraphs-format export now keeps coverage first.  `--export-source auto` probes online memory export, but falls back to dense geometry-key export when memory objects are too sparse.

## Why this repair was needed

The previous repaired run exported online memory objects directly.  For room0+room1 that produced only 40 exported objects and all-scene mIoU 6.258.  The evaluator then had to assign the full SLAM point cloud from a tiny prediction set, causing coverage collapse.

## Implementation summary

- Added `src/duograph3d/export_policy.py` with explicit coverage gates.
- Updated `examples/run_conceptgraphs_engineered_parity.py`:
  - new `--export-source {auto,geometry,memory}` CLI;
  - default `auto` uses online memory only if object/key/point coverage passes;
  - otherwise exports dense geometry-key objects through ConceptGraphs denoise/filter/merge;
  - report now records selected source, fallback reason, memory/key ratios, and point coverage.
- Added `tests/test_export_policy.py` for the fallback/force behavior.

## Two-scene official mIoU evidence

Run: `docs/official_results/duograph3d_coverage_auto_min2_room0_room1_20260428/`

| scene | source | fallback | exported objects | mIoU | CG mIoU | ΔmIoU | F-mIoU | CG F-mIoU | ΔF-mIoU |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| room0 | geometry-key coverage | memory_object_count_below_coverage_floor | 423 | 25.248 | 21.335 | +3.913 | 46.195 | 50.035 | -3.840 |
| room1 | geometry-key coverage | memory_object_count_below_coverage_floor | 285 | 22.990 | 24.477 | -1.487 | 39.102 | 42.957 | -3.855 |
| all | geometry-key coverage | — | 708 | 19.012 | 24.531 | -5.519 | 42.415 | 36.238 | +6.177 |

Compared with the sparse-memory repaired official run (`docs/official_results/duograph3d_repair_official_eval_min2_room0_room1_20260428/`):

| metric | sparse memory export | coverage-preserving export | change |
| --- | ---: | ---: | ---: |
| room0 mIoU | 4.146 | 25.248 | +21.102 |
| room1 mIoU | 13.825 | 22.990 | +9.165 |
| all mIoU | 6.258 | 19.012 | +12.754 |
| exported objects | 40 | 708 | +668 |

## Remaining risk

This fixes the evaluation-surface regression and restores dense mIoU coverage, but it does not prove that online memory itself is sufficiently dense.  Current auto diagnostics still show memory export below coverage floor: room0 memory/key ratio 0.010, room1 0.023.  Future online-object work should improve memory coverage before forcing `--export-source memory` in official mIoU tables.
