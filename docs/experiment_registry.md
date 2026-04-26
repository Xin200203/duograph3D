# Experiment Registry

## 2026-04-26 — GT-aware layer monitor for ConceptGraphs parity

### Phase
- ConceptGraphs gap diagnosis / layer-separated GT proxy monitoring

### Remote execution
- Host: `nebula@10.177.69.184`
- Remote root: `/home/nebula/xxy/duograph3d_artifacts/duograph3d_conceptgraphs_gt_layer_monitor_20260426_v2`
- Local archive: `docs/official_results/duograph3d_conceptgraphs_gt_layer_monitor_20260426/`

### Setting
- Same Replica / GSA input setup as the ConceptGraphs parity run.
- GT target definition: semantic class + 1m GT cell proxy.
- Boundary: Replica semantic map does not provide strict instance IDs here, so ID-switch/duplicate metrics are semantic-cell proxy metrics, not true instance-ID metrics.

### Outcome
- Valid eval observations: `57191`
- Layer1 eval hypotheses: `46522`
- Layer2 valid decisions: `46522`
- Layer2 decision accuracy: `0.102274`
- Layer2 duplicate birth rate: `0.983734`
- Layer2 ID switch events: `43268`
- Layer2 GT-target fragmentation: `41746`

### Diagnosis
- Init already has substantial per-frame duplication: p50 `0.333–0.429`.
- Layer1 reduces duplication but leaves p50 `0.227–0.341`, and false-merge rate is nonzero (`0.017–0.113`), so naive aggressive merging is risky.
- Layer2 remains the dominant failure point: repeated GT semantic-cells are usually born as new memory IDs rather than associated to old IDs.
- ConceptGraphs baseline object duplicate rates are lower than DuoGraph3D exported objects, supporting the hypothesis that baseline aggregation is stronger.

### Deliverables
- `docs/official_results/duograph3d_conceptgraphs_gt_layer_monitor_20260426/README.md`
- `docs/official_results/duograph3d_conceptgraphs_gt_layer_monitor_20260426/raw/gt_layer_monitor_summary.json`
- `docs/official_results/duograph3d_conceptgraphs_gt_layer_monitor_20260426/raw/gt_layer_monitor_report.md`
- `docs/official_results/duograph3d_conceptgraphs_gt_layer_monitor_20260426/raw/run_conceptgraphs_gt_layer_monitor.py`

## 2026-04-26 — ConceptGraphs parity online-merge monitoring

### Phase
- ConceptGraphs comparison diagnosis / online merge gap attribution

### Remote execution
- Host: `nebula@10.177.69.184`
- Remote root: `/home/nebula/xxy/duograph3d_artifacts/duograph3d_conceptgraphs_monitored_20260426`
- Local archive: `docs/official_results/duograph3d_conceptgraphs_monitored_20260426/`

### Setting
- Replica scenes: `room0, room1, room2, office0, office1, office2, office3, office4`
- Inputs: official ConceptGraphs `gsa_detections_none`
- Evaluator: ConceptGraphs `eval_replica_semseg.py`, `n_exclude=6`
- DuoGraph3D variant: `temporal_naive_framewise`
- Audit boundary: no DEVA annotation masks, no GT sidecar.

### Outcome
- All-scene DuoGraph3D vs ConceptGraphs:
  - `mIoU 20.091 vs 24.531` (`Δ=-4.441`)
  - `mRecall 39.284 vs 40.216` (`Δ=-0.932`)
  - `mPrecision 43.646 vs 36.180` (`Δ=+7.466`)
  - `F-mIoU 33.588 vs 36.238` (`Δ=-2.649`)
- Worst gaps: `office3 ΔmIoU=-11.884`, `office4 ΔmIoU=-10.295`.

### Monitoring diagnosis
- Kept observations / keys / memory nodes / track fragmentation:
  - `108992 / 9116 / 85144 / 76028`
- Birth reasons:
  - `no_candidate=75022`
  - `best_candidate_without_strong_identity=10122`
- Shadow under-merge candidate pairs: `14428`.
- Low CLIP-margin observations: `87323` (~80.1% kept observations).
- Low valid-depth observations: `489` (~0.45% kept observations).

### Decision
- Primary gap source is online merge/key fragmentation, not depth/projection failure.
- Threshold-only tuning is not indicated (`best_candidate_below_threshold=0`); next experiment should target candidate retrieval / neighbor-key merge / semantic distribution keys.

### Deliverables
- `docs/official_results/duograph3d_conceptgraphs_monitored_20260426/README.md`
- `docs/official_results/duograph3d_conceptgraphs_monitored_20260426/raw/merge_monitor_summary.json`
- `docs/official_results/duograph3d_conceptgraphs_monitored_20260426/raw/merge_monitor_report.md`
- `docs/official_results/duograph3d_conceptgraphs_monitored_20260426/raw/duograph_monitored_results.csv`
- `docs/official_results/duograph3d_conceptgraphs_monitored_20260426/raw/duograph_monitored_gap_vs_conceptgraphs.csv`

