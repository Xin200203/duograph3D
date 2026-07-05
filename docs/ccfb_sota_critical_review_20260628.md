# DuoGraph3D CCF-B 投稿批判性审查与 2026 SOTA 调研

日期：2026-06-28  
角色：投稿/实验第一负责人，按资深审稿人与领域专家视角审查  
本轮动作：拉取并阅读相关论文 PDF；对照当前 E70/A1/A2/E71 实验包；给出投稿 claim、SOTA 位置和补强路线。

## 0. 一句话结论

当前 DuoGraph3D **有一个可以写进论文的正结果**：在 ConceptGraphs-format Replica official 评测中，E70 相比 ConceptGraphs 达到 `+3.041 mIoU / +4.927 mF1 / +8.460 F-mIoU`。但从 2026 年 open-vocabulary 3D scene understanding 的 SOTA 来看，这还**不是一个足以直接支撑 CCF-B regular 的强方法故事**。

核心问题不是“没有提升”，而是：

1. **实验指标和 SOTA 主流指标错位**：当前主结果是 Replica semantic mIoU/mF1 gap against ConceptGraphs；OV-3DIS SOTA 通常报告 ScanNet200/Replica 的 mAP/AP50/AP25；online mapping 新工作还报告 real-time / incremental / semantic-instance mapping。
2. **创新点和正结果来源错位**：A2 已经证明 graph memory 不是 final mIoU 直接来源；E70 的主增益来自 `tissue-paper→cloth` 和 office2 `bin→table` 两个 diagnosis-guided carrier repair。
3. **统一方法尚未成立**：E71 target-declared evidence gate 只得到 `+0.665 mIoU`，没有恢复 E70；说明现在还不能声称“scene-independent unified carrier repair”。
4. **ConceptGraphs 已不足以作为唯一强 baseline**：2024-2026 年已经出现 Open3DIS、Open-YOLO 3D、Details Matter、OV3D-CG、OVI-MAP、OnlineAnySeg、EmbodiedSAM/ESAM、MV3DIS、OpenTrack3D、SpaCeFormer 等更贴近 OV-3D/online/zero-shot 的方法。

建议的 CCF-B 策略：不要把论文写成“超过 ConceptGraphs 的调参系统”，而要重构为：

> **Geometry-first, auditable online open-vocabulary object mapping**: stable geometry carriers should not be overwritten by noisy semantic readout; graph memory provides observability and export-source gating; object-level diagnostics expose when semantic authority fails.

但要冲 CCF-B，还必须补一条真正跨场景、无 scene id 的 reliability gate，或者补到至少一个更强在线/OV3DIS baseline 上的同协议比较。

---

## 1. 本轮已拉取/阅读的论文与本地归档

PDF 与抽取文本保存在：

- `analysis/literature/ccfb_sota_20260628/pdfs/`
- `analysis/literature/ccfb_sota_20260628/texts/`

已阅读核心文献：

| 方向 | 论文 | 年份/状态 | 本地文件 | 与 DuoGraph3D 的关系 |
| --- | --- | --- | --- | --- |
| graph mapping | ConceptGraphs | arXiv/RSS 系列，2023 | `conceptgraphs_arxiv.pdf` | 当前主 baseline，同类 object graph mapping。 |
| OV-3DIS foundation | OpenMask3D | NeurIPS 2023 | `openmask3d_arxiv.pdf` | per-mask multi-view CLIP aggregation，早期强 baseline。 |
| dense OV semantic | OpenScene | CVPR 2023 | `openscene_cvpr2023.pdf` | dense CLIP feature field，语义上界/related。 |
| 2D-guided OV-3DIS | Open3DIS | CVPR 2024 | `open3dis_cvpr2024.pdf` | 2D mask → geometrically coherent 3D proposals；强相关。 |
| fast OV-3DIS | Open-YOLO 3D | ICLR 2025 Oral | `open_yolo_3d_openreview.pdf` | multi-view detector labels + fast classification；速度强。 |
| online zero-shot | OnlineAnySeg | arXiv 2025 | `onlineanyseg_arxiv.pdf` | online zero-shot direct competitor。 |
| online SAM 3D | EmbodiedSAM / ESAM | ICLR 2025 | `embodiedsam_arxiv.pdf` | online real-time 3D instance segmentation；强 online baseline。 |
| recipe SOTA | Details Matter | ICCV 2025 | `details_matter_iccv2025.pdf` | AlphaCLIP + proposal merge/removal；peer-reviewed OV-3DIS strong baseline。 |
| contextual OV-3DIS | OV3D-CG | ICCV 2025 | `ov3d_cg_iccv2025.pdf` | MLLM + context reasoning；说明 context 已进入主流。 |
| online mapping | OVI-MAP | CVPR 2026 | `ovi_map_cvpr2026.pdf` | 目前最直接威胁：online open-vocabulary instance-semantic mapping。 |
| geometric guidance | GeoGuide | CVPR 2026 | `geoguide_cvpr2026.pdf` | 几何-语义一致性；支持我们“几何重要”的大方向。 |
| zero-shot 3D instance | MV3DIS | CVPR 2026 | `mv3dis_cvpr2026.pdf` | 3D-guided mask matching / depth consistency，与 carrier reliability 强相关。 |
| foundation model | Mosaic3D | arXiv 2025 | `mosaic3d_arxiv.pdf` | 大规模 3D mask-text 数据和基础模型；说明训练型路线在推进。 |
| mesh-free OV-3DIS | OpenTrack3D | arXiv 2025/2026 | `opentrack3d_arxiv.pdf` | tracker + MLLM；最新 preprint，泛化压力很大。 |
| fast proposal-free | SpaCeFormer | arXiv 2026 | `spaceformer_arxiv.pdf` | 极快 proposal-free OV-3DIS preprint，改变效率基线。 |

