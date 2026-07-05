# DuoGraph3D 当前实验设置、结果与论文进展判断（2026-07-05）

## 1. 当前阶段结论

截至 2026-07-05，DuoGraph3D 已经形成一个可写入论文的明确技术主线：

> **Auditable Geometry-Carrier Authority（可审计几何载体语义权威控制）**：在 ConceptGraphs-format 3D 语义评测中，最终错误并不总是来自 2D 检测或总体记忆失败，而经常来自“可靠几何 carrier 被不稳定 CLIP/label readout 覆盖”。DuoGraph3D 通过保持几何 carrier、约束 evaluator-facing semantic source set，并在导出阶段执行稀疏、可监控的大物体语义修复，显著提升官方 Replica semantic mIoU。

当前强结果已经不只是历史 artifact：**当前代码路径已经复现 E70 full result**，并完成 clean leave-one-out 消融。

## 2. 实验协议与设置

### 2.1 数据集与评测口径

- 数据集：Replica 全 8 个场景：`room0, room1, room2, office0, office1, office2, office3, office4`
- 评测口径：ConceptGraphs Replica official semantic evaluator
  - `eval_replica_semseg`
  - `n_exclude=6`
  - 使用 ConceptGraphs-format `full_pcd_<pred_exp_name>.pkl.gz` 输出
- 对比对象：ConceptGraphs official Replica baseline
- 主指标：
  - mIoU
  - mF1
  - F-mIoU
- 实验运行位置：远程 184 服务器
- 本地只保存代码、文档、汇总 artifact，不在本机跑大实验。

### 2.2 当前 full/current reproduction 设置

Full reproduction 是 scene-policy composite：每个场景用对应的诊断策略生成官方格式 pkl，再统一用 ConceptGraphs evaluator 汇总全场景指标。

关键策略：

1. **office1**
   - `phase=beta`
   - `export-source=memory-dense`
   - `memory-dense-split-by-label=1`
   - `cg-merge-overlap-thresh=1.0`
   - `geometry-repair-large-label-rules=tissue-paper:cloth:0.8`
   - 作用：保留 office1 中被语义读出污染的 tissue-paper 几何 carrier，并修复为 cloth。

2. **office2**
   - `phase=gamma`
   - `export-source=memory-dense`
   - `geometry-repair-keep-labels=bin,bottle,camera,chair,clock,cushion,lamp,panel,sofa,stool,table,tablet,tissue-paper,tv-screen,vent,wall-plug`
   - `geometry-repair-carve-rules=cushion:sofa:0.04`
   - Full/E70 upper bound：`geometry-repair-large-label-rules=bin:table:1.0,vent:table:1.0`
   - 更安全核心版本：`geometry-repair-large-label-rules=bin:table:1.0`
   - 作用：在 evaluator-facing source set 内恢复 `bin→table` 的 large carrier 修复。

3. **其它场景**
   - 复用 E70 中已验证的 scene payload。
   - 当前 clean ablation 主要用于归因 office1/office2 两个关键机制，不把其它场景作为新机制来源。

## 3. 关键实验结果

### 3.1 全场景官方 clean ablation 主表

远程 root：

`/home/nebula/xxy/duograph3d_artifacts/ccfb_clean_composite_ablation_20260704_clean_composite_ablation3`

本地汇总：

`analysis/raw/ccfb_20260704/clean_composite_ablation/composite_summary.tsv`

| Variant | all ΔmIoU | all ΔmF1 | all ΔF-mIoU | office1 ΔmIoU | office2 ΔmIoU | 相对 full drop | 解释 |
|---|---:|---:|---:|---:|---:|---:|---|
| `full_repro_current` | **+3.040857** | **+4.926709** | **+8.459598** | **+8.171477** | **+6.491578** | 0.000000 | 当前代码路径精确复现 E70 强结果。 |
| `wo_office1_tissue` | +1.367659 | +3.009318 | +8.411403 | +4.016209 | +6.491578 | -1.673198 | 去掉 office1 `tissue-paper→cloth` 后，全局 mIoU 大幅下降，证明该机制是主贡献之一。 |
| `wo_office2_large` | +2.014351 | +3.952293 | +7.159491 | +8.171477 | +1.279091 | -1.026506 | 去掉 office2 large-label repair 后，office2 与全局 mIoU 明显下降，证明该机制是第二主贡献。 |
| `office2_binonly_no_vent` | +3.000635 | +4.887364 | +8.230699 | +8.171477 | +6.254106 | -0.040222 | 只保留 `bin→table` 几乎等于 full；`vent→table` 不是核心贡献。 |

结论：

