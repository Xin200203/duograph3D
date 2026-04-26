# Agent Worklog

## 2026-04-23T03:40:36Z — Ralph execution start

### Active execution plan
- `top_tier_submission_roadmap.md`

### Completed actions
- Read repository `AGENTS.md`
- Read approved roadmap
- Created Ralph context snapshot
- Created required Ralph planning-gate artifacts:
  - `.omx/plans/prd-duograph3d-top-tier-submission.md`
  - `.omx/plans/test-spec-duograph3d-top-tier-submission.md`
- Executed Phase 0 deliverable work:
  - `docs/submission_lock.md`
  - initialized docs registry/log files required after each phase

### Current status
- Phase 0 deliverables drafted
- Repository test validation completed: `52 tests, OK`
- Architect review round 1 returned **REVISE**
- Applied Phase 0 fixes:
  - recorded actual validation outcomes
  - removed ambiguity around strong graph/geometry claim freeze
  - harmonized the decision log with the frozen strong-claim decision
  - completed re-review for final Phase 0 exit decision
- Architect review round 2 returned **APPROVED**
- Phase 0 exit criteria satisfied

## 2026-04-23T04:00:00Z — Phase 1 execution

### Completed actions
- Implemented real-observation adapters in `src/duograph3d/data.py`
- Added explicit synthetic-path naming via `to_synthetic_frame_inputs(...)`
- Added Replica DEVA-output path and ScanNet online-monitor path
- Extended `examples/run_bounded_slice.py` for real-observation execution flags
- Fixed `examples/remote_smoke_test.py` ScanNet label handoff bug
- Added adapter regression coverage in `tests/test_real_observation_paths.py`
- Ran remote validation against available real artifacts on `nebula@10.177.69.184`

### Validation summary
- Targeted adapter tests: PASS
- Full local unit suite: PASS
- Remote real-observation validation: PASS
  - 6 nonempty scenes total

### Current status
- Phase 1 exit criteria satisfied
- Architect review returned **APPROVED**
- Ready to enter Phase 2

## 2026-04-23T04:20:00Z — Phase 2 execution

### Completed actions
- Added explicit memory relation edges and co-visibility registration
- Reworked layer-1 into an evidence-graph repair stage with compatibility reasons
- Added explicit geometry-profile consistency and dual-consistency gating in layer-2
- Added relation-aware candidate scoring in layer-2
- Extended pipeline summaries to report relation-edge counts
- Added Phase 2 pipeline regression tests
- Ran local and remote validation

### Validation summary
- Local pipeline tests: PASS (`12 tests, 0 failures`)
- Full local suite: PASS (`60 tests, 0 failures`)
- Local minimal sequence smoke: PASS
- Remote real-observation regression: PASS
  - ScanNet `scene0568_00` activated `memory_relation_edge_count = 1797`

### Current status
- Phase 2 exit criteria satisfied
- Architect review returned **APPROVED**
- Ready to enter Phase 3

## 2026-04-23T04:40:00Z — Phase 3 blocker

### Status
- Phase 3 cannot be completed inside the current execution boundary.

### Blocker summary
- Only the DEVA lane currently satisfies reviewer-credible external-baseline provenance.
- Additional accessible artifacts were found (notably remote ScanNet online-monitor outputs), but they are not yet backed by an official baseline repo/command path/documented contract sufficient for top-tier comparison claims.

### Blocker report
- `docs/blockers/phase3_external_baselines_blocker.md`

## 2026-04-23T05:00:00Z — Phase 3 execution

### Completed actions
- Audited remote official repositories and commits for ESAM and ConceptGraphs
- Captured DEVA and ESAM raw result artifacts into local docs-managed storage
- Added ESAM official target + executed-lane summarization code
- Generated local normalized result files for DEVA and ESAM
- Wrote external baseline inventory and Phase 3 checkpoint

### Validation summary
- Targeted baseline tests: PASS (`3 tests, 0 failures`)
- Full local suite: PASS (`62 tests, 0 failures`)
- Two external baseline families now have formalized local result artifacts

### Current status
- Phase 3 exit criteria satisfied
- Architect review returned **APPROVED**
- Ready to enter Phase 4

