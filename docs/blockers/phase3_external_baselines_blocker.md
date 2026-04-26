# Phase 3 Blocker Report — External Reviewer-Credible Baselines

日期：2026-04-23

状态更新（2026-04-23 18:35 +0800）：已完成 184 服务器复核，额外外部基线仓库已在本地确认可见，但尚未产出可复核官方评测成绩。

状态更新（2026-04-23 19:55 +0800）：阻塞已部分解除。OnlineAnySeg 已在远端独立环境 `duograph-oas-cu116` 完成 one-scene 官方方法/evaluator smoke（AP/AP50/AP25=0.127/0.260/0.578），fullval no-rescue/no-dedup 独立复验已完成；ConceptGraphs 的 `chamferdist`/`gradslam` import blocker 已解除，但仍需解决 Replica/ScanNet 任务口径对齐。

状态更新（2026-04-23 20:30 +0800）：按最新投稿主线，ESAM/EmbodiedSAM 已明确降级为 auxiliary compatibility reference；主 zero-shot baselines 是 OnlineAnySeg 与 ConceptGraphs。OnlineAnySeg 已完成固定 ScanNet200 subset20 sparse-feature 官方方法/evaluator bring-up（AP/AP50/AP25=0.061/0.138/0.298，20/20 scenes，335/572 pred/GT），但仍需更大/更完整 zero-shot benchmark；ConceptGraphs import stack 已修复并完成 scoring-path audit，仍需解决 Replica semantic roots / ScanNet export 口径与 `to_tensor` import drift。

## Blocked phase
- Phase 3 — reviewer-credible baseline system build-out

## What was attempted

1. Verified the already-available external baseline lane:
   - **DEVA official offline lane** remains available through the existing target/runtime/result modules.
2. Searched the local and remote workspace for additional nearest-neighbor external baseline assets or runnable repositories.
3. Audited the remote environment for real executed outputs that could serve as a second external baseline family.

## Evidence gathered

### Available and usable today
- DEVA official offline target is already formalized in the repo.
- 本地/远端发现可用官方仓库 clone（含基础文档与入口）：
  - `OnlineAnySeg`：`/Users/xin/Research/project/3D重建/repos/conceptgraph_family/OnlineAnySeg`
  - `ConceptGraphs`：`/Users/xin/Research/project/3D重建/repos/conceptgraph_family/concept-graphs`
- Remote executed DEVA outputs exist under:
  - `/home/nebula/xxy/duograph3d_artifacts/deva_runtime_exec_replica_ext_v1/deva_output/JSONFiles`
- Remote ESAM-family 全量 fullval 及子集监控结果可复核：
  - `/home/nebula/xxy/3D_Reconstruction/work_dirs/ESAM_online_scannet200_CA_mv_fast_ab/fullval_*`

### Present but not reviewer-credible enough yet
- Remote ScanNet online-monitor outputs exist under:
  - `/home/nebula/xxy/3D_Reconstruction/work_dirs/ESAM_online_scannet200_CA_mv_fast_ab/fullval_baseline_dino/online_monitor/online_monitor.json`
- These outputs and raw ESAM-family online-monitor artifacts were sufficient for Phase 1 real-observation replacement and Phase 2 method regression, but they are **not yet packaged as a reviewer-credible direct external baseline lane** with:
  - official repo provenance
  - frozen command path
  - documented configuration contract
  - normalized evaluation summary in this repo

- OnlineAnySeg 已有 fixed subset20 可复现运行与标准化 lane summary，但仍**缺少 reviewer-ready 的更大/完整官方 benchmark 包**。
- ConceptGraphs 已有环境与 scoring-path audit，但仍**缺少任务口径对齐后的语义评分包**，包括：
  - Replica-format DuoGraph3D export + matching semantic roots，或 ScanNet-compatible evaluator
  - 固定命令与 runtime 日志
  - 与本仓库统一格式的 `comparison_summary`

### Missing from the current environment
- 对 OnlineAnySeg / ConceptGraphs，当前仍缺少可直接用于投稿主表的最终已执行结果包：OnlineAnySeg 需要更大/更完整 zero-shot 评分，ConceptGraphs 需要任务/GT 对齐后的评分。
- `no-rescue / no-dedup` 的独立同预算控制复现实验已在远端完成并归档；该项不再是当前 blocker。

## Why this blocks Phase 3

Phase 3 requires more than one external baseline lane with reviewer-credible provenance.

At the moment, **DEVA** satisfies the temporal-reference bar and **OnlineAnySeg** now has an executable fixed subset20 zero-shot method/evaluator bring-up, but OnlineAnySeg still needs a larger or complete official-feature benchmark before it should be treated as submission-ready.
The currently accessible ScanNet monitor artifact is valuable engineering evidence, but it is not yet enough to count as a formal second external nearest-neighbor baseline for top-tier submission quality.

### Current path to unblock

1. 将 `OnlineAnySeg` 从 fixed subset20 sparse-feature bring-up 扩展到更大固定 zero-shot subset 或完整官方 mask embeddings（保留 command + 官方评测摘要）。
2. 将 `ConceptGraphs` bring-up 从 import-ready 推进到任务口径对齐后的可复核结果链路（Replica-format export 或 ScanNet-compatible evaluator）。
3. 在两条外部 direct baseline 可复现后，再继续在主文档中完成 Phase 3 外部 baseline unblock 声明。

## Exact prerequisite to unblock

Before Phase 3 can be treated as submission-ready, at least one primary zero-shot lane must move beyond smoke/subset bring-up into a reviewer-defensible benchmark package, and the second lane must have a documented scoring path:

1. OnlineAnySeg larger fixed zero-shot subset or complete official mask-embedding run, with command/config/logs and normalized comparison summary.
2. ConceptGraphs Replica-format or ScanNet-compatible scoring path, with command/config/logs and normalized comparison summary.
3. ESAM-family artifacts may remain as auxiliary compatibility evidence only; they should not be used to satisfy the primary zero-shot baseline requirement.

## Current recommendation

Preferred unblock path:
- scale OnlineAnySeg first because it is already runnable on subset20
- unblock ConceptGraphs scoring path second because it best supports the graph-memory claim
- keep ESAM-family results as supplementary/compatibility evidence, not as the primary Phase 3 exit criterion
