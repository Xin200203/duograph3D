# DuoGraph3D × ConceptGraphs engineering parity optimization — 2026-04-26

本轮目标：在 **不改变 ConceptGraphs 对比协议** 的前提下，把 ConceptGraphs 已有的工程技巧尽量吸收到 DuoGraph3D 的 parity runner 里，再完整跑一轮 Replica 8 场景对比。

## 1. 设置审计

保持不变的公平对比设置：

- 数据：Replica `room0, room1, room2, office0, office1, office2, office3, office4`
- 输入：ConceptGraphs official `gsa_detections_none`
- 评测：ConceptGraphs `eval_replica_semseg.py`, `n_exclude=6`
- 不使用 DEVA annotation masks，不使用 GT sidecar
- DuoGraph3D temporal variant：`temporal_naive_framewise`
- 远端运行目录：`/home/nebula/xxy/duograph3d_artifacts/duograph3d_conceptgraphs_engineered_20260426`
- 本地归档：`docs/official_results/duograph3d_conceptgraphs_engineered_20260426/raw/`

本轮新增 runner：`examples/run_conceptgraphs_engineered_parity.py`。

## 2. 吸收的 ConceptGraphs 工程技巧

这轮不是改评测，而是让 DuoGraph3D 的输入清洗和导出后处理更像 ConceptGraphs：

1. **class-agnostic online identity**：在线 key 从 `label + 0.75m voxel` 改成 `item + 0.20m voxel`。意思是先不要因为 CLIP top-1 类别抖动就拆成不同物体；类别只作为统计直方图保留。
2. **SAM/GSA mask 清洗**：加入 `mask_subtract_contained`，把被大 mask 包住的小/重叠区域扣掉，减少单帧碎片和互相覆盖。
3. **检测置信度过滤**：只保留 `mask_confidence >= 0.95`，对齐 ConceptGraphs 常用的高置信 mask 设置。
4. **大框过滤**：去掉 bbox 超过图像面积 `50%` 的超大 mask，减少墙/地板/整片背景污染。
5. **深度有效点过滤**：每个 mask 至少要有 `16` 个有效深度点。
6. **更多几何点**：每个 observation 采样点从旧 runner 的较少点数提高到 `160`，后处理前最多保留 `8192` 点，导出对象最多 `4096` 点。
7. **ConceptGraphs-style point cloud postprocess**：导出前对 key objects 执行 `process_pcd -> denoise_objects -> filter_objects(min detections=3) -> merge_objects`。
8. **class-agnostic text anchor**：post-merge text feature 固定成 `item` anchor，避免语义 top-1 噪声阻止几何/视觉上应该合并的对象。
9. **保留监控**：继续记录 raw/kept detections、key 数、memory nodes、fragmentation、birth reasons、shadow under-merge pairs、低 CLIP margin、过滤数量等。

## 3. 主要结果

| scene | old Duo mIoU | engineered Duo mIoU | Δ vs old | ConceptGraphs mIoU | engineered gap |
| --- | ---: | ---: | ---: | ---: | ---: |
| room0 | 21.493 | 25.250 | +3.756 | 21.335 | +3.915 |
| room1 | 26.930 | 22.986 | -3.944 | 24.477 | -1.490 |
| room2 | 23.203 | 24.615 | +1.412 | 26.970 | -2.355 |
| office0 | 16.460 | 17.677 | +1.217 | 20.048 | -2.371 |
| office1 | 10.058 | 12.407 | +2.349 | 14.481 | -2.074 |
| office2 | 20.495 | 16.436 | -4.059 | 21.890 | -5.454 |
| office3 | 9.794 | 17.640 | +7.846 | 21.677 | -4.037 |
| office4 | 36.534 | 43.829 | +7.295 | 46.829 | -3.000 |
| all | 20.091 | 20.566 | +0.475 | 24.531 | -3.965 |

结论：

- 工程化版本让全量 mIoU 从 `20.091` 提到 `20.566`，对 ConceptGraphs 的 gap 从 `-4.441` 缩小到 `-3.965`。
- 最大改善在 `office3 (+7.846)`、`office4 (+7.295)`、`room0 (+3.756)`。
- 明显回退在 `room1 (-3.944)`、`office2 (-4.059)`。
- 所以这些工程技巧 **确实修复了一部分碎片/噪声问题**，但还没有解决 DuoGraph3D 相比 ConceptGraphs 的核心 gap。

完整 CSV：

- `raw/duograph_monitored_results.csv`
- `raw/duograph_monitored_gap_vs_conceptgraphs.csv`

## 4. 关键监控数值对比

| 指标 | old monitored | engineered | 变化 |
| --- | ---: | ---: | ---: |
| raw detections | 109,799 | 109,799 | 0 |
| kept observations | 108,992 | 80,054 | -28,938 |
| track keys | 9,116 | 9,931 | +815 |
| exported objects after postprocess | n/a | 2,308 | n/a |
| memory nodes | 85,144 | 72,329 | -12,815 |
| track fragmentation | 76,028 | 62,398 | -13,630 |
| shadow under-merge candidate pairs | 14,428 | 49,220 | +34,792 |
| low CLIP-margin observations | 87,323 | 63,492 | -23,831 |
| low valid-depth observations | 489 | 392 | -97 |
| no-candidate births | 75,022 | 61,977 | -13,045 |
| weak-identity births | 10,122 | 10,352 | +230 |
| low-confidence masks filtered | n/a | 22,189 | n/a |
| large-bbox masks filtered | n/a | 2,993 | n/a |
| subtracted mask pixels | n/a | 1,422,079,698 | n/a |

