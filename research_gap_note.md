# Research Gap Note

主题：在线、基于图表示、zero-shot、强 2D/3D 双模态耦合的 3D 重建 / 对象级建图系统  
日期：2026-04-21
项目暂定名：`Dual-Consistency Graph Memory / DuoGraph3D`  
GitHub 仓库：`git@github.com:Xin200203/duograph3D.git`

---

## 0. 这份笔记要回答什么

这份笔记不再泛泛地问“图有没有人做过”“online 有没有人做过”，而是更精确地回答下面三个问题：

1. 如果目标是：
   - `online`
   - `zero-shot / open-vocabulary`
   - `object-centric`
   - `graph-based`
   - `2D temporal consistency + 3D geometric consistency`
   - `服务于 3D reconstruction / mapping`
   
   那这个交集目前是否已经被现有工作占满？

2. 目前哪些方向已经很强、不能再拿来当 novelty？

3. 真正还存在的高价值空白是什么？

---

## 1. 先给核心判断

### 1.1 一句话结论

> 当前并不存在“online zero-shot 3D segmentation / mapping”这一大方向上的空白；  
> 但在“把 2D 视频时序记忆、3D 多视角几何一致性、以及 object-centric graph memory 统一进同一个在线 zero-shot 3D reconstruction 系统”这个更窄的交集上，仍然存在真实而有价值的空白。

### 1.2 更具体一点

下面这些方向，已经分别被做得比较强：

- offline zero-shot 3D instance segmentation
- online zero-shot 3D segmentation
- open-vocabulary 3D object map / scene graph
- 2D 视频掩码时序 propagation

但下面这件事，还没有被一个主流方法完整占住：

> **在线维护 object graph memory，并且同时显式利用**
> 1. **2D 视频时序连续性**
> 2. **3D 多视角几何一致性**
> 3. **当前观测修复图 + 当前对象对历史对象关联图**
> 来完成 zero-shot 的对象级 3D reconstruction / mapping。

---

## 2. 已有工作版图

这一节只做“版图划分”，不急着讲 gap。

### 2.1 2D 视频时序 backbone

代表：