说明：`ov3d_cg_arxiv.pdf` 是一次错误下载的无关 arXiv PDF，不纳入阅读结论。

---

## 2. 当前 SOTA 地图：不能再用“一个 SOTA”概括

### 2.1 与 DuoGraph3D 最直接的 SOTA：online open-vocabulary instance-semantic mapping

**代表：OVI-MAP, CVPR 2026。**

关键设计：

- 增量构建 class-agnostic 3D instance map；
- 语义推理只在自动选择的少量视图上做 VLM feature extraction；
- 明确 decouple instance reconstruction from semantic inference；
- real-time online mapping。

论文表 3 报告：

| Dataset | Method | Online | semantic mIoU | AP25 | AP50 | APall |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| Replica | OVI-MAP | yes | 26.5 | 34.5 | 21.2 | 8.5 |
| ScanNet | OVI-MAP | yes | 17.5 | 23.4 | 15.7 | 7.2 |
| Replica 30FPS | OVI-MAP | yes | 27.0 | 31.8 | 17.7 | 8.0 |

**对 DuoGraph3D 的冲击：**

OVI-MAP 的核心故事和我们高度重叠：都是 online incremental、instance map、open vocabulary、语义和几何解耦。它的论文叙事比我们当前版本更“统一”：不是局部 relabel，而是从系统设计上 decouple reconstruction / semantic feature。若 DuoGraph3D 不加入 OVI-MAP 讨论甚至对比，CCF-B 审稿人会认为 related work 不完整。

**我们可能的差异化空间：**

- OVI-MAP 强调实时 instance-semantic mapping；
- DuoGraph3D 可以强调 object-level failure attribution、carrier reliability diagnostics、export-source decision audit；
- 但必须用实验表证明这些 diagnostics 不只是分析工具，而能带来可复现的无 scene-id 改进。

### 2.2 Online zero-shot / online SAM-assisted 3D segmentation SOTA

#### EmbodiedSAM / ESAM, ICLR 2025

论文主张在线、实时、fine-grained 3D perception。其核心模块是 geometric-aware query lifting + dual-level query decoder。表 1 报告 ScanNet200 class-agnostic instance segmentation：

| Method | Type | VFM | AP | AP50 | AP25 | Speed |
| --- | --- | --- | ---: | ---: | ---: | --- |
| SAM3D | Online | SAM | 20.2 | 35.7 | 55.5 | 1369+1518 ms/frame |
| ESAM | Online | SAM | 42.2 | 63.7 | 79.6 | 1369+80 ms/frame |
| ESAM-E | Online | FastSAM | 43.4 | 65.4 | 80.9 | 20+80 ms/frame |

**批判点：**ESAM 是训练型/online 3D perception，不是纯 zero-shot semantic mapping；但它是“online 3D segmentation”审稿人会想到的强 baseline。

#### OnlineAnySeg, arXiv 2025

