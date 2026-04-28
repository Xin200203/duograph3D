# DuoGraph3D repair experiment record — 2026-04-28

## Accepted repair

- Keep `descriptor_fused` as identity descriptor; maintain semantic label separately through class counts/object features.
- In class-agnostic ConceptGraphs-style runs, do not inject a generic text anchor into online semantic gates; leave text feature empty for online matching and rely on votes + visual CLIP.
- Export only non-merged objects with at least two detections in engineered profile; single-detection fragments remain too noisy.

## Two-scene recovery evidence

| run | Layer2 acc | Layer2 duplicate birth | ID switch/revisit | Duo objects | valid objects | Duo semantic acc | Duo duplicate rate | CG semantic acc | CG duplicate rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| bad cg-style semantic regression | 0.694207 | 0.863469 | 0.484880 | 490 | 266 | 0.304511 | 0.511278 | 0.373494 | 0.132530 |
| previous engineered reference | 0.805417 | 0.741573 | 0.419099 | 84 | 42 | 0.380953 | 0.214286 | 0.373494 | 0.132530 |
| current accepted repair | 0.944828 | 0.640000 | 0.255922 | 40 | 18 | 0.444444 | 0.111111 | 0.373494 | 0.132530 |

### Interpretation

- Main regression is fixed: Layer2 accuracy recovers from 0.694207 to 0.944828; object count drops from 490 to 40; object duplicate rate drops from 0.511278 to 0.111111.
- Current object semantic accuracy is 0.444444, above the same-run ConceptGraphs object semantic accuracy 0.373494 on room0+room1. The object count is lower, so this is a conservative export rather than a full coverage win.
- The previous engineered reference had more objects (84) but lower semantic accuracy (0.380953) and higher duplicate rate (0.214286) than the accepted repair.

## Ablations run after the repair

| run | scene | L1 dup p50 | L1 false merge | L2 acc | dup birth | ID switch | objects | valid | semantic acc | object dup | decision |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| duograph3d_repair_assoc155_room0_20260428 | room0 | 0.160000 | 0.011903 | 0.960481 | 0.285714 | 0.263750 | 9 | 5 | 0.200000 | 0.000000 | reject as default: object coverage collapses |
| duograph3d_repair_assoc155_room1_20260428 | room1 | 0.200000 | 0.013754 | 0.954228 | 0.400000 | 0.092120 | 11 | 4 | 0.500000 | 0.000000 | reject as default: object coverage collapses |
| duograph3d_repair_assoc165_room1_20260428 | room1 | 0.200000 | 0.019349 | 0.945140 | 0.789474 | 0.106472 | 14 | 5 | 0.600000 | 0.000000 | reject as default: object coverage drops |
| duograph3d_repair_descriptor_export2_room0_20260428 | room0 | 0.000000 | 0.635569 | 0.836735 | 0.363636 | 0.217949 | 10 | 7 | 0.142857 | 0.142857 | intermediate: generic text hurt semantics |
| duograph3d_repair_descriptor_export_room0_20260428 | room0 | 0.000000 | 0.635569 | 0.836735 | 0.363636 | 0.217949 | 9 | 6 | 0.000000 | 0.000000 | intermediate: export too strict |
| duograph3d_repair_export1_room0_20260428 | room0 | 0.161290 | 0.022526 | 0.952525 | 0.416667 | 0.282938 | 19 | 14 | 0.214286 | 0.285714 | reject: noisy single-detection exports |
| duograph3d_repair_l1_sem0_room0_20260428 | room0 | 0.000000 | 0.332660 | 0.876985 | 0.416667 | 0.263299 | 15 | 9 | 0.222222 | 0.222222 | reject: false merge/semantic collapse |
| duograph3d_repair_no_generic_text_room0_20260428 | room0 | 0.161290 | 0.022526 | 0.952525 | 0.416667 | 0.282938 | 15 | 10 | 0.300000 | 0.200000 | accepted direction |

## Final decision

Use the accepted repair settings for the current comparison slice. Do not adopt `layer1_history_min_semantic=0`, `association_threshold=1.55/1.65`, or `export_min_detections=1` as defaults based on the GT monitored ablations.

## Artifacts

- Final accepted run: `docs/official_results/duograph3d_repair_final_room0_room1_20260428/`
- Ablations: `docs/official_results/duograph3d_repair_ablations_20260428/`
- Bad regression baseline: `docs/official_results/duograph3d_cgstyle_semantics_room0_room1_20260428/`
- Previous engineered reference: `docs/official_results/duograph3d_history_object_greedy_gt_all_20260427/`
