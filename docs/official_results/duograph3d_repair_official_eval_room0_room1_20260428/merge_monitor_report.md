# DuoGraph3D × ConceptGraphs engineered parity run

- Protocol: DuoGraph3D over official ConceptGraphs Replica GSA detections with ConceptGraphs-inspired engineering filters/postprocess, evaluated with ConceptGraphs eval_replica_semseg n_exclude=6
- Pred exp name: `duograph3d_repair_official_eval_room0_room1_20260428`
- Scenes: room0, room1
- Association diagnostics: enabled, top-k=2

## Aggregate metrics vs ConceptGraphs

| scene | ΔmIoU | DuoGraph3D mIoU | ConceptGraphs mIoU | ΔmRecall | ΔmPrecision | ΔF-mIoU |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| room0 | -17.189 | 4.146 | 21.335 | -29.547 | -23.291 | -37.621 |
| room1 | -11.100 | 13.377 | 24.477 | -11.445 | -15.955 | -21.828 |
| all | -18.477 | 6.054 | 24.531 | -22.807 | -26.265 | -19.553 |

## Monitor rollup

- raw detections / kept observations / track keys: 28250 / 20889 / 2571
- memory nodes / track fragmentation: 102 / 1768
- exported objects after ConceptGraphs-style postprocess: 32
- shadow under-merge candidate pairs: 3500
- low CLIP-margin observations: 14785; low valid-depth observations: 0
- birth reasons: `{'no_candidate': 2, 'best_candidate_below_threshold': 100}`
- engineering filters: low-confidence masks=5410; large-bbox masks=997; mask pixels subtracted=402498573

## Per-scene merge monitors

| scene | keys | export objs | memory nodes | fragmentation | singleton-key rate | shadow pairs | no-candidate births | weak-identity births | p50 best score | eval mIoU | ΔmIoU |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| room0 | 1498 | 14 | 35 | 1054 | 0.317 | 1580 | 1 | 0 | 2.414 | 4.146 | -17.189 |
| room1 | 1073 | 18 | 67 | 714 | 0.349 | 1920 | 1 | 0 | 2.399 | 13.377 | -11.100 |

## Preliminary attribution

1. If `shadow pairs`, `singleton-key rate`, and `no_candidate` births are high while valid-depth failures are low, the gap is primarily an online merge/key-fragmentation issue rather than an input projection failure.
2. If low CLIP-margin counts concentrate in the worst-gap scenes, semantic ambiguity contributes to wrong object labels even under the same GSA detections.
3. If precision is above ConceptGraphs but recall/F-mIoU lag, DuoGraph3D is conservative/fragmented; if precision also lags, inspect over-merge or semantic confusion examples before tuning thresholds.
