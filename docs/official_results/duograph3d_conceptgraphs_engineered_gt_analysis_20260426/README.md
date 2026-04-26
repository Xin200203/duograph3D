# DuoGraph3D × ConceptGraphs engineered GT-aware comparison — 2026-04-26

这轮回答两个问题：

1. **基于 GT 代理目标看，模仿 ConceptGraphs 工程技巧后，到底改善了哪一层？**
2. **既然 ConceptGraphs 的对象级聚合/后处理更强，为什么 DuoGraph3D 不能直接学习？**

先给结论：**可以学，而且本轮已经学到了一部分；但目前主要只是把 ConceptGraphs 的优势放到了输入清洗和最终导出后处理，尚未真正放进 DuoGraph3D 的 Layer-2 在线关联决策里。** 所以它能明显减少最终对象重复，但还没有根治 online duplicate birth / ID switch。

> 说明：这里的 GT target 仍然是 `GT semantic class + 1m GT cell` 代理目标，不是真正 instance-ID GT。它适合判断“重复、碎片、ID switch 趋势”，不能当成严格 instance segmentation 指标。

## 1. 本轮执行内容

脚本：`examples/run_conceptgraphs_gt_layer_monitor.py --profile engineered --skip-object-export`

设置：

- 输入仍是 ConceptGraphs official `gsa_detections_none`
- 使用 engineered runner 同样的初始化策略：
  - class-agnostic key: `item + 0.20m voxel`
  - `mask_subtract_contained`
  - confidence `>=0.95`
  - 大 bbox 过滤
  - 最少 16 个有效深度点
  - 每个 observation 采样 160 个 3D 点
- DuoGraph3D object monitor 读取上一轮完整实验产物：`duograph3d_gsa_engineered_monitor`
- ConceptGraphs baseline 读取：`none_overlap_maskconf0.95_simsum1.2_dbscan.1_merge20_masksub`

远端输出：

`/home/nebula/xxy/duograph3d_artifacts/duograph3d_conceptgraphs_engineered_gt_analysis_20260426`

本地归档：

`docs/official_results/duograph3d_conceptgraphs_engineered_gt_analysis_20260426/raw/`

## 2. 总体 GT-aware 结果

| 指标 | old DuoGraph3D | engineered DuoGraph3D | ConceptGraphs baseline |
| --- | ---: | ---: | ---: |
| valid eval observations | 57,191 | 43,369 | n/a |
| Layer1 eval hypotheses | 46,522 | 41,990 | n/a |
| Layer2 decision accuracy | 10.23% | 11.65% | n/a |
| Layer2 duplicate birth rate | 98.37% | 98.25% | n/a |
| Layer2 ID switch events | 43,268 | 38,335 | n/a |
| exported object count | 9,116 | 2,308 | 620 |
| valid eval object count | 3,227 | 751 | 338 |
| object semantic-cell duplicate rate | 82.15% | 45.54% | 21.01% |
| object semantic accuracy | 12.30% | 25.03% | 26.33% |

### 直观解释

把一个真实物体想象成一盒彩笔：

- old DuoGraph3D：同一盒彩笔被拆成很多小包，最后有 `9,116` 个包，重复率 `82.15%`。
- engineered DuoGraph3D：我们学了 CG 的过滤和合并技巧后，小包少了很多，变成 `2,308` 个包，重复率降到 `45.54%`。
- ConceptGraphs：仍然只有 `620` 个包，重复率 `21.01%`。

所以：**我们已经学到了一部分，但还没有学到 ConceptGraphs 最关键的“把碎片稳定揉成对象”的能力。**

## 3. 分层结果：哪一层改善了？

| scene | old init dup p50 | eng init dup p50 | old L1 dup p50 | eng L1 dup p50 | old L2 acc | eng L2 acc | old obj dup | eng obj dup | CG obj dup |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| room0 | 0.333 | 0.192 | 0.227 | 0.182 | 0.087 | 0.095 | 0.812 | 0.446 | 0.087 |
| room1 | 0.368 | 0.222 | 0.250 | 0.200 | 0.149 | 0.152 | 0.739 | 0.329 | 0.189 |
| room2 | 0.348 | 0.214 | 0.250 | 0.167 | 0.100 | 0.114 | 0.820 | 0.429 | 0.231 |
| office0 | 0.385 | 0.275 | 0.300 | 0.257 | 0.095 | 0.108 | 0.839 | 0.509 | 0.186 |
| office1 | 0.385 | 0.200 | 0.273 | 0.200 | 0.178 | 0.204 | 0.833 | 0.485 | 0.167 |
| office2 | 0.421 | 0.304 | 0.339 | 0.282 | 0.081 | 0.096 | 0.849 | 0.578 | 0.244 |
| office3 | 0.429 | 0.310 | 0.341 | 0.294 | 0.079 | 0.095 | 0.835 | 0.421 | 0.298 |
| office4 | 0.333 | 0.261 | 0.250 | 0.167 | 0.095 | 0.125 | 0.821 | 0.341 | 0.235 |

平均 p50：

- init duplicate p50：`0.375 -> 0.247`
- Layer1 duplicate p50：`0.279 -> 0.218`

解释：

