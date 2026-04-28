# DuoGraph3D repaired official Replica eval — room0+room1

Evaluator: ConceptGraphs `eval_replica_semseg.py`, `n_exclude=6`, same `gsa_detections_none` inputs. Metrics are percentages.

## Main result: accepted min-detections=2 export

| scene | mIoU | mRecall | mPrecision | mF1 | F-mIoU | CG mIoU | ΔmIoU | CG F-mIoU | ΔF-mIoU |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| room0 | 4.146 | 8.789 | 6.141 | 5.661 | 12.414 | 21.335 | -17.189 | 50.035 | -37.621 |
| room1 | 13.825 | 27.931 | 17.379 | 17.268 | 22.560 | 24.477 | -10.651 | 42.957 | -20.397 |
| all | 6.258 | 17.957 | 10.299 | 8.706 | 17.368 | 24.531 | -18.273 | 36.238 | -18.870 |

## Export threshold check

| export setting | all mIoU | all mRecall | all mPrecision | all F-mIoU | exported objects | note |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| min3 | 6.054 | 17.409 | 9.915 | 16.685 | 32 | original stricter export |
| min2 | 6.258 | 17.957 | 10.299 | 17.368 | 40 | accepted, slightly better official metrics |

## Diagnosis

- The repaired tracker is stable in GT-layer monitoring, but official semantic mIoU is still low because the official export is sparse: min2 run exports only 40 objects for room0+room1.
- Monitor rollup: track keys=2571, memory nodes=102, track fragmentation=1768, shadow under-merge candidate pairs=3500. This points to coverage / object export granularity as the main remaining official-metric gap, not the earlier identity-descriptor regression.
- Lowering export threshold from 3 to 2 gives a small improvement (all mIoU 6.054 → 6.258, F-mIoU 16.685 → 17.368), so the official-eval script default is now set to 2.

## Artifacts

- Accepted min2 run: `docs/official_results/duograph3d_repair_official_eval_min2_room0_room1_20260428/`
- Stricter min3 comparison: `docs/official_results/duograph3d_repair_official_eval_room0_room1_20260428/`