## 2026-04-23 — Zero-shot baseline focus and OnlineAnySeg subset20 bring-up

### Phase
- Submission-gap closure / story-aligned zero-shot external baselines

### Main framing update
- ESAM/EmbodiedSAM is auxiliary compatibility evidence only; lack of main ESAM AP gain is not a blocker for the zero-shot paper story.
- Primary zero-shot external lanes are now **OnlineAnySeg** and **ConceptGraphs**.

### Remote execution
- All experiment execution happened on `nebula@10.177.69.184`.
- OnlineAnySeg subset20 root:
  - `/home/nebula/xxy/duograph3d_artifacts/onlineanyseg_official_subset20_sparse_20260423`
- ConceptGraphs audit root:
  - `/home/nebula/xxy/duograph3d_artifacts/conceptgraphs_minimal_20260423/conceptgraphs_scoring_path_audit_20260423.txt`

### Validation outcomes
- OnlineAnySeg official method/evaluator subset20 sparse-feature bring-up: **COMPLETED**
  - scenes: first 20 valid fullval scenes, beginning with `scene0568_00`, `scene0568_01`, `scene0568_02`, `scene0304_00`, `scene0488_00`
  - `AP / AP50 / AP25 = 0.061 / 0.138 / 0.298`
  - aggregate pred/GT instances: `335 / 572`
  - boundary: pooled dense CLIP mask embeddings + `mask_weight_threshold=1`; runnable zero-shot subset evidence, not a final full official benchmark.
- ConceptGraphs scoring-path audit: **PARTIAL PASS**
  - `conceptgraph.scripts.eval_replica_semseg`, `gradslam`, `chamferdist` import OK in `duograph-baselines-cu118`.
  - blockers: official Replica semantic scoring roots/outputs are not aligned with the current ScanNet-oriented DuoGraph3D export; `cfslam_pipeline_batch` imports `to_tensor` from the wrong upstream module.

### Deliverables
- `docs/official_results/zero_shot_baseline_focus_20260423.md`
- `docs/official_results/onlineanyseg_minimal_20260423/lane_summary.{json,md}`
- `docs/official_results/onlineanyseg_minimal_20260423/raw/subset20_sparse/*`
- `docs/official_results/conceptgraphs_minimal_20260423/lane_summary.{json,md}`
- `docs/official_results/conceptgraphs_minimal_20260423/raw/conceptgraphs_scoring_path_audit_20260423.txt`

### Next
1. Scale OnlineAnySeg beyond subset20 or generate complete official mask embeddings.
2. Resolve ConceptGraphs scoring via Replica-format export + matching semantic roots or a documented ScanNet-compatible evaluator.
3. Keep ESAM-family AP rows in auxiliary/supplementary compatibility tables only.


## 2026-04-23 — Remote env reconfiguration and submission-gap closure update

### Phase
- Submission-gap closure / remote baseline execution

### Remote execution
- All new experiment execution happened on `nebula@10.177.69.184`; local changes are documentation/artifact sync only.
- Fullval no-rescue/no-dedup independent rerun completed under:
  - `/home/nebula/xxy/duograph3d_artifacts/formal_fullval_norescue_nodedup_rerun_20260423/norescue_nodedup_strict_independent`
- OnlineAnySeg environment configured without modifying the running/base `ESAM` env:
  - `duograph-oas-cu116` cloned from `ESAM`
  - Added source-built `pytorch3d v0.7.2` and `future-fstrings`
- ConceptGraphs environment configured without modifying `conceptgraph-cu118`:
  - `duograph-baselines-cu118` cloned from `conceptgraph-cu118`
  - Added `chamferdist 1.0.3` and `gradslam 0.1.0`

### Validation outcomes
- Fullval no-rescue/no-dedup independent rerun: **COMPLETED**
  - `AP / AP50 / AP25 = 0.4135 / 0.6300 / 0.7886`
  - `312 scenes / 13430 frames`
  - Alias-only evidence gap closed; performance remains aligned with strict baseline.
- OnlineAnySeg official method/evaluator smoke: **COMPLETED**
  - `scene0568_00`, sparse-feature adapter (`83` RGB-D frames, `9` segmentation/CLIP frames)
  - `AP / AP50 / AP25 = 0.127 / 0.260 / 0.578`
  - `36 / 31` pred/GT instances
  - Boundary: executable one-scene smoke, not final fair benchmark.
