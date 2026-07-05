# CCF-B 文献精读：OVI-MAP / ESAM / OnlineAnySeg / OpenTrack3D

> 说明：本报告只基于本地已拉取的四篇论文文本完成。与 DuoGraph3D 的“geometry carrier / graph memory / export gate”对照部分，按这三个设计名词的功能含义做概念级推断；未打开实现代码，因此不声称代码级一致。

## 0. 一页结论

四篇工作可以按“**几何承载方式**、**实例记忆组织方式**、**语义/分类何时出栈**”三条线看：

- **OVI-MAP**：最像“先建几何与实例，再按需取语义”的分层式地图系统；最适合作为 **export gate / view selection** 的设计参考。
- **OnlineAnySeg**：最像“在线实例 bank + append-only 映射表”的轻量在线记忆系统；最适合作为 **graph memory / lazy merge** 的参考。
- **ESAM**：最像“把 2D SAM mask 升成 3D query，再用 query 做跨帧合并”的在线实例表示法；最适合作为 **几何载体从点/mask 到 query** 的参考。
- **OpenTrack3D**：最像“视觉-空间 tracker + MLLM 分类”的 proposal/track 管线；最适合作为 **proposal 生成 + query-aware export** 的参考，但依赖较重。

如果只能优先借鉴两项：
1. **OVI-MAP 的对象中心视图选择**（减少冗余 VLM 查询）
2. **OnlineAnySeg 的 append-only 映射表 + 空间关联合并**（适合在线 graph memory）

---

## 1. OVI-MAP: Open-Vocabulary Instance-Semantic Mapping

### 1.1 主题

OVI-MAP 解决的是 **在线、开词表的 3D instance-semantic mapping**：在 RGB-D 流式输入下，先构建 **class-agnostic 3D instance map**，再对实例做 **zero-shot 语义赋值**。

### 1.2 Pipeline

1. **RGB-D 流式重建**：用 TSDF/体素体积持续融合几何。
2. **类别无关实例重建**：每帧做 2D 分割后 lift 到 3D，形成全局 instance map。
3. **对象中心视图选择**：不对每帧都做 VLM 查询，而是按“新视角是否补充了对象表面覆盖”选择少量信息量高的 view。
4. **语义提取与聚合**：对选中的 view 用 VLM/SigLIP 之类抽特征，按实例聚合成 open-vocabulary embedding。
5. **文本检索 / 高亮**：用文本与实例 embedding 做相似度检索，可用于 query grounding。

### 1.3 关键创新

- **解耦 instance reconstruction 和 semantic inference**：先保证实例稳定，再做语义。
- **对象中心视图覆盖（object-centric view coverage）**：减少冗余 VLM 查询。
- **实例级语义聚合**优于像素级/体素级密集存储：更省内存，也更稳定。
- 强调 **online / incremental**，不是一次性离线后处理。

### 1.4 主要指标 / 表格

- **Table 2**（Replica / ScanNet 实例分割）：
  - Replica：Ours **AP75 22.0 / AP50 50.8 / AP25 76.7 / mIoU 36.3**，明显强于 OVO-SLAM（AP75 11.1 / AP50 23.6 / AP25 32.8）。
  - ScanNet：Ours **AP75 9.8 / AP50 24.0 / AP25 37.4 / mIoU 41.2**，优于 OVO-SLAM（AP75 2.0 / AP50 7.4 / AP25 14.4）。
- **Table 3**（开词表语义 + 实例）：
  - Replica：Ours **mIoU 26.5 / mAcc 32.2 / AP25 34.5 / AP50 21.2**；30 FPS 约束下仍保持 Ours **mIoU 27.0 / AP25 31.8**。
  - ScanNet：Ours **mIoU 17.5 / mAcc 27.6 / AP25 23.4 / AP50 15.7**；30 FPS 下 Ours **mIoU 16.3 / AP25 21.1**。
- **Table 4**（视图选择策略）：对象中心 coverage 用更少 VLM 查询，平均约 **47%** 的 query 成本，相比 pixel counting 几乎不掉精度。
- **Table 5**（实例分割对语义的影响）：更好的 instance map 会直接提升语义 AP / mIoU。
- **Table 6**（语义特征融合）：简单加权平均就很强，复杂 clustering 没有明显收益。

