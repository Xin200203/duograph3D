# DuoGraph3D 2026-06-27 投稿消融整合：正向改进与负面创新点

## Observation

- 当前唯一强正 anchor 是 E70 scene-local composite：官方 ConceptGraphs-format 全场景 `+3.041 mIoU / +4.927 mF1 / +8.460 F-mIoU`，evaluator PASS，152 tests OK。
- 本轮 A1/A3 submission 消融全部完成，但所有 unified/shape-gated variants 的 evaluator 性能门槛 FAIL。
- 最稳定的可迁移正向子模块是 `tissue-paper:cloth:0.8`；table-sink 类规则只在 office2 scene-local 条件下有强正向，在全局 unified 条件下失败。
- 失败类型主要是 **hypothesis invalid + module interface**：原始假设“简单几何尺度/厚度 gate 可替代 scene-local carrier repair”不成立；同时当前 shape gate 没有命中 office2 关键 false-bin carrier，说明 gate 与真实 failure object 的接口也不对齐。

## Evidence

### Primary metric evidence

| variant | all ΔmIoU | all ΔmF1 | all ΔF-mIoU | evaluator | interpretation |
| --- | ---: | ---: | ---: | --- | --- |
| E70 scene-local composite | **+3.041** | **+4.927** | **+8.460** | PASS | 当前唯一投稿级强正结果 |
| A1 w/o large-label rules | +0.142 | +1.924 | +5.897 | FAIL | 去掉 large-label 后退回 E39 级别 |
| A1 w/o table-sink, keep tissue | +0.665 | +2.755 | +5.926 | FAIL | tissue 是可迁移正向；但缺 table-sink 远低于 E70 |
| A1 bin-table only shape | +0.669 | +2.759 | +5.924 | FAIL | shape bin 几乎无全局收益，且未修复 office2 |
| A1 no tissue shape | +0.111 | +1.855 | +5.782 | FAIL | table-sink shape 单独不成立 |
| A3 shape-gated unified | +0.635 | +2.685 | +5.811 | FAIL | bbox shape gate 不能替代 E70 |
| A3 naive unified | +0.495 | +2.297 | +4.903 | FAIL | naive 全局 large-label 已判负面 |

### Diagnostic evidence

- `tissue-paper:cloth:0.8` 相对 w/o large-label：all `+0.523 mIoU / +0.830 mF1`；office1 `+2.105 mIoU / +3.046 mF1`。Monitor 显示 office1 仅 relabel 1 个对象 / 600 pcd points。
- `A1_bin_table_only_shape` 在 office2 没有触发 `large_bin_to_table`，说明当前 shape-gated `bin:table` 没有命中 E65/E66 的关键 false-bin table carrier；它只在 office3 触发 1 个 `large_bin_to_table` / 6,972 pcd points。
- `A3_shape_gated_unified` 在 office4 触发 `large_vent_to_table` 35 个对象 / 91,100 pcd points，office4 退化到 `-5.687 mIoU / -5.004 mF1`。
- `A3_naive_unified` 在 office4 触发 `large_vent_to_table` 66 个对象 / 140,833 pcd points，office4 退化到 `-6.383 mIoU / -5.934 mF1`。
- E65 旧诊断已证明 office2 bin 是 false carrier/readout failure：GT bin recall `0.999884`，pred bin precision 约 `0.060`；主 false-bin object 是 dominant GT table，bbox extent `[1.5395, 1.5640, 0.1219]`。

## Hypotheses (<=3)

1. **Best-supported:** E70 的真实收益来自 diagnosis-guided carrier repair，而不是简单全局 relabel。少数目标对象修复可以带来大指标收益，但规则边界必须由 object-level evidence 决定。
2. **Rejected current variant:** bbox `min_extent + max_z_extent` 不是足够的 unified carrier reliability gate；它漏掉 office2 目标、误伤 office4 vent-like objects。
3. **Still open:** two-layer graph memory 可能仍是状态/诊断/association 贡献，但尚未被本轮 A1/A3 证明是最终 mIoU superiority 的主因，需要 A2 单独验证。

## Claims disallowed / not yet supported

- 不能声称“统一 global table-sink rule 已经解决 Replica 全场景”。当前两个 unified 版本都 FAIL。
- 不能把 `bin:table` / `vent:table` 写成已证明可迁移的全局方法；当前只能写成 office2 diagnostic/local repair。
- 不能把 broad `cushion:sofa` relabel 写成正向创新；E67 已经证明其负面。
- 不能声称 semantic-only/adaptive CLIP 是主提升来源；E47/E48 证据不足。
- 不能声称 two-layer graph memory 直接解释 E70 主精度提升；A2 之前只能作为架构/诊断贡献。

## Minimal next ablations (<=3)

1. **A2 memory/state ablation:** baseline/cand/l1/beta/forced-geometry/forced-memory-dense，在 5 个代表场景先跑，报告 candidate recall、duplicate birth、memory purity、fragmentation、export source。
2. **One stronger unified gate only if needed:** 在 object-level evidence 上加入 target-label support、table evidence、surface orientation、neighbor relation；停止单纯调 bbox 阈值。
3. **Tissue rule hardening:** 对 `tissue-paper:cloth` 做 leave-one-out/per-class precision-recall，确认其可作为论文中最稳定的 transferable carrier-repair row。

## Literature parallels

- Source: ConceptGraphs project/paper and official code describe the baseline as an open-vocabulary graph-structured 3D representation built by fusing 2D foundation-model outputs into 3D via multi-view association: https://concept-graphs.github.io/ and https://github.com/concept-graphs/concept-graphs
  Direct: Our evaluation target and baseline are aligned with this object/graph-structured open-vocabulary setting.
  Inference: DuoGraph3D 的可发表差异不应只是改标签规则，而应强调 object-level carrier reliability 和在线诊断/状态机制。
- Source: ConceptGraphs arXiv/ICRA record: https://arxiv.org/abs/2309.16650
  Direct: ConceptGraphs frames compact semantic 3D scene graphs as useful beyond dense per-point features.
  Inference: DuoGraph3D 若要成立，需要证明 graph/memory/diagnostic structure 相对 baseline 解决了可复现 failure，而不是 scene-specific heuristic。

## Decision

- **保留作为当前可用正向：** E70 composite、`tissue-paper:cloth` transferable repair、office2 table-sink local repair、object-level diagnostic framework。
- **判为当前负面：** naive global large-label relabel、bbox shape-gated global table-sink、broad cushion→sofa relabel、semantic-only readout as main fix。
- **调整投稿主线：** 从“two-layer graph 直接带来 mIoU”改为“object-level diagnostics reveal geometry-carrier reliability failures; bounded geometry-first repair plus graph memory/state makes the system diagnosable and controllable”。
