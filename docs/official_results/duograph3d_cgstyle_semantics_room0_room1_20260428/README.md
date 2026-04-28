# DuoGraph3D CG-style semantic maintenance two-scene run (room0, room1)

Run date: 2026-04-28  
Remote host: `nebula@10.177.69.184`  
Remote root: `/home/nebula/xxy/duograph3d_artifacts/duograph3d_cgstyle_semantics_room0_room1_20260428`

Command:

```bash
cd /home/nebula/xxy/DuoGraph3D
/home/nebula/miniconda3/envs/duograph-baselines-cu118/bin/python examples/run_conceptgraphs_gt_layer_monitor.py \
  --profile engineered \
  --root /home/nebula/xxy/duograph3d_artifacts/duograph3d_cgstyle_semantics_room0_room1_20260428 \
  --scenes room0 room1 \
  --duograph-pred-exp-name duograph3d_cgstyle_semantics_room0_room1_20260428
```

Comparable previous run: `docs/official_results/duograph3d_history_object_greedy_gt_all_20260427/gt_layer_monitor_summary.json`, filtered to `room0` and `room1` only. Both runs use the engineered ConceptGraphs/GSA profile.

## Micro summary over room0 + room1

| metric | previous engineered | CG-style semantic run | delta |
| --- | ---: | ---: | ---: |
| Layer2 decision accuracy | 0.805417 | 0.694207 | -0.111210 |
| Layer2 duplicate-birth rate | 0.741573 | 0.863469 | +0.121896 |
| Duo exported object count | 84 | 490 | +406 |
| Duo valid eval objects | 42 | 266 | +224 |
| Duo object semantic accuracy | 0.380952 | 0.304511 | -0.076441 |
| Duo object duplicate rate | 0.214286 | 0.511278 | +0.296992 |
| ConceptGraphs object semantic accuracy | 0.373494 | 0.373494 | +0.000000 |
| ConceptGraphs object duplicate rate | 0.132530 | 0.132530 | +0.000000 |

## Per-scene comparison

| scene | metric | previous | current | delta |
| --- | --- | ---: | ---: | ---: |
| room0 | Layer2 accuracy | 0.813494 | 0.658530 | -0.154964 |
| room0 | Layer2 duplicate-birth rate | 0.688889 | 0.888545 | +0.199656 |
| room0 | Layer2 ID-switch rate | 0.440159 | 0.496281 | +0.056122 |
| room0 | Duo object count | 38 | 250 | +212 |
| room0 | Duo object semantic accuracy | 0.291667 | 0.243750 | -0.047917 |
| room0 | Duo object duplicate rate | 0.333333 | 0.525000 | +0.191667 |
| room1 | Layer2 accuracy | 0.790437 | 0.744440 | -0.045997 |
| room1 | Layer2 duplicate-birth rate | 0.795455 | 0.826484 | +0.031029 |
| room1 | Layer2 ID-switch rate | 0.379767 | 0.468868 | +0.089101 |
| room1 | Duo object count | 46 | 240 | +194 |
| room1 | Duo object semantic accuracy | 0.500000 | 0.396226 | -0.103774 |
| room1 | Duo object duplicate rate | 0.055556 | 0.490566 | +0.435010 |

## Initial interpretation

The current CG-style feature-fusion change did **not** improve this engineered two-scene setting. It reduces neither duplicate births nor object-level duplication; instead it creates many more exported object fragments. The main warning signs are:

- duplicate-birth rate increased from 0.741573 to 0.863469;
- exported Duo objects increased from 84 to 490;
- object duplicate rate increased from 0.214286 to 0.511278;
- semantic accuracy dropped from 0.380952 to 0.304511.

The likely reason is that the GT-layer monitor now feeds text features derived from noisy per-detection top-1 Replica labels into memory. That is not fully equivalent to ConceptGraphs' safer object-feature maintenance under the GSA `none` detections, where semantic text information is much less dependent on a noisy single-frame top-1 class. In other words, the intended object-level fusion exists, but the text-feature source used by this monitor still injects label noise back into the semantic gate.