### 1.5 与 DuoGraph3D 的相同点 / 冲突

**相同点**
- 如果 DuoGraph3D 的 **geometry carrier** 是“先稳定承载几何/实例，再挂语义”，那 OVI-MAP 的分层策略非常接近。
- 如果 **graph memory** 负责积累实例状态、跨帧保持一致，OVI-MAP 的 instance map + mapping table 与之同构度较高。
- 如果 **export gate** 控制“何时导出语义/外部结果”，OVI-MAP 的对象中心视图选择非常像 gating。

**冲突**
- OVI-MAP 偏向 **实例先行、语义后置**；如果 DuoGraph3D 现在是“几何、语义、关系同步写入”，这会冲突。
- OVI-MAP 很依赖 **VLM 查询预算** 与视图覆盖启发式；如果当前系统想做“全量连续写入”，该设计会显得更保守。

### 1.6 可直接借鉴

1. **对象中心 view coverage 作为 export gate**。
2. **实例级语义聚合，不要把高维语义铺满每个 voxel**。
3. **append-only / lazy remap** 的在线更新方式。
4. **语义更新频率可低于几何更新频率**。

### 1.7 只能启发，不能直接声称

- 不能直接声称“实时开词表地图一定更优”，因为它依赖于 TSDF + VLM + 视图选择组合。
- 不能把 Table 3 的语义指标直接当成 DuoGraph3D 的主结果：它的评价协议是特定数据集和 label-set 对齐方式。
- 不能直接声称“47% 的 VLM 查询节省”对 DuoGraph3D 也成立，除非有同等视角与对象覆盖定义。

---

## 2. EmbodiedSAM (ESAM)

### 2.1 主题

ESAM 是 **在线、实时、细粒度的 3D instance segmentation**，核心目标是把 2D SAM 的能力搬到流式 RGB-D 场景中。

### 2.2 Pipeline

1. **SAM 生成 2D masks**。
2. **Geometric-aware query lifting**：把 2D mask 变成 3D-aware query，而不是简单投影到点云。
3. **Dual-level query decoder**：迭代 refine query，生成更准确的 3D mask。
4. **Query-based mask merging**：利用 query 与 mask 的对应关系，用矩阵运算快速匹配/合并跨帧实例。
5. **辅助任务**：几何、对比、语义三类 similarity 任务，增强 merge 判别性。

### 2.3 关键创新

- **从“2D mask 投影 + 手工 merge”改成“3D query 表示 + learnable merge”**。
- **几何感知 lifting**，避免跨视角不一致。
- **矩阵化 merge**，使 online 速度显著提升。
- 证明了 **只用较少 3D 标注也能学得不错**，因为 2D foundation model 提供强初始化。

### 2.4 主要指标 / 表格

- **Table 1**（ScanNet200 class-agnostic 3D instance segmentation）：
  - SAM3D：AP **20.2**, AP50 **35.7**, AP25 **55.5**，速度 **1369+1518 ms/frame**。
  - ESAM：AP **42.2**, AP50 **63.7**, AP25 **79.6**，速度 **1369+80 ms/frame**。
  - ESAM-E（FastSAM）：AP **43.4**, AP50 **65.4**, AP25 **80.9**，速度 **20+80 ms/frame**。
- **Table 2**（跨数据集泛化 ScanNet200→SceneNN / 3RScan）：
  - ESAM：SceneNN **28.8 / 52.2 / 69.3**，3RScan **14.1 / 31.2 / 59.6**，显著优于 SAM3D。
- **Table 3**（ScanNet / SceneNN 在线实例分割）：
  - ESAM-E+FF 在 ScanNet 上 **AP 42.6 / AP50 61.9 / AP25 77.1**，SceneNN 上 **AP 33.3 / AP50 53.6 / AP25 62.5**。
- **Table 4**（数据效率）：只用 **50% / 10%** 训练数据，性能下降有限，10% 仍明显强于 SAI3D。
- **Table 5**（架构设计）：几何感知 pooling 比平均 pooling 更强，几乎无额外开销。
- **Table 6**（merge 辅助任务）：去掉 box / contrastive / semantic 任一项都会掉点，说明 merge 不是纯 IoU 问题。
- **Table 9**（open-vocab 3D instance segmentation）：ESAM 也可转成 open-vocab，AP **13.7 / 19.2 / 23.9**，优于 SAI3D。