核心：用 voxel hashing 把 2D mask 的 3D overlap 查询从 `O(n^2)` 降到 `O(n)`，做在线 zero-shot 2D mask merging。

表 1 报告：

| Method | Online | Zero-shot | ScanNet200 AP/AP50/AP25 | SceneNN AP/AP50/AP25 | FPS |
| --- | --- | --- | --- | --- | ---: |
| EmbodiedSAM | yes | no | 28.8 / 42.7 / 54.2 | 20.1 / 32.5 / 46.3 | 10 |
| MaskClustering | no | yes | 19.7 / 36.4 / 51.4 | 16.3 / 31.7 / 46.2 | - |
| OnlineAnySeg | yes | yes | 18.6 / 36.1 / 53.5 | 18.1 / 35.3 / 59.5 | 15 |

**对 DuoGraph3D 的冲击：**如果我们声称 online zero-shot segmentation，就必须正面对比 OnlineAnySeg；如果我们只做 Replica final semantic export，就不能写成直接 online segmentation SOTA。

### 2.3 Offline / batch OV-3D instance segmentation SOTA

#### Open3DIS, CVPR 2024

关键设计：aggregates 2D instance masks across frames and maps them to geometrically coherent point cloud regions, then combines these with 3D class-agnostic proposals.

其提出的模式已经非常接近我们想说的 geometry carrier：2D masks 不能直接做最终实体，需要先映射到几何一致的 3D region。

#### Open-YOLO 3D, ICLR 2025 Oral

关键设计：不用重型 SAM/CLIP multi-view aggregation，而用 multi-view 2D object detector labels + MVPDist 解决误分类。论文称：ScanNet200 val mAP `24.7%`，每场景 `22s`，相对 best existing method 最多 `~16x` speedup。

对我们启发：语义不是单帧 top-1，而是 multi-view prompt distribution。DuoGraph3D 的 label evidence 应从 rule relabel 升级为 multi-view label distribution / prompt support。

#### Details Matter, ICCV 2025

这是目前 peer-reviewed OV-3DIS 中非常强的 recipe-style baseline。核心：

- 3D tracking-based proposal aggregation；
- iterative merging/removal 去掉重叠/partial proposal；
- Alpha-CLIP masked object-centric representation；
- standardized maximum similarity score filtering false positives。

表 1 中 Top-K, 2D+3D setting：

| Method | mAP | mAP50 | mAP25 | mAPhead | mAPcommon | mAPtail |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Open3DIS | 23.7 | 29.4 | 32.8 | 27.8 | 21.2 | 21.8 |
| Details Matter | 32.7 | 41.4 | 45.3 | 34.5 | 30.7 | 33.1 |

**对 DuoGraph3D 的冲击：**如果我们只和 ConceptGraphs 比，强审稿人会说没有对比真正的 OV-3DIS recipe SOTA。即使任务不同，也要在 related work 和 optional table 里解释差别。

#### OV3D-CG, ICCV 2025

核心：contextual guidance + MLLM CoT prompt。表 1 ScanNet200 2D+3D：`25.4 AP / 32.9 AP50 / 37.0 AP25`；表 2 Replica 3D-only：`20.0 AP / 25.8 AP50 / 32.0 AP25`。

**对我们启发：**审稿人已经接受“context helps ambiguous object recognition”。我们如果继续只用 label remapping，会显得落后；应把 context/neighborhood/support relation 显式纳入 carrier reliability。

#### OpenTrack3D, arXiv 2025/2026 preprint

核心：mesh-free visual-spatial tracker 构建 cross-view object proposals，DINO features + spatial cues，MLLM 替代 CLIP 处理 compositional/functional queries。表 1：

| Method | Supervised 3D Mask | ScanNet200 AP/AP50/AP25 | Replica AP/AP50/AP25 |
| --- | --- | --- | --- |
| Open3DIS* | no | 18.2 / 26.1 / 31.4 | 18.2 / 25.9 / 31.0 |
| OpenTrack3D | no | 26.0 / 37.7 / 45.4 | 23.9 / 36.4 / 47.6 |

这是 preprint，不能按 peer-reviewed 结论等同 SOTA，但会影响审稿人的预期：**mesh-free、tracker、MLLM、cross-dataset generalization** 已经成为 2026 的新门槛。

#### SpaCeFormer, arXiv 2026 preprint

