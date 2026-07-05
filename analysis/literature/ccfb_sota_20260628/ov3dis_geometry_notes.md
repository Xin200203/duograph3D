# OV-3DIS / 几何一致性文献精读笔记（CCF-B 方向）

日期：2026-06-28
范围：仅基于本地已拉取文本 `analysis/literature/ccfb_sota_20260628/texts/*.txt` 精读整理，不改代码，不动其他文件。

## 一、快速结论

这批论文的共同主线非常清晰：**先想办法拿到“像样的 3D carrier/proposal”，再做语义读出；然后用多视角、一致性、上下文或几何先验把读出抬稳。**

但对 DuoGraph3D 来说，一个更重要的结论是：

- 这些方法大多默认“proposal 质量”和“语义读出质量”都可以通过更好的 2D/多视图/上下文来一起改善；
- 而当前 E70 / E71 / A2 的结果说明，**最终精度仍强烈受 carrier reliability 与 export/source separation 限制**，并不等价于“只要更强的语义模型就能赢”。

因此，这批文献更适合为 **carrier reliability gate v2** 提供“结构模板”和“风险边界”，而不是直接给出一个可照搬的统一方案。

---

## 二、逐篇精读

### 1) Open3DIS (CVPR 2024)

**主题**
- Open-vocabulary 3D instance segmentation。
- 核心问题：仅靠纯 3D proposal 或纯 2D 投影都容易在小目标、歧义目标、长尾类别上失败。

**Pipeline**
1. 2D 文本/实例 grounding，得到每帧 2D mask。
2. 2D mask 跨帧 lift 到 3D 点云。
3. 3D proposal aggregation（tracking / hierarchical agglomeration 类思路）。
4. 将 2D 与 3D proposals 组合成更完整的 3D instance masks。
5. 用 pointwise / multi-scale CLIP feature 做 open-vocab 分类读出。

**创新点**
- `2D-Guided 3D Instance Proposal Module`：把多帧 2D mask 聚成几何一致的 3D proposal，补齐小物体和模糊目标。
- `Pointwise Feature Extraction`：做更细粒度的 3D proposal 表征。
- 2D proposal 与 3D proposal 的组合式补强。

**关键实验指标**
- ScanNet200：
  - 仅 2D：`AP 18.2 / AP50 26.1 / AP25 31.4`
  - 2D+3D：`AP 23.7 / AP50 29.4 / AP25 32.8`
  - 与 OpenMask3D 等相比，ScanNet200 上 AP 提升约 1.5x 级别（文中表述）。
- Replica：
  - 仅 2D：`AP 18.1 / AP50 26.7 / AP25 30.5`
  - 2D+3D：`AP 25.7 / AP50 34.9 / AP25 42.3`（Top-K setting）
- S3DIS：Top-1/Top-K 两种协议都做了，2D+3D 显著优于 Open3DIS 及其他基线。

**对 DuoGraph3D 的启发**
- 它强化了一个规律：**proposal 搭得好，后面的 readout 才有意义**。
- 但它也暴露出 Open-vocab 3D 任务常见的“2D/3D 协议差异”问题：不同 setting、Top-1/Top-K、proposal 来源会让数值不可直接横比。DuoGraph3D 的论文叙事一定要把评测协议讲死。

---

### 2) Details Matter for Indoor Open-vocabulary 3D Instance Segmentation (ICCV 2025)

**主题**
- 不是“发明全新范式”，而是把现有概念做成一个更稳的 recipe。
- 重点在：proposal 聚合、object-centric classification、false positive 抑制。

**Pipeline**
1. 2D VLM / open-vocab 检测器在 RGB-D 帧上产生 2D grounding。
2. 用 tracking-based 3D proposal aggregation，把跨帧 proposal 变成更完整的 3D mask。
3. 迭代 merge / removal，去掉重叠和 partial proposal。
4. 分类阶段把 CLIP 换成 Alpha-CLIP，用 mask 作为 alpha channel，让 readout 更 object-centric。
5. 引入 SMS（Standardized Maximum Similarity）做置信度归一化，过滤 false positives。