- ConceptGraphs evaluator import: **PARTIAL PASS**
  - `conceptgraph.scripts.eval_replica_semseg` imports after `chamferdist`/`gradslam` repair.
  - Remaining blockers: Replica semantic GT/task mismatch for current ScanNet export; `cfslam_pipeline_batch` upstream `to_tensor` import drift.

### Deliverables
- `docs/official_results/scannet200_fullval_norescue_nodedup_rerun_20260423/*`
- `docs/official_results/scannet200_fullval_20260423/comparison_summary.{json,md}`
- `docs/official_results/onlineanyseg_minimal_20260423/lane_summary.{json,md}`
- `docs/official_results/conceptgraphs_minimal_20260423/lane_summary.{json,md}`

### Next
1. Scale OnlineAnySeg from one-scene smoke to a fixed multi-scene subset or generate complete official mask embeddings.
2. Choose ConceptGraphs scoring path: Replica-format DuoGraph3D export vs ScanNet-compatible evaluator.
3. Update manuscript claim map so fullval AP is framed as boundary evidence, not as the main gain claim.


## 2026-04-23 — Direct baseline bring-up and fullval rerun launch

### Phase
- Submission-gap closure / story-aligned external baselines

### Deliverables
- `docs/official_results/direct_baseline_bringup_20260423.md`
- `docs/official_results/onlineanyseg_minimal_20260423/lane_summary.{json,md}`
- `docs/official_results/onlineanyseg_minimal_20260423/raw/*`
- `docs/official_results/conceptgraphs_minimal_20260423/lane_summary.{json,md}`
- `docs/official_results/conceptgraphs_minimal_20260423/raw/*`
- `docs/official_results/scannet200_fullval_norescue_nodedup_rerun_20260423/job_status.md`

### Remote execution
- `OnlineAnySeg` official repo copied to 184:
  - `/home/nebula/xxy/OnlineAnySeg`
  - commit `152466e318f8220bcc6838c03e340cce2f2153b8`
- `OnlineAnySeg` evaluator smoke completed on `scene0568_00`.
- DuoGraph3D dense-sidecar export was accepted by the OnlineAnySeg evaluator.
- `ConceptGraphs` lane health was captured from:
  - `/home/nebula/xxy/concept-graphs`
  - commit `72f5962822b5e8678a446f367a06df1a977d2a4d`
- Independent fullval `no-rescue/no-dedup` rerun launched under:
  - `/home/nebula/xxy/duograph3d_artifacts/formal_fullval_norescue_nodedup_rerun_20260423/norescue_nodedup_strict_independent`

### Validation outcomes
- OnlineAnySeg evaluator smoke: **PASS**
  - selected sequences: `1`
  - missing selected sequences: `0`
  - pred / GT instances in DuoGraph3D dense-sidecar smoke: `119 / 31`
- Full OnlineAnySeg method execution: **ONE-SCENE SMOKE COMPLETED**
  - `duograph-oas-cu116` now has the Python-compatible MinkowskiEngine/FCGF stack plus source-built pytorch3d; scene0568_00 sparse-feature method/evaluator smoke completed.
- ConceptGraphs official evaluation: **IMPORT BLOCKER FIXED, TASK ALIGNMENT PENDING**
  - `chamferdist` and `gradslam` now import in `duograph-baselines-cu118`; remaining blocker is Replica evaluator / current ScanNet export alignment plus cfslam pipeline import drift.
- Fullval independent rerun: **COMPLETED**
  - metric JSON and online monitor summary are archived; AP/AP50/AP25 = 0.4135/0.6300/0.7886.

### Claim boundary
- The OnlineAnySeg AP values in this slice are **not method results**; they are GT-sidecar evaluator-bridge smoke evidence.
- A one-scene OnlineAnySeg direct-method smoke score is now archived, but no submission-ready multi-scene external direct-baseline score is claimed yet.

## 2026-04-23 — Latest experiment plan snapshot

### Purpose
- Record the current executable experiment plan after the latest AP rerun and fullval baseline-check status.

### Plan file
- Main plan document: `docs/latest_experiment_plan_20260423.md`

### Immediate next priorities
1. fullval 内核 5 格同预算收敛结果已完成；no-rescue/no-dedup 独立复验已归档。
2. 尝试并记录第一条在线 direct baseline（OnlineAnySeg）可复现实验。
3. 尝试并记录第二条 graph-memory 对手（ConceptGraphs）可复现实验。
4. 建立外部对比桥接指标（对象结构/轨迹稳定性）并与内部 main table 对齐。
5. 完成 submission hardening 的 clean-env + appendix + claim-lock 清理。 

### 2026-04-23 18:35 +0800 复核快照

