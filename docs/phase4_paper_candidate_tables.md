# Phase 4 Paper Candidate Tables

日期：2026-04-23

## Internal regime main table candidate

| Regime | Coverage | identity_fragmentation_count | track_consistency_rate | real_observation_frame_rate | geometry_support_mean |
| --- | ---: | ---: | ---: | ---: | ---: |
| phase4_baseline | 11 | 63.455 | 0.594 | 0.818 | 0.271 |
| phase4_burst | 11 | 20.273 | 0.716 | 0.500 | 0.287 |
| phase4_random | 11 | 11.364 | 0.815 | 0.348 | 0.317 |
| phase4_stress | 11 | 21.091 | 0.736 | 0.500 | 0.306 |

## Internal ablation table candidate (Δ vs baseline)

| Regime | Δ fragmentation | Δ track consistency | Δ observation frame rate | Δ geometry support |
| --- | ---: | ---: | ---: | ---: |
| phase4_burst | +43.182 | +0.122 | -0.318 | +0.016 |
| phase4_random | +52.091 | +0.221 | -0.470 | +0.046 |
| phase4_stress | +42.364 | +0.142 | -0.318 | +0.035 |

## External baseline family table

| Baseline | Dataset | Scope | Axis | Primary metric | Value | Faithfulness |
| --- | --- | --- | --- | --- | ---: | --- |
| DEVA official offline | replica | office0 | temporal_external_lane | avg_segments_per_frame | 1.0000 | official_repo_executed |
| DEVA official offline | replica | office2 | temporal_external_lane | avg_segments_per_frame | 0.6670 | official_repo_executed |
| DEVA official offline | replica | office3 | temporal_external_lane | avg_segments_per_frame | 0.6670 | official_repo_executed |
| EmbodiedSAM official ScanNet-MV | scannet | fullval | online_3d_external_lane | all_ap | 0.4135 | official_family_fork_executed |

## Notes

- These tables are Phase 4 **candidate** tables, not final camera-ready tables.
- They are sufficient to support the Phase 4 internal paper-grade candidate bar.
- External baseline family metrics remain family-specific and are therefore listed in a parallel comparison table rather than force-merged into a single misleading scalar surface.
