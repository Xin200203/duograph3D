# DuoGraph3D Output Alignment Protocol — OnlineAnySeg + ConceptGraphs

日期：2026-04-23  
状态：code-backed alignment export protocol + dense-geometry bridge

---

## 1. 目标

本阶段先不复现外部 baseline，而是先完成 DuoGraph3D 输出到两个 story-aligned 外部评测面的**格式对齐**：

1. **OnlineAnySeg-style online 3D instance output**
2. **ConceptGraphs-style object-map / semantic-evaluation output**

这一步的目标是让后续可以逐步把 DuoGraph3D 的真实输出送入这些外部 evaluator，而不是继续只保留内部 summary / event metrics。

---

## 2. 已实现的代码入口

### Module
- `src/duograph3d/alignment_exports.py`

### CLI
- `examples/export_alignment_outputs.py`

### Tests
- `tests/test_alignment_exports.py`

---

## 3. OnlineAnySeg 对齐面

### 外部 evaluator 期望
来自本地 OnlineAnySeg repo：
- repo: `/Users/xin/Research/project/3D重建/repos/conceptgraph_family/OnlineAnySeg`
- commit: `152466e318f8220bcc6838c03e340cce2f2153b8`

其 evaluator 期待：

```text
<result_dir>/<scene>/final.ply
<result_dir>/<scene>/ckpt_final.npz
```

其中 `ckpt_final.npz` 至少包含：
- `pred_masks`: shape `(num_points, num_instances)`
- `pred_classes`: shape `(num_instances,)`
- `pred_score`: shape `(num_instances,)`

指标面：
- `all_ap`
- `all_ap_50%`
- `all_ap_25%`

### DuoGraph3D 当前导出
当前实现可以从 `bounded_slice_*.json` 导出：

```bash
PYTHONPATH=src python3 examples/export_alignment_outputs.py \
  --report <bounded_slice_report.json> \
  --output <alignment_output_root>
```

如果已经有真实点云与 object-to-point assignment，可进一步传入 dense geometry sidecar：

```bash
PYTHONPATH=src python3 examples/export_alignment_outputs.py \
  --report <bounded_slice_report.json> \
  --geometry <dense_geometry.json> \
  --output <alignment_output_root>
```

输出：

```text
<alignment_output_root>/onlineanyseg/<scene>/final.ply
<alignment_output_root>/onlineanyseg/<scene>/ckpt_final.npz
<alignment_output_root>/onlineanyseg/<scene>/duograph3d_onlineanyseg_alignment_manifest.json
```

### 当前状态
- 未传入 dense geometry 时：`format_aligned_proxy_geometry`
- 传入真实点云/掩码但缺少正式评测元数据时：`format_aligned_dense_geometry`
- 同时满足 dense assignment、GT/reconstruction 坐标声明、显式类别 id 时：`format_aligned_official_ready`

原因：当前 DuoGraph3D report 已有 object identity / memory assignment，但还没有 dense point/mask assignment。因此目前导出的 mask 是 evaluator-format bring-up placeholder，不可用于正式分数声明。

---

## 4. ConceptGraphs 对齐面

### 外部 evaluator 期望
来自本地 ConceptGraphs repo：
- repo: `/Users/xin/Research/project/3D重建/repos/conceptgraph_family/concept-graphs`
- commit: `93277a02bd89171f8121e84203121cf7af9ebb5d`

其 Replica semantic evaluation 读取：

```text
<replica_root>/<scene>/pcd_saves/full_pcd_<pred_exp_name>*.pkl.gz
```

核心 payload：

```python
{
  "objects": [...],
  "bg_objects": None or [...]
}
```

每个 object 需要类似 ConceptGraphs `MapObjectList.to_serializable()` 的字段：
- `clip_ft`
- `text_ft`
- `pcd_np`
- `pcd_color_np`
- `bbox_np`

其 README 中的 Replica semantic-eval 指标包括：
- `mrecall` / mAcc
- `fmiou` / F-mIoU

### DuoGraph3D 当前导出
当前实现输出：

