# DuoGraph3D 最新实验计划（更新：2026-04-23）

## 2026-04-23 更新（20:30 +08:00，zero-shot baseline 主线校准 + OnlineAnySeg subset20）

- 主线已按最新决策校准：DuoGraph3D 是 **online zero-shot object-centric 3D reconstruction/mapping** 工作；ESAM/EmbodiedSAM 仅作为 auxiliary compatibility / supplementary reference，不作为主增益 comparator。
- 因此 fullval ESAM-family AP 没有形成主增益并不阻塞投稿故事；它只约束我们在 ESAM surface 上保守表述。
- 当前应优先补齐的 zero-shot external baselines 是：
  1. **OnlineAnySeg**（direct online zero-shot 2D/3D object baseline）
  2. **ConceptGraphs**（object-centric graph/memory baseline）
- OnlineAnySeg 已从 one-scene/subset5 smoke 扩展到固定 ScanNet200 subset20 sparse-feature 官方方法/evaluator bring-up：
  - remote root: `/home/nebula/xxy/duograph3d_artifacts/onlineanyseg_official_subset20_sparse_20260423`
  - scenes: first 20 valid fullval scenes, starting with `scene0568_00`, `scene0568_01`, `scene0568_02`, `scene0304_00`, `scene0488_00`
  - 结果：`AP 0.061 / AP50 0.138 / AP25 0.298`，`335 / 572` pred/GT instances，`20/20` sequences，`0` missing。
  - 本地归档：`docs/official_results/onlineanyseg_minimal_20260423/raw/subset20_sparse/` 与 `docs/official_results/onlineanyseg_minimal_20260423/lane_summary.md`。
  - 边界：这是 pooled dense CLIP mask features + `mask_weight_threshold=1` 的 zero-shot subset bring-up，证明官方方法/evaluator 路径可复现；还不是最终 full official benchmark。
- ConceptGraphs 当前状态：`duograph-baselines-cu118` 中 `eval_replica_semseg` / `gradslam` / `chamferdist` import OK；最新 audit 已归档到 `docs/official_results/conceptgraphs_minimal_20260423/raw/conceptgraphs_scoring_path_audit_20260423.txt`。剩余阻塞是 Replica semantic roots / ScanNet export 口径不一致，以及 `cfslam_pipeline_batch` 的 `to_tensor` upstream import drift。
- 下一步优先级：
  1. 将 OnlineAnySeg subset20 sparse bridge 扩到更大固定 zero-shot subset，或生成完整官方 mask embeddings。
  2. 为 ConceptGraphs 选择并实现评分口径：Replica-format DuoGraph3D export + matching Replica semantic roots，或 ScanNet-compatible ConceptGraphs evaluator。
  3. 以 OnlineAnySeg + ConceptGraphs 作为主 zero-shot baseline lanes 更新主表/附录；ESAM-family 只保留为 auxiliary compatibility evidence。

## 2026-04-23 更新（19:55 +08:00，远端环境重配 + gap closure 进展）

- 遵循“实验全部在远端服务器上进行”的约束，本轮只在 `nebula@10.177.69.184` 配置 / 运行实验，本地仅同步文档与原始日志。
- fullval 独立 `no-rescue/no-dedup` 复验已完成：
  - remote root: `/home/nebula/xxy/duograph3d_artifacts/formal_fullval_norescue_nodedup_rerun_20260423/norescue_nodedup_strict_independent`
  - 结果：`AP 0.4135 / AP50 0.6300 / AP25 0.7886`，`312 scenes / 13430 frames`。
  - 本地归档：`docs/official_results/scannet200_fullval_norescue_nodedup_rerun_20260423/`；同时更新 `docs/official_results/scannet200_fullval_20260423/comparison_summary.*`。
  - 结论：此前 alias-only 证据缺口已关闭，但 fullval AP 主结论仍需保守表述（rescue/dedup 变体未超 strict）。