- 从 `nebula@10.177.69.184` 复核了以下 run 根目录，确认实验链路与本地产物一致：  
  - `/home/nebula/xxy/3D_Reconstruction/work_dirs/ESAM_online_scannet200_CA_mv_fast_ab/fullval_baseline_dino`
  - `.../fullval_neg05_v2_rescue_only_strict_retry2`
  - `.../fullval_neg05_v2_dedup_only_strict`
  - `.../fullval_neg05_v2_rescue_all_dedup_strict`
  - `.../2601_dedup_strict_fullval`
- 全量复核结果仍显示：strict 与 no-rescue/no-dedup 为同源代理，当前主对比矩阵 5 格不含独立 no-rescue/no-dedup 重跑。
- `fullval_neg05_v2_rescue_only_strict` 首轮日志不完整，`retry2` 为正式对照；时间戳均在 2026-01-13（当前可复现版本的执行窗口）。  
- 该项已由本地文档与远端监控双重确认，进入下一步 baseline bring-up 阶段。
- 最新核对证据（2026-04-23 18:35）：  
  - `docs/official_results/scannet200_fullval_20260423/raw/remote_verification_184_20260423.md`
  - `docs/official_results/scannet200_fullval_20260423/raw/remote_verification_184_20260423.json`
  - 远端/AP 与本地产物在 AP、match_rate、birth_rate、rescue/topk_drop、scene/frame counts 与 mem_size 上均一致（容差 1e-4）。

### 2026-04-23 18:45 +0800 复核快照（二次验证）

- 从 `nebula@10.177.69.184` 对 fullval 五格主矩阵再次复核并生成新增证据：  
  - `docs/official_results/scannet200_fullval_20260423/raw/remote_verification_184_20260423_recheck.md`
  - `docs/official_results/scannet200_fullval_20260423/raw/remote_verification_184_20260423_recheck.json`
- 五格比对仍为全量一致（1e-4 容差）：`all_match=True`。
- 包含 lane：
  - `fullval_baseline_dino`（strict/aux）
  - `fullval_neg05_v2_rescue_only_strict_retry2`
  - `fullval_neg05_v2_dedup_only_strict`
  - `fullval_neg05_v2_rescue_all_dedup_strict`
  - `2601_dedup_strict_fullval`
- 复核确认：当前未检测到 184 上有新的 fullval 运行任务。

### 2026-04-23 18:50 +0800 进程核查（无新增作业）

- 通过 184 端 `ps` 与目录快检，当前未检测到在线 ESAM/fullval/OnlineAnySeg/ConceptGraphs 长时训练/评测作业。
- 184 上 fullval 缓存路径近期没有被追加新文件；本地复核证据与远端 artifact 仍保持一致。
- 实验推进仍以 `OnlineAnySeg` 最小复现可复查作为下一优先级，随后是 `ConceptGraphs`。

### 2026-04-23 18:53 +0800 复核补充（fullval 一致性再抽检）

- 复核对象扩展为 `fullval_baseline_dino`、`fullval_neg05_v2_rescue_only_strict_retry2`、`fullval_neg05_v2_dedup_only_strict`、`fullval_neg05_v2_rescue_all_dedup_strict`、`2601_dedup_strict_fullval` 的最新 timestamp 文件。
- 本地新增复核证据文件：
  - `docs/official_results/scannet200_fullval_20260423/raw/remote_verification_184_20260423_recheck3.json`
  - `docs/official_results/scannet200_fullval_20260423/raw/remote_verification_184_20260423_recheck3.md`
- `all_match=True`（1e-4 容差）；字段级结论与 18:45 次复核完全一致。
- 继续确认：当前主机无新增 fullval/OnlineAnySeg/ConceptGraphs 持续任务；主线优先级保持 `OnlineAnySeg -> ConceptGraphs`。

### 2026-04-23 18:59 +0800 复核补充（fullval 再抽检5）

- 从 `nebula@10.177.69.184` 再次抓取并比对 fullval 最新 timestamp：
  - `docs/official_results/scannet200_fullval_20260423/raw/remote_verification_184_20260423_recheck5.json`
  - `docs/official_results/scannet200_fullval_20260423/raw/remote_verification_184_20260423_recheck5.md`
- 全量比对字段：AP/AP50/AP25、scene/frame count、match_rate、birth_rate、rescued、topk_drop、mem_size。
- 结论：`all_match=True`，五格字段级一致；`remote_verification_184_20260423_recheck5` 复核通过。
- 额外核查：184 上未检测到 `OnlineAnySeg` / `ConceptGraphs` 长时进程与目录热更新痕迹；当前仍停留在既有 ESAM fullval 套件。

### Boundary
- ESAM is treated as auxiliary compatibility context unless a direct-story baseline is produced and proven.

## 2026-04-23 — Phase 0 claim freeze

### Phase
- Phase 0 — top-tier claim freeze

### Experiment status
- No new numerical experiment was run in this phase.
- This phase establishes execution governance and validation prerequisites for later experimental phases.

### Validation runs
- `python3 -m unittest discover -s tests -v`