### 2.5 与 DuoGraph3D 的相同点 / 冲突

**相同点**
- 适合类比 DuoGraph3D 的 **geometry carrier**：它把 2D 观测升成稳定的 3D 表示，并用 query 承载实例身份。
- 适合类比 **graph memory**：query/track 的长期维护本质上是实例记忆。
- 它强调 **在线 merge**，与任何“持续积累、逐步稳定”的 memory 设计都很接近。

**冲突**
- ESAM 更像“深度学习化的实例跟踪器”，对端到端训练与辅助任务依赖较强；如果 DuoGraph3D 想保持模块化/可解释，ESAM 的结构可能偏重。
- 它依赖 SAM / query decoder / auxiliary losses，迁移成本高。
- 语义不是主线，核心是 instance segmentation；如果 DuoGraph3D 的 graph memory 更偏关系与知识图谱，ESAM 只能借鉴几何-实例表示，不宜原样照搬。

### 2.6 可直接借鉴

1. **3D query 作为 instance memory 的载体**。
2. **跨帧合并用 learnable similarity + 几何先验，而不只是手工阈值**。
3. **辅助任务拆分几何 / 区分性 / 语义三条监督信号**。
4. **几何感知 pooling 用来过滤噪声边界**。

### 2.7 只能启发，不能直接声称

- 不能直接声称“只要把 2D mask lift 成 query 就能实时且高精度”，因为它有明确的 decoder / auxiliary losses 配套。
- 不能直接声称“ESAM 的速度优势适用于任意输入链路”，它的速度统计含特定 VFM 组件拆分。
- 不能把 open-vocab 结果当成主贡献：ESAM 的主线是 class-agnostic instance segmentation。

---

## 3. OnlineAnySeg（Online zero-shot 3D instance segmentation）

### 3.1 主题

OnlineAnySeg 解决的是 **online、zero-shot 的 3D instance segmentation**：在流式重建中组织和合并实例掩码，并保持零样本能力。

### 3.2 Pipeline

1. **逐帧 2D masks**：从 VFM / SAM 类模型得到 2D 分割。
2. **Lift 到 3D**：将 2D mask 投影/反投影成 3D instance candidate。
3. **Hashed voxel volume + mask bank**：为每个 voxel 维护 mask ID 关联；同时保存 mask bank。
4. **动态同步映射表**：合并后不直接频繁更新所有 voxel，而是用 mapping table 记录旧 ID→新 ID 的映射。
5. **在线 merge 策略**：结合 spatial association、overlap ratio、third-view supporting、feature similarity 等条件进行合并。
6. **语义检索**：保持 zero-shot 语义特征，支持 open-vocabulary 查询。

### 3.3 关键创新

- **online mask merging** 是主创新，不是重分类器。
- **append-only hash / mapping table**：避免频繁改 hash entry，提升在线效率。
- **空间关联优先**：作者的消融表明空间对齐比纯特征相似更关键。
- 适配 **SceneNN / ScanNet200** 的流式场景，且零样本泛化较好。

### 3.4 主要指标 / 表格

- **Table 1**（ScanNet200 / SceneNN 全序列）：
  - Ours：ScanNet200 **AP 18.6 / AP50 36.1 / AP25 53.5**，SceneNN **AP 18.1 / AP50 35.3 / AP25 59.5**，FPS **15**。
  - 对比 EmbodiedSAM：ScanNet200 **28.8 / 42.7 / 54.2**，SceneNN **20.1 / 32.5 / 46.3**，但 EmbodiedSAM 不 zero-shot。
- **Table 2**（SceneNN 中间过程 segmentation）：
  - Ours 在 25% / 50% / 75% / Final 的中间阶段都维持较高 AP，说明 online 过程稳定。
- **Table 3**（merge 消融）：
  - 只用 feature similarity：AP **9.7**，非常差。
  - 去掉 overlap ratio：AP **13.7**。
  - 去掉 third-view supporting：AP **16.9**。
  - 去掉 feature similarity：AP **17.1**。
  - Full merging：AP **18.6**。

