# DuoGraph3D 当前实现结构与实验细节记录（2026-04-29）

本文档记录当前分支上 DuoGraph3D 与 ConceptGraphs 对比实验的**实现结构、各层职责、关键判断条件、导出/评测细节、已有实验结果与当前问题边界**。

- 当前分支：`conceptgraphs-engineering-optimizations-20260426`
- 主要代码范围：
  - 核心管线：`src/duograph3d/`
  - ConceptGraphs 对齐实验 runner：`examples/run_conceptgraphs_engineered_parity.py`
  - GT 分层监督 monitor：`examples/run_conceptgraphs_gt_layer_monitor.py`
  - 回归测试：`tests/test_pipeline.py`
- 当前阶段定位：已经实现 ConceptGraphs-style 工程技巧、Layer2 identity gate 收紧、object semantic conflict guard、memory-dense adaptive label split；但 online memory 本身、final export、单场景评测口径仍需要严格区分。

---

## 1. 总体链路

当前实验链路可以理解成：

```text
Replica RGB-D + ConceptGraphs GSA detections_none
  ↓
单帧 mask 过滤 / mask subtraction / 3D 投影
  ↓
Observation / ObjectObservationPayload
  ↓
EvidenceBuilder：把当前观测 + 历史候选 history_candidates 组成 EvidenceItem
  ↓
Layer1：CurrentEvidenceGraphLayer，同帧碎片修复 / hypothesis 生成
  ↓
Layer2：CurrentToMemoryAssociationLayer，把当前 hypothesis 关联到 online memory object
  ↓
ObjectGraphMemory：维护 object node、关系边、object merge / filter / denoise
  ↓
导出选择：geometry / memory / memory-dense
  ↓
ConceptGraphs-style denoise / filter / merge_objects
  ↓
ConceptGraphs official eval_replica_semseg 指标
```

当前最重要的结构特点是：

1. **online identity 使用 class-agnostic geometry key**，语义主要保留在 feature / label histogram 中。
2. **Layer1 是单帧碎片修复层**，会把同帧里相似/同 key/同历史候选的 observation 合成 hypothesis。
3. **Layer2 是 online memory 关联层**，负责 associate / reentry / birth / residual absorption。
4. **final official mIoU 不直接等于 online memory 质量**，因为 memory-dense export 会用 dense geometry + label bucket 修复一部分 semantic collapse。

---

## 2. 核心模块结构

### 2.1 `src/duograph3d/contracts.py`

核心数据结构与默认配置定义在这里。

主要数据结构：

| 数据结构 | 作用 |
| --- | --- |
| `Observation` | runner 中每个单帧 mask 投影后的观测。 |
| `ObjectObservationPayload` | 一个 observation 携带的 object 证据：label、点云采样、bbox、centroid、clip/text feature、mask area。 |
| `EvidenceItem` | EvidenceBuilder 输出给 Layer1 的单帧证据，额外带历史候选。 |
| `HistoryCandidate` | 当前 observation/hypothesis 与历史 memory node 的候选关系。 |
| `CurrentObjectHypothesis` | Layer1 合并后输出的当前帧 object hypothesis。 |
| `MemoryObjectNode` | online memory 中维护的 object 节点。 |
| `AssociationDecision` | Layer2 对一个 hypothesis 的决策：associate / reentry / birth / absorb。 |
| `PipelineConfig` | 所有 Layer1 / Layer2 / memory gate 的默认参数。 |

当前关键默认 gate：

