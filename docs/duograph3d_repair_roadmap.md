# DuoGraph3D Repair Roadmap：诊断驱动的分阶段修理计划

## 0. 当前项目定位

DuoGraph3D 当前不是普通 tracking 项目，而是一个 **online 3D scene reconstruction / online object memory reconstruction** 项目。

核心目标：

```
RGB-D sequence → online object memory graph → 3D semantic object map
```

当前 baseline 是 ConceptGraphs。ConceptGraphs 的优势在于：

```
在线阶段开放保留 → 离线后处理合并清理
```

而当前 DuoGraph3D 的问题是：

```
在线阶段过早强决策 → candidate missing / duplicate birth / retire / label pollution → 后处理无法恢复
```

因此，当前阶段不是追求新模型复杂度，而是先把 DuoGraph3D 修成一个：

> **稳定、开放、可诊断、接近 ConceptGraphs 的 online reconstruction baseline**

之后再逐步恢复 DuoGraph3D 的双层 graph 创新。

---

## 总体推进原则

1. **每次只改一个机制**：禁止同时改 lifecycle + candidate retrieval + identity gate + Layer1 + export
2. **每次实验必须输出六张诊断表**：mIoU 只是最后结果，不是诊断工具
3. **先修基础稳定性，再谈创新**：诊断表 → lifecycle 止血 → candidate recall → identity gate softening → semantic distribution → CGAligned baseline → Layer1/Layer2 graph innovation
4. **ConceptGraphs 是对齐对象，不是单纯被超越对象**：第一阶段目标不是超过 CG，而是让 DuoGraph3D 的开放性、object survival、coverage、postprocess input quality 接近 CG

---

## Phase 0：冻结当前状态，建立可复现实验基线

### 目标

建立一个不会继续漂移的当前状态快照，保证后续每一步都有可回滚基线。

### 任务

**0.1 创建版本标签**

保存当前版本 `duograph3d-chaotic-v0`，记录 commit hash, runner command, dataset path, scene list, stride, config, export mode, current official metrics, current diagnostic if available.

**0.2 固定三个基线配置**

| Baseline | 说明 |
|---|---|
| **B0-current** | 当前完整配置 |
| **B1-no-lifecycle** | retire/occluded/dormant 全部设为 999 |
| **B2-no-lifecycle-unlimited-candidate** | B1 基础上取消 candidate top-K 剪裁 |

后续所有新实验都必须至少和 B0、B1、B2 对比。

**0.3 固定实验命名规范**

每次实验目录必须包含：scene, stride, lifecycle mode, candidate mode, identity gate mode, Layer1 mode, semantic mode, export mode, date

### 通过标准

输出 `baseline_registry.md`，包含 B0/B1/B2 command、结果目录、配置差异。

---

## Phase 1：实现六张诊断表

把 DuoGraph3D 从"只看 mIoU"变成"每一层都可诊断"。

### Table 1：输入观测质量表

回答：上游 GSA/SAM observation 本身是否已经有严重问题？

字段：scene, stride, raw/kept/filtered counts, observations_per_frame stats, valid_depth_ratio, mask_area distribution, confidence distribution, raw_semantic_acc, raw_GT_point_coverage, per_class_raw_recall, top_raw_confusions

### Table 2：Layer1 单帧修复质量表

回答：Layer1 帧内修复是在帮忙还是制造不可逆错误？

字段：observations_before_L1, hypotheses_after_L1, merge_ratio, component_size_stats, component_purity_mean, false_merge_rate, severe_false_merge_rate, under_merge_rate, label_collapse_rate, minority_points_lost, L1_semantic_acc, L1_vs_raw_semantic_delta, L1_edge_reason_breakdown

关键诊断：如果 false_merge_rate 高 + label_collapse_rate 高 → 不能保持 current graph 强合并，应切到 L1-off 或 L1-dedup-only

### Table 3：Layer2 跨帧关联质量表