- OnlineAnySeg 环境已在远端重配为独立环境：
  - `duograph-oas-cu116`（从 `ESAM` clone，未改动正在使用的 ESAM 环境）。
  - 补齐：`pytorch3d v0.7.2`（源码编译，`CUDA_HOME=/usr/local/cuda-11.6`, `TORCH_CUDA_ARCH_LIST=8.6+PTX`）与 `future-fstrings`。
  - 官方 import check：`main / Dataset.dataset / Scene_rep / voxel_hashing` 全部 OK。
  - 已完成 `scene0568_00` 官方方法 + evaluator sparse-feature smoke：`AP 0.127 / AP50 0.260 / AP25 0.578`，36 pred / 31 GT。
  - 边界：该结果使用 83 帧重编号输入、9 个有 dense CLIP feature 的 segmentation frames、池化 CLIP mask embedding，并将 `mask_weight_threshold` 降到 1；它证明官方方法/evaluator 端到端可执行，不作为最终公平 benchmark 分数。
- ConceptGraphs 环境已在远端重配为独立环境：
  - `duograph-baselines-cu118`（从 `conceptgraph-cu118` clone）。
  - 补齐：`chamferdist 1.0.3`（CUDA 11.6 + arch 8.6+PTX 编译）与 `gradslam 0.1.0`。
  - `conceptgraph.scripts.eval_replica_semseg` import OK；剩余 blocker 从 CUDA/chamferdist 转移为“官方 Replica evaluator 与当前 ScanNet export 不同任务/GT root”，以及 `cfslam_pipeline_batch` 的 upstream `to_tensor` import drift。
- 下一步优先级更新：
  1. 将 OnlineAnySeg smoke 扩到固定多场景 subset，或生成完整官方 mask embeddings 后重跑。
  2. 为 ConceptGraphs 选择路径：Replica-format DuoGraph3D export + Replica semantic roots，或文档化 ScanNet-compatible ConceptGraphs evaluator。
  3. 更新投稿主表 claim：fullval 证据作为可复现/边界说明，外部 direct baseline 作为 reviewer-facing 补强。


## 2026-04-23 更新（19:25 +08:00，direct baseline bring-up）

- 184 服务器上已补齐 `OnlineAnySeg` 官方 repo：
  - `/home/nebula/xxy/OnlineAnySeg`
  - commit `152466e318f8220bcc6838c03e340cce2f2153b8`
- `OnlineAnySeg` 官方 evaluator surface 已跑通 one-scene smoke：
  - `scene0568_00`
  - 本地归档：`docs/official_results/onlineanyseg_minimal_20260423/lane_summary.md`
  - 边界：该 AP 数值来自 GT-sidecar evaluator bridge smoke，只证明 evaluator / export surface 可运行，**不作为方法性能或 baseline 分数声明**。
- `OnlineAnySeg main.py` 环境阻塞已解除，已完成 scene0568_00 sparse-feature 官方方法 smoke；多场景公平分数仍待扩展：
  - 现有环境未同时满足 OnlineAnySeg 所需依赖：`conceptgraph-cu118` 缺 Python-compatible MinkowskiEngine，`ESAM` 缺 `pytorch3d` / `open_clip` 等依赖。
- `ConceptGraphs` lane 已形成本地归档：
  - `docs/official_results/conceptgraphs_minimal_20260423/lane_summary.md`
  - DuoGraph3D ConceptGraphs-format manifest 已保存。
  - 官方 `eval_replica_semseg` 的 `chamferdist`/CUDA import blocker 已解除；剩余问题是 Replica evaluator 与当前 ScanNet export/GT root 不匹配。
- 为补齐 fullval 公平对照，已在 184 启动独立 `no-rescue/no-dedup` fullval rerun：
  - remote root: `/home/nebula/xxy/duograph3d_artifacts/formal_fullval_norescue_nodedup_rerun_20260423/norescue_nodedup_strict_independent`
  - 本地状态归档：`docs/official_results/scannet200_fullval_norescue_nodedup_rerun_20260423/job_status.md`
  - 当前状态：completed；metric JSON 与 online monitor summary 已落盘并归档。