| 参数 | 当前默认 | 含义 |
| --- | ---: | --- |
| `association_threshold` | 1.7 | Layer2 关联阈值。 |
| `layer1_merge_threshold` | 0.9 | Layer1 同帧碎片连边阈值。 |
| `layer1_history_shared_boost` | 0.45 | 两个 observation 指向同一历史 object 时给 Layer1 的加分上限。 |
| `layer2_history_identity_threshold` | 0.7 | history candidate 作为 identity 证据的 affinity 阈值。 |
| `history_point_overlap_requires_spatial_evidence` | True | history point-overlap 不能自己充当空间证据。 |
| `layer2_point_overlap_identity_requires_spatial_evidence` | True | Layer2 direct point-overlap 不能自己充当 strong identity。 |
| `layer2_absorption_threshold` | 1.75 | residual absorption 分数阈值。 |
| `layer2_absorption_min_point_overlap` | 0.4 | residual absorption 需要较强 point-overlap，除非 same-geometry。 |
| `layer2_absorption_min_semantic_score` | 0.55 | residual absorption 语义下限。 |
| `object_merge_threshold` | 0.88 | memory object merge 阈值。 |
| `object_merge_semantic_conflict_guard` | True | object merge 是否启用语义冲突保护。 |
| `object_merge_max_merged_label_entropy` | 1.15 | merge 后 label 过混时触发保护。 |
| `object_merge_min_merged_top_label_share` | 0.55 | merge 后 top label 占比太低时触发保护。 |

---

### 2.2 `src/duograph3d/pipeline.py`

`DuoGraph3DPipeline` 是核心执行器。

每帧执行顺序：

1. `EvidenceBuilder.build()`：从 `FrameInput` 生成 `EvidenceItem`。
2. `CurrentEvidenceGraphLayer.repair()`：Layer1 生成 `CurrentObjectHypothesis`。
3. `CurrentToMemoryAssociationLayer.update()`：Layer2 更新 `ObjectGraphMemory`。
4. 每帧记录事件：`comparison_slice_start`、`current_hypothesis_emit`、`association_commit`、`birth_commit` 等。
5. 序列结束后执行一次 `memory.consolidate_objects()`。

对应代码：`src/duograph3d/pipeline.py:13-101`。

---

### 2.3 `src/duograph3d/evidence.py`

EvidenceBuilder 的职责是把 runner 的 observation 转换成 Layer1 可用的 evidence。

当前关键点：

- 每个当前 observation 都会调用：

```python
item.history_candidates = memory.history_candidates_for(item)
```

- 因此 Layer1 已经能够看到历史 memory 信息。
- 如果启用 `TemporalVariant.DEVA_STYLE`，还会插入 propagated evidence；但当前 ConceptGraphs parity runner 使用 `TemporalVariant.NAIVE_FRAMEWISE`，所以主要是当前帧 observation + history candidates，不使用 DEVA-style propagation。

对应代码：`src/duograph3d/evidence.py:25-39`。

---

## 3. ConceptGraphs 对齐实验 runner

主 runner：`examples/run_conceptgraphs_engineered_parity.py`。

### 3.1 数据输入

当前使用 ConceptGraphs 官方 GSA 检测：

```text
/home/nebula/xxy/dataset/Replica/<scene>/gsa_detections_none
```

评测 baseline CSV：

```text
/home/nebula/xxy/duograph3d_artifacts/conceptgraphs_replica_official_20260423/replica_ex6_results.csv
```

官方评测调用 ConceptGraphs 的：

```python
conceptgraph.scripts.eval_replica_semseg.eval_replica
```

对应代码：`examples/run_conceptgraphs_engineered_parity.py:32-42`。

---

### 3.2 当前工程参数

| 参数 | 当前值 | 说明 |
| --- | ---: | --- |
| `VOXEL_SIZE` | 0.20 | class-agnostic geometry key 的量化尺寸。 |
| `MIN_MASK_PIXELS` | 300 | 小 mask 过滤。 |
| `MASK_CONF_THRESHOLD` | 0.95 | 低置信 mask 过滤。 |
| `MAX_BBOX_AREA_RATIO` | 0.50 | 过大 bbox 过滤。 |
| `MIN_VALID_DEPTH_POINTS` | 16 | 投影后有效点数下限。 |
| `MAX_POINTS_PER_OBS` | 160 | 单 observation 点采样上限。 |
| `MAX_POINTS_PER_OBJECT` | 4096 | export object 点数上限。 |
| `MIN_OBJECT_DETECTIONS` | 2 | object export 的检测次数下限。 |
| `LOW_CLIP_MARGIN` | 0.03 | 语义低置信监控阈值。 |
| `CLASS_AGNOSTIC_TOKEN` | `item` | 模仿 CG `gsa_variant=none` 的 class-agnostic identity。 |
| `CG_DOWNSAMPLE_VOXEL_SIZE` | 0.025 | ConceptGraphs-style postprocess。 |
| `CG_DBSCAN_EPS` | 0.1 | DBSCAN denoise。 |
| `CG_DBSCAN_MIN_POINTS` | 10 | DBSCAN min points。 |
| `CG_MERGE_OVERLAP_THRESH` | 0.7 | CG-style object merge overlap 阈值。 |
| `CG_MERGE_VISUAL_SIM_THRESH` | 0.8 | CG-style visual merge 阈值。 |
| `CG_MERGE_TEXT_SIM_THRESH` | 0.8 | CG-style text merge 阈值。 |

