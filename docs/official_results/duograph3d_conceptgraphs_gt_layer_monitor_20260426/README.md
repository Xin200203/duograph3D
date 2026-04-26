# DuoGraph3D × ConceptGraphs GT-aware layer monitor — 2026-04-26

本轮补足了分层监控：利用 Replica semantic GT，把单帧初始化、Layer 1、Layer 2 和 ConceptGraphs baseline 的对象级概率/重复率分开统计。

> 注意：当前可用 GT 是 semantic point map，不是完整 instance-ID GT。因此这里的 `GT target` 定义为 **GT semantic class + 1m GT cell**，用于近似衡量局部重复、错误合并和 ID switch；它不是严格实例级 ID 指标。

## 1. 新增指标

### Init / SAM-GSA 单帧初始化
- observation semantic accuracy：每个 SAM/GSA mask 投影点的多数 GT 类是否等于 CLIP top-1 label。
- per-frame duplicate rate：同一帧里落到同一 GT semantic-cell 的重复 masks 比例。
- per-frame overseg factor：每个 GT semantic-cell 平均被多少个 masks 覆盖。
- CLIP top-1 probability / entropy / margin。

### Layer 1 后
- hypothesis semantic accuracy。
- hypothesis target purity。
- per-frame duplicate rate after Layer 1。
- false-merge hypothesis rate：一个 hypothesis 内含多个 GT semantic-cell。
- merge-pair precision / error rate。

### Layer 2 后
- decision accuracy：正确 birth + 正确 association / 总有效决策。
- duplicate birth rate：GT target 已出现过但仍 birth 新 ID 的比例。
- association accuracy。
- ID switch rate per revisit。
- GT target fragmentation。
- multi-target memory object rate。

### Baseline / ConceptGraphs
- baseline object semantic accuracy。
- baseline object duplicate rate by GT semantic-cell。
- object CLIP top-1 probability / margin / entropy。

## 2. 汇总结果

| 指标 | 数值 |
| --- | ---: |
| valid eval observations | 57,191 |
| Layer1 eval hypotheses | 46,522 |
| Layer2 valid decisions | 46,522 |
| Layer2 decision accuracy | 10.23% |
| Layer2 duplicate birth rate | 98.37% |
| Layer2 ID switch events | 43,268 |
| Layer2 GT-target fragmentation | 41,746 |

## 3. 分场景表

| scene | init dup p50 | layer1 dup p50 | layer1 false merge | layer2 acc | duplicate birth rate | id switch rate | baseline obj acc | baseline obj dup |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| room0 | 0.333 | 0.227 | 0.113 | 0.087 | 0.986 | 0.942 | 0.326 | 0.087 |
| room1 | 0.368 | 0.250 | 0.094 | 0.149 | 0.980 | 0.904 | 0.432 | 0.189 |
| room2 | 0.348 | 0.250 | 0.066 | 0.100 | 0.982 | 0.948 | 0.212 | 0.231 |
| office0 | 0.385 | 0.300 | 0.063 | 0.095 | 0.984 | 0.962 | 0.326 | 0.186 |
| office1 | 0.385 | 0.273 | 0.109 | 0.178 | 0.986 | 0.881 | 0.417 | 0.167 |
| office2 | 0.421 | 0.339 | 0.084 | 0.081 | 0.986 | 0.965 | 0.178 | 0.244 |
| office3 | 0.429 | 0.341 | 0.060 | 0.079 | 0.983 | 0.971 | 0.193 | 0.298 |
| office4 | 0.333 | 0.250 | 0.017 | 0.095 | 0.977 | 0.953 | 0.118 | 0.235 |

## 4. 解读

1. **初始化阶段已经有明显重复。** 单帧 init duplicate p50 在 `0.333–0.429`，说明一个 GT semantic-cell 在同一帧经常被多个 SAM/GSA fragments 覆盖。
2. **Layer 1 有帮助但不够。** Layer1 dup p50 降到 `0.227–0.341`，确实减少重复；但 office2/office3 仍高，说明 Layer1 没有充分处理 SAM 单帧碎片化。
3. **Layer 1 还有 false merge 风险。** false-merge rate 多数为 `6%–11%`，说明不能简单暴力合并所有近邻碎片。
4. **Layer 2 是当前最大断点。** decision accuracy 只有 `8%–18%`，duplicate birth rate 约 `98%`，ID switch rate 约 `88%–97%`；这表明大量已出现过的 GT target 仍被 birth 成新 memory ID。
5. **ConceptGraphs baseline 对象更少、重复率更低。** 例如 office3 baseline object duplicate rate `0.298`，而 DuoGraph3D export object duplicate rate 在 raw summary 中为 `0.835`；baseline 虽然语义准确率也不高，但对象级聚合明显更强。

## 5. 归档

- `raw/run_conceptgraphs_gt_layer_monitor.py`
- `raw/run.log`
- `raw/gt_layer_monitor_summary.json`
- `raw/gt_layer_monitor_report.md`