核心：proposal-free transformer + 大规模 SpaCeFormer-3M 数据，声称 `0.12–0.30s/scene`，ScanNet200 `11.1 mAP`，ScanNet++ `22.9 mAP`，Replica `24.1 mAP`。它不是和我们同一协议，但说明效率/数据规模方向也在快速推进。

### 2.4 Open-vocabulary 3D semantic segmentation SOTA

#### GeoGuide, CVPR 2026

核心：hierarchical geometry-semantic consistency：superpoint uncertainty distillation、instance-level mask reconstruction、inter-instance relation consistency。它直接支持一个大趋势：**2026 年的 open-vocabulary 3D semantic segmentation 已经从纯 2D distillation 转向 geometry-semantic consistency**。

这对 DuoGraph3D 是正向信号：用户提示“几何位置信息非常重要”是对的；但我们需要把 geometry 从经验规则变成可量化模块。

#### Mosaic3D, arXiv 2025

核心：5.6M 3D mask-text pairs + 3D foundation model。表 1 报告 semantic f-mIoU：ScanNet200 `15.7`，ScanNet20 `68.1`，ScanNet++ `18.0`，Matterport3D `13.1`。

这说明：训练型 3D VFM 正在抬高 open-vocabulary 3D semantic baseline。DuoGraph3D 若不走训练路线，必须强调 online、auditable、data-free/low-training、diagnostic 的价值。

---

## 3. 对 DuoGraph3D 当前实验结果的批判性指正

### 3.1 当前正结果是真的，但不是“强 SOTA 结果”

E70 的 `+3.041 mIoU` 相对 ConceptGraphs 是正结果，且 A1 clean leave-one-out 证明了因果来源：

- `tissue-paper→cloth` 贡献约 `+1.800 all mIoU`；
- office2 `bin→table` 贡献约 `+1.153 all mIoU`；
- `vent→table` 基本没有主贡献。

这可以支持一篇论文中的 **case-driven evidence**，但不能直接支持“我们的系统整体超越 SOTA”。原因：

1. 只对 ConceptGraphs 一个老 baseline 成立；
2. 指标是 ConceptGraphs-format semantic mIoU/mF1，不是 OV-3DIS AP；
3. Replica 只有 8 个 synthetic scenes，且强增益集中在 office1/office2；
4. 正结果来自少数 targeted repair，统一 gate 失败。

投稿时应写：

> DuoGraph3D outperforms ConceptGraphs under the same Replica semantic evaluation protocol, and object-level ablation identifies two major carrier-readout failures.

不应写：

> DuoGraph3D achieves SOTA open-vocabulary 3D segmentation.

### 3.2 当前创新点最大问题：claim-evidence 不对齐

旧创新点若写成 two-layer graph memory，会被 A2 自己反驳：

- A2 auto rows final metrics identical，因为 export fallback 到 geometry；
- forced memory-dense 为负：`-2.483 avg ΔmIoU`；
- memory 的主要价值是 diagnostics/state/export-gating，不是 final dense source。

因此，graph memory 不能作为“精度提升主因”。它应被降级为：

- object state container；
- association/fragmentation monitor；
- export-source gate；
- failure attribution substrate。

主创新必须改成 geometry-first carrier reliability / semantic authority control。

### 3.3 当前方法看起来像 scene-local heuristic，这是最大拒稿风险

A1 证明两个 local repair 有效，但 E71 证明统一 rule/gate 未成立。审稿人会问：

1. 这些 rules 是不是看了 GT 后为 Replica 调的？
2. 为什么 office2 `bin→table` 可泛化？
3. 为什么 `vent→table` 在 A1 中被证明没用还留在 E70？
4. 如果换成 ScanNet/SceneNN，table/bin/cloth/tissue 的标签空间不同怎么办？
5. 你的 gate 用了 scene id 吗？用了目标场景的诊断结果吗？

当前最佳应对不是回避，而是正面收窄 claim：

- E70 是 diagnostic composite，证明 failure type 的存在与修复潜力；
- 提交版方法需要 scene-independent reliability score；
- 若来不及做统一方法，则论文定位应从“方法 SOTA”降为“diagnostic framework + bounded repair case study”。

### 3.4 结果解释必须从宏观 mIoU 下沉到 object-level / frame-level

用户要求“每一帧的监测结果、是否正确匹配、记忆维护”等是正确的。2025-2026 相关工作都在强化：

- multi-view consistency；
- instance tracking；
- view coverage；
- depth/projection reliability；
- masked object-centric representation；
- proposal merging/removal。