对应代码：`examples/run_conceptgraphs_engineered_parity.py:39-84`。

---

### 3.3 单帧 mask 处理顺序

当前处理顺序是 ConceptGraphs-style：

1. 从 `gsa_detections_none` 读取 masks / image_feats / xyxy / confidence。
2. 过滤太小 mask：`area < MIN_MASK_PIXELS`。
3. 过滤低 confidence：`confidence < 0.95`。
4. 过滤大 bbox：bbox area 超过图像 50%。
5. 对保留下来的 mask 执行 `mask_subtract_contained()`。
6. 投影到 3D。
7. 过滤有效 depth 点数不足的 mask。
8. 生成 `Observation` 和 `ObjectObservationPayload`。

对应代码：`examples/run_conceptgraphs_engineered_parity.py:320-399`。

重要说明：

- `mask_subtract_contained()` 是 CG 中用于“从大物体 mask 里挖掉被包含小物体”的技巧，例如 sofa 上的 pillow。
- 当前实现已经在预过滤之后执行该操作。

---

### 3.4 identity key 与语义 feature

当前 `quant_key()` 是 class-agnostic：

```python
def quant_key(scene: str, label: str, centroid: np.ndarray) -> str:
    q = np.floor(centroid / VOXEL_SIZE).astype(int)
    del label
    return f"{scene}:gsa:{CLASS_AGNOSTIC_TOKEN}:{q[0]}:{q[1]}:{q[2]}"
```

含义：

- online identity 不直接使用 top-1 semantic label；
- 所有类别共享 `item` token；
- 目的是避免 CLIP 单帧 label flip 直接切断 track；
- 风险是：不同物体如果落在同一个 0.2m cell，Layer1 / Layer2 更容易混合。

对应代码：`examples/run_conceptgraphs_engineered_parity.py:204-210`。

语义部分：

- 每个 detection 的 top-1 label 来自 GSA image feature 与 Replica class text feature 的相似度。
- `ObjectObservationPayload.label` 存 top-1 label。
- online matching 的 `text_feature` 当前为空数组：`online_matching_text_feature = np.asarray((), dtype=np.float32)`。
- key-level export 的 `text_sum` 使用 class-agnostic text anchor，用于模仿 CG `none/item` 设定。
- `key_data.label_buckets` 额外保留每个 geometry key 下不同 label 的 dense geometry 和 feature，用于后续 memory-dense label split。

对应代码：

- top-1 / margin：`examples/run_conceptgraphs_engineered_parity.py:342-365`
- payload：`examples/run_conceptgraphs_engineered_parity.py:390-398`
- key_data / label_buckets：`examples/run_conceptgraphs_engineered_parity.py:400-448`

---

## 4. Layer1：同帧碎片修复层

模块：`src/duograph3d/layer1.py`。

Layer1 输入：一帧的 `EvidenceItem` 列表。  
Layer1 输出：若干 `CurrentObjectHypothesis`。

### 4.1 Layer1 连边打分

两个 EvidenceItem 之间的 score 来源：

| 条件 | 加分 | 说明 |
| --- | ---: | --- |
| `repair_group_id` 相同 | +0.75 | 当前 runner 中等于 geometry key。 |
| `continuity_key` 相同 | +0.70 | 当前 runner 中也等于 geometry key。 |
| `appearance_key` 相同 | +0.35 | 当前为 top-1 label。 |
| `descriptor` 相同 | +0.20 | 当前为 `scene:item`，class-agnostic。 |
| geometry profile consistent | 动态 | support_size / depth_scale / geometry_support 接近。 |
| `geometry_key` 相同 | +0.45 | 同一个 0.2m cell。 |
| shared history object | 最高约 +0.45 | 两个碎片都指向同一历史 object。 |