- [DEVA, ICCV 2023](https://openaccess.thecvf.com/content/ICCV2023/html/Cheng_Tracking_Anything_with_Decoupled_Video_Segmentation_ICCV_2023_paper.html)

它解决的是：

- image segmentation 和 temporal propagation 的解耦
- propagation-first 的视频掩码时序骨架
- open-world / large-vocabulary video segmentation 的 2D 时序基础

它没做的是：

- 3D object-centric mapping
- 显式 3D graph memory

### 2.2 offline zero-shot / open-vocabulary 3D instance segmentation

代表：

- [OpenMask3D, NeurIPS 2023](https://arxiv.org/abs/2306.13631)
- [Open3DIS, CVPR 2024](https://openaccess.thecvf.com/content/CVPR2024/papers/Nguyen_Open3DIS_Open-Vocabulary_3D_Instance_Segmentation_with_2D_Mask_Guidance_CVPR_2024_paper.pdf)
- [SAI3D, CVPR 2024](https://openaccess.thecvf.com/content/CVPR2024/papers/Yin_SAI3D_Segment_Any_Instance_in_3D_Scenes_CVPR_2024_paper.pdf)
- [MaskClustering, CVPR 2024](https://openaccess.thecvf.com/content/CVPR2024/papers/Yan_MaskClustering_View_Consensus_based_Mask_Graph_Clustering_for_Open-Vocabulary_3D_CVPR_2024_paper.pdf)

它们解决的是：

- 多视角 2D masks 如何支撑 3D instance grouping
- zero-shot / open-vocabulary 3D segmentation
- primitive graph / mask graph / clustering

它们没做强的是：

- 在线 object memory
- 2D 视频 propagation 作为主时序 prior

### 2.3 online zero-shot 3D segmentation

代表：

- [EmbodiedSAM, ICLR 2025 Oral](https://arxiv.org/abs/2408.11811)
- [OnlineAnySeg, CVPR 2025](https://openaccess.thecvf.com/content/CVPR2025/papers/Tang_OnlineAnySeg_Online_Zero-Shot_3D_Segmentation_by_Visual_Foundation_Model_Guided_CVPR_2025_paper.pdf)

它们解决的是：

- streaming RGB-D / online 3D segmentation
- foundation model 引导的 2D -> 3D 在线融合
- 在在线 setting 里做 zero-shot 3D segmentation

尤其是 `OnlineAnySeg` 已经很接近你的设定：

- online
- zero-shot
- 2D masks
- 3D overlap query
- semantic / geometric similarity
- third-view consensus

所以必须明确：

> 仅仅做“online + zero-shot + 2D mask 融到 3D”已经不构成足够强的空白。

### 2.4 online open-vocabulary 3D mapping

代表：

- [ConceptFusion, RSS 2023](https://arxiv.org/abs/2302.07241)
- [Open-Fusion, 2023](https://arxiv.org/abs/2310.03923)

它们解决的是：

- online 3D map
- multimodal feature fusion
- open-set / open-vocabulary queryability

它们更偏：

- dense feature map
- TSDF / field / voxel hashing

而不是：

- object graph memory

### 2.5 object-centric graph representation

代表：

- [ConceptGraphs, 2023](https://concept-graphs.github.io/assets/pdf/2023-ConceptGraphs.pdf)
- [Open3DSG, CVPR 2024](https://openaccess.thecvf.com/content/CVPR2024/papers/Koch_Open3DSG_Open-Vocabulary_3D_Scene_Graphs_from_Point_Clouds_with_Queryable_CVPR_2024_paper.pdf)

它们解决的是：

- open-vocabulary object-centric 3D representation
- queryable 3D scene graph

它们没把重点放在：

- 2D 视频时序 memory
- propagation-first 的视频先验

---

## 3. 哪些地方已经不空白了

这部分最重要，因为它决定了以后 proposal / paper 里哪些话不能说。

### 3.1 不能再说“第一个 online zero-shot 3D segmentation”

因为：

- [OnlineAnySeg, CVPR 2025](https://openaccess.thecvf.com/content/CVPR2025/papers/Tang_OnlineAnySeg_Online_Zero-Shot_3D_Segmentation_by_Visual_Foundation_Model_Guided_CVPR_2025_paper.pdf)
- [EmbodiedSAM, ICLR 2025 Oral](https://arxiv.org/abs/2408.11811)

已经把这块占掉了。

### 3.2 不能再说“第一个 open-vocabulary 3D graph representation”

因为：

- [ConceptGraphs](https://concept-graphs.github.io/assets/pdf/2023-ConceptGraphs.pdf)
- [Open3DSG](https://openaccess.thecvf.com/content/CVPR2024/papers/Koch_Open3DSG_Open-Vocabulary_3D_Scene_Graphs_from_Point_Clouds_with_Queryable_CVPR_2024_paper.pdf)

已经明确做了 object-centric / scene-graph 形式的 3D 表达。

### 3.3 不能再说“第一个利用 foundation model 做 online 3D understanding”

因为：

- `ConceptFusion`
- `Open-Fusion`
- `EmbodiedSAM`
- `OnlineAnySeg`

都已经覆盖了这一类叙事。

### 3.4 不能再把“像 SAI3D 一样利用 2D 与 3D 双模态信息”当成唯一 novelty

因为：

- [SAI3D](https://openaccess.thecvf.com/content/CVPR2024/papers/Yin_SAI3D_Segment_Any_Instance_in_3D_Scenes_CVPR_2024_paper.pdf)
- [MaskClustering](https://openaccess.thecvf.com/content/CVPR2024/papers/Yan_MaskClustering_View_Consensus_based_Mask_Graph_Clustering_for_Open-Vocabulary_3D_CVPR_2024_paper.pdf)
- [Open3DIS](https://openaccess.thecvf.com/content/CVPR2024/papers/Nguyen_Open3DIS_Open-Vocabulary_3D_Instance_Segmentation_with_2D_Mask_Guidance_CVPR_2024_paper.pdf)

都已经证明：

- 2D masks
- 3D geometry
- graph / clustering / affinity

这一方向本身已经成熟。

---

## 4. 真正还存在的 gap 是什么

这一节只讲我认为仍然成立的 gap。

## 4.1 Gap A：现有 online zero-shot 3D 方法，很少把 2D 视频时序记忆当成一级公民

这是目前最有价值的 gap 之一。

### 现状

当前在线 zero-shot 3D 方法通常做的是：

- 当前帧出 2D masks
- 把 masks 在线 lift / merge 到 3D
- 利用 overlap / feature / geometry / multi-view support 做关联

例如：

- [OnlineAnySeg](https://openaccess.thecvf.com/content/CVPR2025/papers/Tang_OnlineAnySeg_Online_Zero-Shot_3D_Segmentation_by_Visual_Foundation_Model_Guided_CVPR_2025_paper.pdf)

这条路线已经很强。

### 但缺什么

它们通常没有像 DEVA 这样，把下面这些 2D 视频先验明确做成主干：

- propagation-first
- old object carry-over
- detection frame / propagation frame 分离
- miss-based deletion
- video memory

换句话说：

> 现有很多在线 3D 方法更像“多视角在线 mask merging”，而不是“带视频时序记忆的对象级建图”。

### 为什么这是真 gap

因为对于 object-centric online reconstruction 来说：

- 当前帧分割质量不稳定
- 遮挡与漏检频繁
- 纯当前帧驱动的 3D 合并容易不稳

而 DEVA 类的 2D temporal prior 恰好能补这一块。

---

## 4.2 Gap B：现有方法要么偏 dense map，要么偏 scene graph，缺少“object graph memory”作为主表示

### 现状

主流方法通常二选一：

#### 路线一：dense map / voxel / TSDF / field

代表：

- [ConceptFusion](https://arxiv.org/abs/2302.07241)
- [Open-Fusion](https://arxiv.org/abs/2310.03923)
- [OnlineAnySeg](https://openaccess.thecvf.com/content/CVPR2025/papers/Tang_OnlineAnySeg_Online_Zero-Shot_3D_Segmentation_by_Visual_Foundation_Model_Guided_CVPR_2025_paper.pdf)

优点：

- 在线性好
- 几何融合强

缺点：

- 对象级身份、关系、增量更新的表达不够核心

#### 路线二：scene graph / object graph

代表：

- [ConceptGraphs](https://concept-graphs.github.io/assets/pdf/2023-ConceptGraphs.pdf)
- [Open3DSG](https://openaccess.thecvf.com/content/CVPR2024/papers/Koch_Open3DSG_Open-Vocabulary_3D_Scene_Graphs_from_Point_Clouds_with_Queryable_CVPR_2024_paper.pdf)

优点：

- 表达能力强
- object-centric 很清楚

缺点：

- segmentation / reconstruction / temporal propagation 主链往往不是最强项

### Gap

缺少的是：

> 把“在线维护的对象图记忆”作为核心表示，而不是把对象图当成最后从 dense map 上抽象出来的结果。

这个 gap 对你的目标非常关键，因为你想做的是：

- online
- object-centric
- graph-based
- reconstruction system

---

## 4.3 Gap C：当前观测修复图 与 当前对象到历史对象关联图，缺少统一分层设计

这是我认为最适合切入的 gap。

### 现状

当前不同工作通常只擅长其中一层：

#### 更偏当前观测修复

- [SAI3D](https://openaccess.thecvf.com/content/CVPR2024/papers/Yin_SAI3D_Segment_Any_Instance_in_3D_Scenes_CVPR_2024_paper.pdf)
- [MaskClustering](https://openaccess.thecvf.com/content/CVPR2024/papers/Yan_MaskClustering_View_Consensus_based_Mask_Graph_Clustering_for_Open-Vocabulary_3D_CVPR_2024_paper.pdf)
- `GraphSeg`

#### 更偏当前对象到历史对象的关联

- `ODAM`
- `GNN3DMOT`
- `GMTracker`

#### 更偏 propagation backbone

- [DEVA](https://openaccess.thecvf.com/content/ICCV2023/html/Cheng_Tracking_Anything_with_Decoupled_Video_Segmentation_ICCV_2023_paper.html)

### Gap

缺少一个被清楚写出来并真正跑通的双层框架：

1. `Layer-1`: current evidence graph
   - 当前帧 / 当前短窗 raw evidence 修复
   - 解决 same-frame over-seg / partial evidence

2. `Layer-2`: current-object ↔ memory-object graph
   - 当前对象和历史对象显式关联
   - 解决 long-term identity / re-entry / repeated objects

而且这两层要共享：

- 2D 视频时序信息
- 3D 几何信息
- object-level memory state

这正是你当前想做的结构。

---

## 5. 哪些工作最接近未来的目标

如果要找“真正离我们未来方法最近的邻居”，我会排成下面这个顺序：

### 第一类：最接近整体设定

1. [OnlineAnySeg](https://openaccess.thecvf.com/content/CVPR2025/papers/Tang_OnlineAnySeg_Online_Zero-Shot_3D_Segmentation_by_Visual_Foundation_Model_Guided_CVPR_2025_paper.pdf)
2. [ConceptGraphs](https://concept-graphs.github.io/assets/pdf/2023-ConceptGraphs.pdf)

### 第二类：最接近 2D/3D 融合与图 merge

3. [SAI3D](https://openaccess.thecvf.com/content/CVPR2024/papers/Yin_SAI3D_Segment_Any_Instance_in_3D_Scenes_CVPR_2024_paper.pdf)
4. [MaskClustering](https://openaccess.thecvf.com/content/CVPR2024/papers/Yan_MaskClustering_View_Consensus_based_Mask_Graph_Clustering_for_Open-Vocabulary_3D_CVPR_2024_paper.pdf)

### 第三类：最接近显式对象关联

5. `ODAM`
6. `GMTracker`

### 第四类：最接近 2D 时序 backbone

7. [DEVA](https://openaccess.thecvf.com/content/ICCV2023/html/Cheng_Tracking_Anything_with_Decoupled_Video_Segmentation_ICCV_2023_paper.html)

---

## 6. 最可能成立的“新工作空间”应该如何表述

我认为最合理、也最稳的 gap 表述不是“第一个做 online zero-shot 3D”，而是下面这类。

### 表述版本 A：系统 gap

> 现有方法通常只覆盖以下子问题之一：
> `offline zero-shot 3D instance segmentation`、
> `online zero-shot 3D mask merging`、
> `open-vocabulary object graph mapping`、
> 或 `2D video temporal propagation`。  
> **缺少一个统一系统，把 2D temporal consistency、3D multi-view geometric consistency 和 object-centric graph memory 同时纳入在线 zero-shot 3D reconstruction。**

### 表述版本 B：表示 gap

> 现有在线 zero-shot 3D 方法多依赖 dense map、mask bank 或相似度矩阵，而缺少把对象图记忆作为核心中间表示的框架，因此在 long-term identity、对象级状态维护和关系查询方面仍不理想。

### 表述版本 C：算法 gap

> 现有方法通常只在单一层面融合证据：要么修复当前观测，要么关联当前观测到历史对象。  
> **缺少一个双层图框架，同时处理**
> 1. 当前观测修复  
> 2. 当前对象到历史对象关联  
> 并让两层显式共享 2D 与 3D 双模态证据。

---

## 7. 这是否可以通过“吸收不同工作的优点”来完成

可以，而且我认为这是最自然的路线。

### 7.1 从 DEVA 借

借什么：

- propagation-first
- video memory
- detection frame / propagation frame 分离
- deletion / carry-over 机制

作用：

- 把强 2D 视频时序先验接入 3D object pipeline

### 7.2 从 SAI3D / MaskClustering / GraphSeg 借

借什么：

- primitive / mask graph
- third-view support / view consensus
- progressive merge / graph contraction

作用：

- 做好 `Layer-1` 的 current evidence graph

### 7.3 从 OnlineAnySeg 借

借什么：

- 在线 3D overlap query
- voxel hashing
- semantic / geometric / third-view consistency 的高效实现

作用：

- 解决 online setting 下的效率与可扩展性

### 7.4 从 ODAM / GNN3DMOT / GMTracker 借

借什么：

- `ODAM`：frame-to-model association
- `GNN3DMOT`：feature interaction before matching
- `GMTracker`：二阶 graph matching 作为后续升级方向

作用：

- 做好 `Layer-2` 的 current-object ↔ memory-object 关联

### 7.5 从 ConceptGraphs / Open3DSG 借

借什么：

- object-centric graph representation
- queryable scene graph

作用：

- 把最终输出从“dense label map”升级成“可维护的对象图记忆”

---

## 8. 已有工作的经验参考

这一节不再问“谁和我们最像”，而是把已有工作沉淀成一组可执行的经验原则。

目标是回答：

> 如果我们真的要做这项工作，哪些经验应该直接继承，哪些坑应该主动绕开？

### 8.1 总原则

我认为最值得保留的总原则有五条：

1. **不要把当前观测修复和跨时对象关联混成一个大图一次性求解。**
2. **不要把 2D masks 当作最终对象表示，而应把它们当作对象证据。**
3. **不要只维护 dense map，也不要只维护后验 scene graph，而应维护 online object graph memory。**
4. **不要太早跳到二阶 graph matching；先把一阶 current-to-memory association 做清楚。**
5. **不要把“online、zero-shot、graph”这些标签本身当 novelty，而要把它们统一成一个必要的方法结构。**

### 8.2 从 DEVA 应该学到什么

参考：

- [DEVA, ICCV 2023](https://openaccess.thecvf.com/content/ICCV2023/html/Cheng_Tracking_Anything_with_Decoupled_Video_Segmentation_ICCV_2023_paper.html)

#### 最值得继承的经验

1. **解耦是有价值的。**  
   image model 和 temporal backbone 分开，能显著提高系统的可替换性。
2. **propagation-first 很重要。**  
   当前状态不应该完全由当前帧 detection 决定；旧对象应该能被 memory 带过短期漏检。
3. **检测应该是周期性修正，而不是每帧重新开始。**
4. **删除逻辑必须存在，而且要绑定在支持证据上。**

#### 不应直接照搬的地方

1. `compare-and-merge` 太轻，主要是对象级 IoU 贪心合并。
2. `in-clip consensus` 解决的是短窗时序去噪，不是同帧图合并。
3. 它的 memory 是 2D 掩码传播 memory，不是 3D object graph memory。

#### 对我们的直接启示

> DEVA 更适合作为 **2D temporal backbone**，而不是直接充当 3D object association 的最终答案。

### 8.3 从 OnlineAnySeg 应该学到什么

参考：

- [OnlineAnySeg, CVPR 2025](https://openaccess.thecvf.com/content/CVPR2025/papers/Tang_OnlineAnySeg_Online_Zero-Shot_3D_Segmentation_by_Visual_Foundation_Model_Guided_CVPR_2025_paper.pdf)

#### 最值得继承的经验

1. **online 系统的第一性问题之一是效率，而不是单步推理精度。**  
   voxel hashing、overlap query、在线索引结构都不是工程细节，而是方法成立条件。
2. **在线 3D 关联不能只靠单一相似度。**  
   overlap、semantic similarity、geometric similarity、third-view support 需要组合。
3. **third-view / third-party support 非常重要。**  
   仅靠当前帧和上一帧很容易被局部错误带偏。

#### 不应直接照搬的地方

1. 它更像“在线 3D mask merging”，而不是“2D temporal memory 主导的对象建图”。
2. object graph memory 不是它的核心表示。

#### 对我们的直接启示

> 如果我们要做 online object graph memory，必须同时继承它的 **高效在线空间索引能力**，否则系统会在规模上失控。

### 8.4 从 SAI3D 应该学到什么

参考：

- [SAI3D, CVPR 2024](https://openaccess.thecvf.com/content/CVPR2024/papers/Yin_SAI3D_Segment_Any_Instance_in_3D_Scenes_CVPR_2024_paper.pdf)

#### 最值得继承的经验

1. **2D masks 更适合作为“支持 primitive / object merge 的证据”，而不是最终 3D object 本身。**
2. **primitive / superpoint 是比原始 point 或原始 mask 更稳定的 3D 更新单元。**
3. **progressive merge 很重要。**  
   先高置信局部，再逐步扩展，通常比一次性全局粗暴 merge 更稳。

#### 不应直接照搬的地方

1. 它主要是 offline / multi-view segmentation，而不是 online memory system。
2. 它没有显式 2D temporal propagation prior。

#### 对我们的直接启示

> 我们应该把 2D masks 看成“证据”，把 3D primitive / object node 看成“更新单元”。

### 8.5 从 MaskClustering 应该学到什么

参考：

- [MaskClustering, CVPR 2024](https://openaccess.thecvf.com/content/CVPR2024/papers/Yan_MaskClustering_View_Consensus_based_Mask_Graph_Clustering_for_Open-Vocabulary_3D_CVPR_2024_paper.pdf)

#### 最值得继承的经验

1. **view consensus 不是小技巧，而是强先验。**
2. **全局图聚类比纯 pairwise threshold 更稳。**
3. **第三方支持（third-party support）是一类非常值得保留的边权思想。**

#### 不应直接照搬的地方

1. 全局 mask graph 聚类天然偏 offline。
2. 长时 online memory 如果直接做全局图，规模和延迟都可能失控。

#### 对我们的直接启示

> `MaskClustering` 最适合成为我们 `layer-1` 边权定义与支持统计的思想来源，而不是 online solver 的直接模板。

### 8.6 从 GraphSeg 应该学到什么

参考：

- 见你的阅读笔记中对 `GraphSeg` 的总结

#### 最值得继承的经验

1. **solver 设计和 edge 设计同样重要。**
2. **图收缩 / 阶段式 contraction 常常比单次 connected components 更稳。**

#### 对我们的直接启示

> 我们后续在 `layer-1` 里，应该优先从“简单阈值聚类”升级到“更稳的阶段式 merge / contraction”，而不是立刻上重模型。

### 8.7 从 ConceptFusion / Open-Fusion 应该学到什么

参考：

- [ConceptFusion, RSS 2023](https://arxiv.org/abs/2302.07241)
- [Open-Fusion, 2023](https://arxiv.org/abs/2310.03923)

#### 最值得继承的经验

1. **dense multimodal map 仍然非常有价值。**
2. **开放词汇语义最好持续累积，而不是单帧决定。**

#### 对我们的直接启示

> 最自然的路线不是“dense map 或 object graph 二选一”，而是：  
> **dense substrate + object graph memory**

### 8.8 从 ConceptGraphs / Open3DSG 应该学到什么

参考：

- [ConceptGraphs](https://concept-graphs.github.io/assets/pdf/2023-ConceptGraphs.pdf)
- [Open3DSG, CVPR 2024](https://openaccess.thecvf.com/content/CVPR2024/papers/Koch_Open3DSG_Open-Vocabulary_3D_Scene_Graphs_from_Point_Clouds_with_Queryable_CVPR_2024_paper.pdf)

#### 最值得继承的经验

1. **object graph 是值得做核心表示的。**
2. **queryable representation 很重要。**
3. **对象级 descriptor、关系边、和节点状态维护要从一开始就设计清楚。**

#### 对我们的直接启示

> object graph memory 应该是 reconstruction 主链的一部分，而不是 reconstruction 结束后的附属导出。

### 8.9 从 ODAM 应该学到什么

参考：

- 见你的阅读笔记中对 `ODAM` 的总结

#### 最值得继承的经验

1. **frame-to-model association 非常关键。**
2. **当前观测不等于对象本身，当前观测应先形成 current-object descriptor。**
3. **历史对象应该先做多视角 / 多时刻 descriptor fusion，再和当前匹配。**

#### 对我们的直接启示

> `layer-2` 最自然的设定不是 frame-to-frame，而是 **current-object ↔ memory-object**。

### 8.10 从 GNN3DMOT 应该学到什么

参考：

- 见你的阅读笔记中对 `GNN3DMOT` 的总结

#### 最值得继承的经验

1. **候选剪枝非常重要。**
2. **图可以先用于 feature interaction，而不必直接上 graph matching。**
3. **先把 affinity 做好，再谈更复杂求解器。**

#### 对我们的直接启示

> `GNN3DMOT` 更适合作为 `layer-2` 的 feature encoder / affinity baseline，而不是最终方法。

### 8.11 从 GMTracker / Learnable Graph Matching 应该学到什么

参考：

- 见你的阅读笔记中对 `GMTracker` 的总结

#### 最值得继承的经验

1. **二阶 graph matching 真正有价值，但只在 active set 足够小、候选足够干净时才 practical。**
2. **second-order relation 的价值主要出现在：**
   - 重复对象
   - 长时歧义
   - 遮挡后重现
   - 视角变化大

#### 对我们的直接启示

> `GMTracker` 是 `layer-2` 的后续升级方向，不是当前第一阶段实现的起点。

### 8.12 沉淀成 10 条设计原则

1. `Layer-1` 和 `Layer-2` 必须分开。
2. 2D masks 是证据，不是最终对象表示。
3. 3D primitive / object node 才是更稳定的更新单元。
4. propagation-first 的 2D temporal prior 很值得引入 3D。
5. online 系统必须优先考虑高效 overlap query 与 active set 控制。
6. online object graph memory 必须是核心表示，而不是后处理结果。
7. current-object ↔ memory-object 比 frame-to-frame 更适合 mapping。
8. 先做强的一阶 association，再考虑二阶 graph matching。
9. solver 设计和 edge 设计同等重要。
10. novelty 不在“graph / online / zero-shot”这些标签本身，而在它们是否被统一成一个必要结构。

---

## 9. 最后结论

### 8.1 有空白，但不是大而泛的空白

不存在的空白：

- online zero-shot 3D segmentation 本身
- open-vocabulary 3D graph representation 本身
- 2D foundation model 融到 3D 本身

仍然存在的空白：

> **在线、zero-shot、object-centric、graph-based 3D reconstruction 系统，其中 2D 视频时序记忆与 3D 多视角几何一致性被共同作为一级建模对象。**

### 8.2 能否吸收不同工作的优点合成一个新工作

可以，而且这是最合理的路线。

最可能成立的技术组合是：

- `DEVA`：2D temporal memory backbone
- `SAI3D / MaskClustering / GraphSeg`：current evidence graph
- `OnlineAnySeg`：online 3D overlap query / efficient merging
- `ODAM / GNN3DMOT / GMTracker`：memory-aware association
- `ConceptGraphs / Open3DSG`：最终 object graph memory 表示

### 8.3 当前最值得强调的 novelty 方向

如果以后真的做成论文，我认为最值得强调的不是：

- “我们也做 online zero-shot 3D”

而是：

> **我们把 2D temporal consistency、3D geometric consistency、以及 object graph memory 统一进了一个双层图的在线 zero-shot object-centric reconstruction 系统。**

### 8.4 这个 gap 是否足以支撑 2027 顶会 / 顶刊

我的判断是：

> **gap 本身是够的，但仅凭 gap 不够。**

更准确地说：

- 这个 gap 足以支撑一篇 `CVPR 2027 / ICCV 2027 / IJCV / TPAMI` 级别的工作主线
- 但前提是你把它做成：
  - 真正统一的方法框架
  - 而不是多篇方法的工程拼装

如果最后只做到：

- online zero-shot 3D 系统能跑
- graph 表示也有
- 2D temporal backbone 也接进来了

那么这更像“有潜力的系统原型”，还不自动等于顶会 / 顶刊级贡献。

真正能支撑 2027 顶会 / 顶刊的，是下面这三点同时成立：

1. `2D temporal consistency + 3D geometric consistency + object graph memory`
   之间有清楚的方法学统一
2. 相对 `OnlineAnySeg / SAI3D / ConceptGraphs / DEVA` 有扎实而明确的收益
3. 有清楚的问题定义和不可替代的方法贡献，而不是“多模块都不错”

---

## 10. 核心参考来源

- [DEVA, ICCV 2023](https://openaccess.thecvf.com/content/ICCV2023/html/Cheng_Tracking_Anything_with_Decoupled_Video_Segmentation_ICCV_2023_paper.html)
- [OpenMask3D, NeurIPS 2023](https://arxiv.org/abs/2306.13631)
- [ConceptFusion, RSS 2023](https://arxiv.org/abs/2302.07241)
- [Open-Fusion, 2023](https://arxiv.org/abs/2310.03923)
- [ConceptGraphs, 2023](https://concept-graphs.github.io/assets/pdf/2023-ConceptGraphs.pdf)
- [Open3DIS, CVPR 2024](https://openaccess.thecvf.com/content/CVPR2024/papers/Nguyen_Open3DIS_Open-Vocabulary_3D_Instance_Segmentation_with_2D_Mask_Guidance_CVPR_2024_paper.pdf)
- [SAI3D, CVPR 2024](https://openaccess.thecvf.com/content/CVPR2024/papers/Yin_SAI3D_Segment_Any_Instance_in_3D_Scenes_CVPR_2024_paper.pdf)
- [MaskClustering, CVPR 2024](https://openaccess.thecvf.com/content/CVPR2024/papers/Yan_MaskClustering_View_Consensus_based_Mask_Graph_Clustering_for_Open-Vocabulary_3D_CVPR_2024_paper.pdf)
- [Open3DSG, CVPR 2024](https://openaccess.thecvf.com/content/CVPR2024/papers/Koch_Open3DSG_Open-Vocabulary_3D_Scene_Graphs_from_Point_Clouds_with_Queryable_CVPR_2024_paper.pdf)
- [EmbodiedSAM, ICLR 2025 Oral](https://arxiv.org/abs/2408.11811)
- [OnlineAnySeg, CVPR 2025](https://openaccess.thecvf.com/content/CVPR2025/papers/Tang_OnlineAnySeg_Online_Zero-Shot_3D_Segmentation_by_Visual_Foundation_Model_Guided_CVPR_2025_paper.pdf)