DuoGraph3D 当前已经有一部分监控，但论文表格还不够 reviewer-facing。必须把以下指标固定下来：

| 层级 | 必报指标 | 用途 |
| --- | --- | --- |
| frame / observation | mask count, projected point count, depth-valid rate, source label entropy, CLIP/semantic margin | 证明前端输入质量和噪声来源。 |
| current carrier | bbox extent, planarity/horizontality, support-surface score, view count, label distribution top-share | 证明 geometry carrier 是否支持 relabel/readout。 |
| association | candidate recall@K, chosen-correct rate, wrong-candidate rate, no-candidate count | 证明 Layer2 memory 是否真的在维护 identity。 |
| memory | birth rate, duplicate rate, fragmentation, weak-id, memory purity, coverage ratio | 证明 memory 不是黑箱。 |
| export | geometry vs memory export source, coverage floor pass/fail, relabel object/point count, blocked relabel count | 防止后处理 trick。 |
| final eval | per-scene mIoU/mF1/F-mIoU + AP/AP50/AP25 if possible | 对齐两类评测体系。 |

### 3.5 目前最强创新方向不是“relabel”，而是“semantic authority control”

成熟方法给出的共识是：

- OpenMask3D / Details Matter：object-centric masked representation 比 point/frame top-1 更稳；
- Open3DIS / MV3DIS：2D masks 必须通过 3D geometry / view consistency 约束；
- OVI-MAP：instance reconstruction 和 semantic inference 应解耦；
- GeoGuide：几何-语义一致性应分层建模；
- OnlineAnySeg：spatial association 是 online merging 的关键；
- OpenTrack3D / OV3D-CG：MLLM/context 已经进入 ambiguous object recognition。

DuoGraph3D 可发表的新意应表述为：

> 在 online object graph 中，语义 readout 不是天然权威；只有当 multi-view semantic evidence 与 stable geometry carrier 一致时，语义才可写入 memory/export。否则系统应保留 geometry carrier，并把异常作为可审计 failure signal 暴露。

这比“把 bin 改成 table”强得多。

---

## 4. 与 SOTA 的直接差距

| 维度 | SOTA 趋势 | DuoGraph3D 当前状态 | 差距 |
| --- | --- | --- | --- |
| 在线性 | OVI-MAP/ESAM/OnlineAnySeg 明确 online real-time/incremental | 有 online memory，但最终报告主要是 final export | 缺 incremental curves/FPS/latency。 |
| 指标 | OV-3DIS 主流 AP/AP50/AP25；mapping 报 mIoU+AP | 主要 mIoU/mF1/F-mIoU against CG | 需补 AP 或解释协议差异。 |
| baseline | 2025-2026 baseline 很多 | 主表主要 ConceptGraphs | CCF-B 不够。 |
| 方法统一性 | SOTA 模块是无 scene id 的 tracking/view/geometry consistency | E70 是 scene-local composite；E71 unified gate 失败 | 最大风险。 |
| 语义表示 | AlphaCLIP/masked CLIP/MLLM/context/prompt distribution | 当前更像 label remap + monitor | 需要 object-centric semantic evidence。 |
| 几何建模 | superpoint, 3D-guided mask matching, support/instance consistency | 有 geometry carrier，但形式化不足 | 可补强为核心。 |
| 数据集 | ScanNet200/Replica/SceneNN/3RScan/ScanNet++ | Replica full scenes 为主 | 需要至少一个 OOD sanity。 |

---

## 5. CCF-B 级别的论文创新点建议

### 5.1 不推荐的贡献写法

不要这样写：

1. “We propose a two-layer graph memory that improves segmentation accuracy.”  
   - A2 不支持，forced memory-dense 是负的。
2. “We achieve SOTA open-vocabulary 3D segmentation.”  
   - 没有对比 2025/2026 OV-3DIS SOTA，也不是同指标。
3. “We propose universal relabel rules.”  
   - E71 失败。
4. “We outperform ConceptGraphs by relabeling large labels.”  
   - 这会显得像 heuristic patch。

### 5.2 推荐的三条贡献

#### Contribution 1：Geometry-first semantic authority control

提出一个原则：geometry carrier 是对象身份和导出的基础，semantic readout 只有在 multi-view/geometry/context evidence 足够时才成为权威。

需要实验支持：

- A1 local leave-one-out；
- 新增 shared gate 或至少 OOD case；
- relabel/block monitor。