阈值：`layer1_merge_threshold = 0.9`。

对应代码：`src/duograph3d/layer1.py:61-98`。

### 4.2 历史信息如何进入 Layer1

历史候选来自 `memory.history_candidates_for(item)`。  
Layer1 只使用满足以下条件的 history candidate：

- affinity >= `history_candidate_affinity_threshold`，默认 0.7；
- margin >= `history_candidate_margin_threshold`，默认 0.15；
- spatial_score >= `layer1_history_min_spatial_score`，默认 0.45；
- semantic_score >= `layer1_history_min_semantic_score`，默认 0.55；
- visual_score / size_score 满足下限，默认 0。

如果两个 evidence 都指向同一个可用历史 object，则 Layer1 加 `layer1_history_shared_boost * shared_strength`。

对应代码：`src/duograph3d/layer1.py:30-59`。

### 4.3 Layer1 当前边界

Layer1 当前能解决 SAM 单帧碎片化问题，但存在两个边界：

1. **class-agnostic geometry key 会鼓励同 cell 内不同语义的碎片合并**。
2. `_merge_payloads()` 合并 payload 时只保留 majority label：

```python
label_counts = Counter(payload.label for payload in payloads if payload.label)
label = label_counts.most_common(1)[0][0] if label_counts else ""
```

这意味着 minority class 可能在 online memory 路径里丢失。后续 memory-dense export 的 label bucket 能救回一部分 final map，但 online memory node 的 `class_counts` 仍可能被污染。

对应代码：`src/duograph3d/layer1.py:191-198`。

---

## 5. Layer2：当前 hypothesis 到 online memory 的匹配层

模块：`src/duograph3d/layer2.py`。

Layer2 输入：Layer1 输出的 `CurrentObjectHypothesis`。  
Layer2 输出：对每个 hypothesis 执行 associate / reentry / birth / residual absorption，并更新 `ObjectGraphMemory`。

### 5.1 候选召回

候选来自：

```python
memory.candidate_nodes(
    hypothesis.geometry_key,
    candidate_budget,
    history_object_ids=history_object_ids,
    hypothesis=hypothesis,
)
```

candidate retrieval 会综合：

- history object ids；
- exact geometry key；
- recent active / occluded / dormant nodes；
- spatial score；
- point overlap score；
- visual score；
- semantic score；
- recency score。

最终排序优先级大致是：

```text
history id > exact geometry > point overlap > spatial > visual > semantic > recency > active status
```

对应代码：`src/duograph3d/memory.py:59-152`。

### 5.2 Layer2 association score

Layer2 score 由以下部分组成：

| 分量 | 说明 |
| --- | --- |
| geometry key score | same geometry key 给 +0.8，并视为 strong identity。 |
| descriptor score | descriptor 相同加权，默认 0.55。 |
| confidence score | 当前 hypothesis confidence，最高 +0.2。 |
| visual score | CLIP visual similarity × `layer2_visual_similarity_weight`，默认 0.35。 |
| temporal score | propagated / continuity / appearance。 |
| geometry profile score | support_size / depth_scale / geometry_support 一致性。 |
| history candidate score | history identity gate 通过后最高 +0.65。 |
| direct point overlap score | point-overlap 通过 gate 后按权重加分。 |
| relation bonus | 与当前帧已匹配 object 的 relation edge 加分。 |

最终 associate 条件：

```text
best_score >= association_threshold
且
best_has_identity == True
```

如果不满足，则尝试 residual absorption；仍不满足则 birth。

对应代码：

- score：`src/duograph3d/layer2.py:115-234`
- candidate loop：`src/duograph3d/layer2.py:435-573`
- associate / birth：`src/duograph3d/layer2.py:574-760`

### 5.3 point-overlap identity gate

当前已修复：point-overlap 不能默认单独自证 strong identity。

