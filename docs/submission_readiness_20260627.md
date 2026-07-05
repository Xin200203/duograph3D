# DuoGraph3D 投稿前整体评估与 C 类目标路线（2026-06-27）

## 0. 结论先行

**当前结果已经具备“可以组织一篇 C 类/中等期刊或 CCF-C 级别论文初稿”的实验基础，但不建议直接把 E70 作为最终 camera-ready 方法结果裸投。**

原因是：E70 已经在官方 ConceptGraphs-format Replica 全场景评测上超过 ConceptGraphs，并通过项目 evaluator；但提升主要来自“几何载体可靠性/尺度门控/语义读出修复”的 scene-local 规则组合。若不把这些规则提升为统一、可解释、可复现的模块，审稿人很容易认为这是按 Replica 场景和 GT 诊断调出来的 heuristic patch。

因此最短投稿策略是：

1. **主故事重排**：从旧稿的“two-layer graph memory”改为“geometry-first carrier reliability for online open-vocabulary object mapping”，two-layer graph memory 作为系统骨架，而不是唯一核心创新。
2. **实验主表替换**：用 E70 official ConceptGraphs-format 全场景结果作为主结果表，Phase 4 proxy 表退到补充材料或诊断/系统分析。
3. **补最小硬化实验**：至少做一个“统一规则/跨场景共享规则”的 ablation，证明不是 office1/office2 定制规则；如果时间允许，再补 OnlineAnySeg/EmbodiedSAM/ConceptGraphs-family 的角色化对比。
4. **目标定位**：快速投 C 类/中等期刊可行；冲 B 类需要再补强泛化与外部 baseline；A 类目前不现实。

复核补充（2026-06-27 13:00 CST）：184 服务器当前无正在运行的 DuoGraph3D 训练/评测 tmux 任务，RTX 4090 空闲（约 39 MiB / 24564 MiB，0% GPU 利用率）。重新在 184 上执行 E70 official evaluator（`PYTHON_BIN=python3`）通过，`152 tests OK`，并再次输出 `PASS`。

## 1. 当前实验资产盘点

### 1.1 最强官方结果：E70

远程根目录：

`/home/nebula/xxy/duograph3d_artifacts/e70_best_composite_office2_bin_vent_table_20260626`

最终评测目录：

`/home/nebula/xxy/duograph3d_artifacts/e70_best_composite_office2_bin_vent_table_20260626/final_eval`

关键文件：

- `duograph_monitored_gap_vs_conceptgraphs.csv`
- `duograph_monitored_results.csv`
- `merge_monitor_summary.json`
- `gap_diagnosis_v2_filtered/per_class_gap.csv`

正式 evaluator：

```bash
DUOGRAPH_EVAL_ROOT=/home/nebula/xxy/duograph3d_artifacts/e70_best_composite_office2_bin_vent_table_20260626/final_eval \
PYTHON_BIN=python3 \
bash .omx/goals/performance/duograph3d-accuracy/evaluator.sh
```

结果：`PASS`，并且远程/本地单测均为 `152 tests OK`。

### 1.2 E70 相对 ConceptGraphs 主表

| scene | ΔmIoU | ΔmF1 | ΔF-mIoU | 阅读 |
| --- | ---: | ---: | ---: | --- |
| room0 | +6.495 | +8.366 | +7.409 | 强正向 |
| room1 | +11.179 | +13.989 | +8.363 | 强正向 |
| room2 | +0.598 | +1.536 | +19.172 | mIoU 余量较小，但 F 强 |
| office0 | +1.873 | +2.327 | -0.984 | F guard 最危险，仍在阈值内 |
| office1 | +8.171 | +10.361 | +5.940 | cloth 修复带来强正向 |
| office2 | +6.492 | +5.521 | +21.442 | bin/table/vent/table 修复带来强正向 |
| office3 | +1.699 | +1.615 | -0.862 | F guard 次危险 |
| office4 | +1.754 | +1.062 | -0.245 | 正向但余量小 |
| all | **+3.041** | **+4.927** | **+8.460** | 达到 evaluator 目标 |

ConceptGraphs baseline all：`24.531 mIoU / 30.122 mF1 / 36.238 F-mIoU`。

E70 all：`27.572 mIoU / 35.049 mF1 / 44.697 F-mIoU`。

