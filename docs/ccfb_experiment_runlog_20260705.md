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

## The export-source discovery (2026-07-06, third reversal of the night)

PB2 clean rows kept failing (office4 −36.2 with the gate nearly inert, room2
still negative), which falsified "the gate is the office4 culprit."  E70
forensics from the local A1 mirror then found the real substrate difference:

> **E70's non-target scenes exported via the coverage-gated GEOMETRY fallback**
> (`duograph3d_geometry_key_coverage`, office4 = 191 objects, fallback reason
> `memory_object_count_below_coverage_floor`), while only office1/office2 were
> forced memory-dense.  Every unified run so far forced memory-dense on all
> scenes — the collapses were export-substrate mismatches, not gate failures.

Consequences:

1. The unified config must use `--export-source auto` — the coverage-gated
   policy already in `export_policy.py` (global constants, zero scene names).
   E70's per-scene export split emerges naturally from the coverage floor.
2. E70's forcing of memory-dense on office1/office2 was itself scene knowledge.
   Under auto, office1 (46 memory nodes < 100 floor) likely falls back to
   geometry export; whether the gate+scale-prior gains survive on the geometry
   substrate is the decisive open question → PC2 office1/office2 rows.
3. PA2 floor curve (office1, hand rule, memory-dense): floor 2 = +8.171,
   floor 8 = +6.938 — the floor trades office1 gain for other-scene safety;
   under auto-export this tradeoff must be re-measured.
4. office2@beta has two healthy operating points (all-veto +8.19 / all-merge
   +8.21 with repair) and a worst-of-both middle (floor24 = +2.41) — evidence
   that partial merging is the dangerous regime, relevant to floor choice.

In flight: PC1 gamma matrix on 184 (phase axis for the ablation table), PC2
auto-export rows office4/room0/room2 on 76 and office1/office2 on 184 next.

## The consolidation-ratio substrate signal (2026-07-06 late)

PC2 office1@auto fell back to geometry and landed −1.06 → the coverage-floor
rule mis-routes office1 (needs dense at 46 memory nodes) while office4 (111
nodes) needs geometry — simple coverage thresholds order the scenes WRONGLY.
Full E70 source map from the A1 mirror:

| scene | E70 substrate | E70 gap | mem_nodes/key_count |
| --- | --- | ---: | ---: |
| room1 | memory-dense | +11.18 | 0.16 |
| office1 | memory-dense (forced) | +8.17 | 0.07 |
| office2 | memory-dense (forced) | +6.49 | 0.14 |
| room0 | geometry-multires | +6.50 | 0.28 |
| room2 | geometry-multires | +0.60 | 0.23 |
| office0 | geometry-multires | +1.87 | 0.26 |
| office3 | geometry-multires | +1.70 | 0.20 |
| office4 | geometry plain | +1.75 | 0.23 |

1. E70 is a THREE-substrate composite (dense ×3, multires-geometry ×4, plain
   geometry ×1) — the scene-policy is deeper than merge/phase: it is an export
   substrate assignment.  No single substrate wins all 8 (dense kills office4
   at −26 even without gate/sp; geometry kills office1 at −1.06 with them).
2. **`consolidation_ratio = memory_node_count / key_count` separates the
   substrate classes perfectly on all 8 scenes** (dense-good ≤ 0.16,
   geometry-good ≥ 0.20).  Semantics: when online memory consolidates far
   below key granularity, memory roots carry real object structure → dense
   export; when memory barely consolidates beyond keys, the keys are the
   better substrate.  GT-free, scene-independent, computable online.
3. Selector-v2 (binary substrate choice by consolidation ratio) is thus a
   principled candidate — unlike the rejected arbitrary-portfolio selector.
   Validation pending on the current-code 8×2 matrix (PC2 rooms on 76 + PC3
   geometry arm on 184).

## v4.1: substrate-conditional mechanism scope (2026-07-06 night)

Geometry-arm rows exposed the last structural fact: on raw geometry-key
exports BOTH mechanisms misfire (office0-geo: 148 vetoes + 15 declared-backed
junk relabels, −3.73) because **key-bucket declared distributions are boundary
noise, not multi-view object evidence** — the mechanisms' evidence premise
only holds on consolidated (memory-dense) substrates.  Hence
`--mechanisms-scope consolidated-only`: gate + scale-prior act on dense-routed
scenes; geometry-routed scenes pass through as the coverage fallback.
Substrate-conditional, zero scene names.

Routing validation (current-code matrix, dense arm = v1, geometry arm = PC2/PC3):

| scene | ratio | route | dense | geometry | routing verdict |
| --- | ---: | --- | ---: | ---: | --- |
| room1 | .047 | dense | **+6.29** | +1.79 | ✓ picks winner |
| office1 | .072 | dense | **+4.02** | −1.06 | ✓ |
| office2 | .134 | dense | **+5.72** | −5.88 | ✓ |
| office0 | .307 | geo | +3.18 | −3.73* | ✗ miss (~1-2 mIoU cost under v4.1 passthrough) |
| room0/room2/office3/office4 | ≥.179 | geo | −1.6/−10.2/−0.7/−27.8 | passthrough | ✓ direction (dense arm catastrophic) |

*office0-geo number includes the misfiring mechanisms; v4.1 passthrough will be
higher.  office0 is the single-threshold rule's residual and is documented, not
patched (moving its ratio boundary would re-route office4 into catastrophe).

Overnight queue: 184 = v4_main full → wo_gate full; 76 = wo_sp full →
forced_geo full.  PA2 floor curve final: office1 2→+8.171 / 8→+6.938 /
24→+6.939 (plateau).