1. **初始化层确实变干净了。** mask 过滤、置信度过滤、contained subtraction 明显降低了单帧重复。
2. **Layer1 也变干净了。** 因为输入碎片少了，Layer1 repair 后的重复也下降。
3. **Layer2 只小幅改善。** decision accuracy 只从 `10.23%` 到 `11.65%`，duplicate birth rate 仍约 `98%`。这说明最大的断点仍是在线 memory association。
4. **最终对象层大幅改善，但仍弱于 CG。** object duplicate rate 从 `82.15%` 降到 `45.54%`，但 CG 是 `21.01%`。

## 4. 为什么“学了 CG”但还不够？

因为 ConceptGraphs 的优势不只是某一个阈值，而是一整套对象生命周期：

### 4.1 我们已经学到的部分

这些已经有效：

- 去掉低置信 mask
- 去掉超大背景 mask
- 扣掉 contained mask 重叠区域
- class-agnostic text / identity，减少 label 抖动造成的碎片
- 最终导出前做点云 denoise/filter/merge

GT 证据：

- object count：`9,116 -> 2,308`
- object duplicate rate：`82.15% -> 45.54%`
- object semantic accuracy：`12.30% -> 25.03%`，几乎追到 CG 的 `26.33%`

### 4.2 还没有真正学到的部分

ConceptGraphs 更强的地方在于：它把“对象级聚合”当作核心流程；而我们目前更多是在 **最后导出时补救**。

高中生版本解释：

- ConceptGraphs 像是边整理边把同一本书的散页装订起来。
- 当前 DuoGraph3D 像是先把每页都单独编号，最后再尝试把散页夹起来。
- 最后再夹当然有帮助，但前面已经产生了太多编号、太多关系、太多错误历史；很多东西很难完全补回来。

具体到架构：

1. **Layer2 candidate retrieval 仍太窄。** 现在大量决策找不到候选，直接 birth 新 ID。engineered 后 duplicate birth rate 仍是 `98.25%`。
2. **strong identity 仍太硬。** 即使两个 observation 很像同一物体，只要 key/identity 条件不满足，就很难 association。
3. **postprocess 太晚。** 导出后 merge 能减少 pkl objects，但不能修正在线阶段已经发生的 ID switch、relation edge、memory node 历史。
4. **CG 的 overlap merge 是对象级决策。** 它用点云 overlap、视觉相似、text 相似、detections 数量等一起判断；DuoGraph3D Layer2 目前还没有等价地把这些作为候选召回和关联准则。

## 5. 为什么不能直接照搬？

不是不能，而是不能“无脑照搬”。原因有三个：

1. **任务形态不同。** ConceptGraphs 可以更偏全局/离线地后处理对象；DuoGraph3D 的 Layer2 是在线 memory，需要保持 ID、关系、历史决策一致。
2. **过合并风险真实存在。** 早期 ablation 里 class-agnostic `0.75m` key 让 `room0 mIoU` 掉到 `11.35`，说明简单放宽合并会把不同物体揉坏。
3. **需要把 CG 技巧翻译成 DuoGraph3D 的两层架构。** 也就是：不是只在 export 前调用 merge，而是把 overlap / visual / semantic histogram 变成 Layer2 的 candidate retrieval 和 association evidence。

好消息是：GT 结果显示 Layer1 engineered false-merge rate 只有约 `0.1%–0.6%`，说明在当前过滤后，**还有继续合并碎片的空间**。下一步应该更大胆地学 CG，但要用 GT monitor 防止过合并。

## 6. 下一步应该怎样真正学习 CG 优势？

建议按三个最小实验推进：

### 实验 A：Layer2 neighbor-overlap candidate retrieval

把候选从 exact key 扩展为：

- 邻近 voxel / centroid radius
- 点云 overlap
- CLIP visual similarity
- semantic histogram compatibility
- detection count / confidence

目标监控：

- `no_candidate births` 大幅下降
- `duplicate_birth_rate` 从约 `98%` 明显下降
- object duplicate rate 继续接近 CG 的 `21%`

### 实验 B：online memory consolidation

不是等到 export 才 merge，而是每隔 N 帧对 memory objects 做一次安全合并：

- overlap 高
- visual similarity 高
- semantic histogram 不冲突
- 合并后 relation edges 做 canonical ID remap

目标：减少 ID switch 和 memory fragmentation。

### 实验 C：GT-oracle upper bound

用 GT semantic-cell proxy 做一个只用于诊断的 oracle merge：

- 如果 oracle merge 能把 DuoGraph3D mIoU 拉近 CG，说明 merge 空间确实存在。
- 如果 oracle merge 也不行，则说明问题更多在语义标签/点云投影，而不是 merge。

## 7. 当前决策

**我们可以学习 ConceptGraphs 的优势，而且应该继续学。**

但正确方向不是“再加一个最终后处理”，而是：

> 把 ConceptGraphs 的 overlap/object merge 思想前移到 DuoGraph3D Layer2，让在线候选召回、strong identity、memory consolidation 都使用对象级 overlap + visual similarity + semantic histogram。

本轮 GT 证据支持这个判断：输入和导出层已经明显改善，Layer2 仍是最大瓶颈。

## 8. 归档文件

- `raw/gt_layer_monitor_summary.json`
- `raw/gt_layer_monitor_report.md`
- `raw/gt_engineered_vs_legacy_and_cg.csv`
- `raw/run.log`
- `raw/run_conceptgraphs_gt_layer_monitor.py`
