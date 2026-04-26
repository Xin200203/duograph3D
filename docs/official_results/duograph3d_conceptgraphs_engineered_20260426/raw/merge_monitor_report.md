# DuoGraph3D × ConceptGraphs engineered parity run

- Protocol: DuoGraph3D over official ConceptGraphs Replica GSA detections with ConceptGraphs-inspired engineering filters/postprocess, evaluated with ConceptGraphs eval_replica_semseg n_exclude=6
- Pred exp name: `duograph3d_gsa_engineered_monitor`
- Scenes: room0, room1, room2, office0, office1, office2, office3, office4
- Association diagnostics: enabled, top-k=2

## Aggregate metrics vs ConceptGraphs

| scene | ΔmIoU | DuoGraph3D mIoU | ConceptGraphs mIoU | ΔmRecall | ΔmPrecision | ΔF-mIoU |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| room0 | 3.915 | 25.250 | 21.335 | 1.433 | 11.352 | -4.976 |
| room1 | -1.490 | 22.986 | 24.477 | 4.638 | -6.392 | -3.877 |
| room2 | -2.355 | 24.615 | 26.970 | 0.615 | 3.076 | 2.209 |
| office0 | -2.371 | 17.677 | 20.048 | -8.229 | 1.874 | -3.653 |
| office1 | -2.074 | 12.407 | 14.481 | 4.528 | 0.498 | -1.701 |
| office2 | -5.454 | 16.436 | 21.890 | -5.739 | 0.586 | -2.735 |
| office3 | -4.037 | 17.640 | 21.677 | -4.392 | -3.842 | -1.796 |
| office4 | -3.000 | 43.829 | 46.829 | -1.962 | -0.915 | -10.081 |
| all | -3.965 | 20.566 | 24.531 | -0.740 | 0.958 | -2.834 |

## Monitor rollup

- raw detections / kept observations / track keys: 109799 / 80054 / 9931
- memory nodes / track fragmentation: 72329 / 62398
- exported objects after ConceptGraphs-style postprocess: 2308
- shadow under-merge candidate pairs: 49220
- low CLIP-margin observations: 63492; low valid-depth observations: 392
- birth reasons: `{'no_candidate': 61977, 'best_candidate_without_strong_identity': 10352}`
- engineering filters: low-confidence masks=22189; large-bbox masks=2993; mask pixels subtracted=1422079698

## Per-scene merge monitors

| scene | keys | export objs | memory nodes | fragmentation | singleton-key rate | shadow pairs | no-candidate births | weak-identity births | p50 best score | eval mIoU | ΔmIoU |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| room0 | 1498 | 306 | 11871 | 10373 | 0.317 | 8856 | 10607 | 1264 | 1.414 | 25.250 | 3.915 |
| room1 | 1073 | 208 | 7078 | 6005 | 0.349 | 7169 | 5825 | 1253 | 1.378 | 22.986 | -1.490 |
| room2 | 1164 | 256 | 7371 | 6207 | 0.326 | 7345 | 6008 | 1363 | 1.347 | 24.615 | -2.355 |
| office0 | 1155 | 267 | 9735 | 8580 | 0.250 | 6063 | 8402 | 1333 | 1.370 | 17.677 | -2.371 |
| office1 | 634 | 154 | 5875 | 5241 | 0.235 | 2489 | 4751 | 1124 | 1.526 | 12.407 | -2.074 |
| office2 | 1209 | 328 | 9864 | 8655 | 0.296 | 4513 | 8540 | 1324 | 1.363 | 16.436 | -5.454 |
| office3 | 1582 | 403 | 11415 | 9833 | 0.335 | 7501 | 10138 | 1277 | 1.400 | 17.640 | -4.037 |
| office4 | 1616 | 386 | 9120 | 7504 | 0.356 | 5284 | 7706 | 1414 | 1.339 | 43.829 | -3.000 |

## Preliminary attribution

1. If `shadow pairs`, `singleton-key rate`, and `no_candidate` births are high while valid-depth failures are low, the gap is primarily an online merge/key-fragmentation issue rather than an input projection failure.
2. If low CLIP-margin counts concentrate in the worst-gap scenes, semantic ambiguity contributes to wrong object labels even under the same GSA detections.
3. If precision is above ConceptGraphs but recall/F-mIoU lag, DuoGraph3D is conservative/fragmented; if precision also lags, inspect over-merge or semantic confusion examples before tuning thresholds.
