# E70 reproduction gap analysis — 2026-07-04

## Summary

The first exact-reproduction probe showed that the current runner did **not** reproduce the archived E70 local mechanisms under the nominal scene policies.  A code-path/artifact audit then found a concrete drift: archived E70 used ConceptGraphs postprocess `merge_overlap_thresh=1.0`, while the current runner default/probe used `0.7`.  This changes the carrier objects before the large-label geometry repair stage, so `tissue-paper→cloth` and `bin→table` may never see the same source carriers.

## Probe result: current runner with `cg_merge_overlap_thresh=0.7`

Artifact mirrored locally: `analysis/raw/ccfb_20260704/e70_repro_probe/variant_summary.tsv`.

| variant | scene | status | ΔmIoU | ΔmF1 | ΔF-mIoU | relabels | export objects |
|---|---:|---:|---:|---:|---:|---|---:|
| office1_beta_tissue_off | office1 | 0 | +2.7865 | +3.6098 | +5.1820 | `{}` | 23 |
| office1_beta_no_large | office1 | 0 | +2.7865 | +3.6098 | +5.1820 | `{}` | 23 |
| office2_gamma_bin_only_off | office2 | 0 | -0.1365 | -1.0934 | +10.8612 | `{}` | 32 |
| office2_gamma_bin_vent_off | office2 | 0 | -0.2109 | -1.2638 | +10.7805 | `large_vent_to_table:4` | 32 |
| office2_gamma_bin_carrier_noz | office2 | 0 | -0.1365 | -1.0934 | +10.8612 | `{}` | 32 |
| office2_gamma_bin_active | office2 | 0 | -0.1365 | -1.0934 | +10.8612 | `{}` | 32 |

Interpretation: the rule layer itself is not sufficient.  The carrier set arriving at `apply_geometry_repairs` differs from the E70 carrier set.

## Likely path(s)

1. `examples/run_conceptgraphs_engineered_parity.py` builds map objects and applies ConceptGraphs-style postprocess through `conceptgraphs_postprocess_cfg()`.
2. Export objects are then repaired by `apply_geometry_repairs(...)`.
3. Large-label repairs first compute `object_repair_pred_label(...)` and require the evaluator-facing predicted label to equal the rule source label, e.g. `tissue-paper` or `bin`.
4. If postprocess merging changes the object carrier before this step, the repair does not trigger even if raw frame-level label evidence exists.

## Conflicts or mismatches

- Archived E70 office1 had `large_tissue-paper_to_cloth:1`, `566` points, `30` export objects, and office1 ΔmIoU `+8.1715`.
- Current nominal reproduction office1 had no relabels, `23` export objects, and office1 ΔmIoU `+2.7865`.
- Archived E70 office2 had `large_bin_to_table:1` and `large_vent_to_table:11`, with office2 ΔmIoU `+6.4916`.
- Current nominal office2 with the same visible large-label rules had no `bin→table` and only `large_vent_to_table:4`, with office2 ΔmIoU `-0.2109`.
- Artifact diff found the key parameter drift:
  - E70 office1 `conceptgraphs_postprocess.merge_overlap_thresh = 1.0`.
  - Current probe office1 `conceptgraphs_postprocess.merge_overlap_thresh = 0.7`.
  - E70 office2 also used a narrower `geometry_repair_keep_labels` set; current probe used the broad default keep-set, but the first-order reproduction blocker is the merge threshold because it changes office1 export object count from `30` to `23`.

## Evidence level

High for metric/relabel differences and parameter drift: both are read from remote 184 artifacts (`merge_monitor_summary.json`, `variant_summary.tsv`) and archived E70 summaries.  Medium for causal attribution until the in-flight `cg_merge_overlap_thresh=1.0` probe completes.

## Ablation

### A1 — Postprocess carrier preservation (`merge_overlap_thresh`)

### Target hypothesis
E70's positive mechanisms require preserving geometry carriers through postprocess; `merge_overlap_thresh=0.7` over-merges or changes carriers so the large-label repair stage cannot see the `tissue-paper`/`bin` source objects.

### Expected signal
Re-running target scenes with `--cg-merge-overlap-thresh 1.0` should restore E70-like relabel counts and metrics: office1 should recover `large_tissue-paper_to_cloth:1` and approach ΔmIoU `+8.17`; office2 should recover `large_bin_to_table:1` under the E70 bin/vent policy and approach ΔmIoU `+6.49`.

### Stop condition
If `merge_overlap_thresh=1.0` does not restore the relabel counts, continue diffing E70/current object-level summaries before any broad full-scene run; do not claim a method innovation.

## Ablation

### A2 — Large-label repair leave-one-out under preserved carriers

### Target hypothesis
Once carriers are preserved, the publishable contribution is not raw threshold tuning but **geometry-carrier authority repair**: source labels that are geometrically implausible for their scale are corrected only at export.

### Expected signal
With `merge_overlap_thresh=1.0`, `office1 no_large` should drop relative to `office1 tissue`, and `office2 binonly/binvent` should quantify the positive `bin→table` and unsafe/secondary `vent→table` boundary.

### Stop condition
If no-large rows are close to repaired rows, the relabel mechanism is not causal enough for a paper claim.

## Ablation

### A3 — Safe shared carrier gate after reproduction

### Target hypothesis
A CCF-B defensible method needs a scene-independent version: preserve carriers (`merge_overlap_thresh=1.0`) and permit only high-confidence carrier repairs, while rejecting unsafe broad `vent→table`.

### Expected signal
Full Replica should keep all ΔmIoU above `+2.0` and avoid office4/room collapses.  Relabel counts should be sparse and interpretable.

### Stop condition
If full-scene shared gate remains near `+0.2~+0.7`, keep E70 as a diagnostic composite and write the innovation as observability + failure attribution, not as a universal accuracy method.