**创新点**
- `tracking-based proposal aggregation` + `iterative merging/removal`：把 proposal 质量做实。
- `Alpha-CLIP`：用 object mask 减少背景噪声。
- `SMS`：对 proposal-to-text similarity 做标准化，专门压 false positive。
- 明确指出：已有概念并非互斥，而是互补。

**关键实验指标**
- ScanNet200（Top-1）：
  - 2D only：`AP 21.5 / AP50 31.2 / AP25 37.7`
  - 3D only：`AP 24.2 / AP50 31.8 / AP25 36.4`
  - 2D+3D：`AP 25.8 / AP50 32.5 / AP25 36.2`
- ScanNet200（Top-K）：
  - 2D+3D：`AP 32.7 / AP50 41.4 / AP25 45.3`
- Replica：
  - Top-1 2D+3D：`AP 22.6 / AP50 31.7 / AP25 37.7`
  - Top-K 2D+3D：`AP 25.7 / AP50 34.9 / AP25 42.3`
- S3DIS：`APB50 60.8 / APN50 26.3`（B8/N4 setting）；`APB50 50.0 / APN50 29.0`（B6/N6 setting）。

**对 DuoGraph3D 的启发**
- 这篇最像“工程上真的能落地”的 recipe：**proposal 先 clean，再做 object-centric readout，再做置信度过滤**。
- 对 carrier reliability gate v2 最直接的启发是：
  - gate 不要只看单次读出；
  - 要显式加入 proposal 重叠、partial mask、tracklet consistency、SMS 类的“读出稳定性”指标；
  - 但要避免把过滤阈值做成过强的 hard veto，否则会伤 recall。

---

### 3) MV3DIS (CVPR 2026)

**主题**
- 从“每帧独立处理 + 只看 2D 分数”转向“3D 引导的多视图一致性匹配”。
- 主打 zero-shot 3D instance segmentation。

**Pipeline**
1. 先有 coarse 3D segments，作为共同 reference。
2. 用 `3D-guided mask matching` 在多视图之间匹配 2D masks。
3. 用 `3D coverage distributions` 强化多视图 mask consistency。
4. 根据视图一致的 2D mask 反向细化 coarse 3D segments。
5. 用 `depth consistency weighting` 估计投影可靠性，抑制遮挡歧义。

**创新点**
- `3D-guided mask matching (3DG-MM)`：用粗 3D segment 充当跨视图锚点。
- `depth consistency weighting (DCW)`：把 occlusion / projection reliability 显式建模。
- `coarse-to-fine` 的 view-consistency 递进式 refinement。

**关键实验指标**
- ScanNetV2 closed-vocabulary 3D instance segmentation：`mAP 38.5 / AP50 60.2 / AP25 76.2`。
- ScanNet200：`mAP 35.5 / AP50 54.7 / AP25 69.7`。
- ScanNet++：`mAP 22.0 / AP50 36.7 / AP25 51.7`。
- Replica：
  - Top-1 2D+3D：`mAP 22.6 / mAR 33.9`
  - Top-K 2D+3D：`mAP 25.7 / mAR 48.8`
- 消融：baseline `33.3 mAP` → 加 RR `35.5` → 加 3DG-MM `37.0` → 加 DCW `38.5`。

**对 DuoGraph3D 的启发**
- 这篇最值得借的不是具体模块名，而是一个结构：**先建立稳定 carrier/reference，再做 view-consistent matching，再做可靠性加权**。
- 这和 carrier reliability gate v2 非常接近：
  - carrier 先稳；
  - view/track consistency 作为辅助证据；
  - depth / visibility 权重作为软证据，不要一票否决所有弱但真实的 carrier。

---

### 4) Open-YOLO 3D (ICLR 2025)