### 3.5 与 DuoGraph3D 的相同点 / 冲突

**相同点**
- 与 **graph memory** 的形态最接近：mask bank、ID 映射、在线合并、本质上都是图式记忆/轨迹维护。
- 与 **geometry carrier** 也很契合：几何是判定合并的基础证据，而不是语义后验。
- 如果 DuoGraph3D 有 **export gate**，它的“空间关联优先、特征辅助”的合并准则很像门控。

**冲突**
- 它的核心是 mask merging，不是高层 graph reasoning；如果 DuoGraph3D 追求更丰富的关系语义，OnlineAnySeg 只能借鉴低层记忆更新方式。
- 它的 zero-shot 和 online 目标决定了策略偏保守；若 DuoGraph3D 更强调全局一致性或离线优化，这种 append-only 逻辑可能过于局部。

### 3.6 可直接借鉴

1. **append-only 映射表**，把昂贵的全表更新延后到逻辑层。
2. **空间关联优先，特征相似度辅助**。
3. **多条件 merge 门控**，不要只靠一个阈值。
4. **中间态可查询的 mask bank**，适合调试和回放。

### 3.7 只能启发，不能直接声称

- 不能直接声称“特征相似度越复杂越好”；该文反而证明空间证据是主导。
- 不能直接把它的 15 FPS 作为 DuoGraph3D 的性能预期。
- 不能直接说“零样本就等于无需训练”；它仍有固定的模型组件和阈值策略。

---

## 4. OpenTrack3D

### 4.1 主题

OpenTrack3D 是一个 **training-free、open-vocabulary 3D instance segmentation** 框架，目标是更准确、更通用地生成 3D proposal，并用更强的文本理解做分类。

### 4.2 Pipeline

1. **2D open-vocabulary detector + SAM2** 生成 2D masks。
2. **Lift 到 3D**，并做 denoise。
3. **Visual-Spatial Tracker**：融合视觉特征（DINOv2）和空间信息，构造跨视角一致的 proposal / tracklet。
4. **Proposal Refinement**：
   - Consistency Refinement（多视角一致性过滤）
   - Geometry Refinement（如果有 mesh / superpoints）
   - Proposal merging / NMS
5. **MLLM 分类**：挑选 top-K informative views，用 MLLM 对候选实例做开放词表分类，支持复杂自然语言查询。

### 4.3 关键创新

- **mesh-free 主干**：没有 mesh 也能跑，superpoints 只是可选增强。
- **visual-spatial tracker** 替代“预先 proposal 网络/mesh superpoints”方案。
- **MLLM 替代 CLIP**，改善复杂、组合式、功能性语言理解。
- 通过 **top-K informative views** 控制推理成本。

### 4.4 主要指标 / 表格

- **Table 1**（ScanNet200 / Replica）：
  - ScanNet200：Ours **AP 26.0 / AP50 37.7 / AP25 45.4**。
  - Replica：Ours **AP 23.9 / AP50 36.4 / AP25 47.6**。
  - 对比无 supervised 3D mask 的方法，明显领先。
- **Table 2**（ScanNet++）：
  - Ours **AP 20.6 / AP50 34.2 / AP25 43.4**，显著强于 Any3DIS（12.9 / 19.0 / 21.9）。
- **Table 3**（SceneFun3D）：
  - Ours **AP50 8.9 / AP25 18.5**，优于 OpenMask3D-F（8.0 / 17.5）和 Fun3DU（3.6 / 8.8）。
- **Table 4**（CLIP vs MLLM）：
  - MLLM 在四个数据集上都优于 CLIP，例如 ScanNet200 **26.0 vs 22.9**，SceneFun3D **9.8 vs 4.0**（AP50/AP25 也大幅提升）。
- **Table 5**（proposal generation ablation）：
  - 去掉 IoU、DINO、denoise、mask-wise feature 都会掉点，说明 proposal 生成是多证据融合。
- **Table 6**（proposal refinement）：
  - 去掉 CR / GR / merge 都会明显掉点；尤其 SceneFun3D 上 CR 很关键。
- **Table 7**（τmatch 敏感性）和 **Table 8**（refinement 超参）说明模型对一定范围的超参较稳健。

### 4.5 与 DuoGraph3D 的相同点 / 冲突

