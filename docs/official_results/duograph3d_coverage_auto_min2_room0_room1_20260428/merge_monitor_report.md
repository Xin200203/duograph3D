# DuoGraph3D × ConceptGraphs engineered parity run

- Protocol: DuoGraph3D over official ConceptGraphs Replica GSA detections with ConceptGraphs-inspired engineering filters/postprocess, evaluated with ConceptGraphs eval_replica_semseg n_exclude=6
- Pred exp name: `duograph3d_coverage_auto_min2_room0_room1_20260428`
- Scenes: room0, room1
- Association diagnostics: enabled, top-k=2

## Aggregate metrics vs ConceptGraphs

| scene | ΔmIoU | DuoGraph3D mIoU | ConceptGraphs mIoU | ΔmRecall | ΔmPrecision | ΔF-mIoU |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| room0 | 3.913 | 25.248 | 21.335 | 1.383 | 14.763 | -3.840 |
| room1 | -1.487 | 22.990 | 24.477 | 4.460 | -6.750 | -3.855 |
| all | -5.519 | 19.012 | 24.531 | -1.854 | 2.565 | 6.177 |

## Monitor rollup

- raw detections / kept observations / track keys: 28250 / 20889 / 2571
- memory nodes / track fragmentation: 102 / 1768
- exported objects after ConceptGraphs-style postprocess: 708
- export sources: `{'duograph3d_geometry_key_coverage': 2}`; fallback reasons: `{'memory_object_count_below_coverage_floor': 2}`
- shadow under-merge candidate pairs: 3500
- low CLIP-margin observations: 14785; low valid-depth observations: 0
- birth reasons: `{'no_candidate': 2, 'best_candidate_below_threshold': 100}`
- engineering filters: low-confidence masks=5410; large-bbox masks=997; mask pixels subtracted=402498573

## Per-scene merge monitors

| scene | source | fallback | keys | export objs | memory nodes | fragmentation | singleton-key rate | shadow pairs | no-candidate births | weak-identity births | p50 best score | eval mIoU | ΔmIoU |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| room0 | duograph3d_geometry_key_coverage | memory_object_count_below_coverage_floor | 1498 | 423 | 35 | 1054 | 0.317 | 1580 | 1 | 0 | 2.414 | 25.248 | 3.913 |
| room1 | duograph3d_geometry_key_coverage | memory_object_count_below_coverage_floor | 1073 | 285 | 67 | 714 | 0.349 | 1920 | 1 | 0 | 2.399 | 22.990 | -1.487 |

## Preliminary attribution

1. If `shadow pairs`, `singleton-key rate`, and `no_candidate` births are high while valid-depth failures are low, the gap is primarily an online merge/key-fragmentation issue rather than an input projection failure.
2. If low CLIP-margin counts concentrate in the worst-gap scenes, semantic ambiguity contributes to wrong object labels even under the same GSA detections.
3. If precision is above ConceptGraphs but recall/F-mIoU lag, DuoGraph3D is conservative/fragmented; if precision also lags, inspect over-merge or semantic confusion examples before tuning thresholds.