**主题**
- 目标是“更快的 open-vocabulary 3D instance segmentation”。
- 核心立场：不要重度依赖 SAM + CLIP 的 multi-view 聚合，改用 2D object detector + 低粒度 label map。

**Pipeline**
1. 用 open-vocab 2D detector 在每帧上出 class-labeled bounding boxes。
2. 用这些 bbox 构建 `Low Granularity (LG) label map`。
3. 用 3D class-agnostic proposal network 提供 3D masks。
4. 用 `Multi-View Prompt Distribution (MVPDist)` 将多视图 label map 与 3D mask 对齐，给每个 3D proposal 选 prompt / label。

**创新点**
- `MVPDist`：利用多视图信息纠正 detector 误分类，预测更可靠的 3D mask label。
- 用 bbox 而不是密集 mask / CLIP feature 来做 prompt ID 估计，计算成本很低。
- 兼顾速度和精度，强调 real-time 应用。

**关键实验指标**
- 文中摘要：ScanNet200 val `mAP 24.7%`，推理约 `22 sec/scene`，相对最强已有方法约 `16×` 加速。
- 表格（ScanNet200 Top-1 / 2D+3D setting）：`mAP 25.8 / AP50 32.5 / AP25 36.2`。
- Replica Top-1 / 2D+3D：`mAP 22.6 / AP50 31.7 / AP25 37.7`。
- ScanNet200 class-agnostic：`AP 33.3 / AP50 51.9 / AP25 66.1`（2D only），`AP 46.6 / AP50 59.0 / AP25 64.4`（2D+3D）。

**对 DuoGraph3D 的启发**
- 这篇证明：**轻量 detector + 稀疏 label map + 多视图投票** 也能得到不错的 open-vocab 3D 结果。
- 但它的风险同样明显：它把“检测器给出的 class label”当作上游信号，适合做 prompt distribution，不适合作为最终绝对真值。
- 对 DuoGraph3D 来说，若引入类似机制，应该定位成 **candidate label prior**，而不是最终 source of truth。

---

### 5) OV3D-CG (ICCV 2025)

**主题**
- 关键补缺：现有 OV-3DIS 过度依赖 object-level CLIP 特征，忽视上下文关系。
- 于是提出 contextual guidance + MLLM reasoning。

**Pipeline**
1. Class-agnostic Proposal Module：`SAM-guided segmenter + pre-trained 3D segmentation model`，组合出 3D instance masks。
2. 为每个 instance 选择最佳视角。
3. 构造 3 种 context-aware 表征：`bounding box / landmarks / SAM mask`。
4. 将这些表征输入 MLLM，用 CoT prompting 做语义推理。
5. 输出 semantic label。

**创新点**
- `Semantic Reasoning Module`：不是简单 CLIP 相似度，而是上下文推理。
- 三种 context-aware representation 的对比，证明 `SAM mask` 最强。
- 使用 CoT prompting，让 MLLM 利用环境上下文完成更细粒度识别。

**关键实验指标**
- ScanNet200：
  - 2D only：`AP 21.5 / AP50 31.2 / AP25 37.7`
  - 3D only：`AP 24.2 / AP50 31.8 / AP25 36.4`
  - 2D+3D：`AP 25.8 / AP50 32.5 / AP25 36.2`
- Replica：`AP 25.4 / AP50 32.9 / AP25 37.0`。
- Oracle masks（ScanNet200）：`AP 44.9 / AP50 51.9 / AP25 40.6`（context feature / MLLM reasoning 明显吃到 oracle mask 红利）。
- 消融：
  - bbox / landmarks / SAM mask 中，`SAM mask` 最好。
  - CoT prompt 使 AP 从 `14.4` 提升到 `17.7`。

**对 DuoGraph3D 的启发**
- 这篇说明：**对象级语义读出不够，context 可以补；但前提仍是 mask/proposal 要靠谱。**
- 对 carrier reliability gate v2 很有用的点：
  - 先选“最可信视角”再做读出；
  - 让语义读出看到更完整的 object-centric crop / mask；
  - 但不要让 context 反客为主，去覆盖几何 carrier 的真实性。

