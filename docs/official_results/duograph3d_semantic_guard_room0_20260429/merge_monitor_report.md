# DuoGraph3D × ConceptGraphs engineered parity run

- Protocol: DuoGraph3D over official ConceptGraphs Replica GSA detections with ConceptGraphs-inspired engineering filters/postprocess, evaluated with ConceptGraphs eval_replica_semseg n_exclude=6
- Pred exp name: `duograph3d_semantic_guard_room0_20260429`
- Scenes: room0
- Association diagnostics: enabled, top-k=2

## Aggregate metrics vs ConceptGraphs

| scene | ΔmIoU | DuoGraph3D mIoU | ConceptGraphs mIoU | ΔmRecall | ΔmPrecision | ΔF-mIoU |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| room0 | -1.908 | 19.427 | 21.335 | -3.051 | 2.014 | -9.044 |
| all | -5.105 | 19.427 | 24.531 | -4.932 | -4.733 | 4.753 |

## Monitor rollup

- raw detections / kept observations / track keys: 17601 / 13154 / 1514
- memory nodes / track fragmentation: 717 / 1606
- exported objects after ConceptGraphs-style postprocess: 303
- export sources: `{'duograph3d_online_memory_dense_geometry': 1}`; fallback reasons: `{'forced_memory_dense': 1}`
- shadow under-merge candidate pairs: 3020
- low CLIP-margin observations: 9149; low valid-depth observations: 0
- birth reasons: `{'no_candidate': 1, 'best_candidate_below_threshold': 537, 'best_candidate_without_strong_identity': 179}`
- engineering filters: low-confidence masks=3935; large-bbox masks=408; mask pixels subtracted=101077479

## Per-scene merge monitors

| scene | source | fallback | keys | export objs | memory nodes | fragmentation | singleton-key rate | shadow pairs | no-candidate births | weak-identity births | p50 best score | eval mIoU | ΔmIoU |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| room0 | duograph3d_online_memory_dense_geometry | forced_memory_dense | 1514 | 303 | 717 | 1606 | 0.322 | 3020 | 1 | 179 | 2.929 | 19.427 | -1.908 |

## Preliminary attribution

1. If `shadow pairs`, `singleton-key rate`, and `no_candidate` births are high while valid-depth failures are low, the gap is primarily an online merge/key-fragmentation issue rather than an input projection failure.
2. If low CLIP-margin counts concentrate in the worst-gap scenes, semantic ambiguity contributes to wrong object labels even under the same GSA detections.
3. If precision is above ConceptGraphs but recall/F-mIoU lag, DuoGraph3D is conservative/fragmented; if precision also lags, inspect over-merge or semantic confusion examples before tuning thresholds.