### Validation outcomes
- Repository test suite passed: **52 tests, 0 failures**

### Notes
- Phase 0 is documentation/governance focused.
- Baseline and metric families are frozen here so later experiments can be executed against a stable submission target.

## 2026-04-23 — Phase 1 real observation path replacement

### Phase
- Phase 1 — real observation pathway replacement

### Code changes
- Added real-observation adapters for Replica DEVA outputs, generic frame observation JSON, and ScanNet online monitor JSON
- Isolated synthetic generators into explicit `to_synthetic_frame_inputs(...)` paths
- Added CLI flags to `examples/run_bounded_slice.py` for real-observation execution

### Validation runs
- `python3 -m unittest tests.test_real_observation_paths -v`
- `python3 -m unittest discover -s tests -v`
- remote validation on `nebula@10.177.69.184` using:
  - Replica DEVA JSON outputs for `office0 office1 office2 office3 office4 room0 room1 room2`
  - ScanNet online monitor JSON for `scene0568_00 scene0568_01 scene0568_02`

### Validation outcomes
- Local adapter tests passed: **4 tests, 0 failures**
- Full local suite passed: **56 tests, 0 failures**
- Nonempty real-observation scenes verified: **6**
  - Replica: `office0`, `office2`, `office3`
  - ScanNet: `scene0568_00`, `scene0568_01`, `scene0568_02`

### Notes
- Phase 1 exit criteria are satisfied, but the ScanNet monitor-based path still carries semantic-strength risk for later paper-grade phases.

## 2026-04-23 — Phase 2 method strengthening

### Phase
- Phase 2 — method strengthening toward explicit graph / geometry support

### Code changes
- Added explicit memory relation edges and co-visibility tracking
- Upgraded layer-1 from grouping-only repair to evidence-graph compatibility repair
- Added explicit geometry-profile consistency, dual-consistency gating, and relation-aware association bonus in layer-2
- Exposed relation-edge count through run summaries

### Validation runs
- `python3 -m unittest tests.test_pipeline -v`
- `python3 -m unittest discover -s tests -v`
- `PYTHONPATH=src python3 examples/minimal_sequence.py`
- remote real-observation regression on `office0` and `scene0568_00`

### Validation outcomes
- Local pipeline tests passed: **12 tests, 0 failures**
- Full local suite passed: **60 tests, 0 failures**
- Remote ScanNet real-observation regression produced nonzero `memory_relation_edge_count = 1797` on `scene0568_00`

### Notes
- Phase 2 materially strengthens the code-level grounding of the graph-memory claim, but does not yet replace later paper-grade quantitative evaluation.

## 2026-04-23 — Phase 3 external baseline system build-out

### Phase
- Phase 3 — reviewer-credible external baseline system build-out

### Code changes
- Added official ESAM target metadata and ESAM result summarization support
- Added baseline raw-artifact capture and normalized generated summaries for DEVA and ESAM

### Validation runs
- `python3 -m unittest tests.test_external_baselines tests.test_esam_results -v`
- `python3 -m unittest discover -s tests -v`
- remote provenance audit for official repos / commits / execution artifact paths

### Validation outcomes
- Targeted baseline tests passed: **3 tests, 0 failures**
- Full local suite passed: **62 tests, 0 failures**
- Formalized external baseline families with normalized artifacts: **2**
  - DEVA official offline
  - ESAM / EmbodiedSAM official-family ScanNet-MV lane

### Notes
- The ESAM lane is currently documented as an official-family fork-executed lane with explicit provenance caveat, not hidden as a pure official-rerun claim.

- Unified external baseline matrix generated for comparison-ready lane inventory.
- Official ESAM rerun was attempted from the official checkout and failed due to environment drift (`ultralytics.yolo` import mismatch).

## 2026-04-23 — Phase 4 paper-candidate metric layer

### Phase
- Phase 4 — paper-grade metrics and result package (in progress)

### Validation runs
- `python3 -m unittest tests.test_observation_metrics -v`
- `python3 -m unittest tests.test_runner -v`
- `python3 -m unittest discover -s tests -v`
- remote `examples/run_phase4_candidate_package.py`
- remote `examples/run_phase4_regime_matrix.py`

### Validation outcomes
- Full local suite passed: **64 tests, 0 failures**
- Real-observation regime matrix generated: **24 scene-level rows across 4 regimes**
- Observation-grounded metrics are now captured in a stable JSON/Markdown package
- Phase 4 analysis artifacts generated: main-table candidate, ablation table candidate, worst/best analysis, failure casebook.
- Broadened Phase 4 regime matrix generated: **44 scene-level rows across 4 regimes**.
- Phase 4 representative casebook and broad analysis artifacts generated.
- Phase 4 paper-candidate table bundle generated: internal regime table, ablation table, and external family table.
- Phase 4 readiness summary generated: candidate package complete, paper-grade candidate still false.
- Legacy proxy review generated: legacy proxy gates are now evidence-backed historical-reference candidates for the broad Phase 4 package.
- Updated Phase 4 readiness now reports: candidate package complete = Yes, paper-grade candidate = Yes.
- Phase 4 documentation reconciled: checkpoint/package/mapping/readiness now consistently treat the package as an internal paper-grade candidate rather than a final camera-ready package.