当前条件：

- point_overlap >= score threshold；
- spatial evidence 通过，或 same geometry；
- semantic 或 visual 通过，或 same geometry。

如果 `layer2_point_overlap_identity_requires_spatial_evidence=True`，则 point-overlap 不能自己替代 spatial evidence。

对应代码：`src/duograph3d/layer2.py:246-299`。

### 5.4 residual absorption

residual absorption 用来处理同帧内已经 birth/associate 的 object 对剩余 hypothesis 的吸收。

当前已经收紧：

- 需要 semantic_score >= 0.55；
- 需要 history identity / independent spatial / same geometry 至少一个成立；
- point_overlap >= 0.4，除非 same geometry；
- adjusted_score >= 1.75。

对应代码：`src/duograph3d/layer2.py:352-433`。

当前实验中 room1 修复后 residual absorption 已基本不是主要错误源。

---

## 6. ObjectGraphMemory：online object 维护

模块：`src/duograph3d/memory.py`。

### 6.1 MemoryObjectNode 维护内容

每个 memory node 保存：

- object id；
- descriptor / recent descriptor；
- geometry key；
- active / occluded / dormant / retired status；
- continuity / appearance recent key；
- detection count / confidence sum / mask area sum；
- sampled points / colors；
- bbox / centroid；
- clip feature / text feature；
- class_counts；
- merge_target_id。

对应结构：`src/duograph3d/contracts.py:134-170`。

### 6.2 fuse_hypothesis

Layer2 associate / birth 后都会调用：

```python
memory.fuse_hypothesis(node, hypothesis, step_id=step_id)
```

当前行为：

- 累加 detection_count；
- 累加 confidence / mask area；
- 写入 `class_counts[label] += current_count`；
- 融合 clip_feature / text_feature；
- 合并 bbox / centroid；
- 合并并 capped sampled points。

对应代码：`src/duograph3d/memory.py:703-745`。

重要边界：如果 Layer1 hypothesis 的 label 已经是 majority label，则 memory node 的 class_counts 也会继承这个 majority label，minority label 可能在线上 memory 路径丢失。

### 6.3 object merge

object merge 使用 `object_affinity()`：

```text
score = 0.50 * spatial + 0.25 * visual + 0.20 * semantic + 0.05 * size
        + object_merge_point_overlap_weight * point_overlap
```

此外：

- same geometry key 会让 spatial 至少为 1.0；
- same continuity key 会让 spatial 至少为 0.9；
- semantic conflict guard 会阻止明显不同 label distribution 的 object merge。

对应代码：

- semantic conflict：`src/duograph3d/memory.py:783-844`
- object affinity：`src/duograph3d/memory.py:846-902`
- merge execution：`src/duograph3d/memory.py:904-940`
- merge loop：`src/duograph3d/memory.py:940-966`

---

## 7. Export 与 official eval

当前 runner 支持三种导出策略：

| 策略 | 对应 source | 说明 |
| --- | --- | --- |
| `geometry` | `duograph3d_geometry_key_coverage` | 直接按 geometry key dense geometry 导出，覆盖率强，但 online memory 作用弱。 |
| `memory` | `duograph3d_online_object_memory` | 直接导出 online memory node 的 sampled points。 |
| `memory-dense` | `duograph3d_online_memory_dense_geometry` | 用 online memory root 作为 identity，但导出 dense key geometry。 |
| `auto` | 自动选择 | memory 覆盖率不足则 fallback geometry。 |

对应代码：`src/duograph3d/export_policy.py` 与 `examples/run_conceptgraphs_engineered_parity.py:1244-1335`。

### 7.1 geometry export

`build_initial_map_objects()`：

- 按 `key_data` 中每个 geometry key 聚合点云；
- label 取 key 内 majority label；
- CLIP/text feature 用 key 内平均；
- 然后跑 ConceptGraphs-style process_pcd / denoise / filter / merge。

对应代码：`examples/run_conceptgraphs_engineered_parity.py:743-817`。

### 7.2 memory export

`build_memory_map_objects()`：