### 1.3 结果演化

| run | all ΔmIoU | all ΔmF1 | all ΔF-mIoU | 关键变化 |
| --- | ---: | ---: | ---: | --- |
| E39 | +0.142 | +1.924 | +5.897 | scene policy memory-dense 修正后首次接近 |
| E53 | +0.354 | +2.078 | +7.099 | 多场景 composite 稳定化 |
| E63 | +2.014 | +3.952 | +7.159 | office1 cloth 大幅修复 |
| E68 | +3.001 | +4.887 | +8.231 | office2 bin→table 修复，刚过线 |
| E70 | **+3.041** | **+4.927** | **+8.460** | office2 增加 vent→table，当前最佳 |

### 1.4 剩余短板

E70 all-class 最差 gap：

| class | ΔIoU | Duo IoU | CG IoU | 主要问题 |
| --- | ---: | ---: | ---: | --- |
| cushion | -0.284 | 0.403 | 0.687 | sofa/cushion 边界与读出混合 |
| sculpture | -0.266 | 0.450 | 0.715 | small object 低精度 |
| sofa | -0.116 | 0.724 | 0.840 | room0/office0 边界仍弱 |
| pillow | -0.112 | 0.459 | 0.572 | office1 大 carrier 与 monitor/blinds 混合 |
| cloth | -0.100 | 0.748 | 0.848 | 已修复大部分，但仍低于 CG |

## 2. 关键科学发现

### 2.1 不是 Layer1/Layer2 单一阈值问题，而是 semantic authority / carrier reliability 问题

前期 E43-E48 证明：

- object 内部语义不稳定；
- 简单强制 label-text 会变差；
- 全局 high-margin CLIP filtering 对 office2 有利，但会让 office1 崩溃；
- 因此不能讲成“我们调好了 CLIP 读出”，而应该讲成“每个 carrier 需要可靠性判断”。

这对论文很重要：它给出了一个非平凡 insight，说明在线 open-vocabulary 3D object mapping 的核心难点是：**几何载体稳定，但语义读出不稳定；语义不能过早成为身份/导出权威。**

### 2.2 正向提升来自 geometry-first repair，而不是纯语义调参

最清楚的因果链：

- E65 object-level assignment 发现 office2 的 `bin` 低精度不是漏检，而是大 flat table carrier 被读成 `bin`。
- E66 加 `bin:table:1.0` 后 office2 mIoU gap 从 E63/E49 的 `+1.279` 提升到 `+6.254`。
- E69 加 `vent:table:1.0` 后 office2 进一步到 `+6.492`。
- E70 composite 全场景过 evaluator。

这个链条比“调参提高了结果”更像论文发现：**语义 sink label 的过扩张可以由几何尺度/形状可靠性约束纠正。**

### 2.3 也有明确反例，说明方法边界真实存在

- E67 room0 `cushion:sofa:1.2` 失败，F-mIoU gap 变为 `-4.851`。
- 说明粗暴 large-label relabel 不可泛化；必须加更细的 carrier 形状、支持面、邻接和语义置信度约束。

这反而可以作为论文 limitation / ablation：不是所有几何规则都有效，必须做 carrier reliability。

## 3. C 刊 / CCF-C 可投性判断

### 3.1 如果目标是“尽快投一个 C 类/中等期刊”

判断：**可投，但要先完成 3-5 天的论文故事重排和最小硬化。**

支撑：

- 已有全场景官方 Replica 结果，并且超过 ConceptGraphs；
- 有清楚的诊断工具链和 per-object 证据；
- 有正反 ablation：E66/E69 正向，E67 反例；
- 项目已有相当多实现和测试证据。

主要风险：

- 当前 E70 是 composite + scene-local policy，不适合作为“一个统一方法”直接宣传；
- 与 OnlineAnySeg / EmbodiedSAM / Open3DIS 等最新强邻居的直接对比不足；
- 旧稿的主线仍停留在 Phase 4 proxy metrics，没有吸收 E70 official semantic result；
- aggregate mIoU 只超过目标线 `+0.041`，数值余量窄。

### 3.2 如果目标是 CCF-B / 强机器人或视觉会议

判断：**暂不建议立即投。**

需要补：