- Generated unified external baseline matrix artifacts for DEVA + ESAM lanes
- Attempted direct official ESAM rerun from `/home/nebula/xxy/ESAM`; blocked by official-environment import drift (`ultralytics.yolo`)

## 2026-04-23T05:20:00Z — Phase 4 ongoing work

### Completed actions
- Added observation-grounded metric extraction and rendering
- Added real-observation candidate package runner and regime-matrix runner
- Enabled custom replica-scene subsets in suite specs
- Ran a fresh real-observation regime matrix on remote infrastructure
- Captured Phase 4 candidate package summaries locally
- Froze the first paper-candidate metric lock

### Fresh evidence
- Full local suite: PASS (`64 tests, 0 failures`)
- Remote matrix package: PASS (generated)
- Scene-level rows in matrix package: `24`
- Old proxy pass gates still red: `all_scenes_pass=False`, `all_regimes_pass=False`

### Current status
- Phase 4 remains in progress
- Current package is nonempty and real-observation grounded, but exit criteria are not yet satisfied
- Generated Phase 4 analysis surfaces: main-table candidate, ablation table candidate, worst/best analysis, failure casebook
- Phase 4 still in progress; analysis surfaces now exist but final paper-grade exit criteria remain unmet
- Broadened the Phase 4 regime matrix to 44 scene-level rows
- Generated broad-analysis artifacts plus a representative casebook
- Inspected mature adjacent work (ESAM, ConceptGraphs) to map future Phase 4 metric upgrades
- Generated `docs/phase4_paper_candidate_tables.md` to consolidate Phase 4 internal/external table surfaces
- Generated structured Phase 4 readiness summary: candidate package complete, paper-grade candidate still false
- Built and verified a legacy-proxy review for the broad Phase 4 package
- Regenerated Phase 4 readiness with proxy-transition evidence: candidate package complete = Yes, paper-grade candidate = Yes
- Reconciled Phase 4 checkpoint/package/readiness language so all artifacts consistently mark Phase 4 as internal paper-grade candidate complete
- Architect review returned **APPROVED** for Phase 4
- Ready to enter Phase 5

## 2026-04-23T06:00:00Z — Phase 5 start

### Completed actions
- Opened the Phase 5 manuscript lane
- Wrote a first manuscript draft grounded in completed Phase 0–4 artifacts
- Wrote a figure checklist seeded by current casebooks and table artifacts

### Current status
- Phase 5 is now in progress
- Draft exists, but manuscript completion criteria are not yet satisfied
- Added Phase 5 reviewer-defense pack, claim-evidence map, figure specs, and caption bank
- Expanded the paper draft with more concrete results and writing-side safeguards
- Added Phase 5 table specs and section-completion matrix
- Expanded the draft with more explicit asset-linkage and anti-overclaim writing guidance
- Added Phase 5 appendix draft and submission asset manifest
- Section completion matrix now covers manuscript, supplementary, and packaging assets
- Rendered concrete Phase 5 figure assets and compiled a fresh PDF draft
- Figure plan and PDF build now have asset-rendered status

## 2026-04-23T06:40:00Z — Phase 5 completion review prep

### Completed actions
- Promoted figure/table plans into asset-backed manuscript surfaces
- Verified fresh PDF draft build after figure embedding updates
- Wrote a formal Phase 5 checkpoint

### Current status
- Phase 5 checkpoint is ready for architect verification

## 2026-04-23T12:30:00+08:00 — Story-aligned experiment correction

### Completed actions
- Re-audited the paper story against the frozen innovation points
- Rejected the earlier AP/ESAM-first experimental framing as the primary direct-baseline plan
- Wrote `docs/story_aligned_experiment_setup.md`
- Revised planning and manuscript-facing docs so ESAM/EmbodiedSAM is auxiliary-only rather than the main identity-defining comparison family

### Current status
- The experiment protocol is now explicitly organized around online 3D matching, two-layer structure, and object maintenance
- Direct task neighbors are now planned around OnlineAnySeg-style and graph/mapping-alternative families rather than learning-based instance-segmentation-first comparisons
## 2026-04-23T12:50:00+08:00 — Prioritized baseline roadmap

