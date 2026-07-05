# DuoGraph3D 投稿消融实验运行日志（2026-06-27）

## 0. 负责人状态

当前投稿消融队列已在 184 服务器完成。本轮目标不是继续大范围调参，而是判定：哪些 E70 组件是真正可迁移的正向改进，哪些“创新点/统一化尝试”已经被消融否定。

- 184：`10.177.69.184`，当前无 DuoGraph3D tmux 任务；RTX 4090 空闲（2026-06-27 18:01 CST：39 MiB / 24564 MiB，0% GPU 利用率）。
- 73：此前 SSH reset；76：此前 SSH banner timeout。本轮重实验只使用 184。
- 远程主代码：`/home/nebula/xxy/DuoGraph3D`。
- shape 消融根目录：`/home/nebula/xxy/duograph3d_artifacts/submission_shape_ablations_20260627_1705`。
- naive unified 消融根目录：`/home/nebula/xxy/duograph3d_artifacts/submission_ablations_20260627_1627`。
- E70 anchor：`/home/nebula/xxy/duograph3d_artifacts/e70_best_composite_office2_bin_vent_table_20260626/final_eval`。

## 1. 主结论

1. **当前唯一投稿级强正结果仍是 E70 scene-local composite**：全场景官方 ConceptGraphs-format gap 为 `+3.041 mIoU / +4.927 mF1 / +8.460 F-mIoU`，evaluator PASS，152 tests OK。
2. **当前可迁移的正向规则主要是 `tissue-paper:cloth:0.8`**：相对 w/o large-label，all gap 提升 `+0.523 mIoU / +0.830 mF1 / +0.029 F-mIoU`，主要来自 office1（`+2.105 mIoU / +3.046 mF1`）。
3. **office2 的 `bin:table`、`vent:table` 仍是局部有效诊断修复，不是已证明可全局复用的方法**：E66/E69/E70 证明它们在 office2 正向；本轮 unified/shape-gated 全局化失败。
4. **“统一 large-label relabel / table-sink rule”这个创新点已被当前消融否定**：naive 全局规则、bbox shape-gated 全局规则都远低于 E70，并且出现 office2/office4 负迁移。
5. **two-layer graph memory 尚未被证明是负面，但也尚未被 A1/A3 证明是最终 mIoU 主因**：它应先被写成状态维护/诊断基础设施，不能直接宣称解释 E70 主增益。

## 2. Anchor：E70 full result

| row | all ΔmIoU | all ΔmF1 | all ΔF-mIoU | evaluator | 说明 |
| --- | ---: | ---: | ---: | --- | --- |
| E70 scene-local composite | **+3.041** | **+4.927** | **+8.460** | PASS | 当前唯一强正 anchor；含 office1 tissue、office2 bin/table + vent/table 局部修复 |

E70 per-scene gap 全部 mIoU/mF1 为正：room0 `+6.495/+8.366`，room1 `+11.179/+13.989`，room2 `+0.598/+1.536`，office0 `+1.873/+2.327`，office1 `+8.171/+10.361`，office2 `+6.492/+5.521`，office3 `+1.699/+1.615`，office4 `+1.754/+1.062`。

## 3. 本轮消融结果总表

`status=1` 表示 official evaluator 的性能门槛 FAIL；每个 variant 的 evaluator 单测部分仍通过。

| variant | all ΔmIoU | all ΔmF1 | all ΔF-mIoU | vs E70 ΔmIoU | vs E70 ΔmF1 | 结论 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| A1 w/o large-label rules | +0.142 | +1.924 | +5.897 | -2.899 | -3.003 | 移除 large-label 后退回 E39 级别；证明 E70 需要 carrier reliability repair |
| A1 w/o table-sink rules（保留 tissue） | +0.665 | +2.755 | +5.926 | -2.376 | -2.172 | `tissue-paper:cloth` 是可用正向；但缺 office2 table-sink 远低于 E70 |
| A1 bin-table only shape（tissue + shape bin） | +0.669 | +2.759 | +5.924 | -2.372 | -2.168 | shape-gated `bin:table` 几乎无全局增益，且没有修复 office2 |
| A1 no tissue shape（只保留 shape table-sink） | +0.111 | +1.855 | +5.782 | -2.930 | -3.072 | shape table-sink 单独不成立；office4 明显负迁移 |
| A3 shape-gated unified | +0.635 | +2.685 | +5.811 | -2.406 | -2.241 | bbox shape gate 比 naive 稍好但仍 FAIL；不能替代 scene-local E70 |
| A3 naive unified large rules | +0.495 | +2.297 | +4.903 | -2.546 | -2.630 | 全局 max-extent large-label relabel 已判负面 |

## 4. 正向改进清单

### 4.1 可直接保留的正向：E70 composite 作为内部 best / 投稿 anchor

- 价值：已经超过 ConceptGraphs，且过 evaluator。
- 限制：它是 scene-local composite，不能直接包装成“统一方法”主张；若论文要严谨，应把它作为 strong diagnostic composite 或用更强统一 gate 复现后再作为 main method。

### 4.2 可迁移的正向子模块：`tissue-paper:cloth:0.8`

证据：`A1_wo_table_sink_rules - A1_wo_large_label_rules`：all `+0.523 mIoU / +0.830 mF1`；office1 `+2.105 mIoU / +3.046 mF1`。

Monitor 证据显示它实际改动小：office1 只 relabel 1 个对象、600 pcd points；room0/room1/office3 也只是少量对象。它不像 table-sink 那样造成大面积误触发。

### 4.3 局部正向：office2 `bin:table` + `vent:table`