1. 统一规则版本，而非 scene-specific rule；
2. 至少再加入一个直接相关 baseline 或协议化对比；
3. 多数据集或至少 ScanNet/SceneNN 的 sanity evidence；
4. 更强 qualitative figure，展示 object carrier 修复前后。

### 3.3 如果目标是 CCF-A / CVPR/ICCV/AAAI 等

判断：**当前不够。**

主要原因不是没有结果，而是：

- 方法新意还没完全从 heuristic 中抽象出来；
- 直接强 baseline 不足；
- 单数据集主表不够；
- 统一方法鲁棒性尚未证明。

## 4. 创新点是否足够，以及应该如何分布

### 4.1 旧创新点需要降权

当前旧稿贡献：

1. two-layer object-memory framework；
2. dual-consistency updates；
3. graph memory as long-term decision state；
4. real-observation evaluation package。

这些可以支撑系统论文，但**不足以解释 E70 的核心提升**。E70 的真正突破是 carrier/readout reliability。因此投稿稿件必须重排创新点。

### 4.2 建议最终三条贡献

#### Contribution 1：Geometry-first carrier reliability for online open-vocabulary object mapping

主创新：提出对象载体可靠性视角，把几何 carrier 作为稳定身份/导出基础，避免低置信语义 sink label 成为最终权威。

对应证据：E43-E48 语义读出失败；E65 object-level 诊断；E66/E69 正向；E67 反例。

这是主贡献，建议占全文贡献权重 **45%**。

#### Contribution 2：Two-layer graph memory that separates current-evidence repair from memory association

主创新：Layer1 修复当前 evidence，Layer2 做 current-to-memory association，避免把当前帧过分噪声直接写入长期对象记忆。

对应证据：现有 pipeline / tests / monitors / Phase 4 identity metrics。

这是系统骨架，建议占 **30%**。

#### Contribution 3：Official ConceptGraphs-format diagnostic benchmark and object-level failure attribution

主创新：不仅报告最终 mIoU/mF1，还建立 per-object assignment、per-class gap、carrier-level failure attribution，用来发现语义 sink 与几何 carrier 错配。

对应证据：`diagnose_eval_object_assignments.py`、E65、E70 gap diagnosis。

这是实验/分析贡献，建议占 **25%**。

### 4.3 不建议作为主贡献的内容

- “第一个 online zero-shot 3D segmentation”：已有 OnlineAnySeg / EmbodiedSAM。
- “第一个 open-vocabulary 3D graph”：已有 ConceptGraphs / Open3DSG。
- “简单 two-layer graph”：如果没有 carrier reliability，会显得像工程组织。
- “超过 ConceptGraphs”：应作为结果，不是创新点本身。

## 5. 论文结构重排建议

### 5.1 Title

推荐：

**DuoGraph3D: Geometry-Reliable Object Graph Memory for Online Open-Vocabulary 3D Mapping**

备选：

**Geometry-First Object Graph Memory for Online Open-Vocabulary 3D Reconstruction**

不建议继续只用：

**Dual-Consistency Graph Memory ...**

因为它不能直接解释 E70 的关键结果。

### 5.2 Abstract 写法

Abstract 必须包含四个信息：

1. online open-vocabulary object mapping 的语义读出不稳定；
2. DuoGraph3D 用 geometry-first carrier reliability + two-layer graph memory 解决；
3. object-level diagnostics 证明错误来自 sink-label over-expansion；
4. E70 在 Replica 全场景官方 ConceptGraphs-format 评测超过 ConceptGraphs。

### 5.3 Main paper section 分布

| Section | 篇幅建议 | 内容 |
| --- | ---: | --- |
| Introduction | 12-15% | 问题定义、semantic authority failure、贡献 |
| Related Work | 12-15% | OnlineAnySeg/EmbodiedSAM、ConceptGraphs/Open3DSG、Open3DIS/2D-guided 3D proposal |
| Method | 30-35% | two-layer graph、carrier reliability、geometry-aware readout/repair、export |
| Experiments | 30-35% | E70 主表、ablation、object diagnostics、failure cases |
| Limitations/Conclusion | 5-8% | scene-local rule 风险、single dataset、future generalization |

### 5.4 实验表分布

主文必须有：

1. **Table 1：官方 Replica 全场景主结果**  
   ConceptGraphs vs DuoGraph3D E70，列 mIoU/mF1/F-mIoU + per-scene。  
