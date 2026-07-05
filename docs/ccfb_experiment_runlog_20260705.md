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

## P-A1 probe results (label-cluster merge gate)

Roots: 184 `ccfb_pa1_label_gate_probe_20260705_pa1{,b,c}`, 76 `..._pa1`.

Round 1 (`pa1`) exposed a structural gap: `vetoed=0` everywhere because export
objects carried `class_name=[single aggregated label]` — no multi-view evidence
reached the merge stage.  Fix: every export object now carries
`declared_label_counts` (true per-key/per-node distributions; stored as
[label,count] pairs because CG's `merge_obj2_into_obj1` concatenates lists and
crashes on dicts).  Control rows confirmed gate-off ≡ legacy exactly.

Round 2 (`pa1b`, real distributions) — **方案 A decisive result**:

| variant | scene | ΔmIoU | relabels | objects | gate cand/merged/vetoed |
| --- | --- | ---: | --- | ---: | --- |
| o1_gate_m07 | office1 | **+8.171477** | tissue-paper→cloth:1 | 30 | 7/0/**7** |
| o1_nogate_m07 | office1 | +2.786518 | {} | 23 | legacy control |
| o2_gate_m07 (old code) | office2 | **+6.254106** | bin→table:1 | 32 | 24/20/0 |

One merge config (`overlap 0.7 + label gate`) now satisfies both scenes —
office1 E70 recovered exactly WITHOUT `merge_overlap_thresh=1.0`.  The decisive
vetoed pair is `cloth|picture` (cloth carrier, 164 declared obs, visual_sim
0.94 above CG's threshold, was being absorbed into a picture object with 567
obs; the carrier's wrong tissue-paper CLIP readout then stays visible for the
repair stage to fix).  Also notable: `text_sim=1.0` on every pair — CG's
text-sim merge threshold is vacuous under the class-agnostic token mode, so the
discrete declared-label veto supplies exactly the evidence dimension CG's
continuous-feature thresholds cannot.

Pending: `pa1c` reruns office2 (gamma + beta) on the new code to confirm the
veto does not break office2's same-label fragment merging with real
distributions.

## Pre-registered B2 prediction (written before PB1 ran)

The office2 bin-carrier object record (pa1 o2_gate_m07 relabel example):
`pred_label=bin, max_extent=1.564, z_extent=0.122, declared={table:2, tablet:1,
tv-stand:1, switch:1, camera:1}, source_declared_share=0.0, target(table)
share=0.333`.  Prediction: the scale-prior pass fires here with default guards —
violation (1.564 > bin prior 0.9), source not multi-view supported (0.0 < 0.6),
table is the only declared label whose prior accommodates 1.564m and its share
0.333 ≥ 0.15.  The readout is a single-channel outlier against both the
multi-view label evidence and the geometry — exactly the authority-revocation
case the mechanism encodes.  office1 predicted analogous (declared cloth≈1.0).
office4 vent / room0 cushion predicted to abstain.  PB1 tests all four.

## PA1c results — the mechanism story deepens (2026-07-05 late)

| variant | scene | ΔmIoU | relabels | objects | gate cand/merged/vetoed |
| --- | --- | ---: | --- | ---: | --- |
| o2_gate_m07 (new code, gamma) | office2 | +3.698 | {} | 48 | 23/2/21 |
| o2_gate_m07_beta (new code) | office2 | **+8.185** | {} | 91 | 124/13/108 |

Two findings:

1. **office2@gamma with real distributions over-vetoes**: the same-table fragments
   (declared tops table/tablet/tv-stand/switch, min-side 12-17 obs) are distinct-top
   pairs under split-by-label export, so the veto blocks the fragment assembly the
   bin→table repair needed.  The discriminating signal versus office1's correct
   vetoes (cloth|picture at 164/567 obs) is **multi-view evidence volume** —
   hence the evidence-floor dial `--cg-merge-label-gate-min-obs`
   (`run_ccfb_pa2_minobs_sweep_20260705.sh` calibrates it on the two dev scenes).

2. **office2@beta + gate = +8.185, a new office2 best, with NO repair fired.**
   Mechanistic reading: the "bin" mis-readout was *manufactured by merging* —
   feature averaging across fragments shifted the merged carrier's CLIP top-1 to
   bin.  Preserve the fragments and the mis-readout never exists; the E70 repair
   was compensating for merge-induced corruption.  Carrier preservation is the
   cause; repair is the patch.  This inverts the paper's mechanism hierarchy:
   the merge gate is primary, scale-prior repair handles the residual cases
   (office1's cloth carrier whose readout is corrupted at the *detection* level,
   not by merging).

Unified config candidate: `--phase beta --cg-merge-overlap-thresh 0.7
--cg-merge-label-gate 1 --geometry-repair-keep-mode declared-auto
--geometry-repair-scale-prior-mode apply`, zero scene names, zero hand rules.
Dev-scene evidence: office1 +8.171 (E70-exact), office2 +8.185 (new best).

## Unified v1 full run readout + the two remaining mechanism gaps (2026-07-06)

Per-scene ΔmIoU (unified v1 = gate floor 2, no mutual guard, no hard-ratio):
room0 −1.59, room1 +6.29, room2 −10.22, office0 +3.18, office1 +4.02,
office2 +5.72, office3 −0.73, office4 pending.  v1 becomes the
"no-evidence-floor / no-impossibility-override" ablation row.

Forensics chain (all from object-level probes, no GT):

1. **room0/room2 collapse = over-vetoing.**  room0: 19/20 vetoes have min-side
   2-7 declared obs (noise).  room2: bimodal — 6 noise vetoes plus 11 high-obs
   vetoes that are **mutually contained pairs** (comforter|chair 0.86/0.83 both
   directions; cushion|chair 0.998/0.815): spatially coincident point sets =
   one observation stream split by readout noise.  office1's correct vetoes are
   all one-directional (cloth ⊂ picture 0.71).  → two guards: evidence floor
   (`--cg-merge-label-gate-min-obs`, PA2 sweep) + mutual-containment skip
   (`--cg-merge-label-gate-mutual-thresh`, default 0.7).

2. **office1 landed exactly on the no-repair value (+4.016)**: the gate
   preserved the carrier but scale-prior abstained via `source_well_supported`
   — the carrier's 70/70 detections unanimously declare tissue-paper on a
   1.399m extent (3.1× prior).  Consensus ≠ correctness under systematic
   detector bias.  Discriminator vs room0's true large cushions (1.04-1.3×):
   **violation severity**.  → hard-ratio override (default 2×) + CLIP re-readout
   restricted to physically-compatible labels when declared offers no
   alternative ("the most probable label that is physically possible").

3. **office2 probe-vs-unified delta (+8.19 → +5.72) attributed to the
   cushion:sofa carve rule** (gate behavior identical 124/13/108, sp fired
   nothing in both).  Carve contribution isolated in PB2; decision pending on
   generalize-or-scope-out.

4. **Attribution control**: office2@beta+legacy+repair (+8.211) ≈ beta+gate
   no-repair (+8.185) — office2's jump over E70 is the beta phase; the gate's
   causal ground is office1-type carrier preservation.

## PB2 office1 negative result — CLIP fallback rejected (2026-07-06)

PB2 o1 (floor 24 + hard-ratio + clip-fallback) = **−2.071**: all 7 hard
violations fired the fallback with compatible-CLIP scores ~0.25 and ~0.01
margins — noise-ranking relabels (camera→picture, switch→comforter, ...), and
the tissue carrier itself went to **comforter** (cloth ranked 3rd).

Honest conclusion: the E70 `tissue→cloth` target encodes knowledge that no
GT-free evidence stream on that object carries — declared says tissue (70/70,
systematically wrong), CLIP re-readout says comforter.  Lead decision:

1. `--geometry-repair-scale-prior-clip-fallback` default **0** (diagnostics
   only); scale-prior targets come from declared evidence only.
2. The unified method claims carrier preservation + safe authority control
   (positive everywhere, zero scene knowledge, auditable abstention — office4's
   6 vent violations all correctly abstained, pre-registered).  It does NOT
   claim the office1 repair delta; **E70 remains the with-scene-knowledge
   oracle upper bound**, and the gap between unified and E70 on office1 is the
   honest "price of no scene knowledge" — a paperable negative boundary.
3. B2's realistic role: rare declared-backed repairs + auditable abstention;
   the office2-style gains come from M1 (carrier preservation) + beta phase.

## Next actions

1. PA2 floor sweep on 76 (running) → pick evidence floor from dev scenes.
2. PB2 remaining rows run with fallback-off code (room0/room2/office4 = pure
   gate-guard validation; o2carve = carve isolation).
3. Unified v2 full Replica with calibrated floor → the main-table candidate;
   then ablation matrix + sensitivity sweep + held-out scene accounting
   (dev evidence: office1/office2 + room0/room2/office4 diagnostics; untouched:
   room1, office0, office3).