#### Contribution 2：Auditable object graph memory

two-layer graph memory 不再宣称直接提高 mIoU，而是提供：

- association diagnostics；
- memory fragmentation/birth/weak-id tracking；
- export-source gating；
- failure attribution。

需要实验支持：

- A2 diagnostic table；
- no memory / Layer1 / Layer2 / full memory 对 object-level metrics 的影响；
- forced geometry vs forced memory-dense 证明 source separation 必要。

#### Contribution 3：Object-level failure attribution benchmark for online OV 3D mapping

把 E65/A1 变成正式贡献：不仅报告 final mIoU，还能定位哪个 carrier、哪个 label sink、多少 object/points 被影响、修复是否局限于目标 failure family。

需要实验支持：

- office1 tissue/cloth；
- office2 bin/table；
- room0 cushion/sofa 失败边界；
- E71 blocked relabel examples。

---

## 6. 立即要补的实验/阅读任务

### P0：把 OVI-MAP 作为 direct competitor 纳入 related work 和可运行评估计划

原因：它是 CVPR 2026 online open-vocabulary instance-semantic mapping，和 DuoGraph3D 最近。至少要做：

1. 读通 OVI-MAP evaluation protocol；
2. 检查是否能在 Replica 同 51-class label set 上跑；
3. 若不能跑，至少在论文里给 protocol comparison：输入、在线性、metric、semantic extraction、runtime。

### P0：补一个无 scene-id 的 carrier reliability gate v2

E71 已经说明 target-declared gate 不够。v2 gate 应借鉴：

- OVI-MAP 的 selected-view semantic feature；
- MV3DIS 的 3D-guided mask matching + depth consistency；
- Details Matter 的 object-centric AlphaCLIP / SMS false-positive filtering；
- GeoGuide 的 hierarchical geometry-semantic consistency；
- OV3D-CG 的 contextual view reasoning。

最小可实现版本：

```text
carrier_reliability_score =
  geometry_support_score(planarity, horizontality, extent, height, support relation)
  × multiview_label_support(target label top-share / entropy / margin)
  × projection_reliability(depth-valid, view coverage)
  × risk_guard(point-mass, object-count, scene-wide relabel budget)
```

禁止使用：scene id、GT class、人工 per-scene whitelist。

### P0：把现有 Replica 主结果转换/补充为 AP-style instance metrics

即使不能完整复现 Open3DIS/OVI-MAP 协议，也要至少内部生成：

- AP25/AP50/APall；
- class-agnostic AP 和 semantic AP 分开；
- per-scene instance precision/recall；
- with/without carrier repair。

否则与 OV-3DIS SOTA 无法横向讨论。

### P1：补 OnlineAnySeg / ESAM bridge

最低要求：

- 把已有 OnlineAnySeg sparse bridge 升级成可引用的 protocol table；
- ESAM 若不能完整同协议跑，至少说明 input/output/metric 不同，并给 subset 对齐计划；
- CCF-B 稿中不要只出现 ConceptGraphs。

### P1：补 OOD sanity

至少一个：

- SceneNN / ScanNet subset；
- Replica leave-one-scene-out；
- no-scene-id shared gate on all Replica scenes；
- failure cases where gate refuses relabel。

---

## 7. Closest parallels / supported vs inferred

### Closest parallels

1. **OVI-MAP**：同样把 instance reconstruction 和 semantic inference 解耦，是 DuoGraph3D 最大同类压力。
2. **Open3DIS / MV3DIS**：都说明 2D masks 必须通过 3D geometry/multi-view consistency 约束，和 geometry carrier reliability 高度一致。
3. **Details Matter / OpenMask3D**：object-centric masked feature 与 false-positive filtering 是我们 semantic authority control 的成熟参照。
4. **OnlineAnySeg / ESAM**：online 3D mask merging/tracking 的效率和指标基线。
5. **GeoGuide**：几何-语义一致性已成为 2026 open-vocabulary 3D semantic segmentation 的主流方向之一。

### What is directly supported by sources