- 直接导出 online memory node；
- label 来自 `ObjectGraphMemory.dominant_semantic_label(node)`；
- 点云来自 memory node sampled_points；
- 适合分析 online memory object，但可能覆盖不足。

对应代码：`examples/run_conceptgraphs_engineered_parity.py:820-893`。

### 7.3 memory-dense export

`build_memory_dense_map_objects()`：

- 对每个 geometry key，查看它在 Layer2 事件中被分配到哪些 memory object；
- follow merge alias 得到 root id；
- 用 root id 聚合 dense key geometry；
- 如果 root label distribution 混杂，则按 label bucket split 成 `root_id:label:<label>`；
- 最终仍经过 ConceptGraphs-style denoise / filter / merge_objects。

关键阈值：

| 参数 | 当前值 |
| --- | ---: |
| `MEMORY_DENSE_SPLIT_BY_LABEL` | True |
| `MEMORY_DENSE_SPLIT_MIN_OBSERVATIONS` | 1 |
| `MEMORY_DENSE_SPLIT_MIN_ROOT_LABEL_ENTROPY` | 0.5 |
| `MEMORY_DENSE_SPLIT_MAX_ROOT_TOP_SHARE` | 0.9 |
| `MEMORY_DENSE_MIN_ROOT_SHARE` | 0.60 |
| `MEMORY_DENSE_GEOMETRY_FALLBACK` | True |

对应代码：

- label bucket export item：`examples/run_conceptgraphs_engineered_parity.py:693-717`
- split root 判断：`examples/run_conceptgraphs_engineered_parity.py:720-728`
- dense root aggregation：`examples/run_conceptgraphs_engineered_parity.py:953-1160`

重要解释：

> memory-dense export 的 final object 不等于纯 online memory object。它用 online memory root 控制 identity，但用 dense key geometry 和 label bucket 修复 official semantic map。

---

## 8. ConceptGraphs-style 工程技巧已吸收项

当前实现已经吸收了以下 ConceptGraphs 工程技巧：

1. **使用 GSA detections_none**：class-agnostic 检测输入。
2. **mask confidence filter**：默认 `MASK_CONF_THRESHOLD=0.95`。
3. **大 bbox filter**：默认 `MAX_BBOX_AREA_RATIO=0.50`。
4. **mask_subtract_contained**：从大 mask 中挖掉被包含小 mask。
5. **class-agnostic identity token**：online key 使用 `item`。
6. **dense object geometry postprocess**：`process_pcd()` + DBSCAN denoise。
7. **filter_objects / merge_objects**：使用 ConceptGraphs 的 postprocess。
8. **CLIP/text feature accumulation**：key-level 用平均 feature。
9. **coverage-preserving export policy**：memory 不够密时允许 fallback geometry。
10. **memory-dense hybrid**：online memory root + dense geometry。
11. **adaptive label split**：修复 mixed root 中 minority class 被 majority label 吞掉的问题。

---

## 9. 当前监控结构

### 9.1 preparation monitor

由 `prepare_scene()` 输出，记录：

- raw detection count；
- kept observation count；
- key count；
- mask pixel 分布；
- confidence 分布；
- valid depth ratio；
- CLIP margin；
- observations per frame；
- observations per key；
- label entropy per key；
- low confidence / large bbox / low CLIP margin / zero depth 等计数。

对应代码：`examples/run_conceptgraphs_engineered_parity.py:459-510`。

### 9.2 association diagnostics

由 Layer2 事件统计：

- candidate count；
- best score；
- score margin；
- best candidate 是否 strong identity；
- birth reason；
- best candidate components；
- relation bonus。

对应代码：`examples/run_conceptgraphs_engineered_parity.py:514-563`。

### 9.3 export monitor

记录：

- export selection；
- memory export probe；
- memory-dense export probe；
- geometry export probe；
- initial object count；
- post denoise / filter / merge count；
- skipped keys；
- fragmented export key rate；
- export label entropy；
- detections per exported object；
- points per exported object。

对应代码：`examples/run_conceptgraphs_engineered_parity.py:1309-1355`。

### 9.4 GT layer monitor

脚本：`examples/run_conceptgraphs_gt_layer_monitor.py`。

