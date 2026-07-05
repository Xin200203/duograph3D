# DuoGraph3D × ConceptGraphs engineered parity run

- Protocol: DuoGraph3D over official ConceptGraphs Replica GSA detections with ConceptGraphs-inspired engineering filters/postprocess, evaluated with ConceptGraphs eval_replica_semseg n_exclude=6
- Pred exp name: `duograph3d_layer2_fix_room1_20260429`
- Scenes: room1
- Association diagnostics: enabled, top-k=2

## Aggregate metrics vs ConceptGraphs

| scene | ΔmIoU | DuoGraph3D mIoU | ConceptGraphs mIoU | ΔmRecall | ΔmPrecision | ΔF-mIoU |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| room1 | -2.729 | 21.748 | 24.477 | 2.634 | -10.291 | -7.214 |
| all | -2.783 | 21.748 | 24.531 | 0.746 | -13.842 | -0.495 |

## Monitor rollup

- raw detections / kept observations / track keys: 10649 / 8273 / 1106
- memory nodes / track fragmentation: 401 / 1262
- exported objects after ConceptGraphs-style postprocess: 124
- export sources: `{'duograph3d_online_memory_dense_geometry': 1}`; fallback reasons: `{'forced_memory_dense': 1}`
- shadow under-merge candidate pairs: 3392
- low CLIP-margin observations: 6053; low valid-depth observations: 0
- birth reasons: `{'no_candidate': 1, 'best_candidate_below_threshold': 326, 'best_candidate_without_strong_identity': 74}`
- engineering filters: low-confidence masks=1742; large-bbox masks=591; mask pixels subtracted=54205016

## Per-scene merge monitors

| scene | source | fallback | keys | export objs | memory nodes | fragmentation | singleton-key rate | shadow pairs | no-candidate births | weak-identity births | p50 best score | eval mIoU | ΔmIoU |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| room1 | duograph3d_online_memory_dense_geometry | forced_memory_dense | 1106 | 124 | 401 | 1262 | 0.344 | 3392 | 1 | 74 | 2.866 | 21.748 | -2.729 |

## Preliminary attribution

1. If `shadow pairs`, `singleton-key rate`, and `no_candidate` births are high while valid-depth failures are low, the gap is primarily an online merge/key-fragmentation issue rather than an input projection failure.
2. If low CLIP-margin counts concentrate in the worst-gap scenes, semantic ambiguity contributes to wrong object labels even under the same GSA detections.
3. If precision is above ConceptGraphs but recall/F-mIoU lag, DuoGraph3D is conservative/fragmented; if precision also lags, inspect over-merge or semantic confusion examples before tuning thresholds.