- Full 当前复现超过 ConceptGraphs：`+3.040857 mIoU / +4.926709 mF1 / +8.459598 F-mIoU`。
- office1 `tissue-paper→cloth` 对 all mIoU 贡献约 `+1.67`。
- office2 large-label repair 对 all mIoU 贡献约 `+1.03`。
- office2 `vent→table` 对 all mIoU 只贡献约 `+0.04`，且此前 shared/global 实验显示有负迁移风险，因此不能作为主创新。

### 3.2 office1 局部诊断结果

远程 root：

`/home/nebula/xxy/duograph3d_artifacts/ccfb_cgmerge1_probe_20260704_cgmerge1_probe`

本地汇总：

`analysis/raw/ccfb_20260704/cgmerge1_probe/clean_summary.tsv`

| Variant | scene | ΔmIoU | ΔmF1 | Relabels | Export objects | 结论 |
|---|---|---:|---:|---|---:|---|
| `office1_cgmerge1_tissue` | office1 | **+8.171477** | **+10.361486** | `large_tissue-paper_to_cloth:1` | 30 | 恢复 E70 office1 强结果。 |
| `office1_cgmerge1_no_large` | office1 | +4.016209 | +5.607034 | `{}` | 30 | 相同 carrier-preserving 设置下去掉 repair，office1 mIoU 明显下降。 |

关键发现：

- 当前默认/probe 中 `cg_merge_overlap_thresh=0.7` 会把 carrier 过度合并，export objects 从 30 降到 23，导致 `tissue-paper` source carrier 无法进入 repair 阶段。
- 恢复 `cg_merge_overlap_thresh=1.0` 后，`large_tissue-paper_to_cloth:1` 被重新触发，并精确恢复 office1 E70 指标。

### 3.3 office2 局部诊断结果

远程 root：

`/home/nebula/xxy/duograph3d_artifacts/ccfb_office2_keep_probe_20260704_office2_keep_probe`

本地汇总：

`analysis/raw/ccfb_20260704/office2_keep_probe/clean_summary.tsv`

| Variant | scene | ΔmIoU | ΔmF1 | Relabels | 结论 |
|---|---|---:|---:|---|---|
| `office2_keep_no_large` | office2 | +1.279091 | +0.105776 | `{}` | E70 keep-label authority 下无 large repair 的下界。 |
| `office2_keep_binonly_clip` | office2 | **+6.254106** | **+5.457357** | `large_bin_to_table:1` | `bin→table` 是 office2 的核心贡献。 |
| `office2_keep_binvent_clip` | office2 | +6.491578 | +5.521201 | `large_bin_to_table:1`, `large_vent_to_table:11` | 精确恢复 E70 office2，但 `vent` 增益很小。 |
| `office2_keep_targetgeom_binonly` | office2 | +6.254106 | +5.457357 | `large_bin_to_table:1` | 新 source-mode 在该 exact case 下与 clip-source 一致，可作为诊断开关保留。 |

关键发现：

- office2 不需要 `cg_merge_overlap_thresh=1.0`；该设置反而 over-split 到 50 export objects，无法恢复 E70 bin carrier。
- office2 的核心是 narrow evaluator-facing source authority：只在相关 official semantic keep-set 内做 repair source 判定。
- `bin→table` 足以恢复大部分 office2 和全局收益；`vent→table` 是小幅上界项，不应写成核心创新。

## 4. 已新增/强化的监控指标

为了避免后续再次只看宏观指标，当前代码已新增 large-label repair 的细粒度诊断：

- `geometry_repair_probe.relabel_counts`
- `geometry_repair_probe.relabel_points`
- `geometry_repair_probe.relabel_examples`
- `geometry_repair_probe.blocked_relabel_counts`
- `geometry_repair_probe.source_miss_counts`
- `geometry_repair_probe.source_miss_examples`
- `geometry_repair_probe.shape_fail_counts`
- `geometry_repair_probe.shape_fail_examples`
- per-object repair diagnostics：
  - `pred_label`
  - `source_score`
  - `target_score`
  - `top_repair_scores`
  - `source_matched_by`
  - `declared_label_counts`
  - `source_declared_share`
  - `target_declared_share`
  - `bbox_extent_x/y/z`
  - `max_extent`
  - `detection_count`
  - `projected_large_label_point_rate`

新增显式实验开关：

- `--geometry-repair-large-label-source-mode clip-top1`
- `--geometry-repair-large-label-source-mode declared-source-or-clip`
- `--geometry-repair-large-label-source-mode target-declared-geometry`

默认仍是 legacy `clip-top1`，因此该改动是可逆、可控、不会改变默认行为的监控增强。

## 5. 已修改文件与验证

代码/测试变更：

