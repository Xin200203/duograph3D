# Phase 3 External Baseline Inventory

日期：2026-04-23

## Goal
Establish at least two reviewer-credible external baseline families with formal provenance and result artifacts inside the DuoGraph3D execution lane.

## External baseline family 1 — DEVA official offline

### Official provenance
- Repo: `https://github.com/hkchengrex/Tracking-Anything-with-DEVA`
- Commit: `404a112df77f9644d5c7211811329ccd8174b8c3` (target contract already tracked in repo)

### Executed artifact provenance
- Remote artifact root: `/home/nebula/xxy/duograph3d_artifacts/deva_runtime_exec_replica_ext_v1/deva_output/JSONFiles`
- Local captured raw files:
  - `docs/baselines/raw/deva_jsonfiles/*.json`
- Local generated summaries:
  - `docs/baselines/generated/deva_output_summary.json`
  - `docs/baselines/generated/deva_output_summary.md`
  - `docs/baselines/generated/deva_lanes.json`

### Current quantitative snapshot
- Scene count: `8`
- Active scenes: `3`
- Active Replica scenes: `office0`, `office2`, `office3`
- Mean segments per frame and per-scene details are recorded in the generated summary file.

## External baseline family 2 — EmbodiedSAM / ESAM official ScanNet-MV family

### Official provenance
- Repo: `https://github.com/xuxw98/ESAM`
- Official repo commit on remote machine: `188fc6de44f7577fecec2d69b75c7adbd9992251`
- Official docs include ScanNet200-MV evaluation commands in `docs/run.md`.

### Executed artifact provenance
- Official-family execution artifacts currently come from the tracked local fork lane:
  - executed repo root: `/home/nebula/xxy/3D_Reconstruction`
  - executed commit: `3532e39eedf76c4345125b830bc1ab0412c9f0de`
- Metric artifact:
  - `/home/nebula/xxy/3D_Reconstruction/work_dirs/ESAM_online_scannet200_CA_mv_fast_ab/fullval_baseline_dino/20260113_203250/20260113_203250.json`
- Monitor summary artifact:
  - `/home/nebula/xxy/3D_Reconstruction/work_dirs/ESAM_online_scannet200_CA_mv_fast_ab/fullval_baseline_dino/online_monitor/online_monitor_summary.json`
- Local captured raw files:
  - `docs/baselines/raw/esam/metric.json`
  - `docs/baselines/raw/esam/online_monitor_summary.json`
- Local generated summaries:
  - `docs/baselines/generated/esam_output_summary.json`
  - `docs/baselines/generated/esam_output_summary.md`
  - `docs/baselines/generated/esam_lane.json`

### Current quantitative snapshot
- `all_ap = 0.4135`
- `all_ap_50 = 0.6300`
- `all_ap_25 = 0.7886`
- `scene_count = 312`
- `frame_count = 13430`
- `match_rate_mean = 0.8202`
- `birth_rate_mean = 0.1791`

## Baseline-system status

### What is now satisfied
- Two external baseline families are now documented with:
  - official repository provenance
  - commit anchors
  - executable/config references
  - captured raw artifact paths
  - normalized local summary files

### Remaining caution
- The ESAM executed lane currently comes from a local forked execution root rather than a fresh run launched directly inside the official repo checkout.
- This is documented explicitly, and should be treated as a provenance caveat rather than hidden.
