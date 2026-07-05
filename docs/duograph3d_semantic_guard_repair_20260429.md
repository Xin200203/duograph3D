# DuoGraph3D semantic-guard repair record — 2026-04-29

## 修复目标

上一轮 single-scene 结果显示：Layer2 的重复 birth 与 ID switch 已经下降，但最终 mIoU / mPrecision 没有同步提升。代码审查定位到两个主要问题：

1. `point_overlap` 同时负责候选召回和 strong identity 判定，容易把接触/包含关系误判成同一 object。
2. memory-dense export 按 memory root 聚合后用 majority label 输出，导致 mixed root 中的小物体语义被大物体吞掉，典型表现是 `pillow` 在最终导出中消失。

## 已实现修复

- 收紧 Layer2 strong identity：
  - `point_overlap` 仍可用于候选召回和加分；
  - 默认不再允许 `point_overlap` 自己充当 spatial evidence；
  - history point-overlap boost 同样默认要求独立 spatial evidence。
- 收紧 residual absorption：
  - 提高默认语义/overlap/score gate；
  - 要求 history identity、独立 spatial 或 same-geometry 证据之一成立。
- 增加 object merge semantic conflict guard：
  - 基于左右 object 的 class-count top label、merged entropy、top-label share、small-label share 判断是否疑似“小物体被大物体吸收”；
  - semantic conflict 时不执行 object merge。
- 修复 memory-dense export 语义坍缩：
  - online memory root 仍作为 identity authority；
  - dense export 先按原始 per-key label bucket 保留可拆分材料；
  - 默认只对语义混合的 root 做 label split，避免对干净 root 过度拆分；
  - 阈值：root label entropy >= 0.5 且 top-label share <= 0.9。
- 修复 GT monitor artifact 口径：
  - GT monitor 写 `full_pcd_<name>_gt_monitor.pkl.gz`；
  - object monitor 优先读取本次 export path，避免覆盖/误读 official parity runner 的 pkl。

## 回归测试

- Local `python3 -m py_compile ...`: PASS
- Local `PYTHONPATH=src python3 -m unittest discover -s tests -v`: PASS, 107 tests
- Remote `PYTHONPATH=src python -m unittest discover -s tests -v`: PASS, 107 tests
- 新增核心回归：
  - point-overlap 不能在没有独立 spatial evidence 时自证 strong identity；
  - semantic-conflict guard 阻止 bed/large object 吸收 pillow/small object；
  - residual absorption 仍可在明确同帧碎片情况下工作。

## 官方评测结果

### room1：主要问题场景

| run | mIoU | mRecall | mPrecision | mF1 | F-mIoU |
| --- | ---: | ---: | ---: | ---: | ---: |
| layer2 fix before semantic guard | 21.748 | 40.961 | 22.338 | 25.152 | 35.742 |
| semantic guard, split all labels | 23.852 | 43.197 | 26.019 | 28.321 | 40.719 |
| semantic guard, adaptive split | 27.920 | 45.804 | 46.092 | 33.522 | 36.163 |
| ConceptGraphs baseline | 24.531 | 40.216 | 36.180 | 30.122 | 36.238 |

结论：

- 相比 layer2 fix：mIoU +6.172，mPrecision +23.753，mF1 +8.370。
- 相比 ConceptGraphs：mIoU +3.389，mRecall +5.588，mPrecision +9.912，mF1 +3.399，F-mIoU 基本持平（-0.074）。
- 自适应 split 是本轮最有效的最终评测修复；全量 label split 虽能恢复 pillow，但 precision 仍不足。

### room0：泛化检查

| run | mIoU | mRecall | mPrecision | mF1 | F-mIoU |
| --- | ---: | ---: | ---: | ---: | ---: |
| semantic guard, split all labels | 19.427 | 35.284 | 31.447 | 25.414 | 40.991 |
| semantic guard, adaptive split | 19.346 | 34.980 | 31.418 | 25.292 | 40.877 |

结论：

- room0 没有从 adaptive split 获得收益，说明该场景的主要瓶颈不是 pillow-style majority collapse，而更像是 memory-dense forced export 下的 semantic noise / over-fragmented label buckets。
- 与之前 coverage-preserving `auto` 导出相比，room0 的 forced memory-dense 仍偏弱；后续若以全局 mIoU 为目标，应考虑 scene/object-level export policy，而不是所有场景强制 memory-dense。

## GT / Layer monitor：room1

| monitor | layer2 fix | semantic guard repair |
| --- | ---: | ---: |
| Layer2 decision accuracy | 0.859823 | 0.873997 |
| Layer2 accuracy after object merge | 0.881709 | 0.894061 |
| raw ID-switch events | 1178 | 1148 |
| canonical ID-switch after merge | 486 | 566 |
| GT target fragmentation | 488 | 427 |
| canonical GT fragmentation after merge | 252 | 236 |
| exported GT-monitor object count | 176 | 188 |
| object semantic accuracy | 0.341463 | 0.346667 |

解释：

- Layer2 局部准确率继续提升；
- raw ID switch 下降，fragmentation 下降；
- canonical ID switch 上升，说明 object-merge/root canonicalization 仍有一些边界问题，后续要重点看 canonical root 合并边界；
- object semantic acc 小幅提升，但仍明显受原始 CLIP/GSA label 噪声限制。

## Export 侧变化：room1

| export monitor | layer2 fix | split all labels | adaptive split |
| --- | ---: | ---: | ---: |
| memory nodes | 401 | 416 | 416 |
| track fragmentation | 1262 | 1134 | 1134 |
| memory-dense initial objects | 330 | 514 | 948 |
| final exported objects | 124 | 173 | 173 |
| objects/key mean | 3.297 | 2.115 | see artifact |
| detections/exported object max | 2162 | 639 | see artifact |

解释：

- label-aware export 显著降低了“超级 object”语义坍缩；
- adaptive split 在 CG postprocess 前保留更多可拆分语义材料，但最终 merge 后 object 数量仍保持 173；
- 这正是 room1 precision/mIoU 大幅恢复的主要原因。

## Per-class 关键变化：room1（split all labels 相对 layer2 fix）

- `pillow`: IoU 0.00 → 41.95；precision 0.00 → 72.48；recall 0.00 → 49.89。
- `comforter`: IoU 25.87 → 29.80；precision 25.87 → 29.82。
- `nightstand`: IoU 17.23 → 20.15；precision 17.43 → 20.36。
- 下降项：`indoor-plant` IoU 75.66 → 69.15；`vent` IoU 15.42 → 12.97。

## 当前剩余问题

1. room1 的最终指标已经超过同场景 ConceptGraphs mIoU/mPrecision/mF1；
2. room0 forced memory-dense 仍明显弱于 coverage-preserving 导出策略，说明不能只靠 merge gate 解决所有场景；
3. canonical root ID-switch 仍偏高，object merge / root canonicalization 仍需要更精细的边界控制；
4. 原始 single-frame semantic noise 很高，init semantic accuracy 约 0.414，后续需要 class-aware confidence / entropy filter 或更强视觉语义模型。

## Artifacts

- Best room1 run: `docs/official_results/duograph3d_semantic_guard_adaptive_room1_20260429/`
- room1 GT layer monitor: `docs/official_results/duograph3d_semantic_guard_gt_layer_room1_20260429/`
- room0 adaptive check: `docs/official_results/duograph3d_semantic_guard_adaptive_room0_20260429/`
- Earlier split-all room1 run: `docs/official_results/duograph3d_semantic_guard_room1_20260429/`
- Earlier split-all room0 run: `docs/official_results/duograph3d_semantic_guard_room0_20260429/`