### Completed actions
- Audited local availability of story-aligned baseline repositories
- Verified local official clones for OnlineAnySeg and ConceptGraphs
- Wrote `docs/baseline_execution_roadmap.md`
- Linked the new roadmap to the story-aligned experiment protocol

### Fresh evidence
- OnlineAnySeg local clone available at `/Users/xin/Research/project/3D重建/repos/conceptgraph_family/OnlineAnySeg`
- OnlineAnySeg local commit: `152466e318f8220bcc6838c03e340cce2f2153b8`
- ConceptGraphs local clone available at `/Users/xin/Research/project/3D重建/repos/conceptgraph_family/concept-graphs`
- ConceptGraphs local commit: `93277a02bd89171f8121e84203121cf7af9ebb5d`

### Current status
- The baseline roadmap is now prioritized by story fit and readiness
- OnlineAnySeg is the first external direct-neighbor lane to bring up
- ConceptGraphs is the second external lane to bring up
- ESAM remains auxiliary-only
## 2026-04-23T13:10:00+08:00 — Output alignment implementation

### Completed actions
- Added `src/duograph3d/alignment_exports.py`
- Added `examples/export_alignment_outputs.py`
- Added `tests/test_alignment_exports.py`
- Wrote `docs/alignment_output_protocol.md`
- Generated a demo alignment export manifest from the existing local bounded-slice report

### Current status
- OnlineAnySeg-style `final.ply` + `ckpt_final.npz` surface is implemented
- ConceptGraphs-style `full_pcd_<exp>.pkl.gz` surface is implemented
- Both surfaces are explicitly marked `official_evaluation_ready = false` until dense geometry assignments are available


## 2026-04-23T16:45:00+08:00 — Dense output-alignment bridge

### Scope
- Continued the OnlineAnySeg / ConceptGraphs output-format alignment layer.
- Added optional dense geometry sidecar ingestion to avoid conflating placeholder geometry with formal benchmark evidence.

### Code changes
- Extended `src/duograph3d/alignment_exports.py` with:
  - dense sidecar parsing for `points`, `colors`, `objects[].point_indices`, semantic ids, scores, and CLIP/text features
  - ASCII PLY point-cloud reader for dependency-free bridge usage
  - dense-mask construction for OnlineAnySeg `ckpt_final.npz`
  - dense object point-cloud serialization for ConceptGraphs `full_pcd_*.pkl.gz`
  - manifest readiness flags and explicit status transitions
- Extended `examples/export_alignment_outputs.py` with `--geometry`.
- Extended `tests/test_alignment_exports.py` with dense official-ready surface tests.

### Verification
- Targeted alignment tests: `PYTHONPATH=src python3 -m unittest tests.test_alignment_exports -v` → 4 tests, OK.
- Generated dense fixture export under `docs/alignment_exports/dense_fixture/exports/`.

### Remaining risk
- The fixture proves schema and writer behavior only. Real benchmark numbers still require generating dense sidecars from actual scene reconstructions / object tracks and then running external evaluators with matching GT roots.

### Additional verification — 2026-04-23T16:50:00+08:00
- Full regression suite: `python3 -m unittest discover -s tests -v` → 75 tests, OK.

## 2026-04-23T17:05:00+08:00 — First formal ScanNet200 subset AP result

### Completed
- Reran a strict ESAM online baseline on ScanNet200 subset5 with category-agnostic AP.
- Reran a DuoGraph-style object-maintenance candidate (`rescue+dedup`) on the same subset and evaluator protocol.
- Copied raw metric JSON and monitor summaries into `docs/official_results/scannet200_subset5_20260423/raw/`.
- Added result rendering code and generated `comparison_summary.{json,md}`.

### Fresh result
- Baseline: AP 0.5146 / AP50 0.7348 / AP25 0.8508.
- Candidate: AP 0.5330 / AP50 0.7561 / AP25 0.8837.
- Delta: AP +0.0183 / AP50 +0.0213 / AP25 +0.0329.

### Boundary
- This is a formal evaluator-backed subset result, not a final full-validation main-table claim.

