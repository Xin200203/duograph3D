# DuoGraph3D × ConceptGraphs parity online-merge monitoring run — 2026-04-26

## 1. 实验设置审计

本轮是在已确认的 ConceptGraphs parity 设置上只增加监控，不改变评测协议：

- 数据：Replica `room0, room1, room2, office0, office1, office2, office3, office4`
- 输入：ConceptGraphs official `gsa_detections_none`
- 评测：ConceptGraphs `eval_replica_semseg.py`, `n_exclude=6`
- DuoGraph3D temporal variant：`temporal_naive_framewise`
- 不使用 DEVA annotation masks，不使用 GT sidecar
- 远端运行目录：`/home/nebula/xxy/duograph3d_artifacts/duograph3d_conceptgraphs_monitored_20260426`
- 本地归档：`docs/official_results/duograph3d_conceptgraphs_monitored_20260426/raw/`

## 2. 新增监控面

代码层新增 `PipelineConfig.emit_association_diagnostics` 与 `association_diagnostics_top_k`，在 Layer-2 association 中记录：

1. `association_candidate_diagnostic`：候选数量、best/second score、margin、strong identity 标志、top-k 候选、score components（geometry key、descriptor、confidence、continuity、appearance、geometry profile、relation bonus）。
2. `association_birth_diagnostic`：每次 birth 的原因，区分 `no_candidate`、`best_candidate_without_strong_identity`、`best_candidate_below_threshold`。
3. parity runner 侧额外记录：mask/深度/CLIP margin、obs-per-key、singleton key rate、track fragmentation、export object 点数、shadow under-merge candidate pairs、逐场景 gap。

## 3. 主要结果

| split | DuoGraph3D mIoU | ConceptGraphs mIoU | ΔmIoU | ΔmRecall | ΔmPrecision | ΔF-mIoU |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| all | 20.091 | 24.531 | -4.441 | -0.932 | +7.466 | -2.649 |
| office3 | 9.794 | 21.677 | -11.884 | +1.343 | -3.098 | -11.062 |
| office4 | 36.534 | 46.829 | -10.295 | -6.223 | -4.741 | -10.126 |
| room1 | 26.930 | 24.477 | +2.454 | +9.486 | +15.641 | -2.316 |

完整 CSV：`raw/duograph_monitored_results.csv` 与 `raw/duograph_monitored_gap_vs_conceptgraphs.csv`。

## 4. 关键监控数值

全 8 场景汇总：

- raw detections / kept observations / track keys：`109799 / 108992 / 9116`
- memory nodes / track fragmentation：`85144 / 76028`
- birth reasons：`no_candidate=75022`, `best_candidate_without_strong_identity=10122`
- shadow under-merge candidate pairs：`14428`
- low CLIP-margin observations：`87323`（约 80.1% kept observations）
- low valid-depth observations：`489`（约 0.45% kept observations）

逐场景 merge 监控：

| scene | keys | memory nodes | fragmentation | singleton-key rate | shadow pairs | no-candidate births | weak-identity births | p50 best score | ΔmIoU |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| room0 | 1279 | 13695 | 12416 | 0.273 | 1833 | 12492 | 1203 | 1.364 | +0.158 |
| room1 | 748 | 7936 | 7188 | 0.318 | 1118 | 6773 | 1163 | 1.363 | +2.454 |
| room2 | 1034 | 8674 | 7640 | 0.332 | 1645 | 7363 | 1311 | 0.794 | -3.767 |
| office0 | 1012 | 11387 | 10375 | 0.246 | 1810 | 10072 | 1315 | 1.236 | -3.588 |
| office1 | 651 | 6802 | 6151 | 0.246 | 1182 | 5682 | 1120 | 1.409 | -4.423 |
| office2 | 1252 | 11620 | 10368 | 0.281 | 2000 | 10304 | 1316 | 1.148 | -1.395 |
| office3 | 1562 | 13778 | 12216 | 0.300 | 2511 | 12418 | 1360 | 1.240 | -11.884 |
| office4 | 1578 | 11252 | 9674 | 0.322 | 2329 | 9918 | 1334 | 1.253 | -10.295 |

## 5. 差距来源判断

**主因：online merge/key fragmentation，而不是输入投影失败。**

证据：

- 候选构造经常失败：candidate count 的逐场景 p50 均为 `0`，`no_candidate` births 达 `75022`。
- 当前 key 是 `scene:gsa:label:voxel_x:voxel_y:voxel_z`，continuity key 也等于该 key；同一物体跨 voxel 或 label 轻微抖动时，Layer-2 很难形成 strong identity。
- `best_candidate_below_threshold=0`，说明本轮不是阈值过高导致的大面积失败，而是候选/identity 本身没有进入可合并状态。
- shadow under-merge proxy 找到 `14428` 对近邻同类高相似 key；office3/office4 分别为 `2511/2329`，是最大 gap 场景。
- valid depth 基本正常：低 valid-depth 仅约 `0.45%`，各场景 valid-depth p50 基本为 `1.0`。

**次因：语义边界不稳定会放大 fragmentation。**

- low CLIP-margin observation 占约 `80.1%`；office 场景更高（office1/office4 分别约 `86.8%/86.0%`）。
- key 内含 label，因此语义 top-1 在相近类别之间抖动会直接生成不同 tracks，而不是在同一个 object 中维护 label distribution。
- office3/office4 不只是保守 under-merge：二者 precision 也低于 ConceptGraphs（`-3.10/-4.74`），说明有显著语义/重复对象噪声；top shadow labels 集中在 `vent/monitor/picture/sofa/ceiling/floor` 等大平面或重复结构类别。

**整体 metric 形状支持该判断。**

- all split 上 DuoGraph3D precision 比 ConceptGraphs 高 `+7.47`，但 recall `-0.93`、F-mIoU `-2.65`：整体更像保守、碎片化、覆盖/融合不足。
- office3/office4 precision 也转负，是需要优先处理的失败场景；如果只调低阈值，可能会进一步伤害 precision。

## 6. 下一轮最小修复实验建议

1. **neighbor-key shadow merge ablation**：在 export 前或在线 memory 中，对同 label、近邻 voxel、CLIP similarity 高的 key 做受控合并，优先复验 office3/office4。
2. **candidate retrieval 扩展**：Layer-2 候选不应只依赖 exact geometry key；加入 spatial neighbor voxels + same/compatible label + centroid/point overlap，以验证 `no_candidate` 是否显著下降。
3. **semantic distribution key ablation**：将 hard label 从 geometry/continuity key 中解耦，object 维护 label histogram；检验 low-margin 场景是否减少 label-flip fragmentation。

## 7. 归档文件

- `raw/run_conceptgraphs_parity_with_monitoring.py`
- `raw/run.log`
- `raw/merge_monitor_summary.json`
- `raw/merge_monitor_report.md`
- `raw/duograph_monitored_results.csv`
- `raw/duograph_monitored_gap_vs_conceptgraphs.csv`
- `raw/reports/<scene>/diagnostic_event_sample_replica_<scene>_duograph3d_full.json`
