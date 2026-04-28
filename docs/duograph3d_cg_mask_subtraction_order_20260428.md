# ConceptGraphs-style mask subtraction order audit (2026-04-28)

## Question

ConceptGraphs subtracts small contained masks from larger masks, e.g. subtracting a pillow mask from a sofa mask. We checked whether DuoGraph3D currently does the same operation and whether the order matches ConceptGraphs.

## Code-path finding

- ConceptGraphs calls `mask_subtract_contained` after resizing and filtering detections, before creating object point clouds:
  - `/home/nebula/xxy/concept-graphs-main/conceptgraph/slam/utils.py:497-506`
  - `/home/nebula/xxy/concept-graphs-main/conceptgraph/utils/ious.py:453-496`
- DuoGraph3D's engineered parity runner already called the same function, but previously did so before confidence / size / large-bbox filtering.
- This branch now aligns the order with ConceptGraphs:
  - first filter by raw mask area, confidence, and bbox area;
  - then run `mask_subtract_contained` on the remaining masks;
  - then project the subtracted masks to 3D.

Changed files:

- `examples/run_conceptgraphs_engineered_parity.py`
- `examples/run_conceptgraphs_gt_layer_monitor.py`
- `tests/test_conceptgraphs_preprocess_order.py`

## room1 targeted result

Experiment artifact:

- `docs/official_results/duograph3d_cg_order_masksub_room1_20260428/`
- Supervised diagnosis:
  - `docs/official_results/duograph3d_cg_order_masksub_supervised_diag_room1_20260428/`
  - `docs/official_results/duograph3d_cg_order_masksub_gt_layer_room1_20260428/`

Against the previous memory-dense hybrid room1 result:

| setting | mIoU | mRecall | mPrecision | mF1 | F-mIoU |
| --- | ---: | ---: | ---: | ---: | ---: |
| previous subtract-before-filter | 21.607 | 40.648 | 22.389 | 24.965 | 36.058 |
| CG-aligned filter-then-subtract | 21.735 | 41.153 | 27.363 | 25.431 | 36.372 |
| delta | +0.128 | +0.506 | +4.974 | +0.465 | +0.314 |

The CG-aligned order substantially improves precision, but only slightly improves mIoU. This means the old order was a real engineering mismatch, but it is not the only dominant error source.

## Monitored preprocessing shift

room1 preparation changed from the earlier run as follows:

- kept observations: 8054 -> 8273
- geometry keys: 1073 -> 1106
- mask pixels subtracted: 201,243,028 -> 54,205,016
- post-subtract tiny masks: 176

The large drop in subtracted pixels is expected: after filtering first, low-confidence / too-large / too-small masks no longer participate in carving holes in other masks.

## Remaining failure pattern

The new room1 supervised diagnosis still says the main gap is precision / pollution rather than pure coverage:

- mRecall is above ConceptGraphs: +2.826
- mPrecision is still below ConceptGraphs: -5.267

Major remaining confusions:

- blanket -> comforter: 458,735 points
- pillow -> comforter: 386,976 points
- bed -> comforter: 313,660 points
- lamp -> nightstand / vent: 177,515 / 173,583 points

Ambiguous memory samples still show low-share multi-root assignments where GT class and predicted label disagree, e.g. bed/pillow keys assigned through comforter/pillow/vent roots.

## Interpretation

The mask subtraction order fix helps by reducing false positives from invalid masks carving valid masks before they themselves are filtered. However, room1 remains dominated by semantic aggregation and memory-assignment pollution: pillow/bed/blanket/rug regions are still frequently labeled as comforter, and lamp regions are still split between vent/nightstand.

Next discriminating probe should focus on class-aware label aggregation or per-key semantic calibration after geometry assignment, rather than more mask-subtraction changes alone.