解释：

- 过滤和后处理让 memory nodes、fragmentation、no-candidate births 都下降，说明“重复出生/碎片化”确实被缓解了一部分。
- 但 exported objects 仍是 `2,308`，而 GT-aware baseline 监控里 ConceptGraphs baseline 约 `620` 个对象；DuoGraph3D 仍明显更碎。
- shadow under-merge pairs 反而升到 `49,220`，主要因为 class-agnostic + 细 voxel 产生了更多“看起来应该还能继续合并”的近邻对象候选。这说明后处理还不够强，或者在线阶段应该给 Layer-2 更好的候选召回。

## 5. 分场景 merge 监控

| scene | keys | export objs | memory nodes | fragmentation | singleton-key rate | shadow pairs | no-candidate births | weak-identity births | eval mIoU | ΔmIoU vs CG |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| room0 | 1498 | 306 | 11871 | 10373 | 0.317 | 8856 | 10607 | 1264 | 25.250 | +3.915 |
| room1 | 1073 | 208 | 7078 | 6005 | 0.349 | 7169 | 5825 | 1253 | 22.986 | -1.490 |
| room2 | 1164 | 256 | 7371 | 6207 | 0.326 | 7345 | 6008 | 1363 | 24.615 | -2.355 |
| office0 | 1155 | 267 | 9735 | 8580 | 0.250 | 6063 | 8402 | 1333 | 17.677 | -2.371 |
| office1 | 634 | 154 | 5875 | 5241 | 0.235 | 2489 | 4751 | 1124 | 12.407 | -2.074 |
| office2 | 1209 | 328 | 9864 | 8655 | 0.296 | 4513 | 8540 | 1324 | 16.436 | -5.454 |
| office3 | 1582 | 403 | 11415 | 9833 | 0.335 | 7501 | 10138 | 1277 | 17.640 | -4.037 |
| office4 | 1616 | 386 | 9120 | 7504 | 0.356 | 5284 | 7706 | 1414 | 43.829 | -3.000 |

## 6. 小规模 ablation 记录

在远端跑全量前，先做了几组小规模验证：

1. `voxel=0.75`, class-agnostic, no label split：`room0 mIoU=11.35`，明显过合并。结论：拿掉 label 后不能继续用 0.75m 大格子。
2. `voxel=0.30`, class-agnostic, no label split：部分场景有效，但 `room1=19.405`、`office3=16.604` 不稳定。
3. `voxel=0.30`, label split enabled：`room1=28.388` 变好，但 `office3=12.606` 变差，并且违背 class-agnostic 减少 label-flip fragmentation 的方向。
4. 最终选择 `voxel=0.20`, class-agnostic, no label split：全 8 场景完成，整体最稳。

## 7. 与 ConceptGraphs 仍有差距的主要原因

用简单话说：ConceptGraphs 像是“先收很多碎片，然后用很强的后处理把碎片揉成少量干净物体”；当前 DuoGraph3D 虽然加了类似后处理，但在线 Layer-2 仍然先出生了太多 memory nodes，导出后还剩太多对象。

证据：

1. **对象数仍然偏多**：engineered export 后还有 `2,308` objects；ConceptGraphs baseline 约 `620` objects。对象太多通常意味着同一个真实物体被切成多个预测物体。
2. **Layer-2 召回仍弱**：`no_candidate births=61,977`，说明大量 observation 没找到可关联对象，仍然新建 ID。
3. **weak identity 没改善**：weak-identity births 从 `10,122` 到 `10,352`，几乎没好，说明强 identity 判断仍然卡住。
4. **postprocess 合并不够彻底**：shadow under-merge pairs 高达 `49,220`，表示还有很多近邻、高相似对象没有合并。
5. **precision 优势变小**：all precision 从旧的 `+7.466` 变成 `+0.958`，说明强过滤/合并改善 recall/gap 的同时，也带来一些语义或过合并风险。

## 8. 下一步建议

1. **把 ConceptGraphs overlap merge 前移到 Layer-2 candidate retrieval**：不要只靠 exact key 找候选，加入近邻 voxel、点云 overlap、centroid distance、CLIP similarity。
2. **做受控二次 merge**：对 shadow under-merge pairs 中高 overlap / 高 visual similarity / 不冲突 semantic histogram 的对象再合并一轮。
3. **对 room1 与 office2 做错误样例审计**：这两个场景是本轮回退来源，需要确认是过合并、过滤过强，还是 label histogram 选错。
4. **重跑 GT-aware layer monitor for engineered variant**：当前已有在线/评测监控，但还没有把本轮 engineered export 放进 GT-aware layer monitor 重新算 duplicate rate、ID switch rate、object duplicate rate。

## 9. 归档文件

- `raw/run_conceptgraphs_engineered_parity.py`
- `raw/run.log`
- `raw/merge_monitor_summary.json`
- `raw/merge_monitor_report.md`
- `raw/duograph_monitored_results.csv`
- `raw/duograph_monitored_gap_vs_conceptgraphs.csv`
- `raw/duograph_monitored_conf_matrices.pkl.gz`
- `raw/reports/<scene>/bounded_slice_replica_<scene>.json`
- `raw/reports/<scene>/diagnostic_event_sample_replica_<scene>_duograph3d_full.json`