---

### 6) GeoGuide (CVPR 2026)

**主题**
- Open-vocabulary 3D semantic segmentation 的几何一致性增强。
- 明确反对“直接把 3D 特征对齐到 2D 表征空间就完事”的路线。

**Pipeline**
1. 用预训练 3D backbone + 2D semantic features，估计 per-point uncertainty。
2. `Uncertainty-based Superpoint Distillation (USD)`：在 superpoint 内做加权蒸馏，抑制噪声、保留判别信息。
3. `Instance-level Mask Reconstruction (IMR)`：用几何先验重建完整 instance mask，补全局部缺失。
4. `Inter-Instance Relation Consistency (IIRC)`：对齐几何/语义 similarity matrix，约束同类实例间的一致性。

**创新点**
- 三层几何语义一致性：`superpoint → instance → inter-instance`。
- 不是简单平均池化，而是 uncertainty-weighted distillation。
- 通过几何相似矩阵约束跨实例语义漂移。

**关键实验指标**
- ScanNet v2：`mIoU 64.8 / mAcc 77.3`（SAS* setting，最佳）。
- Matterport3D：`mIoU 51.9 / mAcc 66.3`（SAS*）。
- nuScenes：`mIoU 50.3 / mAcc 74.2`（SAS*）。
- 长尾 Matterport3D（K=160）：`mIoU 9.3 / mAcc 12.2`（SAS*），但相较基线更稳。
- 消融（ScanNet v2）：baseline `54.2/66.6`，加 USD/IMR/IIRC 逐步升到 `59.8/72.5`。

**对 DuoGraph3D 的启发**
- 它给出一个非常直接的设计语义：**不要把所有几何先验塞成硬规则，而是做层级式一致性约束。**
- 对 gate v2 来说，这支持：
  - superpoint-level reliability；
  - instance-level completeness；
  - scene-level / inter-instance consistency。
- 但它也提醒：直接引入 3D pretrained features 不一定提升，可能反而破坏几何信息；这和我们 A2 的“memory-dense export 负向”风险是一致的。

---

### 7) OpenMask3D (arXiv / 2024)

**主题**
- Open-vocabulary 3D instance segmentation 的经典起点之一。
- 核心策略：**先有 class-agnostic 3D masks，再做 multi-view CLIP feature 聚合。**

**Pipeline**
1. 用 3D instance segmentation 网络产生 class-agnostic masks（默认 Mask3D）。
2. 对每个 mask，从多视图 RGB-D 中裁剪多尺度图像 patch。
3. 用 CLIP 抽特征，做 per-mask feature aggregation。
4. 用 text embedding 与 mask feature 做 cosine similarity，实现 open-vocab 分类。

**创新点**
- instance-centric，而不是 point-centric。
- multi-view fusion + multi-scale crop，提高 mask feature 的语义表达。
- 强调“高质量 3D proposal 是瓶颈”，oracle masks 能大幅抬高上限。

**关键实验指标**
- ScanNet200：`AP 15.4 / AP50 19.9 / AP25 23.1`。
- Replica：`AP 13.1 / AP50 18.4 / AP25 24.2`。
- ScanNet200 oracle masks：`AP 29.1 / AP50 31.1 / AP25 24.0`（并且 long-tail 上明显更强）。
- Ablation：
  - 无 2D mask / 无 multi-scale：`AP 12.9`
  - 两者都开：`AP 15.4`
- 论文明确说明：**更好的 mask proposals 会继续显著抬升上限。**

**对 DuoGraph3D 的启发**
- 这是最适合拿来解释“为什么 carrier 不能乱”的一篇：
  - mask quality 直接决定 open-vocab 结果上限；
  - oracle masks 一下子把 AP 抬上去，说明 proposal / carrier 真是主瓶颈。
