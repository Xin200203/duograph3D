# DuoGraph3D × ConceptGraphs engineered parity run

- Protocol: DuoGraph3D over official ConceptGraphs Replica GSA detections with ConceptGraphs-inspired engineering filters/postprocess, evaluated with ConceptGraphs eval_replica_semseg n_exclude=6
- Pred exp name: `duograph3d_memory_dense_hybrid_room0_room1_20260428`
- Scenes: room0, room1
- Association diagnostics: enabled, top-k=2

## Aggregate metrics vs ConceptGraphs

| scene | ΔmIoU | DuoGraph3D mIoU | ConceptGraphs mIoU | ΔmRecall | ΔmPrecision | ΔF-mIoU |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| room0 | 2.426 | 23.761 | 21.335 | -1.484 | 11.780 | -1.549 |
| room1 | -2.870 | 21.607 | 24.477 | 2.321 | -10.240 | -6.899 |
| all | -6.345 | 18.186 | 24.531 | -4.359 | -2.471 | 5.811 |

## Monitor rollup

- raw detections / kept observations / track keys: 28250 / 20889 / 2571
- memory nodes / track fragmentation: 2742 / 3208
- exported objects after ConceptGraphs-style postprocess: 471
- export sources: `{'duograph3d_online_memory_dense_geometry': 2}`; fallback reasons: `{'forced_memory_dense': 2}`
- shadow under-merge candidate pairs: 6875
- low CLIP-margin observations: 14785; low valid-depth observations: 0
- birth reasons: `{'no_candidate': 2, 'best_candidate_below_threshold': 899, 'best_candidate_without_strong_identity': 1841}`
- engineering filters: low-confidence masks=5410; large-bbox masks=997; mask pixels subtracted=402498573

## Per-scene merge monitors

| scene | source | fallback | keys | export objs | memory nodes | fragmentation | singleton-key rate | shadow pairs | no-candidate births | weak-identity births | p50 best score | eval mIoU | ΔmIoU |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| room0 | duograph3d_online_memory_dense_geometry | forced_memory_dense | 1498 | 285 | 1727 | 1969 | 0.317 | 3526 | 1 | 1152 | 2.834 | 23.761 | 2.426 |
| room1 | duograph3d_online_memory_dense_geometry | forced_memory_dense | 1073 | 186 | 1015 | 1239 | 0.349 | 3349 | 1 | 689 | 2.691 | 21.607 | -2.870 |

## Preliminary attribution

1. If `shadow pairs`, `singleton-key rate`, and `no_candidate` births are high while valid-depth failures are low, the gap is primarily an online merge/key-fragmentation issue rather than an input projection failure.
2. If low CLIP-margin counts concentrate in the worst-gap scenes, semantic ambiguity contributes to wrong object labels even under the same GSA detections.
3. If precision is above ConceptGraphs but recall/F-mIoU lag, DuoGraph3D is conservative/fragmented; if precision also lags, inspect over-merge or semantic confusion examples before tuning thresholds.