回答：Layer2 到底为什么失败？候选没召回、打分选错、identity gate 拒绝、还是 lifecycle 杀掉了正确物体？

字段：hypotheses_total, candidate_hit_rate, candidate_missing_rate, true_candidate_rank_mean/p50/p90, true_candidate_score_mean, best_candidate_score_mean, score_margin_true_vs_best, association_accuracy, wrong_object_rate, birth_rate, duplicate_birth_rate, true_new_birth_rate, identity_gate_reject_correct_rate, threshold_reject_correct_rate, lifecycle_missing_rate, residual_absorb_accuracy, birth_reason_breakdown

错误分解：candidate_missing / candidate_present_but_wrong_ranking / candidate_present_but_identity_gate_failed / candidate_present_but_below_threshold / candidate_retired_or_unavailable / residual_absorb_error / duplicate_birth_other

### Table 4：Memory 生存质量表

回答：ObjectGraphMemory 是否真的形成了稳定物体记忆？

字段：created_nodes, active/occluded/dormant/retired/exported nodes, survival_rate, active_survival_rate, mean/median lifetime, detections_per_node stats, nodes_per_GT_object stats, GT_objects_per_node stats, class_entropy_per_node, dominant_label_share_mean, retired_with_GT_support, skip_reason_breakdown

### Table 5：Export 输入质量表

回答：进入 ConceptGraphs 后处理前，DuoGraph3D 给出的 objects 质量如何？

字段：objects before/after denoise/filter/merge, points stats, skipped_objects_by_reason, export_source_distribution, geometry_coverage, object_purity_mean, fragmentation_ratio, duplicate_object_rate, overmerge_rate, export_label_entropy, CG_postprocess_merge_count, CG_filter_removed_count

### Table 6：最终错误分解表

回答：final mIoU 低，到底是 label 错、漏了、碎了、重复了，还是合错了？

字段：final_mIoU/mRecall/mPrecision/FmIoU, label_error_ratio, missing_error_ratio, fragmentation_error_ratio, duplicate_error_ratio, overmerge_error_ratio, per_class_IoU/recall/precision, confusion_matrix, top_confused_pairs, worst_classes_by_recall, worst_classes_by_IoU, large_class_FmIoU_contribution

### 通过标准

每次实验输出：`diagnostic_report.md`, `diagnostic_tables.json`, `diagnostic_tables.csv`, `summary_plots/`

---

## Phase 2：复现三个基线

### 实验 2.1：B0-current

配置：Layer1 current, Layer2 current, candidate top-K, identity gate hard, lifecycle current, semantic top-1, export current memory-dense, stride current

目标：复现当前坏现象

### 实验 2.2：B1-no-lifecycle

配置：retire_after=999, occluded_after=999, dormant_after=999

主要观察 Table 4 (survival_rate) 和 Table 3 (lifecycle_missing_rate, duplicate_birth_rate)

### 实验 2.3：B2-no-lifecycle-unlimited-candidate

配置：lifecycle off, candidate_budget unlimited, identity gate hard, Layer1 current, semantic top-1

主要观察 Table 3 (candidate_hit_rate, candidate_missing_rate, duplicate_birth_rate)

### 通过标准

输出 `baseline_comparison.md`，包含完整对比表并给出瓶颈排序。

---

## Phase 3：止血修理阶段

### Phase 3.1：Lifecycle Repair

实验矩阵：L0-current, L1-immortal, L2-no-retire, L3-retire-exportable, L4-stride-aware

通过标准：survival_rate 上升, lifecycle_missing_rate 下降, duplicate_birth_rate 下降, missing_error_ratio 下降, label_error_ratio 不上升

### Phase 3.2：Candidate Retrieval Repair

候选版本：C0-current, C1-all-alive, C2-spatial-radius, C3-geometry-neighbor, C4-visual-ANN-wide, C5-recall-first-union

