# ScanNet200 fullval official-evaluator result — 2026-04-23

## 状态

- 已在 `/home/nebula/xxy/3D_Reconstruction/work_dirs/ESAM_online_scannet200_CA_mv_fast_ab/` 收敛一组 **312 scenes / 13430 frames** 的 fullval 评测产物。
- 说明：这是一组 **ESAM-online 兼容执行链路的配置 ablation**（固定 backbone / 工程链路，切换 Rescue/Dedup 及运行约束），不是重新训练 ESAM 主干模型的独立重跑，也不是 DuoGraph3D 新模型替换试验。
- 本次已收敛主对照矩阵：
  - ESAM 严格基线（strict baseline / no-rescue no-dedup）
  - DuoGraph-style rescue-only（重跑后的 `retry2` 版本）
  - DuoGraph-style dedup-only
  - DuoGraph-style rescue+dedup
- 另有一条 ESAM-family 诊断变体：`2601_dedup_strict_fullval`。

## 最新量化结论

- 严格基线：AP=0.4135, AP50=0.6300, AP25=0.7886。
- no-rescue/no-dedup 独立同配置重跑（2026-04-23 fresh work-dir）：AP=0.4135, AP50=0.6300, AP25=0.7886；与 strict 数值一致，现已不再只是 alias 证据。
- Dedup-only：AP=0.4133, AP50=0.6244, AP25=0.7797。
- Rescue-only（retry2）：AP=0.4133, AP50=0.6286, AP25=0.7897。
- Rescue+dedup：AP=0.4051, AP50=0.6139, AP25=0.7708。
- ESAM-family dedup_strict 诊断：AP=0.3985, AP50=0.6024, AP25=0.7624。

## 关键观察

- fullval 下目前**尚无单一方法对所有 5 格形成显著 AP 增益**：当前最优值是严格基线 / 独立 no-rescue-no-dedup 同配置重跑（AP=0.4135），其余变体在 AP 上与之接近或略低。
- `fullval_neg05_v2_rescue_only_strict` 的第一版训练/测试日志不完整；`retry2` 版本已用于正式对照。
- 这批结果更多说明 fullval 流程可跑通与监控可用，而不是提供直接 main table 的胜负结论。

## 约束与下一步

1. 独立 no-rescue/no-dedup 同预算复验已经完成并归档，关闭了此前 alias-only 证据缺口。
2. 下一步将 fullval 矩阵与 subset5、OnlineAnySeg/ConceptGraphs 执行结果放入统一实验表，并明确 fullval AP 未提升的边界。
3. 投稿版仍以 story-aligned 外部对比（OnlineAnySeg, ConceptGraphs）优先，ESAM-family 仅作为兼容/可复现证据补充。