它会使用 GT 对照监督：

- init semantic accuracy；
- init duplicate rate；
- Layer1 semantic accuracy / duplicate rate / false merge rate / pair precision；
- Layer2 decision accuracy；
- Layer2 duplicate birth rate；
- Layer2 ID switch rate；
- GT target fragmentation；
- residual absorption accuracy；
- object monitor semantic accuracy。

注意：当前 GT object monitor 的 object export 是 minimal online memory node export，不是 official runner 的 adaptive memory-dense final export。因此它能说明 online memory purity，但不能直接等价为 official mIoU。

对应代码：

- object_probability_monitor：`examples/run_conceptgraphs_gt_layer_monitor.py:1046-1125`
- write_duograph_payload：`examples/run_conceptgraphs_gt_layer_monitor.py:1128-1225`

---

## 10. 当前关键实验结果

### 10.1 room1：adaptive semantic guard

结果目录：

```text
docs/official_results/duograph3d_semantic_guard_adaptive_room1_20260429/
```

per-scene 正确对比：

| 指标 | DuoGraph3D | ConceptGraphs room1 | 差值 |
| --- | ---: | ---: | ---: |
| mIoU | 27.920 | 24.477 | +3.443 |
| mRecall | 45.804 | 38.327 | +7.477 |
| mPrecision | 46.092 | 32.629 | +13.462 |
| mF1 | 33.522 | 29.236 | +4.285 |
| F-mIoU | 36.163 | 42.957 | -6.793 |

解释：

- mIoU / precision / F1 已经超过 room1 CG；
- 但 F-mIoU 仍低，说明大面积类别或频率加权指标仍有差距；
- 不应使用 single-scene `all_gap` 去判断 room1 F-mIoU 是否追平。

### 10.2 room0：adaptive semantic guard

结果目录：

```text
docs/official_results/duograph3d_semantic_guard_adaptive_room0_20260429/
```

per-scene 正确对比：

| 指标 | DuoGraph3D | ConceptGraphs room0 | 差值 |
| --- | ---: | ---: | ---: |
| mIoU | 19.346 | 21.335 | -1.989 |
| mRecall | 34.980 | 38.335 | -3.355 |
| mPrecision | 31.418 | 29.433 | +1.986 |
| mF1 | 25.292 | 25.273 | +0.020 |
| F-mIoU | 40.877 | 50.035 | -9.157 |

解释：

- room0 不是 precision 崩坏；
- 主要是 recall / F-mIoU / 大类别覆盖问题；
- forced memory-dense 在 room0 明显不如之前 coverage-preserving auto。

### 10.3 room1 GT layer monitor

结果目录：

```text
docs/official_results/duograph3d_semantic_guard_gt_layer_room1_20260429/
```

相对 layer2 fix：

| 指标 | layer2 fix | semantic guard |
| --- | ---: | ---: |
| Layer2 decision accuracy | 0.859823 | 0.873997 |
| Layer2 accuracy after object merge | 0.881709 | 0.894061 |
| raw ID switch events | 1178 | 1148 |
| canonical ID switch after merge | 486 | 566 |
| GT target fragmentation | 488 | 427 |
| canonical GT fragmentation after merge | 252 | 236 |
| residual absorption count | 19 | 0 |
| object semantic accuracy | 0.341463 | 0.346667 |

剩余 raw ID switch 主因：

| 原因 | 数量 |
| --- | ---: |
| false_association_candidate_missing_previous | 522 |
| false_association_wrong_object | 472 |
| duplicate_birth_candidate_missing_previous | 120 |
| duplicate_birth_previous_candidate_no_strong_identity | 30 |
| duplicate_birth_previous_candidate_below_threshold | 3 |
| duplicate_birth_other | 1 |

解释：

- point-overlap / residual absorption 问题基本被压住；
- 剩余 Layer2 错误主要是 candidate missing 和 wrong object；
- object merge 虽降低 fragmentation，但 canonical ID switch 可能上升，需要单独监控。

---

## 11. 当前问题边界

### 11.1 已基本关闭的问题