- 但这也意味着：OpenMask3D 的思路对我们是“双刃剑”——它证明 proposal 很重要，同时也证明 **如果 carrier 本身就错了，后面的语义读出再强也救不回**。

---

## 三、成熟方法模式归纳

下面四类模式基本可以视为目前 OV-3DIS / 几何一致性论文中的“成熟模板”。

### 模式 1：2D mask → 3D proposal

**典型链路**
- 2D grounding / SAM / detector 输出帧级 mask 或 bbox；
- lift 到 3D；
- 通过 tracking / merging / clustering 形成完整 3D instance proposal。

**代表论文**
- Open3DIS：2D-guided 3D proposal module。
- Details Matter：tracking-based aggregation + iterative merging/removal。
- OV3D-CG：SAM-guided segmenter + 3D proposal backbone。
- MV3DIS：coarse 3D segment 反向约束 2D mask matching。

**共同经验**
- 单帧 2D mask 不足以形成稳定 3D instance；
- 跨帧 aggregation / merge / remove 是标准操作；
- 提前去掉 multi-object mask 和 partial mask 很关键。

---

### 模式 2：multi-view consistency

**典型链路**
- 将多视图投影结果视作多证据；
- 通过 tracklet、matching、coverage distribution、consensus ratio、depth consistency 等让多视图说同一件事。

**代表论文**
- MV3DIS：3D-guided mask matching + depth consistency weight。
- Details Matter：tracking-based aggregation + multi-view consensus。
- OpenMask3D：multi-view fusion + multi-scale crop。
- Open-YOLO 3D：MVPDist 利用多视图分布纠正 detector misclassification。

**共同经验**
- multi-view 不只是“更多帧”，而是“对同一 carrier 的重复证据”；
- 可靠性通常来自：一致性投票，而不是单次最高分；
- 但如果 3D carrier 本身错误，多视图一致性可能会放大错误。

---

### 模式 3：object-centric semantic readout

**典型链路**
- 先有 object mask / proposal；
- 在 object crop / alpha mask / best view / context crop 上读语义；
- 用 CLIP、Alpha-CLIP、MLLM、Gemini、CoT 等做分类。

**代表论文**
- OpenMask3D：mask-wise CLIP feature。
- Details Matter：Alpha-CLIP + SMS。
- OV3D-CG：best view + bbox/landmarks/SAM mask + MLLM CoT。
- Open-YOLO 3D：bbox label map + MVPDist 做 label readout。

**共同经验**
- object-centric readout 明显优于 point-centric 平均池化；
- background suppression（alpha mask / crop / best view）是核心；
- 语义读出越强，不代表就越能弥补错误 carrier。

---

### 模式 4：geometry-semantic consistency

**典型链路**
- 不把 2D 语义直接当最终权威；
- 用几何先验去修正语义漂移，或者用几何相似度约束语义一致性；
- 常见做法是 uncertainty weighting、instance reconstruction、inter-instance relation consistency。

**代表论文**
- GeoGuide：USD / IMR / IIRC。
- MV3DIS：depth consistency weight。
- Open3DIS / Details Matter：proposal merging/removal 作为几何一致性的一部分。

**共同经验**
- 几何一致性通常不是“单一 hard rule”，而是多层软约束；
- 最终目的是降低错误投影、遮挡和语义漂移带来的误差；
- 几何先验适合做 gate、rank、repair，而不是无条件覆盖所有语义读出。

---

## 四、对 DuoGraph3D carrier reliability gate v2 的可执行启发

下面是可直接落到 DuoGraph3D 设计里的建议，按优先级排序。

### 1. 把 gate 拆成“carrier 可靠性”与“semantic readout 可靠性”两层

**建议**
- 第一层：判断 carrier 是否值得进入最终导出。
- 第二层：在 carrier 已经通过后，再判断语义读出是否稳定。

**为什么**
- OpenMask3D / Details Matter / OV3D-CG 都说明 proposal quality 决定上限。
- E70 / E71 也显示：readout 很强，但 carrier 错了仍然会歪。

