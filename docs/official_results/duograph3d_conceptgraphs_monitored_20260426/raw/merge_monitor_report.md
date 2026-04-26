# DuoGraph3D × ConceptGraphs parity monitored run

- Protocol: DuoGraph3D over official ConceptGraphs Replica GSA detections, evaluated with ConceptGraphs eval_replica_semseg n_exclude=6, plus online-merge monitoring
- Pred exp name: `duograph3d_gsa_parity_monitor`
- Scenes: room0, room1, room2, office0, office1, office2, office3, office4
- Association diagnostics: enabled, top-k=2

## Aggregate metrics vs ConceptGraphs

| scene | ΔmIoU | DuoGraph3D mIoU | ConceptGraphs mIoU | ΔmRecall | ΔmPrecision | ΔF-mIoU |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| room0 | 0.158 | 21.493 | 21.335 | 1.566 | 9.605 | -3.772 |
| room1 | 2.454 | 26.930 | 24.477 | 9.486 | 15.641 | -2.316 |
| room2 | -3.767 | 23.203 | 26.970 | -0.435 | 9.161 | 4.832 |
| office0 | -3.588 | 16.460 | 20.048 | -5.850 | 8.169 | -3.599 |
| office1 | -4.423 | 10.058 | 14.481 | 0.714 | 12.009 | -1.727 |
| office2 | -1.395 | 20.495 | 21.890 | 2.283 | 8.926 | -1.887 |
| office3 | -11.884 | 9.794 | 21.677 | 1.343 | -3.098 | -11.062 |
| office4 | -10.295 | 36.534 | 46.829 | -6.223 | -4.741 | -10.126 |
| all | -4.441 | 20.091 | 24.531 | -0.932 | 7.466 | -2.649 |

## Monitor rollup

- raw detections / kept observations / track keys: 109799 / 108992 / 9116
- memory nodes / track fragmentation: 85144 / 76028
- shadow under-merge candidate pairs: 14428
- low CLIP-margin observations: 87323; low valid-depth observations: 489
- birth reasons: `{'no_candidate': 75022, 'best_candidate_without_strong_identity': 10122}`

## Per-scene merge monitors

| scene | keys | memory nodes | fragmentation | singleton-key rate | shadow pairs | no-candidate births | weak-identity births | p50 best score | eval mIoU | ΔmIoU |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| room0 | 1279 | 13695 | 12416 | 0.273 | 1833 | 12492 | 1203 | 1.364 | 21.493 | 0.158 |
| room1 | 748 | 7936 | 7188 | 0.318 | 1118 | 6773 | 1163 | 1.363 | 26.930 | 2.454 |
| room2 | 1034 | 8674 | 7640 | 0.332 | 1645 | 7363 | 1311 | 0.794 | 23.203 | -3.767 |
| office0 | 1012 | 11387 | 10375 | 0.246 | 1810 | 10072 | 1315 | 1.236 | 16.460 | -3.588 |
| office1 | 651 | 6802 | 6151 | 0.246 | 1182 | 5682 | 1120 | 1.409 | 10.058 | -4.423 |
| office2 | 1252 | 11620 | 10368 | 0.281 | 2000 | 10304 | 1316 | 1.148 | 20.495 | -1.395 |
| office3 | 1562 | 13778 | 12216 | 0.300 | 2511 | 12418 | 1360 | 1.240 | 9.794 | -11.884 |
| office4 | 1578 | 11252 | 9674 | 0.322 | 2329 | 9918 | 1334 | 1.253 | 36.534 | -10.295 |

## Preliminary attribution

1. If `shadow pairs`, `singleton-key rate`, and `no_candidate` births are high while valid-depth failures are low, the gap is primarily an online merge/key-fragmentation issue rather than an input projection failure.
2. If low CLIP-margin counts concentrate in the worst-gap scenes, semantic ambiguity contributes to wrong object labels even under the same GSA detections.
3. If precision is above ConceptGraphs but recall/F-mIoU lag, DuoGraph3D is conservative/fragmented; if precision also lags, inspect over-merge or semantic confusion examples before tuning thresholds.