## 2026-04-23 — Phase 5 manuscript drafting start

### Phase
- Phase 5 — manuscript and figure drafting (started)

### Deliverables
- `docs/manuscript/phase5_paper_draft.md`
- `docs/manuscript/phase5_figure_checklist.md`

### Notes
- Phase 5 has started from the completed Phase 4 candidate package and is now building the written paper shell.
- Phase 5 reviewer-defense pack, figure specs, claim-evidence map, and caption bank generated.
- Phase 5 section-completion matrix and table-spec assets generated.
- Phase 5 appendix draft and submission asset manifest generated.
- Phase 5 concrete figure assets rendered and a fresh PDF manuscript draft compiled successfully.

## 2026-04-23 — Phase 5 completion review

### Phase
- Phase 5 — manuscript and figure/table assets

### Validation runs
- `python3 -m unittest discover -s tests -v`
- fresh XeLaTeX build of `docs/manuscript/phase5_paper_draft.tex`

### Validation outcomes
- Full local suite passed: **71 tests, 0 failures**
- Fresh PDF draft build passed
- Concrete figure asset set exists
- Phase 5 checkpoint written and ready for architect review

## 2026-04-23 — Story-aligned experiment protocol correction

### Phase
- Planning / manuscript protocol correction

### Deliverables
- `docs/story_aligned_experiment_setup.md`
- revised `.omx/plans/prd-duograph3d-benchmark-main-table.md`
- revised `.omx/plans/test-spec-duograph3d-benchmark-main-table.md`

### Notes
- The previous AP/ESAM-first framing has been explicitly downgraded as an unreasonable primary experiment story.
- ESAM / EmbodiedSAM is now recorded as an auxiliary benchmark-compatibility reference rather than the main direct-baseline family.
- Main comparisons are now grouped by innovation row: direct zero-shot online 3D neighbors, temporal backbone, two-layer necessity, and graph-memory/object-maintenance.
## 2026-04-23 — Prioritized baseline execution roadmap

### Phase
- Planning / baseline execution prioritization

### Deliverables
- `docs/baseline_execution_roadmap.md`

### Notes
- Baseline bring-up is now explicitly prioritized by story fit, execution readiness, metric usefulness, and integration cost.
- First runnable external direct-neighbor target: `OnlineAnySeg`.
- First runnable external graph-memory target: `ConceptGraphs`.
- `ESAM / EmbodiedSAM` remains an auxiliary compatibility lane and is not scheduled as the next primary bring-up target.
## 2026-04-23 — OnlineAnySeg / ConceptGraphs output alignment

### Phase
- Story-aligned external evaluator output alignment

### Deliverables
- `src/duograph3d/alignment_exports.py`
- `examples/export_alignment_outputs.py`
- `tests/test_alignment_exports.py`
- `docs/alignment_output_protocol.md`

### Validation outcomes
- Targeted alignment tests passed: **2 tests, 0 failures**
- Full local suite passed with alignment tests included: **73 tests, 0 failures**

### Notes
- Exports currently align file/schema contracts but are marked proxy-geometry and not official-evaluation-ready.
- The next technical blocker is dense point/mask assignment in DuoGraph3D observation and memory outputs.


## 2026-04-23 — Dense sidecar alignment bridge

### Goal
Move the external-evaluator alignment layer from proxy-only format generation toward a real evaluation bridge that can consume dense point assignments when available.

### Artifacts
- `src/duograph3d/alignment_exports.py`
- `examples/export_alignment_outputs.py`
- `tests/test_alignment_exports.py`
- `docs/alignment_output_protocol.md`
- `docs/alignment_exports/dense_fixture/`

### Current result
- OnlineAnySeg export can now use real `points` + object `point_indices` to write `final.ply` and `ckpt_final.npz` masks.
- ConceptGraphs export can now use the same dense assignments to write object `pcd_np`, colors, bbox, semantic labels, and CLIP/text features.
- Manifest states distinguish `format_aligned_proxy_geometry`, `format_aligned_dense_geometry`, and `format_aligned_official_ready`.

### Evidence
- Targeted alignment tests passed: **4 tests, 0 failures**.
- Dense fixture manifest reports `format_aligned_official_ready` for both adapters because the fixture declares GT alignment plus required semantic/features metadata.

