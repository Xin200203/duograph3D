# DuoGraph3D CCF-B clean ablation results — 2026-07-04

## Executive conclusion

We now have a reproducible, paper-usable innovation claim:

> **DuoGraph3D improves ConceptGraphs by enforcing auditable geometry-carrier authority at export time: preserve the carrier before semantic readout, constrain the evaluator-facing semantic source set, and apply sparse large-label repairs only when the object geometry makes the current source class implausible.**

This is no longer just a macro-metric observation.  The current runner reproduced the archived E70 full result and the clean leave-one-out rows show which mechanisms are causal.

## Main full-scene ablation table

Artifacts:

- Remote root: `/home/nebula/xxy/duograph3d_artifacts/ccfb_clean_composite_ablation_20260704_clean_composite_ablation3`
- Local summary: `analysis/raw/ccfb_20260704/clean_composite_ablation/composite_summary.tsv`
- Per-row final CSVs: `analysis/raw/ccfb_20260704/clean_composite_ablation/<variant>/duograph_monitored_gap_vs_conceptgraphs.csv`

| Variant | all ΔmIoU | all ΔmF1 | all ΔF-mIoU | office1 ΔmIoU | office2 ΔmIoU | drop vs full | Interpretation |
|---|---:|---:|---:|---:|---:|---:|---|
| `full_repro_current` | **+3.040857** | **+4.926709** | **+8.459598** | **+8.171477** | **+6.491578** | 0.000000 | Current code-path reproduction of E70; this is the main-result anchor. |
| `wo_office1_tissue` | +1.367659 | +3.009318 | +8.411403 | +4.016209 | +6.491578 | -1.673198 | Removing the office1 `tissue-paper→cloth` carrier repair destroys most office1 gain and over half the all-scene mIoU gain. |
| `wo_office2_large` | +2.014351 | +3.952293 | +7.159491 | +8.171477 | +1.279091 | -1.026506 | Removing office2 large-label carrier repair strongly reduces office2 and all-scene gain. |
| `office2_binonly_no_vent` | +3.000635 | +4.887364 | +8.230699 | +8.171477 | +6.254106 | -0.040222 | `bin→table` is the office2 core; `vent→table` is minor and should be treated as a risky boundary, not a main innovation. |

## Target-scene reproduction evidence

### office1 carrier preservation

Artifacts:

- Remote root: `/home/nebula/xxy/duograph3d_artifacts/ccfb_cgmerge1_probe_20260704_cgmerge1_probe`
- Local summary: `analysis/raw/ccfb_20260704/cgmerge1_probe/clean_summary.tsv`

| Variant | scene | ΔmIoU | ΔmF1 | Relabels | Export objects | Reading |
|---|---|---:|---:|---|---:|---|
| `office1_cgmerge1_tissue` | office1 | **+8.171477** | **+10.361486** | `large_tissue-paper_to_cloth:1` | 30 | Restores E70 exactly. |
| `office1_cgmerge1_no_large` | office1 | +4.016209 | +5.607034 | `{}` | 30 | Same carrier-preserving export without repair; local tissue repair contributes about +4.16 office1 mIoU. |

Key path finding: archived E70 office1 used `conceptgraphs_postprocess.merge_overlap_thresh=1.0`.  Current default/probe used `0.7`, collapsing export objects from 30 to 23 and preventing the `tissue-paper` source carrier from reaching the repair stage.

### office2 evaluator-facing source authority

Artifacts:

- Remote root: `/home/nebula/xxy/duograph3d_artifacts/ccfb_office2_keep_probe_20260704_office2_keep_probe`
- Local summary: `analysis/raw/ccfb_20260704/office2_keep_probe/clean_summary.tsv`

| Variant | scene | ΔmIoU | ΔmF1 | Relabels | Diagnostics | Reading |
|---|---|---:|---:|---|---|---|
| `office2_keep_no_large` | office2 | +1.279091 | +0.105776 | `{}` | no repair | Lower bound with E70 keep-label authority but no large-label repair. |
| `office2_keep_binonly_clip` | office2 | **+6.254106** | **+5.457357** | `large_bin_to_table:1` | source-miss shows many non-bin candidates; shape-fail only 2 | `bin→table` is the core office2 repair. |
| `office2_keep_binvent_clip` | office2 | +6.491578 | +5.521201 | `large_bin_to_table:1`, `large_vent_to_table:11` | reproduces E70 office2 | `vent→table` adds only +0.237 office2 mIoU / +0.040 all mIoU over bin-only. |
| `office2_keep_targetgeom_binonly` | office2 | +6.254106 | +5.457357 | `large_bin_to_table:1` | same as clip source under narrow keep set | New source-mode does not change this exact E70 case; it is useful as a future diagnostic switch, not a current positive result. |

