# DuoGraph3D × ConceptGraphs engineered parity run

- Protocol: DuoGraph3D over official ConceptGraphs Replica GSA detections with ConceptGraphs-inspired engineering filters/postprocess, evaluated with ConceptGraphs eval_replica_semseg n_exclude=6
- Pred exp name: `duograph3d_cg_order_masksub_room1_20260428`
- Scenes: room1
- Association diagnostics: enabled, top-k=2

## Aggregate metrics vs ConceptGraphs

| scene | ΔmIoU | DuoGraph3D mIoU | ConceptGraphs mIoU | ΔmRecall | ΔmPrecision | ΔF-mIoU |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| room1 | -2.742 | 21.735 | 24.477 | 2.826 | -5.267 | -6.585 |
| all | -2.797 | 21.735 | 24.531 | 0.938 | -8.817 | 0.134 |

## Monitor rollup

- raw detections / kept observations / track keys: 10649 / 8273 / 1106
- memory nodes / track fragmentation: 1100 / 1413
- exported objects after ConceptGraphs-style postprocess: 190
- export sources: `{'duograph3d_online_memory_dense_geometry': 1}`; fallback reasons: `{'forced_memory_dense': 1}`
- shadow under-merge candidate pairs: 3797
- low CLIP-margin observations: 6053; low valid-depth observations: 0
- birth reasons: `{'no_candidate': 1, 'best_candidate_below_threshold': 338, 'best_candidate_without_strong_identity': 761}`
- engineering filters: low-confidence masks=1742; large-bbox masks=591; mask pixels subtracted=54205016

## Per-scene merge monitors

| scene | source | fallback | keys | export objs | memory nodes | fragmentation | singleton-key rate | shadow pairs | no-candidate births | weak-identity births | p50 best score | eval mIoU | ΔmIoU |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| room1 | duograph3d_online_memory_dense_geometry | forced_memory_dense | 1106 | 190 | 1100 | 1413 | 0.344 | 3797 | 1 | 761 | 2.688 | 21.735 | -2.742 |

## Preliminary attribution

1. If `shadow pairs`, `singleton-key rate`, and `no_candidate` births are high while valid-depth failures are low, the gap is primarily an online merge/key-fragmentation issue rather than an input projection failure.
2. If low CLIP-margin counts concentrate in the worst-gap scenes, semantic ambiguity contributes to wrong object labels even under the same GSA detections.
3. If precision is above ConceptGraphs but recall/F-mIoU lag, DuoGraph3D is conservative/fragmented; if precision also lags, inspect over-merge or semantic confusion examples before tuning thresholds.