## The consolidation ratio is a voxel artifact (2026-07-06 ~02:00, final negative result)

Three call-site fixes (raw memory count, raw key count, prepare-time key
count) all landed and were each verified by runtime diagnostics — and room0
still routed dense.  Ground truth: **E70's geometry-substrate scenes ran a
coarser prep entirely** (`voxel_size 0.5` → room0 436 keys, plus
min_object_detections 8, max_points_per_obs 640) while its dense scenes used
voxel 0.2.  Under unified prep (0.2 everywhere) the per-scene ratios interleave
completely (dense-good .047/.072/.134 vs geo-good .052/.063/.065/.080/.083):
the "perfect separation" was the prep-granularity difference, not a
consolidation signal.  consolidation-auto is dead as calibrated; the E70
composite rests on FIVE per-scene hand choices (prep granularity, substrate,
phase, merge threshold, keep set), and any post-hoc routing signal is
prep-dependent (circular).

Lead decision: stop the single-config unification chase.  Paper claims settle
on (1) the mechanism tier — causal, exact-recovery-validated carrier-authority
mechanisms on the consolidated substrate with forensic guard derivations and
pre-registered safety; (2) the honest system tier — single-config full-Replica
remains open (documented negative-result chain), E70 oracle as ceiling, the
8×2 substrate matrix as the sensitivity quantification.  v4g's rows are kept
as forced-dense (newest code) and dense+legacy ablation rows.

## Overnight rows sealed (2026-07-06 03:20)

Full-Replica single-config landscape (official all-row ΔmIoU):

| config | all ΔmIoU |
| --- | ---: |
| E70 oracle (5-layer scene-local composite) | **+3.041** |
| v1 dense+gate floor2 (no mutual, old sp) | −3.716 |
| forced_dense, final mechanisms (v4g main) | −4.412 |
| wo_sp (dense + gate + mutual) | −4.451 |
| dense_legacy (dense + CG merge + sp) | −6.082 |
| forced_geo (geometry + misfiring mechanisms) | −4.644 |

Per-scene mechanism value on the consolidated substrate remains the positive
core: office1 +8.171 (gate causal, E70-exact), office2 +8.185/+8.211,
room1 +6.29, office0 +3.18; gate net contribution on dense room0 +2.2 /
office0 +2.9 / room1 +0.5.  gamma-axis office2 floor rows: {2,8,24} →
{+2.96, +2.96, +3.18}, no relabels.  wo_gate office2 forensics: under
auto-keep the merged carrier's readout is not "bin" — the E70 bin case is
only visible under its narrow hand keep-set, confirming the mis-readout
expression depends on the evaluator-facing source set.

## Morning assembly complete (2026-07-06)

- Tables T1 (mechanism causality on the consolidated substrate), T2 (full-scene
  single-config ablations + E70 oracle), T3 (audit counts + pre-registration),
  T4 (12-row negative-boundary table with per-row object-level evidence) —
  `docs/ccfb_tables_20260706.md`.
- Paper story v3 (mechanism tier + failure-attribution framework + honest
  compositionality open problem; supersedes v2) —
  `docs/ccfb_paper_story_v3_20260706.md`, including the reviewer Q&A plan and
  the dev/diagnostic/validation scene accounting.

## 2026-07-06 daytime — T5 + ScanNet bring-up

- **T5 (post-hoc infeasibility)**: CG's own maps + mechanisms → legacy −0.083
  (protocol parity), gate 0/0/0 candidates on all 8 scenes, sp noise −0.461
  at alignment 0.9999.  Central thesis established: authority control is only
  effective at decision time.  Artifacts `ccfb_cg_authority_20260706`.
- **ScanNet transfer pipeline fully assembled in one day**: 8 val_50 scenes
  staged (25k-export layout + scaled intrinsics), GSA detections 8/8
  (SAM+CLIP, `scannet_gsa_20260706{,b}`), CG-baseline cfslam maps 8/8
  (official parameters, `scannet_cfslam_20260706`), NYU40 evaluator
  (`examples/eval_scannet_semseg.py`, dual-path GT: labels.ply or
  segs+aggregation+tsv reconstruction), runner `--dataset scannet` mode
  (per-scene intrinsics, per-frame finite-guarded poses, NYU40 vocabulary +
  frozen priors + NYU40 structural set).  NYU40 priors committed BEFORE any
  ScanNet evaluation (pre-registration).
- **Env incident**: `pip install plyfile` mid-queue pulled numpy 2.x and broke
  cv2 ABI for 4 GSA scenes; rolled back to 1.26.4, retried clean.  Rule
  recorded: no unpinned installs into shared envs while queues run.
- CG paper Table II extracted for baseline context (mAcc/F-mIoU protocol,
  noted as distinct from the repo evaluator): ConceptFusion 24.16/31.31,
  CF+SAM 31.53/38.70, CG 40.63/35.95, CG-D 38.72/35.82.
- HOV-SG protocol verification: web access unavailable in this session
  (WebSearch/WebFetch blocked) — manual item.
- In flight: ScanNet CG-baseline eval + in-loop mechanism smoke (scene0568_00).

## Next (P1, pre-submission)

1. ScanNet OOD sanity (73's 8× RTX 3090: GSA detection generation → mechanism
   fire/abstain behavior on OOD consolidated substrates).
2. Replica instance AP evaluator (supplementary protocol bridge).
3. CG-Detector baseline row + OVI-MAP/OnlineAnySeg/ESAM protocol-bridge table.
4. Manuscript rewrite from story v3 (replace the 4/23 draft mainline).
5. Remaining sensitivity sweeps (mutual thresh, top-share, tolerance).