- 下一步优先级更新：
  1. 将 OnlineAnySeg one-scene smoke 扩到固定多场景 subset，并尽量补齐完整官方 mask embeddings。
  2. 对 ConceptGraphs 做任务口径选择：Replica GT 路径或 ScanNet-compatible evaluator。
  3. 更新主表候选和 claim-evidence map，明确 fullval AP 边界。

## 2026-04-23 更新（18:35 +08:00，184 后端复核后）

- 184 上的 fullval 评测已复核完成，无增量运行任务，当前结果与本地 `docs/official_results/scannet200_fullval_20260423/*` 完全一致。
- 2026-04-23 18:35 新增远端核对证据：`docs/official_results/scannet200_fullval_20260423/raw/remote_verification_184_20260423.{json,md}`；按 1e-4 容差远端与本地五格全量结果一致。
- 这批实验是**ESAM-online 在线测试链路上的配置消融**：使用的不是新训练模型替换，而是固定 ESAM 兼容推理链路下切换 Rescue/Dedup 开关的可比较配置（严格基线、rescue-only、dedup-only、rescue+dedup、plus 诊断变体）。
- `no-rescue/no-dedup` 已完成独立同预算复验；数值与 strict 配置一致，alias-only 证据缺口已关闭。
- 下一步优先继续推进的是：
  1. `OnlineAnySeg` 的官方可复验 bring-up（最小 subset）
  2. `ConceptGraphs` 的官方可复验 bring-up（最小 subset）
  3. 形成两条 direct baseline 的 `lane_summary` + `comparison_summary`
  4. 统一成投稿主表前的最终差距清单

## 2026-04-23 更新（18:45 +08:00，184 复核重跑）

- 在 184 服务器重新做了快速复核后，继续生成：
  - `docs/official_results/scannet200_fullval_20260423/raw/remote_verification_184_20260423_recheck.json`
  - `docs/official_results/scannet200_fullval_20260423/raw/remote_verification_184_20260423_recheck.md`
- 复核口径：remote metric + online monitor summary 与本地 5 格主对照缓存一一对应，字段对齐（AP/AP50/AP25/场景数/帧数/match rate/birth rate/rescued/topk_drop/mem_size）并按 1e-4 容差比较。
- 结论：五条 lane 复核结果仍然 `all_match=True`，说明当前 fullval 缓存是可追踪一致的；无新增实验任务正在 184 运行。

## 2026-04-23 更新（18:50 +08:00，184 空载核查）

- 复核 184 上训练/评测进程：未检测到正在执行的 ESAM/OnlineAnySeg/ConceptGraphs 长任务（`ps` 过滤无任务返回）。
- 再次确认：当前 `fullval` 比较仍停留在 ESAM-online 配置消融链路；未见新一轮 fullval 同预算重跑输出。
- 下一阶段执行顺序不变：先推进 `OnlineAnySeg` 最小可复现 subset，再推进 `ConceptGraphs` 最小可复现链路。

## 2026-04-23 更新（18:53 +08:00，184 复核再确认）

- 继续在 184 端抽取 fullval 五格 monitor+metric，并完成再一次 hash+字段复核：
  - `docs/official_results/scannet200_fullval_20260423/raw/remote_verification_184_20260423_recheck3.json`
  - `docs/official_results/scannet200_fullval_20260423/raw/remote_verification_184_20260423_recheck3.md`
- 复核口径与此前一致：`AP / AP50 / AP25 / scenes / frames / match_rate / birth_rate / rescued / topk_drop / mem_size_*`，容差 1e-4。
- 结论更新：`all_match=True`，五格仍可复核一致；`fullval` 缓存当前无新增文件落盘迹象（远端目录与本地复核路径仍一一对应）。