历史 E66/E69/E70 已证明：

- E66 office2 `bin:table:1.0`：office2 gap 到 `+6.254 mIoU / +5.457 mF1 / +20.397 F`。
- E69 office2 加 `vent:table:1.0`：office2 gap 到 `+6.492 mIoU / +5.521 mF1 / +21.442 F`。
- E70 继承该局部修复后全场景 PASS。

但本轮证明：**该局部修复不能按当前 naive/shape 形式全局化**。

### 4.4 可作为论文强贡献的正向：object-level diagnostic framework

E65 诊断发现 office2 `bin` 失败不是缺失 bin，而是大 table carrier 被读成 bin：GT bin recall `0.999884`，但 predicted bin precision 仅约 `0.060`；主 false-bin object 是 dominant GT table，bbox extent `[1.5395, 1.5640, 0.1219]`。这个诊断直接导向 E66/E69/E70。

本轮负例也反过来证明诊断框架有价值：shape gate 未命中 office2 的关键 `bin` 目标，却在 office3/office4 大量触发 `vent:table`，这类错误只能通过 object-level monitor 看清。

## 5. 已被证明负面的创新点 / 方法表述

### 5.1 负面：全局 naive large-label relabel

规则：`tissue-paper:cloth:0.8,bin:table:1.0,vent:table:1.0` 全场景应用。

结果：all 只有 `+0.495 / +2.297 / +4.903`，远低于 E70；负迁移包括 room2 ΔmIoU `-0.307`、office2 `-0.211/-1.264`、office4 `-6.383/-5.934`。

Monitor：office4 触发 `large_vent_to_table` 66 个对象 / 140,833 pcd points；office3 触发 47 个 `large_vent_to_table` / 102,769 pcd points。结论是：**不能把“见到大 vent/bin 就改成 table”作为论文方法。**

### 5.2 负面/不足：bbox shape-gated table-sink unified rule

规则：`bin:table:1.0:0.25,vent:table:1.0:0.25`，要求水平 extent 足够大且 z 厚度小。

结果：A3 shape-gated unified all `+0.635 / +2.685 / +5.811`，仍 FAIL，且 office2 `-0.191/-1.236`，office4 `-5.687/-5.004`。

更关键的是实现层面的 monitor：

- `A1_bin_table_only_shape` 在 office2 没有任何 `large_bin_to_table` 触发，说明当前 shape gate 没有命中 E65/E66 的关键 false-bin table carrier；只在 office3 触发 1 个 `large_bin_to_table`。
- `vent:table` shape gate 在 office4 触发 35 个对象 / 91,100 pcd points，直接对应 office4 collapse。

结论：**当前 bbox shape gate 不是合格的统一 carrier reliability gate。** 它既漏掉目标，又误伤其他场景。

### 5.3 负面：粗粒度 cushion→sofa broad relabel

历史 E67：`cushion:sofa:1.2` 虽然试图修复 room0/office2 sofa-cushion，但 room0 F-mIoU gap 到 `-4.851`，已拒绝。可保留的是 E70 中更窄的 `cushion:sofa:0.04` carve，不是 broad relabel。

### 5.4 不支持作为主创新：semantic-only/adaptive CLIP readout

E47/E48 已显示 adaptive/high-margin CLIP 可以避免部分 collapse，但不能复现 E70 的 office2 和全场景主增益。因此它是辅助读出诊断，不应作为主贡献。

### 5.5 未证明：two-layer graph memory 直接带来最终 mIoU superiority

A1/A3 没有否定 two-layer memory；但当前 E70 的可解释主增益来自 carrier/readout repair 和 object-level diagnostics。投稿表述应改为：two-layer graph 是在线状态维护、候选关联、诊断和 export/source separation 的基础；是否带来独立 mIoU 增益，需要 A2 单独证明。

## 6. 修改后的论文创新点分布建议

1. **主创新 1：Object-level diagnostic and carrier reliability analysis**（强支持）  
   用 E65/E70/A3 负例支撑：不是只看宏观 mIoU，而是定位到 object carrier、bbox、label sink、per-object relabel count/points。

2. **主创新 2：Geometry-first carrier repair with bounded reliability**（部分支持）  
   支持部分：E70、office2 局部修复、tissue 全局正向。  
   必须降级/限制：当前 naive/shape unified 不成立，不能声称已有简单统一规则解决所有场景。

3. **主创新 3：Two-layer graph memory for online state and diagnosis**（待 A2 支撑）  
   先写成系统架构与可观测性贡献，不要宣称它是 E70 主精度来源。

## 7. 下一步最小动作

1. **停止继续调 naive/shape table-sink 全局规则**；它已是负结果。
2. 若要冲主方法统一性，只能上更强 gate：需要至少包含 target-label support / object-level table evidence / surface orientation / local semantic agreement / scene-independent neighbor relation；不能只用 bbox max extent + thickness。
3. 立即补 A2：证明 graph memory 的状态/诊断价值；如果 A2 对 mIoU 无强正向，就把它放在 system/diagnostic contribution，不强行包装为精度主因。
4. 论文主表可保留 E70，但 main claim 必须写成“diagnosis-guided geometry reliability framework”，并明确当前 unified rule 的失败边界。

## 8. 已执行验证

- 184 远程复核：所有 submission ablation variants 已完成，无 tmux 任务，GPU 空闲。
- 本地同步 raw artifacts 到 `analysis/raw/submission_ablations_20260627/`。
- 本地此前测试：`PYTHONPATH=src python3 -B -m unittest discover -s tests -v`，152 tests OK。
- 本轮分析只更新文档和 raw result mirror；无新增生产代码改动。
