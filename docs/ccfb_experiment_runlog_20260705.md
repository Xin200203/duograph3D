# DuoGraph3D CCF-B experiment runlog — 2026-07-05

## Objective

Act as experiment lead until the paper story closes: scene-independent mechanism, main experiments, ablations.  Today: resource inventory, evidence-chain protection, 76-server bring-up, offline selector feasibility audit, and the scheme-A merge-gate design decision.

## Infrastructure and resources (assessed 2026-07-05)

| Server | Hardware | State | Role |
| --- | --- | --- | --- |
| 184 (`nebula@10.177.69.184`) | 1× RTX 4090, 3.7T disk (1.2T free) | All assets present: DuoGraph3D code, concept-graphs-main, Replica+GSA (400/scene), scannet_v2, 279 artifact dirs.  Canonical python: `/home/nebula/miniconda3/envs/duograph-baselines-cu118/bin/python` (3.10.19; system python3 has no numpy — do NOT use bare python3 for runs). | Primary experiment machine; archive of record. |
| 76 (`xxy@10.176.56.76`) | 7× RTX 4090 (GPU 0-3 occupied by others, 4-6 idle), 112 cores, 503G RAM; datadisk3 662G free | Migration executed at `/datadisk3/xxy/duograph3d/` (code+Replica+GSA+Replica-semantic complete).  Code was stale (May); now synced to current (md5 match).  Env: `/datadisk1/xxy/miniconda3/envs/conceptgraph` (torch 2.0.1).  Baseline CSV pulled from 184.  Env file: `/datadisk3/xxy/duograph3d/duograph_env.sh` (DUOGRAPH_* vars).  NO internet — HF model loads must hit local cache (verified working). | Parallel experiment machine (sweeps, LOSO folds) on GPU 4-6. |
| 73 (`xxy@10.176.56.73:10246`) | 8× RTX 3090 all idle, 96 cores, 251G RAM, 2T free | No DuoGraph3D setup, no conceptgraph env, no Replica.  73→184 and 73→76 SSH auth not configured yet. | Reserve compute; candidate for ScanNet GSA-detection generation (GPU-heavy SAM/CLIP) after env setup. |

Cross-machine reproducibility (same command, office3 full scene, official eval):

| metric | 184 | 76 | abs diff |
| --- | ---: | ---: | ---: |
| mIoU | 16.479867 | 16.479196 | 0.0007 |
| mF1 | 20.484469 | 20.484063 | 0.0004 |
| F-mIoU | 34.578308 | 34.579887 | 0.0016 |

Decision: 76 and 184 results are interchangeable within a documented tolerance of 0.01 mIoU.

GPU-need assessment: the DuoGraph3D runner is inference-light (CLIP encode + point ops; ~6 min/scene/GPU).  Full-Replica variant ≈ 45 min serial on one GPU.  The only genuinely GPU-heavy future item is ScanNet GSA detection generation (P1), which maps onto 73/76 spare GPUs.

## Evidence log

- 2026-07-05: Project directory moved by owner from `~/Research/Code/research/DuoGraph3D` to `/Users/xin/Code/DuoGraph3D`.  All local tooling now uses the new absolute path.
- 2026-07-05: Committed and pushed the previously uncommitted evidence chain (`91413c6`, 110 files): E70 reproduction controls, repair diagnostics, all ccfb docs, previously untracked experiment scripts (`diagnose_eval_object_assignments.py`, `evaluate_composite_policy.py`, `gt_diagnostics.py`, ...).  `analysis/raw/` (2.1G) and literature PDFs excluded via .gitignore.  152 tests OK before commit.
- 2026-07-05: Runner path portability patch: `DUOGRAPH_SRC`, `DUOGRAPH_CG_MAIN`, `DUOGRAPH_ARTIFACT_ROOT`, `DUOGRAPH_REPLICA_ROOT`, `DUOGRAPH_REPLICA_SEMANTIC_ROOT`, `DUOGRAPH_BASELINE_CSV` env overrides; defaults preserve 184 behavior exactly.
- 2026-07-05: Code synced local→184 and local→76 (runner md5 `31d8e5...` on all three).
- 2026-07-05: Offline selector signal audit over 270 archived (run, scene) rows — `examples/analyze_selector_signals.py`, outputs in `analysis/tmp/selector_signal_audit/`.

## Offline selector audit conclusion (feasibility triage for 方案 C)

1. No GT-free signal is a strong global predictor of gap_mIoU (best mean |Spearman ρ| ≈ 0.43).
2. The apparently-best policy (`min_low_confidence_mask_rate`, mean regret 0.09) is **config leakage, not quality measurement**: the signal separates E70's phase-beta/gamma preprocessing from other variants; on a fresh same-preprocessing hypothesis grid it degenerates to ties.  Rejected.
3. `max_relabel_total` is perfect on office1/2/3 but falls into the office4 `vent→table` trap (regret 6.8, picks a gap −5.06 variant) — quantitative proof that repair-count maximization without an unsafe-label principle is dangerous.
4. `no_repair` control costs mean 2.53 mIoU regret — the repair family is worth ~+2.5; selection only needs to avoid unsafe picks.

Decision: **signal-only multi-hypothesis selector (方案 C) is rejected as primary mechanism.**  方案 A (per-pair semantic-aware merge gate) + 方案 B (scale-prior compatibility repair) are the main line; C survives only as a thin abstain/safety layer if needed.

## Key mechanism facts recovered from CG source + archived logs

- CG `merge_overlap_objects`: merge i→j when `overlap_ratio > merge_overlap_thresh` AND visual_sim/text_sim above thresholds.  Since ratio ∈ [0,1], **`merge_overlap_thresh=1.0` disables postprocess merging entirely** — E70 office1's "carrier preservation" is literally merge-off; office2 needs merge-on (0.7).  A per-pair veto replaces this global binary knob.
- Map objects carry per-detection `class_name` lists → `object_declared_label_counts()` gives the discrete multi-view label distribution needed for the label-cluster veto.
- `--phase` controls pipeline features (beta = signed L1 + candidate v2; gamma = +tentative fragments/stable memory).  office1@gamma loses the E70 office1 gain (carrier_v2 20260628 evidence); office2@beta untested — phase unification probe required.
- Canonical E70-mechanism arg strings recovered from `ccfb_cgmerge1_probe` VARIANT_START logs (office1 beta / office2 gamma payloads) — reuse verbatim in new probes.

## Scene-dependent knobs to unify (the actual CCF-B gap)

1. `merge_overlap_thresh` 0.7 vs 1.0(off) → 方案 A per-pair label-cluster veto, one setting everywhere.
2. repair keep-labels broad vs narrow-16 (office2) → auto-derived evaluator-facing source set (observation-count/share threshold, GT-free, scene-adaptive).
3. `--phase` beta vs gamma → single-phase probe both directions.
4. office2 `carve_rules cushion:sofa:0.04` → keep/drop decision after 1-3 land.

## Next actions

1. Implement 方案 A: `label_cluster_veto` pure function in `src/duograph3d/export_policy.py` (unit-tested locally), gated merge path + diagnostics in the runner (`--cg-merge-label-gate`, default off/legacy), source-text test extensions.
2. Launch P-A1 probe on 184 (6 variants, office1/office2): gate unification + phase unification matrix.
3. If P-A1 passes → keep-set auto-derivation (knob 2), then full Replica + LOSO.