### Additional verification — 2026-04-23T17:08:00+08:00
- Targeted result-rendering tests: `PYTHONPATH=src python3 -m unittest tests.test_official_results tests.test_alignment_exports -v` → 5 tests, OK.
- Full local suite: `python3 -m unittest discover -s tests -v` → 76 tests, OK.

## 2026-04-23T18:35:00+08:00 — Fullval 184复核与计划合并

### Completed actions
- 复核远端 `nebula@10.177.69.184` 上 ESAM-family fullval 结果与本地成果的一致性：
  - `fullval_baseline_dino`
  - `fullval_neg05_v2_rescue_only_strict_retry2`
  - `fullval_neg05_v2_dedup_only_strict`
  - `fullval_neg05_v2_rescue_all_dedup_strict`
  - `2601_dedup_strict_fullval`
- 确认远端 `online_monitor_summary.json` 的核心数值与 `docs/official_results/scannet200_fullval_20260423/raw/*` 对齐。
- 将最新复核状态更新到：
  - `docs/blockers/phase3_external_baselines_blocker.md`
  - `docs/latest_experiment_plan_20260423.md`
  - `docs/experiment_registry.md`

### 结果结论（R0）
- 当前 fullval 仍是 ESAM-online harness 的配置消融，而非“新训练的 ESAM 原型重训练”。
- 核心对照中 fullval 主表仍处于**可复用但未决**状态：无独立同预算 `no-rescue/no-dedup` 命令补充，ESAM strict 仅作为等价代理。
- 外部投稿主线仍然等待 OnlineAnySeg + ConceptGraphs 的可复现官方带分数输出。

## 2026-04-23T18:47:00+08:00 — 184 全量复核证据落地

### Completed
- 重新从 `nebula@10.177.69.184` 拉取 fullval5 配置的五条运行目录和对应 monitor-summary，确认时间戳与文件完整性：
  - `fullval_baseline_dino`
  - `fullval_neg05_v2_rescue_only_strict_retry2`
  - `fullval_neg05_v2_dedup_only_strict`
  - `fullval_neg05_v2_rescue_all_dedup_strict`
  - `2601_dedup_strict_fullval`
- 自动生成远端-本地核对报告：
  - `docs/official_results/scannet200_fullval_20260423/raw/remote_verification_184_20260423.json`
  - `docs/official_results/scannet200_fullval_20260423/raw/remote_verification_184_20260423.md`

### Verification result
- 核对口径：AP、`match_rate`、`birth_rate`、`rescued`、`topk_drop`、`mem_size_full`、`mem_size_kept`、scene/frame counts（time 允许 1e-4 近似）。
- 结果：5 格全通过（`match=True`）。

### Boundary
- 本轮结果支持结论：当前 184 上正运行的是 ESAM-online fullval 系列配置消融，不是新训练的 ESAM 模型；下一步仍聚焦 OnlineAnySeg/ConceptGraphs 的可复现官方评分链路。

## 2026-04-23T18:45:00+08:00 — 184 fullval recheck refresh（新增快照）

### Completed
- 再次从 184 端抽取并比对 `fullval_strict`、`rescue-only`、`dedup-only`、`rescue+dedup`、`dedup-strict` 5 条 lane 的 metric + monitor 关键字段，与 `docs/official_results/scannet200_fullval_20260423/raw/*` 一致对齐。
- 生成新增复核证据文件：
  - `docs/official_results/scannet200_fullval_20260423/raw/remote_verification_184_20260423_recheck.json`
  - `docs/official_results/scannet200_fullval_20260423/raw/remote_verification_184_20260423_recheck.md`

### Verification result
- 对齐口径同前（字段级：AP/AP50/AP25/time + scenes/frames + match_rate/birth_rate/rescued/topk_drop + mem_size*），容差 1e-4。
- `all_match=True`（5 格全部一致）。

### Boundary
- 当前仍无新实验输出任务在 184 上继续运行；下一步继续推进 OnlineAnySeg/ConceptGraphs bring-up。

## 2026-04-23T18:50:20+08:00 — 184 空档核查与执行次序确认