**相同点**
- 与 **graph memory** 的“tracklet / candidate / merge”结构很接近。
- 与 **export gate** 非常接近：先筛候选，再挑 top-K views 再分类，相当于“确认后导出”。
- 如果 DuoGraph3D 需要支持自然语言查询，MLLM 分类这一路线很有借鉴意义。

**冲突**
- 对 **mesh-free / scene mesh optional** 的依赖与 DuoGraph3D 若已有固定几何载体可能不完全一致。
- 依赖 MLLM 会引入额外推理成本和 prompt 管理复杂度。
- 它更偏“proposal+classification”而不是持续性的图记忆推理。

### 4.6 可直接借鉴

1. **visual-spatial tracker**：用视觉 + 几何融合维护跨视角一致 proposal。
2. **top-K informative views** 作为 export gate。
3. **MLLM 只在少量高质量候选上做分类**，降低成本。
4. **mesh-free 主干 + 可选几何增强**，增强适配性。

### 4.7 只能启发，不能直接声称

- 不能直接声称“MLLM 一定比 CLIP 好”，因为收益在复杂文本/功能性任务上最显著。
- 不能直接声称 mesh-free 方案可普适到所有几何载体。
- 不能把 SceneFun3D 的功能性查询结果直接外推到一般 indoor instance segmentation。

---

## 5. 对 DuoGraph3D 的总体对照

### 5.1 相同点

如果把 DuoGraph3D 看成“**几何承载 + 图记忆 + 导出门控**”的在线系统，那么四篇论文分别提供了不同层面的同构方案：

- **几何承载**：OVI-MAP 的 TSDF/instance map，ESAM 的 query-lift，OnlineAnySeg 的 voxel-hash，OpenTrack3D 的 visual-spatial proposal。
- **图记忆**：OnlineAnySeg 的 mask bank + mapping table 最像；OpenTrack3D 的 tracklet 也很接近。
- **导出门控**：OVI-MAP 的 view coverage、OpenTrack3D 的 top-K informative views 最像。

### 5.2 冲突

- 这些论文大多仍围绕 **instance segmentation / mapping**，而不是显式“graph reasoning”；如果 DuoGraph3D 的 graph memory 承担关系推理、事件记忆或多跳连接，那它们只能给“记忆组织”的启发，不能直接替代。
- 它们普遍依赖 SAM / DINO / CLIP / MLLM / VLM 链路，推理成本高于纯几何记忆系统。
- 它们的指标主要是 AP / mIoU / FPS，不能直接映射成 DuoGraph3D 的最终任务分数。

### 5.3 最值得借鉴的 3–5 个设计点

1. **先实例、后语义**：几何和实例稳定后再做开词表语义。
2. **对象中心视图选择 / top-K 视图导出**：把 VLM/MLLM 预算放在最有信息量的视角上。
3. **append-only 映射表**：在线合并不要每次重写全局结构。
4. **空间证据优先，语义证据辅助**：先用几何/IoU/track 稳定候选，再用特征或语言确认。
5. **mesh-free 主干 + 可选几何增强**：让系统在不同输入条件下保持可运行。

### 5.4 不能直接声称的内容

- 不能直接声称“这四篇都是 DuoGraph3D 的等价实现/替代实现”。
- 不能把它们的 SOTA 结果直接拿来作为 DuoGraph3D 的对外 claim。
- 不能直接把特定数据集上的 AP 提升外推成你们系统的泛化能力。
- 不能在没有实现核验的情况下，说 DuoGraph3D 现有 geometry carrier / graph memory / export gate 与某一篇论文完全一致。

---

## 6. 适合后续落地的建议

如果后续要把这些论文转成 DuoGraph3D 的设计原则，我建议优先按下面顺序做映射：

1. **OVI-MAP → export gate**：把“什么时候值得花 VLM/LLM 预算”定义清楚。
2. **OnlineAnySeg → graph memory**：把对象 ID、合并历史、空间证据做成可追加、可回放的记忆层。
3. **ESAM → geometry carrier**：如果需要更强实例表达，可以考虑 query 化几何承载。
4. **OpenTrack3D → proposal/classification**：如果需要自然语言查询或功能性理解，再引入 MLLM 作为后置分类器。