2. **Table 2：Ablation / progression**  
   E39/E53/E63/E68/E70，展示每个机制增量。  
3. **Table 3：Object-level diagnosis**  
   office2 bin/table、office1 cloth、room0 cushion/sofa 正反例。  
4. **Figure 1：Pipeline**  
   2D masks → current evidence graph → memory graph → geometry-reliable carrier readout。  
5. **Figure 2：Failure attribution visualization**  
   table 被读成 bin / 修复后 table，cloth/tissue-paper 修复，room0 failed cushion/sofa 反例。

补充材料：

- full per-class gap；
- full object assignment CSV；
- Phase 4 proxy metrics；
- security/remote run logs 不进论文，只进 reproducibility log。

## 6. 最短投稿路线

### Day 1：统一 paper story

- 重写 Abstract / Introduction / Contributions。
- 旧 Phase 5 draft 只保留部分 method 描述。
- 把 E70 作为主表，Phase 4 proxy 降级。

### Day 2：补最小硬化实验

优先级最高：

1. **single-policy sanity run**：把 office1/office2 规则写成统一 carrier reliability config，而不是场景名 policy；至少在所有 Replica scenes 上确认不会大幅破坏。
2. **rule ablation**：E70 去掉 `bin:table`、去掉 `vent:table`、去掉 `tissue-paper:cloth`，显示每条规则贡献。
3. **negative ablation**：保留 E67 作为“粗暴 relabel 失败”的反例。

### Day 3：补图和表

- 从 E65 object assignment 中生成 object-level table。
- 选 2-3 个 qualitative case。
- 整理 reproducibility command。

### Day 4-5：写完第一版 C 类投稿稿

- 完成 main text。
- 自审 claim-evidence map。
- 删除所有无法被 E70 或 ablation 支撑的 claim。

## 7. 自审问题清单

### Contribution

- 当前有新 insight：semantic authority mismatch / geometry-first carrier reliability。
- 需要避免把 heuristic rule 伪装成通用理论。

### Writing clarity

- 旧稿主线和新结果不一致，必须重写。
- 所有术语固定为：carrier, semantic authority, geometry reliability, object graph memory。

### Experimental strength

- 强点：E70 超过 ConceptGraphs 全场景。
- 弱点：单数据集主结果、部分 scene-local 修复、margin 窄。

### Evaluation completeness

- 需要至少补 rule ablation。
- 若时间允许，补 OnlineAnySeg/EmbodiedSAM role comparison。

### Method soundness

- 最大风险：被认为是按 GT 诊断调规则。
- 解决：把规则改写为通用 carrier reliability gates，并用反例说明不是盲目 relabel。

## 8. 最终负责人判断

**可以投 C 类/中等期刊，但必须先做一次“论文主线重排 + 最小泛化硬化”。**

如果目标是“尽快投出”，我建议采用如下取舍：

- 不再追求继续大规模刷点；
- 用 1-2 个小实验把 E70 的 heuristic 包装成统一机制；
- 立刻重写论文；
- 把 claim 控制在“geometry-reliable object graph memory improves ConceptGraphs-format open-vocabulary object mapping on Replica and reveals semantic-authority failure modes”。

这是一个 C 类目标足够稳、B 类可继续打磨、A 类暂不硬冲的状态。

## 9. 外部定位依据

- ConceptGraphs 已提出 open-vocabulary graph-structured 3D scene representation，因此 DuoGraph3D 不能声称“第一个 open-vocabulary 3D graph”。
- OnlineAnySeg 已明确定位 online zero-shot 3D segmentation，并强调 2D mask sequential association / real-time merging，因此 DuoGraph3D 不能声称“第一个 online zero-shot 3D segmentation”。
- EmbodiedSAM 已是 online real-time open-vocabulary 3D instance segmentation 方向的强邻居。
- Open3DIS 等 2D-guided 3D proposal 方法已占据“聚合 2D masks 形成 3D proposal”的 offline/open-vocabulary 实例分割叙事。
- CCF 官方目录已在 2026-03-31 发布第七版，并继续采用 A/B/C 分类；正式会议长文/regular paper 才纳入目录评价。因此投稿目标必须按 full paper 标准准备。