```text
<alignment_output_root>/conceptgraphs/<scene>/pcd_saves/full_pcd_duograph3d_alignment.pkl.gz
<alignment_output_root>/conceptgraphs/<scene>/pcd_saves/duograph3d_alignment_semantic_proxy.json
<alignment_output_root>/conceptgraphs/<scene>/pcd_saves/duograph3d_conceptgraphs_alignment_manifest.json
```

### 当前状态
- 未传入 dense geometry 时：`format_aligned_proxy_geometry`
- 传入真实 object point cloud 但缺少 CLIP/object feature 或 GT 对齐声明时：`format_aligned_dense_geometry`
- 同时满足 dense assignment、GT/reconstruction 坐标声明、object CLIP feature 时：`format_aligned_official_ready`

原因：ConceptGraphs semantic evaluation 需要 Replica semantic GT、SLAM point clouds、以及 CLIP-compatible object features。当前导出已对齐 object-map serialization surface，但 geometry/features 仍是 placeholder。

---

## 5. Dense geometry sidecar schema

输出对齐层现在支持一个 dependency-free JSON sidecar，作为真实 3D 点云/掩码进入 OnlineAnySeg 与 ConceptGraphs evaluator surface 的桥。

最小结构：

```json
{
  "source": "where-this-geometry-came-from",
  "coordinate_frame": "gt_reconstruction",
  "gt_aligned": true,
  "points": [[0.0, 0.0, 0.0]],
  "colors": [[255, 0, 0]],
  "objects": [
    {
      "object_id": "obj-1",
      "track_hint": "track-a",
      "point_indices": [0],
      "class_id": 5,
      "class_name": "chair",
      "score": 0.91,
      "clip_ft": [1.0, 0.0],
      "text_ft": [1.0, 0.0]
    }
  ]
}
```

字段说明：
- `points`: 全局 point cloud，OnlineAnySeg `pred_masks` 的第一维与该数组一一对应。
- `colors`: 可选；如果存在并与 `points` 等长，会写入 `final.ply` 和 ConceptGraphs `pcd_color_np`。
- `objects[].point_indices`: 当前 DuoGraph3D memory object 对应的点索引。
- `class_id` / `class_name`: OnlineAnySeg-style AP evaluator 的类别面；缺失时仍可生成格式，但不能声明正式类别评测 ready。
- `clip_ft` / `text_ft`: ConceptGraphs semantic evaluation 的 object feature 面；缺失时会用占位 feature 保持格式，但不能声明正式语义评测 ready。
- `gt_aligned`: 只有当点云坐标已与 evaluator GT/reconstruction 对齐时才应为 `true`。

也可以用 `point_cloud_path` / `point_cloud_ply` 指向 ASCII PLY 代替内联 `points`；该桥接层有意不引入 Open3D / numpy，因此 binary PLY 需要先预转换。

---

## 6. 当前仍未完成的正式评测缺口

### 必须补齐
1. 从真实 OnlineAnySeg / ConceptGraphs / 自有 3D mapping 输出自动生成 dense geometry sidecar
2. object-level semantic/category label 或 open-vocabulary descriptor 到目标 evaluator 类别空间的映射
3. confidence calibration
4. 在真实 Replica / ScanNet scene 上核实 geometry export 与 GT / recon point cloud 的坐标对齐

### 完成后才能声明
- OnlineAnySeg AP-style 分数
- ConceptGraphs mRecall / F-mIoU-style 分数

---

## 7. 重要边界

当前导出层完成的是：

> **格式和管线对齐**

不是：

> **正式 benchmark 结果**

因此所有当前 manifest 都显式写入：
- `official_evaluation_ready = false`
- `status = format_aligned_proxy_geometry`

后续只有当 dense point/mask assignment 接上后，才允许把状态提升为：
- `official_evaluation_ready = true`

---

## 8. 本地格式 fixture

为了验证导出层本身，当前仓库还包含一个非正式评测 fixture：

```text
docs/alignment_exports/format_fixture/
```

该 fixture 只用于检查 OnlineAnySeg / ConceptGraphs 输出格式是否能被生成，不能作为实验结果或性能证据使用。

另有 dense bridge fixture：

```text
docs/alignment_exports/dense_fixture/
```

它用于验证 `--geometry` 可以把真实点索引、类别 id、颜色、CLIP/text feature 写入两个外部 evaluator surface。它同样不是实验结果，也不能作为性能证据使用。