### Boundary
- This is not a performance benchmark result. It only validates that real dense assignments can be carried into evaluator-compatible file surfaces.

### Additional verification
- Full local suite with dense alignment bridge included: **75 tests, 0 failures**.

## 2026-04-23 — ScanNet200 fullval official AP rerun (ESAM-family compatible 5-cell matrix)

### Dataset / evaluator
- Dataset: ScanNet200 full validation (`scannet200_mv_oneformer3d_infos_val.pkl`)
- Evaluator: MMEngine / UnifiedSegMetric category-agnostic instance AP
- Metrics: `all_ap`, `all_ap_50%`, `all_ap_25%`

### Artifacts
- Candidate set: `docs/official_results/scannet200_fullval_20260423/raw/`（含 strict / no-rescue / rescue-only / dedup-only / rescue+dedup / aux）
- 基准对比产物：`docs/official_results/scannet200_fullval_20260423/comparison_summary.json`
- Comparison JSON: `docs/official_results/scannet200_fullval_20260423/comparison_summary.json`
- Comparison table: `docs/official_results/scannet200_fullval_20260423/comparison_summary.md`
- Report: `docs/official_results/scannet200_fullval_20260423/result_report.md`

### Fresh result
- ESAM online context baseline（strict）：`AP 0.4135 / AP50 0.6300 / AP25 0.7886`（312 scenes, 13430 frames）。
- DuoGraph-style rescue-only：`AP 0.4133 / AP50 0.6286 / AP25 0.7897`（312 scenes, 13430 frames）。
- DuoGraph-style dedup-only：`AP 0.4133 / AP50 0.6244 / AP25 0.7797`（312 scenes, 13430 frames）。
- DuoGraph-style rescue+dedup：`AP 0.4051 / AP50 0.6139 / AP25 0.7708`（312 scenes, 13430 frames）。
- ESAM-family 诊断变体 `2601_dedup_strict_fullval`：`AP 0.3985 / AP50 0.6024 / AP25 0.7624`。

### Claim boundary
- 这批 fullval 实验主结论是：ESAM baseline 与 strict 变体为最优；rescue-only / dedup-only 与其接近、rescue+dedup 略差，说明 fullval 直接胜负尚未形成。
- 当前价值更偏执行健壮性与监控可复现性，不宜单独上主表。

### Next required follow-up
- Keep this run for pipeline robustness evidence.
- 本轮已形成 5 格预算对照（no-rescue/no-dedup 使用 strict 复用）；下一步补一条独立同预算同配置 no-rescue/no-dedup 复验命令，避免复用争议。

### Additional verification
- Latest local full suite remains green: **76 tests, 0 failures**.


## 2026-04-23 — ScanNet200 subset5 official AP comparison

### Dataset / evaluator
- Dataset: ScanNet200 subset5 (`scannet200_mv_oneformer3d_infos_val_subset5.pkl`)
- Evaluator: MMEngine / UnifiedSegMetric category-agnostic instance AP
- Metrics: `all_ap`, `all_ap_50%`, `all_ap_25%`

### Artifacts
- Raw metrics: `docs/official_results/scannet200_subset5_20260423/raw/`
- Comparison JSON: `docs/official_results/scannet200_subset5_20260423/comparison_summary.json`
- Comparison table: `docs/official_results/scannet200_subset5_20260423/comparison_summary.md`
- Report: `docs/official_results/scannet200_subset5_20260423/result_report.md`

### Fresh result
- ESAM online baseline subset5：`AP 0.5146 / AP50 0.7348 / AP25 0.8508`（5 scenes）。
- DuoGraph-style rescue+dedup subset5：`AP 0.5330 / AP50 0.7561 / AP25 0.8837`（5 scenes）。
- Delta（duograph3d - ESAM）：`+0.0183 / +0.0213 / +0.0329`。

### Claim boundary
- 子集结果仍是有效对照，但非主表 final；需要 fullval 与外部 direct baseline 联合证据后才可进入主表。

### Additional verification
- Result rendering regression test added and passed.
- Full local suite with official-result renderer included: **76 tests, 0 failures**.


## 2026-04-23 — OnlineAnySeg AP audit and protocol correction

### Phase
- External zero-shot baseline correction / official reproduction recovery

### Remote artifacts
- Sparse fullval bridge: `/home/nebula/xxy/duograph3d_artifacts/onlineanyseg_official_fullval_sparse_20260423`
- Official Step-1 setup root: `/home/nebula/xxy/duograph3d_artifacts/onlineanyseg_official_repro_setup_20260423`
- Official OnlineAnySeg repo: `/home/nebula/xxy/OnlineAnySeg` at commit `152466e318f8220bcc6838c03e340cce2f2153b8`