**实现上可考虑的信号**
- carrier 几何尺度、长宽高比、支持面、局部密度、track 连续性；
- 多视图 coverage、mask overlap、proposal merge 次数、partial ratio；
- 语义读出一致性、SMS / top-1-top-k margin、跨视图 label entropy。

---

### 2. Gate 应该是“软排序 + 局部修复”，不要一上来就 hard veto

**为什么**
- E71 已经说明：target-declared gate 能阻止很多错误 `vent→table`，但会错过 `bin` carrier。
- 这说明过强的 hard gate 会伤 recall。

**建议的形态**
- 先给候选 carrier 打分与分层：`pass / uncertain / reject`；
- `uncertain` 走 repair 分支，而不是直接丢弃；
- 只有 geometry 明确冲突时才 hard reject。

---

### 3. 把 multi-view consistency 用成“证据聚合器”，不是“真理生成器”

**为什么**
- MV3DIS / Details Matter 都证明多视图一致性能抬稳结果；
- 但多视图一致性本身不能保证正确，只能提高置信度。

**建议**
- 多视图一致性用于：
  - 提升 carrier rank；
  - 选择 best view；
  - 降低 edge cases 的读出噪声；
- 不建议把“多视图一致”直接等价成“必须导出”。

---

### 4. object-centric readout 要有“context 增益”，但不能覆盖几何真值

**为什么**
- OV3D-CG 证明上下文很有用；
- 但它依赖一个“像样的 mask/proposal”作为输入。

**建议**
- 对通过 carrier gate 的对象，做多模态语义读出：
  - crop / alpha mask / best view / context crop；
- 对未通过 carrier gate 的对象，不要让 MLLM/CLIP 直接接管最终标签。

---

### 5. Memory 更适合做 state / diagnostic / export-gating，不宜直接充当最终 dense source

**为什么**
- A2 已经说明：forced memory-dense export 是负的。
- GeoGuide 也提醒：直接把预训练 3D 表征塞进去，不一定更稳。

**建议**
- two-layer memory 继续保留，但角色要明确：
  - 状态维护；
  - 候选关联；
  - 诊断；
  - export gating。
- 最终 semantic output 仍应以 geometry carrier 为默认 source，memory 只在高覆盖/高一致性时升级为 source。

---

### 6. 把“修复”写成可审计的局部规则，而不是整场景全局 relabel

**为什么**
- Open3DIS / Details Matter / MV3DIS 都说明局部 merge / removal / refinement 有用；
- 但 E70/A1/A3 也说明过宽的 relabel 会负迁移。

**建议**
- 每条修复规则都要输出：
  - 触发 carrier；
  - 触发原因；
  - 修复前后 label；
  - 影响点数 / 覆盖率 / 置信度。
- 这样 paper 才能把 heuristic 包装成“可解释的 reliability policy”。

---

## 五、和当前 E70 / E71 / A2 结果的矛盾与风险

这里是最重要的“对照面”。这些论文给了很多成熟模式，但它们和我们当前结果之间有几个明显张力。

### 风险 1：文献普遍强化“更强语义读出”，而 E70 的主增益是“carrier repair”

**文献倾向**
- OpenMask3D / Details Matter / OV3D-CG 都在强调：更好的 CLIP / Alpha-CLIP / MLLM / CoT，会带来更好的 open-vocab 识别。

**我们当前结果**
- E70 的核心提升来自几何载体修复，尤其是 `tissue-paper→cloth` 和 office2 `bin→table`。
- A1 也显示 `vent→table` 不是主要正贡献。

**风险**
- 如果论文主故事写成“语义读出更强所以更好”，会与当前最强证据冲突。

**应对**
- 论文表述应把语义读出定位为 **secondary verifier**，而不是主因。

---

### 风险 2：文献倾向用更强的一致性约束统一一切，而 E71 说明“统一 gate”可能过严