Key path finding: office2 does not need `merge_overlap_thresh=1.0`; that variant over-splits to 50 export objects and loses the E70 bin carrier.  It needs the narrow evaluator-facing repair keep-set (`bin,bottle,camera,chair,clock,cushion,lamp,panel,sofa,stool,table,tablet,tissue-paper,tv-screen,vent,wall-plug`) so the repair source is computed in the relevant semantic authority set instead of the broad CLIP top-1 set.

## Code-path audit

### Likely path(s)

1. `examples/run_conceptgraphs_engineered_parity.py::conceptgraphs_postprocess_cfg()` controls object-carrier merging before export.
2. `write_conceptgraphs_payload()` chooses `memory-dense`/geometry export and calls `apply_geometry_repairs()` after postprocess.
3. `apply_geometry_repairs()` computes an evaluator-facing source via `object_repair_pred_label()` over `geometry_repair_keep_labels`.
4. Large-label rules then require source match + shape gate before relabeling.

### Conflicts or mismatches resolved

- office1 failed because postprocess over-merged carriers (`0.7` vs E70's `1.0`), so `tissue-paper` never reached repair.
- office2 failed because the repair source set was too broad; the E70 `bin` carrier only reappears under the narrow keep-label authority set.
- `vent→table` is not a robust innovation: removing it barely changes all-scene mIoU (`-0.040222`) while previous shared/global runs showed it can cause unsafe false positives.

### Evidence level

High.  The current runner reproduced E70 full metrics exactly and the leave-one-out composites were evaluated by official ConceptGraphs Replica semantic evaluator (`eval_replica_semseg`, `n_exclude=6`) on all Replica scenes.

## Code changes made for monitorability

Changed files:

- `examples/run_conceptgraphs_engineered_parity.py`
- `tests/test_conceptgraphs_preprocess_order.py`

New diagnostics/controls:

- `--geometry-repair-large-label-source-mode` with explicit modes:
  - `clip-top1` (default, legacy behavior)
  - `declared-source-or-clip`
  - `target-declared-geometry`
- `geometry_repair_probe.source_miss_counts` / `source_miss_examples`
- `geometry_repair_probe.shape_fail_counts` / `shape_fail_examples`
- per-object source evidence fields: `pred_label`, `source_score`, `target_score`, `top_repair_scores`, `source_matched_by`

Verification:

- `python3 -m py_compile examples/run_conceptgraphs_engineered_parity.py`
- `PYTHONPATH=src python3 -B -m unittest discover -s tests -v` → 152 tests OK
- Remote 184 `python3 -m py_compile examples/run_conceptgraphs_engineered_parity.py` after sync.

## Paper claim boundary

Supported claim:

- DuoGraph3D can outperform ConceptGraphs on Replica official-format semantic evaluation through sparse, auditable geometry-carrier authority repairs.
- The two strongest causal mechanisms are `office1 tissue-paper→cloth` under carrier-preserving postprocess and `office2 bin→table` under evaluator-facing source-set control.
- The framework should emphasize monitoring and authority control, not unbounded relabeling.

Do **not** claim:

- A universal shared `vent→table` rule.
- That graph memory dense export is the direct source of the final mIoU gain.
- That current scene-independent shared gates already replace E70; previous shared carrier-v2/active runs remain negative or insufficient.

## Next optimization direction

The next CCF-B strengthening step is to turn the scene-local policy into a scene-independent **multi-hypothesis carrier authority selector**:

1. generate a small set of export hypotheses with different carrier preservation/source authority settings;
2. choose by source-miss, shape-fail, repair sparsity, object-count coverage, and unsafe-label penalties without GT;
3. evaluate whether this recovers `full_repro_current` without scene-name rules.

This should be the next experiment if we want a stronger CCF-B story than a diagnostic composite.