通过标准：candidate_hit_rate > 90%, candidate_missing_birth_rate 下降, duplicate_birth_rate 下降

### Phase 3.3：Identity Gate Repair

实验矩阵：I0-hard, I1-soft-bonus, I2-margin-override, I3-history-soft, I4-spatial-visual-override

通过标准：identity_gate_reject_correct_rate 下降, association_accuracy 上升, duplicate_birth_rate 下降, wrong_object_rate 不上升, overmerge_error_ratio 不上升

---

## Phase 4：建立 DuoGraph3D-CGAligned baseline

CGAligned 配置：lifecycle immortal, candidate recall-first, identity gate soft, Layer1 off/dedup-only, semantic distribution accumulation, export coverage-preserving, postprocess same as CG

### Phase 4.1-4.4

4.1: Layer1-off baseline
4.2: Layer1-dedup-only baseline
4.3: Semantic Distribution Accumulation
4.4: CGAligned 汇总对比

通过标准：survival_rate 不再极低, candidate_hit_rate 高, duplicate_birth_rate 明显低于 current, object count 不爆炸, geometry coverage 接近 CG, mIoU 接近或超过 current

---

## Phase 5：重新打开 DuoGraph3D 双层 graph 创新

### Phase 5.1：Layer1 Signed Current Evidence Graph

边类型：must-link (high geometry overlap + same support + no semantic conflict), cannot-link (co-visible + spatially distinct + strong semantic conflict), abstain (不确定)

必须保留 sub-payload：label distribution, per-label point buckets, per-label features, minority labels

### Phase 5.2：Layer2 Memory Graph

先 shadow consulidation，再 partial activation，再 full activation。

### Phase 5.3：Tentative / Promotion

旧：unmatched → new memory node
新：unmatched → tentative fragment → promotion gate → active memory

### Phase 5.4：Working / Stable Memory

Working: short-term, reversible, used for matching
Stable: high-confidence only, used for identity prototype and final semantic/geometric estimate

---

## Phase 6：Carrier Selection / Export 修理

Carrier 候选：memory sampled, dense geometry, memory-dense root, label-bucket split, geometry fallback

实验：E0-memory, E1-geometry, E2-memory-dense, E3-memory-dense-labelbucket, E4-coverage-aware-auto, E5-oracle-carrier

通过标准：mRecall 上升, F-mIoU 上升, carrier_oracle_gap 下降, memory_contribution_ratio 不能过低, duplicate_object_rate 不上升

---

## Phase 7：正式实验矩阵与论文故事验证

主要对照组：ConceptGraphs, DuoGraph3D-current, DuoGraph3D-CGAligned, +Layer1 Graph, +Layer2 Memory Graph, +Tentative/Stable Memory, +Carrier Selection, Full DuoGraph3D

最终验证：Layer1 graph 减少单帧 fragmentation, Layer2 memory graph 减少 duplicate birth, tentative/stable memory 减少 memory drift, carrier selection 提高 final coverage/F-mIoU, 全系统在 mIoU/mRecall/fragmentation/duplicate birth/semantic purity 上优于 baseline

---

## 停止准则

- 诊断表不完整 → 停止，不做算法实验
- candidate_hit_rate < 90% → 停止调 scorer，先修 candidate retrieval
- survival_rate 极低 → 停止调 export，先修 lifecycle/memory survival
- Layer1 false_merge_rate 高 → 停止使用强 Layer1，退回 L1-off/dedup-only
- duplicate_birth_rate 高 → 停止分析 final mIoU，先修 Layer2/tentative birth
- label_error_ratio 仍最高 → 优先修 semantic distribution accumulation
- carrier_oracle_gap 很大 → 说明 export carrier 是瓶颈

---

## 当前最先应该执行的 3 个任务

1. **Task 1：实现六张诊断表**（最高优先级）
2. **Task 2：跑三组 baseline**（B0, B1, B2）
3. **Task 3：建立 CGAligned 最小版本**