### Completed
- 184 主机进程核查（关键词：ESAM / fullval / OnlineAnySeg / ConceptGraphs / duograph）未检测到新的持续任务。
- 复核远端 `/home/nebula/xxy/3D_Reconstruction/work_dirs/ESAM_online_scannet200_CA_mv_fast_ab` 下核心 fullval 目录最近文件结构未新增新 run 目录。
- 已再次核对本地 `docs/experiment_registry.md` 与 `docs/latest_experiment_plan_20260423.md` 反映当前“空档 + 切到外部基线 bring-up”的状态。

### Impact
- 结论：本阶段可复现实验资源暂未增长；继续沿 `OnlineAnySeg` -> `ConceptGraphs` 的可复现对齐顺序推进下一步实验。

## 2026-04-23T18:53:00+08:00 — 184 fullval 再复核（三）与证据补齐

### Completed
- 再次在 184 端抽取 fullval 目录的最新 timestamp metric/monitor（5 格全部）做本地重对齐核查，更新：
  - `docs/official_results/scannet200_fullval_20260423/raw/remote_verification_184_20260423_recheck3.json`
  - `docs/official_results/scannet200_fullval_20260423/raw/remote_verification_184_20260423_recheck3.md`

### Verification result
- 复核口径（AP/AP50/AP25 + scenes/frames + match_rate/birth_rate/rescued/topk_drop/mem_size）与先前保持一致，容差 1e-4。
- 全部 lane 一致：`all_match=True`。

### Process check
- 再次执行 `ps` 关键字核查，仍仅观察到系统级进程，未见新增 ESAM/OnlineAnySeg/ConceptGraphs 长时训练/评测任务。
- 复核后目录快检显示 fullval 运行目录文件清单与既有 artifact 与时间戳未新增偏移（远端执行窗口仍停留在 `2026-01-13` 路径版本）。

## 2026-04-23T18:59:00+08:00 — 184 fullval recheck5 脚本化核验落档

### Completed
- 使用脚本直接抓取远端 `fullval` 最新 timestamp 的 metric 与 online_monitor_summary（5 格）并与本地 `docs/official_results/scannet200_fullval_20260423/raw/*` 对齐核对。
- 新增证据落盘：
  - `docs/official_results/scannet200_fullval_20260423/raw/remote_verification_184_20260423_recheck5.json`
  - `docs/official_results/scannet200_fullval_20260423/raw/remote_verification_184_20260423_recheck5.md`
- 扩展核验项：字段级比对包含 AP/AP50/AP25、scene/frame、match_rate、birth_rate、rescued、topk_drop、mem_size_full/kept。

### Verification result
- `all_match=True`（1e-4 容差）且与 18:53 结果完全一致。
- 补充核查：184 上未检测到在线 `OnlineAnySeg`/`ConceptGraphs` 长任务或新 fullval 产物目录追加。

## 2026-04-26T21:15:00+08:00 — ConceptGraphs GT-aware layer analysis record

### Context
- User pointed out that the previous monitor was not detailed enough and that available GT should be used to separate:
  - single-frame initialization duplication,
  - post-Layer1 duplication/error,
  - Layer2 correctness / ID switch,
  - baseline-side probability and duplicate behavior.
- Added and ran a GT-aware layer monitor on the same ConceptGraphs parity setup.
- Local archive:
  - `docs/official_results/duograph3d_conceptgraphs_gt_layer_monitor_20260426/`
- Remote run root:
  - `/home/nebula/xxy/duograph3d_artifacts/duograph3d_conceptgraphs_gt_layer_monitor_20260426_v2`

### GT proxy definition
- Available Replica GT in this setup is a semantic point map, not strict instance-ID GT.
- Therefore the monitor uses **GT semantic class + 1m GT cell** as a proxy target.
- Consequence: duplicate / ID-switch / fragmentation metrics are local semantic-cell proxy metrics, not strict instance-level metrics.

### Added monitor surfaces
- Init / SAM-GSA stage:
  - observation semantic accuracy,
  - per-frame duplicate rate,
  - per-frame over-segmentation factor,
  - CLIP top-1 probability / entropy / margin,
  - GT point purity per observation.
- Layer1 stage:
  - post-repair hypothesis duplicate rate,
  - hypothesis semantic accuracy,
  - hypothesis GT-target purity,
  - false-merge hypothesis rate,
  - merge-pair precision and error rate.
