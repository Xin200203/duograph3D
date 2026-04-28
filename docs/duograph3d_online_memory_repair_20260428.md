# DuoGraph3D online memory 直接导出修复记录（2026-04-28）

## 修复目标

之前如果直接使用 online memory 导出，会把 `MemoryObjectNode.sampled_points` 当作最终语义地图。这个点集只是 Layer2 匹配用的小采样，所以覆盖率极低，导致 mIoU 很差。此次修复目标是：**用 online memory 决定“哪些片段属于同一个 object”，但用 ConceptGraphs/GSA 单帧投影得到的 dense geometry 做最终导出**。

## 代码改动

1. **merge alias**
   - `MemoryObjectNode` 增加 `merge_target_id`。
   - `ObjectGraphMemory.merge_nodes()` 在 source 被合并时记录目标 object，并把 source 的 co-visibility relation 重定向到 target。

2. **Layer2 gate 收紧**
   - history candidate 不再只看 affinity；必须同时满足 margin、spatial，并且满足 semantic / point-overlap / same-geometry 之一，才算 strong identity。
   - relation bonus 增加上限，并要求 identity/semantic/point-overlap/same-geometry gate；避免 co-visibility 分数把错误候选顶上来。
   - 默认 association 必须有 strong identity，避免高分但弱身份的错误 merge。

3. **dense online-memory export**
   - 新增 `--export-source memory-dense`。
   - 使用 memory root id 聚合 geometry key，但 dense points/colors/features 来自 `key_data`，不再直接使用 sparse sampled points。
   - 新增 geometry-key assignment count：同一个 key 多次对应到不同 object 时，用事件计数选择主 root，而不是只看 set/最高 detection_count。
   - 对低置信 root 归属（top root share < 0.60）启用 geometry fallback，避免把不确定 key 强行合并进错误 memory object。

## 验证

本地：

```bash
python3 -m py_compile src/duograph3d/*.py examples/run_conceptgraphs_engineered_parity.py
PYTHONPATH=src python3 -m unittest discover -s tests -v
# Ran 98 tests OK
```

远端两场景：

```bash
cd /home/nebula/xxy/DuoGraph3D
/home/nebula/miniconda3/envs/duograph-baselines-cu118/bin/python examples/run_conceptgraphs_engineered_parity.py \
  --root /home/nebula/xxy/duograph3d_artifacts/duograph3d_memory_dense_hybrid_room0_room1_20260428 \
  --pred-exp-name duograph3d_memory_dense_hybrid_room0_room1_20260428 \
  --min-object-detections 2 \
  --export-source memory-dense \
  --scenes room0 room1
```

本地结果目录：`docs/official_results/duograph3d_memory_dense_hybrid_room0_room1_20260428/`

## 指标结果

| run | room0 mIoU | room1 mIoU | all mIoU | all F-mIoU | 说明 |
| --- | ---: | ---: | ---: | ---: | --- |
| sparse online memory（旧问题） | 4.146 | 13.825 | 6.258 | - | 直接导出 sampled_points，覆盖率崩掉 |
| memory-dense + assignment count | 20.939 | 20.054 | 16.289 | 38.010 | dense geometry 后大幅回升，但 ambiguous key 仍会被强行归 root |
| **memory-dense hybrid（本次最终）** | **23.761** | **21.607** | **18.186** | **42.048** | online memory root + 低置信 geometry fallback |
| coverage auto geometry fallback（上一次最好） | 25.248 | 22.990 | 19.012 | 42.415 | 主要依赖 geometry-key 覆盖，不是直接 memory root |
| ConceptGraphs baseline | 21.335 | 24.477 | 24.531 | 36.238 | 官方 baseline |

## 关键监控读数

- room0：1498 个 geometry keys；857 个单一 memory assignment；641 个 ambiguous，其中 427 个低 root-share fallback；最终 724 个初始导出 object，CG-style postprocess 后 285 个 object；mIoU 23.761，超过 CG room0 +2.426。
- room1：1073 个 geometry keys；589 个单一 memory assignment；484 个 ambiguous，其中 286 个低 root-share fallback；最终 475 个初始导出 object，postprocess 后 186 个 object；mIoU 21.607，仍低于 CG -2.870。
- two-scene all：mIoU 18.186，仍低于 CG all -6.345；但 F-mIoU 42.048，高于 CG +5.811。

## 结论

修复证明了之前 online memory 直接导出差的主因不是 evaluator 或投影本身，而是 **memory sampled points 太稀疏 + ambiguous key 归属没有计数/置信控制**。改成 “memory root 管对象身份，dense geometry 管最终覆盖” 后，room0 从 4.146 回升到 23.761，room1 从 13.825 回升到 21.607。

剩余主要问题在 room1：precision 明显低于 ConceptGraphs，说明 semantic/identity 仍有错误归属或 label 混淆。下一步应优先做 per-class confusion 与 ambiguous fallback threshold/semantic vote 的小网格，而不是继续改稀疏 sampled-point 出口。