### Findings
- The low OnlineAnySeg fullval number (`0.054 / 0.124 / 0.260`, `310/312` scenes) is now classified as a sparse-feature bridge result, not an official reproduction.
- Official reproduction requires CropFormer+CLIP mask generation before OnlineAnySeg 3D fusion; that path is being configured under the remote setup root.
- DuoGraph3D has ESAM-compatible ScanNet200 fullval evidence, but no claim is made yet for DuoGraph3D under exact OnlineAnySeg/ConceptGraphs official protocols.

### Next required follow-up
- Complete official OnlineAnySeg Step-1 checkpoint/build, run a small official subset, then scale.
- Finish ConceptGraphs Replica official chain and evaluate.
- Export/evaluate DuoGraph3D under the same downstream protocol instead of only reporting reproduced baselines.

### Automation launched
- ConceptGraphs post-GSA supervisor: `/home/nebula/xxy/duograph3d_artifacts/conceptgraphs_replica_official_20260423/continue_after_gsa.sh`.
- OnlineAnySeg official one-scene supervisor: `/home/nebula/xxy/duograph3d_artifacts/onlineanyseg_official_cropformer_scene0568_20260423/run_after_resources.sh`.
- CropFormer checkpoint download source fallback: Google Drive file id `10G7s6bVMwN__bcrR2fBal3goo69Y5Do4` because the official Hugging Face dataset is gated and returned 401 without accepted credentials.


## 2026-04-24 — DuoGraph3D real ConceptGraphs subset evaluation

### Phase
- External graph/object-memory comparison: method-side real evaluation

### Artifacts
- `docs/official_results/duograph3d_conceptgraphs_real_subset_20260424.md`
- remote root: `/home/nebula/xxy/duograph3d_artifacts/duograph3d_conceptgraphs_real_subset_20260424`

### Findings
- First real executed DuoGraph3D -> ConceptGraphs semantic-evaluation score obtained on the current non-empty Replica real-observation subset (`office0`, `office2`, `office3`).
- DuoGraph3D subset aggregate: `mIoU 0.8032 / mRecall 3.7921 / mPrecision 0.9019 / mF1 0.9155 / F-mIoU 2.9930`.
- Official ConceptGraphs baseline on the same subset remains much higher: `mIoU 22.9524 / mRecall 40.0660 / mPrecision 30.9236 / mF1 27.8507 / F-mIoU 35.5410`.
- Current gap source is now explicit: the current DuoGraph3D Replica real-observation package emits only one object on each non-empty scene and stays empty on five of the eight official Replica scenes.

### Boundary
- This is a real evaluator result, not GT-sidecar smoke.
- It is still a non-empty subset comparison, not yet a full 8-scene parity row.


## 2026-04-24 — Corrected DuoGraph3D / ConceptGraphs GSA parity evaluation

### Phase
- External graph/object-memory comparison: corrected same-setting full Replica row

### Artifacts
- Report: `docs/official_results/duograph3d_conceptgraphs_gsa_parity_20260424/README.md`
- Raw DuoGraph3D CSV: `docs/official_results/duograph3d_conceptgraphs_gsa_parity_20260424/raw/duograph_gsa_parity_results.csv`
- Raw summary JSON: `docs/official_results/duograph3d_conceptgraphs_gsa_parity_20260424/raw/duograph_gsa_parity_summary.json`
- Run log: `docs/official_results/duograph3d_conceptgraphs_gsa_parity_20260424/raw/run_gsa_parity_eval.log`
- Remote root: `/home/nebula/xxy/duograph3d_artifacts/duograph3d_conceptgraphs_gsa_parity_20260424`

### Protocol correction
- Supersedes the earlier non-empty DEVA-candidate subset as the main ConceptGraphs parity row.
- Uses the same official ConceptGraphs Replica scene list, `gsa_detections_none`, `eval_replica_semseg`, and `n_exclude=6` setting.
- Uses `temporal_naive_framewise` for the DuoGraph3D pass because the target protocol is ConceptGraphs GSA parity, not the DEVA-style carry-over setting.

### Findings
- DuoGraph3D all-scene parity aggregate: `mIoU 20.0908 / mRecall 39.2840 / mPrecision 43.6455 / mF1 27.9607 / F-mIoU 33.5883`.
- ConceptGraphs all-scene official baseline: `mIoU 24.5313 / mRecall 40.2156 / mPrecision 36.1800 / mF1 30.1223 / F-mIoU 36.2376`.
- DuoGraph3D is below ConceptGraphs on aggregate mIoU by `-4.4405` percentage points, but has higher aggregate precision.
- Diagnostics show high internal DuoGraph3D track fragmentation; exported object maps intentionally anchor one object per stable GSA observation key.

### Boundary
- This is the completed same-setting ConceptGraphs parity result for the current adapter.
- It should be reported with its adapter/export boundary, not as proof that long-horizon memory fragmentation is solved.