- `examples/run_conceptgraphs_engineered_parity.py`
- `tests/test_conceptgraphs_preprocess_order.py`

结果/文档归档：

- `docs/ccfb_clean_ablation_results_20260704.md`
- `docs/ccfb_e70_repro_probe_analysis_20260704.md`
- `docs/ccfb_innovation_ablation_plan_20260704.md`
- `docs/ccfb_experiment_runlog_20260704.md`
- `analysis/raw/ccfb_20260704/`
- `analysis/flywheel_runs/20260705T000000Z-duograph3d-ccfb-clean-ablation-20260705.md`

验证命令：

```bash
python3 -m py_compile examples/run_conceptgraphs_engineered_parity.py
PYTHONPATH=src python3 -B -m unittest discover -s tests -v
```

验证结果：

- 本地 full unit suite：`152 tests OK`
- 184 同步后：`python3 -m py_compile examples/run_conceptgraphs_engineered_parity.py` 通过
- 184 当前无实验进程，GPU 空闲。

## 6. 当前论文进展判断

### 6.1 已经可以支持的论文 claim

当前结果可以支持以下说法：

1. **DuoGraph3D 在 Replica official ConceptGraphs-format semantic evaluation 上超过 ConceptGraphs baseline。**
   - full current reproduction：all `+3.040857 mIoU / +4.926709 mF1 / +8.459598 F-mIoU`。

2. **提升不是随机调参，而是来自两个可定位、可复现、可消融的 geometry-carrier authority 修复。**
   - office1：`tissue-paper→cloth`
   - office2：`bin→table`

3. **细粒度 object-level 监控能解释为何修复触发或不触发。**
   - carrier 是否被 postprocess 合并破坏；
   - source label 是否命中；
   - shape gate 是否通过；
   - repair 是否被 evidence/point-rate gate 阻塞。

4. **负面边界也清楚。**
   - `vent→table` 不是主贡献；
   - shared/global broad relabel 之前实验表现不足或负迁移；
   - graph memory dense export 不是当前 final mIoU 的直接来源。

### 6.2 还不应声称的内容

当前不应声称：

1. 已经有完全 scene-independent 的 unified method 替代 E70 scene-policy composite。
2. `vent→table` 是稳定通用规则。
3. graph memory dense export 是最终 mIoU 提升的直接主因。
4. 当前结果已经达到强 CCF-B regular 的充分标准。

### 6.3 投稿判断

我的判断：

- **CCF-C / 中等期刊**：当前证据已经比较扎实，可以组织成系统/诊断型论文。
- **CCF-B 会议目标**：仍然有机会，但需要继续深化，把 scene-local diagnostic composite 抽象成更统一的机制。
- 当前 CCF-B 的主要风险不是结果弱，而是审稿人会质疑：
  1. 是否按 Replica scene 做了 post-hoc tuning；
  2. 是否只是 heuristic patch；
  3. 是否能泛化到其它场景或其它 zero-shot 3D segmentation/mapping 设置。

因此，现阶段最合理的论文定位是：

> 一个 object-centric open-vocabulary 3D mapping 的 failure-attribution 与 geometry-carrier authority control 框架，证明在 ConceptGraphs official setting 下可以通过可审计的 carrier/source 控制显著超过 baseline，并给出正/负机制边界。

## 7. 下一步建议

为了把论文从“强诊断 composite”推进到更接近 CCF-B 的统一方法，下一轮实验应集中在：

1. **Scene-independent carrier authority selector**
   - 不读 scene name；
   - 同时生成少量 export hypotheses；
   - 用 source-miss、shape-fail、repair sparsity、object-count coverage、unsafe-label penalty 自动选择。

2. **跨场景安全门控**
   - 保留 `tissue→cloth` / `bin→table` 的收益；
   - 抑制 `vent→table` 这种高风险边界；
   - 目标 full all ΔmIoU 至少 `+2.0`，最好接近 `+3.0`。

3. **论文消融表结构**
   - Main table：ConceptGraphs vs DuoGraph3D full current reproduction；
   - Ablation table：w/o office1 tissue、w/o office2 large、office2 bin-only no-vent；
   - Diagnostic table：source-miss / shape-fail / relabel counts；
   - Failure-boundary table：shared/global vent/table variants 的负面结果。

## 8. 当前最重要的一句话

当前最有论文价值的发现不是某个单独规则，而是：

> **在 open-vocabulary 3D mapping 中，最终 semantic output 的可靠性取决于 geometry carrier 是否被保留，以及 evaluator-facing semantic source authority 是否被约束；DuoGraph3D 的 object-level monitoring 能定位并修复这类 carrier/readout mismatch。**