- Open3DIS 聚合 2D instance masks 到几何一致的 3D point cloud regions，并在 ScanNet200/S3DIS/Replica 上比当时 SOTA 有显著提升。
- OVI-MAP decouples instance reconstruction from semantic inference，实时 online，并在 Replica/ScanNet 上超过 open-vocabulary mapping baselines。
- ESAM 是 ICLR 2025 online real-time 3D instance segmentation，ScanNet200/SceneNN/3RScan 等 benchmark 上报告 online SOTA。
- OnlineAnySeg 用 voxel hashing 把 3D overlap 查询从 `O(n^2)` 降到 `O(n)`，并报告 online zero-shot SOTA/高效率。
- Details Matter 在 ICCV 2025 中声称 ScanNet200/S3DIS across AP/AR 的新 SOTA，核心包括 tracking-based proposal aggregation、AlphaCLIP、SMS filtering。
- GeoGuide 明确指出纯 2D open-vocabulary distillation 会继承 2D prediction error，并用 geometry-semantic consistency 处理。

### What is only inferred for the current system

- 文献支持“几何/多视角一致性重要”，但不直接证明 DuoGraph3D 当前 `bin→table`/`tissue→cloth` rules 可泛化。
- 文献支持 object-centric semantic aggregation，但不直接证明当前 DuoGraph3D 的 graph memory 能提升 final mIoU；A2 反而显示当前不能。
- 文献支持 online tracking/mapping 是重要方向，但不直接说明 DuoGraph3D 已达到 online SOTA；我们缺 FPS/incremental/AP 对齐。
- 文献支持 context/MLLM 可以帮助 ambiguous object recognition，但如果引入 MLLM，会改变系统依赖和计算成本，需要单独评估。

---

## 8. 最终审稿人式 verdict

如果现在投稿：

- **CCF-B regular：高风险**。主要拒稿理由会是 heuristic / scene-local / baseline incomplete / metric mismatch。
- **CCF-C 或 workshop/系统型短文：较可行**。若强调 diagnostic framework + bounded ConceptGraphs-format improvement，可以讲通。
- **要冲 CCF-B：必须补强**：
  1. scene-independent carrier reliability gate v2；
  2. AP-style metrics 或至少 OVI-MAP/Open3DIS/OnlineAnySeg protocol bridge；
  3. one OOD sanity；
  4. runtime/incremental/object-level monitoring table；
  5. 论文贡献改成 semantic authority control，而不是 graph memory 直接提升精度。

我的严格判断：**当前项目已经找到了正确科学问题，但还没有把正确科学问题实现成统一、可复现、足够强的 CCF-B 方法。** 下一步不是继续在 `bin/table/vent` 上调参，而是把这些 case 抽象成可测、可解释、无 scene-id 的 reliability model。

---

## 9. Sources

- ConceptGraphs: https://arxiv.org/abs/2309.16650
- OpenMask3D: https://arxiv.org/abs/2306.13631
- OpenScene: https://pengsongyou.github.io/openscene
- Open3DIS: https://openaccess.thecvf.com/content/CVPR2024/html/Nguyen_Open3DIS_Open-Vocabulary_3D_Instance_Segmentation_with_2D_Mask_Guidance_CVPR_2024_paper.html
- Open-YOLO 3D: https://openreview.net/forum?id=CRmiX0v16e
- EmbodiedSAM / ESAM: https://proceedings.iclr.cc/paper_files/paper/2025/hash/5e68f9149d33a6c8ad59ed60bf90606f-Abstract-Conference.html
- OnlineAnySeg: https://arxiv.org/abs/2503.01309
- Details Matter: https://openaccess.thecvf.com/content/ICCV2025/html/Jung_Details_Matter_for_Indoor_Open-vocabulary_3D_Instance_Segmentation_ICCV_2025_paper.html
- OV3D-CG: https://openaccess.thecvf.com/content/ICCV2025/html/Zhou_OV3D-CG_Open-vocabulary_3D_Instance_Segmentation_with_Contextual_Guidance_ICCV_2025_paper.html
- OVI-MAP: https://openaccess.thecvf.com/content/CVPR2026/html/Deng_OVI-MAP_Open-Vocabulary_Instance-Semantic_Mapping_CVPR_2026_paper.html
- MV3DIS: https://openaccess.thecvf.com/content/CVPR2026/html/Zhao_MV3DIS_Multi-View_Mask_Matching_via_3D_Guides_for_Zero-Shot_3D_CVPR_2026_paper.html
- GeoGuide: https://arxiv.org/abs/2603.26260
- Mosaic3D: https://arxiv.org/abs/2502.02548
- OpenTrack3D: https://arxiv.org/abs/2512.03532
- SpaCeFormer: https://arxiv.org/abs/2604.20395