1. **point-overlap 自证 identity**：已经通过 spatial / semantic / visual gate 收紧。
2. **residual absorption 误吸收**：room1 修复后 residual absorption count 为 0。
3. **room1 minority class 被 majority root 吞掉**：adaptive label split 显著恢复 final mIoU / precision。
4. **ConceptGraphs mask subtraction 缺失**：当前 runner 已调用 `mask_subtract_contained()`。

### 11.2 仍未关闭的问题

1. **single-scene `all_gap` 误导**：只跑单场景时，应优先看 per-scene gap row。
2. **online memory object 与 final exported object 不一致**：memory-dense adaptive split 能提升 official mIoU，但不能证明 online memory 已经干净。
3. **Layer1 majority-label collapse**：Layer1 merge payload 仍只保留 majority label。
4. **candidate missing / wrong object**：Layer2 剩余 ID switch 主要集中在候选缺失和错候选。
5. **object merge canonical ID switch**：merge 后 fragmentation 降低，但 canonical switch 可能升高。
6. **room0 forced memory-dense 不稳**：room0 更需要 export policy / coverage 策略，而不是继续只调 Layer2 gate。
7. **语义噪声仍大**：low CLIP-margin 比例高，init semantic accuracy 不高。

---

## 12. 后续实验建议

优先级从高到低：

1. **修正报告口径**：single-scene report 不再突出 `all_gap`；rollup 应显示 per-scene gap。
2. **补 official adaptive export 的 GT object monitor**：把 final exported pkl 与 GT 对齐，而不是只看 online memory minimal pkl。
3. **分离 online memory 指标与 final export 指标**：分别报告 memory-node purity、memory-dense export purity、final postprocess mIoU。
4. **Layer1 保留 label distribution / sub-payload**：不要只把 majority label 写入 hypothesis payload。
5. **Layer2 candidate failure 分桶**：按 candidate missing / wrong object / semantic low / spatial low / geometry key conflict 统计。
6. **room0 做 export policy 对照**：同样 gate 下比较 geometry / memory / memory-dense / auto，确认 room0 差距是否来自 forced memory-dense。
7. **object merge 后 GT switch monitor**：明确哪些 merge 导致 canonical ID switch 增加。

---

## 13. 文件索引

| 文件 | 作用 |
| --- | --- |
| `src/duograph3d/contracts.py` | 数据结构和所有 gate 默认值。 |
| `src/duograph3d/pipeline.py` | 管线调度：Evidence → Layer1 → Layer2 → memory consolidation。 |
| `src/duograph3d/evidence.py` | observation 转 evidence，并注入 history candidates。 |
| `src/duograph3d/layer1.py` | 同帧 current evidence graph 修复。 |
| `src/duograph3d/layer2.py` | 当前 hypothesis 到 memory object 的匹配。 |
| `src/duograph3d/memory.py` | online memory、candidate retrieval、feature fusion、object merge。 |
| `src/duograph3d/export_policy.py` | geometry / memory / memory-dense / auto 导出选择。 |
| `src/duograph3d/metrics.py` | run summary、fragmentation、geometry-key assignment。 |
| `examples/run_conceptgraphs_engineered_parity.py` | 主 official parity runner。 |
| `examples/run_conceptgraphs_gt_layer_monitor.py` | GT 分阶段监督 monitor。 |
| `tests/test_pipeline.py` | Layer1 / Layer2 / memory merge 回归测试。 |
| `docs/duograph3d_semantic_guard_repair_20260429.md` | 上一轮 semantic guard 修复记录。 |

---

## 14. 一句话总结

当前 DuoGraph3D 不是一个单纯“两层匹配 gate”的系统，而是：

> **class-agnostic GSA/SAM observation → Layer1 同帧碎片图修复 → Layer2 online memory 关联 → memory object merge → memory-dense / geometry export → CG-style postprocess → official semantic eval**。

目前 room1 final mIoU 的提升主要来自 **memory-dense adaptive label split 修复 export 语义坍缩**；room0 的主要瓶颈更像 **导出策略和大类别覆盖**；Layer2 剩余问题主要集中在 **candidate missing / wrong object**，而不是 residual absorption 或 point-overlap 自证 identity。