- Layer2 stage:
  - decision accuracy,
  - correct birth / duplicate birth,
  - correct / false association,
  - ID-switch rate per revisit,
  - GT-target fragmentation,
  - multi-target memory-object rate.
- ConceptGraphs baseline stage:
  - baseline object semantic accuracy,
  - baseline object duplicate rate by GT semantic-cell,
  - baseline object CLIP top-1 probability / margin / entropy.

### Key aggregate evidence
- Valid eval observations: `57191`.
- Layer1 eval hypotheses: `46522`.
- Layer2 valid decisions: `46522`.
- Layer2 decision accuracy: `0.102274`.
- Layer2 duplicate birth rate: `0.983734`.
- Layer2 ID switch events: `43268`.
- Layer2 GT-target fragmentation: `41746`.

### Per-layer interpretation
1. **Initialization is already fragmented.**
   - Single-frame init duplicate p50 is high across scenes: roughly `0.333–0.429`.
   - This confirms the user concern: SAM/GSA masks are already significantly fragmented before DuoGraph3D matching begins.
2. **Layer1 helps but does not solve the fragmentation.**
   - Layer1 duplicate p50 drops to roughly `0.227–0.341`.
   - This means Layer1 repairs some same-frame duplicates, but large residual duplicate rates remain, especially `office2` and `office3`.
   - False-merge rate is nonzero (`0.017–0.113`), so simply merging all nearby fragments would be unsafe.
3. **Layer2 is the largest current break point.**
   - Decision accuracy is only about `10.23%` under the GT semantic-cell proxy.
   - Duplicate birth rate is about `98.37%`.
   - ID-switch events are extremely high (`43268`), indicating that repeated GT targets are usually born as new memory IDs instead of being associated to prior IDs.
4. **ConceptGraphs baseline aggregates more strongly.**
   - Baseline object duplicate rates are lower than DuoGraph3D exported-object duplication, supporting the hypothesis that ConceptGraphs has stronger object aggregation under the same GSA input.

### Per-scene summary
| scene | init dup p50 | Layer1 dup p50 | Layer1 false merge | Layer2 acc | duplicate birth rate | ID switch rate | baseline obj acc | baseline obj dup |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| room0 | 0.333 | 0.227 | 0.113 | 0.087 | 0.986 | 0.942 | 0.326 | 0.087 |
| room1 | 0.368 | 0.250 | 0.094 | 0.149 | 0.980 | 0.904 | 0.432 | 0.189 |
| room2 | 0.348 | 0.250 | 0.066 | 0.100 | 0.982 | 0.948 | 0.212 | 0.231 |
| office0 | 0.385 | 0.300 | 0.063 | 0.095 | 0.984 | 0.962 | 0.326 | 0.186 |
| office1 | 0.385 | 0.273 | 0.109 | 0.178 | 0.986 | 0.881 | 0.417 | 0.167 |
| office2 | 0.421 | 0.339 | 0.084 | 0.081 | 0.986 | 0.965 | 0.178 | 0.244 |
| office3 | 0.429 | 0.341 | 0.060 | 0.079 | 0.983 | 0.971 | 0.193 | 0.298 |
| office4 | 0.333 | 0.250 | 0.017 | 0.095 | 0.977 | 0.953 | 0.118 | 0.235 |

### Decision / next experiment implication
- The gap should no longer be described as only an online-merge issue.
- More precise diagnosis:
  - **SAM/GSA initialization creates substantial same-frame fragmentation.**
  - **Layer1 partially repairs it but leaves enough residual duplicates to overload Layer2.**
  - **Layer2 then fails to reuse IDs because current keys/candidates do not preserve strong identity across fragments/frames.**
- Next fixes should be staged rather than threshold-only:
  1. fragment-aware Layer1 initialization ablation,
  2. neighbor-key / spatial-candidate Layer2 retrieval ablation,
  3. semantic-distribution object state rather than hard label-in-key identity.

### Validation
- Remote full 8-scene GT-aware monitor completed.
- Local artifact verification passed.
- Full local unit suite passed: `python3 -m unittest discover -s tests -v` (`81 tests`, OK).