## 2026-04-23 更新（18:59 +08:00，184 recheck5）

- 再次在 184 端抓取五格 latest timestamp 的 metric + online monitor 并与本地五格对照进行一轮字段级比对（脚本化）：  
  - `docs/official_results/scannet200_fullval_20260423/raw/remote_verification_184_20260423_recheck5.json`
  - `docs/official_results/scannet200_fullval_20260423/raw/remote_verification_184_20260423_recheck5.md`
- 比对字段与 18:53 一致：AP/AP50/AP25/scenes/frames/match_rate/birth_rate/rescued/topk_drop/mem_size_*，容差 1e-4。
- 结论：`all_match=True`，依然无新增任务与新产物落盘；当前资源利用仍停留在既有 ESAM fullval 套件。

## 一、当前可复现事实（本计划基准）

- 已完成：
  - real-observation 主链已落地，远端与本地测试通过。
  - 方法增强（Graph/Geometry/Temporal）已完成并有回归测试。
  - 外部基线系统已按 story fit 重排：DEVA 保留 temporal reference；OnlineAnySeg + ConceptGraphs 是当前主 zero-shot external lanes；ESAM family 仅保留为辅助兼容行。
  - Phase4 结果包：内部主表/消融/案例都已生成；proxy 老指标准入口已降级为参考。
  - 全量单元测试通过：`76 tests, 0 failures`。

- 最新实测：
  - ScanNet200 subset5 official AP：
    - ESAM online baseline：`AP 0.5146 / AP50 0.7348 / AP25 0.8508`
    - DuoGraph-style rescue+dedup：`AP 0.5330 / AP50 0.7561 / AP25 0.8837`
    - Delta：`+0.0183 / +0.0213 / +0.0329`
  - ScanNet200 fullval（ESAM-family compatible，已做 5 格对照）：
    - ESAM 上下文基线（strict；no-rescue/no-dedup 已有独立同配置复验）：
      `AP 0.4135 / AP50 0.6300 / AP25 0.7886`
    - DuoGraph-style rescue-only（`fullval_neg05_v2_rescue_only_strict_retry2`）：
      `AP 0.4133 / AP50 0.6286 / AP25 0.7897`
    - DuoGraph-style dedup-only（`fullval_neg05_v2_dedup_only_strict`）：
      `AP 0.4133 / AP50 0.6244 / AP25 0.7797`
    - DuoGraph-style rescue+dedup（`fullval_neg05_v2_rescue_all_dedup_strict`）：
      `AP 0.4051 / AP50 0.6139 / AP25 0.7708`
    - 辅助 ESAM-family 对照（`2601_dedup_strict_fullval`）：
      `AP 0.3985 / AP50 0.6024 / AP25 0.7624`

## 二、实验目标（按可投稿主线顺序）

### 目标 1：补齐 fullval 同预算公平对照（辅助兼容 / provenance 证据）
- 目的：消除 ESAM-family AP surface 的 provenance 争议；该 surface 不再承担主增益 comparator 角色。
- 对照矩阵（同预算）：
  1) strict baseline
  2) no-rescue + no-dedup
  3) rescue-only
  4) dedup-only
  5) rescue+dedup
- 评估指标：`all_ap / all_ap_50% / all_ap_25%` + online monitor (`match_rate`, `birth_rate`, `rescued`)。
- 当前状态：5 格内核指标结果已收敛；no-rescue/no-dedup 已有独立同预算同配置重跑记录。因 ESAM 已降级为 auxiliary compatibility，fullval AP 未形成主增益不再阻塞 zero-shot 主故事。

### 目标 2：主故事对齐外部 direct baseline 带起
- 先行 lane：**OnlineAnySeg**
  - 当前状态：远端独立环境已修复，官方方法/evaluator 已完成固定 ScanNet200 subset20 sparse-feature bring-up（`AP 0.061 / AP50 0.138 / AP25 0.298`，`20/20` scenes），下一步扩展到更大 zero-shot subset 或完整官方 mask embeddings。
