# DuoGraph3D vs ConceptGraphs — Replica GSA parity evaluation (2026-04-24)

## Verdict

This run completes the corrected **same-setting** comparison against ConceptGraphs on the official 8-scene Replica semantic-evaluation protocol.

Key correction versus the earlier `duograph3d_conceptgraphs_real_subset_20260424` result: the earlier run used the current DuoGraph3D DEVA-annotation candidate package and only evaluated the 3 non-empty scenes (`office0`, `office2`, `office3`). This parity run instead uses the same ConceptGraphs GSA detection surface and all 8 Replica scenes.

## Protocol lock

- Scene list: `room0`, `room1`, `room2`, `office0`, `office1`, `office2`, `office3`, `office4`.
- Input detections/features: official ConceptGraphs `gsa_detections_none` for every scene (400 GSA frames per scene).
- Evaluator: ConceptGraphs `eval_replica_semseg` with `n_exclude=6` (`other`, `floor`, `wall`, `ceiling`, `door`, `window`).
- Prediction export name: `duograph3d_gsa_parity_naive`.
- DuoGraph3D temporal setting: `temporal_naive_framewise`. This intentionally disables DEVA-style carry-over because the parity protocol is the ConceptGraphs GSA setting, not the DEVA candidate setting.
- Adapter parameters: `voxel_size=0.75`, `min_mask_pixels=300`, `max_points_per_obs=48`, `max_points_per_object=4096`.
- Metric units: percentages (%), matching ConceptGraphs output.

## Main result

| scene | Duo mIoU | CG mIoU | Δ | Duo mRecall | CG mRecall | Duo mPrecision | CG mPrecision | Duo mF1 | CG mF1 | Duo F-mIoU | CG F-mIoU |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| room0 | 21.4933 | 21.3348 | +0.1585 | 39.9016 | 38.3352 | 39.0372 | 29.4326 | 28.3515 | 25.2726 | 46.2628 | 50.0347 |
| room1 | 26.9305 | 24.4768 | +2.4537 | 47.8130 | 38.3269 | 48.2702 | 32.6292 | 35.8546 | 29.2364 | 40.6407 | 42.9568 |
| room2 | 23.2029 | 26.9701 | -3.7672 | 39.2247 | 39.6599 | 50.1654 | 41.0043 | 29.3821 | 32.1138 | 39.7027 | 34.8707 |
| office0 | 16.4600 | 20.0484 | -3.5884 | 31.6202 | 37.4705 | 33.2585 | 25.0896 | 21.6348 | 23.9950 | 28.6771 | 32.2764 |
| office1 | 10.0580 | 14.4811 | -4.4231 | 26.1146 | 25.4010 | 27.8431 | 15.8341 | 13.5041 | 16.8153 | 12.9931 | 14.7201 |
| office2 | 20.4953 | 21.8904 | -1.3952 | 38.3188 | 36.0357 | 42.2525 | 33.3267 | 27.8076 | 26.9593 | 38.5950 | 40.4821 |
| office3 | 9.7935 | 21.6773 | -11.8838 | 37.2409 | 35.8980 | 22.9361 | 26.0344 | 14.1086 | 25.0890 | 24.7380 | 35.7998 |
| office4 | 36.5337 | 46.8290 | -10.2952 | 54.7751 | 60.9982 | 50.7873 | 55.5282 | 44.9230 | 51.7748 | 41.1079 | 51.2342 |
| all | 20.0908 | 24.5313 | -4.4405 | 39.2840 | 40.2156 | 43.6455 | 36.1800 | 27.9607 | 30.1223 | 33.5883 | 36.2376 |

Aggregate (`all`) summary:

- DuoGraph3D: **mIoU 20.0908 / mRecall 39.2840 / mPrecision 43.6455 / mF1 27.9607 / F-mIoU 33.5883**.
- ConceptGraphs: **mIoU 24.5313 / mRecall 40.2156 / mPrecision 36.1800 / mF1 30.1223 / F-mIoU 36.2376**.
- mIoU gap: **-4.4405** percentage points.

## Setting audit

- `corrects_prior_deva_subset_mismatch`: `True`
- `uses_all_requested_replica_scenes`: `True`
- `uses_conceptgraphs_gsa_detections_none`: `True`
- `uses_conceptgraphs_replica_semantic_evaluator`: `True`
- `does_not_use_deva_annotation_masks`: `True`
- `does_not_use_gt_sidecar`: `True`

## Execution diagnostics

| scene | raw dets | kept obs | track keys | memory nodes | track fragmentation | exported objects | exported points | seconds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| room0 | 17601 | 17502 | 1279 | 13695 | 12416 | 1279 | 684736 | 113.7 |
| room1 | 10649 | 10608 | 748 | 7936 | 7188 | 748 | 429696 | 87.5 |
| room2 | 11130 | 11077 | 1034 | 8674 | 7640 | 1034 | 468320 | 84.9 |
| office0 | 15383 | 15288 | 1012 | 11387 | 10375 | 1012 | 625616 | 93.6 |
| office1 | 9206 | 9167 | 651 | 6802 | 6151 | 651 | 373472 | 76.7 |
| office2 | 14788 | 14674 | 1252 | 11620 | 10368 | 1252 | 629163 | 112.2 |
| office3 | 17090 | 16816 | 1562 | 13778 | 12216 | 1562 | 685649 | 104.7 |
| office4 | 13952 | 13860 | 1578 | 11252 | 9674 | 1578 | 617808 | 117.3 |

## Artifacts

- Local CSV: `docs/official_results/duograph3d_conceptgraphs_gsa_parity_20260424/raw/duograph_gsa_parity_results.csv`
- Local summary: `docs/official_results/duograph3d_conceptgraphs_gsa_parity_20260424/raw/duograph_gsa_parity_summary.json`
- Local run log: `docs/official_results/duograph3d_conceptgraphs_gsa_parity_20260424/raw/run_gsa_parity_eval.log`
- Local runner: `docs/official_results/duograph3d_conceptgraphs_gsa_parity_20260424/raw/run_gsa_parity_eval.py`
- Local runner shell wrapper: `docs/official_results/duograph3d_conceptgraphs_gsa_parity_20260424/raw/run_gsa_parity_eval.sh`
- Baseline CSV mirror: `docs/official_results/duograph3d_conceptgraphs_gsa_parity_20260424/raw/conceptgraphs_replica_ex6_results.csv`
- Remote root: `/home/nebula/xxy/duograph3d_artifacts/duograph3d_conceptgraphs_gsa_parity_20260424`
- Remote exported pcd pattern: `/home/nebula/xxy/dataset/Replica/<scene>/pcd_saves/full_pcd_duograph3d_gsa_parity_naive.pkl.gz`

## Interpretation / remaining risks

- The corrected parity result is much stronger than the earlier DEVA-subset result, but ConceptGraphs still leads on aggregate mIoU and F-mIoU.
- DuoGraph3D is competitive or better on some precision/recall-style scene rows, but `office1` and `office3` remain weak.
- The export intentionally writes one object per stable observation track key. The DuoGraph3D memory layer still reports high internal fragmentation (memory nodes >> exported objects), so this result should be described as a GSA-parity object-map export, not as evidence that the long-horizon memory fragmentation problem is solved.
- The earlier DEVA-style ConceptGraphs run path is now classified as a setting mismatch for this comparison; it should not be used as the main ConceptGraphs parity row.