**文献倾向**
- MV3DIS / GeoGuide 都喜欢把一致性做成更统一的约束模块。

**我们当前结果**
- E71 的 target-declared unified gate 只得到 `+0.665 mIoU / +2.755 mF1 / +5.926 F-mIoU`，明显低于 E70。

**风险**
- 如果把 gate v2 做成“一刀切统一规则”，可能会像 E71 一样：挡住错误，也挡掉正确 carrier。

**应对**
- 用分层 gate + soft repair，而不是单一 hard gate。

---

### 风险 3：文献把 memory / context 视作增益来源，但 A2 说明 memory-dense export 不是最终瓶颈

**文献倾向**
- GeoGuide 强调多层几何语义一致性；
- OV3D-CG 强调 context；
- 这些都容易被解读成“更强记忆 / 上下文就会更好”。

**我们当前结果**
- A2 显示：candidate / L1 / beta 改善的是诊断指标，不改变最终 official output；
- forced memory-dense export 反而是 `-2.483` avg ΔmIoU。

**风险**
- 如果把 memory 写成精度主因，风险很大。

**应对**
- 将 memory 写成 **state/diagnostic/export-gating infrastructure**。

---

### 风险 4：文献多在 ScanNet200 / S3DIS / Replica 的单任务设定里讨论，而我们现在的评测是 ConceptGraphs-format / Replica official evaluator

**问题**
- 这些文献里的指标主要是 AP / mAP / mIoU / mAR。
- DuoGraph3D 当前 E70/E71/A2 的主指标是官方 ConceptGraphs-format / Replica 相关结果。

**风险**
- 直接拿文献里“更强的 mAP / mIoU”来暗示我们也该这样做，容易造成协议错配。

**应对**
- 论文里只借结构，不直接借数值；
- 对比要严格写明任务、协议和评测器。

---

### 风险 5：OpenMask3D / Details Matter 证明 oracle mask 很强，但这反过来也说明 carrier 质量是上限

**文献证据**
- OpenMask3D 的 oracle mask 显著抬高 AP。
- 说明 proposal 质量是主瓶颈。

**我们当前结果**
- E70 的 gain 也是靠局部 carrier repair；A1/A3 的 broad relabel 反而会退化。

**风险**
- 若把 gate v2 写成“只要更强读出就行”，会和这条上限证据冲突。

**应对**
- 把 gate 重点放在 carrier 的可靠性分层和局部修复，而不是纯语义读出。

---

## 六、可直接带走的论文级表述

如果要给 DuoGraph3D 的 carrier reliability gate v2 写一句最稳的论文语义，建议接近下面这类表述：

> 我们不是试图用一个统一的语义模型替代几何 carrier，而是以几何 carrier 为默认真值来源，通过多视图一致性、对象中心读出与局部可靠性门控来修复少量高风险 carrier，并将 memory 主要用于诊断、关联与导出控制。

这句话与当前文献主流兼容，但也和 E70 / E71 / A2 的证据是一致的。

---

## 七、材料来源（本地文本）

- `analysis/literature/ccfb_sota_20260628/texts/open3dis_cvpr2024.txt`
- `analysis/literature/ccfb_sota_20260628/texts/details_matter_iccv2025.txt`
- `analysis/literature/ccfb_sota_20260628/texts/mv3dis_cvpr2026.txt`
- `analysis/literature/ccfb_sota_20260628/texts/open_yolo_3d_openreview.txt`
- `analysis/literature/ccfb_sota_20260628/texts/ov3d_cg_iccv2025.txt`
- `analysis/literature/ccfb_sota_20260628/texts/geoguide_cvpr2026.txt`
- `analysis/literature/ccfb_sota_20260628/texts/openmask3d_arxiv.txt`
- 交叉对照：`docs/ccfb_experiment_runlog_20260627.md`
- 交叉对照：`docs/ccfb_experiment_completion_20260627.md`
- 交叉对照：`docs/submission_readiness_20260627.md`