- 次行 lane：**ConceptGraphs**
  - 当前状态：远端独立环境已修复到 evaluator import OK；最新 audit 证明剩余问题是 Replica semantic roots / ScanNet export 口径不一致与 `to_tensor` import drift，尚未声明语义分数。
- 均应产出（最小可复现目标）：
  - `lane_summary.json`（命令、数据、指标、限制）
  - `comparison_summary.*`（含对比边界）

### 目标 3：把内部指标与 reviewer-friendly 证据桥接
- 当前 internal 指标先行保留：`identity_fragmentation_count`, `track_consistency_rate`, `memory_relation_edge_count`, `relation_density`, `memory_object_purity`。
- 下一步：为 OnlineAnySeg/ConceptGraphs 可复现路径追加分层映射指标（避免主表再次被单一 AP 主导）。

### 目标 4：submission hardening（Phase 6）
- clean-env 复现关键主表与关键图；
- 打包 supplementary/appendix；
- 最终 claim-lock 审核与一致性核验；
- 统一匿名化与脚本复现路径。

## 三、验收标准（里程碑）

1. **fullval 公平对照完成**：5 格全量配置具备同环境、同预算结果文件；no-rescue/no-dedup 的独立同预算命令和结果已归档。
2. **至少一条 external direct baseline 跑通**：OnlineAnySeg 已有可复现固定 subset20 sparse-feature 官方方法/evaluator 结果；投稿主表仍需扩为更大/更完整的公平 zero-shot benchmark。
3. **第二条 external direct baseline 启动**：ConceptGraphs evaluator import 已修复，下一步需完成 Replica/ScanNet 任务口径对齐。
4. **主表可直接面向投稿**：每条关键 claim 都有 story-aligned 主证据映射。
5. **Phase6 清洗通过**：主图主表+附录可打包且不含自相矛盾。

## 四、最新执行顺序（建议）

1. `OnlineAnySeg` scale-up（目标2；从 subset20 sparse bridge 扩到更大/更完整 zero-shot benchmark）
2. `ConceptGraphs` scoring-path unblock（目标2；Replica-format export 或 ScanNet-compatible evaluator）
3. `fullval auxiliary compatibility`（目标1；保持 provenance 与保守表述）
4. `bridge metrics + metric mapping`（目标3）
5. `submission hardening`（目标4）

## 五、对应本地产物（用于落地）

- 继续更新：
  - `docs/experiment_registry.md`
  - `docs/baseline_execution_roadmap.md`
  - `docs/official_results/scannet200_fullval_20260423/*`
  - `docs/official_results/scannet200_subset5_20260423/*`
- 新增/待新增：
  - `docs/official_results/<lane>/<comparison_summary>.{json,md}`
  - `docs/official_results/<lane>/lane_summary.json`
  - `docs/baselines/generated/external_baseline_matrix.*`（持续补齐新直接 baseline）

## 六、距离可投稿的核心差距

1. **外部 zero-shot direct/graph baseline 仍未达到投稿级完整度**：`OnlineAnySeg` 已有 fixed subset20 官方方法/evaluator bring-up，但仍需扩大规模或补完整官方 embeddings；`ConceptGraphs` evaluator import 已修复但仍缺任务/GT 对齐后的语义分数。
2. **fullval 独立 no-rescue/no-dedup 命令缺口已关闭**：当前剩余问题不是 provenance，而是 fullval AP 未显示 rescue/dedup 主增益，需要保守 claim。
3. **指标层级仍偏内测**：仍需补齐外部对比所需的对象级结构指标映射。
4. **提交主表缺少“投稿级 zero-shot 直接对手”支撑**：当前主表仍不能算 final-submission-ready，主要缺口是 OnlineAnySeg 更大规模结果与 ConceptGraphs 对齐评分，而不是 ESAM 增益。
